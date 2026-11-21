from django import forms
from django.utils import timezone
from jalali_date import date2jalali
from jalali_date.fields import JalaliDateField

from inventory.models import Decant, Product
from mahonia.widgets import JalaliDateInput
from .models import Sale


class SaleFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="جستجو",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "نام محصول یا دکانت...", "id": "id_q"}
        ),
    )
    item_type = forms.ChoiceField(
        choices=[
            ("", "همه قلم‌ها"),
            (Sale.ITEM_TYPE_PRODUCT, "فقط کالاها"),
            (Sale.ITEM_TYPE_DECANT, "فقط دکانت‌ها"),
        ],
        required=False,
        label="نوع قلم",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_item_type"}),
    )
    is_active = forms.ChoiceField(
        choices=[
            ("", "همه فاکتورها"),
            ("1", "فقط فعال"),
            ("0", "فقط غیرفعال"),
        ],
        required=False,
        label="وضعیت",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_is_active"}),
    )
    date = JalaliDateField(
        input_formats=["%Y-%m-%d", "%Y/%m/%d"],
        required=False,
        label="تاریخ فاکتور",
        error_messages={"invalid": "تاریخ را به شکل سال/ماه/روز شمسی وارد کنید."},
        widget=JalaliDateInput(
            attrs={
                "class": "form-control",
                "placeholder": "۱۴۰۵-۰۸-۱۲",
                "autocomplete": "off",
                "id": "id_date",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].widget.attrs["data-today"] = date2jalali(
            timezone.localdate()
        ).strftime("%Y-%m-%d")


class SaleForm(forms.ModelForm):
    date = JalaliDateField(
        input_formats=["%Y-%m-%d", "%Y/%m/%d"],
        label="تاریخ فاکتور",
        widget=JalaliDateInput(
            attrs={
                "class": "form-control",
                "placeholder": "۱۴۰۵-۰۸-۱۲",
                "autocomplete": "off",
            }
        ),
    )

    item_type = forms.ChoiceField(
        choices=Sale.ITEM_TYPE_CHOICES,
        label="نوع فروش",
        widget=forms.RadioSelect(attrs={"class": "btn-check"}),
        initial=Sale.ITEM_TYPE_PRODUCT,
    )

    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        required=False,
        empty_label="انتخاب محصول...",
        label="محصول (شیشه کامل)",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_product"}),
    )

    decant = forms.ModelChoiceField(
        queryset=Decant.objects.all(),
        required=False,
        empty_label="انتخاب دکانت...",
        label="دکانت عطر",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_decant"}),
    )

    class Meta:
        model = Sale
        fields = [
            "date",
            "item_type",
            "product",
            "decant",
            "quantity",
            "unit_price",
        ]
        widgets = {
            "quantity": forms.NumberInput(
                attrs={"class": "form-control", "min": 1, "step": 1}
            ),
            "unit_price": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "step": 1000}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.all().order_by("name")
        self.fields["decant"].queryset = Decant.objects.all().order_by("perfume_name", "volume")
        self.fields["date"].widget.attrs["data-today"] = date2jalali(
            timezone.localdate()
        ).strftime("%Y-%m-%d")

    def clean(self):
        cleaned_data = super().clean()
        item_type = cleaned_data.get("item_type")
        product = cleaned_data.get("product")
        decant = cleaned_data.get("decant")
        quantity = cleaned_data.get("quantity") or 0

        if item_type == Sale.ITEM_TYPE_DECANT:
            if not decant:
                self.add_error("decant", "لطفاً یک دکانت عطر را انتخاب کنید.")
            else:
                # بررسی موجودی دکانت
                available_stock = decant.stock_quantity
                if self.instance and self.instance.pk and self.instance.decant_id == decant.pk:
                    available_stock += self.instance.quantity
                if quantity > available_stock:
                    self.add_error(
                        "quantity",
                        f"موجودی دکانت «{decant.perfume_name} ({decant.get_volume_display()})» کافی نیست. موجودی انبار: {available_stock} عدد",
                    )
        else:
            if not product:
                self.add_error("product", "لطفاً یک محصول را انتخاب کنید.")
            else:
                # بررسی موجودی کالا
                available_stock = product.stock_quantity
                if self.instance and self.instance.pk and self.instance.product_id == product.pk:
                    available_stock += self.instance.quantity
                if quantity > available_stock:
                    self.add_error(
                        "quantity",
                        f"موجودی محصول «{product.name}» کافی نیست. موجودی انبار: {available_stock} عدد",
                    )

        return cleaned_data
