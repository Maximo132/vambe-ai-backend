-- Script para generar un informe detallado de la estructura de la base de datos

-- Configuración de salida
\o database_schema_report.txt

-- Información de la base de datos
\echo '=== INFORMACIÓN DE LA BASE DE DATOS ==='
SELECT 
    datname AS database_name,
    pg_size_pretty(pg_database_size(datname)) AS size,
    pg_encoding_to_char(encoding) AS encoding,
    datcollate AS collation,
    datctype AS ctype
FROM pg_database 
WHERE datname = current_database();

-- Tablas en la base de datos
\echo '\n=== TABLAS EN LA BASE DE DATOS ==='
SELECT 
    table_name,
    pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) AS total_size,
    pg_size_pretty(pg_relation_size(quote_ident(table_name))) AS table_size,
    pg_size_pretty(pg_total_relation_size(quote_ident(table_name)) - pg_relation_size(quote_ident(table_name))) AS index_size,
    (SELECT reltuples FROM pg_class WHERE oid = (quote_ident(table_name)::regclass)::oid)::bigint AS estimated_rows
FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

-- Estructura de la tabla 'conversations'
\echo '\n=== ESTRUCTURA DE LA TABLA conversations ==='
\d+ conversations

-- Índices de la tabla 'conversations'
\echo '\n=== ÍNDICES DE LA TABLA conversations ==='
SELECT 
    i.relname AS index_name,
    a.attname AS column_name,
    ix.indisunique AS is_unique,
    ix.indisprimary AS is_primary
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
    AND t.relname = 'conversations'
ORDER BY 
    t.relname, i.relname;

-- Estructura de la tabla 'messages'
\echo '\n=== ESTRUCTURA DE LA TABLA messages ==='
\d+ messages

-- Índices de la tabla 'messages'
\echo '\n=== ÍNDICES DE LA TABLA messages ==='
SELECT 
    i.relname AS index_name,
    a.attname AS column_name,
    ix.indisunique AS is_unique,
    ix.indisprimary AS is_primary
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
    AND t.relname = 'messages'
ORDER BY 
    t.relname, i.relname;

-- Restaurar salida estándar
\o
