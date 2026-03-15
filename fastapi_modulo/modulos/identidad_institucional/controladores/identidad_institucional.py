from __future__ import annotations

from html import escape
from typing import Optional

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse


router = APIRouter()


def _render_identidad_institucional_page(request: Request) -> HTMLResponse:
    from fastapi_modulo.main import (
        DEFAULT_LOGIN_IDENTITY,
        _build_login_asset_url,
        _load_login_identity,
        render_backend_page,
    )

    identity = _load_login_identity()
    favicon_url = _build_login_asset_url(identity.get("favicon_filename"), DEFAULT_LOGIN_IDENTITY["favicon_filename"])
    safe_company_short_name = escape(identity.get("company_short_name", DEFAULT_LOGIN_IDENTITY["company_short_name"]))
    safe_login_message = escape(identity.get("login_message", DEFAULT_LOGIN_IDENTITY["login_message"]))
    current_menu_position = (identity.get("menu_position") or DEFAULT_LOGIN_IDENTITY["menu_position"]).strip().lower()
    if current_menu_position not in {"arriba", "abajo"}:
        current_menu_position = DEFAULT_LOGIN_IDENTITY["menu_position"]
    logo_url = _build_login_asset_url(identity.get("logo_filename"), DEFAULT_LOGIN_IDENTITY["logo_filename"])
    desktop_bg_url = _build_login_asset_url(identity.get("desktop_bg_filename"), DEFAULT_LOGIN_IDENTITY["desktop_bg_filename"])
    mobile_bg_url = _build_login_asset_url(identity.get("mobile_bg_filename"), DEFAULT_LOGIN_IDENTITY["mobile_bg_filename"])
    loaded_assets = sum(1 for value in [favicon_url, logo_url, desktop_bg_url, mobile_bg_url] if (value or "").strip())
    consistency = max(60, min(100, int(round((loaded_assets / 4) * 100)))) if loaded_assets else 60
    saved_flag = request.query_params.get("saved")
    saved_message = "<p class='id-flash'>Identidad institucional actualizada.</p>" if saved_flag == "1" else ""
    content = f"""
        <section class="id-page">
            <style>
                .id-page {{
                    --bg: #f6f8fc;
                    --surface: rgba(255,255,255,.88);
                    --text: #0f172a;
                    --muted: #64748b;
                    --border: rgba(148,163,184,.38);
                    --shadow: 0 18px 40px rgba(15,23,42,.08);
                    --shadow-soft: 0 10px 22px rgba(15,23,42,.06);
                    --radius: 18px;
                    --primary: #0f3d2e;
                    --primary-2: #1f6f52;
                    --ok: #16a34a;
                    --warn: #f59e0b;
                    --crit: #ef4444;
                    width: 100%;
                    font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
                    color: var(--text);
                    background:
                      radial-gradient(1200px 640px at 15% 0%, rgba(15,61,46,.10), transparent 58%),
                      radial-gradient(1000px 540px at 90% 6%, rgba(37,99,235,.10), transparent 55%),
                      var(--bg);
                    border-radius: 18px;
                }}
                .id-wrap {{ width: 100%; margin: 0 auto; padding: 18px 0 34px; }}
                .id-flash {{
                    margin: 0 0 12px;
                    padding: 10px 12px;
                    border-radius: 12px;
                    background: rgba(22,163,74,.10);
                    border: 1px solid rgba(22,163,74,.20);
                    color: #166534;
                    font-weight: 700;
                }}
                .id-btn {{
                    border-radius: 14px;
                    padding: 10px 14px;
                    font-weight: 800;
                    border: 1px solid var(--border);
                    background: rgba(255,255,255,.75);
                    cursor: pointer;
                    box-shadow: var(--shadow-soft);
                    transition: transform .15s ease, box-shadow .15s ease, background .15s ease;
                }}
                .id-btn:hover {{ transform: translateY(-1px); box-shadow: var(--shadow); background: rgba(255,255,255,.95); }}
                .id-btn--primary {{
                    background: linear-gradient(135deg, var(--primary), var(--primary-2));
                    color: #fff;
                    border-color: rgba(15,61,46,.35);
                }}
                .id-btn--primary2 {{
                    background: rgba(37,99,235,.12);
                    color: #1d4ed8;
                    border-color: rgba(37,99,235,.24);
                }}
                .id-btn--soft {{
                    background: rgba(15,61,46,.10);
                    border-color: rgba(15,61,46,.18);
                    color: #0b2a20;
                }}
                .id-btn--ghost2 {{
                    background: rgba(255,255,255,.85);
                    color: var(--text);
                    border-color: var(--border);
                }}
                .id-btn--ghost3 {{
                    background: rgba(255,255,255,.90);
                    color: var(--text);
                    border-color: var(--border);
                }}
                .id-btn--danger {{
                    border-color: rgba(239,68,68,.25);
                    color: #991b1b;
                    background: rgba(239,68,68,.08);
                }}
                .id-stats {{
                    display: grid;
                    grid-template-columns: repeat(4, minmax(0, 1fr));
                    gap: 12px;
                    margin-bottom: 14px;
                }}
                .id-stat {{
                    background: var(--surface);
                    border: 1px solid var(--border);
                    border-radius: var(--radius);
                    box-shadow: var(--shadow-soft);
                    padding: 14px;
                }}
                .id-stat__k {{ color: var(--muted); font-size: 12px; font-weight: 700; }}
                .id-stat__v {{ margin-top: 8px; font-size: 28px; font-weight: 900; letter-spacing: -0.02em; }}
                .id-stat__meta {{ margin-top: 8px; display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }}
                .id-chip {{
                    font-size: 12px;
                    padding: 6px 10px;
                    border-radius: 999px;
                    background: rgba(15,23,42,.05);
                    border: 1px solid rgba(15,23,42,.08);
                    color: rgba(15,23,42,.72);
                }}
                .id-chip--ok {{ background: rgba(22,163,74,.10); border-color: rgba(22,163,74,.20); color: #166534; }}
                .id-bar {{
                    height: 10px;
                    flex: 1 1 auto;
                    min-width: 110px;
                    border-radius: 999px;
                    background: rgba(148,163,184,.25);
                    border: 1px solid rgba(148,163,184,.25);
                    overflow: hidden;
                }}
                .id-bar__fill {{
                    height: 100%;
                    border-radius: 999px;
                    background: linear-gradient(90deg, rgba(15,61,46,1), rgba(31,111,82,1));
                }}
                .id-grid {{ display: grid; grid-template-columns: 1.1fr .9fr; gap: 14px; align-items: start; margin-bottom: 14px; }}
                .id-card {{
                    background: var(--surface);
                    border: 1px solid var(--border);
                    border-radius: 22px;
                    box-shadow: var(--shadow-soft);
                    overflow: hidden;
                }}
                .id-card--pad {{ padding: 16px; }}
                .id-card__head {{
                    display: flex;
                    align-items: flex-start;
                    justify-content: space-between;
                    gap: 12px;
                    margin-bottom: 14px;
                }}
                .id-card__head h2 {{ margin: 0; font-size: 20px; letter-spacing: -0.02em; }}
                .id-card__head p {{ margin: 6px 0 0; color: var(--muted); font-size: 13px; }}
                .id-card__tools {{ display: flex; gap: 10px; align-items: center; }}
                .id-pill {{
                    font-size: 12px;
                    padding: 6px 10px;
                    border-radius: 999px;
                    background: rgba(255,255,255,.70);
                    border: 1px solid var(--border);
                    color: rgba(15,23,42,.72);
                }}
                .id-pill--soft {{
                    background: rgba(15,61,46,.10);
                    border-color: rgba(15,61,46,.18);
                    color: #0b2a20;
                }}
                .id-iconbtn {{
                    width: 38px;
                    height: 38px;
                    border-radius: 14px;
                    border: 1px solid var(--border);
                    background: rgba(255,255,255,.75);
                    box-shadow: var(--shadow-soft);
                    cursor: pointer;
                }}
                .id-form {{ display: flex; flex-direction: column; gap: 12px; }}
                .id-field {{ display: flex; flex-direction: column; gap: 8px; }}
                .id-field label {{ font-size: 13px; font-weight: 700; color: #334155; }}
                .id-field input,
                .id-field textarea {{
                    border: 1px solid var(--border);
                    border-radius: 14px;
                    padding: 12px;
                    background: rgba(255,255,255,.85);
                    box-shadow: 0 10px 20px rgba(15,23,42,.04);
                }}
                .id-field textarea {{ min-height: 90px; resize: vertical; }}
                .id-help {{ color: var(--muted); font-size: 12px; }}
                .id-actions {{ display: flex; gap: 10px; justify-content: flex-end; margin-top: 4px; }}
                .id-tips {{ display: flex; flex-direction: column; gap: 10px; }}
                .id-tip {{
                    display: flex;
                    gap: 10px;
                    align-items: flex-start;
                    background: rgba(255,255,255,.82);
                    border: 1px solid rgba(148,163,184,.30);
                    border-radius: 14px;
                    padding: 10px;
                }}
                .id-tip__icon {{ font-size: 18px; }}
                .id-tip__text strong {{ display: block; font-size: 13px; }}
                .id-tip__text p {{ margin: 4px 0 0; color: var(--muted); font-size: 12px; line-height: 1.35; }}
                .id-divider {{ height: 1px; background: rgba(148,163,184,.25); margin: 4px 0; }}
                .id-cta {{ display: flex; justify-content: space-between; align-items: center; gap: 10px; }}
                .id-cta p {{ margin: 4px 0 0; color: var(--muted); font-size: 12px; }}
                .id-assets__grid {{ display: flex; flex-direction: column; gap: 10px; }}
                .id-asset {{
                    display: grid;
                    grid-template-columns: 240px minmax(0, 1fr) auto;
                    gap: 14px;
                    align-items: center;
                    background: rgba(255,255,255,.86);
                    border: 1px solid rgba(148,163,184,.30);
                    border-radius: 16px;
                    padding: 12px;
                }}
                .id-asset__label {{ display: flex; gap: 8px; align-items: center; }}
                .id-asset__meta {{ margin-top: 4px; font-size: 12px; color: var(--muted); }}
                .id-dot {{ width: 10px; height: 10px; border-radius: 999px; display: inline-block; }}
                .id-dot--ok {{ background: var(--ok); box-shadow: 0 0 0 6px rgba(22,163,74,.10); }}
                .id-asset__preview {{
                    border: 1px solid rgba(148,163,184,.30);
                    background: rgba(248,250,252,.95);
                    border-radius: 12px;
                    overflow: hidden;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                .id-asset__preview img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
                .id-asset__preview--square {{ width: 96px; height: 96px; }}
                .id-asset__preview--square img {{ object-fit: contain; padding: 8px; }}
                .id-asset__preview--logo {{ height: 120px; }}
                .id-asset__preview--logo img {{ object-fit: contain; padding: 10px; }}
                .id-asset__preview--wide {{ height: 140px; }}
                .id-asset__actions {{ display: flex; flex-direction: column; gap: 8px; min-width: 116px; }}
                @media (max-width: 1200px) {{
                    .id-stats {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
                    .id-grid {{ grid-template-columns: 1fr; }}
                    .id-asset {{ grid-template-columns: 1fr; }}
                    .id-asset__actions {{ flex-direction: row; }}
                }}
                @media (max-width: 640px) {{
                    .id-stats {{ grid-template-columns: 1fr; }}
                    .id-actions {{ justify-content: flex-start; flex-wrap: wrap; }}
                    .id-cta {{ flex-direction: column; align-items: flex-start; }}
                }}
            </style>
            <div class="id-wrap">
                <form id="identity-form" method="post" action="/identidad-institucional" enctype="multipart/form-data">
                    <input type="hidden" id="remove_favicon" name="remove_favicon" value="0">
                    <input type="hidden" id="remove_logo" name="remove_logo" value="0">
                    <input type="hidden" id="remove_desktop" name="remove_desktop" value="0">
                    <input type="hidden" id="remove_mobile" name="remove_mobile" value="0">
                    <div style="display:none;">
                        <input type="file" id="favicon" name="favicon" accept="image/*">
                        <input type="file" id="logo_empresa" name="logo_empresa" accept="image/*">
                        <input type="file" id="fondo_escritorio" name="fondo_escritorio" accept="image/*">
                        <input type="file" id="fondo_movil" name="fondo_movil" accept="image/*">
                    </div>
                    {saved_message}
                    <section class="id-card id-card--pad" style="margin-bottom:14px;">
                        <div class="flex flex-wrap items-center justify-between gap-4">
                            <div>
                                <h2 style="margin:0;font-size:18px;">Estilo visual del sistema</h2>
                                <p style="margin:6px 0 0;color:var(--muted);font-size:13px;">Elige entre estilo original o estilo moderno para sidebar y contenedor principal.</p>
                            </div>
                            <label class="label cursor-pointer gap-3">
                                <span id="identity-sidebar-style-label" class="font-semibold text-sm" style="color:#0f3d2e;">Original</span>
                                <input id="identity-sidebar-style-switch" type="checkbox" class="toggle toggle-success">
                            </label>
                        </div>
                    </section>
                    <script>
                        (function () {{
                            var apply = function (variant) {{
                                var modern = variant === 'modern';
                                document.documentElement.classList.toggle('ui-sidebar-modern', modern);
                                var sw = document.getElementById('identity-sidebar-style-switch');
                                var label = document.getElementById('identity-sidebar-style-label');
                                if (sw) sw.checked = modern;
                                if (label) label.textContent = modern ? 'Moderno' : 'Original';
                            }};
                            var bind = function () {{
                                var sw = document.getElementById('identity-sidebar-style-switch');
                                if (!sw) return;
                                try {{
                                    apply(window.localStorage.getItem('sipet_sidebar_style_variant') || 'original');
                                }} catch (e) {{
                                    apply('original');
                                }}
                                sw.addEventListener('change', function () {{
                                    var variant = sw.checked ? 'modern' : 'original';
                                    apply(variant);
                                    try {{ window.localStorage.setItem('sipet_sidebar_style_variant', variant); }} catch (e) {{}}
                                }});
                            }};
                            if (document.readyState === 'loading') {{
                                document.addEventListener('DOMContentLoaded', bind);
                            }} else {{
                                bind();
                            }}
                        }})();
                    </script>
                    <section class="id-card id-card--pad" style="margin-bottom:14px;">
                        <div class="flex flex-wrap items-center justify-between gap-4">
                            <div>
                                <h2 style="margin:0;font-size:18px;">Posición del menu</h2>
                                <p style="margin:6px 0 0;color:var(--muted);font-size:13px;">Arriba mantiene el menú actual. Abajo activa la barra móvil inferior en páginas públicas.</p>
                            </div>
                            <div class="flex items-center gap-4">
                                <label class="label cursor-pointer gap-2">
                                    <input type="radio" name="menu_position" value="arriba" {"checked" if current_menu_position == "arriba" else ""}>
                                    <span class="font-semibold text-sm" style="color:#0f3d2e;">Arriba</span>
                                </label>
                                <label class="label cursor-pointer gap-2">
                                    <input type="radio" name="menu_position" value="abajo" {"checked" if current_menu_position == "abajo" else ""}>
                                    <span class="font-semibold text-sm" style="color:#0f3d2e;">Abajo</span>
                                </label>
                            </div>
                        </div>
                    </section>
                    <section class="id-stats">
                        <article class="id-stat">
                            <div class="id-stat__k">Nombre corto</div>
                            <div class="id-stat__v">{safe_company_short_name}</div>
                            <div class="id-stat__meta"><span class="id-chip">Activo</span></div>
                        </article>
                        <article class="id-stat">
                            <div class="id-stat__k">Recursos cargados</div>
                            <div class="id-stat__v">{loaded_assets}</div>
                            <div class="id-stat__meta"><span class="id-chip id-chip--ok">Completo</span></div>
                        </article>
                        <article class="id-stat">
                            <div class="id-stat__k">Formato recomendado</div>
                            <div class="id-stat__v">SVG/PNG</div>
                            <div class="id-stat__meta"><span class="id-chip">Alta nitidez</span></div>
                        </article>
                        <article class="id-stat">
                            <div class="id-stat__k">Consistencia visual</div>
                            <div class="id-stat__v">{consistency}%</div>
                            <div class="id-stat__meta">
                                <div class="id-bar"><div class="id-bar__fill" style="width:{consistency}%"></div></div>
                                <span class="id-chip id-chip--ok">Optimo</span>
                            </div>
                        </article>
                    </section>
                    <section class="id-grid">
                        <section class="id-card id-card--pad">
                            <header class="id-card__head">
                                <div>
                                    <h2>Datos institucionales</h2>
                                    <p>Estos datos se muestran en login y en elementos de marca del sistema.</p>
                                </div>
                                <div class="id-card__tools">
                                    <span class="id-pill id-pill--soft">Configuracion</span>
                                    <button class="id-iconbtn" type="button" title="Ayuda">?</button>
                                </div>
                            </header>
                            <div class="id-form">
                                <div class="id-field">
                                    <label for="company_short_name">Nombre corto de la empresa</label>
                                    <input class="campo campo-personalizado" id="company_short_name" name="company_short_name" type="text" value="{safe_company_short_name}" placeholder="Ej. AVAN">
                                    <div class="id-help">Se usa en titulos, encabezados y login. Recomendado: 3-18 caracteres.</div>
                                </div>
                                <div class="id-field">
                                    <label for="login_message">Mensaje para pantalla de login</label>
                                    <textarea class="campo campo-personalizado" id="login_message" name="login_message" placeholder="Ej. Incrementando el nivel de eficiencia">{safe_login_message}</textarea>
                                    <div class="id-help">Sugerencia: frase corta y orientada a valor.</div>
                                </div>
                                <div class="id-actions">
                                    <button class="id-btn id-btn--primary" type="submit" form="identity-form">Guardar</button>
                                    <button class="id-btn id-btn--soft" type="reset">Restablecer</button>
                                </div>
                            </div>
                        </section>
                        <aside class="id-card id-card--pad">
                            <header class="id-card__head">
                                <div>
                                    <h2>Recomendaciones</h2>
                                    <p>Buenas practicas para mantener calidad visual en backend y movil.</p>
                                </div>
                                <div class="id-card__tools"><span class="id-pill">Guia rapida</span></div>
                            </header>
                            <div class="id-tips">
                                <div class="id-tip"><div class="id-tip__icon">L</div><div class="id-tip__text"><strong>Logo</strong><p>Preferible SVG; si usas PNG que sea transparente y amplio.</p></div></div>
                                <div class="id-tip"><div class="id-tip__icon">F</div><div class="id-tip__text"><strong>Favicon</strong><p>Usa 32x32 y 64x64 con buena legibilidad.</p></div></div>
                                <div class="id-tip"><div class="id-tip__icon">M</div><div class="id-tip__text"><strong>Fondo movil</strong><p>Formato vertical con punto focal centrado.</p></div></div>
                                <div class="id-tip"><div class="id-tip__icon">E</div><div class="id-tip__text"><strong>Fondo escritorio</strong><p>Recomendado 1920x1080 y buen contraste.</p></div></div>
                                <div class="id-divider"></div>
                                <div class="id-cta">
                                    <div><strong>Vista previa</strong><p>Valida como se vera el login con los recursos actuales.</p></div>
                                    <button class="id-btn id-btn--ghost2" type="button">Abrir preview</button>
                                </div>
                            </div>
                        </aside>
                    </section>
                    <section class="id-card id-card--pad id-assets">
                        <header class="id-card__head">
                            <div>
                                <h2>Recursos visuales</h2>
                                <p>Administra favicon, logo y fondos para backend y movil.</p>
                            </div>
                            <div class="id-card__tools">
                                <span class="id-pill">4 recursos</span>
                            </div>
                        </header>
                        <div class="id-assets__grid">
                            <article class="id-asset">
                                <div class="id-asset__left">
                                    <div class="id-asset__label"><span class="id-dot id-dot--ok"></span><strong>Favicon</strong></div>
                                    <div class="id-asset__meta">Recomendado: 32x32 / 64x64 - PNG/ICO</div>
                                </div>
                                <div class="id-asset__preview id-asset__preview--square">
                                    <img src="{favicon_url}" alt="Favicon">
                                </div>
                                <div class="id-asset__actions identity-asset-actions">
                                    <button class="id-btn id-btn--ghost3 identity-asset-edit" data-target-input="favicon" type="button">Editar</button>
                                    <button class="id-btn id-btn--danger identity-asset-delete" data-target-remove="remove_favicon" type="button">Eliminar</button>
                                </div>
                            </article>
                            <article class="id-asset">
                                <div class="id-asset__left">
                                    <div class="id-asset__label"><span class="id-dot id-dot--ok"></span><strong>Logo de la empresa</strong></div>
                                    <div class="id-asset__meta">Preferible SVG - alternativa PNG transparente</div>
                                </div>
                                <div class="id-asset__preview id-asset__preview--logo">
                                    <img src="{logo_url}" alt="Logo">
                                </div>
                                <div class="id-asset__actions identity-asset-actions">
                                    <button class="id-btn id-btn--ghost3 identity-asset-edit" data-target-input="logo_empresa" type="button">Editar</button>
                                    <button class="id-btn id-btn--danger identity-asset-delete" data-target-remove="remove_logo" type="button">Eliminar</button>
                                </div>
                            </article>
                            <article class="id-asset">
                                <div class="id-asset__left">
                                    <div class="id-asset__label"><span class="id-dot id-dot--ok"></span><strong>Fondo de escritorio</strong></div>
                                    <div class="id-asset__meta">Recomendado: 1920x1080 - JPG/PNG</div>
                                </div>
                                <div class="id-asset__preview id-asset__preview--wide">
                                    <img src="{desktop_bg_url}" alt="Fondo de escritorio">
                                </div>
                                <div class="id-asset__actions identity-asset-actions">
                                    <button class="id-btn id-btn--ghost3 identity-asset-edit" data-target-input="fondo_escritorio" type="button">Editar</button>
                                    <button class="id-btn id-btn--danger identity-asset-delete" data-target-remove="remove_desktop" type="button">Eliminar</button>
                                </div>
                            </article>
                            <article class="id-asset">
                                <div class="id-asset__left">
                                    <div class="id-asset__label"><span class="id-dot id-dot--ok"></span><strong>Fondo movil</strong></div>
                                    <div class="id-asset__meta">Recomendado: 1080x1920 - JPG/PNG</div>
                                </div>
                                <div class="id-asset__preview id-asset__preview--wide">
                                    <img src="{mobile_bg_url}" alt="Fondo movil">
                                </div>
                                <div class="id-asset__actions identity-asset-actions">
                                    <button class="id-btn id-btn--ghost3 identity-asset-edit" data-target-input="fondo_movil" type="button">Editar</button>
                                    <button class="id-btn id-btn--danger identity-asset-delete" data-target-remove="remove_mobile" type="button">Eliminar</button>
                                </div>
                            </article>
                        </div>
                    </section>
                </form>
                <script>
                    (function () {{
                        var form = document.getElementById('identity-form');
                        if (!form) return;

                        function byId(id) {{
                            return document.getElementById(id);
                        }}

                        function bindFileInput(inputId) {{
                            var input = byId(inputId);
                            if (!input) return;
                            input.addEventListener('change', function () {{
                                if (!input.files || !input.files.length) return;
                                form.requestSubmit ? form.requestSubmit() : form.submit();
                            }});
                        }}

                        document.querySelectorAll('.identity-asset-edit[data-target-input]').forEach(function (button) {{
                            button.addEventListener('click', function () {{
                                var inputId = button.getAttribute('data-target-input') || '';
                                var input = byId(inputId);
                                if (!input) return;
                                var removeId = {{
                                    favicon: 'remove_favicon',
                                    logo_empresa: 'remove_logo',
                                    fondo_escritorio: 'remove_desktop',
                                    fondo_movil: 'remove_mobile'
                                }}[inputId];
                                if (removeId && byId(removeId)) {{
                                    byId(removeId).value = '0';
                                }}
                                input.click();
                            }});
                        }});

                        document.querySelectorAll('.identity-asset-delete[data-target-remove]').forEach(function (button) {{
                            button.addEventListener('click', function () {{
                                var removeId = button.getAttribute('data-target-remove') || '';
                                var removeInput = byId(removeId);
                                if (!removeInput) return;
                                removeInput.value = '1';
                                form.requestSubmit ? form.requestSubmit() : form.submit();
                            }});
                        }});

                        bindFileInput('favicon');
                        bindFileInput('logo_empresa');
                        bindFileInput('fondo_escritorio');
                        bindFileInput('fondo_movil');
                    }})();
                </script>
            </div>
        </section>
    """
    return render_backend_page(
        request,
        title="Identidad institucional",
        description="Configuración de identidad para la pantalla de login.",
        content=content,
        hide_floating_actions=True,
        show_page_header=True,
    )


@router.get("/identidad-institucional", response_class=HTMLResponse)
def identidad_institucional_page(request: Request):
    from fastapi_modulo.main import require_admin_or_superadmin

    require_admin_or_superadmin(request)
    return _render_identidad_institucional_page(request)


@router.get("/identidad-institucional/", response_class=HTMLResponse)
def identidad_institucional_page_slash(request: Request):
    from fastapi_modulo.main import require_admin_or_superadmin

    require_admin_or_superadmin(request)
    return RedirectResponse(url="/identidad-institucional", status_code=307)


@router.post("/identidad-institucional", response_class=HTMLResponse)
async def identidad_institucional_save(
    request: Request,
    company_short_name: str = Form(""),
    login_message: str = Form(""),
    menu_position: str = Form("arriba"),
    favicon: Optional[UploadFile] = File(None),
    logo_empresa: Optional[UploadFile] = File(None),
    fondo_escritorio: Optional[UploadFile] = File(None),
    fondo_movil: Optional[UploadFile] = File(None),
    remove_favicon: str = Form("0"),
    remove_logo: str = Form("0"),
    remove_desktop: str = Form("0"),
    remove_mobile: str = Form("0"),
):
    from fastapi_modulo.main import (
        DEFAULT_LOGIN_IDENTITY,
        _load_login_identity,
        _remove_login_image_if_custom,
        _save_login_identity,
        _store_login_image,
        require_admin_or_superadmin,
    )

    require_admin_or_superadmin(request)
    current = _load_login_identity()
    current["company_short_name"] = company_short_name.strip() or DEFAULT_LOGIN_IDENTITY["company_short_name"]
    current["login_message"] = login_message.strip() or DEFAULT_LOGIN_IDENTITY["login_message"]
    current["menu_position"] = "abajo" if str(menu_position).strip().lower() == "abajo" else "arriba"

    if str(remove_favicon).strip() == "1":
        _remove_login_image_if_custom(current.get("favicon_filename"))
        current["favicon_filename"] = DEFAULT_LOGIN_IDENTITY["favicon_filename"]
    if str(remove_logo).strip() == "1":
        _remove_login_image_if_custom(current.get("logo_filename"))
        current["logo_filename"] = DEFAULT_LOGIN_IDENTITY["logo_filename"]
    if str(remove_desktop).strip() == "1":
        _remove_login_image_if_custom(current.get("desktop_bg_filename"))
        current["desktop_bg_filename"] = DEFAULT_LOGIN_IDENTITY["desktop_bg_filename"]
    if str(remove_mobile).strip() == "1":
        _remove_login_image_if_custom(current.get("mobile_bg_filename"))
        current["mobile_bg_filename"] = DEFAULT_LOGIN_IDENTITY["mobile_bg_filename"]

    new_favicon = await _store_login_image(favicon, "favicon") if favicon else None
    if new_favicon:
        _remove_login_image_if_custom(current.get("favicon_filename"))
        current["favicon_filename"] = new_favicon

    new_logo = await _store_login_image(logo_empresa, "logo_empresa") if logo_empresa else None
    if new_logo:
        _remove_login_image_if_custom(current.get("logo_filename"))
        current["logo_filename"] = new_logo

    new_desktop = await _store_login_image(fondo_escritorio, "fondo_escritorio") if fondo_escritorio else None
    if new_desktop:
        _remove_login_image_if_custom(current.get("desktop_bg_filename"))
        current["desktop_bg_filename"] = new_desktop

    new_mobile = await _store_login_image(fondo_movil, "fondo_movil") if fondo_movil else None
    if new_mobile:
        _remove_login_image_if_custom(current.get("mobile_bg_filename"))
        current["mobile_bg_filename"] = new_mobile

    _save_login_identity(current)
    try:
        from fastapi_modulo.modulos.frontend.controladores import frontend as _frontend_module

        _frontend_module._page_cache.clear()
    except Exception:
        pass
    return RedirectResponse(url="/identidad-institucional?saved=1", status_code=303)
