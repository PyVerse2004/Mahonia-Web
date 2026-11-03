from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from jalali_date import date2jalali


class Sale(models.Model):
    class AccountStatus(models.TextChoices):
        DEBT = "debt", "بدهکار"
        SETTLED = "settled", "تسویه‌شده"

    date = models.DateField(default=timezone.localdate, verbose_name="تاریخ فروش")
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
    status = models.CharField(
        max_length=10,
        choices=AccountStatus.choices,
        default=AccountStatus.SETTLED,
        verbose_name="وضعیت حساب",
    )
    debtor_name = models.CharField(
        max_length=200, blank=True, verbose_name="نام بدهکار"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "فروش"
        verbose_name_plural = "فروش‌ها"

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"

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
