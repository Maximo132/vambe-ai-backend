"""
Script para probar los endpoints de perfil de usuario.

Este script realiza pruebas contra la API para verificar el funcionamiento
correcto de los endpoints de gestión de perfiles.
"""
import os
import sys
import asyncio
import httpx
import json
from typing import Dict, Any, Optional
from pathlib import Path

# Añadir el directorio raíz al path para poder importar los módulos
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings

# Configuración
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"
AUTH_URL = f"{BASE_URL}{API_PREFIX}/auth"
PROFILE_URL = f"{BASE_URL}{API_PREFIX}/profile"

# Credenciales de prueba
TEST_USERNAME = "testuser"
TEST_EMAIL = "testuser@example.com"
TEST_PASSWORD = "testpassword123"

# Cliente HTTP asíncrono
client = httpx.AsyncClient()

async def get_auth_token() -> Optional[str]:
    """Obtiene un token de autenticación."""
    try:
        # Primero intentamos iniciar sesión
        login_data = {
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD
        }
        
        response = await client.post(
            f"{AUTH_URL}/login",
            json=login_data
        )
        
        if response.status_code == 200:
            return response.json().get("access_token")
            
        # Si el usuario no existe, intentamos registrarlo
        register_data = {
            "username": TEST_USERNAME,
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
            "full_name": "Usuario de Prueba"
        }
        
        response = await client.post(
            f"{AUTH_URL}/register",
            json=register_data
        )
        
        if response.status_code == 200:
            # Iniciar sesión después del registro
            response = await client.post(
                f"{AUTH_URL}/login",
                json=login_data
            )
            if response.status_code == 200:
                return response.json().get("access_token")
                
        print(f"Error al autenticar: {response.text}")
        return None
        
    except Exception as e:
        print(f"Error en get_auth_token: {str(e)}")
        return None

async def test_get_profile(token: str) -> None:
    """Prueba el endpoint para obtener el perfil del usuario."""
    print("\n=== Probando GET /profile/me ===")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get(
            f"{PROFILE_URL}/me",
            headers=headers
        )
        
        print(f"Status: {response.status_code}")
        print("Respuesta:", response.json())
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error en test_get_profile: {str(e)}")
        return False

async def test_update_profile(token: str) -> None:
    """Prueba el endpoint para actualizar el perfil del usuario."""
    print("\n=== Probando PUT /profile/me ===")
    try:
        update_data = {
            "full_name": "Usuario de Prueba Actualizado",
            "bio": "Biografía de prueba actualizada",
            "phone": "+1234567890"
        }
        
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.put(
            f"{PROFILE_URL}/me",
            json=update_data,
            headers=headers
        )
        
        print(f"Status: {response.status_code}")
        print("Respuesta:", response.json())
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error en test_update_profile: {str(e)}")
        return False

async def test_change_password(token: str) -> None:
    """Prueba el endpoint para cambiar la contraseña."""
    print("\n=== Probando POST /profile/me/change-password ===")
    try:
        password_data = {
            "current_password": TEST_PASSWORD,
            "new_password": "nuevacontraseña123",
            "confirm_password": "nuevacontraseña123"
        }
        
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.post(
            f"{PROFILE_URL}/me/change-password",
            json=password_data,
            headers=headers
        )
        
        print(f"Status: {response.status_code}")
        print("Respuesta:", response.json())
        
        # Cambiar de vuelta la contraseña para otras pruebas
        if response.status_code == 200:
            password_data = {
                "current_password": "nuevacontraseña123",
                "new_password": TEST_PASSWORD,
                "confirm_password": TEST_PASSWORD
            }
            response = await client.post(
                f"{PROFILE_URL}/me/change-password",
                json=password_data,
                headers=headers
            )
            print("\nRestaurando contraseña original...")
            print(f"Status: {response.status_code}")
            
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error en test_change_password: {str(e)}")
        return False

async def test_upload_avatar(token: str) -> None:
    """Prueba el endpoint para subir un avatar."""
    print("\n=== Probando POST /profile/me/avatar ===")
    try:
        # Crear un archivo de prueba en memoria
        from io import BytesIO
        from PIL import Image, ImageDraw
        
        # Crear una imagen simple en memoria
        img = Image.new('RGB', (200, 200), color='blue')
        d = ImageDraw.Draw(img)
        d.text((10, 10), "Avatar de Prueba", fill='white')
        
        # Guardar la imagen en un buffer
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        # Crear el archivo para la solicitud
        files = {"file": ("test_avatar.png", buffer, "image/png")}
        
        headers = {
            "Authorization": f"Bearer {token}",
        }
        
        # Usar httpx.AsyncClient para manejar la carga de archivos
        data = {}
        response = await client.post(
            f"{PROFILE_URL}/me/avatar",
            files=files,
            data=data,
            headers=headers
        )
        
        print(f"Status: {response.status_code}")
        print("Respuesta:", response.json())
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error en test_upload_avatar: {str(e)}")
        return False

async def test_notification_settings(token: str) -> None:
    """Prueba los endpoints de configuración de notificaciones."""
    print("\n=== Probando GET /profile/me/notifications ===")
    try:
        # Obtener configuración actual
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get(
            f"{PROFILE_URL}/me/notifications",
            headers=headers
        )
        
        print("Configuración actual:", response.json())
        
        # Actualizar configuración
        update_data = {
            "email_notifications": True,
            "push_notifications": False,
            "message_notifications": True,
            "mention_notifications": False,
            "newsletter": True
        }
        
        print("\nActualizando configuración...")
        response = await client.put(
            f"{PROFILE_URL}/me/notifications",
            json=update_data,
            headers=headers
        )
        
        print(f"Status: {response.status_code}")
        print("Respuesta:", response.json())
        return response.status_code == 200
        
    except Exception as e:
        print(f"Error en test_notification_settings: {str(e)}")
        return False

async def main():
    """Función principal para ejecutar las pruebas."""
    print("=== Iniciando pruebas de perfil de usuario ===")
    
    # Obtener token de autenticación
    print("\nObteniendo token de autenticación...")
    token = await get_auth_token()
    
    if not token:
        print("Error: No se pudo obtener el token de autenticación")
        return
    
    print("\nToken obtenido con éxito")
    
    # Ejecutar pruebas
    tests = [
        ("Obtener perfil", test_get_profile),
        ("Actualizar perfil", test_update_profile),
        ("Cambiar contraseña", test_change_password),
        ("Subir avatar", test_upload_avatar),
        ("Configuración de notificaciones", test_notification_settings)
    ]
    
    results = {}
    for name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Ejecutando prueba: {name}")
        print(f"{'='*50}")
        success = await test_func(token)
        results[name] = "✅ Éxito" if success else "❌ Fallo"
    
    # Mostrar resumen
    print("\n" + "="*50)
    print("RESUMEN DE PRUEBAS")
    print("="*50)
    for name, result in results.items():
        print(f"{name}: {result}")
    
    # Cerrar el cliente HTTP
    await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())
