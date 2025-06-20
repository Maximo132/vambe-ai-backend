"""
Punto de entrada principal de la aplicación FastAPI.

Este módulo configura e inicia la aplicación FastAPI, incluyendo la configuración
CORS, middleware, rutas y eventos de inicio/cierre.
"""
import asyncio
import logging
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_limiter import FastAPILimiter
from sqlalchemy.orm import Session

from .core.config import settings
from .db import init_db, get_async_db, get_db, async_engine, engine
from .api.endpoints import chat, conversations, messages, auth, documents, analysis, knowledge_bases
from .models import user as user_models
from .models import chat as chat_models, document as document_models, knowledge_base as knowledge_base_models
from .services.cache_service import cache_service

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
import uvicorn
from .core.app_startup import create_app
from .core.config import settings
from .api.endpoints import chat, conversations, messages, auth, documents, analysis

# Crear la aplicación FastAPI
app = create_app()

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Middleware para manejar excepciones de rate limiting
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        if "rate limit" in str(e).lower():
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Demasiadas solicitudes. Por favor, inténtalo de nuevo más tarde."}
            )
        raise

# Eventos de inicio y apagado
@app.on_event("startup")
async def startup_event():
    """
    Evento de inicio de la aplicación.
    
    Se ejecuta al iniciar la aplicación y configura todos los servicios necesarios.
    """
    logger.info("Iniciando aplicación...")
    
    try:
        # Inicializar la base de datos
        logger.info("Inicializando base de datos...")
        await init_db()
        
        # Inicializar el servicio de caché
        logger.info("Inicializando servicio de caché...")
        await cache_service.connect()
        
        # Configurar rate limiting
        logger.info("Configurando rate limiting...")
        await FastAPILimiter.init(
            cache_service.redis,
            prefix="rate_limiter",
            retry_after="x-ratelimit-retry-after"
        )
        
        logger.info("Aplicación iniciada y servicios configurados correctamente")
    except Exception as e:
        logger.error(f"Error al iniciar la aplicación: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """
    Evento de apagado de la aplicación.
    
    Se ejecuta al detener la aplicación y libera todos los recursos utilizados.
    """
    logger.info("Deteniendo aplicación...")
    
    try:
        # Cerrar conexiones de caché
        if cache_service.is_connected:
            await cache_service.close()
        
        # Cerrar conexiones de base de datos
        if engine:
            engine.dispose()
        
        if async_engine:
            await async_engine.dispose()
        
        logger.info("Aplicación detenida y recursos liberados correctamente")
    except Exception as e:
        logger.error(f"Error al detener la aplicación: {e}")
        raise

# Incluir routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Autenticación"])
app.include_router(profile.router, prefix="/api/v1/profile", tags=["Perfil de Usuario"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(knowledge_bases.router, prefix="/api/v1/knowledge-bases", tags=["Bases de Conocimiento"])
app.include_router(conversations.router, prefix="/api/v1/conversations", tags=["Conversaciones"])
app.include_router(messages.router, prefix="/api/v1/messages", tags=["Mensajes"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["Documentos"])
app.include_router(analysis.router, prefix="/api/v1/analysis", tags=["Análisis"])

# Endpoint de salud
@app.get("/health", tags=["health"])
async def health_check():
    """Verificar el estado del servicio"""
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }

# Endpoint raíz
@app.get("/", tags=["root"])
async def root():
    """Endpoint raíz"""
    return {
        "message": f"Bienvenido a {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }

# Manejador de errores global
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# Inicialización de la aplicación
if __name__ == "__main__":
    import uvicorn
    
    # Configuración de uvicorn
    config = uvicorn.Config(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        workers=settings.WORKERS,
        log_level=settings.LOG_LEVEL.lower(),
        proxy_headers=True,
        forwarded_allow_ips="*"
    )
    
    # Iniciar el servidor
    server = uvicorn.Server(config)
    
    try:
        logger.info(f"Iniciando servidor en {settings.HOST}:{settings.PORT}")
        server.run()
    except Exception as e:
        logger.error(f"Error al iniciar el servidor: {e}")
        raise
    finally:
        logger.info("Servidor detenido")
