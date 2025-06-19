from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List, Optional
import uvicorn
import logging
import json

from .core.config import settings
from .db.session import SessionLocal, engine
from .api.endpoints import chat, conversations, messages, auth, documents, analysis
from .models import user as user_models
from .models import chat as chat_models, document as document_models
from .services.cache_service import cache_service
from fastapi_limiter import FastAPILimiter
from fastapi.responses import JSONResponse

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
    """Evento de inicio de la aplicación"""
    # Inicializar el servicio de caché
    await cache_service.connect()
    
    # Configurar rate limiting
    await FastAPILimiter.init(
        cache_service.redis,
        prefix="rate_limiter",
        retry_after="x-ratelimit-retry-after"
    )
    logger.info("Aplicación iniciada y servicios configurados")

@app.on_event("shutdown")
async def shutdown_event():
    """Evento de apagado de la aplicación"""
    # Cerrar conexiones
    await cache_service.close()
    logger.info("Aplicación detenida y recursos liberados")

# Incluir routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Autenticación"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
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
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=4
    )
