from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class AccountsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("sina", password="pass12345")

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
            reverse("login"), {"username": "sina", "password": "pass12345"}
        )
        self.assertRedirects(response, reverse("dashboard"))

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
