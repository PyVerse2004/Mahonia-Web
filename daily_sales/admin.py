from django.contrib import admin

from .models import Sale


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "product_name",
        "quantity",
        "unit_price",
        "status",
        "debtor_name",
    )
    list_filter = ("status", "date")
    search_fields = ("product_name", "debtor_name")
