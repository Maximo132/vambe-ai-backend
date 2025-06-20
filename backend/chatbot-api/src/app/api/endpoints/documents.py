from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select
from typing import List, Optional
import logging
import os
import uuid
from datetime import datetime

from ....db.session import get_db
from ....core.security import get_current_user
from ....models.document import Document as DocumentModel, DocumentType, DocumentStatus
from ....models.knowledge_base import KnowledgeBase, KnowledgeDocument
from ....schemas.document import (
    Document as DocumentSchema,
    DocumentInDB,
    DocumentCreate,
    DocumentUpdate,
    DocumentSearchResults,
    DocumentSearchQuery
)
from ....services.document_service import DocumentService
from ....services.knowledge_base_service import KnowledgeBaseService
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
    document_id: int,
    include_knowledge_bases: bool = Query(
        False, 
        description="Incluir información detallada de las bases de conocimiento asociadas"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene un documento por su ID con información detallada.
    
    Permite recuperar un documento específico junto con su contenido y, opcionalmente,
    información detallada de las bases de conocimiento a las que pertenece.
    
    Args:
        document_id: ID del documento a recuperar
        include_knowledge_bases: Incluir información detallada de las bases de conocimiento
        
    Returns:
        DocumentInDB: El documento solicitado con su información
        
    Raises:
        HTTPException: Si el documento no existe o no se tiene permiso para acceder a él
    """
    service = DocumentService(db)
    
    try:
        # Obtener el documento con las relaciones de knowledge_bases si es necesario
        document = await service.get(
            document_id, 
            user_id=current_user["id"],
            include_knowledge_bases=include_knowledge_bases
        )
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Documento con ID {document_id} no encontrado o sin permisos"
            )
        
        # Si el documento existe pero no tiene knowledge_bases cargadas y se solicitan
        if include_knowledge_bases and not hasattr(document, 'knowledge_bases'):
            # Cargar manualmente las relaciones de knowledge_bases
            stmt = (
                select(KnowledgeDocument)
                .where(KnowledgeDocument.document_id == document_id)
                .options(selectinload(KnowledgeDocument.knowledge_base))
            )
            
            result = await db.execute(stmt)
            knowledge_docs = result.scalars().all()
            
            # Agregar las knowledge_bases al documento
            document.knowledge_bases = [
                {
                    'id': kd.knowledge_base.id,
                    'name': kd.knowledge_base.name,
                    'description': kd.knowledge_base.description,
                    'is_public': kd.knowledge_base.is_public,
                    'added_at': kd.created_at.isoformat() if kd.created_at else None,
                    'metadata': kd.metadata or {}
                }
                for kd in knowledge_docs
            ]
        
        return document
        
    except HTTPException:
        # Re-lanzar excepciones HTTP existentes
        raise
        
    except Exception as e:
        logger.error(f"Error al obtener documento {document_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al recuperar el documento"
        )

@router.get("/", response_model=List[DocumentInDB])
async def list_documents(
    skip: int = 0,
    limit: int = Query(10, le=100, description="Número máximo de documentos a devolver (máx. 100)"),
    status: Optional[str] = Query(
        None, 
        description=f"Filtrar por estado del documento: {', '.join(e.value for e in DocumentStatus)}"
    ),
    doc_type: Optional[str] = Query(
        None, 
        description=f"Filtrar por tipo de documento: {', '.join(e.value for e in DocumentType)}"
    ),
    knowledge_base_id: Optional[int] = Query(
        None, 
        description="Filtrar por ID de base de conocimiento (opcional)"
    ),
    include_knowledge_bases: bool = Query(
        False, 
        description="Incluir información de bases de conocimiento en los resultados"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Lista los documentos del usuario con opciones de filtrado avanzado.
    
    Permite filtrar por estado, tipo de documento y base de conocimiento,
    así como incluir información detallada de las bases de conocimiento
    asociadas a cada documento.
    
    Args:
        skip: Número de documentos a omitir (paginación)
        limit: Número máximo de documentos a devolver (máx. 100)
        status: Filtrar por estado del documento (opcional)
        doc_type: Filtrar por tipo de documento (opcional)
        knowledge_base_id: Filtrar por ID de base de conocimiento (opcional)
        include_knowledge_bases: Incluir información detallada de bases de conocimiento
        
    Returns:
        List[DocumentInDB]: Lista de documentos que coinciden con los criterios
        
    Raises:
        HTTPException: Si hay errores de validación o permisos
    """
    service = DocumentService(db)
    
    # Validar y convertir parámetros
    try:
        # Convertir status a enum si se proporciona
        document_status = None
        if status:
            try:
                document_status = DocumentStatus(status)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Estado de documento no válido. Debe ser uno de: {', '.join(e.value for e in DocumentStatus)}"
                )
        
        # Convertir doc_type a enum si se proporciona
        document_type = None
        if doc_type:
            try:
                document_type = DocumentType(doc_type)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tipo de documento no válido. Debe ser uno de: {', '.join(e.value for e in DocumentType)}"
                )
        
        # Verificar permisos de knowledge_base_id si se proporciona
        kb_id = None
        if knowledge_base_id:
            kb_service = KnowledgeBaseService(db)
            knowledge_base = await kb_service.get(knowledge_base_id, current_user["id"])
            
            if not knowledge_base:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Base de conocimiento con ID {knowledge_base_id} no encontrada o sin permisos"
                )
            
            # Verificar permisos si la base no es pública
            if not knowledge_base.is_public and knowledge_base.owner_id != current_user["id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para acceder a esta base de conocimiento"
                )
            
            kb_id = knowledge_base_id
        
        # Obtener los documentos con los filtros aplicados
        documents = await service.get_multi(
            user_id=current_user["id"],
            skip=skip,
            limit=limit,
            status=document_status,
            doc_type=document_type,
            knowledge_base_id=kb_id,
            include_knowledge_bases=include_knowledge_bases
        )
        
        # Si no se solicitan las bases de conocimiento, quitarlas de los resultados
        if not include_knowledge_bases and documents:
            for doc in documents:
                if hasattr(doc, 'knowledge_bases'):
                    del doc.knowledge_bases
        
        return documents
        
    except HTTPException:
        # Re-lanzar excepciones HTTP existentes
        raise
        
    except Exception as e:
        logger.error(f"Error al listar documentos: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al recuperar los documentos"
        )

@router.post("/search", response_model=DocumentSearchResults)
async def search_documents(
    query: DocumentSearchQuery,
    knowledge_base_id: Optional[int] = Query(
        None, 
        description="Filtrar por ID de base de conocimiento (opcional)"
    ),
    include_knowledge_bases: bool = Query(
        False, 
        description="Incluir información de bases de conocimiento en los resultados"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Busca documentos relevantes para una consulta utilizando búsqueda semántica.
    
    La búsqueda utiliza embeddings para encontrar documentos semánticamente similares
    a la consulta, incluso si no comparten palabras clave exactas.
    
    Args:
        query: Parámetros de búsqueda incluyendo el texto de la consulta
        knowledge_base_id: Filtrar por ID de base de conocimiento (opcional)
        include_knowledge_bases: Si es True, incluye información de las bases de conocimiento
        
    Returns:
        DocumentSearchResults: Resultados de la búsqueda con documentos relevantes
    """
    service = DocumentService(db)
    
    try:
        # Verificar si se especificó un knowledge_base_id
        kb_id = knowledge_base_id or query.knowledge_base_id
        
        # Si se especifica un knowledge_base_id, verificar permisos
        if kb_id:
            kb_service = KnowledgeBaseService(db)
            knowledge_base = await kb_service.get(kb_id, current_user["id"])
            if not knowledge_base:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Base de conocimiento con ID {kb_id} no encontrada o sin permisos"
                )
            
            # Si el usuario no es el propietario y la base no es pública, denegar acceso
            if not knowledge_base.is_public and knowledge_base.owner_id != current_user["id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para acceder a esta base de conocimiento"
                )
        
        # Realizar la búsqueda
        search_results = await service.search_documents(
            query=query.query,
            user_id=current_user["id"],
            search_params=query,
            knowledge_base_id=kb_id
        )
        
        # Si no se solicitan las bases de conocimiento, quitarlas de los resultados
        if not include_knowledge_bases and search_results.results:
            for doc in search_results.results:
                if hasattr(doc, 'knowledge_bases'):
                    del doc.knowledge_bases
        
        return search_results
        
    except HTTPException:
        # Re-lanzar excepciones HTTP existentes
        raise
        
    except Exception as e:
        logger.error(f"Error en la búsqueda de documentos: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al realizar la búsqueda"
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
