import os
import sys
import pytest
import sqlite3
import threading
import queue

# Add project root directory to path to allow absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
settings.DB_PATH = "test_kiosco.db"

from app.core.database import init_db, get_db_conn
from app.core.errors import KioskException
from app.services.caja import CajaService
from app.services.catalog import CategoriaService, ProductoService
from app.services.ventas import VentasService

from app.schemas.caja import CajaApertura
from app.schemas.catalog import CategoriaCreate, ProductoCreate
from app.schemas.ventas import VentaCreate, VentaDetalleCreate, MetodoPago

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

def test_concurrent_sales_same_product():
    """
    Test that concurrent sales on the same product are serialized correctly,
    do not lead to race conditions (e.g. stock underflow below zero), and
    respect transactional boundaries.
    """
    # 1. Configurar datos iniciales
    with get_db_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE username = 'admin';")
        admin_id = cursor.fetchone()["id"]
        
        # Cargar categorías y producto con stock = 5
        cat = CategoriaService.create_category(conn, CategoriaCreate(nombre="Bebidas Concurrente"))
        prod = ProductoService.create_product(conn, ProductoCreate(
            nombre="Lata de Gaseosa",
            categoria_id=cat["id"],
            precio_venta_centavos=1500, # $15.00
            stock_actual=5, # Stock inicial de 5
            stock_minimo=1,
            unidad_medida="UNIDAD"
        ))
        prod_id = prod["id"]
        
        # Abrir la caja
        caja = CajaService.apertura(conn, admin_id, CajaApertura(monto_inicial_centavos=5000))
        caja_id = caja["id"]

    # 2. Vamos a lanzar 7 hilos concurrentes para vender 1 gaseosa cada uno.
    # Como el stock inicial es 5, exactamente 5 ventas deben tener éxito y 2 deben fallar por INSUFFICIENT_STOCK.
    results_queue = queue.Queue()
    
    def worker_sale():
        # Cada hilo debe abrir su propia conexión independiente a la base de datos
        # para simular un proceso/request concurrente real
        try:
            with get_db_conn() as thread_conn:
                venta_payload = VentaCreate(
                    caja_id=caja_id,
                    metodo_pago=MetodoPago.EFECTIVO,
                    subtotal_centavos=1500,
                    descuento_items_centavos=0,
                    descuento_venta_centavos=0,
                    total_centavos=1500,
                    monto_recibido_centavos=1500,
                    vuelto_centavos=0,
                    detalles=[
                        VentaDetalleCreate(producto_id=prod_id, cantidad=1, precio_unitario_centavos=1500, descuento_centavos=0)
                    ]
                )
                VentasService.registrar_venta(thread_conn, admin_id, venta_payload)
                results_queue.put(("SUCCESS", None))
        except KioskException as e:
            results_queue.put(("FAILED_KIOSK_ERR", e.code))
        except Exception as e:
            results_queue.put(("FAILED_OTHER_ERR", str(e)))

    threads = []
    num_threads = 7
    for _ in range(num_threads):
        t = threading.Thread(target=worker_sale)
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    # Analizar resultados de los hilos
    success_count = 0
    insufficient_stock_count = 0
    other_errors = []
    
    while not results_queue.empty():
        status, detail = results_queue.get()
        if status == "SUCCESS":
            success_count += 1
        elif status == "FAILED_KIOSK_ERR" and detail == "INSUFFICIENT_STOCK":
            insufficient_stock_count += 1
        else:
            other_errors.append(detail)
            
    # Validaciones críticas
    assert len(other_errors) == 0, f"Ocurrieron errores inesperados en los hilos: {other_errors}"
    assert success_count == 5, f"Se esperaban 5 ventas exitosas, pero hubo {success_count}"
    assert insufficient_stock_count == 2, f"Se esperaban 2 ventas fallidas por falta de stock, pero hubo {insufficient_stock_count}"
    
    # Validar consistencia final en base de datos
    with get_db_conn() as conn:
        prod_final = ProductoService.get_product(conn, prod_id)
        assert prod_final["stock_actual"] == 0, f"El stock final debería ser 0, pero es {prod_final['stock_actual']}"
        
        # Cantidad de ventas guardadas en DB
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM ventas WHERE caja_id = ? AND estado = 'COMPLETADA';", (caja_id,))
        ventas_db_count = cursor.fetchone()[0]
        assert ventas_db_count == 5, f"Se esperaban 5 ventas completadas en DB, pero hay {ventas_db_count}"
        
        # Cantidad de movimientos de stock en DB
        cursor.execute("SELECT SUM(cantidad) FROM movimientos_stock WHERE producto_id = ?;", (prod_id,))
        sum_movs = cursor.fetchone()[0]
        assert sum_movs == -5, f"La suma de movimientos de stock debería ser -5, pero es {sum_movs}"
