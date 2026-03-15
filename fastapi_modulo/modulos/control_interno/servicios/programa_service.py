from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException

from fastapi_modulo.modulos.control_interno.modelos.enums import (
    ACTIVIDAD_ESTADOS,
    PROGRAMA_ESTADOS,
    EstadoActividad,
    EstadoPrograma,
    clean_optional_text,
    clean_text,
    coerce_choice,
)
from fastapi_modulo.modulos.control_interno.modelos.schemas import (
    ProgramaActividadCreate,
    ProgramaActividadUpdate,
    ProgramaCreate,
    ProgramaUpdate,
    dump_schema,
    validate_schema,
)
from fastapi_modulo.modulos.control_interno.repositorios.base import get_current_tenant, session_scope
from fastapi_modulo.modulos.control_interno.repositorios.programa_repository import (
    create_actividad,
    create_programa,
    delete_actividad,
    delete_programa,
    get_actividad,
    get_programa,
    list_actividades,
    list_all_actividades,
    list_programas,
)
from fastapi_modulo.modulos.control_interno.servicios._common import iso_date, parse_date


def _validate_programa_state(db, programa_id: int, payload: dict[str, Any]) -> None:
    if payload.get("estado") != EstadoPrograma.APROBADO.value:
        return
    if not list_actividades(db, programa_id=programa_id):
        raise HTTPException(status_code=422, detail="No se puede aprobar un programa sin actividades.")


def _validate_actividad_payload(payload: dict[str, Any]) -> None:
    fecha_inicio_programada = payload.get("fecha_inicio_programada")
    fecha_fin_programada = payload.get("fecha_fin_programada")
    fecha_inicio_real = payload.get("fecha_inicio_real")
    fecha_fin_real = payload.get("fecha_fin_real")
    estado = payload.get("estado")

    if fecha_inicio_programada and fecha_fin_programada and fecha_fin_programada < fecha_inicio_programada:
        raise HTTPException(status_code=422, detail="La fecha fin programada no puede ser menor que la fecha inicio programada.")
    if fecha_inicio_real and fecha_fin_real and fecha_fin_real < fecha_inicio_real:
        raise HTTPException(status_code=422, detail="La fecha fin real no puede ser menor que la fecha inicio real.")
    if estado == EstadoActividad.COMPLETADO.value and not fecha_fin_real:
        raise HTTPException(status_code=422, detail="No se puede completar una actividad sin fecha real de cierre.")


def _programa_dict(item) -> dict[str, Any]:
    return {
        "id": item.id,
        "anio": item.anio,
        "nombre": item.nombre,
        "descripcion": item.descripcion or "",
        "estado": item.estado,
        "creado_en": iso_date(item.creado_en),
        "actualizado_en": iso_date(item.actualizado_en),
    }


def _actividad_dict(item) -> dict[str, Any]:
    return {
        "id": item.id,
        "programa_id": item.programa_id,
        "control_id": item.control_id,
        "descripcion": item.descripcion or "",
        "responsable": item.responsable or "",
        "fecha_inicio_programada": iso_date(item.fecha_inicio_programada),
        "fecha_fin_programada": iso_date(item.fecha_fin_programada),
        "fecha_inicio_real": iso_date(item.fecha_inicio_real),
        "fecha_fin_real": iso_date(item.fecha_fin_real),
        "estado": item.estado,
        "observaciones": item.observaciones or "",
        "creado_en": iso_date(item.creado_en),
        "actualizado_en": iso_date(item.actualizado_en),
        "control_codigo": item.control.codigo if item.control else "",
        "control_nombre": item.control.nombre if item.control else "",
        "control_componente": item.control.componente if item.control else "",
    }


def _programa_payload(data: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
    schema_cls = ProgramaUpdate if partial else ProgramaCreate
    payload = dump_schema(validate_schema(schema_cls, data), exclude_unset=partial)
    result = {}
    if "anio" in payload:
        result["anio"] = int(payload["anio"])
    if "nombre" in payload:
        result["nombre"] = clean_text(payload["nombre"])
    if "descripcion" in payload:
        result["descripcion"] = clean_optional_text(payload.get("descripcion"))
    if "estado" in payload:
        result["estado"] = coerce_choice(payload.get("estado"), PROGRAMA_ESTADOS, EstadoPrograma.BORRADOR.value)
    return result


def _actividad_payload(data: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
    schema_cls = ProgramaActividadUpdate if partial else ProgramaActividadCreate
    payload = dump_schema(validate_schema(schema_cls, data), exclude_unset=partial)
    result: dict[str, Any] = {}
    if "control_id" in payload:
        result["control_id"] = int(payload["control_id"]) if payload["control_id"] else None
    for field in ("descripcion", "responsable", "observaciones"):
        if field in payload:
            result[field] = clean_optional_text(payload.get(field))
    for field in ("fecha_inicio_programada", "fecha_fin_programada", "fecha_inicio_real", "fecha_fin_real"):
        if field in payload:
            result[field] = parse_date(payload.get(field))
    if "estado" in payload:
        result["estado"] = coerce_choice(payload.get("estado"), ACTIVIDAD_ESTADOS, EstadoActividad.PROGRAMADO.value)
    return result


def listar_programas_service(anio: int | None = None) -> list[dict[str, Any]]:
    with session_scope() as db:
        return [_programa_dict(item) for item in list_programas(db, anio=anio)]


def obtener_programa_service(programa_id: int) -> dict[str, Any] | None:
    with session_scope() as db:
        item = get_programa(db, programa_id)
        return _programa_dict(item) if item else None


def crear_programa_service(data: dict[str, Any]) -> dict[str, Any]:
    payload = _programa_payload(data)
    if payload.get("estado") == EstadoPrograma.APROBADO.value:
        raise HTTPException(status_code=422, detail="No se puede crear un programa aprobado sin actividades.")
    now = datetime.utcnow()
    with session_scope() as db:
        return _programa_dict(create_programa(db, tenant_id=get_current_tenant(), creado_en=now, actualizado_en=now, **payload))


def actualizar_programa_service(programa_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    payload = _programa_payload(data, partial=True)
    with session_scope() as db:
        item = get_programa(db, programa_id)
        if not item:
            return None
        _validate_programa_state(db, programa_id, payload)
        for key, value in payload.items():
            setattr(item, key, value)
        item.actualizado_en = datetime.utcnow()
        db.flush()
        db.refresh(item)
        return _programa_dict(item)


def eliminar_programa_service(programa_id: int) -> bool:
    with session_scope() as db:
        item = get_programa(db, programa_id)
        if not item:
            return False
        delete_programa(db, item)
        return True


def listar_actividades_service(programa_id: int, estado: str | None = None) -> list[dict[str, Any]]:
    with session_scope() as db:
        return [_actividad_dict(item) for item in list_actividades(db, programa_id=programa_id, estado=estado)]


def obtener_actividad_service(actividad_id: int) -> dict[str, Any] | None:
    with session_scope() as db:
        item = get_actividad(db, actividad_id)
        return _actividad_dict(item) if item else None


def crear_actividad_service(programa_id: int, data: dict[str, Any]) -> dict[str, Any]:
    payload = _actividad_payload(data)
    _validate_actividad_payload(payload)
    now = datetime.utcnow()
    with session_scope() as db:
        return _actividad_dict(create_actividad(db, tenant_id=get_current_tenant(), programa_id=programa_id, creado_en=now, actualizado_en=now, **payload))


def actualizar_actividad_service(actividad_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    payload = _actividad_payload(data, partial=True)
    with session_scope() as db:
        item = get_actividad(db, actividad_id)
        if not item:
            return None
        merged = {
            "fecha_inicio_programada": item.fecha_inicio_programada,
            "fecha_fin_programada": item.fecha_fin_programada,
            "fecha_inicio_real": item.fecha_inicio_real,
            "fecha_fin_real": item.fecha_fin_real,
            "estado": item.estado,
            **payload,
        }
        _validate_actividad_payload(merged)
        for key, value in payload.items():
            setattr(item, key, value)
        item.actualizado_en = datetime.utcnow()
        db.flush()
        return _actividad_dict(get_actividad(db, actividad_id))


def eliminar_actividad_service(actividad_id: int) -> bool:
    with session_scope() as db:
        item = get_actividad(db, actividad_id)
        if not item:
            return False
        delete_actividad(db, item)
        return True


def resumen_programa_service(programa_id: int) -> dict[str, Any]:
    with session_scope() as db:
        items = list_actividades(db, programa_id=programa_id)
    total = len(items)
    conteo: dict[str, int] = {}
    for item in items:
        conteo[item.estado] = conteo.get(item.estado, 0) + 1
    completado = conteo.get(EstadoActividad.COMPLETADO.value, 0)
    return {
        "total": total,
        "conteo": conteo,
        "completado": completado,
        "porcentaje": round(completado * 100 / total) if total else 0,
    }


def all_actividades() -> list:
    with session_scope() as db:
        return list_all_actividades(db)


__all__ = [
    "actualizar_actividad_service",
    "actualizar_programa_service",
    "all_actividades",
    "crear_actividad_service",
    "crear_programa_service",
    "eliminar_actividad_service",
    "eliminar_programa_service",
    "listar_actividades_service",
    "listar_programas_service",
    "obtener_actividad_service",
    "obtener_programa_service",
    "resumen_programa_service",
]
