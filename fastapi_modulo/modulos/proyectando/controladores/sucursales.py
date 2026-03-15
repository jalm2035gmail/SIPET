import json
from datetime import datetime
from html import escape
from textwrap import dedent
from typing import Any, Dict, List

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import HTMLResponse

from fastapi_modulo.modulos.proyectando.modelos.data_store import (
    load_datos_preliminares_store,
    load_sucursales_store,
    save_sucursales_store,
)

router = APIRouter()


def render_backend_page(*args, **kwargs):
    from fastapi_modulo.main import render_backend_page as _impl
    return _impl(*args, **kwargs)


def _load_datos_preliminares_store():
    return load_datos_preliminares_store()


def _load_sucursales_store():
    return load_sucursales_store()


def _save_sucursales_store(rows):
    return save_sucursales_store(rows)


@router.get("/inicio/sucursales", response_class=HTMLResponse)
def inicio_sucursales_page(request: Request):
    return _render_sucursales_page(request)


@router.get("/api/inicio/sucursales")
def listar_sucursales():
    return {"success": True, "data": _load_sucursales_store()}


@router.post("/api/inicio/sucursales")
async def guardar_sucursales(data: dict = Body(...)):
    incoming = data.get("data", [])
    if not isinstance(incoming, list):
        raise HTTPException(status_code=400, detail="Formato inválido")
    _save_sucursales_store(incoming)
    return {"success": True, "data": _load_sucursales_store()}




def _render_sucursales_page(request: Request) -> HTMLResponse:
    preliminares = _load_datos_preliminares_store()
    current_year = datetime.now().year
    try:
        MAIN_year = int((preliminares.get("primer_anio_proyeccion") or "").strip() or current_year)
    except (TypeError, ValueError):
        MAIN_year = current_year
    try:
        projection_years = int((preliminares.get("anios_proyeccion") or "").strip() or 3)
    except (TypeError, ValueError):
        projection_years = 3
    projection_years = max(1, min(projection_years, 10))
    column_offsets = [-4, -3, -2, -1, 0] + list(range(1, projection_years))

    def _header_label(offset: int) -> str:
        if offset < 0:
            return f"{offset} ({MAIN_year + offset})"
        if offset == 0:
            return f"Año actual ({MAIN_year})"
        return f"+{offset} ({MAIN_year + offset})"

    header_cells = "".join(f"<th>{escape(_header_label(offset))}</th>" for offset in column_offsets)
    rubros = [
        "Socios",
        "Menores Ahorradores",
        "Ahorro menores",
        "Captación a la vista",
        "Inversión",
        "Cartera de préstamos",
        "Cartera vencida",
    ]
    results_rows = []
    for row_idx, rubro in enumerate(rubros, start=1):
        inputs = "".join(
            (
                f'<td><input class="input input-bordered input-sm w-full text-right tabular-nums" type="number" step="0.01" min="0" '
                f'name="suc_result_{row_idx}_{offset}" placeholder="0.00"></td>'
            )
            for offset in column_offsets
        )
        results_rows.append(
            f"""
            <tr>
                <td class="font-semibold whitespace-nowrap">{escape(rubro)}</td>
                {inputs}
            </tr>
            """
        )
    resultados_rows_html = "".join(results_rows)
    activo_fijo_catalog = [
        {"rubro": "Terrenos", "years": 0},
        {"rubro": "Construcciones", "years": 20},
        {"rubro": "Construcciones en proceso", "years": 5},
        {"rubro": "Equipo de transporte", "years": 4},
        {"rubro": "Equipo de cómputo", "years": 3},
        {"rubro": "Mobiliario", "years": 3},
        {"rubro": "Otras propiedades, mobiliario y equipo", "years": 2},
    ]
    activo_fijo_catalog_json = json.dumps(activo_fijo_catalog, ensure_ascii=False)

    sucursales_content = dedent(f"""
        <section id="sucursales-module" class="grid gap-4 w-full">
            <div class="titulo bg-MAIN-200 rounded-box border border-MAIN-300 p-4 sm:p-6">
                <div class="w-full flex flex-col md:flex-row items-center gap-10">
                    <img
                        src="/templates/icon/sucursales.svg"
                        alt="Icono sucursales"
                        width="96"
                        height="96"
                        class="shrink-0 rounded-box border border-MAIN-300 bg-MAIN-100 p-3 object-contain"
                    />
                    <div class="w-full grid gap-2 content-center">
                        <div class="block w-full text-3xl sm:text-4xl lg:text-5xl font-bold leading-tight text-[color:var(--sidebar-bottom)]">Sucursales</div>
                        <div class="block w-full text-MAIN sm:text-lg text-MAIN-content/70">Registro y visualización de sucursales.</div>
                    </div>
                </div>
            </div>
            <div class="view-buttons page-view-buttons">
                <button class="view-pill boton_vista" type="button" data-view="form" data-tooltip="Formulario" aria-label="Formulario">
                    <span class="boton_vista-icono view-pill-icon-mask" aria-hidden="true" style="--view-pill-icon-url:url('/icon/boton/formulario.svg')"></span>
                    <span class="view-pill-label boton_vista-label">Formulario</span>
                </button>
                <button class="view-pill boton_vista active" type="button" data-view="list" data-tooltip="Lista" aria-label="Lista">
                    <span class="boton_vista-icono view-pill-icon-mask" aria-hidden="true" style="--view-pill-icon-url:url('/icon/boton/grid.svg')"></span>
                    <span class="view-pill-label boton_vista-label">Lista</span>
                </button>
                <button class="view-pill boton_vista" type="button" data-view="kanban" data-tooltip="Kanban" aria-label="Kanban">
                    <span class="boton_vista-icono view-pill-icon-mask" aria-hidden="true" style="--view-pill-icon-url:url('/icon/boton/kanban.svg')"></span>
                    <span class="view-pill-label boton_vista-label">Kanban</span>
                </button>
                <button class="view-pill boton_vista" type="button" data-view="organigrama" data-tooltip="Organigrama" aria-label="Organigrama">
                    <span class="boton_vista-icono view-pill-icon-mask" aria-hidden="true" style="--view-pill-icon-url:url('/icon/boton/organigrama.svg')"></span>
                    <span class="view-pill-label boton_vista-label">Organigrama</span>
                </button>
            </div>
            <div id="suc-layout" class="flex flex-col gap-4 lg:flex-row">
                <aside id="suc-filter-card" class="card bg-MAIN-100 border border-MAIN-300 shadow-sm lg:w-80 lg:shrink-0">
                    <div class="card-body space-y-3">
                        <h2 class="card-title text-[color:var(--sidebar-bottom)]">Sucursales</h2>
                        <label class="input input-bordered w-full flex items-center gap-2 campo campo-sin-borde">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="h-4 w-4 opacity-70 fill-current"><path d="M10 2a8 8 0 1 1 0 16 8 8 0 0 1 0-16Zm0 2a6 6 0 1 0 3.473 10.894l4.816 4.817 1.414-1.414-4.817-4.816A6 6 0 0 0 10 4Z"/></svg>
                            <input id="suc-filter-search" type="text" class="grow" placeholder="Buscar..." />
                        </label>
                        <div id="suc-filter-tree" class="menu bg-MAIN-100 rounded-box w-full max-h-[60vh] overflow-auto"></div>
                    </div>
                </aside>
                <div class="w-full min-w-0 lg:flex-1">
                    <div id="sucursales-view"></div>
                </div>
            </div>
        </section>
        <script>
            (() => {{
                const mount = document.getElementById('sucursales-view');
                const viewButtons = Array.from(document.querySelectorAll('#sucursales-module .view-buttons .view-pill[data-view]'));
                if (!mount) return;
                const filterSearchEl = document.getElementById('suc-filter-search');
                const filterTreeEl = document.getElementById('suc-filter-tree');
                const data = [];
                const activoFijoCatalog = {activo_fijo_catalog_json};
                const projectionYears = {projection_years};
                const MAINYear = {MAIN_year};
                const purchaseYearOptions = Array.from({{ length: projectionYears }}, (_, idx) => MAINYear + idx);
                const monthOptions = [
                    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
                ];
                const statusOptions = ["Solicitado", "Autorizado", "Comprado"];
                const activoFijoRowsData = [];
                const colaboradoresData = [];
                const regionCatalog = [];
                const regionRowsData = [];
                let currentView = 'list';
                let editingIndex = -1;
                let formTab = 'captura';
                let filterState = {{ type: 'all', value: '' }};
                let filterQuery = '';
                let orgLibPromise = null;
                let sucOrgChart = null;

                const escapeHtml = (value) => String(value || '').replace(/[&<>"']/g, (char) => (
                    {{ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }}[char] || char
                ));
                const normalizeSucursal = (row) => {{
                    const item = row && typeof row === 'object' ? row : {{}};
                    return {{
                        nombre: String(item.nombre || '').trim(),
                        region: String(item.region || '').trim(),
                        codigo: String(item.codigo || '').trim(),
                        descripcion: String(item.descripcion || '').trim(),
                    }};
                }};
                const replaceData = (rows) => {{
                    const normalized = Array.isArray(rows) ? rows.map(normalizeSucursal) : [];
                    data.splice(0, data.length, ...normalized);
                }};
                const normalizeRegionName = (value) => String(value || '').trim();
                const replaceRegionCatalog = (rows) => {{
                    const source = Array.isArray(rows) ? rows : [];
                    const cleanedRows = source
                        .filter((row) => row && typeof row === 'object')
                        .map((row) => ({{
                            nombre: normalizeRegionName(row.nombre),
                            codigo: String(row.codigo || '').trim(),
                            descripcion: String(row.descripcion || '').trim(),
                        }}))
                        .filter((row) => Boolean(row.nombre));
                    regionRowsData.splice(0, regionRowsData.length, ...cleanedRows);
                    const values = cleanedRows.map((row) => row.nombre);
                    const unique = Array.from(new Set(values)).sort((a, b) => a.localeCompare(b, 'es', {{ sensitivity: 'MAIN' }}));
                    regionCatalog.splice(0, regionCatalog.length, ...unique);
                }};
                const loadSucursales = async () => {{
                    try {{
                        const res = await fetch('/api/inicio/sucursales');
                        const json = await res.json().catch(() => ({{}}));
                        if (!res.ok || json?.success === false) throw new Error('No se pudieron cargar sucursales');
                        replaceData(json?.data || []);
                        renderFilterTree();
                    }} catch (_error) {{
                        replaceData([]);
                        renderFilterTree();
                    }}
                }};
                const persistSucursales = async () => {{
                    try {{
                        const res = await fetch('/api/inicio/sucursales', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ data }}),
                        }});
                        const json = await res.json().catch(() => ({{}}));
                        if (!res.ok || json?.success === false) throw new Error('No se pudieron guardar sucursales');
                        replaceData(json?.data || []);
                        renderFilterTree();
                        return true;
                    }} catch (_error) {{
                        return false;
                    }}
                }};
                const loadRegionesCatalog = async () => {{
                    try {{
                        const res = await fetch('/api/inicio/regiones');
                        const json = await res.json().catch(() => ({{}}));
                        if (!res.ok || json?.success === false) throw new Error('No se pudieron cargar regiones');
                        replaceRegionCatalog(json?.data || []);
                    }} catch (_error) {{
                        replaceRegionCatalog([]);
                    }}
                }};
                const persistRegionesCatalog = async () => {{
                    try {{
                        const res = await fetch('/api/inicio/regiones', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{ data: regionRowsData }}),
                        }});
                        const json = await res.json().catch(() => ({{}}));
                        if (!res.ok || json?.success === false) throw new Error('No se pudieron guardar regiones');
                        replaceRegionCatalog(json?.data || []);
                        return true;
                    }} catch (_error) {{
                        return false;
                    }}
                }};
                const normalizeColaborador = (row) => {{
                    const item = row && typeof row === 'object' ? row : {{}};
                    const eficiencia = item.eficiencia;
                    const desempenoRaw = (eficiencia === null || eficiencia === undefined || eficiencia === '')
                        ? ''
                        : String(eficiencia).trim();
                    return {{
                        nombre: String(item.nombre || '').trim(),
                        desempeno: desempenoRaw,
                    }};
                }};
                const replaceColaboradores = (rows) => {{
                    const normalized = Array.isArray(rows)
                        ? rows
                            .filter((row) => row && row.colaborador !== false)
                            .map(normalizeColaborador)
                            .filter((row) => Boolean(row.nombre))
                        : [];
                    colaboradoresData.splice(0, colaboradoresData.length, ...normalized);
                }};
                const loadColaboradores = async () => {{
                    try {{
                        const res = await fetch('/api/colaboradores', {{ headers: {{ Accept: 'application/json' }} }});
                        const json = await res.json().catch(() => ({{}}));
                        if (!res.ok || json?.success === false) throw new Error('No se pudieron cargar colaboradores');
                        replaceColaboradores(json?.data || []);
                    }} catch (_error) {{
                        replaceColaboradores([]);
                    }}
                }};

                const norm = (value) => String(value || '').trim().toLowerCase();
                const laneName = (region) => {{
                    const key = String(region || '').trim();
                    return key || 'Sin región';
                }};
                const isInSelectedRegion = (row) => {{
                    if (filterState.type !== 'region') return true;
                    const selected = norm(filterState.value);
                    if (!selected) return true;
                    return norm(laneName(row.region)) === selected;
                }};
                const matchesQuery = (row) => {{
                    if (!filterQuery) return true;
                    const q = norm(filterQuery);
                    return norm(row.nombre).includes(q) || norm(row.region).includes(q) || norm(row.codigo).includes(q) || norm(row.descripcion).includes(q);
                }};
                const getVisibleData = () => data.filter((row) => isInSelectedRegion(row) && matchesQuery(row));

                const renderFilterTree = () => {{
                    if (!filterTreeEl) return;
                    const total = data.length;
                    const byRegion = {{}};
                    data.forEach((row) => {{
                        const key = laneName(row.region);
                        if (!byRegion[key]) byRegion[key] = 0;
                        byRegion[key] += 1;
                    }});
                    const regions = Object.keys(byRegion).sort((a, b) => a.localeCompare(b, 'es', {{ sensitivity: 'MAIN' }}));
                    let html = '';
                    html += `<li><button type="button" class="${{filterState.type === 'all' ? 'active' : ''}}" data-filter-type="all" data-filter-value="">Todas <span class="ml-auto opacity-70">${{total}}</span></button></li>`;
                    regions.forEach((regionName) => {{
                        const active = filterState.type === 'region' && norm(filterState.value) === norm(regionName);
                        html += `<li><button type="button" class="${{active ? 'active' : ''}}" data-filter-type="region" data-filter-value="${{escapeHtml(regionName)}}">${{escapeHtml(regionName)}} <span class="ml-auto opacity-70">${{byRegion[regionName]}}</span></button></li>`;
                    }});
                    filterTreeEl.innerHTML = html;
                    Array.from(filterTreeEl.querySelectorAll('[data-filter-type]')).forEach((el) => {{
                        el.addEventListener('click', (event) => {{
                            event.preventDefault();
                            filterState = {{
                                type: el.getAttribute('data-filter-type') || 'all',
                                value: el.getAttribute('data-filter-value') || '',
                            }};
                            renderFilterTree();
                            render(currentView);
                        }});
                    }});
                }};

                const renderForm = () => {{
                    const current = editingIndex >= 0
                        ? data[editingIndex]
                        : {{ nombre: '', region: '', codigo: '', descripcion: '' }};
                    const currentRegion = normalizeRegionName(current.region);
                    const regionValues = Array.from(new Set([
                        ...regionCatalog,
                        ...(currentRegion ? [currentRegion] : []),
                    ]));
                    const regionOptionsHtml = regionValues
                        .sort((a, b) => a.localeCompare(b, 'es', {{ sensitivity: 'MAIN' }}))
                        .map((name) => `<option value="${{escapeHtml(name)}}" ${{name === currentRegion ? 'selected' : ''}}>${{escapeHtml(name)}}</option>`)
                        .join('');
                    const isCaptura = formTab === 'captura';
                    const isResultados = formTab === 'resultados';
                    const isActivoFijo = formTab === 'activo-fijo';
                    const isReparaciones = formTab === 'reparaciones';
                    const isColaboradores = formTab === 'colaboradores';
                    mount.innerHTML = `
                        <article class="card bg-MAIN-100 border border-MAIN-300 shadow-sm">
                            <div class="card-body gap-4">
                            <h3 class="card-title text-MAIN-content">Formulario de sucursales</h3>
                            <div class="rounded-box border border-MAIN-300 bg-MAIN-100 p-3">
                                <div class="tabs tabs-lifted w-full flex-wrap" role="tablist" aria-label="Control por sucursal">
                                    <button type="button" class="tab gap-2 rounded-t-lg ${{isCaptura ? 'tab-active' : ''}}" data-suc-form-tab="captura" aria-selected="${{isCaptura ? 'true' : 'false'}}">
                                        <img src="/templates/icon/form.svg" alt="" class="w-4 h-4">
                                        Captura
                                    </button>
                                    <button type="button" class="tab gap-2 rounded-t-lg ${{isResultados ? 'tab-active' : ''}}" data-suc-form-tab="resultados" aria-selected="${{isResultados ? 'true' : 'false'}}">
                                        <img src="/templates/icon/resultados.svg" alt="" class="w-4 h-4">
                                        Resultados
                                    </button>
                                    <button type="button" class="tab gap-2 rounded-t-lg ${{isActivoFijo ? 'tab-active' : ''}}" data-suc-form-tab="activo-fijo" aria-selected="${{isActivoFijo ? 'true' : 'false'}}">
                                        <img src="/templates/icon/activo_fijo.svg" alt="" class="w-4 h-4">
                                        Compras de activo fijo
                                    </button>
                                    <button type="button" class="tab gap-2 rounded-t-lg ${{isReparaciones ? 'tab-active' : ''}}" data-suc-form-tab="reparaciones" aria-selected="${{isReparaciones ? 'true' : 'false'}}">
                                        <img src="/templates/icon/reparaciones.svg" alt="" class="w-4 h-4">
                                        Reparaciones
                                    </button>
                                    <button type="button" class="tab gap-2 rounded-t-lg ${{isColaboradores ? 'tab-active' : ''}}" data-suc-form-tab="colaboradores" aria-selected="${{isColaboradores ? 'true' : 'false'}}">
                                        <img src="/templates/icon/cv.svg" alt="" class="w-4 h-4">
                                        Colaboradores
                                    </button>
                                </div>
                                <div class="-mt-px rounded-b-box border border-MAIN-300 bg-MAIN-100 p-4 grid gap-3">
                            <div class="${{isCaptura ? 'block' : 'hidden'}}" data-suc-form-panel="captura">
                            <form id="sucursales-form" class="grid gap-4">
                                <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                                    <label class="form-control w-full">
                                        <div class="label"><span class="label-text font-semibold">Nombre</span></div>
                                        <input id="sucursal-nombre" class="input input-bordered w-full campo campo-sin-borde" type="text" value="${{escapeHtml(current.nombre)}}" required>
                                    </label>
                                    <label class="form-control w-full">
                                        <div class="label"><span class="label-text font-semibold">Región</span></div>
                                        <select id="sucursal-region-select" class="select select-bordered w-full campo campo-sin-borde" required>
                                            <option value="">Seleccione región</option>
                                            ${{regionOptionsHtml}}
                                            <option value="__new__">+ Agregar región</option>
                                        </select>
                                        <input id="sucursal-region-new" class="input input-bordered w-full mt-2 hidden campo campo-sin-borde" type="text" placeholder="Nueva región">
                                    </label>
                                    <label class="form-control w-full">
                                        <div class="label"><span class="label-text font-semibold">Código</span></div>
                                        <input id="sucursal-codigo" class="input input-bordered w-full campo campo-sin-borde" type="text" value="${{escapeHtml(current.codigo)}}" required>
                                    </label>
                                    <label class="form-control w-full">
                                        <div class="label"><span class="label-text font-semibold">Descripción</span></div>
                                        <textarea id="sucursal-descripcion" class="textarea textarea-bordered w-full min-h-24 campo campo-sin-borde">${{escapeHtml(current.descripcion)}}</textarea>
                                    </label>
                                </div>
                                <div class="botones_accion">
                                    <button type="button" class="view-pill boton_vista" id="suc-btn-new" data-tooltip="Nuevo" aria-label="Nuevo" title="Nuevo">
                                        <span class="boton_vista-icono view-pill-icon-mask" aria-hidden="true" style="--view-pill-icon-url:url('/icon/boton/nuevo.svg')"></span>
                                        <span class="boton_vista-label">Nuevo</span>
                                    </button>
                                    <button type="button" class="view-pill boton_vista" id="suc-btn-edit" data-tooltip="Editar" aria-label="Editar" title="Editar">
                                        <span class="boton_vista-icono view-pill-icon-mask" aria-hidden="true" style="--view-pill-icon-url:url('/icon/boton/editar.svg')"></span>
                                        <span class="boton_vista-label">Editar</span>
                                    </button>
                                    <button type="submit" class="view-pill boton_vista" id="suc-btn-save" data-tooltip="Guardar" aria-label="Guardar" title="Guardar">
                                        <span class="boton_vista-icono view-pill-icon-mask" aria-hidden="true" style="--view-pill-icon-url:url('/icon/boton/guardar.svg')"></span>
                                        <span class="boton_vista-label">Guardar</span>
                                    </button>
                                    <button type="button" class="view-pill boton_vista" id="suc-btn-delete" data-tooltip="Eliminar" aria-label="Eliminar" title="Eliminar">
                                        <span class="boton_vista-icono view-pill-icon-mask" aria-hidden="true" style="--view-pill-icon-url:url('/icon/boton/eliminar.svg')"></span>
                                        <span class="boton_vista-label">Eliminar</span>
                                    </button>
                                </div>
                                <span class="text-sm text-MAIN-content/70" id="suc-form-msg">${{data.length}} registro(s)</span>
                            </form>
                            </div>
                            <div class="${{isResultados ? 'block' : 'hidden'}}" data-suc-form-panel="resultados">
                                <h3 class="text-lg font-semibold text-MAIN-content mb-3">Resultados</h3>
                                <div class="overflow-x-auto">
                                    <table class="table table-zebra table-pin-rows min-w-[980px]">
                                        <thead>
                                            <tr>
                                                <th>Rubro</th>
                                                {header_cells}
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {resultados_rows_html}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                            <div class="${{isActivoFijo ? 'block' : 'hidden'}}" data-suc-form-panel="activo-fijo">
                                <h3 class="text-lg font-semibold text-MAIN-content mb-3">Activo fijo</h3>
                                <div class="flex flex-wrap items-center gap-3 mb-3">
                                    <button type="button" class="btn btn-outline btn-primary btn-sm" id="suc-af-add-btn">Compra de activo fijo</button>
                                    <span class="text-xs text-MAIN-content/60">Procedimiento de autorización pendiente.</span>
                                </div>
                                <div class="overflow-x-auto">
                                    <table class="table table-zebra min-w-[980px]">
                                        <thead>
                                            <tr>
                                                <th>Código</th>
                                                <th>Artículo</th>
                                                <th>Rubro</th>
                                                <th>Precio</th>
                                                <th>Año de compra</th>
                                                <th>Mes de compra</th>
                                                <th>Status</th>
                                            </tr>
                                        </thead>
                                        <tbody id="suc-af-rows"></tbody>
                                    </table>
                                </div>
                            </div>
                            <div class="${{isReparaciones ? 'block' : 'hidden'}}" data-suc-form-panel="reparaciones">
                                <h3 class="text-lg font-semibold text-MAIN-content mb-2">Reparaciones</h3>
                                <p class="text-sm text-MAIN-content/70">Aquí se llevará el registro de las solicitudes de reparación de la sucursal.</p>
                                <p class="text-sm text-MAIN-content/70">Lógica y código pendientes.</p>
                            </div>
                            <div class="${{isColaboradores ? 'block' : 'hidden'}}" data-suc-form-panel="colaboradores">
                                <h3 class="text-lg font-semibold text-MAIN-content mb-2">Colaboradores</h3>
                                <div class="grid gap-3">
                                    <div class="flex flex-wrap items-center gap-3">
                                        <label class="form-control w-full sm:w-72">
                                            <div class="label"><span class="label-text font-semibold">Ordenar por</span></div>
                                            <select id="suc-colab-sort" class="select select-bordered w-full campo campo-sin-borde">
                                                <option value="nombre">Nombre</option>
                                                <option value="desempeno">Desempeño</option>
                                            </select>
                                        </label>
                                    </div>
                                    <div class="overflow-x-auto">
                                        <table class="table table-zebra">
                                            <thead>
                                                <tr>
                                                    <th>Nombre</th>
                                                    <th>Desempeño</th>
                                                </tr>
                                            </thead>
                                            <tbody id="suc-colab-rows"></tbody>
                                        </table>
                                    </div>
                                </div>
                            </div>
                                </div>
                            </div>
                            </div>
                        </article>
                    `;
                    const tabButtons = Array.from(mount.querySelectorAll('[data-suc-form-tab]'));
                    tabButtons.forEach((button) => {{
                        button.addEventListener('click', () => {{
                            formTab = button.getAttribute('data-suc-form-tab') || 'captura';
                            renderForm();
                        }});
                    }});
                    const form = document.getElementById('sucursales-form');
                    const formMsg = document.getElementById('suc-form-msg');
                    const newBtn = document.getElementById('suc-btn-new');
                    const editBtn = document.getElementById('suc-btn-edit');
                    const deleteBtn = document.getElementById('suc-btn-delete');
                    const regionSelect = document.getElementById('sucursal-region-select');
                    const regionNewInput = document.getElementById('sucursal-region-new');
                    const colaboradoresSortEl = document.getElementById('suc-colab-sort');
                    const upsertRegionOption = (name) => {{
                        if (!regionSelect) return;
                        const normalized = normalizeRegionName(name);
                        if (!normalized) return;
                        const options = Array.from(regionSelect.querySelectorAll('option'));
                        const exists = options.some((opt) => normalizeRegionName(opt.value) === normalized);
                        if (!exists) {{
                            const newOption = document.createElement('option');
                            newOption.value = normalized;
                            newOption.textContent = normalized;
                            const newMarker = regionSelect.querySelector('option[value="__new__"]');
                            if (newMarker) {{
                                regionSelect.insertBefore(newOption, newMarker);
                            }} else {{
                                regionSelect.appendChild(newOption);
                            }}
                        }}
                        regionSelect.value = normalized;
                    }};
                    const syncRegionNewVisibility = () => {{
                        if (!regionSelect || !regionNewInput) return;
                        const isNew = regionSelect.value === '__new__';
                        regionNewInput.classList.toggle('hidden', !isNew);
                        regionNewInput.required = isNew;
                    }};
                    regionSelect && regionSelect.addEventListener('change', syncRegionNewVisibility);
                    syncRegionNewVisibility();
                    const readValues = () => {{
                        const nombre = (document.getElementById('sucursal-nombre')?.value || '').trim();
                        const selectedRegion = (regionSelect?.value || '').trim();
                        const newRegion = (regionNewInput?.value || '').trim();
                        const region = selectedRegion === '__new__' ? newRegion : selectedRegion;
                        const codigo = (document.getElementById('sucursal-codigo')?.value || '').trim();
                        const descripcion = (document.getElementById('sucursal-descripcion')?.value || '').trim();
                        return {{ nombre, region, codigo, descripcion }};
                    }};
                    const setFormMsg = (text) => {{
                        if (!formMsg) return;
                        formMsg.textContent = text || `${{data.length}} registro(s)`;
                    }};
                    const resetCapturaInputs = () => {{
                        const nombreInput = document.getElementById('sucursal-nombre');
                        const codigoInput = document.getElementById('sucursal-codigo');
                        const descripcionInput = document.getElementById('sucursal-descripcion');
                        if (nombreInput) nombreInput.value = '';
                        if (codigoInput) codigoInput.value = '';
                        if (descripcionInput) descripcionInput.value = '';
                        if (regionSelect) regionSelect.value = '';
                        if (regionNewInput) regionNewInput.value = '';
                        syncRegionNewVisibility();
                    }};
                    form && form.addEventListener('submit', async (event) => {{
                        event.preventDefault();
                        const {{ nombre, region, codigo, descripcion }} = readValues();
                        if (!nombre || !region || !codigo) return;
                        const normalizedRegion = normalizeRegionName(region);
                        let regionSaved = true;
                        if (normalizedRegion && !regionCatalog.includes(normalizedRegion)) {{
                            regionRowsData.push({{ nombre: normalizedRegion, codigo: '', descripcion: '' }});
                            regionSaved = await persistRegionesCatalog();
                            if (!regionSaved) {{
                                setFormMsg('No se pudo guardar la nueva región.');
                                return;
                            }}
                            upsertRegionOption(normalizedRegion);
                        }}
                        const payload = {{ nombre, region: normalizedRegion, codigo, descripcion }};
                        if (editingIndex >= 0) {{
                            data[editingIndex] = payload;
                        }} else {{
                            data.push(payload);
                        }}
                        editingIndex = -1;
                        const saved = await persistSucursales();
                        if (saved) resetCapturaInputs();
                        setFormMsg(saved ? `Sucursal guardada. Total: ${{data.length}}` : 'No se pudo guardar en la BD/store.');
                    }});
                    newBtn && newBtn.addEventListener('click', () => {{
                        editingIndex = -1;
                        renderForm();
                    }});
                    editBtn && editBtn.addEventListener('click', () => {{
                        const {{ codigo }} = readValues();
                        if (!codigo) {{
                            setFormMsg('Capture el código para editar.');
                            return;
                        }}
                        const idx = data.findIndex((row) => String(row.codigo).trim() === codigo);
                        if (idx < 0) {{
                            setFormMsg('No se encontró sucursal con ese código.');
                            return;
                        }}
                        editingIndex = idx;
                        renderForm();
                        setTimeout(() => {{
                            const msg = document.getElementById('suc-form-msg');
                            if (msg) msg.textContent = `Editando sucursal: ${{codigo}}`;
                        }}, 0);
                    }});
                    deleteBtn && deleteBtn.addEventListener('click', async () => {{
                        const {{ codigo }} = readValues();
                        const idx = editingIndex >= 0
                            ? editingIndex
                            : data.findIndex((row) => String(row.codigo).trim() === codigo);
                        if (idx < 0) {{
                            setFormMsg('No hay sucursal para eliminar.');
                            return;
                        }}
                        data.splice(idx, 1);
                        editingIndex = -1;
                        const saved = await persistSucursales();
                        if (saved) resetCapturaInputs();
                        setFormMsg(saved ? `Sucursal eliminada. Total: ${{data.length}}` : 'No se pudo guardar eliminación en la BD/store.');
                    }});
                    const afAddBtn = document.getElementById('suc-af-add-btn');
                    const afRowsEl = document.getElementById('suc-af-rows');
                    afAddBtn && afAddBtn.addEventListener('click', addActivoFijoRow);
                    afRowsEl && afRowsEl.addEventListener('input', (event) => {{
                        const target = event.target;
                        if (!(target instanceof HTMLElement)) return;
                        const rowElem = target.closest('tr[data-af-row]');
                        if (!rowElem) return;
                        const rowIndex = Number(rowElem.getAttribute('data-af-row'));
                        const row = activoFijoRowsData[rowIndex];
                        if (!row) return;
                        const field = target.getAttribute('data-field');
                        if (!field) return;
                        row[field] = target.value;
                    }});
                    afRowsEl && afRowsEl.addEventListener('change', (event) => {{
                        const target = event.target;
                        if (!(target instanceof HTMLElement)) return;
                        const rowElem = target.closest('tr[data-af-row]');
                        if (!rowElem) return;
                        const rowIndex = Number(rowElem.getAttribute('data-af-row'));
                        const row = activoFijoRowsData[rowIndex];
                        if (!row) return;
                        const field = target.getAttribute('data-field');
                        if (!field) return;
                        row[field] = target.value;
                    }});
                    renderActivoFijoRows();
                    colaboradoresSortEl && colaboradoresSortEl.addEventListener('change', renderColaboradoresRows);
                    renderColaboradoresRows();
                }};

                const renderList = () => {{
                    const visible = getVisibleData();
                    mount.innerHTML = `
                        <article class="card bg-MAIN-100 border border-MAIN-300 shadow-sm">
                            <div class="card-body gap-4">
                            <h3 class="card-title text-MAIN-content">Lista de sucursales</h3>
                            <div class="overflow-x-auto">
                                <table class="table lista">
                                    <thead>
                                        <tr>
                                            <th>Nombre</th>
                                            <th>Región</th>
                                            <th>Código</th>
                                            <th>Descripción</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${{visible.length ? visible.map((row) => `
                                            <tr data-suc-open-form-row data-row-code="${{escapeHtml(row.codigo)}}" class="cursor-pointer hover">
                                                <td>${{escapeHtml(row.nombre)}}</td>
                                                <td>${{escapeHtml(row.region)}}</td>
                                                <td>${{escapeHtml(row.codigo)}}</td>
                                                <td>${{escapeHtml(row.descripcion)}}</td>
                                            </tr>
                                        `).join('') : `
                                            <tr><td colspan="4" class="text-MAIN-content/60">Sin registros.</td></tr>
                                        `}}
                                    </tbody>
                                </table>
                            </div>
                            </div>
                        </article>
                    `;
                }};

                const renderKanban = () => {{
                    const visible = getVisibleData();
                    mount.innerHTML = `
                        <article class="card bg-MAIN-100 border border-MAIN-300 shadow-sm">
                            <div class="card-body gap-4">
                            <h3 class="card-title text-MAIN-content">Kanban de sucursales</h3>
                            ${{visible.length ? `
                                <div class="kanban">
                                    ${{visible.map((row) => `
                                        <article data-suc-item data-row-code="${{escapeHtml(row.codigo)}}" class="kanban-item cursor-pointer">
                                            <div class="kanban-color" style="background: var(--sidebar-bottom, #0f172a); color: var(--sidebar-text, #ffffff);">
                                                ${{escapeHtml((row.nombre || '?').charAt(0).toUpperCase())}}
                                            </div>
                                            <div class="kanban-content">
                                                <p class="kanban-title">${{escapeHtml(row.nombre)}}</p>
                                                <p class="kanban-meta"><strong>Región:</strong> ${{escapeHtml(row.region || 'Sin región')}}</p>
                                                <p class="kanban-meta"><strong>Código:</strong> ${{escapeHtml(row.codigo)}}</p>
                                                <p class="kanban-meta"><strong>Descripción:</strong> ${{escapeHtml(row.descripcion || '—')}}</p>
                                            </div>
                                        </article>
                                    `).join('')}}
                                </div>
                            ` : '<p class="text-sm text-MAIN-content/60">Sin registros.</p>'}}
                            </div>
                        </article>
                    `;
                }};

                const loadScript = (src) => new Promise((resolve, reject) => {{
                    if (document.querySelector(`script[src="${{src}}"]`)) {{
                        resolve();
                        return;
                    }}
                    const script = document.createElement('script');
                    script.src = src;
                    script.async = true;
                    script.onload = () => resolve();
                    script.onerror = () => reject(new Error(`No se pudo cargar ${{src}}`));
                    document.head.appendChild(script);
                }});

                const ensureOrgLibrary = async () => {{
                    if (window.d3 && window.d3.OrgChart) return true;
                    if (!orgLibPromise) {{
                        orgLibPromise = (async () => {{
                            await loadScript('/static/vendor/d3.min.js');
                            await loadScript('/static/vendor/d3-flextree.min.js');
                            await loadScript('/static/vendor/d3-org-chart.min.js');
                        }})().catch(() => false);
                    }}
                    const result = await orgLibPromise;
                    return result !== false && !!(window.d3 && window.d3.OrgChart);
                }};

                const renderOrganigrama = async () => {{
                    const visible = getVisibleData();
                    mount.innerHTML = `
                        <article class="card bg-MAIN-100 border border-MAIN-300 shadow-sm">
                            <div class="card-body gap-4">
                                <h3 class="card-title text-MAIN-content">Organigrama de sucursales</h3>
                                <div id="suc-org-chart" class="w-full min-h-[640px] overflow-auto rounded-box border border-MAIN-300 bg-MAIN-200 p-3">
                                    <p class="text-sm text-MAIN-content/70">Cargando organigrama...</p>
                                </div>
                            </div>
                        </article>
                    `;
                    const orgChartEl = document.getElementById('suc-org-chart');
                    if (!orgChartEl) return;
                    if (!visible.length) {{
                        orgChartEl.innerHTML = '<p class="text-sm text-MAIN-content/70">Sin registros para organizar.</p>';
                        return;
                    }}
                    const libOk = await ensureOrgLibrary();
                    if (!libOk) {{
                        orgChartEl.innerHTML = '<p class="text-sm text-MAIN-content/70">No se pudo cargar la librería de organigrama.</p>';
                        return;
                    }}
                    const nodes = [];
                    const regionMap = {{}};
                    visible.forEach((row) => {{
                        const regionName = laneName(row.region);
                        const regionId = `region::${{regionName}}`;
                        if (!regionMap[regionId]) {{
                            regionMap[regionId] = true;
                            nodes.push({{
                                id: regionId,
                                parentId: '',
                                name: regionName,
                                manager: 'Región',
                                code: regionName,
                                color: '#0f172a',
                                isRegion: true,
                            }});
                        }}
                        nodes.push({{
                            id: String(row.codigo || row.nombre || Math.random().toString(36).slice(2)),
                            parentId: regionId,
                            name: String(row.nombre || 'Sucursal'),
                            manager: String(row.region || 'Sin región'),
                            code: String(row.codigo || '—'),
                            color: '#ffffff',
                            descripcion: String(row.descripcion || ''),
                            isRegion: false,
                        }});
                    }});
                    orgChartEl.innerHTML = '';
                    sucOrgChart = new window.d3.OrgChart()
                        .container(orgChartEl)
                        .data(nodes)
                        .nodeWidth(() => 320)
                        .nodeHeight(() => 150)
                        .childrenMargin(() => 48)
                        .compact(true)
                        .initialExpandLevel(2)
                        .setActiveNodeCentered(true)
                        .nodeButtonWidth(() => 36)
                        .nodeButtonHeight(() => 36)
                        .nodeButtonX(() => -18)
                        .nodeButtonY(() => -18)
                        .buttonContent((ctx) => {{
                            const node = ctx && ctx.node ? ctx.node : null;
                            const expanded = !!(node && node.children);
                            const sign = expanded ? '−' : '+';
                            const count = Number(node && node.data ? node.data._directSubordinates || 0 : 0);
                            return `<div style="width:36px;height:36px;border-radius:9999px;background:#0f172a;color:#fff;display:grid;place-items:center;font-weight:800;font-size:18px;border:2px solid #fff;box-shadow:0 4px 10px rgba(15,23,42,.22);">${{sign}}${{count > 0 ? `<span style='font-size:10px;margin-left:2px;'>${{count}}</span>` : ''}}</div>`;
                        }})
                        .nodeContent((d) => {{
                            const item = d && d.data ? d.data : {{}};
                            const isRegion = !!item.isRegion;
                            const color = isRegion ? '#0f172a' : '#ffffff';
                            const textColor = isRegion ? '#ffffff' : '#0f172a';
                            const sideLetter = isRegion ? 'R' : (item.name || '?').charAt(0).toUpperCase();
                            return ''
                                + '<div style="display:grid;grid-template-columns:90px 1fr;height:146px;border:1px solid #dbe2ea;border-radius:12px;overflow:hidden;background:#fff;box-shadow:0 6px 14px rgba(15,23,42,.12);font-family:inherit;">'
                                +   `<div style="background:${{color}};color:${{textColor}};display:flex;align-items:center;justify-content:center;font-size:56px;font-weight:800;">${{escapeHtml(sideLetter)}}</div>`
                                +   '<div style="padding:12px;display:grid;gap:6px;align-content:start;">'
                                +     `<div style="font-size:24px;font-weight:800;color:#0f172a;line-height:1.1;">${{escapeHtml(item.name || 'Sucursal')}}</div>`
                                +     `<div style="font-size:14px;color:#334155;"><strong>Región:</strong> ${{escapeHtml(item.manager || 'Sin región')}}</div>`
                                +     `<div style="font-size:14px;color:#334155;"><strong>Código:</strong> ${{escapeHtml(item.code || '—')}}</div>`
                                +   '</div>'
                                + '</div>';
                        }})
                        .render();
                }};

                const setActiveViewButton = (view) => {{
                    viewButtons.forEach((btn) => {{
                        btn.classList.toggle('active', btn.getAttribute('data-view') === view);
                    }});
                }};

                const render = (view) => {{
                    currentView = ['form', 'list', 'kanban', 'organigrama'].includes(view) ? view : 'list';
                    setActiveViewButton(currentView);
                    if (currentView === 'list') return renderList();
                    if (currentView === 'kanban') return renderKanban();
                    if (currentView === 'organigrama') return renderOrganigrama();
                    return renderForm();
                }};
                const openFormByCode = (codigo) => {{
                    const targetCode = String(codigo || '').trim();
                    if (!targetCode) return;
                    const idx = data.findIndex((row) => String(row.codigo || '').trim() === targetCode);
                    if (idx < 0) return;
                    editingIndex = idx;
                    formTab = 'captura';
                    render('form');
                    const msg = document.getElementById('suc-form-msg');
                    if (msg) msg.textContent = `Editando sucursal: ${{targetCode}}`;
                }};

                const normalizeSucursalCode = () => {{
                    const raw = String(data[0]?.codigo || '').trim();
                    if (!raw) return "001";
                    const digits = raw.replace(/\\D+/g, "");
                    if (digits) return digits;
                    const normalized = raw.toUpperCase().replace(/[^A-Z0-9]+/g, "");
                    return normalized || "001";
                }};

                const generateActivoFijoCode = () => {{
                    const branchCode = normalizeSucursalCode();
                    const sequence = String(activoFijoRowsData.length + 1).padStart(3, "0");
                    return `${{branchCode}}-${{sequence}}`;
                }};
                const renderColaboradoresRows = () => {{
                    const tbody = document.getElementById('suc-colab-rows');
                    if (!tbody) return;
                    const sortEl = document.getElementById('suc-colab-sort');
                    const sortBy = (sortEl && sortEl.value) || 'nombre';
                    const rows = [...colaboradoresData].sort((a, b) => {{
                        if (sortBy === 'desempeno') {{
                            const aNum = Number(a.desempeno);
                            const bNum = Number(b.desempeno);
                            const aValid = Number.isFinite(aNum);
                            const bValid = Number.isFinite(bNum);
                            if (aValid && bValid) return bNum - aNum;
                            if (aValid) return -1;
                            if (bValid) return 1;
                        }}
                        return String(a.nombre || '').localeCompare(String(b.nombre || ''), 'es', {{ sensitivity: 'MAIN' }});
                    }});
                    if (!rows.length) {{
                        tbody.innerHTML = '<tr><td colspan="2" class="text-MAIN-content/60">Sin colaboradores asignados.</td></tr>';
                        return;
                    }}
                    tbody.innerHTML = rows.map((row) => `
                        <tr>
                            <td>${{escapeHtml(row.nombre)}}</td>
                            <td>${{escapeHtml(row.desempeno || 'N/D')}}</td>
                        </tr>
                    `).join('');
                }};

                const rubroSelectOptions = (selected) => activoFijoCatalog.map((item) => {{
                    const isSelected = item.rubro === selected ? "selected" : "";
                    return `<option value="${{escapeHtml(item.rubro)}}" ${{isSelected}}>${{escapeHtml(item.rubro)}}</option>`;
                }}).join("");
                const yearSelectOptions = (selected) => purchaseYearOptions.map((year) => {{
                    const isSelected = Number(selected) === Number(year) ? "selected" : "";
                    return `<option value="${{year}}" ${{isSelected}}>${{year}}</option>`;
                }}).join("");
                const monthSelectOptions = (selected) => monthOptions.map((month, idx) => {{
                    const value = idx + 1;
                    const isSelected = Number(selected) === value ? "selected" : "";
                    return `<option value="${{value}}" ${{isSelected}}>${{month}}</option>`;
                }}).join("");
                const statusSelectOptions = (selected) => statusOptions.map((status) => {{
                    const isSelected = status === selected ? "selected" : "";
                    return `<option value="${{escapeHtml(status)}}" ${{isSelected}}>${{escapeHtml(status)}}</option>`;
                }}).join("");

                const renderActivoFijoRows = () => {{
                    const activoFijoRows = document.getElementById('suc-af-rows');
                    if (!activoFijoRows) return;
                    if (!activoFijoRowsData.length) {{
                        activoFijoRows.innerHTML = '<tr><td colspan="7" class="text-MAIN-content/60">Sin registros de compras.</td></tr>';
                        return;
                    }}
                    activoFijoRows.innerHTML = activoFijoRowsData.map((row, idx) => `
                        <tr data-af-row="${{idx}}">
                            <td><input class="input input-bordered input-sm w-full" type="text" data-field="code" value="${{escapeHtml(row.code)}}" readonly></td>
                            <td><input class="input input-bordered input-sm w-full" type="text" data-field="article" value="${{escapeHtml(row.article)}}"></td>
                            <td><select class="select select-bordered select-sm w-full" data-field="rubro">${{rubroSelectOptions(row.rubro)}}</select></td>
                            <td><input class="input input-bordered input-sm w-full text-right tabular-nums" type="number" min="0" step="0.01" data-field="price" value="${{escapeHtml(row.price)}}"></td>
                            <td><select class="select select-bordered select-sm w-full" data-field="year">${{yearSelectOptions(row.year)}}</select></td>
                            <td><select class="select select-bordered select-sm w-full" data-field="month">${{monthSelectOptions(row.month)}}</select></td>
                            <td><select class="select select-bordered select-sm w-full" data-field="status">${{statusSelectOptions(row.status)}}</select></td>
                        </tr>
                    `).join("");
                }};

                const addActivoFijoRow = () => {{
                    const firstRubro = activoFijoCatalog[0]?.rubro || "";
                    const newRow = {{
                        code: generateActivoFijoCode(),
                        article: "",
                        rubro: firstRubro,
                        price: "",
                        year: purchaseYearOptions[0] || MAINYear,
                        month: 1,
                        status: "Solicitado",
                    }};
                    activoFijoRowsData.push(newRow);
                    renderActivoFijoRows();
                }};

                document.addEventListener('backend-view-change', (event) => {{
                    const view = event.detail?.view;
                    if (!view) return;
                    render(view);
                }});
                viewButtons.forEach((btn) => {{
                    btn.addEventListener('click', () => {{
                        render(btn.getAttribute('data-view') || 'list');
                    }});
                }});
                mount.addEventListener('click', (event) => {{
                    const target = event.target;
                    if (!(target instanceof HTMLElement)) return;
                    const listRow = target.closest('[data-suc-open-form-row]');
                    if (listRow instanceof HTMLElement) {{
                        openFormByCode(listRow.getAttribute('data-row-code') || '');
                        return;
                    }}
                    const kanbanCard = target.closest('[data-suc-item]');
                    if (kanbanCard instanceof HTMLElement) {{
                        const codeText = (kanbanCard.getAttribute('data-row-code') || '').trim();
                        openFormByCode(codeText);
                        return;
                    }}
                    const organigramaCard = target.closest('[data-suc-org-item]');
                    if (organigramaCard instanceof HTMLElement) {{
                        const codeText = (organigramaCard.getAttribute('data-row-code') || '').trim();
                        openFormByCode(codeText);
                    }}
                }});
                filterSearchEl && filterSearchEl.addEventListener('input', () => {{
                    filterQuery = filterSearchEl.value || '';
                    render(currentView);
                }});

                (async () => {{
                    await loadRegionesCatalog();
                    await loadColaboradores();
                    await loadSucursales();
                    renderFilterTree();
                    render('list');
                }})();
            }})();
        </script>
    """)
    return render_backend_page(
        request,
        title="Sucursales",
        description="Registro y visualización de sucursales.",
        content=sucursales_content,
        hide_floating_actions=True,
        show_page_header=False,
        view_buttons=[
            {"label": "Form", "icon": "/icon/boton/formulario.svg", "view": "form"},
            {"label": "Lista", "icon": "/icon/boton/grid.svg", "view": "list", "active": True},
            {"label": "Kanban", "icon": "/icon/boton/kanban.svg", "view": "kanban"},
            {"label": "Organigrama", "icon": "/icon/boton/organigrama.svg", "view": "organigrama"},
        ],
    )
