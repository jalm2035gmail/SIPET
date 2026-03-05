import os
import json

# Módulo inicial para endpoints y lógica de departamentos
from fastapi import APIRouter, Request, Body, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from typing import List, Dict, Set, Any
from fastapi_modulo.db import SessionLocal, DepartamentoOrganizacional, Base, engine

router = APIRouter()
DEPARTAMENTOS_TEMPLATE_PATH = os.path.join("fastapi_modulo", "modulos", "empleados", "departamentos.html")
DEPARTAMENTOS_PUBLIC_ACCESS = str(
    os.getenv("DEPARTAMENTOS_PUBLIC_ACCESS", "0")
).strip().lower() in {"1", "true", "yes", "on"}


def _ensure_departamentos_schema() -> None:
    # Crea la tabla si no existe (producción sin migración previa).
    Base.metadata.create_all(bind=engine, tables=[DepartamentoOrganizacional.__table__], checkfirst=True)


def _enforce_departamentos_write_permission(request: Request) -> None:
    # Temporal: permitir operación abierta del módulo de departamentos.
    if DEPARTAMENTOS_PUBLIC_ACCESS:
        return
    from fastapi_modulo.main import require_admin_or_superadmin

    require_admin_or_superadmin(request)


def _render_departamentos_page(request: Request) -> HTMLResponse:
    from fastapi_modulo.main import render_backend_page

    try:
        with open(DEPARTAMENTOS_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            areas_content = fh.read()
    except OSError:
        areas_content = ""
    return render_backend_page(
        request,
        title="Departamentos",
        description="Administra la estructura de departamentos de la organización",
        content=areas_content,
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/departamentos", response_class=HTMLResponse)
def departamentos_page(request: Request):
    # Redirige a la vista backend oficial con estilos y layout unificados.
    return RedirectResponse(url="/inicio/departamentos", status_code=307)


@router.get("/inicio/departamentos", response_class=HTMLResponse)
def inicio_departamentos_page(request: Request):
    return _render_departamentos_page(request)


# ── Puestos laborales store ────────────────────────────────────────────────────
_PUESTOS_PATH = os.path.join(
    os.environ.get("RUNTIME_STORE_DIR") or
    os.path.join(os.environ.get("SIPET_DATA_DIR") or os.path.expanduser("~/.sipet/data"),
                 "runtime_store",
                 (os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "development").strip().lower()),
    "puestos_laborales.json"
)


def _load_puestos() -> list:
    try:
        p = _PUESTOS_PATH
        if os.path.exists(p):
            return json.loads(open(p, encoding="utf-8").read())
    except Exception:
        pass
    return []


def _save_puestos(data: list) -> None:
    import pathlib, json as _json
    pathlib.Path(_PUESTOS_PATH).parent.mkdir(parents=True, exist_ok=True)
    open(_PUESTOS_PATH, "w", encoding="utf-8").write(_json.dumps(data, ensure_ascii=False, indent=2))


@router.get("/api/puestos-laborales")
def api_puestos_laborales_list():
    return {"success": True, "data": _load_puestos()}


@router.post("/api/puestos-laborales")
async def api_puestos_laborales_save(request: Request):
    import uuid as _uuid, json as _json
    try:
        body = await request.json()
        if not isinstance(body, dict):
            raise ValueError
        action = body.get("action", "save")
        puestos = _load_puestos()

        if action == "delete":
            pid = str(body.get("id", ""))
            puestos = [p for p in puestos if p.get("id") != pid]
            _save_puestos(puestos)
            return {"success": True, "data": puestos}

        if action == "update_notebook":
            pid = str(body.get("id", ""))
            idx = next((i for i, p in enumerate(puestos) if p.get("id") == pid), None)
            if idx is not None:
                puestos[idx]["habilidades_requeridas"] = body.get("habilidades_requeridas", [])
                puestos[idx]["colaboradores_asignados"] = body.get("colaboradores_asignados", [])
                _save_puestos(puestos)
                return {"success": True, "data": puestos}
            return {"success": False, "error": "Puesto no encontrado"}

        # upsert
        existing = next((p for p in puestos if p.get("id") == str(body.get("id", ""))), {})
        puesto = {
            "id":          str(body.get("id") or _uuid.uuid4()),
            "nombre":      str(body.get("nombre") or "").strip(),
            "area":        str(body.get("area") or "").strip(),
            "nivel":       str(body.get("nivel") or "").strip(),
            "descripcion": str(body.get("descripcion") or "").strip(),
            "habilidades_requeridas":  existing.get("habilidades_requeridas", []),
            "colaboradores_asignados": existing.get("colaboradores_asignados", []),
        }
        if not puesto["nombre"]:
            return {"success": False, "error": "El nombre es requerido"}, 400
        idx = next((i for i, p in enumerate(puestos) if p.get("id") == puesto["id"]), None)
        if idx is not None:
            puestos[idx] = puesto
        else:
            puestos.append(puesto)
        _save_puestos(puestos)
        return {"success": True, "data": puestos, "puesto": puesto}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/inicio/departamentos/puestos-laborales", response_class=HTMLResponse)
def puestos_laborales_page(request: Request):
    from fastapi_modulo.main import render_backend_page

    content = """
<style>
.pl-wrap { max-width: 860px; display: flex; flex-direction: column; gap: 18px; }
/* form card */
.pl-card {
    background: #fff;
    border: 1px solid color-mix(in srgb, var(--button-bg,#0f172a) 14%, #ffffff 86%);
    border-radius: 14px; padding: 22px;
}
.pl-card-title { font-size: 1rem; font-weight: 700; color: var(--sidebar-bottom,#0f172a); margin: 0 0 16px; }
.pl-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px 16px; }
.pl-field { display: flex; flex-direction: column; gap: 5px; }
.pl-field.full { grid-column: 1 / -1; }
.pl-label { font-size: 0.8rem; font-weight: 600; color: color-mix(in srgb,var(--button-bg,#0f172a) 55%,#ffffff 45%); }
.pl-input, .pl-select, .pl-textarea {
    border: 1px solid color-mix(in srgb,var(--button-bg,#0f172a) 18%,#ffffff 82%);
    border-radius: 10px; padding: 9px 12px; font: inherit;
    color: var(--navbar-text,#0f172a); background: var(--field-color,#fff);
    outline: none; transition: border-color 0.15s;
}
.pl-input:focus, .pl-select:focus, .pl-textarea:focus {
    border-color: color-mix(in srgb,var(--button-bg,#0f172a) 40%,#ffffff 60%);
}
.pl-textarea { min-height: 80px; resize: vertical; }
.pl-form-actions { display: flex; gap: 10px; align-items: center; margin-top: 6px; }
.pl-btn-save {
    border: none; border-radius: 10px; padding: 9px 22px;
    background: color-mix(in srgb,var(--button-bg,#0f172a) 90%,#ffffff 10%);
    color: #fff; font-size: 0.9rem; font-weight: 600; cursor: pointer; transition: opacity .15s;
}
.pl-btn-save:hover { opacity: .85; }
.pl-btn-cancel {
    border: 1px solid color-mix(in srgb,var(--button-bg,#0f172a) 18%,#ffffff 82%);
    border-radius: 10px; padding: 9px 18px; background: transparent;
    color: var(--sidebar-bottom,#0f172a); font-size: 0.9rem; cursor: pointer;
    display: none;
}
.pl-msg { font-size: 0.82rem; color: #22c55e; display: none; }
/* table */
.pl-table-wrap { overflow-x: auto; border-radius: 10px; border: 1px solid color-mix(in srgb,var(--button-bg,#0f172a) 12%,#ffffff 88%); }
.pl-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.pl-table thead th {
    padding: 11px 14px; text-align: left; font-size: 0.75rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: .05em;
    color: color-mix(in srgb,var(--button-bg,#0f172a) 50%,#ffffff 50%);
    background: color-mix(in srgb,var(--button-bg,#0f172a) 5%,#ffffff 95%);
    border-bottom: 1px solid color-mix(in srgb,var(--button-bg,#0f172a) 10%,#ffffff 90%);
}
.pl-table tbody tr { border-bottom: 1px solid color-mix(in srgb,var(--button-bg,#0f172a) 7%,#ffffff 93%); transition: background .12s; }
.pl-table tbody tr:last-child { border-bottom: none; }
.pl-table tbody tr:hover { background: color-mix(in srgb,var(--button-bg,#0f172a) 3%,#ffffff 97%); }
.pl-table td { padding: 11px 14px; color: var(--sidebar-bottom,#0f172a); vertical-align: top; }
.pl-table td.area-cell { color: color-mix(in srgb,var(--button-bg,#0f172a) 50%,#ffffff 50%); font-size: 0.82rem; }
.pl-table td.desc-cell { color: color-mix(in srgb,var(--button-bg,#0f172a) 45%,#ffffff 55%); font-size: 0.82rem; max-width: 280px; }
.pl-act-btn { border: none; background: none; cursor: pointer; padding: 4px 6px; border-radius: 6px; font-size: 0.82rem; transition: background .12s; }
.pl-act-btn.edit { color: color-mix(in srgb,var(--button-bg,#0f172a) 45%,#ffffff 55%); }
.pl-act-btn.edit:hover { background: color-mix(in srgb,var(--button-bg,#0f172a) 10%,#ffffff 90%); }
.pl-act-btn.del { color: #ef4444; }
.pl-act-btn.del:hover { background: #fee2e2; }
.pl-empty { text-align: center; padding: 32px; color: color-mix(in srgb,var(--button-bg,#0f172a) 35%,#ffffff 65%); font-size: 0.875rem; }
@media(max-width:620px){ .pl-grid { grid-template-columns: 1fr; } .pl-field.full { grid-column: 1; } }
/* Notebook drawer */
.pl-nb-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.18); z-index: 1000; display: none; }
.pl-nb-drawer { position: fixed; top: 0; right: 0; bottom: 0; width: min(500px,95vw); background: #fff; z-index: 1001; box-shadow: -4px 0 28px rgba(0,0,0,.12); display: flex; flex-direction: column; transform: translateX(100%); transition: transform .28s cubic-bezier(.4,0,.2,1); }
.pl-nb-drawer.open { transform: translateX(0); }
.pl-nb-head { padding: 16px 20px; border-bottom: 1px solid color-mix(in srgb,var(--button-bg,#0f172a) 10%,#ffffff 90%); display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.pl-nb-head-sub { font-size: 0.72rem; color: color-mix(in srgb,var(--button-bg,#0f172a) 40%,#ffffff 60%); font-weight: 400; }
.pl-nb-titulo { font-size: 1rem; font-weight: 700; color: var(--sidebar-bottom,#0f172a); flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pl-nb-close { border: none; background: none; cursor: pointer; font-size: 1.4rem; line-height: 1; color: color-mix(in srgb,var(--button-bg,#0f172a) 45%,#ffffff 55%); padding: 2px 6px; border-radius: 6px; transition: background .12s; }
.pl-nb-close:hover { background: color-mix(in srgb,var(--button-bg,#0f172a) 8%,#ffffff 92%); }
.pl-nb-tabs { display: flex; padding: 12px 20px 0; gap: 2px; border-bottom: 1px solid color-mix(in srgb,var(--button-bg,#0f172a) 10%,#ffffff 90%); }
.pl-nb-tab { border: none; background: none; cursor: pointer; padding: 9px 16px; font-size: 0.84rem; font-weight: 600; color: color-mix(in srgb,var(--button-bg,#0f172a) 42%,#ffffff 58%); border-bottom: 2.5px solid transparent; margin-bottom: -1px; border-radius: 6px 6px 0 0; transition: color .14s, border-color .14s, background .14s; }
.pl-nb-tab:hover { color: var(--sidebar-bottom,#0f172a); background: color-mix(in srgb,var(--button-bg,#0f172a) 5%,#ffffff 95%); }
.pl-nb-tab.active { color: var(--sidebar-bottom,#0f172a); border-bottom-color: var(--button-bg,#0f172a); }
.pl-nb-body { flex: 1; overflow-y: auto; padding: 18px 20px; }
.pl-nb-panel { display: none; }
.pl-nb-panel.active { display: block; }
.pl-nb-loading { color: color-mix(in srgb,var(--button-bg,#0f172a) 40%,#ffffff 60%); font-size: 0.85rem; }
.pl-nb-hab-row { display: flex; align-items: center; gap: 8px; padding: 7px 10px; border: 1px solid #e2e8f0; border-radius: 8px; background: #fff; }
.pl-nb-hab-nombre { flex: 1; font-size: 0.875rem; font-weight: 600; color: var(--sidebar-bottom,#0f172a); }
.pl-nb-hab-badge { flex-shrink: 0; font-size: 0.78rem; font-weight: 700; background: color-mix(in srgb,var(--button-bg,#0f172a) 12%,#ffffff 88%); color: var(--sidebar-bottom,#0f172a); padding: 2px 8px; border-radius: 20px; }
.pl-nb-hab-del { flex-shrink: 0; border: 0; background: transparent; color: #94a3b8; font-size: 1.1rem; line-height: 1; cursor: pointer; padding: 0 2px; transition: color .12s; }
.pl-nb-hab-del:hover { color: #ef4444; }
.pl-nb-search { width: 100%; box-sizing: border-box; border: 1px solid color-mix(in srgb,var(--button-bg,#0f172a) 18%,#ffffff 82%); border-radius: 10px; padding: 9px 13px; font: inherit; font-size: 0.875rem; margin-bottom: 10px; outline: none; }
.pl-nb-search:focus { border-color: color-mix(in srgb,var(--button-bg,#0f172a) 38%,#ffffff 62%); }
.pl-nb-col-item { display: flex; align-items: center; gap: 10px; padding: 9px 10px; border-radius: 8px; cursor: pointer; transition: background .12s; }
.pl-nb-col-item:hover { background: color-mix(in srgb,var(--button-bg,#0f172a) 5%,#ffffff 95%); }
.pl-nb-col-item input[type=checkbox] { width: 15px; height: 15px; flex-shrink: 0; accent-color: var(--button-bg,#0f172a); cursor: pointer; }
.pl-nb-col-name { font-size: 0.875rem; font-weight: 600; color: var(--sidebar-bottom,#0f172a); }
.pl-nb-col-sub { font-size: 0.76rem; color: color-mix(in srgb,var(--button-bg,#0f172a) 45%,#ffffff 55%); }
.pl-nb-avatar { width: 32px; height: 32px; border-radius: 50%; object-fit: cover; background: color-mix(in srgb,var(--button-bg,#0f172a) 12%,#ffffff 88%); display: flex; align-items: center; justify-content: center; font-size: 0.78rem; font-weight: 700; color: var(--sidebar-bottom,#0f172a); flex-shrink: 0; }
.pl-nb-save-bar { padding: 14px 20px; border-top: 1px solid color-mix(in srgb,var(--button-bg,#0f172a) 10%,#ffffff 90%); display: flex; gap: 10px; align-items: center; }
.pl-nb-btn-save { border: none; border-radius: 10px; padding: 9px 22px; background: color-mix(in srgb,var(--button-bg,#0f172a) 90%,#ffffff 10%); color: #fff; font-size: 0.9rem; font-weight: 600; cursor: pointer; transition: opacity .15s; }
.pl-nb-btn-save:hover { opacity: .85; }
.pl-nb-saved { font-size: 0.82rem; color: #22c55e; display: none; }
.pl-act-btn.nb { color: color-mix(in srgb,var(--button-bg,#0f172a) 45%,#ffffff 55%); }
.pl-act-btn.nb:hover { background: color-mix(in srgb,var(--button-bg,#0f172a) 10%,#ffffff 90%); }
/* ── Page-level tabs ── */
.pl-page-tabs { display:flex; border-bottom:2px solid color-mix(in srgb,var(--button-bg,#0f172a) 10%,#ffffff 90%); margin-bottom:24px; }
.pl-page-tab { border:none; background:none; cursor:pointer; padding:10px 24px; font-size:0.88rem; font-weight:700; color:color-mix(in srgb,var(--button-bg,#0f172a) 42%,#ffffff 58%); border-bottom:2.5px solid transparent; margin-bottom:-2px; transition:color .14s,border-color .14s; font-family:inherit; }
.pl-page-tab:hover { color:var(--sidebar-bottom,#0f172a); }
.pl-page-tab.active { color:var(--sidebar-bottom,#0f172a); border-bottom-color:var(--button-bg,#0f172a); }
/* ── Notebook page view ── */
#pl-view-notebook { display:none; max-width:860px; flex-direction:column; gap:18px; }
#pl-view-notebook.active { display:flex; }
.pl-nbp-tabs { display:flex; gap:2px; border-bottom:1px solid color-mix(in srgb,var(--button-bg,#0f172a) 10%,#ffffff 90%); margin-bottom:16px; }
.pl-nbp-tab { border:none; background:none; cursor:pointer; padding:9px 18px; font-size:0.84rem; font-weight:600; color:color-mix(in srgb,var(--button-bg,#0f172a) 42%,#ffffff 58%); border-bottom:2.5px solid transparent; margin-bottom:-1px; border-radius:6px 6px 0 0; transition:color .14s,border-color .14s; font-family:inherit; }
.pl-nbp-tab:hover { color:var(--sidebar-bottom,#0f172a); }
.pl-nbp-tab.active { color:var(--sidebar-bottom,#0f172a); border-bottom-color:var(--button-bg,#0f172a); }
.pl-nbp-panel { display:none; }
.pl-nbp-panel.active { display:block; }
</style>

<div class="pl-page-tabs">
    <button class="pl-page-tab active" data-ptab="puestos">Puestos laborales</button>
    <button class="pl-page-tab" data-ptab="notebook">Notebook de puestos</button>
</div>
<div id="pl-view-puestos">
<div class="pl-wrap">
    <!-- Form -->
    <div class="pl-card">
        <p class="pl-card-title" id="pl-form-title">Nuevo puesto laboral</p>
        <input type="hidden" id="pl-edit-id" value="">
        <div class="pl-grid">
            <div class="pl-field">
                <label class="pl-label" for="pl-nombre">Nombre del puesto <span style="color:#ef4444">*</span></label>
                <input class="pl-input" id="pl-nombre" type="text" placeholder="Ej. Gerente de Marketing" autocomplete="off">
            </div>
            <div class="pl-field">
                <label class="pl-label" for="pl-area">Área a la que pertenece</label>
                <select class="pl-select" id="pl-area">
                    <option value="">— Sin área asignada —</option>
                </select>
            </div>
            <div class="pl-field">
                <label class="pl-label" for="pl-nivel">Nivel organizacional</label>
                <select class="pl-select" id="pl-nivel">
                    <option value="">— Seleccionar —</option>
                    <option value="Directivo">Directivo</option>
                    <option value="Gerencial">Gerencial</option>
                    <option value="Jefatura">Jefatura</option>
                    <option value="Coordinación">Coordinación</option>
                    <option value="Supervisor">Supervisor</option>
                    <option value="Técnico / Especialista">Técnico / Especialista</option>
                    <option value="Operativo">Operativo</option>
                    <option value="Auxiliar / Asistente">Auxiliar / Asistente</option>
                    <option value="Pasante / Prácticas">Pasante / Prácticas</option>
                </select>
            </div>
            <div class="pl-field full">
                <label class="pl-label" for="pl-desc">Descripción</label>
                <textarea class="pl-textarea" id="pl-desc" placeholder="Describe las responsabilidades principales del puesto..."></textarea>
            </div>
        </div>
        <div class="pl-form-actions">
            <button class="pl-btn-save" id="pl-btn-save">Guardar puesto</button>
            <button class="pl-btn-cancel" id="pl-btn-cancel">Cancelar</button>
            <span class="pl-msg" id="pl-msg">&#10003; Guardado</span>
        </div>
    </div>

    <!-- List -->
    <div class="pl-card">
        <p class="pl-card-title">Puestos registrados <span id="pl-count" style="font-weight:400;font-size:.82rem;color:color-mix(in srgb,var(--button-bg,#0f172a) 40%,#ffffff 60%);"></span></p>
        <div class="pl-table-wrap">
            <table class="pl-table">
                <thead>
                    <tr>
                        <th>Nombre del puesto</th>
                        <th>Área</th>
                        <th>Nivel</th>
                        <th>Descripción</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody id="pl-tbody"></tbody>
            </table>
        </div>
    </div>
</div>
</div>

<div id="pl-view-notebook">
  <div class="pl-card">
    <p class="pl-card-title">Notebook de puestos</p>
    <div class="pl-field" style="max-width:420px;margin-bottom:16px;">
      <label class="pl-label">Seleccionar puesto</label>
      <select class="pl-select" id="pl-nbp-sel"><option value="">\u2014 Seleccionar \u2014</option></select>
    </div>
    <div id="pl-nbp-content" style="display:none;">
      <h3 id="pl-nbp-titulo" style="font-size:.95rem;font-weight:700;color:var(--sidebar-bottom,#0f172a);margin:0 0 16px;"></h3>
      <div class="pl-nbp-tabs">
        <button class="pl-nbp-tab active" data-nbptab="hab">Habilidades requeridas</button>
        <button class="pl-nbp-tab" data-nbptab="col">Colaboradores asignados</button>
      </div>
      <div class="pl-nbp-panel active" id="pl-nbp-panel-hab"></div>
      <div class="pl-nbp-panel" id="pl-nbp-panel-col"></div>
      <div style="display:flex;gap:10px;align-items:center;margin-top:18px;padding-top:14px;border-top:1px solid color-mix(in srgb,var(--button-bg,#0f172a) 10%,#ffffff 90%);">
        <button class="pl-btn-save" id="pl-nbp-btn-save">Guardar</button>
        <span style="font-size:.82rem;color:#22c55e;display:none;" id="pl-nbp-saved">&#10003; Guardado</span>
      </div>
    </div>
  </div>
</div>

<!-- Notebook overlay + drawer -->
<div class="pl-nb-overlay" id="pl-nb-overlay"></div>
<div class="pl-nb-drawer" id="pl-nb-drawer">
    <div class="pl-nb-head">
        <div style="flex:1;min-width:0;">
            <div class="pl-nb-titulo" id="pl-nb-titulo">—</div>
            <div class="pl-nb-head-sub">Notebook del puesto</div>
        </div>
        <button class="pl-nb-close" id="pl-nb-close-btn" title="Cerrar">&times;</button>
    </div>
    <div class="pl-nb-tabs">
        <button class="pl-nb-tab active" data-tab="hab">Habilidades requeridas para el puesto</button>
        <button class="pl-nb-tab" data-tab="col">Colaborador@s asignad@s</button>
    </div>
    <div class="pl-nb-body">
        <div class="pl-nb-panel active" id="pl-nb-panel-hab"><p class="pl-nb-loading">Cargando...</p></div>
        <div class="pl-nb-panel" id="pl-nb-panel-col"><p class="pl-nb-loading">Cargando...</p></div>
    </div>
    <div class="pl-nb-save-bar">
        <button class="pl-nb-btn-save" id="pl-nb-btn-save">Guardar</button>
        <span class="pl-nb-saved" id="pl-nb-saved">&#10003; Guardado</span>
    </div>
</div>

<script>
(function() {
    var puestos = [];
    var areas = [];

    // Load areas
    fetch('/api/inicio/departamentos')
        .then(function(r){ return r.json(); })
        .then(function(res){
            areas = (res.data || []).map(function(a){ return a.name || a.nombre || ''; }).filter(Boolean);
            var sel = document.getElementById('pl-area');
            areas.forEach(function(a){
                var o = document.createElement('option');
                o.value = a; o.textContent = a;
                sel.appendChild(o);
            });
        });

    // Load puestos
    function loadPuestos() {
        fetch('/api/puestos-laborales')
            .then(function(r){ return r.json(); })
            .then(function(res){ puestos = res.data || []; renderTable(); });
    }

    function renderTable() {
        var tbody = document.getElementById('pl-tbody');
        var cnt = document.getElementById('pl-count');
        if (cnt) cnt.textContent = puestos.length ? '(' + puestos.length + ')' : '';
        if (!puestos.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="pl-empty">No hay puestos registrados aún.</td></tr>';
            return;
        }
        tbody.innerHTML = '';
        puestos.forEach(function(p) {
            var tr = document.createElement('tr');
            var habCount = (p.habilidades_requeridas || []).length;
            var colCount = (p.colaboradores_asignados || []).length;
            var nbBadge = (habCount || colCount)
                ? ' <span style="font-size:.7rem;background:color-mix(in srgb,var(--button-bg,#0f172a) 12%,#ffffff 88%);padding:1px 6px;border-radius:8px;font-weight:600;vertical-align:middle;">' + (habCount + colCount) + '</span>'
                : '';
            tr.innerHTML =
                '<td><strong>' + _esc(p.nombre) + '</strong></td>' +
                '<td class="area-cell">' + _esc(p.area || '—') + '</td>' +
                '<td class="area-cell">' + _esc(p.nivel || '—') + '</td>' +
                '<td class="desc-cell">' + _esc(p.descripcion || '—') + '</td>' +
                '<td style="white-space:nowrap">' +
                  '<button class="pl-act-btn nb" data-id="' + _esc(p.id) + '" title="Notebook">&#128203;' + nbBadge + '</button>' +
                  '<button class="pl-act-btn edit" data-id="' + _esc(p.id) + '" title="Editar">&#9998;</button>' +
                  '<button class="pl-act-btn del" data-id="' + _esc(p.id) + '" title="Eliminar">&times;</button>' +
                '</td>';
            tr.querySelector('.nb').addEventListener('click', function(){ openNotebook(p.id); });
            tr.querySelector('.edit').addEventListener('click', function(){ startEdit(p.id); });
            tr.querySelector('.del').addEventListener('click', function(){ deletePuesto(p.id); });
            tbody.appendChild(tr);
        });
    }

    function startEdit(id) {
        var p = puestos.find(function(x){ return x.id === id; });
        if (!p) return;
        document.getElementById('pl-edit-id').value = p.id;
        document.getElementById('pl-nombre').value = p.nombre;
        document.getElementById('pl-area').value = p.area || '';
        document.getElementById('pl-nivel').value = p.nivel || '';
        document.getElementById('pl-desc').value = p.descripcion || '';
        document.getElementById('pl-form-title').textContent = 'Editar puesto laboral';
        document.getElementById('pl-btn-cancel').style.display = 'inline-block';
        document.getElementById('pl-nombre').focus();
    }

    function resetForm() {
        document.getElementById('pl-edit-id').value = '';
        document.getElementById('pl-nombre').value = '';
        document.getElementById('pl-area').value = '';
        document.getElementById('pl-nivel').value = '';
        document.getElementById('pl-desc').value = '';
        document.getElementById('pl-form-title').textContent = 'Nuevo puesto laboral';
        document.getElementById('pl-btn-cancel').style.display = 'none';
        document.getElementById('pl-msg').style.display = 'none';
    }

    document.getElementById('pl-btn-cancel').addEventListener('click', resetForm);

    document.getElementById('pl-btn-save').addEventListener('click', function() {
        var nombre = document.getElementById('pl-nombre').value.trim();
        if (!nombre) { document.getElementById('pl-nombre').focus(); return; }
        var payload = {
            id:          document.getElementById('pl-edit-id').value || undefined,
            nombre:      nombre,
            area:        document.getElementById('pl-area').value,
            nivel:       document.getElementById('pl-nivel').value,
            descripcion: document.getElementById('pl-desc').value.trim(),
        };
        fetch('/api/puestos-laborales', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(function(r){ return r.json(); })
        .then(function(res){
            if (res.success) {
                puestos = res.data;
                renderTable();
                resetForm();
                var msg = document.getElementById('pl-msg');
                msg.style.display = 'inline';
                setTimeout(function(){ msg.style.display = 'none'; }, 2000);
            }
        });
    });

    function deletePuesto(id) {
        if (!confirm('¿Eliminar este puesto?')) return;
        fetch('/api/puestos-laborales', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'delete', id: id })
        })
        .then(function(r){ return r.json(); })
        .then(function(res){ if (res.success) { puestos = res.data; renderTable(); } });
    }

    function _esc(s) {
        return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }

    // ── Notebook drawer ────────────────────────────────────────────────────────
    var nbPuestoId = null;
    var nbActiveTab = 'hab';
    var nbHabCatalog = null;   // cached catalog
    var nbColabs = null;       // cached collaborators

    var _HAB_CAT_LABELS = {
        'comunicacion_interpersonales': 'Comunicación e interpersonales',
        'liderazgo_gestion': 'Liderazgo y gestión',
        'liderazgo_equipos': 'Liderazgo de equipos',
        'resolucion_pensamiento': 'Resolución y pensamiento',
        'organizacion_autogestion': 'Organización y autogestión',
        'informatica_tecnologia_general': 'Informática y tecnología general',
        'tecnologias_informacion_it': 'Tecnologías de la información (IT)',
        'diseno_multimedia': 'Diseño y multimedia',
        'marketing_ventas_comunicacion': 'Marketing, ventas y comunicación',
        'finanzas_contabilidad_administracion': 'Finanzas, contabilidad y administración',
        'logistica_produccion_operaciones': 'Logística, producción y operaciones',
        'idiomas_duros': 'Idiomas',
        'sector_salud': 'Sector salud',
        'sector_legal': 'Sector legal',
        'habilidades_manuales_tecnicas': 'Habilidades manuales y técnicas'
    };

    function openNotebook(id) {
        nbPuestoId = id;
        var p = puestos.find(function(x){ return x.id === id; });
        if (!p) return;
        document.getElementById('pl-nb-titulo').textContent = p.nombre;
        // reset tabs
        document.querySelectorAll('.pl-nb-tab').forEach(function(t){ t.classList.remove('active'); });
        document.querySelectorAll('.pl-nb-panel').forEach(function(t){ t.classList.remove('active'); });
        nbActiveTab = 'hab';
        document.querySelector('.pl-nb-tab[data-tab="hab"]').classList.add('active');
        document.getElementById('pl-nb-panel-hab').classList.add('active');
        // show
        document.getElementById('pl-nb-overlay').style.display = 'block';
        document.getElementById('pl-nb-drawer').classList.add('open');
        document.getElementById('pl-nb-saved').style.display = 'none';
        // load
        _nbLoadHab(p);
        _nbLoadCol(p);
    }

    function closeNotebook() {
        document.getElementById('pl-nb-drawer').classList.remove('open');
        document.getElementById('pl-nb-overlay').style.display = 'none';
        nbPuestoId = null;
    }

    document.getElementById('pl-nb-close-btn').addEventListener('click', closeNotebook);
    document.getElementById('pl-nb-overlay').addEventListener('click', closeNotebook);

    document.querySelectorAll('.pl-nb-tab').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var tab = btn.getAttribute('data-tab');
            nbActiveTab = tab;
            document.querySelectorAll('.pl-nb-tab').forEach(function(t){ t.classList.remove('active'); });
            document.querySelectorAll('.pl-nb-panel').forEach(function(t){ t.classList.remove('active'); });
            btn.classList.add('active');
            document.getElementById('pl-nb-panel-' + tab).classList.add('active');
        });
    });

    // ── Habilidades tab ─────────────────────────────────────────────────────────
    function _normHabItem(raw) {
        if (raw && typeof raw === 'object') return { nombre: String(raw.nombre || '').trim(), minimo: parseInt(raw.minimo, 10) || 0 };
        return { nombre: String(raw || '').trim(), minimo: 0 };
    }

    function _nbLoadHab(p) {
        var panel = document.getElementById('pl-nb-panel-hab');
        panel.innerHTML = '<p class="pl-nb-loading">Cargando habilidades...</p>';
        var items = (p.habilidades_requeridas || []).map(_normHabItem);

        function _listHtml() {
            if (!items.length) return '<p class="pl-nb-loading">Sin habilidades agregadas.</p>';
            return items.map(function(it, idx) {
                return '<div class="pl-nb-hab-row" data-idx="' + idx + '">' +
                    '<span class="pl-nb-hab-nombre">' + _esc(it.nombre) + '</span>' +
                    '<span class="pl-nb-hab-badge">' + it.minimo + '%</span>' +
                    '<button class="pl-nb-hab-del" data-idx="' + idx + '" title="Eliminar">&times;</button>' +
                '</div>';
            }).join('');
        }

        function _buildSelect(catalog) {
            var allSkills = [];
            Object.keys(catalog).forEach(function(cat) {
                var catLabel = _HAB_CAT_LABELS[cat] || cat.replace(/_/g,' ');
                (catalog[cat] || []).forEach(function(skill) {
                    var s = typeof skill === 'string' ? skill : (skill.nombre || skill.name || String(skill));
                    if (s) allSkills.push({ nombre: s, categoria: catLabel });
                });
            });
            allSkills.sort(function(a,b){ return a.nombre.localeCompare(b.nombre); });
            var selOpts = '<option value="">— Selecciona una habilidad —</option>';
            var lastCat = '';
            allSkills.forEach(function(sk) {
                if (sk.categoria !== lastCat) {
                    if (lastCat) selOpts += '</optgroup>';
                    selOpts += '<optgroup label="' + _esc(sk.categoria) + '">';
                    lastCat = sk.categoria;
                }
                selOpts += '<option value="' + _esc(sk.nombre) + '">' + _esc(sk.nombre) + '</option>';
            });
            if (lastCat) selOpts += '</optgroup>';
            return selOpts;
        }

        function _renderUI(selOpts) {
            panel.innerHTML =
                '<div id="pl-nb-hab-list" style="display:flex;flex-direction:column;gap:6px;margin-bottom:14px;">' + _listHtml() + '</div>' +
                '<div style="border-top:1px solid #e2e8f0;padding-top:12px;display:flex;flex-direction:column;gap:8px;">' +
                  '<label style="font-size:.78rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.04em;">Agregar habilidad</label>' +
                  '<select id="pl-nb-hab-sel" style="width:100%;padding:7px 10px;border:1px solid #cbd5e1;border-radius:8px;font-size:.9rem;">' + selOpts + '</select>' +
                  '<div style="display:flex;gap:8px;align-items:center;">' +
                    '<label style="font-size:.85rem;color:#475569;white-space:nowrap;">Mínimo requerido</label>' +
                    '<input id="pl-nb-hab-pct" type="number" min="0" max="100" value="80" style="width:72px;padding:6px 8px;border:1px solid #cbd5e1;border-radius:8px;font-size:.9rem;text-align:center;">' +
                    '<span style="font-size:.9rem;color:#64748b;">%</span>' +
                    '<button id="pl-nb-hab-add" style="margin-left:auto;padding:7px 16px;background:var(--button-bg,#0f172a);color:#fff;border:0;border-radius:8px;font-weight:700;cursor:pointer;font-size:.85rem;">Agregar</button>' +
                  '</div>' +
                '</div>';

            function _rebindDeletes() {
                panel.querySelectorAll('.pl-nb-hab-del').forEach(function(btn) {
                    btn.addEventListener('click', function() {
                        var idx = parseInt(this.getAttribute('data-idx'), 10);
                        items.splice(idx, 1);
                        document.getElementById('pl-nb-hab-list').innerHTML = _listHtml();
                        _rebindDeletes();
                    });
                });
            }
            _rebindDeletes();

            document.getElementById('pl-nb-hab-add').addEventListener('click', function() {
                var sel = document.getElementById('pl-nb-hab-sel');
                var pct = document.getElementById('pl-nb-hab-pct');
                var nombre = sel.value.trim();
                var minimo = Math.min(100, Math.max(0, parseInt(pct.value, 10) || 0));
                if (!nombre) { sel.focus(); return; }
                if (items.find(function(x){ return x.nombre === nombre; })) { sel.value = ''; sel.focus(); return; }
                items.push({ nombre: nombre, minimo: minimo });
                sel.value = '';
                pct.value = 80;
                document.getElementById('pl-nb-hab-list').innerHTML = _listHtml();
                _rebindDeletes();
            });
        }

        if (nbHabCatalog) { _renderUI(_buildSelect(nbHabCatalog)); return; }
        fetch('/api/habilidades-catalog')
            .then(function(r){ return r.json(); })
            .then(function(res){
                nbHabCatalog = res.catalog || res.data || res || {};
                _renderUI(_buildSelect(nbHabCatalog));
            })
            .catch(function(){ panel.innerHTML = '<p class="pl-nb-loading">Error al cargar catálogo.</p>'; });
    }

    // ── Colaboradores tab ────────────────────────────────────────────────────────
    function _nbLoadCol(p) {
        var panel = document.getElementById('pl-nb-panel-col');
        panel.innerHTML = '<p class="pl-nb-loading">Cargando colaboradores...</p>';
        var assigned = (p.colaboradores_asignados || []).map(String);
        function _render(colabs) {
            var searchId = 'pl-nb-col-search-' + Date.now();
            var listId = 'pl-nb-col-list-' + Date.now();
            var html = '<input class="pl-nb-search" id="' + searchId + '" placeholder="Buscar colaborador..." autocomplete="off">';
            html += '<div id="' + listId + '">';
            colabs.forEach(function(c) {
                var isChk = assigned.indexOf(String(c.id)) >= 0;
                var initials = (c.nombre || '?').split(' ').slice(0,2).map(function(w){ return w[0]; }).join('').toUpperCase();
                var dept = c.departamento || c.puesto || '';
                html += '<label class="pl-nb-col-item" data-nombre="' + _esc((c.nombre||'').toLowerCase()) + '">' +
                    '<input type="checkbox" value="' + _esc(String(c.id)) + '" ' + (isChk ? 'checked' : '') + '>' +
                    (c.imagen ? '<img class="pl-nb-avatar" src="' + _esc(c.imagen) + '" onerror="this.style.display=\'none\'">' : '<div class="pl-nb-avatar">' + _esc(initials) + '</div>') +
                    '<div>' +
                      '<div class="pl-nb-col-name">' + _esc(c.nombre || '—') + '</div>' +
                      (dept ? '<div class="pl-nb-col-sub">' + _esc(dept) + '</div>' : '') +
                    '</div></label>';
            });
            html += '</div>';
            panel.innerHTML = html;
            var inp = document.getElementById(searchId);
            var lst = document.getElementById(listId);
            inp.addEventListener('input', function() {
                var q = inp.value.toLowerCase();
                lst.querySelectorAll('.pl-nb-col-item').forEach(function(el) {
                    el.style.display = (!q || el.getAttribute('data-nombre').indexOf(q) >= 0) ? '' : 'none';
                });
            });
        }
        if (nbColabs) { _render(nbColabs); return; }
        fetch('/api/colaboradores')
            .then(function(r){ return r.json(); })
            .then(function(res){
                nbColabs = (res.data || res || []).filter(function(c){ return c.colaborador !== false; });
                _render(nbColabs);
            })
            .catch(function(){ panel.innerHTML = '<p class="pl-nb-loading">Error al cargar colaboradores.</p>'; });
    }

    // ── Save notebook ────────────────────────────────────────────────────────────
    document.getElementById('pl-nb-btn-save').addEventListener('click', function() {
        if (!nbPuestoId) return;
        // collect habilidades
        var habs = [];
        document.querySelectorAll('#pl-nb-panel-hab .pl-nb-hab-row').forEach(function(row) {
            var nombre = row.querySelector('.pl-nb-hab-nombre');
            var badge  = row.querySelector('.pl-nb-hab-badge');
            if (nombre) habs.push({ nombre: nombre.textContent.trim(), minimo: parseInt((badge ? badge.textContent : '0'), 10) || 0 });
        });
        // collect colaboradores
        var colPanel = document.getElementById('pl-nb-panel-col');
        var cols = [];
        colPanel.querySelectorAll('input[type=checkbox]:checked').forEach(function(cb) {
            cols.push(cb.value);
        });
        fetch('/api/puestos-laborales', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'update_notebook', id: nbPuestoId, habilidades_requeridas: habs, colaboradores_asignados: cols })
        })
        .then(function(r){ return r.json(); })
        .then(function(res){
            if (res.success) {
                puestos = res.data;
                renderTable();
                var msg = document.getElementById('pl-nb-saved');
                msg.style.display = 'inline';
                setTimeout(function(){ msg.style.display = 'none'; }, 2200);
            }
        });
    });

    // ── Page-level tabs ─────────────────────────────────────────────────────────
    document.querySelectorAll('.pl-page-tab').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var target = btn.getAttribute('data-ptab');
            document.querySelectorAll('.pl-page-tab').forEach(function(t){ t.classList.remove('active'); });
            btn.classList.add('active');
            var vP = document.getElementById('pl-view-puestos');
            var vN = document.getElementById('pl-view-notebook');
            if (target === 'puestos') {
                vP.style.display = '';
                vN.classList.remove('active');
            } else {
                vP.style.display = 'none';
                vN.classList.add('active');
                var sel = document.getElementById('pl-nbp-sel');
                var cur = sel.value;
                sel.innerHTML = '<option value="">\u2014 Seleccionar \u2014</option>';
                puestos.forEach(function(p) {
                    var o = document.createElement('option');
                    o.value = p.id; o.textContent = p.nombre;
                    if (p.id === cur) o.selected = true;
                    sel.appendChild(o);
                });
            }
        });
    });

    // ── Notebook page: selector ─────────────────────────────────────────────────
    var nbpPuestoId = null;
    document.getElementById('pl-nbp-sel').addEventListener('change', function() {
        var id = this.value;
        var cont = document.getElementById('pl-nbp-content');
        if (!id) { cont.style.display = 'none'; nbpPuestoId = null; return; }
        nbpPuestoId = id;
        var p = puestos.find(function(x){ return x.id === id; });
        if (!p) return;
        document.getElementById('pl-nbp-titulo').textContent = p.nombre;
        cont.style.display = '';
        document.querySelectorAll('.pl-nbp-tab').forEach(function(t){ t.classList.remove('active'); });
        document.querySelectorAll('.pl-nbp-panel').forEach(function(t){ t.classList.remove('active'); });
        document.querySelector('.pl-nbp-tab[data-nbptab="hab"]').classList.add('active');
        document.getElementById('pl-nbp-panel-hab').classList.add('active');
        _nbpLoadHab(p);
        _nbpLoadCol(p);
    });

    document.querySelectorAll('.pl-nbp-tab').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var tab = btn.getAttribute('data-nbptab');
            document.querySelectorAll('.pl-nbp-tab').forEach(function(t){ t.classList.remove('active'); });
            document.querySelectorAll('.pl-nbp-panel').forEach(function(t){ t.classList.remove('active'); });
            btn.classList.add('active');
            document.getElementById('pl-nbp-panel-' + tab).classList.add('active');
        });
    });

    // ── Habilidades (notebook page) ─────────────────────────────────────────────
    function _nbpLoadHab(p) {
        var panel = document.getElementById('pl-nbp-panel-hab');
        panel.innerHTML = '<p class="pl-nb-loading">Cargando...</p>';
        var items = (p.habilidades_requeridas || []).map(_normHabItem);
        function _listHtml() {
            if (!items.length) return '<p class="pl-nb-loading">Sin habilidades agregadas.</p>';
            return items.map(function(it, idx) {
                return '<div class="pl-nb-hab-row" data-idx="' + idx + '">' +
                    '<span class="pl-nb-hab-nombre">' + _esc(it.nombre) + '</span>' +
                    '<span class="pl-nb-hab-badge">' + it.minimo + '%</span>' +
                    '<button class="pl-nb-hab-del" data-idx="' + idx + '">&times;</button></div>';
            }).join('');
        }
        function _buildOpts(catalog) {
            var all = [];
            Object.keys(catalog).forEach(function(cat) {
                var lbl = _HAB_CAT_LABELS[cat] || cat.replace(/_/g,' ');
                (catalog[cat] || []).forEach(function(sk) {
                    var s = typeof sk === 'string' ? sk : (sk.nombre || sk.name || String(sk));
                    if (s) all.push({ nombre: s, categoria: lbl });
                });
            });
            all.sort(function(a,b){ return a.nombre.localeCompare(b.nombre); });
            var opts = '<option value="">\u2014 Selecciona una habilidad \u2014</option>'; var lc = '';
            all.forEach(function(sk) {
                if (sk.categoria !== lc) { if (lc) opts += '</optgroup>'; opts += '<optgroup label="' + _esc(sk.categoria) + '">'; lc = sk.categoria; }
                opts += '<option value="' + _esc(sk.nombre) + '">' + _esc(sk.nombre) + '</option>';
            });
            if (lc) opts += '</optgroup>'; return opts;
        }
        function _renderUI(selOpts) {
            panel.innerHTML =
                '<div id="pl-nbp-hab-list" style="display:flex;flex-direction:column;gap:6px;margin-bottom:14px;">' + _listHtml() + '</div>' +
                '<div style="border-top:1px solid #e2e8f0;padding-top:12px;display:flex;flex-direction:column;gap:8px;">' +
                  '<label style="font-size:.78rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.04em;">Agregar habilidad</label>' +
                  '<select id="pl-nbp-hab-sel" style="width:100%;padding:7px 10px;border:1px solid #cbd5e1;border-radius:8px;font-size:.9rem;">' + selOpts + '</select>' +
                  '<div style="display:flex;gap:8px;align-items:center;">' +
                    '<label style="font-size:.85rem;color:#475569;white-space:nowrap;">M\u00ednimo requerido</label>' +
                    '<input id="pl-nbp-hab-pct" type="number" min="0" max="100" value="80" style="width:72px;padding:6px 8px;border:1px solid #cbd5e1;border-radius:8px;font-size:.9rem;text-align:center;">' +
                    '<span style="font-size:.9rem;color:#64748b;">%</span>' +
                    '<button id="pl-nbp-hab-add" style="margin-left:auto;padding:7px 16px;background:var(--button-bg,#0f172a);color:#fff;border:0;border-radius:8px;font-weight:700;cursor:pointer;font-size:.85rem;">Agregar</button>' +
                  '</div></div>';
            function _rebind() {
                panel.querySelectorAll('.pl-nb-hab-del').forEach(function(b) {
                    b.addEventListener('click', function() {
                        items.splice(parseInt(this.getAttribute('data-idx'), 10), 1);
                        document.getElementById('pl-nbp-hab-list').innerHTML = _listHtml();
                        _rebind();
                    });
                });
            }
            _rebind();
            document.getElementById('pl-nbp-hab-add').addEventListener('click', function() {
                var sel = document.getElementById('pl-nbp-hab-sel');
                var pct = document.getElementById('pl-nbp-hab-pct');
                var nombre = sel.value.trim();
                var minimo = Math.min(100, Math.max(0, parseInt(pct.value, 10) || 0));
                if (!nombre || items.find(function(x){ return x.nombre === nombre; })) { sel.focus(); return; }
                items.push({ nombre: nombre, minimo: minimo }); sel.value = ''; pct.value = 80;
                document.getElementById('pl-nbp-hab-list').innerHTML = _listHtml(); _rebind();
            });
        }
        if (nbHabCatalog) { _renderUI(_buildOpts(nbHabCatalog)); return; }
        fetch('/api/habilidades-catalog')
            .then(function(r){ return r.json(); })
            .then(function(res){ nbHabCatalog = res.catalog || res.data || res || {}; _renderUI(_buildOpts(nbHabCatalog)); })
            .catch(function(){ panel.innerHTML = '<p class="pl-nb-loading">Error al cargar cat\u00e1logo.</p>'; });
    }

    // ── Colaboradores (notebook page) ───────────────────────────────────────────
    function _nbpLoadCol(p) {
        var panel = document.getElementById('pl-nbp-panel-col');
        panel.innerHTML = '<p class="pl-nb-loading">Cargando...</p>';
        var assigned = (p.colaboradores_asignados || []).map(String);
        function _render(colabs) {
            var html = '<input class="pl-nb-search" id="pl-nbp-col-search" placeholder="Buscar colaborador..." autocomplete="off">';
            html += '<div id="pl-nbp-col-list">';
            colabs.forEach(function(c) {
                var isChk = assigned.indexOf(String(c.id)) >= 0;
                var initials = (c.nombre || '?').split(' ').slice(0,2).map(function(w){ return w[0]; }).join('').toUpperCase();
                var dept = c.departamento || c.puesto || '';
                html += '<label class="pl-nb-col-item" data-nombre="' + _esc((c.nombre||'').toLowerCase()) + '">' +
                    '<input type="checkbox" value="' + _esc(String(c.id)) + '" ' + (isChk ? 'checked' : '') + '>' +
                    (c.imagen ? '<img class="pl-nb-avatar" src="' + _esc(c.imagen) + '" onerror="this.style.display=\'none\'">' : '<div class="pl-nb-avatar">' + _esc(initials) + '</div>') +
                    '<div><div class="pl-nb-col-name">' + _esc(c.nombre || '\u2014') + '</div>' +
                    (dept ? '<div class="pl-nb-col-sub">' + _esc(dept) + '</div>' : '') + '</div></label>';
            });
            html += '</div>'; panel.innerHTML = html;
            var inp = document.getElementById('pl-nbp-col-search');
            var lst = document.getElementById('pl-nbp-col-list');
            inp.addEventListener('input', function() {
                var q = inp.value.toLowerCase();
                lst.querySelectorAll('.pl-nb-col-item').forEach(function(el) {
                    el.style.display = (!q || el.getAttribute('data-nombre').indexOf(q) >= 0) ? '' : 'none';
                });
            });
        }
        if (nbColabs) { _render(nbColabs); return; }
        fetch('/api/colaboradores')
            .then(function(r){ return r.json(); })
            .then(function(res){ nbColabs = (res.data || res || []).filter(function(c){ return c.colaborador !== false; }); _render(nbColabs); })
            .catch(function(){ panel.innerHTML = '<p class="pl-nb-loading">Error al cargar colaboradores.</p>'; });
    }

    // ── Guardar (notebook page) ─────────────────────────────────────────────────
    document.getElementById('pl-nbp-btn-save').addEventListener('click', function() {
        if (!nbpPuestoId) return;
        var habs = [];
        document.querySelectorAll('#pl-nbp-panel-hab .pl-nb-hab-row').forEach(function(row) {
            var n = row.querySelector('.pl-nb-hab-nombre');
            var b = row.querySelector('.pl-nb-hab-badge');
            if (n) habs.push({ nombre: n.textContent.trim(), minimo: parseInt((b ? b.textContent : '0'), 10) || 0 });
        });
        var cols = [];
        document.querySelectorAll('#pl-nbp-panel-col input[type=checkbox]:checked').forEach(function(cb) { cols.push(cb.value); });
        fetch('/api/puestos-laborales', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'update_notebook', id: nbpPuestoId, habilidades_requeridas: habs, colaboradores_asignados: cols })
        })
        .then(function(r){ return r.json(); })
        .then(function(res){
            if (res.success) {
                puestos = res.data; renderTable();
                var msg = document.getElementById('pl-nbp-saved');
                msg.style.display = 'inline';
                setTimeout(function(){ msg.style.display = 'none'; }, 2200);
            }
        });
    });

    loadPuestos();
})();
</script>
"""
    return render_backend_page(
        request,
        title="Puestos laborales",
        description="Gestión de puestos laborales",
        content=content,
        hide_floating_actions=True,
        floating_actions_screen="none",
    )


@router.get("/inicio/departamentos/notebook-puesto", response_class=HTMLResponse)
def notebook_puesto_page(request: Request):
    from fastapi_modulo.main import render_backend_page
    content = (
        '<div style="max-width:440px;margin:60px auto;background:#fff;border:1px solid #dbe3ef;'
        'border-radius:14px;padding:32px;text-align:center;">'
        '<p style="font-size:1.5rem;margin-bottom:12px;">&#128274;</p>'
        '<h2 style="font-size:1.1rem;color:#0f172a;margin:0 0 10px;">Sin acceso</h2>'
        '<p style="color:#64748b;margin:0;">No tiene acceso, com&#250;niquese con el administrador.</p>'
        '</div>'
    )
    return render_backend_page(
        request,
        title="Notebook de puesto",
        description="Notebook del puesto laboral",
        content=content,
        hide_floating_actions=True,
        floating_actions_screen="none",
    )


@router.get("/inicio/departamentos/puestos-organizacionales", response_class=HTMLResponse)
def puestos_organizacionales_page(request: Request):
    from fastapi_modulo.main import render_backend_page

    content = (
        '<div style="max-width:440px;margin:60px auto;background:#fff;border:1px solid #dbe3ef;'
        'border-radius:14px;padding:32px;text-align:center;">'
        '<p style="font-size:1.5rem;margin-bottom:12px;">&#128274;</p>'
        '<h2 style="font-size:1.1rem;color:#0f172a;margin:0 0 10px;">Sin acceso</h2>'
        '<p style="color:#64748b;margin:0;">No tiene acceso, comuníquese con el administrador.</p>'
        '</div>'
    )
    return render_backend_page(
        request,
        title="Puestos organizacionales",
        description="Gestión de puestos organizacionales",
        content=content,
        hide_floating_actions=True,
        floating_actions_screen="none",
    )


@router.get("/areas-organizacionales", response_class=HTMLResponse)
def areas_organizacionales_page(request: Request):
    return RedirectResponse(url="/inicio/departamentos", status_code=307)


def _build_empleados_count_map(rows: List[DepartamentoOrganizacional]) -> Dict[str, int]:
    # Import diferido para evitar ciclo de importación con fastapi_modulo.main.
    from fastapi_modulo.main import Usuario

    db = SessionLocal()
    try:
        all_users = db.query(Usuario).all()
    finally:
        db.close()

    buckets: Dict[str, int] = {}
    for user in all_users:
        dep = str(getattr(user, "departamento", "") or "").strip().lower()
        if not dep:
            continue
        buckets[dep] = buckets.get(dep, 0) + 1

    counts: Dict[str, int] = {}
    for row in rows:
        name_key = str(row.nombre or "").strip().lower()
        code_key = str(row.codigo or "").strip().lower()
        counts[code_key] = buckets.get(name_key, 0)
        if code_key and code_key != name_key:
            counts[code_key] += buckets.get(code_key, 0)
    return counts


def _serialize_departamentos(
    rows: List[DepartamentoOrganizacional],
    count_map: Dict[str, int] | None = None,
) -> List[Dict[str, Any]]:
    data: List[Dict[str, Any]] = []
    count_map = count_map or {}
    for row in rows:
        code_key = str(row.codigo or "").strip().lower()
        data.append(
            {
                "name": str(row.nombre or "").strip(),
                "parent": str(row.padre or "N/A").strip() or "N/A",
                "manager": str(row.responsable or "").strip(),
                "code": str(row.codigo or "").strip(),
                "color": str(row.color or "#1d4ed8").strip() or "#1d4ed8",
                "status": str(row.estado or "Activo").strip() or "Activo",
                "empleados_asignados": int(count_map.get(code_key, 0)),
            }
        )
    return data

@router.get("/api/inicio/departamentos")
def listar_departamentos():
    _ensure_departamentos_schema()
    db = SessionLocal()
    try:
        rows = (
            db.query(DepartamentoOrganizacional)
            .order_by(DepartamentoOrganizacional.orden.asc(), DepartamentoOrganizacional.id.asc())
            .all()
        )
        count_map = _build_empleados_count_map(rows)
        return {"success": True, "data": _serialize_departamentos(rows, count_map)}
    finally:
        db.close()

@router.post("/api/inicio/departamentos")
async def guardar_departamentos(request: Request, data: dict = Body(...)):
    _enforce_departamentos_write_permission(request)
    incoming = data.get("data", [])
    if not isinstance(incoming, list):
        raise HTTPException(status_code=400, detail="Formato inválido")

    cleaned_rows: List[Dict[str, str]] = []
    used_codes: Set[str] = set()
    for item in incoming:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        code = str(item.get("code") or "").strip()
        parent = str(item.get("parent") or "N/A").strip() or "N/A"
        manager = str(item.get("manager") or "").strip()
        color = str(item.get("color") or "#1d4ed8").strip() or "#1d4ed8"
        status = "Activo"
        if not name or not code:
            continue
        code_key = code.lower()
        if code_key in used_codes:
            continue
        used_codes.add(code_key)
        cleaned_rows.append(
            {
                "name": name,
                "code": code,
                "parent": parent,
                "manager": manager,
                "color": color,
                "status": status,
            }
        )

    if not cleaned_rows:
        raise HTTPException(status_code=400, detail="No hay departamentos válidos para guardar")

    _ensure_departamentos_schema()
    db = SessionLocal()
    try:
        # Upsert no destructivo para evitar pérdida masiva si el frontend envía payload parcial.
        for idx, item in enumerate(cleaned_rows, start=1):
            existing = (
                db.query(DepartamentoOrganizacional)
                .filter(DepartamentoOrganizacional.codigo == item["code"])
                .first()
            )
            if existing:
                existing.nombre = item["name"]
                existing.padre = item["parent"]
                existing.responsable = item["manager"]
                existing.color = item["color"]
                existing.estado = item["status"]
                existing.orden = idx
                db.add(existing)
            else:
                db.add(
                    DepartamentoOrganizacional(
                        nombre=item["name"],
                        codigo=item["code"],
                        padre=item["parent"],
                        responsable=item["manager"],
                        color=item["color"],
                        estado=item["status"],
                        orden=idx,
                    )
                )
        db.commit()
        rows = (
            db.query(DepartamentoOrganizacional)
            .order_by(DepartamentoOrganizacional.orden.asc(), DepartamentoOrganizacional.id.asc())
            .all()
        )
        count_map = _build_empleados_count_map(rows)
        return {"success": True, "data": _serialize_departamentos(rows, count_map)}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error guardando departamentos: {exc}")
    finally:
        db.close()


@router.delete("/api/inicio/departamentos/{code}")
def eliminar_departamento(request: Request, code: str):
    _enforce_departamentos_write_permission(request)
    _ensure_departamentos_schema()
    target_code = str(code or "").strip()
    if not target_code:
        raise HTTPException(status_code=400, detail="Código inválido")
    db = SessionLocal()
    try:
        row = (
            db.query(DepartamentoOrganizacional)
            .filter(DepartamentoOrganizacional.codigo == target_code)
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail="Departamento no encontrado")
        db.delete(row)
        db.commit()
        rows = (
            db.query(DepartamentoOrganizacional)
            .order_by(DepartamentoOrganizacional.orden.asc(), DepartamentoOrganizacional.id.asc())
            .all()
        )
        count_map = _build_empleados_count_map(rows)
        return {"success": True, "data": _serialize_departamentos(rows, count_map)}
    finally:
        db.close()
