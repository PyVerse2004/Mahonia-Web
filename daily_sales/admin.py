from decimal import Decimal

from django import forms
from django.contrib import admin
from django.db import transaction

from inventory.services import change_stock

from .models import Sale


class SaleAdminForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        product = cleaned_data.get("product")
        quantity = cleaned_data.get("quantity") or 0
        unit_price = cleaned_data.get("unit_price") or Decimal("0")
        total_amount = quantity * unit_price
        paid_amount = cleaned_data.get("paid_amount")
        if paid_amount is None:
            paid_amount = Decimal("0")
        status = cleaned_data.get("status")
        debtor_name = (cleaned_data.get("debtor_name") or "").strip()

        if status == Sale.AccountStatus.DEBT and not debtor_name:
            self.add_error("debtor_name", "برای حساب بدهکار، نام بدهکار را وارد کنید.")

        if status == Sale.AccountStatus.SETTLED:
            paid_amount = total_amount
        elif total_amount > 0 and paid_amount >= total_amount:
            status = Sale.AccountStatus.SETTLED
            paid_amount = total_amount
            cleaned_data["status"] = status

        if total_amount > 0 and paid_amount > total_amount:
            self.add_error(
                "paid_amount",
                f"مبلغ پرداخت‌شده نمی‌تواند بیشتر از مبلغ کل ({total_amount:,.0f} تومان) باشد.",
            )

        cleaned_data["debtor_name"] = debtor_name
        cleaned_data["paid_amount"] = paid_amount

        if product and quantity:
            current_stock = product.stock_quantity
            if self.instance.pk:
                old_sale = Sale.objects.filter(pk=self.instance.pk).first()
                if old_sale and old_sale.product_id == product.pk:
                    current_stock += old_sale.quantity
            if quantity > current_stock:
                self.add_error(
                    "quantity",
                    f"موجودی فعلی محصول «{product.name}» برابر {current_stock} است و برای این مقدار کافی نیست.",
                )
        return cleaned_data


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    form = SaleAdminForm
    list_display = (
        "date",
        "product_name",
        "quantity",
        "unit_price",
        "total_amount_display",
        "paid_amount",
        "remaining_debt_display",
        "status",
        "debtor_name",
        "created_at",
    )
    list_filter = ("status", "date")
    search_fields = ("product_name", "debtor_name")
    readonly_fields = ("created_at",)

    @admin.display(description="مبلغ کل")
    def total_amount_display(self, obj):
        return f"{obj.total_amount:,.0f}"

    @admin.display(description="مانده بدهی")
    def remaining_debt_display(self, obj):
        return f"{obj.remaining_debt:,.0f}"

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        if not change:
            super().save_model(request, obj, form, change)
            if obj.product_id is not None:
                change_stock(
                    obj.product_id,
                    -obj.quantity,
                    reason="ثبت فروش از پنل ادمین",
                    reference=f"فروش شماره {obj.pk}",
                )
        else:
            old_sale = Sale.objects.select_for_update().get(pk=obj.pk)
            old_product_id = old_sale.product_id
            old_quantity = old_sale.quantity

            super().save_model(request, obj, form, change)
            reference = f"فروش شماره {obj.pk}"

            if old_product_id == obj.product_id:
                diff = old_quantity - obj.quantity
                if diff != 0 and obj.product_id is not None:
                    change_stock(
                        obj.product_id,
                        diff,
                        reason="ویرایش فروش از پنل ادمین",
                        reference=reference,
                    )
            else:
                if old_product_id is not None:
                    change_stock(
                        old_product_id,
                        old_quantity,
                        reason="ویرایش فروش از پنل ادمین",
                        reference=reference,
                    )
                if obj.product_id is not None:
                    change_stock(
                        obj.product_id,
                        -obj.quantity,
                        reason="ویرایش فروش از پنل ادمین",
                        reference=reference,
                    )

    @transaction.atomic
    def delete_model(self, request, obj):
        if obj.product_id is not None:
            change_stock(
                obj.product_id,
                obj.quantity,
                reason="حذف فروش از پنل ادمین",
                reference=f"فروش شماره {obj.pk}",
            )
        super().delete_model(request, obj)

    @transaction.atomic
    def delete_queryset(self, request, queryset):
        for obj in queryset:
            if obj.product_id is not None:
                change_stock(
                    obj.product_id,
                    obj.quantity,
                    reason="حذف فروش از پنل ادمین",
                    reference=f"فروش شماره {obj.pk}",
                )
        super().delete_queryset(request, queryset)
