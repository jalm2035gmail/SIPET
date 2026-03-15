(function() {
    var puestos = [];
    var areas = (window.__PUESTOS_INIT__ && window.__PUESTOS_INIT__.areas) || [];
    var plOrgLibPromise = null;
    var plOrgChart = null;
    var plCurrentView = 'form';
    var plLastSavedId = '';
    var plFilters = { search: '', nivel: '' };
    var plHabCatalog = {};
    var plHabIndex = {};
    var plHabCatIndex = {};
    var plFormHab = { blandas: [], duras: [] };
    var _HAB_SOFT_KEYS = [
        'comunicacion_interpersonales',
        'liderazgo_gestion',
        'liderazgo_equipos',
        'resolucion_pensamiento',
        'organizacion_autogestion'
    ];
    var _HAB_HARD_KEYS = [
        'informatica_tecnologia_general',
        'tecnologias_informacion_it',
        'diseno_multimedia',
        'marketing_ventas_comunicacion',
        'finanzas_contabilidad_administracion',
        'logistica_produccion_operaciones',
        'idiomas_duros',
        'sector_salud',
        'sector_legal',
        'habilidades_manuales_tecnicas'
    ];
    var _HAB_CAT_LABELS = {
        'comunicacion_interpersonales': 'Comunicación e interpersonales',
        'liderazgo_gestion': 'Liderazgo y gestión',
        'liderazgo_equipos': 'Liderazgo de equipos',
        'resolucion_pensamiento': 'Resolución y pensamiento',
        'organizacion_autogestion': 'Organización y autogestión',
        'informatica_tecnologia_general': 'Informática y tecnología general',
        'tecnologias_informacion_it': 'Tecnologías de la información (IT)',
        'diseno_multimedia': 'Diseño y multimedia',
        'marketing_ventas_comunicacion': 'Marketing, ventas y comunicación',
        'finanzas_contabilidad_administracion': 'Finanzas, contabilidad y administración',
        'logistica_produccion_operaciones': 'Logística, producción y operaciones',
        'idiomas_duros': 'Idiomas',
        'sector_salud': 'Sector salud',
        'sector_legal': 'Sector legal',
        'habilidades_manuales_tecnicas': 'Habilidades manuales y técnicas'
    };
    var _HAB_CAT_ICONS = {
        'comunicacion_interpersonales': '🗣️',
        'liderazgo_gestion': '🌟',
        'liderazgo_equipos': '👥',
        'resolucion_pensamiento': '🧠',
        'organizacion_autogestion': '📅',
        'informatica_tecnologia_general': '💻',
        'tecnologias_informacion_it': '📡',
        'diseno_multimedia': '🎨',
        'marketing_ventas_comunicacion': '📈',
        'finanzas_contabilidad_administracion': '💵',
        'logistica_produccion_operaciones': '🚚',
        'idiomas_duros': '🌐',
        'sector_salud': '💊',
        'sector_legal': '⚖️',
        'habilidades_manuales_tecnicas': '🔨'
    };

    function setAreaOptions(selectedValue) {
        var sel = document.getElementById('pl-area');
        if (!sel) return;
        var selected = String(selectedValue || sel.value || '').trim();
        var catalog = [];
        (areas || []).forEach(function(a) {
            var name = String(a || '').trim();
            if (name && catalog.indexOf(name) === -1) catalog.push(name);
        });
        // Compatibilidad: incluir áreas de puestos existentes (si catálogo de departamentos viene vacío/parcial).
        (puestos || []).forEach(function(p) {
            var area = String((p && p.area) || '').trim();
            if (area && catalog.indexOf(area) === -1) catalog.push(area);
        });
        catalog.sort(function(a, b) { return a.localeCompare(b, 'es'); });
        sel.innerHTML = '<option value="">— Sin área asignada —</option>';
        if (!catalog.length) {
            var empty = document.createElement('option');
            empty.value = '';
            empty.textContent = '— No hay áreas registradas —';
            sel.appendChild(empty);
        } else {
            catalog.forEach(function(a) {
                var o = document.createElement('option');
                o.value = a;
                o.textContent = a;
                sel.appendChild(o);
            });
        }
        if (selected) {
            var exists = catalog.indexOf(selected) !== -1;
            sel.value = exists ? selected : '';
        } else {
            sel.value = '';
        }
    }

    function getFilteredPuestos() {
        var search = String(plFilters.search || '').trim().toLowerCase();
        var nivel = String(plFilters.nivel || '').trim().toLowerCase();
        return (puestos || []).filter(function(p) {
            var pNivel = String((p && p.nivel) || '').trim().toLowerCase();
            var hay = [
                p && p.nombre,
                p && p.area,
                p && p.nivel,
                p && p.descripcion
            ].map(function(v) { return String(v || '').toLowerCase(); }).join(' ');
            if (search && hay.indexOf(search) === -1) return false;
            if (nivel && pNivel !== nivel) return false;
            return true;
        });
    }

    function getOrderedPuestos(items) {
        var rows = Array.isArray(items) ? items.slice() : [];
        rows.sort(function(a, b) {
            var aId = String((a && a.id) || '');
            var bId = String((b && b.id) || '');
            var savedId = String(plLastSavedId || '');
            if (savedId) {
                if (aId === savedId && bId !== savedId) return -1;
                if (bId === savedId && aId !== savedId) return 1;
            }
            var aName = String((a && a.nombre) || '').trim();
            var bName = String((b && b.nombre) || '').trim();
            return aName.localeCompare(bName, 'es', { sensitivity: 'MAIN' });
        });
        return rows;
    }

    function loadAreas() {
        var fallbackAreas = Array.isArray(areas) ? areas.slice() : [];
        return fetch('/api/inicio/departamentos')
            .then(function(r){ return r.json(); })
            .then(function(res){
                var payload = (res && res.data) || [];
                var fetchedAreas = (payload || []).map(function(a){
                    return (a && (a.name || a.nombre || a.area || a.code || '')) || '';
                }).filter(function(v){ return String(v || '').trim() !== ''; });
                if (fetchedAreas.length) {
                    areas = fetchedAreas;
                } else {
                    areas = fallbackAreas;
                }
                setAreaOptions();
            })
            .catch(function() {
                areas = fallbackAreas;
                setAreaOptions();
            });
    }

    function setSaveMessage(text, isError) {
        var ok = document.getElementById('pl-msg');
        var err = document.getElementById('pl-msg-error');
        if (ok) ok.style.display = 'none';
        if (err) {
            err.style.display = 'none';
            err.textContent = '';
        }
        if (!text) return;
        var target = isError ? err : ok;
        if (!target) return;
        target.textContent = text;
        target.style.display = 'inline';
        if (!isError) {
            setTimeout(function() {
                if (target.textContent === text) target.style.display = 'none';
            }, 2200);
        }
    }

    // Load puestos
    function loadPuestos() {
        return fetch('/api/puestos-laborales')
            .then(function(r){ return r.json(); })
            .then(function(res){
                puestos = (res && Array.isArray(res.data)) ? res.data : [];
                renderTable();
                return puestos;
            })
            .catch(function() {
                puestos = [];
                renderTable();
                return puestos;
            });
    }

    function renderTable() {
        var tbody = document.getElementById('pl-tbody');
        var cnt = document.getElementById('pl-count');
        if (!tbody) return;
        var visiblePuestos = getOrderedPuestos(getFilteredPuestos());
        if (cnt) cnt.textContent = visiblePuestos.length ? '(' + visiblePuestos.length + ')' : '';
        setAreaOptions();
        if (!visiblePuestos.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="pl-empty">No hay puestos registrados aún.</td></tr>';
            return;
        }
        tbody.innerHTML = '';
        visiblePuestos.forEach(function(p) {
            var tr = document.createElement('tr');
            tr.className = 'cursor-pointer hover';
            tr.innerHTML =
                '<td><strong>' + _esc(p.nombre) + '</strong></td>' +
                '<td class="area-cell">' + _esc(p.area || '—') + '</td>' +
                '<td class="area-cell">' + _esc(p.nivel || '—') + '</td>' +
                '<td class="desc-cell">' + _esc(p.descripcion || '—') + '</td>' +
                '<td class="actions-cell">' +
                    '<div class="flex items-center justify-end gap-1">' +
                        '<button type="button" class="pl-act-btn edit pl-row-edit" data-id="' + _esc(p.id) + '" aria-label="Editar" title="Editar">' +
                            '<span class="pl-act-btn-icon" aria-hidden="true" style="--pl-act-icon:url(\'/templates/icon/boton/editar.svg\')"></span>' +
                        '</button>' +
                        '<button type="button" class="pl-act-btn del pl-row-del" data-id="' + _esc(p.id) + '" aria-label="Eliminar" title="Eliminar">' +
                            '<span class="pl-act-btn-icon" aria-hidden="true" style="--pl-act-icon:url(\'/templates/icon/boton/eliminar.svg\')"></span>' +
                        '</button>' +
                    '</div>' +
                '</td>';
            tr.addEventListener('click', function() {
                startEdit(p.id);
                setPlView('form');
            });
            tbody.appendChild(tr);
        });
        tbody.querySelectorAll('.pl-row-edit').forEach(function(btn) {
            btn.addEventListener('click', function(ev) {
                ev.stopPropagation();
                startEdit(btn.getAttribute('data-id'));
                setPlView('form');
            });
        });
        tbody.querySelectorAll('.pl-row-del').forEach(function(btn) {
            btn.addEventListener('click', function(ev) {
                ev.stopPropagation();
                deletePuesto(btn.getAttribute('data-id'));
            });
        });
        if (plCurrentView === 'kanban') renderKanbanView();
        if (plCurrentView === 'organigrama') renderOrganigramaView();
    }

    function renderKanbanView() {
        var host = document.getElementById('pl-kanban-host');
        if (!host) return;
        var groups = { 'Sin área': [] };
        getOrderedPuestos(getFilteredPuestos()).forEach(function(p) {
            var area = String((p && p.area) || '').trim() || 'Sin área';
            if (!groups[area]) groups[area] = [];
            groups[area].push(p);
        });
        var html = Object.keys(groups).sort(function(a, b) { return a.localeCompare(b, 'es'); }).map(function(name) {
            var cards = groups[name].map(function(p) {
                var habCount = (p.habilidades_requeridas || []).length;
                var colCount = (p.colaboradores_asignados || []).length;
                return '<article class="rounded-box border border-MAIN-300 bg-MAIN-100 p-3 grid gap-1">' +
                    '<strong class="text-MAIN-content">' + _esc(p.nombre || '—') + '</strong>' +
                    '<span class="text-sm text-MAIN-content/70">' + _esc(p.nivel || 'Sin nivel') + '</span>' +
                    '<span class="text-sm text-MAIN-content/60">' + _esc(p.descripcion || 'Sin descripción') + '</span>' +
                    '<div class="flex items-center gap-2 mt-2">' +
                        '<span class="badge badge-outline badge-sm">Hab: ' + String(habCount || 0) + '</span>' +
                        '<span class="badge badge-outline badge-sm">Col: ' + String(colCount || 0) + '</span>' +
                    '</div>' +
                    '<div class="card-actions justify-end mt-2">' +
                        '<button type="button" class="btn btn-ghost btn-xs pl-kv-nb" data-id="' + _esc(p.id) + '">Notebook</button>' +
                        '<button type="button" class="btn btn-ghost btn-xs pl-kv-edit" data-id="' + _esc(p.id) + '">Editar</button>' +
                        '<button type="button" class="btn btn-ghost btn-xs text-error pl-kv-del" data-id="' + _esc(p.id) + '">Eliminar</button>' +
                    '</div>' +
                '</article>';
            }).join('') || '<p class="text-sm text-MAIN-content/60">Sin registros.</p>';
            return '<section class="rounded-box border border-MAIN-300 bg-MAIN-200 p-3 grid gap-2">' +
                '<div class="flex items-center justify-between gap-2">' +
                    '<h4 class="font-semibold text-MAIN-content">' + _esc(name) + '</h4>' +
                    '<span class="badge badge-outline badge-sm">' + String(groups[name].length) + '</span>' +
                '</div>' +
                cards +
            '</section>';
        }).join('');
        host.innerHTML = html || '<p class="text-sm text-MAIN-content/60">Sin puestos registrados.</p>';
        host.querySelectorAll('.pl-kv-nb').forEach(function(btn) {
            btn.addEventListener('click', function(){ openNotebook(btn.getAttribute('data-id')); });
        });
        host.querySelectorAll('.pl-kv-edit').forEach(function(btn) {
            btn.addEventListener('click', function(){ startEdit(btn.getAttribute('data-id')); setPlView('form'); });
        });
        host.querySelectorAll('.pl-kv-del').forEach(function(btn) {
            btn.addEventListener('click', function(){ deletePuesto(btn.getAttribute('data-id')); });
        });
    }

    function loadPlScript(src) {
        return new Promise(function(resolve, reject) {
            if (document.querySelector('script[src="' + src + '"]')) {
                resolve();
                return;
            }
            var script = document.createElement('script');
            script.src = src;
            script.async = true;
            script.onload = function() { resolve(); };
            script.onerror = function() { reject(new Error('No se pudo cargar ' + src)); };
            document.head.appendChild(script);
        });
    }

    async function ensurePlOrgLibrary() {
        if (window.d3 && window.d3.OrgChart) return true;
        if (!plOrgLibPromise) {
            plOrgLibPromise = (async function() {
                await loadPlScript('/static/vendor/d3.min.js');
                await loadPlScript('/static/vendor/d3-flextree.min.js');
                await loadPlScript('/static/vendor/d3-org-chart.min.js');
            })().catch(function() { return false; });
        }
        var result = await plOrgLibPromise;
        return result !== false && !!(window.d3 && window.d3.OrgChart);
    }

    function renderOrganigramaView() {
        var host = document.getElementById('pl-organigrama-host');
        if (!host) return;
        var data = getFilteredPuestos() || [];
        if (!data.length) {
            host.innerHTML = '<p class="text-sm text-MAIN-content/60">Sin puestos registrados.</p>';
            return;
        }
        ensurePlOrgLibrary().then(function(libOk) {
            if (!libOk) {
                host.innerHTML = '<p class="text-sm text-MAIN-content/60">No se pudo cargar la librería de organigrama.</p>';
                return;
            }
            var areaNodesMap = {};
            var nodes = [];
            data.forEach(function(p) {
                var area = String((p && p.area) || '').trim() || 'Sin área';
                var areaId = 'area::' + area.toLowerCase();
                if (!areaNodesMap[areaId]) {
                    areaNodesMap[areaId] = {
                        id: areaId,
                        parentId: '__ROOT__',
                        type: 'area',
                        area: area,
                        name: area,
                        code: area,
                        count: 0
                    };
                    nodes.push(areaNodesMap[areaId]);
                }
                areaNodesMap[areaId].count += 1;
                nodes.push({
                    id: 'puesto::' + String(p.id || p.nombre || Math.random().toString(36).slice(2)),
                    parentId: areaId,
                    type: 'puesto',
                    puestoId: String(p.id || ''),
                    name: String(p.nombre || '—'),
                    area: area,
                    level: String(p.nivel || 'Sin nivel'),
                    desc: String(p.descripcion || 'Sin descripción'),
                    habCount: (p.habilidades_requeridas || []).length,
                    colCount: (p.colaboradores_asignados || []).length
                });
            });
            nodes.unshift({
                id: '__ROOT__',
                parentId: '',
                type: 'root',
                name: 'Puestos laborales',
                code: 'ORG'
            });

            host.innerHTML = '';
            plOrgChart = new window.d3.OrgChart()
                .container(host)
                .data(nodes)
                .nodeWidth(function(d) { return d && d.data && d.data.type === 'puesto' ? 330 : 280; })
                .nodeHeight(function(d) { return d && d.data && d.data.type === 'puesto' ? 170 : 110; })
                .childrenMargin(function() { return 42; })
                .compact(true)
                .initialExpandLevel(2)
                .nodeButtonWidth(function() { return 36; })
                .nodeButtonHeight(function() { return 36; })
                .nodeButtonX(function() { return -18; })
                .nodeButtonY(function() { return -18; })
                .buttonContent(function(ctx) {
                    var node = ctx && ctx.node ? ctx.node : null;
                    var expanded = !!(node && node.children);
                    var sign = expanded ? '−' : '+';
                    var count = Number(node && node.data ? node.data._directSubordinates || 0 : 0);
                    return '<div style="width:36px;height:36px;border-radius:9999px;background:#0f172a;color:#fff;display:grid;place-items:center;font-weight:800;font-size:18px;border:2px solid #fff;box-shadow:0 4px 10px rgba(15,23,42,.22);">' + sign + (count > 0 ? '<span style="font-size:10px;margin-left:2px;">' + count + '</span>' : '') + '</div>';
                })
                .nodeContent(function(d) {
                    var item = d && d.data ? d.data : {};
                    if (item.type === 'root') {
                        return ''
                            + '<div style="height:106px;border:1px solid #dbe2ea;border-radius:12px;overflow:hidden;background:#0f172a;box-shadow:0 6px 14px rgba(15,23,42,.12);display:grid;place-items:center;color:#fff;font-family:inherit;">'
                            +   '<div style="text-align:center;">'
                            +     '<div style="font-size:26px;font-weight:800;">' + _esc(item.name || 'Puestos laborales') + '</div>'
                            +     '<div style="font-size:13px;opacity:.82;">Estructura por áreas</div>'
                            +   '</div>'
                            + '</div>';
                    }
                    if (item.type === 'area') {
                        return ''
                            + '<div style="height:106px;border:1px solid #dbe2ea;border-radius:12px;overflow:hidden;background:#fff;box-shadow:0 6px 14px rgba(15,23,42,.12);display:grid;grid-template-columns:78px 1fr;font-family:inherit;">'
                            +   '<div style="background:#1d4ed8;color:#fff;display:flex;align-items:center;justify-content:center;font-size:34px;font-weight:800;">' + _esc((item.name || '?').charAt(0).toUpperCase()) + '</div>'
                            +   '<div style="padding:12px;display:grid;gap:6px;align-content:start;">'
                            +     '<div style="font-size:22px;font-weight:800;color:#0f172a;line-height:1.05;">' + _esc(item.name || 'Área') + '</div>'
                            +     '<div style="font-size:13px;color:#334155;">Puestos: ' + String(item.count || 0) + '</div>'
                            +   '</div>'
                            + '</div>';
                    }
                    return ''
                        + '<div style="height:166px;border:1px solid #dbe2ea;border-radius:12px;overflow:hidden;background:#fff;box-shadow:0 6px 14px rgba(15,23,42,.12);display:grid;grid-template-columns:84px 1fr;font-family:inherit;">'
                        +   '<div style="background:#10b981;color:#fff;display:flex;align-items:center;justify-content:center;font-size:34px;font-weight:800;">' + _esc((item.name || '?').charAt(0).toUpperCase()) + '</div>'
                        +   '<div style="padding:12px;display:grid;gap:6px;align-content:start;">'
                        +     '<div style="font-size:20px;font-weight:800;color:#0f172a;line-height:1.05;">' + _esc(item.name || 'Puesto') + '</div>'
                        +     '<div style="font-size:13px;color:#334155;"><strong>Nivel:</strong> ' + _esc(item.level || 'Sin nivel') + '</div>'
                        +     '<div style="font-size:13px;color:#334155;"><strong>Área:</strong> ' + _esc(item.area || 'Sin área') + '</div>'
                        +     '<div style="font-size:12px;color:#64748b;">Habilidades: ' + String(item.habCount || 0) + ' · Colaboradores: ' + String(item.colCount || 0) + '</div>'
                        +   '</div>'
                        + '</div>';
                })
                .render();
        });
    }

    function setPlView(view) {
        plCurrentView = ['form', 'list', 'kanban', 'organigrama'].indexOf(view) >= 0 ? view : 'form';
        var formShell = document.getElementById('pl-form-shell');
        var pageTabs = document.getElementById('pl-page-tabs');
        var puestosView = document.getElementById('pl-view-puestos');
        var kpisView = document.getElementById('pl-view-kpis');
        var notebookView = document.getElementById('pl-view-notebook');
        var map = {
            form: document.getElementById('pl-card-form'),
            list: document.getElementById('pl-card-list'),
            kanban: document.getElementById('pl-card-kanban'),
            organigrama: document.getElementById('pl-card-organigrama')
        };
        if (formShell) formShell.style.display = plCurrentView === 'form' ? '' : 'none';
        if (pageTabs) pageTabs.style.display = plCurrentView === 'form' ? '' : 'none';
        if (plCurrentView !== 'form') {
            document.querySelectorAll('[data-pl-page-tab][data-ptab]').forEach(function(t) {
                var isPuestos = t.getAttribute('data-ptab') === 'puestos';
                t.classList.toggle('active', isPuestos);
                t.classList.toggle('tab-active', isPuestos);
            });
            if (puestosView) puestosView.style.display = '';
            if (kpisView) kpisView.style.display = 'none';
            if (notebookView) {
                notebookView.style.display = 'none';
                notebookView.classList.remove('active');
            }
        }
        Object.keys(map).forEach(function(key) {
            if (map[key]) map[key].style.display = key === plCurrentView ? 'block' : 'none';
        });
        document.querySelectorAll('[data-pl-view]').forEach(function(btn) {
            var isActive = btn.getAttribute('data-pl-view') === plCurrentView;
            btn.classList.toggle('active', isActive);
        });
        if (plCurrentView === 'list') renderTable();
        if (plCurrentView === 'kanban') renderKanbanView();
        if (plCurrentView === 'organigrama') renderOrganigramaView();
    }

    function _buildHabIndex(catalog) {
        var idx = {};
        _HAB_SOFT_KEYS.forEach(function(key) {
            (catalog[key] || []).forEach(function(skill) {
                var s = typeof skill === 'string' ? skill : (skill && (skill.nombre || skill.name));
                if (s) idx[String(s)] = 'blandas';
            });
        });
        _HAB_HARD_KEYS.forEach(function(key) {
            (catalog[key] || []).forEach(function(skill) {
                var s = typeof skill === 'string' ? skill : (skill && (skill.nombre || skill.name));
                if (s) idx[String(s)] = 'duras';
            });
        });
        return idx;
    }

    function _buildHabCatIndex(catalog) {
        var idx = {};
        _HAB_SOFT_KEYS.concat(_HAB_HARD_KEYS).forEach(function(key) {
            (catalog[key] || []).forEach(function(skill) {
                var s = typeof skill === 'string' ? skill : (skill && (skill.nombre || skill.name));
                if (s) idx[String(s)] = key;
            });
        });
        return idx;
    }

    function _normHabFormItem(raw) {
        if (raw && typeof raw === 'object') {
            return {
                nombre: String(raw.nombre || '').trim(),
                minimo: Math.min(100, Math.max(0, parseInt(raw.minimo, 10) || 0)),
                tipo: raw.tipo === 'duras' ? 'duras' : (raw.tipo === 'blandas' ? 'blandas' : '')
            };
        }
        return { nombre: String(raw || '').trim(), minimo: 0, tipo: '' };
    }

    function _splitHabByTipo(items) {
        var out = { blandas: [], duras: [] };
        (items || []).map(_normHabFormItem).forEach(function(it) {
            if (!it.nombre) return;
            var tipo = it.tipo || plHabIndex[it.nombre] || 'duras';
            if (tipo !== 'blandas' && tipo !== 'duras') tipo = 'duras';
            out[tipo].push({
                nombre: it.nombre,
                minimo: it.minimo,
                tipo: tipo,
                categoria: plHabCatIndex[it.nombre] || ''
            });
        });
        return out;
    }

    function _habOptionsHtml(tipo, selectedValue) {
        var keys = tipo === 'blandas' ? _HAB_SOFT_KEYS : _HAB_HARD_KEYS;
        var html = '<option value="">— Seleccionar habilidad —</option>';
        var selected = String(selectedValue || '');
        var seenSelected = false;
        var all = [];
        keys.forEach(function(key) {
            var skills = (plHabCatalog[key] || []).map(function(skill) {
                var s = typeof skill === 'string' ? skill : (skill && (skill.nombre || skill.name));
                return s ? String(s) : '';
            }).filter(Boolean);
            skills.forEach(function(s) {
                if (all.indexOf(s) === -1) all.push(s);
            });
        });
        all.sort(function(a, b) { return a.localeCompare(b); });
        all.forEach(function(s) {
            var sel = selected === s ? ' selected' : '';
            if (sel) seenSelected = true;
            html += '<option value="' + _esc(s) + '"' + sel + '>' + _esc(s) + '</option>';
        });
        if (selected && !seenSelected) {
            html += '<option value="' + _esc(selected) + '" selected>' + _esc(selected) + '</option>';
        }
        return html;
    }

    function _firstHabOption(tipo) {
        var keys = tipo === 'blandas' ? _HAB_SOFT_KEYS : _HAB_HARD_KEYS;
        for (var i = 0; i < keys.length; i += 1) {
            var list = plHabCatalog[keys[i]] || [];
            for (var j = 0; j < list.length; j += 1) {
                var skill = list[j];
                var s = typeof skill === 'string' ? skill : (skill && (skill.nombre || skill.name));
                if (s) return String(s);
            }
        }
        return '';
    }

    function _nextAvailableHab(tipo) {
        var keys = tipo === 'blandas' ? _HAB_SOFT_KEYS : _HAB_HARD_KEYS;
        var used = {};
        (plFormHab[tipo] || []).forEach(function(it) { used[String(it.nombre || '')] = true; });
        for (var i = 0; i < keys.length; i += 1) {
            var list = plHabCatalog[keys[i]] || [];
            for (var j = 0; j < list.length; j += 1) {
                var skill = list[j];
                var s = typeof skill === 'string' ? skill : (skill && (skill.nombre || skill.name));
                if (s && !used[String(s)]) return String(s);
            }
        }
        return _firstHabOption(tipo);
    }

    function _skillsForCat(catKey) {
        return (plHabCatalog[catKey] || []).map(function(skill) {
            var s = typeof skill === 'string' ? skill : (skill && (skill.nombre || skill.name));
            return s ? String(s) : '';
        }).filter(Boolean);
    }

    function _habOptionsHtmlCat(catKey, selectedValue) {
        var selected = String(selectedValue || '');
        var seenSelected = false;
        var skills = _skillsForCat(catKey);
        var html = '<option value="">— Seleccionar habilidad —</option>';
        skills.forEach(function(s) {
            var sel = selected === s ? ' selected' : '';
            if (sel) seenSelected = true;
            html += '<option value="' + _esc(s) + '"' + sel + '>' + _esc(s) + '</option>';
        });
        if (selected && !seenSelected) html += '<option value="' + _esc(selected) + '" selected>' + _esc(selected) + '</option>';
        return html;
    }

    function _nextAvailableHabByCat(tipo, catKey) {
        var used = {};
        (plFormHab[tipo] || []).forEach(function(it) { used[String(it.nombre || '')] = true; });
        var skills = _skillsForCat(catKey);
        for (var i = 0; i < skills.length; i += 1) {
            if (!used[skills[i]]) return skills[i];
        }
        return skills[0] || _nextAvailableHab(tipo);
    }

    function _hasAnyFormHab() {
        return Boolean((plFormHab && plFormHab.blandas && plFormHab.blandas.length) || (plFormHab && plFormHab.duras && plFormHab.duras.length));
    }

    function _buildDefaultHabByTipo(tipo) {
        var out = [];
        var seen = {};
        var keys = tipo === 'blandas' ? _HAB_SOFT_KEYS : _HAB_HARD_KEYS;
        keys.forEach(function(catKey) {
            (_skillsForCat(catKey) || []).forEach(function(skillName) {
                var key = String(skillName || '').trim();
                if (!key || seen[key]) return;
                seen[key] = true;
                out.push({
                    nombre: key,
                    minimo: 80,
                    tipo: tipo,
                    categoria: catKey
                });
            });
        });
        return out;
    }

    function _buildDefaultFormHabFromCatalog() {
        return {
            blandas: _buildDefaultHabByTipo('blandas'),
            duras: _buildDefaultHabByTipo('duras')
        };
    }

    function _buildFormHabForPuesto(items) {
        var parsed = _splitHabByTipo(items || []);
        var hasSavedSkills = Boolean(
            (parsed && parsed.blandas && parsed.blandas.length) ||
            (parsed && parsed.duras && parsed.duras.length)
        );
        return hasSavedSkills ? parsed : _buildDefaultFormHabFromCatalog();
    }

    function _renderHabRows(tipo) {
        if (!plFormHab || typeof plFormHab !== 'object') plFormHab = { blandas: [], duras: [] };
        if (!Array.isArray(plFormHab.blandas)) plFormHab.blandas = [];
        if (!Array.isArray(plFormHab.duras)) plFormHab.duras = [];
        var root = document.getElementById(tipo === 'blandas' ? 'pl-hab-blandas-list' : 'pl-hab-duras-list');
        if (!root) return;
        var rows = plFormHab[tipo] || [];
        var catKeys = tipo === 'blandas' ? _HAB_SOFT_KEYS : _HAB_HARD_KEYS;
        root.innerHTML = catKeys.map(function(catKey, catPos) {
            var catRows = rows.map(function(row, idx) { return { row: row, idx: idx }; }).filter(function(item) {
                var fromRow = String((item.row && item.row.categoria) || '').trim();
                var fromName = plHabCatIndex[String((item.row && item.row.nombre) || '').trim()] || '';
                return (fromRow && fromRow === catKey) || (!fromRow && fromName === catKey);
            });
            var rowHtml = catRows.map(function(item) {
                var options = _habOptionsHtmlCat(catKey, item.row.nombre);
                return (
                    '<div class="grid grid-cols-1 md:grid-cols-[1fr_180px_auto] gap-2 items-end">' +
                        '<div>' +
                            '<label class="pl-label">Nombre</label>' +
                            '<select class="pl-select select select-bordered campo pl-hab-name" data-tipo="' + tipo + '" data-cat="' + catKey + '" data-idx="' + item.idx + '">' + options + '</select>' +
                        '</div>' +
                        '<div>' +
                            '<label class="pl-label">% dominio mínimo</label>' +
                            '<input type="number" min="0" max="100" class="pl-input input input-bordered campo pl-hab-min" data-tipo="' + tipo + '" data-idx="' + item.idx + '" value="' + item.row.minimo + '">' +
                        '</div>' +
                        '<button type="button" class="btn btn-sm btn-error btn-outline pl-hab-del" data-tipo="' + tipo + '" data-idx="' + item.idx + '">Quitar</button>' +
                    '</div>'
                );
            }).join('');
            if (!rowHtml) rowHtml = '<div class="text-sm text-MAIN-content/60">Sin habilidades agregadas en este bloque.</div>';
            return (
                '<details class="collapse collapse-arrow border border-MAIN-300 bg-MAIN-100" ' + (catPos === 0 ? 'open' : '') + '>' +
                    '<summary class="collapse-title text-sm font-semibold">' + _esc((_HAB_CAT_ICONS[catKey] || '•') + ' ' + (_HAB_CAT_LABELS[catKey] || catKey.replace(/_/g, ' '))) + '</summary>' +
                    '<div class="collapse-content grid gap-2">' +
                        rowHtml +
                        '<button type="button" class="btn btn-sm btn-outline pl-hab-add-cat" data-tipo="' + tipo + '" data-cat="' + catKey + '">Agregar habilidad</button>' +
                    '</div>' +
                '</details>'
            );
        }).join('');

        root.querySelectorAll('.pl-hab-name').forEach(function(el) {
            el.addEventListener('change', function() {
                var t = this.getAttribute('data-tipo');
                var cat = this.getAttribute('data-cat') || '';
                var idx = parseInt(this.getAttribute('data-idx'), 10);
                if (!plFormHab[t] || !plFormHab[t][idx]) return;
                plFormHab[t][idx].nombre = this.value.trim();
                if (cat) plFormHab[t][idx].categoria = cat;
                _renderHabRows(t);
            });
        });
        root.querySelectorAll('.pl-hab-min').forEach(function(el) {
            el.addEventListener('change', function() {
                var t = this.getAttribute('data-tipo');
                var idx = parseInt(this.getAttribute('data-idx'), 10);
                if (!plFormHab[t] || !plFormHab[t][idx]) return;
                plFormHab[t][idx].minimo = Math.min(100, Math.max(0, parseInt(this.value, 10) || 0));
                this.value = plFormHab[t][idx].minimo;
            });
        });
        root.querySelectorAll('.pl-hab-del').forEach(function(el) {
            el.addEventListener('click', function() {
                var t = this.getAttribute('data-tipo');
                var idx = parseInt(this.getAttribute('data-idx'), 10);
                if (!plFormHab[t]) return;
                plFormHab[t].splice(idx, 1);
                _renderHabRows(t);
            });
        });
        root.querySelectorAll('.pl-hab-add-cat').forEach(function(el) {
            el.addEventListener('click', function(ev) {
                ev.preventDefault();
                var t = this.getAttribute('data-tipo');
                var cat = this.getAttribute('data-cat');
                if (!plFormHab[t]) plFormHab[t] = [];
                plFormHab[t].push({
                    nombre: _nextAvailableHabByCat(t, cat),
                    minimo: 80,
                    tipo: t,
                    categoria: cat
                });
                _renderHabRows(t);
            });
        });
    }

    function _renderFormHab() {
        _renderHabRows('blandas');
        _renderHabRows('duras');
        ensurePuestosAccordionVisible();
    }

    function ensurePuestosAccordionVisible() {
        var root = document.getElementById('pl-view-puestos');
        if (!root) return;
        root.querySelectorAll('details.collapse').forEach(function(det) {
            if (!det.hasAttribute('open')) det.setAttribute('open', 'open');
            var content = det.querySelector(':scope > .collapse-content');
            if (content) {
                content.style.display = 'grid';
                content.style.maxHeight = 'none';
                content.style.opacity = '1';
            }
        });
    }

    function _getFormHabPayload() {
        var habs = [];
        ['blandas', 'duras'].forEach(function(tipo) {
            (plFormHab[tipo] || []).forEach(function(it) {
                var nombre = String(it.nombre || '').trim();
                if (!nombre) return;
                habs.push({
                    nombre: nombre,
                    minimo: Math.min(100, Math.max(0, parseInt(it.minimo, 10) || 0)),
                    tipo: tipo
                });
            });
        });
        return habs;
    }

    function _loadHabCatalogForForm() {
        return fetch('/api/habilidades-catalog')
            .then(function(r) { return r.json(); })
            .then(function(res) {
                plHabCatalog = res.catalog || res.data || res || {};
                plHabIndex = _buildHabIndex(plHabCatalog);
                plHabCatIndex = _buildHabCatIndex(plHabCatalog);
                var editIdEl = document.getElementById('pl-edit-id');
                var isEditing = Boolean(String((editIdEl && editIdEl.value) || '').trim());
                if (!isEditing && !_hasAnyFormHab()) {
                    plFormHab = _buildDefaultFormHabFromCatalog();
                }
                _renderFormHab();
            })
            .catch(function() {
                plHabCatalog = {};
                plHabIndex = {};
                plHabCatIndex = {};
                _renderFormHab();
            });
    }

    function startEdit(id) {
        var p = puestos.find(function(x){ return x.id === id; });
        if (!p) return;
        document.getElementById('pl-edit-id').value = p.id;
        document.getElementById('pl-nombre').value = p.nombre;
        setAreaOptions(p.area || '');
        document.getElementById('pl-nivel').value = p.nivel || '';
        document.getElementById('pl-desc').value = p.descripcion || '';
        plFormHab = _buildFormHabForPuesto(p.habilidades_requeridas || []);
        _renderFormHab();
        document.getElementById('pl-form-title').textContent = 'Editar puesto laboral';
        document.getElementById('pl-btn-cancel').style.display = 'inline-block';
        document.getElementById('pl-nombre').focus();
    }

    function resetForm() {
        document.getElementById('pl-edit-id').value = '';
        document.getElementById('pl-nombre').value = '';
        setAreaOptions('');
        document.getElementById('pl-nivel').value = '';
        document.getElementById('pl-desc').value = '';
        plFormHab = _buildDefaultFormHabFromCatalog();
        _renderFormHab();
        document.getElementById('pl-form-title').textContent = 'Nuevo puesto laboral';
        document.getElementById('pl-btn-cancel').style.display = 'none';
        setSaveMessage('');
    }

    document.getElementById('pl-btn-cancel').addEventListener('click', resetForm);

    document.getElementById('pl-btn-save').addEventListener('click', function() {
        var saveBtn = document.getElementById('pl-btn-save');
        var nombre = document.getElementById('pl-nombre').value.trim();
        if (!nombre) {
            setSaveMessage('Capture el nombre del puesto.', true);
            document.getElementById('pl-nombre').focus();
            return;
        }
        var area = document.getElementById('pl-area').value.trim();
        if (!area) {
            setSaveMessage('Seleccione un área válida.', true);
            document.getElementById('pl-area').focus();
            return;
        }
        var payload = {
            id:          document.getElementById('pl-edit-id').value || undefined,
            nombre:      nombre,
            area:        area,
            nivel:       document.getElementById('pl-nivel').value,
            descripcion: document.getElementById('pl-desc').value.trim(),
            habilidades_requeridas: _getFormHabPayload(),
        };
        setSaveMessage('');
        if (saveBtn) saveBtn.disabled = true;
        fetch('/api/puestos-laborales', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(function(r){ return r.json(); })
        .then(function(res){
            if (res.success) {
                plLastSavedId = String((res && res.puesto && res.puesto.id) || '');
                return loadPuestos().then(function() {
                    resetForm();
                    setPlView('list');
                    setSaveMessage('✓ Guardado: ' + nombre, false);
                });
            }
            setSaveMessage((res && res.error) || 'No se pudo guardar el puesto.', true);
        })
        .catch(function() {
            setSaveMessage('No se pudo guardar el puesto.', true);
        })
        .finally(function() {
            if (saveBtn) saveBtn.disabled = false;
        });
    });

    function deletePuesto(id) {
        if (!confirm('¿Eliminar este puesto?')) return;
        fetch('/api/puestos-laborales', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'delete', id: id })
        })
        .then(function(r){ return r.json(); })
        .then(function(res){ if (res.success) { puestos = res.data; renderTable(); } });
    }

    function _esc(s) {
        return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }
    document.querySelectorAll('[data-pl-view]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            setPlView(btn.getAttribute('data-pl-view') || 'form');
        });
    });
    (function bindPuestoNewShortcut() {
        var newBtn = document.getElementById('pl-btn-new-short');
        if (!newBtn) return;
        newBtn.addEventListener('click', function() {
            resetForm();
            setPlView('form');
            var nameInput = document.getElementById('pl-nombre');
            if (nameInput) nameInput.focus();
        });
    })();
    (function bindPuestoFilters() {
        var searchEl = document.getElementById('pl-filter-search');
        var nivelEl = document.getElementById('pl-filter-nivel');
        var clearEl = document.getElementById('pl-filter-clear');
        if (searchEl) {
            searchEl.addEventListener('input', function() {
                plFilters.search = String(searchEl.value || '').trim();
                renderTable();
            });
        }
        if (nivelEl) {
            nivelEl.addEventListener('change', function() {
                plFilters.nivel = String(nivelEl.value || '').trim();
                renderTable();
            });
        }
        if (clearEl) {
            clearEl.addEventListener('click', function() {
                plFilters = { search: '', nivel: '' };
                if (searchEl) searchEl.value = '';
                if (nivelEl) nivelEl.value = '';
                renderTable();
            });
        }
    })();

    var addBlandasBtn = document.getElementById('pl-hab-blandas-add');
    if (addBlandasBtn) {
        addBlandasBtn.addEventListener('click', function(ev) {
            ev.preventDefault();
            if (!plFormHab || typeof plFormHab !== 'object') plFormHab = { blandas: [], duras: [] };
            if (!Array.isArray(plFormHab.blandas)) plFormHab.blandas = [];
            plFormHab.blandas.push({ nombre: _nextAvailableHab('blandas'), minimo: 80, tipo: 'blandas', categoria: _HAB_SOFT_KEYS[0] });
            _renderHabRows('blandas');
        });
    }
    var addDurasBtn = document.getElementById('pl-hab-duras-add');
    if (addDurasBtn) {
        addDurasBtn.addEventListener('click', function(ev) {
            ev.preventDefault();
            if (!plFormHab || typeof plFormHab !== 'object') plFormHab = { blandas: [], duras: [] };
            if (!Array.isArray(plFormHab.duras)) plFormHab.duras = [];
            plFormHab.duras.push({ nombre: _nextAvailableHab('duras'), minimo: 80, tipo: 'duras', categoria: _HAB_HARD_KEYS[0] });
            _renderHabRows('duras');
        });
    }

    // ── Notebook drawer ────────────────────────────────────────────────────────
    var nbPuestoId = null;
    var nbActiveTab = 'hab';
    var nbHabCatalog = null;   // cached catalog
    var nbColabs = null;       // cached collaborators

    function openNotebook(id) {
        nbPuestoId = id;
        var p = puestos.find(function(x){ return x.id === id; });
        if (!p) return;
        document.getElementById('pl-nb-titulo').textContent = p.nombre;
        // reset tabs
        document.querySelectorAll('[data-pl-nb-tab][data-tab]').forEach(function(t){ t.classList.remove('active'); t.classList.remove('tab-active'); });
        document.querySelectorAll('.pl-nb-panel').forEach(function(t){ t.classList.remove('active'); });
        nbActiveTab = 'hab';
        document.querySelector('[data-pl-nb-tab][data-tab="hab"]').classList.add('active');
        document.querySelector('[data-pl-nb-tab][data-tab="hab"]').classList.add('tab-active');
        document.getElementById('pl-nb-panel-hab').classList.add('active');
        // show
        document.getElementById('pl-nb-overlay').style.display = 'block';
        document.getElementById('pl-nb-drawer').classList.add('open');
        document.getElementById('pl-nb-saved').style.display = 'none';
        // load
        _nbLoadHab(p);
        _nbLoadCol(p);
    }

    function closeNotebook() {
        document.getElementById('pl-nb-drawer').classList.remove('open');
        document.getElementById('pl-nb-overlay').style.display = 'none';
        nbPuestoId = null;
    }

    document.getElementById('pl-nb-close-btn').addEventListener('click', closeNotebook);
    document.getElementById('pl-nb-overlay').addEventListener('click', closeNotebook);

    document.querySelectorAll('[data-pl-nb-tab][data-tab]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var tab = btn.getAttribute('data-tab');
            nbActiveTab = tab;
            document.querySelectorAll('[data-pl-nb-tab][data-tab]').forEach(function(t){ t.classList.remove('active'); t.classList.remove('tab-active'); });
            document.querySelectorAll('.pl-nb-panel').forEach(function(t){ t.classList.remove('active'); });
            btn.classList.add('active');
            btn.classList.add('tab-active');
            document.getElementById('pl-nb-panel-' + tab).classList.add('active');
        });
    });

    // ── Habilidades tab ─────────────────────────────────────────────────────────
    function _normHabItem(raw) {
        if (raw && typeof raw === 'object') {
            return {
                nombre: String(raw.nombre || '').trim(),
                minimo: parseInt(raw.minimo, 10) || 0,
                tipo: raw.tipo === 'duras' ? 'duras' : (raw.tipo === 'blandas' ? 'blandas' : '')
            };
        }
        return { nombre: String(raw || '').trim(), minimo: 0, tipo: '' };
    }

    function _nbLoadHab(p) {
        var panel = document.getElementById('pl-nb-panel-hab');
        panel.innerHTML = '<p class="pl-nb-loading">Cargando habilidades...</p>';
        var items = (p.habilidades_requeridas || []).map(_normHabItem);

        function _listHtml() {
            if (!items.length) return '<p class="pl-nb-loading">Sin habilidades agregadas.</p>';
            return items.map(function(it, idx) {
                return '<div class="pl-nb-hab-row" data-idx="' + idx + '">' +
                    '<span class="pl-nb-hab-nombre">' + _esc(it.nombre) + '</span>' +
                    '<span class="pl-nb-hab-badge">' + it.minimo + '%</span>' +
                    '<button class="pl-nb-hab-del" data-idx="' + idx + '" title="Eliminar">&times;</button>' +
                '</div>';
            }).join('');
        }

        function _buildSelect(catalog) {
            var allSkills = [];
            Object.keys(catalog).forEach(function(cat) {
                var catLabel = _HAB_CAT_LABELS[cat] || cat.replace(/_/g,' ');
                (catalog[cat] || []).forEach(function(skill) {
                    var s = typeof skill === 'string' ? skill : (skill.nombre || skill.name || String(skill));
                    if (s) allSkills.push({ nombre: s, categoria: catLabel });
                });
            });
            allSkills.sort(function(a,b){ return a.nombre.localeCompare(b.nombre); });
            var selOpts = '<option value="">— Selecciona una habilidad —</option>';
            var lastCat = '';
            allSkills.forEach(function(sk) {
                if (sk.categoria !== lastCat) {
                    if (lastCat) selOpts += '</optgroup>';
                    selOpts += '<optgroup label="' + _esc(sk.categoria) + '">';
                    lastCat = sk.categoria;
                }
                selOpts += '<option value="' + _esc(sk.nombre) + '">' + _esc(sk.nombre) + '</option>';
            });
            if (lastCat) selOpts += '</optgroup>';
            return selOpts;
        }

        function _renderUI(selOpts) {
            panel.innerHTML =
                '<div id="pl-nb-hab-list" style="display:flex;flex-direction:column;gap:6px;margin-bottom:14px;">' + _listHtml() + '</div>' +
                '<div style="border-top:1px solid #e2e8f0;padding-top:12px;display:flex;flex-direction:column;gap:8px;">' +
                  '<label style="font-size:.78rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.04em;">Agregar habilidad</label>' +
                  '<select id="pl-nb-hab-sel" class="select select-bordered campo" style="width:100%;">' + selOpts + '</select>' +
                  '<div style="display:flex;gap:8px;align-items:center;">' +
                    '<label style="font-size:.85rem;color:#475569;white-space:nowrap;">Mínimo requerido</label>' +
                    '<input id="pl-nb-hab-pct" type="number" min="0" max="100" value="80" class="input input-bordered campo" style="width:72px;text-align:center;">' +
                    '<span style="font-size:.9rem;color:#64748b;">%</span>' +
                    '<button id="pl-nb-hab-add" style="margin-left:auto;padding:7px 16px;background:var(--button-bg,#0f172a);color:#fff;border:0;border-radius:8px;font-weight:700;cursor:pointer;font-size:.85rem;">Agregar</button>' +
                  '</div>' +
                '</div>';

            function _rebindDeletes() {
                panel.querySelectorAll('.pl-nb-hab-del').forEach(function(btn) {
                    btn.addEventListener('click', function() {
                        var idx = parseInt(this.getAttribute('data-idx'), 10);
                        items.splice(idx, 1);
                        document.getElementById('pl-nb-hab-list').innerHTML = _listHtml();
                        _rebindDeletes();
                    });
                });
            }
            _rebindDeletes();

            document.getElementById('pl-nb-hab-add').addEventListener('click', function() {
                var sel = document.getElementById('pl-nb-hab-sel');
                var pct = document.getElementById('pl-nb-hab-pct');
                var nombre = sel.value.trim();
                var minimo = Math.min(100, Math.max(0, parseInt(pct.value, 10) || 0));
                if (!nombre) { sel.focus(); return; }
                if (items.find(function(x){ return x.nombre === nombre; })) { sel.value = ''; sel.focus(); return; }
                items.push({ nombre: nombre, minimo: minimo });
                sel.value = '';
                pct.value = 80;
                document.getElementById('pl-nb-hab-list').innerHTML = _listHtml();
                _rebindDeletes();
            });
        }

        if (nbHabCatalog) { _renderUI(_buildSelect(nbHabCatalog)); return; }
        fetch('/api/habilidades-catalog')
            .then(function(r){ return r.json(); })
            .then(function(res){
                nbHabCatalog = res.catalog || res.data || res || {};
                _renderUI(_buildSelect(nbHabCatalog));
            })
            .catch(function(){ panel.innerHTML = '<p class="pl-nb-loading">Error al cargar catálogo.</p>'; });
    }

    // ── Colaboradores tab ────────────────────────────────────────────────────────
    function _nbLoadCol(p) {
        var panel = document.getElementById('pl-nb-panel-col');
        panel.innerHTML = '<p class="pl-nb-loading">Cargando colaboradores...</p>';
        var assigned = (p.colaboradores_asignados || []).map(String);
        function _render(colabs) {
            var searchId = 'pl-nb-col-search-' + Date.now();
            var listId = 'pl-nb-col-list-' + Date.now();
            var html = '<input class="pl-nb-search input input-bordered campo" id="' + searchId + '" placeholder="Buscar colaborador..." autocomplete="off">';
            html += '<div id="' + listId + '">';
            colabs.forEach(function(c) {
                var isChk = assigned.indexOf(String(c.id)) >= 0;
                var initials = (c.nombre || '?').split(' ').slice(0,2).map(function(w){ return w[0]; }).join('').toUpperCase();
                var dept = c.departamento || c.puesto || '';
                html += '<label class="pl-nb-col-item" data-nombre="' + _esc((c.nombre||'').toLowerCase()) + '">' +
                    '<input type="checkbox" value="' + _esc(String(c.id)) + '" ' + (isChk ? 'checked' : '') + '>' +
                    (c.imagen ? '<img class="pl-nb-avatar" src="' + _esc(c.imagen) + '" onerror="this.style.display=\'none\'">' : '<div class="pl-nb-avatar">' + _esc(initials) + '</div>') +
                    '<div>' +
                      '<div class="pl-nb-col-name">' + _esc(c.nombre || '—') + '</div>' +
                      (dept ? '<div class="pl-nb-col-sub">' + _esc(dept) + '</div>' : '') +
                    '</div></label>';
            });
            html += '</div>';
            panel.innerHTML = html;
            var inp = document.getElementById(searchId);
            var lst = document.getElementById(listId);
            inp.addEventListener('input', function() {
                var q = inp.value.toLowerCase();
                lst.querySelectorAll('.pl-nb-col-item').forEach(function(el) {
                    el.style.display = (!q || el.getAttribute('data-nombre').indexOf(q) >= 0) ? '' : 'none';
                });
            });
        }
        if (nbColabs) { _render(nbColabs); return; }
        fetch('/api/colaboradores')
            .then(function(r){ return r.json(); })
            .then(function(res){
                nbColabs = (res.data || res || []).filter(function(c){ return c.colaborador !== false; });
                _render(nbColabs);
            })
            .catch(function(){ panel.innerHTML = '<p class="pl-nb-loading">Error al cargar colaboradores.</p>'; });
    }

    // ── Save notebook ────────────────────────────────────────────────────────────
    document.getElementById('pl-nb-btn-save').addEventListener('click', function() {
        if (!nbPuestoId) return;
        // collect habilidades
        var habs = [];
        document.querySelectorAll('#pl-nb-panel-hab .pl-nb-hab-row').forEach(function(row) {
            var nombre = row.querySelector('.pl-nb-hab-nombre');
            var badge  = row.querySelector('.pl-nb-hab-badge');
            if (nombre) habs.push({ nombre: nombre.textContent.trim(), minimo: parseInt((badge ? badge.textContent : '0'), 10) || 0 });
        });
        // collect colaboradores
        var colPanel = document.getElementById('pl-nb-panel-col');
        var cols = [];
        colPanel.querySelectorAll('input[type=checkbox]:checked').forEach(function(cb) {
            cols.push(cb.value);
        });
        fetch('/api/puestos-laborales', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'update_notebook', id: nbPuestoId, habilidades_requeridas: habs, colaboradores_asignados: cols })
        })
        .then(function(r){ return r.json(); })
        .then(function(res){
            if (res.success) {
                puestos = res.data;
                renderTable();
                var msg = document.getElementById('pl-nb-saved');
                msg.style.display = 'inline';
                setTimeout(function(){ msg.style.display = 'none'; }, 2200);
            }
        });
    });

    // ── Page-level tabs ─────────────────────────────────────────────────────────
    document.querySelectorAll('[data-pl-page-tab][data-ptab]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var target = btn.getAttribute('data-ptab');
            document.querySelectorAll('[data-pl-page-tab][data-ptab]').forEach(function(t){ t.classList.remove('active'); t.classList.remove('tab-active'); });
            btn.classList.add('active');
            btn.classList.add('tab-active');
            var vP = document.getElementById('pl-view-puestos');
            var vN = document.getElementById('pl-view-notebook');
            var vK = document.getElementById('pl-view-kpis');
            vP.style.display = 'none';
            vN.style.display = 'none'; vN.classList.remove('active');
            vK.style.display = 'none';
            if (target === 'puestos') {
                vP.style.display = '';
            } else if (target === 'notebook') {
                vN.style.display = ''; vN.classList.add('active');
                var sel = document.getElementById('pl-nbp-sel');
                var cur = sel.value;
                sel.innerHTML = '<option value="">\u2014 Seleccionar \u2014</option>';
                puestos.forEach(function(p) {
                    var o = document.createElement('option');
                    o.value = p.id; o.textContent = p.nombre;
                    if (p.id === cur) o.selected = true;
                    sel.appendChild(o);
                });
            } else if (target === 'kpis') {
                vK.style.display = '';
                var ksel = document.getElementById('pl-kpi-sel');
                var kcur = ksel.value;
                ksel.innerHTML = '<option value="">\u2014 Seleccionar \u2014</option>';
                puestos.forEach(function(p) {
                    var o = document.createElement('option');
                    o.value = p.id; o.textContent = p.nombre;
                    if (p.id === kcur) o.selected = true;
                    ksel.appendChild(o);
                });
                if (kcur) ksel.dispatchEvent(new Event('change'));
            }
        });
    });

    // ── KPIs inline tab ───────────────────────────────────────────────
    var plKpiPuestoId = null;
    document.getElementById('pl-kpi-sel').addEventListener('change', function() {
        var id = this.value;
        var cont = document.getElementById('pl-kpi-content');
        if (!id) { cont.style.display = 'none'; plKpiPuestoId = null; return; }
        plKpiPuestoId = id;
        var p = puestos.find(function(x){ return x.id === id; });
        if (!p) return;
        cont.style.display = '';
        document.getElementById('pl-kpi-titulo').textContent = p.nombre || '';
        _renderKpiPanel(p.kpis || []);
    });

    function _renderKpiPanel(kpis) {
        var panel = document.getElementById('pl-kpi-panel');
        var html = '';
        (kpis || []).forEach(function(k, idx) {
            html += '<div class="grid grid-cols-1 md:grid-cols-[1fr_180px_180px_auto] gap-2 items-end pl-kpi-row" data-idx="' + idx + '">' +
                '<div><label class="pl-label">KPI</label><input class="pl-input input input-bordered campo pl-kpi-nombre" type="text" value="' + _esc(k.nombre || '') + '" placeholder="Nombre del KPI"></div>' +
                '<div><label class="pl-label">Meta</label><input class="pl-input input input-bordered campo pl-kpi-meta" type="text" value="' + _esc(k.meta || '') + '" placeholder="Ej. 95%"></div>' +
                '<div><label class="pl-label">Unidad</label><input class="pl-input input input-bordered campo pl-kpi-unidad" type="text" value="' + _esc(k.unidad || '') + '" placeholder="%, #, $..."></div>' +
                '<div style="padding-top:22px;"><button class="btn btn-sm btn-error btn-outline pl-kpi-del" type="button">&times;</button></div>' +
                '</div>';
        });
        html += '<div style="margin-top:10px;"><button id="pl-kpi-add" class="btn btn-sm btn-outline" type="button">+ Agregar KPI</button></div>';
        panel.innerHTML = html;
        panel.querySelectorAll('.pl-kpi-del').forEach(function(btn) {
            btn.addEventListener('click', function() { btn.closest('.pl-kpi-row').remove(); });
        });
        var addBtn = panel.querySelector('#pl-kpi-add');
        if (addBtn) addBtn.addEventListener('click', function() {
            _renderKpiPanel(_getKpiRows().concat([{nombre:'',meta:'',unidad:''}]));
        });
    }

    function _getKpiRows() {
        var rows = [];
        document.querySelectorAll('#pl-kpi-panel .pl-kpi-row').forEach(function(row) {
            rows.push({
                nombre: (row.querySelector('.pl-kpi-nombre') || {}).value || '',
                meta:   (row.querySelector('.pl-kpi-meta')   || {}).value || '',
                unidad: (row.querySelector('.pl-kpi-unidad') || {}).value || ''
            });
        });
        return rows;
    }

    document.getElementById('pl-kpi-btn-save').addEventListener('click', function() {
        if (!plKpiPuestoId) return;
        var kpis = _getKpiRows().filter(function(k){ return k.nombre.trim(); });
        fetch('/api/puestos-laborales', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ action: 'update_notebook', id: plKpiPuestoId, kpis: kpis }),
            credentials: 'include'
        })
        .then(function(r){ return r.json(); })
        .then(function(res) {
            if (res.success) {
                puestos = res.data;
                var msg = document.getElementById('pl-kpi-saved');
                msg.style.display = 'inline';
                setTimeout(function(){ msg.style.display = 'none'; }, 2200);
            }
        });
    });

    // ── Notebook page: selector ─────────────────────────────────────────────────
    var nbpPuestoId = null;
    document.getElementById('pl-nbp-sel').addEventListener('change', function() {
        var id = this.value;
        var cont = document.getElementById('pl-nbp-content');
        if (!id) { cont.style.display = 'none'; nbpPuestoId = null; return; }
        nbpPuestoId = id;
        var p = puestos.find(function(x){ return x.id === id; });
        if (!p) return;
        document.getElementById('pl-nbp-titulo').textContent = p.nombre;
        document.getElementById('pl-nbp-area').value = p.area || '— Sin área asignada —';
        document.getElementById('pl-nbp-nivel').value = p.nivel || '— Sin nivel asignado —';
        document.getElementById('pl-nbp-desc').value = p.descripcion || 'Sin descripción.';
        cont.style.display = '';
        document.querySelectorAll('[data-pl-nbp-tab][data-nbptab]').forEach(function(t){ t.classList.remove('active'); t.classList.remove('tab-active'); });
        document.querySelectorAll('.pl-nbp-panel').forEach(function(t){ t.classList.remove('active'); });
        document.querySelector('[data-pl-nbp-tab][data-nbptab="hab"]').classList.add('active');
        document.querySelector('[data-pl-nbp-tab][data-nbptab="hab"]').classList.add('tab-active');
        document.getElementById('pl-nbp-panel-hab').classList.add('active');
        _nbpLoadHab(p);
        _nbpLoadKpi(p);
    });

    document.querySelectorAll('[data-pl-nbp-tab][data-nbptab]').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var tab = btn.getAttribute('data-nbptab');
            if (tab === 'kpi') {
                window.location.href = '/inicio/departamentos/notebook-puesto';
                return;
            }
            document.querySelectorAll('[data-pl-nbp-tab][data-nbptab]').forEach(function(t){ t.classList.remove('active'); t.classList.remove('tab-active'); });
            document.querySelectorAll('.pl-nbp-panel').forEach(function(t){ t.classList.remove('active'); });
            btn.classList.add('active');
            btn.classList.add('tab-active');
            document.getElementById('pl-nbp-panel-' + tab).classList.add('active');
        });
    });

    // ── Habilidades (notebook page) ─────────────────────────────────────────────
    function _nbpLoadHab(p) {
        var panel = document.getElementById('pl-nbp-panel-hab');
        panel.innerHTML = '<p class="pl-nb-loading">Cargando...</p>';
        var items = (p.habilidades_requeridas || []).map(_normHabItem);
        function _listHtml() {
            if (!items.length) return '<p class="pl-nb-loading">Sin habilidades agregadas.</p>';
            return items.map(function(it, idx) {
                return '<div class="pl-nb-hab-row" data-idx="' + idx + '">' +
                    '<span class="pl-nb-hab-nombre">' + _esc(it.nombre) + '</span>' +
                    '<span class="pl-nb-hab-badge">' + it.minimo + '%</span>' +
                    '<button class="pl-nb-hab-del" data-idx="' + idx + '">&times;</button></div>';
            }).join('');
        }
        function _buildOpts(catalog) {
            var all = [];
            Object.keys(catalog).forEach(function(cat) {
                var lbl = _HAB_CAT_LABELS[cat] || cat.replace(/_/g,' ');
                (catalog[cat] || []).forEach(function(sk) {
                    var s = typeof sk === 'string' ? sk : (sk.nombre || sk.name || String(sk));
                    if (s) all.push({ nombre: s, categoria: lbl });
                });
            });
            all.sort(function(a,b){ return a.nombre.localeCompare(b.nombre); });
            var opts = '<option value="">\u2014 Selecciona una habilidad \u2014</option>'; var lc = '';
            all.forEach(function(sk) {
                if (sk.categoria !== lc) { if (lc) opts += '</optgroup>'; opts += '<optgroup label="' + _esc(sk.categoria) + '">'; lc = sk.categoria; }
                opts += '<option value="' + _esc(sk.nombre) + '">' + _esc(sk.nombre) + '</option>';
            });
            if (lc) opts += '</optgroup>'; return opts;
        }
        function _renderUI(selOpts) {
            panel.innerHTML =
                '<div id="pl-nbp-hab-list" style="display:flex;flex-direction:column;gap:6px;margin-bottom:14px;">' + _listHtml() + '</div>' +
                '<div style="border-top:1px solid #e2e8f0;padding-top:12px;display:flex;flex-direction:column;gap:8px;">' +
                  '<label style="font-size:.78rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.04em;">Agregar habilidad</label>' +
                  '<select id="pl-nbp-hab-sel" class="select select-bordered campo" style="width:100%;">' + selOpts + '</select>' +
                  '<div style="display:flex;gap:8px;align-items:center;">' +
                    '<label style="font-size:.85rem;color:#475569;white-space:nowrap;">M\u00ednimo requerido</label>' +
                    '<input id="pl-nbp-hab-pct" type="number" min="0" max="100" value="80" class="input input-bordered campo" style="width:72px;text-align:center;">' +
                    '<span style="font-size:.9rem;color:#64748b;">%</span>' +
                    '<button id="pl-nbp-hab-add" style="margin-left:auto;padding:7px 16px;background:var(--button-bg,#0f172a);color:#fff;border:0;border-radius:8px;font-weight:700;cursor:pointer;font-size:.85rem;">Agregar</button>' +
                  '</div></div>';
            function _rebind() {
                panel.querySelectorAll('.pl-nb-hab-del').forEach(function(b) {
                    b.addEventListener('click', function() {
                        items.splice(parseInt(this.getAttribute('data-idx'), 10), 1);
                        document.getElementById('pl-nbp-hab-list').innerHTML = _listHtml();
                        _rebind();
                    });
                });
            }
            _rebind();
            document.getElementById('pl-nbp-hab-add').addEventListener('click', function() {
                var sel = document.getElementById('pl-nbp-hab-sel');
                var pct = document.getElementById('pl-nbp-hab-pct');
                var nombre = sel.value.trim();
                var minimo = Math.min(100, Math.max(0, parseInt(pct.value, 10) || 0));
                if (!nombre || items.find(function(x){ return x.nombre === nombre; })) { sel.focus(); return; }
                items.push({ nombre: nombre, minimo: minimo }); sel.value = ''; pct.value = 80;
                document.getElementById('pl-nbp-hab-list').innerHTML = _listHtml(); _rebind();
            });
        }
        if (nbHabCatalog) { _renderUI(_buildOpts(nbHabCatalog)); return; }
        fetch('/api/habilidades-catalog')
            .then(function(r){ return r.json(); })
            .then(function(res){ nbHabCatalog = res.catalog || res.data || res || {}; _renderUI(_buildOpts(nbHabCatalog)); })
            .catch(function(){ panel.innerHTML = '<p class="pl-nb-loading">Error al cargar cat\u00e1logo.</p>'; });
    }

    // ── KPIs (notebook page) ────────────────────────────────────────────────────
    function _nbpLoadKpi(p) {
        var panel = document.getElementById('pl-nbp-panel-kpi');
        var items = Array.isArray(p.kpis) ? p.kpis.slice() : [];
        function _rowHtml(it, idx) {
            var nombre = String((it && it.nombre) || '');
            var meta = String((it && it.meta) || '');
            var periodicidad = String((it && it.periodicidad) || '');
            return (
                '<div class="grid grid-cols-1 md:grid-cols-[1fr_180px_180px_auto] gap-2 items-end pl-nbp-kpi-row" data-idx="' + idx + '">' +
                    '<div>' +
                        '<label class="pl-label">Nombre KPI</label>' +
                        '<input class="pl-input input input-bordered campo pl-nbp-kpi-nombre" value="' + _esc(nombre) + '">' +
                    '</div>' +
                    '<div>' +
                        '<label class="pl-label">Meta</label>' +
                        '<input class="pl-input input input-bordered campo pl-nbp-kpi-meta" value="' + _esc(meta) + '">' +
                    '</div>' +
                    '<div>' +
                        '<label class="pl-label">Periodicidad</label>' +
                        '<select class="pl-select select select-bordered campo pl-nbp-kpi-period">' +
                            '<option value=""' + (periodicidad ? '' : ' selected') + '>— Seleccionar —</option>' +
                            '<option value="Diaria"' + (periodicidad === 'Diaria' ? ' selected' : '') + '>Diaria</option>' +
                            '<option value="Semanal"' + (periodicidad === 'Semanal' ? ' selected' : '') + '>Semanal</option>' +
                            '<option value="Mensual"' + (periodicidad === 'Mensual' ? ' selected' : '') + '>Mensual</option>' +
                            '<option value="Trimestral"' + (periodicidad === 'Trimestral' ? ' selected' : '') + '>Trimestral</option>' +
                            '<option value="Anual"' + (periodicidad === 'Anual' ? ' selected' : '') + '>Anual</option>' +
                        '</select>' +
                    '</div>' +
                    '<button class="btn btn-sm btn-error btn-outline pl-nbp-kpi-del" type="button">&times;</button>' +
                '</div>'
            );
        }
        function _render() {
            var html = '<div id="pl-nbp-kpi-list" style="display:flex;flex-direction:column;gap:10px;">';
            if (!items.length) html += '<p class="pl-nb-loading">Sin KPIs agregados.</p>';
            else html += items.map(function(it, idx) { return _rowHtml(it, idx); }).join('');
            html += '</div>';
            html += '<div style="margin-top:10px;"><button id="pl-nbp-kpi-add" class="btn btn-sm btn-outline" type="button">Agregar KPI</button></div>';
            panel.innerHTML = html;
            panel.querySelectorAll('.pl-nbp-kpi-del').forEach(function(btn) {
                btn.addEventListener('click', function() {
                    var row = btn.closest('.pl-nbp-kpi-row');
                    if (!row) return;
                    var idx = parseInt(row.getAttribute('data-idx'), 10);
                    if (Number.isNaN(idx)) return;
                    items.splice(idx, 1);
                    _render();
                });
            });
            var add = document.getElementById('pl-nbp-kpi-add');
            if (add) {
                add.addEventListener('click', function() {
                    items.push({ nombre: '', meta: '', periodicidad: '' });
                    _render();
                });
            }
        }
        _render();
    }

    // ── Guardar (notebook page) ─────────────────────────────────────────────────
    document.getElementById('pl-nbp-btn-save').addEventListener('click', function() {
        if (!nbpPuestoId) return;
        var habs = [];
        document.querySelectorAll('#pl-nbp-panel-hab .pl-nb-hab-row').forEach(function(row) {
            var n = row.querySelector('.pl-nb-hab-nombre');
            var b = row.querySelector('.pl-nb-hab-badge');
            if (n) habs.push({ nombre: n.textContent.trim(), minimo: parseInt((b ? b.textContent : '0'), 10) || 0 });
        });
        var kpis = [];
        document.querySelectorAll('#pl-nbp-panel-kpi .pl-nbp-kpi-row').forEach(function(row) {
            var nombreEl = row.querySelector('.pl-nbp-kpi-nombre');
            var metaEl = row.querySelector('.pl-nbp-kpi-meta');
            var periodEl = row.querySelector('.pl-nbp-kpi-period');
            var nombre = nombreEl ? nombreEl.value.trim() : '';
            var meta = metaEl ? metaEl.value.trim() : '';
            var periodicidad = periodEl ? periodEl.value.trim() : '';
            if (!nombre && !meta && !periodicidad) return;
            kpis.push({ nombre: nombre, meta: meta, periodicidad: periodicidad });
        });
        fetch('/api/puestos-laborales', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'update_notebook', id: nbpPuestoId, habilidades_requeridas: habs, kpis: kpis })
        })
        .then(function(r){ return r.json(); })
        .then(function(res){
            if (res.success) {
                puestos = res.data; renderTable();
                var msg = document.getElementById('pl-nbp-saved');
                msg.style.display = 'inline';
                setTimeout(function(){ msg.style.display = 'none'; }, 2200);
            }
        });
    });

    setAreaOptions();   // poblar el select inmediatamente con __INITIAL_AREAS__
    loadAreas();        // luego actualizar desde la API (async)
    _loadHabCatalogForForm();
    loadPuestos();
    setPlView('list');
    ensurePuestosAccordionVisible();
})();
