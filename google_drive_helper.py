"""
Google Drive Helper Module
Maneja la autenticación y subida de archivos a Google Drive usando PyDrive2
"""

from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import os
import json
from datetime import datetime

class GoogleDriveManager:
    def __init__(self):
        """Inicializa el manager de Google Drive con autenticación"""
        self.gauth = GoogleAuth()
        
        # Configurar autenticación
        self.gauth.LoadCredentialsFile("credentials.json")
        
        if self.gauth.credentials is None:
            # Primera autenticación - abrirá navegador
            print("Primera autenticación con Google Drive...")
            self.gauth.LocalWebserverAuth()
        elif self.gauth.access_token_expired:
            # Renovar token si expiró
            print("Renovando token de Google Drive...")
            self.gauth.Refresh()
        else:
            # Usar credenciales existentes
            self.gauth.Authorize()
        
        # Guardar credenciales para próximas ejecuciones
        self.gauth.SaveCredentialsFile("credentials.json")
        self.drive = GoogleDrive(self.gauth)
        
        # Cargar IDs de carpetas desde configuración
        self.folder_ids = self._load_folder_ids()
    
    def _load_folder_ids(self):
        """Carga los IDs de carpetas desde gdrive_config.json si existe"""
        config_file = "gdrive_config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    print(f"✓ Configuración de Google Drive cargada desde {config_file}")
                    return config
            except Exception as e:
                print(f"⚠ Error cargando configuración de Google Drive: {e}")
        
        # Valores por defecto
        return {
            "pesadas": None,
            "planillas": None,
            "backups": None
        }
    
    def _save_folder_ids(self):
        """Guarda los IDs de carpetas en gdrive_config.json"""
        try:
            with open("gdrive_config.json", 'w', encoding='utf-8') as f:
                json.dump(self.folder_ids, f, indent=2)
            print(f"✓ Configuración guardada en gdrive_config.json")
        except Exception as e:
            print(f"⚠ Error guardando configuración de Google Drive: {e}")
    
    def get_or_create_folder(self, folder_name, parent_id=None):
        """
        Obtiene o crea una carpeta en Google Drive
        
        Args:
            folder_name: Nombre de la carpeta
            parent_id: ID de la carpeta padre (opcional)
        
        Returns:
            ID de la carpeta
        """
        # Buscar carpeta existente
        query = f"title='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        if parent_id:
            query += f" and '{parent_id}' in parents"
        
        file_list = self.drive.ListFile({'q': query}).GetList()
        
        if file_list:
            print(f"✓ Carpeta '{folder_name}' encontrada en Google Drive")
            return file_list[0]['id']
        else:
            # Crear nueva carpeta
            folder_metadata = {
                'title': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            if parent_id:
                folder_metadata['parents'] = [{'id': parent_id}]
            
            folder = self.drive.CreateFile(folder_metadata)
            folder.Upload()
            print(f"✓ Carpeta '{folder_name}' creada en Google Drive")
            return folder['id']
    
    def upload_file(self, local_path, drive_folder_id, subfolder_name=None):
        """
        Sube un archivo a Google Drive
        
        Args:
            local_path: Ruta local del archivo
            drive_folder_id: ID de la carpeta destino en Drive
            subfolder_name: Nombre de subcarpeta (opcional, ej: fecha)
        
        Returns:
            ID del archivo subido o None si falla
        """
        try:
            if not os.path.exists(local_path):
                print(f"⚠ Archivo no encontrado: {local_path}")
                return None
            
            # Crear subcarpeta si se especifica (ej: por fecha)
            target_folder_id = drive_folder_id
            if subfolder_name:
                target_folder_id = self.get_or_create_folder(subfolder_name, drive_folder_id)
            
            # Verificar si el archivo ya existe y eliminarlo (actualización)
            filename = os.path.basename(local_path)
            query = f"title='{filename}' and '{target_folder_id}' in parents and trashed=false"
            existing_files = self.drive.ListFile({'q': query}).GetList()
            
            for existing_file in existing_files:
                existing_file.Delete()
                print(f"  → Versión anterior eliminada: {filename}")
            
            # Crear y subir archivo nuevo
            file_metadata = {
                'title': filename,
                'parents': [{'id': target_folder_id}]
            }
            
            file_drive = self.drive.CreateFile(file_metadata)
            file_drive.SetContentFile(local_path)
            file_drive.Upload()
            
            print(f"✓ Archivo subido a Google Drive: {filename}")
            return file_drive['id']
        
        except Exception as e:
            print(f"✗ Error subiendo a Google Drive ({os.path.basename(local_path)}): {e}")
            return None
    
    def setup_folders(self):
        """Configura las carpetas principales en Google Drive"""
        print("\n" + "="*60)
        print("Configurando estructura de carpetas en Google Drive...")
        print("="*60)
        
        try:
            self.folder_ids["pesadas"] = self.get_or_create_folder("Pesadas")
            self.folder_ids["planillas"] = self.get_or_create_folder("Planilla")
            self.folder_ids["backups"] = self.get_or_create_folder("Daily_BackUp")
            
            self._save_folder_ids()
            
            print("\n" + "="*60)
            print("✓ Carpetas de Google Drive configuradas exitosamente")
            print("="*60)
            print(f"  📁 Pesadas:      {self.folder_ids['pesadas']}")
            print(f"  📁 Planilla:     {self.folder_ids['planillas']}")
            print(f"  📁 Daily_BackUp: {self.folder_ids['backups']}")
            print("="*60 + "\n")
            
            return True
        
        except Exception as e:
            print(f"\n✗ Error configurando carpetas: {e}")
            return False


# Instancia global
gdrive_manager = None

def init_google_drive():
    """
    Inicializa el manager de Google Drive
    
    Returns:
        GoogleDriveManager instance o None si falla
    """
    global gdrive_manager
    
    if gdrive_manager is None:
        try:
            print("\nInicializando Google Drive...")
            gdrive_manager = GoogleDriveManager()
            gdrive_manager.setup_folders()
            print("✓ Google Drive inicializado correctamente\n")
        except Exception as e:
            print(f"✗ Error inicializando Google Drive: {e}\n")
            gdrive_manager = None
    
    return gdrive_manager


def upload_to_drive(local_path, folder_type="pesadas", subfolder=None):
    """
    Helper function para subir archivos a Google Drive
    
    Args:
        local_path: Ruta del archivo local
        folder_type: Tipo de carpeta ("pesadas", "planillas", "backups")
        subfolder: Subcarpeta opcional (ej: fecha)
    
    Returns:
        True si se subió exitosamente, False en caso contrario
    """
    global gdrive_manager
    
    if gdrive_manager is None:
        print("⚠ Google Drive no está inicializado")
        return False
    
    if folder_type not in gdrive_manager.folder_ids:
        print(f"⚠ Tipo de carpeta desconocido: {folder_type}")
        return False
    
    folder_id = gdrive_manager.folder_ids[folder_type]
    if folder_id is None:
        print(f"⚠ ID de carpeta no configurado para: {folder_type}")
        return False
    
    result = gdrive_manager.upload_file(local_path, folder_id, subfolder)
    return result is not None
