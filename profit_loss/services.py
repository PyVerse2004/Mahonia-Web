import datetime
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import DecimalField, F, Sum
import jdatetime

from sales_invoice.models import Sale


def get_jalali_date_range(year, month=None):
    """
    سال و ماه شمسی را دریافت کرده و بازه متناظر میلادی (start_date, end_date) را برمی‌گرداند.
    """
    year = int(year)
    if month:
        month = int(month)
        start_jalali = jdatetime.date(year, month, 1)
        if month == 12:
            next_jalali = jdatetime.date(year + 1, 1, 1)
        else:
            next_jalali = jdatetime.date(year, month + 1, 1)
        end_jalali = next_jalali - datetime.timedelta(days=1)
    else:
        start_jalali = jdatetime.date(year, 1, 1)
        next_jalali = jdatetime.date(year + 1, 1, 1)
        end_jalali = next_jalali - datetime.timedelta(days=1)

    return start_jalali.togregorian(), end_jalali.togregorian()


def get_profit_loss_report(year=None, month=None, product_id=None, query=None):
    """
    فاکتورهای فروش فعال را طبق فیلترها پالایش کرده و گزارش خلاصه سود و زیان را تولید می‌کند.
    """
    sales = Sale.objects.filter(is_active=True).select_related("product")

    selected_year = year
    selected_month = month

    # اگر فقط ماه انتخاب شده باشد و سال خالی باشد، سال جاری شمسی در نظر گرفته می‌شود
    if selected_month and not selected_year:
        selected_year = jdatetime.date.today().year

    if selected_year:
        start_date, end_date = get_jalali_date_range(selected_year, selected_month)
        sales = sales.filter(date__range=(start_date, end_date))

    if product_id:
        sales = sales.filter(product_id=product_id)

    if query:
        query = query.strip()
        if query:
            sales = sales.filter(product_name__icontains=query)

    aggregates = sales.aggregate(
        total_sales=Sum(
            F("quantity") * F("unit_price"),
            output_field=DecimalField(max_digits=20, decimal_places=0),
        ),
        total_cost=Sum(
            F("quantity") * F("purchase_unit_price"),
            output_field=DecimalField(max_digits=20, decimal_places=0),
        ),
        total_quantity=Sum("quantity"),
    )

    total_sales = aggregates["total_sales"] or Decimal("0")
    total_cost = aggregates["total_cost"] or Decimal("0")
    total_quantity = aggregates["total_quantity"] or 0
    total_invoices = sales.count()
    net_profit = total_sales - total_cost

    if total_sales > 0:
        profit_margin = ((net_profit / total_sales) * 100).quantize(
            Decimal("0.1"), rounding=ROUND_HALF_UP
        )
    else:
        profit_margin = Decimal("0")

    summary = {
        "total_sales": total_sales,
        "total_cost": total_cost,
        "net_profit": net_profit,
        "is_profitable": net_profit >= 0,
        "profit_margin": profit_margin,
        "total_quantity": total_quantity,
        "total_invoices": total_invoices,
    }

    return sales, summary
