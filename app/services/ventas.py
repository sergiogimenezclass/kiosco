import sqlite3
import uuid
import datetime
from typing import Dict, Any, List, Optional
from app.core.errors import KioskException
from app.schemas.ventas import VentaCreate, VentaResponse, AnulacionCreate, DevolucionCreate
from app.repositories.ventas import VentasRepository
from app.repositories.caja import CajaRepository
from app.repositories.catalog import ProductoRepository

class VentasService:
    @staticmethod
    def registrar_venta(db: sqlite3.Connection, usuario_id: str, venta_in: VentaCreate) -> Dict[str, Any]:
        # 1. Validar caja abierta
        active_caja = CajaRepository.get_active_caja(db)
        if not active_caja:
            raise KioskException(
                code="CASH_REGISTER_CLOSED",
                message="No hay ninguna caja abierta activa para realizar ventas",
                status_code=400
            )
        
        if active_caja["id"] != venta_in.caja_id:
            raise KioskException(
                code="INVALID_CASH_REGISTER",
                message="La caja especificada no coincide con la caja activa del sistema",
                status_code=400
            )

        # 2. Validar consistencia de cálculos de montos de detalles
        calculated_subtotal = 0
        calculated_details_discount = 0
        
        # Validaremos cada producto antes de realizar cualquier cambio en la base de datos
        detalles_productos = []
        for item in venta_in.detalles:
            prod = ProductoRepository.get_by_id(db, item.producto_id)
            if not prod:
                raise KioskException(
                    code="PRODUCT_NOT_FOUND",
                    message=f"El producto con ID '{item.producto_id}' no existe en el catálogo",
                    status_code=404
                )
            if prod["activo"] != 1:
                raise KioskException(
                    code="PRODUCT_INACTIVE",
                    message=f"El producto '{prod['nombre']}' no está activo y no se puede vender",
                    status_code=400
                )
            
            # Chequear stock en la capa de validación
            if prod["stock_actual"] < item.cantidad:
                raise KioskException(
                    code="INSUFFICIENT_STOCK",
                    message=f"Stock insuficiente para '{prod['nombre']}'. Disponible: {prod['stock_actual']}, Solicitado: {item.cantidad}",
                    status_code=400
                )
            
            # Validar que el precio unitario del payload coincida con el precio real
            if prod["precio_venta_centavos"] != item.precio_unitario_centavos:
                raise KioskException(
                    code="PRICE_MISMATCH",
                    message=f"El precio del producto '{prod['nombre']}' ha cambiado. Por favor actualice el carrito.",
                    status_code=400
                )
            
            calculated_subtotal += item.precio_unitario_centavos * item.cantidad
            calculated_details_discount += item.descuento_centavos
            detalles_productos.append((item, prod))

        if calculated_subtotal != venta_in.subtotal_centavos:
            raise KioskException(
                code="INVALID_SUBTOTAL",
                message="El subtotal enviado no coincide con el cálculo de los productos",
                status_code=400
            )
            
        if calculated_details_discount != venta_in.descuento_items_centavos:
            raise KioskException(
                code="INVALID_DISCOUNT",
                message="La suma de descuentos de ítems no coincide con el total de descuento de ítems",
                status_code=400
            )

        # Calcular total final esperado
        expected_total = calculated_subtotal - (venta_in.descuento_items_centavos + venta_in.descuento_venta_centavos)
        if expected_total < 0:
            expected_total = 0
            
        if expected_total != venta_in.total_centavos:
            raise KioskException(
                code="INVALID_TOTAL",
                message="El total enviado no coincide con el cálculo del subtotal menos descuentos",
                status_code=400
            )

        # 3. Validar descuento máximo permitido
        cursor = db.cursor()
        cursor.execute("SELECT valor FROM configuracion WHERE clave = 'descuento_maximo_porcentaje';")
        row = cursor.fetchone()
        max_discount_pct = int(row["valor"]) if row else 50
        
        total_descuento = venta_in.descuento_items_centavos + venta_in.descuento_venta_centavos
        if calculated_subtotal > 0:
            discount_pct = (total_descuento * 100) / calculated_subtotal
            if discount_pct > max_discount_pct:
                raise KioskException(
                    code="EXCEEDED_MAX_DISCOUNT",
                    message=f"El descuento total excede el porcentaje máximo permitido ({max_discount_pct}%)",
                    status_code=400
                )

        # 4. Validar método de pago y vuelto
        if venta_in.metodo_pago.value == "EFECTIVO":
            if venta_in.monto_recibido_centavos < expected_total:
                raise KioskException(
                    code="INSUFFICIENT_PAYMENT",
                    message="El dinero en efectivo recibido es insuficiente para cubrir el total",
                    status_code=400
                )
            expected_vuelto = venta_in.monto_recibido_centavos - expected_total
            if expected_vuelto != venta_in.vuelto_centavos:
                raise KioskException(
                    code="INVALID_CHANGE",
                    message="El vuelto calculado no coincide con el monto recibido menos el total",
                    status_code=400
                )
        else: # DIGITAL
            if venta_in.monto_recibido_centavos != expected_total or venta_in.vuelto_centavos != 0:
                raise KioskException(
                    code="INVALID_DIGITAL_PAYMENT",
                    message="Para pagos digitales, el monto recibido debe ser idéntico al total y el vuelto debe ser cero",
                    status_code=400
                )

        # 5. Ejecutar transacción atómica
        id_venta = uuid.uuid4().hex
        fecha_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        try:
            # 1. Guardar cabecera de la venta primero para evitar fallos de clave foránea
            VentasRepository.create_venta(db, venta_in, usuario_id, id_venta, fecha_utc)

            # 2. Procesar detalles, actualizar stock y registrar movimientos
            for item, prod in detalles_productos:
                id_detalle = uuid.uuid4().hex
                # Guardar detalle
                VentasRepository.create_venta_detalle(
                    db,
                    item,
                    id_venta,
                    id_detalle,
                    prod["nombre"],
                    prod["unidad_medida"]
                )
                # Descontar stock
                VentasRepository.descontar_stock_producto(db, item.producto_id, item.cantidad)
                
                # Registrar movimiento de stock
                VentasRepository.registrar_movimiento_stock(
                    db,
                    item.producto_id,
                    usuario_id,
                    item.cantidad,
                    prod["stock_actual"],
                    prod["stock_actual"] - item.cantidad,
                    id_venta,
                    fecha_utc
                )
            
            # Recuperar y retornar la venta completa registrada
            venta_guardada = VentasRepository.get_venta_by_id(db, id_venta)
            if not venta_guardada:
                raise KioskException(
                    code="DATABASE_ERROR",
                    message="No se pudo recuperar la venta registrada de la base de datos",
                    status_code=500
                )
            return venta_guardada
            
        except Exception as e:
            # Dado que get_db de FastAPI realiza commits/rollbacks automáticos,
            # cualquier excepción lanzada aquí propagará el error y gatillará el rollback automático
            # en el context manager get_db_conn() de la base de datos.
            raise e

    @staticmethod
    def anular_venta(db: sqlite3.Connection, usuario_id: str, venta_id: str, anulacion_in: AnulacionCreate) -> Dict[str, Any]:
        # 1. Recuperar la venta
        venta = VentasRepository.get_venta_by_id(db, venta_id)
        if not venta:
            raise KioskException(
                code="SALE_NOT_FOUND",
                message="La venta no existe",
                status_code=404
            )
        
        # Validar estado
        if venta["estado"] != "COMPLETADA":
            raise KioskException(
                code="INVALID_SALE_STATE",
                message=f"No se puede anular una venta con estado {venta['estado']}",
                status_code=400
            )
            
        # Validar fecha (mismo día calendario UTC)
        try:
            fecha_venta = datetime.datetime.fromisoformat(venta["fecha"])
        except ValueError:
            raise KioskException(
                code="INVALID_SALE_DATE",
                message="La fecha de la venta no tiene un formato válido",
                status_code=500
            )
            
        if fecha_venta.tzinfo is None:
            fecha_venta = fecha_venta.replace(tzinfo=datetime.timezone.utc)
            
        current_time = datetime.datetime.now(datetime.timezone.utc)
        if fecha_venta.astimezone(datetime.timezone.utc).date() != current_time.date():
            raise KioskException(
                code="SALE_NOT_SAME_DAY",
                message="Solo se pueden anular ventas realizadas el mismo día",
                status_code=400
            )
            
        id_anulacion = uuid.uuid4().hex
        fecha_utc = current_time.isoformat()
        
        try:
            # Registrar anulación
            anulacion = VentasRepository.create_anulacion(
                db,
                id_anulacion=id_anulacion,
                venta_id=venta_id,
                usuario_id=usuario_id,
                motivo=anulacion_in.motivo,
                fecha=fecha_utc
            )
            
            # Cambiar estado de la venta
            VentasRepository.update_venta_estado(db, venta_id, "ANULADA")
            
            # Revertir stock de cada ítem
            for item in venta["detalles"]:
                prod = ProductoRepository.get_by_id(db, item["producto_id"])
                if not prod:
                    raise KioskException(
                        code="PRODUCT_NOT_FOUND",
                        message=f"El producto con ID '{item['producto_id']}' no existe en el catálogo",
                        status_code=404
                    )
                
                stock_anterior = prod["stock_actual"]
                cantidad_a_revertir = item["cantidad"]
                stock_nuevo = stock_anterior + cantidad_a_revertir
                
                VentasRepository.revertir_stock_producto(db, item["producto_id"], cantidad_a_revertir)
                
                VentasRepository.registrar_movimiento_stock_reversion(
                    db,
                    prod_id=item["producto_id"],
                    user_id=usuario_id,
                    tipo_mov="ANULACION",
                    cantidad=cantidad_a_revertir,
                    stock_ant=stock_anterior,
                    stock_nue=stock_nuevo,
                    ref_id=id_anulacion,
                    fecha=fecha_utc,
                    motivo=anulacion_in.motivo
                )
                
            return anulacion
            
        except Exception as e:
            raise e

    @staticmethod
    def devolver_venta(db: sqlite3.Connection, usuario_id: str, venta_id: str, devolucion_in: DevolucionCreate) -> Dict[str, Any]:
        # 1. Recuperar la venta
        venta = VentasRepository.get_venta_by_id(db, venta_id)
        if not venta:
            raise KioskException(
                code="SALE_NOT_FOUND",
                message="La venta no existe",
                status_code=404
            )
        
        # Validar estado
        if venta["estado"] != "COMPLETADA":
            raise KioskException(
                code="INVALID_SALE_STATE",
                message=f"No se puede devolver una venta con estado {venta['estado']}",
                status_code=400
            )
            
        id_devolucion = uuid.uuid4().hex
        fecha_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        monto_devuelto = venta["total_centavos"]
        
        try:
            # Registrar devolución
            devolucion = VentasRepository.create_devolucion(
                db,
                id_devolucion=id_devolucion,
                venta_id=venta_id,
                usuario_id=usuario_id,
                monto_devuelto_centavos=monto_devuelto,
                motivo=devolucion_in.motivo,
                fecha=fecha_utc
            )
            
            # Cambiar estado de la venta
            VentasRepository.update_venta_estado(db, venta_id, "DEVUELTA")
            
            # Revertir stock de cada ítem
            for item in venta["detalles"]:
                prod = ProductoRepository.get_by_id(db, item["producto_id"])
                if not prod:
                    raise KioskException(
                        code="PRODUCT_NOT_FOUND",
                        message=f"El producto con ID '{item['producto_id']}' no existe en el catálogo",
                        status_code=404
                    )
                
                stock_anterior = prod["stock_actual"]
                cantidad_a_revertir = item["cantidad"]
                stock_nuevo = stock_anterior + cantidad_a_revertir
                
                VentasRepository.revertir_stock_producto(db, item["producto_id"], cantidad_a_revertir)
                
                VentasRepository.registrar_movimiento_stock_reversion(
                    db,
                    prod_id=item["producto_id"],
                    user_id=usuario_id,
                    tipo_mov="DEVOLUCION",
                    cantidad=cantidad_a_revertir,
                    stock_ant=stock_anterior,
                    stock_nue=stock_nuevo,
                    ref_id=id_devolucion,
                    fecha=fecha_utc,
                    motivo=devolucion_in.motivo
                )
                
            return devolucion
            
        except Exception as e:
            raise e

    @staticmethod
    def listar_ventas(
        db: sqlite3.Connection,
        desde: Optional[str] = None,
        hasta: Optional[str] = None,
        caja_id: Optional[str] = None,
        usuario_id: Optional[str] = None,
        estado: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        return VentasRepository.get_all_ventas(db, desde, hasta, caja_id, usuario_id, estado)

