from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class GovernmentScheme(models.Model):
    SCHEME_TYPES = [
        ('health', 'Health Insurance'),
        ('life', 'Life Insurance'),
        ('accident', 'Accident Cover'),
        ('pension', 'Pension Scheme'),
        ('education', 'Education Support'),
        ('agriculture', 'Agriculture Support'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    scheme_type = models.CharField(max_length=50, choices=SCHEME_TYPES)
    description = models.TextField()
    short_description = models.CharField(max_length=300)
    state = models.CharField(max_length=100, blank=True, null=True)
    coverage_amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Maximum coverage in INR")
    benefits = models.TextField(help_text="List of key benefits")
    required_documents = models.TextField(help_text="Documents needed for application")
    application_steps = models.TextField(help_text="Steps to apply")
    official_website = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Government Scheme'
        verbose_name_plural = 'Government Schemes'
    
    def __str__(self):
        return self.name


class Eligibility(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scheme = models.OneToOneField(GovernmentScheme, on_delete=models.CASCADE, related_name='eligibility_criteria')
    min_age = models.IntegerField(help_text="Minimum age requirement")
    max_age = models.IntegerField(help_text="Maximum age requirement")
    max_income = models.DecimalField(max_digits=12, decimal_places=2, help_text="Maximum annual income in INR", null=True, blank=True)
    state = models.CharField(max_length=100, blank=True, null=True, help_text="Specific state requirement")
    gender = models.CharField(max_length=20, blank=True, null=True, help_text="Gender requirement if any")
    additional_criteria = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Eligibility Criteria'
        verbose_name_plural = 'Eligibility Criteria'
    
    def __str__(self):
        return f"Eligibility for {self.scheme.name}"


class InsurancePolicy(models.Model):
    POLICY_TYPES = [
        ('health', 'Health Insurance'),
        ('life', 'Life Insurance'),
        ('accident', 'Accident Cover'),
        ('family', 'Family Plan'),
        ('senior', 'Senior Citizen Plan'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    policy_type = models.CharField(max_length=50, choices=POLICY_TYPES)
    description = models.TextField()
    short_description = models.CharField(max_length=300)
    premium_per_month = models.DecimalField(max_digits=10, decimal_places=2, help_text="Starting premium in INR")
    coverage_amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Maximum coverage in INR")
    key_features = models.TextField(help_text="Key features of the policy")
    cashless_hospitals = models.BooleanField(default=True)
    claim_support = models.BooleanField(default=True)
    add_ons_available = models.TextField(blank=True, null=True)
    min_age = models.IntegerField(default=18)
    max_age = models.IntegerField(default=65)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Insurance Policy'
        verbose_name_plural = 'Insurance Policies'
    
    def __str__(self):
        return self.name


class Application(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('documents_required', 'Documents Required'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application_id = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='insurance_applications')
    scheme = models.ForeignKey(GovernmentScheme, on_delete=models.SET_NULL, null=True, blank=True, related_name='applications')
    policy = models.ForeignKey(InsurancePolicy, on_delete=models.SET_NULL, null=True, blank=True, related_name='applications')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft')
    applicant_name = models.CharField(max_length=255)
    applicant_age = models.IntegerField()
    applicant_income = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    applicant_state = models.CharField(max_length=100)
    documents_uploaded = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True, null=True)
    admin_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Application'
        verbose_name_plural = 'Applications'
    
    def __str__(self):
        return f"{self.application_id} - {self.user.email}"
    
    def save(self, *args, **kwargs):
        if not self.application_id:
            # Generate unique application ID
            import random
            self.application_id = f"APP{random.randint(100000, 999999)}"
        super().save(*args, **kwargs)
