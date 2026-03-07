from django.contrib import admin

from .models import Socio


@admin.register(Socio)
class SocioAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "email", "telefono", "fecha_registro")
    search_fields = ("nombre", "email", "telefono")
