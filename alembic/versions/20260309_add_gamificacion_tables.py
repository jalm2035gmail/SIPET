"""Alembic migration: Gamificación — puntos, insignias, colaborador_insignia.

Revision ID: 20260309_add_gamificacion_tables
Revises: 20260309_add_capacitacion_tables
Create Date: 2026-03-09
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260309_add_gamificacion_tables"
down_revision = "20260309_add_capacitacion_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── cap_puntos_log ──────────────────────────────────────────────────
    op.create_table(
        "cap_puntos_log",
        sa.Column("id",              sa.Integer(),     primary_key=True),
        sa.Column("colaborador_key", sa.String(100),   nullable=False),
        sa.Column("puntos",          sa.Integer(),     nullable=False, server_default="0"),
        sa.Column("motivo",          sa.String(100),   nullable=False),
        sa.Column("referencia_tipo", sa.String(50),    nullable=True),
        sa.Column("referencia_id",   sa.Integer(),     nullable=True),
        sa.Column("fecha",           sa.DateTime(),    nullable=True),
    )
    op.create_index("ix_cap_puntos_log_colab", "cap_puntos_log", ["colaborador_key"])
    op.create_index("ix_cap_puntos_log_motivo", "cap_puntos_log", ["motivo"])
    # Unique: a single event only awarded once
    op.create_unique_constraint(
        "uq_cap_puntos_motivo_ref",
        "cap_puntos_log",
        ["colaborador_key", "motivo", "referencia_tipo", "referencia_id"],
    )

    # ── cap_insignia ────────────────────────────────────────────────────
    op.create_table(
        "cap_insignia",
        sa.Column("id",              sa.Integer(),    primary_key=True),
        sa.Column("nombre",          sa.String(100),  nullable=False, unique=True),
        sa.Column("descripcion",     sa.Text(),       nullable=True),
        sa.Column("icono_emoji",     sa.String(10),   nullable=True),
        sa.Column("condicion_tipo",  sa.String(50),   nullable=False),
        sa.Column("condicion_valor", sa.Integer(),    nullable=False, server_default="1"),
        sa.Column("color",           sa.String(30),   nullable=True),
        sa.Column("orden",           sa.Integer(),    nullable=False, server_default="0"),
    )

    # ── cap_colaborador_insignia ────────────────────────────────────────
    op.create_table(
        "cap_colaborador_insignia",
        sa.Column("id",              sa.Integer(),    primary_key=True),
        sa.Column("colaborador_key", sa.String(100),  nullable=False),
        sa.Column("insignia_id",     sa.Integer(),    sa.ForeignKey("cap_insignia.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fecha_obtencion", sa.DateTime(),   nullable=True),
    )
    op.create_index("ix_cap_colab_insignia_colab", "cap_colaborador_insignia", ["colaborador_key"])
    op.create_unique_constraint(
        "uq_cap_colab_insignia",
        "cap_colaborador_insignia",
        ["colaborador_key", "insignia_id"],
    )


def downgrade() -> None:
    op.drop_table("cap_colaborador_insignia")
    op.drop_table("cap_insignia")
    op.drop_table("cap_puntos_log")
