from fastapi import APIRouter, Depends, status
import sqlite3

from app.core.database import get_db
from app.schemas.ventas import (
    VentaCreate,
    VentaResponse,
    AnulacionCreate,
    AnulacionResponse,
    DevolucionCreate,
    DevolucionResponse
)
from app.services.ventas import VentasService
from app.services.auth import RoleChecker

router = APIRouter()

@router.post("", response_model=VentaResponse, status_code=status.HTTP_201_CREATED)
def registrar_venta(
    venta_in: VentaCreate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(RoleChecker(["CAJERO", "SUPERVISOR", "ADMINISTRADOR"]))
):
    """
    Registers a new POS sale, decrements product stock, logs stock movement records,
    and returns the saved sale header with details. Runs inside an atomic transaction.
    """
    return VentasService.registrar_venta(db, current_user["id"], venta_in)

@router.post("/{id}/anular", response_model=AnulacionResponse, status_code=status.HTTP_200_OK)
def anular_venta(
    id: str,
    anulacion_in: AnulacionCreate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(RoleChecker(["SUPERVISOR", "ADMINISTRADOR"]))
):
    """
    Annuls a sale if it was made on the same calendar day (UTC).
    Restores product stock and logs stock movement records.
    Runs inside an atomic transaction.
    """
    return VentasService.anular_venta(db, current_user["id"], id, anulacion_in)

@router.post("/{id}/devolver", response_model=DevolucionResponse, status_code=status.HTTP_200_OK)
def devolver_venta(
    id: str,
    devolucion_in: DevolucionCreate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(RoleChecker(["SUPERVISOR", "ADMINISTRADOR"]))
):
    """
    Fully refunds a sale.
    Restores product stock and logs stock movement records.
    Runs inside an atomic transaction.
    """
    return VentasService.devolver_venta(db, current_user["id"], id, devolucion_in)

