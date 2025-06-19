from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.chat import Conversation, ConversationStatus
from app.schemas.chat import ConversationCreate, ConversationUpdate
from app.crud.base import CRUDBase

class CRUDConversation(CRUDBase[Conversation, ConversationCreate, ConversationUpdate]):
    def get_multi_by_user(
        self, db: Session, *, user_id: str, skip: int = 0, limit: int = 100
    ) -> List[Conversation]:
        return (
            db.query(self.model)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_active_conversations(
        self, db: Session, *, user_id: str, skip: int = 0, limit: int = 100
    ) -> List[Conversation]:
        return (
            db.query(self.model)
            .filter(
                Conversation.user_id == user_id,
                Conversation.status == ConversationStatus.ACTIVE
            )
            .order_by(Conversation.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def archive(self, db: Session, *, db_obj: Conversation) -> Conversation:
        db_obj.status = ConversationStatus.ARCHIVED
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

conversation = CRUDConversation(Conversation)
