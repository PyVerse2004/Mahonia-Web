from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.functions import Lower


class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name="نام محصول")
    image = models.ImageField(
        upload_to="products/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="تصویر محصول",
    )
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


class Decant(models.Model):
    VOLUME_5ML = "5ml"
    VOLUME_10ML = "10ml"
    VOLUME_CHOICES = [
        (VOLUME_5ML, "۵ میل (5ml)"),
        (VOLUME_10ML, "۱۰ میل (10ml)"),
    ]

    perfume_name = models.CharField(max_length=200, verbose_name="نام عطر")
    volume = models.CharField(
        max_length=20,
        choices=VOLUME_CHOICES,
        default=VOLUME_10ML,
        verbose_name="میل عطر",
    )
    stock_quantity = models.PositiveIntegerField(default=0, verbose_name="تعداد موجودی")
    sale_price = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        verbose_name="قیمت فروش (تومان)",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ ثبت")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="آخرین ویرایش")

    class Meta:
        ordering = ["perfume_name", "volume", "id"]
        verbose_name = "دکانت عطر"
        verbose_name_plural = "دکانت‌های عطر"
        constraints = [
            models.UniqueConstraint(
                Lower("perfume_name"),
                "volume",
                name="unique_decant_name_volume_ci",
                violation_error_message="دکانت این عطر با همین حجم قبلاً ثبت شده است.",
            ),
        ]

    def __str__(self):
        return f"{self.perfume_name} - {self.get_volume_display()}"


class StockMovement(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_movements",
        verbose_name="محصول",
    )
    decant = models.ForeignKey(
        Decant,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_movements",
        verbose_name="دکانت",
    )
    product_name = models.CharField(max_length=200, verbose_name="نام محصول یا دکانت")
    quantity_change = models.IntegerField(verbose_name="تغییر موجودی")
    stock_before = models.PositiveIntegerField(verbose_name="موجودی قبل")
    stock_after = models.PositiveIntegerField(verbose_name="موجودی بعد")
    reason = models.CharField(max_length=160, verbose_name="شرح")
    reference = models.CharField(max_length=100, blank=True, verbose_name="مرجع")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاریخ و ساعت")

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "گردش انبار"
        verbose_name_plural = "گردش‌های انبار"

    def __str__(self):
        return f"{self.product_name} ({self.quantity_change:+})"
