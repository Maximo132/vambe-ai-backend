from sqlalchemy import Column, String, DateTime, JSON, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from ..db.base_class import Base

class Conversation(Base):
    """
    Modelo para almacenar las conversaciones de chat.
    """
    __tablename__ = "conversations"
    
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    metadata_ = Column("metadata", JSON, default=dict, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, 
        default=datetime.utcnow, 
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    # Relación con mensajes
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, title='{self.title}')>"
    
    def to_dict(self):
        """Convierte el objeto a diccionario."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "title": self.title,
            "metadata": self.metadata_,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
