# Importar la clase Base primero para evitar importaciones circulares
from .base import Base, BaseModel

# Importar los modelos individuales
from .conversation import Conversation
from .message import Message, MessageRole
from .document import Document
from .user import User, UserRole
from .login_history import LoginHistory
from .auth_token import AuthToken

# Lista de todos los modelos para facilitar la importación
__all__ = [
    "Base",
    "BaseModel",
    "Conversation",
    "Message",
    "MessageRole",
    "Document",
    "User",
    "UserRole",
    "LoginHistory",
    "AuthToken"
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
