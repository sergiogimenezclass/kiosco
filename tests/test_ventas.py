import os
import sys
import pytest
import sqlite3
from fastapi.testclient import TestClient

# Add project root directory to path to allow absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
settings.DB_PATH = "test_kiosco.db"

from app.main import app
from app.core.database import init_db, get_db_conn
from app.repositories.catalog import ProductoRepository

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
