-- =============================================
-- Esquema de la base de datos Vambe.ai
-- Creado: 2025-06-19
-- =============================================

-- Habilitar extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- Nota: Para búsqueda vectorial, necesitarás instalar pgvector
-- CREATE EXTENSION IF NOT EXISTS vector;

-- =============================================
-- Tabla: user_roles
-- Almacena los roles de usuario disponibles
-- =============================================
CREATE TABLE IF NOT EXISTS user_roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Insertar roles por defecto
INSERT INTO user_roles (name, description) VALUES 
('superadmin', 'Super administrador con acceso total al sistema'),
('admin', 'Administradores de la plataforma'),
('agent', 'Agentes de soporte'),
('customer', 'Clientes finales')
ON CONFLICT (name) DO NOTHING;

-- =============================================
-- Tabla: users
-- Almacena la información de los usuarios
-- =============================================
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(100) UNIQUE,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    hashed_password VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    full_name VARCHAR(201), -- Se actualiza con trigger
    avatar_url VARCHAR(500),
    bio TEXT,
    preferences JSONB DEFAULT '{}'::jsonb,
    settings JSONB DEFAULT '{}'::jsonb,
    role VARCHAR(20) NOT NULL DEFAULT 'customer',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    last_login TIMESTAMP,
    login_count INTEGER NOT NULL DEFAULT 0,
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP,
    verification_token VARCHAR(100) UNIQUE,
    verification_token_expires TIMESTAMP,
    password_reset_token VARCHAR(100) UNIQUE,
    password_reset_expires TIMESTAMP,
    two_factor_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    two_factor_secret VARCHAR(255),
    backup_codes JSONB,
    email_notifications BOOLEAN NOT NULL DEFAULT TRUE,
    push_notifications BOOLEAN NOT NULL DEFAULT TRUE,
    sms_notifications BOOLEAN NOT NULL DEFAULT FALSE,
    last_password_change TIMESTAMP NOT NULL DEFAULT NOW(),
    last_seen TIMESTAMP,
    last_ip_address VARCHAR(45),
    active_sessions JSONB DEFAULT '[]'::jsonb,
    show_online_status BOOLEAN NOT NULL DEFAULT TRUE,
    allow_direct_messages BOOLEAN NOT NULL DEFAULT TRUE,
    theme VARCHAR(20) NOT NULL DEFAULT 'system',
    CONSTRAINT fk_user_role FOREIGN KEY (role) REFERENCES user_roles(name) ON UPDATE CASCADE
);

-- Índices para la tabla de usuarios
CREATE INDEX IF NOT EXISTS idx_user_email_lower ON users (LOWER(email));
CREATE INDEX IF NOT EXISTS idx_user_username_lower ON users (LOWER(username));
CREATE INDEX IF NOT EXISTS idx_user_created_at ON users (created_at);
CREATE INDEX IF NOT EXISTS idx_user_role ON users (role);
CREATE INDEX IF NOT EXISTS idx_user_status ON users (is_active, is_verified);

-- =============================================
-- Tabla: user_followers
-- Relación de seguidores entre usuarios
-- =============================================
CREATE TABLE IF NOT EXISTS user_followers (
    follower_id UUID NOT NULL,
    followed_id UUID NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (follower_id, followed_id),
    CONSTRAINT fk_follower FOREIGN KEY (follower_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_followed FOREIGN KEY (followed_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Índices para la tabla de seguidores
CREATE INDEX IF NOT EXISTS idx_user_followers_follower ON user_followers(follower_id);
CREATE INDEX IF NOT EXISTS idx_user_followers_followed ON user_followers(followed_id);
CREATE INDEX IF NOT EXISTS idx_user_followers_created_at ON user_followers(created_at);

-- =============================================
-- Tabla: conversations
-- Almacena las conversaciones de chat
-- =============================================
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP,
    CONSTRAINT fk_conversation_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_conversation_status CHECK (status IN ('active', 'archived', 'deleted'))
);

-- Índices para la tabla de conversaciones
CREATE INDEX IF NOT EXISTS idx_conversation_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversation_status ON conversations(status);
CREATE INDEX IF NOT EXISTS idx_conversation_created_at ON conversations(created_at);
CREATE INDEX IF NOT EXISTS idx_conversation_updated_at ON conversations(updated_at);

-- =============================================
-- Tabla: messages
-- Almacena los mensajes de las conversaciones
-- =============================================
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL,
    user_id UUID,
    content TEXT NOT NULL,
    role VARCHAR(20) NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP,
    parent_message_id UUID,
    tokens INTEGER,
    -- embedding VECTOR(1536), -- Descomentar cuando se instale pgvector
    CONSTRAINT fk_message_conversation FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    CONSTRAINT fk_message_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT fk_message_parent FOREIGN KEY (parent_message_id) REFERENCES messages(id) ON DELETE SET NULL,
    CONSTRAINT chk_message_role CHECK (role IN ('user', 'assistant', 'system', 'function'))
);

-- Índices para la tabla de mensajes
CREATE INDEX IF NOT EXISTS idx_message_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_message_user ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_message_created_at ON messages(created_at);
CREATE INDEX IF NOT EXISTS idx_message_role ON messages(role);
CREATE INDEX IF NOT EXISTS idx_message_parent ON messages(parent_message_id);
-- CREATE INDEX IF NOT EXISTS idx_message_embedding ON messages USING ivfflat (embedding vector_cosine_ops); -- Para pgvector

-- =============================================
-- Tabla: documents
-- Almacena los documentos cargados por los usuarios
-- =============================================
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    file_path VARCHAR(500) NOT NULL,
    file_type VARCHAR(100) NOT NULL,
    file_size BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'uploaded',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP,
    processed_at TIMESTAMP,
    error_message TEXT,
    CONSTRAINT fk_document_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT chk_document_status CHECK (status IN ('uploaded', 'processing', 'processed', 'error', 'deleted'))
);

-- Índices para la tabla de documentos
CREATE INDEX IF NOT EXISTS idx_document_user ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_document_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_document_created_at ON documents(created_at);
CREATE INDEX IF NOT EXISTS idx_document_updated_at ON documents(updated_at);
CREATE INDEX IF NOT EXISTS idx_document_title_fts ON documents USING GIN (to_tsvector('english', title));
CREATE INDEX IF NOT EXISTS idx_document_description_fts ON documents USING GIN (to_tsvector('english', description));

-- =============================================
-- Tabla: document_chunks
-- Almacena fragmentos de documentos para búsqueda
-- =============================================
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    page_number INTEGER,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    -- embedding VECTOR(1536), -- Descomentar cuando se instale pgvector
    CONSTRAINT fk_chunk_document FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);

-- Índices para la tabla de fragmentos de documentos
CREATE INDEX IF NOT EXISTS idx_chunk_document ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunk_index ON document_chunks(chunk_index);
CREATE INDEX IF NOT EXISTS idx_chunk_page ON document_chunks(page_number);
CREATE INDEX IF NOT EXISTS idx_chunk_content_fts ON document_chunks USING GIN (to_tsvector('english', content));
-- CREATE INDEX IF NOT EXISTS idx_chunk_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops); -- Para pgvector

-- =============================================
-- Función y trigger para actualizar full_name
-- =============================================
CREATE OR REPLACE FUNCTION update_users_full_name()
RETURNS TRIGGER AS $$
BEGIN
    NEW.full_name := TRIM(CONCAT(COALESCE(NEW.first_name, ''), ' ', COALESCE(NEW.last_name, '')));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Crear el trigger para actualizar full_name automáticamente
CREATE OR REPLACE TRIGGER trg_users_full_name
BEFORE INSERT OR UPDATE OF first_name, last_name ON users
FOR EACH ROW
EXECUTE FUNCTION update_users_full_name();

-- =============================================
-- Función para actualizar updated_at automáticamente
-- =============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Crear triggers para actualizar automáticamente updated_at
CREATE OR REPLACE TRIGGER trg_update_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER trg_update_conversations_updated_at
BEFORE UPDATE ON conversations
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER trg_update_messages_updated_at
BEFORE UPDATE ON messages
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER trg_update_documents_updated_at
BEFORE UPDATE ON documents
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER trg_update_document_chunks_updated_at
BEFORE UPDATE ON document_chunks
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
