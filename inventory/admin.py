from django.contrib import admin
from . models import Product

# Register your models here.
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "stock_quantity",
        "purchase_price",
        "sale_price",
        "is_active",
    )

    search_fields = ("name",)
    list_filter = ("is_active",)
