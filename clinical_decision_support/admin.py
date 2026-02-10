from django.contrib import admin
from .models import (
    AIConfidenceMetadata, XAIExplanation, TumorBoardSession, 
    TumorBoardMember, TumorBoardAuditLog, ToxicityPrediction,
    DoctorSymptomMonitor
)


@admin.register(AIConfidenceMetadata)
class AIConfidenceMetadataAdmin(admin.ModelAdmin):
    list_display = ['patient', 'analysis_type', 'overall_confidence', 'confidence_level', 'created_at']
    list_filter = ['analysis_type', 'confidence_level', 'created_at']
    search_fields = ['patient__username', 'patient__email']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(XAIExplanation)
class XAIExplanationAdmin(admin.ModelAdmin):
    list_display = ['patient', 'treatment_plan', 'created_at']
    list_filter = ['created_at']
    search_fields = ['patient__username', 'patient__email']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(TumorBoardSession)
class TumorBoardSessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'patient', 'status', 'created_by', 'consensus_reached', 'created_at']
    list_filter = ['status', 'consensus_reached', 'created_at']
    search_fields = ['title', 'patient__username', 'created_by__username']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(TumorBoardMember)
class TumorBoardMemberAdmin(admin.ModelAdmin):
    list_display = ['session', 'doctor', 'role', 'decision', 'accepted']
    list_filter = ['role', 'decision', 'accepted']
    search_fields = ['doctor__username', 'session__title']
    readonly_fields = ['id', 'invited_at']


@admin.register(TumorBoardAuditLog)
class TumorBoardAuditLogAdmin(admin.ModelAdmin):
    list_display = ['session', 'action', 'actor', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['session__title', 'actor__username']
    readonly_fields = ['id', 'timestamp', 'details', 'previous_state', 'new_state']


@admin.register(ToxicityPrediction)
class ToxicityPredictionAdmin(admin.ModelAdmin):
    list_display = ['patient', 'drug_name', 'overall_risk_level', 'prediction_confidence', 'created_at']
    list_filter = ['overall_risk_level', 'created_at']
    search_fields = ['patient__username', 'drug_name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(DoctorSymptomMonitor)
class DoctorSymptomMonitorAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'alert_status', 'last_reviewed_at', 'updated_at']
    list_filter = ['alert_status', 'updated_at']
    search_fields = ['patient__username', 'doctor__username']
    readonly_fields = ['id', 'created_at', 'updated_at']
