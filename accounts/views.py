from decimal import Decimal

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.db.models import F, Sum
from django.utils import timezone
from django.views.generic import TemplateView
from jalali_date import date2jalali

from inventory.models import Product
from sales_invoice.models import Sale
from .forms import LoginForm
from .models import UserProfile, sync_user_role_permissions

PERSIAN_WEEKDAYS = {
    0: "دوشنبه",
    1: "سه‌شنبه",
    2: "چهارشنبه",
    3: "پنج‌شنبه",
    4: "جمعه",
    5: "شنبه",
    6: "یک‌شنبه",
}

PERSIAN_MONTHS = {
    1: "فروردین",
    2: "اردیبهشت",
    3: "خرداد",
    4: "تیر",
    5: "مرداد",
    6: "شهریور",
    7: "مهر",
    8: "آبان",
    9: "آذر",
    10: "دی",
    11: "بهمن",
    12: "اسفند",
}


class CustomLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user
        profile, _ = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "role": UserProfile.ROLE_MANAGER if user.is_superuser else UserProfile.ROLE_SELLER
            },
        )
        effective_role = UserProfile.ROLE_MANAGER if user.is_superuser else profile.role
        self.request.session["active_role"] = effective_role
        sync_user_role_permissions(user, effective_role)
        return response


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.localtime()
        today = now.date()

        # 1. تاریخ و ساعت امروز (شمسی با روز هفته و زمان رسمی)
        j_date = date2jalali(today)
        weekday_name = PERSIAN_WEEKDAYS.get(now.weekday(), "")
        month_name = PERSIAN_MONTHS.get(j_date.month, "")
        formatted_jalali_date = f"{j_date.day} {month_name} {j_date.year}"
        numeric_jalali_date = f"{j_date.year:04d}/{j_date.month:02d}/{j_date.day:02d}"

        # 2. تعداد کل محصولات در انبار
        total_products = Product.objects.count()

        # 3. تعداد فروش و جمع کل مبلغ فروش امروز (روزانه)
        today_sales = Sale.objects.filter(date=today, is_active=True)
        sales_metrics = today_sales.aggregate(
            total_amount=Sum(F("quantity") * F("unit_price")),
            total_quantity=Sum("quantity"),
        )
        today_sales_count = today_sales.count()
        today_sales_quantity = sales_metrics["total_quantity"] or 0
        today_sales_amount = sales_metrics["total_amount"] or Decimal("0")

        context.update(
            {
                "today_jalali_date": formatted_jalali_date,
                "today_numeric_date": numeric_jalali_date,
                "today_weekday": weekday_name,
                "current_time": now.strftime("%H:%M:%S"),
                "total_products": total_products,
                "today_sales_count": today_sales_count,
                "today_sales_quantity": today_sales_quantity,
                "today_sales_amount": today_sales_amount,
            }
        )
        return context
