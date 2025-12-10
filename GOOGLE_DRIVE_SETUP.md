# Integración con Google Drive - Guía de Configuración

## 📋 Resumen

Esta integración permite que tu sistema de balanza guarde automáticamente los archivos tanto en carpetas locales como en Google Drive como respaldo en la nube.

### Archivos que se sincronizan:
- **Pesadas** → PDFs de tickets de compra/venta
- **Planilla** → PDFs de planillas completas
- **Daily_BackUp** → Backups del archivo Excel

---

## 🚀 Instalación y Configuración

### Paso 1: Instalar dependencias

```powershell
pip install -r requirements.txt
```

O instalar solo PyDrive2:

```powershell
pip install PyDrive2
```

---

### Paso 2: Configurar Google Cloud Platform

1. **Ir a Google Cloud Console**
   - https://console.cloud.google.com
   - Inicia sesión con tu cuenta de Google

2. **Crear un nuevo proyecto**
   - Clic en el selector de proyectos (parte superior)
   - "NUEVO PROYECTO"
   - Nombre: `Sistema Balanza`
   - Clic en "CREAR"

3. **Habilitar Google Drive API**
   - Menú lateral: "APIs y servicios" → "Biblioteca"
   - Buscar: `Google Drive API`
   - Clic en "HABILITAR"

4. **Configurar pantalla de consentimiento OAuth**
   - Menú: "APIs y servicios" → "Pantalla de consentimiento de OAuth"
   - Seleccionar "Externo"
   - Rellenar:
     - Nombre de la aplicación: `Sistema Balanza`
     - Correo de asistencia: Tu email
     - Correos de desarrollador: Tu email
   - En "Alcances", agregar: `https://www.googleapis.com/auth/drive.file`
   - En "Usuarios de prueba", agregar tu email

5. **Crear credenciales OAuth 2.0**
   - Menú: "APIs y servicios" → "Credenciales"
   - "+ CREAR CREDENCIALES" → "ID de cliente de OAuth"
   - Tipo: "Aplicación de escritorio"
   - Nombre: `Balanza Desktop Client`
   - Clic en "CREAR"

6. **Descargar credenciales**
   - Clic en "DESCARGAR JSON"
   - Guardar el archivo
   - Renombrarlo a: `client_secrets.json`
   - Copiarlo a la carpeta del proyecto: `c:\Users\Usuario\Documents\balanza\`

---

### Paso 3: Ejecutar configuración inicial

**IMPORTANTE:** Este paso solo se hace UNA VEZ

```powershell
python setup_google_drive.py
```

Este script:
- Abrirá tu navegador para autorizar el acceso
- Creará las carpetas en Google Drive
- Generará los archivos de configuración necesarios

**Archivos que se crean:**
- `credentials.json` - Token de autenticación (no compartir)
- `gdrive_config.json` - IDs de las carpetas en Drive

---

### Paso 4: Habilitar Google Drive en la aplicación

Edita el archivo `.env`:

```env
ENABLE_GOOGLE_DRIVE=true
```

---

### Paso 5: Reiniciar la aplicación

```powershell
python main.py
```

o

```powershell
uvicorn main:app --reload
```

---

## ✅ Verificación

Al iniciar la aplicación, deberías ver estos mensajes:

```
Inicializando Google Drive...
✓ Carpeta 'Pesadas' encontrada en Google Drive
✓ Carpeta 'Planilla' encontrada en Google Drive
✓ Carpeta 'Daily_BackUp' encontrada en Google Drive
✓ Carpetas de Google Drive configuradas exitosamente
✓ Google Drive inicializado correctamente
✓ Google Drive habilitado y configurado
```

---

## 📂 Estructura de carpetas en Google Drive

```
Mi unidad/
├── Pesadas/
│   ├── 10-12-2025/
│   │   ├── compra_1.pdf
│   │   ├── venta_2.pdf
│   │   └── ...
│   └── 11-12-2025/
│       └── ...
├── Planilla/
│   ├── 10-12-2025/
│   │   └── planilla-10-12.pdf
│   └── ...
└── Daily_BackUp/
    ├── 10-12-2025/
    │   └── daily_log_backup_20251210_153045.xlsx
    └── ...
```

---

## 🔧 Funcionalidades

### Guardado automático

Cuando guardas archivos, se guardan en **DOS lugares**:

1. **Local** (carpetas en el VPS):
   - `pesadas/dd-mm-YYYY/`
   - `Planilla/dd-mm-YYYY/`
   - `Daily_BackUp/dd-mm-YYYY/`

2. **Google Drive** (respaldo en la nube):
   - Misma estructura de carpetas
   - Actualización automática (sobrescribe si existe)

### Archivos sincronizados

- ✅ PDFs de compras (`/compras/{id}/guardar`)
- ✅ PDFs de ventas (`/ventas/{id}/guardar`)
- ✅ Planillas completas (`/guardar/planilla-completa`)
- ✅ Backups de Excel (`/backup`)

---

## ⚠️ Solución de problemas

### Error: "client_secrets.json no encontrado"

**Solución:** Asegúrate de haber descargado y renombrado el archivo de credenciales correctamente.

### Error: "PyDrive2 no está instalado"

**Solución:**
```powershell
pip install PyDrive2
```

### Error de autenticación

**Solución:**
1. Elimina los archivos `credentials.json` y `gdrive_config.json`
2. Vuelve a ejecutar `python setup_google_drive.py`
3. Autoriza nuevamente en el navegador

### Google Drive no sube archivos

**Solución:**
1. Verifica que `.env` tenga `ENABLE_GOOGLE_DRIVE=true`
2. Reinicia la aplicación
3. Revisa los logs en la consola

### "Token expirado"

**Solución:** El token se renueva automáticamente. Si persiste:
1. Elimina `credentials.json`
2. Ejecuta `python setup_google_drive.py`

---

## 🔒 Seguridad

**Archivos a NO compartir:**
- `client_secrets.json` - Credenciales OAuth
- `credentials.json` - Token de acceso
- `.env` - Configuración del entorno

**Agregar al `.gitignore`:**
```
client_secrets.json
credentials.json
gdrive_config.json
.env
```

---

## 🛠️ Mantenimiento

### Deshabilitar Google Drive temporalmente

Edita `.env`:
```env
ENABLE_GOOGLE_DRIVE=false
```

Reinicia la aplicación. Los archivos solo se guardarán localmente.

### Cambiar cuenta de Google

1. Elimina `credentials.json`
2. Ejecuta `python setup_google_drive.py`
3. Autoriza con la nueva cuenta

---

## 📞 Soporte

Si encuentras problemas:

1. Revisa los mensajes en la consola
2. Verifica que todos los archivos de configuración estén presentes
3. Asegúrate de que Google Drive API esté habilitada
4. Verifica que tu cuenta esté en "Usuarios de prueba" en Google Cloud

---

## ✨ Ventajas de esta integración

- ✅ **Respaldo automático** en la nube
- ✅ **Redundancia** (local + nube)
- ✅ **Acceso desde cualquier lugar** vía Google Drive
- ✅ **Sin interrupciones** (si falla Drive, sigue guardando localmente)
- ✅ **Organización por fechas** mantenida
- ✅ **Fácil de activar/desactivar**

---

## 📝 Notas adicionales

- Los archivos se suben **después** de guardarse localmente
- Si Google Drive falla, el sistema continúa funcionando normalmente
- La subida es **asíncrona** y no bloquea la aplicación
- Los archivos duplicados se sobrescriben automáticamente en Drive

---

**Fecha de creación:** 10 de diciembre de 2025  
**Versión:** 1.0
