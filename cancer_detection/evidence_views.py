"""
Evidence Traceability API Views
REST endpoints for explaining recommendations with evidence and citations
"""

import json
import logging
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import PersonalizedTreatmentPlan
from .evidence_models import (
    EvidenceSource, RecommendationEvidence, EvidenceExplanationLog,
    RuleBasedReference
)
from .evidence_integration import (
    EvidenceIntegratedPlanner, RecommendationFactorAnalyzer
)
from .evidence_ingester import EvidenceIngestionService

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def explain_recommendation(request, treatment_plan_id, rec_evidence_id=None):
    """
    Explain a treatment recommendation with evidence and citations
    
    Parameters:
        - treatment_plan_id: ID of the treatment plan
        - rec_evidence_id: ID of specific recommendation (optional)
        - format: 'full', 'summary', or 'citations_only' (query param, default: 'full')
        
    Returns:
        JSON with recommendation rationale and evidence sources
    """
    
    try:
        # Get treatment plan
        treatment_plan = PersonalizedTreatmentPlan.objects.get(
            id=treatment_plan_id,
            patient=request.user
        )
    except PersonalizedTreatmentPlan.DoesNotExist:
        return Response(
            {'error': 'Treatment plan not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    planner = EvidenceIntegratedPlanner()
    format_type = request.query_params.get('format', 'full')
    
    if rec_evidence_id:
        # Get specific recommendation evidence
        try:
            rec_evidence = RecommendationEvidence.objects.get(
                id=rec_evidence_id,
                treatment_plan=treatment_plan
            )
        except RecommendationEvidence.DoesNotExist:
            return Response(
                {'error': 'Recommendation evidence not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        explanation = planner.get_recommendation_explanation(
            rec_evidence, request.user, format_type
        )
        
        return Response({
            'status': 'success',
            'explanation': explanation
        })
    else:
        # Return explanations for all recommendations
        rec_evidences = RecommendationEvidence.objects.filter(
            treatment_plan=treatment_plan
        ).order_by('-created_at')
        
        explanations = []
        for rec_evidence in rec_evidences:
            explanation = planner.get_recommendation_explanation(
                rec_evidence, request.user, format_type
            )
            explanations.append(explanation)
        
        return Response({
            'status': 'success',
            'treatment_plan_id': treatment_plan_id,
            'total_recommendations': len(explanations),
            'explanations': explanations
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_recommendation_with_evidence(request, treatment_plan_id):
    """
    Get all recommendations for a treatment plan with their evidence
    
    Returns:
        JSON with all recommendations and evidence summary
    """
    
    try:
        treatment_plan = PersonalizedTreatmentPlan.objects.get(
            id=treatment_plan_id,
            patient=request.user
        )
    except PersonalizedTreatmentPlan.DoesNotExist:
        return Response(
            {'error': 'Treatment plan not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get all recommendation evidences
    rec_evidences = RecommendationEvidence.objects.filter(
        treatment_plan=treatment_plan
    ).prefetch_related('evidence_sources').order_by('-created_at')
    
    recommendations = []
    for rec_evidence in rec_evidences:
        rec_data = {
            'id': rec_evidence.id,
            'recommendation_type': rec_evidence.recommendation_type,
            'recommendation_text': rec_evidence.recommendation_text,
            'confidence_score': rec_evidence.total_evidence_score,
            'evidence_count': rec_evidence.evidence_sources.count(),
            'strength_distribution': {
                'high': rec_evidence.high_strength_count,
                'moderate': rec_evidence.moderate_strength_count,
                'low': rec_evidence.low_strength_count,
            },
            'decision_factors': rec_evidence.decision_factors,
            'created_at': rec_evidence.created_at.isoformat(),
        }
        
        # Get top evidence sources
        evidence_links = rec_evidence.evidence_link_set.all().order_by('-impact_percentage')[:5]
        sources = []
        for link in evidence_links:
            source_data = {
                'id': link.evidence_source.id,
                'title': link.evidence_source.title,
                'authors': link.evidence_source.authors,
                'year': link.evidence_source.publication_year,
                'pmid': link.evidence_source.pmid,
                'source_type': link.evidence_source.source_type,
                'evidence_strength': link.evidence_source.evidence_strength,
                'relevance_score': link.relevance_score,
                'impact_percentage': link.impact_percentage,
            }
            sources.append(source_data)
        
        rec_data['top_evidence_sources'] = sources
        recommendations.append(rec_data)
    
    return Response({
        'status': 'success',
        'treatment_plan': {
            'id': treatment_plan.id,
            'cancer_type': treatment_plan.cancer_type,
            'cancer_stage': treatment_plan.cancer_stage,
        },
        'total_recommendations': len(recommendations),
        'recommendations': recommendations
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_evidence_source_detail(request, evidence_id):
    """
    Get detailed information about a specific evidence source
    """
    
    try:
        evidence = EvidenceSource.objects.get(id=evidence_id)
    except EvidenceSource.DoesNotExist:
        return Response(
            {'error': 'Evidence source not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    detail = {
        'id': evidence.id,
        'title': evidence.title,
        'source_type': evidence.source_type,
        'authors': evidence.authors,
        'year': evidence.publication_year,
        'journal': evidence.journal_or_organization,
        'pmid': evidence.pmid,
        'doi': evidence.doi,
        'evidence_strength': evidence.evidence_strength,
        'abstract': evidence.abstract,
        'key_findings': evidence.key_findings,
        'cancer_types': evidence.cancer_types,
        'treatment_types': evidence.treatment_types,
        'guideline_url': evidence.guideline_url,
        'pdf_url': evidence.pdf_url,
        'created_at': evidence.created_at.isoformat(),
    }
    
    return Response({
        'status': 'success',
        'evidence': detail
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def log_explanation_feedback(request, treatment_plan_id, rec_evidence_id):
    """
    Log user feedback on explanation helpfulness
    
    Body:
        {
            "was_helpful": true/false,
            "feedback": "Optional user feedback text"
        }
    """
    
    try:
        treatment_plan = PersonalizedTreatmentPlan.objects.get(
            id=treatment_plan_id,
            patient=request.user
        )
        rec_evidence = RecommendationEvidence.objects.get(
            id=rec_evidence_id,
            treatment_plan=treatment_plan
        )
    except (PersonalizedTreatmentPlan.DoesNotExist, RecommendationEvidence.DoesNotExist):
        return Response(
            {'error': 'Treatment plan or recommendation not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get most recent explanation log
    log_entry = EvidenceExplanationLog.objects.filter(
        user=request.user,
        treatment_plan=treatment_plan,
        recommendation_evidence=rec_evidence
    ).order_by('-created_at').first()
    
    if not log_entry:
        return Response(
            {'error': 'No explanation log found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    data = request.data
    log_entry.was_helpful = data.get('was_helpful')
    log_entry.user_feedback = data.get('feedback', '')
    log_entry.save()
    
    return Response({
        'status': 'success',
        'message': 'Feedback recorded'
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_evidence(request):
    """
    Search evidence sources by query
    
    Query parameters:
        - q: Search query
        - evidence_strength: Filter by 'high', 'moderate', 'low'
        - source_type: Filter by source type
        - cancer_type: Filter by cancer type
        - page: Page number (default: 1)
    """
    
    query = request.query_params.get('q', '')
    if not query:
        return Response(
            {'error': 'Query parameter required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Build filter
    filters = {}
    if request.query_params.get('evidence_strength'):
        filters['evidence_strength'] = request.query_params.get('evidence_strength')
    if request.query_params.get('source_type'):
        filters['source_type'] = request.query_params.get('source_type')
    
    # Search evidence by title, abstract, or key findings
    evidence_sources = EvidenceSource.objects.filter(
        is_active=True,
        **filters
    ).filter(
        title__icontains=query
    ) | EvidenceSource.objects.filter(
        is_active=True,
        **filters,
        abstract__icontains=query
    )
    
    evidence_sources = evidence_sources.distinct().order_by('-publication_year')
    
    # Pagination
    paginator = Paginator(evidence_sources, 20)
    page_num = request.query_params.get('page', 1)
    page_obj = paginator.get_page(page_num)
    
    results = []
    for evidence in page_obj:
        results.append({
            'id': evidence.id,
            'title': evidence.title,
            'authors': evidence.authors,
            'year': evidence.publication_year,
            'source_type': evidence.source_type,
            'evidence_strength': evidence.evidence_strength,
            'pmid': evidence.pmid,
            'abstract': evidence.abstract[:200] + '...' if evidence.abstract else '',
        })
    
    return Response({
        'status': 'success',
        'query': query,
        'total_results': paginator.count,
        'page': page_num,
        'total_pages': paginator.num_pages,
        'results': results
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_rule_based_reference(request):
    """
    Create a new rule-based reference for fallback evidence
    (Requires admin/doctor permission)
    
    Body:
        {
            "rule_name": "string",
            "description": "string",
            "cancer_type": "string",
            "cancer_stage": "string",
            "recommended_treatment": "string",
            "evidence_strength": "high|moderate|low",
            "pubmed_references": [list of PMIDs],
            "guideline_references": [list of guideline names],
            "priority_level": integer
        }
    """
    
    # Check permission (simplified - in production, use proper permission classes)
    if not (request.user.is_staff or hasattr(request.user, 'doctorprofile')):
        return Response(
            {'error': 'Permission denied'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    data = request.data
    
    try:
        rule = RuleBasedReference.objects.create(
            rule_name=data['rule_name'],
            description=data['description'],
            cancer_type=data['cancer_type'],
            cancer_stage=data.get('cancer_stage'),
            recommended_treatment=data['recommended_treatment'],
            evidence_strength=data.get('evidence_strength', 'moderate'),
            pubmed_references=data.get('pubmed_references', []),
            guideline_references=data.get('guideline_references', []),
            priority_level=data.get('priority_level', 0),
            created_by=request.user,
        )
        
        return Response({
            'status': 'success',
            'rule_id': rule.id,
            'message': 'Rule-based reference created'
        }, status=status.HTTP_201_CREATED)
        
    except KeyError as e:
        return Response(
            {'error': f'Missing required field: {str(e)}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error creating rule: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_patient_decision_factors(request, treatment_plan_id, rec_evidence_id):
    """
    Get analysis of which patient factors influenced a recommendation
    
    Returns:
        JSON with factor importance scores
    """
    
    try:
        treatment_plan = PersonalizedTreatmentPlan.objects.get(
            id=treatment_plan_id,
            patient=request.user
        )
        rec_evidence = RecommendationEvidence.objects.get(
            id=rec_evidence_id,
            treatment_plan=treatment_plan
        )
    except (PersonalizedTreatmentPlan.DoesNotExist, RecommendationEvidence.DoesNotExist):
        return Response(
            {'error': 'Treatment plan or recommendation not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    return Response({
        'status': 'success',
        'recommendation': rec_evidence.recommendation_text,
        'recommendation_type': rec_evidence.recommendation_type,
        'decision_factors': rec_evidence.decision_factors,
        'factor_analysis': {
            factor: {
                'influence_score': RecommendationFactorAnalyzer._calculate_factor_influence(
                    factor, value.get('value'), rec_evidence.recommendation_text
                ),
                'value': value.get('value')
            }
            for factor, value in rec_evidence.decision_factors.items()
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def initialize_evidence_database(request):
    """
    Initialize evidence database with default guidelines
    (Requires admin permission)
    """
    
    if not request.user.is_staff:
        return Response(
            {'error': 'Permission denied'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    ingestion_service = EvidenceIngestionService()
    result = ingestion_service.initialize_default_evidence()
    
    return Response({
        'status': 'success',
        'message': 'Evidence database initialized',
        'results': result
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def search_and_ingest_studies(request):
    """
    Search PubMed and ingest relevant studies
    (Requires admin permission)
    
    Body:
        {
            "cancer_type": "string",
            "treatment_type": "string",
            "max_results": integer (default: 5)
        }
    """
    
    if not request.user.is_staff:
        return Response(
            {'error': 'Permission denied'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    data = request.data
    
    ingestion_service = EvidenceIngestionService()
    result = ingestion_service.search_and_ingest_studies(
        cancer_type=data.get('cancer_type', ''),
        treatment_type=data.get('treatment_type', ''),
        max_results=data.get('max_results', 5)
    )
    
    return Response({
        'status': 'success',
        'results': result
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_explanation_history(request, treatment_plan_id):
    """
    Get history of explanation accesses for a treatment plan
    (Shows when user viewed explanations and feedback)
    """
    
    try:
        treatment_plan = PersonalizedTreatmentPlan.objects.get(
            id=treatment_plan_id,
            patient=request.user
        )
    except PersonalizedTreatmentPlan.DoesNotExist:
        return Response(
            {'error': 'Treatment plan not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    logs = EvidenceExplanationLog.objects.filter(
        user=request.user,
        treatment_plan=treatment_plan
    ).select_related('recommendation_evidence').order_by('-created_at')
    
    history = []
    for log in logs:
        history.append({
            'id': log.id,
            'recommendation_type': log.recommendation_evidence.recommendation_type if log.recommendation_evidence else 'Unknown',
            'explanation_type': log.explanation_type,
            'response_time_ms': log.response_time_ms,
            'was_helpful': log.was_helpful,
            'user_feedback': log.user_feedback,
            'accessed_at': log.created_at.isoformat(),
        })
    
    return Response({
        'status': 'success',
        'treatment_plan_id': treatment_plan_id,
        'total_accesses': len(history),
        'history': history
    })
