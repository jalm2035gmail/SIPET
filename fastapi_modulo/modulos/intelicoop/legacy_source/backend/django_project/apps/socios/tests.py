from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Socio


class SocioListApiTests(APITestCase):
    def setUp(self):
        self.url = reverse("socio_list")
        self.user = User.objects.create_user(username="sociosuser", password="secret123")
        Socio.objects.create(
            nombre="Ana Perez",
            email="ana@socios.com",
            telefono="555-0101",
            direccion="Dir 1",
            segmento="hormiga",
        )
        Socio.objects.create(
            nombre="Luis Gomez",
            email="luis@socios.com",
            telefono="555-0102",
            direccion="Dir 2",
            segmento="gran_ahorrador",
        )

    def test_get_socios_requires_authentication(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_socios_returns_list_for_authenticated_user(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertIn("segmento", response.data[0])
        self.assertIn(response.data[0]["segmento"], {"hormiga", "gran_ahorrador", "inactivo"})
