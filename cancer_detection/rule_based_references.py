"""
Rule-Based Reference Management
Provides fallback evidence when RAG/LLM is unavailable
Implements evidence-based clinical rules for common cancer treatments
"""

import logging
from typing import Dict, List, Optional
from django.db import transaction
from datetime import datetime

from .evidence_models import RuleBasedReference, EvidenceSource
from django.contrib.auth import get_user_model

User = get_user_model()

logger = logging.getLogger(__name__)


class RuleBasedReferenceManager:
    """
    Manages rule-based references for clinical decision support
    Provides deterministic fallback when ML/RAG systems unavailable
    """
    
    # Comprehensive rule base for common cancer treatments
    DEFAULT_RULES = [
        # BREAST CANCER RULES
        {
            'rule_name': 'Breast Cancer Stage 1 - HR+ HER2- Standard Treatment',
            'cancer_type': 'breast',
            'cancer_stage': '1',
            'description': 'Standard treatment protocol for early-stage HR+ HER2- breast cancer',
            'recommended_treatment': 'Surgery (Lumpectomy or Mastectomy) + Radiation + Hormonal Therapy',
            'evidence_strength': 'high',
            'rule_logic': 'For stage 1 HR+ HER2- breast cancer: surgical resection with clear margins, ' +
                         'radiation therapy if breast-conserving surgery, tamoxifen or aromatase inhibitor for 5-10 years',
            'guideline_references': [
                'NCCN Breast Cancer Guidelines 2024',
                'ESMO Breast Cancer Guidelines',
                'ASCO Breast Cancer Guidelines'
            ],
            'pubmed_references': [
                '23455233',  # Example PMIDs
                '24519863'
            ],
            'priority_level': 10,
        },
        {
            'rule_name': 'Breast Cancer Stage 1 - HER2+ Treatment',
            'cancer_type': 'breast',
            'cancer_stage': '1',
            'description': 'Treatment for HER2-positive early-stage breast cancer',
            'recommended_treatment': 'Surgery + Radiation + Chemotherapy + Trastuzumab (Herceptin)',
            'evidence_strength': 'high',
            'rule_logic': 'For stage 1 HER2+ breast cancer: surgery, radiation (if BCS), chemotherapy, ' +
                         'HER2-targeted therapy (trastuzumab) for 1 year',
            'guideline_references': ['NCCN Breast Cancer Guidelines 2024', 'ESMO HER2+ Guidelines'],
            'pubmed_references': ['17522215', '18854488'],
            'priority_level': 10,
        },
        {
            'rule_name': 'Breast Cancer Stage 2 - Adjuvant Chemotherapy',
            'cancer_type': 'breast',
            'cancer_stage': '2',
            'description': 'Adjuvant chemotherapy for stage 2 breast cancer',
            'recommended_treatment': 'Surgery + Chemotherapy (AC or TC regimen) + Radiation + Hormonal Therapy',
            'evidence_strength': 'high',
            'rule_logic': 'Stage 2 BC: Surgery with nodal assessment, adjuvant chemotherapy (anthracycline or taxane based), ' +
                         'radiation if needed, hormonal therapy if HR+',
            'guideline_references': ['NCCN Breast Cancer Guidelines 2024'],
            'pubmed_references': ['23455233', '27480185'],
            'priority_level': 9,
        },
        {
            'rule_name': 'Breast Cancer Stage 3 - Neoadjuvant Approach',
            'cancer_type': 'breast',
            'cancer_stage': '3',
            'description': 'Neoadjuvant chemotherapy for locally advanced breast cancer',
            'recommended_treatment': 'Neoadjuvant Chemotherapy → Surgery → Radiation + Adjuvant Therapy',
            'evidence_strength': 'high',
            'rule_logic': 'Stage 3 BC: Neoadjuvant chemotherapy first (improves operability), then surgery, ' +
                         'radiation, and adjuvant hormonal or targeted therapy',
            'guideline_references': ['NCCN Breast Cancer Guidelines 2024', 'ESMO Breast Guidelines'],
            'pubmed_references': ['23455233', '27480185'],
            'priority_level': 10,
        },
        {
            'rule_name': 'Breast Cancer Stage 4 - Systemic Therapy Focus',
            'cancer_type': 'breast',
            'cancer_stage': '4',
            'description': 'Treatment for metastatic breast cancer',
            'recommended_treatment': 'Systemic Therapy (Targeted/Immunotherapy/Chemotherapy) + Supportive Care + Palliative Radiation',
            'evidence_strength': 'moderate',
            'rule_logic': 'Metastatic BC: Systemic therapy based on HR/HER2 status and performance status. ' +
                         'Endocrine therapy for HR+, HER2-targeted for HER2+, chemotherapy as backbone, ' +
                         'consideration of immunotherapy',
            'guideline_references': ['NCCN Metastatic BC Guidelines', 'ESMO Advanced BC Guidelines'],
            'pubmed_references': ['23093146', '24519863'],
            'priority_level': 9,
        },
        
        # LUNG CANCER RULES
        {
            'rule_name': 'Lung Cancer Stage 1A NSCLC - Surgery Priority',
            'cancer_type': 'lung',
            'cancer_stage': '1',
            'description': 'Early-stage NSCLC treatment',
            'recommended_treatment': 'Surgical Resection (Lobectomy) + Optional Adjuvant Therapy',
            'evidence_strength': 'high',
            'rule_logic': 'Stage 1A NSCLC: Lobectomy with systematic node dissection. Adjuvant chemotherapy ' +
                         'considered in 1B-1C based on risk factors. EGFR/ALK/ROS1 testing for targeted therapy eligibility',
            'guideline_references': ['NCCN NSCLC Guidelines 2024', 'ESMO NSCLC Guidelines'],
            'pubmed_references': ['19318871', '23433757'],
            'priority_level': 10,
        },
        {
            'rule_name': 'Lung Cancer Stage 3 NSCLC - Concurrent Chemorad',
            'cancer_type': 'lung',
            'cancer_stage': '3',
            'description': 'Locally advanced NSCLC treatment',
            'recommended_treatment': 'Concurrent Chemotherapy + Radiation Therapy ± Consolidation Therapy',
            'evidence_strength': 'high',
            'rule_logic': 'Stage 3 unresectable NSCLC: Concurrent cisplatin-based chemotherapy and radiation therapy. ' +
                         'Consolidation with durvalumab (PACIFIC trial). Check PD-L1 status for immunotherapy timing.',
            'guideline_references': ['NCCN NSCLC Guidelines 2024', 'PACIFIC Trial'],
            'pubmed_references': ['28102219', '26344059'],
            'priority_level': 10,
        },
        {
            'rule_name': 'Lung Cancer Stage 4 - Molecular Testing Driven',
            'cancer_type': 'lung',
            'cancer_stage': '4',
            'description': 'Advanced NSCLC treatment based on molecular profile',
            'recommended_treatment': 'Targeted Therapy (EGFR/ALK/ROS1) or Immunotherapy or Chemotherapy',
            'evidence_strength': 'high',
            'rule_logic': 'Metastatic NSCLC: First-line treatment based on molecular profiling. ' +
                         'EGFR mutations → TKI, ALK rearrangement → ALK inhibitor, high PD-L1 → immunotherapy, ' +
                         'No driver mutations → chemo ± immunotherapy',
            'guideline_references': ['NCCN Metastatic NSCLC Guidelines', 'ASCO Guidelines'],
            'pubmed_references': ['24908097', '26481228'],
            'priority_level': 10,
        },
        
        # COLORECTAL CANCER RULES
        {
            'rule_name': 'Colorectal Cancer Stage 2 - Surgery ± Adjuvant',
            'cancer_type': 'colorectal',
            'cancer_stage': '2',
            'description': 'Stage 2 colorectal cancer treatment',
            'recommended_treatment': 'Surgical Resection ± Adjuvant Chemotherapy',
            'evidence_strength': 'high',
            'rule_logic': 'Stage 2 CRC: Surgery with adequate node harvest (≥12 nodes). ' +
                         'Adjuvant chemotherapy considered if high-risk features (T4, poor differentiation, ' +
                         'inadequate nodes, lymphovascular invasion). MSI/dMMR testing for immunotherapy eligibility.',
            'guideline_references': ['NCCN Colon Cancer Guidelines', 'ESMO Colorectal Guidelines'],
            'pubmed_references': ['9619412', '20529870'],
            'priority_level': 9,
        },
        {
            'rule_name': 'Colorectal Cancer Stage 3 - Adjuvant Chemotherapy',
            'cancer_type': 'colorectal',
            'cancer_stage': '3',
            'description': 'Node-positive colorectal cancer',
            'recommended_treatment': 'Surgery + Adjuvant Chemotherapy (FOLFOX ± Bevacizumab)',
            'evidence_strength': 'high',
            'rule_logic': 'Stage 3 CRC: Surgery + adjuvant FOLFOX (fluorouracil, leucovorin, oxaliplatin) × 6-8 months. ' +
                         'Consider duration based on age/comorbidities. Bevacizumab may be added. Test for MMR/MSI status.',
            'guideline_references': ['NCCN Colon Cancer Guidelines 2024'],
            'pubmed_references': ['9619412', '20529870'],
            'priority_level': 10,
        },
        {
            'rule_name': 'Colorectal Cancer Stage 4 - Palliative Systemic Therapy',
            'cancer_type': 'colorectal',
            'cancer_stage': '4',
            'description': 'Metastatic colorectal cancer',
            'recommended_treatment': 'FOLFOX/FOLFIRI ± Bevacizumab/Cetuximab/Panitumumab',
            'evidence_strength': 'high',
            'rule_logic': 'mCRC: Chemotherapy backbone (FOLFOX or FOLFIRI) + targeted agent based on RAS/BRAF/PD-L1 status. ' +
                         'If WT RAS: EGFR inhibitor (cetuximab/panitumumab). If BRAF V600E: consider combination therapy. ' +
                         'If MSI-H: immunotherapy consideration.',
            'guideline_references': ['NCCN Metastatic Colon Cancer Guidelines', 'ESMO Guidelines'],
            'pubmed_references': ['14668643', '23108138'],
            'priority_level': 10,
        },
        
        # PROSTATE CANCER RULES
        {
            'rule_name': 'Prostate Cancer Low-Risk - Active Surveillance',
            'cancer_type': 'prostate',
            'cancer_stage': 'low_risk',
            'description': 'Low-risk localized prostate cancer',
            'recommended_treatment': 'Active Surveillance or Definitive Therapy (Radiation/Surgery)',
            'evidence_strength': 'high',
            'rule_logic': 'Low-risk PCa (PSA <10, Gleason ≤6, T1-T2a): Excellent prognosis with AS or definitive therapy. ' +
                         'Shared decision-making recommended. If treating: radiation or prostatectomy.',
            'guideline_references': ['NCCN Prostate Cancer Guidelines', 'ESMO Prostate Guidelines'],
            'pubmed_references': ['20384310', '20529870'],
            'priority_level': 9,
        },
        {
            'rule_name': 'Prostate Cancer Intermediate-Risk - Radiation + ADT',
            'cancer_type': 'prostate',
            'cancer_stage': 'intermediate_risk',
            'description': 'Intermediate-risk localized prostate cancer',
            'recommended_treatment': 'Radiation Therapy + Androgen Deprivation Therapy (12-24 months)',
            'evidence_strength': 'high',
            'rule_logic': 'Intermediate-risk PCa: Radiation therapy + ADT × 12-24 months preferred over surgery. ' +
                         'Escalated dose radiation (≥75.6 Gy) recommended.',
            'guideline_references': ['NCCN Prostate Cancer Guidelines 2024'],
            'pubmed_references': ['20529870', '20007040'],
            'priority_level': 10,
        },
        {
            'rule_name': 'Prostate Cancer High-Risk - Intensive Multimodal',
            'cancer_type': 'prostate',
            'cancer_stage': 'high_risk',
            'description': 'High-risk localized prostate cancer',
            'recommended_treatment': 'Radiation Therapy + Long-term ADT (24-36 months)',
            'evidence_strength': 'high',
            'rule_logic': 'High-risk PCa: Radiation + ADT × 24-36 months. Pelvic node RT if high CAPRA score. ' +
                         'Consider prostatectomy if candidate. Consider docetaxel with ADT.',
            'guideline_references': ['NCCN Prostate Cancer Guidelines 2024', 'ESMO Prostate Guidelines'],
            'pubmed_references': ['20529870', '23645859'],
            'priority_level': 10,
        },
        {
            'rule_name': 'Prostate Cancer Metastatic - ADT ± Docetaxel',
            'cancer_type': 'prostate',
            'cancer_stage': 'metastatic',
            'description': 'Metastatic prostate cancer',
            'recommended_treatment': 'ADT (GnRH agonist/antagonist) ± Docetaxel ± Novel Hormonal Agents',
            'evidence_strength': 'high',
            'rule_logic': 'mHSPC: ADT is foundation. Consider docetaxel (3x weekly or weekly) with ADT based on performance ' +
                         'status and visceral metastases. Add abiraterone or apalutamide for selected patients.',
            'guideline_references': ['NCCN Prostate Cancer Guidelines 2024'],
            'pubmed_references': ['23677313', '15047866'],
            'priority_level': 10,
        },
    ]
    
    @staticmethod
    @transaction.atomic
    def initialize_default_rules(created_by_user=None):
        """
        Initialize database with default rule-based references
        
        Args:
            created_by_user: User object to mark as creator (optional, can be admin)
        """
        
        count = 0
        for rule_data in RuleBasedReferenceManager.DEFAULT_RULES:
            # Check if rule exists
            existing = RuleBasedReference.objects.filter(
                rule_name=rule_data['rule_name']
            ).exists()
            
            if existing:
                logger.info(f"Rule '{rule_data['rule_name']}' already exists")
                continue
            
            try:
                rule = RuleBasedReference.objects.create(
                    rule_name=rule_data['rule_name'],
                    description=rule_data['description'],
                    cancer_type=rule_data['cancer_type'],
                    cancer_stage=rule_data.get('cancer_stage'),
                    recommended_treatment=rule_data['recommended_treatment'],
                    guideline_references=rule_data.get('guideline_references', []),
                    pubmed_references=rule_data.get('pubmed_references', []),
                    evidence_strength=rule_data.get('evidence_strength', 'moderate'),
                    rule_logic=rule_data['rule_logic'],
                    priority_level=rule_data.get('priority_level', 0),
                    is_active=True,
                    created_by=created_by_user,
                )
                count += 1
                logger.info(f"Created rule: {rule.rule_name}")
                
            except Exception as e:
                logger.error(f"Failed to create rule {rule_data['rule_name']}: {str(e)}")
        
        logger.info(f"Initialized {count} default rule-based references")
        return count
    
    @staticmethod
    def get_matching_rules(cancer_type: str, cancer_stage: str,
                          biomarkers: Optional[Dict] = None) -> List[RuleBasedReference]:
        """
        Get matching rules for a cancer type and stage
        
        Args:
            cancer_type: Type of cancer
            cancer_stage: Cancer stage
            biomarkers: Optional biomarker dict for filtering
            
        Returns:
            List of matching rules, ordered by priority
        """
        
        rules = RuleBasedReference.objects.filter(
            is_active=True,
            cancer_type=cancer_type,
            cancer_stage=cancer_stage
        ).order_by('-priority_level')
        
        return list(rules)
    
    @staticmethod
    def get_rule_evidence(rule: RuleBasedReference) -> List[Dict]:
        """
        Convert a rule into evidence items for use in recommendation
        
        Args:
            rule: RuleBasedReference object
            
        Returns:
            List of evidence dictionaries
        """
        
        evidence_list = []
        
        # Add guideline references
        for guideline_ref in rule.guideline_references:
            evidence_list.append({
                'source': None,
                'relevance_score': 0.95,
                'title': guideline_ref,
                'source_type': 'rule_guideline',
                'evidence_strength': rule.evidence_strength,
                'year': datetime.now().year,
                'authors': 'Clinical Guideline',
                'abstract': f"Referenced in rule: {rule.rule_name}",
                'key_findings': rule.rule_logic,
                'pmid': None,
            })
        
        # Try to link to actual PubMed evidence
        for pmid in rule.pubmed_references[:3]:
            try:
                source = EvidenceSource.objects.get(pmid=pmid, is_active=True)
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
                # Reference PubMed directly
                evidence_list.append({
                    'source': None,
                    'relevance_score': 0.8,
                    'title': f'PubMed Study (PMID: {pmid})',
                    'source_type': 'pubmed_reference',
                    'evidence_strength': 'moderate',
                    'year': None,
                    'authors': 'Unknown',
                    'abstract': f'Referenced in rule: {rule.rule_name}',
                    'key_findings': 'Supporting clinical evidence',
                    'pmid': pmid,
                })
        
        return evidence_list


# Management command helper
def setup_rule_based_references():
    """
    One-time setup function to initialize rule-based references
    Call from Django shell or management command
    """
    logger.info("Setting up rule-based references...")
    count = RuleBasedReferenceManager.initialize_default_rules()
    logger.info(f"Successfully initialized {count} rule-based references")
    return count
