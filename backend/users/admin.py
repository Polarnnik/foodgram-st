from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import Follow

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["email"]
    list_display = (
        "id",
        "email",
        "username",
        "first_name",
        "last_name",
        "is_staff",
    )
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = (
        "email",
        "username",
        "first_name",
        "last_name",
    )
    readonly_fields = ("last_login", "date_joined")


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("user", "author")
    search_fields = ("user__username", "author__username")
    list_filter = ("author",)
