#!/usr/bin/env python
"""
Script de prueba de conexión simple a PostgreSQL.
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
        logging.FileHandler('simple_test.log')
    ]
)
logger = logging.getLogger(__name__)

def main():
    try:
        # Importar psycopg2 directamente
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
        logger.info("¡Conexión exitosa!")
        
        # Crear un cursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Obtener la versión de PostgreSQL
            cur.execute("SELECT version();")
            version = cur.fetchone()
            logger.info(f"Versión de PostgreSQL: {version['version']}")
            
            # Obtener las tablas
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            
            tables = cur.fetchall()
            logger.info(f"\nTablas encontradas ({len(tables)}):")
            
            for table in tables:
                table_name = table['table_name']
                logger.info(f"\nTabla: {table_name}")
                
                # Obtener columnas
                cur.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                    ORDER BY ordinal_position
                """, (table_name,))
                
                columns = cur.fetchall()
                logger.info(f"  Columnas ({len(columns)}):")
                for col in columns:
                    logger.info(f"  - {col['column_name']}: {col['data_type']}")
        
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
    success = main()
    sys.exit(0 if success else 1)
