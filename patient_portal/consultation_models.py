"""
Models for Patient-Doctor Consultation System
"""
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()


class DoctorAvailability(models.Model):
    """
    Doctor's availability schedule
    """
    WEEKDAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='availability_slots')
    
    # Day and time
    weekday = models.IntegerField(choices=WEEKDAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    # Availability status
    is_available = models.BooleanField(default=True)
    
    # Consultation duration in minutes
    slot_duration = models.IntegerField(default=30, help_text="Duration of each consultation in minutes")
    
    # Metadata
    notes = models.TextField(blank=True, help_text="Any special notes about availability")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'doctor_availability'
        ordering = ['weekday', 'start_time']
        verbose_name = 'Doctor Availability'
        verbose_name_plural = 'Doctor Availabilities'
        unique_together = ['doctor', 'weekday', 'start_time']
    
    def __str__(self):
        return f"{self.doctor.username} - {self.get_weekday_display()} {self.start_time}-{self.end_time}"


class ConsultationRequest(models.Model):
    """
    Patient's request for consultation with a doctor
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('scheduled', 'Scheduled'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
    ]
    
    CONSULTATION_TYPE_CHOICES = [
        ('initial', 'Initial Consultation'),
        ('follow_up', 'Follow-up'),
        ('second_opinion', 'Second Opinion'),
        ('treatment_review', 'Treatment Review'),
        ('general', 'General Consultation'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='consultation_requests')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_consultation_requests')
    
    # Request details
    consultation_type = models.CharField(max_length=30, choices=CONSULTATION_TYPE_CHOICES, default='general')
    reason = models.TextField(help_text="Brief description of consultation reason")
    preferred_dates = models.JSONField(default=list, help_text="List of preferred date/times")
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Doctor's response
    doctor_notes = models.TextField(blank=True, help_text="Doctor's notes or response")
    suggested_times = models.JSONField(default=list, help_text="Doctor's suggested time slots")
    
    # Timestamps
    requested_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'consultation_requests'
        ordering = ['-requested_at']
        verbose_name = 'Consultation Request'
        verbose_name_plural = 'Consultation Requests'
    
    def __str__(self):
        return f"Request from {self.patient.username} to Dr. {self.doctor.username} - {self.status}"


class Consultation(models.Model):
    """
    Confirmed consultation appointment
    """
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('no_show', 'No Show'),
    ]
    
    MODE_CHOICES = [
        ('video', 'Video Call'),
        ('phone', 'Phone Call'),
        ('in_person', 'In-Person'),
        ('chat', 'Chat'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.OneToOneField(ConsultationRequest, on_delete=models.CASCADE, related_name='consultation')
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='consultations')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_consultations')
    
    # Consultation details
    scheduled_datetime = models.DateTimeField()
    duration_minutes = models.IntegerField(default=30)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default='video')
    
    # Meeting details
    meeting_link = models.URLField(blank=True, help_text="Video call link if applicable")
    meeting_id = models.CharField(max_length=100, blank=True)
    meeting_password = models.CharField(max_length=100, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    # Call status for real-time calls
    call_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('calling', 'Calling'),
            ('active', 'Active'),
            ('ended', 'Ended'),
        ],
        default='pending',
        help_text="Real-time call status"
    )
    call_initiated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='initiated_calls'
    )
    call_initiated_at = models.DateTimeField(null=True, blank=True)
    
    # WebRTC Signaling data (for peer-to-peer connection)
    patient_offer = models.TextField(blank=True, help_text="WebRTC offer from patient")
    doctor_answer = models.TextField(blank=True, help_text="WebRTC answer from doctor")
    patient_ice_candidates = models.TextField(blank=True, help_text="ICE candidates from patient (JSON)")
    doctor_ice_candidates = models.TextField(blank=True, help_text="ICE candidates from doctor (JSON)")
    
    # Consultation notes
    doctor_notes = models.TextField(blank=True, help_text="Doctor's consultation notes")
    prescription = models.TextField(blank=True, help_text="Prescription if any")
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Ratings (after consultation)
    patient_rating = models.IntegerField(null=True, blank=True, help_text="Patient's rating (1-5)")
    patient_feedback = models.TextField(blank=True)
    
    class Meta:
        db_table = 'consultations'
        ordering = ['-scheduled_datetime']
        verbose_name = 'Consultation'
        verbose_name_plural = 'Consultations'
    
    def __str__(self):
        return f"Consultation: {self.patient.username} with Dr. {self.doctor.username} on {self.scheduled_datetime}"
    
    @property
    def is_upcoming(self):
        """Check if consultation is upcoming"""
        return self.status == 'scheduled' and self.scheduled_datetime > timezone.now()
    
    @property
    def is_past(self):
        """Check if consultation is in the past"""
        return self.scheduled_datetime < timezone.now()


class ConsultationToken(models.Model):
    """
    In-person consultation token with blockchain verification.
    Token number is sequential per doctor, reflecting patient visit count.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consultation = models.OneToOneField(Consultation, on_delete=models.CASCADE, related_name='consultation_token')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='issued_tokens')
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_tokens')
    
    # Sequential token number per doctor (reflects patient visit count)
    token_number = models.IntegerField(help_text="Sequential token number for this doctor")
    
    # PDF and blockchain
    pdf_file = models.FileField(upload_to='consultation_tokens/', blank=True, null=True)
    pdf_hash = models.CharField(max_length=64, blank=True, help_text="SHA-256 hash of PDF")
    blockchain_tx_hash = models.CharField(max_length=66, blank=True, help_text="Blockchain transaction hash")
    is_verified = models.BooleanField(default=False, help_text="Whether hash is confirmed on blockchain")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'consultation_tokens'
        ordering = ['-created_at']
        verbose_name = 'Consultation Token'
        verbose_name_plural = 'Consultation Tokens'
        unique_together = ['doctor', 'token_number']
    
    def __str__(self):
        return f"Token #{self.token_number} - Dr. {self.doctor.last_name} for {self.patient.first_name}"
    
    @classmethod
    def get_next_token_number(cls, doctor):
        """Get the next sequential token number for a given doctor"""
        last_token = cls.objects.filter(doctor=doctor).order_by('-token_number').first()
        return (last_token.token_number + 1) if last_token else 1
