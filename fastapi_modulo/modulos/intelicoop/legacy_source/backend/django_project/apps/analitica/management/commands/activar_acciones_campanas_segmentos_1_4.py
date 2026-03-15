import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.core.management import call_command
from django.core.management.MAIN import MAINCommand
from django.utils import timezone as dj_timezone

from apps.analitica.models import Campania


SEGMENT_ACTION_MAP = {
    "Listos para credito": {
        "accion": "preaprobacion_credito",
        "campania_nombre": "Campania Preaprobacion Inteligente",
        "campania_tipo": "sms",
        "prioridad": "alta",
        "canal": "sms",
    },
    "Renovacion segura": {
        "accion": "renovacion_segura",
        "campania_nombre": "Campania Renovacion Segura",
        "campania_tipo": "llamadas",
        "prioridad": "alta",
        "canal": "telefono",
    },
    "Riesgo alto": {
        "accion": "alerta_cobranza_preventiva",
        "campania_nombre": "Campania Cobranza Preventiva",
        "campania_tipo": "llamadas",
        "prioridad": "critica",
        "canal": "telefono",
    },
    "Potencial captacion": {
        "accion": "captacion_ahorro",
        "campania_nombre": "Campania Captacion Premium",
        "campania_tipo": "email",
        "prioridad": "media",
        "canal": "email",
    },
    "Jovenes digitales": {
        "accion": "oferta_digital_simplificada",
        "campania_nombre": "Campania Digital Simplificada",
        "campania_tipo": "app_push",
        "prioridad": "media",
        "canal": "app",
    },
}


class Command(MAINCommand):
    help = "1.4 Punto 3/3: activa campanas y acciones automaticas por segmento."

    def add_arguments(self, parser):
        parser.add_argument("--metodo", choices=("reglas", "clustering"), default="reglas")
        parser.add_argument("--clusters", type=int, default=5)
        parser.add_argument("--autogenerar-segmentacion", action="store_true")
        parser.add_argument("--segmentacion-dataset-csv", default="docs/mineria/customer_intelligence/01_segmentacion_inteligente_socios.csv")
        parser.add_argument("--summary-csv", default="docs/mineria/customer_intelligence/03_resumen_acciones_segmentos.csv")
        parser.add_argument("--assignments-csv", default="docs/mineria/customer_intelligence/03_acciones_campanas_segmentos.csv")
        parser.add_argument("--report-md", default="docs/mineria/customer_intelligence/03_acciones_campanas_segmentos.md")

    def handle(self, *args, **options):
        root = Path(__file__).resolve().parents[6]
        segmentacion_dataset_opt = Path(options["segmentacion_dataset_csv"])
        summary_csv_opt = Path(options["summary_csv"])
        assignments_csv_opt = Path(options["assignments_csv"])
        report_md_opt = Path(options["report_md"])
        segmentacion_dataset = (
            segmentacion_dataset_opt if segmentacion_dataset_opt.is_absolute() else (root / segmentacion_dataset_opt)
        )
        summary_csv = summary_csv_opt if summary_csv_opt.is_absolute() else (root / summary_csv_opt)
        assignments_csv = assignments_csv_opt if assignments_csv_opt.is_absolute() else (root / assignments_csv_opt)
        report_md = report_md_opt if report_md_opt.is_absolute() else (root / report_md_opt)

        if options["autogenerar_segmentacion"] or not segmentacion_dataset.exists():
            call_command(
                "segmentacion_inteligente_socios_1_4",
                metodo=options["metodo"],
                clusters=int(options["clusters"] or 5),
                dataset_csv=str(segmentacion_dataset),
            )

        if not segmentacion_dataset.exists():
            raise ValueError(f"No se encontro dataset de segmentacion: {segmentacion_dataset}")

        hoy = dj_timezone.localdate()
        fin = hoy + timedelta(days=30)

        with segmentacion_dataset.open("r", encoding="utf-8") as file:
            rows = list(csv.DictReader(file))

        assignments = []
        by_segment = {}
        for row in rows:
            segmento = str(row.get("segmento") or "").strip()
            socio_id = row.get("socio_id")
            mapping = SEGMENT_ACTION_MAP.get(segmento)
            if not mapping or not socio_id:
                continue

            campania, _created = Campania.objects.get_or_create(
                nombre=mapping["campania_nombre"],
                tipo=mapping["campania_tipo"],
                fecha_inicio=hoy,
                fecha_fin=fin,
                defaults={"estado": Campania.ESTADO_ACTIVA},
            )
            if campania.estado != Campania.ESTADO_ACTIVA:
                campania.estado = Campania.ESTADO_ACTIVA
                campania.fecha_inicio = hoy
                campania.fecha_fin = fin
                campania.save(update_fields=["estado", "fecha_inicio", "fecha_fin"])

            assignments.append(
                {
                    "socio_id": socio_id,
                    "segmento": segmento,
                    "accion": mapping["accion"],
                    "campania_id": campania.id,
                    "campania_nombre": campania.nombre,
                    "prioridad": mapping["prioridad"],
                    "canal": mapping["canal"],
                    "estado_campania": campania.estado,
                }
            )
            by_segment.setdefault(segmento, {"socios": 0, "campanias": set(), "accion": mapping["accion"]})
            by_segment[segmento]["socios"] += 1
            by_segment[segmento]["campanias"].add(campania.id)

        summary_rows = []
        for segmento, agg in sorted(by_segment.items(), key=lambda x: x[0]):
            summary_rows.append(
                {
                    "segmento": segmento,
                    "accion": agg["accion"],
                    "socios_objetivo": agg["socios"],
                    "campanias_activas": len(agg["campanias"]),
                    "estado": "Activo" if agg["socios"] > 0 else "Sin objetivo",
                }
            )

        assignments_csv.parent.mkdir(parents=True, exist_ok=True)
        with assignments_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "socio_id",
                    "segmento",
                    "accion",
                    "campania_id",
                    "campania_nombre",
                    "prioridad",
                    "canal",
                    "estado_campania",
                ],
            )
            writer.writeheader()
            writer.writerows(assignments)

        summary_csv.parent.mkdir(parents=True, exist_ok=True)
        with summary_csv.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=["segmento", "accion", "socios_objetivo", "campanias_activas", "estado"],
            )
            writer.writeheader()
            writer.writerows(summary_rows)

        lines = [
            "# Activacion de Acciones/Campanas por Segmento 1.4 - Punto 3 de 3",
            "",
            f"Fecha ejecucion UTC: {datetime.now(timezone.utc).isoformat()}",
            f"Dataset segmentacion: `{segmentacion_dataset}`",
            "",
            "## Resultado operativo",
            f"- Asignaciones por socio generadas: {len(assignments)}",
            f"- Segmentos con activacion: {len(summary_rows)}",
            f"- Campanas activas totales: {Campania.objects.filter(estado=Campania.ESTADO_ACTIVA).count()}",
            "",
            "## Estado",
            "- Punto 3 de 3 completado tecnicamente.",
            "- Acciones y campanas automaticas conectadas por segmento.",
            "",
            "## Artefactos",
            f"- Resumen por segmento: `{summary_csv}`",
            f"- Asignaciones por socio: `{assignments_csv}`",
            "",
        ]
        report_md.parent.mkdir(parents=True, exist_ok=True)
        report_md.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("[activar_acciones_campanas_segmentos_1_4] activacion completada"))
        self.stdout.write(f"asignaciones={len(assignments)} segmentos_activos={len(summary_rows)}")
        self.stdout.write(f"summary_csv={summary_csv}")
        self.stdout.write(f"assignments_csv={assignments_csv}")
        self.stdout.write(f"report_md={report_md}")
