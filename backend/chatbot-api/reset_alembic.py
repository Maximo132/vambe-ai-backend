#!/usr/bin/env python
"""
Script para limpiar el estado de Alembic.
"""
import os
import sys
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('alembic_reset.log')
    ]
)
logger = logging.getLogger(__name__)

def main():
    try:
        # Importar psycopg2
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        # Parámetros de conexión
        db_params = {
            "host": "localhost",
            "database": "chatbot_db",
            "user": "chatbot_user",
            "password": "chatbot_password",
            "port": "5432"
        }
        
        logger.info("Conectando a la base de datos...")
        
        # Establecer conexión
        conn = psycopg2.connect(**db_params)
        conn.autocommit = True
        logger.info("¡Conexión exitosa!")
        
        # Crear un cursor
        with conn.cursor() as cur:
            # Verificar si la tabla alembic_version existe
            cur.execute("""
                DROP TABLE IF EXISTS alembic_version CASCADE;
            """)
            logger.info("Tabla alembic_version eliminada (si existía)")
            
            # Verificar si hay otras tablas de migración
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name LIKE '%alembic%';
            """)
            
            alembic_tables = cur.fetchall()
            if alembic_tables:
                logger.warning(f"Se encontraron tablas de Alembic: {alembic_tables}")
                for table in alembic_tables:
                    cur.execute(f"DROP TABLE IF EXISTS \"{table[0]}\" CASCADE;")
                    logger.info(f"Tabla {table[0]} eliminada")
            
            # Verificar si hay tablas en la base de datos
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public';
            """)
            
            tables = cur.fetchall()
            if tables:
                logger.warning(f"ADVERTENCIA: Se encontraron tablas en la base de datos: {tables}")
                confirm = input("¿Desea eliminar todas las tablas? (s/n): ")
                if confirm.lower() == 's':
                    # Deshabilitar restricciones de clave foránea temporalmente
                    cur.execute("SET session_replication_role = 'replica';")
                    
                    # Eliminar todas las tablas
                    for table in tables:
                        cur.execute(f'DROP TABLE IF EXISTS \"{table[0]}\" CASCADE;')
                        logger.info(f"Tabla {table[0]} eliminada")
                    
                    # Volver a habilitar restricciones
                    cur.execute("SET session_replication_role = 'origin';")
        
        logger.info("Base de datos limpiada exitosamente")
        return True
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return False
    finally:
        # Cerrar la conexión
        if 'conn' in locals():
            conn.close()
            logger.info("Conexión cerrada.")

if __name__ == "__main__":
    logger.warning("¡ADVERTENCIA! Este script eliminará todas las tablas de la base de datos.")
    confirm = input("¿Está seguro de que desea continuar? (s/n): ")
    
    if confirm.lower() == 's':
        success = main()
        sys.exit(0 if success else 1)
    else:
        logger.info("Operación cancelada por el usuario.")
        sys.exit(0)
