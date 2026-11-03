from django.urls import path

from .views import (
    SaleCreateView,
    SaleDeleteView,
    SaleListView,
    SaleSettleView,
    SaleUpdateView,
)

app_name = "daily_sales"

urlpatterns = [
    path("", SaleListView.as_view(), name="sale_list"),
    path("create/", SaleCreateView.as_view(), name="sale_create"),
    path("<int:pk>/edit/", SaleUpdateView.as_view(), name="sale_update"),
    path("<int:pk>/delete/", SaleDeleteView.as_view(), name="sale_delete"),
    path("<int:pk>/settle/", SaleSettleView.as_view(), name="sale_settle"),
]
