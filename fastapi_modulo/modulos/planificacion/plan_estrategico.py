from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from fastapi_modulo.modulos.planificacion import plan_estrategico_service as strategic_api

router = APIRouter()

_PLAN_ESTRATEGICO_TEMPLATE_PATH = Path(__file__).with_name("plan_estrategico.html")
_PLAN_ESTRATEGICO_JS_PATH = Path(__file__).with_name("plan_estrategico.js")
_PLAN_ESTRATEGICO_CSS_PATH = Path(__file__).with_name("plan_estrategico.css")


@router.get("/planes", response_class=HTMLResponse)
@router.get("/plan-estrategico", response_class=HTMLResponse)
@router.get("/ejes-estrategicos", response_class=HTMLResponse)
def ejes_estrategicos_page(request: Request):
    from fastapi_modulo.main import render_backend_page

    try:
        base_content = _PLAN_ESTRATEGICO_TEMPLATE_PATH.read_text(encoding="utf-8")
    except OSError:
        base_content = "<p>No se pudo cargar la vista del plan estratégico.</p>"
    return render_backend_page(
        request,
        title="Plan estratégico",
        description="Edición y administración del plan estratégico de la institución",
        content=base_content,
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/modulos/planificacion/plan_estrategico.js")
def plan_estrategico_js():
    return FileResponse(_PLAN_ESTRATEGICO_JS_PATH, media_type="application/javascript")


@router.get("/modulos/planificacion/plan_estrategico.css")
def plan_estrategico_css():
    return FileResponse(_PLAN_ESTRATEGICO_CSS_PATH, media_type="text/css")


@router.get("/ejes-estrategicos/editor", response_class=HTMLResponse)
def ejes_estrategicos_editor_page(request: Request):
    query = str(request.url.query or "").strip()
    target = "/ejes-estrategicos"
    if query:
        target = f"{target}?{query}"
    return RedirectResponse(url=target, status_code=302)


router.add_api_route(
    "/api/planificacion/plantilla-plan-poa.csv",
    strategic_api.download_strategic_poa_template,
    methods=["GET"],
)
router.add_api_route(
    "/api/planificacion/exportar-plan-poa.xlsx",
    strategic_api.export_strategic_poa_xlsx,
    methods=["GET"],
)
router.add_api_route(
    "/api/planificacion/importar-plan-poa",
    strategic_api.import_strategic_poa_csv,
    methods=["POST"],
)
router.add_api_route(
    "/api/strategic-foundation",
    strategic_api.get_strategic_foundation,
    methods=["GET"],
)
router.add_api_route(
    "/api/strategic-foundation",
    strategic_api.save_strategic_foundation,
    methods=["PUT"],
)
router.add_api_route(
    "/api/strategic-plan/export-doc",
    strategic_api.export_strategic_plan_doc,
    methods=["GET"],
)
router.add_api_route(
    "/api/strategic-identity",
    strategic_api.get_strategic_identity,
    methods=["GET"],
)
router.add_api_route(
    "/api/strategic-identity/{bloque}",
    strategic_api.save_strategic_identity_block,
    methods=["PUT"],
)
router.add_api_route(
    "/api/strategic-identity/{bloque}",
    strategic_api.clear_strategic_identity_block,
    methods=["DELETE"],
)
router.add_api_route(
    "/api/strategic-axes",
    strategic_api.list_strategic_axes,
    methods=["GET"],
)
router.add_api_route(
    "/api/strategic-axes/departments",
    strategic_api.list_strategic_axis_departments,
    methods=["GET"],
)
router.add_api_route(
    "/api/strategic-axes/collaborators-by-department",
    strategic_api.list_collaborators_by_department,
    methods=["GET"],
)
router.add_api_route(
    "/api/strategic-axes/{axis_id}/collaborators",
    strategic_api.list_strategic_axis_collaborators,
    methods=["GET"],
)
router.add_api_route(
    "/api/strategic-axes",
    strategic_api.create_strategic_axis,
    methods=["POST"],
)
router.add_api_route(
    "/api/strategic-axes/{axis_id}",
    strategic_api.update_strategic_axis,
    methods=["PUT"],
)
router.add_api_route(
    "/api/strategic-axes/{axis_id}",
    strategic_api.delete_strategic_axis,
    methods=["DELETE"],
)
router.add_api_route(
    "/api/strategic-axes/{axis_id}/objectives",
    strategic_api.create_strategic_objective,
    methods=["POST"],
)
router.add_api_route(
    "/api/strategic-objectives/{objective_id}",
    strategic_api.update_strategic_objective,
    methods=["PUT"],
)
router.add_api_route(
    "/api/strategic-objectives/{objective_id}",
    strategic_api.delete_strategic_objective,
    methods=["DELETE"],
)
