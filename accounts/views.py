from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView

from .forms import LoginForm
from .models import UserProfile, sync_user_role_permissions


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user
        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "role": UserProfile.ROLE_MANAGER if user.is_superuser else UserProfile.ROLE_SELLER
            },
        )
        effective_role = UserProfile.ROLE_MANAGER if user.is_superuser else profile.role
        self.request.session["active_role"] = effective_role
        sync_user_role_permissions(user, effective_role)
        return response


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"
