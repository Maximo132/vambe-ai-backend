import os
import sys

# Añadir el directorio src al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from alembic import command
from alembic.config import Config

alembic_cfg = Config("alembic.ini")
command.upgrade(alembic_cfg, "head")
