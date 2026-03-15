from __future__ import annotations

from enum import Enum


class EstadoCredito(str, Enum):
    VIGENTE = "vigente"
    EN_MORA = "en_mora"
    REESTRUCTURADO = "reestructurado"
    CASTIGADO = "castigado"
    CANCELADO = "cancelado"


class BucketMora(str, Enum):
    CORRIENTE = "corriente"
    MORA_1_8 = "1_8"
    MORA_9_30 = "9_30"
    MORA_31_60 = "31_60"
    MORA_61_90 = "61_90"
    MORA_MAS_90 = "90_plus"


class NivelRiesgo(str, Enum):
    BAJO = "bajo"
    MEDIO = "medio"
    ALTO = "alto"
    CRITICO = "critico"


class TipoGestionCobranza(str, Enum):
    LLAMADA = "llamada"
    WHATSAPP = "whatsapp"
    CORREO = "correo"
    VISITA = "visita"
    COMITE = "comite"
    REFINANCIACION = "refinanciacion"


class ResultadoGestion(str, Enum):
    SIN_CONTACTO = "sin_contacto"
    PROMESA_PAGO = "promesa_pago"
    PAGO_PARCIAL = "pago_parcial"
    PAGO_TOTAL = "pago_total"
    NEGOCIACION = "negociacion"
    ESCALADO = "escalado"


class EstadoPromesaPago(str, Enum):
    PENDIENTE = "pendiente"
    CUMPLIDA = "cumplida"
    INCUMPLIDA = "incumplida"
    VENCIDA = "vencida"


class TipoIndicador(str, Enum):
    MORA = "mora"
    RECUPERACION = "recuperacion"
    CASTIGO = "castigo"
    PROMESAS = "promesas"
    RIESGO = "riesgo"
    EFECTIVIDAD = "efectividad"


__all__ = [
    "BucketMora",
    "EstadoCredito",
    "EstadoPromesaPago",
    "NivelRiesgo",
    "ResultadoGestion",
    "TipoGestionCobranza",
    "TipoIndicador",
]
