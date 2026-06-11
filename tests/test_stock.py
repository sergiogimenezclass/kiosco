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
from app.repositories.catalog import ProductoRepository

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
def cashier_token(admin_token):
    client.post(
        "/api/users",
        json={
            "nombre": "Cajero Pruebas Stock",
            "username": "cajerostock",
            "password": "cajeropassword123",
            "rol": "CAJERO",
            "activo": 1
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    response_login = client.post(
        "/api/auth/login",
        data={"username": "cajerostock", "password": "cajeropassword123"}
    )
    return response_login.json()["access_token"]

@pytest.fixture(scope="module")
def supervisor_token(admin_token):
    client.post(
        "/api/users",
        json={
            "nombre": "Supervisor Pruebas Stock",
            "username": "supervisorstock",
            "password": "superpassword123",
            "rol": "SUPERVISOR",
            "activo": 1
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    response_login = client.post(
        "/api/auth/login",
        data={"username": "supervisorstock", "password": "superpassword123"}
    )
    return response_login.json()["access_token"]

def test_stock_adjustment_flow(admin_token, supervisor_token):
    # 1. Crear categoría y producto
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO categorias (id, nombre) VALUES ('cat_stock', 'Categoria Stock');")
        conn.commit()

    resp_prod = client.post(
        "/api/productos",
        json={
            "nombre": "Producto Test Stock",
            "categoria_id": "cat_stock",
            "precio_venta_centavos": 1000,
            "stock_actual": 10,
            "stock_minimo": 5,
            "unidad_medida": "UNIDAD"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_prod.status_code == 201
    prod_id = resp_prod.json()["id"]

    # 2. Realizar ajuste positivo (+5) con rol supervisor
    resp_adj = client.post(
        "/api/stock/ajuste",
        json={
            "producto_id": prod_id,
            "cantidad_delta": 5,
            "motivo": "Ajuste positivo por inventario físico"
        },
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    assert resp_adj.status_code == 200
    adj_data = resp_adj.json()
    assert adj_data["producto_id"] == prod_id
    assert adj_data["cantidad"] == 5
    assert adj_data["stock_anterior"] == 10
    assert adj_data["stock_nuevo"] == 15
    assert adj_data["tipo"] == "AJUSTE"
    assert adj_data["motivo"] == "Ajuste positivo por inventario físico"

    # Verificar stock en catálogo
    resp_prod_check = client.get(f"/api/productos/{prod_id}", headers={"Authorization": f"Bearer {supervisor_token}"})
    assert resp_prod_check.status_code == 200
    assert resp_prod_check.json()["stock_actual"] == 15

    # 3. Realizar ajuste negativo (-8) con rol admin
    resp_adj_neg = client.post(
        "/api/stock/ajuste",
        json={
            "producto_id": prod_id,
            "cantidad_delta": -8,
            "motivo": "Mermas detectadas"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_adj_neg.status_code == 200
    adj_neg_data = resp_adj_neg.json()
    assert adj_neg_data["cantidad"] == -8
    assert adj_neg_data["stock_anterior"] == 15
    assert adj_neg_data["stock_nuevo"] == 7

    # Verificar stock en catálogo
    resp_prod_check_2 = client.get(f"/api/productos/{prod_id}", headers={"Authorization": f"Bearer {supervisor_token}"})
    assert resp_prod_check_2.json()["stock_actual"] == 7

def test_stock_adjustment_negative_fails(supervisor_token):
    # Obtener el producto creado en el test anterior
    # Su stock actual es 7. Haremos un ajuste de -8, lo que daría stock final -1 (inválido).
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM productos WHERE nombre = 'Producto Test Stock';")
        prod_id = cursor.fetchone()["id"]

    resp = client.post(
        "/api/stock/ajuste",
        json={
            "producto_id": prod_id,
            "cantidad_delta": -8,
            "motivo": "Ajuste inválido a negativo"
        },
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_STOCK"

    # Verificar que el stock no cambió y sigue en 7
    resp_prod_check = client.get(f"/api/productos/{prod_id}", headers={"Authorization": f"Bearer {supervisor_token}"})
    assert resp_prod_check.json()["stock_actual"] == 7

def test_stock_adjustment_empty_motive_fails(supervisor_token):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM productos WHERE nombre = 'Producto Test Stock';")
        prod_id = cursor.fetchone()["id"]

    # Ajuste con motivo vacío
    resp = client.post(
        "/api/stock/ajuste",
        json={
            "producto_id": prod_id,
            "cantidad_delta": 2,
            "motivo": "   "
        },
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_MOTIVE"

def test_stock_intake_flow(admin_token, supervisor_token):
    # 1. Crear proveedor y producto
    resp_prov = client.post(
        "/api/proveedores",
        json={
            "nombre": "Proveedor Stock Inc",
            "telefono": "123456",
            "email": "stock@test.com"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_prov.status_code == 201
    prov_id = resp_prov.json()["id"]

    resp_prod = client.post(
        "/api/productos",
        json={
            "nombre": "Producto Intake Test",
            "categoria_id": "cat_stock",
            "proveedor_id": prov_id,
            "precio_venta_centavos": 2000,
            "stock_actual": 5,
            "stock_minimo": 10,  # Bajo mínimo inicialmente
            "unidad_medida": "UNIDAD"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_prod.status_code == 201
    prod_id = resp_prod.json()["id"]

    # 2. Registrar ingreso de stock (+20) de mercadería con proveedor
    resp_ing = client.post(
        "/api/stock/ingreso",
        json={
            "producto_id": prod_id,
            "cantidad": 20,
            "proveedor_id": prov_id,
            "motivo": "Compra de mercadería lote 102"
        },
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    assert resp_ing.status_code == 200
    ing_data = resp_ing.json()
    assert ing_data["producto_id"] == prod_id
    assert ing_data["cantidad"] == 20
    assert ing_data["stock_anterior"] == 5
    assert ing_data["stock_nuevo"] == 25
    assert ing_data["tipo"] == "INGRESO"
    assert ing_data["proveedor_id"] == prov_id
    assert ing_data["motivo"] == "Compra de mercadería lote 102"

    # Verificar stock en catálogo
    resp_prod_check = client.get(f"/api/productos/{prod_id}", headers={"Authorization": f"Bearer {supervisor_token}"})
    assert resp_prod_check.json()["stock_actual"] == 25

def test_stock_intake_invalid_provider_fails(supervisor_token):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM productos WHERE nombre = 'Producto Intake Test';")
        prod_id = cursor.fetchone()["id"]

    resp = client.post(
        "/api/stock/ingreso",
        json={
            "producto_id": prod_id,
            "cantidad": 10,
            "proveedor_id": "proveedor_no_existente",
            "motivo": "Lote fantasma"
        },
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "PROVIDER_NOT_FOUND"

def test_stock_intake_invalid_quantity_fails(supervisor_token):
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, proveedor_id FROM productos WHERE nombre = 'Producto Intake Test';")
        row = cursor.fetchone()
        prod_id = row["id"]
        prov_id = row["proveedor_id"]

    # Cantidad <= 0 es inválida
    resp = client.post(
        "/api/stock/ingreso",
        json={
            "producto_id": prod_id,
            "cantidad": 0,
            "proveedor_id": prov_id,
            "motivo": "Ingreso cero"
        },
        headers={"Authorization": f"Bearer {supervisor_token}"}
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_QUANTITY"

def test_stock_get_movements(supervisor_token):
    resp = client.get("/api/stock/movimientos", headers={"Authorization": f"Bearer {supervisor_token}"})
    assert resp.status_code == 200
    movs = resp.json()
    assert len(movs) >= 3  # Deben existir al menos los dos ajustes y el ingreso realizados
    
    # El más reciente debe ser el ingreso (+20) o el error de validación (que no se guarda en movimientos)
    # Así que el primero del historial debe ser el de compra de mercadería lote 102
    assert movs[0]["tipo"] == "INGRESO"
    assert movs[0]["motivo"] == "Compra de mercadería lote 102"
    assert movs[1]["tipo"] == "AJUSTE"
    assert movs[1]["motivo"] == "Mermas detectadas"
    assert movs[2]["tipo"] == "AJUSTE"
    assert movs[2]["motivo"] == "Ajuste positivo por inventario físico"

def test_stock_bajo_minimo(admin_token, supervisor_token):
    # Creamos un producto que tiene stock 2 y stock_minimo 5 (bajo mínimo)
    resp_prod_bajo = client.post(
        "/api/productos",
        json={
            "nombre": "Producto Bajo Stock",
            "categoria_id": "cat_stock",
            "precio_venta_centavos": 500,
            "stock_actual": 2,
            "stock_minimo": 5,
            "unidad_medida": "UNIDAD"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp_prod_bajo.status_code == 201
    prod_bajo_id = resp_prod_bajo.json()["id"]

    # Obtenemos productos bajo mínimo
    resp = client.get("/api/stock/bajo-minimo", headers={"Authorization": f"Bearer {supervisor_token}"})
    assert resp.status_code == 200
    bajo_minimo_list = resp.json()
    
    # Debería contener a "Producto Test Stock" (stock 7, mínimo 5 -> no bajo mínimo)
    # y "Producto Intake Test" (stock 25, mínimo 10 -> no bajo mínimo)
    # pero sí a "Producto Bajo Stock" (stock 2, mínimo 5 -> bajo mínimo)
    # Verifiquemos
    names = [p["nombre"] for p in bajo_minimo_list]
    assert "Producto Bajo Stock" in names
    assert "Producto Test Stock" not in names
    assert "Producto Intake Test" not in names

def test_stock_permissions(cashier_token):
    # El cajero no debería acceder a ningún endpoint de stock (debe retornar 403)
    resp1 = client.post(
        "/api/stock/ajuste",
        json={"producto_id": "id", "cantidad_delta": 5, "motivo": "cajero"},
        headers={"Authorization": f"Bearer {cashier_token}"}
    )
    assert resp1.status_code == 403

    resp2 = client.post(
        "/api/stock/ingreso",
        json={"producto_id": "id", "cantidad": 5, "proveedor_id": "prov", "motivo": "cajero"},
        headers={"Authorization": f"Bearer {cashier_token}"}
    )
    assert resp2.status_code == 403

    resp3 = client.get("/api/stock/movimientos", headers={"Authorization": f"Bearer {cashier_token}"})
    assert resp3.status_code == 403

    resp4 = client.get("/api/stock/bajo-minimo", headers={"Authorization": f"Bearer {cashier_token}"})
    assert resp4.status_code == 403
