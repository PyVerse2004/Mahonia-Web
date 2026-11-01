from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Avg, F
from django.utils import timezone

from .models import Product


class StockError(Exception):
    """موجودی انبار برای انجام عملیات کافی نیست."""


def change_stock(product_id, delta):
    """موجودی محصول را به اندازه‌ی delta زیاد (یا کم) می‌کند.

    کاهش فقط وقتی انجام می‌شود که موجودی کافی باشد. شرط و تغییر در یک دستور
    UPDATE انجام می‌شوند، پس بین بررسی و ثبت، موجودی عوض نمی‌شود.
    """
    if not delta:
        return

    updated = Product.objects.filter(
        pk=product_id, stock_quantity__gte=-delta
    ).update(stock_quantity=F("stock_quantity") + delta, updated_at=timezone.now())

    if not updated:
        name = (
            Product.objects.filter(pk=product_id)
            .values_list("name", flat=True)
            .first()
        )
        raise StockError(f"موجودی محصول «{name}» برای این تغییر کافی نیست.")


def recalculate_purchase_price(product_id):
    """قیمت خرید محصول را برابر میانگین ساده‌ی قیمت خرید ردیف‌های فاکتور می‌گذارد.

    فقط قیمت‌ها در میانگین حساب می‌شوند؛ تعداد خریداری‌شده روی آن اثری ندارد.
    اگر محصول هیچ ردیف فاکتوری نداشته باشد، قیمت فعلی بدون تغییر می‌ماند.
    """
    product = Product.objects.get(pk=product_id)
    average = product.purchase_items.aggregate(average=Avg("unit_price"))["average"]
    if average is None:
        return

    average = Decimal(str(average)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
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
