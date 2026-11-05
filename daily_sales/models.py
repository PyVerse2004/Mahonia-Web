from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from jalali_date import date2jalali


class Sale(models.Model):
    date = models.DateField(default=timezone.localdate, verbose_name="تاریخ فاکتور")
    product = models.ForeignKey(
        "inventory.Product",
        on_delete=models.SET_NULL,
        null=True,
        related_name="sales",
        verbose_name="محصول",
    )
    product_name = models.CharField(max_length=200, verbose_name="نام محصول")
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], verbose_name="تعداد"
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="مبلغ هر واحد",
    )
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "فاکتور فروش"
        verbose_name_plural = "فاکتورهای فروش"

    def __str__(self):
        return f"فاکتور فروش شماره {self.pk} - {self.product_name}"

    @property
    def total_amount(self):
        return self.quantity * self.unit_price

    @property
    def jalali_date(self):
        return date2jalali(self.date).strftime("%Y/%m/%d")

    def save(self, *args, **kwargs):
        if self.product_id:
            self.product_name = self.product.name
        super().save(*args, **kwargs)
