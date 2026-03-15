import csv
import html
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from statistics import pstdev

from django.core.management import call_command
from django.utils.decorators import method_decorator
from django.http import HttpResponse, JsonResponse
from django.db.models import Avg, Count, Max, Sum
from django.utils import timezone
from django.views.decorators.cache import cache_page
from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ahorros.models import Cuenta, Transaccion
from apps.creditos.models import Credito
from apps.creditos.models import HistorialPago
from apps.socios.models import Socio
from apps.authentication.permissions import IsAdministradorOrHigher, IsAuditorOrHigher
from apps.authentication.models import UserProfile

from .models import (
    AlertaMonitoreo,
    Campania,
    Prospecto,
    ReglaAsociacionProducto,
    ResultadoMoraTemprana,
    ResultadoScoring,
    ResultadoSegmentacionSocio,
)
from .serializers import (
    CampaniaSerializer,
    MoraTempranaEvaluateSerializer,
    ProspectoSerializer,
    ReglaAsociacionProductoSerializer,
    ResultadoMoraTempranaSerializer,
    SegmentacionInteligenteRunSerializer,
    ResultadoSegmentacionSocioSerializer,
    ResultadoScoringSerializer,
    ScoringEvaluateSerializer,
)


def ping(_request):
    return JsonResponse({'app': 'analitica', 'status': 'ok'})


@method_decorator(cache_page(60), name='dispatch')
class CampaniaListCreateView(generics.ListCreateAPIView):
    queryset = Campania.objects.all()
    serializer_class = CampaniaSerializer
    permission_classes = [IsAuditorOrHigher]


@method_decorator(cache_page(60), name='dispatch')
class ProspectoListView(generics.ListAPIView):
    queryset = Prospecto.objects.all()
    serializer_class = ProspectoSerializer
    permission_classes = [IsAuditorOrHigher]


class ResultadoScoringListCreateView(generics.ListCreateAPIView):
    serializer_class = ResultadoScoringSerializer
    permission_classes = [IsAuditorOrHigher]

    def get_queryset(self):
        queryset = ResultadoScoring.objects.select_related("credito", "socio").all()

        solicitud_id = self.request.query_params.get("solicitud_id")
        socio = self.request.query_params.get("socio")
        credito = self.request.query_params.get("credito")
        model_version = self.request.query_params.get("model_version")
        fecha_desde = self.request.query_params.get("fecha_desde")
        fecha_hasta = self.request.query_params.get("fecha_hasta")

        if solicitud_id:
            queryset = queryset.filter(solicitud_id=solicitud_id)
        if socio:
            queryset = queryset.filter(socio_id=socio)
        if credito:
            queryset = queryset.filter(credito_id=credito)
        if model_version:
            queryset = queryset.filter(model_version=model_version)
        if fecha_desde:
            queryset = queryset.filter(fecha_creacion__date__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_creacion__date__lte=fecha_hasta)

        return queryset


class ResultadoScoringBySolicitudView(APIView):
    permission_classes = [IsAuditorOrHigher]

    def get(self, request, solicitud_id):
        result = ResultadoScoring.objects.filter(solicitud_id=solicitud_id).order_by("-id").first()
        if not result:
            return Response({"detail": "No encontrado."}, status=404)
        return Response(ResultadoScoringSerializer(result).data)


class ResultadoScoringBySocioView(APIView):
    permission_classes = [IsAuditorOrHigher]

    def get(self, request, socio_id):
        results = (
            ResultadoScoring.objects.filter(socio_id=socio_id)
            .select_related("credito", "socio")
            .order_by("-id")
        )
        return Response(ResultadoScoringSerializer(results, many=True).data)


class ScoringSocioRecomendacionView(APIView):
    permission_classes = [IsAuditorOrHigher]

    def get(self, request, socio_id):
        socio = Socio.objects.filter(pk=socio_id).first()
        if socio is None:
            return Response({"detail": "Socio no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        queryset = ResultadoScoring.objects.filter(socio_id=socio_id).order_by("-fecha_creacion", "-id")
        if not queryset.exists():
            return Response(
                {
                    "socio_id": socio.id,
                    "socio_nombre": socio.nombre,
                    "segmento": socio.segmento,
                    "tiene_scoring": False,
                    "detalle": "No hay inferencias de scoring para este socio.",
                }
            )

        latest = queryset.first()
        total = queryset.count()
        score_promedio = float(queryset.aggregate(v=Avg("score"))["v"] or 0.0)
        aprobaciones = queryset.filter(recomendacion="aprobar").count()
        riesgo_alto = queryset.filter(riesgo=ResultadoScoring.RIESGO_ALTO).count()
        tendencia = list(
            queryset.values("fecha_creacion", "score", "recomendacion", "riesgo", "model_version")[:6]
        )

        score_latest = float(latest.score)
        decision = "preaprobado" if latest.recomendacion == "aprobar" and score_latest >= 0.80 else "revision"
        if latest.riesgo == ResultadoScoring.RIESGO_ALTO:
            decision = "bloqueado_riesgo"

        return Response(
            {
                "socio_id": socio.id,
                "socio_nombre": socio.nombre,
                "segmento": socio.segmento,
                "tiene_scoring": True,
                "actual": {
                    "solicitud_id": latest.solicitud_id,
                    "score": round(score_latest, 4),
                    "recomendacion": latest.recomendacion,
                    "riesgo": latest.riesgo,
                    "model_version": latest.model_version,
                    "fecha_scoring": latest.fecha_creacion,
                    "decision_operativa": decision,
                },
                "resumen": {
                    "inferencias_totales": total,
                    "score_promedio": round(score_promedio, 4),
                    "tasa_aprobacion_pct": round((aprobaciones / total) * 100.0 if total else 0.0, 2),
                    "riesgo_alto_pct": round((riesgo_alto / total) * 100.0 if total else 0.0, 2),
                },
                "historial_reciente": tendencia,
            }
        )


class ScoringResumenView(APIView):
    permission_classes = [IsAuditorOrHigher]

    def get(self, request):
        queryset = ResultadoScoring.objects.all()
        model_version = request.query_params.get("model_version")
        fecha_desde = request.query_params.get("fecha_desde")
        fecha_hasta = request.query_params.get("fecha_hasta")

        if model_version:
            queryset = queryset.filter(model_version=model_version)
        if fecha_desde:
            queryset = queryset.filter(fecha_creacion__date__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_creacion__date__lte=fecha_hasta)

        MAIN = queryset.aggregate(
            total=Count("id"),
            score_promedio=Avg("score"),
        )
        por_riesgo = {
            item["riesgo"]: item["total"]
            for item in queryset.values("riesgo").annotate(total=Count("id"))
        }
        por_recomendacion = {
            item["recomendacion"]: item["total"]
            for item in queryset.values("recomendacion").annotate(total=Count("id"))
        }

        recientes = list(
            queryset.order_by("-id").values(
                "id",
                "solicitud_id",
                "socio_id",
                "credito_id",
                "score",
                "recomendacion",
                "riesgo",
                "model_version",
                "fecha_creacion",
            )[:5]
        )

        return Response(
            {
                "total_inferencias": MAIN["total"] or 0,
                "score_promedio": float(MAIN["score_promedio"] or 0),
                "por_riesgo": {
                    "bajo": por_riesgo.get("bajo", 0),
                    "medio": por_riesgo.get("medio", 0),
                    "alto": por_riesgo.get("alto", 0),
                },
                "por_recomendacion": {
                    "aprobar": por_recomendacion.get("aprobar", 0),
                    "evaluar": por_recomendacion.get("evaluar", 0),
                    "rechazar": por_recomendacion.get("rechazar", 0),
                },
                "recientes": recientes,
            }
        )


def _ejecutivo_sugerido_por_sucursal(sucursal: str) -> str:
    mapping = {
        "Yuriria": "ejecutivo_yuriria",
        "Cuitzeo": "ejecutivo_cuitzeo",
        "Santa Ana Maya": "ejecutivo_santa_ana_maya",
    }
    return mapping.get(sucursal, "ejecutivo_general")


def _prioridad_preaprobado(score: float, segmento: str) -> str:
    if score >= 0.9 or (score >= 0.85 and segmento == Socio.SEGMENTO_GRAN_AHORRADOR):
        return "alta"
    if score >= 0.8:
        return "media"
    return "baja"


class ColocacionPreaprobadosView(APIView):
    permission_classes = [IsAuditorOrHigher]

    def get(self, request):
        sucursal_filter = (request.query_params.get("sucursal") or "").strip()
        ejecutivo_filter = (request.query_params.get("ejecutivo") or "").strip().lower()
        q_filter = (request.query_params.get("q") or "").strip().lower()
        export_format = (request.query_params.get("export") or "").strip().lower()
        limit_raw = (request.query_params.get("limit") or "100").strip()
        score_min_raw = (request.query_params.get("score_min") or "0.80").strip()

        try:
            limit = max(1, min(500, int(limit_raw)))
        except ValueError:
            limit = 100
        try:
            score_min = float(score_min_raw)
        except ValueError:
            score_min = 0.80
        score_min = max(0.0, min(1.0, score_min))

        high_mora_socios = set(
            ResultadoMoraTemprana.objects.filter(
                alerta=ResultadoMoraTemprana.ALERTA_ALTA,
                fecha_corte__gte=timezone.localdate() - timedelta(days=90),
            ).values_list("socio_id", flat=True)
        )

        best_by_socio = {}
        scoring_qs = (
            ResultadoScoring.objects.exclude(socio_id__isnull=True)
            .select_related("socio", "credito")
            .order_by("socio_id", "-score", "-fecha_creacion", "-id")
        )
        for row in scoring_qs:
            if row.recomendacion != "aprobar" or float(row.score) < score_min:
                continue
            if row.socio_id not in best_by_socio:
                best_by_socio[row.socio_id] = row

        preaprobados = []
        for socio_id, row in best_by_socio.items():
            score = float(row.score)
            if socio_id in high_mora_socios:
                continue

            socio = row.socio
            if socio is None:
                continue
            sucursal = _infer_sucursal_dashboard(socio.direccion)
            ejecutivo = _ejecutivo_sugerido_por_sucursal(sucursal)
            ingreso = float(row.ingreso_mensual)
            deuda = float(row.deuda_actual)
            capacidad_mensual = max(0.0, ingreso - deuda)
            credito_MAIN = float(row.credito.monto) if row.credito_id else (capacidad_mensual * 6.0)
            monto_sugerido = round(max(0.0, min(credito_MAIN, capacidad_mensual * 8.0)), 2)

            item = {
                "socio_id": socio.id,
                "socio_nombre": socio.nombre,
                "segmento": socio.segmento,
                "sucursal": sucursal,
                "ejecutivo_sugerido": ejecutivo,
                "score": round(score, 4),
                "recomendacion": row.recomendacion,
                "riesgo": row.riesgo,
                "monto_sugerido": monto_sugerido,
                "prioridad": _prioridad_preaprobado(score, socio.segmento),
                "solicitud_id": row.solicitud_id,
                "model_version": row.model_version,
                "fecha_scoring": row.fecha_creacion,
            }

            if sucursal_filter and item["sucursal"] != sucursal_filter:
                continue
            if ejecutivo_filter and item["ejecutivo_sugerido"].lower() != ejecutivo_filter:
                continue
            if q_filter and q_filter not in item["socio_nombre"].lower() and q_filter not in item["solicitud_id"].lower():
                continue
            preaprobados.append(item)

        preaprobados = sorted(
            preaprobados,
            key=lambda x: (x["prioridad"] == "alta", x["score"], x["monto_sugerido"]),
            reverse=True,
        )[:limit]

        if export_format == "csv":
            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = 'attachment; filename="preaprobados_colocacion.csv"'
            writer = csv.DictWriter(
                response,
                fieldnames=[
                    "socio_id",
                    "socio_nombre",
                    "segmento",
                    "sucursal",
                    "ejecutivo_sugerido",
                    "score",
                    "recomendacion",
                    "riesgo",
                    "monto_sugerido",
                    "prioridad",
                    "solicitud_id",
                    "model_version",
                    "fecha_scoring",
                ],
            )
            writer.writeheader()
            for row in preaprobados:
                writer.writerow(row)
            return response

        resumen = {
            "total_preaprobados": len(preaprobados),
            "monto_sugerido_total": round(sum(item["monto_sugerido"] for item in preaprobados), 2),
            "promedio_score": round(
                (sum(item["score"] for item in preaprobados) / len(preaprobados)) if preaprobados else 0.0,
                4,
            ),
        }

        return Response({"resumen": resumen, "items": preaprobados})


def _infer_producto_credito(credito: Credito) -> str:
    plazo = int(credito.plazo or 0)
    monto = float(credito.monto or 0)
    if plazo <= 6 and monto <= 5000:
        return "microcredito"
    if plazo <= 18:
        return "consumo"
    return "productivo"


class ReportesSucursalProductoEjecutivoView(APIView):
    permission_classes = [IsAuditorOrHigher]

    def get(self, request):
        sucursal_filter = (request.query_params.get("sucursal") or "").strip()
        producto_filter = (request.query_params.get("producto") or "").strip().lower()
        ejecutivo_filter = (request.query_params.get("ejecutivo") or "").strip().lower()
        export_format = (request.query_params.get("export") or "").strip().lower()
        fecha_desde = (request.query_params.get("fecha_desde") or "").strip()
        fecha_hasta = (request.query_params.get("fecha_hasta") or "").strip()

        queryset = Credito.objects.select_related("socio").all()
        if fecha_desde:
            queryset = queryset.filter(fecha_creacion__date__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_creacion__date__lte=fecha_hasta)

        grouped = {}
        for credito in queryset:
            socio = credito.socio
            sucursal = _infer_sucursal_dashboard(socio.direccion if socio else "")
            producto = _infer_producto_credito(credito)
            ejecutivo = _ejecutivo_sugerido_por_sucursal(sucursal)

            if sucursal_filter and sucursal != sucursal_filter:
                continue
            if producto_filter and producto != producto_filter:
                continue
            if ejecutivo_filter and ejecutivo.lower() != ejecutivo_filter:
                continue

            key = (sucursal, producto, ejecutivo)
            if key not in grouped:
                grouped[key] = {
                    "sucursal": sucursal,
                    "producto": producto,
                    "ejecutivo": ejecutivo,
                    "creditos_total": 0,
                    "monto_total": 0.0,
                    "solicitados": 0,
                    "aprobados": 0,
                    "rechazados": 0,
                }
            entry = grouped[key]
            entry["creditos_total"] += 1
            entry["monto_total"] += float(credito.monto)
            if credito.estado == Credito.ESTADO_SOLICITADO:
                entry["solicitados"] += 1
            elif credito.estado == Credito.ESTADO_APROBADO:
                entry["aprobados"] += 1
            elif credito.estado == Credito.ESTADO_RECHAZADO:
                entry["rechazados"] += 1

        items = []
        for _, entry in grouped.items():
            total = entry["creditos_total"]
            aprobados = entry["aprobados"]
            entry["monto_total"] = round(entry["monto_total"], 2)
            entry["monto_promedio"] = round((entry["monto_total"] / total) if total else 0.0, 2)
            entry["tasa_aprobacion_pct"] = round((aprobados / total) * 100.0 if total else 0.0, 2)
            items.append(entry)

        items = sorted(items, key=lambda x: (x["monto_total"], x["creditos_total"]), reverse=True)

        if export_format == "csv":
            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = 'attachment; filename="reporte_sucursal_producto_ejecutivo.csv"'
            writer = csv.DictWriter(
                response,
                fieldnames=[
                    "sucursal",
                    "producto",
                    "ejecutivo",
                    "creditos_total",
                    "monto_total",
                    "monto_promedio",
                    "solicitados",
                    "aprobados",
                    "rechazados",
                    "tasa_aprobacion_pct",
                ],
            )
            writer.writeheader()
            for row in items:
                writer.writerow(row)
            return response

        resumen = {
            "total_grupos": len(items),
            "creditos_total": sum(item["creditos_total"] for item in items),
            "monto_total": round(sum(item["monto_total"] for item in items), 2),
        }
        return Response({"resumen": resumen, "items": items})


def _parse_periodo_mensual(periodo_raw: str):
    if not periodo_raw:
        today = timezone.localdate()
        start = today.replace(day=1)
    else:
        try:
            year_str, month_str = periodo_raw.split("-", 1)
            year = int(year_str)
            month = int(month_str)
            start = date(year, month, 1)
        except (ValueError, TypeError):
            return None, None, None
    if start.month == 12:
        end = date(start.year + 1, 1, 1)
    else:
        end = date(start.year, start.month + 1, 1)
    return start, end, start.strftime("%Y-%m")


def _flatten_reporte_mensual_rows(periodo_label: str, payload: dict):
    rows = []
    for metrica, valor in payload["riesgo"].items():
        rows.append({"periodo": periodo_label, "dimension": "riesgo", "metrica": metrica, "valor": valor})
    for metrica, valor in payload["crecimiento"].items():
        rows.append({"periodo": periodo_label, "dimension": "crecimiento", "metrica": metrica, "valor": valor})
    for row in payload["sucursales"]:
        rows.append(
            {
                "periodo": periodo_label,
                "dimension": "sucursal",
                "metrica": f"{row['sucursal']}_monto_colocado",
                "valor": row["monto_colocado"],
            }
        )
        rows.append(
            {
                "periodo": periodo_label,
                "dimension": "sucursal",
                "metrica": f"{row['sucursal']}_creditos",
                "valor": row["creditos"],
            }
        )
    return rows


def _build_excel_xml_bytes(rows):
    xml_lines = [
        '<?xml version="1.0"?>',
        '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" '
        'xmlns:o="urn:schemas-microsoft-com:office:office" '
        'xmlns:x="urn:schemas-microsoft-com:office:excel" '
        'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">',
        '<Worksheet ss:Name="Consejo">',
        "<Table>",
        "<Row>"
        "<Cell><Data ss:Type=\"String\">periodo</Data></Cell>"
        "<Cell><Data ss:Type=\"String\">dimension</Data></Cell>"
        "<Cell><Data ss:Type=\"String\">metrica</Data></Cell>"
        "<Cell><Data ss:Type=\"String\">valor</Data></Cell>"
        "</Row>",
    ]

    for row in rows:
        value = row["valor"]
        value_type = "Number" if isinstance(value, (int, float, Decimal)) else "String"
        value_text = html.escape(str(value))
        xml_lines.append(
            "<Row>"
            f"<Cell><Data ss:Type=\"String\">{html.escape(str(row['periodo']))}</Data></Cell>"
            f"<Cell><Data ss:Type=\"String\">{html.escape(str(row['dimension']))}</Data></Cell>"
            f"<Cell><Data ss:Type=\"String\">{html.escape(str(row['metrica']))}</Data></Cell>"
            f"<Cell><Data ss:Type=\"{value_type}\">{value_text}</Data></Cell>"
            "</Row>"
        )

    xml_lines.extend(["</Table>", "</Worksheet>", "</Workbook>"])
    return "\n".join(xml_lines).encode("utf-8")


def _pdf_escape_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_simple_pdf(title: str, lines):
    content_lines = [
        "BT",
        "/F1 11 Tf",
        "50 790 Td",
        f"({_pdf_escape_text(title)}) Tj",
        "0 -18 Td",
    ]
    for line in lines[:42]:
        content_lines.append(f"({_pdf_escape_text(line[:110])}) Tj")
        content_lines.append("0 -14 Td")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", "replace")

    objects = [
        b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
        b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n",
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >> endobj\n",
        b"4 0 obj << /Type /Font /Subtype /Type1 /MAINFont /Helvetica >> endobj\n",
        f"5 0 obj << /Length {len(stream)} >> stream\n".encode("ascii") + stream + b"\nendstream endobj\n",
    ]

    pdf = b"%PDF-1.4\n"
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj
    xref_start = len(pdf)
    pdf += f"xref\n0 {len(offsets)}\n".encode("ascii")
    pdf += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        pdf += f"{offset:010d} 00000 n \n".encode("ascii")
    pdf += (
        f"trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode("ascii")
    )
    return pdf


class ReporteMensualRiesgoCrecimientoView(APIView):
    permission_classes = [IsAuditorOrHigher]

    def get(self, request):
        periodo = (request.query_params.get("periodo") or "").strip()
        export_format = (request.query_params.get("export") or "").strip().lower()

        start, end, periodo_label = _parse_periodo_mensual(periodo)
        if start is None:
            return Response(
                {"detail": "Periodo invalido. Usa formato YYYY-MM."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if start.month == 1:
            prev_start = date(start.year - 1, 12, 1)
        else:
            prev_start = date(start.year, start.month - 1, 1)
        prev_end = start

        creditos_mes = Credito.objects.filter(fecha_creacion__date__gte=start, fecha_creacion__date__lt=end)
        creditos_prev = Credito.objects.filter(fecha_creacion__date__gte=prev_start, fecha_creacion__date__lt=prev_end)
        colocacion_monto = float(creditos_mes.aggregate(v=Sum("monto"))["v"] or 0.0)
        colocacion_prev = float(creditos_prev.aggregate(v=Sum("monto"))["v"] or 0.0)
        crecimiento_colocacion_pct = 0.0 if colocacion_prev == 0 else ((colocacion_monto - colocacion_prev) / colocacion_prev) * 100.0

        scoring_mes = ResultadoScoring.objects.filter(fecha_creacion__date__gte=start, fecha_creacion__date__lt=end)
        total_scoring = scoring_mes.count()
        score_promedio = float(scoring_mes.aggregate(v=Avg("score"))["v"] or 0.0)
        riesgo_alto = scoring_mes.filter(riesgo=ResultadoScoring.RIESGO_ALTO).count()
        riesgo_alto_pct = 0.0 if total_scoring == 0 else (riesgo_alto / total_scoring) * 100.0

        mora_mes = ResultadoMoraTemprana.objects.filter(fecha_corte__gte=start, fecha_corte__lt=end)
        mora_alta = mora_mes.filter(alerta=ResultadoMoraTemprana.ALERTA_ALTA).count()
        mora_media = mora_mes.filter(alerta=ResultadoMoraTemprana.ALERTA_MEDIA).count()
        cartera_vencida = float(
            mora_mes.filter(alerta__in=[ResultadoMoraTemprana.ALERTA_MEDIA, ResultadoMoraTemprana.ALERTA_ALTA]).aggregate(
                v=Sum("credito__deuda_actual")
            )["v"]
            or 0.0
        )
        provisiones_estimadas = round(cartera_vencida * 0.5, 2)
        cobertura_pct = 0.0 if cartera_vencida == 0 else (provisiones_estimadas / cartera_vencida) * 100.0

        trans_mes = Transaccion.objects.filter(fecha__date__gte=start, fecha__date__lt=end)
        trans_prev = Transaccion.objects.filter(fecha__date__gte=prev_start, fecha__date__lt=prev_end)
        depositos_mes = float(trans_mes.filter(tipo=Transaccion.TIPO_DEPOSITO).aggregate(v=Sum("monto"))["v"] or 0.0)
        retiros_mes = float(trans_mes.filter(tipo=Transaccion.TIPO_RETIRO).aggregate(v=Sum("monto"))["v"] or 0.0)
        captacion_neta = depositos_mes - retiros_mes
        depositos_prev = float(trans_prev.filter(tipo=Transaccion.TIPO_DEPOSITO).aggregate(v=Sum("monto"))["v"] or 0.0)
        retiros_prev = float(trans_prev.filter(tipo=Transaccion.TIPO_RETIRO).aggregate(v=Sum("monto"))["v"] or 0.0)
        captacion_prev = depositos_prev - retiros_prev
        crecimiento_captacion_pct = 0.0 if captacion_prev == 0 else ((captacion_neta - captacion_prev) / abs(captacion_prev)) * 100.0

        socios_nuevos = Socio.objects.filter(fecha_registro__gte=start, fecha_registro__lt=end).count()

        sucursales = {"Yuriria": {"monto": 0.0, "creditos": 0}, "Cuitzeo": {"monto": 0.0, "creditos": 0}, "Santa Ana Maya": {"monto": 0.0, "creditos": 0}}
        for credito in creditos_mes.select_related("socio"):
            sucursal = _infer_sucursal_dashboard(credito.socio.direccion if credito.socio_id else "")
            if sucursal not in sucursales:
                sucursales[sucursal] = {"monto": 0.0, "creditos": 0}
            sucursales[sucursal]["monto"] += float(credito.monto)
            sucursales[sucursal]["creditos"] += 1
        sucursales_rows = [
            {"sucursal": key, "monto_colocado": round(val["monto"], 2), "creditos": val["creditos"]}
            for key, val in sucursales.items()
        ]
        sucursales_rows = sorted(sucursales_rows, key=lambda x: x["monto_colocado"], reverse=True)

        payload = {
            "periodo": periodo_label,
            "riesgo": {
                "score_promedio": round(score_promedio, 4),
                "riesgo_alto_pct": round(riesgo_alto_pct, 2),
                "alertas_mora_alta": mora_alta,
                "alertas_mora_media": mora_media,
                "cartera_vencida_estimada": round(cartera_vencida, 2),
                "provisiones_estimadas": provisiones_estimadas,
                "cobertura_pct": round(cobertura_pct, 2),
            },
            "crecimiento": {
                "socios_nuevos": socios_nuevos,
                "colocacion_monto": round(colocacion_monto, 2),
                "captacion_neta": round(captacion_neta, 2),
                "crecimiento_colocacion_pct": round(crecimiento_colocacion_pct, 2),
                "crecimiento_captacion_pct": round(crecimiento_captacion_pct, 2),
            },
            "sucursales": sucursales_rows,
        }
        export_rows = _flatten_reporte_mensual_rows(periodo_label, payload)

        if export_format == "csv":
            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = f'attachment; filename="reporte_mensual_riesgo_crecimiento_{periodo_label}.csv"'
            writer = csv.DictWriter(response, fieldnames=["periodo", "dimension", "metrica", "valor"])
            writer.writeheader()
            for row in export_rows:
                writer.writerow(row)
            return response

        if export_format in {"excel", "xls", "xlsx"}:
            response = HttpResponse(
                _build_excel_xml_bytes(export_rows),
                content_type="application/vnd.ms-excel; charset=utf-8",
            )
            response["Content-Disposition"] = (
                f'attachment; filename="reporte_consejo_riesgo_crecimiento_{periodo_label}.xls"'
            )
            return response

        if export_format == "pdf":
            pdf_lines = [f"{row['dimension']} | {row['metrica']} | {row['valor']}" for row in export_rows]
            response = HttpResponse(
                _build_simple_pdf(f"Reporte Consejo {periodo_label}", pdf_lines),
                content_type="application/pdf",
            )
            response["Content-Disposition"] = (
                f'attachment; filename="reporte_consejo_riesgo_crecimiento_{periodo_label}.pdf"'
            )
            return response

        return Response(payload)


def _prioridad_alerta_mora(alerta: str) -> str:
    if alerta == ResultadoMoraTemprana.ALERTA_ALTA:
        return "critica"
    if alerta == ResultadoMoraTemprana.ALERTA_MEDIA:
        return "alta"
    return "media"


def _accion_sugerida_alerta(alerta: str, prob_90d: float) -> str:
    if alerta == ResultadoMoraTemprana.ALERTA_ALTA or prob_90d >= 0.80:
        return "contacto_inmediato_24h"
    if alerta == ResultadoMoraTemprana.ALERTA_MEDIA:
        return "seguimiento_72h"
    return "monitoreo_preventivo"


class AlertasTempranasOperativasView(APIView):
    permission_classes = [IsAuditorOrHigher]

    def get(self, request):
        alerta_filter = (request.query_params.get("alerta") or "").strip().lower()
        sucursal_filter = (request.query_params.get("sucursal") or "").strip()
        prioridad_filter = (request.query_params.get("prioridad") or "").strip().lower()
        q_filter = (request.query_params.get("q") or "").strip().lower()
        export_format = (request.query_params.get("export") or "").strip().lower()
        fecha_desde = (request.query_params.get("fecha_desde") or "").strip()
        fecha_hasta = (request.query_params.get("fecha_hasta") or "").strip()
        limit_raw = (request.query_params.get("limit") or "200").strip()
        try:
            limit = max(1, min(1000, int(limit_raw)))
        except ValueError:
            limit = 200

        queryset = ResultadoMoraTemprana.objects.select_related("socio", "credito").order_by("-fecha_creacion", "-id")
        if fecha_desde:
            queryset = queryset.filter(fecha_corte__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_corte__lte=fecha_hasta)
        if alerta_filter in {"baja", "media", "alta"}:
            queryset = queryset.filter(alerta=alerta_filter)

        items = []
        for row in queryset[: limit * 3]:
            socio = row.socio
            credito = row.credito
            if socio is None or credito is None:
                continue

            sucursal = _infer_sucursal_dashboard(socio.direccion)
            prioridad = _prioridad_alerta_mora(row.alerta)
            prob_90d = float(row.prob_mora_90d)
            item = {
                "socio_id": socio.id,
                "socio_nombre": socio.nombre,
                "credito_id": credito.id,
                "sucursal": sucursal,
                "alerta": row.alerta,
                "prioridad": prioridad,
                "prob_mora_30d": round(float(row.prob_mora_30d), 4),
                "prob_mora_60d": round(float(row.prob_mora_60d), 4),
                "prob_mora_90d": round(prob_90d, 4),
                "deuda_actual": round(float(credito.deuda_actual), 2),
                "accion_sugerida": _accion_sugerida_alerta(row.alerta, prob_90d),
                "fecha_corte": row.fecha_corte,
                "fecha_generacion": row.fecha_creacion,
            }

            if sucursal_filter and item["sucursal"] != sucursal_filter:
                continue
            if prioridad_filter and item["prioridad"] != prioridad_filter:
                continue
            if q_filter and q_filter not in item["socio_nombre"].lower() and q_filter not in str(item["credito_id"]):
                continue
            items.append(item)
            if len(items) >= limit:
                break

        priority_rank = {"critica": 3, "alta": 2, "media": 1}
        items = sorted(
            items,
            key=lambda x: (priority_rank.get(x["prioridad"], 0), x["prob_mora_90d"], x["deuda_actual"]),
            reverse=True,
        )

        if export_format == "csv":
            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = 'attachment; filename="alertas_tempranas_operativas.csv"'
            writer = csv.DictWriter(
                response,
                fieldnames=[
                    "socio_id",
                    "socio_nombre",
                    "credito_id",
                    "sucursal",
                    "alerta",
                    "prioridad",
                    "prob_mora_30d",
                    "prob_mora_60d",
                    "prob_mora_90d",
                    "deuda_actual",
                    "accion_sugerida",
                    "fecha_corte",
                    "fecha_generacion",
                ],
            )
            writer.writeheader()
            for row in items:
                writer.writerow(row)
            return response

        resumen = {
            "total_alertas": len(items),
            "criticas": sum(1 for item in items if item["prioridad"] == "critica"),
            "altas": sum(1 for item in items if item["prioridad"] == "alta"),
            "medias": sum(1 for item in items if item["prioridad"] == "media"),
            "deuda_total_expuesta": round(sum(item["deuda_actual"] for item in items), 2),
        }
        return Response({"resumen": resumen, "items": items})


def _clamp(value: float, min_value: float = 0.0, max_value: float = 1.0) -> float:
    return max(min_value, min(max_value, value))


def _calcular_probabilidades_mora(credito: Credito, fecha_corte):
    cuota_estimada = float(credito.monto) / max(int(credito.plazo), 1)
    pagos_90d = (
        credito.historial_pagos.filter(fecha__gte=fecha_corte - timedelta(days=90), fecha__lte=fecha_corte).aggregate(
            total=Sum("monto")
        )["total"]
        or Decimal("0")
    )
    pagos_90d_value = float(pagos_90d)
    ratio_pago_90d = _clamp(pagos_90d_value / max(cuota_estimada * 3.0, 1.0))
    deuda_ingreso_ratio = _clamp(float(credito.deuda_actual) / max(float(credito.ingreso_mensual), 1.0))
    penalizacion_antiguedad = _clamp(1.0 - (float(credito.antiguedad_meses) / 24.0))
    MAIN = (
        0.10
        + (0.55 * deuda_ingreso_ratio)
        + (0.35 * (1.0 - ratio_pago_90d))
        + (0.15 * penalizacion_antiguedad)
    )
    prob_60d = _clamp(MAIN)
    prob_30d = _clamp(MAIN * 0.85)
    prob_90d = _clamp(MAIN * 1.12)
    alerta = (
        ResultadoMoraTemprana.ALERTA_BAJA
        if prob_90d < 0.35
        else ResultadoMoraTemprana.ALERTA_MEDIA if prob_90d < 0.65 else ResultadoMoraTemprana.ALERTA_ALTA
    )
    return {
        "cuota_estimada": cuota_estimada,
        "pagos_90d": pagos_90d_value,
        "ratio_pago_90d": ratio_pago_90d,
        "deuda_ingreso_ratio": deuda_ingreso_ratio,
        "prob_mora_30d": prob_30d,
        "prob_mora_60d": prob_60d,
        "prob_mora_90d": prob_90d,
        "alerta": alerta,
    }


class ResultadoMoraTempranaListView(generics.ListAPIView):
    serializer_class = ResultadoMoraTempranaSerializer
    permission_classes = [IsAuditorOrHigher]

    def get_queryset(self):
        queryset = ResultadoMoraTemprana.objects.select_related("credito", "socio").all()
        socio = self.request.query_params.get("socio")
        credito = self.request.query_params.get("credito")
        alerta = self.request.query_params.get("alerta")
        fuente = self.request.query_params.get("fuente")
        fecha_corte = self.request.query_params.get("fecha_corte")
        model_version = self.request.query_params.get("model_version")
        if socio:
            queryset = queryset.filter(socio_id=socio)
        if credito:
            queryset = queryset.filter(credito_id=credito)
        if alerta:
            queryset = queryset.filter(alerta=alerta)
        if fuente:
            queryset = queryset.filter(fuente=fuente)
        if fecha_corte:
            queryset = queryset.filter(fecha_corte=fecha_corte)
        if model_version:
            queryset = queryset.filter(model_version=model_version)
        return queryset


class MoraTempranaEvaluateView(APIView):
    permission_classes = [IsAuditorOrHigher]

    def post(self, request):
        serializer = MoraTempranaEvaluateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        credito = Credito.objects.select_related("socio").filter(pk=data["credito"]).first()
        if not credito:
            return Response({"detail": "Credito no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        if not credito.socio_id:
            return Response({"detail": "El credito no tiene socio asociado."}, status=status.HTTP_400_BAD_REQUEST)

        fecha_corte = data.get("fecha_corte") or timezone.localdate()
        metrics = _calcular_probabilidades_mora(credito, fecha_corte)
        model_version = data.get("model_version") or "mora_temprana_v1"
        persist = data.get("persist", True)
        resultado_id = None
        request_id = str(uuid.uuid4())

        if persist:
            defaults = {
                "socio": credito.socio,
                "cuota_estimada": metrics["cuota_estimada"],
                "pagos_90d": metrics["pagos_90d"],
                "ratio_pago_90d": metrics["ratio_pago_90d"],
                "deuda_ingreso_ratio": metrics["deuda_ingreso_ratio"],
                "prob_mora_30d": metrics["prob_mora_30d"],
                "prob_mora_60d": metrics["prob_mora_60d"],
                "prob_mora_90d": metrics["prob_mora_90d"],
                "alerta": metrics["alerta"],
                "fuente": ResultadoMoraTemprana.FUENTE_ONLINE,
            }
            resultado, _created = ResultadoMoraTemprana.objects.update_or_create(
                credito=credito,
                fecha_corte=fecha_corte,
                model_version=model_version,
                fuente=ResultadoMoraTemprana.FUENTE_ONLINE,
                defaults=defaults,
            )
            resultado_id = resultado.id
            request_id = str(resultado.request_id)

        return Response(
            {
                "request_id": request_id,
                "credito": credito.id,
                "socio": credito.socio_id,
                "fecha_corte": str(fecha_corte),
                "model_version": model_version,
                "prob_mora_30d": round(metrics["prob_mora_30d"], 4),
                "prob_mora_60d": round(metrics["prob_mora_60d"], 4),
                "prob_mora_90d": round(metrics["prob_mora_90d"], 4),
                "alerta": metrics["alerta"],
                "persisted": bool(persist),
                "resultado_id": resultado_id,
            }
        )


class MoraTempranaResumenView(APIView):
    permission_classes = [IsAuditorOrHigher]

    def get(self, request):
        queryset = ResultadoMoraTemprana.objects.all()
        fecha_corte = request.query_params.get("fecha_corte")
        model_version = request.query_params.get("model_version")
        fuente = request.query_params.get("fuente")
        if fecha_corte:
            queryset = queryset.filter(fecha_corte=fecha_corte)
        if model_version:
            queryset = queryset.filter(model_version=model_version)
        if fuente:
            queryset = queryset.filter(fuente=fuente)

        MAIN = queryset.aggregate(
            total=Count("id"),
            prob_30d_promedio=Avg("prob_mora_30d"),
            prob_60d_promedio=Avg("prob_mora_60d"),
            prob_90d_promedio=Avg("prob_mora_90d"),
        )
        por_alerta = {item["alerta"]: item["total"] for item in queryset.values("alerta").annotate(total=Count("id"))}
        return Response(
            {
                "total_alertas": MAIN["total"] or 0,
                "prob_30d_promedio": float(MAIN["prob_30d_promedio"] or 0),
                "prob_60d_promedio": float(MAIN["prob_60d_promedio"] or 0),
                "prob_90d_promedio": float(MAIN["prob_90d_promedio"] or 0),
                "por_alerta": {
                    "baja": por_alerta.get("baja", 0),
                    "media": por_alerta.get("media", 0),
                    "alta": por_alerta.get("alta", 0),
                },
            }
        )


class ResultadoSegmentacionSocioListView(generics.ListAPIView):
    serializer_class = ResultadoSegmentacionSocioSerializer
    permission_classes = [IsAuditorOrHigher]

    def get_queryset(self):
        queryset = ResultadoSegmentacionSocio.objects.select_related("socio").all()
        socio = self.request.query_params.get("socio")
        segmento = self.request.query_params.get("segmento")
        fecha_ejecucion = self.request.query_params.get("fecha_ejecucion")
        model_version = self.request.query_params.get("model_version")
        if socio:
            queryset = queryset.filter(socio_id=socio)
        if segmento:
            queryset = queryset.filter(segmento=segmento)
        if fecha_ejecucion:
            queryset = queryset.filter(fecha_ejecucion=fecha_ejecucion)
        if model_version:
            queryset = queryset.filter(model_version=model_version)
        return queryset


class SegmentacionSociosPerfilesView(APIView):
    permission_classes = [IsAuditorOrHigher]

    def get(self, request):
        queryset = ResultadoSegmentacionSocio.objects.all()
        fecha_ejecucion = request.query_params.get("fecha_ejecucion")
        model_version = request.query_params.get("model_version")
        if fecha_ejecucion:
            queryset = queryset.filter(fecha_ejecucion=fecha_ejecucion)
        if model_version:
            queryset = queryset.filter(model_version=model_version)

        total = queryset.count()
        perfiles = []
        for segmento in (
            Socio.SEGMENTO_HORMIGA,
            Socio.SEGMENTO_GRAN_AHORRADOR,
            Socio.SEGMENTO_INACTIVO,
        ):
            MAIN = queryset.filter(segmento=segmento)
            agg = MAIN.aggregate(
                socios=Count("id"),
                saldo_promedio=Avg("saldo_total"),
                mov_total_promedio=Avg("total_movimientos"),
                mov_count_promedio=Avg("cantidad_movimientos"),
                creditos_promedio=Avg("total_creditos"),
            )
            perfiles.append(
                {
                    "segmento": segmento,
                    "socios": agg["socios"] or 0,
                    "cobertura": 0.0 if total == 0 else round(((agg["socios"] or 0) / total) * 100.0, 2),
                    "saldo_promedio": float(agg["saldo_promedio"] or 0),
                    "mov_total_promedio": float(agg["mov_total_promedio"] or 0),
                    "mov_count_promedio": float(agg["mov_count_promedio"] or 0),
                    "creditos_promedio": float(agg["creditos_promedio"] or 0),
                }
            )

        return Response(
            {
                "total_socios_segmentados": total,
                "fecha_ejecucion": fecha_ejecucion,
                "model_version": model_version,
                "perfiles": perfiles,
            }
        )


class SegmentacionInteligenteRunView(APIView):
    permission_classes = [IsAdministradorOrHigher]

    def post(self, request):
        serializer = SegmentacionInteligenteRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        metodo = data.get("metodo", "reglas")
        clusters = int(data.get("clusters", 5))

        project_root = Path(__file__).resolve().parents[4]
        default_report_csv = project_root / "docs" / "mineria" / "customer_intelligence" / "01_segmentacion_inteligente_resumen.csv"
        default_dataset_csv = project_root / "docs" / "mineria" / "customer_intelligence" / "01_segmentacion_inteligente_socios.csv"
        default_report_md = project_root / "docs" / "mineria" / "customer_intelligence" / "01_segmentacion_inteligente.md"
        default_thresholds_json = (
            project_root / "docs" / "mineria" / "customer_intelligence" / "02_umbrales_segmentacion_oficial_v1.json"
        )

        report_csv = data.get("report_csv") or str(default_report_csv)
        dataset_csv = data.get("dataset_csv") or str(default_dataset_csv)
        report_md = data.get("report_md") or str(default_report_md)
        thresholds_json = data.get("thresholds_json") or str(default_thresholds_json)
        thresholds_version = data.get("thresholds_version") or ""

        call_command(
            "segmentacion_inteligente_socios_1_4",
            metodo=metodo,
            clusters=clusters,
            thresholds_json=thresholds_json,
            thresholds_version=thresholds_version,
            report_csv=report_csv,
            dataset_csv=dataset_csv,
            report_md=report_md,
        )

        return Response(
            {
                "status": "ok",
                "metodo": metodo,
                "clusters": clusters,
                "thresholds_json": thresholds_json,
                "thresholds_version": thresholds_version,
                "report_csv": report_csv,
                "dataset_csv": dataset_csv,
                "report_md": report_md,
            }
        )


class ReglasAsociacionListView(generics.ListAPIView):
    serializer_class = ReglaAsociacionProductoSerializer
    permission_classes = [IsAuditorOrHigher]

    def get_queryset(self):
        queryset = ReglaAsociacionProducto.objects.all()
        fecha_ejecucion = self.request.query_params.get("fecha_ejecucion")
        antecedente = self.request.query_params.get("antecedente")
        consecuente = self.request.query_params.get("consecuente")
        vigente = self.request.query_params.get("vigente")
        model_version = self.request.query_params.get("model_version")
        min_lift = self.request.query_params.get("min_lift")

        if fecha_ejecucion:
            queryset = queryset.filter(fecha_ejecucion=fecha_ejecucion)
        if antecedente:
            queryset = queryset.filter(antecedente=antecedente)
        if consecuente:
            queryset = queryset.filter(consecuente=consecuente)
        if vigente in {"true", "false"}:
            queryset = queryset.filter(vigente=(vigente == "true"))
        if model_version:
            queryset = queryset.filter(model_version=model_version)
        if min_lift:
            try:
                queryset = queryset.filter(lift__gte=float(min_lift))
            except ValueError:
                pass
        return queryset


class ReglasAsociacionResumenView(APIView):
    permission_classes = [IsAuditorOrHigher]

    def get(self, request):
        queryset = ReglaAsociacionProducto.objects.all()
        fecha_ejecucion = request.query_params.get("fecha_ejecucion")
        model_version = request.query_params.get("model_version")
        vigente = request.query_params.get("vigente")
        if fecha_ejecucion:
            queryset = queryset.filter(fecha_ejecucion=fecha_ejecucion)
        if model_version:
            queryset = queryset.filter(model_version=model_version)
        if vigente in {"true", "false"}:
            queryset = queryset.filter(vigente=(vigente == "true"))

        MAIN = queryset.aggregate(
            total=Count("id"),
            soporte_promedio=Avg("soporte"),
            confianza_promedio=Avg("confianza"),
            lift_promedio=Avg("lift"),
        )
        top = list(
            queryset.order_by("-lift", "-confianza", "-soporte").values(
                "antecedente",
                "consecuente",
                "soporte",
                "confianza",
                "lift",
                "oportunidad_comercial",
            )[:5]
        )
        return Response(
            {
                "total_reglas": MAIN["total"] or 0,
                "soporte_promedio": float(MAIN["soporte_promedio"] or 0),
                "confianza_promedio": float(MAIN["confianza_promedio"] or 0),
                "lift_promedio": float(MAIN["lift_promedio"] or 0),
                "top_reglas": top,
            }
        )


class SubmodulosIntegracionResumenView(APIView):
    permission_classes = [IsAuditorOrHigher]

    def get(self, request):
        scoring_qs = ResultadoScoring.objects.all()
        mora_qs = ResultadoMoraTemprana.objects.all()
        seg_qs = ResultadoSegmentacionSocio.objects.all()
        reglas_qs = ReglaAsociacionProducto.objects.filter(vigente=True)

        scoring_total = scoring_qs.count()
        mora_total = mora_qs.count()
        seg_total = seg_qs.count()
        reglas_total = reglas_qs.count()

        scoring_socios = set(scoring_qs.exclude(socio_id__isnull=True).values_list("socio_id", flat=True))
        mora_socios = set(mora_qs.values_list("socio_id", flat=True))
        seg_socios = set(seg_qs.values_list("socio_id", flat=True))

        universo = scoring_socios | mora_socios | seg_socios
        socios_con_todo = scoring_socios & mora_socios & seg_socios
        cobertura_consolidada = 0.0 if len(universo) == 0 else round((len(socios_con_todo) / len(universo)) * 100.0, 2)

        return Response(
            {
                "submodulos": {
                    "scoring": {
                        "total_registros": scoring_total,
                        "model_version": (scoring_qs.order_by("-id").values_list("model_version", flat=True).first() or "weighted_score_v1"),
                    },
                    "mora_temprana": {
                        "total_registros": mora_total,
                        "model_version": (mora_qs.order_by("-id").values_list("model_version", flat=True).first() or "mora_temprana_v1"),
                    },
                    "segmentacion_socios": {
                        "total_registros": seg_total,
                        "model_version": (seg_qs.order_by("-id").values_list("model_version", flat=True).first() or "segmentacion_socios_v1"),
                    },
                    "reglas_asociacion": {
                        "total_registros": reglas_total,
                        "model_version": (
                            reglas_qs.order_by("-id").values_list("model_version", flat=True).first() or "asociacion_productos_v1"
                        ),
                    },
                },
                "consistencia": {
                    "socios_universo": len(universo),
                    "socios_con_scoring_mora_segmentacion": len(socios_con_todo),
                    "cobertura_consolidada_pct": cobertura_consolidada,
                },
                "formato_salida": {
                    "version": "integracion_submodulos_v1",
                    "campos_estandar": [
                        "model_version",
                        "fecha_creacion",
                        "total_registros",
                    ],
                },
            }
        )


def _infer_sucursal_dashboard(direccion: str) -> str:
    text = (direccion or "").lower()
    if "cuitzeo" in text:
        return "Cuitzeo"
    if "santa ana maya" in text:
        return "Santa Ana Maya"
    if "yuriria" in text:
        return "Yuriria"
    return "Yuriria"


def _dashboard_status_path() -> Path:
    return Path(__file__).resolve().parents[4] / "docs" / "mineria" / "dashboards" / "08_estado_actualizacion.json"


def _dashboard_actualizacion_info():
    status_file = _dashboard_status_path()
    if status_file.exists():
        try:
            data = json.loads(status_file.read_text(encoding="utf-8"))
            ultima = data.get("ultima_actualizacion_utc")
            if ultima:
                return {
                    "ultima_actualizacion_utc": ultima,
                    "fuente": "archivo_estado",
                }
        except (json.JSONDecodeError, OSError, ValueError):
            pass

    max_scoring = ResultadoScoring.objects.aggregate(m=Max("fecha_creacion"))["m"]
    max_mora = ResultadoMoraTemprana.objects.aggregate(m=Max("fecha_creacion"))["m"]
    max_alerta = AlertaMonitoreo.objects.aggregate(m=Max("fecha_evento"))["m"]
    candidates = [d for d in [max_scoring, max_mora, max_alerta] if d]
    if candidates:
        latest = max(candidates)
        return {
            "ultima_actualizacion_utc": latest.isoformat(),
            "fuente": "fallback_datos",
        }
    return {
        "ultima_actualizacion_utc": None,
        "fuente": "sin_datos",
    }


def _dashboard_access_scope(role: str):
    if role in {UserProfile.ROL_ADMINISTRADOR, UserProfile.ROL_SUPERADMIN}:
        return {"vista": "consejo_gerencia", "drilldown_habilitado": True}
    if role == UserProfile.ROL_JEFE_DEPARTAMENTO:
        return {"vista": "jefatura", "drilldown_habilitado": True}
    return {"vista": "ejecutivo", "drilldown_habilitado": False}


def _apply_role_scope_to_payload(payload: dict, role: str):
    scope = _dashboard_access_scope(role)
    vista = scope["vista"]

    if vista == "jefatura":
        riesgo = payload.get("riesgo", {})
        if isinstance(riesgo, dict):
            riesgo.pop("castigos_estimados", None)
        tendencias = payload.get("tendencias", {})
        if isinstance(tendencias, dict):
            trimestral = tendencias.get("trimestral", {})
            if isinstance(trimestral, dict):
                trimestral.pop("cobranza_eficiencia_pct", None)

    if vista == "ejecutivo":
        payload.pop("riesgo", None)
        payload.pop("eficiencia_cobranza", None)
        coloc = payload.get("colocacion", {})
        if isinstance(coloc, dict):
            coloc.pop("embudo_rechazados", None)
        payload["sucursales"] = [
            {
                "ranking": row.get("ranking"),
                "sucursal": row.get("sucursal"),
                "colocacion_30d": row.get("colocacion_30d"),
            }
            for row in payload.get("sucursales", [])
        ]
        payload.pop("drilldown", None)
        tendencias = payload.get("tendencias", {})
        if isinstance(tendencias, dict):
            mensual = tendencias.get("mensual", {})
            trimestral = tendencias.get("trimestral", {})
            if isinstance(mensual, dict):
                mensual.pop("riesgo_cobertura_pct", None)
                mensual.pop("cobranza_eficiencia_pct", None)
            if isinstance(trimestral, dict):
                trimestral.pop("riesgo_cobertura_pct", None)
                trimestral.pop("cobranza_eficiencia_pct", None)

    payload["acceso"] = {
        "rol": role,
        "vista": scope["vista"],
        "drilldown_habilitado": scope["drilldown_habilitado"],
    }
    return payload


def _build_dashboards_1_8_payload(sucursal_detalle: str = "", include_drilldown: bool = False):
    hoy = timezone.localdate()
    d30 = hoy - timedelta(days=30)
    d90 = hoy - timedelta(days=90)

    mora_media_alta = ResultadoMoraTemprana.objects.filter(
        alerta__in=[ResultadoMoraTemprana.ALERTA_MEDIA, ResultadoMoraTemprana.ALERTA_ALTA]
    )

    cartera_total = float(Credito.objects.aggregate(v=Sum("monto"))["v"] or 0.0)
    cartera_vencida = float(mora_media_alta.aggregate(v=Sum("credito__deuda_actual"))["v"] or 0.0)
    cartera_vigente = max(0.0, cartera_total - cartera_vencida)
    imor = 0.0 if cartera_total <= 0 else (cartera_vencida / cartera_total) * 100.0

    vintage = []
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
        mora_pct = 0.0 if total == 0 else (con_mora / total) * 100.0
        vintage.append(
            {
                "vintage": label,
                "creditos": total,
                "creditos_mora": con_mora,
                "mora_pct": round(mora_pct, 2),
            }
        )

    meta_colocacion = 100000.0
    colocacion_real = float(Credito.objects.filter(fecha_creacion__date__gte=d30).aggregate(v=Sum("monto"))["v"] or 0.0)
    cumplimiento_meta_pct = (colocacion_real / meta_colocacion * 100.0) if meta_colocacion else 0.0
    solicitados = Credito.objects.filter(fecha_creacion__date__gte=d30).count()
    aprobados = Credito.objects.filter(fecha_creacion__date__gte=d30, estado=Credito.ESTADO_APROBADO).count()
    rechazados = Credito.objects.filter(fecha_creacion__date__gte=d30, estado=Credito.ESTADO_RECHAZADO).count()
    tiempos = []
    for row in ResultadoScoring.objects.select_related("credito").filter(credito__isnull=False):
        delta = (row.fecha_creacion - row.credito.fecha_creacion).total_seconds() / 3600.0
        if delta >= 0:
            tiempos.append(delta)
    tiempo_respuesta_h = 0.0 if not tiempos else sum(tiempos) / len(tiempos)

    depositos_30d = float(
        Transaccion.objects.filter(fecha__date__gte=d30, tipo=Transaccion.TIPO_DEPOSITO).aggregate(v=Sum("monto"))["v"] or 0.0
    )
    retiros_30d = float(
        Transaccion.objects.filter(fecha__date__gte=d30, tipo=Transaccion.TIPO_RETIRO).aggregate(v=Sum("monto"))["v"] or 0.0
    )
    crecimiento_neto_30d = depositos_30d - retiros_30d
    saldos = [float(v) for v in Cuenta.objects.values_list("saldo", flat=True)]
    cv = 0.0
    if saldos and sum(saldos) > 0:
        mean = sum(saldos) / len(saldos)
        cv = pstdev(saldos) / mean if mean > 0 else 0.0
    estabilidad_ahorro_pct = max(0.0, min(100.0, (1.0 - cv) * 100.0))

    pagos_90d = float(HistorialPago.objects.filter(fecha__gte=d90).aggregate(v=Sum("monto"))["v"] or 0.0)
    cobertura_pct = 0.0 if cartera_vencida <= 0 else (pagos_90d / cartera_vencida) * 100.0
    provisiones_estimadas = cartera_vencida * 0.35
    castigos_estimados = (
        float(mora_media_alta.filter(prob_mora_90d__gte=0.85).aggregate(v=Sum("credito__deuda_actual"))["v"] or 0.0) * 0.20
    )

    socios_all = list(Socio.objects.all().only("id", "nombre", "direccion"))
    socio_to_sucursal = {s.id: _infer_sucursal_dashboard(s.direccion) for s in socios_all}
    sucursal_to_socios = {
        "Yuriria": [s.id for s in socios_all if socio_to_sucursal[s.id] == "Yuriria"],
        "Cuitzeo": [s.id for s in socios_all if socio_to_sucursal[s.id] == "Cuitzeo"],
        "Santa Ana Maya": [s.id for s in socios_all if socio_to_sucursal[s.id] == "Santa Ana Maya"],
    }

    sucursales = []
    for suc in ["Yuriria", "Cuitzeo", "Santa Ana Maya"]:
        socios = sucursal_to_socios.get(suc, [])
        coloc = float(Credito.objects.filter(socio_id__in=socios, fecha_creacion__date__gte=d30).aggregate(v=Sum("monto"))["v"] or 0.0)
        mora_alertas = mora_media_alta.filter(socio_id__in=socios).count()
        sucursales.append(
            {
                "sucursal": suc,
                "colocacion_30d": round(coloc, 2),
                "alertas_mora": mora_alertas,
            }
        )
    sucursales = sorted(sucursales, key=lambda x: x["colocacion_30d"], reverse=True)
    for idx, row in enumerate(sucursales, start=1):
        row["ranking"] = idx

    gestiones_total = mora_media_alta.count()
    gestiones_con_recuperacion = mora_media_alta.filter(ratio_pago_90d__gte=0.60).count()
    eficiencia_cobranza_pct = 0.0 if gestiones_total == 0 else (gestiones_con_recuperacion / gestiones_total) * 100.0
    recuperacion_por_gestion = 0.0 if gestiones_total == 0 else (pagos_90d / gestiones_total)

    # Tendencias historicas (mensual y trimestral).
    MAIN_month = hoy.replace(day=1)
    month_keys = []
    for i in range(5, -1, -1):
        month_dt = (MAIN_month - timedelta(days=32 * i)).replace(day=1)
        key = month_dt.strftime("%Y-%m")
        if key not in month_keys:
            month_keys.append(key)

    coloc_mes = defaultdict(float)
    for row in Credito.objects.filter(fecha_creacion__date__gte=(hoy - timedelta(days=220))).values("fecha_creacion", "monto"):
        key = row["fecha_creacion"].strftime("%Y-%m")
        coloc_mes[key] += float(row["monto"] or 0.0)

    capt_mes_dep = defaultdict(float)
    capt_mes_ret = defaultdict(float)
    for row in Transaccion.objects.filter(fecha__date__gte=(hoy - timedelta(days=220))).values("fecha", "monto", "tipo"):
        key = row["fecha"].strftime("%Y-%m")
        amount = float(row["monto"] or 0.0)
        if row["tipo"] == Transaccion.TIPO_DEPOSITO:
            capt_mes_dep[key] += amount
        elif row["tipo"] == Transaccion.TIPO_RETIRO:
            capt_mes_ret[key] += amount

    imor_mes_total = defaultdict(float)
    for row in Credito.objects.filter(fecha_creacion__date__gte=(hoy - timedelta(days=220))).values("fecha_creacion", "monto"):
        key = row["fecha_creacion"].strftime("%Y-%m")
        imor_mes_total[key] += float(row["monto"] or 0.0)
    imor_mes_vencida = defaultdict(float)
    for row in mora_media_alta.filter(fecha_creacion__date__gte=(hoy - timedelta(days=220))).values("fecha_creacion", "credito__deuda_actual"):
        key = row["fecha_creacion"].strftime("%Y-%m")
        imor_mes_vencida[key] += float(row["credito__deuda_actual"] or 0.0)

    cob_mes_pagos = defaultdict(float)
    for row in HistorialPago.objects.filter(fecha__gte=(hoy - timedelta(days=220))).values("fecha", "monto"):
        key = row["fecha"].strftime("%Y-%m")
        cob_mes_pagos[key] += float(row["monto"] or 0.0)
    cob_mes_vencida = defaultdict(float)
    for row in mora_media_alta.filter(fecha_creacion__date__gte=(hoy - timedelta(days=220))).values("fecha_creacion", "credito__deuda_actual"):
        key = row["fecha_creacion"].strftime("%Y-%m")
        cob_mes_vencida[key] += float(row["credito__deuda_actual"] or 0.0)

    cobranza_mes_total = defaultdict(int)
    cobranza_mes_rec = defaultdict(int)
    for row in mora_media_alta.filter(fecha_creacion__date__gte=(hoy - timedelta(days=220))).values("fecha_creacion", "ratio_pago_90d"):
        key = row["fecha_creacion"].strftime("%Y-%m")
        cobranza_mes_total[key] += 1
        if float(row["ratio_pago_90d"] or 0.0) >= 0.60:
            cobranza_mes_rec[key] += 1

    suc_mes = {
        "Yuriria": defaultdict(float),
        "Cuitzeo": defaultdict(float),
        "Santa Ana Maya": defaultdict(float),
    }
    for row in Credito.objects.filter(fecha_creacion__date__gte=(hoy - timedelta(days=220))).select_related("socio").only("fecha_creacion", "monto", "socio__direccion"):
        key = row.fecha_creacion.strftime("%Y-%m")
        suc = _infer_sucursal_dashboard(row.socio.direccion if row.socio_id else "")
        if suc in suc_mes:
            suc_mes[suc][key] += float(row.monto or 0.0)

    salud_trend = []
    coloc_trend = []
    capt_trend = []
    riesgo_trend = []
    cobranza_trend = []
    suc_trend = []
    for key in month_keys:
        total = imor_mes_total[key]
        vencida = imor_mes_vencida[key]
        imor_key = 0.0 if total <= 0 else (vencida / total) * 100.0
        salud_trend.append({"periodo": key, "valor": round(imor_key, 2)})

        coloc_trend.append({"periodo": key, "valor": round(coloc_mes[key], 2)})

        neto = capt_mes_dep[key] - capt_mes_ret[key]
        capt_trend.append({"periodo": key, "valor": round(neto, 2)})

        cobertura_key = 0.0 if cob_mes_vencida[key] <= 0 else (cob_mes_pagos[key] / cob_mes_vencida[key]) * 100.0
        riesgo_trend.append({"periodo": key, "valor": round(cobertura_key, 2)})

        cob_total = cobranza_mes_total[key]
        cob_ef = 0.0 if cob_total == 0 else (cobranza_mes_rec[key] / cob_total) * 100.0
        cobranza_trend.append({"periodo": key, "valor": round(cob_ef, 2)})

        suc_trend.append(
            {
                "periodo": key,
                "yuriria": round(suc_mes["Yuriria"][key], 2),
                "cuitzeo": round(suc_mes["Cuitzeo"][key], 2),
                "santa_ana_maya": round(suc_mes["Santa Ana Maya"][key], 2),
            }
        )

    def _quarterly(series):
        grouped = defaultdict(list)
        for row in series:
            y, m = row["periodo"].split("-")
            q = ((int(m) - 1) // 3) + 1
            grouped[f"{y}-Q{q}"].append(float(row["valor"]))
        out = []
        for qkey in sorted(grouped.keys()):
            vals = grouped[qkey]
            out.append({"periodo": qkey, "valor": round(sum(vals) / len(vals), 2)})
        return out[-4:]

    payload = {
        "salud_cartera": {
            "cartera_total": round(cartera_total, 2),
            "cartera_vigente": round(cartera_vigente, 2),
            "cartera_vencida_estimada": round(cartera_vencida, 2),
            "imor_pct": round(imor, 2),
            "meta_imor_pct": 15.0,
            "vintage": vintage,
        },
        "colocacion": {
            "meta_colocacion_30d": round(meta_colocacion, 2),
            "colocacion_real_30d": round(colocacion_real, 2),
            "cumplimiento_meta_pct": round(cumplimiento_meta_pct, 2),
            "embudo_solicitados": solicitados,
            "embudo_aprobados": aprobados,
            "embudo_rechazados": rechazados,
            "tiempo_respuesta_promedio_h": round(tiempo_respuesta_h, 2),
        },
        "captacion": {
            "depositos_30d": round(depositos_30d, 2),
            "retiros_30d": round(retiros_30d, 2),
            "crecimiento_neto_30d": round(crecimiento_neto_30d, 2),
            "estabilidad_ahorro_pct": round(estabilidad_ahorro_pct, 2),
            "meta_estabilidad_ahorro_pct": 60.0,
        },
        "riesgo": {
            "cobertura_pct": round(cobertura_pct, 2),
            "meta_cobertura_pct": 50.0,
            "provisiones_estimadas": round(provisiones_estimadas, 2),
            "castigos_estimados": round(castigos_estimados, 2),
        },
        "sucursales": sucursales,
        "eficiencia_cobranza": {
            "gestiones_total": gestiones_total,
            "gestiones_con_recuperacion": gestiones_con_recuperacion,
            "eficiencia_cobranza_pct": round(eficiencia_cobranza_pct, 2),
            "meta_eficiencia_cobranza_pct": 45.0,
            "recuperacion_por_gestion": round(recuperacion_por_gestion, 2),
        },
        "tendencias": {
            "mensual": {
                "salud_cartera_imor_pct": salud_trend,
                "colocacion_monto": coloc_trend,
                "captacion_neto": capt_trend,
                "riesgo_cobertura_pct": riesgo_trend,
                "cobranza_eficiencia_pct": cobranza_trend,
                "sucursales_colocacion": suc_trend,
            },
            "trimestral": {
                "salud_cartera_imor_pct": _quarterly(salud_trend),
                "colocacion_monto": _quarterly(coloc_trend),
                "captacion_neto": _quarterly(capt_trend),
                "riesgo_cobertura_pct": _quarterly(riesgo_trend),
                "cobranza_eficiencia_pct": _quarterly(cobranza_trend),
            },
        },
    }

    if include_drilldown and sucursal_detalle:
        sucursal_objetivo = sucursal_detalle.strip()
        socio_ids = sucursal_to_socios.get(sucursal_objetivo, [])
        creditos_qs = Credito.objects.filter(socio_id__in=socio_ids).select_related("socio").order_by("-fecha_creacion")[:25]
        alertas_qs = mora_media_alta.filter(socio_id__in=socio_ids).select_related("socio", "credito").order_by("-fecha_creacion")[:25]
        payload["drilldown"] = {
            "sucursal": sucursal_objetivo,
            "total_socios": len(socio_ids),
            "creditos_recientes": [
                {
                    "credito_id": c.id,
                    "socio_id": c.socio_id,
                    "socio_nombre": c.socio.nombre if c.socio_id else "",
                    "monto": round(float(c.monto), 2),
                    "estado": c.estado,
                    "fecha_creacion": c.fecha_creacion,
                }
                for c in creditos_qs
            ],
            "alertas_mora": [
                {
                    "credito_id": a.credito_id,
                    "socio_id": a.socio_id,
                    "socio_nombre": a.socio.nombre if a.socio_id else "",
                    "alerta": a.alerta,
                    "prob_mora_90d": round(float(a.prob_mora_90d), 4),
                    "fecha_creacion": a.fecha_creacion,
                }
                for a in alertas_qs
            ],
        }

    return payload


class DashboardEjecutivosOperativosView(APIView):
    permission_classes = [IsAuditorOrHigher]

    def get(self, request):
        role = getattr(getattr(request.user, "profile", None), "rol", UserProfile.ROL_AUDITOR)
        sucursal = (request.query_params.get("sucursal") or "").strip()
        include_drilldown = (request.query_params.get("detalle") or "").strip() in {"1", "true", "si"} and _dashboard_access_scope(role)["drilldown_habilitado"]
        payload = _build_dashboards_1_8_payload(sucursal_detalle=sucursal, include_drilldown=include_drilldown)
        payload = _apply_role_scope_to_payload(payload, role)
        payload["actualizacion"] = _dashboard_actualizacion_info()
        return Response(payload)


class DashboardSemaforosView(APIView):
    permission_classes = [IsAuditorOrHigher]

    def get(self, request):
        role = getattr(getattr(request.user, "profile", None), "rol", UserProfile.ROL_AUDITOR)
        qs = AlertaMonitoreo.objects.filter(estado=AlertaMonitoreo.ESTADO_ACTIVA).order_by("-fecha_evento")
        by_metrica = {}
        severity_rank = {"info": 1, "warn": 2, "critical": 3}
        for row in qs:
            key = f"{row.ambito}:{row.metrica}"
            current = by_metrica.get(key)
            item = {
                "componente": key,
                "ambito": row.ambito,
                "metrica": row.metrica,
                "valor": float(row.valor),
                "umbral": row.umbral,
                "severidad": row.severidad,
                "fecha_evento": row.fecha_evento,
            }
            if not current or severity_rank.get(row.severidad, 1) >= severity_rank.get(current["severidad"], 1):
                by_metrica[key] = item

        semaforo_filter = (request.query_params.get("semaforo") or "").strip().lower()
        ambito_filter = (request.query_params.get("ambito") or "").strip().lower()
        q_filter = (request.query_params.get("q") or "").strip().lower()

        semaforos = []
        for key, item in sorted(by_metrica.items(), key=lambda x: x[0]):
            semaforo = "Verde"
            if item["severidad"] == "warn":
                semaforo = "Amarillo"
            elif item["severidad"] == "critical":
                semaforo = "Rojo"
            sem = {
                "componente": key,
                "ambito": item["ambito"],
                "metrica": item["metrica"],
                "semaforo": semaforo,
                "estado": "En revision" if semaforo != "Verde" else "Cumple",
                "detalle": {
                    "valor": item["valor"],
                    "umbral": item["umbral"],
                    "severidad": item["severidad"],
                    "fecha_evento": item["fecha_evento"],
                },
            }
            if semaforo_filter and sem["semaforo"].lower() != semaforo_filter:
                continue
            if ambito_filter and sem["ambito"].lower() != ambito_filter:
                continue
            if q_filter and q_filter not in sem["componente"].lower() and q_filter not in sem["metrica"].lower():
                continue
            semaforos.append(sem)

        vista = _dashboard_access_scope(role)["vista"]
        if vista == "jefatura":
            semaforos = [x for x in semaforos if "riesgo" not in x["componente"]]
        elif vista == "ejecutivo":
            semaforos = [x for x in semaforos if all(z not in x["componente"] for z in ("riesgo", "cobranza"))]

        resumen = {
            "total": len(semaforos),
            "rojo": sum(1 for x in semaforos if x["semaforo"] == "Rojo"),
            "amarillo": sum(1 for x in semaforos if x["semaforo"] == "Amarillo"),
            "verde": sum(1 for x in semaforos if x["semaforo"] == "Verde"),
        }

        export_format = (request.query_params.get("export") or "").strip().lower()
        if export_format == "csv":
            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = 'attachment; filename="dashboard_semaforos.csv"'
            writer = csv.DictWriter(
                response,
                fieldnames=["componente", "ambito", "metrica", "semaforo", "estado", "valor", "umbral", "fecha_evento"],
            )
            writer.writeheader()
            for row in semaforos:
                writer.writerow(
                    {
                        "componente": row["componente"],
                        "ambito": row["ambito"],
                        "metrica": row["metrica"],
                        "semaforo": row["semaforo"],
                        "estado": row["estado"],
                        "valor": row["detalle"].get("valor"),
                        "umbral": row["detalle"].get("umbral"),
                        "fecha_evento": row["detalle"].get("fecha_evento"),
                    }
                )
            return response

        return Response(
            {
                "resumen": resumen,
                "semaforos": semaforos,
                "actualizacion": _dashboard_actualizacion_info(),
                "acceso": {
                    "rol": role,
                    "vista": vista,
                    "drilldown_habilitado": _dashboard_access_scope(role)["drilldown_habilitado"],
                },
            }
        )


def _fastapi_scoring_url() -> str:
    raw = os.getenv("FASTAPI_API_URL")
    if raw:
        return f"{raw.rstrip('/')}/ml/scoring"
    MAIN = os.getenv("FASTAPI_MAIN_URL", "http://localhost:8001").rstrip("/")
    return f"{MAIN}/api/ml/scoring"


def _call_fastapi_scoring(payload: dict) -> dict:
    request = urllib.request.Request(
        url=_fastapi_scoring_url(),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=6) as response:
        body = response.read().decode("utf-8")
        return json.loads(body)


class ScoringEvaluateView(APIView):
    permission_classes = [IsAuditorOrHigher]

    def post(self, request):
        request_id = str(uuid.uuid4())
        started = time.perf_counter()
        serializer = ScoringEvaluateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        scoring_payload = {
            "ingreso_mensual": float(data["ingreso_mensual"]),
            "deuda_actual": float(data["deuda_actual"]),
            "antiguedad_meses": int(data["antiguedad_meses"]),
        }

        try:
            scoring_response = _call_fastapi_scoring(scoring_payload)
        except urllib.error.HTTPError:
            return Response(
                {"detail": "No se pudo consultar el servicio de scoring.", "request_id": request_id},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError):
            return Response(
                {"detail": "No se pudo consultar el servicio de scoring.", "request_id": request_id},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        score = scoring_response.get("score")
        recomendacion = scoring_response.get("recomendacion")
        riesgo = scoring_response.get("riesgo")
        if not isinstance(score, (int, float)) or score < 0 or score > 1 or not recomendacion or not riesgo:
            return Response(
                {"detail": "Respuesta invalida del servicio de scoring.", "request_id": request_id},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        persisted_id = None
        if data.get("persist", False):
            solicitud_id = data.get("solicitud_id") or f"solicitud_{request.user.id}_{int(score * 10000)}"
            credito = Credito.objects.filter(pk=data.get("credito")).first() if data.get("credito") else None
            socio = Socio.objects.filter(pk=data.get("socio")).first() if data.get("socio") else None
            saved = ResultadoScoring.objects.create(
                solicitud_id=solicitud_id,
                request_id=uuid.UUID(request_id),
                credito=credito,
                socio=socio,
                ingreso_mensual=data["ingreso_mensual"],
                deuda_actual=data["deuda_actual"],
                antiguedad_meses=data["antiguedad_meses"],
                score=score,
                recomendacion=recomendacion,
                riesgo=riesgo,
                model_version=data.get("model_version") or "weighted_score_v1",
            )
            persisted_id = saved.id

        return Response(
            {
                "request_id": request_id,
                "score": float(score),
                "recomendacion": recomendacion,
                "riesgo": riesgo,
                "persisted": bool(persisted_id),
                "resultado_id": persisted_id,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            }
        )
