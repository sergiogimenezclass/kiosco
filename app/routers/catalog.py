from fastapi import APIRouter, Depends, status, Query
import sqlite3
from typing import List, Optional

from app.core.database import get_db
from app.schemas.catalog import (
    CategoriaCreate,
    CategoriaResponse,
    MarcaCreate,
    MarcaResponse,
    ProveedorCreate,
    ProveedorResponse,
    ProductoCreate,
    ProductoUpdate,
    ProductoResponse,
    AccesoRapidoCreate,
    AccesoRapidoResponse
)
from app.services.catalog import (
    CategoriaService,
    MarcaService,
    ProveedorService,
    ProductoService,
    AccesoRapidoService
)
from app.services.auth import get_current_user, RoleChecker

# Write operations are restricted to SUPERVISOR and ADMINISTRADOR
write_rbac = Depends(RoleChecker(["SUPERVISOR", "ADMINISTRADOR"]))
# Read operations require any logged-in user
read_rbac = Depends(get_current_user)

# --- CATEGORÍAS ROUTER ---
categorias_router = APIRouter()

@categorias_router.get("", response_model=List[CategoriaResponse], dependencies=[read_rbac])
def list_categories(db: sqlite3.Connection = Depends(get_db)):
    """Lists all product categories."""
    return CategoriaService.get_all_categories(db)

@categorias_router.get("/{id}", response_model=CategoriaResponse, dependencies=[read_rbac])
def get_category(id: str, db: sqlite3.Connection = Depends(get_db)):
    """Gets a specific category by its ID."""
    return CategoriaService.get_category(db, id)

@categorias_router.post("", response_model=CategoriaResponse, status_code=status.HTTP_201_CREATED, dependencies=[write_rbac])
def create_category(category_in: CategoriaCreate, db: sqlite3.Connection = Depends(get_db)):
    """Creates a new category. Only available to SUPERVISOR and ADMINISTRADOR."""
    return CategoriaService.create_category(db, category_in)

@categorias_router.put("/{id}", response_model=CategoriaResponse, dependencies=[write_rbac])
def update_category(id: str, category_in: CategoriaCreate, db: sqlite3.Connection = Depends(get_db)):
    """Updates an existing category. Only available to SUPERVISOR and ADMINISTRADOR."""
    return CategoriaService.update_category(db, id, category_in)

@categorias_router.delete("/{id}", status_code=status.HTTP_200_OK, dependencies=[write_rbac])
def delete_category(id: str, db: sqlite3.Connection = Depends(get_db)):
    """Deletes a category. Fails if products are associated with it."""
    CategoriaService.delete_category(db, id)
    return {"message": "Categoría eliminada exitosamente"}


# --- MARCAS ROUTER ---
marcas_router = APIRouter()

@marcas_router.get("", response_model=List[MarcaResponse], dependencies=[read_rbac])
def list_brands(db: sqlite3.Connection = Depends(get_db)):
    """Lists all product brands."""
    return MarcaService.get_all_brands(db)

@marcas_router.get("/{id}", response_model=MarcaResponse, dependencies=[read_rbac])
def get_brand(id: str, db: sqlite3.Connection = Depends(get_db)):
    """Gets a specific brand by its ID."""
    return MarcaService.get_brand(db, id)

@marcas_router.post("", response_model=MarcaResponse, status_code=status.HTTP_201_CREATED, dependencies=[write_rbac])
def create_brand(brand_in: MarcaCreate, db: sqlite3.Connection = Depends(get_db)):
    """Creates a new brand. Only available to SUPERVISOR and ADMINISTRADOR."""
    return MarcaService.create_brand(db, brand_in)

@marcas_router.put("/{id}", response_model=MarcaResponse, dependencies=[write_rbac])
def update_brand(id: str, brand_in: MarcaCreate, db: sqlite3.Connection = Depends(get_db)):
    """Updates an existing brand. Only available to SUPERVISOR and ADMINISTRADOR."""
    return MarcaService.update_brand(db, id, brand_in)

@marcas_router.delete("/{id}", status_code=status.HTTP_200_OK, dependencies=[write_rbac])
def delete_brand(id: str, db: sqlite3.Connection = Depends(get_db)):
    """Deletes a brand. Fails if products are associated with it."""
    MarcaService.delete_brand(db, id)
    return {"message": "Marca eliminada exitosamente"}


# --- PROVEEDORES ROUTER ---
proveedores_router = APIRouter()

@proveedores_router.get("", response_model=List[ProveedorResponse], dependencies=[read_rbac])
def list_providers(db: sqlite3.Connection = Depends(get_db)):
    """Lists all product suppliers/providers."""
    return ProveedorService.get_all_providers(db)

@proveedores_router.get("/{id}", response_model=ProveedorResponse, dependencies=[read_rbac])
def get_provider(id: str, db: sqlite3.Connection = Depends(get_db)):
    """Gets a specific supplier by ID."""
    return ProveedorService.get_provider(db, id)

@proveedores_router.post("", response_model=ProveedorResponse, status_code=status.HTTP_201_CREATED, dependencies=[write_rbac])
def create_provider(provider_in: ProveedorCreate, db: sqlite3.Connection = Depends(get_db)):
    """Creates a new supplier. Only available to SUPERVISOR and ADMINISTRADOR."""
    return ProveedorService.create_provider(db, provider_in)

@proveedores_router.put("/{id}", response_model=ProveedorResponse, dependencies=[write_rbac])
def update_provider(id: str, provider_in: ProveedorCreate, db: sqlite3.Connection = Depends(get_db)):
    """Updates a supplier by ID. Only available to SUPERVISOR and ADMINISTRADOR."""
    return ProveedorService.update_provider(db, id, provider_in)

@proveedores_router.delete("/{id}", status_code=status.HTTP_200_OK, dependencies=[write_rbac])
def delete_provider(id: str, db: sqlite3.Connection = Depends(get_db)):
    """Deletes a supplier by ID. Fails if associated products exist."""
    ProveedorService.delete_provider(db, id)
    return {"message": "Proveedor eliminado exitosamente"}


# --- PRODUCTOS ROUTER ---
productos_router = APIRouter()

@productos_router.get("", response_model=List[ProductoResponse], dependencies=[read_rbac])
def list_products(
    q: Optional[str] = Query(None, description="Búsqueda predictiva por nombre o código de barras"),
    categoria_id: Optional[str] = Query(None, description="Filtro por ID de categoría"),
    marca_id: Optional[str] = Query(None, description="Filtro por ID de marca"),
    activo: Optional[int] = Query(None, description="Filtro por estado activo (1 o 0)", ge=0, le=1),
    db: sqlite3.Connection = Depends(get_db)
):
    """
    Lists all products in catalog, allowing optional query filter parameters.
    """
    return ProductoService.get_all_products(db, q, categoria_id, marca_id, activo)

@productos_router.get("/codigo/{codigo}", response_model=ProductoResponse, dependencies=[read_rbac])
def get_product_by_barcode(codigo: str, db: sqlite3.Connection = Depends(get_db)):
    """
    Retrieves a product by its barcode.
    """
    return ProductoService.get_product_by_barcode(db, codigo)

@productos_router.get("/{id}", response_model=ProductoResponse, dependencies=[read_rbac])
def get_product(id: str, db: sqlite3.Connection = Depends(get_db)):
    """Retrieves a product by its ID."""
    return ProductoService.get_product(db, id)

@productos_router.post("", response_model=ProductoResponse, status_code=status.HTTP_201_CREATED, dependencies=[write_rbac])
def create_product(product_in: ProductoCreate, db: sqlite3.Connection = Depends(get_db)):
    """
    Creates a new product in catalog, optionally associating initial barcodes.
    Only available to SUPERVISOR and ADMINISTRADOR.
    """
    return ProductoService.create_product(db, product_in)

@productos_router.put("/{id}", response_model=ProductoResponse, dependencies=[write_rbac])
def update_product(id: str, product_in: ProductoUpdate, db: sqlite3.Connection = Depends(get_db)):
    """
    Updates an existing product's fields and/or barcodes.
    Only available to SUPERVISOR and ADMINISTRADOR.
    """
    return ProductoService.update_product(db, id, product_in)

@productos_router.delete("/{id}", status_code=status.HTTP_200_OK, dependencies=[write_rbac])
def delete_product(id: str, db: sqlite3.Connection = Depends(get_db)):
    """
    Deletes a product by ID.
    Fails if the product has associated sales or inventory history.
    Only available to SUPERVISOR and ADMINISTRADOR.
    """
    ProductoService.delete_product(db, id)
    return {"message": "Producto eliminado exitosamente"}


# --- ACCESOS RÁPIDOS ROUTER ---
accesos_rapidos_router = APIRouter()

@accesos_rapidos_router.get("", response_model=List[AccesoRapidoResponse], dependencies=[read_rbac])
def list_quick_access(
    active_only: bool = Query(False, description="Filtrar solo accesos rápidos activos"),
    db: sqlite3.Connection = Depends(get_db)
):
    """Lists all product quick accesses."""
    return AccesoRapidoService.get_all_quick_access(db, active_only)

@accesos_rapidos_router.get("/{id}", response_model=AccesoRapidoResponse, dependencies=[read_rbac])
def get_quick_access(id: str, db: sqlite3.Connection = Depends(get_db)):
    """Gets a specific quick access by ID."""
    return AccesoRapidoService.get_quick_access(db, id)

@accesos_rapidos_router.post("", response_model=AccesoRapidoResponse, status_code=status.HTTP_201_CREATED, dependencies=[write_rbac])
def create_quick_access(ar_in: AccesoRapidoCreate, db: sqlite3.Connection = Depends(get_db)):
    """Creates a new product quick access. Only available to SUPERVISOR and ADMINISTRADOR."""
    return AccesoRapidoService.create_quick_access(db, ar_in)

@accesos_rapidos_router.put("/{id}", response_model=AccesoRapidoResponse, dependencies=[write_rbac])
def update_quick_access(id: str, ar_in: AccesoRapidoCreate, db: sqlite3.Connection = Depends(get_db)):
    """Updates a quick access by ID. Only available to SUPERVISOR and ADMINISTRADOR."""
    return AccesoRapidoService.update_quick_access(db, id, ar_in)

@accesos_rapidos_router.delete("/{id}", status_code=status.HTTP_200_OK, dependencies=[write_rbac])
def delete_quick_access(id: str, db: sqlite3.Connection = Depends(get_db)):
    """Deletes a quick access by ID. Only available to SUPERVISOR and ADMINISTRADOR."""
    AccesoRapidoService.delete_quick_access(db, id)
    return {"message": "Acceso rápido eliminado exitosamente"}
