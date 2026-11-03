from django.test import TestCase

import jdatetime
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse

from inventory.models import Product

from .forms import SaleForm
from .models import Sale


class SaleFormTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(name="محصول نمونه")

    def test_jalali_date_is_converted_and_debt_name_is_required(self):
        form = SaleForm(
            data={
                "date": "۱۴۰۵/۰۸/۱۲",
                "product": self.product.pk,
                "quantity": "3",
                "unit_price": "12000",
                "status": Sale.AccountStatus.DEBT,
                "debtor_name": "  علی رضایی  ",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["date"], jdatetime.date(1405, 8, 12).togregorian())
        self.assertEqual(form.cleaned_data["debtor_name"], "علی رضایی")
        self.assertEqual(form.save().total_amount, 36000)

    def test_debt_status_requires_debtor_name(self):
        form = SaleForm(
            data={
                "date": "۱۴۰۵/۰۸/۱۲",
                "product": self.product.pk,
                "quantity": "1",
                "unit_price": "1000",
                "status": Sale.AccountStatus.DEBT,
                "debtor_name": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("debtor_name", form.errors)

    def test_settled_sale_does_not_keep_debtor_name(self):
        form = SaleForm(
            data={
                "date": "۱۴۰۵/۰۸/۱۲",
                "product": self.product.pk,
                "quantity": "1",
                "unit_price": "1000",
                "status": Sale.AccountStatus.SETTLED,
                "debtor_name": "نام اضافه",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["debtor_name"], "")


class SaleListTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="sales-user", password="test")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="daily_sales", codename="view_sale")
        )
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="daily_sales", codename="add_sale")
        )
        self.client.force_login(user)
        self.product = Product.objects.create(name="محصول نمونه")

    def test_create_page_renders_jalali_calendar_and_today_button(self):
        response = self.client.get(reverse("daily_sales:sale_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="date-today"')
        self.assertContains(response, "data-jdp")
        self.assertContains(response, "django_jalali.min.js")
        self.assertContains(response, "django_jalali.min.css")

    def create_sale(self, date, status, debtor_name=""):
        return Sale.objects.create(
            date=date,
            product=self.product,
            product_name=self.product.name,
            quantity=1,
            unit_price=1000,
            status=status,
            debtor_name=debtor_name,
        )

    def test_list_is_ordered_by_latest_sale_date(self):
        older = self.create_sale("2026-01-01", Sale.AccountStatus.SETTLED)
        newer = self.create_sale("2026-02-01", Sale.AccountStatus.DEBT, "مشتری")

        response = self.client.get(reverse("daily_sales:sale_list"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["sales"]), [newer, older])

    def test_search_and_account_status_filters_can_be_combined(self):
        matching = self.create_sale("2026-02-01", Sale.AccountStatus.DEBT, "مشتری نمونه")
        self.create_sale("2026-02-02", Sale.AccountStatus.SETTLED)

        response = self.client.get(
            reverse("daily_sales:sale_list"),
            {"q": "مشتری", "status": Sale.AccountStatus.DEBT},
        )

        self.assertEqual(list(response.context["sales"]), [matching])
