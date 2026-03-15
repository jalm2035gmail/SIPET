from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from fastapi import HTTPException

from fastapi_modulo.modulos.control_interno.modelos.hallazgo import Hallazgo
from fastapi_modulo.modulos.control_interno.modelos.enums import (
    EVIDENCIA_RESULTADOS,
    EVIDENCIA_TIPOS,
    ResultadoEvaluacion,
    TipoEvidencia,
    clean_optional_text,
    clean_text,
    coerce_choice,
)
from fastapi_modulo.modulos.control_interno.modelos.schemas import (
    EvidenciaCreate,
    EvidenciaUpdate,
    dump_schema,
    validate_schema,
)
from fastapi_modulo.modulos.control_interno.repositorios.base import get_current_tenant, session_scope
from fastapi_modulo.modulos.control_interno.repositorios.evidencia_repository import (
    create_evidencia,
    delete_evidencia,
    get_evidencia,
    list_all_evidencias,
    list_evidencias,
    list_resultados,
)
from fastapi_modulo.modulos.control_interno.repositorios.programa_repository import get_actividad
from fastapi_modulo.modulos.control_interno.servicios._common import contains_text, iso_date, parse_date

UPLOAD_DIR = "fastapi_modulo/uploads/control_interno/evidencias"


def _serialize(item) -> dict[str, Any]:
    return {
        "id": item.id,
        "actividad_id": item.actividad_id,
        "control_id": item.control_id,
        "titulo": item.titulo,
        "tipo": item.tipo,
        "descripcion": item.descripcion or "",
        "fecha_evidencia": iso_date(item.fecha_evidencia),
        "resultado_evaluacion": item.resultado_evaluacion,
        "observaciones": item.observaciones or "",
        "archivo_nombre": item.archivo_nombre or "",
        "archivo_uuid": item.archivo_uuid or "",
        "archivo_nombre_original": item.archivo_nombre_original or item.archivo_nombre or "",
        "archivo_extension": item.archivo_extension or "",
        "archivo_mime": item.archivo_mime or "",
        "archivo_tamanio": item.archivo_tamanio or 0,
        "tiene_archivo": bool(item.archivo_ruta and os.path.exists(item.archivo_ruta)),
        "creado_en": iso_date(item.creado_en),
        "actualizado_en": iso_date(item.actualizado_en),
        "actividad_desc": (item.actividad.descripcion or "")[:80] if item.actividad else "",
        "control_codigo": item.control.codigo if item.control else "",
        "control_nombre": item.control.nombre if item.control else "",
    }


def _payload(data: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
    schema_cls = EvidenciaUpdate if partial else EvidenciaCreate
    payload = dump_schema(validate_schema(schema_cls, data), exclude_unset=partial)
    result: dict[str, Any] = {}
    if "titulo" in payload:
        result["titulo"] = clean_text(payload["titulo"])
    if "tipo" in payload:
        result["tipo"] = coerce_choice(payload.get("tipo"), EVIDENCIA_TIPOS, TipoEvidencia.DOCUMENTO.value)
    if "fecha_evidencia" in payload:
        result["fecha_evidencia"] = parse_date(payload.get("fecha_evidencia"))
    if "control_id" in payload:
        result["control_id"] = int(payload["control_id"]) if payload["control_id"] else None
    if "actividad_id" in payload:
        result["actividad_id"] = int(payload["actividad_id"]) if payload["actividad_id"] else None
    if "resultado_evaluacion" in payload:
        result["resultado_evaluacion"] = coerce_choice(payload.get("resultado_evaluacion"), EVIDENCIA_RESULTADOS, ResultadoEvaluacion.POR_EVALUAR.value)
    for field in ("descripcion", "observaciones"):
        if field in payload:
            result[field] = clean_optional_text(payload.get(field))
    return result


def _validate_archivo_meta(archivo_meta: dict[str, Any]) -> None:
    ruta = archivo_meta.get("archivo_ruta")
    if not ruta:
        return
    safe_root = os.path.abspath(UPLOAD_DIR)
    target = os.path.abspath(str(ruta))
    if not target.startswith(safe_root):
        raise HTTPException(status_code=422, detail="La ruta del archivo no es valida.")
    if not archivo_meta.get("archivo_uuid") or not archivo_meta.get("archivo_extension"):
        raise HTTPException(status_code=422, detail="La metadata del archivo esta incompleta.")


def _validate_result_transition(db, item, payload: dict[str, Any]) -> None:
    nuevo_resultado = payload.get("resultado_evaluacion")
    if nuevo_resultado != ResultadoEvaluacion.POR_EVALUAR.value:
        return
    if not item or not getattr(item, "id", None):
        return
    if db.query(Hallazgo.id).filter(Hallazgo.evidencia_id == item.id, Hallazgo.tenant_id == get_current_tenant()).first():
        raise HTTPException(status_code=422, detail="No se puede regresar a 'Por evaluar' una evidencia con hallazgos asociados.")


def _autolink_relations(db, payload: dict[str, Any]) -> dict[str, Any]:
    actividad_id = payload.get("actividad_id")
    control_id = payload.get("control_id")
    if actividad_id and not control_id:
        actividad = get_actividad(db, actividad_id)
        if actividad and actividad.control_id:
            payload["control_id"] = actividad.control_id
    return payload


def listar_service(
    *,
    actividad_id: int | None = None,
    control_id: int | None = None,
    tipo: str | None = None,
    resultado_evaluacion: str | None = None,
    q: str | None = None,
) -> list[dict[str, Any]]:
    with session_scope() as db:
        items = [_serialize(item) for item in list_evidencias(db, actividad_id=actividad_id, control_id=control_id, tipo=tipo, resultado_evaluacion=resultado_evaluacion)]
    return [item for item in items if contains_text(item["titulo"], item["descripcion"], item["control_codigo"], item["actividad_desc"], query=q)]


def obtener_service(evidencia_id: int) -> dict[str, Any] | None:
    with session_scope() as db:
        item = get_evidencia(db, evidencia_id)
        return _serialize(item) if item else None


def obtener_ruta_archivo_service(evidencia_id: int) -> str | None:
    with session_scope() as db:
        item = get_evidencia(db, evidencia_id)
        return _safe_file_path(item.archivo_ruta) if item else None


def crear_service(data: dict[str, Any], **archivo_meta) -> dict[str, Any]:
    payload = _payload(data)
    _validate_archivo_meta(archivo_meta)
    now = datetime.utcnow()
    with session_scope() as db:
        payload = _autolink_relations(db, payload)
        return _serialize(create_evidencia(db, tenant_id=get_current_tenant(), creado_en=now, actualizado_en=now, **payload, **archivo_meta))


def actualizar_service(evidencia_id: int, data: dict[str, Any], **archivo_meta) -> dict[str, Any] | None:
    payload = _payload(data, partial=True)
    _validate_archivo_meta(archivo_meta)
    with session_scope() as db:
        item = get_evidencia(db, evidencia_id)
        if not item:
            return None
        _validate_result_transition(db, item, payload)
        payload = _autolink_relations(db, payload)
        old_ruta = item.archivo_ruta
        for key, value in payload.items():
            setattr(item, key, value)
        if archivo_meta.get("archivo_ruta"):
            _delete_file(old_ruta)
            item.archivo_nombre = archivo_meta.get("archivo_nombre")
            item.archivo_uuid = archivo_meta.get("archivo_uuid")
            item.archivo_nombre_original = archivo_meta.get("archivo_nombre_original")
            item.archivo_extension = archivo_meta.get("archivo_extension")
            item.archivo_ruta = archivo_meta.get("archivo_ruta")
            item.archivo_mime = archivo_meta.get("archivo_mime")
            item.archivo_tamanio = archivo_meta.get("archivo_tamanio")
        item.actualizado_en = datetime.utcnow()
        db.flush()
        return _serialize(get_evidencia(db, evidencia_id))


def eliminar_service(evidencia_id: int) -> bool:
    with session_scope() as db:
        item = get_evidencia(db, evidencia_id)
        if not item:
            return False
        _delete_file(item.archivo_ruta)
        delete_evidencia(db, item)
        return True


def resumen_por_resultado_service() -> dict[str, int]:
    with session_scope() as db:
        rows = list_resultados(db)
    conteo: dict[str, int] = {}
    for value in rows:
        conteo[value] = conteo.get(value, 0) + 1
    return conteo


def all_evidencias() -> list:
    with session_scope() as db:
        return list_all_evidencias(db)


def _delete_file(path: str | None) -> None:
    target = _safe_file_path(path)
    if target and os.path.exists(target):
        os.remove(target)


def _safe_file_path(path: str | None) -> str | None:
    if not path:
        return None
    safe_root = os.path.abspath(UPLOAD_DIR)
    target = os.path.abspath(path)
    return target if target.startswith(safe_root) else None


__all__ = [
    "UPLOAD_DIR",
    "actualizar_service",
    "all_evidencias",
    "crear_service",
    "eliminar_service",
    "listar_service",
    "obtener_ruta_archivo_service",
    "obtener_service",
    "resumen_por_resultado_service",
]
