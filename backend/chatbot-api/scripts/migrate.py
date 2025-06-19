"""
Script para ejecutar migraciones de base de datos con Alembic.

Este script proporciona una interfaz de línea de comandos para:
- Aplicar migraciones
- Revertir migraciones
- Generar migraciones automáticas
- Mostrar el historial de migraciones
"""
import os
import sys
import logging
import argparse
from pathlib import Path
from typing import Optional, List

# Configurar logging básico
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

def import_alembic():
    """Importa los módulos necesarios de Alembic."""
    try:
        from alembic.config import Config
        from alembic import command
        from alembic.util.exc import CommandError
        return Config, command, CommandError
    except ImportError as e:
        logger.error(f"Error al importar módulos de Alembic: {e}")
        sys.exit(1)

def get_alembic_config():
    """Obtiene la configuración de Alembic."""
    try:
        from app.core.config import settings
        
        # Configurar Alembic
        project_root = Path(__file__).parent.parent
        alembic_ini = project_root / 'alembic.ini'
        
        if not alembic_ini.exists():
            logger.error(f"Archivo de configuración de Alembic no encontrado: {alembic_ini}")
            sys.exit(1)
        
        # Cargar configuración
        Config, _, _ = import_alembic()
        alembic_cfg = Config(str(alembic_ini))
        
        # Actualizar configuración con la URL de la base de datos
        alembic_cfg.set_main_option('sqlalchemy.url', str(settings.DATABASE_URL))
        
        return alembic_cfg
    except Exception as e:
        logger.error(f"Error al cargar la configuración de Alembic: {e}")
        sys.exit(1)

def migrate_up(revision: str = 'head') -> bool:
    """Aplica migraciones hacia adelante."""
    try:
        _, command, _ = import_alembic()
        alembic_cfg = get_alembic_config()
        
        logger.info(f"Aplicando migraciones hasta la revisión: {revision}")
        command.upgrade(alembic_cfg, revision)
        logger.info("Migraciones aplicadas exitosamente.")
        return True
    except Exception as e:
        logger.error(f"Error al aplicar migraciones: {e}")
        return False

def migrate_down(revision: str) -> bool:
    """Revierte migraciones."""
    try:
        _, command, _ = import_alembic()
        alembic_cfg = get_alembic_config()
        
        logger.info(f"Revirtiendo a la revisión: {revision}")
        command.downgrade(alembic_cfg, revision)
        logger.info("Migraciones revertidas exitosamente.")
        return True
    except Exception as e:
        logger.error(f"Error al revertir migraciones: {e}")
        return False

def make_migration(message: str, autogenerate: bool = False) -> bool:
    """Crea una nueva migración."""
    try:
        _, command, _ = import_alembic()
        alembic_cfg = get_alembic_config()
        
        logger.info(f"Creando nueva migración: {message}")
        command.revision(
            alembic_cfg,
            message=message,
            autogenerate=autogenerate
        )
        logger.info("Migración creada exitosamente.")
        return True
    except Exception as e:
        logger.error(f"Error al crear migración: {e}")
        return False

def show_history() -> None:
    """Muestra el historial de migraciones."""
    try:
        _, command, _ = import_alembic()
        alembic_cfg = get_alembic_config()
        
        logger.info("Historial de migraciones:")
        command.history(alembic_cfg)
    except Exception as e:
        logger.error(f"Error al mostrar el historial de migraciones: {e}")

def show_current() -> None:
    """Muestra la migración actual."""
    try:
        _, command, _ = import_alembic()
        alembic_cfg = get_alembic_config()
        
        logger.info("Migración actual:")
        command.current(alembic_cfg)
    except Exception as e:
        logger.error(f"Error al mostrar la migración actual: {e}")

def main() -> int:
    """Función principal del script de migración."""
    # Configurar rutas
    setup_paths()
    
    # Configurar el parser de argumentos
    parser = argparse.ArgumentParser(description='Herramienta de migración de base de datos')
    subparsers = parser.add_subparsers(dest='command', help='Comando a ejecutar')
    
    # Comando: up
    up_parser = subparsers.add_parser('up', help='Aplicar migraciones')
    up_parser.add_argument('--revision', type=str, default='head',
                          help='Revisión objetivo (por defecto: head)')
    
    # Comando: down
    down_parser = subparsers.add_parser('down', help='Revertir migraciones')
    down_parser.add_argument('revision', type=str, 
                            help='Revisión objetivo (ej: -1, head-1, <revision_hash>)')
    
    # Comando: create
    create_parser = subparsers.add_parser('create', help='Crear nueva migración')
    create_parser.add_argument('message', type=str, help='Mensaje descriptivo de la migración')
    create_parser.add_argument('--autogenerate', action='store_true',
                              help='Generar automáticamente la migración basada en los modelos')
    
    # Comando: history
    subparsers.add_parser('history', help='Mostrar historial de migraciones')
    
    # Comando: current
    subparsers.add_parser('current', help='Mostrar migración actual')
    
    # Parsear argumentos
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Ejecutar comando
    try:
        if args.command == 'up':
            return 0 if migrate_up(args.revision) else 1
        elif args.command == 'down':
            return 0 if migrate_down(args.revision) else 1
        elif args.command == 'create':
            return 0 if make_migration(args.message, args.autogenerate) else 1
        elif args.command == 'history':
            show_history()
            return 0
        elif args.command == 'current':
            show_current()
            return 0
        else:
            logger.error(f"Comando no reconocido: {args.command}")
            return 1
    except Exception as e:
        logger.error(f"Error inesperado: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
