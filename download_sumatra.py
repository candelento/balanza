#!/usr/bin/env python3
"""
Script para descargar SumatraPDF manualmente
"""

import os
import urllib.request
import zipfile

def download_sumatrapdf():
    """Descargar SumatraPDF portable"""
    sumatra_dir = os.path.join(os.getcwd(), "SumatraPDF")
    sumatra_exe = os.path.join(sumatra_dir, "SumatraPDF.exe")
    
    print(f"Directorio objetivo: {sumatra_dir}")
    
    # Remove download marker to try again
    download_marker = os.path.join(sumatra_dir, ".download_attempted")
    if os.path.exists(download_marker):
        os.remove(download_marker)
        print("Removido marcador de descarga anterior")
    
    # Check if already exists
    if os.path.exists(sumatra_exe):
        print(f"✓ SumatraPDF ya existe en: {sumatra_exe}")
        return sumatra_exe
    
    try:
        print("Creando directorio...")
        os.makedirs(sumatra_dir, exist_ok=True)
        
        # URL for SumatraPDF portable - using a more reliable source
        # Try different versions/sources
        urls = [
            "https://www.sumatrapdfreader.org/dl/rel/3.5.2/SumatraPDF-3.5.2-64.zip",
            "https://github.com/sumatrapdfreader/sumatrapdf/releases/download/3.5.2rel/SumatraPDF-3.5.2-64.zip"
        ]
        
        zip_path = os.path.join(sumatra_dir, "sumatra.zip")
        downloaded = False
        
        for url in urls:
            try:
                print(f"Intentando descargar desde: {url}")
                urllib.request.urlretrieve(url, zip_path)
                if os.path.exists(zip_path) and os.path.getsize(zip_path) > 1000:  # At least 1KB
                    downloaded = True
                    print(f"✓ Descarga exitosa, tamaño: {os.path.getsize(zip_path)} bytes")
                    break
                else:
                    print(f"✗ Archivo descargado vacío o muy pequeño")
            except Exception as e:
                print(f"✗ Error con URL {url}: {e}")
                continue
        
        if not downloaded:
            print("✗ No se pudo descargar desde ninguna URL")
            return None
        
        print("Extrayendo archivo...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # List contents first
            print("Contenido del ZIP:")
            for file_info in zip_ref.infolist():
                print(f"  - {file_info.filename}")
            
            # Find and extract SumatraPDF executable (could have different names)
            for file_info in zip_ref.infolist():
                if ('SumatraPDF' in file_info.filename and 
                    file_info.filename.endswith('.exe')):
                    print(f"Extrayendo: {file_info.filename}")
                    # Extract to target directory
                    extracted_path = zip_ref.extract(file_info, sumatra_dir)
                    # Rename to standard name
                    final_path = os.path.join(sumatra_dir, 'SumatraPDF.exe')
                    if extracted_path != final_path:
                        if os.path.exists(final_path):
                            os.remove(final_path)
                        os.rename(extracted_path, final_path)
                        print(f"Renombrado a: {final_path}")
                    break
        
        # Clean up zip file
        if os.path.exists(zip_path):
            os.remove(zip_path)
            print("Archivo ZIP temporal removido")
        
        if os.path.exists(sumatra_exe):
            print(f"✓ SumatraPDF instalado exitosamente en: {sumatra_exe}")
            return sumatra_exe
        else:
            print("✗ No se pudo extraer SumatraPDF.exe del archivo ZIP")
            return None
            
    except Exception as e:
        print(f"✗ Error durante la descarga: {e}")
        return None

if __name__ == "__main__":
    result = download_sumatrapdf()
    if result:
        print("\n¡Descarga completada!")
        print("Ahora puedes usar impresión silenciosa con SumatraPDF")
    else:
        print("\nDescarga falló. Se usará impresión por defecto de Windows")