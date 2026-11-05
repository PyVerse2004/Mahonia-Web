from django.urls import path

from .views import (
    SaleCreateView,
    SaleListView,
    SaleToggleActiveView,
    SaleUpdateView,
)

app_name = "daily_sales"

urlpatterns = [
    path("", SaleListView.as_view(), name="sale_list"),
    path("create/", SaleCreateView.as_view(), name="sale_create"),
    path("<int:pk>/edit/", SaleUpdateView.as_view(), name="sale_update"),
    path("<int:pk>/toggle-active/", SaleToggleActiveView.as_view(), name="sale_toggle_active"),
]
