from enum import Enum


class NivelCurso(str, Enum):
    BASICO = "basico"
    INTERMEDIO = "intermedio"
    AVANZADO = "avanzado"


class EstadoCurso(str, Enum):
    BORRADOR = "borrador"
    PUBLICADO = "publicado"
    ARCHIVADO = "archivado"


class TipoLeccion(str, Enum):
    TEXTO = "texto"
    VIDEO = "video"
    DOCUMENTO = "documento"
    ENLACE = "enlace"


class EstadoInscripcion(str, Enum):
    PENDIENTE = "pendiente"
    EN_PROGRESO = "en_progreso"
    COMPLETADO = "completado"
    REPROBADO = "reprobado"


class TipoPregunta(str, Enum):
    OPCION_MULTIPLE = "opcion_multiple"
    VERDADERO_FALSO = "verdadero_falso"
    TEXTO_LIBRE = "texto_libre"


class EstadoPresentacion(str, Enum):
    BORRADOR = "borrador"
    PUBLICADO = "publicado"
