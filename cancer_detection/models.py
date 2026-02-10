from django.db import models
from django.contrib.auth import get_user_model
import uuid
import json

User = get_user_model()


class CancerImageAnalysis(models.Model):
    """Model to store uploaded images and their analysis results"""
    
    IMAGE_TYPE_CHOICES = [
        ('xray', 'X-Ray Scan'),
        ('ct', 'CT Scan'),
        ('mri', 'MRI Scan'),
        ('tumor', 'Tumor Image'),
        ('biopsy', 'Biopsy Image'),
        ('ultrasound', 'Ultrasound'),
        ('other', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cancer_analyses')
    image = models.ImageField(upload_to='cancer_images/%Y/%m/%d/')
    image_type = models.CharField(max_length=20, choices=IMAGE_TYPE_CHOICES, default='other')
    original_filename = models.CharField(max_length=255)
    
    # Analysis Results
    tumor_detected = models.BooleanField(default=False)
    tumor_type = models.CharField(max_length=100, null=True, blank=True)
    tumor_stage = models.CharField(max_length=50, null=True, blank=True)
    tumor_size_mm = models.FloatField(null=True, blank=True)
    tumor_location = models.CharField(max_length=200, null=True, blank=True)
    
    # Genetic Profile Indicators
    genetic_profile = models.JSONField(default=dict, blank=True)
    
    # Comorbidities
    comorbidities = models.JSONField(default=list, blank=True)
    
    # Detailed Analysis Data
    analysis_data = models.JSONField(default=dict, blank=True)  # Stores all OpenCV analysis results
    
    # Confidence scores
    detection_confidence = models.FloatField(default=0.0)
    stage_confidence = models.FloatField(default=0.0)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'cancer_image_analyses'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Analysis {self.id} - {self.user.username} - {self.created_at.strftime('%Y-%m-%d')}"


class PersonalizedTreatmentPlan(models.Model):
    """
    Model for storing AI-generated personalized cancer treatment plans.
    Integrates patient profile, tumor analysis, genetic profile, and treatment recommendations.
    """
    
    PLAN_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_review', 'Pending Oncologist Review'),
        ('approved', 'Approved by Oncologist'),
        ('active', 'Active/In Progress'),
        ('completed', 'Completed'),
        ('archived', 'Archived'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='treatment_plans')
    analysis = models.ForeignKey(CancerImageAnalysis, on_delete=models.SET_NULL, null=True, blank=True, 
                                  related_name='treatment_plans')
    
    # Plan Identification
    plan_name = models.CharField(max_length=200, null=True, blank=True)
    cancer_type = models.CharField(max_length=100)
    cancer_stage = models.CharField(max_length=50)
    
    # Patient Profile Data
    patient_profile = models.JSONField(default=dict)  # Age, comorbidities, performance status, etc.
    
    # Tumor Characteristics
    tumor_analysis = models.JSONField(default=dict)  # Size, grade, location, metastasis, etc.
    
    # Genetic & Biomarker Profile
    genetic_profile = models.JSONField(default=dict)  # Mutations, biomarkers, immunoprofile
    
    # Treatment Recommendations
    primary_treatments = models.JSONField(default=list)  # Primary treatment modalities
    adjuvant_treatments = models.JSONField(default=list)  # Adjuvant therapy options
    targeted_therapies = models.JSONField(default=list)  # Targeted therapy eligibility
    side_effects = models.JSONField(default=list)  # Expected side effects
    
    # Outcome Predictions
    predicted_5yr_survival = models.FloatField(null=True, blank=True)  # 5-year survival estimate
    remission_probability = models.FloatField(null=True, blank=True)  # % chance of remission
    quality_of_life_score = models.IntegerField(null=True, blank=True)  # QOL impact (0-100)
    
    # Monitoring & Follow-up
    monitoring_plan = models.JSONField(default=dict)  # Surveillance schedule
    expected_milestones = models.JSONField(default=list)  # Key treatment milestones
    
    # Patient Journey & Decision Support
    treatment_pathway = models.JSONField(default=dict)  # Phases, timeline, decision points
    clinical_trials = models.JSONField(default=list)  # Relevant clinical trial options
    
    # Contraindications & Considerations
    contraindications = models.JSONField(default=list)  # Drugs/treatments to avoid
    special_considerations = models.TextField(null=True, blank=True)  # Additional notes
    
    # Status & Review
    status = models.CharField(max_length=20, choices=PLAN_STATUS_CHOICES, default='draft')
    oncologist_notes = models.TextField(null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                     related_name='reviewed_plans')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    review_date = models.DateTimeField(null=True, blank=True)
    activated_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'personalized_treatment_plans'
        ordering = ['-created_at']
        verbose_name = 'Personalized Treatment Plan'
        verbose_name_plural = 'Personalized Treatment Plans'
    
    def __str__(self):
        return f"Treatment Plan - {self.patient.username} - {self.cancer_type} Stage {self.cancer_stage}"
    
    @property
    def is_pending_review(self):
        return self.status == 'pending_review'
    
    @property
    def is_approved(self):
        return self.status == 'approved'
    
    @property
    def is_active(self):
        return self.status == 'active'


class HistopathologyReport(models.Model):
    """
    Model for storing histopathology/pathology reports
    """
    
    REPORT_STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('analyzing', 'Analyzing'),
        ('analyzed', 'Analyzed'),
        ('error', 'Error'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='histopathology_reports')
    
    # Report file (PDF, image, or text)
    report_file = models.FileField(upload_to='histopathology_reports/%Y/%m/%d/', null=True, blank=True)
    report_text = models.TextField(null=True, blank=True)  # Extracted text from report
    
    # Analysis results
    status = models.CharField(max_length=20, choices=REPORT_STATUS_CHOICES, default='uploaded')
    analysis_results = models.JSONField(default=dict, blank=True)  # Full analysis from HistopathologyAnalyzer
    
    # Extracted information
    cancer_type = models.CharField(max_length=100, null=True, blank=True)
    cancer_subtype = models.CharField(max_length=200, null=True, blank=True)
    grade = models.CharField(max_length=50, null=True, blank=True)
    stage = models.CharField(max_length=50, null=True, blank=True)
    tnm_staging = models.CharField(max_length=50, null=True, blank=True)
    tumor_size_mm = models.FloatField(null=True, blank=True)
    margin_status = models.CharField(max_length=50, null=True, blank=True)
    lymph_node_status = models.JSONField(default=dict, blank=True)
    biomarkers = models.JSONField(default=dict, blank=True)  # ER, PR, HER2, Ki-67, etc.
    
    # Metadata
    report_date = models.DateField(null=True, blank=True)  # Date of original report
    pathologist_name = models.CharField(max_length=200, null=True, blank=True)
    hospital_lab = models.CharField(max_length=200, null=True, blank=True)
    
    # Confidence
    analysis_confidence = models.FloatField(default=0.0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    analyzed_at = models.DateTimeField(null=True, blank=True)
    
    # Notes
    notes = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'histopathology_reports'
        ordering = ['-created_at']
        verbose_name = 'Histopathology Report'
        verbose_name_plural = 'Histopathology Reports'
    
    def __str__(self):
        return f"Pathology Report - {self.patient.username} - {self.created_at.strftime('%Y-%m-%d')}"


class GenomicProfile(models.Model):
    """
    Model for storing comprehensive genomic profiles
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='genomic_profiles')
    
    # Genomic data
    mutations = models.JSONField(default=dict, blank=True)  # Gene mutations
    biomarkers = models.JSONField(default=dict, blank=True)  # Protein biomarkers
    copy_number_variations = models.JSONField(default=dict, blank=True)
    
    # Immunoprofile
    pd_l1_status = models.CharField(max_length=50, null=True, blank=True)
    pd_l1_percentage = models.FloatField(null=True, blank=True)
    msi_status = models.CharField(max_length=50, null=True, blank=True)
    tumor_mutational_burden = models.FloatField(null=True, blank=True)  # TMB in mutations/Mb
    immune_infiltration = models.CharField(max_length=50, null=True, blank=True)
    
    # Analysis results
    analysis_results = models.JSONField(default=dict, blank=True)  # Full analysis from GenomicsAnalyzer
    actionable_mutations = models.JSONField(default=list, blank=True)
    targeted_therapy_eligibility = models.JSONField(default=dict, blank=True)
    immunotherapy_eligibility = models.JSONField(default=dict, blank=True)
    prognostic_profile = models.JSONField(default=dict, blank=True)
    
    # Test information
    test_type = models.CharField(max_length=100, null=True, blank=True)  # NGS, PCR, IHC, etc.
    test_date = models.DateField(null=True, blank=True)
    lab_name = models.CharField(max_length=200, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    analyzed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'genomic_profiles'
        ordering = ['-created_at']
        verbose_name = 'Genomic Profile'
        verbose_name_plural = 'Genomic Profiles'
    
    def __str__(self):
        return f"Genomic Profile - {self.patient.username} - {self.created_at.strftime('%Y-%m-%d')}"


class TreatmentOutcome(models.Model):
    """
    Model for tracking treatment outcomes and real-world data
    """
    
    OUTCOME_STATUS_CHOICES = [
        ('ongoing', 'Treatment Ongoing'),
        ('completed', 'Treatment Completed'),
        ('discontinued', 'Treatment Discontinued'),
        ('follow_up', 'In Follow-up'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='treatment_outcomes')
    treatment_plan = models.ForeignKey(PersonalizedTreatmentPlan, on_delete=models.CASCADE, 
                                       related_name='outcomes', null=True, blank=True)
    
    # Outcome data
    status = models.CharField(max_length=20, choices=OUTCOME_STATUS_CHOICES, default='ongoing')
    treatment_response = models.CharField(max_length=50, null=True, blank=True)  # CR, PR, SD, PD
    response_date = models.DateField(null=True, blank=True)
    
    # Survival data
    progression_free_survival_days = models.IntegerField(null=True, blank=True)
    overall_survival_days = models.IntegerField(null=True, blank=True)
    
    # Quality of life
    quality_of_life_score = models.IntegerField(null=True, blank=True)  # 0-100
    quality_of_life_date = models.DateField(null=True, blank=True)
    
    # Side effects experienced
    side_effects_experienced = models.JSONField(default=list, blank=True)
    side_effects_severity = models.JSONField(default=dict, blank=True)
    
    # Predicted vs actual
    predicted_survival = models.FloatField(null=True, blank=True)
    predicted_response = models.FloatField(null=True, blank=True)
    actual_survival = models.FloatField(null=True, blank=True)
    actual_response = models.CharField(max_length=50, null=True, blank=True)
    
    # Notes
    notes = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'treatment_outcomes'
        ordering = ['-created_at']
        verbose_name = 'Treatment Outcome'
        verbose_name_plural = 'Treatment Outcomes'
    
    def __str__(self):
        return f"Outcome - {self.patient.username} - {self.status}"