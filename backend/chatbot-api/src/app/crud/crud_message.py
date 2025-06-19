from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.chat import Message
from app.schemas.chat import MessageCreate, MessageUpdate
from app.crud.base import CRUDBase

class CRUDMessage(CRUDBase[Message, MessageCreate, MessageUpdate]):
    def get_multi_by_conversation(
        self, db: Session, *, conversation_id: str, skip: int = 0, limit: int = 100
    ) -> List[Message]:
        return (
            db.query(self.model)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_with_conversation(
        self, db: Session, *, obj_in: MessageCreate, conversation_id: str
    ) -> Message:
        db_obj = Message(
            **obj_in.dict(exclude={"conversation_id"}),
            conversation_id=conversation_id,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

message = CRUDMessage(Message)
