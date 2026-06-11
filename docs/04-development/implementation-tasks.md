# implementation-tasks.md

# Plan de Implementación

## Fase 1 - Base técnica

- [x] Crear proyecto FastAPI.
- [x] Configurar SQLite.
- [x] Aplicar PRAGMAs.
- [x] Crear schema.sql.
- [x] Crear conexión DB.
- [x] Crear estructura Controller/Service/Repository.
- [x] Configurar manejo estándar de errores.

## Fase 2 - Autenticación y roles

- Tabla usuarios.
- Hash bcrypt.
- Login.
- JWT.
- Middleware de autenticación.
- Decoradores/guards por rol.
- Seed de usuario administrador.

## Fase 3 - Catálogo

- CRUD categorías.
- CRUD marcas.
- CRUD proveedores.
- CRUD productos.
- Múltiples códigos de barras.
- Accesos rápidos configurables.
- Validaciones de stock, precio y unidad.

## Fase 4 - Caja

- Apertura de caja.
- Validar caja única abierta.
- Ingresos de caja.
- Retiros de caja.
- Cierre ciego.
- Cálculo de desviación.
- Historial de cajas.

## Fase 5 - POS frontend

- Layout principal.
- Scanner listener.
- Búsqueda predictiva.
- Carrito.
- Persistencia localStorage.
- Accesos rápidos.
- Atajos F2 y F9.
- Confirmación de vaciado.
- Sonido de error.

## Fase 6 - Ventas

- Endpoint POST /ventas.
- Validación caja abierta.
- Validación stock.
- Cálculo subtotal.
- Descuentos.
- Cobro efectivo.
- Cobro digital.
- Descuento stock transaccional.
- Registro venta_detalles.
- Registro movimientos_stock.

## Fase 7 - Anulaciones y devoluciones

- Anulación solo mismo día.
- Devolución total.
- Reversión stock.
- Cambio de estado.
- Validación venta no anulada/devuelta.

## Fase 8 - Inventario

- Ajustes de stock.
- Ingreso de mercadería con proveedor.
- Historial de movimientos.
- Stock bajo.

## Fase 9 - Reportes

- Ventas diarias.
- Caja.
- Ranking productos.
- Stock bajo.
- Export CSV.
- Export Excel.
- Export PDF.

## Fase 10 - Testing

- Tests unitarios servicios.
- Tests integración endpoints.
- Tests transacciones stock/venta.
- Tests permisos.
- Tests caja única.
- Tests anulación/devolución.
- Tests frontend básicos.
