# technical-spec.md

# Especificación Técnica - Kiosk Billing & Cash POS

## 1. Stack

### Frontend

- HTML5.
- CSS3.
- JavaScript Vanilla ES6+.
- Sin frameworks SPA.
- CSS Grid y Flexbox.
- localStorage para persistencia temporal del carrito.

### Backend

- Python 3.10+.
- FastAPI.
- Uvicorn.
- Pydantic.
- SQLite 3.

### Base de Datos

SQLite 3 con PRAGMAs obligatorios por conexión:

```sql
PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 20000;
PRAGMA foreign_keys = ON;
PRAGMA temp_store = MEMORY;
```

## 2. Arquitectura

Patrón recomendado:

```text
Controller / Router
  -> Service
    -> Repository
      -> SQLite
```

## 3. Estructura de proyecto

```text
app/
  main.py
  core/
    config.py
    security.py
    database.py
    permissions.py
  api/
    auth.py
    usuarios.py
    cajas.py
    productos.py
    ventas.py
    stock.py
    reportes.py
  schemas/
    auth.py
    usuario.py
    caja.py
    producto.py
    venta.py
    stock.py
  services/
    auth_service.py
    caja_service.py
    producto_service.py
    venta_service.py
    stock_service.py
    reporte_service.py
  repositories/
    usuario_repository.py
    caja_repository.py
    producto_repository.py
    venta_repository.py
    stock_repository.py
  static/
    css/
    js/
  templates/
tests/
database/
  schema.sql
  seed.sql
docs/
```

## 4. Seguridad

- Passwords hasheados con bcrypt.
- JWT o sesión segura.
- Expiración de sesión configurable.
- Protección de endpoints por rol.
- Nunca devolver password_hash.
- Validación server-side en todos los endpoints.

## 5. Permisos técnicos

| Recurso | Cajero | Supervisor | Administrador |
|---|---:|---:|---:|
| Login | Sí | Sí | Sí |
| Crear usuario | No | No | Sí |
| Abrir caja | Sí | Sí | Sí |
| Cerrar caja | No | Sí | Sí |
| Ingresos/Retiros | No | Sí | Sí |
| Vender | Sí | Sí | Sí |
| Aplicar descuento | No | Sí | Sí |
| Anular venta | No | Sí | Sí |
| Devolver venta | No | Sí | Sí |
| Ajustar stock | No | Sí | Sí |
| Gestionar productos | No | Sí | Sí |
| Ver reportes | No | Sí | Sí |

## 6. Transacciones

Deben ejecutarse dentro de transacción:

- Apertura de caja.
- Cierre de caja.
- Venta.
- Anulación.
- Devolución.
- Ingreso/retiro de caja.
- Ajuste de stock.
- Ingreso de mercadería.

## 7. Manejo de errores

Formato estándar:

```json
{
  "error": {
    "code": "STOCK_INSUFICIENTE",
    "message": "No hay stock suficiente para completar la operación",
    "details": {}
  }
}
```

## 8. Códigos de error sugeridos

- AUTH_INVALID_CREDENTIALS
- AUTH_FORBIDDEN
- USER_NOT_FOUND
- CAJA_ALREADY_OPEN
- CAJA_NOT_OPEN
- CAJA_CLOSE_FORBIDDEN
- PRODUCT_NOT_FOUND
- BARCODE_NOT_FOUND
- BARCODE_DUPLICATED
- STOCK_INSUFICIENTE
- DISCOUNT_EXCEEDS_LIMIT
- SALE_NOT_FOUND
- SALE_ALREADY_CANCELLED
- SALE_ALREADY_RETURNED
- SALE_CANCEL_ONLY_SAME_DAY
- VALIDATION_ERROR

## 9. Frontend POS

### Requisitos

- 100vw / 100vh recomendado.
- Sin scroll global.
- Dos columnas:
  - catálogo 65%;
  - carrito 35%.
- Foco persistente en búsqueda/scanner.
- Scanner detectado por ráfaga < 30ms.
- Búsqueda predictiva <= 100ms.
- Carrito persistente en localStorage.
- F9 limpia carrito solo con confirmación.
- Error de scanner con sonido y alerta visual.

## 10. Persistencia del carrito

localStorage key:

```text
kiosk_pos_cart
```

Debe incluir:

- productos;
- cantidades;
- descuentos;
- caja_id;
- timestamp.

Si caja_id no coincide con caja actual, descartar carrito.

## 11. Exportaciones

CSV y Excel generados desde backend.
PDF puede generarse como HTML imprimible o librería PDF.

## 12. Rendimiento

- Agregado scanner a carrito < 50ms.
- Búsqueda visible < 100ms.
- Inicio de UI < 1s.
- Endpoints críticos < 200ms en entorno local.
