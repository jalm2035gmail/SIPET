"""
Revision para agregar la tabla ia_config para configuración de IA
Revision ID: 20260228_add_ia_config_table
Revises: 
Create Date: 2026-02-28
"""

# revision identifiers, used by Alembic.
revision = '20260228_add_ia_config_table'
down_revision = None
branch_labels = None
depends_on = None
from alembic import op
import sqlalchemy as sa


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade():
    if _table_exists('ia_config'):
        return
    op.create_table(
        'ia_config',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('ai_provider', sa.String, nullable=False),
        sa.Column('ai_api_key', sa.String, nullable=False),
        sa.Column('ai_base_url', sa.String, default=""),
        sa.Column('ai_model', sa.String, default=""),
        sa.Column('ai_timeout', sa.Integer, default=30),
        sa.Column('updated_at', sa.DateTime, nullable=True),
    )

def downgrade():
    if _table_exists('ia_config'):
        op.drop_table('ia_config')
