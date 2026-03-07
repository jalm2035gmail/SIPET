from pathlib import Path
import sys

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Ejecuta la segmentación de socios y actualiza el campo segmento."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Calcula segmentos sin persistir cambios en base de datos.",
        )
        parser.add_argument(
            "--engine",
            choices=("auto", "orm", "pyspark"),
            default="auto",
            help="Motor de segmentación (auto/orm/pyspark).",
        )

    def handle(self, *args, **options):
        project_root = Path(__file__).resolve().parents[6]
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        from data_pipelines.spark_jobs.segmentacion_socios import ejecutar_segmentacion

        dry_run = options["dry_run"]
        engine = options["engine"]
        conteo = ejecutar_segmentacion(dry_run=dry_run, engine=engine)
        total = sum(conteo.values())
        modo = "DRY-RUN" if dry_run else "APLICADO"

        self.stdout.write(self.style.SUCCESS(f"[segmentar_socios] modo={modo} engine={engine} total={total}"))
        self.stdout.write(f"  - hormiga: {conteo.get('hormiga', 0)}")
        self.stdout.write(f"  - gran_ahorrador: {conteo.get('gran_ahorrador', 0)}")
        self.stdout.write(f"  - inactivo: {conteo.get('inactivo', 0)}")
