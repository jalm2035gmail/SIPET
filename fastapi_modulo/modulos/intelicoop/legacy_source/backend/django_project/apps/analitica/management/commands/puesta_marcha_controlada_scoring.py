import csv
import statistics
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand

from apps.analitica.models import ResultadoScoring


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((percentile / 100.0) * (len(ordered) - 1)))
    return float(ordered[index])


class Command(MAINCommand):
    help = "Genera plan de puesta en marcha controlada (canary) y criterios de rollback del scoring MVP."

    def add_arguments(self, parser):
        parser.add_argument("--window", type=int, default=200, help="Cantidad de inferencias recientes para monitoreo.")
        parser.add_argument("--max-error-rate", type=float, default=1.0, help="Error rate maximo permitido (%).")
        parser.add_argument("--max-p95-ms", type=float, default=500.0, help="P95 maximo permitido (ms).")
        parser.add_argument(
            "--load-csv",
            default="docs/mineria/fase3/08_prueba_carga_scoring_mvp.csv",
        )
        parser.add_argument(
            "--report-csv",
            default="docs/mineria/fase3/10_puesta_marcha_controlada_scoring.csv",
        )
        parser.add_argument(
            "--report-md",
            default="docs/mineria/fase3/10_puesta_marcha_controlada_scoring.md",
        )

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        load_csv_opt = Path(options["load_csv"])
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        load_csv = load_csv_opt if load_csv_opt.is_absolute() else (root / load_csv_opt)
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        max_error_rate = float(options["max_error_rate"])
        max_p95_ms = float(options["max_p95_ms"])
        monitor_window = int(options["window"])

        latencies = []
        status_codes = []
        if load_csv.exists():
            with load_csv.open("r", encoding="utf-8") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    try:
                        status_codes.append(int(row.get("status_code", "0")))
                    except ValueError:
                        status_codes.append(0)
                    try:
                        latencies.append(float(row.get("latency_ms", "0")))
                    except ValueError:
                        latencies.append(0.0)

        total_load = len(status_codes)
        ok_load = len([code for code in status_codes if code == 200])
        error_rate = 0.0 if total_load == 0 else ((total_load - ok_load) / total_load) * 100.0
        p95_ms = _percentile(latencies, 95)
        avg_ms = statistics.fmean(latencies) if latencies else 0.0

        recent = list(
            ResultadoScoring.objects.order_by("-id").values("riesgo", "recomendacion", "fecha_creacion")[:monitor_window]
        )
        total_recent = len(recent)
        altos = len([item for item in recent if item["riesgo"] == "alto"])
        tasa_alto = 0.0 if total_recent == 0 else (altos / total_recent) * 100.0

        gate_latency = p95_ms <= max_p95_ms if total_load > 0 else False
        gate_error = error_rate <= max_error_rate if total_load > 0 else False
        gate_data = total_recent >= 20
        gate_risk = tasa_alto <= 50.0 if total_recent > 0 else False
        gates_ok = gate_latency and gate_error and gate_data and gate_risk

        phases = [
            ("canary_10", 10, "Monitorear errores, latencia y distribucion de riesgo."),
            ("canary_30", 30, "Validar estabilidad operativa y consistencia del scoring."),
            ("canary_60", 60, "Expandir cobertura con monitoreo continuo de compuertas."),
            ("rollout_100", 100, "Activacion total con monitoreo post-despliegue."),
        ]
        current_phase = phases[0][0] if gates_ok else "hold"
        recommendation = "continuar_canary" if gates_ok else "rollback_o_congelar"

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["fase", "porcentaje_trafico", "criterio_operativo", "estado"],
            )
            writer.writeheader()
            for idx, (fase, pct, criterio) in enumerate(phases):
                estado = "habilitada" if gates_ok and idx == 0 else ("pendiente" if gates_ok else "bloqueada")
                writer.writerow(
                    {
                        "fase": fase,
                        "porcentaje_trafico": pct,
                        "criterio_operativo": criterio,
                        "estado": estado,
                    }
                )

        lines = [
            "# Puesta en Marcha Controlada - Punto 8 de 8 (Fase 3)",
            "",
            f"Fecha: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Compuertas de despliegue",
            f"- Error rate de carga <= {max_error_rate:.2f}%: {'cumple' if gate_error else 'no cumple'} (actual={error_rate:.2f}%)",
            f"- Latencia p95 <= {max_p95_ms:.2f} ms: {'cumple' if gate_latency else 'no cumple'} (actual={p95_ms:.2f} ms)",
            f"- Ventana minima de monitoreo ({monitor_window}): {'cumple' if gate_data else 'no cumple'} (actual={total_recent})",
            f"- Riesgo alto <= 50%: {'cumple' if gate_risk else 'no cumple'} (actual={tasa_alto:.2f}%)",
            "",
            "## Estado operativo",
            f"- Fase actual: `{current_phase}`",
            f"- Recomendacion: `{recommendation}`",
            f"- Latencia promedio observada: {avg_ms:.2f} ms",
            "",
            "## Criterios de rollback y contingencia",
            "- Activar rollback si error rate supera 1% durante 15 minutos continuos.",
            "- Activar rollback si p95 supera 500 ms durante 3 ventanas consecutivas.",
            "- Congelar avance de canary si riesgo alto supera 50% frente a MAINline operativo.",
            "- Contingencia: retornar al modelo/version previa y mantener inferencia en modo manual.",
            "",
            "## Artefactos",
            f"- Plan canary: `{report_csv}`",
            f"- Fuente carga: `{load_csv}`",
            "",
            "## Estado",
            "- Punto 8 de 8 completado tecnicamente.",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[puesta_marcha_controlada_scoring] plan generado"))
        self.stdout.write(f"gates_ok={gates_ok} current_phase={current_phase} recommendation={recommendation}")
        self.stdout.write(f"error_rate={error_rate:.2f}% p95_ms={p95_ms:.2f} avg_ms={avg_ms:.2f}")
        self.stdout.write(f"recent_total={total_recent} riesgo_alto={tasa_alto:.2f}%")
        self.stdout.write(f"report={report_md}")
