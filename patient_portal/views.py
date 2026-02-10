"""
Patient Portal Views
Patient-side views for treatment info, symptoms, and side effects
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q, Avg
from datetime import date, timedelta
import json
import os

from .models import (
    PatientSymptomLog, PatientTreatmentExplanation,
    PatientSideEffectInfo, PatientAlert, PatientNotificationPreference,
    UserBadge
)
from .gamification_service import GamificationService
from .telegram_service import TelegramBotService
from clinical_decision_support.models import AIConfidenceMetadata, ToxicityPrediction
from cancer_detection.models import PersonalizedTreatmentPlan


def patient_required(view_func):
    """Decorator to ensure only patients can access the view"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if request.user.user_type != 'patient':
            messages.error(request, 'This feature is only available to patients.')
            return redirect('doctor_dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def generate_plain_language_explanation(plan):
    """Generate a plain-language explanation of the treatment plan using Groq AI"""
    try:
        from groq import Groq
        client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        
        # Build context from treatment plan
        treatments = plan.primary_treatments or []
        targeted = plan.targeted_therapies or []
        adjuvant = plan.adjuvant_treatments or []
        
        treatment_list = ", ".join([t.get('name', str(t)) if isinstance(t, dict) else str(t) for t in treatments])
        targeted_list = ", ".join([t.get('drug', str(t)) if isinstance(t, dict) else str(t) for t in targeted])
        
        prompt = f"""You are a compassionate healthcare educator. Explain this cancer treatment plan in simple, 
reassuring language for a patient. Avoid medical jargon and be encouraging.

Cancer Type: {plan.cancer_type}
Stage: {plan.cancer_stage}
Primary Treatments: {treatment_list or 'Not specified'}
Targeted Therapies: {targeted_list or 'None'}
Adjuvant Treatments: {adjuvant or 'None'}

Provide:
1. A brief, easy-to-understand overview (2-3 sentences)
2. What each treatment does in simple terms
3. What the patient can expect during treatment
4. Words of encouragement

Keep it under 300 words and use a warm, supportive tone."""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content
    except Exception as e:
        # Fallback to basic explanation
        return None


def generate_side_effects_info(plan):
    """Generate patient-friendly side effects information using Groq AI"""
    try:
        from groq import Groq
        client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        
        side_effects = plan.side_effects or []
        treatments = plan.primary_treatments or []
        
        treatment_names = ", ".join([t.get('name', str(t)) if isinstance(t, dict) else str(t) for t in treatments])
        side_effects_list = ", ".join([s.get('effect', str(s)) if isinstance(s, dict) else str(s) for s in side_effects])
        
        prompt = f"""You are a patient educator. Create a helpful guide about potential side effects for this cancer treatment.

Treatments: {treatment_names or 'Standard cancer treatment'}
Known Side Effects: {side_effects_list or 'Common cancer treatment side effects'}

Provide a JSON response with this exact structure:
{{
    "overview": "Brief reassuring intro (1-2 sentences)",
    "side_effects": [
        {{
            "name": "Side effect name",
            "severity": "low|moderate|high",
            "description": "What this feels like",
            "management": "How to manage at home",
            "when_to_call": "When to contact doctor"
        }}
    ],
    "general_tips": ["Tip 1", "Tip 2", "Tip 3"]
}}

Include 4-6 common side effects. Be practical and reassuring."""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=800
        )
        
        content = response.choices[0].message.content
        # Try to parse JSON from response
        import re
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            return json.loads(json_match.group())
        return None
    except Exception as e:
        return None


# ============================================================================
# Patient Confidence View (Simplified)
# ============================================================================

@login_required
@patient_required
def patient_confidence_view(request):
    """Simplified confidence view for patients - uses treatment plan data directly"""
    # Get treatment plans for this patient
    plans = PersonalizedTreatmentPlan.objects.filter(
        patient=request.user
    ).order_by('-created_at')
    
    # Get confidence records if they exist
    confidence_records = AIConfidenceMetadata.objects.filter(
        patient=request.user
    ).order_by('-created_at')
    
    # Build simplified records from treatment plans if no confidence data
    simplified_records = []
    
    if confidence_records.exists():
        for record in confidence_records:
            simplified_records.append({
                'id': record.id,
                'analysis_type': record.get_analysis_type_display(),
                'confidence_level': record.confidence_level,
                'confidence_label': dict(AIConfidenceMetadata.CONFIDENCE_LEVEL_CHOICES).get(
                    record.confidence_level, 'Unknown'
                ),
                'patient_explanation': record.patient_explanation,
                'created_at': record.created_at,
            })
    else:
        # Generate confidence info from treatment plans
        for plan in plans:
            # Use survival probability and remission rate as confidence indicators
            survival = plan.predicted_5yr_survival or 0
            remission = plan.remission_probability or 0
            
            if survival >= 70 or remission >= 70:
                confidence_level = 'high'
                confidence_label = 'High Confidence'
            elif survival >= 50 or remission >= 50:
                confidence_level = 'medium'
                confidence_label = 'Moderate Confidence'
            else:
                confidence_level = 'low'
                confidence_label = 'Needs Discussion'
            
            simplified_records.append({
                'id': plan.id,
                'analysis_type': f'{plan.cancer_type} Treatment Plan',
                'confidence_level': confidence_level,
                'confidence_label': confidence_label,
                'patient_explanation': f'Your treatment plan for {plan.cancer_type} Stage {plan.cancer_stage} has been analyzed. '
                    f'Based on your profile, the predicted outcomes are: 5-year survival estimate of {survival:.0f}% '
                    f'and remission probability of {remission:.0f}%. Your medical team is here to support you every step of the way.',
                'created_at': plan.created_at,
                'plan': plan,
            })
    
    context = {
        'records': simplified_records,
        'plans': plans,
    }
    return render(request, 'patient_portal/confidence_view.html', context)


# ============================================================================
# Patient Treatment Explanation
# ============================================================================

@login_required
@patient_required
def treatment_explanation_list(request):
    """List patient treatment explanations - fetches directly from treatment plans"""
    # Get all treatment plans for this patient
    plans = PersonalizedTreatmentPlan.objects.filter(
        patient=request.user
    ).order_by('-created_at')
    
    # Check for existing explanations
    existing_explanations = PatientTreatmentExplanation.objects.filter(
        patient=request.user
    ).select_related('treatment_plan')
    
    explanation_map = {exp.treatment_plan_id: exp for exp in existing_explanations}
    
    # Build explanation list from treatment plans
    explanations = []
    for plan in plans:
        if plan.id in explanation_map:
            explanations.append({
                'plan': plan,
                'explanation': explanation_map[plan.id],
                'has_stored': True
            })
        else:
            # Generate explanation on-the-fly from plan data
            treatments = plan.primary_treatments or []
            targeted = plan.targeted_therapies or []
            
            # Build basic explanation from plan data
            treatment_names = [t.get('name', str(t)) if isinstance(t, dict) else str(t) for t in treatments]
            
            explanations.append({
                'plan': plan,
                'explanation': {
                    'overview': f"Your treatment plan for {plan.cancer_type} Stage {plan.cancer_stage}",
                    'treatments': treatment_names,
                    'targeted': [t.get('drug', str(t)) if isinstance(t, dict) else str(t) for t in targeted],
                },
                'has_stored': False
            })
    
    context = {
        'explanations': explanations,
        'plans': plans,
    }
    return render(request, 'patient_portal/treatment_explanation_list.html', context)


@login_required
@patient_required
def treatment_explanation_detail(request, explanation_id):
    """Detailed treatment explanation view - can be plan ID or explanation ID"""
    # Try to find by explanation ID first
    explanation = PatientTreatmentExplanation.objects.filter(
        id=explanation_id,
        patient=request.user
    ).select_related('treatment_plan').first()
    
    if explanation:
        plan = explanation.treatment_plan
        ai_explanation = explanation.treatment_summary
    else:
        # Try to find by plan ID and generate explanation
        plan = get_object_or_404(
            PersonalizedTreatmentPlan,
            id=explanation_id,
            patient=request.user
        )
        
        # Generate AI explanation
        ai_explanation = generate_plain_language_explanation(plan)
        
        # Save it for future use
        if ai_explanation:
            # Build treatment steps from plan data
            treatments = plan.primary_treatments or []
            treatment_steps = []
            for i, t in enumerate(treatments):
                if isinstance(t, dict):
                    treatment_steps.append({
                        'step': i + 1,
                        'title': t.get('name', f'Treatment {i+1}'),
                        'description': t.get('description', ''),
                        'duration': t.get('duration', '')
                    })
            
            explanation = PatientTreatmentExplanation.objects.create(
                patient=request.user,
                treatment_plan=plan,
                treatment_summary=ai_explanation,
                why_this_treatment=f"Based on your {plan.cancer_type} diagnosis at stage {plan.cancer_stage}, this personalized treatment plan was created.",
                expected_benefits=["Target and shrink the tumor", "Prevent further spread", "Improve quality of life"],
                treatment_steps=treatment_steps,
                estimated_duration=plan.monitoring_plan.get('total_duration', '') if isinstance(plan.monitoring_plan, dict) else '',
                key_milestones=plan.expected_milestones or [],
            )
    
    # Extract key info from plan
    treatments = plan.primary_treatments or []
    targeted = plan.targeted_therapies or []
    adjuvant = plan.adjuvant_treatments or []
    monitoring = plan.monitoring_plan or {}
    milestones = plan.expected_milestones or []
    
    context = {
        'plan': plan,
        'explanation': explanation,
        'ai_explanation': ai_explanation,
        'treatments': treatments,
        'targeted_therapies': targeted,
        'adjuvant_treatments': adjuvant,
        'monitoring_plan': monitoring,
        'milestones': milestones,
        'survival_rate': plan.predicted_5yr_survival,
        'remission_rate': plan.remission_probability,
        'qol_score': plan.quality_of_life_score,
    }
    return render(request, 'patient_portal/treatment_explanation_detail.html', context)


# ============================================================================
# Patient Side Effects View
# ============================================================================

@login_required
@patient_required
def side_effects_list(request):
    """List side effect information - fetches from treatment plans"""
    # Get all treatment plans
    plans = PersonalizedTreatmentPlan.objects.filter(
        patient=request.user
    ).order_by('-created_at')
    
    # Get existing side effect info
    existing_info = PatientSideEffectInfo.objects.filter(
        patient=request.user
    ).select_related('treatment_plan')
    
    info_map = {info.treatment_plan_id: info for info in existing_info}
    
    # Build side effects list
    side_effects_list = []
    for plan in plans:
        plan_side_effects = plan.side_effects or []
        
        if plan.id in info_map:
            side_effects_list.append({
                'plan': plan,
                'info': info_map[plan.id],
                'side_effects': plan_side_effects,
                'has_stored': True
            })
        else:
            side_effects_list.append({
                'plan': plan,
                'side_effects': plan_side_effects,
                'has_stored': False
            })
    
    context = {
        'side_effects_list': side_effects_list,
        'plans': plans,
    }
    return render(request, 'patient_portal/side_effects_list.html', context)


@login_required
@patient_required
def side_effects_detail(request, info_id):
    """Detailed side effects information - can be plan ID or info ID"""
    # Try to find by info ID first
    info = PatientSideEffectInfo.objects.filter(
        id=info_id,
        patient=request.user
    ).select_related('treatment_plan').first()
    
    if info:
        plan = info.treatment_plan
        ai_info = {
            'overview': f"Side effects information for {info.treatment_name}",
            'side_effects': info.common_side_effects,
            'general_tips': info.self_care_tips,
            'when_to_call_doctor': info.when_to_contact_doctor,
        }
    else:
        # Try to find by plan ID
        plan = get_object_or_404(
            PersonalizedTreatmentPlan,
            id=info_id,
            patient=request.user
        )
        
        # Generate AI side effects info
        ai_info = generate_side_effects_info(plan)
        
        # Get treatment name from plan
        treatments = plan.primary_treatments or []
        treatment_name = plan.cancer_type + " Treatment"
        if treatments and len(treatments) > 0:
            first_treatment = treatments[0]
            if isinstance(first_treatment, dict):
                treatment_name = first_treatment.get('name', treatment_name)
            else:
                treatment_name = str(first_treatment)
        
        # Save for future use
        if ai_info:
            info = PatientSideEffectInfo.objects.create(
                patient=request.user,
                treatment_plan=plan,
                treatment_name=treatment_name,
                common_side_effects=ai_info.get('side_effects', []),
                self_care_tips=ai_info.get('general_tips', []),
                when_to_contact_doctor=['Fever over 100.4°F (38°C)', 'Severe pain', 'Difficulty breathing', 
                                         'Unusual bleeding', 'Severe nausea/vomiting that doesn\'t stop'],
                what_is_normal=['Mild fatigue for a few days', 'Some nausea after treatment', 'Temporary hair thinning'],
                emergency_signs=['High fever with chills', 'Chest pain', 'Sudden severe headache', 'Difficulty breathing'],
            )
    
    # Get side effects from plan
    plan_side_effects = plan.side_effects or []
    treatments = plan.primary_treatments or []
    
    context = {
        'plan': plan,
        'info': info,
        'ai_info': ai_info,
        'plan_side_effects': plan_side_effects,
        'treatments': treatments,
    }
    return render(request, 'patient_portal/side_effects_detail.html', context)


# ============================================================================
# Symptom Logging
# ============================================================================

@login_required
@patient_required
def symptom_log_list(request):
    """List patient's symptom logs"""
    logs = PatientSymptomLog.objects.filter(
        patient=request.user
    ).order_by('-log_date')
    
    # Apply period filter if requested
    period = request.GET.get('period')
    if period:
        days_ago = timezone.now() - timezone.timedelta(days=int(period))
        logs = logs.filter(log_date__gte=days_ago.date())
    
    # Calculate statistics
    avg_wellness = logs.aggregate(Avg('overall_wellbeing'))['overall_wellbeing__avg'] or 0
    avg_pain = logs.aggregate(Avg('pain'))['pain__avg'] or 0
    days_logged = logs.count()
    
    paginator = Paginator(logs, 10)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)
    
    # Check if logged today
    today = date.today()
    logged_today = logs.filter(log_date=today).exists()
    
    context = {
        'page_obj': page_obj,
        'logs': page_obj.object_list,
        'logged_today': logged_today,
        'today': today,
        'avg_wellness': avg_wellness,
        'avg_pain': avg_pain,
        'days_logged': days_logged,
    }
    return render(request, 'patient_portal/symptom_log_list.html', context)


@login_required
@patient_required
def symptom_log_create(request):
    """Create a new symptom log"""
    today = date.today()
    
    # Check if already logged today
    if PatientSymptomLog.objects.filter(patient=request.user, log_date=today).exists():
        messages.warning(request, 'You have already logged symptoms for today.')
        return redirect('patient_portal:symptom_log_list')
    
    if request.method == 'POST':
        # Get treatment plan if any
        plan = PersonalizedTreatmentPlan.objects.filter(
            patient=request.user,
            status='active'
        ).first()
        
        # Create symptom log
        log = PatientSymptomLog(
            patient=request.user,
            treatment_plan=plan,
            log_date=today,
            log_type=request.POST.get('log_type', 'daily'),
        )
        
        # Symptom fields
        symptom_fields = [
            'fatigue', 'pain', 'nausea', 'vomiting', 'appetite_loss',
            'sleep_problems', 'shortness_of_breath', 'diarrhea', 'constipation',
            'mouth_sores', 'skin_changes', 'numbness_tingling', 'anxiety',
            'depression', 'confusion', 'overall_wellbeing'
        ]
        
        for field in symptom_fields:
            value = request.POST.get(field)
            if value:
                try:
                    setattr(log, field, int(value))
                except ValueError:
                    pass
        
        # Other fields
        log.pain_location = request.POST.get('pain_location', '')
        log.weight_change = request.POST.get('weight_change', '')
        log.fever = request.POST.get('fever') == 'on'
        if log.fever:
            temp = request.POST.get('fever_temperature')
            if temp:
                try:
                    log.fever_temperature = float(temp)
                except ValueError:
                    pass
        
        log.hair_loss = request.POST.get('hair_loss')
        log.activity_level = request.POST.get('activity_level')
        log.additional_symptoms = request.POST.get('additional_symptoms', '')
        log.notes = request.POST.get('notes', '')
        
        log.save()
        
        # Check for severe symptoms and create alert
        severe = log.get_severe_symptoms()
        if severe:
            PatientAlert.objects.create(
                patient=request.user,
                alert_type='general',
                title='Severe Symptoms Reported',
                message=f'You reported severe symptoms: {", ".join([s["symptom"] for s in severe])}. Your healthcare team will review this.',
                is_urgent=True
            )
        
        # Check for badges and level ups (signals will handle this, but we can also check here for immediate response)
        activity_data = {'id': str(log.id), 'log_date': log.log_date.isoformat()}
        newly_earned_badges = GamificationService.check_and_award_badges(
            request.user,
            activity_type='symptom_logged',
            activity_data=activity_data
        )
        level_info = GamificationService.check_level_up(request.user)
        
        messages.success(request, 'Your symptoms have been logged successfully.')
        
        # If badges were earned, store them in session for pop-up display
        if newly_earned_badges or level_info.get('leveled_up'):
            request.session['newly_earned_badges'] = newly_earned_badges
            request.session['level_up'] = level_info if level_info.get('leveled_up') else None
        
        return redirect('patient_portal:symptom_log_list')
    
    context = {
        'today': today,
        'severity_choices': PatientSymptomLog.SEVERITY_CHOICES,
    }
    return render(request, 'patient_portal/symptom_log_create.html', context)


@login_required
@patient_required
def symptom_log_detail(request, log_id):
    """View symptom log details"""
    log = get_object_or_404(
        PatientSymptomLog,
        id=log_id,
        patient=request.user
    )
    
    context = {
        'log': log,
    }
    return render(request, 'patient_portal/symptom_log_detail.html', context)


# ============================================================================
# Patient Alerts & Reminders
# ============================================================================

def auto_generate_treatment_alerts(patient):
    """Auto-generate alerts based on patient's treatment plans"""
    from datetime import datetime
    
    # Get active treatment plans
    plans = PersonalizedTreatmentPlan.objects.filter(
        patient=patient,
        status='active'
    )
    
    alerts_created = []
    
    for plan in plans:
        # Check if we've already created initial alerts for this plan
        existing_alerts = PatientAlert.objects.filter(
            patient=patient,
            metadata__plan_id=str(plan.id)
        ).exists()
        
        if existing_alerts:
            continue
        
        # 1. Welcome alert for new treatment plan
        PatientAlert.objects.create(
            patient=patient,
            alert_type='general',
            title=f'Treatment Plan Ready: {plan.cancer_type}',
            message=f'Your personalized treatment plan for {plan.cancer_type} (Stage {plan.cancer_stage}) has been created and approved. Please review your treatment details and side effects information.',
            is_urgent=False,
            metadata={'plan_id': str(plan.id), 'type': 'welcome'}
        )
        alerts_created.append('welcome')
        
        # 2. Symptom logging reminder
        PatientAlert.objects.create(
            patient=patient,
            alert_type='symptom_reminder',
            title='Daily Symptom Logging',
            message='Remember to log your symptoms daily. This helps your healthcare team monitor your progress and adjust your treatment if needed.',
            is_urgent=False,
            scheduled_for=timezone.now() + timedelta(hours=1),
            metadata={'plan_id': str(plan.id), 'type': 'symptom_reminder'}
        )
        alerts_created.append('symptom_reminder')
        
        # 3. Treatment information reminder
        PatientAlert.objects.create(
            patient=patient,
            alert_type='general',
            title='Learn About Your Treatment',
            message='Take some time to read about your treatment plan and potential side effects. Understanding your treatment can help you feel more prepared and confident.',
            is_urgent=False,
            metadata={'plan_id': str(plan.id), 'type': 'education'}
        )
        alerts_created.append('education')
        
        # 4. Generate medication reminders from treatment plan
        treatments = plan.primary_treatments or []
        for i, treatment in enumerate(treatments):
            if isinstance(treatment, dict):
                treatment_name = treatment.get('name', f'Treatment {i+1}')
                schedule = treatment.get('schedule', 'As directed by your doctor')
            else:
                treatment_name = str(treatment)
                schedule = 'As directed by your doctor'
            
            PatientAlert.objects.create(
                patient=patient,
                alert_type='medication',
                title=f'Treatment: {treatment_name}',
                message=f'Schedule: {schedule}. Please follow your healthcare provider\'s instructions for this treatment.',
                is_urgent=False,
                metadata={'plan_id': str(plan.id), 'type': 'treatment_info', 'treatment': treatment_name}
            )
            alerts_created.append(f'treatment_{i}')
        
        # 5. Side effects awareness
        side_effects = plan.side_effects or []
        if side_effects:
            effects_list = []
            for se in side_effects[:5]:  # Top 5 side effects
                if isinstance(se, dict):
                    effects_list.append(se.get('effect', str(se)))
                else:
                    effects_list.append(str(se))
            
            PatientAlert.objects.create(
                patient=patient,
                alert_type='general',
                title='Potential Side Effects',
                message=f'Be aware of these potential side effects: {", ".join(effects_list)}. Visit the Side Effects section for management tips and when to contact your doctor.',
                is_urgent=False,
                metadata={'plan_id': str(plan.id), 'type': 'side_effects'}
            )
            alerts_created.append('side_effects')
        
        # 6. Weekly check-in reminder (scheduled for next week)
        PatientAlert.objects.create(
            patient=patient,
            alert_type='symptom_reminder',
            title='Weekly Health Check-In',
            message='It\'s time for your weekly health check-in. How are you feeling? Log your symptoms and let us know if you have any concerns.',
            is_urgent=False,
            scheduled_for=timezone.now() + timedelta(days=7),
            metadata={'plan_id': str(plan.id), 'type': 'weekly_checkin'}
        )
        alerts_created.append('weekly_checkin')
        
        # 7. Reassurance message
        PatientAlert.objects.create(
            patient=patient,
            alert_type='reassurance',
            title='You\'re Not Alone',
            message='Remember, your healthcare team is here to support you every step of the way. Don\'t hesitate to reach out with any questions or concerns.',
            is_urgent=False,
            metadata={'plan_id': str(plan.id), 'type': 'reassurance'}
        )
        alerts_created.append('reassurance')
    
    return alerts_created


@login_required
@patient_required
def alerts_list(request):
    """List patient alerts"""
    # Auto-generate alerts from treatment plans if none exist
    existing_count = PatientAlert.objects.filter(patient=request.user).count()
    if existing_count == 0:
        auto_generate_treatment_alerts(request.user)
    
    alerts = PatientAlert.objects.filter(
        patient=request.user
    ).order_by('-created_at')
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        alerts = alerts.filter(status=status)
    
    # Filter unread
    unread_only = request.GET.get('unread')
    if unread_only:
        alerts = alerts.exclude(status='read')
    
    paginator = Paginator(alerts, 15)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)
    
    # Count unread
    unread_count = PatientAlert.objects.filter(
        patient=request.user
    ).exclude(status='read').count()
    
    context = {
        'page_obj': page_obj,
        'alerts': page_obj,  # For template compatibility
        'unread_count': unread_count,
        'selected_status': status,
        'unread_only': unread_only,
    }
    return render(request, 'patient_portal/alerts_list.html', context)


@login_required
@patient_required
@require_POST
def mark_alert_read(request, alert_id):
    """Mark an alert as read"""
    alert = get_object_or_404(PatientAlert, id=alert_id, patient=request.user)
    alert.mark_as_read()
    return JsonResponse({'success': True})


@login_required
@patient_required
@require_POST
def mark_all_alerts_read(request):
    """Mark all alerts as read"""
    PatientAlert.objects.filter(
        patient=request.user
    ).exclude(status='read').update(
        status='read',
        read_at=timezone.now()
    )
    
    # Check if it's an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': True, 'message': 'All alerts marked as read.'})
    
    messages.success(request, 'All alerts marked as read.')
    return redirect('patient_portal:alerts_list')


# ============================================================================
# Notification Preferences
# ============================================================================

@login_required
@patient_required
def notification_preferences(request):
    """Manage notification preferences"""
    prefs, created = PatientNotificationPreference.objects.get_or_create(
        patient=request.user
    )
    
    # Get patient profile for Telegram settings
    try:
        from authentication.models import PatientProfile
        patient_profile = PatientProfile.objects.get(user=request.user)
    except PatientProfile.DoesNotExist:
        patient_profile = None
    
    if request.method == 'POST':
        prefs.enable_in_app = request.POST.get('enable_in_app') == 'on'
        prefs.enable_sms = request.POST.get('enable_sms') == 'on'
        prefs.enable_whatsapp = request.POST.get('enable_whatsapp') == 'on'
        prefs.enable_email = request.POST.get('enable_email') == 'on'
        prefs.phone_number = request.POST.get('phone_number', '')
        prefs.whatsapp_number = request.POST.get('whatsapp_number', '')
        prefs.symptom_reminder_frequency = request.POST.get('symptom_reminder_frequency', 'daily')
        
        # Handle Telegram notification toggle
        if patient_profile and patient_profile.telegram_chat_id:
            patient_profile.telegram_notifications_enabled = request.POST.get('enable_telegram') == 'on'
            patient_profile.save()
        
        time_str = request.POST.get('reminder_time')
        if time_str:
            from datetime import datetime
            try:
                prefs.reminder_time = datetime.strptime(time_str, '%H:%M').time()
            except ValueError:
                pass
        
        prefs.save()
        messages.success(request, 'Notification preferences updated.')
        return redirect('patient_portal:notification_preferences')
    
    context = {
        'prefs': prefs,
        'patient_profile': patient_profile,
        'telegram_linked': patient_profile.telegram_chat_id if patient_profile else False,
    }
    return render(request, 'patient_portal/notification_preferences.html', context)


# ============================================================================
# Patient Dashboard Widget Data
# ============================================================================

@login_required
@patient_required
def patient_overview(request):
    """Patient portal overview/dashboard"""
    # Get counts for quick stats
    active_plans_count = PersonalizedTreatmentPlan.objects.filter(
        patient=request.user,
        status='active'
    ).count()
    
    symptom_logs_count = PatientSymptomLog.objects.filter(
        patient=request.user
    ).count()
    
    unread_alerts_count = PatientAlert.objects.filter(
        patient=request.user
    ).exclude(status='read').count()
    
    # Get upcoming reminders (next 7 days) - using scheduled alerts
    from datetime import timedelta
    upcoming_cutoff = timezone.now() + timedelta(days=7)
    upcoming_reminders = PatientAlert.objects.filter(
        patient=request.user,
        scheduled_for__gte=timezone.now(),
        scheduled_for__lte=upcoming_cutoff,
        status='pending'
    ).order_by('scheduled_for')[:5]
    
    upcoming_reminders_count = upcoming_reminders.count()
    
    # Get recent symptom logs
    recent_logs = PatientSymptomLog.objects.filter(
        patient=request.user
    ).order_by('-log_date')[:7]
    
    # Get recent alerts
    recent_alerts = PatientAlert.objects.filter(
        patient=request.user
    ).exclude(status='read').order_by('-created_at')[:5]
    
    # Get treatment explanations from treatment plans
    plans = PersonalizedTreatmentPlan.objects.filter(
        patient=request.user,
        status='active'
    ).order_by('-created_at')[:4]
    
    treatment_explanations = []
    for plan in plans:
        # Check for existing stored explanation
        stored_exp = PatientTreatmentExplanation.objects.filter(
            treatment_plan=plan
        ).first()
        
        if stored_exp:
            treatment_explanations.append(stored_exp)
        else:
            # Create a simple explanation object for display
            class SimpleExplanation:
                def __init__(self, plan):
                    self.id = plan.id
                    self.treatment_plan = plan
                    treatments = plan.primary_treatments or []
                    treatment_names = [t.get('name', str(t)) if isinstance(t, dict) else str(t) for t in treatments[:2]]
                    self.simple_summary = f"Your personalized treatment plan includes {', '.join(treatment_names) if treatment_names else 'comprehensive care'}. Click to learn more about your treatment in simple terms."
            
            treatment_explanations.append(SimpleExplanation(plan))
    
    # Check if logged today
    today = date.today()
    logged_today = PatientSymptomLog.objects.filter(
        patient=request.user,
        log_date=today
    ).exists()
    
    context = {
        'active_plans_count': active_plans_count,
        'symptom_logs_count': symptom_logs_count,
        'unread_alerts_count': unread_alerts_count,
        'upcoming_reminders_count': upcoming_reminders_count,
        'recent_logs': recent_logs,
        'recent_alerts': recent_alerts,
        'upcoming_reminders': upcoming_reminders,
        'treatment_explanations': treatment_explanations,
        'logged_today': logged_today,
    }
    return render(request, 'patient_portal/overview.html', context)


# ============================================================================
# API for AJAX calls
# ============================================================================

@login_required
@patient_required
def api_unread_alerts_count(request):
    """Get unread alerts count"""
    count = PatientAlert.objects.filter(
        patient=request.user
    ).exclude(status='read').count()
    return JsonResponse({'count': count})


@login_required
@patient_required
def api_symptom_trend(request):
    """Get symptom trend data for charts"""
    days = int(request.GET.get('days', 14))
    logs = PatientSymptomLog.objects.filter(
        patient=request.user,
        log_date__gte=date.today() - timedelta(days=days)
    ).order_by('log_date')
    
    data = []
    for log in logs:
        data.append({
            'date': log.log_date.isoformat(),
            'wellbeing': log.overall_wellbeing,
            'fatigue': log.fatigue,
            'pain': log.pain,
            'nausea': log.nausea,
        })
    
    return JsonResponse({'data': data})


@login_required
@patient_required
def api_check_new_badges(request):
    """API endpoint to check for newly earned badges"""
    # Check session for badges earned in current request
    newly_earned_badges = request.session.pop('newly_earned_badges', [])
    level_up = request.session.pop('level_up', None)
    
    # Also check for any badges earned in the last minute (in case of async processing)
    from datetime import timedelta
    recent_badges = UserBadge.objects.filter(
        user=request.user,
        earned_at__gte=timezone.now() - timedelta(minutes=1),
        notification_sent=False
    ).select_related('badge').order_by('-earned_at')
    
    # Mark as sent and add to response
    for user_badge in recent_badges:
        if str(user_badge.badge.id) not in [b['id'] for b in newly_earned_badges]:
            newly_earned_badges.append({
                'id': str(user_badge.badge.id),
                'name': user_badge.badge.name,
                'description': user_badge.badge.description,
                'category': user_badge.badge.category,
                'rarity': user_badge.badge.rarity,
                'points_reward': user_badge.badge.points_reward,
                'icon_url': user_badge.badge.icon_url,
                'icon_name': user_badge.badge.icon_name,
            })
        user_badge.notification_sent = True
        user_badge.save()
    
    return JsonResponse({
        'badges': newly_earned_badges,
        'level_up': level_up,
        'has_new': len(newly_earned_badges) > 0 or (level_up and level_up.get('leveled_up'))
    })


@login_required
@patient_required
def api_user_stats(request):
    """Get user gamification stats"""
    stats = GamificationService.get_user_stats(request.user)
    return JsonResponse(stats)
