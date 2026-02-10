from django.contrib import admin
from django.db.models import QuerySet
from .models import (
    PatientSymptomLog, PatientTreatmentExplanation,
    PatientSideEffectInfo, PatientAlert, PatientNotificationPreference,
    DoctorAvailability, ConsultationRequest, Consultation,
    # Gamification models
    Badge, UserBadge, UserProgress, HealthChallenge, ChallengeParticipation,
    Reward, UserReward, FriendRequest, UserFriend, LeaderboardEntry, ActivityFeed
)


@admin.register(PatientSymptomLog)
class PatientSymptomLogAdmin(admin.ModelAdmin):
    list_display = ['patient', 'log_date', 'log_type', 'overall_wellbeing', 'reviewed_by_doctor', 'submitted_at']
    list_filter = ['log_type', 'reviewed_by_doctor', 'log_date']
    search_fields = ['patient__username', 'patient__email']
    readonly_fields = ['id', 'submitted_at']
    raw_id_fields = ['patient', 'treatment_plan']  # Use raw_id to avoid queryset iteration issues
    
    def get_queryset(self, request):
        """Optimize queryset to prevent cursor issues"""
        qs = super().get_queryset(request)
        # Force evaluation to prevent lazy queryset iteration issues
        return qs.select_related('patient', 'treatment_plan').prefetch_related()


@admin.register(PatientTreatmentExplanation)
class PatientTreatmentExplanationAdmin(admin.ModelAdmin):
    list_display = ['patient', 'treatment_plan', 'approved_by', 'approved_at', 'created_at']
    list_filter = ['created_at', 'approved_at']
    search_fields = ['patient__username']
    readonly_fields = ['id', 'created_at', 'updated_at', 'treatment_plan']


@admin.register(PatientSideEffectInfo)
class PatientSideEffectInfoAdmin(admin.ModelAdmin):
    list_display = ['patient', 'treatment_name', 'created_at']
    list_filter = ['created_at']
    search_fields = ['patient__username', 'treatment_name']
    readonly_fields = ['id', 'created_at', 'updated_at', 'treatment_plan']


@admin.register(PatientAlert)
class PatientAlertAdmin(admin.ModelAdmin):
    list_display = ['patient', 'alert_type', 'title', 'channel', 'status', 'is_urgent', 'created_at']
    list_filter = ['alert_type', 'channel', 'status', 'is_urgent', 'created_at']
    search_fields = ['patient__username', 'title']
    readonly_fields = ['id', 'created_at']


@admin.register(PatientNotificationPreference)
class PatientNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['patient', 'enable_in_app', 'enable_sms', 'enable_whatsapp', 'enable_email', 'symptom_reminder_frequency']
    search_fields = ['patient__username']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    list_display = ['doctor', 'weekday', 'start_time', 'end_time', 'is_available', 'slot_duration']
    list_filter = ['weekday', 'is_available', 'doctor']
    search_fields = ['doctor__username', 'doctor__first_name', 'doctor__last_name']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(ConsultationRequest)
class ConsultationRequestAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'consultation_type', 'status', 'requested_at']
    list_filter = ['status', 'consultation_type', 'requested_at']
    search_fields = ['patient__username', 'doctor__username', 'reason']
    readonly_fields = ['id', 'requested_at']


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'scheduled_datetime', 'mode', 'status', 'duration_minutes']
    list_filter = ['status', 'mode', 'scheduled_datetime']
    search_fields = ['patient__username', 'doctor__username']
    readonly_fields = ['id', 'created_at', 'updated_at']


# ============================================================================
# GAMIFICATION ADMIN
# ============================================================================

@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'rarity', 'points_reward', 'is_active', 'created_at']
    list_filter = ['category', 'rarity', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ['user', 'badge', 'earned_at', 'notification_sent']
    list_filter = ['badge__category', 'badge__rarity', 'earned_at', 'notification_sent']
    search_fields = ['user__username', 'badge__name']
    readonly_fields = ['id', 'earned_at']


@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ['user', 'level', 'total_points', 'current_streak', 'longest_streak', 'total_badges_earned']
    list_filter = ['level', 'created_at']
    search_fields = ['user__username']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-total_points']


@admin.register(HealthChallenge)
class HealthChallengeAdmin(admin.ModelAdmin):
    list_display = ['title', 'challenge_type', 'status', 'start_date', 'end_date', 'points_reward', 'created_by']
    list_filter = ['challenge_type', 'status', 'is_public', 'start_date', 'end_date']
    search_fields = ['title', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'start_date'


@admin.register(ChallengeParticipation)
class ChallengeParticipationAdmin(admin.ModelAdmin):
    list_display = ['user', 'challenge', 'status', 'progress_percentage', 'joined_at', 'completed_at']
    list_filter = ['status', 'reward_claimed', 'joined_at']
    search_fields = ['user__username', 'challenge__title']
    readonly_fields = ['id', 'joined_at', 'updated_at']


@admin.register(Reward)
class RewardAdmin(admin.ModelAdmin):
    list_display = ['name', 'reward_type', 'points_required', 'level_required', 'is_available', 'current_claims', 'max_claims']
    list_filter = ['reward_type', 'is_available', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(UserReward)
class UserRewardAdmin(admin.ModelAdmin):
    list_display = ['user', 'reward', 'claimed_at', 'points_spent', 'is_used']
    list_filter = ['is_used', 'claimed_at']
    search_fields = ['user__username', 'reward__name', 'claim_code']
    readonly_fields = ['id', 'claimed_at']


@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ['from_user', 'to_user', 'status', 'created_at', 'responded_at']
    list_filter = ['status', 'created_at']
    search_fields = ['from_user__username', 'to_user__username']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(UserFriend)
class UserFriendAdmin(admin.ModelAdmin):
    list_display = ['user', 'friend', 'is_favorite', 'created_at']
    list_filter = ['is_favorite', 'created_at']
    search_fields = ['user__username', 'friend__username']
    readonly_fields = ['id', 'created_at']


@admin.register(LeaderboardEntry)
class LeaderboardEntryAdmin(admin.ModelAdmin):
    list_display = ['user', 'period', 'rank', 'points', 'period_start']
    list_filter = ['period', 'period_start']
    search_fields = ['user__username']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['period', 'rank']


@admin.register(ActivityFeed)
class ActivityFeedAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity_type', 'title', 'visibility', 'created_at']
    list_filter = ['activity_type', 'visibility', 'created_at']
    search_fields = ['user__username', 'title', 'description']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'
