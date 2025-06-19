from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app import crud, models
from app.schemas.chat import Message, MessageCreate, MessageUpdate
from app.api import deps

router = APIRouter()

@router.get("/", response_model=List[Message])
def read_messages(
    conversation_id: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Retrieve messages for a specific conversation.
    """
    # Verify conversation exists and user has access
    conversation = crud.conversation.get(db, id=conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    messages = crud.message.get_multi_by_conversation(
        db, conversation_id=conversation_id, skip=skip, limit=limit
    )
    return messages

@router.post("/", response_model=Message)
def create_message(
    *,
    db: Session = Depends(deps.get_db),
    message_in: MessageCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Create new message in a conversation.
    """
    # Verify conversation exists and user has access
    conversation = crud.conversation.get(db, id=message_in.conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    message = crud.message.create_with_conversation(
        db=db, obj_in=message_in, conversation_id=message_in.conversation_id
    )
    return message

@router.get("/{message_id}", response_model=Message)
def read_message(
    message_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Get a specific message by ID.
    """
    message = crud.message.get(db, id=message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Verify user has access to the conversation
    conversation = crud.conversation.get(db, id=message.conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return message

@router.put("/{message_id}", response_model=Message)
def update_message(
    *,
    db: Session = Depends(deps.get_db),
    message_id: str,
    message_in: MessageUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Update a message.
    """
    message = crud.message.get(db, id=message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Verify user has access to the conversation
    conversation = crud.conversation.get(db, id=message.conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    message = crud.message.update(db, db_obj=message, obj_in=message_in)
    return message

@router.delete("/{message_id}", response_model=Message)
def delete_message(
    *,
    db: Session = Depends(deps.get_db),
    message_id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Delete a message.
    """
    message = crud.message.get(db, id=message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Verify user has access to the conversation
    conversation = crud.conversation.get(db, id=message.conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    message = crud.message.remove(db, id=message_id)
    return message
