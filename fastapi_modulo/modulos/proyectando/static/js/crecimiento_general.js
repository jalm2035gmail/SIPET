(function () {
  var tbodyActivo = document.getElementById("cg-activo-total-tbody");
  var tbodyPasivo = document.getElementById("cg-pasivo-total-tbody");
  var tbodyPatrimonio = document.getElementById("cg-patrimonio-tbody");
  var pasivoCapitalColgroup = document.getElementById("cg-pc-colgroup");
  var pasivoCapitalThead = document.getElementById("cg-pc-thead");
  var pasivoCapitalTbody = document.getElementById("cg-pc-tbody");
  var capitalDetalleColgroup = document.getElementById("cg-capital-colgroup");
  var capitalDetalleThead = document.getElementById("cg-capital-thead");
  var capitalDetalleTbody = document.getElementById("cg-capital-tbody");
  var crecimientoDetalleColgroup = document.getElementById("cg-crecimiento-colgroup");
  var crecimientoDetalleThead = document.getElementById("cg-crecimiento-thead");
  var crecimientoDetalleTbody = document.getElementById("cg-crecimiento-tbody");
  var financiamientoActivoColgroup = document.getElementById("cg-financiamiento-activo-colgroup");
  var financiamientoActivoThead = document.getElementById("cg-financiamiento-activo-thead");
  var financiamientoActivoTbody = document.getElementById("cg-financiamiento-activo-tbody");
  var activoSaveBtn = document.getElementById("cg-activo-save-btn");
  var activoMsg = document.getElementById("cg-activo-msg");
  var pasivoSaveBtn = document.getElementById("cg-pasivo-save-btn");
  var pasivoMsg = document.getElementById("cg-pasivo-msg");
  var patrimonioSaveBtn = document.getElementById("cg-patrimonio-save-btn");
  var patrimonioMsg = document.getElementById("cg-patrimonio-msg");
  var finToggleBtn = document.getElementById("cg-fin-toggle");
  var finPanel = document.getElementById("cg-fin-panel");
  var finPanelBadge = document.getElementById("cg-fin-panel-badge");
  var finPanelSubtitle = document.getElementById("cg-fin-panel-subtitle");
  var finSvg = document.getElementById("cg-fin-svg");
  var finTableHead = document.getElementById("cg-fin-table-head");
  var finTableBody = document.getElementById("cg-fin-table-body");
  var chartToggleBtn = document.getElementById("cg-chart-toggle");
  var chartPanel = document.getElementById("cg-chart-panel");
  var chartSvg = document.getElementById("cg-chart-svg");
  var activoRowsState = [];
  var activoGrowthMap = {};
  var activoChartInstance = null;
  var finChartInstance = null;
  var financiamientoStandardsState = { Pasivo: "80", Capital: "18", Resultado: "2" };
  var financiamientoPasivoPctState = {};
  var financiamientoResultadoPctState = {};
  var financiamientoInsightState = { periods: [], pctRows: {}, gapRows: {} };
  var financiamientoInsightView = "pct";

  function esc(v) {
    return String(v == null ? "" : v)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function num(v) {
    if (v == null || v === "") return "";
    return String(v);
  }

  function parseNumber(value) {
    var cleaned = String(value == null ? "" : value).replace(/,/g, "").replace(/%/g, "").trim();
    if (!cleaned) return NaN;
    var numeric = Number(cleaned);
    return Number.isFinite(numeric) ? numeric : NaN;
  }

  function formatAmount(value) {
    if (!Number.isFinite(value)) return "";
    return Math.round(value).toLocaleString("en-US");
  }

  function formatPercent(value) {
    if (!Number.isFinite(value)) return "";
    return (Math.round(value * 100) / 100).toString().replace(/\.0+$/, "").replace(/(\.\d*[1-9])0+$/, "$1") + "%";
  }

  function formatPercentInput(value) {
    if (!Number.isFinite(value)) return "00.00%";
    return value.toFixed(2) + "%";
  }

  function buildChartPath(points) {
    if (!points.length) return "";
    return points.map(function (point, idx) {
      return (idx === 0 ? "M" : "L") + point.x + " " + point.y;
    }).join(" ");
  }

  function destroyChart(instance) {
    if (instance && typeof instance.destroy === "function") instance.destroy();
    return null;
  }

  function renderMiniInsightChart(series, title) {
    if (!finSvg || !window.Chart) return;
    var rows = Array.isArray(series) ? series.filter(function (item) {
      return item && Array.isArray(item.values) && item.values.some(function (v) { return Number.isFinite(v); });
    }) : [];
    if (!rows.length) {
      finChartInstance = destroyChart(finChartInstance);
      return;
    }
    finChartInstance = destroyChart(finChartInstance);
    var labels = rows[0].labels || [];
    var palette = ["#0f172a", "#0f766e", "#2563eb", "#b45309"];
    var chartType = financiamientoInsightView === "gap" ? "bar" : "line";
    finChartInstance = new window.Chart(finSvg.getContext("2d"), {
      type: chartType,
      data: {
        labels: labels,
        datasets: rows.map(function (row, rowIdx) {
          var color = palette[rowIdx % palette.length];
          return {
            label: row.label,
            data: row.values,
            borderColor: color,
            backgroundColor: chartType === "bar" ? color + "cc" : color + "22",
            pointBackgroundColor: "#fff",
            pointBorderColor: color,
            pointBorderWidth: 2,
            pointRadius: chartType === "bar" ? 0 : 4,
            pointHoverRadius: chartType === "bar" ? 0 : 5,
            borderWidth: 3,
            fill: chartType !== "bar",
            tension: 0.35
          };
        })
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        aspectRatio: 2.6,
        animation: {
          duration: financiamientoInsightView === "gap" ? 1800 : 2200,
          easing: "easeOutQuart"
        },
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: { position: "bottom", labels: { usePointStyle: true, boxWidth: 10 } },
          title: { display: false },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                return ctx.dataset.label + ": " + formatPercent(ctx.parsed.y);
              }
            }
          }
        },
        scales: {
          x: { grid: { display: false } },
          y: {
            ticks: {
              callback: function (value) { return formatPercent(Number(value)); }
            }
          }
        }
      }
    });
  }

  function renderFinanciamientoInsight() {
    var periods = Array.isArray(financiamientoInsightState.periods) ? financiamientoInsightState.periods : [];
    if (!periods.length) {
      if (finTableHead) finTableHead.innerHTML = "";
      if (finTableBody) finTableBody.innerHTML = '<tr><td class="cg-insight-empty">Sin datos</td></tr>';
      if (finSvg) finSvg.innerHTML = "";
      return;
    }
    var rowsMap = financiamientoInsightView === "gap" ? financiamientoInsightState.gapRows : financiamientoInsightState.pctRows;
    var labels = ["Activo total", "Pasivo", "Capital", "Resultado"];
    var rows = labels.map(function (label) {
      return {
        label: label,
        labels: periods.map(function (period) { return period.label; }),
        values: periods.map(function (period) {
          var value = rowsMap[label] && rowsMap[label][period.key];
          return Number.isFinite(value) ? value : null;
        })
      };
    });
    if (finPanelBadge) finPanelBadge.textContent = financiamientoInsightView === "gap" ? "GAP" : "% crecimiento";
    if (finPanelSubtitle) finPanelSubtitle.textContent = financiamientoInsightView === "gap"
      ? "Brecha entre el estándar ideal de st y el porcentaje proyectado de cada rubro."
      : "Porcentaje de activo total representado por cada rubro en cada año.";
    if (finTableHead) {
      finTableHead.innerHTML = '<tr><th>Rubro</th>' + periods.map(function (period) {
        return '<th>' + esc(period.label) + '</th>';
      }).join("") + '</tr>';
    }
    if (finTableBody) {
      finTableBody.innerHTML = labels.map(function (label) {
        return '<tr><td>' + esc(label) + '</td>' + periods.map(function (period) {
          var value = rowsMap[label] && rowsMap[label][period.key];
          return '<td>' + esc(Number.isFinite(value) ? formatPercent(value) : "") + '</td>';
        }).join("") + '</tr>';
      }).join("");
    }
    renderMiniInsightChart(rows, financiamientoInsightView === "gap" ? "GAP" : "% crecimiento");
  }

  function renderActivoChart(rows) {
    if (!chartSvg || !window.Chart) return;
    var data = (Array.isArray(rows) ? rows : []).filter(function (row) {
      return Number.isFinite(parseNumber(row && row.saldo));
    });
    if (!data.length) {
      activoChartInstance = destroyChart(activoChartInstance);
      return;
    }
    activoChartInstance = destroyChart(activoChartInstance);
    activoChartInstance = new window.Chart(chartSvg.getContext("2d"), {
      type: "line",
      data: {
        labels: data.map(function (row) { return row.year; }),
        datasets: [{
          label: "Activo total",
          data: data.map(function (row) { return parseNumber(row.saldo); }),
          borderColor: getComputedStyle(document.documentElement).getPropertyValue("--sidebar-bottom").trim() || "#0f172a",
          backgroundColor: "rgba(15,23,42,0.12)",
          pointBackgroundColor: "#ffffff",
          pointBorderColor: getComputedStyle(document.documentElement).getPropertyValue("--sidebar-bottom").trim() || "#0f172a",
          pointBorderWidth: 2,
          pointRadius: 5,
          pointHoverRadius: 6,
          borderWidth: 4,
          fill: true,
          tension: 0.32
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        aspectRatio: 2.8,
        animation: { duration: 2200, easing: "easeOutQuart" },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                return "Activo total: " + formatAmount(ctx.parsed.y);
              }
            }
          }
        },
        scales: {
          x: { grid: { display: false } },
          y: {
            ticks: {
              callback: function (value) { return formatAmount(Number(value)); }
            }
          }
        }
      }
    });
  }

  function recomputeActivoProjectedRows() {
    var previousSaldo = null;
    activoRowsState.forEach(function (row) {
      if (!row) return;
      var saldo = parseNumber(row.saldo);
      if (!row.projected) {
        previousSaldo = Number.isFinite(saldo) ? saldo : previousSaldo;
        return;
      }
      var pct = parseNumber(row.pct);
      if (Number.isFinite(previousSaldo) && Number.isFinite(pct)) {
        var crecimiento = previousSaldo * (pct / 100);
        var nextSaldo = previousSaldo + crecimiento;
        row.crecimiento = crecimiento;
        row.saldo = nextSaldo;
        previousSaldo = nextSaldo;
      } else {
        row.crecimiento = null;
        row.saldo = null;
      }
    });
  }

  function renderActivo(rows) {
    if (!tbodyActivo) return;
    activoRowsState = Array.isArray(rows) ? rows.slice() : [];
    if (!activoRowsState.length) {
      tbodyActivo.innerHTML = '<tr><td colspan="4">Sin datos</td></tr>';
      return;
    }
    recomputeActivoProjectedRows();
    renderActivoChart(activoRowsState);
      tbodyActivo.innerHTML = activoRowsState.map(function (r, idx) {
      var pctCell = r.projected
        ? '<div class="cg-pct-input-wrap"><input class="input input-bordered campo input-sm cg-input cg-input-projection text-right" data-cg-row="' + idx + '" value="' + esc(formatPercentInput(parseNumber(r.pct))) + '"></div>'
        : esc(formatPercent(parseNumber(r.pct)));
      return "<tr>" +
        "<td>" + esc(r.year) + "</td>" +
        "<td class=\"text-right cg-readonly-cell\">" + esc(formatAmount(parseNumber(r.saldo))) + "</td>" +
        "<td class=\"text-right cg-readonly-cell\">" + esc(formatAmount(parseNumber(r.crecimiento))) + "</td>" +
        "<td class=\"text-right cg-pct-col\">" + pctCell + "</td>" +
      "</tr>";
    }).join("");
    tbodyActivo.querySelectorAll("input[data-cg-row]").forEach(function (input) {
      input.addEventListener("input", function () {
        var rowIdx = parseInt(this.getAttribute("data-cg-row") || "", 10);
        if (!Number.isFinite(rowIdx) || !activoRowsState[rowIdx]) return;
        var pct = parseNumber(this.value);
        activoRowsState[rowIdx].pct = Number.isFinite(pct) ? pct : null;
        activoGrowthMap[String(activoRowsState[rowIdx].offset)] = Number.isFinite(pct) ? String(pct) : "";
      });
      input.addEventListener("focus", function () {
        var rowIdx = parseInt(this.getAttribute("data-cg-row") || "", 10);
        if (!Number.isFinite(rowIdx) || !activoRowsState[rowIdx]) return;
        var pct = parseNumber(activoRowsState[rowIdx].pct);
        this.value = Number.isFinite(pct) ? pct.toFixed(2) : "00.00";
        this.select();
      });
      input.addEventListener("blur", function () {
        var rowIdx = parseInt(this.getAttribute("data-cg-row") || "", 10);
        if (!Number.isFinite(rowIdx) || !activoRowsState[rowIdx]) return;
        var pct = parseNumber(this.value);
        activoRowsState[rowIdx].pct = Number.isFinite(pct) ? pct : null;
        activoGrowthMap[String(activoRowsState[rowIdx].offset)] = Number.isFinite(pct) ? String(pct) : "";
        renderActivo(activoRowsState);
      });
    });
  }

  function renderFinanciamiento(data) {
    var pasivoRows = data && Array.isArray(data.pasivo_total) ? data.pasivo_total : [];
    var patrimonioRows = data && Array.isArray(data.patrimonio) ? data.patrimonio : [];
    var pasivoCapitalDetalle = data && data.pasivo_capital_detalle && typeof data.pasivo_capital_detalle === "object"
      ? data.pasivo_capital_detalle
      : {};
    var capitalDetalle = data && data.capital_detalle && typeof data.capital_detalle === "object"
      ? data.capital_detalle
      : {};
    var crecimientoDetalle = data && data.crecimiento_detalle && typeof data.crecimiento_detalle === "object"
      ? data.crecimiento_detalle
      : {};
    var financiamientoActivo = data && data.financiamiento_activo && typeof data.financiamiento_activo === "object"
      ? data.financiamiento_activo
      : {};
    var financiamientoStandards = financiamientoActivo && typeof financiamientoActivo.standards === "object"
      ? financiamientoActivo.standards
      : {};
    financiamientoStandardsState = {
      Pasivo: String(financiamientoStandards.Pasivo || "80"),
      Capital: String(financiamientoStandards.Capital || "18"),
      Resultado: String(financiamientoStandards.Resultado || "2")
    };
    financiamientoPasivoPctState = financiamientoActivo && typeof financiamientoActivo.pasivo_pct_map === "object"
      ? Object.keys(financiamientoActivo.pasivo_pct_map).reduce(function (acc, key) {
          acc[String(key)] = String(financiamientoActivo.pasivo_pct_map[key] || "");
          return acc;
        }, {})
      : {};
    financiamientoResultadoPctState = financiamientoActivo && typeof financiamientoActivo.resultado_pct_map === "object"
      ? Object.keys(financiamientoActivo.resultado_pct_map).reduce(function (acc, key) {
          acc[String(key)] = String(financiamientoActivo.resultado_pct_map[key] || "");
          return acc;
        }, {})
      : {};
    var faPeriods = Array.isArray(financiamientoActivo.periods) ? financiamientoActivo.periods : [];
    var faRows = Array.isArray(financiamientoActivo.rows) ? financiamientoActivo.rows : [];
    financiamientoInsightState = { periods: faPeriods.slice(), pctRows: {}, gapRows: {} };
    if (financiamientoActivoThead) {
      if (financiamientoActivoColgroup) {
        financiamientoActivoColgroup.innerHTML = faPeriods.length
          ? '<col style="width:var(--cg-st-width)"><col style="width:var(--cg-concept-width)"><col style="width:var(--cg-gap-width)">' + faPeriods.map(function () {
              return '<col style="width:148px">';
            }).join("")
          : "";
      }
      financiamientoActivoThead.innerHTML = faPeriods.length
        ? '<tr><th style="width:var(--cg-st-width);min-width:var(--cg-st-width);" class="text-center">st</th><th style="width:var(--cg-concept-width);min-width:var(--cg-concept-width);">Concepto</th><th class="cg-fin-gap"></th>' + faPeriods.map(function (period) {
            return '<th class="text-right cg-col-amount">' + esc(period.label) + '</th>';
          }).join("") + '</tr>'
        : "";
    }
    if (financiamientoActivoTbody) {
      if (!faRows.length) {
        financiamientoActivoTbody.innerHTML = '<tr><td colspan="3">Sin datos</td></tr>';
      } else {
        var html = "";
        var blockIndex = 0;
        for (var i = 0; i < faRows.length; i += 1) {
          var row = faRows[i] || {};
          var label = String(row.label || "");
          var isValidation = label === "Validación";
          var values = Array.isArray(row.values) ? row.values : [];
          var standard = "";
          if (label === "Pasivo") standard = String(financiamientoStandardsState.Pasivo || "80") + "%";
          else if (label === "Capital") standard = String(financiamientoStandardsState.Capital || "18") + "%";
          else if (label === "Resultado") standard = String(financiamientoStandardsState.Resultado || "2") + "%";
          if (isValidation) {
            html += "<tr class=\"cg-fin-validation\">"
              + "<td class=\"cg-fin-sticky-st\"></td>"
              + "<td class=\"cg-fin-label cg-fin-sticky\">" + esc(label) + "</td>"
              + "<td class=\"cg-fin-gap\"></td>"
              + values.map(function (value) {
                  return "<td class=\"text-right\">" + esc(value || "") + "</td>";
                }).join("")
              + "</tr>";
            continue;
          }
          var nextRow = faRows[i + 1] || {};
          var nextValues = Array.isArray(nextRow.values) ? nextRow.values : [];
          financiamientoInsightState.gapRows[label] = financiamientoInsightState.gapRows[label] || {};
          nextValues.forEach(function (value, valueIdx) {
            var period = faPeriods[valueIdx] || {};
            var periodKey = String(period.key || "");
            var pctNum = parseNumber(value);
            var stNum = parseNumber(financiamientoStandardsState[label] || "");
            if (label === "Activo total") stNum = 100;
            if (Number.isFinite(pctNum) && Number.isFinite(stNum)) {
              financiamientoInsightState.gapRows[label][periodKey] = pctNum - stNum;
            }
          });
          var blockClass = (blockIndex % 2 === 0) ? "cg-fin-block-even" : "cg-fin-block-odd";
          if (label === "Activo total") {
            html += "<tr class=\"cg-fin-group-amount " + blockClass + "\">"
              + "<td class=\"cg-fin-sticky-st\"></td>"
              + "<td class=\"cg-fin-label cg-fin-sticky\">" + esc(label) + "</td>"
              + "<td class=\"cg-fin-gap\"></td>"
              + values.map(function (value) {
                  return "<td class=\"text-right\">" + esc(value || "") + "</td>";
                }).join("")
              + "</tr>";
            blockIndex += 1;
            i += 1;
            continue;
          }
          var standardCell = standard
            ? '<input class="input input-bordered input-sm celda_editable text-right w-full" style="color:#f8fafc !important;-backendkit-text-fill-color:#f8fafc !important;caret-color:#f8fafc !important;background:var(--cg-accent) !important;border-color:var(--cg-accent) !important;" data-cg-standard="' + esc(label) + '" value="' + esc(String(standard) + "%") + '">'
            : '';
          html += "<tr class=\"cg-fin-group-amount " + blockClass + "\">"
            + "<td class=\"cg-fin-sticky-st\" rowspan=\"2\">" + standardCell + "</td>"
            + "<td class=\"cg-fin-label cg-fin-sticky\" rowspan=\"2\">" + esc(label) + "</td>"
            + "<td class=\"cg-fin-gap\" rowspan=\"2\"></td>"
            + values.map(function (value) {
                return "<td class=\"text-right\">" + esc(value || "") + "</td>";
              }).join("")
            + "</tr>";
          html += "<tr class=\"cg-fin-group-growth cg-fin-growth-row " + blockClass + "\">"
            + nextValues.map(function (value, valueIdx) {
                var period = faPeriods[valueIdx] || {};
                var periodKey = String(period.key || "");
                var projected = periodKey && /^-?\d+$/.test(periodKey) && Number(periodKey) >= 0;
                if (label === "Pasivo" && projected) {
                  var editableValue = financiamientoPasivoPctState[periodKey];
                  var displayValue = editableValue ? (editableValue + "%") : (String(value || ""));
                  return '<td class="text-right"><input class="input input-bordered input-sm celda_editable text-right w-full" style="color:#f8fafc !important;-backendkit-text-fill-color:#f8fafc !important;caret-color:#f8fafc !important;background:var(--cg-accent) !important;border-color:var(--cg-accent) !important;" data-cg-pasivo-period="' + esc(periodKey) + '" value="' + esc(displayValue) + '"></td>';
                }
                if (label === "Resultado" && projected) {
                  var editableResultado = financiamientoResultadoPctState[periodKey];
                  var displayResultado = editableResultado ? (editableResultado + "%") : (String(value || ""));
                  return '<td class="text-right"><input class="input input-bordered input-sm celda_editable text-right w-full" style="color:#f8fafc !important;-backendkit-text-fill-color:#f8fafc !important;caret-color:#f8fafc !important;background:var(--cg-accent) !important;border-color:var(--cg-accent) !important;" data-cg-resultado-period="' + esc(periodKey) + '" value="' + esc(displayResultado) + '"></td>';
                }
                return "<td class=\"text-right\">" + esc(value || "") + "</td>";
              }).join("")
            + "</tr>";
          blockIndex += 1;
          i += 1;
        }
        financiamientoActivoTbody.innerHTML = html;
        financiamientoActivoTbody.querySelectorAll("input[data-cg-standard]").forEach(function (input) {
          input.addEventListener("focus", function () {
            var key = String(this.getAttribute("data-cg-standard") || "");
            var current = financiamientoStandardsState[key];
            this.value = current ? String(current) : "";
            this.select();
          });
          input.addEventListener("blur", function () {
            var key = String(this.getAttribute("data-cg-standard") || "");
            var numeric = parseNumber(this.value);
            financiamientoStandardsState[key] = Number.isFinite(numeric) ? String(Math.round(numeric * 100) / 100).replace(/\.0+$/, "").replace(/(\.\d*[1-9])0+$/, "$1") : "";
            this.value = financiamientoStandardsState[key] ? (financiamientoStandardsState[key] + "%") : "";
          });
          input.addEventListener("input", function () {
            var key = String(this.getAttribute("data-cg-standard") || "");
            var numeric = parseNumber(this.value);
            financiamientoStandardsState[key] = Number.isFinite(numeric) ? String(numeric) : "";
          });
        });
        financiamientoActivoTbody.querySelectorAll("input[data-cg-pasivo-period]").forEach(function (input) {
          input.addEventListener("focus", function () {
            var key = String(this.getAttribute("data-cg-pasivo-period") || "");
            var current = financiamientoPasivoPctState[key];
            this.value = current ? String(current) : "";
            this.select();
          });
          input.addEventListener("input", function () {
            var key = String(this.getAttribute("data-cg-pasivo-period") || "");
            var numeric = parseNumber(this.value);
            financiamientoPasivoPctState[key] = Number.isFinite(numeric) ? String(numeric) : "";
          });
          input.addEventListener("blur", function () {
            var key = String(this.getAttribute("data-cg-pasivo-period") || "");
            var numeric = parseNumber(this.value);
            financiamientoPasivoPctState[key] = Number.isFinite(numeric)
              ? String(Math.round(numeric * 100) / 100).replace(/\.0+$/, "").replace(/(\.\d*[1-9])0+$/, "$1")
              : "";
            this.value = financiamientoPasivoPctState[key] ? (financiamientoPasivoPctState[key] + "%") : "";
          });
        });
        financiamientoActivoTbody.querySelectorAll("input[data-cg-resultado-period]").forEach(function (input) {
          input.addEventListener("focus", function () {
            var key = String(this.getAttribute("data-cg-resultado-period") || "");
            var current = financiamientoResultadoPctState[key];
            this.value = current ? String(current) : "";
            this.select();
          });
          input.addEventListener("input", function () {
            var key = String(this.getAttribute("data-cg-resultado-period") || "");
            var numeric = parseNumber(this.value);
            financiamientoResultadoPctState[key] = Number.isFinite(numeric) ? String(numeric) : "";
          });
          input.addEventListener("blur", function () {
            var key = String(this.getAttribute("data-cg-resultado-period") || "");
            var numeric = parseNumber(this.value);
            financiamientoResultadoPctState[key] = Number.isFinite(numeric)
              ? String(Math.round(numeric * 100) / 100).replace(/\.0+$/, "").replace(/(\.\d*[1-9])0+$/, "$1")
              : "";
            this.value = financiamientoResultadoPctState[key] ? (financiamientoResultadoPctState[key] + "%") : "";
          });
        });
        renderFinanciamientoInsight();
      }
    }
    if (!pasivoRows.length && !patrimonioRows.length) {
      if (tbodyPasivo) tbodyPasivo.innerHTML = '<tr><td colspan="4">Sin datos</td></tr>';
      if (tbodyPatrimonio) tbodyPatrimonio.innerHTML = '<tr><td colspan="4">Sin datos</td></tr>';
    }
    if (tbodyPasivo) {
      tbodyPasivo.innerHTML = pasivoRows.length ? pasivoRows.map(function (r) {
        return "<tr><td>" + esc(r.rubro) + "</td><td class=\"text-right\">" + esc(r.y0) + "</td><td class=\"text-right\">" + esc(r.y1) + "</td><td class=\"text-right\">" + esc(r.proj) + "</td></tr>";
      }).join("") : '<tr><td colspan="4">Sin datos</td></tr>';
    }
    if (tbodyPatrimonio) {
      tbodyPatrimonio.innerHTML = patrimonioRows.length ? patrimonioRows.map(function (r) {
        return "<tr><td>" + esc(r.rubro) + "</td><td class=\"text-right\">" + esc(r.y0) + "</td><td class=\"text-right\">" + esc(r.y1) + "</td><td class=\"text-right\">" + esc(r.proj) + "</td></tr>";
      }).join("") : '<tr><td colspan="4">Sin datos</td></tr>';
    }
    function renderPasivoCapitalDetalle(periods, rows, colgroupEl, theadEl, tbodyEl, options) {
      var config = options && typeof options === "object" ? options : {};
      var singleRow = !!config.singleRow;
      var safePeriods = Array.isArray(periods) ? periods : [];
      var safeRows = Array.isArray(rows) ? rows : [];
      if (colgroupEl) {
        colgroupEl.innerHTML = safePeriods.length
          ? '<col style="width:180px">' + safePeriods.map(function () {
              return '<col style="width:148px">';
            }).join("")
          : "";
      }
      if (theadEl) {
        theadEl.innerHTML = safePeriods.length
          ? '<tr><th style="width:180px;min-width:180px;">Concepto</th>' + safePeriods.map(function (period) {
              return '<th class="text-right cg-col-amount">' + esc(period.label) + '</th>';
            }).join("") + '</tr>'
          : "";
      }
      if (!tbodyEl) return;
      if (!safeRows.length) {
        tbodyEl.innerHTML = '<tr><td colspan="2">Sin datos</td></tr>';
        return;
      }
      var html = "";
      var blockIndex = 0;
      if (singleRow) {
        safeRows.forEach(function (row) {
          if (!row || String(row.kind || "") !== "amount") return;
          var amountValues = Array.isArray(row.values) ? row.values : [];
          var blockClass = (blockIndex % 2 === 0) ? "cg-pc-block-even" : "cg-pc-block-odd";
          html += '<tr class="cg-pc-group-amount ' + blockClass + '">'
            + '<td class="cg-pc-sticky">' + esc(String(row.label || "")) + '</td>'
            + amountValues.map(function (value) {
                return '<td class="text-right">' + esc(value || "") + '</td>';
              }).join("")
            + '</tr>';
          blockIndex += 1;
        });
        tbodyEl.innerHTML = html;
        return;
      }
      for (var idx = 0; idx < safeRows.length; idx += 1) {
        var amountRow = safeRows[idx] || {};
        var growthRow = safeRows[idx + 1] || {};
        var amountValues = Array.isArray(amountRow.values) ? amountRow.values : [];
        var growthValues = Array.isArray(growthRow.values) ? growthRow.values : [];
        var blockClass = (blockIndex % 2 === 0) ? "cg-pc-block-even" : "cg-pc-block-odd";
        var hasSecondRow = String(amountRow.kind || "") === "amount" && String(growthRow.kind || "") === "growth";
        if (!hasSecondRow) {
          html += '<tr class="cg-pc-group-amount ' + blockClass + '">'
            + '<td class="cg-pc-sticky">' + esc(String(amountRow.label || "")) + '</td>'
            + amountValues.map(function (value) {
                return '<td class="text-right">' + esc(value || "") + '</td>';
              }).join("")
            + '</tr>';
          blockIndex += 1;
          continue;
        }
        html += '<tr class="cg-pc-group-amount ' + blockClass + '">'
          + '<td class="cg-pc-sticky" rowspan="2">' + esc(String(amountRow.label || "")) + '</td>'
          + amountValues.map(function (value) {
              return '<td class="text-right">' + esc(value || "") + '</td>';
            }).join("")
          + '</tr>';
        html += '<tr class="cg-pc-group-growth ' + blockClass + '">'
          + growthValues.map(function (value) {
              return '<td class="text-right">' + esc(value || "") + '</td>';
            }).join("")
          + '</tr>';
        blockIndex += 1;
        idx += 1;
      }
      tbodyEl.innerHTML = html;
    }

    renderPasivoCapitalDetalle(
      Array.isArray(pasivoCapitalDetalle.periods) ? pasivoCapitalDetalle.periods : [],
      Array.isArray(pasivoCapitalDetalle.rows) ? pasivoCapitalDetalle.rows : [],
      pasivoCapitalColgroup,
      pasivoCapitalThead,
      pasivoCapitalTbody,
      { singleRow: true }
    );
    renderPasivoCapitalDetalle(
      Array.isArray(capitalDetalle.periods) ? capitalDetalle.periods : [],
      Array.isArray(capitalDetalle.rows) ? capitalDetalle.rows : [],
      capitalDetalleColgroup,
      capitalDetalleThead,
      capitalDetalleTbody,
      { singleRow: true }
    );
    renderPasivoCapitalDetalle(
      Array.isArray(crecimientoDetalle.periods) ? crecimientoDetalle.periods : [],
      Array.isArray(crecimientoDetalle.rows) ? crecimientoDetalle.rows : [],
      crecimientoDetalleColgroup,
      crecimientoDetalleThead,
      crecimientoDetalleTbody
    );
    var crecimientoPeriods = Array.isArray(crecimientoDetalle.periods) ? crecimientoDetalle.periods : [];
    var crecimientoRows = Array.isArray(crecimientoDetalle.rows) ? crecimientoDetalle.rows : [];
    if (crecimientoPeriods.length) {
      financiamientoInsightState.periods = crecimientoPeriods.slice();
    }
    crecimientoRows.forEach(function (row) {
      var label = String(row && row.label || "");
      var values = Array.isArray(row && row.values) ? row.values : [];
      if (!label) return;
      financiamientoInsightState.pctRows[label] = financiamientoInsightState.pctRows[label] || {};
      values.forEach(function (value, valueIdx) {
        var period = crecimientoPeriods[valueIdx] || {};
        var periodKey = String(period.key || "");
        var pctNum = parseNumber(value);
        if (Number.isFinite(pctNum)) {
          financiamientoInsightState.pctRows[label][periodKey] = pctNum;
        }
      });
    });
    renderFinanciamientoInsight();
  }

  async function load() {
    try {
      var [resResumen, resActivo] = await Promise.all([
        fetch("/api/proyectando/crecimiento-general/resumen"),
        fetch("/api/proyectando/crecimiento-general/activo-total")
      ]);
      var jsonResumen = await resResumen.json();
      var jsonActivo = await resActivo.json();
      var data = (jsonResumen && jsonResumen.data) || {};
      var activoData = (jsonActivo && jsonActivo.data) || {};
      activoGrowthMap = activoData && typeof activoData.growth_map === "object" ? activoData.growth_map : {};
      renderActivo(Array.isArray(activoData.rows) && activoData.rows.length ? activoData.rows : (Array.isArray(data.activo_total) ? data.activo_total : []));
      renderFinanciamiento(data);
    } catch (_) {
      renderActivo([]);
      renderFinanciamiento({});
    }
  }

  async function saveActivo() {
    if (activoMsg) activoMsg.textContent = "Guardando...";
    try {
      var res = await fetch("/api/proyectando/crecimiento-general/activo-total", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ growth_map: activoGrowthMap })
      });
      var json = await res.json().catch(function () { return {}; });
      if (!res.ok || !json || json.success === false) {
        throw new Error((json && (json.error || json.detail)) || "No se pudo guardar");
      }
      var data = json.data || {};
      activoGrowthMap = data && typeof data.growth_map === "object" ? data.growth_map : activoGrowthMap;
      renderActivo(Array.isArray(data.rows) ? data.rows : []);
      if (activoMsg) activoMsg.textContent = "Guardado.";
      load();
    } catch (err) {
      if (activoMsg) activoMsg.textContent = (err && err.message) ? err.message : "Error al guardar.";
    }
  }

  async function savePasivoPlaceholder() {
    if (pasivoMsg) pasivoMsg.textContent = "Guardando...";
    if (patrimonioMsg) patrimonioMsg.textContent = "Guardando...";
    try {
      var res = await fetch("/api/proyectando/crecimiento-general/financiamiento-activo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({
          standards: financiamientoStandardsState,
          pasivo_pct_map: financiamientoPasivoPctState,
          resultado_pct_map: financiamientoResultadoPctState
        })
      });
      var json = await res.json().catch(function () { return {}; });
      if (!res.ok || !json || json.success === false) {
        throw new Error((json && (json.error || json.detail)) || "No se pudo guardar");
      }
      var data = json.data || {};
      if (data && typeof data.standards === "object") {
        financiamientoStandardsState = {
          Pasivo: String(data.standards.Pasivo || "80"),
          Capital: String(data.standards.Capital || "18"),
          Resultado: String(data.standards.Resultado || "2")
        };
      }
      financiamientoPasivoPctState = data && typeof data.pasivo_pct_map === "object"
        ? Object.keys(data.pasivo_pct_map).reduce(function (acc, key) {
            acc[String(key)] = String(data.pasivo_pct_map[key] || "");
            return acc;
          }, {})
        : financiamientoPasivoPctState;
      financiamientoResultadoPctState = data && typeof data.resultado_pct_map === "object"
        ? Object.keys(data.resultado_pct_map).reduce(function (acc, key) {
            acc[String(key)] = String(data.resultado_pct_map[key] || "");
            return acc;
          }, {})
        : financiamientoResultadoPctState;
      renderFinanciamiento({ financiamiento_activo: data, pasivo_total: [], patrimonio: [] });
      if (pasivoMsg) pasivoMsg.textContent = "Guardado.";
      if (patrimonioMsg) patrimonioMsg.textContent = "Guardado.";
    } catch (err) {
      if (pasivoMsg) pasivoMsg.textContent = (err && err.message) ? err.message : "Error al guardar.";
      if (patrimonioMsg) patrimonioMsg.textContent = (err && err.message) ? err.message : "Error al guardar.";
    }
  }

  var tabs = Array.prototype.slice.call(document.querySelectorAll("[data-tab]"));
  var panels = Array.prototype.slice.call(document.querySelectorAll(".tab-panel[data-panel]"));
  function setTab(tabKey) {
    var target = String(tabKey || "activo-total");
    tabs.forEach(function (tabBtn) {
      var on = (tabBtn.getAttribute("data-tab") || "") === target;
      tabBtn.classList.toggle("tab-active", on);
      tabBtn.classList.toggle("active", on);
    });
    panels.forEach(function (panelEl) {
      var show = (panelEl.getAttribute("data-panel") || "") === target;
      panelEl.hidden = !show;
      panelEl.style.display = show ? "block" : "none";
    });
  }
  tabs.forEach(function (tabBtn) {
    tabBtn.addEventListener("click", function () {
      setTab(tabBtn.getAttribute("data-tab") || "activo-total");
    });
  });
  if (chartToggleBtn && chartPanel) {
    chartToggleBtn.addEventListener("click", function () {
      chartPanel.classList.toggle("open");
      var expanded = chartPanel.classList.contains("open");
      chartToggleBtn.setAttribute("aria-expanded", expanded ? "true" : "false");
      if (expanded) renderActivoChart(activoRowsState);
    });
  }
  document.querySelectorAll("[data-cg-fin-view]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      financiamientoInsightView = String(btn.getAttribute("data-cg-fin-view") || "pct");
      document.querySelectorAll("[data-cg-fin-view]").forEach(function (other) {
        other.classList.toggle("active", other === btn);
      });
      renderFinanciamientoInsight();
    });
  });
  if (finToggleBtn && finPanel) {
    finToggleBtn.addEventListener("click", function () {
      finPanel.classList.toggle("open");
      var expanded = finPanel.classList.contains("open");
      finToggleBtn.setAttribute("aria-expanded", expanded ? "true" : "false");
      if (expanded) renderFinanciamientoInsight();
    });
  }
  if (activoSaveBtn) activoSaveBtn.addEventListener("click", saveActivo);
  if (pasivoSaveBtn) pasivoSaveBtn.addEventListener("click", savePasivoPlaceholder);
  if (patrimonioSaveBtn) patrimonioSaveBtn.addEventListener("click", savePasivoPlaceholder);
  setTab("activo-total");
  load();
})();
