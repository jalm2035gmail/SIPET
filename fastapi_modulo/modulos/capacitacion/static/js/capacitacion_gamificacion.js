/* capacitacion_gamificacion.js */
(function () {
  'use strict';

  function el(id) { return document.getElementById(id); }
  function esc(v) {
    return String(v == null ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function fmtFecha(iso) {
    if (!iso) return '';
    return String(iso).split('T')[0];
  }
  function apiJson(url, opts) {
    return fetch(url, Object.assign({ headers: { 'Content-Type': 'application/json' } }, opts || {}))
      .then(function (r) { return r.json().catch(function () { return null; }).then(function (d) { return { ok: r.ok, status: r.status, data: d }; }); });
  }

  var MOTIVOS = {
    leccion_completada: 'Leccion completada',
    evaluacion_aprobada: 'Evaluacion aprobada',
    evaluacion_perfecta: 'Evaluacion perfecta',
    curso_completado: 'Curso completado',
    certificado_obtenido: 'Certificado obtenido',
    constancia_diaria: 'Puntos por constancia',
    aprobado_primer_intento: 'Aprobacion al primer intento',
    abandono_curso: 'Penalizacion por abandono'
  };
  var MOTIVOS_EMOJI = {
    leccion_completada: '📖',
    evaluacion_aprobada: '✅',
    evaluacion_perfecta: '⭐',
    curso_completado: '🎓',
    certificado_obtenido: '🏅',
    constancia_diaria: '🔥',
    aprobado_primer_intento: '🥇',
    abandono_curso: '⚠️'
  };

  var profileDiv = el('gam-profile');
  var badgesDiv = el('gam-badges');
  var rankingEl = el('gam-ranking');
  var activityEl = el('gam-activity');
  var goalsEl = el('gam-goals');
  var challengesEl = el('gam-challenges');
  var rankScopeEl = el('gam-rank-scope');
  var rankValueEl = el('gam-rank-value');
  var adminWrap = el('gam-admin');
  var adminList = el('gam-badge-admin-list');
  var badgeForm = el('gam-badge-form');

  var state = { perfil: null, insignias: [], isAdmin: false };

  function renderProfile(p) {
    if (!profileDiv || !p) return;
    var pct = Math.max(0, Math.min(Number(p.pct_nivel || 0), 100));
    var proximo = p.pts_siguiente != null ? ('Faltan ' + (p.pts_siguiente - p.puntos_totales) + ' pts para ' + esc(p.nombre_siguiente)) : 'Nivel maximo alcanzado';
    var temporada = p.temporada_actual ? esc(p.temporada_actual.nombre) : 'Temporada';
    profileDiv.innerHTML =
      '<div class="gam-profile-layout">' +
        '<div class="gam-level-badge">' + esc(p.emoji || '🌱') + '</div>' +
        '<div>' +
          '<div class="gam-profile-name">' + esc(p.colaborador_key) + '</div>' +
          '<div class="gam-level-name">' + esc(p.nivel || '') + ' · ' + temporada + '</div>' +
          '<div class="gam-pts">' + esc(p.puntos_totales) + ' pts</div>' +
          '<div class="gam-lvl-bar-bg"><div class="gam-lvl-bar-fill" style="width:' + pct + '%"></div></div>' +
          '<div class="gam-lvl-info">' + esc(proximo) + '</div>' +
        '</div>' +
        '<div class="gam-profile-kpis">' +
          '<div class="gam-kpi"><div class="gam-kpi-label">Racha actual</div><div class="gam-kpi-value">' + esc(p.streak_actual || 0) + '</div></div>' +
          '<div class="gam-kpi"><div class="gam-kpi-label">Mejor racha</div><div class="gam-kpi-value">' + esc(p.streak_maximo || 0) + '</div></div>' +
          '<div class="gam-kpi"><div class="gam-kpi-label">Insignias</div><div class="gam-kpi-value">' + esc((p.insignias || []).length) + '</div></div>' +
        '</div>' +
      '</div>';
  }

  function renderBadges(todas, misMap) {
    if (!badgesDiv) return;
    if (!todas.length) {
      badgesDiv.innerHTML = '<div class="gam-status" style="grid-column:1/-1;">Sin insignias disponibles.</div>';
      return;
    }
    badgesDiv.innerHTML = todas.map(function (ins) {
      var earned = Object.prototype.hasOwnProperty.call(misMap, ins.id);
      var style = earned ? 'style="--badge-color:' + esc(ins.color || '#0f766e') + ';"' : '';
      return '<div class="gam-badge-item ' + (earned ? 'earned' : 'locked') + '" ' + style + ' title="' + esc(ins.descripcion || '') + '">' +
        '<div class="gam-badge-emoji">' + esc(ins.icono_emoji || '🏅') + '</div>' +
        '<div class="gam-badge-name">' + esc(ins.nombre) + '</div>' +
        '<div class="gam-badge-date">' + (earned ? esc(fmtFecha(misMap[ins.id])) : esc(ins.condicion_tipo + ': ' + ins.condicion_valor)) + '</div>' +
      '</div>';
    }).join('');
  }

  function renderRanking(rows) {
    if (!rankingEl) return;
    if (!rows.length) {
      rankingEl.innerHTML = '<li class="gam-status">Sin datos para este filtro.</li>';
      return;
    }
    rankingEl.innerHTML = rows.map(function (r) {
      var pos = r.posicion <= 3 ? ['🥇', '🥈', '🥉'][r.posicion - 1] : '#' + r.posicion;
      var isMe = state.perfil && r.colaborador_key === state.perfil.colaborador_key;
      var extra = r.scope_label ? (' · ' + esc(r.scope_label)) : '';
      return '<li class="gam-rank-item' + (isMe ? ' gam-rank-me' : '') + '">' +
        '<div class="gam-rank-pos">' + pos + '</div>' +
        '<div class="gam-rank-name">' + esc(r.colaborador_nombre || r.colaborador_key) + '<div class="gam-rank-meta">' + esc(r.emoji_nivel || '') + ' ' + esc(r.nivel || '') + extra + '</div></div>' +
        '<div class="gam-rank-pts">' + esc(r.puntos) + ' pts</div>' +
      '</li>';
    }).join('');
  }

  function renderActivity(actividad) {
    if (!activityEl) return;
    if (!actividad || !actividad.length) {
      activityEl.innerHTML = '<li class="gam-status">Sin actividad reciente.</li>';
      return;
    }
    activityEl.innerHTML = actividad.map(function (a) {
      var emoji = MOTIVOS_EMOJI[a.motivo] || '📌';
      var label = MOTIVOS[a.motivo] || a.motivo;
      var cls = Number(a.puntos || 0) < 0 ? 'style="color:#b91c1c;"' : 'style="color:#15803d;"';
      return '<li class="gam-activity-item">' +
        '<div class="gam-activity-icon">' + emoji + '</div>' +
        '<div class="gam-activity-motivo">' + esc(label) + '</div>' +
        '<div class="gam-activity-pts" ' + cls + '>' + (a.puntos > 0 ? '+' : '') + esc(a.puntos) + ' pts</div>' +
        '<div class="gam-activity-fecha">' + esc(fmtFecha(a.fecha)) + '</div>' +
      '</li>';
    }).join('');
  }

  function renderChallenges(items) {
    if (!challengesEl) return;
    if (!items || !items.length) {
      challengesEl.innerHTML = '<li class="gam-status">Sin retos activos.</li>';
      return;
    }
    challengesEl.innerHTML = items.map(function (item) {
      var pct = item.meta ? Math.min(100, Math.round((item.progreso / item.meta) * 100)) : 0;
      return '<li class="gam-challenge-item">' +
        '<div class="gam-challenge-body">' +
          '<div class="gam-challenge-title">' + esc(item.nombre) + '</div>' +
          '<div class="gam-goal-meta">' + esc(item.descripcion) + '</div>' +
          '<div class="gam-progress"><span style="width:' + pct + '%"></span></div>' +
          '<div class="gam-goal-meta">' + esc(item.progreso) + ' / ' + esc(item.meta) + ' · recompensa ' + esc(item.recompensa) + ' pts</div>' +
        '</div>' +
      '</li>';
    }).join('');
  }

  function renderGoals(items, statusCode) {
    if (!goalsEl) return;
    if (statusCode === 403) {
      goalsEl.innerHTML = '<li class="gam-status">Visible para administracion.</li>';
      return;
    }
    if (!items || !items.length) {
      goalsEl.innerHTML = '<li class="gam-status">Sin metas disponibles.</li>';
      return;
    }
    goalsEl.innerHTML = items.map(function (item) {
      var pct = Math.min(100, Math.round(item.avance_pct || 0));
      return '<li class="gam-goal-item">' +
        '<div class="gam-goal-body">' +
          '<div class="gam-goal-title">' + esc(item.departamento) + '</div>' +
          '<div class="gam-goal-meta">' + esc(item.completados) + ' completados de meta ' + esc(item.meta) + ' · ' + esc(item.inscritos) + ' inscritos</div>' +
          '<div class="gam-progress"><span style="width:' + pct + '%"></span></div>' +
        '</div>' +
      '</li>';
    }).join('');
  }

  function fillBadgeForm(ins) {
    el('gam-badge-id').value = ins ? ins.id : '';
    el('gam-badge-name').value = ins ? (ins.nombre || '') : '';
    el('gam-badge-desc').value = ins ? (ins.descripcion || '') : '';
    el('gam-badge-emoji').value = ins ? (ins.icono_emoji || '🏅') : '🏅';
    el('gam-badge-color').value = ins ? (ins.color || '#2563eb') : '#2563eb';
    el('gam-badge-condition').value = ins ? (ins.condicion_tipo || 'lecciones_completadas') : 'lecciones_completadas';
    el('gam-badge-target').value = ins ? (ins.condicion_valor || 1) : 1;
    el('gam-badge-order').value = ins ? (ins.orden || 0) : 0;
  }

  function renderAdminBadges() {
    if (!adminList) return;
    if (!state.isAdmin) {
      if (adminWrap) adminWrap.style.display = 'none';
      return;
    }
    if (adminWrap) adminWrap.style.display = '';
    adminList.innerHTML = (state.insignias || []).map(function (ins) {
      return '<div class="gam-badge-admin-item">' +
        '<div class="gam-badge-emoji">' + esc(ins.icono_emoji || '🏅') + '</div>' +
        '<div class="gam-badge-admin-main">' +
          '<div class="gam-badge-admin-title">' + esc(ins.nombre) + '</div>' +
          '<div class="gam-badge-admin-copy">' + esc(ins.condicion_tipo) + ' >= ' + esc(ins.condicion_valor) + ' · orden ' + esc(ins.orden) + '</div>' +
        '</div>' +
        '<button class="gam-btn" data-edit="' + esc(ins.id) + '">Editar</button>' +
        '<button class="gam-btn" data-delete="' + esc(ins.id) + '">Eliminar</button>' +
      '</div>';
    }).join('') || '<div class="gam-status">Sin insignias.</div>';
  }

  function loadRanking() {
    var params = new URLSearchParams();
    params.set('scope', rankScopeEl && rankScopeEl.value || 'empresa');
    if (rankValueEl && rankValueEl.value.trim()) params.set('value', rankValueEl.value.trim());
    params.set('season', 'actual');
    return apiJson('/api/capacitacion/gamificacion/ranking?' + params.toString()).then(function (res) {
      if (res.ok) renderRanking(Array.isArray(res.data) ? res.data : []);
    });
  }

  function loadAll() {
    Promise.all([
      apiJson('/api/capacitacion/gamificacion/perfil'),
      apiJson('/api/capacitacion/gamificacion/insignias'),
      apiJson('/api/capacitacion/gamificacion/ranking?scope=empresa&season=actual'),
      apiJson('/api/capacitacion/gamificacion/metas-departamento')
    ]).then(function (results) {
      var perfilRes = results[0];
      var insigniasRes = results[1];
      var rankingRes = results[2];
      var metasRes = results[3];
      if (!perfilRes.ok) return;
      state.perfil = perfilRes.data;
      state.insignias = insigniasRes.ok && Array.isArray(insigniasRes.data) ? insigniasRes.data : [];
      state.isAdmin = metasRes.status !== 403;
      renderProfile(state.perfil);
      var misMap = {};
      (state.perfil.insignias || []).forEach(function (ins) { misMap[ins.id] = ins.fecha_obtencion; });
      renderBadges(state.insignias, misMap);
      renderRanking(rankingRes.ok && Array.isArray(rankingRes.data) ? rankingRes.data : []);
      renderActivity(state.perfil.actividad_reciente || []);
      renderChallenges(state.perfil.retos_mensuales || []);
      renderGoals(metasRes.data, metasRes.status);
      renderAdminBadges();
      fillBadgeForm(null);
    }).catch(function () {
      if (profileDiv) profileDiv.innerHTML = '<div class="gam-status">Error al cargar.</div>';
    });
  }

  if (rankScopeEl) rankScopeEl.addEventListener('change', loadRanking);
  if (rankValueEl) rankValueEl.addEventListener('change', loadRanking);
  if (rankValueEl) rankValueEl.addEventListener('keyup', function (ev) {
    if (ev.key === 'Enter') loadRanking();
  });

  if (badgeForm) {
    badgeForm.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var id = el('gam-badge-id').value;
      var payload = {
        nombre: el('gam-badge-name').value.trim(),
        descripcion: el('gam-badge-desc').value.trim(),
        icono_emoji: el('gam-badge-emoji').value.trim() || '🏅',
        color: el('gam-badge-color').value.trim() || '#2563eb',
        condicion_tipo: el('gam-badge-condition').value,
        condicion_valor: Number(el('gam-badge-target').value || 1),
        orden: Number(el('gam-badge-order').value || 0)
      };
      var req = id
        ? apiJson('/api/capacitacion/gamificacion/insignias/' + encodeURIComponent(id), { method: 'PUT', body: JSON.stringify(payload) })
        : apiJson('/api/capacitacion/gamificacion/insignias', { method: 'POST', body: JSON.stringify(payload) });
      req.then(function (res) {
        if (!res.ok) return;
        fillBadgeForm(null);
        loadAll();
      });
    });
  }

  if (adminList) {
    adminList.addEventListener('click', function (ev) {
      var editId = ev.target && ev.target.getAttribute('data-edit');
      var deleteId = ev.target && ev.target.getAttribute('data-delete');
      if (editId) {
        var ins = (state.insignias || []).find(function (item) { return String(item.id) === String(editId); });
        fillBadgeForm(ins || null);
      }
      if (deleteId) {
        apiJson('/api/capacitacion/gamificacion/insignias/' + encodeURIComponent(deleteId), { method: 'DELETE' }).then(function (res) {
          if (res.ok) {
            fillBadgeForm(null);
            loadAll();
          }
        });
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadAll);
  } else {
    loadAll();
  }
})();
