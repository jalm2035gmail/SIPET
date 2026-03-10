/* capacitacion_gamificacion.js — Gamificación v20260309 */
(function () {
  'use strict';

  function el(id) { return document.getElementById(id); }
  function esc(v) {
    return String(v == null ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // ── Selectores ─────────────────────────────────────────────────────────────
  var profileDiv = el('gam-profile');
  var badgesDiv  = el('gam-badges');
  var rankingEl  = el('gam-ranking');
  var activityEl = el('gam-activity');

  // ── API ─────────────────────────────────────────────────────────────────────
  function apiJson(url) {
    return fetch(url, { headers: { 'Content-Type': 'application/json' } })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); });
  }

  function fmtFecha(iso) {
    if (!iso) return '';
    return iso.split('T')[0];
  }

  // ── Textos legibles de motivos ──────────────────────────────────────────────
  var MOTIVOS = {
    leccion_completada:  'Lección completada',
    evaluacion_aprobada: 'Evaluación aprobada',
    evaluacion_perfecta: 'Evaluación perfecta',
    curso_completado:    'Curso completado',
    certificado_obtenido:'Certificado obtenido',
  };
  var MOTIVOS_EMOJI = {
    leccion_completada:  '📖',
    evaluacion_aprobada: '✅',
    evaluacion_perfecta: '⭐',
    curso_completado:    '🎓',
    certificado_obtenido:'🏅',
  };

  // ── Perfil ──────────────────────────────────────────────────────────────────
  function renderProfile(p) {
    if (!profileDiv) return;
    var pct = Math.min(p.pct_nivel || 0, 100);
    var proximo = p.pts_siguiente != null
      ? 'Faltan ' + (p.pts_siguiente - p.puntos_totales) + ' pts para ' + esc(p.nombre_siguiente)
      : 'Nivel máximo alcanzado 🎉';
    profileDiv.innerHTML =
      '<div class="gam-level-badge">' + esc(p.emoji) + '</div>' +
      '<div class="gam-profile-info">' +
        '<div class="gam-profile-name">' + esc(p.colaborador_key) + '</div>' +
        '<div class="gam-level-name">' + esc(p.nivel) + '</div>' +
        '<div class="gam-pts">' + p.puntos_totales + ' <span style="font-size:14px;font-weight:400;opacity:.8">puntos</span></div>' +
        '<div class="gam-lvl-bar-wrap">' +
          '<div class="gam-lvl-bar-bg"><div class="gam-lvl-bar-fill" style="width:' + pct + '%"></div></div>' +
          '<div class="gam-lvl-info">' + esc(proximo) + '</div>' +
        '</div>' +
      '</div>' +
      '<div style="text-align:center;">' +
        '<div style="font-size:36px;">' + (p.insignias ? p.insignias.length : 0) + '</div>' +
        '<div style="font-size:12px;opacity:.8;">insignias</div>' +
      '</div>';
  }

  // ── Insignias ───────────────────────────────────────────────────────────────
  function renderBadges(todas, mis_ids) {
    if (!badgesDiv) return;
    if (!todas.length) {
      badgesDiv.innerHTML = '<p style="color:#94a3b8;font-size:13px;grid-column:1/-1;">Sin insignias disponibles.</p>';
      return;
    }
    badgesDiv.innerHTML = todas.map(function (ins) {
      var earned = mis_ids.hasOwnProperty(ins.id);
      var fechaTxt = earned ? fmtFecha(mis_ids[ins.id]) : '';
      var cls = 'gam-badge-item' + (earned ? ' earned' : ' locked');
      var style = earned ? 'style="--badge-color:' + esc(ins.color || '#6366f1') + ';"' : '';
      return '<div class="' + cls + '" ' + style + ' title="' + esc(ins.descripcion || '') + '">' +
        '<span class="gam-badge-emoji">' + esc(ins.icono_emoji || '🏅') + '</span>' +
        '<span class="gam-badge-name">' + esc(ins.nombre) + '</span>' +
        (fechaTxt ? '<span class="gam-badge-date">' + fechaTxt + '</span>' : '') +
      '</div>';
    }).join('');
  }

  // ── Ranking ─────────────────────────────────────────────────────────────────
  function renderRanking(rows, miKey) {
    if (!rankingEl) return;
    if (!rows.length) {
      rankingEl.innerHTML = '<li style="color:#94a3b8;font-size:13px;padding:16px 0;">Sin datos de ranking todavía.</li>';
      return;
    }
    rankingEl.innerHTML = rows.map(function (r) {
      var posClass = r.posicion === 1 ? 'top1' : r.posicion === 2 ? 'top2' : r.posicion === 3 ? 'top3' : '';
      var posTxt = r.posicion === 1 ? '🥇' : r.posicion === 2 ? '🥈' : r.posicion === 3 ? '🥉' : '#' + r.posicion;
      var isMe = r.colaborador_key === miKey;
      return '<li class="gam-rank-item' + (isMe ? ' gam-rank-me' : '') + '">' +
        '<span class="gam-rank-pos ' + posClass + '">' + posTxt + '</span>' +
        '<span class="gam-rank-name">' + esc(r.colaborador_nombre || r.colaborador_key) + '</span>' +
        '<span class="gam-rank-level">' + esc(r.emoji_nivel) + ' ' + esc(r.nivel) + '</span>' +
        '<span class="gam-rank-pts">' + r.puntos + ' pts</span>' +
        '<span class="gam-rank-badges">🏅 ' + r.num_insignias + '</span>' +
      '</li>';
    }).join('');
  }

  // ── Actividad ───────────────────────────────────────────────────────────────
  function renderActivity(actividad) {
    if (!activityEl) return;
    if (!actividad || !actividad.length) {
      activityEl.innerHTML = '<li style="color:#94a3b8;font-size:13px;padding:16px 0;">Sin actividad reciente todavía.</li>';
      return;
    }
    activityEl.innerHTML = actividad.map(function (a) {
      var emoji = MOTIVOS_EMOJI[a.motivo] || '📌';
      var label = MOTIVOS[a.motivo] || a.motivo;
      return '<li class="gam-activity-item">' +
        '<div class="gam-activity-icon">' + emoji + '</div>' +
        '<span class="gam-activity-motivo">' + esc(label) + '</span>' +
        '<span class="gam-activity-pts">+' + a.puntos + ' pts</span>' +
        '<span class="gam-activity-fecha">' + esc(fmtFecha(a.fecha)) + '</span>' +
      '</li>';
    }).join('');
  }

  // ── Init ────────────────────────────────────────────────────────────────────
  function init() {
    Promise.all([
      apiJson('/api/capacitacion/gamificacion/perfil'),
      apiJson('/api/capacitacion/gamificacion/ranking'),
      apiJson('/api/capacitacion/gamificacion/insignias'),
    ]).then(function (results) {
      var perfil   = results[0].ok ? results[0].data : null;
      var ranking  = results[1].ok ? results[1].data : [];
      var todas    = results[2].ok ? results[2].data : [];

      if (perfil) {
        renderProfile(perfil);
        // Build mis insignias lookup: {id: fecha_obtencion}
        var misMap = {};
        (perfil.insignias || []).forEach(function (ins) { misMap[ins.id] = ins.fecha_obtencion; });
        renderBadges(todas, misMap);
        renderActivity(perfil.actividad_reciente || []);
        renderRanking(Array.isArray(ranking) ? ranking : [], perfil.colaborador_key);
      } else {
        if (profileDiv) profileDiv.innerHTML = '<p style="color:#fca5a5;">Error al cargar perfil.</p>';
      }
    }).catch(function () {
      if (profileDiv) profileDiv.innerHTML = '<p style="color:#fca5a5;">Error al conectar con el servidor.</p>';
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
