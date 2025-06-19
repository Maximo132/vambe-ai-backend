-- Script para obtener la estructura de la base de datos

-- Mostrar tablas
\echo '=== TABLAS EN LA BASE DE DATOS ==='
\dt

-- Mostrar estructura de la tabla conversations
\echo '\n=== ESTRUCTURA DE LA TABLA conversations ==='
\d+ conversations

-- Mostrar estructura de la tabla messages
\echo '\n=== ESTRUCTURA DE LA TABLA messages ==='
\d+ messages

-- Mostrar índices
\echo '\n=== ÍNDICES ==='
\di

-- Mostrar claves foráneas
\echo '\n=== CLAVES FORÁNEAS ==='
SELECT
    tc.table_name AS tabla_origen,
    kcu.column_name AS columna_origen,
    ccu.table_name AS tabla_referenciada,
    ccu.column_name AS columna_referenciada,
    rc.delete_rule AS on_delete,
    rc.update_rule AS on_update
FROM
    information_schema.table_constraints AS tc
    JOIN information_schema.key_column_usage AS kcu
        ON tc.constraint_name = kcu.constraint_name
        AND tc.table_schema = kcu.table_schema
    JOIN information_schema.constraint_column_usage AS ccu
        ON ccu.constraint_name = tc.constraint_name
        AND ccu.table_schema = tc.table_schema
    LEFT JOIN information_schema.referential_constraints rc
        ON tc.constraint_name = rc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY';

-- Mostrar información de columnas para ambas tablas
\echo '\n=== INFORMACIÓN DETALLADA DE COLUMNAS ==='
\echo '\nTabla: conversations'
SELECT
    column_name AS columna,
    data_type AS tipo_dato,
    is_nullable AS permite_nulos,
    column_default AS valor_por_defecto
FROM
    information_schema.columns
WHERE
    table_name = 'conversations'
ORDER BY
    ordinal_position;

\echo '\nTabla: messages'
SELECT
    column_name AS columna,
    data_type AS tipo_dato,
    is_nullable AS permite_nulos,
    column_default AS valor_por_defecto
FROM
    information_schema.columns
WHERE
    table_name = 'messages'
ORDER BY
    ordinal_position;
