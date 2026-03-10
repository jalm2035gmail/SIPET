"""Alembic migration: Presentaciones tipo Genially — cap_presentacion, cap_diapositiva, cap_elemento.

Revision ID: 20260309_add_presentaciones_tables
Revises: 20260309_add_gamificacion_tables
Create Date: 2026-03-09
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260309_add_presentaciones_tables"
down_revision = "20260309_add_gamificacion_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cap_presentacion",
        sa.Column("id",             sa.Integer(),     primary_key=True),
        sa.Column("titulo",         sa.String(200),   nullable=False),
        sa.Column("descripcion",    sa.Text(),         nullable=True),
        sa.Column("autor_key",      sa.String(100),   nullable=True),
        sa.Column("estado",         sa.String(30),    nullable=False, server_default="borrador"),
        sa.Column("curso_id",       sa.Integer(),     sa.ForeignKey("cap_curso.id", ondelete="SET NULL"), nullable=True),
        sa.Column("miniatura_url",  sa.String(400),   nullable=True),
        sa.Column("creado_en",      sa.DateTime(),    nullable=True),
        sa.Column("actualizado_en", sa.DateTime(),    nullable=True),
    )
    op.create_index("ix_cap_pres_estado", "cap_presentacion", ["estado"])
    op.create_index("ix_cap_pres_autor",  "cap_presentacion", ["autor_key"])

    op.create_table(
        "cap_diapositiva",
        sa.Column("id",               sa.Integer(),    primary_key=True),
        sa.Column("presentacion_id",  sa.Integer(),    sa.ForeignKey("cap_presentacion.id", ondelete="CASCADE"), nullable=False),
        sa.Column("orden",            sa.Integer(),    nullable=False, server_default="0"),
        sa.Column("titulo",           sa.String(200),  nullable=True),
        sa.Column("bg_color",         sa.String(30),   nullable=True, server_default="#ffffff"),
        sa.Column("bg_image_url",     sa.String(400),  nullable=True),
        sa.Column("notas",            sa.Text(),        nullable=True),
        sa.Column("creado_en",        sa.DateTime(),   nullable=True),
    )
    op.create_index("ix_cap_diap_pres", "cap_diapositiva", ["presentacion_id", "orden"])

    op.create_table(
        "cap_elemento",
        sa.Column("id",              sa.Integer(),    primary_key=True),
        sa.Column("diapositiva_id",  sa.Integer(),    sa.ForeignKey("cap_diapositiva.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tipo",            sa.String(30),   nullable=False),
        sa.Column("contenido_json",  sa.Text(),       nullable=True),
        sa.Column("pos_x",          sa.Float(),      nullable=False, server_default="10"),
        sa.Column("pos_y",          sa.Float(),      nullable=False, server_default="10"),
        sa.Column("width",          sa.Float(),      nullable=False, server_default="30"),
        sa.Column("height",         sa.Float(),      nullable=False, server_default="20"),
        sa.Column("z_index",        sa.Integer(),    nullable=False, server_default="1"),
        sa.Column("creado_en",      sa.DateTime(),   nullable=True),
    )
    op.create_index("ix_cap_elem_diap", "cap_elemento", ["diapositiva_id"])


def downgrade() -> None:
    op.drop_table("cap_elemento")
    op.drop_table("cap_diapositiva")
    op.drop_table("cap_presentacion")
