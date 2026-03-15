(() => {
          const gridEl = document.getElementById("poa-board-grid");
          const openTreeBtn = document.querySelector('.view-pill[data-view="arbol"]');
          const openGanttBtn = document.querySelector('.view-pill[data-view="gantt"]');
          const openCalendarBtn = document.querySelector('.view-pill[data-view="calendar"]');
          const msgEl = document.getElementById("poa-board-msg");
          const noOwnerMsgEl = document.getElementById("poa-no-owner-msg");
          const noSubOwnerMsgEl = document.getElementById("poa-no-subowner-msg");
          const ownerChartTotalEl = document.getElementById("poa-owner-chart-total");
          const ownerChartEmptyEl = document.getElementById("poa-owner-chart-empty");
          const ownerChartListEl = document.getElementById("poa-owner-chart-list");
          const ownerChartEl = document.getElementById("poa-owner-chart");
          const ownerChartToggleEl = document.getElementById("poa-owner-chart-toggle");
          const treeModalEl = document.getElementById("poa-tree-modal");
          const treeCloseBtn = document.getElementById("poa-tree-close");
          const treeHostEl = document.getElementById("poa-tree-host");
          const ganttModalEl = document.getElementById("poa-gantt-modal");
          const ganttCloseBtn = document.getElementById("poa-gantt-close");
          const ganttHostEl = document.getElementById("poa-gantt-host");
          const ganttBlocksEl = document.getElementById("poa-gantt-blocks");
          const ganttShowAllBtn = document.getElementById("poa-gantt-show-all");
          const ganttHideAllBtn = document.getElementById("poa-gantt-hide-all");
          const calendarModalEl = document.getElementById("poa-calendar-modal");
          const calendarCloseBtn = document.getElementById("poa-calendar-close");
          const calendarPrevBtn = document.getElementById("poa-calendar-prev");
          const calendarTodayBtn = document.getElementById("poa-calendar-today");
          const calendarNextBtn = document.getElementById("poa-calendar-next");
          const calendarMonthEl = document.getElementById("poa-calendar-month");
          const calendarGridEl = document.getElementById("poa-calendar-grid");
          const downloadTemplateBtn = document.getElementById("poa-download-template");
          const exportXlsBtn = document.getElementById("poa-export-xls");
          const importCsvBtn = document.getElementById("poa-import-csv");
          const importCsvFileEl = document.getElementById("poa-import-csv-file");
          const annualCycleSelect = document.getElementById("annual-cycle-select");
          const annualCycleStartBtn = document.getElementById("annual-cycle-start-btn");
          const annualCycleArchiveLink = document.getElementById("annual-cycle-archive-link");
          const annualCycleStatusEl = document.getElementById("annual-cycle-status");
          const modalEl = document.getElementById("poa-activity-modal");
          const closeBtn = document.getElementById("poa-activity-close");
          const cancelBtn = document.getElementById("poa-act-cancel");
          const editBottomBtn = document.getElementById("poa-act-edit-bottom");
          const saveBtn = document.getElementById("poa-act-save");
          const saveTopBtn = document.getElementById("poa-act-save-top");
          const newActBtn = document.getElementById("poa-act-new");
          const editActBtn = document.getElementById("poa-act-edit");
          const deleteActBtn = document.getElementById("poa-act-delete");
          const actListEl = document.getElementById("poa-act-list");
          const actListMsgEl = document.getElementById("poa-act-list-msg");
          const actListPanelEl = modalEl ? modalEl.querySelector(".poa-act-list-panel") : null;
          const formGridEl = modalEl ? modalEl.querySelector(".poa-form-grid") : null;
          const tabsWrapEl = document.getElementById("poa-tabs");
          const subAddBtn = document.getElementById("poa-sub-add");
          const subListEl = document.getElementById("poa-sub-list");
          const subHintEl = document.getElementById("poa-sub-hint");
          const titleEl = document.getElementById("poa-activity-title");
          const subtitleEl = document.getElementById("poa-activity-subtitle");
          const activityBranchEl = document.getElementById("poa-activity-branch");
          const assignedByEl = document.getElementById("poa-assigned-by");
          const actNameEl = document.getElementById("poa-act-name");
          const actOwnerEl = document.getElementById("poa-act-owner");
          const actAssignedEl = document.getElementById("poa-act-assigned");
          const actStartEl = document.getElementById("poa-act-start");
          const actEndEl = document.getElementById("poa-act-end");
          const actImpactHitosEl = document.getElementById("poa-act-impact-hitos");
          const actRecurrenteEl = document.getElementById("poa-act-recurrente");
          const actPeriodicidadEl = document.getElementById("poa-act-periodicidad");
          const actEveryDaysWrapEl = document.getElementById("poa-act-every-days-wrap");
          const actEveryDaysEl = document.getElementById("poa-act-every-days");
          const actDescEl = document.getElementById("poa-act-desc");
          const kpiListEl = document.getElementById("poa-kpi-list");
          const actSuggestIaBtn = document.getElementById("poa-act-suggest-ia");
          const actMsgEl = document.getElementById("poa-act-msg");
          const budgetTypeEl = document.getElementById("poa-budget-type");
          const budgetRubroEl = document.getElementById("poa-budget-rubro");
          const budgetMonthlyEl = document.getElementById("poa-budget-monthly");
          const budgetAnnualEl = document.getElementById("poa-budget-annual");
          const budgetApprovedEl = document.getElementById("poa-budget-approved");
          const budgetAddBtn = document.getElementById("poa-budget-add");
          const budgetCancelBtn = document.getElementById("poa-budget-cancel");
          const budgetListEl = document.getElementById("poa-budget-list");
          const budgetMonthlyTotalEl = document.getElementById("poa-budget-monthly-total");
          const budgetAnnualTotalEl = document.getElementById("poa-budget-annual-total");
          const budgetMsgEl = document.getElementById("poa-budget-msg");
          const delivNameEl = document.getElementById("poa-deliv-name");
          const delivAddBtn = document.getElementById("poa-deliv-add");
          const delivListEl = document.getElementById("poa-deliv-list");
          const delivMsgEl = document.getElementById("poa-deliv-msg");
          const stateNoIniciadoBtn = document.getElementById("poa-state-no-iniciado");
          const stateEnProcesoBtn = document.getElementById("poa-state-en-proceso");
          const stateTerminadoBtn = document.getElementById("poa-state-terminado");
          const stateEnRevisionBtn = document.getElementById("poa-state-en-revision");
          const statusValueEl = document.getElementById("poa-status-value");
          const progressValueEl = document.getElementById("poa-progress-value");
          const approveBtn = document.getElementById("poa-approval-approve");
          const rejectBtn = document.getElementById("poa-approval-reject");
          const subModalEl = document.getElementById("poa-sub-modal");
          const subCloseBtn = document.getElementById("poa-sub-close");
          const subCancelBtn = document.getElementById("poa-sub-cancel");
          const subSaveBtn = document.getElementById("poa-sub-save");
          const subBranchEl = document.getElementById("poa-sub-branch");
          const subNameEl = document.getElementById("poa-sub-name");
          const subOwnerEl = document.getElementById("poa-sub-owner");
          const subAssignedEl = document.getElementById("poa-sub-assigned");
          const subStartEl = document.getElementById("poa-sub-start");
          const subEndEl = document.getElementById("poa-sub-end");
          const subRecurrenteEl = document.getElementById("poa-sub-recurrente");
          const subPeriodicidadEl = document.getElementById("poa-sub-periodicidad");
          const subEveryDaysWrapEl = document.getElementById("poa-sub-every-days-wrap");
          const subEveryDaysEl = document.getElementById("poa-sub-every-days");
          const subDescEl = document.getElementById("poa-sub-desc");
          const subMsgEl = document.getElementById("poa-sub-msg");
          const setupPoaRichEditor = (textareaEl) => {
            if (!textareaEl || textareaEl.dataset.richReady === "1") return null;
            const wrap = document.createElement("div");
            wrap.className = "poa-rt-wrap";
            const toolbar = document.createElement("div");
            toolbar.className = "poa-rt-toolbar";
            const cmds = [
              { cmd: "bold", label: "B" },
              { cmd: "italic", label: "I" },
              { cmd: "underline", label: "U" },
              { cmd: "insertUnorderedList", label: "• Lista" },
              { cmd: "insertOrderedList", label: "1. Lista" },
            ];
            cmds.forEach((item) => {
              const btn = document.createElement("button");
              btn.type = "button";
              btn.className = "poa-rt-btn";
              btn.textContent = item.label;
              btn.addEventListener("click", () => {
                editor.focus();
                document.execCommand(item.cmd, false);
                textareaEl.value = editor.innerHTML;
              });
              toolbar.appendChild(btn);
            });
            const editor = document.createElement("div");
            editor.className = "poa-rt-editor";
            editor.contentEditable = "true";
            editor.innerHTML = textareaEl.value || "";
            editor.addEventListener("input", () => {
              textareaEl.value = editor.innerHTML;
            });
            wrap.appendChild(toolbar);
            wrap.appendChild(editor);
            textareaEl.style.display = "none";
            textareaEl.dataset.richReady = "1";
            textareaEl.parentNode && textareaEl.parentNode.insertBefore(wrap, textareaEl);
            return {
              getHtml: () => String(editor.innerHTML || ""),
              setHtml: (value) => {
                const html = String(value || "");
                editor.innerHTML = html;
                textareaEl.value = html;
              },
            };
          };
          const actDescRich = setupPoaRichEditor(actDescEl);
          if (!gridEl) return;
          let objectivesById = {};
          let activitiesByObjective = {};
          let approvalsByActivity = {};
          let currentObjective = null;
          let currentActivityId = null;
          let selectedListActivityId = null;
          let currentActivityData = null;
          let currentSubactivities = [];
          let currentBudgetItems = [];
          let currentDeliverables = [];
          let canValidateDeliverables = false;
          let editingBudgetIndex = -1;
          let editingSubId = null;
          let currentParentSubId = 0;
          let isSaving = false;
          let activityEditorMode = "list";
          let poaGanttVisibility = {};
          let poaGanttObjectives = [];
          let poaGanttActivities = [];
          let poaTreeVisibility = {};
          let poaCalendarCursor = new Date();
          let poaD3Promise = null;
          let annualCycleState = null;
          let poaPermissions = {
            poa_access_level: "mis_tareas",
            can_manage_content: false,
            can_view_gantt: false,
          };
          let poaIaEnabled = false;
          let allCollaboratorsCache = null;

          const escapeHtml = (value) => String(value || "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
          const fmtDate = (iso) => {
            const value = String(iso || "").trim();
            if (!value) return "N/D";
            const date = new Date(value);
            if (Number.isNaN(date.getTime())) return value;
            return date.toLocaleDateString("es-CR");
          };
          const todayIso = () => {
            const now = new Date();
            const y = now.getFullYear();
            const m = String(now.getMonth() + 1).padStart(2, "0");
            const d = String(now.getDate()).padStart(2, "0");
            return `${y}-${m}-${d}`;
          };
          const loadScript = (src) => new Promise((resolve, reject) => {
            if (document.querySelector(`script[src="${src}"]`)) {
              resolve();
              return;
            }
            const script = document.createElement("script");
            script.src = src;
            script.async = true;
            script.onload = () => resolve();
            script.onerror = () => reject(new Error(`No se pudo cargar ${src}`));
            document.head.appendChild(script);
          });
          const ensureD3Library = async () => {
            if (window.d3) return true;
            if (!poaD3Promise) {
              poaD3Promise = (async () => {
                await loadScript("/static/vendor/d3.min.js");
                return !!window.d3;
              })().catch(() => false);
            }
            const ok = await poaD3Promise;
            return !!ok;
          };
          const showMsg = (text, isError = false) => {
            if (!msgEl) return;
            msgEl.textContent = text || "";
            msgEl.style.color = isError ? "#b91c1c" : "#0f3d2e";
          };
          const setAnnualCycleStatus = (text, isError = false) => {
            if (!annualCycleStatusEl) return;
            annualCycleStatusEl.textContent = text || "";
            annualCycleStatusEl.style.color = isError ? "#b91c1c" : "#475569";
          };
          const loadAnnualCycleContext = async () => {
            if (!annualCycleSelect) return;
            const response = await fetch("/api/annual-cycle/context", {
              headers: { "Content-Type": "application/json" },
              credentials: "same-origin",
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok || payload.success === false) {
              throw new Error(payload.error || "No se pudo cargar el ejercicio operativo.");
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
          };
          const startAnnualCycle = async () => {
            const suggestedYear = Number((annualCycleState && annualCycleState.next_year_suggestion) || new Date().getFullYear() + 1);
            const raw = window.prompt("¿Qué año quieres iniciar?", String(suggestedYear));
            if (!raw) return;
            const year = Number(String(raw).trim());
            if (!Number.isFinite(year) || year < 2000) {
              throw new Error("Debes capturar un año válido.");
            }
            setAnnualCycleStatus("Iniciando nuevo ejercicio...");
            const response = await fetch("/api/annual-cycle/start", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              credentials: "same-origin",
              body: JSON.stringify({ year }),
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok || payload.success === false) {
              throw new Error(payload.error || "No se pudo iniciar el nuevo ejercicio.");
            }
            window.location.reload();
          };
          const renderObjectiveKpis = (objective) => {
            if (!kpiListEl) return;
            const list = Array.isArray(objective?.kpis) ? objective.kpis : [];
            if (!list.length) {
              kpiListEl.innerHTML = '<div class="poa-sub-meta">Los indicadores oficiales se administran en Brújula.</div>';
              return;
            }
            kpiListEl.innerHTML = list.map((item) => {
              const nombre = escapeHtml(String(item?.nombre || "KPI sin nombre"));
              const referencia = escapeHtml(String(item?.referencia || ""));
              const formula = escapeHtml(String(item?.formula || ""));
              const periodicidad = escapeHtml(String(item?.periodicidad || ""));
              const estandar = escapeHtml(String(item?.estandar || ""));
              const meta = [periodicidad, estandar, referencia].filter(Boolean).join(" · ");
              return `
                <article class="poa-kpi-item">
                  <div class="poa-kpi-name">${nombre}</div>
                  ${formula ? `<div class="poa-kpi-meta">Fórmula: ${formula}</div>` : ""}
                  ${meta ? `<div class="poa-kpi-meta">${meta}</div>` : ""}
                </article>
              `;
            }).join("");
          };
          const loadAllCollaboratorNames = async () => {
            if (Array.isArray(allCollaboratorsCache)) return allCollaboratorsCache;
            const response = await fetch("/api/colaboradores", {
              headers: { "Content-Type": "application/json" },
              credentials: "same-origin",
            });
            const payload = await response.json().catch(() => ({}));
            const rows = Array.isArray(payload?.data) ? payload.data : [];
            allCollaboratorsCache = rows
              .map((item) => String(item?.nombre || "").trim())
              .filter(Boolean)
              .filter((name, index, arr) => arr.indexOf(name) === index)
              .sort((a, b) => a.localeCompare(b, "es"));
            return allCollaboratorsCache;
          };
          window.addEventListener("error", (event) => {
            const msg = String(event?.message || "Error JavaScript no controlado").trim();
            showMsg(`Error JS: ${msg}`, true);
          });
          window.addEventListener("unhandledrejection", (event) => {
            const reason = event?.reason;
            const msg = String(reason?.message || reason || "Promesa rechazada sin control").trim();
            showMsg(`Error JS: ${msg}`, true);
          });
          const syncOwnerChartState = () => {
            if (!ownerChartEl || !ownerChartToggleEl) return;
            const expanded = !ownerChartEl.classList.contains("collapsed");
            ownerChartToggleEl.setAttribute("aria-expanded", expanded ? "true" : "false");
            ownerChartToggleEl.setAttribute("aria-label", expanded ? "Contraer concentración por usuario" : "Mostrar concentración por usuario");
          };
          ownerChartToggleEl && ownerChartToggleEl.addEventListener("click", () => {
            if (!ownerChartEl) return;
            ownerChartEl.classList.toggle("collapsed");
            syncOwnerChartState();
          });
          syncOwnerChartState();
          const renderOwnerActivityChart = (activities) => {
            if (!ownerChartListEl || !ownerChartEmptyEl || !ownerChartTotalEl) return;
            const list = Array.isArray(activities) ? activities : [];
            const counts = {};
            let assignedTotal = 0;
            list.forEach((item) => {
              const owner = String(item?.responsable || "").trim();
              if (!owner) return;
              assignedTotal += 1;
              counts[owner] = (counts[owner] || 0) + 1;
            });
            ownerChartTotalEl.textContent = `Total asignadas: ${assignedTotal}`;
            const entries = Object.entries(counts)
              .sort((a, b) => {
                if (b[1] !== a[1]) return b[1] - a[1];
                return a[0].localeCompare(b[0], "es");
              });
            if (!entries.length || assignedTotal <= 0) {
              ownerChartListEl.innerHTML = "";
              ownerChartEmptyEl.style.display = "block";
              ownerChartEmptyEl.textContent = "Sin actividades con responsable.";
              return;
            }
            ownerChartEmptyEl.style.display = "none";
            const maxRows = 10;
            const topEntries = entries.slice(0, maxRows);
            const extraCount = entries.slice(maxRows).reduce((acc, item) => acc + Number(item[1] || 0), 0);
            const rows = topEntries.map(([name, amount]) => {
              const pct = assignedTotal > 0 ? (Number(amount || 0) / assignedTotal) * 100 : 0;
              return `
                <div class="poa-owner-row">
                  <div class="poa-owner-name" title="${escapeHtml(name)}">${escapeHtml(name)}</div>
                  <div class="poa-owner-bar">
                    <div class="poa-owner-fill" style="width:${pct.toFixed(1)}%"></div>
                  </div>
                  <div class="poa-owner-value">${Number(amount || 0)} (${pct.toFixed(1)}%)</div>
                </div>
              `;
            });
            if (extraCount > 0) {
              const pct = assignedTotal > 0 ? (extraCount / assignedTotal) * 100 : 0;
              rows.push(`
                <div class="poa-owner-row">
                  <div class="poa-owner-name" title="Otros usuarios">Otros usuarios</div>
                  <div class="poa-owner-bar">
                    <div class="poa-owner-fill" style="width:${pct.toFixed(1)}%"></div>
                  </div>
                  <div class="poa-owner-value">${extraCount} (${pct.toFixed(1)}%)</div>
                </div>
              `);
            }
            ownerChartListEl.innerHTML = rows.join("");
          };
          const showModalMsg = (text, isError = false) => {
            if (!actMsgEl) return;
            actMsgEl.textContent = text || "";
            actMsgEl.style.color = isError ? "#b91c1c" : "#0f3d2e";
          };
          const requestIaSuggestion = async (texto) => {
            const response = await fetch("/api/ia/suggest/objective-text", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              credentials: "same-origin",
              body: JSON.stringify({ texto: String(texto || "").trim() }),
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok || !payload || payload.error) {
              throw new Error(payload?.error || "No se pudo obtener sugerencia IA.");
            }
            return String(payload.sugerencia || "").trim();
          };
          const iaFeatureEnabled = async (moduleKey = "poa") => {
            try {
              const response = await fetch(`/api/ia/flags?module=${encodeURIComponent(moduleKey)}&feature_key=suggest_objective_text`, {
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
              });
              const payload = await response.json().catch(() => ({}));
              return !!(response.ok && payload?.success === true && payload?.data?.enabled);
            } catch (_err) {
              return false;
            }
          };
          const plainTextFromHtml = (value) => {
            const html = String(value || "").trim();
            if (!html) return "";
            const tmp = document.createElement("div");
            tmp.innerHTML = html;
            return String(tmp.textContent || tmp.innerText || "").trim();
          };
          const showActListMsg = (text, isError = false) => {
            if (!actListMsgEl) return;
            actListMsgEl.textContent = text || "";
            actListMsgEl.style.color = isError ? "#b91c1c" : "#64748b";
          };
          const setActivityEditorMode = (mode) => {
            activityEditorMode = mode === "edit" || mode === "new" ? mode : "list";
            if (!modalEl) return;
            const isList = activityEditorMode === "list";
            modalEl.classList.toggle("list-mode", isList);
            if (saveBtn) saveBtn.disabled = isList;
            if (saveTopBtn) saveTopBtn.disabled = isList;
            if (saveTopBtn) saveTopBtn.style.opacity = isList ? "0.55" : "1";
            if (saveTopBtn) saveTopBtn.style.cursor = isList ? "not-allowed" : "pointer";
            if (actListPanelEl) actListPanelEl.style.display = isList ? "block" : "none";
            if (formGridEl) formGridEl.style.display = isList ? "none" : "block";
            if (tabsWrapEl) tabsWrapEl.style.display = isList ? "none" : "flex";
            if (isList) {
              if (titleEl) titleEl.textContent = "Actividades del objetivo";
            } else if (titleEl) {
              titleEl.textContent = activityEditorMode === "edit" ? "Editar actividad" : "Nueva actividad";
            }
          };
          const showSubMsg = (text, isError = false) => {
            if (!subMsgEl) return;
            subMsgEl.textContent = text || "";
            subMsgEl.style.color = isError ? "#b91c1c" : "#0f3d2e";
          };
          const showBudgetMsg = (text, isError = false) => {
            if (!budgetMsgEl) return;
            budgetMsgEl.textContent = text || "";
            budgetMsgEl.style.color = isError ? "#b91c1c" : "#0f3d2e";
          };
          const canManageContent = () => !!poaPermissions?.can_manage_content;
          const applyPoaPermissionsUI = () => {
            const canManage = canManageContent();
            const canViewGantt = !!poaPermissions?.can_view_gantt;
            if (openGanttBtn) {
              const wrapper = openGanttBtn.closest(".view-pill") || openGanttBtn;
              wrapper.style.display = canViewGantt ? "" : "none";
            }
            if (!canViewGantt && ganttModalEl && ganttModalEl.classList.contains("open")) closeGanttModal();
            [newActBtn, editActBtn, deleteActBtn, saveBtn, saveTopBtn, subAddBtn, subSaveBtn, budgetAddBtn, budgetCancelBtn, delivAddBtn].forEach((btn) => {
              if (!btn) return;
              btn.disabled = !canManage;
              btn.style.opacity = canManage ? "1" : "0.55";
              btn.style.cursor = canManage ? "pointer" : "not-allowed";
            });
            if (actSuggestIaBtn) {
              const allowIa = canManage && poaIaEnabled;
              actSuggestIaBtn.disabled = !allowIa;
              actSuggestIaBtn.style.opacity = allowIa ? "1" : "0.55";
              actSuggestIaBtn.style.cursor = allowIa ? "pointer" : "not-allowed";
              if (!poaIaEnabled) actSuggestIaBtn.title = "IA deshabilitada para tu rol/módulo";
            }
            if (delivNameEl) delivNameEl.disabled = !canManage;
            if (importCsvBtn) {
              importCsvBtn.disabled = !canManage;
              importCsvBtn.style.opacity = canManage ? "1" : "0.55";
            }
          };
          const closeGanttModal = () => {
            if (!ganttModalEl) return;
            ganttModalEl.classList.remove("open");
            document.body.style.overflow = "";
          };
          const closeTreeModal = () => {
            if (!treeModalEl) return;
            treeModalEl.classList.remove("open");
            document.body.style.overflow = "";
          };
          const closeCalendarModal = () => {
            if (!calendarModalEl) return;
            calendarModalEl.classList.remove("open");
            document.body.style.overflow = "";
          };
          const treeKey = (kind, id) => `${kind}:${Number(id || 0)}`;
          const isTreeOpen = (kind, id) => !!poaTreeVisibility[treeKey(kind, id)];
          const setTreeOpen = (kind, id, value) => {
            poaTreeVisibility[treeKey(kind, id)] = !!value;
          };
          const getActivityById = (activityId) => (
            (Array.isArray(poaGanttActivities) ? poaGanttActivities : [])
              .find((item) => Number(item.id || 0) === Number(activityId)) || null
          );
          const poaStateTone = ({ status, entregaEstado, fechaInicial, fechaFinal, avance }) => {
            const st = String(status || "").trim().toLowerCase();
            const de = String(entregaEstado || "").trim().toLowerCase();
            const start = String(fechaInicial || "").trim();
            const end = String(fechaFinal || "").trim();
            const progress = Number(avance || 0);
            const today = todayIso();
            if (de === "pendiente" || st.includes("revisión") || st.includes("revision")) return "orange";
            if (de === "aprobada" || st.includes("terminad") || st.includes("hecho") || progress >= 100) return "green";
            if (st.includes("atras")) return "red";
            if (st.includes("no inici")) return "none";
            if (end && today > end && progress < 100) return "red";
            if (st.includes("proceso")) return "yellow";
            if (start && today >= start && progress < 100) return "yellow";
            return "none";
          };
          const aggregatePoaStateTone = (tones) => {
            const list = Array.isArray(tones) ? tones : [];
            if (!list.length) return "none";
            if (list.includes("red")) return "red";
            if (list.includes("orange")) return "orange";
            if (list.includes("yellow")) return "yellow";
            if (list.includes("green")) return "green";
            return "none";
          };
          const renderPoaAdvanceTree = () => {
            if (!treeHostEl) return;
            const objectives = Array.isArray(poaGanttObjectives) ? poaGanttObjectives : [];
            const activities = Array.isArray(poaGanttActivities) ? poaGanttActivities : [];
            if (!objectives.length) {
              treeHostEl.innerHTML = '<div class="poa-tree-axis"><p class="poa-tree-help">Sin datos para mostrar.</p></div>';
              return;
            }
            const grouped = {};
            objectives.forEach((obj) => {
              const axisName = String(obj.axis_name || "Sin eje").trim() || "Sin eje";
              if (!grouped[axisName]) grouped[axisName] = [];
              grouped[axisName].push(obj);
            });
            const axisNames = Object.keys(grouped).sort((a, b) => a.localeCompare(b, "es"));
            treeHostEl.innerHTML = axisNames.map((axisName) => {
              const axisIdKey = `axis:${axisName}`;
              const axisOpen = !!poaTreeVisibility[axisIdKey];
              const objCards = axisOpen ? (grouped[axisName] || []).map((obj) => {
                const objId = Number(obj.id || 0);
                const objOpen = isTreeOpen("obj", objId);
                const objActs = activities.filter((act) => Number(act.objective_id || 0) === objId);
                const objectiveTone = aggregatePoaStateTone(
                  objActs.map((act) => poaStateTone({
                    status: act?.status,
                    entregaEstado: act?.entrega_estado,
                    fechaInicial: act?.fecha_inicial,
                    fechaFinal: act?.fecha_final,
                    avance: act?.avance,
                  }))
                );
                const actHtml = objOpen ? objActs.map((act) => {
                  const actId = Number(act.id || 0);
                  const actOpen = isTreeOpen("act", actId);
                  const actTone = poaStateTone({
                    status: act?.status,
                    entregaEstado: act?.entrega_estado,
                    fechaInicial: act?.fecha_inicial,
                    fechaFinal: act?.fecha_final,
                    avance: act?.avance,
                  });
                  const subList = Array.isArray(act.subactivities) ? act.subactivities : [];
                  const subHtml = actOpen ? subList.map((sub) => `
                    <div class="poa-tree-item ${poaStateTone({
                      status: sub?.status,
                      entregaEstado: "",
                      fechaInicial: sub?.fecha_inicial,
                      fechaFinal: sub?.fecha_final,
                      avance: sub?.avance,
                    }) !== "none" ? "has-state" : ""}">
                      <div class="poa-tree-state poa-tree-state-${poaStateTone({
                        status: sub?.status,
                        entregaEstado: "",
                        fechaInicial: sub?.fecha_inicial,
                        fechaFinal: sub?.fecha_final,
                        avance: sub?.avance,
                      })}"></div>
                      <div class="poa-tree-item-head">
                        <h6 class="poa-tree-item-title poa-tree-click" data-tree-sub="${Number(sub.id || 0)}" data-tree-sub-parent="${actId}">${escapeHtml(sub.nombre || "Subtarea")}</h6>
                      </div>
                    </div>
                  `).join("") : "";
                  return `
                    <div class="poa-tree-item ${actTone !== "none" ? "has-state" : ""}">
                      <div class="poa-tree-state poa-tree-state-${actTone}"></div>
                      <div class="poa-tree-item-head">
                        <h6 class="poa-tree-item-title poa-tree-click" data-tree-activity="${actId}" data-tree-objective="${objId}">${escapeHtml(act.nombre || "Actividad")}</h6>
                        ${subList.length ? `<button type="button" class="poa-tree-toggle" data-tree-toggle="act" data-tree-id="${actId}">${actOpen ? "Ocultar" : "Mostrar"}</button>` : ""}
                      </div>
                      ${subList.length ? `<p class="poa-tree-item-meta">Subactividades: ${subList.length}</p>` : ""}
                      ${subHtml ? `<div class="poa-tree-children">${subHtml}</div>` : ""}
                    </div>
                  `;
                }).join("") : "";
                return `
                  <div class="poa-tree-item ${objectiveTone !== "none" ? "has-state" : ""}">
                    <div class="poa-tree-state poa-tree-state-${objectiveTone}"></div>
                    <div class="poa-tree-item-head">
                      <h5 class="poa-tree-item-title poa-tree-click" data-tree-objective="${objId}">${escapeHtml(obj.codigo || "xx-yy-zz")} - ${escapeHtml(obj.nombre || "Objetivo")}</h5>
                      ${objActs.length ? `<button type="button" class="poa-tree-toggle" data-tree-toggle="obj" data-tree-id="${objId}">${objOpen ? "Ocultar" : "Mostrar"}</button>` : ""}
                    </div>
                    <p class="poa-tree-item-meta">Actividades: ${objActs.length}</p>
                    ${actHtml ? `<div class="poa-tree-children">${actHtml}</div>` : ""}
                  </div>
                `;
              }).join("") : "";
              return `
                <section class="poa-tree-axis">
                  <div class="poa-tree-axis-head">
                    <h4>${escapeHtml(axisName)}</h4>
                    <button type="button" class="poa-tree-toggle" data-tree-toggle="axis" data-tree-axis="${escapeHtml(axisName)}">${axisOpen ? "Ocultar" : "Mostrar"}</button>
                  </div>
                  ${objCards ? `<div class="poa-tree-objectives">${objCards}</div>` : ""}
                </section>
              `;
            }).join("");
            treeHostEl.querySelectorAll("[data-tree-toggle='axis']").forEach((btn) => {
              btn.addEventListener("click", () => {
                const key = `axis:${String(btn.getAttribute("data-tree-axis") || "")}`;
                poaTreeVisibility[key] = !poaTreeVisibility[key];
                renderPoaAdvanceTree();
              });
            });
            treeHostEl.querySelectorAll("[data-tree-toggle='obj']").forEach((btn) => {
              btn.addEventListener("click", () => {
                setTreeOpen("obj", btn.getAttribute("data-tree-id"), !isTreeOpen("obj", btn.getAttribute("data-tree-id")));
                renderPoaAdvanceTree();
              });
            });
            treeHostEl.querySelectorAll("[data-tree-toggle='act']").forEach((btn) => {
              btn.addEventListener("click", () => {
                setTreeOpen("act", btn.getAttribute("data-tree-id"), !isTreeOpen("act", btn.getAttribute("data-tree-id")));
                renderPoaAdvanceTree();
              });
            });
            treeHostEl.querySelectorAll("[data-tree-objective]").forEach((node) => {
              node.addEventListener("click", async () => {
                const objectiveId = Number(node.getAttribute("data-tree-objective") || 0);
                if (objectiveId > 0) await openActivityForm(objectiveId);
              });
            });
            treeHostEl.querySelectorAll("[data-tree-activity]").forEach((node) => {
              node.addEventListener("click", async () => {
                const objectiveId = Number(node.getAttribute("data-tree-objective") || 0);
                const activityId = Number(node.getAttribute("data-tree-activity") || 0);
                if (objectiveId > 0) {
                  await openActivityForm(objectiveId, { activityId, focusSubId: 0 });
                }
              });
            });
            treeHostEl.querySelectorAll("[data-tree-sub]").forEach((node) => {
              node.addEventListener("click", async () => {
                const subId = Number(node.getAttribute("data-tree-sub") || 0);
                const parentActId = Number(node.getAttribute("data-tree-sub-parent") || 0);
                const act = getActivityById(parentActId);
                const objectiveId = Number(act?.objective_id || 0);
                if (objectiveId > 0) {
                  await openActivityForm(objectiveId, { activityId: parentActId, focusSubId: subId });
                }
              });
            });
          };
          const axisGanttKey = (objective) => String(objective?.axis_name || "Sin eje").trim() || "Sin eje";
          const syncPoaGanttVisibility = () => {
            const groupedKeys = new Set((Array.isArray(poaGanttObjectives) ? poaGanttObjectives : []).map((obj) => axisGanttKey(obj)));
            const next = {};
            Array.from(groupedKeys).forEach((key) => {
              next[key] = Object.prototype.hasOwnProperty.call(poaGanttVisibility, key) ? !!poaGanttVisibility[key] : true;
            });
            poaGanttVisibility = next;
          };
          const renderPoaGanttFilters = () => {
            if (!ganttBlocksEl) return;
            const list = Array.from(new Set((Array.isArray(poaGanttObjectives) ? poaGanttObjectives : []).map((obj) => axisGanttKey(obj)))).sort((a, b) => a.localeCompare(b, "es"));
            if (!list.length) {
              ganttBlocksEl.innerHTML = "";
              return;
            }
            syncPoaGanttVisibility();
            ganttBlocksEl.innerHTML = list.map((axisName) => {
              const checked = poaGanttVisibility[axisName] !== false ? "checked" : "";
              return `<label class="poa-gantt-block"><input type="checkbox" data-poa-gantt-axis="${escapeHtml(axisName)}" ${checked}><span>${escapeHtml(axisName)}</span></label>`;
            }).join("");
            ganttBlocksEl.querySelectorAll("input[data-poa-gantt-axis]").forEach((checkbox) => {
              checkbox.addEventListener("change", async () => {
                const key = String(checkbox.getAttribute("data-poa-gantt-axis") || "");
                if (!key) return;
                poaGanttVisibility[key] = !!checkbox.checked;
                await renderPoaGantt();
              });
            });
          };
          const renderPoaGantt = async () => {
            if (!ganttHostEl) return;
            const ok = await ensureD3Library();
            if (!ok) {
              ganttHostEl.innerHTML = '<p>No se pudo cargar la librería para Gantt.</p>';
              return;
            }
            renderPoaGanttFilters();
            syncPoaGanttVisibility();
            const objectives = Array.isArray(poaGanttObjectives) ? poaGanttObjectives : [];
            const activities = Array.isArray(poaGanttActivities) ? poaGanttActivities : [];
            const activitiesByObj = {};
            activities.forEach((item) => {
              const key = Number(item?.objective_id || 0);
              if (!key) return;
              if (!activitiesByObj[key]) activitiesByObj[key] = [];
              activitiesByObj[key].push(item);
            });
            const rows = [];
            objectives.forEach((obj) => {
              const axisKey = axisGanttKey(obj);
              if (poaGanttVisibility[axisKey] === false) return;
              const objStart = String(obj?.fecha_inicial || "");
              const objEnd = String(obj?.fecha_final || "");
              if (objStart && objEnd) {
                rows.push({
                  level: 0,
                  type: "objective",
                  label: `${obj.codigo || "xx-yy-zz"} · ${obj.nombre || "Objetivo"}`,
                  start: new Date(`${objStart}T00:00:00`),
                  end: new Date(`${objEnd}T00:00:00`),
                });
              }
              (activitiesByObj[Number(obj.id || 0)] || []).forEach((act) => {
                const start = String(act?.fecha_inicial || "");
                const end = String(act?.fecha_final || "");
                if (!start || !end) return;
                rows.push({
                  level: 1,
                  type: "activity",
                  label: `${act.codigo || "ACT"} · ${act.nombre || "Actividad"}`,
                  start: new Date(`${start}T00:00:00`),
                  end: new Date(`${end}T00:00:00`),
                });
              });
            });
            if (!rows.length) {
              ganttHostEl.innerHTML = '<p>No hay fechas suficientes en objetivos/actividades para generar Gantt.</p>';
              return;
            }
            const minDate = new Date(Math.min(...rows.map((item) => item.start.getTime())));
            const maxDate = new Date(Math.max(...rows.map((item) => item.end.getTime())));
            const margin = { top: 44, right: 24, bottom: 30, left: 430 };
            const rowH = 32;
            const chartW = Math.max(920, (ganttHostEl.clientWidth || 920) + 260);
            const width = margin.left + chartW + margin.right;
            const height = margin.top + (rows.length * rowH) + margin.bottom;
            ganttHostEl.innerHTML = "";
            const svg = window.d3.select(ganttHostEl).append("svg")
              .attr("width", width)
              .attr("height", height)
              .style("min-width", `${width}px`)
              .style("display", "block");
            const x = window.d3.scaleTime().domain([minDate, maxDate]).range([margin.left, margin.left + chartW]);
            const y = (idx) => margin.top + (idx * rowH);
            svg.append("g")
              .attr("transform", `translate(0, ${margin.top - 10})`)
              .call(window.d3.axisTop(x).ticks(window.d3.timeMonth.every(1)).tickSize(-rows.length * rowH).tickFormat(window.d3.timeFormat("%b %Y")))
              .call((g) => g.selectAll("text").attr("fill", "#475569").attr("font-size", 11))
              .call((g) => g.selectAll("line").attr("stroke", "rgba(148,163,184,.28)"))
              .call((g) => g.select(".domain").attr("stroke", "rgba(148,163,184,.35)"));
            rows.forEach((row, idx) => {
              const yy = y(idx);
              if (idx % 2 === 0) {
                svg.append("rect")
                  .attr("x", margin.left)
                  .attr("y", yy)
                  .attr("width", chartW)
                  .attr("height", rowH)
                  .attr("fill", "rgba(248,250,252,.70)");
              }
              svg.append("text")
                .attr("x", margin.left - 10 - (row.level ? 16 : 0))
                .attr("y", yy + (rowH / 2) + 4)
                .attr("text-anchor", "end")
                .attr("fill", row.level ? "#334155" : "#0f172a")
                .attr("font-size", row.level ? 12 : 12.5)
                .attr("font-style", row.level ? "italic" : "normal")
                .attr("font-weight", row.level ? 500 : 700)
                .text(row.label);
              const startX = x(row.start);
              const endX = x(row.end);
              const barW = Math.max(3, endX - startX);
              svg.append("rect")
                .attr("x", startX)
                .attr("y", yy + 7)
                .attr("width", barW)
                .attr("height", rowH - 14)
                .attr("rx", 6)
                .attr("fill", row.type === "objective" ? "#0f3d2e" : "#2563eb")
                .attr("opacity", row.type === "objective" ? 0.92 : 0.86);
            });
            const today = new Date();
            if (today >= minDate && today <= maxDate) {
              const xx = x(today);
              svg.append("line")
                .attr("x1", xx).attr("x2", xx)
                .attr("y1", margin.top - 12).attr("y2", height - margin.bottom + 4)
                .attr("stroke", "#ef4444")
                .attr("stroke-width", 1.6)
                .attr("stroke-dasharray", "4,4");
            }
          };
          const toIsoDate = (date) => {
            const y = date.getFullYear();
            const m = String(date.getMonth() + 1).padStart(2, "0");
            const d = String(date.getDate()).padStart(2, "0");
            return `${y}-${m}-${d}`;
          };
          const shiftCalendarMonth = (delta) => {
            poaCalendarCursor = new Date(poaCalendarCursor.getFullYear(), poaCalendarCursor.getMonth() + Number(delta || 0), 1);
          };
          const buildCalendarEvents = () => {
            const objectives = Array.isArray(poaGanttObjectives) ? poaGanttObjectives : [];
            const activities = Array.isArray(poaGanttActivities) ? poaGanttActivities : [];
            const out = [];
            objectives.forEach((obj) => {
              const start = String(obj?.fecha_inicial || "");
              const end = String(obj?.fecha_final || "");
              if (!start || !end) return;
              out.push({
                type: "objective",
                objectiveId: Number(obj.id || 0),
                label: `${obj.codigo || "OBJ"} · ${obj.nombre || "Objetivo"}`,
                start,
                end,
              });
            });
            activities.forEach((act) => {
              const start = String(act?.fecha_inicial || "");
              const end = String(act?.fecha_final || "");
              if (!start || !end) return;
              out.push({
                type: "activity",
                objectiveId: Number(act.objective_id || 0),
                activityId: Number(act.id || 0),
                label: `${act.codigo || "ACT"} · ${act.nombre || "Actividad"}`,
                start,
                end,
              });
            });
            return out;
          };
          const renderPoaCalendar = () => {
            if (!calendarGridEl || !calendarMonthEl) return;
            const monthStart = new Date(poaCalendarCursor.getFullYear(), poaCalendarCursor.getMonth(), 1);
            const monthEnd = new Date(poaCalendarCursor.getFullYear(), poaCalendarCursor.getMonth() + 1, 0);
            const startWeekday = (monthStart.getDay() + 6) % 7;
            const gridStart = new Date(monthStart);
            gridStart.setDate(monthStart.getDate() - startWeekday);
            calendarMonthEl.textContent = monthStart.toLocaleDateString("es-CR", { month: "long", year: "numeric" });
            const events = buildCalendarEvents();
            const dows = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"];
            let html = dows.map((dow) => `<div class="poa-cal-dow">${dow}</div>`).join("");
            for (let i = 0; i < 42; i += 1) {
              const day = new Date(gridStart);
              day.setDate(gridStart.getDate() + i);
              const dayIso = toIsoDate(day);
              const inMonth = day >= monthStart && day <= monthEnd;
              const dayEvents = events.filter((item) => item.start <= dayIso && item.end >= dayIso);
              const visible = dayEvents.slice(0, 2);
              const extra = dayEvents.length - visible.length;
              html += `
                <div class="poa-cal-cell ${inMonth ? "" : "muted"}" data-cal-day="${dayIso}">
                  <div class="poa-cal-day">${day.getDate()}</div>
                  <div class="poa-cal-events">
                    ${visible.map((event, idx) => `<button type="button" class="poa-cal-event ${event.type}" data-cal-event-day="${dayIso}" data-cal-event-idx="${idx}" title="${escapeHtml(event.label)}">${escapeHtml(event.label)}</button>`).join("")}
                    ${extra > 0 ? `<div class="poa-cal-more">+${extra} más</div>` : ""}
                  </div>
                </div>
              `;
            }
            calendarGridEl.innerHTML = html;
            calendarGridEl.querySelectorAll("[data-cal-event-day]").forEach((node) => {
              node.addEventListener("click", async () => {
                const dayIso = String(node.getAttribute("data-cal-event-day") || "");
                const idx = Number(node.getAttribute("data-cal-event-idx") || -1);
                const dayEvents = events.filter((item) => item.start <= dayIso && item.end >= dayIso);
                const event = dayEvents[idx];
                if (!event) return;
                closeCalendarModal();
                if (event.type === "activity" && event.objectiveId && event.activityId) {
                  await openActivityForm(event.objectiveId, { activityId: event.activityId });
                } else if (event.objectiveId) {
                  await openActivityForm(event.objectiveId);
                }
              });
            });
          };
          const showDeliverableMsg = (text, isError = false) => {
            if (!delivMsgEl) return;
            delivMsgEl.textContent = text || "";
            delivMsgEl.style.color = isError ? "#b91c1c" : "#0f3d2e";
          };
          const normalizeDeliverables = (rows) => {
            const list = Array.isArray(rows) ? rows : [];
            return list
              .map((item, idx) => ({
                id: Number(item?.id || 0),
                nombre: String(item?.nombre || "").trim(),
                validado: !!item?.validado,
                orden: Number(item?.orden || (idx + 1)),
              }))
              .filter((item) => item.nombre);
          };
          const renderDeliverables = () => {
            if (!delivListEl) return;
            const canManage = canManageContent();
            const list = normalizeDeliverables(currentDeliverables);
            currentDeliverables = list;
            if (!list.length) {
              delivListEl.innerHTML = '<div class="poa-sub-meta">Sin entregables registrados.</div>';
              return;
            }
            delivListEl.innerHTML = list.map((item, idx) => `
              <div class="poa-deliv-item">
                <label>
                  <input type="checkbox" data-deliv-check="${idx}" ${item.validado ? "checked" : ""} ${(canValidateDeliverables && canManage) ? "" : "disabled"}>
                  <span>${escapeHtml(item.nombre)}</span>
                </label>
                ${canManage ? `<button type="button" class="poa-sub-btn warn" data-deliv-delete="${idx}">Eliminar</button>` : ""}
              </div>
            `).join("");
            delivListEl.querySelectorAll("[data-deliv-check]").forEach((node) => {
              node.addEventListener("change", () => {
                const idx = Number(node.getAttribute("data-deliv-check") || -1);
                if (idx < 0 || idx >= currentDeliverables.length) return;
                if (!canValidateDeliverables) {
                  node.checked = !!currentDeliverables[idx]?.validado;
                  showDeliverableMsg("Solo el líder del objetivo puede validar entregables.", true);
                  return;
                }
                currentDeliverables[idx].validado = !!node.checked;
                showDeliverableMsg("Validación actualizada. Guarda la actividad para persistir.");
              });
            });
            delivListEl.querySelectorAll("[data-deliv-delete]").forEach((node) => {
              node.addEventListener("click", () => {
                const idx = Number(node.getAttribute("data-deliv-delete") || -1);
                if (idx < 0 || idx >= currentDeliverables.length) return;
                currentDeliverables.splice(idx, 1);
                renderDeliverables();
                showDeliverableMsg("Entregable eliminado.");
              });
            });
          };
          const addDeliverable = () => {
            if (!canManageContent()) {
              showDeliverableMsg("Solo administrador puede modificar entregables.", true);
              return;
            }
            const nombre = (delivNameEl && delivNameEl.value ? delivNameEl.value : "").trim();
            if (!nombre) {
              showDeliverableMsg("Escribe el nombre del entregable.", true);
              return;
            }
            currentDeliverables.push({
              id: 0,
              nombre,
              validado: false,
              orden: currentDeliverables.length + 1,
            });
            if (delivNameEl) delivNameEl.value = "";
            renderDeliverables();
            showDeliverableMsg("Entregable agregado. Guarda la actividad para persistir.");
          };
          const toMoney = (value) => {
            const num = Number(value || 0);
            if (!Number.isFinite(num) || num < 0) return 0;
            return Math.round(num * 100) / 100;
          };
          const formatMoney = (value) => toMoney(value).toLocaleString("es-CR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
          const normalizeBudgetItems = (rows) => {
            const list = Array.isArray(rows) ? rows : [];
            return list
              .map((item) => ({
                tipo: String(item?.tipo || "").trim(),
                rubro: String(item?.rubro || "").trim(),
                mensual: toMoney(item?.mensual),
                anual: toMoney(item?.anual),
                autorizado: !!item?.autorizado,
              }))
              .filter((item) => item.tipo && item.rubro);
          };
          const clearBudgetForm = () => {
            if (budgetTypeEl) budgetTypeEl.value = "";
            if (budgetRubroEl) budgetRubroEl.value = "";
            if (budgetMonthlyEl) budgetMonthlyEl.value = "";
            if (budgetAnnualEl) budgetAnnualEl.value = "";
            if (budgetApprovedEl) budgetApprovedEl.checked = false;
            editingBudgetIndex = -1;
            if (budgetAddBtn) budgetAddBtn.textContent = "Agregar rubro";
            showBudgetMsg("");
          };
          const renderBudgetItems = () => {
            if (!budgetListEl) return;
            const canManage = canManageContent();
            const list = normalizeBudgetItems(currentBudgetItems);
            currentBudgetItems = list;
            const monthlyTotal = list.reduce((sum, item) => sum + toMoney(item.mensual), 0);
            const annualTotal = list.reduce((sum, item) => sum + toMoney(item.anual), 0);
            if (budgetMonthlyTotalEl) budgetMonthlyTotalEl.textContent = formatMoney(monthlyTotal);
            if (budgetAnnualTotalEl) budgetAnnualTotalEl.textContent = formatMoney(annualTotal);
            if (!list.length) {
              budgetListEl.innerHTML = '<tr><td colspan="6">Sin rubros registrados.</td></tr>';
              return;
            }
            budgetListEl.innerHTML = list.map((item, idx) => `
              <tr>
                <td>${escapeHtml(item.tipo)}</td>
                <td>${escapeHtml(item.rubro)}</td>
                <td class="num">${escapeHtml(formatMoney(item.mensual))}</td>
                <td class="num">${escapeHtml(formatMoney(item.anual))}</td>
                <td>${item.autorizado ? "Sí" : "No"}</td>
                <td>
                  ${canManage ? `<button type="button" class="poa-sub-btn" data-budget-edit="${idx}">Editar</button>` : ""}
                  ${canManage ? `<button type="button" class="poa-sub-btn warn" data-budget-delete="${idx}">Eliminar</button>` : ""}
                </td>
              </tr>
            `).join("");
            budgetListEl.querySelectorAll("[data-budget-edit]").forEach((btn) => {
              btn.addEventListener("click", () => {
                const idx = Number(btn.getAttribute("data-budget-edit") || -1);
                const row = currentBudgetItems[idx];
                if (!row) return;
                if (budgetTypeEl) budgetTypeEl.value = row.tipo || "";
                if (budgetRubroEl) budgetRubroEl.value = row.rubro || "";
                if (budgetMonthlyEl) budgetMonthlyEl.value = toMoney(row.mensual) ? String(toMoney(row.mensual)) : "";
                if (budgetAnnualEl) budgetAnnualEl.value = toMoney(row.anual) ? String(toMoney(row.anual)) : "";
                if (budgetApprovedEl) budgetApprovedEl.checked = !!row.autorizado;
                editingBudgetIndex = idx;
                if (budgetAddBtn) budgetAddBtn.textContent = "Actualizar rubro";
                showBudgetMsg("Editando rubro de presupuesto.");
                activatePoaTab("budget");
              });
            });
            budgetListEl.querySelectorAll("[data-budget-delete]").forEach((btn) => {
              btn.addEventListener("click", () => {
                const idx = Number(btn.getAttribute("data-budget-delete") || -1);
                if (idx < 0 || idx >= currentBudgetItems.length) return;
                currentBudgetItems.splice(idx, 1);
                renderBudgetItems();
                showBudgetMsg("Rubro eliminado.");
              });
            });
          };
          const addOrUpdateBudgetItem = () => {
            if (!canManageContent()) {
              showBudgetMsg("Solo administrador puede modificar presupuesto.", true);
              return;
            }
            const tipo = (budgetTypeEl && budgetTypeEl.value ? budgetTypeEl.value : "").trim();
            const rubro = (budgetRubroEl && budgetRubroEl.value ? budgetRubroEl.value : "").trim();
            const mensual = toMoney(budgetMonthlyEl && budgetMonthlyEl.value ? budgetMonthlyEl.value : 0);
            let anual = toMoney(budgetAnnualEl && budgetAnnualEl.value ? budgetAnnualEl.value : 0);
            if (!tipo || !rubro) {
              showBudgetMsg("Tipo y rubro son obligatorios.", true);
              return;
            }
            if (!anual && mensual) anual = toMoney(mensual * 12);
            const row = { tipo, rubro, mensual, anual, autorizado: !!(budgetApprovedEl && budgetApprovedEl.checked) };
            if (editingBudgetIndex >= 0 && editingBudgetIndex < currentBudgetItems.length) {
              currentBudgetItems[editingBudgetIndex] = row;
            } else {
              currentBudgetItems.push(row);
            }
            clearBudgetForm();
            renderBudgetItems();
            showBudgetMsg("Rubro listo. Guarda la actividad para persistir.");
          };
          const syncBudgetAnnual = () => {
            if (!budgetMonthlyEl || !budgetAnnualEl) return;
            const mensual = toMoney(budgetMonthlyEl.value || 0);
            const anualRaw = String(budgetAnnualEl.value || "").trim();
            if (anualRaw) return;
            if (!mensual) return;
            budgetAnnualEl.value = String(toMoney(mensual * 12));
          };
          const openModal = () => {
            if (!modalEl) return;
            modalEl.classList.add("open");
            document.body.style.overflow = "hidden";
          };
          const closeModal = () => {
            if (!modalEl) return;
            modalEl.classList.remove("open");
            document.body.style.overflow = "";
          };
          const openSubModal = () => {
            if (!subModalEl) return;
            subModalEl.classList.add("open");
            document.body.style.overflow = "hidden";
          };
          const closeSubModal = () => {
            if (!subModalEl) return;
            subModalEl.classList.remove("open");
            document.body.style.overflow = modalEl && modalEl.classList.contains("open") ? "hidden" : "";
          };
          const nextCode = (objectiveCode, objectiveId = 0) => {
            const code = String(objectiveCode || "").trim().toLowerCase();
            const targetObjectiveId = Number(objectiveId || 0);
            const currentActivities = targetObjectiveId ? (activitiesByObjective[targetObjectiveId] || []) : [];
            const nextOrder = currentActivities.length + 1;
            if (!code) return `obj-00-00-${String(nextOrder).padStart(2, "0")}`;
            return `${code}-${String(nextOrder).padStart(2, "0")}`;
          };
          const buildBranchText = (activityName = "Actividad", slots = {}) => {
            const axisLabel = String(currentObjective?.axis_name || "Eje estratégico").trim() || "Eje estratégico";
            const objectiveLabel = String(currentObjective?.nombre || "Objetivo").trim() || "Objetivo";
            const activityLabel = String(activityName || "Actividad").trim() || "Actividad";
            const tarea = String(slots.tarea || "Tarea").trim() || "Tarea";
            const subtarea = String(slots.subtarea || "Subtarea").trim() || "Subtarea";
            const subsub = String(slots.subsubtarea || "Subsubtarea").trim() || "Subsubtarea";
            return `Ruta: ${axisLabel} / ${objectiveLabel} / ${activityLabel} / ${tarea} / ${subtarea} / ${subsub}`;
          };
          const renderActivityBranch = () => {
            if (!activityBranchEl) return;
            activityBranchEl.textContent = buildBranchText(actNameEl && actNameEl.value ? actNameEl.value : "Actividad");
          };
          const resolveSubBranchSlots = (targetLevel, targetName, parentId) => {
            const byId = {};
            (currentSubactivities || []).forEach((item) => {
              byId[Number(item.id || 0)] = item;
            });
            let tarea = "Tarea";
            let subtarea = "Subtarea";
            let subsubtarea = "Subsubtarea";
            let walker = Number(parentId || 0);
            while (walker) {
              const node = byId[walker];
              if (!node) break;
              const level = Number(node.nivel || 1);
              const name = String(node.nombre || "").trim();
              if (level === 1 && name) tarea = name;
              if (level === 2 && name) subtarea = name;
              if (level === 3 && name) subsubtarea = name;
              walker = Number(node.parent_subactivity_id || 0);
            }
            const cleanTarget = String(targetName || "").trim();
            if (targetLevel === 1 && cleanTarget) tarea = cleanTarget;
            if (targetLevel === 2 && cleanTarget) subtarea = cleanTarget;
            if (targetLevel === 3 && cleanTarget) subsubtarea = cleanTarget;
            return { tarea, subtarea, subsubtarea };
          };
          const renderSubBranch = (targetLevel = 1, targetName = "", parentId = 0) => {
            if (!subBranchEl) return;
            const slots = resolveSubBranchSlots(targetLevel, targetName, parentId);
            const actName = actNameEl && actNameEl.value ? actNameEl.value : "Actividad";
            subBranchEl.textContent = buildBranchText(actName, slots);
          };
          const setDateBounds = (objective) => {
            const minDate = String(objective?.fecha_inicial || "");
            const maxDate = String(objective?.fecha_final || "");
            [actStartEl, actEndEl].forEach((el) => {
              if (!el) return;
              el.min = minDate || "";
              el.max = maxDate || "";
            });
          };
          const fillCollaborators = async (objective) => {
            if (!actOwnerEl || !actAssignedEl) return;
            try {
              const list = await loadAllCollaboratorNames();
              actOwnerEl.innerHTML = '<option value="">Selecciona responsable</option>' + list.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join("");
              actAssignedEl.innerHTML = list.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join("");
            } catch (_err) {
              actOwnerEl.innerHTML = '<option value="">Selecciona responsable</option>';
              actAssignedEl.innerHTML = "";
            }
          };
          const renderImpactedMilestonesOptions = (objective, selectedIds = []) => {
            if (!actImpactHitosEl) return;
            const selectedSet = new Set((Array.isArray(selectedIds) ? selectedIds : [])
              .map((value) => Number(value || 0))
              .filter((value) => value > 0));
            const hitos = Array.isArray(objective?.hitos) ? objective.hitos : [];
            if (!hitos.length) {
              actImpactHitosEl.disabled = true;
              actImpactHitosEl.innerHTML = '<option value="" disabled>Sin hitos registrados en este objetivo</option>';
              return;
            }
            actImpactHitosEl.disabled = false;
            const validIds = new Set(hitos.map((hito) => Number(hito?.id || 0)).filter((value) => value > 0));
            actImpactHitosEl.innerHTML = hitos.map((hito) => {
              const id = Number(hito?.id || 0);
              if (!id) return "";
              const selected = selectedSet.has(id) && validIds.has(id) ? "selected" : "";
              const label = String(hito?.nombre || "Hito").trim() || "Hito";
              return `<option value="${id}" ${selected}>${escapeHtml(label)}</option>`;
            }).join("");
          };
          const currentApprovalForActivity = () => {
            if (!currentActivityId) return null;
            return approvalsByActivity[Number(currentActivityId)] || null;
          };
          const renderStateStrip = () => {
            const rawStatus = String(currentActivityData?.status || "").trim().toLowerCase();
            const endDate = String(currentActivityData?.fecha_final || "").trim();
            const displayStatus = (() => {
              if (rawStatus === "terminada") return "Terminada";
              if (rawStatus === "en revisión") return "En revisión";
              if (rawStatus === "atrasada") return "Atrasada";
              if (endDate && todayIso() > endDate) return "Atrasada";
              if (rawStatus === "en proceso") return "En proceso";
              return "No iniciado";
            })();
            [stateNoIniciadoBtn, stateEnProcesoBtn, stateTerminadoBtn, stateEnRevisionBtn].forEach((btn) => {
              if (btn) btn.classList.remove("active");
            });
            if (displayStatus === "No iniciado" && stateNoIniciadoBtn) stateNoIniciadoBtn.classList.add("active");
            if (displayStatus === "En proceso" && stateEnProcesoBtn) stateEnProcesoBtn.classList.add("active");
            if (displayStatus === "Terminada" && stateTerminadoBtn) stateTerminadoBtn.classList.add("active");
            if (displayStatus === "En revisión" && stateEnRevisionBtn) stateEnRevisionBtn.classList.add("active");
            const canChangeStatus = !!(currentActivityData && currentActivityData.can_change_status);
            if (stateEnProcesoBtn) stateEnProcesoBtn.disabled = !currentActivityId || !canChangeStatus;
            if (stateTerminadoBtn) stateTerminadoBtn.disabled = !currentActivityId || !canChangeStatus;
            if (statusValueEl) {
              const tone = displayStatus === "Terminada" ? "green"
                : displayStatus === "En revisión" ? "orange"
                  : displayStatus === "En proceso" ? "yellow"
                    : displayStatus === "Atrasada" ? "red"
                      : "gray";
              statusValueEl.innerHTML = `<span class="poa-semaforo ${tone}"></span>${escapeHtml(displayStatus)}`;
            }
            const subList = Array.isArray(currentSubactivities) ? currentSubactivities : [];
            let progress = 0;
            if (subList.length) {
              const completed = subList.filter((sub) => {
                const subEnd = String(sub?.fecha_final || "").trim();
                return !!subEnd && subEnd <= todayIso();
              }).length;
              progress = Math.round((completed / subList.length) * 100);
            } else {
              progress = displayStatus === "Terminada" ? 100 : 0;
            }
            if (progressValueEl) progressValueEl.textContent = `${progress}%`;
            const approval = currentApprovalForActivity();
            const canReview = !!approval;
            if (approveBtn) approveBtn.style.display = canReview ? "inline-flex" : "none";
            if (rejectBtn) rejectBtn.style.display = canReview ? "inline-flex" : "none";
          };
          const resetActivityForm = () => {
            if (actNameEl) actNameEl.value = "";
            if (actStartEl) actStartEl.value = "";
            if (actEndEl) actEndEl.value = "";
            if (actRecurrenteEl) actRecurrenteEl.checked = false;
            if (actPeriodicidadEl) actPeriodicidadEl.value = "";
            if (actEveryDaysEl) actEveryDaysEl.value = "";
            if (actDescRich) {
              actDescRich.setHtml("");
            } else if (actDescEl) {
              actDescEl.value = "";
            }
            if (actOwnerEl) actOwnerEl.value = "";
            if (actAssignedEl) Array.from(actAssignedEl.options || []).forEach((opt) => { opt.selected = false; });
            if (actImpactHitosEl) actImpactHitosEl.innerHTML = "";
            currentActivityId = null;
            currentActivityData = null;
            currentSubactivities = [];
            currentBudgetItems = [];
            currentDeliverables = [];
            renderObjectiveKpis(currentObjective);
            selectedListActivityId = null;
            editingSubId = null;
            editingBudgetIndex = -1;
            currentParentSubId = 0;
            syncRecurringFields();
            renderStateStrip();
            clearBudgetForm();
            renderBudgetItems();
            renderDeliverables();
            showDeliverableMsg("");
          };
          const getCurrentObjectiveActivities = () => {
            if (!currentObjective) return [];
            return activitiesByObjective[Number(currentObjective.id || 0)] || [];
          };
          const renderActivityList = () => {
            if (!actListEl) return;
            const canManage = canManageContent();
            const list = getCurrentObjectiveActivities();
            const hasSelection = !!Number(selectedListActivityId || 0);
            if (editActBtn) editActBtn.disabled = !canManage || !hasSelection;
            if (deleteActBtn) deleteActBtn.disabled = !canManage || !hasSelection;
            if (!list.length) {
              actListEl.innerHTML = '<div class="poa-sub-meta">Sin actividades registradas.</div>';
              if (editActBtn) editActBtn.disabled = true;
              if (deleteActBtn) deleteActBtn.disabled = true;
              showActListMsg(canManage ? "Usa 'Nuevo' para crear la primera actividad." : "No hay actividades registradas.");
              return;
            }
            actListEl.innerHTML = list.map((item) => {
              const id = Number(item.id || 0);
              const active = id === Number(selectedListActivityId || 0) ? "active" : "";
              const rawOwner = String(item.responsable || "").trim();
              const noOwner = !rawOwner;
              const ownerText = escapeHtml(rawOwner || "Sin responsable");
              return `
                <article class="poa-act-item ${active}${noOwner ? ' poa-act-no-owner' : ''}" data-poa-activity-id="${id}">
                  <div><strong>${escapeHtml(item.nombre || "Actividad sin nombre")}</strong></div>
                  <div class="meta">${escapeHtml(item.codigo || "sin código")} · <span class="${noOwner ? 'poa-no-owner-text' : ''}">${ownerText}</span></div>
                </article>
              `;
            }).join("");
            actListEl.querySelectorAll("[data-poa-activity-id]").forEach((node) => {
              node.style.cursor = "pointer";
              node.addEventListener("click", async () => {
                const activityId = Number(node.getAttribute("data-poa-activity-id") || 0);
                selectedListActivityId = activityId;
                renderActivityList();
                if (!currentObjective || !activityId) {
                  showActListMsg("No se pudo abrir la actividad seleccionada.", true);
                  return;
                }
                await openActivityForm(Number(currentObjective.id || 0), { activityId });
                activatePoaTab("sub");
                showActListMsg("Mostrando subtareas de la actividad seleccionada.");
              });
            });
            if (!selectedListActivityId) {
              showActListMsg(canManage ? "Selecciona una actividad para abrir sus subtareas o usa 'Nuevo'." : "Selecciona una actividad para abrir sus subtareas.");
            }
          };
          const loadSelectedActivityInForm = () => {
            if (!canManageContent()) return;
            const list = getCurrentObjectiveActivities();
            const selected = list.find((item) => Number(item.id || 0) === Number(selectedListActivityId || 0)) || null;
            if (!selected) {
              showActListMsg("Selecciona una actividad para editar.", true);
              return;
            }
            populateActivityForm(selected);
            setActivityEditorMode("edit");
            showActListMsg("Actividad cargada en formulario.");
            if (actNameEl) actNameEl.focus();
          };
          const startNewActivity = () => {
            if (!canManageContent()) return;
            selectedListActivityId = null;
            const objective = currentObjective;
            resetActivityForm();
            if (objective) {
              currentObjective = objective;
              canValidateDeliverables = !!objective.can_validate_deliverables;
              renderObjectiveKpis(objective);
              renderImpactedMilestonesOptions(objective, []);
              setDateBounds(objective);
            }
            renderActivityBranch();
            renderSubtasks();
            renderActivityList();
            setActivityEditorMode("new");
            showActListMsg("Nueva actividad lista para captura.");
            if (assignedByEl) assignedByEl.textContent = `Asignado por: ${objective?.lider || "N/D"}`;
            if (actNameEl) actNameEl.focus();
          };
          const deleteSelectedActivity = async () => {
            if (!canManageContent()) return;
            const id = Number(selectedListActivityId || 0);
            if (!id) {
              showActListMsg("Selecciona una actividad para eliminar.", true);
              return;
            }
            if (!window.confirm("¿Eliminar esta actividad?")) return;
            showActListMsg("Eliminando actividad...");
            try {
              const response = await fetch(`/api/poa/activities/${id}`, {
                method: "DELETE",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
              });
              const data = await response.json().catch(() => ({}));
              if (!response.ok || data.success === false) {
                throw new Error(data.error || "No se pudo eliminar la actividad.");
              }
              await loadBoard();
              if (currentObjective) {
                selectedListActivityId = null;
                startNewActivity();
              }
              showActListMsg("Actividad eliminada.");
            } catch (error) {
              showActListMsg(error.message || "No se pudo eliminar la actividad.", true);
            }
          };
          const populateActivityForm = (activity) => {
            if (!activity) return;
            if (actNameEl) actNameEl.value = activity.nombre || "";
            if (actOwnerEl) actOwnerEl.value = activity.responsable || "";
            if (actStartEl) actStartEl.value = activity.fecha_inicial || "";
            if (actEndEl) actEndEl.value = activity.fecha_final || "";
            if (actDescRich) {
              actDescRich.setHtml(activity.descripcion || "");
            } else if (actDescEl) {
              actDescEl.value = activity.descripcion || "";
            }
            if (actRecurrenteEl) actRecurrenteEl.checked = !!activity.recurrente;
            if (actPeriodicidadEl) actPeriodicidadEl.value = activity.periodicidad || "";
            if (actEveryDaysEl) actEveryDaysEl.value = activity.cada_xx_dias || "";
            currentActivityId = Number(activity.id || 0);
            selectedListActivityId = Number(activity.id || 0);
            currentActivityData = activity;
            currentSubactivities = Array.isArray(activity.subactivities) ? activity.subactivities : [];
            currentBudgetItems = normalizeBudgetItems(activity.budget_items || []);
            currentDeliverables = normalizeDeliverables(activity.entregables || []);
            renderObjectiveKpis(currentObjective);
            if (!currentDeliverables.length && String(activity.entregable || "").trim()) {
              currentDeliverables = [{ id: 0, nombre: String(activity.entregable || "").trim(), validado: false, orden: 1 }];
            }
            renderImpactedMilestonesOptions(currentObjective, (activity.hitos_impacta || []).map((item) => Number(item?.id || 0)));
            syncRecurringFields();
            renderSubtasks();
            renderStateStrip();
            renderActivityBranch();
            clearBudgetForm();
            renderBudgetItems();
            renderDeliverables();
            renderActivityList();
          };
          const activatePoaTab = (tabKey) => {
            document.querySelectorAll("[data-poa-tab]").forEach((btn) => { btn.classList.remove("active"); btn.classList.remove("tab-active"); });
            document.querySelectorAll("[data-poa-panel]").forEach((panel) => panel.classList.remove("active"));
            const tabBtn = document.querySelector(`[data-poa-tab="${tabKey}"]`);
            const panel = document.querySelector(`[data-poa-panel="${tabKey}"]`);
            if (tabBtn) { tabBtn.classList.add("active"); tabBtn.classList.add("tab-active"); }
            if (panel) panel.classList.add("active");
          };
          const openActivityForm = async (objectiveId, options = {}) => {
            let objective = options.objectiveData || objectivesById[Number(objectiveId)];
            if (!objective) {
              showMsg("Recargando datos POA para abrir el objetivo...");
              await loadBoard();
              objective = objectivesById[Number(objectiveId)];
            }
            if (!objective) {
              showMsg("No se encontró el objetivo seleccionado en el tablero POA.", true);
              return;
            }
            currentObjective = objective;
            canValidateDeliverables = !!objective.can_validate_deliverables;
            renderObjectiveKpis(objective);
            const targetActivityId = Number(options.activityId || 0);
            const shouldLoadExisting = !!(targetActivityId || options.focusSubId);
            const currentList = activitiesByObjective[Number(objective.id || 0)] || [];
            const existing = targetActivityId
              ? (currentList.find((item) => Number(item.id || 0) === targetActivityId) || null)
              : ((currentList[0]) || null);
            if (titleEl) titleEl.textContent = (shouldLoadExisting && existing) ? "Editar actividad" : "Nueva actividad";
            if (subtitleEl) subtitleEl.textContent = `${objective.codigo || ""} · ${objective.nombre || "Objetivo"}`;
            if (assignedByEl) assignedByEl.textContent = `Asignado por: ${(shouldLoadExisting ? existing?.created_by : "") || objective.lider || "N/D"}`;
            resetActivityForm();
            showModalMsg("");
            setDateBounds(objective);
            await fillCollaborators(objective);
            renderImpactedMilestonesOptions(objective, []);
            if (existing) {
              if (shouldLoadExisting) {
                selectedListActivityId = Number(existing.id || 0);
                populateActivityForm(existing);
                setActivityEditorMode("edit");
              } else {
                selectedListActivityId = Number(currentList[0]?.id || 0) || null;
                renderActivityList();
                setActivityEditorMode("list");
                showActListMsg("Selecciona una actividad y pulsa 'Editar' o crea una con 'Nuevo'.");
              }
              if (options.focusSubId && selectedListActivityId) {
                activatePoaTab("sub");
                const subId = Number(options.focusSubId || 0);
                if (subId) {
                  await openSubtaskForm(subId, 0);
                }
              }
            } else {
              renderActivityList();
              setActivityEditorMode("list");
              showActListMsg("Este objetivo no tiene actividades. Pulsa 'Nuevo' para crear la primera.");
            }
            renderActivityList();
            openModal();
          };
          const orderSubtasks = (items) => {
            const childrenByParent = {};
            (items || []).forEach((item) => {
              const parent = Number(item.parent_subactivity_id || 0);
              if (!childrenByParent[parent]) childrenByParent[parent] = [];
              childrenByParent[parent].push(item);
            });
            Object.keys(childrenByParent).forEach((key) => {
              childrenByParent[key].sort((a, b) => Number(a.id || 0) - Number(b.id || 0));
            });
            const out = [];
            const visit = (parentId) => {
              const list = childrenByParent[parentId] || [];
              list.forEach((item) => {
                out.push(item);
                visit(Number(item.id || 0));
              });
            };
            visit(0);
            return out;
          };
          const renderSubtasks = () => {
            if (!subListEl || !subHintEl) return;
            if (!currentActivityId) {
              subHintEl.textContent = "Guarda primero la actividad para habilitar subtareas.";
              subListEl.innerHTML = "";
              return;
            }
            const canManage = canManageContent();
            subHintEl.textContent = "Gestiona las subtareas de esta actividad.";
            if (!currentSubactivities.length) {
              subListEl.innerHTML = '<div class="poa-sub-meta">Sin subtareas registradas.</div>';
              return;
            }
            subListEl.innerHTML = orderSubtasks(currentSubactivities).map((item) => {
              const level = Number(item.nivel || 1);
              const marginLeft = Math.max(0, (level - 1) * 18);
              const rawSubOwner = String(item.responsable || "").trim();
              const noSubOwner = !rawSubOwner;
              const subOwnerText = escapeHtml(rawSubOwner || "Sin responsable");
              const subCode = escapeHtml(String(item.codigo || "sin código"));
              return `
              <article class="poa-sub-item${noSubOwner ? ' poa-act-no-owner' : ''}" data-sub-id="${Number(item.id || 0)}" data-level="${level}" style="margin-left:${marginLeft}px">
                <h5>${subCode} · ${escapeHtml(item.nombre || "Subtarea sin nombre")}</h5>
                <div class="poa-sub-meta">Nivel ${level} · ${escapeHtml(fmtDate(item.fecha_inicial))} - ${escapeHtml(fmtDate(item.fecha_final))} · Responsable: <span class="${noSubOwner ? 'poa-no-owner-text' : ''}">${subOwnerText}</span></div>
                ${canManage ? `
                <div class="poa-sub-actions">
                  <button type="button" class="poa-sub-btn" data-sub-add-child="${Number(item.id || 0)}">Agregar hija</button>
                  <button type="button" class="poa-sub-btn" data-sub-edit="${Number(item.id || 0)}">Editar</button>
                  <button type="button" class="poa-sub-btn warn" data-sub-delete="${Number(item.id || 0)}">Eliminar</button>
                </div>
                ` : ""}
              </article>
            `;
            }).join("");
            if (canManage) {
              subListEl.querySelectorAll("[data-sub-add-child]").forEach((btn) => {
                btn.addEventListener("click", () => openSubtaskForm(0, Number(btn.getAttribute("data-sub-add-child"))));
              });
              subListEl.querySelectorAll("[data-sub-edit]").forEach((btn) => {
                btn.addEventListener("click", () => openSubtaskForm(Number(btn.getAttribute("data-sub-edit")), 0));
              });
              subListEl.querySelectorAll("[data-sub-delete]").forEach((btn) => {
                btn.addEventListener("click", async () => deleteSubtask(Number(btn.getAttribute("data-sub-delete"))));
              });
            }
          };
          const fillSubCollaborators = async () => {
            if (!subOwnerEl || !subAssignedEl || !currentObjective) return;
            try {
              const list = await loadAllCollaboratorNames();
              subOwnerEl.innerHTML = '<option value="">Selecciona responsable</option>' + list.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join("");
              subAssignedEl.innerHTML = list.map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join("");
            } catch (_err) {
              subOwnerEl.innerHTML = '<option value="">Selecciona responsable</option>';
              subAssignedEl.innerHTML = "";
            }
          };
          const setSubDateBounds = (parentSub = null) => {
            const minDate = parentSub?.fecha_inicial || (actStartEl && actStartEl.value ? actStartEl.value : "");
            const maxDate = parentSub?.fecha_final || (actEndEl && actEndEl.value ? actEndEl.value : "");
            [subStartEl, subEndEl].forEach((el) => {
              if (!el) return;
              el.min = minDate || "";
              el.max = maxDate || "";
            });
          };
          const syncSubRecurringFields = () => {
            const enabled = !!(subRecurrenteEl && subRecurrenteEl.checked);
            if (subPeriodicidadEl) {
              subPeriodicidadEl.disabled = !enabled;
              if (!enabled) subPeriodicidadEl.value = "";
            }
            const showEveryDays = enabled && subPeriodicidadEl && subPeriodicidadEl.value === "cada_xx_dias";
            if (subEveryDaysWrapEl) subEveryDaysWrapEl.style.display = showEveryDays ? "block" : "none";
            if (subEveryDaysEl && !showEveryDays) subEveryDaysEl.value = "";
          };
          const openSubtaskForm = async (subId = 0, parentId = 0) => {
            if (!canManageContent()) return;
            if (!currentActivityId) {
              showModalMsg("Guarda la actividad antes de crear subtareas.", true);
              return;
            }
            editingSubId = subId || 0;
            currentParentSubId = parentId || 0;
            await fillSubCollaborators();
            const found = currentSubactivities.find((item) => Number(item.id || 0) === Number(editingSubId));
            if (found && found.parent_subactivity_id) {
              currentParentSubId = Number(found.parent_subactivity_id || 0);
            }
            const parentSub = currentSubactivities.find((item) => Number(item.id || 0) === Number(currentParentSubId)) || null;
            const targetLevel = found ? Number(found.nivel || 1) : (parentSub ? Number(parentSub.nivel || 1) + 1 : 1);
            setSubDateBounds(parentSub);
            if (subNameEl) subNameEl.value = found?.nombre || "";
            if (subOwnerEl) subOwnerEl.value = found?.responsable || "";
            if (subStartEl) subStartEl.value = found?.fecha_inicial || "";
            if (subEndEl) subEndEl.value = found?.fecha_final || "";
            if (subRecurrenteEl) subRecurrenteEl.checked = !!found?.recurrente;
            if (subPeriodicidadEl) subPeriodicidadEl.value = found?.periodicidad || "";
            if (subEveryDaysEl) subEveryDaysEl.value = found?.cada_xx_dias || "";
            syncSubRecurringFields();
            if (subDescEl) subDescEl.value = found?.descripcion || "";
            renderSubBranch(targetLevel, found?.nombre || "", currentParentSubId);
            showSubMsg("");
            openSubModal();
            if (subNameEl) subNameEl.focus();
          };
          const saveSubtask = async () => {
            if (!canManageContent()) {
              showSubMsg("Solo administrador puede guardar subtareas.", true);
              return;
            }
            if (!currentActivityId) {
              showSubMsg("Guarda primero la actividad.", true);
              return;
            }
            const nombre = (subNameEl && subNameEl.value ? subNameEl.value : "").trim();
            const responsable = (subOwnerEl && subOwnerEl.value ? subOwnerEl.value : "").trim();
            const fechaInicial = subStartEl && subStartEl.value ? subStartEl.value : "";
            const fechaFinal = subEndEl && subEndEl.value ? subEndEl.value : "";
            const recurrente = !!(subRecurrenteEl && subRecurrenteEl.checked);
            const periodicidad = (subPeriodicidadEl && subPeriodicidadEl.value ? subPeriodicidadEl.value : "").trim();
            const cadaXxDiasRaw = (subEveryDaysEl && subEveryDaysEl.value ? subEveryDaysEl.value : "").trim();
            const cadaXxDias = cadaXxDiasRaw ? Number(cadaXxDiasRaw) : 0;
            const MAINDesc = (subDescEl && subDescEl.value ? subDescEl.value : "").trim();
            const assigned = subAssignedEl ? Array.from(subAssignedEl.selectedOptions || []).map((opt) => opt.value).filter(Boolean) : [];
            if (!nombre) {
              showSubMsg("Nombre es obligatorio.", true);
              return;
            }
            if (!fechaInicial || !fechaFinal) {
              showSubMsg("Fecha inicial y fecha final son obligatorias.", true);
              return;
            }
            if (fechaInicial > fechaFinal) {
              showSubMsg("La fecha inicial no puede ser mayor que la final.", true);
              return;
            }
            if ((subStartEl && subStartEl.min && fechaInicial < subStartEl.min) || (subEndEl && subEndEl.max && fechaFinal > subEndEl.max)) {
              showSubMsg("Las fechas deben estar dentro del rango de la actividad.", true);
              return;
            }
            if (recurrente) {
              if (!periodicidad) {
                showSubMsg("Selecciona una periodicidad para la subtarea recurrente.", true);
                return;
              }
              if (periodicidad === "cada_xx_dias" && (!Number.isInteger(cadaXxDias) || cadaXxDias <= 0)) {
                showSubMsg("Cada xx dias debe ser un entero mayor a 0.", true);
                return;
              }
            }
            const descripcion = assigned.length
              ? `${MAINDesc}${MAINDesc ? "\\n\\n" : ""}Personas asignadas: ${assigned.join(", ")}`
              : MAINDesc;
            const payload = {
              nombre,
              responsable,
              fecha_inicial: fechaInicial,
              fecha_final: fechaFinal,
              recurrente,
              periodicidad: recurrente ? periodicidad : "",
              cada_xx_dias: recurrente && periodicidad === "cada_xx_dias" ? cadaXxDias : 0,
              descripcion,
            };
            if (!editingSubId && currentParentSubId) {
              payload.parent_subactivity_id = currentParentSubId;
            }
            showSubMsg("Guardando subtarea...");
            try {
              const url = editingSubId ? `/api/poa/subactivities/${editingSubId}` : `/api/poa/activities/${currentActivityId}/subactivities`;
              const method = editingSubId ? "PUT" : "POST";
              const response = await fetch(url, {
                method,
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
                body: JSON.stringify(payload),
              });
              const data = await response.json().catch(() => ({}));
              if (!response.ok || data.success === false) {
                throw new Error(data.error || "No se pudo guardar la subtarea.");
              }
              const item = data.data || {};
              if (editingSubId) {
                currentSubactivities = currentSubactivities.map((sub) => Number(sub.id || 0) === Number(editingSubId) ? item : sub);
              } else {
                currentSubactivities = [item, ...currentSubactivities];
              }
              renderSubtasks();
              closeSubModal();
              showModalMsg("Subtarea guardada.");
            } catch (error) {
              showSubMsg(error.message || "No se pudo guardar la subtarea.", true);
            }
          };
          const deleteSubtask = async (subId) => {
            if (!canManageContent()) return;
            if (!subId) return;
            if (!window.confirm("¿Eliminar esta subtarea?")) return;
            try {
              const response = await fetch(`/api/poa/subactivities/${subId}`, {
                method: "DELETE",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
              });
              const data = await response.json().catch(() => ({}));
              if (!response.ok || data.success === false) {
                throw new Error(data.error || "No se pudo eliminar la subtarea.");
              }
              const removeIds = new Set([Number(subId)]);
              let changed = true;
              while (changed) {
                changed = false;
                currentSubactivities.forEach((item) => {
                  const itemId = Number(item.id || 0);
                  const parentId = Number(item.parent_subactivity_id || 0);
                  if (!removeIds.has(itemId) && removeIds.has(parentId)) {
                    removeIds.add(itemId);
                    changed = true;
                  }
                });
              }
              currentSubactivities = currentSubactivities.filter((item) => !removeIds.has(Number(item.id || 0)));
              renderSubtasks();
              showModalMsg("Subtarea eliminada.");
            } catch (error) {
              showModalMsg(error.message || "No se pudo eliminar la subtarea.", true);
            }
          };
          const validateActivityDates = () => {
            const start = actStartEl && actStartEl.value ? actStartEl.value : "";
            const end = actEndEl && actEndEl.value ? actEndEl.value : "";
            if (!start || !end) return "Fecha inicial y fecha final son obligatorias.";
            if (start > end) return "La fecha inicial no puede ser mayor que la fecha final.";
            const minDate = String(currentObjective?.fecha_inicial || "");
            const maxDate = String(currentObjective?.fecha_final || "");
            if (minDate && start < minDate) return "La fecha inicial no puede ser menor a la del objetivo.";
            if (maxDate && end > maxDate) return "La fecha final no puede ser mayor a la del objetivo.";
            return "";
          };
          const syncRecurringFields = () => {
            const enabled = !!(actRecurrenteEl && actRecurrenteEl.checked);
            if (actPeriodicidadEl) {
              actPeriodicidadEl.disabled = !enabled;
              if (!enabled) actPeriodicidadEl.value = "";
            }
            const showEveryDays = enabled && actPeriodicidadEl && actPeriodicidadEl.value === "cada_xx_dias";
            if (actEveryDaysWrapEl) actEveryDaysWrapEl.style.display = showEveryDays ? "block" : "none";
            if (actEveryDaysEl && !showEveryDays) actEveryDaysEl.value = "";
          };
          const saveActivity = async () => {
            if (!canManageContent()) {
              showModalMsg("Solo administrador puede editar actividades.", true);
              return;
            }
            if (isSaving) return;
            if (activityEditorMode === "list") {
              showActListMsg("Pulsa 'Nuevo' o 'Editar' antes de guardar.", true);
              return;
            }
            if (!currentObjective) {
              showModalMsg("Selecciona un objetivo válido.", true);
              return;
            }
            const nombre = (actNameEl && actNameEl.value ? actNameEl.value : "").trim();
            const responsable = (actOwnerEl && actOwnerEl.value ? actOwnerEl.value : "").trim();
            const fechaInicial = actStartEl && actStartEl.value ? actStartEl.value : "";
            const fechaFinal = actEndEl && actEndEl.value ? actEndEl.value : "";
            const recurrente = !!(actRecurrenteEl && actRecurrenteEl.checked);
            const periodicidad = (actPeriodicidadEl && actPeriodicidadEl.value ? actPeriodicidadEl.value : "").trim();
            const cadaXxDiasRaw = (actEveryDaysEl && actEveryDaysEl.value ? actEveryDaysEl.value : "").trim();
            const cadaXxDias = cadaXxDiasRaw ? Number(cadaXxDiasRaw) : 0;
            const descripcionMAIN = (actDescRich ? actDescRich.getHtml() : (actDescEl && actDescEl.value ? actDescEl.value : "")).trim();
            const assigned = actAssignedEl ? Array.from(actAssignedEl.selectedOptions || []).map((opt) => opt.value).filter(Boolean) : [];
            const impactedMilestoneIds = actImpactHitosEl ? Array.from(actImpactHitosEl.selectedOptions || []).map((opt) => Number(opt.value || 0)).filter((value) => value > 0) : [];
            if (!nombre) {
              showModalMsg("Nombre es obligatorio.", true);
              return;
            }
            const deliverables = normalizeDeliverables(currentDeliverables);
            if (!deliverables.length) {
              showDeliverableMsg("Agrega al menos un entregable.", true);
              activatePoaTab("deliverables");
              return;
            }
            const dateError = validateActivityDates();
            if (dateError) {
              showModalMsg(dateError, true);
              return;
            }
            if (recurrente) {
              if (!periodicidad) {
                showModalMsg("Selecciona una periodicidad para la actividad recurrente.", true);
                return;
              }
              if (periodicidad === "cada_xx_dias" && (!Number.isInteger(cadaXxDias) || cadaXxDias <= 0)) {
                showModalMsg("Cada xx dias debe ser un entero mayor a 0.", true);
                return;
              }
            }
            const assignedHtml = assigned.length
              ? `<p><em>Personas asignadas: ${escapeHtml(assigned.join(", "))}</em></p>`
              : "";
            const descripcion = assignedHtml ? `${descripcionMAIN}${assignedHtml}` : descripcionMAIN;
            const payload = {
              objective_id: Number(currentObjective.id || 0),
              nombre,
              entregable: String(deliverables[0]?.nombre || "").trim(),
              entregables: deliverables,
              responsable,
              fecha_inicial: fechaInicial,
              fecha_final: fechaFinal,
              recurrente,
              periodicidad: recurrente ? periodicidad : "",
              cada_xx_dias: recurrente && periodicidad === "cada_xx_dias" ? cadaXxDias : 0,
              descripcion,
              budget_items: normalizeBudgetItems(currentBudgetItems),
              impacted_milestone_ids: impactedMilestoneIds,
            };
            isSaving = true;
            if (saveBtn) saveBtn.disabled = true;
            showModalMsg("Guardando actividad...");
            try {
              const response = await fetch(currentActivityId ? `/api/poa/activities/${currentActivityId}` : "/api/poa/activities", {
                method: currentActivityId ? "PUT" : "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
                body: JSON.stringify(payload),
              });
              const data = await response.json().catch(() => ({}));
              if (!response.ok || data.success === false) {
                throw new Error(data.error || "No se pudo guardar la actividad.");
              }
              currentActivityId = Number(data.data?.id || currentActivityId || 0);
              selectedListActivityId = Number(data.data?.id || selectedListActivityId || 0);
              currentActivityData = data.data || currentActivityData;
              currentSubactivities = Array.isArray(data.data?.subactivities) ? data.data.subactivities : currentSubactivities;
              currentBudgetItems = normalizeBudgetItems(data.data?.budget_items || currentBudgetItems);
              currentDeliverables = normalizeDeliverables(data.data?.entregables || deliverables);
              renderSubtasks();
              renderBudgetItems();
              renderDeliverables();
              renderStateStrip();
              renderActivityList();
              showModalMsg("Actividad guardada correctamente. Refrescando listado...");
              await loadBoard();
              if (currentObjective) {
                currentObjective = objectivesById[Number(currentObjective.id || 0)] || currentObjective;
                const latest = (activitiesByObjective[Number(currentObjective.id || 0)] || [])
                  .find((item) => Number(item.id || 0) === Number(currentActivityId || selectedListActivityId || 0))
                  || null;
                if (latest) {
                  populateActivityForm(latest);
                  if (assignedByEl) assignedByEl.textContent = `Asignado por: ${latest?.created_by || currentObjective.lider || "N/D"}`;
                  setActivityEditorMode("list");
                  showActListMsg("Actividad guardada. Selecciona una actividad para abrir sus subtareas o usa 'Nuevo'.");
                } else {
                  renderActivityList();
                }
              }
              showModalMsg("Actividad guardada correctamente.");
            } catch (error) {
              showModalMsg(error.message || "No se pudo guardar la actividad.", true);
            } finally {
              isSaving = false;
              if (saveBtn) saveBtn.disabled = false;
            }
          };
          const markInProgress = async () => {
            if (!currentActivityId) {
              showModalMsg("Guarda primero la actividad para cambiar su estado.", true);
              return;
            }
            const canChangeStatus = !!(currentActivityData && currentActivityData.can_change_status);
            if (!canChangeStatus) {
              showModalMsg("Solo el dueño de la tarea puede cambiar estatus.", true);
              return;
            }
            showModalMsg("Actualizando estado...");
            try {
              const response = await fetch(`/api/poa/activities/${currentActivityId}/mark-in-progress`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
              });
              const data = await response.json().catch(() => ({}));
              if (!response.ok || data.success === false) {
                throw new Error(data.error || "No se pudo marcar en proceso.");
              }
              currentActivityData = data.data || currentActivityData;
              currentSubactivities = Array.isArray(data.data?.subactivities) ? data.data.subactivities : currentSubactivities;
              renderStateStrip();
              showModalMsg("Actividad en proceso.");
              await loadBoard();
            } catch (error) {
              showModalMsg(error.message || "No se pudo marcar en proceso.", true);
            }
          };
          const markFinished = async () => {
            if (!currentActivityId) {
              showModalMsg("Guarda primero la actividad para declararla terminada.", true);
              return;
            }
            const canChangeStatus = !!(currentActivityData && currentActivityData.can_change_status);
            if (!canChangeStatus) {
              showModalMsg("Solo el dueño de la tarea puede cambiar estatus.", true);
              return;
            }
            const deliverables = normalizeDeliverables(currentDeliverables);
            const entregableName = String(deliverables[0]?.nombre || currentActivityData?.entregable || "").trim() || "N/D";
            const sendReview = window.confirm(`El entregable es ${entregableName}, ¿Quiere enviarlo a revisión?`);
            showModalMsg(sendReview ? "Enviando a revisión..." : "Declarando terminado...");
            try {
              const response = await fetch(`/api/poa/activities/${currentActivityId}/mark-finished`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
                body: JSON.stringify({ enviar_revision: sendReview }),
              });
              const data = await response.json().catch(() => ({}));
              if (!response.ok || data.success === false) {
                throw new Error(data.error || "No se pudo actualizar el estado.");
              }
              currentActivityData = data.data || currentActivityData;
              currentSubactivities = Array.isArray(data.data?.subactivities) ? data.data.subactivities : currentSubactivities;
              renderStateStrip();
              showModalMsg(data.message || "Estado actualizado.");
              await loadBoard();
            } catch (error) {
              showModalMsg(error.message || "No se pudo actualizar el estado.", true);
            }
          };
          const resolveApproval = async (action) => {
            const approval = currentApprovalForActivity();
            if (!approval) {
              showModalMsg("No hay entregable pendiente para revisar.", true);
              return;
            }
            showModalMsg(action === "autorizar" ? "Aprobando entregable..." : "Rechazando entregable...");
            try {
              const response = await fetch(`/api/poa/approvals/${approval.id}/decision`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
                body: JSON.stringify({ accion: action, comentario: "" }),
              });
              const data = await response.json().catch(() => ({}));
              if (!response.ok || data.success === false) {
                throw new Error(data.error || "No se pudo procesar la revisión.");
              }
              showModalMsg(data.message || "Revisión procesada.");
              await loadBoard();
              if (currentObjective) {
                const latest = (activitiesByObjective[Number(currentObjective.id || 0)] || [])
                  .find((item) => Number(item.id || 0) === Number(currentActivityId))
                  || null;
                if (latest) {
                  currentActivityData = latest;
                  currentSubactivities = Array.isArray(latest.subactivities) ? latest.subactivities : [];
                }
                renderStateStrip();
              }
            } catch (error) {
              showModalMsg(error.message || "No se pudo procesar la revisión.", true);
            }
          };
          closeBtn && closeBtn.addEventListener("click", closeModal);
          cancelBtn && cancelBtn.addEventListener("click", () => {
            const hasSelectedActivity = !!Number(selectedListActivityId || currentActivityId || 0);
            if (hasSelectedActivity && currentObjective) {
              setActivityEditorMode("list");
              renderActivityList();
              showActListMsg("Selecciona una actividad para abrir sus subtareas o usa 'Nuevo'.");
              return;
            }
            closeModal();
          });
          subCloseBtn && subCloseBtn.addEventListener("click", closeSubModal);
          subCancelBtn && subCancelBtn.addEventListener("click", closeSubModal);
          subSaveBtn && subSaveBtn.addEventListener("click", saveSubtask);
          subAddBtn && subAddBtn.addEventListener("click", () => openSubtaskForm(0, 0));
          subRecurrenteEl && subRecurrenteEl.addEventListener("change", syncSubRecurringFields);
          subPeriodicidadEl && subPeriodicidadEl.addEventListener("change", syncSubRecurringFields);
          openGanttBtn && openGanttBtn.addEventListener("click", async () => {
            if (!poaPermissions.can_view_gantt) return;
            window.location.href = "/poa/gantt";
          });
          openTreeBtn && openTreeBtn.addEventListener("click", () => {
            window.location.href = "/poa/arbol";
          });
          openCalendarBtn && openCalendarBtn.addEventListener("click", () => {
            window.location.href = "/poa/calendario";
          });
          treeCloseBtn && treeCloseBtn.addEventListener("click", closeTreeModal);
          ganttCloseBtn && ganttCloseBtn.addEventListener("click", closeGanttModal);
          calendarCloseBtn && calendarCloseBtn.addEventListener("click", closeCalendarModal);
          treeModalEl && treeModalEl.addEventListener("click", (event) => {
            if (event.target === treeModalEl) closeTreeModal();
          });
          ganttModalEl && ganttModalEl.addEventListener("click", (event) => {
            if (event.target === ganttModalEl) closeGanttModal();
          });
          calendarModalEl && calendarModalEl.addEventListener("click", (event) => {
            if (event.target === calendarModalEl) closeCalendarModal();
          });
          calendarPrevBtn && calendarPrevBtn.addEventListener("click", () => {
            shiftCalendarMonth(-1);
            renderPoaCalendar();
          });
          calendarTodayBtn && calendarTodayBtn.addEventListener("click", () => {
            poaCalendarCursor = new Date();
            renderPoaCalendar();
          });
          calendarNextBtn && calendarNextBtn.addEventListener("click", () => {
            shiftCalendarMonth(1);
            renderPoaCalendar();
          });
          ganttShowAllBtn && ganttShowAllBtn.addEventListener("click", async () => {
            syncPoaGanttVisibility();
            Object.keys(poaGanttVisibility).forEach((key) => { poaGanttVisibility[key] = true; });
            renderPoaGanttFilters();
            await renderPoaGantt();
          });
          ganttHideAllBtn && ganttHideAllBtn.addEventListener("click", async () => {
            syncPoaGanttVisibility();
            Object.keys(poaGanttVisibility).forEach((key) => { poaGanttVisibility[key] = false; });
            renderPoaGanttFilters();
            await renderPoaGantt();
          });
          modalEl && modalEl.addEventListener("click", (event) => {
            if (event.target === modalEl) closeModal();
          });
          subModalEl && subModalEl.addEventListener("click", (event) => {
            if (event.target === subModalEl) closeSubModal();
          });
          document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && modalEl && modalEl.classList.contains("open")) closeModal();
            if (event.key === "Escape" && subModalEl && subModalEl.classList.contains("open")) closeSubModal();
            if (event.key === "Escape" && treeModalEl && treeModalEl.classList.contains("open")) closeTreeModal();
            if (event.key === "Escape" && ganttModalEl && ganttModalEl.classList.contains("open")) closeGanttModal();
            if (event.key === "Escape" && calendarModalEl && calendarModalEl.classList.contains("open")) closeCalendarModal();
          });
          saveBtn && saveBtn.addEventListener("click", saveActivity);
          saveTopBtn && saveTopBtn.addEventListener("click", saveActivity);
          newActBtn && newActBtn.addEventListener("click", startNewActivity);
          editActBtn && editActBtn.addEventListener("click", loadSelectedActivityInForm);
          editBottomBtn && editBottomBtn.addEventListener("click", loadSelectedActivityInForm);
          deleteActBtn && deleteActBtn.addEventListener("click", deleteSelectedActivity);
          delivAddBtn && delivAddBtn.addEventListener("click", addDeliverable);
          delivNameEl && delivNameEl.addEventListener("keydown", (event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              addDeliverable();
            }
          });
          budgetAddBtn && budgetAddBtn.addEventListener("click", addOrUpdateBudgetItem);
          budgetCancelBtn && budgetCancelBtn.addEventListener("click", clearBudgetForm);
          budgetMonthlyEl && budgetMonthlyEl.addEventListener("input", syncBudgetAnnual);
          stateEnProcesoBtn && stateEnProcesoBtn.addEventListener("click", markInProgress);
          stateTerminadoBtn && stateTerminadoBtn.addEventListener("click", markFinished);
          approveBtn && approveBtn.addEventListener("click", () => resolveApproval("autorizar"));
          rejectBtn && rejectBtn.addEventListener("click", () => resolveApproval("rechazar"));
          actNameEl && actNameEl.addEventListener("input", renderActivityBranch);
          actRecurrenteEl && actRecurrenteEl.addEventListener("change", syncRecurringFields);
          actPeriodicidadEl && actPeriodicidadEl.addEventListener("change", syncRecurringFields);
          actSuggestIaBtn && actSuggestIaBtn.addEventListener("click", async () => {
            if (!poaIaEnabled) {
              poaIaEnabled = await iaFeatureEnabled("poa");
              applyPoaPermissionsUI();
            }
            if (!poaIaEnabled) {
              showModalMsg("IA deshabilitada para tu rol en este módulo.", true);
              return;
            }
            if (!canManageContent()) {
              showModalMsg("Solo administrador puede usar sugerencias IA en actividades.", true);
              return;
            }
            const objectiveName = String(currentObjective?.nombre || "").trim();
            const axisName = String(currentObjective?.axis_name || "").trim();
            const activityName = (actNameEl && actNameEl.value ? actNameEl.value : "").trim();
            const descHtml = actDescRich ? actDescRich.getHtml() : (actDescEl && actDescEl.value ? actDescEl.value : "");
            const currentDesc = plainTextFromHtml(descHtml);
            if (!objectiveName && !activityName && !currentDesc) {
              showModalMsg("Captura nombre o descripción antes de pedir sugerencia IA.", true);
              return;
            }
            actSuggestIaBtn.disabled = true;
            showModalMsg("Generando sugerencia con IA...");
            try {
              const prompt = [
                "Mejora redacción de actividad POA.",
                `Eje: ${axisName || "Sin eje"}`,
                `Objetivo: ${objectiveName || "Sin objetivo"}`,
                `Actividad: ${activityName || "Sin nombre"}`,
                `Descripción actual: ${currentDesc || "Sin descripción"}`,
                "Responde solo con una descripción final clara, medible y en español.",
              ].join("\\n");
              const draftResp = await fetch("/api/ia/suggestions", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
                body: JSON.stringify({
                  prompt,
                  original_text: currentDesc,
                  target_module: "poa",
                  target_entity: "actividad",
                  target_entity_id: String(currentActivityId || ""),
                  target_field: "descripcion",
                }),
              });
              const draftData = await draftResp.json().catch(() => ({}));
              if (!draftResp.ok || draftData.success === false) {
                throw new Error(draftData.error || "No se pudo generar sugerencia IA.");
              }
              const draft = draftData.data || {};
              const decision = await openPoaIaSuggestionEditor({
                title: "Sugerencia IA para descripción de actividad",
                suggestion: String(draft.suggested_text || ""),
              });
              if (decision.action === "apply") {
                const applyResp = await fetch(`/api/ia/suggestions/${draft.id}/apply`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  credentials: "same-origin",
                  body: JSON.stringify({ edited_text: String(decision.text || "").trim() }),
                });
                const applyData = await applyResp.json().catch(() => ({}));
                if (!applyResp.ok || applyData.success === false) {
                  throw new Error(applyData.error || "No se pudo aplicar sugerencia IA.");
                }
                const appliedText = String(applyData?.data?.applied_text || decision.text || "").trim();
                if (actDescRich) actDescRich.setHtml(appliedText);
                else if (actDescEl) actDescEl.value = appliedText;
                showModalMsg("Sugerencia IA aplicada en la descripción de la actividad.");
              } else if (decision.action === "discard") {
                const discardResp = await fetch(`/api/ia/suggestions/${draft.id}/discard`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  credentials: "same-origin",
                  body: JSON.stringify({ reason: "Descartada por usuario", edited_text: String(decision.text || "").trim() }),
                });
                const discardData = await discardResp.json().catch(() => ({}));
                if (!discardResp.ok || discardData.success === false) {
                  throw new Error(discardData.error || "No se pudo descartar sugerencia IA.");
                }
                showModalMsg("Sugerencia IA descartada.");
              } else {
                showModalMsg("Sugerencia IA generada. Puedes volver a abrir IA para aplicarla o descartarla.");
              }
            } catch (error) {
              showModalMsg(error.message || "No se pudo generar sugerencia IA.", true);
            } finally {
              actSuggestIaBtn.disabled = !canManageContent() || !poaIaEnabled;
            }
          });
          subNameEl && subNameEl.addEventListener("input", () => {
            const found = currentSubactivities.find((item) => Number(item.id || 0) === Number(editingSubId));
            const targetLevel = found ? Number(found.nivel || 1) : (() => {
              const parentSub = currentSubactivities.find((item) => Number(item.id || 0) === Number(currentParentSubId));
              return parentSub ? Number(parentSub.nivel || 1) + 1 : 1;
            })();
            renderSubBranch(targetLevel, subNameEl.value || "", currentParentSubId);
          });
          document.querySelectorAll("[data-poa-tab]").forEach((tabBtn) => {
            tabBtn.addEventListener("click", () => {
              const tabKey = tabBtn.getAttribute("data-poa-tab");
              activatePoaTab(tabKey);
            });
          });

          const renderBoard = (payload) => {
            poaPermissions = {
              poa_access_level: String(payload?.permissions?.poa_access_level || "mis_tareas"),
              can_manage_content: !!payload?.permissions?.can_manage_content,
              can_view_gantt: !!payload?.permissions?.can_view_gantt,
            };
            const diagnostics = payload?.diagnostics || {};
            showMsg("");
            applyPoaPermissionsUI();
            const objectives = Array.isArray(payload.objectives) ? payload.objectives : [];
            const activities = Array.isArray(payload.activities) ? payload.activities : [];
            renderOwnerActivityChart(activities);
            poaGanttObjectives = objectives;
            poaGanttActivities = activities;
            if (treeModalEl && treeModalEl.classList.contains("open")) {
              renderPoaAdvanceTree();
            }
            if (calendarModalEl && calendarModalEl.classList.contains("open")) {
              renderPoaCalendar();
            }
            const pendingApprovals = Array.isArray(payload.pending_approvals) ? payload.pending_approvals : [];
            objectivesById = {};
            activitiesByObjective = {};
            approvalsByActivity = {};
            objectives.forEach((obj) => {
              objectivesById[Number(obj.id || 0)] = obj;
            });
            const activityCountByObjective = {};
            activities.forEach((item) => {
              const key = Number(item.objective_id || 0);
              if (!key) return;
              activityCountByObjective[key] = (activityCountByObjective[key] || 0) + 1;
              if (!activitiesByObjective[key]) activitiesByObjective[key] = [];
              activitiesByObjective[key].push(item);
            });
            Object.keys(activitiesByObjective).forEach((key) => {
              activitiesByObjective[key].sort((a, b) => Number(b.id || 0) - Number(a.id || 0));
            });
            pendingApprovals.forEach((approval) => {
              const actId = Number(approval.activity_id || 0);
              if (!actId) return;
              approvalsByActivity[actId] = approval;
            });
            const activitiesNoOwner = activities.filter((item) => !String(item?.responsable || "").trim());
            if (noOwnerMsgEl) {
              if (!activitiesNoOwner.length) {
                noOwnerMsgEl.style.display = "none";
                noOwnerMsgEl.innerHTML = "";
              } else {
                const listItems = activitiesNoOwner.slice(0, 8)
                  .map((item) => {
                    const code = String(item.codigo || "").trim() || "Sin código";
                    const name = String(item.nombre || "Sin nombre");
                    return `<li><span class="panel__list-item"><span class="panel__list-code">${escapeHtml(code)}</span><span class="panel__list-name">${escapeHtml(name)}</span></span></li>`;
                  })
                  .join("");
                const extraCount = activitiesNoOwner.length > 8 ? `<a href="#" class="panel__more">+${activitiesNoOwner.length - 8} más</a>` : "";
                noOwnerMsgEl.style.display = "block";
                noOwnerMsgEl.innerHTML = `<article class="panel"><header class="panel__head"><h5 class="panel__title">Actividades sin responsable</h5><div class="panel__meta"><strong>${activitiesNoOwner.length}</strong> pendiente(s)</div></header><ul class="panel__list">${listItems}</ul>${extraCount}</article>`;
              }
            }
            const subactivitiesNoOwner = activities.flatMap((item) => {
              const subList = Array.isArray(item?.subactivities) ? item.subactivities : [];
              return subList
                .filter((sub) => !String(sub?.responsable || "").trim())
                .map((sub) => ({
                  nombre: String(sub?.nombre || "Subtarea sin nombre"),
                  activity: String(item?.nombre || "Actividad sin nombre"),
                }));
            });
            if (noSubOwnerMsgEl) {
              if (!subactivitiesNoOwner.length) {
                noSubOwnerMsgEl.style.display = "none";
                noSubOwnerMsgEl.innerHTML = "";
              } else {
                const listItems = subactivitiesNoOwner.slice(0, 8)
                  .map((item) => `<li><span class="panel__list-item"><span class="panel__list-code">Subtarea</span><span class="panel__list-name">${escapeHtml(item.nombre)} <span class="text-MAIN-content/60">(${escapeHtml(item.activity)})</span></span></span></li>`)
                  .join("");
                const extraCount = subactivitiesNoOwner.length > 8 ? `<a href="#" class="panel__more">+${subactivitiesNoOwner.length - 8} más</a>` : "";
                noSubOwnerMsgEl.style.display = "block";
                noSubOwnerMsgEl.innerHTML = `<article class="panel"><header class="panel__head"><h5 class="panel__title">Subtareas sin responsable</h5><div class="panel__meta"><strong>${subactivitiesNoOwner.length}</strong> pendiente(s)</div></header><ul class="panel__list">${listItems}</ul>${extraCount}</article>`;
              }
            }
            if (currentActivityId && currentObjective) {
              const latest = (activitiesByObjective[Number(currentObjective.id || 0)] || [])
                .find((item) => Number(item.id || 0) === Number(currentActivityId))
                || null;
              if (latest) {
                currentActivityData = latest;
                currentSubactivities = Array.isArray(latest.subactivities) ? latest.subactivities : [];
              }
              renderStateStrip();
            }
            const grouped = {};
            objectives.forEach((obj) => {
              const axisName = String(obj.axis_name || "Sin eje").trim() || "Sin eje";
              if (!grouped[axisName]) grouped[axisName] = [];
              grouped[axisName].push(obj);
            });
            const axisNames = Object.keys(grouped).sort((a, b) => a.localeCompare(b, "es"));
            if (!axisNames.length) {
              gridEl.innerHTML = '<div class="poa-obj-card"><h4>Sin objetivos</h4><div class="meta">No hay objetivos disponibles para mostrar.</div></div>';
              return;
            }
            gridEl.innerHTML = axisNames.map((axisName) => {
              const items = grouped[axisName] || [];
              const cards = items.map((obj) => {
                const countActivities = activityCountByObjective[Number(obj.id || 0)] || 0;
                return `
                  <article class="poa-obj-card" data-objective-id="${Number(obj.id || 0)}" data-objective-json="${escapeHtml(JSON.stringify(obj || {}))}">
                    <h4>${escapeHtml(obj.nombre || "Objetivo sin nombre")}</h4>
                    <div class="meta">Hito: ${escapeHtml(obj.hito || "N/D")}</div>
                    <div class="meta">Fecha inicial: ${escapeHtml(fmtDate(obj.fecha_inicial))}</div>
                    <div class="meta">Fecha final: ${escapeHtml(fmtDate(obj.fecha_final))}</div>
                    <div class="meta">Actividades: ${countActivities}</div>
                    <span class="code">${escapeHtml(obj.codigo || "xx-yy-zz")}</span>
                    <div class="code-next">${escapeHtml(nextCode(obj.codigo || "", Number(obj.id || 0)))}</div>
                  </article>
                `;
              }).join("");
              return `
                <section class="poa-axis-col" data-axis-col>
                  <header class="poa-axis-head">
                    <h3 class="poa-axis-title">${escapeHtml(axisName)}</h3>
                    <button type="button" class="poa-axis-toggle" data-axis-toggle aria-label="Colapsar columna">−</button>
                  </header>
                  <div class="poa-axis-cards">${cards || '<article class="poa-obj-card"><div class="meta">Sin objetivos</div></article>'}</div>
                </section>
              `;
            }).join("");

          };
          gridEl.addEventListener("click", async (event) => {
            const target = event.target;
            const toggleBtn = target && target.closest ? target.closest("[data-axis-toggle]") : null;
            if (toggleBtn) {
              const col = toggleBtn.closest("[data-axis-col]");
              if (!col) return;
              const collapsed = col.classList.toggle("collapsed");
              toggleBtn.textContent = collapsed ? "+" : "−";
              toggleBtn.setAttribute("aria-label", collapsed ? "Mostrar columna" : "Colapsar columna");
              return;
            }
            const card = target && target.closest ? target.closest("[data-objective-id]") : null;
            if (card && gridEl.contains(card)) {
              const objectiveId = Number(card.getAttribute("data-objective-id") || 0);
              if (objectiveId) {
                let objectiveData = null;
                try {
                  objectiveData = JSON.parse(card.getAttribute("data-objective-json") || "{}");
                } catch (_err) {
                  objectiveData = null;
                }
                await openActivityForm(objectiveId, { objectiveData });
              }
            }
          });

          const loadBoard = async () => {
            showMsg("Cargando tablero POA...");
            try {
              const controller = new AbortController();
              const timeoutId = window.setTimeout(() => controller.abort(), 20000);
              const response = await fetch("/api/poa/board-data", {
                headers: { "Content-Type": "application/json" },
                credentials: "same-origin",
                signal: controller.signal,
              });
              window.clearTimeout(timeoutId);
              const payload = await response.json().catch(() => ({}));
              if (!response.ok || payload.success === false) {
                throw new Error(payload.error || "No se pudo cargar la vista POA.");
              }
              renderBoard(payload);
            } catch (error) {
              const msg = (error && error.name === "AbortError")
                ? "Tiempo de espera agotado al cargar POA. Reintenta y valida conexión/servidor."
                : (error.message || "No se pudo cargar la vista POA.");
              showMsg(msg, true);
            }
          };
          const importStrategicCsv = async (file) => {
            if (!canManageContent()) {
              showMsg("Solo administrador puede importar información.", true);
              return;
            }
            if (!file) return;
            showMsg("Importando plantilla estratégica y POA...");
            const formData = new FormData();
            formData.append("file", file);
            const response = await fetch("/api/planificacion/importar-plan-poa", {
              method: "POST",
              credentials: "same-origin",
              body: formData,
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok || payload.success === false) {
              throw new Error(payload.error || "No se pudo importar el archivo.");
            }
            await loadBoard();
            const summary = payload.summary || {};
            const created = Number(summary.created || 0);
            const updated = Number(summary.updated || 0);
            const skipped = Number(summary.skipped || 0);
            const errors = Array.isArray(summary.errors) ? summary.errors.length : 0;
            showMsg(`Importación completada. Creados: ${created}, actualizados: ${updated}, omitidos: ${skipped}, errores: ${errors}.`, errors > 0);
          };
          downloadTemplateBtn && downloadTemplateBtn.addEventListener("click", () => {
            window.location.href = "/api/planificacion/plantilla-plan-poa.csv";
          });
          exportXlsBtn && exportXlsBtn.addEventListener("click", () => {
            window.location.href = "/api/planificacion/exportar-plan-poa.xlsx";
          });
          importCsvBtn && importCsvBtn.addEventListener("click", () => {
            if (importCsvFileEl) importCsvFileEl.click();
          });
          importCsvFileEl && importCsvFileEl.addEventListener("change", async () => {
            const file = importCsvFileEl.files && importCsvFileEl.files[0];
            if (!file) return;
            try {
              await importStrategicCsv(file);
            } catch (err) {
              showMsg(err.message || "No se pudo importar el archivo CSV.", true);
            } finally {
              importCsvFileEl.value = "";
            }
          });
          annualCycleStartBtn && annualCycleStartBtn.addEventListener("click", async () => {
            try {
              await startAnnualCycle();
            } catch (err) {
              setAnnualCycleStatus(err.message || "No se pudo iniciar el nuevo ejercicio.", true);
            }
          });
          const openFromQuery = async () => {
            const params = new URLSearchParams(window.location.search || "");
            const objectiveId = Number(params.get("objective_id") || 0);
            const activityId = Number(params.get("activity_id") || 0);
            const subactivityId = Number(params.get("subactivity_id") || 0);
            let targetObjectiveId = objectiveId;
            if (!targetObjectiveId && activityId) {
              const matchObj = Object.keys(activitiesByObjective).find((objId) => {
                const list = activitiesByObjective[Number(objId)] || [];
                return list.some((item) => Number(item.id || 0) === activityId);
              });
              targetObjectiveId = Number(matchObj || 0);
            }
            if (!targetObjectiveId) return;
            await openActivityForm(targetObjectiveId, {
              activityId: activityId || 0,
              focusSubId: subactivityId || 0,
            });
          };

          iaFeatureEnabled("poa").then((enabled) => {
            poaIaEnabled = !!enabled;
            applyPoaPermissionsUI();
          });
          loadAnnualCycleContext().catch((error) => {
            setAnnualCycleStatus(error.message || "No se pudo cargar el ejercicio operativo.", true);
          });
          loadBoard().then(openFromQuery).catch(() => {});
        })();
