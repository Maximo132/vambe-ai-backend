-- Crear la tabla de roles de usuario
CREATE TABLE IF NOT EXISTS user_roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Insertar roles por defecto si no existen
INSERT INTO user_roles (name, description, created_at, updated_at)
SELECT 'superadmin', 'Super administrador con acceso total al sistema', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM user_roles WHERE name = 'superadmin');

INSERT INTO user_roles (name, description, created_at, updated_at)
SELECT 'admin', 'Administradores de la plataforma', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM user_roles WHERE name = 'admin');

INSERT INTO user_roles (name, description, created_at, updated_at)
SELECT 'agent', 'Agentes de soporte', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM user_roles WHERE name = 'agent');

INSERT INTO user_roles (name, description, created_at, updated_at)
SELECT 'customer', 'Clientes finales', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM user_roles WHERE name = 'customer');

INSERT INTO user_roles (name, description, created_at, updated_at)
SELECT 'guest', 'Usuarios invitados (acceso limitado)', NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM user_roles WHERE name = 'guest');

-- Crear la tabla de usuarios
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    external_id VARCHAR(100) UNIQUE,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    hashed_password VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    full_name VARCHAR(201),
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

-- Crear índices para la tabla de usuarios
CREATE INDEX IF NOT EXISTS idx_user_email_lower ON users (LOWER(email));
CREATE INDEX IF NOT EXISTS idx_user_username_lower ON users (LOWER(username));
CREATE INDEX IF NOT EXISTS idx_user_created_at ON users (created_at);
CREATE INDEX IF NOT EXISTS idx_user_role ON users (role);
CREATE INDEX IF NOT EXISTS idx_user_status ON users (is_active, is_verified);

-- Crear tabla de seguidores (relación muchos a muchos)
CREATE TABLE IF NOT EXISTS user_followers (
    follower_id UUID NOT NULL,
    followed_id UUID NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (follower_id, followed_id),
    CONSTRAINT fk_follower FOREIGN KEY (follower_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_followed FOREIGN KEY (followed_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Crear tabla de conversaciones
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP,
    CONSTRAINT fk_conversation_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Crear tabla de mensajes
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
    CONSTRAINT fk_message_conversation FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    CONSTRAINT fk_message_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- Crear tabla de documentos
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    content_type VARCHAR(100),
    file_path VARCHAR(500),
    file_size INTEGER,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP,
    CONSTRAINT fk_document_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Crear tabla de historial de inicio de sesión
CREATE TABLE IF NOT EXISTS login_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    user_agent TEXT,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_login_history_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Crear tabla de tokens de autenticación
CREATE TABLE IF NOT EXISTS auth_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL,
    token VARCHAR(500) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_auth_token_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Crear índices adicionales
CREATE INDEX IF NOT EXISTS idx_conversation_user ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_message_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_message_user ON messages(user_id);
CREATE INDEX IF NOT EXISTS idx_document_user ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_login_history_user ON login_history(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_token_user ON auth_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_token_token ON auth_tokens(token);

-- Asegurarse de que la extensión uuid-ossp esté habilitada
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Actualizar la tabla de control de migraciones
INSERT INTO alembic_version (version_num) VALUES ('ac14d022f86b')
ON CONFLICT (version_num) DO NOTHING;
