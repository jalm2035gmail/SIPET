"""Add permission management tables

Revision ID: xxx
Revises: yyy
Create Date: 2024-01-15 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'xxx'
down_revision = '927131a4a55d'
branch_labels = None
depends_on = None


def _has_table(bind, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _has_index(bind, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(idx.get('name') == index_name for idx in inspector.get_indexes(table_name))


def upgrade():
    bind = op.get_bind()
    # Crear tabla custom_permissions
    if not _has_table(bind, 'custom_permissions'):
        op.create_table('custom_permissions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False),
            sa.Column('created_by', sa.Integer(), nullable=True),
            sa.Column('updated_by', sa.Integer(), nullable=True),
            sa.Column('name', sa.String(length=200), nullable=False),
            sa.Column('code', sa.String(length=100), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('resource', sa.String(length=50), nullable=False),
            sa.Column('action', sa.String(length=50), nullable=False),
            sa.Column('scope', sa.String(length=50), nullable=False),
            sa.Column('is_system', sa.Boolean(), nullable=False),
            sa.Column('module', sa.String(length=100), nullable=True),
            sa.Column('category', sa.String(length=100), nullable=True),
            sa.PrimaryKeyConstraint('id')
        )
    if not _has_index(bind, 'custom_permissions', op.f('ix_custom_permissions_code')):
        op.create_index(op.f('ix_custom_permissions_code'), 'custom_permissions', ['code'], unique=True)
    if not _has_index(bind, 'custom_permissions', op.f('ix_custom_permissions_name')):
        op.create_index(op.f('ix_custom_permissions_name'), 'custom_permissions', ['name'], unique=True)
    if not _has_index(bind, 'custom_permissions', op.f('ix_custom_permissions_id')):
        op.create_index(op.f('ix_custom_permissions_id'), 'custom_permissions', ['id'], unique=False)
    # Crear tabla role_permissions
    if not _has_table(bind, 'role_permissions'):
        op.create_table('role_permissions',
            sa.Column('role', sa.String(length=50), nullable=False),
            sa.Column('permission_id', sa.Integer(), nullable=False),
            sa.Column('granted_by', sa.Integer(), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.ForeignKeyConstraint(['permission_id'], ['custom_permissions.id'], ),
            sa.ForeignKeyConstraint(['granted_by'], ['users.id'], ),
            sa.PrimaryKeyConstraint('role', 'permission_id')
        )
    # Crear tabla user_custom_permissions
    if not _has_table(bind, 'user_custom_permissions'):
        op.create_table('user_custom_permissions',
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('permission_id', sa.Integer(), nullable=False),
            sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('granted_by', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['permission_id'], ['custom_permissions.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.ForeignKeyConstraint(['granted_by'], ['users.id'], ),
            sa.PrimaryKeyConstraint('user_id', 'permission_id')
        )
    # Crear tabla department_custom_permissions
    if not _has_table(bind, 'department_custom_permissions'):
        op.create_table('department_custom_permissions',
            sa.Column('department_id', sa.Integer(), nullable=False),
            sa.Column('permission_id', sa.Integer(), nullable=False),
            sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
            sa.Column('granted_by', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ),
            sa.ForeignKeyConstraint(['permission_id'], ['custom_permissions.id'], ),
            sa.ForeignKeyConstraint(['granted_by'], ['users.id'], ),
            sa.PrimaryKeyConstraint('department_id', 'permission_id')
        )

def downgrade():
    op.drop_table('department_custom_permissions')
    op.drop_table('user_custom_permissions')
    op.drop_table('role_permissions')
    
    op.drop_index(op.f('ix_custom_permissions_id'), table_name='custom_permissions')
    op.drop_index(op.f('ix_custom_permissions_name'), table_name='custom_permissions')
    op.drop_index(op.f('ix_custom_permissions_code'), table_name='custom_permissions')
    op.drop_table('custom_permissions')
