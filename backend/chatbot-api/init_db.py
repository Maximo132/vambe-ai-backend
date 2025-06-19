#!/usr/bin/env python
"""
Script para inicializar la base de datos desde cero.
"""
import os
import sys
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,  # Nivel de depuración más detallado
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('init_db.log')
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
        from sqlalchemy import create_engine, inspect
        from sqlalchemy_utils import database_exists, create_database
        
        # Crear motor de base de datos
        engine = create_engine(db_url, echo=True)
        
        # Crear la base de datos si no existe
        if not database_exists(engine.url):
            logger.info("Creando base de datos...")
            create_database(engine.url)
        
        # Importar base de datos y modelos
        logger.info("Importando base de datos y modelos...")
        from app.db.base import Base, database
        # Importar modelos a través del paquete app
        from app import (
            Conversation, Message, ConversationStatus, MessageRole
        )
        
        # Configurar la URL de la base de datos
        database.set_url(db_url)
        
        # Crear todas las tablas
        logger.info("Creando tablas...")
        Base.metadata.create_all(bind=engine)
        
        # Verificar tablas creadas
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        logger.info(f"Tablas en la base de datos: {tables}")
        
        # Verificar tablas específicas
        expected_tables = {'conversations', 'messages'}
        missing_tables = expected_tables - set(tables)
        
        if missing_tables:
            logger.warning(f"Faltan tablas: {missing_tables}")
            
            # Mostrar metadatos de las tablas
            logger.info("Metadatos de tablas:")
            for table_name in tables:
                logger.info(f"\nTabla: {table_name}")
                try:
                    columns = inspector.get_columns(table_name)
                    for column in columns:
                        logger.info(f"  Columna: {column['name']} ({column['type']})")
                except Exception as e:
                    logger.error(f"Error al obtener columnas de {table_name}: {e}")
        else:
            logger.info("¡Todas las tablas esperadas se crearon correctamente!")
        
        logger.info("¡Base de datos inicializada correctamente!")
        return True
        
    except Exception as e:
        logger.error(f"Error al inicializar la base de datos: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    logger.info("Iniciando inicialización de la base de datos...")
    success = main()
    sys.exit(0 if success else 1)
