from pathlib import Path
import os

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from dotenv import load_dotenv

from app.api.scoring import router as scoring_router

app = FastAPI(title="Intellicoop ML Service", version="0.1.0")

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
TEMPLATES_DIR = APP_DIR / "templates"
SERVICE_ROOT = APP_DIR.parent.parent

load_dotenv(SERVICE_ROOT / ".env")
load_dotenv(SERVICE_ROOT.parent / ".env")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

DJANGO_BASE_URL = os.getenv("DJANGO_BASE_URL", "http://localhost:8010").rstrip("/")
FASTAPI_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://localhost:8001").rstrip("/")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:3010").rstrip("/")


def template_nav_context(is_config_shell: bool = False) -> dict[str, object]:
    template_path = f"{FASTAPI_BASE_URL}/admin/template-backend"
    return {
        "title": "Template Backend",
        "page_heading": "Intellicoop Admin",
        "page_subtitle": "Template backend importado y enlazado con backend/frontend.",
        "blank_path": f"{DJANGO_BASE_URL}/admin/",
        "add_user_path": f"{DJANGO_BASE_URL}/admin/auth/user/",
        "config_path": f"{template_path}/config",
        "template_path": template_path,
        "template_frontend_path": f"{FRONTEND_BASE_URL}/web",
        "is_config_shell": is_config_shell,
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "fastapi"}


@app.get("/admin/template-backend", response_class=HTMLResponse)
def admin_template_backend(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="backend_template.html",
        context=template_nav_context(is_config_shell=False),
    )


@app.get("/admin/template-backend/config", response_class=HTMLResponse)
def admin_template_backend_config(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="backend_template.html",
        context=template_nav_context(is_config_shell=True),
    )


app.include_router(scoring_router, prefix="/api/ml", tags=["ml"])
