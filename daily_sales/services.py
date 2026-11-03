from django.db import transaction

from inventory.services import StockError, change_stock

from .models import Sale


def _stock_reference(sale):
    return f"فروش شماره {sale.pk}"


@transaction.atomic
def create_sale(form):
    sale = form.save()
    if sale.product_id is None:
        raise StockError("برای ثبت فروش باید محصولی انتخاب شود.")

    change_stock(
        sale.product_id,
        -sale.quantity,
        reason="ثبت فروش",
        reference=_stock_reference(sale),
    )
    return sale


@transaction.atomic
def update_sale(form):
    sale = Sale.objects.select_for_update().get(pk=form.instance.pk)
    old_product_id = sale.product_id
    old_quantity = sale.quantity
    sale.date = form.cleaned_data["date"]
    sale.product = form.cleaned_data["product"]
    sale.quantity = form.cleaned_data["quantity"]
    sale.unit_price = form.cleaned_data["unit_price"]
    sale.status = form.cleaned_data["status"]
    sale.debtor_name = form.cleaned_data["debtor_name"]
    updated_sale = sale
    if updated_sale.product_id is None:
        raise StockError("برای ثبت فروش باید محصولی انتخاب شود.")

    updated_sale.save()
    reference = _stock_reference(updated_sale)
    if old_product_id == updated_sale.product_id:
        change_stock(
            updated_sale.product_id,
            old_quantity - updated_sale.quantity,
            reason="ویرایش فروش",
            reference=reference,
        )
    else:
        if old_product_id is not None:
            change_stock(
                old_product_id,
                old_quantity,
                reason="ویرایش فروش",
                reference=reference,
            )
        change_stock(
            updated_sale.product_id,
            -updated_sale.quantity,
            reason="ویرایش فروش",
            reference=reference,
        )
    return updated_sale


@transaction.atomic
def delete_sale(sale):
    sale = Sale.objects.select_for_update().get(pk=sale.pk)
    if sale.product_id is not None:
        change_stock(
            sale.product_id,
            sale.quantity,
            reason="حذف فروش",
            reference=_stock_reference(sale),
        )
    sale.delete()


@transaction.atomic
def settle_sale(sale):
    sale = Sale.objects.select_for_update().get(pk=sale.pk)
    if sale.status != Sale.AccountStatus.DEBT:
        return False
    sale.status = Sale.AccountStatus.SETTLED
    sale.debtor_name = ""
    sale.save(update_fields=["status", "debtor_name"])
    return True
