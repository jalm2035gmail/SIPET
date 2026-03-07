from django.db import models


class Socio(models.Model):
    SEGMENTO_HORMIGA = "hormiga"
    SEGMENTO_GRAN_AHORRADOR = "gran_ahorrador"
    SEGMENTO_INACTIVO = "inactivo"
    SEGMENTO_CHOICES = [
        (SEGMENTO_HORMIGA, "Ahorrador Hormiga"),
        (SEGMENTO_GRAN_AHORRADOR, "Gran Ahorrador"),
        (SEGMENTO_INACTIVO, "Inactivo"),
    ]

    nombre = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=30)
    direccion = models.CharField(max_length=255)
    segmento = models.CharField(max_length=30, choices=SEGMENTO_CHOICES, default=SEGMENTO_INACTIVO)
    fecha_registro = models.DateField(auto_now_add=True)

    class Meta:
        db_table = "socios"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.nombre} ({self.email})"
