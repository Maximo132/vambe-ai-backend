from fastapi import APIRouter
from app.api.endpoints import conversations, messages, auth, documents, chat

# Router principal de la API
api_router = APIRouter()

# Incluir routers de los diferentes módulos
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["conversations"])
api_router.include_router(messages.router, prefix="/messages", tags=["messages"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])

# Exportar el router para su uso en main.py
router = api_router
