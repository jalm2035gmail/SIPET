  function surveyOptionsMarkup() {
    if (!liveSurveys.length) {
      return '<option value="">Sin encuestas live vinculadas</option>';
    }
    return liveSurveys.map(function (survey) {
      return '<option value="' + survey.id + '">' + esc(survey.nombre || ('Encuesta ' + survey.id)) + '</option>';
    }).join('');
  }

  function getSurveyById(surveyId) {
    return liveSurveys.find(function (survey) { return String(survey.id) === String(surveyId); }) || null;
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

  function refreshSurveyPreviews() {
    if (!editor || !editor.getWrapper) return;
    editor.getWrapper().find('.cap-live-survey-widget').forEach(syncSurveyWidgetPreview);
    editor.getWrapper().find('.cap-live-survey-list-widget').forEach(syncSurveyListPreview);
    editor.getWrapper().find('.cap-live-survey-hotspot').forEach(syncHotspotPreview);
  }

  function surveyCardHtml(survey, mode, buttonLabel) {
    if (!survey) {
      return '<div style="padding:24px 28px;border-radius:24px;background:linear-gradient(135deg,#0f172a,#1d4ed8);color:#eff6ff;"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.18em;opacity:.72;margin-bottom:10px;">Encuesta live</div><h3 style="margin:0 0 8px;font-size:28px;">Sin encuesta seleccionada</h3><p style="margin:0;font-size:16px;line-height:1.6;opacity:.85;">Elige una encuesta del curso desde el panel de propiedades.</p></div>';
    }
    if (mode === 'embed') {
      return '<div style="padding:18px;border-radius:24px;background:#ffffff;box-shadow:0 20px 36px rgba(15,23,42,.12);"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.18em;color:#f97316;margin-bottom:10px;">Preview embed</div><div style="min-height:320px;border-radius:18px;background:linear-gradient(180deg,#f8fafc,#e2e8f0);display:flex;align-items:center;justify-content:center;text-align:center;padding:24px;color:#334155;"><div><strong style="display:block;font-size:28px;line-height:1.05;margin-bottom:10px;">' + esc(survey.nombre || 'Encuesta live') + '</strong><div style="font-size:15px;line-height:1.6;max-width:420px;">' + esc(survey.descripcion || 'La encuesta se incrustará aquí cuando la presentación se abra en el visor.') + '</div>' + analyticsBadges(survey.id, true) + '<div style="margin-top:18px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap;"><div style="display:inline-flex;align-items:center;justify-content:center;padding:12px 20px;border-radius:999px;background:#0f172a;color:#eff6ff;font-weight:800;">Ver resultado en vivo</div></div></div></div></div>';
    }
    return '<div style="padding:26px 30px;border-radius:24px;background:linear-gradient(135deg,#0f172a,#1d4ed8);color:#eff6ff;box-shadow:0 22px 44px rgba(15,23,42,.24);"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.18em;opacity:.72;margin-bottom:10px;">Encuesta live</div><h3 style="margin:0 0 8px;font-size:30px;line-height:1.05;">' + esc(survey.nombre || 'Encuesta live') + '</h3><p style="margin:0;font-size:16px;line-height:1.6;color:#dbeafe;">' + esc(survey.descripcion || 'Participa en esta dinámica interactiva del curso.') + '</p>' + analyticsBadges(survey.id, false) + '<div style="margin-top:18px;display:flex;gap:10px;flex-wrap:wrap;"><div style="display:inline-flex;align-items:center;justify-content:center;padding:12px 20px;border-radius:999px;background:#ff8a00;color:#231100;font-weight:800;">' + esc(buttonLabel || 'Responder encuesta') + '</div><div style="display:inline-flex;align-items:center;justify-content:center;padding:12px 20px;border-radius:999px;background:rgba(255,255,255,.14);color:#eff6ff;font-weight:800;border:1px solid rgba(255,255,255,.2);">Ver resultado en vivo</div></div></div>';
  }

  function surveyListHtml(mode) {
    if (!liveSurveys.length) {
      return '<div style="padding:22px;border-radius:20px;background:#f8fafc;border:1px dashed #cbd5e1;color:#475569;">No hay encuestas live vinculadas al curso.</div>';
    }
    if (mode === 'list') {
      return '<div style="padding:26px;border-radius:24px;background:#f8fafc;"><h3 style="margin:0 0 12px;font-size:28px;color:#0f172a;">Encuestas del curso</h3><ul style="margin:0;padding-left:18px;color:#334155;font-size:16px;line-height:1.9;">' +
        liveSurveys.map(function (survey) { return '<li>' + esc(survey.nombre || ('Encuesta ' + survey.id)) + ' · ' + analyticsSummary(survey.id).responses + ' resp.</li>'; }).join('') +
      '</ul></div>';
    }
    return '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;">' +
      liveSurveys.map(function (survey) {
        return '<article style="padding:22px;border-radius:24px;background:linear-gradient(180deg,#ffffff,#eff6ff);box-shadow:0 18px 32px rgba(15,23,42,.12);"><div style="font-size:11px;text-transform:uppercase;letter-spacing:.14em;color:#f97316;margin-bottom:8px;">Mentimeter</div><strong style="display:block;font-size:22px;line-height:1.08;color:#0f172a;">' + esc(survey.nombre || ('Encuesta ' + survey.id)) + '</strong><p style="margin:10px 0 0;font-size:15px;line-height:1.6;color:#475569;">' + esc(survey.descripcion || 'Disponible durante la sesión.') + '</p>' + analyticsBadges(survey.id, true) + '<div style="margin-top:16px;display:flex;gap:10px;flex-wrap:wrap;"><div style="display:inline-flex;padding:11px 16px;border-radius:999px;background:#0f172a;color:#eff6ff;font-weight:800;">Abrir</div><div style="display:inline-flex;padding:11px 16px;border-radius:999px;background:#e2e8f0;color:#0f172a;font-weight:800;">Ver resultado en vivo</div></div></article>';
      }).join('') +
    '</div>';
  }

  function surveyHotspotHtml(survey, label) {
    return '<button class="cap-live-survey-hotspot" data-survey-id="' + esc(survey ? survey.id : '') + '" data-hotspot-label="' + esc(label || 'Abrir encuesta') + '" style="position:relative;display:inline-flex;align-items:center;justify-content:center;width:44px;height:44px;border-radius:999px;border:0;background:#ff8a00;color:#231100;font-weight:800;box-shadow:0 0 0 14px rgba(255,138,0,.18);cursor:pointer;">+</button>';
  }

  function syncHotspotPreview(component) {
    if (!component) return;
    var attrs = component.getAttributes ? component.getAttributes() : {};
    var survey = getSurveyById(attrs['data-survey-id']);
    component.components(surveyHotspotHtml(survey, attrs['data-hotspot-label']));
  }

  function syncSurveyWidgetPreview(component) {
    if (!component) return;
    var attrs = component.getAttributes ? component.getAttributes() : {};
    var survey = getSurveyById(attrs['data-survey-id']);
    component.components(surveyCardHtml(survey, attrs['data-widget-mode'], attrs['data-button-label']));
  }

  function syncSurveyListPreview(component) {
    if (!component) return;
    var attrs = component.getAttributes ? component.getAttributes() : {};
    component.components(surveyListHtml(attrs['data-widget-mode'] || 'cards'));
  }

  function renderWidgetConfig() {
    if (!widgetConfig || !editor) return;
    var selected = editor.getSelected && editor.getSelected();
    if (!selected) {
      widgetConfig.innerHTML = '<div class="ped-empty">Selecciona un widget de encuesta para configurarlo.</div>';
      return;
    }
    var classes = selected.getClasses ? selected.getClasses() : [];
    var isSurvey = classes.indexOf('cap-live-survey-widget') >= 0;
    var isSurveyList = classes.indexOf('cap-live-survey-list-widget') >= 0;
    var isHotspot = classes.indexOf('cap-live-survey-hotspot') >= 0;
    if (!isSurvey && !isSurveyList && !isHotspot) {
      widgetConfig.innerHTML = '<div class="ped-empty">Selecciona un widget de encuesta para ver opciones específicas.</div>';
      return;
    }
    var attrs = selected.getAttributes ? selected.getAttributes() : {};
    var surveyPicker = '<div class="ped-field"><label>Encuesta</label><div style="display:grid;gap:8px;">' +
      (liveSurveys.length ? liveSurveys.map(function (survey) {
        var active = String(attrs['data-survey-id'] || '') === String(survey.id);
        return '<button type="button" class="ped-survey-card-option' + (active ? ' is-active' : '') + '" data-ped-survey-option="' + survey.id + '" style="text-align:left;padding:12px 14px;border-radius:16px;border:1px solid ' + (active ? 'rgba(255,138,0,.82)' : 'rgba(255,255,255,.08)') + ';background:' + (active ? 'rgba(255,138,0,.16)' : 'rgba(255,255,255,.04)') + ';color:#eff6ff;cursor:pointer;">' +
          '<strong style="display:block;font-size:14px;margin-bottom:4px;">' + esc(survey.nombre || ('Encuesta ' + survey.id)) + '</strong>' +
          '<span style="display:block;font-size:12px;color:rgba(203,213,225,.82);">' + esc(survey.descripcion || 'Sin descripción') + '</span>' +
          analyticsBadges(survey.id, false) +
        '</button>';
      }).join('') : '<div class="ped-empty">No hay encuestas live vinculadas al curso.</div>') +
      '</div></div>';
    if (isSurvey) {
      widgetConfig.innerHTML = '<div class="ped-widget-config-card">' +
        '<h4>Widget de encuesta</h4>' +
        surveyPicker +
        '<div class="ped-field"><label>Modo</label><select id="ped-survey-mode"><option value="card">Tarjeta</option><option value="embed">Embed</option></select></div>' +
        '<div class="ped-field"><label>Texto botón</label><input id="ped-survey-button-label" type="text" value="' + esc(attrs['data-button-label'] || 'Responder encuesta') + '"></div>' +
        '</div>';
      var mode = el('ped-survey-mode');
      var label = el('ped-survey-button-label');
      if (mode) mode.value = attrs['data-widget-mode'] || 'card';
      Array.prototype.slice.call(widgetConfig.querySelectorAll('[data-ped-survey-option]')).forEach(function (button) {
        button.addEventListener('click', function () {
          selected.addAttributes({ 'data-survey-id': button.getAttribute('data-ped-survey-option') || '' });
          syncSurveyWidgetPreview(selected);
          renderWidgetConfig();
        });
      });
      if (mode) {
        mode.addEventListener('change', function () {
          selected.addAttributes({ 'data-widget-mode': mode.value || 'card' });
          syncSurveyWidgetPreview(selected);
        });
      }
      if (label) {
        label.addEventListener('input', function () {
          selected.addAttributes({ 'data-button-label': label.value || 'Responder encuesta' });
          syncSurveyWidgetPreview(selected);
        });
      }
      return;
    }
    if (isHotspot) {
      widgetConfig.innerHTML = '<div class="ped-widget-config-card">' +
        '<h4>Hotspot de encuesta</h4>' +
        surveyPicker +
        '<div class="ped-field"><label>Texto accesible</label><input id="ped-hotspot-label" type="text" value="' + esc(attrs['data-hotspot-label'] || 'Abrir encuesta') + '"></div>' +
        '<div class="ped-empty">Colócalo sobre una imagen o composición visual. En el visor abrirá la encuesta en modal.</div>' +
      '</div>';
      Array.prototype.slice.call(widgetConfig.querySelectorAll('[data-ped-survey-option]')).forEach(function (button) {
        button.addEventListener('click', function () {
          selected.addAttributes({ 'data-survey-id': button.getAttribute('data-ped-survey-option') || '' });
          syncHotspotPreview(selected);
          renderWidgetConfig();
        });
      });
      var hotspotLabel = el('ped-hotspot-label');
      if (hotspotLabel) {
        hotspotLabel.addEventListener('input', function () {
          selected.addAttributes({ 'data-hotspot-label': hotspotLabel.value || 'Abrir encuesta' });
          syncHotspotPreview(selected);
        });
      }
      return;
    }
    widgetConfig.innerHTML = '<div class="ped-widget-config-card">' +
      '<h4>Muro de encuestas</h4>' +
      '<div class="ped-field"><label>Modo</label><select id="ped-survey-list-mode"><option value="cards">Tarjetas</option><option value="list">Lista</option></select></div>' +
      '<div class="ped-empty">Este widget mostrará automáticamente las encuestas live del curso vinculado.</div>' +
      '</div>';
    var listMode = el('ped-survey-list-mode');
    if (listMode) listMode.value = attrs['data-widget-mode'] || 'cards';
    if (listMode) {
      listMode.addEventListener('change', function () {
        selected.addAttributes({ 'data-widget-mode': listMode.value || 'cards' });
        syncSurveyListPreview(selected);
      });
    }
  }

