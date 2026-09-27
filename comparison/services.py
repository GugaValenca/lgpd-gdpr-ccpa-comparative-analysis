"""
Business logic for the "Generate compliance summary" feature, kept out of
views.py so it can be unit-tested and reused by both the HTML result page
and the PDF export.

How applicability is decided
-----------------------------
Each Law has a set of ScenarioRule rows, split into two groups:

  - "required_for_all" rules: ALL of them must be answered Yes (AND group).
    Used for compound thresholds, e.g. CCPA/CPRA requires "does business in
    California" as a baseline condition.
  - the remaining rules: ANY one of them being Yes is enough (OR group).
    Used for simple triggers (e.g. GDPR's extraterritorial scope) and for
    "meets at least one applicability threshold" style conditions.

A law is considered "applies" when the AND group (if any) is fully
satisfied AND the OR group (if any) has at least one Yes. A group that has
no rules defined is treated as vacuously satisfied, so a law backed only
by OR rules (e.g. GDPR: "yes" to the single extraterritoriality question
is enough) still works correctly.

This mirrors, at a structural level, well-established public facts about
how each law's applicability works (see seed_data.py), without hardcoding
any law-specific logic here — the categorization lives entirely in the
ScenarioRule data.
"""

from dataclasses import dataclass, field

from .models import ComparisonEntry, Law

# Categories pulled into the compliance summary, in the order they should
# appear. Matched by slug so this stays correct even if seed data changes.
SUMMARY_CATEGORY_SLUGS = [
    "data-subject-rights",
    "compliance-obligations-dpo-dpia-records",
    "enforcement-penalties",
    "private-right-of-action",
]


@dataclass
class LawResult:
    law: Law
    applies: bool
    matched_questions: list = field(default_factory=list)


def evaluate_scenario(answered_flags):
    """
    answered_flags: set/list of ScenarioQuestion.flag strings the user
    answered "Yes" to.

    Returns a list of LawResult, one per Law, ordered like Law.Meta.ordering.
    """
    answered_flags = set(answered_flags)
    results = []

    for law in Law.objects.prefetch_related("scenario_rules__question").all():
        rules = list(law.scenario_rules.all())
        required_rules = [r for r in rules if r.required_for_all]
        optional_rules = [r for r in rules if not r.required_for_all]

        required_ok = (
            all(r.question.flag in answered_flags for r in required_rules)
            if required_rules
            else True
        )
        optional_ok = (
            any(r.question.flag in answered_flags for r in optional_rules)
            if optional_rules
            else True
        )

        applies = bool(rules) and required_ok and optional_ok

        matched = [r.question.question_text for r in rules if r.question.flag in answered_flags]
        results.append(LawResult(law=law, applies=applies, matched_questions=matched))

    return results


def get_obligations_for_law(law):
    """
    Return the ComparisonEntry rows for `law` across the categories that
    matter for a compliance summary (rights, obligations, enforcement,
    private right of action), in display order.
    """
    return (
        ComparisonEntry.objects.filter(law=law, category__slug__in=SUMMARY_CATEGORY_SLUGS)
        .select_related("category")
        .order_by("category__order")
    )


def build_summary_context(answered_flags, company_name=""):
    """
    Full context used by both the HTML result page and the PDF generator.
    """
    results = evaluate_scenario(answered_flags)
    applicable = [r for r in results if r.applies]
    not_applicable = [r for r in results if not r.applies]

    sections = []
    for result in applicable:
        sections.append(
            {
                "law": result.law,
                "matched_questions": result.matched_questions,
                "obligations": get_obligations_for_law(result.law),
            }
        )

    return {
        "company_name": company_name,
        "results": results,
        "applicable": applicable,
        "not_applicable": not_applicable,
        "sections": sections,
        "has_unverified_content": any(
            entry.is_verified is False
            for section in sections
            for entry in section["obligations"]
        ),
    }
