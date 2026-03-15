(function () {
  if (window.__backendSidebarCoreLoaded) return;
  window.__backendSidebarCoreLoaded = true;

  function readStoredToken() {
    const keys = ["access_token", "token", "auth_token"];
    for (let i = 0; i < keys.length; i += 1) {
      const key = keys[i];
      const localValue = window.localStorage.getItem(key);
      if (localValue) return localValue;
      const sessionValue = window.sessionStorage.getItem(key);
      if (sessionValue) return sessionValue;
    }
    return "";
  }

  function parsePayload(tokenValue) {
    const token = tokenValue.startsWith("Bearer ") ? tokenValue.slice(7) : tokenValue;
    const parts = token.split(".");
    if (parts.length < 2) return null;
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4);
    return JSON.parse(window.atob(padded));
  }

  function getUserType() {
    try {
      const token = readStoredToken();
      if (!token) return "";
      const payload = parsePayload(token);
      return (payload && payload.user_type) || "";
    } catch (_error) {
      return "";
    }
  }

  function isSuperadmin() {
    return getUserType() === "superadmin";
  }

  function isAdminOrSuperadmin() {
    const role = getUserType();
    return role === "superadmin" || role === "administrador";
  }

  function initBackendSidebarCore() {
    const btn = document.getElementById("menuBtn");
    const panel = document.getElementById("menuPanel");
    const personalizarItem = document.getElementById("personalizarItem");
    const configuracionItem = document.getElementById("configuracionItem");

    if (personalizarItem) {
      personalizarItem.style.display = isSuperadmin() ? "" : "none";
    }
    if (configuracionItem) {
      configuracionItem.style.display = isAdminOrSuperadmin() ? "" : "none";
    }

    if (!btn || !panel) return;
    if (btn.dataset.sidebarCoreInit === "1") return;
    btn.dataset.sidebarCoreInit = "1";

    function setOpen(open) {
      panel.classList.toggle("open", open);
      btn.setAttribute("aria-expanded", open ? "true" : "false");
      panel.setAttribute("aria-hidden", open ? "false" : "true");
    }

    btn.addEventListener("click", function () {
      const open = btn.getAttribute("aria-expanded") !== "true";
      setOpen(open);
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    });

    document.addEventListener("click", function (event) {
      if (!panel.contains(event.target) && !btn.contains(event.target)) {
        setOpen(false);
      }
    });
  }

  window.initBackendSidebarCore = initBackendSidebarCore;
  document.addEventListener("DOMContentLoaded", initBackendSidebarCore);
})();
