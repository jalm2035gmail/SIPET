from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Optional

from fastapi_modulo.modulos.activo_fijo.models import (
    AfActivo,
    AfAsignacion,
    AfBaja,
    AfDepreciacion,
    AfMantenimiento,
)


def dec_str(value) -> Optional[str]:
    if value is None:
        return None
    return str(Decimal(str(value)).quantize(Decimal("0.01")))


def date_str(value) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def activo_to_dict(obj: AfActivo) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "codigo": obj.codigo,
        "nombre": obj.nombre,
        "categoria": obj.categoria,
        "marca": obj.marca,
        "modelo": obj.modelo,
        "numero_serie": obj.numero_serie,
        "proveedor": obj.proveedor,
        "fecha_adquisicion": date_str(obj.fecha_adquisicion),
        "valor_adquisicion": dec_str(obj.valor_adquisicion),
        "valor_residual": dec_str(obj.valor_residual),
        "vida_util_meses": obj.vida_util_meses,
        "metodo_depreciacion": obj.metodo_depreciacion,
        "valor_libro": dec_str(
            obj.valor_libro if obj.valor_libro is not None else obj.valor_adquisicion
        ),
        "ubicacion": obj.ubicacion,
        "responsable": obj.responsable,
        "estado": obj.estado,
        "descripcion": obj.descripcion,
        "creado_en": date_str(obj.creado_en),
        "actualizado_en": date_str(obj.actualizado_en),
    }


def depreciacion_to_dict(obj: AfDepreciacion) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "activo_id": obj.activo_id,
        "activo_nombre": obj.activo.nombre if obj.activo else None,
        "activo_codigo": obj.activo.codigo if obj.activo else None,
        "periodo": obj.periodo,
        "metodo": obj.metodo,
        "valor_depreciacion": dec_str(obj.valor_depreciacion),
        "valor_libro_anterior": dec_str(obj.valor_libro_anterior),
        "valor_libro_nuevo": dec_str(obj.valor_libro_nuevo),
        "creado_en": date_str(obj.creado_en),
    }


def asignacion_to_dict(obj: AfAsignacion) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "activo_id": obj.activo_id,
        "activo_nombre": obj.activo.nombre if obj.activo else None,
        "activo_codigo": obj.activo.codigo if obj.activo else None,
        "empleado": obj.empleado,
        "area": obj.area,
        "fecha_asignacion": date_str(obj.fecha_asignacion),
        "fecha_devolucion": date_str(obj.fecha_devolucion),
        "estado": obj.estado,
        "observaciones": obj.observaciones,
        "creado_en": date_str(obj.creado_en),
        "actualizado_en": date_str(obj.actualizado_en),
    }


def mantenimiento_to_dict(obj: AfMantenimiento) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "activo_id": obj.activo_id,
        "activo_nombre": obj.activo.nombre if obj.activo else None,
        "activo_codigo": obj.activo.codigo if obj.activo else None,
        "tipo": obj.tipo,
        "descripcion": obj.descripcion,
        "proveedor": obj.proveedor,
        "fecha_inicio": date_str(obj.fecha_inicio),
        "fecha_fin": date_str(obj.fecha_fin),
        "costo": dec_str(obj.costo),
        "estado": obj.estado,
        "observaciones": obj.observaciones,
        "creado_en": date_str(obj.creado_en),
        "actualizado_en": date_str(obj.actualizado_en),
    }


def baja_to_dict(obj: AfBaja) -> Dict[str, Any]:
    return {
        "id": obj.id,
        "activo_id": obj.activo_id,
        "activo_nombre": obj.activo.nombre if obj.activo else None,
        "activo_codigo": obj.activo.codigo if obj.activo else None,
        "motivo": obj.motivo,
        "fecha_baja": date_str(obj.fecha_baja),
        "valor_residual_real": dec_str(obj.valor_residual_real),
        "observaciones": obj.observaciones,
        "creado_en": date_str(obj.creado_en),
    }


__all__ = [
    "activo_to_dict",
    "asignacion_to_dict",
    "baja_to_dict",
    "date_str",
    "dec_str",
    "depreciacion_to_dict",
    "mantenimiento_to_dict",
]
