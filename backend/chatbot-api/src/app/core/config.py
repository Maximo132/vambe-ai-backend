"""
Configuración centralizada de la aplicación.

Este módulo carga y valida las variables de entorno necesarias para el funcionamiento
de la aplicación, proporcionando un acceso centralizado a la configuración.
"""
from pydantic_settings import BaseSettings
from typing import List, Optional, Dict, Any, Union
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env si existe
load_dotenv()

# Directorio base de la aplicación
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # Configuración de la aplicación
    APP_NAME: str = "Vambe.ai Chatbot API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    API_V1_STR: str = "/api/v1"
    
    # Configuración de CORS
    CORS_ORIGINS: List[str] = os.getenv(
        "CORS_ORIGINS", 
        "http://localhost:3000,http://frontend:3000,http://localhost:8000"
    ).split(",")
    
    # Configuración de la base de datos
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://postgres:postgres@localhost:5432/vambeai"
    )
    ASYNC_DATABASE_URL: str = os.getenv(
        "ASYNC_DATABASE_URL", 
        "postgresql+asyncpg://postgres:postgres@localhost:5432/vambeai"
    )
    TEST_DATABASE_URL: str = os.getenv(
        "TEST_DATABASE_URL", 
        "postgresql://postgres:postgres@localhost:5432/vambeai_test"
    )
    TEST_ASYNC_DATABASE_URL: str = os.getenv(
        "TEST_ASYNC_DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/vambeai_test"
    )
    
    # Configuración de autenticación
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your-jwt-secret-key")
    JWT_REFRESH_SECRET: str = os.getenv("JWT_REFRESH_SECRET", "your-refresh-jwt-secret-key")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    # Configuración de tokens de seguridad
    SECURITY_PASSWORD_SALT: str = os.getenv("SECURITY_PASSWORD_SALT", "your-password-salt")
    
    # Configuración de OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_MAX_TOKENS: int = int(os.getenv("OPENAI_MAX_TOKENS", "2000"))
    OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    
    # Configuración de Weaviate
    WEAVIATE_URL: str = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    WEAVIATE_API_KEY: str = os.getenv("WEAVIATE_API_KEY", "")
    WEAVIATE_EMBEDDING_MODEL: str = os.getenv("WEAVIATE_EMBEDDING_MODEL", "text-embedding-3-small")
    
    # Configuración de Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Configuración de almacenamiento (MinIO/S3)
    STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "minio")  # 'minio' o 's3'
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "False").lower() in ("true", "1", "t")
    MINIO_BUCKET_NAME: str = os.getenv("MINIO_BUCKET_NAME", "documents")
    
    # Configuración de AWS S3 (opcional, si se usa S3 directamente)
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_S3_BUCKET_NAME: str = os.getenv("AWS_S3_BUCKET_NAME", "vambeai-documents")
    
    # Configuración de correo electrónico
    SMTP_TLS: bool = os.getenv("SMTP_TLS", "True").lower() in ("true", "1", "t")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    EMAILS_FROM_EMAIL: str = os.getenv("EMAILS_FROM_EMAIL", "noreply@vambe.ai")
    EMAILS_FROM_NAME: str = os.getenv("EMAILS_FROM_NAME", "Vambe.ai")
    
    # Configuración de URLs
    SERVER_HOST: str = os.getenv("SERVER_HOST", "http://localhost:8000")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # Configuración de logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_FORMAT: str = os.getenv(
        "LOG_FORMAT",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    LOG_DATEFORMAT: str = os.getenv("LOG_DATEFORMAT", "%Y-%m-%d %H:%M:%S")
    LOG_JSON: bool = os.getenv("LOG_JSON", "False").lower() in ("true", "1", "t")
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE", str(BASE_DIR / "logs" / "app.log"))
    
    # Tiempos de expiración para tokens de verificación
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = int(
        os.getenv("EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS", "24")
    )
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = int(
        os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_HOURS", "1")
    )
    
    # Configuración de tasa límite (rate limiting)
    RATE_LIMIT: str = os.getenv("RATE_LIMIT", "100/minute")
    
    # Configuración de WebSocket
    WEBSOCKET_URL: str = os.getenv("WEBSOCKET_URL", "ws://localhost:8000/ws")
    
    # Configuración de tareas en segundo plano
    BACKGROUND_TASK_WORKERS: int = int(os.getenv("BACKGROUND_TASK_WORKERS", "4"))
    
    # Configuración de seguridad
    SECURE_COOKIES: bool = os.getenv("SECURE_COOKIES", "False").lower() in ("true", "1", "t")
    SESSION_COOKIE_NAME: str = os.getenv("SESSION_COOKIE_NAME", "vambeai_session")
    SESSION_COOKIE_HTTPONLY: bool = os.getenv("SESSION_COOKIE_HTTPONLY", "True").lower() in ("true", "1", "t")
    SESSION_COOKIE_SECURE: bool = os.getenv("SESSION_COOKIE_SECURE", "False").lower() in ("true", "1", "t")
    SESSION_COOKIE_SAMESITE: str = os.getenv("SESSION_COOKIE_SAMESITE", "lax")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        
        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            """Personaliza las fuentes de configuración."""
            # Primero cargar desde .env, luego de las variables de entorno del sistema
            return env_settings, init_settings, file_secret_settings


# Instancia de configuración
settings = Settings()

# Configurar logging
if settings.LOG_FILE:
    # Asegurarse de que el directorio de logs existe
    log_dir = Path(settings.LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)

# Configurar el nivel de logging para la aplicación
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format=settings.LOG_FORMAT,
    datefmt=settings.LOG_DATEFORMAT,
)

# Configurar el logger para este módulo
logger = logging.getLogger(__name__)

# Validar configuraciones críticas
if not settings.OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY no está configurada. Algunas funciones pueden no estar disponibles.")

if not settings.JWT_SECRET or settings.JWT_SECRET == "your-jwt-secret-key":
    logger.warning("JWT_SECRET está usando el valor por defecto. Esto es inseguro para producción.")

# Exportar configuración
__all__ = ["settings", "logger"]
