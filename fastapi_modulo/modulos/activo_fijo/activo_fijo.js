/* global AF */
(function () {
  'use strict';

  // ── State ─────────────────────────────────────────────────────────────────
  let _activos = [];

  // ── Utils ─────────────────────────────────────────────────────────────────
  const $ = (id) => document.getElementById(id);
  const fmt = (v) => v != null ? Number(v).toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—';
  const fmtDate = (d) => d ? d.slice(0, 10) : '—';

  function badge(cls, label) {
    return `<span class="af-badge badge-${cls}">${label}</span>`;
  }

  const ESTADO_LABEL = {
    activo: 'Activo', asignado: 'Asignado',
    en_mantenimiento: 'En mantenimiento', dado_de_baja: 'Dado de baja',
  };
  const METODO_LABEL = { linea_recta: 'Línea recta', saldo_decreciente: 'Saldo decreciente' };
  const TIPO_LABEL = { preventivo: 'Preventivo', correctivo: 'Correctivo', reparacion: 'Reparación' };
  const ESTADO_MNT = { pendiente: 'Pendiente', en_proceso: 'En proceso', completado: 'Completado' };

  async function api(method, url, body) {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body !== undefined) opts.body = JSON.stringify(body);
    const r = await fetch(url, opts);
    if (r.status === 204) return null;
    const json = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(json.detail || `Error ${r.status}`);
    return json;
  }

  function showError(msg) { alert('Error: ' + msg); }

  // ── Navigation ────────────────────────────────────────────────────────────
  document.querySelectorAll('.af-nav-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.af-nav-btn').forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('.af-panel').forEach((p) => p.classList.remove('active'));
      btn.classList.add('active');
      const panel = document.getElementById('panel-' + btn.dataset.panel);
      if (panel) panel.classList.add('active');
      // Lazy-load panel data
      const p = btn.dataset.panel;
      if (p === 'activos') loadActivos();
      if (p === 'depreciaciones') loadDepreciaciones();
      if (p === 'asignaciones') loadAsignaciones();
      if (p === 'mantenimiento') loadMantenimiento();
      if (p === 'bajas') loadBajas();
    });
  });

  // ── Modal helpers ─────────────────────────────────────────────────────────
  function openModal(id) { $(id).classList.add('open'); }
  function closeModal(id) { $(id).classList.remove('open'); }

  document.querySelectorAll('.af-modal-backdrop').forEach((m) => {
    m.addEventListener('click', (e) => { if (e.target === m) m.classList.remove('open'); });
  });
  $('modal-activo-close').addEventListener('click', () => closeModal('modal-activo'));
  $('btn-activo-cancel').addEventListener('click', () => closeModal('modal-activo'));
  $('modal-dep-close').addEventListener('click', () => closeModal('modal-depreciar'));
  $('btn-dep-cancel').addEventListener('click', () => closeModal('modal-depreciar'));
  $('modal-asig-close').addEventListener('click', () => closeModal('modal-asignacion'));
  $('btn-asig-cancel').addEventListener('click', () => closeModal('modal-asignacion'));
  $('modal-mant-close').addEventListener('click', () => closeModal('modal-mant'));
  $('btn-mant-cancel').addEventListener('click', () => closeModal('modal-mant'));
  $('modal-baja-close').addEventListener('click', () => closeModal('modal-baja'));
  $('btn-baja-cancel').addEventListener('click', () => closeModal('modal-baja'));

  // ── KPIs ──────────────────────────────────────────────────────────────────
  async function loadKpis() {
    try {
      const d = await api('GET', '/api/activo-fijo/resumen');
      $('kpi-total').textContent = d.total_activos;
      $('kpi-asignados').textContent = d.activos_asignados;
      $('kpi-mant').textContent = d.activos_en_mantenimiento;
      $('kpi-baja').textContent = d.activos_dados_baja;
      $('kpi-valor-libro').textContent = '$' + fmt(d.valor_libro_total);
      $('kpi-dep-acum').textContent = '$' + fmt(d.depreciacion_acumulada);
    } catch (e) { /* silent */ }
  }

  // ── Rebuild selects ───────────────────────────────────────────────────────
  function rebuildActivoSelects() {
    const selIds = [
      'filter-activo-dep', 'filter-activo-asig', 'filter-activo-mant',
      'dep-activo-id', 'asig-activo-id', 'mant-activo-id',
    ];
    selIds.forEach((id) => {
      const sel = $(id);
      if (!sel) return;
      const current = sel.value;
      const isFilter = id.startsWith('filter-');
      sel.innerHTML = `<option value="">${isFilter ? 'Todos los activos' : 'Seleccionar activo…'}</option>`;
      _activos.filter((a) => a.estado !== 'dado_de_baja').forEach((a) => {
        const opt = document.createElement('option');
        opt.value = a.id;
        opt.textContent = `${a.codigo} – ${a.nombre}`;
        sel.appendChild(opt);
      });
      sel.value = current || '';
    });
  }

  // ── ACTIVOS ───────────────────────────────────────────────────────────────
  async function loadActivos() {
    const estado = $('filter-estado-activo').value;
    try {
      const url = '/api/activo-fijo/activos' + (estado ? `?estado=${estado}` : '');
      _activos = await api('GET', url);
      rebuildActivoSelects();
      renderActivos();
    } catch (e) { showError(e.message); }
  }

  function renderActivos() {
    const q = $('filter-nombre-activo').value.toLowerCase();
    const rows = _activos.filter((a) =>
      !q || a.nombre.toLowerCase().includes(q) || (a.codigo || '').toLowerCase().includes(q)
    );
    const tb = $('tbody-activos');
    if (!rows.length) { tb.innerHTML = '<tr><td colspan="8" class="af-empty">Sin activos registrados.</td></tr>'; return; }
    tb.innerHTML = rows.map((a) => `
      <tr>
        <td>${a.codigo || '—'}</td>
        <td>${a.nombre}</td>
        <td>${a.categoria || '—'}</td>
        <td>$${fmt(a.valor_adquisicion)}</td>
        <td>$${fmt(a.valor_libro)}</td>
        <td>${METODO_LABEL[a.metodo_depreciacion] || a.metodo_depreciacion}</td>
        <td>${badge(a.estado, ESTADO_LABEL[a.estado] || a.estado)}</td>
        <td style="white-space:nowrap">
          <button class="af-btn af-btn-secondary af-btn-sm" onclick="AF.editActivo(${a.id})">Editar</button>
          <button class="af-btn af-btn-warning af-btn-sm" onclick="AF.bajaActivo(${a.id})">Baja</button>
          <button class="af-btn af-btn-danger af-btn-sm" onclick="AF.deleteActivo(${a.id})">Eliminar</button>
        </td>
      </tr>`).join('');
  }

  $('filter-estado-activo').addEventListener('change', loadActivos);
  $('filter-nombre-activo').addEventListener('input', renderActivos);

  $('btn-nuevo-activo').addEventListener('click', () => {
    $('modal-activo-title').textContent = 'Nuevo activo';
    $('form-activo').reset();
    $('activo-id').value = '';
    $('activo-vida-util').value = '60';
    $('activo-valor-residual').value = '0';
    openModal('modal-activo');
  });

  window.AF = window.AF || {};
  AF.editActivo = async (id) => {
    const a = _activos.find((x) => x.id === id);
    if (!a) return;
    $('modal-activo-title').textContent = 'Editar activo';
    $('activo-id').value = id;
    $('activo-codigo').value = a.codigo || '';
    $('activo-nombre').value = a.nombre || '';
    $('activo-categoria').value = a.categoria || '';
    $('activo-marca').value = a.marca || '';
    $('activo-modelo').value = a.modelo || '';
    $('activo-serie').value = a.numero_serie || '';
    $('activo-proveedor').value = a.proveedor || '';
    $('activo-fecha-adq').value = a.fecha_adquisicion ? a.fecha_adquisicion.slice(0, 10) : '';
    $('activo-valor-adq').value = a.valor_adquisicion || '0';
    $('activo-valor-residual').value = a.valor_residual || '0';
    $('activo-vida-util').value = a.vida_util_meses || 60;
    $('activo-metodo-dep').value = a.metodo_depreciacion || 'linea_recta';
    $('activo-ubicacion').value = a.ubicacion || '';
    $('activo-responsable').value = a.responsable || '';
    $('activo-estado').value = a.estado || 'activo';
    $('activo-descripcion').value = a.descripcion || '';
    openModal('modal-activo');
  };

  $('form-activo').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = $('activo-id').value;
    const payload = {
      codigo: $('activo-codigo').value.trim() || null,
      nombre: $('activo-nombre').value.trim(),
      categoria: $('activo-categoria').value.trim() || null,
      marca: $('activo-marca').value.trim() || null,
      modelo: $('activo-modelo').value.trim() || null,
      numero_serie: $('activo-serie').value.trim() || null,
      proveedor: $('activo-proveedor').value.trim() || null,
      fecha_adquisicion: $('activo-fecha-adq').value || null,
      valor_adquisicion: parseFloat($('activo-valor-adq').value) || 0,
      valor_residual: parseFloat($('activo-valor-residual').value) || 0,
      vida_util_meses: parseInt($('activo-vida-util').value) || 60,
      metodo_depreciacion: $('activo-metodo-dep').value,
      ubicacion: $('activo-ubicacion').value.trim() || null,
      responsable: $('activo-responsable').value.trim() || null,
      estado: $('activo-estado').value,
      descripcion: $('activo-descripcion').value.trim() || null,
    };
    try {
      if (id) {
        await api('PUT', `/api/activo-fijo/activos/${id}`, payload);
      } else {
        await api('POST', '/api/activo-fijo/activos', payload);
      }
      closeModal('modal-activo');
      loadActivos();
      loadKpis();
    } catch (e) { showError(e.message); }
  });

  AF.deleteActivo = async (id) => {
    if (!confirm('¿Eliminar este activo? Se perderán todos sus registros asociados.')) return;
    try {
      await api('DELETE', `/api/activo-fijo/activos/${id}`);
      loadActivos();
      loadKpis();
    } catch (e) { showError(e.message); }
  };

  AF.bajaActivo = (id) => {
    const a = _activos.find((x) => x.id === id);
    if (!a) return;
    $('baja-activo-id').value = id;
    $('baja-activo-nombre').value = `${a.codigo || ''} – ${a.nombre}`;
    const hoy = new Date().toISOString().slice(0, 10);
    $('baja-fecha').value = hoy;
    $('baja-valor-residual').value = a.valor_residual || '0';
    $('baja-obs').value = '';
    openModal('modal-baja');
  };

  // ── DEPRECIACIONES ────────────────────────────────────────────────────────
  async function loadDepreciaciones() {
    const activoId = $('filter-activo-dep').value;
    const periodo = $('filter-periodo-dep').value;
    let url = '/api/activo-fijo/depreciaciones?';
    if (activoId) url += `activo_id=${activoId}&`;
    if (periodo) url += `periodo=${periodo.slice(0, 7)}&`;
    try {
      const rows = await api('GET', url);
      const tb = $('tbody-depreciaciones');
      if (!rows.length) { tb.innerHTML = '<tr><td colspan="7" class="af-empty">Sin depreciaciones registradas.</td></tr>'; return; }
      tb.innerHTML = rows.map((d) => `
        <tr>
          <td>${d.periodo}</td>
          <td>${d.activo_codigo ? d.activo_codigo + ' – ' : ''}${d.activo_nombre || '—'}</td>
          <td>${METODO_LABEL[d.metodo] || d.metodo}</td>
          <td>$${fmt(d.valor_depreciacion)}</td>
          <td>$${fmt(d.valor_libro_anterior)}</td>
          <td>$${fmt(d.valor_libro_nuevo)}</td>
          <td>
            <button class="af-btn af-btn-danger af-btn-sm" onclick="AF.deleteDep(${d.id})">Revertir</button>
          </td>
        </tr>`).join('');
    } catch (e) { showError(e.message); }
  }

  $('filter-activo-dep').addEventListener('change', loadDepreciaciones);
  $('filter-periodo-dep').addEventListener('change', loadDepreciaciones);

  $('btn-depreciar').addEventListener('click', () => {
    $('form-depreciar').reset();
    const hoy = new Date();
    $('dep-periodo').value = `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, '0')}`;
    openModal('modal-depreciar');
  });

  // Show/hide tasa field based on selected activo's method
  $('dep-activo-id').addEventListener('change', () => {
    const id = parseInt($('dep-activo-id').value);
    const a = _activos.find((x) => x.id === id);
    $('dep-tasa-group').style.display = (a && a.metodo_depreciacion === 'saldo_decreciente') ? '' : 'none';
  });
  $('dep-tasa-group').style.display = 'none';

  $('form-depreciar').addEventListener('submit', async (e) => {
    e.preventDefault();
    const activoId = $('dep-activo-id').value;
    const periodoVal = $('dep-periodo').value;
    const tasa = $('dep-tasa').value;
    const payload = {};
    if (periodoVal) payload.periodo = periodoVal.slice(0, 7);
    if (tasa) payload.tasa_saldo_decreciente = parseFloat(tasa);
    try {
      await api('POST', `/api/activo-fijo/activos/${activoId}/depreciar`, payload);
      closeModal('modal-depreciar');
      loadDepreciaciones();
      loadActivos();
      loadKpis();
    } catch (e) { showError(e.message); }
  });

  AF.deleteDep = async (id) => {
    if (!confirm('¿Revertir esta depreciación? Se restaurará el valor en libros anterior.')) return;
    try {
      await api('DELETE', `/api/activo-fijo/depreciaciones/${id}`);
      loadDepreciaciones();
      loadActivos();
      loadKpis();
    } catch (e) { showError(e.message); }
  };

  // ── ASIGNACIONES ──────────────────────────────────────────────────────────
  async function loadAsignaciones() {
    const activoId = $('filter-activo-asig').value;
    const estado = $('filter-estado-asig').value;
    let url = '/api/activo-fijo/asignaciones?';
    if (activoId) url += `activo_id=${activoId}&`;
    if (estado) url += `estado=${estado}&`;
    try {
      const rows = await api('GET', url);
      const tb = $('tbody-asignaciones');
      if (!rows.length) { tb.innerHTML = '<tr><td colspan="7" class="af-empty">Sin asignaciones registradas.</td></tr>'; return; }
      tb.innerHTML = rows.map((a) => `
        <tr>
          <td>${a.activo_codigo ? a.activo_codigo + ' – ' : ''}${a.activo_nombre || '—'}</td>
          <td>${a.empleado || '—'}</td>
          <td>${a.area || '—'}</td>
          <td>${fmtDate(a.fecha_asignacion)}</td>
          <td>${fmtDate(a.fecha_devolucion)}</td>
          <td>${badge(a.estado, a.estado === 'vigente' ? 'Vigente' : 'Devuelto')}</td>
          <td style="white-space:nowrap">
            <button class="af-btn af-btn-secondary af-btn-sm" onclick="AF.editAsig(${a.id})">Editar</button>
            <button class="af-btn af-btn-danger af-btn-sm" onclick="AF.deleteAsig(${a.id})">Eliminar</button>
          </td>
        </tr>`).join('');
    } catch (e) { showError(e.message); }
  }

  $('filter-activo-asig').addEventListener('change', loadAsignaciones);
  $('filter-estado-asig').addEventListener('change', loadAsignaciones);

  $('btn-nueva-asignacion').addEventListener('click', () => {
    $('modal-asig-title').textContent = 'Nueva asignación';
    $('form-asignacion').reset();
    $('asig-id').value = '';
    const hoy = new Date().toISOString().slice(0, 10);
    $('asig-fecha').value = hoy;
    openModal('modal-asignacion');
  });

  let _asigCache = [];
  AF.editAsig = async (id) => {
    if (!_asigCache.length) {
      _asigCache = await api('GET', '/api/activo-fijo/asignaciones');
    }
    const a = _asigCache.find((x) => x.id === id);
    if (!a) return;
    $('modal-asig-title').textContent = 'Editar asignación';
    $('asig-id').value = id;
    $('asig-activo-id').value = a.activo_id;
    $('asig-empleado').value = a.empleado || '';
    $('asig-area').value = a.area || '';
    $('asig-fecha').value = a.fecha_asignacion ? a.fecha_asignacion.slice(0, 10) : '';
    $('asig-fecha-dev').value = a.fecha_devolucion ? a.fecha_devolucion.slice(0, 10) : '';
    $('asig-estado').value = a.estado || 'vigente';
    $('asig-obs').value = a.observaciones || '';
    openModal('modal-asignacion');
  };

  $('form-asignacion').addEventListener('submit', async (e) => {
    e.preventDefault();
    _asigCache = [];
    const id = $('asig-id').value;
    const payload = {
      activo_id: parseInt($('asig-activo-id').value),
      empleado: $('asig-empleado').value.trim(),
      area: $('asig-area').value.trim() || null,
      fecha_asignacion: $('asig-fecha').value || null,
      fecha_devolucion: $('asig-fecha-dev').value || null,
      estado: $('asig-estado').value,
      observaciones: $('asig-obs').value.trim() || null,
    };
    try {
      if (id) {
        await api('PUT', `/api/activo-fijo/asignaciones/${id}`, payload);
      } else {
        await api('POST', '/api/activo-fijo/asignaciones', payload);
      }
      closeModal('modal-asignacion');
      loadAsignaciones();
      loadActivos();
      loadKpis();
    } catch (e) { showError(e.message); }
  });

  AF.deleteAsig = async (id) => {
    _asigCache = [];
    if (!confirm('¿Eliminar esta asignación?')) return;
    try {
      await api('DELETE', `/api/activo-fijo/asignaciones/${id}`);
      loadAsignaciones();
      loadActivos();
    } catch (e) { showError(e.message); }
  };

  // ── MANTENIMIENTO ─────────────────────────────────────────────────────────
  let _mantCache = [];
  async function loadMantenimiento() {
    const activoId = $('filter-activo-mant').value;
    const estado = $('filter-estado-mant').value;
    let url = '/api/activo-fijo/mantenimientos?';
    if (activoId) url += `activo_id=${activoId}&`;
    if (estado) url += `estado=${estado}&`;
    try {
      _mantCache = await api('GET', url);
      const tb = $('tbody-mantenimiento');
      if (!_mantCache.length) { tb.innerHTML = '<tr><td colspan="7" class="af-empty">Sin mantenimientos registrados.</td></tr>'; return; }
      tb.innerHTML = _mantCache.map((m) => `
        <tr>
          <td>${m.activo_codigo ? m.activo_codigo + ' – ' : ''}${m.activo_nombre || '—'}</td>
          <td>${badge(m.tipo, TIPO_LABEL[m.tipo] || m.tipo)}</td>
          <td>${m.descripcion || '—'}</td>
          <td>${fmtDate(m.fecha_inicio)}</td>
          <td>${m.costo != null ? '$' + fmt(m.costo) : '—'}</td>
          <td>${badge(m.estado, ESTADO_MNT[m.estado] || m.estado)}</td>
          <td style="white-space:nowrap">
            <button class="af-btn af-btn-secondary af-btn-sm" onclick="AF.editMant(${m.id})">Editar</button>
            <button class="af-btn af-btn-danger af-btn-sm" onclick="AF.deleteMant(${m.id})">Eliminar</button>
          </td>
        </tr>`).join('');
    } catch (e) { showError(e.message); }
  }

  $('filter-activo-mant').addEventListener('change', loadMantenimiento);
  $('filter-estado-mant').addEventListener('change', loadMantenimiento);

  $('btn-nuevo-mant').addEventListener('click', () => {
    $('modal-mant-title').textContent = 'Registrar mantenimiento';
    $('form-mant').reset();
    $('mant-id').value = '';
    const hoy = new Date().toISOString().slice(0, 10);
    $('mant-fecha-inicio').value = hoy;
    openModal('modal-mant');
  });

  AF.editMant = (id) => {
    const m = _mantCache.find((x) => x.id === id);
    if (!m) return;
    $('modal-mant-title').textContent = 'Editar mantenimiento';
    $('mant-id').value = id;
    $('mant-activo-id').value = m.activo_id;
    $('mant-tipo').value = m.tipo || 'preventivo';
    $('mant-estado').value = m.estado || 'pendiente';
    $('mant-fecha-inicio').value = m.fecha_inicio ? m.fecha_inicio.slice(0, 10) : '';
    $('mant-fecha-fin').value = m.fecha_fin ? m.fecha_fin.slice(0, 10) : '';
    $('mant-proveedor').value = m.proveedor || '';
    $('mant-costo').value = m.costo || '';
    $('mant-descripcion').value = m.descripcion || '';
    $('mant-obs').value = m.observaciones || '';
    openModal('modal-mant');
  };

  $('form-mant').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = $('mant-id').value;
    const payload = {
      activo_id: parseInt($('mant-activo-id').value),
      tipo: $('mant-tipo').value,
      estado: $('mant-estado').value,
      fecha_inicio: $('mant-fecha-inicio').value || null,
      fecha_fin: $('mant-fecha-fin').value || null,
      proveedor: $('mant-proveedor').value.trim() || null,
      costo: $('mant-costo').value ? parseFloat($('mant-costo').value) : null,
      descripcion: $('mant-descripcion').value.trim(),
      observaciones: $('mant-obs').value.trim() || null,
    };
    try {
      if (id) {
        await api('PUT', `/api/activo-fijo/mantenimientos/${id}`, payload);
      } else {
        await api('POST', '/api/activo-fijo/mantenimientos', payload);
      }
      closeModal('modal-mant');
      loadMantenimiento();
      loadActivos();
      loadKpis();
    } catch (e) { showError(e.message); }
  });

  AF.deleteMant = async (id) => {
    if (!confirm('¿Eliminar este registro de mantenimiento?')) return;
    try {
      await api('DELETE', `/api/activo-fijo/mantenimientos/${id}`);
      loadMantenimiento();
      loadActivos();
    } catch (e) { showError(e.message); }
  };

  // ── BAJAS ─────────────────────────────────────────────────────────────────
  async function loadBajas() {
    try {
      const rows = await api('GET', '/api/activo-fijo/bajas');
      const tb = $('tbody-bajas');
      if (!rows.length) { tb.innerHTML = '<tr><td colspan="6" class="af-empty">Sin activos dados de baja.</td></tr>'; return; }
      const MOTIVO = {
        obsolescencia: 'Obsolescencia', dano: 'Daño', venta: 'Venta',
        robo: 'Robo/Extravío', donacion: 'Donación', otro: 'Otro',
      };
      tb.innerHTML = rows.map((b) => `
        <tr>
          <td>${b.activo_codigo ? b.activo_codigo + ' – ' : ''}${b.activo_nombre || '—'}</td>
          <td>${MOTIVO[b.motivo] || b.motivo}</td>
          <td>${fmtDate(b.fecha_baja)}</td>
          <td>${b.valor_residual_real != null ? '$' + fmt(b.valor_residual_real) : '—'}</td>
          <td>${b.observaciones || '—'}</td>
          <td>
            <button class="af-btn af-btn-secondary af-btn-sm" onclick="AF.reactivarBaja(${b.id})">Reactivar</button>
          </td>
        </tr>`).join('');
    } catch (e) { showError(e.message); }
  }

  $('form-baja').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
      activo_id: parseInt($('baja-activo-id').value),
      motivo: $('baja-motivo').value,
      fecha_baja: $('baja-fecha').value || null,
      valor_residual_real: parseFloat($('baja-valor-residual').value) || 0,
      observaciones: $('baja-obs').value.trim() || null,
    };
    try {
      await api('POST', '/api/activo-fijo/bajas', payload);
      closeModal('modal-baja');
      loadBajas();
      loadActivos();
      loadKpis();
    } catch (e) { showError(e.message); }
  });

  AF.reactivarBaja = async (id) => {
    if (!confirm('¿Reactivar este activo? Se eliminará el registro de baja.')) return;
    try {
      await api('DELETE', `/api/activo-fijo/bajas/${id}`);
      loadBajas();
      loadActivos();
      loadKpis();
    } catch (e) { showError(e.message); }
  };

  // ── Init ──────────────────────────────────────────────────────────────────
  loadKpis();
  loadActivos();
})();
