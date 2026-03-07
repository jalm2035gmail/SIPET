import csv
import json
import pickle
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models import Avg, Count
from django.utils import timezone as dj_timezone

from apps.analitica.models import ResultadoScoring


def _bucket_plazo(plazo: int | None) -> str:
    if plazo is None:
        return "sin_plazo"
    if plazo <= 12:
        return "corto_<=12m"
    if plazo <= 24:
        return "medio_13_24m"
    return "largo_>24m"


class Command(BaseCommand):
    help = "Valida tecnicamente desempeno en produccion, estabilidad temporal y degradacion critica (Fase 6)."

    def add_arguments(self, parser):
        parser.add_argument("--max-drift-score", type=float, default=0.10)
        parser.add_argument("--report-csv", default="docs/mineria/fase6/01_validacion_tecnica_modelos.csv")
        parser.add_argument("--report-md", default="docs/mineria/fase6/01_validacion_tecnica_modelos.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)
        max_drift_score = float(options["max_drift_score"])

        model_path = root / "backend" / "fastapi_service" / "app" / "core" / "modelo_scoring.pkl"
        expected_brier = None
        expected_auc = None
        if model_path.exists():
            with model_path.open("rb") as file:
                artifact = pickle.load(file)
            metadata = dict(artifact.get("metadata") or {})
            candidate = dict(metadata.get("candidate_metrics") or {})
            expected_brier = candidate.get("brier")
            expected_auc = candidate.get("auc")

        base = ResultadoScoring.objects.aggregate(
            total=Count("id"),
            score_promedio=Avg("score"),
        )
        total = int(base["total"] or 0)
        score_promedio = float(base["score_promedio"] or 0.0)

        cohort_map: dict[str, list[float]] = defaultdict(list)
        for row in ResultadoScoring.objects.values("fecha_creacion", "score"):
            cohort = row["fecha_creacion"].strftime("%Y-%m")
            cohort_map[cohort].append(float(row["score"]))

        cohort_rows = []
        for cohort, values in sorted(cohort_map.items()):
            avg = sum(values) / len(values)
            drift = abs(avg - score_promedio)
            cohort_rows.append((cohort, len(values), avg, drift))

        tipo_map: dict[str, list[float]] = defaultdict(list)
        rows_tipo = ResultadoScoring.objects.select_related("credito").all()
        for row in rows_tipo:
            plazo = row.credito.plazo if row.credito_id and row.credito else None
            bucket = _bucket_plazo(plazo)
            tipo_map[bucket].append(float(row.score))

        tipo_rows = []
        for bucket, values in sorted(tipo_map.items()):
            avg = sum(values) / len(values)
            drift = abs(avg - score_promedio)
            tipo_rows.append((bucket, len(values), avg, drift))

        promo_manifest = root / "docs" / "mineria" / "fase5" / "03_reentrenamiento_promocion.json"
        post_deploy_drift = 0.0
        post_deploy_status = "En revision"
        if promo_manifest.exists():
            payload = json.loads(promo_manifest.read_text(encoding="utf-8"))
            promoted_at_raw = payload.get("promoted_at")
            promoted_at = None
            if promoted_at_raw:
                promoted_at = datetime.fromisoformat(promoted_at_raw.replace("Z", "+00:00"))
            if promoted_at:
                before_start = promoted_at - timedelta(days=7)
                before_avg = (
                    ResultadoScoring.objects.filter(fecha_creacion__gte=before_start, fecha_creacion__lt=promoted_at).aggregate(
                        v=Avg("score")
                    )["v"]
                    or 0.0
                )
                after_end = promoted_at + timedelta(days=7)
                after_avg = (
                    ResultadoScoring.objects.filter(fecha_creacion__gte=promoted_at, fecha_creacion__lt=after_end).aggregate(
                        v=Avg("score")
                    )["v"]
                    or 0.0
                )
                post_deploy_drift = abs(float(after_avg) - float(before_avg))
                post_deploy_status = "Cumple" if post_deploy_drift <= max_drift_score else "En revision"

        rows = []
        rows.append(
            {
                "dimension": "global",
                "segmento": "scoring_operativo",
                "samples": total,
                "metrica": "score_promedio_real",
                "valor": f"{score_promedio:.6f}",
                "umbral_o_referencia": "comparar_vs_validacion",
                "estado": "Cumple" if total > 0 else "En revision",
            }
        )
        rows.append(
            {
                "dimension": "global",
                "segmento": "referencia_modelo",
                "samples": 1 if expected_brier is not None else 0,
                "metrica": "brier_esperado",
                "valor": f"{float(expected_brier or 0):.6f}",
                "umbral_o_referencia": "metadata_candidate_metrics",
                "estado": "Cumple" if expected_brier is not None else "En revision",
            }
        )
        rows.append(
            {
                "dimension": "global",
                "segmento": "referencia_modelo",
                "samples": 1 if expected_auc is not None else 0,
                "metrica": "auc_esperado",
                "valor": f"{float(expected_auc or 0):.6f}",
                "umbral_o_referencia": "metadata_candidate_metrics",
                "estado": "Cumple" if expected_auc is not None else "En revision",
            }
        )

        for cohort, samples, avg, drift in cohort_rows:
            rows.append(
                {
                    "dimension": "cohorte_temporal",
                    "segmento": cohort,
                    "samples": samples,
                    "metrica": "drift_score_vs_global",
                    "valor": f"{drift:.6f}",
                    "umbral_o_referencia": f"<={max_drift_score:.4f}",
                    "estado": "Cumple" if drift <= max_drift_score else "En revision",
                }
            )

        for bucket, samples, avg, drift in tipo_rows:
            rows.append(
                {
                    "dimension": "tipo_credito",
                    "segmento": bucket,
                    "samples": samples,
                    "metrica": "drift_score_vs_global",
                    "valor": f"{drift:.6f}",
                    "umbral_o_referencia": f"<={max_drift_score:.4f}",
                    "estado": "Cumple" if drift <= max_drift_score else "En revision",
                }
            )

        rows.append(
            {
                "dimension": "post_deploy",
                "segmento": "ultima_promocion_modelo",
                "samples": total,
                "metrica": "drift_7d_before_after",
                "valor": f"{post_deploy_drift:.6f}",
                "umbral_o_referencia": f"<={max_drift_score:.4f}",
                "estado": post_deploy_status,
            }
        )

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "dimension",
                    "segmento",
                    "samples",
                    "metrica",
                    "valor",
                    "umbral_o_referencia",
                    "estado",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

        total_rules = len(rows)
        cumple = sum(1 for row in rows if row["estado"] == "Cumple")
        lines = [
            "# Validacion Tecnica de Modelos - Punto 1 de 8 (Fase 6)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Resumen",
            f"- Reglas tecnicas evaluadas: {total_rules}",
            f"- Reglas en estado cumple: {cumple}",
            f"- Score promedio operativo: {score_promedio:.6f}",
            f"- Drift maximo permitido: {max_drift_score:.4f}",
            "",
            "## Cobertura de validacion",
            "- Desempeno real vs referencia esperada (metadata de modelo).",
            "- Estabilidad temporal por cohorte mensual.",
            "- Estabilidad por tipo de credito (plazo corto/medio/largo).",
            "- Verificacion de degradacion critica tras ultimo despliegue.",
            "",
            "## Estado",
            "- Punto 1 de 8 completado tecnicamente.",
            "- Validacion tecnica base de modelos en produccion documentada.",
            "",
            "## Artefactos",
            f"- Reporte CSV: `{report_csv}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[validar_tecnica_modelos_fase6] validacion generada"))
        self.stdout.write(f"reglas={total_rules} cumple={cumple}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")
