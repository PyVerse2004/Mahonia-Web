from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import ProductForm
from .models import Product


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
