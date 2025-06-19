"""
Servicio para interactuar con la API de OpenAI.

Este módulo proporciona una interfaz de alto nivel para interactuar con los servicios
de OpenAI, incluyendo chat, generación de texto, embeddings y más.
"""
import asyncio
import json
import logging
import time
import hashlib
from typing import List, Dict, Any, Optional, AsyncGenerator, Union, Literal, Type, TypeVar, cast
from datetime import datetime, timedelta
from functools import wraps

import openai
from openai import AsyncOpenAI, APIError, RateLimitError, APITimeoutError, APIConnectionError
from pydantic import BaseModel, Field, validator
from fastapi import HTTPException, status

from ..core.config import settings, logger
from ..core.cache_service import cache
from ..schemas.chat import ChatMessage, MessageRole, ChatResponse, ChatResponseChunk

# Tipo genérico para modelos de Pydantic
T = TypeVar('T', bound=BaseModel)

# Constantes
DEFAULT_TIMEOUT = 30.0  # segundos
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0  # segundos

class OpenAIModelConfig(BaseModel):
    """Configuración para un modelo de OpenAI."""
    name: str = Field(..., description="Nombre del modelo (ej: 'gpt-4', 'gpt-3.5-turbo')")
    max_tokens: int = Field(8192, description="Número máximo de tokens que el modelo puede manejar")
    supports_functions: bool = Field(False, description="Si el modelo soporta llamadas a funciones")
    supports_vision: bool = Field(False, description="Si el modelo soporta entrada de imágenes")
    input_cost_per_1k: float = Field(0.0, description="Costo por 1K tokens de entrada (USD)")
    output_cost_per_1k: float = Field(0.0, description="Costo por 1K tokens de salida (USD)")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "gpt-4-0125-preview",
                "max_tokens": 128000,
                "supports_functions": True,
                "supports_vision": True,
                "input_cost_per_1k": 0.01,
                "output_cost_per_1k": 0.03
            }
        }

class OpenAIService:
    """
    Servicio para interactuar con la API de OpenAI.
    
    Proporciona métodos para generar respuestas de chat, embeddings, y otras
    funcionalidades de los modelos de lenguaje de OpenAI.
    """
    
    _instance = None
    _client = None
    _initialized = False
    _models: Dict[str, OpenAIModelConfig] = {}
    
    # Modelos predefinidos con sus configuraciones
    PREDEFINED_MODELS = {
        # GPT-4
        "gpt-4-0125-preview": OpenAIModelConfig(
            name="gpt-4-0125-preview",
            max_tokens=128000,
            supports_functions=True,
            supports_vision=True,
            input_cost_per_1k=0.01,
            output_cost_per_1k=0.03
        ),
        "gpt-4-1106-preview": OpenAIModelConfig(
            name="gpt-4-1106-preview",
            max_tokens=128000,
            supports_functions=True,
            supports_vision=True,
            input_cost_per_1k=0.01,
            output_cost_per_1k=0.03
        ),
        "gpt-4-vision-preview": OpenAIModelConfig(
            name="gpt-4-vision-preview",
            max_tokens=128000,
            supports_functions=False,
            supports_vision=True,
            input_cost_per_1k=0.01,
            output_cost_per_1k=0.03
        ),
        "gpt-4": OpenAIModelConfig(
            name="gpt-4",
            max_tokens=8192,
            supports_functions=True,
            supports_vision=False,
            input_cost_per_1k=0.03,
            output_cost_per_1k=0.06
        ),
        
        # GPT-3.5
        "gpt-3.5-turbo-1106": OpenAIModelConfig(
            name="gpt-3.5-turbo-1106",
            max_tokens=16385,
            supports_functions=True,
            supports_vision=False,
            input_cost_per_1k=0.001,
            output_cost_per_1k=0.002
        ),
        "gpt-3.5-turbo": OpenAIModelConfig(
            name="gpt-3.5-turbo",
            max_tokens=4096,
            supports_functions=False,
            supports_vision=False,
            input_cost_per_1k=0.0005,
            output_cost_per_1k=0.0015
        ),
        
        # Modelos de embeddings
        "text-embedding-ada-002": OpenAIModelConfig(
            name="text-embedding-ada-002",
            max_tokens=8191,
            supports_functions=False,
            supports_vision=False,
            input_cost_per_1k=0.0001,
            output_cost_per_1k=0.0
        ),
        "text-embedding-3-small": OpenAIModelConfig(
            name="text-embedding-3-small",
            max_tokens=8191,
            supports_functions=False,
            supports_vision=False,
            input_cost_per_1k=0.00002,
            output_cost_per_1k=0.0
        ),
        "text-embedding-3-large": OpenAIModelConfig(
            name="text-embedding-3-large",
            max_tokens=8191,
            supports_functions=False,
            supports_vision=False,
            input_cost_per_1k=0.00013,
            output_cost_per_1k=0.0
        ),
    }
    
    # Modelos por defecto
    DEFAULT_CHAT_MODEL = "gpt-4-0125-preview"
    DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
    
    def __new__(cls, *args, **kwargs):
        """Implementa el patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(OpenAIService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Inicializa el servicio de OpenAI.
        
        Args:
            api_key: Clave API de OpenAI. Si no se proporciona, se usará la de configuración.
            base_url: URL base de la API. Útil para usar con proxies o versiones auto-alojadas.
        """
        if not self._initialized:
            self._api_key = api_key or settings.OPENAI_API_KEY
            self._base_url = base_url or settings.OPENAI_API_BASE or "https://api.openai.com/v1"
            self._default_chat_model = settings.OPENAI_MODEL or self.DEFAULT_CHAT_MODEL
            self._default_embedding_model = settings.OPENAI_EMBEDDING_MODEL or self.DEFAULT_EMBEDDING_MODEL
            
            if not self._api_key:
                raise ValueError("OPENAI_API_KEY no está configurada en las variables de entorno")
            
            # Inicializar el cliente
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=settings.OPENAI_TIMEOUT or 60.0,
                max_retries=settings.OPENAI_MAX_RETRIES or 3
            )
            
            # Cargar configuraciones de modelos
            self._load_model_configs()
            
            # Configurar el logger
            self._setup_logging()
            
            self._initialized = True
    
    def _load_model_configs(self) -> None:
        """Carga las configuraciones de los modelos."""
        # Cargar modelos predefinidos
        self._models = self.PREDEFINED_MODELS.copy()
        
        # Verificar si el modelo por defecto está soportado
        if self._default_chat_model not in self._models:
            logger.warning(
                f"El modelo de chat por defecto '{self._default_chat_model}' no está en la lista de modelos conocidos. "
                "Se utilizará con configuración predeterminada."
            )
            self._models[self._default_chat_model] = OpenAIModelConfig(
                name=self._default_chat_model,
                max_tokens=8192,
                supports_functions=True,
                supports_vision=False
            )
        
        # Verificar si el modelo de embeddings por defecto está soportado
        if self._default_embedding_model not in self._models:
            logger.warning(
                f"El modelo de embeddings por defecto '{self._default_embedding_model}' no está en la lista de modelos conocidos. "
                "Se utilizará con configuración predeterminada."
            )
            self._models[self._default_embedding_model] = OpenAIModelConfig(
                name=self._default_embedding_model,
                max_tokens=8191,
                supports_functions=False,
                supports_vision=False
            )
    
    def _setup_logging(self) -> None:
        """Configura el registro de logs."""
        # Configurar el nivel de log basado en la configuración
        log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        logger.setLevel(log_level)
        
        # Evitar múltiples manejadores
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
    
    @property
    def client(self) -> AsyncOpenAI:
        """Obtiene el cliente de OpenAI."""
        if self._client is None:
            raise RuntimeError("El cliente de OpenAI no está inicializado")
        return self._client
    
    @property
    def default_chat_model(self) -> str:
        """Obtiene el modelo de chat por defecto."""
        return self._default_chat_model
    
    @property
    def default_embedding_model(self) -> str:
        """Obtiene el modelo de embeddings por defecto."""
        return self._default_embedding_model
    
    def get_model_config(self, model_name: str) -> OpenAIModelConfig:
        """
        Obtiene la configuración de un modelo.
        
        Args:
            model_name: Nombre del modelo.
            
        Returns:
            OpenAIModelConfig: Configuración del modelo.
            
        Raises:
            ValueError: Si el modelo no es compatible.
        """
        if model_name not in self._models:
            # Intentar encontrar un modelo similar
            for known_model in self._models.keys():
                if model_name.lower() in known_model.lower() or known_model.lower() in model_name.lower():
                    logger.warning(f"Modelo '{model_name}' no encontrado, usando '{known_model}' como sustituto")
                    return self._models[known_model]
            
            # Si no se encuentra un modelo similar, usar valores por defecto
            logger.warning(f"Modelo '{model_name}' no encontrado, usando configuración por defecto")
            return OpenAIModelConfig(
                name=model_name,
                max_tokens=8192 if "gpt-4" in model_name else 4096,
                supports_functions=("gpt-4" in model_name or "gpt-3.5-turbo" in model_name) and "-1106-" in model_name,
                supports_vision="vision" in model_name.lower()
            )
        
        return self._models[model_name]

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        function_call: Optional[Union[str, Dict[str, str]]] = None,
        **kwargs
    ) -> Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]:
        """
        Genera una respuesta de chat utilizando la API de OpenAI.
        
        Args:
            messages: Lista de mensajes en el formato de chat de OpenAI.
            model: Nombre del modelo a utilizar. Si es None, se usa el modelo por defecto.
            temperature: Controla la aleatoriedad (0-2). Valores más altos son más aleatorios.
            max_tokens: Número máximo de tokens en la respuesta. Si es None, se calcula automáticamente.
            stream: Si es True, devuelve un generador para streaming.
            use_cache: Si es True, intenta obtener la respuesta de la caché.
            cache_ttl: Tiempo de vida de la caché en segundos. Si es None, usa el valor por defecto.
            functions: Lista de funciones disponibles para el modelo.
            function_call: Controla cómo se llama a las funciones.
            **kwargs: Argumentos adicionales para la API de OpenAI.
            
        Returns:
            Union[Dict[str, Any], AsyncGenerator[Dict[str, Any], None]]: 
                - Si stream=False: Un diccionario con la respuesta de la API.
                - Si stream=True: Un generador que produce fragmentos de la respuesta.
                
        Raises:
            HTTPException: Si hay un error al comunicarse con la API de OpenAI.
        """
        if not messages:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La lista de mensajes no puede estar vacía"
            )
        
        # Usar el modelo por defecto si no se especifica
        model = model or self._default_chat_model
        model_config = self.get_model_config(model)
        
        # Validar parámetros
        if temperature < 0 or temperature > 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La temperatura debe estar entre 0 y 2"
            )
        
        # Calcular max_tokens si no se especifica
        if max_tokens is None:
            max_tokens = model_config.max_tokens
        
        # Generar clave de caché si está habilitado
        cache_key = None
        if use_cache and not stream and not functions and not function_call:
            cache_data = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **{k: v for k, v in kwargs.items() if k not in ["stream", "functions", "function_call"]}
            }
            cache_key = self._generate_cache_key("chat", cache_data)
            
            # Intentar obtener de la caché
            cached_response = await cache.get(cache_key)
            if cached_response is not None:
                logger.debug(f"Respuesta de chat obtenida de la caché para el modelo {model}")
                return cached_response
        
        try:
            # Preparar parámetros para la API
            api_params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs
            }
            
            # Añadir funciones si se proporcionan
            if functions:
                api_params["functions"] = functions
            if function_call:
                api_params["function_call"] = function_call
            
            logger.info(f"Enviando solicitud a OpenAI con modelo {model}")
            
            if stream:
                return self._stream_chat_completion(**api_params)
            
            # Llamada a la API con reintentos
            start_time = time.time()
            response = await self._with_retry(
                operation=f"chat_completion ({model})",
                callable_fn=self.client.chat.completions.create,
                **api_params
            )
            response_time = time.time() - start_time
            
            # Procesar la respuesta
            result = self._process_chat_response(response, response_time)
            
            # Almacenar en caché si está habilitado
            if cache_key:
                ttl = cache_ttl or settings.CHAT_CACHE_TTL or 3600  # 1 hora por defecto
                await cache.set(cache_key, result, expire=ttl)
            
            return result
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error inesperado en chat_completion: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al generar la respuesta: {str(e)}"
            ) from e
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
        model: str,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Maneja el streaming de respuestas de chat desde la API de OpenAI.
        
        Args:
            model: Nombre del modelo a utilizar.
            messages: Lista de mensajes en el formato de chat de OpenAI.
            **kwargs: Argumentos adicionales para la API de OpenAI.
            
        Yields:
            Dict[str, Any]: Fragmentos de la respuesta en formato de streaming.
            
        Raises:
            HTTPException: Si hay un error al comunicarse con la API de OpenAI.
        """
        try:
            # Preparar parámetros para la API
            api_params = {
                "model": model,
                "messages": messages,
                "stream": True,
                **{k: v for k, v in kwargs.items() if k != "stream"}
            }
            
            # Iniciar el stream con reintentos
            stream = await self._with_retry(
                operation=f"stream_chat_completion ({model})",
                callable_fn=self.client.chat.completions.create,
                **api_params
            )
            
            # Procesar el stream
            async for chunk in stream:
                if chunk.choices:
                    delta = chunk.choices[0].delta
                    if delta.content or chunk.choices[0].finish_reason:
                        yield {
                            "id": chunk.id,
                            "object": "chat.completion.chunk",
                            "created": chunk.created,
                            "model": chunk.model,
                            "choices": [{
                                "delta": {
                                    "content": delta.content or "",
                                    "role": delta.role or "assistant"
                                },
                                "index": chunk.choices[0].index,
                                "finish_reason": chunk.choices[0].finish_reason
                            }]
                        }
                        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error en el streaming de chat: {str(e)}", exc_info=True)
            # Enviar un mensaje de error como chunk final
            error_chunk = {
                "id": f"error-{int(time.time())}",
                "object": "chat.completion.chunk",
                "created": int(time()),
                "model": model,
                "choices": [{
                    "delta": {"content": ""},
                    "finish_reason": "error",
                    "error": {"message": f"Error en el streaming: {str(e)}"}
                }]
            }
            yield error_chunk
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error en el streaming de chat: {str(e)}"
            ) from e
    
    def _process_chat_response(
        self, 
        response: Any, 
        response_time: float
    ) -> Dict[str, Any]:
        """
        Procesa la respuesta de la API de OpenAI a un diccionario estándar.
        
        Args:
            response: Respuesta de la API de OpenAI.
            response_time: Tiempo de respuesta en segundos.
            
        Returns:
            Dict[str, Any]: Respuesta procesada en formato estándar.
        """
        choice = response.choices[0]
        message = choice.message
        
        # Procesar la respuesta
        result = {
            "id": response.id,
            "object": response.object,
            "created": response.created,
            "model": response.model,
            "choices": [{
                "message": {
                    "role": message.role,
                    "content": message.content or ""
                },
                "index": choice.index,
                "finish_reason": choice.finish_reason
            }]
        }
        
        # Añadir información de uso si está disponible
        if hasattr(response, 'usage') and response.usage:
            result["usage"] = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "response_time": response_time
            }
        
        # Añadir información de función si está presente
        if hasattr(message, 'function_call') and message.function_call:
            result["choices"][0]["message"]["function_call"] = {
                "name": message.function_call.name,
                "arguments": message.function_call.arguments
            }
        
        # Añadir tool_calls si está presente
        if hasattr(message, 'tool_calls') and message.tool_calls:
            result["choices"][0]["message"]["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]
        
        return result

    async def generate_embeddings(
        self, 
        texts: Union[str, List[str]],
        model: Optional[str] = None,
        use_cache: bool = True,
        cache_ttl: Optional[int] = None,
        **kwargs
    ) -> List[List[float]]:
        """
        Genera embeddings de texto usando la API de OpenAI.
        
        Args:
            texts: Texto o lista de textos para generar embeddings.
            model: Modelo de embedding a utilizar. Si es None, se usa el modelo por defecto.
            use_cache: Si es True, intenta obtener los embeddings de la caché.
            cache_ttl: Tiempo de vida de la caché en segundos. Si es None, usa el valor por defecto.
            **kwargs: Argumentos adicionales para la API de OpenAI.
            
        Returns:
            List[List[float]]: Lista de vectores de embedding.
            
        Raises:
            HTTPException: Si hay un error al generar los embeddings.
        """
        try:
            # Normalizar la entrada a una lista
            if isinstance(texts, str):
                texts = [texts]
            
            # Validar la entrada
            if not texts or not all(isinstance(text, str) and text.strip() for text in texts):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Los textos no pueden estar vacíos"
                )
            
            # Usar el modelo por defecto si no se especifica
            model = model or self._default_embedding_model
            model_config = self.get_model_config(model)
            
            # Verificar si el modelo es compatible con embeddings
            if not model.lower().startswith("text-embedding"):
                logger.warning(f"El modelo {model} puede no ser un modelo de embeddings")
            
            # Preparar la clave de caché si está habilitado
            cache_keys = []
            if use_cache:
                cache_keys = [self._generate_cache_key(
                    "embedding", 
                    {"text": text, "model": model, **kwargs}
                ) for text in texts]
                
                # Intentar obtener de la caché
                cached_embeddings = await asyncio.gather(
                    *[cache.get(key) for key in cache_keys],
                    return_exceptions=True
                )
                
                # Procesar resultados de la caché
                result = []
                remaining_indices = []
                remaining_texts = []
                
                for i, (cached, text) in enumerate(zip(cached_embeddings, texts)):
                    if isinstance(cached, Exception) or cached is None:
                        remaining_indices.append(i)
                        remaining_texts.append(text)
                    else:
                        result.append((i, cached))
                
                # Si todos estaban en caché, devolverlos ordenados
                if not remaining_texts:
                    logger.debug(f"Todos los embeddings obtenidos de la caché para el modelo {model}")
                    return [emb for _, emb in sorted(result, key=lambda x: x[0])]
                
                logger.debug(f"{len(result)}/{len(texts)} embeddings obtenidos de la caché")
            else:
                remaining_texts = texts
                remaining_indices = list(range(len(texts)))
            
            # Generar embeddings para los textos restantes
            if remaining_texts:
                try:
                    # Llamada a la API con reintentos
                    start_time = time.time()
                    response = await self._with_retry(
                        operation=f"generate_embeddings ({model}, {len(remaining_texts)} textos)",
                        callable_fn=self.client.embeddings.create,
                        input=remaining_texts,
                        model=model,
                        **kwargs
                    )
                    response_time = time.time() - start_time
                    
                    # Procesar la respuesta
                    embeddings = [item.embedding for item in response.data]
                    
                    # Almacenar en caché si está habilitado
                    if use_cache and cache_keys:
                        ttl = cache_ttl or settings.EMBEDDING_CACHE_TTL or 86400  # 1 día por defecto
                        await asyncio.gather(*[
                            cache.set(cache_keys[idx], emb, expire=ttl)
                            for idx, emb in zip(remaining_indices, embeddings)
                        ])
                    
                    # Combinar con los resultados de la caché
                    if use_cache:
                        for idx, emb in zip(remaining_indices, embeddings):
                            result.append((idx, emb))
                        
                        # Ordenar por índice original
                        result.sort(key=lambda x: x[0])
                        return [emb for _, emb in result]
                    
                    return embeddings
                    
                except HTTPException:
                    raise
                except Exception as e:
                    logger.error(f"Error al generar embeddings: {str(e)}", exc_info=True)
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Error al generar embeddings: {str(e)}"
                    ) from e
            
            # Este punto no debería alcanzarse nunca
            return []
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error inesperado en generate_embeddings: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al procesar la solicitud de embeddings: {str(e)}"
            ) from e

    def format_messages_for_openai(
        self, 
        messages: List[ChatMessage], 
        system_prompt: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Formatea una lista de mensajes para la API de OpenAI.
        
        Args:
            messages: Lista de mensajes a formatear.
            system_prompt: Mensaje del sistema a incluir al principio.
            
        Returns:
            List[Dict[str, str]]: Lista de mensajes formateados para la API de OpenAI.
        """
        formatted_messages = []
        
        # Añadir el mensaje del sistema si se proporciona
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        
        # Formatear cada mensaje
        for msg in messages:
            if msg.role == MessageRole.SYSTEM and system_prompt is None:
                # Solo añadir mensaje de sistema si no se proporcionó uno explícito
                formatted_messages.append({"role": "system", "content": msg.content})
            elif msg.role in [MessageRole.USER, MessageRole.ASSISTANT, MessageRole.FUNCTION]:
                # Manejar mensajes de usuario, asistente y función
                message = {"role": msg.role.value, "content": msg.content}
                if msg.name:
                    message["name"] = msg.name
                if msg.role == MessageRole.FUNCTION and msg.function_call:
                    message["function_call"] = msg.function_call
                formatted_messages.append(message)
        
        return formatted_messages
    
    def count_tokens(
        self,
        text: str,
        model: Optional[str] = None
    ) -> int:
        """
        Cuenta el número de tokens en un texto para un modelo específico.
        
        Args:
            text: Texto a analizar.
            model: Nombre del modelo. Si es None, se usa el modelo de chat por defecto.
            
        Returns:
            int: Número de tokens en el texto.
        """
        try:
            import tiktoken
            
            # Usar el modelo especificado o el modelo de chat por defecto
            model = model or self._default_chat_model
            
            # Obtener el encoding para el modelo
            encoding = tiktoken.encoding_for_model(model)
            
            # Contar los tokens
            return len(encoding.encode(text))
            
        except ImportError:
            logger.warning("tiktoken no está instalado. Usando estimación aproximada de tokens.")
            # Estimación aproximada: 1 token ~= 4 caracteres en inglés
            return (len(text) // 4) + 1
        except Exception as e:
            logger.warning(f"Error al contar tokens: {str(e)}. Usando estimación aproximada.")
            return (len(text) // 4) + 1
    
    async def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de modelos disponibles en la API de OpenAI.
        
        Returns:
            List[Dict[str, Any]]: Lista de modelos disponibles con sus configuraciones.
            
        Note:
            Requiere permisos de API que permitan listar modelos.
        """
        try:
            # Llamada a la API con reintentos
            models = await self._with_retry(
                operation="list_models",
                callable_fn=self.client.models.list
            )
            
            # Procesar y devolver la lista de modelos
            return [
                {
                    "id": model.id,
                    "object": model.object,
                    "created": model.created,
                    "owned_by": model.owned_by,
                    "permission": [p.to_dict() for p in model.permission] if hasattr(model, 'permission') else []
                }
                for model in models.data
            ]
            
        except Exception as e:
            logger.error(f"Error al obtener la lista de modelos: {str(e)}", exc_info=True)
            # Si falla, devolver solo los modelos predefinidos
            return [
                {
                    "id": model_name,
                    "object": "model",
                    "created": None,
                    "owned_by": "openai",
                    "permission": []
                }
                for model_name in self.PREDEFINED_MODELS.keys()
            ]
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """
        Obtiene información sobre un modelo específico.
        
        Args:
            model_name: Nombre del modelo.
            
        Returns:
            Dict[str, Any]: Información del modelo.
        """
        model_config = self.get_model_config(model_name)
        
        return {
            "id": model_config.name,
            "object": "model",
            "created": None,
            "owned_by": "openai",
            "permission": [],
            "max_tokens": model_config.max_tokens,
            "supports_functions": model_config.supports_functions,
            "supports_vision": model_config.supports_vision,
            "input_cost_per_1k": model_config.input_cost_per_1k,
            "output_cost_per_1k": model_config.output_cost_per_1k
        }
    
    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: Optional[str] = None
    ) -> float:
        """
        Calcula el costo estimado de una operación con la API de OpenAI.
        
        Args:
            input_tokens: Número de tokens de entrada.
            output_tokens: Número de tokens de salida.
            model: Nombre del modelo. Si es None, se usa el modelo de chat por defecto.
            
        Returns:
            float: Costo estimado en USD.
        """
        model = model or self._default_chat_model
        model_config = self.get_model_config(model)
        
        input_cost = (input_tokens / 1000) * model_config.input_cost_per_1k
        output_cost = (output_tokens / 1000) * model_config.output_cost_per_1k
        
        return input_cost + output_cost