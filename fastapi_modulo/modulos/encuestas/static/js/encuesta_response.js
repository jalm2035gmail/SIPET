(function () {
  const root = document.getElementById("enc-response-root");
  if (!root) return;

  function parseBootstrap() {
    try {
      return JSON.parse(root.dataset.encResponseBootstrap || "{}");
    } catch (error) {
      console.warn("encuestas response bootstrap invalido", error);
      return {};
    }
  }

  const state = {
    session: parseBootstrap(),
    currentStep: 0,
    answers: {},
    timerId: null,
  };
  const apiMAIN = state.session.access_mode === "public" ? "/api/public/encuestas" : "/api/encuestas";

  const startScreen = document.getElementById("enc-response-start");
  const formScreen = document.getElementById("enc-response-form-screen");
  const closedScreen = document.getElementById("enc-response-closed");
  const titleNode = document.getElementById("enc-response-title");
  const descriptionNode = document.getElementById("enc-response-description");
  const startCopy = document.getElementById("enc-response-start-copy");
  const startMeta = document.getElementById("enc-response-start-meta");
  const eval360Meta = document.getElementById("enc-response-360-meta");
  const startButton = document.getElementById("enc-response-start-btn");
  const progressBar = document.getElementById("enc-response-progress-bar");
  const progressText = document.getElementById("enc-response-progress-text");
  const stepsNode = document.getElementById("enc-response-steps");
  const messageNode = document.getElementById("enc-response-message");
  const stepLabelNode = document.getElementById("enc-response-step-label");
  const sectionTitleNode = document.getElementById("enc-response-section-title");
  const sectionDescriptionNode = document.getElementById("enc-response-section-description");
  const questionsNode = document.getElementById("enc-response-questions");
  const prevButton = document.getElementById("enc-response-prev");
  const saveButton = document.getElementById("enc-response-save");
  const nextButton = document.getElementById("enc-response-next");
  const submitButton = document.getElementById("enc-response-submit");
  const formNode = document.getElementById("enc-response-form");
  const closedCopy = document.getElementById("enc-response-closed-copy");
  const closedScore = document.getElementById("enc-response-closed-score");
  const quizCard = document.getElementById("enc-response-quiz-card");
  const attemptsMeta = document.getElementById("enc-response-attempts-meta");
  const timerWrap = document.getElementById("enc-response-timer-wrap");
  const timerNode = document.getElementById("enc-response-timer");

  function quiz() {
    return state.session.quiz || {};
  }

  function evaluation360() {
    return state.session.evaluation_360 || {};
  }

  function fetchJSON(url, options) {
    return fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    }).then(async (response) => {
      const text = await response.text();
      const data = text ? JSON.parse(text) : null;
      if (!response.ok) {
        const detail = data && data.detail ? data.detail : data;
        throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
      }
      return data;
    });
  }

  function setMessage(message, isError) {
    messageNode.textContent = message || "";
    messageNode.style.color = isError ? "#991b1b" : "";
  }

  function sections() {
    return Array.isArray(state.session.sections) ? state.session.sections : [];
  }

  function responseData() {
    return state.session.response || {};
  }

  function isSubmitted() {
    return responseData().status === "submitted";
  }

  function refreshAnswersFromSession() {
    state.answers = { ...(responseData().answers_json || {}) };
  }

  function showScreen(mode) {
    startScreen.classList.toggle("is-active", mode === "start");
    formScreen.classList.toggle("is-active", mode === "form");
    closedScreen.classList.toggle("is-active", mode === "closed");
  }

  function formatDate(value) {
    if (!value) return "Sin fecha";
    return String(value).replace("T", " ").slice(0, 16);
  }

  function updateChrome() {
    const instance = state.session.instance || {};
    titleNode.textContent = instance.nombre || "Encuesta";
    descriptionNode.textContent = instance.descripcion || "Responde cada sección y guarda tu progreso cuando lo necesites.";
    progressBar.style.width = `${responseData().completion_pct || 0}%`;
    progressText.textContent = `${responseData().completion_pct || 0}%`;
    const quizState = quiz();
    if (quizState.is_quiz) {
      quizCard.style.display = "";
      attemptsMeta.innerHTML = [
        `<div><strong>Intento:</strong> ${quizState.current_attempt_number || 1} / ${quizState.max_attempts || 1}</div>`,
        `<div><strong>Estrategia:</strong> ${quizState.attempt_strategy === "last" ? "Último intento" : "Mejor intento"}</div>`,
        quizState.passing_score != null ? `<div><strong>Puntaje aprobatorio:</strong> ${quizState.passing_score}</div>` : "",
      ].filter(Boolean).join("");
      timerWrap.style.display = quizState.timer_seconds ? "" : "none";
    } else {
      quizCard.style.display = "none";
    }
  }

  function renderStartScreen() {
    const response = responseData();
    const instance = state.session.instance || {};
    const evalState = evaluation360();
    const modeText = state.session.access_mode === "public" ? "enlace público" : "acceso autenticado";
    startCopy.textContent = response.status === "submitted"
      ? "Esta encuesta ya fue enviada. Puedes revisar el estado final a continuación."
      : "Responde la encuesta por secciones. Puedes avanzar, volver y guardar borrador antes de enviarla.";
    if (quiz().is_quiz) {
      startCopy.textContent = response.status === "submitted" && quiz().can_retry
        ? "Tu último intento ya fue enviado. Se habilitó un nuevo intento para continuar con el quiz."
        : `${startCopy.textContent} Este quiz controla intentos y puede incluir límite de tiempo.`;
    }
    startMeta.innerHTML = [
      `<div><strong>Acceso:</strong> ${modeText}</div>`,
      `<div><strong>Disponibilidad:</strong> ${formatDate(instance.schedule_start_at)} a ${formatDate(instance.schedule_end_at)}</div>`,
      response.last_saved_at ? `<div><strong>Último guardado:</strong> ${formatDate(response.last_saved_at)}</div>` : "",
      state.session.draft_exists ? "<div><strong>Borrador detectado:</strong> retomaremos tus respuestas guardadas.</div>" : "",
      quiz().is_quiz ? `<div><strong>Intentos usados:</strong> ${quiz().attempts_used || 0} de ${quiz().max_attempts || 1}</div>` : "",
      quiz().remaining_attempts > 0 ? `<div><strong>Intentos restantes después de este:</strong> ${quiz().remaining_attempts}</div>` : "",
    ].filter(Boolean).join("");
    startButton.textContent = response.status === "submitted"
      ? "Ver cierre"
      : state.session.draft_exists
        ? "Continuar borrador"
        : "Comenzar";
    if (evalState.is_360 && evalState.current && eval360Meta) {
      eval360Meta.style.display = "";
      eval360Meta.innerHTML = [
        `<div><strong>Evaluando a:</strong> ${escapeHtml(evalState.current.evaluatee_name_snapshot || evalState.current.evaluatee_key || "")}</div>`,
        `<div><strong>Relación:</strong> ${escapeHtml(evalState.current.relationship_type || "sin dato")}</div>`,
        `<div><strong>Progreso 360:</strong> ${evalState.completed || 0} de ${evalState.total || 0} relaciones completadas</div>`,
      ].join("");
    } else if (eval360Meta) {
      eval360Meta.style.display = "none";
      eval360Meta.innerHTML = "";
    }
  }

  function formatDuration(totalSeconds) {
    const safe = Math.max(0, Number(totalSeconds) || 0);
    const minutes = String(Math.floor(safe / 60)).padStart(2, "0");
    const seconds = String(safe % 60).padStart(2, "0");
    return `${minutes}:${seconds}`;
  }

  function stopTimer() {
    if (state.timerId) {
      window.clearInterval(state.timerId);
      state.timerId = null;
    }
  }

  async function forceSubmitByTimer() {
    stopTimer();
    try {
      await submitSurvey();
    } catch (error) {
      setMessage(error.message, true);
      renderClosedScreen();
      showScreen("closed");
    }
  }

  function startTimer() {
    stopTimer();
    const quizState = quiz();
    const startedAt = responseData().started_at;
    if (!quizState.is_quiz || !quizState.timer_seconds || !startedAt || isSubmitted()) {
      if (timerNode) timerNode.textContent = "00:00";
      return;
    }
    const deadline = new Date(startedAt).getTime() + (Number(quizState.timer_seconds) * 1000);
    const tick = () => {
      const remaining = Math.max(0, Math.floor((deadline - Date.now()) / 1000));
      timerNode.textContent = formatDuration(remaining);
      if (remaining <= 0) {
        forceSubmitByTimer();
      }
    };
    tick();
    state.timerId = window.setInterval(tick, 1000);
  }

  function renderSteps() {
    stepsNode.innerHTML = sections().map((section, index) => {
      const current = index === state.currentStep ? "is-current" : "";
      const answered = (section.questions || []).filter((question) => hasAnswer(question.id)).length;
      return `
        <button type="button" class="enc-response-step ${current}" data-enc-step="${index}">
          <span>${index + 1}. ${section.titulo}</span>
          <small>${answered}/${(section.questions || []).length} respondidas</small>
        </button>
      `;
    }).join("");
  }

  function hasAnswer(questionId) {
    const value = state.answers[String(questionId)];
    if (Array.isArray(value)) return value.length > 0;
    return value !== null && value !== undefined && String(value).trim() !== "";
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function fileMeta(questionId) {
    const value = state.answers[String(questionId)];
    return value && typeof value === "object" ? value : {};
  }

  function matrixValue(questionId, rowKey) {
    const value = state.answers[String(questionId)];
    if (!value || typeof value !== "object" || Array.isArray(value)) return "";
    return String(value[rowKey] || "");
  }

  function rankingValue(questionId) {
    const value = state.answers[String(questionId)];
    return Array.isArray(value) ? value : [];
  }

  function renderMatrix(question, mode) {
    const rows = Array.isArray(question.options) ? question.options : [];
    const columns = Array.isArray((question.config_json || {}).columns) ? question.config_json.columns : [];
    const leftLabel = escapeHtml((question.config_json || {}).left_label || "");
    const rightLabel = escapeHtml((question.config_json || {}).right_label || "");
    return `
      <div class="enc-response-matrix">
        ${leftLabel || rightLabel ? `<div class="enc-question-meta">${leftLabel}${leftLabel && rightLabel ? " / " : ""}${rightLabel}</div>` : ""}
        <table class="enc-table">
          <thead>
            <tr>
              <th>Ítem</th>
              ${columns.map((column) => `<th>${escapeHtml(column.label)}</th>`).join("")}
            </tr>
          </thead>
          <tbody>
            ${rows.map((row) => `
              <tr>
                <td>${escapeHtml(row.label)}</td>
                ${columns.map((column) => `
                  <td>
                    <input
                      type="radio"
                      name="enc-matrix-${question.id}-${escapeHtml(row.value)}"
                      data-enc-matrix="${question.id}"
                      data-row="${escapeHtml(row.value)}"
                      value="${escapeHtml(column.value)}"
                      ${matrixValue(question.id, row.value) === String(column.value) ? "checked" : ""}
                    >
                  </td>
                `).join("")}
              </tr>
            `).join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  function renderRanking(question) {
    const current = rankingValue(question.id);
    const options = Array.isArray(question.options) ? question.options : [];
    const ranked = current.map((value) => options.find((option) => String(option.value) === String(value))).filter(Boolean);
    const available = options.filter((option) => !current.includes(option.value));
    const all = ranked.concat(available);
    return `
      <div class="enc-response-ranking" data-enc-ranking="${question.id}">
        ${all.map((option, index) => {
          const isRanked = index < ranked.length;
          return `
            <div class="enc-question-meta" style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
              <span style="min-width:24px;font-weight:700;">${isRanked ? index + 1 : "-"}</span>
              <span style="flex:1;">${escapeHtml(option.label)}</span>
              <button type="button" class="enc-mini-btn" data-enc-rank-up="${question.id}" data-value="${escapeHtml(option.value)}">↑</button>
              <button type="button" class="enc-mini-btn" data-enc-rank-down="${question.id}" data-value="${escapeHtml(option.value)}">↓</button>
            </div>
          `;
        }).join("")}
      </div>
    `;
  }

  function renderQuestion(question) {
    const value = state.answers[String(question.id)];
    const required = question.is_required ? '<span class="enc-response-required">*</span>' : "";
    const options = Array.isArray(question.options) ? question.options : [];
    let fieldHtml = "";
    if (question.question_type === "long_text") {
      fieldHtml = `<textarea class="enc-input enc-textarea" data-enc-question="${question.id}" rows="5">${escapeHtml(value || "")}</textarea>`;
    } else if (["short_text", "word_cloud"].includes(question.question_type)) {
      fieldHtml = `<input class="enc-input" data-enc-question="${question.id}" type="text" value="${escapeHtml(value || "")}">`;
    } else if (question.question_type === "multiple_choice") {
      fieldHtml = options.map((option) => {
        const checked = Array.isArray(value) && value.includes(option.value) ? "checked" : "";
        return `<label class="enc-preview-choice"><input type="checkbox" data-enc-question="${question.id}" value="${escapeHtml(option.value)}" ${checked}> <span>${escapeHtml(option.label)}</span></label>`;
      }).join("");
    } else if (question.question_type === "ranking") {
      fieldHtml = renderRanking(question);
    } else if (["matrix", "likert_scale", "semantic_differential"].includes(question.question_type)) {
      fieldHtml = renderMatrix(question, question.question_type);
    } else if (["single_choice", "live_poll_single_choice", "yes_no", "true_false", "quiz_single_choice", "dropdown", "image_choice"].includes(question.question_type)) {
      if (question.question_type === "dropdown") {
        fieldHtml = `
          <select class="enc-input enc-select" data-enc-question="${question.id}">
            <option value="">Selecciona una opción</option>
            ${options.map((option) => `<option value="${escapeHtml(option.value)}" ${String(value || "") === String(option.value) ? "selected" : ""}>${escapeHtml(option.label)}</option>`).join("")}
          </select>
        `;
      } else if (question.question_type === "image_choice") {
        fieldHtml = `<div class="enc-response-image-choice">${options.map((option) => {
          const checked = String(value || "") === String(option.value) ? "checked" : "";
          return `<label class="enc-preview-choice" style="display:flex;align-items:center;gap:12px;padding:12px;border:1px solid rgba(15,23,42,0.1);border-radius:14px;"><input type="radio" name="enc-question-${question.id}" data-enc-question="${question.id}" value="${escapeHtml(option.value)}" ${checked}> <span>${escapeHtml(option.label)}</span></label>`;
        }).join("")}</div>`;
      } else {
      fieldHtml = options.map((option) => {
        const checked = String(value || "") === String(option.value) ? "checked" : "";
        return `<label class="enc-preview-choice"><input type="radio" name="enc-question-${question.id}" data-enc-question="${question.id}" value="${escapeHtml(option.value)}" ${checked}> <span>${escapeHtml(option.label)}</span></label>`;
      }).join("");
      }
    } else if (["scale_1_5", "live_scale_1_5", "nps_0_10"].includes(question.question_type)) {
      fieldHtml = `<div class="enc-response-scale">${options.map((option) => {
        const active = String(value || "") === String(option.value) ? "is-active" : "";
        return `<button type="button" class="enc-preview-scale ${active}" data-enc-scale="${question.id}" data-value="${escapeHtml(option.value)}">${escapeHtml(option.label)}</button>`;
      }).join("")}</div>`;
    } else if (question.question_type === "slider") {
      const config = question.config_json || {};
      const currentValue = value == null || value === "" ? String(config.min ?? 0) : String(value);
      fieldHtml = `
        <div>
          <input class="enc-input" data-enc-question="${question.id}" type="range" min="${escapeHtml(config.min ?? 0)}" max="${escapeHtml(config.max ?? 10)}" step="${escapeHtml(config.step ?? 1)}" value="${escapeHtml(currentValue)}">
          <div class="enc-question-meta">${escapeHtml(config.min_label || "Mínimo")} · <strong>${escapeHtml(currentValue)}</strong> · ${escapeHtml(config.max_label || "Máximo")}</div>
        </div>
      `;
    } else if (question.question_type === "date") {
      fieldHtml = `<input class="enc-input" data-enc-question="${question.id}" type="date" value="${escapeHtml(value || "")}">`;
    } else if (question.question_type === "time") {
      fieldHtml = `<input class="enc-input" data-enc-question="${question.id}" type="time" value="${escapeHtml(value || "")}">`;
    } else if (question.question_type === "file_upload") {
      const file = fileMeta(question.id);
      fieldHtml = `
        <div>
          <input class="enc-input" data-enc-file="${question.id}" type="file" accept="${escapeHtml((question.config_json || {}).accept || '*/*')}">
          <div class="enc-question-meta">${file.name ? `Archivo seleccionado: ${escapeHtml(file.name)}` : "Sin archivo seleccionado."}</div>
        </div>
      `;
    } else {
      fieldHtml = `<input class="enc-input" data-enc-question="${question.id}" type="text" value="${escapeHtml(value || "")}">`;
    }
    return `
      <article class="enc-preview-question enc-response-question">
        <h4>${escapeHtml(question.titulo)} ${required}</h4>
        <p>${escapeHtml(question.descripcion || "")}</p>
        <div class="enc-preview-field">${fieldHtml}</div>
      </article>
    `;
  }

  function renderCurrentStep() {
    const current = sections()[state.currentStep];
    if (!current) {
      questionsNode.innerHTML = '<div class="enc-placeholder">No hay secciones disponibles.</div>';
      return;
    }
    stepLabelNode.textContent = `Paso ${state.currentStep + 1} de ${sections().length}`;
    sectionTitleNode.textContent = current.titulo || `Sección ${state.currentStep + 1}`;
    sectionDescriptionNode.textContent = current.descripcion || "";
    questionsNode.innerHTML = (current.questions || []).map(renderQuestion).join("");
    prevButton.style.display = state.currentStep === 0 ? "none" : "";
    nextButton.style.display = state.currentStep >= sections().length - 1 ? "none" : "";
    submitButton.style.display = state.currentStep >= sections().length - 1 ? "" : "none";
  }

  function validateCurrentStep() {
    const current = sections()[state.currentStep];
    if (!current) return true;
    for (const question of current.questions || []) {
      if (!question.is_required) continue;
      if (!hasAnswer(question.id)) {
        setMessage(`La pregunta "${question.titulo}" es obligatoria.`, true);
        return false;
      }
    }
    setMessage("", false);
    return true;
  }

  function collectCurrentInputs() {
    questionsNode.querySelectorAll("[data-enc-question]").forEach((node) => {
      const questionId = String(node.dataset.encQuestion);
      if (node.type === "checkbox") {
        const group = Array.from(questionsNode.querySelectorAll(`[data-enc-question="${questionId}"]`));
        state.answers[questionId] = group.filter((item) => item.checked).map((item) => item.value);
      } else if (node.type === "radio") {
        if (node.checked) state.answers[questionId] = node.value;
        else if (!questionsNode.querySelector(`[data-enc-question="${questionId}"]:checked`)) state.answers[questionId] = "";
      } else {
        state.answers[questionId] = node.value;
      }
    });
    questionsNode.querySelectorAll("[data-enc-matrix]").forEach((node) => {
      const questionId = String(node.dataset.encMatrix);
      const row = String(node.dataset.row);
      if (!state.answers[questionId] || typeof state.answers[questionId] !== "object" || Array.isArray(state.answers[questionId])) {
        state.answers[questionId] = {};
      }
      if (node.checked) state.answers[questionId][row] = node.value;
    });
  }

  async function saveDraft(message) {
    collectCurrentInputs();
    const payload = await fetchJSON(`${apiMAIN}/respuestas/${responseData().id}/save`, {
      method: "PUT",
      body: JSON.stringify({ answers: state.answers }),
    });
    state.session = payload;
    refreshAnswersFromSession();
    updateChrome();
    renderSteps();
    renderCurrentStep();
    startTimer();
    setMessage(message || "Borrador guardado.", false);
  }

  async function submitSurvey() {
    collectCurrentInputs();
    const payload = await fetchJSON(`${apiMAIN}/respuestas/${responseData().id}/submit`, {
      method: "POST",
      body: JSON.stringify({ answers: state.answers }),
    });
    state.session = payload;
    refreshAnswersFromSession();
    updateChrome();
    stopTimer();
    renderClosedScreen();
    showScreen("closed");
  }

  function renderClosedScreen() {
    const response = responseData();
    const metrics = response.metrics_json || {};
    closedCopy.textContent = response.status === "submitted"
      ? `Tu respuesta fue enviada el ${formatDate(response.submitted_at)}. Gracias por completar la encuesta.`
      : "La captura ya no está disponible.";
    closedScore.textContent = quiz().is_quiz
      ? [
          response.total_score != null ? `Puntaje: ${response.total_score}.` : "",
          metrics.evaluation_status ? `Resultado: ${metrics.evaluation_status}.` : "",
          quiz().best_attempt && quiz().attempt_strategy === "best"
            ? `Mejor intento registrado: ${quiz().best_attempt.score_value}.`
            : "",
        ].filter(Boolean).join(" ")
      : "";
  }

  function bindEvents() {
    startButton.addEventListener("click", () => {
      if (isSubmitted()) {
        renderClosedScreen();
        showScreen("closed");
        return;
      }
      showScreen("form");
      renderCurrentStep();
      startTimer();
    });

    prevButton.addEventListener("click", async () => {
      collectCurrentInputs();
      if (state.currentStep > 0) {
        state.currentStep -= 1;
        renderSteps();
        renderCurrentStep();
      }
    });

    nextButton.addEventListener("click", async () => {
      collectCurrentInputs();
      if (!validateCurrentStep()) return;
      await saveDraft("Progreso guardado.");
      if (state.currentStep < sections().length - 1) {
        state.currentStep += 1;
        renderSteps();
        renderCurrentStep();
      }
    });

    saveButton.addEventListener("click", async () => {
      try {
        await saveDraft("Progreso guardado.");
      } catch (error) {
        setMessage(error.message, true);
      }
    });

    formNode.addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        if (!validateCurrentStep()) return;
        await submitSurvey();
      } catch (error) {
        setMessage(error.message, true);
      }
    });

    stepsNode.addEventListener("click", async (event) => {
      const button = event.target.closest("[data-enc-step]");
      if (!button) return;
      collectCurrentInputs();
      state.currentStep = Number(button.dataset.encStep);
      renderSteps();
      renderCurrentStep();
    });

    questionsNode.addEventListener("click", (event) => {
      const button = event.target.closest("[data-enc-scale]");
      if (!button) return;
      const questionId = String(button.dataset.encScale);
      state.answers[questionId] = button.dataset.value;
      renderCurrentStep();
    });

    questionsNode.addEventListener("click", (event) => {
      const upButton = event.target.closest("[data-enc-rank-up]");
      const downButton = event.target.closest("[data-enc-rank-down]");
      if (!upButton && !downButton) return;
      const button = upButton || downButton;
      const questionId = String(button.dataset.encRankUp || button.dataset.encRankDown);
      const value = String(button.dataset.value || "");
      const current = rankingValue(questionId);
      const ordered = current.slice();
      const currentIndex = ordered.indexOf(value);
      if (currentIndex === -1) {
        ordered.push(value);
      } else {
        const nextIndex = upButton ? currentIndex - 1 : currentIndex + 1;
        if (nextIndex < 0 || nextIndex >= ordered.length) return;
        const temp = ordered[currentIndex];
        ordered[currentIndex] = ordered[nextIndex];
        ordered[nextIndex] = temp;
      }
      state.answers[questionId] = ordered;
      renderCurrentStep();
    });

    questionsNode.addEventListener("change", async (event) => {
      const input = event.target.closest("[data-enc-file]");
      if (!input || !input.files || !input.files[0]) return;
      const questionId = String(input.dataset.encFile);
      const file = input.files[0];
      const reader = new FileReader();
      reader.onload = () => {
        state.answers[questionId] = {
          name: file.name,
          type: file.type,
          size: file.size,
          data_url: typeof reader.result === "string" ? reader.result : "",
        };
        renderCurrentStep();
      };
      reader.readAsDataURL(file);
    });
  }

  function initialize() {
    refreshAnswersFromSession();
    updateChrome();
    renderStartScreen();
    renderSteps();
    if (isSubmitted()) {
      renderClosedScreen();
    }
    bindEvents();
  }

  initialize();
})();
