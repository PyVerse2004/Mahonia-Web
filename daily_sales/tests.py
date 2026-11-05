from django.test import TestCase

import jdatetime
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse

from inventory.models import Product, StockMovement

from .forms import SaleForm
from .models import Sale


class SaleFormTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(name="محصول نمونه", stock_quantity=10)

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

    def test_settled_sale_can_keep_debtor_name(self):
        form = SaleForm(
            data={
                "date": "۱۴۰۵/۰۸/۱۲",
                "product": self.product.pk,
                "quantity": "1",
                "unit_price": "1000",
                "status": Sale.AccountStatus.SETTLED,
                "debtor_name": "نام خریدار",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["debtor_name"], "نام خریدار")



    def test_partial_payment_deducts_from_debt_and_leaves_remaining(self):
        form = SaleForm(
            data={
                "date": "۱۴۰۵/۰۸/۱۲",
                "product": self.product.pk,
                "quantity": "2",
                "unit_price": "10000",
                "status": Sale.AccountStatus.DEBT,
                "debtor_name": "علی رضایی",
                "paid_amount": "5000",
                "payment_amount": "5000",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        sale = form.save()
        self.assertEqual(sale.paid_amount, 10000)
        self.assertEqual(sale.remaining_debt, 10000)
        self.assertEqual(sale.status, Sale.AccountStatus.DEBT)

    def test_full_payment_automatically_settles_account(self):
        form = SaleForm(
            data={
                "date": "۱۴۰۵/۰۸/۱۲",
                "product": self.product.pk,
                "quantity": "1",
                "unit_price": "10000",
                "status": Sale.AccountStatus.DEBT,
                "debtor_name": "علی رضایی",
                "paid_amount": "0",
                "payment_amount": "10000",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        sale = form.save()
        self.assertEqual(sale.paid_amount, 10000)
        self.assertEqual(sale.remaining_debt, 0)
        self.assertEqual(sale.status, Sale.AccountStatus.SETTLED)


class SaleListTests(TestCase):
    def test_filter_by_jalali_date(self):
        s1 = self.create_sale("2026-11-03", Sale.AccountStatus.SETTLED)
        s2 = self.create_sale("2026-11-02", Sale.AccountStatus.SETTLED)

        response = self.client.get(
            reverse("daily_sales:sale_list"),
            {"date": "1405-08-12"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(s1, response.context["sales"])
        self.assertNotIn(s2, response.context["sales"])

    def setUp(self):
        user = get_user_model().objects.create_user(username="sales-user", password="test")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="daily_sales", codename="view_sale")
        )
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="daily_sales", codename="add_sale")
        )
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="daily_sales", codename="change_sale")
        )
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="daily_sales", codename="delete_sale")
        )
        self.client.force_login(user)
        self.product = Product.objects.create(name="محصول نمونه", stock_quantity=10)

    def test_create_page_renders_jalali_calendar_and_today_button(self):
        response = self.client.get(reverse("daily_sales:sale_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="date-today"')
        self.assertContains(response, "data-jdp")
        self.assertContains(response, "django_jalali.min.js")
        self.assertContains(response, "django_jalali.min.css")

    def test_creating_sale_decreases_stock_and_records_stock_movement(self):
        response = self.client.post(
            reverse("daily_sales:sale_create"),
            {
                "date": "1405-08-12",
                "product": self.product.pk,
                "quantity": "3",
                "unit_price": "12000",
                "status": Sale.AccountStatus.SETTLED,
                "debtor_name": "",
            },
        )

        self.assertRedirects(response, reverse("daily_sales:sale_list"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 7)
        self.assertEqual(Sale.objects.count(), 1)
        movement = StockMovement.objects.get()
        self.assertEqual(movement.quantity_change, -3)
        self.assertEqual(movement.stock_before, 10)
        self.assertEqual(movement.stock_after, 7)
        self.assertEqual(movement.reason, "ثبت فروش")

    def test_sale_with_insufficient_stock_is_not_saved(self):
        response = self.client.post(
            reverse("daily_sales:sale_create"),
            {
                "date": "1405-08-12",
                "product": self.product.pk,
                "quantity": "11",
                "unit_price": "12000",
                "status": Sale.AccountStatus.SETTLED,
                "debtor_name": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "موجودی محصول")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)
        self.assertEqual(Sale.objects.count(), 0)
        self.assertEqual(StockMovement.objects.count(), 0)

    def post_sale(self, quantity=3, status=Sale.AccountStatus.DEBT, debtor_name="مشتری"):
        response = self.client.post(
            reverse("daily_sales:sale_create"),
            {
                "date": "1405-08-12",
                "product": self.product.pk,
                "quantity": str(quantity),
                "unit_price": "12000",
                "status": status,
                "debtor_name": debtor_name,
            },
        )
        self.assertRedirects(response, reverse("daily_sales:sale_list"))
        return Sale.objects.latest("pk")

    def test_editing_sale_updates_stock_and_account_status(self):
        sale = self.post_sale()

        response = self.client.post(
            reverse("daily_sales:sale_update", args=[sale.pk]),
            {
                "date": "1405-08-12",
                "product": self.product.pk,
                "quantity": "5",
                "unit_price": "12000",
                "status": Sale.AccountStatus.SETTLED,
                "debtor_name": "",
            },
        )

        self.assertRedirects(response, reverse("daily_sales:sale_list"))
        sale.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(sale.status, Sale.AccountStatus.SETTLED)
        self.assertEqual(sale.debtor_name, "")
        self.assertEqual(sale.quantity, 5)
        self.assertEqual(self.product.stock_quantity, 5)
        self.assertEqual(StockMovement.objects.count(), 2)
        self.assertEqual(StockMovement.objects.latest("pk").quantity_change, -2)

    def test_editing_sale_to_another_product_restores_old_and_decreases_new_stock(self):
        sale = self.post_sale(quantity=3, status=Sale.AccountStatus.SETTLED, debtor_name="")
        other_product = Product.objects.create(name="محصول دیگر", stock_quantity=8)

        response = self.client.post(
            reverse("daily_sales:sale_update", args=[sale.pk]),
            {
                "date": "1405-08-12",
                "product": other_product.pk,
                "quantity": "4",
                "unit_price": "15000",
                "status": Sale.AccountStatus.SETTLED,
                "debtor_name": "",
            },
        )

        self.assertRedirects(response, reverse("daily_sales:sale_list"))
        sale.refresh_from_db()
        self.product.refresh_from_db()
        other_product.refresh_from_db()
        self.assertEqual(sale.product_id, other_product.pk)
        self.assertEqual(self.product.stock_quantity, 10)
        self.assertEqual(other_product.stock_quantity, 4)
        self.assertEqual(StockMovement.objects.count(), 3)

    def test_editing_sale_with_insufficient_stock_keeps_sale_and_stock_unchanged(self):
        sale = self.post_sale(quantity=3)
        other_product = Product.objects.create(name="محصول دیگر", stock_quantity=2)

        response = self.client.post(
            reverse("daily_sales:sale_update", args=[sale.pk]),
            {
                "date": "1405-08-12",
                "product": other_product.pk,
                "quantity": "4",
                "unit_price": "15000",
                "status": Sale.AccountStatus.SETTLED,
                "debtor_name": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "موجودی محصول")
        sale.refresh_from_db()
        self.product.refresh_from_db()
        other_product.refresh_from_db()
        self.assertEqual(sale.product_id, self.product.pk)
        self.assertEqual(sale.quantity, 3)
        self.assertEqual(self.product.stock_quantity, 7)
        self.assertEqual(other_product.stock_quantity, 2)
        self.assertEqual(StockMovement.objects.count(), 1)

    def test_deleting_sale_restores_stock(self):
        sale = self.post_sale(quantity=3)

        response = self.client.post(reverse("daily_sales:sale_delete", args=[sale.pk]))

        self.assertRedirects(response, reverse("daily_sales:sale_list"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)
        self.assertFalse(Sale.objects.filter(pk=sale.pk).exists())
        self.assertEqual(StockMovement.objects.count(), 2)
        self.assertEqual(StockMovement.objects.latest("pk").quantity_change, 3)
        self.assertEqual(StockMovement.objects.latest("pk").reason, "حذف فروش")

    def test_debt_sale_can_be_settled_from_sales_list(self):
        sale = self.post_sale(debtor_name="مشتری نمونه")

        response = self.client.post(reverse("daily_sales:sale_settle", args=[sale.pk]))

        self.assertRedirects(response, reverse("daily_sales:sale_list"))
        sale.refresh_from_db()
        self.assertEqual(sale.status, Sale.AccountStatus.SETTLED)
        self.assertEqual(sale.debtor_name, "مشتری نمونه")
        self.assertEqual(StockMovement.objects.count(), 1)

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



    def test_editing_debt_sale_with_partial_payment_updates_remaining_debt(self):
        sale = self.post_sale(quantity=2)
        self.assertEqual(sale.remaining_debt, 24000)

        response = self.client.post(
            reverse("daily_sales:sale_update", args=[sale.pk]),
            {
                "date": "1405-08-12",
                "product": self.product.pk,
                "quantity": "2",
                "unit_price": "12000",
                "status": Sale.AccountStatus.DEBT,
                "debtor_name": "مشتری",
                "paid_amount": "0",
                "payment_amount": "10000",
            },
        )
        self.assertRedirects(response, reverse("daily_sales:sale_list"))
        sale.refresh_from_db()
        self.assertEqual(sale.paid_amount, 10000)
        self.assertEqual(sale.remaining_debt, 14000)
        self.assertEqual(sale.status, Sale.AccountStatus.DEBT)

        response = self.client.post(
            reverse("daily_sales:sale_update", args=[sale.pk]),
            {
                "date": "1405-08-12",
                "product": self.product.pk,
                "quantity": "2",
                "unit_price": "12000",
                "status": Sale.AccountStatus.DEBT,
                "debtor_name": "مشتری",
                "paid_amount": "10000",
                "payment_amount": "14000",
            },
        )
        self.assertRedirects(response, reverse("daily_sales:sale_list"))
        sale.refresh_from_db()
        self.assertEqual(sale.paid_amount, 24000)
        self.assertEqual(sale.remaining_debt, 0)
        self.assertEqual(sale.status, Sale.AccountStatus.SETTLED)


class SaleAdminTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(
            username="admin-user", password="password", email="admin@example.com"
        )
        self.product = Product.objects.create(name='محصول ادمین', stock_quantity=10)
        self.sale = Sale.objects.create(
            date='2026-01-01',
            product=self.product,
            product_name=self.product.name,
            quantity=2,
            unit_price=5000,
            status=Sale.AccountStatus.SETTLED,
        )

    def test_sale_admin_allows_full_access_and_fields_are_editable(self):
        from django.contrib.admin.sites import site
        from django.test import RequestFactory
        from .admin import SaleAdmin

        rf = RequestFactory()
        request = rf.get("/")
        request.user = self.admin_user

        model_admin = SaleAdmin(Sale, site)
        self.assertTrue(model_admin.has_add_permission(request))
        self.assertTrue(model_admin.has_change_permission(request, self.sale))
        self.assertTrue(model_admin.has_delete_permission(request, self.sale))
        self.assertEqual(model_admin.get_readonly_fields(request, self.sale), ("created_at",))

    def test_sale_admin_save_and_delete_syncs_inventory(self):
        from django.contrib.admin.sites import site
        from .admin import SaleAdmin

        model_admin = SaleAdmin(Sale, site)

        new_sale = Sale(
            date='2026-01-02',
            product=self.product,
            product_name=self.product.name,
            quantity=3,
            unit_price=4000,
            status=Sale.AccountStatus.SETTLED,
        )
        model_admin.save_model(None, new_sale, None, change=False)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 7)

        new_sale.quantity = 5
        model_admin.save_model(None, new_sale, None, change=True)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)

        model_admin.delete_model(None, new_sale)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)
