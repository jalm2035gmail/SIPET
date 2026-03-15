from rest_framework.permissions import MAINPermission

from .models import UserProfile


ROLE_LEVELS = {
    UserProfile.ROL_CONSEJO: 1,
    UserProfile.ROL_AUDITOR: 1,
    UserProfile.ROL_COMERCIAL_EJECUTIVO: 2,
    UserProfile.ROL_ANALISTA: 3,
    UserProfile.ROL_ADMIN_DATOS: 3,
    UserProfile.ROL_RIESGO_COBRANZA: 3,
    UserProfile.ROL_JEFE_DEPARTAMENTO: 3,
    UserProfile.ROL_GERENCIA: 4,
    UserProfile.ROL_ADMINISTRADOR: 4,
    UserProfile.ROL_SUPERADMIN: 5,
}


class RolePermission(MAINPermission):
    min_level = 1

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        profile = getattr(user, "profile", None)
        if profile is None or not profile.activo:
            return False

        if profile.rol in (UserProfile.ROL_AUDITOR, UserProfile.ROL_CONSEJO) and request.method not in ("GET", "HEAD", "OPTIONS"):
            return False

        return ROLE_LEVELS.get(profile.rol, 0) >= self.min_level


class IsAuditorOrHigher(RolePermission):
    min_level = 1


class IsJefeDepartamentoOrHigher(RolePermission):
    min_level = 2


class IsAnalistaOrHigher(RolePermission):
    min_level = 3


class IsGerenciaOrHigher(RolePermission):
    min_level = 4


class IsAdministradorOrHigher(RolePermission):
    min_level = 4


class IsSuperadministrador(RolePermission):
    min_level = 5


# Alias de compatibilidad temporal
IsOficialOrHigher = IsAuditorOrHigher
IsGerenteOrHigher = IsGerenciaOrHigher
IsAdminRole = IsAdministradorOrHigher
