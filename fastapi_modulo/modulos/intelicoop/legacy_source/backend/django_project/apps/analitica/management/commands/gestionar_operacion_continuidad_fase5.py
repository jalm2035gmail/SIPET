import csv
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Genera runbook operativo, procedimientos de rollback y plan de continuidad (Fase 5)."

    def add_arguments(self, parser):
        parser.add_argument("--runbook-csv", default="docs/mineria/fase5/07_runbook_operativo.csv")
        parser.add_argument("--continuidad-csv", default="docs/mineria/fase5/07_continuidad_recuperacion.csv")
        parser.add_argument("--report-md", default="docs/mineria/fase5/07_gestion_operativa_continuidad.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        runbook_csv_opt = Path(options["runbook_csv"])
        continuidad_csv_opt = Path(options["continuidad_csv"])
        report_md_opt = Path(options["report_md"])
        runbook_csv = runbook_csv_opt if runbook_csv_opt.is_absolute() else (root / runbook_csv_opt)
        continuidad_csv = continuidad_csv_opt if continuidad_csv_opt.is_absolute() else (root / continuidad_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        runbook_rows = [
            {
                "proceso": "salud_api_scoring",
                "frecuencia": "cada_5_min",
                "accion": "verificar /api/health y /api/v1/analitica/ml/scoring/resumen/",
                "responsable": "equipo_plataforma",
                "escalamiento": "oncall_plataforma_15min",
            },
            {
                "proceso": "ejecucion_batch_diaria",
                "frecuencia": "diario_02:15_04:00",
                "accion": "ejecutar orquestar_pipelines_fase5 y validar estado en EjecucionPipeline",
                "responsable": "equipo_datos",
                "escalamiento": "oncall_datos_30min",
            },
            {
                "proceso": "monitoreo_alertas",
                "frecuencia": "diario_05:00",
                "accion": "ejecutar monitorear_alertamiento_fase5 y clasificar alertas activas",
                "responsable": "equipo_modelo",
                "escalamiento": "comite_riesgo_2h",
            },
            {
                "proceso": "reentrenamiento_programado",
                "frecuencia": "semanal",
                "accion": "ejecutar automatizar_reentrenamiento_fase5 y revisar promocion",
                "responsable": "equipo_modelo",
                "escalamiento": "arquitectura_datos_24h",
            },
        ]

        continuidad_rows = [
            {
                "escenario": "falla_modelo_scoring",
                "deteccion": "error_rate_api > 5% o respuestas invalidas",
                "rollback": "restaurar backup modelo_scoring.pkl previo",
                "rto_objetivo": "30_min",
                "rpo_objetivo": "1_hora",
                "responsable": "equipo_modelo",
            },
            {
                "escenario": "falla_pipeline_batch",
                "deteccion": "estado=error en EjecucionPipeline",
                "rollback": "reintentar job con run_id nuevo y revisar idempotencia",
                "rto_objetivo": "60_min",
                "rpo_objetivo": "24_horas",
                "responsable": "equipo_datos",
            },
            {
                "escenario": "degradacion_db_o_cache",
                "deteccion": "latencia API sostenida o timeout redis/postgres",
                "rollback": "failover a instancia standby y reinicio controlado de servicios",
                "rto_objetivo": "45_min",
                "rpo_objetivo": "15_min",
                "responsable": "equipo_plataforma",
            },
            {
                "escenario": "incidente_seguridad_api",
                "deteccion": "patrones anómalos auth/rate-limit o acceso no autorizado",
                "rollback": "rotar credenciales, bloquear tokens y restringir rutas sensibles",
                "rto_objetivo": "30_min",
                "rpo_objetivo": "inmediato",
                "responsable": "seguridad_ti",
            },
        ]

        runbook_csv.parent.mkdir(parents=True, exist_ok=True)
        with runbook_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["proceso", "frecuencia", "accion", "responsable", "escalamiento"],
            )
            writer.writeheader()
            writer.writerows(runbook_rows)

        continuidad_csv.parent.mkdir(parents=True, exist_ok=True)
        with continuidad_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["escenario", "deteccion", "rollback", "rto_objetivo", "rpo_objetivo", "responsable"],
            )
            writer.writeheader()
            writer.writerows(continuidad_rows)

        lines = [
            "# Gestion Operativa y Continuidad - Punto 7 de 8 (Fase 5)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Runbook operativo",
            f"- Procesos operativos definidos: {len(runbook_rows)}",
            f"- Evidencia: `{runbook_csv}`",
            "",
            "## Rollback y continuidad",
            f"- Escenarios de contingencia definidos: {len(continuidad_rows)}",
            f"- Evidencia: `{continuidad_csv}`",
            "",
            "## Objetivos operativos",
            "- RTO y RPO establecidos por escenario.",
            "- Escalamiento definido por dominio (plataforma/datos/modelo/seguridad).",
            "",
            "## Estado",
            "- Punto 7 de 8 completado tecnicamente.",
            "- Runbook y protocolo de continuidad/recuperacion documentados.",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[gestionar_operacion_continuidad_fase5] gestion generada"))
        self.stdout.write(f"runbook_items={len(runbook_rows)} continuidad_escenarios={len(continuidad_rows)}")
        self.stdout.write(f"runbook_csv={runbook_csv}")
        self.stdout.write(f"continuidad_csv={continuidad_csv}")
        self.stdout.write(f"report_md={report_md}")
