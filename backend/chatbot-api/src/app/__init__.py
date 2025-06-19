"""
Paquete principal de la aplicación.

Este archivo hace que el directorio app sea un paquete de Python y expone
los componentes principales de la aplicación.
"""
import logging
from typing import List, Optional, TypeVar

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Importar modelos para que estén disponibles cuando se importe el paquete
from .models.chat import Conversation, Message, ConversationStatus, MessageRole
from .models.user import User, UserRole, UserStatus
from .models.base import BaseModel

# Importar configuraciones
try:
    from .core.config import settings
    from .db import init_db, get_db, get_async_db
    from .db.session import SessionLocal, AsyncSessionLocal, engine, async_engine
    
    # Inicializar la base de datos
    init_db()
    
    DB_INITIALIZED = True
except ImportError as e:
    logger.warning(f"No se pudo inicializar la base de datos: {e}")
    DB_INITIALIZED = False

# Hacer los componentes disponibles directamente desde app
__all__ = [
    # Modelos
    'Conversation',
    'Message',
    'ConversationStatus',
    'MessageRole',
    'User',
    'UserRole',
    'UserStatus',
    'BaseModel',
    
    # Configuración
    'settings',
    
    # Base de datos
    'init_db',
    'get_db',
    'get_async_db',
    'SessionLocal',
    'AsyncSessionLocal',
    'engine',
    'async_engine'
]

# Inicializar la aplicación
if DB_INITIALIZED:
    logger.info("Aplicación inicializada correctamente")
