"""
AI Confidence and XAI Generator Module
Generates deterministic explanations for AI decisions
"""

import json
import os
from typing import Dict, List, Optional, Any
from groq import Groq


class AIConfidenceGenerator:
    """Generates AI confidence metadata and explanations"""
    
    def __init__(self):
        self.groq_client = None
        api_key = os.getenv('GROQ_API_KEY')
        if api_key:
            self.groq_client = Groq(api_key=api_key)
    
    def calculate_confidence(
        self,
        analysis_type: str,
        data_sources: Dict[str, Any],
        ocr_quality: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Calculate confidence score based on available data and quality
        
        Returns:
            Dict with confidence scores, uncertainty reasons, and explanations
        """
        confidence_data = {
            'overall_confidence': 0.0,
            'data_quality_score': 0.0,
            'model_certainty_score': 0.0,
            'evidence_strength_score': 0.0,
            'confidence_level': 'moderate',
            'uncertainty_reasons': [],
            'missing_data_sources': [],
            'conflicting_outputs': [],
            'ocr_quality_score': ocr_quality,
            'evidence_breakdown': {},
            'detailed_explanation': '',
            'patient_explanation': ''
        }
        
        # Calculate data quality score
        required_sources = {
            'imaging': ['imaging_analysis', 'patient_history'],
            'histopathology': ['pathology_report', 'patient_history'],
            'genomic': ['genomic_data', 'patient_history'],
            'treatment_plan': ['imaging_analysis', 'pathology_report', 'genomic_data', 'patient_history'],
            'outcome_prediction': ['treatment_plan', 'patient_history', 'lab_values']
        }
        
        sources_needed = required_sources.get(analysis_type, [])
        sources_present = [s for s in sources_needed if data_sources.get(s)]
        sources_missing = [s for s in sources_needed if not data_sources.get(s)]
        
        if sources_needed:
            data_completeness = len(sources_present) / len(sources_needed)
        else:
            data_completeness = 0.5
        
        confidence_data['data_quality_score'] = data_completeness * 100
        confidence_data['missing_data_sources'] = [
            self._format_source_name(s) for s in sources_missing
        ]
        
        # Add uncertainty reasons for missing data
        for source in sources_missing:
            confidence_data['uncertainty_reasons'].append(
                f"Missing {self._format_source_name(source)}"
            )
        
        # Check OCR quality
        if ocr_quality is not None and ocr_quality < 80:
            confidence_data['uncertainty_reasons'].append(
                f"Low OCR quality ({ocr_quality:.0f}%)"
            )
        
        # Calculate model certainty based on analysis type
        model_certainty = self._calculate_model_certainty(analysis_type, data_sources)
        confidence_data['model_certainty_score'] = model_certainty
        
        # Check for conflicting outputs
        conflicts = self._detect_conflicts(data_sources)
        confidence_data['conflicting_outputs'] = conflicts
        for conflict in conflicts:
            confidence_data['uncertainty_reasons'].append(
                f"Conflicting results: {conflict.get('conflict', 'Unknown conflict')}"
            )
        
        # Calculate evidence strength
        evidence = self._calculate_evidence_strength(data_sources)
        confidence_data['evidence_strength_score'] = evidence['score']
        confidence_data['evidence_breakdown'] = evidence['breakdown']
        
        # Calculate overall confidence
        weights = {'data_quality': 0.3, 'model_certainty': 0.4, 'evidence': 0.3}
        overall = (
            confidence_data['data_quality_score'] * weights['data_quality'] +
            confidence_data['model_certainty_score'] * weights['model_certainty'] +
            confidence_data['evidence_strength_score'] * weights['evidence']
        )
        
        # Reduce confidence for conflicts and uncertainty
        penalty = len(confidence_data['uncertainty_reasons']) * 5
        overall = max(0, overall - penalty)
        
        confidence_data['overall_confidence'] = round(overall, 1)
        
        # Set confidence level
        if overall >= 80:
            confidence_data['confidence_level'] = 'high'
        elif overall >= 50:
            confidence_data['confidence_level'] = 'moderate'
        else:
            confidence_data['confidence_level'] = 'low'
        
        # Generate explanations
        confidence_data['detailed_explanation'] = self._generate_detailed_explanation(confidence_data)
        confidence_data['patient_explanation'] = self._generate_patient_explanation(confidence_data)
        
        return confidence_data
    
    def _format_source_name(self, source: str) -> str:
        """Convert source key to readable name"""
        mapping = {
            'imaging_analysis': 'Imaging Analysis',
            'pathology_report': 'Pathology Report',
            'genomic_data': 'Genomic Profile',
            'patient_history': 'Patient Medical History',
            'lab_values': 'Laboratory Values',
            'treatment_plan': 'Treatment Plan'
        }
        return mapping.get(source, source.replace('_', ' ').title())
    
    def _calculate_model_certainty(self, analysis_type: str, data_sources: Dict) -> float:
        """Calculate model certainty based on input quality"""
        base_certainty = 70.0
        
        # Adjust based on data completeness
        data_count = sum(1 for v in data_sources.values() if v)
        if data_count >= 4:
            base_certainty += 15
        elif data_count >= 2:
            base_certainty += 8
        
        # Adjust based on detection confidence if available
        if 'detection_confidence' in data_sources:
            dc = data_sources.get('detection_confidence', 0)
            if dc > 0.8:
                base_certainty += 10
            elif dc > 0.5:
                base_certainty += 5
        
        return min(100, base_certainty)
    
    def _detect_conflicts(self, data_sources: Dict) -> List[Dict]:
        """Detect conflicting outputs between modalities"""
        conflicts = []
        
        # Check stage conflicts
        stages = {}
        if data_sources.get('imaging_stage'):
            stages['Imaging'] = data_sources['imaging_stage']
        if data_sources.get('pathology_stage'):
            stages['Pathology'] = data_sources['pathology_stage']
        
        if len(stages) > 1:
            stage_values = list(stages.values())
            if stage_values[0] != stage_values[1]:
                sources = list(stages.keys())
                conflicts.append({
                    'source1': sources[0],
                    'source2': sources[1],
                    'conflict': f"Stage mismatch: {sources[0]} shows {stage_values[0]}, {sources[1]} shows {stage_values[1]}"
                })
        
        # Check biomarker conflicts
        if data_sources.get('her2_ihc') and data_sources.get('her2_fish'):
            ihc = data_sources['her2_ihc']
            fish = data_sources['her2_fish']
            if (ihc == 'positive' and fish == 'negative') or (ihc == 'negative' and fish == 'positive'):
                conflicts.append({
                    'source1': 'IHC',
                    'source2': 'FISH',
                    'conflict': f"HER2 status discordance: IHC {ihc}, FISH {fish}"
                })
        
        return conflicts
    
    def _calculate_evidence_strength(self, data_sources: Dict) -> Dict:
        """Calculate evidence strength score and breakdown"""
        breakdown = {
            'clinical_trials': data_sources.get('clinical_trial_count', 0),
            'guidelines': data_sources.get('guideline_count', 0),
            'case_studies': data_sources.get('case_study_count', 0),
            'expert_opinion': data_sources.get('expert_opinion_count', 0)
        }
        
        # Weight different evidence types
        weights = {'clinical_trials': 10, 'guidelines': 8, 'case_studies': 5, 'expert_opinion': 3}
        
        total_score = sum(breakdown.get(k, 0) * weights.get(k, 1) for k in breakdown)
        max_score = 100  # Normalize to 100
        
        normalized_score = min(100, (total_score / max_score) * 100) if total_score > 0 else 50
        
        return {
            'score': normalized_score,
            'breakdown': breakdown
        }
    
    def _generate_detailed_explanation(self, confidence_data: Dict) -> str:
        """Generate detailed explanation for doctors"""
        lines = []
        lines.append(f"Overall Confidence: {confidence_data['overall_confidence']:.1f}%")
        lines.append(f"Data Quality Score: {confidence_data['data_quality_score']:.1f}%")
        lines.append(f"Model Certainty: {confidence_data['model_certainty_score']:.1f}%")
        lines.append(f"Evidence Strength: {confidence_data['evidence_strength_score']:.1f}%")
        
        if confidence_data['missing_data_sources']:
            lines.append("\nMissing Data Sources:")
            for source in confidence_data['missing_data_sources']:
                lines.append(f"  • {source}")
        
        if confidence_data['conflicting_outputs']:
            lines.append("\nConflicting Outputs:")
            for conflict in confidence_data['conflicting_outputs']:
                lines.append(f"  • {conflict.get('conflict', 'Unknown')}")
        
        if confidence_data['evidence_breakdown']:
            lines.append("\nEvidence Breakdown:")
            for k, v in confidence_data['evidence_breakdown'].items():
                if v > 0:
                    lines.append(f"  • {k.replace('_', ' ').title()}: {v}")
        
        return "\n".join(lines)
    
    def _generate_patient_explanation(self, confidence_data: Dict) -> str:
        """Generate simple explanation for patients"""
        level = confidence_data['confidence_level']
        
        if level == 'high':
            return ("Our analysis is based on comprehensive data and well-established "
                    "medical evidence. Your healthcare team has reviewed this thoroughly.")
        elif level == 'moderate':
            return ("Our analysis provides useful guidance, though some additional "
                    "information may help refine the recommendations. Your doctor will "
                    "discuss this with you.")
        else:
            return ("This analysis is preliminary and your healthcare team will need "
                    "to gather more information to provide the best recommendations. "
                    "Please discuss this with your doctor.")


class XAIExplanationGenerator:
    """Generates explainable AI (XAI) explanations for treatment recommendations"""
    
    def __init__(self):
        self.groq_client = None
        api_key = os.getenv('GROQ_API_KEY')
        if api_key:
            self.groq_client = Groq(api_key=api_key)
    
    def generate_xai_explanation(
        self,
        treatment_plan: Dict[str, Any],
        tumor_data: Dict[str, Any],
        genomic_data: Dict[str, Any],
        biomarker_data: Dict[str, Any],
        patient_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate XAI explanation for a treatment recommendation
        
        Returns:
            Dict with ranked contributing factors and explanations
        """
        factors = []
        
        # Calculate tumor factor influence
        tumor_influence = self._calculate_tumor_influence(tumor_data)
        if tumor_influence:
            factors.extend(tumor_influence)
        
        # Calculate genomic factor influence
        genomic_influence = self._calculate_genomic_influence(genomic_data)
        if genomic_influence:
            factors.extend(genomic_influence)
        
        # Calculate biomarker factor influence
        biomarker_influence = self._calculate_biomarker_influence(biomarker_data)
        if biomarker_influence:
            factors.extend(biomarker_influence)
        
        # Calculate comorbidity factor influence
        comorbidity_influence = self._calculate_comorbidity_influence(patient_data)
        if comorbidity_influence:
            factors.extend(comorbidity_influence)
        
        # Normalize influences to sum to 100%
        total_influence = sum(f['influence'] for f in factors)
        if total_influence > 0:
            for factor in factors:
                factor['influence'] = round((factor['influence'] / total_influence) * 100, 1)
        
        # Sort by influence and add ranks
        factors.sort(key=lambda x: x['influence'], reverse=True)
        for i, factor in enumerate(factors, 1):
            factor['rank'] = i
        
        # Build structured explanation
        explanation = {
            'contributing_factors': factors,
            'tumor_factors': self._extract_tumor_factors(tumor_data),
            'genomic_factors': self._extract_genomic_factors(genomic_data),
            'biomarker_factors': self._extract_biomarker_factors(biomarker_data),
            'comorbidity_factors': self._extract_comorbidity_factors(patient_data),
            'recommendation_summary': self._generate_recommendation_summary(treatment_plan, factors),
            'explanation_text': self._generate_explanation_text(factors, treatment_plan),
            'structured_explanation': {
                'primary_driver': factors[0] if factors else None,
                'secondary_drivers': factors[1:3] if len(factors) > 1 else [],
                'treatment_rationale': treatment_plan.get('rationale', '')
            },
            'disclaimer': ("This is clinical decision support only. Final treatment decisions "
                          "should be made by qualified healthcare professionals in consultation "
                          "with the patient.")
        }
        
        return explanation
    
    def _calculate_tumor_influence(self, tumor_data: Dict) -> List[Dict]:
        """Calculate influence of tumor characteristics"""
        factors = []
        
        stage = tumor_data.get('stage', '')
        if stage:
            # Higher stages have more influence on treatment
            stage_weights = {'I': 15, 'II': 20, 'III': 28, 'IV': 35}
            weight = stage_weights.get(stage.upper()[:1], 20)
            factors.append({
                'factor': 'Tumor Stage',
                'value': f"Stage {stage}",
                'influence': weight,
                'category': 'tumor'
            })
        
        grade = tumor_data.get('grade', '')
        if grade:
            grade_weights = {'1': 8, '2': 12, '3': 18}
            weight = grade_weights.get(str(grade), 10)
            factors.append({
                'factor': 'Tumor Grade',
                'value': f"Grade {grade}",
                'influence': weight,
                'category': 'tumor'
            })
        
        size = tumor_data.get('size_mm')
        if size:
            # Larger tumors have more influence
            weight = min(15, size / 10 + 5)
            factors.append({
                'factor': 'Tumor Size',
                'value': f"{size}mm",
                'influence': weight,
                'category': 'tumor'
            })
        
        return factors
    
    def _calculate_genomic_influence(self, genomic_data: Dict) -> List[Dict]:
        """Calculate influence of genomic factors"""
        factors = []
        
        mutations = genomic_data.get('mutations', {})
        actionable_mutations = ['EGFR', 'ALK', 'ROS1', 'BRAF', 'KRAS', 'HER2', 'BRCA1', 'BRCA2']
        
        for mutation in actionable_mutations:
            if mutations.get(mutation, {}).get('status') == 'mutated':
                factors.append({
                    'factor': f'{mutation} Mutation',
                    'value': 'Positive',
                    'influence': 22,  # High influence for actionable mutations
                    'category': 'genomic'
                })
        
        # TMB
        tmb = genomic_data.get('tmb')
        if tmb:
            label = 'High' if tmb > 10 else 'Low' if tmb < 5 else 'Moderate'
            factors.append({
                'factor': 'Tumor Mutational Burden',
                'value': f"{label} ({tmb} mut/Mb)",
                'influence': 15 if tmb > 10 else 8,
                'category': 'genomic'
            })
        
        return factors
    
    def _calculate_biomarker_influence(self, biomarker_data: Dict) -> List[Dict]:
        """Calculate influence of biomarker levels"""
        factors = []
        
        pd_l1 = biomarker_data.get('PD-L1', {})
        if pd_l1:
            value = pd_l1.get('value', 0)
            factors.append({
                'factor': 'PD-L1 Expression',
                'value': f"{value}%",
                'influence': 18 if value >= 50 else 10 if value >= 1 else 5,
                'category': 'biomarker'
            })
        
        ki67 = biomarker_data.get('Ki-67', {})
        if ki67:
            value = ki67.get('value', 0)
            label = 'High' if value > 20 else 'Low'
            factors.append({
                'factor': 'Ki-67 Index',
                'value': f"{label} ({value}%)",
                'influence': 12 if value > 20 else 6,
                'category': 'biomarker'
            })
        
        # Hormone receptors for breast cancer
        er = biomarker_data.get('ER', {})
        if er:
            status = 'Positive' if er.get('positive') else 'Negative'
            factors.append({
                'factor': 'Estrogen Receptor',
                'value': status,
                'influence': 15 if er.get('positive') else 8,
                'category': 'biomarker'
            })
        
        return factors
    
    def _calculate_comorbidity_influence(self, patient_data: Dict) -> List[Dict]:
        """Calculate influence of comorbidities"""
        factors = []
        
        comorbidities = patient_data.get('comorbidities', [])
        high_impact = ['cardiac_disease', 'renal_failure', 'liver_disease', 'diabetes']
        
        for condition in comorbidities:
            condition_lower = condition.lower().replace(' ', '_')
            if any(hi in condition_lower for hi in high_impact):
                factors.append({
                    'factor': condition.replace('_', ' ').title(),
                    'value': 'Present',
                    'influence': 10,
                    'category': 'comorbidity'
                })
        
        # Age factor
        age = patient_data.get('age')
        if age:
            if age > 75:
                factors.append({
                    'factor': 'Advanced Age',
                    'value': f"{age} years",
                    'influence': 12,
                    'category': 'patient'
                })
            elif age < 40:
                factors.append({
                    'factor': 'Young Age',
                    'value': f"{age} years",
                    'influence': 8,
                    'category': 'patient'
                })
        
        # Performance status
        ps = patient_data.get('performance_status')
        if ps is not None:
            if ps >= 2:
                factors.append({
                    'factor': 'Performance Status',
                    'value': f"ECOG {ps}",
                    'influence': 15,
                    'category': 'patient'
                })
        
        return factors
    
    def _extract_tumor_factors(self, tumor_data: Dict) -> Dict:
        """Extract tumor factors with influence"""
        return {
            'stage': tumor_data.get('stage'),
            'grade': tumor_data.get('grade'),
            'size_mm': tumor_data.get('size_mm'),
            'location': tumor_data.get('location'),
            'influence': 35  # Base tumor influence
        }
    
    def _extract_genomic_factors(self, genomic_data: Dict) -> Dict:
        """Extract genomic factors with influence"""
        return genomic_data.get('mutations', {})
    
    def _extract_biomarker_factors(self, biomarker_data: Dict) -> Dict:
        """Extract biomarker factors"""
        return biomarker_data
    
    def _extract_comorbidity_factors(self, patient_data: Dict) -> Dict:
        """Extract comorbidity factors"""
        comorbidities = patient_data.get('comorbidities', [])
        result = {}
        for cond in comorbidities:
            result[cond] = {'present': True, 'influence': 8}
        return result
    
    def _generate_recommendation_summary(self, treatment_plan: Dict, factors: List[Dict]) -> str:
        """Generate a summary of the treatment recommendation"""
        primary_treatments = treatment_plan.get('primary_treatments', [])
        top_factors = [f['factor'] for f in factors[:3]]
        
        treatments_str = ', '.join(primary_treatments[:3]) if primary_treatments else 'the recommended treatments'
        factors_str = ', '.join(top_factors) if top_factors else 'clinical factors'
        
        return (f"Based on {factors_str}, {treatments_str} "
                f"are recommended for this patient's cancer type and stage.")
    
    def _generate_explanation_text(self, factors: List[Dict], treatment_plan: Dict) -> str:
        """Generate deterministic explanation text"""
        lines = ["Treatment Recommendation Explanation:", ""]
        
        lines.append("Key Factors Influencing This Recommendation:")
        for i, factor in enumerate(factors[:5], 1):
            lines.append(f"{i}. {factor['factor']}: {factor['value']} ({factor['influence']:.1f}% influence)")
        
        lines.append("")
        lines.append("These factors were analyzed using evidence-based guidelines and clinical data.")
        
        return "\n".join(lines)
