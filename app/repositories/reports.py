import sqlite3
from typing import List, Optional, Dict, Any

class ReportsRepository:
    @staticmethod
    def get_ventas_diarias_data(
        conn: sqlite3.Connection,
        desde: Optional[str] = None,
        hasta: Optional[str] = None
    ) -> Dict[str, Any]:
        cursor = conn.cursor()
        
        # Filtros de fecha lexicográficos
        params = []
        date_filter_venta = ""
        date_filter_anulacion = ""
        date_filter_devolucion = ""
        
        if desde:
            date_filter_venta += " AND fecha >= ?"
            date_filter_anulacion += " AND fecha >= ?"
            date_filter_devolucion += " AND fecha >= ?"
            params.append(desde + "T00:00:00")
        if hasta:
            date_filter_venta += " AND fecha <= ?"
            date_filter_anulacion += " AND fecha <= ?"
            date_filter_devolucion += " AND fecha <= ?"
            params.append(hasta + "T23:59:59.999999")

        # 1. Total general y cantidad de ventas
        query_general = f"""
            SELECT COALESCE(SUM(total_centavos), 0) as total_general_centavos, COUNT(*) as cantidad_ventas
            FROM ventas
            WHERE estado = 'COMPLETADA'{date_filter_venta};
        """
        cursor.execute(query_general, params)
        res_general = cursor.fetchone()
        total_general = res_general["total_general_centavos"]
        cantidad_ventas = res_general["cantidad_ventas"]

        # 2. Descuentos aplicados (items + venta)
        query_descuentos = f"""
            SELECT COALESCE(SUM(descuento_items_centavos + descuento_venta_centavos), 0) as descuentos_centavos
            FROM ventas
            WHERE estado = 'COMPLETADA'{date_filter_venta};
        """
        cursor.execute(query_descuentos, params)
        descuentos = cursor.fetchone()["descuentos_centavos"]

        # 3. Ventas por método de pago
        query_metodo = f"""
            SELECT metodo_pago, COALESCE(SUM(total_centavos), 0) as total_centavos, COUNT(*) as cantidad_ventas
            FROM ventas
            WHERE estado = 'COMPLETADA'{date_filter_venta}
            GROUP BY metodo_pago;
        """
        cursor.execute(query_metodo, params)
        res_metodos = cursor.fetchall()
        total_por_metodo = [dict(row) for row in res_metodos]

        # 4. Ventas por cajero
        query_cajero = f"""
            SELECT v.usuario_id as cajero_id, u.nombre as nombre_cajero, COALESCE(SUM(v.total_centavos), 0) as total_centavos, COUNT(*) as cantidad_ventas
            FROM ventas v
            JOIN usuarios u ON v.usuario_id = u.id
            WHERE v.estado = 'COMPLETADA'{date_filter_venta}
            GROUP BY v.usuario_id;
        """
        cursor.execute(query_cajero, params)
        res_cajeros = cursor.fetchall()
        total_por_cajero = [dict(row) for row in res_cajeros]

        # 5. Anulaciones
        query_anulaciones = f"""
            SELECT COUNT(*) as cantidad_anulaciones, COALESCE(SUM(v.total_centavos), 0) as total_anulado_centavos
            FROM anulaciones a
            JOIN ventas v ON a.venta_id = v.id
            WHERE 1=1{date_filter_anulacion.replace("fecha", "a.fecha")};
        """
        cursor.execute(query_anulaciones, params)
        res_anulaciones = cursor.fetchone()
        cantidad_anulaciones = res_anulaciones["cantidad_anulaciones"]
        total_anulado = res_anulaciones["total_anulado_centavos"]

        # 6. Devoluciones
        query_devoluciones = f"""
            SELECT COUNT(*) as cantidad_devoluciones, COALESCE(SUM(d.monto_devuelto_centavos), 0) as total_devuelto_centavos
            FROM devoluciones d
            WHERE 1=1{date_filter_devolucion.replace("fecha", "d.fecha")};
        """
        cursor.execute(query_devoluciones, params)
        res_devoluciones = cursor.fetchone()
        cantidad_devoluciones = res_devoluciones["cantidad_devoluciones"]
        total_devuelto = res_devoluciones["total_devuelto_centavos"]

        return {
            "total_general_centavos": total_general,
            "cantidad_ventas": cantidad_ventas,
            "descuentos_aplicados_centavos": descuentos,
            "total_por_metodo": total_por_metodo,
            "total_por_cajero": total_por_cajero,
            "cantidad_anulaciones": cantidad_anulaciones,
            "total_anulado_centavos": total_anulado,
            "cantidad_devoluciones": cantidad_devoluciones,
            "total_devuelto_centavos": total_devuelto
        }

    @staticmethod
    def get_cajas_data(
        conn: sqlite3.Connection,
        desde: Optional[str] = None,
        hasta: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        
        params = []
        date_filter = ""
        if desde:
            date_filter += " AND c.fecha_apertura >= ?"
            params.append(desde + "T00:00:00")
        if hasta:
            date_filter += " AND c.fecha_apertura <= ?"
            params.append(hasta + "T23:59:59.999999")

        query = f"""
            SELECT
                c.id,
                c.usuario_apertura_id,
                ua.nombre as usuario_apertura_nombre,
                c.usuario_cierre_id,
                uc.nombre as usuario_cierre_nombre,
                c.estado,
                c.monto_inicial_centavos,
                COALESCE((SELECT SUM(monto_centavos) FROM movimientos_caja WHERE caja_id = c.id AND tipo = 'INGRESO'), 0) as monto_ingresos_centavos,
                COALESCE((SELECT SUM(monto_centavos) FROM movimientos_caja WHERE caja_id = c.id AND tipo = 'RETIRO'), 0) as monto_retiros_centavos,
                COALESCE((SELECT SUM(total_centavos) FROM ventas WHERE caja_id = c.id AND estado = 'COMPLETADA' AND metodo_pago = 'EFECTIVO'), 0) as monto_ventas_efectivo_centavos,
                COALESCE((SELECT SUM(total_centavos) FROM ventas WHERE caja_id = c.id AND estado = 'COMPLETADA' AND metodo_pago = 'DIGITAL'), 0) as monto_ventas_digital_centavos,
                c.monto_declarado_centavos,
                c.monto_esperado_centavos,
                c.desviacion_centavos,
                c.fecha_apertura,
                c.fecha_cierre
            FROM cajas c
            LEFT JOIN usuarios ua ON c.usuario_apertura_id = ua.id
            LEFT JOIN usuarios uc ON c.usuario_cierre_id = uc.id
            WHERE 1=1{date_filter}
            ORDER BY c.fecha_apertura DESC;
        """
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_ranking_productos(
        conn: sqlite3.Connection,
        ordenar_por: str,
        limit: int = 15
    ) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        
        # Validar el ordenamiento para prevenir SQL injection directo
        order_col = "cantidad_vendida"
        if ordenar_por == "monto":
            order_col = "monto_vendido_centavos"

        query = f"""
            SELECT
                vd.producto_id,
                p.nombre as nombre_producto,
                CAST(SUM(vd.cantidad) AS INTEGER) as cantidad_vendida,
                CAST(SUM(vd.total_linea_centavos) AS INTEGER) as monto_vendido_centavos
            FROM venta_detalles vd
            JOIN ventas v ON vd.venta_id = v.id
            JOIN productos p ON vd.producto_id = p.id
            WHERE v.estado = 'COMPLETADA'
            GROUP BY vd.producto_id, p.nombre
            ORDER BY {order_col} DESC
            LIMIT ?;
        """
        cursor.execute(query, (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def get_stock_bajo(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        cursor = conn.cursor()
        
        query = """
            SELECT
                p.id as producto_id,
                p.nombre as nombre_producto,
                p.stock_actual,
                p.stock_minimo,
                c.nombre as categoria_nombre,
                p.unidad_medida
            FROM productos p
            JOIN categorias c ON p.categoria_id = c.id
            WHERE p.activo = 1 AND p.stock_actual <= p.stock_minimo
            ORDER BY p.nombre ASC;
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
