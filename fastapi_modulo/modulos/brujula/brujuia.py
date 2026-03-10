import os

from fastapi import APIRouter, Body, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import text
from fastapi_modulo.modulos.planificacion import kpis_service

router = APIRouter()

BRUJULA_TEMPLATE_PATH = os.path.join(
    "fastapi_modulo", "modulos", "brujula", "brujula.html"
)
BRUJULA_INDICADORES_TEMPLATE_PATH = os.path.join(
    "fastapi_modulo", "modulos", "brujula", "brujula_indicadores.html"
)

BRUJULA_SECTIONS = {
    "dashboard": "Dashboard Ejecutivo",
    "solidez-financiera": "Solidez Financiera",
    "liquidez": "Liquidez",
    "rentabilidad": "Rentabilidad",
    "crecimiento": "Crecimiento",
    "liderazgo": "Liderazgo",
    "productividad": "Productividad",
    "balance-social": "Balance Social",
    "reportes": "Reportes",
    "configuracion": "Configuración",
    "indicadores": "Indicadores",
}

_CORE_BOUND = False


def _load_brujula_template(section_title: str, section_description: str) -> str:
    try:
        with open(BRUJULA_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            template = fh.read()
    except OSError:
        return (
            "<section>"
            f"<h2>{section_title}</h2>"
            f"<p>{section_description}</p>"
            "</section>"
        )
    return (
        template.replace("{{ BRUJULA_SECTION_TITLE }}", section_title)
        .replace("{{ BRUJULA_SECTION_DESCRIPTION }}", section_description)
    )



def _bind_core_symbols() -> None:
    global _CORE_BOUND
    if _CORE_BOUND:
        return
    from fastapi_modulo import main as core

    names = ["SessionLocal"]
    for name in names:
        globals()[name] = getattr(core, name)
    _CORE_BOUND = True


def _load_indicadores_template() -> str:
    try:
        with open(BRUJULA_INDICADORES_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return "<p>No se pudo cargar la vista de indicadores.</p>"


def _ensure_brujula_indicator_table(db) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS brujula_indicator_values (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                indicador VARCHAR(255) NOT NULL DEFAULT '',
                valores_json TEXT NOT NULL DEFAULT '{}',
                orden INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    )
    try:
        db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ux_brujula_indicator_values_indicador ON brujula_indicator_values(indicador)"))
    except Exception:
        pass


def _periods_from_projection_config():
    from fastapi_modulo.modulos.proyectando.data_store import load_datos_preliminares_store

    store = load_datos_preliminares_store()
    current_year = 2026
    try:
        base_year = int(str(store.get("primer_anio_proyeccion") or "").strip() or current_year)
    except Exception:
        base_year = current_year
    try:
        projection_years = int(str(store.get("anios_proyeccion") or "").strip() or 3)
    except Exception:
        projection_years = 3
    if projection_years <= 0:
        projection_years = 3
    periods = []
    for offset in (-3, -2, -1):
        year = base_year + offset
        periods.append({"key": str(year), "label": str(year), "kind": "historico"})
    for idx in range(projection_years):
        year = base_year + idx
        periods.append({"key": str(year), "label": str(year), "kind": "proyectado"})
    return periods


def _load_kpi_indicator_names(db):
    from fastapi_modulo.modulos.planificacion.plan_estrategico_service import _ensure_axis_kpi_table

    _ensure_axis_kpi_table(db)
    db.commit()
    rows = db.execute(
        text(
            """
            SELECT nombre
            FROM strategic_axis_kpis
            WHERE TRIM(COALESCE(nombre, '')) <> ''
            ORDER BY orden ASC, id ASC
            """
        )
    ).fetchall()
    names = []
    seen = set()
    for row in rows:
        name = str(row[0] or "").strip()
        key = name.lower()
        if not name or key in seen:
            continue
        seen.add(key)
        names.append(name)
    return names


def _normalize_indicator_matrix_rows(raw_rows, periods):
    rows = raw_rows if isinstance(raw_rows, list) else []
    valid_period_keys = {str(period.get("key") or "").strip() for period in periods}
    clean = []
    seen = set()
    for idx, item in enumerate(rows, start=1):
        if not isinstance(item, dict):
            continue
        indicador = str(item.get("indicador") or "").strip()
        if not indicador:
            continue
        key = indicador.lower()
        if key in seen:
            continue
        seen.add(key)
        raw_values = item.get("values") if isinstance(item.get("values"), dict) else {}
        values = {}
        for period_key in valid_period_keys:
            values[period_key] = str(raw_values.get(period_key) or "").strip()
        clean.append({"indicador": indicador, "values": values, "orden": idx})
    return clean


def get_brujula_indicator_notebook():
    _bind_core_symbols()
    db = SessionLocal()
    try:
        periods = _periods_from_projection_config()
        _ensure_brujula_indicator_table(db)
        db.commit()
        rows = db.execute(
            text(
                """
                SELECT indicador, valores_json, orden
                FROM brujula_indicator_values
                ORDER BY orden ASC, id ASC
                """
            )
        ).fetchall()
        stored = []
        seen = set()
        for row in rows:
            indicador = str(row[0] or "").strip()
            if not indicador:
                continue
            try:
                values = __import__("json").loads(str(row[1] or "{}"))
            except Exception:
                values = {}
            key = indicador.lower()
            if key in seen:
                continue
            seen.add(key)
            stored.append({"indicador": indicador, "values": values, "orden": int(row[2] or 0)})
        stored = _normalize_indicator_matrix_rows(stored, periods)
        existing = {str(item["indicador"]).strip().lower() for item in stored}
        for name in _load_kpi_indicator_names(db):
            if name.lower() in existing:
                continue
            stored.append(
                {
                    "indicador": name,
                    "values": {str(period["key"]): "" for period in periods},
                    "orden": len(stored) + 1,
                }
            )
        return JSONResponse({"success": True, "data": {"periods": periods, "rows": stored}})
    finally:
        db.close()


def save_brujula_indicator_notebook(data: dict = Body(...)):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        periods = _periods_from_projection_config()
        rows = _normalize_indicator_matrix_rows((data or {}).get("rows"), periods)
        _ensure_brujula_indicator_table(db)
        db.execute(text("DELETE FROM brujula_indicator_values"))
        json = __import__("json")
        for row in rows:
            db.execute(
                text(
                    """
                    INSERT INTO brujula_indicator_values (indicador, valores_json, orden, updated_at)
                    VALUES (:indicador, :valores_json, :orden, CURRENT_TIMESTAMP)
                    """
                ),
                {
                    "indicador": row["indicador"],
                    "valores_json": json.dumps(row["values"], ensure_ascii=False),
                    "orden": int(row["orden"]),
                },
            )
        db.commit()
        return JSONResponse({"success": True, "data": {"rows": rows}})
    except Exception as exc:
        db.rollback()
        return JSONResponse({"success": False, "error": str(exc)}, status_code=500)
    finally:
        db.close()


def _build_section_description(section_title: str) -> str:
    if section_title == "Dashboard Ejecutivo":
        return (
            "Visualiza en tiempo real la solidez financiera, la liquidez, la "
            "rentabilidad, el crecimiento y el balance social de la institución."
        )
    return (
        f"Visualiza el comportamiento de {section_title.lower()} dentro del tablero "
        "ejecutivo de BRUJULA."
    )


def _render_brujula_page(
    request: Request,
    page_title: str,
    section_title: str,
    section_key: str,
):
    from fastapi_modulo.main import render_backend_page

    description = _build_section_description(section_title)
    return render_backend_page(
        request,
        title=page_title,
        description=description,
        content=_load_brujula_template(section_title, description).replace(
            "{{ BRUJULA_SECTION_KEY }}", section_key
        ),
        hide_floating_actions=True,
        show_page_header=False,
    )


def _render_brujula_indicadores_page(request: Request):
    from fastapi_modulo.main import render_backend_page

    return render_backend_page(
        request,
        title="BRUJULA - Indicadores",
        description="Gestión y seguimiento de indicadores clave de desempeño.",
        content=_load_indicadores_template(),
        hide_floating_actions=True,
        show_page_header=False,
    )


@router.get("/brujula", response_class=HTMLResponse)
def brujula_page(request: Request):
    return _render_brujula_page(
        request,
        "BRUJULA",
        "Dashboard Ejecutivo",
        "dashboard",
    )


@router.get("/brujula/{section}", response_class=HTMLResponse)
def brujula_section_page(request: Request, section: str):
    if section == "indicadores":
        return _render_brujula_indicadores_page(request)
    section_title = BRUJULA_SECTIONS.get(section, section.replace("-", " ").title())
    return _render_brujula_page(
        request,
        f"BRUJULA - {section_title}",
        section_title,
        section,
    )


router.add_api_route("/api/brujula/indicadores/notebook", get_brujula_indicator_notebook, methods=["GET"])
router.add_api_route("/api/brujula/indicadores/notebook", save_brujula_indicator_notebook, methods=["POST"])
router.add_api_route("/api/brujula/indicadores/importar", kpis_service.import_kpis_template, methods=["POST"])
