from django.shortcuts import render
from django.contrib.auth.views import LoginView


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True


