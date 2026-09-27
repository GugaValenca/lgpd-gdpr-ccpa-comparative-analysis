from django.contrib import admin

from .models import Category, ComparisonEntry, Law, ScenarioQuestion, ScenarioRule


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
