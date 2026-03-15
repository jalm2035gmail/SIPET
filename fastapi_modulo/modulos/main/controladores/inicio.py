from __future__ import annotations

import json
from datetime import datetime, timedelta, date as Date
from html import escape
from typing import Any, Dict, List

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse


router = APIRouter()


@router.get("/inicio", response_class=HTMLResponse)
def inicio_page(request: Request):
    from fastapi_modulo import main as core
    from fastapi_modulo.modulos.planificacion.controladores.annual_cycle_service import get_active_operational_year
    from fastapi_modulo.modulos.presupuesto.modelos.presupuesto_dashboard_service import load_budget_summary
    from fastapi_modulo.modulos.proyectando.modelos.proyectando_dashboard_service import (
        load_projection_completion_summary,
    )

    perspective_defs = [
        {
            "key": "financiera",
            "title": "Financiera",
            "meaning": "Sostenibilidad y crecimiento",
            "keywords": ["financ", "presupuesto", "ingreso", "sostenib", "liquidez", "rentabil", "gasto", "cartera"],
        },
        {
            "key": "socios_clientes",
            "title": "Socios",
            "meaning": "Valor social y satisfacción",
            "keywords": ["socio", "cliente", "usuario", "satisf", "servicio", "experien", "cobertura", "valor social"],
        },
        {
            "key": "procesos_internos",
            "title": "Procesos",
            "meaning": "Eficiencia operativa",
            "keywords": ["proceso", "operativ", "eficien", "control", "cumpl", "calidad", "riesgo", "mejora"],
        },
        {
            "key": "aprendizaje_innovacion",
            "title": "Aprendizaje",
            "meaning": "Desarrollo institucional",
            "keywords": ["innov", "aprendiz", "talento", "digital", "capacit", "desarrollo", "cultura", "tecnolog"],
        },
    ]
    perspective_title_map = {item["key"]: item["title"] for item in perspective_defs}
    status_chip_map = {
        "No iniciada": ("gris", "No iniciado"),
        "En proceso": ("amarillo", "En proceso"),
        "En revisión": ("naranja", "En revisión"),
        "Terminada": ("verde", "Terminada"),
        "Atrasada": ("rojo", "Atrasada"),
    }

    def classify_perspective(text: str) -> str:
        blob = (text or "").lower()
        for item in perspective_defs:
            if any(token in blob for token in item["keywords"]):
                return item["key"]
        return "procesos_internos"

    def add_months(anchor: Date, delta: int) -> Date:
        idx = (anchor.month - 1) + delta
        year = anchor.year + (idx // 12)
        month = (idx % 12) + 1
        return datetime(year, month, 1).date()

    def month_end(month_start: Date) -> Date:
        return add_months(month_start, 1) - timedelta(days=1)

    metrics = {
        item["key"]: {"objectives": 0, "activities": 0, "progress_values": []}
        for item in perspective_defs
    }
    total_progress_values: List[int] = []
    total_objectives = 0
    total_activities = 0
    status_counts = {key: 0 for key in status_chip_map.keys()}
    risk_objective_rows: List[Dict[str, Any]] = []
    critical_activity_rows: List[Dict[str, Any]] = []
    objective_name_by_id: Dict[int, str] = {}
    tenant_id = core._normalize_tenant_id(core.get_current_tenant(request))

    db = core.SessionLocal()
    try:
        active_year = get_active_operational_year(db, tenant_id)
        axes = (
            db.query(core.StrategicAxisConfig)
            .filter(
                core.StrategicAxisConfig.tenant_id == tenant_id,
                core.StrategicAxisConfig.fiscal_year == active_year,
                core.StrategicAxisConfig.is_active == True,
            )
            .all()
        )
        axis_by_id = {int(axis.id): axis for axis in axes}
        objectives = (
            db.query(core.StrategicObjectiveConfig)
            .filter(
                core.StrategicObjectiveConfig.tenant_id == tenant_id,
                core.StrategicObjectiveConfig.fiscal_year == active_year,
                core.StrategicObjectiveConfig.is_active == True,
            )
            .all()
        )
        objective_ids = [int(obj.id) for obj in objectives]
        activities = (
            db.query(core.POAActivity)
            .filter(
                core.POAActivity.tenant_id == tenant_id,
                core.POAActivity.fiscal_year == active_year,
                core.POAActivity.objective_id.in_(objective_ids),
            )
            .all()
            if objective_ids
            else []
        )
        activity_ids = [int(activity.id) for activity in activities]
        subactivities = (
            db.query(core.POASubactivity)
            .filter(
                core.POASubactivity.tenant_id == tenant_id,
                core.POASubactivity.fiscal_year == active_year,
                core.POASubactivity.activity_id.in_(activity_ids),
            )
            .all()
            if activity_ids
            else []
        )
        sub_by_activity: Dict[int, List[Any]] = {}
        for sub in subactivities:
            sub_by_activity.setdefault(int(sub.activity_id), []).append(sub)

        now = datetime.utcnow().date()
        activity_progress_by_id: Dict[int, int] = {}
        activity_status_by_id: Dict[int, str] = {}
        activity_progress_by_objective: Dict[int, List[int]] = {}

        for activity in activities:
            subs = sub_by_activity.get(int(activity.id), [])
            status = core._activity_status(activity, now)
            if subs:
                done_subs = sum(1 for sub in subs if sub.fecha_final and sub.fecha_final <= now)
                progress = int(round((done_subs / len(subs)) * 100))
            else:
                progress = 100 if status == "Terminada" else 0
            activity_status_by_id[int(activity.id)] = status
            activity_progress_by_id[int(activity.id)] = progress
            status_counts[status] = status_counts.get(status, 0) + 1
            activity_progress_by_objective.setdefault(int(activity.objective_id), []).append(progress)

        for objective in objectives:
            axis = axis_by_id.get(int(objective.eje_id))
            axis_name = (axis.nombre if axis else "").strip() or "Sin eje"
            objective_name_by_id[int(objective.id)] = (objective.nombre or "").strip() or "Sin nombre"
            blob = " ".join(
                [
                    str(objective.nombre or ""),
                    str(getattr(objective, "hito", "") or ""),
                    str(objective.descripcion or ""),
                    str(axis_name),
                ]
            )
            perspective_key = classify_perspective(blob)
            progress_list = activity_progress_by_objective.get(int(objective.id), [])
            objective_progress = int(round(sum(progress_list) / len(progress_list))) if progress_list else 0

            metrics[perspective_key]["objectives"] += 1
            metrics[perspective_key]["activities"] += len(progress_list)
            metrics[perspective_key]["progress_values"].append(objective_progress)

            total_objectives += 1
            total_activities += len(progress_list)
            total_progress_values.append(objective_progress)

            due_days = 9999
            if objective.fecha_final:
                due_days = (objective.fecha_final - now).days
            if objective.fecha_final and objective.fecha_final < now and objective_progress < 100:
                objective_status = "rojo"
                objective_status_label = "Atrasado"
                risk_score = 100 + (100 - objective_progress)
            elif objective_progress < 60 and due_days <= 45:
                objective_status = "amarillo"
                objective_status_label = "En riesgo"
                risk_score = 60 + (60 - objective_progress)
            elif objective_progress < 30:
                objective_status = "amarillo"
                objective_status_label = "En riesgo"
                risk_score = 50 + (30 - objective_progress)
            else:
                objective_status = "verde"
                objective_status_label = "Controlado"
                risk_score = 0
            if risk_score > 0:
                risk_objective_rows.append(
                    {
                        "id": int(objective.id),
                        "nombre": objective_name_by_id[int(objective.id)],
                        "eje": axis_name,
                        "perspectiva": perspective_title_map.get(perspective_key, "Procesos"),
                        "lider": (objective.lider or "").strip()
                        or ((axis.lider_departamento or "").strip() if axis else "")
                        or "Sin líder",
                        "avance": objective_progress,
                        "status": objective_status,
                        "status_label": objective_status_label,
                        "fecha_fin": objective.fecha_final.isoformat() if objective.fecha_final else "Sin fecha",
                        "score": risk_score,
                    }
                )

        for activity in activities:
            status_name = activity_status_by_id.get(int(activity.id), "No iniciada")
            status_key, status_label = status_chip_map.get(status_name, ("gris", "No iniciado"))
            progress = activity_progress_by_id.get(int(activity.id), 0)
            due_days = 9999
            if activity.fecha_final:
                due_days = (activity.fecha_final - now).days

            score = 0
            if status_name == "Atrasada":
                score += 100
            elif status_name == "En revisión":
                score += 70
            elif status_name == "En proceso" and progress < 50 and due_days <= 30:
                score += 55
            elif status_name == "No iniciada" and due_days <= 15:
                score += 40
            score += max(0, 20 - min(20, progress // 5))
            if score > 0:
                start_label = activity.fecha_inicial.isoformat() if activity.fecha_inicial else "Sin inicio"
                end_label = activity.fecha_final.isoformat() if activity.fecha_final else "Sin fin"
                critical_activity_rows.append(
                    {
                        "id": int(activity.id),
                        "nombre": (activity.nombre or "").strip() or "Actividad sin nombre",
                        "periodo": f"{start_label} - {end_label}",
                        "objetivo": objective_name_by_id.get(int(activity.objective_id), "Sin objetivo"),
                        "responsable": (activity.responsable or "").strip() or "Sin responsable",
                        "avance": progress,
                        "entregables": 1 if (activity.entregable or "").strip() else 0,
                        "status": status_key,
                        "status_label": status_label,
                        "score": score,
                    }
                )
    finally:
        db.close()

    total_progress = int(round(sum(total_progress_values) / len(total_progress_values))) if total_progress_values else 0
    terminadas = status_counts.get("Terminada", 0)
    completion_ratio = int(round((terminadas / total_activities) * 100)) if total_activities else 0
    riesgo_count = (
        status_counts.get("Atrasada", 0)
        + status_counts.get("En revisión", 0)
        + status_counts.get("En proceso", 0)
    )

    budget_summary = load_budget_summary(tenant_id, active_year, completion_ratio)
    pres_ejecutado_pct = int(budget_summary["ejecutado_pct"])

    projection_summary = load_projection_completion_summary()

    objective_rows_html = []
    for row in sorted(risk_objective_rows, key=lambda item: item["score"], reverse=True)[:8]:
        objective_rows_html.append(
            f"""
            <tr>
              <td class="bscA__mono"><strong>{escape(row['nombre'])}</strong><div class="bscA__muted">{escape(row['eje'])}</div></td>
              <td><span class="bscA__pill">{escape(row['perspectiva'])}</span></td>
              <td>{escape(row['lider'])}</td>
              <td class="bscA__num">
                <div class="bscA__miniProgress"><div class="bscA__miniFill" style="width:{row['avance']}%"></div></div>
                <span>{row['avance']}%</span>
              </td>
              <td><span class="bscA__status" data-status="{escape(row['status'])}">{escape(row['status_label'])}</span></td>
              <td class="bscA__mono">{escape(row['fecha_fin'])}</td>
            </tr>
            """
        )
    if not objective_rows_html:
        objective_rows_html.append('<tr><td colspan="6" class="bscA__empty">Sin objetivos en riesgo en este momento.</td></tr>')

    activity_rows_html = []
    for row in sorted(critical_activity_rows, key=lambda item: item["score"], reverse=True)[:10]:
        activity_rows_html.append(
            f"""
            <tr>
              <td><strong>{escape(row['nombre'])}</strong><div class="bscA__muted">{escape(row['periodo'])}</div></td>
              <td class="bscA__muted">{escape(row['objetivo'])}</td>
              <td>{escape(row['responsable'])}</td>
              <td class="bscA__num">
                <div class="bscA__miniProgress"><div class="bscA__miniFill" style="width:{row['avance']}%"></div></div>
                <span>{row['avance']}%</span>
              </td>
              <td class="bscA__num">{row['entregables']}</td>
              <td><span class="bscA__status" data-status="{escape(row['status'])}">{escape(row['status_label'])}</span></td>
            </tr>
            """
        )
    if not activity_rows_html:
        activity_rows_html.append('<tr><td colspan="6" class="bscA__empty">Sin actividades críticas en este momento.</td></tr>')

    now = datetime.utcnow().date()
    month_anchor = now.replace(day=1)
    month_names = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    trend_labels: List[str] = []
    trend_expected: List[int] = []
    trend_real: List[int] = []

    if total_activities > 0:
        db = core.SessionLocal()
        try:
            objective_ids = [
                int(item.id)
                for item in db.query(core.StrategicObjectiveConfig)
                .filter(core.StrategicObjectiveConfig.is_active == True)
                .all()
            ]
            activities = (
                db.query(core.POAActivity).filter(core.POAActivity.objective_id.in_(objective_ids)).all()
                if objective_ids
                else []
            )
            for offset in range(-11, 1):
                ref_start = add_months(month_anchor, offset)
                ref_end = month_end(ref_start)
                trend_labels.append(f"{month_names[ref_start.month - 1]}-{str(ref_start.year)[-2:]}")
                expected_due = sum(1 for activity in activities if activity.fecha_final and activity.fecha_final <= ref_end)
                real_done = sum(
                    1
                    for activity in activities
                    if activity.fecha_final and activity.fecha_final <= ref_end and core._activity_status(activity, now) == "Terminada"
                )
                trend_expected.append(int(round((expected_due / len(activities)) * 100)) if activities else 0)
                trend_real.append(int(round((real_done / len(activities)) * 100)) if activities else 0)
        finally:
            db.close()
    else:
        for offset in range(-11, 1):
            ref_start = add_months(month_anchor, offset)
            trend_labels.append(f"{month_names[ref_start.month - 1]}-{str(ref_start.year)[-2:]}")
            trend_expected.append(0)
            trend_real.append(0)

    perspective_progress = []
    perspective_objectives = []
    for item in perspective_defs:
        data = metrics[item["key"]]
        avg_progress = int(round(sum(data["progress_values"]) / len(data["progress_values"]))) if data["progress_values"] else 0
        perspective_progress.append(avg_progress)
        perspective_objectives.append(int(data["objectives"]))

    donut_labels = ["No iniciado", "En proceso", "En revisión", "Terminada", "Atrasada"]
    donut_values = [
        status_counts.get("No iniciada", 0),
        status_counts.get("En proceso", 0),
        status_counts.get("En revisión", 0),
        status_counts.get("Terminada", 0),
        status_counts.get("Atrasada", 0),
    ]

    top_budget = list(budget_summary["top_budget"])
    budget_labels = [f"Rubro {item[0]}" for item in top_budget]
    budget_aprobado = [int(round(item[1])) for item in top_budget]
    budget_ejercido = [int(round(item[1] * (pres_ejecutado_pct / 100.0))) for item in top_budget]
    presupuesto_total = sum(budget_aprobado)
    presupuesto_ejercido = sum(budget_ejercido)

    charts_payload = {
        "trend": {"labels": trend_labels, "real": trend_real, "expected": trend_expected},
        "perspectives": {
            "labels": [item["title"] for item in perspective_defs],
            "avance": perspective_progress,
            "meta": [85, 85, 85, 85],
            "objetivos": perspective_objectives,
        },
        "status": {"labels": donut_labels, "values": donut_values},
        "budget": {"labels": budget_labels, "aprobado": budget_aprobado, "ejercido": budget_ejercido},
    }
    charts_payload_json = json.dumps(charts_payload, ensure_ascii=False).replace("</", "<\\/")
    year_value = now.year
    proyectando_filled = int(projection_summary["filled"])
    proyectando_total = int(projection_summary["total"])

    content = f"""
    <section class="bscA">
      <style>
        .bscA {{ width: 100%; padding: 32px; background: #f6f8fb; color: #0f172a; font-family: "Nunito Sans", "Inter", system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif; }}
        .bscA * {{ box-sizing: border-box; }}
        .bscA__header {{ display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; }}
        .bscA__header h1 {{ font-size: 30px; font-weight: 600; color: #0f172a; margin: 0; }}
        .bscA__titleRow {{ display: flex; align-items: center; gap: 16px; }}
        .bscA__titleIconWrap {{ width: 68px; height: 68px; border-radius: 18px; border: 2px solid #b8c8c4; background: #dbe5e1; display: inline-flex; align-items: center; justify-content: center; box-shadow: inset 0 1px 0 rgba(255,255,255,0.65); flex: 0 0 68px; }}
        .bscA__titleIconWrap img {{ width: 36px; height: 36px; object-fit: contain; display: block; opacity: 0.95; }}
        .bscA__header p {{ margin: 8px 0 0; color: #64748b; }}
        .bscA__filters {{ display: flex; gap: 10px; flex-wrap: wrap; }}
        .bscA__chip {{ background: #ffffff; border: 1px solid #e5e7eb; padding: 10px 12px; border-radius: 999px; color: #475569; box-shadow: 0 6px 18px rgba(15,23,42,.06); }}
        .bscA__kpis {{ margin-top: 22px; display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; }}
        .bscA__kpi {{ background: #fff; border: 1px solid #eef2f7; border-radius: 16px; padding: 18px; box-shadow: 0 10px 25px rgba(15,23,42,.06); transition: .2s; }}
        .bscA__kpi:hover {{ transform: translateY(-3px); }}
        .bscA__kpi span {{ color: #64748b; font-size: 13px; }}
        .bscA__kpi h2 {{ margin: 8px 0 2px; font-size: 32px; color: #0f172a; }}
        .bscA__kpi small {{ color: #94a3b8; }}
        .bscA__kpi--highlight {{ background: linear-gradient(135deg, #1e40af, #2563eb); border: none; }}
        .bscA__kpi--highlight span, .bscA__kpi--highlight h2, .bscA__kpi--highlight small {{ color: #fff; }}
        .bscA__grid {{ margin-top: 18px; display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: 16px; }}
        .bscA__card {{ grid-column: span 6; background: #fff; border: 1px solid #eef2f7; border-radius: 18px; box-shadow: 0 12px 28px rgba(15,23,42,.06); padding: 18px; min-height: 280px; }}
        .bscA__card--wide {{ grid-column: span 12; }}
        .bscA__cardHeader {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 12px; }}
        .bscA__cardHeader h3 {{ margin: 0; font-size: 16px; font-weight: 600; color: #0f172a; }}
        .bscA__cardHeader p {{ margin: 6px 0 0; color: #64748b; font-size: 13px; }}
        .bscA__badge {{ background: #f1f5f9; border: 1px solid #e2e8f0; padding: 8px 10px; border-radius: 999px; color: #475569; font-size: 12px; }}
        .bscA__btn {{ background: #0f172a; color: #fff; border: none; padding: 10px 12px; border-radius: 12px; cursor: pointer; }}
        .bscA__btn--ghost {{ background: #fff; color: #0f172a; border: 1px solid #e5e7eb; }}
        .bscA__chart {{ height: 220px; }}
        .bscA__chart--sm {{ height: 210px; }}
        .bscA__tableWrap {{ margin-top: 8px; overflow: auto; border-radius: 14px; border: 1px solid #eef2f7; }}
        .bscA__table {{ width: 100%; border-collapse: separate; border-spacing: 0; background: #fff; min-width: 690px; }}
        .bscA__table th {{ position: sticky; z-index: 1; top: 0; background: #f8fafc; color: #475569; text-align: left; font-size: 12px; font-weight: 600; padding: 12px 14px; border-bottom: 1px solid #eef2f7; white-space: nowrap; }}
        .bscA__table td {{ padding: 12px 14px; border-bottom: 1px solid #f1f5f9; color: #0f172a; font-size: 13px; vertical-align: middle; }}
        .bscA__table tr:last-child td {{ border-bottom: none; }}
        .bscA__muted {{ color: #64748b; font-size: 12px; margin-top: 4px; }}
        .bscA__mono {{ font-variant-numeric: tabular-nums; min-width: 210px; }}
        .bscA__num {{ white-space: nowrap; }}
        .bscA__pill {{ display: inline-flex; padding: 6px 10px; border-radius: 999px; background: #f1f5f9; border: 1px solid #e2e8f0; color: #334155; font-size: 12px; }}
        .bscA__status {{ display: inline-flex; padding: 6px 10px; border-radius: 999px; font-size: 12px; border: 1px solid #e2e8f0; background: #f8fafc; }}
        .bscA__status[data-status="gris"] {{ background: #eef2f7; border-color: #cbd5e1; color: #475569; }}
        .bscA__status[data-status="amarillo"] {{ background: #fffbeb; border-color: #fde68a; color: #92400e; }}
        .bscA__status[data-status="naranja"] {{ background: #ffedd5; border-color: #fdba74; color: #9a3412; }}
        .bscA__status[data-status="verde"] {{ background: #ecfdf5; border-color: #bbf7d0; color: #166534; }}
        .bscA__status[data-status="rojo"] {{ background: #fff1f2; border-color: #fecdd3; color: #9f1239; }}
        .bscA__miniProgress {{ width: 110px; height: 8px; background: #e2e8f0; border-radius: 99px; overflow: hidden; display: inline-block; vertical-align: middle; margin-right: 8px; }}
        .bscA__miniFill {{ height: 100%; background: linear-gradient(90deg, #16a34a, #22c55e); }}
        .bscA__empty {{ color:#64748b; text-align:center; font-style:italic; }}
        @media (max-width: 1280px) {{ .bscA__kpis {{ grid-template-columns:repeat(2, minmax(0,1fr)); }} .bscA__card, .bscA__card--wide {{ grid-column: span 12; }} }}
        @media (max-width: 780px) {{ .bscA__header {{ align-items:flex-start; flex-direction:column; }} .bscA__titleIconWrap {{ width: 56px; height: 56px; border-radius: 14px; flex-basis: 56px; }} .bscA__titleIconWrap img {{ width: 30px; height: 30px; }} .bscA__kpis {{ grid-template-columns: 1fr; }} .bscA__card, .bscA__card--wide {{ grid-column: span 12; }} }}
      </style>
      <div class="bscA__header">
        <div class="bscA__headerLeft">
          <div class="bscA__titleRow">
            <span class="bscA__titleIconWrap" aria-hidden="true"><img src="/templates/icon/tablero.svg" alt=""></span>
            <h1>Balanced Scorecard - Analítica</h1>
          </div>
          <p>Gráficas, tendencias y control ejecutivo (objetivos + POA + presupuesto + proyectando)</p>
        </div>
        <div class="bscA__filters">
          <div class="bscA__chip">Año: <strong>{year_value}</strong></div>
          <div class="bscA__chip">Periodo: <strong>Ene-Dic</strong></div>
          <div class="bscA__chip">Eje: <strong>Todos</strong></div>
        </div>
      </div>
      <div class="bscA__kpis">
        <div class="bscA__kpi"><span>Avance global</span><h2>{total_progress}%</h2><small>Meta: 85%</small></div>
        <div class="bscA__kpi"><span>Objetivos</span><h2>{total_objectives}</h2><small>Activos</small></div>
        <div class="bscA__kpi"><span>Actividades POA</span><h2>{total_activities}</h2><small>Totales</small></div>
        <div class="bscA__kpi"><span>En riesgo</span><h2>{riesgo_count}</h2><small>Semáforo rojo/amarillo</small></div>
        <div class="bscA__kpi bscA__kpi--highlight"><span>Ejecución presupuestal</span><h2>{pres_ejecutado_pct}%</h2><small>Ejercido / Aprobado</small></div>
      </div>
      <div class="bscA__grid">
        <article class="bscA__card bscA__card--wide bscA__card--trend"><div class="bscA__cardHeader"><div><h3>Tendencia estratégica (mensual)</h3><p>Avance global vs avance esperado</p></div><div class="bscA__badge">Últimos 12 meses</div></div><div class="bscA__chart"><canvas id="bscATrend"></canvas></div></article>
        <article class="bscA__card bscA__card--radar"><div class="bscA__cardHeader"><div><h3>Balance por perspectiva</h3><p>Radar del BSC (4 perspectivas)</p></div></div><div class="bscA__chart bscA__chart--sm"><canvas id="bscARadar"></canvas></div></article>
        <article class="bscA__card bscA__card--bars"><div class="bscA__cardHeader"><div><h3>Avance por perspectiva</h3><p>Comparativo y cumplimiento meta</p></div></div><div class="bscA__chart bscA__chart--sm"><canvas id="bscABars"></canvas></div></article>
        <article class="bscA__card bscA__card--donut"><div class="bscA__cardHeader"><div><h3>Estados POA</h3><p>No iniciado / En proceso / Revisión / Terminado / Atrasado</p></div></div><div class="bscA__chart bscA__chart--sm"><canvas id="bscADonut"></canvas></div></article>
        <article class="bscA__card bscA__card--budget"><div class="bscA__cardHeader"><div><h3>Presupuesto por rubro</h3><p>Aprobado vs ejercido (top rubros)</p></div><div class="bscA__badge">{presupuesto_total:,.0f} aprobado / {presupuesto_ejercido:,.0f} ejercido</div></div><div class="bscA__chart bscA__chart--sm"><canvas id="bscABudget"></canvas></div></article>
        <article class="bscA__card bscA__card--wide bscA__card--risk"><div class="bscA__cardHeader"><div><h3>Objetivos en riesgo</h3><p>Prioridad directiva (impacto + atraso + avance)</p></div><button class="bscA__btn" type="button">Ver todos</button></div><div class="bscA__tableWrap"><table class="bscA__table"><thead><tr><th>Objetivo</th><th>Perspectiva</th><th>Líder</th><th>Avance</th><th>Estado</th><th>Fecha fin</th></tr></thead><tbody>{"".join(objective_rows_html)}</tbody></table></div></article>
        <article class="bscA__card bscA__card--wide bscA__card--activities"><div class="bscA__cardHeader"><div><h3>Actividades POA críticas</h3><p>Top actividades por atraso o revisión pendiente</p></div><div class="bscA__badge">{proyectando_filled}/{proyectando_total} proyectando</div></div><div class="bscA__tableWrap"><table class="bscA__table"><thead><tr><th>Actividad</th><th>Objetivo</th><th>Responsable</th><th>Avance</th><th>Entregables</th><th>Estado</th></tr></thead><tbody>{"".join(activity_rows_html)}</tbody></table></div></article>
      </div>
      <script type="application/json" id="bscAData">{charts_payload_json}</script>
      <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
      <script src="/static/js/bsc_dashboard_analytics.js"></script>
      <script>
        (function() {{
          if (!window.Chart || !window.BscDashboardAnalytics) return;
          const payloadNode = document.getElementById("bscAData");
          if (!payloadNode) return;
          const payload = JSON.parse(payloadNode.textContent || "{{}}");
          const dashboard = new window.BscDashboardAnalytics({{
            state: {{ year: {year_value}, periodLabel: "Ene-Dic", axisLabel: "Todos", kpis: {{ global: {total_progress}, metaGlobal: 85, objetivos: {total_objectives}, actividades: {total_activities}, riesgo: {riesgo_count}, presEjecutado: {pres_ejecutado_pct} }} }},
            payload: payload,
            refs: {{ trendCanvas: document.getElementById("bscATrend"), radarCanvas: document.getElementById("bscARadar"), barsCanvas: document.getElementById("bscABars"), donutCanvas: document.getElementById("bscADonut"), budgetCanvas: document.getElementById("bscABudget") }}
          }});
          dashboard.mount();
        }})();
      </script>
    </section>
    """
    return core.render_backend_page(
        request,
        title="Inicio",
        description="Balanced Scorecard",
        content=content,
        hide_floating_actions=True,
        show_page_header=True,
    )


@router.get("/mi-tablero", response_class=HTMLResponse)
def mi_tablero_page(request: Request):
    from fastapi_modulo import main as core

    user_access = set(core._get_user_app_access(request))
    visible_modules = []
    for module in core.list_modules_payload():
        route = str(module.get("route") or "").strip()
        app_access_name = str(module.get("app_access_name") or "").strip()
        if not route or route == "/mi-tablero" or not bool(module.get("enabled")):
            continue
        if app_access_name and not core.is_superadmin(request) and app_access_name not in user_access:
            continue
        visible_modules.append(
            {
                "label": str(module.get("label") or "Modulo").strip() or "Modulo",
                "description": str(module.get("description") or "").strip(),
                "route": route,
            }
        )

    cards_html = "".join(
        f"""
        <a href="{escape(item['route'])}" style="display:block;text-decoration:none;color:inherit;">
            <article style="height:100%;border:1px solid rgba(15,23,42,.08);border-radius:18px;padding:20px;background:linear-gradient(180deg,#ffffff 0%,#f8fafc 100%);box-shadow:0 18px 45px rgba(15,23,42,.06);">
                <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:14px;">
                    <h3 style="margin:0;font-size:18px;font-weight:800;color:#0f172a;">{escape(item['label'])}</h3>
                    <span style="display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:999px;background:#dcfce7;color:#166534;font-size:18px;font-weight:800;">&rarr;</span>
                </div>
                <p style="margin:0;color:#475569;font-size:14px;line-height:1.5;">{escape(item['description'] or 'Acceso rapido al modulo.')}</p>
            </article>
        </a>
        """
        for item in visible_modules
    )
    no_modules_html = """
    <article style="border:1px dashed rgba(15,23,42,.18);border-radius:18px;padding:28px;background:#ffffff;text-align:center;">
        <h3 style="margin:0 0 10px;font-size:20px;font-weight:800;color:#0f172a;">Sin modulos disponibles</h3>
        <p style="margin:0;color:#475569;font-size:14px;line-height:1.6;">Este usuario no tiene accesos directos asignados en este momento.</p>
    </article>
    """
    quick_links_html = cards_html or no_modules_html
    content = f"""
    <section style="width:100%;min-height:70vh;padding:8px 0 24px;box-sizing:border-box;">
        <div style="display:grid;gap:18px;">
            <article style="border-radius:24px;padding:28px;background:linear-gradient(135deg,#0f172a 0%,#14532d 100%);color:#ffffff;box-shadow:0 24px 60px rgba(15,23,42,.16);">
                <span style="display:inline-flex;align-items:center;gap:8px;padding:8px 14px;border-radius:999px;background:rgba(255,255,255,.14);font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;">Mi tablero</span>
                <h2 style="margin:14px 0 10px;font-size:32px;line-height:1.1;">Accesos rapidos del sistema</h2>
                <p style="margin:0;max-width:720px;color:rgba(255,255,255,.84);font-size:15px;line-height:1.65;">Centraliza los modulos habilitados para tu perfil y entra directo a las vistas operativas principales.</p>
            </article>
            <section style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;">
                {quick_links_html}
            </section>
        </div>
    </section>
    """
    return core.render_backend_page(
        request,
        title="Mi tablero",
        description="Resumen personal y accesos directos.",
        content=content,
        hide_floating_actions=True,
        show_page_header=False,
    )
