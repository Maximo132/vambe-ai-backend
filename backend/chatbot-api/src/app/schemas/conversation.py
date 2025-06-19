from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

from app.schemas.message import Message
from app.models.conversation import MessageRole

class ConversationBase(BaseModel):
    """Base schema para conversaciones.
    
    Attributes:
        title: Título de la conversación
        metadata: Metadatos adicionales en formato JSON
    """
    title: str = Field(..., max_length=255, description="Título de la conversación")
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Metadatos adicionales en formato JSON"
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "title": "Conversación sobre desarrollo de software",
                "metadata": {
                    "tags": ["desarrollo", "programación"],
                    "priority": "alta"
                }
            }
        }
    )

class ConversationCreate(ConversationBase):
    """Schema para crear una nueva conversación."""
    pass

class ConversationUpdate(BaseModel):
    """Schema para actualizar una conversación existente."""
    title: Optional[str] = Field(
        None, 
        max_length=255, 
        description="Nuevo título para la conversación"
    )
    is_active: Optional[bool] = Field(
        None, 
        description="Indica si la conversación está activa"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Metadatos adicionales en formato JSON"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Nuevo título de la conversación",
                "is_active": True,
                "metadata": {"status": "en_progreso"}
            }
        }
    )

class ConversationInDBBase(ConversationBase):
    """Base schema para conversaciones en la base de datos.
    
    Incluye campos de auditoría y relaciones.
    """
    id: int
    user_id: int
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Conversación sobre desarrollo de software",
                "user_id": 1,
                "is_active": True,
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T12:00:00",
                "metadata": {"tags": ["desarrollo", "programación"]}
            }
        }
    )

class Conversation(ConversationInDBBase):
    """Schema para devolver datos de una conversación.
    
    Incluye los mensajes asociados.
    """
    messages: List[Message] = []
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Conversación sobre desarrollo de software",
                "user_id": 1,
                "is_active": True,
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T12:00:00",
                "metadata": {"tags": ["desarrollo", "programación"]},
                "messages": [
                    {
                        "id": 1,
                        "role": "user",
                        "content": "Hola, ¿cómo estás?",
                        "created_at": "2023-01-01T00:01:00"
                    },
                    {
                        "id": 2,
                        "role": "assistant",
                        "content": "¡Hola! Estoy bien, ¿y tú?",
                        "created_at": "2023-01-01T00:01:05"
                    }
                ]
            }
        }
    )

class ConversationInDB(ConversationInDBBase):
    """Schema para datos de conversación en la base de datos."""
    pass
