"""add usuario column to users table
"""
revision = 'add_usuario_column'
down_revision = '927131a4a55d'
branch_labels = None
depends_on = None
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('users', sa.Column('usuario', sa.String(length=50), nullable=True))

def downgrade():
    op.drop_column('users', 'usuario')
