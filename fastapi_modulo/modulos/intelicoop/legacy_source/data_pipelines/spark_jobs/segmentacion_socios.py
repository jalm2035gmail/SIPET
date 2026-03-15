#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable


ROOT_DIR = Path(__file__).resolve().parents[2]
DJANGO_PROJECT_DIR = ROOT_DIR / "backend" / "django_project"

if str(DJANGO_PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(DJANGO_PROJECT_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.db.models import Max, Sum, Count  # noqa: E402

from apps.ahorros.models import Cuenta, Transaccion  # noqa: E402
from apps.socios.models import Socio  # noqa: E402

try:
    from pyspark.sql import SparkSession
    from pyspark.sql import functions as F
    from pyspark.ml.clustering import KMeans
    from pyspark.ml.feature import VectorAssembler
except Exception:  # pragma: no cover - optional dependency
    SparkSession = None
    F = None
    KMeans = None
    VectorAssembler = None

@dataclass
class SocioFeatures:
    socio_id: int
    saldo_total: float
    total_movimientos: float
    cantidad_movimientos: int
    dias_desde_ultimo_movimiento: int | None


def clasificar_segmento(features: SocioFeatures) -> str:
    # Inactivo: sin movimientos o demasiado tiempo sin actividad.
    if features.cantidad_movimientos == 0 and features.saldo_total <= 0:
        return Socio.SEGMENTO_INACTIVO
    if features.dias_desde_ultimo_movimiento is not None and features.dias_desde_ultimo_movimiento > 180:
        return Socio.SEGMENTO_INACTIVO

    # Gran ahorrador: alto saldo, alta actividad o alto volumen.
    if (
        features.saldo_total >= 5000
        or features.total_movimientos >= 10000
        or features.cantidad_movimientos >= 20
    ):
        return Socio.SEGMENTO_GRAN_AHORRADOR

    # Resto: ahorrador hormiga.
    return Socio.SEGMENTO_HORMIGA


def extraer_features() -> Iterable[SocioFeatures]:
    hoy = date.today()

    cuentas_por_socio = (
        Cuenta.objects.values("socio_id")
        .annotate(saldo_total=Sum("saldo"))
    )
    saldo_map = {row["socio_id"]: float(row["saldo_total"] or 0) for row in cuentas_por_socio}

    movs_por_socio = (
        Transaccion.objects.values("cuenta__socio_id")
        .annotate(
            total_movimientos=Sum("monto"),
            cantidad_movimientos=Count("id"),
            ultima_fecha=Max("fecha"),
        )
    )
    movimientos_map = {
        row["cuenta__socio_id"]: {
            "total_movimientos": float(row["total_movimientos"] or 0),
            "cantidad_movimientos": int(row["cantidad_movimientos"] or 0),
            "ultima_fecha": row["ultima_fecha"].date() if row["ultima_fecha"] else None,
        }
        for row in movs_por_socio
    }

    for socio_id in Socio.objects.values_list("id", flat=True):
        saldo_total = saldo_map.get(socio_id, 0.0)
        mov_info = movimientos_map.get(
            socio_id,
            {"total_movimientos": 0.0, "cantidad_movimientos": 0, "ultima_fecha": None},
        )

        ultima_fecha = mov_info["ultima_fecha"]
        dias_desde = (hoy - ultima_fecha).days if ultima_fecha else None

        yield SocioFeatures(
            socio_id=socio_id,
            saldo_total=saldo_total,
            total_movimientos=mov_info["total_movimientos"],
            cantidad_movimientos=mov_info["cantidad_movimientos"],
            dias_desde_ultimo_movimiento=dias_desde,
        )


def segmentar_con_pyspark(features: list[SocioFeatures]) -> dict[int, str]:
    if SparkSession is None or F is None or KMeans is None or VectorAssembler is None:
        raise RuntimeError("PySpark no está disponible en este entorno.")
    if len(features) < 3:
        raise RuntimeError("Se requieren al menos 3 socios para clustering K-Means.")

    spark = SparkSession.builder.appName("segmentacion_socios").getOrCreate()
    rows = [
        {
            "socio_id": item.socio_id,
            "saldo_total": float(item.saldo_total),
            "total_movimientos": float(item.total_movimientos),
            "cantidad_movimientos": int(item.cantidad_movimientos),
            "dias_desde_ultimo_movimiento": item.dias_desde_ultimo_movimiento,
        }
        for item in features
    ]
    df = spark.createDataFrame(rows)

    prepared = (
        df.withColumn("dias_feature", F.coalesce(F.col("dias_desde_ultimo_movimiento"), F.lit(365)))
        .withColumn("saldo_log", F.log1p(F.col("saldo_total")))
        .withColumn("mov_total_log", F.log1p(F.col("total_movimientos")))
        .withColumn("mov_count_log", F.log1p(F.col("cantidad_movimientos")))
        .withColumn("actividad_inv", 1 / (1 + F.col("dias_feature")))
    )

    assembler = VectorAssembler(
        inputCols=["saldo_log", "mov_total_log", "mov_count_log", "actividad_inv"],
        outputCol="features",
    )
    vector_df = assembler.transform(prepared).select("socio_id", "features")

    kmeans = KMeans(k=3, seed=42, featuresCol="features", predictionCol="cluster")
    model = kmeans.fit(vector_df)
    predicted = model.transform(vector_df)

    # Rank clusters by centroid score: higher means better ahorro profile.
    cluster_scores: dict[int, float] = {}
    centers = model.clusterCenters()
    for idx, center in enumerate(centers):
        saldo_log, mov_total_log, mov_count_log, actividad_inv = [float(v) for v in center]
        score = (saldo_log * 0.45) + (mov_total_log * 0.30) + (mov_count_log * 0.15) + (actividad_inv * 0.10)
        cluster_scores[idx] = score

    ranked = [cluster_id for cluster_id, _ in sorted(cluster_scores.items(), key=lambda x: x[1])]
    cluster_to_segment = {
        ranked[0]: Socio.SEGMENTO_INACTIVO,
        ranked[1]: Socio.SEGMENTO_HORMIGA,
        ranked[2]: Socio.SEGMENTO_GRAN_AHORRADOR,
    }

    out = predicted.select("socio_id", "cluster").collect()
    spark.stop()
    return {int(r["socio_id"]): cluster_to_segment[int(r["cluster"])] for r in out}


def ejecutar_segmentacion(dry_run: bool = False, engine: str = "auto") -> Counter:
    socios = {s.id: s for s in Socio.objects.all()}
    cambios = []
    conteo = Counter()
    features = list(extraer_features())

    if engine not in {"auto", "orm", "pyspark"}:
        raise ValueError("engine debe ser auto, orm o pyspark")

    if engine == "pyspark" or (engine == "auto" and SparkSession is not None):
        try:
            segmentos = segmentar_con_pyspark(features)
        except Exception:
            if engine == "pyspark":
                raise
            segmentos = {f.socio_id: clasificar_segmento(f) for f in features}
    else:
        segmentos = {f.socio_id: clasificar_segmento(f) for f in features}

    for socio_id, nuevo_segmento in segmentos.items():
        socio = socios.get(socio_id)
        if not socio:
            continue
        conteo[nuevo_segmento] += 1
        if socio.segmento != nuevo_segmento:
            socio.segmento = nuevo_segmento
            cambios.append(socio)

    if cambios and not dry_run:
        Socio.objects.bulk_update(cambios, ["segmento"])

    return conteo


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Segmentacion diaria de socios.")
    parser.add_argument("--dry-run", action="store_true", help="Calcula segmentos sin escribir en MAIN de datos.")
    parser.add_argument(
        "--engine",
        choices=("auto", "orm", "pyspark"),
        default="auto",
        help="Motor de segmentación.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    conteo = ejecutar_segmentacion(dry_run=args.dry_run, engine=args.engine)
    total = sum(conteo.values())
    modo = "DRY-RUN" if args.dry_run else "APLICADO"

    print(f"[segmentacion_socios] modo={modo} total_socios={total}")
    for segmento in (
        Socio.SEGMENTO_HORMIGA,
        Socio.SEGMENTO_GRAN_AHORRADOR,
        Socio.SEGMENTO_INACTIVO,
    ):
        print(f"  - {segmento}: {conteo.get(segmento, 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
