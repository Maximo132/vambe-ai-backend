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

3. Copia el archivo de ejemplo de variables de entorno y configúralo:
   ```bash
   cp .env.example .env
   ```
   
   Edita el archivo `.env` y configura al menos las siguientes variables:
   - `SECRET_KEY`: Una clave secreta segura para la aplicación
   - `JWT_SECRET`: Una clave secreta segura para JWT
   - `DATABASE_URL`: URL de conexión a PostgreSQL
   - `DEFAULT_ADMIN_PASSWORD`: Cambia la contraseña por defecto del administrador

4. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

5. Inicializa la base de datos y crea el usuario administrador:
   ```bash
   # Aplica migraciones
   alembic upgrade head
   
   # Crea el usuario administrador (opcional, se crea automáticamente al iniciar la aplicación si CREATE_DEFAULT_ADMIN=True)
   python -m scripts.init_db
   ```
   
   Alternativamente, puedes ejecutar solo el script de creación de administrador:
   ```bash
   python -m scripts.create_admin
   ```

6. Inicia el servidor de desarrollo:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   
   La aplicación estará disponible en `http://localhost:8000`
   
   - Documentación interactiva (Swagger UI): `http://localhost:8000/docs`
   - Documentación alternativa (ReDoc): `http://localhost:8000/redoc`

## Acceso al panel de administración

1. Inicia sesión en la ruta `/api/v1/auth/login` con las siguientes credenciales por defecto:
   - **Usuario:** admin
   - **Contraseña:** admin123 (o la que hayas configurado en `.env`)

2. Usa el token JWT devuelto para autenticarte en las rutas protegidas.

## Configuración del entorno de producción

Para entornos de producción, asegúrate de configurar adecuadamente las siguientes variables de entorno:

```env
# Configuración de seguridad
DEBUG=False
SECRET_KEY=una_clave_segura_y_aleatoria
JWT_SECRET=otra_clave_segura_y_aleatoria

# Configuración de base de datos
DATABASE_URL=postgresql://usuario:contraseña@servidor:5432/nombre_bd

# Configuración de Redis (opcional, para caché y rate limiting)
REDIS_URL=redis://localhost:6379/0

# Configuración de almacenamiento
STORAGE_PROVIDER=s3  # o 'minio' para desarrollo
AWS_ACCESS_KEY_ID=tu_access_key
AWS_SECRET_ACCESS_KEY=tu_secret_key
AWS_REGION=us-east-1
AWS_S3_BUCKET_NAME=tu-bucket

# Configuración de OpenAI
OPENAI_API_KEY=tu_api_key_de_openai

# Configuración de Weaviate (opcional, para búsqueda vectorial)
WEAVIATE_URL=tu_servidor_weaviate
WEAVIATE_API_KEY=tu_api_key_weaviate
```

## Variables de entorno importantes

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `DEBUG` | Modo depuración | `False` |
| `SECRET_KEY` | Clave secreta para la aplicación | Requerido |
| `JWT_SECRET` | Clave para firmar tokens JWT | Requerido |
| `DATABASE_URL` | URL de conexión a PostgreSQL | Requerido |
| `CREATE_DEFAULT_ADMIN` | Crear usuario administrador al iniciar | `True` |
| `DEFAULT_ADMIN_USERNAME` | Nombre de usuario del administrador | `admin` |
| `DEFAULT_ADMIN_EMAIL` | Email del administrador | `admin@vambe.ai` |
| `DEFAULT_ADMIN_PASSWORD` | Contraseña del administrador | `admin123` |

## Despliegue con Docker

1. Asegúrate de tener Docker y Docker Compose instalados.

2. Crea un archivo `docker-compose.override.yml` para personalizar la configuración:
   ```yaml
   version: '3.8'
   
   services:
     api:
       environment:
         - DEBUG=False
         - SECRET_KEY=tu_clave_secreta
         - JWT_SECRET=tu_clave_jwt
         - DATABASE_URL=postgresql://postgres:postgres@db:5432/vambeai
         - CREATE_DEFAULT_ADMIN=True
         - DEFAULT_ADMIN_PASSWORD=cambia_esta_contraseña
         - OPENAI_API_KEY=tu_api_key
   ```

3. Inicia los servicios:
   ```bash
   docker-compose up -d
   ```

4. Verifica los logs:
   ```bash
   docker-compose logs -f
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
