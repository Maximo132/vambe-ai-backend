#!/usr/bin/env python
"""
Script simplificado para verificar tablas en la base de datos.
"""
import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, inspect, text

def main():
    # Configuración de la base de datos
    db_url = "postgresql+psycopg2://chatbot_user:chatbot_password@localhost:5432/chatbot_db"
    
    try:
        # Crear conexión a la base de datos
        print(f"Conectando a la base de datos: {db_url}")
        engine = create_engine(db_url)
        
        # Probar la conexión
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"Conexión exitosa: {result.scalar() == 1}")
        
        # Obtener inspector
        inspector = inspect(engine)
        
        # Obtener nombres de tablas
        tables = inspector.get_table_names()
        print(f"\nTablas encontradas: {', '.join(tables) if tables else 'Ninguna'}")
        
        for table_name in tables:
            print(f"\n=== TABLA: {table_name} ===")
            
            # Mostrar columnas
            print("\nColumnas:")
            for col in inspector.get_columns(table_name):
                print(f"  - {col['name']}: {col['type']} (PK: {'Sí' if col.get('primary_key') else 'No'}, Nulo: {'Sí' if col.get('nullable') else 'No'})")
            
            # Mostrar claves foráneas
            fks = inspector.get_foreign_keys(table_name)
            if fks:
                print("\nClaves foráneas:")
                for fk in fks:
                    print(f"  - {', '.join(fk['constrained_columns'])} -> {fk['referred_table']}({', '.join(fk['referred_columns'])})")
            
            # Mostrar índices
            indexes = inspector.get_indexes(table_name)
            if indexes:
                print("\nÍndices:")
                for idx in indexes:
                    print(f"  - {idx['name']}: {', '.join(idx['column_names'])} (Único: {'Sí' if idx.get('unique') else 'No'})")
        
        return True
        
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
