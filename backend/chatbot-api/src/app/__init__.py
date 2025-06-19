# This file makes the app directory a Python package

# Importar modelos para que estén disponibles cuando se importe el paquete
from .models.chat import Conversation, Message, ConversationStatus, MessageRole

# Hacer los modelos disponibles directamente desde app
__all__ = [
    'Conversation',
    'Message',
    'ConversationStatus',
    'MessageRole'
]
