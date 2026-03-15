/* capacitacion_eval.js — Evaluation Player v20260309 */
(function () {
  'use strict';

  var root    = document.getElementById('ev-root');
  if (!root) return;
  var evalId  = parseInt(root.getAttribute('data-eval-id'), 10);
  var inscId  = parseInt(root.getAttribute('data-insc-id'), 10);
  if (!evalId || !inscId) {
    showStatus('Parámetros de evaluación inválidos.');
    return;
  }

  // ── Estado ─────────────────────────────────────────────────────────────────
  var evaluacion       = null;
  var inscripcion      = null;
  var intento          = null;   // respuesta de iniciar_intento
  var preguntas        = [];
  var respuestas       = {};     // { pregunta_id: opcion_id | texto }
  var activePregIdx    = 0;
  var timerInterval    = null;
  var tiempoRestante   = 0;
  var enviando         = false;

  // ── Selectores ─────────────────────────────────────────────────────────────
  function el(id) { return document.getElementById(id); }
  var mainStatus        = el('ev-main-status');
  var screenInstr       = el('ev-screen-instructions');
  var screenQuestions   = el('ev-screen-questions');
  var screenResults     = el('ev-screen-results');

  // instrucciones
  var instrCurso        = el('ev-instr-curso-nombre');
  var instrTitle        = el('ev-instr-title');
  var instrSubtitle     = el('ev-instr-subtitle');
  var instrTextWrap     = el('ev-instr-text-wrap');
  var instrText         = el('ev-instr-text');
  var metaPuntaje       = el('ev-meta-puntaje');
  var metaIntentos      = el('ev-meta-intentos');
  var metaTiempo        = el('ev-meta-tiempo');
  var metaPreguntas     = el('ev-meta-preguntas');
  var btnIniciar        = el('ev-btn-iniciar');

  // preguntas
  var qCounter          = el('ev-q-counter');
  var timerEl           = el('ev-timer');
  var timerText         = el('ev-timer-text');
  var qProgressFill     = el('ev-q-progress-fill');
  var qDots             = el('ev-q-dots');
  var qBadgeWrap        = el('ev-q-badge-wrap');
  var qEnunciado        = el('ev-q-enunciado');
  var qBody             = el('ev-q-body');
  var btnPrevQ          = el('ev-btn-prev-q');
  var btnNextQ          = el('ev-btn-next-q');
  var btnEnviar         = el('ev-btn-enviar');

  // resultados
  var scoreCircle       = el('ev-score-circle');
  var scoreNum          = el('ev-score-num');
  var resultBadge       = el('ev-result-badge');
  var resultMsg         = el('ev-result-msg');
  var resultMinMsg      = el('ev-result-min-msg');
  var certBanner        = el('ev-cert-banner');
  var certFolioText     = el('ev-cert-folio-text');
  var certLink          = el('ev-cert-link');
  var reintentarWrap    = el('ev-reintentar-wrap');
  var reintentarMsg     = el('ev-reintentar-msg');
  var reviewSection     = el('ev-review-section');
  var btnReintentar     = el('ev-btn-reintentar');
  var btnVolverCurso    = el('ev-btn-volver-curso');

  // ── Utilidades ─────────────────────────────────────────────────────────────
  function esc(v) {
    return String(v == null ? '' : v)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function showStatus(msg) {
    if (mainStatus) { mainStatus.style.display = ''; mainStatus.innerHTML = msg; }
  }
  function hideStatus() {
    if (mainStatus) mainStatus.style.display = 'none';
  }
  function hideAll() {
    [screenInstr, screenQuestions, screenResults].forEach(function (s) {
      if (s) s.style.display = 'none';
    });
  }
  function show(el) { if (el) el.style.display = ''; }

  function apiJson(url, opts) {
    return fetch(url, Object.assign({ headers: { 'Content-Type': 'application/json' } }, opts || {}))
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, status: r.status, data: d }; }); });
  }

  function formatMin(minutos) {
    if (!minutos) return 'Sin límite';
    if (minutos < 60) return minutos + ' min';
    return Math.floor(minutos / 60) + 'h ' + (minutos % 60 ? (minutos % 60) + 'min' : '');
  }

  function tipoLabel(t) {
    return { opcion_multiple: 'Opción múltiple', verdadero_falso: 'Verdadero / Falso', texto_libre: 'Respuesta libre' }[t] || t;
  }

  // ── Carga inicial ──────────────────────────────────────────────────────────
  function loadAll() {
    Promise.all([
      apiJson('/api/capacitacion/evaluaciones/' + evalId),
      apiJson('/api/capacitacion/mis-inscripciones'),
    ]).then(function (results) {
      var evalRes = results[0];
      var inscRes = results[1];

      if (!evalRes.ok) {
        showStatus('Evaluación no encontrada.');
        return;
      }
      evaluacion = evalRes.data;

      var misInscs = Array.isArray(inscRes.data) ? inscRes.data : [];
      inscripcion = misInscs.find(function (i) { return i.id === inscId; }) || null;

      hideStatus();
      renderInstructions();
    }).catch(function () {
      showStatus('Error al cargar la evaluación.');
    });
  }

  // ── Pantalla instrucciones ─────────────────────────────────────────────────
  function renderInstructions() {
    if (instrCurso) instrCurso.textContent = inscripcion && inscripcion.curso_nombre ? inscripcion.curso_nombre : '';
    if (instrTitle) instrTitle.textContent = evaluacion.titulo || 'Evaluación';
    if (instrSubtitle) instrSubtitle.textContent = 'Responde con atención.';

    if (evaluacion.instrucciones) {
      if (instrText) instrText.textContent = evaluacion.instrucciones;
      if (instrTextWrap) instrTextWrap.style.display = '';
    }

    if (metaPuntaje) metaPuntaje.textContent = (evaluacion.puntaje_minimo || 0) + '%';
    if (metaIntentos) metaIntentos.textContent = evaluacion.max_intentos || 1;
    if (metaTiempo)  metaTiempo.textContent   = formatMin(evaluacion.tiempo_limite_min);
    if (metaPreguntas) metaPreguntas.textContent = evaluacion.preguntas_por_intento || '—';

    if (btnVolverCurso && evaluacion.curso_id) {
      btnVolverCurso.href = '/capacitacion/curso/' + evaluacion.curso_id;
    }

    hideAll();
    show(screenInstr);
  }

  if (btnIniciar) {
    btnIniciar.addEventListener('click', function () {
      btnIniciar.disabled = true;
      btnIniciar.textContent = 'Iniciando…';
      apiJson('/api/capacitacion/evaluacion/iniciar', {
        method: 'POST',
        body: JSON.stringify({ inscripcion_id: inscId, evaluacion_id: evalId }),
      }).then(function (res) {
        if (!res.ok) {
          btnIniciar.disabled = false;
          btnIniciar.textContent = 'Iniciar evaluación';
          alert(res.data && res.data.detail ? res.data.detail : 'No se pudo iniciar la evaluación.');
          return;
        }
        intento  = res.data;
        preguntas = intento.preguntas || [];
        respuestas = {};
        activePregIdx = 0;
        hideAll();
        show(screenQuestions);
        if (intento.tiempo_limite_min) startTimer(intento.tiempo_limite_min);
        renderPregunta(0);
      }).catch(function () {
        btnIniciar.disabled = false;
        btnIniciar.textContent = 'Iniciar evaluación';
        alert('Error de conexión.');
      });
    });
  }

  // ── Timer ──────────────────────────────────────────────────────────────────
  function startTimer(minutos) {
    tiempoRestante = minutos * 60;
    if (timerEl) timerEl.style.display = '';
    updateTimerDisplay();
    timerInterval = setInterval(function () {
      tiempoRestante--;
      updateTimerDisplay();
      if (tiempoRestante <= 0) {
        stopTimer();
        autoEnviar();
      }
    }, 1000);
  }

  function stopTimer() {
    if (timerInterval) { clearInterval(timerInterval); timerInterval = null; }
  }

  function updateTimerDisplay() {
    if (!timerText) return;
    var m = Math.floor(tiempoRestante / 60);
    var s = tiempoRestante % 60;
    timerText.textContent = String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
    if (timerEl) {
      timerEl.classList.remove('warning', 'danger');
      if (tiempoRestante <= 60)       timerEl.classList.add('danger');
      else if (tiempoRestante <= 300) timerEl.classList.add('warning');
    }
  }

  function autoEnviar() {
    if (!enviando) enviarEvaluacion(true);
  }

  // ── Render pregunta ────────────────────────────────────────────────────────
  function renderPregunta(idx) {
    if (!preguntas.length) return;
    activePregIdx = idx;
    var p = preguntas[idx];
    var total = preguntas.length;

    // Contador y barra
    if (qCounter) qCounter.textContent = 'Pregunta ' + (idx + 1) + ' de ' + total;
    if (qProgressFill) qProgressFill.style.width = (((idx + 1) / total) * 100) + '%';

    // Dots
    renderDots();

    // Badge tipo
    if (qBadgeWrap) {
      qBadgeWrap.innerHTML = '<span class="ev-badge ' + esc(p.tipo) + '">' + tipoLabel(p.tipo) + '</span>';
    }

    // Enunciado
    if (qEnunciado) qEnunciado.textContent = p.enunciado;

    // Cuerpo
    if (qBody) {
      if (p.tipo === 'texto_libre') {
        var val = respuestas[p.id] || '';
        qBody.innerHTML = '<textarea class="ev-textarea" id="ev-textarea-' + p.id + '" placeholder="Escribe tu respuesta aquí…">' + esc(val) + '</textarea>';
        var ta = document.getElementById('ev-textarea-' + p.id);
        if (ta) {
          ta.addEventListener('input', function () {
            respuestas[p.id] = ta.value;
            renderDots();
          });
        }
      } else {
        var optsHtml = '<ul class="ev-options-list">';
        (p.opciones || []).forEach(function (op) {
          var sel = respuestas[p.id] === op.id;
          optsHtml += '<li class="ev-option' + (sel ? ' is-selected' : '') + '" data-opcion-id="' + op.id + '">' +
            '<input type="radio" name="preg_' + p.id + '" value="' + op.id + '"' + (sel ? ' checked' : '') + ' />' +
            '<span>' + esc(op.texto) + '</span>' +
          '</li>';
        });
        optsHtml += '</ul>';
        qBody.innerHTML = optsHtml;
        Array.from(qBody.querySelectorAll('.ev-option')).forEach(function (li) {
          li.addEventListener('click', function () {
            var opId = parseInt(li.getAttribute('data-opcion-id'), 10);
            respuestas[p.id] = opId;
            // Actualizar visual
            Array.from(qBody.querySelectorAll('.ev-option')).forEach(function (x) { x.classList.remove('is-selected'); });
            li.classList.add('is-selected');
            var radio = li.querySelector('input[type=radio]');
            if (radio) radio.checked = true;
            renderDots();
          });
        });
      }
    }

    // Botones nav
    if (btnPrevQ) btnPrevQ.disabled = idx === 0;
    var isLast = idx === total - 1;
    if (btnNextQ) { btnNextQ.style.display = isLast ? 'none' : ''; }
    if (btnEnviar) { btnEnviar.style.display = isLast ? '' : 'none'; }
  }

  function renderDots() {
    if (!qDots) return;
    var html = '';
    preguntas.forEach(function (p, i) {
      var answered = respuestas[p.id] !== undefined && respuestas[p.id] !== '';
      html += '<div class="ev-q-dot' + (answered ? ' is-answered' : '') + (i === activePregIdx ? ' is-current' : '') + '" data-dot-idx="' + i + '">' + (i + 1) + '</div>';
    });
    qDots.innerHTML = html;
    Array.from(qDots.querySelectorAll('[data-dot-idx]')).forEach(function (d) {
      d.addEventListener('click', function () { renderPregunta(parseInt(d.getAttribute('data-dot-idx'), 10)); });
    });
  }

  // Nav buttons
  if (btnPrevQ) btnPrevQ.addEventListener('click', function () { renderPregunta(activePregIdx - 1); });
  if (btnNextQ) btnNextQ.addEventListener('click', function () { renderPregunta(activePregIdx + 1); });

  if (btnEnviar) {
    btnEnviar.addEventListener('click', function () {
      var sinResponder = preguntas.filter(function (p) {
        return respuestas[p.id] === undefined || respuestas[p.id] === '';
      }).length;
      var confirmMsg = sinResponder > 0
        ? 'Tienes ' + sinResponder + ' pregunta(s) sin responder. ¿Deseas enviar de todas formas?'
        : '¿Confirmas el envío de tus respuestas?';
      if (!window.confirm(confirmMsg)) return;
      enviarEvaluacion(false);
    });
  }

  // ── Enviar ──────────────────────────────────────────────────────────────────
  function enviarEvaluacion(autoSubmit) {
    if (enviando || !intento) return;
    enviando = true;
    stopTimer();
    if (btnEnviar) { btnEnviar.disabled = true; btnEnviar.textContent = 'Enviando…'; }

    // Construir respuestas: string keys as required by service
    var respObj = {};
    Object.keys(respuestas).forEach(function (k) { respObj[String(k)] = respuestas[k]; });

    apiJson('/api/capacitacion/evaluacion/enviar', {
      method: 'POST',
      body: JSON.stringify({ intento_id: intento.id, respuestas: respObj }),
    }).then(function (res) {
      enviando = false;
      if (!res.ok) {
        if (btnEnviar) { btnEnviar.disabled = false; btnEnviar.textContent = '✓ Enviar evaluación'; }
        alert(res.data && res.data.detail ? res.data.detail : 'Error al enviar.');
        return;
      }
      showResults(res.data);
    }).catch(function () {
      enviando = false;
      if (btnEnviar) { btnEnviar.disabled = false; btnEnviar.textContent = '✓ Enviar evaluación'; }
      alert('Error de conexión al enviar.');
    });
  }

  // ── Resultados ──────────────────────────────────────────────────────────────
  function showResults(result) {
    hideAll();
    show(screenResults);

    var pct      = result.puntaje || 0;
    var aprobado = result.aprobado;
    var minimo   = result.puntaje_minimo_aprobacion || (evaluacion && evaluacion.puntaje_minimo) || 0;
    var cert     = result.certificado || null;

    // Círculo puntaje
    if (scoreCircle) {
      scoreCircle.className = 'ev-score-circle ' + (aprobado ? 'aprobado' : 'reprobado');
    }
    if (scoreNum) scoreNum.textContent = pct.toFixed(0) + '%';

    // Badge
    if (resultBadge) {
      resultBadge.className = 'ev-result-badge ' + (aprobado ? 'aprobado' : 'reprobado');
      resultBadge.textContent = aprobado ? '✓ Aprobado' : '✗ Reprobado';
    }

    // Mensajes
    if (resultMsg) {
      resultMsg.textContent = aprobado
        ? '¡Felicidades! Has superado la evaluación.'
        : 'No alcanzaste el puntaje mínimo requerido.';
    }
    if (resultMinMsg) {
      resultMinMsg.textContent = 'Puntaje mínimo requerido: ' + minimo + '%  ·  Tu puntaje: ' + pct.toFixed(1) + '%';
    }

    // Certificado
    if (cert && certBanner) {
      certBanner.style.display = '';
      if (certFolioText) certFolioText.textContent = 'Folio: ' + cert.folio;
      if (certLink) certLink.href = '/capacitacion/mis-certificados';
    }

    // Reintentar
    var numIntento   = intento ? intento.numero_intento : 1;
    var maxIntentos  = intento ? intento.max_intentos : (evaluacion ? evaluacion.max_intentos : 1);
    var intentosRestantes = maxIntentos - numIntento;

    if (!aprobado && intentosRestantes > 0) {
      if (reintentarWrap) reintentarWrap.style.display = '';
      if (reintentarMsg) {
        reintentarMsg.textContent = 'Te quedan ' + intentosRestantes + ' intento(s) disponible(s).';
      }
      if (btnReintentar) {
        btnReintentar.style.display = '';
        btnReintentar.onclick = function () { reintentar(); };
      }
    } else if (!aprobado && intentosRestantes <= 0) {
      if (reintentarWrap) reintentarWrap.style.display = '';
      if (reintentarMsg) reintentarMsg.textContent = 'Has agotado todos los intentos permitidos.';
    }

    // Revisión de respuestas
    renderReview();

    // Botón volver al curso
    if (btnVolverCurso && evaluacion && evaluacion.curso_id) {
      btnVolverCurso.href = '/capacitacion/curso/' + evaluacion.curso_id;
    }
  }

  function renderReview() {
    if (!reviewSection || !preguntas.length) return;
    var html = '<h4 style="font-size:15px;font-weight:700;margin:0 0 12px;">Revisión de respuestas</h4>';
    preguntas.forEach(function (p, i) {
      var respVal = respuestas[p.id];
      var respTexto = '—';
      if (p.tipo === 'texto_libre') {
        respTexto = respVal ? esc(respVal) : '<em>Sin respuesta</em>';
      } else if (respVal !== undefined) {
        var opSel = (p.opciones || []).find(function (o) { return o.id === respVal; });
        respTexto = opSel ? esc(opSel.texto) : '<em>Sin respuesta</em>';
      } else {
        respTexto = '<em>Sin respuesta</em>';
      }
      html += '<div style="padding:12px 0;border-bottom:1px solid #f1f5f9;">' +
        '<p style="font-size:13px;font-weight:600;color:#334155;margin:0 0 4px;">' + (i + 1) + '. ' + esc(p.enunciado) + '</p>' +
        '<p style="font-size:13px;color:#64748b;margin:0;">Tu respuesta: ' + respTexto + '</p>' +
      '</div>';
    });
    reviewSection.innerHTML = html;
  }

  function reintentar() {
    // Reset estado y volver a instrucciones
    intento       = null;
    preguntas     = [];
    respuestas    = {};
    activePregIdx = 0;
    stopTimer();
    if (reintentarWrap)  reintentarWrap.style.display  = 'none';
    if (certBanner)      certBanner.style.display       = 'none';
    if (btnReintentar)   btnReintentar.style.display    = 'none';
    if (reviewSection)   reviewSection.innerHTML        = '';
    if (btnIniciar)      { btnIniciar.disabled = false; btnIniciar.textContent = 'Reintentar evaluación'; }
    hideAll();
    show(screenInstr);
  }

  // ── Init ────────────────────────────────────────────────────────────────────
  loadAll();
})();
