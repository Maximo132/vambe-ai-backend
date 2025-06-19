from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List
import uvicorn
import logging

from .core.config import settings
from .db.session import SessionLocal, engine
from .api.endpoints import chat, conversations, messages, auth, documents
from .models import user as user_models
from .models import chat as chat_models, document as document_models

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_tables():
    """Crea las tablas en la base de datos"""
    logger.info("Creando tablas en la base de datos...")
    user_models.Base.metadata.create_all(bind=engine)
    chat_models.Base.metadata.create_all(bind=engine)
    document_models.Base.metadata.create_all(bind=engine)
    logger.info("Tablas creadas exitosamente")

def init_db():
    """Inicializa la base de datos con datos por defecto"""
    db = SessionLocal()
    try:
        # Aquí podrías agregar la inicialización de datos por defecto
        # Por ejemplo, crear un usuario administrador
        from .initial_data import init_db as init_db_data
        init_db_data(db)
    except Exception as e:
        logger.error(f"Error al inicializar la base de datos: {e}")
        raise
    finally:
        db.close()

# Crear tablas en la base de datos al iniciar
create_tables()

# Inicializar datos por defecto
init_db()

# Crear aplicación FastAPI
app = FastAPI(
    title=settings.APP_NAME,
    description="API para el servicio de chatbot conversacional de Vambe.ai",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas de la API
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["authentication"]
)

app.include_router(
    chat.router,
    prefix="/api/v1/chat",
    tags=["chat"]
)

app.include_router(
    conversations.router,
    prefix="/api/v1/conversations",
    tags=["conversations"]
)

app.include_router(
    messages.router,
    prefix="/api/v1/messages",
    tags=["messages"]
)

app.include_router(
    documents.router,
    prefix="/api/v1/documents",
    tags=["documents"]
)

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
