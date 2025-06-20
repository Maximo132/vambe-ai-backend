# Importar la clase Base primero para evitar importaciones circulares
from .base import Base, BaseModel

# Importar las enumeraciones primero
from .enums import MessageRole, UserRole

# Importar los modelos individuales
from .conversation import Conversation
from .message import Message
from .document import Document, DocumentType, DocumentStatus
from .user import User, UserStatus
from .login_history import LoginHistory
from .auth_token import AuthToken
from .chat import Conversation as ChatConversation, ConversationStatus, MessageType

# Lista de todos los modelos para facilitar la importación
__all__ = [
    # Clases base
    "Base",
    "BaseModel",
    
    # Modelos
    "Conversation",
    "ChatConversation",
    "Message",
    "Document",
    "User",
    "LoginHistory",
    "AuthToken",
    
    # Enumeraciones
    "MessageRole",
    "UserRole",
    "UserStatus",
    "ConversationStatus",
    "MessageType",
    "DocumentType",
    "DocumentStatus"
]

# Importar todos los modelos para que SQLAlchemy los registre
# Esto es necesario para que Alembic pueda descubrir los modelos
# y para que SQLAlchemy pueda crear las tablas correctamente
# No es necesario asignar a variables, solo importar
import app.models.conversation
import app.models.message
import app.models.document
import app.models.user
import app.models.login_history
import app.models.auth_token
