from __future__ import annotations

import os
from typing import Dict, List, Tuple

from fastapi_modulo.modulos.planificacion.controladores.annual_cycle_service import get_presupuesto_txt_path


def load_budget_summary(
    tenant_id: str,
    active_year: int,
    completion_ratio: int,
) -> Dict[str, object]:
    presupuesto_rows = 0
    presupuesto_total = 0.0
    presupuesto_por_rubro: Dict[str, float] = {}
    presupuesto_path = str(get_presupuesto_txt_path(tenant_id, active_year))

    if os.path.exists(presupuesto_path):
        try:
            with open(presupuesto_path, "r", encoding="utf-8") as fh:
                for raw in fh:
                    line = (raw or "").strip()
                    if not line:
                        continue
                    parts = [chunk.strip() for chunk in line.split("\t")]
                    if len(parts) < 3:
                        continue
                    code = parts[0]
                    amount_raw = parts[2].replace(",", "").strip()
                    try:
                        amount = float(amount_raw)
                    except (TypeError, ValueError):
                        continue
                    presupuesto_rows += 1
                    presupuesto_total += amount
                    rubro = code.split("-")[0].strip() if code else ""
                    rubro = rubro or "ND"
                    presupuesto_por_rubro[rubro] = float(presupuesto_por_rubro.get(rubro, 0.0)) + amount
        except OSError:
            presupuesto_rows = 0
            presupuesto_total = 0.0
            presupuesto_por_rubro = {}

    presupuesto_ejercido = presupuesto_total * (completion_ratio / 100.0)
    pres_ejecutado_pct = int(round((presupuesto_ejercido / presupuesto_total) * 100)) if presupuesto_total > 0 else 0
    top_budget: List[Tuple[str, float]] = sorted(
        presupuesto_por_rubro.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:6]

    return {
        "rows": presupuesto_rows,
        "total": presupuesto_total,
        "por_rubro": presupuesto_por_rubro,
        "ejercido": presupuesto_ejercido,
        "ejecutado_pct": pres_ejecutado_pct,
        "top_budget": top_budget,
    }
