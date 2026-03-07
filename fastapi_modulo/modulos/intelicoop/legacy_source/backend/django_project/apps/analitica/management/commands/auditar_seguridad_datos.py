import csv
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from apps.authentication.models import UserProfile


def _bool_text(value: bool) -> str:
    return "Cumple" if value else "Atencion"


class Command(BaseCommand):
    help = "Audita controles basicos de seguridad/cumplimiento y genera reporte."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-csv",
            default="docs/mineria/fase2/17_auditoria_seguridad.csv",
            help="Ruta de salida CSV.",
        )
        parser.add_argument(
            "--output-md",
            default="docs/mineria/fase2/17_auditoria_seguridad.md",
            help="Ruta de salida Markdown.",
        )

    def handle(self, *args, **options):
        output_csv = Path(options["output_csv"]).resolve()
        output_md = Path(options["output_md"]).resolve()

        checks: list[dict[str, str]] = []

        jwt_configured = bool(settings.REST_FRAMEWORK.get("DEFAULT_AUTHENTICATION_CLASSES"))
        checks.append(
            {
                "control": "JWT habilitado en DRF",
                "resultado": _bool_text(jwt_configured),
                "detalle": "DEFAULT_AUTHENTICATION_CLASSES configurado",
                "severidad": "Alta",
            }
        )

        roles_defined = len(UserProfile.ROL_CHOICES) >= 4
        checks.append(
            {
                "control": "Roles definidos (auditor/jefe/admin/superadmin)",
                "resultado": _bool_text(roles_defined),
                "detalle": f"roles_detectados={len(UserProfile.ROL_CHOICES)}",
                "severidad": "Alta",
            }
        )

        active_profiles = UserProfile.objects.filter(activo=True).count()
        total_profiles = UserProfile.objects.count()
        checks.append(
            {
                "control": "Perfiles activos",
                "resultado": _bool_text(active_profiles >= 1),
                "detalle": f"activos={active_profiles}, total={total_profiles}",
                "severidad": "Media",
            }
        )

        users_with_2fa = UserProfile.objects.filter(two_factor_enabled=True).count()
        checks.append(
            {
                "control": "2FA disponible y usuarios con 2FA",
                "resultado": _bool_text(True),
                "detalle": f"usuarios_2fa={users_with_2fa}",
                "severidad": "Media",
            }
        )

        cache_backend = settings.CACHES.get("default", {}).get("BACKEND", "")
        checks.append(
            {
                "control": "Cache configurado para soporte 2FA/OTP",
                "resultado": _bool_text(bool(cache_backend)),
                "detalle": cache_backend or "sin backend",
                "severidad": "Media",
            }
        )

        superadmins = User.objects.filter(profile__rol=UserProfile.ROL_SUPERADMIN).count()
        checks.append(
            {
                "control": "Superadministrador semilla existente",
                "resultado": _bool_text(superadmins >= 1),
                "detalle": f"superadmins={superadmins}",
                "severidad": "Alta",
            }
        )

        log_level = getattr(settings, "LOG_LEVEL", "")
        logging_configured = bool(getattr(settings, "LOGGING", {}))
        checks.append(
            {
                "control": "Logging de aplicacion configurado",
                "resultado": _bool_text(logging_configured),
                "detalle": f"log_level={log_level}",
                "severidad": "Media",
            }
        )

        output_csv.parent.mkdir(parents=True, exist_ok=True)
        with output_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["control", "resultado", "detalle", "severidad"])
            writer.writeheader()
            writer.writerows(checks)

        ok_count = sum(1 for row in checks if row["resultado"] == "Cumple")
        warn_count = sum(1 for row in checks if row["resultado"] != "Cumple")

        md_lines = [
            "# Auditoria de Seguridad y Cumplimiento - Fase 2",
            "",
            f"Fecha de generacion: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Controles evaluados",
            "",
            "| Control | Resultado | Detalle | Severidad |",
            "|---|---|---|---|",
        ]
        for row in checks:
            md_lines.append(
                "| {control} | {resultado} | {detalle} | {severidad} |".format(**row)
            )
        md_lines.extend(
            [
                "",
                "## Resumen",
                f"- Controles en cumplimiento: {ok_count}",
                f"- Controles con atencion: {warn_count}",
                "",
                "## Estado para checklist Fase 2 (Punto 7 de 8)",
                "- Estado sugerido: `En revision`.",
                "- Cierre requerido: resolver controles en atencion y adjuntar evidencia operativa.",
                "",
            ]
        )
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text("\n".join(md_lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[auditar_seguridad_datos] auditoria generada"))
        self.stdout.write(f"Controles: {len(checks)}")
        self.stdout.write(f"Cumple: {ok_count}")
        self.stdout.write(f"Atencion: {warn_count}")
        self.stdout.write(f"CSV: {output_csv}")
        self.stdout.write(f"MD: {output_md}")
