from django.contrib import admin
from .models import CancerImageAnalysis
from .evidence_models import (
    EvidenceSource, RecommendationEvidence, EvidenceLink,
    EvidenceExplanationLog, RuleBasedReference
)
from .rule_based_references import RuleBasedReferenceManager


@admin.register(CancerImageAnalysis)
class CancerImageAnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'image_type', 'tumor_detected', 'tumor_type', 'tumor_stage', 'created_at')
    list_filter = ('image_type', 'tumor_detected', 'tumor_stage', 'created_at')
    search_fields = ('user__username', 'user__email', 'tumor_type', 'tumor_location')
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Image Information', {
            'fields': ('user', 'image', 'image_type', 'original_filename')
        }),
        ('Analysis Results', {
            'fields': (
                'tumor_detected', 'tumor_type', 'tumor_stage', 
                'tumor_size_mm', 'tumor_location',
                'detection_confidence', 'stage_confidence'
            )
        }),
        ('Advanced Analysis', {
            'fields': ('genetic_profile', 'comorbidities', 'analysis_data'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )


@admin.register(EvidenceSource)
class EvidenceSourceAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'source_type', 'evidence_strength', 'publication_year',
        'pmid', 'is_active', 'created_at'
    )
    list_filter = (
        'source_type', 'evidence_strength', 'is_active',
        'publication_year', 'created_at'
    )
    search_fields = ('title', 'authors', 'pmid', 'abstract')
    readonly_fields = ('id', 'created_at', 'updated_at', 'last_indexed')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Identification', {
            'fields': ('id', 'title', 'source_type', 'is_active')
        }),
        ('Author & Publication', {
            'fields': (
                'authors', 'publication_year', 'journal_or_organization',
                'doi', 'pmid'
            )
        }),
        ('Content', {
            'fields': ('abstract', 'key_findings', 'full_text'),
            'classes': ('collapse',)
        }),
        ('Evidence Strength', {
            'fields': ('evidence_strength', 'cancer_types', 'treatment_types', 'biomarkers')
        }),
        ('Guideline Information', {
            'fields': ('guideline_version', 'guideline_url'),
            'classes': ('collapse',)
        }),
        ('URLs', {
            'fields': ('pdf_url',),
            'classes': ('collapse',)
        }),
        ('Embeddings & Indexing', {
            'fields': ('embedding', 'last_indexed'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    actions = ['mark_active', 'mark_inactive', 'reindex_embeddings']
    
    def mark_active(self, request, queryset):
        queryset.update(is_active=True)
    mark_active.short_description = "Mark selected as active"
    
    def mark_inactive(self, request, queryset):
        queryset.update(is_active=False)
    mark_inactive.short_description = "Mark selected as inactive"
    
    def reindex_embeddings(self, request, queryset):
        from .evidence_retriever import EvidenceRetriever
        retriever = EvidenceRetriever()
        count = 0
        for source in queryset:
            if not source.embedding:
                text = f"{source.title} {source.abstract or ''} {source.key_findings or ''}"
                source.embedding = retriever.get_embedding(text)
                source.save(update_fields=['embedding', 'last_indexed'])
                count += 1
        self.message_user(request, f"Reindexed embeddings for {count} sources")
    reindex_embeddings.short_description = "Reindex embeddings for selected sources"


@admin.register(RecommendationEvidence)
class RecommendationEvidenceAdmin(admin.ModelAdmin):
    list_display = (
        'recommendation_type', 'get_patient', 'total_evidence_score',
        'high_strength_count', 'moderate_strength_count', 'created_at'
    )
    list_filter = ('recommendation_type', 'created_at', 'total_evidence_score')
    search_fields = ('treatment_plan__patient__username', 'recommendation_text')
    readonly_fields = ('id', 'created_at', 'updated_at', 'total_evidence_score')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Recommendation', {
            'fields': ('treatment_plan', 'recommendation_type', 'recommendation_text')
        }),
        ('Evidence Summary', {
            'fields': (
                'total_evidence_score', 'high_strength_count',
                'moderate_strength_count', 'low_strength_count',
                'recommendation_confidence'
            )
        }),
        ('Decision Factors', {
            'fields': ('decision_factors',),
            'classes': ('collapse',)
        }),
        ('Alternatives', {
            'fields': ('alternative_recommendations',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at')
        }),
    )
    
    def get_patient(self, obj):
        return obj.treatment_plan.patient.username
    get_patient.short_description = 'Patient'
    
    readonly_fields = ('id', 'created_at', 'updated_at')


class EvidenceLinkInline(admin.TabularInline):
    model = EvidenceLink
    extra = 1
    readonly_fields = ('id', 'relevance_score', 'impact_percentage')
    fields = ('evidence_source', 'relevance_type', 'relevance_score', 'impact_percentage', 'how_evidence_supports')


@admin.register(EvidenceExplanationLog)
class EvidenceExplanationLogAdmin(admin.ModelAdmin):
    list_display = (
        'get_patient', 'explanation_type', 'was_helpful',
        'response_time_ms', 'created_at'
    )
    list_filter = ('explanation_type', 'was_helpful', 'created_at')
    search_fields = ('user__username', 'user_feedback')
    readonly_fields = ('id', 'created_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Request Information', {
            'fields': ('user', 'treatment_plan', 'recommendation_evidence', 'explanation_type')
        }),
        ('Response Details', {
            'fields': ('response_time_ms', 'sources_shown'),
            'classes': ('collapse',)
        }),
        ('User Feedback', {
            'fields': ('was_helpful', 'user_feedback')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at')
        }),
    )
    
    def get_patient(self, obj):
        return obj.user.username
    get_patient.short_description = 'Patient'


@admin.register(RuleBasedReference)
class RuleBasedReferenceAdmin(admin.ModelAdmin):
    list_display = (
        'rule_name', 'cancer_type', 'cancer_stage', 'evidence_strength',
        'priority_level', 'is_active', 'created_at'
    )
    list_filter = (
        'cancer_type', 'cancer_stage', 'evidence_strength',
        'priority_level', 'is_active', 'created_at'
    )
    search_fields = ('rule_name', 'description', 'recommended_treatment')
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Rule Identification', {
            'fields': ('id', 'rule_name', 'is_active')
        }),
        ('Cancer Details', {
            'fields': ('cancer_type', 'cancer_stage', 'biomarker_requirement')
        }),
        ('Recommendation', {
            'fields': ('recommended_treatment', 'description')
        }),
        ('Evidence', {
            'fields': (
                'evidence_strength', 'pubmed_references',
                'guideline_references'
            )
        }),
        ('Rule Logic', {
            'fields': ('rule_logic',),
            'classes': ('collapse',)
        }),
        ('Priority & Creator', {
            'fields': ('priority_level', 'created_by')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    actions = ['init_default_rules', 'increase_priority', 'decrease_priority']
    
    def init_default_rules(self, request, queryset):
        """Initialize default rules from manager"""
        count = RuleBasedReferenceManager.initialize_default_rules(request.user)
        self.message_user(request, f"Initialized {count} default rule-based references")
    init_default_rules.short_description = "Initialize default rules"
    
    def increase_priority(self, request, queryset):
        for rule in queryset:
            rule.priority_level = min(rule.priority_level + 1, 100)
            rule.save()
        self.message_user(request, f"Increased priority for {queryset.count()} rules")
    increase_priority.short_description = "Increase priority"
    
    def decrease_priority(self, request, queryset):
        for rule in queryset:
            rule.priority_level = max(rule.priority_level - 1, 0)
            rule.save()
        self.message_user(request, f"Decreased priority for {queryset.count()} rules")
    decrease_priority.short_description = "Decrease priority"
