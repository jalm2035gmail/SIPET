"""
Cascarón de template base para backend.
Incluye Sidebar (hamburguesa) y Navbar para navegación.
"""

from fastapi.templating import Jinja2Templates
from fastapi import Request

TEMPLATES_PATH = "strategic_planning/backend/app/templates"
templates = Jinja2Templates(directory=TEMPLATES_PATH)

def render_base(request: Request, title: str = "", content: str = ""):
    return templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "title": title,
            "content": content
        }
    )
