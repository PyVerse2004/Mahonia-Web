from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from inventory.services import StockError

from . import services
from .forms import PurchaseInvoiceForm, PurchaseItemFormSet, SupplierForm
from .models import PurchaseInvoice, Supplier


# ---------- تامین‌کننده ----------


class SupplierListView(PermissionRequiredMixin, ListView):
    permission_required = "purchases.view_supplier"
    model = Supplier
    template_name = "purchases/supplier_list.html"
    context_object_name = "suppliers"
    paginate_by = 20


class SupplierCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = "purchases.add_supplier"
    model = Supplier
    form_class = SupplierForm
    template_name = "purchases/supplier_form.html"
    success_url = reverse_lazy("purchases:supplier_list")
    success_message = "تامین‌کننده «%(name)s» ثبت شد."


class SupplierUpdateView(PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    permission_required = "purchases.change_supplier"
    model = Supplier
    form_class = SupplierForm
    template_name = "purchases/supplier_form.html"
    success_url = reverse_lazy("purchases:supplier_list")
    success_message = "تامین‌کننده «%(name)s» ویرایش شد."


# ---------- فاکتور خرید ----------


class InvoiceListView(PermissionRequiredMixin, ListView):
    permission_required = "purchases.view_purchaseinvoice"
    template_name = "purchases/invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 20
    queryset = PurchaseInvoice.objects.select_related("supplier")


class InvoiceEditMixin(PermissionRequiredMixin):
    """منطق مشترک ساخت و ویرایش: یک فرم فاکتور + یک formset برای ردیف‌ها."""

    model = PurchaseInvoice
    form_class = PurchaseInvoiceForm
    template_name = "purchases/invoice_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault("formset", PurchaseItemFormSet(instance=self.object))
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object() if "pk" in self.kwargs else None
        form = self.get_form()
        formset = PurchaseItemFormSet(request.POST, instance=form.instance)

        if form.is_valid() and formset.is_valid():
            try:
                invoice = services.save_invoice(form, formset)
            except StockError as error:
                form.add_error(None, str(error))
            else:
                messages.success(request, self.success_text % invoice.pk)
                return redirect("purchases:invoice_list")

        return self.render_to_response(self.get_context_data(form=form, formset=formset))


class InvoiceCreateView(InvoiceEditMixin, CreateView):
    permission_required = "purchases.add_purchaseinvoice"
    success_text = "فاکتور خرید شماره %s ثبت شد."


class InvoiceUpdateView(InvoiceEditMixin, UpdateView):
    permission_required = "purchases.change_purchaseinvoice"
    success_text = "فاکتور خرید شماره %s ویرایش شد."


class InvoiceDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = "purchases.delete_purchaseinvoice"
    model = PurchaseInvoice
    template_name = "purchases/invoice_confirm_delete.html"
    success_url = reverse_lazy("purchases:invoice_list")

    def form_valid(self, form):
        number = self.object.pk
        try:
            services.delete_invoice(self.object)
        except StockError as error:
            messages.error(self.request, f"حذف انجام نشد. {error}")
            return redirect(self.success_url)
        messages.success(self.request, f"فاکتور خرید شماره {number} حذف شد.")
        return redirect(self.success_url)
