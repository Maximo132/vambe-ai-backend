import sys
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database

# Añadir el directorio src al path
src_dir = str(Path(__file__).parent.absolute() / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Configurar la URL de la base de datos
DB_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg2://chatbot_user:chatbot_password@localhost:5432/chatbot_db")

def create_tables():
    # Crear motor de base de datos
    engine = create_engine(DB_URL, echo=True)
    
    # Crear la base de datos si no existe
    if not database_exists(engine.url):
        print("Creando base de datos...")
        create_database(engine.url)
    
    # Importar base de datos y modelos
    print("Importando modelos...")
    from app.db.base import Base
    from app.models.chat import Conversation, Message
    from app.models.user import User
    
    # Crear todas las tablas
    print("Creando tablas...")
    Base.metadata.create_all(bind=engine)
    print("¡Tablas creadas exitosamente!")

if __name__ == "__main__":
    create_tables()
