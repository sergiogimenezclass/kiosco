-- database-schema.sql
-- Kiosk Billing & Cash POS - SQLite Schema

PRAGMA journal_mode = WAL;
PRAGMA busy_timeout = 20000;
PRAGMA foreign_keys = ON;
PRAGMA temp_store = MEMORY;

CREATE TABLE usuarios (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    rol TEXT NOT NULL CHECK (rol IN ('ADMINISTRADOR','SUPERVISOR','CAJERO')),
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
    created_at TEXT NOT NULL
);

CREATE TABLE cajas (
    id TEXT PRIMARY KEY,
    usuario_apertura_id TEXT NOT NULL,
    usuario_cierre_id TEXT,
    estado TEXT NOT NULL CHECK (estado IN ('ABIERTA','CERRADA')),
    monto_inicial_centavos INTEGER NOT NULL CHECK (monto_inicial_centavos >= 0),
    monto_declarado_centavos INTEGER CHECK (monto_declarado_centavos IS NULL OR monto_declarado_centavos >= 0),
    monto_esperado_centavos INTEGER,
    desviacion_centavos INTEGER,
    fecha_apertura TEXT NOT NULL,
    fecha_cierre TEXT,
    FOREIGN KEY (usuario_apertura_id) REFERENCES usuarios(id),
    FOREIGN KEY (usuario_cierre_id) REFERENCES usuarios(id)
);

CREATE UNIQUE INDEX idx_unica_caja_abierta ON cajas(estado) WHERE estado = 'ABIERTA';

CREATE TABLE movimientos_caja (
    id TEXT PRIMARY KEY,
    caja_id TEXT NOT NULL,
    usuario_id TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('INGRESO','RETIRO')),
    monto_centavos INTEGER NOT NULL CHECK (monto_centavos > 0),
    motivo TEXT NOT NULL,
    fecha TEXT NOT NULL,
    FOREIGN KEY (caja_id) REFERENCES cajas(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE categorias (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE
);

CREATE TABLE marcas (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE
);

CREATE TABLE proveedores (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    telefono TEXT,
    email TEXT
);

CREATE TABLE productos (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    categoria_id TEXT NOT NULL,
    marca_id TEXT,
    proveedor_id TEXT,
    precio_venta_centavos INTEGER NOT NULL CHECK (precio_venta_centavos > 0),
    stock_actual INTEGER NOT NULL DEFAULT 0 CHECK (stock_actual >= 0),
    stock_minimo INTEGER NOT NULL DEFAULT 0 CHECK (stock_minimo >= 0),
    unidad_medida TEXT NOT NULL CHECK (unidad_medida IN ('UNIDAD','GRAMO','MILILITRO')),
    imagen_url TEXT,
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (categoria_id) REFERENCES categorias(id),
    FOREIGN KEY (marca_id) REFERENCES marcas(id),
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
);

CREATE INDEX idx_productos_nombre ON productos(nombre);
CREATE INDEX idx_productos_categoria ON productos(categoria_id);
CREATE INDEX idx_productos_stock_bajo ON productos(stock_actual, stock_minimo);

CREATE TABLE codigos_barras (
    id TEXT PRIMARY KEY,
    producto_id TEXT NOT NULL,
    codigo TEXT NOT NULL UNIQUE,
    principal INTEGER NOT NULL DEFAULT 0 CHECK (principal IN (0,1)),
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);

CREATE INDEX idx_codigos_barras_producto ON codigos_barras(producto_id);

CREATE TABLE accesos_rapidos (
    id TEXT PRIMARY KEY,
    producto_id TEXT NOT NULL,
    etiqueta TEXT NOT NULL,
    orden INTEGER NOT NULL,
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);

CREATE UNIQUE INDEX idx_accesos_rapidos_orden ON accesos_rapidos(orden);

CREATE TABLE ventas (
    id TEXT PRIMARY KEY,
    caja_id TEXT NOT NULL,
    usuario_id TEXT NOT NULL,
    estado TEXT NOT NULL CHECK (estado IN ('COMPLETADA','ANULADA','DEVUELTA')),
    metodo_pago TEXT NOT NULL CHECK (metodo_pago IN ('EFECTIVO','DIGITAL')),
    subtotal_centavos INTEGER NOT NULL CHECK (subtotal_centavos >= 0),
    descuento_items_centavos INTEGER NOT NULL DEFAULT 0 CHECK (descuento_items_centavos >= 0),
    descuento_venta_centavos INTEGER NOT NULL DEFAULT 0 CHECK (descuento_venta_centavos >= 0),
    total_centavos INTEGER NOT NULL CHECK (total_centavos >= 0),
    monto_recibido_centavos INTEGER NOT NULL CHECK (monto_recibido_centavos >= 0),
    vuelto_centavos INTEGER NOT NULL DEFAULT 0 CHECK (vuelto_centavos >= 0),
    fecha TEXT NOT NULL,
    FOREIGN KEY (caja_id) REFERENCES cajas(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE INDEX idx_ventas_fecha ON ventas(fecha);
CREATE INDEX idx_ventas_caja ON ventas(caja_id);
CREATE INDEX idx_ventas_usuario ON ventas(usuario_id);
CREATE INDEX idx_ventas_estado ON ventas(estado);

CREATE TABLE venta_detalles (
    id TEXT PRIMARY KEY,
    venta_id TEXT NOT NULL,
    producto_id TEXT NOT NULL,
    nombre_producto_snapshot TEXT NOT NULL,
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    unidad_medida_snapshot TEXT NOT NULL,
    precio_unitario_centavos INTEGER NOT NULL CHECK (precio_unitario_centavos > 0),
    descuento_centavos INTEGER NOT NULL DEFAULT 0 CHECK (descuento_centavos >= 0),
    subtotal_centavos INTEGER NOT NULL CHECK (subtotal_centavos >= 0),
    total_linea_centavos INTEGER NOT NULL CHECK (total_linea_centavos >= 0),
    FOREIGN KEY (venta_id) REFERENCES ventas(id),
    FOREIGN KEY (producto_id) REFERENCES productos(id)
);

CREATE INDEX idx_venta_detalles_venta ON venta_detalles(venta_id);
CREATE INDEX idx_venta_detalles_producto ON venta_detalles(producto_id);

CREATE TABLE devoluciones (
    id TEXT PRIMARY KEY,
    venta_id TEXT NOT NULL UNIQUE,
    usuario_id TEXT NOT NULL,
    monto_devuelto_centavos INTEGER NOT NULL CHECK (monto_devuelto_centavos >= 0),
    motivo TEXT,
    fecha TEXT NOT NULL,
    FOREIGN KEY (venta_id) REFERENCES ventas(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE anulaciones (
    id TEXT PRIMARY KEY,
    venta_id TEXT NOT NULL UNIQUE,
    usuario_id TEXT NOT NULL,
    motivo TEXT,
    fecha TEXT NOT NULL,
    FOREIGN KEY (venta_id) REFERENCES ventas(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE movimientos_stock (
    id TEXT PRIMARY KEY,
    producto_id TEXT NOT NULL,
    usuario_id TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo IN ('VENTA','DEVOLUCION','ANULACION','AJUSTE','INGRESO')),
    cantidad INTEGER NOT NULL,
    stock_anterior INTEGER NOT NULL CHECK (stock_anterior >= 0),
    stock_nuevo INTEGER NOT NULL CHECK (stock_nuevo >= 0),
    referencia_tipo TEXT,
    referencia_id TEXT,
    motivo TEXT,
    proveedor_id TEXT,
    fecha TEXT NOT NULL,
    FOREIGN KEY (producto_id) REFERENCES productos(id),
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
);

CREATE INDEX idx_mov_stock_producto ON movimientos_stock(producto_id);
CREATE INDEX idx_mov_stock_fecha ON movimientos_stock(fecha);
CREATE INDEX idx_mov_stock_tipo ON movimientos_stock(tipo);

CREATE TABLE configuracion (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL
);

INSERT INTO configuracion (clave, valor) VALUES
('descuento_maximo_porcentaje', '50'),
('moneda', 'ARS'),
('nombre_comercio', 'Kiosco');
