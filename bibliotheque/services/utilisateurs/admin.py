from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ["email", "full_name", "role", "department", "is_active", "date_joined"]
    list_filter = ["role", "is_active", "department"]
    search_fields = ["email", "first_name", "last_name", "student_id"]
    ordering = ["last_name"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informations", {
            "fields": ("first_name", "last_name", "role", "student_id",
                       "phone", "avatar", "department", "bio"),
        }),
        ("Permissions", {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
        }),
        ("Dates", {"fields": ("date_joined", "last_login")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "role", "password1", "password2"),
        }),
    )
    readonly_fields = ["date_joined", "last_login"]
