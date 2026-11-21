from decimal import ROUND_HALF_UP, Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from jalali_date import date2jalali


class Sale(models.Model):
    ITEM_TYPE_PRODUCT = "product"
    ITEM_TYPE_DECANT = "decant"
    ITEM_TYPE_CHOICES = [
        (ITEM_TYPE_PRODUCT, "کالا (شیشه کامل)"),
        (ITEM_TYPE_DECANT, "دکانت عطر"),
    ]

    date = models.DateField(default=timezone.localdate, verbose_name="تاریخ فاکتور")
    item_type = models.CharField(
        max_length=20,
        choices=ITEM_TYPE_CHOICES,
        default=ITEM_TYPE_PRODUCT,
        verbose_name="نوع قلم",
    )
    product = models.ForeignKey(
        "inventory.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales",
        verbose_name="محصول",
    )
    decant = models.ForeignKey(
        "inventory.Decant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sales",
        verbose_name="دکانت عطر",
    )
    product_name = models.CharField(max_length=200, verbose_name="نام محصول یا دکانت")
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], verbose_name="تعداد"
    )
    unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="مبلغ هر واحد",
    )
    purchase_unit_price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="قیمت واحد خرید در زمان فروش",
    )
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")

    class Meta:
        ordering = ["-date", "-id"]
        verbose_name = "فاکتور فروش"
        verbose_name_plural = "فاکتور فروش"

    def __str__(self):
        return f"فاکتور فروش شماره {self.pk} - {self.product_name}"

    @property
    def total_amount(self):
        return self.quantity * self.unit_price

    @property
    def total_cost(self):
        return self.quantity * (self.purchase_unit_price or Decimal("0"))

    @property
    def profit(self):
        return self.total_amount - self.total_cost

    @property
    def profit_margin_percent(self):
        if self.total_amount > 0:
            return ((self.profit / self.total_amount) * 100).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP
            )
        return Decimal("0")

    @property
    def jalali_date(self):
        return date2jalali(self.date).strftime("%Y/%m/%d")

    def save(self, *args, **kwargs):
        if self.item_type == self.ITEM_TYPE_DECANT and self.decant_id:
            self.product = None
            self.product_name = f"دکانت {self.decant.perfume_name} ({self.decant.volume})"
            if self.purchase_unit_price is None:
                self.purchase_unit_price = Decimal("0")
        elif self.product_id:
            self.decant = None
            self.product_name = self.product.name
            if (self.purchase_unit_price is None or self.purchase_unit_price == 0) and self.product.purchase_price:
                self.purchase_unit_price = self.product.purchase_price
        super().save(*args, **kwargs)
