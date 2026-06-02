# Kiosk Billing & Cash POS

Sistema de Facturación, Caja Registradora y Punto de Venta (POS) de control interno para kioscos, diseñado bajo un esquema **Single-Tenant** (monousuario / instancia aislada) para máxima velocidad operativa, consistencia de caja y control de inventario riguroso.

El sistema está optimizado para su ejecución en entornos locales o VPS dedicados, garantizando un inicio instantáneo y una interfaz fluida sin sobrecarga administrativa.

---

## 🚀 Arquitectura y Stack Tecnológico

El proyecto está estructurado de manera simple y robusta para garantizar tiempos de respuesta ínfimos y una excelente portabilidad:

- **Frontend (Punto de Venta):** 
  - **HTML5 & CSS3 Vanilla** (layouts de alta densidad con CSS Grid y Flexbox).
  - **JavaScript Vanilla (ES6+)**. 
  - Sin frameworks de SPA para garantizar un tiempo de carga inicial `< 1s` y control absoluto del DOM.
- **Backend (Servidor API):** 
  - **Python 3.10+** con **FastAPI** (asincrónico, alto rendimiento y tipado estático).
- **Base de Datos:** 
  - **SQLite 3** relacional monousuario.
  - Configuración optimizada de alto rendimiento en cada conexión:
    ```sql
    PRAGMA journal_mode = WAL;
    PRAGMA busy_timeout = 20000;
    PRAGMA foreign_keys = ON;
    PRAGMA temp_store = MEMORY;
    ```

---

## 🎨 Sistema de Diseño (Material 3 Alignment)

La interfaz del Punto de Venta (POS) está optimizada para pantallas táctiles pequeñas y operaciones intensivas de teclado (sin ratón).

### Tokens de Color (Modo Oscuro por Defecto)
*   **Color Primario (`#0284C7` - Sky Blue):** Foco actual, acciones principales, navegación activa.
*   **Éxito (`#16A34A` - Emerald Green):** Confirmación de checkout, totales de caja, vuelto correcto.
*   **Advertencia (`#D97706` - Amber):** Procesamiento de pagos, advertencia de bajo stock/modo offline.
*   **Error (`#DC2626` - Red):** Fuera de stock, cancelación de acciones, discrepancias de caja.
*   **Fondo Principal (`#0F172A` - Slate 900) y Contenedores (`#1E293B` - Slate 800)**.

### Tipografía
*   **Textos Generales:** Fuente sans-serif nativa del sistema (`ui-sans-serif, system-ui...`) para lecturas rápidas en pantalla.
*   **Datos Numéricos:** Monospace (`ui-monospace, Consolas...`) para códigos de barra, cantidades y alineación de precios en el carro.

---

## ⚙️ Módulos y Funcionalidades Principales

El sistema cubre los siguientes requisitos críticos del negocio distribuidos en tres áreas operativas:

### 1. Gestión de Caja, Turnos y Trazabilidad
*   **Apertura de Caja Obligatoria:** Formulario que exige el ingreso del monto inicial en centavos (`monto_inicial_centavos`) para habilitar la pantalla de ventas.
*   **Cierre de Caja Ciego:** El cajero declara el dinero físico existente al finalizar el turno sin ver el balance esperado del sistema. El backend calcula y registra de forma atómica la desviación de caja:
    $$\text{Desviación} = \text{Monto Declarado} - (\text{Monto Inicial} + \text{Ventas} - \text{Retiros})$$

### 2. Interfaz del Punto de Venta (POS)
*   **Carga por Código de Barras:** Detección automática en base a velocidad de ráfaga de entrada ($< 30\text{ ms}$) que añade el producto al carrito de forma instantánea sin perder el foco de búsqueda.
*   **Métodos de Pago & Vuelto:** Soporta pago en **Efectivo** (calculando vuelto en vivo) y **Digital** (vuelto automático de `$0.00`).
*   **Atajos de Teclado Globales:** Manejo completo del POS sin ratón:
    *   `F2` o `Espacio` para abrir el modal de Pago.
    *   `F9` para vaciar el carrito actual.
    *   `F4` o `*` para fraccionar cantidades o facturar por monto deseado (para productos pesables o sueltos).

### 3. Control Interno y Resiliencia
*   **Descuento de Stock Atómico:** Las ventas descuentan unidades del stock físico dentro de transacciones SQLite seguras (`ACID`). Si el stock cae por debajo del mínimo, se genera un flag de alerta visual.
*   **Impresión de Ticket No Fiscal:** Estilado especial CSS para `@media print` optimizado para impresoras térmicas de tickets (58mm y 80mm), ocultando la UI del POS al invocar `window.print()`.

---

## 💻 Estados Clave de la Interfaz

*   **Estado A: Caja Cerrada.** Bloqueo total de la pantalla de ventas mediante un fondo difuminado hasta que se complete exitosamente el modal de Apertura de Caja.
*   **Estado B: Modo Offline.** Cambia el indicador de red del header a un estado intermitente ámbar y guarda las transacciones localmente mediante IndexedDB en el navegador para sincronizar al volver la conexión.
*   **Estado C: Interfaz de Pago.** Modal con desenfoque de fondo (`backdrop-filter`) y calculadora interactiva de vuelto que resalta en verde tan pronto como el dinero recibido cubre el total.

---

## 🛠️ Requisitos de Desarrollo

*   **Python 3.10+**
*   **FastAPI** y servidor ASGI como **Uvicorn**.
*   **SQLite 3** instalado de forma nativa.
*   Navegador web moderno compatible con `backdrop-filter`, `PRAGMA` nativos de SQLite y APIs Web estándar.
