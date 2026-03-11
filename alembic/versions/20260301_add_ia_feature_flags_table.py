"""
Revision para agregar la tabla ia_feature_flags para feature flags IA
Revision ID: 20260301_add_ia_feature_flags_table
Revises: 
Create Date: 2026-03-01
"""

# revision identifiers, used by Alembic.
revision = '20260301_add_ia_feature_flags_table'
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


def _table_exists(table_name):
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()

def upgrade():
    if _table_exists('ia_feature_flags'):
        return
    op.create_table(
        'ia_feature_flags',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('feature_key', sa.String, nullable=False),
        sa.Column('enabled', sa.Integer, default=1),
        sa.Column('role', sa.String, nullable=True),
        sa.Column('module', sa.String, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=True),
    )

def downgrade():
    if _table_exists('ia_feature_flags'):
        op.drop_table('ia_feature_flags')
