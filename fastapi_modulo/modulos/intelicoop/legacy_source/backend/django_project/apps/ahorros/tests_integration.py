from pathlib import Path
import sys

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from apps.socios.models import Socio

from .models import Cuenta, Transaccion


class Fase3AhorrosFlowIntegrationTests(APITestCase):
    def setUp(self):
        self.password = "secret12345"
        self.user = User.objects.create_user(
            username="fase3tester",
            email="fase3@test.com",
            password=self.password,
        )
        self.socio = Socio.objects.create(
            nombre="Socio Segmentacion",
            email="segmentacion@socios.com",
            telefono="555-0400",
            direccion="Direccion Segmentacion",
            segmento=Socio.SEGMENTO_INACTIVO,
        )

    def _authenticate_with_jwt(self):
        login_response = self.client.post(
            "/api/auth/login/",
            {"username": self.user.email, "password": self.password},
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        token = login_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_phase3_flow_ahorros_segmentacion(self):
        # Guard: ahorros should reject anonymous users.
        anonymous = self.client.get("/api/ahorros/cuentas/")
        self.assertEqual(anonymous.status_code, status.HTTP_401_UNAUTHORIZED)

        self._authenticate_with_jwt()

        apertura_response = self.client.post(
            "/api/ahorros/aperturar/",
            {"socio": self.socio.id, "tipo": "ahorro", "saldo": "250.00"},
            format="json",
        )
        self.assertEqual(apertura_response.status_code, status.HTTP_201_CREATED)
        cuenta_id = apertura_response.data["id"]

        cuenta = Cuenta.objects.get(id=cuenta_id)
        Transaccion.objects.create(cuenta=cuenta, monto="75.00", tipo="deposito")

        cuentas_response = self.client.get("/api/ahorros/cuentas/")
        self.assertEqual(cuentas_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(cuentas_response.data), 1)

        movimientos_response = self.client.get("/api/ahorros/movimientos/")
        self.assertEqual(movimientos_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(movimientos_response.data), 1)

        # Run nightly segmentation pipeline (ORM mode) and verify socio.segmento update.
        root_dir = Path(__file__).resolve().parents[4]
        if str(root_dir) not in sys.path:
            sys.path.insert(0, str(root_dir))

        from data_pipelines.spark_jobs.segmentacion_socios import ejecutar_segmentacion

        ejecutar_segmentacion(dry_run=False, engine="orm")
        self.socio.refresh_from_db()
        self.assertEqual(self.socio.segmento, Socio.SEGMENTO_HORMIGA)

        socios_response = self.client.get("/api/socios/")
        self.assertEqual(socios_response.status_code, status.HTTP_200_OK)
        self.assertEqual(socios_response.data[0]["segmento"], Socio.SEGMENTO_HORMIGA)
