"""
Script de prueba rápida para verificar la configuración de Google Drive
"""

import os
import sys

def verificar_archivos():
    """Verifica que todos los archivos necesarios estén presentes"""
    archivos_requeridos = {
        "google_drive_helper.py": "Módulo de Google Drive",
        "settings.yaml": "Configuración de PyDrive2",
        ".env": "Variables de entorno",
        "setup_google_drive.py": "Script de configuración",
        "requirements.txt": "Dependencias Python"
    }
    
    archivos_opcionales = {
        "client_secrets.json": "Credenciales OAuth (necesario para usar Google Drive)",
        "credentials.json": "Token de autenticación (se crea al ejecutar setup)",
        "gdrive_config.json": "IDs de carpetas (se crea al ejecutar setup)"
    }
    
    print("\n" + "="*60)
    print("VERIFICACIÓN DE INSTALACIÓN - GOOGLE DRIVE")
    print("="*60 + "\n")
    
    print("Archivos requeridos:")
    todos_ok = True
    for archivo, descripcion in archivos_requeridos.items():
        existe = os.path.exists(archivo)
        estado = "✓" if existe else "✗"
        print(f"  {estado} {archivo:30s} - {descripcion}")
        if not existe:
            todos_ok = False
    
    print("\nArchivos opcionales:")
    for archivo, descripcion in archivos_opcionales.items():
        existe = os.path.exists(archivo)
        estado = "✓" if existe else "⚠"
        print(f"  {estado} {archivo:30s} - {descripcion}")
    
    print("\n" + "="*60)
    
    if not todos_ok:
        print("❌ ERROR: Faltan archivos requeridos")
        return False
    
    return True

def verificar_dependencias():
    """Verifica que PyDrive2 esté instalado"""
    print("\nVerificando dependencias Python:")
    
    try:
        import pydrive2
        print("  ✓ PyDrive2 instalado correctamente")
        return True
    except ImportError:
        print("  ✗ PyDrive2 NO está instalado")
        print("\n    Instalar con: pip install PyDrive2")
        return False

def verificar_configuracion():
    """Verifica la configuración en .env"""
    print("\nVerificando configuración:")
    
    if not os.path.exists(".env"):
        print("  ⚠ Archivo .env no encontrado")
        return False
    
    with open(".env", "r") as f:
        contenido = f.read()
    
    if "ENABLE_GOOGLE_DRIVE=true" in contenido:
        print("  ✓ Google Drive HABILITADO en .env")
    else:
        print("  ⚠ Google Drive DESHABILITADO en .env")
        print("    Para habilitar, edita .env y cambia: ENABLE_GOOGLE_DRIVE=true")
    
    return True

def main():
    """Ejecuta todas las verificaciones"""
    
    # Verificar archivos
    if not verificar_archivos():
        print("\n❌ Instalación incompleta")
        sys.exit(1)
    
    # Verificar dependencias
    if not verificar_dependencias():
        print("\n❌ Faltan dependencias")
        sys.exit(1)
    
    # Verificar configuración
    verificar_configuracion()
    
    # Verificar si está listo para usar
    print("\n" + "="*60)
    print("ESTADO DE LA INSTALACIÓN")
    print("="*60)
    
    tiene_credenciales = os.path.exists("client_secrets.json")
    esta_configurado = os.path.exists("credentials.json") and os.path.exists("gdrive_config.json")
    
    if tiene_credenciales and esta_configurado:
        print("\n✅ Google Drive está COMPLETAMENTE CONFIGURADO")
        print("\nPuedes:")
        print("  1. Editar .env y cambiar ENABLE_GOOGLE_DRIVE=true")
        print("  2. Reiniciar tu aplicación: python main.py")
        print("\n¡Los archivos se guardarán automáticamente en Google Drive!")
    
    elif tiene_credenciales and not esta_configurado:
        print("\n⚠ Credenciales encontradas, pero falta configuración")
        print("\nSiguiente paso:")
        print("  Ejecuta: python setup_google_drive.py")
    
    else:
        print("\n⏳ Instalación completada, pero falta configuración")
        print("\nPróximos pasos:")
        print("\n1. Obtén las credenciales OAuth:")
        print("   - Ve a https://console.cloud.google.com")
        print("   - Sigue las instrucciones en GOOGLE_DRIVE_SETUP.md")
        print("   - Descarga client_secrets.json")
        print("\n2. Ejecuta la configuración:")
        print("   python setup_google_drive.py")
        print("\n3. Habilita Google Drive:")
        print("   Edita .env → ENABLE_GOOGLE_DRIVE=true")
    
    print("\n" + "="*60)
    print("Para más información, consulta: GOOGLE_DRIVE_SETUP.md")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
