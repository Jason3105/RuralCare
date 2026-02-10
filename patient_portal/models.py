from django.db import models
from django.contrib.auth import get_user_model
import uuid
from django.utils import timezone

User = get_user_model()


class PatientSymptomLog(models.Model):
    """
    Patient-reported symptoms logged daily or weekly.
    Cannot be edited after submission.
    """
    
    SEVERITY_CHOICES = [
        (1, 'Very Mild'),
        (2, 'Mild'),
        (3, 'Moderate'),
        (4, 'Severe'),
        (5, 'Very Severe'),
    ]
    
    FREQUENCY_CHOICES = [
        ('rarely', 'Rarely'),
        ('sometimes', 'Sometimes'),
        ('often', 'Often'),
        ('always', 'Always'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='symptom_logs')
    treatment_plan = models.ForeignKey('cancer_detection.PersonalizedTreatmentPlan',
                                        on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='patient_symptom_logs')
    
    # Log date
    log_date = models.DateField(default=timezone.now)
    log_type = models.CharField(max_length=10, choices=[('daily', 'Daily'), ('weekly', 'Weekly')], default='daily')
    
    # Common oncology symptoms (severity 1-5)
    fatigue = models.IntegerField(choices=SEVERITY_CHOICES, null=True, blank=True)
    pain = models.IntegerField(choices=SEVERITY_CHOICES, null=True, blank=True)
    pain_location = models.CharField(max_length=200, null=True, blank=True)
    nausea = models.IntegerField(choices=SEVERITY_CHOICES, null=True, blank=True)
    vomiting = models.IntegerField(choices=SEVERITY_CHOICES, null=True, blank=True)
    appetite_loss = models.IntegerField(choices=SEVERITY_CHOICES, null=True, blank=True)
    weight_change = models.CharField(max_length=50, null=True, blank=True)  # e.g., "Lost 2 kg"
    sleep_problems = models.IntegerField(choices=SEVERITY_CHOICES, null=True, blank=True)
    shortness_of_breath = models.IntegerField(choices=SEVERITY_CHOICES, null=True, blank=True)
    diarrhea = models.IntegerField(choices=SEVERITY_CHOICES, null=True, blank=True)
    constipation = models.IntegerField(choices=SEVERITY_CHOICES, null=True, blank=True)
    mouth_sores = models.IntegerField(choices=SEVERITY_CHOICES, null=True, blank=True)
    skin_changes = models.IntegerField(choices=SEVERITY_CHOICES, null=True, blank=True)
    numbness_tingling = models.IntegerField(choices=SEVERITY_CHOICES, null=True, blank=True)
    fever = models.BooleanField(default=False)
    fever_temperature = models.FloatField(null=True, blank=True)  # in Celsius
    
    # Emotional/Mental symptoms
    anxiety = models.IntegerField(choices=SEVERITY_CHOICES, null=True, blank=True)
    depression = models.IntegerField(choices=SEVERITY_CHOICES, null=True, blank=True)
    confusion = models.IntegerField(choices=SEVERITY_CHOICES, null=True, blank=True)
    
    # Hair loss (specific tracking)
    hair_loss = models.CharField(max_length=50, choices=[
        ('none', 'None'),
        ('minimal', 'Minimal'),
        ('moderate', 'Moderate'),
        ('significant', 'Significant'),
        ('complete', 'Complete'),
    ], null=True, blank=True)
    
    # Overall wellbeing
    overall_wellbeing = models.IntegerField(choices=[
        (1, 'Very Poor'),
        (2, 'Poor'),
        (3, 'Fair'),
        (4, 'Good'),
        (5, 'Very Good'),
    ], null=True, blank=True)
    
    # Activity level
    activity_level = models.CharField(max_length=50, choices=[
        ('bedridden', 'Bedridden'),
        ('mostly_rest', 'Mostly Resting'),
        ('limited', 'Limited Activity'),
        ('normal', 'Normal Activity'),
    ], null=True, blank=True)
    
    # Additional notes
    additional_symptoms = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    
    # Submission tracking
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_submitted = models.BooleanField(default=True)  # Once submitted, cannot edit
    
    # Doctor review status
    reviewed_by_doctor = models.BooleanField(default=False)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    doctor_response = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'patient_symptom_logs'
        ordering = ['-log_date', '-submitted_at']
        verbose_name = 'Patient Symptom Log'
        verbose_name_plural = 'Patient Symptom Logs'
    
    def __str__(self):
        return f"Symptom Log: {self.patient.username} - {self.log_date}"
    
    def get_severe_symptoms(self):
        """Returns list of symptoms with severity >= 4"""
        severe = []
        symptom_fields = [
            'fatigue', 'pain', 'nausea', 'vomiting', 'appetite_loss',
            'sleep_problems', 'shortness_of_breath', 'diarrhea', 'constipation',
            'mouth_sores', 'skin_changes', 'numbness_tingling', 'anxiety',
            'depression', 'confusion'
        ]
        for field in symptom_fields:
            value = getattr(self, field)
            if value and value >= 4:
                severe.append({'symptom': field.replace('_', ' ').title(), 'severity': value})
        return severe


class PatientTreatmentExplanation(models.Model):
    """
    Patient-friendly treatment explanation derived from approved treatment plan.
    Simple language, step-by-step journey.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='treatment_explanations')
    treatment_plan = models.OneToOneField('cancer_detection.PersonalizedTreatmentPlan',
                                           on_delete=models.CASCADE, related_name='patient_explanation')
    
    # Simple language summary
    treatment_summary = models.TextField()  # Plain language overview
    
    # Why this treatment was chosen
    why_this_treatment = models.TextField(null=True, blank=True)
    
    # Expected benefits
    expected_benefits = models.JSONField(default=list)
    # Example: ["Shrink the tumor", "Prevent spread", "Improve quality of life"]
    
    # Step-by-step treatment journey
    treatment_steps = models.JSONField(default=list)
    # Example: [
    #   {"step": 1, "title": "Initial Tests", "description": "Blood tests and scans", "duration": "1-2 weeks"},
    #   {"step": 2, "title": "Start Chemotherapy", "description": "...", "duration": "3 months"},
    # ]
    
    # Timeline
    estimated_duration = models.CharField(max_length=100, null=True, blank=True)
    key_milestones = models.JSONField(default=list, blank=True)
    
    # What to expect
    what_to_expect = models.JSONField(default=list, blank=True)
    # Example: ["Regular hospital visits", "Blood tests every week", "Some side effects"]
    
    # Questions to ask doctor
    suggested_questions = models.JSONField(default=list, blank=True)
    
    # Last updated by doctor
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='approved_explanations')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'patient_treatment_explanations'
        ordering = ['-created_at']
        verbose_name = 'Patient Treatment Explanation'
        verbose_name_plural = 'Patient Treatment Explanations'
    
    def __str__(self):
        return f"Explanation: {self.patient.username} - {self.treatment_plan.cancer_type}"


class PatientSideEffectInfo(models.Model):
    """
    Patient-friendly side effect information.
    Simple labels, no CTCAE grades or probabilities.
    """
    
    SEVERITY_LABEL_CHOICES = [
        ('low', 'Low'),
        ('moderate', 'Moderate'),
        ('high', 'High'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='side_effect_info')
    treatment_plan = models.ForeignKey('cancer_detection.PersonalizedTreatmentPlan',
                                        on_delete=models.CASCADE, related_name='patient_side_effects')
    
    # Drug/Treatment name
    treatment_name = models.CharField(max_length=200)
    
    # Common side effects with simple severity labels
    common_side_effects = models.JSONField(default=list)
    # Example: [
    #   {"effect": "Tiredness", "severity": "moderate", "description": "You may feel more tired than usual"},
    #   {"effect": "Nausea", "severity": "low", "description": "Some stomach upset is normal"},
    # ]
    
    # What is normal
    what_is_normal = models.JSONField(default=list, blank=True)
    # Example: ["Feeling tired for a few days after treatment", "Mild nausea"]
    
    # When to contact doctor
    when_to_contact_doctor = models.JSONField(default=list, blank=True)
    # Example: ["Fever over 38°C", "Severe vomiting", "Unusual bleeding"]
    
    # Self-care tips
    self_care_tips = models.JSONField(default=list, blank=True)
    
    # Emergency signs
    emergency_signs = models.JSONField(default=list, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'patient_side_effect_info'
        ordering = ['-created_at']
        verbose_name = 'Patient Side Effect Info'
        verbose_name_plural = 'Patient Side Effect Info'
    
    def __str__(self):
        return f"Side Effects: {self.treatment_name} - {self.patient.username}"


class PatientAlert(models.Model):
    """
    Patient alerts and reminders.
    Supports multiple notification channels.
    """
    
    ALERT_TYPE_CHOICES = [
        ('symptom_reminder', 'Symptom Log Reminder'),
        ('doctor_review', 'Doctor Reviewed Symptoms'),
        ('appointment', 'Appointment Reminder'),
        ('medication', 'Medication Reminder'),
        ('reassurance', 'Reassurance Message'),
        ('general', 'General Notification'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('read', 'Read'),
        ('failed', 'Failed'),
    ]
    
    CHANNEL_CHOICES = [
        ('in_app', 'In-App Notification'),
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alerts')
    
    # Alert details
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Channel and status
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='in_app')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Scheduling
    scheduled_for = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # Related objects
    related_symptom_log = models.ForeignKey(PatientSymptomLog, on_delete=models.SET_NULL,
                                             null=True, blank=True, related_name='alerts')
    
    # Priority
    is_urgent = models.BooleanField(default=False)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'patient_alerts'
        ordering = ['-created_at']
        verbose_name = 'Patient Alert'
        verbose_name_plural = 'Patient Alerts'
    
    def __str__(self):
        return f"Alert: {self.title} - {self.patient.username}"
    
    def mark_as_sent(self):
        self.status = 'sent'
        self.sent_at = timezone.now()
        self.save()
    
    def mark_as_read(self):
        self.status = 'read'
        self.read_at = timezone.now()
        self.save()
    
    @property
    def is_read(self):
        """Property to check if alert is read"""
        return self.status == 'read'


class PatientNotificationPreference(models.Model):
    """
    Patient notification preferences for different channels.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Channel preferences
    enable_in_app = models.BooleanField(default=True)
    enable_sms = models.BooleanField(default=False)
    enable_whatsapp = models.BooleanField(default=False)
    enable_email = models.BooleanField(default=True)
    
    # Contact information
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    whatsapp_number = models.CharField(max_length=20, null=True, blank=True)
    
    # Reminder preferences
    symptom_reminder_frequency = models.CharField(max_length=20, choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('none', 'No Reminders'),
    ], default='daily')
    reminder_time = models.TimeField(null=True, blank=True)  # Preferred reminder time
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'patient_notification_preferences'
        verbose_name = 'Patient Notification Preference'
        verbose_name_plural = 'Patient Notification Preferences'
    
    def __str__(self):
        return f"Preferences: {self.patient.username}"


# Import consultation models
from .consultation_models import DoctorAvailability, ConsultationRequest, Consultation


# ============================================================================
# GAMIFICATION MODELS
# ============================================================================

class Badge(models.Model):
    """
    Achievement badges that patients can earn.
    """
    
    BADGE_CATEGORY_CHOICES = [
        ('symptom_tracking', 'Symptom Tracking'),
        ('consistency', 'Consistency'),
        ('wellness', 'Wellness'),
        ('milestone', 'Milestone'),
        ('social', 'Social'),
        ('treatment', 'Treatment'),
    ]
    
    BADGE_RARITY_CHOICES = [
        ('common', 'Common'),
        ('uncommon', 'Uncommon'),
        ('rare', 'Rare'),
        ('epic', 'Epic'),
        ('legendary', 'Legendary'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=30, choices=BADGE_CATEGORY_CHOICES)
    rarity = models.CharField(max_length=20, choices=BADGE_RARITY_CHOICES, default='common')
    
    # Badge image/icon
    icon_url = models.URLField(max_length=500, null=True, blank=True)
    icon_name = models.CharField(max_length=100, null=True, blank=True)  # For icon libraries
    
    # Points awarded when badge is earned
    points_reward = models.IntegerField(default=0)
    
    # Criteria for earning (stored as JSON for flexibility)
    criteria = models.JSONField(default=dict)
    # Example: {"action": "log_symptoms", "count": 7, "period": "days"}
    
    # Badge is active/available
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'gamification_badges'
        ordering = ['category', 'rarity', 'name']
        verbose_name = 'Badge'
        verbose_name_plural = 'Badges'
    
    def __str__(self):
        return f"{self.name} ({self.get_rarity_display()})"


class UserBadge(models.Model):
    """
    Tracks badges earned by users.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='earned_badges')
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE, related_name='user_badges')
    
    # When badge was earned
    earned_at = models.DateTimeField(auto_now_add=True)
    
    # Optional: related activity that triggered the badge
    related_activity_type = models.CharField(max_length=50, null=True, blank=True)
    related_activity_id = models.UUIDField(null=True, blank=True)
    
    # Notification sent
    notification_sent = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'gamification_user_badges'
        ordering = ['-earned_at']
        unique_together = ['user', 'badge']  # User can only earn a badge once
        verbose_name = 'User Badge'
        verbose_name_plural = 'User Badges'
    
    def __str__(self):
        return f"{self.user.username} - {self.badge.name}"


class UserProgress(models.Model):
    """
    Tracks user's overall progress, points, level, and streaks.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='gamification_progress')
    
    # Points system
    total_points = models.IntegerField(default=0)
    lifetime_points = models.IntegerField(default=0)  # Never decreases
    
    # Level system (calculated from points)
    level = models.IntegerField(default=1)
    experience_points = models.IntegerField(default=0)  # Points in current level
    points_to_next_level = models.IntegerField(default=100)
    
    # Streaks
    current_streak = models.IntegerField(default=0)  # Current consecutive days
    longest_streak = models.IntegerField(default=0)  # Best streak ever
    last_activity_date = models.DateField(null=True, blank=True)
    
    # Activity counters
    total_symptom_logs = models.IntegerField(default=0)
    total_challenges_completed = models.IntegerField(default=0)
    total_badges_earned = models.IntegerField(default=0)
    
    # Weekly/Monthly stats
    weekly_points = models.IntegerField(default=0)
    monthly_points = models.IntegerField(default=0)
    weekly_reset_date = models.DateField(null=True, blank=True)
    monthly_reset_date = models.DateField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'gamification_user_progress'
        verbose_name = 'User Progress'
        verbose_name_plural = 'User Progress'
    
    def __str__(self):
        return f"{self.user.username} - Level {self.level} ({self.total_points} pts)"
    
    def calculate_level(self):
        """Calculate level based on total points"""
        # Level formula: level = sqrt(points / 100) + 1
        import math
        calculated_level = int(math.sqrt(self.total_points / 100)) + 1
        if calculated_level != self.level:
            self.level = calculated_level
            # Points needed for next level
            next_level_points = (calculated_level ** 2) * 100
            self.points_to_next_level = next_level_points - self.total_points
        return self.level
    
    def add_points(self, points, activity_type=None):
        """Add points and update progress"""
        self.total_points += points
        self.lifetime_points += points
        self.weekly_points += points
        self.monthly_points += points
        self.calculate_level()
        self.save()
    
    def update_streak(self, activity_date=None):
        """Update streak based on activity date"""
        from datetime import date, timedelta
        if activity_date is None:
            activity_date = timezone.now().date()
        
        if self.last_activity_date:
            days_diff = (activity_date - self.last_activity_date).days
            if days_diff == 1:
                # Consecutive day
                self.current_streak += 1
            elif days_diff > 1:
                # Streak broken
                self.current_streak = 1
        else:
            # First activity
            self.current_streak = 1
        
        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak
        
        self.last_activity_date = activity_date
        self.save()


class HealthChallenge(models.Model):
    """
    Health challenges that patients can participate in.
    """
    
    CHALLENGE_TYPE_CHOICES = [
        ('symptom_logging', 'Symptom Logging'),
        ('wellness', 'Wellness'),
        ('consistency', 'Consistency'),
        ('social', 'Social'),
        ('treatment', 'Treatment'),
        ('custom', 'Custom'),
    ]
    
    CHALLENGE_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    description = models.TextField()
    challenge_type = models.CharField(max_length=30, choices=CHALLENGE_TYPE_CHOICES)
    
    # Challenge goals
    goal_description = models.TextField()  # What needs to be achieved
    goal_value = models.IntegerField(default=1)  # Numeric goal (e.g., 7 days, 10 logs)
    goal_unit = models.CharField(max_length=50, default='times')  # days, times, etc.
    
    # Duration
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    duration_days = models.IntegerField(null=True, blank=True)  # Auto-calculated
    
    # Rewards
    points_reward = models.IntegerField(default=0)
    badge_reward = models.ForeignKey(Badge, on_delete=models.SET_NULL, null=True, blank=True, related_name='challenges')
    custom_reward = models.TextField(null=True, blank=True)
    
    # Challenge settings
    status = models.CharField(max_length=20, choices=CHALLENGE_STATUS_CHOICES, default='draft')
    is_public = models.BooleanField(default=True)  # Can all users see it
    max_participants = models.IntegerField(null=True, blank=True)  # None = unlimited
    min_level_required = models.IntegerField(default=1)  # Minimum user level to join
    
    # Criteria (JSON for flexibility)
    criteria = models.JSONField(default=dict)
    # Example: {"action": "log_symptoms", "frequency": "daily", "target": 7}
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_challenges')
    image_url = models.URLField(max_length=500, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'gamification_health_challenges'
        ordering = ['-start_date', '-created_at']
        verbose_name = 'Health Challenge'
        verbose_name_plural = 'Health Challenges'
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    def is_active(self):
        """Check if challenge is currently active"""
        now = timezone.now()
        return (self.status == 'active' and 
                self.start_date <= now <= self.end_date)
    
    def get_participant_count(self):
        """Get number of participants"""
        return self.participants.filter(status__in=['joined', 'completed']).count()


class ChallengeParticipation(models.Model):
    """
    Tracks user participation in health challenges.
    """
    
    PARTICIPATION_STATUS_CHOICES = [
        ('joined', 'Joined'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('abandoned', 'Abandoned'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='challenge_participations')
    challenge = models.ForeignKey(HealthChallenge, on_delete=models.CASCADE, related_name='participants')
    
    # Progress tracking
    status = models.CharField(max_length=20, choices=PARTICIPATION_STATUS_CHOICES, default='joined')
    progress_value = models.IntegerField(default=0)  # Current progress toward goal
    progress_percentage = models.FloatField(default=0.0)  # 0-100
    
    # Completion
    completed_at = models.DateTimeField(null=True, blank=True)
    reward_claimed = models.BooleanField(default=False)
    
    # Timestamps
    joined_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'gamification_challenge_participations'
        ordering = ['-joined_at']
        unique_together = ['user', 'challenge']  # User can only join a challenge once
        verbose_name = 'Challenge Participation'
        verbose_name_plural = 'Challenge Participations'
    
    def __str__(self):
        return f"{self.user.username} - {self.challenge.title}"
    
    def update_progress(self, value):
        """Update progress toward challenge goal"""
        self.progress_value = value
        if self.challenge.goal_value > 0:
            self.progress_percentage = min(100.0, (value / self.challenge.goal_value) * 100)
        
        # Check if completed
        if self.progress_value >= self.challenge.goal_value and self.status != 'completed':
            self.status = 'completed'
            self.completed_at = timezone.now()
            # Award points and badge
            if self.challenge.points_reward > 0:
                progress_obj, _ = UserProgress.objects.get_or_create(user=self.user)
                progress_obj.add_points(self.challenge.points_reward, 'challenge_completion')
        
        self.save()


class Reward(models.Model):
    """
    Rewards that can be earned by users.
    """
    
    REWARD_TYPE_CHOICES = [
        ('points', 'Points'),
        ('badge', 'Badge'),
        ('discount', 'Discount'),
        ('virtual', 'Virtual Item'),
        ('custom', 'Custom'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField()
    reward_type = models.CharField(max_length=20, choices=REWARD_TYPE_CHOICES)
    
    # Reward value
    points_value = models.IntegerField(null=True, blank=True)
    badge = models.ForeignKey(Badge, on_delete=models.SET_NULL, null=True, blank=True, related_name='rewards')
    discount_code = models.CharField(max_length=50, null=True, blank=True)
    discount_percentage = models.FloatField(null=True, blank=True)
    custom_value = models.TextField(null=True, blank=True)
    
    # Requirements
    points_required = models.IntegerField(default=0)  # Points needed to claim
    level_required = models.IntegerField(default=1)  # Level needed to claim
    is_available = models.BooleanField(default=True)
    
    # Limits
    max_claims = models.IntegerField(null=True, blank=True)  # None = unlimited
    current_claims = models.IntegerField(default=0)
    max_claims_per_user = models.IntegerField(default=1)
    
    # Metadata
    image_url = models.URLField(max_length=500, null=True, blank=True)
    expiry_date = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'gamification_rewards'
        ordering = ['points_required', 'name']
        verbose_name = 'Reward'
        verbose_name_plural = 'Rewards'
    
    def __str__(self):
        return f"{self.name} ({self.get_reward_type_display()})"
    
    def can_be_claimed_by(self, user):
        """Check if user can claim this reward"""
        if not self.is_available:
            return False, "Reward is not available"
        
        if self.expiry_date and timezone.now() > self.expiry_date:
            return False, "Reward has expired"
        
        progress, _ = UserProgress.objects.get_or_create(user=user)
        if progress.total_points < self.points_required:
            return False, f"Need {self.points_required} points (you have {progress.total_points})"
        
        if progress.level < self.level_required:
            return False, f"Need level {self.level_required} (you are level {progress.level})"
        
        if self.max_claims and self.current_claims >= self.max_claims:
            return False, "Reward is out of stock"
        
        # Check user's claim count
        user_claims = UserReward.objects.filter(user=user, reward=self).count()
        if user_claims >= self.max_claims_per_user:
            return False, "You have already claimed this reward"
        
        return True, "Can claim"


class UserReward(models.Model):
    """
    Tracks rewards claimed by users.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='claimed_rewards')
    reward = models.ForeignKey(Reward, on_delete=models.CASCADE, related_name='user_rewards')
    
    # Claim details
    claimed_at = models.DateTimeField(auto_now_add=True)
    points_spent = models.IntegerField(default=0)
    
    # Status
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    
    # For discount codes, etc.
    claim_code = models.CharField(max_length=100, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'gamification_user_rewards'
        ordering = ['-claimed_at']
        verbose_name = 'User Reward'
        verbose_name_plural = 'User Rewards'
    
    def __str__(self):
        return f"{self.user.username} - {self.reward.name}"


# ============================================================================
# SOCIAL FEATURES
# ============================================================================

class FriendRequest(models.Model):
    """
    Friend requests between users.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_friend_requests')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_friend_requests')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    message = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'gamification_friend_requests'
        ordering = ['-created_at']
        unique_together = ['from_user', 'to_user']  # One request per pair
        verbose_name = 'Friend Request'
        verbose_name_plural = 'Friend Requests'
    
    def __str__(self):
        return f"{self.from_user.username} -> {self.to_user.username} ({self.status})"
    
    def accept(self):
        """Accept friend request"""
        self.status = 'accepted'
        self.responded_at = timezone.now()
        self.save()
        # Create friendship
        UserFriend.objects.get_or_create(
            user=self.from_user,
            friend=self.to_user
        )
        UserFriend.objects.get_or_create(
            user=self.to_user,
            friend=self.from_user
        )


class UserFriend(models.Model):
    """
    Friendships between users.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friends')
    friend = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friend_of')
    
    # Friendship metadata
    is_favorite = models.BooleanField(default=False)
    notes = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'gamification_user_friends'
        ordering = ['-created_at']
        unique_together = ['user', 'friend']  # One friendship per pair
        verbose_name = 'User Friend'
        verbose_name_plural = 'User Friends'
    
    def __str__(self):
        return f"{self.user.username} <-> {self.friend.username}"


class LeaderboardEntry(models.Model):
    """
    Leaderboard entries for competitive rankings.
    """
    
    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('all_time', 'All Time'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leaderboard_entries')
    
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES)
    period_start = models.DateField()  # Start of the period
    period_end = models.DateField(null=True, blank=True)  # End of the period
    
    # Rankings
    rank = models.IntegerField()
    points = models.IntegerField(default=0)
    
    # Additional metrics
    challenges_completed = models.IntegerField(default=0)
    badges_earned = models.IntegerField(default=0)
    streak_days = models.IntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'gamification_leaderboard_entries'
        ordering = ['period', 'rank', '-points']
        unique_together = ['user', 'period', 'period_start']
        verbose_name = 'Leaderboard Entry'
        verbose_name_plural = 'Leaderboard Entries'
    
    def __str__(self):
        return f"{self.user.username} - {self.get_period_display()} - Rank {self.rank}"


class ActivityFeed(models.Model):
    """
    Activity feed for social features - shows user activities.
    """
    
    ACTIVITY_TYPE_CHOICES = [
        ('badge_earned', 'Badge Earned'),
        ('challenge_completed', 'Challenge Completed'),
        ('level_up', 'Level Up'),
        ('streak_milestone', 'Streak Milestone'),
        ('reward_claimed', 'Reward Claimed'),
        ('friend_added', 'Friend Added'),
        ('custom', 'Custom Activity'),
    ]
    
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('friends', 'Friends Only'),
        ('private', 'Private'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_feed')
    
    activity_type = models.CharField(max_length=30, choices=ACTIVITY_TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Related objects
    related_badge = models.ForeignKey(Badge, on_delete=models.SET_NULL, null=True, blank=True, related_name='activity_feeds')
    related_challenge = models.ForeignKey(HealthChallenge, on_delete=models.SET_NULL, null=True, blank=True, related_name='activity_feeds')
    related_reward = models.ForeignKey(Reward, on_delete=models.SET_NULL, null=True, blank=True, related_name='activity_feeds')
    
    # Metadata
    points_earned = models.IntegerField(default=0)
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'gamification_activity_feed'
        ordering = ['-created_at']
        verbose_name = 'Activity Feed'
        verbose_name_plural = 'Activity Feed'
    
    def __str__(self):
        return f"{self.user.username} - {self.get_activity_type_display()}"


# ============================================================================
# OFFLINE SYNC MODELS
# ============================================================================

class OfflineSyncQueue(models.Model):
    """
    Queue for operations that need to be synced when connection is restored.
    Tracks patient operations performed offline.
    """
    
    OPERATION_TYPE_CHOICES = [
        ('symptom_log', 'Symptom Log'),
        ('alert_read', 'Alert Marked Read'),
        ('alert_read_all', 'All Alerts Marked Read'),
        ('notification_preference', 'Notification Preference Update'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending Sync'),
        ('syncing', 'Syncing'),
        ('synced', 'Synced'),
        ('failed', 'Failed'),
        ('conflict', 'Conflict'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='offline_sync_queue')
    
    # Operation details
    operation_type = models.CharField(max_length=50, choices=OPERATION_TYPE_CHOICES)
    operation_data = models.JSONField()  # Stores the data for the operation
    
    # Sync status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=5)
    
    # Error tracking
    error_message = models.TextField(null=True, blank=True)
    last_error_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    synced_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Client-side tracking
    client_id = models.CharField(max_length=100, null=True, blank=True)  # Client-generated ID
    client_timestamp = models.DateTimeField(null=True, blank=True)  # When operation was created on client
    
    class Meta:
        db_table = 'offline_sync_queue'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['patient', 'status', 'created_at']),
            models.Index(fields=['status', 'created_at']),
        ]
        verbose_name = 'Offline Sync Queue Item'
        verbose_name_plural = 'Offline Sync Queue Items'
    
    def __str__(self):
        return f"{self.patient.username} - {self.get_operation_type_display()} - {self.status}"
    
    def mark_syncing(self):
        """Mark as currently syncing"""
        self.status = 'syncing'
        self.save(update_fields=['status', 'updated_at'])
    
    def mark_synced(self):
        """Mark as successfully synced"""
        self.status = 'synced'
        self.synced_at = timezone.now()
        self.save(update_fields=['status', 'synced_at', 'updated_at'])
    
    def mark_failed(self, error_message):
        """Mark as failed with error message"""
        self.status = 'failed'
        self.error_message = error_message
        self.last_error_at = timezone.now()
        self.retry_count += 1
        self.save(update_fields=['status', 'error_message', 'last_error_at', 'retry_count', 'updated_at'])
    
    def can_retry(self):
        """Check if operation can be retried"""
        return self.retry_count < self.max_retries and self.status in ['pending', 'failed']


class OfflineDataCache(models.Model):
    """
    Cache of patient data for offline access.
    Stores essential patient data that can be accessed without internet.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.OneToOneField(User, on_delete=models.CASCADE, related_name='offline_cache')
    
    # Cached data (JSON)
    symptom_logs = models.JSONField(default=list, blank=True)  # Recent symptom logs
    alerts = models.JSONField(default=list, blank=True)  # Recent alerts
    treatment_plans = models.JSONField(default=list, blank=True)  # Treatment plan summaries
    notifications_prefs = models.JSONField(default=dict, blank=True)  # Notification preferences
    
    # Metadata
    last_synced_at = models.DateTimeField(null=True, blank=True)
    cache_version = models.IntegerField(default=1)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'offline_data_cache'
        verbose_name = 'Offline Data Cache'
        verbose_name_plural = 'Offline Data Caches'
    
    def __str__(self):
        return f"Offline Cache: {self.patient.username} (v{self.cache_version})"
