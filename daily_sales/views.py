from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from .forms import SaleForm
from .models import Sale


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


class SaleCreateView(PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    permission_required = "daily_sales.add_sale"
    form_class = SaleForm
    template_name = "daily_sales/sale_form.html"
    success_url = reverse_lazy("daily_sales:sale_list")
    success_message = "فروش با موفقیت ثبت شد."
