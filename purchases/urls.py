from django.urls import path

from .views import (
    InvoiceCreateView,
    InvoiceDeleteView,
    InvoiceListView,
    InvoiceUpdateView,
    SupplierCreateView,
    SupplierListView,
    SupplierUpdateView,
)

app_name = "purchases"

urlpatterns = [
    path("", InvoiceListView.as_view(), name="invoice_list"),
    path("create/", InvoiceCreateView.as_view(), name="invoice_create"),
    path("<int:pk>/edit/", InvoiceUpdateView.as_view(), name="invoice_update"),
    path("<int:pk>/delete/", InvoiceDeleteView.as_view(), name="invoice_delete"),
    path("suppliers/", SupplierListView.as_view(), name="supplier_list"),
    path("suppliers/create/", SupplierCreateView.as_view(), name="supplier_create"),
    path("suppliers/<int:pk>/edit/", SupplierUpdateView.as_view(), name="supplier_update"),
]
