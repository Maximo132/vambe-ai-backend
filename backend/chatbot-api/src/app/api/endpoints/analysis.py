from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_limiter.depends import RateLimiter
from typing import List, Dict, Any
import logging
import openai
import json

from ....services.chat_service import ChatService
from ....services.cache_service import cache_service
from ....db.session import get_db
from ....core.security import get_current_user
from ....schemas.chat import ChatMessage

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post(
    "/analyze/sentiment",
    dependencies=[Depends(RateLimiter(times=100, minutes=1))],
    response_model=Dict[str, Any]
)
async def analyze_sentiment(
    messages: List[ChatMessage],
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    Analiza el sentimiento de una conversación.
    Devuelve un análisis de sentimiento para cada mensaje y un resumen general.
    """
    try:
        # Crear una clave única para el caché
        cache_key = f"sentiment_analysis:{hash(str(messages))}"
        
        # Intentar obtener del caché primero
        cached_result = await cache_service.get(cache_key)
        if cached_result:
            return cached_result
            
        # Si no está en caché, usar OpenAI para el análisis
        system_prompt = """
        Eres un analista de sentimientos experto. Analiza los mensajes y proporciona:
        1. Sentimiento general (positivo, negativo, neutro)
        2. Puntuación de sentimiento (0-1)
        3. Palabras clave emocionales
        4. Resumen del análisis
        
        Responde en formato JSON.
        """
        
        chat_service = ChatService(db)
        response = await chat_service.process_chat(
            messages=[{"role": "system", "content": system_prompt}] + messages,
            user_id=current_user["username"],
            temperature=0.3  # Baja temperatura para respuestas más deterministas
        )
        
        try:
            # Intentar parsear la respuesta como JSON
            analysis = json.loads(response.content)
        except json.JSONDecodeError:
            # Si falla, devolver un análisis básico
            analysis = {
                "sentiment": "neutral",
                "score": 0.5,
                "keywords": [],
                "summary": "No se pudo analizar el sentimiento."
            }
        
        # Guardar en caché por 1 hora
        await cache_service.set(cache_key, analysis, expire=3600)
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error en el análisis de sentimiento: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al analizar el sentimiento"
        )
