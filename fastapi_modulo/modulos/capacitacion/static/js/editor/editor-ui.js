  function bindTabs() {
    Array.prototype.slice.call(document.querySelectorAll('[data-ped-tab]')).forEach(function (button) {
      button.addEventListener('click', function () {
        var target = button.getAttribute('data-ped-tab');
        Array.prototype.slice.call(document.querySelectorAll('[data-ped-tab]')).forEach(function (item) {
          item.classList.toggle('is-active', item === button);
        });
        Array.prototype.slice.call(document.querySelectorAll('[data-ped-view]')).forEach(function (view) {
          view.classList.toggle('is-active', view.getAttribute('data-ped-view') === target);
        });
      });
    });
  }

  function bindToolbar() {
    function setActiveRail(buttonId) {
      Array.prototype.slice.call(document.querySelectorAll('.ped-rail-btn')).forEach(function (btn) {
        btn.classList.toggle('is-active', btn.id === buttonId);
      });
      setTextPanelVisible(buttonId === 'ped-btn-add-texto');
      setResourcePanelVisible(buttonId === 'ped-btn-add-imagen');
      setInteractivePanelVisible(buttonId === 'ped-btn-add-hotspot');
      setQuestionsPanelVisible(buttonId === 'ped-btn-add-survey');
      setWidgetsPanelVisible(buttonId === 'ped-btn-add-survey-list');
      setInsertPanelVisible(buttonId === 'ped-btn-add-forma');
      setStylePanelVisible(buttonId === 'ped-btn-add-boton');
      setBackgroundPanelVisible(buttonId === 'ped-btn-add-embed');
      setPagesPanelVisible(buttonId === 'ped-btn-add-slide');
    }
    el('ped-btn-add-texto').addEventListener('click', function () { setActiveRail('ped-btn-add-texto'); });
    el('ped-btn-add-imagen').addEventListener('click', function () { setActiveRail('ped-btn-add-imagen'); });
    el('ped-btn-add-boton').addEventListener('click', function () { setActiveRail('ped-btn-add-boton'); });
    el('ped-btn-add-forma').addEventListener('click', function () { setActiveRail('ped-btn-add-forma'); });
    el('ped-btn-add-embed').addEventListener('click', function () { setActiveRail('ped-btn-add-embed'); });
    el('ped-btn-add-survey').addEventListener('click', function () { setActiveRail('ped-btn-add-survey'); });
    el('ped-btn-add-survey-list').addEventListener('click', function () { setActiveRail('ped-btn-add-survey-list'); });
    el('ped-btn-add-hotspot').addEventListener('click', function () { setActiveRail('ped-btn-add-hotspot'); editor.runCommand('ped-insert-survey-hotspot'); });
    if (toggleSidepanelBtn) {
      toggleSidepanelBtn.addEventListener('click', function () {
        setSidepanelCollapsed(!sidepanelCollapsed);
      });
    }
    el('ped-btn-save').addEventListener('click', function () { saveAll(); toast('Cambios guardados y listos para compartir.'); });
    el('ped-btn-preview').addEventListener('click', function () {
      saveCurrentSlide().catch(function () {}).then(function () {
        window.open('/capacitacion/presentacion/' + presId + '/ver?present=1', '_blank', 'noopener,noreferrer');
      });
    });
    el('ped-btn-back').addEventListener('click', function () {
      saveCurrentSlide().catch(function () {}).then(function () {
        window.location.href = '/capacitacion/presentaciones';
      });
    });
    el('ped-btn-publish').addEventListener('click', function () {
      if (!presentation) return;
      var nextStatus = presentation.estado === 'publicado' ? 'borrador' : 'publicado';
      saveCurrentSlide().catch(function () {}).then(function () {
        return apiJson('/api/capacitacion/presentaciones/' + presId, {
          method: 'PUT',
          body: JSON.stringify({ estado: nextStatus, titulo: inputPresTitle.value.trim() || presentation.titulo }),
        });
      }).then(function (res) {
        if (!res.ok) throw new Error('No se pudo actualizar el estado.');
        presentation = res.data;
        syncPresentationHeader();
        if (typeof loadAuditTrail === 'function') loadAuditTrail();
        toast(nextStatus === 'publicado' ? 'Presentación publicada.' : 'Presentación en borrador.');
      }).catch(function (error) {
        toast(error.message || 'Error al publicar.', true);
      });
    });
    el('ped-btn-add-slide').addEventListener('click', function () { setActiveRail('ped-btn-add-slide'); });
    el('ped-btn-dup-slide').addEventListener('click', duplicateSlide);
    el('ped-btn-del-slide').addEventListener('click', deleteSlide);
    el('ped-btn-slide-up').addEventListener('click', function () { moveSlide(-1); });
    el('ped-btn-slide-dn').addEventListener('click', function () { moveSlide(1); });
    inputPresTitle.addEventListener('change', function () {
      if (!presentation) return;
      apiJson('/api/capacitacion/presentaciones/' + presId, {
        method: 'PUT',
        body: JSON.stringify({ titulo: inputPresTitle.value.trim() || presentation.titulo }),
      }).then(function (res) {
        if (res.ok) {
          presentation = res.data;
          syncPresentationHeader();
          if (typeof loadAuditTrail === 'function') loadAuditTrail();
        }
      });
    });
    el('ped-slide-list').addEventListener('click', function (event) {
      var card = event.target.closest('[data-slide-idx]');
      if (!card) return;
      selectSlide(parseInt(card.getAttribute('data-slide-idx'), 10));
    });
    document.addEventListener('keydown', function (event) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 's') {
        event.preventDefault();
        saveAll();
      }
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'd') {
        if (!editor || !editor.getSelected) return;
        event.preventDefault();
        var selected = editor.getSelected();
        if (!selected) return;
        var clone = selected.clone();
        var parent = selected.parent ? selected.parent() : null;
        if (clone && parent && parent.append) {
          parent.append(clone);
          if (editor.select) editor.select(clone);
          saveCurrentSlide({ autosave: true, silent: true }).catch(function () {});
          toast('Bloque duplicado.');
        }
      }
    });
    if (resourcePanel) {
      resourcePanel.addEventListener('click', function (event) {
        var trigger = event.target.closest('[data-ped-resource]');
        if (!trigger) return;
        insertResource(trigger.getAttribute('data-ped-resource') || '');
      });
    }
    if (textPanel) {
      textPanel.addEventListener('click', function (event) {
        var trigger = event.target.closest('[data-ped-text]');
        if (!trigger) return;
        insertTextPreset(trigger.getAttribute('data-ped-text') || '');
      });
    }
    if (interactivePanel) {
      interactivePanel.addEventListener('click', function (event) {
        var trigger = event.target.closest('[data-ped-interactive]');
        if (!trigger) return;
        insertInteractivePreset(trigger.getAttribute('data-ped-interactive') || '');
      });
    }
    if (questionsPanel) {
      questionsPanel.addEventListener('click', function (event) {
        var configBtn = event.target.closest('#ped-question-config-btn');
        if (configBtn) {
          window.location.href = '/encuestas/constructor';
          return;
        }
        var trigger = event.target.closest('[data-ped-question]');
        if (!trigger) return;
        insertQuestionPreset(trigger.getAttribute('data-ped-question') || '');
      });
    }
    if (widgetsPanel) {
      widgetsPanel.addEventListener('click', function (event) {
        var trigger = event.target.closest('[data-ped-widget]');
        if (!trigger) return;
        insertWidgetPreset(trigger.getAttribute('data-ped-widget') || '');
      });
    }
    if (insertPanel) {
      insertPanel.addEventListener('click', function (event) {
        var tab = event.target.closest('[data-ped-insert-tab]');
        if (tab) {
          var target = tab.getAttribute('data-ped-insert-tab');
          Array.prototype.slice.call(insertPanel.querySelectorAll('[data-ped-insert-tab]')).forEach(function (item) {
            item.classList.toggle('is-active', item === tab);
          });
          Array.prototype.slice.call(insertPanel.querySelectorAll('[data-ped-insert-view]')).forEach(function (view) {
            view.classList.toggle('is-active', view.getAttribute('data-ped-insert-view') === target);
          });
          return;
        }
        var action = event.target.closest('[data-ped-insert]');
        if (!action) return;
        insertMediaPreset(action.getAttribute('data-ped-insert') || '');
      });
    }
    if (stylePanel) {
      stylePanel.addEventListener('click', function (event) {
        var palette = event.target.closest('[data-ped-style-palette]');
        if (palette) {
          applyPalette(palette.getAttribute('data-ped-style-palette') || '');
          return;
        }
        var textStyle = event.target.closest('[data-ped-style-text]');
        if (!textStyle) return;
        insertTextPreset(textStyle.getAttribute('data-ped-style-text') || '');
      });
    }
    if (backgroundPanel) {
      backgroundPanel.addEventListener('click', function (event) {
        var tab = event.target.closest('[data-ped-bg-tab]');
        if (tab) {
          var target = tab.getAttribute('data-ped-bg-tab');
          Array.prototype.slice.call(backgroundPanel.querySelectorAll('[data-ped-bg-tab]')).forEach(function (item) {
            item.classList.toggle('is-active', item === tab);
          });
          Array.prototype.slice.call(backgroundPanel.querySelectorAll('[data-ped-bg-view]')).forEach(function (view) {
            view.classList.toggle('is-active', view.getAttribute('data-ped-bg-view') === target);
          });
          return;
        }
        var swatch = event.target.closest('[data-ped-bg-color]');
        if (swatch) {
          Array.prototype.slice.call(backgroundPanel.querySelectorAll('[data-ped-bg-color]')).forEach(function (item) {
            item.classList.toggle('is-selected', item === swatch);
          });
          applyBackgroundColor(swatch.getAttribute('data-ped-bg-color') || '', false);
          return;
        }
        var action = event.target.closest('[data-ped-bg-action]');
        if (!action) return;
        var type = action.getAttribute('data-ped-bg-action') || '';
        if (type === 'upload-image') {
          toast('Pendiente subida de imagen personalizada.');
          return;
        }
        if (type === 'apply-all') {
          applyBackgroundColor((currentSlide() && currentSlide().bg_color) || '#3f6f12', true);
          return;
        }
        if (type === 'set-MAIN') {
          toast('Fondo MAIN guardado para este proyecto.');
        }
      });
    }
    var pagesAddBtn = el('ped-pages-add-btn');
    if (pagesAddBtn) {
      pagesAddBtn.addEventListener('click', function () {
        addSlide();
      });
    }
    var pagesListBtn = el('ped-pages-view-list');
    if (pagesListBtn) {
      pagesListBtn.addEventListener('click', function () {
        setPagesViewMode('list');
      });
    }
    var pagesGridBtn = el('ped-pages-view-grid');
    if (pagesGridBtn) {
      pagesGridBtn.addEventListener('click', function () {
        setPagesViewMode('grid');
      });
    }
    if (pagesPanel) {
      pagesPanel.addEventListener('click', function (event) {
        var selectBtn = event.target.closest('[data-ped-page-select],[data-ped-page-idx]');
        if (selectBtn) {
          var idx = selectBtn.getAttribute('data-ped-page-select');
          if (idx == null) idx = selectBtn.getAttribute('data-ped-page-idx');
          if (idx != null) selectSlide(parseInt(idx, 10));
          return;
        }
        var dupBtn = event.target.closest('[data-ped-page-duplicate]');
        if (dupBtn) {
          selectSlide(parseInt(dupBtn.getAttribute('data-ped-page-duplicate'), 10)).then(function () {
            duplicateSlide();
          });
          return;
        }
        var previewBtn = event.target.closest('[data-ped-page-preview]');
        if (previewBtn) {
          selectSlide(parseInt(previewBtn.getAttribute('data-ped-page-preview'), 10)).then(function () {
            window.open('/capacitacion/presentacion/' + presId + '/ver?present=1', '_blank', 'noopener,noreferrer');
          });
        }
      });
    }
  }

  function bindAutosave() {
    clearInterval(window.__pedAutosaveTimer);
    window.__pedAutosaveTimer = setInterval(function () {
      if (!editorReady || saving || !currentSlide()) return;
      saveCurrentSlide({ autosave: true, silent: true }).catch(function () {});
    }, 30000);
  }
