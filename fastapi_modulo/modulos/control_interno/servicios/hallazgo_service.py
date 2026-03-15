from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException

from fastapi_modulo.modulos.control_interno.modelos.enums import (
    ACCION_ESTADOS,
    HALLAZGO_ESTADOS,
    HALLAZGO_RIESGOS,
    EstadoAccionCorrectiva,
    EstadoHallazgo,
    NivelRiesgoHallazgo,
    clean_optional_text,
    clean_text,
    coerce_choice,
)
from fastapi_modulo.modulos.control_interno.modelos.schemas import (
    AccionCorrectivaCreate,
    AccionCorrectivaUpdate,
    HallazgoCreate,
    HallazgoUpdate,
    dump_schema,
    validate_schema,
)
from fastapi_modulo.modulos.control_interno.repositorios.base import get_current_tenant, session_scope
from fastapi_modulo.modulos.control_interno.repositorios.evidencia_repository import get_evidencia
from fastapi_modulo.modulos.control_interno.repositorios.hallazgo_repository import (
    create_accion,
    create_hallazgo,
    delete_accion,
    delete_hallazgo,
    get_accion,
    get_hallazgo,
    list_acciones,
    list_all_acciones,
    list_all_hallazgos,
    list_hallazgos,
)
from fastapi_modulo.modulos.control_interno.repositorios.programa_repository import get_actividad
from fastapi_modulo.modulos.control_interno.servicios._common import contains_text, iso_date, parse_date


def _validate_hallazgo_payload(db, payload: dict[str, Any], *, hallazgo_id: int | None = None, current_item=None) -> None:
    fecha_deteccion = payload.get("fecha_deteccion", getattr(current_item, "fecha_deteccion", None))
    fecha_limite = payload.get("fecha_limite", getattr(current_item, "fecha_limite", None))
    estado = payload.get("estado", getattr(current_item, "estado", None))
    nivel_riesgo = payload.get("nivel_riesgo", getattr(current_item, "nivel_riesgo", None))
    responsable = payload.get("responsable", getattr(current_item, "responsable", None))
    evidencia_id = payload.get("evidencia_id", getattr(current_item, "evidencia_id", None))

    if fecha_deteccion and fecha_limite and fecha_limite < fecha_deteccion:
        raise HTTPException(status_code=422, detail="La fecha limite no puede ser menor que la fecha de deteccion.")
    if nivel_riesgo == NivelRiesgoHallazgo.CRITICO.value and (not responsable or not fecha_limite):
        raise HTTPException(status_code=422, detail="Un hallazgo critico requiere responsable y fecha limite.")
    if evidencia_id:
        evidencia = get_evidencia(db, evidencia_id)
        if evidencia and evidencia.resultado_evaluacion == "Por evaluar":
            raise HTTPException(status_code=422, detail="No se puede registrar un hallazgo sobre una evidencia pendiente de evaluacion.")
    if estado == EstadoHallazgo.CERRADO.value:
        item = current_item if current_item and current_item.id == hallazgo_id else get_hallazgo(db, hallazgo_id) if hallazgo_id else None
        acciones = list(item.acciones or []) if item else []
        if not any(acc.estado == EstadoAccionCorrectiva.VERIFICADA.value for acc in acciones):
            raise HTTPException(status_code=422, detail="No se puede cerrar un hallazgo sin al menos una accion verificada.")


def _validate_accion_payload(payload: dict[str, Any], *, current_item=None) -> None:
    fecha_compromiso = payload.get("fecha_compromiso", getattr(current_item, "fecha_compromiso", None))
    fecha_ejecucion = payload.get("fecha_ejecucion", getattr(current_item, "fecha_ejecucion", None))
    estado = payload.get("estado", getattr(current_item, "estado", None))
    evidencia_seguimiento = payload.get("evidencia_seguimiento", getattr(current_item, "evidencia_seguimiento", None))
    if fecha_compromiso and fecha_ejecucion and fecha_ejecucion < fecha_compromiso and not evidencia_seguimiento:
        raise HTTPException(status_code=422, detail="Se requiere evidencia de seguimiento para registrar una ejecucion anterior al compromiso.")
    if estado == EstadoAccionCorrectiva.VERIFICADA.value and not evidencia_seguimiento:
        raise HTTPException(status_code=422, detail="No se puede verificar una accion sin evidencia de seguimiento.")


def _accion_dict(item) -> dict[str, Any]:
    return {
        "id": item.id,
        "hallazgo_id": item.hallazgo_id,
        "descripcion": item.descripcion,
        "responsable": item.responsable or "",
        "fecha_compromiso": iso_date(item.fecha_compromiso),
        "fecha_ejecucion": iso_date(item.fecha_ejecucion),
        "estado": item.estado,
        "evidencia_seguimiento": item.evidencia_seguimiento or "",
        "creado_en": iso_date(item.creado_en),
        "actualizado_en": iso_date(item.actualizado_en),
    }


def _hallazgo_dict(item, *, include_acciones: bool = False) -> dict[str, Any]:
    data = {
        "id": item.id,
        "evidencia_id": item.evidencia_id,
        "actividad_id": item.actividad_id,
        "control_id": item.control_id,
        "codigo": item.codigo or "",
        "titulo": item.titulo,
        "descripcion": item.descripcion or "",
        "causa": item.causa or "",
        "efecto": item.efecto or "",
        "componente_coso": item.componente_coso or "",
        "nivel_riesgo": item.nivel_riesgo,
        "estado": item.estado,
        "fecha_deteccion": iso_date(item.fecha_deteccion),
        "fecha_limite": iso_date(item.fecha_limite),
        "responsable": item.responsable or "",
        "creado_en": iso_date(item.creado_en),
        "actualizado_en": iso_date(item.actualizado_en),
        "control_codigo": item.control.codigo if item.control else "",
        "control_nombre": item.control.nombre if item.control else "",
        "total_acciones": len(item.acciones or []),
    }
    if include_acciones:
        data["acciones"] = [_accion_dict(acc) for acc in (item.acciones or [])]
    return data


def _hallazgo_payload(data: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
    schema_cls = HallazgoUpdate if partial else HallazgoCreate
    payload = dump_schema(validate_schema(schema_cls, data), exclude_unset=partial)
    result: dict[str, Any] = {}
    for field in ("evidencia_id", "actividad_id", "control_id"):
        if field in payload:
            result[field] = int(payload[field]) if payload[field] else None
    if "codigo" in payload:
        result["codigo"] = clean_optional_text(payload.get("codigo"))
        if result["codigo"]:
            result["codigo"] = result["codigo"].upper()
    if "titulo" in payload:
        result["titulo"] = clean_text(payload["titulo"])
    for field in ("descripcion", "causa", "efecto", "componente_coso", "responsable"):
        if field in payload:
            result[field] = clean_optional_text(payload.get(field))
    if "nivel_riesgo" in payload:
        result["nivel_riesgo"] = coerce_choice(payload.get("nivel_riesgo"), HALLAZGO_RIESGOS, NivelRiesgoHallazgo.MEDIO.value)
    if "estado" in payload:
        result["estado"] = coerce_choice(payload.get("estado"), HALLAZGO_ESTADOS, EstadoHallazgo.ABIERTO.value)
    for field in ("fecha_deteccion", "fecha_limite"):
        if field in payload:
            result[field] = parse_date(payload.get(field))
    return result


def _accion_payload(data: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
    schema_cls = AccionCorrectivaUpdate if partial else AccionCorrectivaCreate
    payload = dump_schema(validate_schema(schema_cls, data), exclude_unset=partial)
    result: dict[str, Any] = {}
    if "descripcion" in payload:
        result["descripcion"] = clean_text(payload["descripcion"])
    if "responsable" in payload:
        result["responsable"] = clean_optional_text(payload.get("responsable"))
    if "estado" in payload:
        result["estado"] = coerce_choice(payload.get("estado"), ACCION_ESTADOS, EstadoAccionCorrectiva.PENDIENTE.value)
    if "evidencia_seguimiento" in payload:
        result["evidencia_seguimiento"] = clean_optional_text(payload.get("evidencia_seguimiento"))
    for field in ("fecha_compromiso", "fecha_ejecucion"):
        if field in payload:
            result[field] = parse_date(payload.get(field))
    return result


def _autolink_hallazgo_relations(db, payload: dict[str, Any]) -> dict[str, Any]:
    evidencia_id = payload.get("evidencia_id")
    actividad_id = payload.get("actividad_id")
    control_id = payload.get("control_id")

    if evidencia_id:
        evidencia = get_evidencia(db, evidencia_id)
        if evidencia:
            if not actividad_id and evidencia.actividad_id:
                payload["actividad_id"] = evidencia.actividad_id
                actividad_id = evidencia.actividad_id
            if not control_id and evidencia.control_id:
                payload["control_id"] = evidencia.control_id
                control_id = evidencia.control_id

    if actividad_id and not control_id:
        actividad = get_actividad(db, actividad_id)
        if actividad and actividad.control_id:
            payload["control_id"] = actividad.control_id
    return payload


def listar_service(
    *,
    nivel_riesgo: str | None = None,
    estado: str | None = None,
    control_id: int | None = None,
    componente_coso: str | None = None,
    q: str | None = None,
) -> list[dict[str, Any]]:
    with session_scope() as db:
        items = [_hallazgo_dict(item) for item in list_hallazgos(db, nivel_riesgo=nivel_riesgo, estado=estado, control_id=control_id, componente_coso=componente_coso)]
    return [item for item in items if contains_text(item["titulo"], item["codigo"], item["descripcion"], item["responsable"], query=q)]


def obtener_service(hallazgo_id: int) -> dict[str, Any] | None:
    with session_scope() as db:
        item = get_hallazgo(db, hallazgo_id)
        return _hallazgo_dict(item, include_acciones=True) if item else None


def crear_service(data: dict[str, Any]) -> dict[str, Any]:
    payload = _hallazgo_payload(data)
    now = datetime.utcnow()
    with session_scope() as db:
        payload = _autolink_hallazgo_relations(db, payload)
        _validate_hallazgo_payload(db, payload)
        return _hallazgo_dict(create_hallazgo(db, tenant_id=get_current_tenant(), creado_en=now, actualizado_en=now, **payload), include_acciones=True)


def actualizar_service(hallazgo_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    payload = _hallazgo_payload(data, partial=True)
    with session_scope() as db:
        item = get_hallazgo(db, hallazgo_id)
        if not item:
            return None
        payload = _autolink_hallazgo_relations(db, payload)
        _validate_hallazgo_payload(db, payload, hallazgo_id=hallazgo_id, current_item=item)
        for key, value in payload.items():
            setattr(item, key, value)
        item.actualizado_en = datetime.utcnow()
        db.flush()
        return _hallazgo_dict(get_hallazgo(db, hallazgo_id), include_acciones=True)


def eliminar_service(hallazgo_id: int) -> bool:
    with session_scope() as db:
        item = get_hallazgo(db, hallazgo_id)
        if not item:
            return False
        delete_hallazgo(db, item)
        return True


def listar_acciones_service(hallazgo_id: int) -> list[dict[str, Any]]:
    with session_scope() as db:
        return [_accion_dict(item) for item in list_acciones(db, hallazgo_id=hallazgo_id)]


def crear_accion_service(hallazgo_id: int, data: dict[str, Any]) -> dict[str, Any]:
    payload = _accion_payload(data)
    _validate_accion_payload(payload)
    now = datetime.utcnow()
    with session_scope() as db:
        return _accion_dict(create_accion(db, tenant_id=get_current_tenant(), hallazgo_id=hallazgo_id, creado_en=now, actualizado_en=now, **payload))


def actualizar_accion_service(accion_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    payload = _accion_payload(data, partial=True)
    with session_scope() as db:
        item = get_accion(db, accion_id)
        if not item:
            return None
        _validate_accion_payload(payload, current_item=item)
        for key, value in payload.items():
            setattr(item, key, value)
        item.actualizado_en = datetime.utcnow()
        db.flush()
        db.refresh(item)
        return _accion_dict(item)


def eliminar_accion_service(accion_id: int) -> bool:
    with session_scope() as db:
        item = get_accion(db, accion_id)
        if not item:
            return False
        delete_accion(db, item)
        return True


def resumen_service() -> dict[str, Any]:
    with session_scope() as db:
        items = list_all_hallazgos(db)
    por_estado: dict[str, int] = {}
    por_riesgo: dict[str, int] = {}
    for item in items:
        por_estado[item.estado] = por_estado.get(item.estado, 0) + 1
        por_riesgo[item.nivel_riesgo] = por_riesgo.get(item.nivel_riesgo, 0) + 1
    return {"total": len(items), "por_estado": por_estado, "por_riesgo": por_riesgo}


def all_hallazgos() -> list:
    with session_scope() as db:
        return list_all_hallazgos(db)


def all_acciones() -> list:
    with session_scope() as db:
        return list_all_acciones(db)


__all__ = [
    "actualizar_accion_service",
    "actualizar_service",
    "all_acciones",
    "all_hallazgos",
    "crear_accion_service",
    "crear_service",
    "eliminar_accion_service",
    "eliminar_service",
    "listar_acciones_service",
    "listar_service",
    "obtener_service",
    "resumen_service",
]
