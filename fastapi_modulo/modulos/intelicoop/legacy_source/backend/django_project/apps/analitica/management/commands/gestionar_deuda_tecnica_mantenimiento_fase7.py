import csv
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Gestiona deuda tecnica y mantenimiento (calidad, dependencias y documentacion) para Fase 7."

    def add_arguments(self, parser):
        parser.add_argument("--report-csv", default="docs/mineria/fase7/05_deuda_tecnica_mantenimiento.csv")
        parser.add_argument("--report-md", default="docs/mineria/fase7/05_deuda_tecnica_mantenimiento.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        tests_file = root / "backend" / "django_project" / "apps" / "analitica" / "tests.py"
        tests_source = tests_file.read_text(encoding="utf-8")
        tests_count = tests_source.count("\n    def test_")

        commands_dir = root / "backend" / "django_project" / "apps" / "analitica" / "management" / "commands"
        command_files = [path for path in commands_dir.iterdir() if path.is_file() and path.suffix == ".py"]
        command_count = len(command_files)

        requirements_path = root / "backend" / "django_project" / "requirements.txt"
        requirements = [line.strip() for line in requirements_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        deps_with_upper_bound = sum(1 for line in requirements if "<" in line)
        deps_with_lower_bound = sum(1 for line in requirements if ">=" in line)
        deps_controlled = deps_with_upper_bound == len(requirements) and deps_with_lower_bound == len(requirements)

        fase7_readme = root / "docs" / "mineria" / "fase7" / "README.md"
        readme_text = fase7_readme.read_text(encoding="utf-8")
        commands_documented = readme_text.count("manage.py")
        expected_phase7_docs = [
            "01_monitoreo_continuo_desempeno.md",
            "02_gestion_drift_recalibracion.md",
            "03_mejora_incremental_modulo.md",
            "04_experimentacion_controlada.md",
        ]
        docs_present = sum(1 for name in expected_phase7_docs if (root / "docs" / "mineria" / "fase7" / name).exists())

        rows = [
            {
                "dimension": "calidad_codigo",
                "control": "pruebas_unitarias_disponibles",
                "valor": str(tests_count),
                "umbral": ">=45",
                "estado": "Cumple" if tests_count >= 45 else "En revision",
            },
            {
                "dimension": "calidad_codigo",
                "control": "comandos_operativos_disponibles",
                "valor": str(command_count),
                "umbral": ">=35",
                "estado": "Cumple" if command_count >= 35 else "En revision",
            },
            {
                "dimension": "dependencias",
                "control": "dependencias_con_rango_controlado",
                "valor": f"{deps_with_lower_bound}/{len(requirements)} lower, {deps_with_upper_bound}/{len(requirements)} upper",
                "umbral": "100% con >= y <",
                "estado": "Cumple" if deps_controlled else "En revision",
            },
            {
                "dimension": "documentacion",
                "control": "comandos_fase7_documentados",
                "valor": str(commands_documented),
                "umbral": ">=4",
                "estado": "Cumple" if commands_documented >= 4 else "En revision",
            },
            {
                "dimension": "documentacion",
                "control": "evidencias_fase7_presentes",
                "valor": f"{docs_present}/{len(expected_phase7_docs)}",
                "umbral": "4/4",
                "estado": "Cumple" if docs_present == len(expected_phase7_docs) else "En revision",
            },
        ]

        backlog = [
            {
                "item": "Automatizar ejecucion periodica de pruebas con cobertura historica",
                "prioridad": "Alta",
                "estado": "Pendiente",
                "responsable": "equipo_backend",
            },
            {
                "item": "Definir calendario mensual de actualizacion controlada de dependencias",
                "prioridad": "Media",
                "estado": "Pendiente",
                "responsable": "equipo_plataforma",
            },
            {
                "item": "Agregar checklist de actualizacion documental por cada cambio de fase",
                "prioridad": "Media",
                "estado": "Pendiente",
                "responsable": "equipo_analitica",
            },
        ]

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["dimension", "control", "valor", "umbral", "estado"])
            writer.writeheader()
            writer.writerows(rows)

        backlog_csv = report_csv.with_name("05_deuda_tecnica_backlog.csv")
        with backlog_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["item", "prioridad", "estado", "responsable"])
            writer.writeheader()
            writer.writerows(backlog)

        cumple = sum(1 for row in rows if row["estado"] == "Cumple")
        total = len(rows)
        estado_global = "Mantenimiento operativo" if cumple >= (total - 1) else "Mantenimiento en revision"
        lines = [
            "# Gestion de Deuda Tecnica y Mantenimiento - Punto 5 de 8 (Fase 7)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Revisiones periodicas",
            f"- Pruebas detectadas en analitica/tests.py: {tests_count}",
            f"- Comandos operativos disponibles: {command_count}",
            f"- Dependencias con rango controlado: {'si' if deps_controlled else 'no'}",
            f"- Comandos Fase 7 documentados: {commands_documented}",
            "",
            "## Resultado",
            f"- Controles en cumple: {cumple}/{total}",
            f"- Estado global: {estado_global}",
            "",
            "## Backlog de mantenimiento",
            f"- Backlog exportado: `{backlog_csv}`",
            "",
            "## Estado",
            "- Punto 5 de 8 completado tecnicamente.",
            "- Gestion de deuda tecnica y mantenimiento implementada con evidencia reproducible.",
            "",
            "## Artefactos",
            f"- Reporte CSV: `{report_csv}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[gestionar_deuda_tecnica_mantenimiento_fase7] gestion generada"))
        self.stdout.write(f"controles_cumple={cumple}/{total} estado_global={estado_global}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"backlog_csv={backlog_csv}")
        self.stdout.write(f"report_md={report_md}")
