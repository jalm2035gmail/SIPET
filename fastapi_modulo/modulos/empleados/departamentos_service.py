import json
import os
import pathlib
from typing import Any, Dict, List, Set

from fastapi import HTTPException

from fastapi_modulo.db import SessionLocal, DepartamentoOrganizacional, Base, engine
from fastapi_modulo.modulos.empleados.puestos_laborales_store import load_puestos


_DEP_FUNCIONES_PATH = os.path.join(
    os.environ.get("RUNTIME_STORE_DIR")
    or os.path.join(
        os.environ.get("SIPET_DATA_DIR") or os.path.expanduser("~/.sipet/data"),
        "runtime_store",
        (os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "development").strip().lower(),
    ),
    "departamentos_funciones.json",
)


def ensure_departamentos_schema() -> None:
    Base.metadata.create_all(bind=engine, tables=[DepartamentoOrganizacional.__table__], checkfirst=True)


def normalize_funciones_payload(raw: Any) -> Dict[str, List[str]]:
    groups = {
        "misionales": [],
        "apoyo": [],
        "proyectos_especiales": [],
    }
    if isinstance(raw, list):
        for item in raw:
            txt = str(item or "").strip()
            if txt and txt not in groups["misionales"]:
                groups["misionales"].append(txt)
        return groups
    if isinstance(raw, dict):
        for key in groups.keys():
            vals = raw.get(key, [])
            if not isinstance(vals, list):
                continue
            seen: List[str] = []
            for item in vals:
                txt = str(item or "").strip()
                if txt and txt not in seen:
                    seen.append(txt)
            groups[key] = seen
    return groups


def load_departamentos_funciones_map() -> Dict[str, Dict[str, List[str]]]:
    try:
        if os.path.exists(_DEP_FUNCIONES_PATH):
            raw = json.loads(pathlib.Path(_DEP_FUNCIONES_PATH).read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                cleaned: Dict[str, Dict[str, List[str]]] = {}
                for key, value in raw.items():
                    code_key = str(key or "").strip().lower()
                    if not code_key:
                        continue
                    cleaned[code_key] = normalize_funciones_payload(value)
                return cleaned
    except Exception:
        pass
    return {}


def save_departamentos_funciones_map(data: Dict[str, Dict[str, List[str]]]) -> None:
    pathlib.Path(_DEP_FUNCIONES_PATH).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(_DEP_FUNCIONES_PATH).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def build_empleados_count_map(rows: List[DepartamentoOrganizacional]) -> Dict[str, int]:
    from fastapi_modulo.main import Usuario

    db = SessionLocal()
    try:
        all_users = db.query(Usuario).all()
    finally:
        db.close()

    buckets: Dict[str, int] = {}
    for user in all_users:
        dep = str(getattr(user, "departamento", "") or "").strip().lower()
        if not dep:
            continue
        buckets[dep] = buckets.get(dep, 0) + 1

    counts: Dict[str, int] = {}
    for row in rows:
        code = str(getattr(row, "codigo", "") or "").strip().lower()
        name = str(getattr(row, "nombre", "") or "").strip().lower()
        total = 0
        if code:
            total += buckets.get(code, 0)
        if name and name != code:
            total += buckets.get(name, 0)
        counts[code or name] = total
    return counts


def serialize_departamentos(
    rows: List[DepartamentoOrganizacional],
    count_map: Dict[str, int] | None = None,
) -> List[Dict[str, Any]]:
    data: List[Dict[str, Any]] = []
    count_map = count_map or {}
    funciones_map = load_departamentos_funciones_map()
    for row in rows:
        code_key = str(row.codigo or "").strip().lower()
        data.append(
            {
                "name": str(row.nombre or "").strip(),
                "parent": str(row.padre or "N/A").strip() or "N/A",
                "manager": str(row.responsable or "").strip(),
                "code": str(row.codigo or "").strip(),
                "color": str(row.color or "#1d4ed8").strip() or "#1d4ed8",
                "status": str(row.estado or "Activo").strip() or "Activo",
                "empleados_asignados": int(count_map.get(code_key, 0)),
                "funciones": normalize_funciones_payload(funciones_map.get(code_key, {})),
            }
        )
    return data


def list_departamentos_payload() -> Dict[str, Any]:
    ensure_departamentos_schema()
    db = SessionLocal()
    try:
        rows = (
            db.query(DepartamentoOrganizacional)
            .order_by(DepartamentoOrganizacional.orden.asc(), DepartamentoOrganizacional.id.asc())
            .all()
        )
        count_map = build_empleados_count_map(rows)
        return {"success": True, "data": serialize_departamentos(rows, count_map)}
    finally:
        db.close()


def get_departamentos_catalog() -> List[str]:
    ensure_departamentos_schema()
    db = SessionLocal()
    try:
        rows = (
            db.query(DepartamentoOrganizacional)
            .order_by(DepartamentoOrganizacional.orden.asc(), DepartamentoOrganizacional.id.asc())
            .all()
        )
        catalog: List[str] = []
        seen: Set[str] = set()
        for row in rows:
            name = str(getattr(row, "nombre", "") or "").strip()
            key = name.lower()
            if not name or key in seen:
                continue
            seen.add(key)
            catalog.append(name)
        for puesto in load_puestos():
            area = str((puesto or {}).get("area") or "").strip()
            key = area.lower()
            if not area or key in seen:
                continue
            seen.add(key)
            catalog.append(area)
        return catalog
    finally:
        db.close()


def save_departamentos_payload(incoming: Any) -> Dict[str, Any]:
    if not isinstance(incoming, list):
        raise HTTPException(status_code=400, detail="Formato inválido")

    cleaned_rows: List[Dict[str, str]] = []
    funciones_map_next: Dict[str, Dict[str, List[str]]] = {}
    used_codes: Set[str] = set()
    for item in incoming:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        code = str(item.get("code") or "").strip()
        parent = str(item.get("parent") or "N/A").strip() or "N/A"
        manager = str(item.get("manager") or "").strip()
        color = str(item.get("color") or "#1d4ed8").strip() or "#1d4ed8"
        status = "Activo"
        funciones = normalize_funciones_payload(item.get("funciones", {}))
        if not name or not code:
            continue
        code_key = code.lower()
        if code_key in used_codes:
            continue
        used_codes.add(code_key)
        funciones_map_next[code_key] = funciones
        cleaned_rows.append(
            {
                "name": name,
                "code": code,
                "parent": parent,
                "manager": manager,
                "color": color,
                "status": status,
            }
        )

    if not cleaned_rows:
        raise HTTPException(status_code=400, detail="No hay departamentos válidos para guardar")

    ensure_departamentos_schema()
    db = SessionLocal()
    try:
        for idx, item in enumerate(cleaned_rows, start=1):
            existing = (
                db.query(DepartamentoOrganizacional)
                .filter(DepartamentoOrganizacional.codigo == item["code"])
                .first()
            )
            if existing:
                existing.nombre = item["name"]
                existing.padre = item["parent"]
                existing.responsable = item["manager"]
                existing.color = item["color"]
                existing.estado = item["status"]
                existing.orden = idx
                db.add(existing)
            else:
                db.add(
                    DepartamentoOrganizacional(
                        nombre=item["name"],
                        codigo=item["code"],
                        padre=item["parent"],
                        responsable=item["manager"],
                        color=item["color"],
                        estado=item["status"],
                        orden=idx,
                    )
                )
        db.commit()
        save_departamentos_funciones_map(funciones_map_next)
        rows = (
            db.query(DepartamentoOrganizacional)
            .order_by(DepartamentoOrganizacional.orden.asc(), DepartamentoOrganizacional.id.asc())
            .all()
        )
        count_map = build_empleados_count_map(rows)
        return {"success": True, "data": serialize_departamentos(rows, count_map)}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error guardando departamentos: {exc}")
    finally:
        db.close()


def delete_departamento_payload(code: str) -> Dict[str, Any]:
    ensure_departamentos_schema()
    target_code = str(code or "").strip()
    if not target_code:
        raise HTTPException(status_code=400, detail="Código inválido")

    db = SessionLocal()
    try:
        row = (
            db.query(DepartamentoOrganizacional)
            .filter(DepartamentoOrganizacional.codigo == target_code)
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail="Departamento no encontrado")
        db.delete(row)
        db.commit()
        funciones_map = load_departamentos_funciones_map()
        funciones_map.pop(target_code.lower(), None)
        save_departamentos_funciones_map(funciones_map)
        rows = (
            db.query(DepartamentoOrganizacional)
            .order_by(DepartamentoOrganizacional.orden.asc(), DepartamentoOrganizacional.id.asc())
            .all()
        )
        count_map = build_empleados_count_map(rows)
        return {"success": True, "data": serialize_departamentos(rows, count_map)}
    finally:
        db.close()
