from django.db import transaction

from inventory.services import StockError, change_decant_stock, change_stock

from .models import Sale


def _stock_reference(sale):
    return f"فاکتور فروش شماره {sale.pk}"


@transaction.atomic
def create_sale(form):
    sale = form.save()
    if sale.item_type == Sale.ITEM_TYPE_DECANT:
        if sale.decant_id is None:
            raise StockError("برای ثبت فاکتور فروش دکانت، باید یک دکانت انتخاب شود.")
        change_decant_stock(
            sale.decant_id,
            -sale.quantity,
            reason="ثبت فاکتور فروش دکانت",
            reference=_stock_reference(sale),
        )
    else:
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
    old_item_type = sale.item_type
    old_product_id = sale.product_id
    old_decant_id = sale.decant_id
    old_quantity = sale.quantity
    old_is_active = sale.is_active

    sale.date = form.cleaned_data["date"]
    sale.item_type = form.cleaned_data.get("item_type", Sale.ITEM_TYPE_PRODUCT)
    sale.quantity = form.cleaned_data["quantity"]
    sale.unit_price = form.cleaned_data["unit_price"]

    if sale.item_type == Sale.ITEM_TYPE_DECANT:
        sale.product = None
        sale.decant = form.cleaned_data.get("decant")
        if sale.decant_id is None:
            raise StockError("برای ثبت فاکتور فروش دکانت، باید یک دکانت انتخاب شود.")
    else:
        sale.decant = None
        sale.product = form.cleaned_data.get("product")
        if sale.product_id is None:
            raise StockError("برای ثبت فاکتور فروش باید محصولی انتخاب شود.")
        if old_product_id != sale.product_id and sale.product:
            sale.purchase_unit_price = sale.product.purchase_price

    sale.save()
    reference = _stock_reference(sale)

    # Stock adjustments are only applied when invoice was and remains active
    if old_is_active and sale.is_active:
        # 1. Restore previous item stock
        if old_item_type == Sale.ITEM_TYPE_DECANT and old_decant_id is not None:
            if sale.item_type == Sale.ITEM_TYPE_DECANT and old_decant_id == sale.decant_id:
                change_decant_stock(
                    sale.decant_id,
                    old_quantity - sale.quantity,
                    reason="ویرایش فاکتور فروش دکانت",
                    reference=reference,
                )
                return sale
            else:
                change_decant_stock(
                    old_decant_id,
                    old_quantity,
                    reason="ویرایش فاکتور فروش دکانت",
                    reference=reference,
                )
        elif old_product_id is not None:
            if sale.item_type != Sale.ITEM_TYPE_DECANT and old_product_id == sale.product_id:
                change_stock(
                    sale.product_id,
                    old_quantity - sale.quantity,
                    reason="ویرایش فاکتور فروش",
                    reference=reference,
                )
                return sale
            else:
                change_stock(
                    old_product_id,
                    old_quantity,
                    reason="ویرایش فاکتور فروش",
                    reference=reference,
                )

        # 2. Deduct new item stock
        if sale.item_type == Sale.ITEM_TYPE_DECANT:
            change_decant_stock(
                sale.decant_id,
                -sale.quantity,
                reason="ویرایش فاکتور فروش دکانت",
                reference=reference,
            )
        else:
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
        # Deactivate invoice: return product or decant quantity back to stock
        if sale.item_type == Sale.ITEM_TYPE_DECANT and sale.decant_id is not None:
            change_decant_stock(
                sale.decant_id,
                sale.quantity,
                reason="غیرفعال کردن فاکتور فروش دکانت",
                reference=reference,
            )
        elif sale.product_id is not None:
            change_stock(
                sale.product_id,
                sale.quantity,
                reason="غیرفعال کردن فاکتور فروش",
                reference=reference,
            )
        sale.is_active = False
    else:
        # Reactivate invoice: deduct product or decant quantity from stock again
        if sale.item_type == Sale.ITEM_TYPE_DECANT and sale.decant_id is not None:
            change_decant_stock(
                sale.decant_id,
                -sale.quantity,
                reason="فعال‌سازی مجدد فاکتور فروش دکانت",
                reference=reference,
            )
        elif sale.product_id is not None:
            change_stock(
                sale.product_id,
                -sale.quantity,
                reason="فعال‌سازی مجدد فاکتور فروش",
                reference=reference,
            )
        sale.is_active = True

    sale.save(update_fields=["is_active"])
    return sale.is_active
