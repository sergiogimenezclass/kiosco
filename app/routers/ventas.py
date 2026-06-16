from fastapi import APIRouter, Depends, status, Query
import sqlite3
from typing import List, Optional

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

@router.get("", response_model=List[VentaResponse])
def listar_ventas(
    desde: Optional[str] = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    hasta: Optional[str] = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    caja_id: Optional[str] = Query(None, description="Filtrar por caja ID"),
    usuario_id: Optional[str] = Query(None, description="Filtrar por cajero usuario ID"),
    estado: Optional[str] = Query(None, description="Filtrar por estado de la venta (COMPLETADA, ANULADA, DEVUELTA)"),
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(RoleChecker(["SUPERVISOR", "ADMINISTRADOR"]))
):
    """
    Lista las ventas del sistema según filtros de fecha, caja, usuario y estado.
    Solo disponible para SUPERVISOR y ADMINISTRADOR.
    """
    return VentasService.listar_ventas(db, desde, hasta, caja_id, usuario_id, estado)

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

