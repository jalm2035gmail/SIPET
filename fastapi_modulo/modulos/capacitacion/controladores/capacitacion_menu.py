from __future__ import annotations

MENU_ITEMS = [
    {"key": "catalogo", "label": "Catalogo", "href": "/capacitacion"},
    {"key": "dashboard", "label": "Dashboard", "href": "/capacitacion/dashboard"},
    {"key": "progreso", "label": "Mi progreso", "href": "/capacitacion/mi-progreso"},
    {"key": "gamificacion", "label": "Gamificacion", "href": "/capacitacion/gamificacion"},
    {"key": "presentaciones", "label": "Presentaciones", "href": "/capacitacion/presentaciones"},
    {"key": "certificados", "label": "Certificados", "href": "/capacitacion/mis-certificados"},
]


def build_menu_html(active_key: str | None = None) -> str:
    links = []
    for item in MENU_ITEMS:
        cls = "cap-module-menu-link is-active" if item["key"] == active_key else "cap-module-menu-link"
        links.append(f'<a class="{cls}" href="{item["href"]}">{item["label"]}</a>')
    return """
<style>
  .cap-module-menu {
    display:flex;
    align-items:center;
    gap:10px;
    flex-wrap:wrap;
    padding:0 0 18px;
    margin:0 0 18px;
    border-bottom:1px solid rgba(15,23,42,.08);
  }
  .cap-module-menu-link {
    display:inline-flex;
    align-items:center;
    justify-content:center;
    padding:9px 14px;
    border-radius:999px;
    border:1px solid rgba(15,23,42,.1);
    background:#fff;
    color:#17314f;
    text-decoration:none;
    font-size:13px;
    font-weight:700;
  }
  .cap-module-menu-link.is-active {
    background:#17314f;
    color:#fff;
    border-color:#17314f;
  }
</style>
<nav class="cap-module-menu" aria-label="Menu del modulo">
""" + "".join(links) + """
</nav>
"""


__all__ = ["MENU_ITEMS", "build_menu_html"]
