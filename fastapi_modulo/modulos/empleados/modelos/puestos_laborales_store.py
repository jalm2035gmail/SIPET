import json
import os
import pathlib
import uuid
from typing import Any, Dict, List


_APP_ENV = (os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "development").strip().lower()
_DEFAULT_SIPET_DATA_DIR = (os.environ.get("SIPET_DATA_DIR") or os.path.expanduser("~/.sipet/data")).strip()
_ENV_RUNTIME_STORE_DIR = (os.environ.get("RUNTIME_STORE_DIR") or "").strip()
_LEGACY_RUNTIME_STORE_DIR = os.path.join(_DEFAULT_SIPET_DATA_DIR, "runtime_store", _APP_ENV)
_APP_RUNTIME_STORE_DIR = os.path.join("fastapi_modulo", "runtime_store", _APP_ENV)
_PUESTOS_ENV_PATH = (os.environ.get("PUESTOS_LAB_PATH") or "").strip()


def _candidate_puestos_paths() -> List[str]:
    paths: List[str] = []
    if _PUESTOS_ENV_PATH:
        paths.append(_PUESTOS_ENV_PATH)
    if _ENV_RUNTIME_STORE_DIR:
        paths.append(os.path.join(_ENV_RUNTIME_STORE_DIR, "puestos_laborales.json"))
    paths.append(os.path.join(_LEGACY_RUNTIME_STORE_DIR, "puestos_laborales.json"))
    paths.append(os.path.join(_APP_RUNTIME_STORE_DIR, "puestos_laborales.json"))
    unique: List[str] = []
    seen = set()
    for raw in paths:
        path = str(raw or "").strip()
        if not path:
            continue
        key = os.path.abspath(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique


def _read_puestos_file(path: str) -> List[Dict[str, Any]]:
    try:
        if os.path.exists(path):
            data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
    except Exception:
        pass
    return []


def _save_target_path() -> str:
    for path in _candidate_puestos_paths():
        if os.path.exists(path):
            return path
    return os.path.join(_LEGACY_RUNTIME_STORE_DIR, "puestos_laborales.json")


def _puesto_semantic_key(item: Dict[str, Any]) -> str:
    nombre = str(item.get("nombre") or "").strip().lower()
    area = str(item.get("area") or "").strip().lower()
    nivel = str(item.get("nivel") or "").strip().lower()
    return f"{nombre}|{area}|{nivel}"


def _normalize_puestos(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_key: Dict[str, Dict[str, Any]] = {}
    ordered_keys: List[str] = []
    for raw in items or []:
        if not isinstance(raw, dict):
            continue
        item = dict(raw)
        semantic_key = _puesto_semantic_key(item)
        if semantic_key.strip("|"):
            if semantic_key not in ordered_keys:
                ordered_keys.append(semantic_key)
            by_key[semantic_key] = item
        else:
            fallback_id = str(item.get("id") or "").strip()
            if fallback_id and fallback_id not in ordered_keys:
                ordered_keys.append(fallback_id)
            if fallback_id:
                by_key[fallback_id] = item
    normalized: List[Dict[str, Any]] = []
    for key in ordered_keys:
        item = by_key.get(key) or {}
        if not item:
            continue
        normalized.append(item)
    return normalized


def load_puestos() -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    for path in _candidate_puestos_paths():
        for item in _read_puestos_file(path):
            if not isinstance(item, dict):
                continue
            merged.append(item)
    return _normalize_puestos(merged)


def save_puestos(data: List[Dict[str, Any]]) -> None:
    target_path = _save_target_path()
    normalized = _normalize_puestos(data)
    pathlib.Path(target_path).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(target_path).write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")


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
