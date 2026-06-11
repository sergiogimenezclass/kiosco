import sqlite3
import uuid
import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from app.core.errors import KioskException
from app.schemas.catalog import (
    CategoriaCreate,
    MarcaCreate,
    ProveedorCreate,
    ProductoCreate,
    ProductoUpdate,
    AccesoRapidoCreate
)

# --- CATEGORÍAS ---

class CategoriaRepository:
    @staticmethod
    def get_by_id(conn: sqlite3.Connection, cat_id: str) -> Optional[dict]:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre FROM categorias WHERE id = ?;", (cat_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_by_name(conn: sqlite3.Connection, nombre: str) -> Optional[dict]:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre FROM categorias WHERE nombre = ?;", (nombre.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_all(conn: sqlite3.Connection) -> List[dict]:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre FROM categorias;")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def create(conn: sqlite3.Connection, category: CategoriaCreate) -> dict:
        cursor = conn.cursor()
        cat_id = uuid.uuid4().hex
        try:
            cursor.execute(
                "INSERT INTO categorias (id, nombre) VALUES (?, ?);",
                (cat_id, category.nombre.strip())
            )
            return {"id": cat_id, "nombre": category.nombre.strip()}
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e) or "nombre" in str(e):
                raise KioskException(
                    code="CATEGORY_ALREADY_EXISTS",
                    message=f"La categoría '{category.nombre}' ya está registrada",
                    status_code=409
                )
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al guardar la categoría: {str(e)}",
                status_code=500
            )

    @staticmethod
    def update(conn: sqlite3.Connection, cat_id: str, category: CategoriaCreate) -> dict:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE categorias SET nombre = ? WHERE id = ?;",
                (category.nombre.strip(), cat_id)
            )
            if cursor.rowcount == 0:
                raise KioskException(
                    code="CATEGORY_NOT_FOUND",
                    message="La categoría especificada no existe",
                    status_code=404
                )
            return {"id": cat_id, "nombre": category.nombre.strip()}
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e) or "nombre" in str(e):
                raise KioskException(
                    code="CATEGORY_ALREADY_EXISTS",
                    message=f"La categoría '{category.nombre}' ya está registrada",
                    status_code=409
                )
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al actualizar la categoría: {str(e)}",
                status_code=500
            )

    @staticmethod
    def delete(conn: sqlite3.Connection, cat_id: str) -> bool:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM categorias WHERE id = ?;", (cat_id,))
            if cursor.rowcount == 0:
                raise KioskException(
                    code="CATEGORY_NOT_FOUND",
                    message="La categoría especificada no existe",
                    status_code=404
                )
            return True
        except sqlite3.IntegrityError as e:
            if "FOREIGN KEY" in str(e):
                raise KioskException(
                    code="CATEGORY_HAS_PRODUCTS",
                    message="No se puede eliminar la categoría porque tiene productos asociados",
                    status_code=400
                )
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al eliminar la categoría: {str(e)}",
                status_code=500
            )


# --- MARCAS ---

class MarcaRepository:
    @staticmethod
    def get_by_id(conn: sqlite3.Connection, brand_id: str) -> Optional[dict]:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre FROM marcas WHERE id = ?;", (brand_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_by_name(conn: sqlite3.Connection, nombre: str) -> Optional[dict]:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre FROM marcas WHERE nombre = ?;", (nombre.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_all(conn: sqlite3.Connection) -> List[dict]:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre FROM marcas;")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def create(conn: sqlite3.Connection, brand: MarcaCreate) -> dict:
        cursor = conn.cursor()
        brand_id = uuid.uuid4().hex
        try:
            cursor.execute(
                "INSERT INTO marcas (id, nombre) VALUES (?, ?);",
                (brand_id, brand.nombre.strip())
            )
            return {"id": brand_id, "nombre": brand.nombre.strip()}
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e) or "nombre" in str(e):
                raise KioskException(
                    code="BRAND_ALREADY_EXISTS",
                    message=f"La marca '{brand.nombre}' ya está registrada",
                    status_code=409
                )
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al guardar la marca: {str(e)}",
                status_code=500
            )

    @staticmethod
    def update(conn: sqlite3.Connection, brand_id: str, brand: MarcaCreate) -> dict:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE marcas SET nombre = ? WHERE id = ?;",
                (brand.nombre.strip(), brand_id)
            )
            if cursor.rowcount == 0:
                raise KioskException(
                    code="BRAND_NOT_FOUND",
                    message="La marca especificada no existe",
                    status_code=404
                )
            return {"id": brand_id, "nombre": brand.nombre.strip()}
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e) or "nombre" in str(e):
                raise KioskException(
                    code="BRAND_ALREADY_EXISTS",
                    message=f"La marca '{brand.nombre}' ya está registrada",
                    status_code=409
                )
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al actualizar la marca: {str(e)}",
                status_code=500
            )

    @staticmethod
    def delete(conn: sqlite3.Connection, brand_id: str) -> bool:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM marcas WHERE id = ?;", (brand_id,))
            if cursor.rowcount == 0:
                raise KioskException(
                    code="BRAND_NOT_FOUND",
                    message="La marca especificada no existe",
                    status_code=404
                )
            return True
        except sqlite3.IntegrityError as e:
            if "FOREIGN KEY" in str(e):
                raise KioskException(
                    code="BRAND_HAS_PRODUCTS",
                    message="No se puede eliminar la marca porque tiene productos asociados",
                    status_code=400
                )
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al eliminar la marca: {str(e)}",
                status_code=500
            )


# --- PROVEEDORES ---

class ProveedorRepository:
    @staticmethod
    def get_by_id(conn: sqlite3.Connection, prov_id: str) -> Optional[dict]:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, telefono, email FROM proveedores WHERE id = ?;", (prov_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_all(conn: sqlite3.Connection) -> List[dict]:
        cursor = conn.cursor()
        cursor.execute("SELECT id, nombre, telefono, email FROM proveedores;")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def create(conn: sqlite3.Connection, provider: ProveedorCreate) -> dict:
        cursor = conn.cursor()
        prov_id = uuid.uuid4().hex
        try:
            cursor.execute(
                """
                INSERT INTO proveedores (id, nombre, telefono, email)
                VALUES (?, ?, ?, ?);
                """,
                (prov_id, provider.nombre.strip(), provider.telefono, provider.email)
            )
            return {
                "id": prov_id,
                "nombre": provider.nombre.strip(),
                "telefono": provider.telefono,
                "email": provider.email
            }
        except sqlite3.IntegrityError as e:
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al guardar el proveedor: {str(e)}",
                status_code=500
            )

    @staticmethod
    def update(conn: sqlite3.Connection, prov_id: str, provider: ProveedorCreate) -> dict:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                UPDATE proveedores
                SET nombre = ?, telefono = ?, email = ?
                WHERE id = ?;
                """,
                (provider.nombre.strip(), provider.telefono, provider.email, prov_id)
            )
            if cursor.rowcount == 0:
                raise KioskException(
                    code="PROVIDER_NOT_FOUND",
                    message="El proveedor especificado no existe",
                    status_code=404
                )
            return {
                "id": prov_id,
                "nombre": provider.nombre.strip(),
                "telefono": provider.telefono,
                "email": provider.email
            }
        except sqlite3.IntegrityError as e:
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al actualizar el proveedor: {str(e)}",
                status_code=500
            )

    @staticmethod
    def delete(conn: sqlite3.Connection, prov_id: str) -> bool:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM proveedores WHERE id = ?;", (prov_id,))
            if cursor.rowcount == 0:
                raise KioskException(
                    code="PROVIDER_NOT_FOUND",
                    message="El proveedor especificado no existe",
                    status_code=404
                )
            return True
        except sqlite3.IntegrityError as e:
            if "FOREIGN KEY" in str(e):
                raise KioskException(
                    code="PROVIDER_HAS_ASSOCIATED_DATA",
                    message="No se puede eliminar el proveedor porque tiene productos o movimientos asociados",
                    status_code=400
                )
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al eliminar el proveedor: {str(e)}",
                status_code=500
            )


# --- PRODUCTOS Y CÓDIGOS DE BARRA ---

class ProductoRepository:
    @staticmethod
    def get_by_id(conn: sqlite3.Connection, prod_id: str) -> Optional[dict]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, nombre, descripcion, categoria_id, marca_id, proveedor_id,
                   precio_venta_centavos, stock_actual, stock_minimo, unidad_medida,
                   imagen_url, activo, created_at, updated_at
            FROM productos WHERE id = ?;
            """,
            (prod_id,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        
        product = dict(row)
        
        # Get barcodes
        cursor.execute(
            "SELECT codigo FROM codigos_barras WHERE producto_id = ? ORDER BY principal DESC;",
            (prod_id,)
        )
        barcodes = [r["codigo"] for r in cursor.fetchall()]
        product["codigos_barras"] = barcodes
        return product

    @staticmethod
    def get_by_barcode(conn: sqlite3.Connection, barcode: str) -> Optional[dict]:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT producto_id FROM codigos_barras WHERE codigo = ?;",
            (barcode.strip(),)
        )
        row = cursor.fetchone()
        if not row:
            return None
        
        return ProductoRepository.get_by_id(conn, row["producto_id"])

    @staticmethod
    def get_all(
        conn: sqlite3.Connection,
        q: Optional[str] = None,
        categoria_id: Optional[str] = None,
        marca_id: Optional[str] = None,
        activo: Optional[int] = None
    ) -> List[dict]:
        cursor = conn.cursor()
        query = """
            SELECT id, nombre, descripcion, categoria_id, marca_id, proveedor_id,
                   precio_venta_centavos, stock_actual, stock_minimo, unidad_medida,
                   imagen_url, activo, created_at, updated_at
            FROM productos
            WHERE 1=1
        """
        params = []
        
        if q:
            # We can search by name or barcode
            query += " AND (nombre LIKE ? OR id IN (SELECT producto_id FROM codigos_barras WHERE codigo LIKE ?))"
            like_q = f"%{q.strip()}%"
            params.extend([like_q, like_q])
            
        if categoria_id:
            query += " AND categoria_id = ?"
            params.append(categoria_id)
            
        if marca_id:
            query += " AND marca_id = ?"
            params.append(marca_id)
            
        if activo is not None:
            query += " AND activo = ?"
            params.append(activo)
            
        query += " ORDER BY nombre ASC;"
        
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        
        products = []
        for row in rows:
            prod = dict(row)
            # Fetch barcodes for this product
            cursor.execute(
                "SELECT codigo FROM codigos_barras WHERE producto_id = ? ORDER BY principal DESC;",
                (prod["id"],)
            )
            prod["codigos_barras"] = [r["codigo"] for r in cursor.fetchall()]
            products.append(prod)
            
        return products

    @staticmethod
    def create(conn: sqlite3.Connection, prod: ProductoCreate, prod_id: Optional[str] = None) -> dict:
        cursor = conn.cursor()
        if not prod_id:
            prod_id = uuid.uuid4().hex
            
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        try:
            # Check Category exists
            cursor.execute("SELECT id FROM categorias WHERE id = ?;", (prod.categoria_id,))
            if not cursor.fetchone():
                raise KioskException(
                    code="CATEGORY_NOT_FOUND",
                    message="La categoría especificada no existe",
                    status_code=404
                )
                
            # Check Brand exists if provided
            if prod.marca_id:
                cursor.execute("SELECT id FROM marcas WHERE id = ?;", (prod.marca_id,))
                if not cursor.fetchone():
                    raise KioskException(
                        code="BRAND_NOT_FOUND",
                        message="La marca especificada no existe",
                        status_code=404
                    )
                    
            # Check Provider exists if provided
            if prod.proveedor_id:
                cursor.execute("SELECT id FROM proveedores WHERE id = ?;", (prod.proveedor_id,))
                if not cursor.fetchone():
                    raise KioskException(
                        code="PROVIDER_NOT_FOUND",
                        message="El proveedor especificado no existe",
                        status_code=404
                    )

            # Insert product
            cursor.execute(
                """
                INSERT INTO productos (
                    id, nombre, descripcion, categoria_id, marca_id, proveedor_id,
                    precio_venta_centavos, stock_actual, stock_minimo, unidad_medida,
                    imagen_url, activo, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    prod_id,
                    prod.nombre.strip(),
                    prod.descripcion,
                    prod.categoria_id,
                    prod.marca_id,
                    prod.proveedor_id,
                    prod.precio_venta_centavos,
                    prod.stock_actual,
                    prod.stock_minimo,
                    prod.unidad_medida.value,
                    prod.imagen_url,
                    prod.activo,
                    now_str,
                    now_str
                )
            )
            
            # Insert barcodes
            if prod.codigos_barras:
                for idx, code in enumerate(prod.codigos_barras):
                    code_strip = code.strip()
                    if not code_strip:
                        continue
                    # First barcode is principal
                    principal = 1 if idx == 0 else 0
                    
                    # Verify uniqueness
                    cursor.execute("SELECT id FROM codigos_barras WHERE codigo = ?;", (code_strip,))
                    if cursor.fetchone():
                        raise KioskException(
                            code="BARCODE_ALREADY_EXISTS",
                            message=f"El código de barras '{code_strip}' ya está asignado a otro producto",
                            status_code=409
                        )
                        
                    cursor.execute(
                        """
                        INSERT INTO codigos_barras (id, producto_id, codigo, principal)
                        VALUES (?, ?, ?, ?);
                        """,
                        (uuid.uuid4().hex, prod_id, code_strip, principal)
                    )
            
            # Return fresh product details
            return {
                "id": prod_id,
                "nombre": prod.nombre.strip(),
                "descripcion": prod.descripcion,
                "categoria_id": prod.categoria_id,
                "marca_id": prod.marca_id,
                "proveedor_id": prod.proveedor_id,
                "precio_venta_centavos": prod.precio_venta_centavos,
                "stock_actual": prod.stock_actual,
                "stock_minimo": prod.stock_minimo,
                "unidad_medida": prod.unidad_medida,
                "imagen_url": prod.imagen_url,
                "activo": prod.activo,
                "created_at": now_str,
                "updated_at": now_str,
                "codigos_barras": [c.strip() for c in prod.codigos_barras if c.strip()]
            }
        except KioskException:
            raise
        except sqlite3.IntegrityError as e:
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error de integridad en la base de datos: {str(e)}",
                status_code=500
            )

    @staticmethod
    def update(conn: sqlite3.Connection, prod_id: str, prod: ProductoUpdate) -> dict:
        cursor = conn.cursor()
        
        # Check if product exists
        cursor.execute("SELECT created_at FROM productos WHERE id = ?;", (prod_id,))
        row = cursor.fetchone()
        if not row:
            raise KioskException(
                code="PRODUCT_NOT_FOUND",
                message="El producto especificado no existe",
                status_code=404
            )
        created_at = row["created_at"]
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        try:
            # Validate IDs if provided
            if prod.categoria_id:
                cursor.execute("SELECT id FROM categorias WHERE id = ?;", (prod.categoria_id,))
                if not cursor.fetchone():
                    raise KioskException(
                        code="CATEGORY_NOT_FOUND",
                        message="La categoría especificada no existe",
                        status_code=404
                    )
            if prod.marca_id:
                cursor.execute("SELECT id FROM marcas WHERE id = ?;", (prod.marca_id,))
                if not cursor.fetchone():
                    raise KioskException(
                        code="BRAND_NOT_FOUND",
                        message="La marca especificada no existe",
                        status_code=404
                    )
            if prod.proveedor_id:
                cursor.execute("SELECT id FROM proveedores WHERE id = ?;", (prod.proveedor_id,))
                if not cursor.fetchone():
                    raise KioskException(
                        code="PROVIDER_NOT_FOUND",
                        message="El proveedor especificado no existe",
                        status_code=404
                    )

            # Build UPDATE fields dynamically
            fields = []
            values = []
            
            update_data = prod.model_dump(exclude_unset=True)
            # Remove codigos_barras from direct update
            barcodes_to_update = update_data.pop("codigos_barras", None)
            
            for k, v in update_data.items():
                fields.append(f"{k} = ?")
                if isinstance(v, Enum):
                    values.append(v.value)
                elif isinstance(v, str) and k == "nombre":
                    values.append(v.strip())
                else:
                    values.append(v)
                    
            if fields:
                fields.append("updated_at = ?")
                values.append(now_str)
                values.append(prod_id)
                
                query = f"UPDATE productos SET {', '.join(fields)} WHERE id = ?;"
                cursor.execute(query, tuple(values))

            # Handle barcodes if provided
            if barcodes_to_update is not None:
                # Filter out empty entries
                barcodes_to_update = [c.strip() for c in barcodes_to_update if c.strip()]
                
                # Check that they aren't already used by OTHER products
                for code in barcodes_to_update:
                    cursor.execute(
                        "SELECT id FROM codigos_barras WHERE codigo = ? AND producto_id != ?;",
                        (code, prod_id)
                    )
                    if cursor.fetchone():
                        raise KioskException(
                            code="BARCODE_ALREADY_EXISTS",
                            message=f"El código de barras '{code}' ya está asignado a otro producto",
                            status_code=409
                        )
                
                # Delete old barcodes
                cursor.execute("DELETE FROM codigos_barras WHERE producto_id = ?;", (prod_id,))
                
                # Insert new ones
                for idx, code in enumerate(barcodes_to_update):
                    principal = 1 if idx == 0 else 0
                    cursor.execute(
                        """
                        INSERT INTO codigos_barras (id, producto_id, codigo, principal)
                        VALUES (?, ?, ?, ?);
                        """,
                        (uuid.uuid4().hex, prod_id, code, principal)
                    )

            return ProductoRepository.get_by_id(conn, prod_id)
            
        except KioskException:
            raise
        except sqlite3.IntegrityError as e:
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al actualizar el producto: {str(e)}",
                status_code=500
            )

    @staticmethod
    def delete(conn: sqlite3.Connection, prod_id: str) -> bool:
        cursor = conn.cursor()
        
        # Check if product exists
        cursor.execute("SELECT id FROM productos WHERE id = ?;", (prod_id,))
        if not cursor.fetchone():
            raise KioskException(
                code="PRODUCT_NOT_FOUND",
                message="El producto especificado no existe",
                status_code=404
            )
            
        # Check history
        cursor.execute("SELECT COUNT(*) FROM venta_detalles WHERE producto_id = ?;", (prod_id,))
        sales_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM movimientos_stock WHERE producto_id = ?;", (prod_id,))
        stock_count = cursor.fetchone()[0]
        
        if sales_count > 0 or stock_count > 0:
            raise KioskException(
                code="PRODUCT_HAS_HISTORY",
                message="No se puede eliminar el producto porque tiene movimientos de stock o ventas asociadas",
                status_code=400
            )
            
        try:
            # Delete barcodes first
            cursor.execute("DELETE FROM codigos_barras WHERE producto_id = ?;", (prod_id,))
            # Delete quick accesses
            cursor.execute("DELETE FROM accesos_rapidos WHERE producto_id = ?;", (prod_id,))
            # Delete product
            cursor.execute("DELETE FROM productos WHERE id = ?;", (prod_id,))
            return True
        except sqlite3.IntegrityError as e:
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al eliminar el producto: {str(e)}",
                status_code=500
            )


# --- ACCESOS RÁPIDOS ---

class AccesoRapidoRepository:
    @staticmethod
    def get_by_id(conn: sqlite3.Connection, ar_id: str) -> Optional[dict]:
        cursor = conn.cursor()
        cursor.execute("SELECT id, producto_id, etiqueta, orden, activo FROM accesos_rapidos WHERE id = ?;", (ar_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

    @staticmethod
    def get_all(conn: sqlite3.Connection, active_only: bool = False) -> List[dict]:
        cursor = conn.cursor()
        query = "SELECT id, producto_id, etiqueta, orden, activo FROM accesos_rapidos"
        if active_only:
            query += " WHERE activo = 1"
        query += " ORDER BY orden ASC;"
        cursor.execute(query)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def create(conn: sqlite3.Connection, ar: AccesoRapidoCreate) -> dict:
        cursor = conn.cursor()
        ar_id = uuid.uuid4().hex
        
        # Check if product exists
        cursor.execute("SELECT id FROM productos WHERE id = ?;", (ar.producto_id,))
        if not cursor.fetchone():
            raise KioskException(
                code="PRODUCT_NOT_FOUND",
                message="El producto especificado para acceso rápido no existe",
                status_code=404
            )
            
        try:
            cursor.execute(
                """
                INSERT INTO accesos_rapidos (id, producto_id, etiqueta, orden, activo)
                VALUES (?, ?, ?, ?, ?);
                """,
                (ar_id, ar.producto_id, ar.etiqueta.strip(), ar.orden, ar.activo)
            )
            return {
                "id": ar_id,
                "producto_id": ar.producto_id,
                "etiqueta": ar.etiqueta.strip(),
                "orden": ar.orden,
                "activo": ar.activo
            }
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e) or "orden" in str(e):
                raise KioskException(
                    code="ORDER_ALREADY_TAKEN",
                    message=f"El orden '{ar.orden}' ya está asignado a otro acceso rápido",
                    status_code=409
                )
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al guardar el acceso rápido: {str(e)}",
                status_code=500
            )

    @staticmethod
    def update(conn: sqlite3.Connection, ar_id: str, ar: AccesoRapidoCreate) -> dict:
        cursor = conn.cursor()
        
        # Check if exists
        cursor.execute("SELECT id FROM accesos_rapidos WHERE id = ?;", (ar_id,))
        if not cursor.fetchone():
            raise KioskException(
                code="QUICK_ACCESS_NOT_FOUND",
                message="El acceso rápido especificado no existe",
                status_code=404
            )
            
        # Check if product exists
        cursor.execute("SELECT id FROM productos WHERE id = ?;", (ar.producto_id,))
        if not cursor.fetchone():
            raise KioskException(
                code="PRODUCT_NOT_FOUND",
                message="El producto especificado para acceso rápido no existe",
                status_code=404
            )
            
        try:
            cursor.execute(
                """
                UPDATE accesos_rapidos
                SET producto_id = ?, etiqueta = ?, orden = ?, activo = ?
                WHERE id = ?;
                """,
                (ar.producto_id, ar.etiqueta.strip(), ar.orden, ar.activo, ar_id)
            )
            return {
                "id": ar_id,
                "producto_id": ar.producto_id,
                "etiqueta": ar.etiqueta.strip(),
                "orden": ar.orden,
                "activo": ar.activo
            }
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e) or "orden" in str(e):
                raise KioskException(
                    code="ORDER_ALREADY_TAKEN",
                    message=f"El orden '{ar.orden}' ya está asignado a otro acceso rápido",
                    status_code=409
                )
            raise KioskException(
                code="DATABASE_ERROR",
                message=f"Error al actualizar el acceso rápido: {str(e)}",
                status_code=500
            )

    @staticmethod
    def delete(conn: sqlite3.Connection, ar_id: str) -> bool:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM accesos_rapidos WHERE id = ?;", (ar_id,))
        if cursor.rowcount == 0:
            raise KioskException(
                code="QUICK_ACCESS_NOT_FOUND",
                message="El acceso rápido especificado no existe",
                status_code=404
            )
        return True
