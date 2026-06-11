import sqlite3
import uuid
import datetime
from typing import List, Dict, Any, Optional
from app.core.errors import KioskException

class StockRepository:
    @staticmethod
    def get_producto_stock_info(conn: sqlite3.Connection, prod_id: str) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor()
        cursor.execute("SELECT id, stock_actual, stock_minimo FROM productos WHERE id = ?;", (prod_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def update_stock(conn: sqlite3.Connection, prod_id: str, cantidad_delta: int) -> None:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE productos SET stock_actual = stock_actual + ?, updated_at = ? WHERE id = ?;",
                (cantidad_delta, datetime.datetime.now(datetime.timezone.utc).isoformat(), prod_id)
            )
            if cursor.rowcount == 0:
                raise KioskException(
                    code="PRODUCT_NOT_FOUND",
                    message="El producto especificado no existe",
                    status_code=404
                )
        except sqlite3.IntegrityError as e:
            if "CHECK constraint failed" in str(e) or "stock_actual" in str(e):
                raise KioskException(
                    code="INVALID_STOCK",
                    message="El ajuste solicitado resulta en un stock negativo no permitido",
                    status_code=400
                )
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al actualizar stock: {str(e)}",
                status_code=500
            )
        except sqlite3.Error as e:
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error de base de datos al actualizar stock: {str(e)}",
                status_code=500
            )

    @staticmethod
    def registrar_movimiento(
        conn: sqlite3.Connection,
        prod_id: str,
        user_id: str,
        tipo: str,
        cantidad: int,
        stock_ant: int,
        stock_nue: int,
        motivo: str,
        proveedor_id: Optional[str] = None
    ) -> Dict[str, Any]:
        cursor = conn.cursor()
        mov_id = uuid.uuid4().hex
        fecha = datetime.datetime.now(datetime.timezone.utc).isoformat()
        try:
            cursor.execute(
                """
                INSERT INTO movimientos_stock (
                    id, producto_id, usuario_id, tipo, cantidad, stock_anterior, stock_nuevo,
                    referencia_tipo, referencia_id, motivo, proveedor_id, fecha
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    mov_id,
                    prod_id,
                    user_id,
                    tipo,
                    cantidad,
                    stock_ant,
                    stock_nue,
                    tipo,
                    None,
                    motivo,
                    proveedor_id,
                    fecha
                )
            )
            return {
                "id": mov_id,
                "producto_id": prod_id,
                "usuario_id": user_id,
                "tipo": tipo,
                "cantidad": cantidad,
                "stock_anterior": stock_ant,
                "stock_nuevo": stock_nue,
                "referencia_tipo": tipo,
                "referencia_id": None,
                "motivo": motivo,
                "proveedor_id": proveedor_id,
                "fecha": fecha
            }
        except sqlite3.Error as e:
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al registrar el movimiento de stock: {str(e)}",
                status_code=500
            )

    @staticmethod
    def proveedor_existe(conn: sqlite3.Connection, prov_id: str) -> bool:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM proveedores WHERE id = ?;", (prov_id,))
        return cursor.fetchone() is not None

    @staticmethod
    def get_movimientos(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, producto_id, usuario_id, tipo, cantidad, stock_anterior, stock_nuevo,
                   referencia_tipo, referencia_id, motivo, proveedor_id, fecha
            FROM movimientos_stock
            ORDER BY fecha DESC;
            """
        )
        return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def get_stock_bajo_ids(conn: sqlite3.Connection) -> List[str]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id
            FROM productos
            WHERE stock_actual <= stock_minimo AND activo = 1;
            """
        )
        return [r["id"] for r in cursor.fetchall()]
