from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from ....db.session import get_db
from ....core.security import get_current_user
from ....schemas.knowledge_base import (
    KnowledgeBase as KnowledgeBaseSchema,
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseInDB,
    KnowledgeDocument,
    KnowledgeDocumentCreate,
    KnowledgeBaseStats
)
from ....services.knowledge_base_service import KnowledgeBaseService

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post(
    "/", 
    response_model=KnowledgeBaseInDB, 
    status_code=status.HTTP_201_CREATED
)
async def create_knowledge_base(
    knowledge_base: KnowledgeBaseCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Crea una nueva base de conocimiento.
    
    Args:
        knowledge_base: Datos de la base de conocimiento a crear
        
    Returns:
        KnowledgeBaseInDB: La base de conocimiento creada
    """
    service = KnowledgeBaseService(db)
    try:
        db_kb = await service.create(
            obj_in=knowledge_base,
            user_id=current_user["id"]
        )
        return db_kb
    except Exception as e:
        logger.error(f"Error al crear la base de conocimiento: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al crear la base de conocimiento"
        )

@router.get(
    "/{knowledge_base_id}", 
    response_model=KnowledgeBaseInDB
)
async def get_knowledge_base(
    knowledge_base_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene una base de conocimiento por su ID.
    
    Args:
        knowledge_base_id: ID de la base de conocimiento
        
    Returns:
        KnowledgeBaseInDB: La base de conocimiento solicitada
    """
    service = KnowledgeBaseService(db)
    kb = await service.get(knowledge_base_id, current_user["id"])
    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Base de conocimiento no encontrada"
        )
    return kb

@router.put(
    "/{knowledge_base_id}", 
    response_model=KnowledgeBaseInDB
)
async def update_knowledge_base(
    knowledge_base_id: int,
    knowledge_base: KnowledgeBaseUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Actualiza una base de conocimiento existente.
    
    Args:
        knowledge_base_id: ID de la base de conocimiento a actualizar
        knowledge_base: Datos de actualización
        
    Returns:
        KnowledgeBaseInDB: La base de conocimiento actualizada
    """
    service = KnowledgeBaseService(db)
    updated_kb = await service.update(
        id=knowledge_base_id,
        obj_in=knowledge_base,
        user_id=current_user["id"]
    )
    
    if not updated_kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Base de conocimiento no encontrada"
        )
    
    return updated_kb

@router.delete(
    "/{knowledge_base_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_knowledge_base(
    knowledge_base_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Elimina una base de conocimiento.
    
    Args:
        knowledge_base_id: ID de la base de conocimiento a eliminar
    """
    service = KnowledgeBaseService(db)
    success = await service.delete(knowledge_base_id, current_user["id"])
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Base de conocimiento no encontrada"
        )

@router.get(
    "/", 
    response_model=List[KnowledgeBaseInDB]
)
async def list_knowledge_bases(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros a devolver"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Lista las bases de conocimiento del usuario.
    
    Args:
        skip: Número de registros a omitir
        limit: Número máximo de registros a devolver
        
    Returns:
        List[KnowledgeBaseInDB]: Lista de bases de conocimiento del usuario
    """
    service = KnowledgeBaseService(db)
    return await service.get_user_knowledge_bases(
        user_id=current_user["id"],
        skip=skip,
        limit=limit
    )

@router.post(
    "/{knowledge_base_id}/documents",
    response_model=KnowledgeDocument,
    status_code=status.HTTP_201_CREATED
)
async def add_document_to_knowledge_base(
    knowledge_base_id: int,
    document_data: KnowledgeDocumentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Agrega un documento a una base de conocimiento.
    
    Args:
        knowledge_base_id: ID de la base de conocimiento
        document_data: Datos del documento a agregar
        
    Returns:
        KnowledgeDocument: La relación creada entre el documento y la base de conocimiento
    """
    service = KnowledgeBaseService(db)
    try:
        return await service.add_document(
            knowledge_base_id=knowledge_base_id,
            document_data=document_data,
            user_id=current_user["id"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error al agregar documento a la base de conocimiento: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al agregar el documento a la base de conocimiento"
        )

@router.delete(
    "/{knowledge_base_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def remove_document_from_knowledge_base(
    knowledge_base_id: int,
    document_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Elimina un documento de una base de conocimiento.
    
    Args:
        knowledge_base_id: ID de la base de conocimiento
        document_id: ID del documento a eliminar
    """
    service = KnowledgeBaseService(db)
    success = await service.remove_document(
        knowledge_base_id=knowledge_base_id,
        document_id=document_id,
        user_id=current_user["id"]
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento o base de conocimiento no encontrados"
        )

@router.get(
    "/{knowledge_base_id}/stats",
    response_model=KnowledgeBaseStats
)
async def get_knowledge_base_stats(
    knowledge_base_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene estadísticas de una base de conocimiento.
    
    Args:
        knowledge_base_id: ID de la base de conocimiento
        
    Returns:
        KnowledgeBaseStats: Estadísticas de la base de conocimiento
    """
    service = KnowledgeBaseService(db)
    stats = await service.get_stats(knowledge_base_id, current_user["id"])
    
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Base de conocimiento no encontrada"
        )
    
    return stats

@router.get(
    "/{knowledge_base_id}/search",
    response_model=List[dict]
)
async def search_in_knowledge_base(
    knowledge_base_id: int,
    query: str = Query(..., min_length=1, description="Término de búsqueda"),
    limit: int = Query(10, ge=1, le=100, description="Número máximo de resultados"),
    min_score: float = Query(0.5, ge=0.0, le=1.0, description="Puntuación mínima de relevancia"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Busca documentos dentro de una base de conocimiento.
    
    Args:
        knowledge_base_id: ID de la base de conocimiento
        query: Término de búsqueda
        limit: Número máximo de resultados
        min_score: Puntuación mínima de relevancia (0-1)
        
    Returns:
        List[dict]: Lista de documentos que coinciden con la búsqueda
    """
    service = KnowledgeBaseService(db)
    
    try:
        results = await service.search_documents(
            knowledge_base_id=knowledge_base_id,
            query=query,
            user_id=current_user["id"],
            limit=limit,
            min_score=min_score
        )
        return results
    except Exception as e:
        logger.error(f"Error en la búsqueda: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al realizar la búsqueda"
        )
