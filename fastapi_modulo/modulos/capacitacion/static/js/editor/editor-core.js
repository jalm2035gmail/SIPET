'use strict';

function el(id) { return document.getElementById(id); }
function esc(v) {
  return String(v == null ? '' : v)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function paintEditorBackground(slide) {
  if (!editor || !editor.Canvas || !slide) return;
  try {
    var doc = editor.Canvas.getDocument();
    if (!doc || !doc.body) return;

    doc.body.style.backgroundColor = slide.bg_color || '#ffffff';

    if (slide.bg_image_url) {
      doc.body.style.backgroundImage = 'url(' + slide.bg_image_url + ')';
      doc.body.style.backgroundSize = 'cover';
      doc.body.style.backgroundPosition = 'center';
      doc.body.style.backgroundRepeat = 'no-repeat';
    } else {
      doc.body.style.backgroundImage = 'none';
    }

    if (editor.Canvas.getBody) {
      var canvasBody = editor.Canvas.getBody();
      if (canvasBody) {
        canvasBody.style.backgroundColor = slide.bg_color || '#ffffff';
        if (slide.bg_image_url) {
          canvasBody.style.backgroundImage = 'url(' + slide.bg_image_url + ')';
          canvasBody.style.backgroundSize = 'cover';
          canvasBody.style.backgroundPosition = 'center';
          canvasBody.style.backgroundRepeat = 'no-repeat';
        } else {
          canvasBody.style.backgroundImage = 'none';
        }
      }
    }
  } catch (error) {}
}
function toast(msg, isError) {
  var node = el('ped-toast');
  if (!node) return;
  node.textContent = msg || '';
  node.classList.toggle('error', !!isError);
  node.classList.add('show');
  clearTimeout(toast._timer);
  toast._timer = setTimeout(function () { node.classList.remove('show'); }, 2600);
}
function clamp(value, min, max) { return Math.max(min, Math.min(max, value)); }
function readCanvasDimension(varName, fallback) {
  if (!root || !window.getComputedStyle) return fallback;
  var value = parseFloat(window.getComputedStyle(root).getPropertyValue(varName));
  return isFinite(value) && value > 0 ? value : fallback;
}
function getCanvasViewport() {
  var width = readCanvasDimension('--ped-canvas-width', 1280);
  var height = readCanvasDimension('--ped-canvas-height', 720);
  return {
    width: width,
    height: height,
    widthPx: width + 'px',
    heightPx: height + 'px'
  };
}

function apiJson(url, opts) {
  return fetch(url, Object.assign({ headers: { 'Content-Type': 'application/json' } }, opts || {}))
    .then(function (response) {
      return response.text().then(function (text) {
        var data = text ? JSON.parse(text) : null;
        return { ok: response.ok, status: response.status, data: data };
      });
    });
}

var root = el('ped-root');
var presId = root ? parseInt(root.getAttribute('data-pres-id') || '0', 10) : 0;
var editorBootstrapError = !root ? null : (!presId ? 'Presentación inválida.' : (!window.grapesjs ? 'GrapesJS no está disponible.' : null));

var editor = null;
var presentation = null;
var slides = [];
var liveSurveys = [];
var surveyAnalytics = {};
var currentSlideIdx = -1;
var editorReady = false;
var saving = false;
var pagesViewMode = 'list';
var backgroundInputsBound = false;

var inputPresTitle = el('ped-pres-title');
var inputSlideTitle = el('ped-slide-title');
var inputSlideBgColor = el('ped-slide-bg-color');
var inputSlideBgImage = el('ped-slide-bg-image');
var inputSlideNotes = el('ped-slide-notes');
var slideStatus = el('ped-slide-status');
var widgetConfig = el('ped-widget-config');
var auditMeta = el('ped-audit-meta');
var auditList = el('ped-audit-list');
var resourcePanel = el('ped-resource-panel');
var textPanel = el('ped-text-panel');
var interactivePanel = el('ped-interactive-panel');
var questionsPanel = el('ped-questions-panel');
var widgetsPanel = el('ped-widgets-panel');
var insertPanel = el('ped-insert-panel');
var stylePanel = el('ped-style-panel');
var backgroundPanel = el('ped-background-panel');
var pagesPanel = el('ped-pages-panel');
var workspace = root ? root.querySelector('.ped-workspace') : null;
var toggleSidepanelBtn = el('ped-btn-toggle-sidepanel');
var sidepanelHead = el('ped-sidepanel-head');
var sidepanelTitle = el('ped-sidepanel-title');
var sidepanelCopy = el('ped-sidepanel-copy');
var slideSettingsPanel = el('ped-slide-settings');
var panelTabs = el('ped-panel-tabs');
var propsPanel = el('ped-props');
var stageWrap = root ? root.querySelector('.ped-stage-wrap') : null;
var sidepanelCollapsed = false;

function auditActionLabel(action) {
  var labels = {
    created: 'Creado',
    updated: 'Actualizado',
    published: 'Publicado',
    deleted: 'Eliminado',
    slide_created: 'Slide creada',
    slide_updated: 'Slide editada',
    slide_deleted: 'Slide eliminada',
    slide_duplicated: 'Slide duplicada',
    slides_reordered: 'Slides reordenadas',
    elements_saved: 'Elementos guardados'
  };
  return labels[action] || String(action || 'Evento');
}

function renderAuditTrail(items) {
  if (!auditList) return;
  if (!items || !items.length) {
    auditList.innerHTML = '<div class="ped-empty">Sin historial disponible.</div>';
    if (auditMeta) auditMeta.textContent = 'Sin actividad reciente.';
    return;
  }
  if (auditMeta) auditMeta.textContent = items.length + ' evento(s) recientes.';
  auditList.innerHTML = items.slice(0, 8).map(function (item) {
    var actor = item.actor_nombre || item.actor_key || 'Sistema';
    var date = item.creado_en ? String(item.creado_en).replace('T', ' ').slice(0, 16) : 'Sin fecha';
    return '<article class="ped-audit-item">' +
      '<strong>' + esc(auditActionLabel(item.accion)) + '</strong>' +
      '<span>' + esc(actor) + ' · ' + esc(date) + '</span>' +
    '</article>';
  }).join('');
}

function loadAuditTrail() {
  if (!presId || !auditList) return Promise.resolve([]);
  auditList.innerHTML = '<div class="ped-empty">Cargando historial…</div>';
  return apiJson('/api/capacitacion/auditoria/presentacion/' + presId)
    .then(function (res) {
      var items = res && res.ok && res.data && Array.isArray(res.data.items) ? res.data.items : [];
      renderAuditTrail(items);
      return items;
    })
    .catch(function () {
      renderAuditTrail([]);
      return [];
    });
}

function bindBackgroundInputs() {
  if (backgroundInputsBound || !inputSlideBgColor) return;
  backgroundInputsBound = true;

  inputSlideBgColor.addEventListener('input', function () {
    var slide = currentSlide();
    if (!slide) return;
    slide.bg_color = inputSlideBgColor.value || '#ffffff';
    paintEditorBackground(slide);
    renderSlideList();
    updateBackgroundPreview(slide.bg_color);
  });

  inputSlideBgColor.addEventListener('change', function () {
    applyBackgroundColor(inputSlideBgColor.value || '#ffffff', false);
  });
}

function setDefaultSidepanelCopy() {
  if (sidepanelTitle) sidepanelTitle.textContent = 'Panel de edición';
  if (sidepanelCopy) sidepanelCopy.textContent = 'Bloques, estilos, capas y propiedades de cada slide.';
}

function setSidepanelCollapsed(collapsed) {
  sidepanelCollapsed = !!collapsed;
  if (workspace) workspace.classList.toggle('is-sidepanel-collapsed', sidepanelCollapsed);
  if (toggleSidepanelBtn) {
    toggleSidepanelBtn.textContent = sidepanelCollapsed ? '+' : '−';
    toggleSidepanelBtn.title = sidepanelCollapsed ? 'Mostrar submenú' : 'Ocultar submenú';
  }
  refreshEditorCanvas();
}

  function setSidepanelMode(mode) {
    var isBackground = mode === 'background';
    var isPages = mode === 'pages';
    if (sidepanelHead) sidepanelHead.style.display = isBackground ? 'none' : '';
    if (slideSettingsPanel) slideSettingsPanel.style.display = (isBackground || isPages) ? 'none' : '';
    if (panelTabs) panelTabs.style.display = (isBackground || isPages) ? 'none' : '';
    if (propsPanel) propsPanel.style.display = (isBackground || isPages) ? 'none' : '';
    if (!isBackground) setDefaultSidepanelCopy();
    refreshEditorCanvas();
  }

  function refreshEditorCanvas() {
    if (!editorReady || !editor) return;
    setTimeout(function () {
      try {
        var viewport = getCanvasViewport();
        injectCanvasStyles();
        paintEditorBackground(currentSlide());
        var canvas = editor.Canvas;
        var frameWrap = canvas && canvas.getFrame ? canvas.getFrame() : null;
        var frameEl = canvas && canvas.getFrameEl ? canvas.getFrameEl() : null;
        if (frameWrap && frameWrap.view && frameWrap.view.el) {
          frameWrap.view.el.style.width = viewport.widthPx;
          frameWrap.view.el.style.height = viewport.heightPx;
        }
        if (frameEl) {
          frameEl.style.width = viewport.widthPx;
          frameEl.style.height = viewport.heightPx;
        }
        if (canvas && canvas.getBody) {
          var body = canvas.getBody();
          if (body) {
            body.style.width = viewport.widthPx;
            body.style.minWidth = viewport.widthPx;
            body.style.height = viewport.heightPx;
            body.style.minHeight = viewport.heightPx;
            body.style.margin = '0';
            body.style.overflow = 'visible';
          }
        }
        fitSlideSurface();
        if (editor.refresh) editor.refresh({ tools: true });
        window.dispatchEvent(new Event('resize'));
      } catch (error) {}
    }, 60);
  }

  function fitSlideSurface() {
    if (!editor || !editor.Canvas || !stageWrap) return;
    try {
      var viewport = getCanvasViewport();
      var stage = root.querySelector('.ped-stage');
      var rect = (stage || stageWrap).getBoundingClientRect();
      var availableWidth = Math.max(320, rect.width - 80);
      var availableHeight = Math.max(180, rect.height - 80);
      var scale = Math.min(availableWidth / viewport.width, availableHeight / viewport.height);
      scale = clamp(scale, 0.25, 1);

      if (editor.Canvas.setZoom) {
        editor.Canvas.setZoom(Math.round(scale * 100));
      }

      var frameWrap = editor.Canvas.getFrame && editor.Canvas.getFrame();
      if (frameWrap && frameWrap.view && frameWrap.view.el) {
        frameWrap.view.el.style.margin = '0 auto';
      }
    } catch (error) {}
  }

  function injectCanvasStyles() {
  if (!editor || !editor.Canvas || !editor.Canvas.getDocument) return;
  try {
    var doc = editor.Canvas.getDocument();
    if (!doc || !doc.head) return;
    var styleId = 'ped-canvas-inline-styles';
    var styleNode = doc.getElementById(styleId);
    if (!styleNode) {
      styleNode = doc.createElement('style');
      styleNode.id = styleId;
      doc.head.appendChild(styleNode);
    }
    styleNode.textContent = [
      'html, body { width: 100%; min-height: 100%; margin: 0; }',
      'body { font-family: Avenir Next, Montserrat, Segoe UI, sans-serif; color: #0f172a; overflow: hidden; box-sizing: border-box; }',
      'body > * { box-sizing: border-box; }',
      'img { max-width: 100%; }',
      '.gjs-button-link { display:inline-flex; align-items:center; justify-content:center; padding:12px 22px; border-radius:999px; text-decoration:none; font-weight:700; }',
      '.gjs-card { border-radius: 24px; box-shadow: 0 20px 40px rgba(15,23,42,.12); overflow: hidden; }',
      '.gjs-hotspot { position: relative; display: inline-flex; width: 22px; height: 22px; border-radius: 999px; background: #ff8a00; box-shadow: 0 0 0 10px rgba(255,138,0,.18); }'
    ].join('\n');
  } catch (error) {}
}

  function currentSlide() {
    return slides[currentSlideIdx] || null;
  }
