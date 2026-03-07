import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from apps.creditos.models import Credito
from apps.socios.models import Socio


class Campania(models.Model):
    ESTADO_BORRADOR = "borrador"
    ESTADO_ACTIVA = "activa"
    ESTADO_FINALIZADA = "finalizada"
    ESTADO_CHOICES = [
        (ESTADO_BORRADOR, "Borrador"),
        (ESTADO_ACTIVA, "Activa"),
        (ESTADO_FINALIZADA, "Finalizada"),
    ]

    nombre = models.CharField(max_length=150)
    tipo = models.CharField(max_length=100)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_BORRADOR)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "campanias"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"Campania {self.id} - {self.nombre}"


class Prospecto(models.Model):
    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=30)
    direccion = models.CharField(max_length=255)
    fuente = models.CharField(max_length=100)
    score_propension = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "prospectos"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"Prospecto {self.id} - {self.nombre}"


class ResultadoScoring(models.Model):
    RIESGO_BAJO = "bajo"
    RIESGO_MEDIO = "medio"
    RIESGO_ALTO = "alto"
    RIESGO_CHOICES = [
        (RIESGO_BAJO, "Bajo"),
        (RIESGO_MEDIO, "Medio"),
        (RIESGO_ALTO, "Alto"),
    ]

    solicitud_id = models.CharField(max_length=120, db_index=True)
    request_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    credito = models.ForeignKey(
        Credito,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resultados_scoring",
    )
    socio = models.ForeignKey(
        Socio,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resultados_scoring",
    )
    ingreso_mensual = models.DecimalField(max_digits=12, decimal_places=2)
    deuda_actual = models.DecimalField(max_digits=12, decimal_places=2)
    antiguedad_meses = models.PositiveIntegerField(default=0)
    score = models.DecimalField(max_digits=5, decimal_places=2)
    recomendacion = models.CharField(max_length=30)
    riesgo = models.CharField(max_length=10, choices=RIESGO_CHOICES)
    model_version = models.CharField(max_length=60, default="weighted_score_v1")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "resultados_scoring"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"Scoring {self.solicitud_id} ({self.score})"


class ResultadoMoraTemprana(models.Model):
    ALERTA_BAJA = "baja"
    ALERTA_MEDIA = "media"
    ALERTA_ALTA = "alta"
    ALERTA_CHOICES = [
        (ALERTA_BAJA, "Baja"),
        (ALERTA_MEDIA, "Media"),
        (ALERTA_ALTA, "Alta"),
    ]

    FUENTE_BATCH = "batch"
    FUENTE_ONLINE = "online"
    FUENTE_CHOICES = [
        (FUENTE_BATCH, "Batch"),
        (FUENTE_ONLINE, "Online"),
    ]

    request_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    credito = models.ForeignKey(
        Credito,
        on_delete=models.CASCADE,
        related_name="resultados_mora_temprana",
    )
    socio = models.ForeignKey(
        Socio,
        on_delete=models.CASCADE,
        related_name="resultados_mora_temprana",
    )
    fecha_corte = models.DateField(default=timezone.localdate)
    cuota_estimada = models.DecimalField(max_digits=12, decimal_places=2)
    pagos_90d = models.DecimalField(max_digits=12, decimal_places=2)
    ratio_pago_90d = models.DecimalField(max_digits=6, decimal_places=4)
    deuda_ingreso_ratio = models.DecimalField(max_digits=6, decimal_places=4)
    prob_mora_30d = models.DecimalField(max_digits=6, decimal_places=4)
    prob_mora_60d = models.DecimalField(max_digits=6, decimal_places=4)
    prob_mora_90d = models.DecimalField(max_digits=6, decimal_places=4)
    alerta = models.CharField(max_length=10, choices=ALERTA_CHOICES)
    model_version = models.CharField(max_length=60, default="mora_temprana_v1")
    fuente = models.CharField(max_length=10, choices=FUENTE_CHOICES, default=FUENTE_BATCH)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "resultados_mora_temprana"
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["credito", "fecha_corte", "model_version", "fuente"],
                name="uniq_mora_temprana_credito_corte_version_fuente",
            ),
        ]

    def __str__(self) -> str:
        return f"MoraTemprana credito={self.credito_id} alerta={self.alerta} p90={self.prob_mora_90d}"


class ResultadoSegmentacionSocio(models.Model):
    request_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    socio = models.ForeignKey(
        Socio,
        on_delete=models.CASCADE,
        related_name="resultados_segmentacion",
    )
    fecha_ejecucion = models.DateField(default=timezone.localdate)
    segmento = models.CharField(max_length=30, choices=Socio.SEGMENTO_CHOICES)
    saldo_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_movimientos = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    cantidad_movimientos = models.PositiveIntegerField(default=0)
    dias_desde_ultimo_movimiento = models.PositiveIntegerField(null=True, blank=True)
    total_creditos = models.PositiveIntegerField(default=0)
    model_version = models.CharField(max_length=60, default="segmentacion_socios_v1")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "resultados_segmentacion_socios"
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["socio", "fecha_ejecucion", "model_version"],
                name="uniq_segmentacion_socio_fecha_version",
            ),
        ]

    def __str__(self) -> str:
        return f"Segmentacion socio={self.socio_id} segmento={self.segmento} fecha={self.fecha_ejecucion}"


class ReglaAsociacionProducto(models.Model):
    request_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    fecha_ejecucion = models.DateField(default=timezone.localdate)
    antecedente = models.CharField(max_length=120, db_index=True)
    consecuente = models.CharField(max_length=120, db_index=True)
    soporte = models.DecimalField(max_digits=6, decimal_places=4)
    confianza = models.DecimalField(max_digits=6, decimal_places=4)
    lift = models.DecimalField(max_digits=8, decimal_places=4)
    casos_antecedente = models.PositiveIntegerField(default=0)
    casos_regla = models.PositiveIntegerField(default=0)
    oportunidad_comercial = models.CharField(max_length=255)
    vigente = models.BooleanField(default=True)
    model_version = models.CharField(max_length=60, default="asociacion_productos_v1")
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reglas_asociacion_productos"
        ordering = ["-lift", "-confianza", "-soporte", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["fecha_ejecucion", "antecedente", "consecuente", "model_version"],
                name="uniq_regla_asociacion_fecha_ant_cons_version",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.antecedente} -> {self.consecuente} (lift={self.lift})"


class EjecucionPipeline(models.Model):
    ESTADO_OK = "ok"
    ESTADO_ERROR = "error"
    ESTADO_CHOICES = [
        (ESTADO_OK, "OK"),
        (ESTADO_ERROR, "Error"),
    ]

    request_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    pipeline = models.CharField(max_length=120, db_index=True)
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    duracion_ms = models.PositiveIntegerField(default=0)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default=ESTADO_OK)
    detalle = models.CharField(max_length=255, blank=True, default="")
    idempotency_key = models.CharField(max_length=180, db_index=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ejecuciones_pipeline"
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["pipeline", "idempotency_key"],
                name="uniq_pipeline_idempotency_key",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.pipeline} {self.estado} ({self.idempotency_key})"


class AlertaMonitoreo(models.Model):
    SEVERIDAD_INFO = "info"
    SEVERIDAD_WARN = "warn"
    SEVERIDAD_CRITICAL = "critical"
    SEVERIDAD_CHOICES = [
        (SEVERIDAD_INFO, "Info"),
        (SEVERIDAD_WARN, "Warn"),
        (SEVERIDAD_CRITICAL, "Critical"),
    ]

    ESTADO_ACTIVA = "activa"
    ESTADO_RESUELTA = "resuelta"
    ESTADO_CHOICES = [
        (ESTADO_ACTIVA, "Activa"),
        (ESTADO_RESUELTA, "Resuelta"),
    ]

    request_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    ambito = models.CharField(max_length=40, db_index=True)  # tecnico | datos | modelo
    metrica = models.CharField(max_length=80, db_index=True)
    valor = models.DecimalField(max_digits=12, decimal_places=4)
    umbral = models.CharField(max_length=60)
    severidad = models.CharField(max_length=10, choices=SEVERIDAD_CHOICES, default=SEVERIDAD_WARN)
    escalamiento = models.CharField(max_length=100, default="equipo_analitica")
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default=ESTADO_ACTIVA)
    detalle = models.CharField(max_length=255, blank=True, default="")
    fecha_evento = models.DateTimeField(default=timezone.now)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "alertas_monitoreo"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.ambito}:{self.metrica} {self.severidad} {self.estado}"


class ContactoCampania(models.Model):
    ESTADO_PENDIENTE = "pendiente"
    ESTADO_CONTACTADO = "contactado"
    ESTADO_NO_LOCALIZADO = "no_localizado"
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_CONTACTADO, "Contactado"),
        (ESTADO_NO_LOCALIZADO, "No localizado"),
    ]

    request_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    campania = models.ForeignKey(Campania, on_delete=models.CASCADE, related_name="contactos")
    socio = models.ForeignKey(Socio, on_delete=models.CASCADE, related_name="contactos_campania")
    ejecutivo_id = models.CharField(max_length=60, db_index=True)
    canal = models.CharField(max_length=30)
    estado_contacto = models.CharField(max_length=20, choices=ESTADO_CHOICES, default=ESTADO_PENDIENTE)
    fecha_contacto = models.DateField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "contactos_campania"
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["campania", "socio"],
                name="uniq_contacto_campania_socio",
            ),
        ]

    def __str__(self) -> str:
        return f"Contacto campania={self.campania_id} socio={self.socio_id} estado={self.estado_contacto}"


class SeguimientoConversionCampania(models.Model):
    request_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    campania = models.ForeignKey(Campania, on_delete=models.CASCADE, related_name="seguimientos")
    socio = models.ForeignKey(Socio, on_delete=models.CASCADE, related_name="seguimientos_campania")
    lista = models.CharField(max_length=30)
    etapa = models.CharField(max_length=30)
    conversion = models.BooleanField(default=False)
    monto_colocado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fecha_evento = models.DateField(default=timezone.localdate)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "seguimiento_conversion_campania"
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["campania", "socio", "lista"],
                name="uniq_seguimiento_campania_socio_lista",
            ),
        ]

    def __str__(self) -> str:
        return f"Seguimiento campania={self.campania_id} socio={self.socio_id} conversion={self.conversion}"


class EventoAuditoria(models.Model):
    RESULTADO_OK = "ok"
    RESULTADO_ERROR = "error"
    RESULTADO_CHOICES = [
        (RESULTADO_OK, "OK"),
        (RESULTADO_ERROR, "Error"),
    ]

    request_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    modulo = models.CharField(max_length=60, db_index=True)
    accion = models.CharField(max_length=120, db_index=True)
    resultado = models.CharField(max_length=10, choices=RESULTADO_CHOICES, default=RESULTADO_OK, db_index=True)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="eventos_auditoria")
    actor_username = models.CharField(max_length=150, blank=True, default="")
    target_tipo = models.CharField(max_length=60, blank=True, default="")
    target_id = models.CharField(max_length=120, blank=True, default="")
    ip_origen = models.CharField(max_length=64, blank=True, default="")
    detalle = models.JSONField(default=dict, blank=True)
    fecha_evento = models.DateTimeField(default=timezone.now, db_index=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "eventos_auditoria"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"{self.modulo}:{self.accion} {self.resultado}"
