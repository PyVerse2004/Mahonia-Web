from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.db.models import DecimalField, F, Sum
from django.utils import timezone

from .models import Decant, Product, StockMovement


class StockError(Exception):
    """Raised when warehouse stock is insufficient for the requested operation."""


@transaction.atomic
def change_stock(product_id, delta, reason="اصلاح موجودی", reference=""):
    """
    Increase or decrease product stock quantity by delta atomically while recording a cardex entry.

    Reductions are only permitted if sufficient stock exists. Both balance update and
    movement logging execute within a single transaction to ensure consistency.
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
    """
    Recalculate weighted average purchase price for a product across all purchase invoice rows.

    Weighted Average = Total Cost / Total Quantity.
    If the product has no purchase invoice rows, current purchase price remains unchanged.
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
    """
    Retrieve existing product case-insensitively or create a new one with zero initial stock.

    Initial stock and purchase cost are determined by incoming purchase invoices, while
    sale price can be configured from product management views.
    """
    product = Product.objects.filter(name__iexact=name).first()
    if product:
        return product
    return Product.objects.create(name=name)


@transaction.atomic
def change_decant_stock(decant_id, delta, reason="اصلاح موجودی دکانت", reference=""):
    """
    Increase or decrease decant stock quantity by delta atomically while recording a cardex entry.

    Reductions are only permitted if sufficient stock is present in inventory.
    """
    if not delta:
        return

    decant = Decant.objects.select_for_update().filter(pk=decant_id).first()
    if decant is None:
        raise StockError("دکانت موردنظر برای تغییر موجودی پیدا نشد.")

    before = decant.stock_quantity
    after = before + delta
    if after < 0:
        raise StockError(f"موجودی دکانت «{decant.perfume_name} ({decant.volume})» برای این تغییر کافی نیست.")

    updated = Decant.objects.filter(
        pk=decant_id, stock_quantity__gte=-delta
    ).update(
        stock_quantity=F("stock_quantity") + delta, updated_at=timezone.now()
    )
    if not updated:
        raise StockError(f"موجودی دکانت «{decant.perfume_name} ({decant.volume})» برای این تغییر کافی نیست.")

    StockMovement.objects.create(
        decant=decant,
        product_name=f"دکانت {decant.perfume_name} ({decant.volume})",
        quantity_change=delta,
        stock_before=before,
        stock_after=after,
        reason=reason,
        reference=reference,
    )
