from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import F, Sum, DecimalField
from django.utils import timezone

from .models import Product, StockMovement


class StockError(Exception):
    """موجودی انبار برای انجام عملیات کافی نیست."""


@transaction.atomic
def change_stock(product_id, delta, reason="اصلاح موجودی", reference=""):
    """موجودی محصول را به اندازه‌ی delta زیاد (یا کم) می‌کند.

    کاهش فقط وقتی انجام می‌شود که موجودی کافی باشد. تغییر موجودی و ثبت کاردکس
    در یک تراکنش انجام می‌شوند تا گزارش با موجودی واقعی هماهنگ بماند.
    """
    if not delta:
        return

    product = Product.objects.select_for_update().filter(pk=product_id).first()
    if product is None:
        raise StockError("محصول موردنظر برای تغییر موجودی پیدا نشد.")

    before = product.stock_quantity
    after = before + delta
    if after < 0:
        raise StockError(f"موجودی محصول «{product.name}» برای این تغییر کافی نیست.")

    updated = Product.objects.filter(
        pk=product_id, stock_quantity__gte=-delta
    ).update(
        stock_quantity=F("stock_quantity") + delta, updated_at=timezone.now()
    )
    if not updated:
        raise StockError(f"موجودی محصول «{product.name}» برای این تغییر کافی نیست.")

    StockMovement.objects.create(
        product=product,
        product_name=product.name,
        quantity_change=delta,
        stock_before=before,
        stock_after=after,
        reason=reason,
        reference=reference,
    )


def recalculate_purchase_price(product_id):
    """قیمت خرید محصول را برابر میانگین موزون همه‌ی ردیف‌های فاکتور خرید می‌گذارد.

        میانگین = مجموع (تعداد × قیمت) / مجموع تعداد

    اگر محصول هیچ ردیف فاکتوری نداشته باشد، قیمت فعلی بدون تغییر می‌ماند.
    """
    product = Product.objects.get(pk=product_id)

    totals = product.purchase_items.aggregate(
        total_quantity=Sum("quantity"),
        total_cost=Sum(
            F("quantity") * F("unit_price"),
            output_field=DecimalField(max_digits=20, decimal_places=0),
        ),
    )
    if not totals["total_quantity"]:
        return

    average = (totals["total_cost"] / totals["total_quantity"]).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    Product.objects.filter(pk=product_id).update(
        purchase_price=average, updated_at=timezone.now()
    )



def get_or_create_product(name):
    """محصولی با این نام (بدون حساسیت به بزرگی و کوچکی حروف) را برمی‌گرداند؛ اگر نبود می‌سازد.

    محصول تازه با موجودی و قیمت صفر ساخته می‌شود. موجودی و قیمت خرید را فاکتور
    خرید تعیین می‌کند و قیمت فروش را بعداً از صفحه‌ی ویرایش محصول می‌گذاری.
    """
    product = Product.objects.filter(name__iexact=name).first()
    if product:
        return product
    return Product.objects.create(name=name)
