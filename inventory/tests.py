from decimal import Decimal

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse

from .models import Product, StockMovement


def make_user(username="user", perms=(), superuser=False):
    if superuser:
        return User.objects.create_superuser(username, password="pass12345")
    user = User.objects.create_user(username, password="pass12345")
    for codename in perms:
        user.user_permissions.add(Permission.objects.get(codename=codename))
    return user


def make_product(name="Legend", stock=5, buy=3500000, sale=5600000):
    return Product.objects.create(
        name=name,
        stock_quantity=stock,
        purchase_price=Decimal(buy),
        sale_price=Decimal(sale),
    )


class ProductModelTests(TestCase):
    def test_has_no_is_active_field(self):
        field_names = [f.name for f in Product._meta.get_fields()]
        self.assertNotIn("is_active", field_names)

    def test_name_is_unique_case_insensitive(self):
        make_product("Legend")
        duplicate = Product(name="legend")
        with self.assertRaises(Exception):
            duplicate.full_clean()


class ProductAccessTests(TestCase):
    def setUp(self):
        self.product = make_product()

    def test_anonymous_is_redirected_to_login(self):
        urls = [
            reverse("inventory:product_list"),
            reverse("inventory:stock_movement_list"),
            reverse("inventory:product_create"),
            reverse("inventory:product_update", args=[self.product.pk]),
            reverse("inventory:product_delete", args=[self.product.pk]),
        ]
        for url in urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, url)
            self.assertIn(reverse("login"), response["Location"])

    def test_user_without_permission_gets_403(self):
        self.client.force_login(make_user())
        response = self.client.get(reverse("inventory:product_list"))
        self.assertEqual(response.status_code, 403)

    def test_view_only_user_cannot_delete(self):
        self.client.force_login(make_user(perms=["view_product"]))
        url = reverse("inventory:product_delete", args=[self.product.pk])
        self.assertEqual(self.client.post(url).status_code, 403)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())


class ProductCrudTests(TestCase):
    def setUp(self):
        self.client.force_login(make_user("admin", superuser=True))

    def test_list_shows_products(self):
        make_product("Legend")
        make_product("Hawas")
        response = self.client.get(reverse("inventory:product_list"))
        self.assertContains(response, "Legend")
        self.assertContains(response, "Hawas")

    def test_prices_are_shown_with_thousands_separator(self):
        make_product("Legend", sale=5600000)
        response = self.client.get(reverse("inventory:product_list"))
        self.assertContains(response, "5,600,000")

    def test_unset_sale_price_is_flagged_in_list(self):
        make_product("Legend", sale=0)
        response = self.client.get(reverse("inventory:product_list"))
        self.assertContains(response, "تعیین نشده")

    def test_create_product(self):
        response = self.client.post(
            reverse("inventory:product_create"),
            {
                "name": "Lalique",
                "stock_quantity": 8,
                "purchase_price": 0,
                "sale_price": 7500000,
            },
        )
        self.assertRedirects(response, reverse("inventory:product_list"))
        self.assertEqual(Product.objects.get().stock_quantity, 8)
        movement = StockMovement.objects.get()
        self.assertEqual(movement.quantity_change, 8)
        self.assertEqual(movement.stock_before, 0)
        self.assertEqual(movement.stock_after, 8)
        self.assertEqual(movement.reason, "ثبت موجودی اولیه")

    def test_stock_card_shows_and_filters_movements(self):
        legend = make_product("Legend", stock=5)
        hawas = make_product("Hawas", stock=7)
        StockMovement.objects.create(
            product=legend,
            product_name=legend.name,
            quantity_change=3,
            stock_before=2,
            stock_after=5,
            reason="ثبت فاکتور خرید",
            reference="فاکتور خرید شماره ۱",
        )
        StockMovement.objects.create(
            product=hawas,
            product_name=hawas.name,
            quantity_change=-1,
            stock_before=8,
            stock_after=7,
            reason="ثبت فروش",
        )

        response = self.client.get(
            reverse("inventory:stock_movement_list"), {"product": legend.pk}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["movements"]), [StockMovement.objects.get(product=legend)])
        self.assertContains(response, "فاکتور خرید شماره ۱")
        self.assertNotContains(response, "ثبت فروش")

    def test_stock_card_requires_inventory_view_permission(self):
        self.client.force_login(make_user())
        response = self.client.get(reverse("inventory:stock_movement_list"))
        self.assertEqual(response.status_code, 403)

    def test_create_rejects_duplicate_name(self):
        make_product("Legend")
        response = self.client.post(
            reverse("inventory:product_create"),
            {
                "name": "legend",
                "stock_quantity": 1,
                "purchase_price": 0,
                "sale_price": 0,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "قبلاً ثبت شده")
        self.assertEqual(Product.objects.count(), 1)

    def test_update_changes_sale_price_but_not_stock_or_purchase_price(self):
        product = make_product(stock=5, buy=300, sale=100)
        response = self.client.post(
            reverse("inventory:product_update", args=[product.pk]),
            {
                "name": "Legend",
                "stock_quantity": 999,
                "purchase_price": 50,
                "sale_price": 200,
            },
        )
        self.assertRedirects(response, reverse("inventory:product_list"))
        product.refresh_from_db()
        self.assertEqual(product.sale_price, 200)
        self.assertEqual(product.stock_quantity, 5)
        self.assertEqual(product.purchase_price, 300)

    def test_update_allows_keeping_same_name(self):
        product = make_product("Legend")
        response = self.client.post(
            reverse("inventory:product_update", args=[product.pk]),
            {"name": "Legend", "purchase_price": 1, "sale_price": 2},
        )
        self.assertRedirects(response, reverse("inventory:product_list"))

    def test_delete_confirmation_page(self):
        product = make_product("Legend")
        response = self.client.get(reverse("inventory:product_delete", args=[product.pk]))
        self.assertContains(response, "Legend")
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())

    def test_delete_removes_row_from_database(self):
        product = make_product("Legend")
        response = self.client.post(reverse("inventory:product_delete", args=[product.pk]))
        self.assertRedirects(response, reverse("inventory:product_list"))
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())
        self.assertEqual(Product.objects.count(), 0)

    def test_delete_unknown_product_is_404(self):
        response = self.client.post(reverse("inventory:product_delete", args=[12345]))
        self.assertEqual(response.status_code, 404)

    def test_pagination(self):
        for i in range(25):
            make_product(f"Item {i:02d}")
        response = self.client.get(reverse("inventory:product_list"))
        self.assertEqual(len(response.context["products"]), 20)
        response = self.client.get(reverse("inventory:product_list") + "?page=2")
        self.assertEqual(len(response.context["products"]), 5)
