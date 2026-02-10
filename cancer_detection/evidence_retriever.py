"""
RAG (Retrieval-Augmented Generation) Pipeline for Evidence Retrieval
Uses Hugging Face sentence-transformers for semantic search over clinical guidelines and papers
"""

import json
import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import numpy as np
from django.db.models import Q

try:
    from sentence_transformers import SentenceTransformer, util
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from .evidence_models import EvidenceSource

logger = logging.getLogger(__name__)


class EvidenceRetriever:
    """
    Retrieves relevant evidence using semantic search via Hugging Face models
    Implements RAG pipeline for clinical guidelines and research papers
    """
    
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """
        Initialize the retriever with a Hugging Face sentence-transformers model
        
        Args:
            model_name: Hugging Face model identifier
                - "sentence-transformers/all-MiniLM-L6-v2": Fast, lightweight (~22M parameters)
                - "sentence-transformers/all-mpnet-base-v2": Better quality (~109M parameters)
                - "sentence-transformers/paraphrase-MiniLM-L6-v2": Paraphrase-focused
        """
        self.model_name = model_name
        self.model = None
        self.initialized = False
        
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                logger.info(f"Loading sentence-transformer model: {model_name}")
                self.model = SentenceTransformer(model_name)
                self.initialized = True
                logger.info("Sentence-transformer model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load sentence-transformer model: {str(e)}")
                self.initialized = False
        else:
            logger.warning("sentence-transformers not installed. RAG pipeline unavailable.")
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for a text query
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list, or None if embedding failed
        """
        if not self.initialized or not self.model:
            return None
        
        try:
            embedding = self.model.encode(text, convert_to_tensor=False)
            return embedding.tolist() if isinstance(embedding, np.ndarray) else embedding
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            return None
    
    def retrieve_evidence(self, query: str, top_k: int = 5, 
                         cancer_types: Optional[List[str]] = None,
                         evidence_strength_filter: Optional[str] = None,
                         source_types: Optional[List[str]] = None) -> List[Dict]:
        """
        Retrieve most relevant evidence sources for a query using semantic search
        
        Args:
            query: Search query (recommendation or question)
            top_k: Number of results to return
            cancer_types: Filter by cancer types (optional)
            evidence_strength_filter: Filter by evidence strength: 'high', 'moderate', 'low'
            source_types: Filter by source types
            
        Returns:
            List of relevant evidence sources with relevance scores
        """
        if not self.initialized:
            logger.warning("Retriever not initialized. Returning empty results.")
            return []
        
        # Get query embedding
        query_embedding = self.get_embedding(query)
        if query_embedding is None:
            logger.error("Failed to generate query embedding")
            return []
        
        query_embedding = np.array(query_embedding)
        
        # Build filter query
        filter_q = Q(is_active=True)
        if cancer_types:
            filter_q &= Q(cancer_types__overlap=cancer_types)
        if evidence_strength_filter:
            filter_q &= Q(evidence_strength=evidence_strength_filter)
        if source_types:
            filter_q &= Q(source_type__in=source_types)
        
        # Get all relevant evidence sources
        evidence_sources = EvidenceSource.objects.filter(filter_q)
        
        if not evidence_sources.exists():
            logger.info(f"No evidence sources found matching filters: {filter_q}")
            return []
        
        # Retrieve evidence with embeddings
        results = []
        for source in evidence_sources:
            if not source.embedding:
                # Generate embedding if not present
                text_to_embed = f"{source.title} {source.abstract or ''} {source.key_findings or ''}"
                source.embedding = self.get_embedding(text_to_embed)
                source.save(update_fields=['embedding', 'last_indexed'])
            
            if source.embedding:
                try:
                    source_embedding = np.array(source.embedding)
                    # Calculate cosine similarity
                    similarity = util.pytorch_cos_sim(query_embedding, source_embedding)[0][0].item() \
                               if hasattr(util, 'pytorch_cos_sim') else self._cosine_similarity(
                                   query_embedding, source_embedding)
                    
                    results.append({
                        'source': source,
                        'relevance_score': float(similarity),
                        'title': source.title,
                        'authors': source.authors,
                        'year': source.publication_year,
                        'pmid': source.pmid,
                        'evidence_strength': source.evidence_strength,
                        'abstract': source.abstract,
                        'key_findings': source.key_findings,
                        'source_type': source.source_type,
                    })
                except Exception as e:
                    logger.error(f"Error calculating similarity for source {source.id}: {str(e)}")
        
        # Sort by relevance and return top_k
        results = sorted(results, key=lambda x: x['relevance_score'], reverse=True)[:top_k]
        
        return results
    
    @staticmethod
    def _cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors (fallback if PyTorch unavailable)
        """
        dot_product = np.dot(vec1, vec2)
        magnitude1 = np.linalg.norm(vec1)
        magnitude2 = np.linalg.norm(vec2)
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def retrieve_by_cancer_and_treatment(self, cancer_type: str, treatment_type: str,
                                        cancer_stage: Optional[str] = None,
                                        biomarkers: Optional[List[str]] = None) -> List[Dict]:
        """
        Retrieve evidence specific to a cancer type and treatment
        
        Args:
            cancer_type: Type of cancer
            treatment_type: Treatment modality
            cancer_stage: Cancer stage (optional)
            biomarkers: Relevant biomarkers (optional)
            
        Returns:
            Relevant evidence sources
        """
        query_parts = [cancer_type, treatment_type]
        if cancer_stage:
            query_parts.append(f"stage {cancer_stage}")
        if biomarkers:
            query_parts.extend(biomarkers)
        
        query = " ".join(query_parts)
        
        return self.retrieve_evidence(
            query=query,
            top_k=10,
            cancer_types=[cancer_type],
            source_types=['nccn_guideline', 'esmo_guideline', 'asco_guideline', 
                         'pubmed_study', 'systematic_review', 'meta_analysis']
        )
    
    def retrieve_guideline_recommendations(self, cancer_type: str, cancer_stage: str) -> Dict:
        """
        Retrieve key guideline recommendations for a cancer type and stage
        
        Args:
            cancer_type: Type of cancer
            cancer_stage: Cancer stage
            
        Returns:
            Dictionary of recommendations by guideline source
        """
        query = f"{cancer_type} {cancer_stage} treatment recommendations"
        
        guideline_sources = EvidenceSource.objects.filter(
            Q(is_active=True) & Q(source_type__in=['nccn_guideline', 'esmo_guideline', 'asco_guideline']),
            cancer_types__overlap=[cancer_type]
        )
        
        recommendations = {
            'nccn': [],
            'esmo': [],
            'asco': []
        }
        
        for source in guideline_sources:
            if 'nccn' in source.source_type.lower():
                recommendations['nccn'].append({
                    'title': source.title,
                    'key_findings': source.key_findings,
                    'strength': source.evidence_strength,
                    'url': source.guideline_url
                })
            elif 'esmo' in source.source_type.lower():
                recommendations['esmo'].append({
                    'title': source.title,
                    'key_findings': source.key_findings,
                    'strength': source.evidence_strength,
                    'url': source.guideline_url
                })
            elif 'asco' in source.source_type.lower():
                recommendations['asco'].append({
                    'title': source.title,
                    'key_findings': source.key_findings,
                    'strength': source.evidence_strength,
                    'url': source.guideline_url
                })
        
        return recommendations
    
    def batch_embed_evidence(self, max_batch_size: int = 100):
        """
        Embed all evidence sources that don't have embeddings yet (batch operation)
        Useful for initialization
        
        Args:
            max_batch_size: Maximum number to process in one batch
        """
        if not self.initialized:
            logger.warning("Retriever not initialized. Cannot batch embed.")
            return
        
        # Get sources without embeddings
        sources_to_embed = EvidenceSource.objects.filter(embedding__isnull=True, is_active=True)[:max_batch_size]
        
        count = 0
        for source in sources_to_embed:
            try:
                text_to_embed = f"{source.title} {source.abstract or ''} {source.key_findings or ''}"
                source.embedding = self.get_embedding(text_to_embed)
                source.last_indexed = datetime.now()
                source.save(update_fields=['embedding', 'last_indexed'])
                count += 1
            except Exception as e:
                logger.error(f"Failed to embed source {source.id}: {str(e)}")
        
        logger.info(f"Batch embedded {count} evidence sources")
        return count


class EvidenceSynthesizer:
    """
    Synthesizes retrieved evidence into coherent explanations with citations
    """
    
    @staticmethod
    def synthesize_recommendation_rationale(recommendation_text: str, 
                                           evidence_sources: List[Dict],
                                           patient_factors: Dict) -> Dict:
        """
        Create a comprehensive rationale for a recommendation based on evidence
        
        Args:
            recommendation_text: The treatment recommendation
            evidence_sources: Retrieved evidence from RAG pipeline
            patient_factors: Relevant patient factors influencing decision
            
        Returns:
            Synthesized rationale with citations
        """
        
        # Organize evidence by type
        guidelines = [e for e in evidence_sources if 'guideline' in e['source_type']]
        studies = [e for e in evidence_sources if 'study' in e['source_type'] or 'pubmed' in e['source_type']]
        reviews = [e for e in evidence_sources if 'review' in e['source_type']]
        
        rationale = {
            'recommendation': recommendation_text,
            'evidence_summary': {
                'total_sources': len(evidence_sources),
                'average_relevance': sum(e['relevance_score'] for e in evidence_sources) / len(evidence_sources) if evidence_sources else 0,
                'evidence_strength_distribution': _get_strength_distribution(evidence_sources)
            },
            'guideline_basis': [],
            'clinical_evidence': [],
            'patient_factors': patient_factors,
            'citations': []
        }
        
        # Add guideline recommendations
        for guideline in guidelines[:3]:  # Top 3 guidelines
            guideline_entry = {
                'source': guideline['title'],
                'strength': guideline['evidence_strength'],
                'key_finding': guideline['key_findings'][:200] + '...' if guideline['key_findings'] else '',
                'url': guideline.get('guideline_url', '')
            }
            rationale['guideline_basis'].append(guideline_entry)
            rationale['citations'].append(_format_citation(guideline))
        
        # Add clinical evidence
        for study in studies[:5]:  # Top 5 studies
            study_entry = {
                'title': study['title'],
                'authors': study['authors'],
                'year': study['year'],
                'strength': study['evidence_strength'],
                'pmid': study['pmid'],
                'relevance_score': study['relevance_score']
            }
            rationale['clinical_evidence'].append(study_entry)
            rationale['citations'].append(_format_citation(study))
        
        return rationale
    
    @staticmethod
    def generate_explanation_text(rationale: Dict) -> str:
        """
        Generate human-readable explanation text from rationale
        
        Args:
            rationale: Synthesized rationale
            
        Returns:
            Formatted explanation text
        """
        explanation = f"""
TREATMENT RECOMMENDATION: {rationale['recommendation']}

CLINICAL RATIONALE:
This recommendation is based on the following evidence:

GUIDELINE-BASED EVIDENCE:
"""
        
        for guideline in rationale['guideline_basis']:
            explanation += f"\n• {guideline['source']} (Evidence Strength: {guideline['strength']})"
            if guideline['key_finding']:
                explanation += f"\n  Key Finding: {guideline['key_finding']}"
        
        explanation += "\n\nCLINICAL STUDIES:"
        for study in rationale['clinical_evidence']:
            explanation += f"\n• {study['authors']} et al. ({study['year']}). {study['title']}"
            if study['pmid']:
                explanation += f"\n  PMID: {study['pmid']}"
            explanation += f"\n  Evidence Strength: {study['strength']} | Relevance: {study['relevance_score']:.2%}"
        
        explanation += "\n\nPATIENT-SPECIFIC FACTORS:"
        for factor, value in rationale['patient_factors'].items():
            explanation += f"\n• {factor}: {value}"
        
        explanation += "\n\nCITATIONS:\n"
        for i, citation in enumerate(rationale['citations'], 1):
            explanation += f"{i}. {citation}\n"
        
        return explanation


def _get_strength_distribution(evidence_sources: List[Dict]) -> Dict:
    """Count evidence by strength level"""
    distribution = {'high': 0, 'moderate': 0, 'low': 0}
    for source in evidence_sources:
        strength = source.get('evidence_strength', 'moderate')
        if strength in distribution:
            distribution[strength] += 1
    return distribution


def _format_citation(evidence: Dict) -> str:
    """Format evidence as citation"""
    if evidence.get('pmid'):
        return f"{evidence.get('authors', 'Unknown')} et al. ({evidence.get('year', 'N/A')}). {evidence.get('title')}. PMID: {evidence['pmid']}"
    else:
        return f"{evidence.get('title', 'Unknown')}. {evidence.get('journal_or_organization', '')}. {evidence.get('year', '')}"
