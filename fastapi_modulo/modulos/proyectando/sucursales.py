import json
from datetime import datetime
from html import escape
from textwrap import dedent
from typing import Any, Dict, List

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import HTMLResponse

from fastapi_modulo.modulos.proyectando.data_store import (
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
        base_year = int((preliminares.get("primer_anio_proyeccion") or "").strip() or current_year)
    except (TypeError, ValueError):
        base_year = current_year
    try:
        projection_years = int((preliminares.get("anios_proyeccion") or "").strip() or 3)
    except (TypeError, ValueError):
        projection_years = 3
    projection_years = max(1, min(projection_years, 10))
    column_offsets = [-4, -3, -2, -1, 0] + list(range(1, projection_years))

    def _header_label(offset: int) -> str:
        if offset < 0:
            return f"{offset} ({base_year + offset})"
        if offset == 0:
            return f"Año actual ({base_year})"
        return f"+{offset} ({base_year + offset})"

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
                f'<td><input class="suc-result-input" type="number" step="0.01" min="0" '
                f'name="suc_result_{row_idx}_{offset}" placeholder="0.00"></td>'
            )
            for offset in column_offsets
        )
        results_rows.append(
            f"""
            <tr>
                <td class="suc-result-rubro">{escape(rubro)}</td>
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
        <section id="sucursales-module" style="display:grid; gap:14px;">
            <style>
                .suc-tabs {{
                    display:flex;
                    flex-wrap:wrap;
                    gap:10px;
                    border-bottom:1px solid #cbd5e1;
                    padding-bottom:8px;
                }}
                .suc-tab-btn {{
                    display:inline-flex;
                    align-items:center;
                    gap:8px;
                    border:1px solid transparent;
                    border-bottom:3px solid transparent;
                    border-radius:10px;
                    background:transparent;
                    padding:10px 12px;
                    color:#334155;
                    font-weight:700;
                    cursor:pointer;
                }}
                .suc-tab-btn img {{
                    width:18px;
                    height:18px;
                    object-fit:contain;
                }}
                .suc-tab-btn.active {{
                    border-color: var(--sidebar-bottom, #0f172a);
                    border-bottom-color: var(--sidebar-bottom, #0f172a);
                    background: var(--sidebar-text, #ffffff);
                    color: var(--sidebar-bottom, #0f172a);
                }}
                .suc-tab-panel {{
                    display:none;
                }}
                .suc-tab-panel.active {{
                    display:block;
                }}
                .suc-card {{
                    background:#ffffff;
                    border:1px solid #dbe3ef;
                    border-radius:14px;
                    padding:14px;
                }}
                .suc-title {{
                    margin:0 0 10px;
                    font-size:1.02rem;
                    color:#0f172a;
                }}
                .suc-grid {{
                    display:grid;
                    grid-template-columns:repeat(4, minmax(0, 1fr));
                    gap:12px;
                }}
                .suc-field {{
                    display:flex;
                    flex-direction:column;
                    gap:6px;
                }}
                .suc-field label {{
                    font-size:0.85rem;
                    font-weight:700;
                    color:var(--sidebar-bottom, #0f172a);
                }}
                .suc-field input,
                .suc-field select,
                .suc-field textarea {{
                    width:100%;
                    border:1px solid color-mix(in srgb, var(--button-bg, #0f172a) 20%, #ffffff 80%);
                    border-radius:10px;
                    padding:10px;
                    color:var(--navbar-text, #1f172a);
                    background:var(--field-color, #ffffff);
                    font-size:0.95rem;
                }}
                .suc-field textarea {{
                    min-height:82px;
                    resize:vertical;
                }}
                .suc-msg {{
                    font-size:0.88rem;
                    color:#334155;
                }}
                .suc-table {{
                    width:100%;
                    border-collapse:collapse;
                }}
                .suc-table th,
                .suc-table td {{
                    border-bottom:1px solid #e2e8f0;
                    padding:10px;
                    text-align:left;
                    vertical-align:top;
                }}
                .suc-table th {{
                    color:#334155;
                    font-size:0.85rem;
                    text-transform:uppercase;
                    letter-spacing:.04em;
                }}
                .view-list-excel {{
                    width:100%;
                    border-collapse:collapse;
                    border:1px solid rgba(15,23,42,.16);
                    border-radius:12px;
                    overflow:hidden;
                    background:#ffffff;
                }}
                .view-list-excel thead th {{
                    text-align:left;
                    font-size:12px;
                    letter-spacing:.06em;
                    text-transform:uppercase;
                    color:rgba(15,23,42,.82);
                    background:linear-gradient(180deg, rgba(239,246,255,.96), rgba(219,234,254,.90));
                    border:1px solid rgba(15,23,42,.14);
                    padding:10px 12px;
                    white-space:nowrap;
                }}
                .view-list-excel tbody td {{
                    border:1px solid rgba(15,23,42,.10);
                    padding:10px 12px;
                    color:#0f172a;
                    background:#ffffff;
                }}
                .view-list-excel tbody tr:nth-child(even) td {{
                    background:#f3f4f6;
                }}
                .view-list-excel tbody tr:hover td {{
                    background:#e5e7eb;
                }}
                .suc-kanban {{
                    display:grid;
                    grid-template-columns:repeat(3, minmax(0, 1fr));
                    gap:12px;
                }}
                .suc-col {{
                    border:1px solid #dbe3ef;
                    border-radius:12px;
                    background:#f8fafc;
                    padding:10px;
                }}
                .suc-col h4 {{
                    margin:0 0 10px;
                    font-size:0.9rem;
                    color:#0f172a;
                }}
                .suc-item {{
                    border:1px solid #dbe3ef;
                    border-radius:10px;
                    background:#ffffff;
                    padding:10px;
                    margin-bottom:8px;
                    cursor:pointer;
                }}
                .suc-item strong {{
                    color:#0f172a;
                    display:block;
                    margin-bottom:4px;
                }}
                .suc-item p {{
                    margin:0;
                    color:#475569;
                    font-size:0.9rem;
                }}
                .suc-results-wrap {{
                    overflow-x:auto;
                }}
                .suc-results-table {{
                    width:100%;
                    min-width:980px;
                    border-collapse:collapse;
                    border-spacing:0;
                }}
                .suc-results-table thead th {{
                    text-align:left;
                    font-size:13px;
                    letter-spacing:.08em;
                    text-transform:uppercase;
                    color:rgba(15,23,42,.75);
                    background:linear-gradient(180deg, rgba(255,255,255,.92), rgba(255,255,255,.74));
                    border-bottom:1px solid rgba(15,23,42,.10);
                    border-right:1px solid rgba(15,23,42,.10);
                    padding:14px 12px;
                    white-space:nowrap;
                }}
                .suc-results-table thead th:last-child {{
                    border-right:0;
                }}
                .suc-results-table tbody td {{
                    border-bottom:1px solid rgba(15,23,42,.08);
                    border-right:1px solid rgba(15,23,42,.10);
                    background:#ffffff;
                    padding:10px 12px;
                    vertical-align:middle;
                }}
                .suc-results-table tbody td:last-child {{
                    border-right:0;
                }}
                .suc-results-table tbody tr:nth-child(even) td {{
                    background:#ecfdf3;
                }}
                .suc-results-table tbody tr:hover td {{
                    background:#dcfce7;
                }}
                .suc-result-rubro {{
                    font-weight:700;
                    color:#0f172a;
                    white-space:nowrap;
                }}
                .suc-result-input {{
                    width:100%;
                    height:34px;
                    border:1px solid #cbd5e1;
                    border-radius:8px;
                    padding:0 10px;
                    background:#ffffff;
                    color:#0f172a;
                    text-align:right;
                    font-variant-numeric:tabular-nums;
                }}
                .suc-af-toolbar {{
                    display:flex;
                    align-items:center;
                    gap:10px;
                    margin-bottom:10px;
                    flex-wrap:wrap;
                }}
                .suc-af-btn {{
                    height:36px;
                    padding:0 12px;
                    border:1px solid #0f172a;
                    border-radius:8px;
                    background:#0f172a;
                    color:#ffffff;
                    font-weight:600;
                    cursor:pointer;
                }}
                .suc-af-note {{
                    font-size:0.82rem;
                    color:#64748b;
                }}
                .suc-af-input,
                .suc-af-select {{
                    width:100%;
                    height:34px;
                    border:1px solid #cbd5e1;
                    border-radius:8px;
                    padding:0 8px;
                    background:#ffffff;
                    color:#0f172a;
                }}
                .suc-af-input.num {{
                    text-align:right;
                    font-variant-numeric:tabular-nums;
                }}
                @media (max-width: 1100px) {{
                    .suc-grid {{ grid-template-columns:repeat(2, minmax(0, 1fr)); }}
                }}
                @media (max-width: 980px) {{
                    .suc-grid {{ grid-template-columns:1fr; }}
                    .suc-kanban {{ grid-template-columns:1fr; }}
                }}
            </style>
            <div id="sucursales-view"></div>
        </section>
        <script>
            (() => {{
                const mount = document.getElementById('sucursales-view');
                if (!mount) return;
                const data = [];
                const activoFijoCatalog = {activo_fijo_catalog_json};
                const projectionYears = {projection_years};
                const baseYear = {base_year};
                const purchaseYearOptions = Array.from({{ length: projectionYears }}, (_, idx) => baseYear + idx);
                const monthOptions = [
                    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
                ];
                const statusOptions = ["Solicitado", "Autorizado", "Comprado"];
                const activoFijoRowsData = [];
                const regionCatalog = [];
                const regionRowsData = [];
                let currentView = 'list';
                let editingIndex = -1;
                let formTab = 'captura';

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
                    const unique = Array.from(new Set(values)).sort((a, b) => a.localeCompare(b, 'es', {{ sensitivity: 'base' }}));
                    regionCatalog.splice(0, regionCatalog.length, ...unique);
                }};
                const loadSucursales = async () => {{
                    try {{
                        const res = await fetch('/api/inicio/sucursales');
                        const json = await res.json().catch(() => ({{}}));
                        if (!res.ok || json?.success === false) throw new Error('No se pudieron cargar sucursales');
                        replaceData(json?.data || []);
                    }} catch (_error) {{
                        replaceData([]);
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
                        .sort((a, b) => a.localeCompare(b, 'es', {{ sensitivity: 'base' }}))
                        .map((name) => `<option value="${{escapeHtml(name)}}" ${{name === currentRegion ? 'selected' : ''}}>${{escapeHtml(name)}}</option>`)
                        .join('');
                    const isCaptura = formTab === 'captura';
                    const isResultados = formTab === 'resultados';
                    const isActivoFijo = formTab === 'activo-fijo';
                    const isReparaciones = formTab === 'reparaciones';
                    mount.innerHTML = `
                        <article class="suc-card">
                            <h3 class="suc-title">Formulario de sucursales</h3>
                            <div class="suc-tabs" role="tablist" aria-label="Control por sucursal">
                                <button type="button" class="suc-tab-btn ${{isCaptura ? 'active' : ''}}" data-suc-form-tab="captura" aria-selected="${{isCaptura ? 'true' : 'false'}}">Captura</button>
                                <button type="button" class="suc-tab-btn ${{isResultados ? 'active' : ''}}" data-suc-form-tab="resultados" aria-selected="${{isResultados ? 'true' : 'false'}}">
                                    <img src="/templates/icon/resultados.svg" alt="">
                                    Resultados
                                </button>
                                <button type="button" class="suc-tab-btn ${{isActivoFijo ? 'active' : ''}}" data-suc-form-tab="activo-fijo" aria-selected="${{isActivoFijo ? 'true' : 'false'}}">
                                    <img src="/templates/icon/activo_fijo.svg" alt="">
                                    Compras de activo fijo
                                </button>
                                <button type="button" class="suc-tab-btn ${{isReparaciones ? 'active' : ''}}" data-suc-form-tab="reparaciones" aria-selected="${{isReparaciones ? 'true' : 'false'}}">
                                    <img src="/templates/icon/reparaciones.svg" alt="">
                                    Reparaciones
                                </button>
                            </div>
                            <div class="suc-tab-panel ${{isCaptura ? 'active' : ''}}" data-suc-form-panel="captura">
                            <form id="sucursales-form">
                                <div class="suc-grid">
                                    <div class="suc-field">
                                        <label for="sucursal-nombre">Nombre</label>
                                        <input id="sucursal-nombre" type="text" value="${{escapeHtml(current.nombre)}}" required>
                                    </div>
                                    <div class="suc-field">
                                        <label for="sucursal-region-select">Región</label>
                                        <select id="sucursal-region-select" required>
                                            <option value="">Seleccione región</option>
                                            ${{regionOptionsHtml}}
                                            <option value="__new__">+ Agregar región</option>
                                        </select>
                                        <input id="sucursal-region-new" type="text" placeholder="Nueva región" style="display:none; margin-top:6px;">
                                    </div>
                                    <div class="suc-field">
                                        <label for="sucursal-codigo">Código</label>
                                        <input id="sucursal-codigo" type="text" value="${{escapeHtml(current.codigo)}}" required>
                                    </div>
                                    <div class="suc-field">
                                        <label for="sucursal-descripcion">Descripción</label>
                                        <textarea id="sucursal-descripcion">${{escapeHtml(current.descripcion)}}</textarea>
                                    </div>
                                </div>
                                <div class="action-buttons-group">
                                    <button type="button" class="action-button" id="suc-btn-new" data-hover-label="Nuevo" aria-label="Nuevo" title="Nuevo">
                                        <img src="/icon/boton/nuevo.svg" alt="Nuevo">
                                        <span class="action-label">Nuevo</span>
                                    </button>
                                    <button type="button" class="action-button" id="suc-btn-edit" data-hover-label="Editar" aria-label="Editar" title="Editar">
                                        <img src="/icon/boton/editar.svg" alt="Editar">
                                        <span class="action-label">Editar</span>
                                    </button>
                                    <button type="submit" class="action-button" id="suc-btn-save" data-hover-label="Guardar" aria-label="Guardar" title="Guardar">
                                        <img src="/icon/boton/guardar.svg" alt="Guardar">
                                        <span class="action-label">Guardar</span>
                                    </button>
                                    <button type="button" class="action-button" id="suc-btn-delete" data-hover-label="Eliminar" aria-label="Eliminar" title="Eliminar">
                                        <img src="/icon/boton/eliminar.svg" alt="Eliminar">
                                        <span class="action-label">Eliminar</span>
                                    </button>
                                    <span class="suc-msg" id="suc-form-msg">${{data.length}} registro(s)</span>
                                </div>
                            </form>
                            </div>
                            <div class="suc-tab-panel ${{isResultados ? 'active' : ''}}" data-suc-form-panel="resultados">
                                <h3 class="suc-title">Resultados</h3>
                                <div class="suc-results-wrap">
                                    <table class="suc-results-table">
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
                            <div class="suc-tab-panel ${{isActivoFijo ? 'active' : ''}}" data-suc-form-panel="activo-fijo">
                                <h3 class="suc-title">Activo fijo</h3>
                                <div class="suc-af-toolbar">
                                    <button type="button" class="suc-af-btn" id="suc-af-add-btn">Compra de activo fijo</button>
                                    <span class="suc-af-note">Procedimiento de autorización pendiente.</span>
                                </div>
                                <div class="suc-results-wrap">
                                    <table class="suc-results-table">
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
                            <div class="suc-tab-panel ${{isReparaciones ? 'active' : ''}}" data-suc-form-panel="reparaciones">
                                <h3 class="suc-title">Reparaciones</h3>
                                <p class="suc-msg">Aquí se llevará el registro de las solicitudes de reparación de la sucursal.</p>
                                <p class="suc-msg">Lógica y código pendientes.</p>
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
                        regionNewInput.style.display = isNew ? 'block' : 'none';
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
                }};

                const renderList = () => {{
                    mount.innerHTML = `
                        <article class="suc-card">
                            <h3 class="suc-title">Lista de sucursales</h3>
                            <table class="suc-table view-list-excel">
                                <thead>
                                    <tr>
                                        <th>Nombre</th>
                                        <th>Región</th>
                                        <th>Código</th>
                                        <th>Descripción</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${{data.length ? data.map((row) => `
                                        <tr class="suc-open-form-row" data-row-code="${{escapeHtml(row.codigo)}}">
                                            <td>${{escapeHtml(row.nombre)}}</td>
                                            <td>${{escapeHtml(row.region)}}</td>
                                            <td>${{escapeHtml(row.codigo)}}</td>
                                            <td>${{escapeHtml(row.descripcion)}}</td>
                                        </tr>
                                    `).join('') : `
                                        <tr><td colspan="4" style="color:#64748b;">Sin registros.</td></tr>
                                    `}}
                                </tbody>
                            </table>
                        </article>
                    `;
                }};

                const laneName = (region) => {{
                    const key = (region || '').trim();
                    return key || 'Sin región';
                }};

                const renderKanban = () => {{
                    const lanes = {{}};
                    data.forEach((row) => {{
                        const lane = laneName(row.region);
                        if (!lanes[lane]) lanes[lane] = [];
                        lanes[lane].push(row);
                    }});
                    if (!Object.keys(lanes).length) lanes['Sin región'] = [];
                    mount.innerHTML = `
                        <article class="suc-card">
                            <h3 class="suc-title">Kanban de sucursales</h3>
                            <div class="suc-kanban">
                                ${{Object.keys(lanes).map((key) => `
                                    <div class="suc-col">
                                        <h4>${{escapeHtml(key)}}</h4>
                                        ${{lanes[key].length ? lanes[key].map((row) => `
                                            <article class="suc-item" data-row-code="${{escapeHtml(row.codigo)}}">
                                                <strong>${{escapeHtml(row.nombre)}}</strong>
                                                <p>${{escapeHtml(row.codigo)}}</p>
                                                <p>${{escapeHtml(row.descripcion)}}</p>
                                            </article>
                                        `).join('') : '<p class="suc-msg">Sin registros.</p>'}}
                                    </div>
                                `).join('')}}
                            </div>
                        </article>
                    `;
                }};

                const render = (view) => {{
                    currentView = ['form', 'list', 'kanban'].includes(view) ? view : 'form';
                    if (currentView === 'list') return renderList();
                    if (currentView === 'kanban') return renderKanban();
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
                        activoFijoRows.innerHTML = '<tr><td colspan="7" style="color:#64748b;">Sin registros de compras.</td></tr>';
                        return;
                    }}
                    activoFijoRows.innerHTML = activoFijoRowsData.map((row, idx) => `
                        <tr data-af-row="${{idx}}">
                            <td><input class="suc-af-input" type="text" data-field="code" value="${{escapeHtml(row.code)}}" readonly></td>
                            <td><input class="suc-af-input" type="text" data-field="article" value="${{escapeHtml(row.article)}}"></td>
                            <td><select class="suc-af-select" data-field="rubro">${{rubroSelectOptions(row.rubro)}}</select></td>
                            <td><input class="suc-af-input num" type="number" min="0" step="0.01" data-field="price" value="${{escapeHtml(row.price)}}"></td>
                            <td><select class="suc-af-select" data-field="year">${{yearSelectOptions(row.year)}}</select></td>
                            <td><select class="suc-af-select" data-field="month">${{monthSelectOptions(row.month)}}</select></td>
                            <td><select class="suc-af-select" data-field="status">${{statusSelectOptions(row.status)}}</select></td>
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
                        year: purchaseYearOptions[0] || baseYear,
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
                mount.addEventListener('click', (event) => {{
                    const target = event.target;
                    if (!(target instanceof HTMLElement)) return;
                    const listRow = target.closest('.suc-open-form-row');
                    if (listRow instanceof HTMLElement) {{
                        openFormByCode(listRow.getAttribute('data-row-code') || '');
                        return;
                    }}
                    const kanbanCard = target.closest('.suc-item');
                    if (kanbanCard instanceof HTMLElement) {{
                        const codeText = (kanbanCard.getAttribute('data-row-code') || '').trim();
                        openFormByCode(codeText);
                    }}
                }});

                (async () => {{
                    await loadRegionesCatalog();
                    await loadSucursales();
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
        show_page_header=True,
        view_buttons=[
            {"label": "Form", "icon": "/templates/icon/formulario.svg", "view": "form"},
            {"label": "Lista", "icon": "/templates/icon/list.svg", "view": "list", "active": True},
            {"label": "Kanban", "icon": "/templates/icon/kanban.svg", "view": "kanban"},
        ],
    )
