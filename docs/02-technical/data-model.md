# data-model.md

# Modelo de Datos - Kiosk Billing & Cash POS

## Convenciones

- IDs: TEXT UUIDv4.
- Fechas: TEXT ISO-8601 UTC.
- Montos: INTEGER en centavos.
- Cantidades: INTEGER en unidad mínima.
- Productos pesables:
  - gramos para peso;
  - mililitros para volumen.
- Borrado físico restringido en entidades con historial.
- Usuarios se desactivan con `activo = 0`.

## Tabla: usuarios

| Campo | Tipo | Restricción |
|---|---|---|
| id | TEXT | PK |
| nombre | TEXT | NOT NULL |
| username | TEXT | UNIQUE NOT NULL |
| password_hash | TEXT | NOT NULL |
| rol | TEXT | CHECK ADMINISTRADOR/SUPERVISOR/CAJERO |
| activo | INTEGER | DEFAULT 1 |
| created_at | TEXT | NOT NULL |

## Tabla: cajas

| Campo | Tipo | Restricción |
|---|---|---|
| id | TEXT | PK |
| usuario_apertura_id | TEXT | FK usuarios |
| usuario_cierre_id | TEXT | FK usuarios NULL |
| estado | TEXT | ABIERTA/CERRADA |
| monto_inicial_centavos | INTEGER | >= 0 |
| monto_declarado_centavos | INTEGER | NULL >= 0 |
| monto_esperado_centavos | INTEGER | NULL |
| desviacion_centavos | INTEGER | NULL |
| fecha_apertura | TEXT | NOT NULL |
| fecha_cierre | TEXT | NULL |

Regla: solo una caja ABIERTA.

## Tabla: movimientos_caja

| Campo | Tipo | Restricción |
|---|---|---|
| id | TEXT | PK |
| caja_id | TEXT | FK cajas |
| usuario_id | TEXT | FK usuarios |
| tipo | TEXT | INGRESO/RETIRO |
| monto_centavos | INTEGER | > 0 |
| motivo | TEXT | NOT NULL |
| fecha | TEXT | NOT NULL |

## Tabla: categorias

| Campo | Tipo | Restricción |
|---|---|---|
| id | TEXT | PK |
| nombre | TEXT | UNIQUE NOT NULL |

## Tabla: marcas

| Campo | Tipo | Restricción |
|---|---|---|
| id | TEXT | PK |
| nombre | TEXT | UNIQUE NOT NULL |

## Tabla: proveedores

| Campo | Tipo | Restricción |
|---|---|---|
| id | TEXT | PK |
| nombre | TEXT | NOT NULL |
| telefono | TEXT | NULL |
| email | TEXT | NULL |

## Tabla: productos

| Campo | Tipo | Restricción |
|---|---|---|
| id | TEXT | PK |
| nombre | TEXT | NOT NULL |
| descripcion | TEXT | NULL |
| categoria_id | TEXT | FK categorias NOT NULL |
| marca_id | TEXT | FK marcas NULL |
| proveedor_id | TEXT | FK proveedores NULL |
| precio_venta_centavos | INTEGER | > 0 |
| stock_actual | INTEGER | >= 0 |
| stock_minimo | INTEGER | >= 0 |
| unidad_medida | TEXT | UNIDAD/GRAMO/MILILITRO |
| imagen_url | TEXT | NULL |
| activo | INTEGER | DEFAULT 1 |
| created_at | TEXT | NOT NULL |
| updated_at | TEXT | NOT NULL |

Notas:
- Para productos unitarios, stock_actual representa unidades.
- Para productos pesables, stock_actual representa gramos o mililitros.

## Tabla: codigos_barras

| Campo | Tipo | Restricción |
|---|---|---|
| id | TEXT | PK |
| producto_id | TEXT | FK productos |
| codigo | TEXT | UNIQUE NOT NULL |
| principal | INTEGER | DEFAULT 0 |

## Tabla: accesos_rapidos

| Campo | Tipo | Restricción |
|---|---|---|
| id | TEXT | PK |
| producto_id | TEXT | FK productos |
| etiqueta | TEXT | NOT NULL |
| orden | INTEGER | NOT NULL |
| activo | INTEGER | DEFAULT 1 |

## Tabla: ventas

| Campo | Tipo | Restricción |
|---|---|---|
| id | TEXT | PK |
| caja_id | TEXT | FK cajas |
| usuario_id | TEXT | FK usuarios |
| estado | TEXT | COMPLETADA/ANULADA/DEVUELTA |
| metodo_pago | TEXT | EFECTIVO/DIGITAL |
| subtotal_centavos | INTEGER | >= 0 |
| descuento_items_centavos | INTEGER | >= 0 |
| descuento_venta_centavos | INTEGER | >= 0 |
| total_centavos | INTEGER | >= 0 |
| monto_recibido_centavos | INTEGER | >= 0 |
| vuelto_centavos | INTEGER | >= 0 |
| fecha | TEXT | NOT NULL |

## Tabla: venta_detalles

| Campo | Tipo | Restricción |
|---|---|---|
| id | TEXT | PK |
| venta_id | TEXT | FK ventas |
| producto_id | TEXT | FK productos |
| nombre_producto_snapshot | TEXT | NOT NULL |
| cantidad | INTEGER | > 0 |
| unidad_medida_snapshot | TEXT | NOT NULL |
| precio_unitario_centavos | INTEGER | > 0 |
| descuento_centavos | INTEGER | >= 0 |
| subtotal_centavos | INTEGER | >= 0 |
| total_linea_centavos | INTEGER | >= 0 |

## Tabla: devoluciones

| Campo | Tipo | Restricción |
|---|---|---|
| id | TEXT | PK |
| venta_id | TEXT | FK ventas UNIQUE |
| usuario_id | TEXT | FK usuarios |
| monto_devuelto_centavos | INTEGER | >= 0 |
| motivo | TEXT | NULL |
| fecha | TEXT | NOT NULL |

## Tabla: anulaciones

| Campo | Tipo | Restricción |
|---|---|---|
| id | TEXT | PK |
| venta_id | TEXT | FK ventas UNIQUE |
| usuario_id | TEXT | FK usuarios |
| motivo | TEXT | NULL |
| fecha | TEXT | NOT NULL |

## Tabla: movimientos_stock

| Campo | Tipo | Restricción |
|---|---|---|
| id | TEXT | PK |
| producto_id | TEXT | FK productos |
| usuario_id | TEXT | FK usuarios |
| tipo | TEXT | VENTA/DEVOLUCION/ANULACION/AJUSTE/INGRESO |
| cantidad | INTEGER | NOT NULL |
| stock_anterior | INTEGER | >= 0 |
| stock_nuevo | INTEGER | >= 0 |
| referencia_tipo | TEXT | NULL |
| referencia_id | TEXT | NULL |
| motivo | TEXT | NULL |
| proveedor_id | TEXT | FK proveedores NULL |
| fecha | TEXT | NOT NULL |

## Tabla: configuracion

| Campo | Tipo | Restricción |
|---|---|---|
| clave | TEXT | PK |
| valor | TEXT | NOT NULL |

Configuraciones iniciales:
- descuento_maximo_porcentaje
- moneda
- nombre_comercio
