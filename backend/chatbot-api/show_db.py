#!/usr/bin/env python
"""
Script para mostrar la estructura de la base de datos PostgreSQL.
"""
import psycopg2
from psycopg2.extras import DictCursor

def print_header(title):
    """Imprime un encabezado con el título proporcionado."""
    print(f"\n{'=' * 80}")
    print(f"{title.upper()}")
    print(f"{'=' * 80}")

def get_db_connection():
    """Establece y devuelve la conexión a la base de datos."""
    return psycopg2.connect(
        dbname="chatbot_db",
        user="chatbot_user",
        password="chatbot_password",
        host="localhost",
        port="5432"
    )

def show_tables(conn):
    """Muestra las tablas en la base de datos."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cur.fetchall()]
    
    print_header("tablas en la base de datos")
    for table in tables:
        print(f"- {table}")
    
    return tables

def show_table_columns(conn, table_name):
    """Muestra las columnas de una tabla específica."""
    with conn.cursor() as cur:
        # Obtener información de las columnas
        cur.execute("""
            SELECT 
                column_name, 
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position;
        """, (table_name,))
        
        columns = cur.fetchall()
        
        print_header(f"estructura de la tabla: {table_name}")
        print(f"{'Columna':<25} {'Tipo':<25} {'Nulo?':<10} {'Valor por defecto'}")
        print("-" * 80)
        
        for col in columns:
            print(f"{col[0]:<25} {col[1]:<25} {col[2]:<10} {col[3] or '-'}")

def show_primary_keys(conn):
    """Muestra las claves primarias de las tablas."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                tc.table_name,
                kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
            ORDER BY tc.table_name, kcu.ordinal_position;
        """)
        
        pks = cur.fetchall()
        
        print_header("claves primarias")
        if pks:
            current_table = ""
            for table, column in pks:
                if table != current_table:
                    print(f"\n{table}:")
                    current_table = table
                print(f"  - {column}")
        else:
            print("No se encontraron claves primarias.")

def show_foreign_keys(conn):
    """Muestra las claves foráneas de las tablas."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                tc.table_name AS tabla_origen,
                kcu.column_name AS columna_origen,
                ccu.table_name AS tabla_referenciada,
                ccu.column_name AS columna_referenciada,
                rc.delete_rule AS on_delete,
                rc.update_rule AS on_update
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            LEFT JOIN information_schema.referential_constraints rc
                ON tc.constraint_name = rc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY';
        """)
        
        fks = cur.fetchall()
        
        print_header("claves foráneas")
        if fks:
            current_table = ""
            for fk in fks:
                if fk[0] != current_table:
                    print(f"\n{fk[0]}:")
                    current_table = fk[0]
                print(f"  - {fk[1]} -> {fk[2]}({fk[3]})")
                print(f"     ON DELETE {fk[4]} | ON UPDATE {fk[5]}")
        else:
            print("No se encontraron claves foráneas.")

def show_indexes(conn):
    """Muestra los índices de las tablas."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
                t.relname AS table_name,
                i.relname AS index_name,
                a.attname AS column_name,
                ix.indisunique AS is_unique,
                ix.indisprimary AS is_primary
            FROM
                pg_class t,
                pg_class i,
                pg_index ix,
                pg_attribute a
            WHERE
                t.oid = ix.indrelid
                AND i.oid = ix.indexrelid
                AND a.attrelid = t.oid
                AND a.attnum = ANY(ix.indkey)
                AND t.relkind = 'r'
                AND t.relname IN (
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                )
            ORDER BY
                t.relname, i.relname;
        """)
        
        indexes = cur.fetchall()
        
        print_header("índices")
        if indexes:
            current_table = ""
            for idx in indexes:
                if idx[0] != current_table:
                    print(f"\n{idx[0]}:")
                    current_table = idx[0]
                
                idx_type = []
                if idx[3]:  # is_unique
                    idx_type.append("ÚNICO")
                if idx[4]:  # is_primary
                    idx_type.append("PRIMARIO")
                
                idx_type_str = f" ({', '.join(idx_type)})" if idx_type else ""
                print(f"  - {idx[1]}: {idx[2]}{idx_type_str}")
        else:
            print("No se encontraron índices.")

def main():
    """Función principal."""
    conn = None
    try:
        # Conectar a la base de datos
        conn = get_db_connection()
        
        # Mostrar información de la base de datos
        tables = show_tables(conn)
        
        # Mostrar estructura de cada tabla
        for table in tables:
            show_table_columns(conn, table)
        
        # Mostrar claves primarias
        show_primary_keys(conn)
        
        # Mostrar claves foráneas
        show_foreign_keys(conn)
        
        # Mostrar índices
        show_indexes(conn)
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
