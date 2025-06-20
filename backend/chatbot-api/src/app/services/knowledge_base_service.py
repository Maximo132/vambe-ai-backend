from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import logging
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, func, desc

from app.models.knowledge_base import KnowledgeBase, KnowledgeDocument
from app.models.document import Document, DocumentStatus
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeDocumentCreate,
    KnowledgeBaseStats
)
from app.core.security import get_password_hash
from app.core.config import settings
from app.services.base import BaseService
from app.services.weaviate_service import weaviate_service

logger = logging.getLogger(__name__)

class KnowledgeBaseService(BaseService[KnowledgeBase, KnowledgeBaseCreate, KnowledgeBaseUpdate]):
    """
    Servicio para la gestión de bases de conocimiento.
    
    Permite crear, actualizar, eliminar y consultar bases de conocimiento,
    así como gestionar los documentos asociados a cada una.
    """
    
    def __init__(self, db: Session):
        super().__init__(KnowledgeBase, db)
    
    async def create(
        self, 
        obj_in: KnowledgeBaseCreate, 
        user_id: int,
        **kwargs
    ) -> KnowledgeBase:
        """
        Crea una nueva base de conocimiento.
        
        Args:
            obj_in: Datos para crear la base de conocimiento
            user_id: ID del usuario propietario
            
        Returns:
            KnowledgeBase: La base de conocimiento creada
        """
        db_obj = KnowledgeBase(
            name=obj_in.name,
            description=obj_in.description,
            metadata=obj_in.metadata or {},
            owner_id=user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        
        return db_obj
    
    async def update(
        self, 
        id: int, 
        obj_in: Union[KnowledgeBaseUpdate, Dict[str, Any]],
        user_id: int,
        **kwargs
    ) -> Optional[KnowledgeBase]:
        """
        Actualiza una base de conocimiento existente.
        
        Args:
            id: ID de la base de conocimiento a actualizar
            obj_in: Datos de actualización
            user_id: ID del usuario que realiza la actualización
            
        Returns:
            KnowledgeBase: La base de conocimiento actualizada o None si no se encontró
        """
        db_obj = await self.get(id, user_id)
        if not db_obj:
            return None
            
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        
        # Actualizar solo los campos proporcionados
        for field, value in update_data.items():
            if field != 'id' and hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        db_obj.updated_at = datetime.utcnow()
        
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        
        return db_obj
    
    async def get_user_knowledge_bases(
        self, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[KnowledgeBase]:
        """
        Obtiene las bases de conocimiento de un usuario.
        
        Args:
            user_id: ID del usuario
            skip: Número de registros a omitir (para paginación)
            limit: Número máximo de registros a devolver
            
        Returns:
            List[KnowledgeBase]: Lista de bases de conocimiento del usuario
        """
        result = await self.db.execute(
            select(KnowledgeBase)
            .where(KnowledgeBase.owner_id == user_id)
            .order_by(desc(KnowledgeBase.updated_at))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def add_document(
        self,
        knowledge_base_id: int,
        document_data: KnowledgeDocumentCreate,
        user_id: int
    ) -> Optional[KnowledgeDocument]:
        """
        Agrega un documento a una base de conocimiento.
        
        Args:
            knowledge_base_id: ID de la base de conocimiento
            document_data: Datos del documento a agregar
            user_id: ID del usuario que realiza la operación
            
        Returns:
            KnowledgeDocument: La relación creada o None si hubo un error
        """
        # Verificar que la base de conocimiento exista y pertenezca al usuario
        knowledge_base = await self.db.get(KnowledgeBase, knowledge_base_id)
        if not knowledge_base or knowledge_base.owner_id != user_id:
            return None
        
        # Verificar que el documento exista
        document = await self.db.get(Document, document_data.document_id)
        if not document:
            return None
        
        # Verificar si el documento ya está en la base de conocimiento
        existing = await self.db.execute(
            select(KnowledgeDocument)
            .where(
                and_(
                    KnowledgeDocument.knowledge_base_id == knowledge_base_id,
                    KnowledgeDocument.document_id == document_data.document_id
                )
            )
        )
        
        if existing.scalar_one_or_none() is not None:
            raise ValueError("El documento ya está en la base de conocimiento")
        
        # Crear la relación
        knowledge_doc = KnowledgeDocument(
            knowledge_base_id=knowledge_base_id,
            document_id=document_data.document_id,
            metadata=document_data.metadata or {},
            created_at=datetime.utcnow()
        )
        
        self.db.add(knowledge_doc)
        
        # Actualizar la fecha de modificación de la base de conocimiento
        knowledge_base.updated_at = datetime.utcnow()
        self.db.add(knowledge_base)
        
        await self.db.commit()
        await self.db.refresh(knowledge_doc)
        
        return knowledge_doc
    
    async def remove_document(
        self,
        knowledge_base_id: int,
        document_id: int,
        user_id: int
    ) -> bool:
        """
        Elimina un documento de una base de conocimiento.
        
        Args:
            knowledge_base_id: ID de la base de conocimiento
            document_id: ID del documento a eliminar
            user_id: ID del usuario que realiza la operación
            
        Returns:
            bool: True si se eliminó correctamente, False en caso contrario
        """
        # Verificar que la base de conocimiento exista y pertenezca al usuario
        knowledge_base = await self.db.get(KnowledgeBase, knowledge_base_id)
        if not knowledge_base or knowledge_base.owner_id != user_id:
            return False
        
        # Buscar y eliminar la relación
        result = await self.db.execute(
            select(KnowledgeDocument)
            .where(
                and_(
                    KnowledgeDocument.knowledge_base_id == knowledge_base_id,
                    KnowledgeDocument.document_id == document_id
                )
            )
        )
        
        knowledge_doc = result.scalar_one_or_none()
        if not knowledge_doc:
            return False
        
        await self.db.delete(knowledge_doc)
        
        # Actualizar la fecha de modificación de la base de conocimiento
        knowledge_base.updated_at = datetime.utcnow()
        self.db.add(knowledge_base)
        
        await self.db.commit()
        return True
    
    async def get_stats(self, knowledge_base_id: int, user_id: int) -> Optional[KnowledgeBaseStats]:
        """
        Obtiene estadísticas de una base de conocimiento.
        
        Args:
            knowledge_base_id: ID de la base de conocimiento
            user_id: ID del usuario que realiza la consulta
            
        Returns:
            KnowledgeBaseStats: Estadísticas de la base de conocimiento o None si no se encontró
        """
        # Verificar que la base de conocimiento exista y pertenezca al usuario
        knowledge_base = await self.db.get(KnowledgeBase, knowledge_base_id)
        if not knowledge_base or knowledge_base.owner_id != user_id:
            return None
        
        # Obtener el número total de documentos
        total_docs = await self.db.scalar(
            select(func.count(KnowledgeDocument.document_id))
            .where(KnowledgeDocument.knowledge_base_id == knowledge_base_id)
        )
        
        # Obtener el conteo de documentos por estado
        status_count = await self.db.execute(
            select(
                Document.status,
                func.count(Document.id)
            )
            .select_from(KnowledgeDocument)
            .join(Document, KnowledgeDocument.document_id == Document.id)
            .where(KnowledgeDocument.knowledge_base_id == knowledge_base_id)
            .group_by(Document.status)
        )
        
        documents_by_status = {status: count for status, count in status_count.all()}
        
        # Obtener el conteo de documentos por tipo
        type_count = await self.db.execute(
            select(
                Document.doc_type,
                func.count(Document.id)
            )
            .select_from(KnowledgeDocument)
            .join(Document, KnowledgeDocument.document_id == Document.id)
            .where(KnowledgeDocument.knowledge_base_id == knowledge_base_id)
            .group_by(Document.doc_type)
        )
        
        documents_by_type = {doc_type: count for doc_type, count in type_count.all()}
        
        # Obtener el número total de fragmentos (asumiendo que está almacenado en metadata)
        # Esto es un ejemplo, ajusta según tu implementación
        total_chunks = await self.db.scalar(
            select(func.sum(Document.metadata['chunk_count'].as_integer()))
            .select_from(KnowledgeDocument)
            .join(Document, KnowledgeDocument.document_id == Document.id)
            .where(KnowledgeDocument.knowledge_base_id == knowledge_base_id)
        ) or 0
        
        return KnowledgeBaseStats(
            total_documents=total_docs or 0,
            documents_by_status=documents_by_status,
            documents_by_type=documents_by_type,
            total_chunks=total_chunks,
            last_updated=knowledge_base.updated_at
        )
    
    async def search_documents(
        self,
        knowledge_base_id: int,
        query: str,
        user_id: int,
        limit: int = 10,
        min_score: float = 0.5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca documentos dentro de una base de conocimiento.
        
        Args:
            knowledge_base_id: ID de la base de conocimiento
            query: Texto de búsqueda
            user_id: ID del usuario que realiza la búsqueda
            limit: Número máximo de resultados
            min_score: Puntuación mínima de relevancia
            filters: Filtros adicionales para la búsqueda
            
        Returns:
            List[Dict[str, Any]]: Lista de documentos encontrados con metadatos
        """
        # Verificar que la base de conocimiento exista y pertenezca al usuario
        knowledge_base = await self.db.get(KnowledgeBase, knowledge_base_id)
        if not knowledge_base or knowledge_base.owner_id != user_id:
            return []
        
        # Obtener los IDs de los documentos en la base de conocimiento
        result = await self.db.execute(
            select(KnowledgeDocument.document_id)
            .where(KnowledgeDocument.knowledge_base_id == knowledge_base_id)
        )
        document_ids = [str(doc_id) for (doc_id,) in result.all()]
        
        if not document_ids:
            return []
        
        # Aplicar filtros adicionales
        search_filters = {"id": document_ids}
        if filters:
            search_filters.update(filters)
        
        # Realizar la búsqueda semántica en Weaviate
        search_results = await weaviate_service.semantic_search(
            query=query,
            user_id=user_id,
            limit=limit,
            min_score=min_score,
            filters=search_filters
        )
        
        # Obtener los documentos completos de la base de datos
        result_docs = []
        for doc in search_results:
            doc_id = doc.get('_additional', {}).get('id')
            if doc_id and doc_id in document_ids:
                result_docs.append({
                    'document': doc,
                    'score': doc.get('_additional', {}).get('score', 0),
                    'chunk_text': doc.get('content', '')[:500] + '...' if doc.get('content') else '',
                    'chunk_metadata': doc.get('metadata', {})
                })
        
        return result_docs
