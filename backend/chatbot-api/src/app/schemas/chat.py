from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Union, Literal
from pydantic import BaseModel, Field, UUID4
from uuid import UUID

from app.models import MessageRole

class MessageType(str, Enum):
    """Tipos de mensajes."""
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    FUNCTION_CALL = "function_call"
    FUNCTION_RESULT = "function_result"

class ConversationStatus(str, Enum):
    """Estados de una conversación."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"

# Esquemas para mensajes
class MessageBase(BaseModel):
    """Esquema base para mensajes."""
    content: Optional[str] = None
    role: MessageRole
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    message_type: MessageType = MessageType.TEXT

class MessageCreate(MessageBase):
    """Esquema para crear un mensaje."""
    conversation_id: UUID4
    content: str  # Hacemos el contenido obligatorio al crear

class MessageUpdate(BaseModel):
    """Esquema para actualizar un mensaje."""
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    function_call: Optional[Dict[str, Any]] = None

class MessageInDBBase(MessageBase):
    """Esquema base para mensajes en la base de datos."""
    id: UUID4
    conversation_id: UUID4
    created_at: datetime
    tokens: Optional[Dict[str, int]] = None
    
    class Config:
        orm_mode = True
        json_encoders = {
            UUID: lambda v: str(v),
        }

class Message(MessageInDBBase):
    """Esquema para representar un mensaje completo."""
    pass

# Esquemas para conversaciones
class ConversationBase(BaseModel):
    """Esquema base para conversaciones."""
    title: str = Field(..., max_length=255)
    status: ConversationStatus = ConversationStatus.ACTIVE
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ConversationCreate(ConversationBase):
    """Esquema para crear una conversación."""
    title: Optional[str] = "Nueva conversación"

class ConversationUpdate(BaseModel):
    """Esquema para actualizar una conversación."""
    title: Optional[str] = None
    status: Optional[ConversationStatus] = None
    metadata: Optional[Dict[str, Any]] = None

class ConversationInDBBase(ConversationBase):
    """Esquema base para conversaciones en la base de datos."""
    id: UUID4
    user_id: UUID4
    created_at: datetime
    updated_at: datetime
    
    # Campos calculados
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True
        json_encoders = {
            UUID: lambda v: str(v),
        }

class Conversation(ConversationInDBBase):
    """Esquema para representar una conversación con sus mensajes."""
    messages: List[Message] = []

# Esquemas para la API de chat
class ChatMessage(BaseModel):
    """Esquema para un mensaje en una solicitud de chat."""
    role: MessageRole
    content: str
    name: Optional[str] = None
    function_call: Optional[Dict[str, Any]] = None

class ChatRequest(BaseModel):
    """Esquema para una solicitud de chat."""
    messages: List[ChatMessage]
    conversation_id: Optional[UUID4] = None
    user_id: UUID4
    metadata: Dict[str, Any] = Field(default_factory=dict)
    stream: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

class ChatResponse(BaseModel):
    """Esquema para una respuesta de chat."""
    message: MessageInDBBase
    conversation_id: UUID4
    
    class Config:
        json_encoders = {
            UUID: lambda v: str(v),
        }

class ChatResponseChunk(BaseModel):
    """Esquema para un fragmento de respuesta en streaming."""
    id: UUID4
    content: str
    conversation_id: UUID4
    done: bool = False
    
    class Config:
        json_encoders = {
            UUID: lambda v: str(v),
        }

class FunctionCall(BaseModel):
    """Esquema para una llamada a función."""
    name: str
    arguments: Dict[str, Any]

class FunctionCallChunk(BaseModel):
    """Esquema para un fragmento de llamada a función en streaming."""
    name: Optional[str] = None
    arguments: str = ""
