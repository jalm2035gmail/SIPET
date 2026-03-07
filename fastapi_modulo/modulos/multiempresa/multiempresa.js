(function () {
  'use strict';

  // ── State / utils ─────────────────────────────────────────────────────────
  let _empresas = [];
  let _pendingLogoFile = null;
  let _scope = { nivel: 'admin', puede_crear: false, puede_eliminar: false, tenant_filter: null };

  const $ = (id) => document.getElementById(id);
  const fmtDate = (d) => d ? d.slice(0, 10) : '—';

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
  document.querySelectorAll('.me-nav-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.me-nav-btn').forEach((b) => b.classList.remove('active'));
      document.querySelectorAll('.me-panel').forEach((p) => p.classList.remove('active'));
      btn.classList.add('active');
      const panel = document.getElementById('panel-' + btn.dataset.panel);
      if (panel) panel.classList.add('active');
      if (btn.dataset.panel === 'empresas') loadEmpresas();
      if (btn.dataset.panel === 'consolidado') loadConsolidado();
    });
  });

  // ── Modal helpers ─────────────────────────────────────────────────────────
  function openModal(id)  { $(id).classList.add('open'); }
  function closeModal(id) { $(id).classList.remove('open'); }

  document.querySelectorAll('.me-modal-backdrop').forEach((m) => {
    m.addEventListener('click', (e) => { if (e.target === m) m.classList.remove('open'); });
  });
  $('modal-empresa-close').addEventListener('click', () => closeModal('modal-empresa'));
  $('btn-empresa-cancel').addEventListener('click', () => closeModal('modal-empresa'));

  // ── Logo file picker ──────────────────────────────────────────────────────
  $('logo-preview-wrap').addEventListener('click', () => $('logo-file-input').click());
  $('logo-file-input').addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (!file) return;
    _pendingLogoFile = file;
    const reader = new FileReader();
    reader.onload = (ev) => {
      $('logo-preview-img').src = ev.target.result;
      $('logo-preview-img').style.display = 'block';
      $('logo-preview-icon').style.display = 'none';
    };
    reader.readAsDataURL(file);
  });

  function resetLogoPreview(logoUrl) {
    _pendingLogoFile = null;
    $('logo-file-input').value = '';
    if (logoUrl) {
      $('logo-preview-img').src = logoUrl;
      $('logo-preview-img').style.display = 'block';
      $('logo-preview-icon').style.display = 'none';
    } else {
      $('logo-preview-img').style.display = 'none';
      $('logo-preview-icon').style.display = '';
    }
  }

  // ── KPIs ──────────────────────────────────────────────────────────────────
  async function loadKpis() {
    try {
      const d = await api('GET', '/api/multiempresa/consolidado');
      $('kpi-total').textContent    = d.total_empresas;
      $('kpi-activas').textContent  = d.empresas_activas;
      $('kpi-inactivas').textContent = d.empresas_inactivas;
      $('kpi-logo').textContent     = d.empresas_con_logo;
    } catch (_) { /* silent */ }
  }

  // ── EMPRESAS ──────────────────────────────────────────────────────────────
  async function loadEmpresas() {
    const estado = $('filter-estado-empresa').value;
    try {
      const url = '/api/multiempresa/empresas' + (estado ? `?estado=${estado}` : '');
      _empresas = await api('GET', url);
      renderEmpresas();
    } catch (e) { showError(e.message); }
  }

  function renderEmpresas() {
    const q = $('filter-nombre-empresa').value.toLowerCase();
    const rows = _empresas.filter((e) =>
      !q || e.nombre.toLowerCase().includes(q) || (e.codigo || '').toLowerCase().includes(q)
    );
    const tb = $('tbody-empresas');
    if (!rows.length) {
      tb.innerHTML = '<tr><td colspan="8" class="me-empty">Sin empresas registradas.</td></tr>';
      return;
    }
    tb.innerHTML = rows.map((e) => `
      <tr>
        <td>
          ${e.logo_url
            ? `<img src="${e.logo_url}" style="width:36px;height:36px;object-fit:contain;border-radius:6px;border:1px solid #e2e8f0;padding:2px" alt="logo">`
            : `<div style="width:36px;height:36px;border-radius:6px;background:#f1f5f9;border:1px solid #e2e8f0;display:flex;align-items:center;justify-content:center;font-size:16px">🏢</div>`
          }
        </td>
        <td><code style="background:#f1f5f9;padding:2px 6px;border-radius:4px;font-size:12px">${e.codigo}</code></td>
        <td><strong>${e.nombre}</strong></td>
        <td><code style="font-size:11px;color:#64748b">${e.tenant_id}</code></td>
        <td>${e.rfc || '—'}</td>
        <td>${e.email_contacto || '—'}</td>
        <td><span class="me-badge badge-${e.estado}">${e.estado === 'activa' ? 'Activa' : 'Inactiva'}</span></td>
        <td style="white-space:nowrap">
          <button class="me-btn me-btn-secondary me-btn-sm" onclick="ME.editEmpresa(${e.id})">Editar</button>
          ${_scope.puede_eliminar
            ? `<button class="me-btn me-btn-danger me-btn-sm" onclick="ME.deleteEmpresa(${e.id})">Eliminar</button>`
            : ''}
        </td>
      </tr>`).join('');
  }

  $('filter-estado-empresa').addEventListener('change', loadEmpresas);
  $('filter-nombre-empresa').addEventListener('input', renderEmpresas);

  $('btn-nueva-empresa').addEventListener('click', () => {
    $('modal-empresa-title').textContent = 'Nueva empresa';
    $('form-empresa').reset();
    $('empresa-id').value = '';
    $('empresa-estado').value = 'activa';
    $('empresa-color').value = '#0f172a';
    resetLogoPreview(null);
    openModal('modal-empresa');
  });

  window.ME = window.ME || {};

  ME.editEmpresa = (id) => {
    const e = _empresas.find((x) => x.id === id);
    if (!e) return;
    $('modal-empresa-title').textContent = 'Editar empresa';
    $('empresa-id').value         = id;
    $('empresa-codigo').value     = e.codigo || '';
    $('empresa-tenant').value     = e.tenant_id || '';
    $('empresa-nombre').value     = e.nombre || '';
    $('empresa-rfc').value        = e.rfc || '';
    $('empresa-email').value      = e.email_contacto || '';
    $('empresa-telefono').value   = e.telefono || '';
    $('empresa-color').value      = e.color_primario || '#0f172a';
    $('empresa-estado').value     = e.estado || 'activa';
    $('empresa-direccion').value  = e.direccion || '';
    $('empresa-descripcion').value = e.descripcion || '';
    resetLogoPreview(e.logo_url);
    openModal('modal-empresa');
  };

  $('form-empresa').addEventListener('submit', async (e) => {
    e.preventDefault();
    const id = $('empresa-id').value;
    const isNew = !id;

    const payload = {
      codigo: $('empresa-codigo').value.trim().toUpperCase(),
      tenant_id: $('empresa-tenant').value.trim().toLowerCase(),
      nombre: $('empresa-nombre').value.trim(),
      rfc: $('empresa-rfc').value.trim() || null,
      email_contacto: $('empresa-email').value.trim() || null,
      telefono: $('empresa-telefono').value.trim() || null,
      color_primario: $('empresa-color').value,
      estado: $('empresa-estado').value,
      direccion: $('empresa-direccion').value.trim() || null,
      descripcion: $('empresa-descripcion').value.trim() || null,
    };

    try {
      let saved;
      if (isNew) {
        saved = await api('POST', '/api/multiempresa/empresas', payload);
      } else {
        const { codigo, tenant_id, ...updatePayload } = payload;
        saved = await api('PUT', `/api/multiempresa/empresas/${id}`, updatePayload);
      }

      // Upload logo if a file was selected
      if (_pendingLogoFile && saved) {
        const fd = new FormData();
        fd.append('file', _pendingLogoFile);
        const ures = await fetch(`/api/multiempresa/empresas/${saved.id}/logo`, { method: 'POST', body: fd });
        if (!ures.ok) {
          const err = await ures.json().catch(() => ({}));
          showError(err.detail || 'Error al subir el logo');
        }
      }

      closeModal('modal-empresa');
      loadEmpresas();
      loadKpis();
    } catch (err) { showError(err.message); }
  });

  ME.deleteEmpresa = async (id) => {
    const e = _empresas.find((x) => x.id === id);
    if (!confirm(`¿Eliminar la empresa "${e?.nombre}"? Esta acción no se puede deshacer.`)) return;
    try {
      await api('DELETE', `/api/multiempresa/empresas/${id}`);
      loadEmpresas();
      loadKpis();
    } catch (err) { showError(err.message); }
  };

  // Auto-fill tenant_id from codigo
  $('empresa-codigo').addEventListener('input', (e) => {
    if ($('empresa-id').value) return; // editing — don't override
    $('empresa-tenant').value = e.target.value.trim().toLowerCase().replace(/[^a-z0-9._-]/g, '-').replace(/-+/g, '-');
  });

  // ── CONSOLIDADO ───────────────────────────────────────────────────────────
  async function loadConsolidado() {
    const grid = $('consolidado-grid');
    grid.innerHTML = '<p class="me-empty">Cargando consolidado…</p>';
    try {
      const d = await api('GET', '/api/multiempresa/consolidado');
      if (!d.empresas.length) {
        grid.innerHTML = '<p class="me-empty">No hay empresas registradas aún.</p>';
        return;
      }
      grid.innerHTML = d.empresas.map((e) => `
        <div class="me-empresa-card">
          <div class="me-empresa-card-top">
            ${e.logo_url
              ? `<img src="${e.logo_url}" class="me-empresa-logo" alt="logo ${e.nombre}">`
              : `<div class="me-empresa-logo-placeholder">🏢</div>`
            }
            <div>
              <div class="me-empresa-card-name">${e.nombre}</div>
              <div class="me-empresa-card-code">${e.codigo}</div>
              <span class="me-badge badge-${e.estado}" style="margin-top:4px;display:inline-block">
                ${e.estado === 'activa' ? 'Activa' : 'Inactiva'}
              </span>
            </div>
          </div>
          <div class="me-accent-bar" style="background:${e.color_primario || '#0f172a'}"></div>
          <div class="me-empresa-card-meta">
            ${e.tenant_id ? `<span>🔑 <code>${e.tenant_id}</code></span>` : ''}
            ${e.rfc ? `<span>📄 RFC: ${e.rfc}</span>` : ''}
            ${e.email_contacto ? `<span>✉️ ${e.email_contacto}</span>` : ''}
            ${e.telefono ? `<span>📞 ${e.telefono}</span>` : ''}
            ${e.descripcion ? `<span style="color:#64748b;font-style:italic">${e.descripcion}</span>` : ''}
          </div>
        </div>`).join('');
    } catch (err) { showError(err.message); }
  }

  $('btn-refresh-consolidado').addEventListener('click', loadConsolidado);

  // ── Init ──────────────────────────────────────────────────────────────────
  async function init() {
    try {
      _scope = await api('GET', '/api/multiempresa/scope');
    } catch (_) { /* use defaults */ }

    // Show/hide "Nueva empresa" button based on permissions
    const btnNueva = $('btn-nueva-empresa');
    if (btnNueva) btnNueva.style.display = _scope.puede_crear ? '' : 'none';

    loadKpis();
    loadEmpresas();
  }

  init();
})();
