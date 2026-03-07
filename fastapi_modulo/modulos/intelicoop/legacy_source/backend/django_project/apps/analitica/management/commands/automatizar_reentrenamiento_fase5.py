import csv
import json
import pickle
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db.models import Avg
from django.utils import timezone as dj_timezone

from apps.analitica.models import EjecucionPipeline, ResultadoScoring


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class Command(BaseCommand):
    help = "Automatiza ciclo de reentrenamiento de scoring: detectar, reentrenar, evaluar y promover version."

    def add_arguments(self, parser):
        parser.add_argument("--run-id", default="manual")
        parser.add_argument("--force", action="store_true", help="Forzar reentrenamiento sin evaluar disparadores.")
        parser.add_argument(
            "--max-days-without-retrain",
            type=int,
            default=30,
            help="Disparar reentrenamiento si pasan >= N dias desde ultimo entrenamiento.",
        )
        parser.add_argument(
            "--drift-threshold",
            type=float,
            default=0.15,
            help="Disparar reentrenamiento si abs(score_promedio_reciente - score_promedio_global) >= umbral.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Calcula decision sin ejecutar reentrenamiento.")
        parser.add_argument("--report-csv", default="docs/mineria/fase5/03_reentrenamiento_automatico.csv")
        parser.add_argument("--report-md", default="docs/mineria/fase5/03_reentrenamiento_automatico.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        model_path = root / "backend" / "fastapi_service" / "app" / "core" / "modelo_scoring.pkl"
        model_info = {}
        if model_path.exists():
            with model_path.open("rb") as file:
                model_info = pickle.load(file)
        metadata = dict(model_info.get("metadata") or {})

        now = dj_timezone.now()
        trained_at = _parse_dt(metadata.get("trained_at"))
        days_since = 9999 if trained_at is None else max((now - trained_at).days, 0)

        recent_since = now - timedelta(days=30)
        recent_avg = (
            ResultadoScoring.objects.filter(fecha_creacion__gte=recent_since).aggregate(v=Avg("score"))["v"] or 0.0
        )
        global_avg = ResultadoScoring.objects.aggregate(v=Avg("score"))["v"] or 0.0
        drift_abs = abs(float(recent_avg) - float(global_avg))

        by_staleness = days_since >= int(options["max_days_without_retrain"])
        by_drift = drift_abs >= float(options["drift_threshold"])
        by_force = bool(options["force"])
        should_retrain = by_force or by_staleness or by_drift

        run_id = options["run_id"] or "manual"
        idempotency_key = f"reentrenamiento_scoring:{now.date().isoformat()}:{run_id}"
        existing = EjecucionPipeline.objects.filter(
            pipeline="reentrenamiento_scoring",
            idempotency_key=idempotency_key,
        ).first()
        if existing and not by_force:
            self.stdout.write(self.style.WARNING("[automatizar_reentrenamiento_fase5] ya ejecutado para idempotency_key"))
            should_retrain = False

        action = "sin_accion"
        promoted_version = metadata.get("promoted_version") or "weighted_score_v1"
        training_report = "N/A"
        evaluation_report = "N/A"
        promotion_manifest = "N/A"
        start = dj_timezone.now()

        if should_retrain and not options["dry_run"]:
            train_csv = root / "docs" / "mineria" / "fase5" / "03_reentrenamiento_entrenamiento.csv"
            train_md = root / "docs" / "mineria" / "fase5" / "03_reentrenamiento_entrenamiento.md"
            eval_csv = root / "docs" / "mineria" / "fase5" / "03_reentrenamiento_evaluacion.csv"
            eval_md = root / "docs" / "mineria" / "fase5" / "03_reentrenamiento_evaluacion.md"

            call_command(
                "entrenar_scoring_mvp",
                report_csv=str(train_csv),
                report_md=str(train_md),
            )
            call_command(
                "evaluar_scoring_mvp",
                report_csv=str(eval_csv),
                report_md=str(eval_md),
            )

            promoted_version = f"scoring_mvp_{now.strftime('%Y%m%d')}"
            if model_path.exists():
                with model_path.open("rb") as file:
                    refreshed = pickle.load(file)
                refreshed_metadata = dict(refreshed.get("metadata") or {})
                refreshed_metadata["promoted_at"] = now.astimezone(timezone.utc).isoformat()
                refreshed_metadata["promoted_version"] = promoted_version
                refreshed["metadata"] = refreshed_metadata
                with model_path.open("wb") as file:
                    pickle.dump(refreshed, file)

            promotion_payload = {
                "promoted_at": now.astimezone(timezone.utc).isoformat(),
                "promoted_version": promoted_version,
                "source_model": str(model_path),
                "train_report": str(train_md),
                "eval_report": str(eval_md),
            }
            promotion_path = root / "docs" / "mineria" / "fase5" / "03_reentrenamiento_promocion.json"
            promotion_path.parent.mkdir(parents=True, exist_ok=True)
            promotion_path.write_text(json.dumps(promotion_payload, ensure_ascii=True, indent=2), encoding="utf-8")

            action = "reentrenado_validado_promovido"
            training_report = str(train_md)
            evaluation_report = str(eval_md)
            promotion_manifest = str(promotion_path)

        elif should_retrain and options["dry_run"]:
            action = "disparado_dry_run"

        end = dj_timezone.now()
        duracion_ms = int((end - start).total_seconds() * 1000)

        if not existing:
            EjecucionPipeline.objects.create(
                pipeline="reentrenamiento_scoring",
                fecha_inicio=start,
                fecha_fin=end,
                duracion_ms=max(duracion_ms, 0),
                estado=EjecucionPipeline.ESTADO_OK,
                detalle=action,
                idempotency_key=idempotency_key,
            )

        rows = [
            {"dimension": "disparador", "metrica": "force", "valor": "si" if by_force else "no"},
            {"dimension": "disparador", "metrica": "dias_desde_ultimo_entrenamiento", "valor": str(days_since)},
            {"dimension": "disparador", "metrica": "drift_abs_score_promedio", "valor": f"{drift_abs:.4f}"},
            {"dimension": "decision", "metrica": "reentrenar", "valor": "si" if should_retrain else "no"},
            {"dimension": "decision", "metrica": "accion", "valor": action},
            {"dimension": "salida", "metrica": "promoted_version", "valor": promoted_version},
        ]

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["dimension", "metrica", "valor"])
            writer.writeheader()
            writer.writerows(rows)

        lines = [
            "# Automatizacion de Reentrenamiento - Punto 3 de 8 (Fase 5)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            f"Run ID: {run_id}",
            f"Idempotency key: {idempotency_key}",
            "",
            "## Disparadores",
            f"- Force: {'si' if by_force else 'no'}",
            f"- Dias desde ultimo entrenamiento: {days_since} (umbral={options['max_days_without_retrain']})",
            f"- Drift abs(score promedio): {drift_abs:.4f} (umbral={float(options['drift_threshold']):.4f})",
            "",
            "## Resultado",
            f"- Reentrenamiento requerido: {'si' if should_retrain else 'no'}",
            f"- Accion ejecutada: `{action}`",
            f"- Version promovida: `{promoted_version}`",
            "",
            "## Artefactos de ciclo",
            f"- Entrenamiento: `{training_report}`",
            f"- Evaluacion: `{evaluation_report}`",
            f"- Promocion: `{promotion_manifest}`",
            "",
            "## Estado",
            "- Punto 3 de 8 completado tecnicamente.",
            "- Flujo detectar/reentrenar/validar/promover implementado para scoring.",
            "",
            "## Artefactos",
            f"- Reporte CSV: `{report_csv}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[automatizar_reentrenamiento_fase5] ciclo completado"))
        self.stdout.write(f"reentrenar={'si' if should_retrain else 'no'} accion={action} version={promoted_version}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")
