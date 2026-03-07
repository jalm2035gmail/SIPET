from __future__ import annotations

from datetime import datetime, timedelta
from textwrap import dedent
from typing import Any, Dict, List, Set
import sqlite3
import csv
import json
import os
import re
import threading
from html import escape
from io import StringIO, BytesIO
from pathlib import Path

from fastapi import APIRouter, Body, Request, Query, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, Response, RedirectResponse
from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
import numpy as np
from fastapi_modulo.db import IAFeatureFlag

router = APIRouter()

_APP_ENV = (os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "development").strip().lower()
_DEFAULT_SIPET_DATA_DIR = (os.environ.get("SIPET_DATA_DIR") or os.path.expanduser("~/.sipet/data")).strip()
_RUNTIME_STORE_DIR = (os.environ.get("RUNTIME_STORE_DIR") or os.path.join(_DEFAULT_SIPET_DATA_DIR, "runtime_store", _APP_ENV)).strip()
_COLAB_META_PATH = Path(
    os.environ.get("COLAB_META_PATH") or os.path.join(_RUNTIME_STORE_DIR, "colaboradores_meta.json")
)


_CORE_BOUND = False


def _bind_core_symbols() -> None:
    global _CORE_BOUND
    if _CORE_BOUND:
        return
    from fastapi_modulo import main as core

    names = [
        'render_backend_page',
        'SessionLocal',
        'StrategicAxisConfig',
        'StrategicObjectiveConfig',
        'POAActivity',
        'POASubactivity',
        'POADeliverableApproval',
        'UserNotificationRead',
        'DocumentoEvidencia',
        'PublicQuizSubmission',
        'Usuario',
        '_date_to_iso',
        '_activity_status',
        # '_allowed_objectives_for_user',
        'is_admin_or_superadmin',
        '_parse_date_field',
        '_validate_date_range',
        '_validate_child_date_range',
        '_current_user_record',
        '_user_aliases',
        '_resolve_process_owner_for_objective',
        '_is_user_process_owner',
        '_notification_user_key',
        '_normalize_tenant_id',
        # '_get_document_tenant',
            # '_can_authorize_documents',  # commented out: not present in fastapi_modulo.main
        'get_current_tenant',
        'get_current_role',
        'is_superadmin',
        'normalize_role_name',
        '_resolve_user_role_name',
    ]
    for name in names:
        globals()[name] = getattr(core, name)
    _CORE_BOUND = True


def _serialize_strategic_objective(obj: StrategicObjectiveConfig) -> Dict[str, Any]:
    _bind_core_symbols()
    return {
        "id": obj.id,
        "eje_id": obj.eje_id,
        "codigo": obj.codigo or "",
        "nombre": obj.nombre or "",
        "hito": obj.hito or "",
        "lider": obj.lider or "",
        "fecha_inicial": _date_to_iso(obj.fecha_inicial),
        "fecha_final": _date_to_iso(obj.fecha_final),
        "descripcion": obj.descripcion or "",
        "orden": obj.orden or 0,
    }


def _serialize_strategic_axis(axis: StrategicAxisConfig) -> Dict[str, Any]:
    _bind_core_symbols()
    objetivos = sorted(axis.objetivos or [], key=lambda item: (item.orden or 0, item.id or 0))
    return {
        "id": axis.id,
        "nombre": axis.nombre or "",
        "codigo": axis.codigo or "",
        "lider_departamento": axis.lider_departamento or "",
        "responsabilidad_directa": axis.responsabilidad_directa or "",
        "fecha_inicial": _date_to_iso(axis.fecha_inicial),
        "fecha_final": _date_to_iso(axis.fecha_final),
        "descripcion": axis.descripcion or "",
        "orden": axis.orden or 0,
        "objetivos_count": len(objetivos),
        "objetivos": [_serialize_strategic_objective(obj) for obj in objetivos],
    }


def _build_planificacion_snapshot_html() -> str:
    _bind_core_symbols()
    db = SessionLocal()
    try:
        axes = (
            db.query(StrategicAxisConfig)
            .filter(StrategicAxisConfig.is_active == True)
            .order_by(StrategicAxisConfig.orden.asc(), StrategicAxisConfig.id.asc())
            .all()
        )
        if not axes:
            axes = (
                db.query(StrategicAxisConfig)
                .order_by(StrategicAxisConfig.orden.asc(), StrategicAxisConfig.id.asc())
                .all()
            )
        objective_ids: List[int] = []
        axis_rows: List[str] = []
        for axis in axes[:8]:
            obj_count = len(getattr(axis, "objetivos", []) or [])
            objective_ids.extend(int(obj.id) for obj in (axis.objetivos or []) if getattr(obj, "id", None))
            axis_rows.append(
                f'<li><strong>{escape(axis.nombre or "Eje sin nombre")}</strong> '
                f'· {obj_count} objetivos · código {escape(axis.codigo or "N/D")}</li>'
            )
        objective_ids = sorted(set(objective_ids))
        activities_count = (
            db.query(POAActivity).filter(POAActivity.objective_id.in_(objective_ids)).count()
            if objective_ids
            else 0
        )
        axis_list_html = (
            '<ul>' + "".join(axis_rows) + "</ul>"
            if axis_rows
            else ""
        )
        return (
            '<section>'
            f'<div>Resumen cargado desde servidor</div>'
            f'<div>Ejes: {len(axes)} · Objetivos: {len(objective_ids)} · Actividades POA: {activities_count}</div>'
            f'{axis_list_html}'
            '</section>'
        )
    except Exception:
        return (
            '<section>'
            'No se pudo cargar el resumen de estrategia desde servidor.'
            '</section>'
        )
    finally:
        db.close()


def _build_poa_debug_html(request: Request) -> str:
    _bind_core_symbols()
    db = SessionLocal()
    try:
        detected_role = normalize_role_name(get_current_role(request))
        admin_like = _is_request_admin_like(request, db)
        feature_key = "suggest_objective_text"
        module_key = "poa"
        ia_enabled = True
        ia_rule = "*/*"
        ia_rule_id = 0
        try:
            rows = (
                db.query(IAFeatureFlag)
                .filter(IAFeatureFlag.feature_key == feature_key)
                .all()
            )
            if rows:
                candidates = []
                for row in rows:
                    row_role = normalize_role_name(str(row.role or "").strip()) if row.role else ""
                    row_module = str(row.module or "").strip().lower()
                    role_match = (not row_role) or (row_role == detected_role)
                    module_match = (not row_module) or (row_module == module_key)
                    if role_match and module_match:
                        specificity = (2 if row_role else 0) + (1 if row_module else 0)
                        updated_rank = row.updated_at.timestamp() if getattr(row, "updated_at", None) else 0
                        candidates.append((specificity, updated_rank, row))
                if candidates:
                    candidates.sort(key=lambda item: (item[0], item[1], int(item[2].id or 0)), reverse=True)
                    winner = candidates[0][2]
                    ia_enabled = bool(int(getattr(winner, "enabled", 1) or 0))
                    ia_rule = f'{str(winner.role or "*")}/{str(winner.module or "*")}'
                    ia_rule_id = int(getattr(winner, "id", 0) or 0)
        except Exception:
            ia_enabled = True
            ia_rule = "error/*"
            ia_rule_id = 0
        session_role = normalize_role_name(
            str(getattr(request.state, "user_role", None) or request.cookies.get("user_role") or "")
        )
        session_user = (
            str(getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "")
        ).strip() or "N/D"
        return (
            '<section>'
            '<div>Diagnóstico POA (servidor)</div>'
            '<div>'
            'build poa-debug-v3'
            f' · rol_detectado: {escape(detected_role or "n/d")}'
            f' · rol_sesion: {escape(session_role or "n/d")}'
            f' · admin_like: {"si" if admin_like else "no"}'
            f' · ia_poa_suggest: {"si" if ia_enabled else "no"}'
            f' · regla_ia: {escape(ia_rule)}'
            f' · regla_ia_id: {ia_rule_id}'
            f' · usuario_sesion: {escape(session_user)}'
            '</div>'
            '</section>'
        )
    except Exception:
        return (
            '<section>'
            'Diagnóstico POA no disponible.'
            '</section>'
        )
    finally:
        db.close()


def _build_initial_axis_list_html() -> str:
    _bind_core_symbols()
    db = SessionLocal()
    try:
        axes = (
            db.query(StrategicAxisConfig)
            .order_by(StrategicAxisConfig.orden.asc(), StrategicAxisConfig.id.asc())
            .all()
        )
        if not axes:
            return '<div class="axm-axis-meta">Sin ejes disponibles.</div>'
        rows: List[str] = []
        for axis in axes:
            rows.append(
                '<button class="axm-axis-btn" type="button">'
                f'<span><strong>{escape(axis.nombre or "Eje sin nombre")}</strong>'
                f'<div class="axm-axis-meta">{escape(axis.codigo or "Sin código")} • {escape(axis.lider_departamento or "Sin líder")}</div></span>'
                f'<span class="axm-count">{len(getattr(axis, "objetivos", []) or [])}</span>'
                '</button>'
            )
        return "".join(rows)
    except Exception:
        return '<div class="axm-axis-meta">No se pudo cargar ejes iniciales.</div>'
    finally:
        db.close()


def _build_initial_poa_grid_html() -> str:
    _bind_core_symbols()
    db = SessionLocal()
    try:
        objectives = (
            db.query(StrategicObjectiveConfig)
            .order_by(StrategicObjectiveConfig.orden.asc(), StrategicObjectiveConfig.id.asc())
            .all()
        )
        if not objectives:
            return '<div class="poa-obj-card"><h4>Sin objetivos</h4><div class="meta">No hay objetivos para mostrar.</div></div>'
        axis_map = {int(axis.id): str(axis.nombre or "Sin eje") for axis in db.query(StrategicAxisConfig).all()}
        grouped: Dict[str, List[StrategicObjectiveConfig]] = {}
        for obj in objectives:
            axis_name = axis_map.get(int(obj.eje_id or 0), "Sin eje")
            grouped.setdefault(axis_name, []).append(obj)
        columns: List[str] = []
        for axis_name in sorted(grouped.keys()):
            cards = []
            for obj in grouped[axis_name]:
                cards.append(
                    '<article class="poa-obj-card">'
                    f'<h4>{escape(obj.nombre or "Objetivo sin nombre")}</h4>'
                    f'<div class="meta">Hito: {escape(obj.hito or "N/D")}</div>'
                    f'<span class="code">{escape(obj.codigo or "OBJ")}</span>'
                    '</article>'
                )
            columns.append(
                '<section class="poa-axis-col">'
                f'<header class="poa-axis-head"><h3 class="poa-axis-title">{escape(axis_name)}</h3></header>'
                f'<div class="poa-axis-cards">{"".join(cards)}</div>'
                '</section>'
            )
        return "".join(columns)
    except Exception:
        return '<div class="poa-obj-card"><h4>Error</h4><div class="meta">No se pudo cargar POA inicial.</div></div>'
    finally:
        db.close()


def _build_strategic_progress_summary(db) -> Dict[str, Any]:
    total_activities = int(db.execute(text("SELECT COUNT(*) FROM poa_activities")).scalar() or 0)
    # Completadas: entrega_estado = 'aprobada' o 'declarada'
    completed_activities = int(
        db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM poa_activities
                WHERE lower(COALESCE(entrega_estado, '')) IN ('aprobada', 'declarada')
                """
            )
        ).scalar()
        or 0
    )
    # Atrasadas: fecha_final ya pasó y no están completadas
    overdue_activities = int(
        db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM poa_activities
                WHERE COALESCE(fecha_final, '') <> ''
                  AND date(fecha_final) < date('now')
                  AND lower(COALESCE(entrega_estado, '')) NOT IN ('aprobada', 'declarada')
                """
            )
        ).scalar()
        or 0
    )
    # Avance estimado: completadas=100%, en_revision=50%, resto=0%
    avg_progress = 0.0
    if total_activities > 0:
        en_revision = int(
            db.execute(
                text(
                    "SELECT COUNT(*) FROM poa_activities WHERE lower(COALESCE(entrega_estado, '')) = 'pendiente'"
                )
            ).scalar()
            or 0
        )
        avg_progress = round(
            (completed_activities * 100 + en_revision * 50) / total_activities, 2
        )
    return {
        "activities_total": total_activities,
        "activities_completed": completed_activities,
        "activities_overdue": overdue_activities,
        "progress_avg": avg_progress,
        "generated_at": datetime.utcnow().isoformat(),
    }


def _build_strategic_ia_payload(db) -> Dict[str, Any]:
    _ensure_strategic_identity_table(db)
    db.commit()
    identity_rows = db.execute(
        text(
            "SELECT bloque, payload FROM strategic_identity_config "
            "WHERE bloque IN ('mision','vision','valores','fundamentacion','base_ia_extra','base_ia_weekly_meta')"
        )
    ).fetchall()
    payload_map = {str(row[0] or "").strip().lower(): str(row[1] or "") for row in identity_rows}

    def _parse_lines(block: str, prefix: str) -> List[Dict[str, str]]:
        raw = payload_map.get(block, "[]")
        try:
            data = json.loads(raw)
        except Exception:
            data = []
        return _normalize_identity_lines(data, prefix)

    mision = _parse_lines("mision", "m")
    vision = _parse_lines("vision", "v")
    valores = _parse_lines("valores", "val")
    try:
        foundation_payload = json.loads(payload_map.get("fundamentacion", "{}") or "{}")
    except Exception:
        foundation_payload = {}
    try:
        extra_payload = json.loads(payload_map.get("base_ia_extra", "{}") or "{}")
    except Exception:
        extra_payload = {}
    try:
        weekly_meta_payload = json.loads(payload_map.get("base_ia_weekly_meta", "{}") or "{}")
    except Exception:
        weekly_meta_payload = {}
    fundamentacion_html = _normalize_foundation_text(foundation_payload.get("texto"))
    fundamentacion_texto = re.sub(r"<[^>]+>", " ", str(fundamentacion_html or ""))
    fundamentacion_texto = re.sub(r"\s+", " ", fundamentacion_texto).strip()
    contenido_adicional = str((extra_payload if isinstance(extra_payload, dict) else {}).get("texto") or "").strip()
    avance_resumen = _build_strategic_progress_summary(db)
    weekly_meta = weekly_meta_payload if isinstance(weekly_meta_payload, dict) else {}

    axes = (
        db.query(StrategicAxisConfig)
        .filter(StrategicAxisConfig.is_active == True)
        .order_by(StrategicAxisConfig.orden.asc(), StrategicAxisConfig.id.asc())
        .all()
    )
    if not axes:
        axes = (
            db.query(StrategicAxisConfig)
            .order_by(StrategicAxisConfig.orden.asc(), StrategicAxisConfig.id.asc())
            .all()
        )
    axis_data = [_serialize_strategic_axis(axis) for axis in axes]
    return {
        "identidad": {
            "mision": mision,
            "vision": vision,
            "valores": valores,
        },
        "fundamentacion": {
            "html": fundamentacion_html,
            "texto_plano": fundamentacion_texto,
        },
        "contenido_adicional": {
            "texto": contenido_adicional,
        },
        "avance": avance_resumen,
        "cron_semanal": {
            "activo": True,
            "intervalo_dias": int(weekly_meta.get("interval_days") or 7),
            "ultima_actualizacion": str(weekly_meta.get("last_refresh_at") or ""),
            "proxima_actualizacion": str(weekly_meta.get("next_refresh_at") or ""),
            "estado": str(weekly_meta.get("last_status") or ""),
            "error": str(weekly_meta.get("last_error") or ""),
        },
        "ejes": axis_data,
        "resumen": {
            "total_ejes": len(axis_data),
            "total_objetivos": sum(len(axis.get("objetivos") or []) for axis in axis_data),
        },
    }


def _build_strategic_ia_html(payload: Dict[str, Any]) -> str:
    identidad = payload.get("identidad", {}) if isinstance(payload, dict) else {}
    mision = identidad.get("mision", []) if isinstance(identidad, dict) else []
    vision = identidad.get("vision", []) if isinstance(identidad, dict) else []
    valores = identidad.get("valores", []) if isinstance(identidad, dict) else []
    fundamentacion = payload.get("fundamentacion", {}) if isinstance(payload, dict) else {}
    fundamentacion_html = str((fundamentacion or {}).get("html") or "")
    contenido_adicional = payload.get("contenido_adicional", {}) if isinstance(payload, dict) else {}
    contenido_adicional_texto = str((contenido_adicional or {}).get("texto") or "")
    avance = payload.get("avance", {}) if isinstance(payload, dict) else {}
    cron = payload.get("cron_semanal", {}) if isinstance(payload, dict) else {}
    ejes = payload.get("ejes", []) if isinstance(payload, dict) else []
    payload_json = json.dumps(payload, ensure_ascii=False, indent=2)
    fundamentacion_block = fundamentacion_html or "<p>Sin fundamentación registrada.</p>"

    def _render_lines(rows: List[Dict[str, str]]) -> str:
        if not rows:
            return "<p>Sin información.</p>"
        return "<ul>" + "".join(
            f"<li><strong>{escape(str(item.get('code') or '').upper())}</strong>: {escape(str(item.get('text') or ''))}</li>"
            for item in rows
        ) + "</ul>"

    axes_html = []
    for axis in ejes:
        axis_name = escape(str(axis.get("nombre") or "Eje sin nombre"))
        axis_code = escape(str(axis.get("codigo") or ""))
        objectives = axis.get("objetivos") or []
        objectives_html = "".join(
            (
                "<li>"
                f"<strong>{escape(str(obj.get('codigo') or 'OBJ'))}</strong> · "
                f"{escape(str(obj.get('nombre') or 'Objetivo sin nombre'))}"
                "</li>"
            )
            for obj in objectives
        ) or "<li>Sin objetivos registrados.</li>"
        axes_html.append(
            "<article>"
            f"<h4>{axis_name}</h4>"
            f"<div>Código: {axis_code}</div>"
            f"<ul>{objectives_html}</ul>"
            "</article>"
        )
    axes_block = "".join(axes_html) if axes_html else "<p>Sin ejes registrados.</p>"

    return (
        "<section>"
        "<section>"
        "<h3>Base IA · Estrategia y táctica</h3>"
        "<p>Fuente consolidada para consulta de IA: identidad, fundamentación, ejes y objetivos.</p>"
        "</section>"
        "<section>"
        "<h4>Identidad</h4>"
        "<h5>Misión</h5>"
        f"{_render_lines(mision)}"
        "<h5>Visión</h5>"
        f"{_render_lines(vision)}"
        "<h5>Valores</h5>"
        f"{_render_lines(valores)}"
        "</section>"
        "<section>"
        "<h4>Fundamentación</h4>"
        f"<div>{fundamentacion_block}</div>"
        "</section>"
        "<section>"
        "<h4>Ejes y objetivos</h4>"
        f"<div>{axes_block}</div>"
        "</section>"
        "<section>"
        "<h4>Lógica de avance</h4>"
        f"<p>Actividades: <b>{int((avance or {}).get('activities_total') or 0)}</b> · "
        f"Completadas: <b>{int((avance or {}).get('activities_completed') or 0)}</b> · "
        f"Vencidas: <b>{int((avance or {}).get('activities_overdue') or 0)}</b> · "
        f"Avance promedio: <b>{float((avance or {}).get('progress_avg') or 0):.2f}%</b></p>"
        f"<p>Corte: {escape(str((avance or {}).get('generated_at') or ''))}</p>"
        "</section>"
        "<section>"
        "<h4>Cron semanal (renovación automática)</h4>"
        f"<p>Intervalo: <b>{int((cron or {}).get('intervalo_dias') or 7)} días</b> · "
        f"Última actualización: <b>{escape(str((cron or {}).get('ultima_actualizacion') or 'N/D'))}</b> · "
        f"Próxima: <b>{escape(str((cron or {}).get('proxima_actualizacion') or 'N/D'))}</b></p>"
        f"<p>Estado: {escape(str((cron or {}).get('estado') or 'sin_ejecucion'))}</p>"
        "<button type='button' id='base-ia-weekly-refresh'>Actualizar ahora (reemplaza contenido previo)</button>"
        "<span id='base-ia-weekly-refresh-status'></span>"
        "<script>"
        "(function(){"
        "  const btn=document.getElementById('base-ia-weekly-refresh');"
        "  const st=document.getElementById('base-ia-weekly-refresh-status');"
        "  if(!btn||!st){return;}"
        "  btn.addEventListener('click', async function(){"
        "    btn.disabled=true;"
        "    st.textContent='Actualizando...';"
        "    try{"
        "      const res=await fetch('/api/v1/ia/strategic/weekly-refresh',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({force:true})});"
        "      const data=await res.json();"
        "      if(!res.ok||!data||data.success!==true){throw new Error((data&&data.error)||'No se pudo actualizar');}"
        "      st.textContent='Actualización semanal ejecutada. Recarga la página para ver nuevos metadatos.';"
        "    }catch(err){"
        "      st.textContent=(err&&err.message)?err.message:'Error al actualizar';"
        "    }finally{btn.disabled=false;}"
        "  });"
        "})();"
        "</script>"
        "</section>"
        "<section>"
        "<h4>Payload estructurado (JSON)</h4>"
        f"<pre>{escape(payload_json)}</pre>"
        "</section>"
        "<section>"
        "<h4>Contenido adicional para IA (editable)</h4>"
        "<p>Este bloque se usa como contexto adicional en Conversaciones IA.</p>"
        f"<textarea id='base-ia-extra-text'>{escape(contenido_adicional_texto)}</textarea>"
        "<div>"
        "<button type='button' id='base-ia-extra-save'>Guardar contenido adicional</button>"
        "<span id='base-ia-extra-status'></span>"
        "</div>"
        "<script>"
        "(function(){"
        "  const btn=document.getElementById('base-ia-extra-save');"
        "  const txt=document.getElementById('base-ia-extra-text');"
        "  const st=document.getElementById('base-ia-extra-status');"
        "  if(!btn||!txt||!st){return;}"
        "  btn.addEventListener('click', async function(){"
        "    btn.disabled=true;"
        "    st.textContent='Guardando...';"
        "    try{"
        "      const res=await fetch('/api/estrategia-tactica/base-ia/contenido',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({texto:String(txt.value||'')})});"
        "      const data=await res.json();"
        "      if(!res.ok||!data||data.success!==true){"
        "        throw new Error((data&&data.error)||'No se pudo guardar');"
        "      }"
        "      st.textContent='Guardado correctamente';"
        "    }catch(err){"
        "      st.textContent=(err&&err.message)?err.message:'Error al guardar';"
        "    }finally{"
        "      btn.disabled=false;"
        "    }"
        "  });"
        "})();"
        "</script>"
        "</section>"
        "</section>"
    )


def _load_colab_meta() -> Dict[str, Dict[str, Any]]:
    try:
        if not _COLAB_META_PATH.exists():
            return {}
        raw = json.loads(_COLAB_META_PATH.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _normalize_poa_access_level(value: Any) -> str:
    raw = str(value or "").strip().lower()
    return "todas_tareas" if raw == "todas_tareas" else "mis_tareas"


def _poa_access_level_for_request(request: Request, db) -> str:
    _bind_core_symbols()
    if _is_request_admin_like(request, db):
        return "todas_tareas"
    user = _current_user_record(request, db)
    if not user or not getattr(user, "id", None):
        return "mis_tareas"
    meta = _load_colab_meta()
    entry = meta.get(str(int(user.id))) if isinstance(meta, dict) else None
    return _normalize_poa_access_level((entry or {}).get("poa_access_level", "mis_tareas"))


def _compose_axis_code(base_code: str, order_value: int) -> str:
    raw_prefix = (base_code or "").strip().lower()
    safe_prefix = "".join(ch for ch in raw_prefix if ch.isalnum()) or "m1"
    safe_order = int(order_value or 0)
    if safe_order <= 0:
        safe_order = 1
    return f"{safe_prefix}-{safe_order:02d}"


def _is_request_admin_like(request: Request, db) -> bool:
    _bind_core_symbols()
    if is_admin_or_superadmin(request):
        return True
    # Fallback: si la sesión/cookie no trae rol correcto, usamos el rol persistido del usuario.
    user = _current_user_record(request, db)
    if not user:
        return False
    user_role = ""
    try:
        user_role = normalize_role_name(str(_resolve_user_role_name(db, user) or ""))
    except Exception:
        user_role = normalize_role_name(str(getattr(user, "role", "") or ""))
    return user_role in {"administrador", "superadministrador"}


def _compose_objective_code(axis_code: str, order_value: int) -> str:
    raw_axis = (axis_code or "").strip().lower()
    axis_parts = [part for part in raw_axis.split("-") if part]
    if len(axis_parts) >= 2:
        axis_prefix = f"{axis_parts[0]}-{axis_parts[1]}"
    elif axis_parts:
        axis_prefix = f"{axis_parts[0]}-01"
    else:
        axis_prefix = "m1-01"
    safe_order = int(order_value or 0)
    if safe_order <= 0:
        safe_order = 1
    return f"{axis_prefix}-{safe_order:02d}"


def _collaborator_belongs_to_department(db, collaborator_name: str, department: str) -> bool:
    name = (collaborator_name or "").strip()
    dep = (department or "").strip()
    if not name or not dep:
        return False
    exists = (
        db.query(Usuario.id)
        .filter(Usuario.nombre == name, Usuario.departamento == dep)
        .first()
    )
    return bool(exists)


MAX_SUBTASK_DEPTH = 4
VALID_ACTIVITY_PERIODICITIES = {
    "diaria",
    "semanal",
    "quincenal",
    "mensual",
    "bimensual",
    "cada_xx_dias",
}


def _ensure_strategic_identity_table(db) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS strategic_identity_config (
              bloque VARCHAR(20) PRIMARY KEY,
              payload TEXT NOT NULL DEFAULT '[]',
              updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )


def _normalize_identity_lines(raw: Any, prefix: str) -> List[Dict[str, str]]:
    rows = raw if isinstance(raw, list) else []
    clean: List[Dict[str, str]] = []
    for idx, item in enumerate(rows):
        if not isinstance(item, dict):
            continue
        code_raw = str(item.get("code") or "").strip().lower()
        text_raw = str(item.get("text") or "").strip()
        safe_code = "".join(ch for ch in code_raw if ch.isalnum()) or f"{prefix}{idx + 1}"
        clean.append({"code": safe_code, "text": text_raw})
    if not clean:
        clean = [{"code": f"{prefix}1", "text": ""}]
    return clean


def _normalize_foundation_text(raw: Any) -> str:
    return str(raw or "").strip()


def _ensure_objective_kpi_table(db) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS strategic_objective_kpis (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              objective_id INTEGER NOT NULL,
              nombre VARCHAR(255) NOT NULL DEFAULT '',
              proposito TEXT NOT NULL DEFAULT '',
              formula TEXT NOT NULL DEFAULT '',
              periodicidad VARCHAR(100) NOT NULL DEFAULT '',
              estandar VARCHAR(20) NOT NULL DEFAULT '',
              referencia VARCHAR(120) NOT NULL DEFAULT '',
              orden INTEGER NOT NULL DEFAULT 0
            )
            """
        )
    )
    # Backfill para instalaciones existentes sin la columna de referencia.
    try:
        cols = db.execute(text("PRAGMA table_info(strategic_objective_kpis)")).fetchall()
        col_names = {str(col[1]).strip().lower() for col in cols if len(col) > 1}
        if "referencia" not in col_names:
            db.execute(
                text(
                    "ALTER TABLE strategic_objective_kpis ADD COLUMN referencia VARCHAR(120) NOT NULL DEFAULT ''"
                )
            )
    except Exception:
        # Evita romper el flujo si la BD no soporta PRAGMA/ALTER esperado.
        pass


def _normalize_kpi_items(raw: Any) -> List[Dict[str, str]]:
    rows = raw if isinstance(raw, list) else []
    allowed = {"mayor", "menor", "entre", "igual"}
    cleaned: List[Dict[str, str]] = []
    for idx, item in enumerate(rows, start=1):
        if not isinstance(item, dict):
            continue
        nombre = str(item.get("nombre") or "").strip()
        if not nombre:
            continue
        estandar = str(item.get("estandar") or "").strip().lower()
        if estandar not in allowed:
            estandar = ""
        referencia = str(item.get("referencia") or "").strip()
        cleaned.append(
            {
                "nombre": nombre,
                "proposito": str(item.get("proposito") or "").strip(),
                "formula": str(item.get("formula") or "").strip(),
                "periodicidad": str(item.get("periodicidad") or "").strip(),
                "estandar": estandar,
                "referencia": referencia,
                "orden": idx,
            }
        )
    return cleaned


def _kpis_by_objective_ids(db, objective_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    result: Dict[int, List[Dict[str, Any]]] = {}
    if not objective_ids:
        return result
    _ensure_objective_kpi_table(db)
    db.commit()
    placeholders = ", ".join([f":id_{idx}" for idx, _ in enumerate(objective_ids)])
    sql = text(
        f"""
        SELECT id, objective_id, nombre, proposito, formula, periodicidad, estandar, referencia, orden
        FROM strategic_objective_kpis
        WHERE objective_id IN ({placeholders})
        ORDER BY objective_id ASC, orden ASC, id ASC
        """
    )
    params = {f"id_{idx}": int(obj_id) for idx, obj_id in enumerate(objective_ids)}
    rows = db.execute(sql, params).fetchall()
    for row in rows:
        objective_id = int(row[1] or 0)
        if objective_id <= 0:
            continue
        result.setdefault(objective_id, []).append(
            {
                "id": int(row[0] or 0),
                "nombre": str(row[2] or ""),
                "proposito": str(row[3] or ""),
                "formula": str(row[4] or ""),
                "periodicidad": str(row[5] or ""),
                "estandar": str(row[6] or ""),
                "referencia": str(row[7] or ""),
                "orden": int(row[8] or 0),
            }
        )
    return result


def _replace_objective_kpis(db, objective_id: int, items: Any) -> None:
    clean = _normalize_kpi_items(items)
    _ensure_objective_kpi_table(db)
    db.execute(text("DELETE FROM strategic_objective_kpis WHERE objective_id = :oid"), {"oid": int(objective_id)})
    for item in clean:
        db.execute(
            text(
                """
                INSERT INTO strategic_objective_kpis (
                  objective_id, nombre, proposito, formula, periodicidad, estandar, referencia, orden
                ) VALUES (
                  :objective_id, :nombre, :proposito, :formula, :periodicidad, :estandar, :referencia, :orden
                )
                """
            ),
            {
                "objective_id": int(objective_id),
                "nombre": item["nombre"],
                "proposito": item["proposito"],
                "formula": item["formula"],
                "periodicidad": item["periodicidad"],
                "estandar": item["estandar"],
                "referencia": item["referencia"],
                "orden": int(item["orden"]),
            },
        )


def _delete_objective_kpis(db, objective_id: int) -> None:
    _ensure_objective_kpi_table(db)
    db.execute(text("DELETE FROM strategic_objective_kpis WHERE objective_id = :oid"), {"oid": int(objective_id)})


def _ensure_objective_milestone_table(db) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS strategic_objective_milestones (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              objective_id INTEGER NOT NULL,
              nombre VARCHAR(255) NOT NULL DEFAULT '',
              logrado INTEGER NOT NULL DEFAULT 0,
              fecha_realizacion DATE,
              orden INTEGER NOT NULL DEFAULT 0
            )
            """
        )
    )
    try:
        cols = db.execute(text("PRAGMA table_info(strategic_objective_milestones)")).fetchall()
        col_names = {str(col[1]).strip().lower() for col in cols if len(col) > 1}
        if "logrado" not in col_names:
            db.execute(
                text(
                    "ALTER TABLE strategic_objective_milestones ADD COLUMN logrado INTEGER NOT NULL DEFAULT 0"
                )
            )
        if "fecha_realizacion" not in col_names:
            db.execute(
                text(
                    "ALTER TABLE strategic_objective_milestones ADD COLUMN fecha_realizacion DATE"
                )
            )
    except Exception:
        pass


def _normalize_milestone_items(raw: Any) -> List[Dict[str, Any]]:
    rows = raw if isinstance(raw, list) else []
    cleaned: List[Dict[str, Any]] = []
    for idx, item in enumerate(rows, start=1):
        if isinstance(item, dict):
            nombre = str(item.get("nombre") or item.get("text") or "").strip()
            logrado = bool(item.get("logrado"))
            fecha_realizacion = str(item.get("fecha_realizacion") or "").strip()
        else:
            nombre = str(item or "").strip()
            logrado = False
            fecha_realizacion = ""
        if not nombre:
            continue
        cleaned.append({"nombre": nombre, "logrado": logrado, "fecha_realizacion": fecha_realizacion, "orden": idx})
    return cleaned


def _milestones_by_objective_ids(db, objective_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    result: Dict[int, List[Dict[str, Any]]] = {}
    if not objective_ids:
        return result
    _ensure_objective_milestone_table(db)
    db.commit()
    placeholders = ", ".join([f":id_{idx}" for idx, _ in enumerate(objective_ids)])
    sql = text(
        f"""
        SELECT id, objective_id, nombre, logrado, fecha_realizacion, orden
        FROM strategic_objective_milestones
        WHERE objective_id IN ({placeholders})
        ORDER BY objective_id ASC, orden ASC, id ASC
        """
    )
    params = {f"id_{idx}": int(obj_id) for idx, obj_id in enumerate(objective_ids)}
    rows = db.execute(sql, params).fetchall()
    for row in rows:
        objective_id = int(row[1] or 0)
        if objective_id <= 0:
            continue
        result.setdefault(objective_id, []).append(
            {
                "id": int(row[0] or 0),
                "nombre": str(row[2] or ""),
                "logrado": bool(row[3]),
                "fecha_realizacion": str(row[4] or ""),
                "orden": int(row[5] or 0),
            }
        )
    return result


def _replace_objective_milestones(db, objective_id: int, items: Any) -> List[Dict[str, Any]]:
    clean = _normalize_milestone_items(items)
    _ensure_objective_milestone_table(db)
    db.execute(text("DELETE FROM strategic_objective_milestones WHERE objective_id = :oid"), {"oid": int(objective_id)})
    for item in clean:
        db.execute(
            text(
                """
                INSERT INTO strategic_objective_milestones (objective_id, nombre, logrado, fecha_realizacion, orden)
                VALUES (:objective_id, :nombre, :logrado, :fecha_realizacion, :orden)
                """
            ),
            {
                "objective_id": int(objective_id),
                "nombre": item["nombre"],
                "logrado": 1 if item.get("logrado") else 0,
                "fecha_realizacion": item.get("fecha_realizacion") or None,
                "orden": int(item["orden"]),
            },
        )
    return clean


def _delete_objective_milestones(db, objective_id: int) -> None:
    _ensure_objective_milestone_table(db)
    db.execute(text("DELETE FROM strategic_objective_milestones WHERE objective_id = :oid"), {"oid": int(objective_id)})


def _ensure_poa_budget_table(db) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS poa_activity_budgets (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              activity_id INTEGER NOT NULL,
              tipo VARCHAR(120) NOT NULL DEFAULT '',
              rubro VARCHAR(255) NOT NULL DEFAULT '',
              mensual NUMERIC NOT NULL DEFAULT 0,
              anual NUMERIC NOT NULL DEFAULT 0,
              autorizado INTEGER NOT NULL DEFAULT 0,
              orden INTEGER NOT NULL DEFAULT 0
            )
            """
        )
    )


def _to_budget_amount(value: Any) -> float:
    raw = str(value or "").strip().replace(",", "")
    if not raw:
        return 0.0
    try:
        num = float(raw)
    except (TypeError, ValueError):
        return 0.0
    if num < 0:
        return 0.0
    return round(num, 2)


def _normalize_budget_items(raw: Any) -> List[Dict[str, Any]]:
    allowed_types = {
        "Sueldos y similares",
        "Honorarios",
        "Gastos de promoción y publicidad",
        "Gastos no deducibles",
        "Gastos en tecnologia",
        "Otros gastos de administración y promoción",
    }
    rows = raw if isinstance(raw, list) else []
    cleaned: List[Dict[str, Any]] = []
    for idx, item in enumerate(rows, start=1):
        if not isinstance(item, dict):
            continue
        tipo = str(item.get("tipo") or "").strip()
        rubro = str(item.get("rubro") or "").strip()
        if not tipo or tipo not in allowed_types:
            continue
        if not rubro:
            continue
        mensual = _to_budget_amount(item.get("mensual"))
        anual = _to_budget_amount(item.get("anual"))
        cleaned.append(
            {
                "tipo": tipo,
                "rubro": rubro,
                "mensual": mensual,
                "anual": anual,
                "autorizado": bool(item.get("autorizado")),
                "orden": idx,
            }
        )
    return cleaned


def _budgets_by_activity_ids(db, activity_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    result: Dict[int, List[Dict[str, Any]]] = {}
    if not activity_ids:
        return result
    _ensure_poa_budget_table(db)
    db.commit()
    placeholders = ", ".join([f":id_{idx}" for idx, _ in enumerate(activity_ids)])
    sql = text(
        f"""
        SELECT id, activity_id, tipo, rubro, mensual, anual, autorizado, orden
        FROM poa_activity_budgets
        WHERE activity_id IN ({placeholders})
        ORDER BY activity_id ASC, orden ASC, id ASC
        """
    )
    params = {f"id_{idx}": int(activity_id) for idx, activity_id in enumerate(activity_ids)}
    rows = db.execute(sql, params).fetchall()
    for row in rows:
        activity_id = int(row[1] or 0)
        if activity_id <= 0:
            continue
        result.setdefault(activity_id, []).append(
            {
                "id": int(row[0] or 0),
                "tipo": str(row[2] or ""),
                "rubro": str(row[3] or ""),
                "mensual": float(row[4] or 0),
                "anual": float(row[5] or 0),
                "autorizado": bool(row[6]),
                "orden": int(row[7] or 0),
            }
        )
    return result


def _replace_activity_budgets(db, activity_id: int, items: Any) -> List[Dict[str, Any]]:
    clean = _normalize_budget_items(items)
    _ensure_poa_budget_table(db)
    db.execute(text("DELETE FROM poa_activity_budgets WHERE activity_id = :aid"), {"aid": int(activity_id)})
    for item in clean:
        db.execute(
            text(
                """
                INSERT INTO poa_activity_budgets (
                  activity_id, tipo, rubro, mensual, anual, autorizado, orden
                ) VALUES (
                  :activity_id, :tipo, :rubro, :mensual, :anual, :autorizado, :orden
                )
                """
            ),
            {
                "activity_id": int(activity_id),
                "tipo": item["tipo"],
                "rubro": item["rubro"],
                "mensual": float(item["mensual"]),
                "anual": float(item["anual"]),
                "autorizado": 1 if item.get("autorizado") else 0,
                "orden": int(item["orden"]),
            },
        )
    return clean


def _delete_activity_budgets(db, activity_id: int) -> None:
    _ensure_poa_budget_table(db)
    db.execute(text("DELETE FROM poa_activity_budgets WHERE activity_id = :aid"), {"aid": int(activity_id)})


def _ensure_poa_deliverables_table(db) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS poa_activity_deliverables (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              activity_id INTEGER NOT NULL,
              nombre VARCHAR(255) NOT NULL DEFAULT '',
              validado INTEGER NOT NULL DEFAULT 0,
              orden INTEGER NOT NULL DEFAULT 0
            )
            """
        )
    )


def _normalize_deliverable_items(raw: Any) -> List[Dict[str, Any]]:
    rows = raw if isinstance(raw, list) else []
    cleaned: List[Dict[str, Any]] = []
    for idx, item in enumerate(rows, start=1):
        if isinstance(item, dict):
            nombre = str(item.get("nombre") or "").strip()
            validado = bool(item.get("validado"))
            try:
                item_id = int(item.get("id") or 0)
            except (TypeError, ValueError):
                item_id = 0
        else:
            nombre = str(item or "").strip()
            validado = False
            item_id = 0
        if not nombre:
            continue
        cleaned.append(
            {
                "id": item_id if item_id > 0 else 0,
                "nombre": nombre,
                "validado": validado,
                "orden": idx,
            }
        )
    return cleaned


def _deliverables_by_activity_ids(db, activity_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    result: Dict[int, List[Dict[str, Any]]] = {}
    if not activity_ids:
        return result
    _ensure_poa_deliverables_table(db)
    db.commit()
    placeholders = ", ".join([f":id_{idx}" for idx, _ in enumerate(activity_ids)])
    sql = text(
        f"""
        SELECT id, activity_id, nombre, validado, orden
        FROM poa_activity_deliverables
        WHERE activity_id IN ({placeholders})
        ORDER BY activity_id ASC, orden ASC, id ASC
        """
    )
    params = {f"id_{idx}": int(activity_id) for idx, activity_id in enumerate(activity_ids)}
    rows = db.execute(sql, params).fetchall()
    for row in rows:
        activity_id = int(row[1] or 0)
        if activity_id <= 0:
            continue
        result.setdefault(activity_id, []).append(
            {
                "id": int(row[0] or 0),
                "nombre": str(row[2] or ""),
                "validado": bool(row[3]),
                "orden": int(row[4] or 0),
            }
        )
    return result


def _replace_activity_deliverables(db, activity_id: int, items: Any) -> List[Dict[str, Any]]:
    clean = _normalize_deliverable_items(items)
    _ensure_poa_deliverables_table(db)
    db.execute(text("DELETE FROM poa_activity_deliverables WHERE activity_id = :aid"), {"aid": int(activity_id)})
    for item in clean:
        db.execute(
            text(
                """
                INSERT INTO poa_activity_deliverables (
                  activity_id, nombre, validado, orden
                ) VALUES (
                  :activity_id, :nombre, :validado, :orden
                )
                """
            ),
            {
                "activity_id": int(activity_id),
                "nombre": item["nombre"],
                "validado": 1 if item.get("validado") else 0,
                "orden": int(item["orden"]),
            },
        )
    return clean


def _delete_activity_deliverables(db, activity_id: int) -> None:
    _ensure_poa_deliverables_table(db)
    db.execute(text("DELETE FROM poa_activity_deliverables WHERE activity_id = :aid"), {"aid": int(activity_id)})


def _ensure_poa_subactivity_recurrence_columns(db) -> None:
    try:
        cols = db.execute(text("PRAGMA table_info(poa_subactivities)")).fetchall()
        col_names = {str(col[1]).strip().lower() for col in cols if len(col) > 1}
        if "recurrente" not in col_names:
            db.execute(
                text(
                    "ALTER TABLE poa_subactivities ADD COLUMN recurrente INTEGER NOT NULL DEFAULT 0"
                )
            )
        if "periodicidad" not in col_names:
            db.execute(
                text(
                    "ALTER TABLE poa_subactivities ADD COLUMN periodicidad VARCHAR(50) NOT NULL DEFAULT ''"
                )
            )
        if "cada_xx_dias" not in col_names:
            db.execute(
                text(
                    "ALTER TABLE poa_subactivities ADD COLUMN cada_xx_dias INTEGER"
                )
            )
        db.commit()
    except Exception:
        db.rollback()


def _ensure_activity_milestone_link_table(db) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS poa_activity_milestone_links (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              activity_id INTEGER NOT NULL,
              milestone_id INTEGER NOT NULL,
              orden INTEGER NOT NULL DEFAULT 0
            )
            """
        )
    )


def _normalize_impacted_milestone_ids(raw: Any) -> List[int]:
    rows = raw if isinstance(raw, list) else []
    clean: List[int] = []
    for value in rows:
        try:
            milestone_id = int(value)
        except (TypeError, ValueError):
            continue
        if milestone_id > 0 and milestone_id not in clean:
            clean.append(milestone_id)
    return clean


def _activity_milestones_by_activity_ids(db, activity_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    result: Dict[int, List[Dict[str, Any]]] = {}
    if not activity_ids:
        return result
    _ensure_objective_milestone_table(db)
    _ensure_activity_milestone_link_table(db)
    db.commit()
    placeholders = ", ".join([f":id_{idx}" for idx, _ in enumerate(activity_ids)])
    sql = text(
        f"""
        SELECT l.activity_id, m.id, m.nombre, l.orden
        FROM poa_activity_milestone_links l
        JOIN strategic_objective_milestones m ON m.id = l.milestone_id
        WHERE l.activity_id IN ({placeholders})
        ORDER BY l.activity_id ASC, l.orden ASC, l.id ASC
        """
    )
    params = {f"id_{idx}": int(activity_id) for idx, activity_id in enumerate(activity_ids)}
    rows = db.execute(sql, params).fetchall()
    for row in rows:
        activity_id = int(row[0] or 0)
        if activity_id <= 0:
            continue
        result.setdefault(activity_id, []).append(
            {
                "id": int(row[1] or 0),
                "nombre": str(row[2] or ""),
                "orden": int(row[3] or 0),
            }
        )
    return result


def _replace_activity_milestone_links(db, activity_id: int, milestone_ids: Any) -> List[int]:
    clean_ids = _normalize_impacted_milestone_ids(milestone_ids)
    _ensure_activity_milestone_link_table(db)
    db.execute(text("DELETE FROM poa_activity_milestone_links WHERE activity_id = :aid"), {"aid": int(activity_id)})
    for idx, milestone_id in enumerate(clean_ids, start=1):
        db.execute(
            text(
                """
                INSERT INTO poa_activity_milestone_links (activity_id, milestone_id, orden)
                VALUES (:activity_id, :milestone_id, :orden)
                """
            ),
            {
                "activity_id": int(activity_id),
                "milestone_id": int(milestone_id),
                "orden": idx,
            },
        )
    return clean_ids


def _delete_activity_milestone_links(db, activity_id: int) -> None:
    _ensure_activity_milestone_link_table(db)
    db.execute(text("DELETE FROM poa_activity_milestone_links WHERE activity_id = :aid"), {"aid": int(activity_id)})

STRATEGIC_POA_CSV_HEADERS = [
    "tipo_registro",
    "axis_codigo",
    "axis_nombre",
    "axis_lider_departamento",
    "axis_responsabilidad_directa",
    "axis_descripcion",
    "axis_orden",
    "objective_codigo",
    "objective_nombre",
    "objective_hito",
    "objective_lider",
    "objective_fecha_inicial",
    "objective_fecha_final",
    "objective_descripcion",
    "objective_orden",
    "activity_codigo",
    "activity_nombre",
    "activity_responsable",
    "activity_entregable",
    "activity_fecha_inicial",
    "activity_fecha_final",
    "activity_descripcion",
    "activity_recurrente",
    "activity_periodicidad",
    "activity_cada_xx_dias",
    "subactivity_codigo",
    "subactivity_parent_codigo",
    "subactivity_nivel",
    "subactivity_nombre",
    "subactivity_responsable",
    "subactivity_entregable",
    "subactivity_fecha_inicial",
    "subactivity_fecha_final",
    "subactivity_descripcion",
]


def _strategic_poa_template_rows() -> List[Dict[str, str]]:
    return [
        {
            "tipo_registro": "eje",
            "axis_codigo": "m1-01",
            "axis_nombre": "Gobernanza y cumplimiento",
            "axis_lider_departamento": "Dirección",
            "axis_responsabilidad_directa": "Nombre Colaborador",
            "axis_descripcion": "Eje estratégico institucional",
            "axis_orden": "1",
        },
        {
            "tipo_registro": "objetivo",
            "axis_codigo": "m1-01",
            "objective_codigo": "m1-01-01",
            "objective_nombre": "Fortalecer controles y gestión de riesgos",
            "objective_hito": "Modelo de control aprobado",
            "objective_lider": "Nombre Colaborador",
            "objective_fecha_inicial": "2026-01-01",
            "objective_fecha_final": "2026-12-31",
            "objective_descripcion": "Objetivo estratégico anual",
            "objective_orden": "1",
        },
        {
            "tipo_registro": "actividad",
            "objective_codigo": "m1-01-01",
            "activity_codigo": "m1-01-01-aa-bb-cc-dd-ee",
            "activity_nombre": "Implementar matriz de riesgos",
            "activity_responsable": "Nombre Colaborador",
            "activity_entregable": "Matriz de riesgos validada",
            "activity_fecha_inicial": "2026-02-01",
            "activity_fecha_final": "2026-05-30",
            "activity_descripcion": "Actividad POA",
            "activity_recurrente": "no",
            "activity_periodicidad": "",
            "activity_cada_xx_dias": "",
        },
        {
            "tipo_registro": "subactividad",
            "activity_codigo": "m1-01-01-aa-bb-cc-dd-ee",
            "subactivity_codigo": "m1-01-01-aa-bb-cc-dd-ee-01",
            "subactivity_parent_codigo": "",
            "subactivity_nivel": "1",
            "subactivity_nombre": "Levantar riesgos críticos",
            "subactivity_responsable": "Nombre Colaborador",
            "subactivity_entregable": "Inventario de riesgos",
            "subactivity_fecha_inicial": "2026-02-01",
            "subactivity_fecha_final": "2026-02-28",
            "subactivity_descripcion": "Subactividad POA",
        },
    ]


def _strategic_poa_export_rows(db) -> List[Dict[str, str]]:
    _bind_core_symbols()
    rows: List[Dict[str, str]] = []
    axes = (
        db.query(StrategicAxisConfig)
        .filter(StrategicAxisConfig.is_active == True)
        .order_by(StrategicAxisConfig.orden.asc(), StrategicAxisConfig.id.asc())
        .all()
    )
    for axis in axes:
        axis_code = str(axis.codigo or "").strip()
        rows.append(
            {
                "tipo_registro": "eje",
                "axis_codigo": axis_code,
                "axis_nombre": str(axis.nombre or "").strip(),
                "axis_lider_departamento": str(axis.lider_departamento or "").strip(),
                "axis_responsabilidad_directa": str(axis.responsabilidad_directa or "").strip(),
                "axis_descripcion": str(axis.descripcion or "").strip(),
                "axis_orden": str(int(axis.orden or 0)),
            }
        )

        objectives = (
            db.query(StrategicObjectiveConfig)
            .filter(
                StrategicObjectiveConfig.is_active == True,
                StrategicObjectiveConfig.eje_id == axis.id,
            )
            .order_by(StrategicObjectiveConfig.orden.asc(), StrategicObjectiveConfig.id.asc())
            .all()
        )
        for objective in objectives:
            objective_code = str(objective.codigo or "").strip()
            rows.append(
                {
                    "tipo_registro": "objetivo",
                    "axis_codigo": axis_code,
                    "objective_codigo": objective_code,
                    "objective_nombre": str(objective.nombre or "").strip(),
                    "objective_hito": str(objective.hito or "").strip(),
                    "objective_lider": str(objective.lider or "").strip(),
                    "objective_fecha_inicial": str(_date_to_iso(objective.fecha_inicial) or ""),
                    "objective_fecha_final": str(_date_to_iso(objective.fecha_final) or ""),
                    "objective_descripcion": str(objective.descripcion or "").strip(),
                    "objective_orden": str(int(objective.orden or 0)),
                }
            )

            activities = (
                db.query(POAActivity)
                .filter(POAActivity.objective_id == objective.id)
                .order_by(POAActivity.id.asc())
                .all()
            )
            for activity in activities:
                activity_code = str(activity.codigo or "").strip()
                rows.append(
                    {
                        "tipo_registro": "actividad",
                        "objective_codigo": objective_code,
                        "activity_codigo": activity_code,
                        "activity_nombre": str(activity.nombre or "").strip(),
                        "activity_responsable": str(activity.responsable or "").strip(),
                        "activity_entregable": str(activity.entregable or "").strip(),
                        "activity_fecha_inicial": str(_date_to_iso(activity.fecha_inicial) or ""),
                        "activity_fecha_final": str(_date_to_iso(activity.fecha_final) or ""),
                        "activity_descripcion": str(activity.descripcion or "").strip(),
                        "activity_recurrente": "si" if bool(getattr(activity, "recurrente", False)) else "no",
                        "activity_periodicidad": str(getattr(activity, "periodicidad", "") or "").strip(),
                        "activity_cada_xx_dias": str(int(getattr(activity, "cada_xx_dias", 0) or 0)),
                    }
                )

                subactivities = (
                    db.query(POASubactivity)
                    .filter(POASubactivity.activity_id == activity.id)
                    .order_by(POASubactivity.nivel.asc(), POASubactivity.id.asc())
                    .all()
                )
                sub_code_map = {int(sub.id): str(sub.codigo or "").strip() for sub in subactivities}
                for sub in subactivities:
                    parent_code = ""
                    parent_id = int(getattr(sub, "parent_id", 0) or 0)
                    if parent_id > 0:
                        parent_code = sub_code_map.get(parent_id, "")
                    rows.append(
                        {
                            "tipo_registro": "subactividad",
                            "activity_codigo": activity_code,
                            "subactivity_codigo": str(sub.codigo or "").strip(),
                            "subactivity_parent_codigo": parent_code,
                            "subactivity_nivel": str(int(getattr(sub, "nivel", 1) or 1)),
                            "subactivity_nombre": str(sub.nombre or "").strip(),
                            "subactivity_responsable": str(sub.responsable or "").strip(),
                            "subactivity_entregable": str(sub.entregable or "").strip(),
                            "subactivity_fecha_inicial": str(_date_to_iso(sub.fecha_inicial) or ""),
                            "subactivity_fecha_final": str(_date_to_iso(sub.fecha_final) or ""),
                            "subactivity_descripcion": str(sub.descripcion or "").strip(),
                        }
                    )
    return rows


def _csv_value(row: Dict[str, Any], key: str) -> str:
    return str((row.get(key) or "")).strip()


def _normalize_import_kind(value: str) -> str:
    raw = str(value or "").strip().lower()
    aliases = {
        "axis": "eje",
        "eje": "eje",
        "objetivo": "objetivo",
        "objective": "objetivo",
        "actividad": "actividad",
        "activity": "actividad",
        "subactividad": "subactividad",
        "subactivity": "subactividad",
    }
    return aliases.get(raw, raw)


def _parse_import_date(value: str) -> Any:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"Fecha inválida '{raw}', use formato YYYY-MM-DD")


def _parse_import_int(value: str, fallback: int = 0) -> int:
    raw = str(value or "").strip()
    if not raw:
        return fallback
    return int(raw)


def _parse_import_bool(value: str) -> bool:
    raw = str(value or "").strip().lower()
    return raw in {"1", "true", "yes", "si", "sí", "on"}


def _descendant_subactivity_ids(db, activity_id: int, root_id: int) -> List[int]:
    rows = (
        db.query(POASubactivity.id, POASubactivity.parent_subactivity_id)
        .filter(POASubactivity.activity_id == activity_id)
        .all()
    )
    children: Dict[int, List[int]] = {}
    for sub_id, parent_id in rows:
        if parent_id is None:
            continue
        children.setdefault(int(parent_id), []).append(int(sub_id))
    collected: List[int] = []
    stack = [int(root_id)]
    while stack:
        current = stack.pop()
        for child in children.get(current, []):
            collected.append(child)
            stack.append(child)
    return collected


def _serialize_poa_subactivity(item: POASubactivity) -> Dict[str, Any]:
    _bind_core_symbols()
    today = datetime.utcnow().date()
    done = bool(item.fecha_final and today >= item.fecha_final)
    return {
        "id": item.id,
        "activity_id": item.activity_id,
        "parent_subactivity_id": item.parent_subactivity_id,
        "nivel": item.nivel or 1,
        "nombre": item.nombre or "",
        "codigo": item.codigo or "",
        "responsable": item.responsable or "",
        "entregable": item.entregable or "",
        "fecha_inicial": _date_to_iso(item.fecha_inicial),
        "fecha_final": _date_to_iso(item.fecha_final),
        "descripcion": item.descripcion or "",
        "recurrente": bool(getattr(item, "recurrente", False)),
        "periodicidad": str(getattr(item, "periodicidad", "") or ""),
        "cada_xx_dias": int(getattr(item, "cada_xx_dias", 0) or 0),
        "avance": 100 if done else 0,
    }


def _serialize_poa_activity(
    item: POAActivity,
    subactivities: List[POASubactivity],
    budget_items: List[Dict[str, Any]] | None = None,
    hitos_impacta: List[Dict[str, Any]] | None = None,
    deliverables: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    _bind_core_symbols()
    today = datetime.utcnow().date()
    if subactivities:
        done_subs = sum(1 for sub in subactivities if sub.fecha_final and today >= sub.fecha_final)
        activity_progress = int(round((done_subs / len(subactivities)) * 100))
    else:
        activity_progress = 100 if _activity_status(item) == "Terminada" else 0
    return {
        "id": item.id,
        "objective_id": item.objective_id,
        "nombre": item.nombre or "",
        "codigo": item.codigo or "",
        "responsable": item.responsable or "",
        "entregable": item.entregable or "",
        "fecha_inicial": _date_to_iso(item.fecha_inicial),
        "fecha_final": _date_to_iso(item.fecha_final),
        "inicio_forzado": bool(item.inicio_forzado),
        "recurrente": bool(item.recurrente),
        "periodicidad": item.periodicidad or "",
        "cada_xx_dias": item.cada_xx_dias or 0,
        "status": _activity_status(item),
        "avance": activity_progress,
        "entrega_estado": item.entrega_estado or "ninguna",
        "entrega_solicitada_por": item.entrega_solicitada_por or "",
        "entrega_solicitada_at": item.entrega_solicitada_at.isoformat() if item.entrega_solicitada_at else "",
        "entrega_aprobada_por": item.entrega_aprobada_por or "",
        "entrega_aprobada_at": item.entrega_aprobada_at.isoformat() if item.entrega_aprobada_at else "",
        "created_by": item.created_by or "",
        "descripcion": item.descripcion or "",
        "budget_items": budget_items or [],
        "hitos_impacta": hitos_impacta or [],
        "entregables": deliverables or [],
        "subactivities": [
            _serialize_poa_subactivity(sub)
            for sub in sorted(subactivities, key=lambda x: ((x.nivel or 1), x.id or 0))
        ],
    }


EJES_ESTRATEGICOS_HTML = dedent("""
    <section class="axm-wrap">

      <article class="axm-intro">
        <section class="axm-track" id="axm-track-board">
          <h4>Tablero de seguimiento</h4>
          <div class="axm-track-grid">
            <article class="axm-track-card"><div class="axm-track-label">Avance global</div><div class="axm-track-value">0%</div></article>
            <article class="axm-track-card"><div class="axm-track-label">Ejes activos</div><div class="axm-track-value">0</div></article>
            <article class="axm-track-card"><div class="axm-track-label">Objetivos</div><div class="axm-track-value">0</div></article>
            <article class="axm-track-card"><div class="axm-track-label">Objetivos al 100%</div><div class="axm-track-value">0</div></article>
          </div>
        </section>
      </article>
      <section class="axm-card" id="axm-plan-header-card">
        <div class="axm-row">
          <div class="axm-field">
            <label for="axm-plan-years">Vigencia del plan (años):</label>
            <select id="axm-plan-years" class="axm-input">
              <option value="1">1</option>
              <option value="2">2</option>
              <option value="3">3</option>
              <option value="4">4</option>
              <option value="5">5</option>
            </select>
          </div>
          <div class="axm-field">
            <label for="axm-plan-start">Inicio del plan:</label>
            <input id="axm-plan-start" class="axm-input" type="date">
          </div>
        </div>
      </section>

      <div class="tabs tabs-lifted w-full flex-wrap axm-tabs" role="tablist" aria-label="Planificación">
        <button type="button" class="tab gap-2 rounded-t-lg axm-tab" data-axm-tab="fundamentacion"><img src="/templates/icon/macroeconomia.svg" alt="" class="tab-icon">Fundamentación</button>
        <button type="button" class="tab gap-2 rounded-t-lg axm-tab" data-axm-tab="identidad"><img src="/templates/icon/identidad.svg" alt="" class="tab-icon">Identidad</button>
        <button type="button" class="tab gap-2 rounded-t-lg tab-active active axm-tab" data-axm-tab="ejes"><img src="/templates/icon/ejes.svg" alt="" class="tab-icon">Ejes estratégicos</button>
        <button type="button" class="tab gap-2 rounded-t-lg axm-tab" data-axm-tab="objetivos"><img src="/templates/icon/objetivos.svg" alt="" class="tab-icon">Objetivos</button>
      </div>
      <div class="axm-global-msg" id="axm-global-msg" aria-live="polite"></div>
      <section class="axm-foundacion" id="axm-foundacion-panel">
        <h3>Fundamentación</h3>
        <p>Registra aquí la fundamentación del plan estratégico.</p>
        <div class="axm-foundacion-toolbar">
          <button type="button" class="axm-foundacion-tool" data-found-cmd="bold">Negrita</button>
          <button type="button" class="axm-foundacion-tool" data-found-cmd="italic">Itálica</button>
          <button type="button" class="axm-foundacion-tool" data-found-cmd="underline">Subrayar</button>
          <button type="button" class="axm-foundacion-tool" data-found-cmd="insertUnorderedList">Lista</button>
          <button type="button" class="axm-foundacion-tool" data-found-cmd="insertOrderedList">Numerada</button>
          <button type="button" class="axm-foundacion-tool" id="axm-foundacion-upload-btn">Subir HTML</button>
          <label class="axm-foundacion-tool">
            <input id="axm-foundacion-show-source" type="checkbox">
            Ver código HTML
          </label>
          <input id="axm-foundacion-upload" type="file" accept=".html,text/html">
        </div>
        <div id="axm-foundacion-editor" class="axm-foundacion-editor" contenteditable="true"></div>
        <textarea id="axm-foundacion-source" class="axm-foundacion-source" placeholder="Código HTML..."></textarea>
        <div class="axm-foundacion-actions">
          <button type="button" class="action-button" id="axm-foundacion-edit" data-hover-label="Editar" aria-label="Editar" title="Editar">
            <img src="/icon/boton/editar.svg" alt="Editar">
            <span class="action-label">Editar</span>
          </button>
          <button type="button" class="action-button" id="axm-foundacion-save" data-hover-label="Guardar" aria-label="Guardar" title="Guardar">
            <img src="/icon/boton/guardar.svg" alt="Guardar">
            <span class="action-label">Guardar</span>
          </button>
        </div>
        <div class="axm-foundacion-msg" id="axm-foundacion-msg" aria-live="polite"></div>
      </section>
      <section class="axm-identidad" id="axm-identidad-panel">
        <details class="axm-id-acc" open>
          <summary>Misión</summary>
          <div class="axm-id-grid">
            <div class="axm-id-left">
              <div class="axm-id-lines" id="axm-mision-lines"></div>
              <button type="button" class="axm-id-add" id="axm-mision-add">Agregar línea</button>
              <div class="axm-id-actions">
                <button type="button" class="action-button" id="axm-mision-edit" data-hover-label="Editar" aria-label="Editar" title="Editar">
                  <img src="/icon/boton/editar.svg" alt="Editar">
                  <span class="action-label">Editar</span>
                </button>
                <button type="button" class="action-button" id="axm-mision-save" data-hover-label="Guardar" aria-label="Guardar" title="Guardar">
                  <img src="/icon/boton/guardar.svg" alt="Guardar">
                  <span class="action-label">Guardar</span>
                </button>
                <button type="button" class="action-button" id="axm-mision-delete" data-hover-label="Eliminar" aria-label="Eliminar" title="Eliminar">
                  <img src="/icon/boton/eliminar.svg" alt="Eliminar">
                  <span class="action-label">Eliminar</span>
                </button>
              </div>
              <div id="axm-mision-hidden"></div>
            </div>
            <div class="axm-id-right">
              <h4>Misión</h4>
              <p class="axm-id-full" id="axm-mision-full"></p>
            </div>
          </div>
        </details>
        <details class="axm-id-acc">
          <summary>Visión</summary>
          <div class="axm-id-grid">
            <div class="axm-id-left">
              <div class="axm-id-lines" id="axm-vision-lines"></div>
              <button type="button" class="axm-id-add" id="axm-vision-add">Agregar línea</button>
              <div class="axm-id-actions">
                <button type="button" class="action-button" id="axm-vision-edit" data-hover-label="Editar" aria-label="Editar" title="Editar">
                  <img src="/icon/boton/editar.svg" alt="Editar">
                  <span class="action-label">Editar</span>
                </button>
                <button type="button" class="action-button" id="axm-vision-save" data-hover-label="Guardar" aria-label="Guardar" title="Guardar">
                  <img src="/icon/boton/guardar.svg" alt="Guardar">
                  <span class="action-label">Guardar</span>
                </button>
                <button type="button" class="action-button" id="axm-vision-delete" data-hover-label="Eliminar" aria-label="Eliminar" title="Eliminar">
                  <img src="/icon/boton/eliminar.svg" alt="Eliminar">
                  <span class="action-label">Eliminar</span>
                </button>
              </div>
              <div id="axm-vision-hidden"></div>
            </div>
            <div class="axm-id-right">
              <h4>Visión</h4>
              <p class="axm-id-full" id="axm-vision-full"></p>
            </div>
          </div>
        </details>
        <details class="axm-id-acc">
          <summary>Valores</summary>
          <div class="axm-id-grid">
            <div class="axm-id-left">
              <div class="axm-id-lines" id="axm-valores-lines"></div>
              <button type="button" class="axm-id-add" id="axm-valores-add">Agregar línea</button>
              <div class="axm-id-actions">
                <button type="button" class="action-button" id="axm-valores-edit" data-hover-label="Editar" aria-label="Editar" title="Editar">
                  <img src="/icon/boton/editar.svg" alt="Editar">
                  <span class="action-label">Editar</span>
                </button>
                <button type="button" class="action-button" id="axm-valores-save" data-hover-label="Guardar" aria-label="Guardar" title="Guardar">
                  <img src="/icon/boton/guardar.svg" alt="Guardar">
                  <span class="action-label">Guardar</span>
                </button>
                <button type="button" class="action-button" id="axm-valores-delete" data-hover-label="Eliminar" aria-label="Eliminar" title="Eliminar">
                  <img src="/icon/boton/eliminar.svg" alt="Eliminar">
                  <span class="action-label">Eliminar</span>
                </button>
              </div>
              <div id="axm-valores-hidden"></div>
            </div>
            <div class="axm-id-right">
              <h4>Valores</h4>
              <p class="axm-id-full" id="axm-valores-full"></p>
            </div>
          </div>
        </details>
      </section>
      <div class="axm-id-msg" id="axm-identidad-msg" aria-live="polite"></div>
      <div class="axm-modal" id="axm-tree-modal" role="dialog" aria-modal="true" aria-labelledby="axm-tree-modal-title">
        <section class="axm-modal-dialog axm-tree-modal-dialog">
          <div class="axm-modal-head">
            <h2 class="axm-title" id="axm-tree-modal-title">Organigrama estratégico</h2>
            <button class="axm-close" id="axm-tree-modal-close" type="button" aria-label="Cerrar">×</button>
          </div>
          <section class="axm-arbol" id="axm-arbol-panel">
            <p class="axm-arbol-sub">Vista organigrama: Misión/Visión como base, líneas por código y ejes vinculados.</p>
            <div class="axm-org-toolbar">
              <span class="axm-arbol-sub">Haz clic en un nodo para abrir su formulario correspondiente.</span>
              <div class="axm-org-zoom">
                <button type="button" id="axm-tree-expand" title="Expandir todo">▾▾</button>
                <button type="button" id="axm-tree-collapse" title="Contraer todo">▸▸</button>
                <button type="button" id="axm-tree-zoom-out" title="Alejar">-</button>
                <button type="button" id="axm-tree-zoom-in" title="Acercar">+</button>
                <button type="button" id="axm-tree-fit" class="axm-org-fit">Ajustar</button>
              </div>
            </div>
            <div id="axm-tree-chart" class="axm-org-chart-wrap"></div>
          </section>
        </section>
      </div>
      <div class="axm-modal" id="axm-gantt-modal" role="dialog" aria-modal="true" aria-labelledby="axm-gantt-modal-title">
        <section class="axm-modal-dialog axm-tree-modal-dialog">
          <div class="axm-modal-head">
            <h2 class="axm-title" id="axm-gantt-modal-title">Vista Gantt del plan estratégico</h2>
            <button class="axm-close" id="axm-gantt-modal-close" type="button" aria-label="Cerrar">×</button>
          </div>
          <div class="axm-gantt-wrap">
            <div class="axm-gantt-legend">
              <span class="axm-gantt-chip"><span class="axm-gantt-dot"></span>Eje estratégico</span>
              <span class="axm-gantt-chip"><span class="axm-gantt-dot"></span>Objetivo estratégico</span>
              <span class="axm-gantt-chip"><span class="axm-gantt-dot"></span>Hoy</span>
            </div>
            <div class="axm-gantt-controls">
              <div class="axm-gantt-actions">
                <button type="button" class="axm-gantt-action" id="axm-gantt-show-all">Mostrar bloques</button>
                <button type="button" class="axm-gantt-action" id="axm-gantt-hide-all">Ocultar bloques</button>
              </div>
              <div class="axm-gantt-blocks" id="axm-gantt-blocks"></div>
            </div>
            <div id="axm-gantt-host" class="axm-gantt-host"></div>
          </div>
        </section>
      </div>
      <section class="axm-tab-panel" id="axm-tab-panel">No tiene acceso, consulte con el administrador</section>
      <section class="axm-card" id="axm-objetivos-panel">
        <h3>Objetivos del eje</h3>
        <div class="axm-obj-layout">
          <aside>
            <h4>Ejes estratégicos</h4>
            <div class="axm-obj-axis-list" id="axm-obj-axis-list"></div>
          </aside>
          <section>
            <div class="axm-actions">
              <h4 id="axm-obj-axis-title">Objetivos</h4>
              <button class="axm-btn primary" id="axm-add-obj" type="button">Agregar objetivo</button>
            </div>
            <div class="axm-obj-list" id="axm-obj-list"></div>
          </section>
        </div>
      </section>

      <div class="axm-grid">
        <aside class="axm-card">
          <h2 class="axm-title">Plan estratégico</h2>
          <p class="axm-sub">Selecciona un eje para editarlo o crea uno nuevo.</p>
          <div class="axm-actions">
            <button class="axm-btn primary" id="axm-add-axis" type="button" onclick="(function(){var m=document.getElementById('axm-axis-modal');if(m){m.classList.add('open');m.style.display='flex';document.body.style.overflow='hidden';}})();">Agregar eje</button>
            <button class="axm-btn" id="axm-download-template" type="button">Descargar plantilla CSV</button>
            <button class="axm-btn" id="axm-import-csv" type="button">Importar CSV estratégico + POA</button>
            <input id="axm-import-csv-file" type="file" accept=".csv,text/csv">
          </div>
          <div class="axm-list" id="axm-axis-list"></div>
        </aside>
      </div>

      <div class="axm-modal" id="axm-axis-modal" role="dialog" aria-modal="true" aria-labelledby="axm-axis-modal-title">
        <section class="axm-modal-dialog">
          <div class="axm-modal-head">
            <h2 class="axm-title" id="axm-axis-modal-title">Gestión de ejes y objetivos</h2>
            <button class="axm-close" id="axm-axis-modal-close" type="button" aria-label="Cerrar">×</button>
          </div>
          <p class="axm-sub">Edita, guarda o elimina ejes estratégicos y sus objetivos.</p>
          <div class="axm-axis-main-row">
            <div class="axm-field">
              <label for="axm-axis-code">Código del eje (xx-yy)</label>
              <input id="axm-axis-code" class="axm-input axm-axis-code-readonly" type="text" readonly>
            </div>
            <div class="axm-field">
              <label for="axm-axis-name">Nombre del eje</label>
              <input id="axm-axis-name" class="axm-input" type="text" placeholder="Ej. Gobernanza y cumplimiento">
            </div>
            <div class="axm-base-grid">
              <div class="axm-field">
                <label for="axm-axis-base-code">Cod base</label>
                <select id="axm-axis-base-code" class="axm-input">
                  <option value="m1">m1</option>
                </select>
              </div>
              <div class="axm-field">
                <label for="axm-axis-base-preview">Texto cod base</label>
                <div id="axm-axis-base-preview" class="axm-base-preview">Selecciona un código para ver su línea asociada.</div>
              </div>
            </div>
          </div>
          <div class="axm-row">
            <div class="axm-field">
              <label for="axm-axis-leader">Líder del eje estratégico</label>
              <select id="axm-axis-leader" class="axm-input">
                <option value="">Selecciona departamento</option>
              </select>
            </div>
            <div class="axm-field">
              <label for="axm-axis-owner">Responsabilidad directa</label>
              <select id="axm-axis-owner" class="axm-input">
                <option value="">Selecciona colaborador</option>
              </select>
            </div>
          </div>
          <div class="axm-row">
            <div class="axm-field">
              <label for="axm-axis-start">Fecha inicial</label>
              <input id="axm-axis-start" class="axm-input" type="date">
            </div>
            <div class="axm-field">
              <label for="axm-axis-end">Fecha final</label>
              <input id="axm-axis-end" class="axm-input" type="date">
            </div>
          </div>
          <div class="axm-field">
            <label for="axm-axis-progress">Avance</label>
            <input id="axm-axis-progress" class="axm-input" type="text" readonly>
          </div>
          <div class="tabs tabs-lifted w-full flex-wrap axm-axis-tabs" role="tablist" aria-label="Eje">
            <button type="button" class="tab rounded-t-lg tab-active active axm-axis-tab" data-axis-tab="desc">Descripción</button>
            <button type="button" class="tab rounded-t-lg axm-axis-tab" data-axis-tab="objs">Objetivos</button>
          </div>
          <section class="axm-axis-panel active" data-axis-panel="desc">
            <div class="axm-field">
              <label for="axm-axis-desc">Descripción</label>
              <textarea id="axm-axis-desc" class="axm-textarea" placeholder="Describe el propósito del eje"></textarea>
            </div>
          </section>
          <section class="axm-axis-panel" data-axis-panel="objs">
            <div class="axm-axis-objectives" id="axm-axis-objectives-list"></div>
          </section>
          <div class="axm-actions">
            <button class="action-button" id="axm-edit-axis" type="button" data-hover-label="Editar" aria-label="Editar" title="Editar">
              <img src="/icon/boton/editar.svg" alt="Editar">
              <span class="action-label">Editar</span>
            </button>
            <button class="action-button" id="axm-save-axis" type="button" data-hover-label="Guardar" aria-label="Guardar" title="Guardar">
              <img src="/icon/boton/guardar.svg" alt="Guardar">
              <span class="action-label">Guardar</span>
            </button>
            <button class="action-button" id="axm-delete-axis" type="button" data-hover-label="Eliminar" aria-label="Eliminar" title="Eliminar">
              <img src="/icon/boton/eliminar.svg" alt="Eliminar">
              <span class="action-label">Eliminar</span>
            </button>
          </div>
          <div class="axm-msg" id="axm-axis-msg" aria-live="polite"></div>
        </section>
      </div>
      <div class="axm-modal" id="axm-obj-modal" role="dialog" aria-modal="true" aria-labelledby="axm-obj-modal-title">
        <section class="axm-modal-dialog">
          <div class="axm-modal-head">
            <h2 class="axm-title" id="axm-obj-modal-title">Objetivo estratégico</h2>
            <button class="axm-close" id="axm-obj-modal-close" type="button" aria-label="Cerrar">×</button>
          </div>
          <div class="axm-obj-form">
            <div class="axm-obj-main-row">
              <div class="axm-field">
                <label for="axm-obj-code">Código</label>
                <input id="axm-obj-code" class="axm-input axm-obj-code-readonly" type="text" placeholder="xx-yy-zz" readonly>
              </div>
              <div class="axm-field">
                <label for="axm-obj-name">Nombre</label>
                <input id="axm-obj-name" class="axm-input" type="text" placeholder="Nombre del objetivo">
              </div>
            </div>
            <div class="axm-field">
              <label for="axm-obj-progress">Avance</label>
              <input id="axm-obj-progress" class="axm-input" type="text" readonly>
            </div>
            <div class="axm-field">
              <label for="axm-obj-leader">Lider</label>
              <select id="axm-obj-leader" class="axm-input">
                <option value="">Selecciona colaborador</option>
              </select>
            </div>
            <div class="axm-row">
              <div class="axm-field">
                <label for="axm-obj-start">Fecha inicial</label>
                <input id="axm-obj-start" class="axm-input" type="date">
              </div>
              <div class="axm-field">
                <label for="axm-obj-end">Fecha final</label>
                <input id="axm-obj-end" class="axm-input" type="date">
              </div>
            </div>
            <div class="tabs tabs-lifted w-full flex-wrap axm-obj-tabs" role="tablist" aria-label="Objetivo">
              <button type="button" class="tab rounded-t-lg tab-active active axm-obj-tab" data-obj-tab="desc">Descripción</button>
              <button type="button" class="tab rounded-t-lg axm-obj-tab" data-obj-tab="hitos">Hitos</button>
              <button type="button" class="tab rounded-t-lg axm-obj-tab" data-obj-tab="kpi">Kpis</button>
              <button type="button" class="tab rounded-t-lg axm-obj-tab" data-obj-tab="acts">Actividades</button>
            </div>
            <section class="axm-obj-panel active" data-obj-panel="desc">
              <div class="axm-field">
                <label for="axm-obj-desc">Descripción</label>
                <textarea id="axm-obj-desc" class="axm-textarea" placeholder="Descripción del objetivo"></textarea>
              </div>
              <div class="axm-kpi-actions">
                <button class="axm-btn" id="axm-obj-suggest-ia" type="button">Sugerir con IA</button>
              </div>
            </section>
            <section class="axm-obj-panel" data-obj-panel="hitos">
              <div class="axm-kpi-form">
                <div class="axm-field full">
                  <label for="axm-hito-name">Hito</label>
                  <input id="axm-hito-name" class="axm-input" type="text" placeholder="Describe el hito">
                </div>
                <div class="axm-field">
                  <label for="axm-hito-date">Fecha de realización</label>
                  <input id="axm-hito-date" class="axm-input" type="date">
                </div>
                <div class="axm-field">
                  <label>
                    <input id="axm-hito-done" type="checkbox">
                    Logrado
                  </label>
                </div>
                <div class="axm-kpi-actions">
                  <button class="axm-btn primary" id="axm-hito-add" type="button">Agregar hito</button>
                  <button class="axm-btn" id="axm-hito-cancel" type="button">Cancelar edición</button>
                </div>
              </div>
              <div class="axm-kpi-hint" id="axm-hito-msg"></div>
              <div class="axm-kpi-list" id="axm-hito-list"></div>
            </section>
            <section class="axm-obj-panel" data-obj-panel="kpi">
              <div class="axm-kpi-form">
                <div class="axm-field full">
                  <label for="axm-kpi-name">Nombre</label>
                  <input id="axm-kpi-name" class="axm-input" type="text" placeholder="Nombre del KPI">
                </div>
                <div class="axm-field full">
                  <label for="axm-kpi-purpose">Propósito</label>
                  <textarea id="axm-kpi-purpose" class="axm-textarea" placeholder="Propósito del KPI"></textarea>
                </div>
                <div class="axm-field full">
                  <label for="axm-kpi-formula">Fórmula</label>
                  <textarea id="axm-kpi-formula" class="axm-textarea" placeholder="Fórmula de cálculo"></textarea>
                </div>
                <div class="axm-field">
                  <label for="axm-kpi-periodicity">Periodicidad</label>
                  <input id="axm-kpi-periodicity" class="axm-input" type="text" placeholder="Mensual, trimestral, anual, etc.">
                </div>
                <div class="axm-field">
                  <label for="axm-kpi-standard">Estándar</label>
                  <select id="axm-kpi-standard" class="axm-input">
                    <option value="">Selecciona estándar</option>
                    <option value="mayor">Mayor</option>
                    <option value="menor">Menor</option>
                    <option value="entre">Entre</option>
                    <option value="igual">Igual</option>
                  </select>
                </div>
                <div class="axm-field">
                  <label for="axm-kpi-reference">Referencia</label>
                  <input id="axm-kpi-reference" class="axm-input" type="text" placeholder="Ej. 8% o 5%-8%">
                </div>
                <div class="axm-kpi-actions">
                  <button class="axm-btn" id="axm-kpi-suggest-ia" type="button">Sugerir con IA</button>
                  <button class="axm-btn primary" id="axm-kpi-add" type="button">Agregar KPI</button>
                  <button class="axm-btn" id="axm-kpi-cancel" type="button">Cancelar edición</button>
                </div>
              </div>
              <div class="axm-kpi-hint" id="axm-kpi-msg"></div>
              <div class="axm-kpi-list" id="axm-kpi-list"></div>
            </section>
            <section class="axm-obj-panel" data-obj-panel="acts">
              <div class="axm-obj-acts" id="axm-obj-acts-list"></div>
            </section>
            <div class="axm-actions">
              <button class="action-button" id="axm-edit-obj" type="button" data-hover-label="Editar" aria-label="Editar" title="Editar">
                <img src="/icon/boton/editar.svg" alt="Editar">
                <span class="action-label">Editar</span>
              </button>
              <button class="action-button" id="axm-save-obj" type="button" data-hover-label="Guardar" aria-label="Guardar" title="Guardar">
                <img src="/icon/boton/guardar.svg" alt="Guardar">
                <span class="action-label">Guardar</span>
              </button>
              <button class="action-button" id="axm-delete-obj" type="button" data-hover-label="Eliminar" aria-label="Eliminar" title="Eliminar">
                <img src="/icon/boton/eliminar.svg" alt="Eliminar">
                <span class="action-label">Eliminar</span>
              </button>
            </div>
            <div class="axm-msg" id="axm-msg" aria-live="polite"></div>
          </div>
        </section>
      </div>

      <script>
        (() => {
          const tabs = document.querySelectorAll(".axm-tab[data-axm-tab]");
          const openTreeBtn = document.querySelector('.view-pill[data-view="arbol"]');
          const openGanttBtn = document.querySelector('.view-pill[data-view="gantt"]');
          const openCalendarBtn = document.querySelector('.view-pill[data-view="calendar"]');
          const openExportDocBtn = document.querySelector('.view-pill[data-view="export-doc"]');
          const panel = document.getElementById("axm-tab-panel");
          const foundationPanel = document.getElementById("axm-foundacion-panel");
          const foundationEditorEl = document.getElementById("axm-foundacion-editor");
          const foundationSourceEl = document.getElementById("axm-foundacion-source");
          const foundationUploadBtn = document.getElementById("axm-foundacion-upload-btn");
          const foundationUploadEl = document.getElementById("axm-foundacion-upload");
          const foundationShowSourceEl = document.getElementById("axm-foundacion-show-source");
          const foundationEditBtn = document.getElementById("axm-foundacion-edit");
          const foundationSaveBtn = document.getElementById("axm-foundacion-save");
          const foundationMsgEl = document.getElementById("axm-foundacion-msg");
          const identidadPanel = document.getElementById("axm-identidad-panel");
          const blockedContainer = document.querySelector(".axm-grid");
          const objetivosPanel = document.getElementById("axm-objetivos-panel");
          const treeModalEl = document.getElementById("axm-tree-modal");
          const treeModalCloseEl = document.getElementById("axm-tree-modal-close");
          const ganttModalEl = document.getElementById("axm-gantt-modal");
          const ganttModalCloseEl = document.getElementById("axm-gantt-modal-close");
          const ganttHostEl = document.getElementById("axm-gantt-host");
          const ganttBlocksEl = document.getElementById("axm-gantt-blocks");
          const ganttShowAllBtn = document.getElementById("axm-gantt-show-all");
          const ganttHideAllBtn = document.getElementById("axm-gantt-hide-all");
          const arbolPanel = document.getElementById("axm-arbol-panel");
          const treeChartEl = document.getElementById("axm-tree-chart");
          const treeExpandBtn = document.getElementById("axm-tree-expand");
          const treeCollapseBtn = document.getElementById("axm-tree-collapse");
          const treeZoomInBtn = document.getElementById("axm-tree-zoom-in");
          const treeZoomOutBtn = document.getElementById("axm-tree-zoom-out");
          const treeFitBtn = document.getElementById("axm-tree-fit");
          const trackBoardEl = document.getElementById("axm-track-board");
          const escapeHtml = (value) => String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
          const identidadMsgEl = document.getElementById("axm-identidad-msg");
          const misionEditBtn = document.getElementById("axm-mision-edit");
          const misionSaveBtn = document.getElementById("axm-mision-save");
          const misionDeleteBtn = document.getElementById("axm-mision-delete");
          const visionEditBtn = document.getElementById("axm-vision-edit");
          const visionSaveBtn = document.getElementById("axm-vision-save");
          const visionDeleteBtn = document.getElementById("axm-vision-delete");
          const valoresEditBtn = document.getElementById("axm-valores-edit");
          const valoresSaveBtn = document.getElementById("axm-valores-save");
          const valoresDeleteBtn = document.getElementById("axm-valores-delete");
          const setupIdentityComposer = (prefix, linesId, hiddenId, fullId, addId) => {
            const linesHost = document.getElementById(linesId);
            const hiddenHost = document.getElementById(hiddenId);
            const fullHost = document.getElementById(fullId);
            const addBtn = document.getElementById(addId);
            if (!linesHost || !hiddenHost || !fullHost || !addBtn) return null;
            let lines = [{ code: `${prefix}1`, text: "" }];
            let editable = false;
            let onChange = () => {};
            const cleanCode = (value, idx) => {
              const raw = (value || "").trim().toLowerCase();
              return raw || `${prefix}${idx + 1}`;
            };
            const getLines = () => lines.map((item, idx) => ({
              code: cleanCode(item.code, idx),
              text: (item.text || "").trim(),
            }));
            const syncOutputs = () => {
              const safe = getLines();
              hiddenHost.innerHTML = "";
              safe.forEach((item, idx) => {
                const hiddenText = document.createElement("input");
                hiddenText.type = "hidden";
                hiddenText.name = `${prefix}${idx + 1}`;
                hiddenText.value = item.text || "";
                hiddenHost.appendChild(hiddenText);

                const hiddenCode = document.createElement("input");
                hiddenCode.type = "hidden";
                hiddenCode.name = `${prefix}${idx + 1}_code`;
                hiddenCode.value = item.code || "";
                hiddenHost.appendChild(hiddenCode);
              });
              fullHost.textContent = safe.map((line) => line.text).filter(Boolean).join(" ");
              onChange(safe);
            };
            const render = () => {
              linesHost.innerHTML = "";
              const safe = lines.length ? lines : [{ code: `${prefix}1`, text: "" }];
              safe.forEach((value, idx) => {
                const row = document.createElement("div");
                row.className = "axm-id-row";
                const codeInput = document.createElement("input");
                codeInput.type = "text";
                codeInput.className = "axm-id-code";
                codeInput.value = cleanCode(value.code, idx);
                codeInput.placeholder = `Código ${prefix}${idx + 1}`;
                codeInput.readOnly = !editable;
                codeInput.addEventListener("input", () => {
                  lines[idx].code = codeInput.value;
                  syncOutputs();
                });
                const input = document.createElement("input");
                input.type = "text";
                input.className = "axm-id-input";
                input.value = value.text || "";
                input.placeholder = `Escribe ${prefix}${idx + 1}`;
                input.readOnly = !editable;
                input.addEventListener("input", () => {
                  lines[idx].text = input.value;
                  syncOutputs();
                });
                const editBtn = document.createElement("button");
                editBtn.type = "button";
                editBtn.className = "axm-id-action edit";
                editBtn.setAttribute("aria-label", `Editar ${prefix}${idx + 1}`);
                editBtn.innerHTML = '<img src="/icon/editar.svg" alt="">';
                editBtn.addEventListener("click", () => {
                  if (!editable) return;
                  input.focus();
                  input.select();
                });
                editBtn.disabled = !editable;
                const removeBtn = document.createElement("button");
                removeBtn.type = "button";
                removeBtn.className = "axm-id-action delete";
                removeBtn.setAttribute("aria-label", `Eliminar ${prefix}${idx + 1}`);
                removeBtn.innerHTML = '<img src="/icon/eliminar.svg" alt="">';
                removeBtn.addEventListener("click", () => {
                  if (!editable) return;
                  lines.splice(idx, 1);
                  if (!lines.length) lines = [{ code: `${prefix}1`, text: "" }];
                  render();
                });
                removeBtn.disabled = !editable;
                row.appendChild(codeInput);
                row.appendChild(input);
                row.appendChild(editBtn);
                row.appendChild(removeBtn);
                linesHost.appendChild(row);
              });
              addBtn.disabled = !editable;
              syncOutputs();
            };
            addBtn.addEventListener("click", () => {
              if (!editable) return;
              lines.push({ code: `${prefix}${lines.length + 1}`, text: "" });
              render();
            });
            render();
            return {
              getLines,
              setEditable: (flag) => {
                editable = !!flag;
                render();
              },
              isEditable: () => !!editable,
              setLines: (incoming) => {
                const next = Array.isArray(incoming) ? incoming : [];
                lines = next.length
                  ? next.map((item, idx) => ({
                      code: cleanCode(item?.code, idx),
                      text: String(item?.text || ""),
                    }))
                  : [{ code: `${prefix}1`, text: "" }];
                render();
              },
              clearLines: () => {
                lines = [{ code: `${prefix}1`, text: "" }];
                render();
              },
              onChange: (handler) => {
                onChange = typeof handler === "function" ? handler : () => {};
                onChange(getLines());
              },
            };
          };
          const misionComposer = setupIdentityComposer("m", "axm-mision-lines", "axm-mision-hidden", "axm-mision-full", "axm-mision-add");
          const visionComposer = setupIdentityComposer("v", "axm-vision-lines", "axm-vision-hidden", "axm-vision-full", "axm-vision-add");
          const valoresComposer = setupIdentityComposer("val", "axm-valores-lines", "axm-valores-hidden", "axm-valores-full", "axm-valores-add");
          const setIdentityMsg = (text, isError = false) => {
            if (!identidadMsgEl) return;
            identidadMsgEl.textContent = text || "";
            identidadMsgEl.style.color = isError ? "#b91c1c" : "#0f3d2e";
          };
          const setFoundationMsg = (text, isError = false) => {
            if (!foundationMsgEl) return;
            foundationMsgEl.textContent = text || "";
            foundationMsgEl.style.color = isError ? "#b91c1c" : "#0f3d2e";
          };
          let foundationEditable = false;
          const setFoundationEditable = (enabled) => {
            foundationEditable = !!enabled;
            if (foundationEditorEl) {
              foundationEditorEl.contentEditable = foundationEditable ? "true" : "false";
            }
            if (foundationSourceEl) foundationSourceEl.readOnly = !foundationEditable;
            document.querySelectorAll("[data-found-cmd]").forEach((btn) => {
              btn.disabled = !foundationEditable;
            });
            if (foundationUploadBtn) foundationUploadBtn.disabled = !foundationEditable;
            if (foundationUploadEl) foundationUploadEl.disabled = !foundationEditable;
            if (foundationShowSourceEl) foundationShowSourceEl.disabled = !foundationEditable;
          };
          const getFoundationHtml = () => {
            if (foundationShowSourceEl && foundationShowSourceEl.checked) {
              return foundationSourceEl ? String(foundationSourceEl.value || "") : "";
            }
            return foundationEditorEl ? String(foundationEditorEl.innerHTML || "") : "";
          };
          const setFoundationHtml = (html) => {
            const raw = String(html || "");
            if (foundationEditorEl) foundationEditorEl.innerHTML = raw;
            if (foundationSourceEl) foundationSourceEl.value = raw;
          };
          const toggleFoundationSource = () => {
            const show = !!(foundationShowSourceEl && foundationShowSourceEl.checked);
            if (show) {
              if (foundationSourceEl) foundationSourceEl.value = foundationEditorEl ? foundationEditorEl.innerHTML : "";
            } else if (foundationEditorEl && foundationSourceEl) {
              foundationEditorEl.innerHTML = foundationSourceEl.value || "";
            }
            if (foundationSourceEl) foundationSourceEl.style.display = show ? "block" : "none";
            if (foundationEditorEl) foundationEditorEl.style.display = show ? "none" : "block";
          };
          const loadFoundationFromDb = async () => {
            const response = await fetch("/api/strategic-foundation", { method: "GET", credentials: "same-origin" });
            const data = await response.json().catch(() => ({}));
            if (!response.ok || data?.success === false) {
              throw new Error(data?.error || data?.detail || "No se pudo cargar Fundamentación.");
            }
            setFoundationHtml(String(data?.data?.texto || ""));
            toggleFoundationSource();
          };
          const saveFoundationToDb = async () => {
            const response = await fetch("/api/strategic-foundation", {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              credentials: "same-origin",
              body: JSON.stringify({ texto: getFoundationHtml() }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok || data?.success === false) {
              throw new Error(data?.error || data?.detail || "No se pudo guardar Fundamentación.");
            }
          };
          const loadIdentityFromDb = async () => {
            const response = await fetch("/api/strategic-identity", { method: "GET", credentials: "same-origin" });
            const data = await response.json().catch(() => ({}));
            if (!response.ok || data?.success === false) {
              throw new Error(data?.error || data?.detail || "No se pudo cargar Identidad.");
            }
            const mission = Array.isArray(data?.data?.mision) ? data.data.mision : [];
            const vision = Array.isArray(data?.data?.vision) ? data.data.vision : [];
            const valores = Array.isArray(data?.data?.valores) ? data.data.valores : [];
            if (misionComposer && mission.length) misionComposer.setLines(mission);
            if (visionComposer && vision.length) visionComposer.setLines(vision);
            if (valoresComposer && valores.length) valoresComposer.setLines(valores);
          };
          const saveIdentityBlockToDb = async (block, lines) => {
            const response = await fetch(`/api/strategic-identity/${encodeURIComponent(block)}`, {
              method: "PUT",
              headers: { "Content-Type": "application/json" },
              credentials: "same-origin",
              body: JSON.stringify({ lineas: Array.isArray(lines) ? lines : [] }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok || data?.success === false) {
              throw new Error(data?.error || data?.detail || "No se pudo guardar Identidad.");
            }
          };
          const clearIdentityBlockInDb = async (block) => {
            const response = await fetch(`/api/strategic-identity/${encodeURIComponent(block)}`, {
              method: "DELETE",
              credentials: "same-origin",
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok || data?.success === false) {
              throw new Error(data?.error || data?.detail || "No se pudo eliminar Identidad.");
            }
            return data;
          };
          loadIdentityFromDb().then(() => {
            renderStrategicTree();
            renderAxisEditor();
          }).catch((err) => {
            setIdentityMsg(err.message || "No se pudo cargar Identidad desde BD.", true);
          });
          loadFoundationFromDb().catch((err) => {
            setFoundationMsg(err.message || "No se pudo cargar Fundamentación desde BD.", true);
          });
          setFoundationEditable(false);
          foundationEditBtn && foundationEditBtn.addEventListener("click", () => {
            setFoundationEditable(true);
            setFoundationMsg("Edición habilitada en Fundamentación.");
          });
          foundationSaveBtn && foundationSaveBtn.addEventListener("click", async () => {
            try {
              await saveFoundationToDb();
              setFoundationEditable(false);
              setFoundationMsg("Fundamentación guardada correctamente.");
            } catch (err) {
              setFoundationMsg(err.message || "No se pudo guardar Fundamentación.", true);
            }
          });
          foundationShowSourceEl && foundationShowSourceEl.addEventListener("change", toggleFoundationSource);
          foundationSourceEl && foundationSourceEl.addEventListener("input", () => {
            if (foundationShowSourceEl && foundationShowSourceEl.checked && foundationEditorEl) {
              foundationEditorEl.innerHTML = foundationSourceEl.value || "";
            }
          });
          foundationEditorEl && foundationEditorEl.addEventListener("input", () => {
            if (!foundationShowSourceEl || !foundationShowSourceEl.checked) {
              if (foundationSourceEl) foundationSourceEl.value = foundationEditorEl.innerHTML || "";
            }
          });
          document.querySelectorAll("[data-found-cmd]").forEach((btn) => {
            btn.addEventListener("click", () => {
              const cmd = btn.getAttribute("data-found-cmd");
              if (!cmd) return;
              if (foundationShowSourceEl && foundationShowSourceEl.checked) {
                setFoundationMsg("Desactiva 'Ver código HTML' para usar formato visual.", true);
                return;
              }
              if (!foundationEditorEl) return;
              foundationEditorEl.focus();
              document.execCommand(cmd, false);
              if (foundationSourceEl) foundationSourceEl.value = foundationEditorEl.innerHTML || "";
            });
          });
          foundationUploadBtn && foundationUploadBtn.addEventListener("click", () => {
            if (foundationUploadEl) foundationUploadEl.click();
          });
          foundationUploadEl && foundationUploadEl.addEventListener("change", async () => {
            const file = foundationUploadEl.files && foundationUploadEl.files[0];
            if (!file) return;
            try {
              const html = await file.text();
              setFoundationHtml(html);
              setFoundationMsg("Archivo HTML cargado. Guarda para persistir.");
            } catch (_err) {
              setFoundationMsg("No se pudo leer el archivo HTML.", true);
            } finally {
              foundationUploadEl.value = "";
              toggleFoundationSource();
            }
          });
          misionEditBtn && misionEditBtn.addEventListener("click", () => {
            if (!misionComposer) return;
            misionComposer.setEditable(true);
            setIdentityMsg("Edición habilitada en Misión.");
          });
          misionSaveBtn && misionSaveBtn.addEventListener("click", async () => {
            if (!misionComposer) return;
            try {
              await saveIdentityBlockToDb("mision", misionComposer.getLines());
              misionComposer.setEditable(false);
              renderStrategicTree();
              renderAxisEditor();
              setIdentityMsg("Misión guardada correctamente.");
            } catch (err) {
              setIdentityMsg(err.message || "No se pudo guardar Misión.", true);
            }
          });
          misionDeleteBtn && misionDeleteBtn.addEventListener("click", async () => {
            if (!misionComposer) return;
            if (!confirm("¿Está seguro de eliminar las líneas de Misión?")) return;
            try {
              const payload = await clearIdentityBlockInDb("mision");
              const lines = Array.isArray(payload?.data?.lineas) ? payload.data.lineas : [];
              misionComposer.setLines(lines);
              misionComposer.setEditable(false);
              renderStrategicTree();
              renderAxisEditor();
              setIdentityMsg("Misión eliminada.");
            } catch (err) {
              setIdentityMsg(err.message || "No se pudo eliminar Misión.", true);
            }
          });
          visionEditBtn && visionEditBtn.addEventListener("click", () => {
            if (!visionComposer) return;
            visionComposer.setEditable(true);
            setIdentityMsg("Edición habilitada en Visión.");
          });
          visionSaveBtn && visionSaveBtn.addEventListener("click", async () => {
            if (!visionComposer) return;
            try {
              await saveIdentityBlockToDb("vision", visionComposer.getLines());
              visionComposer.setEditable(false);
              renderStrategicTree();
              renderAxisEditor();
              setIdentityMsg("Visión guardada correctamente.");
            } catch (err) {
              setIdentityMsg(err.message || "No se pudo guardar Visión.", true);
            }
          });
          visionDeleteBtn && visionDeleteBtn.addEventListener("click", async () => {
            if (!visionComposer) return;
            if (!confirm("¿Está seguro de eliminar las líneas de Visión?")) return;
            try {
              const payload = await clearIdentityBlockInDb("vision");
              const lines = Array.isArray(payload?.data?.lineas) ? payload.data.lineas : [];
              visionComposer.setLines(lines);
              visionComposer.setEditable(false);
              renderStrategicTree();
              renderAxisEditor();
              setIdentityMsg("Visión eliminada.");
            } catch (err) {
              setIdentityMsg(err.message || "No se pudo eliminar Visión.", true);
            }
          });
          valoresEditBtn && valoresEditBtn.addEventListener("click", () => {
            if (!valoresComposer) return;
            valoresComposer.setEditable(true);
            setIdentityMsg("Edición habilitada en Valores.");
          });
          valoresSaveBtn && valoresSaveBtn.addEventListener("click", async () => {
            if (!valoresComposer) return;
            try {
              await saveIdentityBlockToDb("valores", valoresComposer.getLines());
              valoresComposer.setEditable(false);
              setIdentityMsg("Valores guardados correctamente.");
            } catch (err) {
              setIdentityMsg(err.message || "No se pudo guardar Valores.", true);
            }
          });
          valoresDeleteBtn && valoresDeleteBtn.addEventListener("click", async () => {
            if (!valoresComposer) return;
            if (!confirm("¿Está seguro de eliminar las líneas de Valores?")) return;
            try {
              const payload = await clearIdentityBlockInDb("valores");
              const lines = Array.isArray(payload?.data?.lineas) ? payload.data.lineas : [];
              valoresComposer.setLines(lines);
              valoresComposer.setEditable(false);
              setIdentityMsg("Valores eliminados.");
            } catch (err) {
              setIdentityMsg(err.message || "No se pudo eliminar Valores.", true);
            }
          });
          const applyTabView = (tabKey) => {
            const showFoundation = tabKey === "fundamentacion";
            const showIdentidad = tabKey === "identidad";
            const showEjes = tabKey === "ejes";
            const showObjetivos = tabKey === "objetivos";
            if (panel) {
              panel.textContent = "No tiene acceso, consulte con el administrador";
              panel.style.display = showFoundation || showIdentidad || showEjes || showObjetivos ? "none" : "flex";
            }
            if (foundationPanel) {
              foundationPanel.style.display = showFoundation ? "block" : "none";
            }
            if (identidadPanel) {
              identidadPanel.style.display = showIdentidad ? "block" : "none";
            }
            if (blockedContainer) {
              blockedContainer.style.display = showEjes ? "grid" : "none";
            }
            if (objetivosPanel) {
              objetivosPanel.style.display = showObjetivos ? "block" : "none";
            }
          };
          if (tabs.length) {
            tabs.forEach((tabBtn) => {
              tabBtn.addEventListener("click", () => {
                tabs.forEach((btn) => { btn.classList.remove("active"); btn.classList.remove("tab-active"); });
                tabBtn.classList.add("active");
                tabBtn.classList.add("tab-active");
                applyTabView(tabBtn.getAttribute("data-axm-tab"));
              });
            });
          }
          openTreeBtn && openTreeBtn.addEventListener("click", () => {
            if (!treeModalEl) return;
            if (treeModalEl.parentElement !== document.body) {
              document.body.appendChild(treeModalEl);
            }
            treeModalEl.classList.add("open");
            treeModalEl.style.display = "flex";
            treeModalEl.style.position = "fixed";
            treeModalEl.style.inset = "0";
            document.body.style.overflow = "hidden";
            renderStrategicTree();
          });
          openGanttBtn && openGanttBtn.addEventListener("click", async () => {
            if (!ganttModalEl) return;
            if (ganttModalEl.parentElement !== document.body) {
              document.body.appendChild(ganttModalEl);
            }
            ganttModalEl.classList.add("open");
            ganttModalEl.style.display = "flex";
            ganttModalEl.style.position = "fixed";
            ganttModalEl.style.inset = "0";
            document.body.style.overflow = "hidden";
            await renderStrategicGantt();
          });
          openExportDocBtn && openExportDocBtn.addEventListener("click", () => {
            window.location.href = "/api/strategic-plan/export-doc";
          });
          const activeTab = document.querySelector(".axm-tab.active");
          applyTabView(activeTab ? activeTab.getAttribute("data-axm-tab") : "ejes");

          const axisListEl = document.getElementById("axm-axis-list");
          const axisModalEl = document.getElementById("axm-axis-modal");
          const axisModalCloseEl = document.getElementById("axm-axis-modal-close");
          const objModalEl = document.getElementById("axm-obj-modal");
          const objModalCloseEl = document.getElementById("axm-obj-modal-close");
          const objAxisListEl = document.getElementById("axm-obj-axis-list");
          const objAxisTitleEl = document.getElementById("axm-obj-axis-title");
          const objListEl = document.getElementById("axm-obj-list");
          const axisNameEl = document.getElementById("axm-axis-name");
          const axisBaseCodeEl = document.getElementById("axm-axis-base-code");
          const axisBasePreviewEl = document.getElementById("axm-axis-base-preview");
          const axisCodeEl = document.getElementById("axm-axis-code");
          const axisProgressEl = document.getElementById("axm-axis-progress");
          const axisLeaderEl = document.getElementById("axm-axis-leader");
          const axisOwnerEl = document.getElementById("axm-axis-owner");
          const axisStartEl = document.getElementById("axm-axis-start");
          const axisEndEl = document.getElementById("axm-axis-end");
          const planYearsEl = document.getElementById("axm-plan-years");
          const planStartEl = document.getElementById("axm-plan-start");
          const axisDescEl = document.getElementById("axm-axis-desc");
          const axisObjectivesListEl = document.getElementById("axm-axis-objectives-list");
          const objNameEl = document.getElementById("axm-obj-name");
          const objCodeEl = document.getElementById("axm-obj-code");
          const objProgressEl = document.getElementById("axm-obj-progress");
          const objLeaderEl = document.getElementById("axm-obj-leader");
          const objStartEl = document.getElementById("axm-obj-start");
          const objEndEl = document.getElementById("axm-obj-end");
          const objDescEl = document.getElementById("axm-obj-desc");
          const objSuggestIaBtn = document.getElementById("axm-obj-suggest-ia");
          const hitoNameEl = document.getElementById("axm-hito-name");
          const hitoDateEl = document.getElementById("axm-hito-date");
          const hitoDoneEl = document.getElementById("axm-hito-done");
          const hitoAddBtn = document.getElementById("axm-hito-add");
          const hitoCancelBtn = document.getElementById("axm-hito-cancel");
          const hitoListEl = document.getElementById("axm-hito-list");
          const hitoMsgEl = document.getElementById("axm-hito-msg");
          const kpiNameEl = document.getElementById("axm-kpi-name");
          const kpiPurposeEl = document.getElementById("axm-kpi-purpose");
          const kpiFormulaEl = document.getElementById("axm-kpi-formula");
          const kpiPeriodicityEl = document.getElementById("axm-kpi-periodicity");
          const kpiStandardEl = document.getElementById("axm-kpi-standard");
          const kpiReferenceEl = document.getElementById("axm-kpi-reference");
          const kpiSuggestIaBtn = document.getElementById("axm-kpi-suggest-ia");
          const kpiAddBtn = document.getElementById("axm-kpi-add");
          const kpiCancelBtn = document.getElementById("axm-kpi-cancel");
          const kpiListEl = document.getElementById("axm-kpi-list");
          const kpiMsgEl = document.getElementById("axm-kpi-msg");
          const objActsListEl = document.getElementById("axm-obj-acts-list");
          const msgEl = document.getElementById("axm-msg");
          const axisMsgEl = document.getElementById("axm-axis-msg");
          const globalMsgEl = document.getElementById("axm-global-msg");
          const addAxisBtn = document.getElementById("axm-add-axis");
          const downloadTemplateBtn = document.getElementById("axm-download-template");
          const importCsvBtn = document.getElementById("axm-import-csv");
          const importCsvFileEl = document.getElementById("axm-import-csv-file");
          const editAxisBtn = document.getElementById("axm-edit-axis");
          const saveAxisBtn = document.getElementById("axm-save-axis");
          const deleteAxisBtn = document.getElementById("axm-delete-axis");
          const addObjBtn = document.getElementById("axm-add-obj");
          const editObjBtn = document.getElementById("axm-edit-obj");
          const saveObjBtn = document.getElementById("axm-save-obj");
          const deleteObjBtn = document.getElementById("axm-delete-obj");
          const setupAxmRichEditor = (textareaEl) => {
            if (!textareaEl || textareaEl.dataset.richReady === "1") return null;
            const wrap = document.createElement("div");
            wrap.className = "axm-rt-wrap";
            const toolbar = document.createElement("div");
            toolbar.className = "axm-rt-toolbar";
            const cmds = [
              { cmd: "bold", label: "B" },
              { cmd: "italic", label: "I" },
              { cmd: "underline", label: "U" },
              { cmd: "insertUnorderedList", label: "• Lista" },
              { cmd: "insertOrderedList", label: "1. Lista" },
            ];
            cmds.forEach((item) => {
              const btn = document.createElement("button");
              btn.type = "button";
              btn.className = "axm-rt-btn";
              btn.textContent = item.label;
              btn.addEventListener("click", () => {
                editor.focus();
                document.execCommand(item.cmd, false);
                textareaEl.value = editor.innerHTML;
              });
              toolbar.appendChild(btn);
            });
            const editor = document.createElement("div");
            editor.className = "axm-rt-editor";
            editor.contentEditable = "true";
            editor.innerHTML = textareaEl.value || "";
            editor.addEventListener("input", () => {
              textareaEl.value = editor.innerHTML;
            });
            wrap.appendChild(toolbar);
            wrap.appendChild(editor);
            textareaEl.style.display = "none";
            textareaEl.dataset.richReady = "1";
            textareaEl.parentNode && textareaEl.parentNode.insertBefore(wrap, textareaEl);
            return {
              getHtml: () => String(editor.innerHTML || ""),
              setHtml: (value) => {
                const html = String(value || "");
                editor.innerHTML = html;
                textareaEl.value = html;
              },
            };
          };
          const axisDescRich = setupAxmRichEditor(axisDescEl);
          const objDescRich = setupAxmRichEditor(objDescEl);

          let axes = [];
          let departments = [];
          let axisDepartmentCollaborators = [];
          let collaborators = [];
          let poaActivitiesByObjective = {};
          let strategicTreeChart = null;
          let strategicTreeLibPromise = null;
          let selectedAxisId = null;
          let selectedObjectiveId = null;
          let editingHitoIndex = -1;
          let editingKpiIndex = -1;
          let ganttVisibility = {};
          const entryParams = new URLSearchParams(window.location.search || "");
          const entryOpenTarget = String(entryParams.get("open") || "").toLowerCase();
          const entryTabTarget = String(entryParams.get("tab") || "").toLowerCase();
          const entryAxisIdRaw = entryParams.get("axis_id");
          let entryIntentDone = false;
          const PLAN_STORAGE_KEY = "sipet_plan_macro_v1";
          const toId = (value) => {
            const n = Number(value);
            return Number.isFinite(n) ? n : null;
          };
          const axisPosition = (axis) => {
            const idx = axes.findIndex((item) => toId(item.id) === toId(axis?.id));
            return idx >= 0 ? idx + 1 : Math.max(1, Number(axis?.orden || 1));
          };
          const objectivePosition = (objective) => {
            const axis = selectedAxis();
            const list = (axis && Array.isArray(axis.objetivos)) ? axis.objetivos : [];
            const idx = list.findIndex((item) => toId(item.id) === toId(objective?.id));
            return idx >= 0 ? idx + 1 : Math.max(1, Number(objective?.orden || 1));
          };
          const buildAxisCode = (baseCode, orderNumber) => {
            const normalizedBase = String(baseCode || "").trim().toLowerCase().replace(/[^a-z0-9]/g, "") || "m1";
            const numericOrder = Number(orderNumber);
            const safeOrder = Number.isFinite(numericOrder) && numericOrder > 0 ? numericOrder : 1;
            return `${normalizedBase}-${String(safeOrder).padStart(2, "0")}`;
          };
          const buildObjectiveCode = (axisCode, orderNumber) => {
            const rawAxis = String(axisCode || "").trim().toLowerCase();
            const parts = rawAxis.split("-").filter(Boolean);
            const axisPrefix = parts.length >= 2 ? `${parts[0]}-${parts[1]}` : (parts.length === 1 ? `${parts[0]}-01` : "m1-01");
            const numericOrder = Number(orderNumber);
            const safeOrder = Number.isFinite(numericOrder) && numericOrder > 0 ? numericOrder : 1;
            return `${axisPrefix}-${String(safeOrder).padStart(2, "0")}`;
          };
          const getIdentityCodeOptions = () => {
            const missionCodes = (misionComposer ? misionComposer.getLines() : []).map((line) => String(line.code || "").trim().toLowerCase());
            const visionCodes = (visionComposer ? visionComposer.getLines() : []).map((line) => String(line.code || "").trim().toLowerCase());
            const combined = missionCodes.concat(visionCodes).map((value) => value.replace(/[^a-z0-9]/g, "")).filter(Boolean);
            const unique = [];
            combined.forEach((value) => {
              if (!unique.includes(value)) unique.push(value);
            });
            if (!unique.length) unique.push("m1", "v1");
            return unique;
          };
          const getIdentityCodeEntries = () => {
            const mission = (misionComposer ? misionComposer.getLines() : []).map((line) => ({
              code: String(line.code || "").trim().toLowerCase().replace(/[^a-z0-9]/g, ""),
              text: String(line.text || "").trim(),
            }));
            const vision = (visionComposer ? visionComposer.getLines() : []).map((line) => ({
              code: String(line.code || "").trim().toLowerCase().replace(/[^a-z0-9]/g, ""),
              text: String(line.text || "").trim(),
            }));
            const merged = mission.concat(vision).filter((item) => item.code);
            const deduped = [];
            merged.forEach((item) => {
              if (!deduped.some((entry) => entry.code === item.code)) deduped.push(item);
            });
            if (!deduped.length) deduped.push({ code: "m1", text: "" }, { code: "v1", text: "" });
            return deduped;
          };
          const updateAxisBasePreview = () => {
            if (!axisBasePreviewEl) return;
            const selectedCode = axisBaseCodeEl && axisBaseCodeEl.value ? axisBaseCodeEl.value : "";
            const entries = getIdentityCodeEntries();
            const match = entries.find((item) => item.code === selectedCode);
            axisBasePreviewEl.textContent = (match && match.text)
              ? match.text
              : "Sin texto para este código. Puedes editarlo en Identidad.";
          };
          const loadScript = (src) => new Promise((resolve, reject) => {
            if (document.querySelector(`script[src="${src}"]`)) {
              resolve();
              return;
            }
            const script = document.createElement("script");
            script.src = src;
            script.async = true;
            script.onload = () => resolve();
            script.onerror = () => reject(new Error(`No se pudo cargar ${src}`));
            document.head.appendChild(script);
          });
          const ensureStrategicTreeLibrary = async () => {
            if (window.d3 && window.d3.OrgChart) return true;
            if (!strategicTreeLibPromise) {
              strategicTreeLibPromise = (async () => {
                await loadScript("/static/vendor/d3.min.js");
                  await loadScript("/static/vendor/d3-flextree.min.js");
                  await loadScript("/static/vendor/d3-org-chart.min.js");
              })().catch(() => false);
            }
            const result = await strategicTreeLibPromise;
            return result !== false && !!(window.d3 && window.d3.OrgChart);
          };
          const ensureD3Library = async () => {
            if (window.d3) return true;
            try {
              await loadScript("/static/vendor/d3.min.js");
              return !!window.d3;
            } catch (_err) {
              return false;
            }
          };

          const openAxisModal = () => {
            if (!axisModalEl) return;
            if (axisModalEl.parentElement !== document.body) {
              document.body.appendChild(axisModalEl);
            }
            axisModalEl.classList.add("open");
            axisModalEl.style.display = "flex";
            axisModalEl.style.position = "fixed";
            axisModalEl.style.inset = "0";
            document.body.style.overflow = "hidden";
            document.querySelectorAll("[data-axis-tab]").forEach((btn) => { btn.classList.remove("active"); btn.classList.remove("tab-active"); });
            document.querySelectorAll("[data-axis-panel]").forEach((panelItem) => panelItem.classList.remove("active"));
            const firstTab = document.querySelector('[data-axis-tab="desc"]');
            const firstPanel = document.querySelector('[data-axis-panel="desc"]');
            if (firstTab) { firstTab.classList.add("active"); firstTab.classList.add("tab-active"); }
            if (firstPanel) firstPanel.classList.add("active");
          };
          const closeAxisModal = () => {
            if (!axisModalEl) return;
            axisModalEl.classList.remove("open");
            axisModalEl.style.display = "none";
            document.body.style.overflow = "";
          };
          const openObjModal = () => {
            if (!objModalEl) return;
            if (objModalEl.parentElement !== document.body) {
              document.body.appendChild(objModalEl);
            }
            objModalEl.classList.add("open");
            objModalEl.style.display = "flex";
            objModalEl.style.position = "fixed";
            objModalEl.style.inset = "0";
            document.body.style.overflow = "hidden";
            document.querySelectorAll("[data-obj-tab]").forEach((btn) => { btn.classList.remove("active"); btn.classList.remove("tab-active"); });
            document.querySelectorAll("[data-obj-panel]").forEach((panelItem) => panelItem.classList.remove("active"));
            const firstTab = document.querySelector('[data-obj-tab="desc"]');
            const firstPanel = document.querySelector('[data-obj-panel="desc"]');
            if (firstTab) { firstTab.classList.add("active"); firstTab.classList.add("tab-active"); }
            if (firstPanel) firstPanel.classList.add("active");
          };
          const closeObjModal = () => {
            if (!objModalEl) return;
            objModalEl.classList.remove("open");
            objModalEl.style.display = "none";
            document.body.style.overflow = "";
          };
          const closeTreeModal = () => {
            if (!treeModalEl) return;
            treeModalEl.classList.remove("open");
            treeModalEl.style.display = "none";
            document.body.style.overflow = "";
          };
          const closeGanttModal = () => {
            if (!ganttModalEl) return;
            ganttModalEl.classList.remove("open");
            ganttModalEl.style.display = "none";
            document.body.style.overflow = "";
          };
          axisModalCloseEl && axisModalCloseEl.addEventListener("click", closeAxisModal);
          axisModalEl && axisModalEl.addEventListener("click", (event) => {
            if (event.target === axisModalEl) closeAxisModal();
          });
          objModalCloseEl && objModalCloseEl.addEventListener("click", closeObjModal);
          objModalEl && objModalEl.addEventListener("click", (event) => {
            if (event.target === objModalEl) closeObjModal();
          });
          treeModalCloseEl && treeModalCloseEl.addEventListener("click", closeTreeModal);
          treeModalEl && treeModalEl.addEventListener("click", (event) => {
            if (event.target === treeModalEl) closeTreeModal();
          });
          ganttModalCloseEl && ganttModalCloseEl.addEventListener("click", closeGanttModal);
          ganttModalEl && ganttModalEl.addEventListener("click", (event) => {
            if (event.target === ganttModalEl) closeGanttModal();
          });
          if (axisModalEl && axisModalEl.parentElement !== document.body) {
            document.body.appendChild(axisModalEl);
          }
          if (objModalEl && objModalEl.parentElement !== document.body) {
            document.body.appendChild(objModalEl);
          }
          if (treeModalEl && treeModalEl.parentElement !== document.body) {
            document.body.appendChild(treeModalEl);
          }
          if (ganttModalEl && ganttModalEl.parentElement !== document.body) {
            document.body.appendChild(ganttModalEl);
          }
          document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && axisModalEl && axisModalEl.classList.contains("open")) {
              closeAxisModal();
            }
            if (event.key === "Escape" && objModalEl && objModalEl.classList.contains("open")) {
              closeObjModal();
            }
            if (event.key === "Escape" && treeModalEl && treeModalEl.classList.contains("open")) {
              closeTreeModal();
            }
            if (event.key === "Escape" && ganttModalEl && ganttModalEl.classList.contains("open")) {
              closeGanttModal();
            }
          });
          const centerStrategicTreeScroll = () => {
            if (!treeChartEl) return;
            const maxLeft = Math.max(0, treeChartEl.scrollWidth - treeChartEl.clientWidth);
            const maxTop = Math.max(0, treeChartEl.scrollHeight - treeChartEl.clientHeight);
            treeChartEl.scrollLeft = Math.round(maxLeft / 2);
            treeChartEl.scrollTop = Math.round(maxTop / 2);
          };

          const renderStrategicTree = () => {
            if (!treeChartEl) return;
            const statusFromProgress = (p) => {
              if (Number(p || 0) >= 85) return "ok";
              if (Number(p || 0) >= 60) return "warning";
              return "danger";
            };
            const statusLabel = (s) => {
              if (s === "danger") return "Atrasado";
              if (s === "warning") return "En riesgo";
              return "OK";
            };
            const cardStatusFromTree = (key, progress) => {
              if (key === "red" || key === "orange") return "danger";
              if (key === "yellow") return "warning";
              if (key === "green") return "ok";
              return statusFromProgress(progress);
            };
            const missionLines = misionComposer ? misionComposer.getLines() : [];
            const visionLines = visionComposer ? visionComposer.getLines() : [];
            const normalizeCode = (value) => String(value || "").trim().toLowerCase().replace(/[^a-z0-9]/g, "");
            const progressByCode = {};
            const axesByCode = {};
            const todayIso = (() => {
              const now = new Date();
              const y = now.getFullYear();
              const m = String(now.getMonth() + 1).padStart(2, "0");
              const d = String(now.getDate()).padStart(2, "0");
              return `${y}-${m}-${d}`;
            })();
            const statusInfo = (statusLabel, progress, endDate) => {
              const label = String(statusLabel || "").trim().toLowerCase();
              if (label === "en revisión") return { key: "orange", text: "En revisión" };
              if (label === "terminada" || Number(progress || 0) >= 100) return { key: "green", text: "Realizado" };
              if (endDate && todayIso > String(endDate)) return { key: "red", text: "Atrasado" };
              if (label === "en proceso" || Number(progress || 0) > 0) return { key: "yellow", text: "En proceso" };
              return { key: "gray", text: "No iniciado" };
            };
            const aggregateStatus = (nodes) => {
              const list = Array.isArray(nodes) ? nodes : [];
              if (!list.length) return { key: "gray", text: "No iniciado" };
              const has = (key) => list.some((item) => item.key === key);
              if (has("red")) return { key: "red", text: "Atrasado" };
              if (has("orange")) return { key: "orange", text: "En revisión" };
              if (has("yellow")) return { key: "yellow", text: "En proceso" };
              if (has("green")) return { key: "green", text: "Realizado" };
              return { key: "gray", text: "No iniciado" };
            };
            (axes || []).forEach((axis) => {
              const code = normalizeCode((axis.codigo || "").split("-", 1)[0] || axis.base_code || "");
              if (!code) return;
              if (!progressByCode[code]) progressByCode[code] = [];
              progressByCode[code].push(Number(axis.avance || 0));
              if (!axesByCode[code]) axesByCode[code] = [];
              axesByCode[code].push(axis);
            });
            const consolidatedProgress = (lines) => {
              const values = (lines || [])
                .filter((line) => (line.text || "").trim())
                .map((line) => {
                  const code = normalizeCode(line.code || "");
                  const list = progressByCode[code] || [];
                  if (!list.length) return 0;
                  return Math.round(list.reduce((sum, item) => sum + Number(item || 0), 0) / list.length);
                });
              if (!values.length) return 0;
              return Math.round(values.reduce((sum, item) => sum + Number(item || 0), 0) / values.length);
            };
            const missionProgress = consolidatedProgress(missionLines);
            const visionProgress = consolidatedProgress(visionLines);
            const colorByStatus = (key) => {
              if (key === "green") return "#16a34a";
              if (key === "yellow") return "#f59e0b";
              if (key === "orange") return "#f97316";
              if (key === "red") return "#ef4444";
              return "#94a3b8";
            };
            const buildLineNodes = (rootId, groupName, lines) => {
              const activeLines = (lines || []).filter((line) => (line.text || "").trim());
              const list = [];
              activeLines.forEach((line) => {
                const code = normalizeCode(line.code || "");
                const values = progressByCode[code] || [];
                const progress = values.length ? Math.round(values.reduce((sum, item) => sum + Number(item || 0), 0) / values.length) : 0;
                const lineId = `line-${code || Math.random().toString(36).slice(2, 8)}`;
                list.push({
                  id: lineId,
                  parentId: rootId,
                  type: "line",
                  code: String(line.code || "-"),
                  title: `${groupName} · ${line.text || "Sin línea"}`,
                  subtitle: `Avance ${progress}%`,
                  progress,
                  statusKey: progress >= 100 ? "green" : (progress > 0 ? "yellow" : "gray"),
                  kpi_1_label: "Ejes",
                  kpi_1: String((axesByCode[code] || []).length),
                  kpi_2_label: "Código",
                  kpi_2: String(line.code || "-"),
                });
                (axesByCode[code] || []).forEach((axis) => {
                  const axisObjectives = Array.isArray(axis.objetivos) ? axis.objetivos : [];
                  const axisState = aggregateStatus(axisObjectives.map((obj) => {
                    const activities = poaActivitiesByObjective[Number(obj.id || 0)] || [];
                    return aggregateStatus(activities.map((activity) => statusInfo(activity.status, activity.avance, activity.fecha_final)));
                  }));
                  const axisId = `axis-${Number(axis.id || 0)}`;
                  list.push({
                    id: axisId,
                    parentId: lineId,
                    type: "axis",
                    axisId: Number(axis.id || 0),
                    code: axis.codigo || "sin-codigo",
                    title: axis.nombre || "Eje sin nombre",
                    subtitle: `${axisState.text} · Avance ${Number(axis.avance || 0)}%`,
                    progress: Number(axis.avance || 0),
                    statusKey: axisState.key,
                    owner: axis.responsabilidad_directa || axis.lider_departamento || "",
                    kpi_1_label: "Objetivos",
                    kpi_1: String(axisObjectives.length),
                    kpi_2_label: "Código",
                    kpi_2: String(axis.codigo || "sin-codigo"),
                  });
                  axisObjectives.forEach((objective) => {
                    const activities = poaActivitiesByObjective[Number(objective.id || 0)] || [];
                    const objectiveState = aggregateStatus(activities.map((activity) => statusInfo(activity.status, activity.avance, activity.fecha_final)));
                    const objectiveId = `objective-${Number(objective.id || 0)}`;
                    list.push({
                      id: objectiveId,
                      parentId: axisId,
                      type: "objective",
                      axisId: Number(axis.id || 0),
                      objectiveId: Number(objective.id || 0),
                      code: objective.codigo || "OBJ",
                      title: objective.nombre || "Objetivo",
                      subtitle: `${objectiveState.text} · Avance ${Number(objective.avance || 0)}%`,
                      progress: Number(objective.avance || 0),
                      statusKey: objectiveState.key,
                      kpi_1_label: "Actividades",
                      kpi_1: String(activities.length),
                      kpi_2_label: "Código",
                      kpi_2: String(objective.codigo || "OBJ"),
                    });
                  });
                });
              });
              return list;
            };
            const nodes = [
              { id: "strategic-root", parentId: null, type: "root", code: "BSC", title: "Árbol estratégico", subtitle: "Mapa de decisión", progress: Math.round((missionProgress + visionProgress) / 2), statusKey: "gray" },
              { id: "mission-root", parentId: "strategic-root", type: "mission", code: "MIS", title: "Misión", subtitle: `Avance ${missionProgress}%`, progress: missionProgress, statusKey: missionProgress >= 100 ? "green" : (missionProgress > 0 ? "yellow" : "gray") },
              { id: "vision-root", parentId: "strategic-root", type: "vision", code: "VIS", title: "Visión", subtitle: `Avance ${visionProgress}%`, progress: visionProgress, statusKey: visionProgress >= 100 ? "green" : (visionProgress > 0 ? "yellow" : "gray") },
              ...buildLineNodes("mission-root", "Misión", missionLines),
              ...buildLineNodes("vision-root", "Visión", visionLines),
            ];
            if (!nodes.length || nodes.length <= 3) {
              treeChartEl.innerHTML = '<p>Sin líneas definidas. Agrega líneas en Misión/Visión.</p>';
              return;
            }
            ensureStrategicTreeLibrary().then((available) => {
              if (!available) {
                treeChartEl.innerHTML = '<p>No se pudo cargar la librería de organigrama.</p>';
                return;
              }
              treeChartEl.innerHTML = "";
              strategicTreeChart = new window.d3.OrgChart()
                .container(treeChartEl)
                .data(nodes)
                .nodeWidth((d) => ((d?.data?.type || "") === "root" ? 2 : 340))
                .nodeHeight((d) => ((d?.data?.type || "") === "root" ? 2 : 160))
                .childrenMargin(() => 60)
                .compactMarginBetween(() => 25)
                .compactMarginPair(() => 80)
                .linkYOffset(18)
                .setActiveNodeCentered(true)
                .initialExpandLevel(99)
                .compact(false)
                .nodeButtonWidth(() => 56)
                .nodeButtonHeight(() => 56)
                .nodeButtonX(() => -28)
                .nodeButtonY(() => -28)
                .buttonContent(({ node }) => {
                  const expanded = !!(node && node.children);
                  const sign = expanded ? "−" : "+";
                  const count = Number(node?.data?._directSubordinates || 0);
                  const countText = Number.isFinite(count) && count > 0 ? `${count}` : "";
                  return `
                    <div class="axm-node-toggle">
                      <div class="axm-node-toggle-sign">${sign}</div>
                      <div class="axm-node-toggle-count">${countText}</div>
                    </div>
                  `;
                })
                .onNodeClick(async (d) => {
                  const data = d?.data || {};
                  if (data.type === "mission" || data.type === "vision" || data.type === "line") {
                    closeTreeModal();
                    applyTabView("identidad");
                    const missionAcc = document.querySelector("#axm-identidad-panel details:nth-of-type(1)");
                    const visionAcc = document.querySelector("#axm-identidad-panel details:nth-of-type(2)");
                    if (data.type === "mission") { if (missionAcc) missionAcc.open = true; if (visionAcc) visionAcc.open = false; }
                    if (data.type === "vision") { if (missionAcc) missionAcc.open = false; if (visionAcc) visionAcc.open = true; }
                    if (data.type === "line") {
                      const isMission = String(data.code || "").toLowerCase().startsWith("m");
                      if (missionAcc) missionAcc.open = isMission;
                      if (visionAcc) visionAcc.open = !isMission;
                    }
                    return;
                  }
                  if (data.type === "axis" && data.axisId) {
                    closeTreeModal();
                    selectedAxisId = toId(data.axisId);
                    renderAll();
                    openAxisModal();
                    return;
                  }
                  if (data.type === "objective" && data.objectiveId) {
                    closeTreeModal();
                    selectedAxisId = toId(data.axisId) || selectedAxisId;
                    selectedObjectiveId = toId(data.objectiveId);
                    renderAll();
                    try { await loadCollaborators(); } catch (_err) {}
                    openObjModal();
                    return;
                  }
                  if (data.type === "activity" && data.activityId) {
                    closeTreeModal();
                    window.location.href = `/poa?objective_id=${Number(data.objectiveId || 0)}&activity_id=${Number(data.activityId || 0)}`;
                    return;
                  }
                  if (data.type === "subactivity" && data.subactivityId) {
                    closeTreeModal();
                    window.location.href = `/poa?objective_id=${Number(data.objectiveId || 0)}&activity_id=${Number(data.activityId || 0)}&subactivity_id=${Number(data.subactivityId || 0)}`;
                  }
                })
                .linkUpdate(function () {
                  window.d3.select(this).attr("stroke-width", 1.05).attr("stroke", "rgba(15,23,42,.35)");
                })
                .nodeContent((d) => {
                  const data = d?.data || {};
                  if ((data.type || "") === "root") {
                    return '<div></div>';
                  }
                  const progress = Number(data.progress || 0);
                  const status = cardStatusFromTree(data.statusKey, progress);
                  const typeBadge =
                    data.type === "mission" ? "🎯 Misión" :
                    data.type === "vision" ? "👁 Visión" :
                    data.type === "line" ? "🧩 Línea" :
                    data.type === "axis" ? "🏛 Eje" :
                    data.type === "objective" ? "🎯 Objetivo" :
                    data.type === "activity" ? "⚙ Actividad" :
                    data.type === "subactivity" ? "🛠 Subactividad" :
                    "🏷 Área";
                  const owner = data.owner
                    ? `<span class="oc-pill">👤 ${escapeHtml(data.owner)}</span>`
                    : "";
                  const k1 = (data.kpi_1 ?? "") !== ""
                    ? `<div class="oc-kpi"><span>${escapeHtml(data.kpi_1_label || "KPI")}</span><strong>${escapeHtml(data.kpi_1)}</strong></div>`
                    : "";
                  const k2 = (data.kpi_2 ?? "") !== ""
                    ? `<div class="oc-kpi"><span>${escapeHtml(data.kpi_2_label || "KPI")}</span><strong>${escapeHtml(data.kpi_2)}</strong></div>`
                    : "";
                  const grad =
                    status === "danger" ? "linear-gradient(90deg,#ef4444,#fb7185)" :
                    status === "warning" ? "linear-gradient(90deg,#f59e0b,#fbbf24)" :
                    "linear-gradient(90deg,#16a34a,#22c55e)";
                  return `
                    <div class="oc-card" data-status="${status}">
                      <div class="oc-top">
                        <div class="oc-title">
                          <div class="oc-name">${escapeHtml(data.title || "Área / Puesto")}</div>
                          <div class="oc-sub">
                            <span class="oc-pill">${typeBadge}</span>
                            ${owner}
                          </div>
                        </div>
                        <div class="oc-score">${Math.round(progress)}%</div>
                      </div>
                      <div class="oc-progress"><div class="oc-fill"></div></div>
                      <div class="oc-bottom">
                        <div class="oc-status"danger" ? "#ef4444" : (status === "warning" ? "#f59e0b" : "#16a34a")};">${statusLabel(status)}</div>
                        <div class="oc-kpis">${k1}${k2}</div>
                      </div>
                    </div>
                  `;
                })
                .render();
              if (strategicTreeChart && typeof strategicTreeChart.expandAll === "function") strategicTreeChart.expandAll();
              if (strategicTreeChart && typeof strategicTreeChart.fit === "function") strategicTreeChart.fit();
              setTimeout(centerStrategicTreeScroll, 30);
            });
          };
          if (treeZoomInBtn) {
            treeZoomInBtn.addEventListener("click", () => {
              if (strategicTreeChart && typeof strategicTreeChart.zoomIn === "function") strategicTreeChart.zoomIn();
            });
          }
          if (treeExpandBtn) {
            treeExpandBtn.addEventListener("click", () => {
              if (strategicTreeChart && typeof strategicTreeChart.expandAll === "function") strategicTreeChart.expandAll();
              if (strategicTreeChart && typeof strategicTreeChart.fit === "function") strategicTreeChart.fit();
              setTimeout(centerStrategicTreeScroll, 30);
            });
          }
          if (treeCollapseBtn) {
            treeCollapseBtn.addEventListener("click", () => {
              if (strategicTreeChart && typeof strategicTreeChart.collapseAll === "function") strategicTreeChart.collapseAll();
              if (strategicTreeChart && typeof strategicTreeChart.fit === "function") strategicTreeChart.fit();
              setTimeout(centerStrategicTreeScroll, 30);
            });
          }
          if (treeZoomOutBtn) {
            treeZoomOutBtn.addEventListener("click", () => {
              if (strategicTreeChart && typeof strategicTreeChart.zoomOut === "function") strategicTreeChart.zoomOut();
            });
          }
          if (treeFitBtn) {
            treeFitBtn.addEventListener("click", () => {
              if (strategicTreeChart && typeof strategicTreeChart.fit === "function") strategicTreeChart.fit();
              setTimeout(centerStrategicTreeScroll, 30);
            });
          }
          const renderTrackingBoard = () => {
            if (!trackBoardEl) return;
            const axisList = Array.isArray(axes) ? axes : [];
            const objectives = axisList.flatMap((axis) => Array.isArray(axis.objetivos) ? axis.objetivos : []);
            const objectiveAxisById = {};
            axisList.forEach((axis) => {
              (Array.isArray(axis.objetivos) ? axis.objetivos : []).forEach((obj) => {
                objectiveAxisById[String(obj.id)] = axis;
              });
            });
            const axisCount = axisList.length;
            const objectiveCount = objectives.length;
            const globalProgress = axisCount
              ? Math.round(axisList.reduce((sum, axis) => sum + Number(axis.avance || 0), 0) / axisCount)
              : 0;
            const objectiveDone = objectives.filter((obj) => Number(obj.avance || 0) >= 100).length;
            const axesNoOwner = axisList.filter((axis) => !String(axis?.responsabilidad_directa || "").trim());
            const objectivesNoOwner = objectives.filter((obj) => !String(obj?.lider || "").trim());
            const buildMissingList = (items, mapper) => {
              if (!items.length) return '<div class="axm-track-missing-empty">Sin pendientes.</div>';
              const preview = items.slice(0, 8).map((item) => `<li>${mapper(item)}</li>`).join("");
              const extra = items.length > 8 ? `<div class="axm-track-missing-more">+${items.length - 8} más</div>` : "";
              return `<ul class="axm-track-missing-list">${preview}</ul>${extra}`;
            };

            const missionAxes = axisList.filter((axis) => String(axis.base_code || axis.codigo || "").toLowerCase().startsWith("m"));
            const visionAxes = axisList.filter((axis) => String(axis.base_code || axis.codigo || "").toLowerCase().startsWith("v"));
            const missionProgress = missionAxes.length
              ? Math.round(missionAxes.reduce((sum, axis) => sum + Number(axis.avance || 0), 0) / missionAxes.length)
              : 0;
            const visionProgress = visionAxes.length
              ? Math.round(visionAxes.reduce((sum, axis) => sum + Number(axis.avance || 0), 0) / visionAxes.length)
              : 0;
            const milestones = objectives.flatMap((obj) => {
              if (Array.isArray(obj.hitos) && obj.hitos.length) return obj.hitos;
              return obj.hito ? [{ nombre: obj.hito, logrado: false, fecha_realizacion: "" }] : [];
            });
            const milestonesTotal = milestones.length;
            const milestonesDone = milestones.filter((item) => !!item.logrado).length;
            const milestonesPending = Math.max(0, milestonesTotal - milestonesDone);
            const todayIso = new Date().toISOString().slice(0, 10);
            const milestonesOverdue = milestones.filter((item) => {
              const due = String(item?.fecha_realizacion || "");
              return !item?.logrado && !!due && due < todayIso;
            }).length;
            const milestonesPct = milestonesTotal ? Math.round((milestonesDone * 100) / milestonesTotal) : 0;
            const milestoneChartBg = `conic-gradient(#16a34a 0 ${milestonesPct}%, #e2e8f0 ${milestonesPct}% 100%)`;

            trackBoardEl.innerHTML = `
              <h4>Tablero de seguimiento</h4>
              <div class="axm-track-grid">
                <article class="axm-track-card"><div class="axm-track-label">Avance global</div><div class="axm-track-value">${globalProgress}%</div></article>
                <article class="axm-track-card"><div class="axm-track-label">Ejes activos</div><div class="axm-track-value">${axisCount}</div></article>
                <article class="axm-track-card"><div class="axm-track-label">Objetivos</div><div class="axm-track-value">${objectiveCount}</div></article>
                <article class="axm-track-card"><div class="axm-track-label">Objetivos al 100%</div><div class="axm-track-value">${objectiveDone}</div></article>
              </div>
              <div class="axm-track-bar"><div class="axm-track-fill"></div></div>
              <div class="axm-track-meta">
                <span>Misión: ${missionProgress}%</span>
                <span>Visión: ${visionProgress}%</span>
              </div>
              <div class="axm-track-hitos">
                <div class="axm-track-hitos-chart"><span>${milestonesPct}%</span></div>
                <div class="axm-track-hitos-info">
                  <div class="axm-track-hitos-title">Hitos logrados</div>
                  <div class="axm-track-hitos-values">
                    <span>Total: <b>${milestonesTotal}</b></span>
                    <span>Logrados: <b>${milestonesDone}</b></span>
                    <span>Pendientes: <b>${milestonesPending}</b></span>
                    <span>Atrasados: <b>${milestonesOverdue}</b></span>
                  </div>
                </div>
              </div>
              <div class="axm-track-missing">
                <article class="axm-track-missing-card">
                  <h5 class="axm-track-missing-title">Ejes sin responsable</h5>
                  <div class="axm-track-missing-sub">${axesNoOwner.length} pendiente(s)</div>
                  ${buildMissingList(axesNoOwner, (axis) => `${escapeHtml(axis.codigo || "Sin código")} - ${escapeHtml(axis.nombre || "Sin nombre")}`)}
                </article>
                <article class="axm-track-missing-card">
                  <h5 class="axm-track-missing-title">Objetivos sin responsable</h5>
                  <div class="axm-track-missing-sub">${objectivesNoOwner.length} pendiente(s)</div>
                  ${buildMissingList(objectivesNoOwner, (obj) => {
                    const parentAxis = objectiveAxisById[String(obj.id)] || {};
                    const axisCode = String(parentAxis.codigo || "").trim();
                    const code = String(obj.codigo || "").trim();
                    const left = code || axisCode || "Sin código";
                    return `${escapeHtml(left)} - ${escapeHtml(obj.nombre || "Sin nombre")}`;
                  })}
                </article>
              </div>
            `;
          };

          const showMsg = (text, isError = false) => {
            const color = isError ? "#b91c1c" : "#0f3d2e";
            if (msgEl) {
              msgEl.style.color = color;
              msgEl.textContent = text || "";
            }
            if (axisMsgEl) {
              axisMsgEl.style.color = color;
              axisMsgEl.textContent = text || "";
            }
            if (globalMsgEl) {
              globalMsgEl.style.color = color;
              globalMsgEl.textContent = text || "";
            }
          };

          const requestJson = async (url, options = {}) => {
            const response = await fetch(url, {
              headers: { "Content-Type": "application/json" },
              credentials: "same-origin",
              ...options,
            });
            const raw = await response.text();
            const contentType = (response.headers.get("content-type") || "").toLowerCase();
            let payload = {};
            try {
              payload = raw ? JSON.parse(raw) : {};
            } catch (_err) {
              payload = {};
            }
            const redirectedToLogin = response.redirected && /\/login\b/.test(response.url || "");
            const looksLikeJson = contentType.includes("application/json");
            const successFlag = payload && typeof payload === "object" ? payload.success : undefined;
            if (redirectedToLogin) {
              throw new Error("Tu sesión expiró. Inicia sesión nuevamente.");
            }
            if (!response.ok || !looksLikeJson || successFlag !== true) {
              const fallback = raw && !payload.error ? raw.slice(0, 180) : "";
              throw new Error(payload.error || payload.detail || fallback || "No se pudo completar la operación.");
            }
            return payload;
          };
          const requestIaSuggestion = async (texto) => {
            const response = await fetch("/api/ia/suggest/objective-text", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              credentials: "same-origin",
              body: JSON.stringify({ texto: String(texto || "").trim() }),
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok || !payload || payload.error) {
              throw new Error(payload?.error || "No se pudo obtener sugerencia IA.");
            }
            return String(payload.sugerencia || "").trim();
          };
          const iaFeatureEnabled = async (moduleKey = "plan_estrategico") => {
            try {
              const response = await fetch(`/api/ia/flags?module=${encodeURIComponent(moduleKey)}&feature_key=suggest_objective_text`, {
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
              });
              const payload = await response.json().catch(() => ({}));
              return !!(response.ok && payload?.success === true && payload?.data?.enabled);
            } catch (_err) {
              return false;
            }
          };
          const plainTextFromHtml = (value) => {
            const html = String(value || "").trim();
            if (!html) return "";
            const tmp = document.createElement("div");
            tmp.innerHTML = html;
            return String(tmp.textContent || tmp.innerText || "").trim();
          };
          const openPoaIaSuggestionEditor = ({ title = "Sugerencia IA", suggestion = "" } = {}) => new Promise((resolve) => {
            let overlay = document.getElementById("poa-ia-suggest-overlay");
            if (!overlay) {
              overlay = document.createElement("div");
              overlay.id = "poa-ia-suggest-overlay";
              overlay.style.position = "fixed";
              overlay.style.inset = "0";
              overlay.style.background = "rgba(15,23,42,.42)";
              overlay.style.display = "none";
              overlay.style.alignItems = "center";
              overlay.style.justifyContent = "center";
              overlay.style.zIndex = "2600";
              overlay.innerHTML = `
                <div>
                  <div>
                    <h4 id="poa-ia-suggest-title">Sugerencia IA</h4>
                    <button type="button" id="poa-ia-close">Cerrar</button>
                  </div>
                  <p>Edita el texto y luego decide si lo aplicas o descartas.</p>
                  <textarea id="poa-ia-suggest-text"></textarea>
                  <div>
                    <button type="button" id="poa-ia-discard">Descartar</button>
                    <button type="button" id="poa-ia-apply">Aplicar</button>
                  </div>
                </div>
              `;
              document.body.appendChild(overlay);
            }
            const titleEl = document.getElementById("poa-ia-suggest-title");
            const textEl = document.getElementById("poa-ia-suggest-text");
            const closeEl = document.getElementById("poa-ia-close");
            const discardEl = document.getElementById("poa-ia-discard");
            const applyEl = document.getElementById("poa-ia-apply");
            if (titleEl) titleEl.textContent = title;
            if (textEl) textEl.value = String(suggestion || "");
            const finish = (result) => {
              overlay.style.display = "none";
              document.body.style.overflow = modalEl && modalEl.classList.contains("open") ? "hidden" : "";
              resolve(result);
            };
            if (closeEl) closeEl.onclick = () => finish({ action: "close", text: textEl ? textEl.value : "" });
            if (discardEl) discardEl.onclick = () => finish({ action: "discard", text: textEl ? textEl.value : "" });
            if (applyEl) applyEl.onclick = () => finish({ action: "apply", text: textEl ? textEl.value : "" });
            overlay.onclick = (event) => {
              if (event.target === overlay) finish({ action: "close", text: textEl ? textEl.value : "" });
            };
            overlay.style.display = "flex";
            document.body.style.overflow = "hidden";
            if (textEl) textEl.focus();
          });
          const openIaSuggestionEditor = ({ title = "Sugerencia IA", suggestion = "" } = {}) => new Promise((resolve) => {
            let overlay = document.getElementById("axm-ia-suggest-overlay");
            if (!overlay) {
              overlay = document.createElement("div");
              overlay.id = "axm-ia-suggest-overlay";
              overlay.style.position = "fixed";
              overlay.style.inset = "0";
              overlay.style.background = "rgba(15,23,42,.42)";
              overlay.style.display = "none";
              overlay.style.alignItems = "center";
              overlay.style.justifyContent = "center";
              overlay.style.zIndex = "2500";
              overlay.innerHTML = `
                <div>
                  <div>
                    <h4 id="axm-ia-suggest-title">Sugerencia IA</h4>
                    <button type="button" id="axm-ia-close">Cerrar</button>
                  </div>
                  <p>Puedes editar el texto antes de aplicarlo.</p>
                  <textarea id="axm-ia-suggest-text"></textarea>
                  <div>
                    <button type="button" id="axm-ia-discard">Descartar</button>
                    <button type="button" id="axm-ia-apply">Aplicar</button>
                  </div>
                </div>
              `;
              document.body.appendChild(overlay);
            }
            const titleEl = document.getElementById("axm-ia-suggest-title");
            const textEl = document.getElementById("axm-ia-suggest-text");
            const closeEl = document.getElementById("axm-ia-close");
            const discardEl = document.getElementById("axm-ia-discard");
            const applyEl = document.getElementById("axm-ia-apply");
            if (titleEl) titleEl.textContent = title;
            if (textEl) textEl.value = String(suggestion || "");
            const finish = (result) => {
              overlay.style.display = "none";
              document.body.style.overflow = "";
              resolve(result);
            };
            if (closeEl) closeEl.onclick = () => finish({ action: "close", text: textEl ? textEl.value : "" });
            if (discardEl) discardEl.onclick = () => finish({ action: "discard", text: textEl ? textEl.value : "" });
            if (applyEl) applyEl.onclick = () => finish({ action: "apply", text: textEl ? textEl.value : "" });
            overlay.onclick = (event) => {
              if (event.target === overlay) finish({ action: "close", text: textEl ? textEl.value : "" });
            };
            overlay.style.display = "flex";
            document.body.style.overflow = "hidden";
            if (textEl) textEl.focus();
          });

          const selectedAxis = () => {
            const targetId = toId(selectedAxisId);
            return axes.find((axis) => toId(axis.id) === targetId) || null;
          };
          const selectedObjective = () => {
            const axis = selectedAxis();
            if (!axis) return null;
            return (axis.objetivos || []).find((obj) => obj.id === selectedObjectiveId) || null;
          };
          const normalizeObjectiveMilestones = (rows) => {
            const list = Array.isArray(rows) ? rows : [];
            return list
              .map((item) => {
                if (!item || typeof item !== "object") return { nombre: "", logrado: false, fecha_realizacion: "" };
                return {
                  nombre: String(item.nombre || item.text || "").trim(),
                  logrado: !!item.logrado,
                  fecha_realizacion: String(item.fecha_realizacion || "").trim(),
                };
              })
              .filter((item) => item.nombre);
          };
          const setHitoMsg = (text, isError = false) => {
            if (!hitoMsgEl) return;
            hitoMsgEl.style.color = isError ? "#b91c1c" : "#64748b";
            hitoMsgEl.textContent = text || "";
          };
          const clearHitoForm = () => {
            if (hitoNameEl) hitoNameEl.value = "";
            if (hitoDateEl) hitoDateEl.value = "";
            if (hitoDoneEl) hitoDoneEl.checked = false;
            editingHitoIndex = -1;
            if (hitoAddBtn) hitoAddBtn.textContent = "Agregar hito";
            setHitoMsg("");
          };
          const readHitoForm = () => {
            const nombre = hitoNameEl && hitoNameEl.value ? hitoNameEl.value.trim() : "";
            const fecha_realizacion = hitoDateEl && hitoDateEl.value ? String(hitoDateEl.value) : "";
            const logrado = !!(hitoDoneEl && hitoDoneEl.checked);
            if (!nombre) {
              setHitoMsg("El texto del hito es obligatorio.", true);
              return null;
            }
            return { nombre, logrado, fecha_realizacion };
          };
          const editHitoAt = (index) => {
            const objective = selectedObjective();
            const list = normalizeObjectiveMilestones(objective?.hitos || []);
            if (!objective || index < 0 || index >= list.length) return;
            const item = list[index];
            if (hitoNameEl) hitoNameEl.value = item.nombre || "";
            if (hitoDateEl) hitoDateEl.value = item.fecha_realizacion || "";
            if (hitoDoneEl) hitoDoneEl.checked = !!item.logrado;
            editingHitoIndex = index;
            if (hitoAddBtn) hitoAddBtn.textContent = "Actualizar hito";
            setHitoMsg("Editando hito seleccionado.");
          };
          const deleteHitoAt = (index) => {
            const objective = selectedObjective();
            if (!objective) return;
            const list = normalizeObjectiveMilestones(objective.hitos || []);
            if (index < 0 || index >= list.length) return;
            list.splice(index, 1);
            objective.hitos = list;
            objective.hito = list.length ? String(list[0].nombre || "") : "";
            clearHitoForm();
            renderObjectiveMilestonesPanel();
            setHitoMsg("Hito eliminado del objetivo.");
          };
          const renderObjectiveMilestonesPanel = () => {
            if (!hitoListEl) return;
            const objective = selectedObjective();
            if (!objective) {
              hitoListEl.innerHTML = '<div class="axm-axis-meta">Selecciona un objetivo para gestionar hitos.</div>';
              clearHitoForm();
              return;
            }
            objective.hitos = normalizeObjectiveMilestones(objective.hitos || []);
            objective.hito = objective.hitos.length ? String(objective.hitos[0].nombre || "") : "";
            const list = objective.hitos;
            if (!list.length) {
              hitoListEl.innerHTML = '<div class="axm-axis-meta">Sin hitos registrados para este objetivo.</div>';
            } else {
              hitoListEl.innerHTML = list.map((item, idx) => `
                <article class="axm-kpi-item">
                  <div class="axm-kpi-item-head">
                    <h5>${escapeHtml(item.nombre || `Hito ${idx + 1}`)}</h5>
                    <div class="axm-kpi-item-actions">
                      <button type="button" class="axm-kpi-btn" data-hito-edit="${idx}">Editar</button>
                      <button type="button" class="axm-kpi-btn danger" data-hito-delete="${idx}">Eliminar</button>
                    </div>
                  </div>
                  <div class="axm-kpi-item-meta">Fecha: ${escapeHtml(item.fecha_realizacion || "N/D")}</div>
                  <div class="axm-kpi-item-meta">Estado: ${item.logrado ? "Logrado" : "Pendiente"}</div>
                </article>
              `).join("");
            }
            hitoListEl.querySelectorAll("[data-hito-edit]").forEach((button) => {
              button.addEventListener("click", () => editHitoAt(Number(button.getAttribute("data-hito-edit") || -1)));
            });
            hitoListEl.querySelectorAll("[data-hito-delete]").forEach((button) => {
              button.addEventListener("click", () => deleteHitoAt(Number(button.getAttribute("data-hito-delete") || -1)));
            });
          };
          const KPI_STANDARD_VALUES = ["mayor", "menor", "entre", "igual"];
          const normalizeObjectiveKpis = (rows) => {
            const list = Array.isArray(rows) ? rows : [];
            return list
              .filter((item) => item && typeof item === "object")
              .map((item) => {
                const estandarRaw = String(item.estandar || "").trim().toLowerCase();
                return {
                  nombre: String(item.nombre || "").trim(),
                  proposito: String(item.proposito || "").trim(),
                  formula: String(item.formula || "").trim(),
                  periodicidad: String(item.periodicidad || "").trim(),
                  estandar: KPI_STANDARD_VALUES.includes(estandarRaw) ? estandarRaw : "",
                  referencia: String(item.referencia || "").trim(),
                };
              })
              .filter((item) => item.nombre);
          };
          const setKpiMsg = (text, isError = false) => {
            if (!kpiMsgEl) return;
            kpiMsgEl.style.color = isError ? "#b91c1c" : "#64748b";
            kpiMsgEl.textContent = text || "";
          };
          const clearKpiForm = () => {
            if (kpiNameEl) kpiNameEl.value = "";
            if (kpiPurposeEl) kpiPurposeEl.value = "";
            if (kpiFormulaEl) kpiFormulaEl.value = "";
            if (kpiPeriodicityEl) kpiPeriodicityEl.value = "";
            if (kpiStandardEl) kpiStandardEl.value = "";
            if (kpiReferenceEl) kpiReferenceEl.value = "";
            editingKpiIndex = -1;
            if (kpiAddBtn) kpiAddBtn.textContent = "Agregar KPI";
            setKpiMsg("");
          };
          const readKpiForm = () => {
            const nombre = kpiNameEl && kpiNameEl.value ? kpiNameEl.value.trim() : "";
            const proposito = kpiPurposeEl && kpiPurposeEl.value ? kpiPurposeEl.value.trim() : "";
            const formula = kpiFormulaEl && kpiFormulaEl.value ? kpiFormulaEl.value.trim() : "";
            const periodicidad = kpiPeriodicityEl && kpiPeriodicityEl.value ? kpiPeriodicityEl.value.trim() : "";
            const estandar = kpiStandardEl && kpiStandardEl.value ? String(kpiStandardEl.value).trim().toLowerCase() : "";
            const referencia = kpiReferenceEl && kpiReferenceEl.value ? kpiReferenceEl.value.trim() : "";
            if (!nombre) {
              setKpiMsg("El nombre del KPI es obligatorio.", true);
              return null;
            }
            if (estandar && !KPI_STANDARD_VALUES.includes(estandar)) {
              setKpiMsg("El estándar del KPI no es válido.", true);
              return null;
            }
            if (estandar && !referencia) {
              setKpiMsg("Captura la referencia del estándar (ej. 8%).", true);
              return null;
            }
            return { nombre, proposito, formula, periodicidad, estandar, referencia };
          };
          const editKpiAt = (index) => {
            const objective = selectedObjective();
            const list = normalizeObjectiveKpis(objective?.kpis || []);
            if (!objective || index < 0 || index >= list.length) return;
            const item = list[index];
            if (kpiNameEl) kpiNameEl.value = item.nombre || "";
            if (kpiPurposeEl) kpiPurposeEl.value = item.proposito || "";
            if (kpiFormulaEl) kpiFormulaEl.value = item.formula || "";
            if (kpiPeriodicityEl) kpiPeriodicityEl.value = item.periodicidad || "";
            if (kpiStandardEl) kpiStandardEl.value = item.estandar || "";
            if (kpiReferenceEl) kpiReferenceEl.value = item.referencia || "";
            editingKpiIndex = index;
            if (kpiAddBtn) kpiAddBtn.textContent = "Actualizar KPI";
            setKpiMsg("Editando KPI seleccionado.");
          };
          const deleteKpiAt = (index) => {
            const objective = selectedObjective();
            if (!objective) return;
            const list = normalizeObjectiveKpis(objective.kpis || []);
            if (index < 0 || index >= list.length) return;
            list.splice(index, 1);
            objective.kpis = list;
            clearKpiForm();
            renderObjectiveKpisPanel();
            setKpiMsg("KPI eliminado del objetivo.");
          };
          const renderObjectiveKpisPanel = () => {
            if (!kpiListEl) return;
            const objective = selectedObjective();
            if (!objective) {
              kpiListEl.innerHTML = '<div class="axm-axis-meta">Selecciona un objetivo para gestionar KPIs.</div>';
              clearKpiForm();
              return;
            }
            objective.kpis = normalizeObjectiveKpis(objective.kpis || []);
            const list = objective.kpis;
            if (!list.length) {
              kpiListEl.innerHTML = '<div class="axm-axis-meta">Sin KPIs registrados para este objetivo.</div>';
            } else {
              kpiListEl.innerHTML = list.map((item, idx) => `
                <article class="axm-kpi-item">
                  <div class="axm-kpi-item-head">
                    <h5>${escapeHtml(item.nombre || "KPI")}</h5>
                    <div class="axm-kpi-item-actions">
                      <button type="button" class="axm-kpi-btn" data-kpi-edit="${idx}">Editar</button>
                      <button type="button" class="axm-kpi-btn danger" data-kpi-delete="${idx}">Eliminar</button>
                    </div>
                  </div>
                  <div class="axm-kpi-item-meta">Propósito: ${escapeHtml(item.proposito || "N/D")}</div>
                  <div class="axm-kpi-item-meta">Fórmula: ${escapeHtml(item.formula || "N/D")}</div>
                  <div class="axm-kpi-item-meta">Periodicidad: ${escapeHtml(item.periodicidad || "N/D")} · Estándar: ${escapeHtml(item.estandar ? `${item.estandar} a ${item.referencia || "N/D"}` : "N/D")}</div>
                </article>
              `).join("");
            }
            kpiListEl.querySelectorAll("[data-kpi-edit]").forEach((button) => {
              button.addEventListener("click", () => {
                const idx = Number(button.getAttribute("data-kpi-edit"));
                editKpiAt(Number.isFinite(idx) ? idx : -1);
              });
            });
            kpiListEl.querySelectorAll("[data-kpi-delete]").forEach((button) => {
              button.addEventListener("click", () => {
                const idx = Number(button.getAttribute("data-kpi-delete"));
                deleteKpiAt(Number.isFinite(idx) ? idx : -1);
              });
            });
          };
          const visualRangeError = (start, end, label) => {
            if (!start && !end) return "";
            if (!start || !end) return `${label}: completa fecha inicial y fecha final.`;
            if (start > end) return `${label}: la fecha inicial no puede ser mayor que la final.`;
            return "";
          };
          const computePlanEnd = (startDate, years) => {
            if (!startDate || !years) return "";
            const base = new Date(`${startDate}T00:00:00`);
            if (Number.isNaN(base.getTime())) return "";
            base.setFullYear(base.getFullYear() + Number(years));
            base.setDate(base.getDate() - 1);
            const month = String(base.getMonth() + 1).padStart(2, "0");
            const day = String(base.getDate()).padStart(2, "0");
            return `${base.getFullYear()}-${month}-${day}`;
          };
          const getPlanWindow = () => {
            const years = Number(planYearsEl && planYearsEl.value ? planYearsEl.value : 0);
            const start = planStartEl && planStartEl.value ? String(planStartEl.value) : "";
            const end = computePlanEnd(start, years);
            return { years, start, end };
          };
          const savePlanWindow = () => {
            try {
              const payload = {
                years: String(planYearsEl && planYearsEl.value ? planYearsEl.value : "1"),
                start: String(planStartEl && planStartEl.value ? planStartEl.value : ""),
              };
              window.localStorage.setItem(PLAN_STORAGE_KEY, JSON.stringify(payload));
            } catch (_err) {}
          };
          const loadPlanWindow = () => {
            try {
              const raw = window.localStorage.getItem(PLAN_STORAGE_KEY);
              if (!raw) return;
              const data = JSON.parse(raw);
              if (planYearsEl && ["1", "2", "3", "4", "5"].includes(String(data?.years || ""))) {
                planYearsEl.value = String(data.years);
              }
              if (planStartEl && data?.start) {
                planStartEl.value = String(data.start);
              }
            } catch (_err) {}
          };
          const syncAxisDateBounds = () => {
            const win = getPlanWindow();
            [axisStartEl, axisEndEl].forEach((el) => {
              if (!el) return;
              el.min = win.start || "";
              el.max = win.end || "";
            });
          };
          const validateAxisWithinPlan = (axisStart, axisEnd) => {
            if (!axisStart && !axisEnd) return "";
            const win = getPlanWindow();
            if (!win.start || !win.end) return "";
            if (axisStart && axisStart < win.start) return "Eje estratégico: fecha inicial fuera del marco del plan.";
            if (axisEnd && axisEnd > win.end) return "Eje estratégico: fecha final fuera del marco del plan.";
            return "";
          };
          const axisGanttKey = (axis) => String(axis?.codigo || `axis-${axis?.id || ""}`).trim();
          const syncGanttVisibility = () => {
            const next = {};
            (Array.isArray(axes) ? axes : []).forEach((axis) => {
              const key = axisGanttKey(axis);
              if (!key) return;
              next[key] = Object.prototype.hasOwnProperty.call(ganttVisibility, key) ? !!ganttVisibility[key] : true;
            });
            ganttVisibility = next;
          };
          const renderGanttBlockFilters = () => {
            if (!ganttBlocksEl) return;
            const axisList = Array.isArray(axes) ? axes : [];
            if (!axisList.length) {
              ganttBlocksEl.innerHTML = "";
              return;
            }
            syncGanttVisibility();
            ganttBlocksEl.innerHTML = axisList.map((axis) => {
              const key = axisGanttKey(axis);
              const checked = ganttVisibility[key] !== false ? "checked" : "";
              const code = escapeHtml(axis.codigo || "xx-yy");
              const name = escapeHtml(axis.nombre || "Eje");
              return `
                <label class="axm-gantt-block">
                  <input type="checkbox" data-gantt-axis="${escapeHtml(key)}" ${checked}>
                  <code>${code}</code>
                  <span>${name}</span>
                </label>
              `;
            }).join("");
            ganttBlocksEl.querySelectorAll("input[data-gantt-axis]").forEach((checkbox) => {
              checkbox.addEventListener("change", async () => {
                const key = String(checkbox.getAttribute("data-gantt-axis") || "");
                if (!key) return;
                ganttVisibility[key] = !!checkbox.checked;
                await renderStrategicGantt();
              });
            });
          };
          const renderStrategicGantt = async () => {
            if (!ganttHostEl) return;
            const ok = await ensureD3Library();
            if (!ok) {
              ganttHostEl.innerHTML = '<p>No se pudo cargar la librería para la vista Gantt.</p>';
              return;
            }
            renderGanttBlockFilters();
            syncGanttVisibility();
            const axisList = Array.isArray(axes) ? axes : [];
            const rows = [];
            axisList.forEach((axis) => {
              const axisKey = axisGanttKey(axis);
              if (ganttVisibility[axisKey] === false) return;
              const axisStart = String(axis.fecha_inicial || "");
              const axisEnd = String(axis.fecha_final || "");
              if (axisStart && axisEnd) {
                rows.push({
                  level: 0,
                  type: "axis",
                  label: `${axis.codigo || "xx-yy"} · ${axis.nombre || "Eje sin nombre"}`,
                  start: new Date(`${axisStart}T00:00:00`),
                  end: new Date(`${axisEnd}T00:00:00`),
                });
              }
              (Array.isArray(axis.objetivos) ? axis.objetivos : []).forEach((obj) => {
                const start = String(obj.fecha_inicial || "");
                const end = String(obj.fecha_final || "");
                if (!start || !end) return;
                rows.push({
                  level: 1,
                  type: "objective",
                  label: `${obj.codigo || "xx-yy-zz"} · ${obj.nombre || "Objetivo"}`,
                  start: new Date(`${start}T00:00:00`),
                  end: new Date(`${end}T00:00:00`),
                });
              });
            });
            if (!rows.length) {
              ganttHostEl.innerHTML = '<p>No hay fechas suficientes en ejes/objetivos para generar Gantt.</p>';
              return;
            }
            const planWin = getPlanWindow();
            const dataMin = new Date(Math.min(...rows.map((item) => item.start.getTime())));
            const dataMax = new Date(Math.max(...rows.map((item) => item.end.getTime())));
            const domainStart = planWin.start ? new Date(`${planWin.start}T00:00:00`) : dataMin;
            const domainEnd = planWin.end ? new Date(`${planWin.end}T00:00:00`) : dataMax;
            const margin = { top: 44, right: 24, bottom: 30, left: 390 };
            const rowH = 34;
            const chartW = Math.max(900, ganttHostEl.clientWidth + 280);
            const width = margin.left + chartW + margin.right;
            const height = margin.top + (rows.length * rowH) + margin.bottom;
            ganttHostEl.innerHTML = "";
            const svg = window.d3.select(ganttHostEl).append("svg")
              .attr("width", width)
              .attr("height", height)
              .style("min-width", `${width}px`)
              .style("display", "block");
            const x = window.d3.scaleTime().domain([domainStart, domainEnd]).range([margin.left, margin.left + chartW]);
            const y = (idx) => margin.top + (idx * rowH);

            svg.append("g")
              .attr("transform", `translate(0, ${margin.top - 10})`)
              .call(window.d3.axisTop(x).ticks(window.d3.timeMonth.every(1)).tickSize(-rows.length * rowH).tickFormat(window.d3.timeFormat("%b %Y")))
              .call((g) => g.selectAll("text").attr("fill", "#475569").attr("font-size", 11))
              .call((g) => g.selectAll("line").attr("stroke", "rgba(148,163,184,.28)"))
              .call((g) => g.select(".domain").attr("stroke", "rgba(148,163,184,.35)"));

            rows.forEach((row, idx) => {
              const yy = y(idx);
              if (idx % 2 === 0) {
                svg.append("rect")
                  .attr("x", margin.left)
                  .attr("y", yy)
                  .attr("width", chartW)
                  .attr("height", rowH)
                  .attr("fill", "rgba(248,250,252,.70)");
              }
              svg.append("text")
                .attr("x", margin.left - 10 - (row.level ? 16 : 0))
                .attr("y", yy + (rowH / 2) + 4)
                .attr("text-anchor", "end")
                .attr("fill", row.level ? "#334155" : "#0f172a")
                .attr("font-size", row.level ? 12 : 12.5)
                .attr("font-style", row.level ? "italic" : "normal")
                .attr("font-weight", row.level ? 500 : 700)
                .text(row.label);
              const startX = x(row.start);
              const endX = x(row.end);
              const barW = Math.max(3, endX - startX);
              svg.append("rect")
                .attr("x", startX)
                .attr("y", yy + 7)
                .attr("width", barW)
                .attr("height", rowH - 14)
                .attr("rx", 7)
                .attr("fill", row.type === "axis" ? "#0f3d2e" : "#2563eb")
                .attr("opacity", row.type === "axis" ? 0.88 : 0.80);
            });

            const today = new Date();
            if (today >= domainStart && today <= domainEnd) {
              const tx = x(today);
              svg.append("line")
                .attr("x1", tx)
                .attr("x2", tx)
                .attr("y1", margin.top - 8)
                .attr("y2", margin.top + rows.length * rowH)
                .attr("stroke", "#ef4444")
                .attr("stroke-width", 1.8)
                .attr("stroke-dasharray", "4,3");
            }
          };
          ganttShowAllBtn && ganttShowAllBtn.addEventListener("click", async () => {
            syncGanttVisibility();
            Object.keys(ganttVisibility).forEach((key) => { ganttVisibility[key] = true; });
            renderGanttBlockFilters();
            await renderStrategicGantt();
          });
          ganttHideAllBtn && ganttHideAllBtn.addEventListener("click", async () => {
            syncGanttVisibility();
            Object.keys(ganttVisibility).forEach((key) => { ganttVisibility[key] = false; });
            renderGanttBlockFilters();
            await renderStrategicGantt();
          });

          const renderDepartmentOptions = (selectedValue = "") => {
            if (!axisLeaderEl) return;
            const options = ['<option value="">Selecciona departamento</option>']
              .concat(
                departments.map((name) => {
                  const selected = name === selectedValue ? "selected" : "";
                  return `<option value="${name}" ${selected}>${name}</option>`;
                })
              );
            axisLeaderEl.innerHTML = options.join("");
          };
          const renderAxisOwnerOptions = (selectedValue = "") => {
            if (!axisOwnerEl) return;
            const options = ['<option value="">Selecciona colaborador</option>']
              .concat(
                axisDepartmentCollaborators.map((name) => {
                  const selected = name === selectedValue ? "selected" : "";
                  return `<option value="${name}" ${selected}>${name}</option>`;
                })
              );
            axisOwnerEl.innerHTML = options.join("");
          };
          const loadAxisDepartmentCollaborators = async (department, selectedValue = "") => {
            if (!axisOwnerEl) return;
            const dep = (department || "").trim();
            if (!dep) {
              axisDepartmentCollaborators = [];
              renderAxisOwnerOptions("");
              return;
            }
            try {
              const payload = await requestJson(`/api/strategic-axes/collaborators-by-department?department=${encodeURIComponent(dep)}`);
              axisDepartmentCollaborators = Array.isArray(payload.data) ? payload.data : [];
              renderAxisOwnerOptions(selectedValue || "");
            } catch (_err) {
              axisDepartmentCollaborators = [];
              renderAxisOwnerOptions("");
            }
          };

          const renderCollaboratorOptions = (selectedValue = "") => {
            if (!objLeaderEl) return;
            const options = ['<option value="">Selecciona colaborador</option>']
              .concat(
                collaborators.map((name) => {
                  const selected = name === selectedValue ? "selected" : "";
                  return `<option value="${name}" ${selected}>${name}</option>`;
                })
              );
            objLeaderEl.innerHTML = options.join("");
          };
          const setCollaboratorLoading = (isLoading) => {
            if (!objLeaderEl) return;
            objLeaderEl.disabled = !!isLoading;
            if (isLoading) {
              objLeaderEl.innerHTML = '<option value="">Cargando colaboradores...</option>';
            }
          };
          const renderAxisObjectivesPanel = () => {
            if (!axisObjectivesListEl) return;
            const axis = selectedAxis();
            if (!axis) {
              axisObjectivesListEl.innerHTML = '<div class="axm-axis-meta">Selecciona un eje para ver objetivos.</div>';
              return;
            }
            const list = Array.isArray(axis.objetivos) ? axis.objetivos : [];
            if (!list.length) {
              axisObjectivesListEl.innerHTML = '<div class="axm-axis-meta">Sin objetivos registrados en este eje.</div>';
              return;
            }
            axisObjectivesListEl.innerHTML = list.map((obj) => `
              <article class="axm-axis-objective">
                <h5>${obj.codigo || "OBJ"} · ${obj.nombre || "Objetivo sin nombre"}</h5>
                <div class="meta">Hito: ${obj.hito || "N/D"} · Líder: ${obj.lider || "N/D"} · Avance: ${Number(obj.avance || 0)}%</div>
              </article>
            `).join("");
          };
          const renderObjectiveActivitiesPanel = () => {
            if (!objActsListEl) return;
            const objective = selectedObjective();
            if (!objective) {
              objActsListEl.innerHTML = '<div class="axm-axis-meta">Selecciona un objetivo para ver actividades.</div>';
              return;
            }
            const list = poaActivitiesByObjective[Number(objective.id || 0)] || [];
            if (!list.length) {
              objActsListEl.innerHTML = '<div class="axm-axis-meta">Sin actividades POA para este objetivo.</div>';
              return;
            }
            objActsListEl.innerHTML = list.map((item) => `
              <article class="axm-obj-act">
                <h5>${item.codigo || "ACT"} · ${item.nombre || "Actividad sin nombre"}</h5>
                <div class="meta">Responsable: ${item.responsable || "N/D"} · ${item.fecha_inicial || "N/D"} a ${item.fecha_final || "N/D"}</div>
                <div class="meta">Estatus: ${item.status || "N/D"} · Avance: ${Number(item.avance || 0)}% · Entregable: ${item.entregable || "N/D"}</div>
              </article>
            `).join("");
          };
          const loadObjectiveActivities = async () => {
            try {
              const payload = await requestJson("/api/poa/board-data");
              const activities = Array.isArray(payload.activities) ? payload.activities : [];
              poaActivitiesByObjective = {};
              activities.forEach((item) => {
                const key = Number(item.objective_id || 0);
                if (!key) return;
                if (!poaActivitiesByObjective[key]) poaActivitiesByObjective[key] = [];
                poaActivitiesByObjective[key].push(item);
              });
            } catch (_err) {
              poaActivitiesByObjective = {};
            }
            renderAll();
          };

          const renderAxisList = () => {
            if (!axisListEl) return;
            if (!axes.length) {
              axisListEl.innerHTML = '<div class="axm-axis-meta">Sin ejes cargados. Verifica sesión/API de estrategia.</div>';
              return;
            }
            axisListEl.innerHTML = axes.map((axis) => `
              <button class="axm-axis-btn ${toId(axis.id) === toId(selectedAxisId) ? "active" : ""}" type="button" data-axis-id="${axis.id}">
                <span>
                  <strong>${axis.nombre}</strong>
                  <div class="axm-axis-meta">${axis.codigo || "Sin código"} • ${axis.lider_departamento || "Sin líder"} • Avance ${Number(axis.avance || 0)}%</div>
                </span>
                <span class="axm-count">${axis.objetivos_count || 0}</span>
              </button>
            `).join("");
            axisListEl.querySelectorAll("[data-axis-id]").forEach((button) => {
              button.addEventListener("click", async () => {
                selectedAxisId = toId(button.getAttribute("data-axis-id"));
                selectedObjectiveId = null;
                renderAll();
                openAxisModal();
                try {
                  await loadCollaborators();
                  renderAll();
                } catch (_error) {
                  showMsg("No se pudieron cargar colaboradores para el eje seleccionado.", true);
                }
              });
            });
            const activeBtn = axisListEl.querySelector(".axm-axis-btn.active");
            if (activeBtn && typeof activeBtn.scrollIntoView === "function") {
              activeBtn.scrollIntoView({ block: "nearest", behavior: "smooth" });
            }
          };
          const renderObjectiveAxisList = () => {
            if (!objAxisListEl) return;
            if (!axes.length) {
              objAxisListEl.innerHTML = '<div class="axm-axis-meta">Sin ejes disponibles.</div>';
              return;
            }
            objAxisListEl.innerHTML = (axes || []).map((axis) => `
              <button class="axm-obj-axis-btn ${toId(axis.id) === toId(selectedAxisId) ? "active" : ""}" type="button" data-obj-axis-id="${axis.id}">
                <span>
                  <strong>${axis.nombre || "Eje sin nombre"}</strong>
                </span>
                <span class="axm-obj-axis-arrow">›</span>
              </button>
            `).join("");
            objAxisListEl.querySelectorAll("[data-obj-axis-id]").forEach((button) => {
              button.addEventListener("click", async () => {
                selectedAxisId = toId(button.getAttribute("data-obj-axis-id"));
                selectedObjectiveId = null;
                renderAll();
                try {
                  await loadCollaborators();
                  renderAll();
                } catch (_error) {
                  showMsg("No se pudieron cargar colaboradores para el eje seleccionado.", true);
                }
              });
            });
          };

          const renderAxisEditor = () => {
            const axis = selectedAxis();
            if (!axis) {
              axisNameEl.value = "";
              if (axisBaseCodeEl) axisBaseCodeEl.innerHTML = "";
              if (axisCodeEl) axisCodeEl.value = "";
              if (axisProgressEl) axisProgressEl.value = "0%";
              if (axisStartEl) axisStartEl.value = "";
              if (axisEndEl) axisEndEl.value = "";
              if (axisBasePreviewEl) axisBasePreviewEl.textContent = "Selecciona un código para ver su línea asociada.";
              renderDepartmentOptions("");
              axisDepartmentCollaborators = [];
              renderAxisOwnerOptions("");
              if (axisDescRich) {
                axisDescRich.setHtml("");
              } else if (axisDescEl) {
                axisDescEl.value = "";
              }
              syncAxisDateBounds();
              renderAxisObjectivesPanel();
              return;
            }
            axisNameEl.value = axis.nombre || "";
            const entries = getIdentityCodeEntries();
            const options = entries.map((item) => item.code);
            const codeParts = String(axis.codigo || "").split("-");
            const inferredBase = String(codeParts[0] || "").trim().toLowerCase().replace(/[^a-z0-9]/g, "");
            const selectedBase = options.includes(inferredBase) ? inferredBase : options[0];
            if (axisBaseCodeEl) {
              axisBaseCodeEl.innerHTML = options.map((code) => `<option value="${code}" ${code === selectedBase ? "selected" : ""}>${code}</option>`).join("");
              axisBaseCodeEl.onchange = () => {
                if (axisCodeEl) axisCodeEl.value = buildAxisCode(axisBaseCodeEl.value, axisPosition(axis));
                updateAxisBasePreview();
              };
            }
            if (axisCodeEl) axisCodeEl.value = buildAxisCode(selectedBase, axisPosition(axis));
            if (axisProgressEl) axisProgressEl.value = `${Number(axis.avance || 0)}%`;
            if (axisStartEl) axisStartEl.value = axis.fecha_inicial || "";
            if (axisEndEl) axisEndEl.value = axis.fecha_final || "";
            syncAxisDateBounds();
            updateAxisBasePreview();
            renderDepartmentOptions(axis.lider_departamento || "");
            loadAxisDepartmentCollaborators(axis.lider_departamento || "", axis.responsabilidad_directa || "");
            if (axisDescRich) {
              axisDescRich.setHtml(axis.descripcion || "");
            } else if (axisDescEl) {
              axisDescEl.value = axis.descripcion || "";
            }
            renderAxisObjectivesPanel();
          };

          const renderObjectives = () => {
            const axis = selectedAxis();
            if (objAxisTitleEl) {
              objAxisTitleEl.textContent = axis ? `Objetivos: ${axis.nombre || "Eje seleccionado"}` : "Objetivos";
            }
            if (!axis || !objListEl) {
              if (objListEl) objListEl.innerHTML = "";
              selectedObjectiveId = null;
              if (objNameEl) objNameEl.value = "";
              if (objCodeEl) objCodeEl.value = "";
              if (objProgressEl) objProgressEl.value = "0%";
              if (objDescRich) {
                objDescRich.setHtml("");
              } else if (objDescEl) {
                objDescEl.value = "";
              }
              if (objStartEl) objStartEl.value = "";
              if (objEndEl) objEndEl.value = "";
              renderCollaboratorOptions("");
              renderObjectiveMilestonesPanel();
              renderObjectiveKpisPanel();
              renderObjectiveActivitiesPanel();
              if (objListEl) objListEl.innerHTML = '<div class="axm-axis-meta">Selecciona un eje en la columna izquierda.</div>';
              return;
            }
            if (!selectedObjectiveId || !(axis.objetivos || []).some((obj) => obj.id === selectedObjectiveId)) {
              selectedObjectiveId = (axis.objetivos || [])[0]?.id || null;
            }
            objListEl.innerHTML = (axis.objetivos || []).map((obj) => `
              <button class="axm-obj-btn ${obj.id === selectedObjectiveId ? "active" : ""}" type="button" data-obj-id="${obj.id}">
                <strong>${obj.nombre || "Sin nombre"}</strong>
                <div class="axm-obj-code">${obj.codigo || "OBJ"}</div>
                <div class="axm-obj-sub">Hito: ${obj.hito || "N/D"} · Avance: ${Number(obj.avance || 0)}% · Fecha inicial: ${obj.fecha_inicial || "N/D"} · Fecha final: ${obj.fecha_final || "N/D"}</div>
              </button>
            `).join("");

            objListEl.querySelectorAll("[data-obj-id]").forEach((button) => {
              button.addEventListener("click", () => {
                selectedObjectiveId = Number(button.getAttribute("data-obj-id"));
                renderAll();
                openObjModal();
              });
            });

            const objective = selectedObjective();
            if (!objective) return;
            if (objNameEl) objNameEl.value = objective.nombre || "";
            if (objCodeEl) objCodeEl.value = buildObjectiveCode(axis.codigo || "", objectivePosition(objective));
            if (objProgressEl) objProgressEl.value = `${Number(objective.avance || 0)}%`;
            if (objDescRich) {
              objDescRich.setHtml(objective.descripcion || "");
            } else if (objDescEl) {
              objDescEl.value = objective.descripcion || "";
            }
            if (objStartEl) objStartEl.value = objective.fecha_inicial || "";
            if (objEndEl) objEndEl.value = objective.fecha_final || "";
            if (!Array.isArray(objective.hitos)) {
              objective.hitos = objective.hito ? [{ nombre: objective.hito, logrado: false, fecha_realizacion: "" }] : [];
            }
            renderCollaboratorOptions(objective.lider || "");
            renderObjectiveMilestonesPanel();
            renderObjectiveKpisPanel();
            renderObjectiveActivitiesPanel();
          };

          const renderAll = () => {
            renderAxisList();
            renderObjectiveAxisList();
            renderAxisEditor();
            renderObjectives();
            renderStrategicTree();
            renderTrackingBoard();
          };

          if (misionComposer) misionComposer.onChange(() => {
            renderStrategicTree();
            renderAxisEditor();
          });
          if (visionComposer) visionComposer.onChange(() => {
            renderStrategicTree();
            renderAxisEditor();
          });
          if (valoresComposer) valoresComposer.onChange(() => {
            renderAxisEditor();
          });
          document.querySelectorAll("[data-axis-tab]").forEach((tabBtn) => {
            tabBtn.addEventListener("click", () => {
              const tabKey = tabBtn.getAttribute("data-axis-tab");
              document.querySelectorAll("[data-axis-tab]").forEach((btn) => { btn.classList.remove("active"); btn.classList.remove("tab-active"); });
              document.querySelectorAll("[data-axis-panel]").forEach((panelItem) => panelItem.classList.remove("active"));
              tabBtn.classList.add("active");
              tabBtn.classList.add("tab-active");
              const panelItem = document.querySelector(`[data-axis-panel="${tabKey}"]`);
              if (panelItem) panelItem.classList.add("active");
            });
          });
          document.querySelectorAll("[data-obj-tab]").forEach((tabBtn) => {
            tabBtn.addEventListener("click", () => {
              const tabKey = tabBtn.getAttribute("data-obj-tab");
              document.querySelectorAll("[data-obj-tab]").forEach((btn) => { btn.classList.remove("active"); btn.classList.remove("tab-active"); });
              document.querySelectorAll("[data-obj-panel]").forEach((panelItem) => panelItem.classList.remove("active"));
              tabBtn.classList.add("active");
              tabBtn.classList.add("tab-active");
              const panelItem = document.querySelector(`[data-obj-panel="${tabKey}"]`);
              if (panelItem) panelItem.classList.add("active");
            });
          });
          hitoAddBtn && hitoAddBtn.addEventListener("click", () => {
            const objective = selectedObjective();
            if (!objective) {
              setHitoMsg("Selecciona un objetivo para agregar hitos.", true);
              return;
            }
            const item = readHitoForm();
            if (!item) return;
            const list = normalizeObjectiveMilestones(objective.hitos || []);
            if (editingHitoIndex >= 0 && editingHitoIndex < list.length) {
              list[editingHitoIndex] = item;
            } else {
              list.push(item);
            }
            objective.hitos = list;
            objective.hito = list.length ? String(list[0].nombre || "") : "";
            renderObjectiveMilestonesPanel();
            clearHitoForm();
            setHitoMsg("Hito listo. Guarda el objetivo para persistir en base de datos.");
          });
          hitoCancelBtn && hitoCancelBtn.addEventListener("click", () => {
            clearHitoForm();
            setHitoMsg("Edición de hito cancelada.");
          });
          kpiAddBtn && kpiAddBtn.addEventListener("click", () => {
            const objective = selectedObjective();
            if (!objective) {
              setKpiMsg("Selecciona un objetivo para agregar KPIs.", true);
              return;
            }
            const item = readKpiForm();
            if (!item) return;
            const list = normalizeObjectiveKpis(objective.kpis || []);
            if (editingKpiIndex >= 0 && editingKpiIndex < list.length) {
              list[editingKpiIndex] = item;
            } else {
              list.push(item);
            }
            objective.kpis = list;
            renderObjectiveKpisPanel();
            clearKpiForm();
            setKpiMsg("KPI listo. Guarda el objetivo para persistir en base de datos.");
          });
          kpiCancelBtn && kpiCancelBtn.addEventListener("click", () => {
            clearKpiForm();
            setKpiMsg("Edición de KPI cancelada.");
          });
          objSuggestIaBtn && objSuggestIaBtn.addEventListener("click", async () => {
            if (!(await iaFeatureEnabled("plan_estrategico"))) {
              showMsg("IA deshabilitada para tu rol en este módulo.", true);
              return;
            }
            const objective = selectedObjective();
            const axis = selectedAxis();
            if (!objective) {
              showMsg("Selecciona un objetivo para usar IA.", true);
              return;
            }
            const name = (objNameEl && objNameEl.value ? objNameEl.value : objective.nombre || "").trim();
            const descHtml = objDescRich ? objDescRich.getHtml() : (objDescEl && objDescEl.value ? objDescEl.value : "");
            const currentDesc = plainTextFromHtml(descHtml);
            if (!name && !currentDesc) {
              showMsg("Captura nombre o descripción para generar sugerencia.", true);
              return;
            }
            objSuggestIaBtn.disabled = true;
            showMsg("Generando sugerencia con IA...");
            try {
              const prompt = [
                "Mejora la redacción de un objetivo estratégico.",
                `Eje: ${String(axis?.nombre || "").trim() || "Sin eje"}`,
                `Objetivo: ${name || "Sin nombre"}`,
                `Descripción actual: ${currentDesc || "Sin descripción"}`,
                "Responde solo con el texto final recomendado, en español, claro y conciso.",
              ].join("\\n");
              const draftResp = await requestJson("/api/ia/suggestions", {
                method: "POST",
                body: JSON.stringify({
                  prompt,
                  original_text: currentDesc,
                  target_module: "plan_estrategico",
                  target_entity: "objetivo",
                  target_entity_id: String(objective.id || ""),
                  target_field: "descripcion",
                }),
              });
              const draft = draftResp.data || {};
              const decision = await openIaSuggestionEditor({
                title: "Sugerencia IA para descripción de objetivo",
                suggestion: String(draft.suggested_text || ""),
              });
              if (decision.action === "apply") {
                const applyResp = await requestJson(`/api/ia/suggestions/${draft.id}/apply`, {
                  method: "POST",
                  body: JSON.stringify({ edited_text: String(decision.text || "").trim() }),
                });
                const appliedText = String(applyResp?.data?.applied_text || decision.text || "").trim();
                if (objDescRich) objDescRich.setHtml(appliedText);
                else if (objDescEl) objDescEl.value = appliedText;
                showMsg("Sugerencia IA aplicada en la descripción del objetivo.");
              } else if (decision.action === "discard") {
                await requestJson(`/api/ia/suggestions/${draft.id}/discard`, {
                  method: "POST",
                  body: JSON.stringify({ reason: "Descartada por usuario", edited_text: String(decision.text || "").trim() }),
                });
                showMsg("Sugerencia IA descartada.");
              } else {
                showMsg("Sugerencia IA generada. Puedes volver a abrir IA para aplicarla o descartarla.");
              }
            } catch (error) {
              showMsg(error.message || "No se pudo generar sugerencia IA.", true);
            } finally {
              objSuggestIaBtn.disabled = false;
            }
          });
          kpiSuggestIaBtn && kpiSuggestIaBtn.addEventListener("click", async () => {
            if (!(await iaFeatureEnabled("plan_estrategico"))) {
              setKpiMsg("IA deshabilitada para tu rol en este módulo.", true);
              return;
            }
            const objective = selectedObjective();
            const axis = selectedAxis();
            if (!objective) {
              setKpiMsg("Selecciona un objetivo para sugerir KPI.", true);
              return;
            }
            const objectiveName = (objNameEl && objNameEl.value ? objNameEl.value : objective.nombre || "").trim();
            const axisName = String(axis?.nombre || "").trim();
            const kpiName = (kpiNameEl && kpiNameEl.value ? kpiNameEl.value : "").trim();
            const currentPurpose = (kpiPurposeEl && kpiPurposeEl.value ? kpiPurposeEl.value : "").trim();
            const currentFormula = (kpiFormulaEl && kpiFormulaEl.value ? kpiFormulaEl.value : "").trim();
            if (!objectiveName && !kpiName) {
              setKpiMsg("Captura al menos el nombre del objetivo o del KPI para usar IA.", true);
              return;
            }
            kpiSuggestIaBtn.disabled = true;
            setKpiMsg("Generando sugerencia IA para KPI...");
            try {
              const prompt = [
                "Genera propuesta de KPI para objetivo estratégico.",
                `Eje: ${axisName || "Sin eje"}`,
                `Objetivo: ${objectiveName || "Sin nombre"}`,
                `KPI actual: ${kpiName || "Sin nombre"}`,
                `Propósito actual: ${currentPurpose || "Sin propósito"}`,
                `Fórmula actual: ${currentFormula || "Sin fórmula"}`,
                "Devuelve texto en español con formato:",
                "Nombre: ...",
                "Propósito: ...",
                "Fórmula: ...",
                "Periodicidad: ...",
                "Estándar: ...",
              ].join("\\n");
              const draftResp = await requestJson("/api/ia/suggestions", {
                method: "POST",
                body: JSON.stringify({
                  prompt,
                  original_text: `${currentPurpose}\n${currentFormula}`.trim(),
                  target_module: "plan_estrategico",
                  target_entity: "kpi",
                  target_entity_id: String(objective.id || ""),
                  target_field: "proposito",
                }),
              });
              const draft = draftResp.data || {};
              const decision = await openIaSuggestionEditor({
                title: "Sugerencia IA para KPI",
                suggestion: String(draft.suggested_text || ""),
              });
              if (decision.action === "apply") {
                const applyResp = await requestJson(`/api/ia/suggestions/${draft.id}/apply`, {
                  method: "POST",
                  body: JSON.stringify({ edited_text: String(decision.text || "").trim() }),
                });
                const appliedText = String(applyResp?.data?.applied_text || decision.text || "").trim();
                if (kpiPurposeEl) kpiPurposeEl.value = appliedText;
                setKpiMsg("Sugerencia IA aplicada. Ajusta y guarda el KPI.");
              } else if (decision.action === "discard") {
                await requestJson(`/api/ia/suggestions/${draft.id}/discard`, {
                  method: "POST",
                  body: JSON.stringify({ reason: "Descartada por usuario", edited_text: String(decision.text || "").trim() }),
                });
                setKpiMsg("Sugerencia IA descartada.");
              } else {
                setKpiMsg("Sugerencia IA generada. Puedes volver a abrir IA para aplicarla o descartarla.");
              }
            } catch (error) {
              setKpiMsg(error.message || "No se pudo generar sugerencia IA para KPI.", true);
            } finally {
              kpiSuggestIaBtn.disabled = false;
            }
          });

          const loadAxes = async () => {
            const payload = await requestJson("/api/strategic-axes");
            axes = Array.isArray(payload.data) ? payload.data : [];
            axes.forEach((axis) => {
              (Array.isArray(axis.objetivos) ? axis.objetivos : []).forEach((obj) => {
                if (!Array.isArray(obj.hitos)) {
                  obj.hitos = obj.hito ? [{ nombre: obj.hito, logrado: false, fecha_realizacion: "" }] : [];
                }
              });
            });
            const currentId = toId(selectedAxisId);
            if (!currentId || !axes.some((axis) => toId(axis.id) === currentId)) {
              selectedAxisId = axes.length ? toId(axes[0].id) : null;
            }
            renderAll();
          };

          const loadDepartments = async () => {
            const payload = await requestJson("/api/strategic-axes/departments");
            departments = Array.isArray(payload.data) ? payload.data : [];
            renderDepartmentOptions(selectedAxis()?.lider_departamento || "");
          };

          const loadCollaborators = async () => {
            const axis = selectedAxis();
            if (!axis || !axis.id) {
              collaborators = [];
              setCollaboratorLoading(false);
              renderCollaboratorOptions("");
              return;
            }
            setCollaboratorLoading(true);
            try {
              const payload = await requestJson(`/api/strategic-axes/${axis.id}/collaborators`);
              collaborators = Array.isArray(payload.data) ? payload.data : [];
              renderCollaboratorOptions(selectedObjective()?.lider || "");
            } finally {
              setCollaboratorLoading(false);
            }
          };

          const applyEntryIntent = () => {
            if (entryIntentDone) return;
            const wantsObjectives = entryTabTarget === "objetivos" || entryOpenTarget === "objective";
            if (!wantsObjectives) return;

            const objetivosTab = document.querySelector('.axm-tab[data-axm-tab="objetivos"]');
            if (objetivosTab) {
              tabs.forEach((btn) => { btn.classList.remove("active"); btn.classList.remove("tab-active"); });
              objetivosTab.classList.add("active");
              objetivosTab.classList.add("tab-active");
            }
            applyTabView("objetivos");

            const desiredAxisId = toId(entryAxisIdRaw);
            if (desiredAxisId && axes.some((axis) => toId(axis.id) === desiredAxisId)) {
              selectedAxisId = desiredAxisId;
            }
            renderAll();

            entryIntentDone = true;
            if (window.history && typeof window.history.replaceState === "function") {
              window.history.replaceState({}, "", window.location.pathname);
            }

            if (entryOpenTarget === "objective" && addObjBtn) {
              setTimeout(() => addObjBtn.click(), 0);
            }
          };

          const importStrategicCsv = async (file) => {
            if (!file) return;
            showMsg("Importando plantilla estratégica y POA...");
            const formData = new FormData();
            formData.append("file", file);
            const response = await fetch("/api/planificacion/importar-plan-poa", {
              method: "POST",
              credentials: "same-origin",
              body: formData,
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok || payload.success === false) {
              throw new Error(payload.error || "No se pudo importar el archivo.");
            }
            await Promise.all([loadDepartments(), loadAxes()]);
            await loadCollaborators();
            await loadObjectiveActivities();
            const summary = payload.summary || {};
            const created = Number(summary.created || 0);
            const updated = Number(summary.updated || 0);
            const skipped = Number(summary.skipped || 0);
            const errors = Array.isArray(summary.errors) ? summary.errors.length : 0;
            showMsg(`Importación completada. Creados: ${created}, actualizados: ${updated}, omitidos: ${skipped}, errores: ${errors}.`, errors > 0);
          };

          downloadTemplateBtn && downloadTemplateBtn.addEventListener("click", () => {
            window.location.href = "/api/planificacion/plantilla-plan-poa.csv";
          });
          importCsvBtn && importCsvBtn.addEventListener("click", () => {
            if (importCsvFileEl) importCsvFileEl.click();
          });
          importCsvFileEl && importCsvFileEl.addEventListener("change", async () => {
            const file = importCsvFileEl.files && importCsvFileEl.files[0];
            if (!file) return;
            try {
              await importStrategicCsv(file);
            } catch (err) {
              showMsg(err.message || "No se pudo importar el archivo CSV.", true);
            } finally {
              importCsvFileEl.value = "";
            }
          });

          addAxisBtn && addAxisBtn.addEventListener("click", async () => {
            showMsg("Creando eje...");
            addAxisBtn.disabled = true;
            openAxisModal();
            try {
              const payload = await requestJson("/api/strategic-axes", {
                method: "POST",
                body: JSON.stringify({
                  nombre: "Nuevo eje estratégico (editar nombre)",
                  base_code: getIdentityCodeOptions()[0] || "m1",
                  codigo: "",
                  lider_departamento: "",
                  responsabilidad_directa: "",
                  fecha_inicial: "",
                  fecha_final: "",
                  descripcion: "",
                  orden: axes.length + 1,
                }),
              });
              selectedAxisId = toId(payload.data?.id);
              await loadAxes();
              await loadCollaborators();
              showMsg(`Eje agregado${selectedAxisId ? ` (ID ${selectedAxisId})` : ""}.`);
              if (axisNameEl) {
                axisNameEl.focus();
                axisNameEl.select();
              }
            } catch (err) {
              showMsg(err.message || "No se pudo crear el eje.", true);
            } finally {
              addAxisBtn.disabled = false;
            }
          });

          editAxisBtn && editAxisBtn.addEventListener("click", async () => {
            const axis = selectedAxis();
            if (!axis) {
              showMsg("Selecciona un eje para editar.", true);
              return;
            }
            openAxisModal();
            if (axisNameEl) {
              axisNameEl.focus();
              axisNameEl.select();
            }
            showMsg("Edición habilitada para el eje seleccionado.");
          });

          saveAxisBtn && saveAxisBtn.addEventListener("click", async () => {
            const axis = selectedAxis();
            if (!axis) {
              showMsg("Selecciona un eje para guardar.", true);
              return;
            }
            const body = {
              nombre: axisNameEl.value.trim(),
              base_code: axisBaseCodeEl && axisBaseCodeEl.value ? axisBaseCodeEl.value.trim() : "",
              codigo: axisCodeEl && axisCodeEl.value ? axisCodeEl.value.trim() : "",
              lider_departamento: axisLeaderEl && axisLeaderEl.value ? axisLeaderEl.value.trim() : "",
              responsabilidad_directa: axisOwnerEl && axisOwnerEl.value ? axisOwnerEl.value.trim() : "",
              fecha_inicial: axisStartEl && axisStartEl.value ? axisStartEl.value : "",
              fecha_final: axisEndEl && axisEndEl.value ? axisEndEl.value : "",
              descripcion: (axisDescRich ? axisDescRich.getHtml() : (axisDescEl ? axisDescEl.value : "")).trim(),
              orden: axisPosition(axis),
            };
            if (!body.nombre) {
              showMsg("El nombre del eje es obligatorio.", true);
              return;
            }
            const axisDateError = visualRangeError(body.fecha_inicial, body.fecha_final, "Eje estratégico");
            if (axisDateError) {
              showMsg(axisDateError, true);
              return;
            }
            const planDateError = validateAxisWithinPlan(body.fecha_inicial, body.fecha_final);
            if (planDateError) {
              showMsg(planDateError, true);
              return;
            }
            try {
              await requestJson(`/api/strategic-axes/${axis.id}`, { method: "PUT", body: JSON.stringify(body) });
              await loadAxes();
              await loadCollaborators();
              showMsg("Eje guardado correctamente.");
            } catch (err) {
              showMsg(err.message || "No se pudo guardar el eje.", true);
            }
          });

          deleteAxisBtn && deleteAxisBtn.addEventListener("click", async () => {
            const axis = selectedAxis();
            if (!axis) return;
            if (!window.confirm("¿Eliminar este eje y todos sus objetivos?")) return;
            try {
              await requestJson(`/api/strategic-axes/${axis.id}`, { method: "DELETE" });
              selectedAxisId = null;
              await loadAxes();
              await loadCollaborators();
              showMsg("Eje eliminado.");
              closeAxisModal();
            } catch (err) {
              showMsg(err.message || "No se pudo eliminar el eje.", true);
            }
          });

          addObjBtn && addObjBtn.addEventListener("click", async () => {
            const axis = selectedAxis();
            if (!axis) {
              showMsg("Primero selecciona un eje.", true);
              return;
            }
            openObjModal();
            const body = {
              codigo: buildObjectiveCode(axis.codigo || "", (axis.objetivos || []).length + 1),
              nombre: "Nuevo objetivo",
              hitos: [],
              lider: "",
              descripcion: "",
              orden: (axis.objetivos || []).length + 1,
            };
            try {
              const payload = await requestJson(`/api/strategic-axes/${axis.id}/objectives`, { method: "POST", body: JSON.stringify(body) });
              await loadAxes();
              selectedObjectiveId = payload.data?.id || selectedObjectiveId;
              renderAll();
              showMsg("Objetivo agregado.");
              if (objNameEl) {
                objNameEl.focus();
                objNameEl.select();
              }
            } catch (err) {
              showMsg(err.message || "No se pudo agregar el objetivo.", true);
            }
          });

          editObjBtn && editObjBtn.addEventListener("click", () => {
            const objective = selectedObjective();
            if (!objective) {
              showMsg("Selecciona un objetivo para editar.", true);
              return;
            }
            openObjModal();
            if (objNameEl) {
              objNameEl.focus();
              objNameEl.select();
            }
            showMsg("Edición habilitada para el objetivo seleccionado.");
          });

          saveObjBtn && saveObjBtn.addEventListener("click", async () => {
            const objective = selectedObjective();
            if (!objective) {
              showMsg("Selecciona un objetivo.", true);
              return;
            }
            const body = {
              nombre: objNameEl && objNameEl.value ? objNameEl.value.trim() : "",
              codigo: objCodeEl && objCodeEl.value ? objCodeEl.value.trim() : "",
              lider: objLeaderEl && objLeaderEl.value ? objLeaderEl.value.trim() : "",
              fecha_inicial: objStartEl && objStartEl.value ? objStartEl.value : "",
              fecha_final: objEndEl && objEndEl.value ? objEndEl.value : "",
              descripcion: (objDescRich ? objDescRich.getHtml() : (objDescEl && objDescEl.value ? objDescEl.value : "")).trim(),
              hitos: normalizeObjectiveMilestones(objective.hitos || []),
              kpis: normalizeObjectiveKpis(objective.kpis || []),
              orden: objectivePosition(objective),
            };
            if (!body.nombre) {
              showMsg("El nombre del objetivo es obligatorio.", true);
              return;
            }
            const objectiveDateError = visualRangeError(body.fecha_inicial, body.fecha_final, "Objetivo");
            if (objectiveDateError) {
              showMsg(objectiveDateError, true);
              return;
            }
            try {
              await requestJson(`/api/strategic-objectives/${objective.id}`, { method: "PUT", body: JSON.stringify(body) });
              await loadAxes();
              renderAll();
              showMsg("Objetivo guardado correctamente.");
            } catch (err) {
              showMsg(err.message || "No se pudo guardar el objetivo.", true);
            }
          });

          deleteObjBtn && deleteObjBtn.addEventListener("click", async () => {
            const objective = selectedObjective();
            if (!objective) return;
            if (!window.confirm("¿Eliminar este objetivo?")) return;
            try {
              await requestJson(`/api/strategic-objectives/${objective.id}`, { method: "DELETE" });
              selectedObjectiveId = null;
              await loadAxes();
              renderAll();
              showMsg("Objetivo eliminado.");
            } catch (err) {
              showMsg(err.message || "No se pudo eliminar el objetivo.", true);
            }
          });

          axisLeaderEl && axisLeaderEl.addEventListener("change", async () => {
            await loadAxisDepartmentCollaborators(axisLeaderEl.value || "", "");
          });
          planYearsEl && planYearsEl.addEventListener("change", () => {
            savePlanWindow();
            syncAxisDateBounds();
          });
          planStartEl && planStartEl.addEventListener("change", () => {
            savePlanWindow();
            syncAxisDateBounds();
          });
          loadPlanWindow();
          syncAxisDateBounds();

          Promise.all([loadDepartments(), loadAxes()]).then(async () => {
            await loadCollaborators();
            applyEntryIntent();
          }).catch((err) => {
            showMsg(err.message || "No se pudieron cargar los ejes.", true);
          });
          iaFeatureEnabled("plan_estrategico").then((enabled) => {
            [objSuggestIaBtn, kpiSuggestIaBtn].forEach((btn) => {
              if (!btn) return;
              btn.disabled = !enabled;
              btn.style.opacity = enabled ? "1" : "0.55";
              btn.style.cursor = enabled ? "pointer" : "not-allowed";
              if (!enabled) btn.title = "IA deshabilitada para tu rol/módulo";
            });
          });
          loadObjectiveActivities();
        })();
      </script>
    </section>
""")

POA_LIMPIO_HTML = dedent("""
    <section class="poa-board-wrap">

      <div class="poa-board-head">
        <div class="poa-board-head-row">
          <div>
            <h2>Tablero POA por eje</h2>
            <p>Cada columna corresponde a un eje y contiene las tarjetas de sus objetivos.</p>
          </div>
          <div class="poa-board-head-actions">
            <button type="button" class="poa-btn" id="poa-download-template">Descargar plantilla CSV</button>
            <button type="button" class="poa-btn" id="poa-export-xls">Exportar plan + POA XLS</button>
            <button type="button" class="poa-btn" id="poa-import-csv">Importar CSV estratégico + POA</button>
            <input id="poa-import-csv-file" type="file" accept=".csv,text/csv">
          </div>
        </div>
      </div>
      <div class="poa-board-msg" id="poa-board-msg" aria-live="polite"></div>
      <div class="axm-track-missing" id="poa-no-owner-msg" aria-live="polite"></div>
      <div class="axm-track-missing" id="poa-no-subowner-msg" aria-live="polite"></div>
      <section class="poa-owner-chart" id="poa-owner-chart">
        <div class="poa-owner-chart-head">
          <div>
            <h3 class="poa-owner-chart-title">Concentración de actividades por usuario</h3>
            <p class="poa-owner-chart-sub">Distribución de actividades POA asignadas por responsable.</p>
          </div>
          <span class="poa-owner-chart-total" id="poa-owner-chart-total">Total: 0</span>
        </div>
        <div class="poa-owner-chart-empty" id="poa-owner-chart-empty">Sin actividades con responsable.</div>
        <div class="poa-owner-chart-list" id="poa-owner-chart-list"></div>
      </section>
      <div class="poa-board-grid" id="poa-board-grid"></div>
      <div class="poa-modal" id="poa-tree-modal" role="dialog" aria-modal="true" aria-labelledby="poa-tree-title">
        <section class="poa-modal-dialog">
          <div class="poa-modal-head">
            <h3 id="poa-tree-title">Árbol de avance</h3>
            <button class="poa-modal-close" id="poa-tree-close" type="button" aria-label="Cerrar">×</button>
          </div>
          <div class="poa-tree-wrap">
            <p class="poa-tree-help">Vista compactada por defecto. Usa "Mostrar" para abrir solo el bloque siguiente.</p>
            <div class="poa-tree-grid" id="poa-tree-host"></div>
          </div>
        </section>
      </div>
      <div class="poa-modal" id="poa-gantt-modal" role="dialog" aria-modal="true" aria-labelledby="poa-gantt-title">
        <section class="poa-modal-dialog">
          <div class="poa-modal-head">
            <h3 id="poa-gantt-title">Vista Gantt POA</h3>
            <button class="poa-modal-close" id="poa-gantt-close" type="button" aria-label="Cerrar">×</button>
          </div>
          <div class="poa-gantt-wrap">
            <div class="poa-gantt-legend">
              <span class="poa-gantt-chip"><span class="poa-gantt-dot"></span>Objetivo estratégico</span>
              <span class="poa-gantt-chip"><span class="poa-gantt-dot"></span>Actividad POA</span>
              <span class="poa-gantt-chip"><span class="poa-gantt-dot"></span>Hoy</span>
            </div>
            <div class="poa-gantt-controls">
              <div class="poa-gantt-actions">
                <button type="button" class="poa-gantt-action" id="poa-gantt-show-all">Mostrar bloques</button>
                <button type="button" class="poa-gantt-action" id="poa-gantt-hide-all">Ocultar bloques</button>
              </div>
              <div class="poa-gantt-blocks" id="poa-gantt-blocks"></div>
            </div>
            <div class="poa-gantt-host" id="poa-gantt-host"></div>
          </div>
        </section>
      </div>
      <div class="poa-modal" id="poa-calendar-modal" role="dialog" aria-modal="true" aria-labelledby="poa-calendar-title">
        <section class="poa-modal-dialog">
          <div class="poa-modal-head">
            <h3 id="poa-calendar-title">Vista Calendario POA</h3>
            <button class="poa-modal-close" id="poa-calendar-close" type="button" aria-label="Cerrar">×</button>
          </div>
          <div class="poa-cal-wrap">
            <div class="poa-cal-head">
              <div class="poa-cal-nav">
                <button type="button" class="poa-gantt-action" id="poa-calendar-prev">◀</button>
                <button type="button" class="poa-gantt-action" id="poa-calendar-today">Hoy</button>
                <button type="button" class="poa-gantt-action" id="poa-calendar-next">▶</button>
              </div>
              <h4 class="poa-cal-title" id="poa-calendar-month"></h4>
            </div>
            <div class="poa-cal-grid" id="poa-calendar-grid"></div>
          </div>
        </section>
      </div>
      <div class="poa-modal" id="poa-activity-modal" role="dialog" aria-modal="true" aria-labelledby="poa-activity-title">
        <section class="poa-modal-dialog">
          <div class="poa-modal-head">
            <div>
              <h3 id="poa-activity-title">Nueva actividad</h3>
              <p id="poa-activity-subtitle"></p>
            </div>
            <button class="poa-modal-close" id="poa-activity-close" type="button" aria-label="Cerrar">×</button>
          </div>
          <p class="poa-branch-path" id="poa-activity-branch"></p>
          <div class="poa-summary">
            <div class="poa-summary-item">
              <div class="poa-summary-label">Estatus</div>
              <div class="poa-summary-value" id="poa-status-value"><span class="poa-semaforo gray"></span>No iniciado</div>
            </div>
            <div class="poa-summary-item">
              <div class="poa-summary-label">Avance</div>
              <div class="poa-summary-value" id="poa-progress-value">0%</div>
            </div>
          </div>
          <div class="poa-state-strip" id="poa-state-strip">
            <button type="button" class="poa-state-btn" id="poa-state-no-iniciado" disabled>No iniciado</button>
            <button type="button" class="poa-state-btn" id="poa-state-en-proceso">En proceso</button>
            <button type="button" class="poa-state-btn" id="poa-state-terminado">Terminado</button>
            <button type="button" class="poa-state-btn" id="poa-state-en-revision" disabled>En revisión</button>
          </div>
          <div class="poa-state-actions" id="poa-state-actions">
            <button type="button" class="poa-btn" id="poa-approval-approve">Aprobar entregable</button>
            <button type="button" class="poa-btn" id="poa-approval-reject">Rechazar entregable</button>
          </div>
          <section class="poa-act-list-panel">
            <div class="poa-act-list-head">
              <h4 class="poa-act-list-title">Actividades del objetivo</h4>
              <div class="poa-act-actions">
                <button type="button" class="action-button" id="poa-act-new" data-hover-label="Nuevo" aria-label="Nuevo" title="Nuevo">
                  <img src="/icon/boton/nuevo.svg" alt="Nuevo">
                  <span class="action-label">Nuevo</span>
                </button>
                <button type="button" class="action-button" id="poa-act-edit" data-hover-label="Editar" aria-label="Editar" title="Editar">
                  <img src="/icon/boton/editar.svg" alt="Editar">
                  <span class="action-label">Editar</span>
                </button>
                <button type="button" class="action-button" id="poa-act-save-top" data-hover-label="Guardar" aria-label="Guardar" title="Guardar">
                  <img src="/icon/boton/guardar.svg" alt="Guardar">
                  <span class="action-label">Guardar</span>
                </button>
                <button type="button" class="action-button" id="poa-act-delete" data-hover-label="Eliminar" aria-label="Eliminar" title="Eliminar">
                  <img src="/icon/boton/eliminar.svg" alt="Eliminar">
                  <span class="action-label">Eliminar</span>
                </button>
              </div>
            </div>
            <div class="poa-act-list" id="poa-act-list"></div>
            <div class="poa-act-list-msg" id="poa-act-list-msg"></div>
          </section>

          <div class="poa-form-grid">
            <p class="poa-assigned-by" id="poa-assigned-by">Asignado por: N/D</p>
            <div class="poa-field">
              <label for="poa-act-name">Nombre</label>
              <input id="poa-act-name" class="poa-input" type="text" placeholder="Nombre de la actividad">
            </div>
            <div class="poa-row">
              <div class="poa-field">
                <label for="poa-act-owner">Responsable</label>
                <select id="poa-act-owner" class="poa-select">
                  <option value="">Selecciona responsable</option>
                </select>
              </div>
              <div class="poa-field">
                <label for="poa-act-assigned">Personas asignadas</label>
                <select id="poa-act-assigned" class="poa-select" multiple></select>
              </div>
            </div>
            <div class="poa-row">
              <div class="poa-field">
                <label for="poa-act-start">Fecha inicial</label>
                <input id="poa-act-start" class="poa-input" type="date">
              </div>
              <div class="poa-field">
                <label for="poa-act-end">Fecha final</label>
                <input id="poa-act-end" class="poa-input" type="date">
              </div>
            </div>
            <div class="poa-field">
              <label for="poa-act-impact-hitos">Hitos que impacta</label>
              <select id="poa-act-impact-hitos" class="poa-select" multiple></select>
            </div>
            <div class="poa-row">
              <div class="poa-field">
                <label for="poa-act-recurrente">Recurrente</label>
                <label>
                  <input id="poa-act-recurrente" type="checkbox">
                  Habilitar recurrencia
                </label>
              </div>
              <div class="poa-field">
                <label for="poa-act-periodicidad">Periodicidad</label>
                <select id="poa-act-periodicidad" class="poa-select" disabled>
                  <option value="">Selecciona periodicidad</option>
                  <option value="diaria">diaria</option>
                  <option value="semanal">semanal</option>
                  <option value="quincenal">quincenal</option>
                  <option value="mensual">mensual</option>
                  <option value="bimensual">bimensual</option>
                  <option value="cada_xx_dias">Cada xx dias</option>
                </select>
              </div>
            </div>
            <div class="poa-field" id="poa-act-every-days-wrap">
              <label for="poa-act-every-days">Cada xx dias</label>
              <input id="poa-act-every-days" class="poa-input" type="number" min="1" step="1" placeholder="Ej. 3">
            </div>
          </div>

          <div class="tabs tabs-lifted w-full flex-wrap poa-tabs" id="poa-tabs" role="tablist" aria-label="POA">
            <button type="button" class="tab rounded-t-lg tab-active active poa-tab" data-poa-tab="desc">Descripción</button>
            <button type="button" class="tab rounded-t-lg poa-tab" data-poa-tab="sub">Subtareas</button>
            <button type="button" class="tab rounded-t-lg poa-tab" data-poa-tab="kpi">Kpis</button>
            <button type="button" class="tab rounded-t-lg poa-tab" data-poa-tab="deliverables">Entregables</button>
            <button type="button" class="tab rounded-t-lg poa-tab" data-poa-tab="budget">Presupuesto</button>
          </div>
          <section class="poa-tab-panel active" data-poa-panel="desc">
            <div class="poa-field">
              <label for="poa-act-desc">Descripción</label>
              <textarea id="poa-act-desc" class="poa-textarea" placeholder="Descripción de la actividad"></textarea>
            </div>
            <div class="poa-actions">
              <button type="button" class="poa-btn" id="poa-act-suggest-ia">Sugerir con IA</button>
            </div>
          </section>
          <section class="poa-tab-panel" data-poa-panel="sub">
            <div class="poa-sub-header">
              <p id="poa-sub-hint">Guarda primero la actividad para habilitar subtareas.</p>
              <button type="button" class="poa-btn" id="poa-sub-add">Agregar subtarea</button>
            </div>
            <div class="poa-sub-list" id="poa-sub-list"></div>
          </section>
          <section class="poa-tab-panel" data-poa-panel="kpi">
            <p>Kpis: en construcción.</p>
          </section>
          <section class="poa-tab-panel" data-poa-panel="deliverables">
            <div class="poa-deliv-form">
              <div class="poa-deliv-row">
                <div class="poa-field">
                  <label for="poa-deliv-name">Entregable</label>
                  <input id="poa-deliv-name" class="poa-input" type="text" placeholder="Nombre del entregable">
                </div>
                <button type="button" class="poa-btn" id="poa-deliv-add">Agregar</button>
              </div>
              <div class="poa-deliv-list" id="poa-deliv-list">
                <div class="poa-sub-meta">Sin entregables registrados.</div>
              </div>
              <div class="poa-deliv-msg" id="poa-deliv-msg" aria-live="polite"></div>
            </div>
          </section>
          <section class="poa-tab-panel" data-poa-panel="budget">
            <div class="poa-budget-form">
              <div class="poa-row">
                <div class="poa-field">
                  <label for="poa-budget-type">Tipo</label>
                  <select id="poa-budget-type" class="poa-select">
                    <option value="">Selecciona tipo</option>
                    <option value="Sueldos y similares">Sueldos y similares</option>
                    <option value="Honorarios">Honorarios</option>
                    <option value="Gastos de promoción y publicidad">Gastos de promoción y publicidad</option>
                    <option value="Gastos no deducibles">Gastos no deducibles</option>
                    <option value="Gastos en tecnologia">Gastos en tecnologia</option>
                    <option value="Otros gastos de administración y promoción">Otros gastos de administración y promoción</option>
                  </select>
                </div>
                <div class="poa-field">
                  <label for="poa-budget-rubro">Rubro</label>
                  <input id="poa-budget-rubro" class="poa-input" type="text" placeholder="Rubro presupuestal">
                </div>
              </div>
              <div class="poa-row">
                <div class="poa-field">
                  <label for="poa-budget-monthly">Mensual</label>
                  <input id="poa-budget-monthly" class="poa-input num" type="number" min="0" step="0.01" placeholder="0.00">
                </div>
                <div class="poa-field">
                  <label for="poa-budget-annual">Anual</label>
                  <input id="poa-budget-annual" class="poa-input num" type="number" min="0" step="0.01" placeholder="Mensual x 12 o monto único">
                </div>
              </div>
              <div class="poa-row">
                <div class="poa-field">
                  <label>
                    <input id="poa-budget-approved" type="checkbox">
                    Autorizado
                  </label>
                </div>
                <div class="poa-field">
                  <div class="poa-actions">
                    <button type="button" class="poa-btn primary" id="poa-budget-add">Agregar rubro</button>
                    <button type="button" class="poa-btn" id="poa-budget-cancel">Cancelar</button>
                  </div>
                </div>
              </div>
            </div>
            <div class="poa-budget-table-wrap">
              <table class="poa-budget-table">
                <thead>
                  <tr>
                    <th>Tipo</th>
                    <th>Rubro</th>
                    <th class="num">Mensual</th>
                    <th class="num">Anual</th>
                    <th>Autorizado</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody id="poa-budget-list">
                  <tr><td colspan="6">Sin rubros registrados.</td></tr>
                </tbody>
              </table>
            </div>
            <div class="poa-budget-total">
              <span>Mensual total: <b id="poa-budget-monthly-total">0.00</b></span>
              <span>Anual total: <b id="poa-budget-annual-total">0.00</b></span>
            </div>
            <div class="poa-modal-msg" id="poa-budget-msg" aria-live="polite"></div>
          </section>

          <div class="poa-actions">
            <button type="button" class="action-button" id="poa-act-edit-bottom" data-hover-label="Editar" aria-label="Editar" title="Editar">
              <img src="/icon/boton/editar.svg" alt="Editar">
              <span class="action-label">Editar</span>
            </button>
            <button type="button" class="action-button" id="poa-act-save" data-hover-label="Guardar" aria-label="Guardar" title="Guardar">
              <img src="/icon/boton/guardar.svg" alt="Guardar">
              <span class="action-label">Guardar</span>
            </button>
            <button type="button" class="poa-btn" id="poa-act-cancel">Cancelar</button>
          </div>
          <div class="poa-modal-msg" id="poa-act-msg" aria-live="polite"></div>
        </section>
      </div>
      <div class="poa-modal" id="poa-sub-modal" role="dialog" aria-modal="true" aria-labelledby="poa-sub-title">
        <section class="poa-modal-dialog">
          <div class="poa-modal-head">
            <h3 id="poa-sub-title">Subtarea</h3>
            <button class="poa-modal-close" id="poa-sub-close" type="button" aria-label="Cerrar">×</button>
          </div>
          <p class="poa-branch-path" id="poa-sub-branch"></p>
          <div class="poa-form-grid">
            <div class="poa-field">
              <label for="poa-sub-name">Nombre</label>
              <input id="poa-sub-name" class="poa-input" type="text" placeholder="Nombre de la subtarea">
            </div>
            <div class="poa-row">
              <div class="poa-field">
                <label for="poa-sub-owner">Responsable</label>
                <select id="poa-sub-owner" class="poa-select">
                  <option value="">Selecciona responsable</option>
                </select>
              </div>
              <div class="poa-field">
                <label for="poa-sub-assigned">Personas asignadas</label>
                <select id="poa-sub-assigned" class="poa-select" multiple></select>
              </div>
            </div>
            <div class="poa-row">
              <div class="poa-field">
                <label for="poa-sub-start">Fecha inicial</label>
                <input id="poa-sub-start" class="poa-input" type="date">
              </div>
              <div class="poa-field">
                <label for="poa-sub-end">Fecha final</label>
                <input id="poa-sub-end" class="poa-input" type="date">
              </div>
            </div>
            <div class="poa-row">
              <div class="poa-field">
                <label for="poa-sub-recurrente">Recurrente</label>
                <label>
                  <input id="poa-sub-recurrente" type="checkbox">
                  Habilitar recurrencia
                </label>
              </div>
              <div class="poa-field">
                <label for="poa-sub-periodicidad">Periodicidad</label>
                <select id="poa-sub-periodicidad" class="poa-select" disabled>
                  <option value="">Selecciona periodicidad</option>
                  <option value="diaria">diaria</option>
                  <option value="semanal">semanal</option>
                  <option value="quincenal">quincenal</option>
                  <option value="mensual">mensual</option>
                  <option value="bimensual">bimensual</option>
                  <option value="cada_xx_dias">Cada xx dias</option>
                </select>
              </div>
            </div>
            <div class="poa-field" id="poa-sub-every-days-wrap">
              <label for="poa-sub-every-days">Cada xx dias</label>
              <input id="poa-sub-every-days" class="poa-input" type="number" min="1" step="1" placeholder="Ej. 3">
            </div>
            <div class="poa-field">
              <label for="poa-sub-desc">Descripción</label>
              <textarea id="poa-sub-desc" class="poa-textarea" placeholder="Descripción de la subtarea"></textarea>
            </div>
          </div>
          <div class="poa-actions">
            <button type="button" class="poa-btn primary" id="poa-sub-save">Guardar subtarea</button>
            <button type="button" class="poa-btn" id="poa-sub-cancel">Cancelar</button>
          </div>
          <div class="poa-modal-msg" id="poa-sub-msg" aria-live="polite"></div>
        </section>
      </div>

      <script>
        (() => {
          const gridEl = document.getElementById("poa-board-grid");
          const openTreeBtn = document.querySelector('.view-pill[data-view="arbol"]');
          const openGanttBtn = document.querySelector('.view-pill[data-view="gantt"]');
          const openCalendarBtn = document.querySelector('.view-pill[data-view="calendar"]');
          const msgEl = document.getElementById("poa-board-msg");
          const noOwnerMsgEl = document.getElementById("poa-no-owner-msg");
          const noSubOwnerMsgEl = document.getElementById("poa-no-subowner-msg");
          const ownerChartTotalEl = document.getElementById("poa-owner-chart-total");
          const ownerChartEmptyEl = document.getElementById("poa-owner-chart-empty");
          const ownerChartListEl = document.getElementById("poa-owner-chart-list");
          const treeModalEl = document.getElementById("poa-tree-modal");
          const treeCloseBtn = document.getElementById("poa-tree-close");
          const treeHostEl = document.getElementById("poa-tree-host");
          const ganttModalEl = document.getElementById("poa-gantt-modal");
          const ganttCloseBtn = document.getElementById("poa-gantt-close");
          const ganttHostEl = document.getElementById("poa-gantt-host");
          const ganttBlocksEl = document.getElementById("poa-gantt-blocks");
          const ganttShowAllBtn = document.getElementById("poa-gantt-show-all");
          const ganttHideAllBtn = document.getElementById("poa-gantt-hide-all");
          const calendarModalEl = document.getElementById("poa-calendar-modal");
          const calendarCloseBtn = document.getElementById("poa-calendar-close");
          const calendarPrevBtn = document.getElementById("poa-calendar-prev");
          const calendarTodayBtn = document.getElementById("poa-calendar-today");
          const calendarNextBtn = document.getElementById("poa-calendar-next");
          const calendarMonthEl = document.getElementById("poa-calendar-month");
          const calendarGridEl = document.getElementById("poa-calendar-grid");
          const downloadTemplateBtn = document.getElementById("poa-download-template");
          const exportXlsBtn = document.getElementById("poa-export-xls");
          const importCsvBtn = document.getElementById("poa-import-csv");
          const importCsvFileEl = document.getElementById("poa-import-csv-file");
          const modalEl = document.getElementById("poa-activity-modal");
          const closeBtn = document.getElementById("poa-activity-close");
          const cancelBtn = document.getElementById("poa-act-cancel");
          const editBottomBtn = document.getElementById("poa-act-edit-bottom");
          const saveBtn = document.getElementById("poa-act-save");
          const saveTopBtn = document.getElementById("poa-act-save-top");
          const newActBtn = document.getElementById("poa-act-new");
          const editActBtn = document.getElementById("poa-act-edit");
          const deleteActBtn = document.getElementById("poa-act-delete");
          const actListEl = document.getElementById("poa-act-list");
          const actListMsgEl = document.getElementById("poa-act-list-msg");
          const formGridEl = modalEl ? modalEl.querySelector(".poa-form-grid") : null;
          const tabsWrapEl = document.getElementById("poa-tabs");
          const subAddBtn = document.getElementById("poa-sub-add");
          const subListEl = document.getElementById("poa-sub-list");
          const subHintEl = document.getElementById("poa-sub-hint");
          const titleEl = document.getElementById("poa-activity-title");
          const subtitleEl = document.getElementById("poa-activity-subtitle");
          const activityBranchEl = document.getElementById("poa-activity-branch");
          const assignedByEl = document.getElementById("poa-assigned-by");
          const actNameEl = document.getElementById("poa-act-name");
          const actOwnerEl = document.getElementById("poa-act-owner");
          const actAssignedEl = document.getElementById("poa-act-assigned");
          const actStartEl = document.getElementById("poa-act-start");
          const actEndEl = document.getElementById("poa-act-end");
          const actImpactHitosEl = document.getElementById("poa-act-impact-hitos");
          const actRecurrenteEl = document.getElementById("poa-act-recurrente");
          const actPeriodicidadEl = document.getElementById("poa-act-periodicidad");
          const actEveryDaysWrapEl = document.getElementById("poa-act-every-days-wrap");
          const actEveryDaysEl = document.getElementById("poa-act-every-days");
          const actDescEl = document.getElementById("poa-act-desc");
          const actSuggestIaBtn = document.getElementById("poa-act-suggest-ia");
          const actMsgEl = document.getElementById("poa-act-msg");
          const budgetTypeEl = document.getElementById("poa-budget-type");
          const budgetRubroEl = document.getElementById("poa-budget-rubro");
          const budgetMonthlyEl = document.getElementById("poa-budget-monthly");
          const budgetAnnualEl = document.getElementById("poa-budget-annual");
          const budgetApprovedEl = document.getElementById("poa-budget-approved");
          const budgetAddBtn = document.getElementById("poa-budget-add");
          const budgetCancelBtn = document.getElementById("poa-budget-cancel");
          const budgetListEl = document.getElementById("poa-budget-list");
          const budgetMonthlyTotalEl = document.getElementById("poa-budget-monthly-total");
          const budgetAnnualTotalEl = document.getElementById("poa-budget-annual-total");
          const budgetMsgEl = document.getElementById("poa-budget-msg");
          const delivNameEl = document.getElementById("poa-deliv-name");
          const delivAddBtn = document.getElementById("poa-deliv-add");
          const delivListEl = document.getElementById("poa-deliv-list");
          const delivMsgEl = document.getElementById("poa-deliv-msg");
          const stateNoIniciadoBtn = document.getElementById("poa-state-no-iniciado");
          const stateEnProcesoBtn = document.getElementById("poa-state-en-proceso");
          const stateTerminadoBtn = document.getElementById("poa-state-terminado");
          const stateEnRevisionBtn = document.getElementById("poa-state-en-revision");
          const statusValueEl = document.getElementById("poa-status-value");
          const progressValueEl = document.getElementById("poa-progress-value");
          const approveBtn = document.getElementById("poa-approval-approve");
          const rejectBtn = document.getElementById("poa-approval-reject");
          const subModalEl = document.getElementById("poa-sub-modal");
          const subCloseBtn = document.getElementById("poa-sub-close");
          const subCancelBtn = document.getElementById("poa-sub-cancel");
          const subSaveBtn = document.getElementById("poa-sub-save");
          const subBranchEl = document.getElementById("poa-sub-branch");
          const subNameEl = document.getElementById("poa-sub-name");
          const subOwnerEl = document.getElementById("poa-sub-owner");
          const subAssignedEl = document.getElementById("poa-sub-assigned");
          const subStartEl = document.getElementById("poa-sub-start");
          const subEndEl = document.getElementById("poa-sub-end");
          const subRecurrenteEl = document.getElementById("poa-sub-recurrente");
          const subPeriodicidadEl = document.getElementById("poa-sub-periodicidad");
          const subEveryDaysWrapEl = document.getElementById("poa-sub-every-days-wrap");
          const subEveryDaysEl = document.getElementById("poa-sub-every-days");
          const subDescEl = document.getElementById("poa-sub-desc");
          const subMsgEl = document.getElementById("poa-sub-msg");
          const setupPoaRichEditor = (textareaEl) => {
            if (!textareaEl || textareaEl.dataset.richReady === "1") return null;
            const wrap = document.createElement("div");
            wrap.className = "poa-rt-wrap";
            const toolbar = document.createElement("div");
            toolbar.className = "poa-rt-toolbar";
            const cmds = [
              { cmd: "bold", label: "B" },
              { cmd: "italic", label: "I" },
              { cmd: "underline", label: "U" },
              { cmd: "insertUnorderedList", label: "• Lista" },
              { cmd: "insertOrderedList", label: "1. Lista" },
            ];
            cmds.forEach((item) => {
              const btn = document.createElement("button");
              btn.type = "button";
              btn.className = "poa-rt-btn";
              btn.textContent = item.label;
              btn.addEventListener("click", () => {
                editor.focus();
                document.execCommand(item.cmd, false);
                textareaEl.value = editor.innerHTML;
              });
              toolbar.appendChild(btn);
            });
            const editor = document.createElement("div");
            editor.className = "poa-rt-editor";
            editor.contentEditable = "true";
            editor.innerHTML = textareaEl.value || "";
            editor.addEventListener("input", () => {
              textareaEl.value = editor.innerHTML;
            });
            wrap.appendChild(toolbar);
            wrap.appendChild(editor);
            textareaEl.style.display = "none";
            textareaEl.dataset.richReady = "1";
            textareaEl.parentNode && textareaEl.parentNode.insertBefore(wrap, textareaEl);
            return {
              getHtml: () => String(editor.innerHTML || ""),
              setHtml: (value) => {
                const html = String(value || "");
                editor.innerHTML = html;
                textareaEl.value = html;
              },
            };
          };
          const actDescRich = setupPoaRichEditor(actDescEl);
          if (!gridEl) return;
          let objectivesById = {};
          let activitiesByObjective = {};
          let approvalsByActivity = {};
          let currentObjective = null;
          let currentActivityId = null;
          let selectedListActivityId = null;
          let currentActivityData = null;
          let currentSubactivities = [];
          let currentBudgetItems = [];
          let currentDeliverables = [];
          let canValidateDeliverables = false;
          let editingBudgetIndex = -1;
          let editingSubId = null;
          let currentParentSubId = 0;
          let isSaving = false;
          let activityEditorMode = "list";
          let poaGanttVisibility = {};
          let poaGanttObjectives = [];
          let poaGanttActivities = [];
          let poaTreeVisibility = {};
          let poaCalendarCursor = new Date();
          let poaD3Promise = null;
          let poaPermissions = {
            poa_access_level: "mis_tareas",
            can_manage_content: false,
            can_view_gantt: false,
          };
          let poaIaEnabled = false;

          const escapeHtml = (value) => String(value || "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
          const fmtDate = (iso) => {
            const value = String(iso || "").trim();
            if (!value) return "N/D";
            const date = new Date(value);
            if (Number.isNaN(date.getTime())) return value;
            return date.toLocaleDateString("es-CR");
          };
          const todayIso = () => {
            const now = new Date();
            const y = now.getFullYear();
            const m = String(now.getMonth() + 1).padStart(2, "0");
            const d = String(now.getDate()).padStart(2, "0");
            return `${y}-${m}-${d}`;
          };
          const loadScript = (src) => new Promise((resolve, reject) => {
            if (document.querySelector(`script[src="${src}"]`)) {
              resolve();
              return;
            }
            const script = document.createElement("script");
            script.src = src;
            script.async = true;
            script.onload = () => resolve();
            script.onerror = () => reject(new Error(`No se pudo cargar ${src}`));
            document.head.appendChild(script);
          });
          const ensureD3Library = async () => {
            if (window.d3) return true;
            if (!poaD3Promise) {
              poaD3Promise = (async () => {
                await loadScript("/static/vendor/d3.min.js");
                return !!window.d3;
              })().catch(() => false);
            }
            const ok = await poaD3Promise;
            return !!ok;
          };
          const showMsg = (text, isError = false) => {
            if (!msgEl) return;
            msgEl.textContent = text || "";
            msgEl.style.color = isError ? "#b91c1c" : "#0f3d2e";
          };
          window.addEventListener("error", (event) => {
            const msg = String(event?.message || "Error JavaScript no controlado").trim();
            showMsg(`Error JS: ${msg}`, true);
          });
          window.addEventListener("unhandledrejection", (event) => {
            const reason = event?.reason;
            const msg = String(reason?.message || reason || "Promesa rechazada sin control").trim();
            showMsg(`Error JS: ${msg}`, true);
          });
          const renderOwnerActivityChart = (activities) => {
            if (!ownerChartListEl || !ownerChartEmptyEl || !ownerChartTotalEl) return;
            const list = Array.isArray(activities) ? activities : [];
            const counts = {};
            let assignedTotal = 0;
            list.forEach((item) => {
              const owner = String(item?.responsable || "").trim();
              if (!owner) return;
              assignedTotal += 1;
              counts[owner] = (counts[owner] || 0) + 1;
            });
            ownerChartTotalEl.textContent = `Total asignadas: ${assignedTotal}`;
            const entries = Object.entries(counts)
              .sort((a, b) => {
                if (b[1] !== a[1]) return b[1] - a[1];
                return a[0].localeCompare(b[0], "es");
              });
            if (!entries.length || assignedTotal <= 0) {
              ownerChartListEl.innerHTML = "";
              ownerChartEmptyEl.style.display = "block";
              ownerChartEmptyEl.textContent = "Sin actividades con responsable.";
              return;
            }
            ownerChartEmptyEl.style.display = "none";
            const maxRows = 10;
            const topEntries = entries.slice(0, maxRows);
            const extraCount = entries.slice(maxRows).reduce((acc, item) => acc + Number(item[1] || 0), 0);
            const rows = topEntries.map(([name, amount]) => {
              const pct = assignedTotal > 0 ? (Number(amount || 0) / assignedTotal) * 100 : 0;
              return `
                <div class="poa-owner-row">
                  <div class="poa-owner-name" title="${escapeHtml(name)}">${escapeHtml(name)}</div>
                  <div class="poa-owner-bar">
                    <div class="poa-owner-fill"></div>
                  </div>
                  <div class="poa-owner-value">${Number(amount || 0)} (${pct.toFixed(1)}%)</div>
                </div>
              `;
            });
            if (extraCount > 0) {
              const pct = assignedTotal > 0 ? (extraCount / assignedTotal) * 100 : 0;
              rows.push(`
                <div class="poa-owner-row">
                  <div class="poa-owner-name" title="Otros usuarios">Otros usuarios</div>
                  <div class="poa-owner-bar">
                    <div class="poa-owner-fill"></div>
                  </div>
                  <div class="poa-owner-value">${extraCount} (${pct.toFixed(1)}%)</div>
                </div>
              `);
            }
            ownerChartListEl.innerHTML = rows.join("");
          };
          const showModalMsg = (text, isError = false) => {
            if (!actMsgEl) return;
            actMsgEl.textContent = text || "";
            actMsgEl.style.color = isError ? "#b91c1c" : "#0f3d2e";
          };
          const requestIaSuggestion = async (texto) => {
            const response = await fetch("/api/ia/suggest/objective-text", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              credentials: "same-origin",
              body: JSON.stringify({ texto: String(texto || "").trim() }),
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok || !payload || payload.error) {
              throw new Error(payload?.error || "No se pudo obtener sugerencia IA.");
            }
            return String(payload.sugerencia || "").trim();
          };
          const iaFeatureEnabled = async (moduleKey = "poa") => {
            try {
              const response = await fetch(`/api/ia/flags?module=${encodeURIComponent(moduleKey)}&feature_key=suggest_objective_text`, {
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
              });
              const payload = await response.json().catch(() => ({}));
              return !!(response.ok && payload?.success === true && payload?.data?.enabled);
            } catch (_err) {
              return false;
            }
          };
          const plainTextFromHtml = (value) => {
            const html = String(value || "").trim();
            if (!html) return "";
            const tmp = document.createElement("div");
            tmp.innerHTML = html;
            return String(tmp.textContent || tmp.innerText || "").trim();
          };
          const showActListMsg = (text, isError = false) => {
            if (!actListMsgEl) return;
            actListMsgEl.textContent = text || "";
            actListMsgEl.style.color = isError ? "#b91c1c" : "#64748b";
          };
          const setActivityEditorMode = (mode) => {
            activityEditorMode = mode === "edit" || mode === "new" ? mode : "list";
            if (!modalEl) return;
            const isList = activityEditorMode === "list";
            modalEl.classList.toggle("list-mode", isList);
            if (saveBtn) saveBtn.disabled = isList;
            if (saveTopBtn) saveTopBtn.disabled = isList;
            if (saveTopBtn) saveTopBtn.style.opacity = isList ? "0.55" : "1";
            if (saveTopBtn) saveTopBtn.style.cursor = isList ? "not-allowed" : "pointer";
            if (formGridEl) formGridEl.style.display = isList ? "none" : "block";
            if (tabsWrapEl) tabsWrapEl.style.display = isList ? "none" : "flex";
            if (isList) {
              if (titleEl) titleEl.textContent = "Actividades del objetivo";
            } else if (titleEl) {
              titleEl.textContent = activityEditorMode === "edit" ? "Editar actividad" : "Nueva actividad";
            }
          };
          const showSubMsg = (text, isError = false) => {
            if (!subMsgEl) return;
            subMsgEl.textContent = text || "";
            subMsgEl.style.color = isError ? "#b91c1c" : "#0f3d2e";
          };
          const showBudgetMsg = (text, isError = false) => {
            if (!budgetMsgEl) return;
            budgetMsgEl.textContent = text || "";
            budgetMsgEl.style.color = isError ? "#b91c1c" : "#0f3d2e";
          };
          const canManageContent = () => !!poaPermissions?.can_manage_content;
          const applyPoaPermissionsUI = () => {
            const canManage = canManageContent();
            const canViewGantt = !!poaPermissions?.can_view_gantt;
            if (openGanttBtn) {
              const wrapper = openGanttBtn.closest(".view-pill") || openGanttBtn;
              wrapper.style.display = canViewGantt ? "" : "none";
            }
            if (!canViewGantt && ganttModalEl && ganttModalEl.classList.contains("open")) closeGanttModal();
            [newActBtn, editActBtn, deleteActBtn, saveBtn, saveTopBtn, subAddBtn, subSaveBtn, budgetAddBtn, budgetCancelBtn, delivAddBtn].forEach((btn) => {
              if (!btn) return;
              btn.disabled = !canManage;
              btn.style.opacity = canManage ? "1" : "0.55";
              btn.style.cursor = canManage ? "pointer" : "not-allowed";
            });
            if (actSuggestIaBtn) {
              const allowIa = canManage && poaIaEnabled;
              actSuggestIaBtn.disabled = !allowIa;
              actSuggestIaBtn.style.opacity = allowIa ? "1" : "0.55";
              actSuggestIaBtn.style.cursor = allowIa ? "pointer" : "not-allowed";
              if (!poaIaEnabled) actSuggestIaBtn.title = "IA deshabilitada para tu rol/módulo";
            }
            if (delivNameEl) delivNameEl.disabled = !canManage;
            if (importCsvBtn) {
              importCsvBtn.disabled = !canManage;
              importCsvBtn.style.opacity = canManage ? "1" : "0.55";
            }
          };
          const closeGanttModal = () => {
            if (!ganttModalEl) return;
            ganttModalEl.classList.remove("open");
            document.body.style.overflow = "";
          };
          const closeTreeModal = () => {
            if (!treeModalEl) return;
            treeModalEl.classList.remove("open");
            document.body.style.overflow = "";
          };
          const closeCalendarModal = () => {
            if (!calendarModalEl) return;
            calendarModalEl.classList.remove("open");
            document.body.style.overflow = "";
          };
          const treeKey = (kind, id) => `${kind}:${Number(id || 0)}`;
          const isTreeOpen = (kind, id) => !!poaTreeVisibility[treeKey(kind, id)];
          const setTreeOpen = (kind, id, value) => {
            poaTreeVisibility[treeKey(kind, id)] = !!value;
          };
          const getActivityById = (activityId) => (
            (Array.isArray(poaGanttActivities) ? poaGanttActivities : [])
              .find((item) => Number(item.id || 0) === Number(activityId)) || null
          );
          const poaStateTone = ({ status, entregaEstado, fechaInicial, fechaFinal, avance }) => {
            const st = String(status || "").trim().toLowerCase();
            const de = String(entregaEstado || "").trim().toLowerCase();
            const start = String(fechaInicial || "").trim();
            const end = String(fechaFinal || "").trim();
            const progress = Number(avance || 0);
            const today = todayIso();
            if (de === "pendiente" || st.includes("revisión") || st.includes("revision")) return "orange";
            if (de === "aprobada" || st.includes("terminad") || st.includes("hecho") || progress >= 100) return "green";
            if (st.includes("atras")) return "red";
            if (st.includes("no inici")) return "none";
            if (end && today > end && progress < 100) return "red";
            if (st.includes("proceso")) return "yellow";
            if (start && today >= start && progress < 100) return "yellow";
            return "none";
          };
          const aggregatePoaStateTone = (tones) => {
            const list = Array.isArray(tones) ? tones : [];
            if (!list.length) return "none";
            if (list.includes("red")) return "red";
            if (list.includes("orange")) return "orange";
            if (list.includes("yellow")) return "yellow";
            if (list.includes("green")) return "green";
            return "none";
          };
          const renderPoaAdvanceTree = () => {
            if (!treeHostEl) return;
            const objectives = Array.isArray(poaGanttObjectives) ? poaGanttObjectives : [];
            const activities = Array.isArray(poaGanttActivities) ? poaGanttActivities : [];
            if (!objectives.length) {
              treeHostEl.innerHTML = '<div class="poa-tree-axis"><p class="poa-tree-help">Sin datos para mostrar.</p></div>';
              return;
            }
            const grouped = {};
            objectives.forEach((obj) => {
              const axisName = String(obj.axis_name || "Sin eje").trim() || "Sin eje";
              if (!grouped[axisName]) grouped[axisName] = [];
              grouped[axisName].push(obj);
            });
            const axisNames = Object.keys(grouped).sort((a, b) => a.localeCompare(b, "es"));
            treeHostEl.innerHTML = axisNames.map((axisName) => {
              const axisIdKey = `axis:${axisName}`;
              const axisOpen = !!poaTreeVisibility[axisIdKey];
              const objCards = axisOpen ? (grouped[axisName] || []).map((obj) => {
                const objId = Number(obj.id || 0);
                const objOpen = isTreeOpen("obj", objId);
                const objActs = activities.filter((act) => Number(act.objective_id || 0) === objId);
                const objectiveTone = aggregatePoaStateTone(
                  objActs.map((act) => poaStateTone({
                    status: act?.status,
                    entregaEstado: act?.entrega_estado,
                    fechaInicial: act?.fecha_inicial,
                    fechaFinal: act?.fecha_final,
                    avance: act?.avance,
                  }))
                );
                const actHtml = objOpen ? objActs.map((act) => {
                  const actId = Number(act.id || 0);
                  const actOpen = isTreeOpen("act", actId);
                  const actTone = poaStateTone({
                    status: act?.status,
                    entregaEstado: act?.entrega_estado,
                    fechaInicial: act?.fecha_inicial,
                    fechaFinal: act?.fecha_final,
                    avance: act?.avance,
                  });
                  const subList = Array.isArray(act.subactivities) ? act.subactivities : [];
                  const subHtml = actOpen ? subList.map((sub) => `
                    <div class="poa-tree-item ${poaStateTone({
                      status: sub?.status,
                      entregaEstado: "",
                      fechaInicial: sub?.fecha_inicial,
                      fechaFinal: sub?.fecha_final,
                      avance: sub?.avance,
                    }) !== "none" ? "has-state" : ""}">
                      <div class="poa-tree-state poa-tree-state-${poaStateTone({
                        status: sub?.status,
                        entregaEstado: "",
                        fechaInicial: sub?.fecha_inicial,
                        fechaFinal: sub?.fecha_final,
                        avance: sub?.avance,
                      })}"></div>
                      <div class="poa-tree-item-head">
                        <h6 class="poa-tree-item-title poa-tree-click" data-tree-sub="${Number(sub.id || 0)}" data-tree-sub-parent="${actId}">${escapeHtml(sub.nombre || "Subtarea")}</h6>
                      </div>
                    </div>
                  `).join("") : "";
                  return `
                    <div class="poa-tree-item ${actTone !== "none" ? "has-state" : ""}">
                      <div class="poa-tree-state poa-tree-state-${actTone}"></div>
                      <div class="poa-tree-item-head">
                        <h6 class="poa-tree-item-title poa-tree-click" data-tree-activity="${actId}" data-tree-objective="${objId}">${escapeHtml(act.nombre || "Actividad")}</h6>
                        ${subList.length ? `<button type="button" class="poa-tree-toggle" data-tree-toggle="act" data-tree-id="${actId}">${actOpen ? "Ocultar" : "Mostrar"}</button>` : ""}
                      </div>
                      ${subList.length ? `<p class="poa-tree-item-meta">Subactividades: ${subList.length}</p>` : ""}
                      ${subHtml ? `<div class="poa-tree-children">${subHtml}</div>` : ""}
                    </div>
                  `;
                }).join("") : "";
                return `
                  <div class="poa-tree-item ${objectiveTone !== "none" ? "has-state" : ""}">
                    <div class="poa-tree-state poa-tree-state-${objectiveTone}"></div>
                    <div class="poa-tree-item-head">
                      <h5 class="poa-tree-item-title poa-tree-click" data-tree-objective="${objId}">${escapeHtml(obj.codigo || "xx-yy-zz")} - ${escapeHtml(obj.nombre || "Objetivo")}</h5>
                      ${objActs.length ? `<button type="button" class="poa-tree-toggle" data-tree-toggle="obj" data-tree-id="${objId}">${objOpen ? "Ocultar" : "Mostrar"}</button>` : ""}
                    </div>
                    <p class="poa-tree-item-meta">Actividades: ${objActs.length}</p>
                    ${actHtml ? `<div class="poa-tree-children">${actHtml}</div>` : ""}
                  </div>
                `;
              }).join("") : "";
              return `
                <section class="poa-tree-axis">
                  <div class="poa-tree-axis-head">
                    <h4>${escapeHtml(axisName)}</h4>
                    <button type="button" class="poa-tree-toggle" data-tree-toggle="axis" data-tree-axis="${escapeHtml(axisName)}">${axisOpen ? "Ocultar" : "Mostrar"}</button>
                  </div>
                  ${objCards ? `<div class="poa-tree-objectives">${objCards}</div>` : ""}
                </section>
              `;
            }).join("");
            treeHostEl.querySelectorAll("[data-tree-toggle='axis']").forEach((btn) => {
              btn.addEventListener("click", () => {
                const key = `axis:${String(btn.getAttribute("data-tree-axis") || "")}`;
                poaTreeVisibility[key] = !poaTreeVisibility[key];
                renderPoaAdvanceTree();
              });
            });
            treeHostEl.querySelectorAll("[data-tree-toggle='obj']").forEach((btn) => {
              btn.addEventListener("click", () => {
                setTreeOpen("obj", btn.getAttribute("data-tree-id"), !isTreeOpen("obj", btn.getAttribute("data-tree-id")));
                renderPoaAdvanceTree();
              });
            });
            treeHostEl.querySelectorAll("[data-tree-toggle='act']").forEach((btn) => {
              btn.addEventListener("click", () => {
                setTreeOpen("act", btn.getAttribute("data-tree-id"), !isTreeOpen("act", btn.getAttribute("data-tree-id")));
                renderPoaAdvanceTree();
              });
            });
            treeHostEl.querySelectorAll("[data-tree-objective]").forEach((node) => {
              node.addEventListener("click", async () => {
                const objectiveId = Number(node.getAttribute("data-tree-objective") || 0);
                if (objectiveId > 0) await openActivityForm(objectiveId);
              });
            });
            treeHostEl.querySelectorAll("[data-tree-activity]").forEach((node) => {
              node.addEventListener("click", async () => {
                const objectiveId = Number(node.getAttribute("data-tree-objective") || 0);
                const activityId = Number(node.getAttribute("data-tree-activity") || 0);
                if (objectiveId > 0) {
                  await openActivityForm(objectiveId, { activityId, focusSubId: 0 });
                }
              });
            });
            treeHostEl.querySelectorAll("[data-tree-sub]").forEach((node) => {
              node.addEventListener("click", async () => {
                const subId = Number(node.getAttribute("data-tree-sub") || 0);
                const parentActId = Number(node.getAttribute("data-tree-sub-parent") || 0);
                const act = getActivityById(parentActId);
                const objectiveId = Number(act?.objective_id || 0);
                if (objectiveId > 0) {
                  await openActivityForm(objectiveId, { activityId: parentActId, focusSubId: subId });
                }
              });
            });
          };
          const axisGanttKey = (objective) => String(objective?.axis_name || "Sin eje").trim() || "Sin eje";
          const syncPoaGanttVisibility = () => {
            const groupedKeys = new Set((Array.isArray(poaGanttObjectives) ? poaGanttObjectives : []).map((obj) => axisGanttKey(obj)));
            const next = {};
            Array.from(groupedKeys).forEach((key) => {
              next[key] = Object.prototype.hasOwnProperty.call(poaGanttVisibility, key) ? !!poaGanttVisibility[key] : true;
            });
            poaGanttVisibility = next;
          };
          const renderPoaGanttFilters = () => {
            if (!ganttBlocksEl) return;
            const list = Array.from(new Set((Array.isArray(poaGanttObjectives) ? poaGanttObjectives : []).map((obj) => axisGanttKey(obj)))).sort((a, b) => a.localeCompare(b, "es"));
            if (!list.length) {
              ganttBlocksEl.innerHTML = "";
              return;
            }
            syncPoaGanttVisibility();
            ganttBlocksEl.innerHTML = list.map((axisName) => {
              const checked = poaGanttVisibility[axisName] !== false ? "checked" : "";
              return `<label class="poa-gantt-block"><input type="checkbox" data-poa-gantt-axis="${escapeHtml(axisName)}" ${checked}><span>${escapeHtml(axisName)}</span></label>`;
            }).join("");
            ganttBlocksEl.querySelectorAll("input[data-poa-gantt-axis]").forEach((checkbox) => {
              checkbox.addEventListener("change", async () => {
                const key = String(checkbox.getAttribute("data-poa-gantt-axis") || "");
                if (!key) return;
                poaGanttVisibility[key] = !!checkbox.checked;
                await renderPoaGantt();
              });
            });
          };
          const renderPoaGantt = async () => {
            if (!ganttHostEl) return;
            const ok = await ensureD3Library();
            if (!ok) {
              ganttHostEl.innerHTML = '<p>No se pudo cargar la librería para Gantt.</p>';
              return;
            }
            renderPoaGanttFilters();
            syncPoaGanttVisibility();
            const objectives = Array.isArray(poaGanttObjectives) ? poaGanttObjectives : [];
            const activities = Array.isArray(poaGanttActivities) ? poaGanttActivities : [];
            const activitiesByObj = {};
            activities.forEach((item) => {
              const key = Number(item?.objective_id || 0);
              if (!key) return;
              if (!activitiesByObj[key]) activitiesByObj[key] = [];
              activitiesByObj[key].push(item);
            });
            const rows = [];
            objectives.forEach((obj) => {
              const axisKey = axisGanttKey(obj);
              if (poaGanttVisibility[axisKey] === false) return;
              const objStart = String(obj?.fecha_inicial || "");
              const objEnd = String(obj?.fecha_final || "");
              if (objStart && objEnd) {
                rows.push({
                  level: 0,
                  type: "objective",
                  label: `${obj.codigo || "xx-yy-zz"} · ${obj.nombre || "Objetivo"}`,
                  start: new Date(`${objStart}T00:00:00`),
                  end: new Date(`${objEnd}T00:00:00`),
                });
              }
              (activitiesByObj[Number(obj.id || 0)] || []).forEach((act) => {
                const start = String(act?.fecha_inicial || "");
                const end = String(act?.fecha_final || "");
                if (!start || !end) return;
                rows.push({
                  level: 1,
                  type: "activity",
                  label: `${act.codigo || "ACT"} · ${act.nombre || "Actividad"}`,
                  start: new Date(`${start}T00:00:00`),
                  end: new Date(`${end}T00:00:00`),
                });
              });
            });
            if (!rows.length) {
              ganttHostEl.innerHTML = '<p>No hay fechas suficientes en objetivos/actividades para generar Gantt.</p>';
              return;
            }
            const minDate = new Date(Math.min(...rows.map((item) => item.start.getTime())));
            const maxDate = new Date(Math.max(...rows.map((item) => item.end.getTime())));
            const margin = { top: 44, right: 24, bottom: 30, left: 430 };
            const rowH = 32;
            const chartW = Math.max(920, (ganttHostEl.clientWidth || 920) + 260);
            const width = margin.left + chartW + margin.right;
            const height = margin.top + (rows.length * rowH) + margin.bottom;
            ganttHostEl.innerHTML = "";
            const svg = window.d3.select(ganttHostEl).append("svg")
              .attr("width", width)
              .attr("height", height)
              .style("min-width", `${width}px`)
              .style("display", "block");
            const x = window.d3.scaleTime().domain([minDate, maxDate]).range([margin.left, margin.left + chartW]);
            const y = (idx) => margin.top + (idx * rowH);
            svg.append("g")
              .attr("transform", `translate(0, ${margin.top - 10})`)
              .call(window.d3.axisTop(x).ticks(window.d3.timeMonth.every(1)).tickSize(-rows.length * rowH).tickFormat(window.d3.timeFormat("%b %Y")))
              .call((g) => g.selectAll("text").attr("fill", "#475569").attr("font-size", 11))
              .call((g) => g.selectAll("line").attr("stroke", "rgba(148,163,184,.28)"))
              .call((g) => g.select(".domain").attr("stroke", "rgba(148,163,184,.35)"));
            rows.forEach((row, idx) => {
              const yy = y(idx);
              if (idx % 2 === 0) {
                svg.append("rect")
                  .attr("x", margin.left)
                  .attr("y", yy)
                  .attr("width", chartW)
                  .attr("height", rowH)
                  .attr("fill", "rgba(248,250,252,.70)");
              }
              svg.append("text")
                .attr("x", margin.left - 10 - (row.level ? 16 : 0))
                .attr("y", yy + (rowH / 2) + 4)
                .attr("text-anchor", "end")
                .attr("fill", row.level ? "#334155" : "#0f172a")
                .attr("font-size", row.level ? 12 : 12.5)
                .attr("font-style", row.level ? "italic" : "normal")
                .attr("font-weight", row.level ? 500 : 700)
                .text(row.label);
              const startX = x(row.start);
              const endX = x(row.end);
              const barW = Math.max(3, endX - startX);
              svg.append("rect")
                .attr("x", startX)
                .attr("y", yy + 7)
                .attr("width", barW)
                .attr("height", rowH - 14)
                .attr("rx", 6)
                .attr("fill", row.type === "objective" ? "#0f3d2e" : "#2563eb")
                .attr("opacity", row.type === "objective" ? 0.92 : 0.86);
            });
            const today = new Date();
            if (today >= minDate && today <= maxDate) {
              const xx = x(today);
              svg.append("line")
                .attr("x1", xx).attr("x2", xx)
                .attr("y1", margin.top - 12).attr("y2", height - margin.bottom + 4)
                .attr("stroke", "#ef4444")
                .attr("stroke-width", 1.6)
                .attr("stroke-dasharray", "4,4");
            }
          };
          const toIsoDate = (date) => {
            const y = date.getFullYear();
            const m = String(date.getMonth() + 1).padStart(2, "0");
            const d = String(date.getDate()).padStart(2, "0");
            return `${y}-${m}-${d}`;
          };
          const shiftCalendarMonth = (delta) => {
            poaCalendarCursor = new Date(poaCalendarCursor.getFullYear(), poaCalendarCursor.getMonth() + Number(delta || 0), 1);
          };
          const buildCalendarEvents = () => {
            const objectives = Array.isArray(poaGanttObjectives) ? poaGanttObjectives : [];
            const activities = Array.isArray(poaGanttActivities) ? poaGanttActivities : [];
            const out = [];
            objectives.forEach((obj) => {
              const start = String(obj?.fecha_inicial || "");
              const end = String(obj?.fecha_final || "");
              if (!start || !end) return;
              out.push({
                type: "objective",
                objectiveId: Number(obj.id || 0),
                label: `${obj.codigo || "OBJ"} · ${obj.nombre || "Objetivo"}`,
                start,
                end,
              });
            });
            activities.forEach((act) => {
              const start = String(act?.fecha_inicial || "");
              const end = String(act?.fecha_final || "");
              if (!start || !end) return;
              out.push({
                type: "activity",
                objectiveId: Number(act.objective_id || 0),
                activityId: Number(act.id || 0),
                label: `${act.codigo || "ACT"} · ${act.nombre || "Actividad"}`,
                start,
                end,
              });
            });
            return out;
          };
          const renderPoaCalendar = () => {
            if (!calendarGridEl || !calendarMonthEl) return;
            const monthStart = new Date(poaCalendarCursor.getFullYear(), poaCalendarCursor.getMonth(), 1);
            const monthEnd = new Date(poaCalendarCursor.getFullYear(), poaCalendarCursor.getMonth() + 1, 0);
            const startWeekday = (monthStart.getDay() + 6) % 7;
            const gridStart = new Date(monthStart);
            gridStart.setDate(monthStart.getDate() - startWeekday);
            calendarMonthEl.textContent = monthStart.toLocaleDateString("es-CR", { month: "long", year: "numeric" });
            const events = buildCalendarEvents();
            const dows = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"];
            let html = dows.map((dow) => `<div class="poa-cal-dow">${dow}</div>`).join("");
            for (let i = 0; i < 42; i += 1) {
              const day = new Date(gridStart);
              day.setDate(gridStart.getDate() + i);
              const dayIso = toIsoDate(day);
              const inMonth = day >= monthStart && day <= monthEnd;
              const dayEvents = events.filter((item) => item.start <= dayIso && item.end >= dayIso);
              const visible = dayEvents.slice(0, 2);
              const extra = dayEvents.length - visible.length;
              html += `
                <div class="poa-cal-cell ${inMonth ? "" : "muted"}" data-cal-day="${dayIso}">
                  <div class="poa-cal-day">${day.getDate()}</div>
                  <div class="poa-cal-events">
                    ${visible.map((event, idx) => `<button type="button" class="poa-cal-event ${event.type}" data-cal-event-day="${dayIso}" data-cal-event-idx="${idx}" title="${escapeHtml(event.label)}">${escapeHtml(event.label)}</button>`).join("")}
                    ${extra > 0 ? `<div class="poa-cal-more">+${extra} más</div>` : ""}
                  </div>
                </div>
              `;
            }
            calendarGridEl.innerHTML = html;
            calendarGridEl.querySelectorAll("[data-cal-event-day]").forEach((node) => {
              node.addEventListener("click", async () => {
                const dayIso = String(node.getAttribute("data-cal-event-day") || "");
                const idx = Number(node.getAttribute("data-cal-event-idx") || -1);
                const dayEvents = events.filter((item) => item.start <= dayIso && item.end >= dayIso);
                const event = dayEvents[idx];
                if (!event) return;
                closeCalendarModal();
                if (event.type === "activity" && event.objectiveId && event.activityId) {
                  await openActivityForm(event.objectiveId, { activityId: event.activityId });
                } else if (event.objectiveId) {
                  await openActivityForm(event.objectiveId);
                }
              });
            });
          };
          const showDeliverableMsg = (text, isError = false) => {
            if (!delivMsgEl) return;
            delivMsgEl.textContent = text || "";
            delivMsgEl.style.color = isError ? "#b91c1c" : "#0f3d2e";
          };
          const normalizeDeliverables = (rows) => {
            const list = Array.isArray(rows) ? rows : [];
            return list
              .map((item, idx) => ({
                id: Number(item?.id || 0),
                nombre: String(item?.nombre || "").trim(),
                validado: !!item?.validado,
                orden: Number(item?.orden || (idx + 1)),
              }))
              .filter((item) => item.nombre);
          };
          const renderDeliverables = () => {
            if (!delivListEl) return;
            const canManage = canManageContent();
            const list = normalizeDeliverables(currentDeliverables);
            currentDeliverables = list;
            if (!list.length) {
              delivListEl.innerHTML = '<div class="poa-sub-meta">Sin entregables registrados.</div>';
              return;
            }
            delivListEl.innerHTML = list.map((item, idx) => `
              <div class="poa-deliv-item">
                <label>
                  <input type="checkbox" data-deliv-check="${idx}" ${item.validado ? "checked" : ""} ${(canValidateDeliverables && canManage) ? "" : "disabled"}>
                  <span>${escapeHtml(item.nombre)}</span>
                </label>
                ${canManage ? `<button type="button" class="poa-sub-btn warn" data-deliv-delete="${idx}">Eliminar</button>` : ""}
              </div>
            `).join("");
            delivListEl.querySelectorAll("[data-deliv-check]").forEach((node) => {
              node.addEventListener("change", () => {
                const idx = Number(node.getAttribute("data-deliv-check") || -1);
                if (idx < 0 || idx >= currentDeliverables.length) return;
                if (!canValidateDeliverables) {
                  node.checked = !!currentDeliverables[idx]?.validado;
                  showDeliverableMsg("Solo el líder del objetivo puede validar entregables.", true);
                  return;
                }
                currentDeliverables[idx].validado = !!node.checked;
                showDeliverableMsg("Validación actualizada. Guarda la actividad para persistir.");
              });
            });
            delivListEl.querySelectorAll("[data-deliv-delete]").forEach((node) => {
              node.addEventListener("click", () => {
                const idx = Number(node.getAttribute("data-deliv-delete") || -1);
                if (idx < 0 || idx >= currentDeliverables.length) return;
                currentDeliverables.splice(idx, 1);
                renderDeliverables();
                showDeliverableMsg("Entregable eliminado.");
              });
            });
          };
          const addDeliverable = () => {
            if (!canManageContent()) {
              showDeliverableMsg("Solo administrador puede modificar entregables.", true);
              return;
            }
            const nombre = (delivNameEl && delivNameEl.value ? delivNameEl.value : "").trim();
            if (!nombre) {
              showDeliverableMsg("Escribe el nombre del entregable.", true);
              return;
            }
            currentDeliverables.push({
              id: 0,
              nombre,
              validado: false,
              orden: currentDeliverables.length + 1,
            });
            if (delivNameEl) delivNameEl.value = "";
            renderDeliverables();
            showDeliverableMsg("Entregable agregado. Guarda la actividad para persistir.");
          };
          const toMoney = (value) => {
            const num = Number(value || 0);
            if (!Number.isFinite(num) || num < 0) return 0;
            return Math.round(num * 100) / 100;
          };
          const formatMoney = (value) => toMoney(value).toLocaleString("es-CR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
          const normalizeBudgetItems = (rows) => {
            const list = Array.isArray(rows) ? rows : [];
            return list
              .map((item) => ({
                tipo: String(item?.tipo || "").trim(),
                rubro: String(item?.rubro || "").trim(),
                mensual: toMoney(item?.mensual),
                anual: toMoney(item?.anual),
                autorizado: !!item?.autorizado,
              }))
              .filter((item) => item.tipo && item.rubro);
          };
          const clearBudgetForm = () => {
            if (budgetTypeEl) budgetTypeEl.value = "";
            if (budgetRubroEl) budgetRubroEl.value = "";
            if (budgetMonthlyEl) budgetMonthlyEl.value = "";
            if (budgetAnnualEl) budgetAnnualEl.value = "";
            if (budgetApprovedEl) budgetApprovedEl.checked = false;
            editingBudgetIndex = -1;
            if (budgetAddBtn) budgetAddBtn.textContent = "Agregar rubro";
            showBudgetMsg("");
          };
          const renderBudgetItems = () => {
            if (!budgetListEl) return;
            const canManage = canManageContent();
            const list = normalizeBudgetItems(currentBudgetItems);
            currentBudgetItems = list;
            const monthlyTotal = list.reduce((sum, item) => sum + toMoney(item.mensual), 0);
            const annualTotal = list.reduce((sum, item) => sum + toMoney(item.anual), 0);
            if (budgetMonthlyTotalEl) budgetMonthlyTotalEl.textContent = formatMoney(monthlyTotal);
            if (budgetAnnualTotalEl) budgetAnnualTotalEl.textContent = formatMoney(annualTotal);
            if (!list.length) {
              budgetListEl.innerHTML = '<tr><td colspan="6">Sin rubros registrados.</td></tr>';
              return;
            }
            budgetListEl.innerHTML = list.map((item, idx) => `
              <tr>
                <td>${escapeHtml(item.tipo)}</td>
                <td>${escapeHtml(item.rubro)}</td>
                <td class="num">${escapeHtml(formatMoney(item.mensual))}</td>
                <td class="num">${escapeHtml(formatMoney(item.anual))}</td>
                <td>${item.autorizado ? "Sí" : "No"}</td>
                <td>
                  ${canManage ? `<button type="button" class="poa-sub-btn" data-budget-edit="${idx}">Editar</button>` : ""}
                  ${canManage ? `<button type="button" class="poa-sub-btn warn" data-budget-delete="${idx}">Eliminar</button>` : ""}
                </td>
              </tr>
            `).join("");
            budgetListEl.querySelectorAll("[data-budget-edit]").forEach((btn) => {
              btn.addEventListener("click", () => {
                const idx = Number(btn.getAttribute("data-budget-edit") || -1);
                const row = currentBudgetItems[idx];
                if (!row) return;
                if (budgetTypeEl) budgetTypeEl.value = row.tipo || "";
                if (budgetRubroEl) budgetRubroEl.value = row.rubro || "";
                if (budgetMonthlyEl) budgetMonthlyEl.value = toMoney(row.mensual) ? String(toMoney(row.mensual)) : "";
                if (budgetAnnualEl) budgetAnnualEl.value = toMoney(row.anual) ? String(toMoney(row.anual)) : "";
                if (budgetApprovedEl) budgetApprovedEl.checked = !!row.autorizado;
                editingBudgetIndex = idx;
                if (budgetAddBtn) budgetAddBtn.textContent = "Actualizar rubro";
                showBudgetMsg("Editando rubro de presupuesto.");
                activatePoaTab("budget");
              });
            });
            budgetListEl.querySelectorAll("[data-budget-delete]").forEach((btn) => {
              btn.addEventListener("click", () => {
                const idx = Number(btn.getAttribute("data-budget-delete") || -1);
                if (idx < 0 || idx >= currentBudgetItems.length) return;
                currentBudgetItems.splice(idx, 1);
                renderBudgetItems();
                showBudgetMsg("Rubro eliminado.");
              });
            });
          };
          const addOrUpdateBudgetItem = () => {
            if (!canManageContent()) {
              showBudgetMsg("Solo administrador puede modificar presupuesto.", true);
              return;
            }
            const tipo = (budgetTypeEl && budgetTypeEl.value ? budgetTypeEl.value : "").trim();
            const rubro = (budgetRubroEl && budgetRubroEl.value ? budgetRubroEl.value : "").trim();
            const mensual = toMoney(budgetMonthlyEl && budgetMonthlyEl.value ? budgetMonthlyEl.value : 0);
            let anual = toMoney(budgetAnnualEl && budgetAnnualEl.value ? budgetAnnualEl.value : 0);
            if (!tipo || !rubro) {
              showBudgetMsg("Tipo y rubro son obligatorios.", true);
              return;
            }
            if (!anual && mensual) anual = toMoney(mensual * 12);
            const row = { tipo, rubro, mensual, anual, autorizado: !!(budgetApprovedEl && budgetApprovedEl.checked) };
            if (editingBudgetIndex >= 0 && editingBudgetIndex < currentBudgetItems.length) {
              currentBudgetItems[editingBudgetIndex] = row;
            } else {
              currentBudgetItems.push(row);
            }
            clearBudgetForm();
            renderBudgetItems();
            showBudgetMsg("Rubro listo. Guarda la actividad para persistir.");
          };
          const syncBudgetAnnual = () => {
            if (!budgetMonthlyEl || !budgetAnnualEl) return;
            const mensual = toMoney(budgetMonthlyEl.value || 0);
            const anualRaw = String(budgetAnnualEl.value || "").trim();
            if (anualRaw) return;
            if (!mensual) return;
            budgetAnnualEl.value = String(toMoney(mensual * 12));
          };
          const openModal = () => {
            if (!modalEl) return;
            modalEl.classList.add("open");
            document.body.style.overflow = "hidden";
          };
          const closeModal = () => {
            if (!modalEl) return;
            modalEl.classList.remove("open");
            document.body.style.overflow = "";
          };
          const openSubModal = () => {
            if (!subModalEl) return;
            subModalEl.classList.add("open");
            document.body.style.overflow = "hidden";
          };
          const closeSubModal = () => {
            if (!subModalEl) return;
            subModalEl.classList.remove("open");
            document.body.style.overflow = modalEl && modalEl.classList.contains("open") ? "hidden" : "";
          };
          const nextCode = (objectiveCode) => {
            const code = String(objectiveCode || "").trim().toLowerCase();
            if (!code) return "m1-01-01-aa-bb-cc-dd-ee";
            return `${code}-aa-bb-cc-dd-ee`;
          };
          const buildBranchText = (activityName = "Actividad", slots = {}) => {
            const axisLabel = String(currentObjective?.axis_name || "Eje estratégico").trim() || "Eje estratégico";
            const objectiveLabel = String(currentObjective?.nombre || "Objetivo").trim() || "Objetivo";
            const activityLabel = String(activityName || "Actividad").trim() || "Actividad";
            const tarea = String(slots.tarea || "Tarea").trim() || "Tarea";
            const subtarea = String(slots.subtarea || "Subtarea").trim() || "Subtarea";
            const subsub = String(slots.subsubtarea || "Subsubtarea").trim() || "Subsubtarea";
            return `Ruta: ${axisLabel} / ${objectiveLabel} / ${activityLabel} / ${tarea} / ${subtarea} / ${subsub}`;
          };
          const renderActivityBranch = () => {
            if (!activityBranchEl) return;
            activityBranchEl.textContent = buildBranchText(actNameEl && actNameEl.value ? actNameEl.value : "Actividad");
          };
          const resolveSubBranchSlots = (targetLevel, targetName, parentId) => {
            const byId = {};
            (currentSubactivities || []).forEach((item) => {
              byId[Number(item.id || 0)] = item;
            });
            let tarea = "Tarea";
            let subtarea = "Subtarea";
            let subsubtarea = "Subsubtarea";
            let walker = Number(parentId || 0);
            while (walker) {
              const node = byId[walker];
              if (!node) break;
              const level = Number(node.nivel || 1);
              const name = String(node.nombre || "").trim();
              if (level === 1 && name) tarea = name;
              if (level === 2 && name) subtarea = name;
              if (level === 3 && name) subsubtarea = name;
              walker = Number(node.parent_subactivity_id || 0);
            }
            const cleanTarget = String(targetName || "").trim();
            if (targetLevel === 1 && cleanTarget) tarea = cleanTarget;
            if (targetLevel === 2 && cleanTarget) subtarea = cleanTarget;
            if (targetLevel === 3 && cleanTarget) subsubtarea = cleanTarget;
            return { tarea, subtarea, subsubtarea };
          };
          const renderSubBranch = (targetLevel = 1, targetName = "", parentId = 0) => {
            if (!subBranchEl) return;
            const slots = resolveSubBranchSlots(targetLevel, targetName, parentId);
            const actName = actNameEl && actNameEl.value ? actNameEl.value : "Actividad";
            subBranchEl.textContent = buildBranchText(actName, slots);
          };
          const setDateBounds = (objective) => {
            const minDate = String(objective?.fecha_inicial || "");
            const maxDate = String(objective?.fecha_final || "");
            [actStartEl, actEndEl].forEach((el) => {
              if (!el) return;
              el.min = minDate || "";
              el.max = maxDate || "";
            });
          };
          const fillCollaborators = async (objective) => {
            if (!actOwnerEl || !actAssignedEl) return;
            const axisId = Number(objective?.eje_id || 0);
            if (!axisId) {
              actOwnerEl.innerHTML = '<option value="">Selecciona responsable</option>';
              actAssignedEl.innerHTML = "";
              return;
            }
            try {
              const response = await fetch(`/api/strategic-axes/${axisId}/collaborators`, {
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
              });
              const payload = await response.json().catch(() => ({}));
              const list = Array.isArray(payload.data) ? payload.data : [];
              actOwnerEl.innerHTML = '<option value="">Selecciona responsable</option>' + list.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join("");
              actAssignedEl.innerHTML = list.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join("");
            } catch (_err) {
              actOwnerEl.innerHTML = '<option value="">Selecciona responsable</option>';
              actAssignedEl.innerHTML = "";
            }
          };
          const renderImpactedMilestonesOptions = (objective, selectedIds = []) => {
            if (!actImpactHitosEl) return;
            const selectedSet = new Set((Array.isArray(selectedIds) ? selectedIds : [])
              .map((value) => Number(value || 0))
              .filter((value) => value > 0));
            const hitos = Array.isArray(objective?.hitos) ? objective.hitos : [];
            if (!hitos.length) {
              actImpactHitosEl.disabled = true;
              actImpactHitosEl.innerHTML = '<option value="" disabled>Sin hitos registrados en este objetivo</option>';
              return;
            }
            actImpactHitosEl.disabled = false;
            const validIds = new Set(hitos.map((hito) => Number(hito?.id || 0)).filter((value) => value > 0));
            actImpactHitosEl.innerHTML = hitos.map((hito) => {
              const id = Number(hito?.id || 0);
              if (!id) return "";
              const selected = selectedSet.has(id) && validIds.has(id) ? "selected" : "";
              const label = String(hito?.nombre || "Hito").trim() || "Hito";
              return `<option value="${id}" ${selected}>${escapeHtml(label)}</option>`;
            }).join("");
          };
          const currentApprovalForActivity = () => {
            if (!currentActivityId) return null;
            return approvalsByActivity[Number(currentActivityId)] || null;
          };
          const renderStateStrip = () => {
            const rawStatus = String(currentActivityData?.status || "").trim().toLowerCase();
            const endDate = String(currentActivityData?.fecha_final || "").trim();
            const displayStatus = (() => {
              if (rawStatus === "terminada") return "Terminada";
              if (rawStatus === "en revisión") return "En revisión";
              if (rawStatus === "atrasada") return "Atrasada";
              if (endDate && todayIso() > endDate) return "Atrasada";
              if (rawStatus === "en proceso") return "En proceso";
              return "No iniciado";
            })();
            [stateNoIniciadoBtn, stateEnProcesoBtn, stateTerminadoBtn, stateEnRevisionBtn].forEach((btn) => {
              if (btn) btn.classList.remove("active");
            });
            if (displayStatus === "No iniciado" && stateNoIniciadoBtn) stateNoIniciadoBtn.classList.add("active");
            if (displayStatus === "En proceso" && stateEnProcesoBtn) stateEnProcesoBtn.classList.add("active");
            if (displayStatus === "Terminada" && stateTerminadoBtn) stateTerminadoBtn.classList.add("active");
            if (displayStatus === "En revisión" && stateEnRevisionBtn) stateEnRevisionBtn.classList.add("active");
            const canChangeStatus = !!(currentActivityData && currentActivityData.can_change_status);
            if (stateEnProcesoBtn) stateEnProcesoBtn.disabled = !currentActivityId || !canChangeStatus;
            if (stateTerminadoBtn) stateTerminadoBtn.disabled = !currentActivityId || !canChangeStatus;
            if (statusValueEl) {
              const tone = displayStatus === "Terminada" ? "green"
                : displayStatus === "En revisión" ? "orange"
                  : displayStatus === "En proceso" ? "yellow"
                    : displayStatus === "Atrasada" ? "red"
                      : "gray";
              statusValueEl.innerHTML = `<span class="poa-semaforo ${tone}"></span>${escapeHtml(displayStatus)}`;
            }
            const subList = Array.isArray(currentSubactivities) ? currentSubactivities : [];
            let progress = 0;
            if (subList.length) {
              const completed = subList.filter((sub) => {
                const subEnd = String(sub?.fecha_final || "").trim();
                return !!subEnd && subEnd <= todayIso();
              }).length;
              progress = Math.round((completed / subList.length) * 100);
            } else {
              progress = displayStatus === "Terminada" ? 100 : 0;
            }
            if (progressValueEl) progressValueEl.textContent = `${progress}%`;
            const approval = currentApprovalForActivity();
            const canReview = !!approval;
            if (approveBtn) approveBtn.style.display = canReview ? "inline-flex" : "none";
            if (rejectBtn) rejectBtn.style.display = canReview ? "inline-flex" : "none";
          };
          const resetActivityForm = () => {
            if (actNameEl) actNameEl.value = "";
            if (actStartEl) actStartEl.value = "";
            if (actEndEl) actEndEl.value = "";
            if (actRecurrenteEl) actRecurrenteEl.checked = false;
            if (actPeriodicidadEl) actPeriodicidadEl.value = "";
            if (actEveryDaysEl) actEveryDaysEl.value = "";
            if (actDescRich) {
              actDescRich.setHtml("");
            } else if (actDescEl) {
              actDescEl.value = "";
            }
            if (actOwnerEl) actOwnerEl.value = "";
            if (actAssignedEl) Array.from(actAssignedEl.options || []).forEach((opt) => { opt.selected = false; });
            if (actImpactHitosEl) actImpactHitosEl.innerHTML = "";
            currentActivityId = null;
            currentActivityData = null;
            currentSubactivities = [];
            currentBudgetItems = [];
            currentDeliverables = [];
            selectedListActivityId = null;
            editingSubId = null;
            editingBudgetIndex = -1;
            currentParentSubId = 0;
            syncRecurringFields();
            renderStateStrip();
            clearBudgetForm();
            renderBudgetItems();
            renderDeliverables();
            showDeliverableMsg("");
          };
          const getCurrentObjectiveActivities = () => {
            if (!currentObjective) return [];
            return activitiesByObjective[Number(currentObjective.id || 0)] || [];
          };
          const renderActivityList = () => {
            if (!actListEl) return;
            const canManage = canManageContent();
            const list = getCurrentObjectiveActivities();
            const hasSelection = !!Number(selectedListActivityId || 0);
            if (editActBtn) editActBtn.disabled = !canManage || !hasSelection;
            if (deleteActBtn) deleteActBtn.disabled = !canManage || !hasSelection;
            if (!list.length) {
              actListEl.innerHTML = '<div class="poa-sub-meta">Sin actividades registradas.</div>';
              if (editActBtn) editActBtn.disabled = true;
              if (deleteActBtn) deleteActBtn.disabled = true;
              showActListMsg(canManage ? "Usa 'Nuevo' para crear la primera actividad." : "No hay actividades registradas.");
              return;
            }
            actListEl.innerHTML = list.map((item) => {
              const id = Number(item.id || 0);
              const active = id === Number(selectedListActivityId || 0) ? "active" : "";
              return `
                <article class="poa-act-item ${active}" data-poa-activity-id="${id}">
                  <div><strong>${escapeHtml(item.nombre || "Actividad sin nombre")}</strong></div>
                  <div class="meta">${escapeHtml(item.codigo || "sin código")} · ${escapeHtml(item.responsable || "Sin responsable")}</div>
                </article>
              `;
            }).join("");
            actListEl.querySelectorAll("[data-poa-activity-id]").forEach((node) => {
              node.addEventListener("click", () => {
                selectedListActivityId = Number(node.getAttribute("data-poa-activity-id") || 0);
                renderActivityList();
                showActListMsg("Actividad seleccionada. Usa 'Editar' para cargarla.");
              });
            });
            if (!selectedListActivityId) {
              showActListMsg(canManage ? "Selecciona una actividad de la lista o usa 'Nuevo'." : "Selecciona una actividad de la lista.");
            }
          };
          const loadSelectedActivityInForm = () => {
            if (!canManageContent()) return;
            const list = getCurrentObjectiveActivities();
            const selected = list.find((item) => Number(item.id || 0) === Number(selectedListActivityId || 0)) || null;
            if (!selected) {
              showActListMsg("Selecciona una actividad para editar.", true);
              return;
            }
            populateActivityForm(selected);
            setActivityEditorMode("edit");
            showActListMsg("Actividad cargada en formulario.");
            if (actNameEl) actNameEl.focus();
          };
          const startNewActivity = () => {
            if (!canManageContent()) return;
            selectedListActivityId = null;
            const objective = currentObjective;
            resetActivityForm();
            if (objective) {
              currentObjective = objective;
              canValidateDeliverables = !!objective.can_validate_deliverables;
              renderImpactedMilestonesOptions(objective, []);
              setDateBounds(objective);
            }
            renderActivityBranch();
            renderSubtasks();
            renderActivityList();
            setActivityEditorMode("new");
            showActListMsg("Nueva actividad lista para captura.");
            if (assignedByEl) assignedByEl.textContent = `Asignado por: ${objective?.lider || "N/D"}`;
            if (actNameEl) actNameEl.focus();
          };
          const deleteSelectedActivity = async () => {
            if (!canManageContent()) return;
            const id = Number(selectedListActivityId || 0);
            if (!id) {
              showActListMsg("Selecciona una actividad para eliminar.", true);
              return;
            }
            if (!window.confirm("¿Eliminar esta actividad?")) return;
            showActListMsg("Eliminando actividad...");
            try {
              const response = await fetch(`/api/poa/activities/${id}`, {
                method: "DELETE",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
              });
              const data = await response.json().catch(() => ({}));
              if (!response.ok || data.success === false) {
                throw new Error(data.error || "No se pudo eliminar la actividad.");
              }
              await loadBoard();
              if (currentObjective) {
                selectedListActivityId = null;
                startNewActivity();
              }
              showActListMsg("Actividad eliminada.");
            } catch (error) {
              showActListMsg(error.message || "No se pudo eliminar la actividad.", true);
            }
          };
          const populateActivityForm = (activity) => {
            if (!activity) return;
            if (actNameEl) actNameEl.value = activity.nombre || "";
            if (actOwnerEl) actOwnerEl.value = activity.responsable || "";
            if (actStartEl) actStartEl.value = activity.fecha_inicial || "";
            if (actEndEl) actEndEl.value = activity.fecha_final || "";
            if (actDescRich) {
              actDescRich.setHtml(activity.descripcion || "");
            } else if (actDescEl) {
              actDescEl.value = activity.descripcion || "";
            }
            if (actRecurrenteEl) actRecurrenteEl.checked = !!activity.recurrente;
            if (actPeriodicidadEl) actPeriodicidadEl.value = activity.periodicidad || "";
            if (actEveryDaysEl) actEveryDaysEl.value = activity.cada_xx_dias || "";
            currentActivityId = Number(activity.id || 0);
            selectedListActivityId = Number(activity.id || 0);
            currentActivityData = activity;
            currentSubactivities = Array.isArray(activity.subactivities) ? activity.subactivities : [];
            currentBudgetItems = normalizeBudgetItems(activity.budget_items || []);
            currentDeliverables = normalizeDeliverables(activity.entregables || []);
            if (!currentDeliverables.length && String(activity.entregable || "").trim()) {
              currentDeliverables = [{ id: 0, nombre: String(activity.entregable || "").trim(), validado: false, orden: 1 }];
            }
            renderImpactedMilestonesOptions(currentObjective, (activity.hitos_impacta || []).map((item) => Number(item?.id || 0)));
            syncRecurringFields();
            renderSubtasks();
            renderStateStrip();
            renderActivityBranch();
            clearBudgetForm();
            renderBudgetItems();
            renderDeliverables();
            renderActivityList();
          };
          const activatePoaTab = (tabKey) => {
            document.querySelectorAll("[data-poa-tab]").forEach((btn) => { btn.classList.remove("active"); btn.classList.remove("tab-active"); });
            document.querySelectorAll("[data-poa-panel]").forEach((panel) => panel.classList.remove("active"));
            const tabBtn = document.querySelector(`[data-poa-tab="${tabKey}"]`);
            const panel = document.querySelector(`[data-poa-panel="${tabKey}"]`);
            if (tabBtn) { tabBtn.classList.add("active"); tabBtn.classList.add("tab-active"); }
            if (panel) panel.classList.add("active");
          };
          const openActivityForm = async (objectiveId, options = {}) => {
            let objective = objectivesById[Number(objectiveId)];
            if (!objective) {
              showMsg("Recargando datos POA para abrir el objetivo...");
              await loadBoard();
              objective = objectivesById[Number(objectiveId)];
            }
            if (!objective) {
              showMsg("No se encontró el objetivo seleccionado en el tablero POA.", true);
              return;
            }
            currentObjective = objective;
            canValidateDeliverables = !!objective.can_validate_deliverables;
            const targetActivityId = Number(options.activityId || 0);
            const shouldLoadExisting = !!(targetActivityId || options.focusSubId);
            const currentList = activitiesByObjective[Number(objective.id || 0)] || [];
            const existing = targetActivityId
              ? (currentList.find((item) => Number(item.id || 0) === targetActivityId) || null)
              : ((currentList[0]) || null);
            if (titleEl) titleEl.textContent = (shouldLoadExisting && existing) ? "Editar actividad" : "Nueva actividad";
            if (subtitleEl) subtitleEl.textContent = `${objective.codigo || ""} · ${objective.nombre || "Objetivo"}`;
            if (assignedByEl) assignedByEl.textContent = `Asignado por: ${(shouldLoadExisting ? existing?.created_by : "") || objective.lider || "N/D"}`;
            resetActivityForm();
            showModalMsg("");
            setDateBounds(objective);
            await fillCollaborators(objective);
            renderImpactedMilestonesOptions(objective, []);
            if (existing) {
              if (shouldLoadExisting) {
                selectedListActivityId = Number(existing.id || 0);
                populateActivityForm(existing);
                setActivityEditorMode("edit");
              } else {
                selectedListActivityId = Number(currentList[0]?.id || 0) || null;
                renderActivityList();
                setActivityEditorMode("list");
                showActListMsg("Selecciona una actividad y pulsa 'Editar' o crea una con 'Nuevo'.");
              }
              if (options.focusSubId && selectedListActivityId) {
                activatePoaTab("sub");
                const subId = Number(options.focusSubId || 0);
                if (subId) {
                  await openSubtaskForm(subId, 0);
                }
              }
            } else {
              renderActivityList();
              setActivityEditorMode("list");
              showActListMsg("Este objetivo no tiene actividades. Pulsa 'Nuevo' para crear la primera.");
            }
            renderActivityList();
            openModal();
          };
          const orderSubtasks = (items) => {
            const childrenByParent = {};
            (items || []).forEach((item) => {
              const parent = Number(item.parent_subactivity_id || 0);
              if (!childrenByParent[parent]) childrenByParent[parent] = [];
              childrenByParent[parent].push(item);
            });
            Object.keys(childrenByParent).forEach((key) => {
              childrenByParent[key].sort((a, b) => Number(a.id || 0) - Number(b.id || 0));
            });
            const out = [];
            const visit = (parentId) => {
              const list = childrenByParent[parentId] || [];
              list.forEach((item) => {
                out.push(item);
                visit(Number(item.id || 0));
              });
            };
            visit(0);
            return out;
          };
          const renderSubtasks = () => {
            if (!subListEl || !subHintEl) return;
            if (!currentActivityId) {
              subHintEl.textContent = "Guarda primero la actividad para habilitar subtareas.";
              subListEl.innerHTML = "";
              return;
            }
            const canManage = canManageContent();
            subHintEl.textContent = "Gestiona las subtareas de esta actividad.";
            if (!currentSubactivities.length) {
              subListEl.innerHTML = '<div class="poa-sub-meta">Sin subtareas registradas.</div>';
              return;
            }
            subListEl.innerHTML = orderSubtasks(currentSubactivities).map((item) => {
              const level = Number(item.nivel || 1);
              const marginLeft = Math.max(0, (level - 1) * 18);
              return `
              <article class="poa-sub-item" data-sub-id="${Number(item.id || 0)}">
                <h5>${escapeHtml(item.nombre || "Subtarea sin nombre")}</h5>
                <div class="poa-sub-meta">Nivel ${level} · ${escapeHtml(fmtDate(item.fecha_inicial))} - ${escapeHtml(fmtDate(item.fecha_final))} · Responsable: ${escapeHtml(item.responsable || "N/D")}</div>
                ${canManage ? `
                <div class="poa-sub-actions">
                  <button type="button" class="poa-sub-btn" data-sub-add-child="${Number(item.id || 0)}">Agregar hija</button>
                  <button type="button" class="poa-sub-btn" data-sub-edit="${Number(item.id || 0)}">Editar</button>
                  <button type="button" class="poa-sub-btn warn" data-sub-delete="${Number(item.id || 0)}">Eliminar</button>
                </div>
                ` : ""}
              </article>
            `;
            }).join("");
            if (canManage) {
              subListEl.querySelectorAll("[data-sub-add-child]").forEach((btn) => {
                btn.addEventListener("click", () => openSubtaskForm(0, Number(btn.getAttribute("data-sub-add-child"))));
              });
              subListEl.querySelectorAll("[data-sub-edit]").forEach((btn) => {
                btn.addEventListener("click", () => openSubtaskForm(Number(btn.getAttribute("data-sub-edit")), 0));
              });
              subListEl.querySelectorAll("[data-sub-delete]").forEach((btn) => {
                btn.addEventListener("click", async () => deleteSubtask(Number(btn.getAttribute("data-sub-delete"))));
              });
            }
          };
          const fillSubCollaborators = async () => {
            if (!subOwnerEl || !subAssignedEl || !currentObjective) return;
            const axisId = Number(currentObjective.eje_id || 0);
            if (!axisId) {
              subOwnerEl.innerHTML = '<option value="">Selecciona responsable</option>';
              subAssignedEl.innerHTML = "";
              return;
            }
            try {
              const response = await fetch(`/api/strategic-axes/${axisId}/collaborators`, {
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
              });
              const payload = await response.json().catch(() => ({}));
              const list = Array.isArray(payload.data) ? payload.data : [];
              subOwnerEl.innerHTML = '<option value="">Selecciona responsable</option>' + list.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join("");
              subAssignedEl.innerHTML = list.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join("");
            } catch (_err) {
              subOwnerEl.innerHTML = '<option value="">Selecciona responsable</option>';
              subAssignedEl.innerHTML = "";
            }
          };
          const setSubDateBounds = (parentSub = null) => {
            const minDate = parentSub?.fecha_inicial || (actStartEl && actStartEl.value ? actStartEl.value : "");
            const maxDate = parentSub?.fecha_final || (actEndEl && actEndEl.value ? actEndEl.value : "");
            [subStartEl, subEndEl].forEach((el) => {
              if (!el) return;
              el.min = minDate || "";
              el.max = maxDate || "";
            });
          };
          const syncSubRecurringFields = () => {
            const enabled = !!(subRecurrenteEl && subRecurrenteEl.checked);
            if (subPeriodicidadEl) {
              subPeriodicidadEl.disabled = !enabled;
              if (!enabled) subPeriodicidadEl.value = "";
            }
            const showEveryDays = enabled && subPeriodicidadEl && subPeriodicidadEl.value === "cada_xx_dias";
            if (subEveryDaysWrapEl) subEveryDaysWrapEl.style.display = showEveryDays ? "block" : "none";
            if (subEveryDaysEl && !showEveryDays) subEveryDaysEl.value = "";
          };
          const openSubtaskForm = async (subId = 0, parentId = 0) => {
            if (!canManageContent()) return;
            if (!currentActivityId) {
              showModalMsg("Guarda la actividad antes de crear subtareas.", true);
              return;
            }
            editingSubId = subId || 0;
            currentParentSubId = parentId || 0;
            await fillSubCollaborators();
            const found = currentSubactivities.find((item) => Number(item.id || 0) === Number(editingSubId));
            if (found && found.parent_subactivity_id) {
              currentParentSubId = Number(found.parent_subactivity_id || 0);
            }
            const parentSub = currentSubactivities.find((item) => Number(item.id || 0) === Number(currentParentSubId)) || null;
            const targetLevel = found ? Number(found.nivel || 1) : (parentSub ? Number(parentSub.nivel || 1) + 1 : 1);
            setSubDateBounds(parentSub);
            if (subNameEl) subNameEl.value = found?.nombre || "";
            if (subOwnerEl) subOwnerEl.value = found?.responsable || "";
            if (subStartEl) subStartEl.value = found?.fecha_inicial || "";
            if (subEndEl) subEndEl.value = found?.fecha_final || "";
            if (subRecurrenteEl) subRecurrenteEl.checked = !!found?.recurrente;
            if (subPeriodicidadEl) subPeriodicidadEl.value = found?.periodicidad || "";
            if (subEveryDaysEl) subEveryDaysEl.value = found?.cada_xx_dias || "";
            syncSubRecurringFields();
            if (subDescEl) subDescEl.value = found?.descripcion || "";
            renderSubBranch(targetLevel, found?.nombre || "", currentParentSubId);
            showSubMsg("");
            openSubModal();
            if (subNameEl) subNameEl.focus();
          };
          const saveSubtask = async () => {
            if (!canManageContent()) {
              showSubMsg("Solo administrador puede guardar subtareas.", true);
              return;
            }
            if (!currentActivityId) {
              showSubMsg("Guarda primero la actividad.", true);
              return;
            }
            const nombre = (subNameEl && subNameEl.value ? subNameEl.value : "").trim();
            const responsable = (subOwnerEl && subOwnerEl.value ? subOwnerEl.value : "").trim();
            const fechaInicial = subStartEl && subStartEl.value ? subStartEl.value : "";
            const fechaFinal = subEndEl && subEndEl.value ? subEndEl.value : "";
            const recurrente = !!(subRecurrenteEl && subRecurrenteEl.checked);
            const periodicidad = (subPeriodicidadEl && subPeriodicidadEl.value ? subPeriodicidadEl.value : "").trim();
            const cadaXxDiasRaw = (subEveryDaysEl && subEveryDaysEl.value ? subEveryDaysEl.value : "").trim();
            const cadaXxDias = cadaXxDiasRaw ? Number(cadaXxDiasRaw) : 0;
            const baseDesc = (subDescEl && subDescEl.value ? subDescEl.value : "").trim();
            const assigned = subAssignedEl ? Array.from(subAssignedEl.selectedOptions || []).map((opt) => opt.value).filter(Boolean) : [];
            if (!nombre) {
              showSubMsg("Nombre es obligatorio.", true);
              return;
            }
            if (!fechaInicial || !fechaFinal) {
              showSubMsg("Fecha inicial y fecha final son obligatorias.", true);
              return;
            }
            if (fechaInicial > fechaFinal) {
              showSubMsg("La fecha inicial no puede ser mayor que la final.", true);
              return;
            }
            if ((subStartEl && subStartEl.min && fechaInicial < subStartEl.min) || (subEndEl && subEndEl.max && fechaFinal > subEndEl.max)) {
              showSubMsg("Las fechas deben estar dentro del rango de la actividad.", true);
              return;
            }
            if (recurrente) {
              if (!periodicidad) {
                showSubMsg("Selecciona una periodicidad para la subtarea recurrente.", true);
                return;
              }
              if (periodicidad === "cada_xx_dias" && (!Number.isInteger(cadaXxDias) || cadaXxDias <= 0)) {
                showSubMsg("Cada xx dias debe ser un entero mayor a 0.", true);
                return;
              }
            }
            const descripcion = assigned.length
              ? `${baseDesc}${baseDesc ? "\\n\\n" : ""}Personas asignadas: ${assigned.join(", ")}`
              : baseDesc;
            const payload = {
              nombre,
              responsable,
              fecha_inicial: fechaInicial,
              fecha_final: fechaFinal,
              recurrente,
              periodicidad: recurrente ? periodicidad : "",
              cada_xx_dias: recurrente && periodicidad === "cada_xx_dias" ? cadaXxDias : 0,
              descripcion,
            };
            if (!editingSubId && currentParentSubId) {
              payload.parent_subactivity_id = currentParentSubId;
            }
            showSubMsg("Guardando subtarea...");
            try {
              const url = editingSubId ? `/api/poa/subactivities/${editingSubId}` : `/api/poa/activities/${currentActivityId}/subactivities`;
              const method = editingSubId ? "PUT" : "POST";
              const response = await fetch(url, {
                method,
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
                body: JSON.stringify(payload),
              });
              const data = await response.json().catch(() => ({}));
              if (!response.ok || data.success === false) {
                throw new Error(data.error || "No se pudo guardar la subtarea.");
              }
              const item = data.data || {};
              if (editingSubId) {
                currentSubactivities = currentSubactivities.map((sub) => Number(sub.id || 0) === Number(editingSubId) ? item : sub);
              } else {
                currentSubactivities = [item, ...currentSubactivities];
              }
              renderSubtasks();
              closeSubModal();
              showModalMsg("Subtarea guardada.");
            } catch (error) {
              showSubMsg(error.message || "No se pudo guardar la subtarea.", true);
            }
          };
          const deleteSubtask = async (subId) => {
            if (!canManageContent()) return;
            if (!subId) return;
            if (!window.confirm("¿Eliminar esta subtarea?")) return;
            try {
              const response = await fetch(`/api/poa/subactivities/${subId}`, {
                method: "DELETE",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
              });
              const data = await response.json().catch(() => ({}));
              if (!response.ok || data.success === false) {
                throw new Error(data.error || "No se pudo eliminar la subtarea.");
              }
              const removeIds = new Set([Number(subId)]);
              let changed = true;
              while (changed) {
                changed = false;
                currentSubactivities.forEach((item) => {
                  const itemId = Number(item.id || 0);
                  const parentId = Number(item.parent_subactivity_id || 0);
                  if (!removeIds.has(itemId) && removeIds.has(parentId)) {
                    removeIds.add(itemId);
                    changed = true;
                  }
                });
              }
              currentSubactivities = currentSubactivities.filter((item) => !removeIds.has(Number(item.id || 0)));
              renderSubtasks();
              showModalMsg("Subtarea eliminada.");
            } catch (error) {
              showModalMsg(error.message || "No se pudo eliminar la subtarea.", true);
            }
          };
          const validateActivityDates = () => {
            const start = actStartEl && actStartEl.value ? actStartEl.value : "";
            const end = actEndEl && actEndEl.value ? actEndEl.value : "";
            if (!start || !end) return "Fecha inicial y fecha final son obligatorias.";
            if (start > end) return "La fecha inicial no puede ser mayor que la fecha final.";
            const minDate = String(currentObjective?.fecha_inicial || "");
            const maxDate = String(currentObjective?.fecha_final || "");
            if (minDate && start < minDate) return "La fecha inicial no puede ser menor a la del objetivo.";
            if (maxDate && end > maxDate) return "La fecha final no puede ser mayor a la del objetivo.";
            return "";
          };
          const syncRecurringFields = () => {
            const enabled = !!(actRecurrenteEl && actRecurrenteEl.checked);
            if (actPeriodicidadEl) {
              actPeriodicidadEl.disabled = !enabled;
              if (!enabled) actPeriodicidadEl.value = "";
            }
            const showEveryDays = enabled && actPeriodicidadEl && actPeriodicidadEl.value === "cada_xx_dias";
            if (actEveryDaysWrapEl) actEveryDaysWrapEl.style.display = showEveryDays ? "block" : "none";
            if (actEveryDaysEl && !showEveryDays) actEveryDaysEl.value = "";
          };
          const saveActivity = async () => {
            if (!canManageContent()) {
              showModalMsg("Solo administrador puede editar actividades.", true);
              return;
            }
            if (isSaving) return;
            if (activityEditorMode === "list") {
              showActListMsg("Pulsa 'Nuevo' o 'Editar' antes de guardar.", true);
              return;
            }
            if (!currentObjective) {
              showModalMsg("Selecciona un objetivo válido.", true);
              return;
            }
            const nombre = (actNameEl && actNameEl.value ? actNameEl.value : "").trim();
            const responsable = (actOwnerEl && actOwnerEl.value ? actOwnerEl.value : "").trim();
            const fechaInicial = actStartEl && actStartEl.value ? actStartEl.value : "";
            const fechaFinal = actEndEl && actEndEl.value ? actEndEl.value : "";
            const recurrente = !!(actRecurrenteEl && actRecurrenteEl.checked);
            const periodicidad = (actPeriodicidadEl && actPeriodicidadEl.value ? actPeriodicidadEl.value : "").trim();
            const cadaXxDiasRaw = (actEveryDaysEl && actEveryDaysEl.value ? actEveryDaysEl.value : "").trim();
            const cadaXxDias = cadaXxDiasRaw ? Number(cadaXxDiasRaw) : 0;
            const descripcionBase = (actDescRich ? actDescRich.getHtml() : (actDescEl && actDescEl.value ? actDescEl.value : "")).trim();
            const assigned = actAssignedEl ? Array.from(actAssignedEl.selectedOptions || []).map((opt) => opt.value).filter(Boolean) : [];
            const impactedMilestoneIds = actImpactHitosEl ? Array.from(actImpactHitosEl.selectedOptions || []).map((opt) => Number(opt.value || 0)).filter((value) => value > 0) : [];
            if (!nombre) {
              showModalMsg("Nombre es obligatorio.", true);
              return;
            }
            const deliverables = normalizeDeliverables(currentDeliverables);
            if (!deliverables.length) {
              showDeliverableMsg("Agrega al menos un entregable.", true);
              activatePoaTab("deliverables");
              return;
            }
            const dateError = validateActivityDates();
            if (dateError) {
              showModalMsg(dateError, true);
              return;
            }
            if (recurrente) {
              if (!periodicidad) {
                showModalMsg("Selecciona una periodicidad para la actividad recurrente.", true);
                return;
              }
              if (periodicidad === "cada_xx_dias" && (!Number.isInteger(cadaXxDias) || cadaXxDias <= 0)) {
                showModalMsg("Cada xx dias debe ser un entero mayor a 0.", true);
                return;
              }
            }
            const assignedHtml = assigned.length
              ? `<p><em>Personas asignadas: ${escapeHtml(assigned.join(", "))}</em></p>`
              : "";
            const descripcion = assignedHtml ? `${descripcionBase}${assignedHtml}` : descripcionBase;
            const payload = {
              objective_id: Number(currentObjective.id || 0),
              nombre,
              entregable: String(deliverables[0]?.nombre || "").trim(),
              entregables: deliverables,
              responsable,
              fecha_inicial: fechaInicial,
              fecha_final: fechaFinal,
              recurrente,
              periodicidad: recurrente ? periodicidad : "",
              cada_xx_dias: recurrente && periodicidad === "cada_xx_dias" ? cadaXxDias : 0,
              descripcion,
              budget_items: normalizeBudgetItems(currentBudgetItems),
              impacted_milestone_ids: impactedMilestoneIds,
            };
            isSaving = true;
            if (saveBtn) saveBtn.disabled = true;
            showModalMsg("Guardando actividad...");
            try {
              const response = await fetch(currentActivityId ? `/api/poa/activities/${currentActivityId}` : "/api/poa/activities", {
                method: currentActivityId ? "PUT" : "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
                body: JSON.stringify(payload),
              });
              const data = await response.json().catch(() => ({}));
              if (!response.ok || data.success === false) {
                throw new Error(data.error || "No se pudo guardar la actividad.");
              }
              currentActivityId = Number(data.data?.id || currentActivityId || 0);
              selectedListActivityId = Number(data.data?.id || selectedListActivityId || 0);
              currentActivityData = data.data || currentActivityData;
              currentSubactivities = Array.isArray(data.data?.subactivities) ? data.data.subactivities : currentSubactivities;
              currentBudgetItems = normalizeBudgetItems(data.data?.budget_items || currentBudgetItems);
              currentDeliverables = normalizeDeliverables(data.data?.entregables || deliverables);
              renderSubtasks();
              renderBudgetItems();
              renderDeliverables();
              renderStateStrip();
              renderActivityList();
              showModalMsg("Actividad guardada correctamente. Refrescando listado...");
              await loadBoard();
              if (currentObjective) {
                currentObjective = objectivesById[Number(currentObjective.id || 0)] || currentObjective;
                const latest = (activitiesByObjective[Number(currentObjective.id || 0)] || [])
                  .find((item) => Number(item.id || 0) === Number(currentActivityId || selectedListActivityId || 0))
                  || null;
                if (latest) {
                  populateActivityForm(latest);
                  if (assignedByEl) assignedByEl.textContent = `Asignado por: ${latest?.created_by || currentObjective.lider || "N/D"}`;
                  setActivityEditorMode("edit");
                } else {
                  renderActivityList();
                }
              }
              showModalMsg("Actividad guardada correctamente.");
            } catch (error) {
              showModalMsg(error.message || "No se pudo guardar la actividad.", true);
            } finally {
              isSaving = false;
              if (saveBtn) saveBtn.disabled = false;
            }
          };
          const markInProgress = async () => {
            if (!currentActivityId) {
              showModalMsg("Guarda primero la actividad para cambiar su estado.", true);
              return;
            }
            const canChangeStatus = !!(currentActivityData && currentActivityData.can_change_status);
            if (!canChangeStatus) {
              showModalMsg("Solo el dueño de la tarea puede cambiar estatus.", true);
              return;
            }
            showModalMsg("Actualizando estado...");
            try {
              const response = await fetch(`/api/poa/activities/${currentActivityId}/mark-in-progress`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
              });
              const data = await response.json().catch(() => ({}));
              if (!response.ok || data.success === false) {
                throw new Error(data.error || "No se pudo marcar en proceso.");
              }
              currentActivityData = data.data || currentActivityData;
              currentSubactivities = Array.isArray(data.data?.subactivities) ? data.data.subactivities : currentSubactivities;
              renderStateStrip();
              showModalMsg("Actividad en proceso.");
              await loadBoard();
            } catch (error) {
              showModalMsg(error.message || "No se pudo marcar en proceso.", true);
            }
          };
          const markFinished = async () => {
            if (!currentActivityId) {
              showModalMsg("Guarda primero la actividad para declararla terminada.", true);
              return;
            }
            const canChangeStatus = !!(currentActivityData && currentActivityData.can_change_status);
            if (!canChangeStatus) {
              showModalMsg("Solo el dueño de la tarea puede cambiar estatus.", true);
              return;
            }
            const deliverables = normalizeDeliverables(currentDeliverables);
            const entregableName = String(deliverables[0]?.nombre || currentActivityData?.entregable || "").trim() || "N/D";
            const sendReview = window.confirm(`El entregable es ${entregableName}, ¿Quiere enviarlo a revisión?`);
            showModalMsg(sendReview ? "Enviando a revisión..." : "Declarando terminado...");
            try {
              const response = await fetch(`/api/poa/activities/${currentActivityId}/mark-finished`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
                body: JSON.stringify({ enviar_revision: sendReview }),
              });
              const data = await response.json().catch(() => ({}));
              if (!response.ok || data.success === false) {
                throw new Error(data.error || "No se pudo actualizar el estado.");
              }
              currentActivityData = data.data || currentActivityData;
              currentSubactivities = Array.isArray(data.data?.subactivities) ? data.data.subactivities : currentSubactivities;
              renderStateStrip();
              showModalMsg(data.message || "Estado actualizado.");
              await loadBoard();
            } catch (error) {
              showModalMsg(error.message || "No se pudo actualizar el estado.", true);
            }
          };
          const resolveApproval = async (action) => {
            const approval = currentApprovalForActivity();
            if (!approval) {
              showModalMsg("No hay entregable pendiente para revisar.", true);
              return;
            }
            showModalMsg(action === "autorizar" ? "Aprobando entregable..." : "Rechazando entregable...");
            try {
              const response = await fetch(`/api/poa/approvals/${approval.id}/decision`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
                body: JSON.stringify({ accion: action, comentario: "" }),
              });
              const data = await response.json().catch(() => ({}));
              if (!response.ok || data.success === false) {
                throw new Error(data.error || "No se pudo procesar la revisión.");
              }
              showModalMsg(data.message || "Revisión procesada.");
              await loadBoard();
              if (currentObjective) {
                const latest = (activitiesByObjective[Number(currentObjective.id || 0)] || [])
                  .find((item) => Number(item.id || 0) === Number(currentActivityId))
                  || null;
                if (latest) {
                  currentActivityData = latest;
                  currentSubactivities = Array.isArray(latest.subactivities) ? latest.subactivities : [];
                }
                renderStateStrip();
              }
            } catch (error) {
              showModalMsg(error.message || "No se pudo procesar la revisión.", true);
            }
          };
          closeBtn && closeBtn.addEventListener("click", closeModal);
          cancelBtn && cancelBtn.addEventListener("click", closeModal);
          subCloseBtn && subCloseBtn.addEventListener("click", closeSubModal);
          subCancelBtn && subCancelBtn.addEventListener("click", closeSubModal);
          subSaveBtn && subSaveBtn.addEventListener("click", saveSubtask);
          subAddBtn && subAddBtn.addEventListener("click", () => openSubtaskForm(0, 0));
          subRecurrenteEl && subRecurrenteEl.addEventListener("change", syncSubRecurringFields);
          subPeriodicidadEl && subPeriodicidadEl.addEventListener("change", syncSubRecurringFields);
          openGanttBtn && openGanttBtn.addEventListener("click", async () => {
            if (!poaPermissions.can_view_gantt) return;
            if (!ganttModalEl) return;
            ganttModalEl.classList.add("open");
            document.body.style.overflow = "hidden";
            await renderPoaGantt();
          });
          openTreeBtn && openTreeBtn.addEventListener("click", () => {
            if (!treeModalEl) return;
            treeModalEl.classList.add("open");
            document.body.style.overflow = "hidden";
            renderPoaAdvanceTree();
          });
          openCalendarBtn && openCalendarBtn.addEventListener("click", () => {
            if (!calendarModalEl) return;
            calendarModalEl.classList.add("open");
            document.body.style.overflow = "hidden";
            renderPoaCalendar();
          });
          treeCloseBtn && treeCloseBtn.addEventListener("click", closeTreeModal);
          ganttCloseBtn && ganttCloseBtn.addEventListener("click", closeGanttModal);
          calendarCloseBtn && calendarCloseBtn.addEventListener("click", closeCalendarModal);
          treeModalEl && treeModalEl.addEventListener("click", (event) => {
            if (event.target === treeModalEl) closeTreeModal();
          });
          ganttModalEl && ganttModalEl.addEventListener("click", (event) => {
            if (event.target === ganttModalEl) closeGanttModal();
          });
          calendarModalEl && calendarModalEl.addEventListener("click", (event) => {
            if (event.target === calendarModalEl) closeCalendarModal();
          });
          calendarPrevBtn && calendarPrevBtn.addEventListener("click", () => {
            shiftCalendarMonth(-1);
            renderPoaCalendar();
          });
          calendarTodayBtn && calendarTodayBtn.addEventListener("click", () => {
            poaCalendarCursor = new Date();
            renderPoaCalendar();
          });
          calendarNextBtn && calendarNextBtn.addEventListener("click", () => {
            shiftCalendarMonth(1);
            renderPoaCalendar();
          });
          ganttShowAllBtn && ganttShowAllBtn.addEventListener("click", async () => {
            syncPoaGanttVisibility();
            Object.keys(poaGanttVisibility).forEach((key) => { poaGanttVisibility[key] = true; });
            renderPoaGanttFilters();
            await renderPoaGantt();
          });
          ganttHideAllBtn && ganttHideAllBtn.addEventListener("click", async () => {
            syncPoaGanttVisibility();
            Object.keys(poaGanttVisibility).forEach((key) => { poaGanttVisibility[key] = false; });
            renderPoaGanttFilters();
            await renderPoaGantt();
          });
          modalEl && modalEl.addEventListener("click", (event) => {
            if (event.target === modalEl) closeModal();
          });
          subModalEl && subModalEl.addEventListener("click", (event) => {
            if (event.target === subModalEl) closeSubModal();
          });
          document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && modalEl && modalEl.classList.contains("open")) closeModal();
            if (event.key === "Escape" && subModalEl && subModalEl.classList.contains("open")) closeSubModal();
            if (event.key === "Escape" && treeModalEl && treeModalEl.classList.contains("open")) closeTreeModal();
            if (event.key === "Escape" && ganttModalEl && ganttModalEl.classList.contains("open")) closeGanttModal();
            if (event.key === "Escape" && calendarModalEl && calendarModalEl.classList.contains("open")) closeCalendarModal();
          });
          saveBtn && saveBtn.addEventListener("click", saveActivity);
          saveTopBtn && saveTopBtn.addEventListener("click", saveActivity);
          newActBtn && newActBtn.addEventListener("click", startNewActivity);
          editActBtn && editActBtn.addEventListener("click", loadSelectedActivityInForm);
          editBottomBtn && editBottomBtn.addEventListener("click", loadSelectedActivityInForm);
          deleteActBtn && deleteActBtn.addEventListener("click", deleteSelectedActivity);
          delivAddBtn && delivAddBtn.addEventListener("click", addDeliverable);
          delivNameEl && delivNameEl.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              addDeliverable();
            }
          });
          budgetAddBtn && budgetAddBtn.addEventListener("click", addOrUpdateBudgetItem);
          budgetCancelBtn && budgetCancelBtn.addEventListener("click", clearBudgetForm);
          budgetMonthlyEl && budgetMonthlyEl.addEventListener("input", syncBudgetAnnual);
          stateEnProcesoBtn && stateEnProcesoBtn.addEventListener("click", markInProgress);
          stateTerminadoBtn && stateTerminadoBtn.addEventListener("click", markFinished);
          approveBtn && approveBtn.addEventListener("click", () => resolveApproval("autorizar"));
          rejectBtn && rejectBtn.addEventListener("click", () => resolveApproval("rechazar"));
          actNameEl && actNameEl.addEventListener("input", renderActivityBranch);
          actRecurrenteEl && actRecurrenteEl.addEventListener("change", syncRecurringFields);
          actPeriodicidadEl && actPeriodicidadEl.addEventListener("change", syncRecurringFields);
          actSuggestIaBtn && actSuggestIaBtn.addEventListener("click", async () => {
            if (!poaIaEnabled) {
              poaIaEnabled = await iaFeatureEnabled("poa");
              applyPoaPermissionsUI();
            }
            if (!poaIaEnabled) {
              showModalMsg("IA deshabilitada para tu rol en este módulo.", true);
              return;
            }
            if (!canManageContent()) {
              showModalMsg("Solo administrador puede usar sugerencias IA en actividades.", true);
              return;
            }
            const objectiveName = String(currentObjective?.nombre || "").trim();
            const axisName = String(currentObjective?.axis_name || "").trim();
            const activityName = (actNameEl && actNameEl.value ? actNameEl.value : "").trim();
            const descHtml = actDescRich ? actDescRich.getHtml() : (actDescEl && actDescEl.value ? actDescEl.value : "");
            const currentDesc = plainTextFromHtml(descHtml);
            if (!objectiveName && !activityName && !currentDesc) {
              showModalMsg("Captura nombre o descripción antes de pedir sugerencia IA.", true);
              return;
            }
            actSuggestIaBtn.disabled = true;
            showModalMsg("Generando sugerencia con IA...");
            try {
              const prompt = [
                "Mejora redacción de actividad POA.",
                `Eje: ${axisName || "Sin eje"}`,
                `Objetivo: ${objectiveName || "Sin objetivo"}`,
                `Actividad: ${activityName || "Sin nombre"}`,
                `Descripción actual: ${currentDesc || "Sin descripción"}`,
                "Responde solo con una descripción final clara, medible y en español.",
              ].join("\\n");
              const draftResp = await fetch("/api/ia/suggestions", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
                body: JSON.stringify({
                  prompt,
                  original_text: currentDesc,
                  target_module: "poa",
                  target_entity: "actividad",
                  target_entity_id: String(currentActivityId || ""),
                  target_field: "descripcion",
                }),
              });
              const draftData = await draftResp.json().catch(() => ({}));
              if (!draftResp.ok || draftData.success === false) {
                throw new Error(draftData.error || "No se pudo generar sugerencia IA.");
              }
              const draft = draftData.data || {};
              const decision = await openPoaIaSuggestionEditor({
                title: "Sugerencia IA para descripción de actividad",
                suggestion: String(draft.suggested_text || ""),
              });
              if (decision.action === "apply") {
                const applyResp = await fetch(`/api/ia/suggestions/${draft.id}/apply`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  credentials: "same-origin",
                  body: JSON.stringify({ edited_text: String(decision.text || "").trim() }),
                });
                const applyData = await applyResp.json().catch(() => ({}));
                if (!applyResp.ok || applyData.success === false) {
                  throw new Error(applyData.error || "No se pudo aplicar sugerencia IA.");
                }
                const appliedText = String(applyData?.data?.applied_text || decision.text || "").trim();
                if (actDescRich) actDescRich.setHtml(appliedText);
                else if (actDescEl) actDescEl.value = appliedText;
                showModalMsg("Sugerencia IA aplicada en la descripción de la actividad.");
              } else if (decision.action === "discard") {
                const discardResp = await fetch(`/api/ia/suggestions/${draft.id}/discard`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  credentials: "same-origin",
                  body: JSON.stringify({ reason: "Descartada por usuario", edited_text: String(decision.text || "").trim() }),
                });
                const discardData = await discardResp.json().catch(() => ({}));
                if (!discardResp.ok || discardData.success === false) {
                  throw new Error(discardData.error || "No se pudo descartar sugerencia IA.");
                }
                showModalMsg("Sugerencia IA descartada.");
              } else {
                showModalMsg("Sugerencia IA generada. Puedes volver a abrir IA para aplicarla o descartarla.");
              }
            } catch (error) {
              showModalMsg(error.message || "No se pudo generar sugerencia IA.", true);
            } finally {
              actSuggestIaBtn.disabled = !canManageContent() || !poaIaEnabled;
            }
          });
          subNameEl && subNameEl.addEventListener("input", () => {
            const found = currentSubactivities.find((item) => Number(item.id || 0) === Number(editingSubId));
            const targetLevel = found ? Number(found.nivel || 1) : (() => {
              const parentSub = currentSubactivities.find((item) => Number(item.id || 0) === Number(currentParentSubId));
              return parentSub ? Number(parentSub.nivel || 1) + 1 : 1;
            })();
            renderSubBranch(targetLevel, subNameEl.value || "", currentParentSubId);
          });
          document.querySelectorAll("[data-poa-tab]").forEach((tabBtn) => {
            tabBtn.addEventListener("click", () => {
              const tabKey = tabBtn.getAttribute("data-poa-tab");
              activatePoaTab(tabKey);
            });
          });

          const renderBoard = (payload) => {
            poaPermissions = {
              poa_access_level: String(payload?.permissions?.poa_access_level || "mis_tareas"),
              can_manage_content: !!payload?.permissions?.can_manage_content,
              can_view_gantt: !!payload?.permissions?.can_view_gantt,
            };
            const diagnostics = payload?.diagnostics || {};
            showMsg(
              `Permisos: ${poaPermissions.can_manage_content ? "edicion" : "solo lectura"} · acceso ${poaPermissions.poa_access_level} · rol ${String(diagnostics.role_detected || diagnostics.role_normalized || diagnostics.role_raw || "n/d")}`
            );
            applyPoaPermissionsUI();
            const objectives = Array.isArray(payload.objectives) ? payload.objectives : [];
            const activities = Array.isArray(payload.activities) ? payload.activities : [];
            renderOwnerActivityChart(activities);
            poaGanttObjectives = objectives;
            poaGanttActivities = activities;
            if (treeModalEl && treeModalEl.classList.contains("open")) {
              renderPoaAdvanceTree();
            }
            if (calendarModalEl && calendarModalEl.classList.contains("open")) {
              renderPoaCalendar();
            }
            const pendingApprovals = Array.isArray(payload.pending_approvals) ? payload.pending_approvals : [];
            objectivesById = {};
            activitiesByObjective = {};
            approvalsByActivity = {};
            objectives.forEach((obj) => {
              objectivesById[Number(obj.id || 0)] = obj;
            });
            const activityCountByObjective = {};
            activities.forEach((item) => {
              const key = Number(item.objective_id || 0);
              if (!key) return;
              activityCountByObjective[key] = (activityCountByObjective[key] || 0) + 1;
              if (!activitiesByObjective[key]) activitiesByObjective[key] = [];
              activitiesByObjective[key].push(item);
            });
            Object.keys(activitiesByObjective).forEach((key) => {
              activitiesByObjective[key].sort((a, b) => Number(b.id || 0) - Number(a.id || 0));
            });
            pendingApprovals.forEach((approval) => {
              const actId = Number(approval.activity_id || 0);
              if (!actId) return;
              approvalsByActivity[actId] = approval;
            });
            const activitiesNoOwner = activities.filter((item) => !String(item?.responsable || "").trim());
            if (noOwnerMsgEl) {
              if (!activitiesNoOwner.length) {
                noOwnerMsgEl.style.display = "none";
                noOwnerMsgEl.innerHTML = "";
              } else {
                const listItems = activitiesNoOwner.slice(0, 8)
                  .map((item) => `<li>${escapeHtml(item.codigo ? item.codigo + " - " + (item.nombre || "Sin nombre") : (item.nombre || "Sin nombre"))}</li>`)
                  .join("");
                const extraCount = activitiesNoOwner.length > 8 ? `<div class="axm-track-missing-more">+${activitiesNoOwner.length - 8} más</div>` : "";
                noOwnerMsgEl.style.display = "block";
                noOwnerMsgEl.innerHTML = `<article class="axm-track-missing-card"><h5 class="axm-track-missing-title">Actividades sin responsable</h5><div class="axm-track-missing-sub">${activitiesNoOwner.length} pendiente(s)</div><ul class="axm-track-missing-list">${listItems}</ul>${extraCount}</article>`;
              }
            }
            const subactivitiesNoOwner = activities.flatMap((item) => {
              const subList = Array.isArray(item?.subactivities) ? item.subactivities : [];
              return subList
                .filter((sub) => !String(sub?.responsable || "").trim())
                .map((sub) => ({
                  nombre: String(sub?.nombre || "Subtarea sin nombre"),
                  activity: String(item?.nombre || "Actividad sin nombre"),
                }));
            });
            if (noSubOwnerMsgEl) {
              if (!subactivitiesNoOwner.length) {
                noSubOwnerMsgEl.style.display = "none";
                noSubOwnerMsgEl.innerHTML = "";
              } else {
                const listItems = subactivitiesNoOwner.slice(0, 8)
                  .map((item) => `<li>${escapeHtml(item.nombre)} <span>(${escapeHtml(item.activity)})</span></li>`)
                  .join("");
                const extraCount = subactivitiesNoOwner.length > 8 ? `<div class="axm-track-missing-more">+${subactivitiesNoOwner.length - 8} más</div>` : "";
                noSubOwnerMsgEl.style.display = "block";
                noSubOwnerMsgEl.innerHTML = `<article class="axm-track-missing-card"><h5 class="axm-track-missing-title">Subtareas sin responsable</h5><div class="axm-track-missing-sub">${subactivitiesNoOwner.length} pendiente(s)</div><ul class="axm-track-missing-list">${listItems}</ul>${extraCount}</article>`;
              }
            }
            if (currentActivityId && currentObjective) {
              const latest = (activitiesByObjective[Number(currentObjective.id || 0)] || [])
                .find((item) => Number(item.id || 0) === Number(currentActivityId))
                || null;
              if (latest) {
                currentActivityData = latest;
                currentSubactivities = Array.isArray(latest.subactivities) ? latest.subactivities : [];
              }
              renderStateStrip();
            }
            const grouped = {};
            objectives.forEach((obj) => {
              const axisName = String(obj.axis_name || "Sin eje").trim() || "Sin eje";
              if (!grouped[axisName]) grouped[axisName] = [];
              grouped[axisName].push(obj);
            });
            const axisNames = Object.keys(grouped).sort((a, b) => a.localeCompare(b, "es"));
            if (!axisNames.length) {
              gridEl.innerHTML = '<div class="poa-obj-card"><h4>Sin objetivos</h4><div class="meta">No hay objetivos disponibles para mostrar.</div></div>';
              return;
            }
            gridEl.innerHTML = axisNames.map((axisName) => {
              const items = grouped[axisName] || [];
              const cards = items.map((obj) => {
                const countActivities = activityCountByObjective[Number(obj.id || 0)] || 0;
                return `
                  <article class="poa-obj-card" data-objective-id="${Number(obj.id || 0)}">
                    <h4>${escapeHtml(obj.nombre || "Objetivo sin nombre")}</h4>
                    <div class="meta">Hito: ${escapeHtml(obj.hito || "N/D")}</div>
                    <div class="meta">Fecha inicial: ${escapeHtml(fmtDate(obj.fecha_inicial))}</div>
                    <div class="meta">Fecha final: ${escapeHtml(fmtDate(obj.fecha_final))}</div>
                    <div class="meta">Actividades: ${countActivities}</div>
                    <span class="code">${escapeHtml(obj.codigo || "xx-yy-zz")}</span>
                    <div class="code-next">${escapeHtml(nextCode(obj.codigo || ""))}</div>
                  </article>
                `;
              }).join("");
              return `
                <section class="poa-axis-col" data-axis-col>
                  <header class="poa-axis-head">
                    <h3 class="poa-axis-title">${escapeHtml(axisName)}</h3>
                    <button type="button" class="poa-axis-toggle" data-axis-toggle aria-label="Colapsar columna">−</button>
                  </header>
                  <div class="poa-axis-cards">${cards || '<article class="poa-obj-card"><div class="meta">Sin objetivos</div></article>'}</div>
                </section>
              `;
            }).join("");

          };
          gridEl.addEventListener("click", async (event) => {
            const target = event.target;
            const toggleBtn = target && target.closest ? target.closest("[data-axis-toggle]") : null;
            if (toggleBtn) {
              const col = toggleBtn.closest("[data-axis-col]");
              if (!col) return;
              const collapsed = col.classList.toggle("collapsed");
              toggleBtn.textContent = collapsed ? "+" : "−";
              toggleBtn.setAttribute("aria-label", collapsed ? "Mostrar columna" : "Colapsar columna");
              return;
            }
            const card = target && target.closest ? target.closest("[data-objective-id]") : null;
            if (card && gridEl.contains(card)) {
              await openActivityForm(card.getAttribute("data-objective-id"));
            }
          });

          const loadBoard = async () => {
            showMsg("Cargando tablero POA...");
            try {
              const controller = new AbortController();
              const timeoutId = window.setTimeout(() => controller.abort(), 20000);
              const response = await fetch("/api/poa/board-data", {
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
                signal: controller.signal,
              });
              window.clearTimeout(timeoutId);
              const payload = await response.json().catch(() => ({}));
              if (!response.ok || payload.success === false) {
                throw new Error(payload.error || "No se pudo cargar la vista POA.");
              }
              renderBoard(payload);
            } catch (error) {
              const msg = (error && error.name === "AbortError")
                ? "Tiempo de espera agotado al cargar POA. Reintenta y valida conexión/servidor."
                : (error.message || "No se pudo cargar la vista POA.");
              showMsg(msg, true);
            }
          };
          const importStrategicCsv = async (file) => {
            if (!canManageContent()) {
              showMsg("Solo administrador puede importar información.", true);
              return;
            }
            if (!file) return;
            showMsg("Importando plantilla estratégica y POA...");
            const formData = new FormData();
            formData.append("file", file);
            const response = await fetch("/api/planificacion/importar-plan-poa", {
              method: "POST",
              credentials: "same-origin",
              body: formData,
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok || payload.success === false) {
              throw new Error(payload.error || "No se pudo importar el archivo.");
            }
            await loadBoard();
            const summary = payload.summary || {};
            const created = Number(summary.created || 0);
            const updated = Number(summary.updated || 0);
            const skipped = Number(summary.skipped || 0);
            const errors = Array.isArray(summary.errors) ? summary.errors.length : 0;
            showMsg(`Importación completada. Creados: ${created}, actualizados: ${updated}, omitidos: ${skipped}, errores: ${errors}.`, errors > 0);
          };
          downloadTemplateBtn && downloadTemplateBtn.addEventListener("click", () => {
            window.location.href = "/api/planificacion/plantilla-plan-poa.csv";
          });
          exportXlsBtn && exportXlsBtn.addEventListener("click", () => {
            window.location.href = "/api/planificacion/exportar-plan-poa.xlsx";
          });
          importCsvBtn && importCsvBtn.addEventListener("click", () => {
            if (importCsvFileEl) importCsvFileEl.click();
          });
          importCsvFileEl && importCsvFileEl.addEventListener("change", async () => {
            const file = importCsvFileEl.files && importCsvFileEl.files[0];
            if (!file) return;
            try {
              await importStrategicCsv(file);
            } catch (err) {
              showMsg(err.message || "No se pudo importar el archivo CSV.", true);
            } finally {
              importCsvFileEl.value = "";
            }
          });
          const openFromQuery = async () => {
            const params = new URLSearchParams(window.location.search || "");
            const objectiveId = Number(params.get("objective_id") || 0);
            const activityId = Number(params.get("activity_id") || 0);
            const subactivityId = Number(params.get("subactivity_id") || 0);
            let targetObjectiveId = objectiveId;
            if (!targetObjectiveId && activityId) {
              const matchObj = Object.keys(activitiesByObjective).find((objId) => {
                const list = activitiesByObjective[Number(objId)] || [];
                return list.some((item) => Number(item.id || 0) === activityId);
              });
              targetObjectiveId = Number(matchObj || 0);
            }
            if (!targetObjectiveId) return;
            await openActivityForm(targetObjectiveId, {
              activityId: activityId || 0,
              focusSubId: subactivityId || 0,
            });
          };

          iaFeatureEnabled("poa").then((enabled) => {
            poaIaEnabled = !!enabled;
            applyPoaPermissionsUI();
          });
          loadBoard().then(openFromQuery).catch(() => {});
        })();
      </script>
    </section>
""")


@router.get("/planes", response_class=HTMLResponse)
@router.get("/plan-estrategico", response_class=HTMLResponse)
@router.get("/ejes-estrategicos", response_class=HTMLResponse)
def ejes_estrategicos_page(request: Request):
    _bind_core_symbols()
    base_content = dedent("""
      <section class="grid gap-4 w-full max-w-6xl">
        <style>
          .cards-2{
            display:grid;
            grid-template-columns:repeat(2, minmax(0, 1fr));
            gap:22px;
            align-items:start;
          }
          .panel{
            background:#ffffff;
            border:1px solid #d8dee8;
            border-radius:20px;
            box-shadow:0 10px 24px rgba(16, 24, 40, .06);
            padding:18px 22px 20px;
          }
          .panel__head{
            display:flex;
            flex-direction:column;
            gap:10px;
            margin-bottom:8px;
          }
          .panel__title{
            margin:0;
            font-size:20px;
            font-weight:800;
            letter-spacing:0.10em;
            text-transform:uppercase;
            color:#475569;
          }
          .panel__meta{
            font-size:22px;
            color:#0f172a;
          }
          .panel__meta strong{ font-weight:900; }
          .panel__list{
            list-style:none;
            padding:0;
            margin:10px 0 0 0;
            color:#334155;
            font-size:22px;
            line-height:1.55;
          }
          .panel__list li{
            padding-left:34px;
            position:relative;
            margin:10px 0;
          }
          .panel__list li::before{
            content:"";
            position:absolute;
            left:14px;
            top:0.9em;
            width:6px;
            height:6px;
            border-radius:999px;
            background:rgba(100, 116, 139, .35);
            transform:translateY(-50%);
          }
          .panel__more{
            display:inline-block;
            margin-top:8px;
            color:#64748b;
            font-style:italic;
            font-size:20px;
            text-decoration:none;
          }
          .panel__more:hover{ text-decoration:underline; }
          .poa-small-muted{
            color:#475569;
            font-size:14px;
            margin-bottom:10px;
          }
          .poa-summary{
            display:flex;
            align-items:flex-start;
            justify-content:space-between;
            gap:12px;
          }
          .poa-summary h4{
            margin:0 0 4px 0;
            font-size:22px;
            color:#0f172a;
          }
          .poa-summary p{
            margin:0;
            color:#53657f;
            font-size:16px;
          }
          .poa-summary-total{
            white-space:nowrap;
            color:#334155;
            font-size:18px;
            font-weight:600;
          }
          @media (max-width:980px){
            .cards-2{ grid-template-columns:1fr; }
            .panel__title{ font-size:18px; }
            .panel__meta, .panel__list{ font-size:20px; }
          }
          .planes-action-card{
            border-radius:28px;
          }
          .planes-action-row{
            gap:14px;
            padding-top:16px;
          }
          @media (max-width: 1024px){
            .planes-action-row{ gap:12px; }
          }
          @media (max-width: 640px){
            .planes-action-row{ gap:10px; }
          }
        </style>
        <div class="titulo bg-base-200 rounded-box border border-base-300 p-4 sm:p-6">
          <div class="w-full flex flex-col md:flex-row items-center gap-10">
            <img
              src="/templates/icon/plan.svg"
              alt="Icono plan estratégico"
              width="96"
              height="96"
              class="shrink-0 rounded-box border border-base-300 bg-base-100 p-3 object-contain"
            />
            <div class="w-full grid gap-2 content-center">
              <div class="block w-full text-3xl sm:text-4xl lg:text-5xl font-bold leading-tight text-[color:var(--sidebar-bottom)]">Plan estratégico</div>
              <div class="block w-full text-base sm:text-lg text-base-content/70">Definir la estrategia institucional permite alinear objetivos, iniciativas y resultados.</div>
            </div>
          </div>
        </div>
        <div class="view-buttons page-view-buttons" id="planes-view-switch">
          <button class="view-pill boton_vista active" type="button" data-planes-view="list" data-tooltip="Lista" aria-label="Lista">
            <span class="boton_vista-icono view-pill-icon-mask" aria-hidden="true" style="--view-pill-icon-url:url('/icon/boton/grid.svg')"></span>
            <span class="view-pill-label boton_vista-label">List</span>
          </button>
          <button class="view-pill boton_vista" type="button" data-planes-view="kanban" data-tooltip="Kanban" aria-label="Kanban">
            <span class="boton_vista-icono view-pill-icon-mask" aria-hidden="true" style="--view-pill-icon-url:url('/icon/boton/kanban.svg')"></span>
            <span class="view-pill-label boton_vista-label">Kanban</span>
          </button>
          <button class="view-pill boton_vista" type="button" data-planes-view="organigrama" data-tooltip="Organigrama" aria-label="Organigrama">
            <span class="boton_vista-icono view-pill-icon-mask" aria-hidden="true" style="--view-pill-icon-url:url('/icon/boton/organigrama.svg')"></span>
            <span class="view-pill-label boton_vista-label">Organigrama</span>
          </button>
        </div>
        <article class="titulo bg-base-200 rounded-box border border-base-300 planes-action-card">
          <div class="p-4 sm:p-6">
            <h2 class="page-title">Plan estratégico</h2>
            <p class="page-description">Selecciona un eje para editarlo o crea uno nuevo.</p>
            <div class="view-buttons planes-action-row">
              <button type="button" id="planes-add-axis-btn" class="boton_vista boton_vista-eliptico active">Agregar eje</button>
              <a href="/api/planificacion/plantilla-plan-poa.csv" class="boton_vista boton_vista-eliptico">Descargar plantilla CSV</a>
              <button type="button" id="planes-import-csv-btn" class="boton_vista boton_vista-eliptico">Importar CSV estratégico + POA</button>
              <input id="planes-import-csv-file" type="file" accept=".csv,text/csv" class="hidden">
            </div>
            <div id="planes-import-csv-msg" class="text-sm sm:text-base pt-1 min-h-[1.5rem] text-base-content/70"></div>
          </div>
        </article>
        <article class="card border shadow-sm rounded-[2rem]" style="background:#eff4f2;border-color:#cfd7df;">
          <div class="card-body p-6 sm:p-8 lg:p-10" id="planes-view-list">
            <style>
              .dash{
                background:#ffffff;
                color:#1f2937;
                padding:18px 18px 12px;
                border-radius:18px;
              }
              .axm-tabs .tab-icon{
                width:16px;
                height:16px;
                min-width:16px;
                min-height:16px;
                display:inline-block;
                object-fit:contain;
                vertical-align:middle;
              }
              .dash__title{
                font-size:13.2px;
                line-height:1.2;
                margin:0 0 14px 0;
                font-weight:700;
              }
              .dash__grid{
                display:grid;
                grid-template-columns:repeat(4, minmax(0, 1fr));
                gap:16px;
              }
              .kpi{
                background:#fff;
                border:1px solid #d9dee7;
                border-radius:18px;
                box-shadow:0 10px 24px rgba(16, 24, 40, 0.06);
                padding:16px 18px;
                min-height:92px;
                display:flex;
                flex-direction:column;
                justify-content:center;
              }
              .kpi__label{
                font-size:8.4px;
                letter-spacing:0.12em;
                text-transform:uppercase;
                color:#61708a;
                font-weight:700;
                margin-bottom:10px;
              }
              .kpi__value{
                font-size:24px;
                line-height:1;
                font-weight:800;
                color:#0f5132;
              }
              .dash__progress{
                margin:14px 2px 10px;
                height:10px;
                background:#e5e7eb;
                border-radius:999px;
                overflow:hidden;
              }
              .dash__progress-bar{
                height:100%;
                width:0%;
                background:#cbd5e1;
                border-radius:999px;
              }
              .dash__foot{
                display:flex;
                gap:28px;
                font-size:12px;
                color:#374151;
                padding:6px 0 0;
              }
              .dash__foot strong{ font-weight:800; }
              .milestone-card{
                background:#ffffff;
                border:1px solid #d8dee8;
                border-radius:20px;
                box-shadow:0 10px 24px rgba(16, 24, 40, .06);
                padding:18px 22px;
              }
              .milestone-card__inner{
                display:flex;
                align-items:center;
                gap:22px;
              }
              .donut{
                --p:0;
                width:92px;
                height:92px;
                border-radius:999px;
                background:conic-gradient(#cbd5e1 calc(var(--p) * 1%), #e4e9f1 0);
                position:relative;
                box-shadow:inset 0 0 0 1px rgba(15, 23, 42, .06);
                flex:0 0 auto;
              }
              .donut::before{
                content:"";
                position:absolute;
                inset:12px;
                background:#ffffff;
                border-radius:999px;
                box-shadow:inset 0 0 0 1px rgba(15, 23, 42, .04);
              }
              .donut__center{
                position:absolute;
                inset:0;
                display:grid;
                place-items:center;
                font-weight:800;
                font-size:15.6px;
                color:#0f172a;
                z-index:1;
              }
              .milestone-info{
                display:flex;
                flex-direction:column;
                gap:10px;
                min-width:0;
              }
              .milestone-title{
                font-size:12px;
                font-weight:800;
                letter-spacing:0.10em;
                text-transform:uppercase;
                color:#475569;
              }
              .milestone-stats{
                display:flex;
                flex-wrap:wrap;
                gap:18px;
                font-size:12px;
                color:#334155;
              }
              .milestone-stats strong{
                font-weight:800;
                color:#0f172a;
              }
              .milestone-stats .is-danger{ color:#dc2626; }
              .cards-2{
                display:grid;
                grid-template-columns:repeat(2, minmax(0, 1fr));
                gap:22px;
                align-items:start;
              }
              .panel{
                background:#ffffff;
                border:1px solid #d8dee8;
                border-radius:20px;
                box-shadow:0 10px 24px rgba(16, 24, 40, .06);
                padding:18px 22px 20px;
              }
              .panel__head{
                display:flex;
                flex-direction:column;
                gap:10px;
                margin-bottom:8px;
              }
              .panel__title{
                margin:0;
                font-size:10px;
                font-weight:800;
                letter-spacing:0.10em;
                text-transform:uppercase;
                color:#475569;
              }
              .panel__meta{
                font-size:11px;
                color:#0f172a;
              }
              .panel__meta strong{ font-weight:900; }
              .panel__list{
                list-style:none;
                padding:0;
                margin:10px 0 0 0;
                color:#334155;
                font-size:11px;
                line-height:1.55;
              }
              .panel__list li{
                padding-left:34px;
                position:relative;
                margin:10px 0;
              }
              .panel__list li::before{
                content:"";
                position:absolute;
                left:14px;
                top:0.9em;
                width:6px;
                height:6px;
                border-radius:999px;
                background:rgba(100, 116, 139, .35);
                transform:translateY(-50%);
              }
              .panel__more{
                display:inline-block;
                margin-top:8px;
                color:#64748b;
                font-style:italic;
                font-size:10px;
                text-decoration:none;
              }
              .panel__more:hover{ text-decoration:underline; }
              @media (max-width:1100px){
                .dash__grid{ grid-template-columns:repeat(2, minmax(0, 1fr)); }
              }
              @media (max-width:980px){
                .cards-2{ grid-template-columns:1fr; }
                .panel__title{ font-size:9px; }
                .panel__meta, .panel__list{ font-size:10px; }
              }
              @media (max-width:520px){
                .dash__grid{ grid-template-columns:1fr; }
                .kpi__value{ font-size:21.6px; }
                .dash__foot{ font-size:10.8px; gap:18px; }
              }
              @media (max-width:640px){
                .milestone-card__inner{ align-items:flex-start; }
                .milestone-stats{ font-size:10.8px; gap:12px; }
                .milestone-title{ font-size:10.8px; }
                .donut{ width:84px; height:84px; }
                .donut::before{ inset:11px; }
              }
              /* ── tab panels ───────────────────────────────────── */
              .axm-foundacion{
                background:#fff;
                border:1px solid #d8dee8;
                border-radius:20px;
                padding:24px 28px;
                box-shadow:0 6px 18px rgba(16,24,40,.06);
              }
              .axm-foundacion h3{
                font-size:1rem;
                font-weight:700;
                color:#0f172a;
                margin:0 0 8px;
              }
              .axm-foundacion p{
                font-size:.875rem;
                color:#475569;
                margin:0 0 14px;
              }
              .axm-foundacion-toolbar{
                display:flex;
                flex-wrap:wrap;
                gap:6px;
                margin-bottom:10px;
              }
              .axm-foundacion-tool{
                font-size:.75rem;
                padding:4px 10px;
                border:1px solid #cbd5e1;
                border-radius:6px;
                background:#f8fafc;
                cursor:pointer;
                display:inline-flex;
                align-items:center;
                gap:4px;
                color:#334155;
              }
              .axm-foundacion-tool:hover{ background:#e2e8f0; }
              .axm-foundacion-editor{
                min-height:120px;
                border:1px solid #cbd5e1;
                border-radius:10px;
                padding:12px 14px;
                background:#f8fafc;
                font-size:.875rem;
                line-height:1.6;
                color:#1e293b;
                outline:none;
              }
              .axm-foundacion-editor[contenteditable=true]{
                background:#fff;
                border-color:#94a3b8;
              }
              .axm-foundacion-source{
                width:100%;
                min-height:120px;
                font-family:monospace;
                font-size:.8rem;
                border:1px solid #cbd5e1;
                border-radius:10px;
                padding:10px 12px;
                resize:vertical;
              }
              .axm-foundacion-actions{
                display:flex;
                gap:8px;
                margin-top:12px;
              }
              .axm-foundacion-msg{ font-size:.82rem; margin-top:8px; min-height:1.2em; }
              .axm-identidad{ background:#fff; border:1px solid #d8dee8; border-radius:20px; padding:0; box-shadow:0 6px 18px rgba(16,24,40,.06); overflow:hidden; }
              .axm-id-acc{ border-bottom:1px solid #e2e8f0; }
              .axm-id-acc:last-of-type{ border-bottom:none; }
              .axm-id-acc > summary{
                padding:14px 22px;
                font-size:.875rem;
                font-weight:700;
                color:#0f172a;
                cursor:pointer;
                list-style:none;
                user-select:none;
              }
              .axm-id-acc > summary::-webkit-details-marker{ display:none; }
              .axm-id-grid{
                display:grid;
                grid-template-columns:1fr 1fr;
                gap:16px;
                padding:0 22px 18px;
              }
              @media(max-width:720px){ .axm-id-grid{ grid-template-columns:1fr; } }
              .axm-textarea{
                width:100%;
                min-height:90px;
                border:1px solid #cbd5e1;
                border-radius:10px;
                padding:10px 12px;
                font-size:.875rem;
                line-height:1.6;
                resize:vertical;
                background:#f8fafc;
              }
              .axm-textarea:not([readonly]){ background:#fff; border-color:#94a3b8; }
              .axm-id-actions{ display:flex; gap:6px; margin-top:8px; }
              .axm-id-right h4{ font-size:.875rem; font-weight:700; color:#0f172a; margin:0 0 6px; }
              .axm-id-full{ font-size:.875rem; color:#334155; line-height:1.7; white-space:pre-wrap; }
              .axm-id-msg{ font-size:.82rem; padding:6px 22px 12px; min-height:1.2em; }
              .planes-obj-layout{
                display:grid;
                grid-template-columns: 300px minmax(0, 1fr);
                gap:16px;
                align-items:stretch;
              }
              .planes-obj-axes{
                background:#eef2f6;
                border:1px solid #d2dae4;
                border-radius:16px;
                padding:14px;
              }
              .planes-obj-side-title{
                margin:0 0 10px;
                font-weight:700;
                font-size:1.1rem;
                color:#1f2937;
              }
              .planes-obj-axes-list{
                display:grid;
                gap:10px;
                max-height:460px;
                overflow:auto;
                padding-right:4px;
              }
              .planes-obj-axis-btn{
                width:100%;
                text-align:left;
                border:1px solid #cfd7e3;
                border-radius:14px;
                background:#f7f9fc;
                color:#334155;
                padding:12px 14px;
                font-weight:600;
                font-style:italic;
                cursor:pointer;
              }
              .planes-obj-axis-btn.active{
                background:#ffffff;
                border-color:#9bb1cc;
                color:#0f172a;
              }
              .planes-obj-main{
                border:1px solid #d2dae4;
                border-radius:16px;
                background:#ffffff;
                padding:14px;
              }
              .planes-obj-head{
                display:flex;
                align-items:center;
                justify-content:space-between;
                gap:10px;
                margin-bottom:10px;
              }
              .planes-obj-title{
                margin:0;
                font-weight:700;
                font-size:1.2rem;
                color:#1f2937;
              }
              .planes-obj-list{
                display:grid;
                gap:12px;
                max-height:460px;
                overflow:auto;
                padding-right:4px;
              }
              .planes-obj-item{
                border:1px solid #cfd7e3;
                border-radius:16px;
                background:#f7faf9;
                padding:14px 16px;
              }
              .planes-obj-item h5{
                margin:0;
                font-size:1.05rem;
                font-weight:800;
                color:#0f172a;
              }
              .planes-obj-code{
                margin-top:6px;
                color:#64748b;
                font-style:italic;
              }
              .planes-obj-meta{
                margin-top:6px;
                color:#64748b;
                font-style:italic;
              }
              @media(max-width:980px){
                .planes-obj-layout{ grid-template-columns:1fr; }
                .planes-obj-axes-list,
                .planes-obj-list{ max-height:none; }
              }
            </style>
            <!-- ── Cuatro áreas de resumen (siempre visibles, sobre las pestañas) ── -->
            <div class="grid gap-5" id="planes-dashboard-areas">

              <!-- Área 1: configuración del plan -->
              <article class="card border rounded-[2rem] shadow-sm" style="background:#eff4f2;border-color:#cfd7df;">
                <div class="card-body p-6">
                  <div class="grid grid-cols-1 lg:grid-cols-2 gap-5">
                    <div class="form-control">
                      <label class="label pb-2">
                        <span class="label-text text-[22px] font-semibold" style="color:#475569;">Vigencia del plan (años):</span>
                      </label>
                      <select id="planes-plan-years" class="select w-full text-[40px] font-medium" style="background:#f8fafc;border-color:#b8c4d3;color:#0f172a;">
                        <option value="1">1</option>
                        <option value="2">2</option>
                        <option value="3" selected>3</option>
                        <option value="4">4</option>
                        <option value="5">5</option>
                      </select>
                    </div>
                    <div class="form-control">
                      <label class="label pb-2">
                        <span class="label-text text-[22px] font-semibold" style="color:#475569;">Inicio del plan:</span>
                      </label>
                      <input id="planes-plan-start" type="date" class="input w-full text-[40px] font-medium" style="background:#f8fafc;border-color:#b8c4d3;color:#0f172a;" value="2026-01-01">
                    </div>
                  </div>
                </div>
              </article>

              <!-- Área 2: tablero KPI -->
              <div class="dash">
                <h2 class="dash__title">Tablero de seguimiento</h2>
                <div class="dash__grid">
                  <div class="kpi">
                    <div class="kpi__label">Avance global</div>
                    <div class="kpi__value" id="planes-kpi-progress">0%</div>
                  </div>
                  <div class="kpi">
                    <div class="kpi__label">Ejes activos</div>
                    <div class="kpi__value" id="planes-kpi-axes">0</div>
                  </div>
                  <div class="kpi">
                    <div class="kpi__label">Objetivos</div>
                    <div class="kpi__value" id="planes-kpi-objectives">0</div>
                  </div>
                  <div class="kpi">
                    <div class="kpi__label">Objetivos al 100%</div>
                    <div class="kpi__value" id="planes-kpi-objectives-done">0</div>
                  </div>
                </div>
                <div class="dash__progress">
                  <div class="dash__progress-bar" id="planes-progress-fill" style="width:0%"></div>
                </div>
                <div class="dash__foot">
                  <span><strong>Misión:</strong> <b id="planes-mission-progress">0%</b></span>
                  <span><strong>Visión:</strong> <b id="planes-vision-progress">0%</b></span>
                </div>
              </div>

              <!-- Área 3: hitos logrados -->
              <div class="milestone-card">
                <div class="milestone-card__inner">
                  <div class="donut" id="planes-milestone-donut" style="--p:0">
                    <div class="donut__center" id="planes-milestone-chart">0%</div>
                  </div>
                  <div class="milestone-info">
                    <div class="milestone-title">Hitos logrados</div>
                    <div class="milestone-stats">
                      <span>Total: <strong id="planes-milestone-total">0</strong></span>
                      <span>Logrados: <strong id="planes-milestone-done">0</strong></span>
                      <span>Pendientes: <strong id="planes-milestone-pending">0</strong></span>
                      <span>Atrasados: <strong class="is-danger" id="planes-milestone-overdue">0</strong></span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Área 4: ejes y objetivos sin responsable -->
              <div class="cards-2">
                <section class="panel">
                  <header class="panel__head">
                    <h3 class="panel__title">Ejes sin responsable</h3>
                    <div class="panel__meta"><strong id="planes-axes-pending-count">0</strong> pendiente(s)</div>
                  </header>
                  <ul class="panel__list" id="planes-axes-pending-list">
                    <li>Sin pendientes</li>
                  </ul>
                  <a class="panel__more" id="planes-axes-pending-more" href="#" aria-label="Más ejes sin responsable"></a>
                </section>
                <section class="panel">
                  <header class="panel__head">
                    <h3 class="panel__title">Objetivos sin responsable</h3>
                    <div class="panel__meta"><strong id="planes-objectives-pending-count">0</strong> pendiente(s)</div>
                  </header>
                  <ul class="panel__list" id="planes-objectives-pending-list">
                    <li>Sin pendientes</li>
                  </ul>
                  <a class="panel__more" id="planes-objectives-pending-more" href="#" aria-label="Más objetivos sin responsable"></a>
                </section>
              </div>

            </div>

            <!-- ── Notebook de pestañas (debajo de las cuatro áreas) ───────────────────────── -->
            <section class="grid gap-5" style="margin-top:1.5rem;">
              <div class="tabs tabs-lifted w-full flex-wrap axm-tabs" role="tablist" aria-label="Planificación estratégica">
                <button type="button" class="tab gap-2 rounded-t-lg axm-tab tab-active active" data-planes-strategic-tab="fundamentacion">
                  <img src="/templates/icon/macroeconomia.svg" alt="" class="tab-icon">Fundamentación
                </button>
                <button type="button" class="tab gap-2 rounded-t-lg axm-tab" data-planes-strategic-tab="identidad">
                  <img src="/templates/icon/identidad.svg" alt="" class="tab-icon">Identidad
                </button>
                <button type="button" class="tab gap-2 rounded-t-lg axm-tab" data-planes-strategic-tab="ejes">
                  <img src="/templates/icon/ejes.svg" alt="" class="tab-icon">Ejes estratégicos
                </button>
                <button type="button" class="tab gap-2 rounded-t-lg axm-tab" data-planes-strategic-tab="objetivos">
                  <img src="/templates/icon/objetivos.svg" alt="" class="tab-icon">Objetivos
                </button>
              </div>
              <section id="planes-tab-panel-fundamentacion" class="axm-foundacion" style="display:block;" data-panel-display="block">
                <h3>Fundamentación</h3>
                <p>Registra aquí la fundamentación del plan estratégico.</p>
                <div class="axm-foundacion-toolbar">
                  <button type="button" class="axm-foundacion-tool" data-planes-found-cmd="bold">Negrita</button>
                  <button type="button" class="axm-foundacion-tool" data-planes-found-cmd="italic">Itálica</button>
                  <button type="button" class="axm-foundacion-tool" data-planes-found-cmd="underline">Subrayar</button>
                  <button type="button" class="axm-foundacion-tool" data-planes-found-cmd="insertUnorderedList">Lista</button>
                  <button type="button" class="axm-foundacion-tool" data-planes-found-cmd="insertOrderedList">Numerada</button>
                  <button type="button" class="axm-foundacion-tool" id="planes-foundacion-upload-btn">Subir HTML</button>
                  <label class="axm-foundacion-tool">
                    <input id="planes-foundacion-show-source" type="checkbox">
                    Ver código HTML
                  </label>
                  <input id="planes-foundacion-upload" type="file" accept=".html,text/html">
                </div>
                <div id="planes-foundacion-editor" class="axm-foundacion-editor" contenteditable="false"></div>
                <textarea id="planes-foundacion-source" class="axm-foundacion-source" placeholder="Código HTML..."></textarea>
                <div class="axm-foundacion-actions">
                  <button type="button" class="action-button" id="planes-foundacion-edit" data-hover-label="Editar" aria-label="Editar" title="Editar">
                    <img src="/icon/boton/editar.svg" alt="Editar">
                    <span class="action-label">Editar</span>
                  </button>
                  <button type="button" class="action-button" id="planes-foundacion-save" data-hover-label="Guardar" aria-label="Guardar" title="Guardar">
                    <img src="/icon/boton/guardar.svg" alt="Guardar">
                    <span class="action-label">Guardar</span>
                  </button>
                </div>
                <div class="axm-foundacion-msg" id="planes-foundacion-msg" aria-live="polite"></div>
              </section>
              <section id="planes-tab-panel-identidad" class="axm-identidad" style="display:none;" data-panel-display="block">
                <details class="axm-id-acc" open>
                  <summary>Misión</summary>
                  <div class="axm-id-grid">
                    <div class="axm-id-left">
                      <textarea id="planes-identidad-mision-text" class="axm-textarea" rows="5" placeholder="Escribe la misión (una línea por elemento)" readonly></textarea>
                      <div class="axm-id-actions">
                        <button type="button" class="action-button" id="planes-identidad-mision-edit" data-hover-label="Editar" aria-label="Editar" title="Editar">
                          <img src="/icon/boton/editar.svg" alt="Editar">
                          <span class="action-label">Editar</span>
                        </button>
                        <button type="button" class="action-button" id="planes-identidad-mision-save" data-hover-label="Guardar" aria-label="Guardar" title="Guardar">
                          <img src="/icon/boton/guardar.svg" alt="Guardar">
                          <span class="action-label">Guardar</span>
                        </button>
                        <button type="button" class="action-button" id="planes-identidad-mision-delete" data-hover-label="Eliminar" aria-label="Eliminar" title="Eliminar">
                          <img src="/icon/boton/eliminar.svg" alt="Eliminar">
                          <span class="action-label">Eliminar</span>
                        </button>
                      </div>
                    </div>
                    <div class="axm-id-right">
                      <h4>Misión</h4>
                      <p class="axm-id-full" id="planes-identidad-mision-full"></p>
                    </div>
                  </div>
                </details>
                <details class="axm-id-acc">
                  <summary>Visión</summary>
                  <div class="axm-id-grid">
                    <div class="axm-id-left">
                      <textarea id="planes-identidad-vision-text" class="axm-textarea" rows="5" placeholder="Escribe la visión (una línea por elemento)" readonly></textarea>
                      <div class="axm-id-actions">
                        <button type="button" class="action-button" id="planes-identidad-vision-edit" data-hover-label="Editar" aria-label="Editar" title="Editar">
                          <img src="/icon/boton/editar.svg" alt="Editar">
                          <span class="action-label">Editar</span>
                        </button>
                        <button type="button" class="action-button" id="planes-identidad-vision-save" data-hover-label="Guardar" aria-label="Guardar" title="Guardar">
                          <img src="/icon/boton/guardar.svg" alt="Guardar">
                          <span class="action-label">Guardar</span>
                        </button>
                        <button type="button" class="action-button" id="planes-identidad-vision-delete" data-hover-label="Eliminar" aria-label="Eliminar" title="Eliminar">
                          <img src="/icon/boton/eliminar.svg" alt="Eliminar">
                          <span class="action-label">Eliminar</span>
                        </button>
                      </div>
                    </div>
                    <div class="axm-id-right">
                      <h4>Visión</h4>
                      <p class="axm-id-full" id="planes-identidad-vision-full"></p>
                    </div>
                  </div>
                </details>
                <div class="axm-id-msg" id="planes-identidad-msg" aria-live="polite"></div>
              </section>
              <section id="planes-tab-panel-ejes" class="card bg-base-100 border border-base-300 rounded-2xl" style="display:none;" data-panel-display="block">
                <div class="card-body">
                  <h3 class="card-title">Ejes estratégicos</h3>
                  <p class="text-base-content/70">Listado de ejes estratégicos registrados en el plan.</p>
                  <div id="planes-ejes-list" class="grid gap-3 mt-2">
                    <div class="text-base-content/60">Cargando ejes...</div>
                  </div>
                  <a href="/ejes-estrategicos" class="btn btn-primary mt-2">Ir al editor de ejes</a>
                </div>
              </section>
              <section id="planes-tab-panel-objetivos" class="card bg-base-100 border border-base-300 rounded-2xl" style="display:none;" data-panel-display="block">
                <div class="card-body">
                  <h3 class="card-title">Objetivos del eje</h3>
                  <div class="planes-obj-layout mt-2">
                    <aside class="planes-obj-axes">
                      <h4 class="planes-obj-side-title">Ejes estratégicos</h4>
                      <div id="planes-objetivos-axes-list" class="planes-obj-axes-list">
                        <div class="text-base-content/60">Cargando ejes...</div>
                      </div>
                    </aside>
                    <section class="planes-obj-main">
                      <div class="planes-obj-head">
                        <h4 id="planes-objetivos-selected-axis-title" class="planes-obj-title">Objetivos: sin eje seleccionado</h4>
                        <div class="view-buttons" style="margin:0;">
                          <button type="button" id="planes-add-objective-btn" class="boton_vista boton_vista-eliptico active">Agregar objetivo</button>
                        </div>
                      </div>
                      <div id="planes-objetivos-list" class="planes-obj-list">
                        <div class="text-base-content/60">Cargando objetivos...</div>
                      </div>
                    </section>
                  </div>
                </div>
              </section>
            </section>
          </div>
          <div class="card-body hidden" id="planes-view-kanban">
            <h2 class="card-title">Vista Kanban</h2>
            <p class="text-base-content/70">Módulo en transición DaisyUI. Esta vista confirma estructura Kanban para Plan estratégico.</p>
          </div>
          <div class="card-body hidden" id="planes-view-organigrama">
            <h2 class="card-title">Vista Organigrama</h2>
            <p class="text-base-content/70">Módulo en transición DaisyUI. Esta vista confirma estructura Organigrama para Plan estratégico.</p>
          </div>
        </article>
      </section>
      <script>
        (function () {
          const buttons = Array.from(document.querySelectorAll('[data-planes-view]'));
          const panels = {
            list: document.getElementById('planes-view-list'),
            kanban: document.getElementById('planes-view-kanban'),
            organigrama: document.getElementById('planes-view-organigrama'),
          };
          function setView(view) {
            const target = ['list', 'kanban', 'organigrama'].includes(view) ? view : 'list';
            Object.keys(panels).forEach((key) => {
              const panel = panels[key];
              if (!panel) return;
              panel.classList.toggle('hidden', key !== target);
            });
            buttons.forEach((btn) => {
              btn.classList.toggle('active', (btn.getAttribute('data-planes-view') || '') === target);
            });
            document.dispatchEvent(new CustomEvent('backend-view-change', { detail: { view: target } }));
          }
          buttons.forEach((btn) => {
            btn.addEventListener('click', () => setView(btn.getAttribute('data-planes-view') || 'list'));
          });

          const planesAddAxisBtn = document.getElementById('planes-add-axis-btn');
          const planesImportBtn = document.getElementById('planes-import-csv-btn');
          const planesImportFile = document.getElementById('planes-import-csv-file');
          const planesImportMsg = document.getElementById('planes-import-csv-msg');
          const setPlanesImportMsg = (text, isError = false) => {
            if (!planesImportMsg) return;
            planesImportMsg.textContent = text || '';
            planesImportMsg.style.color = isError ? '#b91c1c' : '#0f3d2e';
          };
          if (planesAddAxisBtn) {
            planesAddAxisBtn.addEventListener('click', () => {
              setStrategicTab('ejes', true);
              const ejesPanel = document.getElementById('planes-tab-panel-ejes');
              const ejesLink = ejesPanel ? ejesPanel.querySelector('a[href="/ejes-estrategicos"]') : null;
              if (ejesLink) {
                ejesLink.focus();
              }
            });
          }
          if (planesImportBtn && planesImportFile) {
            planesImportBtn.addEventListener('click', () => planesImportFile.click());
            planesImportFile.addEventListener('change', async () => {
              const file = planesImportFile.files && planesImportFile.files[0] ? planesImportFile.files[0] : null;
              if (!file) return;
              const form = new FormData();
              form.append('file', file);
              setPlanesImportMsg('Importando plantilla estratégica y POA...');
              planesImportBtn.disabled = true;
              try {
                const response = await fetch('/api/planificacion/importar-plan-poa', {
                  method: 'POST',
                  body: form,
                  credentials: 'same-origin'
                });
                const data = await response.json().catch(() => ({}));
                if (!response.ok || data?.success === false) {
                  throw new Error(data?.error || data?.detail || 'No se pudo importar el archivo.');
                }
                const axes = Number(data?.inserted_axes || 0);
                const objectives = Number(data?.inserted_objectives || 0);
                const acts = Number(data?.inserted_activities || 0);
                setPlanesImportMsg(`Importación completada: ${axes} ejes, ${objectives} objetivos y ${acts} actividades.`);
                setTimeout(() => window.location.reload(), 550);
              } catch (error) {
                setPlanesImportMsg(error?.message || 'No se pudo importar el archivo.', true);
              } finally {
                planesImportBtn.disabled = false;
                planesImportFile.value = '';
              }
            });
          }

          const strategicTabButtons = Array.from(document.querySelectorAll('[data-planes-strategic-tab]'));
          const strategicTabPanels = {
            fundamentacion: document.getElementById('planes-tab-panel-fundamentacion'),
            identidad: document.getElementById('planes-tab-panel-identidad'),
            ejes: document.getElementById('planes-tab-panel-ejes'),
            objetivos: document.getElementById('planes-tab-panel-objetivos'),
          };
          const setStrategicTab = (tab, shouldScroll = false) => {
            const target = ['fundamentacion', 'identidad', 'ejes', 'objetivos'].includes(tab) ? tab : 'ejes';
            Object.keys(strategicTabPanels).forEach((key) => {
              const panel = strategicTabPanels[key];
              if (!panel) return;
              const isActive = key === target;
              const panelDisplay = panel.getAttribute('data-panel-display') || 'block';
              panel.classList.toggle('hidden', !isActive);
              panel.style.display = isActive ? panelDisplay : 'none';
            });
            strategicTabButtons.forEach((btn) => {
              const on = (btn.getAttribute('data-planes-strategic-tab') || '') === target;
              btn.classList.toggle('active', on);
              btn.classList.toggle('tab-active', on);
            });
            if (shouldScroll) {
              const targetPanel = strategicTabPanels[target];
              if (targetPanel && typeof targetPanel.scrollIntoView === 'function') {
                targetPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }
            }
          };
          strategicTabButtons.forEach((btn) => {
            btn.addEventListener('click', () => setStrategicTab(btn.getAttribute('data-planes-strategic-tab') || 'ejes', true));
          });

          const foundationPanelEl = document.getElementById('planes-tab-panel-fundamentacion');
          const foundationEditorEl = document.getElementById('planes-foundacion-editor');
          const foundationSourceEl = document.getElementById('planes-foundacion-source');
          const foundationUploadBtn = document.getElementById('planes-foundacion-upload-btn');
          const foundationUploadEl = document.getElementById('planes-foundacion-upload');
          const foundationShowSourceEl = document.getElementById('planes-foundacion-show-source');
          const foundationEditBtn = document.getElementById('planes-foundacion-edit');
          const foundationSaveBtn = document.getElementById('planes-foundacion-save');
          const foundationMsgEl = document.getElementById('planes-foundacion-msg');
          const setFoundationMsg = (text, isError = false) => {
            if (!foundationMsgEl) return;
            foundationMsgEl.textContent = text || '';
            foundationMsgEl.style.color = isError ? '#b91c1c' : '#0f3d2e';
          };
          const getFoundationHtml = () => {
            if (foundationShowSourceEl && foundationShowSourceEl.checked && foundationSourceEl) {
              return String(foundationSourceEl.value || '');
            }
            return foundationEditorEl ? String(foundationEditorEl.innerHTML || '') : '';
          };
          const setFoundationHtml = (rawHtml) => {
            const raw = String(rawHtml || '');
            if (foundationEditorEl) foundationEditorEl.innerHTML = raw;
            if (foundationSourceEl) foundationSourceEl.value = raw;
          };
          const syncFoundationSourceMode = () => {
            const show = !!(foundationShowSourceEl && foundationShowSourceEl.checked);
            if (show) {
              if (foundationSourceEl) foundationSourceEl.value = foundationEditorEl ? foundationEditorEl.innerHTML : '';
            } else if (foundationEditorEl && foundationSourceEl) {
              foundationEditorEl.innerHTML = foundationSourceEl.value || '';
            }
            if (foundationSourceEl) foundationSourceEl.style.display = show ? 'block' : 'none';
            if (foundationEditorEl) foundationEditorEl.style.display = show ? 'none' : 'block';
          };
          const setFoundationEditable = (enabled) => {
            if (foundationEditorEl) foundationEditorEl.setAttribute('contenteditable', enabled ? 'true' : 'false');
            if (foundationSourceEl) foundationSourceEl.readOnly = !enabled;
          };
          const loadFoundationFromDb = async () => {
            const response = await fetch('/api/strategic-foundation', { method: 'GET', credentials: 'same-origin' });
            const data = await response.json().catch(() => ({}));
            if (!response.ok || data?.success === false) {
              throw new Error(data?.error || data?.detail || 'No se pudo cargar Fundamentación.');
            }
            setFoundationHtml(String(data?.data?.texto || ''));
            syncFoundationSourceMode();
          };
          const saveFoundationToDb = async () => {
            const response = await fetch('/api/strategic-foundation', {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'same-origin',
              body: JSON.stringify({ texto: getFoundationHtml() }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok || data?.success === false) {
              throw new Error(data?.error || data?.detail || 'No se pudo guardar Fundamentación.');
            }
          };
          if (foundationPanelEl) {
            setFoundationEditable(false);
            syncFoundationSourceMode();
            foundationShowSourceEl && foundationShowSourceEl.addEventListener('change', syncFoundationSourceMode);
            foundationUploadBtn && foundationUploadBtn.addEventListener('click', () => {
              if (foundationUploadEl) foundationUploadEl.click();
            });
            foundationUploadEl && foundationUploadEl.addEventListener('change', async () => {
              const file = foundationUploadEl.files && foundationUploadEl.files[0] ? foundationUploadEl.files[0] : null;
              if (!file) return;
              const text = await file.text().catch(() => '');
              if (!text) {
                setFoundationMsg('No se pudo leer el archivo HTML.', true);
                return;
              }
              setFoundationHtml(text);
              syncFoundationSourceMode();
              setFoundationMsg('HTML cargado correctamente.');
            });
            foundationEditBtn && foundationEditBtn.addEventListener('click', () => {
              setFoundationEditable(true);
              setFoundationMsg('Modo edición habilitado.');
              if (foundationEditorEl && foundationEditorEl.style.display !== 'none') foundationEditorEl.focus();
            });
            foundationSaveBtn && foundationSaveBtn.addEventListener('click', async () => {
              try {
                if (foundationShowSourceEl && foundationShowSourceEl.checked && foundationEditorEl && foundationSourceEl) {
                  foundationEditorEl.innerHTML = foundationSourceEl.value || '';
                }
                await saveFoundationToDb();
                setFoundationEditable(false);
                setFoundationMsg('Fundamentación guardada.');
              } catch (error) {
                setFoundationMsg(error?.message || 'No se pudo guardar Fundamentación.', true);
              }
            });
            document.querySelectorAll('[data-planes-found-cmd]').forEach((btn) => {
              btn.addEventListener('click', () => {
                const cmd = btn.getAttribute('data-planes-found-cmd') || '';
                if (!cmd || !foundationEditorEl) return;
                foundationEditorEl.focus();
                try {
                  document.execCommand(cmd, false, null);
                } catch (_err) {}
              });
            });
            loadFoundationFromDb().catch((error) => {
              setFoundationMsg(error?.message || 'No se pudo cargar Fundamentación.', true);
            });
          }

          const identityPanelEl = document.getElementById('planes-tab-panel-identidad');
          const identityMsgEl = document.getElementById('planes-identidad-msg');
          const missionTextEl = document.getElementById('planes-identidad-mision-text');
          const missionFullEl = document.getElementById('planes-identidad-mision-full');
          const missionEditBtn = document.getElementById('planes-identidad-mision-edit');
          const missionSaveBtn = document.getElementById('planes-identidad-mision-save');
          const missionDeleteBtn = document.getElementById('planes-identidad-mision-delete');
          const visionTextEl = document.getElementById('planes-identidad-vision-text');
          const visionFullEl = document.getElementById('planes-identidad-vision-full');
          const visionEditBtn = document.getElementById('planes-identidad-vision-edit');
          const visionSaveBtn = document.getElementById('planes-identidad-vision-save');
          const visionDeleteBtn = document.getElementById('planes-identidad-vision-delete');
          const setIdentityMsg = (text, isError = false) => {
            if (!identityMsgEl) return;
            identityMsgEl.textContent = text || '';
            identityMsgEl.style.color = isError ? '#b91c1c' : '#0f3d2e';
          };
          const normalizeLineText = (line) => {
            if (line == null) return '';
            if (typeof line === 'string') return line.trim();
            if (typeof line === 'object') {
              const code = String(line.code || '').trim();
              const text = String(line.text || '').trim();
              if (code && text) return `${code} - ${text}`;
              return text || code;
            }
            return String(line).trim();
          };
          const linesToTextarea = (lines) => (Array.isArray(lines) ? lines.map(normalizeLineText).filter(Boolean).join('\\n') : '');
          const textareaToLines = (rawValue, prefix) => {
            const chunks = String(rawValue || '').split('\\n').map((item) => item.trim()).filter(Boolean);
            return chunks.map((row, idx) => {
              const dashPos = row.indexOf(' - ');
              if (dashPos > 0) {
                const codeRaw = row.slice(0, dashPos).trim();
                const textRaw = row.slice(dashPos + 3).trim();
                return { code: codeRaw || `${prefix}-${String(idx + 1).padStart(2, '0')}`, text: textRaw || row };
              }
              return { code: `${prefix}-${String(idx + 1).padStart(2, '0')}`, text: row };
            });
          };
          const updateIdentityPreview = () => {
            if (missionFullEl && missionTextEl) missionFullEl.textContent = missionTextEl.value.split('\\n').map((s) => s.trim()).filter(Boolean).join(' | ');
            if (visionFullEl && visionTextEl) visionFullEl.textContent = visionTextEl.value.split('\\n').map((s) => s.trim()).filter(Boolean).join(' | ');
          };
          const setIdentityEditable = (textareaEl, enabled) => {
            if (!textareaEl) return;
            textareaEl.readOnly = !enabled;
            if (enabled) textareaEl.focus();
          };
          const loadIdentityForPlanes = async () => {
            const response = await fetch('/api/strategic-identity', { method: 'GET', credentials: 'same-origin' });
            const data = await response.json().catch(() => ({}));
            if (!response.ok || data?.success === false) {
              throw new Error(data?.error || data?.detail || 'No se pudo cargar Identidad.');
            }
            if (missionTextEl) missionTextEl.value = linesToTextarea(data?.data?.mision);
            if (visionTextEl) visionTextEl.value = linesToTextarea(data?.data?.vision);
            updateIdentityPreview();
          };
          const saveIdentityBlock = async (block, lines) => {
            const response = await fetch(`/api/strategic-identity/${encodeURIComponent(block)}`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'same-origin',
              body: JSON.stringify({ lineas: lines }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok || data?.success === false) {
              throw new Error(data?.error || data?.detail || 'No se pudo guardar Identidad.');
            }
          };
          const clearIdentityBlock = async (block) => {
            const response = await fetch(`/api/strategic-identity/${encodeURIComponent(block)}`, {
              method: 'DELETE',
              credentials: 'same-origin',
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok || data?.success === false) {
              throw new Error(data?.error || data?.detail || 'No se pudo limpiar Identidad.');
            }
          };
          if (identityPanelEl) {
            setIdentityEditable(missionTextEl, false);
            setIdentityEditable(visionTextEl, false);
            missionTextEl && missionTextEl.addEventListener('input', updateIdentityPreview);
            visionTextEl && visionTextEl.addEventListener('input', updateIdentityPreview);
            missionEditBtn && missionEditBtn.addEventListener('click', () => {
              setIdentityEditable(missionTextEl, true);
              setIdentityMsg('Modo edición habilitado para Misión.');
            });
            missionSaveBtn && missionSaveBtn.addEventListener('click', async () => {
              try {
                const lines = textareaToLines(missionTextEl ? missionTextEl.value : '', 'm');
                await saveIdentityBlock('mision', lines);
                setIdentityEditable(missionTextEl, false);
                updateIdentityPreview();
                setIdentityMsg('Misión guardada.');
              } catch (error) {
                setIdentityMsg(error?.message || 'No se pudo guardar Misión.', true);
              }
            });
            missionDeleteBtn && missionDeleteBtn.addEventListener('click', async () => {
              try {
                await clearIdentityBlock('mision');
                if (missionTextEl) missionTextEl.value = '';
                setIdentityEditable(missionTextEl, false);
                updateIdentityPreview();
                setIdentityMsg('Misión limpiada.');
              } catch (error) {
                setIdentityMsg(error?.message || 'No se pudo limpiar Misión.', true);
              }
            });
            visionEditBtn && visionEditBtn.addEventListener('click', () => {
              setIdentityEditable(visionTextEl, true);
              setIdentityMsg('Modo edición habilitado para Visión.');
            });
            visionSaveBtn && visionSaveBtn.addEventListener('click', async () => {
              try {
                const lines = textareaToLines(visionTextEl ? visionTextEl.value : '', 'v');
                await saveIdentityBlock('vision', lines);
                setIdentityEditable(visionTextEl, false);
                updateIdentityPreview();
                setIdentityMsg('Visión guardada.');
              } catch (error) {
                setIdentityMsg(error?.message || 'No se pudo guardar Visión.', true);
              }
            });
            visionDeleteBtn && visionDeleteBtn.addEventListener('click', async () => {
              try {
                await clearIdentityBlock('vision');
                if (visionTextEl) visionTextEl.value = '';
                setIdentityEditable(visionTextEl, false);
                updateIdentityPreview();
                setIdentityMsg('Visión limpiada.');
              } catch (error) {
                setIdentityMsg(error?.message || 'No se pudo limpiar Visión.', true);
              }
            });
            loadIdentityForPlanes().catch((error) => {
              setIdentityMsg(error?.message || 'No se pudo cargar Identidad.', true);
            });
          }

          const escapeHtml = (value) => String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');

          const fillList = (listEl, moreEl, items, mapper) => {
            if (!listEl || !moreEl) return;
            if (!Array.isArray(items) || !items.length) {
              listEl.innerHTML = '<li>Sin pendientes</li>';
              moreEl.textContent = '';
              moreEl.style.display = 'none';
              return;
            }
            const visible = items.slice(0, 8);
            listEl.innerHTML = visible.map((item) => `<li>${mapper(item)}</li>`).join('');
            const extra = items.length - visible.length;
            moreEl.textContent = extra > 0 ? `+${extra} más` : '';
            moreEl.style.display = extra > 0 ? 'inline-block' : 'none';
          };

          const renderPlanesTrackingBoard = (axes) => {
            const axisList = Array.isArray(axes) ? axes : [];
            const objectives = axisList.flatMap((axis) => Array.isArray(axis.objetivos) ? axis.objetivos : []);
            const objectiveAxisById = {};
            axisList.forEach((axis) => {
              (Array.isArray(axis.objetivos) ? axis.objetivos : []).forEach((obj) => {
                objectiveAxisById[String(obj.id)] = axis;
              });
            });

            const axisCount = axisList.length;
            const objectiveCount = objectives.length;
            const globalProgress = axisCount
              ? Math.round(axisList.reduce((sum, axis) => sum + Number(axis.avance || 0), 0) / axisCount)
              : 0;
            const objectiveDone = objectives.filter((obj) => Number(obj.avance || 0) >= 100).length;

            const axesNoOwner = axisList.filter((axis) => !String(axis?.responsabilidad_directa || '').trim());
            const objectivesNoOwner = objectives.filter((obj) => !String(obj?.lider || '').trim());

            const missionAxes = axisList.filter((axis) => String(axis.base_code || axis.codigo || '').toLowerCase().startsWith('m'));
            const visionAxes = axisList.filter((axis) => String(axis.base_code || axis.codigo || '').toLowerCase().startsWith('v'));
            const missionProgress = missionAxes.length
              ? Math.round(missionAxes.reduce((sum, axis) => sum + Number(axis.avance || 0), 0) / missionAxes.length)
              : 0;
            const visionProgress = visionAxes.length
              ? Math.round(visionAxes.reduce((sum, axis) => sum + Number(axis.avance || 0), 0) / visionAxes.length)
              : 0;

            const milestones = objectives.flatMap((obj) => {
              if (Array.isArray(obj.hitos) && obj.hitos.length) return obj.hitos;
              return obj.hito ? [{ nombre: obj.hito, logrado: false, fecha_realizacion: '' }] : [];
            });
            const milestonesTotal = milestones.length;
            const milestonesDone = milestones.filter((item) => !!item.logrado).length;
            const milestonesPending = Math.max(0, milestonesTotal - milestonesDone);
            const todayIso = new Date().toISOString().slice(0, 10);
            const milestonesOverdue = milestones.filter((item) => {
              const due = String(item?.fecha_realizacion || '');
              return !item?.logrado && !!due && due < todayIso;
            }).length;
            const milestonesPct = milestonesTotal ? Math.round((milestonesDone * 100) / milestonesTotal) : 0;

            const byId = (id) => document.getElementById(id);
            const setText = (id, value) => { const el = byId(id); if (el) el.textContent = String(value); };

            setText('planes-kpi-progress', `${globalProgress}%`);
            setText('planes-kpi-axes', axisCount);
            setText('planes-kpi-objectives', objectiveCount);
            setText('planes-kpi-objectives-done', objectiveDone);
            setText('planes-mission-progress', `${missionProgress}%`);
            setText('planes-vision-progress', `${visionProgress}%`);
            setText('planes-milestone-total', milestonesTotal);
            setText('planes-milestone-done', milestonesDone);
            setText('planes-milestone-pending', milestonesPending);
            setText('planes-milestone-overdue', milestonesOverdue);
            setText('planes-axes-pending-count', axesNoOwner.length);
            setText('planes-objectives-pending-count', objectivesNoOwner.length);

            const progressFill = byId('planes-progress-fill');
            if (progressFill) progressFill.style.width = `${Math.max(0, Math.min(100, Number(globalProgress) || 0))}%`;
            const milestoneChart = byId('planes-milestone-chart');
            if (milestoneChart) milestoneChart.textContent = `${milestonesPct}%`;
            const milestoneDonut = byId('planes-milestone-donut');
            if (milestoneDonut) milestoneDonut.style.setProperty('--p', String(Math.max(0, Math.min(100, Number(milestonesPct) || 0))));

            fillList(
              byId('planes-axes-pending-list'),
              byId('planes-axes-pending-more'),
              axesNoOwner,
              (axis) => `${escapeHtml(axis.codigo || 'Sin código')} - ${escapeHtml(axis.nombre || 'Sin nombre')}`
            );
            fillList(
              byId('planes-objectives-pending-list'),
              byId('planes-objectives-pending-more'),
              objectivesNoOwner,
              (obj) => {
                const parentAxis = objectiveAxisById[String(obj.id)] || {};
                const axisCode = String(parentAxis.codigo || '').trim();
                const code = String(obj.codigo || '').trim();
                const left = code || axisCode || 'Sin código';
                return `${escapeHtml(left)} - ${escapeHtml(obj.nombre || 'Sin nombre')}`;
              }
            );
          };

          const renderStrategicAxesPanel = (axes) => {
            const host = document.getElementById('planes-ejes-list');
            if (!host) return;
            const axisList = Array.isArray(axes) ? axes : [];
            if (!axisList.length) {
              host.innerHTML = '<div class="text-base-content/60">Sin ejes registrados.</div>';
              return;
            }
            host.innerHTML = axisList.map((axis) => {
              const code = escapeHtml(axis?.codigo || 'Sin código');
              const name = escapeHtml(axis?.nombre || 'Sin nombre');
              const owner = escapeHtml(axis?.responsabilidad_directa || 'Sin responsable');
              const progress = Math.max(0, Math.min(100, Number(axis?.avance || 0)));
              const objectivesCount = Number(axis?.objetivos_count || (Array.isArray(axis?.objetivos) ? axis.objetivos.length : 0)) || 0;
              return `
                <article class="card bg-base-200 border border-base-300 rounded-xl">
                  <div class="card-body p-4">
                    <div class="flex flex-wrap items-start justify-between gap-2">
                      <h4 class="font-semibold text-base-content">${code} - ${name}</h4>
                      <span class="badge badge-outline">${progress}%</span>
                    </div>
                    <div class="text-sm text-base-content/70">Responsable: ${owner}</div>
                    <div class="text-sm text-base-content/70">Objetivos: ${objectivesCount}</div>
                  </div>
                </article>
              `;
            }).join('');
          };

          const renderStrategicObjectivesPanel = (axes) => {
            const axesHost = document.getElementById('planes-objetivos-axes-list');
            const host = document.getElementById('planes-objetivos-list');
            const titleEl = document.getElementById('planes-objetivos-selected-axis-title');
            const addBtn = document.getElementById('planes-add-objective-btn');
            if (!host || !axesHost) return;
            const axisList = Array.isArray(axes) ? axes : [];
            if (addBtn) {
              addBtn.onclick = () => {
                const selected = axisList.find((axis) => String(axis?.id || '') === String(window.__planesSelectedAxisId || '')) || axisList[0] || null;
                const axisId = selected && selected.id != null ? String(selected.id) : '';
                const qs = new URLSearchParams();
                qs.set('tab', 'objetivos');
                qs.set('open', 'objective');
                if (axisId) qs.set('axis_id', axisId);
                window.location.href = `/ejes-estrategicos?${qs.toString()}`;
              };
            }
            if (!axisList.length) {
              axesHost.innerHTML = '<div class="text-base-content/60">Sin ejes registrados.</div>';
              if (titleEl) titleEl.textContent = 'Objetivos: sin eje seleccionado';
              host.innerHTML = '<div class="text-base-content/60">Sin objetivos registrados.</div>';
              return;
            }
            let selectedAxisId = window.__planesSelectedAxisId || null;
            if (!selectedAxisId || !axisList.some((axis) => String(axis?.id || '') === String(selectedAxisId))) {
              selectedAxisId = axisList[0]?.id || null;
              window.__planesSelectedAxisId = selectedAxisId;
            }

            axesHost.innerHTML = axisList.map((axis) => {
              const axisId = String(axis?.id || '');
              const on = String(selectedAxisId) === axisId;
              const axisCode = escapeHtml(axis?.codigo || 'Sin código');
              const axisName = escapeHtml(axis?.nombre || 'Sin nombre');
              return `<button type="button" class="planes-obj-axis-btn ${on ? 'active' : ''}" data-planes-axis-id="${axisId}">${axisCode}: ${axisName}</button>`;
            }).join('');
            axesHost.querySelectorAll('[data-planes-axis-id]').forEach((btn) => {
              btn.addEventListener('click', () => {
                window.__planesSelectedAxisId = btn.getAttribute('data-planes-axis-id') || null;
                renderStrategicObjectivesPanel(axisList);
              });
            });

            const selectedAxis = axisList.find((axis) => String(axis?.id || '') === String(selectedAxisId)) || axisList[0];
            const selectedAxisCode = escapeHtml(selectedAxis?.codigo || 'Sin código');
            const selectedAxisName = escapeHtml(selectedAxis?.nombre || 'Sin nombre');
            if (titleEl) titleEl.textContent = `Objetivos: ${selectedAxisCode}: ${selectedAxisName}`;

            const objectives = Array.isArray(selectedAxis?.objetivos) ? selectedAxis.objetivos : [];
            if (!objectives.length) {
              host.innerHTML = '<div class="text-base-content/60">Este eje no tiene objetivos registrados.</div>';
              return;
            }
            host.innerHTML = objectives.map((obj) => {
              const name = escapeHtml(obj?.nombre || 'Sin nombre');
              const code = escapeHtml(obj?.codigo || 'Sin código');
              const hito = escapeHtml(obj?.hito || 'N/D');
              const avance = Math.max(0, Math.min(100, Number(obj?.avance || 0)));
              const fechaInicio = escapeHtml(obj?.fecha_inicio || obj?.inicio || 'N/D');
              const fechaFin = escapeHtml(obj?.fecha_fin || obj?.fin || 'N/D');
              return `
                <article class="planes-obj-item">
                  <h5>${name}</h5>
                  <div class="planes-obj-code">${code}</div>
                  <div class="planes-obj-meta">Hito: ${hito} · Avance: ${avance}% · Fecha inicial: ${fechaInicio} · Fecha final: ${fechaFin}</div>
                </article>
              `;
            }).join('');
          };

          const loadTracking = async () => {
            try {
              const response = await fetch('/api/strategic-axes', {
                method: 'GET',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
              });
              const payload = await response.json();
              const axes = (payload && payload.success && Array.isArray(payload.data)) ? payload.data : [];
              renderPlanesTrackingBoard(axes);
              renderStrategicAxesPanel(axes);
              renderStrategicObjectivesPanel(axes);
            } catch (_err) {
              renderPlanesTrackingBoard([]);
              renderStrategicAxesPanel([]);
              renderStrategicObjectivesPanel([]);
            }
          };

          ['planes-axes-pending-more', 'planes-objectives-pending-more'].forEach((id) => {
            const el = document.getElementById(id);
            if (!el) return;
            el.addEventListener('click', (event) => event.preventDefault());
          });

          loadTracking();
          setStrategicTab('fundamentacion');
          setView('list');
        })();
      </script>
    """)
    return render_backend_page(
        request,
        title="Plan estratégico",
        description="Edición y administración del plan estratégico de la institución",
        content=base_content,
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/poa", response_class=HTMLResponse)
@router.get("/poa/crear", response_class=HTMLResponse)
def poa_page(request: Request):
    _bind_core_symbols()
    base_content = dedent("""
      <section class="grid gap-4 w-full max-w-6xl">
        <div class="titulo bg-base-200 rounded-box border border-base-300 p-4 sm:p-6">
          <div class="w-full flex flex-col md:flex-row items-center gap-10">
            <img
              src="/templates/icon/plan.svg"
              alt="Icono POA"
              width="96"
              height="96"
              class="shrink-0 rounded-box border border-base-300 bg-base-100 p-3 object-contain"
            />
            <div class="w-full grid gap-2 content-center">
              <div class="block w-full text-3xl sm:text-4xl lg:text-5xl font-bold leading-tight text-[color:var(--sidebar-bottom)]">POA</div>
              <div class="block w-full text-base sm:text-lg text-base-content/70">El Plan Operativo Anual organiza actividades, responsables y tiempos de ejecución.</div>
            </div>
          </div>
        </div>
        <div class="view-buttons page-view-buttons" id="poa-view-switch">
          <button class="view-pill boton_vista active" type="button" data-poa-view="list" data-tooltip="Lista" aria-label="Lista">
            <span class="boton_vista-icono view-pill-icon-mask" aria-hidden="true" style="--view-pill-icon-url:url('/icon/boton/grid.svg')"></span>
            <span class="view-pill-label boton_vista-label">List</span>
          </button>
          <button class="view-pill boton_vista" type="button" data-poa-view="kanban" data-tooltip="Kanban" aria-label="Kanban">
            <span class="boton_vista-icono view-pill-icon-mask" aria-hidden="true" style="--view-pill-icon-url:url('/icon/boton/kanban.svg')"></span>
            <span class="view-pill-label boton_vista-label">Kanban</span>
          </button>
          <button class="view-pill boton_vista" type="button" data-poa-view="organigrama" data-tooltip="Organigrama" aria-label="Organigrama">
            <span class="boton_vista-icono view-pill-icon-mask" aria-hidden="true" style="--view-pill-icon-url:url('/icon/boton/organigrama.svg')"></span>
            <span class="view-pill-label boton_vista-label">Organigrama</span>
          </button>
        </div>
        <article class="card border border-base-300 shadow-sm rounded-[2rem]" style="background:#eff4f2;">
          <div class="card-body p-6 sm:p-8">
            <h2 class="text-3xl sm:text-4xl font-semibold text-base-content">Tablero POA por eje</h2>
            <p class="text-lg sm:text-2xl text-base-content/70">Cada columna corresponde a un eje y contiene las tarjetas de sus objetivos.</p>
            <div class="flex flex-wrap gap-3 pt-2">
              <a href="/api/planificacion/plantilla-plan-poa.csv" class="btn btn-lg bg-base-100 border border-base-300 text-base-content hover:bg-base-200 normal-case">Descargar plantilla CSV</a>
              <a href="/api/planificacion/exportar-plan-poa.xlsx" class="btn btn-lg bg-base-100 border border-base-300 text-base-content hover:bg-base-200 normal-case">Exportar plan + POA XLS</a>
              <button type="button" id="poa-import-csv-btn" class="btn btn-lg bg-base-100 border border-base-300 text-base-content hover:bg-base-200 normal-case">Importar CSV estratégico + POA</button>
              <input id="poa-import-csv-file" type="file" accept=".csv,text/csv" class="hidden">
            </div>
            <div id="poa-import-csv-msg" class="text-sm sm:text-base pt-1 min-h-[1.5rem] text-base-content/70"></div>
          </div>
        </article>
        <article class="card border border-base-300 shadow-sm rounded-[2rem]" style="background:#eff4f2;">
          <div class="card-body p-6 sm:p-8">
            <div class="poa-small-muted">Permisos: edicion · acceso todas_tareas · rol administrador</div>

            <div class="cards-2 mb-4">
              <section class="panel card bg-base-100 border border-base-300 rounded-2xl shadow-sm">
                <header class="panel__head">
                  <h3 class="panel__title">Actividades sin responsable</h3>
                  <div class="panel__meta"><strong>149</strong> pendiente(s)</div>
                </header>
                <ul class="panel__list">
                  <li>Diseño del Plan Integral de Crecimiento Social 2026</li>
                  <li>Implementación de Campaña Institucional de Captación Territorial</li>
                  <li>Profesionalización y Fortalecimiento del Equipo Comercial</li>
                  <li>Implementación de Sistema de Seguimiento Comercial (CRM o Control Mensual)</li>
                  <li>Estrategia Digital Complementaria de Afiliación</li>
                  <li>Implementación de Programa de Incentivos por Captación</li>
                  <li>Diseño y estructuración del Producto Financiero Juvenil</li>
                  <li>Diseño del Programa de Educación Financiera Juvenil</li>
                </ul>
                <a href="#" class="panel__more">+141 más</a>
              </section>
              <section class="panel card bg-base-100 border border-base-300 rounded-2xl shadow-sm">
                <header class="panel__head">
                  <h3 class="panel__title">Subtareas sin responsable</h3>
                  <div class="panel__meta"><strong>18</strong> pendiente(s)</div>
                </header>
                <ul class="panel__list">
                  <li>Análisis de Crecimiento histórico. <span class="text-base-content/60">(Diseño del Plan Integral de Crecimiento Social 2026)</span></li>
                  <li>Análisis de Penetración territorial <span class="text-base-content/60">(Diseño del Plan Integral de Crecimiento Social 2026)</span></li>
                  <li>Análisis de Competencia (fintech, sofipos, crédito comercial). <span class="text-base-content/60">(Diseño del Plan Integral de Crecimiento Social 2026)</span></li>
                  <li>Análisis de Segmentación demográfica. <span class="text-base-content/60">(Diseño del Plan Integral de Crecimiento Social 2026)</span></li>
                  <li>Establecer Calendario mensual de activaciones. <span class="text-base-content/60">(Implementación de Campaña Institucional de Captación Territorial)</span></li>
                  <li>Establecer programa Presencia en ferias, tianguis y eventos locales. <span class="text-base-content/60">(Implementación de Campaña Institucional de Captación Territorial)</span></li>
                  <li>Documentar Jornadas de afiliación simplificada. <span class="text-base-content/60">(Implementación de Campaña Institucional de Captación Territorial)</span></li>
                  <li>Programa de Taller intensivo de captación. <span class="text-base-content/60">(Profesionalización y Fortalecimiento del Equipo Comercial)</span></li>
                </ul>
                <a href="#" class="panel__more">+10 más</a>
              </section>
            </div>

            <section class="panel card bg-base-100 border border-base-300 rounded-2xl shadow-sm">
              <div class="poa-summary">
                <div>
                  <h4>Concentración de actividades por usuario</h4>
                  <p>Distribución de actividades POA asignadas por responsable.</p>
                </div>
                <div class="poa-summary-total">Total asignadas: 1</div>
              </div>
            </section>
          </div>
        </article>
        <article class="card border border-base-300 shadow-sm rounded-[2rem]" style="background:#eff4f2;">
          <div class="card-body p-6 sm:p-8">
            <div class="poa-summary mb-3">
              <div>
                <h4 class="!text-3xl">Concentración de actividades por usuario</h4>
                <p>Distribución de actividades POA asignadas por responsable.</p>
              </div>
              <div class="poa-summary-total" id="poa-user-total">Total asignadas: 0</div>
            </div>
            <div id="poa-user-bars" class="grid gap-3"></div>
            <div class="cards-2 mt-5" id="poa-axis-columns"></div>
          </div>
        </article>
      </section>
      <dialog id="poa-objective-modal" class="modal">
        <div class="modal-box w-11/12 max-w-6xl rounded-3xl">
          <form method="dialog">
            <button class="btn btn-sm btn-circle btn-ghost absolute right-4 top-4" aria-label="Cerrar">✕</button>
          </form>
          <h3 class="font-bold text-3xl" id="poa-modal-title">Actividades del objetivo</h3>
          <p class="text-lg text-base-content/70 mt-1 mb-3" id="poa-modal-subtitle"></p>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
            <div class="card bg-base-100 border border-base-300 rounded-2xl p-4">
              <div class="panel__title !text-base !tracking-normal">Estatus</div>
              <div id="poa-modal-status" class="text-2xl font-semibold">No iniciado</div>
            </div>
            <div class="card bg-base-100 border border-base-300 rounded-2xl p-4">
              <div class="panel__title !text-base !tracking-normal">Avance</div>
              <div id="poa-modal-progress" class="text-2xl font-semibold">0%</div>
            </div>
          </div>
          <div class="card bg-base-100 border border-base-300 rounded-2xl p-4">
            <div class="panel__title !text-2xl !tracking-normal !mb-2">Actividades del objetivo</div>
            <div id="poa-modal-activities" class="grid gap-2 max-h-[60vh] overflow-auto"></div>
          </div>
        </div>
        <form method="dialog" class="modal-backdrop">
          <button>Cerrar</button>
        </form>
      </dialog>
      <script>
        (function () {
          const importBtn = document.getElementById('poa-import-csv-btn');
          const fileInput = document.getElementById('poa-import-csv-file');
          const msgEl = document.getElementById('poa-import-csv-msg');
          const axisColumnsEl = document.getElementById('poa-axis-columns');
          const userBarsEl = document.getElementById('poa-user-bars');
          const userTotalEl = document.getElementById('poa-user-total');
          const objectiveModal = document.getElementById('poa-objective-modal');
          const modalTitleEl = document.getElementById('poa-modal-title');
          const modalSubtitleEl = document.getElementById('poa-modal-subtitle');
          const modalStatusEl = document.getElementById('poa-modal-status');
          const modalProgressEl = document.getElementById('poa-modal-progress');
          const modalActivitiesEl = document.getElementById('poa-modal-activities');
          const setMsg = (text, isError) => {
            if (!msgEl) return;
            msgEl.textContent = text || '';
            msgEl.style.color = isError ? '#b91c1c' : '#0f3d2e';
          };
          if (!importBtn || !fileInput) return;
          importBtn.addEventListener('click', () => fileInput.click());
          fileInput.addEventListener('change', async () => {
            const file = fileInput.files && fileInput.files[0] ? fileInput.files[0] : null;
            if (!file) return;
            try {
              setMsg('Importando archivo...', false);
              const formData = new FormData();
              formData.append('file', file);
              const response = await fetch('/api/planificacion/importar-plan-poa', {
                method: 'POST',
                body: formData,
                credentials: 'same-origin',
              });
              const data = await response.json().catch(() => ({}));
              if (!response.ok || data?.success === false) {
                throw new Error(data?.error || data?.detail || 'No se pudo importar el archivo.');
              }
              setMsg('Importación completada correctamente.', false);
            } catch (error) {
              setMsg(error?.message || 'No se pudo importar el archivo.', true);
            } finally {
              fileInput.value = '';
            }
          });

          const esc = (v) => String(v == null ? '' : v)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
          const statusRank = (s) => {
            const key = String(s || '').toLowerCase();
            if (key.includes('revision')) return 4;
            if (key.includes('termin')) return 3;
            if (key.includes('proceso')) return 2;
            return 1;
          };
          const buildSubTree = (subs, parentId, depth) => {
            const list = (subs || []).filter((s) => Number(s.parent_subactivity_id || 0) === Number(parentId || 0));
            if (!list.length) return '';
            const items = list.map((s) => {
              const margin = Math.min(10, depth * 14);
              return `
                <li style="margin-left:${margin}px">
                  <span class="text-base-content/70">Nivel ${Number(s.nivel || 1)}:</span>
                  ${esc(s.nombre || 'Subtarea sin nombre')}
                  ${buildSubTree(subs, s.id, depth + 1)}
                </li>
              `;
            }).join('');
            return `<ul class="list-disc pl-6 text-base-content/80 text-sm mt-1">${items}</ul>`;
          };
          const openObjectiveModal = (objective, activities) => {
            if (!objectiveModal || !modalActivitiesEl) return;
            const activityList = Array.isArray(activities) ? activities : [];
            const progress = activityList.length
              ? Math.round(activityList.reduce((s, a) => s + Number(a.avance || 0), 0) / activityList.length)
              : 0;
            const topStatus = activityList.length
              ? activityList.slice().sort((a, b) => statusRank(b.status) - statusRank(a.status))[0].status || 'No iniciado'
              : 'No iniciado';
            if (modalTitleEl) modalTitleEl.textContent = 'Actividades del objetivo';
            if (modalSubtitleEl) modalSubtitleEl.textContent = `${objective.codigo || 'sin código'} · ${objective.nombre || 'Objetivo'}`;
            if (modalStatusEl) modalStatusEl.textContent = topStatus;
            if (modalProgressEl) modalProgressEl.textContent = `${progress}%`;
            modalActivitiesEl.innerHTML = activityList.length ? activityList.map((a) => `
              <article class="border border-base-300 rounded-2xl p-4">
                <h4 class="text-2xl font-semibold">${esc(a.nombre || 'Actividad sin nombre')}</h4>
                <div class="text-base-content/60 italic">${esc(a.codigo || 'sin código')} · ${esc(a.responsable || 'Sin responsable')}</div>
                ${buildSubTree(a.subactivities || [], 0, 1)}
              </article>
            `).join('') : '<p class="text-base-content/70">No hay actividades registradas para este objetivo.</p>';
            if (typeof objectiveModal.showModal === 'function') objectiveModal.showModal();
          };
          const renderPoaAxisBoard = (payload) => {
            if (!axisColumnsEl) return;
            const objectives = Array.isArray(payload?.objectives) ? payload.objectives : [];
            const activities = Array.isArray(payload?.activities) ? payload.activities : [];
            const groupedByAxis = {};
            objectives.forEach((obj) => {
              const axisName = String(obj.axis_name || 'Sin eje').trim() || 'Sin eje';
              if (!groupedByAxis[axisName]) groupedByAxis[axisName] = [];
              groupedByAxis[axisName].push(obj);
            });
            const axisNames = Object.keys(groupedByAxis).sort((a, b) => a.localeCompare(b, 'es'));
            axisColumnsEl.innerHTML = axisNames.map((axisName) => {
              const items = groupedByAxis[axisName] || [];
              const cards = items.map((obj) => {
                const actCount = activities.filter((a) => Number(a.objective_id || 0) === Number(obj.id || 0)).length;
                const hito = Array.isArray(obj.hitos) && obj.hitos.length ? String(obj.hitos[0].nombre || '') : (obj.hito || 'N/D');
                return `
                  <article class="poa-objective-card card bg-base-100 border border-base-300 rounded-2xl shadow-sm p-4" data-poa-objective-id="${Number(obj.id || 0)}">
                    <div class="text-3xl font-semibold">${esc(obj.codigo || '')} ${esc(obj.nombre || 'Objetivo')}</div>
                    <div class="text-base-content/70">Hito: ${esc(hito || 'N/D')}</div>
                    <div class="text-base-content/70">Fecha inicial: ${esc(obj.fecha_inicial || 'N/D')}</div>
                    <div class="text-base-content/70">Fecha final: ${esc(obj.fecha_final || 'N/D')}</div>
                    <div class="text-base-content/70">Actividades: ${actCount}</div>
                    <div class="badge badge-outline mt-2">${esc(obj.codigo || 'sin-codigo')}</div>
                  </article>
                `;
              }).join('');
              return `
                <section class="panel card bg-base-100 border border-base-300 rounded-2xl shadow-sm">
                  <header class="panel__head">
                    <h3 class="text-2xl font-semibold text-base-content">${esc(axisName)}</h3>
                  </header>
                  <div class="grid gap-3">${cards || '<div class="text-base-content/60">Sin objetivos</div>'}</div>
                </section>
              `;
            }).join('');
            axisColumnsEl.querySelectorAll('.poa-objective-card').forEach((card) => {
              card.style.cursor = 'pointer';
              card.addEventListener('click', () => {
                const objectiveId = Number(card.getAttribute('data-poa-objective-id') || 0);
                const objective = objectives.find((o) => Number(o.id || 0) === objectiveId);
                const objectiveActivities = activities.filter((a) => Number(a.objective_id || 0) === objectiveId);
                openObjectiveModal(objective || {}, objectiveActivities);
              });
            });
            if (userBarsEl) {
              const byUser = {};
              activities.forEach((a) => {
                const user = String(a.responsable || 'Sin responsable').trim() || 'Sin responsable';
                byUser[user] = (byUser[user] || 0) + 1;
              });
              const total = activities.length;
              if (userTotalEl) userTotalEl.textContent = `Total asignadas: ${total}`;
              const users = Object.keys(byUser).sort((a, b) => byUser[b] - byUser[a]).slice(0, 8);
              userBarsEl.innerHTML = users.length ? users.map((u) => {
                const count = byUser[u];
                const pct = total ? Math.round((count * 1000) / total) / 10 : 0;
                return `
                  <div class="grid grid-cols-[minmax(220px,1fr)_3fr_auto] gap-3 items-center">
                    <div class="text-xl">${esc(u)}</div>
                    <progress class="progress progress-success w-full" value="${pct}" max="100"></progress>
                    <div class="text-xl">${count} (${pct}%)</div>
                  </div>
                `;
              }).join('') : '<div class="text-base-content/60">Sin actividades asignadas.</div>';
            }
          };
          const loadPoaBoard = async () => {
            try {
              const response = await fetch('/api/poa/board-data', { method: 'GET', credentials: 'same-origin' });
              const payload = await response.json().catch(() => ({}));
              if (!response.ok || payload?.success === false) throw new Error(payload?.error || payload?.detail || 'No se pudo cargar tablero POA.');
              renderPoaAxisBoard(payload);
            } catch (error) {
              if (axisColumnsEl) axisColumnsEl.innerHTML = `<div class="panel text-error">${esc(error?.message || 'No se pudo cargar tablero POA.')}</div>`;
            }
          };
          loadPoaBoard();
        })();
      </script>
    """)
    return render_backend_page(
        request,
        title="POA",
        description="Pantalla de trabajo POA.",
        content=base_content,
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/estrategia-tactica/tablero-control", response_class=HTMLResponse)
def estrategia_tactica_tablero_control_page(request: Request):
    _bind_core_symbols()
    # Esta ruta se usa como entrada del menú "Estrategia y táctica".
    # Redirigimos al módulo operativo para evitar mostrar una pantalla bloqueada.
    return RedirectResponse(url="/planes", status_code=302)


@router.get("/estrategia-tactica/base-ia", response_class=HTMLResponse)
def estrategia_tactica_ia_source_page(request: Request):
    _bind_core_symbols()
    if not is_superadmin(request):
        return RedirectResponse(url="/no-acceso", status_code=302)
    db = SessionLocal()
    try:
        try:
            from fastsipet_modulo.modulos.ia.ia import _refresh_weekly_strategic_extra_if_due
            _refresh_weekly_strategic_extra_if_due(db, force=False)
        except Exception:
            db.rollback()
        payload = _build_strategic_ia_payload(db)
    finally:
        db.close()
    return render_backend_page(
        request,
        title="Base IA estrategia",
        description="Concentrado ordenado para consulta IA del módulo de estrategia y táctica.",
        content=_build_strategic_ia_html(payload),
        hide_floating_actions=True,
        show_page_header=True,
    )


@router.get("/api/estrategia-tactica/base-ia", response_class=JSONResponse)
def estrategia_tactica_ia_source_api(request: Request):
    _bind_core_symbols()
    if not is_superadmin(request):
        return JSONResponse({"success": False, "error": "Acceso denegado"}, status_code=403)
    db = SessionLocal()
    try:
        try:
            from fastsipet_modulo.modulos.ia.ia import _refresh_weekly_strategic_extra_if_due
            _refresh_weekly_strategic_extra_if_due(db, force=False)
        except Exception:
            db.rollback()
        payload = _build_strategic_ia_payload(db)
        return JSONResponse({"success": True, "data": payload})
    finally:
        db.close()


@router.get("/api/estrategia-tactica/base-ia/contenido", response_class=JSONResponse)
def estrategia_tactica_ia_extra_get(request: Request):
    _bind_core_symbols()
    if not is_superadmin(request):
        return JSONResponse({"success": False, "error": "Acceso denegado"}, status_code=403)
    db = SessionLocal()
    try:
        _ensure_strategic_identity_table(db)
        db.commit()
        row = db.execute(
            text("SELECT payload FROM strategic_identity_config WHERE bloque = 'base_ia_extra' LIMIT 1")
        ).fetchone()
        payload_raw = str(row[0] or "{}") if row else "{}"
        try:
            payload_json = json.loads(payload_raw)
        except Exception:
            payload_json = {}
        texto = str((payload_json if isinstance(payload_json, dict) else {}).get("texto") or "").strip()
        return JSONResponse({"success": True, "data": {"texto": texto}})
    finally:
        db.close()


@router.put("/api/estrategia-tactica/base-ia/contenido", response_class=JSONResponse)
def estrategia_tactica_ia_extra_put(request: Request, data: dict = Body(...)):
    _bind_core_symbols()
    if not is_superadmin(request):
        return JSONResponse({"success": False, "error": "Acceso denegado"}, status_code=403)
    texto = str(data.get("texto") or "").strip()
    encoded = json.dumps({"texto": texto}, ensure_ascii=False)
    db = SessionLocal()
    try:
        _ensure_strategic_identity_table(db)
        db.execute(
            text(
                """
                INSERT INTO strategic_identity_config (bloque, payload, updated_at)
                VALUES ('base_ia_extra', :payload, CURRENT_TIMESTAMP)
                ON CONFLICT (bloque)
                DO UPDATE SET payload = EXCLUDED.payload, updated_at = CURRENT_TIMESTAMP
                """
            ),
            {"payload": encoded},
        )
        db.commit()
        return JSONResponse({"success": True, "data": {"texto": texto}})
    except (sqlite3.OperationalError, SQLAlchemyError):
        db.rollback()
        return JSONResponse(
            {"success": False, "error": "No se pudo escribir en la base de datos (modo solo lectura o bloqueo)."},
            status_code=500,
        )
    finally:
        db.close()


# ─────────────────────────────────────────────
# POA · Base IA
# ─────────────────────────────────────────────
_POA_BASE_IA_EXTRA_BLOCK = "poa_base_ia_extra"
_POA_BASE_IA_WEEKLY_META_BLOCK = "poa_base_ia_weekly_meta"
_POA_BASE_IA_WEEKLY_INTERVAL_DAYS = 7
_poa_base_ia_cron_lock = threading.Lock()


def _build_poa_ia_payload(db) -> Dict[str, Any]:
    """Concentra todos los datos de POA relevantes para la IA."""
    _ensure_strategic_identity_table(db)
    db.commit()
    # Contenido adicional editable y meta semanal
    rows_extra = db.execute(
        text(
            "SELECT bloque, payload FROM strategic_identity_config "
            "WHERE bloque IN (:extra, :meta)"
        ),
        {"extra": _POA_BASE_IA_EXTRA_BLOCK, "meta": _POA_BASE_IA_WEEKLY_META_BLOCK},
    ).fetchall()
    payload_map = {str(r[0]).strip(): str(r[1] or "") for r in rows_extra}
    try:
        extra_payload = json.loads(payload_map.get(_POA_BASE_IA_EXTRA_BLOCK, "{}") or "{}")
    except Exception:
        extra_payload = {}
    try:
        weekly_meta_payload = json.loads(payload_map.get(_POA_BASE_IA_WEEKLY_META_BLOCK, "{}") or "{}")
    except Exception:
        weekly_meta_payload = {}
    contenido_adicional = str((extra_payload if isinstance(extra_payload, dict) else {}).get("texto") or "").strip()
    weekly_meta = weekly_meta_payload if isinstance(weekly_meta_payload, dict) else {}

    # Ejes y objetivos con actividades
    axes = (
        db.query(StrategicAxisConfig)
        .filter(StrategicAxisConfig.is_active == True)
        .order_by(StrategicAxisConfig.orden.asc(), StrategicAxisConfig.id.asc())
        .all()
    ) or db.query(StrategicAxisConfig).order_by(StrategicAxisConfig.orden.asc(), StrategicAxisConfig.id.asc()).all()

    today = datetime.utcnow().date()
    axes_data = []
    total_objectives = 0
    total_activities_all = 0
    for axis in axes:
        objectives = (
            db.query(StrategicObjectiveConfig)
            .filter(StrategicObjectiveConfig.axis_id == axis.id, StrategicObjectiveConfig.is_active == True)
            .order_by(StrategicObjectiveConfig.orden.asc(), StrategicObjectiveConfig.id.asc())
            .all()
        ) or (
            db.query(StrategicObjectiveConfig)
            .filter(StrategicObjectiveConfig.axis_id == axis.id)
            .order_by(StrategicObjectiveConfig.orden.asc(), StrategicObjectiveConfig.id.asc())
            .all()
        )
        objectives_data = []
        for obj in objectives:
            activities = (
                db.query(POAActivity)
                .filter(POAActivity.objective_id == obj.id)
                .order_by(POAActivity.id.asc())
                .all()
            )
            total_activities_all += len(activities)
            acts_data = []
            for act in activities:
                estado = _activity_status(act, today)
                acts_data.append({
                    "id": int(act.id or 0),
                    "nombre": str(act.nombre or ""),
                    "codigo": str(act.codigo or ""),
                    "responsable": str(act.responsable or ""),
                    "entregable": str(act.entregable or ""),
                    "entrega_estado": str(act.entrega_estado or "ninguna"),
                    "estado_calculado": estado,
                    "fecha_inicial": _date_to_iso(act.fecha_inicial),
                    "fecha_final": _date_to_iso(act.fecha_final),
                    "recurrente": bool(act.recurrente),
                })
            objectives_data.append({
                "id": int(obj.id or 0),
                "nombre": str(obj.nombre or ""),
                "codigo": str(obj.codigo or ""),
                "lider": str(getattr(obj, "lider", "") or ""),
                "actividades": acts_data,
                "total_actividades": len(acts_data),
            })
        total_objectives += len(objectives_data)
        axes_data.append({
            "id": int(axis.id or 0),
            "nombre": str(axis.nombre or ""),
            "codigo": str(axis.codigo or ""),
            "objetivos": objectives_data,
            "total_objetivos": len(objectives_data),
        })

    avance_resumen = _build_strategic_progress_summary(db)
    return {
        "contenido_adicional": {"texto": contenido_adicional},
        "avance": avance_resumen,
        "cron_semanal": {
            "activo": True,
            "intervalo_dias": int(weekly_meta.get("interval_days") or _POA_BASE_IA_WEEKLY_INTERVAL_DAYS),
            "ultima_actualizacion": str(weekly_meta.get("last_refresh_at") or ""),
            "proxima_actualizacion": str(weekly_meta.get("next_refresh_at") or ""),
            "estado": str(weekly_meta.get("last_status") or ""),
            "error": str(weekly_meta.get("last_error") or ""),
        },
        "ejes": axes_data,
        "resumen": {
            "total_ejes": len(axes_data),
            "total_objetivos": total_objectives,
            "total_actividades": total_activities_all,
        },
    }


def _build_poa_ia_html(payload: Dict[str, Any]) -> str:
    avance = payload.get("avance", {}) if isinstance(payload, dict) else {}
    cron = payload.get("cron_semanal", {}) if isinstance(payload, dict) else {}
    ejes = payload.get("ejes", []) if isinstance(payload, dict) else []
    resumen = payload.get("resumen", {}) if isinstance(payload, dict) else {}
    contenido_adicional_texto = str((payload.get("contenido_adicional") or {}).get("texto") or "")
    payload_json = json.dumps(payload, ensure_ascii=False, indent=2)

    axes_html = []
    for axis in ejes:
        axis_name = escape(str(axis.get("nombre") or "Eje sin nombre"))
        axis_code = escape(str(axis.get("codigo") or ""))
        objectives = axis.get("objetivos") or []
        objs_html_parts = []
        for obj in objectives:
            lider = escape(str(obj.get("lider") or ""))
            obj_lider_line = f"<div>Líder: {lider}</div>" if lider else ""
            activities = obj.get("actividades") or []
            acts_rows = "".join(
                "<tr>"
                f"<td>{escape(str(a.get('codigo') or ''))}</td>"
                f"<td>{escape(str(a.get('nombre') or ''))}</td>"
                f"<td>{escape(str(a.get('responsable') or ''))}</td>"
                f"<td>{escape(str(a.get('estado_calculado') or ''))}</td>"
                f"<td>{escape(str(a.get('fecha_final') or ''))}</td>"
                "</tr>"
                for a in activities
            ) or "<tr><td colspan='5'>Sin actividades</td></tr>"
            acts_table = (
                "<table>"
                "<thead><tr>"
                "<th>Código</th>"
                "<th>Actividad</th>"
                "<th>Responsable</th>"
                "<th>Estado</th>"
                "<th>Fecha fin</th>"
                "</tr></thead>"
                f"<tbody>{acts_rows}</tbody>"
                "</table>"
            )
            objs_html_parts.append(
                "<li>"
                f"<strong>{escape(str(obj.get('codigo') or 'OBJ'))}</strong> · "
                f"{escape(str(obj.get('nombre') or 'Objetivo sin nombre'))}"
                f"{obj_lider_line}"
                f"<div>{acts_table}</div>"
                "</li>"
            )
        objs_block = "<ul>" + "".join(objs_html_parts) + "</ul>" if objs_html_parts else "<p>Sin objetivos.</p>"
        axes_html.append(
            "<article>"
            f"<h4>{axis_name}</h4>"
            f"<div>Código: {axis_code} · {int(axis.get('total_objetivos') or 0)} objetivos</div>"
            f"{objs_block}"
            "</article>"
        )
    axes_block = "".join(axes_html) if axes_html else "<p>Sin ejes registrados.</p>"

    return (
        "<section>"
        "<section>"
        "<h3>Base IA · POA</h3>"
        "<p>Fuente consolidada para consulta de IA: ejes, objetivos, actividades y avance del Plan Operativo Anual.</p>"
        "</section>"
        "<section>"
        "<h4>Resumen</h4>"
        f"<p>Ejes: <b>{int(resumen.get('total_ejes') or 0)}</b> · "
        f"Objetivos: <b>{int(resumen.get('total_objetivos') or 0)}</b> · "
        f"Actividades: <b>{int(resumen.get('total_actividades') or 0)}</b></p>"
        "</section>"
        "<section>"
        "<h4>Avance POA</h4>"
        f"<p>Actividades: <b>{int((avance or {}).get('activities_total') or 0)}</b> · "
        f"Completadas: <b>{int((avance or {}).get('activities_completed') or 0)}</b> · "
        f"Vencidas: <b>{int((avance or {}).get('activities_overdue') or 0)}</b> · "
        f"Avance estimado: <b>{float((avance or {}).get('progress_avg') or 0):.2f}%</b></p>"
        f"<p>Corte: {escape(str((avance or {}).get('generated_at') or ''))}</p>"
        "</section>"
        "<section>"
        "<h4>Cron semanal (renovación automática)</h4>"
        f"<p>Intervalo: <b>{int((cron or {}).get('intervalo_dias') or _POA_BASE_IA_WEEKLY_INTERVAL_DAYS)} días</b> · "
        f"Última actualización: <b>{escape(str((cron or {}).get('ultima_actualizacion') or 'N/D'))}</b> · "
        f"Próxima: <b>{escape(str((cron or {}).get('proxima_actualizacion') or 'N/D'))}</b></p>"
        f"<p>Estado: {escape(str((cron or {}).get('estado') or 'sin_ejecucion'))}</p>"
        "<button type='button' id='poa-base-ia-weekly-refresh'>Actualizar ahora (reemplaza contenido previo)</button>"
        "<span id='poa-base-ia-weekly-refresh-status'></span>"
        "<script>"
        "(function(){"
        "  const btn=document.getElementById('poa-base-ia-weekly-refresh');"
        "  const st=document.getElementById('poa-base-ia-weekly-refresh-status');"
        "  if(!btn||!st){return;}"
        "  btn.addEventListener('click', async function(){"
        "    btn.disabled=true; st.textContent='Actualizando...';"
        "    try{"
        "      const res=await fetch('/api/poa/base-ia/refresh',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({force:true})});"
        "      const data=await res.json();"
        "      if(!res.ok||!data||data.success!==true){throw new Error((data&&data.error)||'No se pudo actualizar');}"
        "      st.textContent='Actualización ejecutada. Recarga para ver cambios.';"
        "    }catch(err){st.textContent=(err&&err.message)?err.message:'Error al actualizar';}"
        "    finally{btn.disabled=false;}"
        "  });"
        "})();"
        "</script>"
        "</section>"
        "<section>"
        "<h4>Ejes, objetivos y actividades</h4>"
        f"<div>{axes_block}</div>"
        "</section>"
        "<section>"
        "<h4>Contenido adicional para IA (editable)</h4>"
        "<p>Este bloque se usa como contexto adicional en Conversaciones IA del módulo POA.</p>"
        f"<textarea id='poa-base-ia-extra-text'>{escape(contenido_adicional_texto)}</textarea>"
        "<div>"
        "<button type='button' id='poa-base-ia-extra-save'>Guardar contenido adicional</button>"
        "<span id='poa-base-ia-extra-status'></span>"
        "</div>"
        "<script>"
        "(function(){"
        "  const btn=document.getElementById('poa-base-ia-extra-save');"
        "  const txt=document.getElementById('poa-base-ia-extra-text');"
        "  const st=document.getElementById('poa-base-ia-extra-status');"
        "  if(!btn||!txt||!st){return;}"
        "  btn.addEventListener('click', async function(){"
        "    btn.disabled=true; st.textContent='Guardando...';"
        "    try{"
        "      const res=await fetch('/api/poa/base-ia/contenido',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({texto:String(txt.value||'')})});"
        "      const data=await res.json();"
        "      if(!res.ok||!data||data.success!==true){throw new Error((data&&data.error)||'No se pudo guardar');}"
        "      st.textContent='Guardado correctamente';"
        "    }catch(err){st.textContent=(err&&err.message)?err.message:'Error al guardar';}"
        "    finally{btn.disabled=false;}"
        "  });"
        "})();"
        "</script>"
        "</section>"
        "<section>"
        "<h4>Payload estructurado (JSON)</h4>"
        f"<pre>{escape(payload_json)}</pre>"
        "</section>"
        "</section>"
    )


def _refresh_weekly_poa_base_ia_if_due(db, force: bool = False) -> dict:
    """Actualiza el resumen semanal de POA reemplazando el contenido anterior."""
    with _poa_base_ia_cron_lock:
        _ensure_strategic_identity_table(db)
        meta_row = db.execute(
            text("SELECT payload FROM strategic_identity_config WHERE bloque = :b LIMIT 1"),
            {"b": _POA_BASE_IA_WEEKLY_META_BLOCK},
        ).fetchone()
        try:
            meta = json.loads(str(meta_row[0] or "{}")) if meta_row else {}
        except Exception:
            meta = {}
        last_refresh_raw = str(meta.get("last_refresh_at") or "").strip()
        now = datetime.utcnow()
        last_refresh_dt = None
        if last_refresh_raw:
            try:
                last_refresh_dt = datetime.fromisoformat(last_refresh_raw)
            except Exception:
                pass
        due = force or (last_refresh_dt is None) or ((now - last_refresh_dt) >= timedelta(days=_POA_BASE_IA_WEEKLY_INTERVAL_DAYS))
        if not due:
            next_at = (last_refresh_dt + timedelta(days=_POA_BASE_IA_WEEKLY_INTERVAL_DAYS)).isoformat() if last_refresh_dt else ""
            return {"updated": False, "reason": "not_due", "last_refresh_at": last_refresh_raw, "next_refresh_at": next_at}
        # Genera snapshot de estado actual del POA como texto
        avance = _build_strategic_progress_summary(db)
        today = now.date()
        snapshot_lines = [
            "=== Snapshot semanal POA ===",
            f"Corte: {now.isoformat()}",
            f"Actividades: {avance.get('activities_total', 0)} totales · {avance.get('activities_completed', 0)} completadas · {avance.get('activities_overdue', 0)} vencidas",
            f"Avance estimado: {avance.get('progress_avg', 0):.2f}%",
        ]
        # ── Sección 1: Ejes → Objetivos → Actividades ──────────────────────
        axes = (
            db.query(StrategicAxisConfig)
            .filter(StrategicAxisConfig.is_active == True)
            .order_by(StrategicAxisConfig.orden.asc(), StrategicAxisConfig.id.asc())
            .all()
        ) or db.query(StrategicAxisConfig).order_by(StrategicAxisConfig.orden.asc(), StrategicAxisConfig.id.asc()).all()
        all_activities_global = []  # acumulado para breakdown posterior
        for axis in axes:
            snapshot_lines.append(f"\nEje: {axis.nombre} ({axis.codigo})")
            objectives = (
                db.query(StrategicObjectiveConfig)
                .filter(StrategicObjectiveConfig.axis_id == axis.id, StrategicObjectiveConfig.is_active == True)
                .all()
            ) or db.query(StrategicObjectiveConfig).filter(StrategicObjectiveConfig.axis_id == axis.id).all()
            for obj in objectives:
                activities = db.query(POAActivity).filter(POAActivity.objective_id == obj.id).all()
                all_activities_global.extend(activities)
                completadas = sum(1 for a in activities if _activity_status(a, today) == "Terminada")
                vencidas = sum(1 for a in activities if _activity_status(a, today) == "Atrasada")
                en_proceso = len(activities) - completadas - vencidas
                snapshot_lines.append(
                    f"  OBJ {obj.codigo} · {obj.nombre} · "
                    f"{len(activities)} act. · {completadas} terminadas · {vencidas} vencidas · {en_proceso} en proceso"
                )
                # Detalle de actividades individuales (máx 50 por objetivo para no superar límite)
                for act in activities[:50]:
                    estado = _activity_status(act, today)
                    resp = str(act.responsable or "Sin asignar").strip()
                    fecha = str(act.fecha_final or "").strip() or "s/f"
                    snapshot_lines.append(
                        f"    • [{estado}] {act.codigo or '?'} · {act.nombre or '?'} · "
                        f"Resp: {resp} · Vence: {fecha}"
                    )
        # ── Sección 2: Breakdown por RESPONSABLE ────────────────────────────
        if all_activities_global:
            resp_map: dict = {}
            for act in all_activities_global:
                r = str(act.responsable or "Sin asignar").strip() or "Sin asignar"
                if r not in resp_map:
                    resp_map[r] = {"total": 0, "terminadas": 0, "atrasadas": 0, "en_proceso": 0, "actividades": []}
                estado = _activity_status(act, today)
                resp_map[r]["total"] += 1
                if estado == "Terminada":
                    resp_map[r]["terminadas"] += 1
                elif estado == "Atrasada":
                    resp_map[r]["atrasadas"] += 1
                else:
                    resp_map[r]["en_proceso"] += 1
                resp_map[r]["actividades"].append(
                    f"{act.codigo or '?'}: {str(act.nombre or '').strip()[:60]} [{estado}]"
                )
            snapshot_lines.append("\n=== AVANCE POR RESPONSABLE ===")
            for responsable in sorted(resp_map.keys()):
                rd = resp_map[responsable]
                pct = round(rd["terminadas"] / rd["total"] * 100, 1) if rd["total"] else 0.0
                snapshot_lines.append(
                    f"\nResponsable: {responsable} · Total: {rd['total']} · "
                    f"Terminadas: {rd['terminadas']} · Atrasadas: {rd['atrasadas']} · "
                    f"En proceso: {rd['en_proceso']} · Avance: {pct}%"
                )
                for act_line in rd["actividades"][:20]:
                    snapshot_lines.append(f"  - {act_line}")
                if len(rd["actividades"]) > 20:
                    snapshot_lines.append(f"  ... y {len(rd['actividades']) - 20} actividades más")
        # ── Sección 3: Resumen estadístico consolidado ──────────────────────
        total_g = len(all_activities_global)
        term_g = sum(1 for a in all_activities_global if _activity_status(a, today) == "Terminada")
        atra_g = sum(1 for a in all_activities_global if _activity_status(a, today) == "Atrasada")
        proc_g = total_g - term_g - atra_g
        snapshot_lines.append("\n=== RESUMEN CONSOLIDADO ===")
        snapshot_lines.append(
            f"Total actividades: {total_g} | Terminadas: {term_g} ({round(term_g/total_g*100,1) if total_g else 0}%) | "
            f"Atrasadas: {atra_g} | En proceso: {proc_g}"
        )
        new_text = "\n".join(snapshot_lines)
        # Reemplaza completamente el contenido anterior
        for bloque, valor in [
            (_POA_BASE_IA_EXTRA_BLOCK, json.dumps({"texto": new_text}, ensure_ascii=False)),
        ]:
            db.execute(
                text(
                    "INSERT INTO strategic_identity_config (bloque, payload, updated_at) "
                    "VALUES (:b, :p, CURRENT_TIMESTAMP) "
                    "ON CONFLICT (bloque) DO UPDATE SET payload = EXCLUDED.payload, updated_at = CURRENT_TIMESTAMP"
                ),
                {"b": bloque, "p": valor},
            )
        next_at = (now + timedelta(days=_POA_BASE_IA_WEEKLY_INTERVAL_DAYS)).isoformat()
        new_meta = {
            "last_refresh_at": now.isoformat(),
            "next_refresh_at": next_at,
            "interval_days": _POA_BASE_IA_WEEKLY_INTERVAL_DAYS,
            "last_status": "ok",
            "last_error": "",
            "generated_chars": len(new_text),
        }
        db.execute(
            text(
                "INSERT INTO strategic_identity_config (bloque, payload, updated_at) "
                "VALUES (:b, :p, CURRENT_TIMESTAMP) "
                "ON CONFLICT (bloque) DO UPDATE SET payload = EXCLUDED.payload, updated_at = CURRENT_TIMESTAMP"
            ),
            {"b": _POA_BASE_IA_WEEKLY_META_BLOCK, "p": json.dumps(new_meta, ensure_ascii=False)},
        )
        db.commit()
        return {"updated": True, "last_refresh_at": now.isoformat(), "next_refresh_at": next_at, "generated_chars": len(new_text)}


@router.get("/poa/base-ia", response_class=HTMLResponse)
def poa_base_ia_page(request: Request):
    _bind_core_symbols()
    if not is_superadmin(request):
        return RedirectResponse(url="/no-acceso", status_code=302)
    db = SessionLocal()
    try:
        try:
            _refresh_weekly_poa_base_ia_if_due(db, force=False)
        except Exception:
            db.rollback()
        payload = _build_poa_ia_payload(db)
    finally:
        db.close()
    return render_backend_page(
        request,
        title="Base IA · POA",
        description="Concentrado ordenado para consulta IA del módulo POA.",
        content=_build_poa_ia_html(payload),
        hide_floating_actions=True,
        show_page_header=True,
    )


@router.get("/api/poa/base-ia", response_class=JSONResponse)
def poa_base_ia_api(request: Request):
    _bind_core_symbols()
    if not is_superadmin(request):
        return JSONResponse({"success": False, "error": "Acceso denegado"}, status_code=403)
    db = SessionLocal()
    try:
        try:
            _refresh_weekly_poa_base_ia_if_due(db, force=False)
        except Exception:
            db.rollback()
        payload = _build_poa_ia_payload(db)
        return JSONResponse({"success": True, "data": payload})
    finally:
        db.close()


@router.get("/api/poa/base-ia/contenido", response_class=JSONResponse)
def poa_base_ia_contenido_get(request: Request):
    _bind_core_symbols()
    if not is_superadmin(request):
        return JSONResponse({"success": False, "error": "Acceso denegado"}, status_code=403)
    db = SessionLocal()
    try:
        _ensure_strategic_identity_table(db)
        db.commit()
        row = db.execute(
            text("SELECT payload FROM strategic_identity_config WHERE bloque = :b LIMIT 1"),
            {"b": _POA_BASE_IA_EXTRA_BLOCK},
        ).fetchone()
        payload_raw = str(row[0] or "{}") if row else "{}"
        try:
            payload_json = json.loads(payload_raw)
        except Exception:
            payload_json = {}
        texto = str((payload_json if isinstance(payload_json, dict) else {}).get("texto") or "").strip()
        return JSONResponse({"success": True, "data": {"texto": texto}})
    finally:
        db.close()


@router.put("/api/poa/base-ia/contenido", response_class=JSONResponse)
def poa_base_ia_contenido_put(request: Request, data: dict = Body(...)):
    _bind_core_symbols()
    if not is_superadmin(request):
        return JSONResponse({"success": False, "error": "Acceso denegado"}, status_code=403)
    texto = str(data.get("texto") or "").strip()
    encoded = json.dumps({"texto": texto}, ensure_ascii=False)
    db = SessionLocal()
    try:
        _ensure_strategic_identity_table(db)
        db.execute(
            text(
                "INSERT INTO strategic_identity_config (bloque, payload, updated_at) "
                "VALUES (:b, :p, CURRENT_TIMESTAMP) "
                "ON CONFLICT (bloque) DO UPDATE SET payload = EXCLUDED.payload, updated_at = CURRENT_TIMESTAMP"
            ),
            {"b": _POA_BASE_IA_EXTRA_BLOCK, "p": encoded},
        )
        db.commit()
        return JSONResponse({"success": True, "data": {"texto": texto}})
    except (sqlite3.OperationalError, SQLAlchemyError):
        db.rollback()
        return JSONResponse({"success": False, "error": "No se pudo escribir en la base de datos."}, status_code=500)
    finally:
        db.close()


@router.post("/api/poa/base-ia/refresh", response_class=JSONResponse)
def poa_base_ia_refresh(request: Request, data: dict = Body(default={})):
    _bind_core_symbols()
    if not is_superadmin(request):
        return JSONResponse({"success": False, "error": "Acceso denegado"}, status_code=403)
    force = bool((data or {}).get("force", True))
    db = SessionLocal()
    try:
        result = _refresh_weekly_poa_base_ia_if_due(db, force=force)
        return JSONResponse({"success": True, "data": result})
    except Exception as exc:
        db.rollback()
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)
    finally:
        db.close()


@router.get("/api/planificacion/plantilla-plan-poa.csv")
def download_strategic_poa_template():
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=STRATEGIC_POA_CSV_HEADERS)
    writer.writeheader()
    for row in _strategic_poa_template_rows():
        writer.writerow({key: row.get(key, "") for key in STRATEGIC_POA_CSV_HEADERS})
    content = output.getvalue()
    headers = {"Content-Disposition": 'attachment; filename="plantilla_plan_estrategico_poa.csv"'}
    return Response(content, media_type="text/csv; charset=utf-8", headers=headers)


@router.get("/api/planificacion/exportar-plan-poa.xlsx")
def export_strategic_poa_xlsx():
    _bind_core_symbols()
    db = SessionLocal()
    try:
        export_rows = _strategic_poa_export_rows(db)
    finally:
        db.close()

    records = [{key: _csv_value(row, key) for key in STRATEGIC_POA_CSV_HEADERS} for row in export_rows]
    df = pd.DataFrame(records, columns=STRATEGIC_POA_CSV_HEADERS)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Plan_POA")
    output.seek(0)
    filename = f'plan_estrategico_poa_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.xlsx'
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.post("/api/planificacion/importar-plan-poa")
async def import_strategic_poa_csv(file: UploadFile = File(...)):
    _bind_core_symbols()
    filename = (file.filename or "").strip().lower()
    if not filename.endswith(".csv"):
        return JSONResponse({"success": False, "error": "El archivo debe ser CSV (.csv)."}, status_code=400)

    raw_bytes = await file.read()
    if not raw_bytes:
        return JSONResponse({"success": False, "error": "El archivo CSV está vacío."}, status_code=400)
    try:
        raw_text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            raw_text = raw_bytes.decode("latin-1")
        except UnicodeDecodeError:
            return JSONResponse(
                {"success": False, "error": "No se pudo leer el archivo. Usa codificación UTF-8."},
                status_code=400,
            )

    reader = csv.DictReader(StringIO(raw_text))
    if not reader.fieldnames:
        return JSONResponse({"success": False, "error": "Encabezados CSV no válidos."}, status_code=400)
    missing_headers = [h for h in ["tipo_registro"] if h not in reader.fieldnames]
    if missing_headers:
        return JSONResponse(
            {"success": False, "error": f"Faltan columnas obligatorias: {', '.join(missing_headers)}"},
            status_code=400,
        )

    db = SessionLocal()
    summary = {"created": 0, "updated": 0, "skipped": 0, "errors": []}
    try:
        _ensure_poa_subactivity_recurrence_columns(db)
        axes = db.query(StrategicAxisConfig).all()
        axis_by_code = {str((item.codigo or "")).strip().lower(): item for item in axes if (item.codigo or "").strip()}
        objectives = db.query(StrategicObjectiveConfig).all()
        objective_by_code = {str((item.codigo or "")).strip().lower(): item for item in objectives if (item.codigo or "").strip()}
        activities = db.query(POAActivity).all()
        activity_by_key: Dict[str, POAActivity] = {}
        activity_by_code_list: Dict[str, List[POAActivity]] = {}
        for item in activities:
            code = str((item.codigo or "")).strip().lower()
            if not code:
                continue
            objective_key = f"{int(item.objective_id)}::{code}"
            activity_by_key[objective_key] = item
            activity_by_code_list.setdefault(code, []).append(item)
        subactivities = db.query(POASubactivity).all()
        sub_by_activity_code: Dict[str, Dict[str, POASubactivity]] = {}
        activity_code_by_id = {int(item.id): str((item.codigo or "")).strip().lower() for item in activities}
        for sub in subactivities:
            activity_code = activity_code_by_id.get(int(sub.activity_id or 0), "")
            sub_code = str((sub.codigo or "")).strip().lower()
            if not activity_code or not sub_code:
                continue
            sub_by_activity_code.setdefault(activity_code, {})[sub_code] = sub

        max_axis_order = db.query(func.max(StrategicAxisConfig.orden)).scalar() or 0
        objective_order_by_axis: Dict[int, int] = {}
        for item in objectives:
            axis_id = int(item.eje_id or 0)
            objective_order_by_axis[axis_id] = max(objective_order_by_axis.get(axis_id, 0), int(item.orden or 0))

        for row_index, row in enumerate(reader, start=2):
            try:
                kind = _normalize_import_kind(_csv_value(row, "tipo_registro"))
                if kind not in {"eje", "objetivo", "actividad", "subactividad"}:
                    summary["skipped"] += 1
                    summary["errors"].append(f"Fila {row_index}: tipo_registro no reconocido.")
                    continue

                if kind == "eje":
                    axis_code = _csv_value(row, "axis_codigo").lower()
                    axis_name = _csv_value(row, "axis_nombre")
                    if not axis_code:
                        raise ValueError("axis_codigo es obligatorio para tipo_registro=eje.")
                    if not axis_name and axis_code not in axis_by_code:
                        raise ValueError("axis_nombre es obligatorio al crear un eje.")
                    axis_order = _parse_import_int(_csv_value(row, "axis_orden"), 0)
                    axis = axis_by_code.get(axis_code)
                    if axis:
                        if axis_name:
                            axis.nombre = axis_name
                        axis.lider_departamento = _csv_value(row, "axis_lider_departamento")
                        axis.responsabilidad_directa = _csv_value(row, "axis_responsabilidad_directa")
                        axis.descripcion = _csv_value(row, "axis_descripcion")
                        if axis_order > 0:
                            axis.orden = axis_order
                        db.add(axis)
                        summary["updated"] += 1
                    else:
                        max_axis_order += 1
                        axis = StrategicAxisConfig(
                            nombre=axis_name or "Nuevo eje",
                            codigo=axis_code,
                            lider_departamento=_csv_value(row, "axis_lider_departamento"),
                            responsabilidad_directa=_csv_value(row, "axis_responsabilidad_directa"),
                            descripcion=_csv_value(row, "axis_descripcion"),
                            orden=axis_order if axis_order > 0 else max_axis_order,
                            is_active=True,
                        )
                        db.add(axis)
                        db.flush()
                        axis_by_code[axis_code] = axis
                        summary["created"] += 1
                    continue

                if kind == "objetivo":
                    axis_code = _csv_value(row, "axis_codigo").lower()
                    axis = axis_by_code.get(axis_code)
                    if not axis:
                        raise ValueError("axis_codigo no existe. Carga primero el eje.")
                    objective_code = _csv_value(row, "objective_codigo").lower()
                    objective_name = _csv_value(row, "objective_nombre")
                    if not objective_code:
                        raise ValueError("objective_codigo es obligatorio para tipo_registro=objetivo.")
                    objective = objective_by_code.get(objective_code)
                    start_date = _parse_import_date(_csv_value(row, "objective_fecha_inicial"))
                    end_date = _parse_import_date(_csv_value(row, "objective_fecha_final"))
                    if (start_date and not end_date) or (end_date and not start_date):
                        raise ValueError("objective_fecha_inicial y objective_fecha_final deben definirse juntas.")
                    if start_date and end_date:
                        range_error = _validate_date_range(start_date, end_date, "Objetivo")
                        if range_error:
                            raise ValueError(range_error)
                    objective_order = _parse_import_int(_csv_value(row, "objective_orden"), 0)
                    if objective:
                        if objective_name:
                            objective.nombre = objective_name
                        objective.eje_id = int(axis.id)
                        objective.hito = _csv_value(row, "objective_hito")
                        objective.lider = _csv_value(row, "objective_lider")
                        objective.fecha_inicial = start_date
                        objective.fecha_final = end_date
                        objective.descripcion = _csv_value(row, "objective_descripcion")
                        if objective_order > 0:
                            objective.orden = objective_order
                        db.add(objective)
                        summary["updated"] += 1
                    else:
                        if not objective_name:
                            raise ValueError("objective_nombre es obligatorio al crear un objetivo.")
                        next_obj_order = objective_order if objective_order > 0 else (objective_order_by_axis.get(int(axis.id), 0) + 1)
                        objective = StrategicObjectiveConfig(
                            eje_id=int(axis.id),
                            codigo=objective_code,
                            nombre=objective_name,
                            hito=_csv_value(row, "objective_hito"),
                            lider=_csv_value(row, "objective_lider"),
                            fecha_inicial=start_date,
                            fecha_final=end_date,
                            descripcion=_csv_value(row, "objective_descripcion"),
                            orden=next_obj_order,
                            is_active=True,
                        )
                        db.add(objective)
                        db.flush()
                        objective_by_code[objective_code] = objective
                        objective_order_by_axis[int(axis.id)] = max(objective_order_by_axis.get(int(axis.id), 0), int(next_obj_order))
                        summary["created"] += 1
                    continue

                if kind == "actividad":
                    objective_code = _csv_value(row, "objective_codigo").lower()
                    objective = objective_by_code.get(objective_code)
                    if not objective:
                        raise ValueError("objective_codigo no existe. Carga primero el objetivo.")
                    activity_code = _csv_value(row, "activity_codigo").lower()
                    activity_name = _csv_value(row, "activity_nombre")
                    if not activity_code:
                        raise ValueError("activity_codigo es obligatorio para tipo_registro=actividad.")
                    activity_key = f"{int(objective.id)}::{activity_code}"
                    activity = activity_by_key.get(activity_key)
                    start_date = _parse_import_date(_csv_value(row, "activity_fecha_inicial"))
                    end_date = _parse_import_date(_csv_value(row, "activity_fecha_final"))
                    if (start_date and not end_date) or (end_date and not start_date):
                        raise ValueError("activity_fecha_inicial y activity_fecha_final deben definirse juntas.")
                    if start_date and end_date:
                        range_error = _validate_date_range(start_date, end_date, "Actividad")
                        if range_error:
                            raise ValueError(range_error)
                        parent_range_error = _validate_child_date_range(
                            start_date,
                            end_date,
                            objective.fecha_inicial,
                            objective.fecha_final,
                            "Actividad",
                            "Objetivo",
                        )
                        if parent_range_error:
                            raise ValueError(parent_range_error)
                    recurrente = _parse_import_bool(_csv_value(row, "activity_recurrente"))
                    periodicidad = _csv_value(row, "activity_periodicidad").lower()
                    cada_xx_dias = _parse_import_int(_csv_value(row, "activity_cada_xx_dias"), 0)
                    if recurrente:
                        if periodicidad not in VALID_ACTIVITY_PERIODICITIES:
                            raise ValueError("activity_periodicidad no es válida para actividad recurrente.")
                        if periodicidad == "cada_xx_dias" and cada_xx_dias <= 0:
                            raise ValueError("activity_cada_xx_dias debe ser mayor a 0 para periodicidad cada_xx_dias.")
                    else:
                        periodicidad = ""
                        cada_xx_dias = 0

                    if activity:
                        if activity_name:
                            activity.nombre = activity_name
                        activity.responsable = _csv_value(row, "activity_responsable")
                        activity.entregable = _csv_value(row, "activity_entregable")
                        activity.fecha_inicial = start_date
                        activity.fecha_final = end_date
                        activity.descripcion = _csv_value(row, "activity_descripcion")
                        activity.recurrente = recurrente
                        activity.periodicidad = periodicidad
                        activity.cada_xx_dias = cada_xx_dias if periodicidad == "cada_xx_dias" else None
                        db.add(activity)
                        summary["updated"] += 1
                    else:
                        if not activity_name:
                            raise ValueError("activity_nombre es obligatorio al crear una actividad.")
                        activity = POAActivity(
                            objective_id=int(objective.id),
                            codigo=activity_code,
                            nombre=activity_name,
                            responsable=_csv_value(row, "activity_responsable"),
                            entregable=_csv_value(row, "activity_entregable"),
                            fecha_inicial=start_date,
                            fecha_final=end_date,
                            descripcion=_csv_value(row, "activity_descripcion"),
                            recurrente=recurrente,
                            periodicidad=periodicidad,
                            cada_xx_dias=cada_xx_dias if periodicidad == "cada_xx_dias" else None,
                            entrega_estado="ninguna",
                            created_by="import_csv",
                        )
                        db.add(activity)
                        db.flush()
                        activity_by_key[activity_key] = activity
                        activity_by_code_list.setdefault(activity_code, []).append(activity)
                        summary["created"] += 1
                    continue

                if kind == "subactividad":
                    objective_code = _csv_value(row, "objective_codigo").lower()
                    activity_code = _csv_value(row, "activity_codigo").lower()
                    sub_code = _csv_value(row, "subactivity_codigo").lower()
                    if not activity_code or not sub_code:
                        raise ValueError("activity_codigo y subactivity_codigo son obligatorios para subactividad.")

                    activity = None
                    if objective_code:
                        objective = objective_by_code.get(objective_code)
                        if objective:
                            activity = activity_by_key.get(f"{int(objective.id)}::{activity_code}")
                    if activity is None:
                        candidates = activity_by_code_list.get(activity_code, [])
                        if len(candidates) == 1:
                            activity = candidates[0]
                    if activity is None:
                        raise ValueError("No se encontró la actividad destino para esta subactividad.")

                    sub_map = sub_by_activity_code.setdefault(activity_code, {})
                    sub = sub_map.get(sub_code)
                    parent_code = _csv_value(row, "subactivity_parent_codigo").lower()
                    parent_sub = sub_map.get(parent_code) if parent_code else None
                    level_raw = _parse_import_int(_csv_value(row, "subactivity_nivel"), 0)
                    level = level_raw if level_raw > 0 else ((int(parent_sub.nivel) + 1) if parent_sub else 1)
                    if level > MAX_SUBTASK_DEPTH:
                        raise ValueError(f"subactivity_nivel no puede ser mayor a {MAX_SUBTASK_DEPTH}.")
                    sub_name = _csv_value(row, "subactivity_nombre")
                    if not sub and not sub_name:
                        raise ValueError("subactivity_nombre es obligatorio al crear una subactividad.")
                    start_date = _parse_import_date(_csv_value(row, "subactivity_fecha_inicial"))
                    end_date = _parse_import_date(_csv_value(row, "subactivity_fecha_final"))
                    if (start_date and not end_date) or (end_date and not start_date):
                        raise ValueError("subactivity_fecha_inicial y subactivity_fecha_final deben definirse juntas.")
                    if start_date and end_date:
                        range_error = _validate_date_range(start_date, end_date, "Subactividad")
                        if range_error:
                            raise ValueError(range_error)
                        parent_range_error = _validate_child_date_range(
                            start_date,
                            end_date,
                            activity.fecha_inicial,
                            activity.fecha_final,
                            "Subactividad",
                            "Actividad",
                        )
                        if parent_range_error:
                            raise ValueError(parent_range_error)

                    if sub:
                        if sub_name:
                            sub.nombre = sub_name
                        sub.parent_subactivity_id = int(parent_sub.id) if parent_sub else None
                        sub.nivel = level
                        sub.responsable = _csv_value(row, "subactivity_responsable")
                        sub.entregable = _csv_value(row, "subactivity_entregable")
                        sub.fecha_inicial = start_date
                        sub.fecha_final = end_date
                        sub.descripcion = _csv_value(row, "subactivity_descripcion")
                        db.add(sub)
                        summary["updated"] += 1
                    else:
                        sub = POASubactivity(
                            activity_id=int(activity.id),
                            parent_subactivity_id=int(parent_sub.id) if parent_sub else None,
                            nivel=level,
                            codigo=sub_code,
                            nombre=sub_name,
                            responsable=_csv_value(row, "subactivity_responsable"),
                            entregable=_csv_value(row, "subactivity_entregable"),
                            fecha_inicial=start_date,
                            fecha_final=end_date,
                            descripcion=_csv_value(row, "subactivity_descripcion"),
                            assigned_by="import_csv",
                        )
                        db.add(sub)
                        db.flush()
                        sub_map[sub_code] = sub
                        summary["created"] += 1
            except Exception as row_error:
                summary["skipped"] += 1
                summary["errors"].append(f"Fila {row_index}: {row_error}")

        db.commit()
        return JSONResponse({"success": True, "summary": summary})
    except (sqlite3.OperationalError, SQLAlchemyError):
        db.rollback()
        return JSONResponse(
            {"success": False, "error": "No se pudo escribir en la base de datos (modo solo lectura o bloqueo)."},
            status_code=500,
        )
    finally:
        db.close()


@router.get("/api/strategic-identity")
def get_strategic_identity():
    _bind_core_symbols()
    db = SessionLocal()
    try:
        _ensure_strategic_identity_table(db)
        db.commit()
        rows = db.execute(
            text("SELECT bloque, payload FROM strategic_identity_config WHERE bloque IN ('mision', 'vision', 'valores')")
        ).fetchall()
        payload_map = {str(row[0] or "").strip().lower(): str(row[1] or "[]") for row in rows}
        mission_raw = payload_map.get("mision", "[]")
        vision_raw = payload_map.get("vision", "[]")
        valores_raw = payload_map.get("valores", "[]")
        try:
            mission_json = json.loads(mission_raw)
        except Exception:
            mission_json = []
        try:
            vision_json = json.loads(vision_raw)
        except Exception:
            vision_json = []
        try:
            valores_json = json.loads(valores_raw)
        except Exception:
            valores_json = []
        return JSONResponse(
            {
                "success": True,
                "data": {
                    "mision": _normalize_identity_lines(mission_json, "m"),
                    "vision": _normalize_identity_lines(vision_json, "v"),
                    "valores": _normalize_identity_lines(valores_json, "val"),
                },
            }
        )
    finally:
        db.close()


@router.get("/api/strategic-foundation")
def get_strategic_foundation():
    _bind_core_symbols()
    db = SessionLocal()
    try:
        _ensure_strategic_identity_table(db)
        db.commit()
        row = db.execute(
            text("SELECT payload FROM strategic_identity_config WHERE bloque = 'fundamentacion' LIMIT 1")
        ).fetchone()
        payload_raw = str(row[0] or "{}") if row else "{}"
        try:
            payload_json = json.loads(payload_raw)
        except Exception:
            payload_json = {}
        texto = _normalize_foundation_text(payload_json.get("texto"))
        return JSONResponse({"success": True, "data": {"texto": texto}})
    finally:
        db.close()


@router.put("/api/strategic-foundation")
def save_strategic_foundation(data: dict = Body(...)):
    _bind_core_symbols()
    texto = _normalize_foundation_text(data.get("texto"))
    encoded = json.dumps({"texto": texto}, ensure_ascii=False)
    db = SessionLocal()
    try:
        _ensure_strategic_identity_table(db)
        db.execute(
            text(
                """
                INSERT INTO strategic_identity_config (bloque, payload, updated_at)
                VALUES ('fundamentacion', :payload, CURRENT_TIMESTAMP)
                ON CONFLICT (bloque)
                DO UPDATE SET payload = EXCLUDED.payload, updated_at = CURRENT_TIMESTAMP
                """
            ),
            {"payload": encoded},
        )
        db.commit()
        return JSONResponse({"success": True, "data": {"texto": texto}})
    except (sqlite3.OperationalError, SQLAlchemyError):
        db.rollback()
        return JSONResponse(
            {"success": False, "error": "No se pudo escribir en la base de datos (modo solo lectura o bloqueo)."},
            status_code=500,
        )
    finally:
        db.close()


@router.get("/api/strategic-plan/export-doc")
def export_strategic_plan_doc():
    _bind_core_symbols()
    db = SessionLocal()
    try:
        _ensure_strategic_identity_table(db)
        db.commit()
        identity_rows = db.execute(
            text(
                "SELECT bloque, payload FROM strategic_identity_config "
                "WHERE bloque IN ('mision','vision','valores','fundamentacion')"
            )
        ).fetchall()
        payload_map = {str(row[0] or "").strip().lower(): str(row[1] or "") for row in identity_rows}

        def _parse_lines(block: str, prefix: str) -> List[Dict[str, str]]:
            raw = payload_map.get(block, "[]")
            try:
                data = json.loads(raw)
            except Exception:
                data = []
            return _normalize_identity_lines(data, prefix)

        mision = _parse_lines("mision", "m")
        vision = _parse_lines("vision", "v")
        valores = _parse_lines("valores", "val")
        try:
            foundation_payload = json.loads(payload_map.get("fundamentacion", "{}") or "{}")
        except Exception:
            foundation_payload = {}
        fundamentacion_html = _normalize_foundation_text(foundation_payload.get("texto"))

        axes = (
            db.query(StrategicAxisConfig)
            .filter(StrategicAxisConfig.is_active == True)
            .order_by(StrategicAxisConfig.orden.asc(), StrategicAxisConfig.id.asc())
            .all()
        )
        axis_data = [_serialize_strategic_axis(axis) for axis in axes]
        objective_ids = [
            int(obj.get("id") or 0)
            for axis in axis_data
            for obj in (axis.get("objetivos") or [])
            if int(obj.get("id") or 0) > 0
        ]
        kpis_by_objective = _kpis_by_objective_ids(db, sorted(set(objective_ids)))

        for axis in axis_data:
            for obj in axis.get("objetivos", []):
                obj_id = int(obj.get("id") or 0)
                obj["kpis"] = kpis_by_objective.get(obj_id, [])

        def _lines_html(rows: List[Dict[str, str]]) -> str:
            if not rows:
                return "<p>N/D</p>"
            return "<ul>" + "".join(
                f"<li><strong>{escape(str(item.get('code') or '').upper())}</strong>: {escape(str(item.get('text') or ''))}</li>"
                for item in rows
            ) + "</ul>"

        axes_html_parts: List[str] = []
        for axis in axis_data:
            axis_name = escape(str(axis.get("nombre") or "Sin nombre"))
            axis_desc = str(axis.get("descripcion") or "")
            objectives = axis.get("objetivos") or []
            objectives_html: List[str] = []
            for obj in objectives:
                obj_name = escape(str(obj.get("nombre") or "Sin nombre"))
                obj_desc = str(obj.get("descripcion") or "")
                kpis = obj.get("kpis") or []
                if kpis:
                    kpi_rows = "".join(
                        "<tr>"
                        f"<td>{escape(str(k.get('nombre') or ''))}</td>"
                        f"<td>{escape(str(k.get('proposito') or ''))}</td>"
                        f"<td>{escape(str(k.get('formula') or ''))}</td>"
                        f"<td>{escape(str(k.get('periodicidad') or ''))}</td>"
                        f"<td>{escape(str(k.get('estandar') or ''))}</td>"
                        "</tr>"
                        for k in kpis
                    )
                    kpis_html = (
                        "<table class='kpi-table'>"
                        "<thead><tr><th>Nombre</th><th>Propósito</th><th>Fórmula</th><th>Periodicidad</th><th>Estándar</th></tr></thead>"
                        f"<tbody>{kpi_rows}</tbody></table>"
                    )
                else:
                    kpis_html = "<p>Sin KPIs registrados.</p>"
                objectives_html.append(
                    "<section class='objective'>"
                    f"<h4>{obj_name}</h4>"
                    f"<div class='rich'>{obj_desc or '<p>Sin descripción.</p>'}</div>"
                    "<h5>KPIs</h5>"
                    f"{kpis_html}"
                    "</section>"
                )
            axes_html_parts.append(
                "<section class='axis'>"
                f"<h2>{axis_name}</h2>"
                "<h3>Descripción</h3>"
                f"<div class='rich'>{axis_desc or '<p>Sin descripción.</p>'}</div>"
                "<h3>Objetivos estratégicos</h3>"
                f"{''.join(objectives_html) if objectives_html else '<p>Sin objetivos registrados.</p>'}"
                "</section>"
            )

        now = datetime.utcnow().strftime("%Y-%m-%d")
        html_doc = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Plan Estratégico</title>
</head>
<body>
  <section class="cover">
    <h1>Plan estratégico</h1>
    <p class="subtitle">Edición y administración del plan estratégico de la institución</p>
    <p class="date">Fecha de exportación: {escape(now)}</p>
  </section>

  <section class="page-break">
    <h2>Misión, Visión y Valores</h2>
    <h3>Misión</h3>
    {_lines_html(mision)}
    <h3>Visión</h3>
    {_lines_html(vision)}
    <h3>Valores</h3>
    {_lines_html(valores)}
  </section>

  <section class="page-break">
    <h2>Fundamentación</h2>
    <div class="rich">{fundamentacion_html or '<p>Sin fundamentación registrada.</p>'}</div>
  </section>

  <section class="page-break">
    <h2>Ejes estratégicos</h2>
    {''.join(axes_html_parts) if axes_html_parts else '<p>Sin ejes estratégicos registrados.</p>'}
  </section>
</body>
</html>"""
        filename = f"plan_estrategico_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.doc"
        return Response(
            content=html_doc,
            media_type="application/msword; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    finally:
        db.close()


@router.put("/api/strategic-identity/{bloque}")
def save_strategic_identity_block(bloque: str, data: dict = Body(...)):
    _bind_core_symbols()
    block = str(bloque or "").strip().lower()
    if block not in {"mision", "vision", "valores"}:
        return JSONResponse({"success": False, "error": "Bloque inválido"}, status_code=400)
    prefix = "m" if block == "mision" else ("v" if block == "vision" else "val")
    lines = _normalize_identity_lines(data.get("lineas"), prefix)
    encoded = json.dumps(lines, ensure_ascii=False)
    db = SessionLocal()
    try:
        _ensure_strategic_identity_table(db)
        db.execute(
            text(
                """
                INSERT INTO strategic_identity_config (bloque, payload, updated_at)
                VALUES (:bloque, :payload, CURRENT_TIMESTAMP)
                ON CONFLICT (bloque)
                DO UPDATE SET payload = EXCLUDED.payload, updated_at = CURRENT_TIMESTAMP
                """
            ),
            {"bloque": block, "payload": encoded},
        )
        db.commit()
        return JSONResponse({"success": True, "data": {"bloque": block, "lineas": lines}})
    except (sqlite3.OperationalError, SQLAlchemyError):
        db.rollback()
        return JSONResponse(
            {"success": False, "error": "No se pudo escribir en la base de datos (modo solo lectura o bloqueo)."},
            status_code=500,
        )
    finally:
        db.close()


@router.delete("/api/strategic-identity/{bloque}")
def clear_strategic_identity_block(bloque: str):
    _bind_core_symbols()
    block = str(bloque or "").strip().lower()
    if block not in {"mision", "vision", "valores"}:
        return JSONResponse({"success": False, "error": "Bloque inválido"}, status_code=400)
    prefix = "m" if block == "mision" else ("v" if block == "vision" else "val")
    lines = _normalize_identity_lines([], prefix)
    encoded = json.dumps(lines, ensure_ascii=False)
    db = SessionLocal()
    try:
        _ensure_strategic_identity_table(db)
        db.execute(
            text(
                """
                INSERT INTO strategic_identity_config (bloque, payload, updated_at)
                VALUES (:bloque, :payload, CURRENT_TIMESTAMP)
                ON CONFLICT (bloque)
                DO UPDATE SET payload = EXCLUDED.payload, updated_at = CURRENT_TIMESTAMP
                """
            ),
            {"bloque": block, "payload": encoded},
        )
        db.commit()
        return JSONResponse({"success": True, "data": {"bloque": block, "lineas": lines}})
    except (sqlite3.OperationalError, SQLAlchemyError):
        db.rollback()
        return JSONResponse(
            {"success": False, "error": "No se pudo escribir en la base de datos (modo solo lectura o bloqueo)."},
            status_code=500,
        )
    finally:
        db.close()


@router.get("/api/strategic-axes")
def list_strategic_axes(request: Request):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        axes = (
            db.query(StrategicAxisConfig)
            .filter(StrategicAxisConfig.is_active == True)
            .order_by(StrategicAxisConfig.orden.asc(), StrategicAxisConfig.id.asc())
            .all()
        )
        if not axes:
            axes = (
                db.query(StrategicAxisConfig)
                .order_by(StrategicAxisConfig.orden.asc(), StrategicAxisConfig.id.asc())
                .all()
            )
        payload_axes = [_serialize_strategic_axis(axis) for axis in axes]
        objective_ids: List[int] = []
        for axis_data in payload_axes:
            for obj in axis_data.get("objetivos", []):
                obj_id = int(obj.get("id") or 0)
                if obj_id:
                    objective_ids.append(obj_id)
        objective_ids = sorted(set(objective_ids))
        kpis_by_objective = _kpis_by_objective_ids(db, objective_ids)
        milestones_by_objective = _milestones_by_objective_ids(db, objective_ids)
        for axis_data in payload_axes:
            for obj in axis_data.get("objetivos", []):
                obj_id = int(obj.get("id") or 0)
                obj["kpis"] = kpis_by_objective.get(obj_id, [])
                obj["hitos"] = milestones_by_objective.get(obj_id, [])
                if obj["hitos"]:
                    obj["hito"] = str(obj["hitos"][0].get("nombre") or obj.get("hito") or "")
        activities = (
            db.query(POAActivity)
            .filter(POAActivity.objective_id.in_(objective_ids))
            .all()
            if objective_ids else []
        )
        activity_ids = [int(item.id) for item in activities if getattr(item, "id", None)]
        subactivities = (
            db.query(POASubactivity)
            .filter(POASubactivity.activity_id.in_(activity_ids))
            .all()
            if activity_ids else []
        )
        sub_by_activity: Dict[int, List[POASubactivity]] = {}
        for sub in subactivities:
            sub_by_activity.setdefault(int(sub.activity_id), []).append(sub)

        today = datetime.utcnow().date()
        activity_progress_by_objective: Dict[int, List[int]] = {}
        for activity in activities:
            subs = sub_by_activity.get(int(activity.id), [])
            if subs:
                done_subs = sum(1 for sub in subs if sub.fecha_final and today >= sub.fecha_final)
                progress = int(round((done_subs / len(subs)) * 100))
            else:
                progress = 100 if _activity_status(activity) == "Terminada" else 0
            activity_progress_by_objective.setdefault(int(activity.objective_id), []).append(progress)

        mv_agg: Dict[str, List[int]] = {}
        for axis_data in payload_axes:
            objective_progress: List[int] = []
            for obj in axis_data.get("objetivos", []):
                obj_id = int(obj.get("id") or 0)
                progress_list = activity_progress_by_objective.get(obj_id, [])
                obj_progress = int(round(sum(progress_list) / len(progress_list))) if progress_list else 0
                obj["avance"] = obj_progress
                objective_progress.append(obj_progress)
            axis_progress = int(round(sum(objective_progress) / len(objective_progress))) if objective_progress else 0
            axis_data["avance"] = axis_progress
            base_code = "".join(ch for ch in str(axis_data.get("codigo") or "").split("-", 1)[0].lower() if ch.isalnum())
            axis_data["base_code"] = base_code
            if base_code:
                mv_agg.setdefault(base_code, []).append(axis_progress)

        mv_data = [
            {"code": code, "avance": int(round(sum(values) / len(values))) if values else 0}
            for code, values in sorted(mv_agg.items(), key=lambda item: item[0])
        ]
        return JSONResponse({"success": True, "data": payload_axes, "mision_vision_avance": mv_data})
    finally:
        db.close()


@router.get("/api/strategic-axes/departments")
def list_strategic_axis_departments():
    _bind_core_symbols()
    db = SessionLocal()
    try:
        departments = []
        rows = (
            db.query(Usuario.departamento)
            .filter(Usuario.departamento.isnot(None))
            .all()
        )
        for row in rows:
            value = (row[0] or "").strip()
            if value:
                departments.append(value)
        unique_departments = sorted(set(departments), key=lambda item: item.lower())
        return JSONResponse({"success": True, "data": unique_departments})
    finally:
        db.close()


@router.get("/api/strategic-axes/collaborators-by-department")
def list_collaborators_by_department(department: str = Query(default="")):
    _bind_core_symbols()
    dep = (department or "").strip()
    if not dep:
        return JSONResponse({"success": True, "data": []})
    db = SessionLocal()
    try:
        rows = (
            db.query(Usuario.nombre)
            .filter(Usuario.departamento == dep)
            .all()
        )
        collaborators = []
        for row in rows:
            value = (row[0] or "").strip()
            if value:
                collaborators.append(value)
        unique_collaborators = sorted(set(collaborators), key=lambda item: item.lower())
        return JSONResponse({"success": True, "data": unique_collaborators})
    finally:
        db.close()


@router.get("/api/strategic-axes/{axis_id}/collaborators")
def list_strategic_axis_collaborators(axis_id: int):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        axis = db.query(StrategicAxisConfig).filter(StrategicAxisConfig.id == axis_id).first()
        if not axis:
            return JSONResponse({"success": False, "error": "Eje no encontrado"}, status_code=404)
        department = (axis.lider_departamento or "").strip()
        if not department:
            return JSONResponse({"success": True, "data": []})
        rows = (
            db.query(Usuario.nombre)
            .filter(Usuario.departamento == department)
            .all()
        )
        collaborators = []
        for row in rows:
            value = (row[0] or "").strip()
            if value:
                collaborators.append(value)
        unique_collaborators = sorted(set(collaborators), key=lambda item: item.lower())
        return JSONResponse({"success": True, "data": unique_collaborators})
    finally:
        db.close()


@router.post("/api/strategic-axes")
def create_strategic_axis(request: Request, data: dict = Body(...)):
    _bind_core_symbols()
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        return JSONResponse({"success": False, "error": "El nombre del eje es obligatorio"}, status_code=400)

    db = SessionLocal()
    try:
        max_order = db.query(func.max(StrategicAxisConfig.orden)).scalar() or 0
        axis_order = int(data.get("orden") or (max_order + 1))
        start_date, start_error = _parse_date_field(data.get("fecha_inicial"), "Fecha inicial", required=False)
        if start_error:
            return JSONResponse({"success": False, "error": start_error}, status_code=400)
        end_date, end_error = _parse_date_field(data.get("fecha_final"), "Fecha final", required=False)
        if end_error:
            return JSONResponse({"success": False, "error": end_error}, status_code=400)
        if (start_date and not end_date) or (end_date and not start_date):
            return JSONResponse(
                {"success": False, "error": "Eje estratégico: fecha inicial y fecha final deben definirse juntas"},
                status_code=400,
            )
        if start_date and end_date:
            range_error = _validate_date_range(start_date, end_date, "Eje estratégico")
            if range_error:
                return JSONResponse({"success": False, "error": range_error}, status_code=400)
        base_code = (data.get("base_code") or "").strip()
        if not base_code:
            raw_code = (data.get("codigo") or "").strip().lower()
            base_code = raw_code.split("-", 1)[0] if "-" in raw_code else raw_code
        axis = StrategicAxisConfig(
            nombre=nombre,
            codigo=_compose_axis_code(base_code, axis_order),
            lider_departamento=(data.get("lider_departamento") or "").strip(),
            responsabilidad_directa=(data.get("responsabilidad_directa") or "").strip(),
            fecha_inicial=start_date,
            fecha_final=end_date,
            descripcion=(data.get("descripcion") or "").strip(),
            orden=axis_order,
            is_active=True,
        )
        db.add(axis)
        db.commit()
        db.refresh(axis)
        return JSONResponse({"success": True, "data": _serialize_strategic_axis(axis)})
    except (sqlite3.OperationalError, SQLAlchemyError):
        db.rollback()
        return JSONResponse(
            {"success": False, "error": "No se pudo escribir en la base de datos (modo solo lectura o bloqueo)."},
            status_code=500,
        )
    finally:
        db.close()


@router.put("/api/strategic-axes/{axis_id}")
def update_strategic_axis(axis_id: int, data: dict = Body(...)):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        axis = db.query(StrategicAxisConfig).filter(StrategicAxisConfig.id == axis_id).first()
        if not axis:
            return JSONResponse({"success": False, "error": "Eje no encontrado"}, status_code=404)
        nombre = (data.get("nombre") or "").strip()
        if not nombre:
            return JSONResponse({"success": False, "error": "El nombre del eje es obligatorio"}, status_code=400)
        axis_order = int(data.get("orden") or axis.orden or 1)
        start_date, start_error = _parse_date_field(data.get("fecha_inicial"), "Fecha inicial", required=False)
        if start_error:
            return JSONResponse({"success": False, "error": start_error}, status_code=400)
        end_date, end_error = _parse_date_field(data.get("fecha_final"), "Fecha final", required=False)
        if end_error:
            return JSONResponse({"success": False, "error": end_error}, status_code=400)
        if (start_date and not end_date) or (end_date and not start_date):
            return JSONResponse(
                {"success": False, "error": "Eje estratégico: fecha inicial y fecha final deben definirse juntas"},
                status_code=400,
            )
        if start_date and end_date:
            range_error = _validate_date_range(start_date, end_date, "Eje estratégico")
            if range_error:
                return JSONResponse({"success": False, "error": range_error}, status_code=400)
        base_code = (data.get("base_code") or "").strip()
        if not base_code:
            raw_code = (data.get("codigo") or axis.codigo or "").strip().lower()
            base_code = raw_code.split("-", 1)[0] if "-" in raw_code else raw_code
        axis.nombre = nombre
        axis.codigo = _compose_axis_code(base_code, axis_order)
        axis.lider_departamento = (data.get("lider_departamento") or "").strip()
        axis.responsabilidad_directa = (data.get("responsabilidad_directa") or "").strip()
        axis.fecha_inicial = start_date
        axis.fecha_final = end_date
        axis.descripcion = (data.get("descripcion") or "").strip()
        axis.orden = axis_order
        db.add(axis)
        db.commit()
        db.refresh(axis)
        return JSONResponse({"success": True, "data": _serialize_strategic_axis(axis)})
    except (sqlite3.OperationalError, SQLAlchemyError):
        db.rollback()
        return JSONResponse(
            {"success": False, "error": "No se pudo escribir en la base de datos (modo solo lectura o bloqueo)."},
            status_code=500,
        )
    finally:
        db.close()


@router.delete("/api/strategic-axes/{axis_id}")
def delete_strategic_axis(axis_id: int):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        axis = db.query(StrategicAxisConfig).filter(StrategicAxisConfig.id == axis_id).first()
        if not axis:
            return JSONResponse({"success": False, "error": "Eje no encontrado"}, status_code=404)
        db.delete(axis)
        db.commit()
        return JSONResponse({"success": True})
    except (sqlite3.OperationalError, SQLAlchemyError):
        db.rollback()
        return JSONResponse(
            {"success": False, "error": "No se pudo escribir en la base de datos (modo solo lectura o bloqueo)."},
            status_code=500,
        )
    finally:
        db.close()


@router.post("/api/strategic-axes/{axis_id}/objectives")
def create_strategic_objective(axis_id: int, data: dict = Body(...)):
    _bind_core_symbols()
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        return JSONResponse({"success": False, "error": "El nombre del objetivo es obligatorio"}, status_code=400)
    db = SessionLocal()
    try:
        axis = db.query(StrategicAxisConfig).filter(StrategicAxisConfig.id == axis_id).first()
        if not axis:
            return JSONResponse({"success": False, "error": "Eje no encontrado"}, status_code=404)
        start_date, start_error = _parse_date_field(data.get("fecha_inicial"), "Fecha inicial", required=False)
        if start_error:
            return JSONResponse({"success": False, "error": start_error}, status_code=400)
        end_date, end_error = _parse_date_field(data.get("fecha_final"), "Fecha final", required=False)
        if end_error:
            return JSONResponse({"success": False, "error": end_error}, status_code=400)
        if (start_date and not end_date) or (end_date and not start_date):
            return JSONResponse(
                {"success": False, "error": "Objetivo: fecha inicial y fecha final deben definirse juntas"},
                status_code=400,
            )
        if start_date and end_date:
            range_error = _validate_date_range(start_date, end_date, "Objetivo")
            if range_error:
                return JSONResponse({"success": False, "error": range_error}, status_code=400)
        objective_leader = (data.get("lider") or "").strip()
        axis_department = (axis.lider_departamento or "").strip()
        if objective_leader and axis_department:
            if not _collaborator_belongs_to_department(db, objective_leader, axis_department):
                return JSONResponse(
                    {
                        "success": False,
                        "error": "El líder debe pertenecer al personal del área/departamento del eje.",
                    },
                    status_code=400,
                )
        max_order = (
            db.query(func.max(StrategicObjectiveConfig.orden))
            .filter(StrategicObjectiveConfig.eje_id == axis_id)
            .scalar()
            or 0
        )
        objective_order = int(data.get("orden") or (max_order + 1))
        objective = StrategicObjectiveConfig(
            eje_id=axis_id,
            codigo=_compose_objective_code(axis.codigo or "", objective_order),
            nombre=nombre,
            hito=(data.get("hito") or "").strip(),
            lider=objective_leader,
            fecha_inicial=start_date,
            fecha_final=end_date,
            descripcion=(data.get("descripcion") or "").strip(),
            orden=objective_order,
            is_active=True,
        )
        db.add(objective)
        db.commit()
        db.refresh(objective)
        milestone_rows: List[Dict[str, Any]] = []
        if "hitos" in data:
            milestone_rows = _replace_objective_milestones(db, int(objective.id), data.get("hitos"))
            if milestone_rows:
                objective.hito = str(milestone_rows[0].get("nombre") or "").strip()
                db.add(objective)
                db.commit()
                db.refresh(objective)
        if "kpis" in data:
            _replace_objective_kpis(db, int(objective.id), data.get("kpis"))
            db.commit()
        payload = _serialize_strategic_objective(objective)
        if "hitos" in data:
            payload["hitos"] = milestone_rows
            if milestone_rows:
                payload["hito"] = str(milestone_rows[0].get("nombre") or "")
        return JSONResponse({"success": True, "data": payload})
    except (sqlite3.OperationalError, SQLAlchemyError):
        db.rollback()
        return JSONResponse(
            {"success": False, "error": "No se pudo escribir en la base de datos (modo solo lectura o bloqueo)."},
            status_code=500,
        )
    finally:
        db.close()


@router.put("/api/strategic-objectives/{objective_id}")
def update_strategic_objective(objective_id: int, data: dict = Body(...)):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        objective = db.query(StrategicObjectiveConfig).filter(StrategicObjectiveConfig.id == objective_id).first()
        if not objective:
            return JSONResponse({"success": False, "error": "Objetivo no encontrado"}, status_code=404)
        nombre = (data.get("nombre") or "").strip()
        if not nombre:
            return JSONResponse({"success": False, "error": "El nombre del objetivo es obligatorio"}, status_code=400)
        start_date, start_error = _parse_date_field(data.get("fecha_inicial"), "Fecha inicial", required=False)
        if start_error:
            return JSONResponse({"success": False, "error": start_error}, status_code=400)
        end_date, end_error = _parse_date_field(data.get("fecha_final"), "Fecha final", required=False)
        if end_error:
            return JSONResponse({"success": False, "error": end_error}, status_code=400)
        if (start_date and not end_date) or (end_date and not start_date):
            return JSONResponse(
                {"success": False, "error": "Objetivo: fecha inicial y fecha final deben definirse juntas"},
                status_code=400,
            )
        if start_date and end_date:
            range_error = _validate_date_range(start_date, end_date, "Objetivo")
            if range_error:
                return JSONResponse({"success": False, "error": range_error}, status_code=400)
        axis = db.query(StrategicAxisConfig).filter(StrategicAxisConfig.id == objective.eje_id).first()
        objective_leader = (data.get("lider") or "").strip()
        axis_department = (axis.lider_departamento or "").strip() if axis else ""
        if objective_leader and axis_department:
            if not _collaborator_belongs_to_department(db, objective_leader, axis_department):
                return JSONResponse(
                    {
                        "success": False,
                        "error": "El líder debe pertenecer al personal del área/departamento del eje.",
                    },
                    status_code=400,
                )
        objective_order = int(data.get("orden") or objective.orden or 1)
        objective.codigo = _compose_objective_code((axis.codigo if axis else ""), objective_order)
        objective.nombre = nombre
        objective.hito = (data.get("hito") or "").strip()
        objective.lider = objective_leader
        objective.fecha_inicial = start_date
        objective.fecha_final = end_date
        objective.descripcion = (data.get("descripcion") or "").strip()
        objective.orden = objective_order
        db.add(objective)
        milestone_rows: List[Dict[str, Any]] = []
        if "hitos" in data:
            milestone_rows = _replace_objective_milestones(db, int(objective.id), data.get("hitos"))
            objective.hito = str(milestone_rows[0].get("nombre") or "").strip() if milestone_rows else ""
            db.add(objective)
        if "kpis" in data:
            _replace_objective_kpis(db, int(objective.id), data.get("kpis"))
        db.commit()
        db.refresh(objective)
        payload = _serialize_strategic_objective(objective)
        if "hitos" in data:
            payload["hitos"] = milestone_rows
            if milestone_rows:
                payload["hito"] = str(milestone_rows[0].get("nombre") or "")
        return JSONResponse({"success": True, "data": payload})
    finally:
        db.close()


@router.delete("/api/strategic-objectives/{objective_id}")
def delete_strategic_objective(objective_id: int):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        objective = db.query(StrategicObjectiveConfig).filter(StrategicObjectiveConfig.id == objective_id).first()
        if not objective:
            return JSONResponse({"success": False, "error": "Objetivo no encontrado"}, status_code=404)
        _delete_objective_kpis(db, int(objective.id))
        _delete_objective_milestones(db, int(objective.id))
        db.delete(objective)
        db.commit()
        return JSONResponse({"success": True})
    finally:
        db.close()


def _allowed_objectives_for_user(request: Request, db) -> List[StrategicObjectiveConfig]:
    _bind_core_symbols()
    def _active_or_any_objectives() -> List[StrategicObjectiveConfig]:
        active_rows = (
            db.query(StrategicObjectiveConfig)
            .filter(StrategicObjectiveConfig.is_active == True)
            .order_by(StrategicObjectiveConfig.orden.asc(), StrategicObjectiveConfig.id.asc())
            .all()
        )
        if active_rows:
            return active_rows
        return (
            db.query(StrategicObjectiveConfig)
            .order_by(StrategicObjectiveConfig.orden.asc(), StrategicObjectiveConfig.id.asc())
            .all()
        )

    if _is_request_admin_like(request, db):
        return _active_or_any_objectives()

    poa_access_level = _poa_access_level_for_request(request, db)
    if poa_access_level == "todas_tareas":
        return _active_or_any_objectives()

    session_username = (getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "").strip()
    user = _current_user_record(request, db)
    aliases = _user_aliases(user, session_username)
    alias_set = {str(item or "").strip().lower() for item in aliases if str(item or "").strip()}
    if not alias_set:
        # Fallback de visualización: si no se pudo resolver identidad de sesión,
        # mostrar objetivos en modo lectura para evitar tablero vacío.
        return _active_or_any_objectives()

    objective_ids: Set[int] = set()
    own_activities = (
        db.query(POAActivity.id, POAActivity.objective_id)
        .filter(func.lower(POAActivity.responsable).in_(alias_set))
        .all()
    )
    for _aid, oid in own_activities:
        try:
            if int(oid or 0) > 0:
                objective_ids.add(int(oid))
        except Exception:
            continue
    own_subactivities = (
        db.query(POASubactivity.id, POAActivity.objective_id)
        .join(POAActivity, POAActivity.id == POASubactivity.activity_id)
        .filter(func.lower(POASubactivity.responsable).in_(alias_set))
        .all()
    )
    for _sid, oid in own_subactivities:
        try:
            if int(oid or 0) > 0:
                objective_ids.add(int(oid))
        except Exception:
            continue
    if not objective_ids:
        # Si el usuario no tiene asignaciones directas, permitir vista global (solo lectura).
        return _active_or_any_objectives()
    rows = (
        db.query(StrategicObjectiveConfig)
        .filter(
            StrategicObjectiveConfig.is_active == True,
            StrategicObjectiveConfig.id.in_(sorted(objective_ids)),
        )
        .order_by(StrategicObjectiveConfig.orden.asc(), StrategicObjectiveConfig.id.asc())
        .all()
    )
    if rows:
        return rows
    return (
        db.query(StrategicObjectiveConfig)
        .filter(StrategicObjectiveConfig.id.in_(sorted(objective_ids)))
        .order_by(StrategicObjectiveConfig.orden.asc(), StrategicObjectiveConfig.id.asc())
        .all()
    )


@router.get("/api/poa/board-data")
def poa_board_data(request: Request):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        _ensure_poa_subactivity_recurrence_columns(db)
        admin_like = _is_request_admin_like(request, db)
        objectives = _allowed_objectives_for_user(request, db)
        objective_ids = [obj.id for obj in objectives]
        objective_axis_map = {obj.id: obj.eje_id for obj in objectives}
        axis_ids = sorted(set(objective_axis_map.values()))
        axes = (
            db.query(StrategicAxisConfig)
            .filter(StrategicAxisConfig.id.in_(axis_ids))
            .all()
            if axis_ids else []
        )
        axis_name_map = {axis.id: axis.nombre for axis in axes}
        milestones_by_objective = _milestones_by_objective_ids(db, objective_ids)

        activities = (
            db.query(POAActivity)
            .filter(POAActivity.objective_id.in_(objective_ids))
            .order_by(POAActivity.id.asc())
            .all()
            if objective_ids else []
        )
        activity_ids = [item.id for item in activities]
        subactivities = (
            db.query(POASubactivity)
            .filter(POASubactivity.activity_id.in_(activity_ids))
            .order_by(POASubactivity.id.asc())
            .all()
            if activity_ids else []
        )
        sub_by_activity: Dict[int, List[POASubactivity]] = {}
        for sub in subactivities:
            sub_by_activity.setdefault(sub.activity_id, []).append(sub)
        budgets_by_activity = _budgets_by_activity_ids(db, [int(activity.id) for activity in activities if getattr(activity, "id", None)])
        deliverables_by_activity = _deliverables_by_activity_ids(db, [int(activity.id) for activity in activities if getattr(activity, "id", None)])
        impacted_milestones_by_activity = _activity_milestones_by_activity_ids(
            db,
            [int(activity.id) for activity in activities if getattr(activity, "id", None)],
        )
        session_username = (getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "").strip()
        user = _current_user_record(request, db)
        aliases = _user_aliases(user, session_username)
        alias_set = {str(item or "").strip().lower() for item in aliases if str(item or "").strip()}
        poa_access_level = _poa_access_level_for_request(request, db)
        session_role_raw = str(getattr(request.state, "user_role", None) or request.cookies.get("user_role") or "")
        session_role_normalized = normalize_role_name(session_role_raw)
        detected_role = normalize_role_name(get_current_role(request))
        if detected_role in {"administrador", "superadministrador"}:
            admin_like = True
            poa_access_level = "todas_tareas"
        objective_can_validate: Dict[int, bool] = {}
        for obj in objectives:
            leader = (obj.lider or "").strip().lower()
            objective_can_validate[int(obj.id)] = bool(leader and leader in aliases) or admin_like

        pending_approvals = (
            db.query(POADeliverableApproval)
            .filter(POADeliverableApproval.status == "pendiente")
            .order_by(POADeliverableApproval.created_at.desc())
            .all()
        )
        approvals_for_user = []
        for approval in pending_approvals:
            if not _is_user_process_owner(request, db, approval.process_owner):
                continue
            activity = next((item for item in activities if item.id == approval.activity_id), None)
            if not activity:
                activity = db.query(POAActivity).filter(POAActivity.id == approval.activity_id).first()
            objective = next((item for item in objectives if item.id == approval.objective_id), None)
            if not objective:
                objective = db.query(StrategicObjectiveConfig).filter(StrategicObjectiveConfig.id == approval.objective_id).first()
            approvals_for_user.append(
                {
                    "id": approval.id,
                    "activity_id": approval.activity_id,
                    "objective_id": approval.objective_id,
                    "process_owner": approval.process_owner or "",
                    "requester": approval.requester or "",
                    "created_at": approval.created_at.isoformat() if approval.created_at else "",
                    "activity_nombre": (activity.nombre if activity else ""),
                    "activity_codigo": (activity.codigo if activity else ""),
                    "objective_nombre": (objective.nombre if objective else ""),
                    "objective_codigo": (objective.codigo if objective else ""),
                }
            )

        return JSONResponse(
            {
                "success": True,
                "objectives": [
                    {
                        **_serialize_strategic_objective(obj),
                        "axis_name": axis_name_map.get(obj.eje_id, ""),
                        "hitos": milestones_by_objective.get(int(obj.id), []),
                        "can_validate_deliverables": bool(objective_can_validate.get(int(obj.id), False)),
                    }
                    for obj in objectives
                ],
                "activities": [
                    {
                        **_serialize_poa_activity(
                            activity,
                            sub_by_activity.get(activity.id, []),
                            budgets_by_activity.get(int(activity.id), []),
                            impacted_milestones_by_activity.get(int(activity.id), []),
                            deliverables_by_activity.get(int(activity.id), []),
                        ),
                        "can_change_status": bool((activity.responsable or "").strip().lower() in alias_set),
                    }
                    for activity in activities
                ],
                "pending_approvals": approvals_for_user,
                "permissions": {
                    "poa_access_level": poa_access_level,
                    "can_manage_content": bool(admin_like),
                    "can_view_gantt": bool(poa_access_level == "todas_tareas"),
                },
                "diagnostics": {
                    "user_name": session_username,
                    "role_raw": session_role_raw,
                    "role_normalized": session_role_normalized,
                    "role_detected": detected_role,
                    "is_admin_or_superadmin": bool(admin_like),
                    "poa_access_level": poa_access_level,
                    "objectives_count": len(objectives),
                    "activities_count": len(activities),
                },
            }
        )
    finally:
        db.close()


@router.get("/api/poa/activities/no-owner")
def poa_activities_without_owner(request: Request):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        objectives = _allowed_objectives_for_user(request, db)
        objective_ids = [obj.id for obj in objectives]
        if not objective_ids:
            return JSONResponse({"success": True, "total": 0, "data": []})
        activities = (
            db.query(POAActivity)
            .filter(POAActivity.objective_id.in_(objective_ids))
            .order_by(POAActivity.id.desc())
            .all()
        )
        objective_map = {int(obj.id): obj for obj in objectives}
        rows: List[Dict[str, Any]] = []
        for item in activities:
            if str(item.responsable or "").strip():
                continue
            objective = objective_map.get(int(item.objective_id or 0))
            rows.append(
                {
                    "activity_id": int(item.id or 0),
                    "activity_nombre": str(item.nombre or ""),
                    "activity_codigo": str(item.codigo or ""),
                    "objective_id": int(item.objective_id or 0),
                    "objective_nombre": str(getattr(objective, "nombre", "") or ""),
                    "objective_codigo": str(getattr(objective, "codigo", "") or ""),
                    "fecha_inicial": _date_to_iso(item.fecha_inicial),
                    "fecha_final": _date_to_iso(item.fecha_final),
                    "status": _activity_status(item),
                }
            )
        return JSONResponse({"success": True, "total": len(rows), "data": rows})
    finally:
        db.close()


@router.get("/api/notificaciones/resumen")
def notifications_summary(request: Request):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        today = now.date()
        tenant_id = _normalize_tenant_id(get_current_tenant(request))
        user_key = _notification_user_key(request, db)
        items: List[Dict[str, Any]] = []

        pending_approvals = (
            db.query(POADeliverableApproval)
            .filter(POADeliverableApproval.status == "pendiente")
            .order_by(POADeliverableApproval.created_at.desc())
            .all()
        )
        for approval in pending_approvals:
            if not _is_user_process_owner(request, db, approval.process_owner):
                continue
            activity = db.query(POAActivity).filter(POAActivity.id == approval.activity_id).first()
            objective = db.query(StrategicObjectiveConfig).filter(StrategicObjectiveConfig.id == approval.objective_id).first()
            items.append(
                {
                    "id": f"poa-approval-{approval.id}",
                    "kind": "poa_aprobacion",
                    "title": "Aprobación de entregable pendiente",
                    "message": (
                        f"Actividad {(activity.nombre if activity else 'sin nombre')} "
                        f"({activity.codigo if activity else ''}) - Objetivo {(objective.nombre if objective else '')}"
                    ).strip(),
                    "created_at": (approval.created_at or now).isoformat(),
                    "href": "/poa/crear",
                }
            )

        # ...línea eliminada: _can_authorize_documents(request) no existe...
            tenant_id = _get_document_tenant(request)
            docs_query = db.query(DocumentoEvidencia).filter(DocumentoEvidencia.estado.in_(["enviado", "actualizado"]))
            if is_superadmin(request):
                header_tenant = request.headers.get("x-tenant-id")
                if header_tenant and _normalize_tenant_id(header_tenant) != "all":
                    docs_query = docs_query.filter(
                        func.lower(DocumentoEvidencia.tenant_id) == _normalize_tenant_id(header_tenant).lower()
                    )
                elif not header_tenant:
                    docs_query = docs_query.filter(func.lower(DocumentoEvidencia.tenant_id) == tenant_id.lower())
            else:
                docs_query = docs_query.filter(func.lower(DocumentoEvidencia.tenant_id) == tenant_id.lower())
            docs_pending = docs_query.order_by(DocumentoEvidencia.updated_at.desc()).limit(20).all()
            for doc in docs_pending:
                items.append(
                    {
                        "id": f"doc-approval-{doc.id}",
                        "kind": "documento_autorizacion",
                        "title": "Documento pendiente de autorización",
                        "message": f"{(doc.titulo or '').strip()} · Estado: {(doc.estado or '').strip()}",
                        "created_at": (doc.updated_at or doc.enviado_at or doc.creado_at or now).isoformat(),
                        "href": "/reportes/documentos",
                    }
                )

        if is_superadmin(request):
            quiz_rows = (
                db.query(PublicQuizSubmission)
                .order_by(PublicQuizSubmission.created_at.desc(), PublicQuizSubmission.id.desc())
                .limit(20)
                .all()
            )
            for quiz in quiz_rows:
                items.append(
                    {
                        "id": f"quiz-submission-{quiz.id}",
                        "kind": "quiz_descuento",
                        "title": "Nuevo cuestionario de descuento",
                        "message": (
                            f"{(quiz.nombre or '').strip()} · {(quiz.cooperativa or '').strip()} · "
                            f"{int(quiz.correctas or 0)}/10 correctas · {int(quiz.descuento or 0)}% de descuento"
                        ),
                        "created_at": (quiz.created_at or now).isoformat(),
                        "href": "/usuarios",
                    }
                )

        session_username = (getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "").strip()
        user = _current_user_record(request, db)
        aliases = sorted(_user_aliases(user, session_username))
        if aliases:
            lookahead = today + timedelta(days=2)
            own_activities = (
                db.query(POAActivity)
                .filter(func.lower(POAActivity.responsable).in_(aliases))
                .order_by(POAActivity.fecha_final.asc(), POAActivity.id.asc())
                .all()
            )
            for activity in own_activities:
                if not activity.fecha_final:
                    continue
                if (activity.entrega_estado or "").strip().lower() == "aprobada":
                    continue
                if activity.fecha_final > lookahead:
                    continue
                delta_days = (activity.fecha_final - today).days
                if delta_days < 0:
                    title = "Tarea atrasada"
                    message = f"{activity.nombre} está atrasada desde {activity.fecha_final.isoformat()}"
                    deadline_state = "atrasada"
                elif delta_days == 0:
                    title = "Actividad vence hoy"
                    message = f"{activity.nombre} vence hoy"
                    deadline_state = "por_vencer"
                else:
                    title = "Actividad por vencer"
                    message = f"{activity.nombre} vence el {activity.fecha_final.isoformat()}"
                    deadline_state = "por_vencer"
                items.append(
                    {
                        "id": f"activity-deadline-{activity.id}",
                        "kind": "actividad_fecha",
                        "title": title,
                        "message": message,
                        "deadline_state": deadline_state,
                        "created_at": datetime.combine(activity.fecha_final, datetime.min.time()).isoformat(),
                        "href": "/poa/crear",
                    }
                )
            own_subactivities = (
                db.query(POASubactivity, POAActivity)
                .join(POAActivity, POAActivity.id == POASubactivity.activity_id)
                .filter(func.lower(POASubactivity.responsable).in_(aliases))
                .order_by(POASubactivity.fecha_final.asc(), POASubactivity.id.asc())
                .all()
            )
            for subactivity, parent_activity in own_subactivities:
                if not subactivity.fecha_final:
                    continue
                # Si la actividad ya está terminada, no generar alerta de atraso para sus subtareas.
                if _activity_status(parent_activity, today=today) == "Terminada":
                    continue
                if subactivity.fecha_final > lookahead:
                    continue
                delta_days = (subactivity.fecha_final - today).days
                if delta_days < 0:
                    title = "Tarea atrasada"
                    message = (
                        f"{subactivity.nombre} (subtarea de {parent_activity.nombre}) "
                        f"está atrasada desde {subactivity.fecha_final.isoformat()}"
                    )
                    deadline_state = "atrasada"
                elif delta_days == 0:
                    title = "Subtarea vence hoy"
                    message = f"{subactivity.nombre} vence hoy"
                    deadline_state = "por_vencer"
                else:
                    title = "Subtarea por vencer"
                    message = f"{subactivity.nombre} vence el {subactivity.fecha_final.isoformat()}"
                    deadline_state = "por_vencer"
                items.append(
                    {
                        "id": f"subactivity-deadline-{subactivity.id}",
                        "kind": "actividad_fecha",
                        "title": title,
                        "message": message,
                        "deadline_state": deadline_state,
                        "created_at": datetime.combine(subactivity.fecha_final, datetime.min.time()).isoformat(),
                        "href": f"/poa/crear?activity_id={int(parent_activity.id or 0)}&subactivity_id={int(subactivity.id or 0)}",
                    }
                )

        # Alertas IA de riesgo POA publicadas por el motor de riesgo.
        try:
            db.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS ia_poa_risk_alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        alert_key TEXT NOT NULL UNIQUE,
                        activity_id INTEGER,
                        objective_id INTEGER,
                        axis_id INTEGER,
                        severity TEXT NOT NULL,
                        risk_score REAL NOT NULL DEFAULT 0,
                        status TEXT NOT NULL DEFAULT 'active',
                        owner TEXT DEFAULT '',
                        title TEXT NOT NULL DEFAULT '',
                        message TEXT NOT NULL DEFAULT '',
                        recommendation TEXT NOT NULL DEFAULT '',
                        source TEXT NOT NULL DEFAULT 'ia_risk_engine',
                        resolved_at TEXT DEFAULT ''
                    )
                    """
                )
            )
            db.commit()
            alerts_rows = db.execute(
                text(
                    """
                    SELECT id, created_at, updated_at, severity, risk_score, title, message, recommendation
                    FROM ia_poa_risk_alerts
                    WHERE source = 'ia_risk_engine' AND status = 'active'
                    ORDER BY
                        CASE severity WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 ELSE 0 END DESC,
                        risk_score DESC,
                        updated_at DESC
                    LIMIT 20
                    """
                )
            ).fetchall()
            for row in alerts_rows:
                severity = str(row.severity or "").strip().lower()
                severity_label = "alto" if severity == "high" else ("medio" if severity == "medium" else "bajo")
                created_at_raw = str(row.updated_at or row.created_at or now.isoformat()).strip() or now.isoformat()
                items.append(
                    {
                        "id": f"ia-poa-risk-{int(row.id or 0)}",
                        "kind": "ia_riesgo_poa",
                        "title": str(row.title or "Alerta IA de riesgo POA").strip(),
                        "message": (
                            f"{str(row.message or '').strip()} · Riesgo {severity_label} · "
                            f"Recomendación: {str(row.recommendation or '').strip()}"
                        ).strip(" ·"),
                        "created_at": created_at_raw,
                        "href": "/poa/crear",
                    }
                )
        except Exception:
            db.rollback()

        # ── Alertas de KPIs fuera de umbral ───────────────────────────────────
        try:
            _ensure_kpi_mediciones_table(db)
            kpi_alert_rows = db.execute(text("""
                SELECT k.id, k.nombre, k.estandar, k.referencia,
                       m.valor, m.periodo, m.created_at
                FROM strategic_objective_kpis k
                INNER JOIN kpi_mediciones m ON m.id = (
                    SELECT id FROM kpi_mediciones
                    WHERE kpi_id = k.id ORDER BY created_at DESC LIMIT 1
                )
                WHERE k.estandar != '' AND k.referencia != ''
            """)).fetchall()
            for krow in kpi_alert_rows:
                kpi_id_v   = int(krow[0])
                nombre_v   = str(krow[1] or "")
                estandar_v = str(krow[2] or "")
                refx_v     = str(krow[3] or "")
                valor_v    = float(krow[4] or 0)
                periodo_v  = str(krow[5] or "")
                med_at_v   = str(krow[6] or "")
                kpi_status = _kpi_evaluate_status(valor_v, estandar_v, refx_v)
                if kpi_status in ("alert", "warning"):
                    sev_label = "Alerta" if kpi_status == "alert" else "Advertencia"
                    items.append({
                        "id": f"kpi-alerta-{kpi_id_v}",
                        "kind": "kpi_alerta",
                        "severity": kpi_status,
                        "title": f"{sev_label} KPI: {nombre_v}",
                        "message": (
                            f"Valor: {valor_v} · Meta ({estandar_v}): {refx_v}"
                            + (f" · Período: {periodo_v}" if periodo_v else "")
                        ),
                        "created_at": med_at_v or now.isoformat(),
                        "href": "/inicio/kpis",
                    })
        except Exception:
            db.rollback()

        items.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        limited_items = items[:25]
        notification_ids = [str(item.get("id") or "").strip() for item in limited_items if str(item.get("id") or "").strip()]
        read_ids: Set[str] = set()
        if user_key and notification_ids:
            read_rows = (
                db.query(UserNotificationRead.notification_id)
                .filter(
                    UserNotificationRead.tenant_id == tenant_id,
                    UserNotificationRead.user_key == user_key,
                    UserNotificationRead.notification_id.in_(notification_ids),
                )
                .all()
            )
            read_ids = {str(row[0]) for row in read_rows}
        for item in limited_items:
            item["read"] = str(item.get("id") or "") in read_ids

        counts = {
            "poa_aprobacion": 0,
            "documento_autorizacion": 0,
            "actividad_fecha": 0,
            "actividad_atrasada": 0,
            "actividad_por_vencer": 0,
            "quiz_descuento": 0,
            "ia_riesgo_poa": 0,
            "kpi_alerta": 0,
            "kpi_advertencia": 0,
        }
        for item in limited_items:
            kind = str(item.get("kind") or "")
            is_unread = not bool(item.get("read"))
            if kind in counts:
                counts[kind] += 1 if is_unread else 0
            if kind == "actividad_fecha" and is_unread:
                deadline_state = str(item.get("deadline_state") or "").strip().lower()
                if deadline_state == "atrasada":
                    counts["actividad_atrasada"] += 1
                elif deadline_state == "por_vencer":
                    counts["actividad_por_vencer"] += 1
            if kind == "kpi_alerta" and is_unread:
                severity = str(item.get("severity") or "").strip().lower()
                if severity == "alert":
                    counts["kpi_alerta"] += 1
                elif severity == "warning":
                    counts["kpi_advertencia"] += 1
        unread = sum(0 if item.get("read") else 1 for item in limited_items)

        return JSONResponse(
            {
                "success": True,
                "total": len(limited_items),
                "unread": unread,
                "counts": counts,
                "items": limited_items,
            }
        )
    finally:
        db.close()


@router.post("/api/notificaciones/marcar-leida")
def mark_notification_read(request: Request, data: dict = Body(default={})):
    _bind_core_symbols()
    notification_id = (data.get("id") or "").strip()
    if not notification_id:
        return JSONResponse({"success": False, "error": "ID de notificación requerido"}, status_code=400)

    db = SessionLocal()
    try:
        tenant_id = _normalize_tenant_id(get_current_tenant(request))
        user_key = _notification_user_key(request, db)
        if not user_key:
            return JSONResponse({"success": False, "error": "Usuario no autenticado"}, status_code=401)

        row = (
            db.query(UserNotificationRead)
            .filter(
                UserNotificationRead.tenant_id == tenant_id,
                UserNotificationRead.user_key == user_key,
                UserNotificationRead.notification_id == notification_id,
            )
            .first()
        )
        if row:
            row.read_at = datetime.utcnow()
            db.add(row)
        else:
            db.add(
                UserNotificationRead(
                    tenant_id=tenant_id,
                    user_key=user_key,
                    notification_id=notification_id,
                    read_at=datetime.utcnow(),
                )
            )
        db.commit()
        return JSONResponse({"success": True})
    finally:
        db.close()


@router.post("/api/notificaciones/marcar-todas-leidas")
def mark_all_notifications_read(request: Request, data: dict = Body(default={})):
    _bind_core_symbols()
    raw_ids = data.get("ids")
    ids = [str(value).strip() for value in (raw_ids if isinstance(raw_ids, list) else [])]
    ids = [value for value in ids if value][:200]

    db = SessionLocal()
    try:
        tenant_id = _normalize_tenant_id(get_current_tenant(request))
        user_key = _notification_user_key(request, db)
        if not user_key:
            return JSONResponse({"success": False, "error": "Usuario no autenticado"}, status_code=401)
        if not ids:
            return JSONResponse({"success": True, "updated": 0})

        existing = (
            db.query(UserNotificationRead)
            .filter(
                UserNotificationRead.tenant_id == tenant_id,
                UserNotificationRead.user_key == user_key,
                UserNotificationRead.notification_id.in_(ids),
            )
            .all()
        )
        existing_by_id = {row.notification_id: row for row in existing}
        now = datetime.utcnow()
        updates = 0
        for notif_id in ids:
            row = existing_by_id.get(notif_id)
            if row:
                row.read_at = now
                db.add(row)
            else:
                db.add(
                    UserNotificationRead(
                        tenant_id=tenant_id,
                        user_key=user_key,
                        notification_id=notif_id,
                        read_at=now,
                    )
                )
            updates += 1
        db.commit()
        return JSONResponse({"success": True, "updated": updates})
    finally:
        db.close()


@router.post("/api/poa/activities")
def create_poa_activity(request: Request, data: dict = Body(...)):
    _bind_core_symbols()
    objective_id = int(data.get("objective_id") or 0)
    nombre = (data.get("nombre") or "").strip()
    responsable = (data.get("responsable") or "").strip()
    entregable = (data.get("entregable") or "").strip()
    deliverables_input = data.get("entregables")
    normalized_deliverables = _normalize_deliverable_items(deliverables_input)
    if not normalized_deliverables and entregable:
        normalized_deliverables = [{"id": 0, "nombre": entregable, "validado": False, "orden": 1}]
    if not objective_id or not nombre or not normalized_deliverables:
        return JSONResponse(
            {"success": False, "error": "Objetivo, nombre y al menos un entregable son obligatorios"},
            status_code=400,
        )
    start_date, start_error = _parse_date_field(data.get("fecha_inicial"), "Fecha inicial", required=True)
    if start_error:
        return JSONResponse({"success": False, "error": start_error}, status_code=400)
    end_date, end_error = _parse_date_field(data.get("fecha_final"), "Fecha final", required=True)
    if end_error:
        return JSONResponse({"success": False, "error": end_error}, status_code=400)
    range_error = _validate_date_range(start_date, end_date, "Actividad")
    if range_error:
        return JSONResponse({"success": False, "error": range_error}, status_code=400)
    recurrente = bool(data.get("recurrente"))
    periodicidad = (data.get("periodicidad") or "").strip().lower()
    try:
        cada_xx_dias = int(data.get("cada_xx_dias") or 0)
    except (TypeError, ValueError):
        return JSONResponse({"success": False, "error": "Cada xx días debe ser un número válido"}, status_code=400)
    if recurrente:
        if periodicidad not in VALID_ACTIVITY_PERIODICITIES:
            return JSONResponse({"success": False, "error": "Selecciona una periodicidad válida"}, status_code=400)
        if periodicidad == "cada_xx_dias":
            if cada_xx_dias <= 0:
                return JSONResponse({"success": False, "error": "Cada xx días debe ser mayor a 0"}, status_code=400)
    else:
        periodicidad = ""
        cada_xx_dias = 0
    impacted_milestone_ids = _normalize_impacted_milestone_ids(data.get("impacted_milestone_ids"))

    db = SessionLocal()
    try:
        admin_like = _is_request_admin_like(request, db)
        if not admin_like:
            return JSONResponse({"success": False, "error": "Solo administrador puede crear actividades"}, status_code=403)
        allowed_ids = {obj.id for obj in _allowed_objectives_for_user(request, db)}
        if objective_id not in allowed_ids and not admin_like:
            return JSONResponse({"success": False, "error": "No autorizado para este objetivo"}, status_code=403)
        objective = db.query(StrategicObjectiveConfig).filter(StrategicObjectiveConfig.id == objective_id).first()
        if not objective:
            return JSONResponse({"success": False, "error": "Objetivo no encontrado"}, status_code=404)
        session_username = (getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "").strip()
        user = _current_user_record(request, db)
        aliases = _user_aliases(user, session_username)
        can_validate_deliverables = bool((objective.lider or "").strip().lower() in aliases) or admin_like
        if not can_validate_deliverables:
            normalized_deliverables = [{**item, "validado": False} for item in normalized_deliverables]
        valid_milestone_ids = {int(item.get("id") or 0) for item in _milestones_by_objective_ids(db, [objective_id]).get(objective_id, [])}
        invalid_milestones = [mid for mid in impacted_milestone_ids if mid not in valid_milestone_ids]
        if invalid_milestones:
            return JSONResponse(
                {"success": False, "error": "Los hitos seleccionados no pertenecen al objetivo."},
                status_code=400,
            )
        parent_error = _validate_child_date_range(
            start_date,
            end_date,
            objective.fecha_inicial,
            objective.fecha_final,
            "Actividad",
            "Objetivo",
        )
        if parent_error:
            return JSONResponse({"success": False, "error": parent_error}, status_code=400)
        created_by = session_username
        activity = POAActivity(
            objective_id=objective_id,
            nombre=nombre,
            codigo=(data.get("codigo") or "").strip(),
            responsable=responsable,
            entregable=str(normalized_deliverables[0].get("nombre") or "").strip(),
            fecha_inicial=start_date,
            fecha_final=end_date,
            inicio_forzado=bool(data.get("inicio_forzado")),
            descripcion=(data.get("descripcion") or "").strip(),
            recurrente=recurrente,
            periodicidad=periodicidad,
            cada_xx_dias=(cada_xx_dias if periodicidad == "cada_xx_dias" else None),
            created_by=created_by,
        )
        db.add(activity)
        db.commit()
        db.refresh(activity)
        budget_rows: List[Dict[str, Any]] = []
        linked_milestones: List[Dict[str, Any]] = []
        deliverable_rows: List[Dict[str, Any]] = _replace_activity_deliverables(db, int(activity.id), normalized_deliverables)
        if "budget_items" in data:
            budget_rows = _replace_activity_budgets(db, int(activity.id), data.get("budget_items"))
        if "impacted_milestone_ids" in data:
            _replace_activity_milestone_links(db, int(activity.id), impacted_milestone_ids)
            linked_milestones = _activity_milestones_by_activity_ids(db, [int(activity.id)]).get(int(activity.id), [])
            db.commit()
        return JSONResponse({"success": True, "data": _serialize_poa_activity(activity, [], budget_rows, linked_milestones, deliverable_rows)})
    finally:
        db.close()


@router.put("/api/poa/activities/{activity_id}")
def update_poa_activity(request: Request, activity_id: int, data: dict = Body(...)):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        admin_like = _is_request_admin_like(request, db)
        if not admin_like:
            return JSONResponse({"success": False, "error": "Solo administrador puede editar actividades"}, status_code=403)
        activity = db.query(POAActivity).filter(POAActivity.id == activity_id).first()
        if not activity:
            return JSONResponse({"success": False, "error": "Actividad no encontrada"}, status_code=404)
        allowed_ids = {obj.id for obj in _allowed_objectives_for_user(request, db)}
        if activity.objective_id not in allowed_ids and not admin_like:
            return JSONResponse({"success": False, "error": "No autorizado para editar esta actividad"}, status_code=403)
        nombre = (data.get("nombre") or "").strip()
        responsable = (data.get("responsable") or "").strip()
        entregable = (data.get("entregable") or "").strip()
        deliverables_input = data.get("entregables")
        normalized_deliverables = _normalize_deliverable_items(deliverables_input)
        if not normalized_deliverables and entregable:
            normalized_deliverables = [{"id": 0, "nombre": entregable, "validado": False, "orden": 1}]
        if not nombre or not normalized_deliverables:
            return JSONResponse(
                {"success": False, "error": "Nombre y al menos un entregable son obligatorios"},
                status_code=400,
            )
        start_date, start_error = _parse_date_field(data.get("fecha_inicial"), "Fecha inicial", required=True)
        if start_error:
            return JSONResponse({"success": False, "error": start_error}, status_code=400)
        end_date, end_error = _parse_date_field(data.get("fecha_final"), "Fecha final", required=True)
        if end_error:
            return JSONResponse({"success": False, "error": end_error}, status_code=400)
        range_error = _validate_date_range(start_date, end_date, "Actividad")
        if range_error:
            return JSONResponse({"success": False, "error": range_error}, status_code=400)
        recurrente = bool(data.get("recurrente"))
        periodicidad = (data.get("periodicidad") or "").strip().lower()
        try:
            cada_xx_dias = int(data.get("cada_xx_dias") or 0)
        except (TypeError, ValueError):
            return JSONResponse({"success": False, "error": "Cada xx días debe ser un número válido"}, status_code=400)
        if recurrente:
            if periodicidad not in VALID_ACTIVITY_PERIODICITIES:
                return JSONResponse({"success": False, "error": "Selecciona una periodicidad válida"}, status_code=400)
            if periodicidad == "cada_xx_dias":
                if cada_xx_dias <= 0:
                    return JSONResponse({"success": False, "error": "Cada xx días debe ser mayor a 0"}, status_code=400)
        else:
            periodicidad = ""
            cada_xx_dias = 0
        impacted_milestone_ids = _normalize_impacted_milestone_ids(data.get("impacted_milestone_ids"))
        objective = db.query(StrategicObjectiveConfig).filter(StrategicObjectiveConfig.id == activity.objective_id).first()
        if not objective:
            return JSONResponse({"success": False, "error": "Objetivo no encontrado"}, status_code=404)
        session_username = (getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "").strip()
        user = _current_user_record(request, db)
        aliases = _user_aliases(user, session_username)
        can_validate_deliverables = bool((objective.lider or "").strip().lower() in aliases) or admin_like
        if not can_validate_deliverables:
            normalized_deliverables = [{**item, "validado": False} for item in normalized_deliverables]
        valid_milestone_ids = {int(item.get("id") or 0) for item in _milestones_by_objective_ids(db, [int(objective.id)]).get(int(objective.id), [])}
        invalid_milestones = [mid for mid in impacted_milestone_ids if mid not in valid_milestone_ids]
        if invalid_milestones:
            return JSONResponse(
                {"success": False, "error": "Los hitos seleccionados no pertenecen al objetivo."},
                status_code=400,
            )
        parent_error = _validate_child_date_range(
            start_date,
            end_date,
            objective.fecha_inicial,
            objective.fecha_final,
            "Actividad",
            "Objetivo",
        )
        if parent_error:
            return JSONResponse({"success": False, "error": parent_error}, status_code=400)
        activity.nombre = nombre
        activity.codigo = (data.get("codigo") or "").strip()
        activity.responsable = responsable
        activity.entregable = str(normalized_deliverables[0].get("nombre") or "").strip()
        activity.fecha_inicial = start_date
        activity.fecha_final = end_date
        activity.inicio_forzado = bool(data.get("inicio_forzado")) if "inicio_forzado" in data else bool(activity.inicio_forzado)
        activity.descripcion = (data.get("descripcion") or "").strip()
        activity.recurrente = recurrente
        activity.periodicidad = periodicidad
        activity.cada_xx_dias = cada_xx_dias if periodicidad == "cada_xx_dias" else None
        db.add(activity)
        budget_rows: List[Dict[str, Any]] = []
        linked_milestones: List[Dict[str, Any]] = []
        deliverable_rows: List[Dict[str, Any]] = _replace_activity_deliverables(db, int(activity.id), normalized_deliverables)
        if "budget_items" in data:
            budget_rows = _replace_activity_budgets(db, int(activity.id), data.get("budget_items"))
        if "impacted_milestone_ids" in data:
            _replace_activity_milestone_links(db, int(activity.id), impacted_milestone_ids)
        db.commit()
        db.refresh(activity)
        subs = db.query(POASubactivity).filter(POASubactivity.activity_id == activity.id).all()
        if not budget_rows:
            budget_rows = _budgets_by_activity_ids(db, [int(activity.id)]).get(int(activity.id), [])
        if not deliverable_rows:
            deliverable_rows = _deliverables_by_activity_ids(db, [int(activity.id)]).get(int(activity.id), [])
        linked_milestones = _activity_milestones_by_activity_ids(db, [int(activity.id)]).get(int(activity.id), [])
        return JSONResponse({"success": True, "data": _serialize_poa_activity(activity, subs, budget_rows, linked_milestones, deliverable_rows)})
    finally:
        db.close()


@router.delete("/api/poa/activities/{activity_id}")
def delete_poa_activity(request: Request, activity_id: int):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        admin_like = _is_request_admin_like(request, db)
        if not admin_like:
            return JSONResponse({"success": False, "error": "Solo administrador puede eliminar actividades"}, status_code=403)
        activity = db.query(POAActivity).filter(POAActivity.id == activity_id).first()
        if not activity:
            return JSONResponse({"success": False, "error": "Actividad no encontrada"}, status_code=404)
        allowed_ids = {obj.id for obj in _allowed_objectives_for_user(request, db)}
        if activity.objective_id not in allowed_ids and not admin_like:
            return JSONResponse({"success": False, "error": "No autorizado para eliminar esta actividad"}, status_code=403)
        db.query(POASubactivity).filter(POASubactivity.activity_id == activity.id).delete()
        _delete_activity_budgets(db, int(activity.id))
        _delete_activity_deliverables(db, int(activity.id))
        _delete_activity_milestone_links(db, int(activity.id))
        db.delete(activity)
        db.commit()
        return JSONResponse({"success": True})
    finally:
        db.close()


@router.post("/api/poa/activities/{activity_id}/mark-in-progress")
def mark_poa_activity_in_progress(request: Request, activity_id: int):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        admin_like = _is_request_admin_like(request, db)
        activity = db.query(POAActivity).filter(POAActivity.id == activity_id).first()
        if not activity:
            return JSONResponse({"success": False, "error": "Actividad no encontrada"}, status_code=404)
        allowed_ids = {obj.id for obj in _allowed_objectives_for_user(request, db)}
        if activity.objective_id not in allowed_ids and not admin_like:
            return JSONResponse({"success": False, "error": "No autorizado para esta actividad"}, status_code=403)
        session_username = (getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "").strip()
        user = _current_user_record(request, db)
        aliases = _user_aliases(user, session_username)
        is_activity_owner = (activity.responsable or "").strip().lower() in aliases
        if not is_activity_owner:
            return JSONResponse({"success": False, "error": "Solo el responsable puede habilitar en proceso"}, status_code=403)
        if (activity.entrega_estado or "").strip().lower() == "aprobada":
            return JSONResponse({"success": False, "error": "La actividad ya está aprobada y terminada"}, status_code=409)
        activity.inicio_forzado = True
        if (activity.entrega_estado or "").strip().lower() == "rechazada":
            activity.entrega_estado = "ninguna"
        db.add(activity)
        db.commit()
        db.refresh(activity)
        subs = db.query(POASubactivity).filter(POASubactivity.activity_id == activity.id).all()
        return JSONResponse({"success": True, "data": _serialize_poa_activity(activity, subs)})
    finally:
        db.close()


@router.post("/api/poa/activities/{activity_id}/mark-finished")
def mark_poa_activity_finished(request: Request, activity_id: int, data: dict = Body(default={})):
    _bind_core_symbols()
    send_review = bool(data.get("enviar_revision"))
    db = SessionLocal()
    try:
        admin_like = _is_request_admin_like(request, db)
        activity = db.query(POAActivity).filter(POAActivity.id == activity_id).first()
        if not activity:
            return JSONResponse({"success": False, "error": "Actividad no encontrada"}, status_code=404)
        allowed_ids = {obj.id for obj in _allowed_objectives_for_user(request, db)}
        if activity.objective_id not in allowed_ids and not admin_like:
            return JSONResponse({"success": False, "error": "No autorizado para esta actividad"}, status_code=403)
        session_username = (getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "").strip()
        user = _current_user_record(request, db)
        aliases = _user_aliases(user, session_username)
        is_activity_owner = (activity.responsable or "").strip().lower() in aliases
        if not is_activity_owner:
            return JSONResponse({"success": False, "error": "Solo el responsable puede declarar terminado"}, status_code=403)
        current_status = _activity_status(activity)
        if current_status == "No iniciada":
            return JSONResponse(
                {"success": False, "error": "La actividad no ha iniciado; habilítala en proceso o espera la fecha inicial"},
                status_code=409,
            )
        if (activity.entrega_estado or "").strip().lower() == "aprobada":
            return JSONResponse({"success": False, "error": "La actividad ya fue aprobada y terminada"}, status_code=409)

        if send_review:
            pending = (
                db.query(POADeliverableApproval)
                .filter(
                    POADeliverableApproval.activity_id == activity.id,
                    POADeliverableApproval.status == "pendiente",
                )
                .first()
            )
            if pending:
                return JSONResponse(
                    {"success": False, "error": "Ya existe una aprobación pendiente para esta actividad"},
                    status_code=409,
                )

            objective = db.query(StrategicObjectiveConfig).filter(StrategicObjectiveConfig.id == activity.objective_id).first()
            if not objective:
                return JSONResponse({"success": False, "error": "Objetivo no encontrado"}, status_code=404)
            axis = db.query(StrategicAxisConfig).filter(StrategicAxisConfig.id == objective.eje_id).first()
            process_owner = (activity.created_by or "").strip() or _resolve_process_owner_for_objective(objective, axis)
            if not process_owner:
                return JSONResponse(
                    {"success": False, "error": "No se pudo identificar el validador del entregable"},
                    status_code=400,
                )
            approval = POADeliverableApproval(
                activity_id=activity.id,
                objective_id=objective.id,
                process_owner=process_owner,
                requester=session_username or (activity.responsable or ""),
                status="pendiente",
            )
            activity.entrega_estado = "pendiente"
            activity.entrega_solicitada_por = session_username or (activity.responsable or "")
            activity.entrega_solicitada_at = datetime.utcnow()
            activity.entrega_aprobada_por = ""
            activity.entrega_aprobada_at = None
            db.add(approval)
            db.add(activity)
            db.commit()
            db.refresh(activity)
            subs = db.query(POASubactivity).filter(POASubactivity.activity_id == activity.id).all()
            return JSONResponse(
                {
                    "success": True,
                    "message": "Entregable enviado a revisión",
                    "data": _serialize_poa_activity(activity, subs),
                }
            )

        activity.entrega_estado = "declarada"
        activity.entrega_solicitada_por = ""
        activity.entrega_solicitada_at = None
        activity.entrega_aprobada_por = ""
        activity.entrega_aprobada_at = None
        db.add(activity)
        db.commit()
        db.refresh(activity)
        subs = db.query(POASubactivity).filter(POASubactivity.activity_id == activity.id).all()
        return JSONResponse(
            {
                "success": True,
                "message": "Actividad declarada terminada",
                "data": _serialize_poa_activity(activity, subs),
            }
        )
    finally:
        db.close()


@router.post("/api/poa/activities/{activity_id}/request-completion")
def request_poa_activity_completion(request: Request, activity_id: int):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        admin_like = _is_request_admin_like(request, db)
        activity = db.query(POAActivity).filter(POAActivity.id == activity_id).first()
        if not activity:
            return JSONResponse({"success": False, "error": "Actividad no encontrada"}, status_code=404)
        allowed_ids = {obj.id for obj in _allowed_objectives_for_user(request, db)}
        if activity.objective_id not in allowed_ids and not admin_like:
            return JSONResponse({"success": False, "error": "No autorizado para esta actividad"}, status_code=403)
        session_username = (getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "").strip()
        user = _current_user_record(request, db)
        aliases = _user_aliases(user, session_username)
        is_activity_owner = (activity.responsable or "").strip().lower() in aliases
        if not is_activity_owner:
            return JSONResponse({"success": False, "error": "Solo el responsable puede solicitar terminación"}, status_code=403)
        if _activity_status(activity) == "No iniciada":
            return JSONResponse(
                {"success": False, "error": "La actividad no ha iniciado; no se puede solicitar terminación"},
                status_code=409,
            )
        if (activity.entrega_estado or "").strip().lower() == "aprobada":
            return JSONResponse({"success": False, "error": "La actividad ya fue aprobada y terminada"}, status_code=409)

        pending = (
            db.query(POADeliverableApproval)
            .filter(
                POADeliverableApproval.activity_id == activity.id,
                POADeliverableApproval.status == "pendiente",
            )
            .first()
        )
        if pending:
            return JSONResponse({"success": False, "error": "Ya existe una aprobación pendiente para esta actividad"}, status_code=409)

        objective = db.query(StrategicObjectiveConfig).filter(StrategicObjectiveConfig.id == activity.objective_id).first()
        if not objective:
            return JSONResponse({"success": False, "error": "Objetivo no encontrado"}, status_code=404)
        axis = db.query(StrategicAxisConfig).filter(StrategicAxisConfig.id == objective.eje_id).first()
        process_owner = (activity.created_by or "").strip() or _resolve_process_owner_for_objective(objective, axis)
        if not process_owner:
            return JSONResponse(
                {"success": False, "error": "No se pudo identificar dueño del proceso (líder objetivo/departamento eje)"},
                status_code=400,
            )

        approval = POADeliverableApproval(
            activity_id=activity.id,
            objective_id=objective.id,
            process_owner=process_owner,
            requester=session_username or (activity.responsable or ""),
            status="pendiente",
        )
        activity.entrega_estado = "pendiente"
        activity.entrega_solicitada_por = session_username or (activity.responsable or "")
        activity.entrega_solicitada_at = datetime.utcnow()
        activity.entrega_aprobada_por = ""
        activity.entrega_aprobada_at = None
        db.add(approval)
        db.add(activity)
        db.commit()
        return JSONResponse({"success": True, "message": "Solicitud de aprobación enviada al dueño del proceso"})
    finally:
        db.close()


@router.post("/api/poa/approvals/{approval_id}/decision")
def decide_poa_deliverable_approval(request: Request, approval_id: int, data: dict = Body(default={})):
    _bind_core_symbols()
    action = (data.get("accion") or "").strip().lower()
    if action not in {"autorizar", "rechazar"}:
        return JSONResponse({"success": False, "error": "Acción inválida. Usa autorizar o rechazar"}, status_code=400)
    comment = (data.get("comentario") or "").strip()

    db = SessionLocal()
    try:
        approval = db.query(POADeliverableApproval).filter(POADeliverableApproval.id == approval_id).first()
        if not approval:
            return JSONResponse({"success": False, "error": "Solicitud de aprobación no encontrada"}, status_code=404)
        if approval.status != "pendiente":
            return JSONResponse({"success": False, "error": "Esta solicitud ya fue resuelta"}, status_code=409)
        if not _is_user_process_owner(request, db, approval.process_owner):
            return JSONResponse({"success": False, "error": "No autorizado para resolver esta aprobación"}, status_code=403)

        activity = db.query(POAActivity).filter(POAActivity.id == approval.activity_id).first()
        if not activity:
            return JSONResponse({"success": False, "error": "Actividad no encontrada"}, status_code=404)
        resolver_user = (getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "").strip()

        approval.status = "autorizada" if action == "autorizar" else "rechazada"
        approval.comment = comment
        approval.resolved_by = resolver_user
        approval.resolved_at = datetime.utcnow()
        db.add(approval)

        if action == "autorizar":
            activity.entrega_estado = "aprobada"
            activity.entrega_aprobada_por = resolver_user
            activity.entrega_aprobada_at = datetime.utcnow()
        else:
            activity.entrega_estado = "rechazada"
            activity.entrega_aprobada_por = ""
            activity.entrega_aprobada_at = None
        db.add(activity)
        db.commit()
        return JSONResponse({"success": True, "message": "Aprobación procesada correctamente"})
    finally:
        db.close()


@router.post("/api/poa/activities/{activity_id}/subactivities")
def create_poa_subactivity(request: Request, activity_id: int, data: dict = Body(...)):
    _bind_core_symbols()
    nombre = (data.get("nombre") or "").strip()
    responsable = (data.get("responsable") or "").strip()
    if not nombre:
        return JSONResponse({"success": False, "error": "Nombre es obligatorio"}, status_code=400)
    start_date, start_error = _parse_date_field(data.get("fecha_inicial"), "Fecha inicial", required=True)
    if start_error:
        return JSONResponse({"success": False, "error": start_error}, status_code=400)
    end_date, end_error = _parse_date_field(data.get("fecha_final"), "Fecha final", required=True)
    if end_error:
        return JSONResponse({"success": False, "error": end_error}, status_code=400)
    range_error = _validate_date_range(start_date, end_date, "Subactividad")
    if range_error:
        return JSONResponse({"success": False, "error": range_error}, status_code=400)
    recurrente = bool(data.get("recurrente"))
    periodicidad = (data.get("periodicidad") or "").strip().lower()
    try:
        cada_xx_dias = int(data.get("cada_xx_dias") or 0)
    except (TypeError, ValueError):
        return JSONResponse({"success": False, "error": "Cada xx dias debe ser un número válido"}, status_code=400)
    if recurrente:
        if periodicidad not in VALID_ACTIVITY_PERIODICITIES:
            return JSONResponse({"success": False, "error": "Selecciona una periodicidad válida"}, status_code=400)
        if periodicidad == "cada_xx_dias" and cada_xx_dias <= 0:
            return JSONResponse({"success": False, "error": "Cada xx dias debe ser mayor a 0"}, status_code=400)
    else:
        periodicidad = ""
        cada_xx_dias = 0

    db = SessionLocal()
    try:
        admin_like = _is_request_admin_like(request, db)
        if not admin_like:
            return JSONResponse({"success": False, "error": "Solo administrador puede crear subtareas"}, status_code=403)
        _ensure_poa_subactivity_recurrence_columns(db)
        activity = db.query(POAActivity).filter(POAActivity.id == activity_id).first()
        if not activity:
            return JSONResponse({"success": False, "error": "Actividad no encontrada"}, status_code=404)
        session_username = (getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "").strip()
        parent_error = _validate_child_date_range(
            start_date,
            end_date,
            activity.fecha_inicial,
            activity.fecha_final,
            "Subactividad",
            "Actividad",
        )
        if parent_error:
            return JSONResponse({"success": False, "error": parent_error}, status_code=400)
        parent_sub_id = int(data.get("parent_subactivity_id") or 0)
        parent_sub = None
        sub_level = 1
        if parent_sub_id:
            parent_sub = (
                db.query(POASubactivity)
                .filter(POASubactivity.id == parent_sub_id, POASubactivity.activity_id == activity.id)
                .first()
            )
            if not parent_sub:
                return JSONResponse({"success": False, "error": "Subactividad padre no encontrada"}, status_code=404)
            sub_level = int(parent_sub.nivel or 1) + 1
            if sub_level > MAX_SUBTASK_DEPTH:
                return JSONResponse(
                    {"success": False, "error": f"Profundidad máxima permitida: {MAX_SUBTASK_DEPTH} niveles"},
                    status_code=400,
                )
            child_error = _validate_child_date_range(
                start_date,
                end_date,
                parent_sub.fecha_inicial,
                parent_sub.fecha_final,
                "Subactividad",
                "Subactividad padre",
            )
            if child_error:
                return JSONResponse({"success": False, "error": child_error}, status_code=400)
        assigned_by = session_username
        sub = POASubactivity(
            activity_id=activity.id,
            parent_subactivity_id=parent_sub.id if parent_sub else None,
            nivel=sub_level,
            nombre=nombre,
            codigo=(data.get("codigo") or "").strip(),
            responsable=responsable,
            entregable=(data.get("entregable") or "").strip(),
            fecha_inicial=start_date,
            fecha_final=end_date,
            descripcion=(data.get("descripcion") or "").strip(),
            recurrente=recurrente,
            periodicidad=periodicidad,
            cada_xx_dias=(cada_xx_dias if periodicidad == "cada_xx_dias" else None),
            assigned_by=assigned_by,
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
        return JSONResponse({"success": True, "data": _serialize_poa_subactivity(sub)})
    finally:
        db.close()


@router.put("/api/poa/subactivities/{subactivity_id}")
def update_poa_subactivity(request: Request, subactivity_id: int, data: dict = Body(...)):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        admin_like = _is_request_admin_like(request, db)
        if not admin_like:
            return JSONResponse({"success": False, "error": "Solo administrador puede editar subtareas"}, status_code=403)
        _ensure_poa_subactivity_recurrence_columns(db)
        sub = db.query(POASubactivity).filter(POASubactivity.id == subactivity_id).first()
        if not sub:
            return JSONResponse({"success": False, "error": "Subactividad no encontrada"}, status_code=404)
        activity = db.query(POAActivity).filter(POAActivity.id == sub.activity_id).first()
        if not activity:
            return JSONResponse({"success": False, "error": "Actividad no encontrada"}, status_code=404)
        session_username = (getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "").strip()
        nombre = (data.get("nombre") or "").strip()
        responsable = (data.get("responsable") or "").strip()
        if not nombre:
            return JSONResponse({"success": False, "error": "Nombre es obligatorio"}, status_code=400)
        start_date, start_error = _parse_date_field(data.get("fecha_inicial"), "Fecha inicial", required=True)
        if start_error:
            return JSONResponse({"success": False, "error": start_error}, status_code=400)
        end_date, end_error = _parse_date_field(data.get("fecha_final"), "Fecha final", required=True)
        if end_error:
            return JSONResponse({"success": False, "error": end_error}, status_code=400)
        range_error = _validate_date_range(start_date, end_date, "Subactividad")
        if range_error:
            return JSONResponse({"success": False, "error": range_error}, status_code=400)
        recurrente = bool(data.get("recurrente"))
        periodicidad = (data.get("periodicidad") or "").strip().lower()
        try:
            cada_xx_dias = int(data.get("cada_xx_dias") or 0)
        except (TypeError, ValueError):
            return JSONResponse({"success": False, "error": "Cada xx dias debe ser un número válido"}, status_code=400)
        if recurrente:
            if periodicidad not in VALID_ACTIVITY_PERIODICITIES:
                return JSONResponse({"success": False, "error": "Selecciona una periodicidad válida"}, status_code=400)
            if periodicidad == "cada_xx_dias" and cada_xx_dias <= 0:
                return JSONResponse({"success": False, "error": "Cada xx dias debe ser mayor a 0"}, status_code=400)
        else:
            periodicidad = ""
            cada_xx_dias = 0
        parent_error = _validate_child_date_range(
            start_date,
            end_date,
            activity.fecha_inicial,
            activity.fecha_final,
            "Subactividad",
            "Actividad",
        )
        if parent_error:
            return JSONResponse({"success": False, "error": parent_error}, status_code=400)
        parent_sub = None
        if sub.parent_subactivity_id:
            parent_sub = (
                db.query(POASubactivity)
                .filter(POASubactivity.id == sub.parent_subactivity_id, POASubactivity.activity_id == activity.id)
                .first()
            )
        if parent_sub:
            child_error = _validate_child_date_range(
                start_date,
                end_date,
                parent_sub.fecha_inicial,
                parent_sub.fecha_final,
                "Subactividad",
                "Subactividad padre",
            )
            if child_error:
                return JSONResponse({"success": False, "error": child_error}, status_code=400)
        sub.nombre = nombre
        sub.codigo = (data.get("codigo") or "").strip()
        sub.responsable = responsable
        sub.entregable = (data.get("entregable") or "").strip()
        sub.fecha_inicial = start_date
        sub.fecha_final = end_date
        sub.descripcion = (data.get("descripcion") or "").strip()
        sub.recurrente = recurrente
        sub.periodicidad = periodicidad
        sub.cada_xx_dias = cada_xx_dias if periodicidad == "cada_xx_dias" else None
        db.add(sub)
        db.commit()
        db.refresh(sub)
        return JSONResponse({"success": True, "data": _serialize_poa_subactivity(sub)})
    finally:
        db.close()


@router.delete("/api/poa/subactivities/{subactivity_id}")
def delete_poa_subactivity(request: Request, subactivity_id: int):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        admin_like = _is_request_admin_like(request, db)
        if not admin_like:
            return JSONResponse({"success": False, "error": "Solo administrador puede eliminar subtareas"}, status_code=403)
        _ensure_poa_subactivity_recurrence_columns(db)
        sub = db.query(POASubactivity).filter(POASubactivity.id == subactivity_id).first()
        if not sub:
            return JSONResponse({"success": False, "error": "Subactividad no encontrada"}, status_code=404)
        activity = db.query(POAActivity).filter(POAActivity.id == sub.activity_id).first()
        if not activity:
            return JSONResponse({"success": False, "error": "Actividad no encontrada"}, status_code=404)
        descendants = _descendant_subactivity_ids(db, activity.id, sub.id)
        if descendants:
            db.query(POASubactivity).filter(POASubactivity.id.in_(descendants)).delete(synchronize_session=False)
        db.delete(sub)
        db.commit()
        return JSONResponse({"success": True})
    finally:
        db.close()


@router.get("/api/poa/subactivities/no-owner")
def poa_subactivities_without_owner(request: Request):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        _ensure_poa_subactivity_recurrence_columns(db)
        objectives = _allowed_objectives_for_user(request, db)
        objective_ids = [obj.id for obj in objectives]
        if not objective_ids:
            return JSONResponse({"success": True, "total": 0, "data": []})
        activities = (
            db.query(POAActivity)
            .filter(POAActivity.objective_id.in_(objective_ids))
            .order_by(POAActivity.id.desc())
            .all()
        )
        if not activities:
            return JSONResponse({"success": True, "total": 0, "data": []})
        activity_ids = [int(item.id) for item in activities if getattr(item, "id", None)]
        activity_map = {int(item.id): item for item in activities if getattr(item, "id", None)}
        objective_map = {int(obj.id): obj for obj in objectives}
        subs = (
            db.query(POASubactivity)
            .filter(POASubactivity.activity_id.in_(activity_ids))
            .order_by(POASubactivity.id.desc())
            .all()
            if activity_ids
            else []
        )
        rows: List[Dict[str, Any]] = []
        for sub in subs:
            if str(sub.responsable or "").strip():
                continue
            activity = activity_map.get(int(sub.activity_id or 0))
            objective = objective_map.get(int(activity.objective_id or 0)) if activity else None
            rows.append(
                {
                    "subactivity_id": int(sub.id or 0),
                    "subactivity_nombre": str(sub.nombre or ""),
                    "subactivity_codigo": str(sub.codigo or ""),
                    "activity_id": int(sub.activity_id or 0),
                    "activity_nombre": str(getattr(activity, "nombre", "") or ""),
                    "activity_codigo": str(getattr(activity, "codigo", "") or ""),
                    "objective_id": int(getattr(activity, "objective_id", 0) or 0),
                    "objective_nombre": str(getattr(objective, "nombre", "") or ""),
                    "objective_codigo": str(getattr(objective, "codigo", "") or ""),
                    "nivel": int(sub.nivel or 1),
                    "fecha_inicial": _date_to_iso(sub.fecha_inicial),
                    "fecha_final": _date_to_iso(sub.fecha_final),
                }
            )
        return JSONResponse({"success": True, "total": len(rows), "data": rows})
    finally:
        db.close()


# ── KPI Mediciones ─────────────────────────────────────────────────────────────

def _ensure_kpi_mediciones_table(db) -> None:
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS kpi_mediciones (
            id          INTEGER  PRIMARY KEY AUTOINCREMENT,
            kpi_id      INTEGER  NOT NULL,
            valor       REAL     NOT NULL,
            periodo     VARCHAR(50)  NOT NULL DEFAULT '',
            notas       TEXT         NOT NULL DEFAULT '',
            created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_by  VARCHAR(100) NOT NULL DEFAULT ''
        )
    """))
    db.commit()


def _kpi_parse_referencia(referencia: str):
    """Parse '8%', '5-8%', '5%-8%' → (lo, hi). hi=None si no es rango."""
    ref = re.sub(r"[%\s]", "", str(referencia or ""))
    if "-" in ref:
        parts = ref.split("-", 1)
        try:
            return float(parts[0]), float(parts[1])
        except (ValueError, IndexError):
            return None, None
    try:
        return float(ref), None
    except ValueError:
        return None, None


def _kpi_evaluate_status(valor: float, estandar: str, referencia: str) -> str:
    """Devuelve 'ok', 'warning', 'alert' o 'sin_meta'."""
    lo, hi = _kpi_parse_referencia(referencia)
    if lo is None:
        return "sin_meta"
    std = str(estandar or "").strip().lower()
    if std == "mayor":
        if valor >= lo:
            return "ok"
        margin = abs(lo * 0.10) if lo != 0 else 0.5
        return "warning" if valor >= lo - margin else "alert"
    elif std == "menor":
        if valor <= lo:
            return "ok"
        margin = abs(lo * 0.10) if lo != 0 else 0.5
        return "warning" if valor <= lo + margin else "alert"
    elif std == "entre" and hi is not None:
        if lo <= valor <= hi:
            return "ok"
        rng = abs(hi - lo) * 0.10 or 0.5
        return "warning" if (lo - rng) <= valor <= (hi + rng) else "alert"
    elif std == "igual":
        tol = abs(lo * 0.05) if lo != 0 else 0.5
        if abs(valor - lo) <= tol:
            return "ok"
        tol2 = abs(lo * 0.15) if lo != 0 else 1.0
        return "warning" if abs(valor - lo) <= tol2 else "alert"
    return "sin_meta"


@router.get("/api/kpis/definiciones")
def kpis_definiciones(request: Request):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        _ensure_objective_kpi_table(db)
        _ensure_kpi_mediciones_table(db)
        rows = db.execute(text("""
            SELECT
                k.id, k.objective_id, k.nombre, k.proposito, k.formula,
                k.periodicidad, k.estandar, k.referencia, k.orden,
                o.nombre   AS obj_nombre,
                o.codigo   AS obj_codigo,
                a.nombre   AS axis_nombre,
                a.codigo   AS axis_codigo
            FROM strategic_objective_kpis k
            LEFT JOIN strategic_objective_configs o ON o.id = k.objective_id
            LEFT JOIN strategic_axis_configs a ON a.id = o.axis_id
            ORDER BY a.codigo ASC, o.codigo ASC, k.orden ASC, k.id ASC
        """)).fetchall()
        kpi_ids = [int(r[0]) for r in rows]
        latest_by_kpi: Dict[int, Dict[str, Any]] = {}
        if kpi_ids:
            placeholders = ", ".join(f":k{i}" for i in range(len(kpi_ids)))
            params: Dict[str, Any] = {f"k{i}": v for i, v in enumerate(kpi_ids)}
            meds = db.execute(text(f"""
                SELECT kpi_id, valor, periodo, created_at
                FROM kpi_mediciones
                WHERE kpi_id IN ({placeholders})
                ORDER BY created_at DESC
            """), params).fetchall()
            seen: set = set()
            for m in meds:
                kid = int(m[0])
                if kid not in seen:
                    latest_by_kpi[kid] = {
                        "valor": float(m[1]),
                        "periodo": str(m[2] or ""),
                        "created_at": str(m[3] or ""),
                    }
                    seen.add(kid)
        data = []
        for r in rows:
            kpi_id = int(r[0])
            latest = latest_by_kpi.get(kpi_id)
            estandar = str(r[6] or "")
            referencia = str(r[7] or "")
            if latest:
                status = _kpi_evaluate_status(latest["valor"], estandar, referencia)
            else:
                status = "sin_medicion"
            data.append({
                "id": kpi_id,
                "objective_id": int(r[1] or 0),
                "nombre": str(r[2] or ""),
                "proposito": str(r[3] or ""),
                "formula": str(r[4] or ""),
                "periodicidad": str(r[5] or ""),
                "estandar": estandar,
                "referencia": referencia,
                "orden": int(r[8] or 0),
                "obj_nombre": str(r[9] or ""),
                "obj_codigo": str(r[10] or ""),
                "axis_nombre": str(r[11] or ""),
                "axis_codigo": str(r[12] or ""),
                "ultimo_valor": latest["valor"] if latest else None,
                "ultimo_periodo": latest["periodo"] if latest else "",
                "ultima_medicion": latest["created_at"] if latest else "",
                "status": status,
            })
        return JSONResponse({"success": True, "total": len(data), "data": data})
    finally:
        db.close()


@router.get("/api/kpis/mediciones")
def kpis_mediciones_list(request: Request):
    _bind_core_symbols()
    kpi_id_raw = request.query_params.get("kpi_id", "")
    db = SessionLocal()
    try:
        _ensure_kpi_mediciones_table(db)
        if kpi_id_raw:
            rows = db.execute(text("""
                SELECT id, kpi_id, valor, periodo, notas, created_at, created_by
                FROM kpi_mediciones WHERE kpi_id = :kid
                ORDER BY created_at DESC LIMIT 200
            """), {"kid": int(kpi_id_raw)}).fetchall()
        else:
            rows = db.execute(text("""
                SELECT id, kpi_id, valor, periodo, notas, created_at, created_by
                FROM kpi_mediciones
                ORDER BY created_at DESC LIMIT 500
            """)).fetchall()
        data = [
            {
                "id": int(r[0]), "kpi_id": int(r[1]), "valor": float(r[2]),
                "periodo": str(r[3] or ""), "notas": str(r[4] or ""),
                "created_at": str(r[5] or ""), "created_by": str(r[6] or ""),
            }
            for r in rows
        ]
        return JSONResponse({"success": True, "total": len(data), "data": data})
    finally:
        db.close()


@router.get("/api/kpis/estadisticas")
def kpis_estadisticas(request: Request):
    """Estadísticas por KPI usando pandas: conteo, media, min, max, desv. estándar y tendencia."""
    _bind_core_symbols()
    db = SessionLocal()
    try:
        _ensure_kpi_mediciones_table(db)
        rows = db.execute(text("""
            SELECT m.kpi_id, m.valor, m.periodo, m.created_at,
                   k.nombre AS kpi_nombre, k.estandar, k.referencia
            FROM kpi_mediciones m
            LEFT JOIN strategic_objective_kpis k ON k.id = m.kpi_id
            ORDER BY m.kpi_id, m.created_at ASC
        """)).fetchall()
    finally:
        db.close()

    if not rows:
        return JSONResponse({"success": True, "total_kpis": 0, "data": []})

    df = pd.DataFrame([
        {
            "kpi_id": int(r[0]),
            "valor": float(r[1]),
            "periodo": str(r[2] or ""),
            "created_at": str(r[3] or ""),
            "nombre": str(r[4] or ""),
            "estandar": str(r[5] or ""),
            "referencia": str(r[6] or ""),
        }
        for r in rows
    ])

    result = []
    for kpi_id, group in df.groupby("kpi_id"):
        vals = group["valor"].values
        n = int(len(vals))
        nombre = group["nombre"].iloc[0]
        estandar = group["estandar"].iloc[0]
        referencia = group["referencia"].iloc[0]

        # Tendencia: pendiente de regresión lineal sobre las mediciones en orden cronológico
        if n >= 2:
            slope = float(np.polyfit(range(n), vals, 1)[0])
        else:
            slope = 0.0

        if abs(slope) >= 0.5:
            trend_label = "subiendo" if slope > 0 else "bajando"
        else:
            trend_label = "estable"

        result.append({
            "kpi_id": int(kpi_id),
            "nombre": nombre,
            "estandar": estandar,
            "referencia": referencia,
            "n_mediciones": n,
            "media": round(float(vals.mean()), 4),
            "minimo": round(float(vals.min()), 4),
            "maximo": round(float(vals.max()), 4),
            "desv_std": round(float(vals.std()) if n > 1 else 0.0, 4),
            "ultimo_valor": round(float(vals[-1]), 4),
            "tendencia_pendiente": round(slope, 4),
            "tendencia": trend_label,
        })

    return JSONResponse({"success": True, "total_kpis": len(result), "data": result})


@router.post("/api/kpis/medicion")
def kpi_medicion_save(request: Request, data: dict = Body(default={})):
    _bind_core_symbols()
    kpi_id_raw = data.get("kpi_id")
    valor_raw = data.get("valor")
    periodo = str(data.get("periodo") or "").strip()
    notas = str(data.get("notas") or "").strip()
    try:
        kpi_id = int(kpi_id_raw)
        valor = float(str(valor_raw).replace(",", ".").replace("%", "").strip())
    except (TypeError, ValueError):
        return JSONResponse({"success": False, "error": "kpi_id y valor son requeridos"}, status_code=400)
    db = SessionLocal()
    try:
        _ensure_kpi_mediciones_table(db)
        created_by = str(
            getattr(request.state, "user_name", None)
            or request.cookies.get("user_name")
            or ""
        ).strip()
        db.execute(text("""
            INSERT INTO kpi_mediciones (kpi_id, valor, periodo, notas, created_at, created_by)
            VALUES (:kpi_id, :valor, :periodo, :notas, :now, :by)
        """), {
            "kpi_id": kpi_id, "valor": valor, "periodo": periodo,
            "notas": notas, "now": datetime.utcnow().isoformat(), "by": created_by,
        })
        db.commit()
        return JSONResponse({"success": True})
    except Exception as exc:
        db.rollback()
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)
    finally:
        db.close()


@router.delete("/api/kpis/medicion/{medicion_id}")
def kpi_medicion_delete(medicion_id: int, request: Request):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        _ensure_kpi_mediciones_table(db)
        db.execute(text("DELETE FROM kpi_mediciones WHERE id = :mid"), {"mid": medicion_id})
        db.commit()
        return JSONResponse({"success": True})
    except Exception as exc:
        db.rollback()
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)
    finally:
        db.close()
