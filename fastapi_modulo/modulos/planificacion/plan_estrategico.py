import json
from datetime import date, datetime
from html import escape
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from fastapi_modulo.modulos.planificacion import plan_estrategico_service as strategic_api
from fastapi_modulo.modulos.planificacion import poa_service

router = APIRouter()

_PLAN_ESTRATEGICO_TEMPLATE_PATH = Path(__file__).with_name("plan_estrategico.html")
_PLAN_ESTRATEGICO_JS_PATH = Path(__file__).with_name("plan_estrategico.js")
_PLAN_ESTRATEGICO_CSS_PATH = Path(__file__).with_name("plan_estrategico.css")
_PLAN_ESTRATEGICO_TABLERO_TEMPLATE = """
<section class="poa-dashboard-page">
  <div class="poa-dashboard-wrap">
    <header class="poa-main-header">
      <div class="poa-main-top">
        <div class="poa-brand">
          <div class="poa-brand-logo">
            <i class="fa-solid fa-compass-drafting" aria-hidden="true"></i>
          </div>
          <div>
            <h1 class="poa-brand-title">SIPET - Sistema de planeación estratética y táctica</h1>
            <p class="poa-brand-subtitle">Tablero ejecutivo del plan estratégico</p>
          </div>
        </div>
        <div class="poa-user-tools">
          <button type="button" class="poa-icon-btn" aria-label="Historial">
            <i class="fa-solid fa-clock-rotate-left" aria-hidden="true"></i>
          </button>
          <button type="button" class="poa-icon-btn" aria-label="Notificaciones">
            <i class="fa-solid fa-bell" aria-hidden="true"></i>
          </button>
          <div class="poa-avatar poa-avatar-initials" aria-hidden="true">JP</div>
        </div>
      </div>
      <div class="poa-tabs" role="tablist" aria-label="Vistas del tablero">
        <button type="button" class="poa-tab active">Tabla</button>
        <button type="button" class="poa-tab">Kanban</button>
        <button type="button" class="poa-tab">Timeline</button>
        <button type="button" class="poa-tab">Dashboard</button>
        <button type="button" class="poa-tab">Presupuesto</button>
      </div>
      <div class="poa-filters">
        <div class="poa-filter">
          <label for="planes-dashboard-area">Área</label>
          <select id="planes-dashboard-area" class="poa-select">
            <option>Todas</option>
            <option>Planeación</option>
            <option>Finanzas</option>
            <option>Obras públicas</option>
          </select>
        </div>
        <div class="poa-filter">
          <label for="planes-dashboard-responsable">Responsable</label>
          <select id="planes-dashboard-responsable" class="poa-select">
            <option>Todos</option>
            <option>Ana López</option>
            <option>Luis Pérez</option>
            <option>Juan Ruiz</option>
          </select>
        </div>
        <div class="poa-filter">
          <label for="planes-dashboard-trimestre">Trimestre</label>
          <select id="planes-dashboard-trimestre" class="poa-select">
            <option>1</option>
            <option>2</option>
            <option>3</option>
            <option>4</option>
          </select>
        </div>
      </div>
    </header>

    <div class="poa-grid">
      <article class="poa-card">
        <div class="poa-card-header">
          <h2 class="poa-card-title">Tabla</h2>
        </div>
        <div class="poa-card-body">
          <div class="poa-table-wrap">
            <table class="poa-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Actividad</th>
                  <th>Responsable</th>
                  <th>Estado</th>
                  <th>Avance</th>
                  <th>KPI</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><input class="poa-check" type="checkbox"></td>
                  <td>
                    <div class="poa-activity">
                      <span class="poa-activity-dot poa-dot-warning"></span>
                      <span>Diagnóstico institucional</span>
                    </div>
                  </td>
                  <td>Ana López</td>
                  <td><span class="poa-status progress">En proceso</span></td>
                  <td>45%</td>
                  <td>
                    <div class="poa-progress-inline">
                      <div class="poa-progress-bar"><div class="poa-progress-fill success" style="width: 45%;"></div></div>
                    </div>
                  </td>
                </tr>
                <tr>
                  <td><input class="poa-check" type="checkbox"></td>
                  <td>
                    <div class="poa-activity">
                      <span class="poa-activity-dot poa-dot-warning"></span>
                      <span>Elaboración POA</span>
                    </div>
                  </td>
                  <td>Luis Pérez</td>
                  <td><span class="poa-status pending">Pendiente</span></td>
                  <td>0%</td>
                  <td>
                    <div class="poa-progress-inline">
                      <div class="poa-progress-bar"><div class="poa-progress-fill danger" style="width: 36%;"></div></div>
                    </div>
                  </td>
                </tr>
                <tr>
                  <td><input class="poa-check" type="checkbox"></td>
                  <td>
                    <div class="poa-activity">
                      <span class="poa-activity-dot poa-dot-warning"></span>
                      <span>Validación Cabildo</span>
                    </div>
                  </td>
                  <td>Juan Ruiz</td>
                  <td><span class="poa-status review">En revisión</span></td>
                  <td>0%</td>
                  <td>
                    <div class="poa-progress-inline">
                      <div class="poa-progress-bar"><div class="poa-progress-fill warning" style="width: 32%;"></div></div>
                    </div>
                  </td>
                </tr>
                <tr>
                  <td><input class="poa-check" type="checkbox"></td>
                  <td>
                    <div class="poa-activity">
                      <span class="poa-activity-dot poa-dot-success"></span>
                      <span>Seguimiento trimestral</span>
                    </div>
                  </td>
                  <td>Carlos Soto</td>
                  <td><span class="poa-status done">Completado</span></td>
                  <td>100%</td>
                  <td>
                    <div class="poa-progress-inline">
                      <div class="poa-progress-bar"><div class="poa-progress-fill success" style="width: 100%;"></div></div>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </article>

      <article class="poa-card">
        <div class="poa-card-header">
          <h2 class="poa-card-title">Vista Kanban</h2>
        </div>
        <div class="poa-card-body">
          <div class="poa-kanban">
            <div class="poa-kanban-col">
              <div class="poa-kanban-col-title poa-col-pending">Pendiente</div>
              <article class="poa-task">
                <h3 class="poa-task-title">Elaboración POA</h3>
                <div class="poa-task-user">
                  <div class="poa-task-user-info">
                    <div class="poa-task-user-avatar poa-avatar-initials">AL</div>
                    <span class="poa-task-user-name">Ana López</span>
                  </div>
                  <span class="poa-task-badge warning">0%</span>
                </div>
              </article>
            </div>
            <div class="poa-kanban-col">
              <div class="poa-kanban-col-title poa-col-progress">En Proceso</div>
              <article class="poa-task">
                <h3 class="poa-task-title">Diagnóstico Institucional</h3>
                <div class="poa-task-user">
                  <div class="poa-task-user-info">
                    <div class="poa-task-user-avatar poa-avatar-initials">AL</div>
                    <span class="poa-task-user-name">Ana López</span>
                  </div>
                  <span class="poa-task-badge success">45%</span>
                </div>
              </article>
              <article class="poa-task">
                <h3 class="poa-task-title">Diagnóstico Institucional</h3>
                <div class="poa-task-user">
                  <div class="poa-task-user-info">
                    <div class="poa-task-user-avatar poa-avatar-initials">LP</div>
                    <span class="poa-task-user-name">Luis Pérez</span>
                  </div>
                  <span class="poa-task-badge info">82%</span>
                </div>
              </article>
            </div>
            <div class="poa-kanban-col">
              <div class="poa-kanban-col-title poa-col-review">En Revisión</div>
              <article class="poa-task">
                <h3 class="poa-task-title">Validación Cabildo</h3>
                <div class="poa-task-user">
                  <div class="poa-task-user-info">
                    <div class="poa-task-user-avatar poa-avatar-initials">JR</div>
                    <span class="poa-task-user-name">Juan Pérez</span>
                  </div>
                  <span class="poa-task-badge warning">0%</span>
                </div>
              </article>
            </div>
            <div class="poa-kanban-col">
              <div class="poa-kanban-col-title poa-col-done">Completado</div>
              <article class="poa-task">
                <h3 class="poa-task-title">Informe Trimestral</h3>
                <div class="poa-task-user">
                  <div class="poa-task-user-info">
                    <div class="poa-task-user-avatar poa-avatar-initials">MB</div>
                    <span class="poa-task-user-name">Manis Batt</span>
                  </div>
                  <span class="poa-task-badge success">100%</span>
                </div>
              </article>
            </div>
          </div>
        </div>
      </article>

      <article class="poa-card">
        <div class="poa-card-header">
          <h2 class="poa-card-title">Vista Timeline</h2>
          <div class="poa-card-actions">
            <button type="button" class="poa-card-action-btn" aria-label="Compartir"><i class="fa-solid fa-share-from-square" aria-hidden="true"></i></button>
            <button type="button" class="poa-card-action-btn" aria-label="Calendario"><i class="fa-regular fa-calendar" aria-hidden="true"></i></button>
            <button type="button" class="poa-card-action-btn" aria-label="Más opciones"><i class="fa-solid fa-caret-down" aria-hidden="true"></i></button>
          </div>
        </div>
        <div class="poa-card-body">
          <div class="poa-timeline-wrap">
            <div class="poa-timeline-grid">
              <div class="poa-timeline-head">Actividad</div>
              <div class="poa-timeline-head">Ene</div>
              <div class="poa-timeline-head">Feb</div>
              <div class="poa-timeline-head">Mar</div>
              <div class="poa-timeline-head">Abr</div>
              <div class="poa-timeline-head">May</div>
              <div class="poa-timeline-head">Jun</div>

              <div class="poa-timeline-row">
                <div class="poa-timeline-task"><span class="poa-activity-dot poa-dot-info"></span>Diagnóstico institucional</div>
                <div class="poa-bar-cell"><div class="poa-bar blue" style="left: 8%; width: 180%;"></div></div>
                <div class="poa-bar-cell"></div>
                <div class="poa-bar-cell"></div>
                <div class="poa-bar-cell"></div>
                <div class="poa-bar-cell"></div>
                <div class="poa-bar-cell"></div>
              </div>

              <div class="poa-timeline-row">
                <div class="poa-timeline-task"><span class="poa-activity-dot poa-dot-warning"></span>Elaboración POA</div>
                <div class="poa-bar-cell"></div>
                <div class="poa-bar-cell"><div class="poa-bar orange" style="left: 20%; width: 190%;"></div></div>
                <div class="poa-bar-cell"></div>
                <div class="poa-bar-cell"></div>
                <div class="poa-bar-cell"></div>
                <div class="poa-bar-cell"></div>
              </div>

              <div class="poa-timeline-row">
                <div class="poa-timeline-task"><span class="poa-activity-dot poa-dot-danger"></span>Validación Cabildo</div>
                <div class="poa-bar-cell"></div>
                <div class="poa-bar-cell"><div class="poa-bar red" style="left: 52%; width: 245%;"></div></div>
                <div class="poa-bar-cell"></div>
                <div class="poa-bar-cell"></div>
                <div class="poa-bar-cell"></div>
                <div class="poa-bar-cell"></div>
              </div>

              <div class="poa-timeline-row">
                <div class="poa-timeline-task"><span class="poa-activity-dot poa-dot-success"></span>Implementación Estrategia</div>
                <div class="poa-bar-cell"></div>
                <div class="poa-bar-cell"></div>
                <div class="poa-bar-cell"><div class="poa-bar green" style="left: 14%; width: 320%;"></div></div>
                <div class="poa-bar-cell"></div>
                <div class="poa-bar-cell"></div>
                <div class="poa-bar-cell"></div>
              </div>
            </div>
          </div>
        </div>
      </article>

      <article class="poa-card">
        <div class="poa-card-header">
          <h2 class="poa-card-title">Dashboard de Seguimiento</h2>
          <div class="poa-card-actions">
            <button type="button" class="poa-card-action-btn" aria-label="Notas"><i class="fa-solid fa-note-sticky" aria-hidden="true"></i></button>
            <button type="button" class="poa-card-action-btn" aria-label="Alertas"><i class="fa-solid fa-bell" aria-hidden="true"></i></button>
            <div class="poa-avatar poa-avatar-initials" aria-hidden="true">JP</div>
          </div>
        </div>
        <div class="poa-card-body">
          <div class="poa-dashboard-panels">
            <article class="poa-panel">
              <h3 class="poa-panel-title">Avance del Plan</h3>
              <div class="poa-metric-row">
                <div class="poa-donut">
                  <div class="poa-donut-value">64%</div>
                </div>
                <div class="poa-mini-bars">
                  <div class="poa-mini-bar green"><span style="width: 74%;"></span></div>
                  <div class="poa-mini-bar blue"><span style="width: 82%;"></span></div>
                  <div class="poa-mini-bar cyan"><span style="width: 64%;"></span></div>
                </div>
              </div>
            </article>

            <article class="poa-panel">
              <h3 class="poa-panel-title">Cumplimiento de Actividades</h3>
              <div class="poa-chart-bars">
                <div class="poa-chart-bar soft" style="height: 22%;"></div>
                <div class="poa-chart-bar" style="height: 30%;"></div>
                <div class="poa-chart-bar" style="height: 48%;"></div>
                <div class="poa-chart-bar" style="height: 70%;"></div>
                <div class="poa-chart-bar light" style="height: 48%;"></div>
                <div class="poa-chart-bar soft" style="height: 28%;"></div>
              </div>
            </article>

            <article class="poa-panel">
              <h3 class="poa-panel-title">Estado de Actividades</h3>
              <div class="poa-metric-row">
                <div class="poa-donut poa-donut-status">
                  <div class="poa-donut-value poa-donut-value-small"></div>
                </div>
                <div class="poa-legend">
                  <div class="poa-legend-item">
                    <div class="poa-legend-left"><span class="poa-legend-dot pending"></span><span class="poa-legend-label">Pendiente</span></div>
                    <span class="poa-legend-value">12</span>
                  </div>
                  <div class="poa-legend-item">
                    <div class="poa-legend-left"><span class="poa-legend-dot progress"></span><span class="poa-legend-label">En Proceso</span></div>
                    <span class="poa-legend-value">8</span>
                  </div>
                  <div class="poa-legend-item">
                    <div class="poa-legend-left"><span class="poa-legend-dot done"></span><span class="poa-legend-label">Completadas</span></div>
                    <span class="poa-legend-value">15</span>
                  </div>
                </div>
              </div>
            </article>

            <article class="poa-panel">
              <h3 class="poa-panel-title">Avance por Área</h3>
              <div class="poa-area-list">
                <div class="poa-area-item">
                  <div class="poa-area-name">Planeación</div>
                  <div class="poa-area-track"><div class="poa-area-fill blue" style="width: 72%;"></div></div>
                  <div class="poa-area-value">72%</div>
                </div>
                <div class="poa-area-item">
                  <div class="poa-area-name">Finanzas</div>
                  <div class="poa-area-track"><div class="poa-area-fill orange" style="width: 61%;"></div></div>
                  <div class="poa-area-value">61%</div>
                </div>
                <div class="poa-area-item">
                  <div class="poa-area-name">Obras Públicas</div>
                  <div class="poa-area-track"><div class="poa-area-fill red" style="width: 70%;"></div></div>
                  <div class="poa-area-value">70%</div>
                </div>
              </div>
            </article>
          </div>
        </div>
      </article>

      <article class="poa-card poa-grid-full">
        <div class="poa-card-header">
          <h2 class="poa-card-title">Control Presupuestal</h2>
        </div>
        <div class="poa-card-body">
          <div class="poa-budget-table-wrap">
            <table class="poa-budget-table">
              <thead>
                <tr>
                  <th>Mes</th>
                  <th>Presupuestado</th>
                  <th>Ejecutado</th>
                  <th>Variación</th>
                  <th class="text-center">Visual</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Enero</td>
                  <td class="poa-money">$1,200,000</td>
                  <td class="poa-money">$1,050,000</td>
                  <td class="poa-variation negative">-$150,000</td>
                  <td>
                    <div class="poa-budget-bars">
                      <span class="poa-budget-bar blue" style="height: 74px;"></span>
                      <span class="poa-budget-bar red" style="height: 82px;"></span>
                      <span class="poa-budget-bar blue" style="height: 72px;"></span>
                    </div>
                  </td>
                </tr>
                <tr>
                  <td>Febrero</td>
                  <td class="poa-money">$900,000</td>
                  <td class="poa-money">$860,000</td>
                  <td class="poa-variation negative">-$40,000</td>
                  <td>
                    <div class="poa-budget-bars">
                      <span class="poa-budget-bar blue" style="height: 56px;"></span>
                      <span class="poa-budget-bar red" style="height: 60px;"></span>
                      <span class="poa-budget-bar blue" style="height: 54px;"></span>
                    </div>
                  </td>
                </tr>
                <tr>
                  <td>Marzo</td>
                  <td class="poa-money">$1,000,000</td>
                  <td class="poa-money">$1,100,000</td>
                  <td class="poa-variation positive">+$100,000</td>
                  <td>
                    <div class="poa-budget-bars">
                      <span class="poa-budget-bar blue" style="height: 64px;"></span>
                      <span class="poa-budget-bar green" style="height: 72px;"></span>
                      <span class="poa-budget-bar blue" style="height: 68px;"></span>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </article>
    </div>
  </div>
</section>
"""


def _response_json_dict(response) -> dict:
    try:
        body = getattr(response, "body", b"")
        if isinstance(body, bytes):
            return json.loads(body.decode("utf-8"))
        if isinstance(body, str):
            return json.loads(body)
    except Exception:
        return {}
    return {}


def _dashboard_avatar_initials(request: Request) -> str:
    raw = str(getattr(request.state, "user_name", None) or request.cookies.get("user_name") or "SP").strip()
    parts = [part for part in raw.replace(".", " ").split() if part]
    if not parts:
        return "SP"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return f"{parts[0][:1]}{parts[1][:1]}".upper()


def _status_meta(status: str) -> tuple[str, str, str]:
    normalized = str(status or "").strip().lower()
    if normalized == "terminada":
        return ("Completado", "done", "success")
    if normalized == "en revisión":
        return ("En revisión", "review", "warning")
    if normalized == "atrasada":
        return ("Atrasada", "pending", "danger")
    if normalized == "en proceso":
        return ("En proceso", "progress", "info")
    return ("Pendiente", "pending", "warning")


def _activity_dot_class(activity: dict) -> str:
    progress = int(activity.get("avance") or 0)
    status = str(activity.get("status") or "").strip().lower()
    if status == "terminada":
        return "poa-dot-success"
    if status == "en proceso":
        return "poa-dot-info"
    if status == "en revisión":
        return "poa-dot-warning"
    if status == "atrasada":
        return "poa-dot-danger"
    if progress >= 100:
        return "poa-dot-success"
    if progress > 0:
        return "poa-dot-info"
    return "poa-dot-warning"


def _progress_fill_class(activity: dict) -> str:
    progress = int(activity.get("avance") or 0)
    status = str(activity.get("status") or "").strip().lower()
    if status == "terminada" or progress >= 100:
        return "success"
    if status == "en proceso":
        return "info"
    if status == "en revisión":
        return "warning"
    if status == "atrasada":
        return "danger"
    return "warning"


def _parse_iso_date(value: str) -> date | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).date()
    except Exception:
        return None


def _month_start(value: date) -> date:
    return value.replace(day=1)


def _add_months(value: date, months: int) -> date:
    month_index = (value.month - 1) + months
    year = value.year + (month_index // 12)
    month = (month_index % 12) + 1
    return date(year, month, 1)


def _timeline_months(activities: list[dict]) -> list[date]:
    starts = [_parse_iso_date(item.get("fecha_inicial")) for item in activities]
    starts = [item for item in starts if item]
    base = _month_start(min(starts)) if starts else _month_start(datetime.utcnow().date())
    return [_add_months(base, idx) for idx in range(6)]


def _format_month_label(value: date) -> str:
    labels = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    return labels[value.month - 1]


def _timeline_bar_style(activity: dict, months: list[date]) -> str:
    start = _parse_iso_date(activity.get("fecha_inicial")) or months[0]
    end = _parse_iso_date(activity.get("fecha_final")) or start
    start_month = _month_start(start)
    end_month = _month_start(end)
    if end_month < start_month:
        end_month = start_month
    start_index = 0
    for idx, month in enumerate(months):
        if start_month <= month:
            start_index = idx
            break
    else:
        start_index = len(months) - 1
    end_index = start_index
    for idx, month in enumerate(months):
        if end_month >= month:
            end_index = idx
    width = max(1, end_index - start_index + 1)
    left_pct = round((start_index / len(months)) * 100, 2)
    width_pct = round((width / len(months)) * 100 - 6, 2)
    return f"left: {left_pct + 3}%; width: {max(width_pct, 10)}%;"


def _build_budget_summary_rows(activities: list[dict]) -> list[dict]:
    rows: dict[str, dict] = {}
    for activity in activities:
        progress_ratio = max(0.0, min(1.0, float(activity.get("avance") or 0) / 100.0))
        for item in activity.get("budget_items") or []:
            label = str(item.get("rubro") or item.get("tipo") or "Sin rubro").strip() or "Sin rubro"
            current = rows.setdefault(label, {"label": label, "presupuestado": 0.0, "ejecutado": 0.0})
            anual = float(item.get("anual") or 0)
            current["presupuestado"] += anual
            current["ejecutado"] += anual * progress_ratio
    ordered = sorted(rows.values(), key=lambda item: item["presupuestado"], reverse=True)
    return ordered[:3]


def _format_money(value: float) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.0f}"


def _build_real_tablero_content(request: Request) -> str:
    axes_payload = _response_json_dict(strategic_api.list_strategic_axes(request))
    poa_payload = _response_json_dict(poa_service.poa_board_data(request))

    axes = axes_payload.get("data") or []
    activities = poa_payload.get("activities") or []
    objectives = poa_payload.get("objectives") or []

    axis_options = "".join(
        f'<option>{escape(str(axis.get("nombre") or ""))}</option>'
        for axis in axes[:12]
        if str(axis.get("nombre") or "").strip()
    )
    responsible_names = sorted(
        {
            str(activity.get("responsable") or "").strip()
            for activity in activities
            if str(activity.get("responsable") or "").strip()
        },
        key=lambda item: item.lower(),
    )
    responsible_options = "".join(f"<option>{escape(name)}</option>" for name in responsible_names[:20])

    table_rows = []
    for activity in activities[:8]:
        label, status_class, _ = _status_meta(activity.get("status") or "")
        progress = max(0, min(100, int(activity.get("avance") or 0)))
        table_rows.append(
            f"""
            <tr>
              <td><input class="poa-check" type="checkbox"></td>
              <td>
                <div class="poa-activity">
                  <span class="poa-activity-dot {_activity_dot_class(activity)}"></span>
                  <span>{escape(str(activity.get("nombre") or ""))}</span>
                </div>
              </td>
              <td>{escape(str(activity.get("responsable") or "Sin responsable"))}</td>
              <td><span class="poa-status {status_class}">{escape(label)}</span></td>
              <td>{progress}%</td>
              <td>
                <div class="poa-progress-inline">
                  <div class="poa-progress-bar"><div class="poa-progress-fill {_progress_fill_class(activity)}" style="width: {progress}%;"></div></div>
                </div>
              </td>
            </tr>
            """
        )
    if not table_rows:
        table_rows.append('<tr><td colspan="6" class="text-center">No hay actividades registradas.</td></tr>')

    grouped = {"Pendiente": [], "En Proceso": [], "En Revisión": [], "Completado": []}
    for activity in activities[:20]:
        label, _, badge_class = _status_meta(activity.get("status") or "")
        grouped.setdefault(label, []).append((activity, badge_class))

    def build_kanban_tasks(items: list[tuple[dict, str]]) -> str:
        if not items:
            return '<div class="text-sm text-base-content/60">Sin actividades</div>'
        cards = []
        for activity, badge_class in items[:6]:
            progress = max(0, min(100, int(activity.get("avance") or 0)))
            responsable = str(activity.get("responsable") or "Sin responsable")
            initials = _dashboard_avatar_initials(request) if responsable == "Sin responsable" else "".join([part[:1] for part in responsable.split()[:2]]).upper()
            cards.append(
                f"""
                <article class="poa-task">
                  <h3 class="poa-task-title">{escape(str(activity.get("nombre") or ""))}</h3>
                  <div class="poa-task-user">
                    <div class="poa-task-user-info">
                      <div class="poa-task-user-avatar">{escape(initials or 'SP')}</div>
                      <span class="poa-task-user-name">{escape(responsable)}</span>
                    </div>
                    <span class="poa-task-badge {badge_class}">{progress}%</span>
                  </div>
                </article>
                """
            )
        return "".join(cards)

    months = _timeline_months(activities)
    timeline_rows = []
    bar_colors = ["blue", "orange", "red", "green"]
    for idx, activity in enumerate(activities[:4]):
        timeline_rows.append(
            f"""
            <div class="poa-timeline-task"><span class="poa-activity-dot {_activity_dot_class(activity)}"></span>{escape(str(activity.get("nombre") or ""))}</div>
            {"".join(
                f'<div class="poa-bar-cell">' +
                (f'<div class="poa-bar {bar_colors[idx % len(bar_colors)]}" style="{_timeline_bar_style(activity, months)}"></div>' if month_idx == 0 else '') +
                '</div>'
                for month_idx, _month in enumerate(months)
            )}
            """
        )
    if not timeline_rows:
        timeline_rows.append('<div class="poa-timeline-task">Sin actividades</div>' + "".join('<div class="poa-bar-cell"></div>' for _ in months))

    total_activities = len(activities)
    avg_progress = int(round(sum(int(item.get("avance") or 0) for item in activities) / total_activities)) if total_activities else 0
    status_counts = {"Pendiente": 0, "En Proceso": 0, "En Revisión": 0, "Completado": 0}
    for activity in activities:
        label, _, _ = _status_meta(activity.get("status") or "")
        status_counts[label] = status_counts.get(label, 0) + 1

    area_rows = []
    for axis in axes[:3]:
        axis_progress = int(axis.get("avance") or 0)
        area_rows.append(
            f"""
            <div class="poa-area-item">
              <div class="poa-area-name">{escape(str(axis.get("nombre") or ""))}</div>
              <div class="poa-area-track"><div class="poa-area-fill {'blue' if len(area_rows) == 0 else 'orange' if len(area_rows) == 1 else 'red'}" style="width: {axis_progress}%;"></div></div>
              <div class="poa-area-value">{axis_progress}%</div>
            </div>
            """
        )
    if not area_rows:
        area_rows.append('<div class="text-sm text-base-content/60">No hay ejes estratégicos.</div>')

    budget_rows = _build_budget_summary_rows(activities)
    budget_html = []
    for item in budget_rows:
        presupuestado = float(item["presupuestado"])
        ejecutado = float(item["ejecutado"])
        variacion = ejecutado - presupuestado
        positive = variacion >= 0
        budget_html.append(
            f"""
            <tr>
              <td>{escape(str(item['label']))}</td>
              <td class="poa-money">{_format_money(presupuestado)}</td>
              <td class="poa-money">{_format_money(ejecutado)}</td>
              <td class="poa-variation {'positive' if positive else 'negative'}">{'+' if positive else '-'}{_format_money(abs(variacion))}</td>
              <td>
                <div class="poa-budget-bars">
                  <span class="poa-budget-bar blue" style="height: 64px;"></span>
                  <span class="poa-budget-bar {'green' if positive else 'red'}" style="height: {72 if positive else 54}px;"></span>
                  <span class="poa-budget-bar blue" style="height: 58px;"></span>
                </div>
              </td>
            </tr>
            """
        )
    if not budget_html:
        budget_html.append('<tr><td colspan="5" class="text-center">No hay datos presupuestales cargados.</td></tr>')

    return f"""
<section class="poa-dashboard-page">
  <div class="poa-dashboard-wrap">
    <header class="poa-main-header">
      <div class="poa-main-top">
        <div class="poa-brand">
          <div class="poa-brand-logo">
            <i class="fa-solid fa-compass-drafting" aria-hidden="true"></i>
          </div>
          <div>
            <h1 class="poa-brand-title">SIPET - Sistema de planeación estratética y táctica</h1>
            <p class="poa-brand-subtitle">Tablero ejecutivo del plan estratégico con información real del plan y POA</p>
          </div>
        </div>
        <div class="poa-user-tools">
          <button type="button" class="poa-icon-btn" aria-label="Historial"><i class="fa-solid fa-clock-rotate-left" aria-hidden="true"></i></button>
          <button type="button" class="poa-icon-btn" aria-label="Notificaciones"><i class="fa-solid fa-bell" aria-hidden="true"></i></button>
          <div class="poa-avatar poa-avatar-initials" aria-hidden="true">{escape(_dashboard_avatar_initials(request))}</div>
        </div>
      </div>
      <div class="poa-tabs" role="tablist" aria-label="Vistas del tablero">
        <button type="button" class="poa-tab active">Tabla</button>
        <button type="button" class="poa-tab">Kanban</button>
        <button type="button" class="poa-tab">Timeline</button>
        <button type="button" class="poa-tab">Dashboard</button>
        <button type="button" class="poa-tab">Presupuesto</button>
      </div>
      <div class="poa-filters">
        <div class="poa-filter">
          <label for="planes-dashboard-area">Área</label>
          <select id="planes-dashboard-area" class="poa-select">
            <option>Todas</option>
            {axis_options}
          </select>
        </div>
        <div class="poa-filter">
          <label for="planes-dashboard-responsable">Responsable</label>
          <select id="planes-dashboard-responsable" class="poa-select">
            <option>Todos</option>
            {responsible_options}
          </select>
        </div>
        <div class="poa-filter">
          <label for="planes-dashboard-trimestre">Trimestre</label>
          <select id="planes-dashboard-trimestre" class="poa-select">
            <option>1</option><option>2</option><option>3</option><option>4</option>
          </select>
        </div>
      </div>
    </header>

    <div class="poa-grid">
      <article class="poa-card">
        <div class="poa-card-header"><h2 class="poa-card-title">Tabla</h2></div>
        <div class="poa-card-body">
          <div class="poa-table-wrap">
            <table class="poa-table">
              <thead>
                <tr><th>#</th><th>Actividad</th><th>Responsable</th><th>Estado</th><th>Avance</th><th>KPI</th></tr>
              </thead>
              <tbody>{''.join(table_rows)}</tbody>
            </table>
          </div>
        </div>
      </article>

      <article class="poa-card">
        <div class="poa-card-header"><h2 class="poa-card-title">Vista Kanban</h2></div>
        <div class="poa-card-body">
          <div class="poa-kanban">
            <div class="poa-kanban-col"><div class="poa-kanban-col-title poa-col-pending">Pendiente</div>{build_kanban_tasks(grouped.get('Pendiente', []))}</div>
            <div class="poa-kanban-col"><div class="poa-kanban-col-title poa-col-progress">En Proceso</div>{build_kanban_tasks(grouped.get('En Proceso', []))}</div>
            <div class="poa-kanban-col"><div class="poa-kanban-col-title poa-col-review">En Revisión</div>{build_kanban_tasks(grouped.get('En Revisión', []))}</div>
            <div class="poa-kanban-col"><div class="poa-kanban-col-title poa-col-done">Completado</div>{build_kanban_tasks(grouped.get('Completado', []))}</div>
          </div>
        </div>
      </article>

      <article class="poa-card">
        <div class="poa-card-header">
          <h2 class="poa-card-title">Vista Timeline</h2>
          <div class="poa-card-actions">
            <button type="button" class="poa-card-action-btn" aria-label="Compartir"><i class="fa-solid fa-share-from-square" aria-hidden="true"></i></button>
            <button type="button" class="poa-card-action-btn" aria-label="Calendario"><i class="fa-regular fa-calendar" aria-hidden="true"></i></button>
            <button type="button" class="poa-card-action-btn" aria-label="Más opciones"><i class="fa-solid fa-caret-down" aria-hidden="true"></i></button>
          </div>
        </div>
        <div class="poa-card-body">
          <div class="poa-timeline-wrap">
            <div class="poa-timeline-grid">
              <div class="poa-timeline-head">Actividad</div>
              {''.join(f'<div class="poa-timeline-head">{_format_month_label(month)}</div>' for month in months)}
              {''.join(timeline_rows)}
            </div>
          </div>
        </div>
      </article>

      <article class="poa-card">
        <div class="poa-card-header">
          <h2 class="poa-card-title">Dashboard de Seguimiento</h2>
          <div class="poa-card-actions">
            <button type="button" class="poa-card-action-btn" aria-label="Notas"><i class="fa-solid fa-note-sticky" aria-hidden="true"></i></button>
            <button type="button" class="poa-card-action-btn" aria-label="Alertas"><i class="fa-solid fa-bell" aria-hidden="true"></i></button>
            <div class="poa-avatar poa-avatar-initials" aria-hidden="true">{escape(_dashboard_avatar_initials(request))}</div>
          </div>
        </div>
        <div class="poa-card-body">
          <div class="poa-dashboard-panels">
            <article class="poa-panel">
              <h3 class="poa-panel-title">Avance del Plan</h3>
              <div class="poa-metric-row">
                <div class="poa-donut"><div class="poa-donut-value">{avg_progress}%</div></div>
                <div class="poa-mini-bars">
                  <div class="poa-mini-bar green"><span style="width: {avg_progress}%;"></span></div>
                  <div class="poa-mini-bar blue"><span style="width: {min(100, len(objectives) * 8)}%;"></span></div>
                  <div class="poa-mini-bar cyan"><span style="width: {min(100, len(axes) * 18)}%;"></span></div>
                </div>
              </div>
            </article>
            <article class="poa-panel">
              <h3 class="poa-panel-title">Cumplimiento de Actividades</h3>
              <div class="poa-chart-bars">
                <div class="poa-chart-bar soft" style="height: {max(18, status_counts['Pendiente'] * 8)}%;"></div>
                <div class="poa-chart-bar" style="height: {max(18, status_counts['En Proceso'] * 10)}%;"></div>
                <div class="poa-chart-bar" style="height: {max(18, status_counts['En Revisión'] * 10)}%;"></div>
                <div class="poa-chart-bar light" style="height: {max(18, status_counts['Completado'] * 10)}%;"></div>
              </div>
            </article>
            <article class="poa-panel">
              <h3 class="poa-panel-title">Estado de Actividades</h3>
              <div class="poa-metric-row">
                <div class="poa-donut poa-donut-status"><div class="poa-donut-value poa-donut-value-small"></div></div>
                <div class="poa-legend">
                  <div class="poa-legend-item"><div class="poa-legend-left"><span class="poa-legend-dot pending"></span><span class="poa-legend-label">Pendiente</span></div><span class="poa-legend-value">{status_counts['Pendiente']}</span></div>
                  <div class="poa-legend-item"><div class="poa-legend-left"><span class="poa-legend-dot progress"></span><span class="poa-legend-label">En Proceso</span></div><span class="poa-legend-value">{status_counts['En Proceso']}</span></div>
                  <div class="poa-legend-item"><div class="poa-legend-left"><span class="poa-legend-dot done"></span><span class="poa-legend-label">Completadas</span></div><span class="poa-legend-value">{status_counts['Completado']}</span></div>
                </div>
              </div>
            </article>
            <article class="poa-panel">
              <h3 class="poa-panel-title">Avance por Área</h3>
              <div class="poa-area-list">{''.join(area_rows)}</div>
            </article>
          </div>
        </div>
      </article>

      <article class="poa-card poa-grid-full">
        <div class="poa-card-header"><h2 class="poa-card-title">Control Presupuestal</h2></div>
        <div class="poa-card-body">
          <div class="poa-budget-table-wrap">
            <table class="poa-budget-table">
              <thead><tr><th>Rubro</th><th>Presupuestado</th><th>Ejecutado</th><th>Variación</th><th class="text-center">Visual</th></tr></thead>
              <tbody>{''.join(budget_html)}</tbody>
            </table>
          </div>
        </div>
      </article>
    </div>
  </div>
</section>
"""


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


@router.get("/planes/tablero-control", response_class=HTMLResponse)
def plan_estrategico_tablero_page(request: Request):
    from fastapi_modulo.main import render_backend_page

    try:
        tablero_css = _PLAN_ESTRATEGICO_CSS_PATH.read_text(encoding="utf-8")
    except OSError:
        tablero_css = ""
    tablero_content = _build_real_tablero_content(request)

    return render_backend_page(
        request,
        title="Tablero de control",
        description="Vista ejecutiva del plan estratégico",
        content=(f"<style>{tablero_css}</style>{tablero_content}"),
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
