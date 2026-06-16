import os
import sys
import uuid
import sqlite3
from datetime import datetime, timedelta, timezone

# Add project root to sys.path to allow absolute imports of app
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.core.database import get_db_conn
from app.services.auth import AuthService

def seed_transactions():
    print("Iniciando la carga de datos transaccionales de prueba...")

    with get_db_conn() as conn:
        cursor = conn.cursor()

        # 1. Verificar catálogo base
        cursor.execute("SELECT COUNT(*) FROM productos;")
        if cursor.fetchone()[0] == 0:
            print("[ERROR] El catálogo está vacío. Por favor, ejecuta primero: python database/seed_data.py")
            return

        # 2. Verificar o crear usuarios
        print("Verificando usuarios...")
        cursor.execute("SELECT id, username, rol FROM usuarios;")
        users = cursor.fetchall()
        
        user_map = {u[1]: u[0] for u in users}
        
        # Asegurarnos de tener admin y cajero
        if "admin" not in user_map:
            admin_id = uuid.uuid4().hex
            pwd_hash = AuthService.hash_password("admin123")
            cursor.execute(
                "INSERT INTO usuarios (id, nombre, username, password_hash, rol, activo, created_at) VALUES (?, ?, ?, ?, ?, ?, ?);",
                (admin_id, "Administrador Sistema", "admin", pwd_hash, "ADMINISTRADOR", 1, datetime.now(timezone.utc).isoformat())
            )
            print("  Usuario 'admin' creado.")
            user_map["admin"] = admin_id
        
        if "juanperez" not in user_map:
            cajero_id = uuid.uuid4().hex
            pwd_hash = AuthService.hash_password("cajero123")
            cursor.execute(
                "INSERT INTO usuarios (id, nombre, username, password_hash, rol, activo, created_at) VALUES (?, ?, ?, ?, ?, ?, ?);",
                (cajero_id, "Juan Perez", "juanperez", pwd_hash, "CAJERO", 1, datetime.now(timezone.utc).isoformat())
            )
            print("  Usuario 'juanperez' creado.")
            user_map["juanperez"] = cajero_id

        admin_id = user_map["admin"]
        cajero_id = user_map["juanperez"]

        # Limpiar transacciones de prueba anteriores para evitar duplicados si se corre varias veces
        print("Limpiando datos transaccionales previos...")
        cursor.execute("DELETE FROM anulaciones;")
        cursor.execute("DELETE FROM devoluciones;")
        cursor.execute("DELETE FROM movimientos_stock;")
        cursor.execute("DELETE FROM movimientos_caja;")
        cursor.execute("DELETE FROM venta_detalles;")
        cursor.execute("DELETE FROM ventas;")
        cursor.execute("DELETE FROM cajas;")

        # Obtener productos del catálogo para usarlos en las ventas
        cursor.execute("SELECT id, nombre, precio_venta_centavos, unidad_medida, stock_actual, stock_minimo FROM productos;")
        products = [
            {"id": p[0], "nombre": p[1], "precio": p[2], "unidad": p[3], "stock": p[4], "minimo": p[5]}
            for p in cursor.fetchall()
        ]
        
        prod_by_barcode = {}
        for p in products:
            cursor.execute("SELECT codigo FROM codigos_barras WHERE producto_id = ? AND principal = 1;", (p["id"],))
            row = cursor.fetchone()
            p["codigo_barra"] = row[0] if row else ""

        # Fechas de referencia
        now_dt = datetime.now(timezone.utc)
        d1 = (now_dt - timedelta(days=3)).strftime("%Y-%m-%d")
        d2 = (now_dt - timedelta(days=2)).strftime("%Y-%m-%d")
        d3 = (now_dt - timedelta(days=1)).strftime("%Y-%m-%d")
        d4_today = now_dt.strftime("%Y-%m-%d")

        # 3. CREAR CAJAS (SESIONES DE CAJA HISTÓRICAS)
        print("Poblando sesiones de caja...")
        
        # Caja 1 (Cerrada, balance perfecto, día D-3)
        caja1_id = uuid.uuid4().hex
        cursor.execute(
            """
            INSERT INTO cajas (id, usuario_apertura_id, usuario_cierre_id, estado, monto_inicial_centavos, monto_declarado_centavos, monto_esperado_centavos, desviacion_centavos, fecha_apertura, fecha_cierre)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (caja1_id, admin_id, admin_id, "CERRADA", 1000000, 2500000, 2500000, 0, f"{d1}T08:00:00.000Z", f"{d1}T16:00:00.000Z")
        )

        # Caja 2 (Cerrada, con Faltante de 2000 centavos ($20), día D-2)
        caja2_id = uuid.uuid4().hex
        cursor.execute(
            """
            INSERT INTO cajas (id, usuario_apertura_id, usuario_cierre_id, estado, monto_inicial_centavos, monto_declarado_centavos, monto_esperado_centavos, desviacion_centavos, fecha_apertura, fecha_cierre)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (caja2_id, cajero_id, admin_id, "CERRADA", 1000000, 3100000, 3300000, -200000, f"{d2}T08:00:00.000Z", f"{d2}T16:00:00.000Z")
        )

        # Caja 3 (Cerrada, con Sobrante de 1000 centavos ($10), día D-1)
        caja3_id = uuid.uuid4().hex
        cursor.execute(
            """
            INSERT INTO cajas (id, usuario_apertura_id, usuario_cierre_id, estado, monto_inicial_centavos, monto_declarado_centavos, monto_esperado_centavos, desviacion_centavos, fecha_apertura, fecha_cierre)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (caja3_id, cajero_id, admin_id, "CERRADA", 1500000, 4600000, 4500000, 100000, f"{d3}T08:00:00.000Z", f"{d3}T16:00:00.000Z")
        )

        # Caja 4 (Abierta hoy)
        caja4_id = uuid.uuid4().hex
        cursor.execute(
            """
            INSERT INTO cajas (id, usuario_apertura_id, estado, monto_inicial_centavos, fecha_apertura)
            VALUES (?, ?, ?, ?, ?);
            """,
            (caja4_id, cajero_id, "ABIERTA", 1500000, f"{d4_today}T08:00:00.000Z")
        )

        # 4. MOVIMIENTOS DE CAJA MANUALES (Caja 2)
        print("Insertando movimientos de efectivo manuales...")
        # Ingreso de $50 (5000 centavos)
        mov_caja1_id = uuid.uuid4().hex
        cursor.execute(
            """
            INSERT INTO movimientos_caja (id, caja_id, usuario_id, tipo, monto_centavos, motivo, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (mov_caja1_id, caja2_id, cajero_id, "INGRESO", 500000, "Cambio de monedas para la caja", f"{d2}T09:00:00.000Z")
        )
        # Retiro de $20 (2000 centavos)
        mov_caja2_id = uuid.uuid4().hex
        cursor.execute(
            """
            INSERT INTO movimientos_caja (id, caja_id, usuario_id, tipo, monto_centavos, motivo, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (mov_caja2_id, caja2_id, admin_id, "RETIRO", 200000, "Pago a repartidor de folletos", f"{d2}T12:00:00.000Z")
        )

        # 5. CREAR VENTAS HISTÓRICAS
        print("Poblando transacciones de ventas y detalles...")
        
        # Producto auxiliar para las ventas
        p_coca = next(p for p in products if "Coca-Cola" in p["nombre"])
        p_guayma = next(p for p in products if "Guaymallén" in p["nombre"])
        p_jorgito = next(p for p in products if "Jorgito" in p["nombre"])
        p_lays = next(p for p in products if "Lays" in p["nombre"])
        p_fernet = next(p for p in products if "Fernet" in p["nombre"])

        # Venta 1 (Caja 1 - Completada - Efectivo)
        v1_id = uuid.uuid4().hex
        total_v1 = p_coca["precio"] * 2 + p_guayma["precio"] * 3
        cursor.execute(
            """
            INSERT INTO ventas (id, caja_id, usuario_id, estado, metodo_pago, subtotal_centavos, total_centavos, monto_recibido_centavos, vuelto_centavos, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (v1_id, caja1_id, admin_id, "COMPLETADA", "EFECTIVO", total_v1, total_v1, total_v1 + 50000, 50000, f"{d1}T10:30:00.000Z")
        )
        # Detalles
        cursor.execute(
            """
            INSERT INTO venta_detalles (id, venta_id, producto_id, nombre_producto_snapshot, cantidad, unidad_medida_snapshot, precio_unitario_centavos, subtotal_centavos, total_linea_centavos)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (uuid.uuid4().hex, v1_id, p_coca["id"], p_coca["nombre"], 2, p_coca["unidad"], p_coca["precio"], p_coca["precio"] * 2, p_coca["precio"] * 2)
        )
        cursor.execute(
            """
            INSERT INTO venta_detalles (id, venta_id, producto_id, nombre_producto_snapshot, cantidad, unidad_medida_snapshot, precio_unitario_centavos, subtotal_centavos, total_linea_centavos)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (uuid.uuid4().hex, v1_id, p_guayma["id"], p_guayma["nombre"], 3, p_guayma["unidad"], p_guayma["precio"], p_guayma["precio"] * 3, p_guayma["precio"] * 3)
        )

        # Venta 2 (Caja 2 - Completada - Digital)
        v2_id = uuid.uuid4().hex
        total_v2 = p_fernet["precio"] * 1 + p_lays["precio"] * 2
        cursor.execute(
            """
            INSERT INTO ventas (id, caja_id, usuario_id, estado, metodo_pago, subtotal_centavos, total_centavos, monto_recibido_centavos, vuelto_centavos, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (v2_id, caja2_id, cajero_id, "COMPLETADA", "DIGITAL", total_v2, total_v2, total_v2, 0, f"{d2}T11:15:00.000Z")
        )
        cursor.execute(
            """
            INSERT INTO venta_detalles (id, venta_id, producto_id, nombre_producto_snapshot, cantidad, unidad_medida_snapshot, precio_unitario_centavos, subtotal_centavos, total_linea_centavos)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (uuid.uuid4().hex, v2_id, p_fernet["id"], p_fernet["nombre"], 1, p_fernet["unidad"], p_fernet["precio"], p_fernet["precio"], p_fernet["precio"])
        )
        cursor.execute(
            """
            INSERT INTO venta_detalles (id, venta_id, producto_id, nombre_producto_snapshot, cantidad, unidad_medida_snapshot, precio_unitario_centavos, subtotal_centavos, total_linea_centavos)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (uuid.uuid4().hex, v2_id, p_lays["id"], p_lays["nombre"], 2, p_lays["unidad"], p_lays["precio"], p_lays["precio"] * 2, p_lays["precio"] * 2)
        )

        # Venta 3 (Caja 3 - Completada - Efectivo)
        v3_id = uuid.uuid4().hex
        total_v3 = p_jorgito["precio"] * 5
        cursor.execute(
            """
            INSERT INTO ventas (id, caja_id, usuario_id, estado, metodo_pago, subtotal_centavos, total_centavos, monto_recibido_centavos, vuelto_centavos, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (v3_id, caja3_id, cajero_id, "COMPLETADA", "EFECTIVO", total_v3, total_v3, total_v3, 0, f"{d3}T14:50:00.000Z")
        )
        cursor.execute(
            """
            INSERT INTO venta_detalles (id, venta_id, producto_id, nombre_producto_snapshot, cantidad, unidad_medida_snapshot, precio_unitario_centavos, subtotal_centavos, total_linea_centavos)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (uuid.uuid4().hex, v3_id, p_jorgito["id"], p_jorgito["nombre"], 5, p_jorgito["unidad"], p_jorgito["precio"], p_jorgito["precio"] * 5, p_jorgito["precio"] * 5)
        )

        # Venta 4 (Caja 4 - Completada HOY - Efectivo)
        v4_id = uuid.uuid4().hex
        total_v4 = p_guayma["precio"] * 5
        cursor.execute(
            """
            INSERT INTO ventas (id, caja_id, usuario_id, estado, metodo_pago, subtotal_centavos, total_centavos, monto_recibido_centavos, vuelto_centavos, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (v4_id, caja4_id, cajero_id, "COMPLETADA", "EFECTIVO", total_v4, total_v4, total_v4 + 20000, 20000, f"{d4_today}T09:30:00.000Z")
        )
        cursor.execute(
            """
            INSERT INTO venta_detalles (id, venta_id, producto_id, nombre_producto_snapshot, cantidad, unidad_medida_snapshot, precio_unitario_centavos, subtotal_centavos, total_linea_centavos)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (uuid.uuid4().hex, v4_id, p_guayma["id"], p_guayma["nombre"], 5, p_guayma["unidad"], p_guayma["precio"], p_guayma["precio"] * 5, p_guayma["precio"] * 5)
        )

        # Venta 5 (Caja 4 - Completada HOY - Digital - Descuento)
        v5_id = uuid.uuid4().hex
        subtotal_v5 = p_lays["precio"] * 3
        descuento_v5 = 50000 # $500 de descuento global
        total_v5 = subtotal_v5 - descuento_v5
        cursor.execute(
            """
            INSERT INTO ventas (id, caja_id, usuario_id, estado, metodo_pago, subtotal_centavos, descuento_venta_centavos, total_centavos, monto_recibido_centavos, vuelto_centavos, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (v5_id, caja4_id, cajero_id, "COMPLETADA", "DIGITAL", subtotal_v5, descuento_v5, total_v5, total_v5, 0, f"{d4_today}T10:15:00.000Z")
        )
        cursor.execute(
            """
            INSERT INTO venta_detalles (id, venta_id, producto_id, nombre_producto_snapshot, cantidad, unidad_medida_snapshot, precio_unitario_centavos, subtotal_centavos, total_linea_centavos)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (uuid.uuid4().hex, v5_id, p_lays["id"], p_lays["nombre"], 3, p_lays["unidad"], p_lays["precio"], p_lays["precio"] * 3, p_lays["precio"] * 3)
        )

        # Venta 6 (Caja 3 - ANULADA históricamente)
        v6_id = uuid.uuid4().hex
        total_v6 = p_coca["precio"] * 1
        cursor.execute(
            """
            INSERT INTO ventas (id, caja_id, usuario_id, estado, metodo_pago, subtotal_centavos, total_centavos, monto_recibido_centavos, vuelto_centavos, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (v6_id, caja3_id, cajero_id, "ANULADA", "EFECTIVO", total_v6, total_v6, total_v6, 0, f"{d3}T10:00:00.000Z")
        )
        cursor.execute(
            """
            INSERT INTO venta_detalles (id, venta_id, producto_id, nombre_producto_snapshot, cantidad, unidad_medida_snapshot, precio_unitario_centavos, subtotal_centavos, total_linea_centavos)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (uuid.uuid4().hex, v6_id, p_coca["id"], p_coca["nombre"], 1, p_coca["unidad"], p_coca["precio"], p_coca["precio"], p_coca["precio"])
        )
        # Tabla Anulaciones
        cursor.execute(
            """
            INSERT INTO anulaciones (id, venta_id, usuario_id, motivo, fecha)
            VALUES (?, ?, ?, ?, ?);
            """,
            (uuid.uuid4().hex, v6_id, admin_id, "Cargado por error en caja", f"{d3}T10:05:00.000Z")
        )

        # Venta 7 (Caja 1 - DEVUELTA históricamente)
        v7_id = uuid.uuid4().hex
        total_v7 = p_jorgito["precio"] * 2
        cursor.execute(
            """
            INSERT INTO ventas (id, caja_id, usuario_id, estado, metodo_pago, subtotal_centavos, total_centavos, monto_recibido_centavos, vuelto_centavos, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (v7_id, caja1_id, admin_id, "DEVUELTA", "DIGITAL", total_v7, total_v7, total_v7, 0, f"{d1}T09:00:00.000Z")
        )
        cursor.execute(
            """
            INSERT INTO venta_detalles (id, venta_id, producto_id, nombre_producto_snapshot, cantidad, unidad_medida_snapshot, precio_unitario_centavos, subtotal_centavos, total_linea_centavos)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (uuid.uuid4().hex, v7_id, p_jorgito["id"], p_jorgito["nombre"], 2, p_jorgito["unidad"], p_jorgito["precio"], p_jorgito["precio"] * 2, p_jorgito["precio"] * 2)
        )
        # Tabla Devoluciones
        cursor.execute(
            """
            INSERT INTO devoluciones (id, venta_id, usuario_id, monto_devuelto_centavos, motivo, fecha)
            VALUES (?, ?, ?, ?, ?, ?);
            """,
            (uuid.uuid4().hex, v7_id, admin_id, total_v7, "Producto defectuoso/vencido", f"{d1}T14:00:00.000Z")
        )

        # 6. REGISTRAR MOVIMIENTOS DE STOCK (Historial Auditoría)
        print("Registrando movimientos de stock e integrando inventario...")
        
        # Usamos los productos y simulamos stock anterior/nuevo
        # Para hacer el seed realista, buscaremos el stock actual de la base de datos de cada uno
        # y re-escribiremos los movimientos hacia atrás para que la suma sea perfecta.
        
        # Coca Cola (v1: -2, v6: -1 anulado: +1 neto = -2)
        # Pongamos stock inicial = 50
        # Venta 1: 50 -> 48
        # Venta 6: 48 -> 47
        # Anulación 6: 47 -> 48
        cursor.execute(
            "INSERT INTO movimientos_stock (id, producto_id, usuario_id, tipo, cantidad, stock_anterior, stock_nuevo, fecha) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            (uuid.uuid4().hex, p_coca["id"], admin_id, "VENTA", 2, 50, 48, f"{d1}T10:30:00.000Z")
        )
        cursor.execute(
            "INSERT INTO movimientos_stock (id, producto_id, usuario_id, tipo, cantidad, stock_anterior, stock_nuevo, fecha) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            (uuid.uuid4().hex, p_coca["id"], cajero_id, "VENTA", 1, 48, 47, f"{d3}T10:00:00.000Z")
        )
        cursor.execute(
            "INSERT INTO movimientos_stock (id, producto_id, usuario_id, tipo, cantidad, stock_anterior, stock_nuevo, fecha) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            (uuid.uuid4().hex, p_coca["id"], admin_id, "ANULACION", 1, 47, 48, f"{d3}T10:05:00.000Z")
        )

        # Guaymallen (v1: -3, v4: -5, total = -8)
        # Stock inicial = 50
        # Venta 1: 50 -> 47
        # Venta 4: 47 -> 42
        cursor.execute(
            "INSERT INTO movimientos_stock (id, producto_id, usuario_id, tipo, cantidad, stock_anterior, stock_nuevo, fecha) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            (uuid.uuid4().hex, p_guayma["id"], admin_id, "VENTA", 3, 50, 47, f"{d1}T10:30:00.000Z")
        )
        cursor.execute(
            "INSERT INTO movimientos_stock (id, producto_id, usuario_id, tipo, cantidad, stock_anterior, stock_nuevo, fecha) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            (uuid.uuid4().hex, p_guayma["id"], cajero_id, "VENTA", 5, 47, 42, f"{d4_today}T09:30:00.000Z")
        )

        # Jorgito (v3: -5, v7: -2 devuelto: +2 neto = -5)
        # Stock inicial = 40
        # Venta 7: 40 -> 38
        # Devolución 7: 38 -> 40
        # Venta 3: 40 -> 35
        cursor.execute(
            "INSERT INTO movimientos_stock (id, producto_id, usuario_id, tipo, cantidad, stock_anterior, stock_nuevo, fecha) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            (uuid.uuid4().hex, p_jorgito["id"], admin_id, "VENTA", 2, 40, 38, f"{d1}T09:00:00.000Z")
        )
        cursor.execute(
            "INSERT INTO movimientos_stock (id, producto_id, usuario_id, tipo, cantidad, stock_anterior, stock_nuevo, fecha) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            (uuid.uuid4().hex, p_jorgito["id"], admin_id, "DEVOLUCION", 2, 38, 40, f"{d1}T14:00:00.000Z")
        )
        cursor.execute(
            "INSERT INTO movimientos_stock (id, producto_id, usuario_id, tipo, cantidad, stock_anterior, stock_nuevo, fecha) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            (uuid.uuid4().hex, p_jorgito["id"], cajero_id, "VENTA", 5, 40, 35, f"{d3}T14:50:00.000Z")
        )

        # Lays (v2: -2, v5: -3, total = -5)
        # Stock inicial = 18
        # Venta 2: 18 -> 16
        # Venta 5: 16 -> 11
        cursor.execute(
            "INSERT INTO movimientos_stock (id, producto_id, usuario_id, tipo, cantidad, stock_anterior, stock_nuevo, fecha) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            (uuid.uuid4().hex, p_lays["id"], cajero_id, "VENTA", 2, 18, 16, f"{d2}T11:15:00.000Z")
        )
        cursor.execute(
            "INSERT INTO movimientos_stock (id, producto_id, usuario_id, tipo, cantidad, stock_anterior, stock_nuevo, fecha) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            (uuid.uuid4().hex, p_lays["id"], cajero_id, "VENTA", 3, 16, 11, f"{d4_today}T10:15:00.000Z")
        )

        # Fernet (v2: -1)
        # Stock inicial = 12
        # Venta 2: 12 -> 11
        cursor.execute(
            "INSERT INTO movimientos_stock (id, producto_id, usuario_id, tipo, cantidad, stock_anterior, stock_nuevo, fecha) VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
            (uuid.uuid4().hex, p_fernet["id"], cajero_id, "VENTA", 1, 12, 11, f"{d2}T11:15:00.000Z")
        )

        # 7. REGISTRAR MOVIMIENTOS MANUALES INDEPENDIENTES (Ajustes e Ingresos)
        print("Registrando ajustes manuales y entradas de stock...")
        
        # Ingreso manual de Coca-Cola (proveedor 1)
        cursor.execute("SELECT id FROM proveedores LIMIT 1;")
        prov_id = cursor.fetchone()[0]
        
        # Coca Cola: 48 -> 98 (+50 unidades)
        cursor.execute(
            """
            INSERT INTO movimientos_stock (id, producto_id, usuario_id, tipo, cantidad, stock_anterior, stock_nuevo, proveedor_id, motivo, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (uuid.uuid4().hex, p_coca["id"], admin_id, "INGRESO", 50, 48, 98, prov_id, "Remito de compra Mayorista", f"{d3}T09:00:00.000Z")
        )
        
        # Ajuste negativo de Lays (vencimiento)
        # Lays: 11 -> 8 (-3 unidades)
        cursor.execute(
            """
            INSERT INTO movimientos_stock (id, producto_id, usuario_id, tipo, cantidad, stock_anterior, stock_nuevo, motivo, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (uuid.uuid4().hex, p_lays["id"], admin_id, "AJUSTE", -3, 11, 8, "Vencimiento lote 002", f"{d4_today}T11:00:00.000Z")
        )
        
        # Ajuste positivo de Yerba Playadito (sobrante inventario)
        # Playadito: 15 -> 17 (+2 unidades)
        p_playa = next(p for p in products if "Playadito" in p["nombre"])
        cursor.execute(
            """
            INSERT INTO movimientos_stock (id, producto_id, usuario_id, tipo, cantidad, stock_anterior, stock_nuevo, motivo, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (uuid.uuid4().hex, p_playa["id"], admin_id, "AJUSTE", 2, 15, 17, "Sobrante detectado en auditoria fisica", f"{d4_today}T11:30:00.000Z")
        )

        # 8. ACTUALIZAR STOCK ACTUAL EN TABLA PRODUCTOS
        print("Actualizando stocks netos finales en tabla de productos...")
        cursor.execute("UPDATE productos SET stock_actual = 98 WHERE id = ?;", (p_coca["id"],))
        cursor.execute("UPDATE productos SET stock_actual = 42 WHERE id = ?;", (p_guayma["id"],))
        cursor.execute("UPDATE productos SET stock_actual = 35 WHERE id = ?;", (p_jorgito["id"],))
        cursor.execute("UPDATE productos SET stock_actual = 8 WHERE id = ?;", (p_lays["id"],))
        cursor.execute("UPDATE productos SET stock_actual = 11 WHERE id = ?;", (p_fernet["id"],))
        cursor.execute("UPDATE productos SET stock_actual = 17 WHERE id = ?;", (p_playa["id"],))

        # 9. CREAR PRODUCTOS CON STOCK CRÍTICO (Ajustar stock mínimo y actual para auditoría)
        # Vamos a poner a la Yerba Taragüí con stock_actual = 2 y stock_minimo = 5 (Crítico)
        # Y al Chupetín Pico Dulce con stock_actual = 0 y stock_minimo = 30 (Crítico / Agotado)
        print("Configurando productos con stock crítico para pruebas...")
        p_tara = next(p for p in products if "Taragüí" in p["nombre"])
        p_pico = next(p for p in products if "Pico Dulce" in p["nombre"])
        
        cursor.execute("UPDATE productos SET stock_actual = 2, stock_minimo = 5 WHERE id = ?;", (p_tara["id"],))
        cursor.execute("UPDATE productos SET stock_actual = 0, stock_minimo = 30 WHERE id = ?;", (p_pico["id"],))

        # Generar registros de movimientos de stock para estos cambios de Taragüí y Chupetín
        # Taragui: 20 -> 2 (ajuste de -18)
        cursor.execute(
            """
            INSERT INTO movimientos_stock (id, producto_id, usuario_id, tipo, cantidad, stock_anterior, stock_nuevo, motivo, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (uuid.uuid4().hex, p_tara["id"], admin_id, "AJUSTE", -18, 20, 2, "Ajuste por merma/pérdida de stock", f"{d4_today}T12:00:00.000Z")
        )
        # Pico dulce: 150 -> 0 (ajuste de -150)
        cursor.execute(
            """
            INSERT INTO movimientos_stock (id, producto_id, usuario_id, tipo, cantidad, stock_anterior, stock_nuevo, motivo, fecha)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (uuid.uuid4().hex, p_pico["id"], admin_id, "AJUSTE", -150, 150, 0, "Ajuste general por robo hormiga", f"{d4_today}T12:05:00.000Z")
        )

        print("\nSeeding de transacciones de prueba completado exitosamente.")
        print("  Cajas creadas: 3 cerradas + 1 abierta para hoy.")
        print("  Ventas creadas: 5 completadas + 1 anulada + 1 devuelta.")
        print("  Movimientos de stock cargados en historial.")
        print("  Productos configurados bajo stock crítico para auditoría.")

if __name__ == "__main__":
    seed_transactions()
