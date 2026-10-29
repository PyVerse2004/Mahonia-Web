from django.urls import path
from .views import CustomLoginView, DashboardView
from django.contrib.auth import views as auth_v

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('logout/', auth_v.LogoutView.as_view(), name='logout')
]
