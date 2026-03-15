/* capacitacion_editor.js — Loader del editor modular */
(function () {
  'use strict';

  var root = document.getElementById('ped-root');
  if (!root) return;

  var files = [
    'editor-core.js?v=20260314a',
    'editor-widgets.js?v=20260314a',
    'editor-background.js?v=20260314a',
    'editor-surveys.js?v=20260314a',
    'editor-canvas.js?v=20260314a',
    'editor-slides.js?v=20260314a',
    'editor-ui.js?v=20260314a'
  ];

  function bootstrap() {
    if (window.editorBootstrapError) {
      if (typeof window.toast === 'function') {
        window.toast(window.editorBootstrapError, true);
      }
      return;
    }

    window.syncPresentationHeader = function () {
      if (!window.presentation) return;
      window.inputPresTitle.value = window.presentation.titulo || 'Presentación';
      var publishBtn = window.el('ped-btn-publish');
      if (publishBtn) {
        publishBtn.textContent = window.presentation.estado === 'publicado' ? 'Despublicar' : 'Publicar';
      }
    };

    window.saveAll = function () {
      if (window.saving) return;
      window.saveCurrentSlide().catch(function () {});
    };

    window.loadData = function () {
      return Promise.all([
        window.apiJson('/api/capacitacion/presentaciones/' + window.presId),
        window.apiJson('/api/capacitacion/presentaciones/' + window.presId + '/diapositivas'),
        window.apiJson('/api/capacitacion/presentaciones/' + window.presId + '/encuestas-live')
      ]).then(function (results) {
        if (!results[0].ok) throw new Error('No se pudo cargar la presentación.');
        window.presentation = results[0].data;
        window.slides = results[1].ok ? (results[1].data || []) : [];
        window.liveSurveys = results[2] && results[2].ok ? (results[2].data || []) : [];
        if (!window.slides.length) throw new Error('La presentación no tiene diapositivas.');
        return window.loadSurveyAnalytics().catch(function () {
          window.surveyAnalytics = {};
        }).then(function () {
          window.syncPresentationHeader();
          window.renderSlideList();
          return window.selectSlide(0).then(function () {
            window.refreshSurveyPreviews();
            return window.loadAuditTrail ? window.loadAuditTrail() : null;
          });
        });
      });
    };

    if (typeof window.bindBackgroundInputs === 'function') {
      window.bindBackgroundInputs();
    }
    window.bindTabs();
    window.initEditor();
    window.bindToolbar();
    if (typeof window.bindAutosave === 'function') {
      window.bindAutosave();
    }
    window.loadData().catch(function (error) {
      window.toast((error && error.message) || 'Error al cargar el editor.', true);
    });
  }

  function loadSequential(index) {
    if (index >= files.length) {
      bootstrap();
      return;
    }
    var script = document.createElement('script');
    script.src = '/capacitacion/assets/js/editor/' + files[index];
    script.onload = function () { loadSequential(index + 1); };
    script.onerror = function () {
      var toastNode = document.getElementById('ped-toast');
      if (toastNode) {
        toastNode.textContent = 'No se pudo cargar el editor.';
        toastNode.classList.add('show', 'error');
      }
    };
    document.body.appendChild(script);
  }

  loadSequential(0);
})();
