import os
import sys
import pytest
import sqlite3
import datetime
from fastapi.testclient import TestClient

# Add project root directory to path to allow absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
settings.DB_PATH = "test_kiosco.db"

from app.main import app
from app.core.database import init_db, get_db_conn
from app.repositories.catalog import ProductoRepository
from app.repositories.ventas import VentasRepository

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
def cashier_token(admin_token):
    # Create a cashier user
    response = client.post(
        "/api/users",
        json={
            "nombre": "Cajero Pruebas Ventas",
            "username": "cajeroventas",
            "password": "cajeropassword123",
            "rol": "CAJERO",
            "activo": 1
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    # Login as cashier
    response_login = client.post(
        "/api/auth/login",
        data={"username": "cajeroventas", "password": "cajeropassword123"}
    )
    return response_login.json()["access_token"]

@pytest.fixture(scope="module")
def supervisor_token(admin_token):
    # Create a supervisor user
    response = client.post(
        "/api/users",
        json={
            "nombre": "Supervisor Pruebas",
            "username": "supervisorventas",
            "password": "superpassword123",
            "rol": "SUPERVISOR",
            "activo": 1
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    # Login as supervisor
    response_login = client.post(
        "/api/auth/login",
        data={"username": "supervisorventas", "password": "superpassword123"}
    )
    return response_login.json()["access_token"]


def test_sales_full_flow(admin_token, cashier_token):
    # 1. Crear prerrequisitos: Categoría y Productos
    resp_cat = client.post(
        "/api/categorias",
        json={"nombre": "Kiosco Ventas"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_cat.status_code == 201
    cat_id = resp_cat.json()["id"]

    # Producto A: Alfajor Guaymallen - Precio: 8000 ($80.00), Stock: 10
    resp_prod_a = client.post(
        "/api/productos",
        json={
            "nombre": "Alfajor Guaymallen",
            "categoria_id": cat_id,
            "precio_venta_centavos": 8000,
            "stock_actual": 10,
            "unidad_medida": "UNIDAD"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_prod_a.status_code == 201
    prod_a = resp_prod_a.json()
    prod_a_id = prod_a["id"]

    # Producto B: Gaseosa - Precio: 12000 ($120.00), Stock: 5
    resp_prod_b = client.post(
        "/api/productos",
        json={
            "nombre": "Gaseosa Cola",
            "categoria_id": cat_id,
            "precio_venta_centavos": 12000,
            "stock_actual": 5,
            "unidad_medida": "UNIDAD"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_prod_b.status_code == 201
    prod_b = resp_prod_b.json()
    prod_b_id = prod_b["id"]

    # 2. Intentar registrar venta con caja cerrada -> Debe fallar con 400
    venta_payload = {
        "caja_id": "caja_inexistente",
        "metodo_pago": "EFECTIVO",
        "subtotal_centavos": 28000,
        "descuento_items_centavos": 0,
        "descuento_venta_centavos": 0,
        "total_centavos": 28000,
        "monto_recibido_centavos": 30000,
        "vuelto_centavos": 2000,
        "detalles": [
            {"producto_id": prod_a_id, "cantidad": 2, "precio_unitario_centavos": 8000},
            {"producto_id": prod_b_id, "cantidad": 1, "precio_unitario_centavos": 12000}
        ]
    }
    resp = client.post(
        "/api/ventas",
        json=venta_payload,
        headers={"Authorization": f"Bearer {cashier_token}"}
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "CASH_REGISTER_CLOSED"

    # 3. Abrir la caja
    resp_caja = client.post(
        "/api/cajas/apertura",
        json={"monto_inicial_centavos": 100000},
        headers={"Authorization": f"Bearer {cashier_token}"}
    )
    assert resp_caja.status_code == 201
    caja_id = resp_caja.json()["id"]
    
    # Actualizar payload con caja_id correcto
    venta_payload["caja_id"] = caja_id

    # 4. Registrar venta exitosa en EFECTIVO
    resp_venta_1 = client.post(
        "/api/ventas",
        json=venta_payload,
        headers={"Authorization": f"Bearer {cashier_token}"}
    )
    assert resp_venta_1.status_code == 201
    venta_1 = resp_venta_1.json()
    assert venta_1["estado"] == "COMPLETADA"
    assert venta_1["total_centavos"] == 28000
    assert venta_1["vuelto_centavos"] == 2000
    assert len(venta_1["detalles"]) == 2

    # Verificar decremento de stock en base de datos
    with get_db_conn() as conn:
        p_a = ProductoRepository.get_by_id(conn, prod_a_id)
        p_b = ProductoRepository.get_by_id(conn, prod_b_id)
        assert p_a["stock_actual"] == 8  # 10 - 2
        assert p_b["stock_actual"] == 4  # 5 - 1

        # Verificar movimientos de stock creados en DB
        cursor = conn.cursor()
        cursor.execute("SELECT cantidad, tipo, referencia_id FROM movimientos_stock WHERE producto_id = ?;", (prod_a_id,))
        movs = cursor.fetchall()
        assert len(movs) == 1
        assert movs[0]["cantidad"] == -2
        assert movs[0]["tipo"] == "VENTA"
        assert movs[0]["referencia_id"] == venta_1["id"]

    # 5. Registrar venta exitosa en DIGITAL (Tarjeta)
    venta_digital_payload = {
        "caja_id": caja_id,
        "metodo_pago": "DIGITAL",
        "subtotal_centavos": 8000,
        "descuento_items_centavos": 0,
        "descuento_venta_centavos": 0,
        "total_centavos": 8000,
        "monto_recibido_centavos": 8000,
        "vuelto_centavos": 0,
        "detalles": [
            {"producto_id": prod_a_id, "cantidad": 1, "precio_unitario_centavos": 8000}
        ]
    }
    resp_venta_2 = client.post(
        "/api/ventas",
        json=venta_digital_payload,
        headers={"Authorization": f"Bearer {cashier_token}"}
    )
    assert resp_venta_2.status_code == 201
    venta_2 = resp_venta_2.json()
    assert venta_2["metodo_pago"] == "DIGITAL"
    assert venta_2["vuelto_centavos"] == 0

    with get_db_conn() as conn:
        p_a = ProductoRepository.get_by_id(conn, prod_a_id)
        assert p_a["stock_actual"] == 7  # 8 - 1

    # 6. Intentar registrar venta con descuento que supera el máximo permitido (Config: 50%)
    venta_descuento_invalido = {
        "caja_id": caja_id,
        "metodo_pago": "EFECTIVO",
        "subtotal_centavos": 10000,
        "descuento_items_centavos": 0,
        "descuento_venta_centavos": 6000, # 60% de descuento
        "total_centavos": 4000,
        "monto_recibido_centavos": 5000,
        "vuelto_centavos": 1000,
        "detalles": [
            {"producto_id": prod_a_id, "cantidad": 1, "precio_unitario_centavos": 8000} # Espera 8000 subtotal, pero payload manda 10000
        ]
    }
    # Primero probamos discrepancia de cálculo subtotal
    resp = client.post(
        "/api/ventas",
        json=venta_descuento_invalido,
        headers={"Authorization": f"Bearer {cashier_token}"}
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_SUBTOTAL"

    # Corregir subtotal para probar descuento excesivo
    venta_descuento_invalido["subtotal_centavos"] = 8000
    venta_descuento_invalido["descuento_venta_centavos"] = 5000 # 5000 de 8000 es 62.5% (> 50%)
    venta_descuento_invalido["total_centavos"] = 3000
    venta_descuento_invalido["monto_recibido_centavos"] = 3000
    venta_descuento_invalido["vuelto_centavos"] = 0
    
    resp = client.post(
        "/api/ventas",
        json=venta_descuento_invalido,
        headers={"Authorization": f"Bearer {cashier_token}"}
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "EXCEEDED_MAX_DISCOUNT"

    # 7. Intentar registrar venta con stock insuficiente -> Debe fallar con 400
    # Gaseosa tiene stock 4. Solicitamos 5.
    venta_stock_insuficiente = {
        "caja_id": caja_id,
        "metodo_pago": "EFECTIVO",
        "subtotal_centavos": 60000,
        "descuento_items_centavos": 0,
        "descuento_venta_centavos": 0,
        "total_centavos": 60000,
        "monto_recibido_centavos": 60000,
        "vuelto_centavos": 0,
        "detalles": [
            {"producto_id": prod_b_id, "cantidad": 5, "precio_unitario_centavos": 12000}
        ]
    }
    resp = client.post(
        "/api/ventas",
        json=venta_stock_insuficiente,
        headers={"Authorization": f"Bearer {cashier_token}"}
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INSUFFICIENT_STOCK"

    # Verificar que el stock de Gaseosa sigue intacto en 4
    with get_db_conn() as conn:
        p_b = ProductoRepository.get_by_id(conn, prod_b_id)
        assert p_b["stock_actual"] == 4

    # 8. Verificar atomicidad y ROLLBACK de base de datos
    # Armamos un payload con dos items: el primero tiene stock suficiente (Alfajor: stock 7, pedimos 1), 
    # pero el segundo no tiene stock suficiente (Gaseosa: stock 4, pedimos 5).
    # Si la transacción no fuera atómica, el primer producto se descontaría antes de fallar.
    venta_mixta_fallida = {
        "caja_id": caja_id,
        "metodo_pago": "EFECTIVO",
        "subtotal_centavos": 68000,
        "descuento_items_centavos": 0,
        "descuento_venta_centavos": 0,
        "total_centavos": 68000,
        "monto_recibido_centavos": 70000,
        "vuelto_centavos": 2000,
        "detalles": [
            {"producto_id": prod_a_id, "cantidad": 1, "precio_unitario_centavos": 8000},
            {"producto_id": prod_b_id, "cantidad": 5, "precio_unitario_centavos": 12000}
        ]
    }
    resp = client.post(
        "/api/ventas",
        json=venta_mixta_fallida,
        headers={"Authorization": f"Bearer {cashier_token}"}
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INSUFFICIENT_STOCK"

    # Verificar que el stock de ambos productos no sufrió alteraciones (se hizo ROLLBACK)
    with get_db_conn() as conn:
        p_a = ProductoRepository.get_by_id(conn, prod_a_id)
        p_b = ProductoRepository.get_by_id(conn, prod_b_id)
        assert p_a["stock_actual"] == 7  # Queda en 7, no bajó a 6
        assert p_b["stock_actual"] == 4  # Queda en 4
        
        # Verificar que no se insertó ninguna cabecera de venta en la tabla ventas
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ventas WHERE caja_id = ?;", (caja_id,))
        assert cursor.fetchone()[0] == 2  # Solo las primeras dos ventas exitosas

    # 9. Limpieza
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM movimientos_stock;")
        cursor.execute("DELETE FROM venta_detalles;")
        cursor.execute("DELETE FROM ventas;")
        cursor.execute("DELETE FROM productos WHERE id IN (?, ?);", (prod_a_id, prod_b_id))
        cursor.execute("DELETE FROM categorias WHERE id = ?;", (cat_id,))
        conn.commit()


def test_annulments_and_refunds(admin_token, supervisor_token, cashier_token):
    # 1. Preparar: Categoría y Producto
    resp_cat = client.post(
        "/api/categorias",
        json={"nombre": "Kiosco Devoluciones"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_cat.status_code == 201
    cat_id = resp_cat.json()["id"]

    # Producto: Chocolate - Precio: 15000 ($150.00), Stock: 20
    resp_prod = client.post(
        "/api/productos",
        json={
            "nombre": "Chocolate Suizo",
            "categoria_id": cat_id,
            "precio_venta_centavos": 15000,
            "stock_actual": 20,
            "unidad_medida": "UNIDAD"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_prod.status_code == 201
    prod = resp_prod.json()
    prod_id = prod["id"]

    # 2. Abrir caja si no está abierta
    resp_active = client.get("/api/cajas/actual", headers={"Authorization": f"Bearer {cashier_token}"})
    if resp_active.json() is None:
        resp_caja = client.post(
            "/api/cajas/apertura",
            json={"monto_inicial_centavos": 100000},
            headers={"Authorization": f"Bearer {cashier_token}"}
        )
        assert resp_caja.status_code == 201
        caja_id = resp_caja.json()["id"]
    else:
        caja_id = resp_active.json()["id"]

    # 3. Realizar una venta
    venta_payload = {
        "caja_id": caja_id,
        "metodo_pago": "EFECTIVO",
        "subtotal_centavos": 30000,
        "descuento_items_centavos": 0,
        "descuento_venta_centavos": 0,
        "total_centavos": 30000,
        "monto_recibido_centavos": 30000,
        "vuelto_centavos": 0,
        "detalles": [
            {"producto_id": prod_id, "cantidad": 2, "precio_unitario_centavos": 15000}
        ]
    }
    resp_venta = client.post(
        "/api/ventas",
        json=venta_payload,
        headers={"Authorization": f"Bearer {cashier_token}"}
    )
    assert resp_venta.status_code == 201
    venta_1 = resp_venta.json()
    venta_1_id = venta_1["id"]

    # Verificar stock disminuido a 18
    with get_db_conn() as conn:
        p = ProductoRepository.get_by_id(conn, prod_id)
        assert p["stock_actual"] == 18

    # 4. Probar control de rol (cajero no puede anular ni devolver)
    resp_anular_cajero = client.post(
        f"/api/ventas/{venta_1_id}/anular",
        json={"motivo": "Prueba Cajero"},
        headers={"Authorization": f"Bearer {cashier_token}"}
    )
    assert resp_anular_cajero.status_code == 403

    resp_devolver_cajero = client.post(
        f"/api/ventas/{venta_1_id}/devolver",
        json={"motivo": "Prueba Cajero"},
        headers={"Authorization": f"Bearer {cashier_token}"}
    )
    assert resp_devolver_cajero.status_code == 403

    # 5. Anulación Exitosa (Mismo día, rol Supervisor)
    resp_anular = client.post(
        f"/api/ventas/{venta_1_id}/anular",
        json={"motivo": "Venta errónea"},
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    assert resp_anular.status_code == 200
    anulacion = resp_anular.json()
    assert anulacion["venta_id"] == venta_1_id
    assert anulacion["motivo"] == "Venta errónea"

    # Verificar estado de venta y stock revertido a 20
    with get_db_conn() as conn:
        v = VentasRepository.get_venta_by_id(conn, venta_1_id)
        assert v["estado"] == "ANULADA"
        p = ProductoRepository.get_by_id(conn, prod_id)
        assert p["stock_actual"] == 20

        # Verificar movimiento de stock de anulación (+2)
        cursor = conn.cursor()
        cursor.execute("SELECT cantidad, tipo, referencia_id FROM movimientos_stock WHERE tipo = 'ANULACION';")
        movs = cursor.fetchall()
        assert len(movs) == 1
        assert movs[0]["cantidad"] == 2
        assert movs[0]["referencia_id"] == anulacion["id"]

    # 6. Probar que no se puede volver a anular o devolver una venta anulada
    resp_anular_already = client.post(
        f"/api/ventas/{venta_1_id}/anular",
        json={"motivo": "Re-anular"},
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    assert resp_anular_already.status_code == 400
    assert resp_anular_already.json()["error"]["code"] == "INVALID_SALE_STATE"

    resp_devolver_already = client.post(
        f"/api/ventas/{venta_1_id}/devolver",
        json={"motivo": "Devolver sobre anulada"},
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    assert resp_devolver_already.status_code == 400
    assert resp_devolver_already.json()["error"]["code"] == "INVALID_SALE_STATE"

    # 7. Crear otra venta para probar fecha de anulación (Mismo día vs Día anterior)
    resp_venta_2 = client.post(
        "/api/ventas",
        json=venta_payload,
        headers={"Authorization": f"Bearer {cashier_token}"}
    )
    assert resp_venta_2.status_code == 201
    venta_2 = resp_venta_2.json()
    venta_2_id = venta_2["id"]

    # Simular que la venta se hizo ayer en la base de datos
    yesterday = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)).isoformat()
    with get_db_conn() as conn:
        conn.execute("UPDATE ventas SET fecha = ? WHERE id = ?;", (yesterday, venta_2_id))
        conn.commit()

    # Intentar anular la venta de ayer -> Debe fallar con 400 SALE_NOT_SAME_DAY
    resp_anular_yesterday = client.post(
        f"/api/ventas/{venta_2_id}/anular",
        json={"motivo": "Anular ayer"},
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    assert resp_anular_yesterday.status_code == 400
    assert resp_anular_yesterday.json()["error"]["code"] == "SALE_NOT_SAME_DAY"

    # 8. Devolución exitosa de la venta de ayer (Rol Administrador)
    resp_devolver = client.post(
        f"/api/ventas/{venta_2_id}/devolver",
        json={"motivo": "Cliente devuelve producto"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_devolver.status_code == 200
    devolucion = resp_devolver.json()
    assert devolucion["venta_id"] == venta_2_id
    assert devolucion["monto_devuelto_centavos"] == 30000

    # Verificar estado de venta DEVUELTA y stock revertido a 20
    with get_db_conn() as conn:
        v = VentasRepository.get_venta_by_id(conn, venta_2_id)
        assert v["estado"] == "DEVUELTA"
        p = ProductoRepository.get_by_id(conn, prod_id)
        assert p["stock_actual"] == 20

        # Verificar movimiento de stock de devolución (+2)
        cursor = conn.cursor()
        cursor.execute("SELECT cantidad, tipo, referencia_id FROM movimientos_stock WHERE tipo = 'DEVOLUCION';")
        movs = cursor.fetchall()
        assert len(movs) == 1
        assert movs[0]["cantidad"] == 2
        assert movs[0]["referencia_id"] == devolucion["id"]

    # 9. Limpieza
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM anulaciones;")
        cursor.execute("DELETE FROM devoluciones;")
        cursor.execute("DELETE FROM movimientos_stock;")
        cursor.execute("DELETE FROM venta_detalles;")
        cursor.execute("DELETE FROM ventas;")
        cursor.execute("DELETE FROM productos WHERE id = ?;", (prod_id,))
        cursor.execute("DELETE FROM categorias WHERE id = ?;", (cat_id,))
        conn.commit()


def test_list_sales_endpoint(admin_token, supervisor_token, cashier_token):
    # 1. Access as Cashier -> should fail with 403
    resp = client.get("/api/ventas", headers={"Authorization": f"Bearer {cashier_token}"})
    assert resp.status_code == 403

    # 2. Access as Supervisor -> should succeed with 200
    resp_sup = client.get("/api/ventas", headers={"Authorization": f"Bearer {supervisor_token}"})
    assert resp_sup.status_code == 200
    assert isinstance(resp_sup.json(), list)

    # 3. Access as Admin -> should succeed with 200
    resp_adm = client.get("/api/ventas", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp_adm.status_code == 200
    assert isinstance(resp_adm.json(), list)

