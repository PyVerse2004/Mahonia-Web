from django.urls import path
from .views import CustomLoginView, DashboardView

urlpatterns = [
    path("login/", CustomLoginView.as_view(), name="login"),
    path('dashboard/', DashboardView.as_view(), name='dashboard')
]
