(function () {
  const root = document.getElementById('intelicoop-root');
  if (!root) return;

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
      throw new Error(data.detail || data.error || `HTTP ${res.status}`);
    }
    return res.json();
  };

  const setStatus = (id, text) => {
    const node = document.getElementById(id);
    if (node) node.textContent = text;
  };

  const renderTable = (mountId, columns, rows) => {
    const mount = document.getElementById(mountId);
    if (!mount) return;
    if (!rows.length) {
      mount.innerHTML = '<p class="intelicoop-status">Sin datos todavia.</p>';
      return;
    }
    const head = columns.map((col) => `<th>${col.label}</th>`).join('');
    const body = rows.map((row) => {
      const cols = columns.map((col) => `<td>${row[col.key] ?? ''}</td>`).join('');
      return `<tr>${cols}</tr>`;
    }).join('');
    mount.innerHTML = `<table class="intelicoop-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
  };

  const updateTabs = () => {
    const buttons = Array.from(document.querySelectorAll('#intelicoop-nav button'));
    const panels = Array.from(document.querySelectorAll('[data-panel-id]'));
    buttons.forEach((button) => {
      button.addEventListener('click', () => {
        const target = button.getAttribute('data-panel');
        buttons.forEach((item) => item.classList.toggle('is-active', item === button));
        panels.forEach((panel) => panel.classList.toggle('is-active', panel.getAttribute('data-panel-id') === target));
      });
    });
  };

  const setFormResult = (id, text, isError) => {
    const node = document.getElementById(id);
    if (!node) return;
    node.innerHTML = `<p class="intelicoop-status" style="color:${isError ? '#991b1b' : '#0f766e'};">${text}</p>`;
  };

  const loadCatalogs = async () => {
    const data = await apiGet('/api/intelicoop/catalogos/basicos');
    const socioSelect = document.getElementById('intelicoop-credito-socio');
    const cuentaSocioSelect = document.getElementById('intelicoop-cuenta-socio');
    const cuentaSelect = document.getElementById('intelicoop-transaccion-cuenta');
    const pagoCreditoSelect = document.getElementById('intelicoop-pago-credito');
    const contactoSocioSelect = document.getElementById('intelicoop-contacto-socio');
    const seguimientoSocioSelect = document.getElementById('intelicoop-seguimiento-socio');
    const socioOptions = '<option value="">Selecciona un socio</option>' + (data.socios || []).map((row) => (
      `<option value="${row.id}">${row.nombre} (#${row.id})</option>`
    )).join('');
    if (socioSelect) {
      const current = socioSelect.value;
      socioSelect.innerHTML = socioOptions;
      if (current) socioSelect.value = current;
    }
    if (cuentaSocioSelect) {
      const current = cuentaSocioSelect.value;
      cuentaSocioSelect.innerHTML = socioOptions;
      if (current) cuentaSocioSelect.value = current;
    }
    if (cuentaSelect) {
      const current = cuentaSelect.value;
      cuentaSelect.innerHTML = '<option value="">Selecciona una cuenta</option>' + (data.cuentas || []).map((row) => (
        `<option value="${row.id}">Cuenta #${row.id} / Socio #${row.socio_id} / ${row.tipo}</option>`
      )).join('');
      if (current) cuentaSelect.value = current;
    }
    if (pagoCreditoSelect) {
      const current = pagoCreditoSelect.value;
      const creditos = await apiGet('/api/intelicoop/creditos');
      pagoCreditoSelect.innerHTML = '<option value="">Selecciona un credito</option>' + (creditos || []).map((row) => (
        `<option value="${row.id}">Credito #${row.id} / ${row.socio_nombre || 'Sin socio'}</option>`
      )).join('');
      if (current) pagoCreditoSelect.value = current;
    }
    if (contactoSocioSelect) {
      const current = contactoSocioSelect.value;
      contactoSocioSelect.innerHTML = socioOptions;
      if (current) contactoSocioSelect.value = current;
    }
    if (seguimientoSocioSelect) {
      const current = seguimientoSocioSelect.value;
      seguimientoSocioSelect.innerHTML = socioOptions;
      if (current) seguimientoSocioSelect.value = current;
    }
    const campanias = await apiGet('/api/intelicoop/campanas');
    const campaniaOptions = '<option value="">Selecciona una campana</option>' + (campanias || []).map((row) => (
      `<option value="${row.id}">${row.nombre} (#${row.id})</option>`
    )).join('');
    const contactoCampaniaSelect = document.getElementById('intelicoop-contacto-campania');
    const seguimientoCampaniaSelect = document.getElementById('intelicoop-seguimiento-campania');
    if (contactoCampaniaSelect) {
      const current = contactoCampaniaSelect.value;
      contactoCampaniaSelect.innerHTML = campaniaOptions;
      if (current) contactoCampaniaSelect.value = current;
    }
    if (seguimientoCampaniaSelect) {
      const current = seguimientoCampaniaSelect.value;
      seguimientoCampaniaSelect.innerHTML = campaniaOptions;
      if (current) seguimientoCampaniaSelect.value = current;
    }
  };

  const loadKpis = async () => {
    const data = await apiGet('/api/intelicoop/dashboard/resumen');
    const kpis = document.getElementById('intelicoop-kpis');
    if (!kpis) return;
    kpis.innerHTML = [
      ['Socios', data.socios || 0],
      ['Creditos', data.creditos || 0],
      ['Campanas', data.campanas || 0],
      ['Scoring', data.scoring_total || 0],
    ].map(([label, value]) => (
      `<article class="intelicoop-card"><span class="intelicoop-kpi-label">${label}</span><strong class="intelicoop-kpi-value">${value}</strong></article>`
    )).join('');
  };

  const loadDashboard = async () => {
    setStatus('intelicoop-dashboard-status', 'Cargando resumen del modulo...');
    const data = await apiGet('/api/intelicoop/dashboard/resumen');
    const mount = document.getElementById('intelicoop-dashboard-content');
    if (mount) {
      const semaforoBadge = (value) => {
        const palette = {
          verde: '#166534',
          amarillo: '#a16207',
          rojo: '#991b1b',
        };
        const bg = {
          verde: '#dcfce7',
          amarillo: '#fef3c7',
          rojo: '#fee2e2',
        };
        const color = palette[value] || '#334155';
        const background = bg[value] || '#e2e8f0';
        return `<span style="display:inline-flex;padding:4px 8px;border-radius:999px;background:${background};color:${color};font-size:12px;font-weight:700;text-transform:uppercase;">${value}</span>`;
      };
      mount.innerHTML = `
        <div class="intelicoop-grid">
          <article class="intelicoop-card"><span class="intelicoop-kpi-label">Prospectos</span><strong class="intelicoop-kpi-value">${data.prospectos || 0}</strong></article>
          <article class="intelicoop-card"><span class="intelicoop-kpi-label">Riesgo bajo</span><strong class="intelicoop-kpi-value">${(data.riesgo || {}).bajo || 0}</strong></article>
          <article class="intelicoop-card"><span class="intelicoop-kpi-label">Riesgo medio</span><strong class="intelicoop-kpi-value">${(data.riesgo || {}).medio || 0}</strong></article>
          <article class="intelicoop-card"><span class="intelicoop-kpi-label">Riesgo alto</span><strong class="intelicoop-kpi-value">${(data.riesgo || {}).alto || 0}</strong></article>
        </div>
        <div class="intelicoop-grid" style="margin-top:16px;">
          <article class="intelicoop-card">
            <span class="intelicoop-kpi-label">Salud de cartera</span>
            <p style="margin:0 0 8px;">Cartera total: $${Number((data.salud_cartera || {}).cartera_total || 0).toFixed(2)}</p>
            <p style="margin:0 0 8px;">Cartera vigente: $${Number((data.salud_cartera || {}).cartera_vigente || 0).toFixed(2)}</p>
            <p style="margin:0;">IMOR estimado: ${Number((data.salud_cartera || {}).imor_pct || 0).toFixed(2)}%</p>
          </article>
          <article class="intelicoop-card">
            <span class="intelicoop-kpi-label">Colocacion</span>
            <p style="margin:0 0 8px;">Solicitados: ${(data.colocacion || {}).solicitados || 0}</p>
            <p style="margin:0 0 8px;">Aprobados: ${(data.colocacion || {}).aprobados || 0}</p>
            <p style="margin:0;">Ticket promedio: $${Number((data.colocacion || {}).ticket_promedio || 0).toFixed(2)}</p>
          </article>
          <article class="intelicoop-card">
            <span class="intelicoop-kpi-label">Captacion</span>
            <p style="margin:0 0 8px;">Depositos: $${Number((data.captacion || {}).depositos_total || 0).toFixed(2)}</p>
            <p style="margin:0 0 8px;">Retiros: $${Number((data.captacion || {}).retiros_total || 0).toFixed(2)}</p>
            <p style="margin:0;">Neta: $${Number((data.captacion || {}).captacion_neta || 0).toFixed(2)}</p>
          </article>
          <article class="intelicoop-card">
            <span class="intelicoop-kpi-label">Comercial</span>
            <p style="margin:0 0 8px;">Campanas activas: ${(data.comercial || {}).campanas_activas || 0}</p>
            <p style="margin:0 0 8px;">Prospectos: ${(data.comercial || {}).prospectos_total || 0}</p>
            <p style="margin:0 0 8px;">Contactos: ${(data.comercial || {}).contactos_total || 0}</p>
            <p style="margin:0 0 8px;">Conversiones: ${(data.comercial || {}).conversiones_total || 0}</p>
            <p style="margin:0;">Conversion %: ${Number((data.comercial || {}).conversion_pct || 0).toFixed(2)}%</p>
          </article>
        </div>
        <div class="intelicoop-card" style="margin-top:16px;">
          <span class="intelicoop-kpi-label">Semaforos</span>
          <div class="intelicoop-grid">
            ${(data.semaforos || []).map((item) => `
              <div style="border:1px solid rgba(15,23,42,.08);border-radius:12px;padding:12px;background:#fff;">
                <div style="display:flex;justify-content:space-between;gap:10px;align-items:center;">
                  <strong>${item.label}</strong>
                  ${semaforoBadge(item.semaforo)}
                </div>
                <p style="margin:8px 0 0;">Valor: ${item.valor}</p>
                <p style="margin:4px 0 0;">Meta: ${item.meta}</p>
              </div>
            `).join('')}
          </div>
        </div>
      `;
    }
    setStatus('intelicoop-dashboard-status', 'Modulo conectado al backend principal de SIPET.');
  };

  const loadSocios = async () => {
    setStatus('intelicoop-socios-status', 'Cargando socios...');
    const rows = await apiGet('/api/intelicoop/socios');
    renderTable('intelicoop-socios-table', [
      { key: 'id', label: 'ID' },
      { key: 'nombre', label: 'Nombre' },
      { key: 'email', label: 'Email' },
      { key: 'segmento', label: 'Segmento' },
    ], rows);
    setStatus('intelicoop-socios-status', `${rows.length} socios cargados.`);
  };

  const loadCreditos = async () => {
    setStatus('intelicoop-creditos-status', 'Cargando creditos...');
    const rows = await apiGet('/api/intelicoop/creditos');
    const mount = document.getElementById('intelicoop-creditos-table');
    if (!mount) return;
    if (!rows.length) {
      mount.innerHTML = '<p class="intelicoop-status">Sin datos todavia.</p>';
    } else {
      const head = ['ID', 'Socio', 'Monto', 'Estado', 'Acciones'].map((label) => `<th>${label}</th>`).join('');
      const body = rows.map((row) => `
        <tr>
          <td>${row.id ?? ''}</td>
          <td>${row.socio_nombre ?? ''}</td>
          <td>${row.monto ?? ''}</td>
          <td>${row.estado ?? ''}</td>
          <td><button type="button" class="intelicoop-detail-credito" data-credito-id="${row.id}">Ver detalle</button></td>
        </tr>
      `).join('');
      mount.innerHTML = `<table class="intelicoop-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
      mount.querySelectorAll('.intelicoop-detail-credito').forEach((button) => {
        button.addEventListener('click', () => {
          const creditoId = Number(button.getAttribute('data-credito-id'));
          loadCreditoDetail(creditoId).catch(() => {});
        });
      });
    }
    setStatus('intelicoop-creditos-status', `${rows.length} creditos cargados.`);
  };

  const loadCreditoDetail = async (creditoId) => {
    const statusNode = document.getElementById('intelicoop-credito-detail-status');
    const mount = document.getElementById('intelicoop-credito-detail');
    if (statusNode) statusNode.textContent = 'Cargando detalle del credito...';
    const data = await apiGet(`/api/intelicoop/creditos/${creditoId}/detalle`);
    if (mount) {
      const pagos = data.historial_pagos || [];
      mount.innerHTML = `
        <div class="intelicoop-grid">
          <article class="intelicoop-card"><span class="intelicoop-kpi-label">Credito</span><strong class="intelicoop-kpi-value">#${data.id}</strong></article>
          <article class="intelicoop-card"><span class="intelicoop-kpi-label">Monto</span><strong class="intelicoop-kpi-value">$${Number(data.monto || 0).toFixed(2)}</strong></article>
          <article class="intelicoop-card"><span class="intelicoop-kpi-label">Pagado</span><strong class="intelicoop-kpi-value">$${Number((data.resumen_pagos || {}).monto_pagado || 0).toFixed(2)}</strong></article>
          <article class="intelicoop-card"><span class="intelicoop-kpi-label">Saldo estimado</span><strong class="intelicoop-kpi-value">$${Number((data.resumen_pagos || {}).saldo_estimado || 0).toFixed(2)}</strong></article>
        </div>
      `;
      if (pagos.length) {
        mount.innerHTML += `
          <div style="margin-top:16px;">
            <h4>Historial de pagos</h4>
            <table class="intelicoop-table">
              <thead><tr><th>ID</th><th>Monto</th><th>Fecha</th></tr></thead>
              <tbody>
                ${pagos.map((row) => `<tr><td>${row.id}</td><td>${row.monto}</td><td>${(row.fecha || '').slice(0, 19)}</td></tr>`).join('')}
              </tbody>
            </table>
          </div>
        `;
      }
    }
    if (statusNode) statusNode.textContent = `Detalle del credito #${data.id}.`;
    const pagoCreditoSelect = document.getElementById('intelicoop-pago-credito');
    if (pagoCreditoSelect) pagoCreditoSelect.value = String(data.id);
  };

  const loadAhorros = async () => {
    setStatus('intelicoop-ahorros-status', 'Cargando resumen de ahorros...');
    const [data, cuentas, movimientos] = await Promise.all([
      apiGet('/api/intelicoop/ahorros/resumen'),
      apiGet('/api/intelicoop/ahorros/cuentas'),
      apiGet('/api/intelicoop/ahorros/transacciones'),
    ]);
    const mount = document.getElementById('intelicoop-ahorros-content');
    if (mount) {
      mount.innerHTML = `
        <div class="intelicoop-grid">
          <article class="intelicoop-card"><span class="intelicoop-kpi-label">Cuentas</span><strong class="intelicoop-kpi-value">${data.cuentas || 0}</strong></article>
          <article class="intelicoop-card"><span class="intelicoop-kpi-label">Movimientos</span><strong class="intelicoop-kpi-value">${data.movimientos || 0}</strong></article>
          <article class="intelicoop-card"><span class="intelicoop-kpi-label">Captacion</span><strong class="intelicoop-kpi-value">$${Number(data.captacion || 0).toFixed(2)}</strong></article>
        </div>
      `;
    }
    renderTable('intelicoop-cuentas-table', [
      { key: 'id', label: 'ID' },
      { key: 'socio_nombre', label: 'Socio' },
      { key: 'tipo', label: 'Tipo' },
      { key: 'saldo', label: 'Saldo' },
    ], cuentas);
    renderTable('intelicoop-transacciones-table', [
      { key: 'id', label: 'ID' },
      { key: 'socio_nombre', label: 'Socio' },
      { key: 'tipo', label: 'Tipo' },
      { key: 'monto', label: 'Monto' },
    ], movimientos);
    setStatus('intelicoop-ahorros-status', 'Resumen de ahorros disponible.');
  };

  const loadCampanas = async () => {
    setStatus('intelicoop-campanas-status', 'Cargando campanas...');
    const [rows, contactos, seguimientos] = await Promise.all([
      apiGet('/api/intelicoop/campanas'),
      apiGet('/api/intelicoop/campanas/contactos'),
      apiGet('/api/intelicoop/campanas/seguimientos'),
    ]);
    renderTable('intelicoop-campanas-table', [
      { key: 'id', label: 'ID' },
      { key: 'nombre', label: 'Nombre' },
      { key: 'tipo', label: 'Tipo' },
      { key: 'estado', label: 'Estado' },
    ], rows);
    renderTable('intelicoop-contactos-table', [
      { key: 'campania_nombre', label: 'Campana' },
      { key: 'socio_nombre', label: 'Socio' },
      { key: 'canal', label: 'Canal' },
      { key: 'estado_contacto', label: 'Estado' },
    ], contactos);
    renderTable('intelicoop-seguimientos-table', [
      { key: 'campania_nombre', label: 'Campana' },
      { key: 'socio_nombre', label: 'Socio' },
      { key: 'etapa', label: 'Etapa' },
      { key: 'conversion', label: 'Conversion' },
      { key: 'monto_colocado', label: 'Monto' },
    ], seguimientos.map((row) => ({ ...row, conversion: row.conversion ? 'Si' : 'No' })));
    setStatus('intelicoop-campanas-status', `${rows.length} campanas cargadas.`);
  };

  const loadProspectos = async () => {
    setStatus('intelicoop-prospectos-status', 'Cargando prospectos...');
    const rows = await apiGet('/api/intelicoop/prospectos');
    renderTable('intelicoop-prospectos-table', [
      { key: 'id', label: 'ID' },
      { key: 'nombre', label: 'Nombre' },
      { key: 'fuente', label: 'Fuente' },
      { key: 'score_propension', label: 'Score' },
    ], rows);
    setStatus('intelicoop-prospectos-status', `${rows.length} prospectos cargados.`);
  };

  const loadScoring = async () => {
    setStatus('intelicoop-scoring-status', 'Cargando resumen de scoring...');
    const data = await apiGet('/api/intelicoop/scoring/resumen');
    const mount = document.getElementById('intelicoop-scoring-content');
    if (mount) {
      mount.innerHTML = `
        <div class="intelicoop-grid">
          <article class="intelicoop-card"><span class="intelicoop-kpi-label">Inferencias</span><strong class="intelicoop-kpi-value">${data.total_inferencias || 0}</strong></article>
          <article class="intelicoop-card"><span class="intelicoop-kpi-label">Score promedio</span><strong class="intelicoop-kpi-value">${Number(data.score_promedio || 0).toFixed(2)}</strong></article>
          <article class="intelicoop-card"><span class="intelicoop-kpi-label">Aprobar</span><strong class="intelicoop-kpi-value">${(data.por_recomendacion || {}).aprobar || 0}</strong></article>
          <article class="intelicoop-card"><span class="intelicoop-kpi-label">Rechazar</span><strong class="intelicoop-kpi-value">${(data.por_recomendacion || {}).rechazar || 0}</strong></article>
        </div>
      `;
    }
    setStatus('intelicoop-scoring-status', 'Resumen de scoring disponible.');
  };

  const bindScoringForm = () => {
    const form = document.getElementById('intelicoop-scoring-form');
    const result = document.getElementById('intelicoop-scoring-result');
    if (!form || !result) return;
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      const payload = {
        solicitud_id: formData.get('solicitud_id') || null,
        socio_id: formData.get('socio_id') ? Number(formData.get('socio_id')) : null,
        ingreso_mensual: Number(formData.get('ingreso_mensual') || 0),
        deuda_actual: Number(formData.get('deuda_actual') || 0),
        antiguedad_meses: Number(formData.get('antiguedad_meses') || 0),
      };
      result.innerHTML = '<p class="intelicoop-status">Evaluando scoring...</p>';
      try {
        const data = await apiPost('/api/intelicoop/scoring/evaluar', payload);
        result.innerHTML = `
          <div class="intelicoop-card">
            <strong>Resultado</strong>
            <p>Score: ${Number(data.score || 0).toFixed(4)}</p>
            <p>Recomendacion: ${data.recomendacion || '-'}</p>
            <p>Riesgo: ${data.riesgo || '-'}</p>
            <p>Version: ${data.model_version || '-'}</p>
          </div>
        `;
        loadScoring().catch(() => {});
        loadDashboard().catch(() => {});
        loadKpis().catch(() => {});
      } catch (error) {
        result.innerHTML = `<p class="intelicoop-status">No se pudo evaluar el scoring: ${error.message}</p>`;
      }
    });
  };

  const bindSociosForm = () => {
    const form = document.getElementById('intelicoop-socios-form');
    if (!form) return;
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      try {
        await apiPost('/api/intelicoop/socios', {
          nombre: formData.get('nombre'),
          email: formData.get('email'),
          telefono: formData.get('telefono'),
          direccion: formData.get('direccion'),
          segmento: formData.get('segmento'),
        });
        form.reset();
        form.querySelector('[name="segmento"]').value = 'inactivo';
        setFormResult('intelicoop-socios-form-result', 'Socio creado correctamente.', false);
        await Promise.all([loadSocios(), loadCatalogs(), loadDashboard(), loadKpis()]);
      } catch (error) {
        setFormResult('intelicoop-socios-form-result', `No se pudo crear el socio: ${error.message}`, true);
      }
    });
  };

  const bindCreditosForm = () => {
    const form = document.getElementById('intelicoop-creditos-form');
    if (!form) return;
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      try {
        const response = await apiPost('/api/intelicoop/creditos', {
          socio_id: Number(formData.get('socio_id')),
          monto: Number(formData.get('monto') || 0),
          plazo: Number(formData.get('plazo') || 0),
          ingreso_mensual: Number(formData.get('ingreso_mensual') || 0),
          deuda_actual: Number(formData.get('deuda_actual') || 0),
          antiguedad_meses: Number(formData.get('antiguedad_meses') || 0),
          estado: formData.get('estado'),
        });
        form.reset();
        form.querySelector('[name="estado"]').value = 'solicitado';
        const scoring = response.scoring || {};
        setFormResult(
          'intelicoop-creditos-form-result',
          `Credito registrado. Scoring: ${Number(scoring.score || 0).toFixed(4)} / ${scoring.recomendacion || 'sin dato'} / ${scoring.riesgo || 'sin dato'}.`,
          false
        );
        await Promise.all([loadCreditos(), loadScoring(), loadDashboard(), loadKpis()]);
      } catch (error) {
        setFormResult('intelicoop-creditos-form-result', `No se pudo registrar el credito: ${error.message}`, true);
      }
    });
  };

  const bindCampanasForm = () => {
    const form = document.getElementById('intelicoop-campanas-form');
    if (!form) return;
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      try {
        await apiPost('/api/intelicoop/campanas', {
          nombre: formData.get('nombre'),
          tipo: formData.get('tipo'),
          fecha_inicio: formData.get('fecha_inicio'),
          fecha_fin: formData.get('fecha_fin'),
          estado: formData.get('estado'),
        });
        form.reset();
        form.querySelector('[name="estado"]').value = 'borrador';
        setFormResult('intelicoop-campanas-form-result', 'Campana creada correctamente.', false);
        await Promise.all([loadCampanas(), loadDashboard(), loadKpis()]);
      } catch (error) {
        setFormResult('intelicoop-campanas-form-result', `No se pudo crear la campana: ${error.message}`, true);
      }
    });
  };

  const bindContactosForm = () => {
    const form = document.getElementById('intelicoop-contactos-form');
    if (!form) return;
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      try {
        await apiPost('/api/intelicoop/campanas/contactos', {
          campania_id: Number(formData.get('campania_id')),
          socio_id: Number(formData.get('socio_id')),
          ejecutivo_id: formData.get('ejecutivo_id'),
          canal: formData.get('canal'),
          estado_contacto: formData.get('estado_contacto'),
        });
        form.reset();
        form.querySelector('[name="ejecutivo_id"]').value = 'ejecutivo_general';
        form.querySelector('[name="canal"]').value = 'telefono';
        form.querySelector('[name="estado_contacto"]').value = 'pendiente';
        setFormResult('intelicoop-contactos-form-result', 'Contacto comercial registrado.', false);
        await Promise.all([loadCatalogs(), loadCampanas(), loadDashboard(), loadKpis()]);
      } catch (error) {
        setFormResult('intelicoop-contactos-form-result', `No se pudo registrar el contacto: ${error.message}`, true);
      }
    });
  };

  const bindSeguimientosForm = () => {
    const form = document.getElementById('intelicoop-seguimientos-form');
    if (!form) return;
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      try {
        await apiPost('/api/intelicoop/campanas/seguimientos', {
          campania_id: Number(formData.get('campania_id')),
          socio_id: Number(formData.get('socio_id')),
          lista: formData.get('lista'),
          etapa: formData.get('etapa'),
          conversion: String(formData.get('conversion')) === '1',
          monto_colocado: Number(formData.get('monto_colocado') || 0),
        });
        form.reset();
        form.querySelector('[name="lista"]').value = 'general';
        form.querySelector('[name="etapa"]').value = 'contactado';
        form.querySelector('[name="conversion"]').value = '0';
        form.querySelector('[name="monto_colocado"]').value = '0';
        setFormResult('intelicoop-seguimientos-form-result', 'Seguimiento comercial registrado.', false);
        await Promise.all([loadCatalogs(), loadCampanas(), loadDashboard(), loadKpis()]);
      } catch (error) {
        setFormResult('intelicoop-seguimientos-form-result', `No se pudo registrar el seguimiento: ${error.message}`, true);
      }
    });
  };

  const bindProspectosForm = () => {
    const form = document.getElementById('intelicoop-prospectos-form');
    if (!form) return;
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      try {
        await apiPost('/api/intelicoop/prospectos', {
          nombre: formData.get('nombre'),
          telefono: formData.get('telefono'),
          direccion: formData.get('direccion'),
          fuente: formData.get('fuente'),
          score_propension: Number(formData.get('score_propension') || 0),
        });
        form.reset();
        setFormResult('intelicoop-prospectos-form-result', 'Prospecto creado correctamente.', false);
        await Promise.all([loadProspectos(), loadDashboard(), loadKpis()]);
      } catch (error) {
        setFormResult('intelicoop-prospectos-form-result', `No se pudo crear el prospecto: ${error.message}`, true);
      }
    });
  };

  const bindCuentasForm = () => {
    const form = document.getElementById('intelicoop-cuentas-form');
    if (!form) return;
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      try {
        await apiPost('/api/intelicoop/ahorros/cuentas', {
          socio_id: Number(formData.get('socio_id')),
          tipo: formData.get('tipo'),
          saldo: Number(formData.get('saldo') || 0),
        });
        form.reset();
        form.querySelector('[name="tipo"]').value = 'ahorro';
        setFormResult('intelicoop-cuentas-form-result', 'Cuenta creada correctamente.', false);
        await Promise.all([loadCatalogs(), loadAhorros(), loadDashboard(), loadKpis()]);
      } catch (error) {
        setFormResult('intelicoop-cuentas-form-result', `No se pudo crear la cuenta: ${error.message}`, true);
      }
    });
  };

  const bindTransaccionesForm = () => {
    const form = document.getElementById('intelicoop-transacciones-form');
    if (!form) return;
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      try {
        await apiPost('/api/intelicoop/ahorros/transacciones', {
          cuenta_id: Number(formData.get('cuenta_id')),
          tipo: formData.get('tipo'),
          monto: Number(formData.get('monto') || 0),
        });
        form.reset();
        form.querySelector('[name="tipo"]').value = 'deposito';
        setFormResult('intelicoop-transacciones-form-result', 'Movimiento registrado correctamente.', false);
        await Promise.all([loadCatalogs(), loadAhorros(), loadDashboard(), loadKpis()]);
      } catch (error) {
        setFormResult('intelicoop-transacciones-form-result', `No se pudo registrar el movimiento: ${error.message}`, true);
      }
    });
  };

  const bindPagosForm = () => {
    const form = document.getElementById('intelicoop-pagos-form');
    if (!form) return;
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      const creditoId = Number(formData.get('credito_id'));
      try {
        await apiPost('/api/intelicoop/creditos/pagos', {
          credito_id: creditoId,
          monto: Number(formData.get('monto') || 0),
        });
        form.reset();
        setFormResult('intelicoop-pagos-form-result', 'Pago registrado correctamente.', false);
        await Promise.all([loadCreditos(), loadCatalogs(), loadDashboard(), loadKpis()]);
        if (creditoId) {
          await loadCreditoDetail(creditoId);
        }
      } catch (error) {
        setFormResult('intelicoop-pagos-form-result', `No se pudo registrar el pago: ${error.message}`, true);
      }
    });
  };

  const bootstrap = async () => {
    updateTabs();
    bindScoringForm();
    bindSociosForm();
    bindCreditosForm();
    bindPagosForm();
    bindCuentasForm();
    bindTransaccionesForm();
    bindCampanasForm();
    bindContactosForm();
    bindSeguimientosForm();
    bindProspectosForm();
    try {
      await Promise.all([
        loadCatalogs(),
        loadKpis(),
        loadDashboard(),
        loadSocios(),
        loadCreditos(),
        loadAhorros(),
        loadCampanas(),
        loadProspectos(),
        loadScoring(),
      ]);
    } catch (error) {
      console.error('Intelicoop bootstrap error', error);
    }
  };

  bootstrap();
})();
