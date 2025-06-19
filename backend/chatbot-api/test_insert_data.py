#!/usr/bin/env python
"""
Script para probar la inserción de datos en las tablas.
"""
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_insert.log')
    ]
)
logger = logging.getLogger(__name__)

def main():
    try:
        # Añadir el directorio src al path
        src_dir = str(Path(__file__).parent.absolute() / "src")
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
        
        # Configurar la URL de la base de datos
        db_url = os.environ.get("DATABASE_URL", "postgresql+psycopg2://chatbot_user:chatbot_password@localhost:5432/chatbot_db")
        os.environ["DATABASE_URL"] = db_url
        
        # Importar SQLAlchemy
        from sqlalchemy import create_engine, text
        
        # Crear motor de base de datos
        engine = create_engine(db_url, echo=True)
        
        # Insertar datos de ejemplo
        with engine.connect() as conn:
            # Iniciar transacción
            trans = conn.begin()
            
            try:
                # Insertar una conversación
                result = conn.execute(
                    text("""
                    INSERT INTO conversations (title, status, user_id, metadata, created_at, updated_at)
                    VALUES (:title, :status, :user_id, :metadata, :created_at, :updated_at)
                    RETURNING id
                    """),
                    {
                        'title': 'Primera conversación',
                        'status': 'active',
                        'user_id': 'usuario1',
                        'metadata': '{"tags": ["importante", "cliente_nuevo"]}',
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    }
                )
                
                # Obtener el ID de la conversación insertada
                conversation_id = result.scalar()
                logger.info(f"Conversación insertada con ID: {conversation_id}")
                
                # Insertar mensajes
                messages = [
                    {
                        'content': 'Hola, ¿cómo estás?',
                        'role': 'user',
                        'conversation_id': conversation_id,
                        'metadata': '{}',
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    },
                    {
                        'content': '¡Hola! Estoy bien, gracias por preguntar. ¿En qué puedo ayudarte hoy?',
                        'role': 'assistant',
                        'conversation_id': conversation_id,
                        'metadata': '{}',
                        'created_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    }
                ]
                
                for msg in messages:
                    result = conn.execute(
                        text("""
                        INSERT INTO messages (content, role, conversation_id, metadata, created_at, updated_at)
                        VALUES (:content, :role, :conversation_id, :metadata, :created_at, :updated_at)
                        RETURNING id
                        """),
                        msg
                    )
                    msg_id = result.scalar()
                    logger.info(f"Mensaje insertado con ID: {msg_id}")
                
                # Confirmar transacción
                trans.commit()
                logger.info("Datos insertados correctamente")
                
                # Consultar datos insertados
                logger.info("\nDatos de la conversación:")
                result = conn.execute(
                    text("SELECT * FROM conversations WHERE id = :id"),
                    {'id': conversation_id}
                )
                conv = result.first()
                logger.info(f"Conversación: {conv}")
                
                logger.info("\nMensajes de la conversación:")
                result = conn.execute(
                    text("SELECT id, role, content FROM messages WHERE conversation_id = :conv_id"),
                    {'conv_id': conversation_id}
                )
                for msg in result:
                    logger.info(f"  - {msg.role.upper()}: {msg.content[:50]}...")
                
            except Exception as e:
                # Revertir en caso de error
                trans.rollback()
                logger.error(f"Error al insertar datos: {e}", exc_info=True)
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    logger.info("Iniciando prueba de inserción de datos...")
    success = main()
    sys.exit(0 if success else 1)
