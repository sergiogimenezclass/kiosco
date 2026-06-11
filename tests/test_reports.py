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
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except PermissionError:
            pass
            
    init_db()
    yield
    
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except PermissionError:
            pass

@pytest.fixture(scope="module")
def admin_token():
    response = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"}
    )
    return response.json()["access_token"]

@pytest.fixture(scope="module")
def supervisor_token(admin_token):
    client.post(
        "/api/users",
        json={
            "nombre": "Supervisor Pruebas Reportes",
            "username": "supervisorreps",
            "password": "superpassword123",
            "rol": "SUPERVISOR",
            "activo": 1
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    response_login = client.post(
        "/api/auth/login",
        data={"username": "supervisorreps", "password": "superpassword123"}
    )
    return response_login.json()["access_token"]

@pytest.fixture(scope="module")
def cashier_token(admin_token):
    client.post(
        "/api/users",
        json={
            "nombre": "Cajero Pruebas Reportes",
            "username": "cajeroreps",
            "password": "cajeropassword123",
            "rol": "CAJERO",
            "activo": 1
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    response_login = client.post(
        "/api/auth/login",
        data={"username": "cajeroreps", "password": "cajeropassword123"}
    )
    return response_login.json()["access_token"]

def test_reports_generation_and_calculations(admin_token, supervisor_token):
    # 1. Configurar datos de prueba: Categorías y Productos
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categorias (id, nombre) VALUES ('cat_reps', 'Categoria Reportes');")
        conn.commit()

    # Producto A (Normal, stock alto)
    resp_prod_a = client.post(
        "/api/productos",
        json={
            "nombre": "Producto Rep A",
            "categoria_id": "cat_reps",
            "precio_venta_centavos": 1000, # $10.00
            "stock_actual": 100,
            "stock_minimo": 10,
            "unidad_medida": "UNIDAD"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    prod_a_id = resp_prod_a.json()["id"]

    # Producto B (Stock Bajo)
    resp_prod_b = client.post(
        "/api/productos",
        json={
            "nombre": "Producto Rep B",
            "categoria_id": "cat_reps",
            "precio_venta_centavos": 2000, # $20.00
            "stock_actual": 3,
            "stock_minimo": 5, # Bajo mínimo
            "unidad_medida": "UNIDAD"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    prod_b_id = resp_prod_b.json()["id"]

    # 2. Abrir Caja
    resp_apertura = client.post(
        "/api/cajas/apertura",
        json={"monto_inicial_centavos": 5000}, # $50.00
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_apertura.status_code == 200
    caja_id = resp_apertura.json()["id"]

    # 3. Movimientos de Caja: Ingreso de $10 y Retiro de $5
    client.post(
        "/api/movimientos-caja",
        json={"caja_id": caja_id, "tipo": "INGRESO", "monto_centavos": 1000, "motivo": "Cambio inicial extra"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    client.post(
        "/api/movimientos-caja",
        json={"caja_id": caja_id, "tipo": "RETIRO", "monto_centavos": 500, "motivo": "Comprar insumos oficina"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # 4. Registrar Ventas
    # Venta 1: Completada Efectivo (Subtotal $20.00, Total $20.00)
    resp_venta_1 = client.post(
        "/api/ventas",
        json={
            "caja_id": caja_id,
            "metodo_pago": "EFECTIVO",
            "subtotal_centavos": 2000,
            "descuento_items_centavos": 0,
            "descuento_venta_centavos": 0,
            "total_centavos": 2000,
            "monto_recibido_centavos": 2000,
            "vuelto_centavos": 0,
            "detalles": [
                {"producto_id": prod_a_id, "cantidad": 2, "precio_unitario_centavos": 1000, "descuento_centavos": 0}
            ]
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_venta_1.status_code == 200
    venta_1_id = resp_venta_1.json()["id"]

    # Venta 2: Completada Digital (Subtotal $20.00, Descuento $2.00, Total $18.00)
    resp_venta_2 = client.post(
        "/api/ventas",
        json={
            "caja_id": caja_id,
            "metodo_pago": "DIGITAL",
            "subtotal_centavos": 2000,
            "descuento_items_centavos": 0,
            "descuento_venta_centavos": 200,
            "total_centavos": 1800,
            "monto_recibido_centavos": 1800,
            "vuelto_centavos": 0,
            "detalles": [
                {"producto_id": prod_a_id, "cantidad": 2, "precio_unitario_centavos": 1000, "descuento_centavos": 0}
            ]
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_venta_2.status_code == 200

    # Venta 3: Venta que será ANULADA
    resp_venta_3 = client.post(
        "/api/ventas",
        json={
            "caja_id": caja_id,
            "metodo_pago": "EFECTIVO",
            "subtotal_centavos": 1000,
            "descuento_items_centavos": 0,
            "descuento_venta_centavos": 0,
            "total_centavos": 1000,
            "monto_recibido_centavos": 1000,
            "vuelto_centavos": 0,
            "detalles": [
                {"producto_id": prod_a_id, "cantidad": 1, "precio_unitario_centavos": 1000, "descuento_centavos": 0}
            ]
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    venta_3_id = resp_venta_3.json()["id"]

    # Anular Venta 3
    resp_anular = client.post(
        f"/api/ventas/{venta_3_id}/anular",
        json={"motivo": "Error de tipeo cajero"},
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    assert resp_anular.status_code == 200

    # Venta 4: Venta que será DEVUELTA
    resp_venta_4 = client.post(
        "/api/ventas",
        json={
            "caja_id": caja_id,
            "metodo_pago": "DIGITAL",
            "subtotal_centavos": 2000,
            "descuento_items_centavos": 0,
            "descuento_venta_centavos": 0,
            "total_centavos": 2000,
            "monto_recibido_centavos": 2000,
            "vuelto_centavos": 0,
            "detalles": [
                {"producto_id": prod_b_id, "cantidad": 1, "precio_unitario_centavos": 2000, "descuento_centavos": 0}
            ]
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    venta_4_id = resp_venta_4.json()["id"]

    # Devolver Venta 4
    resp_devolver = client.post(
        f"/api/ventas/{venta_4_id}/devolver",
        json={"motivo": "Fallo en producto"},
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    assert resp_devolver.status_code == 200

    # --- VERIFICAR REPORTES (GET) ---

    # 1. Ventas Diarias
    resp_diarias = client.get("/api/reportes/ventas-diarias", headers={"Authorization": f"Bearer {supervisor_token}"})
    assert resp_diarias.status_code == 200
    res_diarias = resp_diarias.json()

    # Cálculos esperados de ventas en estado COMPLETADA:
    # Venta 1 ($20) + Venta 2 ($18) = $38 (3800 centavos)
    assert res_diarias["total_general_centavos"] == 3800
    assert res_diarias["cantidad_ventas"] == 2
    assert res_diarias["descuentos_aplicados_centavos"] == 200

    # Anulaciones (Venta 3: $10)
    assert res_diarias["cantidad_anulaciones"] == 1
    assert res_diarias["total_anulado_centavos"] == 1000

    # Devoluciones (Venta 4: $20 devueltos)
    assert res_diarias["cantidad_devoluciones"] == 1
    assert res_diarias["total_devuelto_centavos"] == 2000

    # Desglose por método de pago (Venta 1: Efectivo $20, Venta 2: Digital $18)
    metodos = {m["metodo_pago"]: m["total_centavos"] for m in res_diarias["total_por_metodo"]}
    assert metodos.get("EFECTIVO") == 2000
    assert metodos.get("DIGITAL") == 1800

    # 2. Cajas
    resp_cajas = client.get("/api/reportes/cajas", headers={"Authorization": f"Bearer {supervisor_token}"})
    assert resp_cajas.status_code == 200
    res_cajas = resp_cajas.json()
    assert len(res_cajas) >= 1
    caja_rep = [c for c in res_cajas if c["id"] == caja_id][0]
    assert caja_rep["monto_inicial_centavos"] == 5000
    assert caja_rep["monto_ingresos_centavos"] == 1000
    assert caja_rep["monto_retiros_centavos"] == 500
    assert caja_rep["monto_ventas_efectivo_centavos"] == 2000
    assert caja_rep["monto_ventas_digital_centavos"] == 1800

    # 3. Ranking de Productos
    resp_ranking = client.get("/api/reportes/ranking-productos?ordenar_por=cantidad", headers={"Authorization": f"Bearer {supervisor_token}"})
    assert resp_ranking.status_code == 200
    res_ranking = resp_ranking.json()
    # Producto Rep A se vendió en Venta 1 (2 unidades) y Venta 2 (2 unidades) -> Total 4 unidades COMPLETADAS.
    # Venta 3 (1 unidad) anulada, Venta 4 (1 unidad) devuelta.
    # Así que Producto Rep A tiene 4 unidades vendidas.
    assert len(res_ranking) >= 1
    rank_a = [r for r in res_ranking if r["producto_id"] == prod_a_id][0]
    assert rank_a["cantidad_vendida"] == 4
    assert rank_a["monto_vendido_centavos"] == 4000

    # 4. Stock Bajo
    resp_bajo = client.get("/api/reportes/stock-bajo", headers={"Authorization": f"Bearer {supervisor_token}"})
    assert resp_bajo.status_code == 200
    res_bajo = resp_bajo.json()
    names_bajo = [p["nombre_producto"] for p in res_bajo]
    # Producto Rep B tiene stock 3, stock_minimo 5 -> Bajo Stock.
    # Producto Rep A tiene stock 100 - 4 completados - 1 devuelto (el devuelto se revierte +1, el anulado se revierte +1) -> Stock final 100. Minimo 10. No es bajo stock.
    assert "Producto Rep B" in names_bajo
    assert "Producto Rep A" not in names_bajo

    # Cierre de caja para limpiar
    client.post(
        "/api/cajas/cierre",
        json={"monto_declarado_centavos": 7500},
        headers={"Authorization": f"Bearer {admin_token}"}
    )


def test_reports_permissions(cashier_token):
    # El rol CAJERO no tiene acceso a ningún reporte (retorna 403)
    endpoints = [
        "/api/reportes/ventas-diarias",
        "/api/reportes/cajas",
        "/api/reportes/ranking-productos",
        "/api/reportes/stock-bajo",
        "/api/reportes/ventas-diarias/export?format=csv",
        "/api/reportes/cajas/export?format=xlsx",
        "/api/reportes/ranking-productos/export?format=pdf"
    ]
    for url in endpoints:
        resp = client.get(url, headers={"Authorization": f"Bearer {cashier_token}"})
        assert resp.status_code == 403


def test_reports_exports(supervisor_token):
    # Test export formatos: ventas-diarias
    for fmt, mime in [("csv", "text/csv"), ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), ("pdf", "application/pdf")]:
        resp = client.get(f"/api/reportes/ventas-diarias/export?format={fmt}", headers={"Authorization": f"Bearer {supervisor_token}"})
        assert resp.status_code == 200
        assert resp.headers["Content-Type"].startswith(mime)
        assert "attachment; filename=" in resp.headers["Content-Disposition"]
        assert len(resp.content) > 0

    # Test export formatos: cajas
    for fmt, mime in [("csv", "text/csv"), ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), ("pdf", "application/pdf")]:
        resp = client.get(f"/api/reportes/cajas/export?format={fmt}", headers={"Authorization": f"Bearer {supervisor_token}"})
        assert resp.status_code == 200
        assert resp.headers["Content-Type"].startswith(mime)
        assert "attachment; filename=" in resp.headers["Content-Disposition"]
        assert len(resp.content) > 0

    # Test export formatos: ranking-productos
    for fmt, mime in [("csv", "text/csv"), ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), ("pdf", "application/pdf")]:
        resp = client.get(f"/api/reportes/ranking-productos/export?format={fmt}&ordenar_por=monto", headers={"Authorization": f"Bearer {supervisor_token}"})
        assert resp.status_code == 200
        assert resp.headers["Content-Type"].startswith(mime)
        assert "attachment; filename=" in resp.headers["Content-Disposition"]
        assert len(resp.content) > 0

    # Test export formatos: stock-bajo
    for fmt, mime in [("csv", "text/csv"), ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), ("pdf", "application/pdf")]:
        resp = client.get(f"/api/reportes/stock-bajo/export?format={fmt}", headers={"Authorization": f"Bearer {supervisor_token}"})
        assert resp.status_code == 200
        assert resp.headers["Content-Type"].startswith(mime)
        assert "attachment; filename=" in resp.headers["Content-Disposition"]
        assert len(resp.content) > 0
