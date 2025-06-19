# Script de PowerShell para verificar la estructura de la base de datos

Write-Host "=== TABLAS EN LA BASE DE DATOS ==="
docker exec -i chatbot-postgres psql -U chatbot_user -d chatbot_db -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"

Write-Host "`n=== ESTRUCTURA DE LA TABLA 'conversations' ==="
docker exec -i chatbot-postgres psql -U chatbot_user -d chatbot_db -c "\d+ conversations"

Write-Host "`n=== ESTRUCTURA DE LA TABLA 'messages' ==="
docker exec -i chatbot-postgres psql -U chatbot_user -d chatbot_db -c "\d+ messages"

Write-Host "`n=== CLAVES PRIMARIAS ==="
@"
SELECT
    tc.table_name,
    kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
WHERE tc.constraint_type = 'PRIMARY KEY'
ORDER BY tc.table_name, kcu.ordinal_position;
"@ | docker exec -i chatbot-postgres psql -U chatbot_user -d chatbot_db

Write-Host "`n=== CLAVES FORÁNEAS ==="
@"
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
"@ | docker exec -i chatbot-postgres psql -U chatbot_user -d chatbot_db

Write-Host "`n=== ÍNDICES ==="
@"
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
"@ | docker exec -i chatbot-postgres psql -U chatbot_user -d chatbot_db
