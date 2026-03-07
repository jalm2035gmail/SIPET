(function () {
  'use strict';

  // ── HTTP helpers ────────────────────────────────────────────────────────────

  function req(method, url, body) {
    var opts = { method: method, headers: {} };
    if (body) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    return fetch(url, opts).then(function (r) {
      if (!r.ok) return r.json().then(function (d) { throw new Error(d.detail || r.status); });
      return r.json();
    });
  }
  var apiGet    = function (url)     { return req('GET',    url); };
  var apiPost   = function (url, b)  { return req('POST',   url, b); };
  var apiPut    = function (url, b)  { return req('PUT',    url, b); };
  var apiDelete = function (url)     { return req('DELETE', url); };

  // ── DOM helpers ─────────────────────────────────────────────────────────────

  function qs(sel, ctx) { return (ctx || document).querySelector(sel); }
  function el(id)       { return document.getElementById(id); }
  function status(id, msg) { var e = el(id); if (e) e.textContent = msg; }
  function formToObj(form) {
    var data = {};
    new FormData(form).forEach(function (v, k) {
      data[k] = v === '' ? null : v;
    });
    return data;
  }
  function badge(val, cls) {
    return '<span class="aud-badge ' + (cls || val || '') + '">' + (val || '—') + '</span>';
  }
  function progress(pct) {
    return '<span class="aud-progress"><span class="aud-progress-fill" style="width:' + pct + '%"></span></span> ' + pct + '%';
  }

  // ── Cache de datos ──────────────────────────────────────────────────────────

  var _auditorias    = [];
  var _hallazgos     = [];
  var _recomendaciones = [];

  // ── Navegación ───────────────────────────────────────────────────────────────

  function initNav() {
    var nav = el('aud-nav');
    if (!nav) return;
    nav.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-panel]');
      if (!btn) return;
      var panelId = btn.getAttribute('data-panel');
      nav.querySelectorAll('button').forEach(function (b) { b.classList.remove('is-active'); });
      btn.classList.add('is-active');
      document.querySelectorAll('.aud-panel').forEach(function (p) {
        p.classList.toggle('is-active', p.getAttribute('data-panel-id') === panelId);
      });
      if (panelId === 'hallazgos')       { loadHallazgos(); }
      if (panelId === 'recomendaciones') { loadRecomendaciones(); }
      if (panelId === 'seguimiento')     { loadSeguimiento(); }
    });
  }

  // ── Resumen / KPIs ───────────────────────────────────────────────────────────

  function loadResumen() {
    apiGet('/api/auditoria/resumen').then(function (d) {
      el('aud-kpi-total').textContent     = d.total_auditorias;
      el('aud-kpi-en-proceso').textContent = d.auditorias_en_proceso;
      el('aud-kpi-hallazgos').textContent  = d.hallazgos_abiertos;
      el('aud-kpi-criticos').textContent   = d.hallazgos_criticos;
      el('aud-kpi-recs').textContent       = d.recomendaciones_pendientes;
    }).catch(function () {});
  }

  // ── Auditorías ───────────────────────────────────────────────────────────────

  function loadAuditorias() {
    status('aud-auditorias-status', 'Cargando...');
    apiGet('/api/auditoria/auditorias').then(function (list) {
      _auditorias = list;
      rebuildAuditoriaSelects();
      var container = el('aud-auditorias-table');
      if (!list.length) { status('aud-auditorias-status', 'Sin auditorías registradas.'); container.innerHTML = ''; return; }
      status('aud-auditorias-status', '');
      var rows = list.map(function (a) {
        return '<tr>' +
          '<td>' + a.codigo + '</td>' +
          '<td>' + a.nombre + '</td>' +
          '<td>' + badge(a.tipo) + '</td>' +
          '<td>' + badge(a.estado) + '</td>' +
          '<td>' + (a.area_auditada || '—') + '</td>' +
          '<td>' + (a.responsable || '—') + '</td>' +
          '<td>' + (a.fecha_inicio || '—') + '</td>' +
          '<td><button class="aud-actions button is-danger is-sm" data-del-aud="' + a.id + '">Eliminar</button></td>' +
          '</tr>';
      });
      container.innerHTML = '<table class="aud-table"><thead><tr>' +
        '<th>Código</th><th>Nombre</th><th>Tipo</th><th>Estado</th><th>Área</th><th>Responsable</th><th>Inicio</th><th></th>' +
        '</tr></thead><tbody>' + rows.join('') + '</tbody></table>';
    }).catch(function (err) { status('aud-auditorias-status', 'Error: ' + err.message); });
  }

  function rebuildAuditoriaSelects() {
    ['aud-hall-auditoria-select', 'aud-hall-filter-aud', 'aud-seg-filter-aud-indirect'].forEach(function (id) {
      var sel = el(id);
      if (!sel) return;
      var cur = sel.value;
      var base = id === 'aud-hall-auditoria-select' ? '<option value="">Auditoría *</option>' : '<option value="">Todas las auditorías</option>';
      sel.innerHTML = base + _auditorias.map(function (a) {
        return '<option value="' + a.id + '">' + a.codigo + ' — ' + a.nombre + '</option>';
      }).join('');
      sel.value = cur;
    });
  }

  // submit auditoría
  function initFormAuditoria() {
    var form = el('aud-form-auditoria');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var data = formToObj(form);
      apiPost('/api/auditoria/auditorias', data).then(function () {
        status('aud-auditoria-form-status', '✓ Auditoría registrada.');
        form.reset();
        loadAuditorias();
        loadResumen();
      }).catch(function (err) { status('aud-auditoria-form-status', 'Error: ' + err.message); });
    });
  }

  // delete auditoría
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-del-aud]');
    if (!btn) return;
    if (!confirm('¿Eliminar esta auditoría y todos sus hallazgos?')) return;
    apiDelete('/api/auditoria/auditorias/' + btn.getAttribute('data-del-aud')).then(function () {
      loadAuditorias();
      loadHallazgos();
      loadResumen();
    }).catch(function (err) { alert('Error: ' + err.message); });
  });

  // ── Hallazgos ────────────────────────────────────────────────────────────────

  function loadHallazgos() {
    var audId   = (el('aud-hall-filter-aud')    || {}).value || '';
    var estado  = (el('aud-hall-filter-estado') || {}).value || '';
    var url = '/api/auditoria/hallazgos';
    var params = [];
    if (audId)  params.push('auditoria_id=' + audId);
    if (estado) params.push('estado=' + encodeURIComponent(estado));
    if (params.length) url += '?' + params.join('&');

    status('aud-hallazgos-status', 'Cargando...');
    apiGet(url).then(function (list) {
      _hallazgos = list;
      rebuildHallazgoSelects();
      var container = el('aud-hallazgos-table');
      if (!list.length) { status('aud-hallazgos-status', 'Sin hallazgos.'); container.innerHTML = ''; return; }
      status('aud-hallazgos-status', '');
      var rows = list.map(function (h) {
        return '<tr>' +
          '<td>' + (h.codigo || '—') + '</td>' +
          '<td>' + h.titulo + '</td>' +
          '<td><small>' + (h.auditoria_nombre || '—') + '</small></td>' +
          '<td>' + badge(h.nivel_riesgo) + '</td>' +
          '<td>' + badge(h.estado) + '</td>' +
          '<td>' + (h.responsable || '—') + '</td>' +
          '<td>' + (h.fecha_limite || '—') + '</td>' +
          '<td><button class="aud-actions button is-danger is-sm" data-del-hall="' + h.id + '">Eliminar</button></td>' +
          '</tr>';
      });
      container.innerHTML = '<table class="aud-table"><thead><tr>' +
        '<th>Código</th><th>Título</th><th>Auditoría</th><th>Riesgo</th><th>Estado</th><th>Responsable</th><th>Límite</th><th></th>' +
        '</tr></thead><tbody>' + rows.join('') + '</tbody></table>';
    }).catch(function (err) { status('aud-hallazgos-status', 'Error: ' + err.message); });
  }

  function rebuildHallazgoSelects() {
    ['aud-rec-hallazgo-select'].forEach(function (id) {
      var sel = el(id);
      if (!sel) return;
      var cur = sel.value;
      sel.innerHTML = '<option value="">Hallazgo *</option>' + _hallazgos.map(function (h) {
        return '<option value="' + h.id + '">' + (h.codigo ? h.codigo + ' — ' : '') + h.titulo + '</option>';
      }).join('');
      sel.value = cur;
    });
  }

  function initFormHallazgo() {
    var form = el('aud-form-hallazgo');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var data = formToObj(form);
      if (data.auditoria_id) data.auditoria_id = parseInt(data.auditoria_id);
      apiPost('/api/auditoria/hallazgos', data).then(function () {
        status('aud-hallazgo-form-status', '✓ Hallazgo registrado.');
        form.reset();
        loadHallazgos();
        loadResumen();
      }).catch(function (err) { status('aud-hallazgo-form-status', 'Error: ' + err.message); });
    });
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-del-hall]');
    if (!btn) return;
    if (!confirm('¿Eliminar este hallazgo y sus recomendaciones?')) return;
    apiDelete('/api/auditoria/hallazgos/' + btn.getAttribute('data-del-hall')).then(function () {
      loadHallazgos();
      loadResumen();
    }).catch(function (err) { alert('Error: ' + err.message); });
  });

  // filtros hallazgos
  function initHallazgoFilters() {
    ['aud-hall-filter-aud', 'aud-hall-filter-estado'].forEach(function (id) {
      var sel = el(id);
      if (sel) sel.addEventListener('change', loadHallazgos);
    });
  }

  // ── Recomendaciones ──────────────────────────────────────────────────────────

  function loadRecomendaciones() {
    var estado = (el('aud-rec-filter-estado') || {}).value || '';
    var url = '/api/auditoria/recomendaciones';
    if (estado) url += '?estado=' + encodeURIComponent(estado);

    status('aud-recs-status', 'Cargando...');
    apiGet(url).then(function (list) {
      _recomendaciones = list;
      rebuildRecSelects();
      var container = el('aud-recs-table');
      if (!list.length) { status('aud-recs-status', 'Sin recomendaciones.'); container.innerHTML = ''; return; }
      status('aud-recs-status', '');
      var rows = list.map(function (r) {
        return '<tr>' +
          '<td><small>' + (r.hallazgo_titulo || '—') + '</small></td>' +
          '<td style="max-width:260px;">' + r.descripcion + '</td>' +
          '<td>' + badge(r.prioridad) + '</td>' +
          '<td>' + badge(r.estado) + '</td>' +
          '<td>' + progress(r.porcentaje_avance) + '</td>' +
          '<td>' + (r.responsable || '—') + '</td>' +
          '<td>' + (r.fecha_compromiso || '—') + '</td>' +
          '<td><button class="aud-actions button is-danger is-sm" data-del-rec="' + r.id + '">Eliminar</button></td>' +
          '</tr>';
      });
      container.innerHTML = '<table class="aud-table"><thead><tr>' +
        '<th>Hallazgo</th><th>Recomendación</th><th>Prioridad</th><th>Estado</th><th>Avance</th><th>Responsable</th><th>Compromiso</th><th></th>' +
        '</tr></thead><tbody>' + rows.join('') + '</tbody></table>';
    }).catch(function (err) { status('aud-recs-status', 'Error: ' + err.message); });
  }

  function rebuildRecSelects() {
    ['aud-seg-rec-select'].forEach(function (id) {
      var sel = el(id);
      if (!sel) return;
      var cur = sel.value;
      sel.innerHTML = '<option value="">Recomendación *</option>' + _recomendaciones.map(function (r) {
        var label = (r.hallazgo_titulo ? r.hallazgo_titulo + ' → ' : '') +
          r.descripcion.substring(0, 50) + (r.descripcion.length > 50 ? '…' : '');
        return '<option value="' + r.id + '">' + label + '</option>';
      }).join('');
      sel.value = cur;
    });
    // also rebuild filter in seguimiento
    var filterSel = el('aud-seg-filter-rec');
    if (filterSel) {
      var cur = filterSel.value;
      filterSel.innerHTML = '<option value="">Todas las recomendaciones</option>' +
        _recomendaciones.map(function (r) {
          return '<option value="' + r.id + '">' + r.descripcion.substring(0, 60) + '</option>';
        }).join('');
      filterSel.value = cur;
    }
  }

  function initFormRecomendacion() {
    var form = el('aud-form-recomendacion');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var data = formToObj(form);
      if (data.hallazgo_id) data.hallazgo_id = parseInt(data.hallazgo_id);
      if (data.porcentaje_avance !== null) data.porcentaje_avance = parseInt(data.porcentaje_avance) || 0;
      apiPost('/api/auditoria/recomendaciones', data).then(function () {
        status('aud-rec-form-status', '✓ Recomendación registrada.');
        form.reset();
        loadRecomendaciones();
      }).catch(function (err) { status('aud-rec-form-status', 'Error: ' + err.message); });
    });
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-del-rec]');
    if (!btn) return;
    if (!confirm('¿Eliminar esta recomendación y su seguimiento?')) return;
    apiDelete('/api/auditoria/recomendaciones/' + btn.getAttribute('data-del-rec')).then(function () {
      loadRecomendaciones();
      loadResumen();
    }).catch(function (err) { alert('Error: ' + err.message); });
  });

  function initRecFilters() {
    var sel = el('aud-rec-filter-estado');
    if (sel) sel.addEventListener('change', loadRecomendaciones);
  }

  // ── Seguimiento ───────────────────────────────────────────────────────────────

  function loadSeguimiento() {
    var recId = (el('aud-seg-filter-rec') || {}).value || '';
    var url = '/api/auditoria/seguimiento';
    if (recId) url += '?recomendacion_id=' + recId;

    status('aud-seg-status', 'Cargando...');
    apiGet(url).then(function (list) {
      var container = el('aud-seg-table');
      if (!list.length) { status('aud-seg-status', 'Sin entradas de seguimiento.'); container.innerHTML = ''; return; }
      status('aud-seg-status', '');
      var rows = list.map(function (s) {
        return '<tr>' +
          '<td>' + (s.fecha || '—') + '</td>' +
          '<td>' + s.descripcion + '</td>' +
          '<td>' + progress(s.porcentaje_avance) + '</td>' +
          '<td>' + (s.evidencia ? '<a href="' + s.evidencia + '" target="_blank" rel="noopener">Ver</a>' : '—') + '</td>' +
          '<td>' + (s.registrado_por || '—') + '</td>' +
          '<td><button class="aud-actions button is-danger is-sm" data-del-seg="' + s.id + '">Eliminar</button></td>' +
          '</tr>';
      });
      container.innerHTML = '<table class="aud-table"><thead><tr>' +
        '<th>Fecha</th><th>Descripción del avance</th><th>Avance</th><th>Evidencia</th><th>Registrado por</th><th></th>' +
        '</tr></thead><tbody>' + rows.join('') + '</tbody></table>';
    }).catch(function (err) { status('aud-seg-status', 'Error: ' + err.message); });
  }

  function initFormSeguimiento() {
    var form = el('aud-form-seguimiento');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var data = formToObj(form);
      if (data.recomendacion_id) data.recomendacion_id = parseInt(data.recomendacion_id);
      if (data.porcentaje_avance !== null) data.porcentaje_avance = parseInt(data.porcentaje_avance) || 0;
      apiPost('/api/auditoria/seguimiento', data).then(function () {
        status('aud-seg-form-status', '✓ Avance registrado.');
        form.reset();
        loadSeguimiento();
        loadRecomendaciones();
        loadResumen();
      }).catch(function (err) { status('aud-seg-form-status', 'Error: ' + err.message); });
    });
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-del-seg]');
    if (!btn) return;
    if (!confirm('¿Eliminar esta entrada de seguimiento?')) return;
    apiDelete('/api/auditoria/seguimiento/' + btn.getAttribute('data-del-seg')).then(function () {
      loadSeguimiento();
    }).catch(function (err) { alert('Error: ' + err.message); });
  });

  function initSegFilter() {
    var sel = el('aud-seg-filter-rec');
    if (sel) sel.addEventListener('change', loadSeguimiento);
  }

  // ── Init ──────────────────────────────────────────────────────────────────────

  function init() {
    initNav();
    initFormAuditoria();
    initFormHallazgo();
    initFormRecomendacion();
    initFormSeguimiento();
    initHallazgoFilters();
    initRecFilters();
    initSegFilter();
    loadResumen();
    loadAuditorias();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
