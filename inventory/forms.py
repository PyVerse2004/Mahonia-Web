from django import forms

from .models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["name", "stock_quantity", "purchase_price", "sale_price"]

        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "نام محصول"}
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
        # موجودی فقط هنگام ساخت محصول وارد می‌شود. بعد از آن باید فقط از مسیر
        # فاکتور خرید و فروش تغییر کند تا دو منبع حقیقت پیدا نشود.
        if self.instance.pk:
            stock = self.fields["stock_quantity"]
            stock.disabled = True
            stock.help_text = "موجودی از طریق فاکتور خرید و فروش تغییر می‌کند."
