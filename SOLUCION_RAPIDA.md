# 🚨 SOLUCIÓN RÁPIDA: PWA no funciona en VPS

## ❌ Problema
Tu PWA funciona en **localhost** pero NO en tu **dominio/VPS**.

## ✅ Causa Principal
**Los Service Workers requieren HTTPS en producción** (no funciona con HTTP normal).

---

## 🎯 Solución en 5 Pasos

### ✅ PASO 1: Verifica HTTPS
Tu dominio **DEBE** tener certificado SSL:

```
https://tudominio.com  ✅ CORRECTO
http://tudominio.com   ❌ NO FUNCIONA
```

**Verificar:**
- Abre tu sitio en Chrome
- Debe aparecer el **candado 🔒** en la barra de direcciones
- Si aparece "No seguro", necesitas instalar SSL

**Instalar SSL (si no lo tienes):**
```bash
# En tu VPS (Ubuntu/Debian):
sudo apt update
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d tudominio.com
```

---

### ✅ PASO 2: Sube archivos actualizados
**4 archivos modificados:**

```
📁 Desde c:\Users\Usuario\Documents\balanza\

Subir a tu VPS:
├── static/
│   ├── index.html              ⬆️ ACTUALIZADO
│   ├── service-worker.js       ⬆️ ACTUALIZADO
│   ├── manifest.json           ⬆️ NUEVO
│   └── diagnostico-pwa.html    ⬆️ NUEVO
└── main.py                     ⬆️ ACTUALIZADO
```

**Método 1: Con SCP (PowerShell)**
```powershell
# Reemplaza con tus datos
$USUARIO = "tu-usuario"
$VPS = "tu-vps-ip-o-dominio"
$RUTA = "/home/usuario/balanza"

# Subir archivos
scp static\index.html ${USUARIO}@${VPS}:${RUTA}/static/
scp static\service-worker.js ${USUARIO}@${VPS}:${RUTA}/static/
scp static\manifest.json ${USUARIO}@${VPS}:${RUTA}/static/
scp static\diagnostico-pwa.html ${USUARIO}@${VPS}:${RUTA}/static/
scp main.py ${USUARIO}@${VPS}:${RUTA}/
```

**Método 2: Con FileZilla/WinSCP**
1. Conecta a tu VPS
2. Navega a la carpeta del proyecto
3. Arrastra los archivos

---

### ✅ PASO 3: Reinicia el servidor
**En tu VPS:**

```bash
# SSH a tu VPS
ssh usuario@tu-vps

# Ir a la carpeta
cd /ruta/a/balanza

# Detener servidor (ejemplo con systemd)
sudo systemctl stop balanza

# O si usas screen/tmux, detén el proceso

# Reiniciar
sudo systemctl start balanza

# O manualmente:
python3 main.py
```

---

### ✅ PASO 4: Limpia el navegador
**En tu PC, abre Chrome/Edge:**

1. Ve a: `https://tudominio.com`
2. Presiona **F12** (DevTools)
3. Ve a pestaña **Application**
4. Click en **"Clear storage"** (barra lateral izquierda)
5. Click en **"Clear site data"**
6. Cierra DevTools
7. Presiona **Ctrl + Shift + R** (recarga forzada)

---

### ✅ PASO 5: Verifica con herramienta de diagnóstico
Abre en tu navegador:

```
https://tudominio.com/diagnostico-pwa.html
```

**Debes ver:**
- ✅ **Service Worker REGISTRADO** (caja verde)
- ✅ **Caché con 11+ archivos** (caja verde)
- ✅ **Protocolo: HTTPS** (verde)

---

## 🧪 Prueba Offline

### Método DevTools (más fácil):
1. Abre: `https://tudominio.com` (CON internet)
2. Presiona **F12**
3. Ve a pestaña **Network**
4. Activa checkbox **"Offline"** (arriba)
5. Presiona **F5** (recargar)
6. ✅ **La página debe cargar normalmente**

### Método real:
1. Abre: `https://tudominio.com` (CON internet)
2. Espera 5 segundos
3. Desconecta WiFi
4. Presiona **F5**
5. ✅ **Debe funcionar**

---

## 🔍 Verificar en Consola

Presiona **F12** → **Console**, debes ver:

```
🚀 Iniciando registro de Service Worker
📍 URL actual: https://tudominio.com
✅ Service Worker registrado correctamente
   📂 Scope: https://tudominio.com/
   🔧 Estado: Activo ✅
💾 Cachés disponibles: ["balanza-cache-v1.0.1"]
📦 Archivos en caché: 11
   ✅ PWA lista para funcionar OFFLINE
```

Si ves esto, **¡FUNCIONA!** 🎉

---

## ❌ Errores Comunes

### Error: "Service Worker registration failed"
**Causa:** No tienes HTTPS
**Solución:** Instala certificado SSL (Paso 1)

### Error: "Failed to fetch service-worker.js"
**Causa:** Archivo no subido o servidor no reiniciado
**Solución:** Repite Pasos 2 y 3

### Error: La página se queda en blanco offline
**Causa:** Caché vacío
**Solución:**
1. CON internet, abre el sitio
2. Espera 10 segundos
3. Abre DevTools → Application → Cache Storage
4. Debe tener archivos
5. Si está vacío, limpia caché (Paso 4) y recarga

### Los cambios no se ven
**Causa:** Caché antiguo
**Solución:**
1. Abre: `https://tudominio.com/diagnostico-pwa.html`
2. Click en **"Limpiar Caché"**
3. Click en **"Desregistrar SW"**
4. Recarga la página

---

## ✅ Checklist Rápido

Antes de probar, verifica:

- [ ] El dominio usa **HTTPS** (https://)
- [ ] Certificado SSL **válido** (sin errores)
- [ ] Archivos **subidos** al VPS
- [ ] `main.py` **actualizado**
- [ ] Servidor **reiniciado**
- [ ] Caché del navegador **limpiado**
- [ ] DevTools muestra SW como **"Activated"**
- [ ] Cache Storage tiene **archivos**

---

## 🆘 Si Nada Funciona

### 1. Ejecuta verificación local
**En PowerShell (en tu PC):**
```powershell
cd c:\Users\Usuario\Documents\balanza
.\verificar-pwa.ps1
```

Esto verifica que todo esté bien **antes** de subir.

### 2. Verifica en el VPS
**Conecta por SSH y ejecuta:**
```bash
cd /ruta/a/balanza
ls -la static/service-worker.js  # Debe existir
ls -la static/manifest.json      # Debe existir
grep "service-worker.js" main.py # Debe aparecer
```

### 3. Revisa logs del servidor
```bash
# Ver errores
tail -f /var/log/nginx/error.log
# O
sudo journalctl -u balanza -f
```

---

## 📱 Instalar como App (cuando funcione)

### Android:
1. Abre `https://tudominio.com`
2. Menú (**⋮**) → **"Agregar a pantalla de inicio"**
3. ✅ Aparece ícono

### iPhone:
1. Abre `https://tudominio.com`
2. Compartir → **"Añadir a pantalla de inicio"**
3. ✅ Aparece ícono

---

## 🎯 Resultado Final

✅ Primera vez CON internet → Todo se cachea
✅ Sin internet → Web funciona 100%
✅ Recarga sin internet → No se rompe
✅ Se puede instalar como app nativa

---

## 📚 Más Información

- **Guía completa:** `SOLUCION_VPS.md`
- **Instrucciones PWA:** `INSTRUCCIONES_PWA.md`
- **Diagnóstico:** `https://tudominio.com/diagnostico-pwa.html`

---

## 📞 Soporte Rápido

Si después de seguir estos pasos sigue sin funcionar:

1. Abre: `https://tudominio.com/diagnostico-pwa.html`
2. Toma captura de pantalla
3. Abre DevTools (F12) → Console
4. Copia los mensajes de error
5. Revisa `SOLUCION_VPS.md` para soluciones avanzadas

---

**Versión:** v1.0.1
**Última actualización:** 11 de diciembre de 2025

¡Tu PWA funcionará en el VPS! 🚀
