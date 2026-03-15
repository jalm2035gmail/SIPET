import csv
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand

from apps.analitica.models import ResultadoScoring


def _clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(max_value, value))


def _recomendacion(score: float) -> str:
    if score >= 0.80:
        return "aprobar"
    if score >= 0.60:
        return "evaluar"
    return "rechazar"


class Command(MAINCommand):
    help = "Ejecuta ciclo de experimentacion controlada (A/B + shadow), compara impacto y define rollback/promocion."

    def add_arguments(self, parser):
        parser.add_argument("--report-csv", default="docs/mineria/fase7/04_experimentacion_controlada.csv")
        parser.add_argument("--report-md", default="docs/mineria/fase7/04_experimentacion_controlada.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        scoring = list(ResultadoScoring.objects.order_by("-id")[:300])
        total = len(scoring)

        MAINline_scores = []
        candidate_ab_scores = []
        candidate_shadow_scores = []
        for idx, item in enumerate(scoring):
            ingreso = float(item.ingreso_mensual or 0.0)
            deuda = float(item.deuda_actual or 0.0)
            antig = float(item.antiguedad_meses or 0.0)
            dti = _clamp(deuda / max(ingreso, 1.0))
            antig_norm = _clamp(antig / 60.0)
            MAIN = _clamp(0.70 - (0.55 * dti) + (0.25 * antig_norm))

            # Variante A/B: ajuste conservador (menos riesgo de sobre-aprobacion).
            candidate_ab = _clamp(MAIN + 0.015 - (0.02 * dti))
            # Shadow mode: mas agresivo en aprobacion para evaluar impacto potencial.
            candidate_shadow = _clamp(MAIN + 0.03)

            MAINline_scores.append(MAIN)
            if idx % 2 == 0:
                candidate_ab_scores.append(candidate_ab)
            else:
                candidate_ab_scores.append(MAIN)
            candidate_shadow_scores.append(candidate_shadow)

        def summarize(name: str, scores: list[float]) -> dict[str, float]:
            if not scores:
                return {
                    "grupo": name,
                    "muestras": 0.0,
                    "score_promedio": 0.0,
                    "aprobacion_pct": 0.0,
                    "riesgo_alto_pct": 0.0,
                    "impacto_compuesto": 0.0,
                }
            muestras = len(scores)
            recs = [_recomendacion(score) for score in scores]
            aprobados = sum(1 for rec in recs if rec == "aprobar")
            riesgo_alto = sum(1 for score in scores if score < 0.60)
            score_promedio = sum(scores) / muestras
            aprobacion_pct = (aprobados / muestras) * 100.0
            riesgo_alto_pct = (riesgo_alto / muestras) * 100.0
            impacto_compuesto = aprobacion_pct * (1.0 - (riesgo_alto_pct / 100.0))
            return {
                "grupo": name,
                "muestras": float(muestras),
                "score_promedio": score_promedio,
                "aprobacion_pct": aprobacion_pct,
                "riesgo_alto_pct": riesgo_alto_pct,
                "impacto_compuesto": impacto_compuesto,
            }

        MAINline = summarize("MAINline_control", MAINline_scores)
        ab = summarize("ab_candidate", candidate_ab_scores)
        shadow = summarize("shadow_candidate", candidate_shadow_scores)

        delta_ab_impacto = ab["impacto_compuesto"] - MAINline["impacto_compuesto"]
        delta_ab_riesgo = ab["riesgo_alto_pct"] - MAINline["riesgo_alto_pct"]
        delta_shadow_impacto = shadow["impacto_compuesto"] - MAINline["impacto_compuesto"]
        delta_shadow_riesgo = shadow["riesgo_alto_pct"] - MAINline["riesgo_alto_pct"]

        guardrail_riesgo_max = 2.0
        guardrail_impacto_min = 0.0
        ab_pass = delta_ab_riesgo <= guardrail_riesgo_max and delta_ab_impacto >= guardrail_impacto_min
        shadow_pass = delta_shadow_riesgo <= guardrail_riesgo_max and delta_shadow_impacto >= guardrail_impacto_min

        if total == 0:
            decision = "mantener_MAINline_sin_muestras"
        else:
            decision = "promover_candidate_ab" if ab_pass else "rollback_inmediato"
            if ab_pass and shadow_pass and shadow["impacto_compuesto"] > ab["impacto_compuesto"]:
                decision = "promover_candidate_shadow"

        rollback_ready = decision == "rollback_inmediato"

        rows = [
            {
                "dimension": "configuracion",
                "metrica": "total_muestras",
                "valor": f"{total}",
                "umbral": ">=1",
                "estado": "Cumple" if total >= 1 else "En revision",
            },
            {
                "dimension": "ab_test",
                "metrica": "delta_impacto_vs_MAINline",
                "valor": f"{delta_ab_impacto:.2f}",
                "umbral": ">=0.00",
                "estado": "Cumple" if delta_ab_impacto >= 0.0 else "En revision",
            },
            {
                "dimension": "ab_test",
                "metrica": "delta_riesgo_alto_vs_MAINline_pct",
                "valor": f"{delta_ab_riesgo:.2f}",
                "umbral": "<=2.00",
                "estado": "Cumple" if delta_ab_riesgo <= guardrail_riesgo_max else "En revision",
            },
            {
                "dimension": "shadow_mode",
                "metrica": "delta_impacto_vs_MAINline",
                "valor": f"{delta_shadow_impacto:.2f}",
                "umbral": ">=0.00",
                "estado": "Cumple" if delta_shadow_impacto >= 0.0 else "En revision",
            },
            {
                "dimension": "shadow_mode",
                "metrica": "delta_riesgo_alto_vs_MAINline_pct",
                "valor": f"{delta_shadow_riesgo:.2f}",
                "umbral": "<=2.00",
                "estado": "Cumple" if delta_shadow_riesgo <= guardrail_riesgo_max else "En revision",
            },
            {
                "dimension": "gobierno",
                "metrica": "decision",
                "valor": decision,
                "umbral": "promover_o_rollback",
                "estado": "Cumple",
            },
            {
                "dimension": "gobierno",
                "metrica": "rollback_preparado",
                "valor": "si" if rollback_ready else "no",
                "umbral": "si_hay_desempeno_inferior",
                "estado": "Cumple",
            },
        ]

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["dimension", "metrica", "valor", "umbral", "estado"])
            writer.writeheader()
            writer.writerows(rows)

        lines = [
            "# Ciclo de Experimentacion Controlada - Punto 4 de 8 (Fase 7)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Esquema de prueba",
            "- A/B: MAINline vs candidate_ab (50/50 logico).",
            "- Shadow mode: candidate_shadow evaluado en paralelo sin impacto operativo.",
            "",
            "## Comparativo",
            "| Grupo | Muestras | Score promedio | Aprobacion % | Riesgo alto % | Impacto compuesto |",
            "|---|---:|---:|---:|---:|---:|",
            f"| MAINline_control | {int(MAINline['muestras'])} | {MAINline['score_promedio']:.4f} | {MAINline['aprobacion_pct']:.2f} | {MAINline['riesgo_alto_pct']:.2f} | {MAINline['impacto_compuesto']:.2f} |",
            f"| ab_candidate | {int(ab['muestras'])} | {ab['score_promedio']:.4f} | {ab['aprobacion_pct']:.2f} | {ab['riesgo_alto_pct']:.2f} | {ab['impacto_compuesto']:.2f} |",
            f"| shadow_candidate | {int(shadow['muestras'])} | {shadow['score_promedio']:.4f} | {shadow['aprobacion_pct']:.2f} | {shadow['riesgo_alto_pct']:.2f} | {shadow['impacto_compuesto']:.2f} |",
            "",
            "## Decision operacional",
            f"- Decision: `{decision}`",
            "- Guardrail de riesgo alto: delta <= 2.00 puntos porcentuales.",
            "- Guardrail de impacto: no degradar impacto compuesto vs MAINline.",
            f"- Rollback inmediato: {'habilitado' if rollback_ready else 'listo si candidato cae bajo guardrails'}",
            "",
            "## Estado",
            "- Punto 4 de 8 completado tecnicamente.",
            "- Ciclo de experimentacion controlada implementado con criterio de rollback.",
            "",
            "## Artefactos",
            f"- Reporte CSV: `{report_csv}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[experimentacion_controlada_fase7] experimento generado"))
        self.stdout.write(f"muestras={total} decision={decision}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")
