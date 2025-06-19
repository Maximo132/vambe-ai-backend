from typing import List, Dict, Any, Optional, Union, AsyncGenerator, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_, select, func, text
import logging
import json
import uuid
import re
from pathlib import Path

from fastapi import HTTPException, status, UploadFile

from app.models.chat import Conversation, Message, MessageRole, Document as DocumentModel
from app.models.user import User
from app.models.knowledge_base import KnowledgeBase, KnowledgeDocument
from app.schemas.chat import (
    ChatMessage, ChatResponse, ChatResponseChunk, ConversationInDB, 
    MessageInDB, Document as DocumentSchema, ConversationCreate, 
    ConversationUpdate, FunctionCall, FunctionCallResponse
)
from app.schemas.document import DocumentSearchQuery, DocumentSearchResults
from app.schemas.knowledge_base import KnowledgeBaseWithDocuments, KnowledgeBaseSearchQuery
from app.services.openai_service import openai_service
from app.services.weaviate_service import weaviate_service
from app.services.document_service import DocumentService
from app.services.knowledge_service import KnowledgeBaseService
from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import get_db
from app.utils.cache import cache_service
from app.utils.file_utils import save_upload_file, generate_unique_filename, get_file_extension

# Configurar logging
logger = logging.getLogger(__name__)

# Constantes
MAX_TOKENS = 4000  # Máximo de tokens para el contexto
MAX_HISTORY = 10   # Máximo de mensajes de historial a incluir
DOCUMENT_CONTEXT_TOKENS = 1000  # Tokens máximos para el contexto de documentos

# Funciones disponibles para el modelo de chat
AVAILABLE_FUNCTIONS = {
    "search_documents": {
        "name": "search_documents",
        "description": "Busca en los documentos del usuario información relevante a una consulta",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Consulta de búsqueda"
                },
                "knowledge_base_id": {
                    "type": "string",
                    "description": "ID de la base de conocimiento (opcional)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Número máximo de resultados (por defecto: 3)",
                    "default": 3
                }
            },
            "required": ["query"]
        }
    },
    "search_knowledge_base": {
        "name": "search_knowledge_base",
        "description": "Busca en una base de conocimiento específica",
        "parameters": {
            "type": "object",
            "properties": {
                "knowledge_base_id": {
                    "type": "string",
                    "description": "ID de la base de conocimiento"
                },
                "query": {
                    "type": "string",
                    "description": "Consulta de búsqueda"
                },
                "limit": {
                    "type": "integer",
                    "description": "Número máximo de resultados (por defecto: 3)",
                    "default": 3
                }
            },
            "required": ["knowledge_base_id", "query"]
        }
    }
}

class ChatService:
    """
    Servicio para manejar la lógica de negocio relacionada con el chat.
    Se encarga de gestionar conversaciones, mensajes e interacciones con la IA.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.document_service = DocumentService(db)
        self.knowledge_service = KnowledgeBaseService(db)
        self.default_system_prompt = """
        Eres Vambe AI, un asistente de IA profesional y útil. 
        
        Instrucciones clave:
        1. Responde de manera clara, concisa y profesional.
        2. Utiliza el contexto proporcionado para dar respuestas precisas.
        3. Si no estás seguro de algo, dilo claramente en lugar de inventar información.
        4. Cuando cites documentos o fuentes, menciónalos claramente.
        5. Mantén un tono amable y profesional en todo momento.
        6. Si la pregunta es ambigua, pide aclaraciones.
        7. Para preguntas complejas, desglosa la respuesta en pasos lógicos.
        8. Si te piden realizar una acción que no puedes completar, explícalo claramente.
        
        Recuerda: La precisión y la honestidad son más importantes que dar una respuesta inmediata.
        """
    
    async def _get_user_system_prompt(self, user_id: str) -> str:
        """
        Obtiene el prompt del sistema personalizado para el usuario, si existe.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            str: Prompt del sistema personalizado o el predeterminado
        """
        try:
            # Intentar obtener el prompt personalizado del usuario desde la caché
            cache_key = f"user:{user_id}:system_prompt"
            cached_prompt = await cache_service.get(cache_key)
            if cached_prompt:
                return cached_prompt
                
            # Si no está en caché, obtenerlo de la base de datos
            # (implementación futura: obtener de la tabla de configuración del usuario)
            user_prompt = self.default_system_prompt
            
            # Almacenar en caché por 1 hora
            await cache_service.set(cache_key, user_prompt, expire=3600)
            
            return user_prompt
            
        except Exception as e:
            logger.error(f"Error al obtener el prompt del sistema para el usuario {user_id}: {str(e)}")
            return self.default_system_prompt
            
    async def _search_documents(
        self, 
        query: str, 
        user_id: int,
        knowledge_base_id: Optional[str] = None,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Busca en los documentos del usuario información relevante a una consulta.
        
        Args:
            query: Consulta de búsqueda
            user_id: ID del usuario
            knowledge_base_id: ID opcional de la base de conocimiento
            limit: Número máximo de resultados
            
        Returns:
            Lista de resultados de búsqueda con metadatos
        """
        try:
            search_query = DocumentSearchQuery(
                query=query,
                knowledge_base_id=knowledge_base_id,
                limit=limit,
                min_score=0.7
            )
            
            results = await self.document_service.search_documents(
                query=query,
                user_id=user_id,
                search_params=search_query
            )
            
            return [
                {
                    "document_id": str(result.document.id),
                    "title": result.document.title,
                    "content": result.chunk_text,
                    "score": result.score,
                    "metadata": result.chunk_metadata or {}
                }
                for result in results.results
            ]
            
        except Exception as e:
            logger.error(f"Error al buscar documentos: {str(e)}")
            return []
    
    async def _search_knowledge_base(
        self,
        knowledge_base_id: str,
        query: str,
        user_id: int,
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Busca en una base de conocimiento específica.
        
        Args:
            knowledge_base_id: ID de la base de conocimiento
            query: Consulta de búsqueda
            user_id: ID del usuario
            limit: Número máximo de resultados
            
        Returns:
            Lista de resultados de búsqueda con metadatos
        """
        try:
            # Verificar que el usuario tenga acceso a la base de conocimiento
            kb = await self.knowledge_service.get(knowledge_base_id, user_id=user_id)
            if not kb:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes acceso a esta base de conocimiento"
                )
            
            # Realizar la búsqueda
            search_results = await self.knowledge_service.search(
                query=query,
                knowledge_base_id=knowledge_base_id,
                user_id=user_id,
                limit=limit
            )
            
            # Formatear resultados
            formatted_results = []
            for result in search_results:
                doc = result.get("document", {})
                formatted_results.append({
                    "document_id": str(doc.get("id")),
                    "title": doc.get("title", "Documento sin título"),
                    "content": result.get("chunk_text", ""),
                    "score": result.get("score", 0.0),
                    "metadata": result.get("chunk_metadata", {})
                })
            
            return formatted_results
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al buscar en la base de conocimiento {knowledge_base_id}: {str(e)}")
            return []
    
    async def _call_function(
        self, 
        function_name: str, 
        arguments: Dict[str, Any],
        user_id: int
    ) -> Dict[str, Any]:
        """
        Ejecuta una función específica con los argumentos proporcionados.
        
        Args:
            function_name: Nombre de la función a ejecutar
            arguments: Argumentos para la función
            user_id: ID del usuario que realiza la solicitud
            
        Returns:
            Resultado de la función
        """
        try:
            logger.info(f"Llamando a función: {function_name} con argumentos: {arguments}")
            
            if function_name == "search_documents":
                results = await self._search_documents(
                    query=arguments.get("query"),
                    user_id=user_id,
                    knowledge_base_id=arguments.get("knowledge_base_id"),
                    limit=min(int(arguments.get("limit", 3)), 5)  # Máximo 5 resultados
                )
                return {"results": results}
                
            elif function_name == "search_knowledge_base":
                if not arguments.get("knowledge_base_id"):
                    return {"error": "Se requiere el ID de la base de conocimiento"}
                    
                results = await self._search_knowledge_base(
                    knowledge_base_id=arguments["knowledge_base_id"],
                    query=arguments["query"],
                    user_id=user_id,
                    limit=min(int(arguments.get("limit", 3)), 5)  # Máximo 5 resultados
                )
                return {"results": results}
                
            else:
                return {"error": f"Función no implementada: {function_name}"}
                
        except Exception as e:
            logger.error(f"Error al ejecutar la función {function_name}: {str(e)}")
            return {"error": f"Error al ejecutar la función: {str(e)}"}
    
    async def process_message(
        self,
        message: str,
        conversation_id: str,
        user_id: int,
        metadata: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Union[ChatResponse, AsyncGenerator[ChatResponseChunk, None]]:
        """
        Procesa un mensaje del usuario y genera una respuesta, opcionalmente en streaming.
        
        Args:
            message: Mensaje del usuario
            conversation_id: ID de la conversación
            user_id: ID del usuario
            metadata: Metadatos adicionales
            stream: Si es True, devuelve un generador para streaming
            
        Returns:
            ChatResponse o generador de ChatResponseChunk
        """
        try:
            # Verificar que la conversación exista y pertenezca al usuario
            conversation = await self.get_conversation(conversation_id, str(user_id))
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversación no encontrada"
                )
            
            # Obtener el historial de mensajes recientes
            messages = await self._get_conversation_history(conversation_id, limit=MAX_HISTORY)
            
            # Preparar el mensaje del usuario
            user_message = Message(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                role=MessageRole.USER,
                content=message,
                created_at=datetime.utcnow(),
                metadata=metadata or {}
            )
            
            # Guardar el mensaje del usuario
            self.db.add(user_message)
            await self.db.commit()
            
            # Preparar el mensaje para el modelo
            system_prompt = await self._get_user_system_prompt(str(user_id))
            
            # Construir el historial de mensajes para el modelo
            messages_for_model = [
                {"role": "system", "content": system_prompt},
                *[
                    {
                        "role": msg.role.value,
                        "content": msg.content,
                        "name": str(msg.user_id) if msg.role == MessageRole.USER else None
                    }
                    for msg in messages
                    if msg.role in [MessageRole.USER, MessageRole.ASSISTANT]
                ],
                {"role": "user", "content": message, "name": str(user_id)}
            ]
            
            # Función para manejar la respuesta del modelo
            async def generate_response():
                # Primera pasada: determinar si necesitamos buscar información
                response = await openai_service.chat_completion(
                    messages=messages_for_model,
                    functions=[AVAILABLE_FUNCTIONS[fn] for fn in AVAILABLE_FUNCTIONS],
                    function_call="auto",
                    stream=stream
                )
                
                # Si es streaming, manejar la respuesta como generador
                if stream:
                    async for chunk in self._handle_streaming_response(
                        response,
                        conversation_id,
                        user_id,
                        metadata
                    ):
                        yield chunk
                    return
                
                # Si no es streaming, manejar la respuesta normal
                return await self._handle_direct_response(
                    response,
                    conversation_id,
                    user_id,
                    metadata,
                    messages_for_model
                )
            
            return await generate_response()
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al procesar mensaje: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al procesar el mensaje"
            )
    
    async def _handle_direct_response(
        self,
        response: Dict[str, Any],
        conversation_id: str,
        user_id: int,
        metadata: Optional[Dict[str, Any]],
        messages_for_model: List[Dict[str, Any]]
    ) -> ChatResponse:
        """
        Maneja una respuesta directa (no streaming) del modelo.
        """
        function_call = response.get("function_call")
        
        # Si el modelo quiere llamar a una función
        if function_call:
            function_name = function_call.get("name")
            function_args = json.loads(function_call.get("arguments", "{}"))
            
            # Llamar a la función
            function_response = await self._call_function(
                function_name=function_name,
                arguments=function_args,
                user_id=user_id
            )
            
            # Agregar la respuesta de la función al historial
            messages_for_model.append({
                "role": "assistant",
                "content": None,
                "function_call": function_call
            })
            
            messages_for_model.append({
                "role": "function",
                "name": function_name,
                "content": json.dumps(function_response)
            })
            
            # Obtener la respuesta final del modelo
            final_response = await openai_service.chat_completion(
                messages=messages_for_model,
                functions=[AVAILABLE_FUNCTIONS[fn] for fn in AVAILABLE_FUNCTIONS],
                function_call="none"  # No permitir más llamadas a funciones
            )
            
            content = final_response.get("content", "")
        else:
            content = response.get("content", "")
        
        # Crear y guardar el mensaje de asistente
        assistant_message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=content,
            created_at=datetime.utcnow(),
            metadata={
                "model": response.get("model", "gpt-4"),
                "usage": response.get("usage", {}),
                **(metadata or {})
            }
        )
        
        self.db.add(assistant_message)
        await self.db.commit()
        
        return ChatResponse(
            message=MessageInDB.from_orm(assistant_message),
            conversation_id=conversation_id
        )
    
    async def _handle_streaming_response(
        self,
        response_stream: AsyncGenerator[Dict[str, Any], None],
        conversation_id: str,
        user_id: int,
        metadata: Optional[Dict[str, Any]]
    ) -> AsyncGenerator[ChatResponseChunk, None]:
        """
        Maneja una respuesta en streaming del modelo.
        """
        message_id = str(uuid.uuid4())
        full_content = ""
        function_call = None
        
        # Buffer para acumular el contenido de la función
        function_buffer = ""
        in_function_call = False
        
        # Procesar cada chunk de la respuesta
        async for chunk in response_stream:
            delta = chunk.get("delta", {})
            
            # Manejar llamadas a funciones
            if "function_call" in delta:
                in_function_call = True
                if function_call is None:
                    function_call = {"name": "", "arguments": ""}
                
                # Actualizar el nombre de la función si está presente
                if "name" in delta["function_call"]:
                    function_call["name"] += delta["function_call"]["name"]
                
                # Actualizar los argumentos de la función si están presentes
                if "arguments" in delta["function_call"]:
                    function_buffer += delta["function_call"]["arguments"]
                    function_call["arguments"] = function_buffer
                
                # No enviar nada al cliente todavía
                continue
            
            # Si estábamos en una llamada a función pero ahora no, procesar la función
            if in_function_call and not delta.get("function_call"):
                in_function_call = False
                
                # Llamar a la función
                function_name = function_call.get("name")
                function_args = json.loads(function_call.get("arguments", "{}"))
                
                function_response = await self._call_function(
                    function_name=function_name,
                    arguments=function_args,
                    user_id=user_id
                )
                
                # Obtener la respuesta final del modelo con la función
                messages = [
                    {"role": "system", "content": await self._get_user_system_prompt(str(user_id))},
                    {"role": "user", "content": full_content},
                    {
                        "role": "assistant",
                        "content": None,
                        "function_call": function_call
                    },
                    {
                        "role": "function",
                        "name": function_name,
                        "content": json.dumps(function_response)
                    }
                ]
                
                # Obtener la respuesta final del modelo
                final_response = await openai_service.chat_completion(
                    messages=messages,
                    functions=[AVAILABLE_FUNCTIONS[fn] for fn in AVAILABLE_FUNCTIONS],
                    function_call="none",  # No permitir más llamadas a funciones
                    stream=True
                )
                
                # Procesar la respuesta final en streaming
                async for final_chunk in final_response:
                    delta = final_chunk.get("delta", {})
                    if "content" in delta:
                        content = delta["content"] or ""
                        full_content += content
                        
                        yield ChatResponseChunk(
                            id=message_id,
                            content=content,
                            conversation_id=conversation_id,
                            done=False
                        )
                
                # Salir del bucle principal
                break
            
            # Si no es una llamada a función, manejar el contenido normal
            if "content" in delta:
                content = delta["content"] or ""
                full_content += content
                
                yield ChatResponseChunk(
                    id=message_id,
                    content=content,
                    conversation_id=conversation_id,
                    done=False
                )
        
        # Si no hubo llamadas a funciones, guardar el mensaje
        if not function_call:
            assistant_message = Message(
                id=message_id,
                conversation_id=conversation_id,
                role=MessageRole.ASSISTANT,
                content=full_content,
                created_at=datetime.utcnow(),
                metadata={
                    "model": "gpt-4",
                    **(metadata or {})
                }
            )
            
            self.db.add(assistant_message)
            await self.db.commit()
        
        # Enviar señal de finalización
        yield ChatResponseChunk(
            id=message_id,
            content="",
            conversation_id=conversation_id,
            done=True
        )
    
    async def _get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 10,
        before: Optional[datetime] = None
    ) -> List[Message]:
        """
        Obtiene el historial de mensajes de una conversación.
        
        Args:
            conversation_id: ID de la conversación
            limit: Número máximo de mensajes a devolver
            before: Fecha límite para los mensajes
            
        Returns:
            Lista de mensajes ordenados por fecha de creación (más antiguos primero)
        """
        query = select(Message).where(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at.desc())
        
        if before:
            query = query.where(Message.created_at < before)
        
        if limit > 0:
            query = query.limit(limit)
        
        result = await self.db.execute(query)
        messages = result.scalars().all()
        
        # Invertir el orden para devolver los más antiguos primero
        return list(reversed(messages))
    
    # Métodos para manejar conversaciones
    
    async def create_conversation(
        self, 
        conversation_data: ConversationCreate, 
        user_id: str,
        db: Optional[Session] = None
    ) -> ConversationInDB:
        """
        Crea una nueva conversación para un usuario.
        
        Args:
            conversation_data: Datos para crear la conversación
            user_id: ID del usuario propietario
            db: Sesión de base de datos (opcional)
            
        Returns:
            ConversationInDB: Conversación creada
        """
        db = db or self.db
        try:
            # Crear la conversación en la base de datos
            db_conversation = Conversation(
                id=str(uuid.uuid4()),
                user_id=user_id,
                title=conversation_data.title or "Nueva conversación",
                description=conversation_data.description,
                metadata=conversation_data.metadata or {}
            )
            
            db.add(db_conversation)
            await db.commit()
            await db.refresh(db_conversation)
            
            return ConversationInDB.from_orm(db_conversation)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error al crear conversación: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al crear la conversación"
            )
    
    async def get_conversation(
        self, 
        conversation_id: str, 
        user_id: str,
        db: Optional[Session] = None
    ) -> Optional[ConversationInDB]:
        """
        Obtiene una conversación por su ID, verificando que pertenezca al usuario.
        
        Args:
            conversation_id: ID de la conversación
            user_id: ID del usuario propietario
            db: Sesión de base de datos (opcional)
            
        Returns:
            Optional[ConversationInDB]: Conversación encontrada o None
        """
        db = db or self.db
        try:
            conversation = await db.get(Conversation, conversation_id)
            
            if not conversation:
                return None
                
            if str(conversation.user_id) != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para acceder a esta conversación"
                )
                
            return ConversationInDB.from_orm(conversation)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al obtener conversación {conversation_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al obtener la conversación"
            )
    
    async def list_conversations(
        self, 
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        db: Optional[Session] = None
    ) -> List[ConversationInDB]:
        """
        Lista las conversaciones de un usuario con paginación.
        
        Args:
            user_id: ID del usuario
            skip: Número de conversaciones a saltar
            limit: Número máximo de conversaciones a devolver
            db: Sesión de base de datos (opcional)
            
        Returns:
            List[ConversationInDB]: Lista de conversaciones
        """
        db = db or self.db
        try:
            conversations = await db.execute(
                select(Conversation)
                .where(Conversation.user_id == user_id)
                .order_by(Conversation.updated_at.desc())
                .offset(skip)
                .limit(limit)
            )
            
            return [ConversationInDB.from_orm(conv) for conv in conversations.scalars().all()]
            
        except Exception as e:
            logger.error(f"Error al listar conversaciones para el usuario {user_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al listar las conversaciones"
            )
    
    async def update_conversation(
        self, 
        conversation_id: str, 
        conversation_data: ConversationUpdate, 
        user_id: str,
        db: Optional[Session] = None
    ) -> Optional[ConversationInDB]:
        """
        Actualiza una conversación existente.
        
        Args:
            conversation_id: ID de la conversación a actualizar
            conversation_data: Datos a actualizar
            user_id: ID del usuario propietario
            db: Sesión de base de datos (opcional)
            
        Returns:
            Optional[ConversationInDB]: Conversación actualizada o None si no existe
        """
        db = db or self.db
        try:
            # Obtener la conversación existente
            conversation = await db.get(Conversation, conversation_id)
            if not conversation:
                return None
                
            if str(conversation.user_id) != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para actualizar esta conversación"
                )
            
            # Actualizar campos
            update_data = conversation_data.dict(exclude_unset=True)
            for field, value in update_data.items():
                if hasattr(conversation, field):
                    setattr(conversation, field, value)
            
            conversation.updated_at = datetime.now(timezone.utc)
            
            await db.commit()
            await db.refresh(conversation)
            
            return ConversationInDB.from_orm(conversation)
            
        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error al actualizar conversación {conversation_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al actualizar la conversación"
            )
    
    async def delete_conversation(
        self, 
        conversation_id: str, 
        user_id: str,
        db: Optional[Session] = None
    ) -> bool:
        """
        Elimina una conversación y todos sus mensajes.
        
        Args:
            conversation_id: ID de la conversación a eliminar
            user_id: ID del usuario propietario
            db: Sesión de base de datos (opcional)
            
        Returns:
            bool: True si se eliminó correctamente, False si no existía
        """
        db = db or self.db
        try:
            # Obtener la conversación existente
            conversation = await db.get(Conversation, conversation_id)
            if not conversation:
                return False
                
            if str(conversation.user_id) != user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para eliminar esta conversación"
                )
            
            # Eliminar todos los mensajes de la conversación
            await db.execute(
                delete(Message)
                .where(Message.conversation_id == conversation_id)
            )
            
            # Eliminar la conversación
            await db.delete(conversation)
            await db.commit()
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            await db.rollback()
            logger.error(f"Error al eliminar conversación {conversation_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al eliminar la conversación"
            )
    
    # Métodos para manejar mensajes
    
    async def create_message(
        self, 
        message_data: ChatMessage, 
        user_id: str,
        conversation_id: Optional[str] = None,
        db: Optional[Session] = None
    ) -> MessageInDB:
        """
        Crea un nuevo mensaje en una conversación.
        
        Args:
            message_data: Datos del mensaje a crear
            user_id: ID del usuario que envía el mensaje
            conversation_id: ID de la conversación (opcional, se puede crear una nueva)
            db: Sesión de base de datos (opcional)
            
        Returns:
            MessageInDB: Mensaje creado
        """
        db = db or self.db
        try:
            # Si no se proporciona un conversation_id, crear una nueva conversación
            if not conversation_id:
                conversation = Conversation(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    title=message_data.content[:50] + ("..." if len(message_data.content) > 50 else ""),
                    description=None,
                    metadata={}
                )
                db.add(conversation)
                await db.flush()  # Obtener el ID sin hacer commit
                conversation_id = conversation.id
            
            # Crear el mensaje
            db_message = Message(
                id=str(uuid.uuid4()),
                conversation_id=conversation_id,
                role=message_data.role,
                content=message_data.content,
                metadata=message_data.metadata or {}
            )
            
            db.add(db_message)
            
            # Actualizar la fecha de actualización de la conversación
            await db.execute(
                update(Conversation)
                .where(Conversation.id == conversation_id)
                .values(updated_at=func.now())
            )
            
            await db.commit()
            await db.refresh(db_message)
            
            return MessageInDB.from_orm(db_message)
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error al crear mensaje: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al guardar el mensaje"
            )
    
    async def get_conversation_messages(
        self, 
        conversation_id: str, 
        user_id: str,
        skip: int = 0,
        limit: int = 100,
        db: Optional[Session] = None
    ) -> List[MessageInDB]:
        """
        Obtiene los mensajes de una conversación con paginación.
        
        Args:
            conversation_id: ID de la conversación
            user_id: ID del usuario propietario
            skip: Número de mensajes a saltar
            limit: Número máximo de mensajes a devolver
            db: Sesión de base de datos (opcional)
            
        Returns:
            List[MessageInDB]: Lista de mensajes
        """
        db = db or self.db
        try:
            # Verificar que la conversación pertenezca al usuario
            conversation = await db.get(Conversation, conversation_id)
            if not conversation or str(conversation.user_id) != user_id:
                return []
            
            # Obtener mensajes paginados
            result = await db.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at.asc())
                .offset(skip)
                .limit(limit)
            )
            
            messages = result.scalars().all()
            return [MessageInDB.from_orm(msg) for msg in messages]
            
        except Exception as e:
            logger.error(f"Error al obtener mensajes de la conversación {conversation_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al obtener los mensajes"
            )
    
    # Métodos para interactuar con la IA
    
    async def _get_relevant_context(self, query: str, user_id: str) -> str:
        """
        Obtiene contexto relevante de Weaviate para la consulta del usuario.
        
        Args:
            query: Consulta del usuario
            user_id: ID del usuario
            
        Returns:
            str: Contexto relevante formateado
        """
        # Crear una clave única para la consulta
        cache_key = f"context:{user_id}:{hashlib.md5(query.encode()).hexdigest()}"
        
        # Intentar obtener del caché primero
        cached_context = await cache_service.get(cache_key)
        if cached_context:
            logger.info(f"Contexto obtenido de caché para la consulta: {query[:50]}...")
            return cached_context
            
        try:
            # Verificar si Weaviate está configurado
            if not weaviate_service.is_configured():
                logger.warning("Weaviate no está configurado. No se obtendrá contexto adicional.")
                return ""
                
            logger.info(f"Buscando contexto relevante para la consulta: {query[:100]}...")
            
            # Realizar búsqueda semántica en Weaviate
            search_results = await weaviate_service.search_documents(
                query=query,
                user_id=user_id,
                limit=3,  # Número de resultados a devolver
                certainty=0.7  # Umbral de similitud
            )
            
            if not search_results:
                logger.info("No se encontraron resultados relevantes en Weaviate.")
                return ""
                
            context_parts = ["\n\n---\n\n**Información relevante para tu consulta:**\n\n"]
            
            for i, result in enumerate(search_results, 1):
                context_parts.append(f"**{i}. Fuente:** {result.source or 'Sin fuente'}")
                if result.title:
                    context_parts.append(f"   **Título:** {result.title}")
                if result.metadata and 'page' in result.metadata:
                    context_parts.append(f"   **Página:** {result.metadata['page']}")
                
                # Limitar la longitud del contenido para no exceder el contexto
                max_content_length = 500
                content = result.content[:max_content_length]
                if len(result.content) > max_content_length:
                    content += "..."
                
                context_parts.append(f"   **Contenido:** {content}\n")
            
            context = "\n".join(context_parts)
            
            # Guardar en caché por 1 hora
            await cache_service.set(cache_key, context, expire=3600)
            
            return context
            
        except Exception as e:
            logger.error(f"Error al obtener contexto de Weaviate: {str(e)}")
            # En caso de error, continuar sin contexto adicional
            return ""
    
    async def process_chat(
        self,
        messages: List[ChatMessage],
        user_id: str,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        db: Optional[Session] = None
    ) -> Union[ChatResponse, AsyncGenerator[Dict[str, Any], None]]:
        """
        Procesa un mensaje de chat y genera una respuesta utilizando el modelo de lenguaje.
        
        Args:
            messages: Lista de mensajes en la conversación
            user_id: ID del usuario que envía el mensaje
            conversation_id: ID de la conversación (opcional)
            metadata: Metadatos adicionales (opcional)
            stream: Si es True, devuelve un generador para streaming
            temperature: Temperatura para la generación (0-1)
            max_tokens: Número máximo de tokens en la respuesta
            db: Sesión de base de datos (opcional)
            
        Returns:
            ChatResponse con la respuesta generada o un generador para streaming
            
        Raises:
            HTTPException: Si hay un error al procesar el mensaje
        """
        db = db or self.db
        
        try:
            # Verificar que haya mensajes
            if not messages:
                raise ValueError("La lista de mensajes no puede estar vacía")
                
            # Obtener el último mensaje del usuario
            last_message = messages[-1]
            
            # Verificar que el último mensaje sea del usuario
            if last_message.role != MessageRole.USER:
                raise ValueError("El último mensaje debe ser del usuario")
                
            # Obtener el prompt del sistema personalizado para el usuario
            system_prompt = await self._get_user_system_prompt(user_id)
            
            # Obtener contexto relevante para la consulta
            context = await self._get_relevant_context(last_message.content, user_id)
            
            # Si hay contexto, agregarlo al prompt del sistema
            if context:
                system_prompt = f"{system_prompt.strip()}\n\n{context}"
            
            # Formatear mensajes para la API de OpenAI
            openai_messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # Agregar el historial de mensajes (si hay más de uno)
            for msg in messages[:-1]:  # Excluir el último mensaje que ya lo procesamos
                openai_messages.append({
                    "role": msg.role.value,
                    "content": msg.content
                })
            
            # Agregar el último mensaje del usuario
            openai_messages.append({
                "role": last_message.role.value,
                "content": last_message.content
            })
            
            # Guardar el mensaje del usuario en la base de datos
            user_message = await self.create_message(
                message_data=last_message,
                user_id=user_id,
                conversation_id=conversation_id,
                db=db
            )
            
            # Si no había conversation_id, usar el que se generó al crear el mensaje
            if not conversation_id and hasattr(user_message, 'conversation_id'):
                conversation_id = user_message.conversation_id
            
            # Generar la respuesta con OpenAI
            if stream:
                return self._stream_response(
                    openai_messages=openai_messages,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    db=db
                )
            else:
                return await self._generate_response(
                    openai_messages=openai_messages,
                    user_id=user_id,
                    conversation_id=conversation_id,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    db=db
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error al procesar el mensaje: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al procesar el mensaje: {str(e)}"
            )
    
    async def _generate_response(
        self,
        openai_messages: List[Dict[str, str]],
        user_id: str,
        conversation_id: str,
        temperature: float,
        max_tokens: int,
        db: Session
    ) -> ChatResponse:
        """
        Genera una respuesta utilizando la API de OpenAI (modo no streaming).
        
        Args:
            openai_messages: Mensajes formateados para la API de OpenAI
            user_id: ID del usuario
            conversation_id: ID de la conversación
            temperature: Temperatura para la generación
            max_tokens: Número máximo de tokens
            db: Sesión de base de datos
            
        Returns:
            ChatResponse con la respuesta generada
        """
        try:
            # Generar respuesta con OpenAI
            response = await openai_service.generate_chat_completion(
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False
            )
            
            # Extraer la respuesta
            if not response.choices or not response.choices[0].message:
                raise ValueError("No se pudo generar una respuesta válida")
                
            assistant_message = response.choices[0].message
            
            # Guardar la respuesta en la base de datos
            db_message = await self.create_message(
                message_data=ChatMessage(
                    role=MessageRole.ASSISTANT,
                    content=assistant_message.content,
                    metadata={
                        "model": response.model,
                        "usage": {
                            "prompt_tokens": response.usage.prompt_tokens,
                            "completion_tokens": response.usage.completion_tokens,
                            "total_tokens": response.usage.total_tokens
                        } if hasattr(response.usage, 'total_tokens') else {}
                    }
                ),
                user_id=user_id,
                conversation_id=conversation_id,
                db=db
            )
            
            # Retornar la respuesta
            return ChatResponse(
                id=db_message.id,
                conversation_id=conversation_id,
                role=db_message.role,
                content=db_message.content,
                created_at=db_message.created_at,
                metadata=db_message.metadata or {}
            )
            
        except Exception as e:
            logger.error(f"Error al generar la respuesta: {str(e)}", exc_info=True)
            raise
    
    async def _stream_response(
        self,
        openai_messages: List[Dict[str, str]],
        user_id: str,
        conversation_id: str,
        temperature: float,
        max_tokens: int,
        db: Session
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Genera una respuesta en streaming utilizando la API de OpenAI.
        
        Args:
            openai_messages: Mensajes formateados para la API de OpenAI
            user_id: ID del usuario
            conversation_id: ID de la conversación
            temperature: Temperatura para la generación
            max_tokens: Número máximo de tokens
            db: Sesión de base de datos
            
        Yields:
            Fragmentos de la respuesta en formato de streaming
        """
        full_content = ""
        message_id = str(uuid.uuid4())
        
        try:
            # Iniciar la generación en streaming
            stream = await openai_service.generate_chat_completion(
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True
            )
            
            # Procesar la respuesta en streaming
            async for chunk in stream:
                if not chunk.choices or not chunk.choices[0].delta:
                    continue
                    
                delta = chunk.choices[0].delta
                content = delta.content or ""
                
                # Acumular el contenido completo
                full_content += content
                
                # Enviar el fragmento al cliente
                yield {
                    "id": message_id,
                    "object": "chat.completion.chunk",
                    "created": int(datetime.now(timezone.utc).timestamp()),
                    "model": chunk.model,
                    "choices": [{
                        "index": 0,
                        "delta": {"content": content},
                        "finish_reason": None
                    }]
                }
            
            # Guardar el mensaje completo en la base de datos
            if full_content.strip():
                await self.create_message(
                    message_data=ChatMessage(
                        role=MessageRole.ASSISTANT,
                        content=full_content,
                        metadata={
                            "model": chunk.model,
                            "streaming": True
                        }
                    ),
                    user_id=user_id,
                    conversation_id=conversation_id,
                    db=db
                )
            
            # Enviar mensaje de finalización
            yield {
                "id": message_id,
                "object": "chat.completion.chunk",
                "created": int(datetime.now(timezone.utc).timestamp()),
                "model": chunk.model,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop"
                }]
            }
            
        except Exception as e:
            logger.error(f"Error en el streaming de la respuesta: {str(e)}", exc_info=True)
            # Enviar mensaje de error
            yield {
                "id": message_id,
                "object": "chat.completion.chunk",
                "created": int(datetime.now(timezone.utc).timestamp()),
                "model": "gpt-4",
                "choices": [{
                    "index": 0,
                    "delta": {
                        "content": "\n\nLo siento, ha ocurrido un error al generar la respuesta. Por favor, inténtalo de nuevo."
                    },
                    "finish_reason": "stop"
                }]
            }
    
    def _format_chat_history(self, messages: List[ChatMessage]) -> str:
        """Formatea el historial de chat para incluirlo en el contexto"""
        history = []
        for msg in messages[-5:]:  # Últimos 5 mensajes
            role = "Usuario" if msg.role == "user" else "Asistente"
            history.append(f"{role}: {msg.content}")
        return "\n".join(history)
    
    async def process_chat(
        self, 
        messages: List[ChatMessage], 
        user_id: str,
        conversation_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ChatResponse:
        """
        Procesa un mensaje de chat y devuelve la respuesta del asistente
        """
        # Obtener o crear la conversación
        conversation = await self._get_or_create_conversation(conversation_id, user_id, metadata)
        
        # Obtener el último mensaje del usuario
        user_message_content = messages[-1].content
        
        # Guardar el mensaje del usuario
        user_message = self._save_message(
            content=user_message_content,
            role=MessageRole.USER,
            conversation_id=conversation.id,
            metadata=metadata
        )
        
        try:
            # Obtener contexto relevante
            context = await self._get_relevant_context(user_message_content, user_id)
            chat_history = self._format_chat_history(messages)
            
            # Construir el prompt del sistema con el contexto
            enhanced_system_prompt = f"""
            {self.system_prompt}
            
            Contexto de la conversación:
            {chat_history}
            
            {context}
            
            Por favor, utiliza la información de contexto proporcionada para responder 
            de manera precisa y útil. Si la información no es relevante o no tienes 
            suficiente contexto, indícalo amablemente.
            """
            
            # Generar respuesta del asistente
            formatted_messages = openai_service.format_messages_for_openai(
                messages, enhanced_system_prompt
            )
            
            response = await openai_service.generate_chat_completion(
                messages=formatted_messages,
                temperature=0.7,
                max_tokens=1500
            )
            
            assistant_content = response.choices[0].message.content
            
            # Guardar la respuesta del asistente
            assistant_message = self._save_message(
                content=assistant_content,
                role=MessageRole.ASSISTANT,
                conversation_id=conversation.id,
                metadata={
                    "model": settings.OPENAI_MODEL,
                    "usage": response.usage.dict() if hasattr(response, 'usage') else None,
                    **(metadata or {})
                }
            )
            
            return ChatResponse(
                response=assistant_content,
                conversation_id=conversation.id,
                message_id=assistant_message.id,
                metadata={
                    "usage": response.usage.dict() if hasattr(response, 'usage') else None
                }
            )
            
        except Exception as e:
            # En caso de error, registrar y devolver un mensaje de error
            error_message = f"Error al procesar el mensaje: {str(e)}"
            return ChatResponse(
                response=error_message,
                conversation_id=conversation.id,
                message_id=0,
                metadata={"error": True, "message": str(e)}
            )
    
    def _get_or_create_conversation(
        self, 
        conversation_id: Optional[int], 
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConversationInDB:
        """Obtiene una conversación existente o crea una nueva"""
        if conversation_id:
            conversation = self.db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            ).first()
            if not conversation:
                raise ValueError("Conversación no encontrada o no autorizada")
            return conversation
        
        # Crear nueva conversación
        title = metadata.get('title', f'Conversación {datetime.now().strftime("%Y-%m-%d %H:%M")}')
        conversation = Conversation(
            title=title,
            user_id=user_id,
            metadata_=metadata or {}
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation
    
    def _save_message(
        self,
        content: str,
        role: MessageRole,
        conversation_id: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MessageInDB:
        """Guarda un mensaje en la base de datos"""
        message = Message(
            content=content,
            role=role,
            conversation_id=conversation_id,
            metadata_=metadata or {}
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message
        
    def get_conversation(self, conversation_id: int, user_id: str) -> Optional[ConversationInDB]:
        """Obtiene una conversación por su ID si pertenece al usuario"""
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        return conversation
    
    def get_user_conversations(self, user_id: str, skip: int = 0, limit: int = 10) -> List[ConversationInDB]:
        """Obtiene la lista de conversaciones de un usuario"""
        conversations = self.db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(Conversation.updated_at.desc()).offset(skip).limit(limit).all()
        return conversations
    
    def update_conversation(
        self, 
        conversation_id: int, 
        user_id: str, 
        title: Optional[str] = None, 
        status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[ConversationInDB]:
        """Actualiza una conversación existente"""
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        
        if not conversation:
            return None
            
        if title is not None:
            conversation.title = title
        if status is not None:
            conversation.status = status
        if metadata is not None:
            conversation.metadata_ = {**conversation.metadata_, **metadata}
            
        self.db.commit()
        self.db.refresh(conversation)
        return conversation
    
    def delete_conversation(self, conversation_id: int, user_id: str) -> bool:
        """Elimina una conversación y todos sus mensajes"""
        conversation = self.db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id
        ).first()
        
        if not conversation:
            return False
            
        self.db.delete(conversation)
        self.db.commit()
        return True
    
    def _save_message(
        self,
        content: str,
        role: MessageRole,
        conversation_id: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MessageInDB:
        """Guarda un mensaje en la base de datos"""
        message = Message(
            content=content,
            role=role,
            conversation_id=conversation_id,
            metadata_=metadata or {}
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message
