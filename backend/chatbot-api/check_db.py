import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def check_database_connection():
    """Verifica la conexión a la base de datos."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL no está configurada en el archivo .env")
        return False
    
    print(f"Intentando conectar a la base de datos: {db_url}")
    
    try:
        # Crear un motor SQLAlchemy
        engine = create_engine(db_url)
        
        # Intentar conectarse a la base de datos
        with engine.connect() as connection:
            # Ejecutar una consulta simple
            result = connection.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"Conexión exitosa a la base de datos: {version}")
            
            # Verificar si la base de datos existe
            if "vambeai" in db_url:
                result = connection.execute(text("SELECT current_database()"))
                db_name = result.scalar()
                print(f"Base de datos actual: {db_name}")
                
                # Verificar si existen las tablas necesarias
                result = connection.execute(
                    text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    """)
                )
                tables = [row[0] for row in result.fetchall()]
                print(f"\nTablas existentes en la base de datos:")
                for table in tables:
                    print(f"- {table}")
                
                return True
                
    except Exception as e:
        print(f"Error al conectar a la base de datos: {e}")
        
        # Si la base de datos no existe, intentar crearla
        if "does not exist" in str(e):
            print("\nLa base de datos no existe. Intentando crearla...")
            try:
                # Extraer los datos de conexión para la base de datos postgres
                from urllib.parse import urlparse
                from sqlalchemy_utils import database_exists, create_database
                
                # Crear una URL para la base de datos postgres
                parsed_url = urlparse(db_url)
                base_db_url = f"{parsed_url.scheme}://{parsed_url.hostname}:{parsed_url.port}/postgres"
                
                # Conectar a la base de datos postgres
                engine = create_engine(base_db_url)
                
                # Crear la base de datos si no existe
                if not database_exists(db_url):
                    print(f"Creando base de datos: {parsed_url.path[1:]}")
                    create_database(db_url)
                    print("Base de datos creada exitosamente.")
                    return True
                else:
                    print("La base de datos ya existe.")
                    return True
                    
            except Exception as e2:
                print(f"Error al crear la base de datos: {e2}")
                return False
        
        return False

if __name__ == "__main__":
    if check_database_connection():
        sys.exit(0)
    else:
        sys.exit(1)
