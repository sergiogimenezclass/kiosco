import os
import sys

# Add project root directory to path to allow absolute imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.database import init_db, get_db_conn
from app.core.errors import KioskException

def test_initialization():
    print("Testing DB initialization...")
    # Delete DB if it exists to test clean init
    if os.path.exists(settings.DB_URL):
        print(f"Removing existing test DB at {settings.DB_URL}...")
        os.remove(settings.DB_URL)
        
    # Run init
    init_db()
    
    # Check if DB file was created
    if not os.path.exists(settings.DB_URL):
        print("FAIL: DB file was not created!")
        sys.exit(1)
        
    print("SUCCESS: DB file created.")

def test_pragmas_and_tables():
    print("Testing SQLite PRAGMAs and tables...")
    with get_db_conn() as conn:
        # Check journal_mode
        journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        print(f"PRAGMA journal_mode = {journal_mode}")
        if journal_mode.lower() != "wal":
            print("FAIL: journal_mode is not WAL!")
            sys.exit(1)
            
        # Check foreign_keys
        foreign_keys = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        print(f"PRAGMA foreign_keys = {foreign_keys}")
        if foreign_keys != 1:
            print("FAIL: foreign_keys are not enabled!")
            sys.exit(1)
            
        # Check busy_timeout
        busy_timeout = conn.execute("PRAGMA busy_timeout;").fetchone()[0]
        print(f"PRAGMA busy_timeout = {busy_timeout}")
        if busy_timeout != 20000:
            print("FAIL: busy_timeout is not 20000 ms!")
            sys.exit(1)
            
        # Check tables exist
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row["name"] for row in cursor.fetchall()]
        print(f"Tables created: {', '.join(tables)}")
        
        required_tables = ["usuarios", "cajas", "movimientos_caja", "categorias", "marcas", "proveedores", "productos", "codigos_barras", "accesos_rapidos", "ventas", "venta_detalles", "devoluciones", "anulaciones", "movimientos_stock", "configuracion"]
        for table in required_tables:
            if table not in tables:
                print(f"FAIL: Table '{table}' was not created!")
                sys.exit(1)
                
        # Check configuration seed
        config_val = conn.execute("SELECT valor FROM configuracion WHERE clave = 'descuento_maximo_porcentaje';").fetchone()
        if not config_val or config_val["valor"] != "50":
            print("FAIL: Configuration seed is incorrect or missing!")
            sys.exit(1)
            
        print("SUCCESS: PRAGMAs and tables verified successfully.")

def test_error_handling():
    print("Testing Exception Structure...")
    try:
        raise KioskException(
            code="TEST_ERROR",
            message="Este es un error de prueba",
            status_code=400,
            details={"field": "valor"}
        )
    except KioskException as e:
        print(f"Caught KioskException: code={e.code}, message={e.message}, details={e.details}")
        assert e.code == "TEST_ERROR"
        assert e.details == {"field": "valor"}
        print("SUCCESS: Exception structure verified.")

if __name__ == "__main__":
    print("--- START DATABASE AND BASE TECH VERIFICATION ---")
    test_initialization()
    test_pragmas_and_tables()
    test_error_handling()
    print("--- ALL VERIFICATIONS PASSED ---")
