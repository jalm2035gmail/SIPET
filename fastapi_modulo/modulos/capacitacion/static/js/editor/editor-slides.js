  function setPagesViewMode(mode) {
    pagesViewMode = mode === 'grid' ? 'grid' : 'list';
    var listBtn = el('ped-pages-view-list');
    var gridBtn = el('ped-pages-view-grid');
    if (listBtn) listBtn.classList.toggle('is-active', pagesViewMode === 'list');
    if (gridBtn) gridBtn.classList.toggle('is-active', pagesViewMode === 'grid');
    renderPagesPanel();
  }

  function loadSlideIntoEditor(slide) {
    if (!slide || !editorReady) return;
    applySlideForm(slide);
    var payload = grapesElementFromSlide(slide);
    var project = payload && payload.contenido_json ? payload.contenido_json : null;
    editor.DomComponents.clear();
    editor.CssComposer.clear();
    if (project && project.project && editor.loadProjectData) {
      editor.loadProjectData(project.project);
    } else if (project && (project.html || project.css)) {
      editor.setComponents(project.html || '');
      editor.setStyle(project.css || '');
    } else {
      editor.setComponents(legacyElementsToHtml(slide.elementos || []));
      editor.setStyle('');
    }
    setTimeout(function () {
      refreshSurveyPreviews();
      renderWidgetConfig();
      refreshEditorCanvas();
      paintEditorBackground(slide);
    }, 80);
  }

  function extractProjectPayload() {
    return {
      html: editor.getHtml(),
      css: editor.getCss(),
      project: editor.getProjectData ? editor.getProjectData() : null,
      responsive_mode: window.currentViewportMode || 'desktop',
      saved_at: new Date().toISOString(),
    };
  }

  function saveCurrentSlide(options) {
    options = options || {};
    var slide = currentSlide();
    if (!slide || !editorReady) return Promise.resolve();
    var title = (inputSlideTitle.value || '').trim() || ('Diapositiva ' + (currentSlideIdx + 1));
    var bgColor = inputSlideBgColor.value || '#ffffff';
    var bgImage = (inputSlideBgImage.value || '').trim();
    var notes = (inputSlideNotes.value || '').trim();
    slide.titulo = title;
    slide.bg_color = bgColor;
    slide.bg_image_url = bgImage;
    slide.notas = notes;
    var payload = extractProjectPayload();
    saving = true;
    return apiJson('/api/capacitacion/diapositivas/' + slide.id, {
      method: 'PUT',
      body: JSON.stringify({
        titulo: title,
        bg_color: bgColor,
        bg_image_url: bgImage,
        notas: notes,
      }),
    }).then(function (res) {
      if (!res.ok) throw new Error('No se pudo guardar la diapositiva.');
      return apiJson('/api/capacitacion/diapositivas/' + slide.id + '/elementos', {
        method: 'PUT',
        body: JSON.stringify({
          elementos: [{
            tipo: 'grapes',
            contenido_json: payload,
            animation_json: slide.animation_json || {},
            pos_x: 0,
            pos_y: 0,
            width: 100,
            height: 100,
            z_index: 1,
          }],
          autosave: !!options.autosave,
        }),
      });
    }).then(function (res) {
      saving = false;
      if (!res.ok) throw new Error('No se pudo guardar el contenido.');
      slide.elementos = [{
        tipo: 'grapes',
        contenido_json: payload,
        pos_x: 0,
        pos_y: 0,
        width: 100,
        height: 100,
        z_index: 1,
      }];
      renderSlideList();
      if (typeof loadAuditTrail === 'function') loadAuditTrail();
      if (!options.silent) toast(options.autosave ? 'Auto guardado.' : 'Slide guardada.');
    }).catch(function (error) {
      saving = false;
      if (!options.silent) toast(error.message || 'Error al guardar.', true);
      throw error;
    });
  }

  function selectSlide(index) {
    index = clamp(index, 0, slides.length - 1);
    if (index === currentSlideIdx && currentSlide()) return Promise.resolve();
    var next = function () {
      currentSlideIdx = index;
      renderSlideList();
      loadSlideIntoEditor(currentSlide());
    };
    if (currentSlideIdx >= 0) {
      return saveCurrentSlide().catch(function () {}).then(next);
    }
    next();
    return Promise.resolve();
  }

  function addSlide() {
    return saveCurrentSlide().catch(function () {}).then(function () {
      return apiJson('/api/capacitacion/presentaciones/' + presId + '/diapositivas', {
        method: 'POST',
        body: JSON.stringify({ titulo: 'Nueva diapositiva', bg_color: '#ffffff' }),
      });
    }).then(function (res) {
      if (!res.ok) throw new Error('No se pudo crear la diapositiva.');
      slides.push(res.data);
      return selectSlide(slides.length - 1).then(function () {
        if (typeof loadAuditTrail === 'function') return loadAuditTrail();
      });
    }).catch(function (error) {
      toast(error.message || 'Error al crear diapositiva.', true);
    });
  }

  function duplicateSlide() {
    var slide = currentSlide();
    if (!slide) return;
    saveCurrentSlide().catch(function () {}).then(function () {
      return apiJson('/api/capacitacion/diapositivas/' + slide.id + '/duplicar', { method: 'POST' });
    }).then(function (res) {
      if (!res.ok) throw new Error('No se pudo duplicar la diapositiva.');
      slides.splice(currentSlideIdx + 1, 0, res.data);
      return selectSlide(currentSlideIdx + 1).then(function () {
        if (typeof loadAuditTrail === 'function') return loadAuditTrail();
      });
    }).catch(function (error) {
      toast(error.message || 'Error al duplicar.', true);
    });
  }

  function deleteSlide() {
    var slide = currentSlide();
    if (!slide || slides.length <= 1) {
      toast('La presentación debe conservar al menos una diapositiva.', true);
      return;
    }
    if (!window.confirm('¿Eliminar esta diapositiva?')) return;
    apiJson('/api/capacitacion/diapositivas/' + slide.id, { method: 'DELETE' })
      .then(function (res) {
        if (!res.ok) throw new Error('No se pudo eliminar la diapositiva.');
        slides.splice(currentSlideIdx, 1);
        return selectSlide(Math.max(0, currentSlideIdx - 1)).then(function () {
          if (typeof loadAuditTrail === 'function') return loadAuditTrail();
        });
      })
      .catch(function (error) {
        toast(error.message || 'Error al eliminar.', true);
      });
  }

  function moveSlide(direction) {
    var newIndex = currentSlideIdx + direction;
    if (newIndex < 0 || newIndex >= slides.length) return;
    saveCurrentSlide().catch(function () {}).then(function () {
      var tmp = slides[currentSlideIdx];
      slides[currentSlideIdx] = slides[newIndex];
      slides[newIndex] = tmp;
      currentSlideIdx = newIndex;
      renderSlideList();
      return apiJson('/api/capacitacion/presentaciones/' + presId + '/reordenar', {
        method: 'PUT',
        body: JSON.stringify({ orden_ids: slides.map(function (slide) { return slide.id; }) }),
      });
    }).then(function () {
      loadSlideIntoEditor(currentSlide());
      if (typeof loadAuditTrail === 'function') return loadAuditTrail();
    });
  }
