from django import forms
from django.forms import inlineformset_factory

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
    # نام محصول: یا یکی از محصولات موجود یا نام یک محصول جدید.
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
        # اگر نام وارد‌شده محصول جدیدی باشد، اینجا نگه داشته می‌شود تا هنگام ذخیره‌ی
        # فاکتور ساخته شود. محصول در مرحله‌ی اعتبارسنجی ساخته نمی‌شود.
        self.new_product_name = None

        item = self.instance
        if item.pk:
            self.initial.setdefault(
                "product_text", item.product.name if item.product_id else item.product_name
            )

    def clean_product_text(self):
        # فاصله‌های اضافه حذف می‌شوند تا «Legend » و «Legend» یکی حساب شوند.
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
            # ردیف قدیمی که محصولش بعداً حذف شده؛ دست‌نخورده می‌ماند.
            pass
        elif self.can_create_products:
            self.new_product_name = name
        else:
            self.add_error(
                "product_text",
                f"محصول «{name}» وجود ندارد و اجازه‌ی ثبت محصول جدید را ندارید.",
            )
        return cleaned_data


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
