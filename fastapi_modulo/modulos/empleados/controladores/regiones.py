import os
from typing import List, Dict

from fastapi import APIRouter, Body, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi_modulo.db import SessionLocal, RegionOrganizacional, MAIN, engine

router = APIRouter()
REGIONES_TEMPLATE_PATH = os.path.join("fastapi_modulo", "modulos", "empleados", "vistas", "regiones.html")


def _ensure_regiones_schema() -> None:
    MAIN.metadata.create_all(bind=engine, tables=[RegionOrganizacional.__table__], checkfirst=True)


_ensure_regiones_schema()


def _serialize_regiones(rows: List[RegionOrganizacional]) -> List[Dict[str, str]]:
    return [
        {
            "nombre": str(row.nombre or "").strip(),
            "codigo": str(row.codigo or "").strip(),
            "descripcion": str(row.descripcion or "").strip(),
        }
        for row in rows
    ]


def _load_regiones_template() -> str:
    try:
        with open(REGIONES_TEMPLATE_PATH, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return "<p>No se pudo cargar la plantilla de Regiones.</p>"


@router.get("/inicio/regiones", response_class=HTMLResponse)
def inicio_regiones_page(request: Request):
    from fastapi_modulo.main import render_backend_page

    return render_backend_page(
        request,
        title="Regiones",
        description="Registro y visualización de regiones.",
        content=_load_regiones_template(),
        hide_floating_actions=True,
        show_page_header=False,
        view_buttons=[
            {"label": "Form", "icon": "/templates/icon/formulario.svg", "view": "form", "active": True},
            {"label": "Lista", "icon": "/templates/icon/list.svg", "view": "list"},
            {"label": "Kanban", "icon": "/templates/icon/kanban.svg", "view": "kanban"},
        ],
    )


@router.get("/api/inicio/regiones")
def listar_regiones():
    db = SessionLocal()
    try:
        rows = (
            db.query(RegionOrganizacional)
            .order_by(RegionOrganizacional.orden.asc(), RegionOrganizacional.id.asc())
            .all()
        )
        return {"success": True, "data": _serialize_regiones(rows)}
    finally:
        db.close()


@router.post("/api/inicio/regiones")
async def guardar_regiones(data: dict = Body(...)):
    incoming = data.get("data", [])
    if not isinstance(incoming, list):
        raise HTTPException(status_code=400, detail="Formato inválido")
    cleaned_rows: List[Dict[str, str]] = []
    used_codes = set()
    for item in incoming:
        if not isinstance(item, dict):
            continue
        nombre = str(item.get("nombre") or "").strip()
        codigo = str(item.get("codigo") or "").strip()
        descripcion = str(item.get("descripcion") or "").strip()
        if not nombre or not codigo:
            continue
        code_key = codigo.lower()
        if code_key in used_codes:
            continue
        used_codes.add(code_key)
        cleaned_rows.append({"nombre": nombre, "codigo": codigo, "descripcion": descripcion})

    if not cleaned_rows:
        raise HTTPException(status_code=400, detail="No hay regiones válidas para guardar")

    db = SessionLocal()
    try:
        for idx, item in enumerate(cleaned_rows, start=1):
            existing = (
                db.query(RegionOrganizacional)
                .filter(RegionOrganizacional.codigo == item["codigo"])
                .first()
            )
            if existing:
                existing.nombre = item["nombre"]
                existing.descripcion = item["descripcion"]
                existing.orden = idx
                db.add(existing)
            else:
                db.add(
                    RegionOrganizacional(
                        nombre=item["nombre"],
                        codigo=item["codigo"],
                        descripcion=item["descripcion"],
                        orden=idx,
                    )
                )
        db.commit()
        rows = (
            db.query(RegionOrganizacional)
            .order_by(RegionOrganizacional.orden.asc(), RegionOrganizacional.id.asc())
            .all()
        )
        return {"success": True, "data": _serialize_regiones(rows)}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error guardando regiones: {exc}")
    finally:
        db.close()
