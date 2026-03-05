"""
Revision para agregar la tabla ia_interactions para auditoría de IA
Revision ID: 20260301_add_ia_interactions_table
Revises: 
Create Date: 2026-03-01
"""

# revision identifiers, used by Alembic.
revision = '20260301_add_ia_interactions_table'
down_revision = None
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'ia_interactions',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('user_id', sa.String, nullable=True),
        sa.Column('username', sa.String, nullable=True),
        sa.Column('feature_key', sa.String, nullable=True),
        sa.Column('input_payload', sa.String, nullable=True),
        sa.Column('output_payload', sa.String, nullable=True),
        sa.Column('model_name', sa.String, nullable=True),
        sa.Column('tokens_in', sa.Integer, default=0),
        sa.Column('tokens_out', sa.Integer, default=0),
        sa.Column('estimated_cost', sa.String, default="0"),
        sa.Column('status', sa.String, default="pending"),
        sa.Column('error_message', sa.String, default=""),
    )

def downgrade():
    op.drop_table('ia_interactions')
