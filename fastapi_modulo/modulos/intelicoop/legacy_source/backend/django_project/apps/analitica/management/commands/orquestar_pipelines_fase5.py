import csv
import time
from datetime import datetime, timezone
from pathlib import Path

from django.core.management import call_command
from django.core.management.MAIN import MAINCommand
from django.db import IntegrityError
from django.utils import timezone as dj_timezone

from apps.analitica.models import EjecucionPipeline


class Command(MAINCommand):
    help = "Orquesta pipelines de Fase 5 con control idempotente y registro de ejecucion."

    def add_arguments(self, parser):
        parser.add_argument("--fecha-corte", help="Fecha de corrida YYYY-MM-DD. Default: hoy.")
        parser.add_argument("--run-id", default="manual", help="Identificador de corrida (ej. daily_0215).")
        parser.add_argument("--report-csv", default="docs/mineria/fase5/02_orquestacion_pipelines.csv")
        parser.add_argument("--report-md", default="docs/mineria/fase5/02_orquestacion_pipelines.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        fecha_corte = options["fecha_corte"] or str(dj_timezone.localdate())
        run_id = options["run_id"] or "manual"

        jobs = [
            {
                "pipeline": "mora_temprana_batch",
                "command": ("generar_alertas_mora_temprana",),
                "kwargs": {"fecha_corte": fecha_corte},
            },
            {
                "pipeline": "segmentacion_mensual",
                "command": ("generar_segmentacion_mensual_socios",),
                "kwargs": {"fecha_ejecucion": fecha_corte, "engine": "orm"},
            },
            {
                "pipeline": "segmentacion_inteligente_1_4",
                "command": ("segmentacion_inteligente_socios_1_4",),
                "kwargs": {"metodo": "reglas"},
            },
            {
                "pipeline": "acciones_campanas_segmentos_1_4",
                "command": ("activar_acciones_campanas_segmentos_1_4",),
                "kwargs": {},
            },
            {
                "pipeline": "reglas_asociacion",
                "command": ("generar_reglas_asociacion_productos",),
                "kwargs": {"fecha_ejecucion": fecha_corte},
            },
            {
                "pipeline": "integracion_submodulos",
                "command": ("integrar_submodulos_fase4",),
                "kwargs": {},
            },
            {
                "pipeline": "validacion_submodulos",
                "command": ("validar_submodulos_fase4",),
                "kwargs": {},
            },
        ]

        rows = []
        for job in jobs:
            pipeline = job["pipeline"]
            idempotency_key = f"{pipeline}:{fecha_corte}:{run_id}"

            start = dj_timezone.now()
            start_perf = time.perf_counter()
            estado = EjecucionPipeline.ESTADO_OK
            detalle = "ejecutado"
            skipped = False

            try:
                call_command(job["command"][0], **job["kwargs"])
                end = dj_timezone.now()
                duracion_ms = int((time.perf_counter() - start_perf) * 1000)
                try:
                    EjecucionPipeline.objects.create(
                        pipeline=pipeline,
                        fecha_inicio=start,
                        fecha_fin=end,
                        duracion_ms=duracion_ms,
                        estado=estado,
                        detalle=detalle,
                        idempotency_key=idempotency_key,
                    )
                except IntegrityError:
                    skipped = True
                    detalle = "omitido_por_idempotencia"
                    estado = EjecucionPipeline.ESTADO_OK
            except Exception as exc:  # pragma: no cover - defensive path
                end = dj_timezone.now()
                duracion_ms = int((time.perf_counter() - start_perf) * 1000)
                estado = EjecucionPipeline.ESTADO_ERROR
                detalle = str(exc)[:240]
                try:
                    EjecucionPipeline.objects.create(
                        pipeline=pipeline,
                        fecha_inicio=start,
                        fecha_fin=end,
                        duracion_ms=duracion_ms,
                        estado=estado,
                        detalle=detalle,
                        idempotency_key=idempotency_key,
                    )
                except IntegrityError:
                    skipped = True
                    detalle = "error_omitido_por_idempotencia"

            rows.append(
                {
                    "pipeline": pipeline,
                    "fecha_corte": fecha_corte,
                    "run_id": run_id,
                    "idempotency_key": idempotency_key,
                    "estado": estado,
                    "detalle": detalle,
                    "skipped": "si" if skipped else "no",
                }
            )

        ok_count = sum(1 for row in rows if row["estado"] == EjecucionPipeline.ESTADO_OK)
        skipped_count = sum(1 for row in rows if row["skipped"] == "si")

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["pipeline", "fecha_corte", "run_id", "idempotency_key", "estado", "detalle", "skipped"],
            )
            writer.writeheader()
            writer.writerows(rows)

        lines = [
            "# Orquestacion de Pipelines - Punto 2 de 8 (Fase 5)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            f"Fecha de corte: {fecha_corte}",
            f"Run ID: {run_id}",
            "",
            "## Resultado de orquestacion",
            f"- Pipelines planificados: {len(rows)}",
            f"- Pipelines OK: {ok_count}",
            f"- Pipelines omitidos por idempotencia: {skipped_count}",
            "",
            "## Estado",
            "- Punto 2 de 8 completado tecnicamente.",
            "- Orquestacion con registro de estado/duracion/idempotencia implementada.",
            "",
            "## Artefactos",
            f"- Reporte CSV: `{report_csv}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[orquestar_pipelines_fase5] orquestacion completada"))
        self.stdout.write(f"pipelines={len(rows)} ok={ok_count} skipped={skipped_count}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")
