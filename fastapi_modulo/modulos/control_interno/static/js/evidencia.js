(function () {
  'use strict';

  // ─── Estado ──────────────────────────────────────────────────────
  let evidencias  = [];
  let controles   = [];
  let actividades = [];
  let editingId   = null;
  let deleteId    = null;

  // ─── Refs ─────────────────────────────────────────────────────────
  const tbody       = document.getElementById('ev-tbody');
  const totalEl     = document.getElementById('ev-total');
  const modal       = document.getElementById('ev-modal');
  const modalDelete = document.getElementById('ev-modal-delete');
  const modalTitulo = document.getElementById('ev-modal-titulo');
  const formError   = document.getElementById('ev-form-error');
  const spinner     = document.getElementById('ev-spinner');
  const uploadProg  = document.getElementById('ev-upload-progress');
  const toast       = document.getElementById('ev-toast');
  const toastInner  = document.getElementById('ev-toast-inner');
  const archActual  = document.getElementById('ev-archivo-actual');

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
  const RES_BADGE = {
    'Cumple':               'badge-success',
    'Cumple parcialmente':  'badge-warning',
    'No cumple':            'badge-error',
    'Por evaluar':          'badge-ghost',
  };

  // ─── Formatear tamaño ─────────────────────────────────────────────
  function fmtSize(bytes) {
    if (!bytes) return '';
    if (bytes < 1024)       return bytes + ' B';
    if (bytes < 1048576)    return (bytes/1024).toFixed(1) + ' KB';
    return (bytes/1048576).toFixed(1) + ' MB';
  }

  function fmtFecha(iso) {
    if (!iso) return '—';
    const [y,m,d] = iso.split('-');
    return `${d}/${m}/${y}`;
  }

  // ─── Cargar catálogo y actividades ────────────────────────────────
  async function cargarCatalogo() {
    try {
      const res = await fetch('/api/control-interno', {credentials:'same-origin'});
      const data = await res.json();
      controles = data.controles || [];
      const sel1 = document.getElementById('ev-f-control_id');
      const sel2 = document.getElementById('ev-filtro-control');
      [sel1, sel2].forEach(sel => {
        // keep first option
        while (sel.options.length > 1) sel.remove(1);
        controles.forEach(c => {
          const opt = document.createElement('option');
          opt.value = c.id;
          opt.textContent = `[${c.codigo}] ${c.nombre}`;
          sel.appendChild(opt);
        });
      });
    } catch (_) {}
  }

  async function cargarActividades() {
    try {
      // Load all programs and their activities for the selector
      const rp = await fetch('/api/ci-programa', {credentials:'same-origin'});
      const dp = await rp.json();
      const programas = dp.programas || [];
      const sel = document.getElementById('ev-f-actividad_id');
      while (sel.options.length > 1) sel.remove(1);
      actividades = [];
      for (const p of programas) {
        const ra = await fetch(`/api/ci-programa/${p.id}/actividades`, {credentials:'same-origin'});
        const da = await ra.json();
        const acts = da.actividades || [];
        if (!acts.length) continue;
        const grp = document.createElement('optgroup');
        grp.label = `${p.anio} — ${p.nombre}`;
        acts.forEach(a => {
          actividades.push(a);
          const opt = document.createElement('option');
          opt.value = a.id;
          opt.textContent = (a.descripcion || `Actividad #${a.id}`).substring(0, 60);
          grp.appendChild(opt);
        });
        sel.appendChild(grp);
      }
    } catch (_) {}
  }

  // ─── Cargar evidencias ────────────────────────────────────────────
  async function cargar(params) {
    try {
      const qs = new URLSearchParams(params || {}).toString();
      const res = await fetch('/api/ci-evidencia?' + qs, {credentials:'same-origin'});
      const data = await res.json();
      evidencias = data.evidencias || [];
      renderTabla(evidencias);
      actualizarKPIs(data.resumen || {});
    } catch (_) { showToast('Error al cargar evidencias.', true); }
  }

  function getFiltros() {
    const params = {};
    const tipo   = document.getElementById('ev-filtro-tipo').value;
    const res    = document.getElementById('ev-filtro-resultado').value;
    const ctrl   = document.getElementById('ev-filtro-control').value;
    const q      = document.getElementById('ev-busqueda').value.trim();
    if (tipo) params.tipo = tipo;
    if (res)  params.resultado_evaluacion = res;
    if (ctrl) params.control_id = ctrl;
    if (q)    params.q = q;
    return params;
  }

  document.getElementById('ev-btn-filtrar').addEventListener('click', () => cargar(getFiltros()));
  document.getElementById('ev-btn-limpiar').addEventListener('click', () => {
    document.getElementById('ev-filtro-tipo').value = '';
    document.getElementById('ev-filtro-resultado').value = '';
    document.getElementById('ev-filtro-control').value = '';
    document.getElementById('ev-busqueda').value = '';
    cargar();
  });

  // ─── Render tabla ─────────────────────────────────────────────────
  function renderTabla(lista) {
    totalEl.textContent = lista.length + ' registro' + (lista.length !== 1 ? 's' : '');
    if (!lista.length) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center py-10 text-MAIN-content/40">
        Sin resultados para los filtros aplicados.</td></tr>`;
      return;
    }
    tbody.innerHTML = lista.map(e => {
      const badge   = RES_BADGE[e.resultado_evaluacion] || 'badge-ghost';
      const archivo = e.tiene_archivo
        ? `<a href="/api/ci-evidencia/${e.id}/descargar" target="_blank"
              class="btn btn-ghost btn-xs" title="${esc(e.archivo_nombre)}">📎</a>`
        : '<span class="text-MAIN-content/30 text-xs">—</span>';
      const ctrl = e.control_codigo
        ? `<span class="font-mono text-xs">${esc(e.control_codigo)}</span>`
        : (e.actividad_desc ? `<span class="text-xs text-MAIN-content/50">${esc(e.actividad_desc.substring(0,40))}</span>` : '—');
      return `<tr>
        <td class="font-medium text-sm leading-tight max-w-[200px] truncate">${esc(e.titulo)}</td>
        <td class="hidden md:table-cell"><span class="badge badge-sm badge-outline">${esc(e.tipo)}</span></td>
        <td class="hidden md:table-cell">${ctrl}</td>
        <td class="hidden lg:table-cell text-xs">${fmtFecha(e.fecha_evidencia)}</td>
        <td><span class="badge badge-sm ${badge}">${esc(e.resultado_evaluacion)}</span></td>
        <td class="hidden lg:table-cell text-center">${archivo}</td>
        <td class="text-right whitespace-nowrap">
          <button class="btn btn-ghost btn-xs" title="Editar" onclick="evEdit(${e.id})">✏️</button>
          <button class="btn btn-ghost btn-xs text-error" title="Eliminar"
                  onclick="evDeletePrompt(${e.id}, '${esc(e.titulo).replace(/'/g,"&#39;")}')">🗑️</button>
        </td>
      </tr>`;
    }).join('');
  }

  // ─── KPIs ─────────────────────────────────────────────────────────
  function actualizarKPIs(resumen) {
    const c = resumen.conteo || {};
    document.getElementById('ev-kpi-total').textContent    = resumen.total || 0;
    document.getElementById('ev-kpi-cumple').textContent   = c['Cumple'] || 0;
    document.getElementById('ev-kpi-parcial').textContent  = c['Cumple parcialmente'] || 0;
    document.getElementById('ev-kpi-nocumple').textContent = c['No cumple'] || 0;
  }

  // ─── Abrir modal nuevo ────────────────────────────────────────────
  document.getElementById('ev-btn-nueva').addEventListener('click', () => {
    editingId = null;
    modalTitulo.textContent = 'Nueva evidencia';
    resetForm();
    formError.style.display = 'none';
    modal.showModal();
  });

  function resetForm() {
    document.getElementById('ev-f-titulo').value = '';
    document.getElementById('ev-f-tipo').value = 'Documento';
    document.getElementById('ev-f-fecha_evidencia').value = '';
    document.getElementById('ev-f-control_id').value = '';
    document.getElementById('ev-f-actividad_id').value = '';
    document.getElementById('ev-f-resultado_evaluacion').value = 'Por evaluar';
    document.getElementById('ev-f-descripcion').value = '';
    document.getElementById('ev-f-observaciones').value = '';
    document.getElementById('ev-f-archivo').value = '';
    archActual.style.display = 'none';
    archActual.textContent = '';
  }

  // ─── Editar ───────────────────────────────────────────────────────
  window.evEdit = function(id) {
    const e = evidencias.find(x => x.id === id);
    if (!e) return;
    editingId = id;
    modalTitulo.textContent = 'Editar evidencia';
    document.getElementById('ev-f-titulo').value               = e.titulo;
    document.getElementById('ev-f-tipo').value                 = e.tipo;
    document.getElementById('ev-f-fecha_evidencia').value       = e.fecha_evidencia;
    document.getElementById('ev-f-control_id').value           = e.control_id || '';
    document.getElementById('ev-f-actividad_id').value         = e.actividad_id || '';
    document.getElementById('ev-f-resultado_evaluacion').value = e.resultado_evaluacion;
    document.getElementById('ev-f-descripcion').value          = e.descripcion;
    document.getElementById('ev-f-observaciones').value        = e.observaciones;
    document.getElementById('ev-f-archivo').value              = '';
    if (e.tiene_archivo && e.archivo_nombre) {
      archActual.textContent = `Archivo actual: ${e.archivo_nombre} (${fmtSize(e.archivo_tamanio)})`;
      archActual.style.display = 'block';
    } else {
      archActual.style.display = 'none';
    }
    formError.style.display = 'none';
    modal.showModal();
  };

  document.getElementById('ev-btn-cancelar').addEventListener('click', () => modal.close());

  // ─── Guardar (multipart por el archivo) ───────────────────────────
  document.getElementById('ev-btn-guardar').addEventListener('click', async () => {
    formError.style.display = 'none';
    const titulo = document.getElementById('ev-f-titulo').value.trim();
    const tipo   = document.getElementById('ev-f-tipo').value;
    const res    = document.getElementById('ev-f-resultado_evaluacion').value;
    if (!titulo) { showFormError('El título es obligatorio.'); return; }
    if (!tipo)   { showFormError('El tipo es obligatorio.'); return; }

    spinner.style.display = 'inline-block';
    uploadProg.style.display = 'none';

    const formData = new FormData();
    formData.append('titulo',               titulo);
    formData.append('tipo',                 tipo);
    formData.append('fecha_evidencia',      document.getElementById('ev-f-fecha_evidencia').value);
    formData.append('control_id',           document.getElementById('ev-f-control_id').value);
    formData.append('actividad_id',         document.getElementById('ev-f-actividad_id').value);
    formData.append('resultado_evaluacion', res);
    formData.append('descripcion',          document.getElementById('ev-f-descripcion').value.trim());
    formData.append('observaciones',        document.getElementById('ev-f-observaciones').value.trim());

    const fileInput = document.getElementById('ev-f-archivo');
    if (fileInput.files.length > 0) {
      formData.append('archivo', fileInput.files[0]);
      uploadProg.style.display = 'block';
    }

    try {
      const url    = editingId ? '/api/ci-evidencia/' + editingId : '/api/ci-evidencia';
      const method = editingId ? 'PUT' : 'POST';
      const res2   = await fetch(url, {
        method,
        credentials: 'same-origin',
        body: formData,
      });
      const data = await res2.json();
      if (!res2.ok) throw new Error(data.detail || 'Error al guardar.');
      modal.close();
      showToast(editingId ? 'Evidencia actualizada.' : 'Evidencia registrada.');
      cargar(getFiltros());
    } catch (e) {
      showFormError(e.message);
    } finally {
      spinner.style.display = 'none';
      uploadProg.style.display = 'none';
    }
  });

  function showFormError(msg) {
    formError.textContent = msg;
    formError.style.display = 'flex';
  }

  // ─── Eliminar ─────────────────────────────────────────────────────
  window.evDeletePrompt = function(id, nombre) {
    deleteId = id;
    document.getElementById('ev-delete-nombre').textContent = nombre;
    modalDelete.showModal();
  };

  document.getElementById('ev-btn-confirmar-delete').addEventListener('click', async () => {
    if (!deleteId) return;
    modalDelete.close();
    try {
      const res = await fetch('/api/ci-evidencia/' + deleteId,
                              {method:'DELETE', credentials:'same-origin'});
      if (!res.ok) throw new Error();
      showToast('Evidencia eliminada.');
      cargar(getFiltros());
    } catch { showToast('No se pudo eliminar.', true); }
  });

  // ─── Init ─────────────────────────────────────────────────────────
  Promise.all([cargarCatalogo(), cargarActividades()])
    .then(() => cargar());
})();
