import sqlite3
import uuid
import datetime
from typing import Optional, List, Dict, Any
from app.core.errors import KioskException
from app.schemas.ventas import VentaCreate, VentaDetalleCreate

class VentasRepository:
    @staticmethod
    def create_venta(
        conn: sqlite3.Connection,
        venta: VentaCreate,
        usuario_id: str,
        id_venta: str,
        fecha: str
    ) -> Dict[str, Any]:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO ventas (
                    id, caja_id, usuario_id, estado, metodo_pago, subtotal_centavos,
                    descuento_items_centavos, descuento_venta_centavos, total_centavos,
                    monto_recibido_centavos, vuelto_centavos, fecha
                ) VALUES (?, ?, ?, 'COMPLETADA', ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    id_venta,
                    venta.caja_id,
                    usuario_id,
                    venta.metodo_pago.value,
                    venta.subtotal_centavos,
                    venta.descuento_items_centavos,
                    venta.descuento_venta_centavos,
                    venta.total_centavos,
                    venta.monto_recibido_centavos,
                    venta.vuelto_centavos,
                    fecha
                )
            )
            return {
                "id": id_venta,
                "caja_id": venta.caja_id,
                "usuario_id": usuario_id,
                "estado": "COMPLETADA",
                "metodo_pago": venta.metodo_pago.value,
                "subtotal_centavos": venta.subtotal_centavos,
                "descuento_items_centavos": venta.descuento_items_centavos,
                "descuento_venta_centavos": venta.descuento_venta_centavos,
                "total_centavos": venta.total_centavos,
                "monto_recibido_centavos": venta.monto_recibido_centavos,
                "vuelto_centavos": venta.vuelto_centavos,
                "fecha": fecha
            }
        except sqlite3.Error as e:
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al registrar la cabecera de venta: {str(e)}",
                status_code=500
            )

    @staticmethod
    def create_venta_detalle(
        conn: sqlite3.Connection,
        detalle: VentaDetalleCreate,
        venta_id: str,
        id_detalle: str,
        nombre_snap: str,
        unidad_snap: str
    ) -> Dict[str, Any]:
        cursor = conn.cursor()
        subtotal = detalle.precio_unitario_centavos * detalle.cantidad
        # El descuento en detalle es el descuento sobre la línea completa
        total_linea = subtotal - detalle.descuento_centavos
        try:
            cursor.execute(
                """
                INSERT INTO venta_detalles (
                    id, venta_id, producto_id, nombre_producto_snapshot, cantidad,
                    unidad_medida_snapshot, precio_unitario_centavos, descuento_centavos,
                    subtotal_centavos, total_linea_centavos
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    id_detalle,
                    venta_id,
                    detalle.producto_id,
                    nombre_snap,
                    detalle.cantidad,
                    unidad_snap,
                    detalle.precio_unitario_centavos,
                    detalle.descuento_centavos,
                    subtotal,
                    total_linea
                )
            )
            return {
                "id": id_detalle,
                "venta_id": venta_id,
                "producto_id": detalle.producto_id,
                "nombre_producto_snapshot": nombre_snap,
                "cantidad": detalle.cantidad,
                "unidad_medida_snapshot": unidad_snap,
                "precio_unitario_centavos": detalle.precio_unitario_centavos,
                "descuento_centavos": detalle.descuento_centavos,
                "subtotal_centavos": subtotal,
                "total_linea_centavos": total_linea
            }
        except sqlite3.Error as e:
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al guardar el detalle de venta: {str(e)}",
                status_code=500
            )

    @staticmethod
    def descontar_stock_producto(
        conn: sqlite3.Connection,
        producto_id: str,
        cantidad: int
    ) -> None:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE productos SET stock_actual = stock_actual - ?, updated_at = ? WHERE id = ?;",
                (cantidad, datetime.datetime.now(datetime.timezone.utc).isoformat(), producto_id)
            )
            if cursor.rowcount == 0:
                raise KioskException(
                    code="PRODUCT_NOT_FOUND",
                    message="El producto no existe o no se pudo actualizar",
                    status_code=404
                )
        except sqlite3.IntegrityError as e:
            if "CHECK constraint failed" in str(e) or "stock_actual" in str(e):
                raise KioskException(
                    code="INSUFFICIENT_STOCK",
                    message="El stock del producto no es suficiente para realizar la venta",
                    status_code=400
                )
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al actualizar el stock: {str(e)}",
                status_code=500
            )

    @staticmethod
    def registrar_movimiento_stock(
        conn: sqlite3.Connection,
        prod_id: str,
        user_id: str,
        cantidad: int,
        stock_ant: int,
        stock_nue: int,
        ref_id: str,
        fecha: str
    ) -> None:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO movimientos_stock (
                    id, producto_id, usuario_id, tipo, cantidad, stock_anterior, stock_nuevo,
                    referencia_tipo, referencia_id, motivo, fecha
                ) VALUES (?, ?, ?, 'VENTA', ?, ?, ?, 'VENTA', ?, ?, ?);
                """,
                (
                    uuid.uuid4().hex,
                    prod_id,
                    user_id,
                    -cantidad, # Salida de stock como valor negativo
                    stock_ant,
                    stock_nue,
                    ref_id,
                    "Venta POS",
                    fecha
                )
            )
        except sqlite3.Error as e:
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al registrar movimiento de stock: {str(e)}",
                status_code=500
            )

    @staticmethod
    def get_venta_by_id(conn: sqlite3.Connection, venta_id: str) -> Optional[Dict[str, Any]]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, caja_id, usuario_id, estado, metodo_pago, subtotal_centavos,
                   descuento_items_centavos, descuento_venta_centavos, total_centavos,
                   monto_recibido_centavos, vuelto_centavos, fecha
            FROM ventas WHERE id = ?;
            """,
            (venta_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        
        venta = dict(row)
        
        # Obtener los detalles
        cursor.execute(
            """
            SELECT id, venta_id, producto_id, nombre_producto_snapshot, cantidad,
                   unidad_medida_snapshot, precio_unitario_centavos, descuento_centavos,
                   subtotal_centavos, total_linea_centavos
            FROM venta_detalles WHERE venta_id = ?;
            """,
            (venta_id,)
        )
        venta["detalles"] = [dict(r) for r in cursor.fetchall()]
        return venta

    @staticmethod
    def create_anulacion(
        conn: sqlite3.Connection,
        id_anulacion: str,
        venta_id: str,
        usuario_id: str,
        motivo: Optional[str],
        fecha: str
    ) -> Dict[str, Any]:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO anulaciones (id, venta_id, usuario_id, motivo, fecha)
                VALUES (?, ?, ?, ?, ?);
                """,
                (id_anulacion, venta_id, usuario_id, motivo, fecha)
            )
            return {
                "id": id_anulacion,
                "venta_id": venta_id,
                "usuario_id": usuario_id,
                "motivo": motivo,
                "fecha": fecha
            }
        except sqlite3.Error as e:
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al registrar la cabecera de anulación: {str(e)}",
                status_code=500
            )

    @staticmethod
    def create_devolucion(
        conn: sqlite3.Connection,
        id_devolucion: str,
        venta_id: str,
        usuario_id: str,
        monto_devuelto_centavos: int,
        motivo: Optional[str],
        fecha: str
    ) -> Dict[str, Any]:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO devoluciones (id, venta_id, usuario_id, monto_devuelto_centavos, motivo, fecha)
                VALUES (?, ?, ?, ?, ?, ?);
                """,
                (id_devolucion, venta_id, usuario_id, monto_devuelto_centavos, motivo, fecha)
            )
            return {
                "id": id_devolucion,
                "venta_id": venta_id,
                "usuario_id": usuario_id,
                "monto_devuelto_centavos": monto_devuelto_centavos,
                "motivo": motivo,
                "fecha": fecha
            }
        except sqlite3.Error as e:
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al registrar la cabecera de devolución: {str(e)}",
                status_code=500
            )

    @staticmethod
    def update_venta_estado(
        conn: sqlite3.Connection,
        venta_id: str,
        nuevo_estado: str
    ) -> None:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE ventas SET estado = ? WHERE id = ?;",
                (nuevo_estado, venta_id)
            )
            if cursor.rowcount == 0:
                raise KioskException(
                    code="SALE_NOT_FOUND",
                    message="La venta no existe o no se pudo actualizar",
                    status_code=404
                )
        except sqlite3.Error as e:
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al actualizar el estado de la venta: {str(e)}",
                status_code=500
            )

    @staticmethod
    def revertir_stock_producto(
        conn: sqlite3.Connection,
        producto_id: str,
        cantidad: int
    ) -> None:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE productos SET stock_actual = stock_actual + ?, updated_at = ? WHERE id = ?;",
                (cantidad, datetime.datetime.now(datetime.timezone.utc).isoformat(), producto_id)
            )
            if cursor.rowcount == 0:
                raise KioskException(
                    code="PRODUCT_NOT_FOUND",
                    message="El producto no existe o no se pudo actualizar",
                    status_code=404
                )
        except sqlite3.Error as e:
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al revertir el stock: {str(e)}",
                status_code=500
            )

    @staticmethod
    def registrar_movimiento_stock_reversion(
        conn: sqlite3.Connection,
        prod_id: str,
        user_id: str,
        tipo_mov: str,
        cantidad: int,
        stock_ant: int,
        stock_nue: int,
        ref_id: str,
        fecha: str,
        motivo: Optional[str]
    ) -> None:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO movimientos_stock (
                    id, producto_id, usuario_id, tipo, cantidad, stock_anterior, stock_nuevo,
                    referencia_tipo, referencia_id, motivo, fecha
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    uuid.uuid4().hex,
                    prod_id,
                    user_id,
                    tipo_mov,
                    cantidad,
                    stock_ant,
                    stock_nue,
                    tipo_mov,
                    ref_id,
                    motivo or f"{tipo_mov.capitalize()} de venta",
                    fecha
                )
            )
        except sqlite3.Error as e:
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al registrar movimiento de stock de reversión: {str(e)}",
                status_code=500
            )

    @staticmethod
    def get_all_ventas(
        conn: sqlite3.Connection,
        desde: Optional[str] = None,
        hasta: Optional[str] = None,
        caja_id: Optional[str] = None,
        usuario_id: Optional[str] = None,
        estado: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        query = """
            SELECT id, caja_id, usuario_id, estado, metodo_pago, subtotal_centavos,
                   descuento_items_centavos, descuento_venta_centavos, total_centavos,
                   monto_recibido_centavos, vuelto_centavos, fecha
            FROM ventas
            WHERE 1=1
        """
        params = []
        if desde:
            query += " AND fecha >= ?"
            params.append(desde + "T00:00:00")
        if hasta:
            query += " AND fecha <= ?"
            params.append(hasta + "T23:59:59.999999")
        if caja_id:
            query += " AND caja_id = ?"
            params.append(caja_id)
        if usuario_id:
            query += " AND usuario_id = ?"
            params.append(usuario_id)
        if estado:
            query += " AND estado = ?"
            params.append(estado)

        query += " ORDER BY fecha DESC;"
        
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            ventas = []
            for r in rows:
                v = dict(r)
                cursor.execute(
                    """
                    SELECT id, venta_id, producto_id, nombre_producto_snapshot, cantidad,
                           unidad_medida_snapshot, precio_unitario_centavos, descuento_centavos,
                           subtotal_centavos, total_linea_centavos
                    FROM venta_detalles WHERE venta_id = ?;
                    """,
                    (v["id"],)
                )
                v["detalles"] = [dict(dt) for dt in cursor.fetchall()]
                ventas.append(v)
            return ventas
        except sqlite3.Error as e:
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al listar las ventas de la base de datos: {str(e)}",
                status_code=500
            )


