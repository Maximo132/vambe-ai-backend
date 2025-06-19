import sys
import os

# Añadir el directorio src al path
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

print("Python Path:")
for p in sys.path:
    print(f"- {p}")

try:
    print("\nIntentando importar app.db.base...")
    from app.db import base
    print("✓ app.db.base importado correctamente")
    print(f"Base: {base.Base}")
    print(f"database: {base.database}")
except Exception as e:
    print(f"Error al importar app.db.base: {e}")

try:
    print("\nIntentando importar modelos...")
    from app.models import *
    print("✓ Modelos importados correctamente")
    print(f"Modelos disponibles: {[m for m in dir() if not m.startswith('__')]}")
except Exception as e:
    print(f"Error al importar modelos: {e}")
