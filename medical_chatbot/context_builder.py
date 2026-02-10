"""
Medical Context Builder
Retrieves and structures all medical data for a specific patient
"""
from django.contrib.auth import get_user_model
from authentication.models import PatientProfile, MedicalRecord
from patient_portal.models import (
    PatientSymptomLog, PatientAlert, PatientTreatmentExplanation,
    PatientSideEffectInfo
)
from cancer_detection.models import (
    CancerImageAnalysis, PersonalizedTreatmentPlan,
    HistopathologyReport, GenomicProfile, TreatmentOutcome
)
from patient_portal.consultation_models import Consultation
from medicine_identifier.models import MedicineIdentification
from datetime import datetime, timedelta
from django.utils import timezone

User = get_user_model()


class MedicalContextBuilder:
    """Build comprehensive medical context for a patient"""
    
    def __init__(self, patient):
        self.patient = patient
        
    def get_full_context(self):
        """Get complete medical context for the patient"""
        context = {
            'patient_info': self._get_patient_info(),
            'medical_history': self._get_medical_history(),
            'symptoms': self._get_symptoms(),
            'diagnoses': self._get_diagnoses(),
            'treatments': self._get_treatments(),
            'medications': self._get_medications(),
            'consultations': self._get_consultations(),
            'alerts': self._get_alerts(),
            'lab_results': self._get_lab_results(),
            'genomic_data': self._get_genomic_data(),
            'outcomes': self._get_outcomes(),
        }
        return context
    
    def _get_patient_info(self):
        """Get basic patient information"""
        try:
            profile = self.patient.patient_profile
            return {
                'name': self.patient.get_full_name() or self.patient.username,
                'email': self.patient.email,
                'phone': self.patient.phone_number,
                'date_of_birth': str(profile.date_of_birth) if profile.date_of_birth else None,
                'gender': profile.gender,
                'blood_group': profile.blood_group,
                'address': profile.address,
                'emergency_contact': profile.emergency_contact_name,
                'emergency_phone': profile.emergency_contact_phone,
                'allergies': profile.allergies,
                'current_medications': profile.current_medications,
            }
        except:
            return {
                'name': self.patient.get_full_name() or self.patient.username,
                'email': self.patient.email,
            }
    
    def _get_medical_history(self):
        """Get patient's medical history"""
        try:
            profile = self.patient.patient_profile
            return {
                'medical_history': profile.medical_history,
                'allergies': profile.allergies,
                'current_medications': profile.current_medications,
            }
        except:
            return {}
    
    def _get_symptoms(self):
        """Get recent symptom logs"""
        symptoms = PatientSymptomLog.objects.filter(
            patient=self.patient
        ).order_by('-log_date')[:10]
        
        return [{
            'date': str(symptom.log_date),
            'fatigue': symptom.fatigue,
            'pain': symptom.pain,
            'pain_location': symptom.pain_location,
            'nausea': symptom.nausea,
            'vomiting': symptom.vomiting,
            'appetite_loss': symptom.appetite_loss,
            'sleep_problems': symptom.sleep_problems,
            'anxiety': symptom.anxiety,
            'depression': symptom.depression,
            'overall_wellbeing': symptom.overall_wellbeing,
            'activity_level': symptom.activity_level,
            'additional_symptoms': symptom.additional_symptoms,
            'notes': symptom.notes,
            'severe_symptoms': symptom.get_severe_symptoms() if hasattr(symptom, 'get_severe_symptoms') else [],
        } for symptom in symptoms]
    
    def _get_diagnoses(self):
        """Get cancer diagnoses and analyses"""
        analyses = CancerImageAnalysis.objects.filter(
            user=self.patient
        ).order_by('-created_at')[:5]
        
        return [{
            'date': str(analysis.created_at.date()),
            'image_type': analysis.image_type,
            'tumor_detected': analysis.tumor_detected,
            'tumor_type': analysis.tumor_type,
            'tumor_stage': analysis.tumor_stage,
            'tumor_size_mm': analysis.tumor_size_mm,
            'tumor_location': analysis.tumor_location,
            'detection_confidence': analysis.detection_confidence,
            'notes': analysis.notes,
        } for analysis in analyses]
    
    def _get_treatments(self):
        """Get treatment plans"""
        plans = PersonalizedTreatmentPlan.objects.filter(
            patient=self.patient
        ).order_by('-created_at')[:5]
        
        treatments = []
        for plan in plans:
            treatments.append({
                'date': str(plan.created_at.date()),
                'plan_name': plan.plan_name,
                'cancer_type': plan.cancer_type,
                'cancer_stage': plan.cancer_stage,
                'status': plan.status,
                'primary_treatments': plan.primary_treatments,
                'adjuvant_treatments': plan.adjuvant_treatments,
                'targeted_therapies': plan.targeted_therapies,
                'side_effects': plan.side_effects,
                'predicted_5yr_survival': plan.predicted_5yr_survival,
                'remission_probability': plan.remission_probability,
                'expected_milestones': plan.expected_milestones,
                'oncologist_notes': plan.oncologist_notes,
            })
        
        # Also get patient-friendly explanations
        explanations = PatientTreatmentExplanation.objects.filter(
            patient=self.patient
        ).order_by('-created_at')[:3]
        
        for exp in explanations:
            treatments.append({
                'type': 'explanation',
                'title': exp.title,
                'summary': exp.summary,
                'journey_steps': exp.journey_steps,
                'what_to_expect': exp.what_to_expect,
            })
        
        return treatments
    
    def _get_medications(self):
        """Get identified medicines"""
        medicines = MedicineIdentification.objects.filter(
            user=self.patient
        ).order_by('-created_at')[:10]
        
        return [{
            'date': str(med.created_at.date()),
            'medicine_name': med.medicine_name,
            'generic_name': med.generic_name,
            'brand_name': med.brand_name,
            'manufacturer': med.manufacturer,
            'medicine_form': med.medicine_form,
            'strength': med.strength,
            'description': med.description,
            'uses': med.uses,
            'side_effects': med.side_effects,
            'warnings': med.warnings,
            'dosage_instructions': med.dosage_instructions,
            'drug_class': med.drug_class,
        } for med in medicines]
    
    def _get_consultations(self):
        """Get recent consultations"""
        consultations = Consultation.objects.filter(
            patient=self.patient
        ).order_by('-scheduled_datetime')[:5]
        
        return [{
            'date': str(consultation.scheduled_datetime.date()) if consultation.scheduled_datetime else str(consultation.created_at.date()),
            'doctor': consultation.doctor.get_full_name() if consultation.doctor else 'Unknown',
            'status': consultation.status,
            'mode': consultation.mode,
            'prescription': consultation.prescription,
            'doctor_notes': consultation.doctor_notes,
            'follow_up_required': consultation.follow_up_required,
            'follow_up_date': str(consultation.follow_up_date) if consultation.follow_up_date else None,
        } for consultation in consultations]
    
    def _get_alerts(self):
        """Get recent health alerts"""
        alerts = PatientAlert.objects.filter(
            patient=self.patient,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).order_by('-created_at')[:10]
        
        return [{
            'date': str(alert.created_at.date()),
            'type': alert.alert_type,
            'title': alert.title,
            'message': alert.message,
            'is_urgent': alert.is_urgent,
            'status': alert.status,
            'is_read': alert.is_read,
        } for alert in alerts]
    
    def _get_lab_results(self):
        """Get histopathology and lab reports"""
        reports = HistopathologyReport.objects.filter(
            patient=self.patient
        ).order_by('-created_at')[:5]
        
        return [{
            'date': str(report.created_at.date()),
            'status': report.status,
            'cancer_type': report.cancer_type,
            'cancer_subtype': report.cancer_subtype,
            'grade': report.grade,
            'stage': report.stage,
            'tnm_staging': report.tnm_staging,
            'tumor_size_mm': report.tumor_size_mm,
            'margin_status': report.margin_status,
            'biomarkers': report.biomarkers,
            'pathologist': report.pathologist_name,
            'hospital_lab': report.hospital_lab,
            'notes': report.notes,
        } for report in reports]
    
    def _get_genomic_data(self):
        """Get genomic profile data"""
        profiles = GenomicProfile.objects.filter(
            patient=self.patient
        ).order_by('-created_at')[:3]
        
        return [{
            'date': str(profile.created_at.date()),
            'test_type': profile.test_type,
            'mutations': profile.mutations,
            'biomarkers': profile.biomarkers,
            'actionable_mutations': profile.actionable_mutations,
            'targeted_therapy_eligibility': profile.targeted_therapy_eligibility,
            'immunotherapy_eligibility': profile.immunotherapy_eligibility,
            'pd_l1_status': profile.pd_l1_status,
            'msi_status': profile.msi_status,
            'tumor_mutational_burden': profile.tumor_mutational_burden,
        } for profile in profiles]
    
    def _get_outcomes(self):
        """Get treatment outcomes"""
        outcomes = TreatmentOutcome.objects.filter(
            patient=self.patient
        ).order_by('-created_at')[:5]
        
        return [{
            'date': str(outcome.created_at.date()),
            'status': outcome.status,
            'treatment_response': outcome.treatment_response,
            'progression_free_survival_days': outcome.progression_free_survival_days,
            'overall_survival_days': outcome.overall_survival_days,
            'quality_of_life_score': outcome.quality_of_life_score,
            'side_effects_experienced': outcome.side_effects_experienced,
            'notes': outcome.notes,
        } for outcome in outcomes]
    
    def get_context_summary(self):
        """Get a text summary of the medical context for LLM"""
        context = self.get_full_context()
        
        summary_parts = []
        
        # Patient Info
        info = context['patient_info']
        summary_parts.append(f"PATIENT INFORMATION:")
        summary_parts.append(f"Name: {info.get('name', 'Unknown')}")
        if info.get('date_of_birth'):
            summary_parts.append(f"Date of Birth: {info['date_of_birth']}")
        if info.get('gender'):
            summary_parts.append(f"Gender: {info['gender']}")
        if info.get('blood_group'):
            summary_parts.append(f"Blood Group: {info['blood_group']}")
        if info.get('allergies'):
            summary_parts.append(f"Allergies: {info['allergies']}")
        if info.get('current_medications'):
            summary_parts.append(f"Current Medications: {info['current_medications']}")
        
        # Medical History
        if context['medical_history'].get('medical_history'):
            summary_parts.append(f"\nMEDICAL HISTORY:")
            summary_parts.append(context['medical_history']['medical_history'])
        
        # Recent Symptoms
        if context['symptoms']:
            summary_parts.append(f"\nRECENT SYMPTOMS:")
            for symptom in context['symptoms'][:3]:
                symptom_details = []
                if symptom.get('pain'):
                    symptom_details.append(f"Pain: {symptom['pain']}/5")
                if symptom.get('pain_location'):
                    symptom_details.append(f"Location: {symptom['pain_location']}")
                if symptom.get('fatigue'):
                    symptom_details.append(f"Fatigue: {symptom['fatigue']}/5")
                if symptom.get('nausea'):
                    symptom_details.append(f"Nausea: {symptom['nausea']}/5")
                if symptom.get('anxiety'):
                    symptom_details.append(f"Anxiety: {symptom['anxiety']}/5")
                if symptom.get('overall_wellbeing'):
                    symptom_details.append(f"Wellbeing: {symptom['overall_wellbeing']}/5")
                
                if symptom_details:
                    summary_parts.append(f"- {symptom['date']}: {', '.join(symptom_details)}")
                if symptom.get('additional_symptoms'):
                    summary_parts.append(f"  Additional: {symptom['additional_symptoms']}")
                if symptom.get('notes'):
                    summary_parts.append(f"  Notes: {symptom['notes']}")
        
        # Diagnoses
        if context['diagnoses']:
            summary_parts.append(f"\nDIAGNOSES:")
            for diagnosis in context['diagnoses']:
                if diagnosis.get('tumor_detected'):
                    summary_parts.append(f"- {diagnosis['date']}: {diagnosis.get('tumor_type', 'Unknown')} (Stage: {diagnosis.get('tumor_stage', 'Unknown')}, Confidence: {diagnosis.get('detection_confidence', 0)}%)")
                    if diagnosis.get('tumor_location'):
                        summary_parts.append(f"  Location: {diagnosis['tumor_location']}")
                    if diagnosis.get('tumor_size_mm'):
                        summary_parts.append(f"  Size: {diagnosis['tumor_size_mm']}mm")
        
        # Active Treatments
        if context['treatments']:
            summary_parts.append(f"\nACTIVE TREATMENTS:")
            for treatment in context['treatments'][:2]:
                if treatment.get('cancer_type'):
                    summary_parts.append(f"- {treatment['cancer_type']} Treatment (Stage: {treatment.get('cancer_stage', 'Unknown')}, Status: {treatment['status']})")
                    if treatment.get('primary_treatments'):
                        summary_parts.append(f"  Primary Treatments: {treatment['primary_treatments']}")
                    if treatment.get('predicted_5yr_survival'):
                        summary_parts.append(f"  5-Year Survival: {treatment['predicted_5yr_survival']}%")
        
        # Recent Consultations
        if context['consultations']:
            summary_parts.append(f"\nRECENT CONSULTATIONS:")
            for consult in context['consultations'][:3]:
                summary_parts.append(f"- {consult['date']} with Dr. {consult['doctor']} ({consult.get('mode', 'Unknown')})")
                if consult.get('doctor_notes'):
                    summary_parts.append(f"  Notes: {consult['doctor_notes']}")
                if consult.get('prescription'):
                    summary_parts.append(f"  Prescription: {consult['prescription']}")
        
        # Active Alerts
        if context['alerts']:
            active_alerts = [a for a in context['alerts'] if not a['is_read']]
            if active_alerts:
                summary_parts.append(f"\nACTIVE ALERTS:")
                for alert in active_alerts[:3]:
                    summary_parts.append(f"- {alert['title']}: {alert['message']}")
        
        return "\n".join(summary_parts)
