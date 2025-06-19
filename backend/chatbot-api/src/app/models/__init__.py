from .base import Base, BaseModel
from .chat import Conversation, Message, ConversationStatus, MessageRole
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
    "ConversationStatus", 
    "MessageRole",
    "Document",
    "User",
    "UserRole",
    "LoginHistory",
    "AuthToken"
]

# Importar todos los modelos para que SQLAlchemy los conozca
from .chat import Conversation, Message
from .document import Document
from .user import User
from .login_history import LoginHistory
from .auth_token import AuthToken
