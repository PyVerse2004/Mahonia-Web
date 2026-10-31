from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView

from .forms import LoginForm


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"
