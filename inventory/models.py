from django.db import models
from decimal import Decimal
from django.core.validators import MinValueValidator

# Create your models here.
class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name="Product name")
    stock_quantity = models.PositiveIntegerField(default=0 , verbose_name="Inventory")
    purchase_price = models.DecimalField(max_digits=12, decimal_places=0, validators=[MinValueValidator(Decimal("0"))], verbose_name="Sale Price")
    is_active = models.BooleanField(default=True, verbose_name="Activity")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Add Date")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Edit")

    class Meta:
        ordering = ["name"]
        verbose_name = "Product"
        verbose_name_plural = "Products"

    def __str__(self):
        return self.name
