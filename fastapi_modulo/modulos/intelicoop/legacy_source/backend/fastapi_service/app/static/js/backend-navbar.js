(function () {
  if (window.__backendNavbarInitialized) return;
  window.__backendNavbarInitialized = true;

  const DEFAULT_AVATAR = "/static/imagenes/tu-negocio.png";
  const NAVBAR_STYLE_STORAGE_KEY = "backend_navbar_style_settings";
  const TEMPLATE_STATE_KEY_PREFIX = "backend_template_state:";
  const TEMPLATE_VIEW_KEY_PREFIX = "backend_template_view:";
  const WORKFLOW_KEY_PREFIX = "backend_workflow_state:";
  const DEFAULT_NAVBAR_STYLES = {
    bgColor: "#ffffff",
    textColor: "#374151",
    svgColor: "#374151"
  };

  function detectPrefix(pathname) {
    if (pathname.startsWith("/avan/")) return "/avan";
    if (pathname === "/avan") return "/avan";
    return "";
  }

  function readStoredToken() {
    const keys = ["access_token", "token", "auth_token"];
    for (let i = 0; i < keys.length; i += 1) {
      const key = keys[i];
      const localValue = localStorage.getItem(key);
      if (localValue) return localValue;
      const sessionValue = sessionStorage.getItem(key);
      if (sessionValue) return sessionValue;
    }
    return "";
  }

  function buildAuthHeaders() {
    const headers = { Accept: "application/json" };
    const token = readStoredToken();
    if (!token) return headers;
    const normalizedToken = token.startsWith("Bearer ") ? token.slice(7) : token;
    headers.Authorization = `Bearer ${normalizedToken}`;
    return headers;
  }

  function parsePayload(tokenValue) {
    try {
      const token = tokenValue.startsWith("Bearer ") ? tokenValue.slice(7) : tokenValue;
      const parts = token.split(".");
      if (parts.length < 2) return null;
      const MAIN64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
      const padded = MAIN64 + "=".repeat((4 - (MAIN64.length % 4)) % 4);
      return JSON.parse(window.atob(padded));
    } catch (_error) {
      return null;
    }
  }

  function getCurrentUserType() {
    const token = readStoredToken();
    if (!token) return "";
    const payload = parsePayload(token);
    return payload && payload.user_type ? String(payload.user_type).toLowerCase() : "";
  }

  function loadNavbarStyles() {
    try {
      const raw = localStorage.getItem(NAVBAR_STYLE_STORAGE_KEY);
      if (!raw) return { ...DEFAULT_NAVBAR_STYLES };
      const parsed = JSON.parse(raw);
      return { ...DEFAULT_NAVBAR_STYLES, ...parsed };
    } catch (_error) {
      return { ...DEFAULT_NAVBAR_STYLES };
    }
  }

  function saveNavbarStyles(value) {
    localStorage.setItem(NAVBAR_STYLE_STORAGE_KEY, JSON.stringify(value));
  }

  function applyNavbarStyles(value) {
    document.documentElement.style.setProperty("--backend-navbar-bg", value.bgColor);
    document.documentElement.style.setProperty("--backend-navbar-text", value.textColor);
    document.documentElement.style.setProperty("--backend-navbar-svg", value.svgColor);
  }

  const prefix = detectPrefix(window.location.pathname || "");

  const style = document.createElement("style");
  style.textContent = `
    :root {
      --backend-navbar-bg: ${DEFAULT_NAVBAR_STYLES.bgColor};
      --backend-navbar-text: ${DEFAULT_NAVBAR_STYLES.textColor};
      --backend-navbar-svg: ${DEFAULT_NAVBAR_STYLES.svgColor};
    }

    .backend-navbar {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      height: 56px;
      background: var(--backend-navbar-bg);
      border-bottom: 1px solid #e5e7eb;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 14px 0 18px;
      z-index: 55;
    }

    .backend-navbar-left {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }

    .backend-navbar-path-icon {
      width: 14px;
      height: 14px;
      flex: 0 0 14px;
      background-color: var(--backend-navbar-svg);
      -backendkit-mask: url('/static/icons/configuracion.svg') no-repeat center / contain;
      mask: url('/static/icons/configuracion.svg') no-repeat center / contain;
    }

    .backend-navbar-path {
      color: var(--backend-navbar-text);
      font-size: 13px;
      font-weight: 700;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 60vw;
    }

    .backend-navbar-right {
      display: inline-flex;
      align-items: center;
      gap: 10px;
    }

    .backend-navbar-tools {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      margin-left: 10px;
    }

    .backend-tool-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      width: 34px;
      height: 30px;
      border: 0;
      border-radius: 8px;
      background: transparent;
      color: var(--backend-navbar-text);
      cursor: pointer;
      overflow: hidden;
      transition: width 0.2s ease, padding 0.2s ease;
      padding: 0;
      white-space: nowrap;
    }

    .backend-tool-icon {
      width: 21px;
      height: 21px;
      flex: 0 0 21px;
      background-color: var(--backend-navbar-svg);
      opacity: 1;
      transition: opacity 0.15s ease;
    }

    .backend-tool-btn[data-icon="guardar"] .backend-tool-icon {
      -backendkit-mask: url('/static/icons/guardar.svg') no-repeat center / contain;
      mask: url('/static/icons/guardar.svg') no-repeat center / contain;
    }

    .backend-tool-btn[data-icon="editar"] .backend-tool-icon {
      -backendkit-mask: url('/static/icons/editar.svg') no-repeat center / contain;
      mask: url('/static/icons/editar.svg') no-repeat center / contain;
    }

    .backend-tool-btn[data-icon="eliminar"] .backend-tool-icon {
      -backendkit-mask: url('/static/icons/eliminar.svg') no-repeat center / contain;
      mask: url('/static/icons/eliminar.svg') no-repeat center / contain;
    }

    .backend-tool-btn[data-icon="nuevo"] .backend-tool-icon {
      -backendkit-mask: url('/static/icons/nuevo.svg') no-repeat center / contain;
      mask: url('/static/icons/nuevo.svg') no-repeat center / contain;
    }

    .backend-tool-label {
      font-size: 12px;
      font-weight: 700;
      color: var(--backend-navbar-text);
      opacity: 0;
      width: 0;
      transition: opacity 0.15s ease, width 0.15s ease;
    }

    .backend-tool-btn:hover {
      width: 84px;
      padding: 0 8px;
      justify-content: flex-start;
    }

    .backend-tool-btn:hover .backend-tool-icon {
      opacity: 0;
      width: 0;
      flex-basis: 0;
    }

    .backend-tool-btn:hover .backend-tool-label {
      opacity: 1;
      width: auto;
    }

    .backend-navbar-notif {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border: 0;
      background: transparent;
      color: var(--backend-navbar-svg);
      cursor: pointer;
      padding: 0;
    }

    .backend-navbar-notif-icon {
      width: 18px;
      height: 18px;
      flex: 0 0 18px;
      background-color: currentColor;
      -backendkit-mask: url('/static/icons/notificaciones.svg') no-repeat center / contain;
      mask: url('/static/icons/notificaciones.svg') no-repeat center / contain;
      transition: transform 0.2s ease;
    }

    .backend-navbar-notif:hover .backend-navbar-notif-icon {
      transform: translateY(-2px) rotate(-10deg);
    }

    .backend-navbar-notif-count {
      min-width: 18px;
      height: 18px;
      padding: 0 5px;
      border-radius: 999px;
      border: 1px solid color-mix(in srgb, var(--backend-navbar-svg) 45%, #ffffff);
      color: var(--backend-navbar-svg);
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 11px;
      font-weight: 700;
      line-height: 1;
      background: transparent;
    }

    .backend-navbar-edit-btn {
      border: 1px solid #d1d5db;
      background: #fff;
      color: #374151;
      border-radius: 8px;
      height: 30px;
      padding: 0 10px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      opacity: 1;
      pointer-events: auto;
      transition: opacity 0.2s ease;
    }

    .backend-navbar-user {
      position: relative;
      display: inline-flex;
      align-items: center;
    }

    .backend-navbar-avatar {
      width: 34px;
      height: 34px;
      border-radius: 50%;
      border: 1px solid #d1d5db;
      object-fit: cover;
      cursor: pointer;
      background: #f3f4f6;
    }

    .backend-navbar-menu {
      position: absolute;
      right: 0;
      top: calc(100% + 8px);
      width: 170px;
      background: #ffffff;
      border: 1px solid #e5e7eb;
      border-radius: 10px;
      box-shadow: 0 10px 20px rgba(0, 0, 0, 0.08);
      display: none;
      overflow: hidden;
      z-index: 70;
    }

    .backend-navbar-menu.open { display: block; }

    .backend-navbar-item {
      width: 100%;
      border: 0;
      background: #fff;
      text-align: left;
      padding: 10px 12px;
      color: #1f2937;
      font-size: 13px;
      cursor: pointer;
    }

    .backend-navbar-item:hover { background: #f3f4f6; }

    .backend-navbar-editor {
      position: fixed;
      top: 56px;
      right: 10px;
      width: min(320px, 92vw);
      background: #fff;
      border: 1px solid #e5e7eb;
      border-radius: 12px;
      box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
      padding: 12px;
      z-index: 75;
      display: none;
    }

    .backend-navbar-editor.open { display: block; }

    .backend-action-message {
      position: fixed;
      top: 64px;
      right: 14px;
      z-index: 90;
      border-radius: 10px;
      padding: 8px 12px;
      font-size: 12px;
      font-weight: 700;
      border: 1px solid #d1d5db;
      background: #ffffff;
      color: #1f2937;
      box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
      opacity: 0;
      transform: translateY(-6px);
      transition: opacity 0.18s ease, transform 0.18s ease;
      pointer-events: none;
    }

    .backend-action-message.show {
      opacity: 1;
      transform: translateY(0);
    }

    .backend-action-message.success {
      border-color: #86efac;
      color: #166534;
      background: #f0fdf4;
    }

    .backend-action-message.error {
      border-color: #fca5a5;
      color: #991b1b;
      background: #fef2f2;
    }

    .backend-navbar-editor h4 {
      margin: 0 0 10px;
      font-size: 14px;
      color: #111827;
    }

    .backend-navbar-field {
      margin-bottom: 10px;
    }

    .backend-navbar-field label {
      display: block;
      font-size: 12px;
      font-weight: 700;
      color: #374151;
      margin-bottom: 4px;
    }

    .backend-navbar-field input {
      width: 100%;
      border: 1px solid #d1d5db;
      border-radius: 8px;
      padding: 6px;
      box-sizing: border-box;
      background: #fff;
    }

    .backend-navbar-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
    }

    .backend-navbar-actions button {
      border: 1px solid #d1d5db;
      border-radius: 8px;
      background: #fff;
      padding: 6px 10px;
      font-size: 12px;
      cursor: pointer;
    }

    .backend-view-switcher {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      margin: 8px 0 14px;
      padding: 8px;
      border: 1px solid #e5e7eb;
      border-radius: 10px;
      background: #fff;
    }

    .backend-view-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      border: 1px solid #d1d5db;
      border-radius: 8px;
      background: #fff;
      color: #1f2937;
      font-size: 12px;
      font-weight: 700;
      padding: 6px 10px;
      cursor: pointer;
    }

    .backend-view-btn.active {
      border-color: #2563eb;
      color: #1d4ed8;
      background: #eff6ff;
    }

    .backend-view-btn-icon {
      width: 14px;
      height: 14px;
      flex: 0 0 14px;
      background-color: currentColor;
    }

    .backend-view-btn[data-view="form"] .backend-view-btn-icon {
      -backendkit-mask: url('/static/icons/form.svg') no-repeat center / contain;
      mask: url('/static/icons/form.svg') no-repeat center / contain;
    }

    .backend-view-btn[data-view="list"] .backend-view-btn-icon {
      -backendkit-mask: url('/static/icons/lista.svg') no-repeat center / contain;
      mask: url('/static/icons/lista.svg') no-repeat center / contain;
    }

    .backend-view-btn[data-view="kanban"] .backend-view-btn-icon {
      -backendkit-mask: url('/static/icons/kanban.svg') no-repeat center / contain;
      mask: url('/static/icons/kanban.svg') no-repeat center / contain;
    }

    .backend-view-panel {
      display: none;
      background: #fff;
      border: 1px solid #e5e7eb;
      border-radius: 12px;
      padding: 14px;
      margin-bottom: 14px;
    }

    .backend-view-panel.active {
      display: block;
    }

    .backend-view-form {
      display: grid;
      gap: 10px;
      grid-template-columns: 1fr 1fr;
    }

    .backend-view-input {
      border: 1px solid #d1d5db;
      border-radius: 10px;
      padding: 10px;
      width: 100%;
      font-size: 14px;
    }

    .backend-view-list {
      display: grid;
      gap: 8px;
    }

    .backend-view-list-row {
      display: grid;
      grid-template-columns: 180px 1fr 130px;
      gap: 10px;
      border: 1px solid #e5e7eb;
      border-radius: 10px;
      padding: 10px;
      font-size: 13px;
      color: #374151;
      background: #fff;
    }

    .backend-view-kanban {
      display: grid;
      gap: 10px;
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    .backend-view-kanban-col {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 10px;
      min-height: 140px;
    }

    .backend-view-kanban-col h4 {
      margin: 0 0 8px;
      font-size: 13px;
      color: #334155;
    }

    .backend-view-kanban-card {
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 8px;
      margin-bottom: 8px;
      display: grid;
      grid-template-columns: 56px 1fr;
      gap: 10px;
      align-items: center;
      cursor: pointer;
    }

    .backend-view-kanban-media {
      width: 56px;
      height: 56px;
      border-radius: 8px;
      overflow: hidden;
      border: 1px solid #e2e8f0;
      background: #f8fafc;
    }

    .backend-view-kanban-media img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }

    .backend-view-kanban-content {
      min-width: 0;
    }

    .backend-view-kanban-name {
      margin: 0;
      font-size: 14px;
      font-weight: 800;
      color: #1f2937;
      line-height: 1.2;
      word-break: break-word;
    }

    .backend-view-kanban-meta {
      margin: 2px 0 0;
      font-size: 12px;
      color: #64748b;
      line-height: 1.35;
      word-break: break-word;
    }

    .backend-kanban-actions {
      margin-top: 6px;
    }

    .backend-kanban-action {
      border: 1px solid #d1d5db;
      border-radius: 8px;
      background: #fff;
      color: #1f2937;
      font-size: 11px;
      font-weight: 700;
      padding: 4px 8px;
      cursor: pointer;
    }

    .backend-kanban-note {
      margin: 0;
      font-size: 11px;
      color: #b45309;
      font-weight: 700;
    }

    body { padding-top: 56px !important; }
    .menu-toggle { top: 70px !important; }
    .template-sidebar-toggle { top: 70px !important; }

    @media (max-width: 740px) {
      .backend-navbar-path { max-width: 46vw; font-size: 12px; }
    }
  `;
  document.head.appendChild(style);

  const nav = document.createElement("header");
  nav.className = "backend-navbar";
  nav.innerHTML = `
    <div class="backend-navbar-left">
      <span class="backend-navbar-path-icon" aria-hidden="true"></span>
      <div class="backend-navbar-path"></div>
    </div>
    <div class="backend-navbar-tools">
      <button class="backend-tool-btn" type="button" data-action="save" data-icon="guardar" aria-label="Guardar">
        <span class="backend-tool-icon" aria-hidden="true"></span>
        <span class="backend-tool-label">Guardar</span>
      </button>
      <button class="backend-tool-btn" type="button" data-action="edit-content" data-icon="editar" aria-label="Editar">
        <span class="backend-tool-icon" aria-hidden="true"></span>
        <span class="backend-tool-label">Editar</span>
      </button>
      <button class="backend-tool-btn" type="button" data-action="delete-content" data-icon="eliminar" aria-label="Eliminar">
        <span class="backend-tool-icon" aria-hidden="true"></span>
        <span class="backend-tool-label">Eliminar</span>
      </button>
      <button class="backend-tool-btn" type="button" data-action="new-content" data-icon="nuevo" aria-label="Nuevo">
        <span class="backend-tool-icon" aria-hidden="true"></span>
        <span class="backend-tool-label">Nuevo</span>
      </button>
    </div>
    <div class="backend-navbar-right">
      <button class="backend-navbar-notif" type="button" aria-label="Notificaciones" title="Notificaciones">
        <span class="backend-navbar-notif-icon" aria-hidden="true"></span>
        <span class="backend-navbar-notif-count">0</span>
      </button>
      <button class="backend-navbar-edit-btn" type="button" aria-label="Editar navbar">Editar</button>
      <div class="backend-navbar-user">
        <img class="backend-navbar-avatar" alt="Usuario" />
        <div class="backend-navbar-menu" role="menu" aria-label="Opciones de usuario">
          <button class="backend-navbar-item" type="button" data-action="edit">Editar datos</button>
          <button class="backend-navbar-item" type="button" data-action="logout">Cerrar sesión</button>
        </div>
      </div>
    </div>
  `;

  const editor = document.createElement("div");
  editor.className = "backend-navbar-editor";
  editor.innerHTML = `
    <h4>Editar Navbar</h4>
    <div class="backend-navbar-field">
      <label for="navbarBgColorInput">Color del navbar</label>
      <input id="navbarBgColorInput" type="color" value="${DEFAULT_NAVBAR_STYLES.bgColor}" />
    </div>
    <div class="backend-navbar-field">
      <label for="navbarTextColorInput">Color del texto del navbar</label>
      <input id="navbarTextColorInput" type="color" value="${DEFAULT_NAVBAR_STYLES.textColor}" />
    </div>
    <div class="backend-navbar-field">
      <label for="navbarSvgColorInput">Color del SVG del navbar</label>
      <input id="navbarSvgColorInput" type="color" value="${DEFAULT_NAVBAR_STYLES.svgColor}" />
    </div>
    <div class="backend-navbar-actions">
      <button type="button" id="navbarResetBtn">Restablecer</button>
    </div>
  `;

  document.body.prepend(nav);
  document.body.appendChild(editor);
  const actionMessage = document.createElement("div");
  actionMessage.className = "backend-action-message";
  document.body.appendChild(actionMessage);

  const pathNode = nav.querySelector(".backend-navbar-path");
  const toolsNode = nav.querySelector(".backend-navbar-tools");
  const toolButtons = nav.querySelectorAll(".backend-tool-btn");
  const notifBtn = nav.querySelector(".backend-navbar-notif");
  const notifCount = nav.querySelector(".backend-navbar-notif-count");
  const editNavbarBtn = nav.querySelector(".backend-navbar-edit-btn");
  const avatarNode = nav.querySelector(".backend-navbar-avatar");
  const menuNode = nav.querySelector(".backend-navbar-menu");
  const bgInput = editor.querySelector("#navbarBgColorInput");
  const textInput = editor.querySelector("#navbarTextColorInput");
  const svgInput = editor.querySelector("#navbarSvgColorInput");
  const resetBtn = editor.querySelector("#navbarResetBtn");

  const pathText = window.location.pathname || "/";
  const isTemplateScreen = pathText === `${prefix}/template` || pathText === "/template";
  const isVendorScreen = pathText === `${prefix}/agregar-usuario` || pathText === "/agregar-usuario";
  const isStoreScreen = pathText === `${prefix}/gestion` || pathText === "/gestion";
  const screenStateKey = `${TEMPLATE_STATE_KEY_PREFIX}${pathText}`;
  const templateRoot = document.querySelector(".backend-template");
  const defaultTemplateHTML = templateRoot ? templateRoot.innerHTML : "";
  const vendorFieldSelectors = [
    "#user-name",
    "#user-email",
    "#user-store",
    "#user-username",
    "#user-password",
    "#user-two-factor",
    "#user-phone",
    "#user-role",
    "#user-photo",
    "#photoImage"
  ];
  const vendorFields = vendorFieldSelectors
    .map(function (selector) { return document.querySelector(selector); })
    .filter(Boolean);
  const storeFieldSelectors = [
    "#store-name",
    "#store-type",
    "#store-admin",
    "#store-membership",
    "#store-logo",
    "#logoImage"
  ];
  const storeFields = storeFieldSelectors
    .map(function (selector) { return document.querySelector(selector); })
    .filter(Boolean);
  let editMode = false;
  let actionMessageTimer = null;

  function showActionMessage(text, kind) {
    if (!actionMessage) return;
    actionMessage.textContent = text;
    actionMessage.classList.remove("success", "error", "show");
    actionMessage.classList.add(kind === "error" ? "error" : "success");
    // Force reflow so repeated clicks animate consistently.
    void actionMessage.offsetWidth;
    actionMessage.classList.add("show");
    if (actionMessageTimer) {
      clearTimeout(actionMessageTimer);
    }
    actionMessageTimer = setTimeout(function () {
      actionMessage.classList.remove("show");
    }, 2600);
  }

  function setTemplateEditMode(enabled) {
    editMode = enabled;
    if (!templateRoot) return;
    const editableNodes = templateRoot.querySelectorAll("h1, h2, p, span");
    editableNodes.forEach(function (node) {
      node.setAttribute("contenteditable", enabled ? "true" : "false");
      node.style.outline = enabled ? "1px dashed #9ca3af" : "";
      node.style.outlineOffset = enabled ? "2px" : "";
    });
  }

  function applySavedTemplateState() {
    if (!isTemplateScreen || !templateRoot) return;
    try {
      const raw = localStorage.getItem(screenStateKey);
      if (raw) {
        templateRoot.innerHTML = raw;
      }
    } catch (_error) {}
  }

  applySavedTemplateState();

  function collectVendorState() {
    const state = {};
    vendorFields.forEach(function (field) {
      if (!field.id) return;
      if (field.id === "photoImage") {
        state[field.id] = field.getAttribute("src") || "";
      } else if (field.type === "checkbox") {
        state[field.id] = Boolean(field.checked);
      } else if (field.type === "file") {
        state[field.id] = "";
      } else {
        state[field.id] = field.value;
      }
    });
    return state;
  }

  function applyVendorState(state) {
    if (!state || !vendorFields.length) return;
    vendorFields.forEach(function (field) {
      if (!field.id || !(field.id in state)) return;
      if (field.id === "photoImage") {
        if (state[field.id]) {
          field.setAttribute("src", state[field.id]);
        }
      } else if (field.type === "checkbox") {
        field.checked = Boolean(state[field.id]);
      } else if (field.type === "file") {
        field.value = "";
      } else {
        field.value = state[field.id];
      }
    });
  }

  function setVendorEditMode(enabled) {
    editMode = enabled;
    vendorFields.forEach(function (field) {
      if (field.id === "user-photo" || field.id === "photoImage") return;
      if ("readOnly" in field && field.tagName === "INPUT" && field.type !== "checkbox") {
        field.readOnly = !enabled;
      }
      if (field.tagName === "SELECT" || field.type === "checkbox") {
        field.disabled = !enabled;
      }
      field.style.outline = enabled ? "1px dashed #9ca3af" : "";
      field.style.outlineOffset = enabled ? "2px" : "";
    });
  }

  if (isVendorScreen) {
    try {
      const raw = localStorage.getItem(screenStateKey);
      if (raw) {
        applyVendorState(JSON.parse(raw));
      }
    } catch (_error) {}
    setVendorEditMode(true);
  }

  function collectStoreState() {
    const state = {};
    storeFields.forEach(function (field) {
      if (!field.id) return;
      if (field.id === "logoImage") {
        state[field.id] = field.getAttribute("src") || "";
      } else if (field.type === "file") {
        state[field.id] = "";
      } else {
        state[field.id] = field.value;
      }
    });
    return state;
  }

  function applyStoreState(state) {
    if (!state || !storeFields.length) return;
    storeFields.forEach(function (field) {
      if (!field.id || !(field.id in state)) return;
      if (field.id === "logoImage") {
        if (state[field.id]) {
          field.setAttribute("src", state[field.id]);
        }
      } else if (field.type === "file") {
        field.value = "";
      } else {
        field.value = state[field.id];
      }
    });
  }

  function setStoreEditMode(enabled) {
    editMode = enabled;
    storeFields.forEach(function (field) {
      if (field.id === "store-logo" || field.id === "logoImage") return;
      if ("readOnly" in field && field.tagName === "INPUT") {
        field.readOnly = !enabled;
      }
      if (field.tagName === "SELECT") {
        field.disabled = !enabled;
      }
      field.style.outline = enabled ? "1px dashed #9ca3af" : "";
      field.style.outlineOffset = enabled ? "2px" : "";
    });
  }

  if (isStoreScreen) {
    try {
      const raw = localStorage.getItem(screenStateKey);
      if (raw) {
        applyStoreState(JSON.parse(raw));
      }
    } catch (_error) {}
    setStoreEditMode(true);
  }

  function initTemplateViews() {
    if (!isTemplateScreen || !templateRoot) return;
    if (templateRoot.querySelector(".backend-view-switcher")) return;

    const selectedViewKey = `${TEMPLATE_VIEW_KEY_PREFIX}${pathText}`;
    const container = document.createElement("section");
    container.innerHTML = `
      <div class="backend-view-switcher">
        <button class="backend-view-btn" type="button" data-view="form">
          <span class="backend-view-btn-icon" aria-hidden="true"></span>
          Form
        </button>
        <button class="backend-view-btn" type="button" data-view="list">
          <span class="backend-view-btn-icon" aria-hidden="true"></span>
          List
        </button>
        <button class="backend-view-btn" type="button" data-view="kanban">
          <span class="backend-view-btn-icon" aria-hidden="true"></span>
          Kanban
        </button>
      </div>
      <div class="backend-view-panel" data-view-panel="form">
        <div class="backend-view-form">
          <input class="backend-view-input" type="text" placeholder="Nombre" />
          <input class="backend-view-input" type="text" placeholder="Categoría" />
          <input class="backend-view-input" type="text" placeholder="Administrador" />
          <input class="backend-view-input" type="text" placeholder="Estado" />
        </div>
      </div>
      <div class="backend-view-panel" data-view-panel="list">
        <div class="backend-view-list">
          <div class="backend-view-list-row"><strong>Tienda Norte</strong><span>Moda</span><span>Activa</span></div>
          <div class="backend-view-list-row"><strong>Tienda Centro</strong><span>Restaurante</span><span>Pendiente</span></div>
          <div class="backend-view-list-row"><strong>Tienda Sur</strong><span>Ferretería</span><span>Activa</span></div>
        </div>
      </div>
      <div class="backend-view-panel" data-view-panel="kanban">
        <div class="backend-view-kanban">
          <div class="backend-view-kanban-col">
            <h4>Pendiente</h4>
            <div class="backend-view-kanban-card">
              <div class="backend-view-kanban-media"><img src="/static/imagenes/tunegociovaleinv.png" alt="Tienda Centro" /></div>
              <div class="backend-view-kanban-content">
                <p class="backend-view-kanban-name">Tienda Centro</p>
                <p class="backend-view-kanban-meta">Estado: Pendiente</p>
              </div>
            </div>
          </div>
          <div class="backend-view-kanban-col">
            <h4>En revisión</h4>
            <div class="backend-view-kanban-card">
              <div class="backend-view-kanban-media"><img src="/static/imagenes/tunegociovaleinv.png" alt="Tienda Este" /></div>
              <div class="backend-view-kanban-content">
                <p class="backend-view-kanban-name">Tienda Este</p>
                <p class="backend-view-kanban-meta">Estado: En revisión</p>
              </div>
            </div>
          </div>
          <div class="backend-view-kanban-col">
            <h4>Activo</h4>
            <div class="backend-view-kanban-card">
              <div class="backend-view-kanban-media"><img src="/static/imagenes/tunegociovaleinv.png" alt="Tienda Norte" /></div>
              <div class="backend-view-kanban-content">
                <p class="backend-view-kanban-name">Tienda Norte</p>
                <p class="backend-view-kanban-meta">Estado: Activo</p>
              </div>
            </div>
            <div class="backend-view-kanban-card">
              <div class="backend-view-kanban-media"><img src="/static/imagenes/tunegociovaleinv.png" alt="Tienda Sur" /></div>
              <div class="backend-view-kanban-content">
                <p class="backend-view-kanban-name">Tienda Sur</p>
                <p class="backend-view-kanban-meta">Estado: Activo</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    `;

    const subtitle = templateRoot.querySelector("p");
    if (subtitle && subtitle.parentNode) {
      subtitle.parentNode.insertBefore(container, subtitle.nextSibling);
    } else {
      templateRoot.prepend(container);
    }

    const buttons = Array.from(templateRoot.querySelectorAll(".backend-view-btn"));
    const panels = Array.from(templateRoot.querySelectorAll(".backend-view-panel"));

    function setView(mode) {
      buttons.forEach(function (btn) {
        btn.classList.toggle("active", btn.dataset.view === mode);
      });
      panels.forEach(function (panel) {
        panel.classList.toggle("active", panel.dataset.viewPanel === mode);
      });
      localStorage.setItem(selectedViewKey, mode);
    }

    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        setView(btn.dataset.view);
      });
    });

    container.addEventListener("click", function (event) {
      if (event.target && (event.target.closest(".backend-view-kanban-card") || event.target.closest(".backend-view-list-row"))) {
        setView("form");
      }
    });

    setView("form");
  }

  initTemplateViews();

  function initEntityViews() {
    if (!isVendorScreen && !isStoreScreen) return;
    const pageRoot = document.querySelector(".page");
    if (!pageRoot || pageRoot.querySelector(".backend-view-switcher")) return;

    const selectedViewKey = `${TEMPLATE_VIEW_KEY_PREFIX}${pathText}`;
    const workflowKey = `${WORKFLOW_KEY_PREFIX}${pathText}`;
    const workflowMapKey = `${WORKFLOW_KEY_PREFIX}${pathText}:map`;
    const userType = getCurrentUserType();
    const canAuthorize = userType === "superadmin";
    let workflowStatus = localStorage.getItem(workflowKey) || "pendiente";
    let workflowMap = {};
    try {
      workflowMap = JSON.parse(localStorage.getItem(workflowMapKey) || "{}");
    } catch (_error) {
      workflowMap = {};
    }
    let entitiesCache = [];
    let entitiesLoaded = false;
    const formSections = Array.from(pageRoot.querySelectorAll(".section"));

    const container = document.createElement("section");
    container.innerHTML = `
      <div class="backend-view-switcher">
        <button class="backend-view-btn" type="button" data-view="form">
          <span class="backend-view-btn-icon" aria-hidden="true"></span>
          Form
        </button>
        <button class="backend-view-btn" type="button" data-view="list">
          <span class="backend-view-btn-icon" aria-hidden="true"></span>
          List
        </button>
        <button class="backend-view-btn" type="button" data-view="kanban">
          <span class="backend-view-btn-icon" aria-hidden="true"></span>
          Kanban
        </button>
      </div>
      <div class="backend-view-panel" data-view-panel="list">
        <div class="backend-view-list" id="entityListView"></div>
      </div>
      <div class="backend-view-panel" data-view-panel="kanban">
        <div class="backend-view-kanban" id="entityKanbanView"></div>
      </div>
    `;

    const subtitle = pageRoot.querySelector(".subtitle");
    if (subtitle && subtitle.parentNode) {
      subtitle.parentNode.insertBefore(container, subtitle.nextSibling);
    } else {
      pageRoot.prepend(container);
    }

    const buttons = Array.from(container.querySelectorAll(".backend-view-btn"));
    const listPanel = container.querySelector('[data-view-panel="list"]');
    const kanbanPanel = container.querySelector('[data-view-panel="kanban"]');
    const listView = container.querySelector("#entityListView");
    const kanbanView = container.querySelector("#entityKanbanView");

    async function ensureEntitiesLoaded(forceReload) {
      if (entitiesLoaded && !forceReload) return;
      try {
        if (isStoreScreen) {
          const response = await fetch(`${prefix}/vendors/`, { headers: buildAuthHeaders() });
          if (!response.ok) throw new Error("No stores");
          const stores = await response.json();
          entitiesCache = Array.isArray(stores) ? stores.map(function (store) {
            const rawStatus = String(store.status || "pending").toLowerCase();
            let wf = "pendiente";
            if (rawStatus === "approved") wf = "activo";
            if (rawStatus === "rejected" || rawStatus === "suspended") wf = "en_revision";
            return {
              id: String(store.id || Math.random()),
              name: store.store_name || "Sin nombre",
              subtitle: store.store_slug || store.country || "Tienda",
              details: [store.country || "Sin país", (store.commission_rate || "0") + "% comisión"],
              image: store.logo || "/static/imagenes/tunegociovaleinv.png",
              status: workflowMap[String(store.id)] || wf,
            };
          }) : [];
        } else if (isVendorScreen) {
          const response = await fetch(`${prefix}/users/system-users`, { headers: buildAuthHeaders() });
          if (!response.ok) throw new Error("No users");
          const users = await response.json();
          entitiesCache = Array.isArray(users) ? users
            .filter(function (user) { return String(user.user_type || "").toLowerCase() === "vendor"; })
            .map(function (user) {
              const id = String(user.id || Math.random());
              return {
                id: id,
                name: user.username || "Sin usuario",
                subtitle: user.email || "",
                details: [user.user_type || "vendor", user.email || "sin correo"],
                image: "/static/imagenes/tunegociovaleinv.png",
                status: workflowMap[id] || "pendiente",
              };
            }) : [];
        }
      } catch (_error) {
        entitiesCache = [];
      }
      entitiesLoaded = true;
    }

    function renderEntityViews() {
      const fallbackImage = "/static/imagenes/tunegociovaleinv.png";
      function makeCard(imageUrl, name, details) {
        const safeImage = imageUrl || fallbackImage;
        const safeName = name || "Sin nombre";
        const meta = Array.isArray(details) ? details.join(" · ") : "";
        let actions = "";
        if (workflowStatus === "pendiente") {
          actions = `
            <div class="backend-kanban-actions">
              <button class="backend-kanban-action" type="button" data-next-status="en_revision">Enviar a revisión</button>
            </div>
          `;
        } else if (workflowStatus === "en_revision") {
          actions = canAuthorize
            ? `
              <div class="backend-kanban-actions">
                <button class="backend-kanban-action" type="button" data-next-status="activo">Autorizar</button>
              </div>
            `
            : `<p class="backend-kanban-note">Pendiente de autorización del superadministrador</p>`;
        }
        return `
          <div class="backend-view-kanban-card">
            <div class="backend-view-kanban-media">
              <img src="${safeImage}" alt="${safeName}" onerror="this.onerror=null;this.src='${fallbackImage}'" />
            </div>
            <div class="backend-view-kanban-content">
              <p class="backend-view-kanban-name">${safeName}</p>
              <p class="backend-view-kanban-meta">${meta}</p>
              ${actions}
            </div>
          </div>
        `;
      }

      if (!entitiesCache.length) {
        listView.innerHTML = `<div class="backend-view-list-row"><strong>Sin registros</strong><span>No hay elementos</span><span>-</span></div>`;
        kanbanView.innerHTML = `
          <div class="backend-view-kanban-col"><h4>Pendiente</h4></div>
          <div class="backend-view-kanban-col"><h4>En revisión</h4></div>
          <div class="backend-view-kanban-col"><h4>Activo</h4></div>
        `;
        return;
      }

      listView.innerHTML = entitiesCache.map(function (item) {
        return `<div class="backend-view-list-row" data-entity-id="${item.id}"><strong>${item.name}</strong><span>${item.subtitle}</span><span>${item.status}</span></div>`;
      }).join("");

      function cardFor(item, extraLabel) {
        workflowStatus = item.status;
        return `<div data-entity-id="${item.id}">${makeCard(item.image || fallbackImage, item.name, [item.subtitle].concat(item.details || [], [extraLabel]))}</div>`;
      }

      const pending = entitiesCache.filter(function (item) { return item.status === "pendiente"; });
      const review = entitiesCache.filter(function (item) { return item.status === "en_revision"; });
      const active = entitiesCache.filter(function (item) { return item.status === "activo"; });

      kanbanView.innerHTML = `
        <div class="backend-view-kanban-col">
          <h4>Pendiente</h4>
          ${pending.map(function (item) { return cardFor(item, "Pendiente"); }).join("")}
        </div>
        <div class="backend-view-kanban-col">
          <h4>En revisión</h4>
          ${review.map(function (item) { return cardFor(item, "En revisión"); }).join("")}
        </div>
        <div class="backend-view-kanban-col">
          <h4>Activo</h4>
          ${active.map(function (item) { return cardFor(item, "Activo"); }).join("")}
        </div>
      `;
    }

    async function setView(mode) {
      buttons.forEach(function (btn) {
        btn.classList.toggle("active", btn.dataset.view === mode);
      });
      if (mode === "form") {
        formSections.forEach(function (section) { section.style.display = ""; });
        listPanel.classList.remove("active");
        kanbanPanel.classList.remove("active");
      } else if (mode === "list") {
        await ensureEntitiesLoaded(true);
        renderEntityViews();
        formSections.forEach(function (section) { section.style.display = "none"; });
        listPanel.classList.add("active");
        kanbanPanel.classList.remove("active");
      } else {
        await ensureEntitiesLoaded(true);
        renderEntityViews();
        formSections.forEach(function (section) { section.style.display = "none"; });
        listPanel.classList.remove("active");
        kanbanPanel.classList.add("active");
      }
      localStorage.setItem(selectedViewKey, mode);
    }

    buttons.forEach(function (btn) {
      btn.addEventListener("click", function () {
        void setView(btn.dataset.view);
      });
    });

    container.addEventListener("click", function (event) {
      const actionBtn = event.target && event.target.closest(".backend-kanban-action");
      if (actionBtn) {
        const nextStatus = actionBtn.getAttribute("data-next-status");
        if (nextStatus === "activo" && !canAuthorize) {
          return;
        }
        const entityNode = actionBtn.closest("[data-entity-id]");
        const entityId = entityNode ? entityNode.getAttribute("data-entity-id") : "";
        if (!entityId) return;
        entitiesCache = entitiesCache.map(function (item) {
          if (String(item.id) === String(entityId)) {
            return { ...item, status: nextStatus || item.status };
          }
          return item;
        });
        workflowMap[entityId] = nextStatus || workflowMap[entityId] || "pendiente";
        localStorage.setItem(workflowMapKey, JSON.stringify(workflowMap));
        renderEntityViews();
        return;
      }

      if (event.target && (event.target.closest(".backend-view-kanban-card") || event.target.closest(".backend-view-list-row"))) {
        void setView("form");
      }
    });

    void setView("form");
  }

  initEntityViews();

  pathNode.textContent = pathText;
  pathNode.title = pathText;
  if (toolsNode) {
    toolsNode.style.display = (isTemplateScreen || isVendorScreen || isStoreScreen) ? "inline-flex" : "none";
  }
  const newToolBtn = nav.querySelector('[data-action="new-content"]');
  if (newToolBtn) {
    newToolBtn.style.display = (isTemplateScreen || isStoreScreen || isVendorScreen) ? "inline-flex" : "none";
  }
  if (editNavbarBtn) {
    editNavbarBtn.style.display = isTemplateScreen ? "inline-flex" : "none";
  }

  let avatar = DEFAULT_AVATAR;
  try {
    const raw = localStorage.getItem("backend_template_sidebar_settings");
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && parsed.logo) avatar = parsed.logo;
    }
  } catch (_error) {}
  avatarNode.src = avatar;

  let navbarStyles = loadNavbarStyles();
  applyNavbarStyles(navbarStyles);
  bgInput.value = navbarStyles.bgColor;
  textInput.value = navbarStyles.textColor;
  svgInput.value = navbarStyles.svgColor;

  function setEditorOpen(open) {
    editor.classList.toggle("open", open);
  }

  function updateNavbarStyle(next) {
    navbarStyles = { ...navbarStyles, ...next };
    applyNavbarStyles(navbarStyles);
    saveNavbarStyles(navbarStyles);
    bgInput.value = navbarStyles.bgColor;
    textInput.value = navbarStyles.textColor;
    svgInput.value = navbarStyles.svgColor;
  }

  async function refreshUnreadNotifications() {
    try {
      const token = readStoredToken();
      if (!token) {
        notifCount.textContent = "0";
        return;
      }
      const normalizedToken = token.startsWith("Bearer ") ? token.slice(7) : token;
      const response = await fetch(`${prefix}/users/notifications/unread-count`, {
        headers: {
          Authorization: `Bearer ${normalizedToken}`,
        },
      });
      if (!response.ok) {
        notifCount.textContent = "0";
        return;
      }
      const data = await response.json();
      const count = Number(data && data.unread_count ? data.unread_count : 0);
      notifCount.textContent = String(count);
    } catch (_error) {
      notifCount.textContent = "0";
    }
  }

  notifBtn.addEventListener("click", function () {
    window.location.href = `${prefix}/configuracion`;
  });

  toolButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      if (!isTemplateScreen && !isVendorScreen && !isStoreScreen) return;
      const action = button.dataset.action;

      if (action === "save") {
        try {
          if (isTemplateScreen && templateRoot) {
            localStorage.setItem(screenStateKey, templateRoot.innerHTML);
          } else if (isVendorScreen) {
            localStorage.setItem(screenStateKey, JSON.stringify(collectVendorState()));
          } else if (isStoreScreen) {
            localStorage.setItem(screenStateKey, JSON.stringify(collectStoreState()));
            showActionMessage("Tienda guardada correctamente.", "success");
          }
        } catch (_error) {
          if (isStoreScreen) {
            showActionMessage("No se pudo guardar la tienda. Intenta nuevamente.", "error");
          }
        }
        return;
      }

      if (action === "edit-content") {
        if (isTemplateScreen) {
          setTemplateEditMode(!editMode);
        } else if (isVendorScreen) {
          setVendorEditMode(!editMode);
        } else if (isStoreScreen) {
          setStoreEditMode(!editMode);
        }
        return;
      }

      if (action === "delete-content") {
        if (isTemplateScreen && templateRoot) {
          templateRoot.innerHTML = `
            <h1>Contenido eliminado</h1>
            <p>Se limpió el contenido de esta vista. Puedes crear uno nuevo con el botón Nuevo.</p>
          `;
          setTemplateEditMode(false);
          localStorage.setItem(screenStateKey, templateRoot.innerHTML);
        } else if (isVendorScreen) {
          vendorFields.forEach(function (field) {
            if (field.id === "photoImage") {
              field.setAttribute("src", "/static/imagenes/tu-negocio.png");
            } else if (field.type === "checkbox") {
              field.checked = false;
            } else if (field.type === "file") {
              field.value = "";
            } else if (field.tagName === "SELECT") {
              field.selectedIndex = 0;
            } else if ("value" in field) {
              field.value = "";
            }
          });
          localStorage.setItem(screenStateKey, JSON.stringify(collectVendorState()));
        } else if (isStoreScreen) {
          storeFields.forEach(function (field) {
            if (field.id === "logoImage") {
              field.setAttribute("src", "/static/imagenes/tu-negocio.png");
            } else if (field.type === "file") {
              field.value = "";
            } else if ("value" in field) {
              field.value = "";
            }
          });
          localStorage.setItem(screenStateKey, JSON.stringify(collectStoreState()));
        }
        return;
      }

      if (action === "new-content") {
        if (isTemplateScreen && templateRoot) {
          localStorage.removeItem(screenStateKey);
          templateRoot.innerHTML = defaultTemplateHTML;
          setTemplateEditMode(false);
          return;
        }
        if (isVendorScreen) {
          localStorage.removeItem(screenStateKey);
          vendorFields.forEach(function (field) {
            if (field.id === "photoImage") {
              field.setAttribute("src", "/static/imagenes/tu-negocio.png");
            } else if (field.type === "checkbox") {
              field.checked = false;
            } else if (field.type === "file") {
              field.value = "";
            } else if (field.tagName === "SELECT") {
              field.selectedIndex = 0;
            } else if ("value" in field) {
              field.value = "";
            }
          });
          setVendorEditMode(true);
          return;
        }
        if (isStoreScreen) {
          localStorage.removeItem(screenStateKey);
          storeFields.forEach(function (field) {
            if (field.id === "logoImage") {
              field.setAttribute("src", "/static/imagenes/tu-negocio.png");
            } else if (field.type === "file") {
              field.value = "";
            } else if ("value" in field) {
              field.value = "";
            }
          });
          setStoreEditMode(true);
        }
      }
    });
  });

  editNavbarBtn.addEventListener("click", function (event) {
    event.stopPropagation();
    setEditorOpen(!editor.classList.contains("open"));
  });

  bgInput.addEventListener("input", function () {
    updateNavbarStyle({ bgColor: bgInput.value });
  });

  textInput.addEventListener("input", function () {
    updateNavbarStyle({ textColor: textInput.value });
  });

  svgInput.addEventListener("input", function () {
    updateNavbarStyle({ svgColor: svgInput.value });
  });

  resetBtn.addEventListener("click", function () {
    updateNavbarStyle({ ...DEFAULT_NAVBAR_STYLES });
  });

  avatarNode.addEventListener("click", function (event) {
    event.stopPropagation();
    menuNode.classList.toggle("open");
  });

  menuNode.addEventListener("click", function (event) {
    const target = event.target;
    if (!target || !target.dataset) return;

    if (target.dataset.action === "edit") {
      window.location.href = `${prefix}/agregar-usuario`;
      return;
    }

    if (target.dataset.action === "logout") {
      const keys = ["access_token", "token", "auth_token", "token_type"];
      keys.forEach(function (key) {
        localStorage.removeItem(key);
        sessionStorage.removeItem(key);
      });
      window.location.href = `${prefix}/backend/login`;
    }
  });

  document.addEventListener("click", function (event) {
    const insideNav = nav.contains(event.target);
    const insideEditor = editor.contains(event.target);
    if (!insideNav) menuNode.classList.remove("open");
    if (!insideNav && !insideEditor) setEditorOpen(false);
  });

  refreshUnreadNotifications();
  setInterval(refreshUnreadNotifications, 30000);
})();
