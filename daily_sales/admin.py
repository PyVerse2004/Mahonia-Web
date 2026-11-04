from django.contrib import admin

from .models import Sale


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    # فروش‌ها در ادمین فقط‌خواندنی هستند تا ثبت، ویرایش و حذف بدون هماهنگی
    # با انبار و گردش کالا (StockMovement) انجام نشود.
    # عملیات فروش فقط از طریق بخش فروش برنامه انجام می‌شود.
    list_display = (
        "date",
        "product_name",
        "quantity",
        "unit_price",
        "status",
        "debtor_name",
        "created_at",
    )
    list_filter = ("status", "date")
    search_fields = ("product_name", "debtor_name")
    readonly_fields = (
        "date",
        "product",
        "product_name",
        "quantity",
        "unit_price",
        "status",
        "debtor_name",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
