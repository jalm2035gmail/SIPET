import json
import os
import pathlib
import uuid
from typing import Any, Dict, List


_RUNTIME_STORE_DIR = os.environ.get("RUNTIME_STORE_DIR") or os.path.join(
    os.environ.get("SIPET_DATA_DIR") or os.path.expanduser("~/.sipet/data"),
    "runtime_store",
    (os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "development").strip().lower(),
)

_PUESTOS_PATH = os.path.join(_RUNTIME_STORE_DIR, "puestos_laborales.json")


def load_puestos() -> List[Dict[str, Any]]:
    try:
        if os.path.exists(_PUESTOS_PATH):
            data = json.loads(pathlib.Path(_PUESTOS_PATH).read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def save_puestos(data: List[Dict[str, Any]]) -> None:
    pathlib.Path(_PUESTOS_PATH).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(_PUESTOS_PATH).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def delete_puesto(puesto_id: str) -> List[Dict[str, Any]]:
    puestos = [p for p in load_puestos() if str(p.get("id") or "") != str(puesto_id or "")]
    save_puestos(puestos)
    return puestos


def update_puesto_notebook(
    puesto_id: str,
    *,
    habilidades_requeridas: Any,
    kpis: Any,
    colaboradores_asignados: Any,
) -> Dict[str, Any]:
    puestos = load_puestos()
    idx = next((i for i, p in enumerate(puestos) if str(p.get("id") or "") == str(puesto_id or "")), None)
    if idx is None:
        return {"success": False, "error": "Puesto no encontrado"}

    puestos[idx]["habilidades_requeridas"] = habilidades_requeridas if isinstance(habilidades_requeridas, list) else []
    if isinstance(kpis, list):
        puestos[idx]["kpis"] = kpis
    if isinstance(colaboradores_asignados, list):
        puestos[idx]["colaboradores_asignados"] = colaboradores_asignados
    save_puestos(puestos)
    return {"success": True, "data": puestos}


def upsert_puesto(body: Dict[str, Any], area_catalog: List[str]) -> Dict[str, Any]:
    puestos = load_puestos()
    existing = next((p for p in puestos if str(p.get("id") or "") == str(body.get("id") or "")), {})

    habilidades_requeridas = body.get("habilidades_requeridas", existing.get("habilidades_requeridas", []))
    if not isinstance(habilidades_requeridas, list):
        habilidades_requeridas = existing.get("habilidades_requeridas", [])

    area_value = str(body.get("area") or "").strip()
    catalog_map = {str(name).strip().lower(): str(name).strip() for name in area_catalog}
    if not area_value:
        return {"success": False, "error": "El área es obligatoria."}

    normalized_area = catalog_map.get(area_value.lower())
    if not normalized_area:
        return {"success": False, "error": "Área inválida. Seleccione un área del listado."}

    puesto = {
        "id": str(body.get("id") or uuid.uuid4()),
        "nombre": str(body.get("nombre") or "").strip(),
        "area": normalized_area,
        "nivel": str(body.get("nivel") or "").strip(),
        "descripcion": str(body.get("descripcion") or "").strip(),
        "habilidades_requeridas": habilidades_requeridas,
        "kpis": body.get("kpis", existing.get("kpis", []))
        if isinstance(body.get("kpis", existing.get("kpis", [])), list)
        else existing.get("kpis", []),
        "colaboradores_asignados": existing.get("colaboradores_asignados", []),
    }
    if not puesto["nombre"]:
        return {"success": False, "error": "El nombre es requerido"}

    idx = next((i for i, p in enumerate(puestos) if str(p.get("id") or "") == puesto["id"]), None)
    if idx is not None:
        puestos[idx] = puesto
    else:
        puestos.append(puesto)
    save_puestos(puestos)
    return {"success": True, "data": puestos, "puesto": puesto}
