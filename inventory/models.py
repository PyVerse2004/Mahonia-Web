from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower


class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name="نام محصول")
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name="موجودی انبار")
    purchase_price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="قیمت خرید",
    )
    sale_price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="قیمت فروش",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین ویرایش")

    class Meta:
        ordering = ["name", "id"]
        verbose_name = "محصول"
        verbose_name_plural = "محصولات"
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                name="unique_product_name_ci",
                violation_error_message="محصولی با این نام قبلاً ثبت شده است.",
            ),
        ]

    def __str__(self):
        return self.name
