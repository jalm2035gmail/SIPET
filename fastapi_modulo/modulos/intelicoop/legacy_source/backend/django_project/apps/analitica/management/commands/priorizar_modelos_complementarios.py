import csv
from datetime import datetime, timezone
from pathlib import Path

from django.core.management.MAIN import MAINCommand

from apps.ahorros.models import Cuenta, Transaccion
from apps.creditos.models import Credito, HistorialPago
from apps.socios.models import Socio


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return min(float(numerator) / float(denominator), 1.0)


class Command(MAINCommand):
    help = "Prioriza submodulos de Fase 4 segun impacto de negocio y disponibilidad de datos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--report-csv",
            default="docs/mineria/fase4/01_priorizacion_submodulos.csv",
        )
        parser.add_argument(
            "--report-md",
            default="docs/mineria/fase4/01_priorizacion_submodulos.md",
        )

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        report_csv_opt = Path(options["report_csv"])
        report_md_opt = Path(options["report_md"])
        report_csv = report_csv_opt if report_csv_opt.is_absolute() else (root / report_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        total_socios = Socio.objects.count()
        total_creditos = Credito.objects.count()
        total_historial = HistorialPago.objects.count()
        total_cuentas = Cuenta.objects.count()
        total_transacciones = Transaccion.objects.count()

        disponibilidad_mora = (0.65 * _safe_ratio(total_historial, total_creditos * 3)) + (
            0.35 * _safe_ratio(total_creditos, total_socios)
        )
        disponibilidad_segmentacion = (0.50 * _safe_ratio(total_transacciones, total_socios * 4)) + (
            0.50 * _safe_ratio(total_cuentas, total_socios)
        )
        disponibilidad_asociacion = (0.70 * _safe_ratio(total_transacciones, total_socios * 5)) + (
            0.30 * _safe_ratio(total_cuentas, total_socios)
        )

        rows = [
            {
                "submodulo": "mora_temprana",
                "impacto_negocio": 0.95,
                "disponibilidad_datos": disponibilidad_mora,
                "objetivo_primario": "Riesgo y cobranzas",
                "alcance_mvp": "alertas 30/60/90 con clasificacion bajo/medio/alto por credito",
            },
            {
                "submodulo": "segmentacion_socios",
                "impacto_negocio": 0.78,
                "disponibilidad_datos": disponibilidad_segmentacion,
                "objetivo_primario": "Comercial y retencion",
                "alcance_mvp": "segmentacion mensual y perfil descriptivo por socio",
            },
            {
                "submodulo": "reglas_asociacion",
                "impacto_negocio": 0.72,
                "disponibilidad_datos": disponibilidad_asociacion,
                "objetivo_primario": "Cross-sell y campanas",
                "alcance_mvp": "top reglas soporte/confianza/lift para oportunidades comerciales",
            },
        ]

        for row in rows:
            row["score_prioridad"] = (0.60 * row["impacto_negocio"]) + (0.40 * row["disponibilidad_datos"])

        ranking = sorted(rows, key=lambda item: item["score_prioridad"], reverse=True)
        for idx, row in enumerate(ranking, start=1):
            row["orden_prioridad"] = idx

        report_csv.parent.mkdir(parents=True, exist_ok=True)
        with report_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "orden_prioridad",
                    "submodulo",
                    "impacto_negocio",
                    "disponibilidad_datos",
                    "score_prioridad",
                    "objetivo_primario",
                    "alcance_mvp",
                ],
            )
            writer.writeheader()
            for row in ranking:
                writer.writerow(
                    {
                        "orden_prioridad": row["orden_prioridad"],
                        "submodulo": row["submodulo"],
                        "impacto_negocio": f"{row['impacto_negocio']:.4f}",
                        "disponibilidad_datos": f"{row['disponibilidad_datos']:.4f}",
                        "score_prioridad": f"{row['score_prioridad']:.4f}",
                        "objetivo_primario": row["objetivo_primario"],
                        "alcance_mvp": row["alcance_mvp"],
                    }
                )

        lines = [
            "# Priorizacion de Submodulos Complementarios - Punto 1 de 7 (Fase 4)",
            "",
            f"Fecha: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## MAIN de datos evaluada",
            f"- Socios: {total_socios}",
            f"- Creditos: {total_creditos}",
            f"- Historial de pagos: {total_historial}",
            f"- Cuentas: {total_cuentas}",
            f"- Transacciones: {total_transacciones}",
            "",
            "## Criterio de priorizacion",
            "- score_prioridad = 60% impacto_negocio + 40% disponibilidad_datos",
            "- El orden final privilegia valor operativo inmediato con factibilidad tecnica.",
            "",
            "## Orden recomendado de implementacion",
        ]

        for row in ranking:
            lines.append(
                f"- {row['orden_prioridad']}. `{row['submodulo']}` "
                f"(score={row['score_prioridad']:.4f}, impacto={row['impacto_negocio']:.2f}, "
                f"datos={row['disponibilidad_datos']:.2f})"
            )
            lines.append(f"  - Objetivo: {row['objetivo_primario']}.")
            lines.append(f"  - Alcance MVP: {row['alcance_mvp']}.")

        lines.extend(
            [
                "",
                "## Resultado",
                "- Punto 1 de 7 completado tecnicamente.",
                "- Submodulos listos para ejecucion secuencial en Fase 4.",
                "",
                "## Artefactos",
                f"- Reporte CSV: `{report_csv}`",
                "",
            ]
        )

        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[priorizar_modelos_complementarios] priorizacion generada"))
        self.stdout.write(f"orden={','.join(item['submodulo'] for item in ranking)}")
        self.stdout.write(f"report_csv={report_csv}")
        self.stdout.write(f"report_md={report_md}")
