from django.urls import path

from .views import (
    ProductCreateView,
    ProductDeleteView,
    ProductListView,
    ProductUpdateView,
)

app_name = "inventory"

urlpatterns = [
    path("", ProductListView.as_view(), name="product_list"),
    path("create/", ProductCreateView.as_view(), name="product_create"),
    path("<int:pk>/edit/", ProductUpdateView.as_view(), name="product_update"),
    path("<int:pk>/delete/", ProductDeleteView.as_view(), name="product_delete"),
]
