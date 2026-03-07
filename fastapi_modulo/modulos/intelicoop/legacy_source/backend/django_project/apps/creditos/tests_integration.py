from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from apps.socios.models import Socio


class Fase2CreditoFlowIntegrationTests(APITestCase):
    def setUp(self):
        self.user_password = "secret12345"
        self.user = User.objects.create_user(
            username="fase2tester",
            email="fase2@test.com",
            password=self.user_password,
        )
        self.socio = Socio.objects.create(
            nombre="Socio Fase 2",
            email="socio.fase2@mail.com",
            telefono="555-0200",
            direccion="Direccion Fase 2",
        )

    def _authenticate_with_jwt(self):
        login_response = self.client.post(
            "/api/auth/login/",
            {"username": self.user.email, "password": self.user_password},
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", login_response.data)
        token = login_response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_full_authenticated_credit_flow(self):
        # Guard: endpoints must reject anonymous users.
        anonymous_response = self.client.get("/api/creditos/")
        self.assertEqual(anonymous_response.status_code, status.HTTP_401_UNAUTHORIZED)

        self._authenticate_with_jwt()

        socios_response = self.client.get("/api/socios/")
        self.assertEqual(socios_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(socios_response.data), 1)

        create_payload = {
            "socio": self.socio.id,
            "monto": "2500.00",
            "plazo": 18,
            "ingreso_mensual": "4200.00",
            "deuda_actual": "450.00",
            "antiguedad_meses": 36,
            "estado": "solicitado",
        }
        create_response = self.client.post("/api/creditos/", create_payload, format="json")
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        credito_id = create_response.data["id"]

        detail_response = self.client.get(f"/api/creditos/{credito_id}/")
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["estado"], "solicitado")

        update_status_response = self.client.patch(
            f"/api/creditos/{credito_id}/",
            {"estado": "aprobado"},
            format="json",
        )
        self.assertEqual(update_status_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_status_response.data["estado"], "aprobado")

        pago_response = self.client.post(
            "/api/creditos/pagos/",
            {"credito": credito_id, "fecha": "2026-02-17", "monto": "180.00"},
            format="json",
        )
        self.assertEqual(pago_response.status_code, status.HTTP_201_CREATED)

        pagos_list_response = self.client.get("/api/creditos/pagos/")
        self.assertEqual(pagos_list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(pagos_list_response.data), 1)
        self.assertEqual(pagos_list_response.data[0]["credito"], credito_id)

        delete_response = self.client.delete(f"/api/creditos/{credito_id}/")
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

        deleted_detail_response = self.client.get(f"/api/creditos/{credito_id}/")
        self.assertEqual(deleted_detail_response.status_code, status.HTTP_404_NOT_FOUND)
