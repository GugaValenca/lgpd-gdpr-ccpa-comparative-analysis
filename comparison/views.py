from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from .forms import ScenarioForm
from .models import Category, Law
from .pdf import render_scenario_pdf
from .services import build_summary_context

SESSION_KEY = "scenario_answers"


class ComparisonView(View):
    """
    The main comparison page: every category, with each law's entry,
    plus a keyword search box. Search runs server-side (so the page works
    without JavaScript) and static/comparison/js/filter.js layers instant
    client-side category filtering on top for a snappier feel.
    """

    template_name = "comparison/home.html"

    def get(self, request):
        query = request.GET.get("q", "").strip()

        categories = Category.objects.prefetch_related("entries__law")
        if query:
            categories = categories.filter(
                Q(name__icontains=query)
                | Q(entries__summary__icontains=query)
                | Q(entries__details__icontains=query)
            ).distinct()

        context = {
            "categories": categories,
            "laws": Law.objects.all(),
            "query": query,
        }
        return render(request, self.template_name, context)


class AboutView(TemplateView):
    template_name = "comparison/about.html"


class ScenarioFormView(View):
    template_name = "comparison/scenario_form.html"

    def get(self, request):
        form = ScenarioForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        form = ScenarioForm(request.POST)
        if form.is_valid():
            request.session[SESSION_KEY] = {
                "flags": list(form.get_answered_flags()),
                "company_name": form.cleaned_data["company_name"],
            }
            return redirect(reverse("comparison:scenario_result"))
        return render(request, self.template_name, {"form": form})


class ScenarioResultView(View):
    template_name = "comparison/scenario_result.html"

    def get(self, request):
        data = request.session.get(SESSION_KEY)
        if not data:
            return HttpResponseRedirect(reverse("comparison:scenario_form"))

        context = build_summary_context(data["flags"], data.get("company_name", ""))
        return render(request, self.template_name, context)


def scenario_pdf(request):
    """Regenerate the same summary from session data and stream it as a PDF."""
    data = request.session.get(SESSION_KEY)
    if not data:
        return HttpResponseRedirect(reverse("comparison:scenario_form"))

    context = build_summary_context(data["flags"], data.get("company_name", ""))
    pdf_bytes = render_scenario_pdf(context)

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="compliance-summary.pdf"'
    return response
