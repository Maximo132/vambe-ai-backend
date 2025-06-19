"""
Script para limpiar la base de datos.

Este script elimina todos los datos de las tablas de la base de datos,
pero mantiene la estructura de las mismas. Útil para reiniciar el entorno de desarrollo.
"""
import sys
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def setup_paths() -> None:
    """Configura las rutas necesarias para las importaciones."""
    # Añadir el directorio src al path
    project_root = Path(__file__).parent.parent
    src_path = project_root / 'src'
    
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))
    
    # Configurar nivel de logging para SQLAlchemy
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

def clean_database() -> bool:
    """Limpia todas las tablas de la base de datos."""
    try:
        from sqlalchemy import text
        from sqlalchemy.orm import Session
        from app.db.session import engine, SessionLocal
        from app.db.base import Base
        
        # Obtener metadatos
        metadata = Base.metadata
        
        # Crear una sesión
        db = SessionLocal()
        
        try:
            logger.info("Iniciando limpieza de la base de datos...")
            
            # Deshabilitar restricciones de clave foránea temporalmente
            if 'postgresql' in str(engine.url):
                db.execute(text('SET session_replication_role = \'replica\';'))
            
            # Eliminar datos de todas las tablas
            for table in reversed(metadata.sorted_tables):
                logger.info(f"Eliminando datos de la tabla: {table.name}")
                db.execute(table.delete())
            
            # Volver a habilitar restricciones de clave foránea
            if 'postgresql' in str(engine.url):
                db.execute(text('SET session_replication_role = \'origin\';'))
            
            # Confirmar cambios
            db.commit()
            logger.info("Base de datos limpiada exitosamente.")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error al limpiar la base de datos: {e}")
            return False
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error inesperado al limpiar la base de datos: {e}")
        return False

def reset_sequences() -> bool:
    """Reinicia las secuencias de las tablas (útil para PostgreSQL)."""
    try:
        from sqlalchemy import text
        from sqlalchemy.orm import Session
        from app.db.session import SessionLocal, engine
        
        if 'postgresql' not in str(engine.url):
            logger.info("No es una base de datos PostgreSQL. Saltando reinicio de secuencias.")
            return True
            
        db = SessionLocal()
        
        try:
            logger.info("Reiniciando secuencias...")
            
            # Obtener todas las secuencias
            result = db.execute("""
                SELECT c.relname
                FROM pg_class c
                WHERE c.relkind = 'S';
            """)
            
            sequences = [row[0] for row in result.fetchall()]
            
            # Reiniciar cada secuencia
            for seq in sequences:
                table_name = seq.replace('_id_seq', '')
                logger.info(f"Reiniciando secuencia: {seq} para la tabla: {table_name}")
                
                # Obtener el ID máximo actual de la tabla
                max_id = db.execute(
                    text(f'SELECT COALESCE(MAX(id), 0) + 1 FROM {table_name}')
                ).scalar() or 1
                
                # Establecer el valor de la secuencia
                db.execute(
                    text(f"SELECT setval('{seq}', :max_id, false)"),
                    {'max_id': max_id}
                )
            
            db.commit()
            logger.info("Secuencias reiniciadas exitosamente.")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error al reiniciar secuencias: {e}")
            return False
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error inesperado al reiniciar secuencias: {e}")
        return False

def main() -> int:
    """Función principal del script de limpieza de base de datos."""
    # Configurar rutas
    setup_paths()
    
    # Confirmar con el usuario
    print("\n=== ADVERTENCIA ===\n")
    print("Este script eliminará TODOS los datos de la base de datos.")
    print("Esta operación NO se puede deshacer.\n")
    
    confirm = input("¿Estás absolutamente seguro de que deseas continuar? (escribe 'si' para confirmar): ")
    if confirm.lower() != 'si':
        print("Operación cancelada.")
        return 0
    
    # Limpiar base de datos
    if not clean_database():
        return 1
    
    # Reiniciar secuencias (solo para PostgreSQL)
    if not reset_sequences():
        logger.warning("No se pudieron reiniciar las secuencias. La base de datos puede necesitar un reinicio manual.")
    
    logger.info("¡Base de datos limpiada exitosamente!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
