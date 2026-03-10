/* capacitacion_verificar.js — Verificación de Certificados v20260309 */
(function () {
  'use strict';

  function el(id) { return document.getElementById(id); }
  function esc(v) {
    return String(v == null ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  var root        = el('vf-root');
  var folioInput  = el('vf-folio-input');
  var btnBuscar   = el('vf-btn-buscar');
  var statusEl    = el('vf-status');
  var resultEl    = el('vf-result');
  var notFoundEl  = el('vf-not-found');

  function fmtFecha(iso) {
    if (!iso) return '—';
    var d = new Date(iso);
    return d.toLocaleDateString('es-MX', { day: '2-digit', month: 'long', year: 'numeric' });
  }

  function hideAll() {
    if (statusEl)   statusEl.style.display   = 'none';
    if (resultEl)   resultEl.style.display   = 'none';
    if (notFoundEl) notFoundEl.style.display = 'none';
  }

  function verificar(folio) {
    folio = folio.trim().toUpperCase();
    if (!folio) return;
    if (folioInput) folioInput.value = folio;
    hideAll();
    if (statusEl) statusEl.style.display = '';

    fetch('/api/capacitacion/verificar/' + encodeURIComponent(folio), {
      headers: { 'Content-Type': 'application/json' },
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
      .then(function (res) {
        if (statusEl) statusEl.style.display = 'none';
        if (res.ok && res.data && res.data.folio) {
          renderResult(res.data);
        } else {
          if (notFoundEl) notFoundEl.style.display = '';
        }
      })
      .catch(function () {
        if (statusEl) statusEl.style.display = 'none';
        if (notFoundEl) {
          notFoundEl.style.display = '';
          notFoundEl.querySelector('.vf-not-found').innerHTML = '<strong>Error de conexión.</strong> Intenta nuevamente.';
        }
      });
  }

  function renderResult(c) {
    if (!resultEl) return;
    resultEl.style.display = '';

    var sub = el('vf-result-subtitle');
    var nom = el('vf-r-nombre');
    var cur = el('vf-r-curso');
    var pun = el('vf-r-puntaje');
    var fec = el('vf-r-fecha');
    var fol = el('vf-r-folio');
    var lnk = el('vf-link-cert');

    if (sub) sub.textContent = 'Emitido en ' + fmtFecha(c.fecha_emision);
    if (nom) nom.textContent = c.colaborador_nombre || '—';
    if (cur) cur.textContent = c.curso_nombre || '—';
    if (pun) pun.textContent = c.puntaje_final != null ? c.puntaje_final.toFixed(1) + '%' : '—';
    if (fec) fec.textContent = fmtFecha(c.fecha_emision);
    if (fol) fol.textContent = c.folio;
    if (lnk) lnk.href = '/capacitacion/certificado/' + c.id;
  }

  if (btnBuscar) {
    btnBuscar.addEventListener('click', function () {
      verificar(folioInput ? folioInput.value : '');
    });
  }
  if (folioInput) {
    folioInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') verificar(folioInput.value);
    });
  }

  // Auto-verificar si hay folio en la URL
  var folioFromUrl = root && root.getAttribute('data-folio');
  if (folioFromUrl) verificar(folioFromUrl);
})();
