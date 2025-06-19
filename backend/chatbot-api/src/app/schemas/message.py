from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

from app.models.conversation import MessageRole

class MessageBase(BaseModel):
    """Base schema para mensajes.
    
    Attributes:
        role: Rol del mensaje (system, user, assistant, function)
        content: Contenido del mensaje
        name: Nombre del remitente (opcional)
        function_call: Datos de llamada a función (opcional)
        token_count: Número de tokens del mensaje (opcional)
    """
    role: MessageRole = Field(..., description="Rol del mensaje (system, user, assistant, function)")
    content: str = Field(..., description="Contenido del mensaje")
    name: Optional[str] = Field(None, description="Nombre del remitente (opcional)")
    function_call: Optional[Dict[str, Any]] = Field(
        None, 
        description="Datos de llamada a función (opcional)"
    )
    token_count: Optional[int] = Field(
        None, 
        description="Número de tokens del mensaje (opcional)"
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "role": "user",
                "content": "Hola, ¿cómo estás?",
                "name": "Usuario",
                "token_count": 7
            }
        }
    )

class MessageCreate(MessageBase):
    """Schema para crear un nuevo mensaje."""
    conversation_id: int = Field(..., description="ID de la conversación")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "conversation_id": 1,
                "role": "user",
                "content": "Hola, ¿cómo estás?",
                "name": "Usuario"
            }
        }
    )

class MessageUpdate(BaseModel):
    """Schema para actualizar un mensaje existente."""
    content: Optional[str] = Field(
        None, 
        max_length=10000, 
        description="Nuevo contenido del mensaje"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Metadatos adicionales en formato JSON"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "Mensaje actualizado",
                "metadata": {"edited": True}
            }
        }
    )

class MessageInDBBase(MessageBase):
    """Base schema para mensajes en la base de datos.
    
    Incluye campos de auditoría y relaciones.
    """
    id: int
    conversation_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "conversation_id": 1,
                "role": "user",
                "content": "Hola, ¿cómo estás?",
                "name": "Usuario",
                "token_count": 7,
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00"
            }
        }
    )

class Message(MessageInDBBase):
    """Schema para devolver datos de un mensaje."""
    pass

class MessageInDB(MessageInDBBase):
    """Schema para datos de mensaje en la base de datos."""
    pass

# Esquemas para el chat en tiempo real
class ChatMessage(BaseModel):
    """Schema para mensajes de chat en tiempo real."""
    role: MessageRole = Field(..., description="Rol del mensaje (system, user, assistant, function)")
    content: str = Field(..., description="Contenido del mensaje")
    name: Optional[str] = Field(None, description="Nombre del remitente (opcional)")
    function_call: Optional[Dict[str, Any]] = Field(
        None, 
        description="Datos de llamada a función (opcional)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "role": "user",
                "content": "Hola, ¿cómo estás?",
                "name": "Usuario"
            }
        }
    )

class ChatRequest(BaseModel):
    """Schema para solicitudes de chat.
    
    Se utiliza para enviar mensajes al chatbot y recibir respuestas.
    """
    messages: List[ChatMessage] = Field(
        ..., 
        description="Lista de mensajes de la conversación"
    )
    conversation_id: Optional[int] = Field(
        None, 
        description="ID de la conversación (opcional, para continuar una conversación existente)"
    )
    temperature: Optional[float] = Field(
        0.7, 
        ge=0.0, 
        le=2.0, 
        description="Controla la aleatoriedad de la respuesta (0-2)"
    )
    max_tokens: Optional[int] = Field(
        1000, 
        gt=0, 
        description="Número máximo de tokens en la respuesta"
    )
    stream: bool = Field(
        False, 
        description="Si es True, la respuesta se envía como un stream de eventos"
    )
    functions: Optional[List[Dict[str, Any]]] = Field(
        None, 
        description="Lista de funciones disponibles para el modelo"
    )
    function_call: Optional[Union[str, Dict[str, str]]] = Field(
        None, 
        description="Controla cómo se llama a las funciones"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "messages": [
                    {"role": "system", "content": "Eres un asistente útil."},
                    {"role": "user", "content": "Hola, ¿cómo estás?"}
                ],
                "conversation_id": 1,
                "temperature": 0.7,
                "max_tokens": 1000,
                "stream": False
            }
        }
    )

class ChatResponse(BaseModel):
    """Schema para respuestas del chat."""
    message: ChatMessage = Field(..., description="Mensaje de respuesta")
    conversation_id: Optional[int] = Field(
        None, 
        description="ID de la conversación"
    )
    usage: Optional[Dict[str, int]] = Field(
        None,
        description="Información de uso de tokens"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": {
                    "role": "assistant",
                    "content": "¡Hola! Estoy bien, ¿en qué puedo ayudarte hoy?"
                },
                "conversation_id": 1,
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 15,
                    "total_tokens": 25
                }
            }
        }
    )

class ChatResponseChunk(BaseModel):
    """Schema para fragmentos de respuesta en streaming."""
    chunk: str = Field(..., description="Fragmento de la respuesta")
    conversation_id: Optional[int] = Field(
        None, 
        description="ID de la conversación"
    )
    done: bool = Field(
        False, 
        description="Indica si es el último fragmento"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "chunk": "¡Hola!",
                "conversation_id": 1,
                "done": False
            }
        }
    )
