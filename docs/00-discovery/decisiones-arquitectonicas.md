# Decisiones Arquitectónicas y Funcionales

## Producto

Sistema POS para kioscos en modalidad Single-Tenant, pensado para una instancia aislada por comercio.

## Stack

- Frontend: HTML5, CSS3, JavaScript Vanilla ES6+.
- Backend: Python 3.10+ con FastAPI.
- Base de datos: SQLite 3 con WAL.
- Interfaz: alta densidad, teclado primero, táctil compatible.

## Decisiones cerradas

- Hay login con usuario y contraseña.
- Roles: Administrador, Supervisor y Cajero.
- Los usuarios no se eliminan físicamente: se desactivan.
- Solo el Administrador crea usuarios y cambia contraseñas de otros usuarios.
- El Cajero no ve reportes.
- El Supervisor puede gestionar productos.
- La caja se abre por usuario/cajero.
- Solo puede existir una caja abierta simultáneamente.
- Otro cajero puede vender en la misma caja, pero cada venta queda auditada.
- Ingresos y retiros de caja solo los hacen Supervisor o Administrador.
- El cierre de caja lo hace Supervisor o Administrador.
- Si hay carrito activo al cerrar caja, se descarta.
- Se permite venta digital.
- No hay venta mixta efectivo + digital.
- No se permite modificar manualmente precios en venta.
- No existen ventas pendientes/suspendidas.
- Los descuentos pueden ser por producto y por venta.
- El descuento máximo es configurable.
- El descuento por venta se aplica sobre el subtotal ya descontado por ítems.
- Las ventas nunca se editan.
- Las anulaciones solo se hacen el mismo día.
- Las anulaciones devuelven stock.
- Las anulaciones no requieren motivo obligatorio.
- Las devoluciones son totales, no parciales.
- Las devoluciones devuelven dinero y stock.
- Las devoluciones no requieren motivo obligatorio.
- Devoluciones y anulaciones solo las hacen Supervisor o Administrador.
- No se permite stock negativo.
- Productos pesables se almacenan en unidad mínima: gramos/ml.
- Los productos no se inactivan para conservar historial; se asume borrado restringido si tienen historial.
- Si un producto se vuelve inactivo mientras ya estaba en carrito, puede venderse.
- Ajustes de stock requieren motivo obligatorio.
- Ajustes de stock los hacen Supervisor o Administrador.
- Ingreso de mercadería requiere proveedor obligatorio.
- Precio histórico se guarda en detalle de venta.
- Cambios de precio no requieren auditoría específica en MVP.
- Reportes: ventas diarias, cierre de caja, stock bajo, ranking de productos.
- Exportaciones: CSV, Excel y PDF.
- Todos los roles pueden exportar reportes a los que tengan acceso.
- Pantalla completa recomendada, no obligatoria.
- Carrito persiste en localStorage.
- F9 para vaciar carrito requiere confirmación.
- Scanner emite sonido ante error.
- Accesos rápidos configurables desde administración.

## Fuera de alcance MVP

- AFIP/ARCA.
- Facturación fiscal.
- Multi-sucursal.
- Multi-tenant.
- Sincronización entre cajas.
- Impresora térmica.
- Ventas pendientes.
- Venta mixta.
- Precio manual por venta.
- Devoluciones parciales.
