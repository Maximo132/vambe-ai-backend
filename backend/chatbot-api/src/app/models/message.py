from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from ..db.base_class import Base
from .enums import MessageRole

class Message(Base):
    """
    Modelo para almacenar los mensajes de chat.
    """
    __tablename__ = "messages"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    conversation_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=True)  # Puede ser nulo para mensajes de función
    name = Column(String(100), nullable=True)  # Para mensajes de función
    function_call = Column(JSON, nullable=True)  # Para llamadas a funciones
    metadata_ = Column("metadata", JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    tokens = Column(JSON, nullable=True)  # Información de tokens usados
    
    # Relación con la conversación
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, role='{self.role}', content='{self.content[:30]}...')>"
    
    def to_dict(self):
        """Convierte el objeto a diccionario."""
        return {
            "id": str(self.id),
            "conversation_id": str(self.conversation_id),
            "role": self.role.value,
            "content": self.content,
            "name": self.name,
            "function_call": self.function_call,
            "metadata": self.metadata_,
            "created_at": self.created_at.isoformat(),
            "tokens": self.tokens
        }
    
    @classmethod
    def from_orm(cls, obj):
        """Crea una instancia de Message a partir de un ORM."""
        return cls(
            id=obj.id,
            conversation_id=obj.conversation_id,
            role=MessageRole(obj.role),
            content=obj.content,
            name=obj.name,
            function_call=obj.function_call,
            metadata_=obj.metadata_,
            created_at=obj.created_at,
            tokens=obj.tokens
        )
