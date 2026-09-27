"""
Forms for the "Generate compliance summary" feature.

ScenarioForm is built dynamically from the ScenarioQuestion table rather
than hardcoded, so new questions can be added from the Django admin
without a code change or migration.
"""

from django import forms

from .models import ScenarioQuestion

YES_NO_CHOICES = (
    ("yes", "Yes"),
    ("no", "No"),
)


class ScenarioForm(forms.Form):
    """
    A form with:
      - an optional business/company name (used only for the PDF header)
      - one Yes/No radio field per active ScenarioQuestion, added dynamically
        in __init__ so the question set can grow without code changes.
    """

    company_name = forms.CharField(
        label="Business or product name (optional)",
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Acme SaaS Inc."}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for question in ScenarioQuestion.objects.all():
            field_name = f"q_{question.flag}"
            self.fields[field_name] = forms.ChoiceField(
                label=question.question_text,
                help_text=question.help_text,
                choices=YES_NO_CHOICES,
                widget=forms.RadioSelect,
                initial="no",
                required=True,
            )

    def get_answered_flags(self):
        """Return the set of question flags the user answered 'yes'."""
        flags = set()
        for question in ScenarioQuestion.objects.all():
            field_name = f"q_{question.flag}"
            if self.cleaned_data.get(field_name) == "yes":
                flags.add(question.flag)
        return flags
