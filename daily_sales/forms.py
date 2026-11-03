from django import forms
from django.utils import timezone
from jalali_date import date2jalali
from jalali_date.fields import JalaliDateField
from jalali_date.widgets import AdminJalaliDateWidget

from .models import Sale


class SaleForm(forms.ModelForm):
    date = JalaliDateField(
        input_formats=["%Y-%m-%d", "%Y/%m/%d"],
        label="تاریخ فروش",
        widget=AdminJalaliDateWidget(
            attrs={
                "class": "form-control",
                "placeholder": "۱۴۰۵-۰۸-۱۲",
                "autocomplete": "off",
            }
        ),
    )

    class Meta:
        model = Sale
        fields = [
            "date",
            "product",
            "quantity",
            "unit_price",
            "status",
            "debtor_name",
        ]
        widgets = {
            "product": forms.Select(attrs={"class": "form-select"}),
            "quantity": forms.NumberInput(
                attrs={"class": "form-control", "min": 1, "step": 1}
            ),
            "unit_price": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "step": 1}
            ),
            "status": forms.Select(attrs={"class": "form-select"}),
            "debtor_name": forms.TextInput(
                attrs={"class": "form-control", "autocomplete": "off"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].empty_label = "انتخاب محصول"
        self.fields["product"].required = True
        self.fields["debtor_name"].required = False
        self.fields["date"].widget.attrs["data-today"] = date2jalali(
            timezone.localdate()
        ).strftime("%Y-%m-%d")

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get("status")
        debtor_name = (cleaned_data.get("debtor_name") or "").strip()
        if status == Sale.AccountStatus.DEBT and not debtor_name:
            self.add_error("debtor_name", "برای حساب بدهکار، نام بدهکار را وارد کنید.")
        elif status == Sale.AccountStatus.SETTLED:
            cleaned_data["debtor_name"] = ""
        else:
            cleaned_data["debtor_name"] = debtor_name
        return cleaned_data
