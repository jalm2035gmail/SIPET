/* capacitacion_progreso.js — Mi Progreso v20260309 */
(function () {
  'use strict';

  function el(id) { return document.getElementById(id); }
  function esc(v) {
    return String(v == null ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // ── Selectores ─────────────────────────────────────────────────────────────
  var kpiGrid       = el('pg-kpi-grid');
  var cursosStatus  = el('pg-cursos-status');
  var cursosWrap    = el('pg-cursos-wrap');
  var cursosBody    = el('pg-cursos-body');
  var cursosEmpty   = el('pg-cursos-empty');
  var certsStatus   = el('pg-certs-status');
  var certsGrid     = el('pg-certs-grid');
  var certsEmpty    = el('pg-certs-empty');
  var panelCursos   = el('pg-panel-cursos');
  var panelCerts    = el('pg-panel-certificados');
  var tabs          = document.querySelectorAll('.pg-tab');

  // ── Datos en memoria ────────────────────────────────────────────────────────
  var inscripciones = [];
  var certificados  = [];

  // ── Utilidades ─────────────────────────────────────────────────────────────
  function apiJson(url) {
    return fetch(url, { headers: { 'Content-Type': 'application/json' } })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); });
  }

  function fmtFecha(iso) {
    if (!iso) return '—';
    return iso.split('T')[0];
  }

  // ── KPIs ────────────────────────────────────────────────────────────────────
  function renderKpis(insc, certs) {
    if (!kpiGrid) return;
    var totalInscritos = insc.length;
    var enProgreso     = insc.filter(function (i) { return i.estado === 'en_progreso'; }).length;
    var completados    = insc.filter(function (i) { return i.estado === 'completado'; }).length;
    var pendientes     = insc.filter(function (i) { return i.estado === 'pendiente'; }).length;
    var reprobados     = insc.filter(function (i) { return i.estado === 'reprobado'; }).length;
    var numCerts       = certs.length;
    var tasa           = totalInscritos ? Math.round(completados / totalInscritos * 100) : 0;

    var items = [
      { val: totalInscritos, label: 'Cursos inscritos',   color: '#6366f1' },
      { val: enProgreso,     label: 'En progreso',        color: '#2563eb' },
      { val: completados,    label: 'Completados',        color: '#16a34a' },
      { val: pendientes,     label: 'Pendientes',         color: '#f59e0b' },
      { val: reprobados,     label: 'Reprobados',         color: '#dc2626' },
      { val: numCerts,       label: 'Certificados',       color: '#0891b2' },
      { val: tasa + '%',     label: 'Tasa completado',   color: '#059669' },
    ];
    kpiGrid.innerHTML = items.map(function (k) {
      return '<div class="pg-kpi" style="--kpi-color:' + k.color + ';">' +
        '<div class="pg-kpi-val">' + esc(k.val) + '</div>' +
        '<div class="pg-kpi-label">' + esc(k.label) + '</div>' +
      '</div>';
    }).join('');
  }

  // ── Tabla de cursos ─────────────────────────────────────────────────────────
  function renderCursos(insc) {
    if (cursosStatus) cursosStatus.style.display = 'none';

    if (!insc.length) {
      if (cursosEmpty) cursosEmpty.style.display = '';
      return;
    }
    if (cursosWrap) cursosWrap.style.display = '';

    if (cursosBody) {
      cursosBody.innerHTML = insc.map(function (r, i) {
        var pct    = (r.pct_avance || 0).toFixed(0);
        var estado = r.estado || 'pendiente';
        var accion = '';
        if (estado === 'completado') {
          accion = '<a href="/capacitacion/curso/' + r.curso_id + '" style="color:#16a34a;font-weight:600;">Repasar</a>';
        } else {
          accion = '<a href="/capacitacion/curso/' + r.curso_id + '" style="color:#4f46e5;font-weight:600;">Continuar →</a>';
        }
        return '<tr>' +
          '<td style="color:#94a3b8;">' + (i + 1) + '</td>' +
          '<td style="font-weight:600;">' + esc(r.curso_nombre || '#' + r.curso_id) + '</td>' +
          '<td><span class="pg-badge ' + esc(estado) + '">' + esc(estado.replace('_', ' ')) + '</span></td>' +
          '<td style="min-width:90px;">' +
            '<div class="pg-mini-bar"><div class="pg-mini-fill" style="width:' + pct + '%"></div></div>' +
            '<span style="font-size:11px;color:#64748b;">' + pct + '%</span>' +
          '</td>' +
          '<td>' + (r.puntaje_final != null ? r.puntaje_final.toFixed(1) + '%' : '—') + '</td>' +
          '<td>' + esc(fmtFecha(r.fecha_inscripcion)) + '</td>' +
          '<td>' + esc(fmtFecha(r.fecha_completado)) + '</td>' +
          '<td>' + accion + '</td>' +
        '</tr>';
      }).join('');
    }
  }

  // ── Grid de certificados ────────────────────────────────────────────────────
  function renderCerts(certs) {
    if (certsStatus) certsStatus.style.display = 'none';

    if (!certs.length) {
      if (certsEmpty) certsEmpty.style.display = '';
      return;
    }
    if (certsGrid) {
      certsGrid.style.display = '';
      certsGrid.innerHTML = certs.map(function (c) {
        return '<div class="pg-cert-card">' +
          '<div class="pg-cert-name">' + esc(c.curso_nombre || 'Curso') + '</div>' +
          '<div class="pg-cert-folio">Folio: ' + esc(c.folio) + '</div>' +
          '<div class="pg-cert-date">Emitido: ' + esc(fmtFecha(c.fecha_emision)) + '</div>' +
          '<a href="/capacitacion/certificado/' + c.id + '" class="pg-cert-link" target="_blank">Ver certificado →</a>' +
        '</div>';
      }).join('');
    }
  }

  // ── Tabs ────────────────────────────────────────────────────────────────────
  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      tabs.forEach(function (t) { t.classList.remove('active'); });
      tab.classList.add('active');
      var which = tab.getAttribute('data-tab');
      if (panelCursos)  panelCursos.style.display  = which === 'cursos' ? '' : 'none';
      if (panelCerts)   panelCerts.style.display    = which === 'certificados' ? '' : 'none';
    });
  });

  // ── Init ────────────────────────────────────────────────────────────────────
  function init() {
    Promise.all([
      apiJson('/api/capacitacion/mis-inscripciones'),
      apiJson('/api/capacitacion/mis-certificados'),
    ]).then(function (results) {
      inscripciones = Array.isArray(results[0].data) ? results[0].data : [];
      certificados  = Array.isArray(results[1].data) ? results[1].data : [];
      renderKpis(inscripciones, certificados);
      renderCursos(inscripciones);
      renderCerts(certificados);
    }).catch(function () {
      if (kpiGrid) kpiGrid.innerHTML = '<p style="color:#dc2626;font-size:14px;">Error al cargar datos.</p>';
      if (cursosStatus) cursosStatus.textContent = 'Error al cargar inscripciones.';
      if (certsStatus)  certsStatus.textContent  = 'Error al cargar certificados.';
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
