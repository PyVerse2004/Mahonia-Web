from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import UserProfile, sync_user_role_permissions


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    max_num = 1
    verbose_name = "نقش کاربر"
    verbose_name_plural = "نقش کاربر"


class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = BaseUserAdmin.list_display + ("get_role",)

    def get_role(self, obj):
        profile = getattr(obj, "profile", None)
        return profile.get_role_display() if profile else "-"

    get_role.short_description = "نقش"

    def save_formset(self, request, form, formset, change):
        if formset.model == UserProfile:
            formset.new_objects = []
            formset.changed_objects = []
            formset.deleted_objects = []

            role_to_set = None
            for inline_form in formset.forms:
                if inline_form.is_valid() and not inline_form.cleaned_data.get("DELETE"):
                    role_to_set = inline_form.cleaned_data.get("role")
                    if role_to_set:
                        break

            profile, created = UserProfile.objects.get_or_create(
                user=form.instance,
                defaults={"role": role_to_set or UserProfile.ROLE_SELLER},
            )
            if role_to_set:
                profile.role = role_to_set
                profile.save()
                if created:
                    formset.new_objects.append(profile)
                else:
                    formset.changed_objects.append((profile, ["role"]))
            elif created:
                formset.new_objects.append(profile)

            form.instance.profile = profile
            sync_user_role_permissions(form.instance, profile.role)
            return

        super().save_formset(request, form, formset, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        profile = UserProfile.objects.filter(user=form.instance).first()
        if profile:
            sync_user_role_permissions(form.instance, profile.role)


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(UserProfile)
