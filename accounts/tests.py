from django.contrib.admin.sites import site
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from accounts.models import UserProfile, sync_user_role_permissions


class AccountsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("sina", password="pass12345")
        self.user.profile.role = UserProfile.ROLE_SELLER
        self.user.profile.save()

    def test_root_redirects_to_dashboard(self):
        response = self.client.get("/")
        self.assertRedirects(
            response, reverse("dashboard"), fetch_redirect_response=False
        )

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_login_success_goes_to_dashboard(self):
        response = self.client.post(
            reverse("login"),
            {"username": "sina", "password": "pass12345"},
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(self.client.session.get("active_role"), "seller")

    def test_login_failure_shows_form_again(self):
        response = self.client.post(
            reverse("login"), {"username": "sina", "password": "wrong"}
        )
        self.assertEqual(response.status_code, 200)

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))

    def test_dashboard_renders_for_logged_in_user(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "داشبورد")


class RoleBasedAccessControlTests(TestCase):
    def setUp(self):
        self.seller_user = User.objects.create_user("seller1", password="password123")
        self.seller_user.profile.role = UserProfile.ROLE_SELLER
        self.seller_user.profile.save()
        sync_user_role_permissions(self.seller_user, UserProfile.ROLE_SELLER)

        self.manager_user = User.objects.create_user("manager1", password="password123")
        self.manager_user.profile.role = UserProfile.ROLE_MANAGER
        self.manager_user.profile.save()
        sync_user_role_permissions(self.manager_user, UserProfile.ROLE_MANAGER)

    def test_user_profile_creation_and_string(self):
        self.assertEqual(self.seller_user.profile.role, "seller")
        self.assertTrue(self.seller_user.profile.is_seller)
        self.assertFalse(self.seller_user.profile.is_manager)
        self.assertIn("seller1", str(self.seller_user.profile))
        self.assertIn("فروشنده", str(self.seller_user.profile))

        self.assertEqual(self.manager_user.profile.role, "manager")
        self.assertTrue(self.manager_user.profile.is_manager)
        self.assertFalse(self.manager_user.profile.is_seller)
        self.assertIn("manager1", str(self.manager_user.profile))
        self.assertIn("مدیر", str(self.manager_user.profile))

    def test_login_page_does_not_contain_role_selection(self):
        """
        صفحه لاگین نباید فیلد انتخاب نقش داشته باشد.
        """
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="role"')
        self.assertNotContains(response, "form-select")

    def test_seller_login_automatically_assigns_seller_role(self):
        """
        فروشنده با لاگین عادی بر اساس نقش تعریف‌شده در ادمین وارد می‌شود.
        """
        response = self.client.post(
            reverse("login"),
            {"username": "seller1", "password": "password123"},
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(self.client.session.get("active_role"), "seller")

    def test_manager_login_automatically_assigns_manager_role(self):
        """
        مدیر با لاگین عادی بر اساس نقش تعریف‌شده در ادمین وارد می‌شود.
        """
        response = self.client.post(
            reverse("login"),
            {"username": "manager1", "password": "password123"},
        )
        self.assertRedirects(response, reverse("dashboard"))
        self.assertEqual(self.client.session.get("active_role"), "manager")

    def test_seller_views_restrictions(self):
        """
        فروشنده نباید به فاکتورهای خرید، تامین‌کنندگان و سود و زیان دسترسی داشته باشد.
        اما باید به فاکتور فروش، اشخاص و کالا و انبار دسترسی داشته باشد.
        """
        self.client.force_login(self.seller_user)

        # Forbidden for seller (403):
        self.assertEqual(self.client.get(reverse("purchases:invoice_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("purchases:supplier_list")).status_code, 403)
        self.assertEqual(self.client.get(reverse("profit_loss:report")).status_code, 403)

        # Allowed for seller (200):
        self.assertEqual(self.client.get(reverse("sales_invoice:sale_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("persons:person_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("inventory:product_list")).status_code, 200)

    def test_manager_views_access(self):
        """
        مدیر به تمام بخش‌ها دسترسی دارد.
        """
        self.client.force_login(self.manager_user)
        self.assertEqual(self.client.get(reverse("purchases:invoice_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("purchases:supplier_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("profit_loss:report")).status_code, 200)
        self.assertEqual(self.client.get(reverse("sales_invoice:sale_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("persons:person_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("inventory:product_list")).status_code, 200)

    def test_dashboard_and_navbar_elements_for_seller(self):
        """
        منوی فروشنده نباید فاکتورهای خرید، تامین‌کنندگان و سود و زیان را نمایش دهد.
        """
        self.client.force_login(self.seller_user)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "فاکتور فروش")
        self.assertContains(response, "اشخاص")
        self.assertContains(response, "کالا و انبار")
        self.assertNotContains(response, "فاکتورهای خرید")
        self.assertNotContains(response, "تامین‌کنندگان")
        self.assertNotContains(response, "سود و زیان")
        self.assertContains(response, "فروشنده")

    def test_dashboard_and_navbar_elements_for_manager(self):
        """
        منوی مدیر تمامی موارد را نمایش می‌دهد.
        """
        self.client.force_login(self.manager_user)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "فاکتور فروش")
        self.assertContains(response, "اشخاص")
        self.assertContains(response, "کالا و انبار")
        self.assertContains(response, "فاکتورهای خرید")
        self.assertContains(response, "تامین‌کنندگان")
        self.assertContains(response, "سود و زیان")
        self.assertContains(response, "مدیر")

    def test_inventory_product_list_elements_for_seller_and_manager(self):
        """
        فروشنده در لیست انبار نباید قیمت خرید میانگین و ستون عملیات را ببیند.
        اما مدیر باید هر دو را ببیند.
        """
        from decimal import Decimal
        from inventory.models import Product

        Product.objects.create(
            name="عطر تست",
            stock_quantity=10,
            purchase_price=Decimal("1200000"),
            sale_price=Decimal("1800000"),
        )

        # بررسی برای نقش فروشنده
        self.client.force_login(self.seller_user)
        resp_seller = self.client.get(reverse("inventory:product_list"))
        self.assertEqual(resp_seller.status_code, 200)
        self.assertContains(resp_seller, "عطر تست")
        self.assertContains(resp_seller, "1,800,000")
        self.assertNotContains(resp_seller, "قیمت خرید (میانگین)")
        self.assertNotContains(resp_seller, "1,200,000")
        self.assertNotContains(resp_seller, "<th>عملیات</th>")
        self.assertNotContains(resp_seller, "افزودن محصول")

        # بررسی برای نقش مدیر
        self.client.force_login(self.manager_user)
        resp_manager = self.client.get(reverse("inventory:product_list"))
        self.assertEqual(resp_manager.status_code, 200)
        self.assertContains(resp_manager, "عطر تست")
        self.assertContains(resp_manager, "قیمت خرید (میانگین)")
        self.assertContains(resp_manager, "1,200,000")
        self.assertContains(resp_manager, "<th>عملیات</th>")
        self.assertContains(resp_manager, "افزودن محصول")

    def test_user_admin_registration(self):
        user_admin = site._registry[User]
        inline_models = [inline.model for inline in user_admin.inlines]
        self.assertIn(UserProfile, inline_models)

    def test_admin_can_add_user_with_manager_role(self):
        superuser = User.objects.create_superuser("admin_test", password="AdminPassword123!")
        self.client.force_login(superuser)
        post_data = {
            "username": "new_manager_user",
            "password1": "SecurePass12345!",
            "password2": "SecurePass12345!",
            "profile-TOTAL_FORMS": "1",
            "profile-INITIAL_FORMS": "0",
            "profile-MIN_NUM_FORMS": "0",
            "profile-MAX_NUM_FORMS": "1",
            "profile-0-role": "manager",
        }
        response = self.client.post(reverse("admin:auth_user_add"), post_data)
        self.assertEqual(response.status_code, 302)
        new_user = User.objects.get(username="new_manager_user")
        self.assertEqual(new_user.profile.role, "manager")
        self.assertTrue(new_user.is_staff)
        self.assertIn("مدیران", [g.name for g in new_user.groups.all()])

    def test_admin_can_add_user_with_seller_role(self):
        superuser = User.objects.create_superuser("admin_test2", password="AdminPassword123!")
        self.client.force_login(superuser)
        post_data = {
            "username": "new_seller_user",
            "password1": "SecurePass12345!",
            "password2": "SecurePass12345!",
            "profile-TOTAL_FORMS": "1",
            "profile-INITIAL_FORMS": "0",
            "profile-MIN_NUM_FORMS": "0",
            "profile-MAX_NUM_FORMS": "1",
            "profile-0-role": "seller",
        }
        response = self.client.post(reverse("admin:auth_user_add"), post_data)
        self.assertEqual(response.status_code, 302)
        new_user = User.objects.get(username="new_seller_user")
        self.assertEqual(new_user.profile.role, "seller")
        self.assertFalse(new_user.is_staff)
        self.assertIn("فروشندگان", [g.name for g in new_user.groups.all()])


class TemplateTagsTests(TestCase):
    def test_url_replace_updates_and_preserves_query_params(self):
        from django.template import Context, Template
        from django.test import RequestFactory

        rf = RequestFactory()
        request = rf.get('/test/?q=apple&page=1')
        t = Template('?{% url_replace page=2 %}')
        rendered = t.render(Context({'request': request}))
        self.assertEqual(rendered, '?q=apple&amp;page=2')

    def test_url_replace_removes_none_values(self):
        from django.template import Context, Template
        from django.test import RequestFactory

        rf = RequestFactory()
        request = rf.get('/test/?q=apple&page=1')
        t = Template('?{% url_replace page=None %}')
        rendered = t.render(Context({'request': request}))
        self.assertEqual(rendered, '?q=apple')
