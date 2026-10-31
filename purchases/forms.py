from django import forms
from django.forms import inlineformset_factory

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
    class Meta:
        model = PurchaseInvoice
        fields = ["date", "supplier"]
        widgets = {
            "date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date", "class": "form-control"},
            ),
            "supplier": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["supplier"].empty_label = "انتخاب تامین‌کننده"


class PurchaseItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseItem
        fields = ["product", "quantity", "unit_price"]
        widgets = {
            "product": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "unit_price": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "step": 1}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].empty_label = "انتخاب محصول"


# حداقل یک ردیف لازم است؛ ردیف جدید با جاوااسکریپت اضافه می‌شود.
PurchaseItemFormSet = inlineformset_factory(
    PurchaseInvoice,
    PurchaseItem,
    form=PurchaseItemForm,
    extra=0,
    min_num=1,
    validate_min=True,
    can_delete=True,
)
