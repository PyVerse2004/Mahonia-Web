from django.db import transaction
from django.db.models import Sum

from inventory.services import change_stock, recalculate_purchase_price


def _quantities(invoice):
    """تعداد خریداری‌شده‌ی هر محصول در فاکتور، به شکل {product_id: quantity}."""
    if not invoice.pk:
        return {}
    rows = (
        invoice.items.exclude(product=None)
        .values("product_id")
        .annotate(total=Sum("quantity"))
    )
    return {row["product_id"]: row["total"] for row in rows}


def _sync_inventory(before, after):
    """اختلاف تعداد قبل و بعد را روی موجودی اعمال و قیمت خرید را دوباره محاسبه می‌کند."""
    for product_id in before.keys() | after.keys():
        change_stock(product_id, after.get(product_id, 0) - before.get(product_id, 0))
        recalculate_purchase_price(product_id)


@transaction.atomic
def save_invoice(form, formset):
    """فاکتور و ردیف‌هایش را ذخیره می‌کند و انبار را به‌روز می‌کند.

    همه‌ی مراحل در یک تراکنش‌اند؛ اگر StockError پیش بیاید هیچ تغییری ذخیره نمی‌شود.
    """
    before = _quantities(form.instance)

    invoice = form.save()
    formset.instance = invoice
    formset.save()

    invoice.recalculate_totals()
    _sync_inventory(before, _quantities(invoice))
    return invoice


@transaction.atomic
def delete_invoice(invoice):
    before = _quantities(invoice)
    invoice.delete()  # ردیف‌ها با CASCADE حذف می‌شوند
    _sync_inventory(before, {})
