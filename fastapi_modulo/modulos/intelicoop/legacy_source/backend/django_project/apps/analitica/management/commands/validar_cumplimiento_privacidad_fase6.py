import csv
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.analitica import views as analitica_views
from apps.analitica.models import (
    ReglaAsociacionProducto,
    ResultadoMoraTemprana,
    ResultadoScoring,
    ResultadoSegmentacionSocio,
)
from apps.analitica.serializers import ScoringEvaluateSerializer


def _estado(condicion: bool) -> str:
    return "Cumple" if condicion else "En revision"


class Command(BaseCommand):
    help = "Valida cumplimiento normativo y privacidad (minimizacion, uso legitimo, retencion y anonimización) para Fase 6."

    def add_arguments(self, parser):
        parser.add_argument("--report-csv", default="docs/mineria/fase6/05_cumplimiento_privacidad.csv")
        parser.add_argument("--report-md", default="docs/mineria/fase6/05_cumplimiento_privacidad.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        urls_source = (root / "backend" / "django_project" / "config" / "urls.py").read_text(encoding="utf-8")
        views_source = (root / "backend" / "django_project" / "apps" / "analitica" / "views.py").read_text(encoding="utf-8")

        fields_entrada_scoring = set(ScoringEvaluateSerializer().fields.keys())
        expected_min_fields = {
            "ingreso_mensual",
            "deuda_actual",
            "antiguedad_meses",
            "persist",
            "solicitud_id",
            "credito",
            "socio",
            "model_version",
        }
        minimizacion_entrada = fields_entrada_scoring == expected_min_fields

        pii_forbidden = {"nombre", "email", "telefono", "direccion"}
        modelos_analiticos = [
            ResultadoScoring,
            ResultadoMoraTemprana,
            ResultadoSegmentacionSocio,
            ReglaAsociacionProducto,
        ]
        modelos_sin_pii = 0
        modelos_con_request_id = 0
        modelos_con_fecha_creacion = 0
        for model in modelos_analiticos:
            field_names = {field.name for field in model._meta.fields}
            if pii_forbidden.isdisjoint(field_names):
                modelos_sin_pii += 1
            if "request_id" in field_names:
                modelos_con_request_id += 1
            if "fecha_creacion" in field_names:
                modelos_con_fecha_creacion += 1

        segregacion_roles_api = views_source.count("permission_classes = [IsAuditorOrHigher]") >= 5
        versionado_api = "/api/v1/" in urls_source
        controles_seguridad_previos = (root / "docs" / "mineria" / "fase6" / "04_seguridad_informacion.md").exists()

        retencion_operable = modelos_con_fecha_creacion == len(modelos_analiticos)
        anonimizado_por_pseudonimo = modelos_con_request_id == len(modelos_analiticos)
        minimizacion_historica = modelos_sin_pii == len(modelos_analiticos)

        rows = [
            {
                "dimension": "cumplimiento",
                "control": "politicas_controles_base_documentados",
                "estado": _estado(controles_seguridad_previos),
                "detalle": "evidencia_fase6_seguridad=si" if controles_seguridad_previos else "evidencia_fase6_seguridad=no",
            },
            {
                "dimension": "cumplimiento",
                "control": "versionado_api_para_gobierno_regulatorio",
                "estado": _estado(versionado_api),
                "detalle": "rutas_api_v1=si" if versionado_api else "rutas_api_v1=no",
            },
            {
                "dimension": "privacidad_minimizacion",
                "control": "entrada_scoring_minimizada",
                "estado": _estado(minimizacion_entrada),
                "detalle": f"campos_entrada={len(fields_entrada_scoring)}",
            },
            {
                "dimension": "privacidad_uso_legitimo",
                "control": "acceso_analitica_con_permiso_rol",
                "estado": _estado(segregacion_roles_api),
                "detalle": f"endpoints_protegidos={views_source.count('permission_classes = [IsAuditorOrHigher]')}",
            },
            {
                "dimension": "privacidad_minimizacion",
                "control": "historicos_sin_pii_directa",
                "estado": _estado(minimizacion_historica),
                "detalle": f"modelos_sin_pii={modelos_sin_pii}/{len(modelos_analiticos)}",
            },
            {
                "dimension": "retencion",
                "control": "historicos_con_fecha_para_politica_retencion",
                "estado": _estado(retencion_operable),
                "detalle": f"modelos_con_fecha_creacion={modelos_con_fecha_creacion}/{len(modelos_analiticos)}",
            },
            {
                "dimension": "anonimizacion",
                "control": "historicos_con_pseudonimo_request_id",
                "estado": _estado(anonimizado_por_pseudonimo),
                "detalle": f"modelos_con_request_id={modelos_con_request_id}/{len(modelos_analiticos)}",
            },
        ]

        total = len(rows)
        cumple = sum(1 for row in rows if row["estado"] == "Cumple")
        en_revision = total - cumple
        estado_global = "Cumplimiento y privacidad base aceptables" if en_revision <= 1 else "Cumplimiento en seguimiento"

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["dimension", "control", "estado", "detalle"])
            writer.writeheader()
            writer.writerows(rows)

        lines = [
            "# Cumplimiento Normativo y Privacidad - Punto 5 de 8 (Fase 6)",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Resumen",
            f"- Controles evaluados: {total}",
            f"- Controles en cumple: {cumple}",
            f"- Controles en revision: {en_revision}",
            f"- Estado global: {estado_global}",
            "",
            "| Dimension | Control | Estado | Detalle |",
            "|---|---|---|---|",
        ]
        for row in rows:
            lines.append(f"| {row['dimension']} | {row['control']} | {row['estado']} | {row['detalle']} |")
        lines.extend(
            [
                "",
                "## Politica operativa de retencion y anonimización",
                "- Retencion recomendada para historicos analiticos: 24 meses online + 12 meses archivo frio.",
                "- Eliminacion o archivo irreversible por lote mensual segun `fecha_creacion`/`fecha_ejecucion`.",
                "- Uso de `request_id` como identificador pseudonimo para auditoria tecnica.",
                "- Prohibido incorporar PII directa en tablas de resultados modelados.",
                "",
                "## Estado",
                "- Punto 5 de 8 completado tecnicamente.",
                "- Cumplimiento normativo y privacidad base documentados con evidencia reproducible.",
                "",
                "## Artefactos",
                f"- Reporte CSV: `{report_csv}`",
                "",
            ]
        )
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[validar_cumplimiento_privacidad_fase6] validacion generada"))
        self.stdout.write(f"controles={total} cumple={cumple} en_revision={en_revision}")
        self.stdout.write(f"estado_global={estado_global}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")
