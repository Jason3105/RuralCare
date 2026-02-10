"""
Evidence Traceability Engine Models
Stores clinical guideline references, PubMed studies, and links evidence to treatment recommendations
"""

from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class EvidenceSource(models.Model):
    """
    Model for storing evidence sources (clinical guidelines, PubMed papers, etc.)
    """
    
    SOURCE_TYPE_CHOICES = [
        ('nccn_guideline', 'NCCN Guideline'),
        ('esmo_guideline', 'ESMO Guideline'),
        ('asco_guideline', 'ASCO Guideline'),
        ('pubmed_study', 'PubMed Study'),
        ('clinical_trial', 'Clinical Trial'),
        ('case_report', 'Case Report'),
        ('systematic_review', 'Systematic Review'),
        ('meta_analysis', 'Meta-Analysis'),
        ('other', 'Other'),
    ]
    
    EVIDENCE_STRENGTH_CHOICES = [
        ('high', 'High - Category 1'),
        ('moderate', 'Moderate - Category 2A/2B'),
        ('low', 'Low - Category 3'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identification
    title = models.CharField(max_length=500)
    source_type = models.CharField(max_length=50, choices=SOURCE_TYPE_CHOICES)
    
    # Evidence details
    authors = models.CharField(max_length=500, null=True, blank=True)
    publication_year = models.IntegerField(null=True, blank=True)
    journal_or_organization = models.CharField(max_length=300, null=True, blank=True)
    
    # PubMed specific
    pmid = models.CharField(max_length=50, null=True, blank=True, unique=True, db_index=True)
    doi = models.CharField(max_length=100, null=True, blank=True)
    
    # Guideline specific
    guideline_version = models.CharField(max_length=100, null=True, blank=True)
    guideline_url = models.URLField(null=True, blank=True)
    
    # Content
    abstract = models.TextField(null=True, blank=True)
    key_findings = models.TextField(null=True, blank=True)
    
    # Evidence strength
    evidence_strength = models.CharField(max_length=20, choices=EVIDENCE_STRENGTH_CHOICES, default='moderate')
    
    # Relevance tags
    cancer_types = models.JSONField(default=list, blank=True)  # List of cancer types this applies to
    treatment_types = models.JSONField(default=list, blank=True)  # Treatment modalities covered
    biomarkers = models.JSONField(default=list, blank=True)  # Biomarkers/mutations discussed
    
    # Full text/PDF
    full_text = models.TextField(null=True, blank=True)
    pdf_url = models.URLField(null=True, blank=True)
    
    # Embeddings for semantic search (stored as JSONB for compatibility)
    embedding = models.JSONField(null=True, blank=True)  # Vector embedding for similarity search
    
    # Metadata
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_indexed = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'evidence_sources'
        ordering = ['-publication_year', '-created_at']
        verbose_name = 'Evidence Source'
        verbose_name_plural = 'Evidence Sources'
        indexes = [
            models.Index(fields=['pmid']),
            models.Index(fields=['source_type']),
            models.Index(fields=['evidence_strength']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.source_type}) - {self.evidence_strength}"


class RecommendationEvidence(models.Model):
    """
    Model linking treatment recommendations to their supporting evidence
    Tracks which evidence supports which recommendation
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Link to recommendation
    treatment_plan = models.ForeignKey('PersonalizedTreatmentPlan', on_delete=models.CASCADE, 
                                       related_name='recommendation_evidences')
    
    # Recommendation details
    recommendation_type = models.CharField(max_length=200)  # e.g., 'Chemotherapy', 'Targeted Therapy'
    recommendation_text = models.TextField()
    
    # Supporting evidence
    evidence_sources = models.ManyToManyField(EvidenceSource, through='EvidenceLink')
    
    # Evidence quality metrics
    total_evidence_score = models.FloatField(default=0.0)  # Aggregate strength score (0-1)
    high_strength_count = models.IntegerField(default=0)
    moderate_strength_count = models.IntegerField(default=0)
    low_strength_count = models.IntegerField(default=0)
    
    # Decision factors
    decision_factors = models.JSONField(default=dict)  # Patient features influencing decision
    
    # Confidence
    recommendation_confidence = models.FloatField(default=0.0)  # 0-1 scale
    alternative_recommendations = models.JSONField(default=list, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'recommendation_evidences'
        ordering = ['-created_at']
        verbose_name = 'Recommendation Evidence'
        verbose_name_plural = 'Recommendation Evidences'
    
    def __str__(self):
        return f"Evidence for {self.recommendation_type} - {self.treatment_plan.patient.username}"
    
    def calculate_evidence_score(self):
        """Calculate aggregate evidence strength score"""
        total_score = 0
        total_evidence = 0
        
        for link in self.evidence_link_set.all():
            evidence = link.evidence_source
            # Weight by evidence strength
            strength_weight = {'high': 1.0, 'moderate': 0.6, 'low': 0.3}
            weight = strength_weight.get(evidence.evidence_strength, 0.5)
            total_score += weight * link.relevance_score
            total_evidence += 1
        
        if total_evidence > 0:
            self.total_evidence_score = total_score / total_evidence
        else:
            self.total_evidence_score = 0.0
        
        return self.total_evidence_score


class EvidenceLink(models.Model):
    """
    Through model for linking recommendations to evidence sources
    Tracks relevance and how evidence supports recommendation
    """
    
    RELEVANCE_TYPES = [
        ('directly_supports', 'Directly Supports'),
        ('partially_supports', 'Partially Supports'),
        ('comparative_evidence', 'Comparative Evidence'),
        ('contraindication', 'Contraindication'),
        ('related_finding', 'Related Finding'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    recommendation_evidence = models.ForeignKey(RecommendationEvidence, on_delete=models.CASCADE)
    evidence_source = models.ForeignKey(EvidenceSource, on_delete=models.CASCADE)
    
    # Relevance info
    relevance_type = models.CharField(max_length=50, choices=RELEVANCE_TYPES, default='directly_supports')
    relevance_score = models.FloatField(default=0.8)  # 0-1 scale, higher = more relevant
    
    # Explanation
    how_evidence_supports = models.TextField(null=True, blank=True)  # Narrative of connection
    relevant_excerpts = models.JSONField(default=list, blank=True)  # Quotes from evidence
    
    # Impact
    impact_percentage = models.FloatField(default=0.0)  # % impact on recommendation (0-100)
    
    class Meta:
        db_table = 'evidence_links'
        unique_together = ['recommendation_evidence', 'evidence_source']
        verbose_name = 'Evidence Link'
        verbose_name_plural = 'Evidence Links'
    
    def __str__(self):
        return f"{self.recommendation_evidence.recommendation_type} <- {self.evidence_source.title}"


class EvidenceExplanationLog(models.Model):
    """
    Audit log for evidence explanations shown to users
    Tracks when and how evidence was retrieved and presented
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='evidence_explanations')
    treatment_plan = models.ForeignKey('PersonalizedTreatmentPlan', on_delete=models.CASCADE)
    recommendation_evidence = models.ForeignKey(RecommendationEvidence, on_delete=models.SET_NULL, 
                                               null=True, blank=True)
    
    # Request details
    explanation_type = models.CharField(max_length=50)  # 'full', 'summary', 'citations_only'
    
    # Response details
    explanation_returned = models.JSONField(default=dict)  # What was returned
    sources_shown = models.ManyToManyField(EvidenceSource)
    
    # User interaction
    was_helpful = models.BooleanField(null=True, blank=True)  # Feedback
    user_feedback = models.TextField(null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    response_time_ms = models.IntegerField(null=True, blank=True)
    
    class Meta:
        db_table = 'evidence_explanation_logs'
        ordering = ['-created_at']
        verbose_name = 'Evidence Explanation Log'
        verbose_name_plural = 'Evidence Explanation Logs'
    
    def __str__(self):
        return f"Explanation for {self.treatment_plan.patient.username} - {self.created_at}"


class RuleBasedReference(models.Model):
    """
    Fallback rule-based references for when RAG/LLM is unavailable
    Maps treatment recommendations to evidence using deterministic rules
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Rule identification
    rule_name = models.CharField(max_length=200, unique=True)
    description = models.TextField()
    
    # Conditions
    cancer_type = models.CharField(max_length=100)
    cancer_stage = models.CharField(max_length=50, null=True, blank=True)
    biomarker_requirement = models.JSONField(default=dict, blank=True)  # Biomarkers required
    
    # Recommendations
    recommended_treatment = models.CharField(max_length=200)
    
    # Associated evidence
    guideline_references = models.JSONField(default=list)  # NCCN, ESMO, ASCO guidelines
    pubmed_references = models.JSONField(default=list)  # PMID numbers
    
    # Evidence strength
    evidence_strength = models.CharField(max_length=20, choices=EvidenceSource.EVIDENCE_STRENGTH_CHOICES, 
                                        default='moderate')
    
    # Rule logic
    rule_logic = models.TextField()  # Explain the rule
    priority_level = models.IntegerField(default=0)  # 1 = highest priority
    
    is_active = models.BooleanField(default=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name='created_rules')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rule_based_references'
        ordering = ['-priority_level', 'cancer_type']
        verbose_name = 'Rule-Based Reference'
        verbose_name_plural = 'Rule-Based References'
    
    def __str__(self):
        return f"{self.rule_name} - {self.cancer_type} Stage {self.cancer_stage}"
