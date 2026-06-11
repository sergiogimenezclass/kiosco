from pydantic import BaseModel, Field, ConfigDict
from enum import Enum
from typing import List, Optional

# --- Categorías ---

class CategoriaBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)

class CategoriaCreate(CategoriaBase):
    pass

class CategoriaResponse(CategoriaBase):
    model_config = ConfigDict(from_attributes=True)
    id: str

# --- Marcas ---

class MarcaBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)

class CareaCreate(MarcaBase):  # For compatibility if needed, let's just name it MarcaCreate
    pass

class MarcaCreate(MarcaBase):
    pass

class MarcaResponse(MarcaBase):
    model_config = ConfigDict(from_attributes=True)
    id: str

# --- Proveedores ---

class ProveedorBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    telefono: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=100)

class ProveedorCreate(ProveedorBase):
    pass

class ProveedorResponse(ProveedorBase):
    model_config = ConfigDict(from_attributes=True)
    id: str

# --- Productos ---

class UnidadMedida(str, Enum):
    UNIDAD = "UNIDAD"
    GRAMO = "GRAMO"
    MILILITRO = "MILILITRO"

class ProductoBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    descripcion: Optional[str] = None
    categoria_id: str
    marca_id: Optional[str] = None
    proveedor_id: Optional[str] = None
    precio_venta_centavos: int = Field(..., gt=0)
    stock_actual: int = Field(0, ge=0)
    stock_minimo: int = Field(0, ge=0)
    unidad_medida: UnidadMedida
    imagen_url: Optional[str] = None
    activo: int = Field(1, ge=0, le=1)

class ProductoCreate(ProductoBase):
    codigos_barras: List[str] = []

class ProductoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=200)
    descripcion: Optional[str] = None
    categoria_id: Optional[str] = None
    marca_id: Optional[str] = None
    proveedor_id: Optional[str] = None
    precio_venta_centavos: Optional[int] = Field(None, gt=0)
    stock_actual: Optional[int] = Field(None, ge=0)
    stock_minimo: Optional[int] = Field(None, ge=0)
    unidad_medida: Optional[UnidadMedida] = None
    imagen_url: Optional[str] = None
    activo: Optional[int] = Field(None, ge=0, le=1)
    codigos_barras: Optional[List[str]] = None

class ProductoResponse(ProductoBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: str
    updated_at: str
    codigos_barras: List[str] = []

# --- Accesos Rápidos ---

class AccesoRapidoBase(BaseModel):
    producto_id: str
    etiqueta: str = Field(..., min_length=1, max_length=50)
    orden: int
    activo: int = Field(1, ge=0, le=1)

class AccesoRapidoCreate(AccesoRapidoBase):
    pass

class AccesoRapidoResponse(AccesoRapidoBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
