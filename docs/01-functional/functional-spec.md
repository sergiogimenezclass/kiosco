# functional-spec.md

# Especificación Funcional - Kiosk Billing & Cash POS

## 1. Visión General

Kiosk Billing & Cash POS es un sistema de punto de venta para kioscos, diseñado para operar de forma local o en VPS dedicado bajo modalidad Single-Tenant. El objetivo principal es permitir una operación rápida de caja, con control estricto de inventario, trazabilidad de ventas y cierre de caja confiable.

El sistema prioriza velocidad, bajo costo operativo, simplicidad técnica y consistencia de datos.

## 2. Alcance del MVP

### Incluido

- Login con usuario y contraseña.
- Roles: Administrador, Supervisor y Cajero.
- Apertura de caja.
- Cierre de caja ciego.
- Ingresos y retiros de caja.
- Venta por código de barras.
- Venta por búsqueda textual.
- Venta por accesos rápidos.
- Cobro en efectivo.
- Cobro digital.
- Descuentos por ítem y por venta.
- Anulación total de venta.
- Devolución total de venta.
- Gestión de productos.
- Gestión de categorías.
- Gestión de marcas.
- Gestión de proveedores.
- Productos unitarios.
- Productos pesables.
- Múltiples códigos de barras por producto.
- Stock sin negativos.
- Ingreso de mercadería.
- Ajustes de stock.
- Historial de movimientos de stock.
- Reportes de ventas, caja, stock bajo y ranking de productos.
- Exportación CSV, Excel y PDF.
- Carrito persistente en localStorage.

### Excluido

- AFIP/ARCA.
- Facturación fiscal.
- Multi-sucursal.
- Multi-tenant.
- Sincronización entre cajas.
- Venta mixta efectivo + digital.
- Ventas pendientes.
- Edición de ventas guardadas.
- Devoluciones parciales.
- Impresora térmica en MVP.
- Modificación manual de precio en venta.

## 3. Roles y Permisos

### Administrador

Puede:
- Crear usuarios.
- Cambiar contraseñas de otros usuarios.
- Gestionar productos, categorías, marcas y proveedores.
- Abrir caja si corresponde.
- Realizar ventas.
- Registrar ingresos y retiros de caja.
- Cerrar caja.
- Reabrir caja.
- Aplicar descuentos.
- Anular ventas.
- Realizar devoluciones.
- Ajustar stock.
- Ver todos los reportes.
- Exportar reportes.

### Supervisor

Puede:
- Gestionar productos, categorías, marcas y proveedores.
- Realizar ventas.
- Registrar ingresos y retiros de caja.
- Cerrar caja.
- Aplicar descuentos.
- Anular ventas.
- Realizar devoluciones.
- Ajustar stock.
- Ver reportes operativos.
- Exportar reportes disponibles.

No puede:
- Crear usuarios.
- Cambiar contraseñas de otros usuarios.

### Cajero

Puede:
- Iniciar sesión.
- Abrir caja.
- Realizar ventas.
- Cobrar en efectivo o digital.
- Usar scanner.
- Usar accesos rápidos.
- Ver el carrito.
- Vaciar carrito con confirmación.

No puede:
- Ver reportes.
- Crear usuarios.
- Cambiar contraseñas de otros usuarios.
- Registrar ingresos/retiros.
- Cerrar caja.
- Anular ventas.
- Realizar devoluciones.
- Aplicar descuentos.
- Ajustar stock.

## 4. Reglas de Negocio

### RB-01: Caja única abierta

Solo puede existir una caja en estado ABIERTA en toda la instancia.

### RB-02: Caja abierta por usuario

La caja se abre asociada a un usuario, pero otros usuarios pueden vender usando esa caja. Cada venta registra el usuario que la realizó.

### RB-03: Cierre por rol superior

Solo Supervisor o Administrador pueden cerrar caja.

### RB-04: Carrito activo al cerrar caja

Si existe carrito activo al cerrar caja, se descarta.

### RB-05: Ventas no editables

Una venta guardada nunca se modifica. Para corregir se usa anulación o devolución.

### RB-06: Stock no negativo

No se puede confirmar una venta, anulación, devolución o ajuste que deje stock negativo.

### RB-07: Precio histórico

Cada detalle de venta almacena el precio unitario al momento de la venta.

### RB-08: Productos pesables

Los productos pesables se guardan internamente en unidad mínima:
- gramos para peso;
- mililitros para volumen.

Ejemplo: 1.5 kg se almacena como 1500 gramos.

### RB-09: Descuentos

Los descuentos pueden ser:
- por producto;
- por venta completa.

Requieren Supervisor o Administrador.

El descuento por venta se aplica luego de los descuentos por ítem.

El máximo descuento permitido es configurable.

### RB-10: Anulaciones

La anulación:
- solo puede realizarse el mismo día;
- es total;
- devuelve stock;
- no requiere motivo obligatorio;
- solo la realiza Supervisor o Administrador.

### RB-11: Devoluciones

La devolución:
- es total;
- devuelve stock;
- devuelve dinero;
- no requiere motivo obligatorio;
- solo la realiza Supervisor o Administrador.

### RB-12: Ingresos y retiros

Todo ingreso o retiro de caja:
- requiere motivo obligatorio;
- solo lo realiza Supervisor o Administrador;
- queda auditado.

### RB-13: Ingreso de mercadería

Todo ingreso de mercadería requiere proveedor obligatorio.

### RB-14: Accesos rápidos

Los accesos rápidos se configuran desde administración.

## 5. Casos de Uso

### CU-01: Login

1. El usuario ingresa username y password.
2. El backend valida credenciales.
3. Si son válidas, se emite token/sesión.
4. El frontend redirige según rol.
5. Si son inválidas, se muestra error.

### CU-02: Apertura de caja

1. Cajero ingresa monto inicial.
2. Sistema verifica que no exista caja abierta.
3. Sistema crea caja ABIERTA.
4. Se habilita pantalla POS.

### CU-03: Venta por scanner

1. El cajero escanea producto.
2. Frontend detecta ráfaga de teclado.
3. Busca código de barras.
4. Si existe y hay stock, agrega producto al carrito.
5. Si no existe, muestra error y sonido.
6. Si no hay stock, bloquea agregado.

### CU-04: Venta por búsqueda

1. Cajero escribe nombre/descripción.
2. Sistema filtra productos en menos de 100 ms.
3. Cajero selecciona producto.
4. Producto se agrega al carrito si hay stock.

### CU-05: Venta por acceso rápido

1. Cajero selecciona botón de acceso rápido.
2. Producto se agrega al carrito.
3. Se recalcula total.

### CU-06: Cobro efectivo

1. Cajero abre modal de pago.
2. Selecciona efectivo.
3. Ingresa monto recibido.
4. Sistema calcula vuelto.
5. Si monto recibido >= total, permite confirmar.
6. Backend registra venta y descuenta stock transaccionalmente.

### CU-07: Cobro digital

1. Cajero abre modal de pago.
2. Selecciona digital.
3. Sistema asume monto recibido igual al total.
4. Vuelto = 0.
5. Backend registra venta.

### CU-08: Descuento

1. Supervisor o Administrador aplica descuento.
2. El sistema valida máximo configurable.
3. Recalcula subtotal, descuento y total.
4. Venta queda registrada con desglose.

### CU-09: Anulación

1. Supervisor o Administrador selecciona venta del día.
2. Sistema valida que no esté anulada/devuelta.
3. Sistema revierte stock.
4. Venta cambia a estado ANULADA.
5. Se registra movimiento de stock.

### CU-10: Devolución

1. Supervisor o Administrador selecciona venta.
2. Sistema valida que no esté anulada/devuelta.
3. Sistema devuelve stock.
4. Sistema registra devolución total de dinero.
5. Venta cambia a estado DEVUELTA.

### CU-11: Ajuste de stock

1. Supervisor o Administrador selecciona producto.
2. Ingresa cantidad de ajuste y motivo.
3. Sistema valida stock resultante no negativo.
4. Se registra movimiento.

### CU-12: Cierre de caja

1. Supervisor o Administrador ingresa monto físico declarado.
2. Sistema calcula monto esperado sin mostrarlo antes del cierre.
3. Calcula desviación.
4. Cambia caja a CERRADA.
5. Descarta carrito activo.
6. Bloquea nuevas ventas hasta nueva apertura.

## 6. Reportes

### Ventas diarias

Debe mostrar:
- total general;
- total por método de pago;
- total por cajero;
- cantidad de ventas;
- descuentos aplicados;
- anulaciones;
- devoluciones.

### Caja

Debe mostrar:
- monto inicial;
- ingresos;
- retiros;
- ventas efectivo;
- ventas digitales;
- monto declarado;
- desviación;
- usuario que abrió;
- usuario que cerró.

### Stock bajo

Debe listar productos con stock_actual <= stock_minimo.

### Ranking de productos

Debe permitir ranking por:
- cantidad vendida;
- monto vendido.

## 7. Exportaciones

Formatos:
- CSV.
- Excel.
- PDF.

Cada usuario puede exportar los reportes que tiene permiso de ver.

## 8. Validaciones Funcionales

- Montos en centavos enteros.
- Cantidades en unidad mínima.
- Stock nunca negativo.
- Username único.
- Código de barras único.
- Caja abierta única.
- Motivo obligatorio en ingresos/retiros.
- Motivo obligatorio en ajustes de stock.
- Descuento máximo configurable.
