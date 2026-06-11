import os
import sys
import uuid
import sqlite3
from datetime import datetime, timezone

# Add project root to sys.path to allow absolute imports of app
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the database context manager
from app.core.database import get_db_conn

# Mock data definition
CATEGORIAS = [
    "Alfajores",
    "Golosinas",
    "Gaseosas",
    "Yerba y Té",
    "Bebidas Alcohólicas",
    "Snacks",
    "Galletitas"
]

MARCAS = [
    "Guaymallén",
    "Jorgito",
    "Havanna",
    "Arcor",
    "Terrabusi",
    "Bagley",
    "Coca-Cola",
    "Manaos",
    "Quilmes",
    "PepsiCo",
    "Playadito",
    "Taragüí",
    "Fernet Branca"
]

PROVEEDORES = [
    {
        "nombre": "Mayorista San Martín",
        "telefono": "11-4567-8901",
        "email": "contacto@mayoristasanmartin.com"
    },
    {
        "nombre": "Distribuidora El Trece",
        "telefono": "11-2345-6789",
        "email": "ventas@distribuidoraeltrece.com.ar"
    },
    {
        "nombre": "Distribuidora Golópolis",
        "telefono": "11-9876-5432",
        "email": "golopolis@distribuidores.com"
    }
]

PRODUCTOS = [
    {
        "nombre": "Alfajor Guaymallén Chocolate",
        "descripcion": "Alfajor triple relleno de dulce de leche con baño de repostería fantasía chocolate negro.",
        "categoria": "Alfajores",
        "marca": "Guaymallén",
        "proveedor": "Distribuidora Golópolis",
        "precio_venta_centavos": 80000,
        "stock_actual": 50,
        "stock_minimo": 10,
        "unidad_medida": "UNIDAD",
        "codigo_barras": "7790060023456"
    },
    {
        "nombre": "Alfajor Jorgito Negro",
        "descripcion": "Alfajor de chocolate relleno de dulce de leche clásico de 50g.",
        "categoria": "Alfajores",
        "marca": "Jorgito",
        "proveedor": "Distribuidora Golópolis",
        "precio_venta_centavos": 100000,
        "stock_actual": 40,
        "stock_minimo": 8,
        "unidad_medida": "UNIDAD",
        "codigo_barras": "7790080012345"
    },
    {
        "nombre": "Alfajor Havanna Mixto",
        "descripcion": "Alfajor premium de chocolate y merengue relleno de abundante dulce de leche.",
        "categoria": "Alfajores",
        "marca": "Havanna",
        "proveedor": "Mayorista San Martín",
        "precio_venta_centavos": 250000,
        "stock_actual": 20,
        "stock_minimo": 5,
        "unidad_medida": "UNIDAD",
        "codigo_barras": "7791234567890"
    },
    {
        "nombre": "Chupetín Pico Dulce",
        "descripcion": "Chupetín de caramelo duro sabor tutti-frutti clásico de la infancia.",
        "categoria": "Golosinas",
        "marca": "Arcor",
        "proveedor": "Distribuidora Golópolis",
        "precio_venta_centavos": 25000,
        "stock_actual": 150,
        "stock_minimo": 30,
        "unidad_medida": "UNIDAD",
        "codigo_barras": "7790580121212"
    },
    {
        "nombre": "Caramelos Masticables Surtidos 150g",
        "descripcion": "Bolsa de caramelos masticables surtidos de frutas marca Arcor.",
        "categoria": "Golosinas",
        "marca": "Arcor",
        "proveedor": "Distribuidora Golópolis",
        "precio_venta_centavos": 120000,
        "stock_actual": 30,
        "stock_minimo": 5,
        "unidad_medida": "GRAMO",
        "codigo_barras": "7790580343434"
    },
    {
        "nombre": "Chocolate Shot",
        "descripcion": "Tableta de chocolate con leche con maní crujiente.",
        "categoria": "Golosinas",
        "marca": "Arcor",
        "proveedor": "Distribuidora Golópolis",
        "precio_venta_centavos": 180000,
        "stock_actual": 25,
        "stock_minimo": 5,
        "unidad_medida": "UNIDAD",
        "codigo_barras": "7790580565656"
    },
    {
        "nombre": "Gaseosa Coca-Cola Original 1.5L",
        "descripcion": "Bebida sin alcohol gaseosa refrescante sabor original cola.",
        "categoria": "Gaseosas",
        "marca": "Coca-Cola",
        "proveedor": "Distribuidora El Trece",
        "precio_venta_centavos": 240000,
        "stock_actual": 24,
        "stock_minimo": 6,
        "unidad_medida": "MILILITRO",
        "codigo_barras": "7790895000997"
    },
    {
        "nombre": "Gaseosa Manaos Cola 2.25L",
        "descripcion": "Bebida sin alcohol sabor cola de industria nacional argentina.",
        "categoria": "Gaseosas",
        "marca": "Manaos",
        "proveedor": "Distribuidora El Trece",
        "precio_venta_centavos": 140000,
        "stock_actual": 36,
        "stock_minimo": 12,
        "unidad_medida": "MILILITRO",
        "codigo_barras": "7798158020012"
    },
    {
        "nombre": "Cerveza Quilmes Clásica Lata 473ml",
        "descripcion": "Cerveza rubia lager argentina clásica.",
        "categoria": "Bebidas Alcohólicas",
        "marca": "Quilmes",
        "proveedor": "Distribuidora El Trece",
        "precio_venta_centavos": 180000,
        "stock_actual": 48,
        "stock_minimo": 12,
        "unidad_medida": "MILILITRO",
        "codigo_barras": "7792798000789"
    },
    {
        "nombre": "Fernet Branca 750ml",
        "descripcion": "Aperitivo de hierbas Fernet Branca original de 750ml.",
        "categoria": "Bebidas Alcohólicas",
        "marca": "Fernet Branca",
        "proveedor": "Mayorista San Martín",
        "precio_venta_centavos": 850000,
        "stock_actual": 12,
        "stock_minimo": 3,
        "unidad_medida": "MILILITRO",
        "codigo_barras": "7791475000012"
    },
    {
        "nombre": "Yerba Mate Playadito 1kg",
        "descripcion": "Yerba mate tradicional suave con palo originaria de Corrientes.",
        "categoria": "Yerba y Té",
        "marca": "Playadito",
        "proveedor": "Mayorista San Martín",
        "precio_venta_centavos": 420000,
        "stock_actual": 15,
        "stock_minimo": 4,
        "unidad_medida": "GRAMO",
        "codigo_barras": "7790253120150"
    },
    {
        "nombre": "Yerba Mate Taragüí con Palo 500g",
        "descripcion": "Yerba mate clásica con palo sabor intenso y rendidor.",
        "categoria": "Yerba y Té",
        "marca": "Taragüí",
        "proveedor": "Mayorista San Martín",
        "precio_venta_centavos": 230000,
        "stock_actual": 20,
        "stock_minimo": 5,
        "unidad_medida": "GRAMO",
        "codigo_barras": "7790387013212"
    },
    {
        "nombre": "Papas Fritas Lays Clásicas 150g",
        "descripcion": "Papas fritas saladas crujientes clásicas de copetín.",
        "categoria": "Snacks",
        "marca": "PepsiCo",
        "proveedor": "Distribuidora El Trece",
        "precio_venta_centavos": 200000,
        "stock_actual": 18,
        "stock_minimo": 5,
        "unidad_medida": "GRAMO",
        "codigo_barras": "7790310000150"
    },
    {
        "nombre": "Doritos Queso 150g",
        "descripcion": "Snack de tortillas de maíz con sabor a queso intenso.",
        "categoria": "Snacks",
        "marca": "PepsiCo",
        "proveedor": "Distribuidora El Trece",
        "precio_venta_centavos": 220000,
        "stock_actual": 15,
        "stock_minimo": 5,
        "unidad_medida": "GRAMO",
        "codigo_barras": "7790310001232"
    },
    {
        "nombre": "Galletitas Surtido Bagley 400g",
        "descripcion": "Variedad de galletitas dulces clásicas surtidas marca Bagley.",
        "categoria": "Galletitas",
        "marca": "Bagley",
        "proveedor": "Distribuidora Golópolis",
        "precio_venta_centavos": 160000,
        "stock_actual": 30,
        "stock_minimo": 8,
        "unidad_medida": "GRAMO",
        "codigo_barras": "7790040003058"
    },
    {
        "nombre": "Galletitas Criollitas Terrabusi",
        "descripcion": "Galletitas de agua hojaldradas paquete individual.",
        "categoria": "Galletitas",
        "marca": "Terrabusi",
        "proveedor": "Mayorista San Martín",
        "precio_venta_centavos": 70000,
        "stock_actual": 40,
        "stock_minimo": 10,
        "unidad_medida": "UNIDAD",
        "codigo_barras": "7790060002123"
    }
]

def seed_database():
    print("Iniciando la carga de datos de prueba en la base de datos...")
    
    with get_db_conn() as conn:
        cursor = conn.cursor()
        
        # 1. Cargar Categorías de manera idempotente
        print("\nCargando categorías...")
        categoria_id_map = {}
        for cat_nombre in CATEGORIAS:
            cursor.execute("SELECT id FROM categorias WHERE nombre = ?;", (cat_nombre,))
            row = cursor.fetchone()
            if row:
                cat_id = row[0]
                print(f"  Categoría ya existente: {cat_nombre} (ID: {cat_id})")
            else:
                cat_id = uuid.uuid4().hex
                cursor.execute(
                    "INSERT INTO categorias (id, nombre) VALUES (?, ?);",
                    (cat_id, cat_nombre)
                )
                print(f"  Categoría creada: {cat_nombre} (ID: {cat_id})")
            categoria_id_map[cat_nombre] = cat_id

        # 2. Cargar Marcas de manera idempotente
        print("\nCargando marcas...")
        marca_id_map = {}
        for mar_nombre in MARCAS:
            cursor.execute("SELECT id FROM marcas WHERE nombre = ?;", (mar_nombre,))
            row = cursor.fetchone()
            if row:
                mar_id = row[0]
                print(f"  Marca ya existente: {mar_nombre} (ID: {mar_id})")
            else:
                mar_id = uuid.uuid4().hex
                cursor.execute(
                    "INSERT INTO marcas (id, nombre) VALUES (?, ?);",
                    (mar_id, mar_nombre)
                )
                print(f"  Marca creada: {mar_nombre} (ID: {mar_id})")
            marca_id_map[mar_nombre] = mar_id

        # 3. Cargar Proveedores de manera idempotente
        print("\nCargando proveedores...")
        proveedor_id_map = {}
        for prov in PROVEEDORES:
            cursor.execute("SELECT id FROM proveedores WHERE nombre = ?;", (prov["nombre"],))
            row = cursor.fetchone()
            if row:
                prov_id = row[0]
                print(f"  Proveedor ya existente: {prov['nombre']} (ID: {prov_id})")
            else:
                prov_id = uuid.uuid4().hex
                cursor.execute(
                    "INSERT INTO proveedores (id, nombre, telefono, email) VALUES (?, ?, ?, ?);",
                    (prov_id, prov["nombre"], prov["telefono"], prov["email"])
                )
                print(f"  Proveedor creado: {prov['nombre']} (ID: {prov_id})")
            proveedor_id_map[prov["nombre"]] = prov_id

        # 4. Cargar Productos y sus Códigos de Barras
        print("\nCargando productos...")
        productos_creados = 0
        productos_omitidos = 0
        
        ahora = datetime.now(timezone.utc).isoformat()
        
        for prod in PRODUCTOS:
            # Verificar si el código de barras ya existe en la BD
            cursor.execute("SELECT id FROM codigos_barras WHERE codigo = ?;", (prod["codigo_barras"],))
            bar_row = cursor.fetchone()
            
            # Verificar si el producto ya existe por nombre
            cursor.execute("SELECT id FROM productos WHERE nombre = ?;", (prod["nombre"],))
            prod_row = cursor.fetchone()
            
            if bar_row or prod_row:
                print(f"  Producto/Código omitido (ya existe): {prod['nombre']} ({prod['codigo_barras']})")
                productos_omitidos += 1
                continue
            
            # Obtener IDs correspondientes
            cat_id = categoria_id_map.get(prod["categoria"])
            mar_id = marca_id_map.get(prod["marca"])
            prov_id = proveedor_id_map.get(prod["proveedor"])
            
            if not cat_id:
                print(f"  [ERROR] Categoría '{prod['categoria']}' no encontrada para el producto {prod['nombre']}. Omitiendo.")
                continue
                
            prod_id = uuid.uuid4().hex
            
            # Insertar producto
            cursor.execute(
                """
                INSERT INTO productos (
                    id, nombre, descripcion, categoria_id, marca_id, proveedor_id,
                    precio_venta_centavos, stock_actual, stock_minimo, unidad_medida,
                    activo, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    prod_id,
                    prod["nombre"],
                    prod["descripcion"],
                    cat_id,
                    mar_id,
                    prov_id,
                    prod["precio_venta_centavos"],
                    prod["stock_actual"],
                    prod["stock_minimo"],
                    prod["unidad_medida"],
                    1, # activo
                    ahora,
                    ahora
                )
            )
            
            # Insertar código de barras
            bar_id = uuid.uuid4().hex
            cursor.execute(
                """
                INSERT INTO codigos_barras (id, producto_id, codigo, principal)
                VALUES (?, ?, ?, ?);
                """,
                (bar_id, prod_id, prod["codigo_barras"], 1)
            )
            
            print(f"  Producto creado con éxito: {prod['nombre']} (Código: {prod['codigo_barras']})")
            productos_creados += 1

        print(f"\nProceso finalizado.")
        print(f"  Productos creados en esta tanda: {productos_creados}")
        print(f"  Productos omitidos por ya existir: {productos_omitidos}")

if __name__ == "__main__":
    seed_database()
