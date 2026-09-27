"""
Data model for the LGPD / GDPR / CCPA comparative analysis tool.

Design notes for reviewers:
- `Law` holds the three frameworks being compared.
- `Category` holds the comparison dimensions (scope, rights, penalties, etc.).
- `ComparisonEntry` is the join table: one row per (Category, Law) pair,
  holding the actual legal content. This is what makes the comparison
  "queryable data" rather than a static document — new categories or laws
  can be added without touching templates or views.
- `ScenarioQuestion` / `ScenarioRule` back the "Generate compliance summary"
  feature: each question is a yes/no fact about a hypothetical business,
  and each rule says which Law a combination of answers triggers.
"""

from django.db import models
from django.utils.text import slugify


class Law(models.Model):
    """One of the three privacy law frameworks being compared."""

    code = models.CharField(
        max_length=10,
        unique=True,
        help_text="Short code used in badges/tables, e.g. LGPD, GDPR, CCPA/CPRA.",
    )
    full_name = models.CharField(
        max_length=255,
        help_text="Official full name of the law, e.g. 'Lei Geral de Proteção de Dados Pessoais (Lei nº 13.709/2018)'.",
    )
    jurisdiction = models.CharField(
        max_length=100,
        help_text="e.g. Brazil, European Union / EEA, California (USA).",
    )
    regulator = models.CharField(
        max_length=255,
        blank=True,
        help_text="Primary enforcement authority, e.g. 'ANPD', 'National Data Protection Authorities', 'CPPA / CA Attorney General'.",
    )
    effective_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the law (or its main enforcement provisions) took effect.",
    )
    official_source_url = models.URLField(
        blank=True,
        help_text="Link to the official statutory text (e.g. planalto.gov.br, eur-lex.europa.eu, oag.ca.gov).",
    )
    color_hex = models.CharField(
        max_length=7,
        default="#334155",
        help_text="Accent color used for this law's badge/column in the UI.",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Display order across the site (e.g. LGPD, GDPR, CCPA/CPRA).",
    )

    class Meta:
        ordering = ("order", "code")
        verbose_name = "Law"
        verbose_name_plural = "Laws"

    def __str__(self):
        return self.code


class Category(models.Model):
    """A comparison dimension, e.g. 'Scope & Extraterritoriality'."""

    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    description = models.TextField(
        blank=True,
        help_text="One or two sentences explaining what this category compares.",
    )
    icon = models.CharField(
        max_length=10,
        blank=True,
        help_text="Optional emoji used as a lightweight icon in the UI, e.g. '🌍'.",
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order", "name")
        verbose_name_plural = "Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ComparisonEntry(models.Model):
    """
    The actual legal content for one (Category, Law) pair.

    Kept deliberately as plain text fields (not rich text) so the content
    is easy to review, diff, and verify against primary sources in the
    Django admin — no hidden HTML formatting to trust.
    """

    category = models.ForeignKey(Category, related_name="entries", on_delete=models.CASCADE)
    law = models.ForeignKey(Law, related_name="entries", on_delete=models.CASCADE)

    summary = models.CharField(
        max_length=600,
        help_text="One- or two-sentence takeaway shown in the comparison table/cards.",
    )
    details = models.TextField(
        blank=True,
        help_text="Longer explanation shown when the entry is expanded.",
    )
    source_url = models.URLField(
        blank=True,
        help_text="Link to the specific primary-source provision backing this entry, if verified.",
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Check only after this entry has been personally verified against the official statutory text.",
    )
    verification_notes = models.TextField(
        blank=True,
        help_text="TODO/verification notes, e.g. 'TODO: VERIFY against official source (planalto.gov.br) before publishing.'",
    )

    class Meta:
        unique_together = ("category", "law")
        ordering = ("category__order", "law__order")
        verbose_name_plural = "Comparison entries"

    def __str__(self):
        return f"{self.category.name} — {self.law.code}"


class ScenarioQuestion(models.Model):
    """
    A yes/no question asked in the 'Generate compliance summary' form.

    Kept as data (not hardcoded form fields) so new questions can be added
    from the admin without a code change. `flag` is the short internal name
    referenced by ScenarioRule.condition_flags.
    """

    flag = models.SlugField(
        max_length=50,
        unique=True,
        help_text="Internal identifier referenced by scenario rules, e.g. 'process_eu_data'.",
    )
    question_text = models.CharField(max_length=300)
    help_text = models.CharField(max_length=300, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("order", "id")

    def __str__(self):
        return self.flag


class ScenarioRule(models.Model):
    """
    Maps a ScenarioQuestion flag being answered "Yes" to a Law being
    potentially triggered. Multiple rules for the same law are combined
    with OR by default, except rules marked `required_for_all` which must
    ALL be true (used for CCPA/CPRA-style compound thresholds).
    """

    law = models.ForeignKey(Law, related_name="scenario_rules", on_delete=models.CASCADE)
    question = models.ForeignKey(
        ScenarioQuestion, related_name="rules", on_delete=models.CASCADE
    )
    required_for_all = models.BooleanField(
        default=False,
        help_text=(
            "If checked, this question is part of an AND group: the law is only "
            "triggered if every 'required_for_all' rule for it is answered Yes. "
            "If unchecked, this question alone (OR) is enough to trigger the law."
        ),
    )

    class Meta:
        unique_together = ("law", "question")

    def __str__(self):
        return f"{self.law.code} <- {self.question.flag}"
