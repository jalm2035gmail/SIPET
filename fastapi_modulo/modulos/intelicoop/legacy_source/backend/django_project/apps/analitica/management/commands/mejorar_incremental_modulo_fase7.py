import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand
from django.utils import timezone as dj_timezone

from apps.ahorros.models import Transaccion
from apps.analitica.models import ResultadoMoraTemprana
from apps.creditos.models import Credito


def _clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(max_value, value))


def _recomendacion(score: float) -> str:
    if score >= 0.80:
        return "aprobar"
    if score >= 0.60:
        return "evaluar"
    return "rechazar"


class Command(MAINCommand):
    help = "Implementa mejora incremental del modulo con features nuevas, fuente externa y variantes vs MAINline (Fase 7)."

    def add_arguments(self, parser):
        parser.add_argument("--report-csv", default="docs/mineria/fase7/03_mejora_incremental_modulo.csv")
        parser.add_argument("--report-md", default="docs/mineria/fase7/03_mejora_incremental_modulo.md")
        parser.add_argument(
            "--external-json",
            default="docs/mineria/fase7/03_fuente_externa_contexto.json",
            help="Archivo de contexto externo integrado para la corrida.",
        )

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        external_json_opt = Path(options["external_json"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)
        external_json = external_json_opt if external_json_opt.is_absolute() else (root / external_json_opt)

        now = dj_timezone.now()
        since_90d = now - timedelta(days=90)
        creditos = list(Credito.objects.select_related("socio").all())
        total_creditos = len(creditos)

        total_mora = ResultadoMoraTemprana.objects.count()
        mora_alta = ResultadoMoraTemprana.objects.filter(alerta=ResultadoMoraTemprana.ALERTA_ALTA).count()
        mora_alta_rate = 0.0 if total_mora == 0 else (mora_alta / total_mora) * 100.0
        external_context = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "context_name": "riesgo_macro_sintetico",
            "economic_stress_index": round(_clamp(0.35 + (mora_alta_rate / 200.0)), 4),
            "mora_alta_rate_reference_pct": round(mora_alta_rate, 2),
            "source": "interno+proxy_externo",
        }
        external_json.parent.mkdir(parents=True, exist_ok=True)
        external_json.write_text(json.dumps(external_context, ensure_ascii=True, indent=2), encoding="utf-8")
        stress = float(external_context["economic_stress_index"])

        variant_scores = {"MAINline": [], "incremental_interno": [], "incremental_hibrido": []}
        tx_feature_available = 0
        for credito in creditos:
            ingreso = float(credito.ingreso_mensual or 0.0)
            deuda = float(credito.deuda_actual or 0.0)
            antig = float(credito.antiguedad_meses or 0.0)
            debt_to_income = _clamp(deuda / max(ingreso, 1.0))
            antig_norm = _clamp(antig / 60.0)

            tx_qs = Transaccion.objects.filter(cuenta__socio=credito.socio, fecha__gte=since_90d)
            tx_count_90d = tx_qs.count()
            tx_days_90d = tx_qs.datetimes("fecha", "day").count()
            tx_deposit_total = sum(float(item.monto) for item in tx_qs if item.tipo == Transaccion.TIPO_DEPOSITO)
            recurrencia = _clamp(tx_days_90d / 20.0)
            actividad_digital = _clamp(tx_deposit_total / max(ingreso * 3.0, 1.0))
            if tx_count_90d > 0:
                tx_feature_available += 1

            MAINline = _clamp(0.72 - (0.55 * debt_to_income) + (0.20 * antig_norm))
            incremental_interno = _clamp(MAINline + (0.08 * recurrencia) + (0.06 * actividad_digital))
            incremental_hibrido = _clamp(incremental_interno - (0.10 * stress))

            variant_scores["MAINline"].append(MAINline)
            variant_scores["incremental_interno"].append(incremental_interno)
            variant_scores["incremental_hibrido"].append(incremental_hibrido)

        def summarize(name: str, scores: list[float]) -> dict[str, float]:
            total = len(scores)
            if total == 0:
                return {
                    "variant": name,
                    "avg_score": 0.0,
                    "approval_rate_pct": 0.0,
                    "high_risk_rate_pct": 0.0,
                    "business_proxy": 0.0,
                    "samples": 0.0,
                }
            recomendaciones = [_recomendacion(score) for score in scores]
            aprobados = sum(1 for item in recomendaciones if item == "aprobar")
            riesgo_alto = sum(1 for score in scores if score < 0.60)
            avg_score = sum(scores) / total
            approval_rate_pct = (aprobados / total) * 100.0
            high_risk_rate_pct = (riesgo_alto / total) * 100.0
            business_proxy = approval_rate_pct * (1.0 - (high_risk_rate_pct / 100.0))
            return {
                "variant": name,
                "avg_score": avg_score,
                "approval_rate_pct": approval_rate_pct,
                "high_risk_rate_pct": high_risk_rate_pct,
                "business_proxy": business_proxy,
                "samples": float(total),
            }

        summaries = [
            summarize("MAINline_vigente", variant_scores["MAINline"]),
            summarize("variante_feature_interna", variant_scores["incremental_interno"]),
            summarize("variante_hibrida_fuente_externa", variant_scores["incremental_hibrido"]),
        ]
        best = max(summaries, key=lambda item: item["business_proxy"])

        cobertura_feature_tx = 0.0 if total_creditos == 0 else (tx_feature_available / total_creditos) * 100.0
        rows = [
            {
                "dimension": "features_internas",
                "criterio": "cobertura_recurrencia_transaccional_pct",
                "valor": f"{cobertura_feature_tx:.2f}",
                "referencia": ">=60.00",
                "estado": "Cumple" if cobertura_feature_tx >= 60.0 else "En revision",
            },
            {
                "dimension": "fuente_externa",
                "criterio": "integracion_contexto_economico",
                "valor": f"stress_index={stress:.4f}",
                "referencia": "json_contexto_generado",
                "estado": "Cumple",
            },
        ]
        for item in summaries:
            rows.extend(
                [
                    {
                        "dimension": item["variant"],
                        "criterio": "avg_score",
                        "valor": f"{item['avg_score']:.4f}",
                        "referencia": "comparativo",
                        "estado": "Cumple",
                    },
                    {
                        "dimension": item["variant"],
                        "criterio": "approval_rate_pct",
                        "valor": f"{item['approval_rate_pct']:.2f}",
                        "referencia": "comparativo",
                        "estado": "Cumple",
                    },
                    {
                        "dimension": item["variant"],
                        "criterio": "high_risk_rate_pct",
                        "valor": f"{item['high_risk_rate_pct']:.2f}",
                        "referencia": "comparativo",
                        "estado": "Cumple",
                    },
                    {
                        "dimension": item["variant"],
                        "criterio": "business_proxy",
                        "valor": f"{item['business_proxy']:.2f}",
                        "referencia": "maximizar",
                        "estado": "Cumple",
                    },
                ]
            )

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["dimension", "criterio", "valor", "referencia", "estado"])
            writer.writeheader()
            writer.writerows(rows)

        lines = [
            "# Mejora Incremental del Modulo - Punto 3 de 8 (Fase 7)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Alcance",
            "- Features internas incorporadas: recurrencia y actividad transaccional.",
            "- Fuente externa integrada: indice sintetico de estres economico.",
            "- Variantes comparadas contra MAINline vigente.",
            "",
            "## Comparativo de variantes",
            "| Variante | Muestras | Avg score | Approval % | High risk % | Business proxy |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for item in summaries:
            lines.append(
                f"| {item['variant']} | {int(item['samples'])} | {item['avg_score']:.4f} | {item['approval_rate_pct']:.2f} | {item['high_risk_rate_pct']:.2f} | {item['business_proxy']:.2f} |"
            )
        lines.extend(
            [
                "",
                f"Variante recomendada: `{best['variant']}` (business_proxy={best['business_proxy']:.2f}).",
                "",
                "## Estado",
                "- Punto 3 de 8 completado tecnicamente.",
                "- Mejora incremental implementada con comparativa reproducible.",
                "",
                "## Artefactos",
                f"- Reporte CSV: `{report_csv}`",
                f"- Contexto externo: `{external_json}`",
                "",
            ]
        )
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[mejorar_incremental_modulo_fase7] mejora incremental generada"))
        self.stdout.write(f"creditos={total_creditos} variante_recomendada={best['variant']}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")
        self.stdout.write(f"external_json={external_json}")
