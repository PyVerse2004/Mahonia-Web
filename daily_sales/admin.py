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
        is_active = cleaned_data.get("is_active", True)

        if product and quantity and is_active:
            current_stock = product.stock_quantity
            if self.instance.pk:
                old_sale = Sale.objects.filter(pk=self.instance.pk).first()
                if old_sale and old_sale.is_active and old_sale.product_id == product.pk:
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
        "is_active",
        "created_at",
    )
    list_filter = ("is_active", "date")
    search_fields = ("product_name",)
    readonly_fields = ("created_at",)

    @admin.display(description="مبلغ کل")
    def total_amount_display(self, obj):
        return f"{obj.total_amount:,.0f}"

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        if not change:
            super().save_model(request, obj, form, change)
            if obj.is_active and obj.product_id is not None:
                change_stock(
                    obj.product_id,
                    -obj.quantity,
                    reason="ثبت فاکتور فروش از پنل ادمین",
                    reference=f"فاکتور فروش شماره {obj.pk}",
                )
        else:
            old_sale = Sale.objects.select_for_update().get(pk=obj.pk)
            old_product_id = old_sale.product_id
            old_quantity = old_sale.quantity
            old_active = old_sale.is_active

            super().save_model(request, obj, form, change)
            reference = f"فاکتور فروش شماره {obj.pk}"

            # Stock adjustments based on active state transitions
            if old_active and not obj.is_active:
                if old_product_id is not None:
                    change_stock(
                        old_product_id,
                        old_quantity,
                        reason="غیرفعال‌سازی فاکتور فروش از پنل ادمین",
                        reference=reference,
                    )
            elif not old_active and obj.is_active:
                if obj.product_id is not None:
                    change_stock(
                        obj.product_id,
                        -obj.quantity,
                        reason="فعال‌سازی مجدد فاکتور فروش از پنل ادمین",
                        reference=reference,
                    )
            elif old_active and obj.is_active:
                if old_product_id == obj.product_id:
                    diff = old_quantity - obj.quantity
                    if diff != 0 and obj.product_id is not None:
                        change_stock(
                            obj.product_id,
                            diff,
                            reason="ویرایش فاکتور فروش از پنل ادمین",
                            reference=reference,
                        )
                else:
                    if old_product_id is not None:
                        change_stock(
                            old_product_id,
                            old_quantity,
                            reason="ویرایش فاکتور فروش از پنل ادمین",
                            reference=reference,
                        )
                    if obj.product_id is not None:
                        change_stock(
                            obj.product_id,
                            -obj.quantity,
                            reason="ویرایش فاکتور فروش از پنل ادمین",
                            reference=reference,
                        )

    @transaction.atomic
    def delete_model(self, request, obj):
        if obj.is_active and obj.product_id is not None:
            change_stock(
                obj.product_id,
                obj.quantity,
                reason="حذف فاکتور فروش از پنل ادمین",
                reference=f"فاکتور فروش شماره {obj.pk}",
            )
        super().delete_model(request, obj)

    @transaction.atomic
    def delete_queryset(self, request, queryset):
        for obj in queryset:
            if obj.is_active and obj.product_id is not None:
                change_stock(
                    obj.product_id,
                    obj.quantity,
                    reason="حذف فاکتور فروش از پنل ادمین",
                    reference=f"فاکتور فروش شماره {obj.pk}",
                )
        super().delete_queryset(request, queryset)
