from fastapi import (
    APIRouter, Depends, HTTPException, status, Query, 
    Request, BackgroundTasks, Response
)
from fastapi.responses import StreamingResponse, JSONResponse
from typing import List, Optional, Dict, Any, Union, AsyncGenerator
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
import json
import uuid
import logging
from datetime import datetime

from ....schemas.chat import (
    ChatMessage, ChatRequest, ChatResponse, ChatResponseChunk,
    ConversationInDB, ConversationCreate, ConversationUpdate, MessageRole,
    MessageInDB, MessageCreate
)
from ....schemas.document import DocumentSearchQuery
from ....services.chat_service import ChatService
from ....services.document_service import DocumentService
from ....services.knowledge_service import KnowledgeBaseService
from ....db.session import get_db, get_async_db
from ....core.security import get_current_user, get_current_user_id
from ....core.config import settings
from ....models.message import Message
from ....models.conversation import Conversation

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def process_chat_message(
    message: MessageCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Procesa un mensaje del usuario y devuelve la respuesta del asistente.
    
    Args:
        message: Datos del mensaje a procesar
        background_tasks: Tareas en segundo plano
        db: Sesión de base de datos
        current_user_id: ID del usuario autenticado
        
    Returns:
        Respuesta del asistente
    """
    try:
        # Verificar que el usuario tenga acceso a la conversación
        chat_service = ChatService(db)
        
        # Procesar el mensaje
        response = await chat_service.process_message(
            message=message.content,
            conversation_id=str(message.conversation_id),
            user_id=current_user_id,
            metadata=message.metadata,
            stream=False
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al procesar mensaje: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar el mensaje: {str(e)}"
        )

@router.post("/chat/stream")
async def process_chat_stream(
    message: MessageCreate,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Procesa un mensaje del usuario y devuelve la respuesta del asistente en streaming.
    
    Args:
        message: Datos del mensaje a procesar
        db: Sesión de base de datos
        current_user_id: ID del usuario autenticado
        
    Returns:
        StreamingResponse con la respuesta del asistente
    """
    try:
        chat_service = ChatService(db)
        
        # Función generadora para el streaming
        async def event_generator():
            try:
                # Procesar el mensaje en modo streaming
                response_stream = await chat_service.process_message(
                    message=message.content,
                    conversation_id=str(message.conversation_id),
                    user_id=current_user_id,
                    metadata=message.metadata,
                    stream=True
                )
                
                # Enviar cada chunk de la respuesta
                async for chunk in response_stream:
                    yield f"data: {json.dumps(chunk.dict())}\n\n"
                
                # Señal de finalización
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"Error en el streaming del chat: {str(e)}", exc_info=True)
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al iniciar el streaming del chat: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al iniciar el streaming del chat: {str(e)}"
        )

@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageInDB])
async def get_conversation_messages(
    conversation_id: str,
    skip: int = Query(0, ge=0, description="Número de mensajes a saltar"),
    limit: int = Query(100, le=1000, description="Número máximo de mensajes a devolver"),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Obtiene los mensajes de una conversación específica con paginación.
    
    Args:
        conversation_id: ID de la conversación
        skip: Número de mensajes a saltar
        limit: Número máximo de mensajes a devolver
        db: Sesión de base de datos
        current_user_id: ID del usuario autenticado
        
    Returns:
        Lista de mensajes de la conversación
    """
    try:
        chat_service = ChatService(db)
        messages = await chat_service._get_conversation_history(
            conversation_id=conversation_id,
            limit=limit,
            before=datetime.utcnow() if skip == 0 else None
        )
        
        # Aplicar paginación
        if skip > 0 and skip < len(messages):
            messages = messages[skip:skip+limit]
        elif skip >= len(messages):
            messages = []
        
        return messages
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener mensajes de la conversación {conversation_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener los mensajes: {str(e)}"
        )

@router.get("/conversations", response_model=List[ConversationInDB])
async def list_conversations(
    skip: int = Query(0, ge=0, description="Número de conversaciones a saltar"),
    limit: int = Query(20, le=100, description="Número máximo de conversaciones a devolver"),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Obtiene la lista de conversaciones del usuario autenticado con paginación.
    
    Args:
        skip: Número de conversaciones a saltar
        limit: Número máximo de conversaciones a devolver
        db: Sesión de base de datos
        current_user_id: ID del usuario autenticado
        
    Returns:
        Lista de conversaciones del usuario
    """
    try:
        # Obtener las conversaciones del usuario
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == current_user_id)
            .order_by(Conversation.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        conversations = result.scalars().all()
        
        # Obtener el último mensaje de cada conversación
        for conv in conversations:
            last_message = await db.execute(
                select(Message)
                .where(Message.conversation_id == conv.id)
                .order_by(Message.created_at.desc())
                .limit(1)
            )
            last_message = last_message.scalars().first()
            
            if last_message:
                # Usar el patrón de asignación de atributos dinámicos
                setattr(conv, "last_message", last_message.content[:100])  # Primeros 100 caracteres
                setattr(conv, "last_message_at", last_message.created_at)
        
        return conversations
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al listar conversaciones para el usuario {current_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener las conversaciones: {str(e)}"
        )

@router.get("/conversations/{conversation_id}", response_model=ConversationInDB)
async def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Obtiene los detalles de una conversación específica.
    
    Args:
        conversation_id: ID de la conversación
        db: Sesión de base de datos
        current_user_id: ID del usuario autenticado
        
    Returns:
        Detalles de la conversación
    """
    try:
        # Obtener la conversación
        result = await db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .where(Conversation.user_id == current_user_id)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversación no encontrada o no tienes permiso para acceder a ella"
            )
            
        # Obtener el último mensaje
        last_message = await db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_message = last_message.scalars().first()
        
        if last_message:
            # Usar el patrón de asignación de atributos dinámicos
            setattr(conversation, "last_message", last_message.content[:100])  # Primeros 100 caracteres
            setattr(conversation, "last_message_at", last_message.created_at)
            
        return conversation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener la conversación {conversation_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener la conversación: {str(e)}"
        )

@router.post("/conversations", response_model=ConversationInDB, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation: ConversationCreate,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Crea una nueva conversación.
    
    Args:
        conversation: Datos para crear la conversación
        db: Sesión de base de datos
        current_user_id: ID del usuario autenticado
        
    Returns:
        Conversación creada
    """
    try:
        # Crear la conversación
        db_conversation = Conversation(
            id=str(uuid.uuid4()),
            user_id=current_user_id,
            title=conversation.title or "Nueva conversación",
            metadata=conversation.metadata or {}
        )
        
        db.add(db_conversation)
        await db.commit()
        await db.refresh(db_conversation)
        
        return db_conversation
        
    except Exception as e:
        logger.error(f"Error al crear conversación para el usuario {current_user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear la conversación: {str(e)}"
        )

@router.put("/conversations/{conversation_id}", response_model=ConversationInDB)
async def update_conversation(
    conversation_id: str,
    conversation_update: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Actualiza una conversación existente.
    
    Args:
        conversation_id: ID de la conversación a actualizar
        conversation_update: Datos a actualizar
        db: Sesión de base de datos
        current_user_id: ID del usuario autenticado
        
    Returns:
        Conversación actualizada
    """
    try:
        # Obtener la conversación existente
        result = await db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .where(Conversation.user_id == current_user_id)
        )
        db_conversation = result.scalar_one_or_none()
        
        if not db_conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversación no encontrada o no tienes permiso para modificarla"
            )
        
        # Actualizar los campos
        update_data = conversation_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_conversation, field, value)
        
        db_conversation.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(db_conversation)
        
        return db_conversation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al actualizar la conversación {conversation_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar la conversación: {str(e)}"
        )

@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Elimina una conversación y todos sus mensajes.
    
    Args:
        conversation_id: ID de la conversación a eliminar
        db: Sesión de base de datos
        current_user_id: ID del usuario autenticado
    """
    try:
        # Verificar que la conversación exista y pertenezca al usuario
        result = await db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .where(Conversation.user_id == current_user_id)
        )
        conversation = result.scalar_one_or_none()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversación no encontrada o no tienes permiso para eliminarla"
            )
        
        # Eliminar los mensajes de la conversación
        await db.execute(
            delete(Message)
            .where(Message.conversation_id == conversation_id)
        )
        
        # Eliminar la conversación
        await db.delete(conversation)
        await db.commit()
        
        return Response(status_code=status.HTTP_204_NO_CONTENT)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al eliminar la conversación {conversation_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar la conversación: {str(e)}"
        )
