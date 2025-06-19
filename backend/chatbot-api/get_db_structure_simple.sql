-- Tablas en la base de datos
SELECT '=== TABLAS EN LA BASE DE DATOS ===' AS info;
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Columnas de la tabla conversations
SELECT '\n=== COLUMNAS DE LA TABLA conversations ===' AS info;
SELECT 
    column_name, 
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'conversations'
ORDER BY ordinal_position;

-- Columnas de la tabla messages
SELECT '\n=== COLUMNAS DE LA TABLA messages ===' AS info;
SELECT 
    column_name, 
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'messages'
ORDER BY ordinal_position;

-- Claves primarias
SELECT '\n=== CLAVES PRIMARIAS ===' AS info;
SELECT
    tc.table_name,
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
WHERE tc.constraint_type = 'PRIMARY KEY'
ORDER BY tc.table_name, kcu.ordinal_position;

-- Claves foráneas
SELECT '\n=== CLAVES FORÁNEAS ===' AS info;
SELECT
    tc.table_name AS tabla_origen,
    kcu.column_name AS columna_origen,
    ccu.table_name AS tabla_referenciada,
    ccu.column_name AS columna_referenciada,
    rc.delete_rule AS on_delete,
    rc.update_rule AS on_update
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
LEFT JOIN information_schema.referential_constraints rc
    ON tc.constraint_name = rc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY';

-- Índices
SELECT '\n=== ÍNDICES ===' AS info;
SELECT
    t.relname AS table_name,
    i.relname AS index_name,
    a.attname AS column_name,
    CASE WHEN ix.indisunique THEN 'Sí' ELSE 'No' END AS es_unico,
    CASE WHEN ix.indisprimary THEN 'Sí' ELSE 'No' END AS es_primario
FROM
    pg_class t,
    pg_class i,
    pg_index ix,
    pg_attribute a
WHERE
    t.oid = ix.indrelid
    AND i.oid = ix.indexrelid
    AND a.attrelid = t.oid
    AND a.attnum = ANY(ix.indkey)
    AND t.relkind = 'r'
    AND t.relname IN (
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    )
ORDER BY
    t.relname, i.relname;
