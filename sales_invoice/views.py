from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from inventory.services import StockError

from .forms import SaleFilterForm, SaleForm
from .models import Sale
from .services import create_sale, toggle_sale_active, update_sale


class SaleListView(PermissionRequiredMixin, ListView):
    permission_required = "sales_invoice.view_sale"
    template_name = "sales_invoice/sale_list.html"
    context_object_name = "sales"
    paginate_by = 20

    def get_filter_form(self):
        if not hasattr(self, "_filter_form"):
            self._filter_form = SaleFilterForm(self.request.GET)
        return self._filter_form

    def get_queryset(self):
        sales = Sale.objects.select_related("product")
        form = self.get_filter_form()
        if not form.is_valid():
            return sales.none()

        query = (form.cleaned_data.get("q") or "").strip()
        selected_date = form.cleaned_data.get("date")
        is_active = form.cleaned_data.get("is_active")

        if query:
            sales = sales.filter(product_name__icontains=query)
        if selected_date:
            sales = sales.filter(date=selected_date)
        if is_active == "1":
            sales = sales.filter(is_active=True)
        elif is_active == "0":
            sales = sales.filter(is_active=False)

        return sales

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.get_filter_form()
        return context


class SaleCreateView(PermissionRequiredMixin, CreateView):
    permission_required = "sales_invoice.add_sale"
    form_class = SaleForm
    template_name = "sales_invoice/sale_form.html"
    success_url = reverse_lazy("sales_invoice:sale_list")

    def form_valid(self, form):
        try:
            self.object = create_sale(form)
        except StockError as error:
            form.add_error(None, str(error))
            return self.form_invalid(form)

        messages.success(self.request, "فاکتور فروش با موفقیت ثبت شد و از موجودی انبار کسر گردید.")
        return HttpResponseRedirect(self.get_success_url())


class SaleUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = "sales_invoice.change_sale"
    model = Sale
    form_class = SaleForm
    template_name = "sales_invoice/sale_form.html"
    success_url = reverse_lazy("sales_invoice:sale_list")

    def form_valid(self, form):
        try:
            self.object = update_sale(form)
        except StockError as error:
            form.add_error(None, str(error))
            return self.form_invalid(form)

        messages.success(self.request, "فاکتور فروش با موفقیت ویرایش شد.")
        return HttpResponseRedirect(self.get_success_url())


class SaleToggleActiveView(PermissionRequiredMixin, View):
    permission_required = "sales_invoice.delete_sale"

    def get(self, request, pk):
        sale = get_object_or_404(Sale, pk=pk)
        return redirect("sales_invoice:sale_list")

    def post(self, request, pk):
        sale = get_object_or_404(Sale, pk=pk)
        is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest" or "application/json" in request.headers.get("accept", "")
        try:
            is_active = toggle_sale_active(sale)
        except StockError as error:
            error_msg = f"خطا در تغییر وضعیت فاکتور فروش: {error}"
            if is_ajax:
                return JsonResponse({"status": "error", "message": error_msg}, status=400)
            messages.error(request, error_msg)
            return redirect("sales_invoice:sale_list")

        if is_active:
            msg = f"فاکتور فروش شماره {sale.pk} مجدداً فعال شد و تعداد آن از انبار کسر گردید."
        else:
            msg = f"فاکتور فروش شماره {sale.pk} غیرفعال شد و تعداد آن به موجودی انبار بازگردانده شد."

        if is_ajax:
            return JsonResponse({
                "status": "success",
                "is_active": is_active,
                "message": msg,
                "sale_id": sale.pk,
            })

        messages.success(request, msg)
        return redirect("sales_invoice:sale_list")
