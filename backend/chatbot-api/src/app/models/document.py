from enum import Enum
from sqlalchemy import Column, String, Text, Integer, JSON, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base

class DocumentType(str, Enum):
    """Tipos de documentos soportados."""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    CSV = "csv"
    XLSX = "xlsx"
    PPTX = "pptx"
    HTML = "html"
    JSON = "json"
    XML = "xml"
    MD = "md"
    OTHER = "other"

class DocumentStatus(str, Enum):
    """Estados posibles de un documento."""
    PENDING = "pending"  # En cola para procesar
    PROCESSING = "processing"  # Procesamiento en curso
    COMPLETED = "completed"  # Procesamiento exitoso
    FAILED = "failed"  # Error en el procesamiento
    DELETED = "deleted"  # Documento eliminado

class Document(Base):
    """
    Modelo para almacenar documentos cargados por los usuarios
    """
    __tablename__ = "documents"
    
    id = Column(String(50), primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)  # Contenido de texto extraído
    source = Column(String(500), nullable=True)  # URL o ruta del archivo
    doc_type = Column(SQLEnum(DocumentType), nullable=True)  # Tipo de documento
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False)  # Estado del documento
    size = Column(Integer, nullable=True)  # Tamaño en bytes
    document_metadata = Column('metadata', JSON, nullable=True, default=dict)  # Metadatos adicionales
    weaviate_id = Column(String(100), nullable=True, index=True)  # ID en Weaviate
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False, index=True)
    error_message = Column(Text, nullable=True)  # Mensaje de error si el procesamiento falla
    processed_at = Column(DateTime(timezone=True), nullable=True)  # Fecha de procesamiento
    
    # Relaciones
    user = relationship("User", back_populates="documents")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<Document(id={self.id}, title='{self.title}')>"
