"""Alembic migration: Módulo de Capacitación — tablas MAIN.

Revision ID: 20260309_add_capacitacion_tables
Revises: 20260305_add_ci_hallazgos_tables
Create Date: 2026-03-09
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260309_add_capacitacion_tables"
down_revision = "20260305_add_ci_hallazgos_tables"
branch_labels = None
depends_on = None


def upgrade():
    # ── Categorías ────────────────────────────────────────────────────────────
    op.create_table(
        "cap_categoria",
        sa.Column("id",          sa.Integer,      primary_key=True),
        sa.Column("nombre",      sa.String(100),  nullable=False, unique=True),
        sa.Column("descripcion", sa.Text,         nullable=True),
        sa.Column("color",       sa.String(30),   nullable=True),
        sa.Column("creado_en",   sa.DateTime,     nullable=True),
    )
    op.create_index("ix_cap_categoria_nombre", "cap_categoria", ["nombre"])

    # ── Cursos ─────────────────────────────────────────────────────────────────
    op.create_table(
        "cap_curso",
        sa.Column("id",                  sa.Integer,      primary_key=True),
        sa.Column("codigo",              sa.String(30),   nullable=True,  unique=True),
        sa.Column("nombre",              sa.String(200),  nullable=False),
        sa.Column("descripcion",         sa.Text,         nullable=True),
        sa.Column("objetivo",            sa.Text,         nullable=True),
        sa.Column("categoria_id",        sa.Integer,
                  sa.ForeignKey("cap_categoria.id", ondelete="SET NULL"), nullable=True),
        sa.Column("nivel",               sa.String(30),   nullable=False, server_default="basico"),
        # basico | intermedio | avanzado
        sa.Column("estado",              sa.String(30),   nullable=False, server_default="borrador"),
        # borrador | publicado | archivado
        sa.Column("responsable",         sa.String(150),  nullable=True),
        sa.Column("duracion_horas",      sa.Float,        nullable=True),
        sa.Column("puntaje_aprobacion",  sa.Float,        nullable=False, server_default="70"),
        sa.Column("imagen_url",          sa.String(400),  nullable=True),
        sa.Column("fecha_inicio",        sa.Date,         nullable=True),
        sa.Column("fecha_fin",           sa.Date,         nullable=True),
        sa.Column("es_obligatorio",      sa.Boolean,      nullable=False, server_default="0"),
        sa.Column("creado_en",           sa.DateTime,     nullable=True),
        sa.Column("actualizado_en",      sa.DateTime,     nullable=True),
    )
    op.create_index("ix_cap_curso_categoria_id", "cap_curso", ["categoria_id"])
    op.create_index("ix_cap_curso_estado",       "cap_curso", ["estado"])

    # ── Lecciones ──────────────────────────────────────────────────────────────
    op.create_table(
        "cap_leccion",
        sa.Column("id",              sa.Integer,      primary_key=True),
        sa.Column("curso_id",        sa.Integer,
                  sa.ForeignKey("cap_curso.id", ondelete="CASCADE"), nullable=False),
        sa.Column("titulo",          sa.String(200),  nullable=False),
        sa.Column("tipo",            sa.String(30),   nullable=False, server_default="texto"),
        # texto | video | documento | enlace
        sa.Column("contenido",       sa.Text,         nullable=True),  # texto HTML o URL
        sa.Column("url_archivo",     sa.String(400),  nullable=True),
        sa.Column("duracion_min",    sa.Integer,      nullable=True),
        sa.Column("orden",           sa.Integer,      nullable=False, server_default="0"),
        sa.Column("es_obligatoria",  sa.Boolean,      nullable=False, server_default="1"),
        sa.Column("creado_en",       sa.DateTime,     nullable=True),
    )
    op.create_index("ix_cap_leccion_curso_id", "cap_leccion", ["curso_id"])
    op.create_index("ix_cap_leccion_orden",    "cap_leccion", ["curso_id", "orden"])

    # ── Inscripciones ──────────────────────────────────────────────────────────
    op.create_table(
        "cap_inscripcion",
        sa.Column("id",                  sa.Integer,      primary_key=True),
        sa.Column("colaborador_key",     sa.String(100),  nullable=False),  # clave del colaborador en el store
        sa.Column("colaborador_nombre",  sa.String(200),  nullable=True),
        sa.Column("departamento",        sa.String(150),  nullable=True),
        sa.Column("curso_id",            sa.Integer,
                  sa.ForeignKey("cap_curso.id", ondelete="CASCADE"), nullable=False),
        sa.Column("estado",              sa.String(30),   nullable=False, server_default="pendiente"),
        # pendiente | en_progreso | completado | reprobado
        sa.Column("pct_avance",          sa.Float,        nullable=False, server_default="0"),
        sa.Column("puntaje_final",       sa.Float,        nullable=True),
        sa.Column("aprobado",            sa.Boolean,      nullable=True),
        sa.Column("fecha_inscripcion",   sa.DateTime,     nullable=True),
        sa.Column("fecha_inicio_real",   sa.DateTime,     nullable=True),
        sa.Column("fecha_completado",    sa.DateTime,     nullable=True),
        sa.Column("creado_en",           sa.DateTime,     nullable=True),
        sa.Column("actualizado_en",      sa.DateTime,     nullable=True),
    )
    op.create_index("ix_cap_inscripcion_colaborador", "cap_inscripcion", ["colaborador_key"])
    op.create_index("ix_cap_inscripcion_curso_id",    "cap_inscripcion", ["curso_id"])
    op.create_index("ix_cap_inscripcion_estado",      "cap_inscripcion", ["estado"])
    # Restricción: un colaborador no se inscribe dos veces al mismo curso
    op.create_index(
        "uq_cap_inscripcion_colab_curso",
        "cap_inscripcion",
        ["colaborador_key", "curso_id"],
        unique=True,
    )

    # ── Progreso por lección ───────────────────────────────────────────────────
    op.create_table(
        "cap_progreso_leccion",
        sa.Column("id",               sa.Integer,   primary_key=True),
        sa.Column("inscripcion_id",   sa.Integer,
                  sa.ForeignKey("cap_inscripcion.id", ondelete="CASCADE"), nullable=False),
        sa.Column("leccion_id",       sa.Integer,
                  sa.ForeignKey("cap_leccion.id",    ondelete="CASCADE"), nullable=False),
        sa.Column("completada",       sa.Boolean,   nullable=False, server_default="0"),
        sa.Column("intentos",         sa.Integer,   nullable=False, server_default="0"),
        sa.Column("tiempo_seg",       sa.Integer,   nullable=True),  # segundos en la lección
        sa.Column("fecha_completado", sa.DateTime,  nullable=True),
    )
    op.create_index("ix_cap_progreso_inscripcion_id", "cap_progreso_leccion", ["inscripcion_id"])
    op.create_index("ix_cap_progreso_leccion_id",     "cap_progreso_leccion", ["leccion_id"])
    op.create_index(
        "uq_cap_progreso_insc_lecc",
        "cap_progreso_leccion",
        ["inscripcion_id", "leccion_id"],
        unique=True,
    )

    # ── Evaluaciones ───────────────────────────────────────────────────────────
    op.create_table(
        "cap_evaluacion",
        sa.Column("id",                      sa.Integer,     primary_key=True),
        sa.Column("curso_id",                sa.Integer,
                  sa.ForeignKey("cap_curso.id", ondelete="CASCADE"), nullable=False),
        sa.Column("titulo",                  sa.String(200), nullable=False),
        sa.Column("instrucciones",           sa.Text,        nullable=True),
        sa.Column("puntaje_minimo",          sa.Float,       nullable=False, server_default="70"),
        sa.Column("max_intentos",            sa.Integer,     nullable=False, server_default="3"),
        sa.Column("preguntas_por_intento",   sa.Integer,     nullable=True),  # None = todas
        sa.Column("tiempo_limite_min",       sa.Integer,     nullable=True),
        sa.Column("creado_en",               sa.DateTime,    nullable=True),
    )
    op.create_index("ix_cap_evaluacion_curso_id", "cap_evaluacion", ["curso_id"])

    # ── Preguntas ──────────────────────────────────────────────────────────────
    op.create_table(
        "cap_pregunta",
        sa.Column("id",              sa.Integer,     primary_key=True),
        sa.Column("evaluacion_id",   sa.Integer,
                  sa.ForeignKey("cap_evaluacion.id", ondelete="CASCADE"), nullable=False),
        sa.Column("enunciado",       sa.Text,        nullable=False),
        sa.Column("tipo",            sa.String(30),  nullable=False, server_default="opcion_multiple"),
        # opcion_multiple | verdadero_falso | texto_libre
        sa.Column("explicacion",     sa.Text,        nullable=True),  # retroalimentación
        sa.Column("puntaje",         sa.Float,       nullable=False, server_default="1"),
        sa.Column("orden",           sa.Integer,     nullable=False, server_default="0"),
    )
    op.create_index("ix_cap_pregunta_evaluacion_id", "cap_pregunta", ["evaluacion_id"])

    # ── Opciones de respuesta ──────────────────────────────────────────────────
    op.create_table(
        "cap_opcion",
        sa.Column("id",           sa.Integer,     primary_key=True),
        sa.Column("pregunta_id",  sa.Integer,
                  sa.ForeignKey("cap_pregunta.id", ondelete="CASCADE"), nullable=False),
        sa.Column("texto",        sa.Text,        nullable=False),
        sa.Column("es_correcta",  sa.Boolean,     nullable=False, server_default="0"),
        sa.Column("orden",        sa.Integer,     nullable=False, server_default="0"),
    )
    op.create_index("ix_cap_opcion_pregunta_id", "cap_opcion", ["pregunta_id"])

    # ── Intentos de evaluación ─────────────────────────────────────────────────
    op.create_table(
        "cap_intento_evaluacion",
        sa.Column("id",              sa.Integer,   primary_key=True),
        sa.Column("inscripcion_id",  sa.Integer,
                  sa.ForeignKey("cap_inscripcion.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evaluacion_id",   sa.Integer,
                  sa.ForeignKey("cap_evaluacion.id", ondelete="CASCADE"), nullable=False),
        sa.Column("numero_intento",  sa.Integer,   nullable=False, server_default="1"),
        sa.Column("puntaje",         sa.Float,     nullable=True),
        sa.Column("puntaje_maximo",  sa.Float,     nullable=True),
        sa.Column("aprobado",        sa.Boolean,   nullable=True),
        sa.Column("respuestas_json", sa.Text,      nullable=True),  # JSON {pregunta_id: opcion_id}
        sa.Column("fecha_inicio",    sa.DateTime,  nullable=True),
        sa.Column("fecha_fin",       sa.DateTime,  nullable=True),
    )
    op.create_index("ix_cap_intento_inscripcion_id", "cap_intento_evaluacion", ["inscripcion_id"])
    op.create_index("ix_cap_intento_evaluacion_id",  "cap_intento_evaluacion", ["evaluacion_id"])

    # ── Certificados ───────────────────────────────────────────────────────────
    op.create_table(
        "cap_certificado",
        sa.Column("id",               sa.Integer,     primary_key=True),
        sa.Column("inscripcion_id",   sa.Integer,
                  sa.ForeignKey("cap_inscripcion.id", ondelete="CASCADE"),
                  nullable=False, unique=True),
        sa.Column("folio",            sa.String(50),  nullable=False, unique=True),
        sa.Column("puntaje_final",    sa.Float,       nullable=True),
        sa.Column("fecha_emision",    sa.DateTime,    nullable=True),
        sa.Column("url_pdf",          sa.String(400), nullable=True),
    )
    op.create_index("ix_cap_certificado_folio",          "cap_certificado", ["folio"])
    op.create_index("ix_cap_certificado_inscripcion_id", "cap_certificado", ["inscripcion_id"])


def downgrade():
    op.drop_table("cap_certificado")
    op.drop_table("cap_intento_evaluacion")
    op.drop_table("cap_opcion")
    op.drop_table("cap_pregunta")
    op.drop_table("cap_evaluacion")
    op.drop_table("cap_progreso_leccion")
    op.drop_table("cap_inscripcion")
    op.drop_table("cap_leccion")
    op.drop_table("cap_curso")
    op.drop_table("cap_categoria")
