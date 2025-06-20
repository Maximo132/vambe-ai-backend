import enum
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, JSON, Enum
from sqlalchemy.orm import relationship
from app.models.base import Base
from app.models.enums import MessageRole  # Importar desde enums.py

class ConversationStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"

class MessageType(str, enum.Enum):
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(String(36), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    status = Column(Enum(ConversationStatus), default=ConversationStatus.ACTIVE)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversation {self.id} - {self.title}>"

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(String(36), primary_key=True, index=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)
    message_type = Column(Enum(MessageType), default=MessageType.TEXT)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self):
        return f"<Message {self.id} - {self.role}>"
