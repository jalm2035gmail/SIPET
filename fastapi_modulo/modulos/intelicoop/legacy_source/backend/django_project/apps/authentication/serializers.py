import random

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.mail import send_mail
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import UserProfile


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    rol = serializers.ChoiceField(
        choices=UserProfile.ROL_CHOICES,
        required=False,
        default=UserProfile.ROL_ANALISTA,
    )

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'rol')

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Este correo ya está registrado.')
        return value

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('Este usuario ya existe.')
        return value

    def validate_rol(self, value):
        request = self.context.get("request")
        if value != UserProfile.ROL_SUPERADMIN:
            return value

        if request is None or not request.user or not request.user.is_authenticated:
            raise serializers.ValidationError(
                "Solo un superadministrador puede crear otro superadministrador."
            )

        profile = getattr(request.user, "profile", None)
        if profile is None or profile.rol != UserProfile.ROL_SUPERADMIN:
            raise serializers.ValidationError(
                "Solo un superadministrador puede crear otro superadministrador."
            )
        return value

    def create(self, validated_data):
        rol = validated_data.pop("rol", UserProfile.ROL_ANALISTA)
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
        )
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.rol = rol
        profile.save(update_fields=["rol"])
        user.refresh_from_db()
        return user


class ProfileUpdateSerializer(serializers.Serializer):
    username = serializers.CharField(required=False, min_length=3, max_length=150)
    email = serializers.EmailField(required=False)
    first_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    last_name = serializers.CharField(required=False, allow_blank=True, max_length=150)
    departamento = serializers.CharField(required=False, allow_blank=True, max_length=100)
    puesto_trabajo = serializers.CharField(required=False, allow_blank=True, max_length=120)
    telefono = serializers.CharField(required=False, allow_blank=True, max_length=30)
    celular = serializers.CharField(required=False, allow_blank=True, max_length=30)
    avatar_image = serializers.CharField(required=False, allow_blank=True)
    rol = serializers.ChoiceField(choices=UserProfile.ROL_CHOICES, required=False)
    two_factor_enabled = serializers.BooleanField(required=False)
    activo = serializers.BooleanField(required=False)
    password = serializers.CharField(required=False, write_only=True, min_length=8)

    def validate_rol(self, value):
        request = self.context.get("request")
        user = self.context.get("user")
        actor_profile = getattr(request.user, "profile", None) if request and request.user else None
        target_profile = getattr(user, "profile", None)

        if actor_profile is None:
            raise serializers.ValidationError("No autorizado para cambiar rol.")

        if actor_profile.rol == UserProfile.ROL_SUPERADMIN:
            return value

        if actor_profile.rol == UserProfile.ROL_ADMINISTRADOR:
            if target_profile and target_profile.rol == UserProfile.ROL_SUPERADMIN:
                raise serializers.ValidationError("No puedes modificar usuarios superadministradores.")
            if value == UserProfile.ROL_SUPERADMIN:
                raise serializers.ValidationError("Solo superadministrador puede asignar rol superadministrador.")
            return value

        if target_profile and value != target_profile.rol:
            raise serializers.ValidationError("No autorizado para cambiar rol.")
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        request = self.context.get("request")
        user = self.context.get("user")
        actor_profile = getattr(request.user, "profile", None) if request and request.user else None
        target_profile = getattr(user, "profile", None)

        if (
            actor_profile
            and actor_profile.rol != UserProfile.ROL_SUPERADMIN
            and target_profile
            and target_profile.rol == UserProfile.ROL_SUPERADMIN
            and request.user.pk != user.pk
        ):
            raise serializers.ValidationError("No autorizado para modificar usuarios superadministradores.")

        if "username" in attrs and User.objects.filter(username=attrs["username"]).exclude(pk=self.context["user"].pk).exists():
            raise serializers.ValidationError({"username": "Este usuario ya existe."})
        if "email" in attrs and User.objects.filter(email=attrs["email"]).exclude(pk=self.context["user"].pk).exists():
            raise serializers.ValidationError({"email": "Este correo ya está registrado."})

        if "activo" in attrs:
            if actor_profile is None:
                raise serializers.ValidationError({"activo": "No autorizado para cambiar estado."})

            actor_is_superadmin = actor_profile.rol == UserProfile.ROL_SUPERADMIN
            actor_is_user_admin = actor_profile.rol in {UserProfile.ROL_GERENCIA, UserProfile.ROL_ADMINISTRADOR}
            is_self_update = request and request.user.pk == user.pk

            if target_profile and target_profile.rol == UserProfile.ROL_SUPERADMIN and not actor_is_superadmin:
                raise serializers.ValidationError({"activo": "Solo superadministrador puede cambiar estado de superadministrador."})

            if is_self_update and not actor_is_superadmin:
                raise serializers.ValidationError({"activo": "No puedes cambiar tu propio estado de cuenta."})

            if not actor_is_superadmin and not actor_is_user_admin:
                raise serializers.ValidationError({"activo": "No autorizado para cambiar estado."})
        return attrs

    def update(self, user, validated_data):
        profile = user.profile
        user_fields = ["username", "email", "first_name", "last_name"]
        profile_fields = [
            "departamento",
            "puesto_trabajo",
            "telefono",
            "celular",
            "avatar_image",
            "rol",
            "two_factor_enabled",
            "activo",
        ]

        for field in user_fields:
            if field in validated_data:
                setattr(user, field, validated_data[field])
        if any(field in validated_data for field in user_fields):
            user.save(update_fields=[f for f in user_fields if f in validated_data])

        for field in profile_fields:
            if field in validated_data:
                setattr(profile, field, validated_data[field])
        if any(field in validated_data for field in profile_fields):
            profile.save(update_fields=[f for f in profile_fields if f in validated_data])

        if validated_data.get("password"):
            user.set_password(validated_data["password"])
            user.save(update_fields=["password"])

        user.refresh_from_db()
        return user


class EmailOrUsernameTokenObtainPairSerializer(TokenObtainPairSerializer):
    otp_code = serializers.CharField(required=False, allow_blank=True, write_only=True)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        rol = user.profile.rol if hasattr(user, "profile") else ""
        token["rol"] = rol
        token["user_type"] = rol
        return token

    def validate(self, attrs):
        username_value = attrs.get(self.username_field, "")
        password = attrs.get("password", "")
        otp_code = str(attrs.get("otp_code", "")).strip()

        if username_value and "@" in username_value:
            user = User.objects.filter(email__iexact=username_value).first()
            if user:
                attrs[self.username_field] = user.get_username()

        resolved_username = attrs.get(self.username_field, "")
        authenticated_user = authenticate(
            request=self.context.get("request"),
            username=resolved_username,
            password=password,
        )

        if authenticated_user and hasattr(authenticated_user, "profile"):
            profile = authenticated_user.profile
            if profile.two_factor_enabled:
                cache_key = f"auth:2fa:{authenticated_user.pk}"
                if not otp_code:
                    generated_code = f"{random.randint(0, 999999):06d}"
                    cache.set(cache_key, generated_code, timeout=300)
                    if authenticated_user.email:
                        send_mail(
                            "Codigo de verificacion Intellicoop",
                            f"Tu codigo de autenticacion es: {generated_code}",
                            None,
                            [authenticated_user.email],
                            fail_silently=True,
                        )
                    raise serializers.ValidationError(
                        {
                            "two_factor_required": True,
                            "detail": "Se requiere codigo de autenticacion de dos factores.",
                        }
                    )

                expected_code = cache.get(cache_key)
                if not expected_code or otp_code != str(expected_code):
                    raise serializers.ValidationError({"otp_code": "Codigo 2FA invalido o expirado."})

                cache.delete(cache_key)

        return super().validate(attrs)
