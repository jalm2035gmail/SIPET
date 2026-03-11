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


def _has_table(bind, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _has_index(bind, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(idx.get("name") == index_name for idx in inspector.get_indexes(table_name))


def _has_unique(bind, table_name: str, constraint_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(cst.get("name") == constraint_name for cst in inspector.get_unique_constraints(table_name))


def _has_index_or_unique(bind, table_name: str, name: str) -> bool:
    return _has_index(bind, table_name, name) or _has_unique(bind, table_name, name)


def upgrade() -> None:
    bind = op.get_bind()
    # ── cap_puntos_log ──────────────────────────────────────────────────
    if not _has_table(bind, "cap_puntos_log"):
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
    if not _has_index(bind, "cap_puntos_log", "ix_cap_puntos_log_colab"):
        op.create_index("ix_cap_puntos_log_colab", "cap_puntos_log", ["colaborador_key"])
    if not _has_index(bind, "cap_puntos_log", "ix_cap_puntos_log_motivo"):
        op.create_index("ix_cap_puntos_log_motivo", "cap_puntos_log", ["motivo"])
    if not _has_index_or_unique(bind, "cap_puntos_log", "uq_cap_puntos_motivo_ref"):
        op.create_index(
            "uq_cap_puntos_motivo_ref",
            "cap_puntos_log",
            ["colaborador_key", "motivo", "referencia_tipo", "referencia_id"],
            unique=True,
        )

    # ── cap_insignia ────────────────────────────────────────────────────
    if not _has_table(bind, "cap_insignia"):
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
    if not _has_table(bind, "cap_colaborador_insignia"):
        op.create_table(
            "cap_colaborador_insignia",
            sa.Column("id",              sa.Integer(),    primary_key=True),
            sa.Column("colaborador_key", sa.String(100),  nullable=False),
            sa.Column("insignia_id",     sa.Integer(),    sa.ForeignKey("cap_insignia.id", ondelete="CASCADE"), nullable=False),
            sa.Column("fecha_obtencion", sa.DateTime(),   nullable=True),
        )
    if not _has_index(bind, "cap_colaborador_insignia", "ix_cap_colab_insignia_colab"):
        op.create_index("ix_cap_colab_insignia_colab", "cap_colaborador_insignia", ["colaborador_key"])
    if not _has_index_or_unique(bind, "cap_colaborador_insignia", "uq_cap_colab_insignia"):
        op.create_index(
            "uq_cap_colab_insignia",
            "cap_colaborador_insignia",
            ["colaborador_key", "insignia_id"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    if _has_index(bind, "cap_colaborador_insignia", "uq_cap_colab_insignia"):
        op.drop_index("uq_cap_colab_insignia", table_name="cap_colaborador_insignia")
    if _has_index(bind, "cap_colaborador_insignia", "ix_cap_colab_insignia_colab"):
        op.drop_index("ix_cap_colab_insignia_colab", table_name="cap_colaborador_insignia")
    op.drop_table("cap_colaborador_insignia")
    op.drop_table("cap_insignia")
    if _has_index(bind, "cap_puntos_log", "uq_cap_puntos_motivo_ref"):
        op.drop_index("uq_cap_puntos_motivo_ref", table_name="cap_puntos_log")
    if _has_index(bind, "cap_puntos_log", "ix_cap_puntos_log_motivo"):
        op.drop_index("ix_cap_puntos_log_motivo", table_name="cap_puntos_log")
    if _has_index(bind, "cap_puntos_log", "ix_cap_puntos_log_colab"):
        op.drop_index("ix_cap_puntos_log_colab", table_name="cap_puntos_log")
    op.drop_table("cap_puntos_log")
