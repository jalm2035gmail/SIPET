from django.contrib import admin

from .models import Credito, HistorialPago


@admin.register(Credito)
class CreditoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "socio",
        "monto",
        "plazo",
        "ingreso_mensual",
        "deuda_actual",
        "antiguedad_meses",
        "estado",
        "fecha_creacion",
    )
    list_filter = ("estado",)
    search_fields = ("socio__nombre", "socio__email")


@admin.register(HistorialPago)
class HistorialPagoAdmin(admin.ModelAdmin):
    list_display = ("id", "credito", "fecha", "monto")
    search_fields = ("credito__socio__nombre", "credito__socio__email")
