from .base import Base, BaseModel
from .conversation import Conversation
from .message import Message, MessageRole
from .document import Document
from .user import User, UserRole
from .login_history import LoginHistory
from .auth_token import AuthToken

# Importar todos los modelos aquí para que Alembic los detecte automáticamente
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

# Importar todos los modelos para que SQLAlchemy los conozca
from .conversation import Conversation
from .message import Message
from .document import Document
from .user import User
from .login_history import LoginHistory
from .auth_token import AuthToken
