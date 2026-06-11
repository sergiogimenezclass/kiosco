from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from typing import List, Optional

class MetodoPago(str, Enum):
    EFECTIVO = "EFECTIVO"
    DIGITAL = "DIGITAL"

class VentaEstado(str, Enum):
    COMPLETADA = "COMPLETADA"
    ANULADA = "ANULADA"
    DEVUELTA = "DEVUELTA"

class VentaDetalleCreate(BaseModel):
    producto_id: str
    cantidad: int = Field(..., gt=0, description="Cantidad vendida, debe ser mayor a cero")
    precio_unitario_centavos: int = Field(..., gt=0, description="Precio unitario en centavos")
    descuento_centavos: int = Field(0, ge=0, description="Descuento aplicado en centavos")

class VentaCreate(BaseModel):
    caja_id: str
    metodo_pago: MetodoPago
    subtotal_centavos: int = Field(..., ge=0, description="Subtotal en centavos")
    descuento_items_centavos: int = Field(0, ge=0, description="Suma de descuentos por ítem en centavos")
    descuento_venta_centavos: int = Field(0, ge=0, description="Descuento global a la venta en centavos")
    total_centavos: int = Field(..., ge=0, description="Total neto en centavos")
    monto_recibido_centavos: int = Field(..., ge=0, description="Monto recibido en centavos")
    vuelto_centavos: int = Field(0, ge=0, description="Vuelto entregado en centavos")
    detalles: List[VentaDetalleCreate] = Field(..., min_length=1, description="Lista de detalles de la venta")

class VentaDetalleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    venta_id: str
    producto_id: str
    nombre_producto_snapshot: str
    cantidad: int
    unidad_medida_snapshot: str
    precio_unitario_centavos: int
    descuento_centavos: int
    subtotal_centavos: int
    total_linea_centavos: int

class VentaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    caja_id: str
    usuario_id: str
    estado: VentaEstado
    metodo_pago: MetodoPago
    subtotal_centavos: int
    descuento_items_centavos: int
    descuento_venta_centavos: int
    total_centavos: int
    monto_recibido_centavos: int
    vuelto_centavos: int
    fecha: str
    detalles: List[VentaDetalleResponse] = []
