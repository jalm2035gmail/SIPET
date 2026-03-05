/**
 * sipet-widgets.js
 * Widgets premium SIPET para el constructor de páginas (GrapesJS).
 * Uso: sipetWidgets(editor)  — llamar DESPUÉS de grapesjs.init()
 */
window.sipetWidgets = function sipetWidgets(editor, opts) {
  opts = opts || {};
  var bm = editor.BlockManager;
  var dc = editor.DomComponents;

  // ============ Helpers ============
  function addStyle(css) {
    var wrapper = editor.getWrapper();
    var hosts = wrapper.find('.sipet-style-host');
    if (!hosts || !hosts.length) {
      wrapper.append('<style class="sipet-style-host">' + css + '</style>');
    } else {
      var cur = hosts[0].get('content') || '';
      hosts[0].set('content', cur + '\n' + css);
    }
  }

  // ============ Base CSS (premium SaaS) ============
  addStyle([
    ':root{',
    '  --sipet-bg:#0b1220;',
    '  --sipet-surface:#0f1a2e;',
    '  --sipet-card:#111f3a;',
    '  --sipet-border:rgba(255,255,255,.10);',
    '  --sipet-text:rgba(255,255,255,.90);',
    '  --sipet-muted:rgba(255,255,255,.65);',
    '  --sipet-accent:#4f8ef7;',
    '  --sipet-radius:18px;',
    '}',
    '.sipet-section{padding:64px 20px; background:transparent;}',
    '.sipet-container{max-width:1100px; margin:0 auto;}',
    '.sipet-grid{display:grid; gap:18px;}',
    '.sipet-card{background:linear-gradient(180deg, rgba(255,255,255,.06), rgba(255,255,255,.03));',
    '  border:1px solid var(--sipet-border); border-radius:var(--sipet-radius);',
    '  box-shadow:0 12px 30px rgba(0,0,0,.25); backdrop-filter:blur(10px);}',
    '.sipet-h1{font-size:44px; line-height:1.05; color:var(--sipet-text); margin:0 0 14px;}',
    '.sipet-h2{font-size:28px; line-height:1.15; color:var(--sipet-text); margin:0 0 10px;}',
    '.sipet-p{font-size:16px; line-height:1.6; color:var(--sipet-muted); margin:0;}',
    '.sipet-btn{display:inline-flex; align-items:center; gap:10px; padding:12px 16px;',
    '  border-radius:14px; border:1px solid var(--sipet-border);',
    '  background:rgba(255,255,255,.06); color:var(--sipet-text); text-decoration:none; font-weight:600;}',
    '.sipet-btn--primary{background:rgba(79,142,247,.20); border-color:rgba(79,142,247,.35);}',
    '.sipet-badge{display:inline-flex; padding:6px 10px; border-radius:999px;',
    '  border:1px solid var(--sipet-border); color:var(--sipet-muted); font-size:12px;}',
    '.sipet-row{display:flex; gap:18px; align-items:center; justify-content:space-between; flex-wrap:wrap;}',
    '.sipet-divider{height:1px; background:var(--sipet-border); margin:18px 0;}',
    '.sipet-input{width:100%; padding:12px 14px; border-radius:14px; border:1px solid var(--sipet-border);',
    '  background:rgba(0,0,0,.15); color:var(--sipet-text); outline:none;}',
    '.sipet-label{font-size:13px; color:var(--sipet-muted); margin-bottom:6px; display:block;}',
    '.sipet-kpi{font-size:32px; font-weight:800; color:var(--sipet-text); margin:0;}',
    '.sipet-small{font-size:12px; color:var(--sipet-muted);}',
  ].join('\n'));

  // ============ 1) HERO ============
  bm.add('sipet-hero', {
    category: 'SIPET - Secciones',
    label: 'Hero + CTA',
    content: [
      '<section class="sipet-section" style="background:radial-gradient(800px 400px at 15% 10%, rgba(79,142,247,.35), transparent 60%),',
      'radial-gradient(700px 350px at 90% 20%, rgba(34,211,238,.22), transparent 55%), var(--sipet-bg);">',
      '  <div class="sipet-container">',
      '    <div class="sipet-grid" style="grid-template-columns:1.2fr .8fr; align-items:stretch;">',
      '      <div class="sipet-card" style="padding:28px;">',
      '        <span class="sipet-badge">SIPET \u2022 Planeaci\u00f3n y Seguimiento Municipal</span>',
      '        <h1 class="sipet-h1" style="margin-top:14px;">Control presupuestal, seguimiento de metas y evidencias en un solo lugar</h1>',
      '        <p class="sipet-p">Alineado a criterios de planeaci\u00f3n, programaci\u00f3n y presupuesto. Tableros, reportes y trazabilidad para auditor\u00eda.</p>',
      '        <div style="margin-top:18px; display:flex; gap:12px; flex-wrap:wrap;">',
      '          <a class="sipet-btn sipet-btn--primary" href="#demo">Solicitar demo</a>',
      '          <a class="sipet-btn" href="#tablero">Ver tablero</a>',
      '        </div>',
      '        <div class="sipet-divider"></div>',
      '        <div class="sipet-row">',
      '          <div><p class="sipet-kpi">+60%</p><p class="sipet-small">Aceleraci\u00f3n del seguimiento</p></div>',
      '          <div><p class="sipet-kpi">100%</p><p class="sipet-small">Trazabilidad por actividad</p></div>',
      '          <div><p class="sipet-kpi">1</p><p class="sipet-small">Tablero \u00fanico</p></div>',
      '        </div>',
      '      </div>',
      '      <div class="sipet-card" style="padding:28px; display:flex; flex-direction:column; justify-content:space-between;">',
      '        <div>',
      '          <h2 class="sipet-h2">Vista r\u00e1pida</h2>',
      '          <p class="sipet-p">KPIs clave, ejecuci\u00f3n mensual, alertas y evidencias.</p>',
      '        </div>',
      '        <div class="sipet-card" style="margin-top:18px; padding:18px;">',
      '          <div class="sipet-row">',
      '            <div><div class="sipet-small">Ejecuci\u00f3n</div><div class="sipet-kpi" style="font-size:26px;">78%</div></div>',
      '            <div class="sipet-small">Actualizado: hoy</div>',
      '          </div>',
      '          <div class="sipet-divider"></div>',
      '          <div class="sipet-small">Alertas</div>',
      '          <div style="margin-top:10px; display:grid; gap:10px;">',
      '            <div class="sipet-card" style="padding:12px; border-radius:14px;"><strong style="color:var(--sipet-text);">3 metas</strong> <span class="sipet-small">en riesgo</span></div>',
      '            <div class="sipet-card" style="padding:12px; border-radius:14px;"><strong style="color:var(--sipet-text);">12 evidencias</strong> <span class="sipet-small">pendientes</span></div>',
      '          </div>',
      '        </div>',
      '      </div>',
      '    </div>',
      '  </div>',
      '</section>',
    ].join('\n')
  });

  // ============ 2) ICON BOXES ============
  var featureItems = ['Planeaci\u00f3n', 'Presupuesto', 'Seguimiento', 'Auditor\u00eda'];
  var featureCards = featureItems.map(function(t, i) {
    return [
      '<div class="sipet-card" style="padding:18px;">',
      '  <div class="sipet-badge">0' + (i + 1) + '</div>',
      '  <h3 style="margin:12px 0 6px; color:var(--sipet-text); font-size:18px;">' + t + '</h3>',
      '  <p class="sipet-p">Bloque listo para describir c\u00f3mo funciona esta capacidad en SIPET.</p>',
      '</div>',
    ].join('\n');
  }).join('\n');

  bm.add('sipet-features', {
    category: 'SIPET - Secciones',
    label: 'Features (Icon boxes)',
    content: [
      '<section class="sipet-section" style="background:var(--sipet-bg);">',
      '  <div class="sipet-container">',
      '    <div class="sipet-row" style="align-items:flex-end;">',
      '      <div>',
      '        <span class="sipet-badge">Capacidades</span>',
      '        <h2 class="sipet-h2" style="margin-top:10px;">Lo que automatiza SIPET</h2>',
      '        <p class="sipet-p">Estructura \u2192 POA \u2192 presupuesto \u2192 ejecuci\u00f3n \u2192 evidencias \u2192 reportes.</p>',
      '      </div>',
      '      <a class="sipet-btn" href="#cap">Ver m\u00f3dulos</a>',
      '    </div>',
      '    <div class="sipet-grid" style="margin-top:18px; grid-template-columns:repeat(4, minmax(0,1fr));">',
      featureCards,
      '    </div>',
      '  </div>',
      '</section>',
    ].join('\n')
  });

  // ============ 3) PORTFOLIO FILTER ============
  addStyle([
    '.sipet-filters{display:flex; gap:10px; flex-wrap:wrap; margin-top:14px;}',
    '.sipet-filter{cursor:pointer; user-select:none;}',
    '.sipet-filter[aria-pressed="true"]{outline:2px solid rgba(79,142,247,.5); background:rgba(79,142,247,.18);}',
    '.sipet-portfolio{margin-top:18px; display:grid; gap:14px; grid-template-columns:repeat(3, minmax(0,1fr));}',
    '.sipet-project{padding:16px;}',
    '.sipet-tag{font-size:12px; color:var(--sipet-muted);}',
    '.sipet-title{margin:8px 0 0; color:var(--sipet-text); font-weight:800;}',
    '.sipet-hidden{display:none !important;}',
  ].join('\n'));

  var portfolioData = [
    ['Ejecuci\u00f3n mensual',     'presupuesto', 'Gr\u00e1fica de ejecuci\u00f3n por mes y cap\u00edtulo'],
    ['Sem\u00e1foro de metas',     'metas',        'Estado por objetivo y actividad POA'],
    ['Bandeja de evidencias',      'evidencias',   'Evidencias por actividad, fecha y responsable'],
    ['Reporte CNBV/SEPS',          'reportes',     'Exportables PDF/Excel por periodo'],
    ['Variaciones',                'presupuesto',  'Comparativo presupuestado vs devengado'],
    ['Riesgo de atraso',           'metas',        'Alertas autom\u00e1ticas por retraso'],
  ];
  var portfolioCards = portfolioData.map(function(item) {
    return [
      '<article class="sipet-card sipet-project" data-cat="' + item[1] + '">',
      '  <div class="sipet-tag">' + item[1].toUpperCase() + '</div>',
      '  <h3 class="sipet-title">' + item[0] + '</h3>',
      '  <p class="sipet-p" style="margin-top:6px;">' + item[2] + '</p>',
      '</article>',
    ].join('\n');
  }).join('\n');

  bm.add('sipet-portfolio', {
    category: 'SIPET - Secciones',
    label: 'Portfolio filtrable',
    content: [
      '<section class="sipet-section" style="background:var(--sipet-bg);">',
      '  <div class="sipet-container">',
      '    <span class="sipet-badge">Casos / M\u00f3dulos</span>',
      '    <h2 class="sipet-h2" style="margin-top:10px;">Widgets del tablero</h2>',
      '    <p class="sipet-p">Filtra ejemplos: presupuesto, metas, evidencias, reportes.</p>',
      '    <div class="sipet-filters" data-sipet-filters>',
      '      <button class="sipet-btn sipet-filter" aria-pressed="true"  data-filter="all">Todos</button>',
      '      <button class="sipet-btn sipet-filter" aria-pressed="false" data-filter="presupuesto">Presupuesto</button>',
      '      <button class="sipet-btn sipet-filter" aria-pressed="false" data-filter="metas">Metas</button>',
      '      <button class="sipet-btn sipet-filter" aria-pressed="false" data-filter="evidencias">Evidencias</button>',
      '      <button class="sipet-btn sipet-filter" aria-pressed="false" data-filter="reportes">Reportes</button>',
      '    </div>',
      '    <div class="sipet-portfolio" data-sipet-portfolio>',
      portfolioCards,
      '    </div>',
      '  </div>',
      '  <script>',
      '  (function(){',
      '    var root = document.currentScript && document.currentScript.parentElement;',
      '    if(!root) return;',
      '    var filters = root.querySelector("[data-sipet-filters]");',
      '    var grid    = root.querySelector("[data-sipet-portfolio]");',
      '    if(!filters || !grid) return;',
      '    var buttons = Array.prototype.slice.call(filters.querySelectorAll("[data-filter]"));',
      '    var items   = Array.prototype.slice.call(grid.querySelectorAll("[data-cat]"));',
      '    function setActive(btn){ buttons.forEach(function(b){ b.setAttribute("aria-pressed", b===btn?"true":"false"); }); }',
      '    function apply(f){ items.forEach(function(it){ var ok=(f==="all")||(it.getAttribute("data-cat")===f); it.classList.toggle("sipet-hidden",!ok); }); }',
      '    buttons.forEach(function(btn){ btn.addEventListener("click", function(){ setActive(btn); apply(btn.getAttribute("data-filter")); }); });',
      '  })();',
      '  <\/script>',
      '</section>',
    ].join('\n')
  });

  // ============ 4) PROGRESS BARS ============
  addStyle([
    '.sipet-progress{margin-top:12px;}',
    '.sipet-progress__row{display:flex; justify-content:space-between; gap:12px; align-items:baseline;}',
    '.sipet-progress__bar{height:10px; border-radius:999px; background:rgba(255,255,255,.08); overflow:hidden; border:1px solid var(--sipet-border);}',
    '.sipet-progress__fill{height:100%; width:0%; background:rgba(79,142,247,.55); transition:width 900ms ease;}',
  ].join('\n'));

  var progressRows = [
    ['Planeaci\u00f3n', 85],
    ['Programaci\u00f3n', 72],
    ['Presupuesto', 78],
    ['Evidencias', 64],
  ].map(function(item) {
    return [
      '<div class="sipet-progress" data-sipet-progress="' + item[1] + '">',
      '  <div class="sipet-progress__row">',
      '    <strong style="color:var(--sipet-text);">' + item[0] + '</strong>',
      '    <span class="sipet-small">' + item[1] + '%</span>',
      '  </div>',
      '  <div class="sipet-progress__bar"><div class="sipet-progress__fill"></div></div>',
      '</div>',
    ].join('\n');
  }).join('\n');

  bm.add('sipet-progress', {
    category: 'SIPET - Widgets',
    label: 'Progress / Skills',
    content: [
      '<section class="sipet-section" style="background:var(--sipet-bg);">',
      '  <div class="sipet-container">',
      '    <div class="sipet-grid" style="grid-template-columns:1fr 1fr;">',
      '      <div class="sipet-card" style="padding:20px;">',
      '        <h2 class="sipet-h2">Madurez del seguimiento</h2>',
      '        <p class="sipet-p">Barras animadas cuando entran en pantalla.</p>',
      progressRows,
      '      </div>',
      '      <div class="sipet-card" style="padding:20px;">',
      '        <h2 class="sipet-h2">Qu\u00e9 mejora</h2>',
      '        <p class="sipet-p">Transparencia, control y velocidad en la gesti\u00f3n municipal.</p>',
      '        <div class="sipet-divider"></div>',
      '        <div class="sipet-grid" style="grid-template-columns:1fr 1fr;">',
      '          <div class="sipet-card" style="padding:14px; border-radius:14px;"><p class="sipet-kpi" style="font-size:26px;">-35%</p><p class="sipet-small">tiempo de armado de reportes</p></div>',
      '          <div class="sipet-card" style="padding:14px; border-radius:14px;"><p class="sipet-kpi" style="font-size:26px;">+25%</p><p class="sipet-small">cumplimiento de metas</p></div>',
      '        </div>',
      '      </div>',
      '    </div>',
      '  </div>',
      '  <script>',
      '  (function(){',
      '    var root = document.currentScript && document.currentScript.parentElement;',
      '    if(!root) return;',
      '    var bars = Array.prototype.slice.call(root.querySelectorAll("[data-sipet-progress]"));',
      '    var io = new IntersectionObserver(function(entries){',
      '      entries.forEach(function(e){',
      '        if(!e.isIntersecting) return;',
      '        var el  = e.target;',
      '        var val = parseInt(el.getAttribute("data-sipet-progress")||"0",10);',
      '        var fill = el.querySelector(".sipet-progress__fill");',
      '        if(fill) fill.style.width = Math.max(0,Math.min(100,val)) + "%";',
      '        io.unobserve(el);',
      '      });',
      '    },{threshold:.35});',
      '    bars.forEach(function(b){ io.observe(b); });',
      '  })();',
      '  <\/script>',
      '</section>',
    ].join('\n')
  });

  // ============ 5) STEPS ============
  var stepsData = [
    ['01', 'Estructura',  'Ejes, objetivos, POA y responsables.'],
    ['02', 'Presupuesto', 'Captura mensual y control por rubro.'],
    ['03', 'Ejecuci\u00f3n',  'Seguimiento, alertas y evidencias.'],
    ['04', 'Reporte',     'Exportables y trazabilidad para auditor\u00eda.'],
  ];
  var stepCards = stepsData.map(function(s) {
    return [
      '<div class="sipet-card" style="padding:18px;">',
      '  <div class="sipet-badge">' + s[0] + '</div>',
      '  <h3 style="margin:12px 0 6px; color:var(--sipet-text); font-size:18px;">' + s[1] + '</h3>',
      '  <p class="sipet-p">' + s[2] + '</p>',
      '</div>',
    ].join('\n');
  }).join('\n');

  bm.add('sipet-steps', {
    category: 'SIPET - Widgets',
    label: 'Steps numerados',
    content: [
      '<section class="sipet-section" style="background:var(--sipet-bg);">',
      '  <div class="sipet-container">',
      '    <span class="sipet-badge">Metodolog\u00eda</span>',
      '    <h2 class="sipet-h2" style="margin-top:10px;">De la planeaci\u00f3n al cierre</h2>',
      '    <div class="sipet-grid" style="margin-top:18px; grid-template-columns:repeat(4, minmax(0,1fr));">',
      stepCards,
      '    </div>',
      '  </div>',
      '</section>',
    ].join('\n')
  });

  // ============ 6) TESTIMONIALS ============
  addStyle([
    '.sipet-carousel{position:relative; overflow:hidden;}',
    '.sipet-track{display:flex; gap:14px; transition:transform 500ms ease;}',
    '.sipet-slide{min-width:calc(100% - 0px);}',
    '.sipet-nav{display:flex; gap:10px; margin-top:14px;}',
  ].join('\n'));

  var testimonialData = [
    ['Direcci\u00f3n de Planeaci\u00f3n', '\u201cAhora tenemos trazabilidad por actividad y evidencia, y reportes mensuales sin estr\u00e9s.\u201d'],
    ['Tesorer\u00eda',                    '\u201cEl control presupuestal por mes nos redujo errores y mejor\u00f3 el cierre.\u201d'],
    ['Contralor\u00eda',                  '\u201cLas auditor\u00edas son m\u00e1s f\u00e1ciles: evidencias y bit\u00e1cora a un clic.\u201d'],
  ];
  var slides = testimonialData.map(function(t) {
    return [
      '<div class="sipet-slide">',
      '  <div class="sipet-card" style="padding:18px;">',
      '    <p class="sipet-p" style="font-size:17px; color:var(--sipet-text);">' + t[1] + '</p>',
      '    <div class="sipet-divider"></div>',
      '    <strong style="color:var(--sipet-text);">' + t[0] + '</strong>',
      '    <div class="sipet-small">Gobierno Municipal</div>',
      '  </div>',
      '</div>',
    ].join('\n');
  }).join('\n');

  bm.add('sipet-testimonials', {
    category: 'SIPET - Widgets',
    label: 'Testimonials (simple)',
    content: [
      '<section class="sipet-section" style="background:var(--sipet-bg);">',
      '  <div class="sipet-container">',
      '    <div class="sipet-row">',
      '      <div>',
      '        <span class="sipet-badge">Testimonios</span>',
      '        <h2 class="sipet-h2" style="margin-top:10px;">Lo que dicen los equipos</h2>',
      '      </div>',
      '      <div class="sipet-nav">',
      '        <button class="sipet-btn" data-prev>&larr;</button>',
      '        <button class="sipet-btn" data-next>&rarr;</button>',
      '      </div>',
      '    </div>',
      '    <div class="sipet-card sipet-carousel" style="padding:18px; margin-top:14px;" data-carousel>',
      '      <div class="sipet-track" data-track>',
      slides,
      '      </div>',
      '    </div>',
      '  </div>',
      '  <script>',
      '  (function(){',
      '    var root = document.currentScript && document.currentScript.parentElement;',
      '    if(!root) return;',
      '    var c     = root.querySelector("[data-carousel]");',
      '    var track = root.querySelector("[data-track]");',
      '    var prev  = root.querySelector("[data-prev]");',
      '    var next  = root.querySelector("[data-next]");',
      '    if(!c||!track||!prev||!next) return;',
      '    var slides = Array.prototype.slice.call(track.children);',
      '    var i = 0;',
      '    function render(){ track.style.transform = "translateX(" + (-i * c.clientWidth) + "px)"; }',
      '    prev.addEventListener("click", function(){ i=(i-1+slides.length)%slides.length; render(); });',
      '    next.addEventListener("click", function(){ i=(i+1)%slides.length; render(); });',
      '    window.addEventListener("resize", render);',
      '    render();',
      '  })();',
      '  <\/script>',
      '</section>',
    ].join('\n')
  });

  // ============ 7) TEAM ============
  var teamData = [
    ['Coordinaci\u00f3n', 'Planeaci\u00f3n y POA'],
    ['Tesorer\u00eda',    'Presupuesto y cierre'],
    ['Contralor\u00eda',  'Evidencias y auditor\u00eda'],
  ];
  var teamCards = teamData.map(function(m) {
    return [
      '<div class="sipet-card" style="padding:18px;">',
      '  <div class="sipet-card" style="height:140px; border-radius:16px; background:rgba(255,255,255,.06); border:1px solid var(--sipet-border);"></div>',
      '  <h3 style="margin:14px 0 6px; color:var(--sipet-text);">' + m[0] + '</h3>',
      '  <p class="sipet-p">' + m[1] + '</p>',
      '  <div style="margin-top:12px; display:flex; gap:10px;">',
      '    <a class="sipet-btn" href="#">LinkedIn</a>',
      '    <a class="sipet-btn" href="#">Email</a>',
      '  </div>',
      '</div>',
    ].join('\n');
  }).join('\n');

  bm.add('sipet-team', {
    category: 'SIPET - Widgets',
    label: 'Team cards',
    content: [
      '<section class="sipet-section" style="background:var(--sipet-bg);">',
      '  <div class="sipet-container">',
      '    <span class="sipet-badge">Equipo</span>',
      '    <h2 class="sipet-h2" style="margin-top:10px;">Roles t\u00edpicos en SIPET</h2>',
      '    <div class="sipet-grid" style="margin-top:18px; grid-template-columns:repeat(3, minmax(0,1fr));">',
      teamCards,
      '    </div>',
      '  </div>',
      '</section>',
    ].join('\n')
  });

  // ============ 8) AWARDS LIST ============
  var awardsData = [
    ['Lineamientos de planeaci\u00f3n',    'Actualizado'],
    ['Control presupuestal mensual',       'Implementado'],
    ['Trazabilidad de evidencias',         'Implementado'],
    ['Reportes por periodo',               'Listo'],
  ];
  var awardCards = awardsData.map(function(a) {
    return [
      '<div class="sipet-card" style="padding:14px; border-radius:14px;">',
      '  <strong style="color:var(--sipet-text);">' + a[0] + '</strong>',
      '  <div class="sipet-small">' + a[1] + '</div>',
      '</div>',
    ].join('\n');
  }).join('\n');

  bm.add('sipet-awards', {
    category: 'SIPET - Widgets',
    label: 'Awards / Lista',
    content: [
      '<section class="sipet-section" style="background:var(--sipet-bg);">',
      '  <div class="sipet-container">',
      '    <div class="sipet-row">',
      '      <div>',
      '        <span class="sipet-badge">Reconocimientos</span>',
      '        <h2 class="sipet-h2" style="margin-top:10px;">Cumplimiento y buenas pr\u00e1cticas</h2>',
      '        <p class="sipet-p">Lista editable para normas, lineamientos o logros del municipio.</p>',
      '      </div>',
      '    </div>',
      '    <div class="sipet-card" style="padding:18px; margin-top:14px;">',
      '      <div class="sipet-grid" style="grid-template-columns:1fr 1fr; gap:12px;">',
      awardCards,
      '      </div>',
      '    </div>',
      '  </div>',
      '</section>',
    ].join('\n')
  });

  // ============ 9) CONTACT FORM ============
  bm.add('sipet-contact', {
    category: 'SIPET - Widgets',
    label: 'Contacto (form)',
    content: [
      '<section class="sipet-section" style="background:var(--sipet-bg);">',
      '  <div class="sipet-container">',
      '    <div class="sipet-grid" style="grid-template-columns:1fr 1fr; align-items:start;">',
      '      <div>',
      '        <span class="sipet-badge">Contacto</span>',
      '        <h2 class="sipet-h2" style="margin-top:10px;">Solicitar demo de SIPET</h2>',
      '        <p class="sipet-p">D\u00e9janos tus datos y te compartimos el tablero y un recorrido de 15 minutos.</p>',
      '        <div class="sipet-divider"></div>',
      '        <div class="sipet-small">Email: contacto@sipet.mx</div>',
      '        <div class="sipet-small">WhatsApp: +52 ...</div>',
      '      </div>',
      '      <form class="sipet-card" style="padding:18px;" action="#" method="post">',
      '        <label class="sipet-label">Nombre</label>',
      '        <input class="sipet-input" name="name" placeholder="Tu nombre" />',
      '        <div style="height:10px;"></div>',
      '        <label class="sipet-label">Email</label>',
      '        <input class="sipet-input" type="email" name="email" placeholder="tu@email.com" />',
      '        <div style="height:10px;"></div>',
      '        <label class="sipet-label">Municipio</label>',
      '        <input class="sipet-input" name="org" placeholder="Municipio / Dependencia" />',
      '        <div style="height:10px;"></div>',
      '        <label class="sipet-label">Mensaje</label>',
      '        <textarea class="sipet-input" name="msg" rows="5" placeholder="Cu\u00e9ntanos qu\u00e9 necesitas"></textarea>',
      '        <div style="margin-top:12px;">',
      '          <button class="sipet-btn sipet-btn--primary" type="submit">Enviar</button>',
      '        </div>',
      '      </form>',
      '    </div>',
      '  </div>',
      '</section>',
    ].join('\n')
  });

  // ============ 10) FOOTER ============
  var year = new Date().getFullYear();

  bm.add('sipet-footer', {
    category: 'SIPET - Secciones',
    label: 'Footer (premium)',
    content: [
      '<footer class="sipet-section" style="background:linear-gradient(180deg, transparent, rgba(0,0,0,.25)), var(--sipet-bg); padding-bottom:30px;">',
      '  <div class="sipet-container">',
      '    <div class="sipet-grid" style="grid-template-columns:1.2fr .8fr .8fr; gap:18px;">',
      '      <div class="sipet-card" style="padding:18px;">',
      '        <strong style="color:var(--sipet-text); font-size:18px;">SIPET</strong>',
      '        <p class="sipet-p" style="margin-top:8px;">Sistema de Planeaci\u00f3n y Seguimiento Municipal. Control presupuestal, seguimiento y evidencias.</p>',
      '      </div>',
      '      <div class="sipet-card" style="padding:18px;">',
      '        <strong style="color:var(--sipet-text);">Enlaces</strong>',
      '        <div class="sipet-divider"></div>',
      '        <div style="display:grid; gap:8px;">',
      '          <a class="sipet-btn" href="#tablero">Tablero</a>',
      '          <a class="sipet-btn" href="#reportes">Reportes</a>',
      '          <a class="sipet-btn" href="#demo">Demo</a>',
      '        </div>',
      '      </div>',
      '      <div class="sipet-card" style="padding:18px;">',
      '        <strong style="color:var(--sipet-text);">Contacto</strong>',
      '        <div class="sipet-divider"></div>',
      '        <div class="sipet-small">contacto@sipet.mx</div>',
      '        <div class="sipet-small">+52 ...</div>',
      '        <div class="sipet-divider"></div>',
      '        <div class="sipet-small">&copy; ' + year + ' SIPET</div>',
      '      </div>',
      '    </div>',
      '  </div>',
      '</footer>',
    ].join('\n')
  });

  // ============ Traits para el Hero ============
  dc.addType('sipet-hero', {
    model: {
      defaults: {
        name: 'SIPET Hero',
        traits: [
          { type: 'text', name: 'title',    label: 'T\u00edtulo',      changeProp: 1 },
          { type: 'text', name: 'subtitle', label: 'Subt\u00edtulo',   changeProp: 1 },
          { type: 'text', name: 'cta1',     label: 'CTA 1 texto',      changeProp: 1 },
          { type: 'text', name: 'cta1href', label: 'CTA 1 link',       changeProp: 1 },
          { type: 'text', name: 'cta2',     label: 'CTA 2 texto',      changeProp: 1 },
          { type: 'text', name: 'cta2href', label: 'CTA 2 link',       changeProp: 1 },
        ],
      },
      init: function() {
        this.on(
          'change:title change:subtitle change:cta1 change:cta1href change:cta2 change:cta2href',
          this.applyProps
        );
      },
      applyProps: function() {
        var el      = this.view && this.view.el;
        if (!el) return;
        var title    = this.get('title');
        var subtitle = this.get('subtitle');
        var cta1     = this.get('cta1');
        var cta2     = this.get('cta2');
        var cta1href = this.get('cta1href');
        var cta2href = this.get('cta2href');
        var h1  = el.querySelector('.sipet-h1');
        var p   = el.querySelector('.sipet-p');
        var a1  = el.querySelector('.sipet-btn--primary');
        var a2s = el.querySelectorAll('.sipet-btn');
        var a2  = a2s && a2s.length > 1 ? a2s[1] : null;
        if (title    && h1) h1.textContent = title;
        if (subtitle && p)  p.textContent  = subtitle;
        if (cta1     && a1) a1.textContent = cta1;
        if (cta2     && a2) a2.textContent = cta2;
        if (cta1href && a1) a1.setAttribute('href', cta1href);
        if (cta2href && a2) a2.setAttribute('href', cta2href);
      }
    },
    isComponent: function(el) {
      return el && el.tagName === 'SECTION' && el.querySelector && el.querySelector('.sipet-h1')
        ? { type: 'sipet-hero' }
        : false;
    },
  });
};
