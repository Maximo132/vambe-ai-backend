import os

def check_structure():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(base_dir, 'src')
    
    required_dirs = [
        'src',
        'src/app',
        'src/app/db',
        'src/app/models'
    ]
    
    required_files = [
        'src/app/__init__.py',
        'src/app/db/__init__.py',
        'src/app/db/base.py',
        'src/app/models/__init__.py',
        'src/app/models/base.py'
    ]
    
    print("\nVerificando estructura de directorios:")
    all_ok = True
    
    for dir_path in required_dirs:
        full_path = os.path.join(base_dir, dir_path)
        if os.path.isdir(full_path):
            print(f"✓ {dir_path}/")
        else:
            print(f"✗ Falta directorio: {dir_path}")
            all_ok = False
    
    print("\nVerificando archivos:")
    for file_path in required_files:
        full_path = os.path.join(base_dir, file_path)
        if os.path.isfile(full_path):
            print(f"✓ {file_path}")
        else:
            print(f"✗ Falta archivo: {file_path}")
            all_ok = False
    
    print("\nVerificación completada:", "✓ Todo correcto" if all_ok else "✗ Hay problemas")
    return all_ok

if __name__ == "__main__":
    check_structure()
