Sistema de Balanza – Guía de uso y operación

Este documento explica cómo usar la plataforma “Sistema de Balanza” (compras/ventas), usuarios y contraseñas, roles y permisos, flujos de trabajo, generación/impresión de tickets y planillas, atajos de teclado, dashboard y backups.

URL por defecto: http://localhost:8001

Tabla de contenidos
- Acceso: usuarios y contraseñas
- Roles y permisos
- Interfaz y flujo de trabajo
	- Compras y Ventas: crear/editar/guardar/eliminar
	- Impresión y guardado de tickets
	- Planillas: imprimir, ver, guardar y descargar
	- Filtros y búsqueda por fecha/texto
	- Dashboard
	- Catálogo de productos
- Atajos de teclado y controles útiles
- Backups diarios
- Estructura de archivos generados
- Errores comunes y soluciones
- Puesta en marcha (para administradores/técnicos)


Acceso: usuarios y contraseñas
- Usuario: admin  | Contraseña: ronan1 | Rol: admin
- Usuario: admin2 | Contraseña: ronan2 | Rol: lect
- Usuario: admin3 | Contraseña: ronan3 | Rol: lect
- Usuario: admin4 | Contraseña: ronan4 | Rol: lect

Notas importantes
- Estas credenciales son de ejemplo para uso local. Cambiarlas en producción.
- El sistema usa inicio de sesión con token (JWT) y la sesión caduca a los 30 minutos.


Roles y permisos
- admin
	- Ver, filtrar y buscar compras/ventas
	- Crear, editar y eliminar registros
	- Imprimir/guardar tickets por registro
	- Imprimir/ver/guardar/descargar planillas
	- Ejecutar backups del Excel diario
- lect (lectura)
	- Ver, filtrar y buscar compras/ventas
	- Imprimir/guardar tickets por registro
	- Imprimir/ver/guardar/descargar planillas
	- No puede crear/editar/eliminar registros


Interfaz y flujo de trabajo

Login
- En la pantalla inicial ingrese usuario y contraseña. La validación es en tiempo real y puede auto-enviar cuando coincide.
- Tras ingresar, verá pestañas: Compras, Ventas y Dashboard.

Compras y Ventas
1) Nueva fila
	 - Botón “Nueva Compra” o “Nueva Venta”. Aparece una fila editable al inicio de la tabla.
	 - Campos típicos: Proveedor/Cliente, Mercadería (con lista desplegable), Bruto, Tara, Merma, Chofer/Transporte, Patente y Observaciones.
2) Guardar
	 - Guardado explícito: botón de disquete en la fila o tecla F8 (ver atajos). Recomendado para cargas de Bruto/Tara.
	 - Guardado automático: al salir de campos no críticos (p. ej. texto/observaciones) se intenta un autosave con retardo breve.
	 - Reglas:
		 - El sistema calcula Neto = Bruto − Tara − Merma y Importe = Neto × Precio/kg (si se carga precio).
		 - Hora de Ingreso se fija al cargar Bruto por primera vez; Hora de Salida al cargar Tara por primera vez.
3) Editar
	 - Modificar los campos y presionar Guardar (o F8). Para Bruto/Tara use guardado explícito.
4) Eliminar
	 - Papelera en la fila. Requiere rol admin.

Permisos efectivos por acción
- Ver/filtrar/buscar: admin, lect
- Crear/editar/eliminar: solo admin
- Imprimir/guardar tickets: admin, lect
- Imprimir/ver/guardar/descargar planillas: admin, lect
- Backup: admin, lect


Impresión y guardado de tickets (por fila)
- En cada fila hay botones “Imprimir” y “Guardar”. Seleccione la cantidad de copias (1–3) junto al botón.
- Imprimir envía el PDF a la impresora del sistema (Windows). Guardar crea el PDF en disco.
- Requiere que la fila esté guardada (con ID asignado).


Planillas (general y filtradas)
- Botones superiores:
	- “Imprimir Planilla”: imprime un PDF con compras y ventas del día visible.
	- “Ver Plantilla”: abre en el navegador el PDF combinado.
	- “Guardar Planilla”: genera y guarda la planilla combinada en el servidor.
- Botones “Descarga” en filtros de Compras/Ventas: descarga planilla filtrada por pestaña o combinada (según el botón “Descarga” de cada pestaña).
- Las planillas incluyen totales de Kgs netos por sección y un “Balance Neto” general (Compras − Ventas).


Filtros y búsqueda
- Cada pestaña tiene búsqueda por texto (Proveedor/Cliente, Mercadería, Chofer/Transporte, Patente) y filtro por Fecha (YYYY-MM-DD).
- Use “Filtrar” o “Limpiar” para actualizar.


Dashboard
- Seleccione rango de fechas (Inicio/Fin) o use presets: Hoy, Ayer, Últimos 7 días, Este mes, Mes pasado.
- Muestra:
	- Entradas y salidas (kgs netos)
	- Balance últimos 5 días
	- Ingresos por tipo de material (Compras)


Catálogo de productos
- El desplegable de Mercadería toma valores de `config.json`:
	- productos_compra: opciones para Compras
	- productos_venta: opciones para Ventas
- Edite `config.json` para adaptar los listados.


Atajos de teclado y controles útiles
- F8: Guardar la fila activa o la última fila con foco (recomendado tras cargar Bruto/Tara).
- Enter: no guarda (evita envíos accidentales). Use F8 o el botón Guardar.
- Flechas de desplazamiento: botones flotantes izquierda/derecha para navegar horizontalmente la tabla.
- Interruptor de tema: botón luna/sol en el encabezado para modo claro/oscuro.


Backups diarios
- Botón “Realizar Backup” (admin y lect) crea una copia de `daily_log.xlsx` en `Daily_BackUp/<dd-mm-YYYY>/daily_log_backup_<timestamp>.xlsx`.


Estructura de archivos generados
- Excel diario: `daily_log.xlsx` (con una hoja por fecha YYYY-MM-DD).
- Tickets guardados por fila: `pesadas/<dd-mm-YYYY>/compra_<ID>.pdf` o `pesadas/<dd-mm-YYYY>/venta_<ID>.pdf`.
- Planillas combinadas guardadas: `Planilla/planilla-<dd>-<mm>.pdf`.


Errores comunes y soluciones
- “Permiso denegado” al guardar en Excel: cierre `daily_log.xlsx` si está abierto en Excel u otro programa y vuelva a intentar.
- Impresión falla: requiere Windows con impresora/PDF handler instalado. Si el visor predeterminado no admite impresión silenciosa, guarde el PDF y imprímalo manualmente.
- No veo datos: verifique que inició sesión y que el token no haya expirado (sesión ~30 min).


Puesta en marcha (administradores/técnicos)

Requisitos
- Windows recomendado para impresión; Python 3.11+ (probado hasta 3.13).

Instalación en Windows PowerShell
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Ejecutar el servidor
```powershell
python main.py
```
Abrir navegador en: http://localhost:8001

Tests (opcional)
```powershell
pytest -q
```

Seguridad y configuración
- Cambiar SECRET_KEY en `main.py` y las contraseñas por valores seguros.
- Actualizar `config.json` para los listados de productos.


Glosario de campos
- Proveedor/Cliente: contraparte de la operación.
- Mercadería: material (lista editable según `config.json`).
- Bruto/Tara/Merma: pesos en kg. Neto se calcula automáticamente.
- Chofer (Compras) / Transporte (Ventas): dato logístico.
- Patente: matrícula del vehículo.
- Hora Ingreso/Salida: se setean automáticamente al cargar Bruto/Tara por primera vez.
- Observaciones: texto libre.


Soporte
Si necesita asistencia, documente qué hacía, el mensaje de error, y adjunte `api.log` (bitácora del servidor) para diagnóstico.
