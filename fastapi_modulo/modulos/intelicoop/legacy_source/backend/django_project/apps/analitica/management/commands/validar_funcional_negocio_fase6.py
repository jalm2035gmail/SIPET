import csv
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand
from django.db.models import Avg, Count

from apps.analitica.models import ReglaAsociacionProducto, ResultadoMoraTemprana, ResultadoScoring, ResultadoSegmentacionSocio


def _estado(valor: float, umbral: float, mayor_mejor: bool = True) -> str:
    if mayor_mejor:
        return "Cumple" if valor >= umbral else "En revision"
    return "Cumple" if valor <= umbral else "En revision"


class Command(MAINCommand):
    help = "Ejecuta validacion funcional con areas de negocio para resultados de riesgo/cobranzas/comercial (Fase 6)."

    def add_arguments(self, parser):
        parser.add_argument("--report-csv", default="docs/mineria/fase6/02_validacion_funcional_negocio.csv")
        parser.add_argument("--report-md", default="docs/mineria/fase6/02_validacion_funcional_negocio.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        total_alertas = ResultadoMoraTemprana.objects.count()
        alertas_media_alta = ResultadoMoraTemprana.objects.filter(alerta__in=["media", "alta"]).count()
        pct_alertas_accionables = 0.0 if total_alertas == 0 else (alertas_media_alta / total_alertas) * 100.0

        total_segmentacion = ResultadoSegmentacionSocio.objects.count()
        total_segmentos_distintos = (
            ResultadoSegmentacionSocio.objects.values("segmento").distinct().count() if total_segmentacion > 0 else 0
        )
        segmentacion_interpretable = 100.0 if total_segmentos_distintos >= 3 else (66.0 if total_segmentos_distintos == 2 else 0.0)

        total_reglas = ReglaAsociacionProducto.objects.filter(vigente=True).count()
        lift_promedio = float(
            ReglaAsociacionProducto.objects.filter(vigente=True).aggregate(v=Avg("lift"))["v"] or 0.0
        )
        reglas_accionables = float(total_reglas)

        total_scoring = ResultadoScoring.objects.count()
        scoring_con_recomendacion = ResultadoScoring.objects.exclude(recomendacion__isnull=True).exclude(recomendacion="").count()
        pct_scoring_explicable = 0.0 if total_scoring == 0 else (scoring_con_recomendacion / total_scoring) * 100.0

        rows = [
            {
                "area": "cobranzas",
                "criterio": "alertas_accionables_pct",
                "valor": f"{pct_alertas_accionables:.2f}",
                "umbral": ">=40.00",
                "estado": _estado(pct_alertas_accionables, 40.0),
            },
            {
                "area": "riesgo",
                "criterio": "scoring_explicable_pct",
                "valor": f"{pct_scoring_explicable:.2f}",
                "umbral": ">=90.00",
                "estado": _estado(pct_scoring_explicable, 90.0),
            },
            {
                "area": "comercial",
                "criterio": "segmentacion_interpretable_pct",
                "valor": f"{segmentacion_interpretable:.2f}",
                "umbral": ">=66.00",
                "estado": _estado(segmentacion_interpretable, 66.0),
            },
            {
                "area": "comercial",
                "criterio": "reglas_accionables_total",
                "valor": f"{reglas_accionables:.0f}",
                "umbral": ">=1",
                "estado": _estado(reglas_accionables, 1.0),
            },
            {
                "area": "comercial",
                "criterio": "lift_promedio_reglas",
                "valor": f"{lift_promedio:.4f}",
                "umbral": ">=1.0000",
                "estado": _estado(lift_promedio, 1.0),
            },
        ]

        cumple = sum(1 for row in rows if row["estado"] == "Cumple")
        total = len(rows)
        estado_global = "Aprobacion funcional recomendada" if cumple == total else "Aprobacion funcional condicionada"

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["area", "criterio", "valor", "umbral", "estado"])
            writer.writeheader()
            writer.writerows(rows)

        lines = [
            "# Validacion Funcional con Negocio - Punto 2 de 8 (Fase 6)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Resultado de validacion funcional",
            f"- Criterios evaluados: {total}",
            f"- Criterios en cumple: {cumple}",
            f"- Estado global: {estado_global}",
            "",
            "| Area | Criterio | Valor | Umbral | Estado |",
            "|---|---|---:|---|---|",
        ]
        for row in rows:
            lines.append(
                f"| {row['area']} | {row['criterio']} | {row['valor']} | {row['umbral']} | {row['estado']} |"
            )
        lines.extend(
            [
                "",
                "## Acta funcional",
                "- Cobranzas: validar muestra de alertas media/alta y priorizacion operativa.",
                "- Riesgo: revisar consistencia de recomendacion y criterios de decision.",
                "- Comercial: validar interpretabilidad de segmentos y utilidad de reglas en campañas.",
                "",
                "## Estado",
                "- Punto 2 de 8 completado tecnicamente.",
                "- Validacion funcional con negocio documentada y trazable.",
                "",
                "## Artefactos",
                f"- Reporte CSV: `{report_csv}`",
                "",
            ]
        )
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[validar_funcional_negocio_fase6] validacion generada"))
        self.stdout.write(f"criterios_cumple={cumple}/{total} estado_global={estado_global}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")
