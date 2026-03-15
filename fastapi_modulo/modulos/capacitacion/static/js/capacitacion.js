/* capacitacion.js — Módulo de Capacitación v20260309 */
(function () {
  'use strict';

  // ── Estado global ────────────────────────────────────────────────────────────
  var cursos = [];
  var categorias = [];
  var misInscripciones = [];
  var currentView = 'tarjetas';
  var currentTab  = 'catalogo';
  var filterSearch = '';
  var filterCat    = '';
  var filterNivel  = '';
  var filterEstado = 'publicado';
  var pendingInscCursoId = null;
  var isAdmin = false;

  // ── Selectores ────────────────────────────────────────────────────────────────
  var viewHost         = document.getElementById('cap-view-host');
  var catalogoStatus   = document.getElementById('cap-catalogo-status');
  var viewButtons      = Array.from(document.querySelectorAll('[data-cap-view]'));
  var tabButtons       = Array.from(document.querySelectorAll('[data-cap-tab]'));
  var panels           = Array.from(document.querySelectorAll('[data-cap-panel]'));
  var searchInput      = document.getElementById('cap-search');
  var filterCatEl      = document.getElementById('cap-filter-cat');
  var filterNivelEl    = document.getElementById('cap-filter-nivel');
  var filterEstadoEl   = document.getElementById('cap-filter-estado-curso');
  var inscModal        = document.getElementById('cap-inscribir-modal');
  var modalCursoTitle  = document.getElementById('cap-modal-curso-title');
  var modalCursoDesc   = document.getElementById('cap-modal-curso-desc');
  var modalInscStatus  = document.getElementById('cap-modal-inscribir-status');
  var modalInscBtn     = document.getElementById('cap-modal-inscribir-btn');
  var modalCloseBtn    = document.getElementById('cap-modal-close');
  var modalCloseBtn2   = document.getElementById('cap-modal-close2');
  var auditModal       = document.getElementById('cap-audit-modal');
  var auditCloseBtn    = document.getElementById('cap-audit-close');
  var auditStatusEl    = document.getElementById('cap-audit-status');
  var auditListEl      = document.getElementById('cap-audit-list');
  var auditTitleEl     = document.getElementById('cap-audit-title');

  // ── Utilidades ───────────────────────────────────────────────────────────────
  function esc(v) {
    return String(v == null ? '' : v)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function nivelLabel(n) {
    return n === 'basico' ? 'Básico' : n === 'intermedio' ? 'Intermedio' : n === 'avanzado' ? 'Avanzado' : esc(n);
  }

  function estadoLabel(s) {
    var map = { pendiente: 'Pendiente', en_progreso: 'En progreso', completado: 'Completado', reprobado: 'Reprobado' };
    return map[s] || esc(s);
  }

  function cursoEstadoLabel(s) {
    return { borrador: 'Borrador', publicado: 'Publicado', archivado: 'Archivado' }[s] || esc(s);
  }

  function fmtPct(v) {
    return (v == null ? 0 : v).toFixed(0) + '%';
  }
  function auditActionLabel(action) {
    return {
      created: 'Creado',
      updated: 'Actualizado',
      published: 'Publicado',
      deleted: 'Eliminado'
    }[action] || esc(action || 'Evento');
  }
  function auditSummary(curso) {
    var parts = [];
    if (curso.creado_por) parts.push('Creó: ' + esc(curso.creado_por));
    if (curso.publicado_por) parts.push('Publicó: ' + esc(curso.publicado_por));
    if (curso.actualizado_por && curso.actualizado_por !== curso.creado_por) parts.push('Editó: ' + esc(curso.actualizado_por));
    return parts.join('<br>') || '—';
  }

  function getInscForCurso(cursoId) {
    return misInscripciones.find(function (i) { return i.curso_id === cursoId; }) || null;
  }

  function apiJson(url, opts) {
    return fetch(url, Object.assign({ headers: { 'Content-Type': 'application/json' } }, opts || {}))
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, status: r.status, data: d }; }); });
  }

  // ── Carga de datos ────────────────────────────────────────────────────────────
  function loadAll() {
    if (catalogoStatus) catalogoStatus.textContent = 'Cargando…';
    Promise.all([
      apiJson('/api/capacitacion/categorias'),
      apiJson('/api/capacitacion/cursos'),
      apiJson('/api/capacitacion/mis-inscripciones'),
    ]).then(function (results) {
      categorias       = Array.isArray(results[0].data) ? results[0].data : [];
      cursos           = Array.isArray(results[1].data) ? results[1].data : [];
      misInscripciones = Array.isArray(results[2].data) ? results[2].data : [];

      // Detectar si es admin
      var adminTabBtn = document.querySelector('[data-cap-tab="gestion"]');
      // Detectar admin comprobando si existe algún curso en borrador (solo admin los ve)
      // o si el filtro de estado puede traer borradores
      isAdmin = cursos.some(function (c) { return c.estado === 'borrador'; });
      if (adminTabBtn) {
        adminTabBtn.style.display = isAdmin ? '' : 'none';
        if (isAdmin) populateCursoCategoriasSelect();
      }

      fillCategoryFilter();
      updateKpis();
      if (catalogoStatus) catalogoStatus.textContent = '';
      renderCurrentView();
      if (currentTab === 'mi-progreso') renderProgresoTab();
      if (currentTab === 'gestion' && isAdmin) renderGestionCursos();
    }).catch(function () {
      if (catalogoStatus) catalogoStatus.textContent = 'Error al cargar los datos.';
    });
  }

  function fillCategoryFilter() {
    if (!filterCatEl) return;
    filterCatEl.innerHTML = '<option value="">Todas las categorías</option>';
    categorias.forEach(function (c) {
      var opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = c.nombre;
      filterCatEl.appendChild(opt);
    });
  }

  function updateKpis() {
    var pub = cursos.filter(function (c) { return c.estado === 'publicado'; }).length;
    var total_insc = misInscripciones.length;
    var en_prog    = misInscripciones.filter(function (i) { return i.estado === 'en_progreso'; }).length;
    var compl      = misInscripciones.filter(function (i) { return i.estado === 'completado'; }).length;
    setText('cap-kpi-cursos',     pub);
    setText('cap-kpi-inscritos',  total_insc);
    setText('cap-kpi-progreso',   en_prog);
    setText('cap-kpi-completados', compl);
  }

  function setText(id, val) {
    var el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  // ── Filtrado ─────────────────────────────────────────────────────────────────
  function filteredCursos() {
    var q = filterSearch.trim().toLowerCase();
    return cursos.filter(function (c) {
      if (filterEstado && c.estado !== filterEstado) return false;
      if (filterCat   && String(c.categoria_id) !== String(filterCat)) return false;
      if (filterNivel && c.nivel !== filterNivel) return false;
      if (q && (c.nombre.toLowerCase().indexOf(q) === -1 &&
               (c.descripcion || '').toLowerCase().indexOf(q) === -1 &&
               (c.responsable || '').toLowerCase().indexOf(q) === -1)) return false;
      return true;
    });
  }

  // ── Render según view ─────────────────────────────────────────────────────────
  function renderCurrentView() {
    if (!viewHost) return;
    var list = filteredCursos();
    if (list.length === 0) {
      viewHost.innerHTML = '<div class="cap-empty">No se encontraron cursos.</div>';
      return;
    }
    if (currentView === 'tarjetas') renderCardView(list);
    else if (currentView === 'tabla') renderTableView(list);
    else if (currentView === 'kanban') renderKanbanView(list);
  }

  // ── Vista Tarjetas ────────────────────────────────────────────────────────────
  function renderCardView(list) {
    var html = '<div class="cap-card-grid">';
    list.forEach(function (c) {
      var insc = getInscForCurso(c.id);
      var pct  = insc ? (insc.pct_avance || 0) : 0;
      html += renderCard(c, insc, pct);
    });
    html += '</div>';
    viewHost.innerHTML = html;
    bindCardActions();
  }

  function renderCard(c, insc, pct) {
    var catNombre = c.categoria_nombre ? '<span class="cap-badge">' + esc(c.categoria_nombre) + '</span>' : '';
    var nivelBadge = '<span class="cap-badge ' + esc(c.nivel) + '">' + nivelLabel(c.nivel) + '</span>';
    var oblig = c.es_obligatorio ? '<span class="cap-badge obligatorio">Obligatorio</span>' : '';
    var imgHtml = c.imagen_url
      ? '<img class="cap-card-image" src="' + esc(c.imagen_url) + '" alt="" loading="lazy" />'
      : '<div class="cap-card-image">📚</div>';
    var dur = c.duracion_horas ? '<span style="font-size:11px;color:#64748b;">' + c.duracion_horas + ' h</span>' : '';
    var progBar = insc
      ? '<div class="cap-progress-bar"><div class="cap-progress-fill" style="width:' + pct + '%"></div></div>' +
        '<span style="font-size:11px;color:#475569;">' + fmtPct(pct) + '</span>'
      : '';
    var estadoBadge = insc ? '<span class="cap-badge ' + esc(insc.estado) + '">' + estadoLabel(insc.estado) + '</span>' : '';
    var actionBtn = '';
    if (!insc) {
      actionBtn = '<button class="cap-btn is-primary is-wide" type="button" data-insc-curso-id="' + c.id + '">Inscribirse</button>';
    } else if (insc.estado === 'completado') {
      actionBtn = '<button class="cap-btn is-green is-wide" type="button" data-insc-curso-id="' + c.id + '" disabled>✓ Completado</button>';
    } else {
      actionBtn = '<button class="cap-btn is-outline is-wide" type="button" data-continue-curso-id="' + c.id + '">Continuar →</button>';
    }
    return '<article class="cap-course-card">' +
      imgHtml +
      '<div class="cap-card-body">' +
        '<p class="cap-card-title">' + esc(c.nombre) + '</p>' +
        '<div class="cap-card-meta">' + catNombre + nivelBadge + oblig + dur + '</div>' +
        (insc ? '<div class="cap-card-meta">' + estadoBadge + '</div>' : '') +
        (insc ? '<div style="display:flex;align-items:center;gap:8px;">' + progBar + '</div>' : '') +
        (c.descripcion ? '<p style="font-size:12px;color:#64748b;margin:0;line-clamp:2;-backendkit-line-clamp:2;display:-backendkit-box;-backendkit-box-orient:vertical;overflow:hidden;">' + esc(c.descripcion) + '</p>' : '') +
      '</div>' +
      '<div class="cap-card-footer">' + actionBtn + '</div>' +
    '</article>';
  }

  // ── Vista Tabla ───────────────────────────────────────────────────────────────
  function renderTableView(list) {
    var html = '<div class="cap-table-wrap"><table class="cap-table"><thead><tr>' +
      '<th>Curso</th><th>Categoría</th><th>Nivel</th><th>Estado</th>' +
      '<th>Responsable</th><th>Duración</th><th>Aprobación</th><th>Mi avance</th><th></th>' +
      '</tr></thead><tbody>';
    list.forEach(function (c) {
      var insc = getInscForCurso(c.id);
      var progCell = insc
        ? '<div style="display:flex;align-items:center;gap:6px;"><div class="cap-progress-bar" style="width:70px;"><div class="cap-progress-fill" style="width:' + (insc.pct_avance || 0) + '%"></div></div><span style="font-size:11px;color:#475569;">' + fmtPct(insc.pct_avance) + '</span></div>'
        : '<span style="color:#94a3b8;font-size:12px;">—</span>';
      var actionCell = !insc
        ? '<button class="cap-btn is-primary is-sm" type="button" data-insc-curso-id="' + c.id + '">Inscribirse</button>'
        : (insc.estado === 'completado'
            ? '<span class="cap-badge completado">Completado</span>'
            : '<button class="cap-btn is-outline is-sm" type="button" data-continue-curso-id="' + c.id + '">Continuar</button>');
      html += '<tr>' +
        '<td class="wrap-cell"><strong>' + esc(c.nombre) + '</strong>' + (c.codigo ? '<br><span style="font-size:11px;color:#94a3b8;">' + esc(c.codigo) + '</span>' : '') + '</td>' +
        '<td>' + (c.categoria_nombre ? esc(c.categoria_nombre) : '—') + '</td>' +
        '<td><span class="cap-badge ' + esc(c.nivel) + '">' + nivelLabel(c.nivel) + '</span></td>' +
        '<td><span class="cap-badge ' + esc(c.estado) + '">' + cursoEstadoLabel(c.estado) + '</span></td>' +
        '<td>' + (c.responsable ? esc(c.responsable) : '—') + '</td>' +
        '<td>' + (c.duracion_horas ? c.duracion_horas + ' h' : '—') + '</td>' +
        '<td>' + c.puntaje_aprobacion + '%</td>' +
        '<td>' + progCell + '</td>' +
        '<td>' + actionCell + '</td>' +
      '</tr>';
    });
    html += '</tbody></table></div>';
    viewHost.innerHTML = html;
    bindCardActions();
  }

  // ── Vista Kanban ──────────────────────────────────────────────────────────────
  function renderKanbanView(list) {
    var cols = {
      no_iniciado: { label: 'No iniciado', items: [] },
      en_progreso: { label: 'En progreso', items: [] },
      completado:  { label: 'Completado',  items: [] },
    };
    list.forEach(function (c) {
      var insc = getInscForCurso(c.id);
      if (!insc) cols.no_iniciado.items.push(c);
      else if (insc.estado === 'completado') cols.completado.items.push(c);
      else cols.en_progreso.items.push(c);
    });
    var html = '<div class="cap-kanban">';
    Object.keys(cols).forEach(function (key) {
      var col = cols[key];
      html += '<div class="cap-kanban-col">';
      html += '<div class="cap-kanban-col-title">' + esc(col.label) + '<span class="cap-kanban-count">' + col.items.length + '</span></div>';
      col.items.forEach(function (c) {
        var insc = getInscForCurso(c.id);
        var pct  = insc ? (insc.pct_avance || 0) : 0;
        var cat  = c.categoria_nombre ? '<span class="cap-badge" style="font-size:10px;">' + esc(c.categoria_nombre) + '</span> ' : '';
        html += '<div class="cap-kanban-item" data-kanban-curso-id="' + c.id + '">' +
          '<div class="cap-kanban-item-title">' + esc(c.nombre) + '</div>' +
          '<div class="cap-kanban-item-meta">' + cat + '<span class="cap-badge ' + esc(c.nivel) + '">' + nivelLabel(c.nivel) + '</span>' + (c.duracion_horas ? ' · ' + c.duracion_horas + ' h' : '') + '</div>' +
          (insc ? '<div class="cap-progress-bar"><div class="cap-progress-fill" style="width:' + pct + '%"></div></div>' : '') +
          (!insc ? '<button class="cap-btn is-primary is-sm is-wide" style="margin-top:8px;" type="button" data-insc-curso-id="' + c.id + '">Inscribirse</button>' : '') +
        '</div>';
      });
      if (col.items.length === 0) html += '<p style="font-size:12px;color:#94a3b8;text-align:center;margin:8px 0;">Sin cursos</p>';
      html += '</div>';
    });
    html += '</div>';
    viewHost.innerHTML = html;
    bindCardActions();
  }

  // ── Bind acciones de tarjetas ──────────────────────────────────────────────────
  function bindCardActions() {
    // Inscribirse
    Array.from(viewHost.querySelectorAll('[data-insc-curso-id]')).forEach(function (btn) {
      btn.addEventListener('click', function () {
        var cid = parseInt(btn.getAttribute('data-insc-curso-id'), 10);
        openInscModal(cid);
      });
    });
    // Continuar (placeholder fase 4)
    Array.from(viewHost.querySelectorAll('[data-continue-curso-id]')).forEach(function (btn) {
      btn.addEventListener('click', function () {
        var cid = parseInt(btn.getAttribute('data-continue-curso-id'), 10);
        window.location.href = '/capacitacion/curso/' + cid;
      });
    });
    // Kanban items (click para continuar)
    Array.from(viewHost.querySelectorAll('[data-kanban-curso-id]')).forEach(function (div) {
      div.addEventListener('click', function (e) {
        if (e.target.closest('[data-insc-curso-id]')) return;
        var cid = parseInt(div.getAttribute('data-kanban-curso-id'), 10);
        var insc = getInscForCurso(cid);
        if (insc) window.location.href = '/capacitacion/curso/' + cid;
      });
    });
  }

  // ── Modal inscripción ─────────────────────────────────────────────────────────
  function openInscModal(cursoId) {
    var curso = cursos.find(function (c) { return c.id === cursoId; });
    if (!curso) return;
    pendingInscCursoId = cursoId;
    if (modalCursoTitle)  modalCursoTitle.textContent = curso.nombre;
    if (modalCursoDesc)   modalCursoDesc.textContent  = curso.descripcion || '';
    if (modalInscStatus)  modalInscStatus.textContent  = '';
    if (modalInscBtn)     modalInscBtn.disabled = false;
    if (inscModal) inscModal.style.display = 'block';
  }

  function closeInscModal() {
    if (inscModal) inscModal.style.display = 'none';
    pendingInscCursoId = null;
  }
  function closeAuditModal() {
    if (auditModal) auditModal.style.display = 'none';
  }
  function openAuditModal(tipo, id, title) {
    if (!auditModal || !auditListEl) return;
    auditModal.style.display = 'block';
    if (auditTitleEl) auditTitleEl.textContent = title || 'Historial';
    if (auditStatusEl) auditStatusEl.textContent = 'Cargando…';
    auditListEl.innerHTML = '';
    apiJson('/api/capacitacion/auditoria/' + tipo + '/' + id)
      .then(function (res) {
        var items = res && res.ok && res.data && Array.isArray(res.data.items) ? res.data.items : [];
        if (auditStatusEl) auditStatusEl.textContent = items.length ? '' : 'Sin eventos.';
        auditListEl.innerHTML = items.map(function (item) {
          var actor = item.actor_nombre || item.actor_key || 'Sistema';
          var when = item.creado_en ? String(item.creado_en).replace('T', ' ').slice(0, 16) : 'Sin fecha';
          return '<article class="cap-audit-item"><strong>' + auditActionLabel(item.accion) + '</strong><span>' + esc(actor) + ' · ' + esc(when) + '</span></article>';
        }).join('');
      })
      .catch(function () {
        if (auditStatusEl) auditStatusEl.textContent = 'No se pudo cargar el historial.';
      });
  }

  if (modalCloseBtn)  modalCloseBtn.addEventListener('click',  closeInscModal);
  if (modalCloseBtn2) modalCloseBtn2.addEventListener('click', closeInscModal);
  if (auditCloseBtn)  auditCloseBtn.addEventListener('click', closeAuditModal);

  if (modalInscBtn) {
    modalInscBtn.addEventListener('click', function () {
      if (!pendingInscCursoId) return;
      modalInscBtn.disabled = true;
      if (modalInscStatus) modalInscStatus.textContent = 'Inscribiendo…';
      apiJson('/api/capacitacion/inscribir', {
        method: 'POST',
        body: JSON.stringify({ curso_id: pendingInscCursoId }),
      }).then(function (res) {
        if (res.ok) {
          if (modalInscStatus) modalInscStatus.textContent = '¡Inscrito correctamente!';
          setTimeout(function () {
            closeInscModal();
            loadAll();
          }, 700);
        } else {
          var msg = (res.data && res.data.detail) ? res.data.detail : 'Error al inscribirse.';
          if (modalInscStatus) modalInscStatus.textContent = msg;
          modalInscBtn.disabled = false;
        }
      }).catch(function () {
        if (modalInscStatus) modalInscStatus.textContent = 'Error de conexión.';
        modalInscBtn.disabled = false;
      });
    });
  }

  // ── Tab: Mi progreso ──────────────────────────────────────────────────────────
  function renderProgresoTab() {
    var statusEl  = document.getElementById('cap-progreso-status');
    var tableEl   = document.getElementById('cap-progreso-table');
    if (!tableEl) return;
    if (misInscripciones.length === 0) {
      if (statusEl) statusEl.textContent = '';
      tableEl.innerHTML = '<div class="cap-empty">Aún no tienes inscripciones.</div>';
      return;
    }
    if (statusEl) statusEl.textContent = '';
    var html = '<div class="cap-table-wrap"><table class="cap-table"><thead><tr>' +
      '<th>Curso</th><th>Estado</th><th>Avance</th><th>Puntaje</th><th>Inscrito</th><th>Completado</th><th></th>' +
      '</tr></thead><tbody>';
    misInscripciones.forEach(function (insc) {
      var pct = insc.pct_avance || 0;
      html += '<tr>' +
        '<td class="wrap-cell"><strong>' + esc(insc.curso_nombre || 'Curso ' + insc.curso_id) + '</strong></td>' +
        '<td><span class="cap-badge ' + esc(insc.estado) + '">' + estadoLabel(insc.estado) + '</span></td>' +
        '<td><div style="display:flex;align-items:center;gap:6px;"><div class="cap-progress-bar" style="width:80px;"><div class="cap-progress-fill" style="width:' + pct + '%"></div></div><span style="font-size:12px;">' + fmtPct(pct) + '</span></div></td>' +
        '<td>' + (insc.puntaje_final != null ? insc.puntaje_final.toFixed(1) + '%' : '—') + '</td>' +
        '<td style="font-size:12px;">' + (insc.fecha_inscripcion ? insc.fecha_inscripcion.slice(0, 10) : '—') + '</td>' +
        '<td style="font-size:12px;">' + (insc.fecha_completado   ? insc.fecha_completado.slice(0, 10)   : '—') + '</td>' +
        '<td><a class="cap-btn is-outline is-sm" href="/capacitacion/curso/' + insc.curso_id + '">Ir al curso</a></td>' +
      '</tr>';
    });
    html += '</tbody></table></div>';
    tableEl.innerHTML = html;
  }

  // ── Gestión: categorías ───────────────────────────────────────────────────────
  function populateCursoCategoriasSelect() {
    var sel = document.getElementById('cap-curso-cat-select');
    if (!sel) return;
    sel.innerHTML = '<option value="">Sin categoría</option>';
    categorias.forEach(function (c) {
      var opt = document.createElement('option');
      opt.value = c.id;
      opt.textContent = c.nombre;
      sel.appendChild(opt);
    });
  }

  function renderCatTable() {
    var el = document.getElementById('cap-cat-table');
    if (!el) return;
    if (categorias.length === 0) { el.innerHTML = '<p class="cap-status-msg">Sin categorías registradas.</p>'; return; }
    var html = '<table class="cap-table" style="margin-top:12px;"><thead><tr><th>Nombre</th><th>Descripción</th><th>Color</th><th></th></tr></thead><tbody>';
    categorias.forEach(function (c) {
      html += '<tr>' +
        '<td><strong>' + esc(c.nombre) + '</strong></td>' +
        '<td>' + esc(c.descripcion || '—') + '</td>' +
        '<td>' + (c.color ? '<span style="display:inline-block;width:14px;height:14px;border-radius:4px;background:' + esc(c.color) + ';vertical-align:middle;margin-right:6px;"></span>' + esc(c.color) : '—') + '</td>' +
        '<td><button class="cap-btn is-danger is-sm" type="button" data-del-cat="' + c.id + '">Eliminar</button></td>' +
      '</tr>';
    });
    html += '</tbody></table>';
    el.innerHTML = html;
    Array.from(el.querySelectorAll('[data-del-cat]')).forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = parseInt(btn.getAttribute('data-del-cat'), 10);
        if (!confirm('¿Eliminar esta categoría?')) return;
        apiJson('/api/capacitacion/categorias/' + id, { method: 'DELETE' }).then(function (res) {
          if (res.ok) loadAll();
          else alert((res.data && res.data.detail) || 'Error al eliminar.');
        });
      });
    });
  }

  var formCat = document.getElementById('cap-form-categoria');
  if (formCat) {
    formCat.addEventListener('submit', function (e) {
      e.preventDefault();
      var statusEl = document.getElementById('cap-cat-status');
      var data = { nombre: formCat.nombre.value.trim(), color: formCat.color.value.trim() || null, descripcion: formCat.descripcion.value.trim() || null };
      if (!data.nombre) return;
      if (statusEl) statusEl.textContent = 'Guardando…';
      apiJson('/api/capacitacion/categorias', { method: 'POST', body: JSON.stringify(data) })
        .then(function (res) {
          if (res.ok) {
            if (statusEl) statusEl.textContent = 'Categoría guardada.';
            formCat.reset();
            loadAll();
          } else {
            if (statusEl) statusEl.textContent = (res.data && res.data.detail) || 'Error al guardar.';
          }
        });
    });
  }

  // ── Gestión: cursos ───────────────────────────────────────────────────────────
  function renderGestionCursos() {
    var statusEl = document.getElementById('cap-gestion-cursos-status');
    var tableEl  = document.getElementById('cap-gestion-cursos-table');
    if (!tableEl) return;
    if (statusEl) statusEl.textContent = '';
    var list = cursos;
    if (list.length === 0) { tableEl.innerHTML = '<p class="cap-status-msg">Sin cursos registrados.</p>'; return; }
    var html = '<table class="cap-table"><thead><tr>' +
      '<th>Código</th><th>Nombre</th><th>Nivel</th><th>Estado</th><th>Trazabilidad</th><th>Inscritos</th><th></th>' +
      '</tr></thead><tbody>';
    list.forEach(function (c) {
      html += '<tr>' +
        '<td style="font-size:12px;color:#94a3b8;">' + esc(c.codigo || '—') + '</td>' +
        '<td class="wrap-cell"><strong>' + esc(c.nombre) + '</strong></td>' +
        '<td><span class="cap-badge ' + esc(c.nivel) + '">' + nivelLabel(c.nivel) + '</span></td>' +
        '<td><span class="cap-badge ' + esc(c.estado) + '">' + cursoEstadoLabel(c.estado) + '</span></td>' +
        '<td style="font-size:12px;color:#475569;">' + auditSummary(c) + '</td>' +
        '<td>' + (c.total_inscripciones || 0) + '</td>' +
        '<td style="display:flex;gap:6px;">' +
          '<button class="cap-btn is-outline is-sm" type="button" data-audit-curso="' + c.id + '">Historial</button>' +
          '<button class="cap-btn is-outline is-sm" type="button" data-edit-curso="' + c.id + '">Editar</button>' +
          '<button class="cap-btn is-danger  is-sm" type="button" data-del-curso="' + c.id + '">Eliminar</button>' +
        '</td>' +
      '</tr>';
    });
    html += '</tbody></table>';
    tableEl.innerHTML = html;

    Array.from(tableEl.querySelectorAll('[data-del-curso]')).forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = parseInt(btn.getAttribute('data-del-curso'), 10);
        if (!confirm('¿Eliminar este curso y todas sus lecciones e inscripciones?')) return;
        apiJson('/api/capacitacion/cursos/' + id, { method: 'DELETE' }).then(function (res) {
          if (res.ok) loadAll();
          else alert((res.data && res.data.detail) || 'Error al eliminar.');
        });
      });
    });

    Array.from(tableEl.querySelectorAll('[data-edit-curso]')).forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = parseInt(btn.getAttribute('data-edit-curso'), 10);
        var curso = cursos.find(function (c) { return c.id === id; });
        if (!curso) return;
        populateCursoForm(curso);
        // Scroll to form
        var form = document.getElementById('cap-form-curso');
        if (form) form.scrollIntoView({ behavior: 'smooth', block: 'start' });
      });
    });
    Array.from(tableEl.querySelectorAll('[data-audit-curso]')).forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = parseInt(btn.getAttribute('data-audit-curso'), 10);
        var curso = cursos.find(function (item) { return item.id === id; });
        openAuditModal('curso', id, curso ? ('Historial · ' + curso.nombre) : 'Historial del curso');
      });
    });
  }

  function populateCursoForm(c) {
    var form = document.getElementById('cap-form-curso');
    if (!form) return;
    form.nombre.value             = c.nombre || '';
    form.categoria_id.value       = c.categoria_id || '';
    form.nivel.value              = c.nivel || 'basico';
    form.estado.value             = c.estado || 'borrador';
    form.responsable.value        = c.responsable || '';
    form.duracion_horas.value     = c.duracion_horas || '';
    form.puntaje_aprobacion.value = c.puntaje_aprobacion || 70;
    form.descripcion.value        = c.descripcion || '';
    form.objetivo.value           = c.objetivo || '';
    form.imagen_url.value         = c.imagen_url || '';
    form.fecha_inicio.value       = c.fecha_inicio || '';
    form.fecha_fin.value          = c.fecha_fin || '';
    form.es_obligatorio.checked   = Boolean(c.es_obligatorio);
    form.__curso_id.value         = c.id;
    var submitBtn = document.getElementById('cap-curso-submit-btn');
    var cancelBtn = document.getElementById('cap-curso-cancel-btn');
    if (submitBtn) submitBtn.textContent = 'Guardar cambios';
    if (cancelBtn) cancelBtn.style.display = '';
  }

  function resetCursoForm() {
    var form = document.getElementById('cap-form-curso');
    if (!form) return;
    form.reset();
    form.__curso_id.value = '';
    var submitBtn = document.getElementById('cap-curso-submit-btn');
    var cancelBtn = document.getElementById('cap-curso-cancel-btn');
    if (submitBtn) submitBtn.textContent = 'Crear curso';
    if (cancelBtn) cancelBtn.style.display = 'none';
  }

  var formCurso  = document.getElementById('cap-form-curso');
  var cancelBtn  = document.getElementById('cap-curso-cancel-btn');
  if (cancelBtn) cancelBtn.addEventListener('click', resetCursoForm);

  if (formCurso) {
    formCurso.addEventListener('submit', function (e) {
      e.preventDefault();
      var statusEl = document.getElementById('cap-curso-form-status');
      var cursoId  = formCurso.__curso_id.value ? parseInt(formCurso.__curso_id.value, 10) : null;
      var data = {
        nombre:             formCurso.nombre.value.trim(),
        categoria_id:       formCurso.categoria_id.value ? parseInt(formCurso.categoria_id.value, 10) : null,
        nivel:              formCurso.nivel.value,
        estado:             formCurso.estado.value,
        responsable:        formCurso.responsable.value.trim() || null,
        duracion_horas:     formCurso.duracion_horas.value ? parseFloat(formCurso.duracion_horas.value) : null,
        puntaje_aprobacion: parseFloat(formCurso.puntaje_aprobacion.value) || 70,
        descripcion:        formCurso.descripcion.value.trim() || null,
        objetivo:           formCurso.objetivo.value.trim() || null,
        imagen_url:         formCurso.imagen_url.value.trim() || null,
        fecha_inicio:       formCurso.fecha_inicio.value || null,
        fecha_fin:          formCurso.fecha_fin.value || null,
        es_obligatorio:     formCurso.es_obligatorio.checked,
      };
      if (!data.nombre) return;
      if (statusEl) statusEl.textContent = 'Guardando…';
      var url    = cursoId ? '/api/capacitacion/cursos/' + cursoId : '/api/capacitacion/cursos';
      var method = cursoId ? 'PUT' : 'POST';
      apiJson(url, { method: method, body: JSON.stringify(data) }).then(function (res) {
        if (res.ok) {
          if (statusEl) statusEl.textContent = cursoId ? 'Curso actualizado.' : 'Curso creado.';
          resetCursoForm();
          loadAll();
        } else {
          if (statusEl) statusEl.textContent = (res.data && res.data.detail) || 'Error al guardar.';
        }
      });
    });
  }

  // ── Tabs ──────────────────────────────────────────────────────────────────────
  tabButtons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var tab = btn.getAttribute('data-cap-tab');
      currentTab = tab;
      tabButtons.forEach(function (b) { b.classList.toggle('is-active', b.getAttribute('data-cap-tab') === tab); });
      panels.forEach(function (p) { p.classList.toggle('is-active', p.getAttribute('data-cap-panel') === tab); });
      // Ocultar toolbar en tabs sin vista
      var toolbarEl = document.querySelector('#cap-root .cap-toolbar');
      if (toolbarEl) toolbarEl.style.display = tab === 'catalogo' ? '' : 'none';
      if (tab === 'mi-progreso') renderProgresoTab();
      if (tab === 'gestion' && isAdmin) { renderCatTable(); renderGestionCursos(); populateCursoCategoriasSelect(); }
    });
  });

  // ── View pills ────────────────────────────────────────────────────────────────
  viewButtons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      currentView = btn.getAttribute('data-cap-view');
      viewButtons.forEach(function (b) { b.classList.toggle('active', b === btn); });
      renderCurrentView();
    });
  });

  // ── Filtros ───────────────────────────────────────────────────────────────────
  if (searchInput) {
    searchInput.addEventListener('input', function () { filterSearch = searchInput.value; renderCurrentView(); });
  }
  if (filterCatEl) {
    filterCatEl.addEventListener('change', function () { filterCat = filterCatEl.value; renderCurrentView(); });
  }
  if (filterNivelEl) {
    filterNivelEl.addEventListener('change', function () { filterNivel = filterNivelEl.value; renderCurrentView(); });
  }
  if (filterEstadoEl) {
    filterEstadoEl.addEventListener('change', function () { filterEstado = filterEstadoEl.value; renderCurrentView(); });
  }

  // ── Init ──────────────────────────────────────────────────────────────────────
  loadAll();
})();
