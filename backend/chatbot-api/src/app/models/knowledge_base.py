from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base_class import Base

# Tabla de asociación para la relación muchos a muchos entre KnowledgeBase y Document
knowledge_base_documents = Table(
    'knowledge_base_documents',
    Base.metadata,
    Column('knowledge_base_id', Integer, ForeignKey('knowledge_bases.id'), primary_key=True),
    Column('document_id', Integer, ForeignKey('documents.id'), primary_key=True)
)

class KnowledgeBase(Base):
    """Modelo para almacenar bases de conocimiento.
    
    Una base de conocimiento es una colección lógica de documentos relacionados.
    """
    __tablename__ = "knowledge_bases"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    owner = relationship("User", back_populates="knowledge_bases")
    
    # Relación muchos a muchos con Document
    documents = relationship(
        "Document",
        secondary=knowledge_base_documents,
        back_populates="knowledge_bases"
    )
    
    # Configuración para búsqueda vectorial
    weaviate_class = "KnowledgeBase"
    
    def __repr__(self):
        return f"<KnowledgeBase {self.name}>"
