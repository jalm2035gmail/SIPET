from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Set

from fastapi import Body, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, text

from fastapi_modulo.modulos.planificacion.modelos.kpis_service import _ensure_kpi_mediciones_table, _kpi_evaluate_status

_CORE_BOUND = False


def _bind_core_symbols() -> None:
    global _CORE_BOUND
    if _CORE_BOUND:
        return
    from fastapi_modulo import main as core

    names = [
        "SessionLocal",
        "POADeliverableApproval",
        "POAActivity",
        "POASubactivity",
        "StrategicObjectiveConfig",
        "DocumentoEvidencia",
        "PublicQuizSubmission",
        "UserNotificationRead",
        "_notification_user_key",
        "_normalize_tenant_id",
        "get_current_tenant",
        "_is_user_process_owner",
        "is_superadmin",
        "_current_user_record",
        "_user_aliases",
        "_activity_status",
    ]
    for name in names:
        globals()[name] = getattr(core, name)
    _CORE_BOUND = True


def _get_document_tenant(request: Request) -> str:
    _bind_core_symbols()
    return _normalize_tenant_id(get_current_tenant(request))


def notifications_summary(request: Request):
    _bind_core_symbols()
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        today = now.date()
        tenant_id = _normalize_tenant_id(get_current_tenant(request))
        user_key = _notification_user_key(request, db)
        items: List[Dict[str, Any]] = []

        pending_approvals = (
            db.query(POADeliverableApproval)
            .filter(POADeliverableApproval.status == "pendiente")
            .order_by(POADeliverableApproval.created_at.desc())
            .all()
        )
        for approval in pending_approvals:
            if not _is_user_process_owner(request, db, approval.process_owner):
                continue
            activity = db.query(POAActivity).filter(POAActivity.id == approval.activity_id).first()
            objective = db.query(StrategicObjectiveConfig).filter(StrategicObjectiveConfig.id == approval.objective_id).first()
            items.append(
                {
                    "id": f"poa-approval-{approval.id}",
                    "kind": "poa_aprobacion",
                    "title": "Aprobación de entregable pendiente",
                    "message": (
                        f"Actividad {(activity.nombre if activity else 'sin nombre')} "
                        f"({activity.codigo if activity else ''}) - Objetivo {(objective.nombre if objective else '')}"
                    ).strip(),
                    "created_at": (approval.created_at or now).isoformat(),
                    "href": "/poa/crear",
                }
            )

        try:
            document_tenant = _get_document_tenant(request)
            docs_query = db.query(DocumentoEvidencia).filter(DocumentoEvidencia.estado.in_(["enviado", "actualizado"]))
            if is_superadmin(request):
                header_tenant = request.headers.get("x-tenant-id")
                if header_tenant and _normalize_tenant_id(header_tenant) != "all":
                    docs_query = docs_query.filter(
                        func.lower(DocumentoEvidencia.tenant_id) == _normalize_tenant_id(header_tenant).lower()
                    )
                elif not header_tenant:
                    docs_query = docs_query.filter(func.lower(DocumentoEvidencia.tenant_id) == document_tenant.lower())
            else:
                docs_query = docs_query.filter(func.lower(DocumentoEvidencia.tenant_id) == document_tenant.lower())
            docs_pending = docs_query.order_by(DocumentoEvidencia.updated_at.desc()).limit(20).all()
            for doc in docs_pending:
                items.append(
                    {
                        "id": f"doc-approval-{doc.id}",
                        "kind": "documento_autorizacion",
                        "title": "Documento pendiente de autorización",
                        "message": f"{(doc.titulo or '').strip()} · Estado: {(doc.estado or '').strip()}",
                        "created_at": (doc.updated_at or doc.enviado_at or doc.creado_at or now).isoformat(),
                        "href": "/reportes/documentos",
                    }
                )
        except Exception:
            db.rollback()

        if is_superadmin(request):
            quiz_rows = (
                db.query(PublicQuizSubmission)
                .order_by(PublicQuizSubmission.created_at.desc(), PublicQuizSubmission.id.desc())
                .limit(20)
                .all()
            )
            for quiz in quiz_rows:
                items.append(
                    {
                        "id": f"quiz-submission-{quiz.id}",
                        "kind": "quiz_descuento",
                        "title": "Nuevo cuestionario de descuento",
                        "message": (
                            f"{(quiz.nombre or '').strip()} · {(quiz.cooperativa or '').strip()} · "
                            f"{int(quiz.correctas or 0)}/10 correctas · {int(quiz.descuento or 0)}% de descuento"
                        ),
                        "created_at": (quiz.created_at or now).isoformat(),
                        "href": "/usuarios",
                    }
                )

        session_username = (getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "").strip()
        user = _current_user_record(request, db)
        aliases = sorted(_user_aliases(user, session_username))
        if aliases:
            lookahead = today + timedelta(days=2)
            own_activities = (
                db.query(POAActivity)
                .filter(func.lower(POAActivity.responsable).in_(aliases))
                .order_by(POAActivity.fecha_final.asc(), POAActivity.id.asc())
                .all()
            )
            for activity in own_activities:
                if not activity.fecha_final:
                    continue
                if (activity.entrega_estado or "").strip().lower() == "aprobada":
                    continue
                if activity.fecha_final > lookahead:
                    continue
                delta_days = (activity.fecha_final - today).days
                if delta_days < 0:
                    title = "Tarea atrasada"
                    message = f"{activity.nombre} está atrasada desde {activity.fecha_final.isoformat()}"
                    deadline_state = "atrasada"
                elif delta_days == 0:
                    title = "Actividad vence hoy"
                    message = f"{activity.nombre} vence hoy"
                    deadline_state = "por_vencer"
                else:
                    title = "Actividad por vencer"
                    message = f"{activity.nombre} vence el {activity.fecha_final.isoformat()}"
                    deadline_state = "por_vencer"
                items.append(
                    {
                        "id": f"activity-deadline-{activity.id}",
                        "kind": "actividad_fecha",
                        "title": title,
                        "message": message,
                        "deadline_state": deadline_state,
                        "created_at": datetime.combine(activity.fecha_final, datetime.min.time()).isoformat(),
                        "href": "/poa/crear",
                    }
                )
            own_subactivities = (
                db.query(POASubactivity, POAActivity)
                .join(POAActivity, POAActivity.id == POASubactivity.activity_id)
                .filter(func.lower(POASubactivity.responsable).in_(aliases))
                .order_by(POASubactivity.fecha_final.asc(), POASubactivity.id.asc())
                .all()
            )
            for subactivity, parent_activity in own_subactivities:
                if not subactivity.fecha_final:
                    continue
                if _activity_status(parent_activity, today=today) == "Terminada":
                    continue
                if subactivity.fecha_final > lookahead:
                    continue
                delta_days = (subactivity.fecha_final - today).days
                if delta_days < 0:
                    title = "Tarea atrasada"
                    message = (
                        f"{subactivity.nombre} (subtarea de {parent_activity.nombre}) "
                        f"está atrasada desde {subactivity.fecha_final.isoformat()}"
                    )
                    deadline_state = "atrasada"
                elif delta_days == 0:
                    title = "Subtarea vence hoy"
                    message = f"{subactivity.nombre} vence hoy"
                    deadline_state = "por_vencer"
                else:
                    title = "Subtarea por vencer"
                    message = f"{subactivity.nombre} vence el {subactivity.fecha_final.isoformat()}"
                    deadline_state = "por_vencer"
                items.append(
                    {
                        "id": f"subactivity-deadline-{subactivity.id}",
                        "kind": "actividad_fecha",
                        "title": title,
                        "message": message,
                        "deadline_state": deadline_state,
                        "created_at": datetime.combine(subactivity.fecha_final, datetime.min.time()).isoformat(),
                        "href": f"/poa/crear?activity_id={int(parent_activity.id or 0)}&subactivity_id={int(subactivity.id or 0)}",
                    }
                )

        try:
            db.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS ia_poa_risk_alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        alert_key TEXT NOT NULL UNIQUE,
                        activity_id INTEGER,
                        objective_id INTEGER,
                        axis_id INTEGER,
                        severity TEXT NOT NULL,
                        risk_score REAL NOT NULL DEFAULT 0,
                        status TEXT NOT NULL DEFAULT 'active',
                        owner TEXT DEFAULT '',
                        title TEXT NOT NULL DEFAULT '',
                        message TEXT NOT NULL DEFAULT '',
                        recommendation TEXT NOT NULL DEFAULT '',
                        source TEXT NOT NULL DEFAULT 'ia_risk_engine',
                        resolved_at TEXT DEFAULT ''
                    )
                    """
                )
            )
            db.commit()
            alerts_rows = db.execute(
                text(
                    """
                    SELECT id, created_at, updated_at, severity, risk_score, title, message, recommendation
                    FROM ia_poa_risk_alerts
                    WHERE source = 'ia_risk_engine' AND status = 'active'
                    ORDER BY
                        CASE severity WHEN 'high' THEN 3 WHEN 'medium' THEN 2 WHEN 'low' THEN 1 ELSE 0 END DESC,
                        risk_score DESC,
                        updated_at DESC
                    LIMIT 20
                    """
                )
            ).fetchall()
            for row in alerts_rows:
                severity = str(row.severity or "").strip().lower()
                severity_label = "alto" if severity == "high" else ("medio" if severity == "medium" else "bajo")
                created_at_raw = str(row.updated_at or row.created_at or now.isoformat()).strip() or now.isoformat()
                items.append(
                    {
                        "id": f"ia-poa-risk-{int(row.id or 0)}",
                        "kind": "ia_riesgo_poa",
                        "title": str(row.title or "Alerta IA de riesgo POA").strip(),
                        "message": (
                            f"{str(row.message or '').strip()} · Riesgo {severity_label} · "
                            f"Recomendación: {str(row.recommendation or '').strip()}"
                        ).strip(" ·"),
                        "created_at": created_at_raw,
                        "href": "/poa/crear",
                    }
                )
        except Exception:
            db.rollback()

        try:
            _ensure_kpi_mediciones_table(db)
            kpi_alert_rows = db.execute(
                text(
                    """
                SELECT k.id, k.nombre, k.estandar, k.referencia,
                       m.valor, m.periodo, m.created_at
                FROM strategic_objective_kpis k
                INNER JOIN kpi_mediciones m ON m.id = (
                    SELECT id FROM kpi_mediciones
                    WHERE kpi_id = k.id ORDER BY created_at DESC LIMIT 1
                )
                WHERE k.estandar != '' AND k.referencia != ''
            """
                )
            ).fetchall()
            for krow in kpi_alert_rows:
                kpi_id_v = int(krow[0])
                nombre_v = str(krow[1] or "")
                estandar_v = str(krow[2] or "")
                refx_v = str(krow[3] or "")
                valor_v = float(krow[4] or 0)
                periodo_v = str(krow[5] or "")
                med_at_v = str(krow[6] or "")
                kpi_status = _kpi_evaluate_status(valor_v, estandar_v, refx_v)
                if kpi_status in ("alert", "warning"):
                    sev_label = "Alerta" if kpi_status == "alert" else "Advertencia"
                    items.append(
                        {
                            "id": f"kpi-alerta-{kpi_id_v}",
                            "kind": "kpi_alerta",
                            "severity": kpi_status,
                            "title": f"{sev_label} KPI: {nombre_v}",
                            "message": (
                                f"Valor: {valor_v} · Meta ({estandar_v}): {refx_v}"
                                + (f" · Período: {periodo_v}" if periodo_v else "")
                            ),
                            "created_at": med_at_v or now.isoformat(),
                            "href": "/inicio/kpis",
                        }
                    )
        except Exception:
            db.rollback()

        items.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        limited_items = items[:25]
        notification_ids = [str(item.get("id") or "").strip() for item in limited_items if str(item.get("id") or "").strip()]
        read_ids: Set[str] = set()
        if user_key and notification_ids:
            read_rows = (
                db.query(UserNotificationRead.notification_id)
                .filter(
                    UserNotificationRead.tenant_id == tenant_id,
                    UserNotificationRead.user_key == user_key,
                    UserNotificationRead.notification_id.in_(notification_ids),
                )
                .all()
            )
            read_ids = {str(row[0]) for row in read_rows}
        for item in limited_items:
            item["read"] = str(item.get("id") or "") in read_ids

        counts = {
            "poa_aprobacion": 0,
            "documento_autorizacion": 0,
            "actividad_fecha": 0,
            "actividad_atrasada": 0,
            "actividad_por_vencer": 0,
            "quiz_descuento": 0,
            "ia_riesgo_poa": 0,
            "kpi_alerta": 0,
            "kpi_advertencia": 0,
        }
        for item in limited_items:
            kind = str(item.get("kind") or "")
            is_unread = not bool(item.get("read"))
            if kind in counts:
                counts[kind] += 1 if is_unread else 0
            if kind == "actividad_fecha" and is_unread:
                deadline_state = str(item.get("deadline_state") or "").strip().lower()
                if deadline_state == "atrasada":
                    counts["actividad_atrasada"] += 1
                elif deadline_state == "por_vencer":
                    counts["actividad_por_vencer"] += 1
            if kind == "kpi_alerta" and is_unread:
                severity = str(item.get("severity") or "").strip().lower()
                if severity == "alert":
                    counts["kpi_alerta"] += 1
                elif severity == "warning":
                    counts["kpi_advertencia"] += 1
        unread = sum(0 if item.get("read") else 1 for item in limited_items)

        return JSONResponse(
            {
                "success": True,
                "total": len(limited_items),
                "unread": unread,
                "counts": counts,
                "items": limited_items,
            }
        )
    finally:
        db.close()


def mark_notification_read(request: Request, data: dict = Body(default={})):
    _bind_core_symbols()
    notification_id = (data.get("id") or "").strip()
    if not notification_id:
        return JSONResponse({"success": False, "error": "ID de notificación requerido"}, status_code=400)

    db = SessionLocal()
    try:
        tenant_id = _normalize_tenant_id(get_current_tenant(request))
        user_key = _notification_user_key(request, db)
        if not user_key:
            return JSONResponse({"success": False, "error": "Usuario no autenticado"}, status_code=401)

        row = (
            db.query(UserNotificationRead)
            .filter(
                UserNotificationRead.tenant_id == tenant_id,
                UserNotificationRead.user_key == user_key,
                UserNotificationRead.notification_id == notification_id,
            )
            .first()
        )
        if row:
            row.read_at = datetime.utcnow()
            db.add(row)
        else:
            db.add(
                UserNotificationRead(
                    tenant_id=tenant_id,
                    user_key=user_key,
                    notification_id=notification_id,
                    read_at=datetime.utcnow(),
                )
            )
        db.commit()
        return JSONResponse({"success": True})
    finally:
        db.close()


def mark_all_notifications_read(request: Request, data: dict = Body(default={})):
    _bind_core_symbols()
    raw_ids = data.get("ids")
    ids = [str(value).strip() for value in (raw_ids if isinstance(raw_ids, list) else [])]
    ids = [value for value in ids if value][:200]

    db = SessionLocal()
    try:
        tenant_id = _normalize_tenant_id(get_current_tenant(request))
        user_key = _notification_user_key(request, db)
        if not user_key:
            return JSONResponse({"success": False, "error": "Usuario no autenticado"}, status_code=401)
        if not ids:
            return JSONResponse({"success": True, "updated": 0})

        existing = (
            db.query(UserNotificationRead)
            .filter(
                UserNotificationRead.tenant_id == tenant_id,
                UserNotificationRead.user_key == user_key,
                UserNotificationRead.notification_id.in_(ids),
            )
            .all()
        )
        existing_by_id = {row.notification_id: row for row in existing}
        now = datetime.utcnow()
        updates = 0
        for notif_id in ids:
            row = existing_by_id.get(notif_id)
            if row:
                row.read_at = now
                db.add(row)
            else:
                db.add(
                    UserNotificationRead(
                        tenant_id=tenant_id,
                        user_key=user_key,
                        notification_id=notif_id,
                        read_at=now,
                    )
                )
            updates += 1
        db.commit()
        return JSONResponse({"success": True, "updated": updates})
    finally:
        db.close()
