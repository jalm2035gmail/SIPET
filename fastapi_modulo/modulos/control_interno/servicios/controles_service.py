from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi_modulo.modulos.control_interno.modelos.enums import (
    CONTROL_ESTADOS,
    CONTROL_PERIODICIDADES,
    EstadoControl,
    PeriodicidadControl,
    clean_optional_text,
    clean_text,
    coerce_choice,
)
from fastapi_modulo.modulos.control_interno.modelos.schemas import (
    ControlInternoCreate,
    ControlInternoUpdate,
    dump_schema,
    validate_schema,
)
from fastapi_modulo.modulos.control_interno.repositorios.base import get_current_tenant, session_scope
from fastapi_modulo.modulos.control_interno.repositorios.controles_repository import (
    create_control,
    delete_control,
    distinct_areas,
    distinct_componentes,
    get_control,
    list_controles,
)
from fastapi_modulo.modulos.control_interno.servicios._common import iso_date


def _serialize(obj) -> dict[str, Any]:
    return {
        "id": obj.id,
        "codigo": obj.codigo,
        "nombre": obj.nombre,
        "componente": obj.componente,
        "area": obj.area,
        "tipo_riesgo": obj.tipo_riesgo or "",
        "periodicidad": obj.periodicidad,
        "descripcion": obj.descripcion or "",
        "normativa": obj.normativa or "",
        "estado": obj.estado,
        "creado_en": iso_date(obj.creado_en),
        "actualizado_en": iso_date(obj.actualizado_en),
    }


def _normalized_payload(data: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
    schema_cls = ControlInternoUpdate if partial else ControlInternoCreate
    schema = validate_schema(schema_cls, data)
    payload = dump_schema(schema, exclude_unset=partial)
    normalized = {
        "codigo": clean_text(payload.get("codigo")).upper() if "codigo" in payload else None,
        "nombre": clean_text(payload.get("nombre")) if "nombre" in payload else None,
        "componente": clean_text(payload.get("componente")) if "componente" in payload else None,
        "area": clean_text(payload.get("area")) if "area" in payload else None,
        "tipo_riesgo": clean_optional_text(payload.get("tipo_riesgo")) if "tipo_riesgo" in payload else None,
        "periodicidad": coerce_choice(payload.get("periodicidad"), CONTROL_PERIODICIDADES, PeriodicidadControl.MENSUAL.value) if "periodicidad" in payload else None,
        "descripcion": clean_optional_text(payload.get("descripcion")) if "descripcion" in payload else None,
        "normativa": clean_optional_text(payload.get("normativa")) if "normativa" in payload else None,
        "estado": coerce_choice(payload.get("estado"), CONTROL_ESTADOS, EstadoControl.ACTIVO.value) if "estado" in payload else None,
    }
    return {key: value for key, value in normalized.items() if value is not None}


def listar(componente: str | None = None, area: str | None = None, estado: str | None = None, q: str | None = None) -> list[dict[str, Any]]:
    with session_scope() as db:
        items = [_serialize(item) for item in list_controles(db, componente=componente, area=area, estado=estado)]
    if not q:
        return items
    return [item for item in items if q.lower() in ((item["codigo"] + item["nombre"] + item["area"]).lower())]


def obtener(control_id: int) -> dict[str, Any] | None:
    with session_scope() as db:
        obj = get_control(db, control_id)
        return _serialize(obj) if obj else None


def crear(data: dict[str, Any]) -> dict[str, Any]:
    payload = _normalized_payload(data)
    now = datetime.utcnow()
    with session_scope() as db:
        obj = create_control(db, tenant_id=get_current_tenant(), creado_en=now, actualizado_en=now, **payload)
        return _serialize(obj)


def actualizar(control_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    payload = _normalized_payload(data, partial=True)
    with session_scope() as db:
        obj = get_control(db, control_id)
        if not obj:
            return None
        for key, value in payload.items():
            setattr(obj, key, value)
        obj.actualizado_en = datetime.utcnow()
        db.flush()
        db.refresh(obj)
        return _serialize(obj)


def eliminar(control_id: int) -> bool:
    with session_scope() as db:
        obj = get_control(db, control_id)
        if not obj:
            return False
        delete_control(db, obj)
        return True


def opciones() -> dict[str, list[str]]:
    with session_scope() as db:
        return {
            "componentes": sorted(set(distinct_componentes(db))),
            "areas": sorted(set(distinct_areas(db))),
        }


__all__ = ["actualizar", "crear", "eliminar", "listar", "obtener", "opciones"]
