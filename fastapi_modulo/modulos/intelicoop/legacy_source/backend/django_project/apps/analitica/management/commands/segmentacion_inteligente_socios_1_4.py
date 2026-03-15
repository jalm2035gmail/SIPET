import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import pstdev

from django.core.management.MAIN import MAINCommand
from django.db.models import Avg, Count, Sum
from django.utils import timezone as dj_timezone

from apps.ahorros.models import Cuenta, Transaccion
from apps.analitica.models import ResultadoMoraTemprana, ResultadoScoring
from apps.creditos.models import Credito, HistorialPago
from apps.socios.models import Socio


DEFAULT_THRESHOLDS = {
    "version": "segmentacion_1_4_v1",
    "thresholds": {
        "listos_para_credito": {
            "min_score_promedio": 0.75,
            "max_prob_mora_90d": 0.30,
            "max_variabilidad_ahorro": 0.50,
            "min_ahorro_total": 300.0,
        },
        "renovacion_segura": {
            "min_total_creditos": 1,
            "min_pagos_180d": 1.0,
            "max_prob_mora_90d": 0.30,
        },
        "riesgo_alto": {
            "min_prob_mora_90d": 0.60,
            "min_alertas_altas": 1,
            "min_variabilidad_ahorro": 0.80,
        },
        "potencial_captacion": {
            "min_ahorro_total": 1000.0,
            "max_total_creditos": 0,
        },
        "jovenes_digitales": {
            "min_transacciones_180d": 6,
            "max_monto_promedio_transaccion": 250.0,
            "max_total_creditos": 1,
        },
    },
}


def _safe_cv(values):
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    if mean <= 0:
        return 0.0
    return float(pstdev(values) / mean)


def _normalize_rows(rows, keys):
    mins = {k: min(float(r[k]) for r in rows) for k in keys}
    maxs = {k: max(float(r[k]) for r in rows) for k in keys}
    for row in rows:
        for key in keys:
            lo = mins[key]
            hi = maxs[key]
            val = float(row[key])
            row[f"{key}_norm"] = 0.0 if hi == lo else (val - lo) / (hi - lo)


def _kmeans(points, k, max_iters=30):
    if not points:
        return [], []
    n = len(points)
    k = max(1, min(k, n))
    if k == 1:
        return [0] * n, [points[0]]

    indexed = sorted(enumerate(points), key=lambda x: x[1][0])
    step = (n - 1) / (k - 1) if k > 1 else 0
    centroids = [indexed[int(round(i * step))][1][:] for i in range(k)]
    labels = [0] * n

    for _ in range(max_iters):
        changed = False
        for i, point in enumerate(points):
            best_idx = 0
            best_dist = float("inf")
            for c_idx, centroid in enumerate(centroids):
                dist = 0.0
                for p, c in zip(point, centroid):
                    dist += (p - c) ** 2
                if dist < best_dist:
                    best_dist = dist
                    best_idx = c_idx
            if labels[i] != best_idx:
                labels[i] = best_idx
                changed = True

        if not changed:
            break

        grouped = {i: [] for i in range(k)}
        for label, point in zip(labels, points):
            grouped[label].append(point)
        for idx in range(k):
            group = grouped[idx]
            if not group:
                continue
            dims = len(group[0])
            centroids[idx] = [sum(g[d] for g in group) / len(group) for d in range(dims)]

    return labels, centroids


def _load_thresholds(path: Path):
    payload = DEFAULT_THRESHOLDS
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and "thresholds" in raw:
            payload = raw
    return payload.get("version", "segmentacion_1_4_v1"), payload.get("thresholds", DEFAULT_THRESHOLDS["thresholds"])


def _segmento_reglas(row, thresholds):
    t_riesgo = thresholds["riesgo_alto"]
    t_captacion = thresholds["potencial_captacion"]
    t_listos = thresholds["listos_para_credito"]
    t_renovacion = thresholds["renovacion_segura"]
    t_jovenes = thresholds["jovenes_digitales"]

    if row["prob_mora_90d"] >= float(t_riesgo["min_prob_mora_90d"]) or (
        row["alertas_altas"] >= int(t_riesgo["min_alertas_altas"])
        and row["variabilidad_ahorro"] >= float(t_riesgo["min_variabilidad_ahorro"])
    ):
        return "Riesgo alto"
    if row["ahorro_total"] >= float(t_captacion["min_ahorro_total"]) and row["total_creditos"] <= int(
        t_captacion["max_total_creditos"]
    ):
        return "Potencial captacion"
    if (
        row["score_promedio"] >= float(t_listos["min_score_promedio"])
        and row["prob_mora_90d"] < float(t_listos["max_prob_mora_90d"])
        and row["variabilidad_ahorro"] <= float(t_listos["max_variabilidad_ahorro"])
        and row["ahorro_total"] >= float(t_listos["min_ahorro_total"])
    ):
        return "Listos para credito"
    if (
        row["total_creditos"] >= int(t_renovacion["min_total_creditos"])
        and row["pagos_180d"] > float(t_renovacion["min_pagos_180d"])
        and row["prob_mora_90d"] < float(t_renovacion["max_prob_mora_90d"])
    ):
        return "Renovacion segura"
    if (
        row["transacciones_180d"] >= int(t_jovenes["min_transacciones_180d"])
        and row["monto_promedio_transaccion"] <= float(t_jovenes["max_monto_promedio_transaccion"])
        and row["total_creditos"] <= int(t_jovenes["max_total_creditos"])
    ):
        return "Jovenes digitales"
    return "MAIN general"


def _label_cluster(centroid):
    score = centroid["score_promedio_norm"]
    inv_mora = centroid["inv_mora_norm"]
    ahorro = centroid["ahorro_total_norm"]
    tx = centroid["transacciones_180d_norm"]
    creditos = centroid["total_creditos_norm"]
    inv_var = centroid["inv_variabilidad_norm"]

    scores = {
        "Riesgo alto": ((1.0 - inv_mora) * 0.55) + ((1.0 - inv_var) * 0.45),
        "Potencial captacion": (ahorro * 0.75) + ((1.0 - creditos) * 0.25),
        "Listos para credito": (score * 0.40) + (inv_mora * 0.30) + (ahorro * 0.20) + (inv_var * 0.10),
        "Renovacion segura": (creditos * 0.45) + (inv_mora * 0.35) + (score * 0.20),
        "Jovenes digitales": (tx * 0.55) + ((1.0 - creditos) * 0.30) + ((1.0 - ahorro) * 0.15),
    }
    return max(scores.items(), key=lambda x: x[1])[0]


class Command(MAINCommand):
    help = "1.4 Segmentacion inteligente de socios: reglas por umbrales y segmentacion estadistica (clustering)."

    def add_arguments(self, parser):
        parser.add_argument("--metodo", choices=("reglas", "clustering"), default="reglas")
        parser.add_argument("--clusters", type=int, default=5)
        parser.add_argument(
            "--thresholds-json",
            default="docs/mineria/customer_intelligence/02_umbrales_segmentacion_oficial_v1.json",
        )
        parser.add_argument("--thresholds-version", default="")
        parser.add_argument("--report-csv", default="docs/mineria/customer_intelligence/01_segmentacion_inteligente_resumen.csv")
        parser.add_argument("--dataset-csv", default="docs/mineria/customer_intelligence/01_segmentacion_inteligente_socios.csv")
        parser.add_argument("--report-md", default="docs/mineria/customer_intelligence/01_segmentacion_inteligente.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        metodo = options["metodo"]
        clusters = int(options["clusters"] or 5)
        thresholds_json_opt = Path(options["thresholds_json"])
        thresholds_json = thresholds_json_opt if thresholds_json_opt.is_absolute() else (root / thresholds_json_opt)
        report_csv_opt = Path(options["report_csv"])
        dataset_csv_opt = Path(options["dataset_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        dataset_csv = dataset_csv_opt if dataset_csv_opt.is_absolute() else (root / dataset_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)
        thresholds_version, thresholds = _load_thresholds(thresholds_json)
        if options.get("thresholds_version"):
            thresholds_version = str(options["thresholds_version"])

        hoy = dj_timezone.localdate()
        ventana_180d = hoy - timedelta(days=180)

        ahorro_por_socio = {
            row["socio_id"]: float(row["total"] or 0.0)
            for row in Cuenta.objects.values("socio_id").annotate(total=Sum("saldo"))
        }
        creditos_por_socio = {
            row["socio_id"]: int(row["total"] or 0)
            for row in Credito.objects.values("socio_id").annotate(total=Count("id"))
        }
        scoring_por_socio = {
            row["socio_id"]: float(row["promedio"] or 0.0)
            for row in ResultadoScoring.objects.values("socio_id").annotate(promedio=Avg("score"))
        }
        mora_por_socio = {
            row["socio_id"]: float(row["promedio"] or 0.0)
            for row in ResultadoMoraTemprana.objects.values("socio_id").annotate(promedio=Avg("prob_mora_90d"))
        }
        alerta_alta_por_socio = {
            row["socio_id"]: int(row["total"] or 0)
            for row in ResultadoMoraTemprana.objects.filter(alerta=ResultadoMoraTemprana.ALERTA_ALTA)
            .values("socio_id")
            .annotate(total=Count("id"))
        }
        pagos_por_socio = {
            row["credito__socio_id"]: float(row["total"] or 0.0)
            for row in HistorialPago.objects.filter(fecha__gte=ventana_180d)
            .values("credito__socio_id")
            .annotate(total=Sum("monto"))
        }
        tx_qs = Transaccion.objects.filter(fecha__date__gte=ventana_180d).select_related("cuenta")
        tx_by_socio = {}
        for tx in tx_qs:
            socio_id = tx.cuenta.socio_id
            tx_by_socio.setdefault(socio_id, []).append(float(tx.monto or 0.0))

        rows = []
        for socio in Socio.objects.all().order_by("id"):
            montos = tx_by_socio.get(socio.id, [])
            transacciones_180d = len(montos)
            monto_promedio = (sum(montos) / transacciones_180d) if transacciones_180d > 0 else 0.0
            variabilidad = _safe_cv(montos)
            rows.append(
                {
                    "socio_id": socio.id,
                    "ahorro_total": ahorro_por_socio.get(socio.id, 0.0),
                    "total_creditos": creditos_por_socio.get(socio.id, 0),
                    "score_promedio": scoring_por_socio.get(socio.id, 0.0),
                    "prob_mora_90d": mora_por_socio.get(socio.id, 0.0),
                    "alertas_altas": alerta_alta_por_socio.get(socio.id, 0),
                    "pagos_180d": pagos_por_socio.get(socio.id, 0.0),
                    "transacciones_180d": transacciones_180d,
                    "monto_promedio_transaccion": monto_promedio,
                    "variabilidad_ahorro": variabilidad,
                }
            )

        if metodo == "clustering" and rows:
            _normalize_rows(rows, ["score_promedio", "ahorro_total", "transacciones_180d", "total_creditos"])
            for row in rows:
                row["inv_mora"] = 1.0 - min(1.0, max(0.0, row["prob_mora_90d"]))
                row["inv_variabilidad"] = 1.0 - min(1.0, max(0.0, row["variabilidad_ahorro"]))
            _normalize_rows(rows, ["inv_mora", "inv_variabilidad"])
            points = [
                [
                    row["score_promedio_norm"],
                    row["inv_mora_norm"],
                    row["ahorro_total_norm"],
                    row["transacciones_180d_norm"],
                    row["total_creditos_norm"],
                    row["inv_variabilidad_norm"],
                ]
                for row in rows
            ]
            labels, centroids = _kmeans(points, clusters)
            centroid_map = {}
            for idx, center in enumerate(centroids):
                centroid_map[idx] = {
                    "score_promedio_norm": center[0],
                    "inv_mora_norm": center[1],
                    "ahorro_total_norm": center[2],
                    "transacciones_180d_norm": center[3],
                    "total_creditos_norm": center[4],
                    "inv_variabilidad_norm": center[5],
                }
            label_map = {idx: _label_cluster(center) for idx, center in centroid_map.items()}
            for row, label in zip(rows, labels):
                row["cluster_id"] = int(label)
                row["segmento"] = label_map.get(label, "MAIN general")
        else:
            for row in rows:
                row["cluster_id"] = -1
                row["segmento"] = _segmento_reglas(row, thresholds)

        resumen = {}
        for row in rows:
            resumen[row["segmento"]] = resumen.get(row["segmento"], 0) + 1
        total_socios = len(rows)

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["segmento", "socios", "cobertura_pct", "metodo", "thresholds_version"],
            )
            writer.writeheader()
            for segmento, count in sorted(resumen.items(), key=lambda x: x[0]):
                writer.writerow(
                    {
                        "segmento": segmento,
                        "socios": count,
                        "cobertura_pct": f"{(count / total_socios * 100.0) if total_socios else 0.0:.2f}",
                        "metodo": metodo,
                        "thresholds_version": thresholds_version,
                    }
                )

        dataset_csv.parent.mkdir(parents=True, exist_ok=True)
        with dataset_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "socio_id",
                    "segmento",
                    "cluster_id",
                    "ahorro_total",
                    "total_creditos",
                    "score_promedio",
                    "prob_mora_90d",
                    "pagos_180d",
                    "transacciones_180d",
                    "monto_promedio_transaccion",
                    "variabilidad_ahorro",
                    "metodo",
                    "thresholds_version",
                ],
            )
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        "socio_id": row["socio_id"],
                        "segmento": row["segmento"],
                        "cluster_id": row["cluster_id"],
                        "ahorro_total": f"{row['ahorro_total']:.2f}",
                        "total_creditos": row["total_creditos"],
                        "score_promedio": f"{row['score_promedio']:.4f}",
                        "prob_mora_90d": f"{row['prob_mora_90d']:.4f}",
                        "pagos_180d": f"{row['pagos_180d']:.2f}",
                        "transacciones_180d": row["transacciones_180d"],
                        "monto_promedio_transaccion": f"{row['monto_promedio_transaccion']:.2f}",
                        "variabilidad_ahorro": f"{row['variabilidad_ahorro']:.4f}",
                        "metodo": metodo,
                        "thresholds_version": thresholds_version,
                    }
                )

        segmentos_referencia = [
            "Listos para credito",
            "Renovacion segura",
            "Riesgo alto",
            "Potencial captacion",
            "Jovenes digitales",
        ]
        presentes = sum(1 for seg in segmentos_referencia if seg in resumen)
        lines = [
            "# Segmentacion Inteligente de Socios 1.4",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            f"Metodo: {metodo}",
            f"Clusters solicitados: {clusters}",
            f"Version umbrales: {thresholds_version}",
            "",
            "## Estado",
            "- Segmentacion por reglas de umbrales disponible.",
            "- Segmentacion estadistica (clustering) disponible por parametro.",
            f"- Cobertura de segmentos objetivo: {presentes}/5",
            "",
            "## Artefactos",
            f"- Resumen por segmento: `{report_csv}`",
            f"- Dataset por socio: `{dataset_csv}`",
            f"- Configuracion de umbrales: `{thresholds_json}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[segmentacion_inteligente_socios_1_4] segmentacion generada"))
        self.stdout.write(
            f"metodo={metodo} socios={total_socios} segmentos={len(resumen)} thresholds_version={thresholds_version}"
        )
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"dataset_csv={dataset_csv}")
        self.stdout.write(f"report_md={report_md}")
