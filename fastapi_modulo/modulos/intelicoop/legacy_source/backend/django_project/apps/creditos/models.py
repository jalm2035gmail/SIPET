from django.db import models

from apps.socios.models import Socio


class Credito(models.Model):
    ESTADO_SOLICITADO = "solicitado"
    ESTADO_APROBADO = "aprobado"
    ESTADO_RECHAZADO = "rechazado"
    ESTADO_CHOICES = [
        (ESTADO_SOLICITADO, "Solicitado"),
        (ESTADO_APROBADO, "Aprobado"),
        (ESTADO_RECHAZADO, "Rechazado"),
    ]

    socio = models.ForeignKey(Socio, on_delete=models.CASCADE, related_name="creditos")
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    plazo = models.PositiveIntegerField(help_text="Plazo en meses")
    ingreso_mensual = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deuda_actual = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    antiguedad_meses = models.PositiveIntegerField(default=0)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_SOLICITADO)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "creditos"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"Credito {self.id} - {self.socio.nombre}"


class HistorialPago(models.Model):
    credito = models.ForeignKey(Credito, on_delete=models.CASCADE, related_name="historial_pagos")
    fecha = models.DateField()
    monto = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "historial_pagos"
        ordering = ["-fecha", "-id"]

    def __str__(self) -> str:
        return f"Pago {self.monto} - Credito {self.credito_id}"
