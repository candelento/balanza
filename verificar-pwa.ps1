#!/usr/bin/env pwsh
# Script de verificación PWA para Sistema de Pesaje
# Ejecutar en PowerShell: .\verificar-pwa.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "🔍 VERIFICACIÓN PWA - Sistema de Pesaje" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$errores = 0
$advertencias = 0

# Función para verificar archivo
function Verificar-Archivo {
    param(
        [string]$ruta,
        [string]$nombre
    )
    
    if (Test-Path $ruta) {
        Write-Host "✅ $nombre existe" -ForegroundColor Green
        return $true
    } else {
        Write-Host "❌ $nombre NO existe" -ForegroundColor Red
        $script:errores++
        return $false
    }
}

# Función para buscar texto en archivo
function Buscar-EnArchivo {
    param(
        [string]$ruta,
        [string]$texto,
        [string]$descripcion
    )
    
    if (Test-Path $ruta) {
        $contenido = Get-Content $ruta -Raw
        if ($contenido -match [regex]::Escape($texto)) {
            Write-Host "   ✓ $descripcion" -ForegroundColor Gray
            return $true
        } else {
            Write-Host "   ⚠ $descripcion NO encontrado" -ForegroundColor Yellow
            $script:advertencias++
            return $false
        }
    }
    return $false
}

Write-Host "📁 Verificando archivos estáticos..." -ForegroundColor Yellow
Write-Host ""

# Verificar archivos principales
$archivos = @(
    @{ruta="static\index.html"; nombre="index.html"},
    @{ruta="static\service-worker.js"; nombre="service-worker.js"},
    @{ruta="static\manifest.json"; nombre="manifest.json"},
    @{ruta="static\styles.css"; nombre="styles.css"},
    @{ruta="static\script.js"; nombre="script.js"},
    @{ruta="static\config.js"; nombre="config.js"},
    @{ruta="static\logo.png"; nombre="logo.png"},
    @{ruta="static\diagnostico-pwa.html"; nombre="diagnostico-pwa.html"},
    @{ruta="main.py"; nombre="main.py"}
)

foreach ($archivo in $archivos) {
    Verificar-Archivo -ruta $archivo.ruta -nombre $archivo.nombre | Out-Null
}

Write-Host ""
Write-Host "🔧 Verificando configuración..." -ForegroundColor Yellow
Write-Host ""

# Verificar service-worker.js
if (Test-Path "static\service-worker.js") {
    Write-Host "📄 service-worker.js:" -ForegroundColor Cyan
    Buscar-EnArchivo -ruta "static\service-worker.js" -texto "CACHE_VERSION" -descripcion "Versión de caché configurada"
    Buscar-EnArchivo -ruta "static\service-worker.js" -texto "BASE_URL" -descripcion "BASE_URL dinámica"
    Buscar-EnArchivo -ruta "static\service-worker.js" -texto "/index.html" -descripcion "index.html en lista de caché"
    Buscar-EnArchivo -ruta "static\service-worker.js" -texto "/api/" -descripcion "Ignora rutas /api/"
    
    # Obtener versión
    $contenido = Get-Content "static\service-worker.js" -Raw
    if ($contenido -match "CACHE_VERSION\s*=\s*'([^']+)'") {
        Write-Host "   ℹ Versión actual: $($matches[1])" -ForegroundColor Cyan
    }
}

Write-Host ""

# Verificar index.html
if (Test-Path "static\index.html") {
    Write-Host "📄 index.html:" -ForegroundColor Cyan
    Buscar-EnArchivo -ruta "static\index.html" -texto "manifest.json" -descripcion "Manifest vinculado"
    Buscar-EnArchivo -ruta "static\index.html" -texto "serviceWorker.register" -descripcion "Service Worker registrado"
    Buscar-EnArchivo -ruta "static\index.html" -texto "service-worker.js" -descripcion "Ruta correcta del SW"
}

Write-Host ""

# Verificar main.py
if (Test-Path "main.py") {
    Write-Host "📄 main.py:" -ForegroundColor Cyan
    Buscar-EnArchivo -ruta "main.py" -texto "@app.get(`"/service-worker.js`")" -descripcion "Ruta /service-worker.js"
    Buscar-EnArchivo -ruta "main.py" -texto "@app.get(`"/manifest.json`")" -descripcion "Ruta /manifest.json"
    Buscar-EnArchivo -ruta "main.py" -texto "Service-Worker-Allowed" -descripcion "Header Service-Worker-Allowed"
}

Write-Host ""

# Verificar manifest.json
if (Test-Path "static\manifest.json") {
    Write-Host "📄 manifest.json:" -ForegroundColor Cyan
    try {
        $manifest = Get-Content "static\manifest.json" -Raw | ConvertFrom-Json
        Write-Host "   ✓ Nombre: $($manifest.name)" -ForegroundColor Gray
        Write-Host "   ✓ URL de inicio: $($manifest.start_url)" -ForegroundColor Gray
        Write-Host "   ✓ Display: $($manifest.display)" -ForegroundColor Gray
    } catch {
        Write-Host "   ⚠ Error al leer manifest.json" -ForegroundColor Yellow
        $advertencias++
    }
}

Write-Host ""
Write-Host "🌐 Verificando configuración de red..." -ForegroundColor Yellow
Write-Host ""

# Verificar si el servidor está corriendo localmente
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✅ Servidor local respondiendo en http://localhost:8001" -ForegroundColor Green
    
    # Verificar que devuelve HTML
    if ($response.Content -match "<!DOCTYPE html>") {
        Write-Host "   ✓ Responde con HTML válido" -ForegroundColor Gray
    }
} catch {
    Write-Host "⚠ Servidor local NO está corriendo" -ForegroundColor Yellow
    Write-Host "   Ejecuta: python main.py" -ForegroundColor Gray
    $advertencias++
}

# Verificar service-worker.js accesible
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/service-worker.js" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✅ service-worker.js accesible en /service-worker.js" -ForegroundColor Green
    
    # Verificar Content-Type
    $contentType = $response.Headers['Content-Type']
    if ($contentType -match "javascript") {
        Write-Host "   ✓ Content-Type correcto: $contentType" -ForegroundColor Gray
    } else {
        Write-Host "   ⚠ Content-Type puede ser incorrecto: $contentType" -ForegroundColor Yellow
        $advertencias++
    }
} catch {
    if ($_.Exception.Message -notmatch "No se puede conectar") {
        Write-Host "⚠ service-worker.js NO accesible" -ForegroundColor Yellow
        $advertencias++
    }
}

# Verificar manifest.json accesible
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8001/manifest.json" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✅ manifest.json accesible en /manifest.json" -ForegroundColor Green
} catch {
    if ($_.Exception.Message -notmatch "No se puede conectar") {
        Write-Host "⚠ manifest.json NO accesible" -ForegroundColor Yellow
        $advertencias++
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "📊 RESUMEN" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($errores -eq 0 -and $advertencias -eq 0) {
    Write-Host "✅ TODO PERFECTO - Listo para subir al VPS" -ForegroundColor Green
    Write-Host ""
    Write-Host "📤 Próximos pasos:" -ForegroundColor Yellow
    Write-Host "   1. Sube los archivos al VPS" -ForegroundColor Gray
    Write-Host "   2. Reinicia el servidor FastAPI" -ForegroundColor Gray
    Write-Host "   3. Abre https://tudominio.com/diagnostico-pwa.html" -ForegroundColor Gray
    Write-Host "   4. Verifica que el Service Worker esté activo" -ForegroundColor Gray
} elseif ($errores -eq 0) {
    Write-Host "⚠ $advertencias advertencia(s) encontrada(s)" -ForegroundColor Yellow
    Write-Host "   Puedes continuar pero revisa las advertencias" -ForegroundColor Gray
} else {
    Write-Host "❌ $errores error(es) encontrado(s)" -ForegroundColor Red
    Write-Host "   Corrige los errores antes de subir al VPS" -ForegroundColor Gray
}

Write-Host ""
Write-Host "📖 Lee SOLUCION_VPS.md para más información" -ForegroundColor Cyan
Write-Host ""

# Pausa para que el usuario pueda leer
if ($errores -gt 0 -or $advertencias -gt 0) {
    Write-Host "Presiona cualquier tecla para salir..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
