from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "stock_quantity", "purchase_price", "sale_price")
    search_fields = ("name",)
