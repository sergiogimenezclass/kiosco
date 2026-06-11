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
from app.repositories.user import UserRepository

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

# --- CATEGORÍAS TESTS ---

def test_crud_categorias(admin_token, cashier_token):
    # 1. Create category as Cashier -> should fail with 403
    resp = client.post(
        "/api/categorias",
        json={"nombre": "Bebidas"},
        headers={"Authorization": f"Bearer {cashier_token}"}
    )
    assert resp.status_code == 403
    
    # 2. Create category as Admin -> should succeed
    resp = client.post(
        "/api/categorias",
        json={"nombre": "Bebidas"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 201
    cat = resp.json()
    assert "id" in cat
    assert cat["nombre"] == "Bebidas"
    cat_id = cat["id"]

    # 3. Create duplicate category -> should fail with 409
    resp = client.post(
        "/api/categorias",
        json={"nombre": "Bebidas"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "CATEGORY_ALREADY_EXISTS"

    # 4. Get all categories
    resp = client.get("/api/categorias", headers={"Authorization": f"Bearer {cashier_token}"})
    assert resp.status_code == 200
    cats = resp.json()
    assert len(cats) >= 1
    assert any(c["id"] == cat_id for c in cats)

    # 5. Update category
    resp = client.put(
        f"/api/categorias/{cat_id}",
        json={"nombre": "Bebidas Alcoholicas"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["nombre"] == "Bebidas Alcoholicas"

    # 6. Delete category
    resp = client.delete(f"/api/categorias/{cat_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    
    # Verify deleted
    resp = client.get(f"/api/categorias/{cat_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 404

# --- MARCAS TESTS ---

def test_crud_marcas(admin_token, cashier_token):
    # 1. Create brand as Admin
    resp = client.post(
        "/api/marcas",
        json={"nombre": "Coca Cola"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 201
    brand = resp.json()
    brand_id = brand["id"]

    # 2. Get brands
    resp = client.get("/api/marcas", headers={"Authorization": f"Bearer {cashier_token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    # 3. Update brand
    resp = client.put(
        f"/api/marcas/{brand_id}",
        json={"nombre": "Coca-Cola Company"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    
    # 4. Delete brand
    resp = client.delete(f"/api/marcas/{brand_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200

# --- PROVEEDORES TESTS ---

def test_crud_proveedores(admin_token, cashier_token):
    # 1. Create supplier
    resp = client.post(
        "/api/proveedores",
        json={"nombre": "Distribuidora Sur", "telefono": "12345678", "email": "sur@example.com"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 201
    prov = resp.json()
    prov_id = prov["id"]

    # 2. Update supplier
    resp = client.put(
        f"/api/proveedores/{prov_id}",
        json={"nombre": "Distribuidora Sur S.A.", "telefono": "98765432", "email": "info@sur.com"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["telefono"] == "98765432"

    # 3. Delete supplier
    resp = client.delete(f"/api/proveedores/{prov_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200

# --- PRODUCTOS Y BÚSQUEDA POR CÓDIGO DE BARRAS TESTS ---

def test_crud_productos_validation_and_history(admin_token, cashier_token):
    # Pre-requisites: Category, Brand, Provider
    resp_cat = client.post("/api/categorias", json={"nombre": "Almacen"}, headers={"Authorization": f"Bearer {admin_token}"})
    cat_id = resp_cat.json()["id"]
    
    resp_brand = client.post("/api/marcas", json={"nombre": "Arcor"}, headers={"Authorization": f"Bearer {admin_token}"})
    brand_id = resp_brand.json()["id"]

    resp_prov = client.post("/api/proveedores", json={"nombre": "Arcor Dist."}, headers={"Authorization": f"Bearer {admin_token}"})
    prov_id = resp_prov.json()["id"]

    # 1. Validation error: Negative stock
    resp = client.post(
        "/api/productos",
        json={
            "nombre": "Galletitas Sonrisas",
            "categoria_id": cat_id,
            "marca_id": brand_id,
            "precio_venta_centavos": 15000,
            "stock_actual": -10,
            "unidad_medida": "UNIDAD"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 422 # Pydantic validation handles ge=0

    # 2. Validation error: Invalid Price
    resp = client.post(
        "/api/productos",
        json={
            "nombre": "Galletitas Sonrisas",
            "categoria_id": cat_id,
            "marca_id": brand_id,
            "precio_venta_centavos": 0,
            "stock_actual": 10,
            "unidad_medida": "UNIDAD"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 422 # Pydantic validation handles gt=0

    # 3. Create valid product with barcodes
    product_data = {
        "nombre": "Chocolate Block 38g",
        "descripcion": "Chocolate con maní",
        "categoria_id": cat_id,
        "marca_id": brand_id,
        "proveedor_id": prov_id,
        "precio_venta_centavos": 35000,
        "stock_actual": 50,
        "stock_minimo": 5,
        "unidad_medida": "UNIDAD",
        "codigos_barras": ["779058055610", "111222333"]
    }
    resp = client.post(
        "/api/productos",
        json=product_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 201
    prod = resp.json()
    assert prod["nombre"] == "Chocolate Block 38g"
    assert "779058055610" in prod["codigos_barras"]
    assert "111222333" in prod["codigos_barras"]
    prod_id = prod["id"]

    # 4. Search by barcode
    resp = client.get(f"/api/productos/codigo/779058055610", headers={"Authorization": f"Bearer {cashier_token}"})
    assert resp.status_code == 200
    assert resp.json()["id"] == prod_id

    # 5. Search by second barcode
    resp = client.get(f"/api/productos/codigo/111222333", headers={"Authorization": f"Bearer {cashier_token}"})
    assert resp.status_code == 200
    assert resp.json()["id"] == prod_id

    # 6. Search by non-existent barcode -> 404
    resp = client.get(f"/api/productos/codigo/999999999999", headers={"Authorization": f"Bearer {cashier_token}"})
    assert resp.status_code == 404

    # 7. Predictive search by name query
    resp = client.get(f"/api/productos?q=Block", headers={"Authorization": f"Bearer {cashier_token}"})
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) >= 1
    assert results[0]["id"] == prod_id

    # 8. Duplicate barcode assignment on another product -> should fail with 409
    resp = client.post(
        "/api/productos",
        json={
            "nombre": "Chocolate Block 100g",
            "categoria_id": cat_id,
            "precio_venta_centavos": 80000,
            "stock_actual": 10,
            "unidad_medida": "UNIDAD",
            "codigos_barras": ["779058055610"]
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "BARCODE_ALREADY_EXISTS"

    # 9. Update product barcodes and properties
    resp = client.put(
        f"/api/productos/{prod_id}",
        json={
            "precio_venta_centavos": 38000,
            "codigos_barras": ["779058055610", "444555666"] # Replaces 111222333 with 444555666
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    updated_prod = resp.json()
    assert updated_prod["precio_venta_centavos"] == 38000
    assert "444555666" in updated_prod["codigos_barras"]
    assert "111222333" not in updated_prod["codigos_barras"]

    # 10. Delete validation with history
    # Insert fake movement history in DB
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM usuarios LIMIT 1;")
        db_user_id = cursor.fetchone()["id"]
        # Insert a fake movement
        cursor.execute(
            """
            INSERT INTO movimientos_stock (id, producto_id, usuario_id, tipo, cantidad, stock_anterior, stock_nuevo, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            ("fake_mov_id", prod_id, db_user_id, "AJUSTE", 10, 0, 10, "2026-06-11T12:00:00Z")
        )
        conn.commit()

    # Attempt to delete -> should fail with 400 PRODUCT_HAS_HISTORY
    resp = client.delete(f"/api/productos/{prod_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "PRODUCT_HAS_HISTORY"

    # Clean up fake movement and delete product
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM movimientos_stock WHERE producto_id = ?;", (prod_id,))
        conn.commit()

    # Delete should now succeed
    resp = client.delete(f"/api/productos/{prod_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200


# --- ACCESOS RÁPIDOS TESTS ---

def test_crud_accesos_rapidos(admin_token, cashier_token):
    # Pre-requisite: Category and Product
    resp_cat = client.post("/api/categorias", json={"nombre": "Kiosco Rapido"}, headers={"Authorization": f"Bearer {admin_token}"})
    cat_id = resp_cat.json()["id"]

    resp_prod = client.post(
        "/api/productos",
        json={
            "nombre": "Alfajor Guaymallen",
            "categoria_id": cat_id,
            "precio_venta_centavos": 8000,
            "stock_actual": 100,
            "unidad_medida": "UNIDAD"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    prod_id = resp_prod.json()["id"]

    # 1. Create quick access
    resp = client.post(
        "/api/accesos-rapidos",
        json={"producto_id": prod_id, "etiqueta": "Guaymallen", "orden": 1, "activo": 1},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 201
    ar = resp.json()
    assert ar["etiqueta"] == "Guaymallen"
    assert ar["orden"] == 1
    ar_id = ar["id"]

    # 2. Get quick accesses
    resp = client.get("/api/accesos-rapidos", headers={"Authorization": f"Bearer {cashier_token}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    # 3. Create another with duplicate order -> should fail with 409
    resp_prod2 = client.post(
        "/api/productos",
        json={
            "nombre": "Alfajor Jorgito",
            "categoria_id": cat_id,
            "precio_venta_centavos": 12000,
            "stock_actual": 50,
            "unidad_medida": "UNIDAD"
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    prod_id2 = resp_prod2.json()["id"]

    resp = client.post(
        "/api/accesos-rapidos",
        json={"producto_id": prod_id2, "etiqueta": "Jorgito", "orden": 1, "activo": 1},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "ORDER_ALREADY_TAKEN"

    # 4. Update order to unused one
    resp = client.put(
        f"/api/accesos-rapidos/{ar_id}",
        json={"producto_id": prod_id, "etiqueta": "Guaymallen Triple", "orden": 5, "activo": 1},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["etiqueta"] == "Guaymallen Triple"
    assert resp.json()["orden"] == 5

    # 5. Delete quick access
    resp = client.delete(f"/api/accesos-rapidos/{ar_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    
    # Cleanup products
    client.delete(f"/api/productos/{prod_id}", headers={"Authorization": f"Bearer {admin_token}"})
    client.delete(f"/api/productos/{prod_id2}", headers={"Authorization": f"Bearer {admin_token}"})
    client.delete(f"/api/categorias/{cat_id}", headers={"Authorization": f"Bearer {admin_token}"})
