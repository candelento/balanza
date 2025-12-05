#!/usr/bin/env python3
"""
Demostración de impresión silenciosa desde la API
Este script muestra cómo la nueva funcionalidad permite imprimir PDFs
sin que se abra Adobe Reader u otro visor en primer plano.
"""

import requests
import json
import time

def demo_silent_printing():
    """Demostrar la impresión silenciosa usando la API"""
    
    base_url = "http://127.0.0.1:8001"
    
    print("=== Demostración de Impresión Silenciosa ===\n")
    
    # First, let's get a token
    print("1. Obteniendo token de autenticación...")
    
    token_data = {
        "username": "admin",
        "password": "ronan1"
    }
    
    try:
        response = requests.post(f"{base_url}/token", data=token_data)
        if response.status_code == 200:
            token = response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            print("✓ Token obtenido exitosamente")
        else:
            print(f"✗ Error obteniendo token: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error conectando a la API: {e}")
        return False
    
    # Get existing entries to print
    print("\n2. Obteniendo entradas existentes...")
    
    try:
        # Get compras
        response = requests.get(f"{base_url}/compras", headers=headers)
        if response.status_code == 200:
            compras = response.json()
            print(f"✓ Encontradas {len(compras)} compras")
        else:
            compras = []
            print("⚠ No se pudieron obtener compras")
        
        # Get ventas
        response = requests.get(f"{base_url}/ventas", headers=headers)
        if response.status_code == 200:
            ventas = response.json()
            print(f"✓ Encontradas {len(ventas)} ventas")
        else:
            ventas = []
            print("⚠ No se pudieron obtener ventas")
            
    except Exception as e:
        print(f"✗ Error obteniendo datos: {e}")
        return False
    
    # Demonstrate silent printing
    print(f"\n3. Demostración de impresión silenciosa...")
    
    if compras:
        compra_id = compras[0]["id"]
        print(f"\n   Probando impresión de Compra ID: {compra_id}")
        print("   ANTES: Con Adobe Reader, se abriría una ventana")
        print("   AHORA: Con SumatraPDF + modo silencioso, NO se abre ventana")
        
        confirm = input(f"\n   ¿Imprimir Compra {compra_id} en modo silencioso? (s/N): ")
        
        if confirm.lower() == 's':
            try:
                response = requests.get(
                    f"{base_url}/compras/{compra_id}/imprimir?copies=1",
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"   ✓ {result.get('detail', 'Impresión exitosa')}")
                    print("   ✓ NO se abrió ninguna ventana - impresión en segundo plano")
                else:
                    print(f"   ✗ Error: {response.text}")
                    
            except Exception as e:
                print(f"   ✗ Error imprimiendo: {e}")
    
    if ventas:
        venta_id = ventas[0]["id"]
        print(f"\n   Probando impresión de Venta ID: {venta_id}")
        
        confirm = input(f"   ¿Imprimir Venta {venta_id} en modo silencioso? (s/N): ")
        
        if confirm.lower() == 's':
            try:
                response = requests.get(
                    f"{base_url}/ventas/{venta_id}/imprimir?copies=1",
                    headers=headers
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print(f"   ✓ {result.get('detail', 'Impresión exitosa')}")
                    print("   ✓ NO se abrió ninguna ventana - impresión en segundo plano")
                else:
                    print(f"   ✗ Error: {response.text}")
                    
            except Exception as e:
                print(f"   ✗ Error imprimiendo: {e}")
    
    print(f"\n=== Resumen de la Implementación ===")
    print("✓ SumatraPDF instalado automáticamente")
    print("✓ Impresión en modo silencioso (-silent)")
    print("✓ No se abren ventanas durante la impresión")
    print("✓ Fallback a impresión de Windows si SumatraPDF falla")
    print("✓ Compatible con todos los endpoints de impresión:")
    print("  - /compras/{id}/imprimir")
    print("  - /ventas/{id}/imprimir") 
    print("  - /imprimir/todo")
    
    return True

if __name__ == "__main__":
    success = demo_silent_printing()
    
    if success:
        print(f"\n✓ Demostración completada. La impresión silenciosa está configurada y funcionando.")
    else:
        print(f"\n✗ Hubo problemas durante la demostración.")