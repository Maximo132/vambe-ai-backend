from typing import List, Dict, Any, Optional, Union, AsyncGenerator
from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
import logging
import json
import uuid

from fastapi import HTTPException, status

from ..models.chat import Conversation, Message, MessageRole, Document as DocumentModel
from ..models.user import User
from ..schemas.chat import (
    ChatMessage, ChatResponse, ConversationInDB, MessageInDB, Document,
    ConversationCreate, ConversationUpdate
)
from .openai_service import openai_service
from .weaviate_service import weaviate_service
from ..core.config import settings
from ..core.security import get_password_hash
from ..db.session import get_db

# Configurar logging
logger = logging.getLogger(__name__)

class ChatService:
    """
    Servicio para manejar la lógica de negocio relacionada con el chat.
    Se encarga de gestionar conversaciones, mensajes e interacciones con la IA.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.default_system_prompt = """
        Eres un asistente de IA útil, amable y profesional llamado Vambe AI. 
        Responde a las preguntas de manera clara y concisa. 
        Si no estás seguro de algo, es mejor decirlo que inventar información.
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
            # Aquí podrías obtener un prompt personalizado para el usuario desde la base de datos
            # Por ahora, devolvemos el prompt por defecto
            return self.default_system_prompt
        except Exception as e:
            logger.error(f"Error al obtener el prompt del sistema para el usuario {user_id}: {str(e)}")
            return self.default_system_prompt
    
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
            
            return "\n".join(context_parts)
            
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
