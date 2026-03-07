from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    ROL_SUPERADMIN = "superadmin"
    ROL_ADMIN_DATOS = "admin_datos"
    ROL_ANALISTA = "analista"
    ROL_GERENCIA = "gerencia"
    ROL_COMERCIAL_EJECUTIVO = "comercial_ejecutivo"
    ROL_RIESGO_COBRANZA = "riesgo_cobranza"
    ROL_CONSEJO = "consejo"

    # Roles legacy (compatibilidad temporal).
    ROL_ADMINISTRADOR = "administrador"
    ROL_JEFE_DEPARTAMENTO = "jefe_departamento"
    ROL_AUDITOR = "auditor"
    ROL_CHOICES = [
        (ROL_SUPERADMIN, "Superadministrador"),
        (ROL_ADMIN_DATOS, "Administrador de datos"),
        (ROL_ANALISTA, "Analista"),
        (ROL_GERENCIA, "Gerencia"),
        (ROL_COMERCIAL_EJECUTIVO, "Comercial / Ejecutivos"),
        (ROL_RIESGO_COBRANZA, "Riesgo / Cobranza"),
        (ROL_CONSEJO, "Consejo"),
        (ROL_ADMINISTRADOR, "Administrador (legacy)"),
        (ROL_JEFE_DEPARTAMENTO, "Jefe de departamento (legacy)"),
        (ROL_AUDITOR, "Auditor (legacy)"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default=ROL_ANALISTA)
    two_factor_enabled = models.BooleanField(default=False)
    departamento = models.CharField(max_length=100, blank=True, default="")
    puesto_trabajo = models.CharField(max_length=120, blank=True, default="")
    telefono = models.CharField(max_length=30, blank=True, default="")
    celular = models.CharField(max_length=30, blank=True, default="")
    avatar_image = models.TextField(blank=True, default="")
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_profiles"
        verbose_name = "Perfil de usuario"
        verbose_name_plural = "Perfiles de usuario"

    def __str__(self) -> str:
        return f"{self.user.username} - {self.rol}"
