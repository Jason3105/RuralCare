"""
Groq-based Fast Analyzer for Histopathology and Genomics Reports
Uses Groq's ultra-fast LLM inference for rapid medical report analysis
"""

import os
import json
from typing import Dict, Optional
from datetime import datetime


class GroqAnalyzer:
    """
    Fast medical report analyzer using Groq API
    Groq provides extremely fast LLM inference (often <1 second)
    """
    
    def __init__(self):
        """Initialize the Groq analyzer"""
        self.api_key = os.getenv('GROQ_API_KEY')
        self.client = None
        
        if self.api_key:
            try:
                from groq import Groq
                self.client = Groq(api_key=self.api_key)
            except ImportError:
                print("Groq package not installed")
            except Exception as e:
                print(f"Error initializing Groq client: {e}")
    
    def analyze_histopathology_report(self, report_text: str) -> Dict:
        """
        Analyze histopathology report using Groq LLM
        
        Args:
            report_text: Raw text from pathology report
            
        Returns:
            Dictionary with extracted information
        """
        if not self.client or not report_text:
            return self._empty_histopathology_result()
        
        # Truncate text if too long (keep first 4000 chars for speed)
        truncated_text = report_text[:4000] if len(report_text) > 4000 else report_text
        
        prompt = f"""Analyze this histopathology/pathology report and extract key information.
Return ONLY a valid JSON object with these exact fields (use null for missing info):

{{
    "cancer_type": "breast/lung/colorectal/prostate/other or null",
    "cancer_subtype": "specific subtype or null",
    "grade": "1/2/3/4 or null",
    "grade_description": "well/moderately/poorly differentiated or null",
    "stage": "1/2/3/4 or null",
    "tnm_staging": "T_N_M_ format or null",
    "tumor_size_mm": number or null,
    "margin_status": "positive/negative/close or null",
    "lymph_node_involved": true/false or null,
    "lymph_node_positive_count": number or null,
    "lymph_node_total_count": number or null,
    "biomarkers": {{
        "ER": "positive/negative or null",
        "PR": "positive/negative or null", 
        "HER2": "positive/negative/equivocal or null",
        "Ki67": number (percentage) or null,
        "PD_L1": "positive/negative/high/low or null",
        "MSI": "MSI-H/MSS/MSI-L or null"
    }},
    "additional_findings": ["finding1", "finding2"],
    "confidence": 0.0 to 1.0
}}

PATHOLOGY REPORT:
{truncated_text}

JSON RESPONSE:"""

        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",  # Fast model
                messages=[
                    {
                        "role": "system",
                        "content": "You are a medical AI assistant specialized in analyzing pathology reports. Extract structured data accurately. Return only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=1000,
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Try to parse JSON from response
            result = self._parse_json_response(result_text)
            result['analysis_date'] = datetime.now().isoformat()
            result['raw_text'] = report_text[:500]  # Store first 500 chars
            
            return result
            
        except Exception as e:
            print(f"Groq analysis error: {e}")
            return self._empty_histopathology_result()
    
    def analyze_genomic_profile(self, genomic_data: Dict) -> Dict:
        """
        Analyze genomic profile data using Groq LLM
        
        Args:
            genomic_data: Dictionary with mutations, biomarkers, etc.
            
        Returns:
            Dictionary with analysis results
        """
        if not self.client or not genomic_data:
            return self._empty_genomic_result()
        
        prompt = f"""Analyze this genomic profile and provide treatment recommendations.
Return ONLY a valid JSON object:

{{
    "actionable_mutations": ["mutation1", "mutation2"],
    "targeted_therapy_eligible": {{
        "therapy_name": "eligibility reason"
    }},
    "immunotherapy_eligible": {{
        "eligible": true/false,
        "reason": "explanation",
        "recommended_agents": ["agent1", "agent2"]
    }},
    "prognostic_profile": {{
        "overall": "favorable/intermediate/unfavorable",
        "factors": ["factor1", "factor2"]
    }},
    "clinical_trial_considerations": ["consideration1"],
    "confidence": 0.0 to 1.0
}}

GENOMIC DATA:
{json.dumps(genomic_data, indent=2)}

JSON RESPONSE:"""

        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a medical AI specialized in cancer genomics. Analyze mutation data and provide treatment eligibility assessments. Return only valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=1000,
            )
            
            result_text = response.choices[0].message.content.strip()
            result = self._parse_json_response(result_text)
            result['analysis_date'] = datetime.now().isoformat()
            
            return result
            
        except Exception as e:
            print(f"Groq genomic analysis error: {e}")
            return self._empty_genomic_result()
    
    def _parse_json_response(self, text: str) -> Dict:
        """Parse JSON from LLM response"""
        try:
            # Try direct parse first
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # Try to find JSON in the response
        try:
            # Look for JSON block
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end > start:
                json_str = text[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # Return empty dict if parsing fails
        return {}
    
    def _empty_histopathology_result(self) -> Dict:
        """Return empty histopathology result structure"""
        return {
            'cancer_type': None,
            'cancer_subtype': None,
            'grade': None,
            'grade_description': None,
            'stage': None,
            'tnm_staging': None,
            'tumor_size_mm': None,
            'margin_status': None,
            'lymph_node_involved': None,
            'lymph_node_positive_count': None,
            'lymph_node_total_count': None,
            'biomarkers': {},
            'additional_findings': [],
            'confidence': 0.0,
            'analysis_date': datetime.now().isoformat(),
        }
    
    def _empty_genomic_result(self) -> Dict:
        """Return empty genomic result structure"""
        return {
            'actionable_mutations': [],
            'targeted_therapy_eligible': {},
            'immunotherapy_eligible': {},
            'prognostic_profile': {},
            'clinical_trial_considerations': [],
            'confidence': 0.0,
            'analysis_date': datetime.now().isoformat(),
        }
    
    def is_available(self) -> bool:
        """Check if Groq API is available"""
        return self.client is not None
