from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from inventory.models import Product

from .forms import PersonFilterForm, PersonForm
from .models import Person


class PersonListView(PermissionRequiredMixin, ListView):
    permission_required = "persons.view_person"
    template_name = "persons/person_list.html"
    context_object_name = "persons"
    paginate_by = 20

    def get_filter_form(self):
        if not hasattr(self, "_filter_form"):
            self._filter_form = PersonFilterForm(self.request.GET)
        return self._filter_form

    def get_queryset(self):
        queryset = Person.objects.all()
        form = self.get_filter_form()
        if not form.is_valid():
            return queryset.none()

        query = (form.cleaned_data.get("q") or "").strip()
        status = form.cleaned_data.get("status")
        selected_date = form.cleaned_data.get("date")

        if query:
            queryset = queryset.filter(
                Q(debtor_name__icontains=query) | Q(product_name__icontains=query)
            )
        if status:
            queryset = queryset.filter(status=status)
        if selected_date:
            queryset = queryset.filter(date=selected_date)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.get_filter_form()
        return context


class PersonCreateView(PermissionRequiredMixin, CreateView):
    permission_required = "persons.add_person"
    model = Person
    form_class = PersonForm
    template_name = "persons/person_form.html"
    success_url = reverse_lazy("persons:person_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["available_products"] = Product.objects.all().order_by("name")
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "اطلاعات شخص با موفقیت ثبت شد.")
        return response


class PersonUpdateView(PermissionRequiredMixin, UpdateView):
    permission_required = "persons.change_person"
    model = Person
    form_class = PersonForm
    template_name = "persons/person_form.html"
    success_url = reverse_lazy("persons:person_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["available_products"] = Product.objects.all().order_by("name")
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "اطلاعات شخص با موفقیت به‌روزرسانی شد.")
        return response


class PersonDeleteView(PermissionRequiredMixin, DeleteView):
    permission_required = "persons.delete_person"
    model = Person
    template_name = "persons/person_confirm_delete.html"
    success_url = reverse_lazy("persons:person_list")

    def form_valid(self, form):
        messages.success(self.request, "اطلاعات شخص با موفقیت حذف شد.")
        return super().form_valid(form)


class PersonSettleView(PermissionRequiredMixin, View):
    permission_required = "persons.change_person"

    def get(self, request, pk):
        return redirect("persons:person_list")

    def post(self, request, pk):
        person = get_object_or_404(Person, pk=pk)
        person.status = Person.AccountStatus.SETTLED
        person.paid_amount = person.debt_amount
        person.save(update_fields=["status", "paid_amount", "updated_at"])
        messages.success(request, f"حساب «{person.debtor_name}» با موفقیت به تسویه‌شده تغییر یافت.")
        return redirect("persons:person_list")
