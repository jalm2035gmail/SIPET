import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import pstdev

from django.core.management.base import BaseCommand
from django.db.models import Avg, Count, Sum
from django.utils import timezone as dj_timezone

from apps.ahorros.models import Cuenta, Transaccion
from apps.analitica.models import ResultadoMoraTemprana, ResultadoScoring
from apps.creditos.models import Credito, HistorialPago
from apps.socios.models import Socio


def _infer_sucursal(direccion: str) -> str:
    text = (direccion or "").lower()
    if "cuitzeo" in text:
        return "Cuitzeo"
    if "santa ana maya" in text:
        return "Santa Ana Maya"
    if "yuriria" in text:
        return "Yuriria"
    return "Yuriria"


def _semaforo(value: float, threshold: float, invert: bool = False) -> str:
    ok = value <= threshold if invert else value >= threshold
    if ok:
        return "Verde"
    borderline = value <= (threshold * 1.2) if invert else value >= (threshold * 0.8)
    return "Amarillo" if borderline else "Rojo"


class Command(BaseCommand):
    help = "1.8 Dashboards ejecutivos y operativos: genera tableros para cartera, colocacion, captacion, riesgo, sucursales y cobranza."

    def add_arguments(self, parser):
        parser.add_argument("--salud-cartera-csv", default="docs/mineria/dashboards/01_salud_cartera.csv")
        parser.add_argument("--colocacion-csv", default="docs/mineria/dashboards/02_colocacion.csv")
        parser.add_argument("--captacion-csv", default="docs/mineria/dashboards/03_captacion.csv")
        parser.add_argument("--riesgo-csv", default="docs/mineria/dashboards/04_riesgo.csv")
        parser.add_argument("--sucursales-csv", default="docs/mineria/dashboards/05_sucursales_ranking.csv")
        parser.add_argument("--cobranza-csv", default="docs/mineria/dashboards/06_eficiencia_cobranza.csv")
        parser.add_argument("--semaforos-csv", default="docs/mineria/dashboards/07_semaforos_dashboard.csv")
        parser.add_argument("--report-md", default="docs/mineria/dashboards/01_dashboards_ejecutivos_operativos.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        out = {}
        for key in (
            "salud_cartera_csv",
            "colocacion_csv",
            "captacion_csv",
            "riesgo_csv",
            "sucursales_csv",
            "cobranza_csv",
            "semaforos_csv",
            "report_md",
        ):
            p = Path(options[key])
            out[key] = p if p.is_absolute() else (root / p)
            out[key].parent.mkdir(parents=True, exist_ok=True)

        hoy = dj_timezone.localdate()
        d30 = hoy - timedelta(days=30)
        d90 = hoy - timedelta(days=90)
        d180 = hoy - timedelta(days=180)

        # Salud de cartera.
        cartera_total = float(Credito.objects.aggregate(v=Sum("monto"))["v"] or 0.0)
        mora_media_alta = ResultadoMoraTemprana.objects.filter(
            alerta__in=[ResultadoMoraTemprana.ALERTA_MEDIA, ResultadoMoraTemprana.ALERTA_ALTA]
        )
        cartera_vencida = float(mora_media_alta.aggregate(v=Sum("credito__deuda_actual"))["v"] or 0.0)
        cartera_vigente = max(0.0, cartera_total - cartera_vencida)
        imor = 0.0 if cartera_total <= 0 else (cartera_vencida / cartera_total) * 100.0
        vintage_rows = []
        for label, days in (("0-6m", 180), ("6-12m", 365), ("12m+", 36500)):
            if label == "0-6m":
                qs = Credito.objects.filter(fecha_creacion__date__gte=(hoy - timedelta(days=days)))
            elif label == "6-12m":
                qs = Credito.objects.filter(
                    fecha_creacion__date__lt=(hoy - timedelta(days=180)),
                    fecha_creacion__date__gte=(hoy - timedelta(days=365)),
                )
            else:
                qs = Credito.objects.filter(fecha_creacion__date__lt=(hoy - timedelta(days=365)))
            total = qs.count()
            con_mora = mora_media_alta.filter(credito_id__in=qs.values_list("id", flat=True)).count()
            pct = 0.0 if total == 0 else (con_mora / total) * 100.0
            vintage_rows.append({"vintage": label, "creditos": total, "creditos_mora": con_mora, "mora_pct": f"{pct:.2f}"})

        with out["salud_cartera_csv"].open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["metrica", "valor"])
            writer.writeheader()
            writer.writerows(
                [
                    {"metrica": "cartera_total", "valor": f"{cartera_total:.2f}"},
                    {"metrica": "cartera_vigente", "valor": f"{cartera_vigente:.2f}"},
                    {"metrica": "cartera_vencida_estimada", "valor": f"{cartera_vencida:.2f}"},
                    {"metrica": "imor_pct", "valor": f"{imor:.2f}"},
                ]
            )
            for row in vintage_rows:
                writer.writerow({"metrica": f"vintage_{row['vintage']}_mora_pct", "valor": row["mora_pct"]})

        # Colocacion.
        meta_colocacion = 100000.0
        colocacion_real = float(Credito.objects.filter(fecha_creacion__date__gte=d30).aggregate(v=Sum("monto"))["v"] or 0.0)
        solicitados = Credito.objects.filter(fecha_creacion__date__gte=d30).count()
        aprobados = Credito.objects.filter(fecha_creacion__date__gte=d30, estado=Credito.ESTADO_APROBADO).count()
        rechazados = Credito.objects.filter(fecha_creacion__date__gte=d30, estado=Credito.ESTADO_RECHAZADO).count()
        tiempos = []
        for row in ResultadoScoring.objects.select_related("credito").filter(credito__isnull=False):
            delta = (row.fecha_creacion - row.credito.fecha_creacion).total_seconds() / 3600.0
            if delta >= 0:
                tiempos.append(delta)
        t_promedio = 0.0 if not tiempos else sum(tiempos) / len(tiempos)
        with out["colocacion_csv"].open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["metrica", "valor"])
            writer.writeheader()
            writer.writerows(
                [
                    {"metrica": "meta_colocacion_30d", "valor": f"{meta_colocacion:.2f}"},
                    {"metrica": "colocacion_real_30d", "valor": f"{colocacion_real:.2f}"},
                    {"metrica": "cumplimiento_meta_pct", "valor": f"{(colocacion_real / meta_colocacion * 100.0) if meta_colocacion else 0.0:.2f}"},
                    {"metrica": "embudo_solicitados", "valor": solicitados},
                    {"metrica": "embudo_aprobados", "valor": aprobados},
                    {"metrica": "embudo_rechazados", "valor": rechazados},
                    {"metrica": "tiempo_respuesta_promedio_h", "valor": f"{t_promedio:.2f}"},
                ]
            )

        # Captacion.
        dep30 = float(Transaccion.objects.filter(fecha__date__gte=d30, tipo=Transaccion.TIPO_DEPOSITO).aggregate(v=Sum("monto"))["v"] or 0.0)
        ret30 = float(Transaccion.objects.filter(fecha__date__gte=d30, tipo=Transaccion.TIPO_RETIRO).aggregate(v=Sum("monto"))["v"] or 0.0)
        neto30 = dep30 - ret30
        saldos = [float(v) for v in Cuenta.objects.values_list("saldo", flat=True)]
        cv = 0.0
        if saldos and sum(saldos) > 0:
            mean = sum(saldos) / len(saldos)
            cv = pstdev(saldos) / mean if mean > 0 else 0.0
        estabilidad = max(0.0, min(100.0, (1.0 - cv) * 100.0))
        with out["captacion_csv"].open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["metrica", "valor"])
            writer.writeheader()
            writer.writerows(
                [
                    {"metrica": "depositos_30d", "valor": f"{dep30:.2f}"},
                    {"metrica": "retiros_30d", "valor": f"{ret30:.2f}"},
                    {"metrica": "crecimiento_neto_30d", "valor": f"{neto30:.2f}"},
                    {"metrica": "estabilidad_ahorro_pct", "valor": f"{estabilidad:.2f}"},
                ]
            )

        # Riesgo.
        pagos_90d = float(HistorialPago.objects.filter(fecha__gte=d90).aggregate(v=Sum("monto"))["v"] or 0.0)
        cobertura = 0.0 if cartera_vencida <= 0 else (pagos_90d / cartera_vencida) * 100.0
        provisiones = cartera_vencida * 0.35
        castigos = float(
            mora_media_alta.filter(prob_mora_90d__gte=0.85).aggregate(v=Sum("credito__deuda_actual"))["v"] or 0.0
        ) * 0.20
        with out["riesgo_csv"].open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["metrica", "valor"])
            writer.writeheader()
            writer.writerows(
                [
                    {"metrica": "cobertura_pct", "valor": f"{cobertura:.2f}"},
                    {"metrica": "provisiones_estimadas", "valor": f"{provisiones:.2f}"},
                    {"metrica": "castigos_estimados", "valor": f"{castigos:.2f}"},
                ]
            )

        # Sucursales ranking Yuriria/Cuitzeo/Santa Ana.
        suc_rows = []
        for suc in ["Yuriria", "Cuitzeo", "Santa Ana Maya"]:
            socios = [s.id for s in Socio.objects.all() if _infer_sucursal(s.direccion) == suc]
            coloc = float(Credito.objects.filter(socio_id__in=socios, fecha_creacion__date__gte=d30).aggregate(v=Sum("monto"))["v"] or 0.0)
            mora = mora_media_alta.filter(socio_id__in=socios).count()
            suc_rows.append({"sucursal": suc, "colocacion_30d": f"{coloc:.2f}", "alertas_mora": mora})
        suc_rows = sorted(suc_rows, key=lambda x: float(x["colocacion_30d"]), reverse=True)
        for i, r in enumerate(suc_rows, start=1):
            r["ranking"] = i
        with out["sucursales_csv"].open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["ranking", "sucursal", "colocacion_30d", "alertas_mora"])
            writer.writeheader()
            writer.writerows(suc_rows)

        # Eficiencia cobranza.
        gestiones = mora_media_alta.count()
        recuperadas = mora_media_alta.filter(ratio_pago_90d__gte=0.60).count()
        eficiencia = 0.0 if gestiones == 0 else (recuperadas / gestiones) * 100.0
        rec_por_gestion = 0.0 if gestiones == 0 else (pagos_90d / gestiones)
        with out["cobranza_csv"].open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["metrica", "valor"])
            writer.writeheader()
            writer.writerows(
                [
                    {"metrica": "gestiones_total", "valor": gestiones},
                    {"metrica": "gestiones_con_recuperacion", "valor": recuperadas},
                    {"metrica": "eficiencia_cobranza_pct", "valor": f"{eficiencia:.2f}"},
                    {"metrica": "recuperacion_por_gestion", "valor": f"{rec_por_gestion:.2f}"},
                ]
            )

        # Semaforos consolidados para dashboard.
        coverage_threshold = 50.0
        sem_rows = [
            {"componente": "salud_cartera_imor", "valor": f"{imor:.2f}", "semaforo": _semaforo(imor, 15.0, invert=True)},
            {"componente": "colocacion_cumplimiento", "valor": f"{(colocacion_real / meta_colocacion * 100.0) if meta_colocacion else 0.0:.2f}", "semaforo": _semaforo((colocacion_real / meta_colocacion * 100.0) if meta_colocacion else 0.0, 80.0)},
            {"componente": "captacion_estabilidad", "valor": f"{estabilidad:.2f}", "semaforo": _semaforo(estabilidad, 60.0)},
            {"componente": "riesgo_cobertura", "valor": f"{cobertura:.2f}", "semaforo": _semaforo(cobertura, coverage_threshold)},
            {"componente": "cobranza_eficiencia", "valor": f"{eficiencia:.2f}", "semaforo": _semaforo(eficiencia, 45.0)},
        ]
        for row in sem_rows:
            row["estado"] = "Cumple" if row["semaforo"] == "Verde" else "En revision"
        with out["semaforos_csv"].open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["componente", "valor", "semaforo", "estado"])
            writer.writeheader()
            writer.writerows(sem_rows)

        lines = [
            "# Dashboards Ejecutivos y Operativos 1.8",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Dashboards generados",
            "- Salud de cartera",
            "- Colocacion",
            "- Captacion",
            "- Riesgo",
            "- Sucursales",
            "- Eficiencia de cobranza",
            "",
            "## Estado",
            "- Dashboards ejecutivos y operativos implementados tecnicamente.",
            "- Semaforos consolidados para dashboard disponibles.",
            "",
            "## Artefactos",
            f"- `{out['salud_cartera_csv']}`",
            f"- `{out['colocacion_csv']}`",
            f"- `{out['captacion_csv']}`",
            f"- `{out['riesgo_csv']}`",
            f"- `{out['sucursales_csv']}`",
            f"- `{out['cobranza_csv']}`",
            f"- `{out['semaforos_csv']}`",
            "",
        ]
        out["report_md"].write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[dashboards_ejecutivos_operativos_1_8] dashboards generados"))
        self.stdout.write(f"sucursales={len(suc_rows)} semaforos={len(sem_rows)}")
        self.stdout.write(f"report_md={out['report_md']}")
