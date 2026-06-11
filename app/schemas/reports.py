from pydantic import BaseModel, Field
from typing import List, Optional

class VentasPorCajero(BaseModel):
    cajero_id: str
    nombre_cajero: str
    total_centavos: int
    cantidad_ventas: int

class VentasPorMetodoPago(BaseModel):
    metodo_pago: str
    total_centavos: int
    cantidad_ventas: int

class VentasDiariasResponse(BaseModel):
    total_general_centavos: int
    cantidad_ventas: int
    descuentos_aplicados_centavos: int
    total_por_metodo: List[VentasPorMetodoPago]
    total_por_cajero: List[VentasPorCajero]
    cantidad_anulaciones: int
    total_anulado_centavos: int
    cantidad_devoluciones: int
    total_devuelto_centavos: int

class CajaReportItem(BaseModel):
    id: str
    usuario_apertura_id: str
    usuario_apertura_nombre: str
    usuario_cierre_id: Optional[str] = None
    usuario_cierre_nombre: Optional[str] = None
    estado: str
    monto_inicial_centavos: int
    monto_ingresos_centavos: int
    monto_retiros_centavos: int
    monto_ventas_efectivo_centavos: int
    monto_ventas_digital_centavos: int
    monto_declarado_centavos: Optional[int] = None
    monto_esperado_centavos: Optional[int] = None
    desviacion_centavos: Optional[int] = None
    fecha_apertura: str
    fecha_cierre: Optional[str] = None

class ProductoRankingItem(BaseModel):
    producto_id: str
    nombre_producto: str
    cantidad_vendida: int
    monto_vendido_centavos: int

class StockBajoReportItem(BaseModel):
    producto_id: str
    nombre_producto: str
    stock_actual: int
    stock_minimo: int
    categoria_nombre: str
    unidad_medida: str

