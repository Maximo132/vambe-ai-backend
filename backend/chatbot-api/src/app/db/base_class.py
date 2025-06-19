"""
Este archivo ya no es necesario ya que hemos movido la funcionalidad a models/base.py
Se mantiene por compatibilidad con el código existente, pero debería eliminarse en el futuro.
"""

# Importar la nueva implementación de Base
from app.models.base import Base

# Exportar Base para mantener la compatibilidad con el código existente
__all__ = ['Base']
