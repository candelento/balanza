# 🚀 Instrucciones de Instalación PWA - Sistema de Pesaje

## ✅ Archivos Creados

He creado **3 archivos nuevos** en tu carpeta `static`:

1. **`service-worker.js`** - El cerebro de la PWA que cachea todo
2. **`manifest.json`** - Configuración de la aplicación
3. **`index.html`** - Actualizado con el registro del service worker

---

## 📁 Ubicación de los Archivos

Todos los archivos están en:
```
c:\Users\Usuario\Documents\balanza\static\
```

### Estructura después de la instalación:
```
static/
├── index.html              ← ACTUALIZADO (registra el service worker)
├── service-worker.js       ← NUEVO (cachea archivos)
├── manifest.json           ← NUEVO (config PWA)
├── styles.css
├── script.js
├── config.js
├── logo.png
├── logo1.png
├── fondo.jpeg
├── fondo.webp
└── js/
    └── accessibility.js
```

---

## 🌐 Rutas Configuradas

El service worker cachea estas rutas **automáticamente**:

### Archivos Locales:
- `/` (raíz)
- `/index.html`
- `/styles.css`
- `/script.js`
- `/config.js`
- `/logo.png`
- `/logo1.png`
- `/fondo.jpeg`
- `/fondo.webp`
- `/js/accessibility.js`

### Recursos Externos (CDN):
- Font Awesome
- Google Fonts (Merriweather, Playfair Display, Inter)
- Flatpickr
- Chart.js
- Hammer.js
- Zoom plugin

---

## 🔧 Cómo Funciona

### Primera vez CON internet:
1. El usuario entra a tu web
2. El service worker se instala
3. **Todos los archivos se cachean automáticamente**
4. ✅ La web está lista para funcionar offline

### Sin internet:
1. El usuario abre la web (incluso sin conexión)
2. El service worker carga **todo desde el cache**
3. ✅ La web funciona 100% igual que con internet

### Recarga sin internet:
1. El usuario recarga la página (F5)
2. El service worker intercepta la petición
3. Devuelve los archivos desde el cache
4. ✅ **NO se rompe nada**

---

## 🔄 Actualizar Archivos (Nueva Versión)

Cuando modifiques CSS, JS o HTML:

### Paso 1: Editar el archivo `service-worker.js`
Cambia el número de versión en la línea 3:

```javascript
const CACHE_VERSION = 'v1.0.1'; // ← Cambia esto cada vez
```

**Ejemplos:**
- Primera actualización: `'v1.0.1'`
- Segunda actualización: `'v1.0.2'`
- Cambio mayor: `'v2.0.0'`

### Paso 2: Subir los archivos
Sube los archivos modificados normalmente a tu servidor.

### Paso 3: Los usuarios actualizan
1. El usuario entra con internet
2. El service worker detecta la nueva versión
3. Aparece un mensaje: **"Hay una nueva versión disponible. ¿Deseas actualizar?"**
4. El usuario acepta → **Se actualiza automáticamente**

---

## 🧪 Probar que Funciona

### Test 1: Primera instalación
1. Abre Chrome/Edge
2. Navega a `http://localhost:puerto/` o tu dominio
3. Abre DevTools (F12) → Pestaña **Console**
4. Debes ver: **`✅ Service Worker registrado correctamente`**
5. Ve a **Application** → **Service Workers** → Debe aparecer como **Activated**

### Test 2: Verificar cache
1. En DevTools → **Application** → **Cache Storage**
2. Expande `balanza-cache-v1.0.0`
3. Debes ver **todos los archivos listados** (HTML, CSS, JS, imágenes, CDNs)

### Test 3: Modo offline
1. En DevTools → **Network** → Activa **"Offline"**
2. Recarga la página (F5)
3. ✅ **La web debe cargar completamente**
4. Todas las funciones deben funcionar

### Test 4: En móvil
1. Abre Chrome en tu celular
2. Navega a tu web
3. Menú → **"Agregar a pantalla de inicio"**
4. Se crea un ícono como una app nativa
5. Desactiva WiFi/datos
6. Abre la app → ✅ **Funciona sin internet**

---

## ⚙️ Configuración Avanzada

### Agregar más archivos al cache

Edita `service-worker.js` líneas 8-18:

```javascript
const LOCAL_FILES_TO_CACHE = [
  '/',
  '/index.html',
  '/styles.css',
  '/script.js',
  '/nuevo-archivo.js',  // ← Agrega aquí
  '/imagenes/foto.jpg'   // ← O aquí
];
```

### Cambiar estrategia de cache

El service worker usa **"Cache First, Network Fallback"**:
- Primero busca en cache
- Si no está, intenta red
- Si red falla, devuelve error

Para cambiar a **"Network First"** (buscar primero en red), invierte las líneas 112-146.

---

## 🐛 Solución de Problemas

### El service worker no se registra
**Solución:** Verifica que estés usando HTTPS o `localhost` (HTTP no funciona en PWA)

### Los cambios no se ven
**Solución:**
1. Cambia `CACHE_VERSION` en `service-worker.js`
2. Borra cache manualmente: DevTools → Application → Clear Storage → Clear

### Error "Failed to fetch"
**Solución:** 
- Verifica que la ruta del archivo sea correcta
- Asegúrate que el archivo existe en el servidor

### La app no aparece en "Agregar a pantalla de inicio"
**Solución:**
- Necesitas HTTPS (excepto localhost)
- Verifica que `manifest.json` esté correctamente vinculado
- El service worker debe estar activo

---

## 📦 NO Necesitas Instalar Nada

- ❌ No necesitas instalar paquetes NPM
- ❌ No necesitas Node.js
- ❌ No necesitas compilar nada
- ✅ Solo sube los archivos y funciona

---

## 🎯 Resumen Rápido

| Archivo | Ubicación | Propósito |
|---------|-----------|-----------|
| `service-worker.js` | `/static/` | Cachea archivos y gestiona offline |
| `manifest.json` | `/static/` | Configuración de la PWA |
| `index.html` | `/static/` | Registra el service worker |

**Versión actual:** v1.0.0
**Estado:** ✅ Listo para usar

---

## ✨ Características Implementadas

- ✅ Cache automático en primera visita
- ✅ Funciona 100% offline después de la primera carga
- ✅ Actualización automática cuando subes nueva versión
- ✅ No se rompe al recargar sin internet
- ✅ Manejo de errores robusto
- ✅ Compatible con todos los navegadores modernos
- ✅ Instalable como app nativa en móvil
- ✅ Cache de recursos externos (CDN)

---

## 📱 Compatibilidad

- ✅ Chrome/Edge (escritorio y móvil)
- ✅ Firefox
- ✅ Safari (iOS/macOS)
- ✅ Opera
- ❌ Internet Explorer (obsoleto)

---

¡Tu sistema de pesaje ahora es una PWA completa! 🎉
