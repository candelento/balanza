// CONFIGURACIÓN DEL SERVICE WORKER
// Cambia este número cada vez que actualices archivos para forzar actualización
const CACHE_VERSION = 'v1.0.1';
const CACHE_NAME = `balanza-cache-${CACHE_VERSION}`;

// Obtener el origen actual (funciona en localhost y dominio)
const BASE_URL = self.location.origin;

// Lista de archivos locales a cachear (rutas relativas)
const LOCAL_FILES_TO_CACHE = [
  '/index.html',
  '/styles.css',
  '/script.js',
  '/config.js',
  '/logo.png',
  '/logo1.png',
  '/fondo.jpeg',
  '/fondo.webp',
  '/js/accessibility.js',
  '/manifest.json'
];

// Lista de recursos externos (CDN) a cachear
const EXTERNAL_FILES_TO_CACHE = [
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
  'https://fonts.googleapis.com/css2?family=Merriweather:wght@400;700&display=swap',
  'https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&display=swap',
  'https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap',
  'https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css',
  'https://cdn.jsdelivr.net/npm/chart.js',
  'https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2',
  'https://cdnjs.cloudflare.com/ajax/libs/hammer.js/2.0.8/hammer.min.js',
  'https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1/dist/chartjs-plugin-zoom.min.js',
  'https://cdn.jsdelivr.net/npm/flatpickr'
];

// Todos los archivos a cachear
const ALL_FILES_TO_CACHE = [...LOCAL_FILES_TO_CACHE, ...EXTERNAL_FILES_TO_CACHE];

// EVENTO INSTALL: Se ejecuta cuando se instala el service worker
self.addEventListener('install', (event) => {
  console.log('[Service Worker] Instalando desde:', BASE_URL);
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[Service Worker] Cacheando archivos...');
        
        // Cachear archivos locales con URLs completas
        const localCachePromises = LOCAL_FILES_TO_CACHE.map(url => {
          const fullUrl = `${BASE_URL}${url}`;
          return cache.add(fullUrl).catch(err => {
            console.warn(`[Service Worker] No se pudo cachear: ${fullUrl}`, err);
            return Promise.resolve();
          });
        });
        
        // Cachear archivos externos
        const externalCachePromises = EXTERNAL_FILES_TO_CACHE.map(url => {
          return cache.add(url).catch(err => {
            console.warn(`[Service Worker] No se pudo cachear CDN: ${url}`, err);
            return Promise.resolve();
          });
        });
        
        return Promise.all([...localCachePromises, ...externalCachePromises]);
      })
      .then(() => {
        console.log('[Service Worker] ✅ Archivos cacheados correctamente');
        console.log('[Service Worker] Cache:', CACHE_NAME);
        // Activar inmediatamente el nuevo service worker
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('[Service Worker] ❌ Error al cachear archivos:', error);
      })
  );
});

// EVENTO ACTIVATE: Se ejecuta cuando el service worker se activa
self.addEventListener('activate', (event) => {
  console.log('[Service Worker] Activando...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        // Eliminar cachés antiguos
        return Promise.all(
          cacheNames.map((cacheName) => {
            if (cacheName !== CACHE_NAME) {
              console.log('[Service Worker] Eliminando caché antiguo:', cacheName);
              return caches.delete(cacheName);
            }
          })
        );
      })
      .then(() => {
        console.log('[Service Worker] Caché limpio, activado correctamente');
        // Tomar control de todas las páginas inmediatamente
        return self.clients.claim();
      })
  );
});

// EVENTO FETCH: Intercepta todas las peticiones de red
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Ignorar peticiones no HTTP/HTTPS
  if (!request.url.startsWith('http')) {
    return;
  }

  // Ignorar peticiones POST, PUT, DELETE (solo cachear GET)
  if (request.method !== 'GET') {
    return;
  }

  // Ignorar peticiones a /api/ para que siempre vayan a la red
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(fetch(request));
    return;
  }

  event.respondWith(
    caches.match(request)
      .then((cachedResponse) => {
        // Si está en caché, devolverlo
        if (cachedResponse) {
          console.log('[Service Worker] 📦 Desde caché:', url.pathname);
          
          // Actualizar en segundo plano (estrategia stale-while-revalidate)
          fetch(request)
            .then((networkResponse) => {
              if (networkResponse && networkResponse.status === 200) {
                caches.open(CACHE_NAME).then((cache) => {
                  cache.put(request, networkResponse.clone());
                });
              }
            })
            .catch(() => {
              // Silenciar errores de red en segundo plano
            });
          
          return cachedResponse;
        }

        // Si no está en caché, intentar obtenerlo de la red
        console.log('[Service Worker] 🌐 Desde red:', url.pathname);
        return fetch(request)
          .then((networkResponse) => {
            // Si la respuesta es válida, guardarla en caché
            if (networkResponse && networkResponse.status === 200) {
              const responseToCache = networkResponse.clone();
              
              caches.open(CACHE_NAME)
                .then((cache) => {
                  // Solo cachear recursos de nuestro dominio y CDNs conocidos
                  if (request.url.startsWith(BASE_URL) || 
                      request.url.includes('cdnjs.cloudflare.com') ||
                      request.url.includes('cdn.jsdelivr.net') ||
                      request.url.includes('fonts.googleapis.com') ||
                      request.url.includes('fonts.gstatic.com')) {
                    cache.put(request, responseToCache);
                  }
                })
                .catch((error) => {
                  console.warn('[Service Worker] ⚠️ Error al guardar en caché:', error);
                });
            }
            
            return networkResponse;
          })
          .catch((error) => {
            console.error('[Service Worker] ❌ Error de red para:', url.pathname);
            
            // Si falla la red y es una página HTML, devolver index.html
            if (request.destination === 'document' || url.pathname === '/') {
              return caches.match(`${BASE_URL}/index.html`).then(response => {
                if (response) {
                  return response;
                }
                return new Response('Sitio no disponible offline', {
                  status: 503,
                  statusText: 'Service Unavailable',
                  headers: { 'Content-Type': 'text/html; charset=utf-8' }
                });
              });
            }
            
            // Para otros recursos, devolver error
            return new Response('Recurso no disponible offline', {
              status: 503,
              statusText: 'Service Unavailable',
              headers: { 'Content-Type': 'text/plain' }
            });
          });
      })
  );
});

// Evento para sincronización en segundo plano (opcional)
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});
