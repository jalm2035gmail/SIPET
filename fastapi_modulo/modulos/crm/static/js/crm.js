(function () {
  'use strict';

  const root = document.getElementById('crm-root');
  if (!root) return;

  // ── Helpers HTTP ────────────────────────────────────────────────────────────

  const apiGet = async (url) => {
    const res = await fetch(url, { credentials: 'same-origin' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
  };

  const apiPost = async (url, body) => {
    const res = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `HTTP ${res.status}`);
    }
    return res.json();
  };

  const apiPut = async (url, body) => {
    const res = await fetch(url, {
      method: 'PUT',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `HTTP ${res.status}`);
    }
    return res.json();
  };

  const apiDelete = async (url) => {
    const res = await fetch(url, { method: 'DELETE', credentials: 'same-origin' });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || `HTTP ${res.status}`);
    }
    return res.json();
  };

  // ── Utilidades UI ───────────────────────────────────────────────────────────

  const setText = (id, text) => {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
  };

  const setStatus = (id, text, isError = false) => {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = text;
    el.style.color = isError ? '#dc2626' : '#64748b';
  };

  const badge = (value, extra = '') => {
    const cls = (value || '').toLowerCase().replace(/\s+/g, '_');
    return `<span class="crm-badge ${cls} ${extra}">${value || ''}</span>`;
  };

  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

  const renderTable = (mountId, columns, rows, emptyMsg = 'Sin datos todavía.') => {
    const mount = document.getElementById(mountId);
    if (!mount) return;
    if (!rows.length) {
      mount.innerHTML = `<p class="crm-status">${emptyMsg}</p>`;
      return;
    }
    const head = columns.map((c) => `<th>${esc(c.label)}</th>`).join('');
    const body = rows.map((row) => {
      const cols = columns.map((c) => `<td>${c.render ? c.render(row[c.key], row) : esc(row[c.key])}</td>`).join('');
      return `<tr>${cols}</tr>`;
    }).join('');
    mount.innerHTML = `<div style="overflow-x:auto;"><table class="crm-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
  };

  const formToObj = (form) => {
    const obj = {};
    new FormData(form).forEach((v, k) => { obj[k] = v === '' ? null : v; });
    return obj;
  };

  // ── Navegación por tabs ─────────────────────────────────────────────────────

  const initNav = () => {
    const buttons = Array.from(root.querySelectorAll('#crm-nav button'));
    const panels  = Array.from(root.querySelectorAll('[data-panel-id]'));
    buttons.forEach((btn) => {
      btn.addEventListener('click', () => {
        const target = btn.dataset.panel;
        buttons.forEach((b) => b.classList.toggle('is-active', b === btn));
        panels.forEach((p) => p.classList.toggle('is-active', p.dataset.panelId === target));
        if (target === 'oportunidades') loadOportunidades();
        if (target === 'actividades')   loadActividades();
        if (target === 'notas')         loadNotas();
        if (target === 'campanias')     loadCampanias();
      });
    });
  };

  // ── Catálogos auxiliares ────────────────────────────────────────────────────

  let _contactosCache = [];
  let _opCache = [];

  const loadCatalogos = async () => {
    try {
      _contactosCache = await apiGet('/api/crm/contactos');
      _opCache = await apiGet('/api/crm/oportunidades');
      const contactoOpts = '<option value="">Contacto (opcional)</option>' +
        _contactosCache.map((c) => `<option value="${c.id}">${esc(c.nombre)}</option>`).join('');
      const contactoOptsReq = '<option value="">Seleccionar contacto *</option>' +
        _contactosCache.map((c) => `<option value="${c.id}">${esc(c.nombre)}</option>`).join('');
      const opOpts = '<option value="">Oportunidad (opcional)</option>' +
        _opCache.map((o) => `<option value="${o.id}">${esc(o.nombre)}</option>`).join('');

      ['crm-op-contacto-select'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = contactoOptsReq;
      });
      ['crm-act-contacto-select', 'crm-nota-contacto-select'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = contactoOpts;
      });
      ['crm-act-op-select', 'crm-nota-op-select'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = opOpts;
      });
    } catch (_) { /* silencioso */ }
  };

  // ── Dashboard KPIs ──────────────────────────────────────────────────────────

  const loadResumen = async () => {
    try {
      const d = await apiGet('/api/crm/resumen');
      setText('crm-kpi-contactos',    d.total_contactos);
      setText('crm-kpi-oportunidades', d.oportunidades_abiertas);
      setText('crm-kpi-actividades',   d.actividades_pendientes);
      setText('crm-kpi-campanias',     d.campanias_activas);
    } catch (e) {
      console.error('CRM resumen:', e);
    }
  };

  // ── Contactos ───────────────────────────────────────────────────────────────

  const loadContactos = async () => {
    setStatus('crm-contactos-status', 'Cargando...');
    try {
      const rows = await apiGet('/api/crm/contactos');
      _contactosCache = rows;
      setStatus('crm-contactos-status', '');
      renderTable('crm-contactos-table', [
        { key: 'nombre',   label: 'Nombre',  render: (v) => `<strong>${esc(v)}</strong>` },
        { key: 'email',    label: 'Email',   render: (v) => esc(v) },
        { key: 'empresa',  label: 'Empresa', render: (v) => esc(v) },
        { key: 'puesto',   label: 'Puesto',  render: (v) => esc(v) },
        { key: 'tipo',     label: 'Tipo',    render: (v) => badge(v) },
        { key: 'fuente',   label: 'Fuente',  render: (v) => esc(v) },
        { key: 'telefono', label: 'Teléfono', render: (v) => esc(v) },
        {
          key: 'id', label: 'Acciones',
          render: (id) => `<button class="crm-btn-del-contacto" data-id="${id}" style="background:#dc2626;border:0;border-radius:8px;padding:4px 10px;color:#fff;cursor:pointer;font-size:12px;">Eliminar</button>`,
        },
      ], rows);

      root.querySelectorAll('.crm-btn-del-contacto').forEach((btn) => {
        btn.addEventListener('click', async () => {
          if (!confirm('¿Eliminar contacto?')) return;
          try {
            await apiDelete(`/api/crm/contactos/${btn.dataset.id}`);
            loadContactos();
            loadResumen();
            loadCatalogos();
          } catch (e) { alert(e.message); }
        });
      });
    } catch (e) {
      setStatus('crm-contactos-status', `Error: ${e.message}`, true);
    }
  };

  const initFormContacto = () => {
    const form = document.getElementById('crm-form-contacto');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      setStatus('crm-contacto-form-status', 'Guardando...');
      try {
        const body = formToObj(form);
        await apiPost('/api/crm/contactos', body);
        form.reset();
        setStatus('crm-contacto-form-status', 'Contacto agregado.');
        loadContactos();
        loadResumen();
        loadCatalogos();
      } catch (err) {
        setStatus('crm-contacto-form-status', `Error: ${err.message}`, true);
      }
    });
  };

  // ── Oportunidades ───────────────────────────────────────────────────────────

  const loadOportunidades = async () => {
    setStatus('crm-oportunidades-status', 'Cargando...');
    try {
      const rows = await apiGet('/api/crm/oportunidades');
      _opCache = rows;
      setStatus('crm-oportunidades-status', '');
      renderTable('crm-oportunidades-table', [
        { key: 'nombre',        label: 'Oportunidad', render: (v) => `<strong>${esc(v)}</strong>` },
        { key: 'contacto_nombre', label: 'Contacto',  render: (v) => esc(v) },
        { key: 'etapa',         label: 'Etapa',       render: (v) => badge(v) },
        { key: 'valor_estimado', label: 'Valor',      render: (v) => `$${Number(v).toLocaleString()}` },
        { key: 'probabilidad',  label: '%',           render: (v) => `${v}%` },
        { key: 'fecha_cierre_est', label: 'Cierre est.', render: (v) => esc(v) },
        { key: 'responsable',   label: 'Responsable', render: (v) => esc(v) },
        {
          key: 'id', label: 'Acciones',
          render: (id) => `<button class="crm-btn-del-op" data-id="${id}" style="background:#dc2626;border:0;border-radius:8px;padding:4px 10px;color:#fff;cursor:pointer;font-size:12px;">Eliminar</button>`,
        },
      ], rows);

      root.querySelectorAll('.crm-btn-del-op').forEach((btn) => {
        btn.addEventListener('click', async () => {
          if (!confirm('¿Eliminar oportunidad?')) return;
          try {
            await apiDelete(`/api/crm/oportunidades/${btn.dataset.id}`);
            loadOportunidades();
            loadResumen();
          } catch (e) { alert(e.message); }
        });
      });
    } catch (e) {
      setStatus('crm-oportunidades-status', `Error: ${e.message}`, true);
    }
  };

  const initFormOportunidad = () => {
    const form = document.getElementById('crm-form-oportunidad');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      setStatus('crm-oportunidad-form-status', 'Guardando...');
      try {
        const body = formToObj(form);
        if (body.contacto_id) body.contacto_id = parseInt(body.contacto_id, 10);
        if (body.valor_estimado) body.valor_estimado = parseFloat(body.valor_estimado);
        if (body.probabilidad)   body.probabilidad  = parseInt(body.probabilidad, 10);
        await apiPost('/api/crm/oportunidades', body);
        form.reset();
        setStatus('crm-oportunidad-form-status', 'Oportunidad agregada.');
        loadOportunidades();
        loadResumen();
      } catch (err) {
        setStatus('crm-oportunidad-form-status', `Error: ${err.message}`, true);
      }
    });
  };

  // ── Actividades ─────────────────────────────────────────────────────────────

  const loadActividades = async () => {
    setStatus('crm-actividades-status', 'Cargando...');
    try {
      const rows = await apiGet('/api/crm/actividades?completada=false');
      setStatus('crm-actividades-status', '');
      renderTable('crm-actividades-table', [
        { key: 'tipo',        label: 'Tipo',       render: (v) => esc(v) },
        { key: 'titulo',      label: 'Título',     render: (v) => `<strong>${esc(v)}</strong>` },
        { key: 'fecha',       label: 'Fecha',      render: (v) => esc((v || '').slice(0, 16).replace('T', ' ')) },
        { key: 'responsable', label: 'Responsable', render: (v) => esc(v) },
        {
          key: 'id', label: 'Acciones',
          render: (id) => `
            <button class="crm-btn-done-act" data-id="${id}" style="background:#15803d;border:0;border-radius:8px;padding:4px 10px;color:#fff;cursor:pointer;font-size:12px;margin-right:4px;">✓ Completar</button>
            <button class="crm-btn-del-act"  data-id="${id}" style="background:#dc2626;border:0;border-radius:8px;padding:4px 10px;color:#fff;cursor:pointer;font-size:12px;">Eliminar</button>
          `,
        },
      ], rows);

      root.querySelectorAll('.crm-btn-done-act').forEach((btn) => {
        btn.addEventListener('click', async () => {
          try {
            await apiPut(`/api/crm/actividades/${btn.dataset.id}`, { completada: true });
            loadActividades();
            loadResumen();
          } catch (e) { alert(e.message); }
        });
      });
      root.querySelectorAll('.crm-btn-del-act').forEach((btn) => {
        btn.addEventListener('click', async () => {
          if (!confirm('¿Eliminar actividad?')) return;
          try {
            await apiDelete(`/api/crm/actividades/${btn.dataset.id}`);
            loadActividades();
            loadResumen();
          } catch (e) { alert(e.message); }
        });
      });
    } catch (e) {
      setStatus('crm-actividades-status', `Error: ${e.message}`, true);
    }
  };

  const initFormActividad = () => {
    const form = document.getElementById('crm-form-actividad');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      setStatus('crm-actividad-form-status', 'Guardando...');
      try {
        const body = formToObj(form);
        if (body.contacto_id)    body.contacto_id    = parseInt(body.contacto_id, 10) || null;
        if (body.oportunidad_id) body.oportunidad_id = parseInt(body.oportunidad_id, 10) || null;
        await apiPost('/api/crm/actividades', body);
        form.reset();
        setStatus('crm-actividad-form-status', 'Actividad agregada.');
        loadActividades();
        loadResumen();
      } catch (err) {
        setStatus('crm-actividad-form-status', `Error: ${err.message}`, true);
      }
    });
  };

  // ── Notas ────────────────────────────────────────────────────────────────────

  const loadNotas = async () => {
    setStatus('crm-notas-status', 'Cargando...');
    try {
      const rows = await apiGet('/api/crm/notas');
      setStatus('crm-notas-status', '');
      const mount = document.getElementById('crm-notas-list');
      if (!mount) return;
      if (!rows.length) { mount.innerHTML = '<p class="crm-status">Sin notas todavía.</p>'; return; }
      mount.innerHTML = rows.map((n) => `
        <div style="border:1px solid rgba(15,23,42,.08);border-radius:12px;padding:14px 16px;margin-bottom:10px;background:#fafafa;">
          <p style="margin:0 0 6px;font-size:14px;">${esc(n.contenido)}</p>
          <small style="color:#94a3b8;">
            ${n.autor ? esc(n.autor) + ' · ' : ''}${(n.creado_en || '').slice(0, 16).replace('T', ' ')}
          </small>
          <button class="crm-btn-del-nota" data-id="${n.id}" style="float:right;background:#dc2626;border:0;border-radius:8px;padding:3px 9px;color:#fff;cursor:pointer;font-size:12px;">✕</button>
        </div>
      `).join('');
      root.querySelectorAll('.crm-btn-del-nota').forEach((btn) => {
        btn.addEventListener('click', async () => {
          if (!confirm('¿Eliminar nota?')) return;
          try {
            await apiDelete(`/api/crm/notas/${btn.dataset.id}`);
            loadNotas();
          } catch (e) { alert(e.message); }
        });
      });
    } catch (e) {
      setStatus('crm-notas-status', `Error: ${e.message}`, true);
    }
  };

  const initFormNota = () => {
    const form = document.getElementById('crm-form-nota');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      setStatus('crm-nota-form-status', 'Guardando...');
      try {
        const body = formToObj(form);
        if (body.contacto_id)    body.contacto_id    = parseInt(body.contacto_id, 10) || null;
        if (body.oportunidad_id) body.oportunidad_id = parseInt(body.oportunidad_id, 10) || null;
        await apiPost('/api/crm/notas', body);
        form.reset();
        setStatus('crm-nota-form-status', 'Nota guardada.');
        loadNotas();
      } catch (err) {
        setStatus('crm-nota-form-status', `Error: ${err.message}`, true);
      }
    });
  };

  // ── Campañas ─────────────────────────────────────────────────────────────────

  const loadCampanias = async () => {
    setStatus('crm-campanias-status', 'Cargando...');
    try {
      const rows = await apiGet('/api/crm/campanias');
      setStatus('crm-campanias-status', '');
      renderTable('crm-campanias-table', [
        { key: 'nombre',       label: 'Nombre',      render: (v) => `<strong>${esc(v)}</strong>` },
        { key: 'tipo',         label: 'Tipo',        render: (v) => esc(v) },
        { key: 'estado',       label: 'Estado',      render: (v) => badge(v) },
        { key: 'fecha_inicio', label: 'Inicio',      render: (v) => esc(v) },
        { key: 'fecha_fin',    label: 'Fin',         render: (v) => esc(v) },
        { key: 'descripcion',  label: 'Descripción', render: (v) => esc(v) },
      ], rows);
    } catch (e) {
      setStatus('crm-campanias-status', `Error: ${e.message}`, true);
    }
  };

  const initFormCampania = () => {
    const form = document.getElementById('crm-form-campania');
    if (!form) return;
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      setStatus('crm-campania-form-status', 'Guardando...');
      try {
        const body = formToObj(form);
        await apiPost('/api/crm/campanias', body);
        form.reset();
        setStatus('crm-campania-form-status', 'Campaña creada.');
        loadCampanias();
        loadResumen();
      } catch (err) {
        setStatus('crm-campania-form-status', `Error: ${err.message}`, true);
      }
    });
  };

  // ── Bootstrap ────────────────────────────────────────────────────────────────

  const init = async () => {
    initNav();
    initFormContacto();
    initFormOportunidad();
    initFormActividad();
    initFormNota();
    initFormCampania();
    await loadResumen();
    await loadCatalogos();
    loadContactos();
  };

  init();
})();
