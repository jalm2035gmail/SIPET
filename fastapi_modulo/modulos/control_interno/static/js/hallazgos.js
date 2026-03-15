(function() {

const API = "/api/ci-hallazgo";
const CONTROLES_API = "/api/control-interno";

let _hzSeleccionado = null;  // id del hallazgo cuyo panel de acciones está abierto
let _acciones = [];

/* ── utilidades ─────────────────────────────────────────────────────────── */

function _badgeRiesgo(nivel) {
  const map = {
    "Crítico": "badge-error",
    "Alto":    "badge-error",
    "Medio":   "badge-warning",
    "Bajo":    "badge-ghost",
  };
  return `<span class="badge badge-sm ${map[nivel] || 'badge-ghost'}">${nivel}</span>`;
}

function _badgeEstado(estado) {
  const map = {
    "Abierto":     "badge-error",
    "En atención": "badge-warning",
    "Subsanado":   "badge-info",
    "Cerrado":     "badge-success",
  };
  return `<span class="badge badge-sm ${map[estado] || 'badge-ghost'}">${estado}</span>`;
}

function _badgeEstadoAC(estado) {
  const map = {
    "Pendiente":  "badge-warning",
    "En proceso": "badge-info",
    "Ejecutada":  "badge-success",
    "Verificada": "badge-success",
    "Cancelada":  "badge-ghost",
  };
  return `<span class="badge badge-sm ${map[estado] || 'badge-ghost'}">${estado}</span>`;
}

function _fmtFecha(s) {
  if (!s) return "—";
  const [y, m, d] = s.split("-");
  return `${d}/${m}/${y}`;
}

function _qs(id)  { return document.getElementById(id); }
function _val(id) { return (_qs(id) || {}).value || ""; }

/* ── carga inicial ──────────────────────────────────────────────────────── */

async function _cargarControles() {
  try {
    const r = await fetch(CONTROLES_API);
    if (!r.ok) return;
    const data = await r.json();
    const controles = data.controles || data;
    const sel = _qs("hz-control-id");
    if (!sel) return;
    while (sel.options.length > 1) sel.remove(1);
    controles.forEach(c => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = `${c.codigo || c.id} — ${c.nombre}`;
      sel.appendChild(opt);
    });
  } catch (e) { /* sin controles cargados, no es crítico */ }
}

async function cargar(params = {}) {
  const qs = new URLSearchParams();
  if (params.nivel_riesgo)    qs.set("nivel_riesgo",    params.nivel_riesgo);
  if (params.estado)          qs.set("estado",          params.estado);
  if (params.componente_coso) qs.set("componente_coso", params.componente_coso);
  if (params.q)               qs.set("q",               params.q);

  const tbody = _qs("hz-tbody");
  tbody.innerHTML = `<tr><td colspan="8" class="text-center py-6 text-MAIN-content/50">Cargando…</td></tr>`;

  try {
    const r = await fetch(`${API}?${qs}`);
    if (!r.ok) throw new Error("Error al cargar hallazgos");
    const { hallazgos, resumen } = await r.json();
    _renderTabla(hallazgos);
    _renderKpis(resumen);
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center py-6 text-error">${e.message}</td></tr>`;
  }
}

function _renderKpis(r) {
  const pe = r.por_estado || {};
  const pr = r.por_riesgo || {};
  _qs("hz-kpi-total").textContent    = r.total  || 0;
  _qs("hz-kpi-abiertos").textContent = pe["Abierto"]     || 0;
  _qs("hz-kpi-atencion").textContent = pe["En atención"] || 0;
  _qs("hz-kpi-cerrados").textContent = (pe["Cerrado"] || 0) + (pe["Subsanado"] || 0);
  _qs("hz-kpi-critico").textContent  = pr["Crítico"] || 0;
  _qs("hz-kpi-alto").textContent     = pr["Alto"]    || 0;
  _qs("hz-kpi-medio").textContent    = pr["Medio"]   || 0;
  _qs("hz-kpi-bajo").textContent     = pr["Bajo"]    || 0;
}

function _renderTabla(hallazgos) {
  const tbody = _qs("hz-tbody");
  if (!hallazgos.length) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center py-8 text-MAIN-content/40">Sin hallazgos registrados.</td></tr>`;
    return;
  }
  tbody.innerHTML = hallazgos.map(h => `
    <tr class="hover" data-id="${h.id}">
      <td class="font-mono text-xs">${h.codigo || "—"}</td>
      <td class="max-w-xs">
        <div class="font-medium leading-tight">${h.titulo}</div>
        ${h.control_nombre ? `<div class="text-xs text-MAIN-content/50">${h.control_codigo} ${h.control_nombre}</div>` : ""}
      </td>
      <td class="text-xs">${h.componente_coso || "—"}</td>
      <td>${_badgeRiesgo(h.nivel_riesgo)}</td>
      <td>${_badgeEstado(h.estado)}</td>
      <td class="text-sm">${h.responsable || "—"}</td>
      <td>
        <button class="btn btn-xs btn-outline gap-1 hz-btn-acciones" data-id="${h.id}" title="Ver acciones correctivas">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3 pointer-events-none" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/>
          </svg>
          ${h.total_acciones}
        </button>
      </td>
      <td>
        <div class="flex gap-1">
          <button class="btn btn-xs btn-ghost hz-btn-editar" data-id="${h.id}" title="Editar">✏️</button>
          <button class="btn btn-xs btn-ghost text-error hz-btn-eliminar" data-id="${h.id}" title="Eliminar">🗑️</button>
        </div>
      </td>
    </tr>`).join("");
}

/* ── modal hallazgo ─────────────────────────────────────────────────────── */

function _abrirModal(h = null) {
  const modal = _qs("hz-modal");
  _qs("hz-modal-titulo").textContent = h ? "Editar hallazgo" : "Nuevo hallazgo";
  _qs("hz-id").value                 = h ? h.id       : "";
  _qs("hz-codigo").value             = h ? (h.codigo || "") : "";
  _qs("hz-titulo").value             = h ? h.titulo   : "";
  _qs("hz-descripcion").value        = h ? (h.descripcion || "") : "";
  _qs("hz-causa").value              = h ? (h.causa   || "") : "";
  _qs("hz-efecto").value             = h ? (h.efecto  || "") : "";
  _qs("hz-nivel-riesgo").value       = h ? h.nivel_riesgo : "Medio";
  _qs("hz-estado").value             = h ? h.estado   : "Abierto";
  _qs("hz-responsable").value        = h ? (h.responsable || "") : "";
  _qs("hz-fecha-deteccion").value    = h ? (h.fecha_deteccion || "") : "";
  _qs("hz-fecha-limite").value       = h ? (h.fecha_limite    || "") : "";
  _qs("hz-componente-coso").value    = h ? (h.componente_coso || "") : "";
  _qs("hz-control-id").value         = h ? (h.control_id  || "") : "";
  modal.showModal();
}

_qs("hz-btn-nuevo").addEventListener("click", () => _abrirModal());
_qs("hz-btn-cancelar").addEventListener("click", () => _qs("hz-modal").close());

_qs("hz-form").addEventListener("submit", async e => {
  e.preventDefault();
  const titulo = _val("hz-titulo").trim();
  if (!titulo) { alert("El título es obligatorio."); return; }
  const id = _val("hz-id");
  const payload = {
    codigo:          _val("hz-codigo"),
    titulo,
    descripcion:     _val("hz-descripcion"),
    causa:           _val("hz-causa"),
    efecto:          _val("hz-efecto"),
    componente_coso: _val("hz-componente-coso"),
    nivel_riesgo:    _val("hz-nivel-riesgo"),
    estado:          _val("hz-estado"),
    responsable:     _val("hz-responsable"),
    fecha_deteccion: _val("hz-fecha-deteccion"),
    fecha_limite:    _val("hz-fecha-limite"),
    control_id:      _val("hz-control-id") || null,
  };
  const btn = _qs("hz-btn-guardar");
  btn.disabled = true;
  try {
    const r = await fetch(id ? `${API}/${id}` : API, {
      method:  id ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(payload),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || "Error al guardar.");
    }
    _qs("hz-modal").close();
    cargar(_filtrosActivos());
  } catch (e) {
    alert(e.message);
  } finally {
    btn.disabled = false;
  }
});

/* ── editar/eliminar desde tabla ────────────────────────────────────────── */

_qs("hz-tbody").addEventListener("click", async e => {
  const btn = e.target.closest("button");
  if (!btn) return;
  const id = parseInt(btn.dataset.id);

  if (btn.classList.contains("hz-btn-acciones")) {
    _abrirPanelAcciones(id, btn);
    return;
  }
  if (btn.classList.contains("hz-btn-editar")) {
    try {
      const r  = await fetch(`${API}/${id}`);
      if (!r.ok) throw new Error();
      const h = await r.json();
      _abrirModal(h);
    } catch { alert("No se pudo cargar el hallazgo."); }
    return;
  }
  if (btn.classList.contains("hz-btn-eliminar")) {
    if (!confirm("¿Eliminar este hallazgo y todas sus acciones correctivas?")) return;
    try {
      const r = await fetch(`${API}/${id}`, { method: "DELETE" });
      if (!r.ok) throw new Error();
      if (_hzSeleccionado === id) _cerrarPanel();
      cargar(_filtrosActivos());
    } catch { alert("No se pudo eliminar el hallazgo."); }
  }
});

/* ── filtros ────────────────────────────────────────────────────────────── */

function _filtrosActivos() {
  return {
    nivel_riesgo:    _val("hz-filtro-riesgo"),
    estado:          _val("hz-filtro-estado"),
    componente_coso: _val("hz-filtro-coso"),
    q:               _val("hz-filtro-q"),
  };
}

_qs("hz-btn-filtrar").addEventListener("click", () => cargar(_filtrosActivos()));
_qs("hz-btn-limpiar").addEventListener("click", () => {
  ["hz-filtro-riesgo","hz-filtro-estado","hz-filtro-coso","hz-filtro-q"]
    .forEach(id => { const el = _qs(id); if (el) el.value = ""; });
  cargar();
});
_qs("hz-filtro-q").addEventListener("keydown", e => {
  if (e.key === "Enter") cargar(_filtrosActivos());
});

/* ── panel acciones correctivas ─────────────────────────────────────────── */

async function _abrirPanelAcciones(hallazgoId, triggerBtn) {
  _hzSeleccionado = hallazgoId;
  const panel = _qs("hz-panel-acciones");
  panel.classList.remove("hidden");

  // Resaltar fila seleccionada
  document.querySelectorAll("#hz-tbody tr").forEach(tr => tr.classList.remove("bg-primary/10"));
  const fila = triggerBtn?.closest("tr");
  if (fila) fila.classList.add("bg-primary/10");

  const titulo = fila?.querySelector("td:nth-child(2) div")?.textContent || `Hallazgo #${hallazgoId}`;
  _qs("hz-ac-titulo-panel").textContent = "Acciones correctivas";
  _qs("hz-ac-subtitulo").textContent    = titulo;

  await _cargarAcciones(hallazgoId);
  panel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function _cerrarPanel() {
  _hzSeleccionado = null;
  _qs("hz-panel-acciones").classList.add("hidden");
  document.querySelectorAll("#hz-tbody tr").forEach(tr => tr.classList.remove("bg-primary/10"));
}

_qs("hz-btn-cerrar-panel").addEventListener("click", _cerrarPanel);

async function _cargarAcciones(hallazgoId) {
  const tbody = _qs("hz-ac-tbody");
  tbody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-MAIN-content/50">Cargando…</td></tr>`;
  try {
    const r = await fetch(`${API}/${hallazgoId}/acciones`);
    if (!r.ok) throw new Error();
    _acciones = await r.json();
    _renderAcciones(_acciones);
  } catch {
    tbody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-error">Error al cargar acciones.</td></tr>`;
  }
}

function _renderAcciones(acciones) {
  const tbody = _qs("hz-ac-tbody");
  if (!acciones.length) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-MAIN-content/40">Sin acciones registradas.</td></tr>`;
    return;
  }
  tbody.innerHTML = acciones.map(a => `
    <tr class="hover">
      <td class="max-w-xs text-sm">${a.descripcion}</td>
      <td class="text-xs">${a.responsable || "—"}</td>
      <td class="text-xs">${_fmtFecha(a.fecha_compromiso)}</td>
      <td>${_badgeEstadoAC(a.estado)}</td>
      <td>
        <div class="flex gap-1">
          <button class="btn btn-xs btn-ghost hz-ac-btn-editar" data-id="${a.id}" title="Editar">✏️</button>
          <button class="btn btn-xs btn-ghost text-error hz-ac-btn-eliminar" data-id="${a.id}" title="Eliminar">🗑️</button>
        </div>
      </td>
    </tr>`).join("");
}

/* ── modal acción correctiva ────────────────────────────────────────────── */

function _abrirModalAC(a = null) {
  const modal = _qs("hz-ac-modal");
  _qs("hz-ac-modal-titulo").textContent     = a ? "Editar acción correctiva" : "Nueva acción correctiva";
  _qs("hz-ac-id").value                     = a ? a.id          : "";
  _qs("hz-ac-hallazgo-id").value            = _hzSeleccionado   || "";
  _qs("hz-ac-descripcion").value            = a ? a.descripcion : "";
  _qs("hz-ac-responsable").value            = a ? (a.responsable || "") : "";
  _qs("hz-ac-estado").value                 = a ? a.estado      : "Pendiente";
  _qs("hz-ac-fecha-compromiso").value       = a ? (a.fecha_compromiso || "") : "";
  _qs("hz-ac-fecha-ejecucion").value        = a ? (a.fecha_ejecucion  || "") : "";
  _qs("hz-ac-evidencia-seguimiento").value  = a ? (a.evidencia_seguimiento || "") : "";
  modal.showModal();
}

_qs("hz-btn-nueva-accion").addEventListener("click",    () => _abrirModalAC());
_qs("hz-ac-btn-cancelar").addEventListener("click",     () => _qs("hz-ac-modal").close());

_qs("hz-ac-tbody").addEventListener("click", async e => {
  const btn = e.target.closest("button");
  if (!btn) return;
  const id  = parseInt(btn.dataset.id);
  const a   = _acciones.find(x => x.id === id);

  if (btn.classList.contains("hz-ac-btn-editar")) {
    if (a) _abrirModalAC(a);
    return;
  }
  if (btn.classList.contains("hz-ac-btn-eliminar")) {
    if (!confirm("¿Eliminar esta acción correctiva?")) return;
    try {
      const r = await fetch(`${API}/${_hzSeleccionado}/acciones/${id}`, { method: "DELETE" });
      if (!r.ok) throw new Error();
      await _cargarAcciones(_hzSeleccionado);
      cargar(_filtrosActivos()); // actualiza contador
    } catch { alert("No se pudo eliminar la acción."); }
  }
});

_qs("hz-ac-form").addEventListener("submit", async e => {
  e.preventDefault();
  const desc = _val("hz-ac-descripcion").trim();
  if (!desc) { alert("La descripción es obligatoria."); return; }
  const id         = _val("hz-ac-id");
  const hallazgoId = _val("hz-ac-hallazgo-id") || _hzSeleccionado;
  const payload = {
    descripcion:            desc,
    responsable:            _val("hz-ac-responsable"),
    estado:                 _val("hz-ac-estado"),
    fecha_compromiso:       _val("hz-ac-fecha-compromiso"),
    fecha_ejecucion:        _val("hz-ac-fecha-ejecucion"),
    evidencia_seguimiento:  _val("hz-ac-evidencia-seguimiento"),
  };
  const btn = _qs("hz-ac-btn-guardar");
  btn.disabled = true;
  try {
    const url = id
      ? `${API}/${hallazgoId}/acciones/${id}`
      : `${API}/${hallazgoId}/acciones`;
    const r = await fetch(url, {
      method:  id ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(payload),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({}));
      throw new Error(err.detail || "Error al guardar acción.");
    }
    _qs("hz-ac-modal").close();
    await _cargarAcciones(_hzSeleccionado);
    cargar(_filtrosActivos());
  } catch (err) {
    alert(err.message);
  } finally {
    btn.disabled = false;
  }
});

/* ── inicialización ─────────────────────────────────────────────────────── */

_cargarControles();
cargar();

})();
