# erd.md

# ERD - Entity Relationship Diagram

```mermaid
erDiagram
    USUARIOS ||--o{ CAJAS : abre
    USUARIOS ||--o{ VENTAS : registra
    USUARIOS ||--o{ MOVIMIENTOS_CAJA : realiza
    USUARIOS ||--o{ MOVIMIENTOS_STOCK : realiza
    USUARIOS ||--o{ DEVOLUCIONES : registra
    USUARIOS ||--o{ ANULACIONES : registra

    CAJAS ||--o{ VENTAS : contiene
    CAJAS ||--o{ MOVIMIENTOS_CAJA : registra

    CATEGORIAS ||--o{ PRODUCTOS : agrupa
    MARCAS ||--o{ PRODUCTOS : clasifica
    PROVEEDORES ||--o{ PRODUCTOS : provee
    PROVEEDORES ||--o{ MOVIMIENTOS_STOCK : origen

    PRODUCTOS ||--o{ CODIGOS_BARRAS : tiene
    PRODUCTOS ||--o{ ACCESOS_RAPIDOS : aparece_en
    PRODUCTOS ||--o{ VENTA_DETALLES : vendido_como
    PRODUCTOS ||--o{ MOVIMIENTOS_STOCK : mueve

    VENTAS ||--o{ VENTA_DETALLES : contiene
    VENTAS ||--o| DEVOLUCIONES : puede_tener
    VENTAS ||--o| ANULACIONES : puede_tener

    USUARIOS {
        text id PK
        text nombre
        text username UK
        text password_hash
        text rol
        integer activo
        text created_at
    }

    CAJAS {
        text id PK
        text usuario_apertura_id FK
        text usuario_cierre_id FK
        text estado
        integer monto_inicial_centavos
        integer monto_declarado_centavos
        integer monto_esperado_centavos
        integer desviacion_centavos
        text fecha_apertura
        text fecha_cierre
    }

    MOVIMIENTOS_CAJA {
        text id PK
        text caja_id FK
        text usuario_id FK
        text tipo
        integer monto_centavos
        text motivo
        text fecha
    }

    CATEGORIAS {
        text id PK
        text nombre UK
    }

    MARCAS {
        text id PK
        text nombre UK
    }

    PROVEEDORES {
        text id PK
        text nombre
        text telefono
        text email
    }

    PRODUCTOS {
        text id PK
        text nombre
        text descripcion
        text categoria_id FK
        text marca_id FK
        text proveedor_id FK
        integer precio_venta_centavos
        integer stock_actual
        integer stock_minimo
        text unidad_medida
        text imagen_url
        integer activo
        text created_at
        text updated_at
    }

    CODIGOS_BARRAS {
        text id PK
        text producto_id FK
        text codigo UK
        integer principal
    }

    ACCESOS_RAPIDOS {
        text id PK
        text producto_id FK
        text etiqueta
        integer orden
        integer activo
    }

    VENTAS {
        text id PK
        text caja_id FK
        text usuario_id FK
        text estado
        text metodo_pago
        integer subtotal_centavos
        integer descuento_items_centavos
        integer descuento_venta_centavos
        integer total_centavos
        integer monto_recibido_centavos
        integer vuelto_centavos
        text fecha
    }

    VENTA_DETALLES {
        text id PK
        text venta_id FK
        text producto_id FK
        text nombre_producto_snapshot
        integer cantidad
        text unidad_medida_snapshot
        integer precio_unitario_centavos
        integer descuento_centavos
        integer subtotal_centavos
        integer total_linea_centavos
    }

    DEVOLUCIONES {
        text id PK
        text venta_id FK
        text usuario_id FK
        integer monto_devuelto_centavos
        text motivo
        text fecha
    }

    ANULACIONES {
        text id PK
        text venta_id FK
        text usuario_id FK
        text motivo
        text fecha
    }

    MOVIMIENTOS_STOCK {
        text id PK
        text producto_id FK
        text usuario_id FK
        text tipo
        integer cantidad
        integer stock_anterior
        integer stock_nuevo
        text referencia_tipo
        text referencia_id
        text motivo
        text proveedor_id FK
        text fecha
    }
```

## Cardinalidades principales

- Un usuario puede abrir muchas cajas.
- Una caja puede contener muchas ventas.
- Una venta pertenece a una caja.
- Una venta tiene uno o más detalles.
- Un producto puede tener muchos códigos de barras.
- Un producto puede participar en muchos detalles de venta.
- Una venta puede tener como máximo una anulación.
- Una venta puede tener como máximo una devolución.
- Todo movimiento de stock pertenece a un producto.
