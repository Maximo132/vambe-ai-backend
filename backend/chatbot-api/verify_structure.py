import os
import sys
from pathlib import Path

def print_directory_tree(start_path, prefix=''):
    """Imprime la estructura de directorios de forma recursiva."""
    # Obtener todos los elementos en el directorio actual
    try:
        elements = sorted(os.listdir(start_path))
    except PermissionError:
        print(f"{prefix} [Error de permiso al acceder a {start_path}]")
        return
    except FileNotFoundError:
        print(f"{prefix} [Directorio no encontrado: {start_path}]")
        return
    
    # Filtrar elementos ocultos
    elements = [e for e in elements if not e.startswith('.')]
    
    for i, element in enumerate(elements):
        path = Path(start_path) / element
        is_last = (i == len(elements) - 1)
        
        # Determinar el prefijo para el elemento actual
        if is_last:
            print(f"{prefix}└── {element}")
            new_prefix = f"{prefix}    "
        else:
            print(f"{prefix}├── {element}")
            new_prefix = f"{prefix}│   "
        
        # Si es un directorio, mostrarlo recursivamente
        if path.is_dir():
            print_directory_tree(path, new_prefix)

def check_imports():
    """Verifica las importaciones clave."""
    print("\nVerificando importaciones...")
    
    # Añadir src al path
    src_path = str(Path(__file__).parent.absolute() / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    try:
        print("Intentando importar app.db.base...")
        from app.db import base
        print("✓ app.db.base importado correctamente")
        print(f"  - Base: {base.Base}")
        print(f"  - database: {base.database}")
    except ImportError as e:
        print(f"✗ Error al importar app.db.base: {e}")
        print("Python path:")
        for p in sys.path:
            print(f"  - {p}")
        return False
    
    return True

def main():
    print("Estructura del proyecto:")
    print_directory_tree(".")
    
    print("\nVerificando archivos importantes:")
    required_files = [
        "src/app/__init__.py",
        "src/app/db/__init__.py",
        "src/app/db/base.py",
        "src/app/models/__init__.py",
        "src/app/models/base.py",
        "alembic.ini",
        "migrations/env.py"
    ]
    
    all_ok = True
    for file in required_files:
        exists = os.path.exists(file)
        status = "✓" if exists else "✗"
        print(f"{status} {file}")
        if not exists:
            all_ok = False
    
    if all_ok:
        print("\n✓ Todos los archivos requeridos existen")
    else:
        print("\n✗ Faltan algunos archivos requeridos")
    
    print("\nVerificando importaciones de Python...")
    imports_ok = check_imports()
    
    if all_ok and imports_ok:
        print("\n✅ La estructura del proyecto es correcta")
    else:
        print("\n❌ Hay problemas con la estructura del proyecto")
        sys.exit(1)

if __name__ == "__main__":
    main()
