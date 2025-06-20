"""
Script para crear el directorio de subidas si no existe.
"""
import os
from pathlib import Path
from app.core.config import settings

def create_upload_dir():
    """Crea el directorio de subidas si no existe."""
    try:
        # Crear el directorio de subidas si no existe
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Asegurar que el directorio tenga los permisos correctos
        os.chmod(upload_dir, 0o755)
        
        print(f"Directorio de subidas creado en: {upload_dir}")
        return str(upload_dir)
    except Exception as e:
        print(f"Error al crear el directorio de subidas: {e}")
        return None

if __name__ == "__main__":
    create_upload_dir()
