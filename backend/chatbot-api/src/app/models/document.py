from sqlalchemy import Column, String, Text, Integer, JSON, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base

class Document(Base):
    """
    Modelo para almacenar documentos cargados por los usuarios
    """
    __tablename__ = "documents"
    
    id = Column(String(50), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)  # Contenido de texto extraído
    source = Column(String(500), nullable=True)  # URL o ruta del archivo
    doc_type = Column(String(50), nullable=True)  # pdf, docx, txt, etc.
    size = Column(Integer, nullable=True)  # Tamaño en bytes
    document_metadata = Column('metadata', JSON, nullable=True, default=dict)  # Metadatos adicionales
    weaviate_id = Column(String(100), nullable=True, index=True)  # ID en Weaviate
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False, index=True)
    
    # Relaciones
    user = relationship("User", back_populates="documents")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title='{self.title}')>"
