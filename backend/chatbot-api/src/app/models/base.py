from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import Column, Integer, DateTime, func
from datetime import datetime

Base = declarative_base()

class BaseModel:
    """Base model with common fields and methods for all models"""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @declared_attr
    def __tablename__(cls):
        """
        Generate __tablename__ automatically.
        Converts CamelCase class name to snake_case table name.
        """
        return ''.join(['_'+i.lower() if i.isupper() else i for i in cls.__name__]).lstrip('_')
    
    def to_dict(self):
        """Convert model instance to dictionary"""
        return {
            column.name: getattr(self, column.name) 
            for column in self.__table__.columns
        }
