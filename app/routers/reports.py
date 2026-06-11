from fastapi import APIRouter, Depends, Query, Response, status
import sqlite3
from typing import List, Optional

from app.core.database import get_db
from app.services.auth import RoleChecker
from app.services.reports import ReportsService
from app.schemas.reports import VentasDiariasResponse, CajaReportItem, ProductoRankingItem, StockBajoReportItem

router = APIRouter()

@router.get("/ventas-diarias", response_model=VentasDiariasResponse, status_code=status.HTTP_200_OK)
def obtener_ventas_diarias(
    desde: Optional[str] = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    hasta: Optional[str] = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(RoleChecker(["SUPERVISOR", "ADMINISTRADOR"]))
):
    """
    Obtiene el reporte consolidado de ventas diarias.
    """
    return ReportsService.get_ventas_diarias(db, desde, hasta)

@router.get("/cajas", response_model=List[CajaReportItem], status_code=status.HTTP_200_OK)
def obtener_cajas(
    desde: Optional[str] = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    hasta: Optional[str] = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(RoleChecker(["SUPERVISOR", "ADMINISTRADOR"]))
):
    """
    Obtiene el historial de cajas con ingresos, retiros y ventas.
    """
    return ReportsService.get_cajas(db, desde, hasta)

@router.get("/ranking-productos", response_model=List[ProductoRankingItem], status_code=status.HTTP_200_OK)
def obtener_ranking_productos(
    ordenar_por: str = Query("cantidad", description="Ordenar por 'cantidad' o 'monto'"),
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(RoleChecker(["SUPERVISOR", "ADMINISTRADOR"]))
):
    """
    Obtiene el ranking de los productos más vendidos.
    """
    return ReportsService.get_ranking_productos(db, ordenar_por)

@router.get("/stock-bajo", response_model=List[StockBajoReportItem], status_code=status.HTTP_200_OK)
def obtener_stock_bajo(
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(RoleChecker(["SUPERVISOR", "ADMINISTRADOR"]))
):
    """
    Obtiene los productos con stock igual o inferior al mínimo configurado.
    """
    return ReportsService.get_stock_bajo(db)

@router.get("/{tipo}/export", status_code=status.HTTP_200_OK)
def exportar_reporte(
    tipo: str,
    format: str = Query(..., description="Formato de exportación: 'csv', 'xlsx' o 'pdf'"),
    desde: Optional[str] = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    hasta: Optional[str] = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    ordenar_por: Optional[str] = Query("cantidad", description="Ordenar por 'cantidad' o 'monto' (solo ranking)"),
    db: sqlite3.Connection = Depends(get_db),
    current_user: dict = Depends(RoleChecker(["SUPERVISOR", "ADMINISTRADOR"]))
):
    """
    Exporta un reporte en formato CSV, Excel (xlsx) o PDF.
    """
    content, filename, media_type = ReportsService.export_report(
        db, tipo, format, desde, hasta, ordenar_por
    )
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
