from django.urls import path

from .views import (
    DecantCreateView,
    DecantDeleteView,
    DecantListView,
    DecantUpdateView,
    ProductCreateView,
    ProductDeleteView,
    ProductListView,
    ProductUpdateView,
    StockMovementListView,
)

app_name = "inventory"

urlpatterns = [
    path("", ProductListView.as_view(), name="product_list"),
    path("stock-card/", StockMovementListView.as_view(), name="stock_movement_list"),
    path("create/", ProductCreateView.as_view(), name="product_create"),
    path("<int:pk>/edit/", ProductUpdateView.as_view(), name="product_update"),
    path("<int:pk>/delete/", ProductDeleteView.as_view(), name="product_delete"),
    # دکانت‌های عطر
    path("decants/", DecantListView.as_view(), name="decant_list"),
    path("decants/create/", DecantCreateView.as_view(), name="decant_create"),
    path("decants/<int:pk>/edit/", DecantUpdateView.as_view(), name="decant_update"),
    path("decants/<int:pk>/delete/", DecantDeleteView.as_view(), name="decant_delete"),
]
