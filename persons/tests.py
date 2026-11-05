from decimal import Decimal
import jdatetime
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import RequestFactory, TestCase
from django.urls import reverse

from .admin import PersonAdmin
from .forms import PersonFilterForm, PersonForm
from .models import Person


class PersonFormTests(TestCase):
    def test_create_person_with_jalali_date_and_optional_phone(self):
        form = PersonForm(
            data={
                "date": "۱۴۰۵/۰۸/۱۲",
                "debtor_name": "علی رضایی",
                "phone_number": "09123456789",
                "product_name": "لپ‌تاپ",
                "debt_amount": "25000000",
                "paid_amount": "0",
                "status": Person.AccountStatus.DEBTOR,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        person = form.save()
        self.assertEqual(person.date, jdatetime.date(1405, 8, 12).togregorian())
        self.assertEqual(person.debtor_name, "علی رضایی")
        self.assertEqual(person.phone_number, "09123456789")
        self.assertEqual(person.product_name, "لپ‌تاپ")
        self.assertEqual(person.debt_amount, 25000000)
        self.assertEqual(person.paid_amount, 0)
        self.assertEqual(person.remaining_debt, 25000000)
        self.assertEqual(person.status, Person.AccountStatus.DEBTOR)

    def test_phone_number_is_optional(self):
        form = PersonForm(
            data={
                "date": "۱۴۰۵/۰۸/۱۲",
                "debtor_name": "سارا محمدی",
                "phone_number": "",
                "product_name": "ماوس",
                "debt_amount": "500000",
                "paid_amount": "0",
                "status": Person.AccountStatus.DEBTOR,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        person = form.save()
        self.assertEqual(person.phone_number, "")

    def test_partial_payment_updates_remaining_debt(self):
        person = Person.objects.create(
            date="2026-11-03",
            debtor_name="محمد حسینی",
            product_name="مانیتور",
            debt_amount=10000000,
            paid_amount=2000000,
            status=Person.AccountStatus.DEBTOR,
        )
        self.assertEqual(person.remaining_debt, 8000000)

        # Submit new partial payment of 3,000,000
        form = PersonForm(
            data={
                "date": "۱۴۰۵/۰۸/۱۲",
                "debtor_name": person.debtor_name,
                "phone_number": "",
                "product_name": person.product_name,
                "debt_amount": "10000000",
                "paid_amount": "2000000",
                "payment_amount": "3000000",
                "status": Person.AccountStatus.DEBTOR,
            },
            instance=person,
        )
        self.assertTrue(form.is_valid(), form.errors)
        updated = form.save()
        self.assertEqual(updated.paid_amount, 5000000)
        self.assertEqual(updated.remaining_debt, 5000000)
        self.assertEqual(updated.status, Person.AccountStatus.DEBTOR)

    def test_full_payment_automatically_settles_status(self):
        person = Person.objects.create(
            date="2026-11-03",
            debtor_name="رضا مرادی",
            product_name="کیبورد",
            debt_amount=4000000,
            paid_amount=1000000,
            status=Person.AccountStatus.DEBTOR,
        )

        form = PersonForm(
            data={
                "date": "۱۴۰۵/۰۸/۱۲",
                "debtor_name": person.debtor_name,
                "phone_number": "",
                "product_name": person.product_name,
                "debt_amount": "4000000",
                "paid_amount": "1000000",
                "payment_amount": "3000000",
                "status": Person.AccountStatus.DEBTOR,
            },
            instance=person,
        )
        self.assertTrue(form.is_valid(), form.errors)
        updated = form.save()
        self.assertEqual(updated.paid_amount, 4000000)
        self.assertEqual(updated.remaining_debt, 0)
        self.assertEqual(updated.status, Person.AccountStatus.SETTLED)

    def test_creditor_status(self):
        form = PersonForm(
            data={
                "date": "۱۴۰۵/۰۸/۱۲",
                "debtor_name": "احمد قاسمی",
                "phone_number": "09121111111",
                "product_name": "اسپیکر",
                "debt_amount": "0",
                "paid_amount": "0",
                "status": Person.AccountStatus.CREDITOR,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        person = form.save()
        self.assertEqual(person.status, Person.AccountStatus.CREDITOR)


class PersonViewsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="person-user", password="pwd")
        self.user.user_permissions.add(
            Permission.objects.get(content_type__app_label="persons", codename="view_person"),
            Permission.objects.get(content_type__app_label="persons", codename="add_person"),
            Permission.objects.get(content_type__app_label="persons", codename="change_person"),
            Permission.objects.get(content_type__app_label="persons", codename="delete_person"),
        )
        self.client.force_login(self.user)

    def test_person_list_renders(self):
        p1 = Person.objects.create(
            date="2026-11-03",
            debtor_name="علی علوی",
            product_name="کالای ۱",
            debt_amount=10000,
            status=Person.AccountStatus.DEBTOR,
        )
        response = self.client.get(reverse("persons:person_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "علی علوی")
        self.assertContains(response, "کالای ۱")

    def test_filter_by_debtor_name_and_status_and_date(self):
        p_debtor = Person.objects.create(
            date="2026-11-03",
            debtor_name="حسین کاظمی",
            product_name="پاوربانک",
            debt_amount=50000,
            status=Person.AccountStatus.DEBTOR,
        )
        p_settled = Person.objects.create(
            date="2026-11-03",
            debtor_name="حسین نوری",
            product_name="کابل",
            debt_amount=20000,
            status=Person.AccountStatus.SETTLED,
        )
        p_other_date = Person.objects.create(
            date="2026-11-02",
            debtor_name="حسین کاظمی",
            product_name="هندزفری",
            debt_amount=10000,
            status=Person.AccountStatus.DEBTOR,
        )

        # Filter by debtor_name
        res1 = self.client.get(reverse("persons:person_list"), {"q": "کاظمی"})
        self.assertIn(p_debtor, res1.context["persons"])
        self.assertIn(p_other_date, res1.context["persons"])
        self.assertNotIn(p_settled, res1.context["persons"])

        # Filter by status
        res2 = self.client.get(reverse("persons:person_list"), {"status": "settled"})
        self.assertIn(p_settled, res2.context["persons"])
        self.assertNotIn(p_debtor, res2.context["persons"])

        # Filter by date (1405-08-12 corresponds to 2026-11-03)
        res3 = self.client.get(reverse("persons:person_list"), {"date": "1405-08-12"})
        self.assertIn(p_debtor, res3.context["persons"])
        self.assertIn(p_settled, res3.context["persons"])
        self.assertNotIn(p_other_date, res3.context["persons"])

    def test_create_person_view(self):
        response = self.client.post(
            reverse("persons:person_create"),
            {
                "date": "1405-08-12",
                "debtor_name": "مریم احمدی",
                "phone_number": "09191234567",
                "product_name": "مودم",
                "debt_amount": "1500000",
                "paid_amount": "500000",
                "status": Person.AccountStatus.DEBTOR,
            },
        )
        self.assertRedirects(response, reverse("persons:person_list"))
        self.assertEqual(Person.objects.count(), 1)
        person = Person.objects.first()
        self.assertEqual(person.debtor_name, "مریم احمدی")
        self.assertEqual(person.remaining_debt, 1000000)

    def test_edit_person_with_partial_payment(self):
        person = Person.objects.create(
            date="2026-11-03",
            debtor_name="جعفر صادقی",
            product_name="فلش",
            debt_amount=600000,
            paid_amount=100000,
            status=Person.AccountStatus.DEBTOR,
        )

        response = self.client.post(
            reverse("persons:person_update", args=[person.pk]),
            {
                "date": "1405-08-12",
                "debtor_name": "جعفر صادقی",
                "phone_number": "",
                "product_name": "فلش",
                "debt_amount": "600000",
                "paid_amount": "100000",
                "payment_amount": "200000",
                "status": Person.AccountStatus.DEBTOR,
            },
        )
        self.assertRedirects(response, reverse("persons:person_list"))
        person.refresh_from_db()
        self.assertEqual(person.paid_amount, 300000)
        self.assertEqual(person.remaining_debt, 300000)

    def test_settle_person_view(self):
        person = Person.objects.create(
            date="2026-11-03",
            debtor_name="سعید عباسی",
            product_name="هارد",
            debt_amount=2000000,
            paid_amount=0,
            status=Person.AccountStatus.DEBTOR,
        )
        response = self.client.post(reverse("persons:person_settle", args=[person.pk]))
        self.assertRedirects(response, reverse("persons:person_list"))
        person.refresh_from_db()
        self.assertEqual(person.status, Person.AccountStatus.SETTLED)
        self.assertEqual(person.paid_amount, 2000000)
        self.assertEqual(person.remaining_debt, 0)

    def test_delete_person_view(self):
        person = Person.objects.create(
            date="2026-11-03",
            debtor_name="شخص حذفی",
            product_name="تست",
            debt_amount=100,
            status=Person.AccountStatus.DEBTOR,
        )
        response = self.client.post(reverse("persons:person_delete", args=[person.pk]))
        self.assertRedirects(response, reverse("persons:person_list"))
        self.assertFalse(Person.objects.filter(pk=person.pk).exists())


class PersonAdminTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="admin-persons", password="pwd", email="admin@persons.com"
        )
        self.person = Person.objects.create(
            date="2026-11-03",
            debtor_name="ادمین بدهکار",
            product_name="محصول ادمین",
            debt_amount=500000,
            paid_amount=100000,
            status=Person.AccountStatus.DEBTOR,
        )

    def test_admin_permissions_and_fields(self):
        from django.contrib.admin.sites import site

        rf = RequestFactory()
        req = rf.get("/")
        req.user = self.admin

        model_admin = PersonAdmin(Person, site)
        self.assertTrue(model_admin.has_add_permission(req))
        self.assertTrue(model_admin.has_change_permission(req, self.person))
        self.assertTrue(model_admin.has_delete_permission(req, self.person))
        self.assertEqual(
            model_admin.get_readonly_fields(req, self.person),
            ("created_at", "updated_at"),
        )
        self.assertEqual(model_admin.debt_amount_display(self.person), "500,000")
        self.assertEqual(model_admin.paid_amount_display(self.person), "100,000")
        self.assertEqual(model_admin.remaining_debt_display(self.person), "400,000")
