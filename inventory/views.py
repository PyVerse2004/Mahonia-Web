from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import ProductForm
from .models import Product, StockMovement
from .services import change_stock


class ProductListView(PermissionRequiredMixin, ListView):
    permission_required = "inventory.view_product"
    model = Product
    template_name = "inventory/product_list.html"
    context_object_name = "products"
    paginate_by = 20


class ProductCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = "inventory.add_product"
    model = Product
    form_class = ProductForm
    template_name = "inventory/product_form.html"
    success_url = reverse_lazy("inventory:product_list")
    success_message = "محصول «%(name)s» ثبت شد."

    @transaction.atomic
    def form_valid(self, form):
        initial_stock = form.cleaned_data["stock_quantity"]
        form.instance.stock_quantity = 0
        response = super().form_valid(form)
        if initial_stock:
            change_stock(
                self.object.pk,
                initial_stock,
                reason="ثبت موجودی اولیه",
            )
        return response


class ProductUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = "inventory.change_product"
    model = Product
    form_class = ProductForm
    template_name = "inventory/product_form.html"
    success_url = reverse_lazy("inventory:product_list")
    success_message = "محصول «%(name)s» ویرایش شد."


class ProductDeleteView(PermissionRequiredMixin, DeleteView):
    """محصول را برای همیشه از دیتابیس حذف می‌کند."""

    permission_required = "inventory.delete_product"
    model = Product
    template_name = "inventory/product_confirm_delete.html"
    success_url = reverse_lazy("inventory:product_list")

    def form_valid(self, form):
        name = self.object.name
        response = super().form_valid(form)
        messages.success(self.request, f"محصول «{name}» حذف شد.")
        return response


class StockMovementListView(PermissionRequiredMixin, ListView):
    permission_required = "inventory.view_product"
    model = StockMovement
    template_name = "inventory/stock_movement_list.html"
    context_object_name = "movements"
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset().select_related("product")
        product_id = self.request.GET.get("product")
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["products"] = Product.objects.order_by("name", "id")
        context["selected_product"] = self.request.GET.get("product", "")
        return context
