/* capacitacion_visor.js — Visor de presentaciones v20260309 */
(function () {
  'use strict';

  function el(id) { return document.getElementById(id); }

  function esc(v) {
    return String(v == null ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  function embedUrl(url) {
    if (!url) return '';
    var yt = url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([A-Za-z0-9_-]{11})/);
    if (yt) return 'https://www.youtube.com/embed/' + yt[1];
    var vm = url.match(/vimeo\.com\/(\d+)/);
    if (vm) return 'https://player.vimeo.com/video/' + vm[1];
    return url;
  }

  function apiJson(url) {
    return fetch(url, { headers: { 'Content-Type': 'application/json' } })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); });
  }

  // ── State ─────────────────────────────────────────────────────────────────

  var presId  = parseInt((el('visor-root') || {}).dataset.presId || '0', 10);
  var searchParams = new URLSearchParams(window.location.search || '');
  var presentMode = searchParams.get('present') === '1';
  var pres    = null;
  var slides  = [];
  var liveSurveys = [];
  var surveyAnalytics = {};
  var curIdx  = 0;
  var surveyModal = el('visor-survey-modal');
  var surveyFrame = el('visor-survey-frame');
  var surveyTitle = el('visor-survey-title');
  var resultsModal = el('visor-results-modal');
  var resultsTitle = el('visor-results-title');
  var resultsBody = el('visor-results-body');
  var analyticsPollTimer = null;
  var currentResultsSurveyId = null;

  function presentationTarget() {
    return document.querySelector('.visor-slide-wrapper') || el('visor-root') || document.documentElement;
  }

  function requestPresentationFullscreen() {
    var target = presentationTarget();
    if (!target || document.fullscreenElement || !target.requestFullscreen) return Promise.resolve();
    return target.requestFullscreen().catch(function () {});
  }

  function setPresentMode(enabled) {
    var root = el('visor-root');
    if (!root) return;
    root.classList.toggle('is-present-mode', !!enabled);
  }

  function getSurveyById(surveyId) {
    return liveSurveys.find(function (item) { return String(item.id) === String(surveyId); }) || null;
  }

  function analyticsSummary(surveyId) {
    var data = surveyAnalytics[String(surveyId)] || {};
    var summary = data.summary || {};
    return {
      responses: Number(summary.responses_count || 0),
      completion: Number(summary.completion_pct_avg || 0),
      nps: summary.nps_score != null ? Number(summary.nps_score) : null,
      score: summary.total_score_avg != null ? Number(summary.total_score_avg) : null,
    };
  }

  function analyticsBadges(surveyId, light) {
    var summary = analyticsSummary(surveyId);
    var toneBg = light ? 'rgba(15,23,42,.08)' : 'rgba(255,255,255,.12)';
    var toneText = light ? '#0f172a' : '#eff6ff';
    return '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:14px;">' +
      '<span style="padding:6px 10px;border-radius:999px;background:' + toneBg + ';color:' + toneText + ';font-size:12px;font-weight:700;">Resp. ' + summary.responses + '</span>' +
      '<span style="padding:6px 10px;border-radius:999px;background:' + toneBg + ';color:' + toneText + ';font-size:12px;font-weight:700;">Fin. ' + summary.completion + '%</span>' +
      (summary.nps == null ? '' : '<span style="padding:6px 10px;border-radius:999px;background:' + toneBg + ';color:' + toneText + ';font-size:12px;font-weight:700;">NPS ' + summary.nps + '</span>') +
      (summary.score == null ? '' : '<span style="padding:6px 10px;border-radius:999px;background:' + toneBg + ';color:' + toneText + ';font-size:12px;font-weight:700;">Score ' + summary.score + '</span>') +
    '</div>';
  }

  function loadSurveyAnalytics() {
    if (!liveSurveys.length) return Promise.resolve();
    return Promise.all(liveSurveys.map(function (survey) {
      return apiJson('/api/encuestas/campanas/' + survey.id + '/analytics')
        .then(function (res) {
          if (res.ok) surveyAnalytics[String(survey.id)] = res.data || {};
        })
        .catch(function () {});
    }));
  }

  function openSurveyModal(survey) {
    if (!surveyModal || !surveyFrame || !survey) return;
    if (surveyTitle) surveyTitle.textContent = survey.nombre || 'Encuesta live';
    surveyFrame.src = '/encuestas/responder/' + survey.id + '?embed=1&curso_id=' + (pres && pres.curso_id ? pres.curso_id : '');
    surveyModal.classList.add('is-open');
  }

  function closeSurveyModal() {
    if (!surveyModal || !surveyFrame) return;
    surveyModal.classList.remove('is-open');
    surveyFrame.src = 'about:blank';
  }

  function metricValue(value, suffix, fallback) {
    if (value == null || value === '') return fallback || 'N/A';
    return String(value) + (suffix || '');
  }

  function renderResultsModal(survey) {
    if (!resultsBody || !survey) return;
    var analytics = surveyAnalytics[String(survey.id)] || {};
    var summary = analytics.summary || {};
    var comparison = analytics.comparison_report || [];
    var questions = analytics.question_report || [];
    var segments = [];
    Object.keys(analytics.segment_report || {}).forEach(function (groupKey) {
      (analytics.segment_report[groupKey] || []).forEach(function (item) {
        segments.push(item);
      });
    });
    resultsBody.innerHTML =
      '<section class="visor-results-kpis">' +
        '<article class="visor-results-kpi"><span>Respuestas</span><strong>' + metricValue(summary.responses_count, '', '0') + '</strong></article>' +
        '<article class="visor-results-kpi"><span>Finalización</span><strong>' + metricValue(summary.completion_pct_avg, '%', '0%') + '</strong></article>' +
        '<article class="visor-results-kpi"><span>Score</span><strong>' + metricValue(summary.total_score_avg, '', 'N/A') + '</strong></article>' +
        '<article class="visor-results-kpi"><span>NPS</span><strong>' + metricValue(summary.nps_score, '', 'N/A') + '</strong></article>' +
        '<article class="visor-results-kpi"><span>CSAT</span><strong>' + metricValue(summary.csat_score, '', 'N/A') + '</strong></article>' +
        '<article class="visor-results-kpi"><span>CES</span><strong>' + metricValue(summary.ces_score, '', 'N/A') + '</strong></article>' +
      '</section>' +
      '<section class="visor-results-section"><h3>Preguntas</h3>' +
        (questions.length ? questions.slice(0, 8).map(function (item) {
          var detail = (item.options || []).length
            ? item.options.map(function (option) { return (option.label || 'Opción') + ': ' + (option.count || 0); }).join(' · ')
            : ((item.sample_answers || []).join(' · ') || 'Sin muestras todavía');
          return '<article class="visor-results-card"><strong>' + esc((item.section_title ? item.section_title + ' · ' : '') + (item.question_title || 'Pregunta')) + '</strong><p>' + esc((item.question_type || 'Pregunta') + ' · ' + (item.responses_count || 0) + ' respuesta(s)') + '</p><p>' + esc(detail) + '</p></article>';
        }).join('') : '<div class="visor-results-empty">Todavía no hay respuestas suficientes para construir el detalle de preguntas.</div>') +
      '</section>' +
      '<section class="visor-results-section"><h3>Segmentos</h3><div class="visor-results-grid">' +
        (segments.length ? segments.slice(0, 6).map(function (item) {
          return '<article class="visor-results-card"><strong>' + esc((item.label || 'Segmento') + ': ' + (item.segment || 'Sin dato')) + '</strong><p>' + esc((item.responses || 0) + ' respuesta(s) · Finalización ' + metricValue(item.completion_pct_avg, '%', '0%')) + '</p><p>' + esc('Score ' + metricValue(item.score_avg, '', 'N/A')) + '</p></article>';
        }).join('') : '<div class="visor-results-empty">No hay segmentos disponibles para el filtro actual.</div>') +
      '</div></section>' +
      '<section class="visor-results-section"><h3>Comparativo</h3><div class="visor-results-grid">' +
        (comparison.length ? comparison.slice(0, 6).map(function (item) {
          return '<article class="visor-results-card"><strong>' + esc(item.segment || 'Sin dato') + '</strong><p>' + esc((item.responses || 0) + ' respuesta(s) · Finalización ' + metricValue(item.completion_pct_avg, '%', '0%')) + '</p><p>' + esc('Score ' + metricValue(item.total_score_avg, '', 'N/A') + ' · NPS ' + metricValue(item.nps_score, '', 'N/A')) + '</p></article>';
        }).join('') : '<div class="visor-results-empty">El comparativo aparecerá cuando existan datos segmentados.</div>') +
      '</div></section>';
  }

  function openResultsModal(survey) {
    if (!resultsModal || !resultsBody || !survey) return;
    currentResultsSurveyId = String(survey.id);
    if (resultsTitle) resultsTitle.textContent = survey.nombre || 'Resultado en vivo';
    renderResultsModal(survey);
    resultsModal.classList.add('is-open');
  }

  function closeResultsModal() {
    if (!resultsModal || !resultsBody) return;
    resultsModal.classList.remove('is-open');
    currentResultsSurveyId = null;
    resultsBody.innerHTML = '';
  }

  function hydrateSurveyWidgets(scope) {
    if (!scope) return;
    Array.prototype.slice.call(scope.querySelectorAll('.cap-live-survey-widget')).forEach(function (node) {
      var surveyId = String(node.getAttribute('data-survey-id') || '').trim();
      var mode = String(node.getAttribute('data-widget-mode') || 'card').trim().toLowerCase();
      var buttonLabel = String(node.getAttribute('data-button-label') || 'Responder encuesta').trim();
      var survey = getSurveyById(surveyId) || liveSurveys[0] || null;
      if (!survey) {
        node.innerHTML = '<div style="padding:22px;border-radius:20px;background:#0f172a;color:#eff6ff;"><strong>Sin encuestas live</strong><p style="margin:10px 0 0;color:#cbd5e1;">Vincula una encuesta tipo Mentimeter al curso para usar este widget.</p></div>';
        return;
      }
      if (mode === 'embed') {
        node.innerHTML = '<div style="border-radius:24px;overflow:hidden;box-shadow:0 18px 40px rgba(15,23,42,.18);background:#fff;">' +
          '<iframe src="/encuestas/responder/' + survey.id + '?embed=1&curso_id=' + (pres && pres.curso_id ? pres.curso_id : '') + '" style="width:100%;min-height:540px;border:0;display:block;background:#fff;"></iframe>' +
          '<div style="padding:16px 18px;background:#fff;">' + analyticsBadges(survey.id, true) + '<div style="margin-top:14px;"><button type="button" data-open-survey-results="' + survey.id + '" style="display:inline-flex;align-items:center;justify-content:center;padding:11px 16px;border-radius:999px;background:#0f172a;color:#eff6ff;font-weight:800;border:0;cursor:pointer;">Ver resultado en vivo</button></div></div>' +
        '</div>';
        return;
      }
      node.innerHTML = '<div style="padding:26px 30px;border-radius:24px;background:linear-gradient(135deg,#0f172a,#1d4ed8);color:#eff6ff;box-shadow:0 22px 44px rgba(15,23,42,.24);">' +
        '<div style="font-size:12px;text-transform:uppercase;letter-spacing:.18em;opacity:.72;margin-bottom:10px;">Encuesta live</div>' +
        '<h3 style="margin:0 0 8px;font-size:30px;line-height:1.05;">' + esc(survey.nombre || 'Encuesta live') + '</h3>' +
        '<p style="margin:0;font-size:16px;line-height:1.6;color:#dbeafe;">' + esc(survey.descripcion || 'Participa en esta dinámica interactiva del curso.') + '</p>' +
        analyticsBadges(survey.id, false) +
        '<div style="margin-top:18px;display:flex;gap:10px;flex-wrap:wrap;"><button type="button" data-open-survey-modal="' + survey.id + '" style="display:inline-flex;align-items:center;justify-content:center;padding:12px 20px;border-radius:999px;background:#ff8a00;color:#231100;text-decoration:none;font-weight:800;border:0;cursor:pointer;">' + esc(buttonLabel) + '</button><button type="button" data-open-survey-results="' + survey.id + '" style="display:inline-flex;align-items:center;justify-content:center;padding:12px 20px;border-radius:999px;background:rgba(255,255,255,.14);color:#eff6ff;text-decoration:none;font-weight:800;border:1px solid rgba(255,255,255,.22);cursor:pointer;">Ver resultado en vivo</button></div>' +
      '</div>';
    });

    Array.prototype.slice.call(scope.querySelectorAll('.cap-live-survey-list-widget')).forEach(function (node) {
      var mode = String(node.getAttribute('data-widget-mode') || 'cards').trim().toLowerCase();
      if (!liveSurveys.length) {
        node.innerHTML = '<div style="padding:22px;border-radius:20px;background:#f8fafc;border:1px dashed #cbd5e1;color:#475569;">No hay encuestas live vinculadas al curso.</div>';
        return;
      }
      if (mode === 'list') {
        node.innerHTML = '<div style="padding:26px;border-radius:24px;background:#f8fafc;"><h3 style="margin:0 0 12px;font-size:28px;color:#0f172a;">Encuestas del curso</h3>' +
          '<ul style="margin:0;padding-left:18px;color:#334155;font-size:16px;line-height:1.8;">' +
          liveSurveys.map(function (survey) {
            return '<li><button type="button" data-open-survey-modal="' + survey.id + '" style="border:0;background:none;color:#1d4ed8;text-decoration:none;font-weight:700;padding:0;cursor:pointer;">' + esc(survey.nombre || ('Encuesta ' + survey.id)) + '</button> <span style="color:#64748b;">· ' + analyticsSummary(survey.id).responses + ' resp.</span></li>';
          }).join('') +
          '</ul></div>';
        return;
      }
      node.innerHTML = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;">' +
        liveSurveys.map(function (survey) {
          return '<article style="padding:22px;border-radius:24px;background:linear-gradient(180deg,#ffffff,#eff6ff);box-shadow:0 18px 32px rgba(15,23,42,.12);">' +
            '<div style="font-size:11px;text-transform:uppercase;letter-spacing:.14em;color:#f97316;margin-bottom:8px;">Mentimeter</div>' +
            '<strong style="display:block;font-size:22px;line-height:1.08;color:#0f172a;">' + esc(survey.nombre || ('Encuesta ' + survey.id)) + '</strong>' +
            '<p style="margin:10px 0 0;font-size:15px;line-height:1.6;color:#475569;">' + esc(survey.descripcion || 'Disponible durante la sesión.') + '</p>' +
            analyticsBadges(survey.id, true) +
            '<div style="margin-top:16px;display:flex;gap:10px;flex-wrap:wrap;"><button type="button" data-open-survey-modal="' + survey.id + '" style="display:inline-flex;padding:11px 16px;border-radius:999px;background:#0f172a;color:#eff6ff;text-decoration:none;font-weight:800;border:0;cursor:pointer;">Abrir</button><button type="button" data-open-survey-results="' + survey.id + '" style="display:inline-flex;padding:11px 16px;border-radius:999px;background:#e2e8f0;color:#0f172a;text-decoration:none;font-weight:800;border:0;cursor:pointer;">Ver resultado en vivo</button></div>' +
          '</article>';
        }).join('') +
      '</div>';
    });
    Array.prototype.slice.call(scope.querySelectorAll('.cap-live-survey-hotspot')).forEach(function (node) {
      var surveyId = String(node.getAttribute('data-survey-id') || '').trim();
      var label = String(node.getAttribute('data-hotspot-label') || 'Abrir encuesta').trim();
      var survey = getSurveyById(surveyId) || liveSurveys[0] || null;
      if (!survey) {
        node.innerHTML = '';
        return;
      }
      node.innerHTML = '<button type="button" data-open-survey-modal="' + survey.id + '" aria-label="' + esc(label) + '" title="' + esc(label) + '" style="position:relative;display:inline-flex;align-items:center;justify-content:center;width:54px;height:54px;border-radius:999px;border:0;background:#ff8a00;color:#231100;font-size:22px;font-weight:900;cursor:pointer;box-shadow:0 0 0 16px rgba(255,138,0,.16), 0 18px 30px rgba(15,23,42,.22);animation:capSurveyPulse 1.8s ease-out infinite;">+</button>';
    });
    Array.prototype.slice.call(scope.querySelectorAll('[data-open-survey-modal]')).forEach(function (button) {
      button.addEventListener('click', function () {
        var survey = getSurveyById(button.getAttribute('data-open-survey-modal'));
        if (survey) openSurveyModal(survey);
      });
    });
    Array.prototype.slice.call(scope.querySelectorAll('[data-open-survey-results]')).forEach(function (button) {
      button.addEventListener('click', function () {
        var survey = getSurveyById(button.getAttribute('data-open-survey-results'));
        if (survey) openResultsModal(survey);
      });
    });
  }

  function refreshLiveWidgets() {
    var area = el('visor-slide-area');
    if (!area) return;
    var scope = area.querySelector('.visor-grapes-root') || area;
    hydrateSurveyWidgets(scope);
  }

  function startAnalyticsPolling() {
    if (analyticsPollTimer) {
      clearInterval(analyticsPollTimer);
      analyticsPollTimer = null;
    }
    if (!liveSurveys.length) return;
    analyticsPollTimer = setInterval(function () {
      loadSurveyAnalytics().then(function () {
        refreshLiveWidgets();
        if (resultsModal && resultsModal.classList.contains('is-open')) {
          var currentSurvey = getSurveyById(currentResultsSurveyId);
          if (currentSurvey) renderResultsModal(currentSurvey);
        }
      }).catch(function () {});
    }, 30000);
  }

  // ── Load ──────────────────────────────────────────────────────────────────

  function load() {
    Promise.all([
      apiJson('/api/capacitacion/presentaciones/' + presId),
      apiJson('/api/capacitacion/presentaciones/' + presId + '/diapositivas'),
      apiJson('/api/capacitacion/presentaciones/' + presId + '/encuestas-live')
    ]).then(function (res) {
      if (!res[0].ok) {
        el('visor-loading').textContent = 'No se pudo cargar la presentación.';
        return;
      }
      pres   = res[0].data;
      slides = res[1].data || [];
      liveSurveys = res[2] && res[2].ok ? (res[2].data || []) : [];
      return loadSurveyAnalytics().catch(function () {
        surveyAnalytics = {};
      }).then(function () {
        el('visor-pres-title').textContent = pres.titulo || 'Presentación';
        el('visor-loading').style.display  = 'none';
        renderDots();
        renderSlide(0);
        updateNav();
        startAnalyticsPolling();
        if (presentMode) {
          setPresentMode(true);
          setTimeout(function () {
            requestPresentationFullscreen();
          }, 120);
        }
      });
    });
  }

  // ── Render ────────────────────────────────────────────────────────────────

  function renderSlide(idx) {
    curIdx  = clamp(idx, 0, slides.length - 1);
    var area  = el('visor-slide-area');
    var slide = slides[curIdx];
    if (!slide) return;

    area.style.background = slide.bg_color || '#ffffff';
    if (slide.bg_image_url) {
      area.style.backgroundImage    = 'url(' + esc(slide.bg_image_url) + ')';
      area.style.backgroundSize     = 'cover';
      area.style.backgroundPosition = 'center';
    } else {
      area.style.backgroundImage = 'none';
    }

    // Remove old elements (keep #visor-loading if any)
    Array.prototype.slice.call(area.querySelectorAll('.visor-element, .visor-grapes-root, .visor-grapes-style')).forEach(function (n) { n.remove(); });

    var grapesElement = (slide.elementos || []).find(function (elem) { return elem.tipo === 'grapes'; });
    if (grapesElement) {
      var project = grapesElement.contenido_json || {};
      var styleNode = document.createElement('style');
      styleNode.className = 'visor-grapes-style';
      styleNode.textContent = String(project.css || '');
      var wrapper = document.createElement('div');
      wrapper.className = 'visor-grapes-root';
      wrapper.style.cssText = 'position:absolute;inset:0;overflow:hidden;';
      wrapper.innerHTML = project.html || '';
      area.appendChild(styleNode);
      area.appendChild(wrapper);
      hydrateSurveyWidgets(wrapper);
      updateNav();
      renderDots();
      return;
    }

    (slide.elementos || []).forEach(function (elem) {
      var d = document.createElement('div');
      d.className  = 'visor-element';
      d.style.left   = elem.pos_x  + '%';
      d.style.top    = elem.pos_y  + '%';
      d.style.width  = elem.width  + '%';
      d.style.height = elem.height + '%';
      d.style.zIndex = elem.z_index || 1;

      var c     = elem.contenido_json || {};
      var inner = document.createElement('div');
      inner.className = 'visor-el-' + elem.tipo;

      switch (elem.tipo) {
        case 'texto':
          inner.style.cssText = [
            'font-size:' + (c.fontSize || 16) + 'px;',
            'color:' + (c.color || '#1e293b') + ';',
            c.bgColor ? 'background:' + c.bgColor + ';' : '',
            c.bold    ? 'font-weight:700;' : '',
            c.italic  ? 'font-style:italic;' : '',
            'text-align:' + (c.align || 'left') + ';'
          ].join('');
          inner.textContent = c.texto || '';
          break;

        case 'imagen':
          inner.style.borderRadius = (c.borderRadius || 0) + 'px';
          if (c.url) {
            var img = document.createElement('img');
            img.src = c.url;
            img.style.cssText = 'width:100%;height:100%;object-fit:' + (c.objectFit || 'cover') + ';display:block;';
            img.draggable = false;
            inner.appendChild(img);
          } else {
            inner.style.cssText += 'background:#e2e8f0;display:flex;align-items:center;justify-content:center;';
            inner.innerHTML = '<span style="color:#94a3b8;font-size:28px;">🖼</span>';
          }
          break;

        case 'boton':
          inner.style.cssText = [
            'background:' + (c.bgColor || '#4f46e5') + ';',
            'color:' + (c.textColor || '#fff') + ';'
          ].join('');
          inner.textContent = c.texto || 'Botón';
          inner.addEventListener('click', function () {
            if (c.accion === 'slide') {
              var dest = (c.slideDest || 1) - 1;
              renderSlide(dest);
              updateNav();
            } else if (c.accion === 'url' && c.urlExterno) {
              window.open(c.urlExterno, '_blank', 'noopener,noreferrer');
            }
          });
          break;

        case 'forma':
          var isCircle = c.forma === 'circle';
          inner.style.cssText = [
            'background:' + (c.bgColor || '#4f46e5') + ';',
            isCircle ? 'border-radius:50%;' : (c.borderRadius ? 'border-radius:' + c.borderRadius + 'px;' : ''),
            c.borderColor ? 'border:' + (c.borderWidth || 1) + 'px solid ' + c.borderColor + ';' : ''
          ].join('');
          break;

        case 'embed':
          var eUrl = embedUrl(c.url || '');
          if (eUrl) {
            var iframe = document.createElement('iframe');
            iframe.src = eUrl;
            iframe.setAttribute('allowfullscreen', '1');
            iframe.style.cssText = 'width:100%;height:100%;border:none;display:block;';
            inner.appendChild(iframe);
          }
          break;
      }

      d.appendChild(inner);
      area.appendChild(d);
    });

    hydrateSurveyWidgets(area);

    updateNav();
    renderDots();
  }

  // ── Navigation ────────────────────────────────────────────────────────────

  function updateNav() {
    el('visor-prev').disabled = curIdx <= 0;
    el('visor-next').disabled = curIdx >= slides.length - 1;
    el('visor-counter').textContent = (curIdx + 1) + ' / ' + slides.length;
  }

  function renderDots() {
    var cont = el('visor-dots');
    if (!cont) return;
    cont.innerHTML = slides.map(function (_, i) {
      return '<div class="visor-dot' + (i === curIdx ? ' active' : '') + '" data-i="' + i + '"></div>';
    }).join('');
    cont.onclick = function (e) {
      var dot = e.target.closest('.visor-dot');
      if (!dot) return;
      renderSlide(parseInt(dot.dataset.i, 10));
    };
  }

  // Navigation buttons
  el('visor-prev') && el('visor-prev').addEventListener('click', function () {
    if (curIdx > 0) renderSlide(curIdx - 1);
  });
  el('visor-next') && el('visor-next').addEventListener('click', function () {
    if (curIdx < slides.length - 1) renderSlide(curIdx + 1);
  });

  // Edit button
  el('visor-edit-btn') && el('visor-edit-btn').addEventListener('click', function () {
    window.location.href = '/capacitacion/presentacion/' + presId + '/editor';
  });

  // Fullscreen
  el('visor-fullscreen') && el('visor-fullscreen').addEventListener('click', function () {
    if (!document.fullscreenElement) {
      requestPresentationFullscreen();
    } else {
      document.exitFullscreen && document.exitFullscreen();
    }
  });

  // Keyboard
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && surveyModal && surveyModal.classList.contains('is-open')) {
      closeSurveyModal();
      return;
    }
    if (e.key === 'Escape' && resultsModal && resultsModal.classList.contains('is-open')) {
      closeResultsModal();
      return;
    }
    if (e.key === 'ArrowRight' || e.key === ' ') {
      e.preventDefault();
      if (curIdx < slides.length - 1) renderSlide(curIdx + 1);
    } else if (e.key === 'ArrowLeft') {
      e.preventDefault();
      if (curIdx > 0) renderSlide(curIdx - 1);
    } else if (e.key === 'Escape') {
      document.fullscreenElement && document.exitFullscreen();
    }
  });

  el('visor-survey-close') && el('visor-survey-close').addEventListener('click', closeSurveyModal);
  surveyModal && surveyModal.addEventListener('click', function (event) {
    if (event.target === surveyModal) closeSurveyModal();
  });
  el('visor-results-close') && el('visor-results-close').addEventListener('click', closeResultsModal);
  resultsModal && resultsModal.addEventListener('click', function (event) {
    if (event.target === resultsModal) closeResultsModal();
  });

  // ── Boot ──────────────────────────────────────────────────────────────────

  if (presId) {
    setPresentMode(presentMode);
    load();
  } else {
    el('visor-loading').textContent = 'ID de presentación inválido.';
  }

})();
