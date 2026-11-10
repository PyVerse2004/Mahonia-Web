from decimal import Decimal
import jdatetime
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from sales_invoice.models import Sale
from inventory.models import Product
from profit_loss.services import get_profit_loss_report


class ProfitLossReportTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="report-user", password="pwd")
        self.user.user_permissions.add(
            Permission.objects.get(content_type__app_label="sales_invoice", codename="view_sale"),
            Permission.objects.get(content_type__app_label="sales_invoice", codename="add_sale"),
        )
        self.client.force_login(self.user)

        # Create products with known purchase prices
        self.product_a = Product.objects.create(
            name="کالای الف",
            purchase_price=Decimal("10000"),
            sale_price=Decimal("15000"),
            stock_quantity=50,
        )
        self.product_b = Product.objects.create(
            name="کالای ب",
            purchase_price=Decimal("20000"),
            sale_price=Decimal("25000"),
            stock_quantity=50,
        )

    def test_historical_snapshot_preserves_purchase_price_when_product_price_changes(self):
        # Create a sale when product_a purchase price is 10,000
        sale = Sale.objects.create(
            date="2026-11-01",
            product=self.product_a,
            quantity=2,
            unit_price=Decimal("15000"),
        )
        self.assertEqual(sale.purchase_unit_price, Decimal("10000"))
        self.assertEqual(sale.total_amount, Decimal("30000"))
        self.assertEqual(sale.total_cost, Decimal("20000"))
        self.assertEqual(sale.profit, Decimal("10000"))
        self.assertEqual(sale.profit_margin_percent, Decimal("33.3"))

        # Later, the product's purchase price in inventory changes due to a new expensive purchase
        self.product_a.purchase_price = Decimal("22000")
        self.product_a.save()

        # Reload sale: its purchase_unit_price and profit must remain historically fixed!
        sale.refresh_from_db()
        self.assertEqual(sale.purchase_unit_price, Decimal("10000"))
        self.assertEqual(sale.total_cost, Decimal("20000"))
        self.assertEqual(sale.profit, Decimal("10000"))

    def test_summary_aggregates_calculation(self):
        # 1405-08-10 corresponds to 2026-11-01
        # Sale 1: 3 * 15,000 = 45,000 (cost: 3 * 10,000 = 30,000) -> profit = +15,000
        Sale.objects.create(
            date="2026-11-01",
            product=self.product_a,
            quantity=3,
            unit_price=Decimal("15000"),
            purchase_unit_price=Decimal("10000"),
        )
        # Sale 2: 2 * 30,000 = 60,000 (cost: 2 * 20,000 = 40,000) -> profit = +20,000
        Sale.objects.create(
            date="2026-11-02",
            product=self.product_b,
            quantity=2,
            unit_price=Decimal("30000"),
            purchase_unit_price=Decimal("20000"),
        )
        # Inactive sale (should be excluded!)
        Sale.objects.create(
            date="2026-11-02",
            product=self.product_a,
            quantity=10,
            unit_price=Decimal("100000"),
            purchase_unit_price=Decimal("10000"),
            is_active=False,
        )

        sales, summary = get_profit_loss_report()
        self.assertEqual(sales.count(), 2)
        self.assertEqual(summary["total_sales"], Decimal("105000"))
        self.assertEqual(summary["total_cost"], Decimal("70000"))
        self.assertEqual(summary["net_profit"], Decimal("35000"))
        self.assertTrue(summary["is_profitable"])
        # profit_margin: 35,000 / 105,000 * 100 = 33.3%
        self.assertEqual(summary["profit_margin"], Decimal("33.3"))
        self.assertEqual(summary["total_quantity"], 5)
        self.assertEqual(summary["total_invoices"], 2)

    def test_loss_scenario(self):
        # Sale below purchase price: 2 * 8,000 = 16,000 (cost: 2 * 10,000 = 20,000) -> loss = -4,000
        Sale.objects.create(
            date="2026-11-01",
            product=self.product_a,
            quantity=2,
            unit_price=Decimal("8000"),
            purchase_unit_price=Decimal("10000"),
        )
        sales, summary = get_profit_loss_report()
        self.assertEqual(summary["net_profit"], Decimal("-4000"))
        self.assertFalse(summary["is_profitable"])
        self.assertEqual(summary["profit_margin"], Decimal("-25.0"))

    def test_filter_by_jalali_year_and_month(self):
        # 1405-08-15 corresponds to 2026-11-05 (Month 8 of 1405)
        s1 = Sale.objects.create(
            date="2026-11-05",
            product=self.product_a,
            quantity=1,
            unit_price=Decimal("15000"),
            purchase_unit_price=Decimal("10000"),
        )
        # 1405-09-01 corresponds to 2026-11-22 (Month 9 of 1405)
        s2 = Sale.objects.create(
            date="2026-11-22",
            product=self.product_a,
            quantity=1,
            unit_price=Decimal("15000"),
            purchase_unit_price=Decimal("10000"),
        )
        # 1404-08-15 corresponds to 2025-11-06 (Year 1404)
        s3 = Sale.objects.create(
            date="2025-11-06",
            product=self.product_a,
            quantity=1,
            unit_price=Decimal("15000"),
            purchase_unit_price=Decimal("10000"),
        )

        # Filter year 1405 (all months): should contain s1 and s2, but not s3
        sales_1405, _ = get_profit_loss_report(year=1405)
        self.assertIn(s1, sales_1405)
        self.assertIn(s2, sales_1405)
        self.assertNotIn(s3, sales_1405)

        # Filter year 1405, month 8: should contain s1 only
        sales_m8, _ = get_profit_loss_report(year=1405, month=8)
        self.assertIn(s1, sales_m8)
        self.assertNotIn(s2, sales_m8)
        self.assertNotIn(s3, sales_m8)

        # Filter year 1404: should contain s3 only
        sales_1404, _ = get_profit_loss_report(year=1404)
        self.assertIn(s3, sales_1404)
        self.assertNotIn(s1, sales_1404)

    def test_view_renders_cards_and_table(self):
        Sale.objects.create(
            date="2026-11-01",
            product=self.product_a,
            quantity=2,
            unit_price=Decimal("15000"),
            purchase_unit_price=Decimal("10000"),
        )
        response = self.client.get(reverse("profit_loss:report"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "گزارش سود و زیان")
        self.assertContains(response, "جمع کل فروش")
        self.assertContains(response, "جمع بهای تمام‌شده خرید")
        self.assertContains(response, "سود خالص کل")
        self.assertContains(response, "کالای الف")
        self.assertContains(response, "30,000")
        self.assertContains(response, "10,000")
