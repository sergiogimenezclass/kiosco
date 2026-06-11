import sqlite3
from typing import List, Optional
from app.core.errors import KioskException
from app.repositories.catalog import (
    CategoriaRepository,
    MarcaRepository,
    ProveedorRepository,
    ProductoRepository,
    AccesoRapidoRepository
)
from app.schemas.catalog import (
    CategoriaCreate,
    MarcaCreate,
    ProveedorCreate,
    ProductoCreate,
    ProductoUpdate,
    AccesoRapidoCreate
)

# --- CATEGORÍAS ---

class CategoriaService:
    @staticmethod
    def get_category(db: sqlite3.Connection, cat_id: str) -> dict:
        category = CategoriaRepository.get_by_id(db, cat_id)
        if not category:
            raise KioskException(
                code="CATEGORY_NOT_FOUND",
                message="La categoría especificada no existe",
                status_code=404
            )
        return category

    @staticmethod
    def get_all_categories(db: sqlite3.Connection) -> List[dict]:
        return CategoriaRepository.get_all(db)

    @staticmethod
    def create_category(db: sqlite3.Connection, category: CategoriaCreate) -> dict:
        return CategoriaRepository.create(db, category)

    @staticmethod
    def update_category(db: sqlite3.Connection, cat_id: str, category: CategoriaCreate) -> dict:
        # Check existence first
        CategoriaService.get_category(db, cat_id)
        return CategoriaRepository.update(db, cat_id, category)

    @staticmethod
    def delete_category(db: sqlite3.Connection, cat_id: str) -> bool:
        # Check existence first
        CategoriaService.get_category(db, cat_id)
        return CategoriaRepository.delete(db, cat_id)


# --- MARCAS ---

class MarcaService:
    @staticmethod
    def get_brand(db: sqlite3.Connection, brand_id: str) -> dict:
        brand = MarcaRepository.get_by_id(db, brand_id)
        if not brand:
            raise KioskException(
                code="BRAND_NOT_FOUND",
                message="La marca especificada no existe",
                status_code=404
            )
        return brand

    @staticmethod
    def get_all_brands(db: sqlite3.Connection) -> List[dict]:
        return MarcaRepository.get_all(db)

    @staticmethod
    def create_brand(db: sqlite3.Connection, brand: MarcaCreate) -> dict:
        return MarcaRepository.create(db, brand)

    @staticmethod
    def update_brand(db: sqlite3.Connection, brand_id: str, brand: MarcaCreate) -> dict:
        # Check existence first
        MarcaService.get_brand(db, brand_id)
        return MarcaRepository.update(db, brand_id, brand)

    @staticmethod
    def delete_brand(db: sqlite3.Connection, brand_id: str) -> bool:
        # Check existence first
        MarcaService.get_brand(db, brand_id)
        return MarcaRepository.delete(db, brand_id)


# --- PROVEEDORES ---

class ProveedorService:
    @staticmethod
    def get_provider(db: sqlite3.Connection, prov_id: str) -> dict:
        provider = ProveedorRepository.get_by_id(db, prov_id)
        if not provider:
            raise KioskException(
                code="PROVIDER_NOT_FOUND",
                message="El proveedor especificado no existe",
                status_code=404
            )
        return provider

    @staticmethod
    def get_all_providers(db: sqlite3.Connection) -> List[dict]:
        return ProveedorRepository.get_all(db)

    @staticmethod
    def create_provider(db: sqlite3.Connection, provider: ProveedorCreate) -> dict:
        return ProveedorRepository.create(db, provider)

    @staticmethod
    def update_provider(db: sqlite3.Connection, prov_id: str, provider: ProveedorCreate) -> dict:
        # Check existence first
        ProveedorService.get_provider(db, prov_id)
        return ProveedorRepository.update(db, prov_id, provider)

    @staticmethod
    def delete_provider(db: sqlite3.Connection, prov_id: str) -> bool:
        # Check existence first
        ProveedorService.get_provider(db, prov_id)
        return ProveedorRepository.delete(db, prov_id)


# --- PRODUCTOS ---

class ProductoService:
    @staticmethod
    def get_product(db: sqlite3.Connection, prod_id: str) -> dict:
        product = ProductoRepository.get_by_id(db, prod_id)
        if not product:
            raise KioskException(
                code="PRODUCT_NOT_FOUND",
                message="El producto especificado no existe",
                status_code=404
            )
        return product

    @staticmethod
    def get_product_by_barcode(db: sqlite3.Connection, barcode: str) -> dict:
        product = ProductoRepository.get_by_barcode(db, barcode)
        if not product:
            raise KioskException(
                code="PRODUCT_NOT_FOUND",
                message=f"No se encontró ningún producto con el código de barras '{barcode}'",
                status_code=404
            )
        return product

    @staticmethod
    def get_all_products(
        db: sqlite3.Connection,
        q: Optional[str] = None,
        categoria_id: Optional[str] = None,
        marca_id: Optional[str] = None,
        activo: Optional[int] = None
    ) -> List[dict]:
        return ProductoRepository.get_all(db, q, categoria_id, marca_id, activo)

    @staticmethod
    def create_product(db: sqlite3.Connection, prod: ProductoCreate) -> dict:
        # Validate business logic constraints
        if prod.precio_venta_centavos <= 0:
            raise KioskException(
                code="INVALID_PRICE",
                message="El precio de venta debe ser mayor a cero centavos",
                status_code=400
            )
        if prod.stock_actual < 0:
            raise KioskException(
                code="INVALID_STOCK",
                message="El stock actual no puede ser negativo",
                status_code=400
            )
        if prod.stock_minimo < 0:
            raise KioskException(
                code="INVALID_STOCK",
                message="El stock mínimo no puede ser negativo",
                status_code=400
            )
            
        return ProductoRepository.create(db, prod)

    @staticmethod
    def update_product(db: sqlite3.Connection, prod_id: str, prod: ProductoUpdate) -> dict:
        # Check existence first
        ProductoService.get_product(db, prod_id)
        
        # Validate business logic constraints if provided
        if prod.precio_venta_centavos is not None and prod.precio_venta_centavos <= 0:
            raise KioskException(
                code="INVALID_PRICE",
                message="El precio de venta debe ser mayor a cero centavos",
                status_code=400
            )
        if prod.stock_actual is not None and prod.stock_actual < 0:
            raise KioskException(
                code="INVALID_STOCK",
                message="El stock actual no puede ser negativo",
                status_code=400
            )
        if prod.stock_minimo is not None and prod.stock_minimo < 0:
            raise KioskException(
                code="INVALID_STOCK",
                message="El stock mínimo no puede ser negativo",
                status_code=400
            )
            
        return ProductoRepository.update(db, prod_id, prod)

    @staticmethod
    def delete_product(db: sqlite3.Connection, prod_id: str) -> bool:
        # Checks existences and database constraints in Repository layer
        return ProductoRepository.delete(db, prod_id)


# --- ACCESOS RÁPIDOS ---

class AccesoRapidoService:
    @staticmethod
    def get_quick_access(db: sqlite3.Connection, ar_id: str) -> dict:
        ar = AccesoRapidoRepository.get_by_id(db, ar_id)
        if not ar:
            raise KioskException(
                code="QUICK_ACCESS_NOT_FOUND",
                message="El acceso rápido especificado no existe",
                status_code=404
            )
        return ar

    @staticmethod
    def get_all_quick_access(db: sqlite3.Connection, active_only: bool = False) -> List[dict]:
        return AccesoRapidoRepository.get_all(db, active_only)

    @staticmethod
    def create_quick_access(db: sqlite3.Connection, ar: AccesoRapidoCreate) -> dict:
        return AccesoRapidoRepository.create(db, ar)

    @staticmethod
    def update_quick_access(db: sqlite3.Connection, ar_id: str, ar: AccesoRapidoCreate) -> dict:
        # Check existence first
        AccesoRapidoService.get_quick_access(db, ar_id)
        return AccesoRapidoRepository.update(db, ar_id, ar)

    @staticmethod
    def delete_quick_access(db: sqlite3.Connection, ar_id: str) -> bool:
        # Check existence first
        AccesoRapidoService.get_quick_access(db, ar_id)
        return AccesoRapidoRepository.delete(db, ar_id)
