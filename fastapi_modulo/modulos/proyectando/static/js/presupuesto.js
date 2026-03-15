  (function() {
    const initPresupuestoPage = function() {
    const presupuestoTabs = Array.from(document.querySelectorAll(".presupuesto-notebook [data-presupuesto-tab]"));
    const presupuestoPanels = Array.from(document.querySelectorAll(".presupuesto-notebook .presupuesto-tab-panel[data-presupuesto-panel]"));
    const setPresupuestoTab = (tabKey) => {
      const target = String(tabKey || "presupuesto-anual");
      presupuestoTabs.forEach((tabBtn) => {
        const on = (tabBtn.getAttribute("data-presupuesto-tab") || "") === target;
        tabBtn.classList.toggle("tab-active", on);
        tabBtn.classList.toggle("active", on);
      });
      presupuestoPanels.forEach((panelEl) => {
        const show = (panelEl.getAttribute("data-presupuesto-panel") || "") === target;
        panelEl.hidden = !show;
        panelEl.style.display = show ? "block" : "none";
      });
    };
    presupuestoTabs.forEach((tabBtn) => {
      tabBtn.addEventListener("click", () => {
        setPresupuestoTab(tabBtn.getAttribute("data-presupuesto-tab") || "presupuesto-anual");
      });
    });
    setPresupuestoTab("presupuesto-anual");

    const btn = document.getElementById("toggle-cod-col-btn");
    const importBtn = document.getElementById("presupuesto-import-btn");
    const importFileInput = document.getElementById("presupuesto-import-file");
    const importStatusEl = document.getElementById("presupuesto-action-status");
    const saveBtn = document.querySelector(".dg-save-trigger");
    const saveStatusEl = document.querySelector(".dg-save-status");
    const reportesPanel = document.querySelector('.presupuesto-tab-panel[data-presupuesto-panel="reportes"]');
    const reportesFullscreenBtn = document.getElementById("reportes-fullscreen-btn");
    const reportesFiltroNivelEl = document.getElementById("reportes-filtro-nivel");
    const reportesFiltroElementoEl = document.getElementById("reportes-filtro-elemento");
    const reportesFiltroAplicarBtn = document.getElementById("reportes-filtro-aplicar");
    const reportesFiltroNoteEl = document.getElementById("reportes-filtro-note");
    const controlMensualAccBtn = document.getElementById("control-mensual-acc-btn");
    const controlMensualAccModal = document.getElementById("control-mensual-acc-modal");
    const controlMensualAccClose = document.getElementById("control-mensual-acc-close");
    const controlMensualAccTableBody = document.querySelector("#control-mensual-acc-table tbody");
    const annualCycleSelect = document.getElementById("annual-cycle-select");
    const annualCycleStartBtn = document.getElementById("annual-cycle-start-btn");
    const annualCycleArchiveLink = document.getElementById("annual-cycle-archive-link");
    const annualCycleStatusEl = document.getElementById("annual-cycle-status");
    const codCols = document.querySelectorAll("#presupuesto-table .cod-col");
    let annualCycleState = null;
    let visible = false;
    if (btn) {
      btn.addEventListener("click", function() {
        visible = !visible;
        codCols.forEach((col) => {
          col.style.display = visible ? "table-cell" : "none";
        });
        btn.textContent = visible ? "-" : "+";
      });
    }

    const normalizeInteger = (rawValue) => {
      const raw = String(rawValue || "").trim();
      if (!raw) return "";
      const normalized = raw.replace(/,/g, "");
      const value = Number(normalized);
      if (!Number.isFinite(value)) return raw;
      return Math.round(value).toLocaleString("en-US", { maximumFractionDigits: 0 });
    };

    document.querySelectorAll("#presupuesto-table .presupuesto-num-input").forEach((input) => {
      input.value = normalizeInteger(input.value);
      input.style.setProperty("text-align", "right", "important");
    });

    document.querySelectorAll("#presupuesto-table .presupuesto-mensual").forEach((cell) => {
      cell.textContent = normalizeInteger(cell.textContent);
      cell.style.setProperty("text-align", "right", "important");
    });

    const controlMensualTable = document.getElementById("control-mensual-table");
    const presupuestoTable = document.getElementById("presupuesto-table");
    const months = ["01","02","03","04","05","06","07","08","09","10","11","12"];
    const reportScopeState = { level: "consolidado", element: "global", departments: [] };
    let reportScopeItemsByValue = new Map();
    const setImportStatus = (message, isError = false) => {
      if (!importStatusEl) return;
      importStatusEl.textContent = String(message || "");
      importStatusEl.style.color = isError ? "#b91c1c" : "#0f3d2e";
    };
    const setSaveStatus = (message, isError = false) => {
      if (!saveStatusEl) return;
      saveStatusEl.textContent = String(message || "");
      saveStatusEl.style.color = isError ? "#b91c1c" : "#0f3d2e";
    };
    const setAnnualCycleStatus = (message, isError = false) => {
      if (!annualCycleStatusEl) return;
      annualCycleStatusEl.textContent = String(message || "");
      annualCycleStatusEl.style.color = isError ? "#b91c1c" : "#475569";
    };
    const normalizeRubroKey = (value) => (
      String(value || "")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .replace(/[.,]/g, " ")
        .replace(/\s+/g, " ")
        .trim()
        .toUpperCase()
    );
    const parseIntegerValue = (rawValue) => {
      const raw = String(rawValue || "").trim();
      if (!raw) return 0;
      const normalized = raw.replace(/,/g, "");
      const value = Number(normalized);
      if (!Number.isFinite(value)) return 0;
      return Math.round(value);
    };
    const formatIntegerValue = (value) => {
      const numeric = Number(value || 0);
      return Number.isFinite(numeric) ? numeric.toLocaleString("en-US", { maximumFractionDigits: 0 }) : "0";
    };
    const formatPercentOneDecimal = (value) => {
      const numeric = Number(value || 0);
      if (!Number.isFinite(numeric)) return "0.0%";
      return `${numeric.toFixed(1)}%`;
    };
    const formatCurrency = (value) => `$${formatIntegerValue(value)}`;
    const collectPresupuestoRows = () => {
      if (!presupuestoTable) return [];
      return Array.from(presupuestoTable.querySelectorAll("tbody tr")).map((row) => {
        const cod = (row.querySelector(".cod-col")?.textContent || "").trim();
        const rubro = (row.querySelector(".rubro-col")?.textContent || "").trim();
        const monto = parseIntegerValue(row.querySelector(".presupuesto-num-input")?.value || "0");
        return { cod, rubro, monto };
      }).filter((item) => item.rubro);
    };
    const savePresupuestoAnual = async () => {
      if (!presupuestoTable) return;
      const rows = collectPresupuestoRows();
      const response = await fetch("/proyectando/guardar-presupuesto-anual", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rows }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload?.success === false) {
        throw new Error(payload?.error || "No se pudo guardar el presupuesto anual.");
      }
    };
    const loadAnnualCycleContext = async () => {
      if (!annualCycleSelect) return;
      try {
        const response = await fetch("/api/annual-cycle/context", { credentials: "same-origin" });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok || payload?.success === false) {
          throw new Error(payload?.error || "No se pudo cargar el ejercicio activo.");
        }
        annualCycleState = payload.data || {};
        const years = Array.isArray(annualCycleState.years) ? annualCycleState.years : [];
        annualCycleSelect.innerHTML = years.map((year) => (
          `<option value="${year}" ${Number(year) === Number(annualCycleState.active_year) ? "selected" : ""}>${year}</option>`
        )).join("");
        const previousYear = Number(annualCycleState.active_year || 0) - 1;
        const archiveItem = (Array.isArray(annualCycleState.archives) ? annualCycleState.archives : []).find((item) => Number(item.year) === previousYear);
        if (annualCycleArchiveLink && archiveItem) {
          annualCycleArchiveLink.hidden = false;
          annualCycleArchiveLink.href = archiveItem.download_url;
        } else if (annualCycleArchiveLink) {
          annualCycleArchiveLink.hidden = true;
          annualCycleArchiveLink.removeAttribute("href");
        }
        setAnnualCycleStatus(`Ejercicio activo: ${annualCycleState.active_year}.`);
      } catch (error) {
        setAnnualCycleStatus(error.message || "No se pudo cargar el ejercicio activo.", true);
      }
    };
    const startAnnualCycle = async () => {
      if (!annualCycleSelect) return;
      const suggestedYear = Number((annualCycleState && annualCycleState.next_year_suggestion) || Number(annualCycleSelect.value || 0) + 1 || new Date().getFullYear() + 1);
      const raw = window.prompt("¿Qué año quieres iniciar?", String(suggestedYear));
      if (!raw) return;
      const year = Number(String(raw).trim());
      if (!Number.isFinite(year) || year < 2000) {
        setAnnualCycleStatus("Debes capturar un año válido.", true);
        return;
      }
      setAnnualCycleStatus("Iniciando nuevo ejercicio...");
      const response = await fetch("/api/annual-cycle/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ year }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload?.success === false) {
        throw new Error(payload?.error || "No se pudo iniciar el nuevo ejercicio.");
      }
      window.location.reload();
    };
    const setReportFilterNote = (message, warn = false) => {
      if (!reportesFiltroNoteEl) return;
      reportesFiltroNoteEl.textContent = String(message || "");
      reportesFiltroNoteEl.classList.toggle("warn", !!warn);
    };
    const inferDepartmentFromRubro = (rubro) => {
      const text = String(rubro || "").toLowerCase();
      if (text.includes("interes") || text.includes("moratorio") || text.includes("normal")) return "Crédito";
      if (text.includes("comisiones") || text.includes("productos")) return "Comercial";
      if (text.includes("salarios") || text.includes("aguinaldo") || text.includes("prestaciones") || text.includes("honorarios")) return "Administración";
      if (text.includes("tecnologia")) return "Tecnología";
      if (text.includes("impuestos") || text.includes("derechos")) return "Cumplimiento";
      if (text.includes("promocion") || text.includes("publicidad")) return "Marketing";
      if (text.includes("depreciaciones") || text.includes("amortizaciones") || text.includes("costo neto")) return "Finanzas";
      return "Sucursal Centro";
    };
    const normalizeScopeKey = (value) => (
      String(value || "")
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, " ")
        .trim()
    );
    const canonicalDepartmentKey = (value) => {
      const key = normalizeScopeKey(value);
      if (["ti", "it", "tecnologia", "tecnologia de la informacion", "sistemas"].includes(key)) return "tecnologia";
      if (["administracion", "administrativo"].includes(key)) return "administracion";
      if (["credito", "credito y cobranza"].includes(key)) return "credito";
      if (["comercial", "ventas"].includes(key)) return "comercial";
      if (["marketing", "mercadotecnia"].includes(key)) return "marketing";
      if (["finanzas", "financiero"].includes(key)) return "finanzas";
      if (["cumplimiento", "juridico", "legal"].includes(key)) return "cumplimiento";
      return key;
    };
    const allControlDetailRows = () => {
      if (!controlMensualTable) return [];
      return Array.from(controlMensualTable.querySelectorAll("tbody tr.control-mensual-detail-row"));
    };
    const matchesScopeDepartments = (areaName, departments) => {
      const areaKey = canonicalDepartmentKey(areaName);
      const depKeys = (departments || []).map((item) => canonicalDepartmentKey(item)).filter(Boolean);
      if (!depKeys.length) return true;
      return depKeys.some((dep) => areaKey === dep || areaKey.includes(dep) || dep.includes(areaKey));
    };
    const getScopedDetailRows = () => {
      const rows = allControlDetailRows();
      if (reportScopeState.level === "consolidado") return rows;
      return rows.filter((row) => {
        const rubro = (row.querySelector("td:first-child")?.textContent || "").trim();
        const area = inferDepartmentFromRubro(rubro);
        return matchesScopeDepartments(area, reportScopeState.departments);
      });
    };
    const getScopedMonthTotals = (month) => {
      const detailRows = getScopedDetailRows();
      let ingresosProjected = 0;
      let ingresosRealized = 0;
      let egresosProjected = 0;
      let egresosRealized = 0;
      detailRows.forEach((row) => {
        const tipo = (row.getAttribute("data-tipo") || "").toLowerCase();
        const projectedInput = row.querySelector(`input[name*="_${month}_proyectado"]`);
        const realizedInput = row.querySelector(`input[name*="_${month}_realizado"]`);
        const projected = parseIntegerValue(projectedInput?.value || "0");
        const realized = parseIntegerValue(realizedInput?.value || "0");
        if (tipo === "ingreso") {
          ingresosProjected += projected;
          ingresosRealized += realized;
        } else if (tipo === "egreso") {
          egresosProjected += projected;
          egresosRealized += realized;
        }
      });
      return {
        ingresosProjected,
        ingresosRealized,
        egresosProjected,
        egresosRealized,
        resultadoProjected: ingresosProjected - egresosProjected,
        resultadoRealized: ingresosRealized - egresosRealized,
      };
    };
    const getScopedSummaryValue = (rowClass, month, kind) => {
      const totals = getScopedMonthTotals(month);
      if (rowClass === "control-mensual-total-ingresos") {
        if (kind === "proyectado") return totals.ingresosProjected;
        if (kind === "realizado") return totals.ingresosRealized;
      }
      if (rowClass === "control-mensual-total-egresos") {
        if (kind === "proyectado") return totals.egresosProjected;
        if (kind === "realizado") return totals.egresosRealized;
      }
      if (rowClass === "control-mensual-resultado") {
        if (kind === "proyectado") return totals.resultadoProjected;
        if (kind === "realizado") return totals.resultadoRealized;
      }
      return 0;
    };
    const getScopedYearValue = (rowClass, kind) => months.reduce((acc, month) => (
      acc + getScopedSummaryValue(rowClass, month, kind)
    ), 0);
    const refreshReportesByScope = () => {
      updateReporteEjecutivo();
      updateReporteDesviaciones();
      updateReporteTendencia();
      updateReporteEjecucionArea();
      updateReporteComposicionGasto();
      updateReporteKpisSipet();
      updateReporteMapaCalor();
      updateAlertasInteligentes();
      updateControlDashboard();
    };
    const setScopeFromSelectedElement = () => {
      const level = String(reportesFiltroNivelEl?.value || "consolidado");
      const value = String(reportesFiltroElementoEl?.value || "");
      const selected = reportScopeItemsByValue.get(value) || null;
      const departments = Array.isArray(selected?.departments)
        ? selected.departments.filter((item) => String(item || "").trim())
        : [];
      reportScopeState.level = level;
      reportScopeState.element = value;
      reportScopeState.departments = departments;
      if (level === "consolidado") {
        setReportFilterNote("Vista consolidada del presupuesto.");
      } else if (!departments.length) {
        setReportFilterNote("El elemento seleccionado no tiene departamentos relacionados; se mantiene consolidado.", true);
      } else {
        setReportFilterNote(`Filtro aplicado: ${level} (${selected?.label || value}).`);
      }
      refreshReportesByScope();
    };
    const loadReportFilterElements = async (level, preserveSelection = false) => {
      if (!reportesFiltroElementoEl) return;
      reportesFiltroElementoEl.innerHTML = `<option value="">Cargando...</option>`;
      try {
        const response = await fetch(`/proyectando/presupuesto-reportes-filtros?nivel=${encodeURIComponent(level)}`);
        const payload = await response.json();
        if (!response.ok || !payload?.success) {
          throw new Error(payload?.error || "No se pudieron cargar filtros");
        }
        const items = Array.isArray(payload.items) ? payload.items : [];
        reportScopeItemsByValue = new Map();
        const options = items.map((item) => {
          const value = String(item?.value || "").trim();
          const label = String(item?.label || value || "").trim();
          if (!value) return "";
          reportScopeItemsByValue.set(value, {
            value,
            label,
            departments: Array.isArray(item?.departments) ? item.departments : [],
          });
          return `<option value="${value}">${label}</option>`;
        }).join("");
        reportesFiltroElementoEl.innerHTML = options || `<option value="">Sin elementos</option>`;
        if (preserveSelection && reportScopeState.element && reportScopeItemsByValue.has(reportScopeState.element)) {
          reportesFiltroElementoEl.value = reportScopeState.element;
        }
        if (!reportesFiltroElementoEl.value && reportesFiltroElementoEl.options.length) {
          reportesFiltroElementoEl.selectedIndex = 0;
        }
      } catch (error) {
        reportesFiltroElementoEl.innerHTML = `<option value="">Sin datos</option>`;
        setReportFilterNote(String(error?.message || error || "No se pudieron cargar filtros"), true);
      }
    };
    const getSummaryValue = (rowClass, month, kind) => {
      const row = controlMensualTable?.querySelector(`tbody tr.${rowClass}`);
      if (!row) return 0;
      const input = row.querySelector(`input[data-summary-month="${month}"][data-summary-kind="${kind}"]`);
      return parseIntegerValue(input?.value || "0");
    };
    const getSummaryYearValue = (rowClass, kind) => (
      months.reduce((acc, month) => acc + getSummaryValue(rowClass, month, kind), 0)
    );
    const getRowYearValue = (row, kind) => (
      months.reduce((acc, month) => {
        const input = row?.querySelector(`input[name*="_${month}_${kind}"]`);
        return acc + parseIntegerValue(input?.value || "0");
      }, 0)
    );
    const buildControlMonthlyCells = (rowIndex, mensualMAIN) => {
      const cells = [];
      const MAIN = parseIntegerValue(mensualMAIN);
      months.forEach((month) => {
        const projectedValue = formatIntegerValue(MAIN);
        cells.push(`<td class="tabla-oficial-num month-col month-${month}" data-month-col="${month}"><input class="tabla-oficial-input num" type="text" name="cm_${rowIndex}_${month}_proyectado" value="${projectedValue}" inputmode="numeric"></td>`);
        cells.push(`<td class="tabla-oficial-num month-col month-${month}" data-month-col="${month}"><input class="tabla-oficial-input num" type="text" name="cm_${rowIndex}_${month}_realizado" value="0" inputmode="numeric"></td>`);
        cells.push(`<td class="tabla-oficial-num month-col month-${month} month-percent-col" data-month-col="${month}"><input class="tabla-oficial-input num cm-percent-input" type="text" name="cm_${rowIndex}_${month}_percent" value="0%" inputmode="numeric" readonly></td>`);
      });
      return cells.join("");
    };
    const buildControlSummaryCells = () => {
      const cells = [];
      months.forEach((month) => {
        cells.push(`<td class="tabla-oficial-num month-col month-${month}" data-month-col="${month}"><input class="tabla-oficial-input num" type="text" data-summary-month="${month}" data-summary-kind="proyectado" value="0" readonly></td>`);
        cells.push(`<td class="tabla-oficial-num month-col month-${month}" data-month-col="${month}"><input class="tabla-oficial-input num" type="text" data-summary-month="${month}" data-summary-kind="realizado" value="0" readonly></td>`);
        cells.push(`<td class="tabla-oficial-num month-col month-${month} month-percent-col" data-month-col="${month}"><input class="tabla-oficial-input num cm-percent-input" type="text" data-summary-month="${month}" data-summary-kind="percent" value="0%" readonly></td>`);
      });
      return cells.join("");
    };
    const computePercentValue = (projectedRaw, realizedRaw) => {
      const projected = parseIntegerValue(projectedRaw);
      const realized = parseIntegerValue(realizedRaw);
      if (projected <= 0) return "0%";
      const pct = (realized / projected) * 100;
      return `${pct.toFixed(1)}%`;
    };
    const recalcControlMensualRow = (row) => {
      if (!row) return;
      months.forEach((month) => {
        const projectedInput = row.querySelector(`input[name*="_${month}_proyectado"]`);
        const realizedInput = row.querySelector(`input[name*="_${month}_realizado"]`);
        const percentInput = row.querySelector(`input[name*="_${month}_percent"]`);
        if (!projectedInput || !realizedInput || !percentInput) return;
        percentInput.value = computePercentValue(projectedInput.value, realizedInput.value);
      });
    };
    const bindControlMensualFormula = () => {
      if (!controlMensualTable) return;
      const rows = Array.from(controlMensualTable.querySelectorAll("tbody tr"));
      rows.forEach((row) => {
        if (!row.classList.contains("control-mensual-detail-row")) return;
        const projectedAndRealInputs = row.querySelectorAll('input[name*="_proyectado"], input[name*="_realizado"]');
        projectedAndRealInputs.forEach((input) => {
          input.addEventListener("input", () => {
            recalcControlMensualRow(row);
            recalcControlMensualTotals();
          });
        });
        recalcControlMensualRow(row);
      });
    };
    const recalcControlMensualTotals = () => {
      if (!controlMensualTable) return;
      const detailRows = getScopedDetailRows();
      const totalIngresosRow = controlMensualTable.querySelector("tbody tr.control-mensual-total-ingresos");
      const totalEgresosRow = controlMensualTable.querySelector("tbody tr.control-mensual-total-egresos");
      const resultadoRow = controlMensualTable.querySelector("tbody tr.control-mensual-resultado");
      if (!totalIngresosRow || !totalEgresosRow || !resultadoRow) return;

      months.forEach((month) => {
        let ingresosProjected = 0;
        let ingresosRealized = 0;
        let egresosProjected = 0;
        let egresosRealized = 0;

        detailRows.forEach((row) => {
          const tipo = (row.getAttribute("data-tipo") || "").toLowerCase();
          const projectedInput = row.querySelector(`input[name*="_${month}_proyectado"]`);
          const realizedInput = row.querySelector(`input[name*="_${month}_realizado"]`);
          const projected = parseIntegerValue(projectedInput?.value || "0");
          const realized = parseIntegerValue(realizedInput?.value || "0");
          if (tipo === "ingreso") {
            ingresosProjected += projected;
            ingresosRealized += realized;
          } else if (tipo === "egreso") {
            egresosProjected += projected;
            egresosRealized += realized;
          }
        });

        const resultadoProjected = ingresosProjected - egresosProjected;
        const resultadoRealized = ingresosRealized - egresosRealized;

        const setSummary = (row, kind, value) => {
          const input = row.querySelector(`input[data-summary-month="${month}"][data-summary-kind="${kind}"]`);
          if (input) input.value = value;
        };

        setSummary(totalIngresosRow, "proyectado", formatIntegerValue(ingresosProjected));
        setSummary(totalIngresosRow, "realizado", formatIntegerValue(ingresosRealized));
        setSummary(totalIngresosRow, "percent", computePercentValue(ingresosProjected, ingresosRealized));

        setSummary(totalEgresosRow, "proyectado", formatIntegerValue(egresosProjected));
        setSummary(totalEgresosRow, "realizado", formatIntegerValue(egresosRealized));
        setSummary(totalEgresosRow, "percent", computePercentValue(egresosProjected, egresosRealized));

        setSummary(resultadoRow, "proyectado", formatIntegerValue(resultadoProjected));
        setSummary(resultadoRow, "realizado", formatIntegerValue(resultadoRealized));
        setSummary(resultadoRow, "percent", computePercentValue(resultadoProjected, resultadoRealized));
      });
      updateReporteEjecutivo();
      refreshReportesByScope();
    };
    const updateControlDashboard = () => {
      if (!controlMensualTable) return;
      const monthNames = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"];
      const getSummaryValue = (rowClass, month, kind) => {
        const row = controlMensualTable.querySelector(`tbody tr.${rowClass}`);
        if (!row) return 0;
        const input = row.querySelector(`input[data-summary-month="${month}"][data-summary-kind="${kind}"]`);
        return parseIntegerValue(input?.value || "0");
      };
      const ingP = getScopedYearValue("control-mensual-total-ingresos", "proyectado");
      const ingR = getScopedYearValue("control-mensual-total-ingresos", "realizado");
      const egrP = getScopedYearValue("control-mensual-total-egresos", "proyectado");
      const egrR = getScopedYearValue("control-mensual-total-egresos", "realizado");
      const resP = getScopedYearValue("control-mensual-resultado", "proyectado");
      const resR = getScopedYearValue("control-mensual-resultado", "realizado");
      const setText = (id, value) => { const el = document.getElementById(id); if (el) el.textContent = value; };
      setText("cp-kpi-ingresos", formatCurrency(ingR));
      setText("cp-kpi-ingresos-pct", formatPercentOneDecimal(ingP > 0 ? (ingR / ingP) * 100 : 0));
      setText("cp-kpi-egresos", formatCurrency(egrR));
      setText("cp-kpi-egresos-pct", formatPercentOneDecimal(egrP > 0 ? (egrR / egrP) * 100 : 0));
      setText("cp-kpi-resultado", formatCurrency(resR));
      setText("cp-kpi-resultado-delta", `${resR - resP >= 0 ? "+" : ""}${formatCurrency(resR - resP)}`);
      const detailRows = getScopedDetailRows();
      const avgDesv = detailRows.length ? detailRows.reduce((acc, row) => {
        const p = getRowYearValue(row, "proyectado");
        const r = getRowYearValue(row, "realizado");
        return acc + (p !== 0 ? Math.abs(((r - p) / p) * 100) : 0);
      }, 0) / detailRows.length : 0;
      setText("cp-kpi-desv-prom", formatPercentOneDecimal(avgDesv));
      setText("cp-kpi-riesgo", `${avgDesv >= 0 ? "-" : ""}${formatPercentOneDecimal(avgDesv)}`);
      const pointer = document.getElementById("cp-gauge-pointer");
      if (pointer) pointer.style.left = `${Math.max(0, Math.min(100, avgDesv))}%`;

      const monthly = months.map((m, i) => ({
        label: monthNames[i],
        proy: getScopedSummaryValue("control-mensual-total-ingresos", m, "proyectado"),
        real: getScopedSummaryValue("control-mensual-total-ingresos", m, "realizado"),
      }));
      const barsRoot = document.getElementById("cp-monthly-bars");
      if (barsRoot && window.Plotly) {
        Plotly.react(
          barsRoot,
          [
            { type: "bar", name: "Presupuesto", x: monthly.map((x) => x.label), y: monthly.map((x) => x.proy), marker: { color: "#3b82f6" } },
            { type: "bar", name: "Real", x: monthly.map((x) => x.label), y: monthly.map((x) => x.real), marker: { color: "#f97316" } },
          ],
          {
            margin: { l: 44, r: 12, t: 8, b: 30 },
            barmode: "group",
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            legend: { orientation: "h", y: 1.12 },
            yaxis: { tickformat: ",", gridcolor: "rgba(148,163,184,.35)" },
            xaxis: { tickfont: { size: 11 } },
          },
          { displayModeBar: false, responsive: true }
        );
      }

      const trend = [];
      let proyAccum = 0;
      let realAccum = 0;
      months.forEach((m, i) => {
        proyAccum += getScopedSummaryValue("control-mensual-total-ingresos", m, "proyectado");
        realAccum += getScopedSummaryValue("control-mensual-total-ingresos", m, "realizado");
        trend.push({ label: monthNames[i], p: proyAccum, r: realAccum });
      });
      const trendRoot = document.getElementById("cp-tendencia-chart");
      if (trendRoot && window.Plotly) {
        Plotly.react(
          trendRoot,
          [
            { type: "scatter", mode: "lines+markers", name: "Presupuesto Acumulado", x: trend.map((x) => x.label), y: trend.map((x) => x.p), line: { color: "#2563eb", width: 3 } },
            { type: "scatter", mode: "lines+markers", name: "Real Acumulado", x: trend.map((x) => x.label), y: trend.map((x) => x.r), line: { color: "#f97316", width: 3 } },
          ],
          {
            margin: { l: 46, r: 12, t: 8, b: 30 },
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            legend: { orientation: "h", y: 1.12 },
            yaxis: { tickformat: ",", gridcolor: "rgba(148,163,184,.35)" },
            xaxis: { tickfont: { size: 11 } },
          },
          { displayModeBar: false, responsive: true }
        );
      }

      const semaforo = (p, v) => {
        if (!p) return { cls: "semaforo-normal", dot: "#22c55e", pct: 0 };
        const pct = ((v - p) / p) * 100;
        const abs = Math.abs(pct);
        if (abs <= 5) return { cls: "semaforo-normal", dot: "#22c55e", pct };
        if (abs <= 10) return { cls: "semaforo-atencion", dot: "#f59e0b", pct };
        return { cls: "semaforo-riesgo", dot: "#ef4444", pct };
      };
      const desvBody = document.getElementById("cp-desv-body");
      if (desvBody) {
        const rows = detailRows.map((row) => {
          const rubro = (row.querySelector("td:first-child")?.textContent || "").trim();
          const p = getRowYearValue(row, "proyectado");
          const v = getRowYearValue(row, "realizado");
          const d = v - p;
          const s = semaforo(p, v);
          return { rubro, p, v, d, s };
        }).sort((a, b) => Math.abs(b.s.pct) - Math.abs(a.s.pct)).slice(0, 6);
        desvBody.innerHTML = rows.map((x) => `<tr>
          <td>${x.rubro}</td><td>${formatCurrency(x.p)}</td><td>${formatCurrency(x.v)}</td>
          <td>${x.d >= 0 ? "+" : ""}${formatCurrency(x.d)}</td>
          <td>${formatPercentOneDecimal(x.s.pct)}</td><td><span class="cp-dot" style="background:${x.s.dot};"></span></td>
        </tr>`).join("");
      }

      const catName = (rubro) => {
        const text = String(rubro || "").toLowerCase();
        if (text.includes("salarios") || text.includes("aguinaldo") || text.includes("prestaciones") || text.includes("honorarios") || text.includes("gratificaciones")) return "Personal";
        if (text.includes("tecnologia")) return "Tecnología";
        if (text.includes("promocion") || text.includes("publicidad")) return "Marketing";
        if (text.includes("administracion")) return "Administración";
        if (text.includes("intereses") || text.includes("impuestos") || text.includes("derechos") || text.includes("depreciaciones") || text.includes("amortizaciones")) return "Operación";
        return "Otros";
      };
      const palette = {"Personal":"#2563eb","Administración":"#38a169","Operación":"#f97316","Tecnología":"#f59e0b","Marketing":"#a855f7","Otros":"#ef4444"};
      const cats = new Map([["Personal",0],["Administración",0],["Operación",0],["Tecnología",0],["Marketing",0],["Otros",0]]);
      detailRows.forEach((row) => {
        const tipo = (row.getAttribute("data-tipo") || "").toLowerCase();
        if (tipo !== "egreso") return;
        const rubro = (row.querySelector("td:first-child")?.textContent || "").trim();
        const amount = getRowYearValue(row, "realizado");
        const c = catName(rubro);
        cats.set(c, (cats.get(c) || 0) + amount);
      });
      const items = Array.from(cats.entries()).map(([name, value]) => ({ name, value, color: palette[name] || "#64748b" }));
      const total = items.reduce((acc, it) => acc + it.value, 0);
      let start = 0;
      const gradient = items.map((it) => {
        const pct = total ? (it.value / total) * 100 : 0;
        const end = start + pct;
        const seg = `${it.color} ${start.toFixed(2)}% ${end.toFixed(2)}%`;
        start = end;
        return seg;
      }).join(", ");
      const donut = document.getElementById("cp-donut-chart");
      if (donut && window.Plotly) {
        Plotly.react(
          donut,
          [
            {
              type: "pie",
              labels: items.map((x) => x.name),
              values: items.map((x) => x.value),
              hole: 0.55,
              textinfo: "percent",
              marker: { colors: items.map((x) => x.color), line: { color: "#ffffff", width: 2 } },
            },
          ],
          {
            margin: { l: 4, r: 4, t: 4, b: 4 },
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            showlegend: false,
          },
          { displayModeBar: false, responsive: true }
        );
      } else if (donut) {
        donut.classList.add("use-css-donut");
        donut.style.background = total ? `conic-gradient(${gradient})` : "#e2e8f0";
      }
      const dist = document.getElementById("cp-dist-list");
      if (dist) {
        dist.innerHTML = items.map((it) => `<div class="cp-dist-item"><span class="cp-dot" style="background:${it.color}"></span><span>${it.name}</span><strong>${total ? formatPercentOneDecimal((it.value/total)*100) : "0.0%"}</strong></div>`).join("");
      }

      const heatRoot = document.getElementById("cp-heatmap-chart");
      if (heatRoot && window.Plotly) {
        const rows = [
          { label: "Ingresos", cls: "control-mensual-total-ingresos" },
          { label: "Egresos", cls: "control-mensual-total-egresos" },
          { label: "Resultado", cls: "control-mensual-resultado" },
        ];
        const z = rows.map((row) => months.map((m) => {
          const p = getSummaryValue(row.cls, m, "proyectado");
          const v = getSummaryValue(row.cls, m, "realizado");
          return p ? Math.abs(((v - p) / p) * 100) : 0;
        }));
        const text = rows.map((row) => months.map((m) => formatCurrency(getSummaryValue(row.cls, m, "realizado"))));
        Plotly.react(
          heatRoot,
          [
            {
              type: "heatmap",
              x: monthNames,
              y: rows.map((r) => r.label),
              z,
              text,
              hovertemplate: "%{y} %{x}<br>Real: %{text}<br>Desv: %{z:.1f}%<extra></extra>",
              colorscale: [
                [0, "#86efac"],
                [0.25, "#d9f99d"],
                [0.5, "#fde68a"],
                [0.75, "#fdba74"],
                [1, "#fca5a5"],
              ],
              zmin: 0,
              zmax: Math.max(15, ...z.flat()),
            },
          ],
          {
            margin: { l: 86, r: 12, t: 8, b: 34 },
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            xaxis: { tickfont: { size: 11 } },
            yaxis: { tickfont: { size: 12 } },
          },
          { displayModeBar: false, responsive: true }
        );
      }
    };
    const updateReporteEjecutivo = () => {
      const getSummaryValue = (rowClass, month, kind) => {
        const row = controlMensualTable?.querySelector(`tbody tr.${rowClass}`);
        if (!row) return 0;
        const input = row.querySelector(`input[data-summary-month="${month}"][data-summary-kind="${kind}"]`);
        return parseIntegerValue(input?.value || "0");
      };
      const updateConceptRow = (concept, projected, realized) => {
        const row = document.querySelector(`#reporte-ejecucion-table tr[data-concept="${concept}"]`);
        if (!row) return;
        const variacion = realized - projected;
        const cumplimiento = projected > 0 ? (realized / projected) * 100 : 0;
        const cell = (field) => row.querySelector(`[data-field="${field}"]`);
        if (cell("presupuestado")) cell("presupuestado").textContent = formatIntegerValue(projected);
        if (cell("real")) cell("real").textContent = formatIntegerValue(realized);
        if (cell("variacion")) cell("variacion").textContent = formatIntegerValue(variacion);
        if (cell("cumplimiento")) cell("cumplimiento").textContent = formatPercentOneDecimal(cumplimiento);
      };

      const ingresoProjected = getScopedYearValue("control-mensual-total-ingresos", "proyectado");
      const ingresoRealized = getScopedYearValue("control-mensual-total-ingresos", "realizado");
      const egresoProjected = getScopedYearValue("control-mensual-total-egresos", "proyectado");
      const egresoRealized = getScopedYearValue("control-mensual-total-egresos", "realizado");
      const resultadoProjected = getScopedYearValue("control-mensual-resultado", "proyectado");
      const resultadoRealized = getScopedYearValue("control-mensual-resultado", "realizado");

      updateConceptRow("ingresos", ingresoProjected, ingresoRealized);
      updateConceptRow("egresos", egresoProjected, egresoRealized);
      updateConceptRow("resultado", resultadoProjected, resultadoRealized);

      const kpiIngresos = ingresoProjected > 0 ? (ingresoRealized / ingresoProjected) * 100 : 0;
      const kpiEgresos = egresoProjected > 0 ? (egresoRealized / egresoProjected) * 100 : 0;
      const kpiResultadoVs = resultadoProjected !== 0 ? (resultadoRealized / resultadoProjected) * 100 : 0;
      const k1 = document.getElementById("kpi-ejecucion-ingresos");
      const k2 = document.getElementById("kpi-ejecucion-egresos");
      const k3 = document.getElementById("kpi-resultado-vs");
      if (k1) k1.textContent = formatPercentOneDecimal(kpiIngresos);
      if (k2) k2.textContent = formatPercentOneDecimal(kpiEgresos);
      if (k3) k3.textContent = formatPercentOneDecimal(kpiResultadoVs);

      const barsRoot = document.getElementById("reporte-ejecucion-bars");
      if (!barsRoot) return;
      const monthNames = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"];
      const monthly = months.map((m, index) => ({
        label: monthNames[index],
        proy: getScopedSummaryValue("control-mensual-resultado", m, "proyectado"),
        real: getScopedSummaryValue("control-mensual-resultado", m, "realizado"),
      }));
      const maxVal = Math.max(1, ...monthly.flatMap((x) => [Math.abs(x.proy), Math.abs(x.real)]));
      barsRoot.innerHTML = monthly.map((item) => {
        const hProy = Math.max(3, Math.round((Math.abs(item.proy) / maxVal) * 140));
        const hReal = Math.max(3, Math.round((Math.abs(item.real) / maxVal) * 140));
        return `<div class="reporte-month">
          <div class="reporte-month-bars">
            <div class="reporte-bar proy" style="height:${hProy}px" title="${item.label} Presupuesto: ${formatIntegerValue(item.proy)}"></div>
            <div class="reporte-bar real" style="height:${hReal}px" title="${item.label} Real: ${formatIntegerValue(item.real)}"></div>
          </div>
          <div class="reporte-month-label">${item.label}</div>
        </div>`;
      }).join("");
    };
    const getSemaforo = (pctAbs) => {
      if (pctAbs <= 5) return { label: "Normal", cls: "semaforo-normal" };
      if (pctAbs <= 10) return { label: "Atención", cls: "semaforo-atencion" };
      return { label: "Riesgo", cls: "semaforo-riesgo" };
    };
    const updateReporteDesviaciones = () => {
      if (!controlMensualTable) return;
      const detailRows = getScopedDetailRows();
      const tableBody = document.querySelector("#reporte-desviaciones-table tbody");
      const barsRoot = document.getElementById("reporte-desviaciones-bars");
      if (!tableBody || !barsRoot) return;

      const rubros = detailRows.map((row) => {
        const rubro = (row.querySelector("td:first-child")?.textContent || "").trim();
        const projected = getRowYearValue(row, "proyectado");
        const realized = getRowYearValue(row, "realizado");
        const diff = realized - projected;
        const pct = projected !== 0 ? (diff / projected) * 100 : 0;
        return { rubro, projected, realized, diff, pct, absPct: Math.abs(pct) };
      }).filter((item) => item.rubro);

      tableBody.innerHTML = rubros.map((item) => {
        const semaforo = getSemaforo(item.absPct);
        return `<tr>
          <td>${item.rubro}</td>
          <td class="tabla-oficial-num">${formatIntegerValue(item.projected)}</td>
          <td class="tabla-oficial-num">${formatIntegerValue(item.realized)}</td>
          <td class="tabla-oficial-num">${formatIntegerValue(item.diff)}</td>
          <td class="tabla-oficial-num month-percent-col">${formatPercentOneDecimal(item.pct)}</td>
          <td><span class="semaforo-badge ${semaforo.cls}">${semaforo.label}</span></td>
        </tr>`;
      }).join("");

      const ranked = [...rubros].sort((a, b) => b.absPct - a.absPct).slice(0, 12);
      const maxAbs = Math.max(1, ...ranked.map((x) => x.absPct));
      barsRoot.innerHTML = ranked.map((item) => {
        const width = Math.max(4, Math.round((item.absPct / maxAbs) * 100));
        return `<div class="reporte-variacion-row">
          <div class="reporte-variacion-label" title="${item.rubro}">${item.rubro}</div>
          <div class="reporte-variacion-track"><div class="reporte-variacion-bar" style="width:${width}%;"></div></div>
          <div class="reporte-variacion-value">${formatPercentOneDecimal(item.pct)}</div>
        </div>`;
      }).join("");
    };
    const updateReporteTendencia = () => {
      if (!controlMensualTable) return;
      const monthNames = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"];
      const trend = [];
      let proyAccum = 0;
      let realAccum = 0;
      months.forEach((month, idx) => {
        proyAccum += getScopedSummaryValue("control-mensual-resultado", month, "proyectado");
        const realMonth = getScopedSummaryValue("control-mensual-resultado", month, "realizado");
        realAccum += realMonth;
        trend.push({ label: monthNames[idx], proy: proyAccum, real: realAccum });
      });

      const tbody = document.querySelector("#reporte-tendencia-table tbody");
      if (tbody) {
        tbody.innerHTML = trend.map((item) => (
          `<tr>
            <td>${item.label}</td>
            <td class="tabla-oficial-num">${formatIntegerValue(item.proy)}</td>
            <td class="tabla-oficial-num">${formatIntegerValue(item.real)}</td>
          </tr>`
        )).join("");
      }

      const svg = document.getElementById("reporte-tendencia-svg");
      if (!svg) return;
      const w = 1000;
      const h = 260;
      const padL = 44;
      const padR = 18;
      const padT = 12;
      const padB = 30;
      const chartW = w - padL - padR;
      const chartH = h - padT - padB;
      const maxVal = Math.max(1, ...trend.map((x) => Math.max(Math.abs(x.proy), Math.abs(x.real))));
      const xFor = (i) => padL + ((chartW / 11) * i);
      const yFor = (v) => padT + (chartH - (Math.abs(v) / maxVal) * chartH);
      const pathFor = (key) => trend.map((item, i) => `${i === 0 ? "M" : "L"} ${xFor(i)} ${yFor(item[key])}`).join(" ");
      const points = trend.map((item, i) => ({ x: xFor(i), yp: yFor(item.proy), yr: yFor(item.real), label: item.label }));

      svg.innerHTML = `
        <line x1="${padL}" y1="${h - padB}" x2="${w - padR}" y2="${h - padB}" class="line-axis"></line>
        <line x1="${padL}" y1="${padT}" x2="${padL}" y2="${h - padB}" class="line-axis"></line>
        <path d="${pathFor("proy")}" class="line-proy"></path>
        <path d="${pathFor("real")}" class="line-real"></path>
        ${points.map((p) => `<circle cx="${p.x}" cy="${p.yp}" r="3" class="line-point-proy"></circle>`).join("")}
        ${points.map((p) => `<circle cx="${p.x}" cy="${p.yr}" r="3" class="line-point-real"></circle>`).join("")}
        ${points.map((p) => `<text x="${p.x}" y="${h - 10}" text-anchor="middle" font-size="11" fill="rgba(15,23,42,.8)">${p.label}</text>`).join("")}
      `;
    };
    const resolveAreaSucursal = (rubro) => {
      return inferDepartmentFromRubro(rubro);
    };
    const updateReporteEjecucionArea = () => {
      if (!controlMensualTable) return;
      const detailRows = getScopedDetailRows();
      const grouped = new Map();
      detailRows.forEach((row) => {
        const rubro = (row.querySelector("td:first-child")?.textContent || "").trim();
        const area = resolveAreaSucursal(rubro);
        const projected = getRowYearValue(row, "proyectado");
        const realized = getRowYearValue(row, "realizado");
        const current = grouped.get(area) || { area, projected: 0, realized: 0 };
        current.projected += projected;
        current.realized += realized;
        grouped.set(area, current);
      });
      const rows = Array.from(grouped.values()).sort((a, b) => a.area.localeCompare(b.area, "es"));
      const tbody = document.querySelector("#reporte-area-table tbody");
      if (tbody) {
        tbody.innerHTML = rows.map((item) => {
          const ejec = item.projected > 0 ? (item.realized / item.projected) * 100 : 0;
          return `<tr>
            <td>${item.area}</td>
            <td class="tabla-oficial-num">${formatIntegerValue(item.projected)}</td>
            <td class="tabla-oficial-num">${formatIntegerValue(item.realized)}</td>
            <td class="tabla-oficial-num month-percent-col">${formatPercentOneDecimal(ejec)}</td>
          </tr>`;
        }).join("");
      }
      const barsRoot = document.getElementById("reporte-area-bars");
      if (!barsRoot) return;
      const maxPct = Math.max(100, ...rows.map((x) => (x.projected > 0 ? (x.realized / x.projected) * 100 : 0)));
      barsRoot.innerHTML = rows.map((item) => {
        const pct = item.projected > 0 ? (item.realized / item.projected) * 100 : 0;
        const width = Math.max(3, Math.min(100, (pct / maxPct) * 100));
        const overCls = pct > 100 ? " over" : "";
        return `<div class="area-bar-row">
          <div class="area-bar-label">${item.area}</div>
          <div class="area-bar-track"><div class="area-bar-fill${overCls}" style="width:${width}%;"></div></div>
          <div class="area-bar-value">${formatPercentOneDecimal(pct)}</div>
        </div>`;
      }).join("");
    };
    const resolveGastoCategoria = (rubro) => {
      const text = String(rubro || "").toLowerCase();
      if (text.includes("salarios") || text.includes("aguinaldo") || text.includes("prestaciones") || text.includes("honorarios") || text.includes("gratificaciones")) return "Personal";
      if (text.includes("tecnologia")) return "Tecnología";
      if (text.includes("promocion") || text.includes("publicidad")) return "Marketing";
      if (text.includes("administracion")) return "Administración";
      if (text.includes("intereses") || text.includes("impuestos") || text.includes("derechos") || text.includes("depreciaciones") || text.includes("amortizaciones") || text.includes("fondo de proteccion")) return "Operación";
      return "Otros";
    };
    const updateReporteComposicionGasto = () => {
      if (!controlMensualTable) return;
      const detailRows = Array.from(controlMensualTable.querySelectorAll("tbody tr.control-mensual-detail-row"));
      const categories = new Map([
        ["Personal", 0],
        ["Operación", 0],
        ["Tecnología", 0],
        ["Marketing", 0],
        ["Administración", 0],
        ["Otros", 0],
      ]);
      detailRows.forEach((row) => {
        const tipo = (row.getAttribute("data-tipo") || "").toLowerCase();
        if (tipo !== "egreso") return;
        const rubro = (row.querySelector("td:first-child")?.textContent || "").trim();
        const amount = getRowYearValue(row, "realizado");
        const cat = resolveGastoCategoria(rubro);
        categories.set(cat, (categories.get(cat) || 0) + amount);
      });
      const palette = {
        "Personal": "#0f766e",
        "Operación": "#0369a1",
        "Tecnología": "#7c3aed",
        "Marketing": "#ea580c",
        "Administración": "#0f172a",
        "Otros": "#64748b",
      };
      const items = Array.from(categories.entries()).map(([name, value]) => ({ name, value, color: palette[name] || "#64748b" }));
      const total = items.reduce((acc, item) => acc + item.value, 0);
      let start = 0;
      const slices = items.map((item) => {
        const pct = total > 0 ? (item.value / total) * 100 : 0;
        const end = start + pct;
        const slice = `${item.color} ${start.toFixed(2)}% ${end.toFixed(2)}%`;
        start = end;
        return slice;
      }).join(", ");
      const donut = document.getElementById("reporte-gasto-donut");
      if (donut) donut.style.background = total > 0 ? `conic-gradient(${slices})` : "#e2e8f0";
      const legend = document.getElementById("reporte-gasto-legend");
      if (!legend) return;
      legend.innerHTML = items.map((item) => {
        const pct = total > 0 ? (item.value / total) * 100 : 0;
        return `<div class="gasto-legend-item">
          <span class="gasto-legend-dot" style="background:${item.color};"></span>
          <span>${item.name}</span>
          <span class="gasto-legend-value">${formatIntegerValue(item.value)} (${formatPercentOneDecimal(pct)})</span>
        </div>`;
      }).join("");
    };
    const updateReporteKpisSipet = () => {
      if (!controlMensualTable) return;
      const getSummaryValue = (rowClass, month, kind) => {
        const row = controlMensualTable.querySelector(`tbody tr.${rowClass}`);
        if (!row) return 0;
        const input = row.querySelector(`input[data-summary-month="${month}"][data-summary-kind="${kind}"]`);
        return parseIntegerValue(input?.value || "0");
      };
      const setKpi = (id, value) => {
        const el = document.getElementById(id);
        if (el) el.textContent = value;
      };
      const ingresosP = getScopedYearValue("control-mensual-total-ingresos", "proyectado");
      const ingresosR = getScopedYearValue("control-mensual-total-ingresos", "realizado");
      const egresosP = getScopedYearValue("control-mensual-total-egresos", "proyectado");
      const egresosR = getScopedYearValue("control-mensual-total-egresos", "realizado");
      const resultadoP = getScopedYearValue("control-mensual-resultado", "proyectado");
      const resultadoR = getScopedYearValue("control-mensual-resultado", "realizado");

      const ejecMAINP = ingresosP + egresosP;
      const ejecMAINR = ingresosR + egresosR;
      const indiceEjec = ejecMAINP > 0 ? (ejecMAINR / ejecMAINP) * 100 : 0;

      const detailRows = getScopedDetailRows();
      const desviaciones = detailRows.map((row) => {
        const p = getRowYearValue(row, "proyectado");
        const r = getRowYearValue(row, "realizado");
        return p !== 0 ? Math.abs(((r - p) / p) * 100) : 0;
      });
      const variacionProm = desviaciones.length ? (desviaciones.reduce((a, b) => a + b, 0) / desviaciones.length) : 0;

      const ratioGastoIngreso = ingresosR > 0 ? (egresosR / ingresosR) * 100 : 0;

      const cumplimientosMensuales = months.map((m) => {
        const p = getScopedSummaryValue("control-mensual-resultado", m, "proyectado");
        const r = getScopedSummaryValue("control-mensual-resultado", m, "realizado");
        return p !== 0 ? (r / p) * 100 : 0;
      });
      const cumplimientoProm = cumplimientosMensuales.length ? (cumplimientosMensuales.reduce((a, b) => a + b, 0) / cumplimientosMensuales.length) : 0;

      const desviacionAnual = resultadoR - resultadoP;
      const disciplina = Math.max(0, 100 - variacionProm);

      setKpi("kpi-sipet-ejecucion", formatPercentOneDecimal(indiceEjec));
      setKpi("kpi-sipet-variacion-prom", formatPercentOneDecimal(variacionProm));
      setKpi("kpi-sipet-ratio-gasto-ingreso", formatPercentOneDecimal(ratioGastoIngreso));
      setKpi("kpi-sipet-cumplimiento-prom", formatPercentOneDecimal(cumplimientoProm));
      setKpi("kpi-sipet-desviacion-anual", formatIntegerValue(desviacionAnual));
      setKpi("kpi-sipet-disciplina", formatPercentOneDecimal(disciplina));
    };
    const heatSemaforo = (projected, realized) => {
      if (projected === 0) return { emoji: "🟢", cls: "semaforo-normal" };
      const pctAbs = Math.abs(((realized - projected) / projected) * 100);
      if (pctAbs <= 5) return { emoji: "🟢", cls: "semaforo-normal" };
      if (pctAbs <= 10) return { emoji: "🟡", cls: "semaforo-atencion" };
      return { emoji: "🔴", cls: "semaforo-riesgo" };
    };
    const updateReporteMapaCalor = () => {
      if (!controlMensualTable) return;
      const monthNames = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
      const getSummaryValue = (rowClass, month, kind) => {
        const row = controlMensualTable.querySelector(`tbody tr.${rowClass}`);
        if (!row) return 0;
        const input = row.querySelector(`input[data-summary-month="${month}"][data-summary-kind="${kind}"]`);
        return parseIntegerValue(input?.value || "0");
      };
      const tbody = document.querySelector("#reporte-mapa-calor-table tbody");
      if (!tbody) return;
      tbody.innerHTML = months.map((m, idx) => {
        const ingP = getScopedSummaryValue("control-mensual-total-ingresos", m, "proyectado");
        const ingR = getScopedSummaryValue("control-mensual-total-ingresos", m, "realizado");
        const egrP = getScopedSummaryValue("control-mensual-total-egresos", m, "proyectado");
        const egrR = getScopedSummaryValue("control-mensual-total-egresos", m, "realizado");
        const resP = getScopedSummaryValue("control-mensual-resultado", m, "proyectado");
        const resR = getScopedSummaryValue("control-mensual-resultado", m, "realizado");
        const sIng = heatSemaforo(ingP, ingR);
        const sEgr = heatSemaforo(egrP, egrR);
        const sRes = heatSemaforo(resP, resR);
        return `<tr>
          <td>${monthNames[idx]}</td>
          <td style="text-align:center;"><span class="heat-chip ${sIng.cls}" title="Ingresos">${sIng.emoji}</span></td>
          <td style="text-align:center;"><span class="heat-chip ${sEgr.cls}" title="Egresos">${sEgr.emoji}</span></td>
          <td style="text-align:center;"><span class="heat-chip ${sRes.cls}" title="Resultado">${sRes.emoji}</span></td>
        </tr>`;
      }).join("");
    };
    const updateAlertasInteligentes = () => {
      if (!controlMensualTable) return;
      const getSummaryValue = (rowClass, month, kind) => {
        const row = controlMensualTable.querySelector(`tbody tr.${rowClass}`);
        if (!row) return 0;
        const input = row.querySelector(`input[data-summary-month="${month}"][data-summary-kind="${kind}"]`);
        return parseIntegerValue(input?.value || "0");
      };
      const monthNames = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
      const alerts = [];

      months.forEach((m, idx) => {
        const egP = getScopedSummaryValue("control-mensual-total-egresos", m, "proyectado");
        const egR = getScopedSummaryValue("control-mensual-total-egresos", m, "realizado");
        if (egP > 0 && egR > egP * 1.1) {
          alerts.push({ level: "danger", text: `Riesgo ${monthNames[idx]}: gasto en ${formatPercentOneDecimal((egR / egP) * 100)} del presupuesto (>110%).` });
        }
      });

      months.forEach((m, idx) => {
        const inP = getScopedSummaryValue("control-mensual-total-ingresos", m, "proyectado");
        const inR = getScopedSummaryValue("control-mensual-total-ingresos", m, "realizado");
        if (inP > 0 && inR < inP * 0.9) {
          alerts.push({ level: "warn", text: `Atención ${monthNames[idx]}: ingreso en ${formatPercentOneDecimal((inR / inP) * 100)} del esperado (<90%).` });
        }
      });

      const resultadoSerie = months.map((m) => getScopedSummaryValue("control-mensual-resultado", m, "realizado"));
      for (let i = 2; i < resultadoSerie.length; i += 1) {
        if (resultadoSerie[i] < resultadoSerie[i - 1] && resultadoSerie[i - 1] < resultadoSerie[i - 2]) {
          alerts.push({ level: "danger", text: `Tendencia negativa detectada: 3 meses consecutivos a la baja hasta ${monthNames[i]}.` });
          break;
        }
      }

      const container = document.getElementById("alertas-inteligentes-list");
      if (!container) return;
      if (!alerts.length) {
        container.innerHTML = `<div class="alerta-item ok">Sin alertas críticas. Ejecución dentro de parámetros.</div>`;
        return;
      }
      container.innerHTML = alerts.map((a) => `<div class="alerta-item ${a.level}">${a.text}</div>`).join("");
    };
    const renderControlMensualAccumulatedTable = () => {
      if (!controlMensualAccTableBody) return;
      const monthNames = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"];
      let ingPA = 0;
      let ingRA = 0;
      let egrPA = 0;
      let egrRA = 0;
      let resPA = 0;
      let resRA = 0;
      controlMensualAccTableBody.innerHTML = months.map((m, idx) => {
        const ingP = getSummaryValue("control-mensual-total-ingresos", m, "proyectado");
        const ingR = getSummaryValue("control-mensual-total-ingresos", m, "realizado");
        const egrP = getSummaryValue("control-mensual-total-egresos", m, "proyectado");
        const egrR = getSummaryValue("control-mensual-total-egresos", m, "realizado");
        const resP = getSummaryValue("control-mensual-resultado", m, "proyectado");
        const resR = getSummaryValue("control-mensual-resultado", m, "realizado");
        ingPA += ingP;
        ingRA += ingR;
        egrPA += egrP;
        egrRA += egrR;
        resPA += resP;
        resRA += resR;
        const pct = resPA !== 0 ? (resRA / resPA) * 100 : 0;
        return `<tr>
          <td>${monthNames[idx]}</td>
          <td class="tabla-oficial-num">${formatIntegerValue(ingPA)}</td>
          <td class="tabla-oficial-num">${formatIntegerValue(ingRA)}</td>
          <td class="tabla-oficial-num">${formatIntegerValue(egrPA)}</td>
          <td class="tabla-oficial-num">${formatIntegerValue(egrRA)}</td>
          <td class="tabla-oficial-num">${formatIntegerValue(resPA)}</td>
          <td class="tabla-oficial-num">${formatIntegerValue(resRA)}</td>
          <td class="tabla-oficial-num month-percent-col">${formatPercentOneDecimal(pct)}</td>
        </tr>`;
      }).join("");
    };
    const openControlMensualAccumulatedModal = () => {
      if (!controlMensualAccModal) return;
      renderControlMensualAccumulatedTable();
      controlMensualAccModal.classList.add("is-open");
      controlMensualAccModal.setAttribute("aria-hidden", "false");
    };
    const closeControlMensualAccumulatedModal = () => {
      if (!controlMensualAccModal) return;
      controlMensualAccModal.classList.remove("is-open");
      controlMensualAccModal.setAttribute("aria-hidden", "true");
    };
    const syncControlMensualRubrosFromAnual = () => {
      if (!controlMensualTable || !presupuestoTable) return;
      const anualRows = Array.from(presupuestoTable.querySelectorAll("tbody tr"));
      const controlBody = controlMensualTable.querySelector("tbody");
      if (!controlBody) return;
      const rubros = anualRows.map((row) => {
        const tipoCell = row.querySelector("td.tipo-col");
        const rubroCell = row.querySelector("td.rubro-col");
        const mensualCell = row.querySelector(".presupuesto-mensual");
        return {
          tipo: (tipoCell?.textContent || "").trim(),
          rubro: (rubroCell?.textContent || "").trim(),
          mensualMAIN: normalizeInteger((mensualCell?.textContent || "").trim()) || "0",
        };
      }).filter((item) => item.rubro);
      const detailRowsHtml = rubros.map((item, index) => (
        `<tr class="control-mensual-detail-row" data-tipo="${item.tipo}"><td>${item.rubro}</td>${buildControlMonthlyCells(index + 1, item.mensualMAIN)}</tr>`
      )).join("");
      const summaryRowsHtml = [
        `<tr class="control-mensual-total-ingresos"><td><strong>Total de ingresos</strong></td>${buildControlSummaryCells()}</tr>`,
        `<tr class="control-mensual-total-egresos"><td><strong>Total de egresos</strong></td>${buildControlSummaryCells()}</tr>`,
        `<tr class="control-mensual-resultado"><td><strong>Resultado</strong></td>${buildControlSummaryCells()}</tr>`,
      ].join("");
      controlBody.innerHTML = `${detailRowsHtml}${summaryRowsHtml}`;
      bindControlMensualFormula();
      recalcControlMensualTotals();
      refreshReportesByScope();
    };
    syncControlMensualRubrosFromAnual();

    const collectControlMensualRows = () => {
      if (!controlMensualTable) return [];
      const rows = Array.from(controlMensualTable.querySelectorAll("tbody tr.control-mensual-detail-row"));
      return rows.map((row) => {
        const rubro = (row.querySelector("td:first-child")?.textContent || "").trim();
        const monthValues = {};
        months.forEach((month) => {
          const projectedInput = row.querySelector(`input[name*="_${month}_proyectado"]`);
          const realizedInput = row.querySelector(`input[name*="_${month}_realizado"]`);
          monthValues[month] = {
            proyectado: parseIntegerValue(projectedInput?.value || "0"),
            realizado: parseIntegerValue(realizedInput?.value || "0"),
          };
        });
        return { rubro, months: monthValues };
      }).filter((item) => item.rubro);
    };

    const applySavedControlMensualRows = (savedRows) => {
      if (!controlMensualTable || !Array.isArray(savedRows)) return;
      const rowMap = getControlRowByRubroKey();
      savedRows.forEach((item) => {
        const rubroKey = normalizeRubroKey(item?.rubro || "");
        const row = rowMap.get(rubroKey);
        if (!row) return;
        months.forEach((month) => {
          const monthData = item?.months?.[month] || item?.months?.[Number(month)] || {};
          const projectedInput = row.querySelector(`input[name*="_${month}_proyectado"]`);
          const realizedInput = row.querySelector(`input[name*="_${month}_realizado"]`);
          if (projectedInput && monthData.proyectado !== undefined && monthData.proyectado !== null) {
            projectedInput.value = formatIntegerValue(parseIntegerValue(monthData.proyectado));
          }
          if (realizedInput && monthData.realizado !== undefined && monthData.realizado !== null) {
            realizedInput.value = formatIntegerValue(parseIntegerValue(monthData.realizado));
          }
        });
      });
      Array.from(controlMensualTable.querySelectorAll("tbody tr.control-mensual-detail-row")).forEach((row) => recalcControlMensualRow(row));
      recalcControlMensualTotals();
    };

    const loadControlMensual = async () => {
      try {
        const response = await fetch("/proyectando/control-mensual-datos", { method: "GET" });
        if (!response.ok) return;
        const payload = await response.json().catch(() => ({}));
        if (payload?.success && Array.isArray(payload?.rows) && payload.rows.length > 0) {
          applySavedControlMensualRows(payload.rows);
          setSaveStatus(`Datos cargados: ${payload.rows.length} rubros.`);
        }
      } catch (error) {
        setSaveStatus("No se pudieron cargar datos guardados.", true);
      }
    };

    const saveControlMensual = async () => {
      if (!controlMensualTable) return;
      const rows = collectControlMensualRows();
      setSaveStatus("Guardando datos...");
      const response = await fetch("/proyectando/guardar-control-mensual", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rows }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload?.success === false) {
        throw new Error(payload?.error || "No se pudo guardar la información.");
      }
      setSaveStatus(`Datos guardados correctamente (${rows.length} rubros).`);
    };

    const getControlRowByRubroKey = () => {
      const map = new Map();
      if (!controlMensualTable) return map;
      const rows = Array.from(controlMensualTable.querySelectorAll("tbody tr.control-mensual-detail-row"));
      rows.forEach((row) => {
        const rubro = (row.querySelector("td:first-child")?.textContent || "").trim();
        const key = normalizeRubroKey(rubro);
        if (!key || map.has(key)) return;
        map.set(key, row);
      });
      return map;
    };
    loadControlMensual();
    loadAnnualCycleContext();
    const initializeReportFilters = async () => {
      if (!reportesFiltroNivelEl || !reportesFiltroElementoEl) return;
      const level = String(reportesFiltroNivelEl.value || "consolidado");
      await loadReportFilterElements(level);
      setScopeFromSelectedElement();
    };

    const applyControlMensualImport = (entries) => {
      if (!controlMensualTable) return { applied: 0, missing: 0, overwritten: 0 };
      const rowMap = getControlRowByRubroKey();
      const updates = [];
      let missing = 0;
      let overwritten = 0;
      (Array.isArray(entries) ? entries : []).forEach((entry) => {
        const row = rowMap.get(String(entry?.rubro_key || "").trim()) || rowMap.get(normalizeRubroKey(entry?.rubro || ""));
        if (!row) {
          missing += 1;
          return;
        }
        const mes = String(entry?.mes || "").trim().padStart(2, "0");
        if (!months.includes(mes)) return;
        [["proyectado", entry?.proyectado], ["realizado", entry?.realizado]].forEach(([kind, raw]) => {
          if (raw === null || raw === undefined || raw === "") return;
          const input = row.querySelector(`input[name*="_${mes}_${kind}"]`);
          if (!input) return;
          const oldValue = parseIntegerValue(input.value || "0");
          const newValue = parseIntegerValue(raw);
          if (oldValue !== 0 && newValue !== 0 && oldValue !== newValue) {
            overwritten += 1;
          }
          updates.push({ input, value: formatIntegerValue(newValue) });
        });
      });

      if (overwritten > 0) {
        const proceed = window.confirm(`Se detectaron ${overwritten} celdas con información previa. ¿Deseas sobrescribirlas?`);
        if (!proceed) return { applied: 0, missing, overwritten };
      }

      updates.forEach((item) => {
        item.input.value = item.value;
      });
      Array.from(controlMensualTable.querySelectorAll("tbody tr.control-mensual-detail-row")).forEach((row) => recalcControlMensualRow(row));
      recalcControlMensualTotals();
      return { applied: updates.length, missing, overwritten };
    };

    const importControlMensualFile = async (file) => {
      if (!file) return;
      setImportStatus("Importando datos...");
      const formData = new FormData();
      formData.append("file", file);
      const response = await fetch("/proyectando/importar-control-mensual", {
        method: "POST",
        body: formData,
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload?.success === false) {
        const details = Array.isArray(payload?.details) ? payload.details.slice(0, 3).join(" | ") : "";
        throw new Error(`${payload?.error || "No se pudo importar el archivo."}${details ? ` ${details}` : ""}`);
      }
      const result = applyControlMensualImport(payload.entries || []);
      const dup = Number(payload?.summary?.duplicates_in_file || 0);
      const initialDataRows = Number(payload?.summary?.initial_data_rows || 0);
      const importFormat = String(payload?.summary?.format || "");
      setImportStatus(
        `Importación completada. Formato: ${importFormat || "n/d"}. Celdas aplicadas: ${result.applied}. Rubros no encontrados: ${result.missing}. Sobrescritas: ${result.overwritten}. Duplicados en archivo: ${dup}. Mes 0 con datos: ${initialDataRows} (informativo, no se importa).`,
        false
      );
      const shouldSave = window.confirm("Importación aplicada correctamente. ¿Quieres guardar los datos?");
      if (shouldSave) {
        await saveControlMensual();
      }
    };

    if (importBtn && importFileInput) {
      importBtn.addEventListener("click", () => {
        importFileInput.click();
      });
      importFileInput.addEventListener("change", async () => {
        const file = importFileInput.files && importFileInput.files[0];
        if (!file) return;
        try {
          await importControlMensualFile(file);
        } catch (error) {
          setImportStatus(error.message || "No se pudo importar el archivo.", true);
        } finally {
          importFileInput.value = "";
        }
      });
    }

    if (saveBtn) {
      saveBtn.addEventListener("click", async () => {
        try {
          await savePresupuestoAnual();
          await saveControlMensual();
        } catch (error) {
          setSaveStatus(error.message || "No se pudo guardar la información.", true);
        }
      });
    }
    if (annualCycleStartBtn) {
      annualCycleStartBtn.addEventListener("click", async () => {
        try {
          await startAnnualCycle();
        } catch (error) {
          setAnnualCycleStatus(error.message || "No se pudo iniciar el nuevo ejercicio.", true);
        }
      });
    }
    if (reportesFiltroNivelEl) {
      reportesFiltroNivelEl.addEventListener("change", async () => {
        const level = String(reportesFiltroNivelEl.value || "consolidado");
        await loadReportFilterElements(level);
        setScopeFromSelectedElement();
      });
    }
    if (reportesFiltroAplicarBtn) {
      reportesFiltroAplicarBtn.addEventListener("click", () => {
        setScopeFromSelectedElement();
      });
    }
    if (reportesFiltroElementoEl) {
      reportesFiltroElementoEl.addEventListener("change", () => {
        setScopeFromSelectedElement();
      });
    }
    if (controlMensualAccBtn) {
      controlMensualAccBtn.addEventListener("click", openControlMensualAccumulatedModal);
    }
    if (controlMensualAccClose) {
      controlMensualAccClose.addEventListener("click", closeControlMensualAccumulatedModal);
    }
    if (controlMensualAccModal) {
      controlMensualAccModal.addEventListener("click", (event) => {
        if (event.target === controlMensualAccModal) {
          closeControlMensualAccumulatedModal();
        }
      });
    }

    const syncReportesFullscreenButton = () => {
      if (!reportesFullscreenBtn || !reportesPanel) return;
      const inFullscreen = document.fullscreenElement === reportesPanel;
      reportesFullscreenBtn.textContent = inFullscreen ? "Salir de pantalla completa" : "Ver en pantalla completa";
    };

    if (reportesFullscreenBtn && reportesPanel) {
      reportesFullscreenBtn.addEventListener("click", async () => {
        try {
          if (document.fullscreenElement === reportesPanel) {
            await document.exitFullscreen();
          } else {
            await reportesPanel.requestFullscreen();
          }
        } catch (error) {
          setImportStatus("No fue posible abrir pantalla completa en este navegador.", true);
        } finally {
          syncReportesFullscreenButton();
        }
      });
      document.addEventListener("fullscreenchange", syncReportesFullscreenButton);
      syncReportesFullscreenButton();
    }
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && controlMensualAccModal?.classList.contains("is-open")) {
        closeControlMensualAccumulatedModal();
      }
    });

    document.querySelectorAll("[data-report-target]").forEach((card) => {
      card.addEventListener("click", () => {
        const id = card.getAttribute("data-report-target");
        if (!id) return;
        document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });

    const monthToggleButtons = Array.from(document.querySelectorAll("[data-month-toggle]"));
    initializeReportFilters();
    const setMonthVisibility = (month, visible) => {
      document.querySelectorAll(`.month-col.month-${month}`).forEach((cell) => {
        cell.style.display = visible ? "table-cell" : "none";
      });
      const monthHead = document.querySelector(`.month-group-head.month-${month}`);
      const button = document.querySelector(`[data-month-toggle="${month}"]`);
      if (monthHead) monthHead.classList.toggle("is-collapsed", !visible);
      if (button) button.textContent = visible ? "▾" : "▸";
    };
    monthToggleButtons.forEach((button) => {
      const month = button.getAttribute("data-month-toggle");
      if (!month) return;
      let isVisible = true;
      button.addEventListener("click", () => {
        isVisible = !isVisible;
        setMonthVisibility(month, isVisible);
      });
    });

    };

    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", initPresupuestoPage, { once: true });
    } else {
      initPresupuestoPage();
    }
  })();
