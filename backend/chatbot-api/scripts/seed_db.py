"""
Script para poblar la base de datos con datos de prueba.

Este script carga datos iniciales en la base de datos para desarrollo y pruebas.
"""
import os
import sys
import logging
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def setup_paths() -> None:
    """Configura las rutas necesarias para las importaciones."""
    # Añadir el directorio src al path
    project_root = Path(__file__).parent.parent
    src_path = project_root / 'src'
    
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    # Configurar nivel de logging para SQLAlchemy
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

def get_sample_data() -> Dict[str, List[Dict[str, Any]]]:
    """Genera datos de ejemplo para poblar la base de datos."""
    # Fechas de ejemplo
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    
    # Usuarios de ejemplo
    users = [
        {
            "username": "admin",
            "email": "admin@vambe.ai",
            "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # secret
            "first_name": "Admin",
            "last_name": "Sistema",
            "is_active": True,
            "is_verified": True,
            "role": "admin"
        },
        {
            "username": "usuario1",
            "email": "usuario1@ejemplo.com",
            "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # secret
            "first_name": "Usuario",
            "last_name": "Uno",
            "is_active": True,
            "is_verified": True,
            "role": "user"
        },
        {
            "username": "agente1",
            "email": "agente1@vambe.ai",
            "hashed_password": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # secret
            "first_name": "Agente",
            "last_name": "Soporte",
            "is_active": True,
            "is_verified": True,
            "role": "agent"
        }
    ]
    
    # Documentos de ejemplo
    documents = [
        {
            "title": "Manual de Usuario",
            "description": "Documentación completa del sistema",
            "file_path": "/documents/manual_usuario.pdf",
            "file_type": "application/pdf",
            "file_size": 1024000,
            "user_id": 1
        },
        {
            "title": "Políticas de Privacidad",
            "description": "Términos y condiciones de privacidad",
            "file_path": "/documents/politicas_privacidad.pdf",
            "file_type": "application/pdf",
            "file_size": 512000,
            "user_id": 1
        }
    ]
    
    # Conversaciones de ejemplo
    conversations = [
        {
            "title": "Consulta sobre facturación",
            "status": "completed",
            "user_id": 2,
            "assigned_to": 3,
            "created_at": week_ago + timedelta(hours=2),
            "updated_at": week_ago + timedelta(hours=3)
        },
        {
            "title": "Problema con inicio de sesión",
            "status": "open",
            "user_id": 2,
            "assigned_to": None,
            "created_at": now - timedelta(hours=2),
            "updated_at": now - timedelta(hours=1)
        }
    ]
    
    # Mensajes de ejemplo
    messages = [
        {
            "content": "Hola, tengo un problema con mi factura",
            "role": "user",
            "conversation_id": 1,
            "user_id": 2,
            "created_at": week_ago + timedelta(hours=2, minutes=5)
        },
        {
            "content": "Claro, ¿podrías proporcionarme el número de factura?",
            "role": "assistant",
            "conversation_id": 1,
            "user_id": 3,
            "created_at": week_ago + timedelta(hours=2, minutes=10)
        },
        {
            "content": "No puedo iniciar sesión en mi cuenta",
            "role": "user",
            "conversation_id": 2,
            "user_id": 2,
            "created_at": now - timedelta(hours=2, minutes=30)
        },
        {
            "content": "Hemos recibido tu mensaje. Un agente se pondrá en contacto contigo pronto.",
            "role": "assistant",
            "conversation_id": 2,
            "user_id": None,
            "created_at": now - timedelta(hours=2, minutes=0)
        }
    ]
    
    return {
        "users": users,
        "documents": documents,
        "conversations": conversations,
        "messages": messages
    }

def create_sample_data() -> bool:
    """Crea datos de ejemplo en la base de datos."""
    try:
        from sqlalchemy.orm import Session
        from app.db.session import SessionLocal
        from app.models.user import User
        from app.models.document import Document
        from app.models.conversation import Conversation
        from app.models.message import Message
        
        # Obtener datos de ejemplo
        sample_data = get_sample_data()
        
        # Crear sesión de base de datos
        db = SessionLocal()
        
        try:
            # Crear usuarios
            logger.info("Creando usuarios de ejemplo...")
            for user_data in sample_data["users"]:
                user = User(**user_data)
                db.add(user)
            db.commit()
            
            # Crear documentos
            logger.info("Creando documentos de ejemplo...")
            for doc_data in sample_data["documents"]:
                document = Document(**doc_data)
                db.add(document)
            db.commit()
            
            # Crear conversaciones
            logger.info("Creando conversaciones de ejemplo...")
            for conv_data in sample_data["conversations"]:
                conversation = Conversation(**conv_data)
                db.add(conversation)
            db.commit()
            
            # Crear mensajes
            logger.info("Creando mensajes de ejemplo...")
            for msg_data in sample_data["messages"]:
                message = Message(**msg_data)
                db.add(message)
            db.commit()
            
            logger.info("Datos de ejemplo creados exitosamente.")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error al crear datos de ejemplo: {e}")
            return False
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error inesperado al crear datos de ejemplo: {e}")
        return False

def main() -> int:
    """Función principal del script de población de datos."""
    # Configurar rutas
    setup_paths()
    
    # Confirmar con el usuario
    print("\n=== ADVERTENCIA ===\n")
    print("Este script borrará todos los datos existentes en la base de datos")
    print(f"y cargará datos de ejemplo.\n")
    
    confirm = input("¿Estás seguro de que deseas continuar? (s/n): ")
    if confirm.lower() != 's':
        print("Operación cancelada.")
        return 0
    
    # Crear datos de ejemplo
    logger.info("Iniciando la creación de datos de ejemplo...")
    if create_sample_data():
        logger.info("¡Datos de ejemplo creados exitosamente!")
        return 0
    else:
        logger.error("Error al crear datos de ejemplo.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
