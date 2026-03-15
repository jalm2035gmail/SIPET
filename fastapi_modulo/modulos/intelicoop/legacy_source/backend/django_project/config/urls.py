import os
from django.contrib import admin
from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from apps.analitica.views import CampaniaListCreateView, ProspectoListView
from apps.authentication.views import EmailOrUsernameTokenObtainPairView


def health(_request):
    return JsonResponse({'status': 'ok', 'service': 'django'})

def backend_template_context(is_config_shell=False, is_users_shell=False, is_mineria_shell=False):
    django_MAIN = os.getenv('DJANGO_MAIN_URL', 'http://localhost:8010').rstrip('/')
    frontend_MAIN = os.getenv('FRONTEND_MAIN_URL', 'http://localhost:3010').rstrip('/')
    return {
        "title": "Template Backend",
        "page_heading": "Intellicoop Admin",
        "page_subtitle": "Template backend instalado en Django.",
        "backend_home_path": f"{django_MAIN}/avan",
        "backend_config_path": f"{django_MAIN}/avan/config",
        "backend_personalizar_users_path": f"{django_MAIN}/avan/config/usuarios",
        "backend_mineria_path": f"{django_MAIN}/avan/mineria-datos",
        "backend_login_path": f"{django_MAIN}/avan/login",
        "admin_path": f"{django_MAIN}/admin/",
        "admin_users_path": f"{django_MAIN}/admin/auth/user/",
        "frontend_home_path": f"{frontend_MAIN}/backend",
        "frontend_login_path": f"{frontend_MAIN}/backend/login",
        "frontend_register_path": f"{frontend_MAIN}/backend/register",
        "frontend_forgot_password_path": f"{frontend_MAIN}/backend/forgot-password",
        "frontend_socios_path": f"{frontend_MAIN}/backend/socios",
        "frontend_socios_inactivos_path": f"{frontend_MAIN}/backend/socios-inactivos",
        "frontend_creditos_path": f"{frontend_MAIN}/backend/creditos",
        "frontend_creditos_nuevo_path": f"{frontend_MAIN}/backend/creditos/nuevo",
        "frontend_ahorros_path": f"{frontend_MAIN}/backend/ahorros",
        "frontend_campanas_path": f"{frontend_MAIN}/backend/campanas",
        "frontend_prospectos_path": f"{frontend_MAIN}/backend/prospectos",
        "api_health_path": f"{django_MAIN}/api/health/",
        "api_auth_login_path": f"{django_MAIN}/api/auth/login/",
        "api_auth_refresh_path": f"{django_MAIN}/api/auth/refresh/",
        "api_auth_register_path": f"{django_MAIN}/api/auth/register/",
        "api_auth_profile_path": f"{django_MAIN}/api/auth/profile/",
        "api_auth_users_path": f"{django_MAIN}/api/auth/users/",
        "api_auth_role_auditor_path": f"{django_MAIN}/api/auth/roles/auditor/",
        "api_auth_role_jefe_departamento_path": f"{django_MAIN}/api/auth/roles/jefe-departamento/",
        "api_auth_role_administrador_path": f"{django_MAIN}/api/auth/roles/administrador/",
        "api_auth_role_superadministrador_path": f"{django_MAIN}/api/auth/roles/superadministrador/",
        "api_socios_path": f"{django_MAIN}/api/socios/",
        "api_socios_ping_path": f"{django_MAIN}/api/socios/ping/",
        "api_creditos_path": f"{django_MAIN}/api/creditos/",
        "api_creditos_pagos_path": f"{django_MAIN}/api/creditos/pagos/",
        "api_ahorros_cuentas_path": f"{django_MAIN}/api/ahorros/cuentas/",
        "api_ahorros_movimientos_path": f"{django_MAIN}/api/ahorros/movimientos/",
        "api_ahorros_aperturar_path": f"{django_MAIN}/api/ahorros/aperturar/",
        "api_ahorros_ping_path": f"{django_MAIN}/api/ahorros/ping/",
        "api_campanas_root_path": f"{django_MAIN}/api/campanas/",
        "api_prospectos_root_path": f"{django_MAIN}/api/prospectos/",
        "api_analitica_campanas_path": f"{django_MAIN}/api/analitica/campanas/",
        "api_analitica_prospectos_path": f"{django_MAIN}/api/analitica/prospectos/",
        "api_analitica_ping_path": f"{django_MAIN}/api/analitica/ping/",
        "is_config_shell": is_config_shell,
        "is_users_shell": is_users_shell,
        "is_mineria_shell": is_mineria_shell,
    }


def avan(request):
    return TemplateResponse(request, "backend_template_django.html", backend_template_context(is_config_shell=False))


def avan_config(request):
    return TemplateResponse(request, "backend_template_django.html", backend_template_context(is_config_shell=True))


def avan_config_usuarios(request):
    return TemplateResponse(
        request,
        "backend_template_django.html",
        backend_template_context(is_config_shell=True, is_users_shell=True),
    )


def avan_login(request):
    return TemplateResponse(
        request,
        "login_template_django.html",
        {
            "title": "Login Backend",
            "heading": "Ingreso Backend Intellicoop",
            "subtitle": "Usa tu usuario o correo para autenticarte.",
        },
    )

def avan_mineria_datos(request):
    return TemplateResponse(
        request,
        "backend_template_django.html",
        backend_template_context(is_mineria_shell=True),
    )


urlpatterns = [
    path('admin/', admin.site.urls),
    path('avan', avan),
    path('avan/config', avan_config),
    path('avan/config/usuarios', avan_config_usuarios),
    path('avan/mineria-datos', avan_mineria_datos),
    path('avan/login', avan_login),
    path('api/health/', health),
    path('api/auth/login/', EmailOrUsernameTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/socios/', include('apps.socios.urls')),
    path('api/creditos/', include('apps.creditos.urls')),
    path('api/ahorros/', include('apps.ahorros.urls')),
    path('api/campanas/', CampaniaListCreateView.as_view(), name='campania_list_create_root'),
    path('api/prospectos/', ProspectoListView.as_view(), name='prospecto_list_root'),
    path('api/analitica/', include('apps.analitica.urls')),
    path('api/v1/auth/login/', EmailOrUsernameTokenObtainPairView.as_view(), name='v1_token_obtain_pair'),
    path('api/v1/auth/refresh/', TokenRefreshView.as_view(), name='v1_token_refresh'),
    path('api/v1/auth/', include('apps.authentication.urls')),
    path('api/v1/socios/', include('apps.socios.urls')),
    path('api/v1/creditos/', include('apps.creditos.urls')),
    path('api/v1/ahorros/', include('apps.ahorros.urls')),
    path('api/v1/campanas/', CampaniaListCreateView.as_view(), name='v1_campania_list_create_root'),
    path('api/v1/prospectos/', ProspectoListView.as_view(), name='v1_prospecto_list_root'),
    path('api/v1/analitica/', include('apps.analitica.urls')),
]
