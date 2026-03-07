from django.contrib import admin

from .models import (
    AlertaMonitoreo,
    Campania,
    ContactoCampania,
    EjecucionPipeline,
    Prospecto,
    ReglaAsociacionProducto,
    ResultadoMoraTemprana,
    ResultadoSegmentacionSocio,
    SeguimientoConversionCampania,
)


@admin.register(Campania)
class CampaniaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "tipo", "fecha_inicio", "fecha_fin", "estado")
    list_filter = ("estado", "tipo")
    search_fields = ("nombre", "tipo")


@admin.register(Prospecto)
class ProspectoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "telefono", "fuente", "score_propension")
    list_filter = ("fuente",)
    search_fields = ("nombre", "telefono", "direccion")


@admin.register(ResultadoMoraTemprana)
class ResultadoMoraTempranaAdmin(admin.ModelAdmin):
    list_display = ("id", "credito", "socio", "fecha_corte", "alerta", "prob_mora_90d", "model_version", "fuente")
    list_filter = ("alerta", "fuente", "model_version", "fecha_corte")
    search_fields = ("credito__id", "socio__nombre", "socio__email")


@admin.register(ResultadoSegmentacionSocio)
class ResultadoSegmentacionSocioAdmin(admin.ModelAdmin):
    list_display = ("id", "socio", "fecha_ejecucion", "segmento", "saldo_total", "total_creditos", "model_version")
    list_filter = ("segmento", "model_version", "fecha_ejecucion")
    search_fields = ("socio__nombre", "socio__email")


@admin.register(ReglaAsociacionProducto)
class ReglaAsociacionProductoAdmin(admin.ModelAdmin):
    list_display = ("id", "fecha_ejecucion", "antecedente", "consecuente", "soporte", "confianza", "lift", "vigente")
    list_filter = ("fecha_ejecucion", "vigente", "model_version")
    search_fields = ("antecedente", "consecuente", "oportunidad_comercial")


@admin.register(EjecucionPipeline)
class EjecucionPipelineAdmin(admin.ModelAdmin):
    list_display = ("id", "pipeline", "estado", "duracion_ms", "idempotency_key", "fecha_inicio", "fecha_fin")
    list_filter = ("pipeline", "estado")
    search_fields = ("pipeline", "idempotency_key", "detalle")


@admin.register(AlertaMonitoreo)
class AlertaMonitoreoAdmin(admin.ModelAdmin):
    list_display = ("id", "ambito", "metrica", "severidad", "estado", "valor", "umbral", "fecha_evento")
    list_filter = ("ambito", "severidad", "estado")
    search_fields = ("ambito", "metrica", "detalle", "escalamiento")


@admin.register(ContactoCampania)
class ContactoCampaniaAdmin(admin.ModelAdmin):
    list_display = ("id", "campania", "socio", "ejecutivo_id", "canal", "estado_contacto", "fecha_contacto")
    list_filter = ("canal", "estado_contacto")
    search_fields = ("campania__nombre", "socio__nombre", "socio__email", "ejecutivo_id")


@admin.register(SeguimientoConversionCampania)
class SeguimientoConversionCampaniaAdmin(admin.ModelAdmin):
    list_display = ("id", "campania", "socio", "lista", "etapa", "conversion", "monto_colocado", "fecha_evento")
    list_filter = ("lista", "etapa", "conversion")
    search_fields = ("campania__nombre", "socio__nombre", "socio__email")
