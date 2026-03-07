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

_DEP_FUNCIONES_PATH = os.path.join(
    os.environ.get("RUNTIME_STORE_DIR") or
    os.path.join(
        os.environ.get("SIPET_DATA_DIR") or os.path.expanduser("~/.sipet/data"),
        "runtime_store",
        (os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "development").strip().lower(),
    ),
    "departamentos_funciones.json",
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


def _normalize_funciones_payload(raw: Any) -> Dict[str, List[str]]:
    groups = {
        "misionales": [],
        "apoyo": [],
        "proyectos_especiales": [],
    }
    if isinstance(raw, list):
        for item in raw:
            txt = str(item or "").strip()
            if txt and txt not in groups["misionales"]:
                groups["misionales"].append(txt)
        return groups
    if isinstance(raw, dict):
        for key in groups.keys():
            vals = raw.get(key, [])
            if not isinstance(vals, list):
                continue
            seen: List[str] = []
            for item in vals:
                txt = str(item or "").strip()
                if txt and txt not in seen:
                    seen.append(txt)
            groups[key] = seen
    return groups


def _load_departamentos_funciones_map() -> Dict[str, Dict[str, List[str]]]:
    try:
        if os.path.exists(_DEP_FUNCIONES_PATH):
            raw = json.loads(open(_DEP_FUNCIONES_PATH, encoding="utf-8").read())
            if isinstance(raw, dict):
                cleaned: Dict[str, Dict[str, List[str]]] = {}
                for k, v in raw.items():
                    key = str(k or "").strip().lower()
                    if not key:
                        continue
                    cleaned[key] = _normalize_funciones_payload(v)
                return cleaned
    except Exception:
        pass
    return {}


def _save_departamentos_funciones_map(data: Dict[str, Dict[str, List[str]]]) -> None:
    import pathlib, json as _json
    pathlib.Path(_DEP_FUNCIONES_PATH).parent.mkdir(parents=True, exist_ok=True)
    open(_DEP_FUNCIONES_PATH, "w", encoding="utf-8").write(_json.dumps(data, ensure_ascii=False, indent=2))


@router.get("/api/puestos-laborales")
def api_puestos_laborales_list():
    return {"success": True, "data": _load_puestos()}


def _get_departamentos_catalog() -> List[str]:
    _ensure_departamentos_schema()
    db = SessionLocal()
    try:
        rows = (
            db.query(DepartamentoOrganizacional)
            .order_by(DepartamentoOrganizacional.orden.asc(), DepartamentoOrganizacional.id.asc())
            .all()
        )
        catalog = []
        seen = set()
        for row in rows:
            name = str(getattr(row, "nombre", "") or "").strip()
            key = name.lower()
            if not name or key in seen:
                continue
            seen.add(key)
            catalog.append(name)
        # Fallback/compatibilidad: incluir áreas ya usadas en puestos guardados.
        for puesto in _load_puestos():
            area = str((puesto or {}).get("area") or "").strip()
            key = area.lower()
            if not area or key in seen:
                continue
            seen.add(key)
            catalog.append(area)
        return catalog
    finally:
        db.close()


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
                puestos[idx]["kpis"] = body.get("kpis", puestos[idx].get("kpis", []))
                puestos[idx]["colaboradores_asignados"] = body.get("colaboradores_asignados", puestos[idx].get("colaboradores_asignados", []))
                _save_puestos(puestos)
                return {"success": True, "data": puestos}
            return {"success": False, "error": "Puesto no encontrado"}

        # upsert
        existing = next((p for p in puestos if p.get("id") == str(body.get("id", ""))), {})
        habilidades_requeridas = body.get("habilidades_requeridas", existing.get("habilidades_requeridas", []))
        if not isinstance(habilidades_requeridas, list):
            habilidades_requeridas = existing.get("habilidades_requeridas", [])
        area_value = str(body.get("area") or "").strip()
        catalog = _get_departamentos_catalog()
        catalog_map = {str(name).strip().lower(): str(name).strip() for name in catalog}
        if not area_value:
            return {"success": False, "error": "El área es obligatoria."}
        normalized_area = catalog_map.get(area_value.lower())
        if not normalized_area:
            return {"success": False, "error": "Área inválida. Seleccione un área del listado."}
        area_value = normalized_area

        puesto = {
            "id":          str(body.get("id") or _uuid.uuid4()),
            "nombre":      str(body.get("nombre") or "").strip(),
            "area":        area_value,
            "nivel":       str(body.get("nivel") or "").strip(),
            "descripcion": str(body.get("descripcion") or "").strip(),
            "habilidades_requeridas":  habilidades_requeridas,
            "kpis":        body.get("kpis", existing.get("kpis", [])) if isinstance(body.get("kpis", existing.get("kpis", [])), list) else existing.get("kpis", []),
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
    initial_areas = _get_departamentos_catalog()

    content = """

<div class="titulo bg-base-200 rounded-box border border-base-300 p-4 sm:p-6" style="margin-bottom:12px;">
    <div class="w-full flex flex-col md:flex-row items-center gap-10">
        <img
            src="/templates/icon/inicio.svg"
            alt="Icono organización"
            width="96"
            height="96"
            class="shrink-0 rounded-box border border-base-300 bg-base-100 p-3 object-contain"
        />
        <div class="w-full grid gap-2 content-center">
            <div class="block w-full text-3xl sm:text-4xl lg:text-5xl font-bold leading-tight text-[color:var(--sidebar-bottom)]">Puestos Laborales</div>
            <div class="block w-full text-base sm:text-lg text-base-content/70">Primero debe agregar los puestos laborales para postriormente asignarlos al colaborador</div>
        </div>
    </div>
</div>
<div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3" style="margin:10px 0 14px;">
    <button class="view-pill boton_vista" id="pl-btn-new-short" type="button" data-tooltip="Nuevo" aria-label="Nuevo">
      <span class="boton_vista-icono view-pill-icon-mask" aria-hidden="true" style="--view-pill-icon-url:url('/icon/boton/nuevo.svg')"></span>
      <span class="view-pill-label boton_vista-label">Nuevo</span>
    </button>
    <div class="view-buttons page-view-buttons" id="pl-view-switch">
        <button class="view-pill boton_vista active" type="button" data-pl-view="form" data-tooltip="Formulario" aria-label="Formulario">
          <span class="boton_vista-icono view-pill-icon-mask" aria-hidden="true" style="--view-pill-icon-url:url('/icon/boton/formulario.svg')"></span>
          <span class="view-pill-label boton_vista-label">Form</span>
        </button>
        <button class="view-pill boton_vista" type="button" data-pl-view="list" data-tooltip="Lista" aria-label="Lista">
          <span class="boton_vista-icono view-pill-icon-mask" aria-hidden="true" style="--view-pill-icon-url:url('/icon/boton/grid.svg')"></span>
          <span class="view-pill-label boton_vista-label">List</span>
        </button>
        <button class="view-pill boton_vista" type="button" data-pl-view="kanban" data-tooltip="Kanban" aria-label="Kanban">
          <span class="boton_vista-icono view-pill-icon-mask" aria-hidden="true" style="--view-pill-icon-url:url('/icon/boton/kanban.svg')"></span>
          <span class="view-pill-label boton_vista-label">Kanban</span>
        </button>
        <button class="view-pill boton_vista" type="button" data-pl-view="organigrama" data-tooltip="Organigrama" aria-label="Organigrama">
          <span class="boton_vista-icono view-pill-icon-mask" aria-hidden="true" style="--view-pill-icon-url:url('/icon/boton/organigrama.svg')"></span>
          <span class="view-pill-label boton_vista-label">Organigrama</span>
        </button>
    </div>
</div>
<div class="rounded-box border border-base-300 bg-base-100 p-4" style="margin:0 0 12px;">
    <input type="hidden" id="pl-edit-id" value="">
    <div class="pl-grid">
        <div class="pl-field">
            <label class="pl-label" for="pl-nombre">Nombre del puesto <span style="color:#ef4444">*</span></label>
            <input class="pl-input input input-bordered campo" id="pl-nombre" type="text" placeholder="Ej. Gerente de Marketing" autocomplete="off">
        </div>
        <div class="pl-field">
            <label class="pl-label" for="pl-area">Área a la que pertenece <span style="color:#ef4444">*</span></label>
            <select class="pl-select select select-bordered campo" id="pl-area">
                <option value="">— Sin área asignada —</option>
            </select>
        </div>
        <div class="pl-field">
            <label class="pl-label" for="pl-nivel">Nivel organizacional</label>
            <select class="pl-select select select-bordered campo" id="pl-nivel">
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
            <textarea class="pl-textarea textarea textarea-bordered campo" id="pl-desc" placeholder="Describe las responsabilidades principales del puesto..."></textarea>
        </div>
    </div>
</div>
<div class="tabs tabs-lifted w-full flex-wrap" role="tablist" aria-label="Puestos">
    <button class="tab rounded-t-lg tab-active active" data-pl-page-tab="1" data-ptab="puestos">Puestos laborales</button>
    <button class="tab rounded-t-lg" data-pl-page-tab="1" data-ptab="kpis">KPIs</button>
</div>
<div id="pl-view-puestos">
<div class="pl-wrap">
        <div class="grid grid-cols-1 gap-4">
        <div class="grid gap-4">
            <!-- Form -->
            <div class="pl-card" id="pl-card-form">
                <p class="pl-card-title" id="pl-form-title">Nuevo puesto laboral</p>
                <div class="pl-grid">
                    <div class="pl-field full">
                <details class="collapse collapse-arrow border border-base-300 bg-base-100" open>
                    <summary class="collapse-title text-base font-semibold">Habilidades requeridas</summary>
                    <div class="collapse-content grid gap-3">
                        <details class="collapse collapse-arrow border border-base-300 bg-base-100" open>
                            <summary class="collapse-title text-sm font-semibold">Habilidades blandas</summary>
                            <div class="collapse-content grid gap-2">
                                <div id="pl-hab-blandas-list" class="grid gap-2"></div>
                            </div>
                        </details>
                        <details class="collapse collapse-arrow border border-base-300 bg-base-100" open>
                            <summary class="collapse-title text-sm font-semibold">Habilidades duras</summary>
                            <div class="collapse-content grid gap-2">
                                <div id="pl-hab-duras-list" class="grid gap-2"></div>
                            </div>
                        </details>
                    </div>
                </details>
                    </div>
                </div>
                <div class="pl-form-actions">
                    <button class="pl-btn-save" id="pl-btn-save">Guardar puesto</button>
                    <button class="pl-btn-cancel" id="pl-btn-cancel">Cancelar</button>
                    <span class="pl-msg" id="pl-msg">&#10003; Guardado</span>
                </div>
            </div>
            <!-- List -->
            <article class="card bg-base-100 border border-base-300 shadow-sm" id="pl-card-list" style="display:none;">
                <div class="card-body gap-3">
                    <p class="pl-card-title">Listado de puestos <span id="pl-count" style="font-weight:400;font-size:.82rem;color:color-mix(in srgb,var(--button-bg,#0f172a) 40%,#ffffff 60%);"></span></p>
                    <div class="overflow-x-auto rounded-box border border-base-300">
                        <table class="table table-zebra table-sm md:table-md">
                            <thead>
                                <tr>
                                    <th>Nombre del puesto</th>
                                    <th>Área</th>
                                    <th>Nivel</th>
                                    <th>Descripción</th>
                                    <th class="text-right">Acciones</th>
                                </tr>
                            </thead>
                            <tbody id="pl-tbody"></tbody>
                        </table>
                    </div>
                </div>
            </article>
            <article class="card bg-base-100 border border-base-300 shadow-sm" id="pl-card-kanban" style="display:none;">
                <div class="card-body gap-3">
                    <p class="pl-card-title">Vista Kanban</p>
                    <div id="pl-kanban-host" class="grid grid-cols-1 lg:grid-cols-3 gap-4"></div>
                </div>
            </article>
            <article class="card bg-base-100 border border-base-300 shadow-sm" id="pl-card-organigrama" style="display:none;">
                <div class="card-body gap-3">
                    <p class="pl-card-title">Vista Organigrama</p>
                    <div id="pl-organigrama-host" class="grid grid-cols-1 lg:grid-cols-2 gap-4"></div>
                </div>
            </article>
        </div>
    </div>
</div>
</div>

<div id="pl-view-kpis" style="display:none;">
  <div class="pl-card">
    <p class="pl-card-title">KPIs por puesto laboral</p>
    <div class="pl-field" style="max-width:420px;margin-bottom:16px;">
      <label class="pl-label">Seleccionar puesto</label>
      <select class="pl-select select select-bordered campo" id="pl-kpi-sel"><option value="">&mdash; Seleccionar &mdash;</option></select>
    </div>
    <div id="pl-kpi-content" style="display:none;">
      <h3 id="pl-kpi-titulo" style="font-size:.95rem;font-weight:700;color:var(--sidebar-bottom,#0f172a);margin:0 0 16px;"></h3>
      <div id="pl-kpi-panel"></div>
      <div style="display:flex;gap:10px;align-items:center;margin-top:18px;padding-top:14px;border-top:1px solid color-mix(in srgb,var(--button-bg,#0f172a) 10%,#ffffff 90%);">
        <button class="pl-btn-save" id="pl-kpi-btn-save">Guardar KPIs</button>
        <span style="font-size:.82rem;color:#22c55e;display:none;" id="pl-kpi-saved">&#10003; Guardado</span>
      </div>
    </div>
  </div>
</div>

<div id="pl-view-notebook">
  <div class="pl-card">
    <p class="pl-card-title">Notebook de puestos</p>
    <div class="pl-field" style="max-width:420px;margin-bottom:16px;">
      <label class="pl-label">Seleccionar puesto</label>
      <select class="pl-select select select-bordered campo" id="pl-nbp-sel"><option value="">\u2014 Seleccionar \u2014</option></select>
    </div>
    <div id="pl-nbp-content" style="display:none;">
      <h3 id="pl-nbp-titulo" style="font-size:.95rem;font-weight:700;color:var(--sidebar-bottom,#0f172a);margin:0 0 16px;"></h3>
      <div class="pl-grid" style="margin-bottom:14px;">
        <div class="pl-field">
          <label class="pl-label">Área a la que pertenece</label>
          <input class="pl-input input input-bordered campo" id="pl-nbp-area" type="text" readonly>
        </div>
        <div class="pl-field">
          <label class="pl-label">Nivel organizacional</label>
          <input class="pl-input input input-bordered campo" id="pl-nbp-nivel" type="text" readonly>
        </div>
        <div class="pl-field full">
          <label class="pl-label">Descripción del puesto</label>
          <textarea class="pl-textarea textarea textarea-bordered campo" id="pl-nbp-desc" readonly></textarea>
        </div>
      </div>
      <div class="tabs tabs-lifted w-full flex-wrap" role="tablist" aria-label="Notebook de puestos">
        <button class="tab rounded-t-lg tab-active active" data-pl-nbp-tab="1" data-nbptab="hab">Habilidades requeridas</button>
        <button class="tab rounded-t-lg" data-pl-nbp-tab="1" data-nbptab="kpi">KPIs</button>
      </div>
      <div class="pl-nbp-panel active" id="pl-nbp-panel-hab"></div>
      <div class="pl-nbp-panel" id="pl-nbp-panel-kpi"></div>
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
    <div class="tabs tabs-lifted w-full flex-wrap" role="tablist" aria-label="Notebook del puesto">
        <button class="tab rounded-t-lg tab-active active" data-pl-nb-tab="1" data-tab="hab">Habilidades requeridas para el puesto</button>
        <button class="tab rounded-t-lg" data-pl-nb-tab="1" data-tab="col">Colaborador@s asignad@s</button>
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
    var areas = __INITIAL_AREAS__;
    var plCurrentView = 'form';
    var plFilters = { search: '', nivel: '' };
    var plHabCatalog = {};
    var plHabIndex = {};
    var plHabCatIndex = {};
    var plFormHab = { blandas: [], duras: [] };
    var _HAB_SOFT_KEYS = [
        'comunicacion_interpersonales',
        'liderazgo_gestion',
        'liderazgo_equipos',
        'resolucion_pensamiento',
        'organizacion_autogestion'
    ];
    var _HAB_HARD_KEYS = [
        'informatica_tecnologia_general',
        'tecnologias_informacion_it',
        'diseno_multimedia',
        'marketing_ventas_comunicacion',
        'finanzas_contabilidad_administracion',
        'logistica_produccion_operaciones',
        'idiomas_duros',
        'sector_salud',
        'sector_legal',
        'habilidades_manuales_tecnicas'
    ];
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
    var _HAB_CAT_ICONS = {
        'comunicacion_interpersonales': '🗣️',
        'liderazgo_gestion': '🌟',
        'liderazgo_equipos': '👥',
        'resolucion_pensamiento': '🧠',
        'organizacion_autogestion': '📅',
        'informatica_tecnologia_general': '💻',
        'tecnologias_informacion_it': '📡',
        'diseno_multimedia': '🎨',
        'marketing_ventas_comunicacion': '📈',
        'finanzas_contabilidad_administracion': '💵',
        'logistica_produccion_operaciones': '🚚',
        'idiomas_duros': '🌐',
        'sector_salud': '💊',
        'sector_legal': '⚖️',
        'habilidades_manuales_tecnicas': '🔨'
    };

    function setAreaOptions(selectedValue) {
        var sel = document.getElementById('pl-area');
        if (!sel) return;
        var selected = String(selectedValue || sel.value || '').trim();
        var catalog = [];
        (areas || []).forEach(function(a) {
            var name = String(a || '').trim();
            if (name && catalog.indexOf(name) === -1) catalog.push(name);
        });
        // Compatibilidad: incluir áreas de puestos existentes (si catálogo de departamentos viene vacío/parcial).
        (puestos || []).forEach(function(p) {
            var area = String((p && p.area) || '').trim();
            if (area && catalog.indexOf(area) === -1) catalog.push(area);
        });
        catalog.sort(function(a, b) { return a.localeCompare(b, 'es'); });
        sel.innerHTML = '<option value="">— Sin área asignada —</option>';
        if (!catalog.length) {
            var empty = document.createElement('option');
            empty.value = '';
            empty.textContent = '— No hay áreas registradas —';
            sel.appendChild(empty);
        } else {
            catalog.forEach(function(a) {
                var o = document.createElement('option');
                o.value = a;
                o.textContent = a;
                sel.appendChild(o);
            });
        }
        if (selected) {
            var exists = catalog.indexOf(selected) !== -1;
            sel.value = exists ? selected : '';
        } else {
            sel.value = '';
        }
    }

    function getFilteredPuestos() {
        var search = String(plFilters.search || '').trim().toLowerCase();
        var nivel = String(plFilters.nivel || '').trim().toLowerCase();
        return (puestos || []).filter(function(p) {
            var pNivel = String((p && p.nivel) || '').trim().toLowerCase();
            var hay = [
                p && p.nombre,
                p && p.area,
                p && p.nivel,
                p && p.descripcion
            ].map(function(v) { return String(v || '').toLowerCase(); }).join(' ');
            if (search && hay.indexOf(search) === -1) return false;
            if (nivel && pNivel !== nivel) return false;
            return true;
        });
    }

    function loadAreas() {
        var fallbackAreas = Array.isArray(areas) ? areas.slice() : [];
        return fetch('/api/inicio/departamentos')
            .then(function(r){ return r.json(); })
            .then(function(res){
                var payload = (res && res.data) || [];
                var fetchedAreas = (payload || []).map(function(a){
                    return (a && (a.name || a.nombre || a.area || a.code || '')) || '';
                }).filter(function(v){ return String(v || '').trim() !== ''; });
                if (fetchedAreas.length) {
                    areas = fetchedAreas;
                } else {
                    areas = fallbackAreas;
                }
                setAreaOptions();
            })
            .catch(function() {
                areas = fallbackAreas;
                setAreaOptions();
            });
    }

    // Load puestos
    function loadPuestos() {
        fetch('/api/puestos-laborales')
            .then(function(r){ return r.json(); })
            .then(function(res){ puestos = res.data || []; renderTable(); });
    }

    function renderTable() {
        var tbody = document.getElementById('pl-tbody');
        var cnt = document.getElementById('pl-count');
        if (!tbody) return;
        var visiblePuestos = getFilteredPuestos();
        if (cnt) cnt.textContent = visiblePuestos.length ? '(' + visiblePuestos.length + ')' : '';
        setAreaOptions();
        if (!visiblePuestos.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="pl-empty">No hay puestos registrados aún.</td></tr>';
            return;
        }
        tbody.innerHTML = '';
        visiblePuestos.forEach(function(p) {
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
                '<td style="white-space:nowrap" class="text-right">' +
                  '<button class="btn btn-ghost btn-xs nb" data-id="' + _esc(p.id) + '" title="Notebook">&#128203;' + nbBadge + '</button>' +
                  '<button class="btn btn-ghost btn-xs edit" data-id="' + _esc(p.id) + '" title="Editar">&#9998;</button>' +
                  '<button class="btn btn-ghost btn-xs text-error del" data-id="' + _esc(p.id) + '" title="Eliminar">&times;</button>' +
                '</td>';
            tr.querySelector('.nb').addEventListener('click', function(){ openNotebook(p.id); });
            tr.querySelector('.edit').addEventListener('click', function(){ startEdit(p.id); });
            tr.querySelector('.del').addEventListener('click', function(){ deletePuesto(p.id); });
            tbody.appendChild(tr);
        });
        if (plCurrentView === 'kanban') renderKanbanView();
        if (plCurrentView === 'organigrama') renderOrganigramaView();
    }

    function renderKanbanView() {
        var host = document.getElementById('pl-kanban-host');
        if (!host) return;
        var groups = { 'Sin nivel': [] };
        (getFilteredPuestos() || []).forEach(function(p) {
            var lvl = String((p && p.nivel) || '').trim() || 'Sin nivel';
            if (!groups[lvl]) groups[lvl] = [];
            groups[lvl].push(p);
        });
        var html = Object.keys(groups).sort(function(a, b) { return a.localeCompare(b, 'es'); }).map(function(name) {
            var cards = groups[name].map(function(p) {
                var habCount = (p.habilidades_requeridas || []).length;
                var colCount = (p.colaboradores_asignados || []).length;
                return '<article class="rounded-box border border-base-300 bg-base-100 p-3 grid gap-1">' +
                    '<strong class="text-base-content">' + _esc(p.nombre || '—') + '</strong>' +
                    '<span class="text-sm text-base-content/70">' + _esc(p.area || 'Sin área') + '</span>' +
                    '<span class="text-sm text-base-content/60">' + _esc(p.descripcion || 'Sin descripción') + '</span>' +
                    '<div class="flex items-center gap-2 mt-2">' +
                        '<span class="badge badge-outline badge-sm">Hab: ' + String(habCount || 0) + '</span>' +
                        '<span class="badge badge-outline badge-sm">Col: ' + String(colCount || 0) + '</span>' +
                    '</div>' +
                    '<div class="card-actions justify-end mt-2">' +
                        '<button type="button" class="btn btn-ghost btn-xs pl-kv-nb" data-id="' + _esc(p.id) + '">Notebook</button>' +
                        '<button type="button" class="btn btn-ghost btn-xs pl-kv-edit" data-id="' + _esc(p.id) + '">Editar</button>' +
                        '<button type="button" class="btn btn-ghost btn-xs text-error pl-kv-del" data-id="' + _esc(p.id) + '">Eliminar</button>' +
                    '</div>' +
                '</article>';
            }).join('') || '<p class="text-sm text-base-content/60">Sin registros.</p>';
            return '<section class="rounded-box border border-base-300 bg-base-200 p-3 grid gap-2">' +
                '<h4 class="font-semibold text-base-content">' + _esc(name) + '</h4>' +
                cards +
            '</section>';
        }).join('');
        host.innerHTML = html || '<p class="text-sm text-base-content/60">Sin puestos registrados.</p>';
        host.querySelectorAll('.pl-kv-nb').forEach(function(btn) {
            btn.addEventListener('click', function(){ openNotebook(btn.getAttribute('data-id')); });
        });
        host.querySelectorAll('.pl-kv-edit').forEach(function(btn) {
            btn.addEventListener('click', function(){ startEdit(btn.getAttribute('data-id')); setPlView('form'); });
        });
        host.querySelectorAll('.pl-kv-del').forEach(function(btn) {
            btn.addEventListener('click', function(){ deletePuesto(btn.getAttribute('data-id')); });
        });
    }

    function renderOrganigramaView() {
        var host = document.getElementById('pl-organigrama-host');
        if (!host) return;
        var grouped = {};
        (getFilteredPuestos() || []).forEach(function(p) {
            var area = String((p && p.area) || '').trim() || 'Sin área';
            if (!grouped[area]) grouped[area] = [];
            grouped[area].push(p);
        });
        var html = Object.keys(grouped).sort(function(a, b) { return a.localeCompare(b, 'es'); }).map(function(area) {
            var members = grouped[area].map(function(p) {
                var habCount = (p.habilidades_requeridas || []).length;
                return '<article class="rounded-box border border-base-300 bg-base-100 p-3">' +
                    '<strong class="text-base-content">' + _esc(p.nombre || '—') + '</strong>' +
                    '<div class="text-sm text-base-content/70 mt-1">' + _esc(p.nivel || 'Sin nivel') + '</div>' +
                    '<div class="text-xs text-base-content/60 mt-1">Habilidades: ' + String(habCount || 0) + '</div>' +
                    '<div class="card-actions justify-end mt-2">' +
                        '<button type="button" class="btn btn-ghost btn-xs pl-ov-nb" data-id="' + _esc(p.id) + '">Notebook</button>' +
                        '<button type="button" class="btn btn-ghost btn-xs pl-ov-edit" data-id="' + _esc(p.id) + '">Editar</button>' +
                    '</div>' +
                '</article>';
            }).join('');
            return '<section class="rounded-box border border-base-300 bg-base-200 p-4 grid gap-3">' +
                '<h4 class="font-semibold text-base-content">' + _esc(area) + '</h4>' +
                '<div class="grid gap-2">' + members + '</div>' +
            '</section>';
        }).join('');
        host.innerHTML = html || '<p class="text-sm text-base-content/60">Sin puestos registrados.</p>';
        host.querySelectorAll('.pl-ov-nb').forEach(function(btn) {
            btn.addEventListener('click', function(){ openNotebook(btn.getAttribute('data-id')); });
        });
        host.querySelectorAll('.pl-ov-edit').forEach(function(btn) {
            btn.addEventListener('click', function(){ startEdit(btn.getAttribute('data-id')); setPlView('form'); });
        });
    }

    function setPlView(view) {
        plCurrentView = ['form', 'list', 'kanban', 'organigrama'].indexOf(view) >= 0 ? view : 'form';
        var map = {
            form: document.getElementById('pl-card-form'),
            list: document.getElementById('pl-card-list'),
            kanban: document.getElementById('pl-card-kanban'),
            organigrama: document.getElementById('pl-card-organigrama')
        };
        Object.keys(map).forEach(function(key) {
            if (map[key]) map[key].style.display = key === plCurrentView ? '' : 'none';
        });
        document.querySelectorAll('[data-pl-view]').forEach(function(btn) {
            var isActive = btn.getAttribute('data-pl-view') === plCurrentView;
            btn.classList.toggle('active', isActive);
        });
        if (plCurrentView === 'list') renderTable();
        if (plCurrentView === 'kanban') renderKanbanView();
        if (plCurrentView === 'organigrama') renderOrganigramaView();
    }

    function _buildHabIndex(catalog) {
        var idx = {};
        _HAB_SOFT_KEYS.forEach(function(key) {
            (catalog[key] || []).forEach(function(skill) {
                var s = typeof skill === 'string' ? skill : (skill && (skill.nombre || skill.name));
                if (s) idx[String(s)] = 'blandas';
            });
        });
        _HAB_HARD_KEYS.forEach(function(key) {
            (catalog[key] || []).forEach(function(skill) {
                var s = typeof skill === 'string' ? skill : (skill && (skill.nombre || skill.name));
                if (s) idx[String(s)] = 'duras';
            });
        });
        return idx;
    }

    function _buildHabCatIndex(catalog) {
        var idx = {};
        _HAB_SOFT_KEYS.concat(_HAB_HARD_KEYS).forEach(function(key) {
            (catalog[key] || []).forEach(function(skill) {
                var s = typeof skill === 'string' ? skill : (skill && (skill.nombre || skill.name));
                if (s) idx[String(s)] = key;
            });
        });
        return idx;
    }

    function _normHabFormItem(raw) {
        if (raw && typeof raw === 'object') {
            return {
                nombre: String(raw.nombre || '').trim(),
                minimo: Math.min(100, Math.max(0, parseInt(raw.minimo, 10) || 0)),
                tipo: raw.tipo === 'duras' ? 'duras' : (raw.tipo === 'blandas' ? 'blandas' : '')
            };
        }
        return { nombre: String(raw || '').trim(), minimo: 0, tipo: '' };
    }

    function _splitHabByTipo(items) {
        var out = { blandas: [], duras: [] };
        (items || []).map(_normHabFormItem).forEach(function(it) {
            if (!it.nombre) return;
            var tipo = it.tipo || plHabIndex[it.nombre] || 'duras';
            if (tipo !== 'blandas' && tipo !== 'duras') tipo = 'duras';
            out[tipo].push({
                nombre: it.nombre,
                minimo: it.minimo,
                tipo: tipo,
                categoria: plHabCatIndex[it.nombre] || ''
            });
        });
        return out;
    }

    function _habOptionsHtml(tipo, selectedValue) {
        var keys = tipo === 'blandas' ? _HAB_SOFT_KEYS : _HAB_HARD_KEYS;
        var html = '<option value="">— Seleccionar habilidad —</option>';
        var selected = String(selectedValue || '');
        var seenSelected = false;
        var all = [];
        keys.forEach(function(key) {
            var skills = (plHabCatalog[key] || []).map(function(skill) {
                var s = typeof skill === 'string' ? skill : (skill && (skill.nombre || skill.name));
                return s ? String(s) : '';
            }).filter(Boolean);
            skills.forEach(function(s) {
                if (all.indexOf(s) === -1) all.push(s);
            });
        });
        all.sort(function(a, b) { return a.localeCompare(b); });
        all.forEach(function(s) {
            var sel = selected === s ? ' selected' : '';
            if (sel) seenSelected = true;
            html += '<option value="' + _esc(s) + '"' + sel + '>' + _esc(s) + '</option>';
        });
        if (selected && !seenSelected) {
            html += '<option value="' + _esc(selected) + '" selected>' + _esc(selected) + '</option>';
        }
        return html;
    }

    function _firstHabOption(tipo) {
        var keys = tipo === 'blandas' ? _HAB_SOFT_KEYS : _HAB_HARD_KEYS;
        for (var i = 0; i < keys.length; i += 1) {
            var list = plHabCatalog[keys[i]] || [];
            for (var j = 0; j < list.length; j += 1) {
                var skill = list[j];
                var s = typeof skill === 'string' ? skill : (skill && (skill.nombre || skill.name));
                if (s) return String(s);
            }
        }
        return '';
    }

    function _nextAvailableHab(tipo) {
        var keys = tipo === 'blandas' ? _HAB_SOFT_KEYS : _HAB_HARD_KEYS;
        var used = {};
        (plFormHab[tipo] || []).forEach(function(it) { used[String(it.nombre || '')] = true; });
        for (var i = 0; i < keys.length; i += 1) {
            var list = plHabCatalog[keys[i]] || [];
            for (var j = 0; j < list.length; j += 1) {
                var skill = list[j];
                var s = typeof skill === 'string' ? skill : (skill && (skill.nombre || skill.name));
                if (s && !used[String(s)]) return String(s);
            }
        }
        return _firstHabOption(tipo);
    }

    function _skillsForCat(catKey) {
        return (plHabCatalog[catKey] || []).map(function(skill) {
            var s = typeof skill === 'string' ? skill : (skill && (skill.nombre || skill.name));
            return s ? String(s) : '';
        }).filter(Boolean);
    }

    function _habOptionsHtmlCat(catKey, selectedValue) {
        var selected = String(selectedValue || '');
        var seenSelected = false;
        var skills = _skillsForCat(catKey);
        var html = '<option value="">— Seleccionar habilidad —</option>';
        skills.forEach(function(s) {
            var sel = selected === s ? ' selected' : '';
            if (sel) seenSelected = true;
            html += '<option value="' + _esc(s) + '"' + sel + '>' + _esc(s) + '</option>';
        });
        if (selected && !seenSelected) html += '<option value="' + _esc(selected) + '" selected>' + _esc(selected) + '</option>';
        return html;
    }

    function _nextAvailableHabByCat(tipo, catKey) {
        var used = {};
        (plFormHab[tipo] || []).forEach(function(it) { used[String(it.nombre || '')] = true; });
        var skills = _skillsForCat(catKey);
        for (var i = 0; i < skills.length; i += 1) {
            if (!used[skills[i]]) return skills[i];
        }
        return skills[0] || _nextAvailableHab(tipo);
    }

    function _hasAnyFormHab() {
        return Boolean((plFormHab && plFormHab.blandas && plFormHab.blandas.length) || (plFormHab && plFormHab.duras && plFormHab.duras.length));
    }

    function _buildDefaultHabByTipo(tipo) {
        var out = [];
        var seen = {};
        var keys = tipo === 'blandas' ? _HAB_SOFT_KEYS : _HAB_HARD_KEYS;
        keys.forEach(function(catKey) {
            (_skillsForCat(catKey) || []).forEach(function(skillName) {
                var key = String(skillName || '').trim();
                if (!key || seen[key]) return;
                seen[key] = true;
                out.push({
                    nombre: key,
                    minimo: 80,
                    tipo: tipo,
                    categoria: catKey
                });
            });
        });
        return out;
    }

    function _buildDefaultFormHabFromCatalog() {
        return {
            blandas: _buildDefaultHabByTipo('blandas'),
            duras: _buildDefaultHabByTipo('duras')
        };
    }

    function _renderHabRows(tipo) {
        if (!plFormHab || typeof plFormHab !== 'object') plFormHab = { blandas: [], duras: [] };
        if (!Array.isArray(plFormHab.blandas)) plFormHab.blandas = [];
        if (!Array.isArray(plFormHab.duras)) plFormHab.duras = [];
        var root = document.getElementById(tipo === 'blandas' ? 'pl-hab-blandas-list' : 'pl-hab-duras-list');
        if (!root) return;
        var rows = plFormHab[tipo] || [];
        var catKeys = tipo === 'blandas' ? _HAB_SOFT_KEYS : _HAB_HARD_KEYS;
        root.innerHTML = catKeys.map(function(catKey, catPos) {
            var catRows = rows.map(function(row, idx) { return { row: row, idx: idx }; }).filter(function(item) {
                var fromRow = String((item.row && item.row.categoria) || '').trim();
                var fromName = plHabCatIndex[String((item.row && item.row.nombre) || '').trim()] || '';
                return (fromRow && fromRow === catKey) || (!fromRow && fromName === catKey);
            });
            var rowHtml = catRows.map(function(item) {
                var options = _habOptionsHtmlCat(catKey, item.row.nombre);
                return (
                    '<div class="grid grid-cols-1 md:grid-cols-[1fr_180px_auto] gap-2 items-end">' +
                        '<div>' +
                            '<label class="pl-label">Nombre</label>' +
                            '<select class="pl-select select select-bordered campo pl-hab-name" data-tipo="' + tipo + '" data-cat="' + catKey + '" data-idx="' + item.idx + '">' + options + '</select>' +
                        '</div>' +
                        '<div>' +
                            '<label class="pl-label">% dominio mínimo</label>' +
                            '<input type="number" min="0" max="100" class="pl-input input input-bordered campo pl-hab-min" data-tipo="' + tipo + '" data-idx="' + item.idx + '" value="' + item.row.minimo + '">' +
                        '</div>' +
                        '<button type="button" class="btn btn-sm btn-error btn-outline pl-hab-del" data-tipo="' + tipo + '" data-idx="' + item.idx + '">Quitar</button>' +
                    '</div>'
                );
            }).join('');
            if (!rowHtml) rowHtml = '<div class="text-sm text-base-content/60">Sin habilidades agregadas en este bloque.</div>';
            return (
                '<details class="collapse collapse-arrow border border-base-300 bg-base-100" ' + (catPos === 0 ? 'open' : '') + '>' +
                    '<summary class="collapse-title text-sm font-semibold">' + _esc((_HAB_CAT_ICONS[catKey] || '•') + ' ' + (_HAB_CAT_LABELS[catKey] || catKey.replace(/_/g, ' '))) + '</summary>' +
                    '<div class="collapse-content grid gap-2">' +
                        rowHtml +
                        '<button type="button" class="btn btn-sm btn-outline pl-hab-add-cat" data-tipo="' + tipo + '" data-cat="' + catKey + '">Agregar habilidad</button>' +
                    '</div>' +
                '</details>'
            );
        }).join('');

        root.querySelectorAll('.pl-hab-name').forEach(function(el) {
            el.addEventListener('change', function() {
                var t = this.getAttribute('data-tipo');
                var cat = this.getAttribute('data-cat') || '';
                var idx = parseInt(this.getAttribute('data-idx'), 10);
                if (!plFormHab[t] || !plFormHab[t][idx]) return;
                plFormHab[t][idx].nombre = this.value.trim();
                if (cat) plFormHab[t][idx].categoria = cat;
                _renderHabRows(t);
            });
        });
        root.querySelectorAll('.pl-hab-min').forEach(function(el) {
            el.addEventListener('change', function() {
                var t = this.getAttribute('data-tipo');
                var idx = parseInt(this.getAttribute('data-idx'), 10);
                if (!plFormHab[t] || !plFormHab[t][idx]) return;
                plFormHab[t][idx].minimo = Math.min(100, Math.max(0, parseInt(this.value, 10) || 0));
                this.value = plFormHab[t][idx].minimo;
            });
        });
        root.querySelectorAll('.pl-hab-del').forEach(function(el) {
            el.addEventListener('click', function() {
                var t = this.getAttribute('data-tipo');
                var idx = parseInt(this.getAttribute('data-idx'), 10);
                if (!plFormHab[t]) return;
                plFormHab[t].splice(idx, 1);
                _renderHabRows(t);
            });
        });
        root.querySelectorAll('.pl-hab-add-cat').forEach(function(el) {
            el.addEventListener('click', function(ev) {
                ev.preventDefault();
                var t = this.getAttribute('data-tipo');
                var cat = this.getAttribute('data-cat');
                if (!plFormHab[t]) plFormHab[t] = [];
                plFormHab[t].push({
                    nombre: _nextAvailableHabByCat(t, cat),
                    minimo: 80,
                    tipo: t,
                    categoria: cat
                });
                _renderHabRows(t);
            });
        });
    }

    function _renderFormHab() {
        _renderHabRows('blandas');
        _renderHabRows('duras');
        ensurePuestosAccordionVisible();
    }

    function ensurePuestosAccordionVisible() {
        var root = document.getElementById('pl-view-puestos');
        if (!root) return;
        root.querySelectorAll('details.collapse').forEach(function(det) {
            if (!det.hasAttribute('open')) det.setAttribute('open', 'open');
            var content = det.querySelector(':scope > .collapse-content');
            if (content) {
                content.style.display = 'grid';
                content.style.maxHeight = 'none';
                content.style.opacity = '1';
            }
        });
    }

    function _getFormHabPayload() {
        var habs = [];
        ['blandas', 'duras'].forEach(function(tipo) {
            (plFormHab[tipo] || []).forEach(function(it) {
                var nombre = String(it.nombre || '').trim();
                if (!nombre) return;
                habs.push({
                    nombre: nombre,
                    minimo: Math.min(100, Math.max(0, parseInt(it.minimo, 10) || 0)),
                    tipo: tipo
                });
            });
        });
        return habs;
    }

    function _loadHabCatalogForForm() {
        return fetch('/api/habilidades-catalog')
            .then(function(r) { return r.json(); })
            .then(function(res) {
                plHabCatalog = res.catalog || res.data || res || {};
                plHabIndex = _buildHabIndex(plHabCatalog);
                plHabCatIndex = _buildHabCatIndex(plHabCatalog);
                var editIdEl = document.getElementById('pl-edit-id');
                var isEditing = Boolean(String((editIdEl && editIdEl.value) || '').trim());
                if (!isEditing && !_hasAnyFormHab()) {
                    plFormHab = _buildDefaultFormHabFromCatalog();
                }
                _renderFormHab();
            })
            .catch(function() {
                plHabCatalog = {};
                plHabIndex = {};
                plHabCatIndex = {};
                _renderFormHab();
            });
    }

    function startEdit(id) {
        var p = puestos.find(function(x){ return x.id === id; });
        if (!p) return;
        document.getElementById('pl-edit-id').value = p.id;
        document.getElementById('pl-nombre').value = p.nombre;
        setAreaOptions(p.area || '');
        document.getElementById('pl-nivel').value = p.nivel || '';
        document.getElementById('pl-desc').value = p.descripcion || '';
        plFormHab = _splitHabByTipo(p.habilidades_requeridas || []);
        _renderFormHab();
        document.getElementById('pl-form-title').textContent = 'Editar puesto laboral';
        document.getElementById('pl-btn-cancel').style.display = 'inline-block';
        document.getElementById('pl-nombre').focus();
    }

    function resetForm() {
        document.getElementById('pl-edit-id').value = '';
        document.getElementById('pl-nombre').value = '';
        setAreaOptions('');
        document.getElementById('pl-nivel').value = '';
        document.getElementById('pl-desc').value = '';
        plFormHab = _buildDefaultFormHabFromCatalog();
        _renderFormHab();
        document.getElementById('pl-form-title').textContent = 'Nuevo puesto laboral';
        document.getElementById('pl-btn-cancel').style.display = 'none';
        document.getElementById('pl-msg').style.display = 'none';
    }

    document.getElementById('pl-btn-cancel').addEventListener('click', resetForm);

    document.getElementById('pl-btn-save').addEventListener('click', function() {
        var nombre = document.getElementById('pl-nombre').value.trim();
        if (!nombre) { document.getElementById('pl-nombre').focus(); return; }
        var area = document.getElementById('pl-area').value.trim();
        if (!area) { document.getElementById('pl-area').focus(); return; }
        var payload = {
            id:          document.getElementById('pl-edit-id').value || undefined,
            nombre:      nombre,
            area:        area,
            nivel:       document.getElementById('pl-nivel').value,
            descripcion: document.getElementById('pl-desc').value.trim(),
            habilidades_requeridas: _getFormHabPayload(),
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
    document.querySelectorAll('[data-pl-view]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            setPlView(btn.getAttribute('data-pl-view') || 'form');
        });
    });
    (function bindPuestoNewShortcut() {
        var newBtn = document.getElementById('pl-btn-new-short');
        if (!newBtn) return;
        newBtn.addEventListener('click', function() {
            resetForm();
            setPlView('form');
            var nameInput = document.getElementById('pl-nombre');
            if (nameInput) nameInput.focus();
        });
    })();
    (function bindPuestoFilters() {
        var searchEl = document.getElementById('pl-filter-search');
        var nivelEl = document.getElementById('pl-filter-nivel');
        var clearEl = document.getElementById('pl-filter-clear');
        if (searchEl) {
            searchEl.addEventListener('input', function() {
                plFilters.search = String(searchEl.value || '').trim();
                renderTable();
            });
        }
        if (nivelEl) {
            nivelEl.addEventListener('change', function() {
                plFilters.nivel = String(nivelEl.value || '').trim();
                renderTable();
            });
        }
        if (clearEl) {
            clearEl.addEventListener('click', function() {
                plFilters = { search: '', nivel: '' };
                if (searchEl) searchEl.value = '';
                if (nivelEl) nivelEl.value = '';
                renderTable();
            });
        }
    })();

    var addBlandasBtn = document.getElementById('pl-hab-blandas-add');
    if (addBlandasBtn) {
        addBlandasBtn.addEventListener('click', function(ev) {
            ev.preventDefault();
            if (!plFormHab || typeof plFormHab !== 'object') plFormHab = { blandas: [], duras: [] };
            if (!Array.isArray(plFormHab.blandas)) plFormHab.blandas = [];
            plFormHab.blandas.push({ nombre: _nextAvailableHab('blandas'), minimo: 80, tipo: 'blandas', categoria: _HAB_SOFT_KEYS[0] });
            _renderHabRows('blandas');
        });
    }
    var addDurasBtn = document.getElementById('pl-hab-duras-add');
    if (addDurasBtn) {
        addDurasBtn.addEventListener('click', function(ev) {
            ev.preventDefault();
            if (!plFormHab || typeof plFormHab !== 'object') plFormHab = { blandas: [], duras: [] };
            if (!Array.isArray(plFormHab.duras)) plFormHab.duras = [];
            plFormHab.duras.push({ nombre: _nextAvailableHab('duras'), minimo: 80, tipo: 'duras', categoria: _HAB_HARD_KEYS[0] });
            _renderHabRows('duras');
        });
    }

    // ── Notebook drawer ────────────────────────────────────────────────────────
    var nbPuestoId = null;
    var nbActiveTab = 'hab';
    var nbHabCatalog = null;   // cached catalog
    var nbColabs = null;       // cached collaborators

    function openNotebook(id) {
        nbPuestoId = id;
        var p = puestos.find(function(x){ return x.id === id; });
        if (!p) return;
        document.getElementById('pl-nb-titulo').textContent = p.nombre;
        // reset tabs
        document.querySelectorAll('[data-pl-nb-tab][data-tab]').forEach(function(t){ t.classList.remove('active'); t.classList.remove('tab-active'); });
        document.querySelectorAll('.pl-nb-panel').forEach(function(t){ t.classList.remove('active'); });
        nbActiveTab = 'hab';
        document.querySelector('[data-pl-nb-tab][data-tab="hab"]').classList.add('active');
        document.querySelector('[data-pl-nb-tab][data-tab="hab"]').classList.add('tab-active');
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

    document.querySelectorAll('[data-pl-nb-tab][data-tab]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var tab = btn.getAttribute('data-tab');
            nbActiveTab = tab;
            document.querySelectorAll('[data-pl-nb-tab][data-tab]').forEach(function(t){ t.classList.remove('active'); t.classList.remove('tab-active'); });
            document.querySelectorAll('.pl-nb-panel').forEach(function(t){ t.classList.remove('active'); });
            btn.classList.add('active');
            btn.classList.add('tab-active');
            document.getElementById('pl-nb-panel-' + tab).classList.add('active');
        });
    });

    // ── Habilidades tab ─────────────────────────────────────────────────────────
    function _normHabItem(raw) {
        if (raw && typeof raw === 'object') {
            return {
                nombre: String(raw.nombre || '').trim(),
                minimo: parseInt(raw.minimo, 10) || 0,
                tipo: raw.tipo === 'duras' ? 'duras' : (raw.tipo === 'blandas' ? 'blandas' : '')
            };
        }
        return { nombre: String(raw || '').trim(), minimo: 0, tipo: '' };
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
                  '<select id="pl-nb-hab-sel" class="select select-bordered campo" style="width:100%;">' + selOpts + '</select>' +
                  '<div style="display:flex;gap:8px;align-items:center;">' +
                    '<label style="font-size:.85rem;color:#475569;white-space:nowrap;">Mínimo requerido</label>' +
                    '<input id="pl-nb-hab-pct" type="number" min="0" max="100" value="80" class="input input-bordered campo" style="width:72px;text-align:center;">' +
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
            var html = '<input class="pl-nb-search input input-bordered campo" id="' + searchId + '" placeholder="Buscar colaborador..." autocomplete="off">';
            html += '<div id="' + listId + '">';
            colabs.forEach(function(c) {
                var isChk = assigned.indexOf(String(c.id)) >= 0;
                var initials = (c.nombre || '?').split(' ').slice(0,2).map(function(w){ return w[0]; }).join('').toUpperCase();
                var dept = c.departamento || c.puesto || '';
                html += '<label class="pl-nb-col-item" data-nombre="' + _esc((c.nombre||'').toLowerCase()) + '">' +
                    '<input type="checkbox" value="' + _esc(String(c.id)) + '" ' + (isChk ? 'checked' : '') + '>' +
                    (c.imagen ? '<img class="pl-nb-avatar" src="' + _esc(c.imagen) + '" onerror="this.style.display=\\'none\\'">' : '<div class="pl-nb-avatar">' + _esc(initials) + '</div>') +
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
    document.querySelectorAll('[data-pl-page-tab][data-ptab]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var target = btn.getAttribute('data-ptab');
            document.querySelectorAll('[data-pl-page-tab][data-ptab]').forEach(function(t){ t.classList.remove('active'); t.classList.remove('tab-active'); });
            btn.classList.add('active');
            btn.classList.add('tab-active');
            var vP = document.getElementById('pl-view-puestos');
            var vN = document.getElementById('pl-view-notebook');
            var vK = document.getElementById('pl-view-kpis');
            vP.style.display = 'none';
            vN.style.display = 'none'; vN.classList.remove('active');
            vK.style.display = 'none';
            if (target === 'puestos') {
                vP.style.display = '';
            } else if (target === 'notebook') {
                vN.style.display = ''; vN.classList.add('active');
                var sel = document.getElementById('pl-nbp-sel');
                var cur = sel.value;
                sel.innerHTML = '<option value="">\u2014 Seleccionar \u2014</option>';
                puestos.forEach(function(p) {
                    var o = document.createElement('option');
                    o.value = p.id; o.textContent = p.nombre;
                    if (p.id === cur) o.selected = true;
                    sel.appendChild(o);
                });
            } else if (target === 'kpis') {
                vK.style.display = '';
                var ksel = document.getElementById('pl-kpi-sel');
                var kcur = ksel.value;
                ksel.innerHTML = '<option value="">\u2014 Seleccionar \u2014</option>';
                puestos.forEach(function(p) {
                    var o = document.createElement('option');
                    o.value = p.id; o.textContent = p.nombre;
                    if (p.id === kcur) o.selected = true;
                    ksel.appendChild(o);
                });
                if (kcur) ksel.dispatchEvent(new Event('change'));
            }
        });
    });

    // ── KPIs inline tab ───────────────────────────────────────────────
    var plKpiPuestoId = null;
    document.getElementById('pl-kpi-sel').addEventListener('change', function() {
        var id = this.value;
        var cont = document.getElementById('pl-kpi-content');
        if (!id) { cont.style.display = 'none'; plKpiPuestoId = null; return; }
        plKpiPuestoId = id;
        var p = puestos.find(function(x){ return x.id === id; });
        if (!p) return;
        cont.style.display = '';
        document.getElementById('pl-kpi-titulo').textContent = p.nombre || '';
        _renderKpiPanel(p.kpis || []);
    });

    function _renderKpiPanel(kpis) {
        var panel = document.getElementById('pl-kpi-panel');
        var html = '';
        (kpis || []).forEach(function(k, idx) {
            html += '<div class="grid grid-cols-1 md:grid-cols-[1fr_180px_180px_auto] gap-2 items-end pl-kpi-row" data-idx="' + idx + '">' +
                '<div><label class="pl-label">KPI</label><input class="pl-input input input-bordered campo pl-kpi-nombre" type="text" value="' + _esc(k.nombre || '') + '" placeholder="Nombre del KPI"></div>' +
                '<div><label class="pl-label">Meta</label><input class="pl-input input input-bordered campo pl-kpi-meta" type="text" value="' + _esc(k.meta || '') + '" placeholder="Ej. 95%"></div>' +
                '<div><label class="pl-label">Unidad</label><input class="pl-input input input-bordered campo pl-kpi-unidad" type="text" value="' + _esc(k.unidad || '') + '" placeholder="%, #, $..."></div>' +
                '<div style="padding-top:22px;"><button class="btn btn-sm btn-error btn-outline pl-kpi-del" type="button">&times;</button></div>' +
                '</div>';
        });
        html += '<div style="margin-top:10px;"><button id="pl-kpi-add" class="btn btn-sm btn-outline" type="button">+ Agregar KPI</button></div>';
        panel.innerHTML = html;
        panel.querySelectorAll('.pl-kpi-del').forEach(function(btn) {
            btn.addEventListener('click', function() { btn.closest('.pl-kpi-row').remove(); });
        });
        var addBtn = panel.querySelector('#pl-kpi-add');
        if (addBtn) addBtn.addEventListener('click', function() {
            _renderKpiPanel(_getKpiRows().concat([{nombre:'',meta:'',unidad:''}]));
        });
    }

    function _getKpiRows() {
        var rows = [];
        document.querySelectorAll('#pl-kpi-panel .pl-kpi-row').forEach(function(row) {
            rows.push({
                nombre: (row.querySelector('.pl-kpi-nombre') || {}).value || '',
                meta:   (row.querySelector('.pl-kpi-meta')   || {}).value || '',
                unidad: (row.querySelector('.pl-kpi-unidad') || {}).value || ''
            });
        });
        return rows;
    }

    document.getElementById('pl-kpi-btn-save').addEventListener('click', function() {
        if (!plKpiPuestoId) return;
        var kpis = _getKpiRows().filter(function(k){ return k.nombre.trim(); });
        fetch('/api/puestos-laborales', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ action: 'update_notebook', id: plKpiPuestoId, kpis: kpis }),
            credentials: 'include'
        })
        .then(function(r){ return r.json(); })
        .then(function(res) {
            if (res.success) {
                puestos = res.data;
                var msg = document.getElementById('pl-kpi-saved');
                msg.style.display = 'inline';
                setTimeout(function(){ msg.style.display = 'none'; }, 2200);
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
        document.getElementById('pl-nbp-area').value = p.area || '— Sin área asignada —';
        document.getElementById('pl-nbp-nivel').value = p.nivel || '— Sin nivel asignado —';
        document.getElementById('pl-nbp-desc').value = p.descripcion || 'Sin descripción.';
        cont.style.display = '';
        document.querySelectorAll('[data-pl-nbp-tab][data-nbptab]').forEach(function(t){ t.classList.remove('active'); t.classList.remove('tab-active'); });
        document.querySelectorAll('.pl-nbp-panel').forEach(function(t){ t.classList.remove('active'); });
        document.querySelector('[data-pl-nbp-tab][data-nbptab="hab"]').classList.add('active');
        document.querySelector('[data-pl-nbp-tab][data-nbptab="hab"]').classList.add('tab-active');
        document.getElementById('pl-nbp-panel-hab').classList.add('active');
        _nbpLoadHab(p);
        _nbpLoadKpi(p);
    });

    document.querySelectorAll('[data-pl-nbp-tab][data-nbptab]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var tab = btn.getAttribute('data-nbptab');
            if (tab === 'kpi') {
                window.location.href = '/inicio/departamentos/notebook-puesto';
                return;
            }
            document.querySelectorAll('[data-pl-nbp-tab][data-nbptab]').forEach(function(t){ t.classList.remove('active'); t.classList.remove('tab-active'); });
            document.querySelectorAll('.pl-nbp-panel').forEach(function(t){ t.classList.remove('active'); });
            btn.classList.add('active');
            btn.classList.add('tab-active');
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
                  '<select id="pl-nbp-hab-sel" class="select select-bordered campo" style="width:100%;">' + selOpts + '</select>' +
                  '<div style="display:flex;gap:8px;align-items:center;">' +
                    '<label style="font-size:.85rem;color:#475569;white-space:nowrap;">M\u00ednimo requerido</label>' +
                    '<input id="pl-nbp-hab-pct" type="number" min="0" max="100" value="80" class="input input-bordered campo" style="width:72px;text-align:center;">' +
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

    // ── KPIs (notebook page) ────────────────────────────────────────────────────
    function _nbpLoadKpi(p) {
        var panel = document.getElementById('pl-nbp-panel-kpi');
        var items = Array.isArray(p.kpis) ? p.kpis.slice() : [];
        function _rowHtml(it, idx) {
            var nombre = String((it && it.nombre) || '');
            var meta = String((it && it.meta) || '');
            var periodicidad = String((it && it.periodicidad) || '');
            return (
                '<div class="grid grid-cols-1 md:grid-cols-[1fr_180px_180px_auto] gap-2 items-end pl-nbp-kpi-row" data-idx="' + idx + '">' +
                    '<div>' +
                        '<label class="pl-label">Nombre KPI</label>' +
                        '<input class="pl-input input input-bordered campo pl-nbp-kpi-nombre" value="' + _esc(nombre) + '">' +
                    '</div>' +
                    '<div>' +
                        '<label class="pl-label">Meta</label>' +
                        '<input class="pl-input input input-bordered campo pl-nbp-kpi-meta" value="' + _esc(meta) + '">' +
                    '</div>' +
                    '<div>' +
                        '<label class="pl-label">Periodicidad</label>' +
                        '<select class="pl-select select select-bordered campo pl-nbp-kpi-period">' +
                            '<option value=""' + (periodicidad ? '' : ' selected') + '>— Seleccionar —</option>' +
                            '<option value="Diaria"' + (periodicidad === 'Diaria' ? ' selected' : '') + '>Diaria</option>' +
                            '<option value="Semanal"' + (periodicidad === 'Semanal' ? ' selected' : '') + '>Semanal</option>' +
                            '<option value="Mensual"' + (periodicidad === 'Mensual' ? ' selected' : '') + '>Mensual</option>' +
                            '<option value="Trimestral"' + (periodicidad === 'Trimestral' ? ' selected' : '') + '>Trimestral</option>' +
                            '<option value="Anual"' + (periodicidad === 'Anual' ? ' selected' : '') + '>Anual</option>' +
                        '</select>' +
                    '</div>' +
                    '<button class="btn btn-sm btn-error btn-outline pl-nbp-kpi-del" type="button">&times;</button>' +
                '</div>'
            );
        }
        function _render() {
            var html = '<div id="pl-nbp-kpi-list" style="display:flex;flex-direction:column;gap:10px;">';
            if (!items.length) html += '<p class="pl-nb-loading">Sin KPIs agregados.</p>';
            else html += items.map(function(it, idx) { return _rowHtml(it, idx); }).join('');
            html += '</div>';
            html += '<div style="margin-top:10px;"><button id="pl-nbp-kpi-add" class="btn btn-sm btn-outline" type="button">Agregar KPI</button></div>';
            panel.innerHTML = html;
            panel.querySelectorAll('.pl-nbp-kpi-del').forEach(function(btn) {
                btn.addEventListener('click', function() {
                    var row = btn.closest('.pl-nbp-kpi-row');
                    if (!row) return;
                    var idx = parseInt(row.getAttribute('data-idx'), 10);
                    if (Number.isNaN(idx)) return;
                    items.splice(idx, 1);
                    _render();
                });
            });
            var add = document.getElementById('pl-nbp-kpi-add');
            if (add) {
                add.addEventListener('click', function() {
                    items.push({ nombre: '', meta: '', periodicidad: '' });
                    _render();
                });
            }
        }
        _render();
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
        var kpis = [];
        document.querySelectorAll('#pl-nbp-panel-kpi .pl-nbp-kpi-row').forEach(function(row) {
            var nombreEl = row.querySelector('.pl-nbp-kpi-nombre');
            var metaEl = row.querySelector('.pl-nbp-kpi-meta');
            var periodEl = row.querySelector('.pl-nbp-kpi-period');
            var nombre = nombreEl ? nombreEl.value.trim() : '';
            var meta = metaEl ? metaEl.value.trim() : '';
            var periodicidad = periodEl ? periodEl.value.trim() : '';
            if (!nombre && !meta && !periodicidad) return;
            kpis.push({ nombre: nombre, meta: meta, periodicidad: periodicidad });
        });
        fetch('/api/puestos-laborales', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'update_notebook', id: nbpPuestoId, habilidades_requeridas: habs, kpis: kpis })
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

    setAreaOptions();   // poblar el select inmediatamente con __INITIAL_AREAS__
    loadAreas();        // luego actualizar desde la API (async)
    _loadHabCatalogForForm();
    loadPuestos();
    setPlView('form');
    ensurePuestosAccordionVisible();
})();
</script>
"""
    content = content.replace("__INITIAL_AREAS__", json.dumps(initial_areas, ensure_ascii=False))
    return render_backend_page(
        request,
        title="Puestos laborales",
        description="Gestión de puestos laborales",
        content=content,
        hide_floating_actions=True,
        floating_actions_screen="personalization",
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
        title="KPIs",
        description="Notebook del puesto laboral",
        content=content,
        hide_floating_actions=True,
        floating_actions_screen="personalization",
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
        floating_actions_screen="personalization",
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
    funciones_map = _load_departamentos_funciones_map()
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
                "funciones": _normalize_funciones_payload(funciones_map.get(code_key, {})),
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
    funciones_map_next: Dict[str, Dict[str, List[str]]] = {}
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
        funciones = _normalize_funciones_payload(item.get("funciones", {}))
        if not name or not code:
            continue
        code_key = code.lower()
        if code_key in used_codes:
            continue
        used_codes.add(code_key)
        funciones_map_next[code_key] = funciones
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
        _save_departamentos_funciones_map(funciones_map_next)
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
        funciones_map = _load_departamentos_funciones_map()
        funciones_map.pop(target_code.lower(), None)
        _save_departamentos_funciones_map(funciones_map)
        rows = (
            db.query(DepartamentoOrganizacional)
            .order_by(DepartamentoOrganizacional.orden.asc(), DepartamentoOrganizacional.id.asc())
            .all()
        )
        count_map = _build_empleados_count_map(rows)
        return {"success": True, "data": _serialize_departamentos(rows, count_map)}
    finally:
        db.close()
