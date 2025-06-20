"""
Script para verificar el estado de la base de datos y las migraciones de Alembic.
"""
import os
import sys
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def check_database_connection():
    """Verifica la conexión a la base de datos."""
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            print("❌ DATABASE_URL no está configurada en las variables de entorno")
            return False
        
        engine = create_engine(database_url)
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version();"))
            db_version = result.scalar()
            print(f"✅ Conectado a PostgreSQL: {db_version}")
            return True
    except Exception as e:
        print(f"❌ Error al conectar a la base de datos: {e}")
        return False

def check_alembic_version():
    """Verifica la versión actual de Alembic."""
    try:
        # Configurar Alembic
        alembic_cfg = Config("alembic.ini")
        
        # Obtener la versión actual
        current = command.current(alembic_cfg)
        if current:
            print(f"✅ Versión actual de Alembic: {current}")
        else:
            print("ℹ️ No se encontró información de versión de Alembic")
        
        # Mostrar historial de migraciones
        print("\n📜 Historial de migraciones:")
        command.history(alembic_cfg)
        
        return True
    except Exception as e:
        print(f"❌ Error al verificar la versión de Alembic: {e}")
        return False

def check_database_tables():
    """Verifica las tablas existentes en la base de datos."""
    try:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            print("❌ DATABASE_URL no está configurada en las variables de entorno")
            return False
        
        engine = create_engine(database_url)
        with engine.connect() as connection:
            # Obtener todas las tablas
            result = connection.execute(
                text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
                """)
            )
            
            tables = [row[0] for row in result]
            print(f"\n📊 Tablas en la base de datos ({len(tables)}):")
            for table in tables:
                print(f"  - {table}")
            
            return True
    except Exception as e:
        print(f"❌ Error al verificar las tablas de la base de datos: {e}")
        return False

def main():
    print("🔍 Verificando configuración de la base de datos...\n")
    
    # Verificar conexión a la base de datos
    if not check_database_connection():
        sys.exit(1)
    
    # Verificar tablas existentes
    if not check_database_tables():
        sys.exit(1)
    
    # Verificar migraciones de Alembic
    if not check_alembic_version():
        sys.exit(1)
    
    print("\n✅ Verificación completada exitosamente!")

if __name__ == "__main__":
    main()
