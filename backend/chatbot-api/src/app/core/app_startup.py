"""
Módulo de inicialización de la aplicación.

Este módulo se encarga de configurar e inicializar todos los componentes
necesarios para el funcionamiento de la aplicación.
"""
import logging
from typing import Optional, Callable, List, Dict, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware

from .config import settings, logger
from ..services.cache_service import CacheService
from ..services.weaviate_service import WeaviateService
from ..db.session import init_db, close_db

# Obtener logger
logger = logging.getLogger(__name__)


def setup_middlewares(app: FastAPI) -> None:
    """Configura los middlewares de la aplicación."""
    # Middleware CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Redirigir a HTTPS en producción
    if not settings.DEBUG and settings.SECURE_COOKIES:
        app.add_middleware(HTTPSRedirectMiddleware)
    
    # Otros middlewares pueden ir aquí


def setup_events(app: FastAPI) -> None:
    """Configura los eventos de inicio y cierre de la aplicación."""
    @app.on_event("startup")
    async def startup_event() -> None:
        """Evento de inicio de la aplicación."""
        logger.info("Iniciando la aplicación %s v%s", 
                   settings.APP_NAME, settings.APP_VERSION)
        
        # Inicializar la base de datos
        await init_db()
        
        # Crear directorio de subidas si no existe
        if settings.STORAGE_PROVIDER == 'local':
            import os
            from pathlib import Path
            
            upload_dir = Path(settings.UPLOAD_DIR)
            upload_dir.mkdir(parents=True, exist_ok=True)
            os.chmod(upload_dir, 0o755)
            logger.info(f"Directorio de subidas listo: {upload_dir}")
        
        # Crear un usuario administrador por defecto si no existe
        if settings.CREATE_DEFAULT_ADMIN:
            from sqlalchemy.orm import Session
            from ..db.session import SessionLocal
            from ..models.user import User, UserRole
            from ..core.security import get_password_hash
            from ..core.config import settings
            
            db = SessionLocal()
            try:
                admin = db.query(User).filter(User.username == settings.DEFAULT_ADMIN_USERNAME).first()
                if not admin:
                    admin = User(
                        username=settings.DEFAULT_ADMIN_USERNAME,
                        email=settings.DEFAULT_ADMIN_EMAIL,
                        hashed_password=get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
                        full_name="Administrador",
                        role=UserRole.ADMIN,
                        is_superuser=True,
                        is_verified=True,
                        is_active=True
                    )
                    db.add(admin)
                    db.commit()
                    logger.info(f"Usuario administrador por defecto '{settings.DEFAULT_ADMIN_USERNAME}' creado")
                else:
                    logger.info(f"Usuario administrador '{settings.DEFAULT_ADMIN_USERNAME}' ya existe")
            except Exception as e:
                logger.error(f"Error al crear el usuario administrador: {e}")
                db.rollback()
            finally:
                db.close()
        logger.info("Base de datos inicializada")
        
        # Inicializar el servicio de caché
        await CacheService.initialize(settings.REDIS_URL)
        logger.info("Servicio de caché inicializado")
        
        # Inicializar Weaviate si está configurado
        if settings.WEAVIATE_URL:
            try:
                await WeaviateService.initialize(
                    url=settings.WEAVIATE_URL,
                    api_key=settings.WEAVIATE_API_KEY or None,
                    embedding_model=settings.WEAVIATE_EMBEDDING_MODEL
                )
                logger.info("Servicio Weaviate inicializado")
            except Exception as e:
                logger.error("Error al inicializar Weaviate: %s", str(e), exc_info=True)
    
    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        """Evento de cierre de la aplicación."""
        logger.info("Cerrando la aplicación...")
        
        # Cerrar conexiones a la base de datos
        await close_db()
        logger.info("Conexiones a la base de datos cerradas")
        
        # Cerrar conexión a Redis
        await CacheService.close()
        logger.info("Conexión a Redis cerrada")
        
        logger.info("Aplicación cerrada correctamente")


def create_app(
    title: str = None,
    description: str = "API para el chatbot de Vambe.ai",
    version: str = None,
    **kwargs: Any
) -> FastAPI:
    """
    Crea y configura una instancia de FastAPI.
    
    Args:
        title: Título de la API. Si no se especifica, se usa el de configuración.
        description: Descripción de la API.
        version: Versión de la API. Si no se especifica, se usa el de configuración.
        **kwargs: Argumentos adicionales para FastAPI.
        
    Returns:
        FastAPI: Instancia de FastAPI configurada.
    """
    # Configuración de la aplicación
    app = FastAPI(
        title=title or settings.APP_NAME,
        description=description,
        version=version or settings.APP_VERSION,
        debug=settings.DEBUG,
        **kwargs
    )
    
    # Configurar middlewares
    setup_middlewares(app)
    
    # Configurar eventos de inicio/cierre
    setup_events(app)
    
    # Configurar rutas de la API
    from ..api.v1.api import api_router
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    # Ruta de verificación de salud
    @app.get("/health", include_in_schema=False)
    async def health_check() -> Dict[str, str]:
        """Verificación de salud de la API."""
        return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
    
    return app
