/* capacitacion_presentaciones.js — Dashboard de presentaciones v20260313 */
(function () {
  'use strict';

  function el(id) { return document.getElementById(id); }
  function esc(v) {
    return String(v == null ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function toast(msg, ms) {
    var t = el('pres-toast');
    if (!t) return;
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(function () { t.classList.remove('show'); }, ms || 2500);
  }
  function getCookie(name) {
    var match = document.cookie.match(new RegExp('(?:^|; )' + name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '=([^;]*)'));
    return match ? decodeURIComponent(match[1]) : '';
  }
  function capitalizeWords(text) {
    return String(text || '')
      .toLowerCase()
      .split(/\s+/)
      .filter(Boolean)
      .map(function (part) { return part.charAt(0).toUpperCase() + part.slice(1); })
      .join(' ');
  }
  function resolveGreetingName() {
    var raw = getCookie('user_name') || getCookie('username') || getCookie('usuario') || '';
    raw = String(raw || '').trim();
    if (!raw) return '';
    if (raw.indexOf('@') !== -1) raw = raw.split('@')[0];
    raw = raw.replace(/[._-]+/g, ' ');
    return capitalizeWords(raw);
  }
  function applyGreeting() {
    var node = el('pres-greeting');
    if (!node) return;
    var name = resolveGreetingName();
    node.textContent = name ? ('Hola, ' + name + '. ¿Qué vas a crear hoy?') : 'Hola. ¿Qué vas a crear hoy?';
  }

  var grid = el('pres-grid');
  var filterSel = el('pres-filter-estado');
  var btnNew = el('pres-btn-new');
  var modal = el('pres-modal');
  var modalCancel = el('pres-modal-cancel');
  var modalCreate = el('pres-modal-create');
  var inputTitulo = el('pres-new-titulo');
  var inputDesc = el('pres-new-desc');

  var presentaciones = [];

  function apiJson(url, opts) {
    return fetch(
      url,
      Object.assign(
        { headers: { 'Content-Type': 'application/json' }, credentials: 'include' },
        opts || {}
      )
    ).then(function (r) {
      return r.text().then(function (text) {
        var data = null;
        if (text) {
          try {
            data = JSON.parse(text);
          } catch (error) {
            data = { error: text };
          }
        }
        return { ok: r.ok, status: r.status, data: data };
      });
    });
  }

  function loadingState() {
    grid.innerHTML = '<div class="pres-empty"><div class="pres-empty-icon">⏳</div><div class="pres-empty-msg">Cargando tus plantillas...</div></div>';
  }

  function errorState() {
    grid.innerHTML = '<div class="pres-empty"><div class="pres-empty-icon">⚠</div><div class="pres-empty-msg">Error al cargar.</div></div>';
  }

  function loadList() {
    var estado = filterSel ? filterSel.value : '';
    var url = '/api/capacitacion/presentaciones' + (estado ? '?estado=' + encodeURIComponent(estado) : '');
    loadingState();
    apiJson(url).then(function (res) {
      if (!res.ok) {
        errorState();
        return;
      }
      presentaciones = Array.isArray(res.data) ? res.data : [];
      renderGrid();
    }).catch(function () {
      errorState();
    });
  }

  function renderGrid() {
    if (!presentaciones.length) {
      grid.innerHTML = '<div class="pres-empty"><div class="pres-empty-icon">🗂</div><div class="pres-empty-msg">Aún no hay plantillas. Crea tu primera presentación para verla aquí.</div></div>';
      return;
    }
    grid.innerHTML = presentaciones.map(function (p) {
      var thumb = p.miniatura_url
        ? '<img src="' + esc(p.miniatura_url) + '" alt="' + esc(p.titulo || 'Miniatura de presentación') + '">'
        : '';
      var fecha = p.actualizado_en ? p.actualizado_en.split('T')[0] : '';
      var estado = esc(p.estado || 'borrador');
      var diaps = p.num_diapositivas != null ? p.num_diapositivas + ' diapositiva' + (p.num_diapositivas !== 1 ? 's' : '') : 'Sin diapositivas';
      var meta = [diaps, fecha].filter(Boolean).join(' · ');
      return [
        '<article class="pres-card">',
          '<div class="pres-card-thumb">',
            thumb,
            '<span class="pres-card-label">Plantilla</span>',
          '</div>',
          '<div class="pres-card-body">',
            '<h3 class="pres-card-name">' + esc(p.titulo || 'Sin título') + '</h3>',
            '<p class="pres-card-meta">' + esc(meta || 'Contenido en preparación') + '</p>',
          '</div>',
          '<div class="pres-card-footer">',
            '<span class="pres-badge ' + estado + '">' + estado + '</span>',
            '<div class="pres-card-actions">',
              '<button class="pres-action-btn" data-ver="' + p.id + '" type="button">Ver</button>',
              '<button class="pres-action-btn" data-edit="' + p.id + '" type="button">Editar</button>',
              '<button class="pres-action-btn danger" data-del="' + p.id + '" type="button">Eliminar</button>',
            '</div>',
          '</div>',
        '</article>'
      ].join('');
    }).join('');
  }

  grid.onclick = function (e) {
    var btn = e.target.closest('[data-ver],[data-edit],[data-del]');
    if (!btn) return;
    if (btn.dataset.ver) {
      window.location.href = '/capacitacion/presentacion/' + btn.dataset.ver + '/ver';
      return;
    }
    if (btn.dataset.edit) {
      window.location.href = '/capacitacion/presentacion/' + btn.dataset.edit + '/editor';
      return;
    }
    if (btn.dataset.del) {
      var pres = presentaciones.find(function (item) { return String(item.id) === btn.dataset.del; });
      var nombre = pres ? pres.titulo : 'esta presentación';
      if (!window.confirm('¿Eliminar "' + nombre + '"? Esta acción no se puede deshacer.')) return;
      apiJson('/api/capacitacion/presentaciones/' + btn.dataset.del, { method: 'DELETE' })
        .then(function (res) {
          if (res.ok) {
            toast('Presentación eliminada.');
            loadList();
          } else {
            toast('Error al eliminar.');
          }
        })
        .catch(function () {
          toast('Error al eliminar.');
        });
    }
  };

  btnNew.addEventListener('click', function () {
    inputTitulo.value = '';
    inputDesc.value = '';
    modal.classList.remove('hidden');
    inputTitulo.focus();
  });

  modalCancel.addEventListener('click', function () {
    modal.classList.add('hidden');
  });

  modal.addEventListener('click', function (e) {
    if (e.target === modal) modal.classList.add('hidden');
  });

  modalCreate.addEventListener('click', function () {
    var titulo = inputTitulo.value.trim();
    if (!titulo) {
      toast('Ingresa un título para la presentación.');
      inputTitulo.focus();
      return;
    }
    modalCreate.disabled = true;
    modalCreate.textContent = 'Creando...';
    apiJson('/api/capacitacion/presentaciones', {
      method: 'POST',
      body: JSON.stringify({ titulo: titulo, descripcion: inputDesc.value.trim() })
    }).then(function (res) {
      modalCreate.disabled = false;
      modalCreate.textContent = 'Crear';
      if (res.ok && res.data && res.data.id != null) {
        modal.classList.add('hidden');
        window.location.href = '/capacitacion/presentacion/' + res.data.id + '/editor';
      } else {
        toast((res.data && (res.data.error || res.data.detail)) || 'Error al crear la presentación.');
      }
    }).catch(function () {
      modalCreate.disabled = false;
      modalCreate.textContent = 'Crear';
      toast('Error al crear la presentación.');
    });
  });

  inputTitulo.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') modalCreate.click();
  });

  if (filterSel) filterSel.addEventListener('change', loadList);

  applyGreeting();
  loadList();
})();
