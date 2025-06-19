#!/usr/bin/env python
"""
Script simplificado para mostrar la estructura de las tablas de la base de datos.
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

def print_table_structure(engine, table_name):
    """Muestra la estructura de una tabla específica."""
    with engine.connect() as conn:
        # Obtener columnas
        columns = conn.execute(text("""
            SELECT 
                column_name, 
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = :table_name
            ORDER BY ordinal_position
        """), {'table_name': table_name}).fetchall()
        
        print(f"\nTabla: {table_name}")
        print("-" * 80)
        print("Columnas:")
        for col in columns:
            nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
            default = f"DEFAULT {col[3]}" if col[3] else ""
            print(f"  - {col[0]} ({col[1]}) {nullable} {default}")
        
        # Obtener claves primarias
        primary_keys = conn.execute(text("""
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
            AND tc.table_name = :table_name
        """), {'table_name': table_name}).fetchall()
        
        if primary_keys:
            print("\nClaves primarias:")
            for pk in primary_keys:
                print(f"  - {pk[0]}")
        
        # Obtener claves foráneas
        foreign_keys = conn.execute(text("""
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                rc.delete_rule
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            LEFT JOIN information_schema.referential_constraints rc
                ON tc.constraint_name = rc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY' 
            AND tc.table_name = :table_name
        """), {'table_name': table_name}).fetchall()
        
        if foreign_keys:
            print("\nClaves foráneas:")
            for fk in foreign_keys:
                print(f"  - {fk[0]} -> {fk[1]}({fk[2]}) ON DELETE {fk[3]}")

def main():
    """Función principal."""
    try:
        # Configurar conexión a la base de datos
        db_url = "postgresql+psycopg2://chatbot_user:chatbot_password@localhost:5432/chatbot_db"
        engine = create_engine(db_url)
        
        # Obtener lista de tablas
        with engine.connect() as conn:
            tables = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)).fetchall()
            
            if not tables:
                print("No se encontraron tablas en la base de datos.")
                return True
            
            print(f"\nTablas encontradas: {', '.join([t[0] for t in tables])}")
            
            # Mostrar estructura de cada tabla
            for table in tables:
                print_table_structure(engine, table[0])
                print("\n" + "=" * 80 + "\n")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False
    finally:
        if 'engine' in locals():
            engine.dispose()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
