from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from typing import Optional

class CajaEstado(str, Enum):
    ABIERTA = "ABIERTA"
    CERRADA = "CERRADA"

class MovimientoCajaTipo(str, Enum):
    INGRESO = "INGRESO"
    RETIRO = "RETIRO"

class CajaApertura(BaseModel):
    monto_inicial_centavos: int = Field(..., ge=0, description="Monto inicial de apertura en centavos")

class CajaCierre(BaseModel):
    monto_declarado_centavos: int = Field(..., ge=0, description="Monto físico declarado al cierre en centavos")

class CajaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    usuario_apertura_id: str
    usuario_cierre_id: Optional[str] = None
    estado: CajaEstado
    monto_inicial_centavos: int
    monto_declarado_centavos: Optional[int] = None
    monto_esperado_centavos: Optional[int] = None
    desviacion_centavos: Optional[int] = None
    fecha_apertura: str
    fecha_cierre: Optional[str] = None

class MovimientoCajaCreate(BaseModel):
    tipo: MovimientoCajaTipo
    monto_centavos: int = Field(..., gt=0, description="Monto del movimiento en centavos (debe ser mayor a cero)")
    motivo: str = Field(..., min_length=1, max_length=255, description="Motivo obligatorio del movimiento")

class MovimientoCajaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    caja_id: str
    usuario_id: str
    tipo: MovimientoCajaTipo
    monto_centavos: int
    motivo: str
    fecha: str
