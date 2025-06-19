import logging
from typing import List, Optional, Dict, Any, BinaryIO
from sqlalchemy.orm import Session
import PyPDF2
import docx
import io
import magic
from datetime import datetime

from ..models.document import Document as DocumentModel
from ..schemas.document import DocumentCreate, DocumentUpdate, DocumentInDB
from .base import CRUDBase

logger = logging.getLogger(__name__)

class DocumentService(CRUDBase[DocumentModel, DocumentCreate, DocumentUpdate]):
    """
    Servicio para la gestión de documentos
    """
    def __init__(self, db: Session):
        super().__init__(DocumentModel, db)
    
    async def process_uploaded_file(
        self, 
        filename: str, 
        content: bytes, 
        content_type: str
    ) -> Dict[str, Any]:
        """
        Procesa un archivo subido y extrae su contenido
        
        Args:
            filename: Nombre del archivo
            content: Contenido binario del archivo
            content_type: Tipo MIME del archivo
            
        Returns:
            Diccionario con el contenido procesado y metadatos
        """
        try:
            # Determinar el tipo de archivo
            file_type = self._detect_file_type(filename, content, content_type)
            
            # Procesar según el tipo de archivo
            if file_type == "pdf":
                text = self._extract_text_from_pdf(io.BytesIO(content))
            elif file_type == "docx":
                text = self._extract_text_from_docx(io.BytesIO(content))
            elif file_type == "text" or file_type == "markdown":
                text = content.decode('utf-8')
            else:
                raise ValueError(f"Tipo de archivo no soportado: {file_type}")
            
            return {
                "content": text,
                "content_type": content_type,
                "file_type": file_type,
                "size": len(content)
            }
            
        except Exception as e:
            logger.error(f"Error al procesar archivo: {str(e)}")
            raise
    
    def _detect_file_type(self, filename: str, content: bytes, content_type: str) -> str:
        """Detecta el tipo de archivo usando magic y la extensión"""
        # Usar magic para detectar el tipo MIME real
        mime = magic.Magic(mime=True)
        detected_mime = mime.from_buffer(content)
        
        # Mapear tipos MIME a tipos de archivo soportados
        mime_type_map = {
            'application/pdf': 'pdf',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'text/plain': 'text',
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
                'txt': 'text',
                'md': 'markdown',
                'markdown': 'markdown'
            }
            file_type = ext_map.get(ext)
        
        if not file_type:
            raise ValueError("Tipo de archivo no soportado")
            
        return file_type
    
    def _extract_text_from_pdf(self, file_stream: BinaryIO) -> str:
        """Extrae texto de un archivo PDF"""
        try:
            pdf_reader = PyPDF2.PdfReader(file_stream)
            text_parts = []
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text_parts.append(page.extract_text())
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"Error al extraer texto de PDF: {str(e)}")
            raise
    
    def _extract_text_from_docx(self, file_stream: BinaryIO) -> str:
        """Extrae texto de un archivo DOCX"""
        try:
            doc = docx.Document(file_stream)
            return "\n".join([paragraph.text for paragraph in doc.paragraphs])
        except Exception as e:
            logger.error(f"Error al extraer texto de DOCX: {str(e)}")
            raise
    
    def create_document(self, document: DocumentCreate) -> DocumentInDB:
        """Crea un nuevo documento en la base de datos"""
        db_document = DocumentModel(
            title=document.title,
            content=document.content,
            source=document.source,
            doc_type=document.doc_type,
            size=document.size,
            metadata=document.metadata,
            user_id=document.user_id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(db_document)
        self.db.commit()
        self.db.refresh(db_document)
        
        return db_document
    
    def get_document(self, document_id: str, user_id: str) -> Optional[DocumentInDB]:
        """Obtiene un documento por ID y usuario"""
        return self.db.query(DocumentModel).filter(
            DocumentModel.id == document_id,
            DocumentModel.user_id == user_id
        ).first()
    
    def get_document_by_weaviate_id(self, weaviate_id: str, user_id: str) -> Optional[DocumentInDB]:
        """Obtiene un documento por su ID de Weaviate"""
        return self.db.query(DocumentModel).filter(
            DocumentModel.weaviate_id == weaviate_id,
            DocumentModel.user_id == user_id
        ).first()
    
    def get_user_documents(
        self, 
        user_id: str, 
        skip: int = 0, 
        limit: int = 10
    ) -> List[DocumentInDB]:
        """Obtiene los documentos de un usuario con paginación"""
        return self.db.query(DocumentModel).filter(
            DocumentModel.user_id == user_id
        ).offset(skip).limit(limit).all()
    
    def update_document(
        self, 
        document_id: str, 
        document: DocumentUpdate,
        user_id: str
    ) -> Optional[DocumentInDB]:
        """Actualiza un documento existente"""
        db_document = self.get_document(document_id, user_id)
        if not db_document:
            return None
            
        update_data = document.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        
        for field, value in update_data.items():
            setattr(db_document, field, value)
            
        self.db.add(db_document)
        self.db.commit()
        self.db.refresh(db_document)
        
        return db_document
    
    def delete_document(self, document_id: str, user_id: str) -> bool:
        """Elimina un documento"""
        db_document = self.get_document(document_id, user_id)
        if not db_document:
            return False
            
        self.db.delete(db_document)
        self.db.commit()
        return True
