from fastapi import APIRouter, Depends, status
import sqlite3
from typing import List

from app.core.database import get_db
from app.services.auth import RoleChecker
from app.services.stock import StockService
from app.schemas.stock import (
    StockAjusteCreate,
    StockIngresoCreate,
    MovimientoStockResponse
)
from app.schemas.catalog import ProductoResponse

router = APIRouter()

@router.post("/ajuste", response_model=MovimientoStockResponse, status_code=status.HTTP_200_OK)
def realizar_ajuste(
    ajuste_in: StockAjusteCreate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(RoleChecker(["SUPERVISOR", "ADMINISTRADOR"]))
):
    """
    Performs stock adjustment for a product (addition or reduction).
    Validates that the resulting stock is not negative.
    Logs stock movement audit record.
    """
    return StockService.realizar_ajuste(db, current_user["id"], ajuste_in)

@router.post("/ingreso", response_model=MovimientoStockResponse, status_code=status.HTTP_200_OK)
def realizar_ingreso(
    ingreso_in: StockIngresoCreate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(RoleChecker(["SUPERVISOR", "ADMINISTRADOR"]))
):
    """
    Registers a stock intake from a provider.
    Validates that provider exists and quantity > 0.
    Logs stock movement audit record.
    """
    return StockService.realizar_ingreso(db, current_user["id"], ingreso_in)

@router.get("/movimientos", response_model=List[MovimientoStockResponse], status_code=status.HTTP_200_OK)
def obtener_movimientos(
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(RoleChecker(["SUPERVISOR", "ADMINISTRADOR"]))
):
    """
    Retrieves the chronological list of stock movements (newest first).
    """
    return StockService.obtener_movimientos(db)

@router.get("/bajo-minimo", response_model=List[ProductoResponse], status_code=status.HTTP_200_OK)
def obtener_stock_bajo(
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(RoleChecker(["SUPERVISOR", "ADMINISTRADOR"]))
):
    """
    Lists products whose current stock is less than or equal to their configured minimum.
    """
    return StockService.obtener_stock_bajo(db)
