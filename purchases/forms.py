from django import forms
from django.forms import inlineformset_factory
from django.utils import timezone
from jalali_date import date2jalali
from jalali_date.fields import JalaliDateField

from mahonia.widgets import JalaliDateInput
from inventory.models import Product

from .models import PurchaseInvoice, PurchaseItem, Supplier


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "نام شرکت"}
            ),
        }


class PurchaseInvoiceForm(forms.ModelForm):
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

    class Meta:
        model = PurchaseInvoice
        fields = ["date", "supplier"]
        widgets = {
            "supplier": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["supplier"].empty_label = "انتخاب تامین‌کننده"
        self.fields["date"].widget.attrs["data-today"] = date2jalali(
            timezone.localdate()
        ).strftime("%Y-%m-%d")


class PurchaseItemForm(forms.ModelForm):
    # Product name: selects an existing product or designates a new product name.
    product_text = forms.CharField(
        max_length=200,
        label="محصول",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "list": "product-options",
                "autocomplete": "off",
                "placeholder": "نام محصول را انتخاب یا تایپ کنید",
            }
        ),
    )

    field_order = ["product_text", "quantity", "unit_price"]

    class Meta:
        model = PurchaseItem
        fields = ["quantity", "unit_price"]
        widgets = {
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "unit_price": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "step": 1}
            ),
        }

    def __init__(self, *args, can_create_products=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.can_create_products = can_create_products
        # Holds newly designated product name to be created atomically during invoice persistence.
        self.new_product_name = None

        item = self.instance
        if item.pk:
            self.initial.setdefault(
                "product_text", item.product.name if item.product_id else item.product_name
            )

    def clean_product_text(self):
        # Strip redundant whitespace so that "Legend " and "Legend" are treated identically.
        return " ".join(self.cleaned_data["product_text"].split())

    def clean(self):
        cleaned_data = super().clean()
        name = cleaned_data.get("product_text")
        if not name:
            return cleaned_data

        product = Product.objects.filter(name__iexact=name).first()
        if product:
            self.instance.product = product
        elif (
            self.instance.pk
            and not self.instance.product_id
            and name == self.instance.product_name
        ):
            # Legacy row whose linked product was subsequently deleted; leave untouched.
            pass
        elif self.can_create_products:
            self.new_product_name = name
        else:
            self.add_error(
                "product_text",
                f"محصول «{name}» وجود ندارد و اجازه‌ی ثبت محصول جدید را ندارید.",
            )
        return cleaned_data


# At least one item row is required; additional rows are added dynamically via JS.
PurchaseItemFormSet = inlineformset_factory(
    PurchaseInvoice,
    PurchaseItem,
    form=PurchaseItemForm,
    extra=0,
    min_num=1,
    validate_min=True,
    can_delete=True,
)
