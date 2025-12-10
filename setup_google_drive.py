"""
Script de configuración inicial para Google Drive
Ejecuta este script UNA VEZ para configurar las carpetas en Google Drive
"""

import sys
import os

# Asegurar que el directorio actual sea el del script
os.chdir(os.path.dirname(os.path.abspath(__file__)))

try:
    from google_drive_helper import init_google_drive
except ImportError:
    print("\n" + "="*60)
    print("ERROR: PyDrive2 no está instalado")
    print("="*60)
    print("\nPor favor, ejecuta primero:")
    print("  pip install PyDrive2")
    print("\nO instala todas las dependencias:")
    print("  pip install -r requirements.txt")
    print("="*60 + "\n")
    sys.exit(1)

def main():
    print("\n" + "="*60)
    print("CONFIGURACIÓN INICIAL DE GOOGLE DRIVE")
    print("="*60)
    print("\nEste script configurará:")
    print("  1. Autenticación con Google Drive")
    print("  2. Creación de carpetas principales:")
    print("     - Pesadas")
    print("     - Planilla")
    print("     - Daily_BackUp")
    print("\n" + "="*60)
    
    # Verificar que client_secrets.json existe
    if not os.path.exists("client_secrets.json"):
        print("\n❌ ERROR: Archivo 'client_secrets.json' no encontrado")
        print("\nPasos para obtenerlo:")
        print("  1. Ve a https://console.cloud.google.com")
        print("  2. Crea un proyecto (o selecciona uno existente)")
        print("  3. Habilita 'Google Drive API'")
        print("  4. Crea credenciales OAuth 2.0 (Aplicación de escritorio)")
        print("  5. Descarga el archivo JSON")
        print("  6. Renómbralo a 'client_secrets.json'")
        print("  7. Colócalo en esta carpeta: " + os.getcwd())
        print("\n" + "="*60 + "\n")
        sys.exit(1)
    
    print("\n✓ Archivo 'client_secrets.json' encontrado")
    
    # Verificar que settings.yaml existe
    if not os.path.exists("settings.yaml"):
        print("\n❌ ERROR: Archivo 'settings.yaml' no encontrado")
        print("Este archivo debería haberse creado automáticamente.")
        sys.exit(1)
    
    print("✓ Archivo 'settings.yaml' encontrado")
    
    print("\n" + "="*60)
    print("INICIANDO AUTENTICACIÓN...")
    print("="*60)
    print("\nSe abrirá tu navegador para autorizar el acceso.")
    print("Si no se abre automáticamente, copia y pega la URL que aparecerá.\n")
    
    input("Presiona ENTER para continuar...")
    
    try:
        # Inicializar Google Drive
        manager = init_google_drive()
        
        if manager is None:
            print("\n❌ ERROR: No se pudo inicializar Google Drive")
            sys.exit(1)
        
        print("\n" + "="*60)
        print("✓ CONFIGURACIÓN COMPLETADA EXITOSAMENTE")
        print("="*60)
        print("\nArchivos creados:")
        print("  ✓ credentials.json - Credenciales de autenticación")
        print("  ✓ gdrive_config.json - IDs de carpetas en Drive")
        
        print("\nIDs de carpetas configurados:")
        print(f"  📁 Pesadas:      {manager.folder_ids['pesadas']}")
        print(f"  📁 Planilla:     {manager.folder_ids['planillas']}")
        print(f"  📁 Daily_BackUp: {manager.folder_ids['backups']}")
        
        print("\n" + "="*60)
        print("PRÓXIMOS PASOS:")
        print("="*60)
        print("\n1. Para HABILITAR Google Drive en tu aplicación:")
        print("   Edita el archivo .env y cambia:")
        print("   ENABLE_GOOGLE_DRIVE=true")
        
        print("\n2. Reinicia tu aplicación FastAPI:")
        print("   python main.py")
        
        print("\n3. Los archivos se guardarán automáticamente en:")
        print("   - Carpeta local (como siempre)")
        print("   - Google Drive (respaldo automático)")
        
        print("\n" + "="*60)
        print("✓ Configuración completada")
        print("="*60 + "\n")
        
    except Exception as e:
        print("\n" + "="*60)
        print("❌ ERROR DURANTE LA CONFIGURACIÓN")
        print("="*60)
        print(f"\nError: {e}")
        print("\nSi el error es de autenticación:")
        print("  - Verifica que las credenciales sean correctas")
        print("  - Asegúrate de haber habilitado Google Drive API")
        print("  - Verifica que la aplicación esté configurada como 'Escritorio'")
        print("\n" + "="*60 + "\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
