/* capacitacion_dashboard.js — Dashboard Admin v20260309 */
(function () {
  'use strict';

  function el(id) { return document.getElementById(id); }
  function esc(v) {
    return String(v == null ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // ── Selectores ─────────────────────────────────────────────────────────────
  var kpiGrid      = el('db-kpi-grid');
  var chartEstados = el('db-chart-estados');
  var chartDepts   = el('db-chart-depts');
  var chartTopCur  = el('db-chart-top-cursos');
  var filterCurso  = el('db-filter-curso');
  var filterEstado = el('db-filter-estado');
  var filterDept   = el('db-filter-dept');
  var filterDesde  = el('db-filter-desde');
  var filterHasta  = el('db-filter-hasta');
  var btnFiltrar   = el('db-btn-filtrar');
  var btnLimpiar   = el('db-btn-limpiar');
  var btnCsv       = el('db-btn-csv');
  var tblStatus    = el('db-table-status');
  var tblWrap      = el('db-table-wrap');
  var tblBody      = el('db-table-body');
  var tblEmpty     = el('db-table-empty');
  var pagination   = el('db-pagination');
  var btnPrevPage  = el('db-btn-prev-page');
  var btnNextPage  = el('db-btn-next-page');
  var pageInfo     = el('db-page-info');

  // ── Estado paginación ──────────────────────────────────────────────────────
  var allRows  = [];
  var pageSize = 25;
  var currentPage = 1;

  // ── Utilidades ─────────────────────────────────────────────────────────────
  function apiJson(url) {
    return fetch(url, { headers: { 'Content-Type': 'application/json' } })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); });
  }

  function fmtFecha(iso) {
    if (!iso) return '—';
    return iso.split('T')[0];
  }

  function estadoColor(e) {
    return { completado: '#16a34a', en_progreso: '#2563eb', pendiente: '#94a3b8', reprobado: '#dc2626' }[e] || '#94a3b8';
  }

  // ── KPIs ───────────────────────────────────────────────────────────────────
  function renderKpis(s) {
    if (!kpiGrid) return;
    var items = [
      { val: s.total_inscripciones,   label: 'Total inscripciones',    color: '#6366f1' },
      { val: s.completadas,           label: 'Completadas',            color: '#16a34a' },
      { val: s.en_progreso,           label: 'En progreso',            color: '#2563eb' },
      { val: s.reprobadas,            label: 'Reprobadas',             color: '#dc2626' },
      { val: s.cursos_publicados,     label: 'Cursos publicados',      color: '#f59e0b' },
      { val: s.certificados_emitidos, label: 'Certificados emitidos',  color: '#0891b2' },
      { val: s.colaboradores_unicos,  label: 'Colaboradores únicos',   color: '#7c3aed' },
      { val: s.tasa_completado + '%', label: 'Tasa de completado',     color: '#059669' },
    ];
    kpiGrid.innerHTML = items.map(function (k) {
      return '<div class="db-kpi" style="--kpi-color:' + k.color + ';">' +
        '<div class="db-kpi-val">' + esc(k.val) + '</div>' +
        '<div class="db-kpi-label">' + esc(k.label) + '</div>' +
      '</div>';
    }).join('');
  }

  // ── Gráficos de barras ──────────────────────────────────────────────────────
  function renderBarChart(container, items, labelKey, countKey, cssClass, maxVal) {
    if (!container) return;
    if (!items || !items.length) { container.innerHTML = '<p style="color:#94a3b8;font-size:13px;">Sin datos.</p>'; return; }
    var max = maxVal || Math.max.apply(null, items.map(function (i) { return i[countKey]; })) || 1;
    container.innerHTML = items.map(function (item) {
      var pct = Math.round(item[countKey] / max * 100);
      return '<div class="db-bar-item">' +
        '<span class="db-bar-label" title="' + esc(item[labelKey]) + '">' + esc(item[labelKey]) + '</span>' +
        '<div class="db-bar-track"><div class="db-bar-fill ' + esc(cssClass || item[labelKey]) + '" style="width:' + pct + '%;background:' + estadoColor(item[labelKey]) + '"></div></div>' +
        '<span class="db-bar-count">' + item[countKey] + '</span>' +
      '</div>';
    }).join('');
  }

  // ── Tabla inscripciones ─────────────────────────────────────────────────────
  function buildCsvUrl() {
    var params = new URLSearchParams();
    var ci = filterCurso  ? filterCurso.value  : '';
    var es = filterEstado ? filterEstado.value : '';
    var dp = filterDept   ? filterDept.value.trim() : '';
    var de = filterDesde  ? filterDesde.value  : '';
    var ha = filterHasta  ? filterHasta.value  : '';
    if (ci) params.set('curso_id', ci);
    if (es) params.set('estado', es);
    if (dp) params.set('departamento', dp);
    if (de) params.set('fecha_desde', de);
    if (ha) params.set('fecha_hasta', ha);
    return '/api/capacitacion/inscripciones-csv?' + params.toString();
  }

  function loadTabla() {
    if (tblStatus) tblStatus.style.display = '';
    if (tblWrap)   tblWrap.style.display   = 'none';
    if (tblEmpty)  tblEmpty.style.display  = 'none';
    if (pagination)pagination.style.display= 'none';

    var params = new URLSearchParams();
    var ci = filterCurso  ? filterCurso.value  : '';
    var es = filterEstado ? filterEstado.value : '';
    var dp = filterDept   ? filterDept.value.trim() : '';
    var de = filterDesde  ? filterDesde.value  : '';
    var ha = filterHasta  ? filterHasta.value  : '';
    if (ci) params.set('curso_id', ci);
    if (es) params.set('estado', es);
    if (dp) params.set('departamento', dp);
    if (de) params.set('fecha_desde', de);
    if (ha) params.set('fecha_hasta', ha);

    if (btnCsv) btnCsv.href = '/api/capacitacion/inscripciones-csv?' + params.toString();

    apiJson('/api/capacitacion/inscripciones?' + params.toString()).then(function (res) {
      if (tblStatus) tblStatus.style.display = 'none';
      allRows = Array.isArray(res.data) ? res.data : [];
      currentPage = 1;
      renderTabla();
    }).catch(function () {
      if (tblStatus) tblStatus.textContent = 'Error al cargar inscripciones.';
    });
  }

  function renderTabla() {
    if (!allRows.length) {
      if (tblEmpty) tblEmpty.style.display = '';
      return;
    }
    var total = allRows.length;
    var totalPages = Math.ceil(total / pageSize);
    var start = (currentPage - 1) * pageSize;
    var page  = allRows.slice(start, start + pageSize);

    if (tblWrap) tblWrap.style.display = '';
    if (tblBody) {
      tblBody.innerHTML = page.map(function (r, i) {
        var pct = (r.pct_avance || 0).toFixed(0);
        return '<tr>' +
          '<td style="color:#94a3b8;">' + (start + i + 1) + '</td>' +
          '<td>' + esc(r.colaborador_nombre || r.colaborador_key || '—') + '</td>' +
          '<td>' + esc(r.departamento || '—') + '</td>' +
          '<td><a href="/capacitacion/curso/' + r.curso_id + '" style="color:#4f46e5;font-weight:600;">' + esc(r.curso_nombre || '#' + r.curso_id) + '</a></td>' +
          '<td><span class="db-badge ' + esc(r.estado) + '">' + esc(r.estado) + '</span></td>' +
          '<td style="min-width:80px;"><div class="db-mini-bar"><div class="db-mini-fill" style="width:' + pct + '%"></div></div><span style="font-size:11px;color:#64748b;">' + pct + '%</span></td>' +
          '<td>' + (r.puntaje_final != null ? r.puntaje_final.toFixed(1) + '%' : '—') + '</td>' +
          '<td>' + esc(fmtFecha(r.fecha_inscripcion)) + '</td>' +
          '<td>' + esc(fmtFecha(r.fecha_completado)) + '</td>' +
        '</tr>';
      }).join('');
    }

    // Paginación
    if (pagination) pagination.style.display = totalPages > 1 ? '' : 'none';
    if (pageInfo) pageInfo.textContent = 'Página ' + currentPage + ' de ' + totalPages + '  (' + total + ' registros)';
    if (btnPrevPage) btnPrevPage.disabled = currentPage <= 1;
    if (btnNextPage) btnNextPage.disabled = currentPage >= totalPages;
  }

  if (btnPrevPage) btnPrevPage.addEventListener('click', function () { currentPage--; renderTabla(); });
  if (btnNextPage) btnNextPage.addEventListener('click', function () { currentPage++; renderTabla(); });
  if (btnFiltrar)  btnFiltrar.addEventListener('click', loadTabla);
  if (btnLimpiar) {
    btnLimpiar.addEventListener('click', function () {
      if (filterCurso)  filterCurso.value  = '';
      if (filterEstado) filterEstado.value = '';
      if (filterDept)   filterDept.value   = '';
      if (filterDesde)  filterDesde.value  = '';
      if (filterHasta)  filterHasta.value  = '';
      loadTabla();
    });
  }
  [filterCurso, filterEstado].forEach(function (sel) {
    if (sel) sel.addEventListener('change', loadTabla);
  });

  // ── Poblar select de cursos ─────────────────────────────────────────────────
  function loadCursos() {
    apiJson('/api/capacitacion/cursos').then(function (res) {
      if (!filterCurso) return;
      var cursos = Array.isArray(res.data) ? res.data : [];
      cursos.forEach(function (c) {
        var opt = document.createElement('option');
        opt.value = c.id;
        opt.textContent = c.nombre;
        filterCurso.appendChild(opt);
      });
    });
  }

  // ── Init ────────────────────────────────────────────────────────────────────
  function init() {
    Promise.all([
      apiJson('/api/capacitacion/stats'),
      loadCursos(),
    ]).then(function (results) {
      var stats = results[0];
      if (stats && stats.ok && stats.data) {
        var s = stats.data;
        renderKpis(s);
        renderBarChart(chartEstados, s.estados || [], 'estado', 'n', null, null);
        renderBarChart(chartDepts, s.departamentos || [], 'departamento', 'n', 'dept', null);
        renderBarChart(chartTopCur, s.top_cursos_completados || [], 'nombre', 'total', 'completado', null);
      } else {
        if (kpiGrid) kpiGrid.innerHTML = '<p style="color:#94a3b8;font-size:14px;">Sin datos disponibles.</p>';
      }
    });
    loadTabla();
  }

  // Pequeño delay para que el DOM termine de renderizar
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
