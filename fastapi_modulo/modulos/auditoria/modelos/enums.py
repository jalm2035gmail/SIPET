from enum import Enum

class TipoAuditoria(str, Enum):
    INTERNA = "interna"
    EXTERNA = "externa"
    ESPECIAL = "especial"
    COMPLIANCE = "compliance"

class EstadoAuditoria(str, Enum):
    PLANIFICADA = "planificada"
    EN_PROCESO = "en_proceso"
    INFORME = "informe"
    CERRADA = "cerrada"

class NivelRiesgo(str, Enum):
    BAJO = "bajo"
    MEDIO = "medio"
    ALTO = "alto"
    CRITICO = "critico"

class EstadoHallazgo(str, Enum):
    ABIERTO = "abierto"
    EN_ATENCION = "en_atencion"
    IMPLEMENTADO = "implementado"
    VERIFICADO = "verificado"
    CERRADO = "cerrado"

class PrioridadRecomendacion(str, Enum):
    ALTA = "alta"
    MEDIA = "media"
    BAJA = "baja"

class EstadoRecomendacion(str, Enum):
    PENDIENTE = "pendiente"
    EN_PROCESO = "en_proceso"
    IMPLEMENTADA = "implementada"
    RECHAZADA = "rechazada"

class FaseAuditoria(str, Enum):
    PLANIFICACION = "planificacion"
    EJECUCION = "ejecucion"
    HALLAZGOS = "hallazgos"
    RECOMENDACIONES = "recomendaciones"
    PLAN_ACCION = "plan_accion"
    SEGUIMIENTO = "seguimiento"
    CIERRE = "cierre"
    VERIFICACION = "verificacion"
