from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class Supplier(models.Model):
    name = models.CharField(max_length=200, verbose_name="نام شرکت")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")

    class Meta:
        ordering = ["name", "id"]
        verbose_name = "تامین‌کننده"
        verbose_name_plural = "تامین‌کنندگان"
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                name="unique_supplier_name_ci",
                violation_error_message="تامین‌کننده‌ای با این نام قبلاً ثبت شده است.",
            ),
        ]

    def __str__(self):
        return self.name


class PurchaseInvoice(models.Model):
    date = models.DateField(default=timezone.localdate, verbose_name="تاریخ فاکتور")
    # تامین‌کننده‌ای که فاکتور دارد نباید حذف شود.
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="invoices",
        verbose_name="تامین‌کننده",
    )
    # این دو فیلد دستی وارد نمی‌شوند؛ بعد از هر ذخیره از روی ردیف‌ها محاسبه می‌شوند.
    total_quantity = models.PositiveIntegerField(
        default=0, editable=False, verbose_name="تعداد کل"
    )
    total_amount = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        default=Decimal("0"),
        editable=False,
        verbose_name="جمع کل",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین ویرایش")

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "فاکتور خرید"
        verbose_name_plural = "فاکتورهای خرید"

    def __str__(self):
        return f"فاکتور خرید {self.pk}"

    def recalculate_totals(self):
        items = list(self.items.all())
        self.total_quantity = sum(item.quantity for item in items)
        self.total_amount = sum((item.line_total for item in items), Decimal("0"))
        self.save(update_fields=["total_quantity", "total_amount", "updated_at"])


class PurchaseItem(models.Model):
    invoice = models.ForeignKey(
        PurchaseInvoice,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="فاکتور",
    )
    # اگر محصول از انبار حذف شود، ردیف فاکتور می‌ماند و نام محصول در product_name.
    product = models.ForeignKey(
        "inventory.Product",
        on_delete=models.SET_NULL,
        null=True,
        related_name="purchase_items",
        verbose_name="محصول",
    )
    product_name = models.CharField(
        max_length=200, editable=False, verbose_name="نام محصول"
    )
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], verbose_name="تعداد"
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="قیمت خرید",
    )

    class Meta:
        ordering = ["id"]
        verbose_name = "ردیف فاکتور خرید"
        verbose_name_plural = "ردیف‌های فاکتور خرید"

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"

    @property
    def line_total(self):
        return self.quantity * self.unit_price

    def save(self, *args, **kwargs):
        if self.product_id:
            self.product_name = self.product.name
        super().save(*args, **kwargs)
