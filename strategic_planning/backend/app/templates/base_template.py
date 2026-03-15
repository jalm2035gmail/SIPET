"""
Cascarón de template MAIN para backend.
Incluye Sidebar (hamburguesa) y Navbar para navegación.
"""

from fastapi.templating import Jinja2Templates
from fastapi import Request

TEMPLATES_PATH = "strategic_planning/backend/app/templates"
templates = Jinja2Templates(directory=TEMPLATES_PATH)

def render_MAIN(request: Request, title: str = "", content: str = ""):
    return templates.TemplateResponse(
        "MAIN.html",
        {
            "request": request,
            "title": title,
            "content": content
        }
    )
