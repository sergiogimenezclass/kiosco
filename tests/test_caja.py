import os
import sys
import pytest
from fastapi.testclient import TestClient

# Add project root directory to path to allow absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
settings.DB_PATH = "test_kiosco.db"

from app.main import app
from app.core.database import init_db, get_db_conn

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    db_file = settings.DB_URL
    # Delete test db if it exists
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except PermissionError:
            pass
            
    # Initialize database and seed admin
    init_db()
    
    yield
    
    # Cleanup test database file after tests
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except PermissionError:
            pass

@pytest.fixture(scope="module")
def admin_token():
    # Login as admin to get token
    response = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"}
    )
    return response.json()["access_token"]

@pytest.fixture(scope="module")
def supervisor_token(admin_token):
    # Create a supervisor user
    response = client.post(
        "/api/users",
        json={
            "nombre": "Supervisor Pruebas",
            "username": "supertest",
            "password": "superpassword123",
            "rol": "SUPERVISOR",
            "activo": 1
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    # Login as supervisor
    response_login = client.post(
        "/api/auth/login",
        data={"username": "supertest", "password": "superpassword123"}
    )
    return response_login.json()["access_token"]

@pytest.fixture(scope="module")
def cashier_token(admin_token):
    # Create a cashier user
    response = client.post(
        "/api/users",
        json={
            "nombre": "Cajero Pruebas",
            "username": "cajerotest",
            "password": "cajeropassword123",
            "rol": "CAJERO",
            "activo": 1
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    # Login as cashier
    response_login = client.post(
        "/api/auth/login",
        data={"username": "cajerotest", "password": "cajeropassword123"}
    )
    return response_login.json()["access_token"]


def test_caja_flow_full(admin_token, supervisor_token, cashier_token):
    # 1. Check current active caja -> should be null/None
    resp = client.get("/api/cajas/actual", headers={"Authorization": f"Bearer {cashier_token}"})
    assert resp.status_code == 200
    assert resp.json() is None

    # 2. Try to close cash register when none is open -> should fail with 404
    resp = client.post(
        "/api/cajas/cierre",
        json={"monto_declarado_centavos": 50000},
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "CASH_REGISTER_NOT_FOUND"

    # 3. Open cash register as Cashier -> should succeed
    resp = client.post(
        "/api/cajas/apertura",
        json={"monto_inicial_centavos": 500000},  # 5,000.00
        headers={"Authorization": f"Bearer {cashier_token}"}
    )
    assert resp.status_code == 201
    caja = resp.json()
    assert caja["estado"] == "ABIERTA"
    assert caja["monto_inicial_centavos"] == 500000
    caja_id = caja["id"]

    # 4. Try to open another register while one is open -> should fail with 400
    resp = client.post(
        "/api/cajas/apertura",
        json={"monto_inicial_centavos": 200000},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "ACTIVE_CASH_REGISTER_EXISTS"

    # 5. Check active register -> should return current one
    resp = client.get("/api/cajas/actual", headers={"Authorization": f"Bearer {cashier_token}"})
    assert resp.status_code == 200
    caja_act = resp.json()
    assert caja_act["id"] == caja_id
    assert caja_act["estado"] == "ABIERTA"

    # 6. Registrate movement as Cashier -> should fail with 403
    resp = client.post(
        "/api/movimientos-caja",
        json={"tipo": "INGRESO", "monto_centavos": 150000, "motivo": "Ingreso extra"},
        headers={"Authorization": f"Bearer {cashier_token}"}
    )
    assert resp.status_code == 403

    # 7. Registrate valid INGRESO as Supervisor -> should succeed
    resp = client.post(
        "/api/movimientos-caja",
        json={"tipo": "INGRESO", "monto_centavos": 100000, "motivo": "Cambio chico inicial"},
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    assert resp.status_code == 201
    mov_ing = resp.json()
    assert mov_ing["tipo"] == "INGRESO"
    assert mov_ing["monto_centavos"] == 100000
    assert mov_ing["motivo"] == "Cambio chico inicial"

    # 8. Registrate valid RETIRO as Supervisor -> should succeed
    resp = client.post(
        "/api/movimientos-caja",
        json={"tipo": "RETIRO", "monto_centavos": 40000, "motivo": "Pago limpieza"},
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    assert resp.status_code == 201
    mov_ret = resp.json()
    assert mov_ret["tipo"] == "RETIRO"
    assert mov_ret["monto_centavos"] == 40000
    assert mov_ret["motivo"] == "Pago limpieza"

    # 9. List movements of the cash register
    resp = client.get(
        f"/api/movimientos-caja?caja_id={caja_id}",
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    assert resp.status_code == 200
    movs = resp.json()
    assert len(movs) == 2
    assert movs[0]["tipo"] == "INGRESO"
    assert movs[1]["tipo"] == "RETIRO"

    # 10. Close register as Cashier -> should fail with 403
    resp = client.post(
        "/api/cajas/cierre",
        json={"monto_declarado_centavos": 560000},
        headers={"Authorization": f"Bearer {cashier_token}"}
    )
    assert resp.status_code == 403

    # 11. Close register as Supervisor (Blind closing)
    # Expected: initial (500000) + INGRESO (100000) - RETIRO (40000) + Sales (0) = 560000 centavos
    # If declared is 550000, deviation should be -10000 centavos
    resp = client.post(
        "/api/cajas/cierre",
        json={"monto_declarado_centavos": 550000},
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    assert resp.status_code == 200
    caja_cerrada = resp.json()
    assert caja_cerrada["estado"] == "CERRADA"
    assert caja_cerrada["monto_esperado_centavos"] == 560000
    assert caja_cerrada["monto_declarado_centavos"] == 550000
    assert caja_cerrada["desviacion_centavos"] == -10000
    assert caja_cerrada["fecha_cierre"] is not None
    assert caja_cerrada["usuario_cierre_id"] is not None

    # 12. Check current active caja -> should be null again
    resp = client.get("/api/cajas/actual", headers={"Authorization": f"Bearer {cashier_token}"})
    assert resp.status_code == 200
    assert resp.json() is None

    # 13. Try to add movement to closed register -> should fail with 404
    resp = client.post(
        "/api/movimientos-caja",
        json={"tipo": "INGRESO", "monto_centavos": 5000, "motivo": "Extra"},
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    assert resp.status_code == 404

    # 14. Try to reopen as Supervisor -> should fail with 403
    resp = client.post(
        f"/api/cajas/{caja_id}/reabrir",
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    assert resp.status_code == 403

    # 15. Reopen as Administrator -> should succeed
    resp = client.post(
        f"/api/cajas/{caja_id}/reabrir",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    caja_reabierta = resp.json()
    assert caja_reabierta["estado"] == "ABIERTA"
    assert caja_reabierta["monto_declarado_centavos"] is None
    assert caja_reabierta["monto_esperado_centavos"] is None
    assert caja_reabierta["desviacion_centavos"] is None
    assert caja_reabierta["fecha_cierre"] is None

    # 16. Verify active register is back
    resp = client.get("/api/cajas/actual", headers={"Authorization": f"Bearer {cashier_token}"})
    assert resp.status_code == 200
    assert resp.json()["id"] == caja_id

    # 17. Close it again so we can list history
    client.post(
        "/api/cajas/cierre",
        json={"monto_declarado_centavos": 560000},
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )

    # 18. Historial as Cashier -> should fail with 403
    resp = client.get("/api/cajas/historial", headers={"Authorization": f"Bearer {cashier_token}"})
    assert resp.status_code == 403

    # 19. Historial as Supervisor -> should succeed and contain our register
    resp = client.get("/api/cajas/historial", headers={"Authorization": f"Bearer {supervisor_token}"})
    assert resp.status_code == 200
    hist = resp.json()
    assert len(hist) >= 1
    assert any(c["id"] == caja_id for c in hist)
