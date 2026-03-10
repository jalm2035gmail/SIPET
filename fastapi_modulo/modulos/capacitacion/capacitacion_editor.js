/* capacitacion_editor.js — Editor de presentaciones tipo Genially v20260309 */
(function () {
  'use strict';

  // ── Helpers ──────────────────────────────────────────────────────────────

  function el(id) { return document.getElementById(id); }

  function esc(v) {
    return String(v == null ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function toast(msg, isErr) {
    var t = el('ped-toast');
    t.textContent = msg;
    t.className   = 'show' + (isErr ? ' error' : '');
    clearTimeout(toast._tid);
    toast._tid = setTimeout(function () { t.className = ''; }, 2500);
  }

  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  function apiJson(url, opts) {
    return fetch(url, Object.assign({ headers: { 'Content-Type': 'application/json' } }, opts || {}))
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); });
  }

  function embedUrl(url) {
    if (!url) return '';
    // YouTube
    var yt = url.match(/(?:youtube\.com\/(?:watch\?v=|embed\/)|youtu\.be\/)([A-Za-z0-9_-]{11})/);
    if (yt) return 'https://www.youtube.com/embed/' + yt[1];
    // Vimeo
    var vm = url.match(/vimeo\.com\/(\d+)/);
    if (vm) return 'https://player.vimeo.com/video/' + vm[1];
    return url;
  }

  // ── State ─────────────────────────────────────────────────────────────────

  var presId       = parseInt((el('ped-root') || {}).dataset.presId || '0', 10);
  var pres         = null;
  var slides       = [];   // [{id, orden, titulo, bg_color, bg_image_url, notas, elementos:[...]}]
  var curSlideIdx  = 0;
  var selectedElIdx = -1;
  var dirty        = {};   // { slideId: true }
  var dragState    = null;

  var CANVAS_W = 900;
  var CANVAS_H = 506;

  // ── Defaults por tipo ─────────────────────────────────────────────────────

  var DEFAULTS = {
    texto:  { pos_x: 10, pos_y: 35, width: 50, height: 20, z_index: 1,
              contenido_json: { texto: 'Escribe aquí', fontSize: 24, color: '#1e293b', bgColor: '', bold: false, italic: false, align: 'left' } },
    imagen: { pos_x: 25, pos_y: 20, width: 50, height: 50, z_index: 1,
              contenido_json: { url: '', objectFit: 'cover', borderRadius: 0 } },
    boton:  { pos_x: 35, pos_y: 42, width: 30, height: 12, z_index: 2,
              contenido_json: { texto: 'Botón', bgColor: '#4f46e5', textColor: '#ffffff', accion: 'none', slideDest: 1, urlExterno: '' } },
    forma:  { pos_x: 20, pos_y: 20, width: 25, height: 25, z_index: 1,
              contenido_json: { forma: 'rect', bgColor: '#4f46e5', borderColor: '', borderWidth: 0, borderRadius: 0 } },
    embed:  { pos_x: 10, pos_y: 10, width: 80, height: 70, z_index: 1,
              contenido_json: { url: '', allowScroll: false } },
  };

  // ── Load ──────────────────────────────────────────────────────────────────

  function loadPresentation() {
    Promise.all([
      apiJson('/api/capacitacion/presentaciones/' + presId),
      apiJson('/api/capacitacion/presentaciones/' + presId + '/diapositivas')
    ]).then(function (res) {
      if (!res[0].ok) { toast('Error cargando presentación.', true); return; }
      pres   = res[0].data;
      slides = res[1].data || [];
      el('ped-pres-title').value = pres.titulo || '';
      updatePublishBtn();
      renderSlideList();
      selectSlide(0);
    });
  }

  function updatePublishBtn() {
    var btn = el('ped-btn-publish');
    if (!pres) return;
    btn.textContent = pres.estado === 'publicado' ? '📴 Despublicar' : '📣 Publicar';
  }

  // ── Slide list ────────────────────────────────────────────────────────────

  function renderSlideList() {
    var cont = el('ped-slide-list');
    if (!slides.length) { cont.innerHTML = ''; return; }
    cont.innerHTML = slides.map(function (s, i) {
      var bg = s.bg_color ? 'background:' + esc(s.bg_color) + ';' : '';
      return '<div class="ped-slide-thumb' + (i === curSlideIdx ? ' active' : '') + '" data-idx="' + i + '" style="' + bg + '">'
        + '<div class="ped-slide-thumb-num">' + (i + 1) + '</div>'
        + '</div>';
    }).join('');
    cont.onclick = function (e) {
      var thumb = e.target.closest('.ped-slide-thumb');
      if (!thumb) return;
      var idx = parseInt(thumb.dataset.idx, 10);
      if (idx !== curSlideIdx) { saveCurrentSlideElements(function () { selectSlide(idx); }); }
    };
  }

  function selectSlide(idx) {
    curSlideIdx   = clamp(idx, 0, slides.length - 1);
    selectedElIdx = -1;
    renderSlideList();
    renderCanvas();
    renderProps();
  }

  // ── Canvas ────────────────────────────────────────────────────────────────

  function renderCanvas() {
    var canvas = el('ped-canvas');
    var slide  = slides[curSlideIdx];
    if (!slide) { canvas.innerHTML = ''; return; }

    canvas.style.background = slide.bg_color || '#ffffff';
    if (slide.bg_image_url) {
      canvas.style.backgroundImage  = 'url(' + esc(slide.bg_image_url) + ')';
      canvas.style.backgroundSize   = 'cover';
      canvas.style.backgroundPosition = 'center';
    } else {
      canvas.style.backgroundImage = 'none';
    }

    canvas.innerHTML = '';
    (slide.elementos || []).forEach(function (el_, i) {
      canvas.appendChild(buildElDiv(el_, i));
    });
    canvas.addEventListener('click', function (e) {
      if (e.target === canvas) { clickSelect(-1); }
    });
  }

  function buildElDiv(el_, idx) {
    var d = document.createElement('div');
    d.className = 'ped-element' + (idx === selectedElIdx ? ' selected' : '');
    d.style.left   = el_.pos_x  + '%';
    d.style.top    = el_.pos_y  + '%';
    d.style.width  = el_.width  + '%';
    d.style.height = el_.height + '%';
    d.style.zIndex = el_.z_index || 1;
    d.dataset.idx  = idx;

    var c = el_.contenido_json || {};
    var inner = document.createElement('div');
    inner.className = 'ped-el-' + el_.tipo;

    switch (el_.tipo) {
      case 'texto':
        inner.style.cssText = [
          'width:100%;height:100%;display:flex;align-items:center;box-sizing:border-box;padding:6px 8px;overflow:hidden;',
          'font-size:' + (c.fontSize || 16) + 'px;',
          'color:' + (c.color || '#1e293b') + ';',
          c.bgColor ? 'background:' + c.bgColor + ';' : '',
          c.bold   ? 'font-weight:700;' : '',
          c.italic ? 'font-style:italic;' : '',
          'text-align:' + (c.align || 'left') + ';',
          'white-space:pre-wrap;word-break:break-word;'
        ].join('');
        inner.textContent = c.texto || '';
        break;

      case 'imagen':
        inner.style.cssText = 'width:100%;height:100%;overflow:hidden;' + (c.borderRadius ? 'border-radius:' + c.borderRadius + 'px;' : '');
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
          'width:100%;height:100%;display:flex;align-items:center;justify-content:center;',
          'background:' + (c.bgColor || '#4f46e5') + ';',
          'color:' + (c.textColor || '#fff') + ';',
          'border-radius:8px;cursor:pointer;font-weight:600;font-size:14px;',
          'user-select:none;text-align:center;padding:4px 8px;box-sizing:border-box;overflow:hidden;'
        ].join('');
        inner.textContent = c.texto || 'Botón';
        break;

      case 'forma':
        var isCircle = c.forma === 'circle';
        inner.style.cssText = [
          'width:100%;height:100%;',
          'background:' + (c.bgColor || '#4f46e5') + ';',
          isCircle ? 'border-radius:50%;' : (c.borderRadius ? 'border-radius:' + c.borderRadius + 'px;' : ''),
          c.borderColor ? 'border:' + (c.borderWidth || 1) + 'px solid ' + c.borderColor + ';' : '',
          'box-sizing:border-box;'
        ].join('');
        break;

      case 'embed':
        var eUrl = embedUrl(c.url || '');
        inner.style.cssText = 'width:100%;height:100%;background:#000;overflow:hidden;';
        if (eUrl) {
          var iframe = document.createElement('iframe');
          iframe.src = eUrl;
          iframe.setAttribute('allowfullscreen', '1');
          iframe.style.cssText = 'width:100%;height:100%;border:none;pointer-events:none;display:block;';
          inner.appendChild(iframe);
        } else {
          inner.style.cssText += 'display:flex;align-items:center;justify-content:center;';
          inner.innerHTML = '<span style="color:#fff;opacity:.5;font-size:24px;">▶</span>';
        }
        break;
    }

    d.appendChild(inner);

    // Resize handles (only when selected)
    if (idx === selectedElIdx) {
      ['nw','n','ne','w','e','sw','s','se'].forEach(function (h) {
        var handle = document.createElement('div');
        handle.className = 'ped-handle ped-handle-' + h;
        handle.dataset.handle = h;
        handle.addEventListener('mousedown', function (e) {
          e.stopPropagation();
          startDrag(e, idx, true, h);
        });
        d.appendChild(handle);
      });
    }

    d.addEventListener('mousedown', function (e) {
      if (e.target.classList.contains('ped-handle')) return;
      e.stopPropagation();
      if (idx !== selectedElIdx) { clickSelect(idx); }
      startDrag(e, idx, false, null);
    });

    return d;
  }

  // ── Select / click ────────────────────────────────────────────────────────

  function clickSelect(idx) {
    selectedElIdx = idx;
    renderCanvas();
    renderProps();
  }

  // ── Drag & Resize ─────────────────────────────────────────────────────────

  function startDrag(e, elIdx, isResize, handle) {
    e.preventDefault();
    var slide = slides[curSlideIdx];
    var el_   = slide.elementos[elIdx];
    dragState = {
      isResize: isResize,
      handle:   handle,
      elIdx:    elIdx,
      startMx:  e.clientX,
      startMy:  e.clientY,
      startEl:  { pos_x: el_.pos_x, pos_y: el_.pos_y, width: el_.width, height: el_.height },
    };
  }

  document.addEventListener('mousemove', function (e) {
    if (!dragState) return;
    var slide = slides[curSlideIdx];
    if (!slide) return;
    var el_   = slide.elementos[dragState.elIdx];
    var dx    = (e.clientX - dragState.startMx) / CANVAS_W * 100;
    var dy    = (e.clientY - dragState.startMy) / CANVAS_H * 100;
    var s     = dragState.startEl;

    if (!dragState.isResize) {
      el_.pos_x = clamp(s.pos_x + dx, 0, 100 - el_.width);
      el_.pos_y = clamp(s.pos_y + dy, 0, 100 - el_.height);
    } else {
      var h = dragState.handle;
      var nw_x = s.pos_x, nw_y = s.pos_y, w_ = s.width, h_ = s.height;
      var right  = nw_x + w_;
      var bottom = nw_y + h_;

      if (h.indexOf('w') !== -1) { nw_x = Math.min(s.pos_x + dx, right - 2); }
      if (h.indexOf('n') !== -1) { nw_y = Math.min(s.pos_y + dy, bottom - 2); }
      if (h.indexOf('e') !== -1) { right  = Math.max(s.pos_x + s.width + dx, nw_x + 2); }
      if (h.indexOf('s') !== -1) { bottom = Math.max(s.pos_y + s.height + dy, nw_y + 2); }

      el_.pos_x  = clamp(nw_x, 0, 99);
      el_.pos_y  = clamp(nw_y, 0, 99);
      el_.width  = clamp(right  - el_.pos_x, 2, 100 - el_.pos_x);
      el_.height = clamp(bottom - el_.pos_y, 2, 100 - el_.pos_y);
    }

    markDirty();
    renderCanvas();
  });

  document.addEventListener('mouseup', function () {
    dragState = null;
  });

  // ── Props panel ───────────────────────────────────────────────────────────

  function renderProps() {
    var props = el('ped-props');
    var slide = slides[curSlideIdx];

    if (selectedElIdx === -1 || !slide) {
      // Show slide properties
      if (!slide) { props.innerHTML = '<div class="ped-props-empty">Sin diapositiva</div>'; return; }
      props.innerHTML = slidePropsHTML(slide);
      wireSlideProps(slide);
      return;
    }

    var elem = slide.elementos[selectedElIdx];
    if (!elem) { props.innerHTML = '<div class="ped-props-empty">Sin elemento</div>'; return; }
    props.innerHTML = elPropsHTML(elem);
    wireElProps(elem, selectedElIdx);
  }

  function slidePropsHTML(slide) {
    return [
      '<div class="ped-slide-bg-section">',
        '<div class="ped-prop-row">',
          '<label>Título diapositiva</label>',
          '<input type="text" id="sp-titulo" value="' + esc(slide.titulo || '') + '" />',
        '</div>',
        '<div class="ped-prop-row">',
          '<label>Color de fondo</label>',
          '<div class="ped-prop-inline">',
            '<input type="color" id="sp-bg-color" value="' + esc(slide.bg_color || '#ffffff') + '" />',
            '<input type="text" id="sp-bg-color-txt" value="' + esc(slide.bg_color || '#ffffff') + '" style="flex:1;" />',
          '</div>',
        '</div>',
        '<div class="ped-prop-row">',
          '<label>Imagen de fondo (URL)</label>',
          '<input type="url" id="sp-bg-image" value="' + esc(slide.bg_image_url || '') + '" placeholder="https://..." />',
        '</div>',
        '<div class="ped-prop-row">',
          '<label>Notas</label>',
          '<textarea id="sp-notas">' + esc(slide.notas || '') + '</textarea>',
        '</div>',
      '</div>'
    ].join('');
  }

  function wireSlideProps(slide) {
    function update() {
      slide.titulo        = (el('sp-titulo')    || {}).value || '';
      slide.bg_color      = (el('sp-bg-color')  || {}).value || '';
      slide.bg_image_url  = (el('sp-bg-image')  || {}).value || '';
      slide.notas         = (el('sp-notas')     || {}).value || '';
      el('sp-bg-color-txt') && (el('sp-bg-color-txt').value = slide.bg_color);
      markDirty();
      renderCanvas();
      renderSlideList();
      saveSlideProps(slide);
    }
    ['sp-titulo','sp-bg-color','sp-bg-image','sp-notas'].forEach(function (id) {
      var inp = el(id); if (inp) inp.addEventListener('input', update);
    });
    var colorTxt = el('sp-bg-color-txt');
    if (colorTxt) colorTxt.addEventListener('input', function () {
      var v = colorTxt.value.trim();
      if (/^#[0-9a-fA-F]{3,6}$/.test(v)) { el('sp-bg-color').value = v; update(); }
    });
  }

  function saveSlideProps(slide) {
    apiJson('/api/capacitacion/diapositivas/' + slide.id, {
      method: 'PUT',
      body: JSON.stringify({ titulo: slide.titulo, bg_color: slide.bg_color, bg_image_url: slide.bg_image_url, notas: slide.notas })
    });
  }

  function elPropsHTML(elem) {
    var c = elem.contenido_json || {};
    var rows = [
      '<div class="ped-prop-row"><label>Tipo</label><input type="text" value="' + esc(elem.tipo) + '" disabled /></div>',
      '<div class="ped-prop-row"><label>Z-index</label><input type="number" id="ep-z" value="' + esc(elem.z_index) + '" min="1" max="999" /></div>',
    ];

    switch (elem.tipo) {
      case 'texto':
        rows.push(
          '<div class="ped-prop-row"><label>Texto</label><textarea id="ep-texto">' + esc(c.texto || '') + '</textarea></div>',
          '<div class="ped-prop-row"><label>Tamaño fuente (px)</label><input type="number" id="ep-fontsize" value="' + esc(c.fontSize || 16) + '" min="8" max="120" /></div>',
          '<div class="ped-prop-row"><label>Color texto</label><div class="ped-prop-inline"><input type="color" id="ep-color" value="' + esc(c.color || '#1e293b') + '" /><input type="text" id="ep-color-txt" value="' + esc(c.color || '#1e293b') + '" style="flex:1;" /></div></div>',
          '<div class="ped-prop-row"><label>Color fondo</label><div class="ped-prop-inline"><input type="color" id="ep-bgcolor" value="' + esc(c.bgColor || '#ffffff') + '" /><input type="text" id="ep-bgcolor-txt" value="' + esc(c.bgColor || '') + '" style="flex:1;" placeholder="ninguno" /></div></div>',
          '<div class="ped-prop-row"><label>Alineación</label><select id="ep-align"><option value="left"' + (c.align==='left'?' selected':'')+'>Izq</option><option value="center"' + (c.align==='center'?' selected':'')+'>Centro</option><option value="right"' + (c.align==='right'?' selected':'')+'>Der</option></select></div>',
          '<div class="ped-prop-row"><label><input type="checkbox" id="ep-bold"' + (c.bold?' checked':'')+' /> Negrita</label></div>',
          '<div class="ped-prop-row"><label><input type="checkbox" id="ep-italic"' + (c.italic?' checked':'')+' /> Cursiva</label></div>'
        );
        break;

      case 'imagen':
        rows.push(
          '<div class="ped-prop-row"><label>URL imagen</label><input type="url" id="ep-url" value="' + esc(c.url || '') + '" placeholder="https://..." /></div>',
          '<div class="ped-prop-row"><label>Object fit</label><select id="ep-objectfit"><option value="cover"' + (c.objectFit==='cover'?' selected':'')+'>Cover</option><option value="contain"' + (c.objectFit==='contain'?' selected':'')+'>Contain</option><option value="fill"' + (c.objectFit==='fill'?' selected':'')+'>Fill</option></select></div>',
          '<div class="ped-prop-row"><label>Border radius (px)</label><input type="number" id="ep-borderradius" value="' + esc(c.borderRadius || 0) + '" min="0" max="500" /></div>'
        );
        break;

      case 'boton':
        rows.push(
          '<div class="ped-prop-row"><label>Texto botón</label><input type="text" id="ep-btntexto" value="' + esc(c.texto || '') + '" /></div>',
          '<div class="ped-prop-row"><label>Color fondo</label><div class="ped-prop-inline"><input type="color" id="ep-btnbg" value="' + esc(c.bgColor || '#4f46e5') + '" /><input type="text" id="ep-btnbg-txt" value="' + esc(c.bgColor || '#4f46e5') + '" style="flex:1;" /></div></div>',
          '<div class="ped-prop-row"><label>Color texto</label><div class="ped-prop-inline"><input type="color" id="ep-btntextcolor" value="' + esc(c.textColor || '#ffffff') + '" /><input type="text" id="ep-btntextcolor-txt" value="' + esc(c.textColor || '#ffffff') + '" style="flex:1;" /></div></div>',
          '<div class="ped-prop-row"><label>Acción al hacer clic</label><select id="ep-accion"><option value="none"' + (c.accion==='none'?' selected':'')+'>Ninguna</option><option value="slide"' + (c.accion==='slide'?' selected':'')+'>Ir a diapositiva</option><option value="url"' + (c.accion==='url'?' selected':'')+'>Abrir URL</option></select></div>',
          '<div class="ped-prop-row"><label>Diapositiva destino</label><input type="number" id="ep-slidedest" value="' + esc(c.slideDest || 1) + '" min="1" /></div>',
          '<div class="ped-prop-row"><label>URL destino</label><input type="url" id="ep-urlext" value="' + esc(c.urlExterno || '') + '" placeholder="https://..." /></div>'
        );
        break;

      case 'forma':
        rows.push(
          '<div class="ped-prop-row"><label>Forma</label><select id="ep-forma"><option value="rect"' + (c.forma==='rect'?' selected':'')+'>Rectángulo</option><option value="circle"' + (c.forma==='circle'?' selected':'')+'>Círculo/Elipse</option></select></div>',
          '<div class="ped-prop-row"><label>Color</label><div class="ped-prop-inline"><input type="color" id="ep-formabg" value="' + esc(c.bgColor || '#4f46e5') + '" /><input type="text" id="ep-formabg-txt" value="' + esc(c.bgColor || '#4f46e5') + '" style="flex:1;" /></div></div>',
          '<div class="ped-prop-row"><label>Color borde</label><div class="ped-prop-inline"><input type="color" id="ep-formaborder" value="' + esc(c.borderColor || '#000000') + '" /><input type="text" id="ep-formaborder-txt" value="' + esc(c.borderColor || '') + '" style="flex:1;" placeholder="ninguno" /></div></div>',
          '<div class="ped-prop-row"><label>Grosor borde (px)</label><input type="number" id="ep-borderw" value="' + esc(c.borderWidth || 0) + '" min="0" max="20" /></div>',
          '<div class="ped-prop-row"><label>Border radius (px)</label><input type="number" id="ep-formaradius" value="' + esc(c.borderRadius || 0) + '" min="0" max="500" /></div>'
        );
        break;

      case 'embed':
        rows.push(
          '<div class="ped-prop-row"><label>URL (YouTube, Vimeo, o embed)</label><input type="url" id="ep-embedurl" value="' + esc(c.url || '') + '" placeholder="https://youtube.com/watch?v=..." /></div>'
        );
        break;
    }

    rows.push('<button class="ped-prop-del-btn" id="ep-del-btn">🗑 Eliminar elemento</button>');
    return rows.join('');
  }

  function wireElProps(elem, idx) {
    var c = elem.contenido_json;
    if (!c) { elem.contenido_json = {}; c = elem.contenido_json; }

    function update() {
      switch (elem.tipo) {
        case 'texto':
          c.texto    = (el('ep-texto')    || {}).value || '';
          c.fontSize = parseInt((el('ep-fontsize') || {}).value, 10) || 16;
          c.color    = (el('ep-color')    || {}).value || '#1e293b';
          c.bgColor  = (el('ep-bgcolor-txt') || {}).value.trim() || '';
          c.bold     = !!(el('ep-bold')   || {}).checked;
          c.italic   = !!(el('ep-italic') || {}).checked;
          c.align    = (el('ep-align')    || {}).value || 'left';
          break;
        case 'imagen':
          c.url          = (el('ep-url')          || {}).value || '';
          c.objectFit    = (el('ep-objectfit')     || {}).value || 'cover';
          c.borderRadius = parseInt((el('ep-borderradius') || {}).value, 10) || 0;
          break;
        case 'boton':
          c.texto     = (el('ep-btntexto')         || {}).value || '';
          c.bgColor   = (el('ep-btnbg-txt')        || {}).value || '#4f46e5';
          c.textColor = (el('ep-btntextcolor-txt') || {}).value || '#ffffff';
          c.accion    = (el('ep-accion')           || {}).value || 'none';
          c.slideDest = parseInt((el('ep-slidedest') || {}).value, 10) || 1;
          c.urlExterno = (el('ep-urlext')          || {}).value || '';
          break;
        case 'forma':
          c.forma       = (el('ep-forma')          || {}).value || 'rect';
          c.bgColor     = (el('ep-formabg-txt')    || {}).value || '#4f46e5';
          c.borderColor = (el('ep-formaborder-txt')|| {}).value.trim() || '';
          c.borderWidth = parseInt((el('ep-borderw')      || {}).value, 10) || 0;
          c.borderRadius= parseInt((el('ep-formaradius')  || {}).value, 10) || 0;
          break;
        case 'embed':
          c.url = (el('ep-embedurl') || {}).value || '';
          break;
      }
      elem.z_index = parseInt((el('ep-z') || {}).value, 10) || 1;
      markDirty();
      renderCanvas();
    }

    // Wire color pickers ↔ text inputs
    var colorPairs = {
      'ep-color': 'ep-color-txt', 'ep-bgcolor': 'ep-bgcolor-txt',
      'ep-btnbg': 'ep-btnbg-txt', 'ep-btntextcolor': 'ep-btntextcolor-txt',
      'ep-formabg': 'ep-formabg-txt', 'ep-formaborder': 'ep-formaborder-txt'
    };
    Object.keys(colorPairs).forEach(function (pickId) {
      var txtId = colorPairs[pickId];
      var pick = el(pickId), txt = el(txtId);
      if (!pick || !txt) return;
      pick.addEventListener('input', function () { txt.value = pick.value; update(); });
      txt.addEventListener('input', function () {
        if (/^#[0-9a-fA-F]{3,6}$/.test(txt.value.trim())) { pick.value = txt.value.trim(); }
        update();
      });
    });

    // Wire all other inputs
    var inputIds = [
      'ep-z','ep-texto','ep-fontsize','ep-align','ep-bold','ep-italic',
      'ep-url','ep-objectfit','ep-borderradius',
      'ep-btntexto','ep-accion','ep-slidedest','ep-urlext',
      'ep-forma','ep-borderw','ep-formaradius',
      'ep-embedurl'
    ];
    inputIds.forEach(function (id) {
      var inp = el(id); if (!inp) return;
      inp.addEventListener('input', update);
      inp.addEventListener('change', update);
    });

    var delBtn = el('ep-del-btn');
    if (delBtn) delBtn.addEventListener('click', function () {
      slides[curSlideIdx].elementos.splice(idx, 1);
      selectedElIdx = -1;
      markDirty();
      renderCanvas();
      renderProps();
    });
  }

  // ── Slide operations ──────────────────────────────────────────────────────

  function addSlide() {
    apiJson('/api/capacitacion/presentaciones/' + presId + '/diapositivas', {
      method: 'POST', body: JSON.stringify({ titulo: '' })
    }).then(function (res) {
      if (!res.ok) { toast('Error creando diapositiva.', true); return; }
      var newSlide = res.data;
      newSlide.elementos = newSlide.elementos || [];
      slides.push(newSlide);
      selectSlide(slides.length - 1);
    });
  }

  function delSlide() {
    if (slides.length <= 1) { toast('La presentación debe tener al menos una diapositiva.'); return; }
    var slide = slides[curSlideIdx];
    if (!confirm('¿Eliminar diapositiva ' + (curSlideIdx + 1) + '?')) return;
    apiJson('/api/capacitacion/diapositivas/' + slide.id, { method: 'DELETE' }).then(function (res) {
      if (!res.ok) { toast('Error eliminando.', true); return; }
      slides.splice(curSlideIdx, 1);
      selectSlide(Math.min(curSlideIdx, slides.length - 1));
    });
  }

  function dupSlide() {
    var slide = slides[curSlideIdx];
    apiJson('/api/capacitacion/diapositivas/' + slide.id + '/duplicar', { method: 'POST' })
      .then(function (res) {
        if (!res.ok) { toast('Error duplicando.', true); return; }
        var newSlide = res.data;
        newSlide.elementos = newSlide.elementos || [];
        slides.splice(curSlideIdx + 1, 0, newSlide);
        selectSlide(curSlideIdx + 1);
      });
  }

  function moveSlide(dir) {
    var newIdx = curSlideIdx + dir;
    if (newIdx < 0 || newIdx >= slides.length) return;
    var tmp = slides[curSlideIdx];
    slides[curSlideIdx] = slides[newIdx];
    slides[newIdx]      = tmp;
    curSlideIdx = newIdx;
    var ordenIds = slides.map(function (s) { return s.id; });
    apiJson('/api/capacitacion/presentaciones/' + presId + '/reordenar', {
      method: 'PUT', body: JSON.stringify({ orden_ids: ordenIds })
    });
    renderSlideList();
    renderCanvas();
  }

  // ── Add element ───────────────────────────────────────────────────────────

  function addElement(tipo) {
    var slide = slides[curSlideIdx];
    if (!slide) return;
    var def = DEFAULTS[tipo];
    if (!def) return;
    var elem = {
      tipo:         tipo,
      pos_x:        def.pos_x,
      pos_y:        def.pos_y,
      width:        def.width,
      height:       def.height,
      z_index:      def.z_index,
      contenido_json: JSON.parse(JSON.stringify(def.contenido_json))
    };
    slide.elementos = slide.elementos || [];
    slide.elementos.push(elem);
    selectedElIdx = slide.elementos.length - 1;
    markDirty();
    renderCanvas();
    renderProps();
  }

  // ── Save ──────────────────────────────────────────────────────────────────

  function markDirty() {
    var slide = slides[curSlideIdx];
    if (slide) { dirty[slide.id] = true; }
  }

  function saveCurrentSlideElements(cb) {
    var slide = slides[curSlideIdx];
    if (!slide || !dirty[slide.id]) { if (cb) cb(); return; }
    var payload = (slide.elementos || []).map(function (e) {
      return {
        tipo:         e.tipo,
        contenido_json: e.contenido_json,
        pos_x:  e.pos_x,  pos_y:   e.pos_y,
        width:  e.width,  height:  e.height,
        z_index: e.z_index
      };
    });
    apiJson('/api/capacitacion/diapositivas/' + slide.id + '/elementos', {
      method: 'PUT',
      body: JSON.stringify({ elementos: payload })
    }).then(function (res) {
      if (res.ok) { delete dirty[slide.id]; }
      if (cb) cb();
    });
  }

  function saveAll(showToast) {
    // Save title
    apiJson('/api/capacitacion/presentaciones/' + presId, {
      method: 'PUT',
      body: JSON.stringify({ titulo: (el('ped-pres-title') || {}).value || '' })
    });

    var dirtyIds = Object.keys(dirty).map(Number);
    if (!dirtyIds.length) { if (showToast !== false) toast('Guardado ✓'); return; }

    var promises = dirtyIds.map(function (slideId) {
      var slide = slides.find(function (s) { return s.id === slideId; });
      if (!slide) return Promise.resolve();
      var payload = (slide.elementos || []).map(function (e) {
        return {
          tipo:         e.tipo,
          contenido_json: e.contenido_json,
          pos_x: e.pos_x, pos_y: e.pos_y,
          width: e.width,  height: e.height,
          z_index: e.z_index
        };
      });
      return apiJson('/api/capacitacion/diapositivas/' + slide.id + '/elementos', {
        method: 'PUT',
        body: JSON.stringify({ elementos: payload })
      }).then(function (res) { if (res.ok) { delete dirty[slideId]; } });
    });

    Promise.all(promises).then(function () {
      if (showToast !== false) toast('Guardado ✓');
    });
  }

  // ── Publish ───────────────────────────────────────────────────────────────

  function togglePublish() {
    if (!pres) return;
    var nuevoEstado = pres.estado === 'publicado' ? 'borrador' : 'publicado';
    apiJson('/api/capacitacion/presentaciones/' + presId, {
      method: 'PUT',
      body: JSON.stringify({ estado: nuevoEstado })
    }).then(function (res) {
      if (res.ok) {
        pres.estado = nuevoEstado;
        updatePublishBtn();
        toast(nuevoEstado === 'publicado' ? 'Presentación publicada ✓' : 'Marcada como borrador');
      } else {
        toast('Error al cambiar estado.', true);
      }
    });
  }

  // ── Keyboard shortcuts ────────────────────────────────────────────────────

  document.addEventListener('keydown', function (e) {
    var tag = (e.target || {}).tagName || '';
    var isInput = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT';

    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      saveAll();
      return;
    }
    if (isInput) return;

    if (e.key === 'Delete' || e.key === 'Backspace') {
      if (selectedElIdx !== -1) {
        slides[curSlideIdx].elementos.splice(selectedElIdx, 1);
        selectedElIdx = -1;
        markDirty();
        renderCanvas();
        renderProps();
      }
    }
    if (e.key === 'Escape') { clickSelect(-1); }
    if (e.key === 'ArrowRight') { saveCurrentSlideElements(function () { selectSlide(curSlideIdx + 1); }); }
    if (e.key === 'ArrowLeft')  { saveCurrentSlideElements(function () { selectSlide(curSlideIdx - 1); }); }
  });

  // ── Wire toolbar buttons ──────────────────────────────────────────────────

  el('ped-btn-add-texto')  && el('ped-btn-add-texto').addEventListener('click',  function () { addElement('texto'); });
  el('ped-btn-add-imagen') && el('ped-btn-add-imagen').addEventListener('click', function () { addElement('imagen'); });
  el('ped-btn-add-boton')  && el('ped-btn-add-boton').addEventListener('click',  function () { addElement('boton'); });
  el('ped-btn-add-forma')  && el('ped-btn-add-forma').addEventListener('click',  function () { addElement('forma'); });
  el('ped-btn-add-embed')  && el('ped-btn-add-embed').addEventListener('click',  function () { addElement('embed'); });

  el('ped-btn-add-slide')  && el('ped-btn-add-slide').addEventListener('click',  addSlide);
  el('ped-btn-del-slide')  && el('ped-btn-del-slide').addEventListener('click',  delSlide);
  el('ped-btn-dup-slide')  && el('ped-btn-dup-slide').addEventListener('click',  dupSlide);
  el('ped-btn-slide-up')   && el('ped-btn-slide-up').addEventListener('click',   function () { moveSlide(-1); });
  el('ped-btn-slide-dn')   && el('ped-btn-slide-dn').addEventListener('click',   function () { moveSlide(1); });

  el('ped-btn-save')       && el('ped-btn-save').addEventListener('click',       function () { saveAll(); });
  el('ped-btn-publish')    && el('ped-btn-publish').addEventListener('click',    togglePublish);

  el('ped-btn-preview') && el('ped-btn-preview').addEventListener('click', function () {
    window.open('/capacitacion/presentacion/' + presId + '/ver', '_blank');
  });
  el('ped-btn-back') && el('ped-btn-back').addEventListener('click', function () {
    saveAll(false);
    window.location.href = '/capacitacion/presentaciones';
  });

  el('ped-pres-title') && el('ped-pres-title').addEventListener('blur', function () {
    if (pres) {
      pres.titulo = el('ped-pres-title').value;
      apiJson('/api/capacitacion/presentaciones/' + presId, {
        method: 'PUT', body: JSON.stringify({ titulo: pres.titulo })
      });
    }
  });

  // ── Boot ──────────────────────────────────────────────────────────────────

  if (presId) {
    loadPresentation();
  } else {
    toast('ID de presentación inválido.', true);
  }

})();
