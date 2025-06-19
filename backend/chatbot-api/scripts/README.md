# Scripts de Base de Datos

Este directorio contiene scripts útiles para la gestión de la base de datos del proyecto Vambe.ai Chatbot API.

## Scripts Disponibles

### `init_db.py`

Inicializa la base de datos, crea las tablas necesarias y aplica las migraciones.

**Uso:**
```bash
python -m scripts.init_db
```

### `migrate.py`

Herramienta de línea de comandos para gestionar migraciones de base de datos con Alembic.

**Comandos disponibles:**

- `up [--revision REVISION]`: Aplica migraciones hacia adelante hasta la revisión especificada (por defecto: head)
- `down REVISION`: Revierte migraciones hasta la revisión especificada
- `create MESSAGE [--autogenerate]`: Crea una nueva migración con el mensaje proporcionado
- `history`: Muestra el historial de migraciones
- `current`: Muestra la migración actual

**Ejemplos:**

```bash
# Aplicar todas las migraciones pendientes
python -m scripts.migrate up

# Revertir la última migración
python -m scripts.migrate down -1

# Crear una nueva migración
python -m scripts.migrate create "Agregar campo nuevo a usuarios" --autogenerate

# Ver historial de migraciones
python -m scripts.migrate history
```

### `seed_db.py`

Puebla la base de datos con datos de ejemplo para desarrollo y pruebas.

**Uso:**
```bash
python -m scripts.seed_db
```

**Nota:** Este script pedirá confirmación antes de proceder, ya que sobrescribirá los datos existentes.

### `clean_db.py`

Limpia todos los datos de la base de datos, manteniendo la estructura de las tablas. Útil para reiniciar el entorno de desarrollo.

**Uso:**
```bash
python -m scripts.clean_db
```

**¡ADVERTENCIA!** Este script eliminará TODOS los datos de la base de datos. Se pedirá confirmación antes de proceder.

## Configuración

Los scripts utilizan las siguientes variables de entorno (definidas en `.env`):

- `DATABASE_URL`: URL de conexión a la base de datos principal
- `TEST_DATABASE_URL`: URL de conexión a la base de datos de pruebas (opcional)

## Convenciones de Migraciones

- Las migraciones deben ser atómicas y reversibles
- Cada migración debe tener una descripción clara y concisa
- Las migraciones que modifican esquemas existentes deben incluir código para manejar datos existentes
- Utilizar `--autogenerate` con precaución y siempre revisar el código generado

## Mejores Prácticas

1. **Siempre haz copias de seguridad** antes de ejecutar operaciones destructivas
2. **Prueba las migraciones** en un entorno de desarrollo antes de aplicarlas en producción
3. **Documenta los cambios importantes** en el archivo de migración
4. **Mantén las migraciones pequeñas** y enfocadas en un solo cambio
5. **No modifiques migraciones ya aplicadas** - en su lugar, crea una nueva migración

## Solución de Problemas

Si encuentras problemas con las migraciones:

1. Verifica que la URL de la base de datos sea correcta
2. Asegúrate de que todas las migraciones anteriores se hayan aplicado correctamente
3. Revisa los logs para mensajes de error detallados
4. Si es necesario, puedes corregir manualmente la tabla `alembic_version`

## Recursos Adicionales

- [Documentación de Alembic](https://alembic.sqlalchemy.org/)
- [SQLAlchemy](https://www.sqlalchemy.org/)
- [PostgreSQL](https://www.postgresql.org/docs/)
