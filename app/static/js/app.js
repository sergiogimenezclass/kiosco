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
    paymentMethod: 'EFECTIVO', // EFECTIVO o DIGITAL
    currentView: 'view-pos',
    currentCatalogSubtab: 'catalog-products',
    editingProductBarcodes: []
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
            
            // Configurar permisos de navegación en Sidebar
            setupNavigationPermissions();
            
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
            document.getElementById('header-user-role').textContent = data.user.rol;
            
            // Configurar permisos de navegación en Sidebar
            setupNavigationPermissions();
            
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
    
    // Resetear a vista POS por defecto en logout
    switchView('view-pos');
    
    // Ocultar app y mostrar login
    document.getElementById('app').classList.add('hidden');
    hideAllModals();
    showModal('modal-login');
    document.getElementById('form-login').reset();
}

// ==========================================================================
// CONTROL DE NAVEGACIÓN Y PANELES (PASO 0)
// ==========================================================================

function switchView(viewId) {
    // 1. Quitar clase active de todos los nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });

    // 2. Activar el nav item correspondiente
    const targetItem = document.querySelector(`.nav-item[data-view="${viewId}"]`);
    if (targetItem) {
        targetItem.classList.add('active');
    }

    // 3. Ocultar todos los paneles de vista
    document.querySelectorAll('.view-panel').forEach(panel => {
        panel.classList.add('hidden');
    });

    // 4. Mostrar el panel de vista activo
    const targetPanel = document.getElementById(viewId);
    if (targetPanel) {
        targetPanel.classList.remove('hidden');
        
        // Auto focus en buscador si volvemos a la vista del POS
        if (viewId === 'view-pos') {
            const searchInput = document.getElementById('search-input');
            if (searchInput && state.activeCaja) {
                searchInput.focus();
            }
        }
        
        // Inicializar datos si vamos al panel de Catálogo
        if (viewId === 'view-catalog') {
            switchCatalogSubtab(state.currentCatalogSubtab || 'catalog-products');
        }
    }

    state.currentView = viewId;
}

function setupNavigationPermissions() {
    if (!state.user) return;

    const rol = state.user.rol;
    const navCatalog = document.getElementById('nav-catalog');
    const navInventory = document.getElementById('nav-inventory');
    const navSales = document.getElementById('nav-sales');
    const navReports = document.getElementById('nav-reports');
    const navUsers = document.getElementById('nav-users');

    // Resetear visibilidad por defecto
    const items = [navCatalog, navInventory, navSales, navReports, navUsers];
    items.forEach(item => {
        if (item) item.classList.remove('hidden');
    });

    if (rol === 'CAJERO') {
        // El cajero solo puede ver Ventas (POS)
        if (navCatalog) navCatalog.classList.add('hidden');
        if (navInventory) navInventory.classList.add('hidden');
        if (navSales) navSales.classList.add('hidden');
        if (navReports) navReports.classList.add('hidden');
        if (navUsers) navUsers.classList.add('hidden');
    } else if (rol === 'SUPERVISOR') {
        // El supervisor no puede ver administración de usuarios
        if (navUsers) navUsers.classList.add('hidden');
    }
    
    // Iniciar siempre en la vista de Ventas (POS)
    switchView('view-pos');
}

// ==========================================================================
// MÓDULO DE CATÁLOGO (CRUD COMPLETO - PASO 1)
// ==========================================================================

let activeCatalogCategoryObj = null;
let activeCatalogBrandObj = null;
let activeCatalogProviderObj = null;
let activeCatalogProductObj = null;
let activeCatalogQuickObj = null;

// Cambiar de Sub-Pestaña de Catálogo
function switchCatalogSubtab(subtabId) {
    // 1. Quitar active de subtab buttons
    document.querySelectorAll('.subtab-btn').forEach(btn => {
        btn.classList.remove('active');
    });

    // 2. Activar el botón correspondiente
    const targetBtn = document.querySelector(`.subtab-btn[data-subtab="${subtabId}"]`);
    if (targetBtn) {
        targetBtn.classList.add('active');
    }

    // 3. Ocultar todos los subtab panels
    document.querySelectorAll('.subtab-panel').forEach(panel => {
        panel.classList.add('hidden');
    });

    // 4. Mostrar el panel activo
    const targetPanel = document.getElementById(subtabId);
    if (targetPanel) {
        targetPanel.classList.remove('hidden');
        
        // Cargar datos del subtab
        loadCatalogSubtabData(subtabId);
    }

    state.currentCatalogSubtab = subtabId;
}

// Disparar carga de datos según subtab
function loadCatalogSubtabData(subtabId) {
    if (subtabId === 'catalog-products') {
        loadCatalogProducts();
    } else if (subtabId === 'catalog-categories') {
        loadCatalogCategories();
    } else if (subtabId === 'catalog-brands') {
        loadCatalogBrands();
    } else if (subtabId === 'catalog-providers') {
        loadCatalogProviders();
    } else if (subtabId === 'catalog-quick') {
        loadCatalogQuick();
    }
}

// --- CATEGORÍAS ---
async function loadCatalogCategories(query = '') {
    const tbody = document.getElementById('catalog-categories-body');
    if (!tbody) return;

    try {
        const response = await apiRequest('/categorias');
        if (response.ok) {
            const data = await response.json();
            const filtered = data.filter(cat => cat.nombre.toLowerCase().includes(query.toLowerCase().trim()));
            
            if (filtered.length === 0) {
                tbody.innerHTML = '<tr><td colspan="2" class="text-muted text-center py-4">No se encontraron categorías.</td></tr>';
                return;
            }

            tbody.innerHTML = '';
            filtered.forEach(cat => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="font-weight: 500;">${cat.nombre}</td>
                    <td class="text-center">
                        <div class="action-buttons">
                            <button class="btn btn-secondary btn-sm btn-edit-cat" data-id="${cat.id}">Editar</button>
                            <button class="btn btn-danger-link btn-sm btn-delete-cat" data-id="${cat.id}">Eliminar</button>
                        </div>
                    </td>
                `;
                
                tr.querySelector('.btn-edit-cat').addEventListener('click', () => openCategoryModal(cat));
                tr.querySelector('.btn-delete-cat').addEventListener('click', () => deleteCategory(cat.id, cat.nombre));
                tbody.appendChild(tr);
            });
        }
    } catch (e) {
        showToast("Error al cargar categorías", "error");
    }
}

function openCategoryModal(cat = null) {
    activeCatalogCategoryObj = cat;
    const form = document.getElementById('form-categoria');
    const title = document.getElementById('modal-categoria-title');
    const input = document.getElementById('cat-nombre');
    const errorDiv = document.getElementById('categoria-error');
    
    errorDiv.classList.add('hidden');
    form.reset();

    if (cat) {
        title.textContent = "Editar Categoría";
        input.value = cat.nombre;
    } else {
        title.textContent = "Crear Categoría";
    }

    showModal('modal-categoria');
}

async function saveCategory(e) {
    e.preventDefault();
    const errorDiv = document.getElementById('categoria-error');
    const nombre = document.getElementById('cat-nombre').value.trim();
    
    if (!nombre) {
        errorDiv.textContent = "El nombre es obligatorio.";
        errorDiv.classList.remove('hidden');
        return;
    }

    const payload = { nombre };
    const method = activeCatalogCategoryObj ? 'PUT' : 'POST';
    const endpoint = activeCatalogCategoryObj ? `/categorias/${activeCatalogCategoryObj.id}` : '/categorias';

    try {
        const response = await apiRequest(endpoint, {
            method,
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            playSuccessSound();
            showToast(activeCatalogCategoryObj ? "Categoría actualizada correctamente" : "Categoría creada correctamente", "success");
            document.getElementById('modal-categoria').classList.add('hidden');
            loadCatalogCategories();
        } else {
            const err = await response.json();
            throw new Error(err.error?.message || "Error al guardar la categoría. Asegúrese de que el nombre sea único.");
        }
    } catch (e) {
        playErrorSound();
        errorDiv.textContent = e.message;
        errorDiv.classList.remove('hidden');
    }
}

async function deleteCategory(id, name) {
    if (!confirm(`¿Está seguro que desea eliminar la categoría "${name}"?`)) return;

    try {
        const response = await apiRequest(`/categorias/${id}`, { method: 'DELETE' });
        if (response.ok) {
            playSuccessSound();
            showToast("Categoría eliminada con éxito", "success");
            loadCatalogCategories();
        } else {
            const err = await response.json();
            throw new Error(err.error?.message || "No se puede eliminar la categoría. Probablemente tiene productos asociados.");
        }
    } catch (e) {
        playErrorSound();
        showToast(e.message, "error");
    }
}

// --- MARCAS ---
async function loadCatalogBrands(query = '') {
    const tbody = document.getElementById('catalog-brands-body');
    if (!tbody) return;

    try {
        const response = await apiRequest('/marcas');
        if (response.ok) {
            const data = await response.json();
            const filtered = data.filter(mar => mar.nombre.toLowerCase().includes(query.toLowerCase().trim()));
            
            if (filtered.length === 0) {
                tbody.innerHTML = '<tr><td colspan="2" class="text-muted text-center py-4">No se encontraron marcas.</td></tr>';
                return;
            }

            tbody.innerHTML = '';
            filtered.forEach(mar => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="font-weight: 500;">${mar.nombre}</td>
                    <td class="text-center">
                        <div class="action-buttons">
                            <button class="btn btn-secondary btn-sm btn-edit-brand" data-id="${mar.id}">Editar</button>
                            <button class="btn btn-danger-link btn-sm btn-delete-brand" data-id="${mar.id}">Eliminar</button>
                        </div>
                    </td>
                `;
                
                tr.querySelector('.btn-edit-brand').addEventListener('click', () => openBrandModal(mar));
                tr.querySelector('.btn-delete-brand').addEventListener('click', () => deleteBrand(mar.id, mar.nombre));
                tbody.appendChild(tr);
            });
        }
    } catch (e) {
        showToast("Error al cargar marcas", "error");
    }
}

function openBrandModal(mar = null) {
    activeCatalogBrandObj = mar;
    const form = document.getElementById('form-marca');
    const title = document.getElementById('modal-marca-title');
    const input = document.getElementById('mar-nombre');
    const errorDiv = document.getElementById('marca-error');
    
    errorDiv.classList.add('hidden');
    form.reset();

    if (mar) {
        title.textContent = "Editar Marca";
        input.value = mar.nombre;
    } else {
        title.textContent = "Crear Marca";
    }

    showModal('modal-marca');
}

async function saveBrand(e) {
    e.preventDefault();
    const errorDiv = document.getElementById('marca-error');
    const nombre = document.getElementById('mar-nombre').value.trim();
    
    if (!nombre) {
        errorDiv.textContent = "El nombre es obligatorio.";
        errorDiv.classList.remove('hidden');
        return;
    }

    const payload = { nombre };
    const method = activeCatalogBrandObj ? 'PUT' : 'POST';
    const endpoint = activeCatalogBrandObj ? `/marcas/${activeCatalogBrandObj.id}` : '/marcas';

    try {
        const response = await apiRequest(endpoint, {
            method,
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            playSuccessSound();
            showToast(activeCatalogBrandObj ? "Marca actualizada correctamente" : "Marca creada correctamente", "success");
            document.getElementById('modal-marca').classList.add('hidden');
            loadCatalogBrands();
        } else {
            const err = await response.json();
            throw new Error(err.error?.message || "Error al guardar la marca. Asegúrese de que el nombre sea único.");
        }
    } catch (e) {
        playErrorSound();
        errorDiv.textContent = e.message;
        errorDiv.classList.remove('hidden');
    }
}

async function deleteBrand(id, name) {
    if (!confirm(`¿Está seguro que desea eliminar la marca "${name}"?`)) return;

    try {
        const response = await apiRequest(`/marcas/${id}`, { method: 'DELETE' });
        if (response.ok) {
            playSuccessSound();
            showToast("Marca eliminada con éxito", "success");
            loadCatalogBrands();
        } else {
            const err = await response.json();
            throw new Error(err.error?.message || "No se puede eliminar la marca. Probablemente tiene productos asociados.");
        }
    } catch (e) {
        playErrorSound();
        showToast(e.message, "error");
    }
}

// --- PROVEEDORES ---
async function loadCatalogProviders(query = '') {
    const tbody = document.getElementById('catalog-providers-body');
    if (!tbody) return;

    try {
        const response = await apiRequest('/proveedores');
        if (response.ok) {
            const data = await response.json();
            const filtered = data.filter(p => 
                p.nombre.toLowerCase().includes(query.toLowerCase().trim()) ||
                (p.telefono && p.telefono.includes(query)) ||
                (p.email && p.email.toLowerCase().includes(query.toLowerCase()))
            );
            
            if (filtered.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-muted text-center py-4">No se encontraron proveedores.</td></tr>';
                return;
            }

            tbody.innerHTML = '';
            filtered.forEach(p => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="font-weight: 500;">${p.nombre}</td>
                    <td style="font-family:var(--font-mono);">${p.telefono || '-'}</td>
                    <td>${p.email || '-'}</td>
                    <td class="text-center">
                        <div class="action-buttons">
                            <button class="btn btn-secondary btn-sm btn-edit-prov" data-id="${p.id}">Editar</button>
                            <button class="btn btn-danger-link btn-sm btn-delete-prov" data-id="${p.id}">Eliminar</button>
                        </div>
                    </td>
                `;
                
                tr.querySelector('.btn-edit-prov').addEventListener('click', () => openProviderModal(p));
                tr.querySelector('.btn-delete-prov').addEventListener('click', () => deleteProvider(p.id, p.nombre));
                tbody.appendChild(tr);
            });
        }
    } catch (e) {
        showToast("Error al cargar proveedores", "error");
    }
}

function openProviderModal(prov = null) {
    activeCatalogProviderObj = prov;
    const form = document.getElementById('form-proveedor');
    const title = document.getElementById('modal-proveedor-title');
    const nameInput = document.getElementById('prov-nombre');
    const telInput = document.getElementById('prov-telefono');
    const mailInput = document.getElementById('prov-email');
    const errorDiv = document.getElementById('proveedor-error');
    
    errorDiv.classList.add('hidden');
    form.reset();

    if (prov) {
        title.textContent = "Editar Proveedor";
        nameInput.value = prov.nombre;
        telInput.value = prov.telefono || '';
        mailInput.value = prov.email || '';
    } else {
        title.textContent = "Crear Proveedor";
    }

    showModal('modal-proveedor');
}

async function saveProvider(e) {
    e.preventDefault();
    const errorDiv = document.getElementById('proveedor-error');
    const nombre = document.getElementById('prov-nombre').value.trim();
    const telefono = document.getElementById('prov-telefono').value.trim() || null;
    const email = document.getElementById('prov-email').value.trim() || null;
    
    if (!nombre) {
        errorDiv.textContent = "El nombre es obligatorio.";
        errorDiv.classList.remove('hidden');
        return;
    }

    const payload = { nombre, telefono, email };
    const method = activeCatalogProviderObj ? 'PUT' : 'POST';
    const endpoint = activeCatalogProviderObj ? `/proveedores/${activeCatalogProviderObj.id}` : '/proveedores';

    try {
        const response = await apiRequest(endpoint, {
            method,
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            playSuccessSound();
            showToast(activeCatalogProviderObj ? "Proveedor actualizado correctamente" : "Proveedor creado correctamente", "success");
            document.getElementById('modal-proveedor').classList.add('hidden');
            loadCatalogProviders();
        } else {
            const err = await response.json();
            throw new Error(err.error?.message || "Error al guardar el proveedor.");
        }
    } catch (e) {
        playErrorSound();
        errorDiv.textContent = e.message;
        errorDiv.classList.remove('hidden');
    }
}

async function deleteProvider(id, name) {
    if (!confirm(`¿Está seguro que desea eliminar el proveedor "${name}"?`)) return;

    try {
        const response = await apiRequest(`/proveedores/${id}`, { method: 'DELETE' });
        if (response.ok) {
            playSuccessSound();
            showToast("Proveedor eliminado con éxito", "success");
            loadCatalogProviders();
        } else {
            const err = await response.json();
            throw new Error(err.error?.message || "No se puede eliminar el proveedor. Probablemente tiene productos asociados.");
        }
    } catch (e) {
        playErrorSound();
        showToast(e.message, "error");
    }
}

// --- PRODUCTOS ---
async function loadCatalogProducts(query = '') {
    const tbody = document.getElementById('catalog-products-body');
    if (!tbody) return;

    try {
        // Obtenemos todos los productos (activos e inactivos)
        const response = await apiRequest('/productos');
        if (response.ok) {
            const data = await response.json();
            
            // Filtrar localmente
            const cleanQuery = query.toLowerCase().trim();
            const filtered = data.filter(p => 
                p.nombre.toLowerCase().includes(cleanQuery) ||
                (p.descripcion && p.descripcion.toLowerCase().includes(cleanQuery)) ||
                p.codigos_barras.some(c => c.includes(cleanQuery))
            );

            if (filtered.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" class="text-muted text-center py-4">No se encontraron productos en el catálogo.</td></tr>';
                return;
            }

            // Traer categorías y marcas para mapear nombres en la tabla
            const [catRes, marRes] = await Promise.all([
                apiRequest('/categorias'),
                apiRequest('/marcas')
            ]);
            
            let categories = [];
            let brands = [];
            if (catRes.ok) categories = await catRes.json();
            if (marRes.ok) brands = await marRes.json();

            tbody.innerHTML = '';
            filtered.forEach(p => {
                const tr = document.createElement('tr');
                
                // Mapear Nombres de FKs
                const catObj = categories.find(c => c.id === p.categoria_id);
                const catName = catObj ? catObj.nombre : '-';
                const marObj = brands.find(m => m.id === p.marca_id);
                const marName = marObj ? marObj.nombre : '-';

                // Stock label
                let stockClass = 'normal';
                if (p.stock_actual <= 0) stockClass = 'empty';
                else if (p.stock_actual <= p.stock_minimo) stockClass = 'low';

                // Activo Badge
                const statusBadge = p.activo === 1 
                    ? '<span class="badge-status active">Activo</span>' 
                    : '<span class="badge-status inactive">Inactivo</span>';

                tr.innerHTML = `
                    <td>
                        <div style="font-weight: 600;">${p.nombre}</div>
                        <div style="font-size:0.75rem; color:var(--color-text-muted); font-family:var(--font-mono);">${p.codigos_barras.join(', ') || 'Sin códigos'}</div>
                    </td>
                    <td>${catName}</td>
                    <td>${marName}</td>
                    <td class="text-right price-tag">${formatMoney(p.precio_venta_centavos)}</td>
                    <td class="text-center">
                        <span class="stock-tag ${stockClass}">${p.stock_actual} / min: ${p.stock_minimo}</span>
                    </td>
                    <td class="text-center">${statusBadge}</td>
                    <td class="text-center">
                        <div class="action-buttons">
                            <button class="btn btn-secondary btn-sm btn-edit-prod" data-id="${p.id}">Editar</button>
                            <button class="btn btn-danger-link btn-sm btn-delete-prod" data-id="${p.id}">Eliminar</button>
                        </div>
                    </td>
                `;

                tr.querySelector('.btn-edit-prod').addEventListener('click', () => openProductModal(p));
                tr.querySelector('.btn-delete-prod').addEventListener('click', () => deleteProduct(p.id, p.nombre));
                tbody.appendChild(tr);
            });
        }
    } catch (e) {
        showToast("Error al cargar productos del catálogo", "error");
    }
}

// Cargar selectores dinámicos del formulario
async function populateProductFormSelects() {
    const catSelect = document.getElementById('prod-categoria');
    const marSelect = document.getElementById('prod-marca');
    const provSelect = document.getElementById('prod-proveedor');

    // Limpiar options excepto la primera
    catSelect.innerHTML = '<option value="">Seleccione Categoría</option>';
    marSelect.innerHTML = '<option value="">Ninguna</option>';
    provSelect.innerHTML = '<option value="">Ninguno</option>';

    try {
        const [catsRes, marsRes, provsRes] = await Promise.all([
            apiRequest('/categorias'),
            apiRequest('/marcas'),
            apiRequest('/proveedores')
        ]);

        if (catsRes.ok) {
            const cats = await catsRes.json();
            cats.forEach(c => {
                catSelect.innerHTML += `<option value="${c.id}">${c.nombre}</option>`;
            });
        }
        if (marsRes.ok) {
            const mars = await marsRes.json();
            mars.forEach(m => {
                marSelect.innerHTML += `<option value="${m.id}">${m.nombre}</option>`;
            });
        }
        if (provsRes.ok) {
            const provs = await provsRes.json();
            provs.forEach(p => {
                provSelect.innerHTML += `<option value="${p.id}">${p.nombre}</option>`;
            });
        }
    } catch (e) {
        console.error("Error populating select fields in product modal:", e);
    }
}

// Control interactivo de Códigos de barra (Chips)
function renderBarcodeChips() {
    const container = document.getElementById('barcode-chips-container');
    if (!container) return;
    container.innerHTML = '';

    state.editingProductBarcodes.forEach(code => {
        const chip = document.createElement('div');
        chip.className = 'barcode-chip';
        chip.innerHTML = `
            <span>${code}</span>
            <button type="button" class="remove-chip" data-code="${code}">&times;</button>
        `;
        chip.querySelector('.remove-chip').addEventListener('click', () => removeBarcodeChip(code));
        container.appendChild(chip);
    });
}

function addBarcodeChip(code) {
    const cleanCode = code.trim();
    if (!cleanCode) return;
    
    if (state.editingProductBarcodes.includes(cleanCode)) {
        showToast("Este código de barras ya está asociado en el formulario", "warning");
        return;
    }

    state.editingProductBarcodes.push(cleanCode);
    renderBarcodeChips();
}

function removeBarcodeChip(code) {
    state.editingProductBarcodes = state.editingProductBarcodes.filter(c => c !== code);
    renderBarcodeChips();
}

async function openProductModal(prod = null) {
    activeCatalogProductObj = prod;
    const form = document.getElementById('form-producto');
    const title = document.getElementById('modal-producto-title');
    const errorDiv = document.getElementById('producto-error');
    
    errorDiv.classList.add('hidden');
    form.reset();

    // 1. Cargar selectores dinámicos
    await populateProductFormSelects();

    if (prod) {
        title.textContent = "Editar Producto";
        
        // Cargar campos básicos
        document.getElementById('prod-nombre').value = prod.nombre;
        document.getElementById('prod-unidad').value = prod.unidad_medida;
        document.getElementById('prod-descripcion').value = prod.descripcion || '';
        document.getElementById('prod-categoria').value = prod.categoria_id;
        document.getElementById('prod-marca').value = prod.marca_id || '';
        document.getElementById('prod-proveedor').value = prod.proveedor_id || '';
        
        // Precio (convertir centavos a pesos decimales)
        document.getElementById('prod-precio').value = (prod.precio_venta_centavos / 100).toFixed(2);
        
        document.getElementById('prod-stock').value = prod.stock_actual;
        document.getElementById('prod-stock-min').value = prod.stock_minimo;
        document.getElementById('prod-imagen').value = prod.imagen_url || '';
        document.getElementById('prod-activo').checked = prod.activo === 1;

        // Cargar códigos de barras
        state.editingProductBarcodes = [...prod.codigos_barras];
    } else {
        title.textContent = "Crear Producto";
        state.editingProductBarcodes = [];
    }

    renderBarcodeChips();
    showModal('modal-producto');
}

async function saveProduct(e) {
    e.preventDefault();
    const errorDiv = document.getElementById('producto-error');
    
    const nombre = document.getElementById('prod-nombre').value.trim();
    const unidad_medida = document.getElementById('prod-unidad').value;
    const descripcion = document.getElementById('prod-descripcion').value.trim() || null;
    const categoria_id = document.getElementById('prod-categoria').value;
    const marca_id = document.getElementById('prod-marca').value || null;
    const proveedor_id = document.getElementById('prod-proveedor').value || null;
    
    const precioPesos = parseFloat(document.getElementById('prod-precio').value) || 0;
    const stock_actual = parseInt(document.getElementById('prod-stock').value) || 0;
    const stock_minimo = parseInt(document.getElementById('prod-stock-min').value) || 0;
    
    const imagen_url = document.getElementById('prod-imagen').value.trim() || null;
    const activo = document.getElementById('prod-activo').checked ? 1 : 0;

    if (!nombre || !categoria_id || precioPesos <= 0) {
        errorDiv.textContent = "El nombre, categoría y precio mayor a 0 son obligatorios.";
        errorDiv.classList.remove('hidden');
        return;
    }

    // Convertir precio a centavos
    const precio_venta_centavos = Math.round(precioPesos * 100);

    const payload = {
        nombre,
        descripcion,
        categoria_id,
        marca_id,
        proveedor_id,
        precio_venta_centavos,
        stock_actual,
        stock_minimo,
        unidad_medida,
        imagen_url,
        activo,
        codigos_barras: state.editingProductBarcodes
    };

    const method = activeCatalogProductObj ? 'PUT' : 'POST';
    const endpoint = activeCatalogProductObj ? `/productos/${activeCatalogProductObj.id}` : '/productos';

    try {
        const response = await apiRequest(endpoint, {
            method,
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            playSuccessSound();
            showToast(activeCatalogProductObj ? "Producto actualizado correctamente" : "Producto creado correctamente", "success");
            document.getElementById('modal-producto').classList.add('hidden');
            
            // 1. Recargar el catálogo
            loadCatalogProducts();
            
            // 2. Refrescar listados del POS para que el cajero tenga stock y precios actualizados
            await fetchProducts();
            await fetchQuickAccesses();
        } else {
            const err = await response.json();
            throw new Error(err.error?.message || "Error al guardar el producto.");
        }
    } catch (e) {
        playErrorSound();
        errorDiv.textContent = e.message;
        errorDiv.classList.remove('hidden');
    }
}

async function deleteProduct(id, name) {
    if (!confirm(`¿Está seguro que desea eliminar el producto "${name}"?`)) return;

    try {
        const response = await apiRequest(`/productos/${id}`, { method: 'DELETE' });
        if (response.ok) {
            playSuccessSound();
            showToast("Producto eliminado con éxito", "success");
            
            // Recargar catálogo y POS
            loadCatalogProducts();
            await fetchProducts();
            await fetchQuickAccesses();
        } else {
            const err = await response.json();
            throw new Error(err.error?.message || "No se puede eliminar el producto. Cuenta con historial de ventas o inventario.");
        }
    } catch (e) {
        playErrorSound();
        showToast(e.message, "error");
    }
}

// --- ACCESOS RÁPIDOS ---
async function loadCatalogQuick(query = '') {
    const tbody = document.getElementById('catalog-quick-body');
    if (!tbody) return;

    try {
        const response = await apiRequest('/accesos-rapidos');
        if (response.ok) {
            const data = await response.json();
            
            // Traer productos para mostrar nombres reales
            const prodRes = await apiRequest('/productos');
            let products = [];
            if (prodRes.ok) products = await prodRes.json();

            // Filtrar localmente
            const cleanQuery = query.toLowerCase().trim();
            const filtered = data.filter(ar => {
                const p = products.find(prod => prod.id === ar.producto_id);
                const prodName = p ? p.nombre : '';
                return prodName.toLowerCase().includes(cleanQuery) || ar.etiqueta.toLowerCase().includes(cleanQuery);
            });

            if (filtered.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="text-muted text-center py-4">No se encontraron accesos rápidos configurados.</td></tr>';
                return;
            }

            // Ordenar por campo 'orden'
            filtered.sort((a, b) => a.orden - b.orden);

            tbody.innerHTML = '';
            filtered.forEach(ar => {
                const tr = document.createElement('tr');
                const p = products.find(prod => prod.id === ar.producto_id);
                const prodName = p ? p.nombre : 'Producto no encontrado';

                const statusBadge = ar.activo === 1 
                    ? '<span class="badge-status active">Activo</span>' 
                    : '<span class="badge-status inactive">Inactivo</span>';

                tr.innerHTML = `
                    <td style="font-weight: 500;">${prodName}</td>
                    <td style="font-family:var(--font-mono); font-weight:600; color:#38bdf8;">${ar.etiqueta}</td>
                    <td class="text-center font-bold" style="font-family:var(--font-mono);">${ar.orden}</td>
                    <td class="text-center">${statusBadge}</td>
                    <td class="text-center">
                        <div class="action-buttons">
                            <button class="btn btn-secondary btn-sm btn-edit-quick" data-id="${ar.id}">Editar</button>
                            <button class="btn btn-danger-link btn-sm btn-delete-quick" data-id="${ar.id}">Eliminar</button>
                        </div>
                    </td>
                `;

                tr.querySelector('.btn-edit-quick').addEventListener('click', () => openQuickAccessModal(ar));
                tr.querySelector('.btn-delete-quick').addEventListener('click', () => deleteQuickAccess(ar.id));
                tbody.appendChild(tr);
            });
        }
    } catch (e) {
        showToast("Error al cargar accesos rápidos", "error");
    }
}

async function populateQuickAccessFormSelects() {
    const select = document.getElementById('aq-producto');
    select.innerHTML = '<option value="">Seleccione un producto</option>';

    try {
        const response = await apiRequest('/productos?activo=1');
        if (response.ok) {
            const products = await response.json();
            products.forEach(p => {
                select.innerHTML += `<option value="${p.id}">${p.nombre}</option>`;
            });
        }
    } catch (e) {
        console.error("Error populating products in quick access modal:", e);
    }
}

async function openQuickAccessModal(ar = null) {
    activeCatalogQuickObj = ar;
    const form = document.getElementById('form-acceso-rapido');
    const title = document.getElementById('modal-acceso-rapido-title');
    const errorDiv = document.getElementById('acceso-rapido-error');

    errorDiv.classList.add('hidden');
    form.reset();

    // 1. Cargar select de productos
    await populateQuickAccessFormSelects();

    if (ar) {
        title.textContent = "Editar Acceso Rápido";
        document.getElementById('aq-producto').value = ar.producto_id;
        document.getElementById('aq-etiqueta').value = ar.etiqueta;
        document.getElementById('aq-orden').value = ar.orden;
        document.getElementById('aq-activo').checked = ar.activo === 1;
    } else {
        title.textContent = "Configurar Acceso Rápido";
        // Autopopular orden sugerido (siguiente libre)
        try {
            const res = await apiRequest('/accesos-rapidos');
            if (res.ok) {
                const list = await res.json();
                const max = list.reduce((prev, current) => (prev.orden > current.orden) ? prev : current, { orden: 0 });
                document.getElementById('aq-orden').value = max.orden + 1;
            }
        } catch (e) {
            document.getElementById('aq-orden').value = 1;
        }
    }

    showModal('modal-acceso-rapido');
}

async function saveQuickAccess(e) {
    e.preventDefault();
    const errorDiv = document.getElementById('acceso-rapido-error');
    
    const producto_id = document.getElementById('aq-producto').value;
    const etiqueta = document.getElementById('aq-etiqueta').value.trim();
    const orden = parseInt(document.getElementById('aq-orden').value) || 0;
    const activo = document.getElementById('aq-activo').checked ? 1 : 0;

    if (!producto_id || !etiqueta || orden <= 0) {
        errorDiv.textContent = "Todos los campos son obligatorios y el orden debe ser mayor a 0.";
        errorDiv.classList.remove('hidden');
        return;
    }

    const payload = { producto_id, etiqueta, orden, activo };
    const method = activeCatalogQuickObj ? 'PUT' : 'POST';
    const endpoint = activeCatalogQuickObj ? `/accesos-rapidos/${activeCatalogQuickObj.id}` : '/accesos-rapidos';

    try {
        const response = await apiRequest(endpoint, {
            method,
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            playSuccessSound();
            showToast(activeCatalogQuickObj ? "Acceso rápido actualizado correctamente" : "Acceso rápido configurado correctamente", "success");
            document.getElementById('modal-acceso-rapido').classList.add('hidden');
            
            // Recargar catálogo y POS
            loadCatalogQuick();
            await fetchProducts();
            await fetchQuickAccesses();
        } else {
            const err = await response.json();
            throw new Error(err.error?.message || "Error al configurar el acceso rápido. Valide que el orden de posición no esté duplicado.");
        }
    } catch (e) {
        playErrorSound();
        errorDiv.textContent = e.message;
        errorDiv.classList.remove('hidden');
    }
}

async function deleteQuickAccess(id) {
    if (!confirm("¿Está seguro que desea eliminar este acceso rápido?")) return;

    try {
        const response = await apiRequest(`/accesos-rapidos/${id}`, { method: 'DELETE' });
        if (response.ok) {
            playSuccessSound();
            showToast("Acceso rápido removido con éxito", "success");
            
            // Recargar catálogo y POS
            loadCatalogQuick();
            await fetchProducts();
            await fetchQuickAccesses();
        } else {
            const err = await response.json();
            throw new Error(err.error?.message || "No se pudo eliminar el acceso rápido.");
        }
    } catch (e) {
        playErrorSound();
        showToast(e.message, "error");
    }
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

// Sincronizar el carrito local con el estado fresco del catálogo
function syncCartWithCatalog() {
    if (!state.cart || state.cart.length === 0) return;
    
    let cartChanged = false;
    state.cart = state.cart.map(item => {
        const freshProduct = state.products.find(p => p.id === item.product.id);
        if (freshProduct) {
            let updatedItem = { ...item, product: freshProduct };
            if (freshProduct.activo !== 1 || freshProduct.stock_actual <= 0) {
                cartChanged = true;
                return null;
            }
            if (item.cantidad > freshProduct.stock_actual) {
                updatedItem.cantidad = freshProduct.stock_actual;
                cartChanged = true;
                showToast(`Stock ajustado: ${freshProduct.nombre} limitado a ${freshProduct.stock_actual} unidades`, 'warning');
            }
            if (item.product.precio_venta_centavos !== freshProduct.precio_venta_centavos) {
                cartChanged = true;
            }
            return updatedItem;
        }
        cartChanged = true;
        return null;
    }).filter(item => item !== null);
    
    if (cartChanged) {
        saveCart();
    }
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

// Registrar el cobro de la venta contra el backend
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
            precio_unitario_centavos: item.product.precio_venta_centavos,
            descuento_centavos: 0
        }))
    };

    const confirmBtn = document.getElementById('btn-confirmar-cobro');
    confirmBtn.disabled = true;

    try {
        const response = await apiRequest('/ventas', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            const data = await response.json();
            
            // Actualizar catálogo de productos en memoria para refrescar stocks
            await fetchProducts();
            
            // Refrescar grillas visuales de productos
            const searchInput = document.getElementById('search-input');
            filterResults(searchInput.value);
            renderQuickAccessGrid();

            completarFlujoPago(data.vuelto_centavos);
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

function completarFlujoPago(vueltoCents) {
    playSuccessSound();
    
    const msg = `¡Venta Registrada con Éxito!\nVuelto a entregar: ${formatMoney(vueltoCents)}`;
    showToast(msg, 'success');
    
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
    
    // Sincronizar carrito local con los datos más recientes del catálogo
    syncCartWithCatalog();
    
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

    // --- ENLACES DE NAVEGACIÓN SIDEBAR ---
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            const targetBtn = e.target.closest('.nav-item');
            if (targetBtn) {
                const viewId = targetBtn.getAttribute('data-view');
                switchView(viewId);
            }
        });
    });

    // --- SUB-TABS CATÁLOGO ---
    document.querySelectorAll('.subtab-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const subtabId = e.target.closest('.subtab-btn').getAttribute('data-subtab');
            switchCatalogSubtab(subtabId);
        });
    });

    // --- ACCIONES ABRIR MODAL CATÁLOGO ---
    document.getElementById('btn-add-product').addEventListener('click', () => openProductModal());
    document.getElementById('btn-add-category').addEventListener('click', () => openCategoryModal());
    document.getElementById('btn-add-brand').addEventListener('click', () => openBrandModal());
    document.getElementById('btn-add-provider').addEventListener('click', () => openProviderModal());
    document.getElementById('btn-add-quick').addEventListener('click', () => openQuickAccessModal());

    // --- SUBMITS DE FORMULARIOS CATÁLOGO ---
    document.getElementById('form-producto').addEventListener('submit', saveProduct);
    document.getElementById('form-categoria').addEventListener('submit', saveCategory);
    document.getElementById('form-marca').addEventListener('submit', saveBrand);
    document.getElementById('form-proveedor').addEventListener('submit', saveProvider);
    document.getElementById('form-acceso-rapido').addEventListener('submit', saveQuickAccess);

    // --- AGREGAR CÓDIGO DE BARRAS EN FORM PRODUCTO ---
    document.getElementById('btn-add-barcode-chip').addEventListener('click', () => {
        const input = document.getElementById('prod-new-barcode');
        addBarcodeChip(input.value);
        input.value = '';
    });
    
    document.getElementById('prod-new-barcode').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            addBarcodeChip(e.target.value);
            e.target.value = '';
        }
    });

    // --- CANCELAR MODALES CATÁLOGO ---
    document.querySelectorAll('.modal-cancel-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modal = e.target.closest('.modal-backdrop');
            if (modal) modal.classList.add('hidden');
        });
    });

    // --- BUSCADORES DINÁMICOS CATÁLOGO ---
    let searchProductsTimeout;
    document.getElementById('catalog-search-products').addEventListener('input', (e) => {
        clearTimeout(searchProductsTimeout);
        searchProductsTimeout = setTimeout(() => {
            loadCatalogProducts(e.target.value);
        }, 150);
    });

    let searchCategoriesTimeout;
    document.getElementById('catalog-search-categories').addEventListener('input', (e) => {
        clearTimeout(searchCategoriesTimeout);
        searchCategoriesTimeout = setTimeout(() => {
            loadCatalogCategories(e.target.value);
        }, 150);
    });

    let searchBrandsTimeout;
    document.getElementById('catalog-search-brands').addEventListener('input', (e) => {
        clearTimeout(searchBrandsTimeout);
        searchBrandsTimeout = setTimeout(() => {
            loadCatalogBrands(e.target.value);
        }, 150);
    });

    let searchProvidersTimeout;
    document.getElementById('catalog-search-providers').addEventListener('input', (e) => {
        clearTimeout(searchProvidersTimeout);
        searchProvidersTimeout = setTimeout(() => {
            loadCatalogProviders(e.target.value);
        }, 150);
    });

    let searchQuickTimeout;
    document.getElementById('catalog-search-quick').addEventListener('input', (e) => {
        clearTimeout(searchQuickTimeout);
        searchQuickTimeout = setTimeout(() => {
            loadCatalogQuick(e.target.value);
        }, 150);
    });

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
