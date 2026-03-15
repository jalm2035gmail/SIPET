  function htmlBlock(content) {
    return '<section style="padding:48px 56px;"><h1 style="margin:0 0 12px;font-size:42px;line-height:1.05;">' +
      esc(content.title || 'Título potente') +
      '</h1><p style="margin:0;font-size:18px;line-height:1.6;color:#475569;">' +
      esc(content.text || 'Construye una narrativa visual con bloques editables, medios y llamadas a la acción.') +
      '</p></section>';
  }
  function featureCardBlock() {
    return '<section style="padding:40px 48px;"><div class="gjs-card" style="padding:30px;background:linear-gradient(180deg,#ffffff,#f7f4ef);border:1px solid rgba(15,23,42,.08);"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.16em;color:#64748b;margin-bottom:10px;">Bloque visual</div><h3 style="margin:0 0 10px;font-size:34px;line-height:1.05;color:#1f2937;">Integra una idea con énfasis</h3><p style="margin:0;font-size:17px;line-height:1.7;color:#475569;">Usa este contenedor para beneficios, pasos o llamadas a la acción con un estilo más editorial.</p></div></section>';
  }
  function styledButtonBlock() {
    return '<section style="padding:40px 52px;"><div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap;"><a class="gjs-button-link" href="#" style="background:#4f46e5;color:#ffffff;box-shadow:0 16px 30px rgba(79,70,229,.24);">Botón principal</a><a class="gjs-button-link" href="#" style="background:#ffffff;color:#1f2937;border:1px solid rgba(15,23,42,.12);">Botón secundario</a></div></section>';
  }
  function backgroundFrameBlock() {
    return '<section style="padding:54px 56px;background:linear-gradient(135deg,#476f16 0%,#3e6d12 62%,#c79f66 100%);color:#ffffff;position:relative;overflow:hidden;"><div style="position:absolute;right:-70px;bottom:-90px;width:320px;height:320px;border-radius:50%;background:rgba(255,255,255,.18);"></div><div style="position:relative;max-width:560px;"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.18em;font-weight:800;margin-bottom:18px;opacity:.72;">Portada</div><h2 style="margin:0 0 16px;font-size:52px;line-height:.94;">Fondo y composición</h2><p style="margin:0;font-size:18px;line-height:1.65;color:rgba(255,255,255,.86);">Inserta una slide con atmósfera visual para abrir secciones, reforzar mensajes o presentar un cambio.</p></div></section>';
  }
  function insertResource(kind) {
    var content = '';
    if (kind === 'image-upload' || kind === 'image-laptop') {
      content = '<section style="padding:32px 42px;"><img src="https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=1200&q=80" alt="" style="width:100%;border-radius:24px;display:block;min-height:320px;object-fit:cover;"></section>';
    } else if (kind === 'image-training') {
      content = '<section style="padding:32px 42px;"><img src="https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=1200&q=80" alt="" style="width:100%;border-radius:24px;display:block;min-height:320px;object-fit:cover;"></section>';
    } else if (kind === 'image-cat') {
      content = '<section style="padding:32px 42px;"><img src="https://images.unsplash.com/photo-1518791841217-8f162f1e1131?auto=format&fit=crop&w=1200&q=80" alt="" style="width:100%;border-radius:24px;display:block;min-height:320px;object-fit:cover;"></section>';
    } else if (kind === 'image-ai') {
      content = '<section style="padding:42px 52px;"><div class="gjs-card" style="padding:30px;background:linear-gradient(135deg,#f9f7ff,#efe8ff);border:1px solid rgba(106,52,255,.12);"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.18em;color:#6a34ff;margin-bottom:12px;">Imagen con IA</div><h3 style="margin:0 0 10px;font-size:30px;color:#241f41;">Prompt visual sugerido</h3><p style="margin:0;font-size:16px;line-height:1.65;color:#4b5563;">Inserta aquí una imagen generada con IA para reforzar la narrativa visual de esta diapositiva.</p></div></section>';
    } else if (kind === 'shape-square') {
      content = '<div style="padding:42px 56px;"><div style="width:180px;height:180px;background:#111827;border-radius:24px;"></div></div>';
    } else if (kind === 'shape-circle') {
      content = '<div style="padding:42px 56px;"><div style="width:180px;height:180px;background:#111827;border-radius:999px;"></div></div>';
    } else if (kind === 'shape-line') {
      content = '<div style="padding:54px 56px;"><div style="width:220px;height:6px;background:#111827;border-radius:999px;position:relative;"><span style="position:absolute;right:-10px;top:-7px;font-size:28px;">→</span></div></div>';
    } else if (kind === 'shape-cat') {
      content = '<div style="padding:42px 56px;font-size:110px;line-height:1;">🐈</div>';
    } else if (kind === 'icon-touch' || kind === 'icon-chart' || kind === 'icon-team' || kind === 'icon-burst') {
      var icons = { 'icon-touch': '☝', 'icon-chart': '◔', 'icon-team': '☺', 'icon-burst': '✺' };
      content = '<div style="padding:42px 56px;font-size:96px;line-height:1;color:#111827;">' + icons[kind] + '</div>';
    } else if (kind === 'illus-folder' || kind === 'illus-cassette' || kind === 'illus-rocket' || kind === 'illus-trophy') {
      var illus = { 'illus-folder': '📁', 'illus-cassette': '📼', 'illus-rocket': '🚀', 'illus-trophy': '🏆' };
      content = '<div style="padding:42px 56px;font-size:96px;line-height:1;">' + illus[kind] + '</div>';
    } else if (kind === 'char-1' || kind === 'char-2' || kind === 'char-3' || kind === 'char-4') {
      var chars = { 'char-1': '🧑', 'char-2': '👩', 'char-3': '🧑‍💼', 'char-4': '🧔' };
      content = '<div style="padding:42px 56px;font-size:92px;line-height:1;">' + chars[kind] + '</div>';
    } else if (kind === 'chart-bars') {
      content = '<section style="padding:40px 48px;"><div class="gjs-card" style="padding:28px;background:#ffffff;"><div style="display:flex;align-items:flex-end;gap:18px;height:220px;"><span style="width:64px;height:120px;background:#476f16;border-radius:18px 18px 0 0;"></span><span style="width:64px;height:170px;background:#c79f66;border-radius:18px 18px 0 0;"></span><span style="width:64px;height:90px;background:#1f2937;border-radius:18px 18px 0 0;"></span></div></div></section>';
    } else if (kind === 'chart-line') {
      content = '<section style="padding:40px 48px;"><div class="gjs-card" style="padding:28px;background:#ffffff;"><svg viewBox="0 0 420 180" style="width:100%;height:auto;display:block;"><polyline fill="none" stroke="#6a34ff" stroke-width="8" points="10,150 90,120 170,132 250,70 330,92 410,36"></polyline></svg></div></section>';
    } else if (kind === 'chart-pie') {
      content = '<section style="padding:40px 48px;"><div class="gjs-card" style="padding:28px;background:#ffffff;display:flex;justify-content:center;"><div style="width:220px;height:220px;border-radius:50%;background:conic-gradient(#476f16 0 42%, #c79f66 42% 74%, #111827 74% 100%);"></div></div></section>';
    } else if (kind === 'chart-kpi') {
      content = '<section style="padding:40px 48px;"><div class="gjs-card" style="padding:28px;background:#111827;color:#ffffff;"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.16em;opacity:.7;margin-bottom:10px;">KPI principal</div><div style="font-size:72px;font-weight:800;line-height:1;">87%</div><p style="margin:10px 0 0;font-size:17px;line-height:1.6;color:rgba(255,255,255,.74);">Avance de adopción sobre la iniciativa prioritaria.</p></div></section>';
    } else if (kind === 'comp-hero') {
      content = backgroundFrameBlock();
    } else if (kind === 'comp-quote') {
      content = '<section style="padding:42px 52px;"><div class="gjs-card" style="padding:34px;background:#ffffff;border-left:8px solid #6a34ff;"><div style="font-size:72px;line-height:.8;color:#c4b5fd;">“</div><p style="margin:0;font-size:28px;line-height:1.35;color:#1f2937;">El cambio no es una amenaza, es la dinámica que impulsa el crecimiento.</p></div></section>';
    } else if (kind === 'comp-timeline') {
      content = '<section style="padding:42px 52px;"><div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;"><div class="gjs-card" style="padding:22px;background:#ffffff;"><strong>1. Diagnóstico</strong><p style="margin:8px 0 0;color:#475569;">Identifica el contexto actual.</p></div><div class="gjs-card" style="padding:22px;background:#ffffff;"><strong>2. Acción</strong><p style="margin:8px 0 0;color:#475569;">Activa el cambio con claridad.</p></div><div class="gjs-card" style="padding:22px;background:#ffffff;"><strong>3. Seguimiento</strong><p style="margin:8px 0 0;color:#475569;">Mide impacto y aprendizajes.</p></div></div></section>';
    } else if (kind === 'comp-highlight') {
      content = featureCardBlock();
    }
    if (!content) return;
    editor.addComponents(content);
  }
  function setResourcePanelVisible(show) {
    if (!resourcePanel) return;
    resourcePanel.classList.toggle('is-active', !!show);
  }
  function insertTextPreset(kind) {
    var content = '';
    if (kind === 'title-1') {
      content = '<section style="padding:44px 56px 18px;"><h1 style="margin:0;font-size:62px;line-height:.95;font-weight:800;color:#111827;">Título 1</h1></section>';
    } else if (kind === 'title-2') {
      content = '<section style="padding:36px 56px 16px;"><h2 style="margin:0;font-size:46px;line-height:1;font-weight:800;color:#111827;">Título 2</h2></section>';
    } else if (kind === 'subtitle') {
      content = '<section style="padding:28px 56px 12px;"><h3 style="margin:0;font-size:30px;line-height:1.12;font-weight:500;color:#111827;">Subtítulo</h3></section>';
    } else if (kind === 'paragraph') {
      content = '<section style="padding:28px 56px 12px;"><p style="margin:0;max-width:720px;font-size:22px;line-height:1.55;color:#1f2937;">Esto es un párrafo listo para contener creatividad, experiencias e historias geniales.</p></section>';
    } else if (kind === 'bullets') {
      content = '<section style="padding:28px 56px 12px;"><ul style="margin:0;padding-left:28px;font-size:22px;line-height:1.7;color:#111827;"><li>Listado de puntos</li><li>Listado de puntos</li></ul></section>';
    } else if (kind === 'ordered') {
      content = '<section style="padding:28px 56px 12px;"><ol style="margin:0;padding-left:30px;font-size:22px;line-height:1.7;color:#111827;"><li>Listado ordenado</li><li>Listado ordenado</li></ol></section>';
    } else if (kind === 'brand-typography') {
      content = '<section style="padding:42px 56px;"><div class="gjs-card" style="padding:28px;background:#ffffff;"><div style="font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:#6b7280;margin-bottom:14px;">Contextualiza tu tema</div><div style="display:grid;grid-template-columns:1.1fr .9fr;gap:24px;align-items:end;"><div style="font-size:48px;line-height:.96;font-weight:500;color:#111827;">ESCRIBE UN<br>TITULAR GENIAL</div><div><div style="font-size:28px;line-height:1.05;font-weight:700;color:#111827;">UN TÍTULO GENIAL</div><div style="margin-top:10px;font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:#6b7280;">Contextualiza tu tema</div></div></div></div></section>';
    }
    if (!content) return;
    editor.addComponents(content);
  }
  function setTextPanelVisible(show) {
    if (!textPanel) return;
    textPanel.classList.toggle('is-active', !!show);
  }
  function insertInteractivePreset(kind) {
    var content = '';
    if (kind === 'content-window') {
      content = '<section style="padding:40px 56px;"><div class="gjs-card" style="padding:24px;background:#ffffff;border:1px solid rgba(99,102,241,.18);"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.16em;color:#64748b;margin-bottom:10px;">Ventana</div><h3 style="margin:0 0 8px;font-size:28px;color:#111827;">Contenido desplegable</h3><p style="margin:0;font-size:16px;line-height:1.6;color:#475569;">Usa esta ventana para ampliar información sin saturar la diapositiva principal.</p></div></section>';
    } else if (kind === 'content-label') {
      content = '<div style="padding:34px 56px;"><span style="display:inline-flex;padding:10px 16px;border-radius:999px;background:#eef2ff;color:#4338ca;font-size:14px;font-weight:800;">Etiqueta interactiva</span></div>';
    } else if (kind === 'content-audio') {
      content = '<div style="padding:34px 56px;"><button style="display:inline-flex;align-items:center;gap:10px;border:0;border-radius:999px;padding:16px 22px;background:#111827;color:#ffffff;font-size:16px;font-weight:800;box-shadow:0 16px 26px rgba(17,24,39,.18);">🔊 Dar clic para escuchar el audio</button></div>';
    } else if (kind === 'nav-link') {
      content = '<div style="padding:34px 56px;"><a class="gjs-button-link" href="https://www.avancoop.com" style="background:#ffffff;color:#111827;border:1px solid rgba(15,23,42,.12);">Abrir enlace</a></div>';
    } else if (kind === 'nav-page') {
      content = '<div style="padding:34px 56px;"><a class="gjs-button-link" href="#siguiente" style="background:#ede9fe;color:#5b21b6;">Ir a página</a></div>';
    } else if (kind === 'sticker-party' || kind === 'sticker-clap' || kind === 'sticker-pin') {
      var stickers = { 'sticker-party': '🎉', 'sticker-clap': '👏', 'sticker-pin': '📌' };
      content = '<div style="padding:38px 56px;font-size:82px;line-height:1;filter:drop-shadow(0 14px 22px rgba(15,23,42,.12));">' + stickers[kind] + '</div>';
    } else if (kind === 'button-primary') {
      content = '<div style="padding:34px 56px;"><a class="gjs-button-link" href="#" style="background:#6a34ff;color:#ffffff;box-shadow:0 18px 28px rgba(106,52,255,.26);">Botón principal</a></div>';
    } else if (kind === 'button-secondary') {
      content = '<div style="padding:34px 56px;"><a class="gjs-button-link" href="#" style="background:#ffffff;color:#111827;border:1px solid rgba(15,23,42,.12);">Botón secundario</a></div>';
    } else if (kind === 'button-icon') {
      content = '<div style="padding:34px 56px;"><a class="gjs-button-link" href="#" style="background:#111827;color:#ffffff;">Continuar ➜</a></div>';
    } else if (kind === 'interactive-area') {
      content = '<div style="padding:34px 56px;"><div style="min-height:180px;border:2px dashed rgba(106,52,255,.42);border-radius:24px;background:rgba(106,52,255,.06);display:flex;align-items:center;justify-content:center;color:#6a34ff;font-size:18px;font-weight:800;">Área interactiva</div></div>';
    }
    if (!content) return;
    editor.addComponents(content);
  }
  function setInteractivePanelVisible(show) {
    if (!interactivePanel) return;
    interactivePanel.classList.toggle('is-active', !!show);
  }
  function insertQuestionPreset(kind) {
    var firstSurvey = liveSurveys[0];
    var surveyId = firstSurvey ? String(firstSurvey.id) : '';
    var content = '';
    if (kind === 'quiz-single') {
      content = '<section style="padding:34px 44px;"><div class="gjs-card" style="padding:28px;background:#ffffff;"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.16em;color:#6b7280;margin-bottom:10px;">Elección única</div><h3 style="margin:0 0 14px;font-size:28px;color:#111827;">Selecciona una opción correcta</h3><div style="display:grid;gap:10px;"><label style="display:flex;gap:10px;align-items:center;padding:14px 16px;border-radius:16px;background:#f8fafc;"><input type="radio" name="quiz-single" checked> Opción A</label><label style="display:flex;gap:10px;align-items:center;padding:14px 16px;border-radius:16px;background:#f8fafc;"><input type="radio" name="quiz-single"> Opción B</label><label style="display:flex;gap:10px;align-items:center;padding:14px 16px;border-radius:16px;background:#f8fafc;"><input type="radio" name="quiz-single"> Opción C</label></div></div></section>';
    } else if (kind === 'quiz-multi') {
      content = '<section style="padding:34px 44px;"><div class="gjs-card" style="padding:28px;background:#ffffff;"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.16em;color:#6b7280;margin-bottom:10px;">Elección múltiple</div><h3 style="margin:0 0 14px;font-size:28px;color:#111827;">Selecciona varias respuestas</h3><div style="display:grid;gap:10px;"><label style="display:flex;gap:10px;align-items:center;padding:14px 16px;border-radius:16px;background:#f8fafc;"><input type="checkbox" checked> Respuesta 1</label><label style="display:flex;gap:10px;align-items:center;padding:14px 16px;border-radius:16px;background:#f8fafc;"><input type="checkbox"> Respuesta 2</label><label style="display:flex;gap:10px;align-items:center;padding:14px 16px;border-radius:16px;background:#f8fafc;"><input type="checkbox"> Respuesta 3</label></div></div></section>';
    } else if (kind === 'quiz-boolean') {
      content = '<section style="padding:34px 44px;"><div class="gjs-card" style="padding:28px;background:#ffffff;text-align:center;"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.16em;color:#6b7280;margin-bottom:10px;">Verdadero o falso</div><h3 style="margin:0 0 18px;font-size:28px;color:#111827;">El cambio puede convertirse en una ventaja competitiva.</h3><div style="display:flex;gap:14px;justify-content:center;"><button style="border:0;border-radius:999px;padding:14px 24px;background:#16a34a;color:#fff;font-weight:800;">Verdadero</button><button style="border:0;border-radius:999px;padding:14px 24px;background:#ef4444;color:#fff;font-weight:800;">Falso</button></div></div></section>';
    } else if (kind === 'quiz-image') {
      content = '<section style="padding:34px 44px;"><div class="gjs-card" style="padding:28px;background:#ffffff;"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.16em;color:#6b7280;margin-bottom:10px;">Elección de imagen</div><h3 style="margin:0 0 16px;font-size:28px;color:#111827;">¿Qué imagen representa mejor la adaptación?</h3><div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;"><div style="border-radius:18px;overflow:hidden;background:#eef2ff;min-height:140px;"></div><div style="border-radius:18px;overflow:hidden;background:#fef3c7;min-height:140px;"></div><div style="border-radius:18px;overflow:hidden;background:#dcfce7;min-height:140px;"></div></div></div></section>';
    } else if (kind === 'quiz-order') {
      content = '<section style="padding:34px 44px;"><div class="gjs-card" style="padding:28px;background:#ffffff;"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.16em;color:#6b7280;margin-bottom:10px;">Ordenar</div><h3 style="margin:0 0 14px;font-size:28px;color:#111827;">Ordena los pasos del cambio</h3><div style="display:grid;gap:10px;"><div style="padding:14px 16px;border-radius:16px;background:#f8fafc;">1. Diagnóstico</div><div style="padding:14px 16px;border-radius:16px;background:#f8fafc;">2. Implementación</div><div style="padding:14px 16px;border-radius:16px;background:#f8fafc;">3. Seguimiento</div></div></div></section>';
    } else if (kind === 'quiz-fill') {
      content = '<section style="padding:34px 44px;"><div class="gjs-card" style="padding:28px;background:#ffffff;"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.16em;color:#6b7280;margin-bottom:10px;">Completar huecos</div><h3 style="margin:0 0 14px;font-size:28px;color:#111827;">Adaptarse es <span style="display:inline-block;min-width:120px;border-bottom:3px solid #6a34ff;">&nbsp;</span>.</h3></div></section>';
    } else if (kind === 'quiz-short') {
      content = '<section style="padding:34px 44px;"><div class="gjs-card" style="padding:28px;background:#ffffff;"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.16em;color:#6b7280;margin-bottom:10px;">Respuesta corta</div><h3 style="margin:0 0 14px;font-size:28px;color:#111827;">Describe una acción concreta para facilitar el cambio.</h3><div style="padding:14px 16px;border-radius:16px;background:#f8fafc;color:#94a3b8;">Escribe tu respuesta...</div></div></section>';
    } else if (kind === 'branching') {
      content = '<section style="padding:34px 44px;"><div class="gjs-card" style="padding:28px;background:#111827;color:#ffffff;"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.16em;opacity:.7;margin-bottom:10px;">Multicamino</div><h3 style="margin:0 0 14px;font-size:28px;">Punto de decisión</h3><p style="margin:0 0 16px;color:rgba(255,255,255,.78);font-size:16px;line-height:1.6;">Define dos rutas posibles según la respuesta del participante.</p><div style="display:flex;gap:12px;flex-wrap:wrap;"><span style="padding:12px 18px;border-radius:999px;background:#6a34ff;">Ruta A</span><span style="padding:12px 18px;border-radius:999px;background:#374151;">Ruta B</span></div></div></section>';
    } else if (kind === 'open-answer') {
      content = '<section style="padding:34px 44px;"><div class="gjs-card" style="padding:28px;background:#ffffff;border:1px solid rgba(240,201,75,.42);"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.16em;color:#9a7b00;margin-bottom:10px;">Respuesta abierta</div><p style="margin:0;font-size:16px;line-height:1.6;color:#475569;">Usa este bloque para recoger reflexiones abiertas del participante.</p></div></section>';
    } else if (kind === 'survey-mentimeter') {
      if (surveyId) {
        editor.addComponents('<div class="cap-live-survey-widget" data-survey-id="' + surveyId + '" data-widget-mode="card" data-button-label="Responder encuesta" style="padding:0;"></div>');
        return;
      }
      content = '<section style="padding:34px 44px;"><div class="gjs-card" style="padding:28px;background:#ffffff;border:1px dashed #cbd5e1;"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.16em;color:#6b7280;margin-bottom:10px;">Encuesta</div><p style="margin:0;font-size:16px;line-height:1.6;color:#475569;">Vincula una encuesta live del curso para usar preguntas tipo Mentimeter en esta slide.</p></div></section>';
    } else if (kind === 'survey-image') {
      content = '<section style="padding:34px 44px;"><div class="gjs-card" style="padding:28px;background:#ffffff;border:1px solid rgba(240,201,75,.42);"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.16em;color:#9a7b00;margin-bottom:10px;">Encuesta con imagen</div><p style="margin:0;font-size:16px;line-height:1.6;color:#475569;">Usa una encuesta ilustrada para comparar respuestas visuales o seleccionar imágenes.</p></div></section>';
    }
    if (!content) return;
    editor.addComponents(content);
  }
  function setQuestionsPanelVisible(show) {
    if (!questionsPanel) return;
    questionsPanel.classList.toggle('is-active', !!show);
  }
  function insertWidgetPreset(kind) {
    var content = '';
    if (kind === 'gallery-carousel') {
      content = '<section style="padding:34px 44px;"><div class="gjs-card" style="padding:22px;background:#ffffff;"><div style="display:grid;grid-template-columns:1.2fr .8fr .8fr;gap:12px;"><div style="min-height:220px;border-radius:20px;background:#cbd5e1;"></div><div style="display:grid;gap:12px;"><div style="min-height:104px;border-radius:18px;background:#e2e8f0;"></div><div style="min-height:104px;border-radius:18px;background:#dbeafe;"></div></div><div style="display:grid;gap:12px;"><div style="min-height:104px;border-radius:18px;background:#fef3c7;"></div><div style="min-height:104px;border-radius:18px;background:#dcfce7;"></div></div></div></div></section>';
    } else if (kind === 'gallery-mosaic') {
      content = '<section style="padding:34px 44px;"><div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;"><div class="gjs-card" style="min-height:140px;background:#dbeafe;"></div><div class="gjs-card" style="min-height:140px;background:#fce7f3;"></div><div class="gjs-card" style="min-height:140px;background:#dcfce7;"></div><div class="gjs-card" style="min-height:140px;background:#fef3c7;"></div><div class="gjs-card" style="min-height:140px;background:#ede9fe;"></div><div class="gjs-card" style="min-height:140px;background:#e2e8f0;"></div></div></section>';
    } else if (kind === 'gallery-compare') {
      content = '<section style="padding:34px 44px;"><div class="gjs-card" style="overflow:hidden;background:#ffffff;"><div style="display:grid;grid-template-columns:1fr 1fr;"><div style="min-height:260px;background:#dbeafe;display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:700;">Antes</div><div style="min-height:260px;background:#dcfce7;display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:700;">Después</div></div></div></section>';
    } else if (kind === 'gallery-cards') {
      content = '<section style="padding:34px 44px;"><div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;"><article class="gjs-card" style="padding:22px;background:#ffffff;"><strong>Tarjeta 1</strong><p style="margin:10px 0 0;color:#475569;">Contenido breve de apoyo.</p></article><article class="gjs-card" style="padding:22px;background:#ffffff;"><strong>Tarjeta 2</strong><p style="margin:10px 0 0;color:#475569;">Contenido breve de apoyo.</p></article><article class="gjs-card" style="padding:22px;background:#ffffff;"><strong>Tarjeta 3</strong><p style="margin:10px 0 0;color:#475569;">Contenido breve de apoyo.</p></article></div></section>';
    } else if (kind === 'gallery-chart') {
      content = '<section style="padding:34px 44px;"><div class="gjs-card" style="padding:24px;background:#ffffff;"><svg viewBox="0 0 420 200" style="width:100%;height:auto;display:block;"><rect x="40" y="96" width="54" height="74" rx="14" fill="#6a34ff"></rect><rect x="128" y="54" width="54" height="116" rx="14" fill="#a78bfa"></rect><rect x="216" y="74" width="54" height="96" rx="14" fill="#22c55e"></rect><rect x="304" y="28" width="54" height="142" rx="14" fill="#f59e0b"></rect></svg></div></section>';
    } else if (kind === 'game-dice') {
      content = '<section style="padding:34px 44px;"><div class="gjs-card" style="padding:28px;background:#ffffff;display:flex;align-items:center;justify-content:space-between;"><div><div style="font-size:12px;text-transform:uppercase;letter-spacing:.16em;color:#6b7280;margin-bottom:10px;">Juego</div><strong style="font-size:30px;color:#111827;">Lanza el dado</strong></div><div style="font-size:88px;line-height:1;">⚄</div></div></section>';
    } else if (kind === 'game-coin') {
      content = '<section style="padding:34px 44px;"><div class="gjs-card" style="padding:28px;background:#ffffff;display:flex;align-items:center;justify-content:space-between;"><div><strong style="font-size:30px;color:#111827;">Lanza la moneda</strong><p style="margin:10px 0 0;color:#475569;">Cara o cruz para decidir el siguiente paso.</p></div><div style="font-size:82px;line-height:1;">🪙</div></div></section>';
    } else if (kind === 'game-randomizer') {
      content = '<section style="padding:34px 44px;"><div class="gjs-card" style="padding:28px;background:#111827;color:#ffffff;"><strong style="display:block;font-size:30px;">Randomizer</strong><p style="margin:10px 0 0;color:rgba(255,255,255,.78);">Selecciona de forma aleatoria una dinámica, equipo o reto.</p></div></section>';
    } else if (kind === 'game-match') {
      content = '<section style="padding:34px 44px;"><div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;"><div class="gjs-card" style="min-height:110px;background:#ffffff;"></div><div class="gjs-card" style="min-height:110px;background:#ffffff;"></div><div class="gjs-card" style="min-height:110px;background:#ffffff;"></div><div class="gjs-card" style="min-height:110px;background:#ffffff;"></div></div></section>';
    } else if (kind === 'timer-hourglass') {
      content = '<section style="padding:34px 44px;"><div class="gjs-card" style="padding:28px;background:#ffffff;text-align:center;"><div style="font-size:70px;line-height:1;">⌛</div><strong style="display:block;font-size:30px;color:#111827;">Temporizador</strong></div></section>';
    } else if (kind === 'timer-stopwatch') {
      content = '<section style="padding:34px 44px;"><div class="gjs-card" style="padding:28px;background:#ffffff;text-align:center;"><div style="font-size:70px;line-height:1;">⏱</div><strong style="display:block;font-size:30px;color:#111827;">00:45</strong></div></section>';
    } else if (kind === 'timer-countdown') {
      content = '<section style="padding:34px 44px;"><div class="gjs-card" style="padding:28px;background:#111827;color:#ffffff;text-align:center;"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.16em;opacity:.7;margin-bottom:8px;">Cuenta atrás</div><strong style="display:block;font-size:44px;">05:00</strong></div></section>';
    } else if (kind === 'nav-progress') {
      content = '<section style="padding:24px 44px;"><div style="display:flex;align-items:center;gap:10px;"><span style="font-size:12px;font-weight:800;color:#6b7280;">1/5</span><div style="flex:1;height:10px;border-radius:999px;background:#e5e7eb;overflow:hidden;"><div style="width:20%;height:100%;background:#6a34ff;"></div></div></div></section>';
    } else if (kind === 'nav-menu') {
      content = '<section style="padding:24px 44px;"><div class="gjs-card" style="padding:16px 18px;background:#ffffff;display:flex;align-items:center;gap:18px;"><strong style="font-size:15px;color:#111827;">☰ Menú</strong><span style="color:#6b7280;">Inicio</span><span style="color:#6b7280;">Tema 1</span><span style="color:#6b7280;">Tema 2</span></div></section>';
    }
    if (!content) return;
    editor.addComponents(content);
  }
  function setWidgetsPanelVisible(show) {
    if (!widgetsPanel) return;
    widgetsPanel.classList.toggle('is-active', !!show);
  }
  function insertMediaPreset(kind) {
    var content = '';
    if (kind === 'upload-image' || kind === 'cover-image') {
      content = '<section style="padding:34px 44px;"><img src="https://images.unsplash.com/photo-1497366754035-f200968a6e72?auto=format&fit=crop&w=1200&q=80" alt="" style="width:100%;border-radius:24px;display:block;min-height:320px;object-fit:cover;"></section>';
    } else if (kind === 'gallery-image') {
      content = '<section style="padding:34px 44px;"><div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;"><div class="gjs-card" style="min-height:140px;background:#dbeafe;"></div><div class="gjs-card" style="min-height:140px;background:#fce7f3;"></div><div class="gjs-card" style="min-height:140px;background:#dcfce7;"></div></div></section>';
    } else if (kind === 'upload-audio' || kind === 'audio-button') {
      content = '<div style="padding:34px 56px;"><button style="display:inline-flex;align-items:center;gap:10px;border:0;border-radius:999px;padding:16px 22px;background:#111827;color:#ffffff;font-size:16px;font-weight:800;box-shadow:0 16px 26px rgba(17,24,39,.18);">🔊 Dar clic para escuchar el audio</button></div>';
    } else if (kind === 'upload-video' || kind === 'video-embed') {
      content = '<section style="padding:38px 48px;"><div class="gjs-card" style="background:#0f172a;padding:10px;"><iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ" allowfullscreen style="width:100%;height:360px;border:0;display:block;border-radius:18px;"></iframe></div></section>';
    } else if (kind === 'divider') {
      content = '<div style="padding:24px 56px;"><div style="height:2px;background:#cbd5e1;width:100%;"></div></div>';
    } else if (kind === 'code-block') {
      content = '<section style="padding:34px 44px;"><div class="gjs-card" style="padding:24px;background:#111827;color:#ffffff;"><div style="font-size:12px;text-transform:uppercase;letter-spacing:.16em;opacity:.7;margin-bottom:10px;">Bloque destacado</div><p style="margin:0;font-size:16px;line-height:1.6;color:rgba(255,255,255,.82);">Inserta aquí una referencia, código corto, dato o cita relevante.</p></div></section>';
    } else if (kind === 'embed-frame') {
      content = '<section style="padding:34px 44px;"><div class="gjs-card" style="padding:0;background:#ffffff;overflow:hidden;"><iframe src="https://example.com" style="width:100%;height:320px;border:0;"></iframe></div></section>';
    }
    if (!content) return;
    editor.addComponents(content);
  }
  function setInsertPanelVisible(show) {
    if (!insertPanel) return;
    insertPanel.classList.toggle('is-active', !!show);
  }
  function setStylePanelVisible(show) {
    if (!stylePanel) return;
    stylePanel.classList.toggle('is-active', !!show);
  }
