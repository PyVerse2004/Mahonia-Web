from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from jalali_date import date2jalali


class Person(models.Model):
    class AccountStatus(models.TextChoices):
        SETTLED = "settled", "تسویه شده"
        DEBTOR = "debtor", "بدهکار"
        CREDITOR = "creditor", "بستانکار"

    date = models.DateField(default=timezone.localdate, verbose_name="تاریخ")
    product_name = models.CharField(max_length=200, verbose_name="نام محصول")
    debtor_name = models.CharField(max_length=200, verbose_name="نام بدهکار")
    phone_number = models.CharField(max_length=20, blank=True, verbose_name="شماره تماس")
    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name="تعداد محصول",
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="مبلغ هر واحد",
    )
    debt_amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name="مبلغ کل بدهکاری",
    )
    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=0,
        verbose_name="مبلغ پرداخت‌شده",
    )
    status = models.CharField(
        max_length=20,
        choices=AccountStatus.choices,
        default=AccountStatus.DEBTOR,
        verbose_name="وضعیت حساب",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ایجاد")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین ویرایش")

    class Meta:
        verbose_name = "شخص"
        verbose_name_plural = "اشخاص"
        ordering = ("-date", "-id")

    def __str__(self):
        return f"{self.debtor_name} - {self.product_name} ({self.get_status_display()})"

    @property
    def total_amount(self):
        if self.unit_price and self.quantity:
            return self.quantity * self.unit_price
        return self.debt_amount

    @property
    def remaining_debt(self):
        if self.status == self.AccountStatus.DEBTOR:
            return max(Decimal("0"), self.debt_amount - (self.paid_amount or Decimal("0")))
        return Decimal("0")

    @property
    def jalali_date(self):
        if not self.date:
            return ""
        return date2jalali(self.date).strftime("%Y/%m/%d")

    def save(self, *args, **kwargs):
        if self.unit_price > 0 and self.quantity > 0:
            if not self.debt_amount or self.debt_amount == 0:
                self.debt_amount = self.quantity * self.unit_price
        elif self.debt_amount > 0 and self.quantity > 0 and self.unit_price == 0:
            self.unit_price = self.debt_amount // self.quantity
        super().save(*args, **kwargs)
