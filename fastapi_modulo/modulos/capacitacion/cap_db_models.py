"""Modelos SQLAlchemy — Módulo de Capacitación."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey,
    Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from fastapi_modulo.db import Base


class CapCategoria(Base):
    __tablename__ = "cap_categoria"

    id          = Column(Integer, primary_key=True, index=True)
    nombre      = Column(String(100), nullable=False, unique=True, index=True)
    descripcion = Column(Text,        nullable=True)
    color       = Column(String(30),  nullable=True)
    creado_en   = Column(DateTime,    nullable=True, default=datetime.utcnow)

    cursos = relationship("CapCurso", back_populates="categoria")


class CapCurso(Base):
    __tablename__ = "cap_curso"

    id                 = Column(Integer,     primary_key=True, index=True)
    codigo             = Column(String(30),  nullable=True,  unique=True, index=True)
    nombre             = Column(String(200), nullable=False)
    descripcion        = Column(Text,        nullable=True)
    objetivo           = Column(Text,        nullable=True)
    categoria_id       = Column(Integer,     ForeignKey("cap_categoria.id", ondelete="SET NULL"), nullable=True, index=True)
    nivel              = Column(String(30),  nullable=False, default="basico")
    # basico | intermedio | avanzado
    estado             = Column(String(30),  nullable=False, default="borrador", index=True)
    # borrador | publicado | archivado
    responsable        = Column(String(150), nullable=True)
    duracion_horas     = Column(Float,       nullable=True)
    puntaje_aprobacion = Column(Float,       nullable=False, default=70.0)
    imagen_url         = Column(String(400), nullable=True)
    fecha_inicio       = Column(Date,        nullable=True)
    fecha_fin          = Column(Date,        nullable=True)
    es_obligatorio     = Column(Boolean,     nullable=False, default=False)
    creado_en          = Column(DateTime,    nullable=True, default=datetime.utcnow)
    actualizado_en     = Column(DateTime,    nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)

    categoria     = relationship("CapCategoria",    back_populates="cursos")
    lecciones     = relationship("CapLeccion",      back_populates="curso", cascade="all, delete-orphan", order_by="CapLeccion.orden")
    inscripciones = relationship("CapInscripcion",  back_populates="curso", cascade="all, delete-orphan")
    evaluaciones  = relationship("CapEvaluacion",   back_populates="curso", cascade="all, delete-orphan")


class CapLeccion(Base):
    __tablename__ = "cap_leccion"

    id           = Column(Integer,     primary_key=True, index=True)
    curso_id     = Column(Integer,     ForeignKey("cap_curso.id", ondelete="CASCADE"), nullable=False, index=True)
    titulo       = Column(String(200), nullable=False)
    tipo         = Column(String(30),  nullable=False, default="texto")
    # texto | video | documento | enlace
    contenido    = Column(Text,        nullable=True)
    url_archivo  = Column(String(400), nullable=True)
    duracion_min = Column(Integer,     nullable=True)
    orden        = Column(Integer,     nullable=False, default=0)
    es_obligatoria = Column(Boolean,   nullable=False, default=True)
    creado_en    = Column(DateTime,    nullable=True, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_cap_leccion_orden", "curso_id", "orden"),
    )

    curso    = relationship("CapCurso", back_populates="lecciones")
    progresos = relationship("CapProgresoLeccion", back_populates="leccion", cascade="all, delete-orphan")


class CapInscripcion(Base):
    __tablename__ = "cap_inscripcion"

    id                  = Column(Integer,     primary_key=True, index=True)
    colaborador_key     = Column(String(100), nullable=False, index=True)
    colaborador_nombre  = Column(String(200), nullable=True)
    departamento        = Column(String(150), nullable=True)
    curso_id            = Column(Integer,     ForeignKey("cap_curso.id", ondelete="CASCADE"), nullable=False, index=True)
    estado              = Column(String(30),  nullable=False, default="pendiente", index=True)
    # pendiente | en_progreso | completado | reprobado
    pct_avance          = Column(Float,       nullable=False, default=0.0)
    puntaje_final       = Column(Float,       nullable=True)
    aprobado            = Column(Boolean,     nullable=True)
    fecha_inscripcion   = Column(DateTime,    nullable=True, default=datetime.utcnow)
    fecha_inicio_real   = Column(DateTime,    nullable=True)
    fecha_completado    = Column(DateTime,    nullable=True)
    creado_en           = Column(DateTime,    nullable=True, default=datetime.utcnow)
    actualizado_en      = Column(DateTime,    nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("colaborador_key", "curso_id", name="uq_cap_inscripcion_colab_curso"),
    )

    curso      = relationship("CapCurso",             back_populates="inscripciones")
    progresos  = relationship("CapProgresoLeccion",   back_populates="inscripcion",  cascade="all, delete-orphan")
    intentos   = relationship("CapIntentoEvaluacion", back_populates="inscripcion",  cascade="all, delete-orphan")
    certificado = relationship("CapCertificado",      back_populates="inscripcion",  uselist=False, cascade="all, delete-orphan")


class CapProgresoLeccion(Base):
    __tablename__ = "cap_progreso_leccion"

    id               = Column(Integer,  primary_key=True, index=True)
    inscripcion_id   = Column(Integer,  ForeignKey("cap_inscripcion.id", ondelete="CASCADE"), nullable=False, index=True)
    leccion_id       = Column(Integer,  ForeignKey("cap_leccion.id",    ondelete="CASCADE"), nullable=False, index=True)
    completada       = Column(Boolean,  nullable=False, default=False)
    intentos         = Column(Integer,  nullable=False, default=0)
    tiempo_seg       = Column(Integer,  nullable=True)
    fecha_completado = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("inscripcion_id", "leccion_id", name="uq_cap_progreso_insc_lecc"),
    )

    inscripcion = relationship("CapInscripcion", back_populates="progresos")
    leccion     = relationship("CapLeccion",     back_populates="progresos")


class CapEvaluacion(Base):
    __tablename__ = "cap_evaluacion"

    id                    = Column(Integer,     primary_key=True, index=True)
    curso_id              = Column(Integer,     ForeignKey("cap_curso.id", ondelete="CASCADE"), nullable=False, index=True)
    titulo                = Column(String(200), nullable=False)
    instrucciones         = Column(Text,        nullable=True)
    puntaje_minimo        = Column(Float,       nullable=False, default=70.0)
    max_intentos          = Column(Integer,     nullable=False, default=3)
    preguntas_por_intento = Column(Integer,     nullable=True)
    tiempo_limite_min     = Column(Integer,     nullable=True)
    creado_en             = Column(DateTime,    nullable=True, default=datetime.utcnow)

    curso     = relationship("CapCurso",             back_populates="evaluaciones")
    preguntas = relationship("CapPregunta",           back_populates="evaluacion", cascade="all, delete-orphan", order_by="CapPregunta.orden")
    intentos  = relationship("CapIntentoEvaluacion", back_populates="evaluacion",  cascade="all, delete-orphan")


class CapPregunta(Base):
    __tablename__ = "cap_pregunta"

    id            = Column(Integer,    primary_key=True, index=True)
    evaluacion_id = Column(Integer,    ForeignKey("cap_evaluacion.id", ondelete="CASCADE"), nullable=False, index=True)
    enunciado     = Column(Text,       nullable=False)
    tipo          = Column(String(30), nullable=False, default="opcion_multiple")
    # opcion_multiple | verdadero_falso | texto_libre
    explicacion   = Column(Text,       nullable=True)
    puntaje       = Column(Float,      nullable=False, default=1.0)
    orden         = Column(Integer,    nullable=False, default=0)

    evaluacion = relationship("CapEvaluacion", back_populates="preguntas")
    opciones   = relationship("CapOpcion",     back_populates="pregunta", cascade="all, delete-orphan", order_by="CapOpcion.orden")


class CapOpcion(Base):
    __tablename__ = "cap_opcion"

    id          = Column(Integer,  primary_key=True, index=True)
    pregunta_id = Column(Integer,  ForeignKey("cap_pregunta.id", ondelete="CASCADE"), nullable=False, index=True)
    texto       = Column(Text,     nullable=False)
    es_correcta = Column(Boolean,  nullable=False, default=False)
    orden       = Column(Integer,  nullable=False, default=0)

    pregunta = relationship("CapPregunta", back_populates="opciones")


class CapIntentoEvaluacion(Base):
    __tablename__ = "cap_intento_evaluacion"

    id              = Column(Integer,  primary_key=True, index=True)
    inscripcion_id  = Column(Integer,  ForeignKey("cap_inscripcion.id", ondelete="CASCADE"), nullable=False, index=True)
    evaluacion_id   = Column(Integer,  ForeignKey("cap_evaluacion.id", ondelete="CASCADE"), nullable=False, index=True)
    numero_intento  = Column(Integer,  nullable=False, default=1)
    puntaje         = Column(Float,    nullable=True)
    puntaje_maximo  = Column(Float,    nullable=True)
    aprobado        = Column(Boolean,  nullable=True)
    respuestas_json = Column(Text,     nullable=True)   # JSON {pregunta_id: opcion_id|texto}
    fecha_inicio    = Column(DateTime, nullable=True)
    fecha_fin       = Column(DateTime, nullable=True)

    inscripcion = relationship("CapInscripcion", back_populates="intentos")
    evaluacion  = relationship("CapEvaluacion",  back_populates="intentos")


class CapCertificado(Base):
    __tablename__ = "cap_certificado"

    id             = Column(Integer,     primary_key=True, index=True)
    inscripcion_id = Column(Integer,     ForeignKey("cap_inscripcion.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    folio          = Column(String(50),  nullable=False, unique=True, index=True)
    puntaje_final  = Column(Float,       nullable=True)
    fecha_emision  = Column(DateTime,    nullable=True, default=datetime.utcnow)
    url_pdf        = Column(String(400), nullable=True)

    inscripcion = relationship("CapInscripcion", back_populates="certificado")


# ── Gamificación ────────────────────────────────────────────────────────────────

class CapPuntosLog(Base):
    __tablename__ = "cap_puntos_log"

    id              = Column(Integer,     primary_key=True, index=True)
    colaborador_key = Column(String(100), nullable=False, index=True)
    puntos          = Column(Integer,     nullable=False, default=0)
    motivo          = Column(String(100), nullable=False, index=True)
    referencia_tipo = Column(String(50),  nullable=True)
    referencia_id   = Column(Integer,     nullable=True)
    fecha           = Column(DateTime,    nullable=True, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "colaborador_key", "motivo", "referencia_tipo", "referencia_id",
            name="uq_cap_puntos_motivo_ref",
        ),
    )


class CapInsignia(Base):
    __tablename__ = "cap_insignia"

    id              = Column(Integer,    primary_key=True, index=True)
    nombre          = Column(String(100), nullable=False, unique=True)
    descripcion     = Column(Text,        nullable=True)
    icono_emoji     = Column(String(10),  nullable=True)
    condicion_tipo  = Column(String(50),  nullable=False)
    # lecciones_completadas | cursos_completados | certificados_obtenidos | puntaje_perfecto
    condicion_valor = Column(Integer,     nullable=False, default=1)
    color           = Column(String(30),  nullable=True)
    orden           = Column(Integer,     nullable=False, default=0)

    obtenidas = relationship("CapColaboradorInsignia", back_populates="insignia", cascade="all, delete-orphan")


class CapColaboradorInsignia(Base):
    __tablename__ = "cap_colaborador_insignia"

    id              = Column(Integer,     primary_key=True, index=True)
    colaborador_key = Column(String(100), nullable=False, index=True)
    insignia_id     = Column(Integer,     ForeignKey("cap_insignia.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha_obtencion = Column(DateTime,    nullable=True, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("colaborador_key", "insignia_id", name="uq_cap_colab_insignia"),
    )

    insignia = relationship("CapInsignia", back_populates="obtenidas")


# ── Presentaciones tipo Genially ────────────────────────────────────────────────

class CapPresentacion(Base):
    __tablename__ = "cap_presentacion"

    id             = Column(Integer,     primary_key=True, index=True)
    titulo         = Column(String(200), nullable=False)
    descripcion    = Column(Text,        nullable=True)
    autor_key      = Column(String(100), nullable=True, index=True)
    estado         = Column(String(30),  nullable=False, default="borrador", index=True)
    # borrador | publicado
    curso_id       = Column(Integer,     ForeignKey("cap_curso.id", ondelete="SET NULL"), nullable=True, index=True)
    miniatura_url  = Column(String(400), nullable=True)
    creado_en      = Column(DateTime,    nullable=True, default=datetime.utcnow)
    actualizado_en = Column(DateTime,    nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)

    diapositivas = relationship("CapDiapositiva", back_populates="presentacion",
                                cascade="all, delete-orphan", order_by="CapDiapositiva.orden")


class CapDiapositiva(Base):
    __tablename__ = "cap_diapositiva"

    id               = Column(Integer,     primary_key=True, index=True)
    presentacion_id  = Column(Integer,     ForeignKey("cap_presentacion.id", ondelete="CASCADE"), nullable=False, index=True)
    orden            = Column(Integer,     nullable=False, default=0)
    titulo           = Column(String(200), nullable=True)
    bg_color         = Column(String(30),  nullable=True, default="#ffffff")
    bg_image_url     = Column(String(400), nullable=True)
    notas            = Column(Text,        nullable=True)
    creado_en        = Column(DateTime,    nullable=True, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_cap_diap_pres_orden", "presentacion_id", "orden"),
    )

    presentacion = relationship("CapPresentacion", back_populates="diapositivas")
    elementos    = relationship("CapElemento", back_populates="diapositiva",
                                cascade="all, delete-orphan", order_by="CapElemento.z_index")


class CapElemento(Base):
    __tablename__ = "cap_elemento"

    id             = Column(Integer,  primary_key=True, index=True)
    diapositiva_id = Column(Integer,  ForeignKey("cap_diapositiva.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo           = Column(String(30), nullable=False)
    # texto | imagen | boton | forma | embed
    contenido_json = Column(Text,     nullable=True)
    pos_x          = Column(Float,    nullable=False, default=10.0)
    pos_y          = Column(Float,    nullable=False, default=10.0)
    width          = Column(Float,    nullable=False, default=30.0)
    height         = Column(Float,    nullable=False, default=20.0)
    z_index        = Column(Integer,  nullable=False, default=1)
    creado_en      = Column(DateTime, nullable=True, default=datetime.utcnow)

    diapositiva = relationship("CapDiapositiva", back_populates="elementos")
