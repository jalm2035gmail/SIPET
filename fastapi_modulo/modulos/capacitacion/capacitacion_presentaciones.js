/* capacitacion_presentaciones.js — Catálogo de presentaciones v20260309 */
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
    t.textContent = msg;
    t.classList.add('show');
    setTimeout(function () { t.classList.remove('show'); }, ms || 2500);
  }

  var grid      = el('pres-grid');
  var filterSel = el('pres-filter-estado');
  var btnNew    = el('pres-btn-new');
  var modal     = el('pres-modal');
  var modalCancel = el('pres-modal-cancel');
  var modalCreate = el('pres-modal-create');
  var inputTitulo = el('pres-new-titulo');
  var inputDesc   = el('pres-new-desc');

  var presentaciones = [];

  // ── API ────────────────────────────────────────────────────────────────────

  function apiJson(url, opts) {
    return fetch(url, Object.assign({ headers: { 'Content-Type': 'application/json' } }, opts || {}))
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, status: r.status, data: d }; }); });
  }

  function loadList() {
    var estado = filterSel.value;
    var url = '/api/capacitacion/presentaciones' + (estado ? '?estado=' + encodeURIComponent(estado) : '');
    grid.innerHTML = '<div class="pres-empty"><div class="pres-empty-icon">⏳</div><div class="pres-empty-msg">Cargando...</div></div>';
    apiJson(url).then(function (res) {
      if (!res.ok) { grid.innerHTML = '<div class="pres-empty"><div class="pres-empty-msg">Error al cargar.</div></div>'; return; }
      presentaciones = res.data;
      renderGrid();
    });
  }

  function renderGrid() {
    if (!presentaciones.length) {
      grid.innerHTML = '<div class="pres-empty"><div class="pres-empty-icon">📊</div><div class="pres-empty-msg">No hay presentaciones. ¡Crea la primera!</div></div>';
      return;
    }
    grid.innerHTML = presentaciones.map(function (p) {
      var thumb = p.miniatura_url
        ? '<img src="' + esc(p.miniatura_url) + '" alt="">'
        : '<span style="color:#fff;opacity:.6;">📊</span>';
      var fecha = p.actualizado_en ? p.actualizado_en.split('T')[0] : '';
      var diaps = p.num_diapositivas != null ? p.num_diapositivas + ' diapositiva' + (p.num_diapositivas !== 1 ? 's' : '') : '';
      return [
        '<div class="pres-card">',
          '<div class="pres-card-thumb">' + thumb + '</div>',
          '<div class="pres-card-body">',
            '<p class="pres-card-name">' + esc(p.titulo) + '</p>',
            '<p class="pres-card-meta">' + (diaps ? esc(diaps) + ' · ' : '') + esc(fecha) + '</p>',
          '</div>',
          '<div class="pres-card-footer">',
            '<span class="pres-badge ' + esc(p.estado) + '">' + esc(p.estado) + '</span>',
            '<div class="pres-card-actions">',
              '<button class="pres-action-btn" data-ver="' + p.id + '" title="Ver">▶ Ver</button>',
              '<button class="pres-action-btn" data-edit="' + p.id + '" title="Editar">✏ Editar</button>',
              '<button class="pres-action-btn danger" data-del="' + p.id + '" title="Eliminar">🗑</button>',
            '</div>',
          '</div>',
        '</div>'
      ].join('');
    }).join('');

    // Event delegation
    grid.onclick = function (e) {
      var btn = e.target.closest('[data-ver],[data-edit],[data-del]');
      if (!btn) return;
      if (btn.dataset.ver)  { window.location.href = '/capacitacion/presentacion/' + btn.dataset.ver + '/ver'; }
      if (btn.dataset.edit) { window.location.href = '/capacitacion/presentacion/' + btn.dataset.edit + '/editor'; }
      if (btn.dataset.del) {
        var pres = presentaciones.find(function (p) { return String(p.id) === btn.dataset.del; });
        var nombre = pres ? pres.titulo : 'esta presentación';
        if (!confirm('¿Eliminar "' + nombre + '"? Esta acción no se puede deshacer.')) return;
        apiJson('/api/capacitacion/presentaciones/' + btn.dataset.del, { method: 'DELETE' })
          .then(function (res) {
            if (res.ok) { toast('Presentación eliminada.'); loadList(); }
            else { toast('Error al eliminar.'); }
          });
      }
    };
  }

  // ── Modal crear ────────────────────────────────────────────────────────────

  btnNew.addEventListener('click', function () {
    inputTitulo.value = '';
    inputDesc.value   = '';
    modal.classList.remove('hidden');
    inputTitulo.focus();
  });

  modalCancel.addEventListener('click', function () {
    modal.classList.add('hidden');
  });

  modal.addEventListener('click', function (e) {
    if (e.target === modal) { modal.classList.add('hidden'); }
  });

  modalCreate.addEventListener('click', function () {
    var titulo = inputTitulo.value.trim();
    if (!titulo) { inputTitulo.focus(); return; }
    modalCreate.disabled = true;
    apiJson('/api/capacitacion/presentaciones', {
      method: 'POST',
      body: JSON.stringify({ titulo: titulo, descripcion: inputDesc.value.trim() })
    }).then(function (res) {
      modalCreate.disabled = false;
      if (res.ok) {
        modal.classList.add('hidden');
        window.location.href = '/capacitacion/presentacion/' + res.data.id + '/editor';
      } else {
        toast('Error al crear la presentación.');
      }
    });
  });

  inputTitulo.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') { modalCreate.click(); }
  });

  // ── Filtro ─────────────────────────────────────────────────────────────────

  filterSel.addEventListener('change', loadList);

  // ── Inicio ─────────────────────────────────────────────────────────────────

  loadList();

})();
