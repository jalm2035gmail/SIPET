from django.contrib.auth.models import User
from django.core.cache import cache
from rest_framework import status
from rest_framework.test import APITestCase

from apps.analitica.models import EventoAuditoria


class AuthLoginApiTests(APITestCase):
    def setUp(self):
        self.url = "/api/auth/login/"
        self.password = "secret12345"
        self.user = User.objects.create_user(
            username="testerlogin",
            email="tester@login.com",
            password=self.password,
        )

    def test_login_with_username_returns_tokens(self):
        response = self.client.post(
            self.url,
            {"username": self.user.username, "password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_with_email_returns_tokens(self):
        response = self.client.post(
            self.url,
            {"username": self.user.email, "password": self.password},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_login_requires_otp_when_2fa_enabled(self):
        self.user.profile.two_factor_enabled = True
        self.user.profile.save(update_fields=["two_factor_enabled"])

        first_response = self.client.post(
            self.url,
            {"username": self.user.username, "password": self.password},
            format="json",
        )

        self.assertEqual(first_response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(first_response.data.get("two_factor_required"))

        cache_key = f"auth:2fa:{self.user.pk}"
        otp_code = cache.get(cache_key)
        self.assertIsNotNone(otp_code)

        second_response = self.client.post(
            self.url,
            {"username": self.user.username, "password": self.password, "otp_code": str(otp_code)},
            format="json",
        )
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", second_response.data)
        self.assertIn("refresh", second_response.data)


class RegisterRoleRulesTests(APITestCase):
    def setUp(self):
        self.url = "/api/auth/register/"

    def test_non_superadmin_cannot_create_superadmin(self):
        response = self.client.post(
            self.url,
            {
                "username": "nuevo_superadmin",
                "email": "nuevo_superadmin@intellicoop.local",
                "password": "super-segura-123",
                "rol": "superadmin",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("rol", response.data)

    def test_superadmin_can_create_superadmin(self):
        creator = User.objects.create_user(
            username="root_creator",
            email="root_creator@intellicoop.local",
            password="creator-123",
        )
        creator.profile.rol = "superadmin"
        creator.profile.save(update_fields=["rol"])
        self.client.force_authenticate(user=creator)

        response = self.client.post(
            self.url,
            {
                "username": "nuevo_superadmin_ok",
                "email": "nuevo_superadmin_ok@intellicoop.local",
                "password": "super-segura-123",
                "rol": "superadmin",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"]["rol"], "superadmin")

    def test_default_role_is_analista(self):
        response = self.client.post(
            self.url,
            {
                "username": "nuevo_analista_default",
                "email": "nuevo_analista_default@intellicoop.local",
                "password": "super-segura-123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"]["rol"], "analista")

    def test_can_create_business_role_admin_datos(self):
        response = self.client.post(
            self.url,
            {
                "username": "nuevo_admin_datos",
                "email": "nuevo_admin_datos@intellicoop.local",
                "password": "super-segura-123",
                "rol": "admin_datos",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["user"]["rol"], "admin_datos")


class ProfileUpdateTests(APITestCase):
    def setUp(self):
        self.url = "/api/auth/profile/"
        self.user = User.objects.create_user(
            username="perfiltest",
            email="perfil@test.com",
            password="perfil-1234",
        )
        self.user.profile.rol = "superadmin"
        self.user.profile.save(update_fields=["rol"])
        self.client.force_authenticate(user=self.user)

    def test_patch_profile_updates_fields_and_password(self):
        response = self.client.patch(
            self.url,
            {
                "email": "perfil+ok@test.com",
                "departamento": "Operaciones",
                "puesto_trabajo": "Jefe de proyecto",
                "telefono": "555-1000",
                "celular": "555-2000",
                "rol": "administrador",
                "two_factor_enabled": True,
                "password": "nueva-clave-987",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "perfil+ok@test.com")
        self.assertEqual(self.user.profile.departamento, "Operaciones")
        self.assertEqual(self.user.profile.puesto_trabajo, "Jefe de proyecto")
        self.assertEqual(self.user.profile.telefono, "555-1000")
        self.assertEqual(self.user.profile.celular, "555-2000")
        self.assertEqual(self.user.profile.rol, "administrador")
        self.assertTrue(self.user.profile.two_factor_enabled)
        self.assertTrue(self.user.check_password("nueva-clave-987"))

    def test_non_superadmin_cannot_change_own_activo(self):
        user = User.objects.create_user(
            username="perfil_no_admin",
            email="perfil_no_admin@test.com",
            password="perfil-1234",
        )
        user.profile.rol = "analista"
        user.profile.save(update_fields=["rol"])
        self.client.force_authenticate(user=user)

        response = self.client.patch(
            self.url,
            {"activo": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("activo", response.data)


class UsersManagementTests(APITestCase):
    def setUp(self):
        self.superadmin = User.objects.create_user(
            username="root",
            email="root@test.com",
            password="root-12345",
        )
        self.superadmin.profile.rol = "superadmin"
        self.superadmin.profile.save(update_fields=["rol"])

        self.admin = User.objects.create_user(
            username="admin_user",
            email="admin@test.com",
            password="admin-12345",
        )
        self.admin.profile.rol = "administrador"
        self.admin.profile.save(update_fields=["rol"])

        self.auditor = User.objects.create_user(
            username="auditor_user",
            email="auditor@test.com",
            password="auditor-12345",
        )
        self.auditor.profile.rol = "auditor"
        self.auditor.profile.save(update_fields=["rol"])

        self.analista = User.objects.create_user(
            username="analista_user",
            email="analista@test.com",
            password="analista-12345",
        )
        self.analista.profile.rol = "analista"
        self.analista.profile.save(update_fields=["rol"])

    def test_admin_list_users_excludes_superadmin(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/api/auth/users/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = [item["username"] for item in response.data]
        self.assertNotIn("root", usernames)
        self.assertIn("admin_user", usernames)
        self.assertIn("auditor_user", usernames)

    def test_superadmin_list_users_includes_superadmin(self):
        self.client.force_authenticate(user=self.superadmin)
        response = self.client.get("/api/auth/users/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        usernames = [item["username"] for item in response.data]
        self.assertIn("root", usernames)

    def test_admin_can_update_other_non_superadmin_user(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f"/api/auth/users/{self.auditor.id}/",
            {"departamento": "Auditoría"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.auditor.refresh_from_db()
        self.assertEqual(self.auditor.profile.departamento, "Auditoría")

    def test_admin_can_create_user(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(
            "/api/auth/users/",
            {
                "username": "nuevo_usuario_panel",
                "email": "nuevo_usuario_panel@test.com",
                "password": "nuevo-pass-123",
                "rol": "auditor",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = User.objects.get(username="nuevo_usuario_panel")
        self.assertEqual(created.profile.rol, "auditor")
        self.assertTrue(
            EventoAuditoria.objects.filter(
                modulo="authentication",
                accion="crear_usuario",
                target_id=str(created.pk),
                actor=self.admin,
            ).exists()
        )

    def test_admin_can_delete_non_superadmin_user(self):
        self.client.force_authenticate(user=self.admin)
        auditor_id = self.auditor.id
        response = self.client.delete(f"/api/auth/users/{self.auditor.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(pk=auditor_id).exists())
        self.assertTrue(
            EventoAuditoria.objects.filter(
                modulo="authentication",
                accion="eliminar_usuario",
                target_id=str(auditor_id),
                actor=self.admin,
            ).exists()
        )

    def test_admin_can_deactivate_other_user(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f"/api/auth/users/{self.auditor.id}/",
            {"activo": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.auditor.refresh_from_db()
        self.assertFalse(self.auditor.profile.activo)

    def test_analista_cannot_manage_users(self):
        self.client.force_authenticate(user=self.analista)
        response = self.client.get("/api/auth/users/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class RolesCatalogTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="catalog_user",
            email="catalog@test.com",
            password="catalog-12345",
        )
        self.user.profile.rol = "gerencia"
        self.user.profile.save(update_fields=["rol"])

    def test_roles_catalog_returns_superuser_and_new_roles(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/auth/roles/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["superusuario"], "superadmin")
        roles = {item["rol"] for item in response.data["roles"]}
        self.assertIn("admin_datos", roles)
        self.assertIn("analista", roles)
        self.assertIn("gerencia", roles)
        self.assertIn("comercial_ejecutivo", roles)
        self.assertIn("riesgo_cobranza", roles)
        self.assertIn("consejo", roles)
        self.assertIn("superadmin", roles)


class RoleCapabilitiesTests(APITestCase):
    def test_superadmin_has_all_capabilities_true(self):
        user = User.objects.create_user(
            username="cap_root",
            email="cap_root@test.com",
            password="cap-root-123",
        )
        user.profile.rol = "superadmin"
        user.profile.save(update_fields=["rol"])
        self.client.force_authenticate(user=user)

        response = self.client.get("/api/auth/permissions/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["is_superuser"])
        self.assertTrue(all(response.data["capabilities"].values()))

    def test_analista_has_expected_capabilities(self):
        user = User.objects.create_user(
            username="cap_analista",
            email="cap_analista@test.com",
            password="cap-analista-123",
        )
        user.profile.rol = "analista"
        user.profile.save(update_fields=["rol"])
        self.client.force_authenticate(user=user)

        response = self.client.get("/api/auth/permissions/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        capabilities = response.data["capabilities"]
        self.assertFalse(capabilities["read_only"])
        self.assertFalse(capabilities["can_manage_users"])
        self.assertTrue(capabilities["can_build_segments"])
        self.assertFalse(capabilities["can_run_campaigns"])

    def test_consejo_is_read_only_and_dashboard_enabled(self):
        user = User.objects.create_user(
            username="cap_consejo",
            email="cap_consejo@test.com",
            password="cap-consejo-123",
        )
        user.profile.rol = "consejo"
        user.profile.save(update_fields=["rol"])
        self.client.force_authenticate(user=user)

        response = self.client.get("/api/auth/permissions/me/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        capabilities = response.data["capabilities"]
        self.assertTrue(capabilities["read_only"])
        self.assertFalse(capabilities["can_manage_users"])
        self.assertTrue(capabilities["can_view_governance_dashboards"])


class AuditEventsApiTests(APITestCase):
    def setUp(self):
        self.gerencia = User.objects.create_user(
            username="gerencia_audit",
            email="gerencia_audit@test.com",
            password="gerencia-123",
        )
        self.gerencia.profile.rol = "gerencia"
        self.gerencia.profile.save(update_fields=["rol"])

        self.analista = User.objects.create_user(
            username="analista_audit",
            email="analista_audit@test.com",
            password="analista-123",
        )
        self.analista.profile.rol = "analista"
        self.analista.profile.save(update_fields=["rol"])

        EventoAuditoria.objects.create(
            modulo="authentication",
            accion="crear_usuario",
            actor=self.gerencia,
            actor_username=self.gerencia.username,
            target_tipo="user",
            target_id="999",
            detalle={"origen": "test"},
        )

    def test_gerencia_can_list_recent_audit_events(self):
        self.client.force_authenticate(user=self.gerencia)
        response = self.client.get("/api/auth/audit/events/?modulo=authentication&limit=10")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["modulo"], "authentication")

    def test_analista_cannot_list_recent_audit_events(self):
        self.client.force_authenticate(user=self.analista)
        response = self.client.get("/api/auth/audit/events/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
