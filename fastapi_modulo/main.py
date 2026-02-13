
import json
import base64
import hashlib
import hmac
from datetime import datetime
from html import escape
import os
import secrets
from textwrap import dedent

from typing import Dict, List, Optional
from fastapi import FastAPI, Request, Body, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
import httpx
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import create_engine, Column, String, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

HIDDEN_SYSTEM_USERS = {"0konomiyaki"}
IDENTIDAD_LOGIN_CONFIG_PATH = "fastapi_modulo/identidad_login.json"
IDENTIDAD_LOGIN_IMAGE_DIR = "fastapi_modulo/templates/imagenes"
DEFAULT_LOGIN_IDENTITY = {
    "logo_filename": "icon.png",
    "desktop_bg_filename": "fondo.jpg",
    "mobile_bg_filename": "movil.jpg",
    "company_short_name": "AVAN",
    "login_message": "Incrementando el nivel de eficiencia",
}
PLANTILLAS_STORE_PATH = "fastapi_modulo/plantillas_store.json"
AUTH_COOKIE_NAME = "auth_session"
AUTH_COOKIE_SECRET = os.environ.get("AUTH_COOKIE_SECRET", "sipet-dev-auth-secret")


def get_current_role(request: Request) -> str:
    role = getattr(request.state, "user_role", None)
    if role is None:
        role = request.cookies.get("user_role") or os.environ.get("DEFAULT_USER_ROLE") or ""
    return role.strip().lower()


def is_superadmin(request: Request) -> bool:
    return get_current_role(request) == "superadministrador"


def require_superadmin(request: Request) -> None:
    if not is_superadmin(request):
        raise HTTPException(status_code=403, detail="Acceso restringido a superadministrador")


def _ensure_login_identity_paths() -> None:
    os.makedirs(IDENTIDAD_LOGIN_IMAGE_DIR, exist_ok=True)


def _load_login_identity() -> Dict[str, str]:
    data = DEFAULT_LOGIN_IDENTITY.copy()
    if os.path.exists(IDENTIDAD_LOGIN_CONFIG_PATH):
        try:
            with open(IDENTIDAD_LOGIN_CONFIG_PATH, "r", encoding="utf-8") as fh:
                loaded = json.load(fh)
            if isinstance(loaded, dict):
                data.update({k: v for k, v in loaded.items() if isinstance(v, str)})
        except (OSError, json.JSONDecodeError):
            pass
    return data


def _save_login_identity(data: Dict[str, str]) -> None:
    with open(IDENTIDAD_LOGIN_CONFIG_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def _get_upload_ext(upload: UploadFile) -> str:
    filename = (upload.filename or "").lower()
    ext = os.path.splitext(filename)[1]
    if ext in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
        return ext
    content_type = (upload.content_type or "").lower()
    if "svg" in content_type:
        return ".svg"
    if "webp" in content_type:
        return ".webp"
    if "jpeg" in content_type or "jpg" in content_type:
        return ".jpg"
    return ".png"


def _remove_login_image_if_custom(filename: Optional[str]) -> None:
    if not filename or filename in {
        DEFAULT_LOGIN_IDENTITY["logo_filename"],
        DEFAULT_LOGIN_IDENTITY["desktop_bg_filename"],
        DEFAULT_LOGIN_IDENTITY["mobile_bg_filename"],
    }:
        return
    path = os.path.join(IDENTIDAD_LOGIN_IMAGE_DIR, filename)
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


async def _store_login_image(upload: UploadFile, prefix: str) -> Optional[str]:
    if not upload or not upload.filename:
        return None
    data = await upload.read()
    if not data:
        return None
    _ensure_login_identity_paths()
    ext = _get_upload_ext(upload)
    new_filename = f"{prefix}_{secrets.token_hex(6)}{ext}"
    image_path = os.path.join(IDENTIDAD_LOGIN_IMAGE_DIR, new_filename)
    with open(image_path, "wb") as fh:
        fh.write(data)
    return new_filename


def _build_login_asset_url(filename: Optional[str], default_filename: str) -> str:
    selected = filename or default_filename
    selected_path = os.path.join(IDENTIDAD_LOGIN_IMAGE_DIR, selected)
    if not os.path.exists(selected_path):
        selected = default_filename
        selected_path = os.path.join(IDENTIDAD_LOGIN_IMAGE_DIR, selected)
    version = int(os.path.getmtime(selected_path)) if os.path.exists(selected_path) else 0
    return f"/templates/imagenes/{selected}?v={version}"


def _get_login_identity_context() -> Dict[str, str]:
    data = _load_login_identity()
    return {
        "login_logo_url": _build_login_asset_url(
            data.get("logo_filename"),
            DEFAULT_LOGIN_IDENTITY["logo_filename"],
        ),
        "login_bg_desktop_url": _build_login_asset_url(
            data.get("desktop_bg_filename"),
            DEFAULT_LOGIN_IDENTITY["desktop_bg_filename"],
        ),
        "login_bg_mobile_url": _build_login_asset_url(
            data.get("mobile_bg_filename"),
            DEFAULT_LOGIN_IDENTITY["mobile_bg_filename"],
        ),
        "login_company_short_name": data.get("company_short_name") or DEFAULT_LOGIN_IDENTITY["company_short_name"],
        "login_message": data.get("login_message") or DEFAULT_LOGIN_IDENTITY["login_message"],
    }


def _load_plantillas_store() -> List[Dict[str, str]]:
    if not os.path.exists(PLANTILLAS_STORE_PATH):
        return []
    try:
        with open(PLANTILLAS_STORE_PATH, "r", encoding="utf-8") as fh:
            loaded = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(loaded, list):
        return []
    templates = []
    for item in loaded:
        if not isinstance(item, dict):
            continue
        templates.append(
            {
                "id": str(item.get("id") or "").strip(),
                "nombre": str(item.get("nombre") or "").strip(),
                "html": str(item.get("html") or ""),
                "css": str(item.get("css") or ""),
                "created_at": str(item.get("created_at") or ""),
                "updated_at": str(item.get("updated_at") or ""),
            }
        )
    return [tpl for tpl in templates if tpl["id"] and tpl["nombre"]]


def _save_plantillas_store(templates: List[Dict[str, str]]) -> None:
    os.makedirs(os.path.dirname(PLANTILLAS_STORE_PATH), exist_ok=True)
    with open(PLANTILLAS_STORE_PATH, "w", encoding="utf-8") as fh:
        json.dump(templates, fh, ensure_ascii=False, indent=2)


def build_view_buttons_html(view_buttons: Optional[List[Dict]]) -> str:
    if not view_buttons:
        return ""
    pieces = []
    for button in view_buttons:
        label = button.get("label", "").strip()
        if not label:
            continue
        icon = button.get("icon")
        view = button.get("view")
        url = button.get("url")
        classes = "view-pill"
        if button.get("active"):
            classes += " active"
        attrs = []
        if view:
            attrs.append(f'data-view="{view}"')
        if url:
            attrs.append(f'data-url="{url}"')
        attr_str = f' {" ".join(attrs)}' if attrs else ""
        icon_html = ""
        if icon:
            icon_html = f'<img src="{icon}" alt="{label} icon">'
        pieces.append(f'<button class="{classes}" type="button"{attr_str}>{icon_html}<span>{label}</span></button>')
    return "".join(pieces)


def backend_screen(
    request: Request,
    title: str,
    subtitle: Optional[str] = None,
    description: Optional[str] = None,
    content: str = "",
    view_buttons: Optional[List[Dict]] = None,
    view_buttons_html: str = "",
    floating_buttons: Optional[List[Dict]] = None,
    hide_floating_actions: bool = False,
    show_page_header: bool = True,
    page_title: Optional[str] = None,
    page_description: Optional[str] = None,
):
    """
    Helper para renderizar una pantalla backend con panel flotante y botones de vistas.
    - view_buttons: lista de dicts {label, view?, url, icon}
    - floating_buttons: lista de dicts {label, onclick}
    """
    rendered_view_buttons = view_buttons_html or build_view_buttons_html(view_buttons)
    can_manage_personalization = is_superadmin(request)
    context = {
        "request": request,
        "title": title,
        "subtitle": subtitle,
        "page_title": page_title or title,
        "page_description": page_description or description,
        "content": content,
        "view_buttons_html": rendered_view_buttons,
        "floating_buttons": floating_buttons,
        "hide_floating_actions": hide_floating_actions,
        "show_page_header": show_page_header,
        "colores": get_colores_context(),
        "can_manage_personalization": can_manage_personalization,
    }
    return templates.TemplateResponse("base.html", context)

# Configuración SQLite
DATABASE_URL = "sqlite:///fastapi_modulo/colores.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Colores(Base):
    __tablename__ = "colores"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(String)

# --- NUEVO: Modelos para roles y usuarios ---
class Rol(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True)
    descripcion = Column(String)

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    usuario = Column(String, unique=True, index=True)
    correo = Column(String, unique=True, index=True)
    celular = Column(String)
    contrasena = Column(String)
    departamento = Column(String)
    puesto = Column(String)
    jefe = Column(String)
    coach = Column(String)
    rol_id = Column(Integer)
    imagen = Column(String)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Módulo de Planificación Estratégica y POA", docs_url="/docs", redoc_url="/redoc")
templates = Jinja2Templates(directory="fastapi_modulo/templates")
app.mount("/templates", StaticFiles(directory="fastapi_modulo/templates"), name="templates")

@app.get("/health")
def healthcheck():
    return {"status": "ok"}


def _not_found_context(request: Request, title: str = "Pagina no encontrada") -> Dict[str, str]:
    login_identity = _get_login_identity_context()
    colores = get_colores_context()
    sidebar_top_color = (colores.get("sidebar-top") or "#1f2a3d").strip()
    is_dark_bg = _is_dark_color(sidebar_top_color)
    return {
        "request": request,
        "title": title,
        "company_logo_url": login_identity.get("login_logo_url"),
        "sidebar_top_color": sidebar_top_color,
        "not_found_text_color": "#ffffff" if is_dark_bg else "#2b2b2b",
        "not_found_highlight_color": "#ffffff" if is_dark_bg else "#1f1f1f",
    }


def _is_dark_color(value: str) -> bool:
    color = (value or "").strip().lower()
    if color.startswith("#"):
        hex_color = color[1:]
        if len(hex_color) == 3:
            hex_color = "".join(ch * 2 for ch in hex_color)
        if len(hex_color) == 6:
            try:
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                luminance = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255
                return luminance < 0.5
            except ValueError:
                return True
    return True


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    path = request.url.path
    if path.startswith("/api/"):
        return JSONResponse({"success": False, "error": exc.detail}, status_code=exc.status_code)
    if exc.status_code in {403, 404}:
        return templates.TemplateResponse(
            "not_found.html",
            _not_found_context(request),
            status_code=404,
        )
    return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)


@app.middleware("http")
async def enforce_backend_login(request: Request, call_next):
    path = request.url.path
    public_paths = {
        "/web",
        "/web/404",
        "/web/login",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
    }
    if (
        request.method == "OPTIONS"
        or path in public_paths
        or path.startswith("/templates/")
        or path.startswith("/docs/")
        or path.startswith("/redoc/")
    ):
        return await call_next(request)

    session_token = request.cookies.get(AUTH_COOKIE_NAME, "")
    session_data = _read_session_cookie(session_token)
    if not session_data:
        if path.startswith("/api/") or path.startswith("/guardar-colores"):
            return JSONResponse({"success": False, "error": "No autenticado"}, status_code=401)
        return templates.TemplateResponse(
            "not_found.html",
            _not_found_context(request),
            status_code=404,
        )

    request.state.user_name = session_data["username"]
    request.state.user_role = session_data["role"]
    return await call_next(request)


def hash_password(password: str) -> str:
    iterations = 120_000
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return f"pbkdf2_sha256${iterations}${salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algo, iterations, salt, digest_hex = stored_hash.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


def is_hidden_user(request: Request, username: Optional[str]) -> bool:
    if is_superadmin(request):
        return False
    return (username or "").strip().lower() in {u.lower() for u in HIDDEN_SYSTEM_USERS}


def _build_session_cookie(username: str, role: str) -> str:
    payload_json = json.dumps(
        {"u": username.strip(), "r": role.strip().lower()},
        separators=(",", ":"),
        ensure_ascii=True,
    )
    payload = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("ascii").rstrip("=")
    signature = hmac.new(
        AUTH_COOKIE_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{signature}"


def _read_session_cookie(token: str) -> Optional[Dict[str, str]]:
    if not token or "." not in token:
        return None
    payload, signature = token.rsplit(".", 1)
    expected_signature = hmac.new(
        AUTH_COOKIE_SECRET.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return None
    try:
        padding = "=" * (-len(payload) % 4)
        payload_json = base64.urlsafe_b64decode((payload + padding).encode("ascii")).decode("utf-8")
        data = json.loads(payload_json)
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    username = str(data.get("u", "")).strip()
    role = str(data.get("r", "")).strip().lower()
    if not username or not role:
        return None
    return {"username": username, "role": role}

@app.post("/guardar-colores")
async def guardar_colores(request: Request, data: dict = Body(...)):
    try:
        db = SessionLocal()
        for key, value in data.items():
            color = db.query(Colores).filter(Colores.key == key).first()
            if color:
                color.value = value
            else:
                color = Colores(key=key, value=value)
                db.add(color)
        db.commit()
        db.close()
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)

@app.get("/guardar-colores")
async def obtener_colores():
    try:
        db = SessionLocal()
        colores = db.query(Colores).all()
        db.close()
        data = {c.key: c.value for c in colores}
        return JSONResponse({"success": True, "data": data})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
@app.get("/web", response_class=HTMLResponse)
def web(request: Request):
    return templates.TemplateResponse(
        "frontend/web.html",
        {
            "request": request,
            "title": "Frontend Web",
            "content": "<h2>Bienvenido a la vista web del sistema</h2>",
        },
    )


@app.get("/web/login", response_class=HTMLResponse)
def web_login(request: Request):
    login_identity = _get_login_identity_context()
    return templates.TemplateResponse(
        "web_login.html",
        {
            "request": request,
            "title": "Login",
            "login_error": "",
            **login_identity,
        },
    )


@app.get("/web/404", response_class=HTMLResponse)
def web_not_found(request: Request):
    return templates.TemplateResponse(
        "not_found.html",
        _not_found_context(request),
    )


@app.post("/web/login")
def web_login_submit(
    request: Request,
    usuario: str = Form(""),
    contrasena: str = Form(""),
):
    login_identity = _get_login_identity_context()
    username = usuario.strip()
    password = contrasena or ""
    if not username or not password:
        return templates.TemplateResponse(
            "web_login.html",
            {
                "request": request,
                "title": "Login",
                "login_error": "Datos incorrectos, vuelva a intentarlo",
                **login_identity,
            },
            status_code=401,
        )

    db = SessionLocal()
    try:
        user = db.query(Usuario).filter(Usuario.usuario == username).first()
        if not user or not verify_password(password, user.contrasena or ""):
            return templates.TemplateResponse(
                "web_login.html",
                {
                    "request": request,
                    "title": "Login",
                    "login_error": "Datos incorrectos, vuelva a intentarlo",
                    **login_identity,
                },
                status_code=401,
            )

        role_name = "usuario"
        if user.rol_id:
            role = db.query(Rol).filter(Rol.id == user.rol_id).first()
            if role and role.nombre:
                role_name = role.nombre.strip().lower()
    finally:
        db.close()

    response = RedirectResponse(url="/inicio", status_code=303)
    response.set_cookie(
        AUTH_COOKIE_NAME,
        _build_session_cookie(username, role_name),
        httponly=True,
        samesite="lax",
    )
    response.set_cookie("user_role", role_name, httponly=True, samesite="lax")
    response.set_cookie("user_name", username, httponly=True, samesite="lax")
    return response


def get_colores_context() -> Dict[str, str]:
    db = SessionLocal()
    colores = {c.key: c.value for c in db.query(Colores).all()}
    db.close()
    return colores


def render_backend_page(
    request: Request,
    title: str,
    description: str = "",
    content: str = "",
    subtitle: Optional[str] = None,
    hide_floating_actions: bool = True,
    view_buttons: Optional[List[Dict]] = None,
    view_buttons_html: str = "",
    floating_actions_html: str = "",
    floating_actions_screen: str = "personalization",
    show_page_header: bool = True,
) -> HTMLResponse:
    rendered_view_buttons = view_buttons_html or build_view_buttons_html(view_buttons)
    can_manage_personalization = is_superadmin(request)
    context = {
        "request": request,
        "title": title,
        "content": content,
        "subtitle": subtitle,
        "page_title": title,
        "page_description": description,
        "hide_floating_actions": hide_floating_actions,
        "floating_actions_html": floating_actions_html,
        "floating_actions_screen": floating_actions_screen,
        "view_buttons_html": rendered_view_buttons,
        "show_page_header": show_page_header,
        "can_manage_personalization": can_manage_personalization,
    }
    context.update({"colores": get_colores_context()})
    return templates.TemplateResponse("base.html", context)



# Almacenamiento simple en archivo para el contenido editable de Avance
AVANCE_CONTENT_FILE = "fastapi_modulo/avance_content.txt"
def get_avance_content():
    if os.path.exists(AVANCE_CONTENT_FILE):
        with open(AVANCE_CONTENT_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return "<p>Sin contenido personalizado aún.</p><p>Inicio.<br>bienvenido al tablero</p>"

def set_avance_content(new_content: str):
    with open(AVANCE_CONTENT_FILE, "w", encoding="utf-8") as f:
        f.write(new_content)

@app.get("/avan", response_class=HTMLResponse)
def avan(request: Request, edit: Optional[bool] = False):
    # Solo mostrar contenido, sin edición
    meta = {"title": "Avance", "subtitle": "Progreso y métricas clave", "description": "Resumen del estado del sistema"}
    content = get_avance_content()
    return backend_screen(
        request,
        title=meta["title"],
        subtitle=meta["subtitle"],
        description=meta["description"],
        content=content,
        floating_buttons=None,
        hide_floating_actions=True,
    )




PERSONALIZACION_HTML = dedent("""
    <section class="personalization-panel" aria-labelledby="personalizacion-title">
        <div>
            <h2 id="personalizacion-title">Personalizar pantalla</h2>
            <p>Define los colores principales que se aplicarán en todo el sitio para mantener la identidad institucional.</p>
        </div>
        <div class="color-group">
            <h3>Navbar</h3>
            <div class="color-grid">
                <article class="color-option">
                    <label for="navbar-bg">Fondo</label>
                    <input type="color" id="navbar-bg" name="navbar-bg" value="#ffffff">
                    <div class="color-preview" id="navbar-bg-preview" style="background:#ffffff;"></div>
                </article>
                <article class="color-option">
                    <label for="navbar-text">Texto</label>
                    <input type="color" id="navbar-text" name="navbar-text" value="#0f172a">
                    <div class="color-preview" id="navbar-text-preview" style="background:#0f172a;"></div>
                </article>
            </div>
        </div>
        <div class="color-group">
            <h3>Sidebar</h3>
            <div class="color-grid">
                <article class="color-option">
                    <label for="sidebar-top">Color superior</label>
                    <input type="color" id="sidebar-top" name="sidebar-top" value="#1f2a3d">
                    <div class="color-preview" id="sidebar-top-preview" style="background:#1f2a3d;"></div>
                </article>
                <article class="color-option">
                    <label for="sidebar-bottom">Color inferior</label>
                    <input type="color" id="sidebar-bottom" name="sidebar-bottom" value="#0f172a">
                    <div class="color-preview" id="sidebar-bottom-preview" style="background:#0f172a;"></div>
                </article>
                <article class="color-option">
                    <label for="sidebar-text">Texto</label>
                    <input type="color" id="sidebar-text" name="sidebar-text" value="#ffffff">
                    <div class="color-preview" id="sidebar-text-preview" style="background:#ffffff;"></div>
                </article>
                <article class="color-option">
                    <label for="sidebar-icon">Iconos</label>
                    <input type="color" id="sidebar-icon" name="sidebar-icon" value="#f5f7fb">
                    <div class="color-preview" id="sidebar-icon-preview" style="background:#f5f7fb;"></div>
                </article>
                <article class="color-option">
                    <label for="sidebar-hover">Hover</label>
                    <input type="color" id="sidebar-hover" name="sidebar-hover" value="#2a3a52">
                    <div class="color-preview" id="sidebar-hover-preview" style="background:#2a3a52;"></div>
                </article>
            </div>
        </div>
        <div class="color-field-note">
            <p><strong>Color del campo:</strong> aquí se definirá el color de fondo que se aplicará a los campos donde el usuario ingresará información.</p>
        </div>
    </section>
""")

FODA_HTML = dedent("""
    <section class="foda-page" id="foda-builder">
        <article class="foda-input-card">
            <h2>Matriz FODA</h2>
            <p>Registra factores y clasifícalos como fortalezas, debilidades, oportunidades o amenazas.</p>
            <div class="foda-input-grid">
                <div class="form-field">
                    <label for="foda-description">Descripción</label>
                    <textarea id="foda-description" placeholder="Describe el factor"></textarea>
                </div>
                <div class="form-field">
                    <label for="foda-category">Categoría</label>
                    <select id="foda-category">
                        <option value="strengths">Fortalezas</option>
                        <option value="weaknesses">Debilidades</option>
                        <option value="opportunities">Oportunidades</option>
                        <option value="threats">Amenazas</option>
                    </select>
                </div>
                <div class="form-field">
                    <label for="foda-impact">Impacto</label>
                    <select id="foda-impact">
                        <option value="high">Alto</option>
                        <option value="medium">Medio</option>
                        <option value="low">Bajo</option>
                    </select>
                </div>
            </div>
            <div class="foda-input-actions">
                <button type="button" id="foda-add">Agregar factor</button>
            </div>
        </article>
        <section class="foda-matrix">
            <article class="foda-quadrant foda-strengths">
                <header>
                    <h3>Fortalezas</h3>
                    <span id="foda-count-strengths">0</span>
                </header>
                <ul id="foda-list-strengths"></ul>
            </article>
            <article class="foda-quadrant foda-weaknesses">
                <header>
                    <h3>Debilidades</h3>
                    <span id="foda-count-weaknesses">0</span>
                </header>
                <ul id="foda-list-weaknesses"></ul>
            </article>
            <article class="foda-quadrant foda-opportunities">
                <header>
                    <h3>Oportunidades</h3>
                    <span id="foda-count-opportunities">0</span>
                </header>
                <ul id="foda-list-opportunities"></ul>
            </article>
            <article class="foda-quadrant foda-threats">
                <header>
                    <h3>Amenazas</h3>
                    <span id="foda-count-threats">0</span>
                </header>
                <ul id="foda-list-threats"></ul>
            </article>
        </section>
    </section>
""")

PESTEL_HTML = dedent("""
    <section class="pestel-page" id="pestel-builder">
        <article class="pestel-input-card">
            <h2>Análisis PESTEL</h2>
            <p>Registra factores externos por dimensión: Política, Económica, Social, Tecnológica, Ecológica y Legal.</p>
            <div class="pestel-input-grid">
                <div class="form-field">
                    <label for="pestel-description">Factor</label>
                    <textarea id="pestel-description" placeholder="Describe el factor PESTEL"></textarea>
                </div>
                <div class="form-field">
                    <label for="pestel-factor">Dimensión</label>
                    <select id="pestel-factor">
                        <option value="political">Política</option>
                        <option value="economic">Económica</option>
                        <option value="social">Social</option>
                        <option value="technological">Tecnológica</option>
                        <option value="ecological">Ecológica</option>
                        <option value="legal">Legal</option>
                    </select>
                </div>
                <div class="form-field">
                    <label for="pestel-impact">Impacto</label>
                    <select id="pestel-impact">
                        <option value="high">Alto</option>
                        <option value="medium">Medio</option>
                        <option value="low">Bajo</option>
                    </select>
                </div>
            </div>
            <div class="pestel-input-actions">
                <button type="button" id="pestel-add">Agregar factor</button>
            </div>
        </article>
        <section class="pestel-board">
            <article class="pestel-column">
                <header><h3>Política</h3><span id="pestel-count-political">0</span></header>
                <ul id="pestel-list-political"></ul>
            </article>
            <article class="pestel-column">
                <header><h3>Económica</h3><span id="pestel-count-economic">0</span></header>
                <ul id="pestel-list-economic"></ul>
            </article>
            <article class="pestel-column">
                <header><h3>Social</h3><span id="pestel-count-social">0</span></header>
                <ul id="pestel-list-social"></ul>
            </article>
            <article class="pestel-column">
                <header><h3>Tecnológica</h3><span id="pestel-count-technological">0</span></header>
                <ul id="pestel-list-technological"></ul>
            </article>
            <article class="pestel-column">
                <header><h3>Ecológica</h3><span id="pestel-count-ecological">0</span></header>
                <ul id="pestel-list-ecological"></ul>
            </article>
            <article class="pestel-column">
                <header><h3>Legal</h3><span id="pestel-count-legal">0</span></header>
                <ul id="pestel-list-legal"></ul>
            </article>
        </section>
    </section>
""")

PORTER_HTML = dedent("""
    <section class="porter-page" id="porter-builder">
        <article class="porter-input-card">
            <h2>5 Fuerzas de Porter</h2>
            <p>Analiza la intensidad competitiva del entorno y su impacto en la estrategia.</p>
            <div class="porter-input-grid">
                <div class="form-field">
                    <label for="porter-description">Factor</label>
                    <textarea id="porter-description" placeholder="Describe el factor de la fuerza"></textarea>
                </div>
                <div class="form-field">
                    <label for="porter-force">Fuerza</label>
                    <select id="porter-force">
                        <option value="competitors">Rivalidad entre competidores</option>
                        <option value="entrants">Amenaza de nuevos entrantes</option>
                        <option value="suppliers">Poder de negociación de proveedores</option>
                        <option value="buyers">Poder de negociación de compradores</option>
                        <option value="substitutes">Amenaza de productos sustitutos</option>
                    </select>
                </div>
                <div class="form-field">
                    <label for="porter-impact">Impacto</label>
                    <select id="porter-impact">
                        <option value="high">Alto</option>
                        <option value="medium">Medio</option>
                        <option value="low">Bajo</option>
                    </select>
                </div>
            </div>
            <div class="porter-input-actions">
                <button type="button" id="porter-add">Agregar factor</button>
            </div>
        </article>
        <section class="porter-board">
            <article class="porter-column">
                <header><h3>Competidores</h3><span id="porter-count-competitors">0</span></header>
                <ul id="porter-list-competitors"></ul>
            </article>
            <article class="porter-column">
                <header><h3>Nuevos entrantes</h3><span id="porter-count-entrants">0</span></header>
                <ul id="porter-list-entrants"></ul>
            </article>
            <article class="porter-column">
                <header><h3>Proveedores</h3><span id="porter-count-suppliers">0</span></header>
                <ul id="porter-list-suppliers"></ul>
            </article>
            <article class="porter-column">
                <header><h3>Compradores</h3><span id="porter-count-buyers">0</span></header>
                <ul id="porter-list-buyers"></ul>
            </article>
            <article class="porter-column">
                <header><h3>Sustitutos</h3><span id="porter-count-substitutes">0</span></header>
                <ul id="porter-list-substitutes"></ul>
            </article>
        </section>
    </section>
""")

PERCEPCION_CLIENTE_HTML = dedent("""
    <section class="percepcion-page" id="percepcion-builder">
        <article class="percepcion-input-card">
            <h2>Percepción del cliente</h2>
            <p>Registra percepciones y clasifícalas para orientar mejoras del servicio.</p>
            <div class="percepcion-input-grid">
                <div class="form-field">
                    <label for="percepcion-description">Comentario</label>
                    <textarea id="percepcion-description" placeholder="Describe la percepción detectada"></textarea>
                </div>
                <div class="form-field">
                    <label for="percepcion-category">Categoría</label>
                    <select id="percepcion-category">
                        <option value="positive">Percepción positiva</option>
                        <option value="neutral">Percepción neutral</option>
                        <option value="negative">Percepción negativa</option>
                    </select>
                </div>
                <div class="form-field">
                    <label for="percepcion-priority">Prioridad</label>
                    <select id="percepcion-priority">
                        <option value="high">Alta</option>
                        <option value="medium">Media</option>
                        <option value="low">Baja</option>
                    </select>
                </div>
            </div>
            <div class="percepcion-input-actions">
                <button type="button" id="percepcion-add">Agregar percepción</button>
            </div>
        </article>
        <section class="percepcion-board">
            <article class="percepcion-column">
                <header><h3>Positivas</h3><span id="percepcion-count-positive">0</span></header>
                <ul id="percepcion-list-positive"></ul>
            </article>
            <article class="percepcion-column">
                <header><h3>Neutrales</h3><span id="percepcion-count-neutral">0</span></header>
                <ul id="percepcion-list-neutral"></ul>
            </article>
            <article class="percepcion-column">
                <header><h3>Negativas</h3><span id="percepcion-count-negative">0</span></header>
                <ul id="percepcion-list-negative"></ul>
            </article>
        </section>
    </section>
""")

PLAN_ESTRATEGICO_HTML = dedent("""
    <section class="foda-page">
        <article class="foda-input-card">
            <h2>Plan estratégico</h2>
            <p>En esta vista se concentra la gestión del plan estratégico institucional.</p>
            <p>Incluye definición de objetivos, líneas estratégicas y seguimiento general del plan.</p>
        </article>
    </section>
""")

POA_HTML = dedent("""
    <section class="foda-page">
        <article class="foda-input-card">
            <h2>POA</h2>
            <p>En esta vista se concentra la programación operativa anual vinculada al plan estratégico.</p>
            <p>Aquí se gestionarán actividades, responsables, plazos y presupuesto por periodo.</p>
        </article>
    </section>
""")

KPI_HTML = dedent("""
    <section class="foda-page">
        <article class="foda-input-card">
            <h2>KPIs</h2>
            <p>Panel para administrar indicadores clave de desempeño por objetivo y periodo.</p>
            <div class="foda-matrix">
                <article class="foda-quadrant">
                    <header><h3>Indicadores activos</h3><span>0</span></header>
                    <ul><li class="foda-item"><div><strong>Sin indicadores cargados</strong><br><small>Define KPIs por objetivo estratégico.</small></div></li></ul>
                </article>
                <article class="foda-quadrant">
                    <header><h3>Alertas</h3><span>0</span></header>
                    <ul><li class="foda-item"><div><strong>Sin alertas</strong><br><small>Se mostrarán desvíos y umbrales fuera de rango.</small></div></li></ul>
                </article>
            </div>
        </article>
    </section>
""")

REPORTES_HTML = dedent("""
    <section class="foda-page">
        <article class="foda-input-card">
            <h2>Reportes</h2>
            <p>Consolida reportes de avance, desempeño y seguimiento para exportación.</p>
            <div class="foda-matrix">
                <article class="foda-quadrant">
                    <header><h3>Reportes disponibles</h3><span>3</span></header>
                    <ul>
                        <li class="foda-item"><div><strong>Reporte ejecutivo</strong><br><small>Resumen de estado estratégico.</small></div></li>
                        <li class="foda-item"><div><strong>Reporte operativo</strong><br><small>Actividades, avances y cumplimiento.</small></div></li>
                        <li class="foda-item"><div><strong>Reporte KPI</strong><br><small>Indicadores, metas y variaciones.</small></div></li>
                    </ul>
                </article>
                <article class="foda-quadrant">
                    <header><h3>Exportaciones</h3><span>PDF / Excel</span></header>
                    <ul>
                        <li class="foda-item"><div><strong>Formato PDF</strong><br><small>Para distribución institucional.</small></div></li>
                        <li class="foda-item"><div><strong>Formato Excel</strong><br><small>Para análisis detallado.</small></div></li>
                    </ul>
                </article>
            </div>
        </article>
    </section>
""")


def render_personalizacion_page(request: Request) -> HTMLResponse:
    return render_backend_page(
        request,
        title="Personalizar",
        description="Agrega tu imagen corporativa",
        content=PERSONALIZACION_HTML,
        hide_floating_actions=False,
        floating_actions_screen="personalization",
    )


@app.get("/personalizar-pantalla", response_class=HTMLResponse)
def personalizar_pantalla(request: Request):
    require_superadmin(request)
    return backend_screen(
        request,
        title="Personalizar",
        subtitle="Colores institucionales",
        description="Agrega tu imagen corporativa",
        content=PERSONALIZACION_HTML,
        view_buttons=[
            {"label": "Formulario", "view": "form", "icon": "/templates/icon/formulario.svg"},
            {"label": "Lista", "view": "list", "icon": "/templates/icon/list.svg"},
            {"label": "Colores", "view": "colores", "icon": "/templates/icon/personalizacion.svg", "active": True},
        ],
        hide_floating_actions=False,
    )


@app.get("/backend-template", response_class=HTMLResponse)
def backend_template(request: Request):
    placeholder = "<section style='min-height:300px;display:flex;align-items:center;justify-content:center;'><strong>Template listo para montar una página de backend.</strong></section>"
    return render_backend_page(
        request,
            title="Backend Template",
            description="Cascarón para nuevas pantallas",
            content=placeholder,
            hide_floating_actions=False,
            view_buttons=[
                {"label": "Formulario", "icon": "/templates/icon/formulario.svg", "view": "form"},
                {"label": "Lista", "icon": "/templates/icon/list.svg", "view": "list"},
                {"label": "Kanban", "icon": "/templates/icon/kanban.svg", "view": "kanban"},
                {"label": "Gráfica", "icon": "/templates/icon/grid.svg", "view": "grafica"},
                {"label": "Gantt", "icon": "/templates/icon/grid.svg", "view": "gantt"},
                {"label": "Dashboard", "icon": "/templates/icon/tablero.svg", "view": "dashboard"},
                {"label": "Calendario", "icon": "/templates/icon/calendario.svg", "view": "calendario"},
            ],
        )


@app.get("/reportes", response_class=HTMLResponse)
def reportes(request: Request):
    return render_backend_page(
        request,
        title="Reportes",
        description="Resumen de indicadores, exportaciones y archivos generados",
        content=REPORTES_HTML,
        hide_floating_actions=False,
        floating_actions_html="""
            <div class="floating-actions-group" data-floating-screen="reportes">
                <button class="action-button" type="button" aria-label="Exportar">
                    <img src="/templates/icon/guardar.svg" alt="Exportar">
                    <span class="action-label">Exportar</span>
                </button>
                <button class="action-button" type="button" aria-label="Generar PDF">
                    <img src="/templates/icon/guardar.svg" alt="PDF">
                    <span class="action-label">PDF</span>
                </button>
                <button class="action-button" type="button" aria-label="Generar Excel">
                    <img src="/templates/icon/list.svg" alt="Excel">
                    <span class="action-label">Excel</span>
                </button>
            </div>
        """,
        floating_actions_screen="reportes",
    )


@app.get("/kpis", response_class=HTMLResponse)
def kpis_page(request: Request):
    return render_backend_page(
        request,
        title="KPIs",
        description="Gestión y seguimiento de indicadores clave de desempeño.",
        content=KPI_HTML,
        hide_floating_actions=True,
        show_page_header=True,
    )



# --- NUEVO: Endpoint dinámico para usuarios desde BD ---
def _render_usuarios_page(request: Request) -> HTMLResponse:
    db = SessionLocal()
    usuarios = db.query(Usuario).all()
    db.close()
    usuarios_content = f"""
        <section id="usuario-panel" class="usuario-panel">
            <div class="usuario-tabs">
                <button type="button" class="usuario-tab active" data-view="form">Form</button>
                <button type="button" class="usuario-tab" data-view="list">Lista</button>
                <button type="button" class="usuario-tab" data-view="kanban">Kanban</button>
                <button type="button" class="usuario-tab" data-view="organigrama">Organigrama</button>
            </div>
            <div id="usuario-view"></div>
        </section>
    """
    return render_backend_page(
        request,
        title="Usuarios",
        description="Gestiona usuarios, roles y permisos desde la misma pantalla",
        content=usuarios_content,
        hide_floating_actions=False,
        view_buttons=[
            {"label": "Form", "icon": "/templates/icon/formulario.svg", "view": "form", "active": True},
            {"label": "Lista", "icon": "/templates/icon/list.svg", "view": "list"},
            {"label": "Kanban", "icon": "/templates/icon/kanban.svg", "view": "kanban"},
            {"label": "Organigrama", "view": "organigrama"},
        ],
        floating_actions_screen="usuarios",
    )


@app.get("/usuarios", response_class=HTMLResponse)
@app.get("/usuarios-sistema", response_class=HTMLResponse)
def usuarios_page(request: Request):
    return _render_usuarios_page(request)


@app.get("/plantillas", response_class=HTMLResponse)
def plantillas_page(request: Request):
    plantillas_content = """
        <section id="plantillas-page" class="plantillas-page">
            <div class="plantillas-layout">
                <aside class="plantillas-list-card">
                    <h3>Plantillas</h3>
                    <p class="plantillas-hint">Selecciona una plantilla existente o crea una nueva desde la barra flotante.</p>
                    <ul id="plantillas-list" class="plantillas-list"></ul>
                </aside>
                <section class="plantillas-editor-card">
                    <div class="form-field">
                        <label for="template-name">Nombre de plantilla</label>
                        <input type="text" id="template-name" placeholder="Ej: Tarjeta institucional">
                    </div>
                    <div class="plantillas-editor-grid">
                        <div class="form-field">
                            <label for="template-html">HTML</label>
                            <textarea id="template-html" class="plantilla-code" placeholder="<section class='card'>...</section>"></textarea>
                        </div>
                        <div class="form-field">
                            <label for="template-css">CSS</label>
                            <textarea id="template-css" class="plantilla-code" placeholder=".card { padding: 16px; border-radius: 12px; }"></textarea>
                        </div>
                    </div>
                    <div class="plantillas-preview-head">
                        <h4>Vista previa</h4>
                        <button type="button" id="template-preview-btn">Previsualizar</button>
                    </div>
                    <iframe id="template-preview" class="plantilla-preview-frame" title="Vista previa de plantilla"></iframe>
                </section>
            </div>
        </section>
    """
    return render_backend_page(
        request,
        title="Plantillas",
        description="Crea y guarda plantillas con HTML y CSS.",
        content=plantillas_content,
        hide_floating_actions=False,
        floating_actions_screen="plantillas",
    )


@app.get("/api/plantillas")
def listar_plantillas():
    return JSONResponse({"success": True, "data": _load_plantillas_store()})


@app.post("/api/plantillas")
def guardar_plantilla(data: dict = Body(...)):
    nombre = (data.get("nombre") or "").strip()
    html_code = data.get("html") or ""
    css_code = data.get("css") or ""
    template_id = (data.get("id") or "").strip()
    if not nombre:
        return JSONResponse({"success": False, "error": "El nombre es obligatorio"}, status_code=400)
    if not html_code.strip() and not css_code.strip():
        return JSONResponse({"success": False, "error": "Debes agregar HTML o CSS"}, status_code=400)

    templates = _load_plantillas_store()
    now_iso = datetime.utcnow().isoformat()
    if template_id:
        updated = False
        for template in templates:
            if template.get("id") == template_id:
                template["nombre"] = nombre
                template["html"] = html_code
                template["css"] = css_code
                template["updated_at"] = now_iso
                updated = True
                break
        if not updated:
            return JSONResponse({"success": False, "error": "Plantilla no encontrada"}, status_code=404)
    else:
        template_id = secrets.token_hex(8)
        templates.insert(
            0,
            {
                "id": template_id,
                "nombre": nombre,
                "html": html_code,
                "css": css_code,
                "created_at": now_iso,
                "updated_at": now_iso,
            },
        )
    _save_plantillas_store(templates)
    return JSONResponse({"success": True, "data": {"id": template_id}})


@app.post("/api/usuarios/registro-seguro")
def crear_usuario_seguro(request: Request, data: dict = Body(...)):
    require_superadmin(request)
    nombre = (data.get("nombre") or "").strip()
    usuario_login = (data.get("usuario") or "").strip()
    correo = (data.get("correo") or "").strip()
    password = data.get("contrasena") or ""
    rol_nombre = (data.get("rol") or "").strip().lower()

    if not nombre or not usuario_login or not correo or not password:
        return JSONResponse(
            {"success": False, "error": "nombre, usuario, correo y contrasena son obligatorios"},
            status_code=400,
        )
    if len(password) < 8:
        return JSONResponse(
            {"success": False, "error": "La contraseña debe tener al menos 8 caracteres"},
            status_code=400,
        )

    db = SessionLocal()
    try:
        exists_login = db.query(Usuario).filter(Usuario.usuario == usuario_login).first()
        if exists_login:
            return JSONResponse({"success": False, "error": "El usuario ya existe"}, status_code=409)
        exists_email = db.query(Usuario).filter(Usuario.correo == correo).first()
        if exists_email:
            return JSONResponse({"success": False, "error": "El correo ya existe"}, status_code=409)

        rol_id = None
        if rol_nombre:
            rol = db.query(Rol).filter(Rol.nombre == rol_nombre).first()
            if not rol:
                return JSONResponse({"success": False, "error": "Rol no encontrado"}, status_code=404)
            rol_id = rol.id

        nuevo = Usuario(
            nombre=nombre,
            usuario=usuario_login,
            correo=correo,
            contrasena=hash_password(password),
            rol_id=rol_id,
        )
        db.add(nuevo)
        db.commit()
        db.refresh(nuevo)
        return JSONResponse(
            {
                "success": True,
                "data": {
                    "id": nuevo.id,
                    "nombre": nuevo.nombre,
                    "correo": nuevo.correo,
                    "rol_id": nuevo.rol_id,
                },
            }
        )
    finally:
        db.close()


@app.get("/api/usuarios")
def listar_usuarios_sanitizados(request: Request):
    require_superadmin(request)
    db = SessionLocal()
    try:
        roles = {r.id: r.nombre for r in db.query(Rol).all()}
        usuarios = db.query(Usuario).all()
        data = [
            {
                "id": u.id,
                "nombre": u.nombre,
                "correo": u.correo,
                "rol": roles.get(u.rol_id),
            }
            for u in usuarios
            if not is_hidden_user(request, u.usuario)
        ]
        return JSONResponse({"success": True, "data": data})
    finally:
        db.close()


def _render_areas_page(request: Request) -> HTMLResponse:
    areas_content = """
        <section id="area-panel" class="usuario-panel">
            <div class="area-tabs usuario-tabs">
                <button type="button" class="area-tab active" data-view="form">Form</button>
                <button type="button" class="area-tab" data-view="kanban">Kanban</button>
                <button type="button" class="area-tab" data-view="organigrama">Organigrama</button>
            </div>
            <div id="area-view"></div>
        </section>
    """
    return render_backend_page(
        request,
        title="Áreas organizacionales",
        description="Administra la estructura de áreas de la organización",
        content=areas_content,
        hide_floating_actions=False,
        view_buttons=[
            {"label": "Form", "icon": "/templates/icon/formulario.svg", "view": "form", "active": True},
            {"label": "Kanban", "icon": "/templates/icon/kanban.svg", "view": "kanban"},
            {"label": "Organigrama", "view": "organigrama"},
        ],
        floating_actions_screen="areas",
    )


@app.get("/areas-organizacionales", response_class=HTMLResponse)
def areas_page(request: Request):
    return _render_areas_page(request)


@app.get("/inicio", response_class=HTMLResponse)
def inicio_page(request: Request):
    return render_backend_page(
        request,
        title="Inicio",
        description="",
        content="",
        hide_floating_actions=True,
        show_page_header=False,
    )


@app.get("/planes", response_class=HTMLResponse)
def plan_estrategico_page(request: Request):
    return render_backend_page(
        request,
        title="Plan estratégico",
        description="Consolidación de planificación estratégica institucional.",
        content=PLAN_ESTRATEGICO_HTML,
        hide_floating_actions=True,
        show_page_header=True,
    )


@app.get("/poa", response_class=HTMLResponse)
def poa_page(request: Request):
    return render_backend_page(
        request,
        title="POA",
        description="Programación operativa anual alineada al plan estratégico.",
        content=POA_HTML,
        hide_floating_actions=True,
        show_page_header=True,
    )


def _render_blank_management_screen(request: Request, title: str) -> HTMLResponse:
    return render_backend_page(
        request,
        title=title,
        description="",
        content="",
        hide_floating_actions=True,
        show_page_header=False,
    )


@app.get("/diagnostico", response_class=HTMLResponse)
def diagnostico_page(request: Request):
    return _render_blank_management_screen(request, "Diagnóstico")


@app.get("/diagnostico/foda", response_class=HTMLResponse)
def diagnostico_foda_page(request: Request):
    return render_backend_page(
        request,
        title="FODA",
        description="Identifica factores internos y externos para el diagnóstico estratégico.",
        content=FODA_HTML,
        hide_floating_actions=True,
        show_page_header=True,
    )


@app.get("/diagnostico/pestel", response_class=HTMLResponse)
def diagnostico_pestel_page(request: Request):
    return render_backend_page(
        request,
        title="PESTEL",
        description="Analiza factores externos que impactan la estrategia institucional.",
        content=PESTEL_HTML,
        hide_floating_actions=True,
        show_page_header=True,
    )


@app.get("/diagnostico/porter", response_class=HTMLResponse)
def diagnostico_porter_page(request: Request):
    return render_backend_page(
        request,
        title="PORTER",
        description="Evalúa las cinco fuerzas competitivas para priorizar decisiones estratégicas.",
        content=PORTER_HTML,
        hide_floating_actions=True,
        show_page_header=True,
    )


@app.get("/diagnostico/percepcion-cliente", response_class=HTMLResponse)
def diagnostico_percepcion_cliente_page(request: Request):
    return render_backend_page(
        request,
        title="Percepción del cliente",
        description="Monitorea feedback para detectar fortalezas y brechas del servicio.",
        content=PERCEPCION_CLIENTE_HTML,
        hide_floating_actions=True,
        show_page_header=True,
    )


BACKEND_ROLES_PERMISSIONS_URL = os.environ.get(
    "BACKEND_ROLES_PERMISSIONS_URL",
    "http://localhost:8000/api/v1/personalizacion/roles-permisos"
)


async def _fetch_roles_permissions_view() -> str:
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(BACKEND_ROLES_PERMISSIONS_URL, timeout=10.0)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Error al cargar el módulo de roles: {exc}") from exc
    return resp.text.replace("http://localhost:8000", "http://localhost:8005")


@app.get("/roles-sistema", response_class=HTMLResponse)
@app.get("/roles-permisos", response_class=HTMLResponse)
@app.get("/api/v1/personalizacion/roles-permisos", response_class=HTMLResponse)
@app.get("/personalizacion/roles-permisos", response_class=HTMLResponse)
async def personalizacion_roles_permisos(request: Request):
    require_superadmin(request)
    content = await _fetch_roles_permissions_view()
    return HTMLResponse(content=content)


@app.get("/", response_class=HTMLResponse)
def root():
    return "<h1>Bienvenido al módulo de planificación estratégica y POA</h1>"

# Área de configuración de imagen (menú)
@app.get("/configura-imagen", response_class=HTMLResponse)
def configura_imagen():
    # Aquí se usará un template en el futuro
    return "<h2>Configuración de imagen (template)</h2>"


def _render_identidad_institucional_page(request: Request) -> HTMLResponse:
    identity = _load_login_identity()
    safe_company_short_name = escape(identity.get("company_short_name", DEFAULT_LOGIN_IDENTITY["company_short_name"]))
    safe_login_message = escape(identity.get("login_message", DEFAULT_LOGIN_IDENTITY["login_message"]))
    logo_url = _build_login_asset_url(identity.get("logo_filename"), DEFAULT_LOGIN_IDENTITY["logo_filename"])
    desktop_bg_url = _build_login_asset_url(identity.get("desktop_bg_filename"), DEFAULT_LOGIN_IDENTITY["desktop_bg_filename"])
    mobile_bg_url = _build_login_asset_url(identity.get("mobile_bg_filename"), DEFAULT_LOGIN_IDENTITY["mobile_bg_filename"])
    saved_flag = request.query_params.get("saved")
    saved_message = "<p style='color:#166534;font-weight:600;margin:0 0 12px;'>Identidad institucional actualizada.</p>" if saved_flag == "1" else ""
    content = f"""
        <section class="foda-page">
            <article class="foda-input-card">
                <h2>Identidad institucional</h2>
                <p>Esta configuración alimenta la pantalla de login. Si no hay datos, se usan valores por defecto.</p>
                {saved_message}
                <form method="post" action="/identidad-institucional" enctype="multipart/form-data" class="foda-input-grid">
                    <div class="form-field">
                        <label for="logo_empresa">Logo de la empresa</label>
                        <input type="file" id="logo_empresa" name="logo_empresa" accept="image/*">
                        <small>Actual: {identity.get("logo_filename", DEFAULT_LOGIN_IDENTITY["logo_filename"])}</small>
                    </div>
                    <div class="form-field">
                        <label for="fondo_escritorio">Fondo de escritorio</label>
                        <input type="file" id="fondo_escritorio" name="fondo_escritorio" accept="image/*">
                        <small>Actual: {identity.get("desktop_bg_filename", DEFAULT_LOGIN_IDENTITY["desktop_bg_filename"])}</small>
                    </div>
                    <div class="form-field">
                        <label for="fondo_movil">Fondo de móvil</label>
                        <input type="file" id="fondo_movil" name="fondo_movil" accept="image/*">
                        <small>Actual: {identity.get("mobile_bg_filename", DEFAULT_LOGIN_IDENTITY["mobile_bg_filename"])}</small>
                    </div>
                    <div class="form-field">
                        <label for="company_short_name">Nombre corto de la empresa</label>
                        <input type="text" id="company_short_name" name="company_short_name" value="{safe_company_short_name}" placeholder="Ej: AVAN">
                    </div>
                    <div class="form-field">
                        <label for="login_message">Mensaje para pantalla de login</label>
                        <textarea id="login_message" name="login_message" rows="3" placeholder="Mensaje institucional">{safe_login_message}</textarea>
                    </div>
                    <div class="foda-input-actions" style="grid-column: 1 / -1;">
                        <button type="submit">Guardar identidad</button>
                    </div>
                </form>
            </article>
            <section class="foda-matrix">
                <article class="foda-quadrant">
                    <header><h3>Vista previa logo</h3></header>
                    <img src="{logo_url}" alt="Logo" style="max-width:100%;max-height:180px;object-fit:contain;">
                </article>
                <article class="foda-quadrant">
                    <header><h3>Vista previa fondo escritorio</h3></header>
                    <img src="{desktop_bg_url}" alt="Fondo escritorio" style="max-width:100%;max-height:180px;object-fit:cover;">
                </article>
                <article class="foda-quadrant">
                    <header><h3>Vista previa fondo móvil</h3></header>
                    <img src="{mobile_bg_url}" alt="Fondo móvil" style="max-width:100%;max-height:180px;object-fit:cover;">
                </article>
            </section>
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


@app.get("/identidad-institucional", response_class=HTMLResponse)
def identidad_institucional_page(request: Request):
    return _render_identidad_institucional_page(request)


@app.post("/identidad-institucional", response_class=HTMLResponse)
async def identidad_institucional_save(
    request: Request,
    company_short_name: str = Form(""),
    login_message: str = Form(""),
    logo_empresa: Optional[UploadFile] = File(None),
    fondo_escritorio: Optional[UploadFile] = File(None),
    fondo_movil: Optional[UploadFile] = File(None),
):
    current = _load_login_identity()
    current["company_short_name"] = company_short_name.strip() or DEFAULT_LOGIN_IDENTITY["company_short_name"]
    current["login_message"] = login_message.strip() or DEFAULT_LOGIN_IDENTITY["login_message"]

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
    return RedirectResponse(url="/identidad-institucional?saved=1", status_code=303)

# Placeholder para templates
# En el futuro, importar y usar templates para todas las respuestas

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
