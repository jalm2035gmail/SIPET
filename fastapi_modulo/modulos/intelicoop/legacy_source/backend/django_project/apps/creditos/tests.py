from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.socios.models import Socio

from .models import Credito


class CreditoListApiTests(APITestCase):
    def setUp(self):
        self.url = reverse("credito_list_create")
        self.user = User.objects.create_user(username="tester", email="tester@mail.com", password="secret123")
        self.socio = Socio.objects.create(
            nombre="Socio Demo",
            email="socio@mail.com",
            telefono="000000",
            direccion="Direccion demo",
        )
        Credito.objects.create(
            socio=self.socio,
            monto=1000,
            plazo=12,
            ingreso_mensual=1500,
            deuda_actual=200,
            antiguedad_meses=24,
        )

    def test_get_creditos_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_creditos_returns_list_for_authenticated_user(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["monto"], "1000.00")


class CreditoCreateApiTests(APITestCase):
    def setUp(self):
        self.url = reverse("credito_list_create")
        self.user = User.objects.create_user(username="creator", email="creator@mail.com", password="secret123")
        self.socio = Socio.objects.create(
            nombre="Socio Crear",
            email="socio.crear@mail.com",
            telefono="111111",
            direccion="Direccion crear",
        )

    def test_post_credito_requires_authentication(self):
        payload = {
            "socio": self.socio.id,
            "monto": "2000.00",
            "plazo": 18,
            "ingreso_mensual": "2500.00",
            "deuda_actual": "400.00",
            "antiguedad_meses": 36,
            "estado": "solicitado",
        }
        response = self.client.post(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_post_credito_creates_record(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "socio": self.socio.id,
            "monto": "2000.00",
            "plazo": 18,
            "ingreso_mensual": "2500.00",
            "deuda_actual": "400.00",
            "antiguedad_meses": 36,
            "estado": "solicitado",
        }
        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Credito.objects.count(), 1)
        self.assertEqual(Credito.objects.first().estado, "solicitado")

    def test_post_credito_rejects_invalid_payload(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "socio": self.socio.id,
            "monto": "-50.00",
            "plazo": 0,
            "ingreso_mensual": "1000.00",
            "deuda_actual": "1200.00",
            "antiguedad_meses": -2,
            "estado": "solicitado",
        }
        response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("monto", response.data)


class CreditoDetailApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="detail", email="detail@mail.com", password="secret123")
        self.socio = Socio.objects.create(
            nombre="Socio Detail",
            email="socio.detail@mail.com",
            telefono="222222",
            direccion="Direccion detail",
        )
        self.credito = Credito.objects.create(
            socio=self.socio,
            monto=3200,
            plazo=24,
            ingreso_mensual=4100,
            deuda_actual=500,
            antiguedad_meses=48,
        )
        self.url = reverse("credito_detail", args=[self.credito.id])

    def test_get_credito_detail_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_credito_detail_returns_data_when_authenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.credito.id)
        self.assertEqual(response.data["estado"], "solicitado")

    def test_get_credito_detail_returns_404_for_missing_id(self):
        self.client.force_authenticate(user=self.user)
        missing_url = reverse("credito_detail", args=[999999])
        response = self.client.get(missing_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_put_credito_detail_requires_authentication(self):
        payload = {
            "socio": self.socio.id,
            "monto": "3500.00",
            "plazo": 30,
            "ingreso_mensual": "4500.00",
            "deuda_actual": "700.00",
            "antiguedad_meses": 60,
            "estado": "aprobado",
        }
        response = self.client.put(self.url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_put_credito_detail_updates_record(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "socio": self.socio.id,
            "monto": "3500.00",
            "plazo": 30,
            "ingreso_mensual": "4500.00",
            "deuda_actual": "700.00",
            "antiguedad_meses": 60,
            "estado": "aprobado",
        }
        response = self.client.put(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.credito.refresh_from_db()
        self.assertEqual(str(self.credito.monto), "3500.00")
        self.assertEqual(self.credito.estado, "aprobado")

    def test_put_credito_detail_rejects_invalid_payload(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "socio": self.socio.id,
            "monto": "-10.00",
            "plazo": 0,
            "ingreso_mensual": "1200.00",
            "deuda_actual": "1500.00",
            "antiguedad_meses": -5,
            "estado": "aprobado",
        }
        response = self.client.put(self.url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("monto", response.data)

    def test_delete_credito_detail_requires_authentication(self):
        response = self.client.delete(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_delete_credito_detail_removes_record(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Credito.objects.filter(id=self.credito.id).exists())

    def test_delete_credito_detail_returns_404_for_missing_id(self):
        self.client.force_authenticate(user=self.user)
        missing_url = reverse("credito_detail", args=[999999])
        response = self.client.delete(missing_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
