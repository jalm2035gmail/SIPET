(function () {
  var keyById = {
    "dp-responsable-general": "responsable_general",
    "dp-primer-anio": "primer_anio_proyeccion",
    "dp-anios": "anios_proyeccion",
    "dp-moneda": "moneda",
    "dp-inflacion": "inflacion_estimada",
    "dp-tasa": "tasa_crecimiento",
    "dp-observaciones": "observaciones",
    "dp-sociedad": "sociedad",
    "dp-figura-juridica": "figura_juridica",
    "dp-calle": "calle",
    "dp-numero-exterior": "numero_exterior",
    "dp-numero-interior": "numero_interior",
    "dp-colonia": "colonia",
    "dp-ciudad": "ciudad",
    "dp-municipio": "municipio",
    "dp-estado": "estado",
    "dp-cp": "cp",
    "dp-pais": "pais",
    "dp-macro-inflacion-json": "macro_inflacion_json",
    "dp-macro-udi-json": "macro_udi_json",
    "dp-ifb-activos-m3": "ifb_activos_m3",
    "dp-ifb-activos-m2": "ifb_activos_m2",
    "dp-ifb-activos-m1": "ifb_activos_m1",
    "dp-ifb-pasivos-m3": "ifb_pasivos_m3",
    "dp-ifb-pasivos-m2": "ifb_pasivos_m2",
    "dp-ifb-pasivos-m1": "ifb_pasivos_m1",
    "dp-ifb-capital-m3": "ifb_capital_m3",
    "dp-ifb-capital-m2": "ifb_capital_m2",
    "dp-ifb-capital-m1": "ifb_capital_m1",
    "dp-ifb-ingresos-m3": "ifb_ingresos_m3",
    "dp-ifb-ingresos-m2": "ifb_ingresos_m2",
    "dp-ifb-ingresos-m1": "ifb_ingresos_m1",
    "dp-ifb-egresos-m3": "ifb_egresos_m3",
    "dp-ifb-egresos-m2": "ifb_egresos_m2",
    "dp-ifb-egresos-m1": "ifb_egresos_m1",
    "dp-ifb-resultado-m3": "ifb_resultado_m3",
    "dp-ifb-resultado-m2": "ifb_resultado_m2",
    "dp-ifb-resultado-m1": "ifb_resultado_m1",
    "dp-ifb-rows-json": "ifb_rows_json",
    "dp-ifb-conceptos-json": "ifb_conceptos_json",
    "dp-cg-activo-total-growth-json": "cg_activo_total_growth_json",
    "dp-cg-activo-total-rows-json": "cg_activo_total_rows_json",
    "dp-cg-financiamiento-rows-json": "cg_financiamiento_rows_json",
    "dp-activo-fijo-json": "activo_fijo_json",
    "dp-gastos-rows-json": "gastos_rows_json"
  };

  var saveBtn = document.getElementById("dp-save-btn");
  var clearBtn = document.getElementById("dp-clear-btn");
  var msg = document.getElementById("dp-msg");
  var macroThead = document.getElementById("dp-macro-thead");
  var macroTbody = document.getElementById("dp-macro-tbody");
  var activoFijoTbody = document.getElementById("dp-activo-fijo-tbody");
  var activoFijoTotal = document.getElementById("dp-af-total");
  var activoFijoDepreciables = document.getElementById("dp-af-depreciables");
  var activoFijoPromedio = document.getElementById("dp-af-promedio");
  var gastosSearch = document.getElementById("dp-gastos-search");
  var gastosThead = document.getElementById("dp-gastos-thead");
  var gastosTbody = document.getElementById("dp-gastos-tbody");
  var gastosTotal = document.getElementById("dp-gastos-total");
  var gastosLevels = document.getElementById("dp-gastos-levels");
  var gastosCaptured = document.getElementById("dp-gastos-captured");
  var ifbDetalleThead = document.getElementById("dp-ifb-detalle-thead");
  var ifbDetalleTbody = document.getElementById("dp-ifb-detalle-tbody");
  var ifCatalogSearch = document.getElementById("dp-if-search");
  var ifCatalogThead = document.getElementById("dp-if-catalog-thead");
  var ifCatalogTbody = document.getElementById("dp-if-catalog-tbody");
  var ifCatalogTotal = document.getElementById("dp-if-total");
  var ifCatalogLevels = document.getElementById("dp-if-levels");
  var ifDownloadBtn = document.getElementById("dp-if-download-template");
  var ifUploadBtn = document.getElementById("dp-if-upload-data");
  var ifUploadFile = document.getElementById("dp-if-upload-file");
  var ifUploadMsg = document.getElementById("dp-if-upload-msg");
  var financialCatalogRows = [];
  var financialRowsState = [];
  var gastosRowsState = [];
  var gastosProjectionYears = 3;

  function parseMacroMap(raw) {
    try {
      var parsed = JSON.parse(raw || "{}");
      return parsed && typeof parsed === "object" ? parsed : {};
    } catch (_) {
      return {};
    }
  }

  function writeMacroMaps(inflacionMap, udiMap) {
    var inflacionEl = document.getElementById("dp-macro-inflacion-json");
    var udiEl = document.getElementById("dp-macro-udi-json");
    if (inflacionEl) inflacionEl.value = JSON.stringify(inflacionMap || {});
    if (udiEl) udiEl.value = JSON.stringify(udiMap || {});
  }

  function getMacroYears(inflacionMap, udiMap) {
    var yearsSet = {};
    Object.keys(inflacionMap || {}).forEach(function (y) { if (/^\d{4}$/.test(y)) yearsSet[y] = true; });
    Object.keys(udiMap || {}).forEach(function (y) { if (/^\d{4}$/.test(y)) yearsSet[y] = true; });
    var years = Object.keys(yearsSet).sort();
    if (years.length) return years;
    var primer = parseInt((document.getElementById("dp-primer-anio") || {}).value || "", 10);
    if (!Number.isFinite(primer)) primer = new Date().getFullYear();
    return [primer - 2, primer - 1, primer, primer + 1, primer + 2, primer + 3].map(function (n) { return String(n); });
  }

  function renderMacroTable() {
    if (!macroThead || !macroTbody) return;
    var inflacionEl = document.getElementById("dp-macro-inflacion-json");
    var udiEl = document.getElementById("dp-macro-udi-json");
    var inflacionMap = parseMacroMap(inflacionEl ? inflacionEl.value : "");
    var udiMap = parseMacroMap(udiEl ? udiEl.value : "");
    var years = getMacroYears(inflacionMap, udiMap);

    macroThead.innerHTML =
      "<tr><th>Variable</th>" +
      years.map(function (y) { return "<th>" + y + "</th>"; }).join("") +
      "</tr>";

    function rowHtml(label, rowKey, mapObj, placeholder) {
      return "<tr>" +
        "<td>" + label + "</td>" +
        years.map(function (y) {
          var val = mapObj[y] != null ? String(mapObj[y]) : "";
          return "<td><input class=\"input input-bordered input-sm campo w-full text-right\" data-macro-row=\"" + rowKey + "\" data-year=\"" + y + "\" placeholder=\"" + placeholder + "\" value=\"" +
            val.replace(/&/g, "&amp;").replace(/\"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;") +
            "\"></td>";
        }).join("") +
      "</tr>";
    }

    macroTbody.innerHTML =
      rowHtml("Inflación", "inflacion", inflacionMap, "0.00%") +
      rowHtml("UDI", "udi", udiMap, "0.000000");

    macroTbody.querySelectorAll("input[data-macro-row]").forEach(function (input) {
      input.addEventListener("input", function () {
        var row = this.getAttribute("data-macro-row");
        var year = this.getAttribute("data-year");
        var value = (this.value || "").trim();
        if (row === "inflacion") {
          if (value) inflacionMap[year] = value; else delete inflacionMap[year];
        } else {
          if (value) udiMap[year] = value; else delete udiMap[year];
        }
        writeMacroMaps(inflacionMap, udiMap);
      });
    });
    writeMacroMaps(inflacionMap, udiMap);
  }

  function parseActivoFijoRows(raw) {
    try {
      var parsed = JSON.parse(raw || "[]");
      if (!Array.isArray(parsed)) return [];
      return parsed
        .filter(function (row) { return row && typeof row === "object"; })
        .map(function (row) {
          return {
            rubro: String(row.rubro || "").trim(),
            anios: String(row.anios || "").trim()
          };
        });
    } catch (_) {
      return [];
    }
  }

  function ensureActivoFijoDefaultRows(rows) {
    if (Array.isArray(rows) && rows.length) return rows;
    return [
      { rubro: "Terrenos", anios: "0" },
      { rubro: "Construcciones", anios: "20" },
      { rubro: "Construcciones en proceso", anios: "5" },
      { rubro: "Equipo de transporte", anios: "4" },
      { rubro: "Equipo de cómputo", anios: "3" },
      { rubro: "Mobiliario", anios: "3" },
      { rubro: "Otras propiedades, mobiliario y equipo", anios: "2" }
    ];
  }

  function writeActivoFijoRows(rows) {
    var activoFijoEl = document.getElementById("dp-activo-fijo-json");
    if (activoFijoEl) activoFijoEl.value = JSON.stringify(rows || []);
  }

  function updateActivoFijoSummary(rows) {
    if (!Array.isArray(rows)) rows = [];
    var depreciables = rows.reduce(function (acc, row) {
      var anios = parseFloat(String((row && row.anios) || "").replace(/,/g, ""));
      return acc + ((Number.isFinite(anios) && anios > 0) ? 1 : 0);
    }, 0);
    var activosConVida = rows
      .map(function (row) { return parseFloat(String((row && row.anios) || "").replace(/,/g, "")); })
      .filter(function (value) { return Number.isFinite(value) && value > 0; });
    var promedio = activosConVida.length
      ? (activosConVida.reduce(function (sum, value) { return sum + value; }, 0) / activosConVida.length).toFixed(2)
      : "";
    if (activoFijoTotal) activoFijoTotal.textContent = String(rows.length);
    if (activoFijoDepreciables) activoFijoDepreciables.textContent = String(depreciables);
    if (activoFijoPromedio) activoFijoPromedio.textContent = promedio || "—";
  }

  function renderActivoFijoTable() {
    if (!activoFijoTbody) return;
    var activoFijoEl = document.getElementById("dp-activo-fijo-json");
    var rows = ensureActivoFijoDefaultRows(parseActivoFijoRows(activoFijoEl ? activoFijoEl.value : "[]"));
    activoFijoTbody.innerHTML = rows.map(function (row, idx) {
      var rubro = String(row.rubro || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
      var anios = String(row.anios || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
      var depreciable = parseFloat(String(row.anios || "").replace(/,/g, "")) > 0 ? "Sí" : "No";
      return "<tr>" +
        "<td><input class=\"input input-bordered input-sm campo w-full\" data-af-row=\"" + idx + "\" data-af-col=\"rubro\" value=\"" + rubro + "\"></td>" +
        "<td><input class=\"input input-bordered input-sm campo w-full text-right\" data-af-row=\"" + idx + "\" data-af-col=\"anios\" value=\"" + anios + "\"></td>" +
        "<td><span class=\"badge badge-outline\">" + depreciable + "</span></td>" +
      "</tr>";
    }).join("");
    activoFijoTbody.querySelectorAll("input[data-af-row]").forEach(function (input) {
      input.addEventListener("input", function () {
        var idx = parseInt(this.getAttribute("data-af-row") || "", 10);
        var col = this.getAttribute("data-af-col");
        if (!Number.isFinite(idx) || idx < 0 || idx >= rows.length) return;
        rows[idx][col] = (this.value || "").trim();
        writeActivoFijoRows(rows);
        updateActivoFijoSummary(rows);
        if (col === "anios") {
          var tr = this.closest("tr");
          var badge = tr ? tr.querySelector(".badge") : null;
          if (badge) badge.textContent = parseFloat(String(rows[idx].anios || "").replace(/,/g, "")) > 0 ? "Sí" : "No";
        }
      });
    });
    writeActivoFijoRows(rows);
    updateActivoFijoSummary(rows);
  }

  function parseGastosRows(raw) {
    try {
      var parsed = JSON.parse(raw || "[]");
      if (!Array.isArray(parsed)) return [];
      return parsed.filter(function (row) { return row && typeof row === "object"; }).map(function (row) {
        var projections = Array.isArray(row.proyecciones) ? row.proyecciones : [];
        return {
          codigo: String(row.codigo || "").trim(),
          rubro: String(row.rubro || "").trim(),
          m3: String(row.m3 || "").trim(),
          m2: String(row.m2 || "").trim(),
          m1: String(row.m1 || "").trim(),
          proyecciones: projections.map(function (value) { return String(value == null ? "" : value).trim(); })
        };
      });
    } catch (_) {
      return [];
    }
  }

  function writeGastosRows(rows) {
    var gastosEl = document.getElementById("dp-gastos-rows-json");
    if (gastosEl) gastosEl.value = JSON.stringify(rows || []);
  }

  function getGastoDepth(codigo) {
    var value = String(codigo || "").trim();
    return value ? value.split(".").length - 1 : 0;
  }

  function updateGastosSummary(rows) {
    var levels = {};
    var captured = 0;
    (rows || []).forEach(function (row) {
      var depth = getGastoDepth(row && row.codigo);
      levels[String(depth + 1)] = true;
      var hasValue = ["m3", "m2", "m1"].some(function (key) {
        return String((row && row[key]) || "").trim() !== "";
      }) || (Array.isArray(row && row.proyecciones) && row.proyecciones.some(function (value) {
        return String(value || "").trim() !== "";
      }));
      if (hasValue) captured += 1;
    });
    if (gastosTotal) gastosTotal.textContent = String((rows || []).length);
    if (gastosLevels) {
      var levelKeys = Object.keys(levels).sort(function (a, b) { return Number(a) - Number(b); });
      gastosLevels.textContent = levelKeys.length ? levelKeys.join(", ") : "—";
    }
    if (gastosCaptured) gastosCaptured.textContent = String(captured);
  }

  function renderGastosTable() {
    if (!gastosThead || !gastosTbody) return;
    var rows = Array.isArray(gastosRowsState) ? gastosRowsState : [];
    var query = String((gastosSearch && gastosSearch.value) || "").trim().toLowerCase();
    var filtered = rows.filter(function (row) {
      if (!query) return true;
      return String(row.codigo || "").toLowerCase().indexOf(query) >= 0
        || String(row.rubro || "").toLowerCase().indexOf(query) >= 0;
    });
    gastosThead.innerHTML = "<tr><th class=\"w-40\">Código</th><th>Rubro</th><th class=\"text-right\">M-3</th><th class=\"text-right\">M-2</th><th class=\"text-right\">M-1</th>"
      + Array.from({ length: gastosProjectionYears }).map(function (_, idx) {
          return "<th class=\"text-right\">Y" + (idx + 1) + "</th>";
        }).join("")
      + "</tr>";
    updateGastosSummary(filtered);
    if (!filtered.length) {
      gastosTbody.innerHTML = '<tr><td colspan="' + (5 + gastosProjectionYears) + '" class="text-base-content/60">No hay coincidencias para el filtro actual.</td></tr>';
      return;
    }
    gastosTbody.innerHTML = filtered.map(function (row) {
      var idx = rows.indexOf(row);
      var depth = getGastoDepth(row.codigo);
      var indent = 16 + (depth * 22);
      var weight = depth === 0 ? 800 : (depth === 1 ? 700 : 500);
      var inputs = ["m3", "m2", "m1"].map(function (key) {
        var val = String(row[key] || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
        return "<td><input class=\"input input-bordered input-sm campo w-28 text-right\" data-gasto-row=\"" + idx + "\" data-gasto-col=\"" + key + "\" value=\"" + val + "\"></td>";
      }).join("");
      var projections = Array.from({ length: gastosProjectionYears }).map(function (_, projIdx) {
        var val = String((row.proyecciones && row.proyecciones[projIdx]) || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
        return "<td><input class=\"input input-bordered input-sm campo w-28 text-right\" data-gasto-row=\"" + idx + "\" data-gasto-col=\"proyeccion\" data-gasto-proj=\"" + projIdx + "\" value=\"" + val + "\"></td>";
      }).join("");
      return "<tr>"
        + "<td class=\"font-mono text-xs sm:text-sm\">" + String(row.codigo || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;") + "</td>"
        + "<td><div style=\"padding-left:" + indent + "px;font-weight:" + weight + ";\">" + String(row.rubro || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;") + "</div></td>"
        + inputs
        + projections
        + "</tr>";
    }).join("");
    gastosTbody.querySelectorAll("input[data-gasto-row]").forEach(function (input) {
      input.addEventListener("input", function () {
        var rowIdx = parseInt(this.getAttribute("data-gasto-row") || "", 10);
        if (!Number.isFinite(rowIdx) || !rows[rowIdx]) return;
        var col = this.getAttribute("data-gasto-col");
        if (col === "proyeccion") {
          var projIdx = parseInt(this.getAttribute("data-gasto-proj") || "", 10);
          if (!Array.isArray(rows[rowIdx].proyecciones)) rows[rowIdx].proyecciones = [];
          rows[rowIdx].proyecciones[projIdx] = (this.value || "").trim();
        } else {
          rows[rowIdx][col] = (this.value || "").trim();
        }
        writeGastosRows(rows);
        updateGastosSummary(rows);
      });
    });
    writeGastosRows(rows);
  }

  function renderIfbDetalleTable() {
    if (!ifbDetalleThead || !ifbDetalleTbody) return;
    var raw = (document.getElementById("dp-ifb-rows-json") || {}).value || "[]";
    var rows;
    try {
      rows = JSON.parse(raw);
      if (!Array.isArray(rows)) rows = [];
    } catch (_) {
      rows = [];
    }
    if (!rows.length) {
      ifbDetalleThead.innerHTML = "";
      ifbDetalleTbody.innerHTML = "<tr><td>Sin filas en ifb_rows_json</td></tr>";
      return;
    }
    var maxVals = rows.reduce(function (acc, row) {
      var values = Array.isArray(row && row.values) ? row.values : [];
      return Math.max(acc, values.length);
    }, 0);
    var labels = ["M-3", "M-2", "M-1", "0", "+1", "+2", "+3", "+4"];
    var cols = [];
    for (var i = 0; i < maxVals; i++) cols.push(labels[i] || ("Col " + (i + 1)));
    ifbDetalleThead.innerHTML =
      "<tr><th>Cod</th><th>Rubro</th>" +
      cols.map(function (c) { return "<th class=\"text-right\">" + c + "</th>"; }).join("") +
      "</tr>";
    ifbDetalleTbody.innerHTML = rows.map(function (row) {
      var vals = Array.isArray(row && row.values) ? row.values : [];
      return "<tr>" +
        "<td>" + String(row && row.cod != null ? row.cod : "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;") + "</td>" +
        "<td>" + String(row && row.rubro != null ? row.rubro : "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;") + "</td>" +
        cols.map(function (_, idx) {
          var v = vals[idx] != null ? String(vals[idx]) : "";
          return "<td class=\"text-right\">" + v.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;") + "</td>";
        }).join("") +
      "</tr>";
    }).join("");
  }

  function getIfIndentLevel(nivel) {
    var value = Number(nivel || 0);
    if (value >= 9) return 3;
    if (value >= 6) return 2;
    if (value >= 3) return 1;
    return 0;
  }

  function getIfProjectionYears() {
    var raw = (document.getElementById("dp-anios") || {}).value || "";
    var years = parseInt(String(raw).trim(), 10);
    if (!Number.isFinite(years)) years = 3;
    return Math.max(1, Math.min(years, 10));
  }

  function getIfPeriods() {
    var primerRaw = (document.getElementById("dp-primer-anio") || {}).value || "";
    var primerAnio = parseInt(String(primerRaw).trim(), 10);
    if (!Number.isFinite(primerAnio)) primerAnio = new Date().getFullYear();
    var futureYears = getIfProjectionYears();
    var periods = [
      { key: "-3", label: String(primerAnio - 3) },
      { key: "-2", label: String(primerAnio - 2) },
      { key: "-1", label: String(primerAnio - 1) }
    ];
    for (var idx = 0; idx < futureYears; idx += 1) {
      periods.push({
        key: String(idx),
        label: String(primerAnio + idx)
      });
    }
    return periods;
  }

  function parseIfRows(raw) {
    try {
      var parsed = JSON.parse(raw || "[]");
      if (!Array.isArray(parsed)) return [];
      return parsed.filter(function (row) {
        return row && typeof row === "object";
      }).map(function (row) {
        var values = row.values && typeof row.values === "object" && !Array.isArray(row.values)
          ? row.values
          : {};
        if ((!values || !Object.keys(values).length) && Array.isArray(row.values)) {
          var legacyPeriods = ["-3", "-2", "-1", "0", "1", "2", "3", "4"];
          values = {};
          row.values.forEach(function (value, idx) {
            if (legacyPeriods[idx] != null) values[legacyPeriods[idx]] = String(value == null ? "" : value).trim();
          });
        }
        return {
          cuenta: String(row.cuenta || row.cod || "").trim(),
          descripcion: String(row.descripcion || row.rubro || "").trim(),
          nivel: String(row.nivel || "").trim(),
          values: Object.keys(values || {}).reduce(function (acc, key) {
            acc[String(key)] = String(values[key] == null ? "" : values[key]).trim();
            return acc;
          }, {})
        };
      });
    } catch (_) {
      return [];
    }
  }

  function writeIfRows(rows) {
    var input = document.getElementById("dp-ifb-rows-json");
    if (input) input.value = JSON.stringify(rows || []);
  }

  function getIfParentLevel6(cuenta) {
    var parts = String(cuenta || "").split("-");
    if (parts.length !== 6) return "";
    parts[2] = "00";
    parts[3] = "00";
    parts[4] = "00";
    parts[5] = "000";
    return parts.join("-");
  }

  function parseIfNumeric(value) {
    var cleaned = String(value == null ? "" : value).replace(/,/g, "").trim();
    if (!cleaned) return NaN;
    var num = Number(cleaned);
    return Number.isFinite(num) ? num : NaN;
  }

  function formatIfNumeric(value) {
    if (!Number.isFinite(value)) return "";
    return Math.round(value).toLocaleString("en-US");
  }

  function getIfDisplayRowByIndex(displayIndex) {
    var target = Number(displayIndex || 0);
    if (!Number.isFinite(target) || target <= 0) return null;
    return Array.isArray(financialRowsState) && financialRowsState[target - 1]
      ? financialRowsState[target - 1]
      : null;
  }

  function getIfPeriodWarnings(periods) {
    var row1 = getIfDisplayRowByIndex(1);
    var row49 = getIfDisplayRowByIndex(49);
    var row56 = getIfDisplayRowByIndex(56);
    var row70 = getIfDisplayRowByIndex(70);
    var warnings = {};
    periods.forEach(function (period) {
      var total = parseIfNumeric(row1 && row1.values ? row1.values[period.key] : "");
      var pasivo = parseIfNumeric(row49 && row49.values ? row49.values[period.key] : "");
      var capital = parseIfNumeric(row56 && row56.values ? row56.values[period.key] : "");
      var resultado = parseIfNumeric(row70 && row70.values ? row70.values[period.key] : "");
      var diff = (Number.isFinite(total) ? total : 0)
        - (Number.isFinite(pasivo) ? pasivo : 0)
        - (Number.isFinite(capital) ? capital : 0)
        - (Number.isFinite(resultado) ? resultado : 0);
      warnings[period.key] = Math.abs(diff) > 1e-9;
    });
    return warnings;
  }

  function recomputeIfLevel6Totals() {
    if (!Array.isArray(financialRowsState) || !financialRowsState.length) return;
    var periods = getIfPeriods().map(function (period) { return period.key; });
    var level9Rows = financialRowsState.filter(function (row) {
      return String(row.nivel || "").trim() === "9";
    });
    var grouped = {};
    level9Rows.forEach(function (row) {
      var parent = getIfParentLevel6(row.cuenta);
      if (!parent) return;
      if (!grouped[parent]) grouped[parent] = {};
      periods.forEach(function (periodKey) {
        var numeric = parseIfNumeric(row.values && row.values[periodKey]);
        if (!Number.isFinite(numeric)) return;
        grouped[parent][periodKey] = (grouped[parent][periodKey] || 0) + numeric;
      });
    });
    financialRowsState.forEach(function (row) {
      if (String(row.nivel || "").trim() !== "6") return;
      var sums = grouped[String(row.cuenta || "").trim()];
      if (!row.values || typeof row.values !== "object") row.values = {};
      periods.forEach(function (periodKey) {
        if (sums && Number.isFinite(sums[periodKey])) {
          row.values[periodKey] = formatIfNumeric(sums[periodKey]);
        } else {
          row.values[periodKey] = "";
        }
      });
    });
    var validationRow = getIfDisplayRowByIndex(71);
    var row1 = getIfDisplayRowByIndex(1);
    var row49 = getIfDisplayRowByIndex(49);
    var row56 = getIfDisplayRowByIndex(56);
    var row70 = getIfDisplayRowByIndex(70);
    if (validationRow) {
      if (!validationRow.values || typeof validationRow.values !== "object") validationRow.values = {};
      periods.forEach(function (periodKey) {
        var diff = (parseIfNumeric(row1 && row1.values ? row1.values[periodKey] : "") || 0)
          - (parseIfNumeric(row49 && row49.values ? row49.values[periodKey] : "") || 0)
          - (parseIfNumeric(row56 && row56.values ? row56.values[periodKey] : "") || 0)
          - (parseIfNumeric(row70 && row70.values ? row70.values[periodKey] : "") || 0);
        validationRow.values[periodKey] = formatIfNumeric(diff);
      });
    }
    writeIfRows(financialRowsState);
  }

  function ensureIfRowsState() {
    if (!Array.isArray(financialCatalogRows) || !financialCatalogRows.length) {
      if (!Array.isArray(financialRowsState) || !financialRowsState.length) {
        financialRowsState = parseIfRows((document.getElementById("dp-ifb-rows-json") || {}).value || "[]");
      }
      return Array.isArray(financialRowsState) ? financialRowsState : [];
    }
    var existingMap = {};
    parseIfRows((document.getElementById("dp-ifb-rows-json") || {}).value || "[]").forEach(function (row) {
      if (row.cuenta) existingMap[String(row.cuenta)] = row;
    });
    financialRowsState = financialCatalogRows.map(function (row) {
      var cuenta = String(row.cuenta || "").trim();
      var existing = existingMap[cuenta] || {};
      return {
        cuenta: cuenta,
        descripcion: String(row.descripcion || existing.descripcion || "").trim(),
        nivel: String(row.nivel || existing.nivel || "").trim(),
        values: existing.values && typeof existing.values === "object" ? existing.values : {}
      };
    });
    [
      { cuenta: "__resultado__", descripcion: "Resultado", nivel: "" },
      { cuenta: "__validacion__", descripcion: "Validación", nivel: "" },
      { cuenta: "__metric_socios__", descripcion: "# de Socios", nivel: "" },
      { cuenta: "__metric_ahorradores_menores__", descripcion: "# de Ahorradores menores", nivel: "" },
      { cuenta: "__metric_sucursales__", descripcion: "# de Sucursales (Incluyendo Matriz y/o colectoras)", nivel: "" },
      { cuenta: "__metric_empleados__", descripcion: "# de Empleados", nivel: "" },
      { cuenta: "__metric_parte_social__", descripcion: "Valor de la parte social", nivel: "" }
    ].forEach(function (synthetic) {
      var existing = existingMap[synthetic.cuenta] || {};
      financialRowsState.push({
        cuenta: synthetic.cuenta,
        descripcion: synthetic.descripcion,
        nivel: synthetic.nivel,
        values: existing.values && typeof existing.values === "object" ? existing.values : {}
      });
    });
    recomputeIfLevel6Totals();
    writeIfRows(financialRowsState);
    return financialRowsState;
  }

  function renderFinancialCatalogTable() {
    if (!ifCatalogTbody || !ifCatalogThead) return;
    var periods = getIfPeriods();
    var rowsState = ensureIfRowsState();
    var warnings = getIfPeriodWarnings(periods);
    var query = String((ifCatalogSearch && ifCatalogSearch.value) || "").trim().toLowerCase();
    var filtered = rowsState.filter(function (row) {
      if (!query) return true;
      return String(row.cuenta || "").toLowerCase().indexOf(query) >= 0
        || String(row.descripcion || "").toLowerCase().indexOf(query) >= 0
        || String(row.nivel || "").toLowerCase().indexOf(query) >= 0;
    });
    var columnCount = 3 + periods.length;
    ifCatalogThead.innerHTML = "<tr class=\"bg-base-200/80\">"
      + Array.from({ length: columnCount }).map(function (_, idx) {
          return "<th class=\"text-center text-[11px] font-bold text-base-content/60\">" + (idx + 1) + "</th>";
        }).join("")
      + "</tr>"
      + "<tr>"
      + "<th class=\"w-16 text-center\">#</th>"
      + "<th class=\"w-28\">Nivel</th>"
      + "<th class=\"min-w-[320px]\">Descripción</th>"
      + periods.map(function (period) {
          var review = warnings[period.key] ? '<div class="text-[10px] font-extrabold uppercase tracking-[0.08em] text-error">Revisar</div>' : '';
          return "<th class=\"text-right min-w-[110px]\">" + review + "<div>" + period.label + "</div></th>";
        }).join("")
      + "</tr>";
    if (ifCatalogTotal) ifCatalogTotal.textContent = String(filtered.length);
    if (ifCatalogLevels) {
      var levels = {};
      filtered.forEach(function (row) {
        var level = String(row.nivel || "").trim();
        if (level) levels[level] = true;
      });
      var labels = Object.keys(levels).sort(function (a, b) { return Number(a) - Number(b); });
      ifCatalogLevels.textContent = labels.length ? labels.join(", ") : "—";
    }
    if (!filtered.length) {
      ifCatalogTbody.innerHTML = '<tr><td colspan="' + (3 + periods.length) + '" class="text-base-content/60">No hay coincidencias para el filtro actual.</td></tr>';
      return;
    }
    ifCatalogTbody.innerHTML = filtered.map(function (row) {
      var rowIndex = rowsState.indexOf(row) + 1;
      var depth = getIfIndentLevel(row.nivel);
      var indent = 16 + (depth * 28);
      var fontWeight = depth === 0 ? 800 : (depth === 1 ? 700 : 500);
      var opacity = depth >= 2 ? 0.88 : 1;
      var rowLevel = String(row.nivel || "").trim();
      var rowClass = rowLevel === "1"
        ? ' class="dp-if-level-1"'
        : (rowLevel === "3" ? ' class="dp-if-level-3"' : "");
      var escapedCuenta = String(row.cuenta || '').replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
      var valueCells = periods.map(function (period) {
        var isProjectedPeriod = /^\d+$/.test(String(period.key || "").trim());
        var isReadOnly = rowIndex === 71 || isProjectedPeriod;
        var value = row.values && row.values[period.key] != null ? String(row.values[period.key]) : "";
        var escapedValue = value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
        return '<td><input class="input input-bordered input-sm campo w-28 text-right' + (isReadOnly ? ' dp-readonly-cell' : '') + '" data-if-row="' + escapedCuenta.replace(/"/g, "&quot;") + '" data-if-period="' + period.key + '" value="' + escapedValue + '"' + (isReadOnly ? ' readonly' : '') + '></td>';
      }).join("");
      return ''
        + '<tr' + rowClass + '>'
        +   '<td class="text-center font-mono text-xs text-base-content/60">' + rowIndex + '</td>'
        +   '<td><span class="badge badge-outline font-semibold">' + String(row.nivel || "") + '</span></td>'
        +   '<td><div style="padding-left:' + indent + 'px;font-weight:' + fontWeight + ';opacity:' + opacity + ';">' + String(row.descripcion || '').replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;") + '</div></td>'
        +   valueCells
        + '</tr>';
    }).join("");
    ifCatalogTbody.querySelectorAll("input[data-if-row]").forEach(function (input) {
      input.addEventListener("input", function () {
        var cuenta = String(this.getAttribute("data-if-row") || "");
        var period = String(this.getAttribute("data-if-period") || "");
        var row = financialRowsState.find(function (item) { return String(item.cuenta || "") === cuenta; });
        if (!row) return;
        if (!row.values || typeof row.values !== "object") row.values = {};
        row.values[period] = String(this.value || "").trim();
        recomputeIfLevel6Totals();
        renderFinancialCatalogTable();
      });
      input.addEventListener("blur", function () {
        var cuenta = String(this.getAttribute("data-if-row") || "");
        var period = String(this.getAttribute("data-if-period") || "");
        var row = financialRowsState.find(function (item) { return String(item.cuenta || "") === cuenta; });
        if (!row) return;
        var numeric = parseIfNumeric(this.value);
        if (!row.values || typeof row.values !== "object") row.values = {};
        row.values[period] = Number.isFinite(numeric) ? formatIfNumeric(numeric) : "";
        recomputeIfLevel6Totals();
        renderFinancialCatalogTable();
      });
    });
  }

  async function loadFinancialCatalog() {
    if (!ifCatalogTbody) return;
    try {
      var res = await fetch("/api/proyectando/datos-preliminares/informacion-financiera");
      var json = await res.json().catch(function () { return {}; });
      if (!res.ok || !json || json.success === false) {
        throw new Error((json && (json.error || json.detail)) || "No se pudo cargar la información financiera");
      }
      financialCatalogRows = Array.isArray(json.data) ? json.data : [];
      ensureIfRowsState();
      renderFinancialCatalogTable();
    } catch (err) {
      ifCatalogTbody.innerHTML = '<tr><td colspan="' + (3 + getIfPeriods().length) + '" class="text-error">' + ((err && err.message) ? err.message.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;") : 'No se pudo cargar la información financiera.') + '</td></tr>';
      if (ifCatalogTotal) ifCatalogTotal.textContent = "0";
      if (ifCatalogLevels) ifCatalogLevels.textContent = "—";
    }
  }

  async function loadActivoFijoResumen() {
    try {
      var res = await fetch("/api/proyectando/datos-preliminares/activo-fijo");
      var json = await res.json().catch(function () { return {}; });
      if (!res.ok || !json || json.success === false) {
        throw new Error((json && (json.error || json.detail)) || "No se pudo cargar activo fijo");
      }
      var data = json.data || {};
      var rows = Array.isArray(data.rows) ? data.rows.map(function (row) {
        return { rubro: String(row.rubro || "").trim(), anios: String(row.anios || "").trim() };
      }) : [];
      writeActivoFijoRows(rows);
      renderActivoFijoTable();
      if (data.summary) {
        if (activoFijoTotal) activoFijoTotal.textContent = String(data.summary.total || rows.length || 0);
        if (activoFijoDepreciables) activoFijoDepreciables.textContent = String(data.summary.depreciables || 0);
        if (activoFijoPromedio) activoFijoPromedio.textContent = String(data.summary.vida_util_promedio || "—");
      }
    } catch (_) {
      renderActivoFijoTable();
    }
  }

  async function loadGastosResumen() {
    try {
      var res = await fetch("/api/proyectando/datos-preliminares/gastos");
      var json = await res.json().catch(function () { return {}; });
      if (!res.ok || !json || json.success === false) {
        throw new Error((json && (json.error || json.detail)) || "No se pudieron cargar gastos");
      }
      var data = json.data || {};
      gastosRowsState = Array.isArray(data.rows) ? data.rows.map(function (row) {
        return {
          codigo: String(row.codigo || "").trim(),
          rubro: String(row.rubro || "").trim(),
          m3: String(row.m3 || "").trim(),
          m2: String(row.m2 || "").trim(),
          m1: String(row.m1 || "").trim(),
          proyecciones: Array.isArray(row.proyecciones) ? row.proyecciones.map(function (value) { return String(value || "").trim(); }) : []
        };
      }) : [];
      gastosProjectionYears = Math.max(1, Number(data.projection_years || 3) || 3);
      writeGastosRows(gastosRowsState);
      renderGastosTable();
      if (data.summary) {
        if (gastosTotal) gastosTotal.textContent = String(data.summary.total || gastosRowsState.length || 0);
        if (gastosLevels) gastosLevels.textContent = String(data.summary.niveles || "—");
        if (gastosCaptured) gastosCaptured.textContent = String(data.summary.capturados || 0);
      }
    } catch (err) {
      gastosRowsState = parseGastosRows((document.getElementById("dp-gastos-rows-json") || {}).value || "[]");
      renderGastosTable();
      if (!gastosRowsState.length && gastosTbody) {
        gastosTbody.innerHTML = '<tr><td colspan="' + (5 + gastosProjectionYears) + '" class="text-error">' + (((err && err.message) || 'No se pudieron cargar gastos').replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")) + '</td></tr>';
      }
    }
  }

  async function loadData() {
    try {
      var res = await fetch("/api/proyectando/datos-preliminares");
      var json = await res.json();
      if (!res.ok || !json || json.success === false) return;
      var data = json.data || {};
      Object.keys(keyById).forEach(function (id) {
        var el = document.getElementById(id);
        if (!el) return;
        var key = keyById[id];
        el.value = data[key] != null ? String(data[key]) : "";
      });
      renderMacroTable();
      gastosRowsState = parseGastosRows(data.gastos_rows_json || "[]");
      financialRowsState = parseIfRows(data.ifb_rows_json || "[]");
      writeIfRows(financialRowsState);
      renderIfbDetalleTable();
      if (Array.isArray(financialCatalogRows) && financialCatalogRows.length) {
        renderFinancialCatalogTable();
      }
    } catch (_) {}
  }

  async function saveData() {
    if (msg) msg.textContent = "Guardando...";
    var payload = {};
    Object.keys(keyById).forEach(function (id) {
      var el = document.getElementById(id);
      if (!el) return;
      payload[keyById[id]] = (el.value || "").trim();
    });
    try {
      var res = await fetch("/api/proyectando/datos-preliminares/datos-generales", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      var json = await res.json().catch(function () { return {}; });
      if (!res.ok || !json || json.success === false) {
        throw new Error((json && (json.error || json.detail)) || "No se pudo guardar");
      }
      if (msg) msg.textContent = "Guardado.";
    } catch (err) {
      if (msg) msg.textContent = (err && err.message) ? err.message : "Error al guardar.";
    }
  }

  function clearData() {
    Object.keys(keyById).forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.value = "";
    });
    gastosRowsState = [];
    renderMacroTable();
    renderActivoFijoTable();
    renderGastosTable();
    renderIfbDetalleTable();
    financialRowsState = [];
    writeIfRows(financialRowsState);
    renderFinancialCatalogTable();
    if (msg) msg.textContent = "Campos limpiados.";
  }

  if (saveBtn) saveBtn.addEventListener("click", saveData);
  if (clearBtn) clearBtn.addEventListener("click", clearData);
  var primerAnioInput = document.getElementById("dp-primer-anio");
  if (primerAnioInput) {
    primerAnioInput.addEventListener("change", renderMacroTable);
    primerAnioInput.addEventListener("input", renderMacroTable);
    primerAnioInput.addEventListener("change", renderFinancialCatalogTable);
    primerAnioInput.addEventListener("input", renderFinancialCatalogTable);
  }
  var aniosProyeccionInput = document.getElementById("dp-anios");
  if (aniosProyeccionInput) {
    aniosProyeccionInput.addEventListener("change", renderFinancialCatalogTable);
    aniosProyeccionInput.addEventListener("input", renderFinancialCatalogTable);
  }
  var ifbRowsTextarea = document.getElementById("dp-ifb-rows-json");
  if (ifbRowsTextarea) {
    ifbRowsTextarea.addEventListener("input", renderIfbDetalleTable);
    ifbRowsTextarea.addEventListener("change", renderIfbDetalleTable);
  }
  if (ifCatalogSearch) {
    ifCatalogSearch.addEventListener("input", renderFinancialCatalogTable);
  }
  if (ifDownloadBtn) {
    ifDownloadBtn.addEventListener("click", function () {
      window.location.href = "/api/proyectando/datos-preliminares/informacion-financiera/plantilla.csv";
    });
  }
  if (ifUploadBtn && ifUploadFile) {
    ifUploadBtn.addEventListener("click", function () {
      ifUploadFile.click();
    });
    ifUploadFile.addEventListener("change", async function () {
      var file = this.files && this.files[0];
      if (!file) return;
      if (ifUploadMsg) ifUploadMsg.textContent = "Subiendo CSV...";
      var formData = new FormData();
      formData.append("file", file);
      try {
        var res = await fetch("/api/proyectando/datos-preliminares/informacion-financiera/importar.csv", {
          method: "POST",
          credentials: "same-origin",
          body: formData
        });
        var json = await res.json().catch(function () { return {}; });
        if (!res.ok || !json || json.success === false) {
          throw new Error((json && (json.error || json.detail)) || "No se pudo importar el CSV");
        }
        await loadData();
        await loadFinancialCatalog();
        if (ifUploadMsg) ifUploadMsg.textContent = "Datos importados.";
      } catch (err) {
        if (ifUploadMsg) ifUploadMsg.textContent = (err && err.message) ? err.message : "Error al importar.";
      } finally {
        ifUploadFile.value = "";
      }
    });
  }
  if (gastosSearch) {
    gastosSearch.addEventListener("input", renderGastosTable);
  }
  var tabs = Array.prototype.slice.call(document.querySelectorAll("[data-tab]"));
  var panels = Array.prototype.slice.call(document.querySelectorAll(".tab-panel[data-panel]"));
  function setTab(tabKey) {
    var target = String(tabKey || "datos-generales");
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
      setTab(tabBtn.getAttribute("data-tab") || "datos-generales");
    });
  });
  setTab("datos-generales");
  loadData();
  loadFinancialCatalog();
  loadActivoFijoResumen();
  loadGastosResumen();
})();
