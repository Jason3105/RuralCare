"""
Medicine Identifier Models
Stores medicine identification records and analysis results
"""

from django.db import models
from django.conf import settings
import uuid

from authentication.supabase_storage import SupabaseStorage


def get_medicine_storage():
    """Return SupabaseStorage instance for medicine images."""
    try:
        return SupabaseStorage(bucket_name=getattr(settings, 'SUPABASE_STORAGE_BUCKET', 'media'))
    except Exception:
        # Fallback to default storage if Supabase is not configured
        from django.core.files.storage import default_storage
        return default_storage


class MedicineIdentification(models.Model):
    """Model to store medicine identification requests and results"""
    
    MEDICINE_FORM_CHOICES = [
        ('tablet', 'Tablet'),
        ('capsule', 'Capsule'),
        ('syrup', 'Syrup'),
        ('injection', 'Injection'),
        ('cream', 'Cream/Lotion'),
        ('ointment', 'Ointment'),
        ('drops', 'Drops'),
        ('inhaler', 'Inhaler'),
        ('powder', 'Powder'),
        ('gel', 'Gel'),
        ('spray', 'Spray'),
        ('patch', 'Patch'),
        ('suppository', 'Suppository'),
        ('other', 'Other'),
        ('unknown', 'Unknown'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('invalid_image', 'Invalid Image'),
    ]
    
    # Primary fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='medicine_identifications'
    )
    
    # Image fields
    image = models.ImageField(upload_to='medicine_images/', storage=get_medicine_storage)
    original_filename = models.CharField(max_length=255)
    supabase_image_url = models.URLField(max_length=1024, blank=True, null=True)
    
    # Processing status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Extracted text from image (OCR)
    extracted_text = models.TextField(blank=True, null=True)
    
    # Image analysis data (OpenCV results)
    image_analysis = models.JSONField(default=dict, blank=True)
    
    # Identified medicine details
    medicine_name = models.CharField(max_length=255, blank=True, null=True)
    generic_name = models.CharField(max_length=255, blank=True, null=True)
    brand_name = models.CharField(max_length=255, blank=True, null=True)
    manufacturer = models.CharField(max_length=255, blank=True, null=True)
    medicine_form = models.CharField(max_length=50, choices=MEDICINE_FORM_CHOICES, default='unknown')
    
    # Dosage information
    strength = models.CharField(max_length=100, blank=True, null=True)
    dosage_form = models.CharField(max_length=100, blank=True, null=True)
    
    # Comprehensive medicine information (from Groq AI)
    description = models.TextField(blank=True, null=True)
    uses = models.JSONField(default=list, blank=True)  # List of uses/indications
    side_effects = models.JSONField(default=list, blank=True)  # List of side effects
    warnings = models.JSONField(default=list, blank=True)  # List of warnings
    contraindications = models.JSONField(default=list, blank=True)  # List of contraindications
    drug_interactions = models.JSONField(default=list, blank=True)  # Drug interactions
    dosage_instructions = models.TextField(blank=True, null=True)
    storage_instructions = models.TextField(blank=True, null=True)
    
    # Additional AI-generated information
    active_ingredients = models.JSONField(default=list, blank=True)
    inactive_ingredients = models.JSONField(default=list, blank=True)
    drug_class = models.CharField(max_length=255, blank=True, null=True)
    prescription_required = models.BooleanField(null=True, blank=True)
    
    # Full AI response
    ai_analysis = models.JSONField(default=dict, blank=True)
    
    # Confidence scores
    ocr_confidence = models.FloatField(default=0.0)
    identification_confidence = models.FloatField(default=0.0)
    
    # Error handling
    error_message = models.TextField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processing_time_seconds = models.FloatField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Medicine Identification'
        verbose_name_plural = 'Medicine Identifications'
    
    def __str__(self):
        return f"{self.medicine_name or 'Unknown'} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class MedicineDatabase(models.Model):
    """
    Local database of known medicines for faster identification
    Can be populated over time from successful identifications
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Medicine identification
    medicine_name = models.CharField(max_length=255, db_index=True)
    generic_name = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    brand_names = models.JSONField(default=list, blank=True)  # List of brand names
    
    # Classification
    drug_class = models.CharField(max_length=255, blank=True, null=True)
    therapeutic_class = models.CharField(max_length=255, blank=True, null=True)
    
    # Visual characteristics (for ML matching)
    typical_colors = models.JSONField(default=list, blank=True)
    typical_shapes = models.JSONField(default=list, blank=True)
    typical_markings = models.JSONField(default=list, blank=True)
    
    # Medicine information
    description = models.TextField(blank=True, null=True)
    uses = models.JSONField(default=list, blank=True)
    side_effects = models.JSONField(default=list, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    identification_count = models.IntegerField(default=0)  # How many times identified
    
    class Meta:
        ordering = ['medicine_name']
        verbose_name = 'Medicine Database Entry'
        verbose_name_plural = 'Medicine Database Entries'
    
    def __str__(self):
        return self.medicine_name
