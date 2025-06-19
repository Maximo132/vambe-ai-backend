#!/usr/bin/env python
"""
Script simple para mostrar la estructura de la base de datos usando psycopg2.
"""
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

def get_db_connection():
    """Establece y devuelve la conexión a la base de datos."""
    return psycopg2.connect(
        dbname="chatbot_db",
        user="chatbot_user",
        password="chatbot_password",
        host="localhost",
        port="5432"
    )

def get_tables(conn):
    """Obtiene la lista de tablas en la base de datos."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        return [row[0] for row in cur.fetchall()]

def print_table_structure(conn, table_name):
    """Muestra la estructura de una tabla específica."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Obtener columnas
        cur.execute("""
            SELECT 
                column_name, 
                data_type,
                is_nullable,
                column_default,
                character_maximum_length,
                numeric_precision,
                numeric_scale
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position;
        """, (table_name,))
        
        columns = cur.fetchall()
        
        print(f"\n=== TABLA: {table_name} ===")
        print("\nCOLUMNAS:")
        print("-" * 80)
        for col in columns:
            # Formatear el tipo de dato
            data_type = col['data_type'].upper()
            if col['character_maximum_length'] is not None:
                data_type += f"({col['character_maximum_length']})"
            elif col['numeric_precision'] is not None:
                if col['numeric_scale'] is not None and col['numeric_scale'] > 0:
                    data_type += f"({col['numeric_precision']},{col['numeric_scale']})"
                else:
                    data_type += f"({col['numeric_precision']})"
            
            # Mostrar información de la columna
            nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
            default = f"DEFAULT {col['column_default']}" if col['column_default'] else ""
            print(f"{col['column_name']:20} {data_type:20} {nullable:10} {default}")
        
        # Obtener claves primarias
        cur.execute("""
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
            AND tc.table_name = %s;
        """, (table_name,))
        
        primary_keys = [row['column_name'] for row in cur.fetchall()]
        
        if primary_keys:
            print("\nCLAVES PRIMARIAS:")
            print("-" * 80)
            for pk in primary_keys:
                print(f"- {pk}")
        
        # Obtener claves foráneas
        cur.execute("""
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                rc.delete_rule,
                rc.update_rule
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
            AND tc.table_name = %s;
        """, (table_name,))
        
        foreign_keys = cur.fetchall()
        
        if foreign_keys:
            print("\nCLAVES FORÁNEAS:")
            print("-" * 80)
            for fk in foreign_keys:
                print(f"- {fk['column_name']} -> {fk['foreign_table_name']}({fk['foreign_column_name']}) "
                      f"ON DELETE {fk['delete_rule']} ON UPDATE {fk['update_rule']}")
        
        # Obtener índices
        cur.execute("""
            SELECT
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
                AND t.relname = %s
            ORDER BY
                t.relname, i.relname;
        """, (table_name,))
        
        indexes = cur.fetchall()
        
        if indexes:
            print("\nÍNDICES:")
            print("-" * 80)
            for idx in indexes:
                idx_type = []
                if idx['is_unique']:
                    idx_type.append("ÚNICO")
                if idx['is_primary']:
                    idx_type.append("PRIMARIO")
                
                idx_type_str = f" ({', '.join(idx_type)})" if idx_type else ""
                print(f"- {idx['index_name']}: {idx['column_name']}{idx_type_str}")

def main():
    """Función principal."""
    conn = None
    try:
        # Conectar a la base de datos
        conn = get_db_connection()
        
        # Obtener lista de tablas
        tables = get_tables(conn)
        
        if not tables:
            print("No se encontraron tablas en la base de datos.")
            return True
        
        print(f"\nTABLAS ENCONTRADAS ({len(tables)}): {', '.join(tables)}\n")
        
        # Mostrar estructura de cada tabla
        for table in tables:
            print_table_structure(conn, table)
            print("\n" + "=" * 80 + "\n")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False
    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
