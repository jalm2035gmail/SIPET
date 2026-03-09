(function () {
  var tabs = Array.prototype.slice.call(document.querySelectorAll("[data-af-tab]"));
  var panels = Array.prototype.slice.call(document.querySelectorAll("[data-af-panel]"));
  var comprasThead = document.getElementById("af-compras-thead");
  var comprasTbody = document.getElementById("af-compras-tbody");
  var comprasSaveBtn = document.getElementById("af-compras-save-btn");
  var comprasMsg = document.getElementById("af-compras-msg");
  var depreciacionComprasThead = document.getElementById("af-depreciacion-compras-thead");
  var depreciacionComprasTbody = document.getElementById("af-depreciacion-compras-tbody");
  var saldosThead = document.getElementById("af-saldos-thead");
  var saldosTbody = document.getElementById("af-saldos-tbody");
  var revalThead = document.getElementById("af-reval-thead");
  var revalTbody = document.getElementById("af-reval-tbody");
  var depThead = document.getElementById("af-dep-thead");
  var depTbody = document.getElementById("af-dep-tbody");
  var saldosPeriodsState = [];
  var saldosRowsState = [];
  var revalPeriodsState = [];
  var revalRowsState = [];
  var depPeriodsState = [];
  var depRowsState = [];
  var comprasRowsState = [];
  var comprasYearsState = [];
  var activoFijoRubrosBase = [
    "Propiedades, mobiliario y equipo",
    "Terrenos",
    "Construcciones",
    "Equipo de transporte",
    "Equipo de cómputo",
    "Mobiliario",
    "Adaptaciones y mejoras"
  ];

  function esc(v) {
    return String(v == null ? "" : v)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function setTab(tabKey) {
    var target = String(tabKey || "compras");
    tabs.forEach(function (tabBtn) {
      var active = (tabBtn.getAttribute("data-af-tab") || "") === target;
      tabBtn.classList.toggle("tab-active", active);
      tabBtn.classList.toggle("active", active);
    });
    panels.forEach(function (panel) {
      var show = (panel.getAttribute("data-af-panel") || "") === target;
      panel.hidden = !show;
      panel.style.display = show ? "block" : "none";
    });
  }

  function renderComprasTable(data) {
    var years = Array.isArray(data && data.years) ? data.years : [];
    var rows = Array.isArray(data && data.rows) ? data.rows : [];
    comprasYearsState = years.slice();
    comprasRowsState = rows.map(function (row) {
      return {
        rubro: String(row && row.rubro || ""),
        proyecciones: Array.isArray(row && row.proyecciones) ? row.proyecciones.slice() : []
      };
    });
    if (comprasThead) {
      comprasThead.innerHTML = '<tr><th>Rubro</th>' + years.map(function (year) {
        return '<th class="text-right">' + esc(year) + '</th>';
      }).join("") + '</tr>';
    }
    if (!comprasTbody) return;
    if (!comprasRowsState.length) {
      comprasTbody.innerHTML = '<tr><td class="text-base-content/60">Sin rubros configurados.</td></tr>';
      return;
    }
    function recalculateComprasTotalRow() {
      if (!comprasRowsState.length) return;
      for (var colIdx = 0; colIdx < years.length; colIdx += 1) {
        var total = 0;
        var hasValue = false;
        for (var rowIdx = 1; rowIdx < comprasRowsState.length; rowIdx += 1) {
          var raw = String(comprasRowsState[rowIdx].proyecciones[colIdx] || "").replace(/,/g, "").trim();
          var numeric = Number(raw);
          if (Number.isFinite(numeric)) {
            total += numeric;
            hasValue = true;
          }
        }
        comprasRowsState[0].proyecciones[colIdx] = hasValue ? Math.round(total).toLocaleString("en-US") : "";
      }
    }
    recalculateComprasTotalRow();
    comprasTbody.innerHTML = comprasRowsState.map(function (row, rowIdx) {
      return '<tr><td>' + esc(row.rubro) + '</td>' + years.map(function (_, colIdx) {
        var value = row.proyecciones[colIdx] || "";
        var readonly = rowIdx === 0;
        var inputClass = readonly
          ? "input input-bordered campo input-sm w-full text-right bg-base-200 text-base-content/80"
          : "input input-bordered campo input-sm w-full text-right";
        return '<td class="text-right"><input class="' + inputClass + '" data-af-row="' + rowIdx + '" data-af-col="' + colIdx + '" value="' + esc(value) + '"' + (readonly ? ' readonly tabindex="-1"' : '') + '></td>';
      }).join("") + '</tr>';
    }).join("");
    comprasTbody.querySelectorAll("input[data-af-row][data-af-col]").forEach(function (input) {
      input.addEventListener("input", function () {
        var rowIdx = parseInt(this.getAttribute("data-af-row") || "", 10);
        var colIdx = parseInt(this.getAttribute("data-af-col") || "", 10);
        if (!Number.isFinite(rowIdx) || !Number.isFinite(colIdx) || !comprasRowsState[rowIdx] || rowIdx === 0) return;
        comprasRowsState[rowIdx].proyecciones[colIdx] = this.value;
        recalculateComprasTotalRow();
        var totalInput = comprasTbody.querySelector('input[data-af-row="0"][data-af-col="' + colIdx + '"]');
        if (totalInput) totalInput.value = comprasRowsState[0].proyecciones[colIdx] || "";
      });
      input.addEventListener("blur", function () {
        var cleaned = String(this.value || "").replace(/,/g, "").trim();
        var rowIdx = parseInt(this.getAttribute("data-af-row") || "", 10);
        var colIdx = parseInt(this.getAttribute("data-af-col") || "", 10);
        if (rowIdx === 0) return;
        if (!cleaned) {
          this.value = "";
          if (Number.isFinite(rowIdx) && Number.isFinite(colIdx) && comprasRowsState[rowIdx]) {
            comprasRowsState[rowIdx].proyecciones[colIdx] = "";
            recalculateComprasTotalRow();
            var totalInput = comprasTbody.querySelector('input[data-af-row="0"][data-af-col="' + colIdx + '"]');
            if (totalInput) totalInput.value = comprasRowsState[0].proyecciones[colIdx] || "";
          }
          return;
        }
        var numeric = Number(cleaned);
        if (Number.isFinite(numeric)) {
          this.value = Math.round(numeric).toLocaleString("en-US");
          if (Number.isFinite(rowIdx) && Number.isFinite(colIdx) && comprasRowsState[rowIdx]) {
            comprasRowsState[rowIdx].proyecciones[colIdx] = this.value;
            recalculateComprasTotalRow();
            var totalInput2 = comprasTbody.querySelector('input[data-af-row="0"][data-af-col="' + colIdx + '"]');
            if (totalInput2) totalInput2.value = comprasRowsState[0].proyecciones[colIdx] || "";
          }
        }
      });
    });
    renderDepreciacionComprasTable();
  }

  async function buildEmptyComprasFallback() {
    var startYear = new Date().getFullYear() + 1;
    var projectionYears = 3;
    try {
      var res = await fetch("/api/proyectando/datos-preliminares", { credentials: "same-origin" });
      var json = await res.json().catch(function () { return {}; });
      var data = json && json.data ? json.data : {};
      var parsedStart = Number(String(data.primer_anio_proyeccion || "").trim());
      var parsedYears = Number(String(data.anios_proyeccion || "").trim());
      if (Number.isFinite(parsedStart) && parsedStart > 0) startYear = parsedStart;
      if (Number.isFinite(parsedYears) && parsedYears > 0) projectionYears = Math.max(1, Math.trunc(parsedYears));
    } catch (_) {}
    renderComprasTable({
      years: Array.from({ length: projectionYears }, function (_, idx) { return startYear + idx; }),
      rows: activoFijoRubrosBase.map(function (rubro) {
        return { rubro: rubro, proyecciones: Array.from({ length: projectionYears }, function () { return ""; }) };
      })
    });
  }

  function renderSaldosTable() {
    if (saldosThead) {
      saldosThead.innerHTML = '<tr><th style="width:220px;min-width:220px;">Concepto</th>' + saldosPeriodsState.map(function (year) {
        return '<th class="text-right">' + esc(year) + '</th>';
      }).join("") + '</tr>';
    }
    if (!saldosTbody) return;
    if (!saldosRowsState.length) {
      saldosTbody.innerHTML = '<tr><td class="text-base-content/60">Sin datos.</td></tr>';
      return;
    }
    saldosTbody.innerHTML = saldosRowsState.map(function (row, idx) {
      var blockClass = (idx % 2 === 0) ? "af-fin-block-even" : "af-fin-block-odd";
      return '<tr class="af-fin-group-amount ' + blockClass + '">'
        + '<td class="af-fin-sticky">' + esc(row.rubro) + '</td>'
        + saldosPeriodsState.map(function (_, colIdx) {
            return '<td class="text-right">' + esc(row.values[colIdx] || "") + '</td>';
          }).join("")
        + '</tr>';
    }).join("");
  }

  function renderRevaluacionesTable() {
    if (revalThead) {
      revalThead.innerHTML = '<tr><th style="width:220px;min-width:220px;">Concepto</th>' + revalPeriodsState.map(function (year) {
        return '<th class="text-right">' + esc(year) + '</th>';
      }).join("") + '</tr>';
    }
    if (!revalTbody) return;
    if (!revalRowsState.length) {
      revalTbody.innerHTML = '<tr><td class="text-base-content/60">Sin datos.</td></tr>';
      return;
    }
    revalTbody.innerHTML = revalRowsState.map(function (row, idx) {
      var blockClass = (idx % 2 === 0) ? "af-fin-block-even" : "af-fin-block-odd";
      return '<tr class="af-fin-group-amount ' + blockClass + '">'
        + '<td class="af-fin-sticky">' + esc(row.rubro) + '</td>'
        + revalPeriodsState.map(function (_, colIdx) {
            return '<td class="text-right">' + esc(row.values[colIdx] || "") + '</td>';
          }).join("")
        + '</tr>';
    }).join("");
  }

  async function buildEmptyRevaluacionesFallback() {
    var startYear = new Date().getFullYear() + 1;
    var projectionYears = 3;
    try {
      var res = await fetch("/api/proyectando/datos-preliminares", { credentials: "same-origin" });
      var json = await res.json().catch(function () { return {}; });
      var data = json && json.data ? json.data : {};
      var parsedStart = Number(String(data.primer_anio_proyeccion || "").trim());
      var parsedYears = Number(String(data.anios_proyeccion || "").trim());
      if (Number.isFinite(parsedStart) && parsedStart > 0) startYear = parsedStart;
      if (Number.isFinite(parsedYears) && parsedYears > 0) projectionYears = Math.max(1, Math.trunc(parsedYears));
    } catch (_) {}
    revalPeriodsState = [];
    for (var offset = -3; offset < projectionYears; offset += 1) {
      revalPeriodsState.push(String(startYear + offset));
    }
    revalRowsState = [
      "Terrenos",
      "Construcciones",
      "Equipo de cómputo",
      "Mobiliario",
      "Adaptaciones y mejoras"
    ].map(function (rubro) {
      return { rubro: rubro, values: revalPeriodsState.map(function () { return ""; }) };
    });
    renderRevaluacionesTable();
  }

  function renderDepreciacionTable() {
    if (depThead) {
      depThead.innerHTML = '<tr><th style="width:220px;min-width:220px;">Concepto</th>' + depPeriodsState.map(function (year) {
        return '<th class="text-right">' + esc(year) + '</th>';
      }).join("") + '</tr>';
    }
    if (!depTbody) return;
    if (!depRowsState.length) {
      depTbody.innerHTML = '<tr><td class="text-base-content/60">Sin datos.</td></tr>';
      return;
    }
    depTbody.innerHTML = depRowsState.map(function (row, idx) {
      var blockClass = (idx % 2 === 0) ? "af-fin-block-even" : "af-fin-block-odd";
      return '<tr class="af-fin-group-amount ' + blockClass + '">'
        + '<td class="af-fin-sticky">' + esc(row.rubro) + '</td>'
        + depPeriodsState.map(function (_, colIdx) {
            return '<td class="text-right">' + esc(row.values[colIdx] || "") + '</td>';
          }).join("")
        + '</tr>';
    }).join("");
  }

  async function buildEmptyDepreciacionFallback() {
    var startYear = new Date().getFullYear() + 1;
    var projectionYears = 3;
    try {
      var res = await fetch("/api/proyectando/datos-preliminares", { credentials: "same-origin" });
      var json = await res.json().catch(function () { return {}; });
      var data = json && json.data ? json.data : {};
      var parsedStart = Number(String(data.primer_anio_proyeccion || "").trim());
      var parsedYears = Number(String(data.anios_proyeccion || "").trim());
      if (Number.isFinite(parsedStart) && parsedStart > 0) startYear = parsedStart;
      if (Number.isFinite(parsedYears) && parsedYears > 0) projectionYears = Math.max(1, Math.trunc(parsedYears));
    } catch (_) {}
    depPeriodsState = [];
    for (var offset = -3; offset < projectionYears; offset += 1) {
      depPeriodsState.push(String(startYear + offset));
    }
    depRowsState = [
      "Propiedades, mobiliario y equipo",
      "Terrenos",
      "Construcciones",
      "Equipo de transporte",
      "Equipo de cómputo",
      "Mobiliario",
      "Adaptaciones y mejoras"
    ].map(function (rubro) {
      return { rubro: rubro, values: depPeriodsState.map(function () { return ""; }) };
    });
    renderDepreciacionTable();
  }

  async function buildEmptySaldosFallback() {
    var startYear = new Date().getFullYear() + 1;
    var projectionYears = 3;
    try {
      var res = await fetch("/api/proyectando/datos-preliminares", { credentials: "same-origin" });
      var json = await res.json().catch(function () { return {}; });
      var data = json && json.data ? json.data : {};
      var parsedStart = Number(String(data.primer_anio_proyeccion || "").trim());
      var parsedYears = Number(String(data.anios_proyeccion || "").trim());
      if (Number.isFinite(parsedStart) && parsedStart > 0) startYear = parsedStart;
      if (Number.isFinite(parsedYears) && parsedYears > 0) projectionYears = Math.max(1, Math.trunc(parsedYears));
    } catch (_) {}
    saldosPeriodsState = [];
    for (var offset = -3; offset < projectionYears; offset += 1) {
      saldosPeriodsState.push(String(startYear + offset));
    }
    saldosRowsState = activoFijoRubrosBase.map(function (rubro) {
      return {
        rubro: rubro,
        values: saldosPeriodsState.map(function () { return ""; })
      };
    });
    renderSaldosTable();
    loadDepreciacion();
  }

  async function loadSaldos() {
    await buildEmptySaldosFallback();
    try {
      var res = await fetch("/api/proyectando/activo-fijo/saldos", { credentials: "same-origin" });
      var json = await res.json().catch(function () { return {}; });
      if (!res.ok || !json || json.success === false) {
        throw new Error((json && (json.error || json.detail)) || "No se pudo cargar saldos de activo fijo");
      }
      var data = json.data || {};
      saldosPeriodsState = Array.isArray(data.periods) ? data.periods.map(function (period) { return period.label; }) : [];
      saldosRowsState = Array.isArray(data.rows) ? data.rows.map(function (row) {
        return {
          rubro: String(row && row.rubro || ""),
          values: Array.isArray(row && row.values) ? row.values.slice() : []
        };
      }) : [];
      renderSaldosTable();
      loadDepreciacion();
    } catch (err) {
      renderSaldosTable();
      loadDepreciacion();
    }
  }

  async function loadRevaluaciones() {
    await buildEmptyRevaluacionesFallback();
    try {
      var res = await fetch("/api/proyectando/activo-fijo/revaluaciones", { credentials: "same-origin" });
      var json = await res.json().catch(function () { return {}; });
      if (!res.ok || !json || json.success === false) {
        throw new Error((json && (json.error || json.detail)) || "No se pudo cargar revaluaciones");
      }
      var data = json.data || {};
      revalPeriodsState = Array.isArray(data.periods) ? data.periods.map(function (period) { return period.label; }) : [];
      revalRowsState = Array.isArray(data.rows) ? data.rows.map(function (row) {
        return {
          rubro: String(row && row.rubro || ""),
          values: Array.isArray(row && row.values) ? row.values.slice() : []
        };
      }) : [];
      renderRevaluacionesTable();
    } catch (err) {
      renderRevaluacionesTable();
    }
  }

  async function loadDepreciacion() {
    await buildEmptyDepreciacionFallback();
    try {
      var res = await fetch("/api/proyectando/activo-fijo/depreciacion", { credentials: "same-origin" });
      var json = await res.json().catch(function () { return {}; });
      if (!res.ok || !json || json.success === false) {
        throw new Error((json && (json.error || json.detail)) || "No se pudo cargar depreciación");
      }
      var data = json.data || {};
      depPeriodsState = Array.isArray(data.periods) ? data.periods.map(function (period) { return period.label; }) : [];
      depRowsState = Array.isArray(data.rows) ? data.rows.map(function (row) {
        return {
          rubro: String(row && row.rubro || ""),
          values: Array.isArray(row && row.values) ? row.values.slice() : []
        };
      }) : [];
      renderDepreciacionTable();
    } catch (err) {
      renderDepreciacionTable();
    }
  }

  function renderDepreciacionComprasTable() {
    if (depreciacionComprasThead) {
      depreciacionComprasThead.innerHTML = '<tr><th style="width:220px;min-width:220px;">Concepto</th>' + comprasYearsState.map(function (year) {
        return '<th class="text-right">' + esc(year) + '</th>';
      }).join("") + '</tr>';
    }
    if (!depreciacionComprasTbody) return;
    if (!comprasRowsState.length) {
      depreciacionComprasTbody.innerHTML = '<tr><td class="text-base-content/60">Sin datos.</td></tr>';
      return;
    }
    depreciacionComprasTbody.innerHTML = comprasRowsState.map(function (row, idx) {
      var blockClass = (idx % 2 === 0) ? "af-fin-block-even" : "af-fin-block-odd";
      return '<tr class="af-fin-group-amount ' + blockClass + '">'
        + '<td class="af-fin-sticky">' + esc(row.rubro) + '</td>'
        + comprasYearsState.map(function () {
            return '<td class="text-right"></td>';
          }).join("")
        + '</tr>';
    }).join("");
  }

  async function loadCompras() {
    await buildEmptyComprasFallback();
    try {
      var res = await fetch("/api/proyectando/activo-fijo/compras", { credentials: "same-origin" });
      var json = await res.json().catch(function () { return {}; });
      if (!res.ok || !json || json.success === false) {
        throw new Error((json && (json.error || json.detail)) || "No se pudo cargar compras de activo fijo");
      }
      renderComprasTable(json.data || {});
    } catch (err) {
      renderComprasTable({ years: comprasYearsState, rows: comprasRowsState });
    }
  }

  async function saveCompras() {
    if (comprasMsg) comprasMsg.textContent = "Guardando...";
    try {
      var res = await fetch("/api/proyectando/activo-fijo/compras", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ rows: comprasRowsState })
      });
      var json = await res.json().catch(function () { return {}; });
      if (!res.ok || !json || json.success === false) {
        throw new Error((json && (json.error || json.detail)) || "No se pudo guardar");
      }
      renderComprasTable(json.data || {});
      loadSaldos();
      if (comprasMsg) comprasMsg.textContent = "Guardado.";
    } catch (err) {
      if (comprasMsg) comprasMsg.textContent = (err && err.message) || "Error al guardar.";
    }
  }

  tabs.forEach(function (tabBtn) {
    tabBtn.addEventListener("click", function () {
      setTab(tabBtn.getAttribute("data-af-tab") || "compras");
    });
  });
  if (comprasSaveBtn) comprasSaveBtn.addEventListener("click", saveCompras);
  setTab("compras");
  loadCompras();
  loadSaldos();
  loadRevaluaciones();
  loadDepreciacion();
})();
