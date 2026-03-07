from django.contrib import admin

from .models import Cuenta, Transaccion


@admin.register(Cuenta)
class CuentaAdmin(admin.ModelAdmin):
    list_display = ("id", "socio", "tipo", "saldo", "fecha_creacion")
    list_filter = ("tipo",)
    search_fields = ("socio__nombre", "socio__email")


@admin.register(Transaccion)
class TransaccionAdmin(admin.ModelAdmin):
    list_display = ("id", "cuenta", "tipo", "monto", "fecha")
    list_filter = ("tipo",)
    search_fields = ("cuenta__socio__nombre", "cuenta__socio__email")
