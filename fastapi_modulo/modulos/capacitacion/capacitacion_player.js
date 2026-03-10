/* capacitacion_player.js — Course Player v20260309 */
(function () {
  'use strict';

  var root = document.getElementById('cp-root');
  if (!root) return;
  var cursoId = parseInt(root.getAttribute('data-curso-id'), 10);
  if (!cursoId) return;

  // ── Estado ───────────────────────────────────────────────────────────────────
  var curso        = null;
  var lecciones    = [];
  var inscripcion  = null;
  var progresos    = {};   // { leccion_id: CapProgresoLeccion }
  var evaluaciones = [];
  var activeLeccionIdx = -1;
  var markingComplete  = false;

  // ── Selectores ────────────────────────────────────────────────────────────────
  var layoutEl       = document.getElementById('cp-layout');
  var mainStatus     = document.getElementById('cp-main-status');
  var cursoTitleEl   = document.getElementById('cp-curso-title');
  var cursoMetaEl    = document.getElementById('cp-curso-meta');
  var progressFill   = document.getElementById('cp-progress-fill');
  var progressPct    = document.getElementById('cp-progress-pct');
  var lessonCount    = document.getElementById('cp-lesson-count');
  var lessonList     = document.getElementById('cp-lesson-list');
  var courseInfo     = document.getElementById('cp-course-info');
  var lessonTitle    = document.getElementById('cp-lesson-title');
  var lessonMeta     = document.getElementById('cp-lesson-meta');
  var lessonDoneBadge= document.getElementById('cp-lesson-done-badge');
  var playerContent  = document.getElementById('cp-player-content');
  var playerFooter   = document.getElementById('cp-player-footer');
  var btnPrev        = document.getElementById('cp-btn-prev');
  var btnNext        = document.getElementById('cp-btn-next');
  var btnComplete    = document.getElementById('cp-btn-complete');
  var evalBanner     = document.getElementById('cp-eval-banner');
  var evalBannerDesc = document.getElementById('cp-eval-banner-desc');
  var btnGoEval      = document.getElementById('cp-btn-go-eval');

  // ── Utilidades ────────────────────────────────────────────────────────────────
  function esc(v) {
    return String(v == null ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function apiJson(url, opts) {
    return fetch(url, Object.assign({ headers: { 'Content-Type': 'application/json' } }, opts || {}))
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, status: r.status, data: d }; }); });
  }

  function typeLabel(t) {
    return { texto: 'Texto', video: 'Video', documento: 'Documento', enlace: 'Enlace externo' }[t] || t;
  }

  function typeIcon(t) {
    return { texto: '📄', video: '▶️', documento: '📎', enlace: '🔗' }[t] || '📄';
  }

  function isLeccionDone(lid) {
    var p = progresos[lid];
    return p && p.completada;
  }

  // ── Carga ─────────────────────────────────────────────────────────────────────
  function loadAll() {
    if (mainStatus) mainStatus.textContent = 'Cargando curso…';
    Promise.all([
      apiJson('/api/capacitacion/cursos/' + cursoId + '?con_lecciones=true'),
      apiJson('/api/capacitacion/mis-inscripciones'),
      apiJson('/api/capacitacion/cursos/' + cursoId + '/evaluaciones'),
    ]).then(function (results) {
      var cursoRes  = results[0];
      var inscRes   = results[1];
      var evalRes   = results[2];

      if (!cursoRes.ok) {
        if (mainStatus) mainStatus.textContent = 'Curso no encontrado.';
        return;
      }
      curso      = cursoRes.data;
      lecciones  = Array.isArray(curso.lecciones) ? curso.lecciones : [];
      evaluaciones = Array.isArray(evalRes.data) ? evalRes.data : [];

      var misInscs = Array.isArray(inscRes.data) ? inscRes.data : [];
      inscripcion  = misInscs.find(function (i) { return i.curso_id === cursoId; }) || null;

      if (mainStatus) mainStatus.textContent = '';
      renderHeader();
      renderSidebar();
      renderCourseInfo();
      if (layoutEl) layoutEl.style.display = '';

      if (inscripcion) {
        // Cargar progresos
        apiJson('/api/capacitacion/inscripciones/' + inscripcion.id + '/progreso')
          .then(function (r) {
            if (r.ok && Array.isArray(r.data)) {
              r.data.forEach(function (p) { progresos[p.leccion_id] = p; });
            }
            renderSidebar();
            updateProgress();
            checkEvalBanner();
            // Abrir primera lección no completada o la primera
            var firstPending = lecciones.findIndex(function (l) { return !isLeccionDone(l.id); });
            selectLesson(firstPending >= 0 ? firstPending : 0);
          });
      } else {
        // No inscripto — mostrar primera lección de preview
        selectLesson(0);
      }
    }).catch(function () {
      if (mainStatus) mainStatus.textContent = 'Error al cargar el curso.';
    });
  }

  // ── Header / progreso ─────────────────────────────────────────────────────────
  function renderHeader() {
    if (cursoTitleEl) cursoTitleEl.textContent = curso.nombre || '';
    if (cursoMetaEl) {
      var badges = '';
      if (curso.nivel)     badges += '<span class="cp-badge ' + esc(curso.nivel) + '">' + esc({basico:'Básico',intermedio:'Intermedio',avanzado:'Avanzado'}[curso.nivel] || curso.nivel) + '</span>';
      if (curso.categoria_nombre) badges += '<span style="font-size:12px;color:#475569;">' + esc(curso.categoria_nombre) + '</span>';
      if (curso.duracion_horas) badges += '<span style="font-size:12px;color:#94a3b8;">' + curso.duracion_horas + ' h</span>';
      cursoMetaEl.innerHTML = badges;
    }
    updateProgress();
  }

  function updateProgress() {
    var pct = inscripcion ? (inscripcion.pct_avance || 0) : 0;
    if (progressFill) progressFill.style.width = pct + '%';
    if (progressPct)  progressPct.textContent   = pct.toFixed(0) + '%';
  }

  // ── Sidebar ───────────────────────────────────────────────────────────────────
  function renderSidebar() {
    if (!lessonList) return;
    if (lessonCount) lessonCount.textContent = lecciones.length;
    var html = '';
    lecciones.forEach(function (l, idx) {
      var done   = isLeccionDone(l.id);
      var active = idx === activeLeccionIdx;
      var dur    = l.duracion_min ? l.duracion_min + ' min' : '';
      html += '<li class="cp-lesson-item' + (done ? ' is-done' : '') + (active ? ' is-active' : '') + '" data-lesson-idx="' + idx + '">' +
        '<span class="cp-lesson-check">' + (done ? '✓' : '') + '</span>' +
        '<span class="cp-lesson-type-icon">' + typeIcon(l.tipo) + '</span>' +
        '<span class="cp-lesson-title">' + esc(l.titulo) + '</span>' +
        (dur ? '<span class="cp-lesson-dur">' + esc(dur) + '</span>' : '') +
      '</li>';
    });
    lessonList.innerHTML = html;
    Array.from(lessonList.querySelectorAll('[data-lesson-idx]')).forEach(function (li) {
      li.addEventListener('click', function () {
        selectLesson(parseInt(li.getAttribute('data-lesson-idx'), 10));
      });
    });
  }

  function renderCourseInfo() {
    if (!courseInfo) return;
    var rows = '';
    if (curso.responsable)        rows += infoRow('Instructor', esc(curso.responsable));
    if (curso.puntaje_aprobacion) rows += infoRow('Aprobación', curso.puntaje_aprobacion + '%');
    if (curso.fecha_fin)          rows += infoRow('Fecha límite', esc(curso.fecha_fin));
    if (lecciones.length)         rows += infoRow('Total lecciones', lecciones.length);
    var oblCount = lecciones.filter(function (l) { return l.es_obligatoria; }).length;
    if (oblCount) rows += infoRow('Obligatorias', oblCount);
    if (evaluaciones.length)      rows += infoRow('Evaluaciones', evaluaciones.length);
    courseInfo.innerHTML = rows;
  }

  function infoRow(label, val) {
    return '<div class="cp-info-row"><span class="cp-info-label">' + label + '</span><span class="cp-info-value">' + val + '</span></div>';
  }

  // ── Seleccionar lección ───────────────────────────────────────────────────────
  function selectLesson(idx) {
    if (idx < 0 || idx >= lecciones.length) return;
    activeLeccionIdx = idx;
    var l = lecciones[idx];
    var done = isLeccionDone(l.id);

    // Header del player
    if (lessonTitle) lessonTitle.textContent = l.titulo;
    if (lessonMeta) {
      lessonMeta.innerHTML = '<span class="cp-badge ' + esc(l.tipo) + '">' + typeLabel(l.tipo) + '</span>' +
        (l.duracion_min ? '<span style="font-size:12px;color:#94a3b8;">' + l.duracion_min + ' min</span>' : '') +
        (!l.es_obligatoria ? '<span style="font-size:12px;color:#94a3b8;">Opcional</span>' : '');
    }
    if (lessonDoneBadge) {
      lessonDoneBadge.innerHTML = done
        ? '<span class="cp-badge completada">✓ Completada</span>'
        : '<span class="cp-badge pendiente">Pendiente</span>';
    }

    // Contenido
    renderLessonContent(l);

    // Footer
    if (playerFooter) playerFooter.style.display = '';
    if (btnPrev) { btnPrev.disabled = idx === 0; }
    if (btnNext) { btnNext.disabled = idx === lecciones.length - 1; }
    if (btnComplete) {
      if (done) {
        btnComplete.textContent = '✓ Completada';
        btnComplete.className   = 'cp-btn is-green';
        btnComplete.disabled    = true;
      } else {
        if (!inscripcion) {
          btnComplete.textContent = 'Inscribirse para completar';
          btnComplete.className   = 'cp-btn is-outline';
          btnComplete.disabled    = false;
        } else {
          btnComplete.textContent = '✓ Marcar como completada';
          btnComplete.className   = 'cp-btn is-green';
          btnComplete.disabled    = false;
        }
      }
    }

    // Actualizar sidebar
    renderSidebar();
  }

  // ── Render de contenido según tipo ───────────────────────────────────────────
  function renderLessonContent(l) {
    if (!playerContent) return;
    if (l.tipo === 'video') {
      var embedUrl = resolveVideoEmbed(l.url_archivo || l.contenido || '');
      if (embedUrl) {
        playerContent.innerHTML = '<div class="cp-video-wrap"><iframe src="' + esc(embedUrl) + '" allowfullscreen allow="autoplay; fullscreen"></iframe></div>';
      } else {
        playerContent.innerHTML = '<p class="cp-status-msg">No se encontró URL de video.</p>';
      }
    } else if (l.tipo === 'documento') {
      var pdfUrl = l.url_archivo || '';
      if (pdfUrl) {
        playerContent.innerHTML = '<div class="cp-pdf-wrap"><embed src="' + esc(pdfUrl) + '" type="application/pdf" /></div>';
      } else if (l.contenido) {
        playerContent.innerHTML = '<div class="cp-text-content">' + l.contenido + '</div>';
      } else {
        playerContent.innerHTML = '<p class="cp-status-msg">Sin documento adjunto.</p>';
      }
    } else if (l.tipo === 'enlace') {
      var href = l.url_archivo || l.contenido || '';
      playerContent.innerHTML = '<div class="cp-link-content">' +
        '<p style="color:#475569;font-size:14px;">Este recurso se abre en una nueva ventana.</p>' +
        (href ? '<a href="' + esc(href) + '" target="_blank" rel="noopener noreferrer">🔗 Abrir enlace externo</a>' : '<p class="cp-status-msg">Sin enlace disponible.</p>') +
        (l.contenido && l.contenido !== href ? '<div class="cp-text-content" style="text-align:left;margin-top:10px;">' + l.contenido + '</div>' : '') +
      '</div>';
    } else {
      // texto (default)
      var html = l.contenido
        ? '<div class="cp-text-content">' + l.contenido + '</div>'
        : '<p class="cp-status-msg">Sin contenido de texto.</p>';
      playerContent.innerHTML = html;
    }
  }

  // ── Resolver URL de embed para video ──────────────────────────────────────────
  function resolveVideoEmbed(url) {
    if (!url) return '';
    // YouTube
    var ytMatch = url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([A-Za-z0-9_\-]{11})/);
    if (ytMatch) return 'https://www.youtube.com/embed/' + ytMatch[1];
    // Vimeo
    var vmMatch = url.match(/vimeo\.com\/(\d+)/);
    if (vmMatch) return 'https://player.vimeo.com/video/' + vmMatch[1];
    // Si ya es una URL directa de embed o archivo
    return url;
  }

  // ── Navegación prev/next ──────────────────────────────────────────────────────
  if (btnPrev) {
    btnPrev.addEventListener('click', function () { selectLesson(activeLeccionIdx - 1); });
  }
  if (btnNext) {
    btnNext.addEventListener('click', function () { selectLesson(activeLeccionIdx + 1); });
  }

  // ── Marcar completada ─────────────────────────────────────────────────────────
  if (btnComplete) {
    btnComplete.addEventListener('click', function () {
      if (!inscripcion) {
        // Inscribirse primero
        apiJson('/api/capacitacion/inscribir', {
          method: 'POST',
          body: JSON.stringify({ curso_id: cursoId }),
        }).then(function (res) {
          if (res.ok) {
            inscripcion = res.data;
            markLeccionComplete();
          } else {
            alert((res.data && res.data.detail) || 'Error al inscribirse.');
          }
        });
        return;
      }
      markLeccionComplete();
    });
  }

  function markLeccionComplete() {
    if (markingComplete || activeLeccionIdx < 0) return;
    var l = lecciones[activeLeccionIdx];
    if (isLeccionDone(l.id)) return;
    markingComplete = true;
    if (btnComplete) { btnComplete.disabled = true; btnComplete.textContent = 'Guardando…'; }
    apiJson('/api/capacitacion/progreso', {
      method: 'POST',
      body: JSON.stringify({ inscripcion_id: inscripcion.id, leccion_id: l.id }),
    }).then(function (res) {
      markingComplete = false;
      if (res.ok) {
        progresos[l.id] = res.data;
        // Actualizar pct_avance en inscripcion local
        var doneLecObl = Object.values(progresos).filter(function (p) {
          if (!p.completada) return false;
          var lec = lecciones.find(function (x) { return x.id === p.leccion_id; });
          return lec && lec.es_obligatoria;
        }).length;
        var totalObl = lecciones.filter(function (l) { return l.es_obligatoria; }).length;
        inscripcion.pct_avance = totalObl > 0 ? Math.round(doneLecObl / totalObl * 100) : 100;
        updateProgress();
        selectLesson(activeLeccionIdx);
        checkEvalBanner();
        // Auto-avanzar a siguiente lección
        if (activeLeccionIdx < lecciones.length - 1) {
          setTimeout(function () { selectLesson(activeLeccionIdx + 1); }, 500);
        }
      } else {
        if (btnComplete) { btnComplete.disabled = false; btnComplete.textContent = '✓ Marcar como completada'; }
        alert((res.data && res.data.detail) || 'Error al guardar progreso.');
      }
    }).catch(function () {
      markingComplete = false;
      if (btnComplete) { btnComplete.disabled = false; btnComplete.textContent = '✓ Marcar como completada'; }
    });
  }

  // ── Banner evaluación ──────────────────────────────────────────────────────────
  function checkEvalBanner() {
    if (!evalBanner) return;
    var totalObl  = lecciones.filter(function (l) { return l.es_obligatoria; }).length;
    var doneObl   = lecciones.filter(function (l) {
      return l.es_obligatoria && isLeccionDone(l.id);
    }).length;
    var cursoCompletado = inscripcion && inscripcion.estado === 'completado';

    if (evaluaciones.length > 0 && totalObl > 0 && doneObl >= totalObl && !cursoCompletado) {
      evalBanner.style.display = '';
      var ev = evaluaciones[0];
      if (evalBannerDesc) {
        evalBannerDesc.textContent = 'Evaluación: "' + ev.titulo + '" — puntaje mínimo ' + ev.puntaje_minimo + '%.';
      }
      if (btnGoEval) {
        btnGoEval.onclick = function () {
          window.location.href = '/capacitacion/evaluacion/' + ev.id + '?insc=' + inscripcion.id;
        };
      }
    } else if (cursoCompletado) {
      evalBanner.style.display = '';
      evalBanner.style.background = 'linear-gradient(135deg,#14532d 0%,#16a34a 100%)';
      evalBanner.innerHTML = '<div><h3>🎉 ¡Curso completado!</h3><p>Ya cuentas con tu certificado.</p></div>' +
        '<a class="cp-btn" href="/capacitacion/mis-certificados" style="background:#fff;color:#15803d;font-weight:700;">Ver certificado</a>';
    } else {
      evalBanner.style.display = 'none';
    }
  }

  // ── Init ──────────────────────────────────────────────────────────────────────
  loadAll();
})();
