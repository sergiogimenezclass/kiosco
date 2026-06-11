from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from typing import Optional

class MovimientoTipo(str, Enum):
    VENTA = "VENTA"
    DEVOLUCION = "DEVOLUCION"
    ANULACION = "ANULACION"
    AJUSTE = "AJUSTE"
    INGRESO = "INGRESO"

class StockAjusteCreate(BaseModel):
    producto_id: str = Field(..., min_length=1, description="ID del producto a ajustar")
    cantidad_delta: int = Field(..., description="Cantidad a ajustar, puede ser positiva o negativa")
    motivo: str = Field(..., min_length=1, description="Motivo del ajuste de stock")

class StockIngresoCreate(BaseModel):
    producto_id: str = Field(..., min_length=1, description="ID del producto a ingresar")
    cantidad: int = Field(..., description="Cantidad a ingresar, debe ser mayor a cero")
    proveedor_id: str = Field(..., min_length=1, description="ID del proveedor obligatorio")
    motivo: str = Field(..., min_length=1, description="Motivo del ingreso de stock")

class MovimientoStockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    producto_id: str
    usuario_id: str
    tipo: MovimientoTipo
    cantidad: int
    stock_anterior: int
    stock_nuevo: int
    referencia_tipo: Optional[str] = None
    referencia_id: Optional[str] = None
    motivo: Optional[str] = None
    proveedor_id: Optional[str] = None
    fecha: str
