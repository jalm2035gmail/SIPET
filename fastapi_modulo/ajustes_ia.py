from html import escape
import json
from urllib import error, request
from urllib.parse import urlparse, urlunparse

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse

from fastapi_modulo.db import SessionLocal, IAConfig

router = APIRouter()


def _normalize_provider_name(value: str) -> str:
    raw = str(value or "").strip().lower()
    if raw in {"chatgpt", "gpt", "gpt4"}:
        return "openai"
    return raw


def _parse_provider_chain(raw_value: str) -> list[str]:
    raw = str(raw_value or "").strip()
    if not raw:
        return []
    items: list[str] = []
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                items = [str(item or "").strip() for item in parsed]
        except Exception:
            items = []
    if not items:
        items = [part.strip() for part in raw.split(",")]
    out: list[str] = []
    for item in items:
        normalized = _normalize_provider_name(item)
        if normalized in {"ollama", "openai", "deepseek"} and normalized not in out:
            out.append(normalized)
    return out


def _normalize_ollama_generate_url(raw_url: str) -> str:
    raw = str(raw_url or "").strip()
    if not raw:
        return "http://127.0.0.1:11434/api/generate"
    if "://" not in raw:
        raw = f"http://{raw}"
    parsed = urlparse(raw)
    path = str(parsed.path or "").rstrip("/")
    if path in {"", "/api"}:
        parsed = parsed._replace(path="/api/generate")
    return urlunparse(parsed)


def _ollama_tags_url_from_generate_url(generate_url: str) -> str:
    parsed = urlparse(_normalize_ollama_generate_url(generate_url))
    return urlunparse(parsed._replace(path="/api/tags", query="", fragment=""))


def _check_ollama_connected(generate_url: str, timeout_seconds: int) -> tuple[bool, str]:
    tags_url = _ollama_tags_url_from_generate_url(generate_url)
    try:
        req = request.Request(tags_url, headers={"Accept": "application/json"}, method="GET")
        with request.urlopen(req, timeout=max(1, min(int(timeout_seconds or 3), 6))) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            status = int(getattr(resp, "status", 200) or 200)
            if status < 200 or status >= 300:
                return False, f"Ollama HTTP {status}"
            try:
                payload = json.loads(body or "{}")
                models = payload.get("models", []) if isinstance(payload, dict) else []
                return True, f"models={len(models)}"
            except Exception:
                return True, "respuesta sin JSON parseable"
    except error.HTTPError as exc:
        return False, f"Ollama HTTP {int(getattr(exc, 'code', 0) or 0)}"
    except Exception as exc:
        return False, str(exc)


def _ia_form_content(
    ai_provider: str = "",
    ai_api_key: str = "",
    ai_base_url: str = "",
    ai_model: str = "",
    ai_timeout: int = 30,
    ai_temperature: float = 0.7,
    ai_top_p: float = 0.9,
    ai_num_predict: int = 700,
) -> str:
    provider_raw = str(ai_provider or "").strip()
    provider_chain = _parse_provider_chain(provider_raw)
    if len(provider_chain) >= 2:
        provider_norm = "hybrid"
        hybrid_primary = provider_chain[0]
        hybrid_fallback = provider_chain[1]
    else:
        provider_norm = (provider_chain[0] if provider_chain else _normalize_provider_name(provider_raw)) or "ollama"
        if provider_norm not in {"ollama", "openai", "deepseek", "hybrid"}:
            provider_norm = "ollama"
        hybrid_primary = provider_norm if provider_norm in {"ollama", "openai", "deepseek"} else "ollama"
        hybrid_fallback = "openai" if hybrid_primary != "openai" else "deepseek"
    provider_options = [
        ("ollama", "Ollama (local)"),
        ("openai", "OpenAI"),
        ("deepseek", "DeepSeek"),
        ("hybrid", "Hybrid (fallback)"),
    ]
    provider_options_html = "".join(
        f'<option value="{escape(value)}" {"selected" if value == provider_norm else ""}>{escape(label)}</option>'
        for value, label in provider_options
    )
    chain_options = [
        ("ollama", "Ollama"),
        ("openai", "OpenAI"),
        ("deepseek", "DeepSeek"),
    ]
    primary_options_html = "".join(
        f'<option value="{escape(value)}" {"selected" if value == hybrid_primary else ""}>{escape(label)}</option>'
        for value, label in chain_options
    )
    fallback_options_html = "".join(
        f'<option value="{escape(value)}" {"selected" if value == hybrid_fallback else ""}>{escape(label)}</option>'
        for value, label in chain_options
    )
    api_key = escape(str(ai_api_key or ""))
    base_url = escape(str(ai_base_url or ""))
    model = escape(str(ai_model or ""))
    timeout = int(ai_timeout or 30)
    temperature = float(ai_temperature if ai_temperature is not None else 0.7)
    top_p = float(ai_top_p if ai_top_p is not None else 0.9)
    num_predict = int(ai_num_predict if ai_num_predict is not None else 700)
    if timeout < 1:
        timeout = 1
    if timeout > 120:
        timeout = 120
    return f"""
<section class="ia-wrap">
  <style>
    .ia-wrap {{
      max-width: 920px;
      margin: 0 auto;
      display: grid;
      gap: 14px;
    }}
    .ia-card {{
      background: #ffffff;
      border: 1px solid rgba(148,163,184,.30);
      border-radius: 16px;
      box-shadow: 0 10px 22px rgba(15,23,42,.06);
      padding: 18px;
    }}
    .ia-head {{
      display:flex;
      align-items:center;
      gap:12px;
      margin-bottom: 14px;
    }}
    .ia-head-icon {{
      width: 42px;
      height: 42px;
      border-radius: 12px;
      border: 1px solid color-mix(in srgb, var(--sidebar-bottom, #0f172a) 22%, #ffffff 78%);
      background: color-mix(in srgb, var(--sidebar-bottom, #0f172a) 10%, #ffffff 90%);
      display:inline-flex;
      align-items:center;
      justify-content:center;
      flex-shrink:0;
      overflow: hidden;
    }}
    .ia-head-icon img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
    }}
    .ia-head h3 {{
      margin: 0;
      font-size: 20px;
      color: var(--sidebar-bottom, #0f172a);
    }}
    .ia-head p {{
      margin: 4px 0 0;
      color: #64748b;
      font-size: 13px;
    }}
    .ia-grid {{
      display:grid;
      gap: 10px;
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .ia-field {{
      display:grid;
      gap: 6px;
    }}
    .ia-field.full {{
      grid-column: 1 / -1;
    }}
    .ia-field label {{
      font-size: 13px;
      font-weight: 700;
      color: var(--sidebar-bottom, #0f172a);
    }}
    .ia-field input,
    .ia-field select {{
      width:100%;
      border: 1px solid rgba(148,163,184,.36);
      border-radius: 10px;
      padding: 10px 12px;
      box-sizing: border-box;
      font-size: 14px;
      color: #0f172a;
      background: #fff;
    }}
    .ia-actions {{
      margin-top: 4px;
      display:flex;
      align-items:center;
      gap: 12px;
      flex-wrap: wrap;
    }}
    .ia-btn {{
      border: 1px solid var(--sidebar-bottom, #0f172a);
      border-radius: 10px;
      background: var(--sidebar-bottom, #0f172a);
      color: #fff;
      font-size: 14px;
      font-weight: 700;
      padding: 10px 14px;
      cursor: pointer;
    }}
    .ia-help {{
      margin:0;
      color:#64748b;
      font-size: 13px;
    }}
    .ia-ff-grid {{
      display:grid;
      gap: 10px;
      grid-template-columns: 1.2fr 1fr 1fr auto;
      align-items:end;
    }}
    .ia-ff-table-wrap {{
      margin-top: 10px;
      border: 1px solid rgba(148,163,184,.30);
      border-radius: 12px;
      overflow:auto;
      background:#fff;
    }}
    .ia-ff-table {{
      width:100%;
      border-collapse:collapse;
      font-size: 13px;
    }}
    .ia-ff-table th, .ia-ff-table td {{
      padding: 8px 10px;
      border-bottom: 1px solid rgba(148,163,184,.22);
      text-align:left;
      white-space: nowrap;
    }}
    .ia-ff-actions {{
      display:flex;
      gap:6px;
      flex-wrap:wrap;
    }}
    .ia-ff-btn {{
      border: 1px solid rgba(148,163,184,.45);
      border-radius: 8px;
      background: #fff;
      color: #0f172a;
      font-size: 12px;
      font-weight: 700;
      padding: 6px 8px;
      cursor: pointer;
    }}
    @media (max-width: 860px) {{
      .ia-grid {{
        grid-template-columns: 1fr;
      }}
      .ia-ff-grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
  <article class="ia-card">
    <header class="ia-head">
      <span class="ia-head-icon" aria-hidden="true">
        <img src="/templates/imagenes/lobo.jpg" alt="">
      </span>
      <div>
        <h3>Ajustes del Agente IA AVAN</h3>
        <p>Configura proveedor, modelo y parámetros de conexión del agente AVAN.</p>
      </div>
    </header>
    <form method="post" action="/ajustes/ia">
      <div class="ia-grid">
        <div class="ia-field">
          <label for="ai_provider">Proveedor IA</label>
          <select id="ai_provider" name="ai_provider">
            {provider_options_html}
          </select>
        </div>
        <div class="ia-field">
          <label for="ai_model">Modelo</label>
          <input type="text" id="ai_model" name="ai_model" value="{model}"
            placeholder="deepseek-chat | deepseek-reasoner | gpt-4o-mini …">
          <small style="color:#888;font-size:0.78rem;">DeepSeek: <code>deepseek-chat</code> o <code>deepseek-reasoner</code>. Vacío usa el valor por defecto del proveedor.</small>
        </div>
        <div class="ia-field" id="ia-hybrid-primary-row">
          <label for="ai_primary_provider">Proveedor primario</label>
          <select id="ai_primary_provider" name="ai_primary_provider">
            {primary_options_html}
          </select>
        </div>
        <div class="ia-field" id="ia-hybrid-fallback-row">
          <label for="ai_fallback_provider">Proveedor fallback</label>
          <select id="ai_fallback_provider" name="ai_fallback_provider">
            {fallback_options_html}
          </select>
        </div>
        <div class="ia-field full">
          <label for="ai_api_key">API Key</label>
          <input type="password" id="ai_api_key" name="ai_api_key" value="{api_key}">
        </div>
        <div class="ia-field full">
          <label for="ai_base_url">Base URL</label>
          <input type="text" id="ai_base_url" name="ai_base_url" value="{base_url}">
        </div>
        <div class="ia-field">
          <label for="ai_timeout">Timeout (segundos)</label>
          <input type="number" id="ai_timeout" name="ai_timeout" min="1" max="120" value="{timeout}">
        </div>
        <div class="ia-field">
          <label for="ai_temperature">Temperature</label>
          <input type="number" id="ai_temperature" name="ai_temperature" min="0" max="2" step="0.1" value="{temperature}">
          <small style="color:#888;font-size:0.78rem;">0.6–0.8 recomendado. Más alto = más creativo.</small>
        </div>
        <div class="ia-field">
          <label for="ai_top_p">Top P</label>
          <input type="number" id="ai_top_p" name="ai_top_p" min="0" max="1" step="0.05" value="{top_p}">
          <small style="color:#888;font-size:0.78rem;">0.9 recomendado. Controla diversidad del vocabulario.</small>
        </div>
        <div class="ia-field">
          <label for="ai_num_predict">Longitud respuesta (tokens)</label>
          <input type="number" id="ai_num_predict" name="ai_num_predict" min="100" max="4000" step="50" value="{num_predict}">
          <small style="color:#888;font-size:0.78rem;">500–1000 recomendado.</small>
        </div>
      </div>
      <div class="ia-actions">
        <button type="submit" class="ia-btn">Guardar</button>
        <p class="ia-help">En modo <b>hybrid</b> se usan los campos primario/fallback de esta pantalla.</p>
      </div>
    </form>
    <script>
      (function() {{
        const PROVIDERS = [
          {{ value: "ollama",   label: "Ollama" }},
          {{ value: "openai",   label: "OpenAI" }},
          {{ value: "deepseek", label: "DeepSeek" }},
        ];
        const primarySel  = document.getElementById("ai_primary_provider");
        const fallbackSel = document.getElementById("ai_fallback_provider");
        if (!primarySel || !fallbackSel) return;
        const syncFallbackOptions = () => {{
          const chosen  = primarySel.value;
          const current = fallbackSel.value;
          fallbackSel.innerHTML = PROVIDERS
            .filter(p => p.value !== chosen)
            .map(p => `<option value="${{p.value}}"${{p.value === current ? " selected" : ""}}>${{p.label}}</option>`)
            .join("");
          if (!fallbackSel.value || fallbackSel.value === chosen) {{
            fallbackSel.selectedIndex = 0;
          }}
        }};
        primarySel.addEventListener("change", syncFallbackOptions);
        syncFallbackOptions();
      }})();
    </script>
  </article>
  <article class="ia-card">
    <header class="ia-head">
      <span class="ia-head-icon" aria-hidden="true">
        <img src="/templates/icon/ia.svg" alt="">
      </span>
      <div>
        <h3>Feature Flags IA por rol/módulo</h3>
        <p>Controla qué roles pueden usar IA en cada módulo.</p>
      </div>
    </header>
    <div class="ia-ff-grid">
      <label class="ia-field">
        <span>Feature key</span>
        <input type="text" id="ia-ff-feature" value="suggest_objective_text">
      </label>
      <label class="ia-field">
        <span>Módulo</span>
        <input type="text" id="ia-ff-module" placeholder="plan_estrategico, poa, kpis">
      </label>
      <label class="ia-field">
        <span>Rol</span>
        <input type="text" id="ia-ff-role" placeholder="administrador, usuario, ...">
      </label>
      <label class="ia-field">
        <span>Habilitado</span>
        <select id="ia-ff-enabled">
          <option value="1">Sí</option>
          <option value="0">No</option>
        </select>
      </label>
    </div>
    <div class="ia-actions">
      <button type="button" class="ia-btn" id="ia-ff-save">Guardar regla</button>
      <p class="ia-help" id="ia-ff-msg"></p>
    </div>
    <div class="ia-ff-table-wrap">
      <table class="ia-ff-table">
        <thead>
          <tr>
            <th>Feature</th>
            <th>Módulo</th>
            <th>Rol</th>
            <th>Habilitado</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody id="ia-ff-list">
          <tr><td colspan="5" style="color:#64748b;">Cargando reglas...</td></tr>
        </tbody>
      </table>
    </div>
  </article>
  <article class="ia-card">
    <header class="ia-head">
      <span class="ia-head-icon" aria-hidden="true">
        <img src="/templates/icon/ia.svg" alt="">
      </span>
      <div>
        <h3>Jobs IA asíncronos</h3>
        <p>Seguimiento de trabajos IA: pendiente, en proceso, completado o error.</p>
      </div>
    </header>
    <div class="ia-ff-grid">
      <label class="ia-field">
        <span>Módulo</span>
        <input type="text" id="ia-job-module" value="plan_estrategico">
      </label>
      <label class="ia-field" style="grid-column: span 2;">
        <span>Prompt</span>
        <input type="text" id="ia-job-prompt" placeholder="Describe la tarea de IA a procesar">
      </label>
      <label class="ia-field">
        <span>Acción</span>
        <button type="button" class="ia-btn" id="ia-job-create">Crear job</button>
      </label>
    </div>
    <div class="ia-actions">
      <button type="button" class="ia-ff-btn" id="ia-job-refresh">Actualizar</button>
      <p class="ia-help" id="ia-job-msg"></p>
    </div>
    <div class="ia-ff-table-wrap">
      <table class="ia-ff-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>Módulo</th>
            <th>Estado</th>
            <th>Progreso</th>
            <th>Intentos</th>
            <th>Actualizado</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody id="ia-job-list">
          <tr><td colspan="7" style="color:#64748b;">Cargando jobs...</td></tr>
        </tbody>
      </table>
    </div>
  </article>
  <article class="ia-card">
    <header class="ia-head">
      <span class="ia-head-icon" aria-hidden="true">
        <img src="/templates/icon/ia.svg" alt="">
      </span>
      <div>
        <h3>Trazabilidad y operación IA</h3>
        <p>Auditoría visible de interacciones, jobs, reportes y chat RAG.</p>
      </div>
    </header>
    <div class="ia-ff-grid">
      <label class="ia-field">
        <span>Rango (días)</span>
        <input type="number" id="ia-audit-days" min="1" max="365" value="30">
      </label>
      <label class="ia-field">
        <span>Operaciones</span>
        <input type="text" id="ia-audit-ops" value="-" readonly>
      </label>
      <label class="ia-field">
        <span>Error %</span>
        <input type="text" id="ia-audit-err" value="-" readonly>
      </label>
      <label class="ia-field">
        <span>Tokens</span>
        <input type="text" id="ia-audit-tokens" value="-" readonly>
      </label>
    </div>
    <div class="ia-actions">
      <button type="button" class="ia-btn" id="ia-audit-refresh">Actualizar auditoría</button>
      <p class="ia-help" id="ia-audit-msg"></p>
    </div>
    <div class="ia-ff-table-wrap">
      <table class="ia-ff-table">
        <thead>
          <tr>
            <th>Fecha</th>
            <th>Usuario</th>
            <th>Fuente</th>
            <th>Módulo</th>
            <th>Estado</th>
            <th>Modelo</th>
            <th>Tokens</th>
            <th>Costo est.</th>
            <th>Detalle</th>
          </tr>
        </thead>
        <tbody id="ia-audit-list">
          <tr><td colspan="9" style="color:#64748b;">Cargando auditoría...</td></tr>
        </tbody>
      </table>
    </div>
  </article>
  <script>
    (function() {{
      const listEl = document.getElementById('ia-ff-list');
      const msgEl = document.getElementById('ia-ff-msg');
      const featureEl = document.getElementById('ia-ff-feature');
      const moduleEl = document.getElementById('ia-ff-module');
      const roleEl = document.getElementById('ia-ff-role');
      const enabledEl = document.getElementById('ia-ff-enabled');
      const saveBtn = document.getElementById('ia-ff-save');
      const jobListEl = document.getElementById('ia-job-list');
      const jobMsgEl = document.getElementById('ia-job-msg');
      const jobModuleEl = document.getElementById('ia-job-module');
      const jobPromptEl = document.getElementById('ia-job-prompt');
      const jobCreateBtn = document.getElementById('ia-job-create');
      const jobRefreshBtn = document.getElementById('ia-job-refresh');
      const auditDaysEl = document.getElementById('ia-audit-days');
      const auditOpsEl = document.getElementById('ia-audit-ops');
      const auditErrEl = document.getElementById('ia-audit-err');
      const auditTokensEl = document.getElementById('ia-audit-tokens');
      const auditMsgEl = document.getElementById('ia-audit-msg');
      const auditListEl = document.getElementById('ia-audit-list');
      const auditRefreshBtn = document.getElementById('ia-audit-refresh');
      const setMsg = (text, isErr) => {{
        if (!msgEl) return;
        msgEl.textContent = text || '';
        msgEl.style.color = isErr ? '#b91c1c' : '#0f3d2e';
      }};
      const setJobMsg = (text, isErr) => {{
        if (!jobMsgEl) return;
        jobMsgEl.textContent = text || '';
        jobMsgEl.style.color = isErr ? '#b91c1c' : '#0f3d2e';
      }};
      const setAuditMsg = (text, isErr) => {{
        if (!auditMsgEl) return;
        auditMsgEl.textContent = text || '';
        auditMsgEl.style.color = isErr ? '#b91c1c' : '#0f3d2e';
      }};
      const escapeHtml = (v) => String(v || '')
        .replaceAll('&','&amp;')
        .replaceAll('<','&lt;')
        .replaceAll('>','&gt;')
        .replaceAll('"','&quot;')
        .replaceAll("'", '&#039;');
      const loadFlags = async () => {{
        try {{
          const res = await fetch('/api/ia/feature-flags', {{ credentials: 'same-origin' }});
          const data = await res.json().catch(() => ({{}}));
          if (!res.ok || data.success === false) {{
            throw new Error(data.error || 'Sin permisos para ver feature flags.');
          }}
          const rows = Array.isArray(data.data) ? data.data : [];
          if (!rows.length) {{
            listEl.innerHTML = '<tr><td colspan="5" style="color:#64748b;">Sin reglas. Por defecto IA habilitada.</td></tr>';
            return;
          }}
          listEl.innerHTML = rows.map((row) => `
            <tr>
              <td>${{escapeHtml(row.feature_key)}}</td>
              <td>${{escapeHtml(row.module || '*')}}</td>
              <td>${{escapeHtml(row.role || '*')}}</td>
              <td>${{row.enabled ? 'Sí' : 'No'}}</td>
              <td>
                <div class="ia-ff-actions">
                  <button type="button" class="ia-ff-btn" data-del="${{row.id}}">Eliminar</button>
                </div>
              </td>
            </tr>
          `).join('');
          listEl.querySelectorAll('[data-del]').forEach((btn) => {{
            btn.addEventListener('click', async () => {{
              const id = Number(btn.getAttribute('data-del') || 0);
              if (!id) return;
              try {{
                const r = await fetch(`/api/ia/feature-flags/${{id}}/delete`, {{
                  method: 'POST',
                  headers: {{ 'Content-Type': 'application/json' }},
                  credentials: 'same-origin',
                }});
                const j = await r.json().catch(() => ({{}}));
                if (!r.ok || j.success === false) throw new Error(j.error || 'No se pudo eliminar regla.');
                setMsg('Regla eliminada.');
                await loadFlags();
              }} catch (e) {{
                setMsg(e.message || 'Error al eliminar regla.', true);
              }}
            }});
          }});
        }} catch (err) {{
          listEl.innerHTML = '<tr><td colspan="5" style="color:#b91c1c;">No se pudieron cargar reglas.</td></tr>';
          setMsg(err.message || 'No se pudieron cargar reglas.', true);
        }}
      }};
      const loadJobs = async () => {{
        if (!jobListEl) return;
        try {{
          const res = await fetch('/api/ia/jobs?limit=20', {{ credentials: 'same-origin' }});
          const data = await res.json().catch(() => ({{}}));
          if (!res.ok || data.success === false) {{
            throw new Error(data.error || 'No se pudieron cargar jobs.');
          }}
          const rows = Array.isArray(data.data) ? data.data : [];
          if (!rows.length) {{
            jobListEl.innerHTML = '<tr><td colspan="7" style="color:#64748b;">Sin jobs registrados.</td></tr>';
            return;
          }}
          jobListEl.innerHTML = rows.map((row) => `
            <tr>
              <td>${{row.id}}</td>
              <td>${{escapeHtml(row.module || '-')}}</td>
              <td>${{escapeHtml(row.status || 'pending')}}</td>
              <td>${{Number(row.progress || 0)}}%</td>
              <td>${{Number(row.attempts || 0)}}/${{Number(row.max_attempts || 1)}}</td>
              <td>${{escapeHtml(row.updated_at || '-')}}</td>
              <td>
                <div class="ia-ff-actions">
                  <button type="button" class="ia-ff-btn" data-retry="${{row.id}}">Retry</button>
                </div>
              </td>
            </tr>
          `).join('');
          jobListEl.querySelectorAll('[data-retry]').forEach((btn) => {{
            btn.addEventListener('click', async () => {{
              const id = Number(btn.getAttribute('data-retry') || 0);
              if (!id) return;
              try {{
                const r = await fetch(`/api/ia/jobs/${{id}}/retry`, {{
                  method: 'POST',
                  headers: {{ 'Content-Type': 'application/json' }},
                  credentials: 'same-origin',
                }});
                const j = await r.json().catch(() => ({{}}));
                if (!r.ok || j.success === false) throw new Error(j.error || 'No se pudo reintentar job.');
                setJobMsg(`Job #${{id}} reintentado.`);
                await loadJobs();
              }} catch (e) {{
                setJobMsg(e.message || 'Error al reintentar job.', true);
              }}
            }});
          }});
        }} catch (err) {{
          jobListEl.innerHTML = '<tr><td colspan="7" style="color:#b91c1c;">No se pudieron cargar jobs.</td></tr>';
          setJobMsg(err.message || 'No se pudieron cargar jobs.', true);
        }}
      }};
      const loadAuditSummary = async () => {{
        const days = Number(auditDaysEl && auditDaysEl.value ? auditDaysEl.value : 30);
        try {{
          const res = await fetch(`/api/ia/audit/summary?days=${{days}}`, {{ credentials: 'same-origin' }});
          const data = await res.json().catch(() => ({{}}));
          if (!res.ok || data.success === false) throw new Error(data.error || 'No se pudo cargar resumen de auditoría.');
          const d = data.data || {{}};
          if (auditOpsEl) auditOpsEl.value = String(d.operations_total ?? 0);
          if (auditErrEl) auditErrEl.value = `${{Number(d.error_rate_pct || 0)}}%`;
          if (auditTokensEl) auditTokensEl.value = String(d.tokens_total ?? 0);
          setAuditMsg(`Resumen actualizado desde ${{d.since || ''}}`);
        }} catch (err) {{
          if (auditOpsEl) auditOpsEl.value = '-';
          if (auditErrEl) auditErrEl.value = '-';
          if (auditTokensEl) auditTokensEl.value = '-';
          setAuditMsg(err.message || 'Error al cargar resumen de auditoría.', true);
        }}
      }};
      const loadAuditFeed = async () => {{
        if (!auditListEl) return;
        try {{
          const res = await fetch('/api/ia/audit/feed?limit=80', {{ credentials: 'same-origin' }});
          const data = await res.json().catch(() => ({{}}));
          if (!res.ok || data.success === false) throw new Error(data.error || 'No se pudo cargar bitácora IA.');
          const rows = Array.isArray(data.data) ? data.data : [];
          if (!rows.length) {{
            auditListEl.innerHTML = '<tr><td colspan="9" style="color:#64748b;">Sin eventos registrados.</td></tr>';
            return;
          }}
          auditListEl.innerHTML = rows.map((row) => `
            <tr>
              <td>${{escapeHtml(row.created_at || '-')}}</td>
              <td>${{escapeHtml(row.username || '-')}}</td>
              <td>${{escapeHtml(row.source || '-')}}</td>
              <td>${{escapeHtml(row.module || '-')}}</td>
              <td>${{escapeHtml(row.status || '-')}}</td>
              <td>${{escapeHtml(row.model || '-')}}</td>
              <td>${{Number(row.total_tokens || 0)}}</td>
              <td>${{Number(row.cost_estimated || 0).toFixed(6)}}</td>
              <td>${{escapeHtml(row.message || '-')}}</td>
            </tr>
          `).join('');
        }} catch (err) {{
          auditListEl.innerHTML = '<tr><td colspan="9" style="color:#b91c1c;">No se pudo cargar la bitácora IA.</td></tr>';
          setAuditMsg(err.message || 'Error al cargar bitácora IA.', true);
        }}
      }};
      saveBtn && saveBtn.addEventListener('click', async () => {{
        const feature_key = String(featureEl && featureEl.value ? featureEl.value : '').trim();
        const module = String(moduleEl && moduleEl.value ? moduleEl.value : '').trim();
        const role = String(roleEl && roleEl.value ? roleEl.value : '').trim();
        const enabled = String(enabledEl && enabledEl.value ? enabledEl.value : '1') === '1';
        if (!feature_key) {{
          setMsg('Feature key es obligatorio.', true);
          return;
        }}
        try {{
          const res = await fetch('/api/ia/feature-flags', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            credentials: 'same-origin',
            body: JSON.stringify({{ feature_key, module, role, enabled }}),
          }});
          const data = await res.json().catch(() => ({{}}));
          if (!res.ok || data.success === false) {{
            throw new Error(data.error || 'No se pudo guardar la regla.');
          }}
          setMsg('Regla guardada.');
          await loadFlags();
        }} catch (err) {{
          setMsg(err.message || 'No se pudo guardar la regla.', true);
        }}
      }});
      jobCreateBtn && jobCreateBtn.addEventListener('click', async () => {{
        const module = String(jobModuleEl && jobModuleEl.value ? jobModuleEl.value : '').trim();
        const prompt = String(jobPromptEl && jobPromptEl.value ? jobPromptEl.value : '').trim();
        if (!prompt) {{
          setJobMsg('Prompt requerido para crear job.', true);
          return;
        }}
        try {{
          const res = await fetch('/api/ia/jobs', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            credentials: 'same-origin',
            body: JSON.stringify({{ module, prompt, job_type: 'suggest_objective_text', feature_key: 'suggest_objective_text' }}),
          }});
          const data = await res.json().catch(() => ({{}}));
          if (!res.ok || data.success === false) {{
            throw new Error(data.error || 'No se pudo crear job.');
          }}
          setJobMsg(`Job creado #${{data?.data?.id || ''}}`);
          if (jobPromptEl) jobPromptEl.value = '';
          await loadJobs();
        }} catch (err) {{
          setJobMsg(err.message || 'No se pudo crear job.', true);
        }}
      }});
      jobRefreshBtn && jobRefreshBtn.addEventListener('click', loadJobs);
      auditRefreshBtn && auditRefreshBtn.addEventListener('click', async () => {{
        await loadAuditSummary();
        await loadAuditFeed();
      }});
      loadFlags();
      loadJobs();
      loadAuditSummary();
      loadAuditFeed();
      window.setInterval(loadJobs, 6000);
      window.setInterval(loadAuditSummary, 15000);
      window.setInterval(loadAuditFeed, 15000);
    }})();
  </script>
</section>
"""


@router.get("/ajustes/ia", response_class=HTMLResponse)
def ajustes_ia_get(request: Request):
    from fastapi_modulo.main import render_backend_page

    db = SessionLocal()
    try:
        IAConfig.__table__.create(bind=db.get_bind(), checkfirst=True)
        config = db.query(IAConfig).order_by(IAConfig.updated_at.desc()).first()
    finally:
        db.close()

    content = _ia_form_content(
        ai_provider=getattr(config, "ai_provider", ""),
        ai_api_key=getattr(config, "ai_api_key", ""),
        ai_base_url=getattr(config, "ai_base_url", ""),
        ai_model=getattr(config, "ai_model", ""),
        ai_timeout=getattr(config, "ai_timeout", 30),
        ai_temperature=getattr(config, "ai_temperature", 0.7),
        ai_top_p=getattr(config, "ai_top_p", 0.9),
        ai_num_predict=getattr(config, "ai_num_predict", 700),
    )
    return render_backend_page(
        request,
        title="Ajustes IA",
        description="Configuración del agente IA AVAN y parámetros de conexión.",
        content=content,
        hide_floating_actions=True,
        show_page_header=True,
    )


@router.post("/ajustes/ia", response_class=HTMLResponse)
async def ajustes_ia_post(request: Request):
    form = await request.form()
    ai_provider = str(form.get("ai_provider") or "").strip()
    ai_api_key = str(form.get("ai_api_key") or "").strip()
    ai_base_url = str(form.get("ai_base_url") or "").strip()
    ai_model = str(form.get("ai_model") or "").strip()
    ai_primary_provider = _normalize_provider_name(str(form.get("ai_primary_provider") or "").strip())
    ai_fallback_provider = _normalize_provider_name(str(form.get("ai_fallback_provider") or "").strip())
    ai_timeout = str(form.get("ai_timeout") or "30").strip()
    try:
        timeout_value = int(ai_timeout or "30")
    except Exception:
        timeout_value = 30
    if timeout_value < 1:
        timeout_value = 1
    if timeout_value > 120:
        timeout_value = 120
    try:
        temperature_value = float(form.get("ai_temperature") or "0.7")
        temperature_value = max(0.0, min(2.0, temperature_value))
    except Exception:
        temperature_value = 0.7
    try:
        top_p_value = float(form.get("ai_top_p") or "0.9")
        top_p_value = max(0.0, min(1.0, top_p_value))
    except Exception:
        top_p_value = 0.9
    try:
        num_predict_value = int(form.get("ai_num_predict") or "700")
        num_predict_value = max(100, min(4000, num_predict_value))
    except Exception:
        num_predict_value = 700

    provider_norm = _normalize_provider_name(ai_provider)
    if provider_norm == "hybrid":
        primary = ai_primary_provider if ai_primary_provider in {"ollama", "openai", "deepseek"} else "ollama"
        fallback = ai_fallback_provider if ai_fallback_provider in {"ollama", "openai", "deepseek"} else "openai"
        if fallback == primary:
            fallback = "deepseek" if primary != "deepseek" else "openai"
        ai_provider = f"{primary},{fallback}"
        if primary == "ollama":
            ai_base_url = _normalize_ollama_generate_url(ai_base_url)
    elif provider_norm == "ollama":
        ai_base_url = _normalize_ollama_generate_url(ai_base_url)

    db = SessionLocal()
    try:
        IAConfig.__table__.create(bind=db.get_bind(), checkfirst=True)
        prev = db.query(IAConfig).order_by(IAConfig.updated_at.desc()).first()
        if not ai_provider and prev:
            ai_provider = str(getattr(prev, "ai_provider", "") or "")
        if not ai_api_key and prev:
            ai_api_key = str(getattr(prev, "ai_api_key", "") or "")
        if not ai_base_url and prev:
            ai_base_url = str(getattr(prev, "ai_base_url", "") or "")
        if not ai_model and prev:
            ai_model = str(getattr(prev, "ai_model", "") or "")
        config = IAConfig(
            ai_provider=ai_provider,
            ai_api_key=ai_api_key,
            ai_base_url=ai_base_url,
            ai_model=ai_model,
            ai_timeout=timeout_value,
            ai_temperature=temperature_value,
            ai_top_p=top_p_value,
            ai_num_predict=num_predict_value,
        )
        db.add(config)
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/ajustes/ia", status_code=303)


@router.get("/api/ia/status", response_class=JSONResponse)
def ia_status_api(request: Request):
    db = SessionLocal()
    try:
        IAConfig.__table__.create(bind=db.get_bind(), checkfirst=True)
        config = db.query(IAConfig).order_by(IAConfig.updated_at.desc()).first()
    finally:
        db.close()

    provider_raw = str(getattr(config, "ai_provider", "") or "").strip()
    provider_chain = _parse_provider_chain(provider_raw)
    primary_provider = provider_chain[0] if provider_chain else (_normalize_provider_name(provider_raw) or "")
    provider = "hybrid" if len(provider_chain) >= 2 else primary_provider
    fallback_provider = provider_chain[1] if len(provider_chain) >= 2 else ""
    api_key = str(getattr(config, "ai_api_key", "") or "").strip()
    base_url = str(getattr(config, "ai_base_url", "") or "").strip()
    model = str(getattr(config, "ai_model", "") or "").strip()
    timeout = int(getattr(config, "ai_timeout", 30) or 30) if config else 30
    health_detail = ""
    primary_connected = False
    if primary_provider == "ollama":
        primary_connected, health_detail = _check_ollama_connected(base_url, timeout)
        base_url = _normalize_ollama_generate_url(base_url)
    else:
        primary_connected = bool(primary_provider and api_key)
    fallback_ready = bool(fallback_provider and api_key)
    connected = bool(primary_connected or fallback_ready)
    if provider == "hybrid":
        extra = f"primary={primary_provider} ({'ok' if primary_connected else 'sin conexión'})"
        if fallback_provider:
            extra += f", fallback={fallback_provider} ({'listo' if fallback_ready else 'sin key'})"
        health_detail = f"{extra}{' | ' + health_detail if health_detail else ''}"
    return {
        "success": True,
        "connected": connected,
        "provider": provider,
        "model": model,
        "base_url": base_url,
        "health_detail": health_detail,
        "agent_name": "AVAN",
        "agent_avatar": "/templates/imagenes/lobo.jpg",
    }
