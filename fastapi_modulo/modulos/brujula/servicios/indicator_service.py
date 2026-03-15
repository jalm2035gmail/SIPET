from __future__ import annotations

from fastapi.responses import JSONResponse

from fastapi_modulo.modulos.brujula.controladores.dependencies import get_session_local, resolve_current_tenant_id
from fastapi_modulo.modulos.brujula.modelos.brujula_fixed_indicators import get_brujula_fixed_indicators
from fastapi_modulo.modulos.brujula.modelos.schemas import (
    IndicatorDefinitionOverrideUpdate,
    IndicatorMatrixResponse,
    IndicatorNotebookUpdate,
    IndicatorScenariosResponse,
)
from fastapi_modulo.modulos.brujula.repositorios.indicator_repository import (
    list_indicator_rows,
    replace_indicator_rows,
)
from fastapi_modulo.modulos.brujula.repositorios.override_repository import (
    load_overrides,
    upsert_override,
)
from fastapi_modulo.modulos.brujula.repositorios.tenant_repository import require_tenant_id
from fastapi_modulo.modulos.brujula.servicios.analysis_service import (
    build_brujula_indicator_scenarios,
    calculate_brujula_indicator_values,
)
from fastapi_modulo.modulos.brujula.servicios.projection_service import (
    get_projection_periods,
    normalize_indicator_matrix_rows,
)


def fixed_indicator_definitions() -> list[dict]:
    return get_brujula_fixed_indicators()


def fixed_indicator_names() -> list[str]:
    return [str(item.get("nombre") or "").strip() for item in fixed_indicator_definitions() if str(item.get("nombre") or "").strip()]


def merge_indicator_definitions_with_overrides(db=None, tenant_id: str | None = None) -> list[dict]:
    items = fixed_indicator_definitions()
    overrides: dict[str, dict[str, str]] = {}
    if db is not None and tenant_id:
        overrides = load_overrides(db, require_tenant_id(tenant_id))
    merged: list[dict] = []
    for item in items:
        current = dict(item)
        override = overrides.get(str(current.get("nombre") or "").strip().lower()) or {}
        for field in ("estandar_meta", "semaforo_rojo", "semaforo_verde"):
            if field in override:
                current[field] = str(override.get(field) or "").strip()
        merged.append(current)
    return merged


def get_indicator_notebook_response(request):
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        tenant_id = require_tenant_id(resolve_current_tenant_id(request))
        periods = get_projection_periods()
        calculated_values = calculate_brujula_indicator_values(periods, fixed_indicator_names())
        stored = normalize_indicator_matrix_rows(list_indicator_rows(db, tenant_id), periods)
        values_by_name = {str(item["indicador"]).strip().lower(): item.get("values") or {} for item in stored}
        fixed_rows = []
        for order, name in enumerate(fixed_indicator_names(), start=1):
            calculated_row = calculated_values.get(name) or {}
            stored_row = values_by_name.get(name.lower()) or {}
            fixed_rows.append(
                {
                    "indicador": name,
                    "values": {
                        str(period["key"]): str(calculated_row.get(str(period["key"])) or stored_row.get(str(period["key"]), "")).strip()
                        for period in periods
                    },
                    "orden": order,
                }
            )
        payload = IndicatorMatrixResponse(periods=periods, rows=fixed_rows)
        return JSONResponse({"success": True, "data": payload.model_dump()})
    finally:
        db.close()


def save_indicator_notebook_response(request, data: IndicatorNotebookUpdate):
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        tenant_id = require_tenant_id(resolve_current_tenant_id(request))
        periods = get_projection_periods()
        rows = normalize_indicator_matrix_rows(data.model_dump().get("rows"), periods)
        allowed_names = {name.lower(): name for name in fixed_indicator_names()}
        values_by_name = {}
        for row in rows:
            indicator_name = str(row.get("indicador") or "").strip()
            if indicator_name.lower() not in allowed_names:
                continue
            canonical_name = allowed_names[indicator_name.lower()]
            values_by_name[canonical_name] = row.get("values") or {}
        fixed_rows = []
        for order, canonical_name in enumerate(fixed_indicator_names(), start=1):
            fixed_rows.append(
                {
                    "indicador": canonical_name,
                    "values": {str(period["key"]): str((values_by_name.get(canonical_name) or {}).get(str(period["key"]), "")).strip() for period in periods},
                    "orden": order,
                }
            )
        replace_indicator_rows(db, tenant_id, fixed_rows)
        db.commit()
        payload = {"rows": fixed_rows}
        return JSONResponse({"success": True, "data": payload})
    except Exception as exc:
        db.rollback()
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)
    finally:
        db.close()


def list_indicator_definitions_response(request):
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        tenant_id = require_tenant_id(resolve_current_tenant_id(request))
        return JSONResponse({"success": True, "data": merge_indicator_definitions_with_overrides(db, tenant_id)})
    finally:
        db.close()


def get_indicator_scenarios_response(request):
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        tenant_id = require_tenant_id(resolve_current_tenant_id(request))
        periods = get_projection_periods()
        scenarios = build_brujula_indicator_scenarios(periods, merge_indicator_definitions_with_overrides(db, tenant_id))
        payload = IndicatorScenariosResponse(periods=periods, scenarios=scenarios)
        return JSONResponse({"success": True, "data": payload.model_dump()})
    finally:
        db.close()


def save_indicator_definition_response(request, data: IndicatorDefinitionOverrideUpdate):
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        tenant_id = require_tenant_id(resolve_current_tenant_id(request))
        allowed_names = {str(item.get("nombre") or "").strip().lower(): str(item.get("nombre") or "").strip() for item in fixed_indicator_definitions()}
        payload = data.model_dump()
        indicador = str(payload.get("nombre") or payload.get("indicador") or "").strip()
        if not indicador or indicador.lower() not in allowed_names:
            return JSONResponse({"success": False, "error": "Indicador invalido."}, status_code=400)
        canonical_name = allowed_names[indicador.lower()]
        upsert_override(
            db,
            tenant_id,
            canonical_name,
            str(payload.get("estandar_meta") or "").strip(),
            str(payload.get("semaforo_rojo") or "").strip(),
            str(payload.get("semaforo_verde") or "").strip(),
        )
        db.commit()
        merged_items = merge_indicator_definitions_with_overrides(db, tenant_id)
        updated = next((item for item in merged_items if str(item.get("nombre") or "").strip().lower() == canonical_name.lower()), None)
        return JSONResponse({"success": True, "data": updated or {}})
    except Exception as exc:
        db.rollback()
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)
    finally:
        db.close()


def delete_indicator_definition_response():
    return JSONResponse(
        {"success": False, "error": "Los indicadores de BRUJULA estan fijos en la aplicacion."},
        status_code=405,
    )


def import_indicator_definitions_response():
    return JSONResponse(
        {"success": False, "error": "La importacion esta deshabilitada porque los indicadores de BRUJULA son fijos."},
        status_code=405,
    )


def initialize_indicator_storage_on_startup() -> None:
    from fastapi_modulo.modulos.brujula.repositorios.schema import (
        ensure_indicator_table_schema,
        ensure_override_table_schema,
    )

    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        ensure_indicator_table_schema(db)
        ensure_override_table_schema(db)
        db.commit()
    finally:
        db.close()
