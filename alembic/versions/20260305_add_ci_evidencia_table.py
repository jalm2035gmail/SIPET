"""Alembic migration: Fase 3 — Evidencias de control interno.

Revision ID: 20260305_add_ci_evidencia_table
Revises: 20260305_add_ci_programa_tables
Create Date: 2026-03-05
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260305_add_ci_evidencia_table"
down_revision = "20260305_add_ci_programa_tables"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ci_evidencia",
        sa.Column("id",                   sa.Integer,      primary_key=True),
        sa.Column("actividad_id",         sa.Integer,
                  sa.ForeignKey("ci_programa_actividad.id", ondelete="SET NULL"), nullable=True),
        sa.Column("control_id",           sa.Integer,
                  sa.ForeignKey("control_interno.id",      ondelete="SET NULL"), nullable=True),
        sa.Column("titulo",               sa.String(200),  nullable=False),
        sa.Column("tipo",                 sa.String(50),   nullable=False, server_default="Documento"),
        sa.Column("descripcion",          sa.Text,         nullable=True),
        sa.Column("fecha_evidencia",      sa.Date,         nullable=True),
        sa.Column("resultado_evaluacion", sa.String(50),   nullable=False, server_default="Por evaluar"),
        sa.Column("observaciones",        sa.Text,         nullable=True),
        sa.Column("archivo_nombre",       sa.String(255),  nullable=True),
        sa.Column("archivo_ruta",         sa.String(500),  nullable=True),
        sa.Column("archivo_mime",         sa.String(100),  nullable=True),
        sa.Column("archivo_tamanio",      sa.BigInteger,   nullable=True),
        sa.Column("creado_en",            sa.DateTime,     nullable=True),
        sa.Column("actualizado_en",       sa.DateTime,     nullable=True),
    )
    op.create_index("ix_ci_evidencia_actividad_id", "ci_evidencia", ["actividad_id"])
    op.create_index("ix_ci_evidencia_control_id",   "ci_evidencia", ["control_id"])


def downgrade():
    op.drop_table("ci_evidencia")
