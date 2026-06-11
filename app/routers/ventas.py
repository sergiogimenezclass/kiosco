from fastapi import APIRouter, Depends, status
import sqlite3

from app.core.database import get_db
from app.schemas.ventas import VentaCreate, VentaResponse
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
