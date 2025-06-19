import os
import sys
from pathlib import Path

def list_dir(path, indent=0):
    """Lista el contenido de un directorio recursivamente."""
    try:
        path = Path(path)
        print('  ' * indent + f"📁 {path.name}/")
        
        # Listar archivos primero
        files = []
        dirs = []
        
        for item in path.iterdir():
            if item.is_file():
                files.append(item)
            else:
                dirs.append(item)
        
        # Ordenar
        files.sort()
        dirs.sort()
        
        # Imprimir archivos
        for f in files:
            print('  ' * (indent + 1) + f"📄 {f.name}")
            
        # Imprimir directorios recursivamente
        for d in dirs:
            list_dir(d, indent + 1)
            
    except PermissionError as e:
        print('  ' * indent + f"🔒 Error de permiso: {e}")
    except Exception as e:
        print('  ' * indent + f"❌ Error: {e}")

if __name__ == "__main__":
    src_path = Path("src")
    if src_path.exists() and src_path.is_dir():
        print(f"Contenido de {src_path.absolute()}:")
        list_dir(src_path)
    else:
        print(f"El directorio {src_path.absolute()} no existe o no es un directorio")
