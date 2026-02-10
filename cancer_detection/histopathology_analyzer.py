"""
Histopathology Report Analyzer
Uses NLP and pattern matching to extract key information from pathology reports
"""

import re
from typing import Dict, List, Optional
from datetime import datetime
import json


class HistopathologyAnalyzer:
    """
    Analyzes histopathology reports to extract:
    - Cancer type and subtype
    - Tumor grade
    - Stage information
    - Biomarker status (ER, PR, HER2, Ki-67, etc.)
    - Margin status
    - Lymph node involvement
    - Additional findings
    """
    
    # Common cancer types and their patterns
    CANCER_PATTERNS = {
        'breast': [
            r'breast\s+carcinoma',
            r'invasive\s+ductal\s+carcinoma',
            r'invasive\s+lobular\s+carcinoma',
            r'ductal\s+carcinoma\s+in\s+situ',
            r'triple\s+negative',
        ],
        'lung': [
            r'lung\s+carcinoma',
            r'non-small\s+cell\s+lung\s+cancer',
            r'small\s+cell\s+lung\s+cancer',
            r'adenocarcinoma\s+of\s+lung',
            r'squamous\s+cell\s+carcinoma',
        ],
        'colorectal': [
            r'colorectal\s+carcinoma',
            r'colon\s+cancer',
            r'rectal\s+cancer',
            r'adenocarcinoma\s+of\s+colon',
        ],
        'prostate': [
            r'prostate\s+cancer',
            r'prostatic\s+adenocarcinoma',
            r'gleason',
        ],
    }
    
    # Grade patterns
    GRADE_PATTERNS = {
        'grade_1': [r'grade\s*[1i]', r'well\s+differentiated', r'low\s+grade'],
        'grade_2': [r'grade\s*[2ii]', r'moderately\s+differentiated', r'intermediate\s+grade'],
        'grade_3': [r'grade\s*[3iii]', r'poorly\s+differentiated', r'high\s+grade'],
        'grade_4': [r'grade\s*[4iv]', r'undifferentiated'],
    }
    
    # Stage patterns
    STAGE_PATTERNS = {
        'stage_1': [r'stage\s*[1i]', r't1[abc]?\s+n0\s+m0', r'stage\s+i'],
        'stage_2': [r'stage\s*[2ii]', r't2[abc]?\s+n0\s+m0', r'stage\s+ii'],
        'stage_3': [r'stage\s*[3iii]', r't[123][abc]?\s+n[12]\s+m0', r'stage\s+iii'],
        'stage_4': [r'stage\s*[4iv]', r'm1', r'metastatic', r'stage\s+iv'],
    }
    
    # Biomarker patterns
    BIOMARKER_PATTERNS = {
        'er': [r'er\s*[:\-]?\s*(positive|negative|pos|neg|\+|\-)', r'estrogen\s+receptor'],
        'pr': [r'pr\s*[:\-]?\s*(positive|negative|pos|neg|\+|\-)', r'progesterone\s+receptor'],
        'her2': [r'her2?\s*[:\-]?\s*(positive|negative|pos|neg|\+|\-|0|1\+|2\+|3\+)', r'her-2/neu'],
        'ki67': [r'ki-?67\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*%?', r'ki67\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*%?'],
        'pd_l1': [r'pd-?l1\s*[:\-]?\s*(positive|negative|pos|neg|\+|\-|high|low)', r'programmed\s+death\s+ligand'],
        'msi': [r'msi-?(h|high|l|low|stable)', r'microsatellite\s+instability'],
        'egfr': [r'egfr\s*(mutation|mutant|wild|wt)', r'epidermal\s+growth\s+factor'],
        'alk': [r'alk\s*(positive|negative|fusion|rearrangement)', r'anaplastic\s+lymphoma\s+kinase'],
        'braf': [r'braf\s*(mutation|mutant|v600e)', r'braf\s*v600e'],
        'kras': [r'kras\s*(mutation|mutant|wild|wt)', r'k-ras'],
    }
    
    def __init__(self):
        """Initialize the analyzer"""
        self.extracted_data = {}
    
    def analyze_report(self, report_text: str) -> Dict:
        """
        Analyze histopathology report text
        
        Args:
            report_text: Raw text from pathology report
            
        Returns:
            Dictionary with extracted information
        """
        if not report_text:
            return self._empty_result()
        
        # Normalize text
        text = self._normalize_text(report_text)
        
        # Extract information
        result = {
            'cancer_type': self._extract_cancer_type(text),
            'cancer_subtype': self._extract_subtype(text),
            'grade': self._extract_grade(text),
            'stage': self._extract_stage(text),
            'tumor_size': self._extract_tumor_size(text),
            'margin_status': self._extract_margin_status(text),
            'lymph_node_status': self._extract_lymph_node_status(text),
            'biomarkers': self._extract_biomarkers(text),
            'additional_findings': self._extract_additional_findings(text),
            'confidence': self._calculate_confidence(text),
            'raw_text': report_text,
            'analysis_date': datetime.now().isoformat(),
        }
        
        return result
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for analysis"""
        # Convert to lowercase
        text = text.lower()
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep essential punctuation
        text = re.sub(r'[^\w\s\-\+\:\%]', ' ', text)
        return text
    
    def _extract_cancer_type(self, text: str) -> Dict:
        """Extract cancer type from text"""
        for cancer_type, patterns in self.CANCER_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return {
                        'type': cancer_type,
                        'confidence': 0.9,
                        'matched_pattern': pattern
                    }
        
        # Fallback: look for generic cancer terms
        if re.search(r'carcinoma|cancer|malignancy|tumor', text):
            return {
                'type': 'unknown',
                'confidence': 0.5,
                'note': 'Cancer detected but type unclear'
            }
        
        return {'type': None, 'confidence': 0.0}
    
    def _extract_subtype(self, text: str) -> Optional[str]:
        """Extract cancer subtype"""
        subtypes = {
            'invasive ductal carcinoma': r'invasive\s+ductal',
            'invasive lobular carcinoma': r'invasive\s+lobular',
            'ductal carcinoma in situ': r'ductal\s+carcinoma\s+in\s+situ|dcis',
            'adenocarcinoma': r'adenocarcinoma',
            'squamous cell carcinoma': r'squamous\s+cell',
            'small cell': r'small\s+cell',
            'large cell': r'large\s+cell',
        }
        
        for subtype, pattern in subtypes.items():
            if re.search(pattern, text, re.IGNORECASE):
                return subtype
        
        return None
    
    def _extract_grade(self, text: str) -> Dict:
        """Extract tumor grade"""
        for grade_key, patterns in self.GRADE_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    grade_num = grade_key.split('_')[1]
                    return {
                        'grade': grade_num,
                        'description': self._get_grade_description(grade_num),
                        'confidence': 0.85
                    }
        
        return {'grade': None, 'confidence': 0.0}
    
    def _get_grade_description(self, grade: str) -> str:
        """Get human-readable grade description"""
        descriptions = {
            '1': 'Well differentiated (Low grade)',
            '2': 'Moderately differentiated (Intermediate grade)',
            '3': 'Poorly differentiated (High grade)',
            '4': 'Undifferentiated (High grade)',
        }
        return descriptions.get(grade, 'Unknown')
    
    def _extract_stage(self, text: str) -> Dict:
        """Extract cancer stage"""
        # Try TNM staging first
        tnm_pattern = r'(t\d+[abc]?)\s*(n\d+[abc]?)?\s*(m\d+)?'
        tnm_match = re.search(tnm_pattern, text, re.IGNORECASE)
        
        if tnm_match:
            t_stage = tnm_match.group(1).upper()
            n_stage = tnm_match.group(2).upper() if tnm_match.group(2) else 'N0'
            m_stage = tnm_match.group(3).upper() if tnm_match.group(3) else 'M0'
            
            stage_num = self._tnm_to_stage(t_stage, n_stage, m_stage)
            return {
                'stage': stage_num,
                'tnm': f"{t_stage} {n_stage} {m_stage}",
                'confidence': 0.9
            }
        
        # Try stage patterns
        for stage_key, patterns in self.STAGE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    stage_num = stage_key.split('_')[1]
                    return {
                        'stage': stage_num,
                        'confidence': 0.8
                    }
        
        return {'stage': None, 'confidence': 0.0}
    
    def _tnm_to_stage(self, t: str, n: str, m: str) -> str:
        """Convert TNM staging to stage number"""
        if 'M1' in m.upper():
            return '4'
        
        t_num = int(re.search(r'\d+', t).group()) if re.search(r'\d+', t) else 0
        n_num = int(re.search(r'\d+', n).group()) if re.search(r'\d+', n) else 0
        
        if t_num <= 1 and n_num == 0:
            return '1'
        elif t_num <= 2 and n_num == 0:
            return '2'
        elif n_num >= 1 or t_num >= 3:
            return '3'
        
        return 'unknown'
    
    def _extract_tumor_size(self, text: str) -> Optional[Dict]:
        """Extract tumor size"""
        # Look for size in mm or cm
        size_patterns = [
            r'size[:\s]+(\d+(?:\.\d+)?)\s*(mm|cm|millimeter|centimeter)',
            r'(\d+(?:\.\d+)?)\s*(mm|cm)\s*(?:tumor|lesion|mass)',
            r'dimension[:\s]+(\d+(?:\.\d+)?)\s*(?:x\s*\d+(?:\.\d+)?)?\s*(mm|cm)',
        ]
        
        for pattern in size_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                size = float(match.group(1))
                unit = match.group(2).lower()
                if unit in ['cm', 'centimeter']:
                    size = size * 10  # Convert to mm
                
                return {
                    'size_mm': size,
                    'unit': 'mm',
                    'confidence': 0.85
                }
        
        return None
    
    def _extract_margin_status(self, text: str) -> Optional[Dict]:
        """Extract surgical margin status"""
        margin_patterns = [
            r'margin[:\s]+(positive|negative|involved|clear|free)',
            r'margins?\s+(positive|negative|involved|clear|free)',
        ]
        
        for pattern in margin_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                status = match.group(1).lower()
                is_positive = status in ['positive', 'involved']
                return {
                    'status': 'positive' if is_positive else 'negative',
                    'description': match.group(1),
                    'confidence': 0.9
                }
        
        return None
    
    def _extract_lymph_node_status(self, text: str) -> Dict:
        """Extract lymph node involvement"""
        # Look for lymph node counts
        ln_patterns = [
            r'lymph\s+node[:\s]+(\d+)\s*(?:of|/)\s*(\d+)\s*(?:positive|involved)',
            r'(\d+)\s*(?:of|/)\s*(\d+)\s*lymph\s+nodes?\s*(?:positive|involved)',
            r'nodal\s+status[:\s]+(positive|negative)',
        ]
        
        for pattern in ln_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    positive = int(match.group(1))
                    total = int(match.group(2))
                    return {
                        'involved': positive > 0,
                        'positive_count': positive,
                        'total_count': total,
                        'confidence': 0.9
                    }
                else:
                    is_positive = match.group(1).lower() == 'positive'
                    return {
                        'involved': is_positive,
                        'confidence': 0.8
                    }
        
        # Check for N stage in TNM
        if re.search(r'n[1-3]', text, re.IGNORECASE):
            return {
                'involved': True,
                'confidence': 0.7
            }
        elif re.search(r'n0', text, re.IGNORECASE):
            return {
                'involved': False,
                'confidence': 0.7
            }
        
        return {'involved': None, 'confidence': 0.0}
    
    def _extract_biomarkers(self, text: str) -> Dict:
        """Extract biomarker information"""
        biomarkers = {}
        
        for biomarker, patterns in self.BIOMARKER_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = self._parse_biomarker_value(biomarker, match)
                    if value:
                        biomarkers[biomarker] = value
                        break
        
        return biomarkers
    
    def _parse_biomarker_value(self, biomarker: str, match) -> Optional[Dict]:
        """Parse biomarker value from match"""
        groups = match.groups()
        
        if biomarker in ['er', 'pr', 'her2', 'pd_l1']:
            value_str = groups[0] if groups else match.group(0)
            value_lower = value_str.lower()
            
            if 'positive' in value_lower or '+' in value_str or value_str in ['3+', '2+']:
                return {
                    'status': 'positive',
                    'value': value_str,
                    'confidence': 0.9
                }
            elif 'negative' in value_lower or '-' in value_str or value_str in ['0', '1+']:
                return {
                    'status': 'negative',
                    'value': value_str,
                    'confidence': 0.9
                }
        
        elif biomarker == 'ki67':
            value = float(groups[0]) if groups else None
            if value is not None:
                return {
                    'percentage': value,
                    'interpretation': 'high' if value >= 20 else 'low',
                    'confidence': 0.9
                }
        
        elif biomarker in ['msi', 'egfr', 'alk', 'braf', 'kras']:
            value_str = groups[0] if groups else match.group(0)
            return {
                'status': value_str.lower(),
                'confidence': 0.85
            }
        
        return None
    
    def _extract_additional_findings(self, text: str) -> List[str]:
        """Extract additional findings"""
        findings = []
        
        # Look for common findings
        finding_patterns = {
            'lymphovascular invasion': r'lymphovascular\s+invasion|lvi',
            'perineural invasion': r'perineural\s+invasion|pni',
            'necrosis': r'necrosis|necrotic',
            'inflammation': r'inflammation|inflammatory',
            'calcification': r'calcification|calcified',
        }
        
        for finding, pattern in finding_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                findings.append(finding)
        
        return findings
    
    def _calculate_confidence(self, text: str) -> float:
        """Calculate overall confidence in extraction"""
        confidence_factors = []
        
        # Check for key terms
        if re.search(r'carcinoma|cancer|malignancy', text):
            confidence_factors.append(0.3)
        
        if re.search(r'grade|stage|tnm', text):
            confidence_factors.append(0.3)
        
        if re.search(r'biomarker|er|pr|her2', text):
            confidence_factors.append(0.2)
        
        if re.search(r'margin|lymph\s+node', text):
            confidence_factors.append(0.2)
        
        return sum(confidence_factors) if confidence_factors else 0.0
    
    def _empty_result(self) -> Dict:
        """Return empty result structure"""
        return {
            'cancer_type': {'type': None, 'confidence': 0.0},
            'cancer_subtype': None,
            'grade': {'grade': None, 'confidence': 0.0},
            'stage': {'stage': None, 'confidence': 0.0},
            'tumor_size': None,
            'margin_status': None,
            'lymph_node_status': {'involved': None, 'confidence': 0.0},
            'biomarkers': {},
            'additional_findings': [],
            'confidence': 0.0,
            'raw_text': '',
            'analysis_date': datetime.now().isoformat(),
        }

