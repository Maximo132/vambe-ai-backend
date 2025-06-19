from typing import Any, Dict
from sqlalchemy.ext.declarative import as_declarative, declared_attr
from sqlalchemy import Column, Integer

@as_declarative()
class Base:
    """Clase base para todos los modelos SQLAlchemy."""
    id = Column(Integer, primary_key=True, index=True)
    __name__: str

    # Genera el nombre de la tabla a partir del nombre de la clase
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte el modelo a un diccionario.
        
        Returns:
            Dict[str, Any]: Diccionario con los atributos del modelo
        """
        result = {}
        for column in self.__table__.columns:
            result[column.name] = getattr(self, column.name)
        return result
    
    def update(self, **kwargs: Any) -> None:
        """
        Actualiza los atributos del modelo con los valores proporcionados.
        
        Args:
            **kwargs: Atributos a actualizar
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
