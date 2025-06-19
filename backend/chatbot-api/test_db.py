#!/usr/bin/env python
"""
Script de prueba de conexión a la base de datos.
"""
import os
import sys
import logging
from pathlib import Path

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_db.log')
    ]
)
logger = logging.getLogger(__name__)

def main():
    try:
        # Configurar la URL de la base de datos
        db_url = "postgresql+psycopg2://chatbot_user:chatbot_password@localhost:5432/chatbot_db"
        logger.info(f"Conectando a la base de datos: {db_url}")
        
        # Importar SQLAlchemy
        from sqlalchemy import create_engine
        
        # Crear motor de base de datos con eco habilitado
        engine = create_engine(db_url, echo=True)
        
        # Probar la conexión
        logger.info("Probando conexión...")
        with engine.connect() as conn:
            logger.info("Conexión exitosa")
            
            # Obtener nombres de tablas
            logger.info("Consultando tablas...")
            result = conn.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            
            tables = [row[0] for row in result]
            
            if tables:
                logger.info(f"\nTablas encontradas ({len(tables)}):")
                for table in tables:
                    logger.info(f"\nTabla: {table}")
                    
                    try:
                        # Obtener columnas de cada tabla usando parámetros
                        cols_result = conn.execute("""
                            SELECT column_name, data_type 
                            FROM information_schema.columns 
                            WHERE table_schema = 'public' 
                            AND table_name = %s
                            ORDER BY ordinal_position
                        """, (table,))
                        
                        columns = list(cols_result)
                        logger.info(f"  Columnas ({len(columns)}):")
                        for col in columns:
                            logger.info(f"  - {col[0]}: {col[1]}")
                    except Exception as e:
                        logger.error(f"  Error al obtener columnas: {e}")
            else:
                logger.info("No se encontraron tablas en la base de datos.")
        
        return True
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
