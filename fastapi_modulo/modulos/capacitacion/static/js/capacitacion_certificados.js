/* capacitacion_certificados.js — Mis Certificados v20260309 */
(function () {
  'use strict';

  function el(id) { return document.getElementById(id); }
  function esc(v) {
    return String(v == null ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  var statusEl   = el('mcs-status');
  var gridEl     = el('mcs-grid');
  var emptyEl    = el('mcs-empty');
  var folioInput = el('mcs-folio-input');
  var btnVerif   = el('mcs-btn-verificar');
  var verifRes   = el('mcs-verify-result');

  function apiJson(url) {
    return fetch(url, { headers: { 'Content-Type': 'application/json' } })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); });
  }

  function fmtFecha(iso) {
    if (!iso) return '—';
    var d = new Date(iso);
    return d.toLocaleDateString('es-MX', { day: '2-digit', month: 'long', year: 'numeric' });
  }

  // ── Carga mis certificados ──────────────────────────────────────────────────
  function loadCertificados() {
    apiJson('/api/capacitacion/mis-certificados').then(function (res) {
      if (statusEl) statusEl.style.display = 'none';
      var certs = Array.isArray(res.data) ? res.data : [];
      if (!certs.length) {
        if (emptyEl) emptyEl.style.display = '';
        return;
      }
      if (gridEl) {
        gridEl.style.display = '';
        gridEl.innerHTML = certs.map(buildCard).join('');
      }
    }).catch(function () {
      if (statusEl) statusEl.textContent = 'Error al cargar certificados.';
    });
  }

  function buildCard(c) {
    return '<div class="mcs-cert-card">' +
      '<div class="mcs-cert-header">' +
        '<div class="mcs-cert-icon">📜</div>' +
        '<p class="mcs-cert-curso">' + esc(c.curso_nombre || 'Curso') + '</p>' +
        '<div class="mcs-cert-seal">✓</div>' +
      '</div>' +
      '<div class="mcs-cert-body">' +
        '<div class="mcs-cert-row">' +
          '<span class="mcs-cert-row-label">Colaborador</span>' +
          '<span class="mcs-cert-row-value">' + esc(c.colaborador_nombre || '—') + '</span>' +
        '</div>' +
        '<div class="mcs-cert-row">' +
          '<span class="mcs-cert-row-label">Puntaje</span>' +
          '<span class="mcs-cert-row-value mcs-puntaje">' + (c.puntaje_final != null ? c.puntaje_final.toFixed(1) + '%' : '—') + '</span>' +
        '</div>' +
        '<div class="mcs-cert-row">' +
          '<span class="mcs-cert-row-label">Fecha de emisión</span>' +
          '<span class="mcs-cert-row-value">' + esc(fmtFecha(c.fecha_emision)) + '</span>' +
        '</div>' +
        '<div class="mcs-cert-row">' +
          '<span class="mcs-cert-row-label">Folio</span>' +
          '<span class="mcs-folio-badge">' + esc(c.folio) + '</span>' +
        '</div>' +
      '</div>' +
      '<div class="mcs-cert-footer">' +
        '<a href="/capacitacion/certificado/' + c.id + '" target="_blank" class="mcs-btn is-primary">Ver certificado</a>' +
        '<a href="/capacitacion/verificar/' + esc(c.folio) + '" class="mcs-btn is-outline">Compartir</a>' +
      '</div>' +
    '</div>';
  }

  // ── Verificador ─────────────────────────────────────────────────────────────
  function verificarFolio() {
    var folio = (folioInput ? folioInput.value.trim().toUpperCase() : '');
    if (!folio) { if (verifRes) verifRes.textContent = 'Ingresa un folio.'; return; }
    if (verifRes) { verifRes.innerHTML = '<span style="color:#64748b;">Buscando…</span>'; }
    apiJson('/api/capacitacion/verificar/' + encodeURIComponent(folio)).then(function (res) {
      if (res.ok && res.data && res.data.folio) {
        if (verifRes) verifRes.innerHTML = '✅ <strong>' + esc(res.data.curso_nombre) + '</strong> — ' + esc(res.data.colaborador_nombre);
        window.location.href = '/capacitacion/verificar/' + encodeURIComponent(folio);
      } else {
        if (verifRes) verifRes.innerHTML = '<span style="color:#dc2626;">❌ Folio no encontrado.</span>';
      }
    }).catch(function () {
      if (verifRes) verifRes.innerHTML = '<span style="color:#dc2626;">Error de conexión.</span>';
    });
  }

  if (btnVerif) btnVerif.addEventListener('click', verificarFolio);
  if (folioInput) {
    folioInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') verificarFolio();
    });
  }

  loadCertificados();
})();
