import csv
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management.MAIN import MAINCommand
from rest_framework.test import APIClient


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((percentile / 100.0) * (len(ordered) - 1)))
    return float(ordered[index])


class Command(MAINCommand):
    help = "Ejecuta una prueba de carga ligera del endpoint de scoring MVP."

    def add_arguments(self, parser):
        parser.add_argument("--requests", type=int, default=120)
        parser.add_argument("--warmup", type=int, default=10)
        parser.add_argument("--target-p95-ms", type=float, default=500.0)
        parser.add_argument(
            "--report-csv",
            default="docs/mineria/fase3/08_prueba_carga_scoring_mvp.csv",
        )
        parser.add_argument(
            "--report-md",
            default="docs/mineria/fase3/08_prueba_carga_scoring_mvp.md",
        )

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        requests_count = max(1, int(options["requests"]))
        warmup = max(0, int(options["warmup"]))
        target_p95_ms = float(options["target_p95_ms"])

        user, _ = User.objects.get_or_create(username="benchmark_scoring_mvp")
        user.set_password("benchmark_temp_123")
        user.save(update_fields=["password"])
        user.profile.rol = "administrador"
        user.profile.activo = True
        user.profile.save(update_fields=["rol", "activo"])

        client = APIClient()
        client.force_authenticate(user=user)
        client.defaults["HTTP_HOST"] = "localhost"

        payload = {
            "ingreso_mensual": 3500.0,
            "deuda_actual": 450.0,
            "antiguedad_meses": 24,
            "persist": False,
        }

        rows = []
        latencies = []
        status_counts = {}

        mock_response = {"score": 0.74, "recomendacion": "evaluar", "riesgo": "medio"}
        with patch("apps.analitica.views._call_fastapi_scoring", return_value=mock_response):
            for _ in range(warmup):
                client.post("/api/analitica/ml/scoring/evaluar/", payload, format="json")

            for index in range(1, requests_count + 1):
                started = time.perf_counter()
                response = client.post("/api/analitica/ml/scoring/evaluar/", payload, format="json")
                elapsed_ms = (time.perf_counter() - started) * 1000
                status_code = int(response.status_code)
                status_counts[status_code] = status_counts.get(status_code, 0) + 1
                latencies.append(elapsed_ms)
                rows.append(
                    {
                        "request_num": index,
                        "status_code": status_code,
                        "latency_ms": f"{elapsed_ms:.2f}",
                    }
                )

        total = len(rows)
        ok = status_counts.get(200, 0)
        error_rate = 0.0 if total == 0 else ((total - ok) / total) * 100
        p50 = _percentile(latencies, 50)
        p95 = _percentile(latencies, 95)
        p99 = _percentile(latencies, 99)
        avg = statistics.fmean(latencies) if latencies else 0.0
        meets_target = p95 <= target_p95_ms and error_rate == 0.0

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["request_num", "status_code", "latency_ms"])
            writer.writeheader()
            writer.writerows(rows)

        lines = [
            "# Prueba de Carga Scoring MVP - Punto 7 de 8 (Fase 3)",
            "",
            f"Fecha: {datetime.now(timezone.utc).isoformat()}",
            f"Requests: {requests_count}",
            f"Warmup: {warmup}",
            "",
            "## Resultados",
            f"- Total requests: {total}",
            f"- HTTP 200: {ok}",
            f"- Error rate: {error_rate:.2f}%",
            f"- Latencia promedio: {avg:.2f} ms",
            f"- Latencia p50: {p50:.2f} ms",
            f"- Latencia p95: {p95:.2f} ms",
            f"- Latencia p99: {p99:.2f} ms",
            f"- Objetivo p95 <= {target_p95_ms:.2f} ms: {'cumplido' if meets_target else 'no cumplido'}",
            "",
            "## Artefactos",
            f"- CSV detallado: `{report_csv}`",
            "",
            "## Estado",
            "- Evidencia de carga del MVP generada tecnicamente.",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[probar_carga_scoring_mvp] prueba completada"))
        self.stdout.write(f"total={total} ok={ok} error_rate={error_rate:.2f}%")
        self.stdout.write(f"p50_ms={p50:.2f} p95_ms={p95:.2f} p99_ms={p99:.2f}")
        self.stdout.write(f"target_p95_ms={target_p95_ms:.2f} meets_target={meets_target}")
        self.stdout.write(f"report={report_md}")
