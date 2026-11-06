from django.contrib import admin

from .models import Person


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "debtor_name",
        "phone_number",
        "product_name",
        "quantity",
        "unit_price_display",
        "debt_amount_display",
        "paid_amount_display",
        "remaining_debt_display",
        "status",
        "created_at",
    )
    list_filter = ("status", "date")
    search_fields = ("debtor_name", "product_name", "phone_number")
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="مبلغ هر واحد")
    def unit_price_display(self, obj):
        return f"{obj.unit_price:,.0f}"

    @admin.display(description="مبلغ کل بدهکاری")
    def debt_amount_display(self, obj):
        return f"{obj.debt_amount:,.0f}"

    @admin.display(description="پرداخت‌شده")
    def paid_amount_display(self, obj):
        return f"{obj.paid_amount:,.0f}"

    @admin.display(description="مانده بدهی")
    def remaining_debt_display(self, obj):
        return f"{obj.remaining_debt:,.0f}"
