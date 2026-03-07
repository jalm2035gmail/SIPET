import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import BaseCommand
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.authentication.models import UserProfile
from apps.analitica.views import DashboardEjecutivosOperativosView, DashboardSemaforosView


def _check(ok: bool, criterio: str, evidencia: str):
    return {
        "criterio": criterio,
        "resultado": "cumple" if ok else "no_cumple",
        "evidencia": evidencia,
        "estado": "Aprobado" if ok else "Pendiente",
    }


class Command(BaseCommand):
    help = "1.8 Cierre UAT: valida criterios de aceptacion de negocio y genera evidencias operativas."

    def add_arguments(self, parser):
        parser.add_argument("--report-csv", default="docs/mineria/dashboards/10_uat_aceptacion_negocio.csv")
        parser.add_argument("--evidencias-jsonl", default="docs/mineria/dashboards/10_uat_evidencias_operacion.jsonl")
        parser.add_argument("--report-md", default="docs/mineria/dashboards/10_uat_aceptacion_negocio.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        evidencias_opt = Path(options["evidencias_jsonl"])
        report_md_opt = Path(options["report_md"])

        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        evidencias_jsonl = evidencias_opt if evidencias_opt.is_absolute() else (root / evidencias_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)
        report_csv.parent.mkdir(parents=True, exist_ok=True)
        evidencias_jsonl.parent.mkdir(parents=True, exist_ok=True)
        report_md.parent.mkdir(parents=True, exist_ok=True)
        call_command(
            "actualizar_dashboards_programado_1_8",
            fuente_ejecucion="uat",
        )

        admin_user, _ = User.objects.get_or_create(username="uat_dashboards_admin", defaults={"email": "uat_admin@intelicoop.local"})
        admin_user.profile.rol = UserProfile.ROL_ADMINISTRADOR
        admin_user.profile.activo = True
        admin_user.profile.save(update_fields=["rol", "activo"])

        auditor_user, _ = User.objects.get_or_create(username="uat_dashboards_auditor", defaults={"email": "uat_auditor@intelicoop.local"})
        auditor_user.profile.rol = UserProfile.ROL_AUDITOR
        auditor_user.profile.activo = True
        auditor_user.profile.save(update_fields=["rol", "activo"])

        factory = APIRequestFactory()
        dashboard_view = DashboardEjecutivosOperativosView.as_view()
        semaforos_view = DashboardSemaforosView.as_view()

        req_admin = factory.get("/api/analitica/ml/dashboard/ejecutivos-operativos/")
        force_authenticate(req_admin, user=admin_user)
        res_admin = dashboard_view(req_admin)
        data_admin = getattr(res_admin, "data", {}) if getattr(res_admin, "status_code", 500) == 200 else {}

        req_aud = factory.get("/api/analitica/ml/dashboard/ejecutivos-operativos/")
        force_authenticate(req_aud, user=auditor_user)
        res_aud = dashboard_view(req_aud)
        data_aud = getattr(res_aud, "data", {}) if getattr(res_aud, "status_code", 500) == 200 else {}

        req_drill = factory.get("/api/analitica/ml/dashboard/ejecutivos-operativos/?sucursal=Yuriria&detalle=1")
        force_authenticate(req_drill, user=admin_user)
        res_drill = dashboard_view(req_drill)
        data_drill = getattr(res_drill, "data", {}) if getattr(res_drill, "status_code", 500) == 200 else {}

        req_sem = factory.get("/api/analitica/ml/dashboard/semaforos/")
        force_authenticate(req_sem, user=admin_user)
        res_sem = semaforos_view(req_sem)
        data_sem = getattr(res_sem, "data", {}) if getattr(res_sem, "status_code", 500) == 200 else {}

        req_csv = factory.get("/api/analitica/ml/dashboard/semaforos/?export=csv")
        force_authenticate(req_csv, user=admin_user)
        res_csv = semaforos_view(req_csv)
        csv_text = ""
        if getattr(res_csv, "status_code", 500) == 200 and hasattr(res_csv, "content"):
            csv_text = res_csv.content.decode("utf-8")

        checks = [
            _check(
                getattr(res_admin, "status_code", 500) == 200
                and all(k in data_admin for k in ("salud_cartera", "colocacion", "captacion", "riesgo", "sucursales", "eficiencia_cobranza", "tendencias")),
                "Disponibilidad de 6 tableros ejecutivos-operativos",
                f"status_admin={getattr(res_admin, 'status_code', 500)}",
            ),
            _check(
                "mensual" in data_admin.get("tendencias", {}) and "trimestral" in data_admin.get("tendencias", {}),
                "Tendencias mensual/trimestral publicadas",
                "tendencias_keys=" + ",".join(sorted(data_admin.get("tendencias", {}).keys())),
            ),
            _check(
                data_admin.get("acceso", {}).get("vista") == "consejo_gerencia"
                and data_aud.get("acceso", {}).get("vista") == "ejecutivo",
                "Control de acceso por rol aplicado",
                f"vista_admin={data_admin.get('acceso', {}).get('vista')} vista_auditor={data_aud.get('acceso', {}).get('vista')}",
            ),
            _check(
                "drilldown" in data_drill and data_drill.get("drilldown", {}).get("sucursal") == "Yuriria",
                "Drill-down por sucursal disponible",
                f"drilldown_keys={','.join(sorted(data_drill.get('drilldown', {}).keys())) if 'drilldown' in data_drill else 'none'}",
            ),
            _check(
                getattr(res_sem, "status_code", 500) == 200
                and "resumen" in data_sem
                and "semaforos" in data_sem,
                "Semaforos operativos disponibles",
                f"semaforos_total={len(data_sem.get('semaforos', []))}",
            ),
            _check(
                getattr(res_csv, "status_code", 500) == 200 and "componente,ambito,metrica,semaforo,estado,valor,umbral,fecha_evento" in csv_text,
                "Exportacion CSV operativa",
                f"csv_len={len(csv_text)}",
            ),
            _check(
                bool(data_admin.get("actualizacion", {}).get("ultima_actualizacion_utc")),
                "Trazabilidad de ultima actualizacion visible",
                f"ultima_actualizacion_utc={data_admin.get('actualizacion', {}).get('ultima_actualizacion_utc')}",
            ),
        ]

        aprobados = sum(1 for c in checks if c["resultado"] == "cumple")
        estado_global = "Aprobado" if aprobados == len(checks) else "Pendiente"

        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["criterio", "resultado", "evidencia", "estado"])
            writer.writeheader()
            writer.writerows(checks)

        ts = datetime.now(timezone.utc).isoformat()
        with evidencias_jsonl.open("w", encoding="utf-8") as file:
            for row in checks:
                file.write(
                    json.dumps(
                        {
                            "timestamp_utc": ts,
                            "modulo": "dashboards_1_8",
                            "criterio": row["criterio"],
                            "resultado": row["resultado"],
                            "evidencia": row["evidencia"],
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )

        md_lines = [
            "# Acta UAT Dashboards 1.8",
            "",
            f"Fecha ejecucion UTC: {ts}",
            f"Resultado global: **{estado_global}** ({aprobados}/{len(checks)} criterios)",
            "",
            "## Criterios evaluados",
        ]
        for row in checks:
            md_lines.append(f"- {row['criterio']}: {row['resultado']} ({row['evidencia']})")
        md_lines.extend(
            [
                "",
                "## Artefactos",
                f"- `{report_csv}`",
                f"- `{evidencias_jsonl}`",
                f"- `{report_md}`",
                "",
            ]
        )
        report_md.write_text("\n".join(md_lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[cerrar_uat_dashboards_1_8] acta UAT generada"))
        self.stdout.write(f"resultado_global={estado_global} aprobados={aprobados}/{len(checks)}")
        self.stdout.write(f"report_csv={report_csv}")
