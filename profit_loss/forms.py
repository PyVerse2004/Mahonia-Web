from django import forms
import jdatetime

from sales_invoice.models import Sale
from inventory.models import Product

JALALI_MONTH_CHOICES = [
    ("", "همه ماه‌ها"),
    ("1", "فروردین"),
    ("2", "اردیبهشت"),
    ("3", "خرداد"),
    ("4", "تیر"),
    ("5", "مرداد"),
    ("6", "شهریور"),
    ("7", "مهر"),
    ("8", "آبان"),
    ("9", "آذر"),
    ("10", "دی"),
    ("11", "بهمن"),
    ("12", "اسفند"),
]


def get_year_choices():
    current_year = jdatetime.date.today().year
    years = {current_year, current_year - 1, current_year - 2}
    # Retrieve years from existing sales if any
    try:
        for s_date in Sale.objects.values_list("date", flat=True).distinct():
            if s_date:
                years.add(jdatetime.date.fromgregorian(date=s_date).year)
    except Exception:
        pass
    sorted_years = sorted(list(years), reverse=True)
    return [("", "همه سال‌ها")] + [(str(y), str(y)) for y in sorted_years]


class ProfitLossFilterForm(forms.Form):
    year = forms.ChoiceField(
        choices=(),
        required=False,
        label="سال",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_year"}),
    )
    month = forms.ChoiceField(
        choices=JALALI_MONTH_CHOICES,
        required=False,
        label="ماه",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_month"}),
    )
    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        required=False,
        empty_label="همه محصولات",
        label="محصول",
        widget=forms.Select(attrs={"class": "form-select", "id": "id_product"}),
    )
    q = forms.CharField(
        required=False,
        label="جستجو",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "جستجو در نام محصول...",
                "id": "id_q",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["year"].choices = get_year_choices()
