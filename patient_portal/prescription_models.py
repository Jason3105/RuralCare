"""
Prescription Model for Medical Prescriptions
"""
from django.db import models
from django.contrib.auth import get_user_model
import uuid
import hashlib
import json

User = get_user_model()


class Prescription(models.Model):
    """Medical Prescription with blockchain verification"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    consultation = models.ForeignKey(
        'Consultation',
        on_delete=models.CASCADE,
        related_name='prescriptions'
    )
    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='prescriptions_received'
    )
    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='prescriptions_issued'
    )
    
    # Prescription details
    diagnosis = models.TextField(help_text="Patient diagnosis")
    symptoms = models.TextField(blank=True, help_text="Observed symptoms")
    
    # Additional notes
    doctor_notes = models.TextField(blank=True, help_text="Additional instructions or notes")
    follow_up_instructions = models.TextField(blank=True, help_text="Follow-up care instructions")
    
    # Blockchain verification
    pdf_hash = models.CharField(max_length=64, blank=True, db_index=True, help_text="SHA-256 hash of PDF")
    blockchain_tx_hash = models.CharField(max_length=66, blank=True, help_text="Blockchain transaction hash")
    qr_code = models.ImageField(upload_to='prescription_qr/', blank=True, null=True)
    verification_url = models.URLField(blank=True, help_text="URL for prescription verification")
    
    # PDF storage
    pdf_file = models.FileField(upload_to='prescriptions/', blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Verification status
    is_verified = models.BooleanField(default=False, help_text="Blockchain verification status")
    
    class Meta:
        db_table = 'prescriptions'
        ordering = ['-created_at']
        verbose_name = 'Prescription'
        verbose_name_plural = 'Prescriptions'
    
    def __str__(self):
        return f"Prescription for {self.patient.username} by Dr. {self.doctor.username}"
    
    def generate_hash(self, pdf_content):
        """Generate SHA-256 hash of PDF content"""
        return hashlib.sha256(pdf_content).hexdigest()


class PrescriptionMedicine(models.Model):
    """Individual medicine in a prescription"""
    
    FREQUENCY_CHOICES = [
        ('once_daily', 'Once Daily'),
        ('twice_daily', 'Twice Daily (Morning & Evening)'),
        ('thrice_daily', 'Thrice Daily (Morning, Afternoon & Evening)'),
        ('four_times', 'Four Times Daily'),
        ('every_4_hours', 'Every 4 Hours'),
        ('every_6_hours', 'Every 6 Hours'),
        ('every_8_hours', 'Every 8 Hours'),
        ('every_12_hours', 'Every 12 Hours'),
        ('as_needed', 'As Needed'),
        ('before_meals', 'Before Meals'),
        ('after_meals', 'After Meals'),
        ('at_bedtime', 'At Bedtime'),
    ]
    
    TIMING_CHOICES = [
        ('before_food', 'Before Food'),
        ('after_food', 'After Food'),
        ('with_food', 'With Food'),
        ('empty_stomach', 'Empty Stomach'),
        ('anytime', 'Anytime'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prescription = models.ForeignKey(
        Prescription,
        on_delete=models.CASCADE,
        related_name='medicines'
    )
    
    # Medicine details
    medicine_name = models.CharField(max_length=255, help_text="Generic or Brand name")
    dosage = models.CharField(max_length=100, help_text="e.g., 500mg, 10ml, 1 tablet")
    frequency = models.CharField(max_length=50, choices=FREQUENCY_CHOICES)
    timing = models.CharField(max_length=50, choices=TIMING_CHOICES, default='after_food')
    duration_days = models.IntegerField(help_text="Duration in days")
    
    # Special instructions
    instructions = models.TextField(blank=True, help_text="Special instructions for this medicine")
    
    # Ordering
    order = models.IntegerField(default=0, help_text="Display order")
    
    class Meta:
        db_table = 'prescription_medicines'
        ordering = ['order', 'medicine_name']
        verbose_name = 'Prescription Medicine'
        verbose_name_plural = 'Prescription Medicines'
    
    def __str__(self):
        return f"{self.medicine_name} - {self.dosage}"
