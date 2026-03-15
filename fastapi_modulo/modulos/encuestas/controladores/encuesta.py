from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote
import re
import secrets
import unicodedata

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response as FastAPIResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from fastapi_modulo.modulos.encuestas.modelos.encuestas_question_catalog import (
    list_question_types,
)
from fastapi_modulo.modulos.encuestas.modelos.encuestas_store import (
    archive_or_delete_instance,
    create_section,
    create_question,
    create_instance,
    create_instance_from_template,
    create_template,
    ensure_default_templates,
    ensure_survey_schema,
    export_results_csv,
    export_results_excel,
    export_results_pdf,
    get_instance,
    get_instance_builder,
    get_results_dashboard,
    list_instances,
    list_assignable_users,
    list_assignments,
    list_dispatch_logs,
    list_integration_sources,
    list_results,
    list_templates,
    publish_instance,
    reorder_questions,
    reorder_sections,
    save_instance_as_template,
    sync_assignments,
    queue_automation_job,
    update_instance_draft,
    update_question,
    update_section,
    close_instance,
    duplicate_question,
    get_response_session,
    save_response_draft,
    start_internal_response,
    start_public_response,
    submit_response,
    run_automation_jobs,
    validate_instance_for_publish,
)

router = APIRouter()
ensure_survey_schema()
ensure_survey_schema = lambda: None

_MANAGE_ROLES = {"superadministrador", "administrador_multiempresa", "administrador"}
_RESULTS_ROLES = _MANAGE_ROLES | {"autoridades", "departamento"}
_SENSITIVE_RESULTS_ROLES = _MANAGE_ROLES
_ROLE_ALIASES = {
    "superadmin": "superadministrador",
    "super_admin": "superadministrador",
    "super_administrador": "superadministrador",
    "superadministrdor": "superadministrador",
    "admin_multiempresa": "administrador_multiempresa",
    "multiempresa_admin": "administrador_multiempresa",
    "administrador_multi": "administrador_multiempresa",
    "admin": "administrador",
    "administador": "administrador",
    "administrdor": "administrador",
    "admnistrador": "administrador",
}

_MODULE_DIR = Path(__file__).resolve().parents[1]
_VIEWS_DIR = _MODULE_DIR / "vistas"
_STATIC_DIR = _MODULE_DIR / "static"
_ENCUESTA_TEMPLATE_PATH = _VIEWS_DIR / "encuesta.html"
_ENCUESTA_JS_PATH = _STATIC_DIR / "js" / "encuesta.js"
_ENCUESTA_CSS_PATH = _STATIC_DIR / "css" / "encuesta.css"
_ENCUESTA_RESPONSE_TEMPLATE_PATH = _VIEWS_DIR / "encuesta_response.html"
_ENCUESTA_RESPONSE_JS_PATH = _STATIC_DIR / "js" / "encuesta_response.js"
_ENCUESTAS_IMAGE_DIR = _MODULE_DIR / "imagenes"

_ENCUESTA_BOOTSTRAP_STATE = {
    "navigation": [
        {"id": "dashboard", "label": "Dashboard"},
        {"id": "encuestas", "label": "Encuestas"},
        {"id": "constructor", "label": "Constructor"},
        {"id": "resultados", "label": "Resultados"},
    ],
    "metrics": {
        "drafts": 4,
        "active": 2,
        "completion_rate": 76,
        "responses_today": 39,
    },
    "conventions": {
        "id_prefix": "enc-",
        "class_prefix": "enc-",
        "hook_prefix": "data-enc-",
    },
}


def _encuestas_bootstrap(panel_id: str = "dashboard") -> Dict[str, Any]:
    payload = json.loads(json.dumps(_ENCUESTA_BOOTSTRAP_STATE))
    payload["current_panel"] = panel_id
    return payload


class SurveyTemplateCreateIn(BaseModel):
    nombre: str = Field(..., max_length=200)
    slug: Optional[str] = Field(None, max_length=160)
    descripcion: Optional[str] = None
    categoria: Optional[str] = Field(None, max_length=80)
    survey_type: str = Field("general", max_length=50)
    source_app: Optional[str] = Field(None, max_length=80)
    external_entity_type: Optional[str] = Field(None, max_length=80)
    external_entity_id: Optional[str] = Field(None, max_length=120)
    scoring_mode: str = Field("none", max_length=40)
    settings_json: Dict[str, Any] = Field(default_factory=dict)
    validation_rules_json: Dict[str, Any] = Field(default_factory=dict)


class SurveyTemplateSaveFromInstanceIn(BaseModel):
    nombre: str = Field(..., max_length=200)
    slug: Optional[str] = Field(None, max_length=160)
    descripcion: Optional[str] = None
    categoria: Optional[str] = Field(None, max_length=80)
    survey_type: str = Field("general", max_length=50)
    external_entity_type: Optional[str] = Field(None, max_length=80)
    external_entity_id: Optional[str] = Field(None, max_length=120)


class SurveyInstanceCreateIn(BaseModel):
    template_id: Optional[int] = None
    codigo: Optional[str] = Field(None, max_length=80)
    nombre: str = Field(..., max_length=200)
    descripcion: Optional[str] = None
    publication_mode: str = Field("manual", max_length=30)
    audience_mode: str = Field("internal", max_length=30)
    anonymity_mode: str = Field("identified", max_length=30)
    schedule_start_at: Optional[str] = None
    schedule_end_at: Optional[str] = None
    is_public_link_enabled: bool = False
    public_link_token: Optional[str] = Field(None, max_length=120)
    source_app: Optional[str] = Field(None, max_length=80)
    external_entity_type: Optional[str] = Field(None, max_length=80)
    external_entity_id: Optional[str] = Field(None, max_length=120)
    settings_json: Dict[str, Any] = Field(default_factory=dict)
    publication_rules_json: Dict[str, Any] = Field(default_factory=dict)


class SurveyInstanceDraftUpdateIn(BaseModel):
    template_id: Optional[int] = None
    nombre: Optional[str] = Field(None, max_length=200)
    descripcion: Optional[str] = None
    publication_mode: Optional[str] = Field(None, max_length=30)
    audience_mode: Optional[str] = Field(None, max_length=30)
    anonymity_mode: Optional[str] = Field(None, max_length=30)
    schedule_start_at: Optional[str] = None
    schedule_end_at: Optional[str] = None
    is_public_link_enabled: Optional[bool] = None
    public_link_token: Optional[str] = Field(None, max_length=120)
    source_app: Optional[str] = Field(None, max_length=80)
    external_entity_type: Optional[str] = Field(None, max_length=80)
    external_entity_id: Optional[str] = Field(None, max_length=120)
    settings_json: Optional[Dict[str, Any]] = None
    publication_rules_json: Optional[Dict[str, Any]] = None


class SurveySectionIn(BaseModel):
    titulo: str = Field(..., max_length=200)
    descripcion: Optional[str] = None
    is_required: bool = False
    settings_json: Dict[str, Any] = Field(default_factory=dict)


class SurveySectionUpdateIn(BaseModel):
    titulo: Optional[str] = Field(None, max_length=200)
    descripcion: Optional[str] = None
    is_required: Optional[bool] = None
    settings_json: Optional[Dict[str, Any]] = None


class SurveyOptionIn(BaseModel):
    label: str = Field(..., max_length=300)
    value: Optional[str] = Field(None, max_length=160)
    orden: Optional[int] = None
    score_value: Optional[float] = None
    is_correct: bool = False
    config_json: Dict[str, Any] = Field(default_factory=dict)


class SurveyQuestionIn(BaseModel):
    question_key: Optional[str] = Field(None, max_length=120)
    titulo: str
    descripcion: Optional[str] = None
    question_type: str = Field("short_text", max_length=50)
    is_required: bool = False
    is_scored: bool = False
    max_score: Optional[float] = None
    min_score: Optional[float] = None
    config_json: Dict[str, Any] = Field(default_factory=dict)
    validation_json: Dict[str, Any] = Field(default_factory=dict)
    logic_json: Dict[str, Any] = Field(default_factory=dict)
    options: list[SurveyOptionIn] = Field(default_factory=list)


class SurveyQuestionUpdateIn(BaseModel):
    question_key: Optional[str] = Field(None, max_length=120)
    titulo: Optional[str] = None
    descripcion: Optional[str] = None
    question_type: Optional[str] = Field(None, max_length=50)
    is_required: Optional[bool] = None
    is_scored: Optional[bool] = None
    max_score: Optional[float] = None
    min_score: Optional[float] = None
    config_json: Optional[Dict[str, Any]] = None
    validation_json: Optional[Dict[str, Any]] = None
    logic_json: Optional[Dict[str, Any]] = None
    options: Optional[list[SurveyOptionIn]] = None


class ReorderIn(BaseModel):
    ids: list[int] = Field(default_factory=list)


class AssignmentEntryIn(BaseModel):
    type: str = Field(..., max_length=40)
    values: list[str] = Field(default_factory=list)


class ManualGroupMemberIn(BaseModel):
    user_id: str
    nombre: Optional[str] = None
    role: Optional[str] = None
    departamento: Optional[str] = None
    puesto: Optional[str] = None
    empresa: Optional[str] = None


class ManualGroupIn(BaseModel):
    name: str = Field(..., max_length=180)
    description: Optional[str] = None
    members: list[ManualGroupMemberIn] = Field(default_factory=list)


class AssignmentSyncIn(BaseModel):
    assignments: list[AssignmentEntryIn] = Field(default_factory=list)
    manual_groups: list[ManualGroupIn] = Field(default_factory=list)
    due_at: Optional[str] = None


class ResponseSaveIn(BaseModel):
    answers: Dict[str, Any] = Field(default_factory=dict)


def _normalize_tenant_id(value: Optional[str]) -> str:
    raw = str(value or "").strip().lower()
    normalized = re.sub(r"[^a-z0-9._-]+", "-", raw).strip("-._")
    return normalized or "default"


def _get_current_tenant(request: Request) -> str:
    tenant = getattr(request.state, "tenant_id", None)
    if tenant:
        return _normalize_tenant_id(tenant)
    cookie_tenant = request.cookies.get("tenant_id")
    if cookie_tenant:
        return _normalize_tenant_id(cookie_tenant)
    header_tenant = request.headers.get("x-tenant-id")
    if header_tenant and _current_role(request) == "superadministrador":
        return _normalize_tenant_id(header_tenant)
    return _normalize_tenant_id("default")


def _slugify_value(value: str) -> str:
    MAIN = str(value or "").strip().lower()
    MAIN = re.sub(r"[^a-z0-9]+", "-", MAIN)
    MAIN = re.sub(r"-+", "-", MAIN).strip("-")
    return MAIN or secrets.token_hex(4)


def _tenant_id(request: Request) -> str:
    return _normalize_tenant_id(_get_current_tenant(request))


def _normalize_role_name(raw_role: str) -> str:
    role = unicodedata.normalize("NFKD", str(raw_role or "").strip().lower())
    role = "".join(ch for ch in role if not unicodedata.combining(ch))
    role = re.sub(r"[^a-z0-9]+", "_", role).strip("_")
    return _ROLE_ALIASES.get(role, role)


def _current_role(request: Request) -> str:
    return _normalize_role_name(
        str(getattr(request.state, "user_role", None) or request.cookies.get("user_role") or "")
    )


def _encuestas_permissions(request: Request) -> Dict[str, bool]:
    role = _current_role(request)
    return {
        "view_module": bool(role),
        "manage_surveys": role in _MANAGE_ROLES,
        "view_results_summary": role in _RESULTS_ROLES,
        "view_sensitive_results": role in _SENSITIVE_RESULTS_ROLES,
        "export_sensitive_results": role in _SENSITIVE_RESULTS_ROLES,
    }


def _require_encuestas_permission(request: Request, permission: str) -> None:
    permissions = _encuestas_permissions(request)
    if not permissions.get(permission):
        raise HTTPException(status_code=403, detail="No tienes permiso para realizar esta acción en Encuestas.")


def _coerce_360_anonymity(data: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(data or {})
    survey_type = str(payload.get("survey_type") or "").strip().lower()
    external_entity_type = str(payload.get("external_entity_type") or "").strip().lower()
    is_360 = survey_type in {"360", "evaluation_360", "evaluacion_360"} or "360" in external_entity_type
    if is_360:
        payload["anonymity_mode"] = "restricted"
    return payload


def _sanitize_dashboard_payload(dashboard: Dict[str, Any], request: Request) -> Dict[str, Any]:
    permissions = _encuestas_permissions(request)
    payload = json.loads(json.dumps(dashboard))
    anonymity_mode = str(payload.get("instance", {}).get("anonymity_mode") or "identified").strip().lower()
    settings = payload.get("instance", {}).get("settings_json") or {}
    publication_rules = payload.get("instance", {}).get("publication_rules_json") or {}
    min_segment_size = int(
        publication_rules.get("min_segment_size")
        or settings.get("min_segment_size")
        or 3
    )
    can_view_sensitive = permissions.get("view_sensitive_results", False) and anonymity_mode == "identified"
    external_entity_type = str(payload.get("instance", {}).get("external_entity_type") or "").strip().lower()
    is_360 = "360" in external_entity_type

    segment_report = payload.get("segment_report") or {}
    for key, rows in segment_report.items():
        sanitized_rows = []
        hidden_count = 0
        for row in rows:
            if int(row.get("responses") or 0) < min_segment_size:
                hidden_count += int(row.get("responses") or 0)
                continue
            sanitized_rows.append(row)
        if hidden_count:
            sanitized_rows.append(
                {
                    "segment": "Oculto por umbral",
                    "label": key.capitalize(),
                    "responses": hidden_count,
                    "completion_pct_avg": None,
                    "score_avg": None,
                }
            )
        segment_report[key] = sanitized_rows
    comparison_report = []
    hidden_comparison_count = 0
    for row in payload.get("comparison_report") or []:
        if int(row.get("responses") or 0) < min_segment_size:
            hidden_comparison_count += int(row.get("responses") or 0)
            continue
        comparison_report.append(row)
    if hidden_comparison_count:
        comparison_report.append(
            {
                "segment_by": (payload.get("applied_filters") or {}).get("segment_by") or "department",
                "segment": "Oculto por umbral",
                "responses": hidden_comparison_count,
                "completion_pct_avg": None,
                "total_score_avg": None,
                "nps_score": None,
                "csat_score": None,
                "ces_score": None,
            }
        )
    payload["comparison_report"] = comparison_report

    if anonymity_mode == "anonymous" or not can_view_sensitive or is_360:
        masked_rows = []
        for index, row in enumerate(payload.get("responses_table") or [], start=1):
            masked = dict(row)
            masked["respondent_key"] = None
            masked["respondent_name"] = f"Participante {index}" if anonymity_mode != "anonymous" else "Anónimo"
            masked["role"] = ""
            masked["department"] = ""
            masked["position"] = ""
            masked["company"] = ""
            masked["answers_json"] = {}
            masked_rows.append(masked)
        payload["responses_table"] = masked_rows
        for question in payload.get("question_report") or []:
            if question.get("question_type") in {"short_text", "long_text"}:
                question["sample_answers"] = []
    if is_360:
        report_360 = payload.get("report_360") or {}
        report_360["links"] = []
        report_360["by_evaluatee"] = [
            {
                **row,
                "evaluatee_name": f"Perfil {index}",
            }
            for index, row in enumerate(report_360.get("by_evaluatee") or [], start=1)
        ]
        payload["report_360"] = report_360

    payload["permissions"] = permissions
    payload["visibility"] = {
        "anonymity_mode": anonymity_mode,
        "min_segment_size": min_segment_size,
        "show_sensitive_results": can_view_sensitive,
    }
    return payload


def _parse_dt(value: Optional[str]) -> Optional[object]:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return __import__("datetime").datetime.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Fecha inválida: {raw}") from exc


def _survey_code(seed: str) -> str:
    MAIN = _slugify_value(seed or "encuesta").replace("-", "_").upper()[:50]
    if not MAIN:
        MAIN = "ENCUESTA"
    return f"{MAIN}_{Path(__file__).stat().st_mtime_ns % 100000}"


def _load_template() -> str:
    try:
        return _ENCUESTA_TEMPLATE_PATH.read_text(encoding="utf-8")
    except OSError:
        return "<section class='enc-shell'><p>No se pudo cargar la vista MAIN del modulo de encuestas.</p></section>"


def _load_css() -> str:
    try:
        return _ENCUESTA_CSS_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""


def _load_response_template() -> str:
    try:
        return _ENCUESTA_RESPONSE_TEMPLATE_PATH.read_text(encoding="utf-8")
    except OSError:
        return "<section class='enc-response-shell'><p>No se pudo cargar la vista de respuesta.</p></section>"


def _asset_url(path: str, source: Path) -> str:
    try:
        return f"{path}?v={source.stat().st_mtime_ns}"
    except OSError:
        return path


def _render_module_shell(
    request: Request,
    *,
    title: str,
    content: str,
    js_url: str,
    current_panel: str = "",
    is_response: bool = False,
    show_back_link: bool = True,
) -> HTMLResponse:
    icon_url = "/modulos/encuestas/imagenes/encuestas.svg"
    nav_items = [
        ("dashboard", "Dashboard", "/encuestas"),
        ("encuestas", "Encuestas", "/encuestas/encuestas"),
        ("constructor", "Constructor", "/encuestas/constructor"),
        ("resultados", "Resultados", "/encuestas/resultados"),
    ]
    current_panel_label = next((label for key, label, _ in nav_items if key == current_panel), "Encuestas")
    nav_html = ""
    if not is_response:
        nav_html = "".join(
            (
                f'<a class="enc-app-link{" is-current" if key == current_panel else ""}" '
                f'href="{href}">{escape(label)}</a>'
            )
            for key, label, href in nav_items
        )
        nav_html += '<a class="enc-app-link" href="/inicio">Panel</a>'
    elif show_back_link:
        nav_html = '<a class="enc-app-link" href="/encuestas">Volver a Encuestas</a>'

    if not is_response:
        from fastapi_modulo.main import get_colores_context

        module_nav = f"""
        <div class="enc-sidebar-card">
          <p class="enc-sidebar-label">Módulo</p>
          <nav class="enc-nav" aria-label="Navegación interna de Encuestas">
            {''.join(
                (
                    f'<a class="enc-nav-link{" is-active" if key == current_panel else ""}" '
                    f'data-enc-nav="{key}" href="{href}">{escape(label)}</a>'
                )
                for key, label, href in nav_items
            )}
          </nav>
        </div>
        """
        wrapped_content = (
            f"<style>{_load_css()}</style>"
            f"<div class=\"enc-app-main\">{module_nav}{content}</div>"
            f"<script src=\"{js_url}\"></script>"
        )
        return request.app.state.templates.TemplateResponse(
            "MAIN.html",
            {
                "request": request,
                "title": title,
                "description": "Módulo de encuestas",
                "page_title": f"Encuestas · {current_panel_label}",
                "page_description": f"Encuestas: {current_panel_label}.",
                "section_label": "",
                "section_title": "",
                "content": wrapped_content,
                "hide_floating_actions": True,
                "show_page_header": False,
                "view_buttons_html": "",
                "floating_actions_html": "",
                "colores": get_colores_context(),
            },
        )

    shell = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{escape(title)}</title>
  <link rel="icon" type="image/svg+xml" href="{icon_url}">
  <link rel="stylesheet" href="{_asset_url('/modulos/encuestas/encuesta.css', _ENCUESTA_CSS_PATH)}">
</head>
<body class="enc-page-body">
  <div class="enc-app-shell">
    <header class="enc-app-topbar">
      <a class="enc-app-brand" href="/encuestas">
        <img src="{icon_url}" alt="Encuestas">
        <span class="enc-app-brand-copy">
          <strong>Encuestas</strong>
          <span>Modulo autocontenido</span>
        </span>
      </a>
      <nav class="enc-app-links" aria-label="Navegacion Encuestas">
        {nav_html}
      </nav>
    </header>
    <main class="enc-app-main{' is-response' if is_response else ''}">
      {content}
    </main>
  </div>
  <script src="{js_url}"></script>
</body>
</html>"""
    return HTMLResponse(shell)


def _current_user_payload(request: Request) -> Dict[str, Any]:
    session_name = str(
        getattr(request.state, "user_name", None)
        or request.cookies.get("user_name")
        or request.cookies.get("username")
        or ""
    ).strip()
    if not session_name:
        return {}
    for item in list_assignable_users():
        aliases = {
            str(item.get("user_id") or "").strip(),
            str(item.get("user_key") or "").strip(),
            str(item.get("usuario") or "").strip().lower(),
            str(item.get("nombre") or "").strip().lower(),
        }
        if session_name.lower() in aliases:
            return item
    return {"user_id": session_name, "user_key": session_name, "nombre": session_name, "usuario": session_name}


def _render_preview_html(builder: Dict[str, Any]) -> str:
    sections = builder.get("sections") or []
    blocks = []
    for section in sections:
        questions_html = []
        for question in section.get("questions") or []:
            qtype = question.get("question_type") or "short_text"
            options = question.get("options") or []
            field_html = '<input class="enc-preview-input" type="text" placeholder="Respuesta..." />'
            if qtype == "long_text":
                field_html = '<textarea class="enc-preview-input enc-preview-textarea" placeholder="Respuesta abierta"></textarea>'
            elif qtype in {"short_text", "word_cloud"}:
                placeholder = (question.get("config_json") or {}).get("placeholder") or "Respuesta breve"
                field_html = f'<input class="enc-preview-input" type="text" placeholder="{placeholder}" />'
            elif qtype in {"single_choice", "live_poll_single_choice", "quiz_single_choice", "yes_no"}:
                field_html = "".join(
                    f'<label class="enc-preview-choice"><input type="radio" name="q-{question["id"]}" /> <span>{option.get("label")}</span></label>'
                    for option in options
                ) or '<div class="enc-preview-empty">Sin opciones configuradas.</div>'
            elif qtype == "multiple_choice":
                field_html = "".join(
                    f'<label class="enc-preview-choice"><input type="checkbox" /> <span>{option.get("label")}</span></label>'
                    for option in options
                ) or '<div class="enc-preview-empty">Sin opciones configuradas.</div>'
            elif qtype == "ranking":
                field_html = "".join(
                    f'<label class="enc-preview-choice"><span>{index}. {option.get("label")}</span></label>'
                    for index, option in enumerate(options, start=1)
                ) or '<div class="enc-preview-empty">Sin opciones configuradas.</div>'
            elif qtype in {"scale_1_5", "live_scale_1_5", "nps_0_10"}:
                field_html = "".join(
                    f'<button type="button" class="enc-preview-scale">{option.get("label")}</button>'
                    for option in options
                ) or '<div class="enc-preview-empty">Escala pendiente.</div>'
            elif qtype in {"matrix", "likert_scale", "semantic_differential"}:
                columns = (question.get("config_json") or {}).get("columns") or []
                header = "".join(f"<th>{column.get('label')}</th>" for column in columns)
                rows = "".join(
                    f"<tr><td>{option.get('label')}</td>{''.join('<td>○</td>' for _ in columns)}</tr>"
                    for option in options
                )
                field_html = f'<table class="enc-table"><thead><tr><th>Ítem</th>{header}</tr></thead><tbody>{rows}</tbody></table>'
            elif qtype == "dropdown":
                field_html = "<select class='enc-preview-input'>" + "".join(
                    f"<option>{option.get('label')}</option>" for option in options
                ) + "</select>"
            elif qtype == "slider":
                config = question.get("config_json") or {}
                field_html = (
                    f"<input class='enc-preview-input' type='range' min='{config.get('min', 0)}' "
                    f"max='{config.get('max', 10)}' step='{config.get('step', 1)}' />"
                )
            elif qtype == "image_choice":
                field_html = "".join(
                    f'<label class="enc-preview-choice"><input type="radio" name="q-{question["id"]}" /> <span>{option.get("label")}</span></label>'
                    for option in options
                ) or '<div class="enc-preview-empty">Sin opciones configuradas.</div>'
            elif qtype == "true_false":
                field_html = (
                    f'<label class="enc-preview-choice"><input type="radio" name="q-{question["id"]}" /> <span>Verdadero</span></label>'
                    f'<label class="enc-preview-choice"><input type="radio" name="q-{question["id"]}" /> <span>Falso</span></label>'
                )
            elif qtype == "date":
                field_html = '<input class="enc-preview-input" type="date" />'
            elif qtype == "time":
                field_html = '<input class="enc-preview-input" type="time" />'
            elif qtype == "file_upload":
                field_html = '<input class="enc-preview-input" type="file" />'
            questions_html.append(
                f"""
                <article class="enc-preview-question">
                  <h4>{question.get("titulo") or "Pregunta sin titulo"}</h4>
                  <p>{question.get("descripcion") or ""}</p>
                  <small>{question.get("question_type_label") or qtype}</small>
                  <div class="enc-preview-field">{field_html}</div>
                </article>
                """
            )
        blocks.append(
            f"""
            <section class="enc-preview-section">
              <header>
                <h3>{section.get("titulo") or "Seccion"}</h3>
                <p>{section.get("descripcion") or ""}</p>
              </header>
              <div class="enc-preview-questions">{''.join(questions_html) or '<div class="enc-preview-empty">Agrega preguntas para visualizar la encuesta.</div>'}</div>
            </section>
            """
        )
    return "".join(blocks) or '<div class="enc-preview-empty">Agrega secciones para visualizar la encuesta.</div>'


def _render_response_page(request: Request, session_payload: Dict[str, Any]) -> HTMLResponse:
    content = _load_response_template().replace(
        "__ENCUESTA_RESPONSE_BOOTSTRAP__",
        json.dumps(session_payload, ensure_ascii=True),
    )
    js_url = "/api/public/encuestas/assets/encuesta_response.js"
    if str(session_payload.get("session", {}).get("access_mode") or "").strip().lower() != "public":
        js_url = _asset_url("/modulos/encuestas/encuesta_response.js", _ENCUESTA_RESPONSE_JS_PATH)
    html_response = _render_module_shell(
        request,
        title=f"Responder · {session_payload.get('instance', {}).get('nombre') or 'Encuesta'}",
        content=content,
        js_url=js_url,
        is_response=True,
        show_back_link=str(session_payload.get("session", {}).get("access_mode") or "").strip().lower() != "public",
    )
    return html_response


def _render_encuestas_page(request: Request, panel_id: str) -> HTMLResponse:
    ensure_survey_schema()
    module_html = _load_template().replace(
        "__ENCUESTA_BOOTSTRAP__",
        json.dumps(_encuestas_bootstrap(panel_id), ensure_ascii=True),
    )
    # La función _render_module_shell ya se encarga de incluir el CSS y JS.
    # Esto desacopla completamente el renderizado del módulo de `main.py`,
    # solucionando el error de "Internal Server Error".
    return _render_module_shell(
        request,
        title="Módulo de Encuestas",
        content=module_html,
        js_url=_asset_url("/modulos/encuestas/encuesta.js", _ENCUESTA_JS_PATH),
        current_panel=panel_id,
        is_response=False,
    )


@router.get("/encuestas", response_class=HTMLResponse)
@router.get("/encuestas/dashboard", response_class=HTMLResponse)
def encuestas_page(request: Request):
    return _render_encuestas_page(request, "dashboard")


@router.get("/encuestas/encuestas", response_class=HTMLResponse)
def encuestas_list_page(request: Request):
    return _render_encuestas_page(request, "encuestas")


@router.get("/encuestas/constructor", response_class=HTMLResponse)
def encuestas_constructor_page(request: Request):
    return _render_encuestas_page(request, "constructor")


@router.get("/encuestas/resultados", response_class=HTMLResponse)
def encuestas_results_page(request: Request):
    return _render_encuestas_page(request, "resultados")


@router.get("/encuestas/responder/{instance_id}", response_class=HTMLResponse)
def encuesta_responder_interna(instance_id: int, request: Request):
    ensure_survey_schema()
    user_payload = _current_user_payload(request)
    if not user_payload:
        raise HTTPException(status_code=401, detail="Debes iniciar sesión para responder esta encuesta.")
    try:
        session_payload = start_internal_response(instance_id, _tenant_id(request), user_payload)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return _render_response_page(request, session_payload)


@router.get("/api/public/encuestas/{public_token}", response_class=HTMLResponse)
def encuesta_responder_publica(public_token: str, request: Request):
    ensure_survey_schema()
    response_key = str(request.cookies.get("enc_response_key") or "").strip()
    try:
        session_payload = start_public_response(public_token, _tenant_id(request), response_key=response_key)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    response = _render_response_page(request, session_payload)
    response.set_cookie(
        key="enc_response_key",
        value=str(session_payload.get("response_key") or ""),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )
    return response


@router.get("/modulos/encuestas/encuesta.js")
def encuesta_js():
    return FileResponse(_ENCUESTA_JS_PATH, media_type="application/javascript")


@router.get("/modulos/encuestas/encuesta.css")
def encuesta_css():
    return FileResponse(_ENCUESTA_CSS_PATH, media_type="text/css")


@router.get("/modulos/encuestas/encuesta_response.js")
def encuesta_response_js():
    return FileResponse(_ENCUESTA_RESPONSE_JS_PATH, media_type="application/javascript")


@router.get("/modulos/encuestas/imagenes/{filename}")
def encuesta_image(filename: str):
    safe_name = Path(filename).name
    image_root = _ENCUESTAS_IMAGE_DIR.resolve()
    file_path = (image_root / safe_name).resolve()
    if file_path.parent != image_root or not file_path.exists():
        raise HTTPException(status_code=404, detail="Recurso no encontrado.")
    return FileResponse(file_path)


@router.get("/api/public/encuestas/assets/encuesta.css")
def encuesta_public_css():
    return FileResponse(_ENCUESTA_CSS_PATH, media_type="text/css")


@router.get("/api/public/encuestas/assets/encuesta_response.js")
def encuesta_public_response_js():
    return FileResponse(_ENCUESTA_RESPONSE_JS_PATH, media_type="application/javascript")


@router.get("/api/encuestas/templates")
def api_list_templates(request: Request, status: str = Query(default="")):
    ensure_survey_schema()
    _require_encuestas_permission(request, "view_module")
    tenant_id = _tenant_id(request)
    ensure_default_templates(
        tenant_id,
        created_by=getattr(request.state, "user_name", None) or request.cookies.get("user_name"),
    )
    return list_templates(tenant_id, status=status.strip())


@router.get("/api/encuestas/question-types")
def api_list_question_types():
    return list_question_types()


@router.get("/api/encuestas/permissions")
def api_encuestas_permissions(request: Request):
    return _encuestas_permissions(request)


@router.post("/api/encuestas/templates", status_code=201)
def api_create_template(payload: SurveyTemplateCreateIn, request: Request):
    ensure_survey_schema()
    _require_encuestas_permission(request, "manage_surveys")
    tenant_id = _tenant_id(request)
    slug = _slugify_value(payload.slug or payload.nombre)
    data = _coerce_360_anonymity(payload.model_dump())
    data["tenant_id"] = tenant_id
    data["slug"] = slug
    data["created_by"] = getattr(request.state, "user_name", None) or request.cookies.get("user_name")
    try:
        return create_template(data)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Ya existe una plantilla con ese slug.") from exc


@router.get("/api/encuestas/campanas")
def api_list_campaigns(request: Request, status: str = Query(default="")):
    ensure_survey_schema()
    _require_encuestas_permission(request, "view_module")
    return list_instances(_tenant_id(request), status=status.strip())


@router.get("/api/encuestas/assignable-users")
def api_assignable_users(request: Request):
    ensure_survey_schema()
    _require_encuestas_permission(request, "manage_surveys")
    return list_assignable_users()


@router.get("/api/encuestas/integration-sources")
def api_integration_sources(request: Request):
    ensure_survey_schema()
    _require_encuestas_permission(request, "manage_surveys")
    return list_integration_sources()


@router.post("/api/encuestas/campanas", status_code=201)
def api_create_campaign(payload: SurveyInstanceCreateIn, request: Request):
    ensure_survey_schema()
    _require_encuestas_permission(request, "manage_surveys")
    tenant_id = _tenant_id(request)
    data = _coerce_360_anonymity(payload.model_dump())
    data["tenant_id"] = tenant_id
    data["codigo"] = data.get("codigo") or _survey_code(payload.nombre)
    data["schedule_start_at"] = _parse_dt(payload.schedule_start_at)
    data["schedule_end_at"] = _parse_dt(payload.schedule_end_at)
    if data["schedule_start_at"] and data["schedule_end_at"] and data["schedule_end_at"] < data["schedule_start_at"]:
        raise HTTPException(status_code=422, detail="La fecha de cierre no puede ser menor a la de publicación.")
    if data.get("is_public_link_enabled") and not data.get("public_link_token"):
        data["public_link_token"] = _slugify_value(payload.nombre)[:80] or data["codigo"].lower()
    data["created_by"] = getattr(request.state, "user_name", None) or request.cookies.get("user_name")
    try:
        if data.get("template_id"):
            return create_instance_from_template(tenant_id, int(data["template_id"]), data)
        return create_instance(data)
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="Ya existe una campaña con ese código.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/encuestas/campanas/{instance_id}/save-template", status_code=201)
def api_save_campaign_as_template(instance_id: int, payload: SurveyTemplateSaveFromInstanceIn, request: Request):
    ensure_survey_schema()
    _require_encuestas_permission(request, "manage_surveys")
    tenant_id = _tenant_id(request)
    data = payload.model_dump()
    data["slug"] = _slugify_value(payload.slug or payload.nombre)
    data["created_by"] = getattr(request.state, "user_name", None) or request.cookies.get("user_name")
    try:
        return save_instance_as_template(instance_id, tenant_id, data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.patch("/api/encuestas/campanas/{instance_id}/draft")
def api_update_campaign_draft(instance_id: int, payload: SurveyInstanceDraftUpdateIn, request: Request):
    ensure_survey_schema()
    _require_encuestas_permission(request, "manage_surveys")
    data = _coerce_360_anonymity(payload.model_dump(exclude_unset=True))
    if "schedule_start_at" in data:
        data["schedule_start_at"] = _parse_dt(payload.schedule_start_at)
    if "schedule_end_at" in data:
        data["schedule_end_at"] = _parse_dt(payload.schedule_end_at)
    if data.get("schedule_start_at") and data.get("schedule_end_at") and data["schedule_end_at"] < data["schedule_start_at"]:
        raise HTTPException(status_code=422, detail="La fecha de cierre no puede ser menor a la de publicación.")
    try:
        instance = update_instance_draft(instance_id, _tenant_id(request), data)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not instance:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada.")
    return instance


@router.get("/api/encuestas/campanas/{instance_id}")
def api_get_campaign(instance_id: int, request: Request):
    ensure_survey_schema()
    _require_encuestas_permission(request, "view_module")
    instance = get_instance(instance_id, _tenant_id(request))
    if not instance:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada.")
    return instance


@router.get("/api/encuestas/campanas/{instance_id}/assignments")
def api_list_campaign_assignments(instance_id: int, request: Request):
    ensure_survey_schema()
    _require_encuestas_permission(request, "manage_surveys")
    return list_assignments(instance_id, _tenant_id(request))


@router.get("/api/encuestas/campanas/{instance_id}/dispatch-log")
def api_list_campaign_dispatch_log(instance_id: int, request: Request):
    ensure_survey_schema()
    _require_encuestas_permission(request, "manage_surveys")
    return list_dispatch_logs(instance_id, _tenant_id(request))


@router.get("/api/encuestas/campanas/{instance_id}/results")
def api_list_campaign_results(instance_id: int, request: Request):
    ensure_survey_schema()
    _require_encuestas_permission(request, "view_results_summary")
    return list_results(instance_id, _tenant_id(request))


@router.get("/api/encuestas/campanas/{instance_id}/analytics")
def api_campaign_analytics(
    instance_id: int,
    request: Request,
    department: str = Query(default=""),
    role: str = Query(default=""),
    company: str = Query(default=""),
    segment_by: str = Query(default="department"),
):
    ensure_survey_schema()
    _require_encuestas_permission(request, "view_results_summary")
    try:
        filters = {
            "department": department,
            "role": role,
            "company": company,
        }
        dashboard = get_results_dashboard(
            instance_id,
            _tenant_id(request),
            filters=filters,
            segment_by=segment_by,
        )
        return _sanitize_dashboard_payload(dashboard, request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Error interno del servidor") from exc


@router.get("/api/encuestas/campanas/{instance_id}/export.csv")
def api_export_campaign_csv(
    instance_id: int,
    request: Request,
    department: str = Query(default=""),
    role: str = Query(default=""),
    company: str = Query(default=""),
    segment_by: str = Query(default="department"),
):
    ensure_survey_schema()
    _require_encuestas_permission(request, "export_sensitive_results")
    dashboard = _sanitize_dashboard_payload(
        get_results_dashboard(
            instance_id,
            _tenant_id(request),
            filters={"department": department, "role": role, "company": company},
            segment_by=segment_by,
        ),
        request,
    )
    content = export_results_csv(instance_id, _tenant_id(request), dashboard=dashboard)
    headers = {
        "Content-Disposition": f'attachment; filename="{quote(f"encuesta_{instance_id}_resultados.csv")}"'
    }
    return FastAPIResponse(content, media_type="text/csv; charset=utf-8", headers=headers)


@router.get("/api/encuestas/campanas/{instance_id}/export.xlsx")
def api_export_campaign_excel(
    instance_id: int,
    request: Request,
    department: str = Query(default=""),
    role: str = Query(default=""),
    company: str = Query(default=""),
    segment_by: str = Query(default="department"),
):
    ensure_survey_schema()
    _require_encuestas_permission(request, "export_sensitive_results")
    dashboard = _sanitize_dashboard_payload(
        get_results_dashboard(
            instance_id,
            _tenant_id(request),
            filters={"department": department, "role": role, "company": company},
            segment_by=segment_by,
        ),
        request,
    )
    content = export_results_excel(instance_id, _tenant_id(request), dashboard=dashboard)
    headers = {
        "Content-Disposition": f'attachment; filename="{quote(f"encuesta_{instance_id}_resultados.xlsx")}"'
    }
    return FastAPIResponse(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )


@router.get("/api/encuestas/campanas/{instance_id}/export.pdf")
def api_export_campaign_pdf(
    instance_id: int,
    request: Request,
    department: str = Query(default=""),
    role: str = Query(default=""),
    company: str = Query(default=""),
    segment_by: str = Query(default="department"),
):
    ensure_survey_schema()
    _require_encuestas_permission(request, "export_sensitive_results")
    dashboard = _sanitize_dashboard_payload(
        get_results_dashboard(
            instance_id,
            _tenant_id(request),
            filters={"department": department, "role": role, "company": company},
            segment_by=segment_by,
        ),
        request,
    )
    content = export_results_pdf(instance_id, _tenant_id(request), dashboard=dashboard)
    headers = {
        "Content-Disposition": f'attachment; filename="{quote(f"encuesta_{instance_id}_resultados.pdf")}"'
    }
    return FastAPIResponse(content, media_type="application/pdf", headers=headers)


@router.post("/api/encuestas/campanas/{instance_id}/assignments/sync")
def api_sync_campaign_assignments(instance_id: int, payload: AssignmentSyncIn, request: Request):
    ensure_survey_schema()
    _require_encuestas_permission(request, "manage_surveys")
    sync_payload = payload.model_dump()
    sync_payload["assignment_rules"] = {"manual_groups": sync_payload.pop("manual_groups", [])}
    sync_payload["due_at"] = _parse_dt(payload.due_at)
    try:
        return sync_assignments(instance_id, _tenant_id(request), sync_payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/encuestas/campanas/{instance_id}/builder")
def api_get_campaign_builder(instance_id: int, request: Request):
    ensure_survey_schema()
    _require_encuestas_permission(request, "manage_surveys")
    instance = get_instance_builder(instance_id, _tenant_id(request))
    if not instance:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada.")
    return instance


@router.post("/api/encuestas/campanas/{instance_id}/sections", status_code=201)
def api_create_section(instance_id: int, payload: SurveySectionIn, request: Request):
    ensure_survey_schema()
    _require_encuestas_permission(request, "manage_surveys")
    try:
        section = create_section(instance_id, _tenant_id(request), payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not section:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada.")
    return section


@router.patch("/api/encuestas/campanas/{instance_id}/sections/{section_id}")
def api_update_section(instance_id: int, section_id: int, payload: SurveySectionUpdateIn, request: Request):
    ensure_survey_schema()
    _require_encuestas_permission(request, "manage_surveys")
    try:
        section = update_section(instance_id, section_id, _tenant_id(request), payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not section:
        raise HTTPException(status_code=404, detail="Seccion no encontrada.")
    return section


@router.post("/api/encuestas/campanas/{instance_id}/sections/reorder")
def api_reorder_sections(instance_id: int, payload: ReorderIn, request: Request):
    ensure_survey_schema()
    _require_encuestas_permission(request, "manage_surveys")
    ok = reorder_sections(instance_id, _tenant_id(request), payload.ids)
    if not ok:
        raise HTTPException(status_code=404, detail="No se pudieron reordenar las secciones.")
    return {"ok": True}


@router.post("/api/encuestas/campanas/{instance_id}/sections/{section_id}/questions", status_code=201)
def api_create_question(instance_id: int, section_id: int, payload: SurveyQuestionIn, request: Request):
    ensure_survey_schema()
    _require_encuestas_permission(request, "manage_surveys")
    try:
        question = create_question(instance_id, section_id, _tenant_id(request), payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not question:
        raise HTTPException(status_code=404, detail="Seccion no encontrada.")
    return question


@router.patch("/api/encuestas/campanas/{instance_id}/questions/{question_id}")
def api_update_question(instance_id: int, question_id: int, payload: SurveyQuestionUpdateIn, request: Request):
    ensure_survey_schema()
    _require_encuestas_permission(request, "manage_surveys")
    try:
        question = update_question(instance_id, question_id, _tenant_id(request), payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not question:
        raise HTTPException(status_code=404, detail="Pregunta no encontrada.")
    return question


@router.post("/api/encuestas/campanas/{instance_id}/questions/{question_id}/duplicate", status_code=201)
def api_duplicate_question(instance_id: int, question_id: int, request: Request):
    ensure_survey_schema()
    _require_encuestas_permission(request, "manage_surveys")
    question = duplicate_question(instance_id, question_id, _tenant_id(request))
    if not question:
        raise HTTPException(status_code=404, detail="Pregunta no encontrada.")
    return question


@router.post("/api/encuestas/campanas/{instance_id}/sections/{section_id}/questions/reorder")
def api_reorder_questions(instance_id: int, section_id: int, payload: ReorderIn, request: Request):
    ensure_survey_schema()
    _require_encuestas_permission(request, "manage_surveys")
    ok = reorder_questions(instance_id, section_id, _tenant_id(request), payload.ids)
    if not ok:
        raise HTTPException(status_code=404, detail="No se pudieron reordenar las preguntas.")
    return {"ok": True}


@router.get("/api/encuestas/campanas/{instance_id}/publish-validation")
def api_publish_validation(instance_id: int, request: Request):
    ensure_survey_schema()
    _require_encuestas_permission(request, "manage_surveys")
    validation = validate_instance_for_publish(instance_id, _tenant_id(request))
    if validation["errors"] == ["Encuesta no encontrada."]:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada.")
    return validation


@router.get("/api/encuestas/campanas/{instance_id}/preview")
def api_campaign_preview(instance_id: int, request: Request):
    ensure_survey_schema()
    _require_encuestas_permission(request, "manage_surveys")
    builder = get_instance_builder(instance_id, _tenant_id(request))
    if not builder:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada.")
    return {
        "instance_id": instance_id,
        "html": _render_preview_html(builder),
        "validation": builder.get("publish_validation") or {"ok": False, "errors": []},
    }


@router.post("/api/encuestas/campanas/{instance_id}/publish")
def api_publish_campaign(instance_id: int, request: Request):
    ensure_survey_schema()
    _require_encuestas_permission(request, "manage_surveys")
    validation = validate_instance_for_publish(instance_id, _tenant_id(request))
    if not validation["ok"]:
        raise HTTPException(status_code=409, detail={"message": "La encuesta no cumple validaciones previas.", "errors": validation["errors"]})
    try:
        instance = publish_instance(instance_id, _tenant_id(request))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not instance:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada.")
    return instance


@router.post("/api/encuestas/campanas/{instance_id}/close")
def api_close_campaign(instance_id: int, request: Request):
    ensure_survey_schema()
    _require_encuestas_permission(request, "manage_surveys")
    instance = close_instance(instance_id, _tenant_id(request))
    if not instance:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada.")
    return instance


@router.post("/api/encuestas/automation/run")
def api_run_encuestas_automation(request: Request, instance_id: int = Query(default=0)):
    ensure_survey_schema()
    _require_encuestas_permission(request, "manage_surveys")
    try:
        return queue_automation_job(_tenant_id(request), instance_id=instance_id or None)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/api/encuestas/campanas/{instance_id}", status_code=204)
def api_delete_or_archive_campaign(
    instance_id: int,
    request: Request,
    hard_delete: bool = Query(default=False),
):
    ensure_survey_schema()
    _require_encuestas_permission(request, "manage_surveys")
    deleted = archive_or_delete_instance(instance_id, _tenant_id(request), hard_delete=hard_delete)
    if not deleted:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada.")


@router.get("/api/encuestas/respuestas/{response_id}/session")
def api_get_response_session(response_id: int, request: Request):
    ensure_survey_schema()
    session_payload = get_response_session(response_id, _tenant_id(request))
    if not session_payload:
        raise HTTPException(status_code=404, detail="Respuesta no encontrada.")
    return session_payload


@router.get("/api/public/encuestas/respuestas/{response_id}/session")
def api_get_public_response_session(response_id: int, request: Request):
    return api_get_response_session(response_id, request)


@router.put("/api/encuestas/respuestas/{response_id}/save")
def api_save_response_draft(response_id: int, payload: ResponseSaveIn, request: Request):
    ensure_survey_schema()
    try:
        return save_response_draft(response_id, _tenant_id(request), payload.answers)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.put("/api/public/encuestas/respuestas/{response_id}/save")
def api_save_public_response_draft(response_id: int, payload: ResponseSaveIn, request: Request):
    return api_save_response_draft(response_id, payload, request)


@router.post("/api/encuestas/respuestas/{response_id}/submit")
def api_submit_response(response_id: int, payload: ResponseSaveIn, request: Request):
    ensure_survey_schema()
    try:
        return submit_response(response_id, _tenant_id(request), payload.answers)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/api/public/encuestas/respuestas/{response_id}/submit")
def api_submit_public_response(response_id: int, payload: ResponseSaveIn, request: Request):
    return api_submit_response(response_id, payload, request)
