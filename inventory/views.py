from .models import Product
from .forms import ProductForm
from django.shortcuts import render
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

# Create your views here.
class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = "product_list.html"
    context_object_name = "products"
    paginate_by = 20
    login_url = "accounts:login"

    def get_queryset(self):
        return Product.objects.filter(is_active= True).only( "id","name","stock_quantity","sale_price","is_active",).order_by("name")


class ProductCreateView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = "product_form.html"
    success_url = reverse_lazy("product_list")
    login_url = "accounts:login"
    

class ProductUpdateView(LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = "product_form.html"
    success_url = reverse_lazy("product_list")
    login_url = "accounts:login"


class ProductDeleteView(LoginRequiredMixin, DeleteView):
    model = Product
    template_name = "product_confirm_delete.html"
    success_url = reverse_lazy("product_list")
    login_url = "accounts:login"

    def form_valid(self, form):
        self.object = self.get_object()
        self.object.is_active = False
        self.object.save(update_fields=["is_active", "updated_at"])

        return HttpResponseRedirect(self.get_success_url())