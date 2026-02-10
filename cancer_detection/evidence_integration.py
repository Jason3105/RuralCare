"""
Evidence Integration Module
Integrates RAG-based evidence retrieval and tracking into treatment planning
Modifies treatment recommendations to include evidence citations
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from .evidence_models import (
    EvidenceSource, RecommendationEvidence, EvidenceLink, 
    RuleBasedReference, EvidenceExplanationLog
)
from .evidence_retriever import EvidenceRetriever, EvidenceSynthesizer
from .evidence_ingester import EvidenceIngestionService

logger = logging.getLogger(__name__)


class EvidenceTrackedRecommendation:
    """
    Wrapper for treatment recommendations with integrated evidence tracking
    """
    
    def __init__(self, recommendation_text: str, recommendation_type: str,
                 patient_factors: Dict, treatment_plan=None):
        """
        Args:
            recommendation_text: The actual recommendation
            recommendation_type: Category (e.g., 'Chemotherapy', 'Targeted Therapy')
            patient_factors: Factors influencing the recommendation
            treatment_plan: Associated PersonalizedTreatmentPlan instance
        """
        self.recommendation_text = recommendation_text
        self.recommendation_type = recommendation_type
        self.patient_factors = patient_factors
        self.treatment_plan = treatment_plan
        self.evidence_sources: List[Dict] = []
        self.rationale: Optional[Dict] = None
        self.recommendation_evidence: Optional[RecommendationEvidence] = None
    
    def add_evidence(self, evidence_list: List[Dict]):
        """Add evidence sources to recommendation"""
        self.evidence_sources.extend(evidence_list)
    
    def synthesize_evidence(self) -> Dict:
        """Generate rationale from evidence"""
        self.rationale = EvidenceSynthesizer.synthesize_recommendation_rationale(
            self.recommendation_text,
            self.evidence_sources,
            self.patient_factors
        )
        return self.rationale
    
    def get_explanation(self) -> str:
        """Get human-readable explanation"""
        if not self.rationale:
            self.synthesize_evidence()
        return EvidenceSynthesizer.generate_explanation_text(self.rationale)
    
    @transaction.atomic
    def save_to_database(self) -> RecommendationEvidence:
        """Save recommendation with evidence to database"""
        if not self.treatment_plan:
            raise ValueError("Cannot save without associated treatment plan")
        
        if not self.rationale:
            self.synthesize_evidence()
        
        # Create RecommendationEvidence
        rec_evidence = RecommendationEvidence.objects.create(
            treatment_plan=self.treatment_plan,
            recommendation_type=self.recommendation_type,
            recommendation_text=self.recommendation_text,
            decision_factors=self.patient_factors,
        )
        
        # Link evidence sources
        for source_data in self.evidence_sources:
            source = source_data['source']
            
            evidence_link = EvidenceLink.objects.create(
                recommendation_evidence=rec_evidence,
                evidence_source=source,
                relevance_type='directly_supports',
                relevance_score=source_data['relevance_score'],
                how_evidence_supports=source_data.get('how_evidence_supports', ''),
                relevant_excerpts=source_data.get('relevant_excerpts', []),
                impact_percentage=min(100, source_data['relevance_score'] * 100)
            )
        
        # Update recommendation evidence scores
        rec_evidence.calculate_evidence_score()
        rec_evidence.high_strength_count = sum(1 for e in self.evidence_sources 
                                              if e['evidence_strength'] == 'high')
        rec_evidence.moderate_strength_count = sum(1 for e in self.evidence_sources 
                                                  if e['evidence_strength'] == 'moderate')
        rec_evidence.low_strength_count = sum(1 for e in self.evidence_sources 
                                            if e['evidence_strength'] == 'low')
        rec_evidence.save()
        
        self.recommendation_evidence = rec_evidence
        logger.info(f"Saved recommendation evidence {rec_evidence.id} with "
                   f"{len(self.evidence_sources)} sources")
        
        return rec_evidence


class EvidenceIntegratedPlanner:
    """
    Wraps TreatmentPlanningEngine to integrate evidence tracking
    """
    
    def __init__(self):
        self.retriever = EvidenceRetriever()
        self.ingestion_service = EvidenceIngestionService()
    
    def create_treatment_recommendation_with_evidence(self, 
                                                     cancer_type: str,
                                                     cancer_stage: str,
                                                     treatment_recommendation: str,
                                                     treatment_type: str,
                                                     patient_factors: Dict,
                                                     treatment_plan=None,
                                                     biomarkers: Optional[List[str]] = None,
                                                     use_rag: bool = True,
                                                     fallback_to_rules: bool = True) -> EvidenceTrackedRecommendation:
        """
        Create a treatment recommendation with integrated evidence
        
        Args:
            cancer_type: Type of cancer
            cancer_stage: Cancer stage
            treatment_recommendation: The recommendation text
            treatment_type: Type of treatment (Chemotherapy, etc.)
            patient_factors: Relevant patient factors
            treatment_plan: Associated treatment plan object
            biomarkers: Relevant biomarkers
            use_rag: Whether to use RAG pipeline (default True)
            fallback_to_rules: Fall back to rules if RAG unavailable (default True)
            
        Returns:
            EvidenceTrackedRecommendation with evidence integrated
        """
        
        rec = EvidenceTrackedRecommendation(
            recommendation_text=treatment_recommendation,
            recommendation_type=treatment_type,
            patient_factors=patient_factors,
            treatment_plan=treatment_plan
        )
        
        evidence_sources = []
        
        # Try RAG pipeline first
        if use_rag and self.retriever.initialized:
            try:
                evidence_sources = self._retrieve_rag_evidence(
                    cancer_type, cancer_stage, treatment_type, 
                    treatment_recommendation, biomarkers
                )
                logger.info(f"Retrieved {len(evidence_sources)} evidence sources via RAG")
            except Exception as e:
                logger.error(f"RAG retrieval failed: {str(e)}")
                evidence_sources = []
        
        # Fall back to rule-based references if needed
        if not evidence_sources and fallback_to_rules:
            try:
                evidence_sources = self._get_rule_based_references(
                    cancer_type, cancer_stage, treatment_type, biomarkers
                )
                logger.info(f"Retrieved {len(evidence_sources)} evidence sources via rules")
            except Exception as e:
                logger.error(f"Rule-based retrieval failed: {str(e)}")
        
        # Add evidence to recommendation
        if evidence_sources:
            rec.add_evidence(evidence_sources)
        else:
            logger.warning(f"No evidence found for {cancer_type} {cancer_stage} {treatment_type}")
        
        return rec
    
    def _retrieve_rag_evidence(self, cancer_type: str, cancer_stage: str,
                              treatment_type: str, query: str,
                              biomarkers: Optional[List[str]] = None) -> List[Dict]:
        """Retrieve evidence using RAG pipeline"""
        
        if not self.retriever.initialized:
            logger.warning("Retriever not initialized")
            return []
        
        # Search for evidence
        evidence_sources = self.retriever.retrieve_evidence(
            query=query,
            top_k=10,
            cancer_types=[cancer_type],
            source_types=['nccn_guideline', 'esmo_guideline', 'asco_guideline',
                         'pubmed_study', 'systematic_review', 'meta_analysis']
        )
        
        return evidence_sources
    
    def _get_rule_based_references(self, cancer_type: str, cancer_stage: str,
                                  treatment_type: str,
                                  biomarkers: Optional[List[str]] = None) -> List[Dict]:
        """Retrieve evidence using rule-based fallback"""
        
        rules = RuleBasedReference.objects.filter(
            is_active=True,
            cancer_type=cancer_type,
            cancer_stage=cancer_stage
        ).order_by('-priority_level')
        
        evidence_list = []
        
        for rule in rules[:5]:  # Top 5 matching rules
            # Create pseudo-evidence from rule
            evidence_item = {
                'source': None,  # No database object for rules
                'relevance_score': 0.9,  # High relevance for rule-based
                'title': rule.rule_name,
                'source_type': 'rule_based',
                'evidence_strength': rule.evidence_strength,
                'year': None,
                'authors': 'Clinical Protocol',
                'abstract': rule.description,
                'key_findings': rule.rule_logic,
                'pmid': None,
            }
            
            evidence_list.append(evidence_item)
        
        # Also try to link to actual evidence sources referenced by rules
        for rule in rules:
            if rule.pubmed_references:
                for pmid in rule.pubmed_references[:2]:  # Top 2 PMIDs per rule
                    try:
                        source = EvidenceSource.objects.get(pmid=pmid)
                        evidence_list.append({
                            'source': source,
                            'relevance_score': 0.85,
                            'title': source.title,
                            'source_type': source.source_type,
                            'evidence_strength': source.evidence_strength,
                            'year': source.publication_year,
                            'authors': source.authors,
                            'abstract': source.abstract,
                            'key_findings': source.key_findings,
                            'pmid': source.pmid,
                        })
                    except EvidenceSource.DoesNotExist:
                        continue
        
        return evidence_list
    
    @transaction.atomic
    def log_explanation_access(self, user, treatment_plan, 
                              recommendation_evidence: Optional[RecommendationEvidence] = None,
                              explanation_type: str = 'full',
                              response_time_ms: int = 0) -> EvidenceExplanationLog:
        """Log when a user views an explanation"""
        
        log_entry = EvidenceExplanationLog.objects.create(
            user=user,
            treatment_plan=treatment_plan,
            recommendation_evidence=recommendation_evidence,
            explanation_type=explanation_type,
            response_time_ms=response_time_ms,
        )
        
        if recommendation_evidence:
            log_entry.sources_shown.set(
                recommendation_evidence.evidence_sources.all()
            )
        
        return log_entry
    
    def get_recommendation_explanation(self, recommendation_evidence: RecommendationEvidence,
                                      user, format_type: str = 'full') -> Dict:
        """
        Get detailed explanation for a recommendation
        
        Args:
            recommendation_evidence: The RecommendationEvidence object
            user: User requesting explanation
            format_type: 'full', 'summary', or 'citations_only'
            
        Returns:
            Explanation dictionary
        """
        
        import time
        start_time = time.time()
        
        # Build explanation
        evidence_links = EvidenceLink.objects.filter(
            recommendation_evidence=recommendation_evidence
        ).select_related('evidence_source').order_by('-impact_percentage')
        
        explanation = {
            'recommendation': recommendation_evidence.recommendation_text,
            'recommendation_type': recommendation_evidence.recommendation_type,
            'overall_confidence': recommendation_evidence.total_evidence_score,
            'decision_factors': recommendation_evidence.decision_factors,
        }
        
        if format_type in ['full', 'summary']:
            # Add evidence sources
            evidence_list = []
            for link in evidence_links[:10]:  # Top 10
                source = link.evidence_source
                evidence_item = {
                    'title': source.title,
                    'authors': source.authors,
                    'year': source.publication_year,
                    'source_type': source.source_type,
                    'pmid': source.pmid,
                    'doi': source.doi,
                    'evidence_strength': source.evidence_strength,
                    'relevance': link.relevance_score,
                    'impact': link.impact_percentage,
                    'how_supports': link.how_evidence_supports,
                    'excerpts': link.relevant_excerpts,
                }
                evidence_list.append(evidence_item)
            
            explanation['evidence_sources'] = evidence_list
            explanation['evidence_summary'] = {
                'total_sources': len(evidence_links),
                'high_strength': recommendation_evidence.high_strength_count,
                'moderate_strength': recommendation_evidence.moderate_strength_count,
                'low_strength': recommendation_evidence.low_strength_count,
            }
        
        if format_type in ['full', 'citations_only']:
            # Add formatted citations
            citations = []
            for i, link in enumerate(evidence_links, 1):
                source = link.evidence_source
                if source.pmid:
                    citation = (f"{i}. {source.authors or 'Unknown'} et al. "
                               f"({source.publication_year or 'N/A'}). {source.title}. "
                               f"PMID: {source.pmid}")
                else:
                    citation = (f"{i}. {source.title}. "
                               f"{source.journal_or_organization or ''} "
                               f"{source.publication_year or ''}")
                citations.append(citation)
            
            explanation['citations'] = citations
        
        # Log access
        response_time = int((time.time() - start_time) * 1000)
        self.log_explanation_access(
            user=user,
            treatment_plan=recommendation_evidence.treatment_plan,
            recommendation_evidence=recommendation_evidence,
            explanation_type=format_type,
            response_time_ms=response_time
        )
        
        return explanation


class RecommendationFactorAnalyzer:
    """
    Analyzes which patient features influenced a recommendation
    Provides feature importance scores
    """
    
    @staticmethod
    def analyze_decision_factors(patient_data: Dict, recommendation: str) -> Dict:
        """
        Analyze which patient factors influenced the recommendation
        
        Args:
            patient_data: Patient profile data
            recommendation: The recommendation
            
        Returns:
            Dictionary of factors and their influence scores (0-1)
        """
        
        factor_influence = {}
        
        # Analyze various patient factors
        factors_to_check = {
            'age': 'patient_age',
            'performance_status': 'patient_performance_status',
            'comorbidities': 'comorbidities',
            'genetic_mutations': 'genetic_profile',
            'biomarkers': 'biomarkers',
            'organ_function': 'organ_function',
            'previous_treatments': 'previous_treatments',
            'allergies': 'allergies',
        }
        
        for factor_name, data_key in factors_to_check.items():
            if data_key in patient_data and patient_data[data_key]:
                # Calculate influence based on factor type
                influence = RecommendationFactorAnalyzer._calculate_factor_influence(
                    factor_name, patient_data[data_key], recommendation
                )
                if influence > 0:
                    factor_influence[factor_name] = {
                        'value': patient_data[data_key],
                        'influence_score': influence
                    }
        
        return factor_influence
    
    @staticmethod
    def _calculate_factor_influence(factor_name: str, factor_value, 
                                   recommendation: str) -> float:
        """
        Calculate influence score (0-1) of a factor on recommendation
        
        Args:
            factor_name: Name of factor
            factor_value: Value of factor
            recommendation: The recommendation
            
        Returns:
            Influence score 0-1
        """
        
        # Heuristic rules for factor influence
        if factor_name == 'age':
            # Age is very influential for cancer treatment
            return 0.85
        elif factor_name == 'performance_status':
            # PS is critical for treatment decisions
            return 0.9
        elif factor_name == 'genetic_mutations' or factor_name == 'biomarkers':
            # Genetic factors are highly influential for targeted therapy
            if 'targeted' in recommendation.lower():
                return 0.95
            else:
                return 0.6
        elif factor_name == 'comorbidities':
            # Comorbidities affect feasibility
            return 0.8
        elif factor_name == 'organ_function':
            # Organ function critical for dose adjustments
            return 0.85
        else:
            return 0.5  # Default moderate influence
