from django.db import models
from django.contrib.auth import get_user_model
import uuid
import json
from django.utils import timezone

User = get_user_model()


class AIConfidenceMetadata(models.Model):
    """
    Stores AI confidence scores and uncertainty data for all AI outputs.
    Doctor-only access for full breakdown.
    """
    
    ANALYSIS_TYPE_CHOICES = [
        ('imaging', 'Imaging Analysis'),
        ('histopathology', 'Histopathology Extraction'),
        ('genomic', 'Genomic Analysis'),
        ('treatment_plan', 'Treatment Plan'),
        ('outcome_prediction', 'Outcome Prediction'),
    ]
    
    CONFIDENCE_LEVEL_CHOICES = [
        ('high', 'High Confidence'),
        ('moderate', 'Moderate Confidence'),
        ('low', 'Low Confidence'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_confidence_records')
    
    # Link to source analysis
    analysis_type = models.CharField(max_length=30, choices=ANALYSIS_TYPE_CHOICES)
    source_id = models.UUIDField(null=True, blank=True)  # ID of the source analysis/plan
    
    # Confidence Scores (0-100)
    overall_confidence = models.FloatField(default=0.0)
    data_quality_score = models.FloatField(default=0.0)
    model_certainty_score = models.FloatField(default=0.0)
    evidence_strength_score = models.FloatField(default=0.0)
    
    # Simplified level for patient view
    confidence_level = models.CharField(max_length=20, choices=CONFIDENCE_LEVEL_CHOICES, default='moderate')
    
    # Uncertainty reasons (JSON list)
    uncertainty_reasons = models.JSONField(default=list, blank=True)
    # Example: ["Missing genomic data", "Low OCR quality (65%)", "Conflicting biomarker results"]
    
    # Missing data sources
    missing_data_sources = models.JSONField(default=list, blank=True)
    # Example: ["Genomic profile", "Recent lab values", "PET scan"]
    
    # Conflicting modality outputs
    conflicting_outputs = models.JSONField(default=list, blank=True)
    # Example: [{"source1": "Imaging", "source2": "Pathology", "conflict": "Stage mismatch"}]
    
    # OCR quality for document-based analyses
    ocr_quality_score = models.FloatField(null=True, blank=True)
    
    # Evidence strength breakdown
    evidence_breakdown = models.JSONField(default=dict, blank=True)
    # Example: {"clinical_trials": 3, "guidelines": 2, "case_studies": 5, "expert_opinion": 1}
    
    # Detailed explanation for doctors
    detailed_explanation = models.TextField(null=True, blank=True)
    
    # Plain language explanation for patients
    patient_explanation = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ai_confidence_metadata'
        ordering = ['-created_at']
        verbose_name = 'AI Confidence Metadata'
        verbose_name_plural = 'AI Confidence Metadata'
    
    def __str__(self):
        return f"Confidence: {self.analysis_type} - {self.patient.username} - {self.overall_confidence}%"
    
    def get_color_indicator(self):
        """Returns color indicator based on confidence level"""
        if self.overall_confidence >= 80:
            return 'green'
        elif self.overall_confidence >= 50:
            return 'amber'
        return 'red'
    
    def calculate_confidence_level(self):
        """Calculate and set confidence level based on score"""
        if self.overall_confidence >= 80:
            self.confidence_level = 'high'
        elif self.overall_confidence >= 50:
            self.confidence_level = 'moderate'
        else:
            self.confidence_level = 'low'
        return self.confidence_level


class XAIExplanation(models.Model):
    """
    Explainable AI (XAI) data for treatment recommendations.
    Stores ranked contributing factors with influence percentages.
    Doctor-only access.
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    treatment_plan = models.ForeignKey('cancer_detection.PersonalizedTreatmentPlan', 
                                        on_delete=models.CASCADE, related_name='xai_explanations')
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='xai_explanations')
    
    # Ranked contributing factors with influence percentages
    contributing_factors = models.JSONField(default=list)
    # Example: [
    #   {"rank": 1, "factor": "Tumor Stage", "value": "Stage IIIA", "influence": 28.5},
    #   {"rank": 2, "factor": "EGFR Mutation", "value": "Positive", "influence": 22.3},
    #   {"rank": 3, "factor": "PD-L1 Expression", "value": "High (80%)", "influence": 18.7},
    # ]
    
    # Detailed factor breakdowns
    tumor_factors = models.JSONField(default=dict, blank=True)
    # {"stage": "IIIA", "grade": 2, "size_mm": 45, "location": "Right upper lobe", "influence": 35}
    
    genomic_factors = models.JSONField(default=dict, blank=True)
    # {"EGFR": {"status": "mutated", "variant": "L858R", "influence": 22}, "KRAS": {...}}
    
    biomarker_factors = models.JSONField(default=dict, blank=True)
    # {"PD-L1": {"value": 80, "unit": "%", "influence": 15}, "Ki-67": {...}}
    
    comorbidity_factors = models.JSONField(default=dict, blank=True)
    # {"diabetes": {"present": true, "influence": 8}, "hypertension": {...}}
    
    # Treatment recommendation summary
    recommendation_summary = models.TextField(null=True, blank=True)
    
    # Deterministic explanation text
    explanation_text = models.TextField(null=True, blank=True)
    
    # Structured JSON for programmatic access
    structured_explanation = models.JSONField(default=dict, blank=True)
    
    # Disclaimer
    disclaimer = models.TextField(default="This is clinical decision support only. Final treatment decisions should be made by qualified healthcare professionals in consultation with the patient.")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'xai_explanations'
        ordering = ['-created_at']
        verbose_name = 'XAI Explanation'
        verbose_name_plural = 'XAI Explanations'
    
    def __str__(self):
        return f"XAI: {self.treatment_plan} - {self.patient.username}"


class TumorBoardSession(models.Model):
    """
    Multidisciplinary Tumor Board session for collaborative treatment planning.
    Doctor-only access.
    """
    
    SESSION_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('in_review', 'In Review'),
        ('consensus_achieved', 'Consensus Achieved'),
        ('closed', 'Closed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Session details
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    
    # Patient and treatment plan
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tumor_board_sessions')
    treatment_plan = models.ForeignKey('cancer_detection.PersonalizedTreatmentPlan', 
                                        on_delete=models.CASCADE, related_name='tumor_board_sessions')
    
    # Session creator
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tumor_boards')
    
    # Status
    status = models.CharField(max_length=20, choices=SESSION_STATUS_CHOICES, default='draft')
    
    # Scheduled time
    scheduled_at = models.DateTimeField(null=True, blank=True)
    
    # Consensus tracking
    consensus_reached = models.BooleanField(default=False)
    consensus_date = models.DateTimeField(null=True, blank=True)
    final_recommendation = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tumor_board_sessions'
        ordering = ['-created_at']
        verbose_name = 'Tumor Board Session'
        verbose_name_plural = 'Tumor Board Sessions'
    
    def __str__(self):
        return f"Tumor Board: {self.title} - {self.patient.username}"
    
    def can_activate_plan(self):
        """Check if treatment plan can be activated"""
        return self.consensus_reached and self.status == 'consensus_achieved'


class TumorBoardMember(models.Model):
    """
    Members invited to a tumor board session with their roles.
    """
    
    ROLE_CHOICES = [
        ('medical_oncologist', 'Medical Oncologist'),
        ('surgical_oncologist', 'Surgical Oncologist'),
        ('radiation_oncologist', 'Radiation Oncologist'),
        ('pathologist', 'Pathologist'),
        ('radiologist', 'Radiologist'),
        ('geneticist', 'Geneticist'),
        ('palliative_care', 'Palliative Care Specialist'),
        ('other', 'Other Specialist'),
    ]
    
    DECISION_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('suggested_modification', 'Suggested Modification'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(TumorBoardSession, on_delete=models.CASCADE, related_name='members')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tumor_board_memberships')
    
    # Role in the session
    role = models.CharField(max_length=30, choices=ROLE_CHOICES)
    
    # Decision
    decision = models.CharField(max_length=25, choices=DECISION_CHOICES, default='pending')
    decision_date = models.DateTimeField(null=True, blank=True)
    
    # Comments
    comments = models.TextField(null=True, blank=True)
    suggested_modifications = models.JSONField(default=list, blank=True)
    
    # Invitation
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'tumor_board_members'
        unique_together = ['session', 'doctor']
        verbose_name = 'Tumor Board Member'
        verbose_name_plural = 'Tumor Board Members'
    
    def __str__(self):
        return f"{self.doctor.username} - {self.role} - {self.session.title}"


class TumorBoardAuditLog(models.Model):
    """
    Immutable audit log for tumor board activities.
    """
    
    ACTION_CHOICES = [
        ('session_created', 'Session Created'),
        ('member_invited', 'Member Invited'),
        ('member_accepted', 'Member Accepted'),
        ('comment_added', 'Comment Added'),
        ('decision_made', 'Decision Made'),
        ('status_changed', 'Status Changed'),
        ('consensus_reached', 'Consensus Reached'),
        ('plan_activated', 'Plan Activated'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(TumorBoardSession, on_delete=models.CASCADE, related_name='audit_logs')
    
    # Action details
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='tumor_board_actions')
    
    # Details
    details = models.JSONField(default=dict, blank=True)
    previous_state = models.JSONField(null=True, blank=True)
    new_state = models.JSONField(null=True, blank=True)
    
    # Timestamp (immutable)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # IP and user agent for security
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'tumor_board_audit_logs'
        ordering = ['-timestamp']
        verbose_name = 'Tumor Board Audit Log'
        verbose_name_plural = 'Tumor Board Audit Logs'
    
    def __str__(self):
        return f"{self.action} - {self.session.title} - {self.timestamp}"


class ToxicityPrediction(models.Model):
    """
    Drug toxicity and adverse event predictions with CTCAE grading.
    Doctor-only full access.
    """
    
    CTCAE_GRADE_CHOICES = [
        (1, 'Grade 1 - Mild'),
        (2, 'Grade 2 - Moderate'),
        (3, 'Grade 3 - Severe'),
        (4, 'Grade 4 - Life-threatening'),
    ]
    
    RISK_LEVEL_CHOICES = [
        ('low', 'Low Risk'),
        ('moderate', 'Moderate Risk'),
        ('high', 'High Risk'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='toxicity_predictions')
    treatment_plan = models.ForeignKey('cancer_detection.PersonalizedTreatmentPlan', 
                                        on_delete=models.CASCADE, related_name='toxicity_predictions',
                                        null=True, blank=True)
    
    # Drug information
    drug_name = models.CharField(max_length=200)
    drug_class = models.CharField(max_length=100, null=True, blank=True)
    
    # Toxicity predictions (JSON list of toxicities)
    predicted_toxicities = models.JSONField(default=list)
    # Example: [
    #   {"toxicity": "Neutropenia", "probability": 0.45, "ctcae_grade": 3, "onset_days": "7-14"},
    #   {"toxicity": "Nausea", "probability": 0.72, "ctcae_grade": 2, "onset_days": "1-3"},
    # ]
    
    # High-risk toxicities (flagged for attention)
    high_risk_toxicities = models.JSONField(default=list, blank=True)
    
    # Overall risk level
    overall_risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, default='moderate')
    
    # Dose adjustment recommendations
    dose_adjustments = models.JSONField(default=list, blank=True)
    # Example: [{"current_dose": "150mg", "recommended_dose": "100mg", "reason": "Renal impairment"}]
    
    # Correlated lab values
    correlated_lab_values = models.JSONField(default=dict, blank=True)
    # Example: {"creatinine": {"value": 1.8, "unit": "mg/dL", "status": "elevated", "impact": "Increased nephrotoxicity risk"}}
    
    # AI Confidence for predictions
    prediction_confidence = models.FloatField(default=0.0)
    
    # Patient-friendly summary
    patient_summary = models.TextField(null=True, blank=True)
    
    # Doctor notes
    doctor_notes = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'toxicity_predictions'
        ordering = ['-created_at']
        verbose_name = 'Toxicity Prediction'
        verbose_name_plural = 'Toxicity Predictions'
    
    def __str__(self):
        return f"Toxicity: {self.drug_name} - {self.patient.username}"
    
    def get_risk_color(self):
        """Returns color based on risk level"""
        colors = {'low': 'green', 'moderate': 'amber', 'high': 'red'}
        return colors.get(self.overall_risk_level, 'gray')


class DoctorSymptomMonitor(models.Model):
    """
    Doctor's view of patient symptom monitoring.
    Read-only for doctors, linked to patient symptom logs.
    """
    
    ALERT_STATUS_CHOICES = [
        ('none', 'No Alert'),
        ('attention', 'Needs Attention'),
        ('urgent', 'Urgent'),
        ('critical', 'Critical'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='symptom_monitors')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='monitored_patients')
    treatment_plan = models.ForeignKey('cancer_detection.PersonalizedTreatmentPlan', 
                                        on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='symptom_monitors')
    
    # Current alert status
    alert_status = models.CharField(max_length=20, choices=ALERT_STATUS_CHOICES, default='none')
    
    # Latest symptom summary
    latest_symptoms = models.JSONField(default=list, blank=True)
    
    # Threshold breaches
    threshold_breaches = models.JSONField(default=list, blank=True)
    # Example: [{"symptom": "Pain", "reported": 8, "threshold": 6, "date": "2025-12-18"}]
    
    # Treatment phase correlation
    current_treatment_phase = models.CharField(max_length=100, null=True, blank=True)
    phase_correlation = models.JSONField(default=dict, blank=True)
    
    # Doctor notes and interventions
    doctor_notes = models.TextField(null=True, blank=True)
    interventions = models.JSONField(default=list, blank=True)
    # Example: [{"date": "2025-12-18", "intervention": "Adjusted pain medication", "doctor": "Dr. Smith"}]
    
    # Last review
    last_reviewed_at = models.DateTimeField(null=True, blank=True)
    last_reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                          related_name='reviewed_symptom_monitors')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'doctor_symptom_monitors'
        unique_together = ['patient', 'doctor']
        ordering = ['-updated_at']
        verbose_name = 'Doctor Symptom Monitor'
        verbose_name_plural = 'Doctor Symptom Monitors'
    
    def __str__(self):
        return f"Monitor: {self.patient.username} by Dr. {self.doctor.username}"
    
    def get_alert_color(self):
        """Returns color based on alert status"""
        colors = {'none': 'green', 'attention': 'amber', 'urgent': 'orange', 'critical': 'red'}
        return colors.get(self.alert_status, 'gray')
