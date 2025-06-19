from datetime import datetime
from typing import Any, Dict
from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy.orm import declarative_base

# Crear una base declarativa que se usará para todos los modelos
Base = declarative_base()

class BaseModel:
    """
    Clase base para todos los modelos con campos comunes.
    """
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte el modelo a un diccionario.
        
        Returns:
            Dict[str, Any]: Diccionario con los atributos del modelo
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result
    
    def update(self, **kwargs) -> None:
        """
        Actualiza los atributos del modelo con los valores proporcionados.
        
        Args:
            **kwargs: Atributos a actualizar
        """
        for key, value in kwargs.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)
        return self

# Clase base que combina SQLAlchemy Base con nuestra funcionalidad personalizada
class Base(Base, BaseModel):
    __abstract__ = True
