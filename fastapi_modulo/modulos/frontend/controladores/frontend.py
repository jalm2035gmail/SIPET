import json
import os
import re
import uuid as _uuid
import shutil
from datetime import datetime

from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse

from fastapi_modulo.modulos.frontend.modelos.frontend_store import (
    delete_page as store_delete_page,
    get_page as store_get_page,
    get_page_by_slug as store_get_page_by_slug,
    list_pages as store_list_pages,
    list_versions as store_list_versions,
    publish_page as store_publish_page,
    restore_version as store_restore_version,
    upsert_page as store_upsert_page,
)

router = APIRouter()

_STORE_PATH       = os.path.join("fastapi_modulo", "modulos", "frontend", "pages_store.json")
_BUILDER_TEMPLATE = os.path.join("fastapi_modulo", "modulos", "frontend", "vistas", "frontend.html")
_TASAS_PATH       = os.path.join("fastapi_modulo", "modulos", "frontend", "tasas_store.json")
_CONTACT_PATH     = os.path.join("fastapi_modulo", "modulos", "frontend", "contact_store.json")
_VERSIONS_PATH    = os.path.join("fastapi_modulo", "modulos", "frontend", "versions_store.json")
_GALLERY_DIR      = os.path.join("static", "gallery")
_GALLERY_MAX_MB   = 5
_MAX_VERSIONS     = 5
_BRAND_PATH       = os.path.join("fastapi_modulo", "modulos", "frontend", "brand_store.json")
_RESERVED_backend_SLUGS = {
    "",
    "descripcion",
    "funcionalidades",
    "login",
    "404",
    "passkey",
}

# Simple in-memory page render cache: {slug: rendered_html}
_page_cache: dict = {}
_CORE_BOUND = False


def clear_all_page_cache() -> None:
    """Flush the full page render cache (e.g. after brand color changes)."""
    _page_cache.clear()


def _bind_core_symbols() -> None:
    global _CORE_BOUND
    if _CORE_BOUND:
        return
    from fastapi_modulo import main as core

    names = [
        "AUTH_COOKIE_NAME",
        "Colores",
        "SessionLocal",
        "_get_login_identity_context",
        "_get_user_backend_roles",
        "_read_session_cookie",
        "normalize_role_name",
        "templates",
    ]
    for name in names:
        globals()[name] = getattr(core, name)
    _CORE_BOUND = True

_TASAS_DEFAULT = [
    {"id": "ahorro_vista",  "label": "Ahorro a la vista",   "rate": "3.50",  "color": "#3b82f6", "unit": "% anual"},
    {"id": "dpf_6m",        "label": "DPF 6 meses",         "rate": "6.25",  "color": "#10b981", "unit": "% anual"},
    {"id": "credito_per",   "label": "Crédito personal",    "rate": "14.00", "color": "#f59e0b", "unit": "% anual"},
    {"id": "credito_hip",   "label": "Crédito hipotecario", "rate": "10.00", "color": "#8b5cf6", "unit": "% anual"},
]


# ── Data helpers ──────────────────────────────────────────────────────────────

def _load_pages() -> list:
    return store_list_pages()


def _is_public_frontend_page_path(path: str) -> bool:
    if not path.startswith("/backend/"):
        return False
    slug = (path[len("/backend/"):] or "").strip().strip("/")
    if not slug or "/" in slug:
        return False
    if slug in {"descripcion", "funcionalidades", "login", "404", "passkey"}:
        return False
    try:
        page = store_get_page_by_slug(slug, published_only=True)
        return bool(page)
    except Exception:
        return False


# ── Builder UI ────────────────────────────────────────────────────────────────

@router.get("/frontend/builder", response_class=HTMLResponse)
def frontend_builder(request: Request):
    try:
        with open(_BUILDER_TEMPLATE, "r", encoding="utf-8") as fh:
            return HTMLResponse(fh.read())
    except OSError:
        return HTMLResponse("<h1>Template no encontrado</h1>", status_code=500)


@router.get("/api/backend/me")
def api_backend_me(request: Request):
    _bind_core_symbols()
    session_token = request.cookies.get(AUTH_COOKIE_NAME, "")
    session_data = _read_session_cookie(session_token) if session_token else None
    if not session_data:
        return {"authenticated": False, "is_superadmin": False, "backend_roles": [], "role": "", "username": ""}
    role = normalize_role_name(session_data.get("role") or "")
    username = (session_data.get("username") or "").strip()
    superadmin = role == "superadministrador"
    if not superadmin:
        request.state.user_name = username
        request.state.user_role = role
        backend_roles = _get_user_backend_roles(request)
    else:
        backend_roles = ["editor", "designer"]
    can_use_bar = superadmin or bool(backend_roles)
    bar_color = "#0f172a"
    try:
        _cdb = SessionLocal()
        _col = _cdb.query(Colores).filter(Colores.key == "sidebar-bottom").first()
        if _col and _col.value:
            bar_color = _col.value.strip()
        _cdb.close()
    except Exception:
        pass
    return {
        "authenticated": can_use_bar,
        "is_superadmin": superadmin,
        "backend_roles": backend_roles,
        "role": role,
        "username": username,
        "builder_url": "/frontend/builder",
        "bar_color": bar_color,
    }


@router.get("/backend", response_class=HTMLResponse)
def backend(request: Request):
    _bind_core_symbols()
    login_identity = _get_login_identity_context()
    return templates.TemplateResponse(
        "frontend/web_blank.html",
        {
            "request": request,
            "title": "SIPET",
            "app_favicon_url": login_identity.get("login_favicon_url"),
            "company_logo_url": login_identity.get("login_logo_url"),
            "login_company_short_name": login_identity.get("login_company_short_name"),
            "menu_position": login_identity.get("menu_position"),
        },
    )


@router.get("/backend/descripcion", response_class=HTMLResponse)
def backend_descripcion(request: Request):
    _bind_core_symbols()
    login_identity = _get_login_identity_context()
    return templates.TemplateResponse(
        "frontend/web.html",
        {
            "request": request,
            "title": "SIPET",
            "app_favicon_url": login_identity.get("login_favicon_url"),
            "company_logo_url": login_identity.get("login_logo_url"),
            "menu_position": login_identity.get("menu_position"),
        },
    )


@router.get("/backend/funcionalidades", response_class=HTMLResponse)
def backend_funcionalidades(request: Request):
    _bind_core_symbols()
    login_identity = _get_login_identity_context()
    return templates.TemplateResponse(
        "frontend/modulo_funcionalidades.html",
        {
            "request": request,
            "title": "Funcionalidades | SIPET",
            "app_favicon_url": login_identity.get("login_favicon_url"),
            "company_logo_url": login_identity.get("login_logo_url"),
            "menu_position": login_identity.get("menu_position"),
        },
    )


# ── API: pages CRUD ───────────────────────────────────────────────────────────

@router.get("/api/frontend/pages")
def api_pages_list():
    return {"success": True, "data": store_list_pages()}


@router.get("/api/frontend/pages/{page_id}")
def api_page_get(page_id: str):
    page = store_get_page(page_id)
    if not page:
        return JSONResponse({"success": False, "error": "No encontrado"}, status_code=404)
    return {"success": True, "data": page}


@router.post("/api/frontend/pages")
async def api_pages_save(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"success": False, "error": "JSON inválido"}, status_code=400)

    action = body.get("action", "upsert")

    if action == "delete":
        pid = str(body.get("id", ""))
        return {"success": True, "data": store_delete_page(pid)}

    # upsert
    pid = str(body.get("id") or _uuid.uuid4())
    pages = store_list_pages()

    slug_raw = str(body.get("slug") or body.get("title") or "pagina").strip().lower()
    slug = "".join(c if c.isalnum() or c == "-" else "-" for c in slug_raw).strip("-") or "pagina"
    if slug in _RESERVED_backend_SLUGS:
        return JSONResponse(
            {"success": False, "error": f'La ruta "/backend/{slug}" está reservada. Usa otro slug.'},
            status_code=400,
        )
    duplicate = next((p for p in pages if p.get("slug") == slug and p.get("id") != pid), None)
    if duplicate:
        return JSONResponse(
            {"success": False, "error": f'Ya existe otra página con la ruta "/backend/{slug}".'},
            status_code=400,
        )

    page = {
        "id":       pid,
        "title":    str(body.get("title") or "Sin título").strip(),
        "slug":     slug,
        "status":   str(body.get("status") or "draft"),
        "is_home":  bool(body.get("is_home", False)),
        "gjs_html": str(body.get("gjs_html") or ""),
        "gjs_css":  str(body.get("gjs_css")  or ""),
        "blocks":   body.get("blocks") if isinstance(body.get("blocks"), list) else [],
        "meta":     body.get("meta") if isinstance(body.get("meta"), dict) else {},
    }

    saved = store_upsert_page(page)
    # Invalidate render cache on any save
    _page_cache.pop(page["slug"], None)
    _page_cache.pop("backend:" + page["slug"], None)
    return {"success": True, "data": saved["pages"], "page": saved["page"]}


# ── Public preview ────────────────────────────────────────────────────────────

@router.get("/p/{slug}", response_class=HTMLResponse)
def public_page(slug: str):
    if slug in _page_cache:
        return HTMLResponse(_page_cache[slug])
    page = store_get_page_by_slug(slug, published_only=True)
    if not page:
        return HTMLResponse("<h1 style='font-family:sans-serif;padding:40px'>Página no encontrada</h1>", status_code=404)
    rendered = _render_page_html(page)
    _page_cache[slug] = rendered.body.decode("utf-8")
    return rendered


@router.get("/backend/{slug}", response_class=HTMLResponse)
def public_page_backend(slug: str):
    """Public pages served at /backend/<slug> — mirrors /p/<slug>."""
    cache_key = "backend:" + slug
    if cache_key in _page_cache:
        return HTMLResponse(_page_cache[cache_key])
    page = store_get_page_by_slug(slug, published_only=True)
    if not page:
        return HTMLResponse("<h1 style='font-family:sans-serif;padding:40px'>Página no encontrada</h1>", status_code=404)
    rendered = _render_page_html(page)
    _page_cache[cache_key] = rendered.body.decode("utf-8")
    return rendered


@router.get("/p-preview/{slug}", response_class=HTMLResponse)
def preview_page(slug: str):
    """Draft preview — accessible from the builder regardless of publish status."""
    page = store_get_page_by_slug(slug, published_only=False)
    if not page:
        return HTMLResponse("<h1 style='font-family:sans-serif;padding:40px'>Página no encontrada</h1>", status_code=404)
    return _render_page_html(page)


@router.post("/api/frontend/pages/{page_id}/publish")
def api_page_publish(page_id: str):
    """Set page status to 'published' and invalidate render cache."""
    page = store_publish_page(page_id)
    if not page:
        return JSONResponse({"success": False, "error": "No encontrado"}, status_code=404)
    _page_cache.pop(page.get("slug", ""), None)
    _page_cache.pop("backend:" + page.get("slug", ""), None)
    return {"success": True, "page": page}


@router.get("/api/frontend/versions/{page_id}")
def api_versions_list(page_id: str):
    """Return version snapshots for a page (newest first, max 5)."""
    return {"success": True, "data": store_list_versions(page_id)}


@router.post("/api/frontend/versions/{page_id}/restore/{version_idx}")
def api_version_restore(page_id: str, version_idx: int):
    """Restore a version snapshot back into the active page."""
    versions = store_list_versions(page_id)
    if version_idx < 0 or version_idx >= len(versions):
        return JSONResponse({"success": False, "error": "Versión no encontrada"}, status_code=404)
    page = store_restore_version(page_id, version_idx)
    if not page:
        return JSONResponse({"success": False, "error": "Página no encontrada"}, status_code=404)
    _page_cache.pop(page.get("slug", ""), None)
    _page_cache.pop("backend:" + page.get("slug", ""), None)
    return {"success": True, "page": page}


@router.get("/api/frontend/forms")
def api_list_forms():
    """List active form definitions so the builder can populate the sipet-form trait select."""
    try:
        import fastapi_modulo.main as _core  # lazy import to avoid circular deps
        from fastapi_modulo.modulos.plantillas.modelos.plantillas_db_models import FormDefinition

        db_gen = _core.get_db()
        db = next(db_gen)
        try:
            forms = (
                db.query(FormDefinition)
                .filter(FormDefinition.is_active == True)  # noqa: E712
                .order_by(FormDefinition.name)
                .all()
            )
            return {
                "success": True,
                "data": [{"id": f.id, "name": f.name, "slug": f.slug} for f in forms],
            }
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass
    except Exception as exc:
        return JSONResponse({"success": False, "data": [], "error": str(exc)}, status_code=500)


_FORM_WIDGET_SCRIPT = """
<script>
(function(){
  'use strict';
  function _e(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
  function _field(f,slug){
    var id='sfw-'+slug+'-'+f.name;
    var b='width:100%;padding:10px 14px;border:1px solid #d1d5db;border-radius:8px;font-size:14px;outline:none;';
    var fc='onFocus="this.style.borderColor=\'#3b82f6\'" onBlur="this.style.borderColor=\'#d1d5db\'";';
    if(f.type==='divider') return '<hr style="border:none;border-top:1px solid #e5e7eb;margin:4px 0;">';
    if(f.type==='header')  return '<h3 style="font-size:1.1rem;font-weight:700;color:#111827;">'+_e(f.label||'')+'</h3>';
    if(f.type==='paragraph') return '<p style="font-size:14px;color:#64748b;line-height:1.6;">'+_e(f.label||'')+'</p>';
    var w='<div style="display:flex;flex-direction:column;gap:5px;">';
    if(f.type!=='checkbox'){
      w+='<label for="'+_e(id)+'" style="font-size:13px;font-weight:600;color:#374151;">'+_e(f.label||f.name)+(f.required?' <span style="color:#ef4444">*</span>':'')+'</label>';
    }
    if(f.type==='textarea'){
      w+='<textarea id="'+_e(id)+'" name="'+_e(f.name)+'" rows="4" placeholder="'+_e(f.placeholder||'')+'" style="'+b+'resize:vertical;" '+fc+(f.required?' required':'')+'></textarea>';
    } else if(f.type==='select'){
      w+='<select id="'+_e(id)+'" name="'+_e(f.name)+'" style="'+b+'" '+fc+(f.required?' required':'')+'>'
        +'<option value="">-- Seleccionar --</option>';
      (f.options||[]).forEach(function(o){var v=typeof o==='object'?(o.value||o):o;var l=typeof o==='object'?(o.label||o.value||o):o;w+='<option value="'+_e(v)+'">'+_e(l)+'</option>';});
      w+='</select>';
    } else if(f.type==='radio'){
      w+='<div style="display:flex;flex-direction:column;gap:8px;">';
      (f.options||[]).forEach(function(o){var v=typeof o==='object'?(o.value||o):o;var l=typeof o==='object'?(o.label||o.value||o):o;w+='<label style="display:flex;align-items:center;gap:8px;font-size:14px;cursor:pointer;"><input type="radio" name="'+_e(f.name)+'" value="'+_e(v)+'"'+(f.required?' required':'')+'>'+_e(l)+'</label>';});
      w+='</div>';
    } else if(f.type==='checkboxes'){
      w+='<div style="display:flex;flex-direction:column;gap:8px;">';
      (f.options||[]).forEach(function(o){var v=typeof o==='object'?(o.value||o):o;var l=typeof o==='object'?(o.label||o.value||o):o;w+='<label style="display:flex;align-items:center;gap:8px;font-size:14px;cursor:pointer;"><input type="checkbox" name="'+_e(f.name)+'" value="'+_e(v)+'">'+_e(l)+'</label>';});
      w+='</div>';
    } else if(f.type==='checkbox'){
      w+='<label style="display:flex;align-items:center;gap:8px;font-size:14px;cursor:pointer;"><input type="checkbox" id="'+_e(id)+'" name="'+_e(f.name)+'" value="1"'+(f.required?' required':'')+'>'+_e(f.label||f.name)+'</label>';
    } else if(f.type==='date'){
      w+='<input type="date" id="'+_e(id)+'" name="'+_e(f.name)+'" style="'+b+'" '+fc+(f.required?' required':'')+'>'
    } else if(f.type==='time'){
      w+='<input type="time" id="'+_e(id)+'" name="'+_e(f.name)+'" style="'+b+'" '+fc+(f.required?' required':'')+'>'
    } else {
      var t=(f.type==='email'||f.type==='url'||f.type==='number'||f.type==='integer'||f.type==='decimal')? f.type.replace('integer','number').replace('decimal','number') : 'text';
      w+='<input type="'+t+'" id="'+_e(id)+'" name="'+_e(f.name)+'" placeholder="'+_e(f.placeholder||'')+'" style="'+b+'" '+fc+(f.required?' required':'')+'>'
    }
    if(f.helpText) w+='<span style="font-size:11px;color:#64748b;">'+_e(f.helpText)+'</span>';
    w+='</div>';
    return w;
  }
  function _render(data,el){
    var cfg=data.config||{};
    var pc=cfg.primary_color||'#3b82f6';
    var lbl=cfg.submit_label||'Enviar';
    var ok=cfg.success_message||'¡Gracias! Tu respuesta fue enviada.';
    var h='<form data-slug="'+_e(data.slug)+'" novalidate style="display:flex;flex-direction:column;gap:18px;">';
    if(data.name) h+='<h2 style="font-size:1.4rem;font-weight:800;color:#111827;">'+_e(data.name)+'</h2>';
    if(data.description) h+='<p style="font-size:14px;color:#64748b;margin-top:-10px;line-height:1.6;">'+_e(data.description)+'</p>';
    (data.fields||[]).forEach(function(f){h+=_field(f,data.slug);});
    h+='<div style="display:flex;align-items:center;gap:12px;"><button type="submit" style="padding:12px 28px;background:'+_e(pc)+';color:#fff;border:none;border-radius:8px;font-size:14px;font-weight:700;cursor:pointer;">'+_e(lbl)+'</button><span class="_sfw_msg" style="display:none;font-size:13px;"></span></div>';
    h+='</form>';
    el.innerHTML=h;
    el.querySelector('form').addEventListener('submit',function(ev){
      ev.preventDefault();
      var btn=this.querySelector('button[type=submit]'),msg=this.querySelector('._sfw_msg'),fd={};
      new FormData(this).forEach(function(v,k){fd[k]=v;});
      if(btn)btn.disabled=true;
      fetch('/api/forms/'+encodeURIComponent(data.slug)+'/submit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(fd),credentials:'include'})
        .then(function(r){return r.json();})
        .then(function(j){
          if(j.success){
            el.innerHTML='<div style="padding:24px;background:#ecfdf5;border-radius:10px;color:#065f46;font-weight:600;text-align:center;font-size:15px;">&#10003; '+_e(ok)+'</div>';
          } else {
            if(msg){msg.style.display='inline';msg.style.color='#b91c1c';msg.textContent=j.error||'Error al enviar';}
            if(btn)btn.disabled=false;
          }
        }).catch(function(){
          if(msg){msg.style.display='inline';msg.style.color='#b91c1c';msg.textContent='Error de conexión';}
          if(btn)btn.disabled=false;
        });
    });
  }
  function init(){
    document.querySelectorAll('.sipet-form-widget[data-slug]').forEach(function(el){
      var slug=el.dataset.slug;
      if(!slug){el.innerHTML='<p style="color:#94a3b8;padding:16px;font-style:italic;">Formulario sin configurar</p>';return;}
      el.innerHTML='<p style="color:#94a3b8;font-size:13px;padding:16px;text-align:center;">&#8987; Cargando formulario…</p>';
      fetch('/api/forms/'+encodeURIComponent(slug),{credentials:'include'})
        .then(function(r){return r.json();})
        .then(function(j){
          if(!j.success||!j.data){el.innerHTML='<p style="color:#ef4444;padding:16px;font-size:13px;">Formulario &ldquo;'+_e(slug)+'&rdquo; no encontrado</p>';return;}
          _render(j.data,el);
        }).catch(function(){el.innerHTML='<p style="color:#ef4444;padding:16px;font-size:13px;">Error al cargar formulario</p>';});
    });
  }
  if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',init);}else{init();}
})();
</script>"""


def _brand_css_vars() -> str:
    """Return a <style>:root{...}</style> block with brand color CSS variables."""
    try:
        from fastapi_modulo.main import get_colores_context
        data = get_colores_context()
        if not data:
            return ""
        rules = "".join(f"--{k.replace(' ','-')}:{v};" for k, v in data.items() if isinstance(v, str))
        return f"<style>:root{{{rules}}}</style>" if rules else ""
    except Exception:
        return ""


def _frontend_menu_position() -> str:
    try:
        import fastapi_modulo.main as _core
        data = _core._load_login_identity()
        value = str(data.get("menu_position") or "arriba").strip().lower()
        return value if value in {"arriba", "abajo"} else "arriba"
    except Exception:
        return "arriba"


def _mobile_bottom_menu_html() -> str:
    return """
<style>
.sipet-mobile-bottom-nav{
  position:fixed;bottom:0;left:0;right:0;display:flex;z-index:2000;
  background:#fff;border-top:1px solid #e2e8f0;box-shadow:0 -4px 16px rgba(0,0,0,.08)
}
body.sipet-menu-bottom{padding-bottom:76px}
.sipet-mobile-bottom-nav a{
  flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;
  gap:3px;padding:10px 4px;text-decoration:none;color:#94a3b8;font-family:system-ui,sans-serif
}
.sipet-mobile-bottom-nav a.is-active{color:#3b82f6}
.sipet-mobile-bottom-nav__icon{font-size:1.3rem;line-height:1}
.sipet-mobile-bottom-nav__label{font-size:.65rem;font-weight:600;line-height:1.1}
@media (min-width: 901px){
  .sipet-mobile-bottom-nav{
    left:50%;right:auto;bottom:20px;transform:translateX(-50%);
    width:min(680px,calc(100vw - 32px));border:1px solid #e2e8f0;border-radius:18px;
    box-shadow:0 20px 50px rgba(15,23,42,.18)
  }
  body.sipet-menu-bottom{padding-bottom:96px}
  .sipet-mobile-bottom-nav a{padding:12px 8px}
}
</style>
<nav class="sipet-mobile-bottom-nav" aria-label="Menú móvil inferior">
  <a href="/backend/inicio"><span class="sipet-mobile-bottom-nav__icon">🏠</span><span class="sipet-mobile-bottom-nav__label">Inicio</span></a>
  <a href="/backend/funcionalidades"><span class="sipet-mobile-bottom-nav__icon">💳</span><span class="sipet-mobile-bottom-nav__label">Servicios</span></a>
  <a href="/backend/descripcion"><span class="sipet-mobile-bottom-nav__icon">🔍</span><span class="sipet-mobile-bottom-nav__label">Buscar</span></a>
  <a href="/backend/login"><span class="sipet-mobile-bottom-nav__icon">👤</span><span class="sipet-mobile-bottom-nav__label">Perfil</span></a>
</nav>
<script>
(function(){
  var path=(window.location.pathname||'').replace(/\\/+$/,'')||'/';
  document.body.classList.add('sipet-menu-bottom');
  document.querySelectorAll('.sipet-mobile-bottom-nav a[href]').forEach(function(link){
    var href=(link.getAttribute('href')||'').replace(/\\/+$/,'')||'/';
    if(href===path || (href!=='/' && path.indexOf(href + '/')===0)){ link.classList.add('is-active'); }
  });
})();
</script>
"""


def _resolve_frontend_logo_url() -> str:
    brand = _load_brand()
    brand_logo = str(brand.get("logo_url") or "").strip()
    if brand_logo:
        return brand_logo
    return _resolve_identidad_logo_url()


def _inject_frontend_logo(html: str) -> str:
    logo_url = _resolve_frontend_logo_url()
    if not logo_url or 'data-sipet-logo' not in (html or ''):
        return html
    logo_markup = (
        f'<img src="{_esc(logo_url)}" '
        'style="height:38px;width:auto;object-fit:contain;display:block;" '
        'alt="Logo" data-sipet-logo="1">'
    )
    pattern = re.compile(r'(<[^>]*data-sipet-logo="1"[^>]*>)(.*?)(</[^>]+>)', re.IGNORECASE | re.DOTALL)
    return pattern.sub(lambda m: f"{m.group(1)}{logo_markup}{m.group(3)}", html)


def _render_page_html(page: dict) -> HTMLResponse:
    title = _esc(page.get("title", ""))
    meta  = page.get("meta") or {}
    meta_title = _esc(meta.get("title") or page.get("title") or "")
    meta_desc  = _esc(meta.get("description") or "")
    og_image   = _esc(meta.get("og_image") or "")
    gjs_html = page.get("gjs_html") or ""
    gjs_css  = page.get("gjs_css")  or ""
    if gjs_html:
        body_content = _inject_frontend_logo(gjs_html)
        extra_style  = f"<style>{gjs_css}</style>" if gjs_css else ""
    else:
        body_content = _inject_frontend_logo(_render_blocks(page.get("blocks", [])))
        extra_style  = ""
    og_image_tag = f'<meta property="og:image" content="{og_image}">' if og_image else ""
    # Inject form-widget script only when needed
    has_forms = 'sipet-form-widget' in (gjs_html or body_content)
    form_script = _FORM_WIDGET_SCRIPT if has_forms else ""
    brand_vars = _brand_css_vars()
    menu_position = _frontend_menu_position()
    bottom_menu = _mobile_bottom_menu_html() if menu_position == "abajo" else ""
    return HTMLResponse(f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{meta_title or title}</title>
  {f'<meta name="description" content="{meta_desc}">' if meta_desc else ''}
  {og_image_tag}
  <meta property="og:title" content="{meta_title or title}">
  <meta property="og:type" content="backendsite">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap" rel="stylesheet">
  {brand_vars}
  <style>*{{box-sizing:border-box;margin:0;padding:0}}body{{font-family:system-ui,sans-serif;color:#1e293b}}</style>
  {extra_style}
</head>
<body>{body_content}{bottom_menu}{form_script}</body>
</html>""")


# ── Block renderer (server-side, for preview route) ───────────────────────────

def _esc(s: str) -> str:
    return str(s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _render_blocks(blocks: list) -> str:
    html = ""
    for b in blocks:
        btype = b.get("type", "")
        p = b.get("props", {})
        if btype == "hero":
            align = p.get("align", "center")
            html += f"""<section style="background:{_esc(p.get('bg','#1e293b'))};color:{_esc(p.get('color','#ffffff'))};padding:80px 24px;text-align:{align};">
  <h1 style="font-size:2.5rem;font-weight:800;margin-bottom:16px;">{_esc(p.get('title',''))}</h1>
  <p style="font-size:1.2rem;opacity:.8;margin-bottom:32px;">{_esc(p.get('subtitle',''))}</p>
  {f'<a href="{_esc(p.get("btn_url","#"))}" style="display:inline-block;padding:14px 32px;background:{_esc(p.get("btn_bg","#3b82f6"))};color:#fff;border-radius:8px;text-decoration:none;font-weight:700;">{_esc(p.get("btn_label",""))}</a>' if p.get('btn_label') else ''}
</section>"""
        elif btype == "text":
            html += f"""<section style="max-width:{_esc(p.get('max_width','760px'))};margin:0 auto;padding:{_esc(p.get('padding','48px 24px'))};">
  <div style="font-size:{_esc(p.get('font_size','1rem'))};line-height:1.7;color:{_esc(p.get('color','#1e293b'))};">{p.get('content','')}</div>
</section>"""
        elif btype == "image":
            html += f"""<section style="padding:{_esc(p.get('padding','32px 24px'))};text-align:{_esc(p.get('align','center'))};">
  <img src="{_esc(p.get('src',''))}" alt="{_esc(p.get('alt',''))}" style="max-width:{_esc(p.get('max_width','100%'))};border-radius:{_esc(p.get('radius','0px'))};">
  {f'<p style="margin-top:10px;color:#64748b;font-size:.9rem;">{_esc(p.get("caption",""))}</p>' if p.get('caption') else ''}
</section>"""
        elif btype == "columns2":
            cols = p.get("columns", [{}, {}])
            c1, c2 = (cols + [{}, {}])[:2]
            html += f"""<section style="padding:{_esc(p.get('padding','48px 24px'))};max-width:1100px;margin:0 auto;">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:32px;">
    <div>{c1.get('content','')}</div>
    <div>{c2.get('content','')}</div>
  </div>
</section>"""
        elif btype == "columns3":
            cols = p.get("columns", [{}, {}, {}])
            c1, c2, c3 = (cols + [{}, {}, {}])[:3]
            html += f"""<section style="padding:{_esc(p.get('padding','48px 24px'))};max-width:1100px;margin:0 auto;">
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:24px;">
    <div>{c1.get('content','')}</div>
    <div>{c2.get('content','')}</div>
    <div>{c3.get('content','')}</div>
  </div>
</section>"""
        elif btype == "cta":
            html += f"""<section style="background:{_esc(p.get('bg','#0f172a'))};color:{_esc(p.get('color','#fff'))};padding:60px 24px;text-align:center;">
  <h2 style="font-size:2rem;font-weight:700;margin-bottom:12px;">{_esc(p.get('title',''))}</h2>
  <p style="opacity:.8;margin-bottom:28px;">{_esc(p.get('subtitle',''))}</p>
  {f'<a href="{_esc(p.get("btn_url","#"))}" style="display:inline-block;padding:14px 36px;background:{_esc(p.get("btn_bg","#3b82f6"))};color:#fff;border-radius:8px;text-decoration:none;font-weight:700;">{_esc(p.get("btn_label",""))}</a>' if p.get('btn_label') else ''}
</section>"""
        elif btype == "cards":
            cards = p.get("cards", [])
            cards_html = "".join(
                f'<div style="background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:24px;">'
                f'<h3 style="font-size:1.1rem;font-weight:700;margin-bottom:8px;">{_esc(c.get("title",""))}</h3>'
                f'<p style="color:#64748b;font-size:.9rem;">{_esc(c.get("body",""))}</p></div>'
                for c in cards
            )
            html += f"""<section style="padding:{_esc(p.get('padding','48px 24px'))};max-width:1100px;margin:0 auto;">
  {f'<h2 style="text-align:center;font-size:1.8rem;font-weight:700;margin-bottom:32px;">{_esc(p.get("title",""))}</h2>' if p.get('title') else ''}
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:20px;">{cards_html}</div>
</section>"""
        elif btype == "divider":
            html += f'<hr style="border:none;border-top:{_esc(p.get("thickness","1px"))} solid {_esc(p.get("color","#e2e8f0"))};margin:{_esc(p.get("margin","0"))};">'
        elif btype == "spacer":
            html += f'<div style="height:{_esc(p.get("height","48px"))};"></div>'
        elif btype == "html":
            html += p.get("content", "")
    return html


# ── API: Tasas de interés ─────────────────────────────────────────────────────

def _load_tasas() -> list:
    try:
        with open(_TASAS_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, list) else _TASAS_DEFAULT
    except (OSError, json.JSONDecodeError):
        return list(_TASAS_DEFAULT)


def _save_tasas(tasas: list) -> None:
    with open(_TASAS_PATH, "w", encoding="utf-8") as fh:
        json.dump(tasas, fh, ensure_ascii=False, indent=2)


@router.get("/api/frontend/tasas")
def api_tasas_list():
    return {"success": True, "data": _load_tasas()}


@router.post("/api/frontend/tasas")
async def api_tasas_save(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"success": False, "error": "JSON inválido"}, status_code=400)
    tasas = body if isinstance(body, list) else []
    _save_tasas(tasas)
    return {"success": True, "data": tasas}


# ── API: Formulario de contacto ───────────────────────────────────────────────

def _load_contacts() -> list:
    try:
        with open(_CONTACT_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
            return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _save_contacts(contacts: list) -> None:
    os.makedirs(os.path.dirname(_CONTACT_PATH), exist_ok=True)
    with open(_CONTACT_PATH, "w", encoding="utf-8") as fh:
        json.dump(contacts, fh, ensure_ascii=False, indent=2)


@router.post("/api/frontend/contact")
async def api_contact_submit(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"success": False, "error": "JSON inválido"}, status_code=400)
    name    = str(body.get("name", "")).strip()
    email   = str(body.get("email", "")).strip()
    message = str(body.get("message", "")).strip()
    if not name or not email or not message:
        return JSONResponse({"success": False, "error": "Campos requeridos: name, email, message"}, status_code=422)
    contacts = _load_contacts()
    entry = {
        "id":         str(_uuid.uuid4()),
        "name":       name,
        "email":      email,
        "message":    message,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "read":       False,
    }
    contacts.insert(0, entry)
    _save_contacts(contacts)
    return {"success": True, "message": "Mensaje recibido, gracias."}


@router.get("/api/frontend/contact")
def api_contact_list():
    return {"success": True, "data": _load_contacts()}


@router.post("/api/frontend/contact/{contact_id}/read")
def api_contact_mark_read(contact_id: str):
    contacts = _load_contacts()
    for c in contacts:
        if c.get("id") == contact_id:
            c["read"] = True
            break
    _save_contacts(contacts)
    return {"success": True}


# ── API: Galería de imágenes ──────────────────────────────────────────────────

_ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".backendp", ".svg"}


def _gallery_items() -> list:
    os.makedirs(_GALLERY_DIR, exist_ok=True)
    items = []
    for fname in sorted(os.listdir(_GALLERY_DIR)):
        ext = os.path.splitext(fname)[1].lower()
        if ext in _ALLOWED_IMAGE_EXTS:
            items.append({
                "filename": fname,
                "url": f"/static/gallery/{fname}",
            })
    return items


def _load_brand() -> dict:
    try:
        with open(_BRAND_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_brand(data: dict) -> None:
    os.makedirs(os.path.dirname(_BRAND_PATH), exist_ok=True)
    with open(_BRAND_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def _resolve_identidad_logo_url() -> str:
    """Retorna la URL del logo configurado en /empresa/identidad institucional.
    Prioridad: 1) logo subido en Identidad institucional, 2) logo en Personalización.
    """
    import glob as _glob
    _CONFIG = (os.environ.get("IDENTIDAD_LOGIN_CONFIG_PATH") or "fastapi_modulo/identidad_login.json").strip()
    _IMG_DIR = "fastapi_modulo/templates/imagenes"
    _DEFAULT_LOGO = "icon.png"
    # Priority 1: identidad institucional
    try:
        with open(_CONFIG, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        logo_filename = str(data.get("logo_filename") or "").strip()
        if logo_filename and logo_filename != _DEFAULT_LOGO:
            path = os.path.join(_IMG_DIR, logo_filename)
            v = int(os.path.getmtime(path)) if os.path.exists(path) else 0
            return f"/templates/imagenes/{logo_filename}?v={v}"
    except (OSError, json.JSONDecodeError):
        pass
    # Priority 2: personalizacion/uploads/logo_empresa.*
    _UPLOADS = os.path.join("fastapi_modulo", "modulos", "personalizacion", "uploads")
    candidates = sorted(
        _glob.glob(os.path.join(_UPLOADS, "logo_empresa.*")),
        key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0,
        reverse=True,
    )
    if candidates:
        fname = os.path.MAINname(candidates[0])
        v = int(os.path.getmtime(candidates[0])) if os.path.exists(candidates[0]) else 0
        return f"/personalizar/uploads/{fname}?v={v}"
    return ""


@router.get("/api/frontend/brand")
def api_brand_get():
    brand = _load_brand()
    # Always expose the identidad institucional logo so the builder can auto-inject it
    brand["identidad_logo_url"] = _resolve_identidad_logo_url()
    return {"success": True, "data": brand}


@router.post("/api/frontend/brand")
async def api_brand_save(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"success": False, "error": "JSON inválido"}, status_code=400)
    brand = _load_brand()
    brand.update({k: v for k, v in body.items() if isinstance(v, str)})
    _save_brand(brand)
    clear_all_page_cache()
    return {"success": True, "data": brand}


@router.get("/api/frontend/gallery")
def api_gallery_list():
    return {"success": True, "data": _gallery_items()}


@router.post("/api/frontend/gallery/upload")
async def api_gallery_upload(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_IMAGE_EXTS:
        return JSONResponse(
            {"success": False, "error": f"Tipo no permitido. Usa: {', '.join(_ALLOWED_IMAGE_EXTS)}"},
            status_code=415
        )
    data = await file.read()
    if len(data) > _GALLERY_MAX_MB * 1024 * 1024:
        return JSONResponse(
            {"success": False, "error": f"Imagen demasiado grande (máx {_GALLERY_MAX_MB} MB)"},
            status_code=413
        )
    # Optimizar: redimensionar a máx 1200×1200 y convertir a backendP (excepto SVG)
    try:
        from fastapi_modulo.image_utils import optimize_image
        data, ext = optimize_image(data, ext, profile="asset")
    except Exception:
        pass  # Si falla, guarda el original
    os.makedirs(_GALLERY_DIR, exist_ok=True)
    safe_name = f"{_uuid.uuid4().hex}{ext}"
    dest = os.path.join(_GALLERY_DIR, safe_name)
    with open(dest, "wb") as fh:
        fh.write(data)
    url = f"/static/gallery/{safe_name}"
    return {"success": True, "filename": safe_name, "url": url}


@router.delete("/api/frontend/gallery/{filename}")
def api_gallery_delete(filename: str):
    # sanitize: no path traversal
    safe = os.path.MAINname(filename)
    path = os.path.join(_GALLERY_DIR, safe)
    if os.path.isfile(path):
        os.remove(path)
        return {"success": True}
    return JSONResponse({"success": False, "error": "Archivo no encontrado"}, status_code=404)
