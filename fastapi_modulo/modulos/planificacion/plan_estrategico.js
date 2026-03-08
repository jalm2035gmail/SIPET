(function () {
          const buttons = Array.from(document.querySelectorAll('[data-planes-view]'));
          const panels = {
            list: document.getElementById('planes-view-list'),
            kanban: document.getElementById('planes-view-kanban'),
            organigrama: document.getElementById('planes-view-organigrama'),
          };
          function setView(view) {
            const target = ['list', 'kanban', 'organigrama'].includes(view) ? view : 'list';
            Object.keys(panels).forEach((key) => {
              const panel = panels[key];
              if (!panel) return;
              panel.classList.toggle('hidden', key !== target);
            });
            buttons.forEach((btn) => {
              btn.classList.toggle('active', (btn.getAttribute('data-planes-view') || '') === target);
            });
            if (target === 'organigrama') {
              renderStrategicTree(planesOrganigramaHostEl, { inline: true });
            }
            document.dispatchEvent(new CustomEvent('backend-view-change', { detail: { view: target } }));
          }
          buttons.forEach((btn) => {
            btn.addEventListener('click', () => setView(btn.getAttribute('data-planes-view') || 'list'));
          });

          const planesAddAxisBtn = document.getElementById('planes-add-axis-btn');
          const planesImportBtn = document.getElementById('planes-import-csv-btn');
          const planesImportFile = document.getElementById('planes-import-csv-file');
          const planesImportMsg = document.getElementById('planes-import-csv-msg');
          const setPlanesImportMsg = (text, isError = false) => {
            if (!planesImportMsg) return;
            planesImportMsg.textContent = text || '';
            planesImportMsg.style.color = isError ? '#b91c1c' : '#0f3d2e';
          };
          if (planesAddAxisBtn) {
            planesAddAxisBtn.addEventListener('click', () => {
              setStrategicTab('ejes', true);
              const ejesPanel = document.getElementById('planes-tab-panel-ejes');
              const ejesLink = ejesPanel ? ejesPanel.querySelector('a[href="/ejes-estrategicos"]') : null;
              if (ejesLink) {
                ejesLink.focus();
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
              const owner = escapeHtml(axis?.responsabilidad_directa || 'Sin responsable');
              const progress = Math.max(0, Math.min(100, Number(axis?.avance || 0)));
              const objectivesCount = Number(axis?.objetivos_count || (Array.isArray(axis?.objetivos) ? axis.objetivos.length : 0)) || 0;
              return `
                <article class="card bg-base-200 border border-base-300 rounded-xl">
                  <div class="card-body p-4">
                    <div class="flex flex-wrap items-start justify-between gap-2">
                      <h4 class="font-semibold text-base-content">${code} - ${name}</h4>
                      <span class="badge badge-outline">${progress}%</span>
                    </div>
                    <div class="text-sm text-base-content/70">Responsable: ${owner}</div>
                    <div class="text-sm text-base-content/70">Objetivos: ${objectivesCount}</div>
                  </div>
                </article>
              `;
            }).join('');
          };

          const renderStrategicObjectivesPanel = (axes) => {
            const axesHost = document.getElementById('planes-objetivos-axes-list');
            const host = document.getElementById('planes-objetivos-list');
            const titleEl = document.getElementById('planes-objetivos-selected-axis-title');
            const addBtn = document.getElementById('planes-add-objective-btn');
            if (!host || !axesHost) return;
            const axisList = Array.isArray(axes) ? axes : [];
            if (addBtn) {
              addBtn.onclick = () => {
                const selected = axisList.find((axis) => String(axis?.id || '') === String(window.__planesSelectedAxisId || '')) || axisList[0] || null;
                const axisId = selected && selected.id != null ? String(selected.id) : '';
                const qs = new URLSearchParams();
                qs.set('tab', 'objetivos');
                qs.set('open', 'objective');
                if (axisId) qs.set('axis_id', axisId);
                window.location.href = `/ejes-estrategicos?${qs.toString()}`;
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
              const fechaInicio = escapeHtml(obj?.fecha_inicio || obj?.inicio || 'N/D');
              const fechaFin = escapeHtml(obj?.fecha_fin || obj?.fin || 'N/D');
              return `
                <button type="button" class="planes-obj-item" data-planes-objective-id="${String(obj?.id || '')}" data-planes-objective-axis-id="${String(selectedAxis?.id || '')}">
                  <h5>${name}</h5>
                  <div class="planes-obj-code">${code}</div>
                  <div class="planes-obj-meta">Hito: ${hito} · Avance: ${avance}% · Fecha inicial: ${fechaInicio} · Fecha final: ${fechaFin}</div>
                </button>
              `;
            }).join('');
            host.querySelectorAll('[data-planes-objective-id]').forEach((button) => {
              button.addEventListener('click', () => {
                const objectiveId = String(button.getAttribute('data-planes-objective-id') || '').trim();
                if (!objectiveId) return;
                const qs = new URLSearchParams();
                qs.set('objective_id', objectiveId);
                window.location.href = `/poa?${qs.toString()}`;
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
              renderPlanesTrackingBoard(axes);
              renderStrategicAxesPanel(axes);
              renderStrategicObjectivesPanel(axes);
            } catch (_err) {
              renderPlanesTrackingBoard([]);
              renderStrategicAxesPanel([]);
              renderStrategicObjectivesPanel([]);
            }
          };

          ['planes-axes-pending-more', 'planes-objectives-pending-more'].forEach((id) => {
            const el = document.getElementById(id);
            if (!el) return;
            el.addEventListener('click', (event) => event.preventDefault());
          });

          loadTracking();
          setStrategicTab('fundamentacion');
          setView('list');
        })();
