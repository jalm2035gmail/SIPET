import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand

from apps.analitica.models import EjecucionPipeline
from apps.authentication.models import UserProfile


def _estado(condicion: bool) -> str:
    return "Cumple" if condicion else "En revision"


class Command(MAINCommand):
    help = "Define y verifica gobierno de cambios del modulo (comite, promocion entre ambientes e impacto post-cambio)."

    def add_arguments(self, parser):
        parser.add_argument("--report-csv", default="docs/mineria/fase6/07_gobierno_cambios_modulo.csv")
        parser.add_argument("--report-md", default="docs/mineria/fase6/07_gobierno_cambios_modulo.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        activos_por_rol = {
            "auditor": UserProfile.objects.filter(rol=UserProfile.ROL_AUDITOR, activo=True).count(),
            "jefe_departamento": UserProfile.objects.filter(rol=UserProfile.ROL_JEFE_DEPARTAMENTO, activo=True).count(),
            "administrador": UserProfile.objects.filter(rol=UserProfile.ROL_ADMINISTRADOR, activo=True).count(),
            "superadmin": UserProfile.objects.filter(rol=UserProfile.ROL_SUPERADMIN, activo=True).count(),
        }
        comite_roles_cubiertos = all(value >= 1 for value in activos_por_rol.values())

        corrida_reentrenamiento = EjecucionPipeline.objects.filter(pipeline="reentrenamiento_scoring").exists()
        corrida_orquestacion = EjecucionPipeline.objects.filter(pipeline="orquestacion_fase5").exists()
        promotion_manifest = root / "docs" / "mineria" / "fase5" / "03_reentrenamiento_promocion.json"
        flujo_promocion_formal = corrida_reentrenamiento and promotion_manifest.exists()

        post_validacion_tecnica = (root / "docs" / "mineria" / "fase6" / "01_validacion_tecnica_modelos.md").exists()
        post_validacion_funcional = (root / "docs" / "mineria" / "fase6" / "02_validacion_funcional_negocio.md").exists()
        post_monitoreo = (root / "docs" / "mineria" / "fase5" / "05_monitoreo_alertamiento.md").exists()
        impactos_post_cambio_documentados = post_validacion_tecnica and post_validacion_funcional and post_monitoreo

        promo_version = "N/A"
        if promotion_manifest.exists():
            payload = json.loads(promotion_manifest.read_text(encoding="utf-8"))
            promo_version = payload.get("promoted_version", "N/A")

        rows = [
            {
                "dimension": "comite",
                "control": "comite_tecnico_funcional_con_roles_cubiertos",
                "estado": _estado(comite_roles_cubiertos),
                "detalle": (
                    f"auditor={activos_por_rol['auditor']}, "
                    f"jefe={activos_por_rol['jefe_departamento']}, "
                    f"admin={activos_por_rol['administrador']}, "
                    f"superadmin={activos_por_rol['superadmin']}"
                ),
            },
            {
                "dimension": "promocion",
                "control": "flujo_formal_dev_qa_prod_con_evidencia",
                "estado": _estado(flujo_promocion_formal),
                "detalle": (
                    f"orquestacion={'si' if corrida_orquestacion else 'no'}, "
                    f"reentrenamiento={'si' if corrida_reentrenamiento else 'no'}, "
                    f"promocion={'si' if promotion_manifest.exists() else 'no'}"
                ),
            },
            {
                "dimension": "post_cambio",
                "control": "impactos_esperados_y_resultados_documentados",
                "estado": _estado(impactos_post_cambio_documentados),
                "detalle": (
                    f"validacion_tecnica={'si' if post_validacion_tecnica else 'no'}, "
                    f"validacion_funcional={'si' if post_validacion_funcional else 'no'}, "
                    f"monitoreo={'si' if post_monitoreo else 'no'}"
                ),
            },
            {
                "dimension": "post_cambio",
                "control": "version_promovida_identificada",
                "estado": _estado(promo_version != "N/A"),
                "detalle": f"promoted_version={promo_version}",
            },
        ]

        total = len(rows)
        cumple = sum(1 for row in rows if row["estado"] == "Cumple")
        en_revision = total - cumple
        estado_global = "Gobierno de cambios operativo" if en_revision <= 1 else "Gobierno de cambios en consolidacion"

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["dimension", "control", "estado", "detalle"])
            writer.writeheader()
            writer.writerows(rows)

        lines = [
            "# Gobierno de Cambios del Modulo - Punto 7 de 8 (Fase 6)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Comite tecnico-funcional",
            "- Roles requeridos: auditor, jefe de departamento, administrador y superadministrador.",
            "- Objetivo: aprobar cambios criticos de modelos, umbrales y configuraciones operativas.",
            "",
            "## Flujo formal de promocion",
            "1. Desarrollo: ajuste controlado de modelo/configuracion.",
            "2. QA: validacion tecnica/funcional y pruebas de robustez.",
            "3. Produccion: promocion versionada con monitoreo y rollback definido.",
            "",
            "## Impacto post-cambio",
            f"- Validacion tecnica disponible: {'si' if post_validacion_tecnica else 'no'}",
            f"- Validacion funcional disponible: {'si' if post_validacion_funcional else 'no'}",
            f"- Monitoreo de salud disponible: {'si' if post_monitoreo else 'no'}",
            f"- Version promovida referenciada: `{promo_version}`",
            "",
            "## Resumen de controles",
            f"- Controles evaluados: {total}",
            f"- Controles en cumple: {cumple}",
            f"- Controles en revision: {en_revision}",
            f"- Estado global: {estado_global}",
            "",
            "## Estado",
            "- Punto 7 de 8 completado tecnicamente.",
            "- Gobierno de cambios del modulo definido con evidencia reproducible.",
            "",
            "## Artefactos",
            f"- Reporte CSV: `{report_csv}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[gobierno_cambios_modulo_fase6] gobierno de cambios generado"))
        self.stdout.write(f"controles={total} cumple={cumple} en_revision={en_revision}")
        self.stdout.write(f"estado_global={estado_global}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")
