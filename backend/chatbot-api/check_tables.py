#!/usr/bin/env python
"""
Script para verificar las tablas en la base de datos.
"""
import os
import sys
import logging
from pathlib import Path
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    # Añadir el directorio src al path
    src_dir = str(Path(__file__).parent.absolute() / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    
    # Configurar la URL de la base de datos
    os.environ["DATABASE_URL"] = "postgresql+psycopg2://chatbot_user:chatbot_password@localhost:5432/chatbot_db"
    
    try:
        # Importar SQLAlchemy
        from sqlalchemy import create_engine, inspect
        
        # Crear motor de base de datos
        db_url = os.environ["DATABASE_URL"]
        logger.info(f"Conectando a la base de datos: {db_url}")
        
        engine = create_engine(db_url)
        
        # Probar la conexión
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info(f"Conexión exitosa a la base de datos: {result.scalar() == 1}")
        
        # Obtener inspector
        inspector = inspect(engine)
        logger.info("Inspector de base de datos creado correctamente")
        
        # Obtener nombres de tablas
        tables = inspector.get_table_names()
        
        print("\n" + "=" * 80)
        print(f"ANÁLISIS DE LA BASE DE DATOS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        
        if tables:
            print(f"\nSe encontraron {len(tables)} tablas en la base de datos:")
            print("=" * 80)
            
            for table_name in sorted(tables):
                print(f"\nTABLA: {table_name}")
                print("-" * 80)
                
                # Obtener columnas de la tabla
                columns = inspector.get_columns(table_name)
                print(f"\n  COLUMNAS ({len(columns)}):")
                print(f"  {'Nombre':<25} {'Tipo':<30} {'Nulo':<5} {'Clave Primaria'}")
                print("  " + "-" * 75)
                
                for col in columns:
                    print(f"  {col['name']:<25} {str(col['type']):<30} {'Sí' if col.get('nullable', False) else 'No':<5} {'Sí' if col.get('primary_key', False) else 'No'}")
                
                # Obtener claves foráneas
                fks = inspector.get_foreign_keys(table_name)
                if fks:
                    print(f"\n  CLAVES FORÁNEAS ({len(fks)}):")
                    print(f"  {'Columna':<25} {'Referencia':<50}")
                    print("  " + "-" * 75)
                    
                    for fk in fks:
                        cols = ', '.join(fk['constrained_columns'])
                        ref = f"{fk['referred_table']}({', '.join(fk['referred_columns'])})"
                        print(f"  {cols:<25} {ref:<50}")
                
                # Obtener índices
                indexes = inspector.get_indexes(table_name)
                if indexes:
                    print(f"\n  ÍNDICES ({len(indexes)}):")
                    print(f"  {'Nombre':<30} {'Columnas':<40} {'Único'}")
                    print("  " + "-" * 75)
                    
                    for idx in indexes:
                        cols = ', '.join(idx['column_names'])
                        unique = 'Sí' if idx.get('unique', False) else 'No'
                        print(f"  {idx['name']:<30} {cols:<40} {unique}")
                
                print("\n" + "-" * 80)
        else:
            print("\nNo se encontraron tablas en la base de datos.")
        
        return True
        
    except Exception as e:
        logger.error(f"Error al verificar tablas: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
