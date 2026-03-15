"""Modelos SQLAlchemy — Módulo de Capacitación."""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Float, ForeignKey,
    Enum as SAEnum, Index, Integer, String, Text, UniqueConstraint, text,
)
from sqlalchemy.orm import relationship

from fastapi_modulo.db import MAIN, engine
from fastapi_modulo.modulos.capacitacion.modelos.enums import (
    EstadoCurso,
    EstadoInscripcion,
    EstadoPresentacion,
    NivelCurso,
    TipoLeccion,
    TipoPregunta,
)


class CapCategoria(MAIN):
    __tablename__ = "cap_categoria"

    tenant_id   = Column(String(100), nullable=False, default="default", index=True)
    id          = Column(Integer, primary_key=True, index=True)
    nombre      = Column(String(100), nullable=False, index=True)
    descripcion = Column(Text,        nullable=True)
    color       = Column(String(30),  nullable=True)
    creado_en   = Column(DateTime,    nullable=True, default=datetime.utcnow)

    cursos = relationship("CapCurso", back_populates="categoria")


class CapCurso(MAIN):
    __tablename__ = "cap_curso"

    tenant_id           = Column(String(100), nullable=False, default="default", index=True)
    id                 = Column(Integer,     primary_key=True, index=True)
    codigo             = Column(String(30),  nullable=True, index=True)
    nombre             = Column(String(200), nullable=False)
    descripcion        = Column(Text,        nullable=True)
    objetivo           = Column(Text,        nullable=True)
    categoria_id       = Column(Integer,     ForeignKey("cap_categoria.id", ondelete="SET NULL"), nullable=True, index=True)
    nivel              = Column(SAEnum(NivelCurso), nullable=False, default=NivelCurso.BASICO)
    estado             = Column(SAEnum(EstadoCurso), nullable=False, default=EstadoCurso.BORRADOR, index=True)
    responsable        = Column(String(150), nullable=True)
    duracion_horas     = Column(Float,       nullable=True)
    puntaje_aprobacion = Column(Float,       nullable=False, default=70.0)
    imagen_url         = Column(String(400), nullable=True)
    fecha_inicio       = Column(Date,        nullable=True)
    fecha_fin          = Column(Date,        nullable=True)
    es_obligatorio     = Column(Boolean,     nullable=False, default=False)
    vence_dias         = Column(Integer,     nullable=True)
    recordatorio_dias  = Column(Integer,     nullable=True, default=7)
    reinscripcion_automatica = Column(Boolean, nullable=False, default=False)
    prerrequisitos_json = Column(Text,       nullable=True)
    departamentos_json = Column(Text,        nullable=True)
    rol_objetivo       = Column(String(100), nullable=True, index=True)
    puesto_objetivo    = Column(String(150), nullable=True, index=True)
    bloquear_certificado_encuesta = Column(Boolean, nullable=False, default=False)
    requiere_encuesta_satisfaccion = Column(Boolean, nullable=False, default=False)
    version_numero     = Column(Integer,     nullable=False, default=1)
    version_padre_id   = Column(Integer,     ForeignKey("cap_curso.id", ondelete="SET NULL"), nullable=True, index=True)
    version_actual     = Column(Boolean,     nullable=False, default=True)
    creado_por         = Column(String(100), nullable=True, index=True)
    actualizado_por    = Column(String(100), nullable=True, index=True)
    publicado_por      = Column(String(100), nullable=True, index=True)
    publicado_en       = Column(DateTime,    nullable=True)
    creado_en          = Column(DateTime,    nullable=True, default=datetime.utcnow)
    actualizado_en     = Column(DateTime,    nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)

    categoria     = relationship("CapCategoria",    back_populates="cursos")
    lecciones     = relationship("CapLeccion",      back_populates="curso", cascade="all, delete-orphan", order_by="CapLeccion.orden")
    inscripciones = relationship("CapInscripcion",  back_populates="curso", cascade="all, delete-orphan")
    evaluaciones  = relationship("CapEvaluacion",   back_populates="curso", cascade="all, delete-orphan")
    versiones     = relationship("CapCurso", remote_side=[id])


class CapLeccion(MAIN):
    __tablename__ = "cap_leccion"

    tenant_id     = Column(String(100), nullable=False, default="default", index=True)
    id           = Column(Integer,     primary_key=True, index=True)
    curso_id     = Column(Integer,     ForeignKey("cap_curso.id", ondelete="CASCADE"), nullable=False, index=True)
    titulo       = Column(String(200), nullable=False)
    tipo         = Column(SAEnum(TipoLeccion), nullable=False, default=TipoLeccion.TEXTO)
    contenido    = Column(Text,        nullable=True)
    url_archivo  = Column(String(400), nullable=True)
    duracion_min = Column(Integer,     nullable=True)
    orden        = Column(Integer,     nullable=False, default=0)
    es_obligatoria = Column(Boolean,   nullable=False, default=True)
    creado_en    = Column(DateTime,    nullable=True, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "curso_id", "orden", name="uq_cap_leccion_tenant_curso_orden"),
        Index("ix_cap_leccion_orden", "curso_id", "orden"),
    )

    curso    = relationship("CapCurso", back_populates="lecciones")
    progresos = relationship("CapProgresoLeccion", back_populates="leccion", cascade="all, delete-orphan")


class CapInscripcion(MAIN):
    __tablename__ = "cap_inscripcion"

    tenant_id            = Column(String(100), nullable=False, default="default", index=True)
    id                  = Column(Integer,     primary_key=True, index=True)
    colaborador_key     = Column(String(100), nullable=False, index=True)
    colaborador_nombre  = Column(String(200), nullable=True)
    departamento        = Column(String(150), nullable=True)
    rol                 = Column(String(100), nullable=True, index=True)
    puesto              = Column(String(150), nullable=True, index=True)
    curso_id            = Column(Integer,     ForeignKey("cap_curso.id", ondelete="CASCADE"), nullable=False, index=True)
    estado              = Column(SAEnum(EstadoInscripcion), nullable=False, default=EstadoInscripcion.PENDIENTE, index=True)
    pct_avance          = Column(Float,       nullable=False, default=0.0)
    puntaje_final       = Column(Float,       nullable=True)
    aprobado            = Column(Boolean,     nullable=True)
    fecha_inscripcion   = Column(DateTime,    nullable=True, default=datetime.utcnow)
    fecha_inicio_real   = Column(DateTime,    nullable=True)
    fecha_completado    = Column(DateTime,    nullable=True)
    fecha_vencimiento   = Column(DateTime,    nullable=True, index=True)
    recordatorio_enviado_en = Column(DateTime, nullable=True)
    origen_regla        = Column(String(120), nullable=True)
    creado_en           = Column(DateTime,    nullable=True, default=datetime.utcnow)
    actualizado_en      = Column(DateTime,    nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "colaborador_key", "curso_id", name="uq_cap_inscripcion_colab_curso_tenant"),
    )

    curso      = relationship("CapCurso",             back_populates="inscripciones")
    progresos  = relationship("CapProgresoLeccion",   back_populates="inscripcion",  cascade="all, delete-orphan")
    intentos   = relationship("CapIntentoEvaluacion", back_populates="inscripcion",  cascade="all, delete-orphan")
    certificado = relationship("CapCertificado",      back_populates="inscripcion",  uselist=False, cascade="all, delete-orphan")
    satisfaccion = relationship("CapEncuestaSatisfaccion", back_populates="inscripcion", uselist=False, cascade="all, delete-orphan")


class CapProgresoLeccion(MAIN):
    __tablename__ = "cap_progreso_leccion"

    tenant_id         = Column(String(100), nullable=False, default="default", index=True)
    id               = Column(Integer,  primary_key=True, index=True)
    inscripcion_id   = Column(Integer,  ForeignKey("cap_inscripcion.id", ondelete="CASCADE"), nullable=False, index=True)
    leccion_id       = Column(Integer,  ForeignKey("cap_leccion.id",    ondelete="CASCADE"), nullable=False, index=True)
    completada       = Column(Boolean,  nullable=False, default=False)
    intentos         = Column(Integer,  nullable=False, default=0)
    tiempo_seg       = Column(Integer,  nullable=True)
    fecha_completado = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "inscripcion_id", "leccion_id", name="uq_cap_progreso_insc_lecc_tenant"),
    )

    inscripcion = relationship("CapInscripcion", back_populates="progresos")
    leccion     = relationship("CapLeccion",     back_populates="progresos")


class CapEvaluacion(MAIN):
    __tablename__ = "cap_evaluacion"

    tenant_id              = Column(String(100), nullable=False, default="default", index=True)
    id                    = Column(Integer,     primary_key=True, index=True)
    curso_id              = Column(Integer,     ForeignKey("cap_curso.id", ondelete="CASCADE"), nullable=False, index=True)
    titulo                = Column(String(200), nullable=False)
    instrucciones         = Column(Text,        nullable=True)
    puntaje_minimo        = Column(Float,       nullable=False, default=70.0)
    max_intentos          = Column(Integer,     nullable=False, default=3)
    preguntas_por_intento = Column(Integer,     nullable=True)
    tiempo_limite_min     = Column(Integer,     nullable=True)
    creado_por            = Column(String(100), nullable=True, index=True)
    actualizado_por       = Column(String(100), nullable=True, index=True)
    publicado_por         = Column(String(100), nullable=True, index=True)
    publicado_en          = Column(DateTime,    nullable=True)
    creado_en             = Column(DateTime,    nullable=True, default=datetime.utcnow)

    curso     = relationship("CapCurso",             back_populates="evaluaciones")
    preguntas = relationship("CapPregunta",           back_populates="evaluacion", cascade="all, delete-orphan", order_by="CapPregunta.orden")
    intentos  = relationship("CapIntentoEvaluacion", back_populates="evaluacion",  cascade="all, delete-orphan")


class CapPregunta(MAIN):
    __tablename__ = "cap_pregunta"

    tenant_id      = Column(String(100), nullable=False, default="default", index=True)
    id            = Column(Integer,    primary_key=True, index=True)
    evaluacion_id = Column(Integer,    ForeignKey("cap_evaluacion.id", ondelete="CASCADE"), nullable=False, index=True)
    enunciado     = Column(Text,       nullable=False)
    tipo          = Column(SAEnum(TipoPregunta), nullable=False, default=TipoPregunta.OPCION_MULTIPLE)
    explicacion   = Column(Text,       nullable=True)
    puntaje       = Column(Float,      nullable=False, default=1.0)
    orden         = Column(Integer,    nullable=False, default=0)

    evaluacion = relationship("CapEvaluacion", back_populates="preguntas")
    opciones   = relationship("CapOpcion",     back_populates="pregunta", cascade="all, delete-orphan", order_by="CapOpcion.orden")


class CapOpcion(MAIN):
    __tablename__ = "cap_opcion"

    tenant_id   = Column(String(100), nullable=False, default="default", index=True)
    id          = Column(Integer,  primary_key=True, index=True)
    pregunta_id = Column(Integer,  ForeignKey("cap_pregunta.id", ondelete="CASCADE"), nullable=False, index=True)
    texto       = Column(Text,     nullable=False)
    es_correcta = Column(Boolean,  nullable=False, default=False)
    orden       = Column(Integer,  nullable=False, default=0)

    pregunta = relationship("CapPregunta", back_populates="opciones")


class CapIntentoEvaluacion(MAIN):
    __tablename__ = "cap_intento_evaluacion"

    tenant_id        = Column(String(100), nullable=False, default="default", index=True)
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


class CapCertificado(MAIN):
    __tablename__ = "cap_certificado"

    tenant_id       = Column(String(100), nullable=False, default="default", index=True)
    id             = Column(Integer,     primary_key=True, index=True)
    inscripcion_id = Column(Integer,     ForeignKey("cap_inscripcion.id", ondelete="CASCADE"), nullable=False, index=True)
    folio          = Column(String(50),  nullable=False, index=True)
    puntaje_final  = Column(Float,       nullable=True)
    creado_por     = Column(String(100), nullable=True, index=True)
    fecha_emision  = Column(DateTime,    nullable=True, default=datetime.utcnow)
    url_pdf        = Column(String(400), nullable=True)

    inscripcion = relationship("CapInscripcion", back_populates="certificado")


class CapRutaAprendizaje(MAIN):
    __tablename__ = "cap_ruta_aprendizaje"

    tenant_id      = Column(String(100), nullable=False, default="default", index=True)
    id             = Column(Integer, primary_key=True, index=True)
    nombre         = Column(String(200), nullable=False)
    descripcion    = Column(Text, nullable=True)
    rol_objetivo   = Column(String(100), nullable=True, index=True)
    puesto_objetivo = Column(String(150), nullable=True, index=True)
    departamentos_json = Column(Text, nullable=True)
    creada_en      = Column(DateTime, nullable=True, default=datetime.utcnow)

    cursos = relationship("CapRutaCurso", back_populates="ruta", cascade="all, delete-orphan", order_by="CapRutaCurso.orden")


class CapRutaCurso(MAIN):
    __tablename__ = "cap_ruta_curso"

    tenant_id      = Column(String(100), nullable=False, default="default", index=True)
    id             = Column(Integer, primary_key=True, index=True)
    ruta_id        = Column(Integer, ForeignKey("cap_ruta_aprendizaje.id", ondelete="CASCADE"), nullable=False, index=True)
    curso_id       = Column(Integer, ForeignKey("cap_curso.id", ondelete="CASCADE"), nullable=False, index=True)
    orden          = Column(Integer, nullable=False, default=0)
    obligatorio    = Column(Boolean, nullable=False, default=True)

    ruta = relationship("CapRutaAprendizaje", back_populates="cursos")


class CapEncuestaSatisfaccion(MAIN):
    __tablename__ = "cap_encuesta_satisfaccion"

    tenant_id      = Column(String(100), nullable=False, default="default", index=True)
    id             = Column(Integer, primary_key=True, index=True)
    inscripcion_id = Column(Integer, ForeignKey("cap_inscripcion.id", ondelete="CASCADE"), nullable=False, index=True)
    calificacion   = Column(Integer, nullable=False, default=5)
    comentario     = Column(Text, nullable=True)
    respondida_en  = Column(DateTime, nullable=True, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "inscripcion_id", name="uq_cap_satisfaccion_inscripcion_tenant"),
    )

    inscripcion = relationship("CapInscripcion", back_populates="satisfaccion")


# ── Gamificación ────────────────────────────────────────────────────────────────

class CapPuntosLog(MAIN):
    __tablename__ = "cap_puntos_log"

    tenant_id       = Column(String(100), nullable=False, default="default", index=True)
    id              = Column(Integer,     primary_key=True, index=True)
    colaborador_key = Column(String(100), nullable=False, index=True)
    puntos          = Column(Integer,     nullable=False, default=0)
    motivo          = Column(String(100), nullable=False, index=True)
    referencia_tipo = Column(String(50),  nullable=True)
    referencia_id   = Column(Integer,     nullable=True)
    fecha           = Column(DateTime,    nullable=True, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "colaborador_key", "motivo", "referencia_tipo", "referencia_id",
            name="uq_cap_puntos_motivo_ref_tenant",
        ),
    )


class CapInsignia(MAIN):
    __tablename__ = "cap_insignia"

    tenant_id        = Column(String(100), nullable=False, default="default", index=True)
    id              = Column(Integer,    primary_key=True, index=True)
    nombre          = Column(String(100), nullable=False)
    descripcion     = Column(Text,        nullable=True)
    icono_emoji     = Column(String(10),  nullable=True)
    condicion_tipo  = Column(String(50),  nullable=False)
    # lecciones_completadas | cursos_completados | certificados_obtenidos | puntaje_perfecto
    condicion_valor = Column(Integer,     nullable=False, default=1)
    color           = Column(String(30),  nullable=True)
    orden           = Column(Integer,     nullable=False, default=0)

    obtenidas = relationship("CapColaboradorInsignia", back_populates="insignia", cascade="all, delete-orphan")


class CapColaboradorInsignia(MAIN):
    __tablename__ = "cap_colaborador_insignia"

    tenant_id       = Column(String(100), nullable=False, default="default", index=True)
    id              = Column(Integer,     primary_key=True, index=True)
    colaborador_key = Column(String(100), nullable=False, index=True)
    insignia_id     = Column(Integer,     ForeignKey("cap_insignia.id", ondelete="CASCADE"), nullable=False, index=True)
    fecha_obtencion = Column(DateTime,    nullable=True, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("tenant_id", "colaborador_key", "insignia_id", name="uq_cap_colab_insignia_tenant"),
    )

    insignia = relationship("CapInsignia", back_populates="obtenidas")


# ── Presentaciones tipo Genially ────────────────────────────────────────────────

class CapPresentacion(MAIN):
    __tablename__ = "cap_presentacion"

    tenant_id       = Column(String(100), nullable=False, default="default", index=True)
    id             = Column(Integer,     primary_key=True, index=True)
    titulo         = Column(String(200), nullable=False)
    descripcion    = Column(Text,        nullable=True)
    autor_key      = Column(String(100), nullable=True, index=True)
    template_key   = Column(String(100), nullable=True, index=True)
    theme_key      = Column(String(100), nullable=True, index=True)
    responsive_mode = Column(String(30), nullable=True, default="desktop")
    autosave_json  = Column(Text,        nullable=True)
    estado         = Column(SAEnum(EstadoPresentacion), nullable=False, default=EstadoPresentacion.BORRADOR, index=True)
    curso_id       = Column(Integer,     ForeignKey("cap_curso.id", ondelete="SET NULL"), nullable=True, index=True)
    miniatura_url  = Column(String(400), nullable=True)
    creado_por     = Column(String(100), nullable=True, index=True)
    actualizado_por = Column(String(100), nullable=True, index=True)
    publicado_por  = Column(String(100), nullable=True, index=True)
    publicado_en   = Column(DateTime,    nullable=True)
    creado_en      = Column(DateTime,    nullable=True, default=datetime.utcnow)
    actualizado_en = Column(DateTime,    nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow)

    diapositivas = relationship("CapDiapositiva", back_populates="presentacion",
                                cascade="all, delete-orphan", order_by="CapDiapositiva.orden")
    versiones = relationship("CapPresentacionVersion", back_populates="presentacion",
                             cascade="all, delete-orphan", order_by="CapPresentacionVersion.creado_en")
    assets = relationship("CapAssetBiblioteca", back_populates="presentacion", cascade="all, delete-orphan")


class CapDiapositiva(MAIN):
    __tablename__ = "cap_diapositiva"

    tenant_id         = Column(String(100), nullable=False, default="default", index=True)
    id               = Column(Integer,     primary_key=True, index=True)
    presentacion_id  = Column(Integer,     ForeignKey("cap_presentacion.id", ondelete="CASCADE"), nullable=False, index=True)
    orden            = Column(Integer,     nullable=False, default=0)
    titulo           = Column(String(200), nullable=True)
    layout_key       = Column(String(100), nullable=True, index=True)
    transition_key   = Column(String(100), nullable=True)
    animation_json   = Column(Text,        nullable=True)
    responsive_json  = Column(Text,        nullable=True)
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


class CapElemento(MAIN):
    __tablename__ = "cap_elemento"

    tenant_id     = Column(String(100), nullable=False, default="default", index=True)
    id             = Column(Integer,  primary_key=True, index=True)
    diapositiva_id = Column(Integer,  ForeignKey("cap_diapositiva.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo           = Column(String(30), nullable=False)
    # texto | imagen | boton | forma | embed
    contenido_json = Column(Text,     nullable=True)
    asset_id       = Column(Integer,  ForeignKey("cap_asset_biblioteca.id", ondelete="SET NULL"), nullable=True, index=True)
    animation_json = Column(Text,     nullable=True)
    hotspot_key    = Column(String(100), nullable=True, index=True)
    pos_x          = Column(Float,    nullable=False, default=10.0)
    pos_y          = Column(Float,    nullable=False, default=10.0)
    width          = Column(Float,    nullable=False, default=30.0)
    height         = Column(Float,    nullable=False, default=20.0)
    z_index        = Column(Integer,  nullable=False, default=1)
    creado_en      = Column(DateTime, nullable=True, default=datetime.utcnow)

    diapositiva = relationship("CapDiapositiva", back_populates="elementos")
    asset = relationship("CapAssetBiblioteca", back_populates="elementos")


class CapPresentacionVersion(MAIN):
    __tablename__ = "cap_presentacion_version"

    tenant_id       = Column(String(100), nullable=False, default="default", index=True)
    id              = Column(Integer, primary_key=True, index=True)
    presentacion_id = Column(Integer, ForeignKey("cap_presentacion.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo            = Column(String(30), nullable=False, default="snapshot", index=True)
    etiqueta        = Column(String(120), nullable=True)
    contenido_json  = Column(Text, nullable=True)
    actor_key       = Column(String(100), nullable=True, index=True)
    creado_en       = Column(DateTime, nullable=True, default=datetime.utcnow, index=True)

    presentacion = relationship("CapPresentacion", back_populates="versiones")


class CapAssetBiblioteca(MAIN):
    __tablename__ = "cap_asset_biblioteca"

    tenant_id       = Column(String(100), nullable=False, default="default", index=True)
    id              = Column(Integer, primary_key=True, index=True)
    presentacion_id = Column(Integer, ForeignKey("cap_presentacion.id", ondelete="CASCADE"), nullable=True, index=True)
    nombre          = Column(String(200), nullable=False)
    tipo            = Column(String(50), nullable=False, default="imagen", index=True)
    url             = Column(String(500), nullable=False)
    thumb_url       = Column(String(500), nullable=True)
    tags_json       = Column(Text, nullable=True)
    metadata_json   = Column(Text, nullable=True)
    creado_por      = Column(String(100), nullable=True, index=True)
    creado_en       = Column(DateTime, nullable=True, default=datetime.utcnow)

    presentacion = relationship("CapPresentacion", back_populates="assets")
    elementos = relationship("CapElemento", back_populates="asset")


class CapArchivo(MAIN):
    __tablename__ = "cap_archivo"

    tenant_id      = Column(String(100), nullable=False, default="default", index=True)
    id             = Column(Integer, primary_key=True, index=True)
    entidad_tipo   = Column(String(50), nullable=True, index=True)
    entidad_id     = Column(Integer, nullable=True, index=True)
    categoria      = Column(String(50), nullable=False, index=True)
    nombre_original = Column(String(255), nullable=False)
    nombre_archivo = Column(String(255), nullable=False, index=True)
    ruta_relativa  = Column(String(500), nullable=False)
    public_url     = Column(String(500), nullable=False)
    mime_type      = Column(String(120), nullable=True)
    size_bytes     = Column(Integer, nullable=True)
    creado_por     = Column(String(100), nullable=True, index=True)
    metadata_json  = Column(Text, nullable=True)
    creado_en      = Column(DateTime, nullable=True, default=datetime.utcnow, index=True)


class CapEventoEntidad(MAIN):
    __tablename__ = "cap_evento_entidad"

    tenant_id     = Column(String(100), nullable=False, default="default", index=True)
    id            = Column(Integer, primary_key=True, index=True)
    entidad_tipo  = Column(String(50), nullable=False, index=True)
    entidad_id    = Column(Integer, nullable=False, index=True)
    accion        = Column(String(50), nullable=False, index=True)
    actor_key     = Column(String(100), nullable=True, index=True)
    actor_nombre  = Column(String(200), nullable=True)
    detalle_json  = Column(Text, nullable=True)
    creado_en     = Column(DateTime, nullable=True, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("ix_cap_evento_entidad_lookup", "tenant_id", "entidad_tipo", "entidad_id", "creado_en"),
    )


def ensure_capacitacion_tenant_schema() -> None:
    MAIN.metadata.create_all(bind=engine, checkfirst=True)
    statements = [
        "ALTER TABLE cap_categoria ADD COLUMN tenant_id VARCHAR(100) NOT NULL DEFAULT 'default'",
        "ALTER TABLE cap_curso ADD COLUMN tenant_id VARCHAR(100) NOT NULL DEFAULT 'default'",
        "ALTER TABLE cap_leccion ADD COLUMN tenant_id VARCHAR(100) NOT NULL DEFAULT 'default'",
        "ALTER TABLE cap_inscripcion ADD COLUMN tenant_id VARCHAR(100) NOT NULL DEFAULT 'default'",
        "ALTER TABLE cap_progreso_leccion ADD COLUMN tenant_id VARCHAR(100) NOT NULL DEFAULT 'default'",
        "ALTER TABLE cap_evaluacion ADD COLUMN tenant_id VARCHAR(100) NOT NULL DEFAULT 'default'",
        "ALTER TABLE cap_pregunta ADD COLUMN tenant_id VARCHAR(100) NOT NULL DEFAULT 'default'",
        "ALTER TABLE cap_opcion ADD COLUMN tenant_id VARCHAR(100) NOT NULL DEFAULT 'default'",
        "ALTER TABLE cap_intento_evaluacion ADD COLUMN tenant_id VARCHAR(100) NOT NULL DEFAULT 'default'",
        "ALTER TABLE cap_certificado ADD COLUMN tenant_id VARCHAR(100) NOT NULL DEFAULT 'default'",
        "ALTER TABLE cap_curso ADD COLUMN vence_dias INTEGER",
        "ALTER TABLE cap_curso ADD COLUMN recordatorio_dias INTEGER DEFAULT 7",
        "ALTER TABLE cap_curso ADD COLUMN reinscripcion_automatica BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE cap_curso ADD COLUMN prerrequisitos_json TEXT",
        "ALTER TABLE cap_curso ADD COLUMN departamentos_json TEXT",
        "ALTER TABLE cap_curso ADD COLUMN rol_objetivo VARCHAR(100)",
        "ALTER TABLE cap_curso ADD COLUMN puesto_objetivo VARCHAR(150)",
        "ALTER TABLE cap_curso ADD COLUMN bloquear_certificado_encuesta BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE cap_curso ADD COLUMN requiere_encuesta_satisfaccion BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE cap_curso ADD COLUMN version_numero INTEGER NOT NULL DEFAULT 1",
        "ALTER TABLE cap_curso ADD COLUMN version_padre_id INTEGER",
        "ALTER TABLE cap_curso ADD COLUMN version_actual BOOLEAN NOT NULL DEFAULT 1",
        "ALTER TABLE cap_inscripcion ADD COLUMN rol VARCHAR(100)",
        "ALTER TABLE cap_inscripcion ADD COLUMN puesto VARCHAR(150)",
        "ALTER TABLE cap_inscripcion ADD COLUMN fecha_vencimiento DATETIME",
        "ALTER TABLE cap_inscripcion ADD COLUMN recordatorio_enviado_en DATETIME",
        "ALTER TABLE cap_inscripcion ADD COLUMN origen_regla VARCHAR(120)",
        "ALTER TABLE cap_puntos_log ADD COLUMN tenant_id VARCHAR(100) NOT NULL DEFAULT 'default'",
        "ALTER TABLE cap_insignia ADD COLUMN tenant_id VARCHAR(100) NOT NULL DEFAULT 'default'",
        "ALTER TABLE cap_colaborador_insignia ADD COLUMN tenant_id VARCHAR(100) NOT NULL DEFAULT 'default'",
        "ALTER TABLE cap_presentacion ADD COLUMN tenant_id VARCHAR(100) NOT NULL DEFAULT 'default'",
        "ALTER TABLE cap_diapositiva ADD COLUMN tenant_id VARCHAR(100) NOT NULL DEFAULT 'default'",
        "ALTER TABLE cap_elemento ADD COLUMN tenant_id VARCHAR(100) NOT NULL DEFAULT 'default'",
        "ALTER TABLE cap_curso ADD COLUMN creado_por VARCHAR(100)",
        "ALTER TABLE cap_curso ADD COLUMN actualizado_por VARCHAR(100)",
        "ALTER TABLE cap_curso ADD COLUMN publicado_por VARCHAR(100)",
        "ALTER TABLE cap_curso ADD COLUMN publicado_en DATETIME",
        "ALTER TABLE cap_presentacion ADD COLUMN creado_por VARCHAR(100)",
        "ALTER TABLE cap_presentacion ADD COLUMN actualizado_por VARCHAR(100)",
        "ALTER TABLE cap_presentacion ADD COLUMN publicado_por VARCHAR(100)",
        "ALTER TABLE cap_presentacion ADD COLUMN publicado_en DATETIME",
        "ALTER TABLE cap_presentacion ADD COLUMN template_key VARCHAR(100)",
        "ALTER TABLE cap_presentacion ADD COLUMN theme_key VARCHAR(100)",
        "ALTER TABLE cap_presentacion ADD COLUMN responsive_mode VARCHAR(30) DEFAULT 'desktop'",
        "ALTER TABLE cap_presentacion ADD COLUMN autosave_json TEXT",
        "ALTER TABLE cap_diapositiva ADD COLUMN layout_key VARCHAR(100)",
        "ALTER TABLE cap_diapositiva ADD COLUMN transition_key VARCHAR(100)",
        "ALTER TABLE cap_diapositiva ADD COLUMN animation_json TEXT",
        "ALTER TABLE cap_diapositiva ADD COLUMN responsive_json TEXT",
        "ALTER TABLE cap_elemento ADD COLUMN asset_id INTEGER",
        "ALTER TABLE cap_elemento ADD COLUMN animation_json TEXT",
        "ALTER TABLE cap_elemento ADD COLUMN hotspot_key VARCHAR(100)",
        "ALTER TABLE cap_archivo ADD COLUMN tenant_id VARCHAR(100) NOT NULL DEFAULT 'default'",
        "ALTER TABLE cap_evaluacion ADD COLUMN creado_por VARCHAR(100)",
        "ALTER TABLE cap_evaluacion ADD COLUMN actualizado_por VARCHAR(100)",
        "ALTER TABLE cap_evaluacion ADD COLUMN publicado_por VARCHAR(100)",
        "ALTER TABLE cap_evaluacion ADD COLUMN publicado_en DATETIME",
        "ALTER TABLE cap_certificado ADD COLUMN creado_por VARCHAR(100)",
    ]
    with engine.begin() as conn:
        try:
            CapEventoEntidad.__table__.create(bind=conn, checkfirst=True)
        except Exception:
            pass
        for table in [CapRutaAprendizaje.__table__, CapRutaCurso.__table__, CapEncuestaSatisfaccion.__table__, CapPresentacionVersion.__table__, CapAssetBiblioteca.__table__, CapArchivo.__table__]:
            try:
                table.create(bind=conn, checkfirst=True)
            except Exception:
                pass
        for stmt in statements:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass
        for stmt in [
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_cap_categoria_tenant_nombre_idx ON cap_categoria(tenant_id, nombre)",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_cap_curso_tenant_codigo_idx ON cap_curso(tenant_id, codigo)",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_cap_inscripcion_colab_curso_tenant_idx ON cap_inscripcion(tenant_id, colaborador_key, curso_id)",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_cap_cert_folio_tenant_idx ON cap_certificado(tenant_id, folio)",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_cap_colab_insignia_tenant_idx ON cap_colaborador_insignia(tenant_id, colaborador_key, insignia_id)",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_cap_puntos_motivo_ref_tenant_idx ON cap_puntos_log(tenant_id, colaborador_key, motivo, referencia_tipo, referencia_id)",
        ]:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass
    __table_args__ = (
        UniqueConstraint("tenant_id", "nombre", name="uq_cap_categoria_tenant_nombre"),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "codigo", name="uq_cap_curso_tenant_codigo"),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "inscripcion_id", name="uq_cap_cert_inscripcion_tenant"),
        UniqueConstraint("tenant_id", "folio", name="uq_cap_cert_folio_tenant"),
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "nombre", name="uq_cap_insignia_tenant_nombre"),
    )
