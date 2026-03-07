"""
Agregar tabla control_interno (Fase 1 — catálogo de controles)
Revision ID: 20260305_add_control_interno_table
Revises: 20260301_add_ia_feature_flags_table, 20260301_add_ia_interactions_table, 8d6c7410e0b7
Create Date: 2026-03-05
"""

revision = '20260305_add_control_interno_table'
down_revision = ('20260301_add_ia_feature_flags_table', '20260301_add_ia_interactions_table', '8d6c7410e0b7')
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'control_interno',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('codigo', sa.String(30), nullable=False, unique=True, index=True),
        sa.Column('nombre', sa.String(200), nullable=False),
        sa.Column('componente', sa.String(50), nullable=False),
        sa.Column('area', sa.String(100), nullable=False),
        sa.Column('tipo_riesgo', sa.String(100), nullable=True),
        sa.Column('periodicidad', sa.String(30), nullable=False, server_default='Mensual'),
        sa.Column('descripcion', sa.Text, nullable=True),
        sa.Column('normativa', sa.String(200), nullable=True),
        sa.Column('estado', sa.String(30), nullable=False, server_default='Activo'),
        sa.Column('creado_en', sa.DateTime, nullable=False),
        sa.Column('actualizado_en', sa.DateTime, nullable=False),
    )


def downgrade():
    op.drop_table('control_interno')
