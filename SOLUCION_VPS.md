# 🔧 SOLUCIÓN: PWA no funciona en VPS/Dominio

## ⚠️ Problema Identificado

Tu PWA funciona en **localhost** pero NO en tu **VPS/dominio** porque:

1. ❌ **Service Workers solo funcionan con HTTPS** (excepto localhost)
2. ⚠️ Los archivos estáticos necesitan headers especiales
3. 🔒 El dominio debe tener certificado SSL válido

---

## ✅ Solución Implementada

He actualizado **3 archivos** para que funcione:

### 1. `main.py` (servidor FastAPI)
- ✅ Agregadas rutas especiales para `/service-worker.js` y `/manifest.json`
- ✅ Headers correctos para PWA
- ✅ Cache-Control configurado

### 2. `service-worker.js` (v1.0.1)
- ✅ Usa `BASE_URL` dinámico (funciona en localhost Y dominio)
- ✅ Ignora rutas `/api/` para que no las cachee
- ✅ Mejor manejo de errores
- ✅ Logs más detallados

### 3. `index.html`
- ✅ Registro del service worker mejorado
- ✅ Logs de diagnóstico en consola
- ✅ Verificación automática de caché

### 4. `diagnostico-pwa.html` (NUEVO)
- ✅ Herramienta de diagnóstico visual
- ✅ Verifica estado del SW y caché
- ✅ Pruebas offline

---

## 🚀 Pasos para Solucionar en tu VPS

### Paso 1: Verificar HTTPS
Tu dominio **DEBE usar HTTPS**. Verifica:

```bash
# En tu VPS, verifica si tienes certificado SSL
sudo certbot certificates

# Si NO tienes certificado, instálalo (ejemplo con Certbot):
sudo certbot --nginx -d tudominio.com
```

**⚠️ IMPORTANTE:** Sin HTTPS, los Service Workers NO funcionarán en producción.

### Paso 2: Subir archivos actualizados
Sube estos archivos a tu VPS:

```bash
# Desde tu PC local (PowerShell):
scp static/service-worker.js usuario@tu-vps:/ruta/balanza/static/
scp static/index.html usuario@tu-vps:/ruta/balanza/static/
scp static/manifest.json usuario@tu-vps:/ruta/balanza/static/
scp static/diagnostico-pwa.html usuario@tu-vps:/ruta/balanza/static/
scp main.py usuario@tu-vps:/ruta/balanza/
```

O usando FileZilla/WinSCP:
1. Conecta a tu VPS
2. Sube todos los archivos de la carpeta `static/`
3. Sube `main.py` a la raíz del proyecto

### Paso 3: Reiniciar el servidor
En tu VPS:

```bash
# Detener el servidor actual
sudo systemctl stop balanza  # o el nombre de tu servicio

# O si usas screen/tmux, cierra la sesión y reinicia

# Reiniciar
cd /ruta/balanza
python3 main.py

# O si usas systemd:
sudo systemctl restart balanza
```

### Paso 4: Limpiar caché del navegador
En tu navegador:

1. Abre DevTools (F12)
2. Ve a **Application** → **Clear Storage**
3. Marca todo y haz clic en **"Clear site data"**
4. Cierra DevTools
5. Recarga la página (Ctrl + Shift + R)

### Paso 5: Verificar con la herramienta de diagnóstico

Navega a:
```
https://tudominio.com/diagnostico-pwa.html
```

Debes ver:
- ✅ Service Worker REGISTRADO (verde)
- ✅ Caché con archivos (verde)
- ✅ Protocolo: HTTPS (verde)

---

## 🧪 Probar que Funciona Offline

### Método 1: DevTools (Recomendado)
1. Abre tu sitio: `https://tudominio.com`
2. Abre DevTools (F12)
3. Ve a **Application** → **Service Workers**
4. Verifica que aparezca como "Activated and running"
5. Ve a **Network** → Activa el checkbox **"Offline"**
6. Recarga la página (F5)
7. ✅ **Debe cargar sin errores**

### Método 2: Desconectar internet
1. Visita tu sitio CON internet
2. Espera 5 segundos (para que cachee todo)
3. Desconecta WiFi/datos
4. Recarga la página (F5)
5. ✅ **Debe funcionar completamente**

### Método 3: Modo Avión (móvil)
1. Abre tu sitio en el celular
2. Activa Modo Avión
3. Abre la app
4. ✅ **Debe funcionar**

---

## 🔍 Verificaciones en el Navegador

### Abrir DevTools (F12) y verificar:

#### 1. Console (Consola)
Debes ver estos mensajes:
```
🚀 Iniciando registro de Service Worker
📍 URL actual: https://tudominio.com
✅ Service Worker registrado correctamente
   📂 Scope: https://tudominio.com/
   🔧 Estado: Activo
💾 Cachés disponibles: ["balanza-cache-v1.0.1"]
📦 Archivos en caché: 11
   ✅ PWA lista para funcionar OFFLINE
```

#### 2. Application → Service Workers
- Estado: **Activated and running** (círculo verde)
- Scope: **https://tudominio.com/**

#### 3. Application → Cache Storage
- Debe aparecer: **balanza-cache-v1.0.1**
- Al expandir, debe mostrar ~11 archivos

#### 4. Network (con Offline activado)
- Recarga la página
- Todos los recursos deben mostrar: **(ServiceWorker)**
- No debe haber errores 404

---

## ❌ Problemas Comunes y Soluciones

### Error: "Service Worker registration failed"
**Causa:** No estás usando HTTPS
**Solución:** Instala certificado SSL en tu VPS

### Error: "Failed to fetch service-worker.js"
**Causa:** Archivo no subido o ruta incorrecta
**Solución:** 
```bash
# Verificar que existe
ls -la /ruta/balanza/static/service-worker.js

# Si no existe, súbelo de nuevo
```

### Los cambios no se ven
**Causa:** Caché antiguo activo
**Solución:**
1. Abre: `https://tudominio.com/diagnostico-pwa.html`
2. Haz clic en **"🗑️ Limpiar Caché"**
3. Haz clic en **"❌ Desregistrar SW"**
4. Recarga la página principal

### La página se queda en blanco offline
**Causa:** No se cachearon los archivos
**Solución:**
1. CON internet, abre el sitio
2. Espera 10 segundos
3. Abre DevTools → Application → Cache Storage
4. Verifica que tenga archivos
5. Si está vacío, revisa la consola por errores

### Error 404 en service-worker.js
**Causa:** FastAPI no está sirviendo el archivo correctamente
**Solución:** Verifica que `main.py` tenga las rutas agregadas:

```python
# Debe estar en main.py (cerca de la línea 2360)
@app.get("/service-worker.js")
async def service_worker():
    ...
```

---

## 🔒 Configuración HTTPS con Nginx (Ejemplo)

Si usas Nginx como proxy reverso:

```nginx
server {
    listen 443 ssl http2;
    server_name tudominio.com;
    
    ssl_certificate /etc/letsencrypt/live/tudominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tudominio.com/privkey.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Headers adicionales para PWA
    add_header Service-Worker-Allowed /;
}
```

Después de editar:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## 📊 Checklist Final

Antes de probar, verifica:

- [ ] ✅ El dominio usa HTTPS (https://)
- [ ] ✅ Certificado SSL válido (sin errores)
- [ ] ✅ Archivos subidos al VPS
- [ ] ✅ `main.py` actualizado con las rutas del SW
- [ ] ✅ Servidor FastAPI reiniciado
- [ ] ✅ Caché del navegador limpiado
- [ ] ✅ DevTools muestra SW como "Activated"
- [ ] ✅ Cache Storage tiene archivos
- [ ] ✅ Funciona en modo offline

---

## 🆘 Si Nada Funciona

### Opción 1: Diagnóstico Completo
Abre: `https://tudominio.com/diagnostico-pwa.html`

Captura de pantalla y envía:
- Estado del Service Worker
- Lista de archivos en caché
- Errores en la consola

### Opción 2: Verificar con Lighthouse
1. DevTools (F12) → **Lighthouse**
2. Marca solo **"Progressive Web App"**
3. Haz clic en **"Analyze page load"**
4. Debe dar puntaje alto (>80)

### Opción 3: Logs del servidor
```bash
# Ver logs en tiempo real
tail -f /var/log/balanza/error.log

# O si usas systemd:
sudo journalctl -u balanza -f
```

---

## 📱 Instalación como App en Móvil

Una vez que funcione offline:

### Android (Chrome):
1. Abre `https://tudominio.com`
2. Menú (⋮) → **"Agregar a pantalla de inicio"**
3. ✅ Aparece ícono como app nativa

### iOS (Safari):
1. Abre `https://tudominio.com`
2. Botón compartir → **"Añadir a pantalla de inicio"**
3. ✅ Aparece ícono

---

## 🎯 Resumen: ¿Qué cambió?

| Archivo | Cambios |
|---------|---------|
| `main.py` | + Rutas para SW y manifest con headers correctos |
| `service-worker.js` | + BASE_URL dinámico, ignora /api/, mejor logging |
| `index.html` | + Logging detallado, verificación de caché |
| `diagnostico-pwa.html` | + NUEVO: Herramienta de pruebas |

**Versión actual:** v1.0.1

---

## ✨ Resultado Esperado

Después de aplicar estos cambios:

✅ La web carga la primera vez CON internet
✅ Todo se cachea automáticamente
✅ Desconectas internet
✅ La web sigue funcionando 100%
✅ Puedes recargar sin conexión sin problemas
✅ Se puede instalar como app nativa

---

¡Tu PWA ahora funciona en producción! 🚀
