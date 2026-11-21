from django.db import transaction
from django.db.models import Sum

from inventory.services import (
    change_stock,
    get_or_create_product,
    recalculate_purchase_price,
)


def _quantities(invoice):
    """Dictionary of product quantities on invoice: {product_id: total_quantity}."""
    if not invoice.pk:
        return {}
    rows = (
        invoice.items.exclude(product=None)
        .values("product_id")
        .annotate(total=Sum("quantity"))
    )
    return {row["product_id"]: row["total"] for row in rows}


def _sync_inventory(before, after, reason, reference):
    """Apply quantity deltas to inventory and recalculate weighted average purchase prices."""
    for product_id in before.keys() | after.keys():
        change_stock(
            product_id,
            after.get(product_id, 0) - before.get(product_id, 0),
            reason=reason,
            reference=reference,
        )
        recalculate_purchase_price(product_id)


def _assign_new_products(formset):
    """Resolve or create product instances for rows specifying new product names."""
    deleted = formset.deleted_forms
    for item_form in formset.forms:
        if item_form.new_product_name and item_form not in deleted:
            item_form.instance.product = get_or_create_product(item_form.new_product_name)


@transaction.atomic
def save_invoice(form, formset):
    """
    Persist invoice and items atomically while updating warehouse stock and average costs.

    All steps execute in a single transaction; if StockError occurs, all changes roll back.
    """
    is_new = form.instance.pk is None
    before = _quantities(form.instance)

    invoice = form.save()
    formset.instance = invoice
    _assign_new_products(formset)
    formset.save()

    invoice.recalculate_totals()
    _sync_inventory(
        before,
        _quantities(invoice),
        reason="ثبت فاکتور خرید" if is_new else "ویرایش فاکتور خرید",
        reference=f"فاکتور خرید شماره {invoice.pk}",
    )
    return invoice


@transaction.atomic
def delete_invoice(invoice):
    reference = f"فاکتور خرید شماره {invoice.pk}"
    before = _quantities(invoice)
    invoice.delete()  # Items cascade with deletion
    _sync_inventory(before, {}, reason="حذف فاکتور خرید", reference=reference)
