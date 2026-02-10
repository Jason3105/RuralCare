"""
Toxicity Prediction Service
Predicts drug toxicities using rule-based and ML approaches
"""

import os
from typing import Dict, List, Optional, Any
from groq import Groq


class ToxicityPredictor:
    """Predicts drug toxicities and adverse events with CTCAE grading"""
    
    # Common chemotherapy drugs and their known toxicity profiles
    DRUG_TOXICITY_PROFILES = {
        'cisplatin': {
            'nephrotoxicity': {'probability': 0.35, 'ctcae_grade': 3, 'onset_days': '3-7'},
            'ototoxicity': {'probability': 0.25, 'ctcae_grade': 2, 'onset_days': '7-14'},
            'nausea': {'probability': 0.80, 'ctcae_grade': 2, 'onset_days': '1-3'},
            'vomiting': {'probability': 0.70, 'ctcae_grade': 2, 'onset_days': '1-3'},
            'myelosuppression': {'probability': 0.45, 'ctcae_grade': 3, 'onset_days': '7-14'},
            'peripheral_neuropathy': {'probability': 0.30, 'ctcae_grade': 2, 'onset_days': '14-28'},
        },
        'carboplatin': {
            'thrombocytopenia': {'probability': 0.50, 'ctcae_grade': 3, 'onset_days': '14-21'},
            'neutropenia': {'probability': 0.40, 'ctcae_grade': 3, 'onset_days': '14-21'},
            'nausea': {'probability': 0.60, 'ctcae_grade': 2, 'onset_days': '1-3'},
            'fatigue': {'probability': 0.45, 'ctcae_grade': 2, 'onset_days': '1-7'},
        },
        'paclitaxel': {
            'neutropenia': {'probability': 0.60, 'ctcae_grade': 3, 'onset_days': '7-14'},
            'peripheral_neuropathy': {'probability': 0.55, 'ctcae_grade': 2, 'onset_days': '7-14'},
            'alopecia': {'probability': 0.95, 'ctcae_grade': 2, 'onset_days': '14-21'},
            'myalgia': {'probability': 0.50, 'ctcae_grade': 2, 'onset_days': '2-5'},
            'hypersensitivity': {'probability': 0.10, 'ctcae_grade': 3, 'onset_days': '0-1'},
        },
        'docetaxel': {
            'neutropenia': {'probability': 0.75, 'ctcae_grade': 4, 'onset_days': '7-14'},
            'alopecia': {'probability': 0.90, 'ctcae_grade': 2, 'onset_days': '14-21'},
            'fluid_retention': {'probability': 0.40, 'ctcae_grade': 2, 'onset_days': '21-28'},
            'fatigue': {'probability': 0.55, 'ctcae_grade': 2, 'onset_days': '1-7'},
            'nail_changes': {'probability': 0.35, 'ctcae_grade': 1, 'onset_days': '28-42'},
        },
        'doxorubicin': {
            'cardiotoxicity': {'probability': 0.20, 'ctcae_grade': 3, 'onset_days': '30-365'},
            'myelosuppression': {'probability': 0.65, 'ctcae_grade': 3, 'onset_days': '7-14'},
            'alopecia': {'probability': 0.95, 'ctcae_grade': 2, 'onset_days': '14-21'},
            'nausea': {'probability': 0.70, 'ctcae_grade': 2, 'onset_days': '1-3'},
            'mucositis': {'probability': 0.40, 'ctcae_grade': 2, 'onset_days': '5-14'},
        },
        'cyclophosphamide': {
            'myelosuppression': {'probability': 0.60, 'ctcae_grade': 3, 'onset_days': '7-14'},
            'hemorrhagic_cystitis': {'probability': 0.15, 'ctcae_grade': 3, 'onset_days': '1-7'},
            'nausea': {'probability': 0.65, 'ctcae_grade': 2, 'onset_days': '1-3'},
            'alopecia': {'probability': 0.50, 'ctcae_grade': 2, 'onset_days': '14-21'},
        },
        'gemcitabine': {
            'myelosuppression': {'probability': 0.55, 'ctcae_grade': 3, 'onset_days': '7-14'},
            'flu_like_symptoms': {'probability': 0.45, 'ctcae_grade': 1, 'onset_days': '1-3'},
            'hepatotoxicity': {'probability': 0.20, 'ctcae_grade': 2, 'onset_days': '7-14'},
            'rash': {'probability': 0.25, 'ctcae_grade': 1, 'onset_days': '7-14'},
        },
        'pembrolizumab': {
            'fatigue': {'probability': 0.35, 'ctcae_grade': 1, 'onset_days': '7-28'},
            'pneumonitis': {'probability': 0.05, 'ctcae_grade': 3, 'onset_days': '30-90'},
            'hypothyroidism': {'probability': 0.10, 'ctcae_grade': 2, 'onset_days': '30-180'},
            'colitis': {'probability': 0.05, 'ctcae_grade': 3, 'onset_days': '30-60'},
            'rash': {'probability': 0.15, 'ctcae_grade': 1, 'onset_days': '14-30'},
        },
        'nivolumab': {
            'fatigue': {'probability': 0.30, 'ctcae_grade': 1, 'onset_days': '7-28'},
            'pneumonitis': {'probability': 0.04, 'ctcae_grade': 3, 'onset_days': '30-90'},
            'hypothyroidism': {'probability': 0.08, 'ctcae_grade': 2, 'onset_days': '30-180'},
            'hepatitis': {'probability': 0.03, 'ctcae_grade': 3, 'onset_days': '30-90'},
            'rash': {'probability': 0.12, 'ctcae_grade': 1, 'onset_days': '14-30'},
        },
        'erlotinib': {
            'rash': {'probability': 0.75, 'ctcae_grade': 2, 'onset_days': '7-14'},
            'diarrhea': {'probability': 0.55, 'ctcae_grade': 2, 'onset_days': '7-14'},
            'hepatotoxicity': {'probability': 0.10, 'ctcae_grade': 2, 'onset_days': '14-30'},
            'interstitial_lung_disease': {'probability': 0.01, 'ctcae_grade': 4, 'onset_days': '30-90'},
        },
        'osimertinib': {
            'diarrhea': {'probability': 0.45, 'ctcae_grade': 1, 'onset_days': '7-14'},
            'rash': {'probability': 0.40, 'ctcae_grade': 1, 'onset_days': '14-28'},
            'paronychia': {'probability': 0.25, 'ctcae_grade': 1, 'onset_days': '28-56'},
            'qt_prolongation': {'probability': 0.05, 'ctcae_grade': 2, 'onset_days': '7-28'},
        },
        'tamoxifen': {
            'hot_flashes': {'probability': 0.65, 'ctcae_grade': 1, 'onset_days': '14-30'},
            'thromboembolic_events': {'probability': 0.02, 'ctcae_grade': 3, 'onset_days': '30-365'},
            'endometrial_cancer': {'probability': 0.01, 'ctcae_grade': 4, 'onset_days': '365+'},
            'vaginal_discharge': {'probability': 0.35, 'ctcae_grade': 1, 'onset_days': '30-90'},
        },
        'letrozole': {
            'arthralgia': {'probability': 0.45, 'ctcae_grade': 2, 'onset_days': '30-90'},
            'hot_flashes': {'probability': 0.50, 'ctcae_grade': 1, 'onset_days': '14-30'},
            'osteoporosis': {'probability': 0.15, 'ctcae_grade': 2, 'onset_days': '180-365'},
            'fatigue': {'probability': 0.25, 'ctcae_grade': 1, 'onset_days': '14-28'},
        },
    }
    
    # Lab value thresholds that affect toxicity risk
    LAB_THRESHOLDS = {
        'creatinine': {'normal_max': 1.2, 'unit': 'mg/dL', 'affects': ['nephrotoxicity', 'drug_clearance']},
        'egfr': {'normal_min': 90, 'unit': 'mL/min', 'affects': ['nephrotoxicity', 'drug_clearance']},
        'bilirubin': {'normal_max': 1.2, 'unit': 'mg/dL', 'affects': ['hepatotoxicity']},
        'alt': {'normal_max': 40, 'unit': 'U/L', 'affects': ['hepatotoxicity']},
        'ast': {'normal_max': 40, 'unit': 'U/L', 'affects': ['hepatotoxicity']},
        'neutrophils': {'normal_min': 2000, 'unit': 'cells/µL', 'affects': ['myelosuppression', 'neutropenia']},
        'platelets': {'normal_min': 150000, 'unit': 'cells/µL', 'affects': ['thrombocytopenia']},
        'hemoglobin': {'normal_min': 12, 'unit': 'g/dL', 'affects': ['anemia']},
        'lvef': {'normal_min': 50, 'unit': '%', 'affects': ['cardiotoxicity']},
    }
    
    def __init__(self):
        self.groq_client = None
        api_key = os.getenv('GROQ_API_KEY')
        if api_key:
            self.groq_client = Groq(api_key=api_key)
    
    def predict_toxicities(
        self,
        drug_name: str,
        patient_labs: Dict[str, float],
        patient_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Predict toxicities for a given drug based on patient data
        
        Returns:
            Dict with predicted toxicities, risk levels, and recommendations
        """
        drug_lower = drug_name.lower().replace(' ', '_').replace('-', '_')
        
        # Get base toxicity profile
        base_profile = self.DRUG_TOXICITY_PROFILES.get(drug_lower, {})
        
        if not base_profile:
            # Try partial match
            for drug_key in self.DRUG_TOXICITY_PROFILES:
                if drug_key in drug_lower or drug_lower in drug_key:
                    base_profile = self.DRUG_TOXICITY_PROFILES[drug_key]
                    break
        
        if not base_profile:
            # Generate generic profile
            base_profile = {
                'nausea': {'probability': 0.40, 'ctcae_grade': 2, 'onset_days': '1-7'},
                'fatigue': {'probability': 0.50, 'ctcae_grade': 2, 'onset_days': '1-14'},
                'myelosuppression': {'probability': 0.30, 'ctcae_grade': 2, 'onset_days': '7-21'},
            }
        
        # Adjust probabilities based on patient labs
        adjusted_profile = self._adjust_for_labs(base_profile, patient_labs)
        
        # Adjust for patient factors
        adjusted_profile = self._adjust_for_patient_factors(adjusted_profile, patient_data)
        
        # Format toxicities
        predicted_toxicities = []
        high_risk_toxicities = []
        
        for toxicity, data in adjusted_profile.items():
            tox_entry = {
                'toxicity': toxicity.replace('_', ' ').title(),
                'probability': round(data['probability'], 2),
                'ctcae_grade': data['ctcae_grade'],
                'onset_days': data['onset_days']
            }
            predicted_toxicities.append(tox_entry)
            
            # Flag high-risk toxicities (grade 3-4 or high probability)
            if data['ctcae_grade'] >= 3 or data['probability'] >= 0.5:
                high_risk_toxicities.append(tox_entry)
        
        # Sort by probability descending
        predicted_toxicities.sort(key=lambda x: x['probability'], reverse=True)
        high_risk_toxicities.sort(key=lambda x: (x['ctcae_grade'], x['probability']), reverse=True)
        
        # Determine overall risk level
        max_grade = max([t['ctcae_grade'] for t in predicted_toxicities], default=1)
        max_prob = max([t['probability'] for t in predicted_toxicities], default=0)
        
        if max_grade >= 4 or max_prob >= 0.7:
            overall_risk = 'high'
        elif max_grade >= 3 or max_prob >= 0.4:
            overall_risk = 'moderate'
        else:
            overall_risk = 'low'
        
        # Generate dose adjustments
        dose_adjustments = self._generate_dose_adjustments(drug_name, patient_labs, patient_data)
        
        # Correlate lab values
        correlated_labs = self._correlate_lab_values(patient_labs)
        
        # Calculate prediction confidence
        confidence = self._calculate_confidence(base_profile, patient_labs)
        
        # Generate patient summary
        patient_summary = self._generate_patient_summary(drug_name, predicted_toxicities, overall_risk)
        
        return {
            'drug_name': drug_name,
            'drug_class': self._get_drug_class(drug_name),
            'predicted_toxicities': predicted_toxicities,
            'high_risk_toxicities': high_risk_toxicities,
            'overall_risk_level': overall_risk,
            'dose_adjustments': dose_adjustments,
            'correlated_lab_values': correlated_labs,
            'prediction_confidence': confidence,
            'patient_summary': patient_summary
        }
    
    def _adjust_for_labs(self, profile: Dict, labs: Dict) -> Dict:
        """Adjust toxicity probabilities based on lab values"""
        adjusted = {}
        
        for toxicity, data in profile.items():
            adjusted_data = data.copy()
            prob = data['probability']
            
            # Nephrotoxicity adjustments
            if 'nephro' in toxicity.lower():
                creatinine = labs.get('creatinine', 1.0)
                if creatinine > 1.5:
                    prob = min(1.0, prob * 1.5)
                    adjusted_data['ctcae_grade'] = min(4, data['ctcae_grade'] + 1)
                elif creatinine > 1.2:
                    prob = min(1.0, prob * 1.2)
            
            # Hepatotoxicity adjustments
            if 'hepato' in toxicity.lower():
                alt = labs.get('alt', 30)
                ast = labs.get('ast', 30)
                if alt > 80 or ast > 80:
                    prob = min(1.0, prob * 1.5)
                elif alt > 40 or ast > 40:
                    prob = min(1.0, prob * 1.2)
            
            # Myelosuppression adjustments
            if 'myelo' in toxicity.lower() or 'neutro' in toxicity.lower():
                neutrophils = labs.get('neutrophils', 4000)
                if neutrophils < 2000:
                    prob = min(1.0, prob * 1.4)
                    adjusted_data['ctcae_grade'] = min(4, data['ctcae_grade'] + 1)
            
            # Thrombocytopenia adjustments
            if 'thrombo' in toxicity.lower():
                platelets = labs.get('platelets', 200000)
                if platelets < 100000:
                    prob = min(1.0, prob * 1.5)
            
            # Cardiotoxicity adjustments
            if 'cardio' in toxicity.lower():
                lvef = labs.get('lvef', 60)
                if lvef < 50:
                    prob = min(1.0, prob * 2.0)
                    adjusted_data['ctcae_grade'] = min(4, data['ctcae_grade'] + 1)
            
            adjusted_data['probability'] = prob
            adjusted[toxicity] = adjusted_data
        
        return adjusted
    
    def _adjust_for_patient_factors(self, profile: Dict, patient_data: Dict) -> Dict:
        """Adjust toxicity probabilities based on patient factors"""
        adjusted = {}
        
        age = patient_data.get('age', 50)
        ps = patient_data.get('performance_status', 0)
        comorbidities = patient_data.get('comorbidities', [])
        
        for toxicity, data in profile.items():
            adjusted_data = data.copy()
            prob = data['probability']
            
            # Age adjustments
            if age > 70:
                prob = min(1.0, prob * 1.2)
            elif age > 80:
                prob = min(1.0, prob * 1.4)
            
            # Performance status adjustments
            if ps >= 2:
                prob = min(1.0, prob * 1.3)
            
            # Comorbidity adjustments
            comorb_lower = [c.lower() for c in comorbidities]
            if 'renal' in toxicity.lower() and any('kidney' in c or 'renal' in c for c in comorb_lower):
                prob = min(1.0, prob * 1.4)
            if 'cardio' in toxicity.lower() and any('heart' in c or 'cardiac' in c for c in comorb_lower):
                prob = min(1.0, prob * 1.5)
            
            adjusted_data['probability'] = prob
            adjusted[toxicity] = adjusted_data
        
        return adjusted
    
    def _generate_dose_adjustments(
        self, 
        drug_name: str, 
        labs: Dict, 
        patient_data: Dict
    ) -> List[Dict]:
        """Generate dose adjustment recommendations"""
        adjustments = []
        
        # Renal impairment
        creatinine = labs.get('creatinine', 1.0)
        egfr = labs.get('egfr', 90)
        
        if creatinine > 1.5 or egfr < 60:
            adjustments.append({
                'reason': 'Renal impairment',
                'recommendation': 'Consider 25-50% dose reduction',
                'lab_value': f"Creatinine: {creatinine} mg/dL" if creatinine > 1.5 else f"eGFR: {egfr} mL/min",
                'priority': 'high'
            })
        
        # Hepatic impairment
        bilirubin = labs.get('bilirubin', 1.0)
        alt = labs.get('alt', 30)
        
        if bilirubin > 1.5 or alt > 80:
            adjustments.append({
                'reason': 'Hepatic impairment',
                'recommendation': 'Consider 25-50% dose reduction',
                'lab_value': f"Bilirubin: {bilirubin} mg/dL" if bilirubin > 1.5 else f"ALT: {alt} U/L",
                'priority': 'high'
            })
        
        # Age-based adjustment
        age = patient_data.get('age', 50)
        if age > 75:
            adjustments.append({
                'reason': 'Advanced age (>75 years)',
                'recommendation': 'Consider starting at reduced dose (75-80%)',
                'lab_value': f"Age: {age} years",
                'priority': 'moderate'
            })
        
        # Low baseline counts
        neutrophils = labs.get('neutrophils', 4000)
        if neutrophils < 2000:
            adjustments.append({
                'reason': 'Baseline neutropenia',
                'recommendation': 'Consider G-CSF support or dose reduction',
                'lab_value': f"ANC: {neutrophils} cells/µL",
                'priority': 'high'
            })
        
        return adjustments
    
    def _correlate_lab_values(self, labs: Dict) -> Dict:
        """Correlate lab values with toxicity risks"""
        correlations = {}
        
        for lab_name, value in labs.items():
            if lab_name in self.LAB_THRESHOLDS:
                threshold = self.LAB_THRESHOLDS[lab_name]
                
                # Determine status
                if 'normal_max' in threshold:
                    if value > threshold['normal_max'] * 2:
                        status = 'severely elevated'
                    elif value > threshold['normal_max']:
                        status = 'elevated'
                    else:
                        status = 'normal'
                elif 'normal_min' in threshold:
                    if value < threshold['normal_min'] * 0.5:
                        status = 'severely decreased'
                    elif value < threshold['normal_min']:
                        status = 'decreased'
                    else:
                        status = 'normal'
                else:
                    status = 'unknown'
                
                correlations[lab_name] = {
                    'value': value,
                    'unit': threshold['unit'],
                    'status': status,
                    'impact': f"Affects {', '.join(threshold['affects'])}" if status != 'normal' else 'Within normal limits'
                }
        
        return correlations
    
    def _calculate_confidence(self, base_profile: Dict, labs: Dict) -> float:
        """Calculate prediction confidence"""
        base_confidence = 70.0
        
        # More lab data increases confidence
        lab_count = len([v for v in labs.values() if v is not None])
        if lab_count >= 5:
            base_confidence += 15
        elif lab_count >= 3:
            base_confidence += 10
        elif lab_count >= 1:
            base_confidence += 5
        
        # Known drug profile increases confidence
        if base_profile:
            base_confidence += 10
        
        return min(95, base_confidence)
    
    def _get_drug_class(self, drug_name: str) -> str:
        """Get drug class"""
        drug_classes = {
            'cisplatin': 'Platinum Agent',
            'carboplatin': 'Platinum Agent',
            'paclitaxel': 'Taxane',
            'docetaxel': 'Taxane',
            'doxorubicin': 'Anthracycline',
            'cyclophosphamide': 'Alkylating Agent',
            'gemcitabine': 'Antimetabolite',
            'pembrolizumab': 'Checkpoint Inhibitor (PD-1)',
            'nivolumab': 'Checkpoint Inhibitor (PD-1)',
            'erlotinib': 'EGFR Inhibitor',
            'osimertinib': 'EGFR Inhibitor',
            'tamoxifen': 'Hormonal Agent (SERM)',
            'letrozole': 'Hormonal Agent (Aromatase Inhibitor)',
        }
        drug_lower = drug_name.lower().replace(' ', '_').replace('-', '_')
        return drug_classes.get(drug_lower, 'Chemotherapy/Targeted Agent')
    
    def _generate_patient_summary(
        self, 
        drug_name: str, 
        toxicities: List[Dict], 
        risk_level: str
    ) -> str:
        """Generate patient-friendly summary"""
        common_effects = [t['toxicity'] for t in toxicities if t['probability'] >= 0.3][:3]
        
        if risk_level == 'high':
            intro = f"Your treatment with {drug_name} may have some significant side effects."
        elif risk_level == 'moderate':
            intro = f"Your treatment with {drug_name} may cause some manageable side effects."
        else:
            intro = f"Your treatment with {drug_name} is expected to be well-tolerated."
        
        if common_effects:
            effects_str = ', '.join(common_effects)
            details = f" The most common ones are: {effects_str}."
        else:
            details = ""
        
        closing = " Your healthcare team will monitor you closely and help manage any symptoms."
        
        return intro + details + closing
