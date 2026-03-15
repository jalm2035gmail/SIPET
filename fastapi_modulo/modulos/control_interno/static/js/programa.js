(function () {
  'use strict';

  // ─── Estado global ──────────────────────────────────────────────
  let programas    = [];
  let actividades  = [];
  let controles    = [];     // catálogo de fase 1
  let activoProgramaId = null;
  let editingProgId    = null;
  let editingActId     = null;
  let deleteTarget     = null;  // {tipo:'prog'|'act', id, nombre}

  // ─── Refs ────────────────────────────────────────────────────────
  const listaProgramas  = document.getElementById('pa-lista-programas');
  const listaEmpty      = document.getElementById('pa-lista-empty');
  const placeholder     = document.getElementById('pa-placeholder');
  const programaActivo  = document.getElementById('pa-programa-activo');
  const tablaTitulo     = document.getElementById('pa-tabla-titulo');
  const tbody           = document.getElementById('pa-tbody');
  const totalAct        = document.getElementById('pa-total-act');
  const toast           = document.getElementById('pa-toast');
  const toastInner      = document.getElementById('pa-toast-inner');
  const modalProg       = document.getElementById('pa-modal-prog');
  const modalAct        = document.getElementById('pa-modal-act');
  const modalDelete     = document.getElementById('pa-modal-delete');
  const deleteNombreEl  = document.getElementById('pa-delete-nombre');
  const progress        = document.getElementById('pa-progress');
  const pctLabel        = document.getElementById('pa-pct-label');

  // ─── Toast ────────────────────────────────────────────────────────
  let toastTimer;
  function showToast(msg, isError) {
    toastInner.className = 'alert shadow-lg max-w-xs text-sm ' +
      (isError ? 'alert-error' : 'alert-success');
    toastInner.textContent = msg;
    toast.style.display = 'block';
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { toast.style.display = 'none'; }, 3500);
  }

  function esc(s) {
    return String(s || '')
      .replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // ─── Badges ───────────────────────────────────────────────────────
  const PROG_BADGE = {
    'Borrador':      'badge-ghost',
    'Aprobado':      'badge-info',
    'En ejecución':  'badge-primary',
    'Cerrado':       'badge-neutral',
  };
  const ACT_BADGE = {
    'Programado':  'badge-warning',
    'En proceso':  'badge-info',
    'Completado':  'badge-success',
    'Diferido':    'badge-error',
    'Cancelado':   'badge-neutral',
  };

  // ═══════════════ CATÁLOGO ════════════════════════════════════════
  async function cargarCatalogo() {
    try {
      const res = await fetch('/api/control-interno', {credentials:'same-origin'});
      const data = await res.json();
      controles = data.controles || [];
      const sel = document.getElementById('pa-f-control_id');
      sel.innerHTML = '<option value="">— Sin vincular —</option>';
      controles.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.id;
        opt.textContent = `[${c.codigo}] ${c.nombre}`;
        sel.appendChild(opt);
      });
    } catch (_) {}
  }

  // ═══════════════ PROGRAMAS ═══════════════════════════════════════
  async function cargarProgramas() {
    try {
      const res = await fetch('/api/ci-programa', {credentials:'same-origin'});
      const data = await res.json();
      programas = data.programas || [];
      renderListaProgramas();
    } catch (_) { showToast('Error al cargar programas.', true); }
  }

  function renderListaProgramas() {
    if (!programas.length) {
      listaProgramas.innerHTML = '';
      listaProgramas.appendChild(listaEmpty);
      listaEmpty.style.display = 'block';
      return;
    }
    listaEmpty.style.display = 'none';
    listaProgramas.innerHTML = programas.map(p => {
      const active = p.id === activoProgramaId ? 'bg-primary/10 font-semibold' : 'hover:bg-MAIN-200';
      const badge = PROG_BADGE[p.estado] || 'badge-ghost';
      return `<li>
        <button onclick="paSelectPrograma(${p.id})"
                class="w-full text-left px-4 py-3 ${active} transition-colors flex items-center justify-between gap-2">
          <span class="flex flex-col gap-0.5">
            <span class="text-sm leading-tight">${esc(p.nombre)}</span>
            <span class="text-xs text-MAIN-content/50">${p.anio}</span>
          </span>
          <span class="badge badge-sm ${badge} shrink-0">${esc(p.estado)}</span>
        </button>
      </li>`;
    }).join('');
  }

  window.paSelectPrograma = function(id) {
    activoProgramaId = id;
    renderListaProgramas();
    placeholder.style.display = 'none';
    programaActivo.style.display = 'grid';
    const prog = programas.find(p => p.id === id);
    if (prog) tablaTitulo.textContent = `Actividades — ${prog.nombre} (${prog.anio})`;
    cargarActividades();
  };

  // ─── Nuevo programa ────────────────────────────────────────────
  document.getElementById('pa-btn-nuevo-programa').addEventListener('click', () => {
    editingProgId = null;
    document.getElementById('pa-modal-prog-titulo').textContent = 'Nuevo programa';
    document.getElementById('pa-f-anio').value = new Date().getFullYear();
    document.getElementById('pa-f-nombre').value = '';
    document.getElementById('pa-f-descripcion').value = '';
    document.getElementById('pa-f-estado').value = 'Borrador';
    document.getElementById('pa-prog-error').style.display = 'none';
    modalProg.showModal();
  });

  // ─── Editar programa ───────────────────────────────────────────
  document.getElementById('pa-btn-editar-programa').addEventListener('click', () => {
    const prog = programas.find(p => p.id === activoProgramaId);
    if (!prog) return;
    editingProgId = prog.id;
    document.getElementById('pa-modal-prog-titulo').textContent = 'Editar programa';
    document.getElementById('pa-f-anio').value = prog.anio;
    document.getElementById('pa-f-nombre').value = prog.nombre;
    document.getElementById('pa-f-descripcion').value = prog.descripcion;
    document.getElementById('pa-f-estado').value = prog.estado;
    document.getElementById('pa-prog-error').style.display = 'none';
    modalProg.showModal();
  });

  document.getElementById('pa-btn-cancel-prog').addEventListener('click', () => modalProg.close());

  document.getElementById('pa-btn-save-prog').addEventListener('click', async () => {
    const errEl   = document.getElementById('pa-prog-error');
    const spinner = document.getElementById('pa-prog-spinner');
    errEl.style.display = 'none';
    const anio   = document.getElementById('pa-f-anio').value.trim();
    const nombre = document.getElementById('pa-f-nombre').value.trim();
    if (!anio)   { errEl.textContent = 'El año es obligatorio.'; errEl.style.display='flex'; return; }
    if (!nombre) { errEl.textContent = 'El nombre es obligatorio.'; errEl.style.display='flex'; return; }
    spinner.style.display = 'inline-block';
    try {
      const payload = {
        anio:        parseInt(anio),
        nombre,
        descripcion: document.getElementById('pa-f-descripcion').value.trim(),
        estado:      document.getElementById('pa-f-estado').value,
      };
      const url    = editingProgId ? '/api/ci-programa/' + editingProgId : '/api/ci-programa';
      const method = editingProgId ? 'PUT' : 'POST';
      const res    = await fetch(url, {
        method, credentials: 'same-origin',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error.');
      modalProg.close();
      showToast(editingProgId ? 'Programa actualizado.' : 'Programa creado.');
      await cargarProgramas();
      if (!editingProgId) paSelectPrograma(data.id);
    } catch (e) {
      errEl.textContent = e.message; errEl.style.display = 'flex';
    } finally { spinner.style.display = 'none'; }
  });

  // ═══════════════ ACTIVIDADES ═════════════════════════════════════
  async function cargarActividades() {
    if (!activoProgramaId) return;
    try {
      const estado = document.getElementById('pa-filtro-estado').value;
      const qs = estado ? '?estado=' + encodeURIComponent(estado) : '';
      const res = await fetch(`/api/ci-programa/${activoProgramaId}/actividades${qs}`,
                              {credentials:'same-origin'});
      const data = await res.json();
      actividades = data.actividades || [];
      renderTablaActividades();
      actualizarKPIs(data.resumen || {});
    } catch (_) { showToast('Error al cargar actividades.', true); }
  }

  function renderTablaActividades() {
    totalAct.textContent = actividades.length;
    if (!actividades.length) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center py-8 text-MAIN-content/40">
        Sin actividades. Usa <b>Agregar actividad</b>.</td></tr>`;
      return;
    }
    tbody.innerHTML = actividades.map(a => {
      const badge = ACT_BADGE[a.estado] || 'badge-ghost';
      const ctrl = a.control_codigo ? `<span class="font-mono text-xs">${esc(a.control_codigo)}</span>` : '—';
      return `<tr>
        <td class="hidden md:table-cell">${ctrl}</td>
        <td>
          <div class="font-medium text-sm leading-tight">${esc(a.descripcion || '—')}</div>
          ${a.responsable ? `<div class="text-xs text-MAIN-content/50">${esc(a.responsable)}</div>` : ''}
        </td>
        <td class="hidden lg:table-cell text-xs">${fmtFecha(a.fecha_inicio_programada)}</td>
        <td class="hidden lg:table-cell text-xs">${fmtFecha(a.fecha_fin_programada)}</td>
        <td><span class="badge badge-sm ${badge}">${esc(a.estado)}</span></td>
        <td class="text-right">
          <button class="btn btn-ghost btn-xs" title="Editar" onclick="paEditAct(${a.id})">✏️</button>
          <button class="btn btn-ghost btn-xs text-error" title="Eliminar"
                  onclick="paDeleteActPrompt(${a.id}, '${esc(a.descripcion || 'actividad').replace(/'/g,"&#39;")}')">🗑️</button>
        </td>
      </tr>`;
    }).join('');
  }

  function fmtFecha(iso) {
    if (!iso) return '—';
    const [y,m,d] = iso.split('-');
    return `${d}/${m}/${y}`;
  }

  function actualizarKPIs(resumen) {
    const c = resumen.conteo || {};
    document.getElementById('pa-kpi-total').textContent      = resumen.total || 0;
    document.getElementById('pa-kpi-completado').textContent = c['Completado'] || 0;
    document.getElementById('pa-kpi-enproceso').textContent  = c['En proceso']  || 0;
    document.getElementById('pa-kpi-programado').textContent = c['Programado'] || 0;
    document.getElementById('pa-kpi-diferido').textContent   = (c['Diferido'] || 0) + (c['Cancelado'] || 0);
    const pct = resumen.porcentaje || 0;
    progress.value    = pct;
    pctLabel.textContent = pct + '%';
  }

  // ─── Filtros actividades ───────────────────────────────────────
  document.getElementById('pa-btn-filtrar').addEventListener('click', cargarActividades);
  document.getElementById('pa-btn-limpiar-filtro').addEventListener('click', () => {
    document.getElementById('pa-filtro-estado').value = '';
    cargarActividades();
  });

  // ─── Nueva actividad ───────────────────────────────────────────
  document.getElementById('pa-btn-nueva-actividad').addEventListener('click', () => {
    editingActId = null;
    document.getElementById('pa-modal-act-titulo').textContent = 'Nueva actividad';
    ['control_id','descripcion','responsable',
     'fecha_inicio_programada','fecha_fin_programada',
     'fecha_inicio_real','fecha_fin_real','observaciones'].forEach(f => {
       const el = document.getElementById('pa-f-' + f);
       if (el) el.value = '';
     });
    document.getElementById('pa-f-estado').value = 'Programado';
    document.getElementById('pa-act-error').style.display = 'none';
    modalAct.showModal();
  });

  window.paEditAct = function(id) {
    const a = actividades.find(x => x.id === id);
    if (!a) return;
    editingActId = id;
    document.getElementById('pa-modal-act-titulo').textContent = 'Editar actividad';
    document.getElementById('pa-f-control_id').value = a.control_id || '';
    document.getElementById('pa-f-descripcion').value = a.descripcion;
    document.getElementById('pa-f-responsable').value = a.responsable;
    document.getElementById('pa-f-fecha_inicio_programada').value = a.fecha_inicio_programada;
    document.getElementById('pa-f-fecha_fin_programada').value = a.fecha_fin_programada;
    document.getElementById('pa-f-fecha_inicio_real').value = a.fecha_inicio_real;
    document.getElementById('pa-f-fecha_fin_real').value = a.fecha_fin_real;
    document.getElementById('pa-f-estado').value = a.estado;
    document.getElementById('pa-f-observaciones').value = a.observaciones;
    document.getElementById('pa-act-error').style.display = 'none';
    modalAct.showModal();
  };

  document.getElementById('pa-btn-cancel-act').addEventListener('click', () => modalAct.close());

  document.getElementById('pa-btn-save-act').addEventListener('click', async () => {
    const errEl   = document.getElementById('pa-act-error');
    const spinner = document.getElementById('pa-act-spinner');
    errEl.style.display = 'none';
    spinner.style.display = 'inline-block';
    try {
      const payload = {
        control_id:              document.getElementById('pa-f-control_id').value || null,
        descripcion:             document.getElementById('pa-f-descripcion').value.trim(),
        responsable:             document.getElementById('pa-f-responsable').value.trim(),
        fecha_inicio_programada: document.getElementById('pa-f-fecha_inicio_programada').value || null,
        fecha_fin_programada:    document.getElementById('pa-f-fecha_fin_programada').value || null,
        fecha_inicio_real:       document.getElementById('pa-f-fecha_inicio_real').value || null,
        fecha_fin_real:          document.getElementById('pa-f-fecha_fin_real').value || null,
        estado:                  document.getElementById('pa-f-estado').value,
        observaciones:           document.getElementById('pa-f-observaciones').value.trim(),
      };
      const url    = editingActId
        ? `/api/ci-programa/${activoProgramaId}/actividades/${editingActId}`
        : `/api/ci-programa/${activoProgramaId}/actividades`;
      const method = editingActId ? 'PUT' : 'POST';
      const res    = await fetch(url, {
        method, credentials: 'same-origin',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Error.');
      modalAct.close();
      showToast(editingActId ? 'Actividad actualizada.' : 'Actividad registrada.');
      cargarActividades();
    } catch (e) {
      errEl.textContent = e.message; errEl.style.display = 'flex';
    } finally { spinner.style.display = 'none'; }
  });

  // ─── Eliminar ─────────────────────────────────────────────────
  window.paDeleteActPrompt = function(id, nombre) {
    deleteTarget = {tipo:'act', id, nombre};
    deleteNombreEl.textContent = nombre;
    modalDelete.showModal();
  };

  document.getElementById('pa-btn-confirmar-delete').addEventListener('click', async () => {
    if (!deleteTarget) return;
    modalDelete.close();
    const {tipo, id} = deleteTarget;
    try {
      let url = tipo === 'prog'
        ? `/api/ci-programa/${id}`
        : `/api/ci-programa/${activoProgramaId}/actividades/${id}`;
      const res = await fetch(url, {method:'DELETE', credentials:'same-origin'});
      if (!res.ok) throw new Error();
      showToast('Eliminado correctamente.');
      if (tipo === 'prog') {
        activoProgramaId = null;
        placeholder.style.display = '';
        programaActivo.style.display = 'none';
        cargarProgramas();
      } else {
        cargarActividades();
      }
    } catch { showToast('No se pudo eliminar.', true); }
  });

  // ─── Init ─────────────────────────────────────────────────────
  cargarCatalogo();
  cargarProgramas();
})();
