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
    
    async def search_documents(self, query: str, limit: int = 5, min_score: float = 0.7) -> List[SearchResult]:
        """
        Busca documentos similares a la consulta usando búsqueda semántica.
        
        Args:
            query: Texto de búsqueda
            limit: Número máximo de resultados a devolver
            min_score: Puntuación mínima de similitud (0-1)
            
        Returns:
            Lista de resultados de búsqueda
        """
        try:
            # Generar embeddings para la consulta usando OpenAI
            query_embedding = await openai_service.generate_embeddings(query)
            
            # Realizar la búsqueda en Weaviate
            result = (
                self.client.query
                .get("Document", ["title", "content", "source", "metadata"])
                .with_near_vector({
                    "vector": query_embedding[0],
                    "certainty": min_score
                })
                .with_limit(limit)
                .with_additional(["id", "certainty"])
                .do()
            )
            
            # Procesar resultados
            search_results = []
            if "data" in result and "Get" in result["data"] and "Document" in result["data"]["Get"]:
                for item in result["data"]["Get"]["Document"]:
                    search_results.append(SearchResult(
                        id=item["_additional"]["id"],
                        title=item["title"],
                        content=item["content"],
                        source=item.get("source", ""),
                        metadata=item.get("metadata", {}),
                        score=item["_additional"]["certainty"]
                    ))
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error en búsqueda semántica: {str(e)}")
            return []
            
    async def get_embedding(self, text: str) -> List[float]:
        """
        Obtiene el embedding de un texto usando el modelo configurado en Weaviate.
        
        Args:
            text: Texto a obtener el embedding
            
        Returns:
            Lista de floats que representa el vector de embedding
        """
        try:
            # Usar el cliente de Weaviate para generar el embedding
            result = self.client.query.raw('''
            {
                  Get {
                    OpenAI {
                      _additional {
                        generate(
                          prompt: """{{text}}"""
                        ) {
                          singleResult {
                            vector
                          }
                        }
                      }
                    }
                  }
                }
            '''.replace('{{text}}', text.replace('"', '\\"')))
            
            # Extraer el vector del resultado
            if result and 'data' in result and 'Get' in result['data'] and 'OpenAI' in result['data']['Get']:
                openai_data = result['data']['Get']['OpenAI']
                if openai_data and len(openai_data) > 0:
                    vector = openai_data[0]['_additional']['generate']['singleResult']['vector']
                    return vector
            
            # Si falla, usar directamente la API de OpenAI
            import openai
            from openai import OpenAI
            
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            response = client.embeddings.create(
                input=text,
                model="text-embedding-3-small"
            )
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Error al obtener embedding: {str(e)}", exc_info=True)
            raise
    
    async def semantic_search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        min_score: float = 0.5,
        filters: Optional[Dict[str, Any]] = None,
        include_vectors: bool = False,
        include_metadata: bool = True,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Realiza una búsqueda semántica en los documentos indexados usando un vector de embedding.
        
        Args:
            query_embedding: Vector de embedding de la consulta
            limit: Número máximo de resultados a devolver
            min_score: Puntuación mínima de relevancia (0-1)
            filters: Filtros adicionales para la búsqueda
            include_vectors: Si es True, incluye los vectores en los resultados
            include_metadata: Si es True, incluye los metadatos en los resultados
            
        Returns:
            Lista de documentos relevantes con metadatos y puntuación
        """
        try:
            # Construir la consulta de búsqueda
            query_builder = (
                self.client.query
                .get("Document", 
                     ["content", "title", "source", "metadata", "doc_id", "user_id"])
                .with_near_vector({
                    "vector": query_embedding,
                    "certainty": min_score
                })
                .with_limit(limit)
                .with_additional(["id", "certainty", "distance", "vector"])
            )
            
            # Aplicar filtros
            if filters:
                filter_conditions = []
                for key, value in filters.items():
                    if value is None:
                        continue
                        
                    if isinstance(value, (list, tuple, set)):
                        # Para filtros con múltiples valores (IN)
                        if value:  # Solo agregar si hay valores
                            value_filter = {
                                "operator": "Or",
                                "operands": [
                                    {"path": [key], "operator": "Equal", "valueString": str(v)}
                                    for v in value
                                ]
                            }
                            filter_conditions.append(value_filter)
                    else:
                        # Para filtros con un solo valor
                        filter_conditions.append({
                            "path": [key],
                            "operator": "Equal",
                            "valueString": str(value)
                        })
                
                if filter_conditions:
                    if len(filter_conditions) > 1:
                        # Combinar múltiples condiciones con AND
                        combined_filter = {
                            "operator": "And",
                            "operands": filter_conditions
                        }
                        query_builder = query_builder.with_where(combined_filter)
                    else:
                        query_builder = query_builder.with_where(filter_conditions[0])
            
            # Ejecutar la consulta
            result = query_builder.do()
            
            # Procesar resultados
            search_results = []
            if "data" in result and "Get" in result["data"] and "Document" in result["data"]["Get"]:
                for item in result["data"]["Get"]["Document"]:
                    result_item = {
                        "id": item["_additional"]["id"],
                        "document_id": int(item.get("doc_id")) if item.get("doc_id") else None,
                        "title": item.get("title", ""),
                        "text": item.get("content", ""),
                        "source": item.get("source", ""),
                        "score": float(item["_additional"].get("certainty", 0.0)),
                        "distance": float(item["_additional"].get("distance", 0.0))
                    }
                    
                    # Incluir metadatos si se solicita
                    if include_metadata:
                        metadata = item.get("metadata", {})
                        if isinstance(metadata, str):
                            try:
                                metadata = json.loads(metadata)
                            except (json.JSONDecodeError, TypeError):
                                metadata = {}
                        result_item["metadata"] = metadata
                    
                    # Incluir vector si se solicita
                    if include_vectors and "vector" in item["_additional"]:
                        result_item["vector"] = item["_additional"]["vector"]
                    
                    search_results.append(result_item)
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error en búsqueda semántica: {str(e)}", exc_info=True)
            raise
    
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
