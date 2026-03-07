"""Alembic migration: Fase 4 — Hallazgos y acciones correctivas.

Revision ID: 20260305_add_ci_hallazgos_tables
Revises: 20260305_add_ci_evidencia_table
Create Date: 2026-03-05
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260305_add_ci_hallazgos_tables"
down_revision = "20260305_add_ci_evidencia_table"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ci_hallazgo",
        sa.Column("id",              sa.Integer,      primary_key=True),
        sa.Column("evidencia_id",    sa.Integer,
                  sa.ForeignKey("ci_evidencia.id",           ondelete="SET NULL"), nullable=True),
        sa.Column("actividad_id",    sa.Integer,
                  sa.ForeignKey("ci_programa_actividad.id",  ondelete="SET NULL"), nullable=True),
        sa.Column("control_id",      sa.Integer,
                  sa.ForeignKey("control_interno.id",        ondelete="SET NULL"), nullable=True),
        sa.Column("codigo",          sa.String(30),   nullable=True),
        sa.Column("titulo",          sa.String(200),  nullable=False),
        sa.Column("descripcion",     sa.Text,         nullable=True),
        sa.Column("causa",           sa.Text,         nullable=True),
        sa.Column("efecto",          sa.Text,         nullable=True),
        sa.Column("componente_coso", sa.String(100),  nullable=True),
        sa.Column("nivel_riesgo",    sa.String(30),   nullable=False, server_default="Medio"),
        sa.Column("estado",          sa.String(50),   nullable=False, server_default="Abierto"),
        sa.Column("fecha_deteccion", sa.Date,         nullable=True),
        sa.Column("fecha_limite",    sa.Date,         nullable=True),
        sa.Column("responsable",     sa.String(150),  nullable=True),
        sa.Column("creado_en",       sa.DateTime,     nullable=True),
        sa.Column("actualizado_en",  sa.DateTime,     nullable=True),
    )
    op.create_index("ix_ci_hallazgo_control_id",   "ci_hallazgo", ["control_id"])
    op.create_index("ix_ci_hallazgo_evidencia_id", "ci_hallazgo", ["evidencia_id"])
    op.create_index("ix_ci_hallazgo_actividad_id", "ci_hallazgo", ["actividad_id"])

    op.create_table(
        "ci_accion_correctiva",
        sa.Column("id",                    sa.Integer,     primary_key=True),
        sa.Column("hallazgo_id",           sa.Integer,
                  sa.ForeignKey("ci_hallazgo.id", ondelete="CASCADE"), nullable=False),
        sa.Column("descripcion",           sa.Text,        nullable=False),
        sa.Column("responsable",           sa.String(150), nullable=True),
        sa.Column("fecha_compromiso",      sa.Date,        nullable=True),
        sa.Column("fecha_ejecucion",       sa.Date,        nullable=True),
        sa.Column("estado",                sa.String(50),  nullable=False, server_default="Pendiente"),
        sa.Column("evidencia_seguimiento", sa.Text,        nullable=True),
        sa.Column("creado_en",             sa.DateTime,    nullable=True),
        sa.Column("actualizado_en",        sa.DateTime,    nullable=True),
    )
    op.create_index("ix_ci_accion_hallazgo_id", "ci_accion_correctiva", ["hallazgo_id"])


def downgrade():
    op.drop_table("ci_accion_correctiva")
    op.drop_table("ci_hallazgo")
