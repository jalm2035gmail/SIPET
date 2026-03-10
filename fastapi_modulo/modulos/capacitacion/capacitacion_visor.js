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
  var pres    = null;
  var slides  = [];
  var curIdx  = 0;

  // ── Load ──────────────────────────────────────────────────────────────────

  function load() {
    Promise.all([
      apiJson('/api/capacitacion/presentaciones/' + presId),
      apiJson('/api/capacitacion/presentaciones/' + presId + '/diapositivas')
    ]).then(function (res) {
      if (!res[0].ok) {
        el('visor-loading').textContent = 'No se pudo cargar la presentación.';
        return;
      }
      pres   = res[0].data;
      slides = res[1].data || [];
      el('visor-pres-title').textContent = pres.titulo || 'Presentación';
      el('visor-loading').style.display  = 'none';
      renderDots();
      renderSlide(0);
      updateNav();
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
    Array.prototype.slice.call(area.querySelectorAll('.visor-element')).forEach(function (n) { n.remove(); });

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
    var wrapper = document.querySelector('.visor-slide-wrapper');
    if (!wrapper) return;
    if (!document.fullscreenElement) {
      wrapper.requestFullscreen && wrapper.requestFullscreen();
    } else {
      document.exitFullscreen && document.exitFullscreen();
    }
  });

  // Keyboard
  document.addEventListener('keydown', function (e) {
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

  // ── Boot ──────────────────────────────────────────────────────────────────

  if (presId) {
    load();
  } else {
    el('visor-loading').textContent = 'ID de presentación inválido.';
  }

})();
