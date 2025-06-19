from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.models.chat import ConversationStatus, MessageRole, MessageType

# Esquemas para mensajes
class MessageBase(BaseModel):
    content: str
    role: MessageRole
    message_type: MessageType = MessageType.TEXT
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class MessageCreate(MessageBase):
    conversation_id: str

class MessageUpdate(BaseModel):
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class MessageInDBBase(MessageBase):
    id: str
    conversation_id: str
    created_at: datetime

    class Config:
        orm_mode = True

class Message(MessageInDBBase):
    pass

# Esquemas para conversaciones
class ConversationBase(BaseModel):
    title: str = Field(..., max_length=255)
    status: Optional[ConversationStatus] = ConversationStatus.ACTIVE
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class ConversationCreate(ConversationBase):
    pass

class ConversationUpdate(ConversationBase):
    title: Optional[str] = None
    status: Optional[ConversationStatus] = None

class ConversationInDBBase(ConversationBase):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

class Conversation(ConversationInDBBase):
    messages: List[Message] = []

# Esquemas para respuestas de la API
class ChatMessage(BaseModel):
    role: MessageRole
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    conversation_id: Optional[int] = None
    user_id: str
    metadata: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: int
    message_id: int
    metadata: Optional[Dict[str, Any]] = None
