from django import forms
from django.utils import timezone
from jalali_date import date2jalali
from jalali_date.fields import JalaliDateField

from mahonia.widgets import JalaliDateInput
from .models import Product


class StockMovementFilterForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.none(),
        required=False,
        empty_label="همه محصولات",
        label="محصول",
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    date = JalaliDateField(
        input_formats=["%Y-%m-%d", "%Y/%m/%d"],
        required=False,
        label="تاریخ",
        error_messages={"invalid": "تاریخ را به شکل سال/ماه/روز شمسی وارد کنید."},
        widget=JalaliDateInput(
            attrs={
                "class": "form-control",
                "placeholder": "۱۴۰۵-۰۸-۱۲",
                "autocomplete": "off",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.order_by("name", "id")
        self.fields["date"].widget.attrs["data-today"] = date2jalali(
            timezone.localdate()
        ).strftime("%Y-%m-%d")


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "image", "stock_quantity", "purchase_price", "sale_price"]

        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "نام محصول"}
            ),
            "image": forms.FileInput(
                attrs={"class": "form-control", "accept": "image/*", "id": "id_image"}
            ),
            "stock_quantity": forms.NumberInput(
                attrs={"class": "form-control", "min": 0}
            ),
            "purchase_price": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "step": 1}
            ),
            "sale_price": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "step": 1}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # موجودی و قیمت خرید فقط هنگام ساخت محصول (به‌عنوان مقدار اولیه) وارد
        # می‌شوند. بعد از آن موجودی با فاکتور خرید و فروش تغییر می‌کند و قیمت خرید
        # میانگین فاکتورهای خرید است.
        if self.instance.pk:
            stock = self.fields["stock_quantity"]
            stock.disabled = True
            stock.help_text = "موجودی از طریق فاکتور خرید و فروش تغییر می‌کند."

            price = self.fields["purchase_price"]
            price.disabled = True
            price.help_text = "میانگین قیمت خرید در فاکتورهای خرید است."
