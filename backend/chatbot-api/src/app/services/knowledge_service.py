import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Union, AsyncGenerator
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.knowledge_base import KnowledgeBase, KnowledgeDocument, KnowledgeBaseStatus
from app.models.document import Document as DocumentModel, DocumentStatus
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate, KnowledgeBaseUpdate, KnowledgeBaseInDB,
    KnowledgeDocumentCreate, KnowledgeDocumentInDB, KnowledgeBaseStats,
    KnowledgeBaseWithDocuments, KnowledgeDocumentWithContent
)
from app.services.base import CRUDBase
from app.services.document_service import DocumentService
from app.services.openai_service import openai_service
from app.services.weaviate_service import weaviate_service

logger = logging.getLogger(__name__)

class KnowledgeBaseService(CRUDBase[KnowledgeBase, KnowledgeBaseCreate, KnowledgeBaseUpdate]):
    """
    Servicio para la gestión de bases de conocimiento.
    Permite crear, actualizar, eliminar y consultar bases de conocimiento,
    así como gestionar los documentos asociados a cada una.
    """
    
    def __init__(self, db: AsyncSession):
        super().__init__(KnowledgeBase, db)
        self.document_service = DocumentService(db)
    
    async def create_with_owner(
        self, 
        obj_in: KnowledgeBaseCreate, 
        owner_id: int,
        **kwargs
    ) -> KnowledgeBaseInDB:
        """
        Crea una nueva base de conocimiento para un propietario específico.
        
        Args:
            obj_in: Datos para crear la base de conocimiento
            owner_id: ID del usuario propietario
            
        Returns:
            KnowledgeBaseInDB: La base de conocimiento creada
        """
        db_obj = KnowledgeBase(
            **obj_in.dict(exclude={"document_ids"}),
            owner_id=owner_id,
            status=KnowledgeBaseStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata=obj_in.metadata or {}
        )
        
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        
        # Si se proporcionaron documentos, asociarlos
        if obj_in.document_ids:
            await self.add_documents(
                knowledge_base_id=db_obj.id,
                document_ids=obj_in.document_ids,
                user_id=owner_id
            )
        
        return db_obj
    
    async def update(
        self, 
        id: int, 
        obj_in: Union[KnowledgeBaseUpdate, Dict[str, Any]],
        user_id: int,
        **kwargs
    ) -> Optional[KnowledgeBaseInDB]:
        """
        Actualiza una base de conocimiento existente.
        
        Args:
            id: ID de la base de conocimiento
            obj_in: Datos a actualizar
            user_id: ID del usuario que realiza la actualización
            
        Returns:
            KnowledgeBaseInDB: La base de conocimiento actualizada o None si no existe
        """
        db_obj = await self.get(id, user_id=user_id)
        if not db_obj:
            return None
            
        update_data = obj_in.dict(exclude_unset=True) if not isinstance(obj_in, dict) else obj_in
        
        # Actualizar campos básicos
        for field, value in update_data.items():
            if field != "document_ids":
                setattr(db_obj, field, value)
        
        db_obj.updated_at = datetime.utcnow()
        
        # Si se proporcionaron documentos, actualizar las asociaciones
        if "document_ids" in update_data and update_data["document_ids"] is not None:
            # Obtener los documentos actuales
            current_docs = await self.get_documents(db_obj.id, user_id)
            current_doc_ids = {doc.id for doc in current_docs}
            new_doc_ids = set(update_data["document_ids"])
            
            # Documentos a añadir
            to_add = new_doc_ids - current_doc_ids
            if to_add:
                await self.add_documents(db_obj.id, list(to_add), user_id)
            
            # Documentos a eliminar
            to_remove = current_doc_ids - new_doc_ids
            if to_remove:
                await self.remove_documents(db_obj.id, list(to_remove), user_id)
        
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        
        return db_obj
    
    async def get_with_documents(
        self, 
        id: int, 
        user_id: int,
        include_content: bool = False
    ) -> Optional[KnowledgeBaseWithDocuments]:
        """
        Obtiene una base de conocimiento con sus documentos asociados.
        
        Args:
            id: ID de la base de conocimiento
            user_id: ID del usuario que realiza la consulta
            include_content: Si es True, incluye el contenido de los documentos
            
        Returns:
            KnowledgeBaseWithDocuments: La base de conocimiento con sus documentos
        """
        # Obtener la base de conocimiento
        knowledge_base = await self.get(id, user_id=user_id)
        if not knowledge_base:
            return None
        
        # Obtener los documentos asociados
        documents = await self.get_documents(id, user_id, include_content=include_content)
        
        # Obtener estadísticas
        stats = await self.get_stats(id, user_id)
        
        return KnowledgeBaseWithDocuments(
            **knowledge_base.dict(),
            documents=documents,
            stats=stats
        )
    
    async def get_documents(
        self, 
        knowledge_base_id: int, 
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        include_content: bool = False
    ) -> List[Union[KnowledgeDocumentInDB, KnowledgeDocumentWithContent]]:
        """
        Obtiene los documentos asociados a una base de conocimiento.
        
        Args:
            knowledge_base_id: ID de la base de conocimiento
            user_id: ID del usuario que realiza la consulta
            skip: Número de documentos a saltar (para paginación)
            limit: Número máximo de documentos a devolver
            include_content: Si es True, incluye el contenido de los documentos
            
        Returns:
            Lista de documentos asociados a la base de conocimiento
        """
        # Verificar que el usuario tenga acceso a la base de conocimiento
        kb = await self.get(knowledge_base_id, user_id=user_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Base de conocimiento no encontrada o acceso denegado"
            )
        
        # Construir la consulta
        query = select(KnowledgeDocument).where(
            KnowledgeDocument.knowledge_base_id == knowledge_base_id
        ).offset(skip).limit(limit)
        
        if include_content:
            query = query.join(DocumentModel, KnowledgeDocument.document_id == DocumentModel.id)
            query = query.add_columns(DocumentModel.content)
        
        result = await self.db.execute(query)
        
        if include_content:
            return [
                KnowledgeDocumentWithContent(
                    **doc[0].__dict__,
                    content=doc[1]
                )
                for doc in result.all()
            ]
        else:
            return [doc[0] for doc in result.all()]
    
    async def add_documents(
        self, 
        knowledge_base_id: int, 
        document_ids: List[int],
        user_id: int
    ) -> List[KnowledgeDocumentInDB]:
        """
        Añade documentos a una base de conocimiento.
        
        Args:
            knowledge_base_id: ID de la base de conocimiento
            document_ids: Lista de IDs de documentos a añadir
            user_id: ID del usuario que realiza la operación
            
        Returns:
            Lista de asociaciones creadas
        """
        # Verificar que la base de conocimiento exista y el usuario tenga acceso
        kb = await self.get(knowledge_base_id, user_id=user_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Base de conocimiento no encontrada o acceso denegado"
            )
        
        # Verificar que los documentos existan y pertenezcan al usuario
        result = await self.db.execute(
            select(DocumentModel).where(
                and_(
                    DocumentModel.id.in_(document_ids),
                    DocumentModel.user_id == user_id,
                    DocumentModel.status == DocumentStatus.COMPLETED
                )
            )
        )
        
        valid_documents = {doc.id: doc for doc in result.scalars().all()}
        
        # Verificar que todos los documentos solicitados sean válidos
        invalid_docs = set(document_ids) - valid_documents.keys()
        if invalid_docs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Los siguientes documentos no son válidos o no están disponibles: {invalid_docs}"
            )
        
        # Verificar qué documentos ya están en la base de conocimiento
        existing = await self.db.execute(
            select(KnowledgeDocument).where(
                and_(
                    KnowledgeDocument.knowledge_base_id == knowledge_base_id,
                    KnowledgeDocument.document_id.in_(document_ids)
                )
            )
        )
        
        existing_doc_ids = {doc.document_id for doc in existing.scalars().all()}
        
        # Crear solo las asociaciones que no existen
        to_add = []
        for doc_id in document_ids:
            if doc_id not in existing_doc_ids:
                to_add.append(KnowledgeDocument(
                    knowledge_base_id=knowledge_base_id,
                    document_id=doc_id,
                    added_at=datetime.utcnow(),
                    added_by=user_id,
                    metadata={"source": "manual"}
                ))
        
        if to_add:
            self.db.add_all(to_add)
            await self.db.commit()
            
            # Actualizar el contador de documentos
            await self._update_document_count(knowledge_base_id)
        
        return to_add
    
    async def remove_documents(
        self, 
        knowledge_base_id: int, 
        document_ids: List[int],
        user_id: int
    ) -> bool:
        """
        Elimina documentos de una base de conocimiento.
        
        Args:
            knowledge_base_id: ID de la base de conocimiento
            document_ids: Lista de IDs de documentos a eliminar
            user_id: ID del usuario que realiza la operación
            
        Returns:
            bool: True si la operación fue exitosa
        """
        # Verificar que la base de conocimiento exista y el usuario tenga acceso
        kb = await self.get(knowledge_base_id, user_id=user_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Base de conocimiento no encontrada o acceso denegado"
            )
        
        # Eliminar las asociaciones
        result = await self.db.execute(
            KnowledgeDocument.__table__.delete().where(
                and_(
                    KnowledgeDocument.knowledge_base_id == knowledge_base_id,
                    KnowledgeDocument.document_id.in_(document_ids)
                )
            )
        )
        
        await self.db.commit()
        
        # Actualizar el contador de documentos
        if result.rowcount > 0:
            await self._update_document_count(knowledge_base_id)
        
        return True
    
    async def get_stats(
        self, 
        knowledge_base_id: int, 
        user_id: int
    ) -> KnowledgeBaseStats:
        """
        Obtiene estadísticas de una base de conocimiento.
        
        Args:
            knowledge_base_id: ID de la base de conocimiento
            user_id: ID del usuario que realiza la consulta
            
        Returns:
            KnowledgeBaseStats: Estadísticas de la base de conocimiento
        """
        # Verificar que la base de conocimiento exista y el usuario tenga acceso
        kb = await self.get(knowledge_base_id, user_id=user_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Base de conocimiento no encontrada o acceso denegado"
            )
        
        # Contar documentos
        doc_count = await self.db.execute(
            select(func.count(KnowledgeDocument.id)).where(
                KnowledgeDocument.knowledge_base_id == knowledge_base_id
            )
        )
        document_count = doc_count.scalar() or 0
        
        # Obtener el tamaño total de los documentos
        size_result = await self.db.execute(
            select(func.sum(DocumentModel.size)).join(
                KnowledgeDocument,
                KnowledgeDocument.document_id == DocumentModel.id
            ).where(
                KnowledgeDocument.knowledge_base_id == knowledge_base_id
            )
        )
        total_size = size_result.scalar() or 0
        
        # Obtener el número de fragmentos en Weaviate
        weaviate_count = await weaviate_service.get_document_count(
            filters={"knowledge_base_id": knowledge_base_id}
        )
        
        return KnowledgeBaseStats(
            document_count=document_count,
            total_size=total_size,
            chunk_count=weaviate_count,
            last_updated=kb.updated_at
        )
    
    async def search(
        self, 
        query: str,
        knowledge_base_id: int,
        user_id: int,
        limit: int = 10,
        min_score: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Busca en una base de conocimiento usando una consulta semántica.
        
        Args:
            query: Texto de búsqueda
            knowledge_base_id: ID de la base de conocimiento
            user_id: ID del usuario que realiza la búsqueda
            limit: Número máximo de resultados a devolver
            min_score: Puntuación mínima para incluir un resultado
            
        Returns:
            Lista de resultados de búsqueda con metadatos
        """
        # Verificar que la base de conocimiento exista y el usuario tenga acceso
        kb = await self.get(knowledge_base_id, user_id=user_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Base de conocimiento no encontrada o acceso denegado"
            )
        
        # Generar embedding para la consulta
        query_embedding = await openai_service.generate_embeddings(query)
        
        # Buscar en Weaviate
        search_results = await weaviate_service.search_similar(
            query_embedding[0],
            limit=limit,
            min_score=min_score,
            filters={"knowledge_base_id": knowledge_base_id}
        )
        
        # Obtener documentos completos para los resultados
        if not search_results:
            return []
            
        document_ids = list({r["document_id"] for r in search_results})
        
        # Obtener los documentos de la base de datos
        result = await self.db.execute(
            select(DocumentModel).where(DocumentModel.id.in_(document_ids))
        )
        documents = {doc.id: doc for doc in result.scalars().all()}
        
        # Formatear resultados
        formatted_results = []
        for result in search_results:
            doc = documents.get(result["document_id"])
            if doc:
                formatted_results.append({
                    "document": doc,
                    "score": result["score"],
                    "chunk_text": result["text"],
                    "chunk_metadata": result["metadata"]
                })
        
        return formatted_results
    
    async def _update_document_count(self, knowledge_base_id: int) -> None:
        """
        Actualiza el contador de documentos de una base de conocimiento.
        
        Args:
            knowledge_base_id: ID de la base de conocimiento
        """
        # Contar documentos
        result = await self.db.execute(
            select(func.count(KnowledgeDocument.id)).where(
                KnowledgeDocument.knowledge_base_id == knowledge_base_id
            )
        )
        
        count = result.scalar() or 0
        
        # Actualizar el contador
        await self.db.execute(
            KnowledgeBase.__table__
            .update()
            .where(KnowledgeBase.id == knowledge_base_id)
            .values(document_count=count, updated_at=datetime.utcnow())
        )
        
        await self.db.commit()
    
    async def get_user_knowledge_bases(
        self, 
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        include_stats: bool = True
    ) -> List[Union[KnowledgeBaseInDB, KnowledgeBaseWithDocuments]]:
        """
        Obtiene las bases de conocimiento de un usuario.
        
        Args:
            user_id: ID del usuario
            skip: Número de bases de conocimiento a saltar
            limit: Número máximo de bases de conocimiento a devolver
            include_stats: Si es True, incluye estadísticas de cada base de conocimiento
            
        Returns:
            Lista de bases de conocimiento del usuario
        """
        query = select(KnowledgeBase).where(
            KnowledgeBase.owner_id == user_id
        ).order_by(KnowledgeBase.updated_at.desc())
        
        if limit > 0:
            query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        knowledge_bases = result.scalars().all()
        
        if not include_stats:
            return knowledge_bases
        
        # Obtener estadísticas para cada base de conocimiento
        knowledge_bases_with_stats = []
        for kb in knowledge_bases:
            stats = await self.get_stats(kb.id, user_id)
            kb_with_stats = KnowledgeBaseWithDocuments(
                **kb.__dict__,
                documents=[],
                stats=stats
            )
            knowledge_bases_with_stats.append(kb_with_stats)
        
        return knowledge_bases_with_stats
