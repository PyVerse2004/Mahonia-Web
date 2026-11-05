from decimal import Decimal

from django import forms
from django.utils import timezone
from jalali_date import date2jalali
from jalali_date.fields import JalaliDateField
from jalali_date.widgets import AdminJalaliDateWidget

from .models import Person


class PersonFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="نام بدهکار",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "جستجو در نام بدهکار یا نام محصول...",
                "id": "id_q",
            }
        ),
    )
    status = forms.ChoiceField(
        choices=[("", "همه وضعیت‌ها"), *Person.AccountStatus.choices],
        required=False,
        label="وضعیت حساب",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_filter_status"}),
    )
    date = JalaliDateField(
        input_formats=["%Y-%m-%d", "%Y/%m/%d"],
        required=False,
        label="تاریخ",
        error_messages={"invalid": "تاریخ را به شکل سال/ماه/روز شمسی وارد کنید."},
        widget=AdminJalaliDateWidget(
            attrs={
                "class": "form-control",
                "placeholder": "۱۴۰۵-۰۸-۱۲",
                "autocomplete": "off",
                "id": "id_filter_date",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["date"].widget.attrs["data-today"] = date2jalali(
            timezone.localdate()
        ).strftime("%Y-%m-%d")


class PersonForm(forms.ModelForm):
    date = JalaliDateField(
        input_formats=["%Y-%m-%d", "%Y/%m/%d"],
        label="تاریخ",
        widget=AdminJalaliDateWidget(
            attrs={
                "class": "form-control",
                "placeholder": "۱۴۰۵-۰۸-۱۲",
                "autocomplete": "off",
                "id": "id_date",
            }
        ),
    )
    payment_amount = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=0,
        label="مبلغ پرداختی جدید (کسر از بدهی)",
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "placeholder": "مبلغ پرداختی جدید...",
                "id": "id_payment_amount",
            }
        ),
    )

    class Meta:
        model = Person
        fields = [
            "date",
            "product_name",
            "debtor_name",
            "phone_number",
            "debt_amount",
            "paid_amount",
            "status",
        ]
        widgets = {
            "product_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "نام محصول..."}
            ),
            "debtor_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "نام بدهکار..."}
            ),
            "phone_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "شماره تماس (اختیاری)...",
                    "dir": "ltr",
                }
            ),
            "debt_amount": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "step": 1, "id": "id_debt_amount"}
            ),
            "paid_amount": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "step": 1, "id": "id_paid_amount"}
            ),
            "status": forms.Select(attrs={"class": "form-select", "id": "id_status"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phone_number"].required = False
        self.fields["paid_amount"].required = False
        if not self.instance.pk and "paid_amount" not in self.initial:
            self.initial["paid_amount"] = 0
        self.fields["date"].widget.attrs["data-today"] = date2jalali(
            timezone.localdate()
        ).strftime("%Y-%m-%d")

    def clean(self):
        cleaned_data = super().clean()
        debt_amount = cleaned_data.get("debt_amount") or Decimal("0")
        paid_amount = cleaned_data.get("paid_amount") or Decimal("0")
        payment_amount = cleaned_data.get("payment_amount") or Decimal("0")
        status = cleaned_data.get("status")

        # If a payment was made, add it to paid_amount
        if payment_amount > 0:
            paid_amount += payment_amount

        # Automatic settlement if paid_amount reaches or exceeds debt_amount
        if debt_amount > 0 and paid_amount >= debt_amount:
            status = Person.AccountStatus.SETTLED
            paid_amount = debt_amount

        if status == Person.AccountStatus.SETTLED and debt_amount > 0:
            paid_amount = debt_amount

        if status == Person.AccountStatus.DEBTOR and debt_amount > 0 and paid_amount > debt_amount:
            self.add_error(
                "paid_amount",
                f"مبلغ پرداخت‌شده نمی‌تواند بیشتر از مبلغ بدهکاری ({debt_amount:,.0f} تومان) باشد.",
            )

        cleaned_data["paid_amount"] = paid_amount
        cleaned_data["status"] = status
        return cleaned_data
