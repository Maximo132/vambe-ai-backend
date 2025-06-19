"""
Módulo principal del paquete core.

Este paquete contiene la configuración y la lógica central de la aplicación.
"""

# Importar la configuración para que esté disponible directamente desde el paquete
from .config import settings, logger
from .app_startup import create_app

__all__ = ["settings", "logger", "create_app"]
