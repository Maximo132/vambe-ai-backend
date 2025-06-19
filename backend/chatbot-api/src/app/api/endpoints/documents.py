from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import os
import uuid
from datetime import datetime

from ....db.session import get_db
from ....core.security import get_current_user
from ....schemas.document import (
    Document as DocumentSchema,
    DocumentInDB,
    DocumentCreate,
    DocumentUpdate,
    DocumentSearchResults,
    DocumentSearchQuery
)
from ....services.document_service import DocumentService
from ....services.weaviate_service import weaviate_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/upload", response_model=DocumentInDB, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    source: str = Form(""),
    metadata: str = Form("{}"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Sube un documento para su indexación y procesamiento
    """
    try:
        # Validar el tipo de archivo
        allowed_extensions = {".pdf", ".txt", ".docx", ".md"}
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tipo de archivo no soportado. Formatos permitidos: {', '.join(allowed_extensions)}"
            )
        
        # Leer el contenido del archivo
        content = await file.read()
        
        # Procesar el documento según su tipo
        document_service = DocumentService(db)
        processed_doc = await document_service.process_uploaded_file(
            filename=file.filename,
            content=content,
            content_type=file.content_type
        )
        
        # Crear documento en la base de datos
        doc_data = DocumentCreate(
            title=title,
            content=processed_doc["content"],
            source=source or file.filename,
            doc_type=file_extension.lstrip("."),
            size=len(content),
            metadata={"original_metadata": metadata},
            user_id=current_user["username"]
        )
        
        db_doc = document_service.create_document(doc_data)
        
        # Indexar en Weaviate
        weaviate_doc = {
            "content": processed_doc["content"],
            "title": title,
            "source": source or file.filename,
            "doc_id": str(db_doc.id),
            "metadata": {"type": file_extension.lstrip("."), "original_metadata": metadata},
            "user_id": current_user["username"],
            "created_at": datetime.utcnow().isoformat()
        }
        
        await weaviate_service.index_document(weaviate_doc)
        
        return db_doc
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al subir documento: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar el documento: {str(e)}"
        )

@router.get("/{document_id}", response_model=DocumentInDB)
async def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene un documento por su ID
    """
    document_service = DocumentService(db)
    db_doc = document_service.get_document(document_id, current_user["username"])
    
    if not db_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado"
        )
    
    return db_doc

@router.get("/", response_model=List[DocumentInDB])
async def list_documents(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Lista los documentos del usuario
    """
    document_service = DocumentService(db)
    return document_service.get_user_documents(
        user_id=current_user["username"],
        skip=skip,
        limit=limit
    )

@router.post("/search", response_model=DocumentSearchResults)
async def search_documents(
    query: DocumentSearchQuery,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Busca documentos relevantes para una consulta
    """
    try:
        # Buscar en Weaviate
        search_results = await weaviate_service.search_documents(
            query=query.query,
            user_id=current_user["username"],
            limit=query.limit,
            certainty=query.min_score
        )
        
        # Obtener documentos completos de la base de datos
        document_service = DocumentService(db)
        results = []
        
        for result in search_results:
            doc = document_service.get_document_by_weaviate_id(
                result.id, 
                current_user["username"]
            )
            if doc:
                results.append({
                    "document": doc,
                    "score": result.score
                })
        
        return {"results": results, "total": len(results)}
        
    except Exception as e:
        logger.error(f"Error en la búsqueda: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al realizar la búsqueda: {str(e)}"
        )

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Elimina un documento
    """
    document_service = DocumentService(db)
    db_doc = document_service.get_document(document_id, current_user["username"])
    
    if not db_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado"
        )
    
    try:
        # Eliminar de Weaviate
        await weaviate_service.delete_document(db_doc.weaviate_id)
        
        # Eliminar de la base de datos
        document_service.delete_document(document_id, current_user["username"])
        
        return {"status": "success", "message": "Documento eliminado correctamente"}
        
    except Exception as e:
        logger.error(f"Error al eliminar documento: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el documento: {str(e)}"
        )
