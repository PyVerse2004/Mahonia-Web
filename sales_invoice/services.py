from django.db import transaction

from inventory.services import StockError, change_stock

from .models import Sale


def _stock_reference(sale):
    return f"فاکتور فروش شماره {sale.pk}"


@transaction.atomic
def create_sale(form):
    sale = form.save()
    if sale.product_id is None:
        raise StockError("برای ثبت فاکتور فروش باید محصولی انتخاب شود.")

    change_stock(
        sale.product_id,
        -sale.quantity,
        reason="ثبت فاکتور فروش",
        reference=_stock_reference(sale),
    )
    return sale


@transaction.atomic
def update_sale(form):
    sale = Sale.objects.select_for_update().get(pk=form.instance.pk)
    old_product_id = sale.product_id
    old_quantity = sale.quantity
    old_is_active = sale.is_active

    sale.date = form.cleaned_data["date"]
    sale.product = form.cleaned_data["product"]
    sale.quantity = form.cleaned_data["quantity"]
    sale.unit_price = form.cleaned_data["unit_price"]

    if sale.product_id is None:
        raise StockError("برای ثبت فاکتور فروش باید محصولی انتخاب شود.")

    if old_product_id != sale.product_id and sale.product:
        sale.purchase_unit_price = sale.product.purchase_price

    sale.save()
    reference = _stock_reference(sale)

    # فقط اگر فاکتور فعال است، تغییرات روی موجودی انبار اعمال می‌شود
    if old_is_active and sale.is_active:
        if old_product_id == sale.product_id:
            change_stock(
                sale.product_id,
                old_quantity - sale.quantity,
                reason="ویرایش فاکتور فروش",
                reference=reference,
            )
        else:
            if old_product_id is not None:
                change_stock(
                    old_product_id,
                    old_quantity,
                    reason="ویرایش فاکتور فروش",
                    reference=reference,
                )
            change_stock(
                sale.product_id,
                -sale.quantity,
                reason="ویرایش فاکتور فروش",
                reference=reference,
            )
    return sale


@transaction.atomic
def toggle_sale_active(sale):
    sale = Sale.objects.select_for_update().get(pk=sale.pk)
    reference = _stock_reference(sale)

    if sale.is_active:
        # غیرفعال کردن فاکتور: کالا به انبار بازمی‌گردد
        if sale.product_id is not None:
            change_stock(
                sale.product_id,
                sale.quantity,
                reason="غیرفعال کردن فاکتور فروش",
                reference=reference,
            )
        sale.is_active = False
    else:
        # فعال‌سازی مجدد فاکتور: کالا دوباره از انبار کسر می‌شود
        if sale.product_id is not None:
            change_stock(
                sale.product_id,
                -sale.quantity,
                reason="فعال‌سازی مجدد فاکتور فروش",
                reference=reference,
            )
        sale.is_active = True

    sale.save(update_fields=["is_active"])
    return sale.is_active
