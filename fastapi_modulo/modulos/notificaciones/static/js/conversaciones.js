(() => {
  "use strict";

  const $ = (s) => document.querySelector(s);
  const pageEl = $(".wa-page");
  const shellEl = $(".wa-shell");
  const listEl = $("#wa-list");
  const searchEl = $("#wa-search");
  const messagesEl = $("#wa-messages");
  const formEl = $("#wa-form");
  const inputEl = $("#wa-input");
  const topkEl = $("#wa-topk");
  const topkWrap = $("#wa-topk-wrap");
  const notifyScopeWrap = $("#wa-notify-scope-wrap");
  const notifyScopeEl = $("#wa-notify-scope");
  const chatTitleEl = $("#wa-chat-title");
  const chatSubtitleEl = $("#wa-chat-subtitle");
  const chatAvatarEl = $("#wa-chat-avatar-el");
  const indexBtn = $("#wa-index-btn");
  const newBtn = $("#wa-new-btn");
  const newGroupBtn = $("#wa-new-group-btn");
  const notifyBtn = $("#wa-notify-btn");
  const indexStatusEl = $("#wa-index-status");
  const delBtn = $("#wa-del-conv");
  const modal = $("#wa-modal");
  const modalClose = $("#wa-modal-close");
  const modalSearch = $("#wa-modal-search");
  const modalList = $("#wa-modal-list");
  const groupModal = $("#wa-group-modal");
  const groupModalClose = $("#wa-group-modal-close");
  const groupNameEl = $("#wa-group-name");
  const groupSearchEl = $("#wa-group-search");
  const groupListEl = $("#wa-group-list");
  const groupCreateBtn = $("#wa-group-create");
  const groupSelectedEl = $("#wa-group-selected");
  const floatingStack = $("#wa-floating-stack");
  const sendBtn = $("#wa-send-btn");
  const avanAvatarUrl = String(pageEl?.getAttribute("data-wa-avatar") || "/templates/imagenes/lobo.jpg");

  let currentConvId = "";
  let currentConvType = "";
  let avanConvs = [];
  let dmConvs = [];
  let groupConvs = [];
  let allUsers = [];
  let sending = false;
  let moduleAccess = null;
  let hasInternalConversationAccess = false;
  let selectedGroupUsers = new Set();

  const getCookieValue = (name) => {
    const prefix = `${name}=`;
    const found = String(document.cookie || "")
      .split(";")
      .map((part) => part.trim())
      .find((part) => part.startsWith(prefix));
    return found ? decodeURIComponent(found.slice(prefix.length)) : "";
  };

  const currentUsername = String(getCookieValue("user_name") || "").trim().toLowerCase();

  const esc = (s) => String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");

  const initials = (s) => {
    const t = String(s ?? "").trim();
    if (!t) return "??";
    const p = t.split(/\s+/).filter(Boolean);
    return p.length === 1 ? p[0].slice(0, 2).toUpperCase() : (p[0][0] + p[1][0]).toUpperCase();
  };

  const avatarHtml = (label, imgUrl) => imgUrl
    ? `<img src="${esc(imgUrl)}" alt="${esc(label)}" loading="lazy" onerror="this.style.display='none'">`
    : esc(initials(label));

  const cleanAssistantText = (value) => String(value ?? "")
    .replace(/\s*\[S\d+\]/gi, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();

  const fmtTime = (iso) => {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      const now = new Date();
      if (d.toDateString() === now.toDateString()) {
        return d.toLocaleTimeString("es", { hour: "2-digit", minute: "2-digit" });
      }
      return d.toLocaleDateString("es", { day: "2-digit", month: "2-digit" });
    } catch {
      return String(iso).slice(0, 10);
    }
  };

  const dmConversationId = (otherUsername) => {
    const other = String(otherUsername || "").trim().toLowerCase();
    if (!other || !currentUsername) return "";
    const pair = [currentUsername, other].sort((a, b) => a.localeCompare(b));
    return `dm-${pair[0]}_${pair[1]}`;
  };

  const showIndexStatus = (text, isErr) => {
    if (!indexStatusEl) return;
    indexStatusEl.style.display = "block";
    indexStatusEl.textContent = String(text || "");
    indexStatusEl.style.color = isErr ? "#b42318" : "#54656f";
  };

  const showFloatingNotification = (title, message) => {
    if (!floatingStack) return;
    const card = document.createElement("article");
    card.className = "wa-floating-note";
    card.innerHTML = `<strong>${esc(title || "Notificación")}</strong><div>${esc(message || "")}</div>`;
    floatingStack.appendChild(card);
    requestAnimationFrame(() => card.classList.add("show"));
    window.setTimeout(() => {
      card.classList.remove("show");
      window.setTimeout(() => card.remove(), 220);
    }, 4200);
  };

  const renderNoAccess = (message) => {
    if (!shellEl) return;
    shellEl.innerHTML = `<article class="wa-empty-state">${esc(message || "Sin acceso a Conversaciones.")}</article>`;
  };

  const getUnifiedConversations = () => {
    const latestAvan = avanConvs.length ? avanConvs[0] : null;
    const avanEntry = {
      conv_id: latestAvan?.conv_id || "conv-avan",
      type: "avan",
      label: "AVAN",
      img: avanAvatarUrl,
      last_at: latestAvan?.last_at || "",
      last_message: latestAvan?.last_message || "Nueva conversación con AVAN",
      unread: 0,
    };
    return [avanEntry].concat(groupConvs).concat(dmConvs);
  };

  const renderList = () => {
    const term = (searchEl?.value ?? "").trim().toLowerCase();
    const filtered = getUnifiedConversations().filter((c) => {
      if (!term) return true;
      return `${c.label || ""} ${c.last_message || ""} ${c.conv_id || ""}`.toLowerCase().includes(term);
    });
    if (!filtered.length) {
      listEl.innerHTML = `<div class="wa-empty">Sin conversaciones. Usa + o 👥 para iniciar una.</div>`;
      return;
    }
    listEl.innerHTML = filtered.map((c) => {
      const active = currentConvId === c.conv_id ? "active" : "";
      const badge = c.unread > 0 ? `<span class="wa-unread-badge">${c.unread}</span>` : "";
      const subtitle = c.type === "group" ? "Grupo" : c.type === "dm" ? "Directo" : "IA";
      return `
        <button type="button" class="wa-item ${active}" data-id="${esc(c.conv_id)}" data-type="${esc(c.type)}">
          <div class="wa-item-avatar">${avatarHtml(c.label, c.img)}</div>
          <div class="wa-item-main">
            <div class="wa-item-top">
              <div class="wa-item-name">${esc(c.label)}</div>
              <div class="wa-item-time">${esc(fmtTime(c.last_at))} ${badge}</div>
            </div>
            <div class="wa-item-msg">${esc(c.last_message || subtitle)}</div>
          </div>
        </button>`;
    }).join("");
    listEl.querySelectorAll(".wa-item").forEach((btn) => {
      btn.addEventListener("click", () => openConv(btn.getAttribute("data-id"), btn.getAttribute("data-type")));
    });
  };

  const refreshModuleAccess = async () => {
    const res = await fetch("/api/v1/conversaciones/access");
    const data = await res.json();
    if (!res.ok || !data?.success) {
      if (res.status === 403) {
        hasInternalConversationAccess = false;
        moduleAccess = {
          role: "",
          can_create_groups: false,
          can_send_notifications: false,
          can_access_ai: true,
        };
        if (newGroupBtn) newGroupBtn.style.display = "none";
        return moduleAccess;
      }
      throw new Error((data && (data.error || data.detail)) || "Sin acceso");
    }
    moduleAccess = data.data || {};
    moduleAccess.can_access_ai = true;
    hasInternalConversationAccess = true;
    if (newGroupBtn) {
      newGroupBtn.style.display = moduleAccess.can_create_groups ? "inline-flex" : "none";
    }
    return moduleAccess;
  };

  const loadModuleUsers = async () => {
    if (!hasInternalConversationAccess) {
      allUsers = [];
      return;
    }
    const res = await fetch("/api/v1/conversaciones/users");
    const data = await res.json();
    if (!res.ok || !data?.success) {
      throw new Error((data && (data.error || data.detail)) || "No se pudieron cargar usuarios");
    }
    allUsers = Array.isArray(data.data) ? data.data : [];
  };

  const loadAvanConvs = async () => {
    try {
      const res = await fetch("/api/v1/ia/rag/conversations?limit=80");
      const data = await res.json();
      if (!data?.success) {
        avanConvs = [];
        return;
      }
      avanConvs = (data.data || []).map((item) => ({
        conv_id: item.conversation_id,
        type: "avan",
        label: "AVAN",
        img: avanAvatarUrl,
        last_at: item.last_at,
        last_message: item.last_answer || item.last_question || "",
        unread: 0,
      }));
    } catch {
      avanConvs = [];
    }
  };

  const loadDmConvs = async () => {
    if (!hasInternalConversationAccess) {
      dmConvs = [];
      return;
    }
    const res = await fetch("/api/v1/conversaciones/direct");
    const data = await res.json();
    if (!res.ok || !data?.success) {
      throw new Error((data && (data.error || data.detail)) || "No se pudieron cargar conversaciones directas");
    }
    dmConvs = (data.data || []).map((item) => {
      const user = allUsers.find((entry) => entry.username === item.other_user);
      return {
        conv_id: item.conversation_id,
        type: "dm",
        label: user?.full_name || item.other_user || "Usuario",
        img: user?.imagen || "",
        last_at: item.last_at,
        last_message: item.last_message || "",
        unread: item.unread || 0,
      };
    });
  };

  const loadGroupConvs = async () => {
    if (!hasInternalConversationAccess) {
      groupConvs = [];
      return;
    }
    const res = await fetch("/api/v1/conversaciones/groups");
    const data = await res.json();
    if (!res.ok || !data?.success) {
      throw new Error((data && (data.error || data.detail)) || "No se pudieron cargar grupos");
    }
    groupConvs = (data.data || []).map((item) => ({
      conv_id: item.conversation_id,
      type: "group",
      label: item.group_name || "Grupo",
      img: "",
      last_at: item.last_at,
      last_message: item.last_message || "",
      unread: item.unread || 0,
      members: item.member_usernames || [],
    }));
  };

  const loadAll = async () => {
    await Promise.all([loadAvanConvs(), loadDmConvs(), loadGroupConvs()]);
    renderList();
  };

  const renderMessages = (rows, type) => {
    if (!rows?.length) {
      messagesEl.innerHTML = '<div class="wa-empty">No hay mensajes aún. Escribe el primero.</div>';
      return;
    }
    messagesEl.innerHTML = rows.map((row) => {
      const isMine = type === "avan" ? String(row.message_type || "").toLowerCase() === "user" : row.is_mine === true;
      const css = isMine ? "wa-msg wa-msg--out" : "wa-msg wa-msg--in";
      const meta = isMine
        ? (fmtTime(row.created_at) || "Tú")
        : (type === "avan" ? "AVAN" : esc(row.from_username || ""));
      const body = !isMine && type === "avan"
        ? cleanAssistantText(row.message_text ?? row.message ?? "")
        : String(row.message_text ?? row.message ?? "");
      return `<div class="${css}"><div class="wa-msg-body">${esc(body)}</div><div class="wa-msg-meta">${meta}</div></div>`;
    }).join("");
    messagesEl.scrollTop = messagesEl.scrollHeight;
  };

  const updateHeaderActions = () => {
    topkWrap.style.display = currentConvType === "avan" ? "flex" : "none";
    delBtn.style.display = hasInternalConversationAccess && (currentConvType === "dm" || currentConvType === "group") ? "inline-flex" : "none";
    notifyBtn.style.display = moduleAccess?.can_send_notifications && hasInternalConversationAccess && (currentConvType === "dm" || currentConvType === "group")
      ? "inline-flex" : "none";
    if (notifyScopeWrap && notifyScopeEl) {
      var maxScope = String(moduleAccess?.notification_scope || "").trim().toLowerCase();
      var allowedScopes = ["conversation"];
      if (maxScope === "department" || maxScope === "company") allowedScopes.push("department");
      if (maxScope === "company") allowedScopes.push("company");
      Array.from(notifyScopeEl.options).forEach((option) => {
        option.hidden = allowedScopes.indexOf(String(option.value || "").trim().toLowerCase()) === -1;
      });
      if (allowedScopes.indexOf(String(notifyScopeEl.value || "").trim().toLowerCase()) === -1) {
        notifyScopeEl.value = allowedScopes[0];
      }
      notifyScopeWrap.style.display = moduleAccess?.can_send_notifications && hasInternalConversationAccess && (currentConvType === "dm" || currentConvType === "group")
        ? "flex"
        : "none";
    }
    if (newBtn) {
      newBtn.style.display = hasInternalConversationAccess ? "inline-flex" : "none";
    }
  };

  const startDmWithUser = (username) => {
    const user = allUsers.find((item) => item.username === username);
    const convId = dmConversationId(username);
    if (!convId) return;
    if (!dmConvs.find((item) => item.conv_id === convId)) {
      dmConvs.unshift({
        conv_id: convId,
        type: "dm",
        label: user?.full_name || username,
        img: user?.imagen || "",
        last_at: "",
        last_message: "",
        unread: 0,
      });
    }
    currentConvId = convId;
    currentConvType = "dm";
    chatTitleEl.textContent = user?.full_name || username;
    chatSubtitleEl.textContent = "Mensaje directo";
    chatAvatarEl.innerHTML = avatarHtml(user?.full_name || username, user?.imagen || "");
    updateHeaderActions();
    renderMessages([], "dm");
    renderList();
  };

  const openConv = async (convId, type) => {
    currentConvId = convId || "";
    currentConvType = type || "";
    renderList();
    updateHeaderActions();
    let label = convId;
    let img = "";
    if (type === "avan") {
      label = "AVAN";
      img = avanAvatarUrl;
    } else if (type === "group") {
      const group = groupConvs.find((item) => item.conv_id === convId);
      label = group?.label || "Grupo";
    } else {
      const direct = dmConvs.find((item) => item.conv_id === convId);
      label = direct?.label || convId;
      img = direct?.img || "";
    }
    chatTitleEl.textContent = label || "Conversación";
    chatSubtitleEl.textContent = type === "avan" ? "Agente IA AVAN" : type === "group" ? "Grupo" : "Mensaje directo";
    chatAvatarEl.innerHTML = avatarHtml(label, img);
    if (type === "avan" && !avanConvs.find((item) => item.conv_id === convId)) {
      renderMessages([{ message_text: "Conversación iniciada. Escribe tu mensaje.", is_mine: false, created_at: "" }], "avan");
      return;
    }
    try {
      const url = type === "avan"
        ? `/api/v1/ia/rag/conversations/${encodeURIComponent(convId)}`
        : type === "group"
          ? `/api/v1/conversaciones/groups/${encodeURIComponent(convId)}`
          : `/api/v1/conversaciones/direct/${encodeURIComponent(convId)}`;
      const res = await fetch(url);
      const data = await res.json();
      if (!res.ok || !data?.success) {
        throw new Error((data && (data.error || data.detail)) || "No se pudo cargar la conversación");
      }
      renderMessages(data.data || [], type);
    } catch (error) {
      renderMessages([{ message_text: error?.message || "No se pudo cargar.", is_mine: false, created_at: "" }], type);
    }
    await loadAll();
  };

  const sendMsg = async (event) => {
    event.preventDefault();
    const txt = String(inputEl?.value || "").trim();
    if (!txt || sending) return;
    if (!currentConvId) {
      window.alert("Selecciona una conversación primero.");
      return;
    }
    sending = true;
    sendBtn.disabled = true;
    inputEl.value = "";
    try {
      if (currentConvType === "avan") {
        const res = await fetch("/api/v1/ia/rag/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ conversation_id: currentConvId, message: txt, top_k: Number(topkEl?.value || 6) }),
        });
        const data = await res.json();
        if (!res.ok || !data?.success) throw new Error((data && (data.error || data.detail)) || "No se pudo enviar");
        currentConvId = data.data?.conversation_id || currentConvId;
      } else if (currentConvType === "group") {
        const res = await fetch(`/api/v1/conversaciones/groups/${encodeURIComponent(currentConvId)}/send`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: txt }),
        });
        const data = await res.json();
        if (!res.ok || !data?.success) throw new Error((data && (data.error || data.detail)) || "No se pudo enviar");
      } else {
        const res = await fetch("/api/v1/conversaciones/direct/send", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ conversation_id: currentConvId, message: txt }),
        });
        const data = await res.json();
        if (!res.ok || !data?.success) throw new Error((data && (data.error || data.detail)) || "No se pudo enviar");
        currentConvId = data.data?.conversation_id || currentConvId;
      }
      await openConv(currentConvId, currentConvType);
    } catch (error) {
      window.alert(error?.message || "No se pudo enviar");
      inputEl.value = txt;
    } finally {
      sending = false;
      sendBtn.disabled = false;
      inputEl.focus();
    }
  };

  const deleteConv = async () => {
    if (!currentConvId || (currentConvType !== "dm" && currentConvType !== "group")) return;
    if (!window.confirm("¿Eliminar esta conversación?")) return;
    try {
      const url = currentConvType === "group"
        ? `/api/v1/conversaciones/groups/${encodeURIComponent(currentConvId)}`
        : `/api/v1/conversaciones/direct/${encodeURIComponent(currentConvId)}`;
      const res = await fetch(url, { method: "DELETE" });
      const data = await res.json();
      if (!res.ok || !data?.success) {
        throw new Error((data && (data.error || data.detail)) || "No se pudo eliminar");
      }
      currentConvId = "";
      currentConvType = "";
      chatTitleEl.textContent = "Selecciona una conversación";
      chatSubtitleEl.textContent = "—";
      chatAvatarEl.innerHTML = "AV";
      updateHeaderActions();
      messagesEl.innerHTML = '<div class="wa-empty">Conversación eliminada.</div>';
      await loadAll();
    } catch (error) {
      window.alert(error?.message || "No se pudo eliminar");
    }
  };

  const openUserModal = () => {
    modal.style.display = "flex";
    modalSearch.value = "";
    renderModalList();
    modalSearch.focus();
  };

  const renderModalList = () => {
    const term = String(modalSearch?.value || "").trim().toLowerCase();
    const filtered = allUsers.filter((user) => !term || `${user.full_name} ${user.username}`.toLowerCase().includes(term));
    if (!filtered.length) {
      modalList.innerHTML = '<li class="wa-empty">Sin usuarios encontrados.</li>';
      return;
    }
    modalList.innerHTML = filtered.map((user) => `
      <li class="wa-modal-user" data-username="${esc(user.username)}">
        <div class="wa-modal-avatar">${avatarHtml(user.full_name || user.username, user.imagen)}</div>
        <div class="wa-modal-info">
          <strong>${esc(user.full_name || user.username)}</strong>
          <small>${esc(user.conversation_access?.role || user.role || user.username)}</small>
        </div>
      </li>`).join("");
    modalList.querySelectorAll(".wa-modal-user").forEach((item) => {
      item.addEventListener("click", () => {
        const username = item.getAttribute("data-username");
        modal.style.display = "none";
        if (username) startDmWithUser(username);
      });
    });
  };

  const openGroupModal = () => {
    if (!moduleAccess?.can_create_groups) return;
    selectedGroupUsers = new Set();
    groupModal.style.display = "flex";
    groupNameEl.value = "";
    groupSearchEl.value = "";
    renderGroupList();
    groupNameEl.focus();
  };

  const renderGroupList = () => {
    const term = String(groupSearchEl?.value || "").trim().toLowerCase();
    const filtered = allUsers.filter((user) => !term || `${user.full_name} ${user.username}`.toLowerCase().includes(term));
    if (!filtered.length) {
      groupListEl.innerHTML = '<li class="wa-empty">Sin usuarios encontrados.</li>';
      return;
    }
    groupListEl.innerHTML = filtered.map((user) => `
      <li class="wa-modal-user">
        <div class="wa-modal-avatar">${avatarHtml(user.full_name || user.username, user.imagen)}</div>
        <div class="wa-modal-info">
          <strong>${esc(user.full_name || user.username)}</strong>
          <small>${esc(user.username)}</small>
        </div>
        <input type="checkbox" data-group-user="${esc(user.username)}" ${selectedGroupUsers.has(user.username) ? "checked" : ""}>
      </li>`).join("");
    groupListEl.querySelectorAll("input[type='checkbox'][data-group-user]").forEach((checkbox) => {
      checkbox.addEventListener("change", () => {
        const username = checkbox.getAttribute("data-group-user");
        if (!username) return;
        if (checkbox.checked) selectedGroupUsers.add(username);
        else selectedGroupUsers.delete(username);
        groupSelectedEl.textContent = `${selectedGroupUsers.size} seleccionados`;
      });
    });
    groupSelectedEl.textContent = `${selectedGroupUsers.size} seleccionados`;
  };

  const createGroup = async () => {
    const groupName = String(groupNameEl?.value || "").trim();
    const memberUsernames = Array.from(selectedGroupUsers);
    if (!groupName) {
      window.alert("Escribe un nombre para el grupo.");
      return;
    }
    if (!memberUsernames.length) {
      window.alert("Selecciona al menos un usuario.");
      return;
    }
    groupCreateBtn.disabled = true;
    try {
      const res = await fetch("/api/v1/conversaciones/groups", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ group_name: groupName, member_usernames: memberUsernames }),
      });
      const data = await res.json();
      if (!res.ok || !data?.success) {
        throw new Error((data && (data.error || data.detail)) || "No se pudo crear el grupo");
      }
      groupModal.style.display = "none";
      await loadAll();
      await openConv(data.data?.conversation_id, "group");
    } catch (error) {
      window.alert(error?.message || "No se pudo crear el grupo");
    } finally {
      groupCreateBtn.disabled = false;
    }
  };

  const sendModuleNotification = async () => {
    if (!moduleAccess?.can_send_notifications || !currentConvId || (currentConvType !== "dm" && currentConvType !== "group")) return;
    const message = window.prompt("Mensaje de notificación");
    if (!message || !message.trim()) return;
    const selectedScope = String(notifyScopeEl?.value || "conversation").trim().toLowerCase() || "conversation";
    try {
      const res = await fetch("/api/v1/conversaciones/notifications/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ conversation_id: currentConvId, message: message.trim(), scope: selectedScope }),
      });
      const data = await res.json();
      if (!res.ok || !data?.success) {
        throw new Error((data && (data.error || data.detail)) || "No se pudo enviar la notificación");
      }
      showFloatingNotification("Notificación enviada", message.trim());
    } catch (error) {
      window.alert(error?.message || "No se pudo enviar la notificación");
    }
  };

  const refreshIndexStatus = async () => {
    try {
      const res = await fetch("/api/v1/ia/rag/index-status");
      const data = await res.json();
      if (!data?.success) {
        if (res.status === 403) indexBtn.disabled = true;
        return;
      }
      const info = data.data || {};
      showIndexStatus(`Índice: ${info.documents ?? 0} docs · ${info.chunks ?? 0} chunks`);
    } catch (error) {
      showIndexStatus(error?.message || "Error índice", true);
    }
  };

  const runIndex = async () => {
    indexBtn.disabled = true;
    showIndexStatus("Indexando documentos…");
    try {
      const res = await fetch("/api/v1/ia/rag/index-documents", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ limit: 500 }),
      });
      const data = await res.json();
      if (!res.ok || !data?.success) throw new Error((data && (data.error || data.detail)) || "Error");
      const info = data.data || {};
      showIndexStatus(`Indexación lista: ${info.indexed_documents ?? 0} docs, ${info.indexed_chunks ?? 0} chunks`);
      await loadAll();
    } catch (error) {
      showIndexStatus(error?.message || "Error", true);
    } finally {
      indexBtn.disabled = false;
      refreshIndexStatus();
    }
  };

  const refreshUnread = async () => {
    if (!hasInternalConversationAccess) return;
    try {
      const res = await fetch("/api/v1/conversaciones/unread-count");
      const data = await res.json();
      const n = data?.data?.count ?? 0;
      if (newBtn) {
        newBtn.setAttribute("title", n > 0 ? `Nueva conversación · ${n} pendientes` : "Nueva conversación");
      }
    } catch {}
  };

  const pollCurrentConversation = async () => {
    if (!hasInternalConversationAccess) return;
    if (!currentConvId || (currentConvType !== "dm" && currentConvType !== "group")) return;
    try {
      const url = currentConvType === "group"
        ? `/api/v1/conversaciones/groups/${encodeURIComponent(currentConvId)}`
        : `/api/v1/conversaciones/direct/${encodeURIComponent(currentConvId)}`;
      const res = await fetch(url);
      const data = await res.json();
      if (data?.success) renderMessages(data.data || [], currentConvType);
    } catch {}
  };

  const pollFloatingNotifications = async () => {
    if (!hasInternalConversationAccess) return;
    try {
      const res = await fetch("/api/v1/conversaciones/notifications/inbox");
      const data = await res.json();
      if (!res.ok || !data?.success) return;
      (data.data || []).forEach((item) => {
        showFloatingNotification(`Mensaje de ${item.from_username || "Sistema"}`, item.message_text || "");
      });
    } catch {}
  };

  searchEl?.addEventListener("input", renderList);
  formEl?.addEventListener("submit", sendMsg);
  indexBtn?.addEventListener("click", runIndex);
  newBtn?.addEventListener("click", openUserModal);
  newGroupBtn?.addEventListener("click", openGroupModal);
  notifyBtn?.addEventListener("click", sendModuleNotification);
  delBtn?.addEventListener("click", deleteConv);
  modalClose?.addEventListener("click", () => { modal.style.display = "none"; });
  modal?.addEventListener("click", (event) => { if (event.target === modal) modal.style.display = "none"; });
  modalSearch?.addEventListener("input", renderModalList);
  groupModalClose?.addEventListener("click", () => { groupModal.style.display = "none"; });
  groupModal?.addEventListener("click", (event) => { if (event.target === groupModal) groupModal.style.display = "none"; });
  groupSearchEl?.addEventListener("input", renderGroupList);
  groupCreateBtn?.addEventListener("click", createGroup);

  (async () => {
    try {
      await refreshModuleAccess();
      await loadModuleUsers();
    } catch (error) {
      renderNoAccess(error?.message || "Sin acceso a Conversaciones.");
      return;
    }

    await loadAll();
    refreshIndexStatus();
    refreshUnread();
    if (hasInternalConversationAccess) {
      await pollFloatingNotifications();
    }

    if (!currentConvId) {
      const first = getUnifiedConversations()[0];
      if (first?.conv_id) {
        await openConv(first.conv_id, first.type);
      }
    }

    if (hasInternalConversationAccess) {
      window.setInterval(loadAll, 12000);
      window.setInterval(refreshUnread, 15000);
      window.setInterval(pollCurrentConversation, 8000);
      window.setInterval(pollFloatingNotifications, 10000);
    }
    window.setInterval(refreshIndexStatus, 30000);
  })();
})();
