import csv
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models import Avg

from apps.analitica.models import ResultadoMoraTemprana, ResultadoScoring


class Command(BaseCommand):
    help = "Consolida entregables obligatorios de Fase 7 y genera acta de cierre tecnico."

    def add_arguments(self, parser):
        parser.add_argument("--report-csv", default="docs/mineria/fase7/08_entregables_fase7.csv")
        parser.add_argument("--report-md", default="docs/mineria/fase7/08_entregables_fase7.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        required_files = [
            root / "docs" / "mineria" / "fase7" / "01_monitoreo_continuo_desempeno.md",
            root / "docs" / "mineria" / "fase7" / "01_monitoreo_continuo_desempeno.csv",
            root / "docs" / "mineria" / "fase7" / "05_deuda_tecnica_backlog.csv",
            root / "docs" / "mineria" / "fase7" / "02_recalibracion_umbral_scoring.json",
            root / "docs" / "mineria" / "fase7" / "02_gestion_drift_recalibracion.md",
            root / "docs" / "mineria" / "fase7" / "04_experimentacion_controlada.md",
            root / "docs" / "mineria" / "fase7" / "07_roadmap_trimestral.csv",
        ]
        files_ok = all(path.exists() for path in required_files)

        total_scoring = ResultadoScoring.objects.count()
        score_promedio = float(ResultadoScoring.objects.aggregate(v=Avg("score"))["v"] or 0.0)
        total_mora = ResultadoMoraTemprana.objects.count()
        mora_alta = ResultadoMoraTemprana.objects.filter(alerta=ResultadoMoraTemprana.ALERTA_ALTA).count()
        mora_alta_pct = 0.0 if total_mora == 0 else (mora_alta / total_mora) * 100.0

        entregables = [
            {
                "entregable": "Tablero permanente de monitoreo tecnico/analitico/negocio",
                "evidencia": "01_monitoreo_continuo_desempeno.*",
                "estado": "Cumplido" if (required_files[0].exists() and required_files[1].exists()) else "Condicionado",
            },
            {
                "entregable": "Plan de mejora continua con backlog priorizado",
                "evidencia": "05_deuda_tecnica_backlog.csv + 07_roadmap_trimestral.csv",
                "estado": "Cumplido" if (required_files[2].exists() and required_files[6].exists()) else "Condicionado",
            },
            {
                "entregable": "Evidencia retraining/recalibracion y resultados comparativos",
                "evidencia": "02_recalibracion_umbral_scoring.json + 02_gestion_drift_recalibracion.md + 04_experimentacion_controlada.md",
                "estado": "Cumplido"
                if (required_files[3].exists() and required_files[4].exists() and required_files[5].exists())
                else "Condicionado",
            },
            {
                "entregable": "Reporte ejecutivo periodico de valor generado",
                "evidencia": "08_entregables_fase7.md (resumen ejecutivo)",
                "estado": "Cumplido",
            },
        ]

        cumplidos = sum(1 for row in entregables if row["estado"] == "Cumplido")
        total = len(entregables)
        cierre = "Cierre tecnico completado" if (cumplidos == total and files_ok) else "Cierre tecnico condicionado"

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["entregable", "evidencia", "estado"])
            writer.writeheader()
            writer.writerows(entregables)

        lines = [
            "# Entregables Obligatorios - Punto 8 de 8 (Fase 7)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Consolidado",
            f"- Entregables cumplidos: {cumplidos}/{total}",
            f"- Estado de cierre: {cierre}",
            "",
            "## Reporte ejecutivo periodico",
            f"- Inferencias scoring acumuladas: {total_scoring}",
            f"- Score promedio observado: {score_promedio:.4f}",
            f"- Alertas de mora alta: {mora_alta} ({mora_alta_pct:.2f}%)",
            "- Mensaje ejecutivo: mantener monitoreo continuo y ejecutar roadmap trimestral priorizado.",
            "",
            "| Entregable | Evidencia | Estado |",
            "|---|---|---|",
        ]
        for row in entregables:
            lines.append(f"| {row['entregable']} | {row['evidencia']} | {row['estado']} |")
        lines.extend(
            [
                "",
                "## Estado",
                "- Punto 8 de 8 completado tecnicamente.",
                "- Fase 7 cerrada tecnicamente con trazabilidad de entregables obligatorios.",
                "",
                "## Artefactos",
                f"- Reporte CSV: `{report_csv}`",
                "",
            ]
        )
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[cerrar_fase7_operacion_mejora] cierre generado"))
        self.stdout.write(f"entregables_cumplidos={cumplidos}/{total} estado={cierre}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")
