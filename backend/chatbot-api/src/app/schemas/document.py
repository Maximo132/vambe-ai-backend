from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, HttpUrl, ConfigDict
from enum import Enum

from app.models.document import DocumentType, DocumentStatus

class DocumentBase(BaseModel):
    """Base schema para documentos.
    
    Attributes:
        title: Título del documento
        description: Descripción opcional del documento
        file_url: URL del archivo (opcional, si se almacena externamente)
        file_type: Tipo de documento (PDF, DOCX, TXT, etc.)
        metadata: Metadatos adicionales en formato JSON
    """
    title: str = Field(..., max_length=255, description="Título del documento")
    description: Optional[str] = Field(
        None, 
        max_length=1000, 
        description="Descripción del documento"
    )
    file_url: Optional[HttpUrl] = Field(
        None, 
        description="URL del archivo (opcional, si se almacena externamente)"
    )
    file_type: DocumentType = Field(..., description="Tipo de documento")
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Metadatos adicionales en formato JSON"
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "title": "Documento de ejemplo",
                "description": "Este es un documento de ejemplo",
                "file_type": "pdf",
                "metadata": {"author": "Autor", "pages": 10}
            }
        }
    )

class DocumentCreate(DocumentBase):
    """Schema para crear un nuevo documento."""
    pass

class DocumentUpdate(BaseModel):
    """Schema para actualizar un documento existente."""
    title: Optional[str] = Field(
        None, 
        max_length=255, 
        description="Nuevo título del documento"
    )
    description: Optional[str] = Field(
        None, 
        max_length=1000, 
        description="Nueva descripción del documento"
    )
    status: Optional[DocumentStatus] = Field(
        None, 
        description="Nuevo estado del documento"
    )
    error_message: Optional[str] = Field(
        None, 
        description="Mensaje de error (si el procesamiento falló)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Metadatos adicionales en formato JSON"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Documento actualizado",
                "description": "Descripción actualizada",
                "status": "completed",
                "metadata": {"author": "Nuevo Autor"}
            }
        }
    )

class DocumentInDBBase(DocumentBase):
    """Base schema para documentos en la base de datos.
    
    Incluye campos de auditoría y estado.
    """
    id: int
    file_path: Optional[str] = Field(
        None, 
        description="Ruta al archivo en el sistema de archivos"
    )
    status: DocumentStatus = Field(
        default=DocumentStatus.PENDING,
        description="Estado actual del documento"
    )
    error_message: Optional[str] = Field(
        None, 
        description="Mensaje de error (si el procesamiento falló)"
    )
    created_at: datetime
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = Field(
        None,
        description="Fecha y hora en que se completó el procesamiento"
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Documento de ejemplo",
                "description": "Este es un documento de ejemplo",
                "file_type": "pdf",
                "file_path": "/uploads/documents/example.pdf",
                "status": "completed",
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:05:00",
                "processed_at": "2023-01-01T00:04:30",
                "metadata": {"author": "Autor", "pages": 10}
            }
        }
    )

class Document(DocumentInDBBase):
    """Schema para devolver datos de un documento."""
    pass

class DocumentInDB(DocumentInDBBase):
    """Schema para datos de documento en la base de datos."""
    pass

class DocumentProcessRequest(BaseModel):
    """Schema para solicitar el procesamiento de un documento.
    
    Se utiliza para iniciar el procesamiento de un documento existente.
    """
    knowledge_base_id: int = Field(
        ..., 
        description="ID de la base de conocimiento donde se indexará el documento"
    )
    chunk_size: int = Field(
        1000, 
        ge=100, 
        le=10000, 
        description="Tamaño de los fragmentos de texto (en caracteres)"
    )
    chunk_overlap: int = Field(
        200, 
        ge=0, 
        le=2000, 
        description="Superposición entre fragmentos (en caracteres)"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Metadatos adicionales para el procesamiento"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "knowledge_base_id": 1,
                "chunk_size": 1000,
                "chunk_overlap": 200,
                "metadata": {"language": "es", "category": "legal"}
            }
        }
    )

class DocumentProcessResponse(BaseModel):
    """Respuesta del procesamiento de un documento."""
    document_id: int = Field(..., description="ID del documento procesado")
    status: str = Field(..., description="Estado del procesamiento")
    message: str = Field(..., description="Mensaje descriptivo")
    chunks_processed: Optional[int] = Field(
        None, 
        description="Número de fragmentos procesados"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "document_id": 1,
                "status": "completed",
                "message": "Documento procesado exitosamente",
                "chunks_processed": 5
            }
        }
    )

class DocumentSearchQuery(BaseModel):
    """Schema para consultas de búsqueda de documentos."""
    query: str = Field(..., description="Consulta de búsqueda")
    knowledge_base_id: Optional[int] = Field(
        None, 
        description="ID de la base de conocimiento para buscar (opcional)"
    )
    limit: int = Field(
        10, 
        ge=1, 
        le=100, 
        description="Número máximo de resultados a devolver"
    )
    min_score: float = Field(
        0.5, 
        ge=0.0, 
        le=1.0, 
        description="Puntuación mínima de relevancia (0-1)"
    )
    filters: Optional[Dict[str, Any]] = Field(
        None,
        description="Filtros adicionales para la búsqueda (opcional)"
    )
    include_vectors: bool = Field(
        False,
        description="Incluir vectores de embedding en los resultados (para depuración)"
    )
    include_metadata: bool = Field(
        True,
        description="Incluir metadatos en los resultados"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "contrato de servicios",
                "knowledge_base_id": 1,
                "limit": 10,
                "min_score": 0.6,
                "filters": {"status": "completed"},
                "include_vectors": False,
                "include_metadata": True
            }
        }
    )

class DocumentSearchResult(BaseModel):
    """Resultado de búsqueda de un documento."""
    document: Document = Field(..., description="Documento encontrado")
    score: float = Field(..., description="Puntuación de relevancia (0-1)")
    chunk_text: Optional[str] = Field(
        None, 
        description="Fragmento de texto relevante"
    )
    chunk_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Metadatos del fragmento"
    )
    vector: Optional[List[float]] = Field(
        None,
        description="Vector de embedding del fragmento (solo para depuración)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "document": {
                    "id": 1,
                    "title": "Contrato de Servicios",
                    "file_type": "pdf",
                    "status": "completed",
                    "knowledge_bases": [
                        {
                            "id": 1,
                            "name": "Contratos",
                            "description": "Base de conocimiento para contratos legales",
                            "is_public": False,
                            "added_at": "2023-01-01T12:00:00",
                            "metadata": {"department": "legal"}
                        }
                    ]
                },
                "score": 0.85,
                "chunk_text": "... cláusulas del contrato de servicios ...",
                "chunk_metadata": {"page": 5, "section": "Términos y condiciones"},
                "vector": [0.1, 0.2, 0.3, ...]
            }
        }
    )

class DocumentSearchResults(BaseModel):
    """Resultados de búsqueda de documentos."""
    results: List[DocumentSearchResult] = Field(
        ..., 
        description="Lista de documentos encontrados"
    )
    total: int = Field(..., description="Número total de resultados")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "results": [
                    {
                        "document": {"id": 1, "title": "Contrato de Servicios"},
                        "score": 0.85,
                        "chunk_text": "... cláusulas del contrato ..."
                    }
                ],
                "total": 1
            }
        }
    )

class DocumentUploadResponse(DocumentInDB):
    """Respuesta para la carga de documentos."""
    message: str = Field(..., description="Mensaje descriptivo")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Documento cargado",
                "status": "pending",
                "message": "Documento cargado exitosamente y en cola para procesamiento"
            }
        }
    )
