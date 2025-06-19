import os
import sys
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Asegurarse de que el directorio src esté en el PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

# Configurar la variable de entorno DATABASE_URL si no está configurada
if not os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5432/vambeai"

# Importar los modelos para que Alembic los detecte
from app.models import Base

# Ejecutar el comando de Alembic
if __name__ == "__main__":
    from alembic.config import Config
    from alembic import command
    
    # Configurar Alembic
    alembic_cfg = Config("alembic.ini")
    
    # Generar la migración
    print("Generando migración...")
    command.revision(
        alembic_cfg,
        autogenerate=True,
        message="Add authentication models (User, AuthToken, LoginHistory)",
        rev_id="initial"
    )
    print("Migración generada exitosamente.")
    
    # Aplicar la migración
    print("Aplicando migración...")
    command.upgrade(alembic_cfg, "head")
    print("Migración aplicada exitosamente.")
