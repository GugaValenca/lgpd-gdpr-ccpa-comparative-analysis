from django.contrib import admin
from django_ratelimit.decorators import ratelimit

from .models import Category, ComparisonEntry, Law, ScenarioQuestion, ScenarioRule
from .throttling import client_ip


@admin.register(Law)
class LawAdmin(admin.ModelAdmin):
    list_display = ("code", "full_name", "jurisdiction", "effective_date", "order")
    list_editable = ("order",)
    ordering = ("order",)
    search_fields = ("code", "full_name")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order")
    list_editable = ("order",)
    prepopulated_fields = {"slug": ("name",)}  # noqa: RUF012 - ModelAdmin expects a dict
    ordering = ("order",)
    search_fields = ("name",)


class ScenarioRuleInline(admin.TabularInline):
    model = ScenarioRule
    extra = 1


@admin.register(ComparisonEntry)
class ComparisonEntryAdmin(admin.ModelAdmin):
    list_display = ("category", "law", "summary", "is_verified")
    list_filter = ("law", "category", "is_verified")
    list_editable = ("summary",)
    search_fields = ("summary", "details", "category__name")
    autocomplete_fields = ("category", "law")


@admin.register(ScenarioQuestion)
class ScenarioQuestionAdmin(admin.ModelAdmin):
    list_display = ("flag", "question_text", "order")
    list_editable = ("order",)
    ordering = ("order",)
    inlines = (ScenarioRuleInline,)


admin.site.site_header = "LGPD / GDPR / CCPA Comparative Analysis — Admin"
admin.site.site_title = "Privacy Law Comparison Admin"
admin.site.index_title = "Content management"

# The login form is the one publicly reachable, unauthenticated endpoint in
# this app, so it's the one worth rate limiting against brute force. Wraps
# the existing admin site's bound login method directly (rather than
# swapping in a new AdminSite instance) so every @admin.register() call
# above keeps registering against the same site that urls.py serves.
admin.site.login = ratelimit(  # type: ignore[method-assign]
    key=client_ip, rate="5/m", method="POST", block=True
)(admin.site.login)
