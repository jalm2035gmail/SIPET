(function () {
  const root = document.getElementById("enc-root");
  if (!root) return;

  const state = {
    bootstrap: parseBootstrapState(),
    campaigns: [],
    templates: [],
    builder: null,
    results: null,
    permissions: null,
    currentInstanceId: null,
    selectedSectionId: null,
    questionTypes: [],
    assignableUsers: [],
    chart: null,
    questionModalType: null,
  };

  const navButtons = Array.from(root.querySelectorAll("[data-enc-nav]"));
  const panels = Array.from(root.querySelectorAll("[data-enc-panel]"));
  const builderTabs = Array.from(root.querySelectorAll("[data-enc-builder-tab]"));
  const builderPanels = Array.from(root.querySelectorAll("[data-enc-builder-panel]"));
  const surveyTabs = Array.from(root.querySelectorAll("[data-enc-survey-tab]"));
  const surveyPanels = Array.from(root.querySelectorAll("[data-enc-survey-panel]"));
  const metricNodes = root.querySelectorAll("[data-enc-metric]");
  const actionButtons = root.querySelectorAll("[data-enc-action]");

  const campaignsBody = document.getElementById("enc-campaigns-body");
  const campaignsMsg = document.getElementById("enc-campaigns-msg");
  const builderMsg = document.getElementById("enc-builder-msg");
  const builderSelect = document.getElementById("enc-builder-instance-select");
  const templateSelect = document.getElementById("enc-template-select");
  const resultsSelect = document.getElementById("enc-results-instance-select");
  const resultsMsg = document.getElementById("enc-results-msg");
  const resultsEmpty = document.getElementById("enc-results-empty");
  const resultsBody = document.getElementById("enc-results-body");
  const resultsResponsesCount = document.getElementById("enc-results-responses-count");
  const resultsCompletion = document.getElementById("enc-results-completion");
  const resultsNps = document.getElementById("enc-results-nps");
  const resultsScore = document.getElementById("enc-results-score");
  const resultsSegments = document.getElementById("enc-results-segments");
  const resultsQuestions = document.getElementById("enc-results-questions");
  const resultsResponsesBody = document.getElementById("enc-results-responses-body");
  const resultsChartNode = document.getElementById("enc-results-chart");
  const resultsComparison = document.getElementById("enc-results-comparison");
  const resultsExportCsv = document.getElementById("enc-results-export-csv");
  const resultsExportPdf = document.getElementById("enc-results-export-pdf");
  const resultsExportXlsx = document.getElementById("enc-results-export-xlsx");
  const resultsFilterDepartment = document.getElementById("enc-results-filter-department");
  const resultsFilterRole = document.getElementById("enc-results-filter-role");
  const resultsFilterCompany = document.getElementById("enc-results-filter-company");
  const resultsSegmentBy = document.getElementById("enc-results-segment-by");
  const sectionsList = document.getElementById("enc-sections-list");
  const questionsList = document.getElementById("enc-questions-list");
  const questionsEmpty = document.getElementById("enc-questions-empty");
  const previewRoot = document.getElementById("enc-preview-root");
  const validationBox = document.getElementById("enc-publish-validation");

  const generalForm = document.getElementById("enc-general-form");
  const audienceForm = document.getElementById("enc-audience-form");
  const rulesForm = document.getElementById("enc-rules-form");
  const publicationForm = document.getElementById("enc-publication-form");
  const surveyOptionsForm = document.getElementById("enc-survey-options-form");
  const surveyDescriptionForm = document.getElementById("enc-survey-description-form");
  const surveyFinalMessageForm = document.getElementById("enc-survey-final-message-form");
  const editorTitle = document.getElementById("enc-editor-title");
  const editorParticipaciones = document.getElementById("enc-editor-participaciones");
  const editorResponsable = document.getElementById("enc-editor-responsable");
  const editorRestringido = document.getElementById("enc-editor-restringido");
  const editorAudienceMode = document.getElementById("enc-editor-audience-mode");
  const editorAnonymityMode = document.getElementById("enc-editor-anonymity-mode");
  const editorScoringMode = document.getElementById("enc-editor-scoring-mode");
  const editorPublicationMode = document.getElementById("enc-editor-publication-mode");
  const editorDescription = document.getElementById("enc-editor-description");
  const editorFinalMessage = document.getElementById("enc-editor-final-message");
  const questionModal = document.getElementById("enc-question-modal");
  const questionModalTitle = document.getElementById("enc-modal-question-title");
  const questionModalTypes = document.getElementById("enc-modal-question-types");
  const questionModalPreview = document.getElementById("enc-modal-question-preview");
  const questionModalOptions = document.getElementById("enc-modal-question-options");
  const questionModalDescription = document.getElementById("enc-modal-question-description");
  const questionModalRequired = document.getElementById("enc-modal-question-required");
  const questionModalSaveClose = document.getElementById("enc-modal-question-save-close");
  const questionModalSaveNew = document.getElementById("enc-modal-question-save-new");
  const questionModalTabs = Array.from(root.querySelectorAll("[data-enc-question-tab]"));
  const questionModalPanels = Array.from(root.querySelectorAll("[data-enc-question-panel]"));

  function parseBootstrapState() {
    try {
      return JSON.parse(root.dataset.encBootstrap || "{}");
    } catch (error) {
      console.warn("encuestas bootstrap invalido", error);
      return {};
    }
  }

  function setMessage(node, message, isError) {
    if (!node) return;
    node.textContent = message || "";
    node.style.color = isError ? "#991b1b" : "";
  }

  function selectedResultsFilters() {
    return {
      department: resultsFilterDepartment ? resultsFilterDepartment.value : "",
      role: resultsFilterRole ? resultsFilterRole.value : "",
      company: resultsFilterCompany ? resultsFilterCompany.value : "",
      segment_by: resultsSegmentBy ? resultsSegmentBy.value : "department",
    };
  }

  function fillResultsFilterSelect(node, values, placeholder, selectedValue) {
    if (!node) return;
    node.innerHTML = [`<option value="">${placeholder}</option>`]
      .concat((values || []).map((value) => `<option value="${value}" ${String(selectedValue) === String(value) ? "selected" : ""}>${value}</option>`))
      .join("");
  }

  function can(permission) {
    return !!(state.permissions && state.permissions[permission]);
  }

  async function fetchJSON(url, options) {
    const response = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (response.status === 204) return null;
    const text = await response.text();
    const data = text ? JSON.parse(text) : null;
    if (!response.ok) {
      const detail = data && data.detail ? data.detail : data;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return data;
  }

  function showPanel(panelId) {
    const targetPanel = panels.some((panel) => panel.dataset.encPanel === panelId) ? panelId : "dashboard";
    navButtons.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.encNav === targetPanel);
    });
    panels.forEach((panel) => {
      panel.classList.toggle("is-active", panel.dataset.encPanel === targetPanel);
    });
  }

  function initialPanel() {
    const panel = String((state.bootstrap && state.bootstrap.current_panel) || "").trim();
    if (panel) return panel;
    const currentPath = window.location.pathname;
    if (currentPath.endsWith("/constructor")) return "constructor";
    if (currentPath.endsWith("/resultados")) return "resultados";
    if (currentPath.endsWith("/encuestas")) return "encuestas";
    return "dashboard";
  }

  function showBuilderTab(tabId) {
    builderTabs.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.encBuilderTab === tabId);
    });
    builderPanels.forEach((panel) => {
      panel.classList.toggle("is-active", panel.dataset.encBuilderPanel === tabId);
    });
  }

  function showSurveyTab(tabId) {
    surveyTabs.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.encSurveyTab === tabId);
    });
    surveyPanels.forEach((panel) => {
      panel.classList.toggle("is-active", panel.dataset.encSurveyPanel === tabId);
    });
  }

  function showQuestionModalTab(tabId) {
    questionModalTabs.forEach((button) => {
      button.classList.toggle("is-active", button.dataset.encQuestionTab === tabId);
    });
    questionModalPanels.forEach((panel) => {
      panel.classList.toggle("is-active", panel.dataset.encQuestionPanel === tabId);
    });
  }

  function paintMetrics() {
    const metrics = state.bootstrap.metrics || {};
    metricNodes.forEach((node) => {
      const key = node.dataset.encMetric;
      const value = metrics[key];
      if (value == null) return;
      node.textContent = key === "completion_rate" ? `${value}%` : String(value);
    });
  }

  function formatDateForInput(value) {
    if (!value) return "";
    return String(value).slice(0, 16);
  }

  function formatDateLabel(value) {
    if (!value) return "Pendiente";
    return value.replace("T", " ").slice(0, 16);
  }

  function statusPill(status) {
    if (status === "published") return '<span class="enc-pill is-live">Publicada</span>';
    if (status === "closed") return '<span class="enc-pill is-planned">Cerrada</span>';
    return '<span class="enc-pill is-draft">Borrador</span>';
  }

  function parseOptionsText(rawText, type) {
    if (type === "yes_no") {
      return [
        { label: "Sí", value: "yes", orden: 1 },
        { label: "No", value: "no", orden: 2 },
      ];
    }
    if (type === "true_false") {
      return [
        { label: "Verdadero", value: "true", orden: 1 },
        { label: "Falso", value: "false", orden: 2 },
      ];
    }
    if (type === "scale_1_5" || type === "live_scale_1_5") {
      return [1, 2, 3, 4, 5].map((value) => ({ label: String(value), value: String(value), orden: value }));
    }
    if (type === "nps_0_10") {
      return Array.from({ length: 11 }, (_, index) => ({
        label: String(index),
        value: String(index),
        orden: index + 1,
      }));
    }
    return String(rawText || "")
      .split(",")
      .map((part) => part.trim())
      .filter(Boolean)
      .map((label, index) => ({ label, value: label.toLowerCase().replace(/\s+/g, "_"), orden: index + 1 }));
  }

  function typeSupportsOptions(type) {
    return [
      "single_choice",
      "live_poll_single_choice",
      "multiple_choice",
      "yes_no",
      "scale_1_5",
      "live_scale_1_5",
      "nps_0_10",
      "quiz_single_choice",
      "ranking",
      "matrix",
      "likert_scale",
      "semantic_differential",
      "dropdown",
      "image_choice",
      "true_false",
    ].includes(type);
  }

  function defaultOptionsText(type) {
    if (type === "yes_no") return "Sí\nNo";
    if (type === "true_false") return "Verdadero\nFalso";
    if (type === "scale_1_5" || type === "live_scale_1_5") return "1\n2\n3\n4\n5";
    if (type === "nps_0_10") return "0\n1\n2\n3\n4\n5\n6\n7\n8\n9\n10";
    if (type === "likert_scale") return "Totalmente en desacuerdo\nEn desacuerdo\nNeutral\nDe acuerdo\nTotalmente de acuerdo";
    if (type === "semantic_differential") return "Muy negativo\nNegativo\nNeutral\nPositivo\nMuy positivo";
    if (type === "matrix") return "Fila 1\nFila 2\nFila 3";
    return "";
  }

  function getQuestionTypeKeys() {
    return (state.questionTypes || []).map((item) => item.key);
  }

  function questionTypeLabel(key) {
    const labels = {
      short_text: "Texto corto",
      long_text: "Texto largo",
      word_cloud: "Nube de palabras",
      single_choice: "Opción única",
      live_poll_single_choice: "Encuesta en vivo de opción única",
      multiple_choice: "Selección múltiple",
      yes_no: "Sí / No",
      scale_1_5: "Escala del 1 al 5",
      live_scale_1_5: "Escala en vivo del 1 al 5",
      nps_0_10: "NPS del 0 al 10",
      quiz_single_choice: "Quiz de opción única",
      ranking: "Ordenamiento / Priorización",
      matrix: "Matriz de valoraciones",
      likert_scale: "Escala de Likert",
      semantic_differential: "Diferencial semántico",
      date: "Fecha",
      time: "Hora",
      dropdown: "Lista desplegable",
      file_upload: "Carga de archivos",
      slider: "Control deslizante",
      image_choice: "Selección con imágenes",
      true_false: "Verdadero / Falso",
    };
    return labels[key] || key;
  }

  function questionTypePromptLabel() {
    const items = (state.questionTypes || []).map((item) => `${questionTypeLabel(item.key)}\n${item.key}`);
    return items.join("\n\n");
  }

  async function pickQuestionType() {
    const items = (state.questionTypes || []).map((item) => {
      const icon = ({
        short_text: "⌶",
        long_text: "≣",
        word_cloud: "◌",
        single_choice: "◉",
        live_poll_single_choice: "◉",
        multiple_choice: "☑",
        yes_no: "↔",
        scale_1_5: "◔",
        live_scale_1_5: "◔",
        nps_0_10: "◒",
        quiz_single_choice: "✦",
        ranking: "⇅",
        matrix: "▦",
        likert_scale: "☷",
        semantic_differential: "⟷",
        date: "◷",
        time: "◔",
        dropdown: "▾",
        file_upload: "⤴",
        slider: "⎯",
        image_choice: "▥",
        true_false: "✓",
      })[item.key] || "•";
      return `
        <button type="button" class="enc-type-picker-item" data-enc-type-choice="${item.key}">
          <span class="enc-type-picker-icon" aria-hidden="true">${icon}</span>
          <span class="enc-type-picker-copy">
            <strong>${questionTypeLabel(item.key)}</strong>
            <small>${item.key}</small>
          </span>
        </button>
      `;
    }).join("");
    const container = document.createElement("div");
    container.className = "enc-type-picker";
    container.innerHTML = `
      <div class="enc-type-picker-head">
        <p class="enc-sidebar-label">Tipo de pregunta</p>
        <div class="enc-type-picker-list">${items}</div>
      </div>
    `;
    const anchor = builderMsg || root;
    anchor.innerHTML = "";
    anchor.appendChild(container);
    setMessage("", false);
    return await new Promise((resolve) => {
      container.addEventListener("click", (event) => {
        const button = event.target.closest("[data-enc-type-choice]");
        if (!button) return;
        resolve(String(button.dataset.encTypeChoice || ""));
      }, { once: true });
    });
  }

  function parseQuestionModalOptions(type) {
    if (!typeSupportsOptions(type)) return [];
    return parseOptionsText(
      String((questionModalOptions && questionModalOptions.value) || "")
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)
        .join(", "),
      type
    );
  }

  function fillSurveyEditor() {
    const builder = state.builder;
    if (!builder) return;
    const settings = builder.settings_json || {};
    const publicationRules = builder.publication_rules_json || {};
    if (editorTitle) editorTitle.value = builder.nombre || "";
    if (editorParticipaciones) editorParticipaciones.textContent = String(builder.responses_count || 0);
    if (editorResponsable) {
      editorResponsable.textContent = builder.created_by_name || builder.owner_name || builder.responsable || "SIPET";
    }
    if (editorRestringido) {
      const labels = {
        internal: "Personal interno",
        mixed: "Audiencia mixta",
        public_link: "Enlace público",
      };
      editorRestringido.textContent = labels[builder.audience_mode] || "Todos los participantes autorizados";
    }
    if (editorAudienceMode) editorAudienceMode.value = builder.audience_mode || "internal";
    if (editorAnonymityMode) editorAnonymityMode.value = builder.anonymity_mode || "identified";
    if (editorScoringMode) editorScoringMode.value = settings.scoring_mode || "none";
    if (editorPublicationMode) editorPublicationMode.value = builder.publication_mode || "manual";
    if (editorDescription) editorDescription.value = builder.descripcion || "";
    if (editorFinalMessage) editorFinalMessage.value = publicationRules.final_message || "";
  }

  function renderQuestionModalPreview() {
    if (!questionModalPreview) return;
    const type = state.questionModalType || (state.questionTypes[0] && state.questionTypes[0].key) || "short_text";
    const title = String((questionModalTitle && questionModalTitle.value) || "").trim() || "¿Cuál es tu pregunta?";
    const options = parseQuestionModalOptions(type).slice(0, 5);
    let body = '<div class="enc-input">respuesta</div>';
    if (["single_choice", "live_poll_single_choice", "quiz_single_choice", "yes_no", "true_false", "dropdown", "image_choice"].includes(type)) {
      const source = options.length ? options : parseOptionsText("", type);
      body = source.slice(0, 3).map((option, index) => `<div class="enc-question-meta">${index === 1 ? "◉" : "○"} ${option.label}</div>`).join("");
    } else if (["multiple_choice", "ranking"].includes(type)) {
      const source = options.length ? options : [{ label: "opción 1" }, { label: "opción 2" }, { label: "opción 3" }];
      body = source.slice(0, 3).map((option, index) => `<div class="enc-question-meta">${index === 0 ? "☑" : "☐"} ${option.label}</div>`).join("");
    } else if (["scale_1_5", "live_scale_1_5", "nps_0_10", "slider", "likert_scale", "semantic_differential", "matrix"].includes(type)) {
      const source = options.length ? options : [{ label: "1" }, { label: "2" }, { label: "3" }, { label: "4" }, { label: "5" }];
      body = `<div class="enc-builder-toolbar">${source.slice(0, 5).map((option) => `<span class="enc-pill is-draft">${option.label}</span>`).join("")}</div>`;
    }
    questionModalPreview.innerHTML = `
      <strong>${title}</strong>
      <p class="enc-question-meta">${questionTypeLabel(type)}</p>
      ${body}
    `;
  }

  function renderQuestionModalTypeList() {
    if (!questionModalTypes) return;
    if (!state.questionModalType) {
      state.questionModalType = state.questionTypes[0] ? state.questionTypes[0].key : "short_text";
    }
    questionModalTypes.innerHTML = (state.questionTypes || []).map((item) => `
      <button type="button" class="enc-question-type-chip ${state.questionModalType === item.key ? "is-active" : ""}" data-enc-modal-type="${item.key}">
        <input type="radio" name="enc-modal-type" ${state.questionModalType === item.key ? "checked" : ""} tabindex="-1">
        <span class="enc-question-type-chip-copy">
          <strong>${questionTypeLabel(item.key)}</strong>
          <small>${item.key}</small>
        </span>
      </button>
    `).join("");
    if (questionModalOptions) {
      if (typeSupportsOptions(state.questionModalType)) {
        questionModalOptions.disabled = false;
        if (!questionModalOptions.value.trim()) {
          questionModalOptions.value = defaultOptionsText(state.questionModalType);
        }
      } else {
        questionModalOptions.disabled = true;
        questionModalOptions.value = "";
      }
    }
    renderQuestionModalPreview();
  }

  function resetQuestionModal() {
    state.questionModalType = state.questionTypes[0] ? state.questionTypes[0].key : "short_text";
    if (questionModalTitle) questionModalTitle.value = "";
    if (questionModalDescription) questionModalDescription.value = "";
    if (questionModalRequired) questionModalRequired.value = "false";
    if (questionModalOptions) questionModalOptions.value = defaultOptionsText(state.questionModalType);
    showQuestionModalTab("answers");
    renderQuestionModalTypeList();
  }

  function openQuestionModal() {
    if (!questionModal) return;
    resetQuestionModal();
    questionModal.hidden = false;
    document.body.style.overflow = "hidden";
    if (questionModalTitle) questionModalTitle.focus();
  }

  function closeQuestionModal() {
    if (!questionModal) return;
    questionModal.hidden = true;
    document.body.style.overflow = "";
  }

  function parseCsvValues(rawText) {
    return String(rawText || "")
      .split(",")
      .map((part) => part.trim())
      .filter(Boolean);
  }

  function stringifyManualGroups(groups) {
    if (!Array.isArray(groups) || !groups.length) return "";
    return JSON.stringify(groups, null, 2);
  }

  function parseManualGroups(rawText) {
    const text = String(rawText || "").trim();
    if (!text) return [];
    const parsed = JSON.parse(text);
    if (Array.isArray(parsed)) return parsed;
    return [parsed];
  }

  function getCurrentSection() {
    const sections = (state.builder && state.builder.sections) || [];
    return sections.find((section) => section.id === state.selectedSectionId) || null;
  }

  function renderCampaigns() {
    if (!campaignsBody) return;
    if (!state.campaigns.length) {
      campaignsBody.innerHTML = '<tr><td colspan="5">No hay campañas registradas.</td></tr>';
      return;
    }
    campaignsBody.innerHTML = state.campaigns
      .map(
        (campaign) => `
          <tr>
            <td>${campaign.nombre}</td>
            <td>${statusPill(campaign.status)}</td>
            <td>${campaign.audience_mode || "internal"}</td>
            <td>${formatDateLabel(campaign.published_at || campaign.schedule_start_at)}</td>
            <td>
              ${can("manage_surveys") ? `<button type="button" class="enc-mini-btn is-primary" data-enc-open-builder="${campaign.id}">Constructor</button>` : ""}
              ${can("view_results_summary") ? `<button type="button" class="enc-mini-btn" data-enc-open-results="${campaign.id}">Resultados</button>` : ""}
            </td>
          </tr>
        `
      )
      .join("");
  }

  function renderBuilderSelect() {
    if (!builderSelect) return;
    const selected = state.currentInstanceId ? String(state.currentInstanceId) : "";
    builderSelect.innerHTML = ['<option value="">Selecciona una campaña</option>']
      .concat(
        state.campaigns.map(
          (campaign) => `<option value="${campaign.id}" ${selected === String(campaign.id) ? "selected" : ""}>${campaign.nombre}</option>`
        )
      )
      .join("");
    if (resultsSelect) {
      resultsSelect.innerHTML = builderSelect.innerHTML;
    }
  }

  function renderTemplateSelect() {
    if (!templateSelect) return;
    templateSelect.innerHTML = ['<option value="">Usar plantilla</option>']
      .concat(
        state.templates.map(
          (template) => `<option value="${template.id}">${template.nombre}</option>`
        )
      )
      .join("");
  }

  function applyPermissionsUI() {
    root.querySelectorAll('[data-enc-action="new-survey"], [data-enc-action="add-section"], [data-enc-action="add-question"], [data-enc-action="publish-campaign"], [data-enc-action="close-campaign"]').forEach((node) => {
      node.style.display = can("manage_surveys") ? "" : "none";
    });
    root.querySelectorAll('[data-enc-action="create-from-template"], [data-enc-action="save-as-template"]').forEach((node) => {
      node.style.display = can("manage_surveys") ? "" : "none";
    });
    if (builderSelect) builderSelect.disabled = !can("manage_surveys");
    if (templateSelect) templateSelect.disabled = !can("manage_surveys");
    if (resultsExportCsv) resultsExportCsv.style.display = can("export_sensitive_results") ? "" : "none";
    if (resultsExportPdf) resultsExportPdf.style.display = can("export_sensitive_results") ? "" : "none";
    if (resultsExportXlsx) resultsExportXlsx.style.display = can("export_sensitive_results") ? "" : "none";
  }

  function segmentSummaryRows() {
    if (!state.results || !state.results.segment_report) return [];
    return ["department", "role", "company"]
      .flatMap((key) => (state.results.segment_report[key] || []).slice(0, 3));
  }

  function renderResultsChart() {
    if (!resultsChartNode || !state.results || !window.Chart) return;
    const summary = state.results.summary || {};
    if (state.chart) {
      state.chart.destroy();
    }
    state.chart = new window.Chart(resultsChartNode, {
      type: "bar",
      data: {
        labels: ["Finalización", "NPS", "CSAT", "CES", "Quiz"],
        datasets: [
          {
            label: "Indicadores",
            data: [
              summary.completion_pct_avg || 0,
              summary.nps_score || 0,
              summary.csat_score || 0,
              summary.ces_score || 0,
              summary.quiz_approval_pct || 0,
            ],
            backgroundColor: ["#2b6c4f", "#1d4ed8", "#0f766e", "#c2410c", "#7c3aed"],
            borderRadius: 10,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true } },
      },
    });
  }

  function renderComparison() {
    if (!resultsComparison || !state.results) return;
    const rows = state.results.comparison_report || [];
    resultsComparison.innerHTML = rows.length
      ? rows.map((row) => `
          <article class="enc-section-card">
            <strong>${row.segment}</strong>
            <p class="enc-section-meta">
              ${row.responses} respuesta(s) · Finalización ${row.completion_pct_avg ?? 0}% · Score ${row.total_score_avg ?? "N/A"} · NPS ${row.nps_score ?? "N/A"} · CSAT ${row.csat_score ?? "N/A"} · CES ${row.ces_score ?? "N/A"}
            </p>
          </article>
        `).join("")
      : '<div class="enc-placeholder">No hay comparativos disponibles para el filtro actual.</div>';
  }

  function syncResultsFilters() {
    if (!state.results) return;
    const available = state.results.available_filters || {};
    const applied = state.results.applied_filters || {};
    fillResultsFilterSelect(resultsFilterDepartment, available.departments || [], "Todos los departamentos", applied.department || "");
    fillResultsFilterSelect(resultsFilterRole, available.roles || [], "Todos los roles", applied.role || "");
    fillResultsFilterSelect(resultsFilterCompany, available.companies || [], "Todas las empresas", applied.company || "");
    if (resultsSegmentBy) {
      resultsSegmentBy.value = applied.segment_by || "department";
    }
  }

  function renderResults() {
    if (!resultsBody || !resultsEmpty) return;
    const data = state.results;
    if (!data) {
      resultsBody.hidden = true;
      resultsEmpty.hidden = false;
      return;
    }
    const summary = data.summary || {};
    resultsBody.hidden = false;
    resultsEmpty.hidden = true;
    resultsResponsesCount.textContent = String(summary.responses_count || 0);
    resultsCompletion.textContent = `${summary.completion_pct_avg || 0}%`;
    resultsNps.textContent = String(summary.nps_score ?? 0);
    resultsScore.textContent = String(summary.total_score_avg ?? 0);
    const filters = selectedResultsFilters();
    const query = new URLSearchParams();
    if (filters.department) query.set("department", filters.department);
    if (filters.role) query.set("role", filters.role);
    if (filters.company) query.set("company", filters.company);
    if (filters.segment_by) query.set("segment_by", filters.segment_by);
    const suffix = query.toString() ? `?${query.toString()}` : "";
    if (resultsExportCsv) {
      resultsExportCsv.href = `/api/encuestas/campanas/${data.instance.id}/export.csv${suffix}`;
    }
    if (resultsExportPdf) {
      resultsExportPdf.href = `/api/encuestas/campanas/${data.instance.id}/export.pdf${suffix}`;
    }
    if (resultsExportXlsx) {
      resultsExportXlsx.href = `/api/encuestas/campanas/${data.instance.id}/export.xlsx${suffix}`;
    }
    resultsSegments.innerHTML = segmentSummaryRows().length
      ? segmentSummaryRows().map((item) => `
          <article class="enc-section-card">
            <strong>${item.label}: ${item.segment}</strong>
            <p class="enc-section-meta">${item.responses} respuesta(s) · Finalización ${item.completion_pct_avg ?? 0}% · Score ${item.score_avg ?? "N/A"}</p>
          </article>
        `).join("")
      : '<div class="enc-placeholder">No hay segmentos con respuestas enviadas.</div>';
    resultsQuestions.innerHTML = (data.question_report || []).length
      ? data.question_report.map((item) => {
          const options = (item.options || []).length
            ? `<div class="enc-question-meta">${item.options.map((option) => `${option.label}: ${option.count}`).join(" · ")}</div>`
            : `<div class="enc-question-meta">${(item.sample_answers || []).join(" · ") || "Sin muestras"}</div>`;
          return `
            <article class="enc-question-card">
              <strong>${item.section_title} · ${item.question_title}</strong>
              <p class="enc-question-meta">${questionTypeLabel(item.question_type)} · ${item.responses_count} respuesta(s) · Score ${item.avg_score ?? "N/A"}</p>
              ${options}
            </article>
          `;
        }).join("")
      : '<div class="enc-placeholder">No hay respuestas enviadas para generar reporte.</div>';
    resultsResponsesBody.innerHTML = (data.responses_table || []).length
      ? data.responses_table.map((row) => `
          <tr>
            <td>${row.respondent_name}</td>
            <td>${row.role || "Sin dato"}</td>
            <td>${row.department || "Sin dato"}</td>
            <td>${row.status}</td>
            <td>${row.total_score ?? "N/A"}</td>
            <td>${formatDateLabel(row.submitted_at)}</td>
          </tr>
        `).join("")
      : '<tr><td colspan="6">Sin respuestas enviadas.</td></tr>';
    syncResultsFilters();
    renderComparison();
    renderResultsChart();
  }

  function fillBuilderForms() {
    const builder = state.builder;
    if (!builder) return;
    const settings = builder.settings_json || {};
    document.getElementById("enc-general-nombre").value = builder.nombre || "";
    document.getElementById("enc-general-descripcion").value = builder.descripcion || "";
    document.getElementById("enc-general-publication-mode").value = builder.publication_mode || "manual";
    document.getElementById("enc-general-start-at").value = formatDateForInput(builder.schedule_start_at);
    document.getElementById("enc-general-end-at").value = formatDateForInput(builder.schedule_end_at);
    document.getElementById("enc-audience-mode").value = builder.audience_mode || "internal";
    document.getElementById("enc-audience-source-app").value = builder.source_app || "";
    document.getElementById("enc-audience-assignment-type").value = settings.assignment_type || "user";
    document.getElementById("enc-audience-values").value = Array.isArray(settings.assignment_values)
      ? settings.assignment_values.join(", ")
      : "";
    document.getElementById("enc-audience-group-note").value = settings.audience_note || "";
    document.getElementById("enc-audience-manual-group").value = stringifyManualGroups(settings.manual_groups);
    document.getElementById("enc-rules-anonymity-mode").value = builder.anonymity_mode || "identified";
    document.getElementById("enc-rules-scoring-mode").value = settings.scoring_mode || "none";
    document.getElementById("enc-rules-json").value = JSON.stringify(builder.publication_rules_json || {}, null, 2);
    document.getElementById("enc-public-link-enabled").value = builder.is_public_link_enabled ? "true" : "false";
    document.getElementById("enc-public-link-token").value = builder.public_link_token || "";
    document.getElementById("enc-publication-due-at").value = formatDateForInput(settings.assignment_due_at);
  }

  function renderSections() {
    if (!sectionsList) return;
    const sections = (state.builder && state.builder.sections) || [];
    if (!sections.length) {
      sectionsList.innerHTML = '<div class="enc-placeholder">Aún no hay secciones. Agrega la primera.</div>';
      questionsList.innerHTML = "";
      questionsEmpty.style.display = "";
      return;
    }
    if (!state.selectedSectionId || !sections.some((section) => section.id === state.selectedSectionId)) {
      state.selectedSectionId = sections[0].id;
    }
    sectionsList.innerHTML = sections
      .map((section, index) => {
        const activeClass = section.id === state.selectedSectionId ? "is-active" : "";
        return `
          <article class="enc-section-card ${activeClass}" data-enc-section-id="${section.id}">
            <strong>${index + 1}. ${section.titulo}</strong>
            <p class="enc-section-meta">${section.descripcion || "Sin descripción"} · ${section.questions.length} pregunta(s)</p>
            <div class="enc-section-actions">
              <button type="button" class="enc-mini-btn" data-enc-select-section="${section.id}">Abrir</button>
              <button type="button" class="enc-mini-btn" data-enc-edit-section="${section.id}">Editar</button>
              <button type="button" class="enc-mini-btn" data-enc-section-up="${section.id}">Subir</button>
              <button type="button" class="enc-mini-btn" data-enc-section-down="${section.id}">Bajar</button>
            </div>
          </article>
        `;
      })
      .join("");
    renderQuestions();
  }

  function renderQuestions() {
    const section = getCurrentSection();
    if (!section) {
      questionsList.innerHTML = "";
      questionsEmpty.style.display = "";
      return;
    }
    questionsEmpty.style.display = "none";
    questionsList.innerHTML = (section.questions || [])
      .map(
        (question, index) => `
          <article class="enc-question-card">
            <strong>${index + 1}. ${question.titulo}</strong>
            <p class="enc-question-meta">${questionTypeLabel(question.question_type)} · ${question.is_required ? "Obligatoria" : "Opcional"}</p>
            <div class="enc-question-actions">
              <button type="button" class="enc-mini-btn" data-enc-edit-question="${question.id}">Editar</button>
              <button type="button" class="enc-mini-btn" data-enc-duplicate-question="${question.id}">Duplicar</button>
              <button type="button" class="enc-mini-btn" data-enc-question-up="${question.id}">Subir</button>
              <button type="button" class="enc-mini-btn" data-enc-question-down="${question.id}">Bajar</button>
            </div>
          </article>
        `
      )
      .join("");
  }

  function renderValidation() {
    if (!validationBox) return;
    const validation = (state.builder && state.builder.publish_validation) || null;
    if (!validation) {
      validationBox.className = "enc-validation-box";
      validationBox.textContent = "Selecciona una campaña para evaluar su publicación.";
      return;
    }
    validationBox.className = `enc-validation-box ${validation.ok ? "is-ok" : "is-error"}`;
    validationBox.innerHTML = validation.ok
      ? "La encuesta cumple las validaciones mínimas para publicación."
      : `<strong>Faltantes:</strong><ul>${validation.errors.map((error) => `<li>${error}</li>`).join("")}</ul>`;
  }

  async function loadPreview() {
    if (!state.currentInstanceId || !previewRoot) return;
    const preview = await fetchJSON(`/api/encuestas/campanas/${state.currentInstanceId}/preview`);
    previewRoot.innerHTML = preview.html;
  }

  async function loadCampaigns(focusBuilder) {
    state.campaigns = await fetchJSON("/api/encuestas/campanas");
    renderCampaigns();
    renderBuilderSelect();
    if (focusBuilder && state.campaigns.length) {
      const candidate = state.currentInstanceId || state.campaigns[0].id;
      await loadBuilder(candidate);
      showPanel("constructor");
    }
  }

  async function loadQuestionTypes() {
    state.questionTypes = await fetchJSON("/api/encuestas/question-types");
  }

  async function loadTemplates() {
    state.templates = await fetchJSON("/api/encuestas/templates");
    renderTemplateSelect();
  }

  async function loadPermissions() {
    state.permissions = await fetchJSON("/api/encuestas/permissions");
    applyPermissionsUI();
  }

  async function loadAssignableUsers() {
    state.assignableUsers = await fetchJSON("/api/encuestas/assignable-users");
  }

  async function loadBuilder(instanceId) {
    if (!instanceId) return;
    state.currentInstanceId = Number(instanceId);
    state.builder = await fetchJSON(`/api/encuestas/campanas/${instanceId}/builder`);
    if (!state.selectedSectionId && state.builder.sections && state.builder.sections.length) {
      state.selectedSectionId = state.builder.sections[0].id;
    }
    fillBuilderForms();
    fillSurveyEditor();
    renderSections();
    renderValidation();
    await loadPreview();
  }

  async function ensureChartLibrary() {
    if (window.Chart) return;
    await new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "/static/vendor/chart.umd.min.js";
      script.onload = resolve;
      script.onerror = reject;
      document.body.appendChild(script);
    });
  }

  async function loadResults(instanceId) {
    if (!instanceId) return;
    await ensureChartLibrary();
    const filters = selectedResultsFilters();
    const query = new URLSearchParams();
    if (filters.department) query.set("department", filters.department);
    if (filters.role) query.set("role", filters.role);
    if (filters.company) query.set("company", filters.company);
    if (filters.segment_by) query.set("segment_by", filters.segment_by);
    state.results = await fetchJSON(`/api/encuestas/campanas/${instanceId}/analytics?${query.toString()}`);
    if (state.results && state.results.permissions) {
      state.permissions = { ...state.permissions, ...state.results.permissions };
      applyPermissionsUI();
    }
    renderResults();
  }

  async function createCampaign() {
    const timestamp = new Date().toISOString().slice(0, 16).replace("T", " ");
    const nombre = window.prompt("Nombre de la nueva campaña", `Nueva encuesta ${timestamp}`);
    if (!nombre) return;
    const campaign = await fetchJSON("/api/encuestas/campanas", {
      method: "POST",
      body: JSON.stringify({ nombre }),
    });
    state.currentInstanceId = campaign.id;
    state.selectedSectionId = null;
    await loadCampaigns(true);
    setMessage(campaignsMsg, "Campaña creada.");
  }

  async function createCampaignFromTemplate() {
    if (!templateSelect || !templateSelect.value) {
      setMessage(builderMsg, "Selecciona una plantilla primero.", true);
      return;
    }
    const template = (state.templates || []).find((item) => String(item.id) === String(templateSelect.value));
    const nombre = window.prompt("Nombre de la campaña", template ? template.nombre : "Nueva encuesta");
    if (!nombre) return;
    const campaign = await fetchJSON("/api/encuestas/campanas", {
      method: "POST",
      body: JSON.stringify({ nombre, template_id: Number(templateSelect.value) }),
    });
    state.currentInstanceId = campaign.id;
    state.selectedSectionId = null;
    await loadCampaigns(true);
    setMessage(builderMsg, "Campaña creada desde plantilla.");
  }

  async function saveAsTemplate() {
    if (!state.currentInstanceId || !state.builder) {
      setMessage(builderMsg, "Selecciona una campaña primero.", true);
      return;
    }
    const nombre = window.prompt("Nombre de la plantilla", state.builder.nombre || "Nueva plantilla");
    if (!nombre) return;
    const slug = window.prompt("Slug de la plantilla", nombre.toLowerCase().replace(/\s+/g, "-"));
    if (!slug) return;
    await fetchJSON(`/api/encuestas/campanas/${state.currentInstanceId}/save-template`, {
      method: "POST",
      body: JSON.stringify({
        nombre,
        slug,
        descripcion: state.builder.descripcion || "",
      }),
    });
    await loadTemplates();
    setMessage(builderMsg, "Plantilla guardada.");
  }

  async function saveDraft(payload, message) {
    if (!state.currentInstanceId) {
      setMessage(builderMsg, "Selecciona una campaña primero.", true);
      return;
    }
    await fetchJSON(`/api/encuestas/campanas/${state.currentInstanceId}/draft`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    await loadCampaigns(false);
    await loadBuilder(state.currentInstanceId);
    setMessage(builderMsg, message || "Cambios guardados.");
  }

  async function addSection() {
    if (!state.currentInstanceId) {
      setMessage(builderMsg, "Selecciona una campaña primero.", true);
      return;
    }
    const titulo = window.prompt("Título de la sección", "Nueva sección");
    if (!titulo) return;
    await fetchJSON(`/api/encuestas/campanas/${state.currentInstanceId}/sections`, {
      method: "POST",
      body: JSON.stringify({ titulo }),
    });
    await loadBuilder(state.currentInstanceId);
    setMessage(builderMsg, "Sección agregada.");
  }

  async function editSection(sectionId) {
    const section = ((state.builder && state.builder.sections) || []).find((item) => item.id === sectionId);
    if (!section) return;
    const titulo = window.prompt("Editar título de la sección", section.titulo || "");
    if (!titulo) return;
    const descripcion = window.prompt("Descripción de la sección", section.descripcion || "");
    await fetchJSON(`/api/encuestas/campanas/${state.currentInstanceId}/sections/${sectionId}`, {
      method: "PATCH",
      body: JSON.stringify({ titulo, descripcion }),
    });
    await loadBuilder(state.currentInstanceId);
    setMessage(builderMsg, "Sección actualizada.");
  }

  async function reorderSection(sectionId, direction) {
    const sections = (state.builder && state.builder.sections) || [];
    const index = sections.findIndex((item) => item.id === sectionId);
    const swapIndex = index + direction;
    if (index < 0 || swapIndex < 0 || swapIndex >= sections.length) return;
    const ids = sections.map((item) => item.id);
    const temp = ids[index];
    ids[index] = ids[swapIndex];
    ids[swapIndex] = temp;
    await fetchJSON(`/api/encuestas/campanas/${state.currentInstanceId}/sections/reorder`, {
      method: "POST",
      body: JSON.stringify({ ids }),
    });
    await loadBuilder(state.currentInstanceId);
  }

  async function addQuestion() {
    const section = getCurrentSection();
    if (!state.currentInstanceId || !section) {
      setMessage(builderMsg, "Selecciona una sección primero.", true);
      return;
    }
    openQuestionModal();
  }

  async function saveQuestionFromModal(keepOpen) {
    const section = getCurrentSection();
    if (!state.currentInstanceId || !section) {
      setMessage(builderMsg, "Selecciona una sección primero.", true);
      return;
    }
    const titulo = String((questionModalTitle && questionModalTitle.value) || "").trim();
    if (!titulo) {
      throw new Error("Escribe la pregunta.");
    }
    const type = state.questionModalType || "";
    if (!getQuestionTypeKeys().includes(type)) {
      throw new Error("Selecciona un tipo de pregunta válido.");
    }
    await fetchJSON(`/api/encuestas/campanas/${state.currentInstanceId}/sections/${section.id}/questions`, {
      method: "POST",
      body: JSON.stringify({
        titulo,
        descripcion: String((questionModalDescription && questionModalDescription.value) || "").trim(),
        question_type: type,
        is_required: String((questionModalRequired && questionModalRequired.value) || "false") === "true",
        options: parseQuestionModalOptions(type),
      }),
    });
    await loadBuilder(state.currentInstanceId);
    setMessage(builderMsg, "Pregunta agregada.");
    if (keepOpen) {
      resetQuestionModal();
      return;
    }
    closeQuestionModal();
  }

  async function editQuestion(questionId) {
    const section = getCurrentSection();
    const question = section && (section.questions || []).find((item) => item.id === questionId);
    if (!question) return;
    const titulo = window.prompt("Editar pregunta", question.titulo || "");
    if (!titulo) return;
    const descripcion = window.prompt("Descripción", question.descripcion || "");
    const optionsText = ["single_choice", "live_poll_single_choice", "multiple_choice", "yes_no", "scale_1_5", "live_scale_1_5", "nps_0_10", "quiz_single_choice", "ranking", "matrix", "likert_scale", "semantic_differential", "dropdown", "image_choice", "true_false"].includes(question.question_type)
      ? window.prompt(
          "Opciones separadas por coma",
          (question.options || []).map((option) => option.label).join(", ")
        )
      : null;
    const payload = {
      titulo,
      descripcion,
      options: optionsText === null ? undefined : parseOptionsText(optionsText, question.question_type),
    };
    await fetchJSON(`/api/encuestas/campanas/${state.currentInstanceId}/questions/${questionId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
    await loadBuilder(state.currentInstanceId);
    setMessage(builderMsg, "Pregunta actualizada.");
  }

  async function duplicateQuestion(questionId) {
    await fetchJSON(`/api/encuestas/campanas/${state.currentInstanceId}/questions/${questionId}/duplicate`, {
      method: "POST",
    });
    await loadBuilder(state.currentInstanceId);
    setMessage(builderMsg, "Pregunta duplicada.");
  }

  async function reorderQuestion(questionId, direction) {
    const section = getCurrentSection();
    if (!section) return;
    const ids = (section.questions || []).map((item) => item.id);
    const index = ids.indexOf(questionId);
    const swapIndex = index + direction;
    if (index < 0 || swapIndex < 0 || swapIndex >= ids.length) return;
    const temp = ids[index];
    ids[index] = ids[swapIndex];
    ids[swapIndex] = temp;
    await fetchJSON(`/api/encuestas/campanas/${state.currentInstanceId}/sections/${section.id}/questions/reorder`, {
      method: "POST",
      body: JSON.stringify({ ids }),
    });
    await loadBuilder(state.currentInstanceId);
  }

  async function publishCampaign() {
    if (!state.currentInstanceId) return;
    await fetchJSON(`/api/encuestas/campanas/${state.currentInstanceId}/publish`, { method: "POST" });
    await loadCampaigns(false);
    await loadBuilder(state.currentInstanceId);
    setMessage(builderMsg, "Encuesta publicada.");
  }

  async function closeCampaign() {
    if (!state.currentInstanceId) return;
    await fetchJSON(`/api/encuestas/campanas/${state.currentInstanceId}/close`, { method: "POST" });
    await loadCampaigns(false);
    await loadBuilder(state.currentInstanceId);
    setMessage(builderMsg, "Encuesta cerrada.");
  }

  function bindNavigation() {
    navButtons.forEach((button) => {
      button.addEventListener("click", function () {
        showPanel(button.dataset.encNav);
      });
    });
    builderTabs.forEach((button) => {
      button.addEventListener("click", function () {
        showBuilderTab(button.dataset.encBuilderTab);
      });
    });
    surveyTabs.forEach((button) => {
      button.addEventListener("click", function () {
        showSurveyTab(button.dataset.encSurveyTab);
      });
    });
    questionModalTabs.forEach((button) => {
      button.addEventListener("click", function () {
        showQuestionModalTab(button.dataset.encQuestionTab);
      });
    });
  }

  function bindActions() {
    actionButtons.forEach((button) => {
      button.addEventListener("click", async function () {
        try {
          const action = button.dataset.encAction;
          if (action === "open-builder") {
            await loadCampaigns(true);
            showPanel("constructor");
            return;
          }
          if (action === "new-survey") {
            await createCampaign();
            showPanel("constructor");
            return;
          }
          if (action === "create-from-template") {
            await createCampaignFromTemplate();
            showPanel("constructor");
            return;
          }
          if (action === "save-as-template") {
            await saveAsTemplate();
            return;
          }
          if (action === "refresh-builder") {
            if (state.currentInstanceId) await loadBuilder(state.currentInstanceId);
            return;
          }
          if (action === "refresh-results") {
            const targetId = resultsSelect && resultsSelect.value ? resultsSelect.value : state.currentInstanceId;
            if (targetId) await loadResults(targetId);
            return;
          }
          if (action === "add-section") {
            await addSection();
            return;
          }
          if (action === "add-question") {
            await addQuestion();
            return;
          }
          if (action === "publish-campaign") {
            await publishCampaign();
            return;
          }
          if (action === "close-campaign") {
            await closeCampaign();
          }
        } catch (error) {
          setMessage(builderMsg, error.message, true);
        }
      });
    });

    root.addEventListener("click", async function (event) {
      const target = event.target.closest("button");
      if (!target) return;
      try {
        if (target.dataset.encCloseModal === "question") {
          closeQuestionModal();
        } else if (target.dataset.encModalType) {
          state.questionModalType = String(target.dataset.encModalType);
          if (questionModalOptions) {
            questionModalOptions.value = defaultOptionsText(state.questionModalType);
          }
          renderQuestionModalTypeList();
        } else if (target.dataset.encOpenBuilder) {
          showPanel("constructor");
          await loadBuilder(target.dataset.encOpenBuilder);
          renderBuilderSelect();
        } else if (target.dataset.encOpenResults) {
          showPanel("resultados");
          if (resultsSelect) resultsSelect.value = String(target.dataset.encOpenResults);
          await loadResults(target.dataset.encOpenResults);
        } else if (target.dataset.encSelectSection) {
          state.selectedSectionId = Number(target.dataset.encSelectSection);
          renderSections();
        } else if (target.dataset.encEditSection) {
          await editSection(Number(target.dataset.encEditSection));
        } else if (target.dataset.encSectionUp) {
          await reorderSection(Number(target.dataset.encSectionUp), -1);
        } else if (target.dataset.encSectionDown) {
          await reorderSection(Number(target.dataset.encSectionDown), 1);
        } else if (target.dataset.encEditQuestion) {
          await editQuestion(Number(target.dataset.encEditQuestion));
        } else if (target.dataset.encDuplicateQuestion) {
          await duplicateQuestion(Number(target.dataset.encDuplicateQuestion));
        } else if (target.dataset.encQuestionUp) {
          await reorderQuestion(Number(target.dataset.encQuestionUp), -1);
        } else if (target.dataset.encQuestionDown) {
          await reorderQuestion(Number(target.dataset.encQuestionDown), 1);
        }
      } catch (error) {
        setMessage(builderMsg, error.message, true);
      }
    });

    if (questionModalSaveClose) {
      questionModalSaveClose.addEventListener("click", async function () {
        try {
          await saveQuestionFromModal(false);
        } catch (error) {
          setMessage(builderMsg, error.message, true);
        }
      });
    }

    if (questionModalSaveNew) {
      questionModalSaveNew.addEventListener("click", async function () {
        try {
          await saveQuestionFromModal(true);
        } catch (error) {
          setMessage(builderMsg, error.message, true);
        }
      });
    }

    if (questionModalTitle) {
      questionModalTitle.addEventListener("input", renderQuestionModalPreview);
    }
    if (questionModalOptions) {
      questionModalOptions.addEventListener("input", renderQuestionModalPreview);
    }
  }

  function bindForms() {
    builderSelect.addEventListener("change", async function () {
      if (!builderSelect.value) return;
      await loadBuilder(builderSelect.value);
    });

    generalForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      try {
        await saveDraft(
          {
            nombre: document.getElementById("enc-general-nombre").value,
            descripcion: document.getElementById("enc-general-descripcion").value,
            publication_mode: document.getElementById("enc-general-publication-mode").value,
            schedule_start_at: document.getElementById("enc-general-start-at").value || null,
            schedule_end_at: document.getElementById("enc-general-end-at").value || null,
          },
          "Datos generales guardados."
        );
      } catch (error) {
        setMessage(builderMsg, error.message, true);
      }
    });

    audienceForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      try {
        const assignmentType = document.getElementById("enc-audience-assignment-type").value;
        const assignmentValues = parseCsvValues(document.getElementById("enc-audience-values").value);
        const manualGroups = parseManualGroups(document.getElementById("enc-audience-manual-group").value);
        const nextSettings = {
          ...(state.builder && state.builder.settings_json ? state.builder.settings_json : {}),
          audience_note: document.getElementById("enc-audience-group-note").value,
          assignment_type: assignmentType,
          assignment_values: assignmentValues,
          manual_groups: manualGroups,
        };
        await saveDraft(
          {
            audience_mode: document.getElementById("enc-audience-mode").value,
            source_app: document.getElementById("enc-audience-source-app").value,
            settings_json: nextSettings,
          },
          "Audiencia MAIN guardada."
        );
        await fetchJSON(`/api/encuestas/campanas/${state.currentInstanceId}/assignments/sync`, {
          method: "POST",
          body: JSON.stringify({
            assignments: assignmentValues.length ? [{ type: assignmentType, values: assignmentValues }] : [],
            manual_groups: manualGroups,
            due_at: nextSettings.assignment_due_at || null,
          }),
        });
        await loadBuilder(state.currentInstanceId);
        setMessage(builderMsg, "Audiencia guardada y materializada.");
      } catch (error) {
        setMessage(builderMsg, error.message, true);
      }
    });

    rulesForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      try {
        const rulesText = document.getElementById("enc-rules-json").value.trim();
        const publicationRules = rulesText ? JSON.parse(rulesText) : {};
        await saveDraft(
          {
            anonymity_mode: document.getElementById("enc-rules-anonymity-mode").value,
            settings_json: {
              ...(state.builder && state.builder.settings_json ? state.builder.settings_json : {}),
              scoring_mode: document.getElementById("enc-rules-scoring-mode").value,
            },
            publication_rules_json: publicationRules,
          },
          "Reglas guardadas."
        );
      } catch (error) {
        setMessage(builderMsg, error.message || "JSON inválido en reglas.", true);
      }
    });

    publicationForm.addEventListener("submit", async function (event) {
      event.preventDefault();
      try {
        const nextSettings = {
          ...(state.builder && state.builder.settings_json ? state.builder.settings_json : {}),
          assignment_due_at: document.getElementById("enc-publication-due-at").value || null,
        };
        await saveDraft(
          {
            is_public_link_enabled: document.getElementById("enc-public-link-enabled").value === "true",
            public_link_token: document.getElementById("enc-public-link-token").value,
            settings_json: nextSettings,
          },
          "Configuración de publicación guardada."
        );
      } catch (error) {
        setMessage(builderMsg, error.message, true);
      }
    });

    if (surveyOptionsForm) {
      surveyOptionsForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        try {
          await saveDraft(
            {
              audience_mode: editorAudienceMode ? editorAudienceMode.value : "internal",
              anonymity_mode: editorAnonymityMode ? editorAnonymityMode.value : "identified",
              publication_mode: editorPublicationMode ? editorPublicationMode.value : "manual",
              settings_json: {
                ...(state.builder && state.builder.settings_json ? state.builder.settings_json : {}),
                scoring_mode: editorScoringMode ? editorScoringMode.value : "none",
              },
            },
            "Opciones guardadas."
          );
        } catch (error) {
          setMessage(builderMsg, error.message, true);
        }
      });
    }

    if (surveyDescriptionForm) {
      surveyDescriptionForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        try {
          await saveDraft(
            {
              nombre: editorTitle ? editorTitle.value : "",
              descripcion: editorDescription ? editorDescription.value : "",
            },
            "Descripción guardada."
          );
        } catch (error) {
          setMessage(builderMsg, error.message, true);
        }
      });
    }

    if (surveyFinalMessageForm) {
      surveyFinalMessageForm.addEventListener("submit", async function (event) {
        event.preventDefault();
        try {
          await saveDraft(
            {
              publication_rules_json: {
                ...(state.builder && state.builder.publication_rules_json ? state.builder.publication_rules_json : {}),
                final_message: editorFinalMessage ? editorFinalMessage.value : "",
              },
            },
            "Mensaje final guardado."
          );
        } catch (error) {
          setMessage(builderMsg, error.message, true);
        }
      });
    }
  }

  function bindResultsFilters() {
    [resultsFilterDepartment, resultsFilterRole, resultsFilterCompany, resultsSegmentBy].forEach((node) => {
      if (!node) return;
      node.addEventListener("change", async function () {
        const targetId = resultsSelect && resultsSelect.value ? resultsSelect.value : state.currentInstanceId;
        if (!targetId) return;
        try {
          await loadResults(targetId);
          setMessage(resultsMsg, "Resultados filtrados.");
        } catch (error) {
          setMessage(resultsMsg, error.message, true);
        }
      });
    });
    if (resultsSelect) {
      resultsSelect.addEventListener("change", async function () {
        if (!resultsSelect.value) return;
        try {
          await loadResults(resultsSelect.value);
          setMessage(resultsMsg, "");
        } catch (error) {
          setMessage(resultsMsg, error.message, true);
        }
      });
    }
  }

  async function initialize() {
    paintMetrics();
    showPanel(initialPanel());
    bindNavigation();
    bindActions();
    bindForms();
    bindResultsFilters();
    await loadPermissions();
    await loadQuestionTypes();
    await loadTemplates();
    if (can("manage_surveys")) {
      await loadAssignableUsers();
    }
    await loadCampaigns(false);
    renderCampaigns();
    renderBuilderSelect();
    renderResults();
  }

  initialize().catch((error) => {
    setMessage(builderMsg, error.message, true);
    setMessage(campaignsMsg, error.message, true);
  });
})();
