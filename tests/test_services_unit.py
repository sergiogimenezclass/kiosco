import os
import sys
import pytest
import sqlite3
import uuid
import datetime

# Add project root directory to path to allow absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
settings.DB_PATH = "test_kiosco.db"

from app.core.database import init_db, get_db_conn
from app.core.errors import KioskException
from app.services.auth import AuthService
from app.services.caja import CajaService
from app.services.catalog import CategoriaService, ProductoService
from app.services.ventas import VentasService
from app.services.reports import ReportsService

from app.schemas.caja import CajaApertura, CajaCierre, MovimientoCajaCreate, MovimientoCajaTipo
from app.schemas.catalog import CategoriaCreate, ProductoCreate
from app.schemas.ventas import VentaCreate, VentaDetalleCreate, AnulacionCreate, DevolucionCreate, MetodoPago

@pytest.fixture(scope="function", autouse=True)
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

def test_auth_service_unit():
    with get_db_conn() as conn:
        # Test success using seeded admin credentials
        user = AuthService.authenticate_user(conn, "admin", "admin123")
        assert user["username"] == "admin"
        assert user["rol"] == "ADMINISTRADOR"
        assert user["activo"] == 1
        
        # Test failure: incorrect password
        with pytest.raises(KioskException) as excinfo:
            AuthService.authenticate_user(conn, "admin", "wrong_password")
        assert excinfo.value.code == "UNAUTHORIZED"
        assert excinfo.value.status_code == 401
        
        # Test failure: non-existent user
        with pytest.raises(KioskException) as excinfo:
            AuthService.authenticate_user(conn, "nonexistent", "somepassword")
        assert excinfo.value.code == "UNAUTHORIZED"
        
        # Test failure: inactive user
        # 1. Crear un usuario inactivo usando el hash del admin (que es admin123)
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM usuarios WHERE username = 'admin';")
        admin_hash = cursor.fetchone()["password_hash"]
        cursor.execute(
            """
            INSERT INTO usuarios (id, nombre, username, password_hash, rol, activo, created_at)
            VALUES ('inactive_user', 'Inactivo', 'inactive', ?, 'CAJERO', 0, '2026-06-11T00:00:00');
            """,
            (admin_hash,)
        )
        conn.commit()
        
        with pytest.raises(KioskException) as excinfo:
            AuthService.authenticate_user(conn, "inactive", "admin123")
        assert excinfo.value.code == "USER_INACTIVE"

def test_caja_service_unit():
    with get_db_conn() as conn:
        # Get active user id
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE username = 'admin';")
        admin_id = cursor.fetchone()["id"]
        
        # Apertura de caja exitosa
        apertura_payload = CajaApertura(monto_inicial_centavos=15000)
        caja = CajaService.apertura(conn, admin_id, apertura_payload)
        assert caja["estado"] == "ABIERTA"
        assert caja["monto_inicial_centavos"] == 15000
        
        # Intentar doble apertura -> falla
        with pytest.raises(KioskException) as excinfo:
            CajaService.apertura(conn, admin_id, apertura_payload)
        assert excinfo.value.code == "ACTIVE_CASH_REGISTER_EXISTS"
        assert excinfo.value.status_code == 400
        
        # Registrar movimiento de caja: INGRESO
        mov_ingreso = MovimientoCajaCreate(tipo=MovimientoCajaTipo.INGRESO, monto_centavos=5000, motivo="Sencillo inicial")
        mov = CajaService.registrar_movimiento(conn, admin_id, mov_ingreso)
        assert mov["tipo"] == "INGRESO"
        assert mov["monto_centavos"] == 5000
        
        # Registrar movimiento de caja: RETIRO
        mov_retiro = MovimientoCajaCreate(tipo=MovimientoCajaTipo.RETIRO, monto_centavos=2000, motivo="Pago flete")
        mov = CajaService.registrar_movimiento(conn, admin_id, mov_retiro)
        assert mov["tipo"] == "RETIRO"
        assert mov["monto_centavos"] == 2000
        
        # Cierre de caja
        # Esperado: 15000 (inicial) + 5000 (ingreso) - 2000 (retiro) + 0 (ventas efectivo) = 18000 centavos.
        # Declaramos 17500 (desviación = -500 centavos).
        cierre_payload = CajaCierre(monto_declarado_centavos=17500)
        caja_cerrada = CajaService.cierre(conn, admin_id, cierre_payload)
        assert caja_cerrada["estado"] == "CERRADA"
        assert caja_cerrada["monto_esperado_centavos"] == 18000
        assert caja_cerrada["monto_declarado_centavos"] == 17500
        assert caja_cerrada["desviacion_centavos"] == -500

def test_catalog_service_unit():
    with get_db_conn() as conn:
        # Crear Categoría
        cat_create = CategoriaCreate(nombre="Bebidas")
        cat = CategoriaService.create_category(conn, cat_create)
        assert cat["nombre"] == "Bebidas"
        assert "id" in cat
        cat_id = cat["id"]
        
        # Crear Producto
        prod_create = ProductoCreate(
            nombre="Coca Cola 500ml",
            categoria_id=cat_id,
            precio_venta_centavos=12000,
            stock_actual=24,
            stock_minimo=6,
            unidad_medida="UNIDAD",
            codigo_barras="77900704"
        )
        prod = ProductoService.create_product(conn, prod_create)
        assert prod["nombre"] == "Coca Cola 500ml"
        assert prod["stock_actual"] == 24
        assert prod["precio_venta_centavos"] == 12000
        
        # Validaciones de producto unitarias (Validadas en la inicialización por Pydantic)
        from pydantic import ValidationError
        # 1. Precio negativo -> debe lanzar ValidationError de Pydantic
        with pytest.raises(ValidationError):
            ProductoCreate(
                nombre="Prod Invalido 1",
                categoria_id=cat_id,
                precio_venta_centavos=-100,
                stock_actual=10,
                stock_minimo=2,
                unidad_medida="UNIDAD"
            )
        
        # 2. Stock negativo -> debe lanzar ValidationError de Pydantic
        with pytest.raises(ValidationError):
            ProductoCreate(
                nombre="Prod Invalido 2",
                categoria_id=cat_id,
                precio_venta_centavos=1000,
                stock_actual=-5,
                stock_minimo=2,
                unidad_medida="UNIDAD"
            )

def test_ventas_service_unit():
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE username = 'admin';")
        admin_id = cursor.fetchone()["id"]
        
        # Crear categoria y producto de prueba
        cat = CategoriaService.create_category(conn, CategoriaCreate(nombre="Golosinas"))
        prod = ProductoService.create_product(conn, ProductoCreate(
            nombre="Chicle Beldent",
            categoria_id=cat["id"],
            precio_venta_centavos=1000, # $10.00
            stock_actual=50,
            stock_minimo=5,
            unidad_medida="UNIDAD"
        ))
        
        # 1. Intentar registrar venta sin caja abierta -> falla
        venta_payload = VentaCreate(
            caja_id="caja_falsa",
            metodo_pago=MetodoPago.EFECTIVO,
            subtotal_centavos=1000,
            descuento_items_centavos=0,
            descuento_venta_centavos=0,
            total_centavos=1000,
            monto_recibido_centavos=1000,
            vuelto_centavos=0,
            detalles=[
                VentaDetalleCreate(producto_id=prod["id"], cantidad=1, precio_unitario_centavos=1000, descuento_centavos=0)
            ]
        )
        with pytest.raises(KioskException) as excinfo:
            VentasService.registrar_venta(conn, admin_id, venta_payload)
        assert excinfo.value.code == "CASH_REGISTER_CLOSED"
        
        # 2. Abrir caja
        caja = CajaService.apertura(conn, admin_id, CajaApertura(monto_inicial_centavos=10000))
        venta_payload.caja_id = caja["id"]
        
        # 3. Registrar venta de 2 chicles (Total $20.00)
        venta_payload.subtotal_centavos = 2000
        venta_payload.total_centavos = 2000
        venta_payload.monto_recibido_centavos = 2000
        venta_payload.detalles[0].cantidad = 2
        
        venta = VentasService.registrar_venta(conn, admin_id, venta_payload)
        assert venta["estado"] == "COMPLETADA"
        assert venta["total_centavos"] == 2000
        
        # Verificar stock actualizado
        p_updated = ProductoService.get_product(conn, prod["id"])
        assert p_updated["stock_actual"] == 48 # 50 - 2
        
        # 4. Devolución de venta
        dev = VentasService.devolver_venta(conn, admin_id, venta["id"], DevolucionCreate(motivo="Cliente arrepentido"))
        assert dev["venta_id"] == venta["id"]
        assert dev["monto_devuelto_centavos"] == 2000
        
        # Verificar stock revertido
        p_reverted = ProductoService.get_product(conn, prod["id"])
        assert p_reverted["stock_actual"] == 50 # Revertido a 50
        
        # Intentar devolver una venta ya devuelta -> falla
        with pytest.raises(KioskException) as excinfo:
            VentasService.devolver_venta(conn, admin_id, venta["id"], DevolucionCreate(motivo="Repetir"))
        assert excinfo.value.code == "INVALID_SALE_STATE"
