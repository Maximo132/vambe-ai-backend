# Script de PowerShell para obtener la estructura de la base de datos paso a paso

# Función para ejecutar una consulta SQL y mostrar los resultados
function Invoke-PostgresQuery {
    param (
        [string]$Query
    )
    
    Write-Host "`n$Query`n" -ForegroundColor Green
    $result = docker exec -i chatbot-postgres psql -U chatbot_user -d chatbot_db -c "$Query"
    Write-Host $result
    Write-Host "`n" + ("-" * 80) + "`n"
}

# Tablas en la base de datos
Write-Host "=== TABLAS EN LA BASE DE DATOS ===" -ForegroundColor Cyan
Invoke-PostgresQuery "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"

# Columnas de la tabla conversations
Write-Host "=== COLUMNAS DE LA TABLA conversations ===" -ForegroundColor Cyan
Invoke-PostgresQuery @"
SELECT 
    column_name, 
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'conversations'
ORDER BY ordinal_position;
"@

# Columnas de la tabla messages
Write-Host "=== COLUMNAS DE LA TABLA messages ===" -ForegroundColor Cyan
Invoke-PostgresQuery @"
SELECT 
    column_name, 
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'messages'
ORDER BY ordinal_position;
"@

# Claves primarias
Write-Host "=== CLAVES PRIMARIAS ===" -ForegroundColor Cyan
Invoke-PostgresQuery @"
SELECT
    tc.table_name,
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
WHERE tc.constraint_type = 'PRIMARY KEY'
ORDER BY tc.table_name, kcu.ordinal_position;
"@

# Claves foráneas
Write-Host "=== CLAVES FORÁNEAS ===" -ForegroundColor Cyan
Invoke-PostgresQuery @"
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
"@

# Índices
Write-Host "=== ÍNDICES ===" -ForegroundColor Cyan
Invoke-PostgresQuery @"
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
"@
