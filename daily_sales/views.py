from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from inventory.services import StockError

from .forms import SaleForm
from .models import Sale
from .services import create_sale, delete_sale, settle_sale, update_sale


class SaleListView(PermissionRequiredMixin, ListView):
    permission_required = "daily_sales.view_sale"
    template_name = "daily_sales/sale_list.html"
    context_object_name = "sales"
    paginate_by = 20

    def get_queryset(self):
        sales = Sale.objects.select_related("product")
        query = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "")
        if query:
            sales = sales.filter(
                Q(product_name__icontains=query) | Q(debtor_name__icontains=query)
            )
        if status in Sale.AccountStatus.values:
            sales = sales.filter(status=status)
        return sales

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "").strip()
        context["selected_status"] = self.request.GET.get("status", "")
        context["status_choices"] = Sale.AccountStatus.choices
        return context


class SaleCreateView(PermissionRequiredMixin, CreateView):
    permission_required = "daily_sales.add_sale"
    form_class = SaleForm
    template_name = "daily_sales/sale_form.html"
    success_url = reverse_lazy("daily_sales:sale_list")

    def form_valid(self, form):
        try:
            self.object = create_sale(form)
        except StockError as error:
            form.add_error(None, str(error))
            return self.form_invalid(form)

        messages.success(self.request, "فروش با موفقیت ثبت شد و از موجودی انبار کسر شد.")
        return HttpResponseRedirect(self.get_success_url())


class SaleUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = "daily_sales.change_sale"
    model = Sale
    form_class = SaleForm
    template_name = "daily_sales/sale_form.html"
    success_url = reverse_lazy("daily_sales:sale_list")

    def form_valid(self, form):
        try:
            self.object = update_sale(form)
        except StockError as error:
            form.add_error(None, str(error))
            return self.form_invalid(form)

        messages.success(self.request, "فروش و موجودی انبار با موفقیت ویرایش شدند.")
        return HttpResponseRedirect(self.get_success_url())


class SaleDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = "daily_sales.delete_sale"
    model = Sale
    template_name = "daily_sales/sale_confirm_delete.html"
    success_url = reverse_lazy("daily_sales:sale_list")

    def form_valid(self, form):
        sale_reference = self.object.pk
        try:
            delete_sale(self.object)
        except StockError as error:
            messages.error(self.request, f"حذف فروش انجام نشد. {error}")
            return redirect(self.success_url)

        messages.success(
            self.request,
            f"فروش شماره {sale_reference} حذف و تعداد آن به موجودی انبار بازگردانده شد.",
        )
        return HttpResponseRedirect(self.get_success_url())


class SaleSettleView(PermissionRequiredMixin, View):
    permission_required = "daily_sales.change_sale"

    def post(self, request, *args, **kwargs):
        sale = get_object_or_404(Sale, pk=kwargs["pk"])
        if settle_sale(sale):
            messages.success(request, "وضعیت فروش به تسویه‌شده تغییر کرد.")
        return redirect("daily_sales:sale_list")
