from django.urls import path

from .views import SaleCreateView, SaleListView

app_name = "daily_sales"

urlpatterns = [
    path("", SaleListView.as_view(), name="sale_list"),
    path("create/", SaleCreateView.as_view(), name="sale_create"),
]
