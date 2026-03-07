import csv
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from itertools import permutations
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone as dj_timezone

from apps.ahorros.models import Cuenta, Transaccion
from apps.analitica.models import ReglaAsociacionProducto
from apps.creditos.models import Credito
from apps.socios.models import Socio


def _safe_div(numerator: int | float, denominator: int | float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)


def _oportunidad_por_item(item: str) -> str:
    mapping = {
        "cuenta_ahorro": "Ofrecer plan de ahorro programado.",
        "cuenta_aportacion": "Impulsar aportacion automatica mensual.",
        "credito_aprobado": "Campana de cross-sell para segundo credito.",
        "credito_solicitado": "Campana de acompanamiento a solicitud de credito.",
        "credito_rechazado": "Campana de reactivacion y educacion financiera.",
        "movimientos_recientes": "Campana de fidelizacion por alta actividad.",
    }
    return mapping.get(item, "Campana de cross-sell basada en patron de productos.")


class Command(BaseCommand):
    help = "Genera reglas de asociacion tipo Apriori para productos por socio y publica oportunidades comerciales."

    def add_arguments(self, parser):
        parser.add_argument("--fecha-ejecucion", help="Fecha de ejecucion YYYY-MM-DD. Default: hoy.")
        parser.add_argument("--window-days", type=int, default=3650, help="Ventana historica para creditos/transacciones.")
        parser.add_argument("--min-support", type=float, default=0.10)
        parser.add_argument("--min-confidence", type=float, default=0.20)
        parser.add_argument("--min-lift", type=float, default=1.00)
        parser.add_argument("--top", type=int, default=20, help="Maximo de reglas a publicar.")
        parser.add_argument("--model-version", default="asociacion_productos_v1")
        parser.add_argument("--report-csv", default="docs/mineria/fase4/04_reglas_asociacion_productos.csv")
        parser.add_argument("--report-md", default="docs/mineria/fase4/04_reglas_asociacion_productos.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        fecha_ejecucion = options["fecha_ejecucion"] or str(dj_timezone.localdate())
        model_version = options["model_version"] or "asociacion_productos_v1"
        min_support = float(options["min_support"])
        min_confidence = float(options["min_confidence"])
        min_lift = float(options["min_lift"])
        top = int(options["top"])
        window_days = int(options["window_days"])
        fecha_inicio = dj_timezone.localdate() - timedelta(days=window_days)

        socios_ids = list(Socio.objects.values_list("id", flat=True))
        baskets: dict[int, set[str]] = defaultdict(set)
        for socio_id in socios_ids:
            baskets[socio_id] = set()

        for row in Cuenta.objects.values("socio_id", "tipo"):
            if row["socio_id"] not in baskets:
                continue
            baskets[row["socio_id"]].add(f"cuenta_{row['tipo']}")

        for row in Credito.objects.filter(fecha_creacion__date__gte=fecha_inicio).values("socio_id", "estado"):
            if row["socio_id"] not in baskets:
                continue
            baskets[row["socio_id"]].add(f"credito_{row['estado']}")

        socios_activos = set(
            Transaccion.objects.filter(fecha__date__gte=fecha_inicio).values_list("cuenta__socio_id", flat=True)
        )
        for socio_id in socios_activos:
            if socio_id in baskets:
                baskets[socio_id].add("movimientos_recientes")

        valid_baskets = [items for items in baskets.values() if len(items) >= 2]
        total_baskets = len(valid_baskets)

        item_counts = Counter()
        pair_counts = Counter()
        for basket in valid_baskets:
            for item in basket:
                item_counts[item] += 1
            for pair in permutations(sorted(basket), 2):
                pair_counts[pair] += 1

        rules = []
        for (antecedente, consecuente), pair_count in pair_counts.items():
            support = _safe_div(pair_count, total_baskets)
            confidence = _safe_div(pair_count, item_counts[antecedente])
            support_consecuente = _safe_div(item_counts[consecuente], total_baskets)
            lift = _safe_div(confidence, support_consecuente)

            if support < min_support or confidence < min_confidence or lift < min_lift:
                continue
            rules.append(
                {
                    "antecedente": antecedente,
                    "consecuente": consecuente,
                    "soporte": support,
                    "confianza": confidence,
                    "lift": lift,
                    "casos_antecedente": item_counts[antecedente],
                    "casos_regla": pair_count,
                    "oportunidad_comercial": _oportunidad_por_item(consecuente),
                }
            )

        rules.sort(key=lambda item: (item["lift"], item["confianza"], item["soporte"]), reverse=True)
        selected = rules[:top] if top > 0 else rules

        ReglaAsociacionProducto.objects.filter(
            fecha_ejecucion=fecha_ejecucion,
            model_version=model_version,
        ).delete()
        for rule in selected:
            ReglaAsociacionProducto.objects.create(
                fecha_ejecucion=fecha_ejecucion,
                antecedente=rule["antecedente"],
                consecuente=rule["consecuente"],
                soporte=rule["soporte"],
                confianza=rule["confianza"],
                lift=rule["lift"],
                casos_antecedente=rule["casos_antecedente"],
                casos_regla=rule["casos_regla"],
                oportunidad_comercial=rule["oportunidad_comercial"],
                vigente=True,
                model_version=model_version,
            )

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "fecha_ejecucion",
                    "model_version",
                    "antecedente",
                    "consecuente",
                    "soporte",
                    "confianza",
                    "lift",
                    "casos_antecedente",
                    "casos_regla",
                    "oportunidad_comercial",
                ],
            )
            writer.writeheader()
            for rule in selected:
                writer.writerow(
                    {
                        "fecha_ejecucion": fecha_ejecucion,
                        "model_version": model_version,
                        "antecedente": rule["antecedente"],
                        "consecuente": rule["consecuente"],
                        "soporte": f"{rule['soporte']:.4f}",
                        "confianza": f"{rule['confianza']:.4f}",
                        "lift": f"{rule['lift']:.4f}",
                        "casos_antecedente": rule["casos_antecedente"],
                        "casos_regla": rule["casos_regla"],
                        "oportunidad_comercial": rule["oportunidad_comercial"],
                    }
                )

        lines = [
            "# Reglas de Asociacion de Productos - Punto 4 de 7 (Fase 4)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            f"Fecha de reglas: {fecha_ejecucion}",
            f"Version modelo: {model_version}",
            "",
            "## Parametros de filtro",
            f"- min_support: {min_support:.2f}",
            f"- min_confidence: {min_confidence:.2f}",
            f"- min_lift: {min_lift:.2f}",
            f"- top reglas: {top}",
            "",
            "## Resultado de corrida",
            f"- Socios evaluados: {len(socios_ids)}",
            f"- Cestas validas (>=2 items): {total_baskets}",
            f"- Reglas candidatas: {len(rules)}",
            f"- Reglas publicadas: {len(selected)}",
            "",
            "## Estado",
            "- Punto 4 de 7 completado tecnicamente.",
            "- Reglas filtradas por soporte/confianza/lift publicadas para campanas comerciales.",
            "",
            "## Artefactos",
            f"- Reporte CSV: `{report_csv}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[generar_reglas_asociacion_productos] corrida completada"))
        self.stdout.write(
            f"socios={len(socios_ids)} cestas_validas={total_baskets} reglas_candidatas={len(rules)} publicadas={len(selected)}"
        )
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")
