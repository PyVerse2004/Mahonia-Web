from decimal import Decimal

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse

from inventory.models import Product
from inventory.services import StockError, change_stock

from .models import PurchaseInvoice, Supplier


def make_admin():
    return User.objects.create_superuser("admin", password="pass12345")


def make_product(name="Legend", stock=0, price=0):
    return Product.objects.create(
        name=name, stock_quantity=stock, purchase_price=Decimal(price), sale_price=0
    )


def invoice_data(supplier, rows, existing=None, date="2026-10-31"):
    """داده‌ی POST برای فرم فاکتور و formset ردیف‌ها.

    rows: لیست (product یا نام محصول، quantity, unit_price)
    existing: برای ویرایش، فاکتوری که ردیف‌هایش به همین ترتیب قبلاً ثبت شده‌اند.
    """
    data = {
        "date": date,
        "supplier": supplier.pk,
        "items-TOTAL_FORMS": len(rows),
        "items-INITIAL_FORMS": existing.items.count() if existing else 0,
        "items-MIN_NUM_FORMS": 1,
        "items-MAX_NUM_FORMS": 1000,
    }
    old_items = list(existing.items.all()) if existing else []
    for i, (product, quantity, price) in enumerate(rows):
        data[f"items-{i}-product_text"] = getattr(product, "name", product)
        data[f"items-{i}-quantity"] = quantity
        data[f"items-{i}-unit_price"] = price
        if i < len(old_items):
            data[f"items-{i}-id"] = old_items[i].pk
            data[f"items-{i}-invoice"] = existing.pk
    return data


class PurchaseTestCase(TestCase):
    def setUp(self):
        self.client.force_login(make_admin())
        self.supplier = Supplier.objects.create(name="Atr Co")
        self.legend = make_product("Legend")
        self.hawas = make_product("Hawas")

    def post_new(self, rows, **kwargs):
        return self.client.post(
            reverse("purchases:invoice_create"), invoice_data(self.supplier, rows, **kwargs)
        )

    def refresh(self, product):
        product.refresh_from_db()
        return product


class CreateInvoiceTests(PurchaseTestCase):
    def test_totals_stock_and_price_after_create(self):
        response = self.post_new(
            [(self.legend, 10, 4000000), (self.hawas, 5, 3000000)]
        )
        self.assertRedirects(response, reverse("purchases:invoice_list"))

        invoice = PurchaseInvoice.objects.get()
        self.assertEqual(invoice.total_quantity, 15)
        self.assertEqual(invoice.total_amount, Decimal(55000000))
        self.assertEqual(invoice.items.count(), 2)

        self.assertEqual(self.refresh(self.legend).stock_quantity, 10)
        self.assertEqual(self.refresh(self.legend).purchase_price, Decimal(4000000))
        self.assertEqual(self.refresh(self.hawas).stock_quantity, 5)

    def test_price_is_simple_average_across_invoices(self):
        self.post_new([(self.legend, 10, 4000000)])
        self.post_new([(self.legend, 30, 5000000)])
        legend = self.refresh(self.legend)
        # (4,000,000 + 5,000,000) / 2 = 4,500,000
        self.assertEqual(legend.purchase_price, Decimal(4500000))
        self.assertEqual(legend.stock_quantity, 40)

    def test_quantity_does_not_affect_average(self):
        self.post_new([(self.legend, 1, 100)])
        self.post_new([(self.legend, 1000, 200)])
        self.assertEqual(self.refresh(self.legend).purchase_price, Decimal(150))

    def test_average_is_rounded_half_up_to_whole_number(self):
        self.post_new([(self.legend, 1, 100)])
        self.post_new([(self.legend, 1, 101)])
        # (100 + 101) / 2 = 100.5
        self.assertEqual(self.refresh(self.legend).purchase_price, Decimal(101))

    def test_opening_stock_is_kept_and_added_to(self):
        self.legend.stock_quantity = 5
        self.legend.save()
        self.post_new([(self.legend, 10, 4000000)])
        self.assertEqual(self.refresh(self.legend).stock_quantity, 15)

    def test_same_product_on_two_rows(self):
        self.post_new([(self.legend, 2, 100), (self.legend, 2, 200)])
        legend = self.refresh(self.legend)
        self.assertEqual(legend.stock_quantity, 4)
        self.assertEqual(legend.purchase_price, Decimal(150))

    def test_item_keeps_product_name_snapshot(self):
        self.post_new([(self.legend, 1, 100)])
        self.assertEqual(PurchaseInvoice.objects.get().items.get().product_name, "Legend")

    def test_invoice_without_items_is_rejected(self):
        data = invoice_data(self.supplier, [])
        data["items-TOTAL_FORMS"] = 0
        response = self.client.post(reverse("purchases:invoice_create"), data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PurchaseInvoice.objects.count(), 0)

    def test_invalid_quantity_is_rejected(self):
        response = self.post_new([(self.legend, 0, 100)])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PurchaseInvoice.objects.count(), 0)
        self.assertEqual(self.refresh(self.legend).stock_quantity, 0)

    def test_failed_create_changes_nothing(self):
        self.post_new([(self.legend, 5, 100), (self.hawas, -1, 100)])
        self.assertEqual(PurchaseInvoice.objects.count(), 0)
        self.assertEqual(self.refresh(self.legend).stock_quantity, 0)

    def test_form_page_renders_with_empty_row_template(self):
        response = self.client.get(reverse("purchases:invoice_create"))
        self.assertContains(response, "items-TOTAL_FORMS")
        self.assertContains(response, "__prefix__")


class UpdateInvoiceTests(PurchaseTestCase):
    def setUp(self):
        super().setUp()
        self.post_new([(self.legend, 10, 4000000), (self.hawas, 5, 3000000)])
        self.invoice = PurchaseInvoice.objects.get()

    def post_update(self, rows):
        return self.client.post(
            reverse("purchases:invoice_update", args=[self.invoice.pk]),
            invoice_data(self.supplier, rows, existing=self.invoice),
        )

    def test_edit_quantity_and_price_updates_everything(self):
        response = self.post_update([(self.legend, 20, 5000000), (self.hawas, 5, 3000000)])
        self.assertRedirects(response, reverse("purchases:invoice_list"))

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.total_quantity, 25)
        self.assertEqual(self.invoice.total_amount, Decimal(115000000))

        legend = self.refresh(self.legend)
        self.assertEqual(legend.stock_quantity, 20)
        self.assertEqual(legend.purchase_price, Decimal(5000000))
        self.assertEqual(self.refresh(self.hawas).stock_quantity, 5)

    def test_changing_product_moves_stock_between_products(self):
        self.post_update([(self.hawas, 10, 4000000), (self.hawas, 5, 3000000)])
        self.assertEqual(self.refresh(self.legend).stock_quantity, 0)
        self.assertEqual(self.refresh(self.hawas).stock_quantity, 15)

    def test_removing_a_row_with_delete_flag(self):
        data = invoice_data(
            self.supplier,
            [(self.legend, 10, 4000000), (self.hawas, 5, 3000000)],
            existing=self.invoice,
        )
        data["items-1-DELETE"] = "on"
        self.client.post(reverse("purchases:invoice_update", args=[self.invoice.pk]), data)

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.items.count(), 1)
        self.assertEqual(self.invoice.total_quantity, 10)
        self.assertEqual(self.refresh(self.hawas).stock_quantity, 0)

    def test_edit_that_would_make_stock_negative_is_rolled_back(self):
        # بعد از خرید، ۸ عدد فروخته شده است (فروش هنوز ثبت نمی‌شود؛ مستقیم کم می‌کنیم).
        change_stock(self.legend.pk, -8)

        response = self.post_update([(self.legend, 5, 4000000), (self.hawas, 5, 3000000)])
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "کافی نیست")

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.total_quantity, 15)
        self.assertEqual(self.refresh(self.legend).stock_quantity, 2)

    def test_update_page_renders_existing_rows(self):
        response = self.client.get(reverse("purchases:invoice_update", args=[self.invoice.pk]))
        self.assertContains(response, "Legend")
        self.assertContains(response, "value=\"10\"")


class DeleteInvoiceTests(PurchaseTestCase):
    def test_delete_reverts_stock_and_recalculates_price(self):
        self.post_new([(self.legend, 10, 4000000)])
        self.post_new([(self.legend, 30, 5000000)])
        second = PurchaseInvoice.objects.order_by("id").last()

        response = self.client.post(reverse("purchases:invoice_delete", args=[second.pk]))
        self.assertRedirects(response, reverse("purchases:invoice_list"))

        legend = self.refresh(self.legend)
        self.assertEqual(legend.stock_quantity, 10)
        self.assertEqual(legend.purchase_price, Decimal(4000000))
        self.assertEqual(PurchaseInvoice.objects.count(), 1)

    def test_delete_blocked_when_stock_was_used(self):
        self.post_new([(self.legend, 10, 4000000)])
        invoice = PurchaseInvoice.objects.get()
        change_stock(self.legend.pk, -8)

        response = self.client.post(reverse("purchases:invoice_delete", args=[invoice.pk]))
        self.assertRedirects(response, reverse("purchases:invoice_list"))
        self.assertTrue(PurchaseInvoice.objects.filter(pk=invoice.pk).exists())
        self.assertEqual(self.refresh(self.legend).stock_quantity, 2)

    def test_deleting_last_invoice_keeps_last_price(self):
        self.post_new([(self.legend, 10, 4000000)])
        invoice = PurchaseInvoice.objects.get()
        self.client.post(reverse("purchases:invoice_delete", args=[invoice.pk]))
        legend = self.refresh(self.legend)
        self.assertEqual(legend.stock_quantity, 0)
        self.assertEqual(legend.purchase_price, Decimal(4000000))

    def test_deleting_product_keeps_invoice_row_with_name(self):
        self.post_new([(self.legend, 10, 4000000)])
        self.legend.delete()
        item = PurchaseInvoice.objects.get().items.get()
        self.assertIsNone(item.product)
        self.assertEqual(item.product_name, "Legend")

    def test_deleting_invoice_with_deleted_product_works(self):
        self.post_new([(self.legend, 10, 4000000)])
        invoice = PurchaseInvoice.objects.get()
        self.legend.delete()
        response = self.client.post(reverse("purchases:invoice_delete", args=[invoice.pk]))
        self.assertRedirects(response, reverse("purchases:invoice_list"))
        self.assertEqual(PurchaseInvoice.objects.count(), 0)


class NewProductFromInvoiceTests(PurchaseTestCase):
    def test_new_name_creates_product_with_stock_and_price(self):
        response = self.post_new([("Lalique", 8, 5000000)])
        self.assertRedirects(response, reverse("purchases:invoice_list"))

        product = Product.objects.get(name="Lalique")
        self.assertEqual(product.stock_quantity, 8)
        self.assertEqual(product.purchase_price, Decimal(5000000))
        self.assertEqual(product.sale_price, 0)

        item = PurchaseInvoice.objects.get().items.get()
        self.assertEqual(item.product, product)
        self.assertEqual(item.product_name, "Lalique")

    def test_existing_name_matches_ignoring_case_and_spaces(self):
        self.post_new([("  legend ", 3, 100)])
        self.assertEqual(Product.objects.filter(name__iexact="legend").count(), 1)
        self.assertEqual(self.refresh(self.legend).stock_quantity, 3)

    def test_same_new_name_on_two_rows_creates_one_product(self):
        self.post_new([("Lalique", 2, 100), ("lalique", 3, 300)])
        product = Product.objects.get(name="Lalique")
        self.assertEqual(Product.objects.filter(name__iexact="lalique").count(), 1)
        self.assertEqual(product.stock_quantity, 5)
        self.assertEqual(product.purchase_price, Decimal(200))

    def test_failed_invoice_does_not_create_product(self):
        before = Product.objects.count()
        self.post_new([("Lalique", 5, 100), (self.legend, 0, 100)])
        self.assertEqual(Product.objects.count(), before)
        self.assertEqual(PurchaseInvoice.objects.count(), 0)

    def test_blank_product_name_is_rejected(self):
        response = self.post_new([("", 5, 100)])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PurchaseInvoice.objects.count(), 0)

    def test_editing_row_to_new_name_creates_product_and_moves_stock(self):
        self.post_new([(self.legend, 10, 4000000)])
        invoice = PurchaseInvoice.objects.get()
        self.client.post(
            reverse("purchases:invoice_update", args=[invoice.pk]),
            invoice_data(self.supplier, [("Lalique", 10, 4000000)], existing=invoice),
        )
        self.assertEqual(self.refresh(self.legend).stock_quantity, 0)
        self.assertEqual(Product.objects.get(name="Lalique").stock_quantity, 10)

    def test_editing_row_of_deleted_product_does_not_recreate_it(self):
        self.post_new([(self.legend, 10, 4000000), (self.hawas, 5, 3000000)])
        invoice = PurchaseInvoice.objects.get()
        self.legend.delete()

        response = self.client.post(
            reverse("purchases:invoice_update", args=[invoice.pk]),
            invoice_data(
                self.supplier,
                [("Legend", 12, 4000000), (self.hawas, 5, 3000000)],
                existing=invoice,
            ),
        )
        self.assertRedirects(response, reverse("purchases:invoice_list"))
        self.assertFalse(Product.objects.filter(name="Legend").exists())
        invoice.refresh_from_db()
        self.assertEqual(invoice.total_quantity, 17)

    def test_form_page_lists_existing_products_as_suggestions(self):
        response = self.client.get(reverse("purchases:invoice_create"))
        self.assertContains(response, 'id="product-options"')
        self.assertContains(response, '<option value="Legend">')

    def test_update_page_shows_product_name_in_row(self):
        self.post_new([(self.legend, 10, 4000000)])
        invoice = PurchaseInvoice.objects.get()
        response = self.client.get(reverse("purchases:invoice_update", args=[invoice.pk]))
        self.assertContains(response, 'value="Legend"')


class NewProductPermissionTests(PurchaseTestCase):
    def login_with(self, *codenames):
        user = User.objects.create_user("clerk", password="pass12345")
        for codename in codenames:
            user.user_permissions.add(Permission.objects.get(codename=codename))
        self.client.force_login(user)

    def test_user_without_add_product_cannot_create_new_product(self):
        self.login_with("add_purchaseinvoice")
        response = self.post_new([("Lalique", 5, 100)])
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "اجازه‌ی ثبت محصول جدید")
        self.assertFalse(Product.objects.filter(name="Lalique").exists())
        self.assertEqual(PurchaseInvoice.objects.count(), 0)

    def test_user_without_add_product_can_use_existing_products(self):
        self.login_with("add_purchaseinvoice")
        response = self.post_new([(self.legend, 5, 100)])
        self.assertRedirects(
            response, reverse("purchases:invoice_list"), fetch_redirect_response=False
        )
        self.assertEqual(self.refresh(self.legend).stock_quantity, 5)

    def test_user_with_add_product_can_create_new_product(self):
        self.login_with("add_purchaseinvoice", "add_product")
        self.post_new([("Lalique", 5, 100)])
        self.assertTrue(Product.objects.filter(name="Lalique").exists())


class StockServiceTests(TestCase):
    def test_change_stock_increase_and_decrease(self):
        product = make_product(stock=5)
        change_stock(product.pk, 3)
        change_stock(product.pk, -8)
        product.refresh_from_db()
        self.assertEqual(product.stock_quantity, 0)

    def test_change_stock_below_zero_raises(self):
        product = make_product(stock=2)
        with self.assertRaises(StockError):
            change_stock(product.pk, -3)
        product.refresh_from_db()
        self.assertEqual(product.stock_quantity, 2)


class SupplierTests(TestCase):
    def setUp(self):
        self.client.force_login(make_admin())

    def test_create_and_update_supplier(self):
        response = self.client.post(reverse("purchases:supplier_create"), {"name": "Atr Co"})
        self.assertRedirects(response, reverse("purchases:supplier_list"))
        supplier = Supplier.objects.get()
        self.client.post(
            reverse("purchases:supplier_update", args=[supplier.pk]), {"name": "Atr Co 2"}
        )
        supplier.refresh_from_db()
        self.assertEqual(supplier.name, "Atr Co 2")

    def test_supplier_name_is_unique_case_insensitive(self):
        Supplier.objects.create(name="Atr Co")
        response = self.client.post(reverse("purchases:supplier_create"), {"name": "atr co"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "قبلاً ثبت شده")
        self.assertEqual(Supplier.objects.count(), 1)

    def test_supplier_with_invoices_cannot_be_deleted(self):
        from django.db.models import ProtectedError

        supplier = Supplier.objects.create(name="Atr Co")
        PurchaseInvoice.objects.create(supplier=supplier)
        with self.assertRaises(ProtectedError):
            supplier.delete()


class PurchasePermissionTests(TestCase):
    def test_anonymous_redirected_to_login(self):
        for name in ["invoice_list", "invoice_create", "supplier_list", "supplier_create"]:
            response = self.client.get(reverse(f"purchases:{name}"))
            self.assertEqual(response.status_code, 302, name)
            self.assertIn(reverse("login"), response["Location"])

    def test_user_without_permission_gets_403(self):
        self.client.force_login(User.objects.create_user("u", password="pass12345"))
        self.assertEqual(self.client.get(reverse("purchases:invoice_list")).status_code, 403)

    def test_view_only_user_cannot_create_or_delete(self):
        user = User.objects.create_user("v", password="pass12345")
        user.user_permissions.add(Permission.objects.get(codename="view_purchaseinvoice"))
        supplier = Supplier.objects.create(name="Atr Co")
        invoice = PurchaseInvoice.objects.create(supplier=supplier)
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("purchases:invoice_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("purchases:invoice_create")).status_code, 403)
        self.assertEqual(
            self.client.post(reverse("purchases:invoice_delete", args=[invoice.pk])).status_code,
            403,
        )
