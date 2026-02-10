from django.contrib import admin
from .models import GovernmentScheme, InsurancePolicy, Application, Eligibility

@admin.register(GovernmentScheme)
class GovernmentSchemeAdmin(admin.ModelAdmin):
    list_display = ['name', 'scheme_type', 'state', 'is_active', 'coverage_amount']
    list_filter = ['scheme_type', 'state', 'is_active']
    search_fields = ['name', 'description']

@admin.register(InsurancePolicy)
class InsurancePolicyAdmin(admin.ModelAdmin):
    list_display = ['name', 'policy_type', 'premium_per_month', 'coverage_amount', 'is_active']
    list_filter = ['policy_type', 'is_active']
    search_fields = ['name', 'description']

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['application_id', 'user', 'scheme', 'policy', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['application_id', 'user__email']
    readonly_fields = ['application_id', 'created_at', 'updated_at']

@admin.register(Eligibility)
class EligibilityAdmin(admin.ModelAdmin):
    list_display = ['scheme', 'min_age', 'max_age', 'max_income', 'state']
    list_filter = ['state']
    search_fields = ['scheme__name']
