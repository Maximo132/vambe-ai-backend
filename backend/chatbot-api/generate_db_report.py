#!/usr/bin/env python
"""
Script para generar un informe detallado de la estructura de la base de datos.
"""
import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import URL

def get_db_connection():
    """Establece y devuelve la conexión a la base de datos."""
    db_url = "postgresql+psycopg2://chatbot_user:chatbot_password@localhost:5432/chatbot_db"
    return create_engine(db_url)

def get_table_info(engine, table_name):
    """Obtiene información detallada de una tabla."""
    inspector = inspect(engine)
    
    # Obtener columnas
    columns = inspector.get_columns(table_name)
    
    # Obtener claves primarias
    primary_keys = inspector.get_pk_constraint(table_name)
    
    # Obtener claves foráneas
    foreign_keys = inspector.get_foreign_keys(table_name)
    
    # Obtener índices
    indexes = inspector.get_indexes(table_name)
    
    return {
        'columns': columns,
        'primary_keys': primary_keys,
        'foreign_keys': foreign_keys,
        'indexes': indexes
    }

def format_column(column):
    """Formatea la información de una columna para mostrarla."""
    parts = [f"{column['name']} ({str(column['type'])})"]
    
    if column.get('primary_key', False):
        parts.append("PRIMARY KEY")
    if not column.get('nullable', True):
        parts.append("NOT NULL")
    if column.get('default') is not None:
        parts.append(f"DEFAULT {column['default']}")
    
    return " ".join(parts)

def generate_report():
    """Genera un informe detallado de la base de datos."""
    try:
        engine = get_db_connection()
        inspector = inspect(engine)
        
        # Obtener lista de tablas
        tables = inspector.get_table_names()
        
        # Crear informe
        report = []
        report.append("=" * 80)
        report.append(f"INFORME DE ESTRUCTURA DE LA BASE DE DATOS")
        report.append(f"Generado el: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 80)
        
        report.append(f"\nTABLAS ENCONTRADAS ({len(tables)}): {', '.join(tables)}")
        
        for table_name in tables:
            report.append("\n" + "=" * 80)
            report.append(f"TABLA: {table_name}")
            report.append("=" * 80)
            
            # Obtener información de la tabla
            table_info = get_table_info(engine, table_name)
            
            # Mostrar columnas
            report.append("\nCOLUMNAS:")
            report.append("-" * 80)
            for col in table_info['columns']:
                report.append(f"- {format_column(col)}")
            
            # Mostrar claves foráneas
            if table_info['foreign_keys']:
                report.append("\nCLAVES FORÁNEAS:")
                report.append("-" * 80)
                for fk in table_info['foreign_keys']:
                    cols = ", ".join(fk['constrained_columns'])
                    ref = f"{fk['referred_table']}({', '.join(fk['referred_columns'])})"
                    on_delete = f"ON DELETE {fk.get('ondelete', 'NO ACTION')}"
                    on_update = f"ON UPDATE {fk.get('onupdate', 'NO ACTION')}"
                    report.append(f"- {cols} -> {ref} {on_delete} {on_update}")
            
            # Mostrar índices
            if table_info['indexes']:
                report.append("\nÍNDICES:")
                report.append("-" * 80)
                for idx in table_info['indexes']:
                    cols = ", ".join(idx['column_names'])
                    unique = "ÚNICO" if idx.get('unique', False) else "NO ÚNICO"
                    report.append(f"- {idx['name']}: {cols} ({unique})")
        
        # Escribir informe en archivo
        with open('database_report.txt', 'w', encoding='utf-8') as f:
            f.write("\n".join(report))
        
        print("Informe generado correctamente en 'database_report.txt'")
        return True
        
    except Exception as e:
        print(f"Error al generar el informe: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    success = generate_report()
    sys.exit(0 if success else 1)
