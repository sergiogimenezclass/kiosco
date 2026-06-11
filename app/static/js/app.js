/* ==========================================================================
   KIOSCO POS - LÓGICA DE APLICACIÓN (VANILLA JS)
   ========================================================================== */

// --- ESTADO GLOBAL ---
const state = {
    token: localStorage.getItem('kiosco_token') || null,
    user: null,
    activeCaja: null,
    products: [],         // Todos los productos activos en catálogo
    quickAccesses: [],     // Configuraciones de accesos rápidos
    cart: JSON.parse(localStorage.getItem('kiosco_cart')) || [],
    searchResults: [],     // Resultados de la búsqueda predictiva actual
    paymentMethod: 'EFECTIVO' // EFECTIVO o DIGITAL
};

// --- CONFIGURACIÓN ---
const API_URL = '/api';

// ==========================================================================
// UTILIDADES GENERALES
// ==========================================================================

// Formatear centavos a Pesos ($ XX,XX)
function formatMoney(cents) {
    const pesos = cents / 100;
    return pesos.toLocaleString('es-AR', {
        style: 'currency',
        currency: 'ARS',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

// Sonido de Error (Sintetizador Web Audio API)
function playErrorSound() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(140, ctx.currentTime); // Frecuencia baja
        
        gain.gain.setValueAtTime(0.15, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.3);
        
        osc.connect(gain);
        gain.connect(ctx.destination);
        
        osc.start();
        osc.stop(ctx.currentTime + 0.3);
    } catch (e) {
        console.error("No se pudo reproducir sonido de error:", e);
    }
}

// Sonido de Éxito (Sintetizador Web Audio API)
function playSuccessSound() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        
        osc.type = 'sine';
        osc.frequency.setValueAtTime(880, ctx.currentTime); // Frecuencia alta (La 5)
        
        gain.gain.setValueAtTime(0.1, ctx.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.15);
        
        osc.connect(gain);
        gain.connect(ctx.destination);
        
        osc.start();
        osc.stop(ctx.currentTime + 0.15);
    } catch (e) {
        console.error("No se pudo reproducir sonido de éxito:", e);
    }
}

// Mostrar Notificaciones Flotantes (Toasts)
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    let icon = '';
    if (type === 'success') {
        icon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:8px;"><polyline points="20 6 9 17 4 12"/></svg>';
    } else if (type === 'error') {
        icon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:8px;"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';
    } else if (type === 'warning') {
        icon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right:8px;"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>';
    }

    toast.innerHTML = `
        <div style="display:flex; align-items:center;">
            ${icon}
            <span>${message}</span>
        </div>
        <button class="toast-close">&times;</button>
    `;

    container.appendChild(toast);

    // Cerrar automáticamente en 4 segundos
    const autoClose = setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 150);
    }, 4000);

    // Cerrar al hacer clic en la X
    toast.querySelector('.toast-close').addEventListener('click', () => {
        clearTimeout(autoClose);
        toast.remove();
    });
}

// Fetch general con inyección de Token Bearer
async function apiRequest(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
    }

    const config = {
        ...options,
        headers
    };

    const response = await fetch(`${API_URL}${endpoint}`, config);
    
    if (response.status === 401) {
        // Token expirado o inválido
        logout();
        throw new Error("Sesión expirada. Inicie sesión nuevamente.");
    }
    
    return response;
}

// ==========================================================================
// AUTENTICACIÓN
// ==========================================================================

async function checkAuth() {
    if (!state.token) {
        showModal('modal-login');
        return;
    }

    try {
        const response = await apiRequest('/auth/me');
        if (response.ok) {
            state.user = await response.json();
            document.getElementById('modal-login').classList.add('hidden');
            document.getElementById('app').classList.remove('hidden');
            
            // Mostrar info en Header
            document.getElementById('header-user-name').textContent = state.user.nombre;
            document.getElementById('header-user-role').textContent = state.user.rol;
            
            // Inicializar POS
            initializePOS();
        } else {
            throw new Error("Error verificando sesión");
        }
    } catch (error) {
        console.error(error);
        logout();
    }
}

async function login(username, password) {
    const errorDiv = document.getElementById('login-error');
    errorDiv.classList.add('hidden');

    try {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch(`${API_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: formData
        });

        if (response.ok) {
            const data = await response.json();
            state.token = data.access_token;
            state.user = data.user;
            localStorage.setItem('kiosco_token', data.access_token);
            
            document.getElementById('modal-login').classList.add('hidden');
            document.getElementById('app').classList.remove('hidden');
            
            document.getElementById('header-user-name').textContent = state.user.nombre;
            document.getElementById('header-user-role').textContent = state.user.rol;
            
            playSuccessSound();
            showToast(`¡Bienvenido, ${state.user.nombre}!`, 'success');
            initializePOS();
        } else {
            throw new Error("Credenciales inválidas");
        }
    } catch (e) {
        playErrorSound();
        errorDiv.textContent = e.message || "Error de conexión al servidor";
        errorDiv.classList.remove('hidden');
    }
}

function logout() {
    state.token = null;
    state.user = null;
    state.activeCaja = null;
    localStorage.removeItem('kiosco_token');
    
    // Ocultar app y mostrar login
    document.getElementById('app').classList.add('hidden');
    hideAllModals();
    showModal('modal-login');
    document.getElementById('form-login').reset();
}

// ==========================================================================
// CICLO DE VIDA DE CAJA
// ==========================================================================

async function checkCajaStatus() {
    try {
        const response = await apiRequest('/cajas/actual');
        if (response.ok) {
            const data = await response.json();
            const badge = document.getElementById('caja-badge');
            
            if (data) {
                // Caja ABIERTA
                state.activeCaja = data;
                badge.textContent = `Caja Abierta (ID: ${data.id.substring(0, 8)})`;
                badge.className = 'caja-badge abierta';
                document.getElementById('modal-apertura').classList.add('hidden');
                
                // Mostrar botones de control para Supervisor / Admin
                if (state.user.rol === 'SUPERVISOR' || state.user.rol === 'ADMINISTRADOR') {
                    document.getElementById('btn-movimiento-caja').classList.remove('hidden');
                    document.getElementById('btn-cerrar-caja').classList.remove('hidden');
                } else {
                    document.getElementById('btn-movimiento-caja').classList.add('hidden');
                    document.getElementById('btn-cerrar-caja').classList.add('hidden');
                }
            } else {
                // Caja CERRADA
                state.activeCaja = null;
                badge.textContent = "Caja Cerrada";
                badge.className = 'caja-badge cerrada';
                
                document.getElementById('btn-movimiento-caja').classList.add('hidden');
                document.getElementById('btn-cerrar-caja').classList.add('hidden');
                
                // Vaciar el carrito inmediatamente si se cerró la caja
                vaciarCarritoSinConfirmar();
                
                // Mostrar modal de apertura bloqueante
                showModal('modal-apertura');
            }
        }
    } catch (error) {
        showToast("Error comprobando el estado de la caja", 'error');
    }
}

async function abrirCaja(montoInicialPesos) {
    const errorDiv = document.getElementById('apertura-error');
    errorDiv.classList.add('hidden');
    
    const montoCentavos = Math.round(montoInicialPesos * 100);

    try {
        const response = await apiRequest('/cajas/apertura', {
            method: 'POST',
            body: JSON.stringify({ monto_inicial_centavos: montoCentavos })
        });

        if (response.ok) {
            playSuccessSound();
            showToast("¡Caja abierta correctamente!", "success");
            document.getElementById('modal-apertura').classList.add('hidden');
            checkCajaStatus();
        } else {
            const err = await response.json();
            throw new Error(err.error?.message || "Error al abrir la caja");
        }
    } catch (e) {
        playErrorSound();
        errorDiv.textContent = e.message;
        errorDiv.classList.remove('hidden');
    }
}

async function cerrarCaja(montoDeclaradoPesos) {
    const errorDiv = document.getElementById('cierre-error');
    errorDiv.classList.add('hidden');
    
    const montoCentavos = Math.round(montoDeclaradoPesos * 100);

    try {
        const response = await apiRequest('/cajas/cierre', {
            method: 'POST',
            body: JSON.stringify({ monto_declared_centavos: montoCentavos, monto_declarado_centavos: montoCentavos }) // compatibilidad
        });

        if (response.ok) {
            const data = await response.json();
            playSuccessSound();
            
            // Mostrar reporte rápido de desviación
            const desviacion = data.desviacion_centavos / 100;
            const desc = desviacion === 0 
                ? "Cuadre perfecto ($0.00)" 
                : (desviacion > 0 ? `Sobrante de: ${formatMoney(data.desviacion_centavos)}` : `Faltante de: ${formatMoney(Math.abs(data.desviacion_centavos))}`);
            
            alert(`Caja cerrada exitosamente.\n\nMonto esperado: ${formatMoney(data.monto_esperado_centavos)}\nMonto declarado: ${formatMoney(data.monto_declarado_centavos)}\nDesviación: ${desc}`);
            
            document.getElementById('modal-cierre').classList.add('hidden');
            checkCajaStatus();
        } else {
            const err = await response.json();
            throw new Error(err.error?.message || "Error al cerrar la caja");
        }
    } catch (e) {
        playErrorSound();
        errorDiv.textContent = e.message;
        errorDiv.classList.remove('hidden');
    }
}

async function registrarMovimiento(tipo, montoPesos, motivo) {
    const errorDiv = document.getElementById('movimiento-error');
    errorDiv.classList.add('hidden');
    
    const montoCentavos = Math.round(montoPesos * 100);

    try {
        const response = await apiRequest('/movimientos-caja', {
            method: 'POST',
            body: JSON.stringify({ tipo, monto_centavos: montoCentavos, motivo })
        });

        if (response.ok) {
            playSuccessSound();
            showToast(`Movimiento de ${tipo.toLowerCase()} registrado correctamente`, 'success');
            document.getElementById('modal-movimiento').classList.add('hidden');
            document.getElementById('form-movimiento').reset();
        } else {
            const err = await response.json();
            throw new Error(err.error?.message || "Error al registrar movimiento");
        }
    } catch (e) {
        playErrorSound();
        errorDiv.textContent = e.message;
        errorDiv.classList.remove('hidden');
    }
}

// ==========================================================================
// CATÁLOGO Y BÚSQUEDA PREDICTIVA
// ==========================================================================

async function fetchProducts() {
    try {
        const response = await apiRequest('/productos?activo=1');
        if (response.ok) {
            state.products = await response.json();
        }
    } catch (error) {
        console.error("Error cargando productos:", error);
    }
}

async function fetchQuickAccesses() {
    try {
        const response = await apiRequest('/accesos-rapidos');
        if (response.ok) {
            state.quickAccesses = await response.json();
            renderQuickAccessGrid();
        }
    } catch (error) {
        console.error("Error cargando accesos rápidos:", error);
    }
}

function renderQuickAccessGrid() {
    const grid = document.getElementById('quick-access-grid');
    if (!grid) return;
    grid.innerHTML = '';

    // Ordenar por campo 'orden'
    const sorted = [...state.quickAccesses].sort((a, b) => a.orden - b.orden);

    sorted.forEach(ar => {
        // Encontrar datos de producto
        const p = state.products.find(prod => prod.id === ar.producto_id);
        if (!p || p.activo !== 1) return;

        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn-quick';
        btn.innerHTML = `
            <span>${ar.etiqueta}</span>
            <span class="price">${formatMoney(p.precio_venta_centavos)}</span>
        `;
        
        btn.addEventListener('click', () => {
            agregarAlCarrito(p);
        });

        grid.appendChild(btn);
    });
}

// Búsqueda en tiempo real
function filterResults(query) {
    const resultsBody = document.getElementById('search-results-body');
    if (!resultsBody) return;

    if (!query || query.trim().length === 0) {
        resultsBody.innerHTML = '<tr><td colspan="5" class="text-muted text-center py-4">Ingresa un término de búsqueda para ver productos.</td></tr>';
        return;
    }

    const cleanQuery = query.toLowerCase().trim();
    
    // Filtrar localmente
    const filtered = state.products.filter(p => 
        p.nombre.toLowerCase().includes(cleanQuery) || 
        (p.descripcion && p.descripcion.toLowerCase().includes(cleanQuery)) ||
        p.codigos_barras.some(code => code.includes(cleanQuery))
    );

    if (filtered.length === 0) {
        resultsBody.innerHTML = '<tr><td colspan="5" class="text-muted text-center py-4">No se encontraron productos coincidentes.</td></tr>';
        return;
    }

    resultsBody.innerHTML = '';
    filtered.slice(0, 15).forEach(p => {
        const tr = document.createElement('tr');
        
        // Stock render
        let stockBadge = '';
        if (p.stock_actual <= 0) {
            stockBadge = `<span class="stock-tag empty">Agotado (0)</span>`;
        } else if (p.stock_actual <= p.stock_minimo) {
            stockBadge = `<span class="stock-tag low">Bajo (${p.stock_actual} ${p.unidad_medida.toLowerCase()}(s))</span>`;
        } else {
            stockBadge = `<span class="stock-tag normal">${p.stock_actual} ${p.unidad_medida.toLowerCase()}(s)</span>`;
        }

        const barcodeDisplay = p.codigos_barras.length > 0 ? p.codigos_barras[0] : '-';

        tr.innerHTML = `
            <td>
                <div style="font-weight: 500;">${p.nombre}</div>
                <div style="font-size:0.75rem; color:var(--color-text-muted);">${p.descripcion || ''}</div>
            </td>
            <td style="font-family:var(--font-mono);">${barcodeDisplay}</td>
            <td class="text-right price-tag">${formatMoney(p.precio_venta_centavos)}</td>
            <td class="text-center">${stockBadge}</td>
            <td class="text-center">
                <button class="btn btn-primary btn-sm btn-add-item" ${p.stock_actual <= 0 ? 'disabled' : ''}>+ Agregar</button>
            </td>
        `;

        tr.querySelector('.btn-add-item').addEventListener('click', () => {
            agregarAlCarrito(p);
        });

        resultsBody.appendChild(tr);
    });
}

// Búsqueda por Escáner
async function processScannedCode(code) {
    // Buscar primero en los productos cacheados
    let product = state.products.find(p => p.codigos_barras.includes(code));

    if (!product) {
        // Habilitar consulta fallback al backend por si el producto no estaba cargado
        try {
            const response = await apiRequest(`/productos/codigo/${code}`);
            if (response.ok) {
                product = await response.json();
                // Agregar temporalmente al listado en memoria
                state.products.push(product);
            }
        } catch (e) {
            console.error("Error buscando código en backend:", e);
        }
    }

    if (product) {
        agregarAlCarrito(product);
    } else {
        playErrorSound();
        showToast(`Código de barra no registrado: ${code}`, 'error');
    }
}

// ==========================================================================
// CARRITO DE COMPRAS Y TOTALES
// ==========================================================================

function agregarAlCarrito(product) {
    if (!state.activeCaja) {
        playErrorSound();
        showToast("Debes abrir la caja antes de registrar ventas", "warning");
        showModal('modal-apertura');
        return;
    }

    if (product.stock_actual <= 0) {
        playErrorSound();
        showToast(`Sin Stock: ${product.nombre} no tiene stock disponible.`, 'error');
        return;
    }

    const existingItem = state.cart.find(item => item.product.id === product.id);
    
    if (existingItem) {
        if (existingItem.cantidad >= product.stock_actual) {
            playErrorSound();
            showToast(`Límite alcanzado: Solo hay ${product.stock_actual} unidades de ${product.nombre} en stock.`, 'error');
            return;
        }
        existingItem.cantidad += 1;
    } else {
        state.cart.push({
            product,
            cantidad: 1
        });
    }

    playSuccessSound();
    saveCart();
    renderCart();
}

function actualizarCantidadItem(productId, qty) {
    const item = state.cart.find(item => item.product.id === productId);
    if (!item) return;

    if (qty <= 0) {
        eliminarItemCarrito(productId);
        return;
    }

    if (qty > item.product.stock_actual) {
        playErrorSound();
        showToast(`Stock insuficiente: Solo hay ${item.product.stock_actual} unidades disponibles.`, 'error');
        renderCart(); // Reestablecer valor viejo en input
        return;
    }

    item.cantidad = qty;
    saveCart();
    renderCart();
}

function eliminarItemCarrito(productId) {
    state.cart = state.cart.filter(item => item.product.id !== productId);
    saveCart();
    renderCart();
}

function vaciarCarrito() {
    if (state.cart.length === 0) return;
    
    if (confirm("¿Seguro que deseas vaciar el carrito?")) {
        vaciarCarritoSinConfirmar();
        showToast("Carrito vaciado correctamente", "info");
    }
}

function vaciarCarritoSinConfirmar() {
    state.cart = [];
    saveCart();
    renderCart();
}

function saveCart() {
    localStorage.setItem('kiosco_cart', JSON.stringify(state.cart));
}

function calculateCartTotals() {
    let subtotal = 0;
    let descuento = 0; // Se pueden integrar descuentos en Fases posteriores
    
    state.cart.forEach(item => {
        subtotal += item.product.precio_venta_centavos * item.cantidad;
    });

    const total = subtotal - descuento;

    return {
        subtotal,
        descuento,
        total
    };
}

function renderCart() {
    const list = document.getElementById('cart-list');
    const emptyState = document.getElementById('cart-empty-state');
    const btnCobrar = document.getElementById('btn-cobrar');
    
    if (!list || !emptyState) return;

    if (state.cart.length === 0) {
        list.classList.add('hidden');
        emptyState.classList.remove('hidden');
        btnCobrar.disabled = true;
        
        document.getElementById('summary-subtotal').textContent = '$0,00';
        document.getElementById('summary-descuento').textContent = '-$0,00';
        document.getElementById('summary-total').textContent = '$0,00';
        return;
    }

    emptyState.classList.add('hidden');
    list.classList.remove('hidden');
    btnCobrar.disabled = false;

    list.innerHTML = '';
    state.cart.forEach(item => {
        const li = document.createElement('li');
        li.className = 'cart-item';
        
        const subtotalLinea = item.product.precio_venta_centavos * item.cantidad;

        li.innerHTML = `
            <div class="cart-item-info">
                <span class="cart-item-name" title="${item.product.nombre}">${item.product.nombre}</span>
                <div class="cart-item-meta">
                    <span class="cart-item-price">${formatMoney(item.product.precio_venta_centavos)}</span>
                    <span style="color:var(--color-text-muted);">x ${item.product.unidad_medida.toLowerCase()}</span>
                </div>
            </div>
            
            <div class="cart-item-qty">
                <button class="qty-btn btn-minus">&minus;</button>
                <input type="number" class="qty-input" value="${item.cantidad}" min="1" max="${item.product.stock_actual}">
                <button class="qty-btn btn-plus">&plus;</button>
            </div>
            
            <div class="cart-item-right">
                <span class="cart-item-subtotal">${formatMoney(subtotalLinea)}</span>
                <button class="btn-icon btn-delete" title="Quitar ítem" style="color:var(--color-text-muted);">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
            </div>
        `;

        // Lógica de botones en línea
        li.querySelector('.btn-minus').addEventListener('click', () => {
            actualizarCantidadItem(item.product.id, item.cantidad - 1);
        });

        li.querySelector('.btn-plus').addEventListener('click', () => {
            actualizarCantidadItem(item.product.id, item.cantidad + 1);
        });

        li.querySelector('.qty-input').addEventListener('change', (e) => {
            const val = parseInt(e.target.value);
            actualizarCantidadItem(item.product.id, isNaN(val) ? 1 : val);
        });

        li.querySelector('.btn-delete').addEventListener('click', () => {
            eliminarItemCarrito(item.product.id);
            showToast(`Item removido: ${item.product.nombre}`, 'info');
        });

        list.appendChild(li);
    });

    // Totales
    const totals = calculateCartTotals();
    document.getElementById('summary-subtotal').textContent = formatMoney(totals.subtotal);
    document.getElementById('summary-descuento').textContent = `-${formatMoney(totals.descuento)}`;
    document.getElementById('summary-total').textContent = formatMoney(totals.total);
}

// ==========================================================================
// MODAL DE PAGO Y COBRO (F2)
// ==========================================================================

function abrirCobroModal() {
    if (state.cart.length === 0 || !state.activeCaja) return;

    const totals = calculateCartTotals();
    
    document.getElementById('cobro-total-val').textContent = formatMoney(totals.total);
    
    // Configurar método de pago inicial (Efectivo)
    setPaymentMethod('EFECTIVO');
    
    // Vaciar el campo recibido y reinicializar vuelto
    const receivedInput = document.getElementById('cobro-recibido');
    receivedInput.value = '';
    receivedInput.focus();
    
    document.getElementById('cobro-vuelto-val').textContent = '$0,00';
    
    const vueltoBox = document.getElementById('vuelto-box');
    vueltoBox.className = 'vuelto-box status-insufficient';

    // Deshabilitar confirmación inicialmente en efectivo
    document.getElementById('btn-confirmar-cobro').disabled = true;

    showModal('modal-cobro');
}

function setPaymentMethod(method) {
    state.paymentMethod = method;
    
    const btnCash = document.getElementById('pay-method-cash');
    const btnDigital = document.getElementById('pay-method-digital');
    const cashFields = document.getElementById('cash-payment-fields');
    const digitalFields = document.getElementById('digital-payment-fields');
    const btnConfirmar = document.getElementById('btn-confirmar-cobro');
    const totals = calculateCartTotals();

    if (method === 'EFECTIVO') {
        btnCash.classList.add('active');
        btnDigital.classList.remove('active');
        cashFields.classList.remove('hidden');
        digitalFields.classList.add('hidden');
        
        // Recalcular vuelto
        recalcularVuelto();
    } else {
        btnCash.classList.remove('active');
        btnDigital.classList.add('active');
        cashFields.classList.add('hidden');
        digitalFields.classList.remove('hidden');
        
        // El pago digital asume el monto exacto
        btnConfirmar.disabled = false;
    }
}

function recalcularVuelto() {
    const receivedInput = document.getElementById('cobro-recibido');
    const receivedAmount = parseFloat(receivedInput.value) || 0;
    const totals = calculateCartTotals();
    
    const receivedCents = Math.round(receivedAmount * 100);
    const vueltoCents = receivedCents - totals.total;
    const btnConfirmar = document.getElementById('btn-confirmar-cobro');
    const vueltoVal = document.getElementById('cobro-vuelto-val');
    const vueltoBox = document.getElementById('vuelto-box');

    if (vueltoCents >= 0) {
        vueltoVal.textContent = formatMoney(vueltoCents);
        vueltoBox.className = 'vuelto-box status-sufficient';
        btnConfirmar.disabled = false;
    } else {
        vueltoVal.textContent = '- ' + formatMoney(Math.abs(vueltoCents));
        vueltoBox.className = 'vuelto-box status-insufficient';
        btnConfirmar.disabled = true;
    }
}

// Simular el cobro de la venta (Compatibilidad Fase 6)
async function procesarPago() {
    const totals = calculateCartTotals();
    const receivedInput = document.getElementById('cobro-recibido');
    const receivedAmount = state.paymentMethod === 'EFECTIVO' ? parseFloat(receivedInput.value) || 0 : totals.total / 100;
    
    const payload = {
        caja_id: state.activeCaja.id,
        metodo_pago: state.paymentMethod,
        subtotal_centavos: totals.subtotal,
        descuento_items_centavos: totals.descuento,
        descuento_venta_centavos: 0,
        total_centavos: totals.total,
        monto_recibido_centavos: Math.round(receivedAmount * 100),
        vuelto_centavos: state.paymentMethod === 'EFECTIVO' ? Math.max(0, Math.round(receivedAmount * 100) - totals.total) : 0,
        detalles: state.cart.map(item => ({
            producto_id: item.product.id,
            cantidad: item.cantidad,
            precio_unitario_centavos: item.product.precio_venta_centavos
        }))
    };

    const confirmBtn = document.getElementById('btn-confirmar-cobro');
    confirmBtn.disabled = true;

    try {
        // Intentar registrar la venta contra el endpoint (que se desarrollará en la Fase 6)
        const response = await apiRequest('/ventas', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            const data = await response.json();
            completarFlujoPago(data.vuelto_centavos);
        } else if (response.status === 404) {
            // FALLBACK SIMULATION: Si no está implementado /ventas (Fase 6), simulamos éxito local
            console.warn("POST /api/ventas no disponible (Esperado en Fase 6). Procediendo con simulación local.");
            
            // Simular descuento de stock localmente
            state.cart.forEach(item => {
                const prod = state.products.find(p => p.id === item.product.id);
                if (prod) {
                    prod.stock_actual = Math.max(0, prod.stock_actual - item.cantidad);
                }
            });

            // Forzar recarga de grillas de búsqueda
            const searchInput = document.getElementById('search-input');
            filterResults(searchInput.value);
            renderQuickAccessGrid();

            completarFlujoPago(payload.vuelto_centavos, true);
        } else {
            const err = await response.json();
            throw new Error(err.error?.message || "Error al procesar el cobro");
        }
    } catch (e) {
        playErrorSound();
        const errorDiv = document.getElementById('cobro-error');
        errorDiv.textContent = e.message;
        errorDiv.classList.remove('hidden');
        confirmBtn.disabled = false;
    }
}

function completarFlujoPago(vueltoCents, simulated = false) {
    playSuccessSound();
    
    const msg = simulated 
        ? `¡Venta Simulada con Éxito!\nVuelto a entregar: ${formatMoney(vueltoCents)}` 
        : `¡Venta Registrada con Éxito!\nVuelto a entregar: ${formatMoney(vueltoCents)}`;
        
    alert(msg);
    
    // Limpiar carrito
    vaciarCarritoSinConfirmar();
    
    // Ocultar modal
    document.getElementById('modal-cobro').classList.add('hidden');
    document.getElementById('cobro-error').classList.add('hidden');
}

// ==========================================================================
// CONTROL DE VENTANAS / MODALES
// ==========================================================================

function showModal(modalId) {
    // Si la caja está cerrada, no permitir abrir modales excepto el de apertura y login
    if (!state.activeCaja && modalId !== 'modal-apertura' && modalId !== 'modal-login') {
        showToast("Debes abrir la caja primero", "warning");
        return;
    }
    
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('hidden');
        
        // Auto-focus en el primer input del modal
        const firstInput = modal.querySelector('input');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 150);
        }
    }
}

function hideAllModals() {
    const modales = document.querySelectorAll('.modal-backdrop');
    modales.forEach(m => {
        // No ocultar modal de login si no tiene token ni modal de apertura si caja es nula
        if (m.id === 'modal-login' && !state.token) return;
        if (m.id === 'modal-apertura' && state.token && !state.activeCaja) return;
        
        m.classList.add('hidden');
    });
}

// ==========================================================================
// INICIALIZACIÓN Y BINDINGS DE EVENTOS
// ==========================================================================

async function initializePOS() {
    // 1. Obtener estado de la caja
    await checkCajaStatus();
    
    // 2. Traer productos de catálogo y cargarlos
    await fetchProducts();
    
    // 3. Traer configuraciones de accesos rápidos
    await fetchQuickAccesses();
    
    // 4. Renderizar carrito inicial guardado
    renderCart();
}

// Inicialización de Eventos DOM
document.addEventListener('DOMContentLoaded', () => {
    
    // Validar token inicial
    checkAuth();
    
    // Reloj del header
    setInterval(() => {
        const timeSpan = document.getElementById('current-time');
        if (timeSpan) {
            const d = new Date();
            timeSpan.textContent = d.toLocaleTimeString('es-AR');
        }
    }, 1000);

    // --- FORMULARIO DE LOGIN ---
    document.getElementById('form-login').addEventListener('submit', (e) => {
        e.preventDefault();
        const user = document.getElementById('login-username').value;
        const pass = document.getElementById('login-password').value;
        login(user, pass);
    });

    // --- FORMULARIO DE APERTURA ---
    document.getElementById('form-apertura').addEventListener('submit', (e) => {
        e.preventDefault();
        const monto = parseFloat(document.getElementById('apertura-monto').value) || 0;
        abrirCaja(monto);
    });

    // --- FORMULARIO DE CIERRE ---
    document.getElementById('form-cierre').addEventListener('submit', (e) => {
        e.preventDefault();
        const monto = parseFloat(document.getElementById('cierre-monto').value) || 0;
        cerrarCaja(monto);
    });

    // --- FORMULARIO DE MOVIMIENTO DE CAJA ---
    document.getElementById('form-movimiento').addEventListener('submit', (e) => {
        e.preventDefault();
        const tipo = document.querySelector('input[name="movimiento-tipo"]:checked').value;
        const monto = parseFloat(document.getElementById('movimiento-monto').value) || 0;
        const motivo = document.getElementById('movimiento-motivo').value;
        registrarMovimiento(tipo, monto, motivo);
    });

    // --- CONTROLES DE MODALES ---
    document.getElementById('btn-movimiento-caja').addEventListener('click', () => showModal('modal-movimiento'));
    document.getElementById('btn-cerrar-caja').addEventListener('click', () => showModal('modal-cierre'));
    document.getElementById('btn-logout').addEventListener('click', logout);
    document.getElementById('btn-vaciar-carrito').addEventListener('click', vaciarCarrito);
    document.getElementById('btn-cobrar').addEventListener('click', abrirCobroModal);

    // Botón cancelar del modal cobro
    document.getElementById('btn-cancelar-cobro').addEventListener('click', () => {
        document.getElementById('modal-cobro').classList.add('hidden');
        document.getElementById('cobro-error').classList.add('hidden');
    });

    // Confirmación de Pago
    document.getElementById('btn-confirmar-cobro').addEventListener('click', procesarPago);

    // Botones de cerrar modales (X)
    document.querySelectorAll('.modal-close').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modal = e.target.closest('.modal-backdrop');
            if (modal) {
                // Prevenir cierre de Login y Apertura si son requeridos
                if (modal.id === 'modal-login' && !state.token) return;
                if (modal.id === 'modal-apertura' && state.token && !state.activeCaja) return;
                
                modal.classList.add('hidden');
                
                // Limpiar posibles errores
                const errDiv = modal.querySelector('.alert-error');
                if (errDiv) errDiv.classList.add('hidden');
            }
        });
    });

    // --- FILTRADO DE BÚSQUEDA ---
    const searchInput = document.getElementById('search-input');
    
    // Implementar debounce para la búsqueda de catálogo (100ms)
    let searchTimeout;
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            filterResults(e.target.value);
        }, 100);
    });

    // Foco inicial en buscador al presionar Esc en cualquier parte
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            hideAllModals();
        }
    });

    // --- CONTROLES DE PAGO Y BILLETES RÁPIDOS ---
    document.getElementById('pay-method-cash').addEventListener('click', () => setPaymentMethod('EFECTIVO'));
    document.getElementById('pay-method-digital').addEventListener('click', () => setPaymentMethod('DIGITAL'));
    
    document.getElementById('cobro-recibido').addEventListener('input', recalcularVuelto);

    // Asignar clics a billetes rápidos
    document.querySelectorAll('.btn-billete').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const amount = parseFloat(e.target.getAttribute('data-amount'));
            const receivedInput = document.getElementById('cobro-recibido');
            receivedInput.value = amount.toFixed(2);
            recalcularVuelto();
            receivedInput.focus();
        });
    });

    // ==========================================================================
    // ATAJOS DE TECLADO GLOBALES
    // ==========================================================================
    document.addEventListener('keydown', (e) => {
        // F1: Foco en Buscador
        if (e.key === 'F1') {
            e.preventDefault();
            const input = document.getElementById('search-input');
            if (input && state.activeCaja) {
                input.focus();
                input.select();
            }
        }
        
        // F2: Ir a Cobrar
        if (e.key === 'F2') {
            e.preventDefault();
            if (state.cart.length > 0 && state.activeCaja) {
                // Asegurarse de que no haya otros modales abiertos bloqueando
                const activeModal = document.querySelector('.modal-backdrop:not(.hidden)');
                if (!activeModal || activeModal.id === 'modal-cobro') {
                    abrirCobroModal();
                }
            }
        }
        
        // F9: Vaciar Carrito
        if (e.key === 'F9') {
            e.preventDefault();
            if (state.cart.length > 0 && state.activeCaja) {
                const activeModal = document.querySelector('.modal-backdrop:not(.hidden)');
                if (!activeModal) {
                    vaciarCarrito();
                }
            }
        }
    });

    // ==========================================================================
    // ESCUCHADOR GLOBAL DE LECTOR DE CÓDIGO DE BARRAS (SCANNER LISTENER)
    // ==========================================================================
    let barcodeBuffer = '';
    let lastKeyTime = 0;

    window.addEventListener('keydown', (e) => {
        // Ignorar si el foco está en un input de modal (ej. montos, contraseñas, motivos, etc.)
        const active = document.activeElement;
        if (active && active.tagName === 'INPUT' && active.id !== 'search-input') {
            // El usuario está rellenando un formulario de modal, ignorar scanner
            return;
        }

        const currentTime = Date.now();
        
        if (e.key === 'Enter') {
            const elapsed = currentTime - lastKeyTime;
            
            // Si el buffer tiene contenido y se escribió a velocidad de escáner (<100ms en total desde la última tecla)
            if (barcodeBuffer.length >= 2 && elapsed < 80) {
                e.preventDefault();
                const code = barcodeBuffer.trim();
                barcodeBuffer = '';
                
                if (state.activeCaja) {
                    processScannedCode(code);
                } else {
                    playErrorSound();
                    showToast("Abre la caja antes de escanear productos", "warning");
                }
            } else {
                // Enter normal
                barcodeBuffer = '';
            }
        } else if (e.key.length === 1) { // Capturar caracteres legibles
            const timeDiff = currentTime - lastKeyTime;
            
            // Un humano normal no escribe a menos de 50-60 milisegundos por tecla de forma sostenida
            if (timeDiff < 60 || barcodeBuffer === '') {
                barcodeBuffer += e.key;
            } else {
                // Demasiado lento, se resetea asumiendo tipeo manual humano
                barcodeBuffer = e.key;
            }
            lastKeyTime = currentTime;
        }
    });
});
