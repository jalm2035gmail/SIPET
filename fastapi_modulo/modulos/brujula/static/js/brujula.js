(function () {
  const app = document.getElementById("brujula-indicadores-app");
  if (!app) return;

  const tabButtons = Array.from(app.querySelectorAll("[data-brujula-ind-tab]"));
  const tabPanels = Array.from(app.querySelectorAll("[data-brujula-ind-panel]"));
  const analysisModePanels = Array.from(app.querySelectorAll("[data-analysis-mode-panel]"));

  const matrixMsgEl = document.getElementById("brujula-ind-msg");
  const colgroupEl = document.getElementById("brujula-ind-colgroup");
  const theadEl = document.getElementById("brujula-ind-thead");
  const tbodyEl = document.getElementById("brujula-ind-tbody");

  const analysisMsgEl = document.getElementById("brujula-analysis-msg");
  const analysisModeEl = document.getElementById("brujula-analysis-mode");
  const analysisPeriodEl = document.getElementById("brujula-analysis-period");
  const analysisStatusEl = document.getElementById("brujula-analysis-status");
  const analysisQueryEl = document.getElementById("brujula-analysis-query");
  const analysisListEl = document.getElementById("brujula-analysis-list");

  const compareIndicatorsEl = document.getElementById("brujula-compare-indicators");
  const comparePeriodsEl = document.getElementById("brujula-compare-periods");
  const compareTheadEl = document.getElementById("brujula-compare-thead");
  const compareTbodyEl = document.getElementById("brujula-compare-tbody");

  const scenarioIndicatorEl = document.getElementById("brujula-scenario-indicator");
  const scenarioPeriodEl = document.getElementById("brujula-scenario-period");
  const scenarioTargetEl = document.getElementById("brujula-scenario-target");
  const scenarioMsgEl = document.getElementById("brujula-scenario-msg");
  const scenarioInputsEl = document.getElementById("brujula-scenario-inputs");
  const scenarioCurrentEl = document.getElementById("brujula-scenario-current");
  const scenarioResultEl = document.getElementById("brujula-scenario-result");
  const scenarioGapEl = document.getElementById("brujula-scenario-gap");
  const scenarioRecommendationEl = document.getElementById("brujula-scenario-recommendation");

  const kpiMsgEl = document.getElementById("brujula-kpi-msg");
  const kpiListEl = document.getElementById("brujula-kpi-list");

  let matrixPeriods = [];
  let matrixRows = [];
  let kpiDefinitionsCache = [];
  let scenarioDefinitions = [];
  const kpiSaveTimers = {};

  const escapeHtml = (value) =>
    String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");

  const parseNumber = (value) => {
    const raw = String(value ?? "").replace(/,/g, "").replace(/%/g, "").trim();
    if (!raw) return null;
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : null;
  };

  const parseMetaRule = (meta) => {
    const raw = String(meta ?? "").trim();
    if (!raw || /^n\/a$/i.test(raw)) return null;
    const match = raw.match(/^(>=|<=|>|<|=)?\s*(-?\d+(?:\.\d+)?)\s*%?$/);
    if (!match) return null;
    return { operator: match[1] || ">=", target: Number(match[2]) };
  };

  const evaluateMetaRule = (value, meta) => {
    const numeric = parseNumber(value);
    const rule = parseMetaRule(meta);
    if (numeric === null || !rule) return null;
    if (rule.operator === ">=") return numeric >= rule.target;
    if (rule.operator === "<=") return numeric <= rule.target;
    if (rule.operator === ">") return numeric > rule.target;
    if (rule.operator === "<") return numeric < rule.target;
    return numeric === rule.target;
  };

  const formatScenarioValue = (value, formatKind) => {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return "";
    if (formatKind === "percent") return `${Math.round(numeric)}%`;
    if (formatKind === "number") return `${Math.round(numeric)}`;
    return Math.round(numeric).toLocaleString("en-US");
  };

  const showText = (element, text, isError) => {
    if (!element) return;
    element.textContent = text || "";
    element.style.color = isError ? "#b91c1c" : "#0f3d2e";
  };

  const setTab = (tabKey) => {
    tabButtons.forEach((button) => {
      const active = button.getAttribute("data-brujula-ind-tab") === tabKey;
      button.classList.toggle("tab-active", active);
      button.classList.toggle("active", active);
    });
    tabPanels.forEach((panel) => {
      const visible = panel.getAttribute("data-brujula-ind-panel") === tabKey;
      panel.classList.toggle("hidden", !visible);
    });
  };

  const setAnalysisMode = (modeKey) => {
    if (analysisModeEl) analysisModeEl.value = modeKey;
    analysisModePanels.forEach((panel) => {
      const visible = panel.getAttribute("data-analysis-mode-panel") === modeKey;
      panel.classList.toggle("hidden", !visible);
    });
  };

  const normalizeMatrixRow = (row) => {
    const values = {};
    matrixPeriods.forEach((period) => {
      values[String(period.key)] = String(row?.values?.[period.key] || "").trim();
    });
    return {
      indicador: String(row?.indicador || "").trim(),
      values,
    };
  };

  const getMetaByIndicator = (name) => {
    const item = kpiDefinitionsCache.find((current) => String(current?.nombre || "").trim().toLowerCase() === String(name || "").trim().toLowerCase());
    return String(item?.estandar_meta || "").trim();
  };

  const getIndicatorEvaluation = (name, value) => {
    const currentValue = String(value || "").trim();
    const meta = getMetaByIndicator(name);
    if (!currentValue) return { status: "na", label: "Sin evaluacion", meta, value: currentValue };
    const meetsMeta = evaluateMetaRule(currentValue, meta);
    if (meetsMeta === true) return { status: "ok", label: "Cumple", meta, value: currentValue };
    if (meetsMeta === false) return { status: "fail", label: "No cumple", meta, value: currentValue };
    return { status: "na", label: "Sin evaluacion", meta, value: currentValue };
  };

  const renderMatrixTable = () => {
    if (!colgroupEl || !theadEl || !tbodyEl) return;
    colgroupEl.innerHTML = ['<col style="width:280px;min-width:280px">']
      .concat(matrixPeriods.map(() => '<col style="width:140px;min-width:140px">'))
      .join("");
    theadEl.innerHTML = `
      <tr>
        <th>Indicador</th>
        ${matrixPeriods.map((period) => `<th class="text-right">${escapeHtml(period.label)}<div class="text-xs opacity-60">${escapeHtml(period.kind)}</div></th>`).join("")}
      </tr>
    `;
    if (!matrixRows.length) {
      tbodyEl.innerHTML = `<tr><td colspan="${matrixPeriods.length + 1}" class="text-MAIN-content/60">Sin indicadores registrados.</td></tr>`;
      return;
    }
    tbodyEl.innerHTML = matrixRows.map((row) => `
      <tr>
        <td><div class="font-medium text-MAIN-content">${escapeHtml(row.indicador)}</div></td>
        ${matrixPeriods.map((period) => {
          const evaluation = getIndicatorEvaluation(row.indicador, row.values[period.key]);
          const className = evaluation.status === "ok" ? "text-status-ok" : evaluation.status === "fail" ? "text-status-fail" : "text-status-na";
          return `<td class="text-right ${className}">${escapeHtml(row.values[period.key] || "")}</td>`;
        }).join("")}
      </tr>
    `).join("");
  };

  const renderAnalysisPeriodOptions = () => {
    if (!analysisPeriodEl) return;
    analysisPeriodEl.innerHTML = matrixPeriods.map((period) => `<option value="${escapeHtml(period.key)}">${escapeHtml(period.label)} (${escapeHtml(period.kind)})</option>`).join("");
  };

  const renderAnalysisTable = () => {
    if (!analysisListEl || !analysisPeriodEl) return;
    const periodKey = String(analysisPeriodEl.value || "").trim();
    const statusFilter = String(analysisStatusEl?.value || "all").trim();
    const query = String(analysisQueryEl?.value || "").trim().toLowerCase();
    const rows = matrixRows
      .map((row) => {
        const evaluation = getIndicatorEvaluation(row.indicador, row.values[periodKey]);
        return { indicador: row.indicador, value: row.values[periodKey], meta: evaluation.meta, status: evaluation.status, label: evaluation.label };
      })
      .filter((row) => statusFilter === "all" || row.status === statusFilter)
      .filter((row) => !query || row.indicador.toLowerCase().includes(query));
    analysisListEl.innerHTML = rows.length ? rows.map((row) => `
      <tr>
        <td class="font-medium">${escapeHtml(row.indicador)}</td>
        <td class="text-right">${escapeHtml(row.value || "")}</td>
        <td class="text-right">${escapeHtml(row.meta || "")}</td>
        <td>${escapeHtml(row.label)}</td>
      </tr>
    `).join("") : '<tr><td colspan="4" class="text-MAIN-content/60">No hay indicadores para este filtro.</td></tr>';
    showText(analysisMsgEl, rows.length ? `${rows.length} indicadores encontrados.` : "", false);
  };

  const renderCompareIndicatorOptions = () => {
    if (!compareIndicatorsEl) return;
    compareIndicatorsEl.innerHTML = matrixRows.map((row, index) => `
      <label class="label cursor-pointer justify-start gap-2 rounded-full border border-MAIN-300 bg-MAIN-100 px-3 py-2 mb-2">
        <input type="checkbox" class="checkbox checkbox-sm" data-compare-indicator value="${escapeHtml(row.indicador)}" ${index < 3 ? "checked" : ""}>
        <span class="label-text">${escapeHtml(row.indicador)}</span>
      </label>
    `).join("");
    compareIndicatorsEl.querySelectorAll("[data-compare-indicator]").forEach((input) => input.addEventListener("change", renderCompareTable));
  };

  const renderComparePeriodOptions = () => {
    if (!comparePeriodsEl) return;
    comparePeriodsEl.innerHTML = matrixPeriods.map((period) => `
      <label class="label cursor-pointer justify-start gap-2 rounded-full border border-MAIN-300 bg-MAIN-100 px-3 py-2">
        <input type="checkbox" class="checkbox checkbox-sm" data-compare-period value="${escapeHtml(period.key)}" checked>
        <span class="label-text">${escapeHtml(period.label)} (${escapeHtml(period.kind)})</span>
      </label>
    `).join("");
    comparePeriodsEl.querySelectorAll("[data-compare-period]").forEach((input) => input.addEventListener("change", renderCompareTable));
  };

  const renderCompareTable = () => {
    if (!compareTheadEl || !compareTbodyEl) return;
    const selectedIndicators = Array.from(compareIndicatorsEl?.querySelectorAll("[data-compare-indicator]:checked") || []).map((input) => String(input.value || ""));
    const selectedPeriods = Array.from(comparePeriodsEl?.querySelectorAll("[data-compare-period]:checked") || []).map((input) => matrixPeriods.find((period) => String(period.key) === String(input.value || ""))).filter(Boolean);
    if (!selectedIndicators.length || !selectedPeriods.length) {
      compareTheadEl.innerHTML = "";
      compareTbodyEl.innerHTML = '<tr><td class="text-MAIN-content/60">Selecciona indicadores y periodos.</td></tr>';
      return;
    }
    compareTheadEl.innerHTML = `<tr><th>Indicador</th>${selectedPeriods.map((period) => `<th class="text-right">${escapeHtml(period.label)}</th>`).join("")}</tr>`;
    compareTbodyEl.innerHTML = selectedIndicators.map((name) => {
      const row = matrixRows.find((item) => item.indicador === name);
      if (!row) return "";
      return `<tr><td class="font-medium">${escapeHtml(name)}</td>${selectedPeriods.map((period) => `<td class="text-right">${escapeHtml(row.values[period.key] || "")}</td>`).join("")}</tr>`;
    }).join("");
  };

  const renderScenarioPeriodOptions = () => {
    if (!scenarioPeriodEl) return;
    scenarioPeriodEl.innerHTML = matrixPeriods.map((period) => `<option value="${escapeHtml(period.key)}">${escapeHtml(period.label)} (${escapeHtml(period.kind)})</option>`).join("");
  };

  const renderScenarioIndicatorOptions = () => {
    if (!scenarioIndicatorEl) return;
    scenarioIndicatorEl.innerHTML = scenarioDefinitions.map((item) => `<option value="${escapeHtml(item.indicador)}">${escapeHtml(item.indicador)}</option>`).join("");
  };

  const computeScenarioResult = (formulaKind, inputs) => {
    const values = Object.fromEntries((inputs || []).map((item) => [item.key, parseNumber(item.value)]));
    if (formulaKind === "ratio") {
      const numerator = values[inputs?.[0]?.key];
      const denominator = values[inputs?.[1]?.key];
      if (numerator == null || denominator == null || Math.abs(denominator) < 1e-9) return null;
      return numerator / denominator;
    }
    if (formulaKind === "difference") {
      const left = values[inputs?.[0]?.key];
      const right = values[inputs?.[1]?.key];
      if (left == null || right == null) return null;
      return left - right;
    }
    if (formulaKind === "growth") {
      if (values.current == null || values.previous == null || Math.abs(values.previous) < 1e-9) return null;
      return ((values.current - values.previous) / values.previous) * 100;
    }
    if (formulaKind === "ratio_average") {
      const numerator = values[inputs?.[0]?.key];
      const current = values[inputs?.[1]?.key];
      const previous = values[inputs?.[2]?.key];
      if (numerator == null || current == null || previous == null) return null;
      const denominator = (current + previous) / 2;
      if (Math.abs(denominator) < 1e-9) return null;
      return (numerator / denominator) * 100;
    }
    if (formulaKind === "direct") return values[inputs?.[0]?.key] ?? null;
    return null;
  };

  const renderScenarioSection = () => {
    if (!scenarioInputsEl || !scenarioIndicatorEl || !scenarioPeriodEl) return;
    const definition = scenarioDefinitions.find((item) => String(item.indicador || "") === String(scenarioIndicatorEl.value || ""));
    const periodData = definition?.periods?.[String(scenarioPeriodEl.value || "")];
    if (!definition || !periodData) {
      scenarioInputsEl.innerHTML = '<tr><td colspan="3" class="text-MAIN-content/60">Selecciona un indicador y un periodo.</td></tr>';
      if (scenarioCurrentEl) scenarioCurrentEl.textContent = "-";
      if (scenarioResultEl) scenarioResultEl.textContent = "-";
      if (scenarioGapEl) scenarioGapEl.textContent = "-";
      if (scenarioRecommendationEl) scenarioRecommendationEl.textContent = "Selecciona un indicador y un periodo.";
      return;
    }
    const inputs = Array.isArray(periodData.inputs) ? periodData.inputs.map((item) => ({ ...item, value: item.value })) : [];
    scenarioInputsEl.innerHTML = inputs.map((item) => `
      <tr>
        <td class="font-medium">${escapeHtml(item.label)}</td>
        <td class="text-right">${escapeHtml(formatScenarioValue(item.value, definition.format_kind) || "")}</td>
        <td class="text-right"><input class="input input-bordered input-sm w-full text-right" data-scenario-input="${escapeHtml(item.key)}" value="${escapeHtml(formatScenarioValue(item.value, definition.format_kind) || "")}"></td>
      </tr>
    `).join("");
    const update = () => {
      const scenarioValue = computeScenarioResult(definition.formula_kind, inputs);
      const targetRule = parseMetaRule(String(scenarioTargetEl?.value || definition.meta || "").trim());
      scenarioCurrentEl.textContent = String(periodData.result || "-");
      scenarioResultEl.textContent = formatScenarioValue(scenarioValue, definition.format_kind) || "-";
      if (!targetRule || scenarioValue == null) {
        scenarioGapEl.textContent = "-";
      } else {
        scenarioGapEl.textContent = formatScenarioValue(scenarioValue - targetRule.target, definition.format_kind);
      }
      scenarioRecommendationEl.textContent = "Ajusta los insumos para simular el resultado esperado.";
    };
    scenarioInputsEl.querySelectorAll("[data-scenario-input]").forEach((input) => {
      input.addEventListener("input", () => {
        const key = String(input.getAttribute("data-scenario-input") || "");
        const match = inputs.find((item) => item.key === key);
        if (match) match.value = input.value;
        update();
      });
    });
    update();
    showText(scenarioMsgEl, "", false);
  };

  const normalizeKpi = (item) => ({
    id: Number(item?.id || 0) || 0,
    nombre: String(item?.nombre || "").trim(),
    estandar_meta: String(item?.estandar_meta || "").trim(),
    semaforo_rojo: String(item?.semaforo_rojo || "").trim(),
    semaforo_verde: String(item?.semaforo_verde || "").trim(),
  });

  const renderKpiList = () => {
    if (!kpiListEl) return;
    kpiListEl.innerHTML = kpiDefinitionsCache.length ? kpiDefinitionsCache.map((item) => `
      <tr>
        <td class="font-medium">${escapeHtml(item.nombre)}</td>
        <td class="text-right"><input class="input input-bordered input-sm w-full text-right" data-kpi-field="estandar_meta" data-kpi-name="${escapeHtml(item.nombre)}" value="${escapeHtml(item.estandar_meta)}"></td>
        <td class="text-right"><input class="input input-bordered input-sm w-full text-right" data-kpi-field="semaforo_rojo" data-kpi-name="${escapeHtml(item.nombre)}" value="${escapeHtml(item.semaforo_rojo)}"></td>
        <td class="text-right"><input class="input input-bordered input-sm w-full text-right" data-kpi-field="semaforo_verde" data-kpi-name="${escapeHtml(item.nombre)}" value="${escapeHtml(item.semaforo_verde)}"></td>
        <td><span class="text-xs text-MAIN-content/60" data-kpi-status="${escapeHtml(item.nombre)}">Listo</span></td>
      </tr>
    `).join("") : '<tr><td colspan="5" class="text-MAIN-content/60">Sin indicadores registrados.</td></tr>';
    kpiListEl.querySelectorAll("[data-kpi-field]").forEach((input) => {
      const name = String(input.getAttribute("data-kpi-name") || "");
      input.addEventListener("change", () => scheduleKpiSave(name));
      input.addEventListener("blur", () => scheduleKpiSave(name));
    });
  };

  const setKpiStatus = (name, text, isError) => {
    const element = kpiListEl?.querySelector(`[data-kpi-status="${CSS.escape(name)}"]`);
    if (!element) return;
    element.textContent = text;
    element.style.color = isError ? "#b91c1c" : "#0f3d2e";
  };

  const collectKpiPayload = (name) => {
    const pick = (field) => kpiListEl?.querySelector(`[data-kpi-field="${field}"][data-kpi-name="${CSS.escape(name)}"]`);
    return {
      nombre: name,
      estandar_meta: String(pick("estandar_meta")?.value || "").trim(),
      semaforo_rojo: String(pick("semaforo_rojo")?.value || "").trim(),
      semaforo_verde: String(pick("semaforo_verde")?.value || "").trim(),
    };
  };

  const saveKpiRow = async (name) => {
    const response = await fetch("/api/brujula/indicadores/definicion", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify(collectKpiPayload(name)),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload?.success === false) throw new Error(payload?.error || "No se pudo guardar la configuracion.");
    const updated = normalizeKpi(payload?.data || {});
    kpiDefinitionsCache = kpiDefinitionsCache.map((item) => item.nombre === updated.nombre ? { ...item, ...updated } : item);
    setKpiStatus(name, "Guardado", false);
    renderAnalysisTable();
    renderScenarioSection();
  };

  const scheduleKpiSave = (name) => {
    if (!name) return;
    window.clearTimeout(kpiSaveTimers[name]);
    setKpiStatus(name, "Pendiente...", false);
    kpiSaveTimers[name] = window.setTimeout(() => {
      saveKpiRow(name).catch((error) => {
        setKpiStatus(name, error?.message || "Error", true);
        showText(kpiMsgEl, error?.message || "No se pudo guardar la configuracion.", true);
      });
    }, 250);
  };

  const loadMatrix = async () => {
    showText(matrixMsgEl, "Cargando indicadores...", false);
    const response = await fetch("/api/brujula/indicadores/notebook", { credentials: "same-origin" });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload?.success === false) throw new Error(payload?.error || "No se pudo cargar indicadores.");
    matrixPeriods = Array.isArray(payload?.data?.periods) ? payload.data.periods : [];
    matrixRows = Array.isArray(payload?.data?.rows) ? payload.data.rows.map(normalizeMatrixRow) : [];
    renderAnalysisPeriodOptions();
    renderCompareIndicatorOptions();
    renderComparePeriodOptions();
    renderScenarioPeriodOptions();
    renderMatrixTable();
    renderAnalysisTable();
    renderCompareTable();
    renderScenarioSection();
    showText(matrixMsgEl, "", false);
  };

  const loadDefinitions = async () => {
    showText(kpiMsgEl, "Cargando descripciones...", false);
    const response = await fetch("/api/brujula/indicadores/definiciones", { credentials: "same-origin" });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload?.success === false) throw new Error(payload?.error || "No se pudo cargar indicadores.");
    kpiDefinitionsCache = Array.isArray(payload?.data) ? payload.data.map(normalizeKpi) : [];
    renderKpiList();
    showText(kpiMsgEl, "", false);
  };

  const loadScenarios = async () => {
    showText(scenarioMsgEl, "Cargando escenarios...", false);
    const response = await fetch("/api/brujula/indicadores/escenario", { credentials: "same-origin" });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload?.success === false) throw new Error(payload?.error || "No se pudo cargar escenarios.");
    scenarioDefinitions = Array.isArray(payload?.data?.scenarios) ? payload.data.scenarios : [];
    renderScenarioIndicatorOptions();
    renderScenarioSection();
    showText(scenarioMsgEl, "", false);
  };

  tabButtons.forEach((button) => button.addEventListener("click", () => setTab(button.getAttribute("data-brujula-ind-tab") || "matrix")));
  if (analysisModeEl) analysisModeEl.addEventListener("change", (event) => setAnalysisMode(event.target.value));
  if (analysisPeriodEl) analysisPeriodEl.addEventListener("change", renderAnalysisTable);
  if (analysisStatusEl) analysisStatusEl.addEventListener("change", renderAnalysisTable);
  if (analysisQueryEl) analysisQueryEl.addEventListener("input", renderAnalysisTable);
  if (scenarioIndicatorEl) scenarioIndicatorEl.addEventListener("change", renderScenarioSection);
  if (scenarioPeriodEl) scenarioPeriodEl.addEventListener("change", renderScenarioSection);
  if (scenarioTargetEl) scenarioTargetEl.addEventListener("input", renderScenarioSection);

  setTab("matrix");
  setAnalysisMode("summary");
  Promise.all([loadMatrix(), loadDefinitions(), loadScenarios()]).catch((error) => {
    showText(matrixMsgEl, error?.message || "No se pudo cargar indicadores.", true);
    showText(kpiMsgEl, error?.message || "No se pudo cargar descripciones.", true);
    showText(scenarioMsgEl, error?.message || "No se pudo cargar escenarios.", true);
  });
})();
