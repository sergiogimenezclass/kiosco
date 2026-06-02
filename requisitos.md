# Documento de Especificaciones Técnicas y Requisitos del Proyecto

## Sistema de Facturación y Caja Registradora para Kioscos (Single-Tenant MVP)

## 1. Introducción y Alcance del Proyecto

Este documento define las especificaciones técnicas, la arquitectura de datos, los requisitos funcionales y no funcionales, y las historias de usuario para el desarrollo del Mínimo Producto Viable (MVP) de un sistema de facturación y caja registradora de control interno para kioscos.

El sistema está diseñado bajo un esquema **Single-Tenant** (monousuario o instancia aislada por comercio) para ejecutarse de manera local (servidor en el punto de venta) o en una instancia cloud dedicada (VPS clonaviles). Su objetivo principal es asegurar la máxima velocidad operativa, la consistencia de caja y un control de inventario riguroso sin la complejidad de integración fiscal en la primera fase.

## 2. Stack Tecnológico Seleccionado

* **Frontend (Cliente POS):** HTML5 semi-estático, CSS3 (utilizando CSS Grid y Flexbox para layouts fluidos adaptados a terminales de alta densidad y pantallas táctiles), y JavaScript Vanilla (ES6+). No se utilizarán frameworks de SPA (Single Page Application) para garantizar un tiempo de inicio inferior a 1 segundo y un control total del ciclo de vida del DOM.

* **Backend (Servidor local/API):** Python 3.10+ utilizando el framework asincrónico **FastAPI**. Proporciona alto rendimiento, tipado estático en backend y generación automática de la especificación OpenAPI (Swagger).

* **Base de Datos:** **SQLite 3**. Se configura en modo monousuario, eliminando la sobrecarga de administración de motores relacionales más complejos en despliegues iniciales y simplificando las copias de seguridad de los comercios.

## 3. Arquitectura de Datos y Configuración de Base de Datos

Para mitigar los límites transaccionales de SQLite y garantizar que la interfaz web sea fluida, la base de datos debe operar bajo parámetros estrictos de rendimiento.

### 3.1. Script de Configuración Inicial (PRAGMA)

Cada conexión creada por el backend de Python debe ejecutar obligatoriamente las siguientes instrucciones:


-- Habilita el modo Write-Ahead Logging para permitir lecturas simultáneas durante transacciones de escritura
PRAGMA journal_mode = WAL;

-- Establece un tiempo de espera de 20 segundos antes de lanzar una excepción de base de datos bloqueada
PRAGMA busy_timeout = 20000;

-- Fuerza la validación de integridad referencial de las claves foráneas
PRAGMA foreign_keys = ON;

-- Almacena los índices y tablas temporales en la memoria RAM para acelerar las consultas complejas
PRAGMA temp_store = MEMORY;

## 4. Historias de Usuario (Completas y Sin Omisiones)

### Módulo 1: Gestión de Caja, Turnos y Trazabilidad de Dinero

#### HU-01: Apertura de Caja Obligatoria

* **Como:** Cajero del kiosco.

* **Quiero:** Registrar el monto inicial en efectivo en la caja registradora al iniciar mi turno de trabajo.

* **Para:** Que el sistema habilite los módulos de venta y se asocie cada transacción a mi sesión activa de manera transparente.

* **Criterios de Aceptación:**

  1. Si el usuario intenta acceder a la pantalla de ventas (`/ventas`) sin una caja en estado `ABIERTA`, la aplicación web debe redirigir de forma automática al formulario de apertura de caja (`/caja/apertura`).

  2. El formulario debe exigir el ingreso del campo `monto_inicial_centavos`. Este valor debe ser un entero no negativo representativo en centavos de la moneda local (ej: `$1500.50` se ingresa como `150050`).

  3. Al enviar el formulario, el sistema debe generar una petición `POST /api/cajas/apertura` que inserte un registro en la tabla `cajas` con un nuevo UUIDv4, el timestamp UTC actual, el estado inicial en `'ABIERTA'` y almacenar la variable en la sesión del cliente (localStorage o Cookie segura).

  4. El sistema debe permitir la carga rápida mediante teclado (tecla `Enter` para confirmar).

#### HU-02: Arqueo y Cierre de Caja (Cierre Ciego)

* **Como:** Cajero o administrador del kiosco.

* **Quiero:** Declarar el monto total de dinero físico existente en la caja de seguridad al finalizar mi jornada laboral.

* **Para:** Que el sistema compare automáticamente el conteo físico contra el balance registrado en el sistema y determine la existencia de faltantes o sobrantes de dinero.

* **Criterios de Aceptación:**

  1. La pantalla de cierre de caja debe presentar un formulario de ingreso de dinero físico en efectivo "ciego" (el sistema no debe mostrar el monto calculado esperado en pantalla al cajero para evitar fraudes o ajustes manuales).

  2. Al confirmar la declaración, el backend in Python debe calcular el total teórico esperado usando la fórmula de conciliación:
     

     $$
     \text{Monto Calculado} = \text{Monto Inicial} + \sum (\text{Ventas en Efectivo}) - \sum (\text{Retiros de Efectivo})
     $$

  3. El sistema debe registrar la desviación calculada:
     

     $$
     \text{Desviación} = \text{Monto Declarado} - \text{Monto Calculado}
     $$

  4. El estado de la caja en la tabla `cajas` debe actualizarse a `'CERRADA'`, y el campo `timestamp_cierre` debe rellenarse con la hora UTC actual.

  5. Se debe invalidar la sesión de caja activa en el cliente web, bloqueando inmediatamente la adición de nuevos productos al carro de compras.

### Módulo 2: Interfaz del Punto de Venta (Alta Densidad y Velocidad)

#### HU-03: Carga de Productos por Código de Barras

* **Como:** Cajero del kiosco.

* **Quiero:** Pasar un artículo bajo el lector de códigos de barras en cualquier momento mientras la pantalla de ventas esté activa.

* **Para:** Que el sistema identifique y agregue el producto de manera inmediata al carrito actual sin necesidad de usar el mouse o hacer clic en entradas de texto manualmente.

* **Criterios de Aceptación:**

  1. El código JavaScript en el frontend debe registrar un event listener global para el evento `keydown` en el objeto `document`.

  2. Debe diferenciar entre una entrada de teclado humana y el lector de códigos de barras basándose en la velocidad de la ráfaga de eventos (intervalo entre caracteres $< 30\text{ ms}$).

  3. Al capturar el código completo, debe realizar una búsqueda instantánea en memoria o caché local de productos.

  4. Si el código existe en la base de datos, el producto se añade al arreglo de elementos del carrito con una cantidad de $+1.0$. Si ya se encontraba en el carrito, se incrementa su cantidad actual por el incremento correspondiente de su unidad de medida.

  5. Si el código no se encuentra registrado en el sistema, la pantalla de ventas debe emitir una señal sonora sutil y mostrar una notificación visual temporal de error de "Producto no registrado" de color amarillo que no bloquee el foco del teclado.

#### HU-04: Procesamiento de Venta y Métodos de Pago

* **Como:** Cajero del kiosco.

* **Quiero:** Finalizar el proceso de compra de los artículos acumulados en el carrito, seleccionando el método de pago e ingresando la cantidad de dinero que entrega el cliente.

* **Para:** Registrar formalmente la transacción en la base de datos local y calcular el vuelto de manera exacta, reduciendo errores humanos.

* **Criterios de Aceptación:**

  1. Al presionar una tecla de acceso rápido configurada (ej: `Espacio` o `F2`), se debe abrir un modal de pago superpuesto.

  2. El modal debe permitir alternar el método de pago entre `'EFECTIVO'` y `'DIGITAL'` mediante las flechas de dirección del teclado (`Arriba`/`Abajo` o `Izquierda`/`Derecha`).

  3. Si el método seleccionado es `'EFECTIVO'`:

     * El sistema debe exigir el ingreso del monto entregado por el comprador.

     * Se debe calcular y mostrar el vuelto exacto con un tamaño de fuente destacado (mínimo `24px` o `text-3xl`).

     * El monto recibido debe ser estrictamente mayor o igual al total de la compra para poder proceder.

  4. Si el método seleccionado es `'DIGITAL'`:

     * El sistema asume que el monto recibido es igual al total de la transacción. El campo "Vuelto" debe mostrar automáticamente `$0.00` y quedar deshabilitado para edición.

  5. Al pulsar la tecla `Enter`, la venta se envía en formato JSON al backend y se guarda de forma atómica. Tras un guardado exitoso, el carrito de compras del frontend se vacía por completo y el foco vuelve automáticamente a la escucha de códigos de barras.

### Módulo 3: Control Interno y Sincronización de Stock

#### HU-05: Descuento Automático de Stock

* **Como:** Dueño de negocio / Administrador del kiosco.

* **Quiero:** Que el sistema debite las unidades vendidas directamente del stock de productos cada vez que se confirme una venta en la caja registradora.

* **Para:** Evitar la necesidad de auditorías manuales diarias y saber con precisión la mercadería disponible en góndola.

* **Criterios de Aceptación:**

  1. La inserción de la transacción de venta en la base de datos debe ser atómica (dentro de una transacción SQLite `BEGIN TRANSACTION` / `COMMIT`).

  2. Por cada ítem presente en `venta_detalles`, el backend debe realizar el decremento correspondiente:
     

     $$
     \text{Nuevo Stock} = \text{Stock Anterior} - \text{Cantidad Vendida}
     $$

  3. Si la operación resulta en un stock menor o igual al `stock_minimo` definido para ese producto, el sistema debe marcar el registro con un flag de alerta de bajo inventario.

  4. En la pantalla de ventas del frontend, si un producto tiene stock menor o igual a `0`, se debe mostrar un indicador de advertencia rojo ("Sin Stock") y bloquear su adición al carrito a menos que la configuración del negocio permita la venta con stock negativo (configurable).

#### HU-06: Impresión de Ticket no Fiscal de Control Interno

* **Como:** Cajero del kiosco.

* **Quiero:** Imprimir un ticket físico de control interno optimizado para tiras de papel de impresora térmica inmediatamente después de confirmar el pago de una venta.

* **Para:** Entregar un comprobante físico claro al cliente que detalla la mercadería adquirida y los valores asociados.

* **Criterios de Aceptación:**

  1. La confirmación del pago debe invocar la llamada nativa `window.print()` en el navegador del cliente.

  2. La aplicación debe contar con un bloque de estilos CSS específicos dentro de una directiva `@media print`.

  3. Bajo el contexto de impresión, se deben ocultar todos los elementos de la interfaz de usuario (botones, cabeceras del sistema, barras laterales, inputs de búsqueda y alertas).

  4. El ticket impreso debe formatearse de forma fluida para ajustarse a anchos comunes de impresoras de tickets térmicos (58mm o 80mm), forzando márgenes en cero y utilizando fuentes monoespaciadas para la alineación del listado de productos y totales.

#### HU-07: Producto Pesable / Venta por Monto (Fraccionados)

* **Como:** Cajero del kiosco.

* **Quiero:** Modificar la cantidad de un ítem en el carrito de compras ingresando valores decimales o establecer un valor monetario directo para fraccionar el peso de un producto a demanda.

* **Para:** Facturar adecuadamente artículos sueltos como caramelos sueltos, fiambres o frutas sin estar limitado a la facturación rígida por unidades enteras.

* **Criterios de Aceptación:**

  1. En la pantalla de ventas, al tener un ítem seleccionado en el carrito, se debe poder presionar una tecla de atajo rápido (ej: `F4` o `*` en el teclado numérico) para abrir un pequeño diálogo emergente de edición de cantidad.

  2. Si el producto está configurado con unidad de medida `'KILO'`, `'GRAMO'` o `'LITRO'`, el input numérico debe validar y admitir hasta tres decimales (ej: `0.350` representando gramos).

  3. El sistema debe permitir la venta inversa por monto fijo. Ejemplo: El cajero escribe un monto total de dinero (ej: `$500`) y el sistema calcula la cantidad fraccionaria resultante utilizando la fórmula:
     

     $$
     \text{Cantidad} = \frac{\text{Monto Deseado en Centavos}}{\text{Precio Unitario por Unidad en Centavos}}
     $$

  4. La cantidad calculada debe redondearse a tres cifras decimales antes de agregarse al carrito y antes de realizar el descuento de stock.

## 5. Requisitos Funcionales del Sistema (RF)

### 5.1. Módulo del Punto de Venta (POS)

* **RF-1.1:** El POS debe arrancar en modo pantalla completa optimizada, evitando scrollbars verticales o laterales innecesarios mediante el uso de contenedores con altura relativa al viewport (`vh` / `h-screen`).

* **RF-1.2:** Debe proveer un listado de "Acceso Rápido" en forma de cuadrícula (Grid) para productos que no poseen código de barras físico (ej: cigarrillos sueltos, encendedores, bolsas de hielo).

* **RF-1.3:** Debe contener un buscador predictivo de productos por texto que filtre coincidencias por nombre o descripción a medida que se tipea, con actualización en tiempo real en un intervalo máximo de `100ms`.

### 5.2. Módulo de Administración y Catálogo

* **RF-2.1:** Pantalla independiente para la gestión del catálogo (CRUD de productos): creación, lectura, actualización y eliminación de artículos.

* **RF-2.2:** Interfaz para el ajuste rápido de inventario (ingreso de mercadería) donde se pueda escanear un código de barras y actualizar de inmediato el stock disponible de forma sumatoria.

### 5.3. Módulo de Reportes de Caja

* **RF-3.1:** El sistema debe registrar un historial de todas las cajas cerradas con sus respectivas desviaciones monetarias para permitir la auditoría del dueño del negocio.

* **RF-3.2:** Vista analítica simple que resuma los totales recaudados divididos por tipo de cobro (Efectivo y Digital) correspondientes al día calendario en curso.

## 6. Requisitos No Funcionales del Sistema (RNF)

### 6.1. Rendimiento y Usabilidad

* **RNF-1.1:** El tiempo de renderizado e inserción de un producto al carrito tras ser escaneado por el lector de barras debe ser inferior a `50ms`.

* **RNF-1.2:** La interfaz gráfica del POS debe estar optimizada para entrada de teclado al 100%. El cajero debe poder abrir caja, escanear, cobrar, dar vuelto, imprimir ticket y cerrar caja utilizando únicamente atajos del teclado numérico y teclas de función (`F1-F12`).

* **RNF-1.3:** El diseño visual debe mantener altos contrastes cromáticos y botones de tamaño óptimo (mínimo `48px` de altura) para facilitar la manipulación táctil en pantallas de baja calidad física.

### 6.2. Confiabilidad y Resiliencia

* **RNF-2.1:** Las modificaciones de stock e inserción de ventas deben estar encapsuladas en bloques transaccionales ACID de SQLite. Bajo ninguna circunstancia de error del sistema o caída energética a mitad de operación se admitirá una venta registrada sin su respectiva deducción de stock, o viceversa.

* **RNF-2.2:** En caso de corte energético total del servidor de base de datos durante una escritura, SQLite debe recuperarse automáticamente utilizando el archivo del diario de transacciones (`-wal` y `-shm`) en el siguiente arranque del software.

### 6.3. Portabilidad y Despliegue

* **RNF-3.1:** El sistema completo debe pesar menos de `50MB` de almacenamiento en disco para el entorno del backend en Python y la base de datos vacía.

* **RNF-3.2:** El backend de Python debe ser ejecutable multiplataforma (compatible con Windows 10/11, macOS y distribuciones de Linux basadas en Debian/Ubuntu para facilitar la reutilización de hardware de computadoras antiguas en los comercios).

## 7. Estilo de Impresión Térmica (CSS @media print)

Para garantizar la correcta impresión sin distorsiones en ticketeadoras térmicas de 58mm y 80mm, el frontend debe implementar las siguientes directivas CSS en su hoja de estilos principal:

