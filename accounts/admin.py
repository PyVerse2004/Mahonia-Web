from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import UserProfile, sync_user_role_permissions


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name = "نقش کاربر"
    verbose_name_plural = "نقش کاربر"


class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = BaseUserAdmin.list_display + ("get_role",)

    def get_role(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.get_role_display() if profile else "-"

    get_role.short_description = "نقش"

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        profile = getattr(form.instance, "profile", None)
        if profile:
            sync_user_role_permissions(form.instance, profile.role)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(UserProfile)
