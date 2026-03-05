from __future__ import annotations

from datetime import datetime
from html import escape
from io import BytesIO
from typing import Any, Callable, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from openpyxl import Workbook

SYSTEM_REPORT_HEADER_TEMPLATE_ID = "system-report-header"

router = APIRouter()


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_key(value: Any) -> str:
    return _normalize_text(value).lower()


def _get_core_callables() -> Tuple[Optional[Callable[[], List[Dict[str, str]]]], Optional[Callable[[], Dict[str, Any]]]]:
    try:
        from fastapi_modulo import main as core  # Import diferido para evitar ciclo.
    except Exception:
        return None, None
    load_plantillas_store = getattr(core, "_load_plantillas_store", None)
    load_login_identity = getattr(core, "_load_login_identity", None)
    if not callable(load_plantillas_store):
        load_plantillas_store = None
    if not callable(load_login_identity):
        load_login_identity = None
    return load_plantillas_store, load_login_identity


def _get_report_runtime():
    try:
        from fastapi_modulo import main as core
        from fastapi_modulo import db as core_db
        from fastapi_modulo.modulos.proyectando.data_store import load_sucursales_store
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo cargar runtime de reportes: {exc}") from exc
    return {
        "render_backend_page": getattr(core, "render_backend_page"),
        "SessionLocal": getattr(core, "SessionLocal"),
        "Usuario": getattr(core, "Usuario"),
        "Rol": getattr(core, "Rol"),
        "POAActivity": getattr(core, "POAActivity"),
        "StrategicObjectiveConfig": getattr(core, "StrategicObjectiveConfig"),
        "StrategicAxisConfig": getattr(core, "StrategicAxisConfig"),
        "DepartamentoOrganizacional": getattr(core, "DepartamentoOrganizacional", getattr(core_db, "DepartamentoOrganizacional", None)),
        "RegionOrganizacional": getattr(core, "RegionOrganizacional", getattr(core_db, "RegionOrganizacional", None)),
        "_decrypt_sensitive": getattr(core, "_decrypt_sensitive"),
        "_current_user_record": getattr(core, "_current_user_record"),
        "normalize_role_name": getattr(core, "normalize_role_name"),
        "get_current_role": getattr(core, "get_current_role"),
        "load_sucursales_store": load_sucursales_store,
    }


def _is_full_reports_access(request: Request, runtime: Dict[str, Any]) -> bool:
    role = runtime["normalize_role_name"](runtime["get_current_role"](request))
    return role in {"administrador", "superadministrador"}


def _resolve_user_scope(request: Request, db, runtime: Dict[str, Any]) -> Dict[str, str]:
    user = runtime["_current_user_record"](request, db)
    decrypt = runtime["_decrypt_sensitive"]
    session_name = _normalize_text(getattr(request.state, "user_name", None) or request.cookies.get("user_name"))
    username = _normalize_text(decrypt(getattr(user, "usuario", "")) if user else "") or session_name
    department = _normalize_text(getattr(user, "departamento", "") if user else "")
    return {
        "username": username,
        "department": department,
    }


def _build_alias_user_map(db, runtime: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    users = db.query(runtime["Usuario"]).all()
    by_alias: Dict[str, Dict[str, str]] = {}
    decrypt = runtime["_decrypt_sensitive"]
    roles_by_id = {
        int(getattr(r, "id", 0)): runtime["normalize_role_name"](getattr(r, "nombre", ""))
        for r in db.query(runtime["Rol"]).all()
    }
    for user in users:
        username = _normalize_text(decrypt(getattr(user, "usuario", "")))
        email = _normalize_text(decrypt(getattr(user, "correo", "")))
        full_name = _normalize_text(getattr(user, "nombre", ""))
        department = _normalize_text(getattr(user, "departamento", ""))
        role_name = roles_by_id.get(int(getattr(user, "rol_id", 0) or 0), "")
        payload = {
            "username": username,
            "nombre": full_name,
            "departamento": department,
            "rol": role_name,
        }
        for alias in {username, email, full_name}:
            key = _normalize_key(alias)
            if key and key not in by_alias:
                by_alias[key] = payload
    return by_alias


def _build_report_rows(request: Request, db, runtime: Dict[str, Any]) -> List[Dict[str, Any]]:
    poa_rows = db.query(runtime["POAActivity"]).all()
    objectives = {
        int(getattr(obj, "id", 0)): obj for obj in db.query(runtime["StrategicObjectiveConfig"]).all()
    }
    axes = {
        int(getattr(axis, "id", 0)): axis for axis in db.query(runtime["StrategicAxisConfig"]).all()
    }
    alias_map = _build_alias_user_map(db, runtime)

    sucursales = runtime["load_sucursales_store"]()
    sucursal_by_key: Dict[str, Dict[str, str]] = {}
    for item in sucursales:
        name = _normalize_text(item.get("nombre"))
        code = _normalize_text(item.get("codigo"))
        region = _normalize_text(item.get("region"))
        payload = {"sucursal": name, "region": region}
        for key in {_normalize_key(name), _normalize_key(code)}:
            if key and key not in sucursal_by_key:
                sucursal_by_key[key] = payload

    rows: List[Dict[str, Any]] = []
    for activity in poa_rows:
        objective = objectives.get(int(getattr(activity, "objective_id", 0) or 0))
        axis = axes.get(int(getattr(objective, "eje_id", 0) or 0)) if objective else None
        responsible_raw = _normalize_text(getattr(activity, "responsable", ""))
        responsible = alias_map.get(_normalize_key(responsible_raw), {})
        department = _normalize_text(responsible.get("departamento"))
        sucursal_meta = sucursal_by_key.get(_normalize_key(department), {})
        rows.append(
            {
                "id": int(getattr(activity, "id", 0) or 0),
                "actividad": _normalize_text(getattr(activity, "nombre", "")),
                "responsable": responsible_raw,
                "usuario": _normalize_text(responsible.get("username")) or responsible_raw,
                "departamento": department,
                "sucursal": _normalize_text(sucursal_meta.get("sucursal")),
                "region": _normalize_text(sucursal_meta.get("region")),
                "objetivo": _normalize_text(getattr(objective, "nombre", "") if objective else ""),
                "eje": _normalize_text(getattr(axis, "nombre", "") if axis else ""),
                "fecha_inicial": (
                    getattr(activity, "fecha_inicial").isoformat()
                    if getattr(activity, "fecha_inicial", None)
                    else ""
                ),
                "fecha_final": (
                    getattr(activity, "fecha_final").isoformat()
                    if getattr(activity, "fecha_final", None)
                    else ""
                ),
            }
        )
    return rows


def _collect_filter_options(rows: List[Dict[str, Any]], runtime: Dict[str, Any], db) -> Dict[str, List[str]]:
    users = sorted(
        {
            _normalize_text(item.get("usuario"))
            for item in rows
            if _normalize_text(item.get("usuario"))
        },
        key=str.lower,
    )
    departments = sorted(
        {
            _normalize_text(item.get("departamento"))
            for item in rows
            if _normalize_text(item.get("departamento"))
        },
        key=str.lower,
    )
    sucursales = sorted(
        {
            _normalize_text(item.get("sucursal"))
            for item in rows
            if _normalize_text(item.get("sucursal"))
        },
        key=str.lower,
    )
    regiones = sorted(
        {
            _normalize_text(item.get("region"))
            for item in rows
            if _normalize_text(item.get("region"))
        },
        key=str.lower,
    )

    # Completa catálogos para filtros aunque no haya datos POA.
    for item in runtime["load_sucursales_store"]():
        name = _normalize_text(item.get("nombre"))
        region = _normalize_text(item.get("region"))
        if name and name not in sucursales:
            sucursales.append(name)
        if region and region not in regiones:
            regiones.append(region)
    RegionModel = runtime.get("RegionOrganizacional")
    if RegionModel is not None:
        for reg in db.query(RegionModel).all():
            nombre = _normalize_text(getattr(reg, "nombre", ""))
            if nombre and nombre not in regiones:
                regiones.append(nombre)
    DepartmentModel = runtime.get("DepartamentoOrganizacional")
    if DepartmentModel is not None:
        for dep in db.query(DepartmentModel).all():
            nombre = _normalize_text(getattr(dep, "nombre", ""))
            if nombre and nombre not in departments:
                departments.append(nombre)
    return {
        "usuario": sorted(set(users), key=str.lower),
        "sucursal": sorted(set(sucursales), key=str.lower),
        "departamento": sorted(set(departments), key=str.lower),
        "region": sorted(set(regiones), key=str.lower),
    }


def _filter_report_rows(
    rows: List[Dict[str, Any]],
    filters: Dict[str, str],
) -> List[Dict[str, Any]]:
    def matches(row: Dict[str, Any]) -> bool:
        for key, expected in filters.items():
            value = _normalize_text(expected)
            if not value:
                continue
            if _normalize_key(row.get(key)) != _normalize_key(value):
                return False
        return True

    return [row for row in rows if matches(row)]


def _resolve_effective_filters(
    request: Request,
    runtime: Dict[str, Any],
    db,
    requested: Dict[str, str],
) -> Tuple[Dict[str, str], bool]:
    full_access = _is_full_reports_access(request, runtime)
    if full_access:
        return requested, True
    scope = _resolve_user_scope(request, db, runtime)
    forced = dict(requested)
    forced["usuario"] = scope.get("username", "")
    # Si no hay usuario ligado en sesión, limita por departamento si existe.
    if not forced["usuario"] and scope.get("department"):
        forced["departamento"] = scope["department"]
    if not forced["usuario"] and not forced.get("departamento"):
        forced["usuario"] = "__NO_ACCESS__"
    return forced, False


def _build_reportes_content(can_access_all: bool) -> str:
    scope_text = (
        "Acceso completo habilitado (Administrador/Superadministrador)."
        if can_access_all
        else "Acceso limitado a tu alcance de usuario."
    )
    return (
        "<section class='content-section'>"
        "<div class='content-section-head'><h2 class='content-section-title'>Reportes</h2></div>"
        "<div class='content-section-body'>"
        "<p>Consulta y exporta avances con control de permisos por rol.</p>"
        f"<p style='margin-top:6px;color:#475569;font-style:italic'>{escape(scope_text)}</p>"
        "<div class='report-filters' style='display:grid;grid-template-columns:repeat(4,minmax(160px,1fr));gap:10px;margin-top:10px;'>"
        "<label>Usuario<select id='rep-f-usuario' class='campo-personalizado'><option value=''>Todos</option></select></label>"
        "<label>Sucursal<select id='rep-f-sucursal' class='campo-personalizado'><option value=''>Todas</option></select></label>"
        "<label>Departamento<select id='rep-f-departamento' class='campo-personalizado'><option value=''>Todos</option></select></label>"
        "<label>Región<select id='rep-f-region' class='campo-personalizado'><option value=''>Todas</option></select></label>"
        "</div>"
        "<div style='display:flex;gap:10px;flex-wrap:wrap;margin-top:10px;'>"
        "<button id='rep-aplicar' class='color-btn color-btn--primary' type='button'>Aplicar filtros</button>"
        "<button id='rep-limpiar' class='color-btn color-btn--ghost' type='button'>Limpiar</button>"
        "<a class='color-btn color-btn--ghost' href='/api/reportes/export/html'>Exportar HTML</a>"
        "<a class='color-btn color-btn--ghost' href='/api/reportes/export/pdf'>Exportar PDF</a>"
        "<a class='color-btn color-btn--ghost' href='/api/reportes/export/excel'>Exportar Excel</a>"
        "</div>"
        "<div id='rep-kpis' style='display:grid;grid-template-columns:repeat(4,minmax(120px,1fr));gap:10px;margin-top:12px;'></div>"
        "<div style='overflow:auto;margin-top:10px;border:1px solid #cbd5e1;border-radius:10px;'>"
        "<table class='table-excel' style='min-width:980px'>"
        "<thead><tr><th>Actividad</th><th>Responsable</th><th>Usuario</th><th>Sucursal</th><th>Departamento</th><th>Región</th><th>Eje</th><th>Objetivo</th></tr></thead>"
        "<tbody id='rep-body'></tbody>"
        "</table></div>"
        "<p id='rep-msg' style='margin-top:8px;color:#64748b;'></p>"
        "</div></section>"
        "<script>"
        "(function(){"
        "const ids=['usuario','sucursal','departamento','region'];"
        "const byId=(id)=>document.getElementById(id);"
        "const body=byId('rep-body');"
        "const msg=byId('rep-msg');"
        "const kpis=byId('rep-kpis');"
        "const filterEl=(name)=>byId('rep-f-'+name);"
        "const buildQuery=()=>{const p=new URLSearchParams();ids.forEach((k)=>{const v=(filterEl(k)?.value||'').trim();if(v)p.set(k,v)});return p.toString();};"
        "const fillSelect=(name,items)=>{const el=filterEl(name);if(!el)return;const current=el.value;const label=name==='usuario'?'Todos':(name==='sucursal'?'Todas':(name==='region'?'Todas':'Todos'));el.innerHTML='<option value=\"\">'+label+'</option>' + (items||[]).map((x)=>'<option value=\"'+String(x).replace(/\"/g,'&quot;')+'\">'+x+'</option>').join('');if(current){el.value=current;}};"
        "const renderRows=(rows)=>{if(!body)return;body.innerHTML=(rows||[]).map((r)=>'<tr><td>'+ (r.actividad||'N/D') +'</td><td>'+ (r.responsable||'N/D') +'</td><td>'+ (r.usuario||'N/D') +'</td><td>'+ (r.sucursal||'N/D') +'</td><td>'+ (r.departamento||'N/D') +'</td><td>'+ (r.region||'N/D') +'</td><td>'+ (r.eje||'N/D') +'</td><td>'+ (r.objetivo||'N/D') +'</td></tr>').join('') || '<tr><td colspan=\"8\" style=\"text-align:center;color:#64748b;\">Sin resultados</td></tr>';};"
        "const renderKpis=(summary)=>{if(!kpis)return;const cards=[['Actividades',summary.total_actividades],['Usuarios',summary.total_usuarios],['Departamentos',summary.total_departamentos],['Regiones',summary.total_regiones]];kpis.innerHTML=cards.map((c)=>'<article style=\"border:1px solid #cbd5e1;border-radius:10px;padding:10px;background:#fff\"><div style=\"font-size:12px;color:#64748b\">'+c[0]+'</div><div style=\"font-size:24px;font-weight:700;color:#0f172a\">'+String(c[1]||0)+'</div></article>').join('');};"
        "const load=async()=>{try{const q=buildQuery();const res=await fetch('/api/reportes/datos'+(q?('?'+q):''));const data=await res.json();if(!res.ok||!data.success){throw new Error(data.error||'No se pudo cargar reportes');}ids.forEach((k)=>fillSelect(k,(data.filters||{})[k]||[]));renderRows(data.rows||[]);renderKpis(data.summary||{});if(msg){msg.textContent='Mostrando '+String((data.rows||[]).length)+' registro(s).';}}catch(err){if(msg)msg.textContent=String(err&&err.message||err);}};"
        "byId('rep-aplicar')?.addEventListener('click',load);"
        "byId('rep-limpiar')?.addEventListener('click',()=>{ids.forEach((k)=>{const el=filterEl(k);if(el)el.value='';});load();});"
        "load();"
        "})();"
        "</script>"
    )


def _render_reportes_page(request: Request, title: str = "Reportes") -> HTMLResponse:
    runtime = _get_report_runtime()
    db = runtime["SessionLocal"]()
    try:
        can_access_all = _is_full_reports_access(request, runtime)
    finally:
        db.close()
    content = _build_reportes_content(can_access_all=can_access_all)
    try:
        from fastapi_modulo.main import render_backend_page
    except Exception:
        return HTMLResponse("<h1>Reportes</h1><p>Módulo de reportes.</p>")
    return render_backend_page(
        request,
        title=title,
        description="Analítica y exportación con filtros y permisos por rol.",
        content=content,
        hide_floating_actions=True,
        show_page_header=True,
    )


@router.get("/reportes", response_class=HTMLResponse)
def reportes_page(request: Request) -> HTMLResponse:
    return _render_reportes_page(request, "Reportes")


@router.get("/reportes/documentos", response_class=HTMLResponse)
def reportes_documentos_page(request: Request) -> HTMLResponse:
    return _render_reportes_page(request, "Reportes de documentos")


def build_default_report_header_template() -> Dict[str, str]:
    now_iso = datetime.utcnow().isoformat()
    return {
        "id": SYSTEM_REPORT_HEADER_TEMPLATE_ID,
        "nombre": "Encabezado",
        "html": (
            "<header class='reporte-encabezado'>"
            "<div class='reporte-encabezado__marca'>{{ empresa }}</div>"
            "<div class='reporte-encabezado__meta'>"
            "<h1>{{ titulo_reporte }}</h1>"
            "<p>{{ subtitulo_reporte }}</p>"
            "</div>"
            "<div class='reporte-encabezado__fecha'>Fecha: {{ fecha_reporte }}</div>"
            "</header>"
        ),
        "css": (
            ".reporte-encabezado { display:flex; align-items:center; justify-content:space-between; gap:16px; "
            "padding:16px 20px; border:1px solid #cbd5e1; border-radius:12px; background:#f8fafc; font-family:Arial,sans-serif; } "
            ".reporte-encabezado__marca { font-weight:800; color:#0f172a; font-size:1.1rem; letter-spacing:.04em; } "
            ".reporte-encabezado__meta h1 { margin:0; font-size:1.05rem; color:#0f172a; } "
            ".reporte-encabezado__meta p { margin:4px 0 0; color:#475569; font-size:.88rem; } "
            ".reporte-encabezado__fecha { color:#334155; font-size:.84rem; white-space:nowrap; }"
        ),
        "created_at": now_iso,
        "updated_at": now_iso,
    }


def _get_report_header_template() -> Dict[str, str]:
    load_plantillas_store, _ = _get_core_callables()
    if not load_plantillas_store:
        return build_default_report_header_template()
    templates = load_plantillas_store()
    for tpl in templates:
        if str(tpl.get("id", "")).strip() == SYSTEM_REPORT_HEADER_TEMPLATE_ID:
            return tpl
    for tpl in templates:
        if str(tpl.get("nombre", "")).strip().lower() == "encabezado":
            return tpl
    return build_default_report_header_template()


def _apply_template_context(content: str, context: Dict[str, str]) -> str:
    rendered = content or ""
    for key, value in context.items():
        rendered = rendered.replace(f"{{{{ {key} }}}}", value)
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def _build_report_export_context() -> Dict[str, str]:
    _, load_login_identity = _get_core_callables()
    identidad = load_login_identity() if load_login_identity else {}
    empresa = str(identidad.get("company_short_name") or "SIPET")
    return {
        "empresa": empresa,
        "titulo_reporte": "Reporte consolidado",
        "subtitulo_reporte": "Avance, desempeno y seguimiento",
        "fecha_reporte": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def _build_report_export_rows(request: Request) -> List[Dict[str, str]]:
    runtime = _get_report_runtime()
    db = runtime["SessionLocal"]()
    try:
        requested = {"usuario": "", "sucursal": "", "departamento": "", "region": ""}
        effective, can_access_all = _resolve_effective_filters(request, runtime, db, requested)
        base_rows = _build_report_rows(request, db, runtime)
        rows = _filter_report_rows(base_rows, effective)
        return [
            {
                "reporte": "Reporte ejecutivo",
                "descripcion": (
                    "Acceso completo: consolidado global"
                    if can_access_all
                    else "Acceso limitado por rol"
                ),
                "formato": "PDF / Excel",
            },
            {
                "reporte": "Actividades POA",
                "descripcion": f"Registros visibles: {len(rows)}",
                "formato": "HTML / Excel",
            },
            {
                "reporte": "Filtros aplicados",
                "descripcion": ", ".join(
                    f"{k}={v}" for k, v in effective.items() if _normalize_text(v)
                ) or "Sin filtros",
                "formato": "Contexto",
            },
        ]
    finally:
        db.close()


def _build_report_export_html_document(request: Request) -> str:
    template = _get_report_header_template()
    context = _build_report_export_context()
    header_html = _apply_template_context(template.get("html", ""), context)
    header_css = template.get("css", "")
    rows = _build_report_export_rows(request)
    rows_html = "".join(
        (
            "<tr>"
            f"<td>{escape(row['reporte'])}</td>"
            f"<td>{escape(row['descripcion'])}</td>"
            f"<td>{escape(row['formato'])}</td>"
            "</tr>"
        )
        for row in rows
    )
    return (
        "<!doctype html><html lang='es'><head><meta charset='utf-8'>"
        "<title>Reporte consolidado</title>"
        "<style>"
        f"{header_css}"
        "body{font-family:Arial,sans-serif;background:#fff;color:#0f172a;padding:24px;}"
        ".reporte-bloque{margin-top:18px;}"
        "table{width:100%;border-collapse:collapse;}"
        "th,td{border:1px solid #cbd5e1;padding:10px;text-align:left;font-size:14px;}"
        "th{background:#f1f5f9;}"
        "</style></head><body>"
        f"{header_html}"
        "<section class='reporte-bloque'>"
        "<h2>Detalle de reportes</h2>"
        "<table><thead><tr><th>Reporte</th><th>Descripcion</th><th>Formato</th></tr></thead>"
        f"<tbody>{rows_html}</tbody></table>"
        "</section></body></html>"
    )


def _build_report_export_xlsx_bytes(request: Request) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Reporte"
    sheet.append(["Reporte", "Descripcion", "Formato"])
    for row in _build_report_export_rows(request):
        sheet.append([row["reporte"], row["descripcion"], row["formato"]])
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


@router.get("/api/reportes/datos")
def reportes_datos(
    request: Request,
    usuario: str = Query(default=""),
    sucursal: str = Query(default=""),
    departamento: str = Query(default=""),
    region: str = Query(default=""),
):
    runtime = _get_report_runtime()
    db = runtime["SessionLocal"]()
    try:
        requested = {
            "usuario": _normalize_text(usuario),
            "sucursal": _normalize_text(sucursal),
            "departamento": _normalize_text(departamento),
            "region": _normalize_text(region),
        }
        effective, can_access_all = _resolve_effective_filters(request, runtime, db, requested)
        rows = _build_report_rows(request, db, runtime)
        filtered_rows = _filter_report_rows(rows, effective)
        filters = _collect_filter_options(rows, runtime, db)
        if not can_access_all:
            # En alcance limitado solo ve sus opciones efectivas.
            for key in ("usuario", "sucursal", "departamento", "region"):
                value = _normalize_text(effective.get(key))
                if value:
                    filters[key] = [value]
        summary = {
            "total_actividades": len(filtered_rows),
            "total_usuarios": len({_normalize_key(row.get("usuario")) for row in filtered_rows if row.get("usuario")}),
            "total_departamentos": len({_normalize_key(row.get("departamento")) for row in filtered_rows if row.get("departamento")}),
            "total_regiones": len({_normalize_key(row.get("region")) for row in filtered_rows if row.get("region")}),
        }
        return JSONResponse(
            {
                "success": True,
                "can_access_all": can_access_all,
                "requested_filters": requested,
                "effective_filters": effective,
                "filters": filters,
                "rows": filtered_rows,
                "summary": summary,
            }
        )
    finally:
        db.close()


@router.get("/reportes/exportar-html", response_class=HTMLResponse)
def exportar_reporte_html_legacy(request: Request) -> HTMLResponse:
    html = _build_report_export_html_document(request)
    return HTMLResponse(content=html)


@router.get("/api/reportes/export/html", response_class=HTMLResponse)
def exportar_reporte_html(request: Request) -> HTMLResponse:
    html = _build_report_export_html_document(request)
    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": "attachment; filename=reporte_consolidado.html"},
    )


@router.get("/api/reportes/export/pdf", response_class=HTMLResponse)
def exportar_reporte_pdf(request: Request) -> HTMLResponse:
    # Fallback mientras no exista motor PDF en el proyecto.
    html = _build_report_export_html_document(request)
    return HTMLResponse(
        content=html,
        headers={"Content-Disposition": "attachment; filename=reporte_consolidado.html"},
    )


@router.get("/api/reportes/export/excel")
def exportar_reporte_excel(request: Request) -> Response:
    return Response(
        content=_build_report_export_xlsx_bytes(request),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reporte_consolidado.xlsx"},
    )
