from django.contrib import admin
from django.db import transaction

from .models import Product, StockMovement
from .services import change_stock


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "stock_quantity", "purchase_price", "sale_price")
    search_fields = ("name",)

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        if change:
            if "stock_quantity" in form.changed_data:
                old_product = Product.objects.select_for_update().get(pk=obj.pk)
                diff = obj.stock_quantity - old_product.stock_quantity
                super().save_model(request, obj, form, change)
                if diff != 0:
                    StockMovement.objects.create(
                        product=obj,
                        product_name=obj.name,
                        quantity_change=diff,
                        stock_before=old_product.stock_quantity,
                        stock_after=obj.stock_quantity,
                        reason="اصلاح موجودی از پنل ادمین",
                        reference="پنل ادمین",
                    )
            else:
                super().save_model(request, obj, form, change)
        else:
            initial_stock = obj.stock_quantity
            obj.stock_quantity = 0
            super().save_model(request, obj, form, change)
            if initial_stock > 0:
                change_stock(
                    obj.pk,
                    initial_stock,
                    reason="ثبت موجودی اولیه از پنل ادمین",
                    reference="پنل ادمین",
                )


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "product_name",
        "quantity_change",
        "stock_before",
        "stock_after",
        "reason",
        "reference",
    )
    list_filter = ("reason", "created_at")
    search_fields = ("product_name", "reference")
    readonly_fields = ("created_at",)
