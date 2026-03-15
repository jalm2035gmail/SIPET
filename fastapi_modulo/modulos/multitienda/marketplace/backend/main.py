import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import bcrypt
from sqlalchemy import select, text, inspect

from apps.users.routes import router as users_router
from apps.users.models import User, UserType
from apps.vendors.routes import router as vendors_router
from apps.products.routes import router as products_router
from apps.orders.routes import router as orders_router
from apps.payments.routes import router as payments_router
from core.db import engine

# Registrar modelos relacionados para resolver relationships SQLAlchemy.
import apps.analytics.models  # noqa: F401
import apps.commissions.models  # noqa: F401

BACKEND_ROOT_PATH = os.getenv("BACKEND_ROOT_PATH", "")
BACKEND_ROUTE_PREFIX = os.getenv("BACKEND_ROUTE_PREFIX", "").rstrip("/")
if BACKEND_ROUTE_PREFIX and not BACKEND_ROUTE_PREFIX.startswith("/"):
    BACKEND_ROUTE_PREFIX = f"/{BACKEND_ROUTE_PREFIX}"

app = FastAPI(title="MultiTiendApp API", root_path=BACKEND_ROOT_PATH)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = PROJECT_ROOT / "static"
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

SEED_USER_USERNAME = "0konomiyaki"
SEED_USER_PASSWORD = "XX,$,26,multitienda,26,$,XX"
SEED_USER_EMAIL = "0konomiyaki@multitienda.local"

BACKEND_SHARED_SIDEBAR_CSS = """
    .menu-toggle {
      position: fixed;
      top: 16px;
      left: 16px;
      width: 44px;
      height: 44px;
      border: 1px solid #d0d0d0;
      border-radius: 8px;
      background: #fff;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      z-index: 20;
    }

    .menu-icon,
    .menu-icon::before,
    .menu-icon::after {
      width: 20px;
      height: 2px;
      background: #222;
      border-radius: 2px;
      display: block;
      content: "";
      transition: transform 0.2s ease, opacity 0.2s ease;
      position: relative;
    }

    .menu-icon::before {
      position: absolute;
      top: -6px;
      left: 0;
    }

    .menu-icon::after {
      position: absolute;
      top: 6px;
      left: 0;
    }

    .menu-panel {
      position: fixed;
      top: 0;
      left: 0;
      width: 240px;
      height: 100%;
      background: #fff5ee;
      border-right: 1px solid #ececec;
      box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
      transform: translateX(-100%);
      transition: transform 0.2s ease;
      z-index: 15;
      padding-top: 20px;
    }

    .menu-header {
      padding: 12px 16px 16px;
      border-bottom: 1px solid #ececec;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 72px;
    }

    .menu-header img {
      max-width: 100%;
      max-height: 60px;
      object-fit: contain;
    }

    .menu-panel.open {
      transform: translateX(0);
    }

    .menu-list {
      list-style: none;
      margin: 0;
      padding: 0;
    }

    .menu-list > li {
      border-bottom: 1px solid #f1f1f1;
    }

    .menu-list a {
      display: block;
      padding: 12px 18px;
      color: #164723;
      text-decoration: none;
    }

    .menu-list a:hover {
      background: #f0f0f0;
    }

    .menu-label {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 12px 18px 6px;
      color: #164723;
      font-size: 0.9rem;
      font-weight: 700;
      letter-spacing: 0.04em;
    }

    .menu-label-icon {
      width: 16px;
      height: 16px;
      flex: 0 0 16px;
      background-color: currentColor;
      -webkit-mask: url('/static/icons/personalizar.svg') no-repeat center / contain;
      mask: url('/static/icons/personalizar.svg') no-repeat center / contain;
    }

    .menu-label-icon-config {
      width: 16px;
      height: 16px;
      flex: 0 0 16px;
      background-color: currentColor;
      -webkit-mask: url('/static/icons/configuracion.svg') no-repeat center / contain;
      mask: url('/static/icons/configuracion.svg') no-repeat center / contain;
    }

    .submenu {
      list-style: none;
      margin: 0;
      padding: 0 0 8px;
    }

    .submenu a {
      padding-left: 34px;
    }

    .submenu-group > summary {
      list-style: none;
      cursor: pointer;
      padding: 12px 34px;
      color: #164723;
      user-select: none;
    }

    .submenu-group > summary::-webkit-details-marker {
      display: none;
    }

    .submenu-nested {
      list-style: none;
      margin: 0;
      padding: 0 0 8px;
    }

    .submenu-nested a {
      padding-left: 50px;
    }
"""

BACKEND_SHARED_SIDEBAR_HTML = """
  <button id="menuBtn" class="menu-toggle" aria-label="Abrir menu" aria-expanded="false" aria-controls="menuPanel">
    <span class="menu-icon"></span>
  </button>

  <nav id="menuPanel" class="menu-panel" aria-hidden="true">
    <div class="menu-header">
      <img src="/static/imagenes/tu-negocio.png" alt="Tu Negocio" />
    </div>
    <ul class="menu-list">
      <li><a href="#">Inicio</a></li>
      <li><a href="#">Productos</a></li>
      <li><a href="#">Pedidos</a></li>
      <li id="configuracionItem">
        <span class="menu-label">
          <span class="menu-label-icon-config" aria-hidden="true"></span>
          Configuración
        </span>
        <ul class="submenu">
          <li><a href="__CONFIG_PATH__">Configuración</a></li>
        </ul>
      </li>
      <li id="personalizarItem">
        <span class="menu-label">
          <span class="menu-label-icon" aria-hidden="true"></span>
          Personalizar
        </span>
        <ul class="submenu">
          <li><a href="__BLANK_PATH__">Agregar nueva tienda</a></li>
          <li><a href="__ADD_USER_PATH__">Vendedores</a></li>
          <li>
            <details class="submenu-group">
              <summary>Template</summary>
              <ul class="submenu-nested">
                <li><a href="__TEMPLATE_PATH__">Backend</a></li>
                <li><a href="__TEMPLATE_FRONTEND_PATH__">Frontend</a></li>
              </ul>
            </details>
          </li>
        </ul>
      </li>
      <li><a href="#">Cerrar</a></li>
    </ul>
  </nav>
"""

BACKEND_SHARED_FORM_BASE_CSS = """
    .page {
      max-width: 1100px;
      margin: 0 auto;
      padding: 28px 18px 40px 72px;
    }

    .title {
      margin: 0 0 6px;
      font-size: 1.6rem;
      font-weight: 700;
    }

    .subtitle {
      margin: 0 0 24px;
      color: #6b7280;
      font-size: 0.95rem;
    }

    .section {
      background: #fff;
      border: 1px solid #e6e8ee;
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 16px;
    }

    .section h2 {
      margin: 0 0 14px;
      font-size: 1.05rem;
    }

    .section-grid {
      display: grid;
      grid-template-columns: 1fr 320px;
      gap: 24px;
    }

    .field {
      margin-bottom: 14px;
    }

    label {
      display: block;
      margin-bottom: 8px;
      font-size: 1rem;
      font-weight: 700;
      color: #2f343b;
      text-transform: none;
    }

    .field-input {
      width: 100%;
      height: 50px;
      border: 1px solid #eadfe2;
      border-radius: 14px;
      padding: 0 14px;
      font-size: 1.1rem;
      outline: none;
      background: #f2e9eb;
      color: #1f2937;
    }

    .field-input:focus {
      border-color: #9ea3ad;
      box-shadow: 0 0 0 3px rgba(158, 163, 173, 0.15);
    }

    .field-select {
      appearance: none;
      cursor: pointer;
    }
"""


def render_backend_view_html(html: str, blank_path: str, add_user_path: str, config_path: str, template_path: str, template_frontend_path: str, extra_replacements: dict | None = None) -> str:
    rendered = (
        html.replace("__BACKEND_SHARED_SIDEBAR_CSS__", BACKEND_SHARED_SIDEBAR_CSS)
        .replace("__BACKEND_SHARED_SIDEBAR_HTML__", BACKEND_SHARED_SIDEBAR_HTML)
        .replace("__BACKEND_SHARED_FORM_BASE_CSS__", BACKEND_SHARED_FORM_BASE_CSS)
        .replace("__BLANK_PATH__", blank_path)
        .replace("__ADD_USER_PATH__", add_user_path)
        .replace("__CONFIG_PATH__", config_path)
        .replace("__TEMPLATE_PATH__", template_path)
        .replace("__TEMPLATE_FRONTEND_PATH__", template_frontend_path)
    )
    if extra_replacements:
        for key, value in extra_replacements.items():
            rendered = rendered.replace(key, value)
    return rendered


@app.on_event("startup")
def seed_default_user():
    User.__table__.create(bind=engine, checkfirst=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS user_notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title VARCHAR(120) NOT NULL,
                    message TEXT NOT NULL,
                    is_read BOOLEAN NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
    inspector = inspect(engine)
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "two_factor_enabled" not in user_columns:
        with engine.begin() as conn:
            conn.execute(
                text("ALTER TABLE users ADD COLUMN two_factor_enabled BOOLEAN NOT NULL DEFAULT 0")
            )

    with engine.begin() as conn:
        existing = conn.execute(
            select(User.__table__.c.id).where(User.__table__.c.username == SEED_USER_USERNAME)
        ).first()
        seed_user_id = existing[0] if existing else None
        if not seed_user_id:
            seed_email = SEED_USER_EMAIL
            email_in_use = conn.execute(
                select(User.__table__.c.id).where(User.__table__.c.email == seed_email)
            ).first()
            if email_in_use:
                seed_email = f"{SEED_USER_USERNAME}+seed@multitienda.local"

            insert_result = conn.execute(
                User.__table__.insert().values(
                    username=SEED_USER_USERNAME,
                    email=seed_email,
                    hashed_password=bcrypt.hashpw(
                        SEED_USER_PASSWORD.encode("utf-8"), bcrypt.gensalt()
                    ).decode("utf-8"),
                    user_type=UserType.superadmin,
                    two_factor_enabled=False,
                )
            )
            seed_user_id = insert_result.inserted_primary_key[0]

        existing_notification = conn.execute(
            text(
                """
                SELECT id
                FROM user_notifications
                WHERE user_id = :user_id AND title = :title
                LIMIT 1
                """
            ),
            {"user_id": seed_user_id, "title": "Bienvenido"},
        ).first()
        if not existing_notification:
            conn.execute(
                text(
                    """
                    INSERT INTO user_notifications (user_id, title, message, is_read)
                    VALUES (:user_id, :title, :message, 0)
                    """
                ),
                {
                    "user_id": seed_user_id,
                    "title": "Bienvenido",
                    "message": "Tu panel de administración está listo.",
                },
            )


@app.get(f"{BACKEND_ROUTE_PREFIX}/", response_class=HTMLResponse)
def root_blank():
    blank_path = f"{BACKEND_ROUTE_PREFIX}/gestion" if BACKEND_ROUTE_PREFIX else "/gestion"
    add_user_path = f"{BACKEND_ROUTE_PREFIX}/agregar-usuario" if BACKEND_ROUTE_PREFIX else "/agregar-usuario"
    config_path = f"{BACKEND_ROUTE_PREFIX}/configuracion" if BACKEND_ROUTE_PREFIX else "/configuracion"
    template_path = f"{BACKEND_ROUTE_PREFIX}/template" if BACKEND_ROUTE_PREFIX else "/template"
    template_frontend_path = (
        f"{BACKEND_ROUTE_PREFIX}/template-frontend" if BACKEND_ROUTE_PREFIX else "/template-frontend"
    )
    html = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="icon" type="image/png" href="/static/imagenes/tu-negocio.png" />
  <title>Menu</title>
  <style>
    html, body {
      width: 100%;
      height: 100%;
      margin: 0;
      background: #fff;
      font-family: Arial, sans-serif;
    }

    .menu-toggle {
      position: fixed;
      top: 16px;
      left: 16px;
      width: 44px;
      height: 44px;
      border: 1px solid #d0d0d0;
      border-radius: 8px;
      background: #fff;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      z-index: 20;
    }

    .menu-icon,
    .menu-icon::before,
    .menu-icon::after {
      width: 20px;
      height: 2px;
      background: #222;
      border-radius: 2px;
      display: block;
      content: "";
      transition: transform 0.2s ease, opacity 0.2s ease;
      position: relative;
    }

    .menu-icon::before {
      position: absolute;
      top: -6px;
      left: 0;
    }

    .menu-icon::after {
      position: absolute;
      top: 6px;
      left: 0;
    }

    .menu-panel {
      position: fixed;
      top: 0;
      left: 0;
      width: 240px;
      height: 100%;
      background: #fff5ee;
      border-right: 1px solid #ececec;
      box-shadow: 0 8px 30px rgba(0, 0, 0, 0.08);
      transform: translateX(-100%);
      transition: transform 0.2s ease;
      z-index: 15;
      padding-top: 20px;
    }

    .menu-header {
      padding: 12px 16px 16px;
      border-bottom: 1px solid #ececec;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 72px;
    }

    .menu-header img {
      max-width: 100%;
      max-height: 60px;
      object-fit: contain;
    }

    .menu-panel.open {
      transform: translateX(0);
    }

    .menu-list {
      list-style: none;
      margin: 0;
      padding: 0;
    }

    .menu-list > li {
      border-bottom: 1px solid #f1f1f1;
    }

    .menu-list a {
      display: block;
      padding: 12px 18px;
      color: #164723;
      text-decoration: none;
    }

    .menu-list a:hover {
      background: #f0f0f0;
    }

    .menu-label {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 12px 18px 6px;
      color: #164723;
      font-size: 0.9rem;
      font-weight: 700;
      letter-spacing: 0.04em;
    }

    .menu-label-icon {
      width: 16px;
      height: 16px;
      flex: 0 0 16px;
      background-color: currentColor;
      -webkit-mask: url('/static/icons/personalizar.svg') no-repeat center / contain;
      mask: url('/static/icons/personalizar.svg') no-repeat center / contain;
    }

    .menu-label-icon-config {
      width: 16px;
      height: 16px;
      flex: 0 0 16px;
      background-color: currentColor;
      -webkit-mask: url('/static/icons/configuracion.svg') no-repeat center / contain;
      mask: url('/static/icons/configuracion.svg') no-repeat center / contain;
    }

    .submenu {
      list-style: none;
      margin: 0;
      padding: 0 0 8px;
    }

    .submenu a {
      padding-left: 34px;
    }

    .submenu-group > summary {
      list-style: none;
      cursor: pointer;
      padding: 12px 34px;
      color: #164723;
      user-select: none;
    }

    .submenu-group > summary::-webkit-details-marker {
      display: none;
    }

    .submenu-nested {
      list-style: none;
      margin: 0;
      padding: 0 0 8px;
    }

    .submenu-nested a {
      padding-left: 50px;
    }
  </style>
</head>
<body>
__BACKEND_SHARED_SIDEBAR_HTML__

  <script src="/static/js/backend-sidebar-core.js"></script>
  <script>
    (function () {
      if (window.initBackendSidebarCore) {
        window.initBackendSidebarCore();
      }
    })();
  </script>
  <script src="/static/js/sidebar-theme-editor.js"></script>
  <script src="/static/js/backend-navbar.js"></script>
</body>
</html>
"""
    return render_backend_view_html(
        html=html,
        blank_path=blank_path,
        add_user_path=add_user_path,
        config_path=config_path,
        template_path=template_path,
        template_frontend_path=template_frontend_path,
    )


@app.get(f"{BACKEND_ROUTE_PREFIX}/health")
def health():
    return {"status": "ok", "prefix": BACKEND_ROUTE_PREFIX or "/"}


@app.get("/web/login", response_class=HTMLResponse)
@app.get(f"{BACKEND_ROUTE_PREFIX}/web/login", response_class=HTMLResponse)
def web_login_view():
    login_api_path = f"{BACKEND_ROUTE_PREFIX}/users/login" if BACKEND_ROUTE_PREFIX else "/users/login"
    home_path = f"{BACKEND_ROUTE_PREFIX}/" if BACKEND_ROUTE_PREFIX else "/"
    html = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="icon" type="image/png" href="/static/imagenes/tu-negocio.png" />
  <title>Login</title>
  <style>
    html, body {
      margin: 0;
      padding: 0;
      min-height: 100vh;
      font-family: "Nunito Sans", "Trebuchet MS", Arial, sans-serif;
      background: #e8e8ea;
      color: #1f2328;
    }

    .wrap {
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 24px;
    }

    .panel {
      width: min(1600px, 100%);
      min-height: 760px;
      display: grid;
      grid-template-columns: 1.05fr 1.45fr;
      gap: 18px;
    }

    .form-side {
      background: #f3f3f5;
      border-radius: 30px;
      padding: 42px;
      display: grid;
      align-content: start;
    }

    .login-card {
      width: min(500px, 100%);
      margin: 0 auto;
    }

    .logo-wrap {
      display: grid;
      place-items: center;
    }

    .logo-wrap img {
      width: 188px;
      height: 188px;
      object-fit: contain;
    }

    .separator {
      height: 1px;
      background: #cfcfd4;
      margin: 12px 0 42px;
    }

    .form {
      display: grid;
      gap: 18px;
    }

    .field-group {
      display: grid;
      gap: 10px;
    }

    .field-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }

    label {
      font-size: 2.75rem;
      color: #1f2328;
      margin: 0;
    }

    .inline-link {
      border: 0;
      background: transparent;
      padding: 0;
      color: #a8680f;
      font-size: 1.9rem;
      cursor: pointer;
    }

    .form input {
      height: 92px;
      border-radius: 24px;
      border: 2px solid #b6c3d8;
      background: #c9d3e3;
      padding: 0 22px;
      font-size: 2.6rem;
      color: #111827;
      outline: none;
    }

    .form input:focus {
      border-color: #798eb3;
    }

    .submit-btn {
      margin-top: 10px;
      width: 100%;
      height: 94px;
      border: 0;
      border-radius: 24px;
      background: #5c5fe0;
      color: #fff;
      font-size: 4rem;
      font-weight: 700;
      cursor: pointer;
    }

    .submit-btn:disabled {
      opacity: 0.7;
      cursor: wait;
    }

    .msg {
      margin: 4px 0 0;
      font-size: 1.7rem;
      font-weight: 700;
      min-height: 1.2em;
    }

    .error { color: #b91c1c; }
    .ok { color: #166534; }

    .signup-text {
      margin: 18px 0 0;
      text-align: center;
      color: #a8680f;
      font-size: 2rem;
    }

    .hero-side {
      border-radius: 30px;
      overflow: hidden;
      position: relative;
    }

    .hero-image {
      width: 100%;
      height: 100%;
      background: url('/static/imagenes/login.png') center / cover no-repeat;
      position: relative;
      display: flex;
      align-items: flex-end;
    }

    .hero-overlay {
      position: absolute;
      inset: 0;
      background: rgba(15, 16, 20, 0.25);
    }

    .hero-copy {
      position: relative;
      z-index: 1;
      padding: 0 56px 54px;
      color: #fff;
    }

    .hero-copy h2 {
      margin: 0;
      font-size: 5.7rem;
      line-height: 1.05;
      font-weight: 700;
    }

    .hero-copy p {
      margin: 12px 0 0;
      font-size: 2.65rem;
      line-height: 1.3;
    }

    @media (max-width: 1320px) {
      .wrap { padding: 14px; }
      .panel { gap: 14px; min-height: 680px; }
      .form-side { border-radius: 22px; padding: 28px 26px; }
      .hero-side { border-radius: 22px; }
      .logo-wrap img { width: 128px; height: 128px; }
      .separator { margin-bottom: 26px; }
      label { font-size: 1.95rem; }
      .inline-link { font-size: 1.35rem; }
      .form input { height: 64px; border-radius: 16px; font-size: 1.6rem; }
      .submit-btn { height: 68px; border-radius: 16px; font-size: 2.2rem; }
      .msg { font-size: 1.05rem; }
      .signup-text { font-size: 1.2rem; }
      .hero-copy { padding: 0 30px 28px; }
      .hero-copy h2 { font-size: 3.2rem; }
      .hero-copy p { font-size: 1.35rem; }
    }

    @media (max-width: 980px) {
      .panel { grid-template-columns: 1fr; min-height: auto; }
      .hero-side { order: 1; min-height: 340px; }
      .form-side { order: 2; }
      .hero-copy h2 { font-size: 2.5rem; }
      .hero-copy p { font-size: 1.1rem; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="panel">
      <div class="form-side">
        <div class="login-card">
          <div class="logo-wrap">
            <img src="/static/imagenes/tu-negocio.png" alt="Tu Negocio" />
          </div>
          <div class="separator"></div>

          <form id="loginForm" class="form">
            <div class="field-group">
              <div class="field-header">
                <label for="username">Correo electrónico</label>
                <button class="inline-link" type="button">Elija un usuario</button>
              </div>
              <input id="username" name="username" type="text" autocomplete="username" placeholder="alopez@avancoop.org" required />
            </div>
            <div class="field-group">
              <div class="field-header">
                <label for="password">Contraseña</label>
                <button class="inline-link" type="button">Restablecer contraseña</button>
              </div>
              <input id="password" name="password" type="password" autocomplete="current-password" placeholder="•••••••" required />
            </div>
            <button id="submitBtn" class="submit-btn" type="submit">Login</button>
            <p id="message" class="msg"></p>
          </form>

          <p class="signup-text">¿No tiene una cuenta?</p>
        </div>
      </div>

      <div class="hero-side">
        <div class="hero-image">
          <div class="hero-overlay"></div>
          <div class="hero-copy">
            <h2>Gestiona tu negocio</h2>
            <p>Organiza ventas, inventario y contabilidad en un solo lugar.</p>
          </div>
        </div>
      </div>
    </section>
  </div>

  <script>
    (function () {
      const form = document.getElementById("loginForm");
      const submitBtn = document.getElementById("submitBtn");
      const message = document.getElementById("message");

      form.addEventListener("submit", async function (event) {
        event.preventDefault();
        message.textContent = "";
        message.className = "msg";
        submitBtn.disabled = true;
        submitBtn.textContent = "Ingresando...";

        const username = document.getElementById("username").value.trim();
        const password = document.getElementById("password").value;

        try {
          const body = new URLSearchParams({ username: username, password: password });
          const loginPaths = Array.from(
            new Set(["__LOGIN_API_PATH__", "/avan/users/login", "/users/login"])
          );
          let response = null;
          let lastNetworkError = null;

          for (const path of loginPaths) {
            try {
              const attempt = await fetch(path, {
                method: "POST",
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
                body: body.toString(),
              });
              if (attempt.status === 404) {
                continue;
              }
              response = attempt;
              break;
            } catch (networkError) {
              lastNetworkError = networkError;
            }
          }

          if (!response) {
            if (lastNetworkError) {
              throw new Error("No se pudo conectar al servidor. Verifica que el backend esté activo.");
            }
            throw new Error("No se encontró la ruta de login en el backend.");
          }

          const raw = await response.text();
          let data = null;
          try {
            data = raw ? JSON.parse(raw) : null;
          } catch (parseError) {
            data = null;
          }
          if (!response.ok) {
            const backendMessage =
              (data && (data.detail || data.message || data.error)) ||
              (raw && raw.trim()) ||
              "";
            const statusText = response.status ? ` (HTTP ${response.status})` : "";
            throw new Error(
              backendMessage || `No se pudo iniciar sesión.${statusText}`
            );
          }

          if (!data || !data.access_token) {
            throw new Error("No se recibió token de acceso.");
          }

          localStorage.setItem("access_token", data.access_token);
          localStorage.setItem("token_type", data.token_type || "bearer");
          message.textContent = "Inicio de sesión correcto.";
          message.className = "msg ok";
          window.location.href = "__HOME_PATH__";
        } catch (error) {
          const errorText = (error && error.message) || "";
          message.textContent = errorText || "Error al iniciar sesión.";
          message.className = "msg error";
        } finally {
          submitBtn.disabled = false;
          submitBtn.textContent = "Login";
        }
      });
    })();
  </script>
  <script src="/static/js/sidebar-theme-editor.js"></script>
  <script src="/static/js/backend-navbar.js"></script>
</body>
</html>
"""
    return html.replace("__LOGIN_API_PATH__", login_api_path).replace("__HOME_PATH__", home_path)


@app.get(f"{BACKEND_ROUTE_PREFIX}/admin", response_class=HTMLResponse)
def admin_view(request: Request):
    blank_path = f"{BACKEND_ROUTE_PREFIX}/gestion" if BACKEND_ROUTE_PREFIX else "/gestion"
    add_user_path = f"{BACKEND_ROUTE_PREFIX}/agregar-usuario" if BACKEND_ROUTE_PREFIX else "/agregar-usuario"
    config_path = f"{BACKEND_ROUTE_PREFIX}/configuracion" if BACKEND_ROUTE_PREFIX else "/configuracion"
    template_path = f"{BACKEND_ROUTE_PREFIX}/template" if BACKEND_ROUTE_PREFIX else "/template"
    template_frontend_path = (
        f"{BACKEND_ROUTE_PREFIX}/template-frontend" if BACKEND_ROUTE_PREFIX else "/template-frontend"
    )
    return templates.TemplateResponse(
        request=request,
        name="backend_template.html",
        context={
            "title": "Admin",
            "page_heading": "Admin",
            "page_subtitle": "Vista de administración con layout backend unificado.",
            "blank_path": blank_path,
            "add_user_path": add_user_path,
            "config_path": config_path,
            "template_path": template_path,
            "template_frontend_path": template_frontend_path,
        },
    )


@app.get(f"{BACKEND_ROUTE_PREFIX}/configuracion", response_class=HTMLResponse)
def config_view(request: Request):
    blank_path = f"{BACKEND_ROUTE_PREFIX}/gestion" if BACKEND_ROUTE_PREFIX else "/gestion"
    add_user_path = f"{BACKEND_ROUTE_PREFIX}/agregar-usuario" if BACKEND_ROUTE_PREFIX else "/agregar-usuario"
    config_path = f"{BACKEND_ROUTE_PREFIX}/configuracion" if BACKEND_ROUTE_PREFIX else "/configuracion"
    template_path = f"{BACKEND_ROUTE_PREFIX}/template" if BACKEND_ROUTE_PREFIX else "/template"
    template_frontend_path = (
        f"{BACKEND_ROUTE_PREFIX}/template-frontend" if BACKEND_ROUTE_PREFIX else "/template-frontend"
    )
    return templates.TemplateResponse(
        request=request,
        name="backend_template.html",
        context={
            "title": "Configuración",
            "page_heading": "Configuración",
            "page_subtitle": "Vista de configuración con layout backend unificado.",
            "is_config_shell": True,
            "blank_path": blank_path,
            "add_user_path": add_user_path,
            "config_path": config_path,
            "template_path": template_path,
            "template_frontend_path": template_frontend_path,
        },
    )


@app.get(f"{BACKEND_ROUTE_PREFIX}/template", response_class=HTMLResponse)
def template_view(request: Request):
    blank_path = f"{BACKEND_ROUTE_PREFIX}/gestion" if BACKEND_ROUTE_PREFIX else "/gestion"
    add_user_path = f"{BACKEND_ROUTE_PREFIX}/agregar-usuario" if BACKEND_ROUTE_PREFIX else "/agregar-usuario"
    config_path = f"{BACKEND_ROUTE_PREFIX}/configuracion" if BACKEND_ROUTE_PREFIX else "/configuracion"
    template_path = f"{BACKEND_ROUTE_PREFIX}/template" if BACKEND_ROUTE_PREFIX else "/template"
    template_frontend_path = (
        f"{BACKEND_ROUTE_PREFIX}/template-frontend" if BACKEND_ROUTE_PREFIX else "/template-frontend"
    )
    return templates.TemplateResponse(
        request=request,
        name="backend_template.html",
        context={
            "title": "Template Backend",
            "blank_path": blank_path,
            "add_user_path": add_user_path,
            "config_path": config_path,
            "template_path": template_path,
            "template_frontend_path": template_frontend_path,
        },
    )


@app.get(f"{BACKEND_ROUTE_PREFIX}/template-frontend", response_class=HTMLResponse)
def template_frontend_view(request: Request):
    return """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="icon" type="image/png" href="/static/imagenes/tu-negocio.png" />
  <title>Template frontend</title>
  <link rel="stylesheet" href="/static/templates/fields-template.css" />
  <style>
    html, body {
      margin: 0;
      padding: 0;
      background: #f5f6f8;
      font-family: Arial, sans-serif;
      color: #1f2937;
    }

    * {
      box-sizing: border-box;
    }

    .content {
      max-width: 980px;
      margin: 0 auto;
      padding: 28px 18px 40px 72px;
    }

    .section {
      background: #fff;
      border: 1px solid #e6e8ee;
      border-radius: 12px;
      padding: 20px;
      margin-bottom: 16px;
    }

    .section h1 {
      margin: 0 0 12px;
      font-size: 1.35rem;
    }

    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }

    .field {
      display: grid;
      gap: 8px;
    }

    .field label {
      font-size: 1rem;
      font-weight: 700;
      color: #2f343b;
    }

    @media (max-width: 860px) {
      .grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <button id="templateSidebarBtn" class="template-sidebar-toggle" aria-label="Abrir menu" aria-expanded="false" aria-controls="templateSidebarPanel">
    <span class="template-sidebar-icon"></span>
  </button>

  <nav id="templateSidebarPanel" class="template-sidebar-panel" aria-hidden="true">
    <div class="template-sidebar-header">
      <img src="/static/imagenes/tu-negocio.png" alt="Tu Negocio" />
    </div>
    <ul class="template-sidebar-list">
      <li><a href="#">Inicio</a></li>
      <li><a href="#">Productos</a></li>
      <li>
        <span class="template-sidebar-label">Template frontend</span>
        <ul class="template-sidebar-submenu">
          <li><a href="#">Formulario base</a></li>
        </ul>
      </li>
    </ul>
  </nav>

  <main class="content">
    <section class="section">
      <h1>Template frontend reutilizado</h1>
      <div class="grid">
        <div class="field">
          <label for="field1">Nombre</label>
          <input id="field1" class="template-field-input" type="text" placeholder="Ej. Tienda Norte" />
        </div>
        <div class="field">
          <label for="field2">Categoría</label>
          <input id="field2" class="template-field-input" type="text" placeholder="Ej. Moda" />
        </div>
        <div class="field">
          <label for="field3">Administrador</label>
          <input id="field3" class="template-field-input" type="text" placeholder="Nombre del responsable" />
        </div>
        <div class="field">
          <label for="field4">Correo</label>
          <input id="field4" class="template-field-input" type="email" placeholder="correo@ejemplo.com" />
        </div>
      </div>
    </section>
  </main>

  <script>
    (function () {
      const btn = document.getElementById("templateSidebarBtn");
      const panel = document.getElementById("templateSidebarPanel");

      function setOpen(open) {
        panel.classList.toggle("open", open);
        btn.setAttribute("aria-expanded", open ? "true" : "false");
        panel.setAttribute("aria-hidden", open ? "false" : "true");
      }

      btn.addEventListener("click", function () {
        const open = btn.getAttribute("aria-expanded") !== "true";
        setOpen(open);
      });

      document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
          setOpen(false);
        }
      });
    })();
  </script>
  <script src="/static/js/sidebar-theme-editor.js"></script>
  <script src="/static/js/backend-navbar.js"></script>
</body>
</html>
"""


@app.get(f"{BACKEND_ROUTE_PREFIX}/gestion", response_class=HTMLResponse)
def blank_view():
    blank_path = f"{BACKEND_ROUTE_PREFIX}/gestion" if BACKEND_ROUTE_PREFIX else "/gestion"
    add_user_path = f"{BACKEND_ROUTE_PREFIX}/agregar-usuario" if BACKEND_ROUTE_PREFIX else "/agregar-usuario"
    config_path = f"{BACKEND_ROUTE_PREFIX}/configuracion" if BACKEND_ROUTE_PREFIX else "/configuracion"
    template_path = f"{BACKEND_ROUTE_PREFIX}/template" if BACKEND_ROUTE_PREFIX else "/template"
    template_frontend_path = (
        f"{BACKEND_ROUTE_PREFIX}/template-frontend" if BACKEND_ROUTE_PREFIX else "/template-frontend"
    )
    users_path = f"{BACKEND_ROUTE_PREFIX}/users/system-users" if BACKEND_ROUTE_PREFIX else "/users/system-users"
    html = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="icon" type="image/png" href="/static/imagenes/tu-negocio.png" />
  <title>Agregar Nueva Tienda</title>
  <style>
    html, body {
      margin: 0;
      padding: 0;
      background: #f5f6f8;
      font-family: Arial, sans-serif;
      color: #1f2937;
    }

    * {
      box-sizing: border-box;
    }

__BACKEND_SHARED_SIDEBAR_CSS__

__BACKEND_SHARED_FORM_BASE_CSS__

    .business-type-tools {
      margin-top: 8px;
      display: grid;
      gap: 6px;
    }

    .business-type-btn {
      width: fit-content;
      border: 1px solid #d1d5db;
      border-radius: 8px;
      background: #fff;
      color: #1f2937;
      font-size: 0.82rem;
      font-weight: 700;
      padding: 6px 10px;
      cursor: pointer;
    }

    .business-type-description {
      font-size: 0.83rem;
      color: #475569;
    }

    .business-type-panel {
      margin-top: 10px;
      border: 1px solid #dbe2ea;
      border-radius: 10px;
      background: #f8fafc;
      padding: 10px;
      display: grid;
      gap: 8px;
    }

    .business-type-panel[hidden] {
      display: none;
    }

    .business-type-grid {
      display: grid;
      grid-template-columns: 1fr 160px;
      gap: 8px;
    }

    .business-type-textarea {
      width: 100%;
      min-height: 76px;
      border: 1px solid #eadfe2;
      border-radius: 10px;
      padding: 8px 10px;
      font-size: 0.95rem;
      outline: none;
      background: #fff;
      color: #1f2937;
      resize: vertical;
    }

    .business-type-actions {
      display: flex;
      gap: 8px;
    }

    .business-type-message {
      margin: 0;
      font-size: 0.8rem;
      font-weight: 700;
      min-height: 1.2em;
    }

    .admin-user-tools {
      margin-top: 8px;
      display: grid;
      gap: 6px;
    }

    .admin-user-note {
      margin: 0;
      font-size: 0.82rem;
      color: #475569;
    }

    .admin-user-btn {
      width: fit-content;
      border: 1px solid #d1d5db;
      border-radius: 8px;
      background: #fff;
      color: #1f2937;
      font-size: 0.82rem;
      font-weight: 700;
      padding: 6px 10px;
      cursor: pointer;
    }

    .logo-box {
      border: 1px solid #e7ecef;
      border-radius: 10px;
      min-height: 260px;
      background: #f8fbfd;
      padding: 14px;
      display: flex;
      flex-direction: column;
      justify-content: flex-start;
      align-items: center;
      text-align: center;
      gap: 14px;
    }

    .logo-preview {
      width: 146px;
      height: 146px;
      border-radius: 2px;
      border: 1px solid #e5e7eb;
      background: #ffffff;
      color: #fff;
      font-size: 4rem;
      display: grid;
      place-items: center;
      margin-top: 4px;
      overflow: hidden;
    }

    .logo-preview-wrap {
      position: relative;
      width: 146px;
      height: 182px;
      display: flex;
      align-items: flex-start;
      justify-content: center;
    }

    .logo-preview img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }

    .logo-actions {
      position: absolute;
      left: 50%;
      bottom: 0;
      transform: translateX(-50%);
      display: flex;
      gap: 8px;
      z-index: 3;
    }

    .logo-action-btn {
      width: 34px;
      height: 34px;
      border: 1px solid #d9dee3;
      border-radius: 999px;
      background: #fff;
      color: #4b5563;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 1rem;
      line-height: 1;
    }

    .logo-action-btn:hover {
      background: #f3f4f6;
    }

    .logo-input {
      display: none;
    }

    .logo-urls {
      width: 100%;
      margin-top: 6px;
      text-align: left;
      display: grid;
      gap: 10px;
    }

    .url-item {
      display: grid;
      gap: 4px;
    }

    .url-label {
      font-size: 0.86rem;
      font-weight: 700;
      color: #4b5563;
      text-transform: lowercase;
    }

    .url-value {
      font-size: 0.9rem;
      color: #2563eb;
      text-decoration: none;
      word-break: break-all;
    }

    .url-value:hover {
      text-decoration: underline;
    }

    .placeholder {
      color: #6b7280;
      font-size: 0.92rem;
      margin: 0;
    }

    .avan-grid {
      display: grid;
      gap: 14px;
      max-width: 760px;
    }

    .avan-row {
      display: grid;
      grid-template-columns: 320px 1fr;
      align-items: center;
      gap: 10px;
    }

    .avan-label {
      font-size: 1rem;
      font-weight: 700;
      color: #2f343b;
      margin: 0;
    }

    .avan-label .hint {
      color: #1f9bb8;
      font-size: 1rem;
      margin-left: 6px;
    }

    .avan-check {
      width: 28px;
      height: 28px;
      accent-color: #5b8fab;
      cursor: pointer;
    }

    .avan-input {
      width: 100%;
      height: 52px;
      border: 1px solid #eadfe2;
      border-radius: 18px;
      background: #f2e9eb;
      padding: 0 14px;
      font-size: 1.05rem;
      color: #374151;
      outline: none;
    }

    @media (max-width: 920px) {
      .section-grid {
        grid-template-columns: 1fr;
      }

      .avan-row {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
__BACKEND_SHARED_SIDEBAR_HTML__

  <main class="page">
    <h1 class="title">Agregar Nueva Tienda</h1>
    <p class="subtitle">Completa la configuración de tu tienda en tres secciones.</p>

    <section class="section">
      <h2>Datos generales</h2>
      <div class="section-grid">
        <div>
          <div class="field">
            <label for="store-name">Nombre de la tienda</label>
            <input class="field-input" id="store-name" type="text" placeholder="Ej. Tu Negocio" />
          </div>
          <div class="field">
            <label for="store-type">Giro o tipo de negocio</label>
            <select class="field-input field-select" id="store-type">
              <option value="">Selecciona un giro</option>
            </select>
            <div class="business-type-tools">
              <button class="business-type-btn" id="openBusinessTypePanelBtn" type="button">Agregar giro</button>
              <span class="business-type-description" id="storeTypeDescription"></span>
            </div>
            <div class="business-type-panel" id="businessTypePanel" hidden>
              <div class="business-type-grid">
                <input class="field-input" id="business-type-name" type="text" placeholder="Giro de negocio" />
                <input class="field-input" id="business-type-code" type="text" placeholder="Código" />
              </div>
              <textarea class="business-type-textarea" id="business-type-description" placeholder="Descripción"></textarea>
              <div class="business-type-actions">
                <button class="business-type-btn" id="saveBusinessTypeBtn" type="button">Guardar giro</button>
                <button class="business-type-btn" id="cancelBusinessTypeBtn" type="button">Cancelar</button>
              </div>
              <p class="business-type-message" id="businessTypeMessage"></p>
            </div>
          </div>
          <div class="field">
            <label for="store-admin">Administrador de la tienda</label>
            <select class="field-input field-select" id="store-admin">
              <option value="">Cargando usuarios...</option>
            </select>
            <div class="admin-user-tools">
              <p class="admin-user-note" id="storeAdminNote"></p>
              <button class="admin-user-btn" id="createAdminUserBtn" type="button" hidden>Crear nuevo vendedor</button>
            </div>
          </div>
          <div class="field">
            <label for="store-membership">Membresía</label>
            <input class="field-input" id="store-membership" type="text" placeholder="Tipo de membresía" />
          </div>
        </div>
        <div>
          <label for="store-logo">Logo de la tienda</label>
          <div class="logo-box">
            <div class="logo-preview-wrap">
              <div class="logo-preview" id="logoPreview">
                <span id="logoFallback" style="display:none;">A</span>
                <img id="logoImage" src="/static/imagenes/tu-negocio.png" alt="Preview del logo" />
              </div>
              <div class="logo-actions">
                <button type="button" class="logo-action-btn" id="editLogoBtn" title="Editar logo" aria-label="Editar logo">✎</button>
                <button type="button" class="logo-action-btn" id="deleteLogoBtn" title="Eliminar logo" aria-label="Eliminar logo">🗑</button>
              </div>
            </div>
            <input class="logo-input" id="store-logo" type="file" accept="image/*" />
            <div class="logo-urls">
              <div class="url-item">
                <span class="url-label">url de la tienda:</span>
                <a class="url-value" href="#" id="storeUrl">https://mi-tienda.ejemplo.com</a>
              </div>
              <div class="url-item">
                <span class="url-label">url de administración:</span>
                <a class="url-value" href="#" id="adminUrl">https://admin.mi-tienda.ejemplo.com</a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section class="section">
      <h2>Acceso a AVAN</h2>
      <div class="avan-grid">
        <div class="avan-row">
          <p class="avan-label">Active</p>
          <input class="avan-check" type="checkbox" checked />
        </div>
        <div class="avan-row">
          <p class="avan-label">Tienda destacada<span class="hint">?</span></p>
          <input class="avan-check" type="checkbox" checked />
        </div>
        <div class="avan-row">
          <p class="avan-label">Sistema de inventario</p>
          <input class="avan-check" type="checkbox" />
        </div>
        <div class="avan-row">
          <p class="avan-label">Vigencia<span class="hint">?</span></p>
          <input class="avan-input" type="text" />
        </div>
        <div class="avan-row">
          <p class="avan-label">Sistema de referidos</p>
          <input class="avan-input" type="text" />
        </div>
        <div class="avan-row">
          <p class="avan-label">Sistema de cita</p>
          <input class="avan-input" type="text" />
        </div>
        <div class="avan-row">
          <p class="avan-label">Sistema de cupones</p>
          <input class="avan-input" type="text" />
        </div>
        <div class="avan-row">
          <p class="avan-label">WhatsApp</p>
          <input class="avan-input" type="text" />
        </div>
      </div>
    </section>

    <section class="section">
      <h2>Sección 3</h2>
      <p class="placeholder">Pendiente por agregar.</p>
    </section>
  </main>
  <script src="/static/js/backend-sidebar-core.js"></script>
  <script>
    (function () {
      if (window.initBackendSidebarCore) {
        window.initBackendSidebarCore();
      }
    })();

    (function () {
      const STORAGE_KEY = "store_business_types_catalog";
      const defaults = [
        { name: "Restaurante", code: "REST", description: "Negocios de alimentos y bebidas." },
        { name: "Moda", code: "MODA", description: "Ropa, calzado y accesorios." },
        { name: "Ferretería", code: "FERR", description: "Herramientas y materiales para construcción." }
      ];
      const select = document.getElementById("store-type");
      const description = document.getElementById("storeTypeDescription");
      const openPanelBtn = document.getElementById("openBusinessTypePanelBtn");
      const panel = document.getElementById("businessTypePanel");
      const nameInput = document.getElementById("business-type-name");
      const codeInput = document.getElementById("business-type-code");
      const detailInput = document.getElementById("business-type-description");
      const saveBtn = document.getElementById("saveBusinessTypeBtn");
      const cancelBtn = document.getElementById("cancelBusinessTypeBtn");
      const message = document.getElementById("businessTypeMessage");
      if (!select) {
        return;
      }

      function loadCatalog() {
        try {
          const raw = localStorage.getItem(STORAGE_KEY);
          if (!raw) return defaults.slice();
          const parsed = JSON.parse(raw);
          if (!Array.isArray(parsed) || parsed.length === 0) return defaults.slice();
          return parsed;
        } catch (error) {
          return defaults.slice();
        }
      }

      function saveCatalog(catalog) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(catalog));
      }

      function clearPanelMessage() {
        if (!message) return;
        message.textContent = "";
        message.style.color = "#b91c1c";
      }

      function renderOptions(catalog, selectedCode) {
        const currentValue = selectedCode || select.value || "";
        select.innerHTML = '<option value="">Selecciona un giro</option>';
        catalog.forEach(function (item) {
          const option = document.createElement("option");
          option.value = item.code;
          option.textContent = item.name + " (" + item.code + ")";
          option.dataset.description = item.description || "";
          select.appendChild(option);
        });
        select.value = currentValue;
      }

      function updateDescription() {
        const option = select.options[select.selectedIndex];
        if (!option || !description) return;
        description.textContent = option.dataset.description || "";
      }

      function openPanel() {
        if (!panel) return;
        panel.hidden = false;
        clearPanelMessage();
      }

      function closePanel() {
        if (!panel) return;
        panel.hidden = true;
        clearPanelMessage();
        if (nameInput) nameInput.value = "";
        if (codeInput) codeInput.value = "";
        if (detailInput) detailInput.value = "";
      }

      let catalog = loadCatalog();
      renderOptions(catalog);
      updateDescription();

      select.addEventListener("change", updateDescription);

      if (openPanelBtn) {
        openPanelBtn.addEventListener("click", openPanel);
      }
      if (cancelBtn) {
        cancelBtn.addEventListener("click", closePanel);
      }

      if (saveBtn) {
        saveBtn.addEventListener("click", function () {
          const name = (nameInput && nameInput.value || "").trim();
          const code = (codeInput && codeInput.value || "").trim().toUpperCase();
          const detail = (detailInput && detailInput.value || "").trim();
          if (!name || !code || !detail) {
            if (message) {
              message.textContent = "Completa Giro de negocio, Código y Descripción.";
            }
            return;
          }
          const exists = catalog.some(function (item) {
            return item.code.toUpperCase() === code || item.name.toLowerCase() === name.toLowerCase();
          });
          if (exists) {
            if (message) {
              message.textContent = "Ese giro o código ya existe.";
            }
            return;
          }
          catalog = catalog.concat([{ name: name, code: code, description: detail }]);
          saveCatalog(catalog);
          renderOptions(catalog, code);
          updateDescription();
          if (message) {
            message.style.color = "#166534";
            message.textContent = "Giro agregado correctamente.";
          }
          setTimeout(closePanel, 600);
        });
      }
    })();

    (function () {
      const adminSelect = document.getElementById("store-admin");
      const adminNote = document.getElementById("storeAdminNote");
      const createUserBtn = document.getElementById("createAdminUserBtn");
      if (!adminSelect) {
        return;
      }

      async function loadUsers() {
        try {
          const response = await fetch("__USERS_PATH__", { headers: { "Accept": "application/json" } });
          if (!response.ok) {
            throw new Error("No se pudieron cargar usuarios");
          }
          const users = await response.json();
          adminSelect.innerHTML = "";

          const placeholder = document.createElement("option");
          placeholder.value = "";
          placeholder.textContent = "Selecciona un usuario";
          adminSelect.appendChild(placeholder);

          if (!Array.isArray(users) || users.length === 0) {
            const emptyOption = document.createElement("option");
            emptyOption.value = "";
            emptyOption.textContent = "Sin usuarios registrados";
            adminSelect.appendChild(emptyOption);
            if (adminNote) {
              adminNote.textContent = "No existen usuarios del sistema para asignar.";
            }
            if (createUserBtn) {
              createUserBtn.hidden = false;
            }
            return;
          }

          users.forEach(function (user) {
            const option = document.createElement("option");
            option.value = String(user.id || "");
            option.textContent = (user.username || "Usuario") + " (" + (user.user_type || "sistema") + ")";
            adminSelect.appendChild(option);
          });

          if (adminNote) {
            adminNote.textContent = "El administrador debe ser un usuario del sistema.";
          }
          if (createUserBtn) {
            createUserBtn.hidden = true;
          }
        } catch (error) {
          adminSelect.innerHTML = '<option value="">No disponible</option>';
          if (adminNote) {
            adminNote.textContent = "No se pudo cargar el listado. Intenta nuevamente.";
          }
          if (createUserBtn) {
            createUserBtn.hidden = false;
          }
        }
      }

      if (createUserBtn) {
        createUserBtn.addEventListener("click", function () {
          window.location.href = "__ADD_USER_PATH__";
        });
      }

      loadUsers();
    })();

    (function () {
      const input = document.getElementById("store-logo");
      const image = document.getElementById("logoImage");
      const fallback = document.getElementById("logoFallback");
      const editButton = document.getElementById("editLogoBtn");
      const deleteButton = document.getElementById("deleteLogoBtn");
      const defaultLogo = "/static/imagenes/tu-negocio.png";

      function resetLogo() {
        input.value = "";
        image.src = defaultLogo;
        image.style.display = "block";
        fallback.style.display = "none";
      }

      input.addEventListener("change", function (event) {
        const file = event.target.files && event.target.files[0];
        if (!file) {
          resetLogo();
          return;
        }
        const url = URL.createObjectURL(file);
        image.src = url;
        image.style.display = "block";
        fallback.style.display = "none";
      });

      editButton.addEventListener("click", function () {
        input.click();
      });

      deleteButton.addEventListener("click", function () {
        resetLogo();
      });
    })();
  </script>
  <script src="/static/js/sidebar-theme-editor.js"></script>
  <script src="/static/js/backend-navbar.js"></script>
</body>
</html>
"""
    return render_backend_view_html(
        html=html,
        blank_path=blank_path,
        add_user_path=add_user_path,
        config_path=config_path,
        template_path=template_path,
        template_frontend_path=template_frontend_path,
        extra_replacements={"__USERS_PATH__": users_path},
    )


@app.get(f"{BACKEND_ROUTE_PREFIX}/agregar-usuario", response_class=HTMLResponse)
def add_user_view():
    blank_path = f"{BACKEND_ROUTE_PREFIX}/gestion" if BACKEND_ROUTE_PREFIX else "/gestion"
    add_user_path = f"{BACKEND_ROUTE_PREFIX}/agregar-usuario" if BACKEND_ROUTE_PREFIX else "/agregar-usuario"
    config_path = f"{BACKEND_ROUTE_PREFIX}/configuracion" if BACKEND_ROUTE_PREFIX else "/configuracion"
    template_path = f"{BACKEND_ROUTE_PREFIX}/template" if BACKEND_ROUTE_PREFIX else "/template"
    template_frontend_path = (
        f"{BACKEND_ROUTE_PREFIX}/template-frontend" if BACKEND_ROUTE_PREFIX else "/template-frontend"
    )
    vendors_path = f"{BACKEND_ROUTE_PREFIX}/vendors/" if BACKEND_ROUTE_PREFIX else "/vendors/"
    html = """
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="icon" type="image/png" href="/static/imagenes/tu-negocio.png" />
  <title>Agregar Vendedor</title>
  <style>
    html, body {
      margin: 0;
      padding: 0;
      background: #f5f6f8;
      font-family: Arial, sans-serif;
      color: #1f2937;
    }

    * {
      box-sizing: border-box;
    }

__BACKEND_SHARED_SIDEBAR_CSS__

__BACKEND_SHARED_FORM_BASE_CSS__

    .photo-box {
      border: 1px solid #e7ecef;
      border-radius: 10px;
      min-height: 320px;
      background: #f8fbfd;
      padding: 14px;
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      gap: 14px;
    }

    .photo-preview {
      width: 146px;
      height: 146px;
      border-radius: 2px;
      border: 1px solid #e5e7eb;
      background: #ffffff;
      color: #fff;
      font-size: 4rem;
      display: grid;
      place-items: center;
      margin-top: 4px;
      overflow: hidden;
    }

    .photo-preview-wrap {
      position: relative;
      width: 146px;
      height: 182px;
      display: flex;
      align-items: flex-start;
      justify-content: center;
    }

    .photo-preview img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }

    .photo-actions {
      position: absolute;
      left: 50%;
      bottom: 0;
      transform: translateX(-50%);
      display: flex;
      gap: 8px;
      z-index: 3;
    }

    .photo-action-btn {
      width: 34px;
      height: 34px;
      border: 1px solid #d9dee3;
      border-radius: 999px;
      background: #fff;
      color: #4b5563;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 1rem;
      line-height: 1;
    }

    .photo-action-btn:hover {
      background: #f3f4f6;
    }

    .photo-input {
      display: none;
    }

    .right-field {
      width: 100%;
      text-align: left;
      margin-top: 8px;
    }

    .role-help {
      margin: 8px 0 0;
      padding-left: 18px;
      color: #4b5563;
      font-size: 0.9rem;
      line-height: 1.4;
    }

    .user-check-row {
      display: flex;
      align-items: center;
      gap: 10px;
      min-height: 50px;
    }

    .user-check {
      width: 20px;
      height: 20px;
      accent-color: #5b8fab;
      cursor: pointer;
    }

    @media (max-width: 920px) {
      .section-grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
__BACKEND_SHARED_SIDEBAR_HTML__

  <main class="page">
    <h1 class="title">Agregar Vendedor</h1>
    <p class="subtitle">Completa la información del usuario.</p>

    <section class="section">
      <h2>Sección 1: Datos generales</h2>
      <div class="section-grid">
        <div>
          <div class="field">
            <label for="user-name">Nombre</label>
            <input class="field-input" id="user-name" type="text" placeholder="Nombre completo" />
          </div>
          <div class="field">
            <label for="user-email">Correo electrónico</label>
            <input class="field-input" id="user-email" type="email" placeholder="correo@ejemplo.com" />
          </div>
          <div class="field">
            <label for="user-store">Tienda</label>
            <select class="field-input field-select" id="user-store">
              <option value="">Cargando tiendas...</option>
            </select>
          </div>
          <div class="field">
            <label for="user-username">usuario</label>
            <input class="field-input" id="user-username" type="text" placeholder="Nombre de usuario" />
          </div>
          <div class="field">
            <label for="user-password">Contraseña</label>
            <input class="field-input" id="user-password" type="password" placeholder="********" />
          </div>
          <div class="field">
            <label for="user-two-factor">Habilitar identificación por dos factores</label>
            <div class="user-check-row">
              <input class="user-check" id="user-two-factor" type="checkbox" />
            </div>
          </div>
        </div>
        <div>
          <label for="user-photo">foto</label>
          <div class="photo-box">
            <div class="photo-preview-wrap">
              <div class="photo-preview" id="photoPreview">
                <img id="photoImage" src="/static/imagenes/tu-negocio.png" alt="Preview de foto" />
              </div>
              <div class="photo-actions">
                <button type="button" class="photo-action-btn" id="editPhotoBtn" title="Editar foto" aria-label="Editar foto">✎</button>
                <button type="button" class="photo-action-btn" id="deletePhotoBtn" title="Eliminar foto" aria-label="Eliminar foto">🗑</button>
              </div>
            </div>
            <input class="photo-input" id="user-photo" type="file" accept="image/*" />
            <div class="right-field">
              <label for="user-phone">celular</label>
              <input class="field-input" id="user-phone" type="tel" placeholder="Ej. 555 123 4567" />
            </div>
            <div class="right-field">
              <label for="user-role">rol</label>
              <select class="field-input field-select" id="user-role">
                <option value="">Selecciona un rol</option>
                <option value="superadministrador">Superadministrador</option>
                <option value="administrador_tienda">Administrador de tienda</option>
                <option value="vendededor">Vendededor</option>
                <option value="auditor">Auditor</option>
              </select>
              <ul class="role-help">
                <li>Superadministrador = acceso total</li>
                <li>Administrador de tienda = solo podra ver su tienda</li>
                <li>Vendededor = solo podra ver productos</li>
                <li>Auditor</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  </main>

  <script src="/static/js/backend-sidebar-core.js"></script>
  <script>
    (function () {
      if (window.initBackendSidebarCore) {
        window.initBackendSidebarCore();
      }
    })();

    (function () {
      const input = document.getElementById("user-photo");
      const image = document.getElementById("photoImage");
      const editButton = document.getElementById("editPhotoBtn");
      const deleteButton = document.getElementById("deletePhotoBtn");
      const defaultImage = "/static/imagenes/tu-negocio.png";
      if (!input || !image || !editButton || !deleteButton) {
        return;
      }

      function resetPhoto() {
        input.value = "";
        image.src = defaultImage;
      }

      input.addEventListener("change", function (event) {
        const file = event.target.files && event.target.files[0];
        if (!file) {
          resetPhoto();
          return;
        }
        const url = URL.createObjectURL(file);
        image.src = url;
      });

      editButton.addEventListener("click", function () {
        input.click();
      });

      deleteButton.addEventListener("click", function () {
        resetPhoto();
      });
    })();

    (function () {
      const storeSelect = document.getElementById("user-store");
      if (!storeSelect) {
        return;
      }

      async function loadStores() {
        try {
          const response = await fetch("__VENDORS_PATH__", { headers: { "Accept": "application/json" } });
          if (!response.ok) {
            throw new Error("No se pudieron cargar tiendas");
          }
          const stores = await response.json();
          storeSelect.innerHTML = "";

          const placeholder = document.createElement("option");
          placeholder.value = "";
          placeholder.textContent = "Selecciona una tienda";
          storeSelect.appendChild(placeholder);

          if (!Array.isArray(stores) || stores.length === 0) {
            const emptyOption = document.createElement("option");
            emptyOption.value = "";
            emptyOption.textContent = "Sin tiendas registradas";
            storeSelect.appendChild(emptyOption);
            return;
          }

          stores.forEach(function (store) {
            const option = document.createElement("option");
            const storeId = (store && store.id !== null && store.id !== undefined) ? store.id : "";
            option.value = String(storeId);
            option.textContent = store.store_name || ("Tienda #" + String(storeId));
            storeSelect.appendChild(option);
          });
        } catch (error) {
          storeSelect.innerHTML = "<option value=\"\">No disponible</option>";
        }
      }

      loadStores();
    })();
  </script>
  <script src="/static/js/sidebar-theme-editor.js"></script>
  <script src="/static/js/backend-navbar.js"></script>
</body>
</html>
"""
    return render_backend_view_html(
        html=html,
        blank_path=blank_path,
        add_user_path=add_user_path,
        config_path=config_path,
        template_path=template_path,
        template_frontend_path=template_frontend_path,
        extra_replacements={"__VENDORS_PATH__": vendors_path},
    )


app.include_router(users_router, prefix=f"{BACKEND_ROUTE_PREFIX}/users", tags=["users"])
app.include_router(vendors_router, prefix=f"{BACKEND_ROUTE_PREFIX}/vendors", tags=["vendors"])
app.include_router(products_router, prefix=f"{BACKEND_ROUTE_PREFIX}/products", tags=["products"])
app.include_router(orders_router, prefix=f"{BACKEND_ROUTE_PREFIX}/orders", tags=["orders"])
app.include_router(payments_router, prefix=f"{BACKEND_ROUTE_PREFIX}/payments", tags=["payments"])

# Routers opcionales: si estos modulos tienen imports incompletos,
# el backend principal igual puede iniciar.
try:
    from apps.reviews.api import router as reviews_api_router
    app.include_router(reviews_api_router, prefix=BACKEND_ROUTE_PREFIX)
except Exception as exc:
    print(f"[startup] reviews router disabled: {exc}")

try:
    from apps.analytics.api import router as analytics_router
    app.include_router(analytics_router, prefix=BACKEND_ROUTE_PREFIX)
except Exception as exc:
    print(f"[startup] analytics router disabled: {exc}")
