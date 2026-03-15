import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand
from django.db.models import Count, Max, Sum
from django.utils import timezone as dj_timezone

from apps.ahorros.models import Transaccion
from apps.analitica.models import AlertaMonitoreo, ContactoCampania, ResultadoMoraTemprana
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


def _producto_credito(credito: Credito) -> str:
    plazo = int(credito.plazo or 0)
    if plazo <= 6:
        return "consumo_corto"
    if plazo <= 18:
        return "consumo_estandar"
    return "patrimonial_largo"


def _severity(valor: float, umbral: float) -> tuple[str, str]:
    if valor >= (umbral * 1.3):
        return "critical", "Rojo"
    if valor >= umbral:
        return "warn", "Amarillo"
    return "info", "Verde"


class Command(MAINCommand):
    help = "1.7 Early Warning System: detecta alertas tempranas, semaforos y cola de notificaciones internas."

    def add_arguments(self, parser):
        parser.add_argument("--drop-ahorro-ratio", type=float, default=0.20)
        parser.add_argument("--payment-drop-ratio", type=float, default=0.40)
        parser.add_argument("--concentracion-mora-pct", type=float, default=40.0)
        parser.add_argument("--coverage-min-pct", type=float, default=50.0)
        parser.add_argument("--report-csv", default="docs/mineria/early_warning/01_alertas_tempranas.csv")
        parser.add_argument("--semaforos-csv", default="docs/mineria/early_warning/02_semaforos_dashboard.csv")
        parser.add_argument("--notify-jsonl", default="docs/mineria/early_warning/03_notificaciones_internas.jsonl")
        parser.add_argument("--report-md", default="docs/mineria/early_warning/01_early_warning_system.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        semaforos_csv_opt = Path(options["semaforos_csv"])
        notify_jsonl_opt = Path(options["notify_jsonl"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        semaforos_csv = semaforos_csv_opt if semaforos_csv_opt.is_absolute() else (root / semaforos_csv_opt)
        notify_jsonl = notify_jsonl_opt if notify_jsonl_opt.is_absolute() else (root / notify_jsonl_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        drop_ratio = float(options["drop_ahorro_ratio"])
        payment_drop_ratio = float(options["payment_drop_ratio"])
        concentracion_mora_pct = float(options["concentracion_mora_pct"])
        coverage_min_pct = float(options["coverage_min_pct"])

        hoy = dj_timezone.localdate()
        d30 = hoy - timedelta(days=30)
        prev_d30 = hoy - timedelta(days=60)
        d90 = hoy - timedelta(days=90)

        alerts = []
        notifications = []

        # 1) Caida fuerte de ahorro.
        ahorro_total_by_socio = {
            row["socio_id"]: float(row["v"] or 0.0)
            for row in Socio.objects.values("id").annotate(socio_id=Max("id"), v=Sum("cuentas__saldo"))
        }
        dep30_by_socio = {
            row["cuenta__socio_id"]: float(row["v"] or 0.0)
            for row in Transaccion.objects.filter(fecha__date__gte=d30, tipo=Transaccion.TIPO_DEPOSITO)
            .values("cuenta__socio_id")
            .annotate(v=Sum("monto"))
        }
        ret30_by_socio = {
            row["cuenta__socio_id"]: float(row["v"] or 0.0)
            for row in Transaccion.objects.filter(fecha__date__gte=d30, tipo=Transaccion.TIPO_RETIRO)
            .values("cuenta__socio_id")
            .annotate(v=Sum("monto"))
        }
        for socio in Socio.objects.all():
            ahorro_total = float(ahorro_total_by_socio.get(socio.id, 0.0))
            dep30 = float(dep30_by_socio.get(socio.id, 0.0))
            ret30 = float(ret30_by_socio.get(socio.id, 0.0))
            neto = dep30 - ret30
            ratio = 0.0 if ahorro_total <= 0 else abs(min(0.0, neto)) / ahorro_total
            if neto < 0 and ratio >= drop_ratio:
                sev, sem = _severity(ratio * 100.0, drop_ratio * 100.0)
                alerts.append(
                    {
                        "tipo_alerta": "caida_fuerte_ahorro",
                        "dimension": "socio",
                        "entidad_id": str(socio.id),
                        "valor": f"{ratio * 100.0:.2f}",
                        "umbral": f"{drop_ratio * 100.0:.2f}",
                        "severidad": sev,
                        "semaforo": sem,
                        "canal_sugerido": "email",
                        "detalle": f"Caida neta de ahorro 30d en socio {socio.id}",
                    }
                )

        # 2) Cambio brusco de patron de pago.
        pagos_actual = {
            row["credito__socio_id"]: float(row["v"] or 0.0)
            for row in HistorialPago.objects.filter(fecha__gte=d30).values("credito__socio_id").annotate(v=Sum("monto"))
        }
        pagos_prev = {
            row["credito__socio_id"]: float(row["v"] or 0.0)
            for row in HistorialPago.objects.filter(fecha__gte=prev_d30, fecha__lt=d30)
            .values("credito__socio_id")
            .annotate(v=Sum("monto"))
        }
        for socio in Socio.objects.all():
            prev = pagos_prev.get(socio.id, 0.0)
            actual = pagos_actual.get(socio.id, 0.0)
            if prev > 0:
                caida = (prev - actual) / prev
                if caida >= payment_drop_ratio:
                    sev, sem = _severity(caida * 100.0, payment_drop_ratio * 100.0)
                    alerts.append(
                        {
                            "tipo_alerta": "cambio_brusco_patron_pago",
                            "dimension": "socio",
                            "entidad_id": str(socio.id),
                            "valor": f"{caida * 100.0:.2f}",
                            "umbral": f"{payment_drop_ratio * 100.0:.2f}",
                            "severidad": sev,
                            "semaforo": sem,
                            "canal_sugerido": "email",
                            "detalle": f"Caida de pagos de {prev:.2f} a {actual:.2f}",
                        }
                    )

        # 3) Primer atraso (mora temprana).
        mora_qs = ResultadoMoraTemprana.objects.select_related("socio", "credito").order_by("socio_id", "fecha_creacion")
        first_alert_socios = set()
        for row in mora_qs:
            if row.socio_id in first_alert_socios:
                continue
            if row.alerta in (ResultadoMoraTemprana.ALERTA_MEDIA, ResultadoMoraTemprana.ALERTA_ALTA):
                first_alert_socios.add(row.socio_id)
                sev = "critical" if row.alerta == ResultadoMoraTemprana.ALERTA_ALTA else "warn"
                sem = "Rojo" if row.alerta == ResultadoMoraTemprana.ALERTA_ALTA else "Amarillo"
                alerts.append(
                    {
                        "tipo_alerta": "primer_atraso_mora_temprana",
                        "dimension": "socio",
                        "entidad_id": str(row.socio_id),
                        "valor": f"{float(row.prob_mora_90d) * 100.0:.2f}",
                        "umbral": "35.00",
                        "severidad": sev,
                        "semaforo": sem,
                        "canal_sugerido": "whatsapp_interno",
                        "detalle": f"Primer atraso detectado (credito {row.credito_id})",
                    }
                )

        # 4) Concentracion de mora (producto/sucursal/ejecutivo).
        mora_alta = mora_qs.filter(alerta=ResultadoMoraTemprana.ALERTA_ALTA)
        total_mora_alta = mora_alta.count()
        if total_mora_alta > 0:
            # producto
            by_producto = {}
            for row in mora_alta:
                producto = _producto_credito(row.credito)
                by_producto[producto] = by_producto.get(producto, 0) + 1
            for producto, cnt in by_producto.items():
                pct = (cnt / total_mora_alta) * 100.0
                if pct >= concentracion_mora_pct:
                    sev, sem = _severity(pct, concentracion_mora_pct)
                    alerts.append(
                        {
                            "tipo_alerta": "concentracion_mora_producto",
                            "dimension": "producto",
                            "entidad_id": producto,
                            "valor": f"{pct:.2f}",
                            "umbral": f"{concentracion_mora_pct:.2f}",
                            "severidad": sev,
                            "semaforo": sem,
                            "canal_sugerido": "email",
                            "detalle": f"Concentracion de mora alta en producto {producto}",
                        }
                    )

            # sucursal
            by_sucursal = {}
            for row in mora_alta:
                suc = _infer_sucursal(row.socio.direccion)
                by_sucursal[suc] = by_sucursal.get(suc, 0) + 1
            for sucursal, cnt in by_sucursal.items():
                pct = (cnt / total_mora_alta) * 100.0
                if pct >= concentracion_mora_pct:
                    sev, sem = _severity(pct, concentracion_mora_pct)
                    alerts.append(
                        {
                            "tipo_alerta": "concentracion_mora_sucursal",
                            "dimension": "sucursal",
                            "entidad_id": sucursal,
                            "valor": f"{pct:.2f}",
                            "umbral": f"{concentracion_mora_pct:.2f}",
                            "severidad": sev,
                            "semaforo": sem,
                            "canal_sugerido": "email",
                            "detalle": f"Concentracion de mora alta en sucursal {sucursal}",
                        }
                    )

            # ejecutivo (si existe mapeo en ContactoCampania)
            socio_to_ejecutivo = {
                row["socio_id"]: row["ejecutivo_id"]
                for row in ContactoCampania.objects.values("socio_id").annotate(ejecutivo_id=Max("ejecutivo_id"))
            }
            by_ejecutivo = {}
            for row in mora_alta:
                ejec = socio_to_ejecutivo.get(row.socio_id)
                if not ejec:
                    continue
                by_ejecutivo[ejec] = by_ejecutivo.get(ejec, 0) + 1
            for ejecutivo, cnt in by_ejecutivo.items():
                pct = (cnt / total_mora_alta) * 100.0
                if pct >= concentracion_mora_pct:
                    sev, sem = _severity(pct, concentracion_mora_pct)
                    alerts.append(
                        {
                            "tipo_alerta": "concentracion_mora_ejecutivo",
                            "dimension": "ejecutivo",
                            "entidad_id": ejecutivo,
                            "valor": f"{pct:.2f}",
                            "umbral": f"{concentracion_mora_pct:.2f}",
                            "severidad": sev,
                            "semaforo": sem,
                            "canal_sugerido": "whatsapp_interno",
                            "detalle": f"Concentracion de mora alta en ejecutivo {ejecutivo}",
                        }
                    )

        # 5) Deterioro de cobertura.
        cartera_total = float(Credito.objects.aggregate(v=Sum("monto"))["v"] or 0.0)
        cartera_vencida_estimada = float(
            mora_alta.select_related("credito").aggregate(v=Sum("credito__deuda_actual"))["v"] or 0.0
        )
        pagos_90d = float(HistorialPago.objects.filter(fecha__gte=d90).aggregate(v=Sum("monto"))["v"] or 0.0)
        cobertura_pct = 0.0 if cartera_vencida_estimada <= 0 else (pagos_90d / cartera_vencida_estimada) * 100.0
        if cobertura_pct < coverage_min_pct:
            sev = "critical" if cobertura_pct < (coverage_min_pct * 0.8) else "warn"
            sem = "Rojo" if sev == "critical" else "Amarillo"
            alerts.append(
                {
                    "tipo_alerta": "deterioro_cobertura",
                    "dimension": "cartera",
                    "entidad_id": "global",
                    "valor": f"{cobertura_pct:.2f}",
                    "umbral": f"{coverage_min_pct:.2f}",
                    "severidad": sev,
                    "semaforo": sem,
                    "canal_sugerido": "email",
                    "detalle": "Cobertura por debajo del minimo esperado",
                }
            )

        # Persist AlertaMonitoreo + notification queue.
        for row in alerts:
            AlertaMonitoreo.objects.create(
                ambito="riesgo",
                metrica=row["tipo_alerta"],
                valor=float(row["valor"] or 0.0),
                umbral=row["umbral"],
                severidad=row["severidad"],
                escalamiento="equipo_riesgo" if row["severidad"] != "critical" else "comite_riesgo_2h",
                estado=AlertaMonitoreo.ESTADO_ACTIVA,
                detalle=row["detalle"][:255],
            )
            channels = ["email"]
            if row["canal_sugerido"] == "whatsapp_interno" or row["severidad"] == "critical":
                channels.append("whatsapp_interno")
            for ch in channels:
                notifications.append(
                    {
                        "fecha_evento_utc": datetime.now(timezone.utc).isoformat(),
                        "canal": ch,
                        "tipo_alerta": row["tipo_alerta"],
                        "entidad_id": row["entidad_id"],
                        "severidad": row["severidad"],
                        "destino": "riesgo@intelicoop.local" if ch == "email" else "grupo_riesgo_interno",
                        "mensaje": row["detalle"],
                    }
                )

        # Semaforos dashboard
        by_tipo = {}
        for row in alerts:
            t = row["tipo_alerta"]
            by_tipo.setdefault(t, {"count": 0, "max_sev": "info"})
            by_tipo[t]["count"] += 1
            if row["severidad"] == "critical":
                by_tipo[t]["max_sev"] = "critical"
            elif row["severidad"] == "warn" and by_tipo[t]["max_sev"] != "critical":
                by_tipo[t]["max_sev"] = "warn"

        sem_rows = []
        for tipo, agg in sorted(by_tipo.items(), key=lambda x: x[0]):
            if agg["max_sev"] == "critical":
                semaforo = "Rojo"
            elif agg["max_sev"] == "warn":
                semaforo = "Amarillo"
            else:
                semaforo = "Verde"
            sem_rows.append(
                {
                    "componente": tipo,
                    "alertas_activas": agg["count"],
                    "semaforo": semaforo,
                    "estado": "En revision" if semaforo != "Verde" else "Cumple",
                }
            )
        if not sem_rows:
            sem_rows.append(
                {"componente": "early_warning_global", "alertas_activas": 0, "semaforo": "Verde", "estado": "Cumple"}
            )

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "tipo_alerta",
                    "dimension",
                    "entidad_id",
                    "valor",
                    "umbral",
                    "severidad",
                    "semaforo",
                    "canal_sugerido",
                    "detalle",
                ],
            )
            writer.writeheader()
            writer.writerows(alerts)

        semaforos_csv.parent.mkdir(parents=True, exist_ok=True)
        with semaforos_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["componente", "alertas_activas", "semaforo", "estado"])
            writer.writeheader()
            writer.writerows(sem_rows)

        notify_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with notify_jsonl.open("w", encoding="utf-8") as file:
            for n in notifications:
                file.write(json.dumps(n, ensure_ascii=True) + "\n")

        lines = [
            "# Early Warning System 1.7",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Alertas detectadas",
            f"- Total alertas: {len(alerts)}",
            f"- Cola notificaciones internas: {len(notifications)}",
            f"- Semaforos en dashboard: {len(sem_rows)}",
            "",
            "## Cobertura de alertas",
            "- caida_fuerte_ahorro",
            "- cambio_brusco_patron_pago",
            "- primer_atraso_mora_temprana",
            "- concentracion_mora_producto/sucursal/ejecutivo",
            "- deterioro_cobertura",
            "",
            "## Estado",
            "- Early Warning System implementado tecnicamente.",
            "- Alertas internas por correo/whatsapp y semaforos de dashboard disponibles.",
            "",
            "## Artefactos",
            f"- Alertas: `{report_csv}`",
            f"- Semaforos dashboard: `{semaforos_csv}`",
            f"- Notificaciones internas: `{notify_jsonl}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[alertas_tempranas_early_warning_1_7] early warning generado"))
        self.stdout.write(f"alertas={len(alerts)} semaforos={len(sem_rows)} notificaciones={len(notifications)}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"semaforos_csv={semaforos_csv}")
        self.stdout.write(f"notify_jsonl={notify_jsonl}")
        self.stdout.write(f"report_md={report_md}")
