(function () {
          const buttons = Array.from(document.querySelectorAll('[data-planes-view]'));
          const planesQuery = new URLSearchParams(window.location.search || '');
          const planesAxisEditorShell = document.getElementById('planes-axis-editor-shell');
          const planesAxisListShell = document.getElementById('planes-axis-list-shell');
          const panels = {
            list: document.getElementById('planes-view-list'),
            kanban: document.getElementById('planes-view-kanban'),
            organigrama: document.getElementById('planes-view-organigrama'),
          };
          const syncAxisShells = (view) => {
            const isFormView = view === 'form';
            if (planesAxisEditorShell) {
              planesAxisEditorShell.style.display = isFormView ? '' : 'none';
            }
            if (planesAxisListShell) {
              planesAxisListShell.style.display = isFormView ? 'none' : '';
            }
          };
          function setView(view) {
            const target = ['form', 'list', 'kanban', 'organigrama'].includes(view) ? view : 'list';
            Object.keys(panels).forEach((key) => {
              const panel = panels[key];
              if (!panel) return;
              const visible = target === 'form' ? key === 'list' : key === target;
              panel.classList.toggle('hidden', !visible);
            });
            buttons.forEach((btn) => {
              btn.classList.toggle('active', (btn.getAttribute('data-planes-view') || '') === target);
            });
            syncAxisShells(target);
            if (target === 'form') {
              setStrategicTab('ejes');
            }
            if (target === 'organigrama') {
              renderStrategicTree(planesOrganigramaHostEl, { inline: true });
            }
            document.dispatchEvent(new CustomEvent('backend-view-change', { detail: { view: target } }));
          }
          buttons.forEach((btn) => {
            btn.addEventListener('click', () => setView(btn.getAttribute('data-planes-view') || 'list'));
          });

          const planesAddAxisBtn = document.getElementById('planes-add-axis-btn');
          const planesAxisEditorTitle = document.getElementById('planes-axis-editor-title');
          const planesAxisNewBtn = document.getElementById('planes-axis-new-btn');
          const planesAxisEditBtn = document.getElementById('planes-axis-edit-btn');
          const planesAxisSaveBtn = document.getElementById('planes-axis-save-btn');
          const planesAxisDeleteBtn = document.getElementById('planes-axis-delete-btn');
          const planesAxisBackBtn = document.getElementById('planes-axis-back-btn');
          const planesAxisMsg = document.getElementById('planes-axis-msg');
          const planesAxisNombre = document.getElementById('planes-axis-nombre');
          const planesAxisBaseCode = document.getElementById('planes-axis-base-code');
          const planesAxisOrden = document.getElementById('planes-axis-orden');
          const planesAxisDepartamento = document.getElementById('planes-axis-departamento');
          const planesAxisResponsable = document.getElementById('planes-axis-responsable');
          const planesAxisFechaInicial = document.getElementById('planes-axis-fecha-inicial');
          const planesAxisFechaFinal = document.getElementById('planes-axis-fecha-final');
          const planesAxisDescripcion = document.getElementById('planes-axis-descripcion');
          const planesAxisFormatButtons = Array.from(document.querySelectorAll('[data-planes-axis-cmd]'));
          const planesAxisKpiSection = document.getElementById('planes-axis-kpi-section');
          const planesAxisKpiList = document.getElementById('planes-axis-kpi-list');
          const planesAxisKpiAddBtn = document.getElementById('planes-axis-kpi-add-btn');
          const planesImportBtn = document.getElementById('planes-import-csv-btn');
          const planesImportFile = document.getElementById('planes-import-csv-file');
          const planesImportMsg = document.getElementById('planes-import-csv-msg');
          let planesAxesCache = [];
          let planesAxisCurrentId = '';
          let planesAxisEditMode = false;
          let planesAxisKpisState = [];
          const setPlanesImportMsg = (text, isError = false) => {
            if (!planesImportMsg) return;
            planesImportMsg.textContent = text || '';
            planesImportMsg.style.color = isError ? '#b91c1c' : '#0f3d2e';
          };
          const setPlanesAxisMsg = (text, isError = false) => {
            if (!planesAxisMsg) return;
            planesAxisMsg.textContent = text || '';
            planesAxisMsg.style.color = isError ? '#b91c1c' : '#0f3d2e';
          };
          const setAxisKpiSectionOpen = (open) => {
            if (!planesAxisKpiSection) return;
            if (open) {
              planesAxisKpiSection.setAttribute('open', 'open');
            } else {
              planesAxisKpiSection.removeAttribute('open');
            }
          };
          const normalizeAxisKpiItem = (item) => ({
            nombre: String(item?.nombre || '').trim(),
            descripcion: String(item?.descripcion || '').trim(),
            objetivo: String(item?.objetivo || '').trim(),
            formula: String(item?.formula || '').trim(),
            responsable: String(item?.responsable || '').trim(),
            fuente_datos: String(item?.fuente_datos || '').trim(),
            unidad: String(item?.unidad || '').trim(),
            frecuencia: String(item?.frecuencia || '').trim(),
            linea_base: String(item?.linea_base || '').trim(),
            estandar_meta: String(item?.estandar_meta || '').trim(),
            semaforo_rojo: String(item?.semaforo_rojo || '').trim(),
            semaforo_verde: String(item?.semaforo_verde || '').trim(),
            categoria: String(item?.categoria || '').trim(),
            perspectiva: String(item?.perspectiva || '').trim(),
          });
          const renderAxisKpiEditor = () => {
            if (!planesAxisKpiList) return;
            if (!planesAxisKpisState.length) {
              planesAxisKpiList.innerHTML = '<div class="text-base-content/60">Sin KPIs registrados.</div>';
              return;
            }
            planesAxisKpiList.innerHTML = planesAxisKpisState.map((item, idx) => `
              <article class="rounded-box border border-base-300 bg-base-100 p-4 grid gap-3">
                <div class="flex items-center justify-between gap-2">
                  <strong>KPI ${idx + 1}</strong>
                  <button type="button" class="btn btn-error btn-xs" data-planes-axis-kpi-remove="${idx}">Eliminar</button>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                  <label class="form-control w-full"><div class="label"><span class="label-text">Nombre</span></div><input class="input input-bordered w-full" data-kpi-field="nombre" data-kpi-index="${idx}" value="${escapeHtml(item.nombre)}" ${planesAxisEditMode ? '' : 'disabled'}></label>
                  <label class="form-control w-full"><div class="label"><span class="label-text">Responsable</span></div><input class="input input-bordered w-full" data-kpi-field="responsable" data-kpi-index="${idx}" value="${escapeHtml(item.responsable)}" ${planesAxisEditMode ? '' : 'disabled'}></label>
                  <label class="form-control w-full"><div class="label"><span class="label-text">Categoría</span></div><input class="input input-bordered w-full" data-kpi-field="categoria" data-kpi-index="${idx}" value="${escapeHtml(item.categoria)}" ${planesAxisEditMode ? '' : 'disabled'}></label>
                  <label class="form-control w-full"><div class="label"><span class="label-text">Perspectiva</span></div><input class="input input-bordered w-full" data-kpi-field="perspectiva" data-kpi-index="${idx}" value="${escapeHtml(item.perspectiva)}" ${planesAxisEditMode ? '' : 'disabled'}></label>
                  <label class="form-control w-full md:col-span-2 xl:col-span-3"><div class="label"><span class="label-text">Descripción</span></div><textarea class="textarea textarea-bordered w-full" data-kpi-field="descripcion" data-kpi-index="${idx}" ${planesAxisEditMode ? '' : 'disabled'}>${escapeHtml(item.descripcion)}</textarea></label>
                  <label class="form-control w-full md:col-span-2 xl:col-span-3"><div class="label"><span class="label-text">Objetivo</span></div><textarea class="textarea textarea-bordered w-full" data-kpi-field="objetivo" data-kpi-index="${idx}" ${planesAxisEditMode ? '' : 'disabled'}>${escapeHtml(item.objetivo)}</textarea></label>
                  <label class="form-control w-full md:col-span-2 xl:col-span-3"><div class="label"><span class="label-text">Fórmula</span></div><textarea class="textarea textarea-bordered w-full" data-kpi-field="formula" data-kpi-index="${idx}" ${planesAxisEditMode ? '' : 'disabled'}>${escapeHtml(item.formula)}</textarea></label>
                  <label class="form-control w-full"><div class="label"><span class="label-text">Fuente de datos</span></div><input class="input input-bordered w-full" data-kpi-field="fuente_datos" data-kpi-index="${idx}" value="${escapeHtml(item.fuente_datos)}" ${planesAxisEditMode ? '' : 'disabled'}></label>
                  <label class="form-control w-full"><div class="label"><span class="label-text">Unidad</span></div><input class="input input-bordered w-full" data-kpi-field="unidad" data-kpi-index="${idx}" value="${escapeHtml(item.unidad)}" ${planesAxisEditMode ? '' : 'disabled'}></label>
                  <label class="form-control w-full"><div class="label"><span class="label-text">Frecuencia</span></div><input class="input input-bordered w-full" data-kpi-field="frecuencia" data-kpi-index="${idx}" value="${escapeHtml(item.frecuencia)}" ${planesAxisEditMode ? '' : 'disabled'}></label>
                  <label class="form-control w-full"><div class="label"><span class="label-text">Línea base</span></div><input class="input input-bordered w-full" data-kpi-field="linea_base" data-kpi-index="${idx}" value="${escapeHtml(item.linea_base)}" ${planesAxisEditMode ? '' : 'disabled'}></label>
                  <label class="form-control w-full"><div class="label"><span class="label-text">Estándar / Meta</span></div><input class="input input-bordered w-full" data-kpi-field="estandar_meta" data-kpi-index="${idx}" value="${escapeHtml(item.estandar_meta)}" ${planesAxisEditMode ? '' : 'disabled'}></label>
                  <label class="form-control w-full"><div class="label"><span class="label-text">Semáforo rojo</span></div><input class="input input-bordered w-full" data-kpi-field="semaforo_rojo" data-kpi-index="${idx}" value="${escapeHtml(item.semaforo_rojo)}" ${planesAxisEditMode ? '' : 'disabled'}></label>
                  <label class="form-control w-full"><div class="label"><span class="label-text">Semáforo verde</span></div><input class="input input-bordered w-full" data-kpi-field="semaforo_verde" data-kpi-index="${idx}" value="${escapeHtml(item.semaforo_verde)}" ${planesAxisEditMode ? '' : 'disabled'}></label>
                </div>
              </article>
            `).join('');
            planesAxisKpiList.querySelectorAll('[data-kpi-field]').forEach((field) => {
              field.addEventListener('input', () => {
                const idx = Number(field.getAttribute('data-kpi-index') || -1);
                const key = String(field.getAttribute('data-kpi-field') || '').trim();
                if (idx < 0 || !key || !planesAxisKpisState[idx]) return;
                planesAxisKpisState[idx][key] = String(field.value || '');
              });
            });
            planesAxisKpiList.querySelectorAll('[data-planes-axis-kpi-remove]').forEach((btn) => {
              btn.disabled = !planesAxisEditMode;
              btn.addEventListener('click', () => {
                if (!planesAxisEditMode) return;
                const idx = Number(btn.getAttribute('data-planes-axis-kpi-remove') || -1);
                if (idx < 0) return;
                planesAxisKpisState.splice(idx, 1);
                renderAxisKpiEditor();
              });
            });
          };
          const renderAxisDescription = (value) => {
            if (!planesAxisDescripcion) return;
            const raw = String(value || '').trim();
            if (!raw) {
              planesAxisDescripcion.innerHTML = '<span class="text-base-content/50">Sin descripción.</span>';
              planesAxisDescripcion.dataset.empty = 'true';
              return;
            }
            planesAxisDescripcion.dataset.empty = 'false';
            const looksLikeHtml = /<[^>]+>/.test(raw);
            planesAxisDescripcion.innerHTML = looksLikeHtml
              ? raw
              : escapeHtml(raw).replace(/\n/g, '<br>');
          };
          const focusAxisDescriptionAtEnd = () => {
            if (!planesAxisDescripcion || typeof window.getSelection !== 'function' || typeof document.createRange !== 'function') return;
            planesAxisDescripcion.focus();
            const selection = window.getSelection();
            if (!selection) return;
            const range = document.createRange();
            range.selectNodeContents(planesAxisDescripcion);
            range.collapse(false);
            selection.removeAllRanges();
            selection.addRange(range);
          };
          const setAxisEditorDisabled = (disabled) => {
            [
              planesAxisNombre,
              planesAxisBaseCode,
              planesAxisOrden,
              planesAxisDepartamento,
              planesAxisResponsable,
              planesAxisFechaInicial,
              planesAxisFechaFinal,
            ].forEach((el) => {
              if (!el) return;
              el.disabled = !!disabled;
            });
            if (planesAxisDescripcion) {
              planesAxisDescripcion.setAttribute('contenteditable', disabled ? 'false' : 'true');
              planesAxisDescripcion.classList.toggle('cursor-text', !disabled);
              if (!disabled && planesAxisDescripcion.dataset.empty === 'true') {
                planesAxisDescripcion.innerHTML = '';
                planesAxisDescripcion.dataset.empty = 'false';
              }
            }
            planesAxisFormatButtons.forEach((btn) => {
              btn.disabled = !!disabled;
            });
            if (planesAxisKpiAddBtn) planesAxisKpiAddBtn.disabled = !!disabled;
            if (planesAxisSaveBtn) planesAxisSaveBtn.disabled = !!disabled;
            if (planesAxisDeleteBtn) planesAxisDeleteBtn.disabled = !!disabled || !planesAxisCurrentId;
            renderAxisKpiEditor();
          };
          const readAxisFormPayload = () => ({
            nombre: String(planesAxisNombre?.value || '').trim(),
            base_code: String(planesAxisBaseCode?.value || '').trim(),
            orden: String(planesAxisOrden?.value || '').trim(),
            lider_departamento: String(planesAxisDepartamento?.value || '').trim(),
            responsabilidad_directa: String(planesAxisResponsable?.value || '').trim(),
            fecha_inicial: String(planesAxisFechaInicial?.value || '').trim(),
            fecha_final: String(planesAxisFechaFinal?.value || '').trim(),
            descripcion: String(planesAxisDescripcion?.innerHTML || '').trim(),
            kpis: planesAxisKpisState.map((item) => normalizeAxisKpiItem(item)).filter((item) => item.nombre),
          });
          const fillAxisEditor = (axis, editMode = false) => {
            const current = axis && typeof axis === 'object' ? axis : null;
            planesAxisCurrentId = current && current.id != null ? String(current.id) : '';
            planesAxisEditMode = !!editMode;
            if (planesAxisEditorTitle) {
              planesAxisEditorTitle.textContent = planesAxisCurrentId
                ? `${planesAxisEditMode ? 'Editar' : 'Eje'}: ${String(current?.codigo || 'Sin código')} - ${String(current?.nombre || 'Sin nombre')}`
                : 'Nuevo eje estratégico';
            }
            if (planesAxisNombre) planesAxisNombre.value = String(current?.nombre || '');
            if (planesAxisBaseCode) planesAxisBaseCode.value = String(current?.base_code || '').trim();
            if (planesAxisOrden) planesAxisOrden.value = String(current?.orden || (planesAxesCache.length + 1) || 1);
            if (planesAxisDepartamento) planesAxisDepartamento.value = String(current?.lider_departamento || '');
            if (typeof window.__planesFillResponsables === 'function') {
              window.__planesFillResponsables(String(current?.lider_departamento || ''));
            }
            if (planesAxisResponsable) planesAxisResponsable.value = String(current?.responsabilidad_directa || '');
            if (planesAxisFechaInicial) planesAxisFechaInicial.value = String(current?.fecha_inicial || '');
            if (planesAxisFechaFinal) planesAxisFechaFinal.value = String(current?.fecha_final || '');
            renderAxisDescription(current?.descripcion || '');
            planesAxisKpisState = Array.isArray(current?.kpis) ? current.kpis.map((item) => normalizeAxisKpiItem(item)) : [];
            setAxisKpiSectionOpen(false);
            if (planesAxisEditBtn) planesAxisEditBtn.disabled = !planesAxisCurrentId;
            setAxisEditorDisabled(!planesAxisEditMode);
          };
          const selectAxisForEditing = (axisId, editMode = true) => {
            const target = planesAxesCache.find((axis) => String(axis?.id || '') === String(axisId || '')) || null;
            if (!target) return;
            try {
              const nextQuery = new URLSearchParams(window.location.search || '');
              nextQuery.set('tab', 'ejes');
              nextQuery.set('open', 'axis');
              nextQuery.set('axis_id', String(axisId || ''));
              nextQuery.set('view', 'form');
              window.history.replaceState({}, '', `${window.location.pathname}?${nextQuery.toString()}`);
            } catch (_err) {}
            setView('form');
            fillAxisEditor(target, editMode);
            setStrategicTab('ejes');
            const panel = document.getElementById('planes-tab-panel-ejes');
            if (panel && typeof panel.scrollIntoView === 'function') {
              panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
          };
          if (planesAddAxisBtn) {
            planesAddAxisBtn.addEventListener('click', () => {
              setView('form');
              setStrategicTab('ejes', true);
              fillAxisEditor(null, true);
              setPlanesAxisMsg('');
              if (planesAxisNombre) planesAxisNombre.focus();
            });
          }
          if (planesAxisNewBtn) {
            planesAxisNewBtn.addEventListener('click', () => {
              setView('form');
              fillAxisEditor(null, true);
              setPlanesAxisMsg('');
              if (planesAxisNombre) planesAxisNombre.focus();
            });
          }
          if (planesAxisBackBtn) {
            planesAxisBackBtn.addEventListener('click', () => {
              setView('list');
            });
          }
          if (planesAxisEditBtn) {
            planesAxisEditBtn.addEventListener('click', () => {
              if (!planesAxisCurrentId) return;
              selectAxisForEditing(planesAxisCurrentId, true);
              setPlanesAxisMsg('Modo edición habilitado.');
              focusAxisDescriptionAtEnd();
            });
          }
          planesAxisFormatButtons.forEach((btn) => {
            btn.addEventListener('click', () => {
              const cmd = btn.getAttribute('data-planes-axis-cmd') || '';
              if (!cmd || !planesAxisDescripcion || planesAxisDescripcion.getAttribute('contenteditable') !== 'true') return;
              planesAxisDescripcion.focus();
              try {
                document.execCommand(cmd, false, null);
              } catch (_err) {}
            });
          });
          if (planesAxisKpiAddBtn) {
            planesAxisKpiAddBtn.addEventListener('click', () => {
              if (!planesAxisEditMode) return;
              setAxisKpiSectionOpen(true);
              planesAxisKpisState.push(normalizeAxisKpiItem({}));
              renderAxisKpiEditor();
            });
          }
          if (planesAxisSaveBtn) {
            planesAxisSaveBtn.addEventListener('click', async () => {
              const payload = readAxisFormPayload();
              if (!payload.nombre) {
                setPlanesAxisMsg('El nombre del eje es obligatorio.', true);
                if (planesAxisNombre) planesAxisNombre.focus();
                return;
              }
              planesAxisSaveBtn.disabled = true;
              try {
                const targetId = String(planesAxisCurrentId || '').trim();
                const response = await fetch(targetId ? `/api/strategic-axes/${encodeURIComponent(targetId)}` : '/api/strategic-axes', {
                  method: targetId ? 'PUT' : 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  credentials: 'same-origin',
                  body: JSON.stringify(payload),
                });
                const data = await response.json().catch(() => ({}));
                if (!response.ok || data?.success === false) {
                  throw new Error(data?.error || data?.detail || 'No se pudo guardar el eje.');
                }
                setPlanesAxisMsg('Eje guardado.');
                await loadTracking();
                const savedId = String(data?.data?.id || targetId || '').trim();
                if (savedId) selectAxisForEditing(savedId, false);
              } catch (error) {
                setPlanesAxisMsg(error?.message || 'No se pudo guardar el eje.', true);
              } finally {
                planesAxisSaveBtn.disabled = false;
              }
            });
          }
          if (planesAxisDeleteBtn) {
            planesAxisDeleteBtn.addEventListener('click', async () => {
              const targetId = String(planesAxisCurrentId || '').trim();
              if (!targetId) return;
              if (!window.confirm('¿Eliminar este eje estratégico?')) return;
              planesAxisDeleteBtn.disabled = true;
              try {
                const response = await fetch(`/api/strategic-axes/${encodeURIComponent(targetId)}`, {
                  method: 'DELETE',
                  credentials: 'same-origin',
                });
                const data = await response.json().catch(() => ({}));
                if (!response.ok || data?.success === false) {
                  throw new Error(data?.error || data?.detail || 'No se pudo eliminar el eje.');
                }
                setPlanesAxisMsg('Eje eliminado.');
                planesAxisCurrentId = '';
                await loadTracking();
                fillAxisEditor(null, true);
              } catch (error) {
                setPlanesAxisMsg(error?.message || 'No se pudo eliminar el eje.', true);
              } finally {
                planesAxisDeleteBtn.disabled = false;
              }
            });
          }
          if (planesImportBtn && planesImportFile) {
            planesImportBtn.addEventListener('click', () => planesImportFile.click());
            planesImportFile.addEventListener('change', async () => {
              const file = planesImportFile.files && planesImportFile.files[0] ? planesImportFile.files[0] : null;
              if (!file) return;
              const form = new FormData();
              form.append('file', file);
              setPlanesImportMsg('Importando plantilla estratégica y POA...');
              planesImportBtn.disabled = true;
              try {
                const response = await fetch('/api/planificacion/importar-plan-poa', {
                  method: 'POST',
                  body: form,
                  credentials: 'same-origin'
                });
                const data = await response.json().catch(() => ({}));
                if (!response.ok || data?.success === false) {
                  throw new Error(data?.error || data?.detail || 'No se pudo importar el archivo.');
                }
                const axes = Number(data?.inserted_axes || 0);
                const objectives = Number(data?.inserted_objectives || 0);
                const acts = Number(data?.inserted_activities || 0);
                setPlanesImportMsg(`Importación completada: ${axes} ejes, ${objectives} objetivos y ${acts} actividades.`);
                setTimeout(() => window.location.reload(), 550);
              } catch (error) {
                setPlanesImportMsg(error?.message || 'No se pudo importar el archivo.', true);
              } finally {
                planesImportBtn.disabled = false;
                planesImportFile.value = '';
              }
            });
          }

          const strategicTabButtons = Array.from(document.querySelectorAll('[data-planes-strategic-tab]'));
          const strategicTabPanels = {
            fundamentacion: document.getElementById('planes-tab-panel-fundamentacion'),
            identidad: document.getElementById('planes-tab-panel-identidad'),
            ejes: document.getElementById('planes-tab-panel-ejes'),
            objetivos: document.getElementById('planes-tab-panel-objetivos'),
          };
          const planesOrganigramaHostEl = document.getElementById('planes-organigrama-host');
          const setStrategicTab = (tab, shouldScroll = false) => {
            const target = ['fundamentacion', 'identidad', 'ejes', 'objetivos'].includes(tab) ? tab : 'ejes';
            Object.keys(strategicTabPanels).forEach((key) => {
              const panel = strategicTabPanels[key];
              if (!panel) return;
              const isActive = key === target;
              const panelDisplay = panel.getAttribute('data-panel-display') || 'block';
              panel.classList.toggle('hidden', !isActive);
              panel.style.display = isActive ? panelDisplay : 'none';
            });
            strategicTabButtons.forEach((btn) => {
              const on = (btn.getAttribute('data-planes-strategic-tab') || '') === target;
              btn.classList.toggle('active', on);
              btn.classList.toggle('tab-active', on);
            });
            if (shouldScroll) {
              const targetPanel = strategicTabPanels[target];
              if (targetPanel && typeof targetPanel.scrollIntoView === 'function') {
                targetPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
              }
            }
          };
          strategicTabButtons.forEach((btn) => {
            btn.addEventListener('click', () => setStrategicTab(btn.getAttribute('data-planes-strategic-tab') || 'ejes', true));
          });

          const foundationPanelEl = document.getElementById('planes-tab-panel-fundamentacion');
          const foundationEditorEl = document.getElementById('planes-foundacion-editor');
          const foundationSourceEl = document.getElementById('planes-foundacion-source');
          const foundationUploadBtn = document.getElementById('planes-foundacion-upload-btn');
          const foundationUploadEl = document.getElementById('planes-foundacion-upload');
          const foundationShowSourceEl = document.getElementById('planes-foundacion-show-source');
          const foundationEditBtn = document.getElementById('planes-foundacion-edit');
          const foundationSaveBtn = document.getElementById('planes-foundacion-save');
          const foundationMsgEl = document.getElementById('planes-foundacion-msg');
          const setFoundationMsg = (text, isError = false) => {
            if (!foundationMsgEl) return;
            foundationMsgEl.textContent = text || '';
            foundationMsgEl.style.color = isError ? '#b91c1c' : '#0f3d2e';
          };
          const getFoundationHtml = () => {
            if (foundationShowSourceEl && foundationShowSourceEl.checked && foundationSourceEl) {
              return String(foundationSourceEl.value || '');
            }
            return foundationEditorEl ? String(foundationEditorEl.innerHTML || '') : '';
          };
          const setFoundationHtml = (rawHtml) => {
            const raw = String(rawHtml || '');
            if (foundationEditorEl) foundationEditorEl.innerHTML = raw;
            if (foundationSourceEl) foundationSourceEl.value = raw;
          };
          const syncFoundationSourceMode = () => {
            const show = !!(foundationShowSourceEl && foundationShowSourceEl.checked);
            if (show) {
              if (foundationSourceEl) foundationSourceEl.value = foundationEditorEl ? foundationEditorEl.innerHTML : '';
            } else if (foundationEditorEl && foundationSourceEl) {
              foundationEditorEl.innerHTML = foundationSourceEl.value || '';
            }
            if (foundationSourceEl) foundationSourceEl.style.display = show ? 'block' : 'none';
            if (foundationEditorEl) foundationEditorEl.style.display = show ? 'none' : 'block';
          };
          const setFoundationEditable = (enabled) => {
            if (foundationEditorEl) foundationEditorEl.setAttribute('contenteditable', enabled ? 'true' : 'false');
            if (foundationSourceEl) foundationSourceEl.readOnly = !enabled;
          };
          const loadFoundationFromDb = async () => {
            const response = await fetch('/api/strategic-foundation', { method: 'GET', credentials: 'same-origin' });
            const data = await response.json().catch(() => ({}));
            if (!response.ok || data?.success === false) {
              throw new Error(data?.error || data?.detail || 'No se pudo cargar Fundamentación.');
            }
            setFoundationHtml(String(data?.data?.texto || ''));
            syncFoundationSourceMode();
          };
          const saveFoundationToDb = async () => {
            const response = await fetch('/api/strategic-foundation', {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'same-origin',
              body: JSON.stringify({ texto: getFoundationHtml() }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok || data?.success === false) {
              throw new Error(data?.error || data?.detail || 'No se pudo guardar Fundamentación.');
            }
          };
          if (foundationPanelEl) {
            setFoundationEditable(false);
            syncFoundationSourceMode();
            foundationShowSourceEl && foundationShowSourceEl.addEventListener('change', syncFoundationSourceMode);
            foundationUploadBtn && foundationUploadBtn.addEventListener('click', () => {
              if (foundationUploadEl) foundationUploadEl.click();
            });
            foundationUploadEl && foundationUploadEl.addEventListener('change', async () => {
              const file = foundationUploadEl.files && foundationUploadEl.files[0] ? foundationUploadEl.files[0] : null;
              if (!file) return;
              const text = await file.text().catch(() => '');
              if (!text) {
                setFoundationMsg('No se pudo leer el archivo HTML.', true);
                return;
              }
              setFoundationHtml(text);
              syncFoundationSourceMode();
              setFoundationMsg('HTML cargado correctamente.');
            });
            foundationEditBtn && foundationEditBtn.addEventListener('click', () => {
              setFoundationEditable(true);
              setFoundationMsg('Modo edición habilitado.');
              if (foundationEditorEl && foundationEditorEl.style.display !== 'none') foundationEditorEl.focus();
            });
            foundationSaveBtn && foundationSaveBtn.addEventListener('click', async () => {
              try {
                if (foundationShowSourceEl && foundationShowSourceEl.checked && foundationEditorEl && foundationSourceEl) {
                  foundationEditorEl.innerHTML = foundationSourceEl.value || '';
                }
                await saveFoundationToDb();
                setFoundationEditable(false);
                setFoundationMsg('Fundamentación guardada.');
              } catch (error) {
                setFoundationMsg(error?.message || 'No se pudo guardar Fundamentación.', true);
              }
            });
            document.querySelectorAll('[data-planes-found-cmd]').forEach((btn) => {
              btn.addEventListener('click', () => {
                const cmd = btn.getAttribute('data-planes-found-cmd') || '';
                if (!cmd || !foundationEditorEl) return;
                foundationEditorEl.focus();
                try {
                  document.execCommand(cmd, false, null);
                } catch (_err) {}
              });
            });
            loadFoundationFromDb().catch((error) => {
              setFoundationMsg(error?.message || 'No se pudo cargar Fundamentación.', true);
            });
          }

          const identityPanelEl = document.getElementById('planes-tab-panel-identidad');
          const identityMsgEl = document.getElementById('planes-identidad-msg');
          const missionLinesEl = document.getElementById('planes-identidad-mision-lines');
          const missionHiddenEl = document.getElementById('planes-identidad-mision-hidden');
          const missionFullEl = document.getElementById('planes-identidad-mision-full');
          const missionAddBtn = document.getElementById('planes-identidad-mision-add');
          const missionEditBtn = document.getElementById('planes-identidad-mision-edit');
          const missionSaveBtn = document.getElementById('planes-identidad-mision-save');
          const missionDeleteBtn = document.getElementById('planes-identidad-mision-delete');
          const visionLinesEl = document.getElementById('planes-identidad-vision-lines');
          const visionHiddenEl = document.getElementById('planes-identidad-vision-hidden');
          const visionFullEl = document.getElementById('planes-identidad-vision-full');
          const visionAddBtn = document.getElementById('planes-identidad-vision-add');
          const visionEditBtn = document.getElementById('planes-identidad-vision-edit');
          const visionSaveBtn = document.getElementById('planes-identidad-vision-save');
          const visionDeleteBtn = document.getElementById('planes-identidad-vision-delete');
          const setIdentityMsg = (text, isError = false) => {
            if (!identityMsgEl) return;
            identityMsgEl.textContent = text || '';
            identityMsgEl.style.color = isError ? '#b91c1c' : '#0f3d2e';
          };
          const setupIdentityComposer = (prefix, linesHost, hiddenHost, fullHost, addBtn) => {
            if (!linesHost || !hiddenHost || !fullHost || !addBtn) return null;
            let lines = [{ code: `${prefix}1`, text: '' }];
            let editable = false;
            const cleanCode = (value, idx) => {
              const raw = String(value || '').trim();
              return raw || `${prefix}${idx + 1}`;
            };
            const getLines = () => lines.map((item, idx) => ({
              code: cleanCode(item.code, idx),
              text: String(item.text || '').trim(),
            }));
            const syncOutputs = () => {
              const safe = getLines();
              hiddenHost.innerHTML = '';
              safe.forEach((item, idx) => {
                const codeInput = document.createElement('input');
                codeInput.type = 'hidden';
                codeInput.name = `${prefix}${idx + 1}_code`;
                codeInput.value = item.code;
                hiddenHost.appendChild(codeInput);
                const textInput = document.createElement('input');
                textInput.type = 'hidden';
                textInput.name = `${prefix}${idx + 1}`;
                textInput.value = item.text;
                hiddenHost.appendChild(textInput);
              });
              fullHost.textContent = safe.map((item) => item.text).filter(Boolean).join(' | ');
            };
            const render = () => {
              linesHost.innerHTML = '';
              const safeLines = lines.length ? lines : [{ code: `${prefix}1`, text: '' }];
              safeLines.forEach((item, idx) => {
                const row = document.createElement('div');
                row.className = 'axm-id-row';
                const codeEl = document.createElement('input');
                codeEl.type = 'text';
                codeEl.className = 'axm-id-code';
                codeEl.placeholder = `${prefix}${idx + 1}`;
                codeEl.value = cleanCode(item.code, idx);
                codeEl.readOnly = !editable;
                codeEl.addEventListener('input', () => {
                  lines[idx].code = codeEl.value;
                  syncOutputs();
                });
                const textEl = document.createElement('input');
                textEl.type = 'text';
                textEl.className = 'axm-id-input';
                textEl.placeholder = 'Texto';
                textEl.value = String(item.text || '');
                textEl.readOnly = !editable;
                textEl.addEventListener('input', () => {
                  lines[idx].text = textEl.value;
                  syncOutputs();
                });
                const removeBtn = document.createElement('button');
                removeBtn.type = 'button';
                removeBtn.className = 'axm-id-action delete';
                removeBtn.setAttribute('aria-label', 'Eliminar línea');
                removeBtn.innerHTML = '<img src="/icon/eliminar.svg" alt="">';
                removeBtn.disabled = !editable;
                removeBtn.addEventListener('click', () => {
                  if (!editable) return;
                  lines.splice(idx, 1);
                  if (!lines.length) lines = [{ code: `${prefix}1`, text: '' }];
                  render();
                });
                row.appendChild(codeEl);
                row.appendChild(textEl);
                row.appendChild(removeBtn);
                linesHost.appendChild(row);
              });
              addBtn.disabled = !editable;
              syncOutputs();
            };
            addBtn.addEventListener('click', () => {
              if (!editable) return;
              lines.push({ code: `${prefix}${lines.length + 1}`, text: '' });
              render();
            });
            render();
            return {
              getLines,
              setEditable(flag) {
                editable = !!flag;
                render();
              },
              setLines(next) {
                const rows = Array.isArray(next) ? next : [];
                lines = rows.length
                  ? rows.map((item, idx) => ({
                      code: cleanCode(item && item.code, idx),
                      text: String((item && item.text) || ''),
                    }))
                  : [{ code: `${prefix}1`, text: '' }];
                render();
              },
              clear() {
                lines = [{ code: `${prefix}1`, text: '' }];
                render();
              }
            };
          };
          const missionComposer = setupIdentityComposer('m', missionLinesEl, missionHiddenEl, missionFullEl, missionAddBtn);
          const visionComposer = setupIdentityComposer('v', visionLinesEl, visionHiddenEl, visionFullEl, visionAddBtn);
          const loadIdentityForPlanes = async () => {
            const response = await fetch('/api/strategic-identity', { method: 'GET', credentials: 'same-origin' });
            const data = await response.json().catch(() => ({}));
            if (!response.ok || data?.success === false) {
              throw new Error(data?.error || data?.detail || 'No se pudo cargar Identidad.');
            }
            if (missionComposer) missionComposer.setLines(data?.data?.mision);
            if (visionComposer) visionComposer.setLines(data?.data?.vision);
          };
          const saveIdentityBlock = async (block, lines) => {
            const response = await fetch(`/api/strategic-identity/${encodeURIComponent(block)}`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              credentials: 'same-origin',
              body: JSON.stringify({ lineas: lines }),
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok || data?.success === false) {
              throw new Error(data?.error || data?.detail || 'No se pudo guardar Identidad.');
            }
          };
          const clearIdentityBlock = async (block) => {
            const response = await fetch(`/api/strategic-identity/${encodeURIComponent(block)}`, {
              method: 'DELETE',
              credentials: 'same-origin',
            });
            const data = await response.json().catch(() => ({}));
            if (!response.ok || data?.success === false) {
              throw new Error(data?.error || data?.detail || 'No se pudo limpiar Identidad.');
            }
          };
          if (identityPanelEl) {
            missionEditBtn && missionEditBtn.addEventListener('click', () => {
              if (!missionComposer) return;
              missionComposer.setEditable(true);
              setIdentityMsg('Modo edición habilitado para Misión.');
            });
            missionSaveBtn && missionSaveBtn.addEventListener('click', async () => {
              try {
                const lines = missionComposer ? missionComposer.getLines() : [];
                await saveIdentityBlock('mision', lines);
                if (missionComposer) missionComposer.setEditable(false);
                setIdentityMsg('Misión guardada.');
              } catch (error) {
                setIdentityMsg(error?.message || 'No se pudo guardar Misión.', true);
              }
            });
            missionDeleteBtn && missionDeleteBtn.addEventListener('click', async () => {
              try {
                await clearIdentityBlock('mision');
                if (missionComposer) {
                  missionComposer.clear();
                  missionComposer.setEditable(false);
                }
                setIdentityMsg('Misión limpiada.');
              } catch (error) {
                setIdentityMsg(error?.message || 'No se pudo limpiar Misión.', true);
              }
            });
            visionEditBtn && visionEditBtn.addEventListener('click', () => {
              if (!visionComposer) return;
              visionComposer.setEditable(true);
              setIdentityMsg('Modo edición habilitado para Visión.');
            });
            visionSaveBtn && visionSaveBtn.addEventListener('click', async () => {
              try {
                const lines = visionComposer ? visionComposer.getLines() : [];
                await saveIdentityBlock('vision', lines);
                if (visionComposer) visionComposer.setEditable(false);
                setIdentityMsg('Visión guardada.');
              } catch (error) {
                setIdentityMsg(error?.message || 'No se pudo guardar Visión.', true);
              }
            });
            visionDeleteBtn && visionDeleteBtn.addEventListener('click', async () => {
              try {
                await clearIdentityBlock('vision');
                if (visionComposer) {
                  visionComposer.clear();
                  visionComposer.setEditable(false);
                }
                setIdentityMsg('Visión limpiada.');
              } catch (error) {
                setIdentityMsg(error?.message || 'No se pudo limpiar Visión.', true);
              }
            });
            loadIdentityForPlanes().catch((error) => {
              setIdentityMsg(error?.message || 'No se pudo cargar Identidad.', true);
            });
          }

          const escapeHtml = (value) => String(value == null ? '' : value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');

          const fillList = (listEl, moreEl, items, mapper) => {
            if (!listEl || !moreEl) return;
            if (!Array.isArray(items) || !items.length) {
              listEl.innerHTML = '<li>Sin pendientes</li>';
              moreEl.textContent = '';
              moreEl.style.display = 'none';
              return;
            }
            const visible = items.slice(0, 8);
            listEl.innerHTML = visible.map((item) => `<li>${mapper(item)}</li>`).join('');
            const extra = items.length - visible.length;
            moreEl.textContent = extra > 0 ? `+${extra} más` : '';
            moreEl.style.display = extra > 0 ? 'inline-block' : 'none';
          };
          const renderPendingLabel = (code, name) => `
            <span class="panel__list-item">
              <span class="panel__list-code">${escapeHtml(code || 'Sin código')}</span>
              <span class="panel__list-name">${escapeHtml(name || 'Sin nombre')}</span>
            </span>
          `;

          const renderPlanesTrackingBoard = (axes) => {
            const axisList = Array.isArray(axes) ? axes : [];
            const objectives = axisList.flatMap((axis) => Array.isArray(axis.objetivos) ? axis.objetivos : []);
            const objectiveAxisById = {};
            axisList.forEach((axis) => {
              (Array.isArray(axis.objetivos) ? axis.objetivos : []).forEach((obj) => {
                objectiveAxisById[String(obj.id)] = axis;
              });
            });

            const axisCount = axisList.length;
            const objectiveCount = objectives.length;
            const globalProgress = axisCount
              ? Math.round(axisList.reduce((sum, axis) => sum + Number(axis.avance || 0), 0) / axisCount)
              : 0;
            const objectiveDone = objectives.filter((obj) => Number(obj.avance || 0) >= 100).length;

            const axesNoOwner = axisList.filter((axis) => !String(axis?.responsabilidad_directa || '').trim());
            const objectivesNoOwner = objectives.filter((obj) => !String(obj?.lider || '').trim());

            const missionAxes = axisList.filter((axis) => String(axis.base_code || axis.codigo || '').toLowerCase().startsWith('m'));
            const visionAxes = axisList.filter((axis) => String(axis.base_code || axis.codigo || '').toLowerCase().startsWith('v'));
            const missionProgress = missionAxes.length
              ? Math.round(missionAxes.reduce((sum, axis) => sum + Number(axis.avance || 0), 0) / missionAxes.length)
              : 0;
            const visionProgress = visionAxes.length
              ? Math.round(visionAxes.reduce((sum, axis) => sum + Number(axis.avance || 0), 0) / visionAxes.length)
              : 0;

            const milestones = objectives.flatMap((obj) => {
              if (Array.isArray(obj.hitos) && obj.hitos.length) return obj.hitos;
              return obj.hito ? [{ nombre: obj.hito, logrado: false, fecha_realizacion: '' }] : [];
            });
            const milestonesTotal = milestones.length;
            const milestonesDone = milestones.filter((item) => !!item.logrado).length;
            const milestonesPending = Math.max(0, milestonesTotal - milestonesDone);
            const todayIso = new Date().toISOString().slice(0, 10);
            const milestonesOverdue = milestones.filter((item) => {
              const due = String(item?.fecha_realizacion || '');
              return !item?.logrado && !!due && due < todayIso;
            }).length;
            const milestonesPct = milestonesTotal ? Math.round((milestonesDone * 100) / milestonesTotal) : 0;

            const byId = (id) => document.getElementById(id);
            const setText = (id, value) => { const el = byId(id); if (el) el.textContent = String(value); };

            setText('planes-kpi-progress', `${globalProgress}%`);
            setText('planes-kpi-axes', axisCount);
            setText('planes-kpi-objectives', objectiveCount);
            setText('planes-kpi-objectives-done', objectiveDone);
            setText('planes-mission-progress', `${missionProgress}%`);
            setText('planes-vision-progress', `${visionProgress}%`);
            setText('planes-milestone-total', milestonesTotal);
            setText('planes-milestone-done', milestonesDone);
            setText('planes-milestone-pending', milestonesPending);
            setText('planes-milestone-overdue', milestonesOverdue);
            setText('planes-axes-pending-count', axesNoOwner.length);
            setText('planes-objectives-pending-count', objectivesNoOwner.length);

            const progressFill = byId('planes-progress-fill');
            if (progressFill) progressFill.style.width = `${Math.max(0, Math.min(100, Number(globalProgress) || 0))}%`;
            const milestoneChart = byId('planes-milestone-chart');
            if (milestoneChart) milestoneChart.textContent = `${milestonesPct}%`;
            const milestoneDonut = byId('planes-milestone-donut');
            if (milestoneDonut) milestoneDonut.style.setProperty('--p', String(Math.max(0, Math.min(100, Number(milestonesPct) || 0))));

            fillList(
              byId('planes-axes-pending-list'),
              byId('planes-axes-pending-more'),
              axesNoOwner,
              (axis) => renderPendingLabel(axis.codigo || 'Sin código', axis.nombre || 'Sin nombre')
            );
            fillList(
              byId('planes-objectives-pending-list'),
              byId('planes-objectives-pending-more'),
              objectivesNoOwner,
              (obj) => {
                const parentAxis = objectiveAxisById[String(obj.id)] || {};
                const axisCode = String(parentAxis.codigo || '').trim();
                const code = String(obj.codigo || '').trim();
                const left = code || axisCode || 'Sin código';
                return renderPendingLabel(left, obj.nombre || 'Sin nombre');
              }
            );
          };

          const renderStrategicAxesPanel = (axes) => {
            const host = document.getElementById('planes-ejes-list');
            if (!host) return;
            const axisList = Array.isArray(axes) ? axes : [];
            if (!axisList.length) {
              host.innerHTML = '<div class="text-base-content/60">Sin ejes registrados.</div>';
              return;
            }
            host.innerHTML = axisList.map((axis) => {
              const code = escapeHtml(axis?.codigo || 'Sin código');
              const name = escapeHtml(axis?.nombre || 'Sin nombre');
              const rawOwner = String(axis?.responsabilidad_directa || '').trim();
              const noOwner = !rawOwner;
              const owner = escapeHtml(rawOwner || 'Sin responsable');
              const progress = Math.max(0, Math.min(100, Number(axis?.avance || 0)));
              const objectivesCount = Number(axis?.objetivos_count || (Array.isArray(axis?.objetivos) ? axis.objetivos.length : 0)) || 0;
              const axisId = String(axis?.id || '').trim();
              const active = axisId && axisId === String(planesAxisCurrentId || '');
              const borderClass = active ? 'border-primary bg-base-100' : noOwner ? 'border-error bg-error/5' : 'border-base-300';
              return `
                <button type="button" class="card bg-base-200 border ${borderClass} rounded-xl text-left transition hover:border-primary/30 hover:bg-base-100" data-planes-edit-axis="${axisId}">
                  <div class="card-body p-4">
                    <div class="flex flex-wrap items-start justify-between gap-2">
                      <h4 class="font-semibold text-base-content">${code} - ${name}</h4>
                      <span class="badge badge-outline">${progress}%</span>
                    </div>
                    <div class="text-sm ${noOwner ? 'text-error font-medium' : 'text-base-content/70'}">Responsable: ${owner}</div>
                    <div class="text-sm text-base-content/70">Objetivos: ${objectivesCount}</div>
                  </div>
                </button>
              `;
            }).join('');
            host.querySelectorAll('[data-planes-edit-axis]').forEach((button) => {
              button.addEventListener('click', () => {
                const axisId = String(button.getAttribute('data-planes-edit-axis') || '').trim();
                if (!axisId) return;
                selectAxisForEditing(axisId, true);
                renderStrategicAxesPanel(planesAxesCache);
              });
            });
          };

          const renderStrategicObjectivesPanel = (axes) => {
            const axesHost = document.getElementById('planes-objetivos-axes-list');
            const host = document.getElementById('planes-objetivos-list');
            const titleEl = document.getElementById('planes-objetivos-selected-axis-title');
            const addBtn = document.getElementById('planes-add-objective-btn');
            const objShell = document.getElementById('planes-obj-editor-shell');
            const objTitleEl = document.getElementById('planes-obj-editor-title');
            const objNombreEl = document.getElementById('planes-obj-nombre');
            const objHitoEl = document.getElementById('planes-obj-hito');
            const objLiderEl = document.getElementById('planes-obj-lider');
            const objFiEl = document.getElementById('planes-obj-fecha-inicial');
            const objFfEl = document.getElementById('planes-obj-fecha-final');
            const objMsgEl = document.getElementById('planes-obj-msg');
            const objCancelBtn = document.getElementById('planes-obj-cancel-btn');
            const objSaveBtn = document.getElementById('planes-obj-save-btn');
            const objDeleteBtn = document.getElementById('planes-obj-delete-btn');
            const objKpiSection = document.getElementById('planes-obj-kpi-section');
            const objKpiAddBtn = document.getElementById('planes-obj-kpi-add-btn');
            const objKpiList = document.getElementById('planes-obj-kpi-list');
            if (!host || !axesHost) return;
            let objKpisState = Array.isArray(window.__planesObjectiveKpisState) ? window.__planesObjectiveKpisState : [];

            const setObjKpiSectionOpen = (open) => {
              if (!objKpiSection) return;
              if (open) {
                objKpiSection.setAttribute('open', 'open');
              } else {
                objKpiSection.removeAttribute('open');
              }
            };
            const normalizeObjectiveKpiItem = (item) => ({
              axis_kpi_id: Number(item?.axis_kpi_id || 0) || 0,
              nombre: String(item?.nombre || '').trim(),
            });
            const dedupeObjectiveKpis = (items) => {
              const seen = new Set();
              return (Array.isArray(items) ? items : []).map((item) => normalizeObjectiveKpiItem(item)).filter((item) => {
                const key = Number(item.axis_kpi_id || 0);
                if (key <= 0 || !item.nombre || seen.has(key)) return false;
                seen.add(key);
                return true;
              });
            };
            const getObjectiveAxisEntry = (axisId) => axisList.find((axis) => String(axis?.id || '') === String(axisId || '')) || null;
            const renderObjKpiEditor = (axisId) => {
              if (!objKpiList) return;
              const axisEntry = getObjectiveAxisEntry(axisId);
              const axisKpis = Array.isArray(axisEntry?.kpis) ? axisEntry.kpis : [];
              if (!objKpisState.length) {
                objKpiList.innerHTML = '<div class="text-base-content/60">Sin KPIs seleccionados.</div>';
                return;
              }
              objKpiList.innerHTML = objKpisState.map((item, idx) => {
                const currentId = Number(item?.axis_kpi_id || 0) || 0;
                const takenIds = new Set(
                  objKpisState
                    .filter((entry, entryIdx) => entryIdx !== idx)
                    .map((entry) => Number(entry?.axis_kpi_id || 0) || 0)
                    .filter((id) => id > 0)
                );
                const options = ['<option value="">Selecciona KPI</option>'].concat(
                  axisKpis.filter((kpi) => {
                    const kpiId = Number(kpi?.id || 0) || 0;
                    return kpiId === currentId || !takenIds.has(kpiId);
                  }).map((kpi) => {
                    const kpiId = Number(kpi?.id || 0) || 0;
                    const selected = currentId > 0 && currentId === kpiId ? ' selected' : '';
                    return `<option value="${kpiId}"${selected}>${escapeHtml(String(kpi?.nombre || ''))}</option>`;
                  })
                ).join('');
                return `
                  <article class="rounded-box border border-base-300 bg-base-100 p-4 grid gap-3">
                    <div class="flex items-center justify-between gap-2">
                      <strong>KPI ${idx + 1}</strong>
                      <button type="button" class="btn btn-error btn-xs" data-planes-obj-kpi-remove="${idx}">Eliminar</button>
                    </div>
                    <label class="form-control w-full">
                      <div class="label"><span class="label-text">KPI del eje</span></div>
                      <select class="select select-bordered w-full" data-planes-obj-kpi-select="${idx}">
                        ${options}
                      </select>
                    </label>
                  </article>
                `;
              }).join('');
              objKpiList.querySelectorAll('[data-planes-obj-kpi-select]').forEach((field) => {
                field.addEventListener('change', () => {
                  const idx = Number(field.getAttribute('data-planes-obj-kpi-select') || -1);
                  const selectedId = Number(field.value || 0) || 0;
                  if (idx < 0 || !objKpisState[idx]) return;
                  const selectedKpi = axisKpis.find((item) => Number(item?.id || 0) === selectedId) || null;
                  objKpisState[idx] = normalizeObjectiveKpiItem({
                    axis_kpi_id: selectedId,
                    nombre: selectedKpi?.nombre || '',
                  });
                  objKpisState = dedupeObjectiveKpis(objKpisState);
                  window.__planesObjectiveKpisState = objKpisState;
                  renderObjKpiEditor(axisId);
                });
              });
              objKpiList.querySelectorAll('[data-planes-obj-kpi-remove]').forEach((btn) => {
                btn.addEventListener('click', () => {
                  const idx = Number(btn.getAttribute('data-planes-obj-kpi-remove') || -1);
                  if (idx < 0) return;
                  objKpisState.splice(idx, 1);
                  window.__planesObjectiveKpisState = objKpisState;
                  renderObjKpiEditor(axisId);
                });
              });
            };

            const showObjForm = (show) => {
              if (objShell) objShell.style.display = show ? '' : 'none';
              if (host) host.style.display = show ? 'none' : '';
            };

            const fillObjForm = async (obj, axisId, isNew) => {
              const axisEntry = getObjectiveAxisEntry(axisId);
              if (objTitleEl) objTitleEl.textContent = isNew ? 'Nuevo objetivo estratégico' : 'Editar objetivo estratégico';
              if (objNombreEl) objNombreEl.value = isNew ? '' : (obj?.nombre || '');
              if (objHitoEl) objHitoEl.value = isNew ? '' : (obj?.hito || '');
              if (objLiderEl) objLiderEl.value = isNew ? '' : (obj?.lider || '');
              if (objFiEl) objFiEl.value = isNew ? '' : (obj?.fecha_inicial || '');
              if (objFfEl) objFfEl.value = isNew ? '' : (obj?.fecha_final || '');
              objKpisState = dedupeObjectiveKpis(Array.isArray(obj?.kpis) ? obj.kpis : []);
              window.__planesObjectiveKpisState = objKpisState;
              renderObjKpiEditor(axisId);
              setObjKpiSectionOpen(false);
              if (objKpiAddBtn) {
                const availableCount = Array.isArray(axisEntry?.kpis) ? axisEntry.kpis.length : 0;
                objKpiAddBtn.disabled = availableCount <= objKpisState.length;
              }
              if (objMsgEl) objMsgEl.textContent = '';
              if (objDeleteBtn) objDeleteBtn.style.display = isNew ? 'none' : '';
              window.__planesEditingObjId = isNew ? null : (obj?.id || null);
              window.__planesEditingObjAxisId = axisId;
              if (typeof window.__planesLoadObjLiderOptions === 'function') {
                await window.__planesLoadObjLiderOptions(axisId);
              }
              showObjForm(true);
            };

            const axisList = Array.isArray(axes) ? axes : [];

            if (objCancelBtn) objCancelBtn.onclick = () => showObjForm(false);

            if (objSaveBtn) {
              objSaveBtn.onclick = async () => {
                const axisId = window.__planesEditingObjAxisId;
                const objId = window.__planesEditingObjId;
                const nombre = (objNombreEl?.value || '').trim();
                if (!nombre) { if (objMsgEl) objMsgEl.textContent = 'El nombre es obligatorio.'; return; }
                const payload = {
                  nombre,
                  hito: (objHitoEl?.value || '').trim(),
                  lider: (objLiderEl?.value || '').trim(),
                  fecha_inicial: objFiEl?.value || null,
                  fecha_final: objFfEl?.value || null,
                  kpis: dedupeObjectiveKpis(objKpisState),
                };
                if (objMsgEl) objMsgEl.textContent = 'Guardando...';
                try {
                  const url = objId ? `/api/strategic-objectives/${objId}` : `/api/strategic-axes/${axisId}/objectives`;
                  const r = await fetch(url, {
                    method: objId ? 'PUT' : 'POST',
                    credentials: 'same-origin',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                  });
                  const resp = await r.json();
                  if (resp?.success) {
                    showObjForm(false);
                    const lr = await fetch('/api/strategic-axes', { method: 'GET', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' } });
                    const lp = await lr.json();
                    const updatedAxes = (lp?.success && Array.isArray(lp.data)) ? lp.data : [];
                    planesAxesCache = updatedAxes;
                    renderPlanesTrackingBoard(updatedAxes);
                    renderStrategicAxesPanel(updatedAxes);
                    renderStrategicObjectivesPanel(updatedAxes);
                  } else {
                    if (objMsgEl) objMsgEl.textContent = resp?.error || 'Error al guardar.';
                  }
                } catch (_) {
                  if (objMsgEl) objMsgEl.textContent = 'Error de red.';
                }
              };
            }

            if (objDeleteBtn) {
              objDeleteBtn.onclick = async () => {
                const objId = window.__planesEditingObjId;
                if (!objId) return;
                if (!confirm('¿Eliminar este objetivo estratégico?')) return;
                try {
                  const r = await fetch(`/api/strategic-objectives/${objId}`, { method: 'DELETE', credentials: 'same-origin' });
                  const resp = await r.json();
                  if (resp?.success) {
                    showObjForm(false);
                    const lr = await fetch('/api/strategic-axes', { method: 'GET', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' } });
                    const lp = await lr.json();
                    const updatedAxes = (lp?.success && Array.isArray(lp.data)) ? lp.data : [];
                    planesAxesCache = updatedAxes;
                    renderPlanesTrackingBoard(updatedAxes);
                    renderStrategicAxesPanel(updatedAxes);
                    renderStrategicObjectivesPanel(updatedAxes);
                  }
                } catch (_) {}
              };
            }
            if (objKpiAddBtn) {
              objKpiAddBtn.onclick = () => {
                const axisId = window.__planesEditingObjAxisId;
                const axisEntry = getObjectiveAxisEntry(axisId);
                const axisKpis = Array.isArray(axisEntry?.kpis) ? axisEntry.kpis : [];
                const takenIds = new Set(objKpisState.map((item) => Number(item?.axis_kpi_id || 0) || 0).filter((id) => id > 0));
                const availableKpis = axisKpis.filter((item) => !takenIds.has(Number(item?.id || 0) || 0));
                if (!availableKpis.length) {
                  if (objMsgEl) objMsgEl.textContent = 'Este eje no tiene KPIs disponibles.';
                  return;
                }
                const firstKpi = availableKpis[0] || null;
                objKpisState.push(normalizeObjectiveKpiItem({
                  axis_kpi_id: Number(firstKpi?.id || 0) || 0,
                  nombre: String(firstKpi?.nombre || ''),
                }));
                window.__planesObjectiveKpisState = objKpisState;
                setObjKpiSectionOpen(true);
                renderObjKpiEditor(axisId);
              };
            }

            if (addBtn) {
              addBtn.onclick = () => {
                const selected = axisList.find((axis) => String(axis?.id || '') === String(window.__planesSelectedAxisId || '')) || axisList[0] || null;
                if (!selected) return;
                fillObjForm(null, selected.id, true);
              };
            }
            if (!axisList.length) {
              axesHost.innerHTML = '<div class="text-base-content/60">Sin ejes registrados.</div>';
              if (titleEl) titleEl.textContent = 'Objetivos: sin eje seleccionado';
              host.innerHTML = '<div class="text-base-content/60">Sin objetivos registrados.</div>';
              return;
            }
            let selectedAxisId = window.__planesSelectedAxisId || null;
            if (!selectedAxisId || !axisList.some((axis) => String(axis?.id || '') === String(selectedAxisId))) {
              selectedAxisId = axisList[0]?.id || null;
              window.__planesSelectedAxisId = selectedAxisId;
            }

            axesHost.innerHTML = axisList.map((axis) => {
              const axisId = String(axis?.id || '');
              const on = String(selectedAxisId) === axisId;
              const axisCode = escapeHtml(axis?.codigo || 'Sin código');
              const axisName = escapeHtml(axis?.nombre || 'Sin nombre');
              return `<button type="button" class="planes-obj-axis-btn ${on ? 'active' : ''}" data-planes-axis-id="${axisId}">${axisCode}: ${axisName}</button>`;
            }).join('');
            axesHost.querySelectorAll('[data-planes-axis-id]').forEach((btn) => {
              btn.addEventListener('click', () => {
                window.__planesSelectedAxisId = btn.getAttribute('data-planes-axis-id') || null;
                renderStrategicObjectivesPanel(axisList);
              });
            });

            const selectedAxis = axisList.find((axis) => String(axis?.id || '') === String(selectedAxisId)) || axisList[0];
            const selectedAxisCode = escapeHtml(selectedAxis?.codigo || 'Sin código');
            const selectedAxisName = escapeHtml(selectedAxis?.nombre || 'Sin nombre');
            if (titleEl) titleEl.textContent = `Objetivos: ${selectedAxisCode}: ${selectedAxisName}`;

            const objectives = Array.isArray(selectedAxis?.objetivos) ? selectedAxis.objetivos : [];
            if (!objectives.length) {
              host.innerHTML = '<div class="text-base-content/60">Este eje no tiene objetivos registrados.</div>';
              return;
            }
            host.innerHTML = objectives.map((obj) => {
              const name = escapeHtml(obj?.nombre || 'Sin nombre');
              const code = escapeHtml(obj?.codigo || 'Sin código');
              const hito = escapeHtml(obj?.hito || 'N/D');
              const avance = Math.max(0, Math.min(100, Number(obj?.avance || 0)));
              const fechaInicio = escapeHtml(obj?.fecha_inicio || obj?.fecha_inicial || obj?.inicio || 'N/D');
              const fechaFin = escapeHtml(obj?.fecha_fin || obj?.fecha_final || obj?.fin || 'N/D');
              const rawLider = String(obj?.lider || '').trim();
              const noLider = !rawLider;
              const lider = escapeHtml(rawLider || 'Sin responsable asignado');
              const kpiNames = Array.isArray(obj?.kpis)
                ? obj.kpis.map((item) => String(item?.nombre || '').trim()).filter(Boolean)
                : [];
              const kpiLabel = kpiNames.length ? escapeHtml(kpiNames.join(', ')) : 'Sin KPIs';
              return `
                <button type="button" class="planes-obj-item${noLider ? ' planes-obj-item--no-owner' : ''}" data-planes-objective-id="${String(obj?.id || '')}" data-planes-objective-axis-id="${String(selectedAxis?.id || '')}">
                  <h5>${name}</h5>
                  <div class="planes-obj-code">${code}</div>
                  <div class="planes-obj-meta">Hito: ${hito} · Avance: ${avance}% · Fecha inicial: ${fechaInicio} · Fecha final: ${fechaFin}</div>
                  <div class="text-sm ${noLider ? 'text-error font-medium' : 'text-base-content/70'}">Responsable: ${lider}</div>
                  <div class="text-sm text-base-content/70">KPIs: ${kpiLabel}</div>
                </button>
              `;
            }).join('');
            host.querySelectorAll('[data-planes-objective-id]').forEach((button) => {
              button.addEventListener('click', () => {
                const objectiveId = String(button.getAttribute('data-planes-objective-id') || '').trim();
                const btnAxisId = String(button.getAttribute('data-planes-objective-axis-id') || '').trim();
                if (!objectiveId) return;
                const axisEntry = axisList.find((a) => String(a?.id || '') === btnAxisId);
                const obj = Array.isArray(axisEntry?.objetivos)
                  ? axisEntry.objetivos.find((o) => String(o?.id || '') === objectiveId)
                  : null;
                fillObjForm(obj, btnAxisId, false);
              });
            });
          };

          const loadTracking = async () => {
            try {
              const response = await fetch('/api/strategic-axes', {
                method: 'GET',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json' },
              });
              const payload = await response.json();
              const axes = (payload && payload.success && Array.isArray(payload.data)) ? payload.data : [];
              planesAxesCache = axes;
              renderPlanesTrackingBoard(axes);
              renderStrategicAxesPanel(axes);
              renderStrategicObjectivesPanel(axes);
              const openMode = String(planesQuery.get('open') || '').trim().toLowerCase();
              const axisIdFromQuery = String(planesQuery.get('axis_id') || '').trim();
              setView('list');
              renderStrategicAxesPanel(axes);
            } catch (_err) {
              planesAxesCache = [];
              renderPlanesTrackingBoard([]);
              renderStrategicAxesPanel([]);
              renderStrategicObjectivesPanel([]);
              setView('list');
              fillAxisEditor(null, true);
            }
          };

          ['planes-axes-pending-more', 'planes-objectives-pending-more'].forEach((id) => {
            const el = document.getElementById(id);
            if (!el) return;
            el.addEventListener('click', (event) => event.preventDefault());
          });

          (async () => {
            const makeCombo = (inputEl, dropdownEl, getOptions) => {
              if (!inputEl || !dropdownEl) return;
              let activeIdx = -1;
              const open = (items) => {
                dropdownEl.innerHTML = '';
                activeIdx = -1;
                if (!items.length) { dropdownEl.classList.remove('open'); return; }
                items.forEach((text, i) => {
                  const li = document.createElement('li');
                  li.textContent = text;
                  li.setAttribute('role', 'option');
                  li.addEventListener('mousedown', (e) => {
                    e.preventDefault();
                    inputEl.value = text;
                    dropdownEl.classList.remove('open');
                    inputEl.dispatchEvent(new Event('combo-select', { bubbles: true }));
                  });
                  dropdownEl.appendChild(li);
                });
                dropdownEl.classList.add('open');
              };
              const filter = () => {
                const q = inputEl.value.trim().toLowerCase();
                const opts = getOptions();
                open(q ? opts.filter((o) => o.toLowerCase().includes(q)) : opts);
              };
              inputEl.addEventListener('input', filter);
              inputEl.addEventListener('focus', filter);
              inputEl.addEventListener('keydown', (e) => {
                const items = dropdownEl.querySelectorAll('li');
                if (!items.length) return;
                if (e.key === 'ArrowDown') {
                  e.preventDefault();
                  activeIdx = Math.min(activeIdx + 1, items.length - 1);
                } else if (e.key === 'ArrowUp') {
                  e.preventDefault();
                  activeIdx = Math.max(activeIdx - 1, 0);
                } else if (e.key === 'Enter' && activeIdx >= 0) {
                  e.preventDefault();
                  inputEl.value = items[activeIdx].textContent;
                  dropdownEl.classList.remove('open');
                  inputEl.dispatchEvent(new Event('combo-select', { bubbles: true }));
                  return;
                } else if (e.key === 'Escape') {
                  dropdownEl.classList.remove('open'); return;
                } else { return; }
                items.forEach((li, i) => li.setAttribute('aria-selected', i === activeIdx ? 'true' : 'false'));
                items[activeIdx]?.scrollIntoView({ block: 'nearest' });
              });
              inputEl.addEventListener('blur', () => {
                setTimeout(() => dropdownEl.classList.remove('open'), 150);
              });
            };

            try {
              const [depRes, colRes] = await Promise.all([
                fetch('/api/inicio/departamentos', { credentials: 'same-origin', headers: { Accept: 'application/json' } }),
                fetch('/api/colaboradores', { credentials: 'same-origin', headers: { Accept: 'application/json' } }),
              ]);
              const depPayload = await depRes.json();
              const colPayload = await colRes.json();
              const departamentos = (Array.isArray(depPayload?.data) ? depPayload.data : [])
                .map((d) => String(d?.name || '').trim()).filter(Boolean).sort((a, b) => a.localeCompare(b));
              window.__planesColaboradoresAll = Array.isArray(colPayload) ? colPayload : (Array.isArray(colPayload?.data) ? colPayload.data : []);

              const getResponsableOptions = () => {
                const dep = String(planesAxisDepartamento?.value || '').trim().toLowerCase();
                const all = window.__planesColaboradoresAll || [];
                const filtered = dep
                  ? all.filter((c) => String(c?.departamento || '').trim().toLowerCase() === dep)
                  : all;
                return filtered.map((c) => String(c?.nombre || '').trim()).filter(Boolean).sort((a, b) => a.localeCompare(b));
              };

              const depDropdown = document.getElementById('planes-axis-departamento-dropdown');
              const colDropdown = document.getElementById('planes-axis-responsable-dropdown');
              makeCombo(planesAxisDepartamento, depDropdown, () => departamentos);
              makeCombo(planesAxisResponsable, colDropdown, getResponsableOptions);

              const fillResponsables = (depName) => {
                window.__planesFillResponsables_dep = depName;
              };
              window.__planesFillResponsables = fillResponsables;

              if (planesAxisDepartamento) {
                planesAxisDepartamento.addEventListener('combo-select', () => {
                  if (planesAxisResponsable) planesAxisResponsable.value = '';
                });
                planesAxisDepartamento.addEventListener('input', () => {
                  if (planesAxisResponsable) planesAxisResponsable.value = '';
                });
              }

              // Objective lider combo (options loaded dynamically per axis)
              window.__planesObjLiderOptions = [];
              const objLiderInput = document.getElementById('planes-obj-lider');
              const objLiderDropdown = document.getElementById('planes-obj-lider-dropdown');
              makeCombo(objLiderInput, objLiderDropdown, () => window.__planesObjLiderOptions || []);

              window.__planesLoadObjLiderOptions = async (axisId) => {
                if (!axisId) { window.__planesObjLiderOptions = []; return; }
                try {
                  const r = await fetch(`/api/strategic-axes/${axisId}/collaborators`, {
                    credentials: 'same-origin',
                    headers: { Accept: 'application/json' },
                  });
                  const payload = await r.json();
                  const names = Array.isArray(payload?.data) ? payload.data : (Array.isArray(payload) ? payload : []);
                  window.__planesObjLiderOptions = names
                    .map((n) => (typeof n === 'string' ? n : String(n?.nombre || n || '')))
                    .filter(Boolean)
                    .sort((a, b) => a.localeCompare(b));
                } catch (_) { window.__planesObjLiderOptions = []; }
              };
            } catch (_err) {}
          })();

          loadTracking();
          setStrategicTab(planesQuery.get('tab') || 'fundamentacion');
          setView(planesQuery.get('view') === 'kanban' || planesQuery.get('view') === 'organigrama' ? planesQuery.get('view') : 'list');
        })();
