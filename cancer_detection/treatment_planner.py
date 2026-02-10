"""
AI-Driven Personalized Cancer Treatment Planning Engine
Analyzes patient data, medical history, tumor characteristics, and genetic profiles
to recommend optimized treatment protocols using evidence-based guidelines.
"""

import json
from typing import Dict, List, Tuple
from datetime import datetime
import statistics

# Import new analyzers
try:
    from .histopathology_analyzer import HistopathologyAnalyzer
    from .genomics_analyzer import GenomicsAnalyzer
    from .outcome_predictor import OutcomePredictor
    ANALYZERS_AVAILABLE = True
except ImportError:
    ANALYZERS_AVAILABLE = False


class TreatmentPlanningEngine:
    """
    Main engine for AI-driven personalized cancer treatment planning.
    Integrates patient history, histopathology, genomics, and outcomes data.
    """
    
    # Evidence-based treatment protocols by cancer type and stage
    CANCER_TREATMENT_PROTOCOLS = {
        'breast': {
            'stage_1': {
                'primary': ['Surgery (Lumpectomy/Mastectomy)', 'Radiation Therapy'],
                'adjuvant': ['Hormonal Therapy (if HR+)', 'Chemotherapy (select cases)'],
                'targeted': ['HER2-targeted therapy (if HER2+)'],
                'survival_rate_5yr': 99,
            },
            'stage_2': {
                'primary': ['Surgery', 'Radiation Therapy'],
                'adjuvant': ['Chemotherapy', 'Hormonal Therapy (if HR+)'],
                'targeted': ['HER2-targeted therapy (if HER2+)'],
                'survival_rate_5yr': 93,
            },
            'stage_3': {
                'primary': ['Neoadjuvant Chemotherapy', 'Surgery', 'Radiation Therapy'],
                'adjuvant': ['Chemotherapy', 'Hormonal Therapy (if HR+)'],
                'targeted': ['HER2-targeted therapy (if HER2+)'],
                'survival_rate_5yr': 72,
            },
            'stage_4': {
                'primary': ['Systemic Therapy (Chemotherapy/Targeted/Immunotherapy)'],
                'palliative': ['Radiation for bone metastases', 'Supportive care'],
                'survival_rate_5yr': 29,
            }
        },
        'lung': {
            'stage_1': {
                'primary': ['Surgery (Lobectomy/Segmentectomy)', 'Stereotactic Body Radiation'],
                'adjuvant': ['Chemotherapy (select cases)'],
                'targeted': ['EGFR inhibitors (if mutation+)', 'ALK inhibitors (if fusion+)'],
                'survival_rate_5yr': 56,
            },
            'stage_2': {
                'primary': ['Surgery', 'Chemotherapy'],
                'adjuvant': ['Chemotherapy'],
                'targeted': ['EGFR inhibitors', 'ALK inhibitors'],
                'survival_rate_5yr': 40,
            },
            'stage_3': {
                'primary': ['Concurrent Chemoradiation', 'Surgery (select cases)'],
                'adjuvant': ['Durvalumab (PD-L1 inhibitor)'],
                'targeted': ['EGFR inhibitors', 'ALK inhibitors'],
                'survival_rate_5yr': 19,
            },
            'stage_4': {
                'primary': ['Targeted Therapy', 'Immunotherapy', 'Chemotherapy'],
                'palliative': ['Radiation for brain/bone metastases', 'Supportive care'],
                'survival_rate_5yr': 5,
            }
        },
        'colorectal': {
            'stage_1': {
                'primary': ['Surgery'],
                'adjuvant': [],
                'targeted': [],
                'survival_rate_5yr': 92,
            },
            'stage_2': {
                'primary': ['Surgery'],
                'adjuvant': ['Chemotherapy (select cases)'],
                'targeted': [],
                'survival_rate_5yr': 87,
            },
            'stage_3': {
                'primary': ['Surgery'],
                'adjuvant': ['Chemotherapy'],
                'targeted': [],
                'survival_rate_5yr': 89,
            },
            'stage_4': {
                'primary': ['Surgery (if resectable)', 'Systemic Therapy'],
                'palliative': ['Targeted therapy', 'Immunotherapy', 'Supportive care'],
                'survival_rate_5yr': 14,
            }
        },
        'prostate': {
            'low_risk': {
                'primary': ['Active Surveillance', 'Surgery (Prostatectomy)', 'Radiation Therapy'],
                'adjuvant': [],
                'targeted': [],
                'survival_rate_5yr': 99,
            },
            'intermediate_risk': {
                'primary': ['Radiation Therapy + ADT', 'Surgery'],
                'adjuvant': ['Androgen Deprivation Therapy (12-24 months)'],
                'targeted': [],
                'survival_rate_5yr': 98,
            },
            'high_risk': {
                'primary': ['Radiation Therapy + ADT', 'Surgery'],
                'adjuvant': ['Androgen Deprivation Therapy (24-36 months)'],
                'targeted': [],
                'survival_rate_5yr': 95,
            },
            'metastatic': {
                'primary': ['Systemic Therapy', 'Radiation for metastases'],
                'palliative': ['ADT', 'Chemotherapy', 'Novel hormonal agents'],
                'survival_rate_5yr': 32,
            }
        }
    }
    
    # Side effects by treatment modality
    TREATMENT_SIDE_EFFECTS = {
        'chemotherapy': [
            {'name': 'Nausea/Vomiting', 'severity': 'moderate', 'frequency': 'common'},
            {'name': 'Hair Loss', 'severity': 'moderate', 'frequency': 'common'},
            {'name': 'Bone Marrow Suppression', 'severity': 'severe', 'frequency': 'common'},
            {'name': 'Peripheral Neuropathy', 'severity': 'moderate', 'frequency': 'common'},
            {'name': 'Fatigue', 'severity': 'moderate', 'frequency': 'very common'},
            {'name': 'Infections', 'severity': 'severe', 'frequency': 'occasional'},
            {'name': 'Cardiotoxicity', 'severity': 'severe', 'frequency': 'rare'},
        ],
        'radiation': [
            {'name': 'Skin Irritation', 'severity': 'mild', 'frequency': 'common'},
            {'name': 'Fatigue', 'severity': 'moderate', 'frequency': 'common'},
            {'name': 'Fibrosis', 'severity': 'severe', 'frequency': 'occasional'},
            {'name': 'Secondary Malignancy', 'severity': 'severe', 'frequency': 'rare'},
        ],
        'surgery': [
            {'name': 'Pain at Incision', 'severity': 'moderate', 'frequency': 'common'},
            {'name': 'Infection', 'severity': 'moderate', 'frequency': 'occasional'},
            {'name': 'Numbness/Sensory Changes', 'severity': 'mild', 'frequency': 'occasional'},
            {'name': 'Seroma/Hematoma', 'severity': 'mild', 'frequency': 'occasional'},
        ],
        'immunotherapy': [
            {'name': 'Fatigue', 'severity': 'moderate', 'frequency': 'common'},
            {'name': 'Immune-Related Colitis', 'severity': 'severe', 'frequency': 'occasional'},
            {'name': 'Pneumonitis', 'severity': 'severe', 'frequency': 'rare'},
            {'name': 'Thyroid Dysfunction', 'severity': 'mild', 'frequency': 'occasional'},
            {'name': 'Rash', 'severity': 'mild', 'frequency': 'common'},
        ]
    }
    
    def __init__(self):
        """Initialize the treatment planning engine"""
        self.recommendations = []
        self.contraindications = []
        self.risk_factors = []
        
        # Initialize analyzers
        if ANALYZERS_AVAILABLE:
            self.histopathology_analyzer = HistopathologyAnalyzer()
            self.genomics_analyzer = GenomicsAnalyzer()
            self.outcome_predictor = OutcomePredictor()
        else:
            self.histopathology_analyzer = None
            self.genomics_analyzer = None
            self.outcome_predictor = None
    
    def analyze_patient_profile(self, patient_data: Dict) -> Dict:
        """
        Comprehensive patient analysis incorporating demographics, medical history,
        comorbidities, and performance status.
        
        Args:
            patient_data: Dictionary containing patient information
            
        Returns:
            Dictionary with analyzed patient profile
        """
        profile = {
            'age_group': self._categorize_age(patient_data.get('age', 0)),
            'performance_status': patient_data.get('performance_status', 'Unknown'),
            'comorbidities': patient_data.get('comorbidities', []),
            'organ_function': self._assess_organ_function(patient_data),
            'fitness_for_treatment': self._assess_treatment_fitness(patient_data),
            'risk_profile': self._calculate_risk_profile(patient_data),
        }
        return profile
    
    def analyze_tumor_characteristics(self, tumor_data: Dict) -> Dict:
        """
        Analyze tumor type, size, grade, stage, and location.
        
        Args:
            tumor_data: Dictionary with tumor characteristics
            
        Returns:
            Dictionary with tumor analysis
        """
        analysis = {
            'cancer_type': tumor_data.get('cancer_type', 'Unknown'),
            'stage': tumor_data.get('stage', 'Unknown'),
            'grade': tumor_data.get('grade', 'Unknown'),
            'size_mm': tumor_data.get('size_mm', None),
            'location': tumor_data.get('location', 'Unknown'),
            'lymph_node_involvement': tumor_data.get('lymph_node_involvement', False),
            'metastasis': tumor_data.get('metastasis', False),
            'metastasis_sites': tumor_data.get('metastasis_sites', []),
            'urgency_level': self._assess_urgency(tumor_data),
        }
        return analysis
    
    def analyze_genetic_profile(self, genetic_data: Dict) -> Dict:
        """
        Analyze genetic mutations, biomarkers, and immunoprofile.
        Uses enhanced genomics analyzer if available.
        
        Args:
            genetic_data: Dictionary with genetic test results
            
        Returns:
            Dictionary with genetic analysis and implications
        """
        # Use enhanced genomics analyzer if available
        if self.genomics_analyzer:
            return self.genomics_analyzer.analyze_genomic_profile(genetic_data)
        
        # Fallback to original analysis
        analysis = {
            'mutations': genetic_data.get('mutations', {}),
            'biomarkers': genetic_data.get('biomarkers', {}),
            'immunoprofile': self._analyze_immunoprofile(genetic_data),
            'targeted_therapy_eligible': self._check_targeted_therapy_eligibility(genetic_data),
            'immunotherapy_eligible': self._check_immunotherapy_eligibility(genetic_data),
            'prognosis_indicators': self._assess_prognosis_from_genetics(genetic_data),
        }
        return analysis
    
    def generate_treatment_plan(self, patient_profile: Dict, tumor_analysis: Dict, 
                               genetic_profile: Dict) -> Dict:
        """
        Generate personalized treatment plan based on comprehensive analysis.
        
        Args:
            patient_profile: Analyzed patient profile
            tumor_analysis: Analyzed tumor characteristics
            genetic_profile: Analyzed genetic profile
            
        Returns:
            Dictionary with personalized treatment recommendations
        """
        cancer_type = tumor_analysis.get('cancer_type', '').lower()
        stage = tumor_analysis.get('stage', 'Unknown')
        
        # Get base protocol
        base_protocol = self._get_base_protocol(cancer_type, stage)
        
        # Customize based on patient factors
        customized_plan = self._customize_protocol(
            base_protocol,
            patient_profile,
            tumor_analysis,
            genetic_profile
        )
        
        # Generate side effect profile
        side_effects = self._generate_side_effect_profile(customized_plan)
        
        # Calculate outcome predictions using ML predictor if available
        if self.outcome_predictor:
            outcomes = self.outcome_predictor.predict_survival(
                patient_profile,
                tumor_analysis,
                customized_plan,
                genetic_profile
            )
            treatment_response = self.outcome_predictor.predict_treatment_response(
                patient_profile,
                tumor_analysis,
                customized_plan,
                genetic_profile
            )
            qol_prediction = self.outcome_predictor.predict_quality_of_life(
                patient_profile,
                customized_plan
            )
            side_effect_prediction = self.outcome_predictor.predict_side_effects(
                patient_profile,
                customized_plan
            )
            
            outcomes = {
                'survival': outcomes,
                'treatment_response': treatment_response,
                'quality_of_life': qol_prediction,
                'side_effects': side_effect_prediction,
            }
        else:
            # Fallback to original prediction
            outcomes = self._predict_outcomes(
                patient_profile,
                tumor_analysis,
                genetic_profile,
                customized_plan
            )
        
        treatment_plan = {
            'plan_date': datetime.now().isoformat(),
            'cancer_type': cancer_type,
            'stage': stage,
            'recommended_protocols': customized_plan.get('protocols', []),
            'primary_treatment': customized_plan.get('primary', []),
            'adjuvant_treatment': customized_plan.get('adjuvant', []),
            'targeted_therapy': customized_plan.get('targeted', []),
            'side_effects': side_effects,
            'outcome_predictions': outcomes,
            'monitoring_recommendations': self._generate_monitoring_plan(cancer_type, stage),
            'contraindications': self.contraindications,
            'clinical_trials': self._find_relevant_trials(cancer_type, stage, genetic_profile),
        }
        
        return treatment_plan
    
    def predict_outcomes(self, plan: Dict, patient_profile: Dict) -> Dict:
        """
        Predict likely outcomes and survival metrics.
        
        Args:
            plan: Treatment plan
            patient_profile: Patient profile
            
        Returns:
            Dictionary with outcome predictions
        """
        base_survival = plan.get('base_survival_rate', 50)
        
        # Adjust based on patient factors
        adjustments = []
        
        # Age adjustment
        age_group = patient_profile.get('age_group', 'adult')
        if age_group == 'elderly':
            base_survival *= 0.85
            adjustments.append('Age > 70 reduces survival by ~15%')
        
        # Performance status adjustment
        ps = patient_profile.get('performance_status', 1)
        if ps >= 2:
            base_survival *= 0.70
            adjustments.append('Poor performance status significantly reduces survival')
        
        # Comorbidities adjustment
        comorbidities = patient_profile.get('comorbidities', [])
        if len(comorbidities) > 2:
            base_survival *= 0.85
            adjustments.append(f'Multiple comorbidities reduce survival by ~15%')
        
        return {
            'predicted_5yr_survival': round(base_survival, 1),
            'adjusted_survival_rate': round(base_survival, 1),
            'adjustment_factors': adjustments,
            'response_probability': self._estimate_response_probability(plan),
            'quality_of_life_impact': self._estimate_qol_impact(plan),
        }
    
    def generate_patient_pathway(self, treatment_plan: Dict) -> Dict:
        """
        Generate visual patient-specific treatment pathway for shared decision-making.
        
        Args:
            treatment_plan: Personalized treatment plan
            
        Returns:
            Dictionary with treatment pathway timeline
        """
        pathway = {
            'phases': [
                {
                    'phase': 'Diagnosis & Staging',
                    'duration': '1-2 weeks',
                    'key_activities': [
                        'Confirm pathology',
                        'Complete staging workup',
                        'Genetic testing',
                        'Multidisciplinary tumor board review'
                    ],
                    'timeline': 'Week 1-2'
                },
                {
                    'phase': 'Treatment Planning',
                    'duration': '1-2 weeks',
                    'key_activities': [
                        'Discuss treatment options',
                        'Obtain informed consent',
                        'Treatment simulation (if radiation)',
                        'Finalize treatment plan'
                    ],
                    'timeline': 'Week 3-4'
                },
                {
                    'phase': 'Primary Treatment',
                    'duration': treatment_plan.get('primary_duration', '4-8 weeks'),
                    'key_activities': treatment_plan.get('primary_treatment', []),
                    'timeline': 'Week 5+',
                    'monitoring': ['Weekly clinic visits', 'Regular blood work', 'Imaging as needed']
                },
                {
                    'phase': 'Adjuvant Treatment',
                    'duration': treatment_plan.get('adjuvant_duration', 'Variable'),
                    'key_activities': treatment_plan.get('adjuvant_treatment', []),
                    'monitoring': ['Monthly clinic visits', 'Regular labs', 'Imaging as planned']
                },
                {
                    'phase': 'Surveillance & Follow-up',
                    'duration': '5+ years',
                    'key_activities': [
                        'Regular oncology follow-up',
                        'Imaging surveillance',
                        'Survivorship program enrollment',
                        'Late effect monitoring'
                    ],
                    'monitoring': ['Every 3-6 months initially', 'Then annually']
                }
            ],
            'decision_points': self._identify_decision_points(treatment_plan),
            'expected_milestones': self._define_milestones(treatment_plan),
        }
        
        return pathway
    
    # Helper methods
    
    def _categorize_age(self, age: int) -> str:
        """Categorize patient age"""
        if age < 18:
            return 'pediatric'
        elif age < 65:
            return 'adult'
        elif age < 75:
            return 'elderly'
        else:
            return 'very_elderly'
    
    def _assess_organ_function(self, patient_data: Dict) -> Dict:
        """Assess organ function from lab values"""
        lab_values = patient_data.get('lab_values', {})
        return {
            'cardiac': self._assess_cardiac_function(lab_values),
            'renal': self._assess_renal_function(lab_values),
            'hepatic': self._assess_hepatic_function(lab_values),
            'bone_marrow': self._assess_bone_marrow_function(lab_values),
        }
    
    def _assess_treatment_fitness(self, patient_data: Dict) -> str:
        """Assess patient fitness for treatment"""
        ps = patient_data.get('performance_status', 2)
        comorbidities = len(patient_data.get('comorbidities', []))
        
        if ps <= 1 and comorbidities <= 2:
            return 'Excellent'
        elif ps <= 1 and comorbidities <= 4:
            return 'Good'
        elif ps <= 2:
            return 'Fair'
        else:
            return 'Poor'
    
    def _calculate_risk_profile(self, patient_data: Dict) -> str:
        """Calculate patient risk profile"""
        age = patient_data.get('age', 50)
        ps = patient_data.get('performance_status', 1)
        comorbidities = len(patient_data.get('comorbidities', []))
        
        risk_score = 0
        if age > 70:
            risk_score += 2
        if ps >= 2:
            risk_score += 3
        if comorbidities > 2:
            risk_score += 2
        
        if risk_score >= 5:
            return 'High'
        elif risk_score >= 2:
            return 'Moderate'
        else:
            return 'Low'
    
    def _assess_urgency(self, tumor_data: Dict) -> str:
        """Assess treatment urgency"""
        stage = tumor_data.get('stage', 'Unknown')
        metastasis = tumor_data.get('metastasis', False)
        
        if metastasis or stage in ['3', '4', 'stage_3', 'stage_4']:
            return 'Urgent (Start within 2 weeks)'
        else:
            return 'Standard (Start within 4 weeks)'
    
    def _analyze_immunoprofile(self, genetic_data: Dict) -> Dict:
        """Analyze tumor immune profile"""
        return {
            'pd_l1_status': genetic_data.get('pd_l1_status', 'Unknown'),
            'msi_status': genetic_data.get('msi_status', 'Unknown'),
            'tmb': genetic_data.get('tumor_mutational_burden', 'Unknown'),
            'immune_infiltration': genetic_data.get('immune_infiltration', 'Unknown'),
        }
    
    def _check_targeted_therapy_eligibility(self, genetic_data: Dict) -> List[str]:
        """Check for targeted therapy mutations"""
        mutations = genetic_data.get('mutations', {})
        eligible_therapies = []
        
        if mutations.get('EGFR'):
            eligible_therapies.append('EGFR Inhibitors (Gefitinib, Erlotinib, Afatinib)')
        if mutations.get('ALK'):
            eligible_therapies.append('ALK Inhibitors (Crizotinib, Alectinib, Brigatinib)')
        if mutations.get('HER2'):
            eligible_therapies.append('HER2-Targeted Therapy (Trastuzumab, Pertuzumab)')
        if mutations.get('BRAF'):
            eligible_therapies.append('BRAF Inhibitors (Vemurafenib, Dabrafenib)')
        if mutations.get('KRAS'):
            eligible_therapies.append('KRAS Inhibitors (Sotorasib, Adagrasib) - if G12C mutation')
        if mutations.get('PD-L1'):
            eligible_therapies.append('PD-L1/PD-1 Inhibitors')
        
        return eligible_therapies
    
    def _check_immunotherapy_eligibility(self, genetic_data: Dict) -> bool:
        """Check immunotherapy eligibility"""
        pd_l1 = genetic_data.get('pd_l1_status', '').lower()
        msi = genetic_data.get('msi_status', '').lower()
        tmb = genetic_data.get('tumor_mutational_burden', '').lower()
        
        # PD-L1 positive typically eligible
        if 'positive' in pd_l1 or 'high' in pd_l1:
            return True
        
        # MSI-H typically eligible
        if 'msi-h' in msi or 'high' in msi:
            return True
        
        # High TMB typically eligible
        if 'high' in tmb:
            return True
        
        return False
    
    def _assess_prognosis_from_genetics(self, genetic_data: Dict) -> Dict:
        """Assess prognosis from genetic markers"""
        return {
            'favorable_markers': self._identify_favorable_markers(genetic_data),
            'unfavorable_markers': self._identify_unfavorable_markers(genetic_data),
            'prognosis_category': self._categorize_prognosis(genetic_data),
        }
    
    def _identify_favorable_markers(self, genetic_data: Dict) -> List[str]:
        """Identify favorable prognostic markers"""
        markers = []
        mutations = genetic_data.get('mutations', {})
        
        if mutations.get('TP53') is False:
            markers.append('TP53 wild-type (favorable)')
        if mutations.get('BRCA1') or mutations.get('BRCA2'):
            markers.append('BRCA mutation (eligible for PARPi)')
        
        return markers
    
    def _identify_unfavorable_markers(self, genetic_data: Dict) -> List[str]:
        """Identify unfavorable prognostic markers"""
        markers = []
        mutations = genetic_data.get('mutations', {})
        
        if mutations.get('TP53'):
            markers.append('TP53 mutation (unfavorable)')
        if genetic_data.get('tmb', '').lower() == 'low':
            markers.append('Low tumor mutational burden (unfavorable)')
        
        return markers
    
    def _categorize_prognosis(self, genetic_data: Dict) -> str:
        """Categorize prognosis"""
        favorable = len(self._identify_favorable_markers(genetic_data))
        unfavorable = len(self._identify_unfavorable_markers(genetic_data))
        
        if favorable > unfavorable:
            return 'Favorable'
        elif unfavorable > favorable:
            return 'Unfavorable'
        else:
            return 'Intermediate'
    
    def _get_base_protocol(self, cancer_type: str, stage: str) -> Dict:
        """Get base treatment protocol"""
        # Map stage names to standard format
        stage_map = {
            'i': 'stage_1', '1': 'stage_1',
            'ii': 'stage_2', '2': 'stage_2',
            'iii': 'stage_3', '3': 'stage_3',
            'iv': 'stage_4', '4': 'stage_4',
        }
        
        stage_key = stage_map.get(stage.lower(), stage)
        
        if cancer_type in self.CANCER_TREATMENT_PROTOCOLS:
            if stage_key in self.CANCER_TREATMENT_PROTOCOLS[cancer_type]:
                return self.CANCER_TREATMENT_PROTOCOLS[cancer_type][stage_key]
        
        # Default protocol if not found
        return {
            'primary': ['Consult with oncologist'],
            'adjuvant': [],
            'targeted': [],
            'survival_rate_5yr': 50,
        }
    
    def _customize_protocol(self, base_protocol: Dict, patient_profile: Dict,
                           tumor_analysis: Dict, genetic_profile: Dict) -> Dict:
        """Customize protocol based on patient factors"""
        customized = base_protocol.copy()
        
        # Adjust based on patient fitness
        fitness = patient_profile.get('fitness_for_treatment', 'Fair')
        if fitness == 'Poor':
            customized['protocols'] = [p.replace('Chemotherapy', 'Reduced-dose Chemotherapy') 
                                      for p in customized.get('primary', [])]
        
        # Add targeted therapies if eligible
        if genetic_profile.get('targeted_therapy_eligible'):
            customized['targeted'] = genetic_profile.get('targeted_therapy_eligible', [])
        
        # Add immunotherapy if eligible
        if genetic_profile.get('immunotherapy_eligible'):
            customized['protocols'] = customized.get('primary', []) + ['Immunotherapy']
        
        return customized
    
    def _generate_side_effect_profile(self, plan: Dict) -> List[Dict]:
        """Generate comprehensive side effect profile"""
        side_effects = []
        treatments = plan.get('protocols', []) + plan.get('primary', [])
        
        for treatment in treatments:
            treatment_lower = treatment.lower()
            
            if 'chemo' in treatment_lower:
                side_effects.extend(self.TREATMENT_SIDE_EFFECTS.get('chemotherapy', []))
            elif 'radiation' in treatment_lower:
                side_effects.extend(self.TREATMENT_SIDE_EFFECTS.get('radiation', []))
            elif 'surgery' in treatment_lower:
                side_effects.extend(self.TREATMENT_SIDE_EFFECTS.get('surgery', []))
            elif 'immuno' in treatment_lower:
                side_effects.extend(self.TREATMENT_SIDE_EFFECTS.get('immunotherapy', []))
        
        # Remove duplicates
        seen = set()
        unique_side_effects = []
        for se in side_effects:
            if se['name'] not in seen:
                seen.add(se['name'])
                unique_side_effects.append(se)
        
        return unique_side_effects
    
    def _predict_outcomes(self, patient_profile: Dict, tumor_analysis: Dict,
                         genetic_profile: Dict, plan: Dict) -> Dict:
        """Predict treatment outcomes"""
        base_survival = 50  # Default
        
        # Get base survival from protocol
        if plan.get('survival_rate_5yr'):
            base_survival = plan.get('survival_rate_5yr')
        
        # Adjust for patient factors
        age = patient_profile.get('age_group', 'adult')
        ps = patient_profile.get('performance_status', 1)
        
        if age == 'elderly':
            base_survival *= 0.85
        if ps >= 2:
            base_survival *= 0.75
        
        return {
            'expected_5yr_survival': round(base_survival, 1),
            'remission_probability': round(70 + (20 if genetic_profile.get('targeted_therapy_eligible') else 0), 1),
            'quality_of_life_score': self._estimate_qol(plan),
        }
    
    def _estimate_response_probability(self, plan: Dict) -> float:
        """Estimate probability of treatment response"""
        base_response = 70.0
        
        if plan.get('targeted'):
            base_response += 15
        if plan.get('immunotherapy'):
            base_response += 10
        
        return min(base_response, 95.0)
    
    def _estimate_qol_impact(self, plan: Dict) -> str:
        """Estimate quality of life impact"""
        treatments = plan.get('protocols', []) + plan.get('primary', [])
        
        if len(treatments) > 2:
            return 'Moderate to High Impact'
        elif len(treatments) > 1:
            return 'Moderate Impact'
        else:
            return 'Mild Impact'
    
    def _estimate_qol(self, plan: Dict) -> int:
        """Estimate QOL score (0-100)"""
        score = 70
        
        if 'Chemotherapy' in str(plan.get('primary', [])):
            score -= 15
        if 'Radiation' in str(plan.get('primary', [])):
            score -= 10
        
        return max(score, 30)
    
    def _generate_monitoring_plan(self, cancer_type: str, stage: str) -> Dict:
        """Generate surveillance and monitoring plan"""
        return {
            'initial_phase': {
                'frequency': 'Every 2-4 weeks',
                'duration': '3-6 months',
                'tests': ['Physical exam', 'Labs (CBC, CMP)', 'Imaging as indicated']
            },
            'maintenance_phase': {
                'frequency': 'Every 3 months',
                'duration': '1-2 years',
                'tests': ['Physical exam', 'Labs every 3-6 months', 'Imaging every 3-6 months']
            },
            'long_term_phase': {
                'frequency': 'Every 6-12 months',
                'duration': '5+ years',
                'tests': ['Annual physical exam', 'Annual imaging for high-risk cases']
            }
        }
    
    def _find_relevant_trials(self, cancer_type: str, stage: str, genetic_profile: Dict) -> List[Dict]:
        """Find relevant clinical trials"""
        # This would connect to a clinical trials database
        trials = [
            {
                'trial_name': f'Personalized treatment study for {cancer_type}',
                'phase': 'Phase 3',
                'status': 'Active',
                'description': f'Evaluating novel therapies for stage {stage} {cancer_type}'
            }
        ]
        
        if genetic_profile.get('targeted_therapy_eligible'):
            trials.append({
                'trial_name': 'Targeted therapy cohort study',
                'phase': 'Phase 2',
                'status': 'Recruiting',
                'description': 'Evaluating targeted therapy combinations'
            })
        
        return trials
    
    def _identify_decision_points(self, treatment_plan: Dict) -> List[Dict]:
        """Identify key decision points in treatment pathway"""
        return [
            {
                'decision': 'Proceed with standard therapy vs clinical trial',
                'timing': 'Week 3-4 (Planning phase)',
                'options': ['Standard protocol', 'Clinical trial enrollment', 'Alternative therapy']
            },
            {
                'decision': 'Response assessment',
                'timing': 'During/After primary treatment',
                'options': ['Continue current plan', 'Modify regimen', 'Switch therapy']
            },
            {
                'decision': 'Adjuvant therapy',
                'timing': 'After primary treatment',
                'options': ['Proceed with adjuvant', 'Surveillance only', 'Clinical trial']
            }
        ]
    
    def _define_milestones(self, treatment_plan: Dict) -> List[Dict]:
        """Define expected treatment milestones"""
        return [
            {'milestone': 'Treatment initiation', 'expected_date': 'Week 4-5', 'marker': 'First therapy dose'},
            {'milestone': 'Initial response assessment', 'expected_date': 'Week 8-12', 'marker': 'First imaging'},
            {'milestone': 'Primary treatment completion', 'expected_date': 'Week 12-24', 'marker': 'Treatment finished'},
            {'milestone': 'Adjuvant therapy (if applicable)', 'expected_date': 'Week 24-28', 'marker': 'Adjuvant initiation'},
            {'milestone': 'Complete response assessment', 'expected_date': 'Month 3-6 post-treatment', 'marker': 'Final staging'},
        ]
    
    def _assess_cardiac_function(self, lab_values: Dict) -> str:
        """Assess cardiac function"""
        ejection_fraction = lab_values.get('ejection_fraction', 55)
        if ejection_fraction >= 50:
            return 'Normal'
        elif ejection_fraction >= 40:
            return 'Mild reduction'
        else:
            return 'Moderate to severe reduction'
    
    def _assess_renal_function(self, lab_values: Dict) -> str:
        """Assess renal function"""
        creatinine = lab_values.get('creatinine', 1.0)
        gfr = lab_values.get('gfr', 90)
        
        if gfr >= 60:
            return 'Normal'
        elif gfr >= 30:
            return 'Moderate impairment'
        else:
            return 'Severe impairment'
    
    def _assess_hepatic_function(self, lab_values: Dict) -> str:
        """Assess hepatic function"""
        bilirubin = lab_values.get('bilirubin', 0.7)
        ast = lab_values.get('ast', 30)
        alt = lab_values.get('alt', 30)
        
        if bilirubin <= 1.5 and ast <= 40 and alt <= 40:
            return 'Normal'
        else:
            return 'Impaired'
    
    def _assess_bone_marrow_function(self, lab_values: Dict) -> str:
        """Assess bone marrow function"""
        wbc = lab_values.get('wbc', 7.0)
        hgb = lab_values.get('hemoglobin', 12.0)
        platelets = lab_values.get('platelets', 200)
        
        if wbc >= 3.5 and hgb >= 10 and platelets >= 100:
            return 'Normal'
        else:
            return 'Impaired'
