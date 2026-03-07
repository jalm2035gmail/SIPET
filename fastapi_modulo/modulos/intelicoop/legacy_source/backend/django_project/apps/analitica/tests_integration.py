from unittest.mock import patch

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from apps.creditos.models import Credito
from apps.socios.models import Socio

from .models import ResultadoScoring


class Fase3AnaliticaFlowIntegrationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="integracion_analitica", password="secret123")
        self.user.profile.rol = "administrador"
        self.user.profile.save(update_fields=["rol"])
        self.client.force_authenticate(user=self.user)

        self.socio = Socio.objects.create(
            nombre="Socio Integracion",
            email="socio.integracion@test.com",
            telefono="555-0700",
            direccion="Direccion Integracion",
        )
        self.credito = Credito.objects.create(
            socio=self.socio,
            monto="2000.00",
            plazo=18,
            ingreso_mensual="3200.00",
            deuda_actual="200.00",
            antiguedad_meses=20,
            estado="solicitado",
        )

    @patch("apps.analitica.views._call_fastapi_scoring")
    def test_scoring_flow_integration(self, mock_scoring):
        mock_scoring.return_value = {"score": 0.79, "recomendacion": "evaluar", "riesgo": "medio"}

        eval_response = self.client.post(
            "/api/analitica/ml/scoring/evaluar/",
            {
                "persist": True,
                "solicitud_id": f"credito_{self.credito.id}",
                "credito": self.credito.id,
                "socio": self.socio.id,
                "ingreso_mensual": "3200.00",
                "deuda_actual": "200.00",
                "antiguedad_meses": 20,
                "model_version": "weighted_score_v1",
            },
            format="json",
        )
        self.assertEqual(eval_response.status_code, status.HTTP_200_OK)
        self.assertTrue(eval_response.data["persisted"])

        self.assertEqual(ResultadoScoring.objects.count(), 1)

        by_solicitud = self.client.get(f"/api/analitica/ml/scoring/credito_{self.credito.id}/")
        self.assertEqual(by_solicitud.status_code, status.HTTP_200_OK)
        self.assertEqual(by_solicitud.data["socio"], self.socio.id)

        by_socio = self.client.get(f"/api/analitica/ml/scoring/socio/{self.socio.id}/")
        self.assertEqual(by_socio.status_code, status.HTTP_200_OK)
        self.assertEqual(len(by_socio.data), 1)

        resumen = self.client.get("/api/analitica/ml/scoring/resumen/")
        self.assertEqual(resumen.status_code, status.HTTP_200_OK)
        self.assertEqual(resumen.data["total_inferencias"], 1)
