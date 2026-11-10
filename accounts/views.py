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
        selected_role = form.cleaned_data.get("role")
        user = self.request.user
        profile = getattr(user, "profile", None)
        effective_role = (
            selected_role or (profile.role if profile else UserProfile.ROLE_SELLER)
        )
        self.request.session["active_role"] = effective_role
        if profile:
            sync_user_role_permissions(user, effective_role)
        return response


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"
