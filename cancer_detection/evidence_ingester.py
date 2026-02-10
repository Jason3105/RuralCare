"""
Evidence Ingestion Engine
Ingests clinical guidelines and research papers (PDF, text, PubMed data)
Extracts and stores evidence in structured format
"""

import os
import json
import logging
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import requests
from django.db import transaction
from django.core.files.base import ContentFile

try:
    import PyPDF2
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from xml.etree import ElementTree as ET
    XML_SUPPORT = True
except ImportError:
    XML_SUPPORT = False

from .evidence_models import EvidenceSource
from .evidence_retriever import EvidenceRetriever

logger = logging.getLogger(__name__)


class PubMedIngester:
    """
    Ingests PubMed study data via NCBI E-utilities API
    No API key required for basic access
    """
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    # Cancer-related keywords for searches
    CANCER_KEYWORDS = {
        'breast': ['breast cancer', 'HER2+', 'hormone receptor', 'estrogen receptor'],
        'lung': ['lung cancer', 'EGFR', 'ALK', 'non-small cell'],
        'colorectal': ['colorectal cancer', 'colon cancer', 'rectal cancer'],
        'prostate': ['prostate cancer', 'PSA', 'androgen deprivation'],
    }
    
    TREATMENT_KEYWORDS = {
        'chemotherapy': ['chemotherapy', 'cytotoxic', 'FOLFOX', 'carboplatin'],
        'immunotherapy': ['immunotherapy', 'PD-1', 'PD-L1', 'checkpoint inhibitor'],
        'targeted_therapy': ['targeted therapy', 'tyrosine kinase', 'monoclonal antibody'],
        'radiation': ['radiation therapy', 'radiotherapy', 'SBRT'],
        'surgery': ['surgical resection', 'mastectomy', 'lobectomy'],
    }
    
    def search_pubmed(self, query: str, max_results: int = 10, 
                     filters: Optional[Dict] = None) -> List[str]:
        """
        Search PubMed for relevant studies
        
        Args:
            query: Search query (e.g., "breast cancer HER2+ chemotherapy")
            max_results: Maximum number of PMIDs to return
            filters: Additional filters (e.g., {'min_date': '2020/01/01'})
            
        Returns:
            List of PubMed IDs (PMIDs)
        """
        try:
            # Build search query
            search_query = query
            if filters and 'min_date' in filters:
                min_date = filters['min_date'].split('/')[0]
                search_query += f" AND {min_date}[DP]"
            
            # Add study type preferences
            search_query += " AND (randomized OR systematic OR meta-analysis OR clinical trial OR cohort)"
            
            # Search
            params = {
                'db': 'pubmed',
                'term': search_query,
                'rettype': 'uilist',
                'retmax': max_results,
                'tool': 'cancer_treatment_system',
                'email': 'system@cancerfree.india'
            }
            
            response = requests.get(f"{self.BASE_URL}/esearch.fcgi", params=params, timeout=10)
            response.raise_for_status()
            
            # Parse response
            root = ET.fromstring(response.content)
            pmids = [id_elem.text for id_elem in root.findall('.//Id')]
            
            logger.info(f"PubMed search returned {len(pmids)} results for query: {query}")
            return pmids
            
        except Exception as e:
            logger.error(f"PubMed search failed: {str(e)}")
            return []
    
    def fetch_study_details(self, pmid: str) -> Optional[Dict]:
        """
        Fetch detailed information about a PubMed study
        
        Args:
            pmid: PubMed ID
            
        Returns:
            Dictionary with study details or None if fetch failed
        """
        try:
            params = {
                'db': 'pubmed',
                'id': pmid,
                'rettype': 'abstract',
                'retmode': 'xml',
                'tool': 'cancer_treatment_system',
                'email': 'system@cancerfree.india'
            }
            
            response = requests.get(f"{self.BASE_URL}/efetch.fcgi", params=params, timeout=10)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            
            # Extract article information
            article = root.find('.//Article')
            if article is None:
                return None
            
            # Extract title
            title_elem = article.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None else ''
            
            # Extract authors
            authors_list = []
            for author in article.findall('.//Author'):
                last_name = author.findtext('LastName', '')
                first_init = author.findtext('Initials', '')
                if last_name and first_init:
                    authors_list.append(f"{last_name} {first_init}")
            authors = ', '.join(authors_list[:3])  # First 3 authors
            
            # Extract year
            pub_date = article.find('.//PubDate')
            year = pub_date.findtext('Year', '') if pub_date is not None else ''
            
            # Extract journal
            journal = article.findtext('.//Journal/Title', '')
            
            # Extract abstract
            abstract_elem = article.find('.//Abstract')
            abstract = ''
            if abstract_elem is not None:
                abstract_texts = []
                for abstract_text in abstract_elem.findall('.//AbstractText'):
                    if abstract_text.text:
                        abstract_texts.append(abstract_text.text)
                abstract = ' '.join(abstract_texts)
            
            # Extract DOI
            doi = ''
            for article_id in article.findall('.//ArticleId'):
                if article_id.get('IdType') == 'doi':
                    doi = article_id.text
                    break
            
            return {
                'pmid': pmid,
                'title': title,
                'authors': authors,
                'year': int(year) if year.isdigit() else None,
                'journal': journal,
                'abstract': abstract,
                'doi': doi,
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch PubMed details for PMID {pmid}: {str(e)}")
            return None
    
    @transaction.atomic
    def ingest_pubmed_study(self, pmid: str, 
                           cancer_types: Optional[List[str]] = None,
                           treatment_types: Optional[List[str]] = None) -> Optional[EvidenceSource]:
        """
        Ingest a PubMed study into the database
        
        Args:
            pmid: PubMed ID
            cancer_types: Associated cancer types
            treatment_types: Associated treatment types
            
        Returns:
            Created EvidenceSource object or None if failed
        """
        
        # Check if already ingested
        if EvidenceSource.objects.filter(pmid=pmid).exists():
            logger.info(f"PMID {pmid} already in database")
            return EvidenceSource.objects.get(pmid=pmid)
        
        # Fetch details
        details = self.fetch_study_details(pmid)
        if not details:
            return None
        
        # Determine evidence strength (heuristic based on study type)
        # In production, this would be more sophisticated
        abstract_lower = (details.get('abstract', '') or '').lower()
        if any(term in abstract_lower for term in ['meta-analysis', 'systematic review']):
            strength = 'high'
        elif any(term in abstract_lower for term in ['randomized', 'rct', 'prospective']):
            strength = 'moderate'
        else:
            strength = 'moderate'
        
        # Create evidence source
        evidence = EvidenceSource.objects.create(
            title=details['title'],
            source_type='pubmed_study',
            authors=details['authors'],
            publication_year=details['year'],
            journal_or_organization=details['journal'],
            pmid=pmid,
            doi=details.get('doi', ''),
            abstract=details['abstract'],
            evidence_strength=strength,
            cancer_types=cancer_types or [],
            treatment_types=treatment_types or [],
            last_indexed=datetime.now(),
        )
        
        logger.info(f"Ingested PubMed study {pmid}: {evidence.title}")
        return evidence


class GuidelineIngester:
    """
    Ingests clinical guidelines from NCCN, ESMO, ASCO
    Parses structured guideline data
    """
    
    # Sample guideline data (in production, would parse from APIs or PDFs)
    NCCN_GUIDELINES = {
        'breast': {
            'stage_1': {
                'recommendations': [
                    'Surgery (lumpectomy or mastectomy)',
                    'Sentinel lymph node biopsy',
                    'Radiation therapy (if lumpectomy)',
                    'Hormonal therapy if HR+',
                    'HER2-targeted therapy if HER2+',
                ],
                'version': '2024',
                'url': 'https://www.nccn.org/guidelines/guidelines-detail?category=1&id=1419'
            },
            'stage_2': {
                'recommendations': [
                    'Surgery with axillary assessment',
                    'Radiation therapy',
                    'Adjuvant chemotherapy',
                    'Hormonal therapy if HR+',
                    'HER2-targeted therapy if HER2+',
                ],
                'version': '2024',
                'url': 'https://www.nccn.org/guidelines/guidelines-detail?category=1&id=1419'
            }
        },
        'lung': {
            'stage_1': {
                'recommendations': [
                    'Surgical resection',
                    'Stereotactic body radiation (if not surgical candidate)',
                    'Adjuvant chemotherapy (selected patients)',
                    'Targeted therapy if mutation present',
                ],
                'version': '2024',
                'url': 'https://www.nccn.org/guidelines/guidelines-detail?category=1&id=1450'
            },
        }
    }
    
    @transaction.atomic
    def ingest_guideline(self, guideline_data: Dict) -> Optional[EvidenceSource]:
        """
        Ingest a clinical guideline
        
        Args:
            guideline_data: Dictionary with guideline information
                Required keys: title, source_type, organization, cancer_types
                Optional: url, version, key_findings, treatments
                
        Returns:
            Created EvidenceSource or None
        """
        
        # Check if already exists
        existing = EvidenceSource.objects.filter(
            title=guideline_data['title'],
            source_type=guideline_data['source_type']
        ).first()
        
        if existing:
            logger.info(f"Guideline '{guideline_data['title']}' already in database")
            return existing
        
        # Create guideline evidence
        evidence = EvidenceSource.objects.create(
            title=guideline_data['title'],
            source_type=guideline_data['source_type'],
            journal_or_organization=guideline_data.get('organization', ''),
            cancer_types=guideline_data.get('cancer_types', []),
            treatment_types=guideline_data.get('treatment_types', []),
            key_findings='\n'.join(guideline_data.get('treatments', [])) if guideline_data.get('treatments') else '',
            guideline_url=guideline_data.get('url', ''),
            guideline_version=guideline_data.get('version', ''),
            evidence_strength='high',  # Guidelines are typically high strength
            publication_year=datetime.now().year,
            last_indexed=datetime.now(),
        )
        
        logger.info(f"Ingested guideline: {evidence.title}")
        return evidence
    
    def ingest_default_guidelines(self):
        """
        Ingest default NCCN guidelines for common cancers
        """
        count = 0
        
        for cancer, stages in self.NCCN_GUIDELINES.items():
            for stage, data in stages.items():
                guideline_data = {
                    'title': f"NCCN {cancer.capitalize()} Cancer {stage.replace('_', ' ').title()}",
                    'source_type': 'nccn_guideline',
                    'organization': 'National Comprehensive Cancer Network (NCCN)',
                    'cancer_types': [cancer],
                    'treatment_types': ['surgery', 'chemotherapy', 'radiation', 'targeted_therapy'],
                    'treatments': data['recommendations'],
                    'version': data.get('version', ''),
                    'url': data.get('url', ''),
                }
                
                if self.ingest_guideline(guideline_data):
                    count += 1
        
        logger.info(f"Ingested {count} default NCCN guidelines")
        return count


class PDFGuidelineParser:
    """
    Parses clinical guideline PDFs (requires PyPDF2)
    Extracts key recommendations and clinical evidence
    """
    
    def __init__(self):
        self.pdf_support = PDF_SUPPORT
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from PDF file
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Extracted text
        """
        if not self.pdf_support:
            logger.error("PyPDF2 not available. Cannot parse PDFs.")
            return ""
        
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text()
            return text
        except Exception as e:
            logger.error(f"Failed to extract text from PDF {pdf_path}: {str(e)}")
            return ""
    
    def parse_guideline_pdf(self, pdf_path: str, title: str, 
                          organization: str, cancer_types: List[str]) -> Optional[EvidenceSource]:
        """
        Parse a clinical guideline PDF and ingest to database
        
        Args:
            pdf_path: Path to PDF file
            title: Title of the guideline
            organization: Organization that published it (NCCN, ESMO, ASCO)
            cancer_types: Associated cancer types
            
        Returns:
            Created EvidenceSource or None
        """
        
        # Extract text
        text = self.extract_text_from_pdf(pdf_path)
        if not text:
            logger.error(f"Could not extract text from PDF: {pdf_path}")
            return None
        
        # Extract key findings (simple heuristic)
        key_findings = self._extract_key_sections(text)
        
        # Determine source type
        org_lower = organization.lower()
        if 'nccn' in org_lower:
            source_type = 'nccn_guideline'
        elif 'esmo' in org_lower:
            source_type = 'esmo_guideline'
        elif 'asco' in org_lower:
            source_type = 'asco_guideline'
        else:
            source_type = 'other'
        
        # Create evidence source
        evidence = EvidenceSource.objects.create(
            title=title,
            source_type=source_type,
            journal_or_organization=organization,
            cancer_types=cancer_types,
            full_text=text,
            key_findings=key_findings,
            abstract=text[:500],  # First 500 chars as abstract
            evidence_strength='high',
            publication_year=datetime.now().year,
            last_indexed=datetime.now(),
        )
        
        logger.info(f"Ingested PDF guideline: {evidence.title}")
        return evidence
    
    @staticmethod
    def _extract_key_sections(text: str, max_length: int = 1000) -> str:
        """
        Extract key sections from guideline text
        
        Args:
            text: Full guideline text
            max_length: Maximum length of extraction
            
        Returns:
            Key findings text
        """
        
        # Look for recommendations, treatment, management sections
        patterns = [
            r'(recommendation|treatment|management|approach)[\s\S]{0,500}',
            r'(primary|adjuvant|neoadjuvant)[\s\S]{0,300}',
            r'(stage \d+?)[\s\S]{0,200}',
        ]
        
        key_findings = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            key_findings.extend(matches[:2])  # Take first 2 matches per pattern
        
        # Combine and truncate
        result = ' '.join(key_findings)[:max_length]
        return result


class EvidenceIngestionService:
    """
    High-level service coordinating all evidence ingestion
    """
    
    def __init__(self):
        self.pubmed_ingester = PubMedIngester()
        self.guideline_ingester = GuidelineIngester()
        self.pdf_parser = PDFGuidelineParser()
        self.retriever = EvidenceRetriever()
    
    def initialize_default_evidence(self):
        """
        Initialize database with default evidence (guidelines and sample studies)
        """
        logger.info("Initializing default evidence database...")
        
        # Ingest default NCCN guidelines
        guideline_count = self.guideline_ingester.ingest_default_guidelines()
        
        # Optionally search and ingest recent PubMed studies
        # (This can be called separately to avoid long initialization)
        
        logger.info(f"Initialization complete: {guideline_count} guidelines ingested")
        return {'guidelines': guideline_count}
    
    def search_and_ingest_studies(self, cancer_type: str, treatment_type: str,
                                 max_results: int = 5) -> Dict:
        """
        Search PubMed and ingest relevant studies
        
        Args:
            cancer_type: Type of cancer
            treatment_type: Treatment type
            max_results: Maximum studies to ingest
            
        Returns:
            Dictionary with ingestion results
        """
        
        query = f"{cancer_type} cancer {treatment_type}"
        pmids = self.pubmed_ingester.search_pubmed(query, max_results=max_results)
        
        ingested = []
        for pmid in pmids:
            evidence = self.pubmed_ingester.ingest_pubmed_study(
                pmid,
                cancer_types=[cancer_type],
                treatment_types=[treatment_type]
            )
            if evidence:
                ingested.append(evidence)
        
        logger.info(f"Ingested {len(ingested)} studies for {cancer_type} + {treatment_type}")
        return {
            'cancer_type': cancer_type,
            'treatment_type': treatment_type,
            'studies_ingested': len(ingested),
            'studies': [
                {
                    'pmid': e.pmid,
                    'title': e.title,
                    'year': e.publication_year,
                    'strength': e.evidence_strength,
                }
                for e in ingested
            ]
        }
