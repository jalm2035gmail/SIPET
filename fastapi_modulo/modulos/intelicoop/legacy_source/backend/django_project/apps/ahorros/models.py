from django.db import models

from apps.socios.models import Socio


class Cuenta(models.Model):
    TIPO_AHORRO = "ahorro"
    TIPO_APORTACION = "aportacion"
    TIPO_CHOICES = [
        (TIPO_AHORRO, "Ahorro"),
        (TIPO_APORTACION, "Aportacion"),
    ]

    socio = models.ForeignKey(Socio, on_delete=models.CASCADE, related_name="cuentas")
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default=TIPO_AHORRO)
    saldo = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "cuentas"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"Cuenta {self.id} - {self.socio.nombre}"


class Transaccion(models.Model):
    TIPO_DEPOSITO = "deposito"
    TIPO_RETIRO = "retiro"
    TIPO_CHOICES = [
        (TIPO_DEPOSITO, "Deposito"),
        (TIPO_RETIRO, "Retiro"),
    ]

    cuenta = models.ForeignKey(Cuenta, on_delete=models.CASCADE, related_name="transacciones")
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "transacciones"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.tipo} - {self.monto} (Cuenta {self.cuenta_id})"
