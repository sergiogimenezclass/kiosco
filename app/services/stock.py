import sqlite3
from typing import List, Dict, Any
from app.core.errors import KioskException
from app.repositories.stock import StockRepository
from app.repositories.catalog import ProductoRepository
from app.schemas.stock import StockAjusteCreate, StockIngresoCreate

class StockService:
    @staticmethod
    def realizar_ajuste(db: sqlite3.Connection, usuario_id: str, ajuste: StockAjusteCreate) -> Dict[str, Any]:
        # Validar que motivo no esté vacío
        if not ajuste.motivo.strip():
            raise KioskException(
                code="INVALID_MOTIVE",
                message="El motivo del ajuste de stock es obligatorio y no puede estar vacío",
                status_code=400
            )

        # Validar existencia del producto
        prod = ProductoRepository.get_by_id(db, ajuste.producto_id)
        if not prod:
            raise KioskException(
                code="PRODUCT_NOT_FOUND",
                message=f"El producto con ID '{ajuste.producto_id}' no existe en el catálogo",
                status_code=404
            )

        stock_anterior = prod["stock_actual"]
        stock_nuevo = stock_anterior + ajuste.cantidad_delta

        # La actualización lanzará KioskException(code="INVALID_STOCK") si el stock final resulta negativo
        StockRepository.update_stock(db, ajuste.producto_id, ajuste.cantidad_delta)

        movimiento = StockRepository.registrar_movimiento(
            conn=db,
            prod_id=ajuste.producto_id,
            user_id=usuario_id,
            tipo="AJUSTE",
            cantidad=ajuste.cantidad_delta,
            stock_ant=stock_anterior,
            stock_nue=stock_nuevo,
            motivo=ajuste.motivo.strip()
        )
        return movimiento

    @staticmethod
    def realizar_ingreso(db: sqlite3.Connection, usuario_id: str, ingreso: StockIngresoCreate) -> Dict[str, Any]:
        # Validar que motivo no esté vacío
        if not ingreso.motivo.strip():
            raise KioskException(
                code="INVALID_MOTIVE",
                message="El motivo del ingreso de stock es obligatorio y no puede estar vacío",
                status_code=400
            )

        # Validar que cantidad sea mayor a cero
        if ingreso.cantidad <= 0:
            raise KioskException(
                code="INVALID_QUANTITY",
                message="La cantidad a ingresar debe ser mayor a cero",
                status_code=400
            )

        # Validar existencia del producto
        prod = ProductoRepository.get_by_id(db, ingreso.producto_id)
        if not prod:
            raise KioskException(
                code="PRODUCT_NOT_FOUND",
                message=f"El producto con ID '{ingreso.producto_id}' no existe en el catálogo",
                status_code=404
            )

        # Validar existencia del proveedor
        if not StockRepository.proveedor_existe(db, ingreso.proveedor_id):
            raise KioskException(
                code="PROVIDER_NOT_FOUND",
                message=f"El proveedor con ID '{ingreso.proveedor_id}' no existe en la base de datos",
                status_code=400
            )

        stock_anterior = prod["stock_actual"]
        stock_nuevo = stock_anterior + ingreso.cantidad

        StockRepository.update_stock(db, ingreso.producto_id, ingreso.cantidad)

        movimiento = StockRepository.registrar_movimiento(
            conn=db,
            prod_id=ingreso.producto_id,
            user_id=usuario_id,
            tipo="INGRESO",
            cantidad=ingreso.cantidad,
            stock_ant=stock_anterior,
            stock_nue=stock_nuevo,
            motivo=ingreso.motivo.strip(),
            proveedor_id=ingreso.proveedor_id
        )
        return movimiento

    @staticmethod
    def obtener_movimientos(db: sqlite3.Connection) -> List[Dict[str, Any]]:
        return StockRepository.get_movimientos(db)

    @staticmethod
    def obtener_stock_bajo(db: sqlite3.Connection) -> List[Dict[str, Any]]:
        prod_ids = StockRepository.get_stock_bajo_ids(db)
        productos = []
        for p_id in prod_ids:
            prod = ProductoRepository.get_by_id(db, p_id)
            if prod:
                productos.append(prod)
        return productos
