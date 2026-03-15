from __future__ import annotations

from enum import Enum


class StrEnumCompat(str, Enum):
    pass


class MetodoDepreciacion(StrEnumCompat):
    LINEA_RECTA = "linea_recta"
    SALDO_DECRECIENTE = "saldo_decreciente"


class EstadoActivo(StrEnumCompat):
    ACTIVO = "activo"
    ASIGNADO = "asignado"
    EN_MANTENIMIENTO = "en_mantenimiento"
    DADO_DE_BAJA = "dado_de_baja"


class EstadoAsignacion(StrEnumCompat):
    VIGENTE = "vigente"
    DEVUELTO = "devuelto"


class TipoMantenimiento(StrEnumCompat):
    PREVENTIVO = "preventivo"
    CORRECTIVO = "correctivo"
    REPARACION = "reparacion"


class EstadoMantenimiento(StrEnumCompat):
    PENDIENTE = "pendiente"
    EN_PROCESO = "en_proceso"
    COMPLETADO = "completado"


class MotivoBaja(StrEnumCompat):
    OBSOLESCENCIA = "obsolescencia"
    DANO = "dano"
    VENTA = "venta"
    ROBO = "robo"
    DONACION = "donacion"
    OTRO = "otro"
