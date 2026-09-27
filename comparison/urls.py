from django.urls import path

from . import views

app_name = "comparison"

urlpatterns = [
    path("", views.ComparisonView.as_view(), name="home"),
    path("about/", views.AboutView.as_view(), name="about"),
    path("compliance-summary/", views.ScenarioFormView.as_view(), name="scenario_form"),
    path(
        "compliance-summary/result/", views.ScenarioResultView.as_view(), name="scenario_result"
    ),
    path("compliance-summary/pdf/", views.scenario_pdf, name="scenario_pdf"),
]
