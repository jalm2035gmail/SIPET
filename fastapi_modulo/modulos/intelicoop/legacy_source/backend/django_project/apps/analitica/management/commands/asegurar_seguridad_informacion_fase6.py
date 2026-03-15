import csv
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.MAIN import MAINCommand

from apps.authentication.models import UserProfile


def _estado(condicion: bool) -> str:
    return "Cumple" if condicion else "En revision"


def _detalle_bool(nombre: str, condicion: bool) -> str:
    return f"{nombre}={'si' if condicion else 'no'}"


class Command(MAINCommand):
    help = "Evalua controles de seguridad de la informacion para Fase 6 (cifrado, roles, acceso y credenciales)."

    def add_arguments(self, parser):
        parser.add_argument("--report-csv", default="docs/mineria/fase6/04_seguridad_informacion.csv")
        parser.add_argument("--report-md", default="docs/mineria/fase6/04_seguridad_informacion.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        drf_auth_classes = settings.REST_FRAMEWORK.get("DEFAULT_AUTHENTICATION_CLASSES", ())
        throttle_classes = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_CLASSES", ())
        throttle_rates = settings.REST_FRAMEWORK.get("DEFAULT_THROTTLE_RATES", {})
        simple_jwt = getattr(settings, "SIMPLE_JWT", {})

        https_redirect = bool(getattr(settings, "SECURE_SSL_REDIRECT", False))
        jwt_habilitado = any("JWTAuthentication" in klass for klass in drf_auth_classes)
        throttling_habilitado = bool(throttle_classes) and bool(throttle_rates.get("anon")) and bool(
            throttle_rates.get("user")
        )

        total_users = User.objects.count()
        strong_hash_prefixes = ("pbkdf2_", "argon2", "bcrypt", "scrypt")
        users_with_strong_hash = User.objects.exclude(password="").filter(
            password__startswith=strong_hash_prefixes
        ).count()
        hash_robusto = total_users == 0 or users_with_strong_hash == total_users

        roles_definidos = len(UserProfile.ROL_CHOICES) >= 4
        perfiles_activos = UserProfile.objects.filter(activo=True).count()
        perfiles_con_2fa = UserProfile.objects.filter(activo=True, two_factor_enabled=True).count()
        cobertura_2fa = 0.0 if perfiles_activos == 0 else (perfiles_con_2fa / perfiles_activos) * 100.0
        control_2fa = perfiles_con_2fa >= 1

        views_path = root / "backend" / "django_project" / "apps" / "analitica" / "views.py"
        views_source = views_path.read_text(encoding="utf-8")
        endpoints_protegidos = views_source.count("permission_classes = [IsAuditorOrHigher]")
        segregacion_roles_api = endpoints_protegidos >= 5

        token_expiracion_configurada = "ACCESS_TOKEN_LIFETIME" in simple_jwt
        token_rotacion_configurada = bool(simple_jwt.get("ROTATE_REFRESH_TOKENS")) and bool(
            simple_jwt.get("BLACKLIST_AFTER_ROTATION")
        )

        rows = [
            {
                "dimension": "cifrado_transito",
                "control": "https_redirect_global",
                "estado": _estado(https_redirect),
                "detalle": _detalle_bool("SECURE_SSL_REDIRECT", https_redirect),
                "severidad": "Alta",
            },
            {
                "dimension": "cifrado_transito",
                "control": "autenticacion_jwt_en_api",
                "estado": _estado(jwt_habilitado),
                "detalle": f"auth_classes={len(drf_auth_classes)}",
                "severidad": "Alta",
            },
            {
                "dimension": "cifrado_reposo",
                "control": "credenciales_hash_robusto",
                "estado": _estado(hash_robusto),
                "detalle": f"usuarios_hash_robusto={users_with_strong_hash}/{total_users}",
                "severidad": "Alta",
            },
            {
                "dimension": "segregacion_rol",
                "control": "roles_MAIN_definidos",
                "estado": _estado(roles_definidos),
                "detalle": f"roles_detectados={len(UserProfile.ROL_CHOICES)}",
                "severidad": "Alta",
            },
            {
                "dimension": "segregacion_rol",
                "control": "endpoints_analitica_con_role_permission",
                "estado": _estado(segregacion_roles_api),
                "detalle": f"endpoints_protegidos={endpoints_protegidos}",
                "severidad": "Alta",
            },
            {
                "dimension": "control_acceso",
                "control": "cobertura_2fa_en_perfiles_activos",
                "estado": _estado(control_2fa),
                "detalle": f"2fa_activos={perfiles_con_2fa}/{perfiles_activos} ({cobertura_2fa:.2f}%)",
                "severidad": "Media",
            },
            {
                "dimension": "control_acceso",
                "control": "throttling_api_habilitado",
                "estado": _estado(throttling_habilitado),
                "detalle": f"anon={throttle_rates.get('anon', 'N/A')}, user={throttle_rates.get('user', 'N/A')}",
                "severidad": "Media",
            },
            {
                "dimension": "credenciales",
                "control": "expiracion_tokens_configurada",
                "estado": _estado(token_expiracion_configurada),
                "detalle": _detalle_bool("ACCESS_TOKEN_LIFETIME", token_expiracion_configurada),
                "severidad": "Alta",
            },
            {
                "dimension": "credenciales",
                "control": "rotacion_tokens_refresh_configurada",
                "estado": _estado(token_rotacion_configurada),
                "detalle": _detalle_bool("ROTATE+BLACKLIST", token_rotacion_configurada),
                "severidad": "Alta",
            },
        ]

        total = len(rows)
        cumple = sum(1 for row in rows if row["estado"] == "Cumple")
        en_revision = total - cumple
        estado_global = "Seguridad MAIN aceptable" if en_revision <= 2 else "Seguridad con brechas por remediar"

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["dimension", "control", "estado", "detalle", "severidad"])
            writer.writeheader()
            writer.writerows(rows)

        lines = [
            "# Seguridad de la Informacion - Punto 4 de 8 (Fase 6)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Resumen",
            f"- Controles evaluados: {total}",
            f"- Controles en cumple: {cumple}",
            f"- Controles en revision: {en_revision}",
            f"- Estado global: {estado_global}",
            "",
            "| Dimension | Control | Estado | Detalle | Severidad |",
            "|---|---|---|---|---|",
        ]
        for row in rows:
            lines.append(
                f"| {row['dimension']} | {row['control']} | {row['estado']} | {row['detalle']} | {row['severidad']} |"
            )
        lines.extend(
            [
                "",
                "## Remediaciones recomendadas",
                "- Activar HTTPS estricto (`SECURE_SSL_REDIRECT`, HSTS y cookies seguras) en ambiente productivo.",
                "- Configurar expiracion y rotacion de JWT (`SIMPLE_JWT`) con blacklist de refresh tokens.",
                "- Elevar cobertura de 2FA para usuarios con privilegios altos.",
                "",
                "## Estado",
                "- Punto 4 de 8 completado tecnicamente.",
                "- Matriz MAIN de seguridad de la informacion generada con evidencia reproducible.",
                "",
                "## Artefactos",
                f"- Reporte CSV: `{report_csv}`",
                "",
            ]
        )
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[asegurar_seguridad_informacion_fase6] evaluacion generada"))
        self.stdout.write(f"controles={total} cumple={cumple} en_revision={en_revision}")
        self.stdout.write(f"estado_global={estado_global}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")
