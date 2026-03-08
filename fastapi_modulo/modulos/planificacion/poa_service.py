from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Set

from fastapi import Body, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, text

from fastapi_modulo.modulos.empleados.empleados import _load_colab_meta, _normalize_poa_access_level
from fastapi_modulo.modulos.planificacion.plan_estrategico_service import (
    _milestones_by_objective_ids,
    _serialize_strategic_objective,
)

_CORE_BOUND = False


def _bind_core_symbols() -> None:
    global _CORE_BOUND
    if _CORE_BOUND:
        return
    from fastapi_modulo import main as core

    names = [
        'SessionLocal',
        'StrategicAxisConfig',
        'StrategicObjectiveConfig',
        'POAActivity',
        'POASubactivity',
        'POADeliverableApproval',
        'Usuario',
        '_date_to_iso',
        '_activity_status',
        'is_admin_or_superadmin',
        '_parse_date_field',
        '_validate_date_range',
        '_validate_child_date_range',
        '_current_user_record',
        '_user_aliases',
        '_resolve_process_owner_for_objective',
        '_is_user_process_owner',
        'normalize_role_name',
        'get_current_role',
        '_resolve_user_role_name',
    ]
    for name in names:
        globals()[name] = getattr(core, name)
    _CORE_BOUND = True

def _poa_access_level_for_request(request: Request, db) -> str:
    _bind_core_symbols()
    if _is_request_admin_like(request, db):
        return "todas_tareas"
    user = _current_user_record(request, db)
    if not user or not getattr(user, "id", None):
        return "mis_tareas"
    meta = _load_colab_meta()
    entry = meta.get(str(int(user.id))) if isinstance(meta, dict) else None
    return _normalize_poa_access_level((entry or {}).get("poa_access_level", "mis_tareas"))


def _is_request_admin_like(request: Request, db) -> bool:
    _bind_core_symbols()
    if is_admin_or_superadmin(request):
        return True
    # Fallback: si la sesión/cookie no trae rol correcto, usamos el rol persistido del usuario.
    user = _current_user_record(request, db)
    if not user:
        return False
    user_role = ""
    try:
        user_role = normalize_role_name(str(_resolve_user_role_name(db, user) or ""))
    except Exception:
        user_role = normalize_role_name(str(getattr(user, "role", "") or ""))
    return user_role in {"administrador", "superadministrador"}


def _ensure_poa_budget_table(db) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS poa_activity_budgets (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              activity_id INTEGER NOT NULL,
              tipo VARCHAR(120) NOT NULL DEFAULT '',
              rubro VARCHAR(255) NOT NULL DEFAULT '',
              mensual NUMERIC NOT NULL DEFAULT 0,
              anual NUMERIC NOT NULL DEFAULT 0,
              autorizado INTEGER NOT NULL DEFAULT 0,
              orden INTEGER NOT NULL DEFAULT 0
            )
            """
        )
    )


def _to_budget_amount(value: Any) -> float:
    raw = str(value or "").strip().replace(",", "")
    if not raw:
        return 0.0
    try:
        num = float(raw)
    except (TypeError, ValueError):
        return 0.0
    if num < 0:
        return 0.0
    return round(num, 2)


def _normalize_budget_items(raw: Any) -> List[Dict[str, Any]]:
    allowed_types = {
        "Sueldos y similares",
        "Honorarios",
        "Gastos de promoción y publicidad",
        "Gastos no deducibles",
        "Gastos en tecnologia",
        "Otros gastos de administración y promoción",
    }
    rows = raw if isinstance(raw, list) else []
    cleaned: List[Dict[str, Any]] = []
    for idx, item in enumerate(rows, start=1):
        if not isinstance(item, dict):
            continue
        tipo = str(item.get("tipo") or "").strip()
        rubro = str(item.get("rubro") or "").strip()
        if not tipo or tipo not in allowed_types:
            continue
        if not rubro:
            continue
        mensual = _to_budget_amount(item.get("mensual"))
        anual = _to_budget_amount(item.get("anual"))
        cleaned.append(
            {
                "tipo": tipo,
                "rubro": rubro,
                "mensual": mensual,
                "anual": anual,
                "autorizado": bool(item.get("autorizado")),
                "orden": idx,
            }
        )
    return cleaned


def _budgets_by_activity_ids(db, activity_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    result: Dict[int, List[Dict[str, Any]]] = {}
    if not activity_ids:
        return result
    _ensure_poa_budget_table(db)
    db.commit()
    placeholders = ", ".join([f":id_{idx}" for idx, _ in enumerate(activity_ids)])
    sql = text(
        f"""
        SELECT id, activity_id, tipo, rubro, mensual, anual, autorizado, orden
        FROM poa_activity_budgets
        WHERE activity_id IN ({placeholders})
        ORDER BY activity_id ASC, orden ASC, id ASC
        """
    )
    params = {f"id_{idx}": int(activity_id) for idx, activity_id in enumerate(activity_ids)}
    rows = db.execute(sql, params).fetchall()
    for row in rows:
        activity_id = int(row[1] or 0)
        if activity_id <= 0:
            continue
        result.setdefault(activity_id, []).append(
            {
                "id": int(row[0] or 0),
                "tipo": str(row[2] or ""),
                "rubro": str(row[3] or ""),
                "mensual": float(row[4] or 0),
                "anual": float(row[5] or 0),
                "autorizado": bool(row[6]),
                "orden": int(row[7] or 0),
            }
        )
    return result


def _replace_activity_budgets(db, activity_id: int, items: Any) -> List[Dict[str, Any]]:
    clean = _normalize_budget_items(items)
    _ensure_poa_budget_table(db)
    db.execute(text("DELETE FROM poa_activity_budgets WHERE activity_id = :aid"), {"aid": int(activity_id)})
    for item in clean:
        db.execute(
            text(
                """
                INSERT INTO poa_activity_budgets (
                  activity_id, tipo, rubro, mensual, anual, autorizado, orden
                ) VALUES (
                  :activity_id, :tipo, :rubro, :mensual, :anual, :autorizado, :orden
                )
                """
            ),
            {
                "activity_id": int(activity_id),
                "tipo": item["tipo"],
                "rubro": item["rubro"],
                "mensual": float(item["mensual"]),
                "anual": float(item["anual"]),
                "autorizado": 1 if item.get("autorizado") else 0,
                "orden": int(item["orden"]),
            },
        )
    return clean


def _delete_activity_budgets(db, activity_id: int) -> None:
    _ensure_poa_budget_table(db)
    db.execute(text("DELETE FROM poa_activity_budgets WHERE activity_id = :aid"), {"aid": int(activity_id)})


def _ensure_poa_deliverables_table(db) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS poa_activity_deliverables (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              activity_id INTEGER NOT NULL,
              nombre VARCHAR(255) NOT NULL DEFAULT '',
              validado INTEGER NOT NULL DEFAULT 0,
              orden INTEGER NOT NULL DEFAULT 0
            )
            """
        )
    )


def _normalize_deliverable_items(raw: Any) -> List[Dict[str, Any]]:
    rows = raw if isinstance(raw, list) else []
    cleaned: List[Dict[str, Any]] = []
    for idx, item in enumerate(rows, start=1):
        if isinstance(item, dict):
            nombre = str(item.get("nombre") or "").strip()
            validado = bool(item.get("validado"))
            try:
                item_id = int(item.get("id") or 0)
            except (TypeError, ValueError):
                item_id = 0
        else:
            nombre = str(item or "").strip()
            validado = False
            item_id = 0
        if not nombre:
            continue
        cleaned.append(
            {
                "id": item_id if item_id > 0 else 0,
                "nombre": nombre,
                "validado": validado,
                "orden": idx,
            }
        )
    return cleaned


def _deliverables_by_activity_ids(db, activity_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    result: Dict[int, List[Dict[str, Any]]] = {}
    if not activity_ids:
        return result
    _ensure_poa_deliverables_table(db)
    db.commit()
    placeholders = ", ".join([f":id_{idx}" for idx, _ in enumerate(activity_ids)])
    sql = text(
        f"""
        SELECT id, activity_id, nombre, validado, orden
        FROM poa_activity_deliverables
        WHERE activity_id IN ({placeholders})
        ORDER BY activity_id ASC, orden ASC, id ASC
        """
    )
    params = {f"id_{idx}": int(activity_id) for idx, activity_id in enumerate(activity_ids)}
    rows = db.execute(sql, params).fetchall()
    for row in rows:
        activity_id = int(row[1] or 0)
        if activity_id <= 0:
            continue
        result.setdefault(activity_id, []).append(
            {
                "id": int(row[0] or 0),
                "nombre": str(row[2] or ""),
                "validado": bool(row[3]),
                "orden": int(row[4] or 0),
            }
        )
    return result


def _replace_activity_deliverables(db, activity_id: int, items: Any) -> List[Dict[str, Any]]:
    clean = _normalize_deliverable_items(items)
    _ensure_poa_deliverables_table(db)
    db.execute(text("DELETE FROM poa_activity_deliverables WHERE activity_id = :aid"), {"aid": int(activity_id)})
    for item in clean:
        db.execute(
            text(
                """
                INSERT INTO poa_activity_deliverables (
                  activity_id, nombre, validado, orden
                ) VALUES (
                  :activity_id, :nombre, :validado, :orden
                )
                """
            ),
            {
                "activity_id": int(activity_id),
                "nombre": item["nombre"],
                "validado": 1 if item.get("validado") else 0,
                "orden": int(item["orden"]),
            },
        )
    return clean


def _delete_activity_deliverables(db, activity_id: int) -> None:
    _ensure_poa_deliverables_table(db)
    db.execute(text("DELETE FROM poa_activity_deliverables WHERE activity_id = :aid"), {"aid": int(activity_id)})


def _ensure_poa_subactivity_recurrence_columns(db) -> None:
    try:
        cols = db.execute(text("PRAGMA table_info(poa_subactivities)")).fetchall()
        col_names = {str(col[1]).strip().lower() for col in cols if len(col) > 1}
        if "recurrente" not in col_names:
            db.execute(
                text(
                    "ALTER TABLE poa_subactivities ADD COLUMN recurrente INTEGER NOT NULL DEFAULT 0"
                )
            )
        if "periodicidad" not in col_names:
            db.execute(
                text(
                    "ALTER TABLE poa_subactivities ADD COLUMN periodicidad VARCHAR(50) NOT NULL DEFAULT ''"
                )
            )
        if "cada_xx_dias" not in col_names:
            db.execute(
                text(
                    "ALTER TABLE poa_subactivities ADD COLUMN cada_xx_dias INTEGER"
                )
            )
        db.commit()
    except Exception:
        db.rollback()


def _ensure_activity_milestone_link_table(db) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS poa_activity_milestone_links (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              activity_id INTEGER NOT NULL,
              milestone_id INTEGER NOT NULL,
              orden INTEGER NOT NULL DEFAULT 0
            )
            """
        )
    )


def _normalize_impacted_milestone_ids(raw: Any) -> List[int]:
    rows = raw if isinstance(raw, list) else []
    clean: List[int] = []
    for value in rows:
        try:
            milestone_id = int(value)
        except (TypeError, ValueError):
            continue
        if milestone_id > 0 and milestone_id not in clean:
            clean.append(milestone_id)
    return clean


def _activity_milestones_by_activity_ids(db, activity_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
    result: Dict[int, List[Dict[str, Any]]] = {}
    if not activity_ids:
        return result
    _ensure_objective_milestone_table(db)
    _ensure_activity_milestone_link_table(db)
    db.commit()
    placeholders = ", ".join([f":id_{idx}" for idx, _ in enumerate(activity_ids)])
    sql = text(
        f"""
        SELECT l.activity_id, m.id, m.nombre, l.orden
        FROM poa_activity_milestone_links l
        JOIN strategic_objective_milestones m ON m.id = l.milestone_id
        WHERE l.activity_id IN ({placeholders})
        ORDER BY l.activity_id ASC, l.orden ASC, l.id ASC
        """
    )
    params = {f"id_{idx}": int(activity_id) for idx, activity_id in enumerate(activity_ids)}
    rows = db.execute(sql, params).fetchall()
    for row in rows:
        activity_id = int(row[0] or 0)
        if activity_id <= 0:
            continue
        result.setdefault(activity_id, []).append(
            {
                "id": int(row[1] or 0),
                "nombre": str(row[2] or ""),
                "orden": int(row[3] or 0),
            }
        )
    return result


def _replace_activity_milestone_links(db, activity_id: int, milestone_ids: Any) -> List[int]:
    clean_ids = _normalize_impacted_milestone_ids(milestone_ids)
    _ensure_activity_milestone_link_table(db)
    db.execute(text("DELETE FROM poa_activity_milestone_links WHERE activity_id = :aid"), {"aid": int(activity_id)})
    for idx, milestone_id in enumerate(clean_ids, start=1):
        db.execute(
            text(
                """
                INSERT INTO poa_activity_milestone_links (activity_id, milestone_id, orden)
                VALUES (:activity_id, :milestone_id, :orden)
                """
            ),
            {
                "activity_id": int(activity_id),
                "milestone_id": int(milestone_id),
                "orden": idx,
            },
        )
    return clean_ids


def _delete_activity_milestone_links(db, activity_id: int) -> None:
    _ensure_activity_milestone_link_table(db)
    db.execute(text("DELETE FROM poa_activity_milestone_links WHERE activity_id = :aid"), {"aid": int(activity_id)})


def _descendant_subactivity_ids(db, activity_id: int, root_id: int) -> List[int]:
    rows = (
        db.query(POASubactivity.id, POASubactivity.parent_subactivity_id)
        .filter(POASubactivity.activity_id == activity_id)
        .all()
    )
    children: Dict[int, List[int]] = {}
    for sub_id, parent_id in rows:
        if parent_id is None:
            continue
        children.setdefault(int(parent_id), []).append(int(sub_id))
    collected: List[int] = []
    stack = [int(root_id)]
    while stack:
        current = stack.pop()
        for child in children.get(current, []):
            collected.append(child)
            stack.append(child)
    return collected


def _serialize_poa_subactivity(item: POASubactivity) -> Dict[str, Any]:
    _bind_core_symbols()
    today = datetime.utcnow().date()
    done = bool(item.fecha_final and today >= item.fecha_final)
    return {
        "id": item.id,
        "activity_id": item.activity_id,
        "parent_subactivity_id": item.parent_subactivity_id,
        "nivel": item.nivel or 1,
        "nombre": item.nombre or "",
        "codigo": item.codigo or "",
        "responsable": item.responsable or "",
        "entregable": item.entregable or "",
        "fecha_inicial": _date_to_iso(item.fecha_inicial),
        "fecha_final": _date_to_iso(item.fecha_final),
        "descripcion": item.descripcion or "",
        "recurrente": bool(getattr(item, "recurrente", False)),
        "periodicidad": str(getattr(item, "periodicidad", "") or ""),
        "cada_xx_dias": int(getattr(item, "cada_xx_dias", 0) or 0),
        "avance": 100 if done else 0,
    }


def _serialize_poa_activity(
    item: POAActivity,
    subactivities: List[POASubactivity],
    budget_items: List[Dict[str, Any]] | None = None,
    hitos_impacta: List[Dict[str, Any]] | None = None,
    deliverables: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    _bind_core_symbols()
    today = datetime.utcnow().date()
    if subactivities:
        done_subs = sum(1 for sub in subactivities if sub.fecha_final and today >= sub.fecha_final)
        activity_progress = int(round((done_subs / len(subactivities)) * 100))
    else:
        activity_progress = 100 if _activity_status(item) == "Terminada" else 0
    return {
        "id": item.id,
        "objective_id": item.objective_id,
        "nombre": item.nombre or "",
        "codigo": item.codigo or "",
        "responsable": item.responsable or "",
        "entregable": item.entregable or "",
        "fecha_inicial": _date_to_iso(item.fecha_inicial),
        "fecha_final": _date_to_iso(item.fecha_final),
        "inicio_forzado": bool(item.inicio_forzado),
        "recurrente": bool(item.recurrente),
        "periodicidad": item.periodicidad or "",
        "cada_xx_dias": item.cada_xx_dias or 0,
        "status": _activity_status(item),
        "avance": activity_progress,
        "entrega_estado": item.entrega_estado or "ninguna",
        "entrega_solicitada_por": item.entrega_solicitada_por or "",
        "entrega_solicitada_at": item.entrega_solicitada_at.isoformat() if item.entrega_solicitada_at else "",
        "entrega_aprobada_por": item.entrega_aprobada_por or "",
        "entrega_aprobada_at": item.entrega_aprobada_at.isoformat() if item.entrega_aprobada_at else "",
        "created_by": item.created_by or "",
        "descripcion": item.descripcion or "",
        "budget_items": budget_items or [],
        "hitos_impacta": hitos_impacta or [],
        "entregables": deliverables or [],
        "subactivities": [
            _serialize_poa_subactivity(sub)
            for sub in sorted(subactivities, key=lambda x: ((x.nivel or 1), x.id or 0))
        ],
    }


def _allowed_objectives_for_user(request: Request, db) -> List[StrategicObjectiveConfig]:
    _bind_core_symbols()
    def _active_or_any_objectives() -> List[StrategicObjectiveConfig]:
        active_rows = (
            db.query(StrategicObjectiveConfig)
            .filter(StrategicObjectiveConfig.is_active == True)
            .order_by(StrategicObjectiveConfig.orden.asc(), StrategicObjectiveConfig.id.asc())
            .all()
        )
        if active_rows:
            return active_rows
        return (
            db.query(StrategicObjectiveConfig)
            .order_by(StrategicObjectiveConfig.orden.asc(), StrategicObjectiveConfig.id.asc())
            .all()
        )

    if _is_request_admin_like(request, db):
        return _active_or_any_objectives()

    poa_access_level = _poa_access_level_for_request(request, db)
    if poa_access_level == "todas_tareas":
        return _active_or_any_objectives()

    session_username = (getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "").strip()
    user = _current_user_record(request, db)
    aliases = _user_aliases(user, session_username)
    alias_set = {str(item or "").strip().lower() for item in aliases if str(item or "").strip()}
    if not alias_set:
        # Fallback de visualización: si no se pudo resolver identidad de sesión,
        # mostrar objetivos en modo lectura para evitar tablero vacío.
        return _active_or_any_objectives()

    objective_ids: Set[int] = set()
    own_activities = (
        db.query(POAActivity.id, POAActivity.objective_id)
        .filter(func.lower(POAActivity.responsable).in_(alias_set))
        .all()
    )
    for _aid, oid in own_activities:
        try:
            if int(oid or 0) > 0:
                objective_ids.add(int(oid))
        except Exception:
            continue
    own_subactivities = (
        db.query(POASubactivity.id, POAActivity.objective_id)
        .join(POAActivity, POAActivity.id == POASubactivity.activity_id)
        .filter(func.lower(POASubactivity.responsable).in_(alias_set))
        .all()
    )
    for _sid, oid in own_subactivities:
        try:
            if int(oid or 0) > 0:
                objective_ids.add(int(oid))
        except Exception:
            continue
    if not objective_ids:
        # Si el usuario no tiene asignaciones directas, permitir vista global (solo lectura).
        return _active_or_any_objectives()
    rows = (
        db.query(StrategicObjectiveConfig)
        .filter(
            StrategicObjectiveConfig.is_active == True,
            StrategicObjectiveConfig.id.in_(sorted(objective_ids)),
        )
        .order_by(StrategicObjectiveConfig.orden.asc(), StrategicObjectiveConfig.id.asc())
        .all()
    )
    if rows:
        return rows
    return (
        db.query(StrategicObjectiveConfig)
        .filter(StrategicObjectiveConfig.id.in_(sorted(objective_ids)))
        .order_by(StrategicObjectiveConfig.orden.asc(), StrategicObjectiveConfig.id.asc())
        .all()
    )


def poa_board_data(request: Request):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        _ensure_poa_subactivity_recurrence_columns(db)
        admin_like = _is_request_admin_like(request, db)
        objectives = _allowed_objectives_for_user(request, db)
        objective_ids = [obj.id for obj in objectives]
        objective_axis_map = {obj.id: obj.eje_id for obj in objectives}
        axis_ids = sorted(set(objective_axis_map.values()))
        axes = (
            db.query(StrategicAxisConfig)
            .filter(StrategicAxisConfig.id.in_(axis_ids))
            .all()
            if axis_ids else []
        )
        axis_name_map = {axis.id: axis.nombre for axis in axes}
        milestones_by_objective = _milestones_by_objective_ids(db, objective_ids)

        activities = (
            db.query(POAActivity)
            .filter(POAActivity.objective_id.in_(objective_ids))
            .order_by(POAActivity.id.asc())
            .all()
            if objective_ids else []
        )
        activity_ids = [item.id for item in activities]
        subactivities = (
            db.query(POASubactivity)
            .filter(POASubactivity.activity_id.in_(activity_ids))
            .order_by(POASubactivity.id.asc())
            .all()
            if activity_ids else []
        )
        sub_by_activity: Dict[int, List[POASubactivity]] = {}
        for sub in subactivities:
            sub_by_activity.setdefault(sub.activity_id, []).append(sub)
        budgets_by_activity = _budgets_by_activity_ids(db, [int(activity.id) for activity in activities if getattr(activity, "id", None)])
        deliverables_by_activity = _deliverables_by_activity_ids(db, [int(activity.id) for activity in activities if getattr(activity, "id", None)])
        impacted_milestones_by_activity = _activity_milestones_by_activity_ids(
            db,
            [int(activity.id) for activity in activities if getattr(activity, "id", None)],
        )
        session_username = (getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "").strip()
        user = _current_user_record(request, db)
        aliases = _user_aliases(user, session_username)
        alias_set = {str(item or "").strip().lower() for item in aliases if str(item or "").strip()}
        poa_access_level = _poa_access_level_for_request(request, db)
        session_role_raw = str(getattr(request.state, "user_role", None) or request.cookies.get("user_role") or "")
        session_role_normalized = normalize_role_name(session_role_raw)
        detected_role = normalize_role_name(get_current_role(request))
        if detected_role in {"administrador", "superadministrador"}:
            admin_like = True
            poa_access_level = "todas_tareas"
        objective_can_validate: Dict[int, bool] = {}
        for obj in objectives:
            leader = (obj.lider or "").strip().lower()
            objective_can_validate[int(obj.id)] = bool(leader and leader in aliases) or admin_like

        pending_approvals = (
            db.query(POADeliverableApproval)
            .filter(POADeliverableApproval.status == "pendiente")
            .order_by(POADeliverableApproval.created_at.desc())
            .all()
        )
        approvals_for_user = []
        for approval in pending_approvals:
            if not _is_user_process_owner(request, db, approval.process_owner):
                continue
            activity = next((item for item in activities if item.id == approval.activity_id), None)
            if not activity:
                activity = db.query(POAActivity).filter(POAActivity.id == approval.activity_id).first()
            objective = next((item for item in objectives if item.id == approval.objective_id), None)
            if not objective:
                objective = db.query(StrategicObjectiveConfig).filter(StrategicObjectiveConfig.id == approval.objective_id).first()
            approvals_for_user.append(
                {
                    "id": approval.id,
                    "activity_id": approval.activity_id,
                    "objective_id": approval.objective_id,
                    "process_owner": approval.process_owner or "",
                    "requester": approval.requester or "",
                    "created_at": approval.created_at.isoformat() if approval.created_at else "",
                    "activity_nombre": (activity.nombre if activity else ""),
                    "activity_codigo": (activity.codigo if activity else ""),
                    "objective_nombre": (objective.nombre if objective else ""),
                    "objective_codigo": (objective.codigo if objective else ""),
                }
            )

        return JSONResponse(
            {
                "success": True,
                "objectives": [
                    {
                        **_serialize_strategic_objective(obj),
                        "axis_name": axis_name_map.get(obj.eje_id, ""),
                        "hitos": milestones_by_objective.get(int(obj.id), []),
                        "can_validate_deliverables": bool(objective_can_validate.get(int(obj.id), False)),
                    }
                    for obj in objectives
                ],
                "activities": [
                    {
                        **_serialize_poa_activity(
                            activity,
                            sub_by_activity.get(activity.id, []),
                            budgets_by_activity.get(int(activity.id), []),
                            impacted_milestones_by_activity.get(int(activity.id), []),
                            deliverables_by_activity.get(int(activity.id), []),
                        ),
                        "can_change_status": bool((activity.responsable or "").strip().lower() in alias_set),
                    }
                    for activity in activities
                ],
                "pending_approvals": approvals_for_user,
                "permissions": {
                    "poa_access_level": poa_access_level,
                    "can_manage_content": bool(admin_like),
                    "can_view_gantt": bool(poa_access_level == "todas_tareas"),
                },
                "diagnostics": {
                    "user_name": session_username,
                    "role_raw": session_role_raw,
                    "role_normalized": session_role_normalized,
                    "role_detected": detected_role,
                    "is_admin_or_superadmin": bool(admin_like),
                    "poa_access_level": poa_access_level,
                    "objectives_count": len(objectives),
                    "activities_count": len(activities),
                },
            }
        )
    finally:
        db.close()


def poa_activities_without_owner(request: Request):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        objectives = _allowed_objectives_for_user(request, db)
        objective_ids = [obj.id for obj in objectives]
        if not objective_ids:
            return JSONResponse({"success": True, "total": 0, "data": []})
        activities = (
            db.query(POAActivity)
            .filter(POAActivity.objective_id.in_(objective_ids))
            .order_by(POAActivity.id.desc())
            .all()
        )
        objective_map = {int(obj.id): obj for obj in objectives}
        rows: List[Dict[str, Any]] = []
        for item in activities:
            if str(item.responsable or "").strip():
                continue
            objective = objective_map.get(int(item.objective_id or 0))
            rows.append(
                {
                    "activity_id": int(item.id or 0),
                    "activity_nombre": str(item.nombre or ""),
                    "activity_codigo": str(item.codigo or ""),
                    "objective_id": int(item.objective_id or 0),
                    "objective_nombre": str(getattr(objective, "nombre", "") or ""),
                    "objective_codigo": str(getattr(objective, "codigo", "") or ""),
                    "fecha_inicial": _date_to_iso(item.fecha_inicial),
                    "fecha_final": _date_to_iso(item.fecha_final),
                    "status": _activity_status(item),
                }
            )
        return JSONResponse({"success": True, "total": len(rows), "data": rows})
    finally:
        db.close()


def create_poa_activity(request: Request, data: dict = Body(...)):
    _bind_core_symbols()
    objective_id = int(data.get("objective_id") or 0)
    nombre = (data.get("nombre") or "").strip()
    responsable = (data.get("responsable") or "").strip()
    entregable = (data.get("entregable") or "").strip()
    deliverables_input = data.get("entregables")
    normalized_deliverables = _normalize_deliverable_items(deliverables_input)
    if not normalized_deliverables and entregable:
        normalized_deliverables = [{"id": 0, "nombre": entregable, "validado": False, "orden": 1}]
    if not objective_id or not nombre or not normalized_deliverables:
        return JSONResponse(
            {"success": False, "error": "Objetivo, nombre y al menos un entregable son obligatorios"},
            status_code=400,
        )
    start_date, start_error = _parse_date_field(data.get("fecha_inicial"), "Fecha inicial", required=True)
    if start_error:
        return JSONResponse({"success": False, "error": start_error}, status_code=400)
    end_date, end_error = _parse_date_field(data.get("fecha_final"), "Fecha final", required=True)
    if end_error:
        return JSONResponse({"success": False, "error": end_error}, status_code=400)
    range_error = _validate_date_range(start_date, end_date, "Actividad")
    if range_error:
        return JSONResponse({"success": False, "error": range_error}, status_code=400)
    recurrente = bool(data.get("recurrente"))
    periodicidad = (data.get("periodicidad") or "").strip().lower()
    try:
        cada_xx_dias = int(data.get("cada_xx_dias") or 0)
    except (TypeError, ValueError):
        return JSONResponse({"success": False, "error": "Cada xx días debe ser un número válido"}, status_code=400)
    if recurrente:
        if periodicidad not in VALID_ACTIVITY_PERIODICITIES:
            return JSONResponse({"success": False, "error": "Selecciona una periodicidad válida"}, status_code=400)
        if periodicidad == "cada_xx_dias":
            if cada_xx_dias <= 0:
                return JSONResponse({"success": False, "error": "Cada xx días debe ser mayor a 0"}, status_code=400)
    else:
        periodicidad = ""
        cada_xx_dias = 0
    impacted_milestone_ids = _normalize_impacted_milestone_ids(data.get("impacted_milestone_ids"))

    db = SessionLocal()
    try:
        admin_like = _is_request_admin_like(request, db)
        if not admin_like:
            return JSONResponse({"success": False, "error": "Solo administrador puede crear actividades"}, status_code=403)
        allowed_ids = {obj.id for obj in _allowed_objectives_for_user(request, db)}
        if objective_id not in allowed_ids and not admin_like:
            return JSONResponse({"success": False, "error": "No autorizado para este objetivo"}, status_code=403)
        objective = db.query(StrategicObjectiveConfig).filter(StrategicObjectiveConfig.id == objective_id).first()
        if not objective:
            return JSONResponse({"success": False, "error": "Objetivo no encontrado"}, status_code=404)
        session_username = (getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "").strip()
        user = _current_user_record(request, db)
        aliases = _user_aliases(user, session_username)
        can_validate_deliverables = bool((objective.lider or "").strip().lower() in aliases) or admin_like
        if not can_validate_deliverables:
            normalized_deliverables = [{**item, "validado": False} for item in normalized_deliverables]
        valid_milestone_ids = {int(item.get("id") or 0) for item in _milestones_by_objective_ids(db, [objective_id]).get(objective_id, [])}
        invalid_milestones = [mid for mid in impacted_milestone_ids if mid not in valid_milestone_ids]
        if invalid_milestones:
            return JSONResponse(
                {"success": False, "error": "Los hitos seleccionados no pertenecen al objetivo."},
                status_code=400,
            )
        parent_error = _validate_child_date_range(
            start_date,
            end_date,
            objective.fecha_inicial,
            objective.fecha_final,
            "Actividad",
            "Objetivo",
        )
        if parent_error:
            return JSONResponse({"success": False, "error": parent_error}, status_code=400)
        created_by = session_username
        activity = POAActivity(
            objective_id=objective_id,
            nombre=nombre,
            codigo=(data.get("codigo") or "").strip(),
            responsable=responsable,
            entregable=str(normalized_deliverables[0].get("nombre") or "").strip(),
            fecha_inicial=start_date,
            fecha_final=end_date,
            inicio_forzado=bool(data.get("inicio_forzado")),
            descripcion=(data.get("descripcion") or "").strip(),
            recurrente=recurrente,
            periodicidad=periodicidad,
            cada_xx_dias=(cada_xx_dias if periodicidad == "cada_xx_dias" else None),
            created_by=created_by,
        )
        db.add(activity)
        db.commit()
        db.refresh(activity)
        budget_rows: List[Dict[str, Any]] = []
        linked_milestones: List[Dict[str, Any]] = []
        deliverable_rows: List[Dict[str, Any]] = _replace_activity_deliverables(db, int(activity.id), normalized_deliverables)
        if "budget_items" in data:
            budget_rows = _replace_activity_budgets(db, int(activity.id), data.get("budget_items"))
        if "impacted_milestone_ids" in data:
            _replace_activity_milestone_links(db, int(activity.id), impacted_milestone_ids)
            linked_milestones = _activity_milestones_by_activity_ids(db, [int(activity.id)]).get(int(activity.id), [])
            db.commit()
        return JSONResponse({"success": True, "data": _serialize_poa_activity(activity, [], budget_rows, linked_milestones, deliverable_rows)})
    finally:
        db.close()


def update_poa_activity(request: Request, activity_id: int, data: dict = Body(...)):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        admin_like = _is_request_admin_like(request, db)
        if not admin_like:
            return JSONResponse({"success": False, "error": "Solo administrador puede editar actividades"}, status_code=403)
        activity = db.query(POAActivity).filter(POAActivity.id == activity_id).first()
        if not activity:
            return JSONResponse({"success": False, "error": "Actividad no encontrada"}, status_code=404)
        allowed_ids = {obj.id for obj in _allowed_objectives_for_user(request, db)}
        if activity.objective_id not in allowed_ids and not admin_like:
            return JSONResponse({"success": False, "error": "No autorizado para editar esta actividad"}, status_code=403)
        nombre = (data.get("nombre") or "").strip()
        responsable = (data.get("responsable") or "").strip()
        entregable = (data.get("entregable") or "").strip()
        deliverables_input = data.get("entregables")
        normalized_deliverables = _normalize_deliverable_items(deliverables_input)
        if not normalized_deliverables and entregable:
            normalized_deliverables = [{"id": 0, "nombre": entregable, "validado": False, "orden": 1}]
        if not nombre or not normalized_deliverables:
            return JSONResponse(
                {"success": False, "error": "Nombre y al menos un entregable son obligatorios"},
                status_code=400,
            )
        start_date, start_error = _parse_date_field(data.get("fecha_inicial"), "Fecha inicial", required=True)
        if start_error:
            return JSONResponse({"success": False, "error": start_error}, status_code=400)
        end_date, end_error = _parse_date_field(data.get("fecha_final"), "Fecha final", required=True)
        if end_error:
            return JSONResponse({"success": False, "error": end_error}, status_code=400)
        range_error = _validate_date_range(start_date, end_date, "Actividad")
        if range_error:
            return JSONResponse({"success": False, "error": range_error}, status_code=400)
        recurrente = bool(data.get("recurrente"))
        periodicidad = (data.get("periodicidad") or "").strip().lower()
        try:
            cada_xx_dias = int(data.get("cada_xx_dias") or 0)
        except (TypeError, ValueError):
            return JSONResponse({"success": False, "error": "Cada xx días debe ser un número válido"}, status_code=400)
        if recurrente:
            if periodicidad not in VALID_ACTIVITY_PERIODICITIES:
                return JSONResponse({"success": False, "error": "Selecciona una periodicidad válida"}, status_code=400)
            if periodicidad == "cada_xx_dias":
                if cada_xx_dias <= 0:
                    return JSONResponse({"success": False, "error": "Cada xx días debe ser mayor a 0"}, status_code=400)
        else:
            periodicidad = ""
            cada_xx_dias = 0
        impacted_milestone_ids = _normalize_impacted_milestone_ids(data.get("impacted_milestone_ids"))
        objective = db.query(StrategicObjectiveConfig).filter(StrategicObjectiveConfig.id == activity.objective_id).first()
        if not objective:
            return JSONResponse({"success": False, "error": "Objetivo no encontrado"}, status_code=404)
        session_username = (getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "").strip()
        user = _current_user_record(request, db)
        aliases = _user_aliases(user, session_username)
        can_validate_deliverables = bool((objective.lider or "").strip().lower() in aliases) or admin_like
        if not can_validate_deliverables:
            normalized_deliverables = [{**item, "validado": False} for item in normalized_deliverables]
        valid_milestone_ids = {int(item.get("id") or 0) for item in _milestones_by_objective_ids(db, [int(objective.id)]).get(int(objective.id), [])}
        invalid_milestones = [mid for mid in impacted_milestone_ids if mid not in valid_milestone_ids]
        if invalid_milestones:
            return JSONResponse(
                {"success": False, "error": "Los hitos seleccionados no pertenecen al objetivo."},
                status_code=400,
            )
        parent_error = _validate_child_date_range(
            start_date,
            end_date,
            objective.fecha_inicial,
            objective.fecha_final,
            "Actividad",
            "Objetivo",
        )
        if parent_error:
            return JSONResponse({"success": False, "error": parent_error}, status_code=400)
        activity.nombre = nombre
        activity.codigo = (data.get("codigo") or "").strip()
        activity.responsable = responsable
        activity.entregable = str(normalized_deliverables[0].get("nombre") or "").strip()
        activity.fecha_inicial = start_date
        activity.fecha_final = end_date
        activity.inicio_forzado = bool(data.get("inicio_forzado")) if "inicio_forzado" in data else bool(activity.inicio_forzado)
        activity.descripcion = (data.get("descripcion") or "").strip()
        activity.recurrente = recurrente
        activity.periodicidad = periodicidad
        activity.cada_xx_dias = cada_xx_dias if periodicidad == "cada_xx_dias" else None
        db.add(activity)
        budget_rows: List[Dict[str, Any]] = []
        linked_milestones: List[Dict[str, Any]] = []
        deliverable_rows: List[Dict[str, Any]] = _replace_activity_deliverables(db, int(activity.id), normalized_deliverables)
        if "budget_items" in data:
            budget_rows = _replace_activity_budgets(db, int(activity.id), data.get("budget_items"))
        if "impacted_milestone_ids" in data:
            _replace_activity_milestone_links(db, int(activity.id), impacted_milestone_ids)
        db.commit()
        db.refresh(activity)
        subs = db.query(POASubactivity).filter(POASubactivity.activity_id == activity.id).all()
        if not budget_rows:
            budget_rows = _budgets_by_activity_ids(db, [int(activity.id)]).get(int(activity.id), [])
        if not deliverable_rows:
            deliverable_rows = _deliverables_by_activity_ids(db, [int(activity.id)]).get(int(activity.id), [])
        linked_milestones = _activity_milestones_by_activity_ids(db, [int(activity.id)]).get(int(activity.id), [])
        return JSONResponse({"success": True, "data": _serialize_poa_activity(activity, subs, budget_rows, linked_milestones, deliverable_rows)})
    finally:
        db.close()


def delete_poa_activity(request: Request, activity_id: int):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        admin_like = _is_request_admin_like(request, db)
        if not admin_like:
            return JSONResponse({"success": False, "error": "Solo administrador puede eliminar actividades"}, status_code=403)
        activity = db.query(POAActivity).filter(POAActivity.id == activity_id).first()
        if not activity:
            return JSONResponse({"success": False, "error": "Actividad no encontrada"}, status_code=404)
        allowed_ids = {obj.id for obj in _allowed_objectives_for_user(request, db)}
        if activity.objective_id not in allowed_ids and not admin_like:
            return JSONResponse({"success": False, "error": "No autorizado para eliminar esta actividad"}, status_code=403)
        db.query(POASubactivity).filter(POASubactivity.activity_id == activity.id).delete()
        _delete_activity_budgets(db, int(activity.id))
        _delete_activity_deliverables(db, int(activity.id))
        _delete_activity_milestone_links(db, int(activity.id))
        db.delete(activity)
        db.commit()
        return JSONResponse({"success": True})
    finally:
        db.close()


def mark_poa_activity_in_progress(request: Request, activity_id: int):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        admin_like = _is_request_admin_like(request, db)
        activity = db.query(POAActivity).filter(POAActivity.id == activity_id).first()
        if not activity:
            return JSONResponse({"success": False, "error": "Actividad no encontrada"}, status_code=404)
        allowed_ids = {obj.id for obj in _allowed_objectives_for_user(request, db)}
        if activity.objective_id not in allowed_ids and not admin_like:
            return JSONResponse({"success": False, "error": "No autorizado para esta actividad"}, status_code=403)
        session_username = (getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "").strip()
        user = _current_user_record(request, db)
        aliases = _user_aliases(user, session_username)
        is_activity_owner = (activity.responsable or "").strip().lower() in aliases
        if not is_activity_owner:
            return JSONResponse({"success": False, "error": "Solo el responsable puede habilitar en proceso"}, status_code=403)
        if (activity.entrega_estado or "").strip().lower() == "aprobada":
            return JSONResponse({"success": False, "error": "La actividad ya está aprobada y terminada"}, status_code=409)
        activity.inicio_forzado = True
        if (activity.entrega_estado or "").strip().lower() == "rechazada":
            activity.entrega_estado = "ninguna"
        db.add(activity)
        db.commit()
        db.refresh(activity)
        subs = db.query(POASubactivity).filter(POASubactivity.activity_id == activity.id).all()
        return JSONResponse({"success": True, "data": _serialize_poa_activity(activity, subs)})
    finally:
        db.close()


def mark_poa_activity_finished(request: Request, activity_id: int, data: dict = Body(default={})):
    _bind_core_symbols()
    send_review = bool(data.get("enviar_revision"))
    db = SessionLocal()
    try:
        admin_like = _is_request_admin_like(request, db)
        activity = db.query(POAActivity).filter(POAActivity.id == activity_id).first()
        if not activity:
            return JSONResponse({"success": False, "error": "Actividad no encontrada"}, status_code=404)
        allowed_ids = {obj.id for obj in _allowed_objectives_for_user(request, db)}
        if activity.objective_id not in allowed_ids and not admin_like:
            return JSONResponse({"success": False, "error": "No autorizado para esta actividad"}, status_code=403)
        session_username = (getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "").strip()
        user = _current_user_record(request, db)
        aliases = _user_aliases(user, session_username)
        is_activity_owner = (activity.responsable or "").strip().lower() in aliases
        if not is_activity_owner:
            return JSONResponse({"success": False, "error": "Solo el responsable puede declarar terminado"}, status_code=403)
        current_status = _activity_status(activity)
        if current_status == "No iniciada":
            return JSONResponse(
                {"success": False, "error": "La actividad no ha iniciado; habilítala en proceso o espera la fecha inicial"},
                status_code=409,
            )
        if (activity.entrega_estado or "").strip().lower() == "aprobada":
            return JSONResponse({"success": False, "error": "La actividad ya fue aprobada y terminada"}, status_code=409)

        if send_review:
            pending = (
                db.query(POADeliverableApproval)
                .filter(
                    POADeliverableApproval.activity_id == activity.id,
                    POADeliverableApproval.status == "pendiente",
                )
                .first()
            )
            if pending:
                return JSONResponse(
                    {"success": False, "error": "Ya existe una aprobación pendiente para esta actividad"},
                    status_code=409,
                )

            objective = db.query(StrategicObjectiveConfig).filter(StrategicObjectiveConfig.id == activity.objective_id).first()
            if not objective:
                return JSONResponse({"success": False, "error": "Objetivo no encontrado"}, status_code=404)
            axis = db.query(StrategicAxisConfig).filter(StrategicAxisConfig.id == objective.eje_id).first()
            process_owner = (activity.created_by or "").strip() or _resolve_process_owner_for_objective(objective, axis)
            if not process_owner:
                return JSONResponse(
                    {"success": False, "error": "No se pudo identificar el validador del entregable"},
                    status_code=400,
                )
            approval = POADeliverableApproval(
                activity_id=activity.id,
                objective_id=objective.id,
                process_owner=process_owner,
                requester=session_username or (activity.responsable or ""),
                status="pendiente",
            )
            activity.entrega_estado = "pendiente"
            activity.entrega_solicitada_por = session_username or (activity.responsable or "")
            activity.entrega_solicitada_at = datetime.utcnow()
            activity.entrega_aprobada_por = ""
            activity.entrega_aprobada_at = None
            db.add(approval)
            db.add(activity)
            db.commit()
            db.refresh(activity)
            subs = db.query(POASubactivity).filter(POASubactivity.activity_id == activity.id).all()
            return JSONResponse(
                {
                    "success": True,
                    "message": "Entregable enviado a revisión",
                    "data": _serialize_poa_activity(activity, subs),
                }
            )

        activity.entrega_estado = "declarada"
        activity.entrega_solicitada_por = ""
        activity.entrega_solicitada_at = None
        activity.entrega_aprobada_por = ""
        activity.entrega_aprobada_at = None
        db.add(activity)
        db.commit()
        db.refresh(activity)
        subs = db.query(POASubactivity).filter(POASubactivity.activity_id == activity.id).all()
        return JSONResponse(
            {
                "success": True,
                "message": "Actividad declarada terminada",
                "data": _serialize_poa_activity(activity, subs),
            }
        )
    finally:
        db.close()


def request_poa_activity_completion(request: Request, activity_id: int):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        admin_like = _is_request_admin_like(request, db)
        activity = db.query(POAActivity).filter(POAActivity.id == activity_id).first()
        if not activity:
            return JSONResponse({"success": False, "error": "Actividad no encontrada"}, status_code=404)
        allowed_ids = {obj.id for obj in _allowed_objectives_for_user(request, db)}
        if activity.objective_id not in allowed_ids and not admin_like:
            return JSONResponse({"success": False, "error": "No autorizado para esta actividad"}, status_code=403)
        session_username = (getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "").strip()
        user = _current_user_record(request, db)
        aliases = _user_aliases(user, session_username)
        is_activity_owner = (activity.responsable or "").strip().lower() in aliases
        if not is_activity_owner:
            return JSONResponse({"success": False, "error": "Solo el responsable puede solicitar terminación"}, status_code=403)
        if _activity_status(activity) == "No iniciada":
            return JSONResponse(
                {"success": False, "error": "La actividad no ha iniciado; no se puede solicitar terminación"},
                status_code=409,
            )
        if (activity.entrega_estado or "").strip().lower() == "aprobada":
            return JSONResponse({"success": False, "error": "La actividad ya fue aprobada y terminada"}, status_code=409)

        pending = (
            db.query(POADeliverableApproval)
            .filter(
                POADeliverableApproval.activity_id == activity.id,
                POADeliverableApproval.status == "pendiente",
            )
            .first()
        )
        if pending:
            return JSONResponse({"success": False, "error": "Ya existe una aprobación pendiente para esta actividad"}, status_code=409)

        objective = db.query(StrategicObjectiveConfig).filter(StrategicObjectiveConfig.id == activity.objective_id).first()
        if not objective:
            return JSONResponse({"success": False, "error": "Objetivo no encontrado"}, status_code=404)
        axis = db.query(StrategicAxisConfig).filter(StrategicAxisConfig.id == objective.eje_id).first()
        process_owner = (activity.created_by or "").strip() or _resolve_process_owner_for_objective(objective, axis)
        if not process_owner:
            return JSONResponse(
                {"success": False, "error": "No se pudo identificar dueño del proceso (líder objetivo/departamento eje)"},
                status_code=400,
            )

        approval = POADeliverableApproval(
            activity_id=activity.id,
            objective_id=objective.id,
            process_owner=process_owner,
            requester=session_username or (activity.responsable or ""),
            status="pendiente",
        )
        activity.entrega_estado = "pendiente"
        activity.entrega_solicitada_por = session_username or (activity.responsable or "")
        activity.entrega_solicitada_at = datetime.utcnow()
        activity.entrega_aprobada_por = ""
        activity.entrega_aprobada_at = None
        db.add(approval)
        db.add(activity)
        db.commit()
        return JSONResponse({"success": True, "message": "Solicitud de aprobación enviada al dueño del proceso"})
    finally:
        db.close()


def decide_poa_deliverable_approval(request: Request, approval_id: int, data: dict = Body(default={})):
    _bind_core_symbols()
    action = (data.get("accion") or "").strip().lower()
    if action not in {"autorizar", "rechazar"}:
        return JSONResponse({"success": False, "error": "Acción inválida. Usa autorizar o rechazar"}, status_code=400)
    comment = (data.get("comentario") or "").strip()

    db = SessionLocal()
    try:
        approval = db.query(POADeliverableApproval).filter(POADeliverableApproval.id == approval_id).first()
        if not approval:
            return JSONResponse({"success": False, "error": "Solicitud de aprobación no encontrada"}, status_code=404)
        if approval.status != "pendiente":
            return JSONResponse({"success": False, "error": "Esta solicitud ya fue resuelta"}, status_code=409)
        if not _is_user_process_owner(request, db, approval.process_owner):
            return JSONResponse({"success": False, "error": "No autorizado para resolver esta aprobación"}, status_code=403)

        activity = db.query(POAActivity).filter(POAActivity.id == approval.activity_id).first()
        if not activity:
            return JSONResponse({"success": False, "error": "Actividad no encontrada"}, status_code=404)
        resolver_user = (getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "").strip()

        approval.status = "autorizada" if action == "autorizar" else "rechazada"
        approval.comment = comment
        approval.resolved_by = resolver_user
        approval.resolved_at = datetime.utcnow()
        db.add(approval)

        if action == "autorizar":
            activity.entrega_estado = "aprobada"
            activity.entrega_aprobada_por = resolver_user
            activity.entrega_aprobada_at = datetime.utcnow()
        else:
            activity.entrega_estado = "rechazada"
            activity.entrega_aprobada_por = ""
            activity.entrega_aprobada_at = None
        db.add(activity)
        db.commit()
        return JSONResponse({"success": True, "message": "Aprobación procesada correctamente"})
    finally:
        db.close()


def create_poa_subactivity(request: Request, activity_id: int, data: dict = Body(...)):
    _bind_core_symbols()
    nombre = (data.get("nombre") or "").strip()
    responsable = (data.get("responsable") or "").strip()
    if not nombre:
        return JSONResponse({"success": False, "error": "Nombre es obligatorio"}, status_code=400)
    start_date, start_error = _parse_date_field(data.get("fecha_inicial"), "Fecha inicial", required=True)
    if start_error:
        return JSONResponse({"success": False, "error": start_error}, status_code=400)
    end_date, end_error = _parse_date_field(data.get("fecha_final"), "Fecha final", required=True)
    if end_error:
        return JSONResponse({"success": False, "error": end_error}, status_code=400)
    range_error = _validate_date_range(start_date, end_date, "Subactividad")
    if range_error:
        return JSONResponse({"success": False, "error": range_error}, status_code=400)
    recurrente = bool(data.get("recurrente"))
    periodicidad = (data.get("periodicidad") or "").strip().lower()
    try:
        cada_xx_dias = int(data.get("cada_xx_dias") or 0)
    except (TypeError, ValueError):
        return JSONResponse({"success": False, "error": "Cada xx dias debe ser un número válido"}, status_code=400)
    if recurrente:
        if periodicidad not in VALID_ACTIVITY_PERIODICITIES:
            return JSONResponse({"success": False, "error": "Selecciona una periodicidad válida"}, status_code=400)
        if periodicidad == "cada_xx_dias" and cada_xx_dias <= 0:
            return JSONResponse({"success": False, "error": "Cada xx dias debe ser mayor a 0"}, status_code=400)
    else:
        periodicidad = ""
        cada_xx_dias = 0

    db = SessionLocal()
    try:
        admin_like = _is_request_admin_like(request, db)
        if not admin_like:
            return JSONResponse({"success": False, "error": "Solo administrador puede crear subtareas"}, status_code=403)
        _ensure_poa_subactivity_recurrence_columns(db)
        activity = db.query(POAActivity).filter(POAActivity.id == activity_id).first()
        if not activity:
            return JSONResponse({"success": False, "error": "Actividad no encontrada"}, status_code=404)
        session_username = (getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "").strip()
        parent_error = _validate_child_date_range(
            start_date,
            end_date,
            activity.fecha_inicial,
            activity.fecha_final,
            "Subactividad",
            "Actividad",
        )
        if parent_error:
            return JSONResponse({"success": False, "error": parent_error}, status_code=400)
        parent_sub_id = int(data.get("parent_subactivity_id") or 0)
        parent_sub = None
        sub_level = 1
        if parent_sub_id:
            parent_sub = (
                db.query(POASubactivity)
                .filter(POASubactivity.id == parent_sub_id, POASubactivity.activity_id == activity.id)
                .first()
            )
            if not parent_sub:
                return JSONResponse({"success": False, "error": "Subactividad padre no encontrada"}, status_code=404)
            sub_level = int(parent_sub.nivel or 1) + 1
            if sub_level > MAX_SUBTASK_DEPTH:
                return JSONResponse(
                    {"success": False, "error": f"Profundidad máxima permitida: {MAX_SUBTASK_DEPTH} niveles"},
                    status_code=400,
                )
            child_error = _validate_child_date_range(
                start_date,
                end_date,
                parent_sub.fecha_inicial,
                parent_sub.fecha_final,
                "Subactividad",
                "Subactividad padre",
            )
            if child_error:
                return JSONResponse({"success": False, "error": child_error}, status_code=400)
        assigned_by = session_username
        sub = POASubactivity(
            activity_id=activity.id,
            parent_subactivity_id=parent_sub.id if parent_sub else None,
            nivel=sub_level,
            nombre=nombre,
            codigo=(data.get("codigo") or "").strip(),
            responsable=responsable,
            entregable=(data.get("entregable") or "").strip(),
            fecha_inicial=start_date,
            fecha_final=end_date,
            descripcion=(data.get("descripcion") or "").strip(),
            recurrente=recurrente,
            periodicidad=periodicidad,
            cada_xx_dias=(cada_xx_dias if periodicidad == "cada_xx_dias" else None),
            assigned_by=assigned_by,
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
        return JSONResponse({"success": True, "data": _serialize_poa_subactivity(sub)})
    finally:
        db.close()


def update_poa_subactivity(request: Request, subactivity_id: int, data: dict = Body(...)):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        admin_like = _is_request_admin_like(request, db)
        if not admin_like:
            return JSONResponse({"success": False, "error": "Solo administrador puede editar subtareas"}, status_code=403)
        _ensure_poa_subactivity_recurrence_columns(db)
        sub = db.query(POASubactivity).filter(POASubactivity.id == subactivity_id).first()
        if not sub:
            return JSONResponse({"success": False, "error": "Subactividad no encontrada"}, status_code=404)
        activity = db.query(POAActivity).filter(POAActivity.id == sub.activity_id).first()
        if not activity:
            return JSONResponse({"success": False, "error": "Actividad no encontrada"}, status_code=404)
        session_username = (getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "").strip()
        nombre = (data.get("nombre") or "").strip()
        responsable = (data.get("responsable") or "").strip()
        if not nombre:
            return JSONResponse({"success": False, "error": "Nombre es obligatorio"}, status_code=400)
        start_date, start_error = _parse_date_field(data.get("fecha_inicial"), "Fecha inicial", required=True)
        if start_error:
            return JSONResponse({"success": False, "error": start_error}, status_code=400)
        end_date, end_error = _parse_date_field(data.get("fecha_final"), "Fecha final", required=True)
        if end_error:
            return JSONResponse({"success": False, "error": end_error}, status_code=400)
        range_error = _validate_date_range(start_date, end_date, "Subactividad")
        if range_error:
            return JSONResponse({"success": False, "error": range_error}, status_code=400)
        recurrente = bool(data.get("recurrente"))
        periodicidad = (data.get("periodicidad") or "").strip().lower()
        try:
            cada_xx_dias = int(data.get("cada_xx_dias") or 0)
        except (TypeError, ValueError):
            return JSONResponse({"success": False, "error": "Cada xx dias debe ser un número válido"}, status_code=400)
        if recurrente:
            if periodicidad not in VALID_ACTIVITY_PERIODICITIES:
                return JSONResponse({"success": False, "error": "Selecciona una periodicidad válida"}, status_code=400)
            if periodicidad == "cada_xx_dias" and cada_xx_dias <= 0:
                return JSONResponse({"success": False, "error": "Cada xx dias debe ser mayor a 0"}, status_code=400)
        else:
            periodicidad = ""
            cada_xx_dias = 0
        parent_error = _validate_child_date_range(
            start_date,
            end_date,
            activity.fecha_inicial,
            activity.fecha_final,
            "Subactividad",
            "Actividad",
        )
        if parent_error:
            return JSONResponse({"success": False, "error": parent_error}, status_code=400)
        parent_sub = None
        if sub.parent_subactivity_id:
            parent_sub = (
                db.query(POASubactivity)
                .filter(POASubactivity.id == sub.parent_subactivity_id, POASubactivity.activity_id == activity.id)
                .first()
            )
        if parent_sub:
            child_error = _validate_child_date_range(
                start_date,
                end_date,
                parent_sub.fecha_inicial,
                parent_sub.fecha_final,
                "Subactividad",
                "Subactividad padre",
            )
            if child_error:
                return JSONResponse({"success": False, "error": child_error}, status_code=400)
        sub.nombre = nombre
        sub.codigo = (data.get("codigo") or "").strip()
        sub.responsable = responsable
        sub.entregable = (data.get("entregable") or "").strip()
        sub.fecha_inicial = start_date
        sub.fecha_final = end_date
        sub.descripcion = (data.get("descripcion") or "").strip()
        sub.recurrente = recurrente
        sub.periodicidad = periodicidad
        sub.cada_xx_dias = cada_xx_dias if periodicidad == "cada_xx_dias" else None
        db.add(sub)
        db.commit()
        db.refresh(sub)
        return JSONResponse({"success": True, "data": _serialize_poa_subactivity(sub)})
    finally:
        db.close()


def delete_poa_subactivity(request: Request, subactivity_id: int):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        admin_like = _is_request_admin_like(request, db)
        if not admin_like:
            return JSONResponse({"success": False, "error": "Solo administrador puede eliminar subtareas"}, status_code=403)
        _ensure_poa_subactivity_recurrence_columns(db)
        sub = db.query(POASubactivity).filter(POASubactivity.id == subactivity_id).first()
        if not sub:
            return JSONResponse({"success": False, "error": "Subactividad no encontrada"}, status_code=404)
        activity = db.query(POAActivity).filter(POAActivity.id == sub.activity_id).first()
        if not activity:
            return JSONResponse({"success": False, "error": "Actividad no encontrada"}, status_code=404)
        descendants = _descendant_subactivity_ids(db, activity.id, sub.id)
        if descendants:
            db.query(POASubactivity).filter(POASubactivity.id.in_(descendants)).delete(synchronize_session=False)
        db.delete(sub)
        db.commit()
        return JSONResponse({"success": True})
    finally:
        db.close()


def poa_subactivities_without_owner(request: Request):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        _ensure_poa_subactivity_recurrence_columns(db)
        objectives = _allowed_objectives_for_user(request, db)
        objective_ids = [obj.id for obj in objectives]
        if not objective_ids:
            return JSONResponse({"success": True, "total": 0, "data": []})
        activities = (
            db.query(POAActivity)
            .filter(POAActivity.objective_id.in_(objective_ids))
            .order_by(POAActivity.id.desc())
            .all()
        )
        if not activities:
            return JSONResponse({"success": True, "total": 0, "data": []})
        activity_ids = [int(item.id) for item in activities if getattr(item, "id", None)]
        activity_map = {int(item.id): item for item in activities if getattr(item, "id", None)}
        objective_map = {int(obj.id): obj for obj in objectives}
        subs = (
            db.query(POASubactivity)
            .filter(POASubactivity.activity_id.in_(activity_ids))
            .order_by(POASubactivity.id.desc())
            .all()
            if activity_ids
            else []
        )
        rows: List[Dict[str, Any]] = []
        for sub in subs:
            if str(sub.responsable or "").strip():
                continue
            activity = activity_map.get(int(sub.activity_id or 0))
            objective = objective_map.get(int(activity.objective_id or 0)) if activity else None
            rows.append(
                {
                    "subactivity_id": int(sub.id or 0),
                    "subactivity_nombre": str(sub.nombre or ""),
                    "subactivity_codigo": str(sub.codigo or ""),
                    "activity_id": int(sub.activity_id or 0),
                    "activity_nombre": str(getattr(activity, "nombre", "") or ""),
                    "activity_codigo": str(getattr(activity, "codigo", "") or ""),
                    "objective_id": int(getattr(activity, "objective_id", 0) or 0),
                    "objective_nombre": str(getattr(objective, "nombre", "") or ""),
                    "objective_codigo": str(getattr(objective, "codigo", "") or ""),
                    "nivel": int(sub.nivel or 1),
                    "fecha_inicial": _date_to_iso(sub.fecha_inicial),
                    "fecha_final": _date_to_iso(sub.fecha_final),
                }
            )
        return JSONResponse({"success": True, "total": len(rows), "data": rows})
    finally:
        db.close()
