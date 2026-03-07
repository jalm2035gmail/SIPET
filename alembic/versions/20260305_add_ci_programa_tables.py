"""Alembic migration: Fase 2 — Programa anual de control interno.

Revision ID: 20260305_add_ci_programa_tables
Revises: 20260305_add_control_interno_table
Create Date: 2026-03-05
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260305_add_ci_programa_tables"
down_revision = "20260305_add_control_interno_table"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ci_programa_anual",
        sa.Column("id",             sa.Integer,     primary_key=True),
        sa.Column("anio",           sa.Integer,     nullable=False),
        sa.Column("nombre",         sa.String(200), nullable=False),
        sa.Column("descripcion",    sa.Text,        nullable=True),
        sa.Column("estado",         sa.String(50),  nullable=False, server_default="Borrador"),
        sa.Column("creado_en",      sa.DateTime,    nullable=True),
        sa.Column("actualizado_en", sa.DateTime,    nullable=True),
    )
    op.create_index("ix_ci_programa_anual_anio", "ci_programa_anual", ["anio"])

    op.create_table(
        "ci_programa_actividad",
        sa.Column("id",                      sa.Integer,  primary_key=True),
        sa.Column("programa_id",             sa.Integer,
                  sa.ForeignKey("ci_programa_anual.id", ondelete="CASCADE"), nullable=False),
        sa.Column("control_id",              sa.Integer,
                  sa.ForeignKey("control_interno.id", ondelete="SET NULL"), nullable=True),
        sa.Column("descripcion",             sa.Text,        nullable=True),
        sa.Column("responsable",             sa.String(150), nullable=True),
        sa.Column("fecha_inicio_programada", sa.Date,        nullable=True),
        sa.Column("fecha_fin_programada",    sa.Date,        nullable=True),
        sa.Column("fecha_inicio_real",       sa.Date,        nullable=True),
        sa.Column("fecha_fin_real",          sa.Date,        nullable=True),
        sa.Column("estado",                  sa.String(50),  nullable=False, server_default="Programado"),
        sa.Column("observaciones",           sa.Text,        nullable=True),
        sa.Column("creado_en",               sa.DateTime,    nullable=True),
        sa.Column("actualizado_en",          sa.DateTime,    nullable=True),
    )
    op.create_index("ix_ci_programa_actividad_programa_id", "ci_programa_actividad", ["programa_id"])
    op.create_index("ix_ci_programa_actividad_control_id",  "ci_programa_actividad", ["control_id"])


def downgrade():
    op.drop_table("ci_programa_actividad")
    op.drop_table("ci_programa_anual")
