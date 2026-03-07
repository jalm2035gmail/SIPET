from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.socios.models import Socio

from .models import Cuenta, Transaccion


class AhorrosApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="ahorros_user", password="secret123")
        self.socio = Socio.objects.create(
            nombre="Socio Ahorros",
            email="socio.ahorros@mail.com",
            telefono="555-0300",
            direccion="Direccion Ahorros",
        )
        self.cuenta = Cuenta.objects.create(socio=self.socio, tipo="ahorro", saldo="120.00")
        Transaccion.objects.create(cuenta=self.cuenta, monto="50.00", tipo="deposito")

        self.cuentas_url = reverse("ahorro_cuentas_list")
        self.movimientos_url = reverse("ahorro_movimientos_list")
        self.aperturar_url = reverse("ahorro_aperturar")

    def test_get_cuentas_requires_authentication(self):
        response = self.client.get(self.cuentas_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_cuentas_returns_data_for_authenticated_user(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.cuentas_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["socio"], self.socio.id)

    def test_get_movimientos_requires_authentication(self):
        response = self.client.get(self.movimientos_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_movimientos_returns_data_for_authenticated_user(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.movimientos_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["cuenta"], self.cuenta.id)

    def test_post_aperturar_requires_authentication(self):
        payload = {"socio": self.socio.id, "tipo": "ahorro", "saldo": "0.00"}
        response = self.client.post(self.aperturar_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_post_aperturar_creates_account(self):
        self.client.force_authenticate(user=self.user)
        payload = {"socio": self.socio.id, "tipo": "aportacion", "saldo": "300.00"}
        response = self.client.post(self.aperturar_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Cuenta.objects.count(), 2)
        self.assertEqual(response.data["tipo"], "aportacion")

    def test_post_aperturar_rejects_negative_saldo(self):
        self.client.force_authenticate(user=self.user)
        payload = {"socio": self.socio.id, "tipo": "ahorro", "saldo": "-1.00"}
        response = self.client.post(self.aperturar_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("saldo", response.data)
