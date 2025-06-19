import logging
import os
import io
import magic
import PyPDF2
import docx
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, BinaryIO, Union, AsyncGenerator
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_

from app.core.config import settings
from app.models.document import Document as DocumentModel, DocumentType, DocumentStatus
from app.models.knowledge_base import KnowledgeBase, KnowledgeDocument
from app.schemas.document import (
    DocumentBase, DocumentCreate, DocumentUpdate, DocumentInDB, DocumentProcessRequest,
    DocumentProcessResponse, DocumentSearchQuery, DocumentSearchResults, DocumentUploadResponse
)
from app.services.base import CRUDBase
from app.services.openai_service import openai_service
from app.services.weaviate_service import weaviate_service
from app.utils.file_utils import save_upload_file, get_file_extension, generate_unique_filename

logger = logging.getLogger(__name__)

class DocumentService(CRUDBase[DocumentModel, DocumentCreate, DocumentUpdate]):
    """
    Servicio para la gestión de documentos, incluyendo carga, procesamiento y búsqueda.
    """
    
    def __init__(self, db: Session):
        super().__init__(DocumentModel, db)
        self.upload_dir = Path(settings.UPLOAD_DIR) / "documents"
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    async def upload_document(
        self,
        file: UploadFile,
        user_id: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DocumentUploadResponse:
        """
        Sube un documento al servidor y crea un registro en la base de datos.
        
        Args:
            file: Archivo a subir
            user_id: ID del usuario que sube el documento
            metadata: Metadatos adicionales
            
        Returns:
            DocumentUploadResponse con los detalles del documento subido
        """
        try:
            # Validar el tipo de archivo
            file_type = self._detect_file_type(file.filename, await file.read(1024), file.content_type)
            await file.seek(0)  # Volver al inicio del archivo
            
            # Generar un nombre de archivo único
            file_ext = get_file_extension(file.filename)
            filename = generate_unique_filename(file.filename, prefix=f"doc_{user_id}_")
            file_path = self.upload_dir / filename
            
            # Guardar el archivo
            await save_upload_file(file, file_path)
            
            # Crear el registro en la base de datos
            document_data = DocumentCreate(
                title=file.filename,
                description=metadata.get("description") if metadata else None,
                file_url=str(file_path),
                file_type=DocumentType(file_type),
                metadata=metadata or {}
            )
            
            db_document = await self.create(document_data, user_id=user_id)
            
            return DocumentUploadResponse(
                **db_document.dict(),
                message="Documento cargado exitosamente"
            )
            
        except Exception as e:
            logger.error(f"Error al subir documento: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error al subir el documento: {str(e)}"
            )
    
    async def process_document(
        self,
        document_id: int,
        process_data: DocumentProcessRequest,
        user_id: int
    ) -> DocumentProcessResponse:
        """
        Procesa un documento para extraer texto y generar embeddings.
        
        Args:
            document_id: ID del documento a procesar
            process_data: Datos de procesamiento (tamaño de fragmentos, etc.)
            user_id: ID del usuario que realiza la operación
            
        Returns:
            DocumentProcessResponse con el resultado del procesamiento
        """
        # Obtener el documento
        document = await self.get(document_id, user_id=user_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Documento no encontrado"
            )
        
        try:
            # Actualizar el estado del documento
            document.status = DocumentStatus.PROCESSING
            self.db.commit()
            self.db.refresh(document)
            
            # Leer el contenido del archivo
            with open(document.file_url, "rb") as f:
                content = f.read()
            
            # Extraer texto según el tipo de archivo
            text = await self._extract_text(document.file_url, content, document.file_type)
            
            # Dividir el texto en fragmentos
            chunks = self._chunk_text(
                text,
                chunk_size=process_data.chunk_size,
                chunk_overlap=process_data.chunk_overlap
            )
            
            # Generar embeddings para cada fragmento
            chunks_with_embeddings = []
            for i, chunk in enumerate(chunks):
                # Generar un ID único para el fragmento
                chunk_id = f"{document_id}_{i}"
                
                # Generar embedding
                embedding = await openai_service.generate_embeddings(chunk["text"])
                
                # Almacenar en Weaviate
                weaviate_id = await weaviate_service.add_document_chunk(
                    document_id=document_id,
                    chunk_id=chunk_id,
                    text=chunk["text"],
                    metadata={
                        "document_title": document.title,
                        "chunk_index": i,
                        **chunk.get("metadata", {}),
                        **process_data.metadata
                    },
                    vector=embedding[0]  # Tomar el primer embedding
                )
                
                chunks_with_embeddings.append({
                    "chunk_id": chunk_id,
                    "weaviate_id": weaviate_id,
                    "text": chunk["text"],
                    "metadata": chunk.get("metadata", {})
                })
            
            # Actualizar el estado del documento
            document.status = DocumentStatus.COMPLETED
            document.processed_at = datetime.utcnow()
            document.metadata = {
                **document.metadata,
                "chunks_processed": len(chunks_with_embeddings),
                "processing_metadata": process_data.metadata
            }
            self.db.commit()
            
            return DocumentProcessResponse(
                document_id=document_id,
                status="completed",
                message=f"Documento procesado exitosamente. {len(chunks_with_embeddings)} fragmentos generados.",
                chunks_processed=len(chunks_with_embeddings)
            )
            
        except Exception as e:
            # Actualizar el estado del documento en caso de error
            document.status = DocumentStatus.FAILED
            document.metadata = {
                **document.metadata,
                "error": str(e),
                "error_timestamp": datetime.utcnow().isoformat()
            }
            self.db.commit()
            
            logger.error(f"Error al procesar documento {document_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al procesar el documento: {str(e)}"
            )
    
    async def search_documents(
        self,
        query: str,
        user_id: int,
        search_params: DocumentSearchQuery
    ) -> DocumentSearchResults:
        """
        Busca documentos relevantes para una consulta.
        
        Args:
            query: Texto de búsqueda
            user_id: ID del usuario que realiza la búsqueda
            search_params: Parámetros de búsqueda
            
        Returns:
            DocumentSearchResults con los resultados de la búsqueda
        """
        try:
            # Generar embedding para la consulta
            query_embedding = await openai_service.generate_embeddings(query)
            
            # Buscar en Weaviate
            search_results = await weaviate_service.search_similar(
                query_embedding[0],  # Tomar el primer embedding
                limit=search_params.limit,
                min_score=search_params.min_score,
                filters={
                    "user_id": user_id,
                    "knowledge_base_id": search_params.knowledge_base_id
                } if search_params.knowledge_base_id else {"user_id": user_id}
            )
            
            # Obtener documentos completos
            document_ids = list({r["document_id"] for r in search_results})
            documents = {}
            
            if document_ids:
                result = await self.db.execute(
                    select(DocumentModel).where(DocumentModel.id.in_(document_ids))
                )
                documents = {doc.id: doc for doc in result.scalars().all()}
            
            # Formatear resultados
            results = []
            for result in search_results:
                doc = documents.get(result["document_id"])
                if doc:
                    results.append({
                        "document": doc,
                        "score": result["score"],
                        "chunk_text": result["text"],
                        "chunk_metadata": result["metadata"]
                    })
            
            return DocumentSearchResults(
                results=results,
                total=len(results)
            )
            
        except Exception as e:
            logger.error(f"Error al buscar documentos: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al buscar documentos: {str(e)}"
            )
    
    async def _extract_text(
        self,
        file_path: str,
        content: bytes,
        file_type: DocumentType
    ) -> str:
        """Extrae texto de un archivo según su tipo."""
        try:
            if file_type == DocumentType.PDF:
                return self._extract_text_from_pdf(io.BytesIO(content))
            elif file_type == DocumentType.DOCX:
                return self._extract_text_from_docx(io.BytesIO(content))
            elif file_type in [DocumentType.TXT, DocumentType.MARKDOWN]:
                return content.decode('utf-8')
            else:
                raise ValueError(f"Tipo de archivo no soportado: {file_type}")
        except Exception as e:
            logger.error(f"Error al extraer texto: {str(e)}")
            raise
    
    def _detect_file_type(self, filename: str, content: bytes, content_type: str) -> str:
        """Detecta el tipo de archivo usando magic y la extensión."""
        try:
            # Usar magic para detectar el tipo MIME real
            mime = magic.Magic(mime=True)
            detected_mime = mime.from_buffer(content)
            
            # Mapear tipos MIME a tipos de documento
            mime_type_map = {
                'application/pdf': 'pdf',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
                'text/plain': 'txt',
                'text/markdown': 'markdown',
                'text/x-markdown': 'markdown',
            }
            
            file_type = mime_type_map.get(detected_mime.lower())
            
            # Si no se pudo detectar por MIME, intentar por extensión
            if not file_type:
                ext = filename.split('.')[-1].lower()
                ext_map = {
                    'pdf': 'pdf',
                    'docx': 'docx',
                    'txt': 'txt',
                    'md': 'markdown',
                    'markdown': 'markdown'
                }
                file_type = ext_map.get(ext)
            
            if not file_type:
                raise ValueError("Tipo de archivo no soportado")
                
            return file_type
            
        except Exception as e:
            logger.error(f"Error al detectar tipo de archivo: {str(e)}")
            raise ValueError("No se pudo determinar el tipo de archivo")
    
    def _chunk_text(
        self,
        text: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Divide el texto en fragmentos con superposición.
        
        Args:
            text: Texto a dividir
            chunk_size: Tamaño máximo de cada fragmento en caracteres
            chunk_overlap: Número de caracteres de superposición entre fragmentos
            
        Returns:
            Lista de fragmentos con metadatos
        """
        if not text:
            return []
            
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            end = min(start + chunk_size, text_length)
            
            # Asegurarse de no cortar palabras a la mitad
            if end < text_length:
                # Buscar el último espacio en blanco o salto de línea
                split_at = text.rfind(' ', start, end + 1)
                if split_at == -1 or split_at < start + chunk_size // 2:
                    split_at = text.find(' ', end, end + 100)  # Buscar el siguiente espacio
                    if split_at == -1:
                        split_at = end
                end = split_at
            
            chunk_text = text[start:end].strip()
            if chunk_text:  # Solo agregar fragmentos no vacíos
                chunks.append({
                    "text": chunk_text,
                    "metadata": {
                        "chunk_start": start,
                        "chunk_end": end,
                        "chunk_length": end - start
                    }
                })
            
            # Mover el inicio al final del fragmento actual, menos el solapamiento
            start = max(start + 1, end - chunk_overlap)
            
            # Si no hay progreso, forzar el avance para evitar bucles infinitos
            if start >= end and end < text_length:
                start = end
        
        return chunks
    
    def _extract_text_from_pdf(self, file_stream: BinaryIO) -> str:
        """Extrae texto de un archivo PDF."""
        try:
            pdf_reader = PyPDF2.PdfReader(file_stream)
            text_parts = []
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text = page.extract_text() or ""  # Manejar páginas sin texto
                text_parts.append(f"--- Página {page_num + 1} ---\n{text}")
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"Error al extraer texto de PDF: {str(e)}")
            raise
    
    def _extract_text_from_docx(self, file_stream: BinaryIO) -> str:
        """Extrae texto de un archivo DOCX."""
        try:
            doc = docx.Document(file_stream)
            return "\n".join(
                paragraph.text for paragraph in doc.paragraphs 
                if paragraph.text.strip()
            )
        except Exception as e:
            logger.error(f"Error al extraer texto de DOCX: {str(e)}")
            raise
    
    async def create(
        self, 
        obj_in: DocumentCreate, 
        user_id: int,
        **kwargs
    ) -> DocumentModel:
        """Crea un nuevo documento en la base de datos."""
        db_obj = DocumentModel(
            **obj_in.dict(exclude_unset=True),
            user_id=user_id,
            status=DocumentStatus.PENDING,
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
        obj_in: Union[DocumentUpdate, Dict[str, Any]],
        user_id: int,
        **kwargs
    ) -> Optional[DocumentModel]:
        """Actualiza un documento existente."""
        db_obj = await self.get(id, user_id=user_id)
        if not db_obj:
            return None
            
        update_data = obj_in.dict(exclude_unset=True) if not isinstance(obj_in, dict) else obj_in
        update_data["updated_at"] = datetime.utcnow()
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
            
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        
        return db_obj
    
    async def get(self, id: int, user_id: int, **kwargs) -> Optional[DocumentModel]:
        """Obtiene un documento por ID y usuario."""
        result = await self.db.execute(
            select(DocumentModel)
            .where(and_(
                DocumentModel.id == id,
                DocumentModel.user_id == user_id
            ))
        )
        return result.scalars().first()
    
    async def get_multi(
        self, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 100,
        **kwargs
    ) -> List[DocumentModel]:
        """Obtiene múltiples documentos de un usuario con paginación."""
        result = await self.db.execute(
            select(DocumentModel)
            .where(DocumentModel.user_id == user_id)
            .order_by(DocumentModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def delete(self, id: int, user_id: int, **kwargs) -> bool:
        """Elimina un documento."""
        db_obj = await self.get(id, user_id=user_id)
        if not db_obj:
            return False
            
        # Eliminar el archivo físico si existe
        if db_obj.file_url and os.path.exists(db_obj.file_url):
            try:
                os.remove(db_obj.file_url)
            except Exception as e:
                logger.error(f"Error al eliminar archivo {db_obj.file_url}: {str(e)}")
        
        # Eliminar de Weaviate si existe
        if db_obj.weaviate_id:
            try:
                await weaviate_service.delete_document(db_obj.weaviate_id)
            except Exception as e:
                logger.error(f"Error al eliminar documento de Weaviate: {str(e)}")
        
        # Eliminar de la base de datos
        await self.db.delete(db_obj)
        await self.db.commit()
        
        return True
