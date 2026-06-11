import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import sqlite3

from app.core.config import settings
from app.core.database import init_db, get_db
from app.core.errors import (
    KioskException,
    kiosk_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.catalog import (
    categorias_router,
    marcas_router,
    proveedores_router,
    productos_router,
    accesos_rapidos_router,
)
from app.routers.caja import (
    cajas_router,
    movimientos_caja_router,
)
from app.routers.ventas import router as ventas_router

# Setup basic logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize the database
    logger.info("Starting up Kiosk Billing & Cash POS backend...")
    try:
        init_db()
    except Exception as e:
        logger.critical(f"Failed to initialize database: {e}", exc_info=True)
        raise e
    yield
    # Shutdown: Perform cleanups if any
    logger.info("Shutting down Kiosk Billing & Cash POS backend...")

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Exception Handlers
app.add_exception_handler(KioskException, kiosk_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Register Routers
app.include_router(auth_router, prefix=f"{settings.API_PREFIX}/auth")
app.include_router(users_router, prefix=f"{settings.API_PREFIX}/users")
app.include_router(users_router, prefix=f"{settings.API_PREFIX}/usuarios")
app.include_router(categorias_router, prefix=f"{settings.API_PREFIX}/categorias")
app.include_router(marcas_router, prefix=f"{settings.API_PREFIX}/marcas")
app.include_router(proveedores_router, prefix=f"{settings.API_PREFIX}/proveedores")
app.include_router(productos_router, prefix=f"{settings.API_PREFIX}/productos")
app.include_router(accesos_rapidos_router, prefix=f"{settings.API_PREFIX}/accesos-rapidos")
app.include_router(cajas_router, prefix=f"{settings.API_PREFIX}/cajas")
app.include_router(movimientos_caja_router, prefix=f"{settings.API_PREFIX}/movimientos-caja")
app.include_router(ventas_router, prefix=f"{settings.API_PREFIX}/ventas")

# Serve static files and redirect root
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
def read_root():
    return RedirectResponse(url="/static/index.html")

@app.get("/api/health", status_code=status.HTTP_200_OK)

def health_check(db: sqlite3.Connection = Depends(get_db)):
    """
    Checks the health of the application and the connection to the database.
    Verifies that sqlite3 is properly configured with requested PRAGMAs.
    """
    try:
        # Check database connection and verify PRAGMAs
        journal_mode = db.execute("PRAGMA journal_mode;").fetchone()[0]
        foreign_keys = db.execute("PRAGMA foreign_keys;").fetchone()[0]
        busy_timeout = db.execute("PRAGMA busy_timeout;").fetchone()[0]
        
        # Verify the database contains the required tables
        cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row["name"] for row in cursor.fetchall()]
        
        db_status = "connected"
        if not tables:
            db_status = "connected_but_no_tables"
            
        return {
            "status": "ok",
            "database": {
                "status": db_status,
                "path": settings.DB_URL,
                "tables_count": len(tables),
                "pragmas": {
                    "journal_mode": journal_mode,
                    "foreign_keys": "on" if foreign_keys == 1 else "off",
                    "busy_timeout_ms": busy_timeout
                }
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise KioskException(
            code="DATABASE_CONNECTION_ERROR",
            message=f"No se pudo conectar a la base de datos: {str(e)}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )
