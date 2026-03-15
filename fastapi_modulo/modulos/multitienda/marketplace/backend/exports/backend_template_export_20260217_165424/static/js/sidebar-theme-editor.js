(function () {
  if (window.__sidebarThemeEditorInitialized) return;
  window.__sidebarThemeEditorInitialized = true;

  const panel = document.getElementById("menuPanel");
  const header = panel ? panel.querySelector(".menu-header") : null;
  if (!panel || !header) return;

  if (document.getElementById("openSidebarEditor") || document.getElementById("sidebarEditor")) {
    return;
  }

  const STORAGE_KEY = "backend_template_sidebar_settings";
  const DEFAULTS = {
    logo: "/static/imagenes/tu-negocio.png",
    textColor: "#164723",
    iconColor: "#164723",
    topBg: "#fff5ee",
    bottomBg: "#ffe8d7",
    animation: "slide-lr"
  };

  const style = document.createElement("style");
  style.textContent = `
    :root {
      --sidebar-text-color: ${DEFAULTS.textColor};
      --sidebar-icon-color: ${DEFAULTS.iconColor};
      --sidebar-top-bg: ${DEFAULTS.topBg};
      --sidebar-bottom-bg: ${DEFAULTS.bottomBg};
    }

    #menuPanel {
      background: linear-gradient(to bottom, var(--sidebar-top-bg) 0%, var(--sidebar-top-bg) 45%, var(--sidebar-bottom-bg) 100%) !important;
      overflow: auto;
      top: 56px !important;
      height: calc(100% - 56px) !important;
      padding-top: 12px !important;
      z-index: 45 !important;
    }

    #menuBtn {
      z-index: 80 !important;
    }

    #menuPanel .menu-list a,
    #menuPanel .menu-label,
    #menuPanel .submenu-group > summary {
      color: var(--sidebar-text-color) !important;
    }

    #menuPanel .menu-label-icon,
    #menuPanel .menu-label-icon-config {
      background-color: var(--sidebar-icon-color) !important;
    }

    #menuPanel.anim-slide-lr.open { animation: sidebar-slide-lr 0.35s ease; }
    #menuPanel.anim-slide-rl.open { animation: sidebar-slide-rl 0.35s ease; }
    #menuPanel.anim-slide-td.open { animation: sidebar-slide-td 0.35s ease; }
    #menuPanel.anim-slide-bu.open { animation: sidebar-slide-bu 0.35s ease; }

    @keyframes sidebar-slide-lr { from { transform: translateX(-100%); opacity: 0.4; } to { transform: translateX(0); opacity: 1; } }
    @keyframes sidebar-slide-rl { from { transform: translateX(100%); opacity: 0.4; } to { transform: translateX(0); opacity: 1; } }
    @keyframes sidebar-slide-td { from { transform: translateY(-100%); opacity: 0.4; } to { transform: translateY(0); opacity: 1; } }
    @keyframes sidebar-slide-bu { from { transform: translateY(100%); opacity: 0.4; } to { transform: translateY(0); opacity: 1; } }

    .sidebar-edit-btn {
      position: absolute;
      right: 10px;
      top: 10px;
      width: 30px;
      height: 30px;
      border-radius: 50%;
      border: 1px solid #d4d4d8;
      background: #fff;
      color: #374151;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.2s ease;
      z-index: 2;
    }

    #menuPanel:hover .sidebar-edit-btn,
    .sidebar-edit-btn:focus-visible {
      opacity: 1;
      pointer-events: auto;
    }

    .sidebar-editor {
      position: fixed;
      top: 0;
      right: 0;
      width: min(360px, 94vw);
      height: 100%;
      background: #ffffff;
      border-left: 1px solid #e5e7eb;
      box-shadow: -8px 0 24px rgba(0, 0, 0, 0.08);
      transform: translateX(100%);
      transition: transform 0.25s ease;
      z-index: 60;
      padding: 20px 16px;
      overflow: auto;
    }

    .sidebar-editor.open { transform: translateX(0); }
    .editor-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
    .editor-head h3 { margin: 0; font-size: 18px; color: #111827; }
    .editor-close { width: 28px; height: 28px; border-radius: 50%; border: 1px solid #d1d5db; background: #fff; cursor: pointer; }
    .editor-field { margin-bottom: 12px; }
    .editor-field label { display: block; margin-bottom: 6px; font-size: 13px; font-weight: 700; color: #374151; }
    .editor-field input, .editor-field select { width: 100%; box-sizing: border-box; border: 1px solid #d1d5db; border-radius: 8px; padding: 10px; font-size: 14px; }
    .editor-actions { display: flex; gap: 8px; margin-top: 8px; }
    .editor-actions button { border: 1px solid #d1d5db; border-radius: 8px; background: #fff; padding: 8px 12px; cursor: pointer; font-size: 13px; }
  `;
  document.head.appendChild(style);

  const menuHeaderImg = header.querySelector("img");

  const editBtn = document.createElement("button");
  editBtn.id = "openSidebarEditor";
  editBtn.className = "sidebar-edit-btn";
  editBtn.type = "button";
  editBtn.setAttribute("aria-label", "Editar sidebar");
  editBtn.setAttribute("title", "Editar sidebar");
  editBtn.textContent = "✎";
  header.style.position = "relative";
  header.appendChild(editBtn);

  const editor = document.createElement("aside");
  editor.id = "sidebarEditor";
  editor.className = "sidebar-editor";
  editor.setAttribute("aria-hidden", "true");
  editor.innerHTML = `
    <div class="editor-head">
      <h3>Editar Sidebar</h3>
      <button id="closeSidebarEditor" class="editor-close" type="button" aria-label="Cerrar editor">x</button>
    </div>
    <div class="editor-field">
      <label for="sidebarLogoInput">Logo</label>
      <input id="sidebarLogoInput" type="file" accept="image/*" />
    </div>
    <div class="editor-field">
      <label for="sidebarTextColor">Color de texto</label>
      <input id="sidebarTextColor" type="color" value="#164723" />
    </div>
    <div class="editor-field">
      <label for="sidebarIconColor">Color de icono</label>
      <input id="sidebarIconColor" type="color" value="#164723" />
    </div>
    <div class="editor-field">
      <label for="sidebarTopBg">Color sidebar superior</label>
      <input id="sidebarTopBg" type="color" value="#fff5ee" />
    </div>
    <div class="editor-field">
      <label for="sidebarBottomBg">Color sidebar inferior</label>
      <input id="sidebarBottomBg" type="color" value="#ffe8d7" />
    </div>
    <div class="editor-field">
      <label for="sidebarAnimation">Animación</label>
      <select id="sidebarAnimation">
        <option value="slide-lr">Desplazar izquierda a derecha</option>
        <option value="slide-rl">Desplazar derecha a izquierda</option>
        <option value="slide-td">Desplazar arriba a abajo</option>
        <option value="slide-bu">Desplazar abajo a arriba</option>
      </select>
    </div>
    <div class="editor-actions">
      <button id="resetSidebarStyle" type="button">Restablecer</button>
    </div>
  `;
  document.body.appendChild(editor);

  const closeEditorBtn = document.getElementById("closeSidebarEditor");
  const logoInput = document.getElementById("sidebarLogoInput");
  const textColorInput = document.getElementById("sidebarTextColor");
  const iconColorInput = document.getElementById("sidebarIconColor");
  const topBgInput = document.getElementById("sidebarTopBg");
  const bottomBgInput = document.getElementById("sidebarBottomBg");
  const animationInput = document.getElementById("sidebarAnimation");
  const resetBtn = document.getElementById("resetSidebarStyle");

  function setEditorState(open) {
    editor.classList.toggle("open", open);
    editor.setAttribute("aria-hidden", String(!open));
  }

  function saveSettings(settings) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  }

  function loadSettings() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return { ...DEFAULTS };
      const parsed = JSON.parse(raw);
      return { ...DEFAULTS, ...parsed };
    } catch (_error) {
      return { ...DEFAULTS };
    }
  }

  function applyAnimation(animation) {
    panel.classList.remove("anim-slide-lr", "anim-slide-rl", "anim-slide-td", "anim-slide-bu");
    panel.classList.add(`anim-${animation}`);
  }

  function applySettings(settings) {
    document.documentElement.style.setProperty("--sidebar-text-color", settings.textColor);
    document.documentElement.style.setProperty("--sidebar-icon-color", settings.iconColor);
    document.documentElement.style.setProperty("--sidebar-top-bg", settings.topBg);
    document.documentElement.style.setProperty("--sidebar-bottom-bg", settings.bottomBg);
    if (menuHeaderImg) menuHeaderImg.src = settings.logo || DEFAULTS.logo;
    applyAnimation(settings.animation);

    textColorInput.value = settings.textColor;
    iconColorInput.value = settings.iconColor;
    topBgInput.value = settings.topBg;
    bottomBgInput.value = settings.bottomBg;
    animationInput.value = settings.animation;
  }

  let currentSettings = loadSettings();
  applySettings(currentSettings);

  const menuButton = document.getElementById("menuBtn");
  if (menuButton && !menuButton.dataset.sidebarToggleBound) {
    menuButton.dataset.sidebarToggleBound = "true";
    menuButton.setAttribute("aria-expanded", panel.classList.contains("open") ? "true" : "false");

    function setMenuOpen(open) {
      panel.classList.toggle("open", open);
      panel.style.transform = open ? "translateX(0)" : "translateX(-100%)";
      panel.style.transition = "transform 0.2s ease";
      menuButton.setAttribute("aria-expanded", open ? "true" : "false");
      panel.setAttribute("aria-hidden", open ? "false" : "true");
    }

    function toggleFromButton(event) {
      event.preventDefault();
      event.stopPropagation();
      if (typeof event.stopImmediatePropagation === "function") {
        event.stopImmediatePropagation();
      }
      setMenuOpen(!panel.classList.contains("open"));
    }

    menuButton.addEventListener("click", toggleFromButton, true);
    menuButton.addEventListener("touchstart", toggleFromButton, { passive: false, capture: true });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        setMenuOpen(false);
      }
    });

    document.addEventListener("click", function (event) {
      const insideMenu = panel.contains(event.target);
      const insideBtn = menuButton.contains(event.target);
      if (!insideMenu && !insideBtn) {
        setMenuOpen(false);
      }
    });
  }

  function updateSetting(key, value) {
    currentSettings = { ...currentSettings, [key]: value };
    applySettings(currentSettings);
    saveSettings(currentSettings);
  }

  editBtn.addEventListener("click", function (event) {
    event.stopPropagation();
    setEditorState(true);
  });

  closeEditorBtn.addEventListener("click", function () {
    setEditorState(false);
  });

  document.addEventListener("click", function (event) {
    const isInsideEditor = editor.contains(event.target) || editBtn.contains(event.target);
    if (!isInsideEditor) setEditorState(false);
  });

  textColorInput.addEventListener("input", function () {
    updateSetting("textColor", textColorInput.value);
  });

  iconColorInput.addEventListener("input", function () {
    updateSetting("iconColor", iconColorInput.value);
  });

  topBgInput.addEventListener("input", function () {
    updateSetting("topBg", topBgInput.value);
  });

  bottomBgInput.addEventListener("input", function () {
    updateSetting("bottomBg", bottomBgInput.value);
  });

  animationInput.addEventListener("change", function () {
    updateSetting("animation", animationInput.value);
  });

  logoInput.addEventListener("change", function () {
    const file = logoInput.files && logoInput.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function (event) {
      const result = event.target && event.target.result;
      if (typeof result === "string") {
        updateSetting("logo", result);
      }
    };
    reader.readAsDataURL(file);
  });

  resetBtn.addEventListener("click", function () {
    currentSettings = { ...DEFAULTS };
    applySettings(currentSettings);
    saveSettings(currentSettings);
    logoInput.value = "";
  });
})();
