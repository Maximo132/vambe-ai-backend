"""
Servicio de caché utilizando Redis como backend.

Este módulo proporciona una interfaz para almacenar y recuperar datos en caché
utilizando Redis como backend. Incluye soporte para diferentes tipos de datos
y operaciones atómicas.
"""
import json
import pickle
import asyncio
from datetime import datetime, timedelta
from typing import Any, Optional, Union, List, Dict, Callable, Awaitable, TypeVar, Type, TypeVar
import functools
import hashlib

import redis.asyncio as redis
from fastapi import HTTPException, status, Depends
from pydantic import BaseModel

from ..core.config import settings, logger

# Tipo genérico para los modelos Pydantic
ModelType = TypeVar('ModelType', bound=BaseModel)
T = TypeVar('T')

class CacheService:
    """
    Servicio para manejar el almacenamiento en caché con Redis.
    
    Proporciona métodos para almacenar y recuperar datos de diferentes tipos,
    incluyendo objetos Pydantic, diccionarios, listas y tipos primitivos.
    """
    _instance = None
    _redis: Optional[redis.Redis] = None
    _is_connected: bool = False
    
    def __new__(cls, *args, **kwargs):
        """Implementa el patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(CacheService, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, redis_url: Optional[str] = None):
        """Inicializa el servicio de caché."""
        if not hasattr(self, '_initialized') or not self._initialized:
            self.redis_url = redis_url or settings.REDIS_URL
            self._initialized = True
    
    async def initialize(self, redis_url: Optional[str] = None) -> bool:
        """
        Inicializa la conexión con Redis.
        
        Args:
            redis_url: URL de conexión a Redis. Si no se proporciona, se usa la de configuración.
            
        Returns:
            bool: True si la conexión fue exitosa, False en caso contrario.
        """
        if redis_url:
            self.redis_url = redis_url
            
        try:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,  # Desactivamos decode_responses para mayor flexibilidad
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                max_connections=20,
            )
            
            # Probar la conexión
            await self._redis.ping()
            self._is_connected = True
            logger.info("Conexión exitosa con Redis")
            return True
            
        except Exception as e:
            self._is_connected = False
            logger.error(f"Error al conectar con Redis: {str(e)}")
            return False
    
    @classmethod
    async def close(cls) -> None:
        """Cierra la conexión con Redis."""
        if cls._instance and cls._instance._redis:
            await cls._instance._redis.close()
            await cls._instance._redis.connection_pool.disconnect()
            cls._instance._is_connected = False
            logger.info("Conexión con Redis cerrada")
    
    @property
    def is_connected(self) -> bool:
        """Indica si el servicio está conectado a Redis."""
        return self._is_connected and self._redis is not None
    
    def _generate_key(self, prefix: str, *args) -> str:
        """
        Genera una clave de caché consistente a partir de un prefijo y argumentos.
        
        Args:
            prefix: Prefijo para la clave.
            *args: Argumentos adicionales para incluir en la clave.
            
        Returns:
            str: Clave de caché generada.
        """
        key_parts = [str(prefix)] + [str(arg) for arg in args]
        key = ":".join(key_parts)
        # Usar hash para claves muy largas
        if len(key) > 200:
            return f"{prefix}:{hashlib.md5(key.encode()).hexdigest()}"
        return key
    
    async def get(self, key: str, model: Type[ModelType] = None) -> Optional[Any]:
        """
        Obtiene un valor del caché.
        
        Args:
            key: Clave del valor a obtener.
            model: (Opcional) Modelo Pydantic para deserializar el valor.
            
        Returns:
            El valor almacenado o None si no existe.
        """
        if not self.is_connected:
            return None
            
        try:
            value = await self._redis.get(key)
            if value is None:
                return None
                
            # Deserializar según el tipo de valor
            try:
                # Primero intentamos con JSON
                data = json.loads(value)
                if model and isinstance(data, dict):
                    return model(**data)
                return data
            except (json.JSONDecodeError, TypeError):
                # Si falla, intentamos con pickle
                try:
                    data = pickle.loads(value)
                    if model and isinstance(data, dict):
                        return model(**data)
                    return data
                except (pickle.PickleError, AttributeError, EOFError, ImportError):
                    # Si todo falla, devolvemos el valor tal cual
                    return value.decode() if isinstance(value, bytes) else value
                    
        except Exception as e:
            logger.error(f"Error al obtener del caché (key={key}): {str(e)}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: Optional[int] = 3600,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """
        Almacena un valor en el caché.
        
        Args:
            key: Clave bajo la que se almacenará el valor.
            value: Valor a almacenar.
            expire: Tiempo de expiración en segundos. None para que no expire.
            nx: Si es True, solo establece la clave si no existe.
            xx: Si es True, solo establece la clave si ya existe.
            
        Returns:
            bool: True si la operación fue exitosa, False en caso contrario.
        """
        if not self.is_connected:
            return False
            
        try:
            # Serializar el valor según su tipo
            if isinstance(value, (str, int, float, bool)) or value is None:
                serialized_value = json.dumps(value).encode()
            elif isinstance(value, (dict, list, tuple)):
                serialized_value = json.dumps(value).encode()
            elif hasattr(value, 'model_dump_json'):  # Para modelos Pydantic v2
                serialized_value = value.model_dump_json().encode()
            elif hasattr(value, 'dict'):  # Para modelos Pydantic v1
                serialized_value = json.dumps(value.dict()).encode()
            else:
                # Usar pickle para otros tipos de objetos
                serialized_value = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
            
            # Configurar parámetros adicionales
            kwargs = {}
            if nx:
                kwargs['nx'] = True
            if xx:
                kwargs['xx'] = True
                
            # Almacenar en Redis
            if expire is not None:
                result = await self._redis.setex(key, expire, serialized_value, **kwargs)
            else:
                result = await self._redis.set(key, serialized_value, **kwargs)
                
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error al guardar en caché (key={key}): {str(e)}")
            return False
    
    async def get_or_set(
        self,
        key: str,
        default: Union[Any, Callable[[], Awaitable[Any]]],
        expire: Optional[int] = 3600,
        model: Type[ModelType] = None
    ) -> Any:
        """
        Obtiene un valor del caché o lo establece si no existe.
        
        Args:
            key: Clave del valor a obtener o establecer.
            default: Valor por defecto o función que lo genera. Puede ser síncrono o asíncrono.
            expire: Tiempo de expiración en segundos. None para que no expire.
            model: (Opcional) Modelo Pydantic para deserializar el valor.
            
        Returns:
            El valor almacenado en caché o el valor por defecto.
        """
        # Intentar obtener el valor del caché
        cached_value = await self.get(key, model=model)
        if cached_value is not None:
            return cached_value
            
        # Si no está en caché, obtener el valor por defecto
        if callable(default):
            if asyncio.iscoroutinefunction(default):
                value = await default()
            else:
                value = default()
        else:
            value = default
            
        # Almacenar en caché si el valor no es None
        if value is not None:
            await self.set(key, value, expire=expire)
            
        return value
    
    async def delete(self, *keys: str) -> int:
        """
        Elimina una o más claves del caché.
        
        Args:
            *keys: Claves a eliminar.
            
        Returns:
            int: Número de claves eliminadas.
        """
        if not self.is_connected or not keys:
            return 0
            
        try:
            return await self._redis.delete(*keys)
        except Exception as e:
            logger.error(f"Error al eliminar claves del caché: {str(e)}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """
        Verifica si una clave existe en el caché.
        
        Args:
            key: Clave a verificar.
            
        Returns:
            bool: True si la clave existe, False en caso contrario.
        """
        if not self.is_connected:
            return False
            
        try:
            return bool(await self._redis.exists(key))
        except Exception as e:
            logger.error(f"Error al verificar existencia de clave {key}: {str(e)}")
            return False
    
    async def expire(self, key: str, time: int) -> bool:
        """
        Establece un tiempo de expiración para una clave.
        
        Args:
            key: Clave a la que se le establecerá el tiempo de expiración.
            time: Tiempo en segundos hasta la expiración.
            
        Returns:
            bool: True si se estableció correctamente, False en caso contrario.
        """
        if not self.is_connected:
            return False
            
        try:
            return await self._redis.expire(key, time)
        except Exception as e:
            logger.error(f"Error al establecer expiración para {key}: {str(e)}")
            return False
    
    async def ttl(self, key: str) -> Optional[int]:
        """
        Obtiene el tiempo restante de vida de una clave.
        
        Args:
            key: Clave a consultar.
            
        Returns:
            Optional[int]: Tiempo restante en segundos, -1 si no tiene expiración,
                         -2 si la clave no existe, o None en caso de error.
        """
        if not self.is_connected:
            return None
            
        try:
            return await self._redis.ttl(key)
        except Exception as e:
            logger.error(f"Error al obtener TTL para {key}: {str(e)}")
            return None
    
    async def clear(self, pattern: str = "*") -> int:
        """
        Elimina todas las claves que coincidan con un patrón.
        
        Args:
            pattern: Patrón de búsqueda de claves (ej: "user:*").
            
        Returns:
            int: Número de claves eliminadas.
        """
        if not self.is_connected:
            return 0
            
        try:
            keys = await self._redis.keys(pattern)
            if keys:
                return await self._redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Error al limpiar caché con patrón '{pattern}': {str(e)}")
            return 0
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Incrementa el valor de una clave numérica.
        
        Args:
            key: Clave a incrementar.
            amount: Cantidad a incrementar (puede ser negativo).
            
        Returns:
            Optional[int]: Nuevo valor o None en caso de error.
        """
        if not self.is_connected:
            return None
            
        try:
            return await self._redis.incrby(key, amount)
        except Exception as e:
            logger.error(f"Error al incrementar {key}: {str(e)}")
            return None
    
    async def get_many(self, keys: List[str], model: Type[ModelType] = None) -> List[Any]:
        """
        Obtiene múltiples valores del caché.
        
        Args:
            keys: Lista de claves a obtener.
            model: (Opcional) Modelo Pydantic para deserializar los valores.
            
        Returns:
            Lista de valores en el mismo orden que las claves solicitadas.
            Los valores que no existen serán None.
        """
        if not self.is_connected or not keys:
            return [None] * len(keys) if keys else []
            
        try:
            values = await self._redis.mget(keys)
            result = []
            
            for value in values:
                if value is None:
                    result.append(None)
                    continue
                    
                try:
                    # Intentar deserializar como JSON
                    data = json.loads(value)
                    if model and isinstance(data, dict):
                        result.append(model(**data))
                    else:
                        result.append(data)
                except (json.JSONDecodeError, TypeError):
                    # Si falla, intentar con pickle
                    try:
                        data = pickle.loads(value)
                        if model and isinstance(data, dict):
                            result.append(model(**data))
                        else:
                            result.append(data)
                    except (pickle.PickleError, AttributeError, EOFError, ImportError):
                        # Si todo falla, devolver el valor tal cual
                        result.append(value.decode() if isinstance(value, bytes) else value)
            
            return result
            
        except Exception as e:
            logger.error(f"Error al obtener múltiples valores del caché: {str(e)}")
            return [None] * len(keys)
    
    async def set_many(
        self,
        items: Dict[str, Any],
        expire: Optional[int] = 3600
    ) -> bool:
        """
        Almacena múltiples valores en el caché.
        
        Args:
            items: Diccionario de pares clave-valor a almacenar.
            expire: Tiempo de expiración en segundos. None para que no expire.
            
        Returns:
            bool: True si la operación fue exitosa, False en caso contrario.
        """
        if not self.is_connected or not items:
            return False
            
        try:
            # Convertir los valores a formato serializado
            pipeline = self._redis.pipeline()
            
            for key, value in items.items():
                # Serializar el valor según su tipo
                if isinstance(value, (str, int, float, bool)) or value is None:
                    serialized_value = json.dumps(value).encode()
                elif isinstance(value, (dict, list, tuple)):
                    serialized_value = json.dumps(value).encode()
                elif hasattr(value, 'model_dump_json'):  # Para modelos Pydantic v2
                    serialized_value = value.model_dump_json().encode()
                elif hasattr(value, 'dict'):  # Para modelos Pydantic v1
                    serialized_value = json.dumps(value.dict()).encode()
                else:
                    # Usar pickle para otros tipos de objetos
                    serialized_value = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
                
                # Configurar el comando SET o SETEX según corresponda
                if expire is not None:
                    pipeline.setex(key, expire, serialized_value)
                else:
                    pipeline.set(key, serialized_value)
            
            # Ejecutar todos los comandos en una sola operación atómica
            await pipeline.execute()
            return True
            
        except Exception as e:
            logger.error(f"Error al guardar múltiples valores en caché: {str(e)}")
            return False
    
    def cached(
        self,
        key: Optional[str] = None,
        expire: int = 3600,
        prefix: str = "cache",
        key_func: Optional[Callable[..., str]] = None
    ) -> Callable:
        """
        Decorador para almacenar en caché el resultado de una función.
        
        Args:
            key: Clave de caché estática. Si es None, se genera a partir de los argumentos.
            expire: Tiempo de expiración en segundos.
            prefix: Prefijo para las claves de caché.
            key_func: Función personalizada para generar la clave de caché.
            
        Returns:
            Callable: Función decorada con caché.
        """
        def decorator(func):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # Generar la clave de caché
                cache_key = key
                if cache_key is None:
                    if key_func:
                        cache_key = key_func(*args, **kwargs)
                    else:
                        # Generar clave a partir de la función y sus argumentos
                        key_parts = [prefix, func.__module__, func.__name__]
                        if args:
                            key_parts.extend(str(arg) for arg in args)
                        if kwargs:
                            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                        cache_key = ":".join(key_parts)
                
                # Intentar obtener el valor del caché
                cached_value = await self.get(cache_key)
                if cached_value is not None:
                    return cached_value
                
                # Si no está en caché, ejecutar la función
                result = await func(*args, **kwargs)
                
                # Almacenar el resultado en caché si no es None
                if result is not None:
                    await self.set(cache_key, result, expire=expire)
                
                return result
            
            return wrapper
        
        return decorator

# Instancia global del servicio de caché
cache = CacheService()

# Función para obtener la instancia del servicio de caché
async def get_cache() -> CacheService:
    """
    Obtiene la instancia del servicio de caché.
    
    Returns:
        CacheService: Instancia del servicio de caché.
    """
    if not cache.is_connected:
        await cache.initialize()
    return cache
