#!/usr/bin/env python
"""
Script de prueba para verificar la conexión a la base de datos y la creación de tablas.
"""
import os
import sys
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_db_connection.log')
    ]
)
logger = logging.getLogger(__name__)

def main():
    try:
        # Añadir el directorio src al path
        src_dir = str(Path(__file__).parent.absolute() / "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
        logger.debug(f"sys.path: {sys.path}")
        
        # Configurar la URL de la base de datos
        db_url = os.environ.get("DATABASE_URL", "postgresql+psycopg2://chatbot_user:chatbot_password@localhost:5432/chatbot_db")
        os.environ["DATABASE_URL"] = db_url
        logger.info(f"Usando URL de base de datos: {db_url}")
        
        # Importar SQLAlchemy
        from sqlalchemy import create_engine, inspect, text
        from sqlalchemy_utils import database_exists, create_database
        
        # Crear motor de base de datos
        engine = create_engine(db_url, echo=True)
        
        # Verificar conexión
        logger.info("Probando conexión a la base de datos...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            logger.info(f"Versión de PostgreSQL: {version}")
        
        # Verificar si la base de datos existe
        if not database_exists(engine.url):
            logger.info("La base de datos no existe. Creando...")
            create_database(engine.url)
        
        # Verificar tablas existentes
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"Tablas en la base de datos: {tables}")
        
        # Si no hay tablas, intentar crearlas
        if not tables:
            logger.info("No se encontraron tablas. Intentando crear tablas...")
            
            # Importar modelos
            from app.db.base import Base
            from app import (
                Conversation, Message, ConversationStatus, MessageRole
            )
            
            # Crear tablas
            logger.info("Creando tablas...")
            Base.metadata.create_all(bind=engine)
            
            # Verificar tablas creadas
            tables = inspector.get_table_names()
            logger.info(f"Tablas después de crearlas: {tables}")
            
            # Mostrar metadatos de las tablas
            for table_name in tables:
                logger.info(f"\nTabla: {table_name}")
                try:
                    columns = inspector.get_columns(table_name)
                    for column in columns:
                        logger.info(f"  Columna: {column['name']} ({column['type']})")
                except Exception as e:
                    logger.error(f"Error al obtener columnas de {table_name}: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    logger.info("Iniciando prueba de conexión a la base de datos...")
    success = main()
    sys.exit(0 if success else 1)
