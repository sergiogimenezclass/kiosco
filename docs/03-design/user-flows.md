# user-flows.md

# Flujos de Usuario

## Flujo: Venta normal

1. Usuario inicia sesión.
2. Si no hay caja abierta, abre caja.
3. Escanea productos.
4. Sistema agrega al carrito.
5. Cajero presiona F2.
6. Selecciona método de pago.
7. Confirma.
8. Sistema registra venta y descuenta stock.
9. Carrito se vacía.

## Flujo: Error por producto inexistente

1. Cajero escanea código.
2. Sistema no encuentra producto.
3. Emite sonido.
4. Muestra alerta temporal.
5. Mantiene foco en scanner.

## Flujo: Cierre de caja

1. Supervisor/Admin accede a cierre.
2. Ingresa monto declarado.
3. Sistema calcula monto esperado.
4. Registra desviación.
5. Cierra caja.
6. Descarta carrito local.

## Flujo: Anulación

1. Supervisor/Admin selecciona venta del día.
2. Solicita anulación.
3. Sistema valida fecha.
4. Devuelve stock.
5. Cambia estado a ANULADA.

## Flujo: Devolución

1. Supervisor/Admin selecciona venta.
2. Solicita devolución total.
3. Sistema devuelve dinero y stock.
4. Cambia estado a DEVUELTA.
