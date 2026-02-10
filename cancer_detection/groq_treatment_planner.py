"""
Enhanced AI-Driven Cancer Treatment Planning with Groq Integration
Uses Groq's fast LLM API for intelligent, personalized treatment recommendations
"""

import os
import json
from typing import Dict, List, Optional
from datetime import datetime
from groq import Groq


class GroqTreatmentPlanner:
    """
    Advanced treatment planning engine powered by Groq API.
    Provides intelligent, evidence-based treatment recommendations.
    """
    
    def __init__(self):
        """Initialize Groq client"""
        self.client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        self.model = "llama-3.3-70b-versatile"  # Fast, powerful model
        
    def create_comprehensive_treatment_plan(
        self,
        patient_data: Dict,
        cancer_analyses: List[Dict],
        histopathology_reports: List[Dict],
        genomic_profiles: List[Dict]
    ) -> Dict:
        """
        Create a comprehensive treatment plan integrating all available data sources.
        
        Args:
            patient_data: Patient demographics and medical history
            cancer_analyses: List of cancer image analyses
            histopathology_reports: List of histopathology reports
            genomic_profiles: List of genomic test results
            
        Returns:
            Comprehensive treatment plan with integrated recommendations
        """
        # Compile all data into a structured format
        integrated_data = self._integrate_all_data(
            patient_data,
            cancer_analyses,
            histopathology_reports,
            genomic_profiles
        )
        
        # Generate treatment recommendations using Groq
        treatment_plan = self._generate_treatment_recommendations(integrated_data)
        
        # Generate pathway and monitoring schedule
        pathway = self._generate_treatment_pathway(treatment_plan, integrated_data)
        
        # Generate clinical decision support
        decision_support = self._generate_decision_support(treatment_plan, integrated_data)
        
        # Find relevant clinical trials
        clinical_trials = self._find_clinical_trials(integrated_data)
        
        # Calculate outcome predictions
        outcomes = self._predict_outcomes(treatment_plan, integrated_data)
        
        return {
            'plan_summary': treatment_plan,
            'treatment_pathway': pathway,
            'decision_support': decision_support,
            'clinical_trials': clinical_trials,
            'outcome_predictions': outcomes,
            'integrated_data': integrated_data,
            'generated_at': datetime.now().isoformat(),
        }
    
    def _integrate_all_data(
        self,
        patient_data: Dict,
        analyses: List[Dict],
        histopathology: List[Dict],
        genomics: List[Dict]
    ) -> Dict:
        """Integrate all data sources into a coherent patient profile"""
        
        # Determine primary cancer type and stage
        cancer_type = self._determine_cancer_type(analyses, histopathology)
        cancer_stage = self._determine_cancer_stage(analyses, histopathology)
        
        # Compile biomarkers and mutations
        biomarkers = self._compile_biomarkers(histopathology, genomics)
        mutations = self._compile_mutations(genomics)
        
        # Assess tumor characteristics
        tumor_characteristics = self._assess_tumor_characteristics(analyses, histopathology)
        
        return {
            'patient': patient_data,
            'cancer_type': cancer_type,
            'cancer_stage': cancer_stage,
            'tumor_characteristics': tumor_characteristics,
            'biomarkers': biomarkers,
            'mutations': mutations,
            'analyses': analyses,
            'histopathology_reports': histopathology,
            'genomic_profiles': genomics,
        }
    
    def _generate_treatment_recommendations(self, integrated_data: Dict) -> Dict:
        """Use Groq API to generate intelligent treatment recommendations"""
        
        prompt = self._build_treatment_prompt(integrated_data)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert oncologist AI assistant. Based on patient data, tumor characteristics, 
                        biomarkers, and genetic profiles, provide evidence-based, personalized cancer treatment recommendations. 
                        Consider NCCN guidelines, FDA-approved therapies, and emerging treatments. Structure your response as JSON."""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent medical advice
                max_tokens=3000,
            )
            
            # Parse response
            content = response.choices[0].message.content
            
            # Try to extract JSON from response
            try:
                # Look for JSON in response
                if '```json' in content:
                    json_start = content.find('```json') + 7
                    json_end = content.find('```', json_start)
                    content = content[json_start:json_end].strip()
                elif '```' in content:
                    json_start = content.find('```') + 3
                    json_end = content.find('```', json_start)
                    content = content[json_start:json_end].strip()
                
                return json.loads(content)
            except json.JSONDecodeError:
                # If JSON parsing fails, structure the text response
                return self._structure_text_response(content, integrated_data)
                
        except Exception as e:
            print(f"Error calling Groq API: {e}")
            # Fallback to rule-based recommendations
            return self._fallback_treatment_plan(integrated_data)
    
    def _build_treatment_prompt(self, data: Dict) -> str:
        """Build comprehensive prompt for Groq API"""
        
        patient = data.get('patient', {})
        cancer_type = data.get('cancer_type', 'Unknown')
        cancer_stage = data.get('cancer_stage', 'Unknown')
        tumor = data.get('tumor_characteristics', {})
        biomarkers = data.get('biomarkers', {})
        mutations = data.get('mutations', [])
        
        prompt = f"""
Patient Case Summary:
- Age: {patient.get('age', 'Unknown')}
- Sex: {patient.get('sex', 'Unknown')}
- Performance Status: {patient.get('performance_status', 'Unknown')}
- Comorbidities: {', '.join(patient.get('comorbidities', []))}

Cancer Diagnosis:
- Type: {cancer_type}
- Stage: {cancer_stage}
- Grade: {tumor.get('grade', 'Unknown')}
- Tumor Size: {tumor.get('size_mm', 'Unknown')} mm
- Location: {tumor.get('location', 'Unknown')}
- Lymph Node Involvement: {'Yes' if tumor.get('lymph_node_positive') else 'No'}
- Metastases: {'Yes (' + ', '.join(tumor.get('metastasis_sites', [])) + ')' if tumor.get('metastases') else 'No'}

Biomarkers:
{json.dumps(biomarkers, indent=2)}

Genetic Mutations:
{', '.join(mutations) if mutations else 'None identified'}

Histopathology Findings:
- Margin Status: {tumor.get('margin_status', 'Unknown')}
- Histologic Type: {tumor.get('histologic_type', 'Unknown')}

Please provide a comprehensive, evidence-based treatment plan in the following JSON format:
{{
    "primary_treatment": {{
        "modalities": ["List of primary treatment approaches"],
        "rationale": "Explanation of primary treatment strategy",
        "sequence": "Recommended treatment sequence",
        "duration": "Expected duration"
    }},
    "systemic_therapy": {{
        "chemotherapy": {{
            "recommended": true/false,
            "regimens": ["List of specific regimens if recommended"],
            "rationale": "Explanation"
        }},
        "targeted_therapy": {{
            "recommended": true/false,
            "agents": ["List of specific targeted agents"],
            "targets": ["Mutations/biomarkers being targeted"],
            "rationale": "Explanation"
        }},
        "immunotherapy": {{
            "recommended": true/false,
            "agents": ["List of immunotherapy agents"],
            "biomarker_basis": "Biomarker justification (PD-L1, MSI, TMB)",
            "rationale": "Explanation"
        }},
        "hormonal_therapy": {{
            "recommended": true/false,
            "agents": ["List of hormonal agents if applicable"],
            "rationale": "Explanation"
        }}
    }},
    "radiation_therapy": {{
        "recommended": true/false,
        "type": "IMRT/SBRT/etc",
        "dose": "Recommended dose and fractionation",
        "target": "Target area",
        "timing": "When in treatment sequence",
        "rationale": "Explanation"
    }},
    "surgery": {{
        "recommended": true/false,
        "procedure": "Specific surgical procedure",
        "timing": "When in treatment sequence",
        "rationale": "Explanation"
    }},
    "supportive_care": {{
        "growth_factors": ["List of growth factors needed"],
        "antiemetics": ["Antiemetic regimen"],
        "pain_management": ["Pain management strategies"],
        "nutrition": ["Nutritional support recommendations"]
    }},
    "monitoring": {{
        "imaging": {{
            "modality": "CT/MRI/PET",
            "frequency": "Frequency of imaging",
            "duration": "Duration of surveillance"
        }},
        "tumor_markers": {{
            "markers": ["Specific tumor markers to follow"],
            "frequency": "Testing frequency"
        }},
        "lab_monitoring": {{
            "tests": ["Specific lab tests"],
            "frequency": "Testing frequency"
        }}
    }},
    "expected_outcomes": {{
        "response_rate": "Expected overall response rate",
        "median_pfs": "Median progression-free survival",
        "median_os": "Median overall survival",
        "5yr_survival": "5-year survival estimate",
        "quality_of_life": "Expected QOL impact"
    }},
    "side_effects": {{
        "common": ["List common expected side effects"],
        "serious": ["List serious potential side effects"],
        "management": ["Key side effect management strategies"]
    }},
    "contraindications": ["List any contraindications based on patient factors"],
    "alternatives": ["List alternative treatment approaches if standard therapy not suitable"],
    "clinical_trial_opportunities": ["Suggest types of clinical trials to consider"],
    "multidisciplinary_recommendations": ["Recommendations for other specialists to involve"],
    "follow_up_plan": {{
        "phase_1": {{
            "duration": "First phase duration",
            "frequency": "Visit frequency",
            "assessments": ["Key assessments"]
        }},
        "phase_2": {{
            "duration": "Second phase duration",
            "frequency": "Visit frequency",
            "assessments": ["Key assessments"]
        }},
        "long_term": {{
            "frequency": "Long-term follow-up frequency",
            "assessments": ["Key assessments"],
            "survivorship_care": ["Survivorship care recommendations"]
        }}
    }}
}}

Provide comprehensive, evidence-based recommendations following NCCN guidelines and current standard of care.
"""
        return prompt
    
    def _generate_treatment_pathway(self, treatment_plan: Dict, integrated_data: Dict) -> Dict:
        """Generate ultra-detailed treatment pathway with week-by-week timeline using Groq AI"""
        
        # Extract treatment details
        primary = treatment_plan.get('primary_treatment', {})
        systemic = treatment_plan.get('systemic_therapy', {})
        radiation = treatment_plan.get('radiation_therapy', {})
        surgery = treatment_plan.get('surgery', {})
        
        prompt = f"""
Based on this comprehensive treatment plan for {integrated_data.get('cancer_type')} Stage {integrated_data.get('cancer_stage')}:

PRIMARY TREATMENT: {json.dumps(primary, indent=2)}
SYSTEMIC THERAPY: {json.dumps(systemic, indent=2)}
RADIATION: {json.dumps(radiation, indent=2)}
SURGERY: {json.dumps(surgery, indent=2)}

Patient: {integrated_data.get('patient', {}).get('age')} years old, Performance Status {integrated_data.get('patient', {}).get('performance_status')}

Create an ULTRA-DETAILED, week-by-week treatment pathway timeline. Break down the entire treatment journey into specific phases with detailed weekly activities, milestones, decision points, and monitoring requirements.

Return in this EXACT JSON format:
{{
    "pretreatment_phase": {{
        "duration": "2-3 weeks",
        "weeks": [
            {{
                "week_number": 1,
                "title": "Baseline Assessment Week",
                "description": "Complete baseline evaluations and prepare for treatment",
                "key_activities": [
                    "Complete staging workup (CT, PET-CT, MRI as needed)",
                    "Baseline tumor marker assessment",
                    "Echocardiogram and pulmonary function tests",
                    "Dental evaluation if chemotherapy planned",
                    "Fertility preservation counseling if applicable"
                ],
                "milestone": "All baseline assessments complete",
                "decision_point": "Confirm treatment plan with MDT",
                "labs_imaging": ["CBC", "CMP", "Tumor markers", "Baseline imaging"],
                "patient_prep": ["Medication review", "Consent forms", "Insurance authorization"]
            }}
        ]
    }},
    "active_treatment_phase": {{
        "duration": "12-24 weeks (varies by regimen)",
        "weeks": [
            {{
                "week_number": 1,
                "cycle": "Cycle 1",
                "title": "Treatment Initiation",
                "description": "Begin first cycle of systemic therapy",
                "key_activities": [
                    "Administer first chemotherapy infusion",
                    "Pre-medications: antiemetics, corticosteroids",
                    "Patient education on side effect management",
                    "Establish supportive care plan"
                ],
                "treatments": ["List specific drugs/interventions"],
                "milestone": "First cycle successfully administered",
                "decision_point": "Assess tolerance to first cycle",
                "monitoring": ["Daily: Temperature, symptoms", "CBC on day 7-10", "Phone follow-up day 3"],
                "side_effect_watch": ["Nausea/vomiting", "Fever", "Diarrhea", "Mucositis"],
                "patient_instructions": ["Take anti-nausea meds as prescribed", "Call if fever >100.4°F", "Maintain hydration"]
            }}
        ]
    }},
    "surgery_phase": {{
        "duration": "Variable based on procedure",
        "timing": "After neoadjuvant therapy or primary surgery",
        "weeks": [
            {{
                "week_number": "Post-chemo week 3-4",
                "title": "Pre-operative Week",
                "description": "Surgical preparation and optimization",
                "key_activities": [
                    "Pre-operative medical clearance",
                    "Anesthesia consultation",
                    "Imaging for surgical planning",
                    "Optimize nutritional status"
                ],
                "milestone": "Cleared for surgery",
                "labs_imaging": ["CBC", "CMP", "Coagulation studies", "Chest X-ray", "ECG"],
                "patient_prep": ["NPO instructions", "Bowel prep if needed", "Stop anticoagulants"]
            }},
            {{
                "week_number": "Surgery week",
                "title": "Surgical Intervention",
                "description": "Definitive surgical resection",
                "key_activities": [
                    "Surgical procedure as planned",
                    "Intraoperative pathology assessment",
                    "Post-op ICU/ward care",
                    "Early mobilization and recovery"
                ],
                "milestone": "Successful surgical resection",
                "monitoring": ["Vital signs Q4H", "Drain output", "Pain control", "Early ambulation"],
                "complications_watch": ["Bleeding", "Infection", "Ileus", "DVT/PE"]
            }}
        ]
    }},
    "adjuvant_phase": {{
        "duration": "Variable",
        "weeks": []
    }},
    "surveillance_phase": {{
        "duration": "5+ years",
        "schedule": {{
            "year_1": {{
                "frequency": "Every 3 months",
                "assessments": ["Physical exam", "Tumor markers", "Imaging as indicated"]
            }},
            "years_2_3": {{
                "frequency": "Every 3-6 months",
                "assessments": ["Physical exam", "Tumor markers", "Imaging per protocol"]
            }},
            "years_4_5_plus": {{
                "frequency": "Every 6-12 months",
                "assessments": ["Physical exam", "Annual imaging", "Cancer screening"]
            }}
        }}
    }},
    "supportive_care_throughout": {{
        "nutrition": ["Maintain protein intake", "Hydration goals", "Nutrition consult if needed"],
        "psychosocial": ["Support groups", "Counseling services", "Survivorship program"],
        "symptom_management": ["Pain control", "Fatigue management", "Sleep hygiene"],
        "exercise": ["Physical therapy referral", "Gentle exercise as tolerated", "Gradual return to activity"]
    }},
    "key_decision_timepoints": [
        {{
            "timepoint": "After Cycle 2-3",
            "decision": "Assess response to therapy",
            "criteria": ["Imaging response", "Tumor marker trend", "Clinical assessment"],
            "possible_actions": ["Continue same regimen", "Modify doses", "Change therapy", "Proceed to surgery"]
        }}
    ],
    "total_duration_estimate": "6-12 months for active treatment, then long-term surveillance",
    "flexibility_notes": "Timeline may be adjusted based on patient tolerance, response to therapy, and complications"
}}

Make this extremely detailed, practical, and specific to the cancer type and treatments planned. Include every important activity, test, decision point, and patient instruction.
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert oncologist creating ultra-detailed, week-by-week treatment pathways. Be extremely specific and comprehensive. Every week should have clear activities, milestones, and monitoring requirements."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=4000,  # Increased for detailed pathway
            )
            
            content = response.choices[0].message.content
            
            # Extract JSON
            if '```json' in content:
                json_start = content.find('```json') + 7
                json_end = content.find('```', json_start)
                content = content[json_start:json_end].strip()
            
            pathway = json.loads(content)
            
            # Ensure pathway has the expected structure
            if 'pretreatment_phase' not in pathway:
                pathway['pretreatment_phase'] = {"duration": "2-3 weeks", "weeks": []}
            if 'active_treatment_phase' not in pathway:
                pathway['active_treatment_phase'] = {"duration": "Variable", "weeks": []}
            
            return pathway
            
        except Exception as e:
            print(f"Error generating pathway: {e}")
            import traceback
            traceback.print_exc()
            return self._fallback_pathway(treatment_plan, integrated_data)
    
    def _generate_decision_support(self, treatment_plan: Dict, integrated_data: Dict) -> Dict:
        """Generate clinical decision support insights"""
        
        prompt = f"""
Provide clinical decision support for this case:

Cancer: {integrated_data.get('cancer_type')} Stage {integrated_data.get('cancer_stage')}
Patient Age: {integrated_data.get('patient', {}).get('age')}
Comorbidities: {integrated_data.get('patient', {}).get('comorbidities')}
Biomarkers: {json.dumps(integrated_data.get('biomarkers', {}), indent=2)}

Treatment Plan Summary:
{json.dumps(treatment_plan, indent=2)[:1000]}

Provide decision support in JSON format:
{{
    "key_considerations": ["List of critical factors influencing treatment decisions"],
    "risk_benefit_analysis": {{
        "benefits": ["Expected benefits"],
        "risks": ["Potential risks"],
        "net_benefit": "Overall risk-benefit assessment"
    }},
    "patient_counseling_points": ["Key points to discuss with patient"],
    "shared_decision_making": {{
        "patient_preferences_to_explore": ["Preferences to discuss"],
        "trade_offs": ["Trade-offs between treatment options"]
    }},
    "quality_metrics": {{
        "adherence_to_guidelines": "How well plan follows guidelines",
        "evidence_level": "Strength of evidence for recommendations",
        "personalization_factors": ["Factors that personalize this plan"]
    }},
    "red_flags": ["Warning signs/symptoms requiring immediate attention"],
    "second_opinion_triggers": ["When to seek second opinion"]
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert providing clinical decision support for oncology treatment plans."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            
            content = response.choices[0].message.content
            
            # Extract JSON
            if '```json' in content:
                json_start = content.find('```json') + 7
                json_end = content.find('```', json_start)
                content = content[json_start:json_end].strip()
            
            return json.loads(content)
            
        except Exception as e:
            print(f"Error generating decision support: {e}")
            return self._fallback_decision_support()
    
    def _find_clinical_trials(self, integrated_data: Dict) -> List[Dict]:
        """Find relevant clinical trials based on patient profile"""
        
        cancer_type = integrated_data.get('cancer_type', '')
        stage = integrated_data.get('cancer_stage', '')
        mutations = integrated_data.get('mutations', [])
        biomarkers = integrated_data.get('biomarkers', {})
        
        # In production, this would query ClinicalTrials.gov API
        # For now, generate relevant trial suggestions using Groq
        
        prompt = f"""
Suggest relevant clinical trial types for:
Cancer: {cancer_type} Stage {stage}
Mutations: {', '.join(mutations)}
Biomarkers: {json.dumps(biomarkers)}

List 3-5 types of clinical trials this patient should consider in JSON format:
{{
    "trials": [
        {{
            "trial_type": "Type of trial",
            "phase": "Phase I/II/III",
            "focus": "What the trial is testing",
            "eligibility_basis": "Why patient might be eligible",
            "potential_benefit": "Potential benefit over standard care"
        }}
    ]
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an oncology clinical trials expert. Suggest relevant trial types."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1000,
            )
            
            content = response.choices[0].message.content
            
            # Extract JSON
            if '```json' in content:
                json_start = content.find('```json') + 7
                json_end = content.find('```', json_start)
                content = content[json_start:json_end].strip()
            
            result = json.loads(content)
            return result.get('trials', [])
            
        except Exception as e:
            print(f"Error finding clinical trials: {e}")
            return []
    
    def _predict_outcomes(self, treatment_plan: Dict, integrated_data: Dict) -> Dict:
        """Predict treatment outcomes"""
        
        # Extract baseline survival rates from treatment plan
        expected_outcomes = treatment_plan.get('expected_outcomes', {})
        
        # Adjust based on patient factors
        age = integrated_data.get('patient', {}).get('age', 60)
        ps = integrated_data.get('patient', {}).get('performance_status', 1)
        comorbidities = len(integrated_data.get('patient', {}).get('comorbidities', []))
        
        # Base survival estimate
        try:
            base_5yr = float(expected_outcomes.get('5yr_survival', '50').replace('%', ''))
        except:
            base_5yr = 50.0
        
        # Age adjustment
        if age > 70:
            base_5yr *= 0.85
        elif age > 80:
            base_5yr *= 0.70
        
        # Performance status adjustment
        if ps >= 2:
            base_5yr *= 0.80
        
        # Comorbidity adjustment
        if comorbidities > 2:
            base_5yr *= 0.90
        
        return {
            'predicted_5yr_survival': round(base_5yr, 1),
            'response_rate': expected_outcomes.get('response_rate', 'Unknown'),
            'median_pfs': expected_outcomes.get('median_pfs', 'Unknown'),
            'median_os': expected_outcomes.get('median_os', 'Unknown'),
            'quality_of_life_impact': expected_outcomes.get('quality_of_life', 'Moderate impact expected'),
            'adjustment_factors': {
                'age_adjusted': age > 70,
                'performance_status_adjusted': ps >= 2,
                'comorbidity_adjusted': comorbidities > 2
            }
        }
    
    # Helper methods for data integration
    
    def _determine_cancer_type(self, analyses: List[Dict], histopathology: List[Dict]) -> str:
        """Determine primary cancer type from available data"""
        # Prioritize histopathology
        if histopathology:
            for report in histopathology:
                if report.get('cancer_type'):
                    return report['cancer_type']
        
        # Fall back to image analysis
        if analyses:
            for analysis in analyses:
                if analysis.get('tumor_type'):
                    return analysis['tumor_type']
        
        return 'Unknown'
    
    def _determine_cancer_stage(self, analyses: List[Dict], histopathology: List[Dict]) -> str:
        """Determine cancer stage"""
        # Prioritize TNM staging from histopathology
        if histopathology:
            for report in histopathology:
                if report.get('stage'):
                    return report['stage']
                if report.get('tnm_staging'):
                    return report['tnm_staging']
        
        # Fall back to image analysis
        if analyses:
            for analysis in analyses:
                if analysis.get('stage'):
                    return analysis['stage']
        
        return 'Unknown'
    
    def _compile_biomarkers(self, histopathology: List[Dict], genomics: List[Dict]) -> Dict:
        """Compile all biomarkers from available sources"""
        biomarkers = {}
        
        # From histopathology
        for report in histopathology:
            if report.get('biomarkers'):
                biomarkers.update(report['biomarkers'])
        
        # From genomics
        for profile in genomics:
            if profile.get('biomarkers'):
                biomarkers.update(profile['biomarkers'])
        
        return biomarkers
    
    def _compile_mutations(self, genomics: List[Dict]) -> List[str]:
        """Compile all identified mutations"""
        mutations = []
        
        for profile in genomics:
            if profile.get('mutations'):
                if isinstance(profile['mutations'], list):
                    mutations.extend(profile['mutations'])
                elif isinstance(profile['mutations'], dict):
                    mutations.extend([k for k, v in profile['mutations'].items() if v])
        
        return list(set(mutations))  # Remove duplicates
    
    def _assess_tumor_characteristics(self, analyses: List[Dict], histopathology: List[Dict]) -> Dict:
        """Assess comprehensive tumor characteristics"""
        characteristics = {
            'size_mm': None,
            'grade': None,
            'location': None,
            'histologic_type': None,
            'margin_status': None,
            'lymph_node_positive': False,
            'metastases': False,
            'metastasis_sites': []
        }
        
        # From histopathology
        for report in histopathology:
            if report.get('tumor_size_mm'):
                characteristics['size_mm'] = report['tumor_size_mm']
            if report.get('grade'):
                characteristics['grade'] = report['grade']
            if report.get('margin_status'):
                characteristics['margin_status'] = report['margin_status']
            if report.get('cancer_subtype'):
                characteristics['histologic_type'] = report['cancer_subtype']
            if report.get('lymph_node_status'):
                ln_status = report['lymph_node_status']
                if isinstance(ln_status, dict) and ln_status.get('involved'):
                    characteristics['lymph_node_positive'] = True
        
        # From analyses
        for analysis in analyses:
            if analysis.get('tumor_size_mm') and not characteristics['size_mm']:
                characteristics['size_mm'] = analysis['tumor_size_mm']
            if analysis.get('location'):
                characteristics['location'] = analysis['location']
        
        return characteristics
    
    # Fallback methods
    
    def _fallback_treatment_plan(self, integrated_data: Dict) -> Dict:
        """Fallback treatment plan if Groq API fails"""
        return {
            'primary_treatment': {
                'modalities': ['Multidisciplinary consultation required'],
                'rationale': 'Comprehensive treatment plan requires expert oncology review',
                'sequence': 'To be determined',
                'duration': 'Variable'
            },
            'note': 'Detailed AI-generated plan unavailable. Please consult with oncology team.'
        }
    
    def _fallback_pathway(self, treatment_plan: Dict, integrated_data: Dict) -> Dict:
        """Fallback pathway if Groq API fails"""
        return {
            'phases': [
                {
                    'name': 'Diagnosis Confirmation',
                    'duration_weeks': '2',
                    'activities': ['Complete staging', 'Genetic testing', 'Tumor board review'],
                    'milestones': ['Confirmed diagnosis and stage']
                },
                {
                    'name': 'Treatment Planning',
                    'duration_weeks': '2',
                    'activities': ['Discuss options', 'Obtain consent', 'Schedule treatments'],
                    'milestones': ['Treatment plan finalized']
                },
                {
                    'name': 'Active Treatment',
                    'duration_weeks': '12-24',
                    'activities': ['Deliver planned therapy', 'Manage side effects', 'Monitor response'],
                    'milestones': ['Treatment completion', 'Response assessment']
                }
            ]
        }
    
    def _fallback_decision_support(self) -> Dict:
        """Fallback decision support if Groq API fails"""
        return {
            'key_considerations': ['Comprehensive oncology review recommended'],
            'patient_counseling_points': ['Discuss treatment options', 'Review risks and benefits'],
            'quality_metrics': {
                'adherence_to_guidelines': 'Requires expert review',
                'evidence_level': 'To be determined by oncology team'
            }
        }
    
    def _structure_text_response(self, text: str, integrated_data: Dict) -> Dict:
        """Structure text response if JSON parsing fails"""
        # Basic structuring of text response
        return {
            'raw_recommendations': text,
            'cancer_type': integrated_data.get('cancer_type'),
            'cancer_stage': integrated_data.get('cancer_stage'),
            'note': 'Structured response not available. Review raw recommendations.'
        }
