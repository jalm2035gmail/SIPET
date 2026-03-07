import json
from datetime import datetime, timezone
from pathlib import Path

from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = "1.8 Programacion: refresca dashboards ejecutivos-operativos y registra ultima actualizacion para ejecucion automatizada (cron)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--estado-json",
            default="docs/mineria/dashboards/08_estado_actualizacion.json",
            help="Ruta de salida para estado de actualizacion.",
        )
        parser.add_argument(
            "--fuente-ejecucion",
            default="cron",
            help="Etiqueta de origen de la ejecucion (cron/manual/pipeline).",
        )

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        estado_opt = Path(options["estado_json"])
        estado_json = estado_opt if estado_opt.is_absolute() else (root / estado_opt)
        estado_json.parent.mkdir(parents=True, exist_ok=True)

        started_at = datetime.now(timezone.utc)
        call_command("dashboards_ejecutivos_operativos_1_8")
        finished_at = datetime.now(timezone.utc)

        payload = {
            "modulo": "dashboards_1_8",
            "estado": "ok",
            "fuente_ejecucion": options["fuente_ejecucion"],
            "ultima_actualizacion_utc": finished_at.isoformat(),
            "inicio_utc": started_at.isoformat(),
            "duracion_ms": int((finished_at - started_at).total_seconds() * 1000),
            "frecuencia_sugerida": "cada 60 minutos",
            "siguiente_paso": "Programar en cron: 0 * * * * <python> manage.py actualizar_dashboards_programado_1_8",
        }
        estado_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[actualizar_dashboards_programado_1_8] actualizacion registrada"))
        self.stdout.write(f"estado_json={estado_json}")
