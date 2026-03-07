import csv
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.analitica.models import ResultadoMoraTemprana, ResultadoScoring


class Command(BaseCommand):
    help = "Define adopcion organizacional: entrenamiento, rutinas operativas y retroalimentacion priorizada (Fase 7)."

    def add_arguments(self, parser):
        parser.add_argument("--report-csv", default="docs/mineria/fase7/06_adopcion_organizacional.csv")
        parser.add_argument("--report-md", default="docs/mineria/fase7/06_adopcion_organizacional.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        # Base operativa para disenar adopcion
        total_scoring = ResultadoScoring.objects.count()
        total_mora = ResultadoMoraTemprana.objects.count()
        alertas_altas = ResultadoMoraTemprana.objects.filter(alerta=ResultadoMoraTemprana.ALERTA_ALTA).count()
        recomendaciones = {
            item["recomendacion"]: item["total"]
            for item in ResultadoScoring.objects.values("recomendacion").annotate(total=Count("id"))
        }

        plan_entrenamiento = [
            {
                "modulo": "interpretacion_scoring",
                "audiencia": "riesgo y originacion",
                "duracion_horas": "2",
                "objetivo": "interpretar score/recomendacion y excepciones",
                "estado": "Programado",
            },
            {
                "modulo": "gestion_alertas_mora",
                "audiencia": "cobranzas",
                "duracion_horas": "2",
                "objetivo": "priorizar alertas media/alta y medir recuperacion",
                "estado": "Programado",
            },
            {
                "modulo": "segmentacion_y_reglas",
                "audiencia": "comercial",
                "duracion_horas": "1.5",
                "objetivo": "usar segmentos y reglas para campanas",
                "estado": "Programado",
            },
        ]

        rutinas_operativas = [
            {
                "rutina": "revision_diaria_alertas_mora",
                "frecuencia": "diaria",
                "responsable": "equipo_cobranzas",
                "kpi": "alertas_altas_gestionadas_pct",
                "estado": "Activa",
            },
            {
                "rutina": "revision_scoring_originacion",
                "frecuencia": "diaria",
                "responsable": "equipo_riesgo",
                "kpi": "tiempo_respuesta_scoring",
                "estado": "Activa",
            },
            {
                "rutina": "revision_oportunidades_comerciales",
                "frecuencia": "semanal",
                "responsable": "equipo_comercial",
                "kpi": "conversion_campanas_pct",
                "estado": "Activa",
            },
        ]

        feedback_backlog = [
            {
                "feedback": "Explicar factores clave en scoring para casos en evaluacion",
                "valor": "Alto",
                "esfuerzo": "Medio",
                "prioridad": "P1",
                "responsable": "analitica_backend",
            },
            {
                "feedback": "Panel rapido de alertas altas por gestor de cobranza",
                "valor": "Alto",
                "esfuerzo": "Bajo",
                "prioridad": "P1",
                "responsable": "analitica_frontend",
            },
            {
                "feedback": "Comparador de segmentos historicos para campanas",
                "valor": "Medio",
                "esfuerzo": "Medio",
                "prioridad": "P2",
                "responsable": "equipo_comercial_datos",
            },
        ]

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["dimension", "item", "detalle", "estado"])
            writer.writeheader()
            for row in plan_entrenamiento:
                writer.writerow(
                    {
                        "dimension": "entrenamiento",
                        "item": row["modulo"],
                        "detalle": f"audiencia={row['audiencia']};duracion_horas={row['duracion_horas']};objetivo={row['objetivo']}",
                        "estado": row["estado"],
                    }
                )
            for row in rutinas_operativas:
                writer.writerow(
                    {
                        "dimension": "rutina_operativa",
                        "item": row["rutina"],
                        "detalle": f"frecuencia={row['frecuencia']};responsable={row['responsable']};kpi={row['kpi']}",
                        "estado": row["estado"],
                    }
                )
            for row in feedback_backlog:
                writer.writerow(
                    {
                        "dimension": "feedback_priorizado",
                        "item": row["feedback"],
                        "detalle": f"valor={row['valor']};esfuerzo={row['esfuerzo']};prioridad={row['prioridad']};responsable={row['responsable']}",
                        "estado": "Priorizado",
                    }
                )

        train_csv = report_csv.with_name("06_plan_entrenamiento_usuarios.csv")
        with train_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["modulo", "audiencia", "duracion_horas", "objetivo", "estado"])
            writer.writeheader()
            writer.writerows(plan_entrenamiento)

        routines_csv = report_csv.with_name("06_rutinas_operativas.csv")
        with routines_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["rutina", "frecuencia", "responsable", "kpi", "estado"])
            writer.writeheader()
            writer.writerows(rutinas_operativas)

        backlog_csv = report_csv.with_name("06_feedback_priorizado.csv")
        with backlog_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["feedback", "valor", "esfuerzo", "prioridad", "responsable"])
            writer.writeheader()
            writer.writerows(feedback_backlog)

        lines = [
            "# Adopcion Organizacional - Punto 6 de 8 (Fase 7)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Base operativa observada",
            f"- Registros de scoring historicos: {total_scoring}",
            f"- Alertas de mora historicas: {total_mora}",
            f"- Alertas altas: {alertas_altas}",
            f"- Recomendaciones scoring: {recomendaciones}",
            "",
            "## Componentes de adopcion",
            f"- Modulos de entrenamiento definidos: {len(plan_entrenamiento)}",
            f"- Rutinas operativas activas: {len(rutinas_operativas)}",
            f"- Feedback priorizado en backlog: {len(feedback_backlog)}",
            "",
            "## Estado",
            "- Punto 6 de 8 completado tecnicamente.",
            "- Adopcion organizacional implementada con plan de entrenamiento y rutina operativa.",
            "",
            "## Artefactos",
            f"- Consolidado: `{report_csv}`",
            f"- Entrenamiento: `{train_csv}`",
            f"- Rutinas: `{routines_csv}`",
            f"- Backlog feedback: `{backlog_csv}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[adopcion_organizacional_fase7] plan generado"))
        self.stdout.write(f"entrenamientos={len(plan_entrenamiento)} rutinas={len(rutinas_operativas)} feedback={len(feedback_backlog)}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")
