"""
Configuración centralizada de logging para la aplicación.

Este módulo configura el sistema de registro (logging) de Python para la aplicación,
proporcionando diferentes niveles de registro y formatos para diferentes entornos.
"""
import logging
import logging.config
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional
import json
import logging.handlers

from ..core.config import settings


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    log_format: Optional[str] = None,
    log_date_format: Optional[str] = None,
) -> None:
    """
    Configura el sistema de logging de la aplicación.

    Args:
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Ruta al archivo de log (opcional)
        log_format: Formato de los mensajes de log
        log_date_format: Formato de fecha para los logs
    """
    if log_level is None:
        log_level = settings.LOG_LEVEL
    if log_format is None:
        log_format = settings.LOG_FORMAT
    if log_date_format is None:
        log_date_format = settings.LOG_DATEFORMAT
    
    # Nivel de logging numérico
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Nivel de log inválido: {log_level}')
    
    # Configuración básica de logging
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        datefmt=log_date_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    
    # Configurar el logger raíz
    root_logger = logging.getLogger()
    
    # Si se especificó un archivo de log, agregar un FileHandler
    if log_file:
        # Asegurarse de que el directorio existe
        log_path = Path(log_file).parent
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Configurar rotación de logs (20 MB por archivo, mantener 5 archivos de respaldo)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=20 * 1024 * 1024,  # 20 MB
            backupCount=5,
            encoding='utf-8',
        )
        file_handler.setFormatter(
            logging.Formatter(fmt=log_format, datefmt=log_date_format)
        )
        root_logger.addHandler(file_handler)
    
    # Configurar el nivel de logging para bibliotecas de terceros
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # Configurar el logger para la aplicación
    app_logger = logging.getLogger(settings.APP_NAME)
    app_logger.setLevel(numeric_level)
    
    # Configurar el logger para el módulo actual
    logger = logging.getLogger(__name__)
    logger.info("Configuración de logging completada")


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Obtiene un logger con el nombre especificado.
    
    Si no se especifica un nombre, devuelve el logger raíz.
    
    Args:
        name: Nombre del logger (opcional)
        
    Returns:
        logging.Logger: Instancia del logger
    """
    if name is None:
        return logging.getLogger()
    return logging.getLogger(f"{settings.APP_NAME}.{name}")


# Configuración de logging estructurado para JSON
class JsonLogFormatter(logging.Formatter):
    """Formateador de logs en formato JSON."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Formatea el registro de log como JSON."""
        log_record = {
            'timestamp': self.formatTime(record, self.datefmt),
            'level': record.levelname,
            'name': record.name,
            'message': record.getMessage(),
            'pathname': record.pathname,
            'lineno': record.lineno,
            'funcName': record.funcName,
        }
        
        # Agregar campos adicionales si existen
        if hasattr(record, 'extra') and isinstance(record.extra, dict):
            log_record.update(record.extra)
        
        # Manejar excepciones
        if record.exc_info:
            log_record['exc_info'] = self.formatException(record.exc_info)
        
        return json.dumps(log_record, ensure_ascii=False)


def setup_structured_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
) -> None:
    """
    Configura el logging estructurado en formato JSON.
    
    Args:
        log_level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Ruta al archivo de log (opcional)
    """
    if log_level is None:
        log_level = settings.LOG_LEVEL
    
    # Nivel de logging numérico
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Nivel de log inválido: {log_level}')
    
    # Configurar el formateador JSON
    formatter = JsonLogFormatter()
    
    # Configurar el manejador de consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Configurar el logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Limpiar manejadores existentes
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Agregar el manejador de consola
    root_logger.addHandler(console_handler)
    
    # Si se especificó un archivo de log, agregar un FileHandler
    if log_file:
        # Asegurarse de que el directorio existe
        log_path = Path(log_file).parent
        log_path.mkdir(parents=True, exist_ok=True)
        
        # Configurar rotación de logs (20 MB por archivo, mantener 5 archivos de respaldo)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=20 * 1024 * 1024,  # 20 MB
            backupCount=5,
            encoding='utf-8',
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Configurar el nivel de logging para bibliotecas de terceros
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    # Configurar el logger para la aplicación
    app_logger = logging.getLogger(settings.APP_NAME)
    app_logger.setLevel(numeric_level)
    
    # Configurar el logger para el módulo actual
    logger = logging.getLogger(__name__)
    logger.info("Configuración de logging estructurado completada")


# Configurar logging al importar el módulo
if settings.LOG_JSON:
    setup_structured_logging(
        log_level=settings.LOG_LEVEL,
        log_file=settings.LOG_FILE
    )
else:
    setup_logging(
        log_level=settings.LOG_LEVEL,
        log_file=settings.LOG_FILE,
        log_format=settings.LOG_FORMAT,
        log_date_format=settings.LOG_DATEFORMAT,
    )

# Obtener el logger para este módulo
logger = get_logger(__name__)
