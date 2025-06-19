from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum

class DocumentType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MARKDOWN = "markdown"
    OTHER = "other"

class DocumentBase(BaseModel):
    """Esquema base para documentos"""
    title: str = Field(..., max_length=255, description="Título del documento")
    content: Optional[str] = Field(None, description="Contenido de texto del documento")
    source: Optional[str] = Field(None, max_length=500, description="Fuente u origen del documento")
    doc_type: Optional[DocumentType] = Field(None, description="Tipo de documento")
    size: Optional[int] = Field(None, ge=0, description="Tamaño del documento en bytes")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadatos adicionales")

class DocumentCreate(DocumentBase):
    """Esquema para la creación de documentos"""
    user_id: str = Field(..., description="ID del usuario propietario del documento")

class DocumentUpdate(BaseModel):
    """Esquema para la actualización de documentos"""
    title: Optional[str] = Field(None, max_length=255, description="Nuevo título del documento")
    source: Optional[str] = Field(None, max_length=500, description="Nueva fuente del documento")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadatos actualizados")

class DocumentInDBBase(DocumentBase):
    """Esquema base para documentos en la base de datos"""
    id: str
    user_id: str
    weaviate_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class DocumentInDB(DocumentInDBBase):
    """Esquema para documentos en la base de datos"""
    pass

class DocumentSearchQuery(BaseModel):
    """Esquema para consultas de búsqueda de documentos"""
    query: str = Field(..., description="Consulta de búsqueda")
    limit: int = Field(10, ge=1, le=50, description="Número máximo de resultados")
    min_score: float = Field(0.5, ge=0.0, le=1.0, description="Puntuación mínima de relevancia")

class DocumentSearchResult(BaseModel):
    """Resultado de búsqueda de un documento"""
    document: DocumentInDB
    score: float

class DocumentSearchResults(BaseModel):
    """Resultados de búsqueda de documentos"""
    results: List[DocumentSearchResult]
    total: int

class DocumentUploadResponse(DocumentInDB):
    """Respuesta para la carga de documentos"""
    message: str = "Documento cargado exitosamente"

# Alias para compatibilidad
Document = DocumentInDB
