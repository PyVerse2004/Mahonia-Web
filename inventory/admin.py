from django.contrib import admin

from .models import Product, StockMovement


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "stock_quantity", "purchase_price", "sale_price")
    search_fields = ("name",)
    readonly_fields = ("stock_quantity",)


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
    readonly_fields = (
        "product",
        "product_name",
        "quantity_change",
        "stock_before",
        "stock_after",
        "reason",
        "reference",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
