from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import json
import uuid
from datetime import datetime

from ....schemas.chat import (
    ChatMessage, ChatRequest, ChatResponse, ChatResponseChunk,
    ConversationInDB, ConversationCreate, ConversationUpdate, MessageRole
)
from ....services.chat_service import ChatService
from ....db.session import get_db
from ....core.security import get_current_user
from ....core.config import settings

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Endpoint para enviar mensajes al chatbot y recibir respuestas.
    
    Args:
        request: Datos de la solicitud de chat
        db: Sesión de base de datos
        current_user: Usuario autenticado
        
    Returns:
        Respuesta del asistente con el mensaje generado
    """
    try:
        # Verificar que el user_id del token coincida con el de la solicitud
        if current_user["username"] != request.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No autorizado para realizar esta acción"
            )
            
        chat_service = ChatService(db)
        response = await chat_service.process_chat(
            messages=request.messages,
            user_id=request.user_id,
            conversation_id=request.conversation_id,
            metadata=request.metadata,
            stream=False,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar el mensaje: {str(e)}"
        )

@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Endpoint para enviar mensajes al chatbot y recibir respuestas en streaming.
    
    Args:
        request: Datos de la solicitud de chat
        db: Sesión de base de datos
        current_user: Usuario autenticado
        
    Returns:
        StreamingResponse con la respuesta del asistente en tiempo real
    """
    try:
        # Verificar que el user_id del token coincida con el de la solicitud
        if current_user["username"] != request.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No autorizado para realizar esta acción"
            )
            
        chat_service = ChatService(db)
        
        # Crear una función generadora para el streaming
        async def event_generator():
            try:
                # Procesar el chat en modo streaming
                response_stream = await chat_service.process_chat(
                    messages=request.messages,
                    user_id=request.user_id,
                    conversation_id=request.conversation_id,
                    metadata=request.metadata,
                    stream=True,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                )
                
                # Enviar cada fragmento de la respuesta
                async for chunk in response_stream:
                    yield f"data: {json.dumps(chunk)}\n\n"
                
                # Señal de finalización
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                logger.error(f"Error en el streaming del chat: {str(e)}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Importante para Nginx
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al iniciar el streaming del chat: {str(e)}"
        )

@router.get("/conversations/{conversation_id}/messages", response_model=List[ChatMessage])
async def get_conversation_messages(
    conversation_id: str,
    skip: int = Query(0, ge=0, description="Número de mensajes a saltar"),
    limit: int = Query(100, le=1000, description="Número máximo de mensajes a devolver"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene los mensajes de una conversación específica con paginación.
    
    Args:
        conversation_id: ID de la conversación
        skip: Número de mensajes a saltar
        limit: Número máximo de mensajes a devolver
        db: Sesión de base de datos
        current_user: Usuario autenticado
        
    Returns:
        Lista de mensajes de la conversación
    """
    try:
        chat_service = ChatService(db)
        messages = await chat_service.get_conversation_messages(
            conversation_id=conversation_id,
            user_id=current_user["username"],
            skip=skip,
            limit=limit
        )
        
        return messages
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener los mensajes: {str(e)}"
        )

@router.get("/conversations", response_model=List[ConversationInDB])
async def list_conversations(
    skip: int = Query(0, ge=0, description="Número de conversaciones a saltar"),
    limit: int = Query(20, le=100, description="Número máximo de conversaciones a devolver"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene la lista de conversaciones del usuario autenticado con paginación.
    
    Args:
        skip: Número de conversaciones a saltar
        limit: Número máximo de conversaciones a devolver
        db: Sesión de base de datos
        current_user: Usuario autenticado
        
    Returns:
        Lista de conversaciones del usuario
    """
    try:
        chat_service = ChatService(db)
        conversations = await chat_service.list_conversations(
            user_id=current_user["username"],
            skip=skip,
            limit=limit
        )
        
        return conversations
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al listar las conversaciones: {str(e)}"
        )

@router.get("/conversations/{conversation_id}", response_model=ConversationInDB)
async def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Obtiene los detalles de una conversación específica.
    
    Args:
        conversation_id: ID de la conversación
        db: Sesión de base de datos
        current_user: Usuario autenticado
        
    Returns:
        Detalles de la conversación
    """
    try:
        chat_service = ChatService(db)
        conversation = await chat_service.get_conversation(
            conversation_id=conversation_id,
            user_id=current_user["username"]
        )
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversación no encontrada o no autorizada"
            )
        
        return conversation
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener la conversación: {str(e)}"
        )

@router.post("/conversations", response_model=ConversationInDB, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Crea una nueva conversación.
    
    Args:
        conversation: Datos para crear la conversación
        db: Sesión de base de datos
        current_user: Usuario autenticado
        
    Returns:
        Conversación creada
    """
    try:
        # Verificar que el user_id coincida con el usuario autenticado
        if current_user["username"] != conversation.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No autorizado para crear una conversación para otro usuario"
            )
        
        chat_service = ChatService(db)
        new_conversation = await chat_service.create_conversation(
            conversation_data=conversation,
            user_id=current_user["username"]
        )
        
        return new_conversation
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear la conversación: {str(e)}"
        )

@router.put("/conversations/{conversation_id}", response_model=ConversationInDB)
async def update_conversation(
    conversation_id: str,
    conversation_update: ConversationUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Actualiza una conversación existente.
    
    Args:
        conversation_id: ID de la conversación a actualizar
        conversation_update: Datos a actualizar
        db: Sesión de base de datos
        current_user: Usuario autenticado
        
    Returns:
        Conversación actualizada
    """
    try:
        chat_service = ChatService(db)
        updated_conversation = await chat_service.update_conversation(
            conversation_id=conversation_id,
            conversation_data=conversation_update,
            user_id=current_user["username"]
        )
        
        if not updated_conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversación no encontrada o no autorizada"
            )
        
        return updated_conversation
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar la conversación: {str(e)}"
        )

@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Elimina una conversación y todos sus mensajes.
    
    Args:
        conversation_id: ID de la conversación a eliminar
        db: Sesión de base de datos
        current_user: Usuario autenticado
    """
    try:
        chat_service = ChatService(db)
        deleted = await chat_service.delete_conversation(
            conversation_id=conversation_id,
            user_id=current_user["username"]
        )
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversación no encontrada o no autorizada"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar la conversación: {str(e)}"
        )
    
    return None
