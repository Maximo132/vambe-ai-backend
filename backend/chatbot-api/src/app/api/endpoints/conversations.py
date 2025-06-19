from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app import crud, models
from app.schemas.chat import Conversation, ConversationCreate, ConversationUpdate
from app.api import deps

router = APIRouter()

@router.get("/", response_model=List[Conversation])
def read_conversations(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Retrieve conversations for the current user.
    """
    conversations = crud.conversation.get_multi_by_user(
        db, user_id=current_user.id, skip=skip, limit=limit
    )
    return conversations

@router.post("/", response_model=Conversation)
def create_conversation(
    *,
    db: Session = Depends(deps.get_db),
    conversation_in: ConversationCreate,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Create new conversation.
    """
    conversation = crud.conversation.create_with_owner(
        db=db, obj_in=conversation_in, owner_id=current_user.id
    )
    return conversation

@router.get("/{conversation_id}", response_model=Conversation)
def read_conversation(
    conversation_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Get a specific conversation by ID.
    """
    conversation = crud.conversation.get(db, id=conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return conversation

@router.put("/{conversation_id}", response_model=Conversation)
def update_conversation(
    *,
    db: Session = Depends(deps.get_db),
    conversation_id: str,
    conversation_in: ConversationUpdate,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Update a conversation.
    """
    conversation = crud.conversation.get(db, id=conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    conversation = crud.conversation.update(db, db_obj=conversation, obj_in=conversation_in)
    return conversation

@router.delete("/{conversation_id}", response_model=Conversation)
def delete_conversation(
    *,
    db: Session = Depends(deps.get_db),
    conversation_id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Delete a conversation.
    """
    conversation = crud.conversation.get(db, id=conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    conversation = crud.conversation.remove(db, id=conversation_id)
    return conversation

@router.post("/{conversation_id}/archive", response_model=Conversation)
def archive_conversation(
    *,
    db: Session = Depends(deps.get_db),
    conversation_id: str,
    current_user: models.User = Depends(deps.get_current_active_user),
):
    """
    Archive a conversation.
    """
    conversation = crud.conversation.get(db, id=conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conversation.user_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    conversation = crud.conversation.archive(db, db_obj=conversation)
    return conversation
