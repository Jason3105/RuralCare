"""
Clinical Decision Support Views
Doctor-only views for AI confidence, XAI, tumor board, and toxicity prediction
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods, require_POST
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q
import json

from .models import (
    AIConfidenceMetadata, XAIExplanation, TumorBoardSession,
    TumorBoardMember, TumorBoardAuditLog, ToxicityPrediction,
    DoctorSymptomMonitor
)
from .ai_services import AIConfidenceGenerator, XAIExplanationGenerator
from .toxicity_service import ToxicityPredictor
from cancer_detection.models import (
    PersonalizedTreatmentPlan, CancerImageAnalysis,
    HistopathologyReport, GenomicProfile
)
from patient_portal.models import PatientSymptomLog
from authentication.models import User, DoctorProfile


def doctor_required(view_func):
    """Decorator to ensure only doctors can access the view"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.user_type != 'doctor':
            messages.error(request, 'This feature is only available to doctors.')
            return redirect('patient_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


# ============================================================================
# AI Confidence Dashboard Views
# ============================================================================

@login_required
@doctor_required
def ai_confidence_dashboard(request):
    """Main AI Confidence Dashboard for doctors"""
    # Get all confidence records for filtering
    confidence_records = AIConfidenceMetadata.objects.select_related('patient').order_by('-created_at')
    
    # Filter by patient if provided
    patient_id = request.GET.get('patient')
    if patient_id:
        confidence_records = confidence_records.filter(patient_id=patient_id)
    
    # Filter by analysis type
    analysis_type = request.GET.get('type')
    if analysis_type:
        confidence_records = confidence_records.filter(analysis_type=analysis_type)
    
    # Filter by confidence level
    confidence_level = request.GET.get('level')
    if confidence_level:
        confidence_records = confidence_records.filter(confidence_level=confidence_level)
    
    # Pagination
    paginator = Paginator(confidence_records, 10)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)
    
    # Get patients for filter dropdown
    patients = User.objects.filter(user_type='patient').order_by('username')
    
    context = {
        'page_obj': page_obj,
        'patients': patients,
        'analysis_types': AIConfidenceMetadata.ANALYSIS_TYPE_CHOICES,
        'confidence_levels': AIConfidenceMetadata.CONFIDENCE_LEVEL_CHOICES,
        'selected_patient': patient_id,
        'selected_type': analysis_type,
        'selected_level': confidence_level,
    }
    return render(request, 'clinical_decision_support/ai_confidence_dashboard.html', context)


@login_required
@doctor_required
def ai_confidence_detail(request, confidence_id):
    """Detailed AI Confidence view"""
    confidence = get_object_or_404(AIConfidenceMetadata, id=confidence_id)
    
    context = {
        'confidence': confidence,
    }
    return render(request, 'clinical_decision_support/ai_confidence_detail.html', context)


@login_required
@doctor_required
def generate_confidence_for_plan(request, plan_id):
    """Generate AI confidence metadata for a treatment plan"""
    plan = get_object_or_404(PersonalizedTreatmentPlan, id=plan_id)
    
    # Gather data sources
    data_sources = {
        'imaging_analysis': plan.analysis is not None,
        'pathology_report': HistopathologyReport.objects.filter(patient=plan.patient).exists(),
        'genomic_data': GenomicProfile.objects.filter(patient=plan.patient).exists(),
        'patient_history': True,  # Assume patient profile exists
    }
    
    # Add detection confidence if available
    if plan.analysis:
        data_sources['detection_confidence'] = plan.analysis.detection_confidence
        data_sources['imaging_stage'] = plan.analysis.tumor_stage
    
    # Get histopathology stage if available
    histo = HistopathologyReport.objects.filter(patient=plan.patient).first()
    if histo:
        data_sources['pathology_stage'] = histo.stage
    
    # Generate confidence
    generator = AIConfidenceGenerator()
    confidence_data = generator.calculate_confidence(
        analysis_type='treatment_plan',
        data_sources=data_sources,
        ocr_quality=histo.analysis_confidence if histo else None
    )
    
    # Create or update confidence record
    confidence, created = AIConfidenceMetadata.objects.update_or_create(
        source_id=plan.id,
        analysis_type='treatment_plan',
        defaults={
            'patient': plan.patient,
            'overall_confidence': confidence_data['overall_confidence'],
            'data_quality_score': confidence_data['data_quality_score'],
            'model_certainty_score': confidence_data['model_certainty_score'],
            'evidence_strength_score': confidence_data['evidence_strength_score'],
            'confidence_level': confidence_data['confidence_level'],
            'uncertainty_reasons': confidence_data['uncertainty_reasons'],
            'missing_data_sources': confidence_data['missing_data_sources'],
            'conflicting_outputs': confidence_data['conflicting_outputs'],
            'ocr_quality_score': confidence_data['ocr_quality_score'],
            'evidence_breakdown': confidence_data['evidence_breakdown'],
            'detailed_explanation': confidence_data['detailed_explanation'],
            'patient_explanation': confidence_data['patient_explanation'],
        }
    )
    
    messages.success(request, 'AI Confidence analysis generated successfully.')
    return redirect('clinical_decision_support:ai_confidence_detail', confidence_id=confidence.id)


# ============================================================================
# XAI Dashboard Views
# ============================================================================

@login_required
@doctor_required
def xai_dashboard(request):
    """Explainable AI Dashboard for doctors"""
    xai_records = XAIExplanation.objects.select_related(
        'treatment_plan', 'patient'
    ).order_by('-created_at')
    
    # Filter by patient
    patient_id = request.GET.get('patient')
    if patient_id:
        xai_records = xai_records.filter(patient_id=patient_id)
    
    # Pagination
    paginator = Paginator(xai_records, 10)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)
    
    patients = User.objects.filter(user_type='patient').order_by('username')
    
    context = {
        'page_obj': page_obj,
        'patients': patients,
        'selected_patient': patient_id,
    }
    return render(request, 'clinical_decision_support/xai_dashboard.html', context)


@login_required
@doctor_required
def xai_detail(request, xai_id):
    """Detailed XAI Explanation view"""
    xai = get_object_or_404(XAIExplanation, id=xai_id)
    
    context = {
        'xai': xai,
    }
    return render(request, 'clinical_decision_support/xai_detail.html', context)


@login_required
@doctor_required
def generate_xai_for_plan(request, plan_id):
    """Generate XAI explanation for a treatment plan"""
    plan = get_object_or_404(PersonalizedTreatmentPlan, id=plan_id)
    
    # Gather data
    tumor_data = plan.tumor_analysis or {}
    tumor_data['stage'] = plan.cancer_stage
    
    genomic = GenomicProfile.objects.filter(patient=plan.patient).first()
    genomic_data = genomic.analysis_results if genomic else {}
    if genomic:
        genomic_data['mutations'] = genomic.mutations
        genomic_data['tmb'] = genomic.tumor_mutational_burden
    
    biomarker_data = plan.genetic_profile or {}
    
    patient_data = plan.patient_profile or {}
    if hasattr(plan.patient, 'patient_profile'):
        patient_data['comorbidities'] = []
        if plan.patient.patient_profile.medical_history:
            patient_data['comorbidities'] = plan.patient.patient_profile.medical_history.split(',')
    
    treatment_data = {
        'primary_treatments': plan.primary_treatments,
        'targeted_therapies': plan.targeted_therapies,
        'rationale': plan.oncologist_notes or ''
    }
    
    # Generate XAI
    generator = XAIExplanationGenerator()
    xai_data = generator.generate_xai_explanation(
        treatment_plan=treatment_data,
        tumor_data=tumor_data,
        genomic_data=genomic_data,
        biomarker_data=biomarker_data,
        patient_data=patient_data
    )
    
    # Create or update XAI record
    xai, created = XAIExplanation.objects.update_or_create(
        treatment_plan=plan,
        defaults={
            'patient': plan.patient,
            'contributing_factors': xai_data['contributing_factors'],
            'tumor_factors': xai_data['tumor_factors'],
            'genomic_factors': xai_data['genomic_factors'],
            'biomarker_factors': xai_data['biomarker_factors'],
            'comorbidity_factors': xai_data['comorbidity_factors'],
            'recommendation_summary': xai_data['recommendation_summary'],
            'explanation_text': xai_data['explanation_text'],
            'structured_explanation': xai_data['structured_explanation'],
            'disclaimer': xai_data['disclaimer'],
        }
    )
    
    messages.success(request, 'XAI Explanation generated successfully.')
    return redirect('clinical_decision_support:xai_detail', xai_id=xai.id)


# ============================================================================
# Tumor Board Views
# ============================================================================

@login_required
@doctor_required
def tumor_board_list(request):
    """List all tumor board sessions"""
    sessions = TumorBoardSession.objects.select_related(
        'patient', 'treatment_plan', 'created_by'
    ).prefetch_related('members')
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        sessions = sessions.filter(status=status)
    
    # Filter sessions where current doctor is a member or creator
    my_sessions = request.GET.get('my_sessions')
    if my_sessions:
        sessions = sessions.filter(
            Q(created_by=request.user) |
            Q(members__doctor=request.user)
        ).distinct()
    
    sessions = sessions.order_by('-created_at')
    
    paginator = Paginator(sessions, 10)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)
    
    context = {
        'page_obj': page_obj,
        'status_choices': TumorBoardSession.SESSION_STATUS_CHOICES,
        'selected_status': status,
        'my_sessions': my_sessions,
    }
    return render(request, 'clinical_decision_support/tumor_board_list.html', context)


@login_required
@doctor_required
def tumor_board_create(request):
    """Create a new tumor board session"""
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        patient_id = request.POST.get('patient_id')
        plan_id = request.POST.get('plan_id')
        scheduled_at = request.POST.get('scheduled_at')
        
        patient = get_object_or_404(User, id=patient_id, user_type='patient')
        plan = get_object_or_404(PersonalizedTreatmentPlan, id=plan_id, patient=patient)
        
        session = TumorBoardSession.objects.create(
            title=title,
            description=description,
            patient=patient,
            treatment_plan=plan,
            created_by=request.user,
            scheduled_at=scheduled_at if scheduled_at else None,
            status='draft'
        )
        
        # Create audit log
        TumorBoardAuditLog.objects.create(
            session=session,
            action='session_created',
            actor=request.user,
            details={'title': title},
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        messages.success(request, 'Tumor Board session created successfully.')
        return redirect('clinical_decision_support:tumor_board_detail', session_id=session.id)
    
    # Get patients with treatment plans
    patients = User.objects.filter(user_type='patient').order_by('username')
    plans = PersonalizedTreatmentPlan.objects.select_related('patient').order_by('-created_at')
    
    context = {
        'patients': patients,
        'plans': plans,
    }
    return render(request, 'clinical_decision_support/tumor_board_create.html', context)


@login_required
@doctor_required
def tumor_board_detail(request, session_id):
    """View tumor board session details"""
    session = get_object_or_404(
        TumorBoardSession.objects.select_related('patient', 'treatment_plan', 'created_by'),
        id=session_id
    )
    members = session.members.select_related('doctor').order_by('invited_at')
    audit_logs = session.audit_logs.select_related('actor').order_by('-timestamp')[:20]
    
    # Get XAI if available
    xai = XAIExplanation.objects.filter(treatment_plan=session.treatment_plan).first()
    
    # Get confidence if available
    confidence = AIConfidenceMetadata.objects.filter(
        source_id=session.treatment_plan.id,
        analysis_type='treatment_plan'
    ).first()
    
    context = {
        'session': session,
        'members': members,
        'audit_logs': audit_logs,
        'xai': xai,
        'confidence': confidence,
        'role_choices': TumorBoardMember.ROLE_CHOICES,
        'is_creator': session.created_by == request.user,
    }
    return render(request, 'clinical_decision_support/tumor_board_detail.html', context)


@login_required
@doctor_required
@require_POST
def tumor_board_invite_member(request, session_id):
    """Invite a doctor to tumor board session"""
    session = get_object_or_404(TumorBoardSession, id=session_id)
    
    if session.created_by != request.user:
        messages.error(request, 'Only the session creator can invite members.')
        return redirect('clinical_decision_support:tumor_board_detail', session_id=session_id)
    
    doctor_id = request.POST.get('doctor_id')
    role = request.POST.get('role')
    
    doctor = get_object_or_404(User, id=doctor_id, user_type='doctor')
    
    if TumorBoardMember.objects.filter(session=session, doctor=doctor).exists():
        messages.warning(request, 'This doctor is already invited.')
        return redirect('clinical_decision_support:tumor_board_detail', session_id=session_id)
    
    member = TumorBoardMember.objects.create(
        session=session,
        doctor=doctor,
        role=role
    )
    
    # Audit log
    TumorBoardAuditLog.objects.create(
        session=session,
        action='member_invited',
        actor=request.user,
        details={'doctor': doctor.username, 'role': role},
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    messages.success(request, f'Dr. {doctor.username} has been invited.')
    return redirect('clinical_decision_support:tumor_board_detail', session_id=session_id)


@login_required
@doctor_required
@require_POST
def tumor_board_submit_decision(request, session_id):
    """Submit decision for tumor board"""
    session = get_object_or_404(TumorBoardSession, id=session_id)
    
    try:
        member = TumorBoardMember.objects.get(session=session, doctor=request.user)
    except TumorBoardMember.DoesNotExist:
        messages.error(request, 'You are not a member of this tumor board.')
        return redirect('clinical_decision_support:tumor_board_detail', session_id=session_id)
    
    decision = request.POST.get('decision')
    comments = request.POST.get('comments')
    modifications = request.POST.get('modifications')
    
    member.decision = decision
    member.comments = comments
    member.decision_date = timezone.now()
    if modifications:
        member.suggested_modifications = [m.strip() for m in modifications.split('\n') if m.strip()]
    member.save()
    
    # Audit log
    TumorBoardAuditLog.objects.create(
        session=session,
        action='decision_made',
        actor=request.user,
        details={'decision': decision, 'role': member.role},
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    # Check if consensus is achieved
    members = session.members.all()
    if members.exists():
        all_decided = all(m.decision != 'pending' for m in members)
        all_approved = all(m.decision == 'approved' for m in members)
        
        if all_decided and all_approved:
            session.status = 'consensus_achieved'
            session.consensus_reached = True
            session.consensus_date = timezone.now()
            session.save()
            
            TumorBoardAuditLog.objects.create(
                session=session,
                action='consensus_reached',
                actor=request.user,
                details={'consensus': 'All members approved'},
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, 'Consensus achieved! Treatment plan can now be activated.')
        elif all_decided:
            session.status = 'in_review'
            session.save()
    
    messages.success(request, 'Your decision has been recorded.')
    return redirect('clinical_decision_support:tumor_board_detail', session_id=session_id)


@login_required
@doctor_required
@require_POST
def tumor_board_activate_plan(request, session_id):
    """Activate treatment plan after consensus"""
    session = get_object_or_404(TumorBoardSession, id=session_id)
    
    if not session.can_activate_plan():
        messages.error(request, 'Cannot activate plan without consensus.')
        return redirect('clinical_decision_support:tumor_board_detail', session_id=session_id)
    
    plan = session.treatment_plan
    plan.status = 'active'
    plan.activated_date = timezone.now()
    plan.reviewed_by = request.user
    plan.save()
    
    session.status = 'closed'
    session.final_recommendation = request.POST.get('final_recommendation', '')
    session.save()
    
    # Audit log
    TumorBoardAuditLog.objects.create(
        session=session,
        action='plan_activated',
        actor=request.user,
        details={'plan_id': str(plan.id)},
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    messages.success(request, 'Treatment plan has been activated.')
    return redirect('clinical_decision_support:tumor_board_detail', session_id=session_id)


# ============================================================================
# Toxicity Prediction Views
# ============================================================================

@login_required
@doctor_required
def toxicity_dashboard(request):
    """Toxicity prediction dashboard"""
    predictions = ToxicityPrediction.objects.select_related(
        'patient', 'treatment_plan'
    ).order_by('-created_at')
    
    # Filter by patient
    patient_id = request.GET.get('patient')
    if patient_id:
        predictions = predictions.filter(patient_id=patient_id)
    
    # Filter by risk level
    risk_level = request.GET.get('risk')
    if risk_level:
        predictions = predictions.filter(overall_risk_level=risk_level)
    
    paginator = Paginator(predictions, 10)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)
    
    patients = User.objects.filter(user_type='patient').order_by('username')
    
    context = {
        'page_obj': page_obj,
        'patients': patients,
        'risk_levels': ToxicityPrediction.RISK_LEVEL_CHOICES,
        'selected_patient': patient_id,
        'selected_risk': risk_level,
    }
    return render(request, 'clinical_decision_support/toxicity_dashboard.html', context)


@login_required
@doctor_required
def toxicity_detail(request, prediction_id):
    """Detailed toxicity prediction view"""
    prediction = get_object_or_404(ToxicityPrediction, id=prediction_id)
    
    context = {
        'prediction': prediction,
    }
    return render(request, 'clinical_decision_support/toxicity_detail.html', context)


@login_required
@doctor_required
def toxicity_predict(request):
    """Generate new toxicity prediction"""
    if request.method == 'POST':
        patient_id = request.POST.get('patient_id')
        plan_id = request.POST.get('plan_id')
        drug_name = request.POST.get('drug_name')
        
        patient = get_object_or_404(User, id=patient_id, user_type='patient')
        plan = get_object_or_404(PersonalizedTreatmentPlan, id=plan_id) if plan_id else None
        
        # Gather lab values from form
        labs = {}
        lab_fields = ['creatinine', 'egfr', 'bilirubin', 'alt', 'ast', 
                      'neutrophils', 'platelets', 'hemoglobin', 'lvef']
        for field in lab_fields:
            value = request.POST.get(field)
            if value:
                try:
                    labs[field] = float(value)
                except ValueError:
                    pass
        
        # Gather patient data
        patient_data = {
            'age': plan.patient_profile.get('age', 50) if plan else 50,
            'performance_status': int(request.POST.get('performance_status', 0)),
            'comorbidities': request.POST.get('comorbidities', '').split(',')
        }
        
        # Generate prediction
        predictor = ToxicityPredictor()
        result = predictor.predict_toxicities(drug_name, labs, patient_data)
        
        # Save prediction
        prediction = ToxicityPrediction.objects.create(
            patient=patient,
            treatment_plan=plan,
            drug_name=drug_name,
            drug_class=result['drug_class'],
            predicted_toxicities=result['predicted_toxicities'],
            high_risk_toxicities=result['high_risk_toxicities'],
            overall_risk_level=result['overall_risk_level'],
            dose_adjustments=result['dose_adjustments'],
            correlated_lab_values=result['correlated_lab_values'],
            prediction_confidence=result['prediction_confidence'],
            patient_summary=result['patient_summary']
        )
        
        messages.success(request, 'Toxicity prediction generated successfully.')
        return redirect('clinical_decision_support:toxicity_detail', prediction_id=prediction.id)
    
    patients = User.objects.filter(user_type='patient').order_by('username')
    plans = PersonalizedTreatmentPlan.objects.select_related('patient').order_by('-created_at')
    
    context = {
        'patients': patients,
        'plans': plans,
    }
    return render(request, 'clinical_decision_support/toxicity_predict.html', context)


# ============================================================================
# Doctor Symptom Monitoring Views
# ============================================================================

@login_required
@doctor_required
def symptom_monitoring_dashboard(request):
    """Doctor's symptom monitoring dashboard"""
    monitors = DoctorSymptomMonitor.objects.select_related(
        'patient', 'treatment_plan'
    ).filter(doctor=request.user).order_by('-updated_at')
    
    # Filter by alert status
    alert_status = request.GET.get('alert')
    if alert_status:
        monitors = monitors.filter(alert_status=alert_status)
    
    paginator = Paginator(monitors, 10)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)
    
    # Get patients with recent severe symptoms
    severe_alerts = DoctorSymptomMonitor.objects.filter(
        doctor=request.user,
        alert_status__in=['urgent', 'critical']
    ).count()
    
    context = {
        'page_obj': page_obj,
        'alert_statuses': DoctorSymptomMonitor.ALERT_STATUS_CHOICES,
        'selected_alert': alert_status,
        'severe_alerts_count': severe_alerts,
    }
    return render(request, 'clinical_decision_support/symptom_monitoring_dashboard.html', context)


@login_required
@doctor_required
def symptom_monitoring_patient(request, patient_id):
    """View symptom details for a specific patient"""
    patient = get_object_or_404(User, id=patient_id, user_type='patient')
    
    # Get or create monitor
    monitor, created = DoctorSymptomMonitor.objects.get_or_create(
        patient=patient,
        doctor=request.user,
        defaults={'alert_status': 'none'}
    )
    
    # Get symptom logs
    symptom_logs = PatientSymptomLog.objects.filter(patient=patient).order_by('-log_date')
    
    # Get treatment plan
    plan = PersonalizedTreatmentPlan.objects.filter(patient=patient).order_by('-created_at').first()
    
    # Build symptom timeline
    timeline_data = []
    for log in symptom_logs[:30]:  # Last 30 entries
        severe_symptoms = log.get_severe_symptoms()
        timeline_data.append({
            'date': log.log_date.isoformat(),
            'overall_wellbeing': log.overall_wellbeing,
            'severe_symptoms': severe_symptoms,
            'has_severe': len(severe_symptoms) > 0
        })
    
    # Check for threshold breaches
    breaches = []
    for log in symptom_logs[:7]:  # Check last week
        severe = log.get_severe_symptoms()
        for s in severe:
            breaches.append({
                'symptom': s['symptom'],
                'severity': s['severity'],
                'date': log.log_date.isoformat(),
                'threshold': 3  # Threshold is 3 (moderate)
            })
    
    # Update monitor
    if breaches:
        if any(b['severity'] >= 5 for b in breaches):
            monitor.alert_status = 'critical'
        elif any(b['severity'] >= 4 for b in breaches):
            monitor.alert_status = 'urgent'
        else:
            monitor.alert_status = 'attention'
    else:
        monitor.alert_status = 'none'
    
    monitor.threshold_breaches = breaches[:10]
    monitor.save()
    
    paginator = Paginator(symptom_logs, 10)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)
    
    context = {
        'patient': patient,
        'monitor': monitor,
        'page_obj': page_obj,
        'plan': plan,
        'timeline_data': json.dumps(timeline_data),
        'breaches': breaches[:5],
    }
    return render(request, 'clinical_decision_support/symptom_monitoring_patient.html', context)


@login_required
@doctor_required
@require_POST
def add_intervention(request, patient_id):
    """Add a doctor intervention/note"""
    patient = get_object_or_404(User, id=patient_id, user_type='patient')
    
    monitor = get_object_or_404(DoctorSymptomMonitor, patient=patient, doctor=request.user)
    
    intervention = {
        'date': timezone.now().isoformat(),
        'intervention': request.POST.get('intervention'),
        'doctor': request.user.username
    }
    
    interventions = monitor.interventions or []
    interventions.append(intervention)
    monitor.interventions = interventions
    monitor.doctor_notes = request.POST.get('notes', monitor.doctor_notes)
    monitor.last_reviewed_at = timezone.now()
    monitor.last_reviewed_by = request.user
    monitor.save()
    
    # Mark symptom logs as reviewed
    PatientSymptomLog.objects.filter(
        patient=patient,
        reviewed_by_doctor=False
    ).update(
        reviewed_by_doctor=True,
        reviewed_at=timezone.now(),
        doctor_response=request.POST.get('response', '')
    )
    
    messages.success(request, 'Intervention recorded and symptoms marked as reviewed.')
    return redirect('clinical_decision_support:symptom_monitoring_patient', patient_id=patient_id)


@login_required
@doctor_required
def symptom_update_status(request, patient_id):
    """Update the monitoring status for a patient"""
    if request.method != 'POST':
        return redirect('clinical_decision_support:symptom_monitoring_patient', patient_id=patient_id)
    
    try:
        patient = User.objects.get(id=patient_id, user_type='patient')
    except User.DoesNotExist:
        messages.error(request, 'Patient not found.')
        return redirect('clinical_decision_support:symptom_monitoring_dashboard')
    
    monitor = DoctorSymptomMonitor.objects.filter(
        patient=patient,
        doctor=request.user
    ).first()
    
    if not monitor:
        messages.error(request, 'No active monitoring found for this patient.')
        return redirect('clinical_decision_support:symptom_monitoring_patient', patient_id=patient_id)
    
    status = request.POST.get('status', 'reviewed')
    monitor.last_reviewed_at = timezone.now()
    monitor.last_reviewed_by = request.user
    monitor.save()
    
    # Mark all unreviewed symptom logs as reviewed
    PatientSymptomLog.objects.filter(
        patient=patient,
        reviewed_by_doctor=False
    ).update(
        reviewed_by_doctor=True,
        reviewed_at=timezone.now()
    )
    
    messages.success(request, 'Patient symptoms marked as reviewed.')
    return redirect('clinical_decision_support:symptom_monitoring_patient', patient_id=patient_id)


# ============================================================================
# API Endpoints for AJAX
# ============================================================================

@login_required
@doctor_required
def api_get_plans_for_patient(request, patient_id):
    """API: Get treatment plans for a patient"""
    plans = PersonalizedTreatmentPlan.objects.filter(
        patient_id=patient_id
    ).values('id', 'plan_name', 'cancer_type', 'cancer_stage', 'status')
    return JsonResponse({'plans': list(plans)})


@login_required
@doctor_required
def api_get_doctors(request):
    """API: Get list of verified doctors"""
    doctors = User.objects.filter(
        user_type='doctor'
    ).exclude(id=request.user.id).values('id', 'username', 'first_name', 'last_name')
    return JsonResponse({'doctors': list(doctors)})


# ============================================================================
# Patient Alerts & Notifications (Doctor Features)
# ============================================================================

from patient_portal.models import PatientAlert

@login_required
@doctor_required
def patient_alerts_dashboard(request):
    """Dashboard for doctors to manage patient alerts"""
    # Get all patients with treatment plans
    patients = User.objects.filter(
        user_type='patient',
        treatment_plans__isnull=False
    ).distinct().order_by('username')
    
    # Filter by patient if specified
    patient_id = request.GET.get('patient')
    selected_patient = None
    alerts = PatientAlert.objects.none()
    
    if patient_id:
        try:
            selected_patient = User.objects.get(id=patient_id, user_type='patient')
            alerts = PatientAlert.objects.filter(
                patient=selected_patient
            ).order_by('-created_at')[:20]
        except User.DoesNotExist:
            pass
    
    # Get recent alerts sent by this doctor (via metadata)
    recent_sent = PatientAlert.objects.filter(
        metadata__sent_by=str(request.user.id)
    ).order_by('-created_at')[:10]
    
    context = {
        'patients': patients,
        'selected_patient': selected_patient,
        'alerts': alerts,
        'recent_sent': recent_sent,
    }
    return render(request, 'clinical_decision_support/patient_alerts_dashboard.html', context)


@login_required
@doctor_required
def send_patient_alert(request):
    """Send an alert/notification to a patient"""
    if request.method != 'POST':
        # Show form for GET request
        patients = User.objects.filter(
            user_type='patient',
            treatment_plans__isnull=False
        ).distinct().order_by('username')
        
        # Pre-select patient if provided
        patient_id = request.GET.get('patient')
        selected_patient = None
        if patient_id:
            try:
                selected_patient = User.objects.get(id=patient_id, user_type='patient')
            except User.DoesNotExist:
                pass
        
        context = {
            'patients': patients,
            'selected_patient': selected_patient,
            'alert_types': PatientAlert.ALERT_TYPE_CHOICES,
        }
        return render(request, 'clinical_decision_support/send_patient_alert.html', context)
    
    # Process POST request
    patient_id = request.POST.get('patient_id')
    alert_type = request.POST.get('alert_type', 'general')
    title = request.POST.get('title', '').strip()
    message = request.POST.get('message', '').strip()
    is_urgent = request.POST.get('is_urgent') == 'on'
    
    if not patient_id or not title or not message:
        messages.error(request, 'Please provide patient, title, and message.')
        return redirect('clinical_decision_support:send_patient_alert')
    
    try:
        patient = User.objects.get(id=patient_id, user_type='patient')
    except User.DoesNotExist:
        messages.error(request, 'Patient not found.')
        return redirect('clinical_decision_support:send_patient_alert')
    
    # Create the alert
    PatientAlert.objects.create(
        patient=patient,
        alert_type=alert_type,
        title=title,
        message=message,
        is_urgent=is_urgent,
        status='sent',
        sent_at=timezone.now(),
        metadata={
            'sent_by': str(request.user.id),
            'sent_by_name': request.user.get_full_name() or request.user.username,
            'type': 'doctor_message'
        }
    )
    
    messages.success(request, f'Alert sent to {patient.get_full_name() or patient.username} successfully.')
    return redirect('clinical_decision_support:patient_alerts_dashboard')


@login_required
@doctor_required
def send_bulk_alerts(request):
    """Send alerts to multiple patients at once"""
    if request.method != 'POST':
        # Show form for GET request
        patients = User.objects.filter(
            user_type='patient',
            treatment_plans__isnull=False
        ).distinct().order_by('username')
        
        context = {
            'patients': patients,
            'alert_types': PatientAlert.ALERT_TYPE_CHOICES,
        }
        return render(request, 'clinical_decision_support/send_bulk_alerts.html', context)
    
    # Process POST request
    patient_ids = request.POST.getlist('patient_ids')
    alert_type = request.POST.get('alert_type', 'general')
    title = request.POST.get('title', '').strip()
    message = request.POST.get('message', '').strip()
    is_urgent = request.POST.get('is_urgent') == 'on'
    
    if not patient_ids or not title or not message:
        messages.error(request, 'Please select patients and provide title and message.')
        return redirect('clinical_decision_support:send_bulk_alerts')
    
    # Get patients
    patients = User.objects.filter(id__in=patient_ids, user_type='patient')
    
    # Create alerts for all patients
    alerts_created = 0
    for patient in patients:
        PatientAlert.objects.create(
            patient=patient,
            alert_type=alert_type,
            title=title,
            message=message,
            is_urgent=is_urgent,
            status='sent',
            sent_at=timezone.now(),
            metadata={
                'sent_by': str(request.user.id),
                'sent_by_name': request.user.get_full_name() or request.user.username,
                'type': 'doctor_bulk_message'
            }
        )
        alerts_created += 1
    
    messages.success(request, f'Alert sent to {alerts_created} patient(s) successfully.')
    return redirect('clinical_decision_support:patient_alerts_dashboard')


@login_required
@doctor_required
def quick_send_alert(request, patient_id):
    """Quick send alert from symptom monitoring page"""
    if request.method != 'POST':
        return redirect('clinical_decision_support:symptom_monitoring_patient', patient_id=patient_id)
    
    try:
        patient = User.objects.get(id=patient_id, user_type='patient')
    except User.DoesNotExist:
        messages.error(request, 'Patient not found.')
        return redirect('clinical_decision_support:symptom_monitoring_dashboard')
    
    alert_type = request.POST.get('alert_type', 'general')
    title = request.POST.get('title', '').strip()
    message = request.POST.get('message', '').strip()
    is_urgent = request.POST.get('is_urgent') == 'on'
    
    if not title or not message:
        messages.error(request, 'Please provide title and message.')
        return redirect('clinical_decision_support:symptom_monitoring_patient', patient_id=patient_id)
    
    # Create the alert
    PatientAlert.objects.create(
        patient=patient,
        alert_type=alert_type,
        title=title,
        message=message,
        is_urgent=is_urgent,
        status='sent',
        sent_at=timezone.now(),
        metadata={
            'sent_by': str(request.user.id),
            'sent_by_name': request.user.get_full_name() or request.user.username,
            'type': 'doctor_quick_message'
        }
    )
    
    messages.success(request, f'Alert sent to {patient.get_full_name() or patient.username} successfully.')
    return redirect('clinical_decision_support:symptom_monitoring_patient', patient_id=patient_id)
