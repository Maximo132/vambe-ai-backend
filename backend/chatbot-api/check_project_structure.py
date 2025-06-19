import os
import sys
from pathlib import Path

def print_tree(directory, prefix=""):
    """Imprime la estructura de directorios de forma recursiva."""
    contents = list(Path(directory).iterdir())
    pointers = ["├──"] * (len(contents) - 1) + ["└──"]
    for pointer, path in zip(pointers, contents):
        print(prefix + pointer + " " + path.name)
        if path.is_dir():
            extension = "    " if pointer == "└──" else "│   "
            print_tree(path, prefix=prefix + extension)

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
    except ImportError as e:
        print(f"✗ Error al importar app.db.base: {e}")
        print("Python path:", sys.path)
        raise

def main():
    print("Estructura del proyecto:")
    print_tree(".")
    check_imports()

if __name__ == "__main__":
    main()
