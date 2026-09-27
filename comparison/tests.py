"""
Lightweight smoke tests: enough to catch broken views/templates/PDF
generation without over-engineering the test suite.
"""

from django.apps import apps
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse

from .models import Law
from .services import evaluate_scenario


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
