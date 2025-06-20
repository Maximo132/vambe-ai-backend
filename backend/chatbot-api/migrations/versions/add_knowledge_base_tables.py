"""Add knowledge base tables

Revision ID: 1a2b3c4d5e6f
Revises: 
Create Date: 2023-10-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1a2b3c4d5e6f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Crear tabla knowledge_bases
    op.create_table(
        'knowledge_bases',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_public', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Crear tabla knowledge_base_documents
    op.create_table(
        'knowledge_base_documents',
        sa.Column('knowledge_base_id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['knowledge_base_id'], ['knowledge_bases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('knowledge_base_id', 'document_id')
    )
    
    # Crear índices
    op.create_index(op.f('ix_knowledge_bases_owner_id'), 'knowledge_bases', ['owner_id'], unique=False)
    op.create_index(op.f('ix_knowledge_bases_created_at'), 'knowledge_bases', ['created_at'], unique=False)
    op.create_index(op.f('ix_knowledge_base_documents_document_id'), 'knowledge_base_documents', ['document_id'], unique=False)


def downgrade():
    # Eliminar índices
    op.drop_index(op.f('ix_knowledge_base_documents_document_id'), table_name='knowledge_base_documents')
    op.drop_index(op.f('ix_knowledge_bases_created_at'), table_name='knowledge_bases')
    op.drop_index(op.f('ix_knowledge_bases_owner_id'), table_name='knowledge_bases')
    
    # Eliminar tablas
    op.drop_table('knowledge_base_documents')
    op.drop_table('knowledge_bases')
