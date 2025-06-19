from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.document import Document

class KnowledgeBaseBase(BaseModel):
    """Base schema para bases de conocimiento.
    
    Attributes:
        name: Nombre de la base de conocimiento
        description: Descripción opcional
        metadata: Metadatos adicionales en formato JSON
    """
    name: str = Field(..., max_length=255, description="Nombre de la base de conocimiento")
    description: Optional[str] = Field(
        None, 
        max_length=1000, 
        description="Descripción de la base de conocimiento"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Metadatos adicionales en formato JSON"
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "name": "Base de Conocimiento Legal",
                "description": "Documentos legales y normativas",
                "metadata": {"category": "legal", "language": "es"}
            }
        }
    )

class KnowledgeBaseCreate(KnowledgeBaseBase):
    """Schema para crear una nueva base de conocimiento."""
    pass

class KnowledgeBaseUpdate(BaseModel):
    """Schema para actualizar una base de conocimiento existente."""
    name: Optional[str] = Field(
        None, 
        max_length=255, 
        description="Nuevo nombre para la base de conocimiento"
    )
    description: Optional[str] = Field(
        None, 
        max_length=1000, 
        description="Nueva descripción"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Metadatos adicionales en formato JSON"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Base de Conocimiento Legal Actualizada",
                "description": "Documentos legales actualizados",
                "metadata": {"category": "legal", "language": "es", "version": "2.0"}
            }
        }
    )

class KnowledgeBaseInDBBase(KnowledgeBaseBase):
    """Base schema para bases de conocimiento en la base de datos.
    
    Incluye campos de auditoría.
    """
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Base de Conocimiento Legal",
                "description": "Documentos legales y normativas",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T12:00:00",
                "metadata": {"category": "legal", "language": "es"}
            }
        }
    )

class KnowledgeBase(KnowledgeBaseInDBBase):
    """Schema para devolver datos de una base de conocimiento.
    
    Incluye los documentos asociados.
    """
    documents: List[Document] = []
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Base de Conocimiento Legal",
                "description": "Documentos legales y normativas",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T12:00:00",
                "metadata": {"category": "legal"},
                "documents": [
                    {
                        "id": 1,
                        "title": "Ley de Protección de Datos",
                        "file_type": "pdf",
                        "status": "completed"
                    }
                ]
            }
        }
    )

class KnowledgeBaseInDB(KnowledgeBaseInDBBase):
    """Schema para datos de base de conocimiento en la base de datos."""
    pass

class KnowledgeDocumentBase(BaseModel):
    """Base schema para la relación entre documentos y bases de conocimiento."""
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Metadatos específicos para esta relación"
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "metadata": {"added_by": "admin@example.com", "access_level": "public"}
            }
        }
    )

class KnowledgeDocumentCreate(KnowledgeDocumentBase):
    """Schema para asociar un documento a una base de conocimiento."""
    document_id: int = Field(..., description="ID del documento a asociar")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "document_id": 1,
                "metadata": {"added_by": "admin@example.com"}
            }
        }
    )

class KnowledgeDocument(KnowledgeDocumentBase):
    """Schema para la relación entre documentos y bases de conocimiento."""
    id: int
    knowledge_base_id: int
    document: Document
    created_at: datetime
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "knowledge_base_id": 1,
                "document": {
                    "id": 1,
                    "title": "Ley de Protección de Datos",
                    "file_type": "pdf"
                },
                "created_at": "2023-01-01T00:00:00",
                "metadata": {"added_by": "admin@example.com"}
            }
        }
    )

class KnowledgeBaseStats(BaseModel):
    """Estadísticas de una base de conocimiento."""
    total_documents: int = Field(..., description="Número total de documentos")
    documents_by_status: Dict[str, int] = Field(
        ..., 
        description="Conteo de documentos por estado"
    )
    documents_by_type: Dict[str, int] = Field(
        ..., 
        description="Conteo de documentos por tipo"
    )
    total_chunks: int = Field(
        ..., 
        description="Número total de fragmentos indexados"
    )
    last_updated: Optional[datetime] = Field(
        None, 
        description="Fecha de la última actualización"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_documents": 15,
                "documents_by_status": {"completed": 12, "processing": 2, "failed": 1},
                "documents_by_type": {"pdf": 10, "docx": 5},
                "total_chunks": 245,
                "last_updated": "2023-01-01T12:00:00"
            }
        }
    )
