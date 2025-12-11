/**
 * Mejoras de accesibilidad (a11y) para el sistema de pesaje
 * Implementa ARIA labels, navegación por teclado y feedback para lectores de pantalla
 */

class AccessibilityManager {
    constructor() {
        this.focusTrapStack = [];
        this.announcer = this.createAnnouncer();
        this.setupGlobalKeyboardNav();
    }

    /**
     * Crea un elemento para anuncios a lectores de pantalla
     */
    createAnnouncer() {
        let announcer = document.getElementById('a11y-announcer');
        
        if (!announcer) {
            announcer = document.createElement('div');
            announcer.id = 'a11y-announcer';
            announcer.setAttribute('role', 'status');
            announcer.setAttribute('aria-live', 'polite');
            announcer.setAttribute('aria-atomic', 'true');
            announcer.style.cssText = `
                position: absolute;
                left: -10000px;
                width: 1px;
                height: 1px;
                overflow: hidden;
            `;
            document.body.appendChild(announcer);
        }

        return announcer;
    }

    /**
     * Anuncia mensaje a lectores de pantalla
     */
    announce(message, priority = 'polite') {
        this.announcer.setAttribute('aria-live', priority);
        this.announcer.textContent = '';
        
        setTimeout(() => {
            this.announcer.textContent = message;
        }, 100);
    }

    /**
     * Configura navegación global por teclado
     */
    setupGlobalKeyboardNav() {
        // Skip links para navegación rápida
        this.createSkipLinks();

        // Navegación entre tabs con flechas
        document.addEventListener('keydown', (e) => {
            const tabButtons = document.querySelectorAll('.tab-button');
            const activeTab = document.querySelector('.tab-button[aria-selected="true"]');
            
            if (!activeTab || !tabButtons.length) return;

            const currentIndex = Array.from(tabButtons).indexOf(activeTab);
            let newIndex;

            if (e.key === 'ArrowRight') {
                e.preventDefault();
                newIndex = (currentIndex + 1) % tabButtons.length;
            } else if (e.key === 'ArrowLeft') {
                e.preventDefault();
                newIndex = currentIndex - 1;
                if (newIndex < 0) newIndex = tabButtons.length - 1;
            }

            if (newIndex !== undefined) {
                tabButtons[newIndex].click();
                tabButtons[newIndex].focus();
            }
        });

        // Navegación en tablas con teclado
        this.setupTableKeyboardNav();
    }

    /**
     * Crea skip links para navegación rápida
     */
    createSkipLinks() {
        if (document.getElementById('skip-links')) return;

        const skipLinks = document.createElement('div');
        skipLinks.id = 'skip-links';
        skipLinks.innerHTML = `
            <style>
                #skip-links a {
                    position: absolute;
                    left: -10000px;
                    top: auto;
                    width: 1px;
                    height: 1px;
                    overflow: hidden;
                    background: var(--primary-color, #495f5b);
                    color: white;
                    padding: 0.75rem 1.5rem;
                    text-decoration: none;
                    border-radius: 0 0 4px 0;
                    font-weight: 600;
                    z-index: 10000;
                }
                #skip-links a:focus {
                    position: fixed;
                    left: 0;
                    top: 0;
                    width: auto;
                    height: auto;
                    overflow: visible;
                }
            </style>
            <a href="#main-content">Saltar al contenido principal</a>
            <a href="#compras-content">Ir a Compras</a>
            <a href="#ventas-content">Ir a Ventas</a>
            <a href="#dashboard-content">Ir a Dashboard</a>
        `;

        document.body.insertBefore(skipLinks, document.body.firstChild);
    }

    /**
     * Configura navegación por teclado en tablas
     */
    setupTableKeyboardNav() {
        document.addEventListener('keydown', (e) => {
            const target = e.target;
            
            // Solo actuar en inputs de tabla
            if (!target.matches('table input, table select')) return;

            const cell = target.closest('td');
            if (!cell) return;

            const row = cell.parentElement;
            const cells = Array.from(row.children);
            const currentIndex = cells.indexOf(cell);

            let newCell;

            switch(e.key) {
                case 'ArrowRight':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        newCell = cells[currentIndex + 1];
                    }
                    break;
                case 'ArrowLeft':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        newCell = cells[currentIndex - 1];
                    }
                    break;
                case 'ArrowUp':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        const prevRow = row.previousElementSibling;
                        if (prevRow) {
                            newCell = prevRow.children[currentIndex];
                        }
                    }
                    break;
                case 'ArrowDown':
                    if (e.ctrlKey || e.metaKey) {
                        e.preventDefault();
                        const nextRow = row.nextElementSibling;
                        if (nextRow) {
                            newCell = nextRow.children[currentIndex];
                        }
                    }
                    break;
            }

            if (newCell) {
                const input = newCell.querySelector('input, select, button');
                if (input) {
                    input.focus();
                    if (input.select) input.select();
                }
            }
        });
    }

    /**
     * Atrapa el foco dentro de un elemento (útil para modales)
     */
    trapFocus(element) {
        const focusableElements = element.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );

        if (focusableElements.length === 0) return () => {};

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        const handleTabKey = (e) => {
            if (e.key !== 'Tab') return;

            if (e.shiftKey) {
                if (document.activeElement === firstElement) {
                    e.preventDefault();
                    lastElement.focus();
                }
            } else {
                if (document.activeElement === lastElement) {
                    e.preventDefault();
                    firstElement.focus();
                }
            }
        };

        element.addEventListener('keydown', handleTabKey);
        firstElement.focus();

        this.focusTrapStack.push({ element, handler: handleTabKey });

        // Retornar función para liberar el trap
        return () => {
            element.removeEventListener('keydown', handleTabKey);
            const index = this.focusTrapStack.findIndex(trap => trap.element === element);
            if (index > -1) {
                this.focusTrapStack.splice(index, 1);
            }
        };
    }

    /**
     * Mejora accesibilidad de formularios
     */
    enhanceForm(formId) {
        const form = document.getElementById(formId);
        if (!form) return;

        // Asociar labels con inputs
        const inputs = form.querySelectorAll('input, select, textarea');
        inputs.forEach(input => {
            if (!input.id) {
                input.id = `${formId}-${input.name || Math.random().toString(36).substr(2, 9)}`;
            }

            // Buscar label asociado
            let label = form.querySelector(`label[for="${input.id}"]`);
            if (!label) {
                // Buscar label padre
                label = input.closest('label');
            }

            if (label && !label.getAttribute('for')) {
                label.setAttribute('for', input.id);
            }

            // Agregar aria-required si el input es required
            if (input.required) {
                input.setAttribute('aria-required', 'true');
            }

            // Agregar aria-invalid para validación
            if (!input.hasAttribute('aria-invalid')) {
                input.setAttribute('aria-invalid', 'false');
            }
        });

        // Mejorar mensajes de error
        const errorMessages = form.querySelectorAll('.error-message, .validation-error');
        errorMessages.forEach(error => {
            if (!error.id) {
                error.id = `error-${Math.random().toString(36).substr(2, 9)}`;
            }
            error.setAttribute('role', 'alert');
            error.setAttribute('aria-live', 'assertive');
        });
    }

    /**
     * Mejora accesibilidad de tablas
     */
    enhanceTable(tableId) {
        const table = document.getElementById(tableId);
        if (!table) return;

        // Agregar caption si no existe
        if (!table.querySelector('caption')) {
            const caption = document.createElement('caption');
            caption.className = 'sr-only';
            caption.textContent = table.getAttribute('aria-label') || 'Tabla de datos';
            table.insertBefore(caption, table.firstChild);
        }

        // Asegurar scope en headers
        const headers = table.querySelectorAll('thead th');
        headers.forEach(th => {
            if (!th.hasAttribute('scope')) {
                th.setAttribute('scope', 'col');
            }
        });

        // Agregar roles ARIA si no existen
        if (!table.hasAttribute('role')) {
            table.setAttribute('role', 'table');
        }
    }

    /**
     * Mejora accesibilidad de botones
     */
    enhanceButtons() {
        const buttons = document.querySelectorAll('button, [role="button"]');
        
        buttons.forEach(button => {
            // Asegurar que tenga texto o aria-label
            if (!button.textContent.trim() && !button.getAttribute('aria-label')) {
                const icon = button.querySelector('i[class*="fa-"]');
                if (icon) {
                    const iconClass = Array.from(icon.classList).find(c => c.startsWith('fa-'));
                    if (iconClass) {
                        const label = iconClass.replace('fa-', '').replace(/-/g, ' ');
                        button.setAttribute('aria-label', label);
                    }
                }
            }

            // Mejorar estado disabled
            if (button.disabled) {
                button.setAttribute('aria-disabled', 'true');
            }
        });
    }

    /**
     * Configura landmarks ARIA
     */
    setupLandmarks() {
        // Main content
        const main = document.querySelector('main');
        if (main && !main.hasAttribute('role')) {
            main.setAttribute('role', 'main');
            main.id = 'main-content';
        }

        // Navigation
        const nav = document.querySelector('.tabs');
        if (nav && !nav.hasAttribute('role')) {
            nav.setAttribute('role', 'navigation');
            nav.setAttribute('aria-label', 'Navegación principal');
        }

        // Header
        const header = document.querySelector('header');
        if (header && !header.hasAttribute('role')) {
            header.setAttribute('role', 'banner');
        }
    }

    /**
     * Inicializa todas las mejoras de accesibilidad
     */
    init() {
        // Setup landmarks
        this.setupLandmarks();

        // Mejorar formularios
        document.querySelectorAll('form').forEach(form => {
            if (form.id) this.enhanceForm(form.id);
        });

        // Mejorar tablas
        document.querySelectorAll('table').forEach(table => {
            if (table.id) this.enhanceTable(table.id);
        });

        // Mejorar botones
        this.enhanceButtons();

        // Anunciar página cargada
        this.announce('Página cargada correctamente');

        console.log('✓ Mejoras de accesibilidad inicializadas');
    }
}

// Utilidades para clases solo-lectura-pantalla
const srOnlyStyles = `
    <style>
        .sr-only {
            position: absolute;
            left: -10000px;
            width: 1px;
            height: 1px;
            top: auto;
            overflow: hidden;
        }
        
        .sr-only-focusable:focus {
            position: static;
            width: auto;
            height: auto;
        }
    </style>
`;

if (!document.getElementById('sr-only-styles')) {
    document.head.insertAdjacentHTML('beforeend', srOnlyStyles.replace('<style>', '<style id="sr-only-styles">'));
}

// Export para uso global
window.AccessibilityManager = AccessibilityManager;

// Inicializar automáticamente cuando el DOM esté listo
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.a11yManager = new AccessibilityManager();
        window.a11yManager.init();
    });
} else {
    window.a11yManager = new AccessibilityManager();
    window.a11yManager.init();
}
