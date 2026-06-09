# test-plan.md

# Plan de Pruebas

## Pruebas críticas

### Caja

- No permitir abrir dos cajas.
- Cerrar caja solo Supervisor/Admin.
- Ingreso/retiro requiere motivo.
- Cierre calcula desviación correctamente.

### Ventas

- Venta sin caja abierta falla.
- Venta con stock suficiente descuenta stock.
- Venta con stock insuficiente falla.
- Venta digital tiene vuelto 0.
- Venta efectivo calcula vuelto.
- Venta no permite precio manual.
- Venta no permite método mixto.

### Descuentos

- Cajero no puede aplicar descuento.
- Supervisor/Admin puede aplicar.
- Descuento máximo configurable.
- Descuento venta se aplica luego de descuento ítem.

### Anulaciones

- Solo mismo día.
- Solo Supervisor/Admin.
- Devuelve stock.
- No permite anular dos veces.
- No permite anular venta devuelta.

### Devoluciones

- Solo total.
- Solo Supervisor/Admin.
- Devuelve stock.
- Devuelve dinero.
- No permite devolver dos veces.
- No permite devolver venta anulada.

### Inventario

- Stock nunca negativo.
- Ajuste requiere motivo.
- Ingreso requiere proveedor.
- Movimiento de stock registra stock anterior y nuevo.

### Seguridad

- Password no se devuelve.
- Cajero no accede reportes.
- Cajero no crea usuario.
- Supervisor no crea usuario.
- Admin crea usuarios.

## Tests de performance

- Buscar producto < 100ms.
- Agregar scanner al carrito < 50ms.
- Registrar venta local < 200ms.

## Tests manuales UX

- F2 abre pago.
- F9 pide confirmación.
- Scanner inexistente emite sonido.
- Carrito persiste tras refresh.
- Carrito se descarta si caja cambia.
