/* capacitacion_dashboard.js */
(function () {
  'use strict';

  function el(id) { return document.getElementById(id); }
  function esc(v) {
    return String(v == null ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  var kpiGrid = el('db-kpi-grid');
  var chartEstados = el('db-chart-estados');
  var chartDepts = el('db-chart-depts');
  var chartTopCur = el('db-chart-top-cursos');
  var chartCompletados = el('db-chart-completados');
  var chartAbandonados = el('db-chart-abandonados');
  var chartCertificados = el('db-chart-certificados');
  var chartPeor = el('db-chart-peor-desempeno');
  var overdueList = el('db-overdue-list');
  var zeroList = el('db-zero-list');
  var filterCurso = el('db-filter-curso');
  var filterEstado = el('db-filter-estado');
  var filterDept = el('db-filter-dept');
  var filterDesde = el('db-filter-desde');
  var filterHasta = el('db-filter-hasta');
  var btnFiltrar = el('db-btn-filtrar');
  var btnLimpiar = el('db-btn-limpiar');
  var btnCsv = el('db-btn-csv');
  var tblStatus = el('db-table-status');
  var tblWrap = el('db-table-wrap');
  var tblBody = el('db-table-body');
  var tblEmpty = el('db-table-empty');
  var pagination = el('db-pagination');
  var btnPrevPage = el('db-btn-prev-page');
  var btnNextPage = el('db-btn-next-page');
  var pageInfo = el('db-page-info');

  var allRows = [];
  var pageSize = 25;
  var currentPage = 1;

  function apiJson(url) {
    return fetch(url, { headers: { 'Content-Type': 'application/json' } })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); });
  }

  function fmtFecha(iso) {
    if (!iso) return '—';
    return String(iso).split('T')[0];
  }

  function barColor(key) {
    return {
      completado: '#15803d',
      en_progreso: '#1d4ed8',
      pendiente: '#64748b',
      reprobado: '#b91c1c'
    }[key] || '#0f766e';
  }

  function renderKpis(s) {
    if (!kpiGrid) return;
    var items = [
      { val: s.total_inscripciones, label: 'Inscripciones', color: '#17314f' },
      { val: s.cursos_publicados, label: 'Cursos activos', color: '#0f766e' },
      { val: s.cursos_archivados, label: 'Cursos archivados', color: '#94a3b8' },
      { val: s.tasa_completado + '%', label: 'Tasa finalizacion', color: '#c2410c' },
      { val: s.tasa_aprobacion + '%', label: 'Tasa aprobacion', color: '#2563eb' },
      { val: s.promedio_finalizacion_dias, label: 'Promedio dias', color: '#7c3aed' },
      { val: s.obligatorios_vencidos_total, label: 'Obligatorios vencidos', color: '#dc2626' },
      { val: s.certificados_emitidos, label: 'Certificados emitidos', color: '#0891b2' }
    ];
    kpiGrid.innerHTML = items.map(function (k) {
      return '<div class="db-kpi" style="--kpi-color:' + k.color + ';">' +
        '<div class="db-kpi-val">' + esc(k.val) + '</div>' +
        '<div class="db-kpi-label">' + esc(k.label) + '</div>' +
      '</div>';
    }).join('');
  }

  function renderBarChart(container, items, labelKey, countKey, formatter) {
    if (!container) return;
    if (!items || !items.length) {
      container.innerHTML = '<p class="db-status" style="padding:0;">Sin datos.</p>';
      return;
    }
    var max = Math.max.apply(null, items.map(function (i) { return Number(i[countKey] || 0); })) || 1;
    container.innerHTML = items.map(function (item) {
      var count = Number(item[countKey] || 0);
      var pct = Math.round((count / max) * 100);
      return '<div class="db-bar-item">' +
        '<span class="db-bar-label" title="' + esc(item[labelKey]) + '">' + esc(item[labelKey]) + '</span>' +
        '<div class="db-bar-track"><div class="db-bar-fill" style="width:' + pct + '%;background:' + (item.estado ? barColor(item.estado) : '') + '"></div></div>' +
        '<span class="db-bar-count">' + esc(formatter ? formatter(item) : count) + '</span>' +
      '</div>';
    }).join('');
  }

  function renderInlineList(container, items, titleKey, copyFn) {
    if (!container) return;
    if (!items || !items.length) {
      container.innerHTML = '<div class="db-status" style="padding:8px 0;">Sin datos.</div>';
      return;
    }
    container.innerHTML = items.map(function (item) {
      return '<div class="db-inline-item">' +
        '<div class="db-inline-title">' + esc(item[titleKey]) + '</div>' +
        '<div class="db-inline-copy">' + esc(copyFn(item)) + '</div>' +
      '</div>';
    }).join('');
  }

  function buildCsvUrl() {
    var params = new URLSearchParams();
    if (filterCurso && filterCurso.value) params.set('curso_id', filterCurso.value);
    if (filterEstado && filterEstado.value) params.set('estado', filterEstado.value);
    if (filterDept && filterDept.value.trim()) params.set('departamento', filterDept.value.trim());
    if (filterDesde && filterDesde.value) params.set('fecha_desde', filterDesde.value);
    if (filterHasta && filterHasta.value) params.set('fecha_hasta', filterHasta.value);
    return '/api/capacitacion/inscripciones-csv?' + params.toString();
  }

  function loadTabla() {
    if (tblStatus) tblStatus.style.display = '';
    if (tblWrap) tblWrap.style.display = 'none';
    if (tblEmpty) tblEmpty.style.display = 'none';
    if (pagination) pagination.style.display = 'none';
    if (btnCsv) btnCsv.href = buildCsvUrl();
    var params = buildCsvUrl().split('?')[1] || '';
    apiJson('/api/capacitacion/inscripciones?' + params).then(function (res) {
      if (tblStatus) tblStatus.style.display = 'none';
      allRows = Array.isArray(res.data) ? res.data : [];
      currentPage = 1;
      renderTabla();
    }).catch(function () {
      if (tblStatus) tblStatus.textContent = 'Error al cargar.';
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
    var page = allRows.slice(start, start + pageSize);
    if (tblWrap) tblWrap.style.display = '';
    if (tblBody) {
      tblBody.innerHTML = page.map(function (r, idx) {
        var pct = Number(r.pct_avance || 0).toFixed(0);
        return '<tr>' +
          '<td>' + esc(start + idx + 1) + '</td>' +
          '<td>' + esc(r.colaborador_nombre || r.colaborador_key || '—') + '</td>' +
          '<td>' + esc(r.departamento || '—') + '</td>' +
          '<td><a href="/capacitacion/curso/' + esc(r.curso_id) + '" style="color:#17314f;font-weight:700;">' + esc(r.curso_nombre || ('#' + r.curso_id)) + '</a></td>' +
          '<td><span class="db-badge ' + esc(r.estado) + '">' + esc(r.estado) + '</span></td>' +
          '<td><div class="db-mini-bar"><div class="db-mini-fill" style="width:' + pct + '%"></div></div><span style="font-size:11px;color:#64748b;">' + pct + '%</span></td>' +
          '<td>' + (r.puntaje_final != null ? esc(Number(r.puntaje_final).toFixed(1) + '%') : '—') + '</td>' +
          '<td>' + esc(fmtFecha(r.fecha_inscripcion)) + '</td>' +
          '<td>' + esc(fmtFecha(r.fecha_completado)) + '</td>' +
        '</tr>';
      }).join('');
    }
    if (pagination) pagination.style.display = totalPages > 1 ? '' : 'none';
    if (pageInfo) pageInfo.textContent = 'Pagina ' + currentPage + ' de ' + totalPages + ' (' + total + ' registros)';
    if (btnPrevPage) btnPrevPage.disabled = currentPage <= 1;
    if (btnNextPage) btnNextPage.disabled = currentPage >= totalPages;
  }

  function loadCursos() {
    apiJson('/api/capacitacion/cursos').then(function (res) {
      if (!filterCurso || !res.ok) return;
      (Array.isArray(res.data) ? res.data : []).forEach(function (c) {
        var opt = document.createElement('option');
        opt.value = c.id;
        opt.textContent = c.nombre;
        filterCurso.appendChild(opt);
      });
    });
  }

  function renderDashboard(stats) {
    renderKpis(stats);
    renderBarChart(chartEstados, stats.estados || [], 'estado', 'n');
    renderBarChart(chartDepts, stats.avance_departamento || [], 'departamento', 'avance', function (item) { return Number(item.avance || 0).toFixed(1) + '%'; });
    renderBarChart(chartTopCur, stats.inscripciones_por_curso || [], 'nombre', 'total');
    renderBarChart(chartCompletados, stats.top_cursos_completados || [], 'nombre', 'total');
    renderBarChart(chartAbandonados, stats.top_cursos_abandonados || [], 'nombre', 'total');
    renderBarChart(chartCertificados, stats.certificados_por_periodo || [], 'periodo', 'total');
    renderBarChart(chartPeor, stats.cursos_peor_aprobacion || [], 'nombre', 'tasa_aprobacion', function (item) { return Number(item.tasa_aprobacion || 0).toFixed(1) + '%'; });
    renderInlineList(overdueList, stats.obligatorios_vencidos || [], 'nombre', function (item) { return item.total + ' colaboradores fuera de tiempo'; });
    renderInlineList(zeroList, stats.sin_avance || [], 'colaborador_nombre', function (item) {
      return (item.curso_nombre || 'Curso') + ' · ' + (item.departamento || 'Sin departamento');
    });
  }

  if (btnPrevPage) btnPrevPage.addEventListener('click', function () { currentPage -= 1; renderTabla(); });
  if (btnNextPage) btnNextPage.addEventListener('click', function () { currentPage += 1; renderTabla(); });
  if (btnFiltrar) btnFiltrar.addEventListener('click', loadTabla);
  if (btnLimpiar) btnLimpiar.addEventListener('click', function () {
    if (filterCurso) filterCurso.value = '';
    if (filterEstado) filterEstado.value = '';
    if (filterDept) filterDept.value = '';
    if (filterDesde) filterDesde.value = '';
    if (filterHasta) filterHasta.value = '';
    loadTabla();
  });
  [filterCurso, filterEstado].forEach(function (item) {
    if (item) item.addEventListener('change', loadTabla);
  });

  function init() {
    Promise.all([apiJson('/api/capacitacion/stats'), loadCursos()]).then(function (results) {
      if (results[0] && results[0].ok) renderDashboard(results[0].data || {});
    });
    loadTabla();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
