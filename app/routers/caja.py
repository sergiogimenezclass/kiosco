from fastapi import APIRouter, Depends, status, Query
import sqlite3
from typing import List, Optional

from app.core.database import get_db
from app.schemas.caja import (
    CajaApertura,
    CajaCierre,
    CajaResponse,
    MovimientoCajaCreate,
    MovimientoCajaResponse
)
from app.services.caja import CajaService
from app.services.auth import get_current_user, RoleChecker

# --- CAJAS ROUTER ---
cajas_router = APIRouter()

@cajas_router.get("/actual", response_model=Optional[CajaResponse])
def get_actual_caja(
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Returns the currently active (open) cash register, or null if there is no open register.
    """
    return CajaService.get_active_caja(db)

@cajas_router.post("/apertura", response_model=CajaResponse, status_code=status.HTTP_201_CREATED)
def abrir_caja(
    apertura_in: CajaApertura,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(RoleChecker(["CAJERO", "SUPERVISOR", "ADMINISTRADOR"]))
):
    """
    Opens a new cash register with an initial amount in cents.
    Fails if a cash register is already open.
    """
    return CajaService.apertura(db, current_user["id"], apertura_in)

@cajas_router.post("/cierre", response_model=CajaResponse)
def cerrar_caja(
    cierre_in: CajaCierre,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(RoleChecker(["SUPERVISOR", "ADMINISTRADOR"]))
):
    """
    Closes the currently active cash register (blind closing).
    Calculates expected amount and discrepancy.
    """
    return CajaService.cierre(db, current_user["id"], cierre_in)

@cajas_router.post("/{id}/reabrir", response_model=CajaResponse)
def reabrir_caja(
    id: str,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(RoleChecker(["ADMINISTRADOR"]))
):
    """
    Reopens a previously closed cash register.
    Fails if there is another cash register currently open.
    """
    return CajaService.reabrir(db, id)

@cajas_router.get("/historial", response_model=List[CajaResponse])
def get_historial(
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(RoleChecker(["SUPERVISOR", "ADMINISTRADOR"]))
):
    """
    Lists all cash registers (open and closed) in reverse chronological order.
    """
    return CajaService.get_historial(db)


# --- MOVIMIENTOS DE CAJA ROUTER ---
movimientos_caja_router = APIRouter()

@movimientos_caja_router.post("", response_model=MovimientoCajaResponse, status_code=status.HTTP_201_CREATED)
def registrar_movimiento(
    mov_in: MovimientoCajaCreate,
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(RoleChecker(["SUPERVISOR", "ADMINISTRADOR"]))
):
    """
    Registers a new movement (deposit or withdrawal) for the active cash register.
    """
    return CajaService.registrar_movimiento(db, current_user["id"], mov_in)

@movimientos_caja_router.get("", response_model=List[MovimientoCajaResponse])
def list_movimientos(
    caja_id: Optional[str] = Query(None, description="Filtrar movimientos por ID de caja específica"),
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(RoleChecker(["SUPERVISOR", "ADMINISTRADOR"]))
):
    """
    Lists movements. If caja_id is provided, returns movements for that register.
    Otherwise, returns all registered movements across all registers.
    """
    if caja_id:
        CajaService.get_caja_by_id(db, caja_id)
        from app.repositories.caja import CajaRepository
        return CajaRepository.get_movimientos_by_caja_id(db, caja_id)
    return CajaService.get_all_movimientos(db)
