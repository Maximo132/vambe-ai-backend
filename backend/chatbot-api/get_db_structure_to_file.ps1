# Script de PowerShell para obtener la estructura de la base de datos y guardarla en un archivo

# Archivo de salida
$outputFile = "db_structure_$(Get-Date -Format 'yyyyMMdd_HHmmss').txt"

# Función para ejecutar una consulta SQL y devolver los resultados
function Get-PostgresQueryResult {
    param (
        [string]$Query
    )
    
    $result = docker exec -i chatbot-postgres psql -U chatbot_user -d chatbot_db -c "$Query" 2>&1
    return $result
}

# Iniciar el archivo de salida
"=== ESTRUCTURA DE LA BASE DE DATOS ===" | Out-File -FilePath $outputFile -Encoding utf8
"Generado el: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -FilePath $outputFile -Append -Encoding utf8
"`n" | Out-File -FilePath $outputFile -Append -Encoding utf8

# Tablas en la base de datos
"=== TABLAS EN LA BASE DE DATOS ===" | Out-File -FilePath $outputFile -Append -Encoding utf8
$tables = Get-PostgresQueryResult "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"
$tables | Out-File -FilePath $outputFile -Append -Encoding utf8

# Para cada tabla, obtener su estructura
foreach ($table in ($tables | Where-Object { $_ -match '^\s*[a-z]' } | ForEach-Object { $_.Trim() })) {
    "`n=== ESTRUCTURA DE LA TABLA '$table' ===" | Out-File -FilePath $outputFile -Append -Encoding utf8
    $structure = Get-PostgresQueryResult "\d+ $table"
    $structure | Out-File -FilePath $outputFile -Append -Encoding utf8
}

# Claves primarias
"`n=== CLAVES PRIMARIAS ===" | Out-File -FilePath $outputFile -Append -Encoding utf8
$primaryKeys = Get-PostgresQueryResult @"
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
$primaryKeys | Out-File -FilePath $outputFile -Append -Encoding utf8

# Claves foráneas
"`n=== CLAVES FORÁNEAS ===" | Out-File -FilePath $outputFile -Append -Encoding utf8
$foreignKeys = Get-PostgresQueryResult @"
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
$foreignKeys | Out-File -FilePath $outputFile -Append -Encoding utf8

# Índices
"`n=== ÍNDICES ===" | Out-File -FilePath $outputFile -Append -Encoding utf8
$indexes = Get-PostgresQueryResult @"
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
$indexes | Out-File -FilePath $outputFile -Append -Encoding utf8

Write-Host "La estructura de la base de datos se ha guardado en: $outputFile" -ForegroundColor Green
