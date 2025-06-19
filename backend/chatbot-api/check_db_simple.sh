#!/bin/bash
# Script para verificar la estructura de la base de datos

echo "=== TABLAS EN LA BASE DE DATOS ==="
docker exec -i chatbot-postgres psql -U chatbot_user -d chatbot_db -c "\dt"

echo -e "\n=== ESTRUCTURA DE LA TABLA 'conversations' ==="
docker exec -i chatbot-postgres psql -U chatbot_user -d chatbot_db -c "\d+ conversations"

echo -e "\n=== ESTRUCTURA DE LA TABLA 'messages' ==="
docker exec -i chatbot-postgres psql -U chatbot_user -d chatbot_db -c "\d+ messages"

echo -e "\n=== CLAVES FORÁNEAS ==="
docker exec -i chatbot-postgres psql -U chatbot_user -d chatbot_db -c "\d" | grep -i "foreign"

echo -e "\n=== ÍNDICES ==="
docker exec -i chatbot-postgres psql -U chatbot_user -d chatbot_db -c "\di"
