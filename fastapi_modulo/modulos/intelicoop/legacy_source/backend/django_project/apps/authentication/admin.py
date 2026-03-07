from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "rol", "activo", "fecha_creacion")
    list_filter = ("rol", "activo")
    search_fields = ("user__username", "user__email")
