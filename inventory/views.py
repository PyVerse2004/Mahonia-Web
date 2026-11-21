from datetime import datetime, time, timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.utils import timezone
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from .forms import DecantFilterForm, DecantForm, ProductForm, StockMovementFilterForm
from .models import Decant, Product, StockMovement
from .services import change_decant_stock, change_stock


def _clean_price_filter(value: str):
    """Clean string price input: normalize Persian/Arabic digits, strip commas, return Decimal or None."""
    if not value:
        return None
    val_str = str(value)
    persian_digits = "۰۱۲۳۴۵۶۷۸۹"
    arabic_digits = "٠١٢٣٤٥٦٧٨٩"
    for i, d in enumerate(persian_digits):
        val_str = val_str.replace(d, str(i))
    for i, d in enumerate(arabic_digits):
        val_str = val_str.replace(d, str(i))
    val_str = val_str.replace(",", "").replace("،", "").replace(" ", "").strip()
    try:
        dec = Decimal(val_str)
        return dec if dec >= 0 else None
    except (InvalidOperation, ValueError):
        return None


class ProductListView(PermissionRequiredMixin, ListView):
    permission_required = "inventory.view_product"
    model = Product
    template_name = "inventory/product_list.html"
    context_object_name = "products"
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get("q", "").strip()
        if query:
            queryset = queryset.filter(name__icontains=query)

        # Exclusive filter by sale price (purchase price is deliberately excluded)
        min_price = _clean_price_filter(self.request.GET.get("min_price"))
        if min_price is not None:
            queryset = queryset.filter(sale_price__gte=min_price)

        max_price = _clean_price_filter(self.request.GET.get("max_price"))
        if max_price is not None:
            queryset = queryset.filter(sale_price__lte=max_price)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "").strip()
        context["min_price"] = self.request.GET.get("min_price", "").strip()
        context["max_price"] = self.request.GET.get("max_price", "").strip()
        return context


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
    """Permanently delete product from the database."""

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

    def get_filter_form(self):
        if not hasattr(self, "_filter_form"):
            self._filter_form = StockMovementFilterForm(self.request.GET)
        return self._filter_form

    def get_queryset(self):
        queryset = super().get_queryset().select_related("product")
        form = self.get_filter_form()
        if not form.is_valid():
            return queryset.none()

        product = form.cleaned_data.get("product")
        if product:
            queryset = queryset.filter(product=product)

        selected_date = form.cleaned_data.get("date")
        if selected_date:
            local_start = timezone.make_aware(
                datetime.combine(selected_date, time.min)
            )
            local_end = local_start + timedelta(days=1)
            queryset = queryset.filter(
                created_at__gte=local_start,
                created_at__lt=local_end,
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.get_filter_form()
        return context


# ==============================================================================
# Perfume Decants (CRUD & Live Filter)
# ==============================================================================

class DecantListView(PermissionRequiredMixin, ListView):
    permission_required = "inventory.view_decant"
    model = Decant
    template_name = "inventory/decant_list.html"
    context_object_name = "decants"
    paginate_by = 24

    def get_filter_form(self):
        if not hasattr(self, "_filter_form"):
            self._filter_form = DecantFilterForm(self.request.GET)
        return self._filter_form

    def get_queryset(self):
        queryset = super().get_queryset()
        form = self.get_filter_form()
        if not form.is_valid():
            return queryset

        query = (form.cleaned_data.get("q") or "").strip()
        volume = form.cleaned_data.get("volume")

        if query:
            queryset = queryset.filter(perfume_name__icontains=query)
        if volume:
            queryset = queryset.filter(volume=volume)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.get_filter_form()
        context["filter_form"] = form
        context["search_query"] = self.request.GET.get("q", "").strip()
        context["selected_volume"] = self.request.GET.get("volume", "").strip()
        context["volume_choices"] = Decant.VOLUME_CHOICES
        return context


class DecantCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = "inventory.add_decant"
    model = Decant
    form_class = DecantForm
    template_name = "inventory/decant_form.html"
    success_url = reverse_lazy("inventory:decant_list")
    success_message = "دکانت «%(perfume_name)s (%(volume)s)» با موفقیت افزوده شد."

    @transaction.atomic
    def form_valid(self, form):
        initial_stock = form.cleaned_data.get("stock_quantity") or 0
        form.instance.stock_quantity = 0
        response = super().form_valid(form)
        if initial_stock > 0:
            change_decant_stock(
                self.object.pk,
                initial_stock,
                reason="ثبت موجودی اولیه دکانت",
            )
        return response


class DecantUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = "inventory.change_decant"
    model = Decant
    form_class = DecantForm
    template_name = "inventory/decant_form.html"
    success_url = reverse_lazy("inventory:decant_list")
    success_message = "دکانت «%(perfume_name)s (%(volume)s)» با موفقیت ویرایش شد."


class DecantDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = "inventory.delete_decant"
    model = Decant
    template_name = "inventory/decant_confirm_delete.html"
    success_url = reverse_lazy("inventory:decant_list")

    def form_valid(self, form):
        name = str(self.object)
        response = super().form_valid(form)
        messages.success(self.request, f"دکانت «{name}» حذف شد.")
        return response
