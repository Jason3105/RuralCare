"""
Evidence Traceability Engine - Web Views (HTML Rendering)

Provides HTML-based views for displaying evidence, explanations, and decision factors
to patients and healthcare providers.
"""

import json
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils.html import escape
from django.urls import reverse

from authentication.models import User, DoctorProfile, PatientProfile
from .models import (
    CancerImageAnalysis, 
    PersonalizedTreatmentPlan
)
from .evidence_models import (
    EvidenceSource, 
    RecommendationEvidence,
    EvidenceExplanationLog,
    RuleBasedReference
)
from .evidence_integration import EvidenceIntegratedPlanner, RecommendationFactorAnalyzer
from .rule_based_references import RuleBasedReferenceManager


@login_required
def treatment_plan_with_evidence(request, plan_id):
    """
    Display treatment plan with evidence explanations.
    Shows recommendations with citations, strength scores, and decision factors.
    """
    treatment_plan = get_object_or_404(PersonalizedTreatmentPlan, id=plan_id)
    
    # Check access permissions
    if request.user != treatment_plan.patient.user and not request.user.doctorprofile:
        return HttpResponse("Unauthorized", status=403)
    
    # Get all recommendations with evidence
    planner = EvidenceIntegratedPlanner()
    recommendations_with_evidence = []
    
    try:
        for recommendation in treatment_plan.treatment_recommendations.all():
            try:
                rec_evidence = RecommendationEvidence.objects.get(
                    treatment_plan=treatment_plan,
                    recommendation_text=recommendation.recommendation_text
                )
                explanation = planner.get_recommendation_explanation(rec_evidence)
                recommendations_with_evidence.append({
                    'recommendation': recommendation,
                    'evidence': rec_evidence,
                    'explanation': explanation,
                    'has_evidence': True
                })
            except RecommendationEvidence.DoesNotExist:
                recommendations_with_evidence.append({
                    'recommendation': recommendation,
                    'evidence': None,
                    'explanation': None,
                    'has_evidence': False
                })
    except Exception as e:
        print(f"Error loading evidence: {str(e)}")
    
    context = {
        'treatment_plan': treatment_plan,
        'recommendations': recommendations_with_evidence,
        'patient': treatment_plan.patient,
        'is_doctor': request.user.is_staff or hasattr(request.user, 'doctorprofile'),
        'is_patient': hasattr(request.user, 'patientprofile'),
    }
    
    return render(request, 'cancer_detection/treatment_plan_with_evidence.html', context)


@login_required
def evidence_explanation_detail(request, plan_id, rec_evidence_id):
    """
    Display detailed evidence explanation for a specific recommendation.
    Shows all citations, evidence strength, and decision factors.
    """
    treatment_plan = get_object_or_404(PersonalizedTreatmentPlan, id=plan_id)
    rec_evidence = get_object_or_404(RecommendationEvidence, id=rec_evidence_id)
    
    # Check access
    if request.user != treatment_plan.patient.user and not request.user.doctorprofile:
        return HttpResponse("Unauthorized", status=403)
    
    if rec_evidence.treatment_plan != treatment_plan:
        return HttpResponse("Invalid recommendation", status=400)
    
    # Get detailed explanation
    planner = EvidenceIntegratedPlanner()
    explanation = planner.get_recommendation_explanation(rec_evidence)
    
    # Get decision factors
    analyzer = RecommendationFactorAnalyzer()
    decision_factors = analyzer.analyze_decision_factors(
        treatment_plan.patient,
        rec_evidence.recommendation_text
    )
    
    # Get related evidence sources with details
    evidence_links = rec_evidence.evidencelink_set.all().select_related('evidence_source')
    evidence_sources = [
        {
            'source': link.evidence_source,
            'link': link,
            'relevance_type': link.relevance_type,
            'relevance_score': link.relevance_score,
            'impact_percentage': link.impact_percentage,
            'excerpts': link.relevant_excerpts
        }
        for link in evidence_links
    ]
    
    # Get explanation history
    history = EvidenceExplanationLog.objects.filter(
        treatment_plan=treatment_plan,
        recommendation_evidence=rec_evidence
    ).order_by('-created_at')[:10]
    
    # Get feedback statistics
    helpful_count = EvidenceExplanationLog.objects.filter(
        treatment_plan=treatment_plan,
        was_helpful=True
    ).count()
    total_views = EvidenceExplanationLog.objects.filter(
        treatment_plan=treatment_plan
    ).count()
    
    context = {
        'treatment_plan': treatment_plan,
        'rec_evidence': rec_evidence,
        'explanation': explanation,
        'decision_factors': decision_factors,
        'evidence_sources': evidence_sources,
        'history': history,
        'helpful_percentage': (helpful_count / total_views * 100) if total_views > 0 else 0,
        'total_views': total_views,
        'is_doctor': request.user.is_staff or hasattr(request.user, 'doctorprofile'),
    }
    
    return render(request, 'cancer_detection/evidence_explanation_detail.html', context)


@login_required
def evidence_search(request):
    """
    Search for evidence sources with full-text search and filtering.
    Allows users to browse available clinical evidence.
    """
    query = request.GET.get('q', '')
    evidence_type = request.GET.get('type', '')
    strength = request.GET.get('strength', '')
    cancer_type = request.GET.get('cancer', '')
    page_num = request.GET.get('page', 1)
    
    # Base queryset
    evidence_sources = EvidenceSource.objects.filter(is_active=True)
    
    # Apply filters
    if query:
        evidence_sources = evidence_sources.filter(
            Q(title__icontains=query) |
            Q(authors__icontains=query) |
            Q(abstract__icontains=query) |
            Q(pmid__icontains=query)
        )
    
    if evidence_type:
        evidence_sources = evidence_sources.filter(source_type=evidence_type)
    
    if strength:
        evidence_sources = evidence_sources.filter(evidence_strength=strength)
    
    if cancer_type:
        # JSON array field filter
        evidence_sources = evidence_sources.filter(cancer_types__contains=cancer_type)
    
    # Pagination
    paginator = Paginator(evidence_sources, 20)
    page_obj = paginator.get_page(page_num)
    
    # Get available filters
    source_types = EvidenceSource.objects.filter(is_active=True).values_list(
        'source_type', flat=True
    ).distinct()
    strength_choices = ['High', 'Moderate', 'Low']
    
    context = {
        'page_obj': page_obj,
        'evidence_sources': page_obj.object_list,
        'query': query,
        'selected_type': evidence_type,
        'selected_strength': strength,
        'selected_cancer': cancer_type,
        'source_types': source_types,
        'strength_choices': strength_choices,
        'total_count': paginator.count,
    }
    
    return render(request, 'cancer_detection/evidence_search.html', context)


@login_required
def evidence_source_detail(request, source_id):
    """
    Display detailed information about a specific evidence source.
    Shows full abstract, metadata, related recommendations, and usage statistics.
    """
    evidence_source = get_object_or_404(EvidenceSource, id=source_id)
    
    # Get related recommendations
    related_links = evidence_source.evidencelink_set.all().select_related(
        'recommendation_evidence__treatment_plan__patient'
    )
    related_recommendations = [link.recommendation_evidence for link in related_links]
    
    # Get usage statistics
    usage_count = related_links.count()
    average_impact = 0
    if usage_count > 0:
        average_impact = sum([
            link.impact_percentage for link in related_links
        ]) / usage_count
    
    # Parse cancer types and treatment types
    cancer_types = evidence_source.cancer_types if evidence_source.cancer_types else []
    treatment_types = evidence_source.treatment_types if evidence_source.treatment_types else []
    
    context = {
        'evidence_source': evidence_source,
        'related_recommendations': related_recommendations,
        'usage_count': usage_count,
        'average_impact': average_impact,
        'cancer_types': cancer_types,
        'treatment_types': treatment_types,
        'related_links': related_links,
    }
    
    return render(request, 'cancer_detection/evidence_source_detail.html', context)


@login_required
def decision_factors_breakdown(request, plan_id, rec_evidence_id):
    """
    Display breakdown of decision factors for a specific recommendation.
    Shows which patient characteristics influenced the treatment choice.
    """
    treatment_plan = get_object_or_404(PersonalizedTreatmentPlan, id=plan_id)
    rec_evidence = get_object_or_404(RecommendationEvidence, id=rec_evidence_id)
    
    # Check access
    if request.user != treatment_plan.patient.user and not request.user.doctorprofile:
        return HttpResponse("Unauthorized", status=403)
    
    # Get decision factors
    analyzer = RecommendationFactorAnalyzer()
    decision_factors = analyzer.analyze_decision_factors(
        treatment_plan.patient,
        rec_evidence.recommendation_text
    )
    
    # Parse factors from JSON
    factors_list = []
    if rec_evidence.decision_factors:
        for factor_name, influence_score in rec_evidence.decision_factors.items():
            # Get patient's actual value for this factor
            patient_value = _get_patient_factor_value(treatment_plan.patient, factor_name)
            factors_list.append({
                'name': factor_name,
                'influence_score': influence_score,
                'patient_value': patient_value,
                'percentage': int(influence_score * 100),
            })
    
    # Sort by influence score (descending)
    factors_list.sort(key=lambda x: x['influence_score'], reverse=True)
    
    context = {
        'treatment_plan': treatment_plan,
        'rec_evidence': rec_evidence,
        'decision_factors': factors_list,
        'total_factors': len(factors_list),
        'recommendation_text': rec_evidence.recommendation_text,
        'evidence_strength': rec_evidence.total_evidence_score,
    }
    
    return render(request, 'cancer_detection/decision_factors_breakdown.html', context)


@login_required
def evidence_statistics(request, plan_id):
    """
    Display overall evidence statistics for a treatment plan.
    Shows evidence coverage, quality metrics, and audit trail.
    """
    treatment_plan = get_object_or_404(PersonalizedTreatmentPlan, id=plan_id)
    
    # Check access
    if request.user != treatment_plan.patient.user and not request.user.doctorprofile:
        return HttpResponse("Unauthorized", status=403)
    
    # Get statistics
    rec_evidences = RecommendationEvidence.objects.filter(treatment_plan=treatment_plan)
    
    total_recommendations = rec_evidences.count()
    high_strength = rec_evidences.filter(total_evidence_score__gte=0.7).count()
    moderate_strength = rec_evidences.filter(
        total_evidence_score__gte=0.4, 
        total_evidence_score__lt=0.7
    ).count()
    low_strength = rec_evidences.filter(total_evidence_score__lt=0.4).count()
    
    # Get evidence types
    all_links = sum([re.evidencelink_set.count() for re in rec_evidences])
    guideline_refs = sum([
        len([link for link in re.evidencelink_set.all() 
             if link.evidence_source.source_type.startswith('nccn') or
                link.evidence_source.source_type.startswith('esmo') or
                link.evidence_source.source_type.startswith('asco')])
        for re in rec_evidences
    ])
    pubmed_refs = all_links - guideline_refs
    
    # Get audit trail
    explanation_logs = EvidenceExplanationLog.objects.filter(
        treatment_plan=treatment_plan
    ).order_by('-created_at')[:20]
    
    # Get feedback
    helpful_count = explanation_logs.filter(was_helpful=True).count()
    total_views = explanation_logs.count()
    feedback_percentage = (helpful_count / total_views * 100) if total_views > 0 else 0
    
    context = {
        'treatment_plan': treatment_plan,
        'total_recommendations': total_recommendations,
        'high_strength': high_strength,
        'moderate_strength': moderate_strength,
        'low_strength': low_strength,
        'all_links': all_links,
        'guideline_refs': guideline_refs,
        'pubmed_refs': pubmed_refs,
        'explanation_logs': explanation_logs,
        'feedback_percentage': feedback_percentage,
        'total_views': total_views,
    }
    
    return render(request, 'cancer_detection/evidence_statistics.html', context)


@login_required
def submit_explanation_feedback(request, plan_id, rec_evidence_id):
    """
    Submit user feedback on explanation (AJAX endpoint).
    Tracks whether explanation was helpful to the user.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    treatment_plan = get_object_or_404(PersonalizedTreatmentPlan, id=plan_id)
    rec_evidence = get_object_or_404(RecommendationEvidence, id=rec_evidence_id)
    
    # Check access
    if request.user != treatment_plan.patient.user and not request.user.doctorprofile:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    was_helpful = request.POST.get('was_helpful') == 'true'
    user_feedback = request.POST.get('feedback', '')
    
    # Get or create latest log
    try:
        log = EvidenceExplanationLog.objects.filter(
            treatment_plan=treatment_plan,
            recommendation_evidence=rec_evidence,
            user=request.user
        ).latest('created_at')
        
        log.was_helpful = was_helpful
        log.user_feedback = user_feedback
        log.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Thank you for your feedback!'
        })
    except EvidenceExplanationLog.DoesNotExist:
        return JsonResponse({
            'error': 'Explanation log not found'
        }, status=404)


@login_required
def evidence_audit_trail(request, plan_id):
    """
    Display complete audit trail of evidence explanations accessed.
    Shows when explanations were viewed, by whom, and user feedback.
    """
    treatment_plan = get_object_or_404(PersonalizedTreatmentPlan, id=plan_id)
    
    # Check access - only patient and doctors can view
    if request.user != treatment_plan.patient.user and not request.user.doctorprofile:
        return HttpResponse("Unauthorized", status=403)
    
    # Get audit trail
    audit_logs = EvidenceExplanationLog.objects.filter(
        treatment_plan=treatment_plan
    ).select_related(
        'user', 'rec_evidence', 'treatment_plan'
    ).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(audit_logs, 50)
    page_num = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_num)
    
    # Statistics
    total_views = audit_logs.count()
    helpful_views = audit_logs.filter(was_helpful=True).count()
    unhelpful_views = audit_logs.filter(was_helpful=False).count()
    
    context = {
        'treatment_plan': treatment_plan,
        'page_obj': page_obj,
        'total_views': total_views,
        'helpful_views': helpful_views,
        'unhelpful_views': unhelpful_views,
        'helpful_percentage': (helpful_views / total_views * 100) if total_views > 0 else 0,
    }
    
    return render(request, 'cancer_detection/evidence_audit_trail.html', context)


@login_required
def rule_based_references_view(request):
    """
    Display available rule-based references for fallback evidence.
    Shows pre-configured treatment guidelines for different cancer types/stages.
    """
    cancer_type = request.GET.get('cancer_type', '')
    cancer_stage = request.GET.get('cancer_stage', '')
    
    # Get rules
    rules = RuleBasedReference.objects.filter(is_active=True)
    
    if cancer_type:
        rules = rules.filter(cancer_type=cancer_type)
    
    if cancer_stage:
        rules = rules.filter(cancer_stage=cancer_stage)
    
    # Get unique cancer types and stages for filter
    cancer_types = RuleBasedReference.objects.filter(is_active=True).values_list(
        'cancer_type', flat=True
    ).distinct()
    cancer_stages = RuleBasedReference.objects.filter(is_active=True).values_list(
        'cancer_stage', flat=True
    ).distinct()
    
    # Pagination
    paginator = Paginator(rules, 10)
    page_num = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_num)
    
    context = {
        'page_obj': page_obj,
        'cancer_types': sorted(cancer_types),
        'cancer_stages': sorted(cancer_stages),
        'selected_type': cancer_type,
        'selected_stage': cancer_stage,
        'rules': page_obj.object_list,
    }
    
    return render(request, 'cancer_detection/rule_based_references.html', context)


# Helper Functions

def _get_patient_factor_value(patient, factor_name):
    """Extract patient's value for a specific decision factor."""
    factor_name_lower = factor_name.lower()
    
    # Map factor names to patient attributes
    if 'age' in factor_name_lower:
        return f"{patient.age} years"
    elif 'performance' in factor_name_lower or 'ecog' in factor_name_lower:
        return getattr(patient, 'performance_status', 'Unknown')
    elif 'comorbid' in factor_name_lower:
        comorbidities = getattr(patient, 'comorbidities', [])
        return ', '.join(comorbidities) if comorbidities else 'None'
    elif 'stage' in factor_name_lower:
        return getattr(patient, 'cancer_stage', 'Unknown')
    elif 'grade' in factor_name_lower:
        return getattr(patient, 'cancer_grade', 'Unknown')
    elif 'receptor' in factor_name_lower or 'hormone' in factor_name_lower:
        return getattr(patient, 'hormone_receptor_status', 'Unknown')
    elif 'her2' in factor_name_lower:
        return getattr(patient, 'her2_status', 'Unknown')
    elif 'egfr' in factor_name_lower or 'mutation' in factor_name_lower:
        return getattr(patient, 'molecular_markers', 'Unknown')
    elif 'kidney' in factor_name_lower:
        return getattr(patient, 'renal_function', 'Unknown')
    elif 'liver' in factor_name_lower:
        return getattr(patient, 'hepatic_function', 'Unknown')
    else:
        return 'Information not available'
