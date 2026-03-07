from rest_framework import status
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken

from .permissions import (
    IsAdministradorOrHigher,
    IsAnalistaOrHigher,
    IsAuditorOrHigher,
    IsGerenciaOrHigher,
    IsJefeDepartamentoOrHigher,
    IsSuperadministrador,
)
from .serializers import EmailOrUsernameTokenObtainPairSerializer, ProfileUpdateSerializer, RegisterSerializer
from apps.analitica.auditoria import registrar_evento_auditoria
from apps.analitica.models import EventoAuditoria


class EmailOrUsernameTokenObtainPairView(TokenObtainPairView):
    serializer_class = EmailOrUsernameTokenObtainPairSerializer


class RegisterView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        registrar_evento_auditoria(
            request=request,
            modulo="authentication",
            accion="registro_publico_usuario",
            target_tipo="user",
            target_id=str(user.pk),
            detalle={"rol": user.profile.rol},
        )

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'rol': user.profile.rol,
                },
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            status=status.HTTP_201_CREATED,
        )


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response(
            {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'rol': user.profile.rol if hasattr(user, 'profile') else None,
                'activo': user.profile.activo if hasattr(user, 'profile') else None,
                'two_factor_enabled': user.profile.two_factor_enabled if hasattr(user, 'profile') else False,
                'departamento': user.profile.departamento if hasattr(user, 'profile') else "",
                'puesto_trabajo': user.profile.puesto_trabajo if hasattr(user, 'profile') else "",
                'telefono': user.profile.telefono if hasattr(user, 'profile') else "",
                'celular': user.profile.celular if hasattr(user, 'profile') else "",
                'avatar_image': user.profile.avatar_image if hasattr(user, 'profile') else "",
            }
        )

    def patch(self, request):
        serializer = ProfileUpdateSerializer(
            data=request.data,
            context={"request": request, "user": request.user},
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.update(request.user, serializer.validated_data)
        changed_fields = [field for field in serializer.validated_data.keys() if field != "password"]
        registrar_evento_auditoria(
            request=request,
            modulo="authentication",
            accion="actualizar_perfil_propio",
            target_tipo="user",
            target_id=str(user.pk),
            detalle={"campos": changed_fields},
        )
        return Response(
            {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'rol': user.profile.rol,
                'activo': user.profile.activo,
                'two_factor_enabled': user.profile.two_factor_enabled,
                'departamento': user.profile.departamento,
                'puesto_trabajo': user.profile.puesto_trabajo,
                'telefono': user.profile.telefono,
                'celular': user.profile.celular,
                'avatar_image': user.profile.avatar_image,
            }
        )


class TwoFactorPreferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        return Response({'two_factor_enabled': profile.two_factor_enabled})

    def post(self, request):
        profile = request.user.profile
        raw_enabled = request.data.get('enabled', False)
        if isinstance(raw_enabled, bool):
            enabled = raw_enabled
        else:
            enabled = str(raw_enabled).strip().lower() in {'1', 'true', 'yes', 'on'}
        profile.two_factor_enabled = enabled
        profile.save(update_fields=['two_factor_enabled'])
        registrar_evento_auditoria(
            request=request,
            modulo="authentication",
            accion="actualizar_preferencia_2fa",
            target_tipo="user",
            target_id=str(request.user.pk),
            detalle={"two_factor_enabled": profile.two_factor_enabled},
        )
        return Response({'two_factor_enabled': profile.two_factor_enabled})


class RolesCatalogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "superusuario": "superadmin",
                "roles": [
                    {"rol": "admin_datos", "nombre": "Administrador de datos", "scope": "carga y validación de fuentes"},
                    {"rol": "analista", "nombre": "Analista", "scope": "segmentos, indicadores y reportes"},
                    {"rol": "gerencia", "nombre": "Gerencia", "scope": "dashboards, alertas y decisiones"},
                    {"rol": "comercial_ejecutivo", "nombre": "Comercial / Ejecutivos", "scope": "campañas, seguimiento y conversión"},
                    {"rol": "riesgo_cobranza", "nombre": "Riesgo / Cobranza", "scope": "alertas, scoring y priorización"},
                    {"rol": "consejo", "nombre": "Consejo", "scope": "tablero ejecutivo y reportes de gobierno"},
                    {"rol": "superadmin", "nombre": "Superadministrador", "scope": "acceso total"},
                ],
                "user_role": request.user.profile.rol,
            }
        )


class RoleCapabilitiesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        role = request.user.profile.rol
        is_superadmin = role == "superadmin"
        is_read_only = role in {"consejo", "auditor"}
        can_manage_users = role in {"superadmin", "gerencia", "administrador"}

        capabilities = {
            "read_only": is_read_only,
            "can_manage_users": can_manage_users,
            "can_manage_data_intake": is_superadmin or role == "admin_datos",
            "can_build_segments": is_superadmin or role in {"analista", "gerencia"},
            "can_run_campaigns": is_superadmin or role in {"comercial_ejecutivo", "gerencia"},
            "can_manage_risk_alerts": is_superadmin or role in {"riesgo_cobranza", "gerencia"},
            "can_view_governance_dashboards": is_superadmin or role in {"consejo", "gerencia"},
        }

        if is_superadmin:
            capabilities = {key: True for key in capabilities}

        return Response(
            {
                "user_role": role,
                "is_superuser": is_superadmin,
                "capabilities": capabilities,
            }
        )


class UsersManagementView(APIView):
    permission_classes = [IsAdministradorOrHigher]

    def get(self, request):
        users = User.objects.select_related("profile").order_by("username")
        actor_profile = request.user.profile
        if actor_profile.rol != "superadmin":
            users = users.exclude(profile__rol="superadmin")

        payload = [
            {
                "id": item.id,
                "username": item.username,
                "email": item.email,
                "rol": item.profile.rol if hasattr(item, "profile") else "",
                "activo": item.profile.activo if hasattr(item, "profile") else False,
                "departamento": item.profile.departamento if hasattr(item, "profile") else "",
                "puesto_trabajo": item.profile.puesto_trabajo if hasattr(item, "profile") else "",
                "avatar_image": item.profile.avatar_image if hasattr(item, "profile") else "",
            }
            for item in users
        ]
        return Response(payload)

    def post(self, request):
        serializer = RegisterSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        registrar_evento_auditoria(
            request=request,
            modulo="authentication",
            accion="crear_usuario",
            target_tipo="user",
            target_id=str(user.pk),
            detalle={"rol": user.profile.rol},
        )
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "rol": user.profile.rol,
            },
            status=status.HTTP_201_CREATED,
        )


class UserDetailManagementView(APIView):
    permission_classes = [IsAdministradorOrHigher]

    def get_target_user(self, request, user_id):
        user = User.objects.select_related("profile").filter(pk=user_id).first()
        if user is None:
            return None, Response({"detail": "Usuario no encontrado."}, status=status.HTTP_404_NOT_FOUND)

        actor_profile = request.user.profile
        target_profile = user.profile
        if actor_profile.rol != "superadmin" and target_profile.rol == "superadmin" and user.pk != request.user.pk:
            return None, Response({"detail": "No autorizado."}, status=status.HTTP_403_FORBIDDEN)

        return user, None

    def get(self, request, user_id):
        user, error_response = self.get_target_user(request, user_id)
        if error_response:
            return error_response

        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "rol": user.profile.rol,
                "activo": user.profile.activo,
                "two_factor_enabled": user.profile.two_factor_enabled,
                "departamento": user.profile.departamento,
                "puesto_trabajo": user.profile.puesto_trabajo,
                "telefono": user.profile.telefono,
                "celular": user.profile.celular,
                "avatar_image": user.profile.avatar_image,
            }
        )

    def patch(self, request, user_id):
        user, error_response = self.get_target_user(request, user_id)
        if error_response:
            return error_response

        serializer = ProfileUpdateSerializer(
            data=request.data,
            context={"request": request, "user": user},
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        updated = serializer.update(user, serializer.validated_data)
        changed_fields = [field for field in serializer.validated_data.keys() if field != "password"]
        registrar_evento_auditoria(
            request=request,
            modulo="authentication",
            accion="actualizar_usuario",
            target_tipo="user",
            target_id=str(updated.pk),
            detalle={"campos": changed_fields},
        )
        return Response(
            {
                "id": updated.id,
                "username": updated.username,
                "email": updated.email,
                "first_name": updated.first_name,
                "last_name": updated.last_name,
                "rol": updated.profile.rol,
                "activo": updated.profile.activo,
                "two_factor_enabled": updated.profile.two_factor_enabled,
                "departamento": updated.profile.departamento,
                "puesto_trabajo": updated.profile.puesto_trabajo,
                "telefono": updated.profile.telefono,
                "celular": updated.profile.celular,
                "avatar_image": updated.profile.avatar_image,
            }
        )

    def delete(self, request, user_id):
        user, error_response = self.get_target_user(request, user_id)
        if error_response:
            return error_response
        if user.pk == request.user.pk:
            return Response({"detail": "No puedes eliminar tu propio usuario."}, status=status.HTTP_400_BAD_REQUEST)
        deleted_pk = user.pk
        deleted_username = user.username
        user.delete()
        registrar_evento_auditoria(
            request=request,
            modulo="authentication",
            accion="eliminar_usuario",
            target_tipo="user",
            target_id=str(deleted_pk),
            detalle={"username": deleted_username},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AuditEventsRecentView(APIView):
    permission_classes = [IsGerenciaOrHigher]

    def get(self, request):
        modulo_filter = (request.query_params.get("modulo") or "").strip()
        accion_filter = (request.query_params.get("accion") or "").strip()
        limit_raw = (request.query_params.get("limit") or "100").strip()
        try:
            limit = max(1, min(500, int(limit_raw)))
        except ValueError:
            limit = 100

        queryset = EventoAuditoria.objects.select_related("actor").order_by("-fecha_evento", "-id")
        if modulo_filter:
            queryset = queryset.filter(modulo=modulo_filter)
        if accion_filter:
            queryset = queryset.filter(accion=accion_filter)

        payload = [
            {
                "id": item.id,
                "request_id": str(item.request_id),
                "fecha_evento": item.fecha_evento.isoformat(),
                "modulo": item.modulo,
                "accion": item.accion,
                "resultado": item.resultado,
                "actor_username": item.actor_username,
                "target_tipo": item.target_tipo,
                "target_id": item.target_id,
                "ip_origen": item.ip_origen,
                "detalle": item.detalle,
            }
            for item in queryset[:limit]
        ]
        return Response(payload)


class RoleAuditorView(APIView):
    permission_classes = [IsAuditorOrHigher]

    def get(self, request):
        return Response({'ok': True, 'required_role': 'auditor', 'user_role': request.user.profile.rol})


class RoleJefeDepartamentoView(APIView):
    permission_classes = [IsJefeDepartamentoOrHigher]

    def get(self, request):
        return Response({'ok': True, 'required_role': 'jefe_departamento', 'user_role': request.user.profile.rol})


class RoleAdministradorView(APIView):
    permission_classes = [IsAdministradorOrHigher]

    def get(self, request):
        return Response({'ok': True, 'required_role': 'administrador', 'user_role': request.user.profile.rol})


class RoleSuperadministradorView(APIView):
    permission_classes = [IsSuperadministrador]

    def get(self, request):
        return Response({'ok': True, 'required_role': 'superadmin', 'user_role': request.user.profile.rol})


class RoleConsejoView(APIView):
    permission_classes = [IsAuditorOrHigher]

    def get(self, request):
        return Response({'ok': True, 'required_role': 'consejo', 'user_role': request.user.profile.rol})


class RoleComercialEjecutivoView(APIView):
    permission_classes = [IsJefeDepartamentoOrHigher]

    def get(self, request):
        return Response({'ok': True, 'required_role': 'comercial_ejecutivo', 'user_role': request.user.profile.rol})


class RoleAnalistaView(APIView):
    permission_classes = [IsAnalistaOrHigher]

    def get(self, request):
        return Response({'ok': True, 'required_role': 'analista', 'user_role': request.user.profile.rol})


class RoleAdminDatosView(APIView):
    permission_classes = [IsAnalistaOrHigher]

    def get(self, request):
        return Response({'ok': True, 'required_role': 'admin_datos', 'user_role': request.user.profile.rol})


class RoleRiesgoCobranzaView(APIView):
    permission_classes = [IsAnalistaOrHigher]

    def get(self, request):
        return Response({'ok': True, 'required_role': 'riesgo_cobranza', 'user_role': request.user.profile.rol})


class RoleGerenciaView(APIView):
    permission_classes = [IsGerenciaOrHigher]

    def get(self, request):
        return Response({'ok': True, 'required_role': 'gerencia', 'user_role': request.user.profile.rol})
