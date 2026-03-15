import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.core.management import call_command
from django.core.management.MAIN import MAINCommand
from django.db.models import Avg
from django.utils import timezone as dj_timezone

from apps.analitica.models import ResultadoScoring


class Command(MAINCommand):
    help = "Detecta drift, recalibra umbrales de scoring y dispara reentrenamiento segun metricas (Fase 7)."

    def add_arguments(self, parser):
        parser.add_argument("--drift-threshold", type=float, default=0.15)
        parser.add_argument("--min-approval-rate", type=float, default=20.0)
        parser.add_argument("--max-approval-rate", type=float, default=80.0)
        parser.add_argument("--max-high-risk-rate", type=float, default=40.0)
        parser.add_argument("--execute-retrain", action="store_true")
        parser.add_argument("--run-id", default="fase7_drift")
        parser.add_argument("--report-csv", default="docs/mineria/fase7/02_gestion_drift_recalibracion.csv")
        parser.add_argument("--report-md", default="docs/mineria/fase7/02_gestion_drift_recalibracion.md")
        parser.add_argument("--thresholds-json", default="docs/mineria/fase7/02_recalibracion_umbral_scoring.json")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        thresholds_json_opt = Path(options["thresholds_json"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)
        thresholds_json = thresholds_json_opt if thresholds_json_opt.is_absolute() else (root / thresholds_json_opt)

        now = dj_timezone.now()
        since_30d = now - timedelta(days=30)
        since_7d = now - timedelta(days=7)

        scoring_30d = ResultadoScoring.objects.filter(fecha_creacion__gte=since_30d)
        scoring_7d = ResultadoScoring.objects.filter(fecha_creacion__gte=since_7d)
        n_30d = scoring_30d.count()
        n_7d = scoring_7d.count()

        avg_30d = float(scoring_30d.aggregate(v=Avg("score"))["v"] or 0.0)
        avg_7d = float(scoring_7d.aggregate(v=Avg("score"))["v"] or 0.0)
        drift_abs = abs(avg_7d - avg_30d)

        aprobados_30d = scoring_30d.filter(recomendacion="aprobar").count()
        approval_rate = 0.0 if n_30d == 0 else (aprobados_30d / n_30d) * 100.0
        riesgo_alto_30d = scoring_30d.filter(riesgo=ResultadoScoring.RIESGO_ALTO).count()
        high_risk_rate = 0.0 if n_30d == 0 else (riesgo_alto_30d / n_30d) * 100.0

        drift_detected = drift_abs >= float(options["drift_threshold"])
        approval_out_of_range = approval_rate < float(options["min_approval_rate"]) or approval_rate > float(
            options["max_approval_rate"]
        )
        risk_too_high = high_risk_rate > float(options["max_high_risk_rate"])

        # Umbrales MAIN: score >= 0.80 aprobar, < 0.60 rechazar.
        threshold_approve = 0.80
        threshold_reject = 0.60
        recalibration_reason = []

        if drift_detected:
            threshold_approve = min(0.90, threshold_approve + 0.03)
            threshold_reject = min(threshold_approve - 0.05, threshold_reject + 0.03)
            recalibration_reason.append("drift_detectado")
        if risk_too_high:
            threshold_approve = min(0.92, threshold_approve + 0.02)
            threshold_reject = min(threshold_approve - 0.05, threshold_reject + 0.02)
            recalibration_reason.append("riesgo_alto_excesivo")
        if approval_rate < float(options["min_approval_rate"]):
            threshold_approve = max(0.70, threshold_approve - 0.03)
            threshold_reject = max(0.45, threshold_reject - 0.02)
            recalibration_reason.append("aprobacion_baja")
        if approval_rate > float(options["max_approval_rate"]):
            threshold_approve = min(0.92, threshold_approve + 0.03)
            threshold_reject = min(threshold_approve - 0.05, threshold_reject + 0.02)
            recalibration_reason.append("aprobacion_alta")

        recalibrated = bool(recalibration_reason)
        retrain_required = drift_detected or risk_too_high

        retrain_action = "no_disparado"
        if retrain_required:
            if options["execute_retrain"]:
                call_command(
                    "automatizar_reentrenamiento_fase5",
                    run_id=str(options["run_id"]),
                    force=True,
                    report_csv=str(root / "docs" / "mineria" / "fase7" / "02_reentrenamiento_disparado.csv"),
                    report_md=str(root / "docs" / "mineria" / "fase7" / "02_reentrenamiento_disparado.md"),
                )
                retrain_action = "reentrenamiento_ejecutado"
            else:
                call_command(
                    "automatizar_reentrenamiento_fase5",
                    run_id=f"{options['run_id']}_dry_run",
                    dry_run=True,
                    force=True,
                    report_csv=str(root / "docs" / "mineria" / "fase7" / "02_reentrenamiento_disparado.csv"),
                    report_md=str(root / "docs" / "mineria" / "fase7" / "02_reentrenamiento_disparado.md"),
                )
                retrain_action = "reentrenamiento_dry_run"

        thresholds_payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "window_7d_samples": n_7d,
            "window_30d_samples": n_30d,
            "drift_abs_score": round(drift_abs, 6),
            "approval_rate_pct": round(approval_rate, 2),
            "high_risk_rate_pct": round(high_risk_rate, 2),
            "thresholds": {
                "approve_if_score_gte": round(threshold_approve, 4),
                "reject_if_score_lt": round(threshold_reject, 4),
            },
            "recalibrated": recalibrated,
            "recalibration_reason": recalibration_reason,
            "retrain_required": retrain_required,
            "retrain_action": retrain_action,
        }
        thresholds_json.parent.mkdir(parents=True, exist_ok=True)
        thresholds_json.write_text(json.dumps(thresholds_payload, ensure_ascii=True, indent=2), encoding="utf-8")

        rows = [
            {"dimension": "drift", "metrica": "drift_abs_score_7d_vs_30d", "valor": f"{drift_abs:.4f}", "umbral": f"<={float(options['drift_threshold']):.4f}", "estado": "Cumple" if not drift_detected else "En revision"},
            {"dimension": "calibracion", "metrica": "approval_rate_30d_pct", "valor": f"{approval_rate:.2f}", "umbral": f"{float(options['min_approval_rate']):.2f}-{float(options['max_approval_rate']):.2f}", "estado": "Cumple" if not approval_out_of_range else "En revision"},
            {"dimension": "calibracion", "metrica": "high_risk_rate_30d_pct", "valor": f"{high_risk_rate:.2f}", "umbral": f"<={float(options['max_high_risk_rate']):.2f}", "estado": "Cumple" if not risk_too_high else "En revision"},
            {"dimension": "calibracion", "metrica": "threshold_approve", "valor": f"{threshold_approve:.4f}", "umbral": "ajuste_dinamico", "estado": "Cumple"},
            {"dimension": "calibracion", "metrica": "threshold_reject", "valor": f"{threshold_reject:.4f}", "umbral": "ajuste_dinamico", "estado": "Cumple"},
            {"dimension": "reentrenamiento", "metrica": "retrain_required", "valor": "si" if retrain_required else "no", "umbral": "si_hay_drift_o_riesgo_alto", "estado": "Cumple"},
            {"dimension": "reentrenamiento", "metrica": "retrain_action", "valor": retrain_action, "umbral": "dry_run_o_ejecucion", "estado": "Cumple"},
        ]

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["dimension", "metrica", "valor", "umbral", "estado"])
            writer.writeheader()
            writer.writerows(rows)

        cumple = sum(1 for row in rows if row["estado"] == "Cumple")
        total = len(rows)
        estado_global = "Gestion de drift operativa" if cumple >= (total - 1) else "Gestion de drift en revision"
        lines = [
            "# Gestion de Drift y Recalibracion - Punto 2 de 8 (Fase 7)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Deteccion de drift",
            f"- Muestras scoring 7d: {n_7d}",
            f"- Muestras scoring 30d: {n_30d}",
            f"- Drift abs(score): {drift_abs:.4f} (umbral<={float(options['drift_threshold']):.4f})",
            "",
            "## Recalibracion de umbrales",
            f"- Threshold aprobar (score>=): {threshold_approve:.4f}",
            f"- Threshold rechazar (score<): {threshold_reject:.4f}",
            f"- Recalibrado: {'si' if recalibrated else 'no'}",
            f"- Motivos: {', '.join(recalibration_reason) if recalibration_reason else 'sin_ajustes'}",
            "",
            "## Reentrenamiento",
            f"- Requerido: {'si' if retrain_required else 'no'}",
            f"- Accion: {retrain_action}",
            "",
            "## Estado",
            "- Punto 2 de 8 completado tecnicamente.",
            "- Gestion de drift y recalibracion implementada con disparo de reentrenamiento.",
            f"- Estado global: {estado_global}",
            "",
            "## Artefactos",
            f"- Reporte CSV: `{report_csv}`",
            f"- Umbrales recalibrados: `{thresholds_json}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[gestionar_drift_recalibracion_fase7] gestion generada"))
        self.stdout.write(f"drift_detected={'si' if drift_detected else 'no'} retrain_required={'si' if retrain_required else 'no'} action={retrain_action}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")
        self.stdout.write(f"thresholds_json={thresholds_json}")
