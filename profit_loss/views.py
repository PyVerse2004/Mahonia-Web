from django.contrib.auth.mixins import PermissionRequiredMixin
from django.views.generic import ListView

from .forms import JALALI_MONTH_CHOICES, ProfitLossFilterForm
from .services import get_profit_loss_report


class ProfitLossReportView(PermissionRequiredMixin, ListView):
    permission_required = "sales_invoice.view_sale"
    template_name = "profit_loss/report.html"
    context_object_name = "sales"
    paginate_by = 30

    def get_filter_form(self):
        if not hasattr(self, "_filter_form"):
            self._filter_form = ProfitLossFilterForm(self.request.GET)
        return self._filter_form

    def get_queryset(self):
        form = self.get_filter_form()
        year = None
        month = None
        product_id = None
        query = None

        if form.is_valid():
            year = form.cleaned_data.get("year")
            month = form.cleaned_data.get("month")
            product = form.cleaned_data.get("product")
            if product:
                product_id = product.pk
            query = form.cleaned_data.get("q")

        sales, summary = get_profit_loss_report(
            year=year,
            month=month,
            product_id=product_id,
            query=query,
        )
        self.summary_data = summary
        return sales

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = self.get_filter_form()
        context["filter_form"] = form
        context["summary"] = getattr(self, "summary_data", {})

        # Find selected month name
        selected_month_val = form.cleaned_data.get("month") if form.is_valid() else ""
        month_dict = dict(JALALI_MONTH_CHOICES)
        context["selected_month_name"] = month_dict.get(selected_month_val, "")
        context["selected_year_val"] = form.cleaned_data.get("year") if form.is_valid() else ""

        return context
