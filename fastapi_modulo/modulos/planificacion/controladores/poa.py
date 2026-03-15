from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from fastapi_modulo.modulos.planificacion.modelos import poa_service


router = APIRouter()
_CORE_BOUND = False

MODULE_DIR = Path(__file__).resolve().parent.parent
_POA_TEMPLATE_PATH = MODULE_DIR / "vistas" / "poa.html"
_POA_JS_PATH = MODULE_DIR / "static" / "js" / "poa.js"
_POA_CSS_PATH = MODULE_DIR / "static" / "css" / "poa.css"
_POA_TREE_TEMPLATE_PATH = MODULE_DIR / "vistas" / "poa_tree.html"
_POA_GANTT_TEMPLATE_PATH = MODULE_DIR / "vistas" / "poa_gantt.html"
_POA_CAL_TEMPLATE_PATH = MODULE_DIR / "vistas" / "poa_cal.html"


def _bind_core_symbols() -> None:
    global _CORE_BOUND
    if _CORE_BOUND:
        return
    from fastapi_modulo import main as core

    globals()["_render_no_access_module_page"] = getattr(core, "_render_no_access_module_page", None)
    globals()["_has_strategy_submenu_access"] = getattr(core, "_has_strategy_submenu_access", None)
    _CORE_BOUND = True


def _render_poa_page(
    request: Request,
    *,
    title: str,
    description: str,
    template_path: Path,
    fallback: str,
) -> HTMLResponse:
    from fastapi_modulo.main import render_backend_page

    try:
        MAIN_content = template_path.read_text(encoding="utf-8")
    except OSError:
        MAIN_content = fallback
    return render_backend_page(
        request,
        title=title,
        description=description,
        content=MAIN_content,
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/poa", response_class=HTMLResponse)
@router.get("/poa/crear", response_class=HTMLResponse)
def poa_page(request: Request):
    _bind_core_symbols()
    if callable(globals().get("_has_strategy_submenu_access")) and not _has_strategy_submenu_access(request, "POA"):
        return _render_no_access_module_page(
            request,
            title="POA",
            description="Acceso restringido al programa operativo anual.",
        )
    return _render_poa_page(
        request,
        title="POA",
        description="Pantalla de trabajo POA.",
        template_path=_POA_TEMPLATE_PATH,
        fallback="<p>No se pudo cargar la vista de POA.</p>",
    )


@router.get("/modulos/planificacion/poa.js")
def poa_js():
    return FileResponse(_POA_JS_PATH, media_type="application/javascript")


@router.get("/modulos/planificacion/poa.css")
def poa_css():
    return FileResponse(_POA_CSS_PATH, media_type="text/css")


@router.get("/poa/actividades", response_class=HTMLResponse)
def poa_activities_page(request: Request):
    _bind_core_symbols()
    if callable(globals().get("_has_strategy_submenu_access")) and not _has_strategy_submenu_access(request, "POA"):
        return _render_no_access_module_page(
            request,
            title="POA",
            description="Acceso restringido al programa operativo anual.",
        )
    query = str(request.url.query or "").strip()
    target = "/poa"
    if query:
        target = f"{target}?{query}"
    return RedirectResponse(url=target, status_code=302)


@router.get("/poa/arbol", response_class=HTMLResponse)
def poa_tree_page(request: Request):
    _bind_core_symbols()
    if callable(globals().get("_has_strategy_submenu_access")) and not _has_strategy_submenu_access(request, "POA"):
        return _render_no_access_module_page(
            request,
            title="Árbol POA",
            description="Acceso restringido al árbol de avance POA.",
        )
    return _render_poa_page(
        request,
        title="Árbol POA",
        description="Vista separada del árbol de avance POA.",
        template_path=_POA_TREE_TEMPLATE_PATH,
        fallback="<p>No se pudo cargar la vista del árbol POA.</p>",
    )


@router.get("/poa/gantt", response_class=HTMLResponse)
def poa_gantt_page(request: Request):
    _bind_core_symbols()
    if callable(globals().get("_has_strategy_submenu_access")) and not _has_strategy_submenu_access(request, "POA"):
        return _render_no_access_module_page(
            request,
            title="Gantt POA",
            description="Acceso restringido al cronograma Gantt POA.",
        )
    return _render_poa_page(
        request,
        title="Gantt POA",
        description="Vista separada del cronograma Gantt POA.",
        template_path=_POA_GANTT_TEMPLATE_PATH,
        fallback="<p>No se pudo cargar la vista Gantt POA.</p>",
    )


@router.get("/poa/calendario", response_class=HTMLResponse)
def poa_calendar_page(request: Request):
    _bind_core_symbols()
    if callable(globals().get("_has_strategy_submenu_access")) and not _has_strategy_submenu_access(request, "POA"):
        return _render_no_access_module_page(
            request,
            title="Calendario POA",
            description="Acceso restringido al calendario POA.",
        )
    return _render_poa_page(
        request,
        title="Calendario POA",
        description="Vista separada del calendario POA.",
        template_path=_POA_CAL_TEMPLATE_PATH,
        fallback="<p>No se pudo cargar la vista del calendario POA.</p>",
    )


router.add_api_route(
    "/api/poa/board-data",
    poa_service.poa_board_data,
    methods=["GET"],
)
router.add_api_route(
    "/api/poa/activities/no-owner",
    poa_service.poa_activities_without_owner,
    methods=["GET"],
)
router.add_api_route(
    "/api/poa/activities",
    poa_service.create_poa_activity,
    methods=["POST"],
)
router.add_api_route(
    "/api/poa/activities/{activity_id}",
    poa_service.update_poa_activity,
    methods=["PUT"],
)
router.add_api_route(
    "/api/poa/activities/{activity_id}",
    poa_service.delete_poa_activity,
    methods=["DELETE"],
)
router.add_api_route(
    "/api/poa/activities/{activity_id}/mark-in-progress",
    poa_service.mark_poa_activity_in_progress,
    methods=["POST"],
)
router.add_api_route(
    "/api/poa/activities/{activity_id}/mark-finished",
    poa_service.mark_poa_activity_finished,
    methods=["POST"],
)
router.add_api_route(
    "/api/poa/activities/{activity_id}/request-completion",
    poa_service.request_poa_activity_completion,
    methods=["POST"],
)
router.add_api_route(
    "/api/poa/approvals/{approval_id}/decision",
    poa_service.decide_poa_deliverable_approval,
    methods=["POST"],
)
router.add_api_route(
    "/api/poa/activities/{activity_id}/subactivities",
    poa_service.create_poa_subactivity,
    methods=["POST"],
)
router.add_api_route(
    "/api/poa/subactivities/{subactivity_id}",
    poa_service.update_poa_subactivity,
    methods=["PUT"],
)
router.add_api_route(
    "/api/poa/subactivities/{subactivity_id}",
    poa_service.delete_poa_subactivity,
    methods=["DELETE"],
)
router.add_api_route(
    "/api/poa/subactivities/no-owner",
    poa_service.poa_subactivities_without_owner,
    methods=["GET"],
)
