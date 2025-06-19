import openai
import json
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator, Union
from datetime import datetime
from fastapi import HTTPException
from ..core.config import settings
from ..schemas.chat import ChatMessage, MessageRole

# Configurar logging
logger = logging.getLogger(__name__)

class OpenAIService:
    """
    Servicio para interactuar con la API de OpenAI.
    Maneja la generación de respuestas de chat, embeddings y otras operaciones.
    """
    
    def __init__(self):
        """Inicializa el cliente de OpenAI con la clave API de configuración."""
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY no está configurada en las variables de entorno")
            
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL
        self.embedding_model = settings.OPENAI_EMBEDDING_MODEL

    async def generate_chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Genera una respuesta de chat usando la API de OpenAI.
        
        Args:
            messages: Lista de mensajes en el formato de chat de OpenAI
            temperature: Controla la aleatoriedad de las respuestas (0-1)
            max_tokens: Número máximo de tokens en la respuesta
            stream: Si es True, devuelve un generador para streaming
            **kwargs: Argumentos adicionales para la API de OpenAI
            
        Returns:
            Dict con la respuesta de la API de OpenAI o un generador para streaming
            
        Raises:
            HTTPException: Si hay un error al comunicarse con la API de OpenAI
        """
        try:
            if not messages:
                raise ValueError("La lista de mensajes no puede estar vacía")
                
            logger.info(f"Enviando solicitud a OpenAI con modelo {self.model}")
            
            if stream:
                return await self._stream_chat_completion(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            # Convertir el objeto de respuesta a un diccionario
            return self._process_chat_completion(response)
            
        except openai.APIError as e:
            logger.error(f"Error de API de OpenAI: {str(e)}")
            raise HTTPException(
                status_code=502,
                detail=f"Error en el servicio de OpenAI: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error inesperado en generate_chat_completion: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error al generar la respuesta: {str(e)}"
            )
    
    async def _stream_chat_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Maneja el streaming de respuestas de chat desde la API de OpenAI.
        """
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                **kwargs
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield {
                        "id": chunk.id,
                        "object": chunk.object,
                        "created": chunk.created,
                        "model": chunk.model,
                        "choices": [{
                            "delta": {"content": chunk.choices[0].delta.content},
                            "index": chunk.choices[0].index,
                            "finish_reason": chunk.choices[0].finish_reason
                        }]
                    }
        except Exception as e:
            logger.error(f"Error en el streaming de OpenAI: {str(e)}")
            raise
    
    def _process_chat_completion(self, response) -> Dict[str, Any]:
        """Procesa la respuesta de la API de OpenAI a un formato estándar."""
        return {
            "id": response.id,
            "object": response.object,
            "created": response.created,
            "model": response.model,
            "choices": [{
                "message": {
                    "role": response.choices[0].message.role,
                    "content": response.choices[0].message.content
                },
                "index": response.choices[0].index,
                "finish_reason": response.choices[0].finish_reason
            }],
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            } if hasattr(response, 'usage') else {}
        }

    async def generate_embeddings(
        self, 
        texts: Union[str, List[str]],
        model: Optional[str] = None
    ) -> List[List[float]]:
        """
        Genera embeddings de texto usando la API de OpenAI.
        
        Args:
            texts: Texto o lista de textos para generar embeddings
            model: Modelo de embedding a utilizar (opcional)
            
        Returns:
            Lista de vectores de embedding
            
        Raises:
            HTTPException: Si hay un error al generar los embeddings
        """
        try:
            if isinstance(texts, str):
                texts = [texts]
                
            model = model or self.embedding_model
            response = await self.client.embeddings.create(
                input=texts,
                model=model
            )
            
            # Extraer los embeddings de la respuesta
            return [item.embedding for item in response.data]
            
        except Exception as e:
            logger.error(f"Error al generar embeddings: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error al generar embeddings: {str(e)}"
            )

    def format_messages_for_openai(
        self, 
        messages: List[ChatMessage], 
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
