# api-spec.md

# API REST - Kiosk Billing & Cash POS

## Convenciones

Base path:

```text
/api
```

Formato de error:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Mensaje legible",
    "details": {}
  }
}
```

## Auth

### POST /api/auth/login

Request:

```json
{
  "username": "cajero1",
  "password": "secret"
}
```

Response:

```json
{
  "access_token": "jwt",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "nombre": "Juan",
    "rol": "CAJERO"
  }
}
```

### GET /api/auth/me

Devuelve usuario autenticado.

### POST /api/auth/logout

Invalida sesión del lado cliente.

## Usuarios

### GET /api/usuarios

Roles: ADMINISTRADOR.

### POST /api/usuarios

Roles: ADMINISTRADOR.

```json
{
  "nombre": "Juan Pérez",
  "username": "juan",
  "password": "123456",
  "rol": "CAJERO"
}
```

### PATCH /api/usuarios/{id}/desactivar

Roles: ADMINISTRADOR.

### PATCH /api/usuarios/{id}/password

Roles: ADMINISTRADOR.

## Caja

### GET /api/cajas/actual

Devuelve caja abierta o null.

### POST /api/cajas/apertura

Roles: CAJERO, SUPERVISOR, ADMINISTRADOR.

```json
{
  "monto_inicial_centavos": 500000
}
```

### POST /api/cajas/cierre

Roles: SUPERVISOR, ADMINISTRADOR.

```json
{
  "monto_declarado_centavos": 1250000
}
```

### POST /api/cajas/{id}/reabrir

Roles: ADMINISTRADOR.

### GET /api/cajas/historial

Roles: SUPERVISOR, ADMINISTRADOR.

## Movimientos de caja

### POST /api/movimientos-caja

Roles: SUPERVISOR, ADMINISTRADOR.

```json
{
  "tipo": "RETIRO",
  "monto_centavos": 100000,
  "motivo": "Pago proveedor"
}
```

### GET /api/movimientos-caja

Roles: SUPERVISOR, ADMINISTRADOR.

## Catálogo

### Categorías

- GET /api/categorias
- POST /api/categorias
- PUT /api/categorias/{id}
- DELETE /api/categorias/{id}

Roles escritura: SUPERVISOR, ADMINISTRADOR.

### Marcas

- GET /api/marcas
- POST /api/marcas
- PUT /api/marcas/{id}
- DELETE /api/marcas/{id}

Roles escritura: SUPERVISOR, ADMINISTRADOR.

### Proveedores

- GET /api/proveedores
- POST /api/proveedores
- PUT /api/proveedores/{id}
- DELETE /api/proveedores/{id}

Roles escritura: SUPERVISOR, ADMINISTRADOR.

## Productos

### GET /api/productos

Query params:
- q
- categoria_id
- marca_id
- activo

### GET /api/productos/{id}

### GET /api/productos/codigo/{codigo}

Busca por código de barras.

### POST /api/productos

Roles: SUPERVISOR, ADMINISTRADOR.

```json
{
  "nombre": "Coca Cola 500ml",
  "descripcion": "",
  "categoria_id": "uuid",
  "marca_id": "uuid",
  "proveedor_id": "uuid",
  "precio_venta_centavos": 150000,
  "stock_actual": 20,
  "stock_minimo": 5,
  "unidad_medida": "UNIDAD",
  "imagen_url": null,
  "codigos_barras": ["779000000001"]
}
```

### PUT /api/productos/{id}

Roles: SUPERVISOR, ADMINISTRADOR.

### DELETE /api/productos/{id}

Roles: SUPERVISOR, ADMINISTRADOR.

Debe fallar si producto tiene historial.

## Accesos rápidos

- GET /api/accesos-rapidos
- POST /api/accesos-rapidos
- PUT /api/accesos-rapidos/{id}
- DELETE /api/accesos-rapidos/{id}

Roles escritura: SUPERVISOR, ADMINISTRADOR.

## Ventas

### POST /api/ventas

Roles: CAJERO, SUPERVISOR, ADMINISTRADOR.

```json
{
  "metodo_pago": "EFECTIVO",
  "items": [
    {
      "producto_id": "uuid",
      "cantidad": 2,
      "descuento_centavos": 0
    }
  ],
  "descuento_venta_centavos": 0,
  "monto_recibido_centavos": 500000
}
```

Response:

```json
{
  "id": "uuid",
  "estado": "COMPLETADA",
  "total_centavos": 300000,
  "vuelto_centavos": 200000
}
```

### GET /api/ventas

Roles: SUPERVISOR, ADMINISTRADOR.

Filtros:
- desde
- hasta
- cajero_id
- metodo_pago
- estado

### GET /api/ventas/{id}

Roles: SUPERVISOR, ADMINISTRADOR.

### POST /api/ventas/{id}/anular

Roles: SUPERVISOR, ADMINISTRADOR.

```json
{
  "motivo": null
}
```

### POST /api/ventas/{id}/devolver

Roles: SUPERVISOR, ADMINISTRADOR.

```json
{
  "motivo": null
}
```

## Stock

### POST /api/stock/ajuste

Roles: SUPERVISOR, ADMINISTRADOR.

```json
{
  "producto_id": "uuid",
  "cantidad_delta": 10,
  "motivo": "Ajuste por conteo físico"
}
```

### POST /api/stock/ingreso

Roles: SUPERVISOR, ADMINISTRADOR.

```json
{
  "producto_id": "uuid",
  "cantidad": 100,
  "proveedor_id": "uuid",
  "motivo": "Ingreso de mercadería"
}
```

### GET /api/stock/movimientos

Roles: SUPERVISOR, ADMINISTRADOR.

### GET /api/stock/bajo-minimo

Roles: SUPERVISOR, ADMINISTRADOR.

## Reportes

### GET /api/reportes/ventas-diarias

Roles: SUPERVISOR, ADMINISTRADOR.

### GET /api/reportes/cajas

Roles: SUPERVISOR, ADMINISTRADOR.

### GET /api/reportes/ranking-productos

Roles: SUPERVISOR, ADMINISTRADOR.

Query:
- ordenar_por=cantidad|monto

### GET /api/reportes/stock-bajo

Roles: SUPERVISOR, ADMINISTRADOR.

### GET /api/reportes/{tipo}/export

Roles: según acceso al reporte.

Query:
- format=csv|xlsx|pdf
