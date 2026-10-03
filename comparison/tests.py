"""
Lightweight smoke tests: enough to catch broken views/templates/PDF
generation without over-engineering the test suite.
"""

from django.apps import apps
from django.core.cache import cache
from django.core.management import call_command
from django.test import Client
from django.test import TestCase as DjangoTestCase
from django.urls import reverse

from .models import Law
from .services import evaluate_scenario
from .throttling import client_ip


class TestCase(DjangoTestCase):
    """Clears the cache before every test: the rate limiter counts requests
    there, and the suite as a whole makes more POSTs than one visitor may
    per minute."""

    def setUp(self):
        super().setUp()
        cache.clear()


class SeedDataTests(TestCase):
    def setUp(self):
        call_command("seed_data")

    def test_seed_creates_three_laws(self):
        self.assertEqual(Law.objects.count(), 3)

    def test_seed_is_idempotent(self):
        call_command("seed_data")
        self.assertEqual(Law.objects.count(), 3)

    def test_seeded_values_fit_their_column_limits(self):
        # SQLite doesn't enforce max_length but Postgres does, so an
        # over-long seed value passes locally and only fails once deployed.
        too_long = []
        for model in apps.get_app_config("comparison").get_models():
            for field in model._meta.concrete_fields:
                limit = getattr(field, "max_length", None)
                if not limit or field.get_internal_type() == "TextField":
                    continue
                for obj in model.objects.all():
                    value = getattr(obj, field.name) or ""
                    if len(str(value)) > limit:
                        too_long.append(f"{model.__name__}.{field.name} pk={obj.pk}")
        self.assertEqual(too_long, [])


class ViewTests(TestCase):
    def setUp(self):
        call_command("seed_data")
        self.client = Client()

    def test_home_page_loads(self):
        response = self.client.get(reverse("comparison:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "LGPD")
        self.assertContains(response, "GDPR")

    def test_home_page_search(self):
        response = self.client.get(reverse("comparison:home"), {"q": "consent"})
        self.assertEqual(response.status_code, 200)

    def test_about_page_loads(self):
        response = self.client.get(reverse("comparison:about"))
        self.assertEqual(response.status_code, 200)

    def test_scenario_form_loads(self):
        response = self.client.get(reverse("comparison:scenario_form"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "EU/EEA")

    def test_scenario_submit_and_result(self):
        data = {
            "company_name": "Test Co",
            "q_process_eu_data": "yes",
            "q_process_br_data": "no",
            "q_does_business_in_ca": "no",
            "q_ca_revenue_threshold": "no",
            "q_ca_data_volume_threshold": "no",
            "q_ca_revenue_from_sale_threshold": "no",
            "q_processes_sensitive_data": "no",
        }
        response = self.client.post(reverse("comparison:scenario_form"), data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "GDPR")

    def test_scenario_pdf_download(self):
        data = {
            "company_name": "Test Co",
            "q_process_eu_data": "yes",
            "q_process_br_data": "yes",
            "q_does_business_in_ca": "yes",
            "q_ca_revenue_threshold": "yes",
            "q_ca_data_volume_threshold": "no",
            "q_ca_revenue_from_sale_threshold": "no",
            "q_processes_sensitive_data": "yes",
        }
        self.client.post(reverse("comparison:scenario_form"), data)
        response = self.client.get(reverse("comparison:scenario_pdf"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_scenario_pdf_rejects_markup_injection_in_company_name(self):
        # `company_name` is free text from an anonymous public form and gets
        # interpolated into a ReportLab Paragraph, which parses a small
        # HTML/XML-like markup language. An unescaped value here used to
        # either inject formatting into the PDF or crash with an unhandled
        # ValueError on an unclosed tag (a 500 from a single bad input).
        data = {
            "company_name": "Acme <font size=40 color='red'>PWNED</font> & <unclosed",
            "q_process_eu_data": "yes",
            "q_process_br_data": "no",
            "q_does_business_in_ca": "no",
            "q_ca_revenue_threshold": "no",
            "q_ca_data_volume_threshold": "no",
            "q_ca_revenue_from_sale_threshold": "no",
            "q_processes_sensitive_data": "no",
        }
        self.client.post(reverse("comparison:scenario_form"), data)
        response = self.client.get(reverse("comparison:scenario_pdf"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b"%PDF"))


class ScenarioLogicTests(TestCase):
    def setUp(self):
        call_command("seed_data")

    def test_gdpr_triggered_alone(self):
        results = evaluate_scenario({"process_eu_data"})
        applicable_codes = {r.law.code for r in results if r.applies}
        self.assertIn("GDPR", applicable_codes)
        self.assertNotIn("LGPD", applicable_codes)
        self.assertNotIn("CCPA/CPRA", applicable_codes)

    def test_ccpa_requires_baseline_and_a_threshold(self):
        # Baseline alone, no threshold met -> should NOT apply.
        results = evaluate_scenario({"does_business_in_ca"})
        ccpa = next(r for r in results if r.law.code == "CCPA/CPRA")
        self.assertFalse(ccpa.applies)

        # Baseline + one threshold -> should apply.
        results = evaluate_scenario({"does_business_in_ca", "ca_revenue_threshold"})
        ccpa = next(r for r in results if r.law.code == "CCPA/CPRA")
        self.assertTrue(ccpa.applies)

    def test_no_answers_triggers_nothing(self):
        results = evaluate_scenario(set())
        self.assertTrue(all(not r.applies for r in results))


def _scenario_post_data(**overrides):
    data = {
        "company_name": "Test Co",
        "q_process_eu_data": "no",
        "q_process_br_data": "no",
        "q_does_business_in_ca": "no",
        "q_ca_revenue_threshold": "no",
        "q_ca_data_volume_threshold": "no",
        "q_ca_revenue_from_sale_threshold": "no",
        "q_processes_sensitive_data": "no",
    }
    data.update(overrides)
    return data


class RateLimitTests(TestCase):
    def setUp(self):
        super().setUp()
        call_command("seed_data")

    def test_scenario_form_submissions_are_limited_per_visitor(self):
        url = reverse("comparison:scenario_form")
        statuses = [self.client.post(url, _scenario_post_data()).status_code for _ in range(31)]
        self.assertEqual(statuses[:30], [302] * 30)
        self.assertEqual(statuses[30], 403)

    def test_pdf_exports_are_limited_per_visitor(self):
        self.client.post(reverse("comparison:scenario_form"), _scenario_post_data())
        url = reverse("comparison:scenario_pdf")
        statuses = [self.client.get(url).status_code for _ in range(11)]
        self.assertEqual(statuses[:10], [200] * 10)
        self.assertEqual(statuses[10], 403)


class AdminLoginRateLimitTests(TestCase):
    def test_admin_login_attempts_are_limited_per_visitor(self):
        url = reverse("admin:login")
        data = {"username": "nobody", "password": "wrong"}
        statuses = [self.client.post(url, data).status_code for _ in range(6)]
        self.assertEqual(statuses[:5], [200] * 5)
        self.assertEqual(statuses[5], 403)


class ClientIpTests(TestCase):
    """The rate-limit key trusts X-Real-IP only where the platform
    guarantees it (Vercel); elsewhere it could be forged to dodge limits."""

    def request(self, **meta):
        from django.test import RequestFactory

        return RequestFactory().get("/", REMOTE_ADDR="10.0.0.1", **meta)

    def test_header_is_ignored_off_vercel(self):
        with self.settings(RUNNING_ON_VERCEL=False):
            self.assertEqual(client_ip("g", self.request(HTTP_X_REAL_IP="1.2.3.4")), "10.0.0.1")

    def test_header_is_used_on_vercel(self):
        with self.settings(RUNNING_ON_VERCEL=True):
            self.assertEqual(client_ip("g", self.request(HTTP_X_REAL_IP="1.2.3.4")), "1.2.3.4")

    def test_falls_back_to_remote_addr_on_vercel_without_header(self):
        with self.settings(RUNNING_ON_VERCEL=True):
            self.assertEqual(client_ip("g", self.request()), "10.0.0.1")


class SecurityHeaderTests(TestCase):
    def test_pages_send_a_strict_content_security_policy(self):
        response = self.client.get(reverse("comparison:about"))
        policy = response["Content-Security-Policy"]
        self.assertIn("default-src 'self'", policy)
        self.assertIn("frame-ancestors 'none'", policy)
        self.assertNotIn("unsafe-inline", policy)
        self.assertEqual(response["X-Frame-Options"], "DENY")
