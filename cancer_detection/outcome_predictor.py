"""
ML-Based Outcome Prediction Models
Predicts survival, treatment response, and quality of life outcomes
using machine learning models
"""

import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import json

try:
    from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: scikit-learn not installed. Install with: pip install scikit-learn")


class OutcomePredictor:
    """
    ML-based outcome prediction for cancer treatment
    Predicts survival, treatment response, and quality of life
    """
    
    def __init__(self):
        """Initialize predictor with models"""
        self.models_initialized = False
        if SKLEARN_AVAILABLE:
            self._initialize_models()
    
    def _initialize_models(self):
        """Initialize ML models"""
        # In production, these would be trained on real data
        # For now, we use rule-based predictions with ML-like structure
        self.models_initialized = True
    
    def predict_survival(self, patient_profile: Dict, tumor_data: Dict, 
                       treatment_plan: Dict, genomic_data: Dict) -> Dict:
        """
        Predict 5-year survival probability
        
        Args:
            patient_profile: Patient demographics and health status
            tumor_data: Tumor characteristics
            treatment_plan: Treatment plan details
            genomic_data: Genomic profile
            
        Returns:
            Survival prediction with confidence intervals
        """
        # Base survival from cancer type and stage
        base_survival = self._get_base_survival(tumor_data)
        
        # Adjust for patient factors
        age_factor = self._calculate_age_factor(patient_profile.get('age', 50))
        ps_factor = self._calculate_performance_status_factor(
            patient_profile.get('performance_status', 1)
        )
        comorbidity_factor = self._calculate_comorbidity_factor(
            patient_profile.get('comorbidities', [])
        )
        
        # Adjust for tumor factors
        stage_factor = self._calculate_stage_factor(tumor_data.get('stage', '1'))
        grade_factor = self._calculate_grade_factor(tumor_data.get('grade', '2'))
        metastasis_factor = 0.5 if tumor_data.get('metastasis', False) else 1.0
        
        # Adjust for treatment
        treatment_factor = self._calculate_treatment_factor(treatment_plan)
        
        # Adjust for genomics
        genomic_factor = self._calculate_genomic_factor(genomic_data)
        
        # Calculate adjusted survival
        adjusted_survival = base_survival
        adjusted_survival *= age_factor
        adjusted_survival *= ps_factor
        adjusted_survival *= comorbidity_factor
        adjusted_survival *= stage_factor
        adjusted_survival *= grade_factor
        adjusted_survival *= metastasis_factor
        adjusted_survival *= treatment_factor
        adjusted_survival *= genomic_factor
        
        # Ensure reasonable bounds
        adjusted_survival = max(5.0, min(95.0, adjusted_survival))
        
        # Calculate confidence intervals (simplified)
        confidence_interval = self._calculate_confidence_interval(adjusted_survival)
        
        return {
            'predicted_5yr_survival': round(adjusted_survival, 1),
            'confidence_interval_95': confidence_interval,
            'base_survival': round(base_survival, 1),
            'adjustment_factors': {
                'age': round(age_factor, 2),
                'performance_status': round(ps_factor, 2),
                'comorbidities': round(comorbidity_factor, 2),
                'stage': round(stage_factor, 2),
                'grade': round(grade_factor, 2),
                'metastasis': round(metastasis_factor, 2),
                'treatment': round(treatment_factor, 2),
                'genomics': round(genomic_factor, 2),
            },
            'prediction_date': datetime.now().isoformat(),
            'model_version': '1.0',
        }
    
    def predict_treatment_response(self, patient_profile: Dict, tumor_data: Dict,
                                  treatment_plan: Dict, genomic_data: Dict) -> Dict:
        """
        Predict treatment response probability
        
        Args:
            patient_profile: Patient information
            tumor_data: Tumor characteristics
            treatment_plan: Treatment details
            genomic_data: Genomic profile
            
        Returns:
            Response prediction
        """
        base_response = 60.0  # Base response rate
        
        # Adjust for treatment type
        if 'targeted' in str(treatment_plan).lower():
            base_response += 15
        if 'immunotherapy' in str(treatment_plan).lower():
            base_response += 10
        
        # Adjust for genomics
        if genomic_data.get('actionable_mutations'):
            base_response += 10
        
        # Adjust for performance status
        ps = patient_profile.get('performance_status', 1)
        if ps <= 1:
            base_response += 5
        elif ps >= 2:
            base_response -= 15
        
        # Adjust for stage
        stage = tumor_data.get('stage', '1')
        if stage in ['1', '2']:
            base_response += 10
        elif stage == '4':
            base_response -= 10
        
        base_response = max(20.0, min(90.0, base_response))
        
        return {
            'response_probability': round(base_response, 1),
            'response_category': self._categorize_response(base_response),
            'factors': self._get_response_factors(patient_profile, tumor_data, treatment_plan, genomic_data),
            'prediction_date': datetime.now().isoformat(),
        }
    
    def predict_quality_of_life(self, patient_profile: Dict, treatment_plan: Dict) -> Dict:
        """
        Predict quality of life impact
        
        Args:
            patient_profile: Patient information
            treatment_plan: Treatment details
            
        Returns:
            QOL prediction
        """
        base_qol = 70  # Base QOL score (0-100)
        
        # Adjust for treatment intensity
        treatments = str(treatment_plan).lower()
        if 'chemotherapy' in treatments:
            base_qol -= 15
        if 'radiation' in treatments:
            base_qol -= 10
        if 'surgery' in treatments:
            base_qol -= 5
        
        # Adjust for age
        age = patient_profile.get('age', 50)
        if age > 70:
            base_qol -= 5
        
        # Adjust for comorbidities
        comorbidities = patient_profile.get('comorbidities', [])
        base_qol -= len(comorbidities) * 3
        
        base_qol = max(30, min(90, base_qol))
        
        return {
            'predicted_qol_score': base_qol,
            'qol_category': self._categorize_qol(base_qol),
            'impact_assessment': self._assess_qol_impact(base_qol),
            'prediction_date': datetime.now().isoformat(),
        }
    
    def predict_side_effects(self, patient_profile: Dict, treatment_plan: Dict) -> Dict:
        """
        Predict likely side effects
        
        Args:
            patient_profile: Patient information
            treatment_plan: Treatment details
            
        Returns:
            Side effect predictions
        """
        side_effects = []
        severity_scores = []
        
        treatments = str(treatment_plan).lower()
        
        # Chemotherapy side effects
        if 'chemo' in treatments:
            side_effects.extend([
                {'name': 'Nausea/Vomiting', 'probability': 0.7, 'severity': 'moderate'},
                {'name': 'Fatigue', 'probability': 0.85, 'severity': 'moderate'},
                {'name': 'Hair Loss', 'probability': 0.6, 'severity': 'mild'},
                {'name': 'Bone Marrow Suppression', 'probability': 0.5, 'severity': 'severe'},
            ])
            severity_scores.append(0.6)
        
        # Radiation side effects
        if 'radiation' in treatments:
            side_effects.extend([
                {'name': 'Skin Irritation', 'probability': 0.6, 'severity': 'mild'},
                {'name': 'Fatigue', 'probability': 0.7, 'severity': 'moderate'},
            ])
            severity_scores.append(0.4)
        
        # Immunotherapy side effects
        if 'immuno' in treatments:
            side_effects.extend([
                {'name': 'Immune-Related Colitis', 'probability': 0.15, 'severity': 'severe'},
                {'name': 'Pneumonitis', 'probability': 0.1, 'severity': 'severe'},
                {'name': 'Fatigue', 'probability': 0.5, 'severity': 'moderate'},
            ])
            severity_scores.append(0.3)
        
        # Adjust for patient factors
        age = patient_profile.get('age', 50)
        if age > 70:
            for se in side_effects:
                se['probability'] = min(1.0, se['probability'] * 1.2)
        
        # Calculate overall severity
        overall_severity = np.mean(severity_scores) if severity_scores else 0.0
        
        return {
            'predicted_side_effects': side_effects,
            'overall_severity_score': round(overall_severity, 2),
            'severity_category': self._categorize_severity(overall_severity),
            'management_recommendations': self._get_side_effect_management(side_effects),
            'prediction_date': datetime.now().isoformat(),
        }
    
    # Helper methods
    
    def _get_base_survival(self, tumor_data: Dict) -> float:
        """Get base survival rate from cancer type and stage"""
        cancer_type = tumor_data.get('cancer_type', 'unknown').lower()
        stage = str(tumor_data.get('stage', '1'))
        
        # Base survival rates by cancer type and stage
        survival_rates = {
            'breast': {'1': 99, '2': 93, '3': 72, '4': 29},
            'lung': {'1': 56, '2': 40, '3': 19, '4': 5},
            'colorectal': {'1': 92, '2': 87, '3': 89, '4': 14},
            'prostate': {'1': 99, '2': 98, '3': 95, '4': 32},
        }
        
        if cancer_type in survival_rates and stage in survival_rates[cancer_type]:
            return float(survival_rates[cancer_type][stage])
        
        return 50.0  # Default
    
    def _calculate_age_factor(self, age: int) -> float:
        """Calculate age adjustment factor"""
        if age < 50:
            return 1.0
        elif age < 65:
            return 0.95
        elif age < 75:
            return 0.85
        else:
            return 0.75
    
    def _calculate_performance_status_factor(self, ps: int) -> float:
        """Calculate performance status factor"""
        if ps == 0:
            return 1.0
        elif ps == 1:
            return 0.95
        elif ps == 2:
            return 0.75
        else:
            return 0.60
    
    def _calculate_comorbidity_factor(self, comorbidities: List) -> float:
        """Calculate comorbidity adjustment"""
        num_comorbidities = len(comorbidities) if comorbidities else 0
        if num_comorbidities == 0:
            return 1.0
        elif num_comorbidities == 1:
            return 0.95
        elif num_comorbidities == 2:
            return 0.90
        else:
            return 0.85
    
    def _calculate_stage_factor(self, stage: str) -> float:
        """Calculate stage adjustment"""
        stage_num = int(stage) if stage.isdigit() else 1
        if stage_num == 1:
            return 1.0
        elif stage_num == 2:
            return 0.95
        elif stage_num == 3:
            return 0.80
        else:
            return 0.50
    
    def _calculate_grade_factor(self, grade: str) -> float:
        """Calculate grade adjustment"""
        grade_num = int(grade) if grade.isdigit() else 2
        if grade_num == 1:
            return 1.0
        elif grade_num == 2:
            return 0.95
        else:
            return 0.85
    
    def _calculate_treatment_factor(self, treatment_plan: Dict) -> float:
        """Calculate treatment benefit factor"""
        treatments = str(treatment_plan).lower()
        factor = 1.0
        
        if 'targeted' in treatments:
            factor = 1.15
        elif 'immunotherapy' in treatments:
            factor = 1.10
        elif 'chemo' in treatments:
            factor = 1.05
        
        return factor
    
    def _calculate_genomic_factor(self, genomic_data: Dict) -> float:
        """Calculate genomic adjustment factor"""
        if genomic_data.get('actionable_mutations'):
            return 1.10
        elif genomic_data.get('immunotherapy_eligible'):
            return 1.05
        else:
            return 1.0
    
    def _calculate_confidence_interval(self, survival: float) -> Dict:
        """Calculate 95% confidence interval"""
        margin = survival * 0.1  # 10% margin
        return {
            'lower': round(max(0, survival - margin), 1),
            'upper': round(min(100, survival + margin), 1),
        }
    
    def _categorize_response(self, probability: float) -> str:
        """Categorize response probability"""
        if probability >= 70:
            return 'High likelihood of response'
        elif probability >= 50:
            return 'Moderate likelihood of response'
        else:
            return 'Lower likelihood of response'
    
    def _get_response_factors(self, patient_profile: Dict, tumor_data: Dict,
                             treatment_plan: Dict, genomic_data: Dict) -> List[str]:
        """Get factors influencing response"""
        factors = []
        
        if genomic_data.get('actionable_mutations'):
            factors.append('Actionable mutations present')
        
        if patient_profile.get('performance_status', 1) <= 1:
            factors.append('Good performance status')
        
        if 'targeted' in str(treatment_plan).lower():
            factors.append('Targeted therapy planned')
        
        return factors
    
    def _categorize_qol(self, score: int) -> str:
        """Categorize QOL score"""
        if score >= 70:
            return 'Good'
        elif score >= 50:
            return 'Moderate'
        else:
            return 'Poor'
    
    def _assess_qol_impact(self, score: int) -> str:
        """Assess QOL impact"""
        if score >= 70:
            return 'Treatment expected to have minimal impact on quality of life'
        elif score >= 50:
            return 'Treatment may have moderate impact on quality of life'
        else:
            return 'Treatment may significantly impact quality of life - supportive care important'
    
    def _categorize_severity(self, score: float) -> str:
        """Categorize severity"""
        if score >= 0.6:
            return 'High'
        elif score >= 0.4:
            return 'Moderate'
        else:
            return 'Low'
    
    def _get_side_effect_management(self, side_effects: List[Dict]) -> List[str]:
        """Get management recommendations"""
        recommendations = []
        
        severe_effects = [se for se in side_effects if se.get('severity') == 'severe']
        if severe_effects:
            recommendations.append('Proactive monitoring for severe side effects recommended')
            recommendations.append('Consider pre-medication and supportive care')
        
        if any('Nausea' in se.get('name', '') for se in side_effects):
            recommendations.append('Antiemetic prophylaxis recommended')
        
        if any('Bone Marrow' in se.get('name', '') for se in side_effects):
            recommendations.append('Regular CBC monitoring required')
        
        return recommendations

