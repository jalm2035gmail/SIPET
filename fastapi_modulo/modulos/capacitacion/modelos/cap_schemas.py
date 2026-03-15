"""Schemas Pydantic — Módulo de Capacitación."""
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

from fastapi_modulo.modulos.capacitacion.modelos.enums import (
    EstadoCurso,
    EstadoInscripcion,
    EstadoPresentacion,
    NivelCurso,
    TipoLeccion,
    TipoPregunta,
)


# ── Categoría ──────────────────────────────────────────────────────────────────

class CapCategoriaOut(BaseModel):
    id: int
    nombre: str
    descripcion: Optional[str] = None
    color: Optional[str] = None

    class Config:
        from_attributes = True


class CapCategoriaIn(BaseModel):
    nombre: str = Field(..., max_length=100)
    descripcion: Optional[str] = None
    color: Optional[str] = Field(None, max_length=30)


# ── Curso ──────────────────────────────────────────────────────────────────────

class CapCursoMAIN(BaseModel):
    nombre: str = Field(..., max_length=200)
    descripcion: Optional[str] = None
    objetivo: Optional[str] = None
    categoria_id: Optional[int] = None
    nivel: NivelCurso = NivelCurso.BASICO
    estado: EstadoCurso = EstadoCurso.BORRADOR
    responsable: Optional[str] = Field(None, max_length=150)
    duracion_horas: Optional[float] = Field(None, ge=0)
    puntaje_aprobacion: float = Field(70.0, ge=0, le=100)
    imagen_url: Optional[str] = Field(None, max_length=400)
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    es_obligatorio: bool = False

    @model_validator(mode="after")
    def validate_course_dates(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser menor que fecha_inicio")
        return self


class CapCursoIn(CapCursoMAIN):
    pass


class CapCursoOut(CapCursoMAIN):
    id: int
    codigo: Optional[str] = None
    creado_en: Optional[datetime] = None
    actualizado_en: Optional[datetime] = None
    total_lecciones: Optional[int] = None
    total_inscripciones: Optional[int] = None

    class Config:
        from_attributes = True


# ── Lección ────────────────────────────────────────────────────────────────────

class CapLeccionMAIN(BaseModel):
    titulo: str = Field(..., max_length=200)
    tipo: TipoLeccion = TipoLeccion.TEXTO
    contenido: Optional[str] = None
    url_archivo: Optional[str] = Field(None, max_length=400)
    duracion_min: Optional[int] = None
    orden: int = 0
    es_obligatoria: bool = True


class CapLeccionIn(CapLeccionMAIN):
    curso_id: int


class CapLeccionOut(CapLeccionMAIN):
    id: int
    curso_id: int
    creado_en: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Inscripción ────────────────────────────────────────────────────────────────

class CapInscripcionIn(BaseModel):
    colaborador_key: str = Field(..., max_length=100)
    colaborador_nombre: Optional[str] = Field(None, max_length=200)
    departamento: Optional[str] = Field(None, max_length=150)
    curso_id: int


class CapInscripcionOut(BaseModel):
    id: int
    colaborador_key: str
    colaborador_nombre: Optional[str] = None
    departamento: Optional[str] = None
    curso_id: int
    estado: EstadoInscripcion
    pct_avance: float
    puntaje_final: Optional[float] = None
    aprobado: Optional[bool] = None
    fecha_inscripcion: Optional[datetime] = None
    fecha_completado: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Progreso por lección ───────────────────────────────────────────────────────

class CapProgresoLeccionIn(BaseModel):
    inscripcion_id: int
    leccion_id: int
    tiempo_seg: Optional[int] = None


class CapProgresoLeccionOut(BaseModel):
    id: int
    inscripcion_id: int
    leccion_id: int
    completada: bool
    intentos: int
    tiempo_seg: Optional[int] = None
    fecha_completado: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Evaluación ─────────────────────────────────────────────────────────────────

class CapOpcionIn(BaseModel):
    texto: str
    es_correcta: bool = False
    orden: int = 0


class CapOpcionOut(CapOpcionIn):
    id: int
    pregunta_id: int

    class Config:
        from_attributes = True


class CapOpcionResultado(BaseModel):
    """Opción sin revelar si es correcta (para presentar al usuario)."""
    id: int
    texto: str
    orden: int

    class Config:
        from_attributes = True


class CapPreguntaIn(BaseModel):
    enunciado: str
    tipo: TipoPregunta = TipoPregunta.OPCION_MULTIPLE
    explicacion: Optional[str] = None
    puntaje: float = 1.0
    orden: int = 0
    opciones: List[CapOpcionIn] = []


class CapPreguntaOut(BaseModel):
    id: int
    evaluacion_id: int
    enunciado: str
    tipo: TipoPregunta
    explicacion: Optional[str] = None
    puntaje: float
    orden: int
    opciones: List[CapOpcionOut] = []

    class Config:
        from_attributes = True


class CapPreguntaParaUsuario(BaseModel):
    """Pregunta sin respuestas correctas marcadas."""
    id: int
    enunciado: str
    tipo: TipoPregunta
    puntaje: float
    orden: int
    opciones: List[CapOpcionResultado] = []

    class Config:
        from_attributes = True


class CapEvaluacionIn(BaseModel):
    curso_id: int
    titulo: str = Field(..., max_length=200)
    instrucciones: Optional[str] = None
    puntaje_minimo: float = Field(70.0, ge=0, le=100)
    max_intentos: int = Field(3, ge=1)
    preguntas_por_intento: Optional[int] = Field(None, ge=1)
    tiempo_limite_min: Optional[int] = None
    preguntas: List[CapPreguntaIn] = []


class CapEvaluacionOut(BaseModel):
    id: int
    curso_id: int
    titulo: str
    instrucciones: Optional[str] = None
    puntaje_minimo: float
    max_intentos: int
    preguntas_por_intento: Optional[int] = None
    tiempo_limite_min: Optional[int] = None
    total_preguntas: Optional[int] = None

    class Config:
        from_attributes = True


# ── Intento de evaluación ──────────────────────────────────────────────────────

class CapRespuestaIn(BaseModel):
    """Una respuesta del usuario a una pregunta."""
    pregunta_id: int
    opcion_id: Optional[int] = None       # para opcion_multiple / verdadero_falso
    texto_libre: Optional[str] = None     # para texto_libre


class CapIntentoEnviarIn(BaseModel):
    inscripcion_id: int
    evaluacion_id: int
    respuestas: List[CapRespuestaIn]


class CapIntentoOut(BaseModel):
    id: int
    inscripcion_id: int
    evaluacion_id: int
    numero_intento: int
    puntaje: Optional[float] = None
    puntaje_maximo: Optional[float] = None
    aprobado: Optional[bool] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None

    class Config:
        from_attributes = True


# ── Certificado ────────────────────────────────────────────────────────────────

class CapCertificadoOut(BaseModel):
    id: int
    inscripcion_id: int
    folio: str
    puntaje_final: Optional[float] = None
    fecha_emision: Optional[datetime] = None
    url_pdf: Optional[str] = None

    class Config:
        from_attributes = True


# ── Respuestas de API generales ────────────────────────────────────────────────

class CapRespuestaOK(BaseModel):
    success: bool = True
    message: Optional[str] = None


class CapRespuestaError(BaseModel):
    success: bool = False
    error: str
