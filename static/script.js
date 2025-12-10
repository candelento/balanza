document.addEventListener('DOMContentLoaded', function() {
    // El tema se maneja más abajo con soporte de Chart.js

    // --- Toasts reutilizables (éxito/error/info) ---
    function getToastContainer() {
        let c = document.getElementById('toast-container');
        if (!c) {
            c = document.createElement('div');
            c.id = 'toast-container';
            document.body.appendChild(c);
        }
        return c;
    }
    function showToast(message, variant = 'success', timeout = 3000) {
        try {
            const container = getToastContainer();
            const el = document.createElement('div');
            el.className = `toast toast-${variant}`;
            el.textContent = message;
            container.appendChild(el);
            // Forzar transiciones CSS: añadir clase 'show' en el siguiente frame
            requestAnimationFrame(() => { try { el.classList.add('show'); } catch(_) {} });
            const remove = () => { if (el && el.parentNode) el.parentNode.removeChild(el); };
            setTimeout(() => {
                try { el.classList.remove('show'); el.classList.add('hide'); } catch(_) {}
                setTimeout(remove, 220);
            }, Math.max(1200, timeout));
            return el;
        } catch (_) {
            // Fallback silencioso
            console[variant === 'error' ? 'error' : 'log'](message);
        }
    }
    // Flechas flotantes externas para ventas
    const ventasScrollLeft = document.getElementById('ventasScrollLeft');
    const ventasScrollRight = document.getElementById('ventasScrollRight');
    const ventasTableWrapper = document.querySelector('#ventas-content .table-wrapper');
    if (ventasScrollLeft && ventasTableWrapper) {
        ventasScrollLeft.addEventListener('click', function() {
            ventasTableWrapper.scrollBy({ left: -200, behavior: 'smooth' });
        });
    }
    if (ventasScrollRight && ventasTableWrapper) {
        ventasScrollRight.addEventListener('click', function() {
            ventasTableWrapper.scrollBy({ left: 200, behavior: 'smooth' });
        });
    }
    // --- Authentication Elements ---
    const loginContainer = document.getElementById('login-container');
    const appContent = document.getElementById('app-content');
    const loginForm = document.getElementById('login-form');
    const loginError = document.getElementById('login-error');
    const logoutBtn = document.getElementById('logoutBtn');
    // Cache login submit button and its original content to restore on logout
    const loginSubmitBtn = loginForm ? loginForm.querySelector('button[type="submit"]') : null;
    const loginSubmitOriginal = loginSubmitBtn ? loginSubmitBtn.innerHTML : 'Login';

    // --- Tab Elements ---
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');

    // Compras Elements
    const addCompraBtn = document.getElementById('addCompraBtn');
    const comprasTableBody = document.getElementById('comprasTableBody');

    // Ventas Elements
    const addVentaBtn = document.getElementById('addVentaBtn');
    const ventasTableBody = document.getElementById('ventasTableBody');

    // Filter Elements
    const comprasFilterForm = document.getElementById('compras-filter-form');
    const ventasFilterForm = document.getElementById('ventas-filter-form');
    const comprasDateStart = document.getElementById('compras-date-start');
    const comprasDateEnd = document.getElementById('compras-date-end');
    const ventasDateStart = document.getElementById('ventas-date-start');
    const ventasDateEnd = document.getElementById('ventas-date-end');
    const downloadComprasPlanillaBtn = document.getElementById('downloadComprasPlanillaBtn');
    const downloadVentasPlanillaBtn = document.getElementById('downloadVentasPlanillaBtn');
    const downloadTodoPlanillaBtn = document.getElementById('downloadTodoPlanillaBtn');
    const downloadTodoPlanillaBtn2 = document.getElementById('downloadTodoPlanillaBtn2');

    // --- State ---
    let activeTab = 'compras'; // 'compras' or 'ventas' or 'dashboard'
    const autosaveTimers = new WeakMap(); // store debounce timers per row
    let isUpdating = false;
    let entriesExitsChart = null;
    let materialTypesChart = null;
    let last5DaysBalanceChart = null;
    // Estado de visibilidad del dashboard (persistente)
    const DASHBOARD_VIS_KEY = 'dashboard_visibility';
    let dashboardVisibility = { entries: true, days5: true, ranking: true, lastmoves: true };
    let currentUserRole = null; // Store the current user's role
    let productosCompra = []; // To store purchase products
    let productosVenta = []; // To store sale products
    let transportes = (window.APP_CONFIG && Array.isArray(window.APP_CONFIG.transportes)) ? window.APP_CONFIG.transportes : []; // Lista de transportes
    let autoLoginTriggered = false; // Prevent repeated automatic submits
    let lastFocusedRow = null; // Track last focused table row for global shortcuts
    const pendingExplicitSave = new WeakSet(); // Queue for explicit F8 saves per row
    // Throttle de toasts para guardados automáticos por fila
    const autosaveLastToast = new WeakMap();

    // --- Configuration ---
    const STORAGE_KEY_COMPRAS = 'comprasData';
    const STORAGE_KEY_VENTAS = 'ventasData';
    const STORAGE_KEY_TOKEN = 'accessToken'; // Key for storing JWT
    const CUTOFF_HOUR = 18; // Hour (0-23) after which data should be hidden
    
    // Dynamic configuration for deployment - pointing to remote server
    let API_BASE_URL = 'http://91.108.124.58:8001'; // Remote VPS
    let WS_URL = 'ws://91.108.124.58:8001/ws';
    
    console.log('✓ Using remote VPS server configuration');

    // --- Helper Functions ---
    function shouldShowData() {
        // Returns true if the current hour is before the cutoff hour
        return new Date().getHours() < CUTOFF_HOUR;

    }

    // --- Authentication Functions ---
    // --- CLIENT-SIDE CREDENTIALS (only these combinations accepted) ---
    const ALLOWED_CREDENTIALS = {
        'admin': 'ronan1',
        'admin2': 'ronan2',
        'admin3': 'ronan3',
        'admin4': 'ronan4'
    };

    // Small helpers to show validation state next to inputs
    function setValidationState(inputEl, state) {
        if (!inputEl) return;
        // Clean classes
        inputEl.classList.remove('is-valid', 'is-invalid');
        // Remove existing icon if any
        const existing = inputEl.parentElement && inputEl.parentElement.querySelector('.validation-icon');
        if (existing) existing.remove();

        if (state === 'valid') {
            inputEl.classList.add('is-valid');
            const span = document.createElement('span');
            span.className = 'validation-icon validation-valid';
            // Prefer FontAwesome if available, fallback to unicode
            span.innerHTML = (window.FontAwesome || window.FontAwesome !== undefined) ? '<i class="fas fa-check" aria-hidden="true"></i>' : '✓';
            inputEl.parentElement.appendChild(span);
        } else if (state === 'invalid') {
            inputEl.classList.add('is-invalid');
            const span = document.createElement('span');
            span.className = 'validation-icon validation-invalid';
            span.innerHTML = (window.FontAwesome || window.FontAwesome !== undefined) ? '<i class="fas fa-times" aria-hidden="true"></i>' : '✗';
            inputEl.parentElement.appendChild(span);
        }
    }

    function validateCredentialsRealtime() {
        const usernameEl = document.getElementById('username');
        const passwordEl = document.getElementById('password');
        if (!usernameEl || !passwordEl) return;
        const u = usernameEl.value.trim();
        const p = passwordEl.value;

        const userExists = Object.prototype.hasOwnProperty.call(ALLOWED_CREDENTIALS, u);
        const match = userExists && ALLOWED_CREDENTIALS[u] === p;

        // If both fields are filled and match -> valid
        if (u && p && match) {
            setValidationState(usernameEl, 'valid');
            setValidationState(passwordEl, 'valid');
            if (loginError) loginError.textContent = '';
            // Trigger automatic login once per correct credential entry
            if (!autoLoginTriggered && loginForm) {
                autoLoginTriggered = true;
                // small delay so UI can show the valid state before animating
                setTimeout(() => {
                    try {
                        if (typeof loginForm.requestSubmit === 'function') {
                            loginForm.requestSubmit();
                        } else {
                            // Fallback: dispatch submit event
                            loginForm.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
                        }
                    } catch (e) {
                        console.warn('Auto-login submit failed:', e);
                    }
                }, 150);
            }
            return true;
        }

        // If user started typing but not correct yet -> show invalid X
        if (u || p) {
            setValidationState(usernameEl, userExists ? 'invalid' : 'invalid');
            setValidationState(passwordEl, 'invalid');
            // allow future auto-login attempts when the user corrects fields
            autoLoginTriggered = false;
            return false;
        }

        // Neutral (no input)
        // Clean any states
        usernameEl.classList.remove('is-valid', 'is-invalid');
        passwordEl.classList.remove('is-valid', 'is-invalid');
        const icu = usernameEl.parentElement && usernameEl.parentElement.querySelector('.validation-icon'); if (icu) icu.remove();
        const icp = passwordEl.parentElement && passwordEl.parentElement.querySelector('.validation-icon'); if (icp) icp.remove();
        return false;
    }

    // Remove validation states and icons from login inputs
    function resetLoginValidation() {
        const usernameEl = document.getElementById('username');
        const passwordEl = document.getElementById('password');
        [usernameEl, passwordEl].forEach(el => {
            if (!el) return;
            el.classList.remove('is-valid', 'is-invalid');
            const icon = el.parentElement && el.parentElement.querySelector('.validation-icon');
            if (icon) icon.remove();
        });
        if (loginError) loginError.textContent = '';
    // allow auto-login again after reset
    autoLoginTriggered = false;
    }
    function saveToken(token) {
        localStorage.setItem(STORAGE_KEY_TOKEN, token);
    }

    function getToken() {
        return localStorage.getItem(STORAGE_KEY_TOKEN);
    }

    function removeToken() {
        localStorage.removeItem(STORAGE_KEY_TOKEN);
    }

    async function login(username, password) {
        loginError.textContent = ''; // Clear previous errors
        try {
            const form = new FormData();
            form.append('username', username);
            form.append('password', password);

            const response = await fetch(`${API_BASE_URL}/token`, {
                method: 'POST',
                body: form
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Login failed');
            }

            const data = await response.json();
            saveToken(data.access_token);
            // Do not initialize the app here so the caller can play the exit animation first.
            return true;

        } catch (error) {
            console.error('Login error:', error);
            loginError.textContent = `Login failed: ${error.message}`;
            return false;
        }
    }

    function logout() {
        removeToken();
        currentUserRole = null; // Clear user role

        const loginContainerEl = document.getElementById('login-container');
        const appContentEl = document.getElementById('app-content');
        const logoutBtnEl = document.getElementById('logoutBtn');

        // Smooth transition: fade out app content, then show login with fade-in
        if (appContentEl && appContentEl.style.display !== 'none') {
            appContentEl.classList.add('fade-out');
            const onAppFade = () => {
                appContentEl.removeEventListener('animationend', onAppFade);
                appContentEl.classList.remove('fade-out');
                appContentEl.style.display = 'none';

                // Show login container with fade-in
                if (loginContainerEl) {
                    // Reset form state before showing
                    try {
                        if (loginForm) loginForm.reset();
                        if (loginError) loginError.textContent = '';
                        // Also clear visual validation (ticks / crosses)
                        resetLoginValidation();
                        if (loginSubmitBtn) {
                            loginSubmitBtn.classList.remove('btn-loading');
                            loginSubmitBtn.disabled = false;
                            loginSubmitBtn.innerHTML = loginSubmitOriginal;
                        }
                    } catch (e) {
                        console.warn('Could not fully reset login form on logout:', e);
                    }

                    loginContainerEl.style.display = 'block';
                    // Ensure body has the login-page class so the background shows behind the login
                    try { document.body.classList.add('login-page'); } catch(e) { /* ignore in non-DOM env */ }
                    // ensure any previous fade classes are removed
                    loginContainerEl.classList.remove('fade-out');
                    requestAnimationFrame(() => {
                        loginContainerEl.classList.add('fade-in');
                    });
                    const onLoginFade = () => {
                        loginContainerEl.removeEventListener('animationend', onLoginFade);
                        loginContainerEl.classList.remove('fade-in');
                        // focus first input
                        const firstInput = loginContainerEl.querySelector('input');
                        if (firstInput) firstInput.focus();
                    };
                    loginContainerEl.addEventListener('animationend', onLoginFade);
                }

                if (logoutBtnEl) logoutBtnEl.style.display = 'none';
                clearTables(); // Clear tables on logout
                // Close WebSocket connection if open
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.close(1000, "Logout"); // Use code 1000 for normal closure
                }
            };
            appContentEl.addEventListener('animationend', onAppFade);
            return;
        }

        // Fallback: immediate switch
        if (loginContainerEl) loginContainerEl.style.display = 'block';
    try { document.body.classList.add('login-page'); } catch(e) { }
        // Clear validation icons/states on fallback too
        resetLoginValidation();
        if (appContentEl) appContentEl.style.display = 'none';
        if (logoutBtnEl) logoutBtnEl.style.display = 'none';
        clearTables();
        if (ws && ws.readyState === WebSocket.OPEN) ws.close(1000, "Logout");
    }

    // --- Event Listeners ---
    // Realtime validation while typing (micro-interaction)
    const usernameEl = document.getElementById('username');
    const passwordEl = document.getElementById('password');
    const togglePasswordBtn = document.getElementById('togglePassword');
    if (usernameEl) usernameEl.addEventListener('input', validateCredentialsRealtime);
    if (passwordEl) passwordEl.addEventListener('input', validateCredentialsRealtime);
    if (togglePasswordBtn && passwordEl) {
        const setPasswordVisible = (visible) => {
            passwordEl.setAttribute('type', visible ? 'text' : 'password');
            const icon = togglePasswordBtn.querySelector('i');
            if (icon) {
                icon.classList.toggle('fa-eye', !visible);
                icon.classList.toggle('fa-eye-slash', visible);
            }
            togglePasswordBtn.setAttribute('aria-pressed', String(visible));
            togglePasswordBtn.setAttribute('aria-label', visible ? 'Ocultar contraseña' : 'Mostrar contraseña');
            togglePasswordBtn.setAttribute('title', visible ? 'Ocultar contraseña' : 'Mostrar contraseña (mantener para ver)');
        };

        // Click alterna
        togglePasswordBtn.addEventListener('click', () => {
            const showing = passwordEl.getAttribute('type') === 'text';
            setPasswordVisible(!showing);
            passwordEl.focus({ preventScroll: true });
        });

        // Mantener presionado: mostrar mientras se mantiene el puntero/tecla
        const pressStart = () => setPasswordVisible(true);
        const pressEnd = () => setPasswordVisible(false);
        togglePasswordBtn.addEventListener('mousedown', pressStart);
        togglePasswordBtn.addEventListener('touchstart', pressStart, { passive: true });
        togglePasswordBtn.addEventListener('mouseup', pressEnd);
        togglePasswordBtn.addEventListener('mouseleave', pressEnd);
        togglePasswordBtn.addEventListener('touchend', pressEnd);
        togglePasswordBtn.addEventListener('touchcancel', pressEnd);
    }
    // Run once to clear any previous state
    validateCredentialsRealtime();
    loginForm.addEventListener('submit', async function(event) {
        event.preventDefault();
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;

        // Client-side enforcement: only accept the allowed username/password combinations
        const isAllowed = Object.prototype.hasOwnProperty.call(ALLOWED_CREDENTIALS, username) && ALLOWED_CREDENTIALS[username] === password;
        if (!isAllowed) {
            // Show realtime invalid feedback and block submission
            validateCredentialsRealtime();
            if (loginError) loginError.textContent = 'Usuario o contraseña inválidos.';
            return;
        }

        // Micro-interacción: animar el botón, mostrar spinner y garantizar al menos 1s de feedback
        const submitBtn = loginForm.querySelector('button[type="submit"]');
        if (submitBtn) {
            const originalContent = submitBtn.innerHTML;
            submitBtn.disabled = true;
            submitBtn.classList.add('btn-loading');
            // show spinner (FontAwesome) and keep some text to avoid layout jump
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin" aria-hidden="true"></i> Accediendo...';

            const start = Date.now();
            const success = await login(username, password);
            const elapsed = Date.now() - start;
            const minDelay = 1000; // ms
            if (elapsed < minDelay) {
                await new Promise(resolve => setTimeout(resolve, minDelay - elapsed));
            }

            if (success) {
                // Play fade-out on login container then initialize app
                const loginContainerEl = document.getElementById('login-container');
                if (loginContainerEl) {
                    loginContainerEl.classList.add('fade-out');
                    // Wait for CSS animation to end (400ms) then initialize
                    const onAnimEnd = () => {
                        loginContainerEl.removeEventListener('animationend', onAnimEnd);
                        // restore button state before switching views
                        submitBtn.classList.remove('btn-loading');
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalContent;
                        // Remove login-page class so the background disappears as we initialize the app
                        try { document.body.classList.remove('login-page'); } catch(e) { }
                        // Initialize app (shows appContent)
                        initializeApp();
                    };
                    loginContainerEl.addEventListener('animationend', onAnimEnd);
                } else {
                    // Fallback: restore button and initialize immediately
                    submitBtn.classList.remove('btn-loading');
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalContent;
                    initializeApp();
                }
                return;
            } else {
                // Login failed: restore button and show error (login() already sets loginError)
                submitBtn.classList.remove('btn-loading');
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalContent;
                return;
            }
        } else {
            // Fallback: if no button found, call login normally
            await login(username, password);
        }
    });

    logoutBtn.addEventListener('click', logout);

    // --- Backup Button Logic ---
    const backupBtn = document.getElementById('backupBtn');

    if (backupBtn) {
    backupBtn.addEventListener('click', performBackup);
    }

    async function performBackup() {
        console.log("Attempting to perform backup...");

        const token = getToken();
        if (!token) {
            showToast("Debe iniciar sesión para realizar el backup.", 'error');
            return;
        }

        // Optional: Disable button and show loading indicator
        backupBtn.disabled = true;
        const originalButtonContent = backupBtn.innerHTML;
        backupBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Realizando Backup...';


        try {
            const response = await fetch(`${API_BASE_URL}/backup`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}` // Include token
                }
            });

            if (!response.ok) {
                let errorDetail = `Error del servidor (${response.status})`;
                 try {
                     const errorData = await response.json();
                     errorDetail = errorData.detail || errorDetail;
                 } catch (e) {
                     errorDetail = response.statusText || errorDetail;
                     console.warn("Could not parse JSON error response from server.");
                 }
                throw new Error(errorDetail);
            }

            const result = await response.json();
            console.log("Backup successful:", result);
            showToast(`Backup realizado con éxito: ${result.message}`, 'success');

        } catch (error) {
            console.error("Backup failed:", error);
            showToast(`Error al realizar el backup: ${error.message}`, 'error');
        } finally {
            // Re-enable button and restore content
            backupBtn.disabled = false;
            backupBtn.innerHTML = originalButtonContent;
        }
    }


    // Updated localStorage functions
    function saveDataToLocalStorage(type, data) {
        const key = type === 'compras' ? STORAGE_KEY_COMPRAS : STORAGE_KEY_VENTAS;
        try {
            localStorage.setItem(key, JSON.stringify(data));
            console.log(`Data for ${type} saved to localStorage`);
        } catch (e) {
            console.error(`Error saving ${type} data to localStorage:`, e);
        }
    }

    function loadDataFromLocalStorage(type) {
        const key = type === 'compras' ? STORAGE_KEY_COMPRAS : STORAGE_KEY_VENTAS;
        try {
            const storedData = localStorage.getItem(key);
            if (storedData) {
                console.log(`Data for ${type} loaded from localStorage`);
                return JSON.parse(storedData);
            }
        } catch (e) {
            console.error(`Error loading ${type} data from localStorage:`, e);
        }
        return null; // Return null if no data or error
    }

    // Updated clearTables function (plural)
    function clearTables() {
         comprasTableBody.innerHTML = '';
         ventasTableBody.innerHTML = '';
         console.log("Tables cleared due to time cutoff.");
    }

    // --- Tab Switching Logic ---
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.dataset.tab;
            if (tabName === activeTab) return;

            activeTab = tabName;

            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');

            tabContents.forEach(content => {
                content.classList.toggle('active', content.id === `${tabName}-content`);
            });

            console.log(`Switched to tab: ${activeTab}`);
            // Re-vincular iconos de calendario por si el DOM activo cambió
            try { if (typeof wireDateIconButtons === 'function') wireDateIconButtons(); } catch(_) {}
            
            if (activeTab === 'dashboard') {
                const startDateInput = document.getElementById('dashboard-date-start');
                const endDateInput = document.getElementById('dashboard-date-end');
                // Aplicar visibilidad y cablear toggles al entrar al dashboard
                loadDashboardVisibility();
                applyDashboardVisibility();
                wireDashboardToggles();
                updateDashboard(startDateInput.value, endDateInput.value);
            }
        });
    });

    // --- INICIO: HTML para el botón de Imprimir (Original) ---
    // No longer using a global printButtonHTML, it will be part of the row template.
    // --- FIN: HTML para el botón de Imprimir (Original) ---

    // --- Add New Row Logic (Combined for Compras and Ventas) ---
    function addNewRow(type) {
        const tableBody = type === 'compras' ? comprasTableBody : ventasTableBody;
    const thirdColumnName = type === 'compras' ? 'proveedor' : 'cliente'; // Dynamic column name
        const thirdColumnLabel = type === 'compras' ? 'Proveedor' : 'Cliente'; // Dynamic label for input
        const productList = type === 'compras' ? productosCompra : productosVenta;
        const datalistId = `datalist-${type}-${Date.now()}`; // Unique ID for the datalist

        const row = document.createElement('tr');
        row.dataset.isNew = 'true';
        row.dataset.type = type; // Store the type in the row

        // Create product datalist for combobox effect
        const productOptions = productList.map(p => `<option value="${p}"></option>`).join('');
        const productComboboxHTML = `
            <input class="table-input" name="mercaderia" list="${datalistId}" placeholder="Seleccionar o escribir..." autocomplete="off">
            <datalist id="${datalistId}">
                ${productOptions}
            </datalist>
        `;
        // Transporte combobox (solo ventas)
        const datalistTransId = `datalist-transporte-${type}-${Date.now()}`;
        const transportOptions = transportes.map(t => `<option value="${t}"></option>`).join('');
        const transporteComboboxHTML = `
            <input class="table-input" name="transporte" list="${datalistTransId}" placeholder="Seleccionar o escribir..." autocomplete="off">
            <datalist id="${datalistTransId}">
                ${transportOptions}
            </datalist>
        `;

        row.innerHTML = `            <td class="read-only no-editable" tabindex="-1">Nuevo</td>
            <td class="read-only no-editable" tabindex="-1">-</td>
            <td>${type === 'ventas' ? `
                    <div class="incoterm-group" role="group" aria-label="Incoterm" style="margin-bottom:4px">
                        <label style="margin-right:8px"><input type="checkbox" name="incoterm_cif"> CIF</label>
                        <label><input type="checkbox" name="incoterm_fob"> FOB</label>
                    </div>
                    <input type="text" class="table-input" name="${thirdColumnName}" placeholder="${thirdColumnLabel}" required>
                ` : `
                    <input type="text" class="table-input" name="${thirdColumnName}" placeholder="${thirdColumnLabel}" required>
                `}
            </td>
            <td>${productComboboxHTML}</td>
            <td><input type="number" class="table-input numeric-input" name="bruto" placeholder="0" min="0"></td>
            <td><input type="number" class="table-input numeric-input" name="tara" placeholder="0" min="0"></td>
            <td><input type="number" class="table-input numeric-input" name="merma" placeholder="0" min="0"></td>
            <td class="read-only no-editable" tabindex="-1">-</td>
            ${type === 'compras' ? `
                <td><input type="text" class="table-input" name="chofer" placeholder="Nombre del Chofer"></td>
                <td><input type="text" class="table-input" name="patente" placeholder="Patente"></td>
                <td class="read-only no-editable" tabindex="-1">-</td>
                <td class="read-only no-editable" tabindex="-1">-</td>
            ` : `
                <td>${transporteComboboxHTML}</td>
                <td><input type="text" class="table-input" name="patente" placeholder="Patente"></td>
                <td class="read-only no-editable" tabindex="-1">-</td> <!-- Hora Entrada -->
                <td class="read-only no-editable" tabindex="-1">-</td> <!-- Hora Salida -->
            `}
        <td class="actions-cell">
                <div class="action-buttons">
            <button class="save-btn" onclick="guardarFila(this, { explicit: true })" title="Guardar">
                        <i class="fas fa-save"></i>
                    </button>
                    <button class="delete-btn" onclick="eliminarFila(this)" title="Eliminar">
                        <i class="fas fa-trash"></i>
                    </button>
                    <div class="print-action-group">
                        <button class="pdf-btn" onclick="generarPDF(this, event)" title="Imprimir Ticket">
                            <i class="fas fa-print"></i>
                            <span class="button-text">Imprimir</span>
                        </button>
                        <div class="copies-selector">
                            <label for="numCopies">Copias:</label>
                            <select class="num-copies-select" name="numCopies">
                                <option value="1">1</option>
                                <option value="2" selected>2</option>
                                <option value="3">3</option>
                            </select>
                        </div>
                    </div>
                    <button class="save-pdf-btn" onclick="guardarPDF(this, event)" title="Guardar Ticket">
                        <i class="fas fa-file-pdf"></i>
                        <span class="button-text">Guardar</span>
                    </button>
                </div>
                </td>
                ${type === 'ventas' ? `<td><input type="number" class="table-input numeric-input" name="remito" placeholder="Remito" min="0" step="1"></td>` : ''}
                <td><input type="text" class="table-input" name="observaciones" placeholder="Observaciones"></td>
            `;

    // Agregar eventos para los campos numéricos y cálculo instantáneo de neto
        row.querySelectorAll('.numeric-input').forEach(input => {
            input.addEventListener('input', function(e) {
                // Permitir solo números y punto decimal
                let value = this.value.replace(/[^\d.-]/g, '');
                // Asegurar que solo haya un punto decimal
                const parts = value.split('.');
                if (parts.length > 2) value = parts[0] + '.' + parts.slice(1).join('');
                this.value = value;
                
                // Si es bruto, tara o merma, actualizar neto instantáneamente
                const fieldName = this.getAttribute('name');
                if (fieldName === 'bruto' || fieldName === 'tara' || fieldName === 'merma') {
                    const brutoInput = row.querySelector('[name="bruto"]');
                    const taraInput = row.querySelector('[name="tara"]');
                    const mermaInput = row.querySelector('[name="merma"]');
                    const mermaCell = mermaInput ? mermaInput.closest('td') : null;
                    const netoCell = mermaCell ? mermaCell.nextElementSibling : null;
                    
                    if (netoCell && brutoInput && taraInput && mermaInput) {
                        const bruto = parseFloat(brutoInput.value) || 0;
                        const tara = parseFloat(taraInput.value) || 0;
                        const merma = parseFloat(mermaInput.value) || 0;
                        const neto = bruto - tara - merma;
                        netoCell.textContent = neto.toFixed(2);
                    }
                }
            });
        });

        tableBody.insertBefore(row, tableBody.firstChild);

        // Incoterm mutual exclusivity (ventas only)
    if (type === 'ventas') {
            const cif = row.querySelector('input[name="incoterm_cif"]');
            const fob = row.querySelector('input[name="incoterm_fob"]');
            if (cif && fob) {
                const sync = (changed) => {
                    if (changed === 'cif' && cif.checked) fob.checked = false;
                    if (changed === 'fob' && fob.checked) cif.checked = false;
                };
        const delayedSave = () => setTimeout(() => window.guardarFila(row, { silent: true, explicit: false }), 600);
        cif.addEventListener('change', () => { sync('cif'); delayedSave(); });
        fob.addEventListener('change', () => { sync('fob'); delayedSave(); });
            }
        }

        // --- NEW --- Set focus on the first input of the new row
        const firstInput = row.querySelector('input.table-input');
        if (firstInput) {
            firstInput.focus();
        }
    // Attach autosave handlers to the new row
    attachAutosaveToRow(row);
    }

    // Efecto estético: ripple + micro-bounce en los botones de nueva fila
    function wireAddButtonEffects(btn, type) {
        if (!btn) return;
        btn.addEventListener('click', (e) => {
            // Ejecutar acción principal
            addNewRow(type);
            // Animación ripple
            try {
                const rect = btn.getBoundingClientRect();
                const size = Math.max(rect.width, rect.height);
                const ripple = document.createElement('span');
                ripple.className = 'ripple';
                ripple.style.width = ripple.style.height = size + 'px';
                ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
                ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
                btn.appendChild(ripple);
                ripple.addEventListener('animationend', () => ripple.remove());
            } catch(_) { /* no-op */ }
            // micro-bounce
            btn.classList.add('bounce');
            setTimeout(() => btn.classList.remove('bounce'), 220);
        });
    }
    wireAddButtonEffects(addCompraBtn, 'compras');
    wireAddButtonEffects(addVentaBtn, 'ventas');

    // --- WebSocket Handling ---
    let ws;
    function connectWebSocket() {
        ws = new WebSocket(WS_URL);

        ws.onopen = function() {
            console.log("WebSocket connection established.");
            // Optional: Request initial data upon connection if needed
            // ws.send(JSON.stringify({ action: 'getInitialData' }));
        };

        ws.onmessage = function(event) {
            // If user is typing in any input, don't refresh the table from WebSocket
            if (document.activeElement && (document.activeElement.tagName.toLowerCase() === 'input' || document.activeElement.tagName.toLowerCase() === 'select')) {
                console.log("WebSocket update skipped: user is editing.");
                return;
            }
            try {
                const message = JSON.parse(event.data);
                console.log("Data received via WebSocket:", message);

                if (message.type && message.payload) {
                    const dataType = message.type === 'compra' ? 'compras' : (message.type === 'venta' ? 'ventas' : null);

                    if (dataType) {
                        // Save the fresh data to local storage
                        saveDataToLocalStorage(dataType, message.payload);
                        
                        // Re-apply filters if the updated data matches the active tab
                        if (dataType === activeTab) {
                            const form = dataType === 'compras' ? comprasFilterForm : ventasFilterForm;
                            const searchInput = form.querySelector('input[type="text"]');
                            const dateInput = form.querySelector('input[type="date"]');
                            
                            const filters = {
                                search: searchInput.value,
                                date: dateInput.value
                            };
                            
                            // Fetch and display with current filters
                            fetchAndDisplayData(dataType, filters);
                        }
                    } else {
                         console.warn(`Received WebSocket message with unknown type: ${message.type}`, message);
                    }
                } else {
                    console.warn("Received WebSocket message without expected 'type' or 'payload'.", message);
                }
            } catch (e) {
                console.error("Error parsing WebSocket message:", e);
            }
        };

        ws.onclose = function(e) {
            console.log(`WebSocket closed (Code: ${e.code}, Reason: ${e.reason || 'N/A'}). Reconnecting...`);
            // Avoid immediate reconnection if closed cleanly or intentionally
            if (e.code !== 1000 && e.code !== 1005) {
                 setTimeout(connectWebSocket, 5000); // Wait 5 seconds before reconnecting
            } else {
                 console.log("WebSocket closed normally or without status. Not attempting automatic reconnection.");
            }
        };

        ws.onerror = function(err) {
            console.error('WebSocket error:', err);
            // onclose will likely be called after an error, triggering reconnection logic
        };
    }

    // --- Updated updateTable Function ---
    function updateTable(type, data) {
        // Always update the table when new data is received,
        // the interval will handle clearing past the cutoff time.

        if (isUpdating) return; // Avoid updates while saving

        const tableBody = type === 'compras' ? comprasTableBody : ventasTableBody;
    const thirdColumnName = type === 'compras' ? 'proveedor' : 'cliente';
        console.log(`updateTable called for type: ${type} with data:`, data);

        const editingRowsData = new Map();
        // Preserve editing state for the specific table being updated
        Array.from(tableBody.children).forEach(row => {
            const id = row.dataset.id;
            const isNewRow = row.dataset.isNew === 'true';
            // Check if an input within this row has focus, for both existing and new rows
            if ((id || isNewRow) && row.querySelector('.table-input:focus')) {
                 const rowData = {
                     [thirdColumnName]: row.querySelector(`[name="${thirdColumnName}"]`)?.value,
                     mercaderia: row.querySelector('[name="mercaderia"]')?.value,
                     bruto: row.querySelector('[name="bruto"]')?.value,
                     tara: row.querySelector('[name="tara"]')?.value,
                     merma: row.querySelector('[name="merma"]')?.value,
                     // Also preserve the isNew state and any temporary ID if it exists
                     isNew: isNewRow,
                     tempId: isNewRow ? row.dataset.tempId : undefined // Preserve temp ID for new rows
                 };
                 // Use a temporary ID or the actual ID as the key for the map
                 const mapKey = isNewRow ? row.dataset.tempId : id;
                 if (mapKey) {
                     editingRowsData.set(mapKey, rowData);
                     console.log(`Preserving editing state for ${type} row (ID: ${id}, isNew: ${isNewRow}, tempId: ${row.dataset.tempId})`);
                 } else {
                     console.warn(`Could not determine key for preserving editing state for a ${type} row.`);
                 }
            }
        });

        // Clear the specific table body
        tableBody.innerHTML = '';

        // Sort and add updated rows
        data.sort((a, b) => b.id - a.id).forEach(item => {
            const row = document.createElement('tr');
            row.dataset.id = item.id; // Set ID
            row.dataset.type = type; // Set type

            // Default values from the item
            let thirdColVal = item[thirdColumnName] || ''; // Use dynamic name
            let mercaderiaVal = item.mercaderia || '';
            let brutoVal = item.bruto ?? '';
            let taraVal = item.tara ?? '';
            let mermaVal = item.merma ?? '';

            // Restore values if the row was being edited
            if (editingRowsData.has(item.id.toString())) {
                const savedData = editingRowsData.get(item.id.toString());
                thirdColVal = savedData[thirdColumnName];
                mercaderiaVal = savedData.mercaderia;
                brutoVal = savedData.bruto;
                taraVal = savedData.tara;
                mermaVal = savedData.merma;
                console.log(`Restoring editing state for ${type} row ID: ${item.id}`);
            }

            const productList = type === 'compras' ? productosCompra : productosVenta;
            const datalistId = `datalist-${type}-${item.id}`; // Unique ID for the datalist
            const productOptions = productList.map(p => `<option value="${p}"></option>`).join('');
            const productComboboxHTML = `
                <input class="table-input" name="mercaderia" list="${datalistId}" value="${mercaderiaVal}" placeholder="Seleccionar o escribir..." autocomplete="off">
                <datalist id="${datalistId}">
                    ${productOptions}
                </datalist>
            `;
            // Transporte combobox (ventas)
            const datalistTransId = `datalist-transporte-${type}-${item.id}`; // Unique ID for transporte datalist
            const transportOptions = transportes.map(t => `<option value="${t}"></option>`).join('');
            const transporteComboboxHTML = `
                <input class="table-input" name="transporte" list="${datalistTransId}" value="${item.transporte ? item.transporte : 'N/A'}" placeholder="Seleccionar o escribir..." autocomplete="off">
                <datalist id="${datalistTransId}">
                    ${transportOptions}
                </datalist>
            `;

            // Determine incoterm flags (ventas only)
            const inc = (item.incoterm || '').toString().toUpperCase();
            const isCIF = inc === 'CIF';
            const isFOB = inc === 'FOB';

            // Generate row HTML
            row.innerHTML = `
                <td class="read-only no-editable" tabindex="-1">${item.id}</td>
                <td class="read-only no-editable" tabindex="-1">${item.fecha || '-'}</td>
                <td>${type === 'ventas' ? `
                        <div class=\"incoterm-group\" role=\"group\" aria-label=\"Incoterm\" style=\"margin-bottom:4px\"> 
                            <label style=\"margin-right:8px\"><input type=\"checkbox\" name=\"incoterm_cif\" ${isCIF ? 'checked' : ''}> CIF</label>
                            <label><input type=\"checkbox\" name=\"incoterm_fob\" ${isFOB ? 'checked' : ''}> FOB</label>
                        </div>
                        <input type=\"text\" class=\"table-input\" name=\"${thirdColumnName}\" value=\"${thirdColVal}\"> 
                    ` : `
                        <input type=\"text\" class=\"table-input\" name=\"${thirdColumnName}\" value=\"${thirdColVal}\">
                    `}
                </td>
                <td>${productComboboxHTML}</td>
                <td><input type="number" class="table-input numeric-input" name="bruto" value="${brutoVal}" step="0.01" min="0"></td>
                <td><input type="number" class="table-input numeric-input" name="tara" value="${taraVal}" step="0.01" min="0"></td>
                <td><input type="number" class="table-input numeric-input" name="merma" value="${mermaVal}" step="0.01" min="0"></td>
                <td class="read-only no-editable" tabindex="-1">${item.neto != null ? item.neto : '-'}</td>
                ${type === 'compras' ? `
                    <td><input type="text" class="table-input" name="chofer" value="${item.chofer ? item.chofer : 'N/A'}" placeholder="Nombre del Chofer"></td>
                    <td><input type="text" class="table-input" name="patente" value="${item.patente ? item.patente : 'N/A'}" placeholder="Patente"></td>
                ` : `
                    <td>${transporteComboboxHTML}</td>
                    <td><input type="text" class="table-input" name="patente" value="${item.patente ? item.patente : 'N/A'}" placeholder="Patente"></td>
                `}
                <td class="read-only no-editable" tabindex="-1">${item.hora_ingreso || '-'}</td>
                <td class="read-only no-editable" tabindex="-1">${item.hora_salida || '-'}</td>
                <td class="actions-cell">
                    <div class="action-buttons">
                        <button class="save-btn" onclick="guardarFila(this, { explicit: true })" title="Guardar">
                            <i class="fas fa-save"></i>
                        </button>
                        <button class="delete-btn" onclick="eliminarFila(this)" title="Eliminar">
                            <i class="fas fa-trash"></i>
                        </button>
                        <div class="print-action-group">
                            <button class="pdf-btn" onclick="generarPDF(this, event)" title="Imprimir Ticket">
                                <i class="fas fa-print"></i>
                                <span class="button-text">Imprimir</span>
                            </button>
                            <div class="copies-selector">
                                <label for="numCopies">Copias:</label>
                                <select class="num-copies-select" name="numCopies">
                                    <option value="1">1</option>
                                    <option value="2" selected>2</option>
                                    <option value="3">3</option>
                                </select>
                            </div>
                        </div>
                        <button class="save-pdf-btn" onclick="guardarPDF(this, event)" title="Guardar Ticket">
                            <i class="fas fa-file-pdf"></i>
                            <span class="button-text">Guardar</span>
                        </button>
                    </div>
                </td>
                ${type === 'ventas' ? `<td><input type="number" class="table-input numeric-input" name="remito" value="${(item.remito ?? '')}" placeholder="Remito" min="0" step="1"></td>` : ''}
                <td><input type="text" class="table-input" name="observaciones" value="${item.observaciones ? item.observaciones : ''}" placeholder="Observaciones"></td>
            `;

            // Agregar eventos para los campos numéricos y cálculo instantáneo de neto
            row.querySelectorAll('.numeric-input').forEach(input => {
                input.addEventListener('input', function(e) {
                    // Permitir solo números y punto decimal
                    let value = this.value.replace(/[^\d.-]/g, '');
                    // Asegurar que solo haya un punto decimal
                    const parts = value.split('.');
                    if (parts.length > 2) value = parts[0] + '.' + parts.slice(1).join('');
                    this.value = value;
                    
                    // Si es bruto, tara o merma, actualizar neto instantáneamente
                    const fieldName = this.getAttribute('name');
                    if (fieldName === 'bruto' || fieldName === 'tara' || fieldName === 'merma') {
                        const brutoInput = row.querySelector('[name="bruto"]');
                        const taraInput = row.querySelector('[name="tara"]');
                        const mermaInput = row.querySelector('[name="merma"]');
                        const mermaCell = mermaInput ? mermaInput.closest('td') : null;
                        const netoCell = mermaCell ? mermaCell.nextElementSibling : null;
                        
                        if (netoCell && brutoInput && taraInput && mermaInput) {
                            const bruto = parseFloat(brutoInput.value) || 0;
                            const tara = parseFloat(taraInput.value) || 0;
                            const merma = parseFloat(mermaInput.value) || 0;
                            const neto = bruto - tara - merma;
                            netoCell.textContent = neto.toFixed(2);
                        }
                    }
                });
            });

            tableBody.appendChild(row);

            // Wire incoterm checkboxes (ventas only)
        if (type === 'ventas') {
                const cif = row.querySelector('input[name="incoterm_cif"]');
                const fob = row.querySelector('input[name="incoterm_fob"]');
                if (cif && fob) {
                    const sync = (changed) => {
                        if (changed === 'cif' && cif.checked) fob.checked = false;
                        if (changed === 'fob' && fob.checked) cif.checked = false;
                    };
            const delayedSave = () => setTimeout(() => window.guardarFila(row, { silent: true, explicit: false }), 600);
            cif.addEventListener('change', () => { sync('cif'); delayedSave(); });
            fob.addEventListener('change', () => { sync('fob'); delayedSave(); });
                }
            }
            // Attach autosave handlers to the row
            attachAutosaveToRow(row);
        });
    }
    // Attach autosave handlers to a row's inputs (debounced)
    function attachAutosaveToRow(row) {
        if (!row) return;
        // Avoid double attaching
        if (row.__autosave_attached) return;
        row.__autosave_attached = true;

        // Track last focused row for global keyboard shortcuts
        row.addEventListener('focusin', () => { lastFocusedRow = row; });

        // Helper: calcular neto instantáneamente en el frontend
        function updateNetoInstantly() {
            const brutoInput = row.querySelector('[name="bruto"]');
            const taraInput = row.querySelector('[name="tara"]');
            const mermaInput = row.querySelector('[name="merma"]');
            
            // Buscar la celda de neto de manera más robusta (es la celda después de merma)
            const mermaCell = mermaInput ? mermaInput.closest('td') : null;
            const netoCell = mermaCell ? mermaCell.nextElementSibling : null;
            
            if (brutoInput && taraInput && mermaInput && netoCell) {
                const bruto = parseFloat(brutoInput.value) || 0;
                const tara = parseFloat(taraInput.value) || 0;
                const merma = parseFloat(mermaInput.value) || 0;
                const neto = bruto - tara - merma;
                
                // Actualizar visual instantáneamente
                netoCell.textContent = neto.toFixed(2);
                
                // Marcar que se actualizó (para debug)
                netoCell.style.fontWeight = 'bold';
                setTimeout(() => { netoCell.style.fontWeight = ''; }, 300);
            }
        }

        // Helper: programa un guardado de la fila respetando isUpdating (reintenta si está ocupado)
        function scheduleRowSave(delayMs = 0, forceSilent = false) {
            if (autosaveTimers.has(row)) {
                clearTimeout(autosaveTimers.get(row));
            }
            const timer = setTimeout(() => {
                // Si hay un guardado en curso, reintentar pronto
                if (isUpdating) {
                    scheduleRowSave(250, forceSilent);
                    return;
                }
                window.guardarFila(row, { silent: forceSilent, explicit: false });
                autosaveTimers.delete(row);
            }, delayMs);
            autosaveTimers.set(row, timer);
        }

        const inputs = Array.from(row.querySelectorAll('.table-input'));
        inputs.forEach(input => {
            const name = input.getAttribute('name');
            
            // Guardado en tiempo real mientras se escribe
            input.addEventListener('input', () => {
                // Para bruto, tara y merma: calcular neto instantáneamente y autoguardar
                if (name === 'bruto' || name === 'tara' || name === 'merma') {
                    // Calcular y mostrar neto inmediatamente (sin esperar al servidor)
                    updateNetoInstantly();
                    
                    // Limpiar flags de cambios pendientes
                    if (row.dataset) {
                        delete row.dataset.pendingPesoChanges;
                        delete row.dataset.pendingBruto;
                        delete row.dataset.pendingTara;
                    }
                    
                    // Guardar automáticamente después de 800ms de inactividad (espera a que termines de escribir)
                    scheduleRowSave(800, true); // 800ms debounce, silent=true
                    return;
                }
                // Debounce 600ms y programar guardado para otros campos
                scheduleRowSave(600);
            });
            
            // On focusout we trigger a debounced save for the whole row
            input.addEventListener('focusout', (e) => {
                // If the new focused element is still inside the same row, skip
                const related = e.relatedTarget || document.activeElement;
                if (related && row.contains(related)) return;

                // Para bruto, tara y merma: calcular neto y guardar inmediatamente al salir del campo
                if (name === 'bruto' || name === 'tara' || name === 'merma') {
                    // Calcular neto instantáneamente
                    updateNetoInstantly();
                    // Limpiar flags
                    if (row.dataset) {
                        delete row.dataset.pendingPesoChanges;
                        delete row.dataset.pendingBruto;
                        delete row.dataset.pendingTara;
                    }
                    // Guardar inmediatamente al salir del campo (200ms para evitar conflictos)
                    scheduleRowSave(200, true);
                    return;
                }

                // Debounce per-row saves using scheduler
                scheduleRowSave(500); // 500ms debounce al salir
            });

            // Teclas: Enter no guarda; F8 se maneja globalmente
            input.addEventListener('keydown', (ev) => {
                if (ev.key === 'Enter') {
                    // Evitar submit
                    ev.preventDefault();
                }
            });
        });
    }

    // Helper: obtener celdas de hora ingreso/salida considerando columnas variables
    function getHoraCells(row) {
        const isVentas = row && row.dataset && row.dataset.type === 'ventas';
        // Base (sin Remito): Ingreso = 4to desde el final, Salida = 3ro desde el final
        // Ventas (con Remito): ambos se desplazan +1
        const ingresoIdx = isVentas ? 5 : 4;
        const salidaIdx = isVentas ? 4 : 3;
        const horaInCell = row.querySelector(`td.read-only:nth-last-child(${ingresoIdx})`);
        const horaOutCell = row.querySelector(`td.read-only:nth-last-child(${salidaIdx})`);
        return { horaInCell, horaOutCell };
    }

    // Atajo global de teclado: F8 guarda la fila activa o la última con foco
    document.addEventListener('keydown', (ev) => {
        if (ev.key !== 'F8') return;
        // Evitar acciones del navegador y duplicados
        ev.preventDefault();
        ev.stopPropagation();

        // Determinar fila objetivo: la del foco actual o la última enfocada
        let target = document.activeElement;
        let row = target ? target.closest('tr') : null;
        if (!row) row = lastFocusedRow;
        // Solo permitir en las tablas de compras/ventas
        if (!row || !row.closest || !row.closest('#comprasTableBody, #ventasTableBody')) return;

        // Cancelar cualquier autosave pendiente y guardar explícitamente
        if (autosaveTimers.has(row)) {
            clearTimeout(autosaveTimers.get(row));
            autosaveTimers.delete(row);
        }
        // Actualización optimista de hora (mostrar al instante mientras se guarda)
        try {
            const now = new Date();
            const hh = String(now.getHours()).padStart(2, '0');
            const mm = String(now.getMinutes()).padStart(2, '0');
            const ss = String(now.getSeconds()).padStart(2, '0');
            const timeStr = `${hh}:${mm}:${ss}`;
            // Determinar qué hora estampar según el campo editado (bruto o tara)
            const { horaInCell, horaOutCell } = getHoraCells(row);
            const pendingBruto = row.dataset && row.dataset.pendingBruto === '1';
            const pendingTara = row.dataset && row.dataset.pendingTara === '1';
            if (pendingBruto && horaInCell && (!horaInCell.textContent || horaInCell.textContent.trim() === '-' || horaInCell.textContent.trim() === '')) {
                horaInCell.textContent = timeStr;
            } else if (pendingTara && horaOutCell && (!horaOutCell.textContent || horaOutCell.textContent.trim() === '-' || horaOutCell.textContent.trim() === '')) {
                horaOutCell.textContent = timeStr;
            } else {
                // Fallback legado: Ingreso si vacío, si no Salida
                if (horaInCell && (!horaInCell.textContent || horaInCell.textContent.trim() === '-' || horaInCell.textContent.trim() === '')) {
                    horaInCell.textContent = timeStr;
                } else if (horaOutCell && (!horaOutCell.textContent || horaOutCell.textContent.trim() === '-' || horaOutCell.textContent.trim() === '')) {
                    horaOutCell.textContent = timeStr;
                }
            }
        } catch (_) { /* noop */ }

        if (isUpdating) {
            // Si hay un guardado en curso, marcar esta fila para guardado explícito al terminar
            pendingExplicitSave.add(row);
        } else {
            window.guardarFila(row, { silent: false, explicit: true });
        }
    });

    // --- Updated Global Action Functions ---
    // Renamed eliminarPesada to eliminarFila and adapted for type
    window.eliminarFila = async function(btn) {
        const row = btn.closest('tr');
        if (!row) {
            console.error("Eliminar: No se encontró la fila.");
            return;
        }
        const id = row.dataset.id;
        const type = row.dataset.type; // Get type from the row

        if (!type) {
             console.error("Eliminar: No se pudo determinar el tipo (compra/venta) de la fila.");
             showToast("Error interno: No se pudo determinar el tipo del registro.", 'error');
             return;
        }

        const confirmationMessage = `¿Está seguro de eliminar este registro de ${type}?`;
        if (!confirm(confirmationMessage)) return;


        // If it's a new row (no ID), just remove it from the DOM
        if (!id) {
            row.remove();
            console.log(`Fila nueva (${type}) eliminada del DOM.`);
            try { showToast('Registro eliminado.', 'success'); } catch(_) {}
            return;
        }

        // If it has an ID, call the backend
        const endpoint = `${API_BASE_URL}/${type}/${id}`; // Dynamic endpoint
        console.log(`Attempting to delete ${type} with ID ${id} at endpoint: ${endpoint}`);

        try {
            const token = getToken();
            if (!token) {
                showToast("Debe iniciar sesión para eliminar registros.", 'error');
                return;
            }

            const response = await fetch(endpoint, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                 let errorDetail = `Error del servidor (${response.status})`;
                 try {
                     // Try to parse JSON error detail from backend
                     const errorData = await response.json();
                     errorDetail = errorData.detail || errorDetail;
                 } catch (e) {
                     // If response is not JSON or parsing fails, use the status text
                     errorDetail = response.statusText || errorDetail;
                     console.warn("Could not parse JSON error response from server.");
                 }
                throw new Error(errorDetail);
            }

            // Optional: Remove row immediately for faster UI feedback,
            // although WebSocket should handle it. Uncomment if needed.
            // row.remove();
            console.log(`Registro ${id} (${type}) eliminado. La tabla se actualizará vía WebSocket.`);
            try { showToast('Registro eliminado correctamente.', 'success'); } catch(_) {}

        } catch (error) {
            console.error(`Error al eliminar el registro (${type}):`, error);
            showToast(`No se pudo eliminar el registro: ${error.message}`, 'error');
        }
    };

    // Updated guardarFila function: performs POST/PUT to backend
    window.guardarFila = async function(btnOrRow, { silent = false, explicit = false } = {}) {
        if (isUpdating) return false; // Prevent concurrent saves
        isUpdating = true;

        // Accept either the save button or the row element
        let row;
        if (!btnOrRow) {
            isUpdating = false;
            return false;
        }
        if (btnOrRow instanceof HTMLElement && btnOrRow.tagName && btnOrRow.tagName.toLowerCase() === 'tr') {
            row = btnOrRow;
        } else {
            row = btnOrRow.closest ? btnOrRow.closest('tr') : null;
        }

        if (!row) {
            console.error('Guardar: no se encontró la fila asociada.');
            isUpdating = false;
            return false;
        }

        const saveBtn = row.querySelector('.save-btn');
        if (saveBtn) saveBtn.disabled = true;

        const isNew = row.dataset.isNew === 'true';
        const id = row.dataset.id; // may be undefined
        const type = row.dataset.type;
        if (!type) {
            console.error('Guardar: no se pudo determinar el tipo (compra/venta) de la fila.');
            if (!silent) showToast('Error interno: no se pudo determinar el tipo del registro.', 'error');
            if (saveBtn) saveBtn.disabled = false;
            isUpdating = false;
            return false;
        }

        const thirdColumnName = type === 'compras' ? 'proveedor' : 'cliente';
        const thirdColumnLabel = type === 'compras' ? 'Proveedor' : 'Cliente';

        try {
            // Parse numeric fields safely
            const brutoRaw = row.querySelector('[name="bruto"]')?.value;
            const taraRaw = row.querySelector('[name="tara"]')?.value;
            const mermaRaw = row.querySelector('[name="merma"]')?.value;
            const brutoValue = brutoRaw ? parseFloat(brutoRaw) : null;
            const taraValue = taraRaw ? parseFloat(taraRaw) : null;
            const mermaValue = mermaRaw ? parseFloat(mermaRaw) : null;

            if (brutoRaw && isNaN(brutoValue)) throw new Error("El valor de 'Bruto' no es un número válido.");
            if (taraRaw && isNaN(taraValue)) throw new Error("El valor de 'Tara' no es un número válido.");
            if (mermaRaw && isNaN(mermaValue)) throw new Error("El valor de 'Merma' no es un número válido.");

            const formData = {
                [thirdColumnName]: row.querySelector(`[name="${thirdColumnName}"]`)?.value || '',
                bruto: brutoValue,
                mercaderia: row.querySelector('[name="mercaderia"]')?.value || '',
                tara: taraValue,
                merma: mermaValue,
                ...(type === 'compras' && {
                    chofer: row.querySelector('[name="chofer"]')?.value || '',
                    patente: row.querySelector('[name="patente"]')?.value || ''
                }),
                ...(type === 'ventas' && {
                    transporte: row.querySelector('[name="transporte"]')?.value || '',
                    patente: row.querySelector('[name="patente"]')?.value || '',
                    incoterm: (() => {
                        const cif = row.querySelector('input[name="incoterm_cif"]');
                        const fob = row.querySelector('input[name="incoterm_fob"]');
                        if (cif && cif.checked) return 'CIF';
                        if (fob && fob.checked) return 'FOB';
                        return null;
                    })(),
                    remito: (() => {
                        const rv = row.querySelector('[name="remito"]')?.value;
                        if (!rv) return null;
                        const iv = parseInt(rv, 10);
                        return isNaN(iv) ? null : iv;
                    })()
                }),
                observaciones: row.querySelector('[name="observaciones"]')?.value || ''
            };

            // Basic validation
            if (!formData[thirdColumnName]) {
                throw new Error(`El campo '${thirdColumnLabel}' es obligatorio.`);
            }

            const token = getToken();
            if (!token) {
                if (!silent) showToast('Debe iniciar sesión para guardar cambios.', 'error');
                if (saveBtn) saveBtn.disabled = false;
                isUpdating = false;
                return false;
            }

            const endpoint = isNew ? `${API_BASE_URL}/${type}` : `${API_BASE_URL}/${type}/${id}`;
            const method = isNew ? 'POST' : 'PUT';

            const response = await fetch(endpoint, {
                method,
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify(formData)
            });

            if (!response.ok) {
                let errorDetail = `Error del servidor (${response.status})`;
                try {
                    const errorData = await response.json();
                    errorDetail = errorData.detail || errorDetail;
                } catch (e) {
                    errorDetail = response.statusText || errorDetail;
                }
                throw new Error(errorDetail);
            }

            const saved = await response.json();
            // Update row with returned data
            if (saved && saved.id) {
                row.dataset.id = saved.id;
                row.dataset.isNew = 'false';
                // Update read-only cells
                const idCell = row.querySelector('td.read-only');
                if (idCell) idCell.textContent = saved.id;
                // Update fecha, neto, horas if returned
                const fechaCell = row.querySelector('td.read-only:nth-child(2)');
                if (fechaCell && saved.fecha) fechaCell.textContent = saved.fecha;
                const netoCell = row.querySelector('td.read-only:nth-child(8)');
                if (netoCell && saved.neto != null) netoCell.textContent = saved.neto;
                // horas
                // Corrige selectores: ingreso es 4to desde el final, salida es 3ro desde el final
                const { horaInCell, horaOutCell } = getHoraCells(row);
                if (horaInCell) horaInCell.textContent = (saved && Object.prototype.hasOwnProperty.call(saved, 'hora_ingreso')) ? (saved.hora_ingreso || '-') : (horaInCell.textContent || '-');
                if (horaOutCell) horaOutCell.textContent = (saved && Object.prototype.hasOwnProperty.call(saved, 'hora_salida')) ? (saved.hora_salida || '-') : (horaOutCell.textContent || '-');

                // Optionally show a non-intrusive success state
                if (!silent) {
                    setValidationState(row.querySelector(`[name="${thirdColumnName}"]`), 'valid');
                    setTimeout(() => setValidationState(row.querySelector(`[name="${thirdColumnName}"]`), ''), 1000);
                }

                // Save locally as fallback
                try {
                    const existing = loadDataFromLocalStorage(type) || [];
                    // Replace or add
                    const index = existing.findIndex(it => it.id === saved.id);
                    if (index >= 0) existing[index] = saved; else existing.push(saved);
                    saveDataToLocalStorage(type, existing);
                } catch (e) { /* non-fatal */ }
            }

            console.log(`Registro ${isNew ? 'creado' : 'actualizado'} correctamente (${type}).`);
            // Si el guardado fue explícito (botón o F8), limpiar bandera de cambios pendientes en bruto/tara
            try {
                if (explicit && row && row.dataset) {
                    if (row.dataset.pendingPesoChanges) delete row.dataset.pendingPesoChanges;
                    if (row.dataset.pendingBruto) delete row.dataset.pendingBruto;
                    if (row.dataset.pendingTara) delete row.dataset.pendingTara;
                }
            } catch (_) { /* noop */ }
            // Si hay un guardado explícito pendiente (por F8) en esta fila, encadenarlo ahora
            try {
                if (pendingExplicitSave.has(row)) {
                    pendingExplicitSave.delete(row);
                    // Ejecutar guardado explícito encadenado
                    setTimeout(() => window.guardarFila(row, { silent: false, explicit: true }), 0);
                }
            } catch (_) { /* noop */ }
                // Carteles de éxito:
                // - Guardado explícito (botón o F8): mensaje completo
                // - Guardado automático: mensaje sutil con throttling por fila para evitar spam
                if (explicit && !silent) {
                    showToast('Guardado exitoso.', 'success');
                } else {
                    try {
                        const now = Date.now();
                        const last = autosaveLastToast.get(row) || 0;
                        if (now - last > 15000) { // una vez cada 15s por fila
                            showToast('Cambios guardados.', 'success', 2000);
                            autosaveLastToast.set(row, now);
                        }
                    } catch(_) { /* noop */ }
                }
                isUpdating = false;
                if (saveBtn) saveBtn.disabled = false;
                return true;

        } catch (error) {
            console.error(`Error al guardar (${type}):`, error);
            if (!silent) showToast(`No se pudo guardar el registro: ${error.message}`, 'error');
            isUpdating = false;
            if (saveBtn) saveBtn.disabled = false;
            return false;
        }
    };

    // ================================================================
    //               FUNCIÓN GENERAR PDF (ADAPTADA)
    // ================================================================
    window.generarPDF = async function(btn, event) {
        if (event) {
            event.preventDefault();
        }

        const row = btn.closest('tr');
        if (!row) {
            console.error('generarPDF: No se pudo encontrar la fila padre del botón.');
            showToast('Error interno: No se pudo encontrar la fila del registro.', 'error');
            return;
        }

    const id = row.dataset.id;
    const type = row.dataset.type; // Get type from the row
        const numCopiesSelect = row.querySelector('.num-copies-select');
        const numCopies = numCopiesSelect ? parseInt(numCopiesSelect.value, 10) : 1;

       if (!type) {
           console.error("generarPDF: No se pudo determinar el tipo (compra/venta) de la fila.");
           showToast("Error interno: No se pudo determinar el tipo del registro para imprimir.", 'error');
           return;
       }

        if (!id) {
            showToast(`Por favor, guarde el registro de ${type} antes de intentar imprimir.`, 'info');
            return;
        }

        btn.disabled = true;
        const originalButtonContent = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span class="button-text">Imprimiendo...</span>';

        let endpoint = `${API_BASE_URL}/${type}/${id}/imprimir`; // Dynamic endpoint
        endpoint += `?copies=${numCopies}`;
        // If the current table was filtered by date, include it so backend can load historical records
        try {
            const dateInputId = type === 'compras' ? 'compras-date' : 'ventas-date';
            const dateValISO = getISODateFromInputEl(document.getElementById(dateInputId));
            if (dateValISO) endpoint += `&date=${encodeURIComponent(dateValISO)}`;
        } catch (e) {
            console.warn('Could not append date to print endpoint:', e);
        }
        console.log(`Attempting to print ${type} with ID ${id} (Copies: ${numCopies}) at endpoint: ${endpoint}`);

        try {
            const token = getToken();
            if (!token) {
                showToast("Debe iniciar sesión para imprimir tickets.", 'error');
                return;
            }

            const response = await fetch(endpoint, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}` // Include token
                }
                // No body needed for GET print request
            });

            if (!response.ok) {
                let errorDetail = `Error del servidor (${response.status})`;
                try {
                    const errorData = await response.json();
                    errorDetail = errorData.detail || errorDetail;
                } catch (jsonError) {
                    errorDetail = response.statusText || errorDetail;
                    console.warn("La respuesta de error del servidor no es JSON válido.");
                }
                throw new Error(errorDetail);
            }

            // Check if response is PDF or JSON
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/pdf')) {
                // PDF response - open in new window for printing
                const copiesRequested = response.headers.get('X-Copies-Requested') || numCopies;
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                
                // Open PDF in new window and trigger print dialog
                const printWindow = window.open(url, '_blank');
                if (printWindow) {
                    printWindow.onload = () => {
                        printWindow.focus();
                        printWindow.print();
                    };
                    showToast(`Ventana de impresión abierta. Imprima ${copiesRequested} copia(s).`, 'success', 5000);
                } else {
                    // If popup was blocked, trigger download
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `ticket_${type}_${id}.pdf`;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    showToast(`PDF descargado. Por favor imprima ${copiesRequested} copia(s).`, 'info', 5000);
                }
                
                // Clean up the URL after a delay
                setTimeout(() => window.URL.revokeObjectURL(url), 60000);
            } else {
                // JSON response for direct printing/saving
                const result = await response.json();
                if (result.status === 'success') {
                    showToast(result.message || 'Ticket guardado en Pesadas e impreso.', 'success');
                } else {
                    // Fallback if status is not success but response was ok
                    showToast('Operación completada.', 'info');
                }
            }

        } catch (error) {
            console.error(`Error al solicitar la impresión (${type}):`, error);
            showToast(`No se pudo imprimir el ticket: ${error.message}`, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalButtonContent;
        }
    };
    // ================================================================
    //             FIN FUNCIÓN GENERAR PDF (ADAPTADA)
    // ================================================================

    // ================================================================
    //               FUNCIÓN GUARDAR PDF
    // ================================================================
    window.guardarPDF = async function(btn, event) {
        if (event) {
            event.preventDefault();
        }

        const row = btn.closest('tr');
        if (!row) {
            console.error('guardarPDF: No se pudo encontrar la fila padre del botón.');
            showToast('Error interno: No se pudo encontrar la fila del registro.', 'error');
            return;
        }

    const id = row.dataset.id;
    const type = row.dataset.type;

       if (!type) {
           console.error("guardarPDF: No se pudo determinar el tipo (compra/venta) de la fila.");
           showToast("Error interno: No se pudo determinar el tipo del registro para guardar.", 'error');
           return;
       }

        if (!id) {
            showToast(`Por favor, guarde el registro de ${type} antes de intentar guardar el PDF.`, 'info');
            return;
        }

        btn.disabled = true;
        const originalButtonContent = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> <span class="button-text">Guardando...</span>';

        let endpoint = `${API_BASE_URL}/${type}/${id}/guardar`; // Dynamic endpoint
        try {
            const dateInputId = type === 'compras' ? 'compras-date' : 'ventas-date';
            const dateValISO = getISODateFromInputEl(document.getElementById(dateInputId));
            if (dateValISO) endpoint += `?date=${encodeURIComponent(dateValISO)}`;
        } catch (e) {
            console.warn('Could not append date to save endpoint:', e);
        }
        console.log(`Attempting to save PDF for ${type} with ID ${id} at endpoint: ${endpoint}`);

        try {
            const token = getToken();
            if (!token) {
                showToast("Debe iniciar sesión para guardar tickets.", 'error');
                return;
            }

            const response = await fetch(endpoint, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (!response.ok) {
                let errorDetail = `Error del servidor (${response.status})`;
                try {
                    const errorData = await response.json();
                    errorDetail = errorData.detail || errorDetail;
                } catch (jsonError) {
                    errorDetail = response.statusText || errorDetail;
                    console.warn("La respuesta de error del servidor no es JSON válido.");
                }
                throw new Error(errorDetail);
            }

            // Handle JSON response (Saved to server)
            const result = await response.json();
            if (result.status === 'success') {
                showToast(result.message || 'Ticket guardado correctamente en el servidor.', 'success');
            } else {
                showToast('Operación completada.', 'info');
            }

        } catch (error) {
            console.error(`Error al solicitar guardar el PDF (${type}):`, error);
            showToast(`No se pudo guardar el ticket: ${error.message}`, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalButtonContent;
        }
    };

    // --- JWT Decoding Helper ---
    function parseJwt (token) {
        try {
            const base64Url = token.split('.')[1];
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
            const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
            }).join(''));

            return JSON.parse(jsonPayload);
        } catch (e) {
            console.error("Error decoding JWT:", e);
            return null;
        }
    }

    // --- Product Catalog Logic ---
    async function populateProductDropdowns() {
        const token = getToken();
        if (!token) return;

        try {
            const [comprasRes, ventasRes] = await Promise.all([
                fetch(`${API_BASE_URL}/api/productos/compras`, { headers: { 'Authorization': `Bearer ${token}` } }),
                fetch(`${API_BASE_URL}/api/productos/ventas`, { headers: { 'Authorization': `Bearer ${token}` } })
            ]);

            if (!comprasRes.ok || !ventasRes.ok) {
                throw new Error('Failed to fetch product lists');
            }

            productosCompra = await comprasRes.json();
            productosVenta = await ventasRes.json();
            
            console.log("Product lists loaded:", { productosCompra, productosVenta });

        } catch (error) {
            console.error("Error fetching product lists:", error);
            showToast("No se pudo cargar la lista de productos desde el servidor.", 'error');
        }
    }

    // --- Data Fetching and Filtering Logic ---
    async function fetchAndDisplayData(type, filters = {}) {
        const token = getToken();
        if (!token) return;

        let url = `${API_BASE_URL}/${type}`;
        const params = new URLSearchParams();
        if (filters.search) {
            params.append('search', filters.search);
        }
        if (filters.date) {
            params.append('date', filters.date);
        }
        
        const queryString = params.toString();
        if (queryString) {
            url += `?${queryString}`;
        }

        try {
            const response = await fetch(url, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!response.ok) {
                throw new Error(`Failed to fetch ${type}`);
            }
            const data = await response.json();
            updateTable(type, data);
        } catch (error) {
            console.error(`Error fetching ${type}:`, error);
            showToast(`No se pudieron cargar datos: ${error.message}`, 'error');
        }
    }

    // --- Filter Form Event Listeners ---
    // Establecer fecha actual por defecto en los campos de rango
    function setDefaultDateRange(startInput, endInput) {
        const today = new Date();
        const yyyy = today.getFullYear();
        const mm = String(today.getMonth() + 1).padStart(2, '0');
        const dd = String(today.getDate()).padStart(2, '0');
        const todayStr = `${yyyy}-${mm}-${dd}`;
        if (startInput) startInput.value = todayStr;
        if (endInput) endInput.value = todayStr;
    }
    setDefaultDateRange(comprasDateStart, comprasDateEnd);
    setDefaultDateRange(ventasDateStart, ventasDateEnd);

    // Enviar filtro con rango de fechas para compras
    if (comprasFilterForm) {
        comprasFilterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const search = document.getElementById('compras-search').value;
            const startDate = comprasDateStart.value;
            const endDate = comprasDateEnd.value;
            filtrarCompras(search, startDate, endDate);
        });
    }

    // Enviar filtro con rango de fechas para ventas
    if (ventasFilterForm) {
        ventasFilterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const search = document.getElementById('ventas-search').value;
            const startDate = ventasDateStart.value;
            const endDate = ventasDateEnd.value;
            filtrarVentas(search, startDate, endDate);
        });
    }

    // Función para filtrar compras
    function filtrarCompras(search, startDate, endDate) {
        const token = getToken && typeof getToken === 'function' ? getToken() : null;
        fetch(`${API_BASE_URL}/filter_section_dato?section=compras&search=${encodeURIComponent(search)}&start_date=${startDate}&end_date=${endDate}`, {
            headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        })
            .then(res => {
                if (!res.ok) throw new Error('No autorizado o error de red');
                return res.json();
            })
            .then(data => {
                updateTable('compras', data);
            })
            .catch(err => {
                showToast('Error al filtrar compras: ' + err.message, 'error');
            });
    }

    // Función para filtrar ventas
    function filtrarVentas(search, startDate, endDate) {
        const token = getToken && typeof getToken === 'function' ? getToken() : null;
        fetch(`${API_BASE_URL}/filter_section_dato?section=ventas&search=${encodeURIComponent(search)}&start_date=${startDate}&end_date=${endDate}`, {
            headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        })
            .then(res => {
                if (!res.ok) throw new Error('No autorizado o error de red');
                return res.json();
            })
            .then(data => {
                updateTable('ventas', data);
            })
            .catch(err => {
                showToast('Error al filtrar ventas: ' + err.message, 'error');
            });
    }

    // --- Icono clickeable para abrir selector de fecha en filtros ---
    function wireDateIconButtons() {
        try {
            document.querySelectorAll('.filter-section .date-icon-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const targetId = btn.getAttribute('data-target');
                    const input = document.getElementById(targetId);
                    if (!input) return;
                    if (window.flatpickr && input._flatpickr) {
                        input._flatpickr.open();
                    } else if (typeof input.showPicker === 'function') {
                        input.showPicker();
                    } else {
                        input.focus();
                    }
                });
            });
        } catch (_) { /* noop */ }
    }
    wireDateIconButtons();

    // Helper: obtener fecha ISO (Y-m-d) desde un input con flatpickr o dd/mm/yy
    function getISODateFromInputEl(input) {
        if (!input) return '';
        try {
            if (input._flatpickr) {
                const inst = input._flatpickr;
                const dateObj = inst.selectedDates && inst.selectedDates[0]
                    ? inst.selectedDates[0]
                    : (input.value ? inst.parseDate(input.value, 'd/m/y') : null);
                return dateObj ? inst.formatDate(dateObj, 'Y-m-d') : '';
            }
            const m = (input.value || '').match(/^(\d{2})\/(\d{2})\/(\d{2})$/);
            if (m) {
                const [_, dd, mm, yy] = m;
                const yyyy = `20${yy}`;
                return `${yyyy}-${mm}-${dd}`;
            }
        } catch(_) { /* noop */ }
        return '';
    }

    // --- Inicializar Flatpickr para inputs de fecha (solo calendario, dd/mm/yy visible) ---
    function initDatePickers() {
        if (!window.flatpickr) return;
        const opts = {
            dateFormat: 'd/m/y', // visible
            altInput: false,
            allowInput: false,
            clickOpens: true,
            locale: {
                firstDayOfWeek: 1
            },
            disableMobile: true,
            onChange: function(selectedDates, dateStr, instance) {
                // Nada extra: el valor visible es dd/mm/yy
            }
        };
        const compras = document.getElementById('compras-date');
        const ventas = document.getElementById('ventas-date');
        const today = new Date();
        if (compras) {
            const fp = flatpickr(compras, opts);
            // si está vacío, setear hoy por defecto
            if (!compras.value) fp.setDate(today, true);
            if (!compras.placeholder) compras.placeholder = 'dd/mm/yy';
        }
        if (ventas) {
            const fp2 = flatpickr(ventas, opts);
            if (!ventas.value) fp2.setDate(today, true);
            if (!ventas.placeholder) ventas.placeholder = 'dd/mm/yy';
        }
    }
    initDatePickers();


    // --- Helper to set default dates in filters ---
    function setDefaultDates() {
        try {
            const today = new Date();
            const yyyy = today.getFullYear();
            const mm = String(today.getMonth() + 1).padStart(2, '0');
            const dd = String(today.getDate()).padStart(2, '0');
            // Mostrar dd/mm/yy en los inputs visibles
            const currentDisplay = `${dd}/${mm}/${String(yyyy).slice(-2)}`;
            const currentISO = `${yyyy}-${mm}-${dd}`;

            const comprasDate = document.getElementById('compras-date');
            const ventasDate = document.getElementById('ventas-date');
            if (comprasDate && !comprasDate.value) {
                if (comprasDate._flatpickr) comprasDate._flatpickr.setDate(currentISO, true);
                comprasDate.value = currentDisplay;
            }
            if (ventasDate && !ventasDate.value) {
                if (ventasDate._flatpickr) ventasDate._flatpickr.setDate(currentISO, true);
                ventasDate.value = currentDisplay;
            }
        } catch (e) {
            console.warn('No se pudieron establecer las fechas por defecto:', e);
        }
    }

    // --- Updated Initial Load Logic ---
    async function initializeApp() {
        const token = getToken();
        if (token) {
            const payload = parseJwt(token);
            if (payload && payload.exp * 1000 > Date.now()) { // Check token expiration
                currentUserRole = payload.roles && payload.roles.length > 0 ? payload.roles[0] : null; // Assuming single role
                console.log("Logged in with token. User role:", currentUserRole);
                loginContainer.style.display = 'none';
                appContent.style.display = 'block';
                logoutBtn.style.display = 'block';

                // First, load product catalogs
                await populateProductDropdowns();

                // Load data for both types if available
                const localCompras = loadDataFromLocalStorage('compras');
                if (localCompras) {
                    console.log("Initializing Compras table with data from localStorage.");
                    updateTable('compras', localCompras);
                    // Ensure autosave handlers are attached to any rows loaded from storage
                    document.querySelectorAll('#comprasTableBody tr').forEach(r => attachAutosaveToRow(r));
                } else {
                    console.log("No valid localStorage data found for Compras, table initially empty.");
                }

                const localVentas = loadDataFromLocalStorage('ventas');
                if (localVentas) {
                    console.log("Initializing Ventas table with data from localStorage.");
                    updateTable('ventas', localVentas);
                    // Ensure autosave handlers are attached to any rows loaded from storage
                    document.querySelectorAll('#ventasTableBody tr').forEach(r => attachAutosaveToRow(r));
                } else {
                    console.log("No valid localStorage data found for Ventas, table initially empty.");
                }

                // Fetch initial data without filters
                fetchAndDisplayData('compras');
                fetchAndDisplayData('ventas');

                // Always connect WebSocket to get live updates
                connectWebSocket();

                // Update UI based on user role
                // updateUIBasedOnRole(); // TODO: Implement this function if needed

                // Set default dates for filters
                setDefaultDates();

                // Preparar dashboard si está visible por defecto
                try {
                    loadDashboardVisibility();
                    applyDashboardVisibility();
                    wireDashboardToggles();
                } catch(_) {}

            } else { // If no token or token expired
                console.log("No valid token found. Showing login form.");
                     loginContainer.style.display = 'block';
                     try { document.body.classList.add('login-page'); } catch(e) { }
                appContent.style.display = 'none';
                logoutBtn.style.display = 'none';
                clearTables(); // Clear tables if not logged in
            }
        } else { // If no token at all
             console.log("No token found. Showing login form.");
                 loginContainer.style.display = 'block';
                 try { document.body.classList.add('login-page'); } catch(e) { }
             appContent.style.display = 'none';
             logoutBtn.style.display = 'none';
             clearTables(); // Clear tables if not logged in
        }
    }

    // --- Planilla Printing Logic ---
    const printComprasBtn = document.getElementById('printComprasBtn');
    const printVentasBtn = document.getElementById('printVentasBtn'); // Get the new button
    const printTodoBtn = document.getElementById('printTodoBtn');

    async function handlePlanillaPrint(btn, endpoint) {
        if (!btn) return; // Safety check
        
        // Prevent double-clicks: if button is already disabled, return immediately
        if (btn.disabled) {
            console.log('[DEBUG] Button already disabled, ignoring click');
            return;
        }

        btn.disabled = true;
        const originalButtonContent = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generando PDF...';

        console.log(`[DEBUG] Attempting to print planilla at endpoint: ${endpoint}`);

        // Helper to restore button state
        const restoreButton = () => {
            console.log('[DEBUG] Restoring button state');
            btn.disabled = false;
            btn.innerHTML = originalButtonContent;
        };

        // Safety timeout to restore button after 10 seconds no matter what
        const safetyTimeout = setTimeout(() => {
            console.warn('[DEBUG] Safety timeout reached - forcing button restore');
            restoreButton();
        }, 10000);

        try {
            const token = getToken();
            if (!token) {
                console.log('[DEBUG] No token found');
                if (printWindow) printWindow.close();
                showToast("Debe iniciar sesión para imprimir planillas.", 'error');
                clearTimeout(safetyTimeout);
                restoreButton();
                return;
            }

            console.log('[DEBUG] Fetching PDF from server...');
            const response = await fetch(`${API_BASE_URL}${endpoint}`, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            console.log('[DEBUG] Response received, status:', response.status);

            if (!response.ok) {
                let errorDetail = `Error del servidor (${response.status})`;
                try {
                    const errorData = await response.json();
                    errorDetail = errorData.detail || errorDetail;
                } catch (jsonError) {
                    errorDetail = response.statusText || errorDetail;
                    console.warn("La respuesta de error del servidor no es JSON válido.");
                }
                if (printWindow) printWindow.close();
                clearTimeout(safetyTimeout);
                restoreButton();
                throw new Error(errorDetail);
            }

            // Check if the response is a PDF (VPS/Linux behavior)
            const contentType = response.headers.get('content-type');
            console.log('[DEBUG] Content-Type:', contentType);
            
            if (contentType && contentType.includes('application/pdf')) {
                // Server returned a PDF - display it in the opened window
                console.log('[DEBUG] PDF received, creating blob...');
                const blob = await response.blob();
                console.log('[DEBUG] Blob created, size:', blob.size);
                const url = window.URL.createObjectURL(blob);
                console.log('[DEBUG] Object URL created');
                
                // Clear safety timeout since we're handling it properly
                clearTimeout(safetyTimeout);
                
                // Restore button immediately since PDF is ready
                restoreButton();
                
                // Open PDF directly with the blob URL
                console.log('[DEBUG] Opening PDF in new window');
                const win = window.open(url, '_blank');
                
                if (win) {
                    win.onload = () => {
                        console.log('[DEBUG] PDF loaded, focusing and triggering print');
                        win.focus();
                        win.print();
                    };
                    showToast('Ventana de impresión abierta. Presione Aceptar para imprimir.', 'success');
                    
                    // Clean up the URL after a delay
                    setTimeout(() => {
                        console.log('[DEBUG] Cleaning up object URL');
                        window.URL.revokeObjectURL(url);
                    }, 30000);
                } else {
                    console.log('[DEBUG] Window was blocked by popup blocker');
                    showToast('Por favor permita ventanas emergentes para imprimir.', 'warning');
                    setTimeout(() => window.URL.revokeObjectURL(url), 30000);
                }
            } else {
                // Server returned JSON (Windows behavior - direct printing succeeded)
                console.log('[DEBUG] JSON response received');
                if (printWindow) printWindow.close();
                const result = await response.json();
                console.log('[DEBUG] Result:', result);
                clearTimeout(safetyTimeout);
                restoreButton();
                showToast(result.message || 'Planilla enviada a imprimir.', 'success');
            }

        } catch (error) {
            console.error('[DEBUG] Error:', error);
            if (printWindow && !printWindow.closed) printWindow.close();
            clearTimeout(safetyTimeout);
            restoreButton();
            showToast(`No se pudo imprimir la planilla: ${error.message}`, 'error');
        }
    }

    if (printComprasBtn) {
        printComprasBtn.addEventListener('click', () => handlePlanillaPrint(printComprasBtn, '/imprimir/compras'));
    }
    if (printVentasBtn) { // Add listener for the Ventas button
        printVentasBtn.addEventListener('click', () => handlePlanillaPrint(printVentasBtn, '/imprimir/ventas'));
    }
    if (printTodoBtn) {
        printTodoBtn.addEventListener('click', () => handlePlanillaPrint(printTodoBtn, '/imprimir/todo'));
    }

    // --- Planilla View Logic ---
    const viewComprasBtn = document.getElementById('viewComprasBtn');
    const viewVentasBtn = document.getElementById('viewVentasBtn');
    const viewTodoBtn = document.getElementById('viewTodoBtn');

    // Función para manejar la visualización de PDFs
    async function handlePlanillaView(endpoint) {
        try {
            const token = getToken();
            if (!token) {
                showToast("Debe iniciar sesión para ver planillas.", 'error');
                return;
            }

            const url = `${API_BASE_URL}/ver/${endpoint}`;
            console.log('Intentando obtener PDF desde:', url);
            
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Accept': 'application/pdf',
                    'Authorization': `Bearer ${token}` // Include token
                }
            });

            console.log('Estado de la respuesta:', response.status);
            if (!response.ok) {
                const message = `Error del servidor: ${response.status} - ${response.statusText}`;
                console.error('Error al obtener el PDF:', message);
                throw new Error(message);
            }

            const blob = await response.blob();
            console.log('PDF blob obtenido correctamente.');
            const pdfUrl = window.URL.createObjectURL(blob);
            window.open(pdfUrl, '_blank');
        } catch (error) {
            console.error('Error al obtener el PDF:', error);
            showToast(`Error al abrir el PDF: ${error.message}`, 'error');
        }
    }

    // Event listeners para visualización
    if (document.getElementById('viewComprasBtn')) {
        document.getElementById('viewComprasBtn').addEventListener('click', () => {
            handlePlanillaView('planilla-compras');
        });
    }

    if (document.getElementById('viewVentasBtn')) {
        document.getElementById('viewVentasBtn').addEventListener('click', () => {
            handlePlanillaView('planilla-ventas');
        });
    }    if (document.getElementById('viewTodoBtn')) {
        document.getElementById('viewTodoBtn').addEventListener('click', () => {
            handlePlanillaView('planilla-completa');
        });
    }

    if (document.getElementById('printTodoBtn')) {
        document.getElementById('printTodoBtn').addEventListener('click', () => {
            handlePlanillaPrint(document.getElementById('printTodoBtn'), '/imprimir/todo');
        });
    }

    // --- Planilla Save (Server) Logic for top button ---
    const downloadPlanillaBtn = document.getElementById('downloadPlanillaBtn');

    async function handlePlanillaServerSave(btn) {
        if (!btn) return; // Safety check

        btn.disabled = true;
        const originalButtonContent = btn.innerHTML;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';

        const endpoint = '/guardar/planilla-completa';
        console.log(`Attempting to save planilla on server from endpoint: ${endpoint}`);

        try {
            const token = getToken();
            if (!token) {
                showToast("Debe iniciar sesión para guardar planillas.", 'error');
                return;
            }

            const response = await fetch(`${API_BASE_URL}${endpoint}`, { // Prepend API_BASE_URL
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${token}` // Include token
                }
            });

            if (!response.ok) {
                let errorDetail = `Error del servidor (${response.status})`;
                try {
                    const errorData = await response.json();
                    errorDetail = errorData.detail || errorDetail;
                } catch (jsonError) {
                    errorDetail = response.statusText || errorDetail;
                    console.warn("La respuesta de error del servidor no es JSON válido.");
                }
                // Fallback: si el endpoint nuevo no existe aún (404),
                // usar el endpoint de descarga para provocar la generación en servidor
                if (response.status === 404) {
                    console.warn('Endpoint /guardar/planilla-completa no encontrado. Probando fallback /descargar/planilla-completa...');
                    const fallbackResp = await fetch(`${API_BASE_URL}/descargar/planilla-completa`, {
                        method: 'GET',
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    if (!fallbackResp.ok) {
                        throw new Error(errorDetail);
                    }
                    // Consumir el blob sin descargar al disco del usuario
                    await fallbackResp.blob();
                    // Continuar como éxito (mostraremos el toast abajo)
                } else {
                    throw new Error(errorDetail);
                }
            }

            let result;
            try {
                result = await response.json();
            } catch {
                // En fallback no hay JSON del endpoint de descarga; inventamos uno mínimo
                const now = new Date();
                const dd = String(now.getDate()).padStart(2, '0');
                const mm = String(now.getMonth() + 1).padStart(2, '0');
                result = { filename: `planilla-${dd}-${mm}.pdf`, path: `Planilla/planilla-${dd}-${mm}.pdf` };
            }
            console.log(`Planilla guardada:`, result);

            // Toast ligero de confirmación
            showToast(`Planilla guardada en: ${result.path}`, 'success');

        } catch (error) {
            console.error(`Error al guardar la planilla en el servidor:`, error);
            showToast(`No se pudo guardar la planilla: ${error.message}`, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalButtonContent;
        }
    }

    if (downloadPlanillaBtn) {
        downloadPlanillaBtn.addEventListener('click', () => handlePlanillaServerSave(downloadPlanillaBtn));
    }


    // --- Descargar planilla filtrada (compras/ventas) ---
    async function descargarPlanillaFiltrada(tipo) {
        const token = getToken();
        if (!token) {
            showToast('Debe iniciar sesión para descargar la planilla.', 'error');
            return;
        }
        let search = '';
        let date = '';
        if (tipo === 'compras') {
            search = document.getElementById('compras-search').value;
            date = getISODateFromInputEl(document.getElementById('compras-date'));
        } else {
            search = document.getElementById('ventas-search').value;
            date = getISODateFromInputEl(document.getElementById('ventas-date'));
        }
        const params = new URLSearchParams();
        if (search) params.append('search', search);
        if (date) params.append('date', date);
        params.append('type', tipo);
        const endpoint = `/descargar/planilla?${params.toString()}`;
        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`, {
                method: 'GET',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!response.ok) {
                let errorDetail = `Error del servidor (${response.status})`;
                try {
                    const errorData = await response.json();
                    errorDetail = errorData.detail || errorDetail;
                } catch (jsonError) {
                    errorDetail = response.statusText || errorDetail;
                }
                throw new Error(errorDetail);
            }
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = `planilla_${tipo}.pdf`;
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="(.+)"/);
                if (filenameMatch && filenameMatch[1]) filename = filenameMatch[1];
            }
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
        } catch (error) {
            showToast(`No se pudo descargar la planilla: ${error.message}`, 'error');
        }
    }

    if (downloadComprasPlanillaBtn) {
        downloadComprasPlanillaBtn.addEventListener('click', () => descargarPlanillaFiltrada('compras'));
    }
    if (downloadVentasPlanillaBtn) {
        downloadVentasPlanillaBtn.addEventListener('click', () => descargarPlanillaFiltrada('ventas'));
    }

    // --- Descargar planilla combinada (compras + ventas) ---
    async function descargarPlanillaCombinada() {
        const token = getToken();
        if (!token) {
            showToast('Debe iniciar sesión para descargar la planilla.', 'error');
            return;
        }
        // Detectar si estamos en compras o ventas
        let search = '';
        let date = '';
        if (activeTab === 'compras') {
            search = document.getElementById('compras-search').value;
            date = getISODateFromInputEl(document.getElementById('compras-date'));
        } else {
            search = document.getElementById('ventas-search').value;
            date = getISODateFromInputEl(document.getElementById('ventas-date'));
        }
        const params = new URLSearchParams();
        if (search) params.append('search', search);
        if (date) params.append('date', date);
        params.append('type', 'todo');
        const endpoint = `/descargar/planilla?${params.toString()}`;
        try {
            const response = await fetch(`${API_BASE_URL}${endpoint}`, {
                method: 'GET',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!response.ok) {
                let errorDetail = `Error del servidor (${response.status})`;
                try {
                    const errorData = await response.json();
                    errorDetail = errorData.detail || errorDetail;
                } catch (jsonError) {
                    errorDetail = response.statusText || errorDetail;
                }
                throw new Error(errorDetail);
            }
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = `planilla_combinada.pdf`;
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename="(.+)"/);
                if (filenameMatch && filenameMatch[1]) filename = filenameMatch[1];
            }
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
        } catch (error) {
            showToast(`No se pudo descargar la planilla: ${error.message}`, 'error');
        }
    }

    if (downloadTodoPlanillaBtn) {
        downloadTodoPlanillaBtn.addEventListener('click', descargarPlanillaCombinada);
    }
    if (downloadTodoPlanillaBtn2) {
        downloadTodoPlanillaBtn2.addEventListener('click', descargarPlanillaCombinada);
    }

    // --- Theme Switcher ---
    const themeSwitch = document.getElementById('checkbox');
    function applyThemeInstant(theme) {
        // Evitar flickers: desactivar transiciones por un instante
        document.documentElement.classList.add('theme-animating');
        // Aplicar clase de modo oscuro según corresponda
        if (theme === 'dark') {
            document.body.classList.add('dark-mode');
        } else {
            document.body.classList.remove('dark-mode');
        }
        // Forzar reflow para asegurar aplicación inmediata
        void document.body.offsetHeight;
        // Quitar el bloqueo de transiciones en el siguiente frame
        requestAnimationFrame(() => {
            document.documentElement.classList.remove('theme-animating');
        });
    }

    // Recolorear y actualizar gráficos sin animaciones cuando cambia el tema
    function refreshChartsForTheme() {
        // Si Chart no está disponible o aún no se cargó, salir silenciosamente
        if (typeof Chart === 'undefined') return;

    const isDark = document.body.classList.contains('dark-mode');
    // En modo oscuro, todo el texto de gráficos debe ser blanco
    const textColor = isDark ? '#ffffff' : '#000000';

        // Donut Entradas/Salidas
        if (entriesExitsChart && entriesExitsChart.options) {
            try {
                const legend = entriesExitsChart.options.plugins && entriesExitsChart.options.plugins.legend;
                if (legend && legend.labels) legend.labels.color = textColor;
            } catch (_) { /* noop */ }
            // El plugin de texto central lee body.dark-mode en cada draw
            entriesExitsChart.update();
        }

        // Barras por material
        if (materialTypesChart) {
            const opts = materialTypesChart.options || (materialTypesChart.options = {});
            opts.plugins = opts.plugins || {};
            const legend = opts.plugins.legend = opts.plugins.legend || {};
            legend.labels = legend.labels || {};
            legend.labels.color = textColor;

            opts.scales = opts.scales || {};
            ['x', 'y'].forEach(axis => {
                const ax = opts.scales[axis] = opts.scales[axis] || {};
                ax.ticks = ax.ticks || {};
                ax.ticks.color = isDark ? '#ffffff' : '#000000';
                ax.grid = ax.grid || {};
                if (axis === 'y') {
                    ax.grid.color = isDark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.08)';
                    ax.title = ax.title || { display: true, text: 'Kilos' };
                    ax.title.color = isDark ? '#ffffff' : '#000000';
                } else {
                    ax.grid.display = false;
                }
            });
            materialTypesChart.update();
        }

        // Barras últimos 5 días (sus opciones ya consultan el modo oscuro en funciones)
        if (last5DaysBalanceChart) {
            last5DaysBalanceChart.update();
        }
    }

    themeSwitch.addEventListener('change', function() {
        const targetTheme = this.checked ? 'dark' : 'light';
        // Desactivar animaciones de Chart.js temporalmente para un swap instantáneo
        let prevAnimDuration;
        try {
            if (typeof Chart !== 'undefined' && Chart.defaults && Chart.defaults.animation) {
                prevAnimDuration = Chart.defaults.animation.duration;
                Chart.defaults.animation.duration = 0;
            }
        } catch(_) { /* noop */ }

        applyThemeInstant(targetTheme);
        refreshChartsForTheme();
        // Restaurar animación en el siguiente frame
        requestAnimationFrame(() => {
            try {
                if (typeof Chart !== 'undefined' && Chart.defaults && Chart.defaults.animation) {
                    Chart.defaults.animation.duration = (prevAnimDuration ?? 400);
                }
            } catch(_) { /* noop */ }
        });

        localStorage.setItem('theme', targetTheme);
    });

    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        applyThemeInstant('dark');
        themeSwitch.checked = true;
        // Si ya existen gráficos (p.ej., sesión rehidratada), refrescar su estilo
        refreshChartsForTheme();
    }


    // --- Dashboard Logic ---
    const updateDashboardBtn = document.getElementById('update-dashboard');
    // Eliminamos el KPI separado y dibujaremos el balance dentro del donut

    updateDashboardBtn.addEventListener('click', (e) => {
        const startDate = document.getElementById('dashboard-date-start').value;
        const endDate = document.getElementById('dashboard-date-end').value;

        // Ripple verde militar clarito
        const rect = updateDashboardBtn.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const ripple = document.createElement('span');
        ripple.className = 'ripple';
        ripple.style.width = ripple.style.height = size + 'px';
        ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
        ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
        updateDashboardBtn.appendChild(ripple);
        ripple.addEventListener('animationend', () => ripple.remove());

        // animación de salto
        updateDashboardBtn.classList.add('bounce');
        setTimeout(() => updateDashboardBtn.classList.remove('bounce'), 220);

        // activar loading (spinner)
        updateDashboardBtn.classList.add('loading');
        updateDashboardBtn.disabled = true;
        updateDashboard(startDate, endDate).finally(() => {
            updateDashboardBtn.classList.remove('loading');
            updateDashboardBtn.disabled = false;
        });
    });

    // Presets de fecha: Hoy, Ayer, Últimos 7, Este mes, Mes pasado
    function formatDateISO(d) {
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        return `${yyyy}-${mm}-${dd}`;
    }
    function setPreset(preset) {
        const startEl = document.getElementById('dashboard-date-start');
        const endEl = document.getElementById('dashboard-date-end');
        const now = new Date();
        let start = new Date(now);
        let end = new Date(now);
        if (preset === 'today') {
            // start = end = hoy
        } else if (preset === 'yesterday') {
            start.setDate(start.getDate() - 1);
            end.setDate(end.getDate() - 1);
        } else if (preset === 'last7') {
            start.setDate(start.getDate() - 6); // incluye hoy
        } else if (preset === 'thisMonth') {
            start = new Date(now.getFullYear(), now.getMonth(), 1);
            end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
        } else if (preset === 'lastMonth') {
            start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
            end = new Date(now.getFullYear(), now.getMonth(), 0);
        }
        startEl.value = formatDateISO(start);
        endEl.value = formatDateISO(end);
        // activar estilo activo
        document.querySelectorAll('.preset-chip').forEach(ch => ch.classList.remove('active'));
        const active = document.querySelector(`.preset-chip[data-preset="${preset}"]`);
        if (active) active.classList.add('active');
        // refrescar dashboard
        updateDashboard(startEl.value, endEl.value);
    }
    document.querySelectorAll('.preset-chip').forEach(chip => {
        chip.addEventListener('click', () => setPreset(chip.dataset.preset));
    });

    async function updateDashboard(startDate, endDate) {
        if (!startDate || !endDate) return;

        const token = getToken();
        if (!token) return;

        try {
            const response = await fetch(`${API_BASE_URL}/api/dashboard/data?start_date=${startDate}&end_date=${endDate}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!response.ok) {
                throw new Error('Failed to fetch dashboard data');
            }

            const data = await response.json();

            // Update Charts (el donut también mostrará el balance en el centro)
            updateEntriesExitsChart(data.total_kilos_comprados, data.total_kilos_vendidos, data.balance_neto);
            updateMaterialTypesChart(data.compras_por_material);
            // Actualizar KPIs superiores
            try {
                const comprasKg = Number(data.total_kilos_comprados || 0);
                const ventasKg = Number(data.total_kilos_vendidos || 0);
                const balanceKg = Number(
                    typeof data.balance_neto === 'number' ? data.balance_neto : (comprasKg - ventasKg)
                );
                const top = Array.isArray(data.compras_por_material) && data.compras_por_material.length
                    ? data.compras_por_material.slice().sort((a,b)=>Number(b.total_kilos||0)-Number(a.total_kilos||0))[0]
                    : null;
                const topText = top ? `${top.mercaderia} (${Number(top.total_kilos||0).toLocaleString('es-AR')} kg)` : '—';
                const elCompras = document.getElementById('kpi-compras');
                const elVentas = document.getElementById('kpi-ventas');
                const elBalance = document.getElementById('kpi-balance');
                const elTop = document.getElementById('kpi-top-producto');
                if (elCompras) elCompras.textContent = comprasKg.toLocaleString('es-AR');
                if (elVentas) elVentas.textContent = ventasKg.toLocaleString('es-AR');
                if (elBalance) elBalance.textContent = balanceKg.toLocaleString('es-AR');
                if (elTop) elTop.textContent = topText;
                // animación de pulso al actualizar KPIs
                ['kpi-compras','kpi-ventas','kpi-balance','kpi-top-producto'].forEach(id => {
                    const el = document.getElementById(id);
                    if (!el) return;
                    el.classList.remove('pulse');
                    void el.offsetWidth;
                    el.classList.add('pulse');
                    setTimeout(() => el.classList.remove('pulse'), 700);
                });
            } catch(_) {}

            // Cargar y actualizar el gráfico de últimos 5 días (filtro aplica solo a estas cards)
            await updateLast5DaysBalance(endDate);

            // Últimos movimientos (lista compacta)
            await updateLastMoves(startDate, endDate);

        } catch (error) {
            console.error('Error updating dashboard:', error);
            showToast('No se pudieron cargar los datos del dashboard.', 'error');
        }
    }

    async function updateLastMoves(startDate, endDate) {
        const token = getToken();
        if (!token) return;
        try {
            const url = `${API_BASE_URL}/api/dashboard/last-moves?start_date=${encodeURIComponent(startDate)}&end_date=${encodeURIComponent(endDate)}&limit=6`;
            const resp = await fetch(url, { headers: { 'Authorization': `Bearer ${token}` } });
            if (!resp.ok) throw new Error('No se pudieron cargar los últimos movimientos');
            const items = await resp.json();
            const ul = document.getElementById('last-moves-list');
            if (!ul) return;
            ul.innerHTML = '';
            (items || []).slice(0, 6).forEach(it => {
                const li = document.createElement('li');
                li.className = `last-move ${it.tipo || ''}`;
                const sign = (it.tipo === 'venta') ? '-' : '+';
                const quien = it.tercero || it.proveedor || it.cliente || '—';
                const fecha = it.fecha || '';
                const mat = it.mercaderia || '';
                const neto = Number(it.neto || 0).toLocaleString('es-AR');
                li.innerHTML = `<span class="lm-date">${fecha}</span><span class="lm-who">${quien}</span><span class="lm-mat">${mat}</span><span class="lm-neto ${it.tipo==='venta'?'neg':'pos'}">${sign}${neto} kg</span>`;
                ul.appendChild(li);
            });
        } catch (e) {
            console.warn(e);
        }
    }

    // Personalización: toggles de secciones del dashboard
    function loadDashboardVisibility() {
        try {
            const raw = localStorage.getItem(DASHBOARD_VIS_KEY);
            if (!raw) return;
            const parsed = JSON.parse(raw);
            if (parsed && typeof parsed === 'object') {
                dashboardVisibility = { ...dashboardVisibility, ...parsed };
            }
        } catch(_) {}
    }

    function applyDashboardVisibility() {
        const secEntries = document.getElementById('section-entries');
        const sec5 = document.getElementById('section-5days');
    const secRank = document.getElementById('section-ranking');
    const secLast = document.getElementById('section-last-moves');
        if (secEntries) secEntries.style.display = dashboardVisibility.entries ? '' : 'none';
        if (sec5) sec5.style.display = dashboardVisibility.days5 ? '' : 'none';
        if (secRank) secRank.style.display = dashboardVisibility.ranking ? '' : 'none';
    if (secLast) secLast.style.display = dashboardVisibility.lastmoves ? '' : 'none';
        // Sincronizar checkboxes
        const tEntries = document.getElementById('toggle-entries');
        const t5 = document.getElementById('toggle-5days');
        const tRank = document.getElementById('toggle-ranking');
    const tMoves = document.getElementById('toggle-lastmoves');
        if (tEntries) tEntries.checked = !!dashboardVisibility.entries;
        if (t5) t5.checked = !!dashboardVisibility.days5;
        if (tRank) tRank.checked = !!dashboardVisibility.ranking;
    if (tMoves) tMoves.checked = !!dashboardVisibility.lastmoves;
    }

    function saveDashboardVisibility() {
        try { localStorage.setItem(DASHBOARD_VIS_KEY, JSON.stringify(dashboardVisibility)); } catch(_) {}
    }

    function wireDashboardToggles() {
        const tEntries = document.getElementById('toggle-entries');
        const t5 = document.getElementById('toggle-5days');
        const tRank = document.getElementById('toggle-ranking');
        const btnReset = document.getElementById('reset-dashboard');
        if (tEntries) tEntries.addEventListener('change', () => { dashboardVisibility.entries = !!tEntries.checked; saveDashboardVisibility(); applyDashboardVisibility(); });
        if (t5) t5.addEventListener('change', () => { dashboardVisibility.days5 = !!t5.checked; saveDashboardVisibility(); applyDashboardVisibility(); });
        if (tRank) tRank.addEventListener('change', () => { dashboardVisibility.ranking = !!tRank.checked; saveDashboardVisibility(); applyDashboardVisibility(); });
        const tMoves = document.getElementById('toggle-lastmoves');
        if (tMoves) tMoves.addEventListener('change', () => { dashboardVisibility.lastmoves = !!tMoves.checked; saveDashboardVisibility(); applyDashboardVisibility(); });
        if (btnReset) btnReset.addEventListener('click', () => {
            dashboardVisibility = { entries: true, days5: true, ranking: true, lastmoves: true };
            saveDashboardVisibility();
            applyDashboardVisibility();
        });
    }

    async function updateLast5DaysBalance(endDate) {
        const token = getToken();
        if (!token) return;
        try {
            const url = endDate ? `${API_BASE_URL}/api/dashboard/last5days?end_date=${encodeURIComponent(endDate)}` : `${API_BASE_URL}/api/dashboard/last5days`;
            const resp = await fetch(url, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!resp.ok) throw new Error('No se pudo cargar el balance de los últimos 5 días');
            const series = await resp.json(); // [{fecha, balance_neto}]
            const labels = series.map(d => formatShortDate(d.fecha));
            const values = series.map(d => d.balance_neto);
            renderLast5DaysChart(labels, values);
        } catch (e) {
            console.error(e);
        }
    }

    function formatShortDate(yyyyMMdd) {
        // yyyy-mm-dd -> dd/mm
        try {
            const [y, m, d] = yyyyMMdd.split('-');
            return `${d}/${m}`;
        } catch {
            return yyyyMMdd;
        }
    }

    function updateEntriesExitsChart(compras, ventas, balanceNeto = (compras - ventas)) {
        const ctx = document.getElementById('entriesExitsChart').getContext('2d');
        const data = {
            labels: ['Entradas (Compras)', 'Salidas (Ventas)'],
            datasets: [{
                data: [compras, ventas],
                backgroundColor: ['#2e7d32', '#e53935'], // verde más fuerte y rojo
                hoverBackgroundColor: ['#1b5e20', '#c62828'],
                borderColor: ['#ffffff', '#ffffff'],
                borderWidth: 2,
                cutout: '58%'
            }]
        };

        // Plugin para texto central con el balance neto
      const centerTextPlugin = {
            id: 'centerTextPlugin',
            afterDraw(chart, args, options) {
                const {ctx, chartArea: {width, height}} = chart;
                ctx.save();
                const centerX = chart.getDatasetMeta(0).data[0].x;
                const centerY = chart.getDatasetMeta(0).data[0].y;
                const isDark = document.body.classList.contains('dark-mode');
                const title = 'Balance neto';
            // Preferir el valor en la instancia del gráfico; fallback al cálculo por datos o al parámetro
            const currentData = chart.data?.datasets?.[0]?.data || [];
            let bn = typeof chart.__balance === 'number' ? chart.__balance
                : (currentData.length === 2 ? (Number(currentData[0] || 0) - Number(currentData[1] || 0)) : (balanceNeto || 0));
            const value = `${(bn || 0).toFixed(2)} kg`;
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                // Título más grande y en negrita
                ctx.fillStyle = isDark ? '#ffffff' : '#111';
                ctx.font = '700 14px Merriweather, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif';
                ctx.fillText(title, centerX, centerY - 14);
                // Valor grande con mejor alineación de unidad
                ctx.fillStyle = isDark ? '#ffffff' : '#000';
                ctx.font = '800 20px Merriweather, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif';
                ctx.fillText(value, centerX, centerY + 10);
                ctx.restore();
            }
        };

        if (entriesExitsChart) {
            entriesExitsChart.data = data;
            // Guardar balance en instancia para que el plugin lo use en updates
            entriesExitsChart.__balance = balanceNeto;
            entriesExitsChart.update();
        } else {
            entriesExitsChart = new Chart(ctx, {
                type: 'doughnut',
                data: data,
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: {
                                // En modo oscuro forzar blanco
                                color: (ctx) => (document.body.classList.contains('dark-mode') ? '#ffffff' : '#000000')
                            }
                        },
                        datalabels: {
                            color: (ctx) => (document.body.classList.contains('dark-mode') ? '#fff' : '#000'),
                            font: { weight: '700' },
                            formatter: (value, ctx) => {
                                const dataset = ctx.chart.data.datasets[0];
                                const total = dataset.data.reduce((a, b) => Number(a) + Number(b), 0) || 1;
                                const pct = (value / total) * 100;
                                return `${pct.toFixed(0)}%`;
                            },
                            anchor: 'center',
                            align: 'center'
                        },
                        tooltip: {
                            titleColor: (ctx) => (document.body.classList.contains('dark-mode') ? '#ffffff' : '#000000'),
                            bodyColor: (ctx) => (document.body.classList.contains('dark-mode') ? '#ffffff' : '#000000'),
                            callbacks: {
                                label: (ctx) => `${ctx.label}: ${ctx.parsed} kg (${(() => {
                                    const total = ctx.dataset.data.reduce((a, b) => Number(a) + Number(b), 0) || 1;
                                    return ((ctx.parsed / total) * 100).toFixed(0);
                                })()}%)`
                            }
                        }
                    },
                    cutout: '58%'
                },
                plugins: [centerTextPlugin, ChartDataLabels]
            });
            entriesExitsChart.__balance = balanceNeto;
        }
    }

    // Estado para controles del gráfico de materiales
    let materialChartState = { topN: 10, horizontal: true };

    function updateMaterialTypesChart(materialData) {
        const canvas = document.getElementById('materialTypesChart');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');

        // Ordenar por kilos desc y aplicar Top N
        const sorted = [...materialData].sort((a,b) => Number(b.total_kilos||0) - Number(a.total_kilos||0));
        let filtered = sorted;
        if (materialChartState.topN !== 'all') {
            const n = Number(materialChartState.topN) || 10;
            filtered = sorted.slice(0, n);
        }

        const labels = filtered.map(item => item.mercaderia);
        const data = filtered.map(item => Number(item.total_kilos || 0));
        const total = data.reduce((a,b)=>a+Number(b||0),0);

        // Mostrar total arriba a la derecha
        try {
            const totalEl = document.getElementById('material-total');
            if (totalEl) totalEl.textContent = `Total: ${total.toLocaleString('es-AR')} kg`;
        } catch(_) {}

        // Paleta sobria
        const base = ['#7daea3','#5aa29a','#8cc0b3','#4f8f87','#91c7bd','#6fb3a8','#88bfb4','#63a79e','#7cb7ad','#4aa096'];
        const colors = labels.map((_, i) => base[i % base.length]);

        const chartData = {
            labels,
            datasets: [{
                label: 'Kilos comprados',
                data,
                backgroundColor: colors,
                borderRadius: 6,
                barThickness: 'flex'
            }]
        };

        const isDark = document.body.classList.contains('dark-mode');
        const common = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    titleColor: () => (document.body.classList.contains('dark-mode') ? '#ffffff' : '#000000'),
                    bodyColor: () => (document.body.classList.contains('dark-mode') ? '#ffffff' : '#000000'),
                    callbacks: {
                        label: (ctx) => {
                            const v = Number(ctx.parsed[materialChartState.horizontal ? 'x' : 'y'] || 0);
                            const pct = total ? (v/total*100).toFixed(1) : '0.0';
                            return `${v.toLocaleString('es-AR')} kg (${pct}%)`;
                        }
                    }
                }
            }
        };

        // Plugin para etiquetas de valor al final de la barra
        const valueLabelPlugin = {
            id: 'materialValueLabels',
            afterDatasetsDraw(chart) {
                const { ctx } = chart;
                ctx.save();
                ctx.font = '600 11px Merriweather, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = isDark ? '#ffffff' : '#333333';
                const metas = chart.getDatasetMeta(0).data;
                metas.forEach((bar, i) => {
                    const v = Number(data[i] || 0);
                    const pct = total ? Math.round(v/total*100) : 0;
                    const text = `${v.toLocaleString('es-AR')} kg · ${pct}%`;
                    // Posición según orientación
                    if (materialChartState.horizontal) {
                        ctx.textAlign = 'left';
                        ctx.fillText(text, bar.x + 8, bar.y);
                    } else {
                        ctx.textAlign = 'center';
                        ctx.fillText(text, bar.x, bar.y - 8);
                    }
                });
                ctx.restore();
            }
        };

    const options = materialChartState.horizontal ? {
            ...common,
            indexAxis: 'y',
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: { color: isDark ? '#fff' : '#000' },
                    grid: { color: isDark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.08)' },
                    title: { display: true, text: 'Kilos', color: isDark ? '#fff' : '#000' }
                },
                y: {
                    ticks: { color: isDark ? '#fff' : '#000' },
                    grid: { display: false }
                }
            }
        } : {
            ...common,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { color: isDark ? '#fff' : '#000' },
                    grid: { color: isDark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.08)' },
                    title: { display: true, text: 'Kilos', color: isDark ? '#fff' : '#000' }
                },
                x: {
                    ticks: { color: isDark ? '#fff' : '#000', maxRotation: 30, minRotation: 20 },
                    grid: { display: false }
                }
            }
        };

        if (materialTypesChart) {
            materialTypesChart.data = chartData;
            materialTypesChart.options = options;
            materialTypesChart.update();
        } else {
            // Asegurar altura fija del canvas (fallback por si CSS no aplica por alguna razón)
            try { canvas.style.height = '420px'; } catch(_) {}
            materialTypesChart = new Chart(ctx, { type: 'bar', data: chartData, options, plugins: [valueLabelPlugin] });
        }
    }

    // Listeners para controles del gráfico de materiales
    document.addEventListener('click', (ev) => {
        const target = ev.target;
        if (!(target instanceof HTMLElement)) return;
        if (target.matches('.material-chips .preset-chip[data-top]')) {
            document.querySelectorAll('.material-chips .preset-chip[data-top]').forEach(el => el.classList.remove('active'));
            target.classList.add('active');
            const val = target.getAttribute('data-top') || '10';
            materialChartState.topN = (val === 'all') ? 'all' : parseInt(val, 10);
            // Recalcular usando la última data cargada en el dashboard
            try { refreshMaterialChartFromServer(); } catch (_) {}
        }
    // El botón de orientación puede no existir; no hacer nada si no está presente en HTML
    });

    // Helper: reutiliza las fechas del dashboard para recargar solo el gráfico de materiales
    async function refreshMaterialChartFromServer() {
        const startDate = document.getElementById('dashboard-date-start')?.value;
        const endDate = document.getElementById('dashboard-date-end')?.value;
        const token = getToken();
        if (!token || !startDate || !endDate) return;
        try {
            const response = await fetch(`${API_BASE_URL}/api/dashboard/data?start_date=${startDate}&end_date=${endDate}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!response.ok) throw new Error('No se pudo refrescar el gráfico de materiales');
            const data = await response.json();
            updateMaterialTypesChart(data.compras_por_material || []);
        } catch (e) { console.warn(e); }
    }

    function renderLast5DaysChart(labels, data) {
        const canvas = document.getElementById('last5DaysBalanceChart');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const colors = data.map(v => v >= 0 ? '#43a047' : '#e57373');
        const chartData = {
            labels,
            datasets: [{
                label: 'Balance (kg) por día',
                data,
                backgroundColor: colors
            }]
        };
        const options = {
            responsive: true,
            plugins: { 
                legend: { display: false },
                tooltip: {
                    titleColor: () => (document.body.classList.contains('dark-mode') ? '#ffffff' : '#000000'),
                    bodyColor: () => (document.body.classList.contains('dark-mode') ? '#ffffff' : '#000000')
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'kg', color: () => (document.body.classList.contains('dark-mode') ? '#ffffff' : '#000000') },
                    grid: {
                        color: () => (document.body.classList.contains('dark-mode') ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.08)')
                    },
                    ticks: {
                        color: () => (document.body.classList.contains('dark-mode') ? '#ffffff' : '#000000')
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: () => (document.body.classList.contains('dark-mode') ? '#ffffff' : '#000000'),
                        maxRotation: 40,
                        minRotation: 25
                    }
                }
            }
        };
        const valueLabelPlugin = {
            id: 'barValueLabels',
            afterDatasetsDraw(chart) {
                const { ctx } = chart;
                ctx.save();
                ctx.font = '600 11px Merriweather, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'bottom';
                const isDark = document.body.classList.contains('dark-mode');
                const ds = chart.data.datasets[0];
                chart.getDatasetMeta(0).data.forEach((bar, i) => {
                    const val = (ds.data[i] ?? 0).toFixed(0);
                    ctx.fillStyle = isDark ? '#ffffff' : '#333';
                    ctx.fillText(val, bar.x, Math.min(bar.y, bar.base) - 4);
                });
                ctx.restore();
            }
        };
        // calcular promedio
        const avg = data.length ? (data.reduce((a,b)=>a+Number(b||0),0) / data.length) : 0;
        // Mostrar promedio debajo de la card para mejor visibilidad
        try {
            const avgEl = document.getElementById('avg-5days-text');
            if (avgEl) {
                avgEl.textContent = `Promedio últimos 5 días: ${avg.toFixed(0)} kg`;
            }
        } catch (_) { /* noop */ }

        if (last5DaysBalanceChart) {
            last5DaysBalanceChart.data = chartData;
            last5DaysBalanceChart.options = options;
            last5DaysBalanceChart.update();
        } else {
            last5DaysBalanceChart = new Chart(ctx, { type: 'bar', data: chartData, options, plugins: [valueLabelPlugin] });
        }
    }

    // --- Horizontal Scroll Arrows Logic ---
    // Flechas internas (dentro del área scrollable)
    document.querySelectorAll('.scroll-arrow').forEach(arrow => {
        arrow.addEventListener('click', function() {
            const container = this.closest('.scroll-arrows-container');
            const tableWrapper = container.querySelector('.table-wrapper');
            const scrollAmount = 200;
            if (this.classList.contains('left')) {
                tableWrapper.scrollBy({ left: -scrollAmount, behavior: 'smooth' });
            } else if (this.classList.contains('right')) {
                tableWrapper.scrollBy({ left: scrollAmount, behavior: 'smooth' });
            }
        });
    });

    // Flechas flotantes externas
    const comprasScrollLeft = document.getElementById('comprasScrollLeft');
    const comprasScrollRight = document.getElementById('comprasScrollRight');
    const comprasTableWrapper = document.querySelector('#compras-content .table-wrapper');
    if (comprasScrollLeft && comprasTableWrapper) {
        comprasScrollLeft.addEventListener('click', function() {
            comprasTableWrapper.scrollBy({ left: -200, behavior: 'smooth' });
        });
    }
    if (comprasScrollRight && comprasTableWrapper) {
        comprasScrollRight.addEventListener('click', function() {
            comprasTableWrapper.scrollBy({ left: 200, behavior: 'smooth' });
        });
    }
    
    // Inicializar la app al cargar (rehidrata sesión si hay token válido)
    initializeApp();
});
