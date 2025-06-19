"""Initial migration

Revision ID: ac14d022f86b
Revises: 
Create Date: 2025-06-19 17:31:48.740407

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ac14d022f86b'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Crear la tabla de roles de usuario
    op.create_table(
        'user_roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=50), nullable=False, unique=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Insertar roles por defecto
    op.bulk_insert(
        sa.table('user_roles',
            sa.column('name', sa.String),
            sa.column('description', sa.String),
            sa.column('created_at', sa.DateTime),
            sa.column('updated_at', sa.DateTime)
        ),
        [
            {'name': 'superadmin', 'description': 'Super administrador con acceso total al sistema',
             'created_at': 'now()', 'updated_at': 'now()'},
            {'name': 'admin', 'description': 'Administradores de la plataforma',
             'created_at': 'now()', 'updated_at': 'now()'},
            {'name': 'agent', 'description': 'Agentes de soporte',
             'created_at': 'now()', 'updated_at': 'now()'},
            {'name': 'customer', 'description': 'Clientes finales',
             'created_at': 'now()', 'updated_at': 'now()'},
            {'name': 'guest', 'description': 'Usuarios invitados (acceso limitado)',
             'created_at': 'now()', 'updated_at': 'now()'}
        ]
    )
    
    # Crear tabla de usuarios
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True, index=True, server_default=sa.text('uuid_generate_v4()')),
        sa.Column('email', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('first_name', sa.String(100), nullable=True),
        sa.Column('last_name', sa.String(100), nullable=True),
        sa.Column('role', sa.String(20), nullable=False, server_default='customer'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['role'], ['user_roles.name'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Crear tabla de conversaciones
    op.create_table(
        'conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('metadata', sa.JSON, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    
    # Crear tabla de mensajes
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', sa.JSON, nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )
    
    # Crear índices adicionales
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_conversations_user_id'), 'conversations', ['user_id'])
    op.create_index(op.f('ix_messages_conversation_id'), 'messages', ['conversation_id'])
    op.create_index(op.f('ix_messages_user_id'), 'messages', ['user_id'])


def downgrade() -> None:
    # Eliminar índices
    op.drop_index(op.f('ix_messages_user_id'), table_name='messages')
    op.drop_index(op.f('ix_messages_conversation_id'), table_name='messages')
    op.drop_index(op.f('ix_conversations_user_id'), table_name='conversations')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    
    # Eliminar tablas en orden inverso para evitar problemas de claves foráneas
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('users')
    op.drop_table('user_roles')
