# Vambe.ai Chatbot API

API de backend para el sistema de chatbot conversacional de Vambe.ai, construido con FastAPI, PostgreSQL, Weaviate y OpenAI. Este proyecto implementa un sistema de chat con IA que incluye análisis de sentimientos, caché distribuido y gestión de conversaciones.

## Características Principales

- **Autenticación JWT** con soporte para múltiples roles de usuario
- **Integración con OpenAI** para generación de respuestas conversacionales
- **Soporte para bases de datos asíncronas** con SQLAlchemy 2.0
- **Almacenamiento vectorial** con Weaviate para búsqueda semántica
- **Sistema de caché distribuido** con Redis para mejorar el rendimiento
- **Análisis de sentimientos** en tiempo real de las conversaciones
- **Rate limiting** para prevenir abusos de la API
- Almacenamiento de documentos con MinIO/S3
- Sistema de logging estructurado y configurable
- Documentación automática con Swagger UI y ReDoc
- Soporte para WebSockets para chat en tiempo real
- Tareas en segundo plano con Celery
- Validación de datos con Pydantic v2
- Variables de entorno para configuración
- Migraciones de base de datos con Alembic
- Soporte para operaciones asíncronas en toda la aplicación
- Inicialización automática de la base de datos
- Datos iniciales configurables

## Requisitos Previos

- Python 3.9+
- PostgreSQL 13+
- Redis 6+ (requerido para caché y rate limiting)
- MinIO o S3 para almacenamiento de archivos
- Weaviate para búsqueda vectorial (recomendado)
- Docker y Docker Compose (para desarrollo local)

## Configuración del Entorno

1. Clona el repositorio:
   ```bash
   git clone https://github.com/tu-usuario/vambe-ai-chatbot-api.git
   cd vambe-ai-chatbot-api
   ```

2. Crea un entorno virtual y actívalo:
   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

4. Copia el archivo de ejemplo de variables de entorno y configúralo:
   ```bash
   cp .env.example .env
   ```
   Edita el archivo `.env` con tus configuraciones.

5. Crea la base de datos PostgreSQL y ejecuta las migraciones:
   ```bash
   alembic upgrade head
   ```

6. Inicia la aplicación:
   ```bash
   uvicorn app.main:app --reload
   ```

La aplicación estará disponible en `http://localhost:8000`

## Estructura del Proyecto

```
chatbot-api/
├── alembic/               # Migraciones de la base de datos
├── app/
│   ├── api/               # Endpoints de la API
│   ├── core/              # Configuración y utilidades principales
│   ├── crud/              # Operaciones de base de datos
│   ├── db/                # Configuración de la base de datos
│   ├── models/            # Modelos SQLAlchemy
│   ├── schemas/           # Esquemas Pydantic
│   ├── services/          # Lógica de negocio
│   ├── tasks/             # Tareas en segundo plano
│   ├── utils/             # Utilidades varias
│   ├── main.py            # Punto de entrada de la aplicación
│   └── config.py          # Configuración de la aplicación
├── tests/                 # Pruebas automatizadas
├── .env.example           # Variables de entorno de ejemplo
├── .gitignore
├── alembic.ini            # Configuración de Alembic
├── requirements.txt       # Dependencias de Python
└── README.md             # Este archivo
```

## Configuración de Base de Datos Asíncrona

El proyecto utiliza SQLAlchemy 2.0 con soporte para operaciones asíncronas. La configuración incluye:

### Variables de Entorno para Base de Datos

Copia el archivo `.env.example` a `.env` y configura las siguientes variables:

```
# Configuración de base de datos síncrona (para migraciones y tareas síncronas)
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/chatbot_db

# Configuración de base de datos asíncrona (para operaciones asíncronas)
ASYNC_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/chatbot_db

# Configuración para pruebas
TEST_DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/chatbot_test_db
TEST_ASYNC_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/chatbot_test_db
```

### Uso de Sesiones Asíncronas

Para utilizar sesiones asíncronas en tus rutas FastAPI:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_db

@app.get("/items/")
async def read_items(
    db: AsyncSession = Depends(get_async_db)
):
    # Usa la sesión asíncrona
    result = await db.execute(select(MyModel))
    items = result.scalars().all()
    return items
```

### Migraciones con Alembic

El proyecto incluye configuración para migraciones con Alembic. Para crear una nueva migración:

```bash
alembic revision --autogenerate -m "Descripción de los cambios"
```

Para aplicar las migraciones:

```bash
alembic upgrade head
```

### Inicialización de la Base de Datos

Para inicializar la base de datos con datos iniciales:

```bash
python -m scripts.init_db
```

## Variables de Entorno Adicionales

Además de las variables de base de datos, configura las siguientes variables:

- `DATABASE_URL`: URL de conexión a PostgreSQL
- `JWT_SECRET`: Clave secreta para firmar los tokens JWT
- `OPENAI_API_KEY`: Clave de API de OpenAI
- `WEAVIATE_URL`: URL del servidor Weaviate
- `REDIS_URL`: URL de conexión a Redis
- `MINIO_*`: Configuración de MinIO para almacenamiento de archivos
- `SMTP_*`: Configuración del servidor SMTP para envío de correos

## Documentación de la API

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Despliegue

### Con Docker (Recomendado)

```bash
docker-compose up --build
```

### En Producción

1. Configura un servidor WSGI como Gunicorn:
   ```bash
   gunicorn -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000 app.main:app
   ```

2. Configura un proxy inverso con Nginx o similar.

## Pruebas

Para ejecutar las pruebas:

```bash
pytest
```

## Contribución

1. Haz un fork del proyecto
2. Crea una rama para tu característica (`git checkout -b feature/AmazingFeature`)
3. Haz commit de tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Haz push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para más detalles.

## Contacto

Tu Nombre - [@tu_twitter](https://twitter.com/tu_twitter) - email@ejemplo.com

Enlace del Proyecto: [https://github.com/tu-usuario/vambe-ai-chatbot-api](https://github.com/tu-usuario/vambe-ai-chatbot-api)
