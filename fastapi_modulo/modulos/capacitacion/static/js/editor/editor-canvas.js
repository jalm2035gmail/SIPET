  function initEditor() {
    editor = window.grapesjs.init({
      container: '#ped-canvas',
      height: '100%',
      width: '100%',
      fromElement: false,
      storageManager: false,
      noticeOnUnload: false,
      selectorManager: { appendTo: '#ped-styles' },
      styleManager: { appendTo: '#ped-styles' },
      traitManager: { appendTo: '#ped-traits' },
      layerManager: { appendTo: '#ped-layers' },
      blockManager: { appendTo: '#ped-blocks' },
      panels: { defaults: [] },
      canvas: {},
    });
    editor.on('load', function () {
      injectCanvasStyles();
      refreshEditorCanvas();
      setTimeout(function () {
        paintEditorBackground(currentSlide());
      }, 120);
    });

    var bm = editor.BlockManager;
    bm.add('hero-cover', {
      label: 'Hero',
      category: 'Story',
      content: '<section style="padding:72px 68px;background:linear-gradient(135deg,#ff8a00 0%,#ffd166 42%,#22d3ee 100%);color:#081120;"><div style="max-width:520px;"><div style="font-size:12px;letter-spacing:.18em;text-transform:uppercase;font-weight:800;margin-bottom:18px;">Story frame</div><h1 style="font-size:54px;line-height:.95;margin:0 0 16px;font-weight:800;">Crea slides memorables</h1><p style="font-size:19px;line-height:1.55;margin:0;">Combina tipografía, bloques visuales, medios y navegación para experiencias tipo Genially.</p></div></section>',
    });
    bm.add('content-split', {
      label: 'Split',
      category: 'Story',
      content: '<section style="padding:52px 56px;"><div style="display:grid;grid-template-columns:1.1fr .9fr;gap:32px;align-items:center;"><div><h2 style="margin:0 0 10px;font-size:38px;">Explica una idea</h2><p style="margin:0;font-size:18px;line-height:1.7;color:#475569;">Usa este bloque para una narrativa con texto a la izquierda y visual a la derecha.</p></div><div class="gjs-card" style="min-height:260px;background:linear-gradient(160deg,#0f172a,#1d4ed8);"></div></div></section>',
    });
    bm.add('stat-cards', {
      label: 'Stats',
      category: 'Data',
      content: '<section style="padding:42px 52px;background:#f8fafc;"><div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;"><div class="gjs-card" style="padding:22px;background:#fff;"><div style="font-size:13px;color:#64748b;">Cobertura</div><strong style="font-size:42px;">92%</strong></div><div class="gjs-card" style="padding:22px;background:#fff;"><div style="font-size:13px;color:#64748b;">Engagement</div><strong style="font-size:42px;">4.8</strong></div><div class="gjs-card" style="padding:22px;background:#fff;"><div style="font-size:13px;color:#64748b;">NPS</div><strong style="font-size:42px;">67</strong></div></div></section>',
    });
    bm.add('cta-button', {
      label: 'CTA',
      category: 'Interactive',
      content: '<div style="padding:40px 56px;"><a class="gjs-button-link" href="#" style="background:#ff8a00;color:#1f1300;">Explorar contenido</a></div>',
    });
    bm.add('video-embed', {
      label: 'Video',
      category: 'Media',
      content: '<section style="padding:38px 48px;"><div class="gjs-card" style="background:#0f172a;padding:10px;"><iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ" allowfullscreen style="width:100%;height:360px;border:0;display:block;border-radius:18px;"></iframe></div></section>',
    });
    bm.add('image-stage', {
      label: 'Imagen',
      category: 'Media',
      content: '<section style="padding:32px 44px;"><img src="https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1200&q=80" alt="" style="display:block;width:100%;border-radius:24px;object-fit:cover;min-height:340px;"></section>',
    });
    bm.add('highlight-note', {
      label: 'Note',
      category: 'Interactive',
      content: '<div style="padding:40px 56px;"><div style="display:flex;gap:16px;align-items:flex-start;padding:20px 22px;border-radius:20px;background:#0f172a;color:#eff6ff;"><span class="gjs-hotspot"></span><div><strong style="display:block;font-size:18px;margin-bottom:6px;">Punto clave</strong><div style="font-size:15px;line-height:1.6;color:#cbd5e1;">Resalta una idea importante o un insight que el usuario debe recordar.</div></div></div></div>',
    });
    bm.add('survey-card', {
      label: 'Encuesta live',
      category: 'Interactive',
      content: '<div class="cap-live-survey-widget" data-survey-id="" data-widget-mode="card" data-button-label="Responder encuesta" style="padding:26px 30px;border-radius:24px;background:linear-gradient(135deg,#0f172a,#1d4ed8);color:#eff6ff;"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.18em;opacity:.75;margin-bottom:10px;">Encuesta live</div><h3 style="margin:0 0 8px;font-size:28px;">Widget de encuesta</h3><p style="margin:0;font-size:16px;line-height:1.6;opacity:.85;">Selecciona una encuesta del curso desde las propiedades del componente.</p><div style="margin-top:18px;display:inline-flex;padding:11px 18px;border-radius:999px;background:#ff8a00;color:#1f1300;font-weight:800;">Responder encuesta</div></div>',
    });
    bm.add('survey-list', {
      label: 'Muro encuestas',
      category: 'Interactive',
      content: '<div class="cap-live-survey-list-widget" data-widget-mode="list" style="padding:28px;border-radius:24px;background:#f8fafc;border:1px dashed #cbd5e1;"><h3 style="margin:0 0 8px;font-size:28px;color:#0f172a;">Encuestas del curso</h3><p style="margin:0;color:#475569;font-size:16px;line-height:1.6;">Este widget mostrará todas las encuestas live vinculadas al curso.</p></div>',
    });
    bm.add('survey-hotspot', {
      label: 'Hotspot encuesta',
      category: 'Interactive',
      content: '<div class="cap-live-survey-hotspot" data-survey-id="" data-hotspot-label="Abrir encuesta" style="display:inline-flex;"></div>',
    });

    var domc = editor.DomComponents;
    domc.addType('survey-widget', {
      isComponent: function (elNode) {
        if (elNode && elNode.classList && elNode.classList.contains('cap-live-survey-widget')) {
          return { type: 'survey-widget' };
        }
        return false;
      },
      model: {
        defaults: {
          traits: [
            { type: 'text', name: 'data-survey-id', label: 'Survey ID' },
            { type: 'select', name: 'data-widget-mode', label: 'Modo', options: [
              { id: 'card', name: 'Tarjeta' },
              { id: 'embed', name: 'Embed' },
            ]},
            { type: 'text', name: 'data-button-label', label: 'Texto botón' },
          ],
        },
      },
    });
    domc.addType('survey-list-widget', {
      isComponent: function (elNode) {
        if (elNode && elNode.classList && elNode.classList.contains('cap-live-survey-list-widget')) {
          return { type: 'survey-list-widget' };
        }
        return false;
      },
      model: {
        defaults: {
          traits: [
            { type: 'select', name: 'data-widget-mode', label: 'Modo', options: [
              { id: 'list', name: 'Lista' },
              { id: 'cards', name: 'Tarjetas' },
            ]},
          ],
        },
      },
    });
    domc.addType('survey-hotspot', {
      isComponent: function (elNode) {
        if (elNode && elNode.classList && elNode.classList.contains('cap-live-survey-hotspot')) {
          return { type: 'survey-hotspot' };
        }
        return false;
      },
      model: {
        defaults: {
          traits: [
            { type: 'text', name: 'data-survey-id', label: 'Survey ID' },
            { type: 'text', name: 'data-hotspot-label', label: 'Label' },
          ],
        },
      },
    });
    editor.on('component:selected', renderWidgetConfig);
    editor.on('component:update:attributes', function (component) {
      if (!component || !component.getClasses) return;
      var classes = component.getClasses();
      if (classes.indexOf('cap-live-survey-widget') >= 0) syncSurveyWidgetPreview(component);
      if (classes.indexOf('cap-live-survey-list-widget') >= 0) syncSurveyListPreview(component);
      if (classes.indexOf('cap-live-survey-hotspot') >= 0) syncHotspotPreview(component);
      renderWidgetConfig();
    });

    editor.Commands.add('ped-insert-text', {
      run: function (ed) { ed.addComponents(htmlBlock({})); }
    });
    editor.Commands.add('ped-insert-image', {
      run: function (ed) { ed.addComponents('<section style="padding:32px 42px;"><img src="https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1200&q=80" alt="" style="width:100%;border-radius:24px;display:block;min-height:320px;object-fit:cover;"></section>'); }
    });
    editor.Commands.add('ped-insert-button', {
      run: function (ed) { ed.addComponents(styledButtonBlock()); }
    });
    editor.Commands.add('ped-insert-card', {
      run: function (ed) { ed.addComponents(featureCardBlock()); }
    });
    editor.Commands.add('ped-insert-video', {
      run: function (ed) { ed.addComponents(backgroundFrameBlock()); }
    });
    editor.Commands.add('ped-insert-survey', {
      run: function (ed) {
        var firstSurvey = liveSurveys[0];
        var surveyId = firstSurvey ? String(firstSurvey.id) : '';
        ed.addComponents('<div class="cap-live-survey-widget" data-survey-id="' + surveyId + '" data-widget-mode="card" data-button-label="Responder encuesta" style="padding:0;"></div>');
      }
    });
    editor.Commands.add('ped-insert-survey-list', {
      run: function (ed) {
        ed.addComponents('<div class="cap-live-survey-list-widget" data-widget-mode="cards" style="padding:0;"></div>');
      }
    });
    editor.Commands.add('ped-insert-survey-hotspot', {
      run: function (ed) {
        var firstSurvey = liveSurveys[0];
        var surveyId = firstSurvey ? String(firstSurvey.id) : '';
        ed.addComponents('<div class="cap-live-survey-hotspot" data-survey-id="' + surveyId + '" data-hotspot-label="Abrir encuesta" style="display:inline-flex;"></div>');
      }
    });

    editorReady = true;
  }

  function grapesElementFromSlide(slide) {
    return (slide.elementos || []).find(function (item) { return item.tipo === 'grapes'; }) || null;
  }

  function legacyElementsToHtml(elements) {
    if (!Array.isArray(elements) || !elements.length) {
      return htmlBlock({ title: 'Nueva diapositiva', text: 'Empieza arrastrando un bloque desde el panel derecho.' });
    }
    return elements.map(function (item) {
      var c = item.contenido_json || {};
      if (item.tipo === 'texto') {
        return '<div style="position:absolute;left:' + item.pos_x + '%;top:' + item.pos_y + '%;width:' + item.width + '%;height:' + item.height + '%;font-size:' + (c.fontSize || 16) + 'px;color:' + esc(c.color || '#0f172a') + ';font-weight:' + (c.bold ? '700' : '400') + ';font-style:' + (c.italic ? 'italic' : 'normal') + ';text-align:' + esc(c.align || 'left') + ';background:' + esc(c.bgColor || 'transparent') + ';padding:6px 8px;box-sizing:border-box;">' + esc(c.texto || '') + '</div>';
      }
      if (item.tipo === 'imagen') {
        return '<img src="' + esc(c.url || '') + '" alt="" style="position:absolute;left:' + item.pos_x + '%;top:' + item.pos_y + '%;width:' + item.width + '%;height:' + item.height + '%;object-fit:' + esc(c.objectFit || 'cover') + ';border-radius:' + Number(c.borderRadius || 0) + 'px;">';
      }
      if (item.tipo === 'boton') {
        return '<a href="' + esc(c.urlExterno || '#') + '" style="position:absolute;left:' + item.pos_x + '%;top:' + item.pos_y + '%;width:' + item.width + '%;height:' + item.height + '%;display:flex;align-items:center;justify-content:center;text-decoration:none;background:' + esc(c.bgColor || '#4f46e5') + ';color:' + esc(c.textColor || '#ffffff') + ';border-radius:16px;font-weight:700;">' + esc(c.texto || 'Botón') + '</a>';
      }
      if (item.tipo === 'forma') {
        return '<div style="position:absolute;left:' + item.pos_x + '%;top:' + item.pos_y + '%;width:' + item.width + '%;height:' + item.height + '%;background:' + esc(c.bgColor || '#1d4ed8') + ';border-radius:' + (c.forma === 'circle' ? '999px' : Number(c.borderRadius || 12) + 'px') + ';"></div>';
      }
      if (item.tipo === 'embed') {
        return '<iframe src="' + esc(c.url || '') + '" style="position:absolute;left:' + item.pos_x + '%;top:' + item.pos_y + '%;width:' + item.width + '%;height:' + item.height + '%;border:0;border-radius:18px;"></iframe>';
      }
      return '';
    }).join('');
  }

  function applySlideForm(slide) {
    if (!slide) return;
    inputSlideTitle.value = slide.titulo || '';
    inputSlideBgColor.value = slide.bg_color || '#ffffff';
    inputSlideBgImage.value = slide.bg_image_url || '';
    inputSlideNotes.value = slide.notas || '';
    if (slideStatus) slideStatus.textContent = 'Slide ' + (currentSlideIdx + 1);
  }

  function renderSlideList() {
    var node = el('ped-slide-list');
    if (!node) return;
    node.innerHTML = slides.map(function (slide, index) {
      var activeClass = index === currentSlideIdx ? ' active' : '';
      var style = 'background:linear-gradient(180deg, rgba(15,23,42,.18), rgba(15,23,42,.48)),' + esc(slide.bg_color || '#64748b') + ';';
      if (slide.bg_image_url) {
        style = 'background-image:linear-gradient(180deg, rgba(15,23,42,.18), rgba(15,23,42,.48)),url(' + esc(slide.bg_image_url) + ');background-size:cover;background-position:center;';
      }
      return '<article class="ped-slide-thumb' + activeClass + '" data-slide-idx="' + index + '" style="' + style + '">' +
        '<div class="ped-slide-thumb-num">' + (index + 1) + '</div>' +
        '<div class="ped-slide-thumb-title">' + esc(slide.titulo || ('Diapositiva ' + (index + 1))) + '</div>' +
        '<div class="ped-slide-thumb-meta">' + ((slide.elementos || []).length ? (slide.elementos || []).length + ' elemento(s)' : 'Vacía') + '</div>' +
      '</article>';
    }).join('');
    renderPagesPanel();
  }

  function renderPagesPanel() {
    var node = el('ped-pages-list');
    if (!node) return;
    node.classList.toggle('is-grid', pagesViewMode === 'grid');
    node.innerHTML = slides.map(function (slide, index) {
      var activeClass = index === currentSlideIdx ? ' is-active' : '';
      var style = 'background:linear-gradient(180deg, rgba(15,23,42,.12), rgba(15,23,42,.34)),' + esc(slide.bg_color || '#64748b') + ';';
      if (slide.bg_image_url) {
        style = 'background-image:linear-gradient(180deg, rgba(15,23,42,.12), rgba(15,23,42,.34)),url(' + esc(slide.bg_image_url) + ');background-size:cover;background-position:center;';
      }
      var title = slide.titulo || ('Diapositiva ' + (index + 1));
      return '<article class="ped-page-card' + activeClass + '" data-ped-page-idx="' + index + '">' +
        '<div class="ped-page-row">' +
          '<div>' +
            '<div class="ped-page-thumb" style="' + style + '"></div>' +
            '<div class="ped-page-meta"><span>' + (index + 1) + ' |</span><strong>' + esc(title) + '</strong></div>' +
          '</div>' +
          '<div class="ped-page-actions">' +
            '<button class="ped-page-icon' + (index === currentSlideIdx ? ' is-active' : '') + '" data-ped-page-select="' + index + '" type="button">↪</button>' +
            '<button class="ped-page-icon" data-ped-page-duplicate="' + index + '" type="button">🔑</button>' +
            '<button class="ped-page-icon" data-ped-page-preview="' + index + '" type="button">◉</button>' +
          '</div>' +
        '</div>' +
      '</article>';
    }).join('');
  }
