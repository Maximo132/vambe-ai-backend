import weaviate
from typing import List, Dict, Any, Optional
import json
from datetime import datetime
from uuid import uuid4

from ..core.config import settings
from ..schemas.chat import Document, SearchResult

class WeaviateService:
    def __init__(self):
        """Inicializa el cliente de Weaviate"""
        self.client = weaviate.Client(
            url=settings.WEAVIATE_URL,
            additional_headers={
                "X-OpenAI-Api-Key": settings.OPENAI_API_KEY
            }
        )
        self._ensure_schema()
    
    def _ensure_schema(self):
        """Asegura que exista el esquema en Weaviate"""
        schema = {
            "classes": [
                {
                    "class": "Document",
                    "description": "Documento con embeddings para búsqueda semántica",
                    "vectorizer": "text2vec-openai",
                    "moduleConfig": {
                        "text2vec-openai": {
                            "model": "text-embedding-3-small",
                            "type": "text"
                        }
                    },
                    "properties": [
                        {
                            "name": "content",
                            "dataType": ["text"],
                            "description": "Contenido del documento",
                            "moduleConfig": {
                                "text2vec-openai": {
                                    "skip": False,
                                    "vectorizePropertyName": False
                                }
                            }
                        },
                        {
                            "name": "title",
                            "dataType": ["string"],
                            "description": "Título del documento"
                        },
                        {
                            "name": "source",
                            "dataType": ["string"],
                            "description": "Fuente del documento (URL, nombre de archivo, etc.)"
                        },
                        {
                            "name": "doc_id",
                            "dataType": ["string"],
                            "description": "ID único del documento en el sistema externo"
                        },
                        {
                            "name": "metadata",
                            "dataType": ["object"],
                            "description": "Metadatos adicionales del documento"
                        },
                        {
                            "name": "user_id",
                            "dataType": ["string"],
                            "description": "ID del usuario propietario del documento"
                        },
                        {
                            "name": "created_at",
                            "dataType": ["date"],
                            "description": "Fecha de creación del documento"
                        }
                    ]
                }
            ]
        }
        
        # Verificar si la clase ya existe
        if not self.client.schema.contains(schema["classes"][0]):
            self.client.schema.create_class(schema["classes"][0])
    
    async def index_document(self, document: Document) -> str:
        """
        Indexa un documento en Weaviate
        
        Args:
            document: Documento a indexar
            
        Returns:
            ID del documento en Weaviate
        """
        doc_id = str(uuid4())
        
        doc_obj = {
            "content": document.content,
            "title": document.title,
            "source": document.source,
            "doc_id": document.doc_id or doc_id,
            "metadata": document.metadata or {},
            "user_id": document.user_id,
            "created_at": document.created_at or datetime.utcnow().isoformat()
        }
        
        try:
            result = self.client.data_object.create(
                data_object=doc_obj,
                class_name="Document"
            )
            return result["id"]
        except Exception as e:
            raise Exception(f"Error al indexar documento en Weaviate: {str(e)}")
    
    async def search_documents(
        self, 
        query: str, 
        user_id: str, 
        limit: int = 5,
        certainty: float = 0.7
    ) -> List[SearchResult]:
        """
        Busca documentos similares a la consulta
        
        Args:
            query: Texto de búsqueda
            user_id: ID del usuario que realiza la búsqueda
            limit: Número máximo de resultados a devolver
            certainty: Umbral de similitud (0-1)
            
        Returns:
            Lista de documentos relevantes
        """
        try:
            result = (
                self.client.query
                .get("Document", ["content", "title", "source", "metadata"])
                .with_where({
                    "path": ["user_id"],
                    "operator": "Equal",
                    "valueString": user_id
                })
                .with_near_text({"concepts": [query]})
                .with_limit(limit)
                .with_additional(["certainty", "id"])
                .do()
            )
            
            if "errors" in result:
                raise Exception(f"Error en la búsqueda: {result['errors']}")
                
            items = result.get("data", {}).get("Get", {}).get("Document", [])
            
            return [
                SearchResult(
                    id=item["_additional"]["id"],
                    content=item["content"],
                    title=item.get("title", ""),
                    source=item.get("source", ""),
                    metadata=item.get("metadata", {}),
                    score=item["_additional"].get("certainty", 0)
                )
                for item in items
            ]
            
        except Exception as e:
            raise Exception(f"Error al buscar documentos: {str(e)}")
    
    async def delete_document(self, doc_id: str) -> bool:
        """
        Elimina un documento de Weaviate
        
        Args:
            doc_id: ID del documento a eliminar
            
        Returns:
            True si se eliminó correctamente, False en caso contrario
        """
        try:
            self.client.data_object.delete(uuid=doc_id, class_name="Document")
            return True
        except Exception as e:
            print(f"Error al eliminar documento {doc_id}: {str(e)}")
            return False

# Instancia global del servicio
weaviate_service = WeaviateService()
