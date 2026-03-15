import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand

from apps.analitica.models import (
    EjecucionPipeline,
    ReglaAsociacionProducto,
    ResultadoMoraTemprana,
    ResultadoScoring,
    ResultadoSegmentacionSocio,
)


def _json_dump(data: dict) -> str:
    return json.dumps(data, ensure_ascii=True, separators=(",", ":"))


class Command(MAINCommand):
    help = "Centraliza observabilidad y trazabilidad de inferencias/batch para Fase 5."

    def add_arguments(self, parser):
        parser.add_argument("--trace-csv", default="docs/mineria/fase5/06_trazabilidad_predicciones.csv")
        parser.add_argument("--changes-csv", default="docs/mineria/fase5/06_bitacora_cambios.csv")
        parser.add_argument("--logs-jsonl", default=".run/mineria/06_observabilidad_inferencias.jsonl")
        parser.add_argument("--report-md", default="docs/mineria/fase5/06_observabilidad_trazabilidad.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        trace_csv_opt = Path(options["trace_csv"])
        changes_csv_opt = Path(options["changes_csv"])
        logs_jsonl_opt = Path(options["logs_jsonl"])
        report_md_opt = Path(options["report_md"])

        trace_csv = trace_csv_opt if trace_csv_opt.is_absolute() else (root / trace_csv_opt)
        changes_csv = changes_csv_opt if changes_csv_opt.is_absolute() else (root / changes_csv_opt)
        logs_jsonl = logs_jsonl_opt if logs_jsonl_opt.is_absolute() else (root / logs_jsonl_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        traces = []

        for item in ResultadoScoring.objects.order_by("-id")[:200]:
            feature_set = {
                "ingreso_mensual": float(item.ingreso_mensual),
                "deuda_actual": float(item.deuda_actual),
                "antiguedad_meses": int(item.antiguedad_meses),
            }
            salida = {
                "score": float(item.score),
                "riesgo": item.riesgo,
                "recomendacion": item.recomendacion,
            }
            traces.append(
                {
                    "tipo_prediccion": "scoring",
                    "request_id": str(item.request_id),
                    "fecha_evento": item.fecha_creacion.isoformat(),
                    "entidad_id": item.socio_id or item.credito_id or 0,
                    "model_version": item.model_version,
                    "feature_set": _json_dump(feature_set),
                    "salida": _json_dump(salida),
                    "fuente": "online",
                }
            )

        for item in ResultadoMoraTemprana.objects.order_by("-id")[:200]:
            feature_set = {
                "cuota_estimada": float(item.cuota_estimada),
                "pagos_90d": float(item.pagos_90d),
                "ratio_pago_90d": float(item.ratio_pago_90d),
                "deuda_ingreso_ratio": float(item.deuda_ingreso_ratio),
            }
            salida = {
                "prob_mora_30d": float(item.prob_mora_30d),
                "prob_mora_60d": float(item.prob_mora_60d),
                "prob_mora_90d": float(item.prob_mora_90d),
                "alerta": item.alerta,
            }
            traces.append(
                {
                    "tipo_prediccion": "mora_temprana",
                    "request_id": str(item.request_id),
                    "fecha_evento": item.fecha_creacion.isoformat(),
                    "entidad_id": item.socio_id,
                    "model_version": item.model_version,
                    "feature_set": _json_dump(feature_set),
                    "salida": _json_dump(salida),
                    "fuente": item.fuente,
                }
            )

        for item in ResultadoSegmentacionSocio.objects.order_by("-id")[:200]:
            feature_set = {
                "saldo_total": float(item.saldo_total),
                "total_movimientos": float(item.total_movimientos),
                "cantidad_movimientos": int(item.cantidad_movimientos),
                "dias_desde_ultimo_movimiento": item.dias_desde_ultimo_movimiento,
                "total_creditos": int(item.total_creditos),
            }
            salida = {"segmento": item.segmento}
            traces.append(
                {
                    "tipo_prediccion": "segmentacion",
                    "request_id": str(item.request_id),
                    "fecha_evento": item.fecha_creacion.isoformat(),
                    "entidad_id": item.socio_id,
                    "model_version": item.model_version,
                    "feature_set": _json_dump(feature_set),
                    "salida": _json_dump(salida),
                    "fuente": "batch",
                }
            )

        for item in ReglaAsociacionProducto.objects.order_by("-id")[:200]:
            feature_set = {
                "antecedente": item.antecedente,
                "consecuente": item.consecuente,
                "casos_antecedente": int(item.casos_antecedente),
                "casos_regla": int(item.casos_regla),
            }
            salida = {
                "soporte": float(item.soporte),
                "confianza": float(item.confianza),
                "lift": float(item.lift),
                "oportunidad_comercial": item.oportunidad_comercial,
            }
            traces.append(
                {
                    "tipo_prediccion": "reglas_asociacion",
                    "request_id": str(item.request_id),
                    "fecha_evento": item.fecha_creacion.isoformat(),
                    "entidad_id": 0,
                    "model_version": item.model_version,
                    "feature_set": _json_dump(feature_set),
                    "salida": _json_dump(salida),
                    "fuente": "batch",
                }
            )

        trace_csv.parent.mkdir(parents=True, exist_ok=True)
        with trace_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "tipo_prediccion",
                    "request_id",
                    "fecha_evento",
                    "entidad_id",
                    "model_version",
                    "feature_set",
                    "salida",
                    "fuente",
                ],
            )
            writer.writeheader()
            writer.writerows(traces)

        logs_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with logs_jsonl.open("w", encoding="utf-8") as file:
            for row in traces:
                file.write(json.dumps(row, ensure_ascii=True) + "\n")

        cambios = []
        for run in EjecucionPipeline.objects.order_by("-id")[:200]:
            cambios.append(
                {
                    "fecha": run.fecha_creacion.isoformat(),
                    "tipo_cambio": "pipeline_run",
                    "referencia": run.pipeline,
                    "detalle": f"estado={run.estado};duracion_ms={run.duracion_ms};idempotency_key={run.idempotency_key}",
                }
            )

        promotion_manifest = root / "docs" / "mineria" / "fase5" / "03_reentrenamiento_promocion.json"
        if promotion_manifest.exists():
            payload = json.loads(promotion_manifest.read_text(encoding="utf-8"))
            cambios.append(
                {
                    "fecha": payload.get("promoted_at", ""),
                    "tipo_cambio": "model_promotion",
                    "referencia": payload.get("promoted_version", ""),
                    "detalle": f"source_model={payload.get('source_model','')}",
                }
            )

        changes_csv.parent.mkdir(parents=True, exist_ok=True)
        with changes_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["fecha", "tipo_cambio", "referencia", "detalle"])
            writer.writeheader()
            writer.writerows(cambios)

        lines = [
            "# Observabilidad y Trazabilidad - Punto 6 de 8 (Fase 5)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Centralizacion de logs",
            f"- Log central JSONL: `{logs_jsonl}`",
            f"- Eventos registrados: {len(traces)}",
            "",
            "## Trazabilidad de predicciones",
            "- Cada prediccion queda trazada a `request_id`, `model_version` y `feature_set`.",
            f"- Export consolidado: `{trace_csv}`",
            "",
            "## Bitacora de cambios",
            "- Se consolidan corridas de pipeline e hitos de promocion de modelo.",
            f"- Bitacora: `{changes_csv}`",
            "",
            "## Estado",
            "- Punto 6 de 8 completado tecnicamente.",
            "- Observabilidad y trazabilidad extremo a extremo implementadas.",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[observabilidad_trazabilidad_fase5] generado"))
        self.stdout.write(f"traces={len(traces)} cambios={len(cambios)}")
        self.stdout.write(f"trace_csv={trace_csv}")
        self.stdout.write(f"changes_csv={changes_csv}")
        self.stdout.write(f"logs_jsonl={logs_jsonl}")
        self.stdout.write(f"report_md={report_md}")
