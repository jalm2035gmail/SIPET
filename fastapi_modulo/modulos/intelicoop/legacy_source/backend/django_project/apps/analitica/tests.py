from unittest.mock import patch
from datetime import timedelta
from pathlib import Path
import tempfile
import uuid
import json

from django.contrib.auth.models import User
from django.core.management import call_command
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.ahorros.models import Cuenta, Transaccion
from apps.creditos.models import Credito, HistorialPago
from apps.socios.models import Socio

from .models import (
    AlertaMonitoreo,
    Campania,
    ContactoCampania,
    EjecucionPipeline,
    Prospecto,
    ReglaAsociacionProducto,
    ResultadoMoraTemprana,
    ResultadoScoring,
    ResultadoSegmentacionSocio,
    SeguimientoConversionCampania,
)


class AnaliticaApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="analitica_user", password="secret123")
        self.user.profile.rol = "administrador"
        self.user.profile.save(update_fields=["rol"])
        self.socio = Socio.objects.create(
            nombre="Socio Analitica",
            email="socio.analitica@test.com",
            telefono="555-0600",
            direccion="Direccion Analitica",
        )
        self.credito = Credito.objects.create(
            socio=self.socio,
            monto="1500.00",
            plazo=12,
            ingreso_mensual="3000.00",
            deuda_actual="200.00",
            antiguedad_meses=24,
            estado="solicitado",
        )
        HistorialPago.objects.create(
            credito=self.credito,
            fecha=timezone.localdate() - timedelta(days=20),
            monto="150.00",
        )
        self.cuenta = Cuenta.objects.create(
            socio=self.socio,
            tipo="ahorro",
            saldo="400.00",
        )
        Transaccion.objects.create(
            cuenta=self.cuenta,
            monto="120.00",
            tipo="deposito",
        )
        Campania.objects.create(
            nombre="Campania Inicial",
            tipo="email",
            fecha_inicio="2026-02-18",
            fecha_fin="2026-03-18",
            estado="borrador",
        )
        Prospecto.objects.create(
            nombre="Prospecto Uno",
            telefono="555-0500",
            direccion="Zona Centro",
            fuente="referido",
            score_propension="0.72",
        )

    def test_get_campanas_requires_authentication(self):
        response = self.client.get("/api/campanas/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_campanas_returns_list_when_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/campanas/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["nombre"], "Campania Inicial")

    def test_post_campanas_creates_record(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "nombre": "Campania Reactivacion",
            "tipo": "llamadas",
            "fecha_inicio": "2026-03-01",
            "fecha_fin": "2026-03-31",
            "estado": "activa",
        }
        response = self.client.post("/api/campanas/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Campania.objects.count(), 2)
        self.assertEqual(response.data["estado"], "activa")

    def test_post_campanas_rejects_invalid_dates(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "nombre": "Campania Invalida",
            "tipo": "email",
            "fecha_inicio": "2026-03-20",
            "fecha_fin": "2026-03-10",
            "estado": "borrador",
        }
        response = self.client.post("/api/campanas/", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("fecha_fin", response.data)

    def test_get_prospectos_requires_authentication(self):
        response = self.client.get("/api/prospectos/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_prospectos_returns_list_when_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/prospectos/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["nombre"], "Prospecto Uno")

    def test_scoring_resultados_requires_authentication(self):
        response = self.client.get("/api/analitica/ml/scoring-resultados/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_post_scoring_resultado_and_get_by_solicitud(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "solicitud_id": "credito_123",
            "credito": self.credito.id,
            "socio": self.socio.id,
            "ingreso_mensual": "3000.00",
            "deuda_actual": "200.00",
            "antiguedad_meses": 24,
            "score": "0.82",
            "recomendacion": "aprobar",
            "riesgo": "bajo",
            "model_version": "weighted_score_v1",
        }
        create_response = self.client.post("/api/analitica/ml/scoring-resultados/", payload, format="json")
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ResultadoScoring.objects.count(), 1)

        get_response = self.client.get("/api/analitica/ml/scoring/credito_123/")
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_response.data["solicitud_id"], "credito_123")
        self.assertEqual(get_response.data["recomendacion"], "aprobar")

    @patch("apps.analitica.views._call_fastapi_scoring")
    def test_scoring_evaluar_without_persist(self, mock_scoring):
        mock_scoring.return_value = {"score": 0.73, "recomendacion": "evaluar", "riesgo": "medio"}
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/analitica/ml/scoring/evaluar/",
            {
                "ingreso_mensual": "3000.00",
                "deuda_actual": "200.00",
                "antiguedad_meses": 24,
                "persist": False,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["score"], 0.73)
        self.assertFalse(response.data["persisted"])
        self.assertIn("request_id", response.data)
        self.assertIn("latency_ms", response.data)

    @patch("apps.analitica.views._call_fastapi_scoring")
    def test_scoring_evaluar_with_persist(self, mock_scoring):
        mock_scoring.return_value = {"score": 0.82, "recomendacion": "aprobar", "riesgo": "bajo"}
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/analitica/ml/scoring/evaluar/",
            {
                "ingreso_mensual": "3000.00",
                "deuda_actual": "200.00",
                "antiguedad_meses": 24,
                "persist": True,
                "solicitud_id": "credito_eval_1",
                "credito": self.credito.id,
                "socio": self.socio.id,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["persisted"])
        self.assertEqual(ResultadoScoring.objects.filter(solicitud_id="credito_eval_1").count(), 1)
        saved = ResultadoScoring.objects.get(solicitud_id="credito_eval_1")
        self.assertEqual(str(saved.request_id), response.data["request_id"])
        uuid.UUID(response.data["request_id"])

    def test_scoring_evaluar_rejects_debt_greater_than_income(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/analitica/ml/scoring/evaluar/",
            {
                "ingreso_mensual": "1200.00",
                "deuda_actual": "1500.00",
                "antiguedad_meses": 12,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("deuda_actual", response.data)

    @patch("apps.analitica.views._call_fastapi_scoring")
    def test_scoring_evaluar_returns_502_when_fastapi_payload_is_invalid(self, mock_scoring):
        mock_scoring.return_value = {"score": "no-num", "recomendacion": "aprobar", "riesgo": "bajo"}
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            "/api/analitica/ml/scoring/evaluar/",
            {
                "ingreso_mensual": "3000.00",
                "deuda_actual": "200.00",
                "antiguedad_meses": 24,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("request_id", response.data)

    def test_scoring_resultados_filter_by_socio(self):
        self.client.force_authenticate(user=self.user)
        another_socio = Socio.objects.create(
            nombre="Otro Socio",
            email="otro.socio@test.com",
            telefono="555-0601",
            direccion="Direccion 2",
        )
        ResultadoScoring.objects.create(
            solicitud_id="sol_1",
            socio=self.socio,
            credito=self.credito,
            ingreso_mensual="3000.00",
            deuda_actual="100.00",
            antiguedad_meses=24,
            score="0.81",
            recomendacion="aprobar",
            riesgo="bajo",
            model_version="weighted_score_v1",
        )
        ResultadoScoring.objects.create(
            solicitud_id="sol_2",
            socio=another_socio,
            ingreso_mensual="2500.00",
            deuda_actual="300.00",
            antiguedad_meses=12,
            score="0.55",
            recomendacion="evaluar",
            riesgo="medio",
            model_version="weighted_score_v1",
        )

        response = self.client.get(f"/api/analitica/ml/scoring-resultados/?socio={self.socio.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["socio"], self.socio.id)

    def test_scoring_resultados_by_socio_endpoint(self):
        self.client.force_authenticate(user=self.user)
        ResultadoScoring.objects.create(
            solicitud_id="sol_3",
            socio=self.socio,
            credito=self.credito,
            ingreso_mensual="3100.00",
            deuda_actual="150.00",
            antiguedad_meses=30,
            score="0.77",
            recomendacion="aprobar",
            riesgo="bajo",
            model_version="weighted_score_v1",
        )

        response = self.client.get(f"/api/analitica/ml/scoring/socio/{self.socio.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["socio"], self.socio.id)

    def test_scoring_socio_recomendacion_returns_executive_summary(self):
        self.client.force_authenticate(user=self.user)
        ResultadoScoring.objects.create(
            solicitud_id="socio_score_1",
            socio=self.socio,
            credito=self.credito,
            ingreso_mensual="3000.00",
            deuda_actual="200.00",
            antiguedad_meses=24,
            score="0.84",
            recomendacion="aprobar",
            riesgo="bajo",
            model_version="weighted_score_v1",
        )
        ResultadoScoring.objects.create(
            solicitud_id="socio_score_2",
            socio=self.socio,
            credito=self.credito,
            ingreso_mensual="3000.00",
            deuda_actual="400.00",
            antiguedad_meses=24,
            score="0.70",
            recomendacion="evaluar",
            riesgo="medio",
            model_version="weighted_score_v1",
        )

        response = self.client.get(f"/api/analitica/ml/scoring/socio/{self.socio.id}/recomendacion/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["tiene_scoring"])
        self.assertEqual(response.data["socio_id"], self.socio.id)
        self.assertIn("actual", response.data)
        self.assertIn("resumen", response.data)
        self.assertIn("historial_reciente", response.data)
        self.assertIn(response.data["actual"]["decision_operativa"], {"preaprobado", "revision", "bloqueado_riesgo"})

    def test_scoring_socio_recomendacion_handles_no_scoring(self):
        self.client.force_authenticate(user=self.user)
        socio_sin_scoring = Socio.objects.create(
            nombre="Socio Sin Scoring",
            email="socio.sin.scoring@test.com",
            telefono="555-0111",
            direccion="Direccion Nueva",
        )
        response = self.client.get(f"/api/analitica/ml/scoring/socio/{socio_sin_scoring.id}/recomendacion/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["tiene_scoring"])
        self.assertIn("detalle", response.data)

    def test_colocacion_preaprobados_lists_only_approved_and_high_score(self):
        self.client.force_authenticate(user=self.user)
        ResultadoScoring.objects.create(
            solicitud_id="pre_001",
            socio=self.socio,
            credito=self.credito,
            ingreso_mensual="3000.00",
            deuda_actual="200.00",
            antiguedad_meses=24,
            score="0.88",
            recomendacion="aprobar",
            riesgo="bajo",
            model_version="weighted_score_v1",
        )
        ResultadoScoring.objects.create(
            solicitud_id="pre_002",
            socio=self.socio,
            credito=self.credito,
            ingreso_mensual="3000.00",
            deuda_actual="200.00",
            antiguedad_meses=24,
            score="0.70",
            recomendacion="evaluar",
            riesgo="medio",
            model_version="weighted_score_v1",
        )

        response = self.client.get("/api/analitica/ml/colocacion/preaprobados/?score_min=0.80")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["resumen"]["total_preaprobados"], 1)
        self.assertEqual(response.data["items"][0]["solicitud_id"], "pre_001")
        self.assertEqual(response.data["items"][0]["socio_id"], self.socio.id)

    def test_colocacion_preaprobados_filters_by_sucursal_and_exports_csv(self):
        self.client.force_authenticate(user=self.user)
        socio_cuitzeo = Socio.objects.create(
            nombre="Socio Cuitzeo",
            email="socio.cuitzeo@test.com",
            telefono="555-0777",
            direccion="Centro Cuitzeo",
        )
        credito_cuitzeo = Credito.objects.create(
            socio=socio_cuitzeo,
            monto="2200.00",
            plazo=12,
            ingreso_mensual="3600.00",
            deuda_actual="300.00",
            antiguedad_meses=30,
            estado="solicitado",
        )
        ResultadoScoring.objects.create(
            solicitud_id="pre_cuitzeo",
            socio=socio_cuitzeo,
            credito=credito_cuitzeo,
            ingreso_mensual="3600.00",
            deuda_actual="300.00",
            antiguedad_meses=30,
            score="0.90",
            recomendacion="aprobar",
            riesgo="bajo",
            model_version="weighted_score_v1",
        )

        response = self.client.get("/api/analitica/ml/colocacion/preaprobados/?sucursal=Cuitzeo&export=csv")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        csv_text = response.content.decode("utf-8")
        self.assertIn("pre_cuitzeo", csv_text)
        self.assertIn("ejecutivo_cuitzeo", csv_text)

    def test_reportes_sucursal_producto_ejecutivo_returns_grouped_metrics(self):
        self.client.force_authenticate(user=self.user)
        socio_yuriria = Socio.objects.create(
            nombre="Socio Yuriria",
            email="socio.yuriria@test.com",
            telefono="555-0888",
            direccion="Zona Yuriria",
        )
        Credito.objects.create(
            socio=socio_yuriria,
            monto="3000.00",
            plazo=6,
            ingreso_mensual="3200.00",
            deuda_actual="400.00",
            antiguedad_meses=20,
            estado=Credito.ESTADO_APROBADO,
        )
        Credito.objects.create(
            socio=socio_yuriria,
            monto="2500.00",
            plazo=6,
            ingreso_mensual="3200.00",
            deuda_actual="400.00",
            antiguedad_meses=20,
            estado=Credito.ESTADO_RECHAZADO,
        )

        response = self.client.get("/api/analitica/ml/reportes/sucursal-producto-ejecutivo/?sucursal=Yuriria")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["resumen"]["total_grupos"], 1)
        first = response.data["items"][0]
        self.assertEqual(first["sucursal"], "Yuriria")
        self.assertIn(first["producto"], {"microcredito", "consumo", "productivo"})
        self.assertIn("ejecutivo", first)
        self.assertIn("tasa_aprobacion_pct", first)

    def test_reportes_sucursal_producto_ejecutivo_exports_csv(self):
        self.client.force_authenticate(user=self.user)
        socio_cuitzeo = Socio.objects.create(
            nombre="Socio Ejecutivo Cuitzeo",
            email="socio.ejecutivo.cuitzeo@test.com",
            telefono="555-0999",
            direccion="Avenida Cuitzeo",
        )
        Credito.objects.create(
            socio=socio_cuitzeo,
            monto="7000.00",
            plazo=12,
            ingreso_mensual="5000.00",
            deuda_actual="600.00",
            antiguedad_meses=25,
            estado=Credito.ESTADO_APROBADO,
        )

        response = self.client.get(
            "/api/analitica/ml/reportes/sucursal-producto-ejecutivo/?sucursal=Cuitzeo&export=csv"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        csv_text = response.content.decode("utf-8")
        self.assertIn("sucursal,producto,ejecutivo", csv_text)
        self.assertIn("Cuitzeo", csv_text)

    def test_alertas_tempranas_operativas_returns_prioritized_items(self):
        self.client.force_authenticate(user=self.user)
        ResultadoMoraTemprana.objects.create(
            credito=self.credito,
            socio=self.socio,
            fecha_corte=timezone.localdate(),
            cuota_estimada="200.00",
            pagos_90d="100.00",
            ratio_pago_90d="0.50",
            deuda_ingreso_ratio="0.60",
            prob_mora_30d="0.70",
            prob_mora_60d="0.80",
            prob_mora_90d="0.92",
            alerta=ResultadoMoraTemprana.ALERTA_ALTA,
            model_version="mora_temprana_v1",
            fuente=ResultadoMoraTemprana.FUENTE_BATCH,
        )
        response = self.client.get("/api/analitica/ml/alertas-tempranas/operativas/?prioridad=critica")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["resumen"]["total_alertas"], 1)
        self.assertEqual(response.data["items"][0]["prioridad"], "critica")
        self.assertEqual(response.data["items"][0]["accion_sugerida"], "contacto_inmediato_24h")

    def test_alertas_tempranas_operativas_exports_csv(self):
        self.client.force_authenticate(user=self.user)
        ResultadoMoraTemprana.objects.create(
            credito=self.credito,
            socio=self.socio,
            fecha_corte=timezone.localdate(),
            cuota_estimada="200.00",
            pagos_90d="180.00",
            ratio_pago_90d="0.70",
            deuda_ingreso_ratio="0.40",
            prob_mora_30d="0.30",
            prob_mora_60d="0.45",
            prob_mora_90d="0.60",
            alerta=ResultadoMoraTemprana.ALERTA_MEDIA,
            model_version="mora_temprana_v1",
            fuente=ResultadoMoraTemprana.FUENTE_BATCH,
        )
        response = self.client.get("/api/analitica/ml/alertas-tempranas/operativas/?export=csv")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        csv_text = response.content.decode("utf-8")
        self.assertIn("socio_id,socio_nombre,credito_id", csv_text)
        self.assertIn("accion_sugerida", csv_text)

    def test_reporte_mensual_riesgo_crecimiento_returns_payload(self):
        self.client.force_authenticate(user=self.user)
        today = timezone.localdate()
        periodo = today.strftime("%Y-%m")

        scoring = ResultadoScoring.objects.create(
            solicitud_id="rep_mensual_scoring",
            socio=self.socio,
            credito=self.credito,
            ingreso_mensual="3000.00",
            deuda_actual="300.00",
            antiguedad_meses=24,
            score="0.82",
            recomendacion="aprobar",
            riesgo="medio",
            model_version="weighted_score_v1",
        )
        ResultadoScoring.objects.filter(pk=scoring.pk).update(fecha_creacion=timezone.now())

        mora = ResultadoMoraTemprana.objects.create(
            credito=self.credito,
            socio=self.socio,
            fecha_corte=today,
            cuota_estimada="200.00",
            pagos_90d="120.00",
            ratio_pago_90d="0.60",
            deuda_ingreso_ratio="0.50",
            prob_mora_30d="0.40",
            prob_mora_60d="0.55",
            prob_mora_90d="0.70",
            alerta=ResultadoMoraTemprana.ALERTA_MEDIA,
            model_version="mora_temprana_v1",
            fuente=ResultadoMoraTemprana.FUENTE_BATCH,
        )
        ResultadoMoraTemprana.objects.filter(pk=mora.pk).update(fecha_creacion=timezone.now())

        response = self.client.get(f"/api/analitica/ml/reportes/mensual-riesgo-crecimiento/?periodo={periodo}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["periodo"], periodo)
        self.assertIn("riesgo", response.data)
        self.assertIn("crecimiento", response.data)
        self.assertIn("sucursales", response.data)
        self.assertIn("cobertura_pct", response.data["riesgo"])
        self.assertIn("colocacion_monto", response.data["crecimiento"])

    def test_reporte_mensual_riesgo_crecimiento_exports_csv_and_validates_period(self):
        self.client.force_authenticate(user=self.user)
        invalid = self.client.get("/api/analitica/ml/reportes/mensual-riesgo-crecimiento/?periodo=2026/02")
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)

        periodo = timezone.localdate().strftime("%Y-%m")
        csv_response = self.client.get(
            f"/api/analitica/ml/reportes/mensual-riesgo-crecimiento/?periodo={periodo}&export=csv"
        )
        self.assertEqual(csv_response.status_code, status.HTTP_200_OK)
        self.assertEqual(csv_response["Content-Type"], "text/csv; charset=utf-8")
        csv_text = csv_response.content.decode("utf-8")
        self.assertIn("periodo,dimension,metrica,valor", csv_text)
        self.assertIn("riesgo", csv_text)
        self.assertIn("crecimiento", csv_text)

    def test_reporte_mensual_riesgo_crecimiento_exports_excel_and_pdf(self):
        self.client.force_authenticate(user=self.user)
        periodo = timezone.localdate().strftime("%Y-%m")

        excel_response = self.client.get(
            f"/api/analitica/ml/reportes/mensual-riesgo-crecimiento/?periodo={periodo}&export=excel"
        )
        self.assertEqual(excel_response.status_code, status.HTTP_200_OK)
        self.assertEqual(excel_response["Content-Type"], "application/vnd.ms-excel; charset=utf-8")
        self.assertIn(".xls", excel_response["Content-Disposition"])
        self.assertIn(b"<Workbook", excel_response.content)

        pdf_response = self.client.get(f"/api/analitica/ml/reportes/mensual-riesgo-crecimiento/?periodo={periodo}&export=pdf")
        self.assertEqual(pdf_response.status_code, status.HTTP_200_OK)
        self.assertEqual(pdf_response["Content-Type"], "application/pdf")
        self.assertIn(".pdf", pdf_response["Content-Disposition"])
        self.assertTrue(pdf_response.content.startswith(b"%PDF-1.4"))

    def test_reporte_consejo_exportables_alias_works(self):
        self.client.force_authenticate(user=self.user)
        periodo = timezone.localdate().strftime("%Y-%m")
        response = self.client.get(f"/api/analitica/ml/reportes/consejo/exportables/?periodo={periodo}&export=pdf")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")

    def test_scoring_resumen_endpoint(self):
        self.client.force_authenticate(user=self.user)
        ResultadoScoring.objects.create(
            solicitud_id="res_1",
            socio=self.socio,
            credito=self.credito,
            ingreso_mensual="3000.00",
            deuda_actual="100.00",
            antiguedad_meses=24,
            score="0.80",
            recomendacion="aprobar",
            riesgo="bajo",
            model_version="weighted_score_v1",
        )
        ResultadoScoring.objects.create(
            solicitud_id="res_2",
            socio=self.socio,
            credito=self.credito,
            ingreso_mensual="3000.00",
            deuda_actual="1200.00",
            antiguedad_meses=6,
            score="0.35",
            recomendacion="rechazar",
            riesgo="alto",
            model_version="weighted_score_v1",
        )

        response = self.client.get("/api/analitica/ml/scoring/resumen/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_inferencias"], 2)
        self.assertIn("score_promedio", response.data)
        self.assertEqual(response.data["por_riesgo"]["bajo"], 1)
        self.assertEqual(response.data["por_riesgo"]["alto"], 1)
        self.assertEqual(response.data["por_recomendacion"]["aprobar"], 1)
        self.assertEqual(response.data["por_recomendacion"]["rechazar"], 1)
        self.assertLessEqual(len(response.data["recientes"]), 5)

    @patch("apps.analitica.views._call_fastapi_scoring")
    def test_scoring_evaluar_forbids_post_for_auditor(self, mock_scoring):
        mock_scoring.return_value = {"score": 0.61, "recomendacion": "evaluar", "riesgo": "medio"}
        auditor = User.objects.create_user(username="analitica_auditor", password="secret123")
        auditor.profile.rol = "auditor"
        auditor.profile.save(update_fields=["rol"])
        self.client.force_authenticate(user=auditor)

        response = self.client.post(
            "/api/analitica/ml/scoring/evaluar/",
            {
                "ingreso_mensual": "3000.00",
                "deuda_actual": "200.00",
                "antiguedad_meses": 24,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("apps.analitica.views._call_fastapi_scoring")
    def test_scoring_evaluar_allows_post_for_admin(self, mock_scoring):
        mock_scoring.return_value = {"score": 0.61, "recomendacion": "evaluar", "riesgo": "medio"}
        admin = User.objects.create_user(username="analitica_admin_2", password="secret123")
        admin.profile.rol = "administrador"
        admin.profile.save(update_fields=["rol"])
        self.client.force_authenticate(user=admin)

        response = self.client.post(
            "/api/analitica/ml/scoring/evaluar/",
            {
                "ingreso_mensual": "3000.00",
                "deuda_actual": "200.00",
                "antiguedad_meses": 24,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["recomendacion"], "evaluar")

    def test_priorizar_modelos_complementarios_generates_reports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "prioridad.csv"
            md_path = Path(tmpdir) / "prioridad.md"

            call_command(
                "priorizar_modelos_complementarios",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )

            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            csv_content = csv_path.read_text(encoding="utf-8")
            md_content = md_path.read_text(encoding="utf-8")
            self.assertIn("mora_temprana", csv_content)
            self.assertIn("segmentacion_socios", csv_content)
            self.assertIn("reglas_asociacion", csv_content)
            self.assertIn("Punto 1 de 7 completado tecnicamente", md_content)

    def test_mora_temprana_evaluar_with_persist(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            "/api/analitica/ml/mora-temprana/evaluar/",
            {"credito": self.credito.id, "persist": True},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["persisted"])
        self.assertEqual(response.data["credito"], self.credito.id)
        self.assertIn(response.data["alerta"], ("baja", "media", "alta"))
        self.assertEqual(ResultadoMoraTemprana.objects.count(), 1)

    def test_mora_temprana_resumen_endpoint(self):
        self.client.force_authenticate(user=self.user)
        ResultadoMoraTemprana.objects.create(
            credito=self.credito,
            socio=self.socio,
            fecha_corte=timezone.localdate(),
            cuota_estimada="125.00",
            pagos_90d="120.00",
            ratio_pago_90d="0.3200",
            deuda_ingreso_ratio="0.1000",
            prob_mora_30d="0.2000",
            prob_mora_60d="0.3000",
            prob_mora_90d="0.4000",
            alerta="media",
            fuente="batch",
            model_version="mora_temprana_v1",
        )

        response = self.client.get("/api/analitica/ml/mora-temprana/resumen/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_alertas"], 1)
        self.assertIn("prob_90d_promedio", response.data)
        self.assertEqual(response.data["por_alerta"]["media"], 1)

    def test_generar_alertas_mora_temprana_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "mora.csv"
            md_path = Path(tmpdir) / "mora.md"
            call_command(
                "generar_alertas_mora_temprana",
                limit=10,
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("credito_id", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 2 de 7 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_generar_segmentacion_mensual_socios_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "segmentacion.csv"
            md_path = Path(tmpdir) / "segmentacion.md"
            call_command(
                "generar_segmentacion_mensual_socios",
                engine="orm",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("segmento", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 3 de 7 completado tecnicamente", md_path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(ResultadoSegmentacionSocio.objects.count(), 1)

    def test_segmentacion_socios_perfiles_endpoint(self):
        self.client.force_authenticate(user=self.user)
        ResultadoSegmentacionSocio.objects.create(
            socio=self.socio,
            fecha_ejecucion=timezone.localdate(),
            segmento="hormiga",
            saldo_total="400.00",
            total_movimientos="120.00",
            cantidad_movimientos=1,
            dias_desde_ultimo_movimiento=0,
            total_creditos=1,
            model_version="segmentacion_socios_v1",
        )
        response = self.client.get("/api/analitica/ml/segmentacion-socios/perfiles/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_socios_segmentados"], 1)
        self.assertEqual(len(response.data["perfiles"]), 3)

    def test_segmentacion_inteligente_ejecutar_requires_authentication(self):
        response = self.client.post("/api/analitica/ml/segmentacion-inteligente/ejecutar/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_segmentacion_inteligente_ejecutar_forbids_auditor(self):
        auditor = User.objects.create_user(username="auditor_seg", password="secret123")
        auditor.profile.rol = "auditor"
        auditor.profile.save(update_fields=["rol"])
        self.client.force_authenticate(user=auditor)

        response = self.client.post("/api/analitica/ml/segmentacion-inteligente/ejecutar/", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_segmentacion_inteligente_ejecutar_allows_admin(self):
        self.client.force_authenticate(user=self.user)
        with tempfile.TemporaryDirectory() as tmpdir:
            report_csv = Path(tmpdir) / "seg_resumen.csv"
            dataset_csv = Path(tmpdir) / "seg_dataset.csv"
            report_md = Path(tmpdir) / "seg.md"
            thresholds_json = Path(tmpdir) / "umbrales.json"
            thresholds_json.write_text(
                json.dumps(
                    {
                        "version": "segmentacion_1_4_test_v9",
                        "thresholds": {
                            "listos_para_credito": {
                                "min_score_promedio": 0.75,
                                "max_prob_mora_90d": 0.30,
                                "max_variabilidad_ahorro": 0.50,
                                "min_ahorro_total": 300.0,
                            },
                            "renovacion_segura": {
                                "min_total_creditos": 1,
                                "min_pagos_180d": 1.0,
                                "max_prob_mora_90d": 0.30,
                            },
                            "riesgo_alto": {
                                "min_prob_mora_90d": 0.60,
                                "min_alertas_altas": 1,
                                "min_variabilidad_ahorro": 0.80,
                            },
                            "potencial_captacion": {"min_ahorro_total": 1000.0, "max_total_creditos": 0},
                            "jovenes_digitales": {
                                "min_transacciones_180d": 6,
                                "max_monto_promedio_transaccion": 250.0,
                                "max_total_creditos": 1,
                            },
                        },
                    },
                    ensure_ascii=True,
                ),
                encoding="utf-8",
            )

            response = self.client.post(
                "/api/analitica/ml/segmentacion-inteligente/ejecutar/",
                {
                    "metodo": "reglas",
                    "clusters": 4,
                    "thresholds_json": str(thresholds_json),
                    "thresholds_version": "segmentacion_1_4_test_v9",
                    "report_csv": str(report_csv),
                    "dataset_csv": str(dataset_csv),
                    "report_md": str(report_md),
                },
                format="json",
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["status"], "ok")
            self.assertEqual(response.data["metodo"], "reglas")
            self.assertEqual(response.data["thresholds_version"], "segmentacion_1_4_test_v9")
            self.assertTrue(report_csv.exists())
            self.assertTrue(dataset_csv.exists())
            self.assertTrue(report_md.exists())
            dataset_content = dataset_csv.read_text(encoding="utf-8")
            self.assertIn("segmento", dataset_content)
            self.assertIn("segmentacion_1_4_test_v9", dataset_content)

    def test_generar_reglas_asociacion_productos_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "reglas.csv"
            md_path = Path(tmpdir) / "reglas.md"
            call_command(
                "generar_reglas_asociacion_productos",
                min_support=0.10,
                min_confidence=0.10,
                min_lift=1.00,
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("antecedente", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 4 de 7 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_reglas_asociacion_resumen_endpoint(self):
        self.client.force_authenticate(user=self.user)
        ReglaAsociacionProducto.objects.create(
            fecha_ejecucion=timezone.localdate(),
            antecedente="cuenta_ahorro",
            consecuente="credito_solicitado",
            soporte="0.5000",
            confianza="0.7000",
            lift="1.1000",
            casos_antecedente=2,
            casos_regla=1,
            oportunidad_comercial="Campana de acompanamiento a solicitud de credito.",
            vigente=True,
            model_version="asociacion_productos_v1",
        )
        response = self.client.get("/api/analitica/ml/reglas-asociacion/resumen/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["total_reglas"], 1)
        self.assertEqual(len(response.data["top_reglas"]), 1)

    def test_submodulos_integracion_resumen_endpoint(self):
        self.client.force_authenticate(user=self.user)
        ResultadoScoring.objects.create(
            solicitud_id="integ_scoring",
            socio=self.socio,
            credito=self.credito,
            ingreso_mensual="3000.00",
            deuda_actual="200.00",
            antiguedad_meses=24,
            score="0.70",
            recomendacion="evaluar",
            riesgo="medio",
            model_version="weighted_score_v1",
        )
        ResultadoMoraTemprana.objects.create(
            credito=self.credito,
            socio=self.socio,
            fecha_corte=timezone.localdate(),
            cuota_estimada="125.00",
            pagos_90d="120.00",
            ratio_pago_90d="0.3200",
            deuda_ingreso_ratio="0.1000",
            prob_mora_30d="0.2000",
            prob_mora_60d="0.3000",
            prob_mora_90d="0.4000",
            alerta="media",
            fuente="batch",
            model_version="mora_temprana_v1",
        )
        ResultadoSegmentacionSocio.objects.create(
            socio=self.socio,
            fecha_ejecucion=timezone.localdate(),
            segmento="hormiga",
            saldo_total="400.00",
            total_movimientos="120.00",
            cantidad_movimientos=1,
            dias_desde_ultimo_movimiento=0,
            total_creditos=1,
            model_version="segmentacion_socios_v1",
        )
        response = self.client.get("/api/analitica/ml/submodulos/resumen/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("submodulos", response.data)
        self.assertIn("consistencia", response.data)
        self.assertEqual(response.data["consistencia"]["socios_con_scoring_mora_segmentacion"], 1)

    def test_integrar_submodulos_fase4_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "integracion.csv"
            md_path = Path(tmpdir) / "integracion.md"
            call_command(
                "integrar_submodulos_fase4",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("submodulo", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 5 de 7 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_validar_submodulos_fase4_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "validacion.csv"
            md_path = Path(tmpdir) / "validacion.md"
            call_command(
                "validar_submodulos_fase4",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("dimension", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 6 de 7 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_cerrar_fase4_modelos_complementarios_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "cierre.csv"
            md_path = Path(tmpdir) / "cierre.md"
            call_command(
                "cerrar_fase4_modelos_complementarios",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("entregable", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 7 de 7 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_disenar_arquitectura_ejecucion_fase5_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "arquitectura.csv"
            md_path = Path(tmpdir) / "arquitectura.md"
            call_command(
                "disenar_arquitectura_ejecucion_fase5",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("flujo", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 1 de 8 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_orquestar_pipelines_fase5_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "orquestacion.csv"
            md_path = Path(tmpdir) / "orquestacion.md"
            call_command(
                "orquestar_pipelines_fase5",
                fecha_corte=str(timezone.localdate()),
                run_id="test_run",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            csv_content = csv_path.read_text(encoding="utf-8")
            self.assertIn("pipeline", csv_content)
            self.assertIn("segmentacion_inteligente_1_4", csv_content)
            self.assertIn("acciones_campanas_segmentos_1_4", csv_content)
            self.assertIn("Punto 2 de 8 completado tecnicamente", md_path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(EjecucionPipeline.objects.count(), 1)

    def test_automatizar_reentrenamiento_fase5_command_dry_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "reentrenamiento.csv"
            md_path = Path(tmpdir) / "reentrenamiento.md"
            call_command(
                "automatizar_reentrenamiento_fase5",
                run_id="test_retrain",
                dry_run=True,
                force=True,
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("dimension", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 3 de 8 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_publicar_contratos_api_fase5_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            openapi_path = Path(tmpdir) / "openapi.json"
            csv_path = Path(tmpdir) / "consumidores.csv"
            md_path = Path(tmpdir) / "contratos.md"
            call_command(
                "publicar_contratos_api_fase5",
                openapi_json=str(openapi_path),
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(openapi_path.exists())
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("openapi", openapi_path.read_text(encoding="utf-8").lower())
            self.assertIn("consumidor", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 4 de 8 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_v1_analitica_routes_available(self):
        response = self.client.get("/api/v1/analitica/ml/scoring-resultados/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_monitorear_alertamiento_fase5_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "monitoreo.csv"
            md_path = Path(tmpdir) / "monitoreo.md"
            call_command(
                "monitorear_alertamiento_fase5",
                min_availability=101.0,
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("ambito", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 5 de 8 completado tecnicamente", md_path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(AlertaMonitoreo.objects.count(), 1)

    def test_observabilidad_trazabilidad_fase5_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_csv = Path(tmpdir) / "trace.csv"
            changes_csv = Path(tmpdir) / "changes.csv"
            logs_jsonl = Path(tmpdir) / "obs.jsonl"
            report_md = Path(tmpdir) / "obs.md"
            call_command(
                "observabilidad_trazabilidad_fase5",
                trace_csv=str(trace_csv),
                changes_csv=str(changes_csv),
                logs_jsonl=str(logs_jsonl),
                report_md=str(report_md),
            )
            self.assertTrue(trace_csv.exists())
            self.assertTrue(changes_csv.exists())
            self.assertTrue(logs_jsonl.exists())
            self.assertTrue(report_md.exists())
            self.assertIn("tipo_prediccion", trace_csv.read_text(encoding="utf-8"))
            self.assertIn("tipo_cambio", changes_csv.read_text(encoding="utf-8"))
            self.assertIn("Punto 6 de 8 completado tecnicamente", report_md.read_text(encoding="utf-8"))

    def test_gestionar_operacion_continuidad_fase5_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            runbook_csv = Path(tmpdir) / "runbook.csv"
            continuidad_csv = Path(tmpdir) / "continuidad.csv"
            report_md = Path(tmpdir) / "gestion.md"
            call_command(
                "gestionar_operacion_continuidad_fase5",
                runbook_csv=str(runbook_csv),
                continuidad_csv=str(continuidad_csv),
                report_md=str(report_md),
            )
            self.assertTrue(runbook_csv.exists())
            self.assertTrue(continuidad_csv.exists())
            self.assertTrue(report_md.exists())
            self.assertIn("proceso", runbook_csv.read_text(encoding="utf-8"))
            self.assertIn("escenario", continuidad_csv.read_text(encoding="utf-8"))
            self.assertIn("Punto 7 de 8 completado tecnicamente", report_md.read_text(encoding="utf-8"))

    def test_cerrar_fase5_integracion_automatizacion_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "fase5.csv"
            md_path = Path(tmpdir) / "fase5.md"
            call_command(
                "cerrar_fase5_integracion_automatizacion",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("entregable", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 8 de 8 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_validar_tecnica_modelos_fase6_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "fase6.csv"
            md_path = Path(tmpdir) / "fase6.md"
            call_command(
                "validar_tecnica_modelos_fase6",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("dimension", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 1 de 8 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_validar_funcional_negocio_fase6_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "fase6_funcional.csv"
            md_path = Path(tmpdir) / "fase6_funcional.md"
            call_command(
                "validar_funcional_negocio_fase6",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("area", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 2 de 8 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_probar_robustez_resiliencia_fase6_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "fase6_robustez.csv"
            md_path = Path(tmpdir) / "fase6_robustez.md"
            call_command(
                "probar_robustez_resiliencia_fase6",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("escenario", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 3 de 8 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_asegurar_seguridad_informacion_fase6_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "fase6_seguridad.csv"
            md_path = Path(tmpdir) / "fase6_seguridad.md"
            call_command(
                "asegurar_seguridad_informacion_fase6",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("dimension", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 4 de 8 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_validar_cumplimiento_privacidad_fase6_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "fase6_cumplimiento.csv"
            md_path = Path(tmpdir) / "fase6_cumplimiento.md"
            call_command(
                "validar_cumplimiento_privacidad_fase6",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("dimension", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 5 de 8 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_auditar_trazabilidad_extremo_extremo_fase6_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            trace_csv = Path(tmpdir) / "fase6_trace.csv"
            changes_csv = Path(tmpdir) / "fase6_changes.csv"
            approvals_csv = Path(tmpdir) / "fase6_approvals.csv"
            md_path = Path(tmpdir) / "fase6_trace.md"
            call_command(
                "auditar_trazabilidad_extremo_extremo_fase6",
                trace_csv=str(trace_csv),
                changes_csv=str(changes_csv),
                approvals_csv=str(approvals_csv),
                report_md=str(md_path),
            )
            self.assertTrue(trace_csv.exists())
            self.assertTrue(changes_csv.exists())
            self.assertTrue(approvals_csv.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("tipo_inferencia", trace_csv.read_text(encoding="utf-8"))
            self.assertIn("actor", changes_csv.read_text(encoding="utf-8"))
            self.assertIn("decision", approvals_csv.read_text(encoding="utf-8"))
            self.assertIn("Punto 6 de 8 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_gobierno_cambios_modulo_fase6_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "fase6_gobierno.csv"
            md_path = Path(tmpdir) / "fase6_gobierno.md"
            call_command(
                "gobierno_cambios_modulo_fase6",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("dimension", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 7 de 8 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_cerrar_fase6_validacion_seguridad_auditoria_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "fase6_cierre.csv"
            md_path = Path(tmpdir) / "fase6_cierre.md"
            call_command(
                "cerrar_fase6_validacion_seguridad_auditoria",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("entregable", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 8 de 8 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_monitorear_desempeno_continuo_fase7_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "fase7_monitoreo.csv"
            md_path = Path(tmpdir) / "fase7_monitoreo.md"
            call_command(
                "monitorear_desempeno_continuo_fase7",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("dimension", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 1 de 8 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_gestionar_drift_recalibracion_fase7_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "fase7_drift.csv"
            md_path = Path(tmpdir) / "fase7_drift.md"
            json_path = Path(tmpdir) / "fase7_thresholds.json"
            call_command(
                "gestionar_drift_recalibracion_fase7",
                report_csv=str(csv_path),
                report_md=str(md_path),
                thresholds_json=str(json_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertTrue(json_path.exists())
            self.assertIn("dimension", csv_path.read_text(encoding="utf-8"))
            self.assertIn("thresholds", json_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 2 de 8 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_mejorar_incremental_modulo_fase7_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "fase7_mejora.csv"
            md_path = Path(tmpdir) / "fase7_mejora.md"
            json_path = Path(tmpdir) / "fase7_externa.json"
            call_command(
                "mejorar_incremental_modulo_fase7",
                report_csv=str(csv_path),
                report_md=str(md_path),
                external_json=str(json_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertTrue(json_path.exists())
            self.assertIn("dimension", csv_path.read_text(encoding="utf-8"))
            self.assertIn("economic_stress_index", json_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 3 de 8 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_experimentacion_controlada_fase7_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "fase7_experimento.csv"
            md_path = Path(tmpdir) / "fase7_experimento.md"
            call_command(
                "experimentacion_controlada_fase7",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("dimension", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 4 de 8 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_gestionar_deuda_tecnica_mantenimiento_fase7_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "fase7_deuda.csv"
            md_path = Path(tmpdir) / "fase7_deuda.md"
            call_command(
                "gestionar_deuda_tecnica_mantenimiento_fase7",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertTrue((Path(tmpdir) / "05_deuda_tecnica_backlog.csv").exists())
            self.assertIn("dimension", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 5 de 8 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_adopcion_organizacional_fase7_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "fase7_adopcion.csv"
            md_path = Path(tmpdir) / "fase7_adopcion.md"
            call_command(
                "adopcion_organizacional_fase7",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertTrue((Path(tmpdir) / "06_plan_entrenamiento_usuarios.csv").exists())
            self.assertTrue((Path(tmpdir) / "06_rutinas_operativas.csv").exists())
            self.assertTrue((Path(tmpdir) / "06_feedback_priorizado.csv").exists())
            self.assertIn("dimension", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 6 de 8 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_gobierno_roadmap_evolutivo_fase7_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "fase7_roadmap.csv"
            md_path = Path(tmpdir) / "fase7_roadmap.md"
            call_command(
                "gobierno_roadmap_evolutivo_fase7",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertTrue((Path(tmpdir) / "07_roadmap_trimestral.csv").exists())
            self.assertIn("dimension", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 7 de 8 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_cerrar_fase7_operacion_mejora_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "fase7_cierre.csv"
            md_path = Path(tmpdir) / "fase7_cierre.md"
            call_command(
                "cerrar_fase7_operacion_mejora",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("entregable", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Punto 8 de 8 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_cerrar_fase3_construccion_mvp_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "fase3_cierre.csv"
            md_path = Path(tmpdir) / "fase3_cierre.md"
            call_command(
                "cerrar_fase3_construccion_mvp",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("entregable", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Fase 3 cerrada tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_ingesta_cargadores_fuentes_1_1_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "incoming"
            raw_dir = Path(tmpdir) / "raw"
            report_csv = Path(tmpdir) / "ingesta.csv"
            report_md = Path(tmpdir) / "ingesta.md"
            input_dir.mkdir(parents=True, exist_ok=True)

            (input_dir / "socios.csv").write_text(
                "id_socio,nombre,email\n1,Socio Uno,s1@test.com\n",
                encoding="utf-8",
            )
            (input_dir / "creditos.csv").write_text(
                "id_credito,id_socio,monto\n10,1,1500.00\n",
                encoding="utf-8",
            )
            (input_dir / "captacion.csv").write_text(
                "id_movimiento,id_socio,tipo,monto,fecha\nm1,1,deposito,100.00,2026-02-18\n",
                encoding="utf-8",
            )
            (input_dir / "cobranza.csv").write_text(
                "id_gestion,id_credito,estado,fecha\ng1,10,gestionado,2026-02-18\n",
                encoding="utf-8",
            )
            (input_dir / "contabilidad.csv").write_text(
                "id_asiento,cuenta,monto,fecha\na1,1101,100.00,2026-02-18\n",
                encoding="utf-8",
            )

            call_command(
                "ingesta_cargadores_fuentes_1_1",
                input_dir=str(input_dir),
                raw_dir=str(raw_dir),
                report_csv=str(report_csv),
                report_md=str(report_md),
                actor="tester",
                dataset_version="intake_test_v1",
            )

            self.assertTrue(report_csv.exists())
            self.assertTrue(report_md.exists())
            self.assertTrue((raw_dir / "socios.jsonl").exists())
            self.assertTrue((raw_dir / "creditos.jsonl").exists())
            self.assertIn("fuente", report_csv.read_text(encoding="utf-8"))
            self.assertIn("Etapa 1 de 4 completada tecnicamente", report_md.read_text(encoding="utf-8"))

    def test_ingesta_conectores_fuentes_1_1_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            input_dir = Path(tmpdir) / "incoming"
            report_csv = Path(tmpdir) / "conectores.csv"
            report_md = Path(tmpdir) / "conectores.md"
            manifest_json = Path(tmpdir) / "conectores.json"
            input_dir.mkdir(parents=True, exist_ok=True)

            call_command(
                "ingesta_conectores_fuentes_1_1",
                input_dir=str(input_dir),
                report_csv=str(report_csv),
                report_md=str(report_md),
                manifest_json=str(manifest_json),
            )

            self.assertTrue(report_csv.exists())
            self.assertTrue(report_md.exists())
            self.assertTrue(manifest_json.exists())
            self.assertIn("conector", report_csv.read_text(encoding="utf-8"))
            self.assertIn("connectors", manifest_json.read_text(encoding="utf-8"))
            self.assertIn("Etapa 2 de 4 completada tecnicamente", report_md.read_text(encoding="utf-8"))

    def test_ingesta_validaciones_1_1_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "raw"
            raw_dir.mkdir(parents=True, exist_ok=True)
            report_csv = Path(tmpdir) / "validaciones.csv"
            report_md = Path(tmpdir) / "validaciones.md"

            socios_line = {
                "source": "socios",
                "row_num": 1,
                "loaded_at": "2026-02-18T00:00:00+00:00",
                "dataset_version": "test",
                "actor": "tester",
                "data": {"id_socio": "1", "nombre": "Socio Uno", "email": "s1@test.com"},
            }
            (raw_dir / "socios.jsonl").write_text(json.dumps(socios_line, ensure_ascii=True) + "\n", encoding="utf-8")

            call_command(
                "ingesta_validaciones_1_1",
                raw_dir=str(raw_dir),
                report_csv=str(report_csv),
                report_md=str(report_md),
            )

            self.assertTrue(report_csv.exists())
            self.assertTrue(report_md.exists())
            self.assertIn("fuente", report_csv.read_text(encoding="utf-8"))
            self.assertIn("Etapa 3 de 4 completada tecnicamente", report_md.read_text(encoding="utf-8"))

    def test_ingesta_auditoria_salida_1_1_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            raw_dir = Path(tmpdir) / "raw"
            std_dir = Path(tmpdir) / "standardized"
            raw_dir.mkdir(parents=True, exist_ok=True)
            report_csv = Path(tmpdir) / "auditoria.csv"
            report_md = Path(tmpdir) / "auditoria.md"
            audit_jsonl = Path(tmpdir) / "audit.jsonl"

            socios_line = {
                "source": "socios",
                "row_num": 1,
                "loaded_at": "2026-02-18T00:00:00+00:00",
                "dataset_version": "test",
                "actor": "tester",
                "data": {"id_socio": "1", "nombre": " Socio Uno ", "email": "S1@TEST.COM"},
            }
            (raw_dir / "socios.jsonl").write_text(json.dumps(socios_line, ensure_ascii=True) + "\n", encoding="utf-8")

            call_command(
                "ingesta_auditoria_salida_1_1",
                raw_dir=str(raw_dir),
                std_dir=str(std_dir),
                audit_jsonl=str(audit_jsonl),
                report_csv=str(report_csv),
                report_md=str(report_md),
                actor="tester",
                dataset_version="intake_test_v1",
            )

            self.assertTrue(report_csv.exists())
            self.assertTrue(report_md.exists())
            self.assertTrue(audit_jsonl.exists())
            self.assertTrue((std_dir / "socios.jsonl").exists())
            std_content = (std_dir / "socios.jsonl").read_text(encoding="utf-8")
            self.assertIn("s1@test.com", std_content)
            self.assertIn("Etapa 4 de 4 completada tecnicamente", report_md.read_text(encoding="utf-8"))

    def test_catalogo_maestro_institucional_1_2_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "master.csv"
            md_path = Path(tmpdir) / "master.md"
            call_command(
                "catalogo_maestro_institucional_1_2",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("socio_id", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Elemento 1 de 4 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_catalogo_territorio_sucursales_1_2_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "territorio.csv"
            md_path = Path(tmpdir) / "territorio.md"
            call_command(
                "catalogo_territorio_sucursales_1_2",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            content = csv_path.read_text(encoding="utf-8")
            self.assertIn("sucursal_id", content)
            self.assertIn("Yuriria", content)
            self.assertIn("Elemento 2 de 4 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_catalogo_comercios_campanas_1_2_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "comercios.csv"
            md_path = Path(tmpdir) / "comercios.md"
            call_command(
                "catalogo_comercios_campanas_1_2",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            content = csv_path.read_text(encoding="utf-8")
            self.assertIn("comercio_id", content)
            self.assertIn("catalogo_comercio", content)
            self.assertIn("Elemento 3 de 4 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_catalogo_identificadores_consistentes_1_2_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "ids.csv"
            md_path = Path(tmpdir) / "ids.md"
            call_command(
                "catalogo_identificadores_consistentes_1_2",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertTrue((Path(tmpdir) / "04_controles_identificadores.csv").exists())
            self.assertTrue((Path(tmpdir) / "04_catalogo_sucursales_MAIN.csv").exists())
            self.assertTrue((Path(tmpdir) / "04_catalogo_productos_MAIN.csv").exists())
            self.assertIn("socio_id", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Elemento 4 de 4 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_motor_indicadores_mora_riesgo_1_3_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "kpis_mora.csv"
            md_path = Path(tmpdir) / "kpis_mora.md"
            call_command(
                "motor_indicadores_mora_riesgo_1_3",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("kpi", csv_path.read_text(encoding="utf-8"))
            self.assertIn("Elemento 1 de 4 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_motor_indicadores_dinamica_ahorro_credito_1_3_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = Path(tmpdir) / "kpis_dinamica.csv"
            md_path = Path(tmpdir) / "kpis_dinamica.md"
            call_command(
                "motor_indicadores_dinamica_ahorro_credito_1_3",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            content = csv_path.read_text(encoding="utf-8")
            self.assertIn("rotacion_creditos_180d", content)
            self.assertIn("estabilidad_ahorro_pct", content)
            self.assertIn("Elemento 2 de 4 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_motor_indicadores_respuesta_cobranza_1_3_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ResultadoScoring.objects.create(
                solicitud_id="resp_cob_1",
                socio=self.socio,
                credito=self.credito,
                ingreso_mensual="3000.00",
                deuda_actual="200.00",
                antiguedad_meses=24,
                score="0.78",
                recomendacion="aprobar",
                riesgo="bajo",
                model_version="weighted_score_v1",
            )
            ResultadoMoraTemprana.objects.create(
                credito=self.credito,
                socio=self.socio,
                cuota_estimada="300.00",
                pagos_90d="180.00",
                ratio_pago_90d="0.6000",
                deuda_ingreso_ratio="0.2000",
                prob_mora_30d="0.1200",
                prob_mora_60d="0.1800",
                prob_mora_90d="0.2200",
                alerta=ResultadoMoraTemprana.ALERTA_MEDIA,
                fuente=ResultadoMoraTemprana.FUENTE_BATCH,
                model_version="mora_temprana_test_v2",
            )
            csv_path = Path(tmpdir) / "kpis_respuesta_cobranza.csv"
            md_path = Path(tmpdir) / "kpis_respuesta_cobranza.md"
            call_command(
                "motor_indicadores_respuesta_cobranza_1_3",
                report_csv=str(csv_path),
                report_md=str(md_path),
            )
            self.assertTrue(csv_path.exists())
            self.assertTrue(md_path.exists())
            content = csv_path.read_text(encoding="utf-8")
            self.assertIn("tiempo_respuesta_credito_horas", content)
            self.assertIn("eficiencia_cobranza_pct", content)
            self.assertIn("Elemento 3 de 4 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_motor_indicadores_segmentacion_dataset_1_3_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ResultadoSegmentacionSocio.objects.create(
                socio=self.socio,
                fecha_ejecucion=timezone.localdate(),
                segmento=self.socio.segmento,
                saldo_total="400.00",
                total_movimientos="120.00",
                cantidad_movimientos=1,
                dias_desde_ultimo_movimiento=5,
                total_creditos=1,
                model_version="segmentacion_test_v1",
            )
            ResultadoScoring.objects.create(
                solicitud_id="seg_ds_1",
                socio=self.socio,
                credito=self.credito,
                ingreso_mensual="3000.00",
                deuda_actual="200.00",
                antiguedad_meses=24,
                score="0.80",
                recomendacion="aprobar",
                riesgo="bajo",
                model_version="weighted_score_v1",
            )
            ResultadoMoraTemprana.objects.create(
                credito=self.credito,
                socio=self.socio,
                cuota_estimada="300.00",
                pagos_90d="150.00",
                ratio_pago_90d="0.5000",
                deuda_ingreso_ratio="0.2000",
                prob_mora_30d="0.1200",
                prob_mora_60d="0.1800",
                prob_mora_90d="0.2200",
                alerta=ResultadoMoraTemprana.ALERTA_BAJA,
                fuente=ResultadoMoraTemprana.FUENTE_BATCH,
                model_version="mora_temprana_test_v3",
            )
            kpi_csv = Path(tmpdir) / "kpis_segmentacion.csv"
            dataset_csv = Path(tmpdir) / "dataset_decision.csv"
            md_path = Path(tmpdir) / "kpis_segmentacion.md"
            call_command(
                "motor_indicadores_segmentacion_dataset_1_3",
                report_csv=str(kpi_csv),
                dataset_csv=str(dataset_csv),
                report_md=str(md_path),
            )
            self.assertTrue(kpi_csv.exists())
            self.assertTrue(dataset_csv.exists())
            self.assertTrue(md_path.exists())
            self.assertIn("cobertura_segmentacion_pct", kpi_csv.read_text(encoding="utf-8"))
            dataset_content = dataset_csv.read_text(encoding="utf-8")
            self.assertIn("accion_sugerida", dataset_content)
            self.assertIn("socio_id", dataset_content)
            self.assertIn("Elemento 4 de 4 completado tecnicamente", md_path.read_text(encoding="utf-8"))

    def test_segmentacion_inteligente_socios_1_4_reglas_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            socio_captacion = Socio.objects.create(
                nombre="Socio Captacion",
                email="captacion@test.com",
                telefono="555-0700",
                direccion="Zona Norte",
                segmento=Socio.SEGMENTO_GRAN_AHORRADOR,
            )
            Cuenta.objects.create(
                socio=socio_captacion,
                tipo=Cuenta.TIPO_AHORRO,
                saldo="1800.00",
            )

            report_csv = Path(tmpdir) / "segmentacion_resumen.csv"
            dataset_csv = Path(tmpdir) / "segmentacion_socios.csv"
            report_md = Path(tmpdir) / "segmentacion.md"
            call_command(
                "segmentacion_inteligente_socios_1_4",
                metodo="reglas",
                report_csv=str(report_csv),
                dataset_csv=str(dataset_csv),
                report_md=str(report_md),
            )

            self.assertTrue(report_csv.exists())
            self.assertTrue(dataset_csv.exists())
            self.assertTrue(report_md.exists())
            dataset_content = dataset_csv.read_text(encoding="utf-8")
            self.assertIn("segmento", dataset_content)
            self.assertIn("metodo", dataset_content)
            self.assertIn("Potencial captacion", dataset_content)
            self.assertIn("Segmentacion por reglas de umbrales disponible", report_md.read_text(encoding="utf-8"))

    def test_segmentacion_inteligente_socios_1_4_clustering_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report_csv = Path(tmpdir) / "segmentacion_resumen_cluster.csv"
            dataset_csv = Path(tmpdir) / "segmentacion_socios_cluster.csv"
            report_md = Path(tmpdir) / "segmentacion_cluster.md"
            call_command(
                "segmentacion_inteligente_socios_1_4",
                metodo="clustering",
                clusters=3,
                report_csv=str(report_csv),
                dataset_csv=str(dataset_csv),
                report_md=str(report_md),
            )

            self.assertTrue(report_csv.exists())
            self.assertTrue(dataset_csv.exists())
            self.assertTrue(report_md.exists())
            dataset_content = dataset_csv.read_text(encoding="utf-8")
            self.assertIn("cluster_id", dataset_content)
            self.assertIn(",clustering", dataset_content)
            self.assertIn("Segmentacion estadistica (clustering) disponible por parametro", report_md.read_text(encoding="utf-8"))

    def test_definir_umbrales_segmentacion_1_4_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            thresholds_json = Path(tmpdir) / "umbrales_v2.json"
            report_csv = Path(tmpdir) / "umbrales_v2.csv"
            report_md = Path(tmpdir) / "umbrales_v2.md"
            call_command(
                "definir_umbrales_segmentacion_1_4",
                thresholds_version="segmentacion_1_4_v2",
                aprobado_por="comite_riesgo",
                thresholds_json=str(thresholds_json),
                report_csv=str(report_csv),
                report_md=str(report_md),
            )
            self.assertTrue(thresholds_json.exists())
            self.assertTrue(report_csv.exists())
            self.assertTrue(report_md.exists())
            json_content = thresholds_json.read_text(encoding="utf-8")
            self.assertIn("segmentacion_1_4_v2", json_content)
            self.assertIn("comite_riesgo", json_content)
            self.assertIn("listos_para_credito", json_content)
            self.assertIn("version,segmento,regla,valor", report_csv.read_text(encoding="utf-8"))
            self.assertIn("Punto 2 de 3 completado tecnicamente", report_md.read_text(encoding="utf-8"))

    def test_activar_acciones_campanas_segmentos_1_4_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            segmentacion_csv = Path(tmpdir) / "segmentacion.csv"
            segmentacion_csv.write_text(
                (
                    "socio_id,segmento,cluster_id,ahorro_total,total_creditos,score_promedio,prob_mora_90d,pagos_180d,"
                    "transacciones_180d,monto_promedio_transaccion,variabilidad_ahorro,metodo,thresholds_version\n"
                    "1,Listos para credito,-1,400.00,1,0.8200,0.1200,200.00,4,120.00,0.2000,reglas,segmentacion_1_4_v1\n"
                    "1,Riesgo alto,-1,400.00,1,0.4200,0.7800,50.00,2,70.00,0.9000,reglas,segmentacion_1_4_v1\n"
                ),
                encoding="utf-8",
            )
            summary_csv = Path(tmpdir) / "acciones_resumen.csv"
            assignments_csv = Path(tmpdir) / "acciones_asignaciones.csv"
            report_md = Path(tmpdir) / "acciones.md"

            call_command(
                "activar_acciones_campanas_segmentos_1_4",
                segmentacion_dataset_csv=str(segmentacion_csv),
                summary_csv=str(summary_csv),
                assignments_csv=str(assignments_csv),
                report_md=str(report_md),
            )

            self.assertTrue(summary_csv.exists())
            self.assertTrue(assignments_csv.exists())
            self.assertTrue(report_md.exists())
            self.assertIn("segmento,accion,socios_objetivo", summary_csv.read_text(encoding="utf-8"))
            assignments_content = assignments_csv.read_text(encoding="utf-8")
            self.assertIn("campania_id", assignments_content)
            self.assertIn("alerta_cobranza_preventiva", assignments_content)
            self.assertIn("preaprobacion_credito", assignments_content)
            self.assertIn("Punto 3 de 3 completado tecnicamente", report_md.read_text(encoding="utf-8"))
            self.assertGreaterEqual(Campania.objects.filter(estado=Campania.ESTADO_ACTIVA).count(), 1)

    def test_motor_campanas_colocacion_1_6_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            socio_abandono = Socio.objects.create(
                nombre="Socio Abandono",
                email="abandono@test.com",
                telefono="555-0800",
                direccion="Yuriria Centro",
                segmento=Socio.SEGMENTO_INACTIVO,
            )
            Cuenta.objects.create(
                socio=socio_abandono,
                tipo=Cuenta.TIPO_AHORRO,
                saldo="250.00",
            )

            ResultadoScoring.objects.create(
                solicitud_id="growth_1",
                socio=self.socio,
                credito=self.credito,
                ingreso_mensual="3000.00",
                deuda_actual="200.00",
                antiguedad_meses=24,
                score="0.82",
                recomendacion="aprobar",
                riesgo="bajo",
                model_version="weighted_score_v1",
            )
            ResultadoMoraTemprana.objects.create(
                credito=self.credito,
                socio=self.socio,
                cuota_estimada="300.00",
                pagos_90d="180.00",
                ratio_pago_90d="0.6000",
                deuda_ingreso_ratio="0.2000",
                prob_mora_30d="0.1200",
                prob_mora_60d="0.1800",
                prob_mora_90d="0.2200",
                alerta=ResultadoMoraTemprana.ALERTA_BAJA,
                fuente=ResultadoMoraTemprana.FUENTE_BATCH,
                model_version="mora_temprana_growth_v1",
            )
            Transaccion.objects.create(cuenta=self.cuenta, monto="250.00", tipo=Transaccion.TIPO_RETIRO)

            preaprobados_csv = Path(tmpdir) / "preaprobados.csv"
            renovacion_csv = Path(tmpdir) / "renovacion.csv"
            baja_ahorro_csv = Path(tmpdir) / "baja_ahorro.csv"
            abandono_csv = Path(tmpdir) / "abandono.csv"
            asignacion_csv = Path(tmpdir) / "asignacion.csv"
            contacto_csv = Path(tmpdir) / "contacto.csv"
            seguimiento_csv = Path(tmpdir) / "seguimiento.csv"
            medicion_csv = Path(tmpdir) / "medicion.csv"
            report_md = Path(tmpdir) / "growth.md"

            call_command(
                "motor_campanas_colocacion_1_6",
                preaprobados_csv=str(preaprobados_csv),
                renovacion_csv=str(renovacion_csv),
                baja_ahorro_csv=str(baja_ahorro_csv),
                abandono_csv=str(abandono_csv),
                asignacion_csv=str(asignacion_csv),
                contacto_csv=str(contacto_csv),
                seguimiento_csv=str(seguimiento_csv),
                medicion_csv=str(medicion_csv),
                report_md=str(report_md),
            )

            self.assertTrue(preaprobados_csv.exists())
            self.assertTrue(renovacion_csv.exists())
            self.assertTrue(baja_ahorro_csv.exists())
            self.assertTrue(abandono_csv.exists())
            self.assertTrue(asignacion_csv.exists())
            self.assertTrue(contacto_csv.exists())
            self.assertTrue(seguimiento_csv.exists())
            self.assertTrue(medicion_csv.exists())
            self.assertTrue(report_md.exists())

            self.assertIn("socio_id,sucursal,score", preaprobados_csv.read_text(encoding="utf-8"))
            self.assertIn("socio_id,sucursal,total_creditos", renovacion_csv.read_text(encoding="utf-8"))
            self.assertIn("ratio_baja", baja_ahorro_csv.read_text(encoding="utf-8"))
            self.assertIn(str(socio_abandono.id), abandono_csv.read_text(encoding="utf-8"))
            asignacion_content = asignacion_csv.read_text(encoding="utf-8")
            self.assertIn("ejecutivo_id", asignacion_content)
            self.assertIn("ejec_yur_", asignacion_content)
            self.assertIn("estado_contacto", contacto_csv.read_text(encoding="utf-8"))
            self.assertIn("conversion", seguimiento_csv.read_text(encoding="utf-8"))
            self.assertIn("tasa_conversion_pct", medicion_csv.read_text(encoding="utf-8"))
            self.assertIn("Motor de campanas y colocacion implementado tecnicamente", report_md.read_text(encoding="utf-8"))
            self.assertGreaterEqual(ContactoCampania.objects.count(), 1)
            self.assertGreaterEqual(SeguimientoConversionCampania.objects.count(), 1)

    def test_configurar_catalogo_growth_engine_1_6_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalogo_json = Path(tmpdir) / "catalogo.json"
            report_csv = Path(tmpdir) / "catalogo.csv"
            report_md = Path(tmpdir) / "catalogo.md"
            call_command(
                "configurar_catalogo_growth_engine_1_6",
                catalog_version="growth_engine_catalogo_v2",
                catalogo_json=str(catalogo_json),
                report_csv=str(report_csv),
                report_md=str(report_md),
            )
            self.assertTrue(catalogo_json.exists())
            self.assertTrue(report_csv.exists())
            self.assertTrue(report_md.exists())
            self.assertIn("growth_engine_catalogo_v2", catalogo_json.read_text(encoding="utf-8"))
            self.assertIn("sucursal_nombre", report_csv.read_text(encoding="utf-8"))
            self.assertIn("Punto 1 de 3 completado tecnicamente", report_md.read_text(encoding="utf-8"))

    def test_integrar_canales_crm_growth_engine_1_6_command(self):
        campania = Campania.objects.create(
            nombre="GE Integracion Canales",
            tipo="llamadas",
            fecha_inicio=timezone.localdate(),
            fecha_fin=timezone.localdate() + timedelta(days=30),
            estado=Campania.ESTADO_ACTIVA,
        )
        ContactoCampania.objects.create(
            campania=campania,
            socio=self.socio,
            ejecutivo_id="ejec_test_01",
            canal="telefono",
            estado_contacto=ContactoCampania.ESTADO_PENDIENTE,
        )
        SeguimientoConversionCampania.objects.create(
            campania=campania,
            socio=self.socio,
            lista="preaprobados",
            etapa="seguimiento",
            conversion=False,
            monto_colocado="0.00",
            fecha_evento=timezone.localdate(),
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            config_json = Path(tmpdir) / "canales.json"
            dispatch_jsonl = Path(tmpdir) / "dispatch.jsonl"
            feedback_csv = Path(tmpdir) / "feedback.csv"
            report_csv = Path(tmpdir) / "medicion.csv"
            report_md = Path(tmpdir) / "integracion.md"
            config_json.write_text(
                json.dumps(
                    {
                        "version": "canales_crm_test_v1",
                        "providers": {"telefono": {"sistema": "crm_callcenter_test", "canal": "llamada"}},
                        "default_provider": {"sistema": "crm_default_test", "canal": "general"},
                    },
                    ensure_ascii=True,
                ),
                encoding="utf-8",
            )

            call_command(
                "integrar_canales_crm_growth_engine_1_6",
                config_json=str(config_json),
                dispatch_jsonl=str(dispatch_jsonl),
                feedback_csv=str(feedback_csv),
                report_csv=str(report_csv),
                report_md=str(report_md),
            )

            self.assertTrue(dispatch_jsonl.exists())
            self.assertTrue(feedback_csv.exists())
            self.assertTrue(report_csv.exists())
            self.assertTrue(report_md.exists())
            self.assertIn("crm_callcenter_test", dispatch_jsonl.read_text(encoding="utf-8"))
            self.assertIn("origen_feedback", feedback_csv.read_text(encoding="utf-8"))
            self.assertIn("config_version", report_csv.read_text(encoding="utf-8"))
            self.assertIn("Punto 3 de 3 completado tecnicamente", report_md.read_text(encoding="utf-8"))

            contacto = ContactoCampania.objects.get(campania=campania, socio=self.socio)
            self.assertEqual(contacto.estado_contacto, ContactoCampania.ESTADO_CONTACTADO)
            seg = SeguimientoConversionCampania.objects.get(campania=campania, socio=self.socio, lista="preaprobados")
            self.assertTrue(seg.conversion)

    def test_alertas_tempranas_early_warning_1_7_command(self):
        self.socio.direccion = "Yuriria Centro"
        self.socio.save(update_fields=["direccion"])
        socio2 = Socio.objects.create(
            nombre="Socio Riesgo",
            email="riesgo.test@example.com",
            telefono="555-0900",
            direccion="Yuriria Barrio Alto",
            segmento=Socio.SEGMENTO_INACTIVO,
        )
        credito2 = Credito.objects.create(
            socio=socio2,
            monto="6000.00",
            plazo=24,
            ingreso_mensual="5000.00",
            deuda_actual="5000.00",
            antiguedad_meses=5,
            estado="solicitado",
        )
        HistorialPago.objects.create(credito=self.credito, fecha=timezone.localdate() - timedelta(days=40), monto="500.00")
        HistorialPago.objects.create(credito=self.credito, fecha=timezone.localdate() - timedelta(days=10), monto="50.00")
        Transaccion.objects.create(cuenta=self.cuenta, monto="320.00", tipo=Transaccion.TIPO_RETIRO)
        ResultadoMoraTemprana.objects.create(
            credito=self.credito,
            socio=self.socio,
            cuota_estimada="300.00",
            pagos_90d="60.00",
            ratio_pago_90d="0.2000",
            deuda_ingreso_ratio="0.2000",
            prob_mora_30d="0.3200",
            prob_mora_60d="0.5200",
            prob_mora_90d="0.7200",
            alerta=ResultadoMoraTemprana.ALERTA_ALTA,
            fuente=ResultadoMoraTemprana.FUENTE_BATCH,
            model_version="mora_temprana_ews_v1",
        )
        ResultadoMoraTemprana.objects.create(
            credito=credito2,
            socio=socio2,
            cuota_estimada="500.00",
            pagos_90d="0.00",
            ratio_pago_90d="0.0000",
            deuda_ingreso_ratio="1.0000",
            prob_mora_30d="0.4200",
            prob_mora_60d="0.6200",
            prob_mora_90d="0.8200",
            alerta=ResultadoMoraTemprana.ALERTA_ALTA,
            fuente=ResultadoMoraTemprana.FUENTE_BATCH,
            model_version="mora_temprana_ews_v2",
        )
        ContactoCampania.objects.create(
            campania=Campania.objects.order_by("id").first(),
            socio=self.socio,
            ejecutivo_id="ejec_yur_01",
            canal="telefono",
            estado_contacto=ContactoCampania.ESTADO_PENDIENTE,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            alertas_csv = Path(tmpdir) / "ews_alertas.csv"
            semaforos_csv = Path(tmpdir) / "ews_semaforos.csv"
            notify_jsonl = Path(tmpdir) / "ews_notify.jsonl"
            report_md = Path(tmpdir) / "ews.md"
            call_command(
                "alertas_tempranas_early_warning_1_7",
                report_csv=str(alertas_csv),
                semaforos_csv=str(semaforos_csv),
                notify_jsonl=str(notify_jsonl),
                report_md=str(report_md),
            )

            self.assertTrue(alertas_csv.exists())
            self.assertTrue(semaforos_csv.exists())
            self.assertTrue(notify_jsonl.exists())
            self.assertTrue(report_md.exists())
            alerts_content = alertas_csv.read_text(encoding="utf-8")
            self.assertIn("tipo_alerta", alerts_content)
            self.assertIn("caida_fuerte_ahorro", alerts_content)
            self.assertIn("deterioro_cobertura", alerts_content)
            self.assertIn("primer_atraso_mora_temprana", alerts_content)
            self.assertIn("concentracion_mora_sucursal", alerts_content)
            sem_content = semaforos_csv.read_text(encoding="utf-8")
            self.assertIn("semaforo", sem_content)
            notify_content = notify_jsonl.read_text(encoding="utf-8")
            self.assertIn("\"canal\": \"email\"", notify_content)
            self.assertIn("Early Warning System implementado tecnicamente", report_md.read_text(encoding="utf-8"))
            self.assertGreaterEqual(AlertaMonitoreo.objects.count(), 1)

    def test_dashboard_semaforos_endpoint(self):
        self.client.force_authenticate(user=self.user)
        AlertaMonitoreo.objects.create(
            ambito="riesgo",
            metrica="deterioro_cobertura",
            valor="35.00",
            umbral="50.00",
            severidad=AlertaMonitoreo.SEVERIDAD_CRITICAL,
            escalamiento="comite_riesgo_2h",
            estado=AlertaMonitoreo.ESTADO_ACTIVA,
            detalle="Cobertura por debajo del umbral",
        )
        AlertaMonitoreo.objects.create(
            ambito="cobranza",
            metrica="primer_atraso_mora_temprana",
            valor="5.00",
            umbral="2.00",
            severidad=AlertaMonitoreo.SEVERIDAD_WARN,
            escalamiento="supervisor_24h",
            estado=AlertaMonitoreo.ESTADO_ACTIVA,
            detalle="Atrasos por arriba del umbral",
        )
        response = self.client.get("/api/analitica/ml/dashboard/semaforos/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("resumen", response.data)
        self.assertIn("semaforos", response.data)
        self.assertGreaterEqual(response.data["resumen"]["rojo"], 1)
        self.assertIn("ambito", response.data["semaforos"][0])
        self.assertIn("metrica", response.data["semaforos"][0])

        filtered = self.client.get("/api/analitica/ml/dashboard/semaforos/?semaforo=Rojo&ambito=riesgo&q=cobertura")
        self.assertEqual(filtered.status_code, status.HTTP_200_OK)
        self.assertEqual(filtered.data["resumen"]["total"], 1)
        self.assertEqual(len(filtered.data["semaforos"]), 1)
        self.assertEqual(filtered.data["semaforos"][0]["ambito"], "riesgo")
        self.assertEqual(filtered.data["semaforos"][0]["semaforo"], "Rojo")

        csv_response = self.client.get("/api/analitica/ml/dashboard/semaforos/?semaforo=Rojo&export=csv")
        self.assertEqual(csv_response.status_code, status.HTTP_200_OK)
        self.assertIn("text/csv", csv_response["Content-Type"])
        csv_content = csv_response.content.decode("utf-8")
        self.assertIn("componente,ambito,metrica,semaforo,estado,valor,umbral,fecha_evento", csv_content)
        self.assertIn("riesgo:deterioro_cobertura", csv_content)

    def test_dashboard_ejecutivos_operativos_endpoint(self):
        self.client.force_authenticate(user=self.user)
        ResultadoScoring.objects.create(
            solicitud_id="dashboard_1",
            socio=self.socio,
            credito=self.credito,
            ingreso_mensual="3000.00",
            deuda_actual="200.00",
            antiguedad_meses=24,
            score="0.79",
            recomendacion="aprobar",
            riesgo="bajo",
            model_version="weighted_score_v1",
        )
        ResultadoMoraTemprana.objects.create(
            credito=self.credito,
            socio=self.socio,
            cuota_estimada="300.00",
            pagos_90d="100.00",
            ratio_pago_90d="0.5500",
            deuda_ingreso_ratio="0.2000",
            prob_mora_30d="0.2500",
            prob_mora_60d="0.3500",
            prob_mora_90d="0.4500",
            alerta=ResultadoMoraTemprana.ALERTA_MEDIA,
            fuente=ResultadoMoraTemprana.FUENTE_BATCH,
            model_version="mora_temprana_dash_v1",
        )
        response = self.client.get("/api/analitica/ml/dashboard/ejecutivos-operativos/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("salud_cartera", response.data)
        self.assertIn("colocacion", response.data)
        self.assertIn("captacion", response.data)
        self.assertIn("riesgo", response.data)
        self.assertIn("sucursales", response.data)
        self.assertIn("eficiencia_cobranza", response.data)
        self.assertIn("actualizacion", response.data)
        self.assertIn("tendencias", response.data)
        self.assertIn("mensual", response.data["tendencias"])
        self.assertIn("trimestral", response.data["tendencias"])
        self.assertIn("salud_cartera_imor_pct", response.data["tendencias"]["mensual"])
        self.assertEqual(response.data["acceso"]["vista"], "consejo_gerencia")
        self.assertTrue(response.data["acceso"]["drilldown_habilitado"])
        self.assertIn("imor_pct", response.data["salud_cartera"])
        self.assertIn("meta_imor_pct", response.data["salud_cartera"])
        self.assertIn("meta_estabilidad_ahorro_pct", response.data["captacion"])
        self.assertEqual(len(response.data["sucursales"]), 3)

        drilldown = self.client.get("/api/analitica/ml/dashboard/ejecutivos-operativos/?sucursal=Yuriria&detalle=1")
        self.assertEqual(drilldown.status_code, status.HTTP_200_OK)
        self.assertIn("drilldown", drilldown.data)
        self.assertEqual(drilldown.data["drilldown"]["sucursal"], "Yuriria")
        self.assertIn("creditos_recientes", drilldown.data["drilldown"])
        self.assertIn("alertas_mora", drilldown.data["drilldown"])

    def test_dashboard_ejecutivos_operativos_endpoint_role_scope_auditor(self):
        auditor = User.objects.create_user(username="auditor_dash", password="secret123")
        auditor.profile.rol = "auditor"
        auditor.profile.save(update_fields=["rol"])
        self.client.force_authenticate(user=auditor)

        response = self.client.get("/api/analitica/ml/dashboard/ejecutivos-operativos/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["acceso"]["vista"], "ejecutivo")
        self.assertFalse(response.data["acceso"]["drilldown_habilitado"])
        self.assertNotIn("riesgo", response.data)
        self.assertNotIn("eficiencia_cobranza", response.data)
        self.assertNotIn("riesgo_cobertura_pct", response.data["tendencias"]["mensual"])
        self.assertNotIn("cobranza_eficiencia_pct", response.data["tendencias"]["trimestral"])

        drilldown = self.client.get("/api/analitica/ml/dashboard/ejecutivos-operativos/?sucursal=Yuriria&detalle=1")
        self.assertEqual(drilldown.status_code, status.HTTP_200_OK)
        self.assertNotIn("drilldown", drilldown.data)

    def test_dashboards_ejecutivos_operativos_1_8_command(self):
        ResultadoScoring.objects.create(
            solicitud_id="db_1",
            socio=self.socio,
            credito=self.credito,
            ingreso_mensual="3000.00",
            deuda_actual="200.00",
            antiguedad_meses=24,
            score="0.81",
            recomendacion="aprobar",
            riesgo="bajo",
            model_version="weighted_score_v1",
        )
        ResultadoMoraTemprana.objects.create(
            credito=self.credito,
            socio=self.socio,
            cuota_estimada="300.00",
            pagos_90d="100.00",
            ratio_pago_90d="0.3300",
            deuda_ingreso_ratio="0.2000",
            prob_mora_30d="0.2500",
            prob_mora_60d="0.3500",
            prob_mora_90d="0.4500",
            alerta=ResultadoMoraTemprana.ALERTA_MEDIA,
            fuente=ResultadoMoraTemprana.FUENTE_BATCH,
            model_version="mora_temprana_dash_v1",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            salud = Path(tmpdir) / "salud.csv"
            coloc = Path(tmpdir) / "coloc.csv"
            capt = Path(tmpdir) / "capt.csv"
            riesgo = Path(tmpdir) / "riesgo.csv"
            suc = Path(tmpdir) / "suc.csv"
            cob = Path(tmpdir) / "cob.csv"
            sem = Path(tmpdir) / "sem.csv"
            md = Path(tmpdir) / "dash.md"
            call_command(
                "dashboards_ejecutivos_operativos_1_8",
                salud_cartera_csv=str(salud),
                colocacion_csv=str(coloc),
                captacion_csv=str(capt),
                riesgo_csv=str(riesgo),
                sucursales_csv=str(suc),
                cobranza_csv=str(cob),
                semaforos_csv=str(sem),
                report_md=str(md),
            )
            self.assertTrue(salud.exists())
            self.assertTrue(coloc.exists())
            self.assertTrue(capt.exists())
            self.assertTrue(riesgo.exists())
            self.assertTrue(suc.exists())
            self.assertTrue(cob.exists())
            self.assertTrue(sem.exists())
            self.assertTrue(md.exists())
            self.assertIn("imor_pct", salud.read_text(encoding="utf-8"))
            self.assertIn("cumplimiento_meta_pct", coloc.read_text(encoding="utf-8"))
            self.assertIn("estabilidad_ahorro_pct", capt.read_text(encoding="utf-8"))
            self.assertIn("cobertura_pct", riesgo.read_text(encoding="utf-8"))
            self.assertIn("ranking", suc.read_text(encoding="utf-8"))
            self.assertIn("eficiencia_cobranza_pct", cob.read_text(encoding="utf-8"))
            self.assertIn("semaforo", sem.read_text(encoding="utf-8"))
            self.assertIn("Dashboards ejecutivos y operativos implementados tecnicamente", md.read_text(encoding="utf-8"))

    def test_actualizar_dashboards_programado_1_8_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            estado_json = Path(tmpdir) / "estado_actualizacion.json"
            call_command(
                "actualizar_dashboards_programado_1_8",
                estado_json=str(estado_json),
                fuente_ejecucion="test",
            )
            self.assertTrue(estado_json.exists())
            payload = json.loads(estado_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["modulo"], "dashboards_1_8")
            self.assertEqual(payload["estado"], "ok")
            self.assertEqual(payload["fuente_ejecucion"], "test")
            self.assertIn("ultima_actualizacion_utc", payload)

    def test_cerrar_uat_dashboards_1_8_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            report_csv = Path(tmpdir) / "uat.csv"
            evidencias_jsonl = Path(tmpdir) / "uat.jsonl"
            report_md = Path(tmpdir) / "uat.md"
            call_command(
                "cerrar_uat_dashboards_1_8",
                report_csv=str(report_csv),
                evidencias_jsonl=str(evidencias_jsonl),
                report_md=str(report_md),
            )
            self.assertTrue(report_csv.exists())
            self.assertTrue(evidencias_jsonl.exists())
            self.assertTrue(report_md.exists())
            csv_content = report_csv.read_text(encoding="utf-8")
            self.assertIn("criterio,resultado,evidencia,estado", csv_content)
            self.assertIn("Disponibilidad de 6 tableros ejecutivos-operativos", csv_content)
            jsonl_content = evidencias_jsonl.read_text(encoding="utf-8")
            self.assertIn("\"modulo\": \"dashboards_1_8\"", jsonl_content)
            self.assertIn("Acta UAT Dashboards 1.8", report_md.read_text(encoding="utf-8"))
