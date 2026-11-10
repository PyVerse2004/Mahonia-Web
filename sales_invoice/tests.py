import jdatetime
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from inventory.models import Product, StockMovement

from .forms import SaleForm
from .models import Sale


class SaleFormTests(TestCase):
    def setUp(self):
        self.product = Product.objects.create(name="محصول نمونه", stock_quantity=10)

    def test_jalali_date_is_converted(self):
        form = SaleForm(
            data={
                "date": "۱۴۰۵/۰۸/۱۲",
                "product": self.product.pk,
                "quantity": "3",
                "unit_price": "12000",
            }
        )

        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["date"], jdatetime.date(1405, 8, 12).togregorian())
        sale = form.save()
        self.assertEqual(sale.total_amount, 36000)
        self.assertTrue(sale.is_active)


class SaleListAndOperationTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user(username="sales-user", password="test")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="sales_invoice", codename="view_sale")
        )
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="sales_invoice", codename="add_sale")
        )
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="sales_invoice", codename="change_sale")
        )
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label="sales_invoice", codename="delete_sale")
        )
        self.client.force_login(user)
        self.product = Product.objects.create(name="محصول نمونه", stock_quantity=10)

    def create_sale(self, date="2026-11-03", quantity=1, is_active=True, product=None):
        prod = product or self.product
        return Sale.objects.create(
            date=date,
            product=prod,
            product_name=prod.name,
            quantity=quantity,
            unit_price=1000,
            is_active=is_active,
        )

    def test_create_page_renders_jalali_calendar_and_today_button(self):
        response = self.client.get(reverse("sales_invoice:sale_create"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="date-today"')
        self.assertContains(response, "data-jdp")
        self.assertContains(response, "django_jalali.min.js")
        self.assertContains(response, "django_jalali.min.css")

    def test_creating_sale_decreases_stock_and_records_stock_movement(self):
        response = self.client.post(
            reverse("sales_invoice:sale_create"),
            {
                "date": "1405-08-12",
                "product": self.product.pk,
                "quantity": "3",
                "unit_price": "12000",
            },
        )

        self.assertRedirects(response, reverse("sales_invoice:sale_list"))
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 7)
        self.assertEqual(Sale.objects.count(), 1)
        sale = Sale.objects.first()
        self.assertTrue(sale.is_active)
        movement = StockMovement.objects.get()
        self.assertEqual(movement.quantity_change, -3)
        self.assertEqual(movement.stock_before, 10)
        self.assertEqual(movement.stock_after, 7)
        self.assertEqual(movement.reason, "ثبت فاکتور فروش")

    def test_sale_with_insufficient_stock_is_not_saved(self):
        response = self.client.post(
            reverse("sales_invoice:sale_create"),
            {
                "date": "1405-08-12",
                "product": self.product.pk,
                "quantity": "11",
                "unit_price": "12000",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "موجودی محصول")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)
        self.assertEqual(Sale.objects.count(), 0)
        self.assertEqual(StockMovement.objects.count(), 0)

    def test_editing_sale_updates_stock(self):
        response = self.client.post(
            reverse("sales_invoice:sale_create"),
            {
                "date": "1405-08-12",
                "product": self.product.pk,
                "quantity": "3",
                "unit_price": "12000",
            },
        )
        self.assertRedirects(response, reverse("sales_invoice:sale_list"))
        sale = Sale.objects.latest("pk")

        response = self.client.post(
            reverse("sales_invoice:sale_update", args=[sale.pk]),
            {
                "date": "1405-08-12",
                "product": self.product.pk,
                "quantity": "5",
                "unit_price": "12000",
            },
        )

        self.assertRedirects(response, reverse("sales_invoice:sale_list"))
        sale.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(sale.quantity, 5)
        self.assertEqual(self.product.stock_quantity, 5)
        self.assertEqual(StockMovement.objects.count(), 2)
        self.assertEqual(StockMovement.objects.latest("pk").quantity_change, -2)

    def test_editing_sale_to_another_product_restores_old_and_decreases_new_stock(self):
        self.client.post(
            reverse("sales_invoice:sale_create"),
            {
                "date": "1405-08-12",
                "product": self.product.pk,
                "quantity": "3",
                "unit_price": "12000",
            },
        )
        sale = Sale.objects.latest("pk")
        other_product = Product.objects.create(name="محصول دیگر", stock_quantity=8)

        response = self.client.post(
            reverse("sales_invoice:sale_update", args=[sale.pk]),
            {
                "date": "1405-08-12",
                "product": other_product.pk,
                "quantity": "4",
                "unit_price": "15000",
            },
        )

        self.assertRedirects(response, reverse("sales_invoice:sale_list"))
        sale.refresh_from_db()
        self.product.refresh_from_db()
        other_product.refresh_from_db()
        self.assertEqual(sale.product_id, other_product.pk)
        self.assertEqual(self.product.stock_quantity, 10)
        self.assertEqual(other_product.stock_quantity, 4)

    def test_toggle_active_sale_deactivates_and_restores_stock(self):
        self.client.post(
            reverse("sales_invoice:sale_create"),
            {
                "date": "1405-08-12",
                "product": self.product.pk,
                "quantity": "3",
                "unit_price": "12000",
            },
        )
        sale = Sale.objects.latest("pk")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 7)

        # Deactivate
        response = self.client.post(reverse("sales_invoice:sale_toggle_active", args=[sale.pk]))
        self.assertRedirects(response, reverse("sales_invoice:sale_list"))
        sale.refresh_from_db()
        self.assertFalse(sale.is_active)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)

        # Reactivate
        response = self.client.post(reverse("sales_invoice:sale_toggle_active", args=[sale.pk]))
        self.assertRedirects(response, reverse("sales_invoice:sale_list"))
        sale.refresh_from_db()
        self.assertTrue(sale.is_active)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 7)

    def test_filter_by_jalali_date(self):
        s1 = self.create_sale("2026-11-03")
        s2 = self.create_sale("2026-11-02")

        response = self.client.get(
            reverse("sales_invoice:sale_list"),
            {"date": "1405-08-12"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(s1, response.context["sales"])
        self.assertNotIn(s2, response.context["sales"])

    def test_filter_by_is_active(self):
        active_sale = self.create_sale(is_active=True)
        inactive_sale = self.create_sale(is_active=False)

        response = self.client.get(
            reverse("sales_invoice:sale_list"),
            {"is_active": "1"},
        )
        self.assertIn(active_sale, response.context["sales"])
        self.assertNotIn(inactive_sale, response.context["sales"])

        response2 = self.client.get(
            reverse("sales_invoice:sale_list"),
            {"is_active": "0"},
        )
        self.assertIn(inactive_sale, response2.context["sales"])
        self.assertNotIn(active_sale, response2.context["sales"])


class SaleAdminTests(TestCase):
    def setUp(self):
        self.admin_user = get_user_model().objects.create_superuser(
            username="admin-user", password="password", email="admin@example.com"
        )
        self.product = Product.objects.create(name="محصول ادمین", stock_quantity=10)
        self.sale = Sale.objects.create(
            date="2026-01-01",
            product=self.product,
            product_name=self.product.name,
            quantity=2,
            unit_price=5000,
            is_active=True,
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
            date="2026-01-02",
            product=self.product,
            product_name=self.product.name,
            quantity=3,
            unit_price=4000,
            is_active=True,
        )
        model_admin.save_model(None, new_sale, None, change=False)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 7)

        new_sale.quantity = 5
        model_admin.save_model(None, new_sale, None, change=True)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)

        # Deactivate in admin
        new_sale.is_active = False
        model_admin.save_model(None, new_sale, None, change=True)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)

        # Delete model
        model_admin.delete_model(None, new_sale)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 10)
