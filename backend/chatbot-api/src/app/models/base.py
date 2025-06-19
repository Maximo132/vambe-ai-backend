from datetime import datetime
from sqlalchemy import Column, DateTime, func
from sqlalchemy.ext.declarative import declared_attr

from ..db.base_class import Base as BaseModel

class Base(BaseModel):
    """
    Clase base para todos los modelos con campos comunes.
    Hereda de Base que ya incluye id y métodos comunes.
    """
    __abstract__ = True
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        """
        Convierte el modelo a un diccionario.
        
        Returns:
            dict: Diccionario con los atributos del modelo
        """
        result = super().to_dict()
        # Convertir campos datetime a string ISO format
        for key, value in result.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
        return result
    
    def update(self, **kwargs):
        """
        Actualiza los atributos del modelo con los valores proporcionados.
        
        Args:
            **kwargs: Atributos a actualizar
        """
        for key, value in kwargs.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)
        return self
