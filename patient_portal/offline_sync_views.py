"""
Offline Sync Views for Patient Portal
Handles synchronization of offline operations when connection is restored.
"""

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.utils import timezone
from django.db import transaction
import json
from datetime import datetime

from .models import (
    OfflineSyncQueue, OfflineDataCache,
    PatientSymptomLog, PatientAlert, PatientNotificationPreference
)
from .views import patient_required
from cancer_detection.models import PersonalizedTreatmentPlan


@login_required
@patient_required
@require_http_methods(['GET', 'POST'])
def sync_status(request):
    """Get sync status and pending operations count"""
    pending_count = OfflineSyncQueue.objects.filter(
        patient=request.user,
        status__in=['pending', 'failed']
    ).count()
    
    syncing_count = OfflineSyncQueue.objects.filter(
        patient=request.user,
        status='syncing'
    ).count()
    
    # Get last sync time
    cache, _ = OfflineDataCache.objects.get_or_create(patient=request.user)
    last_synced = cache.last_synced_at.isoformat() if cache.last_synced_at else None
    
    return JsonResponse({
        'pending_count': pending_count,
        'syncing_count': syncing_count,
        'last_synced': last_synced,
        'is_online': True,  # If this endpoint is reachable, we're online
    })


@login_required
@patient_required
@require_POST
def sync_operations(request):
    """
    Sync pending offline operations.
    Accepts batch of operations from client and processes them.
    """
    try:
        data = json.loads(request.body)
        operations = data.get('operations', [])
        client_sync_id = data.get('sync_id', None)
        
        results = {
            'synced': [],
            'failed': [],
            'conflicts': []
        }
        
        for op in operations:
            operation_id = op.get('id')
            operation_type = op.get('type')
            operation_data = op.get('data', {})
            client_timestamp = op.get('timestamp')
            
            try:
                # Parse client timestamp
                if client_timestamp:
                    client_ts = datetime.fromisoformat(client_timestamp.replace('Z', '+00:00'))
                else:
                    client_ts = timezone.now()
                
                # Process based on operation type
                if operation_type == 'symptom_log':
                    result = _sync_symptom_log(request.user, operation_data, client_ts)
                elif operation_type == 'alert_read':
                    result = _sync_alert_read(request.user, operation_data)
                elif operation_type == 'alert_read_all':
                    result = _sync_alert_read_all(request.user)
                elif operation_type == 'notification_preference':
                    result = _sync_notification_preference(request.user, operation_data)
                else:
                    result = {'success': False, 'error': f'Unknown operation type: {operation_type}'}
                
                if result.get('success'):
                    results['synced'].append({
                        'id': operation_id,
                        'server_id': result.get('server_id')
                    })
                elif result.get('conflict'):
                    results['conflicts'].append({
                        'id': operation_id,
                        'error': result.get('error', 'Conflict detected')
                    })
                else:
                    results['failed'].append({
                        'id': operation_id,
                        'error': result.get('error', 'Unknown error')
                    })
                    
            except Exception as e:
                results['failed'].append({
                    'id': operation_id,
                    'error': str(e)
                })
        
        return JsonResponse({
            'success': True,
            'results': results,
            'sync_id': client_sync_id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


def _sync_symptom_log(patient, data, client_timestamp):
    """Sync a symptom log created offline"""
    try:
        with transaction.atomic():
            # Check if log already exists for this date
            log_date = datetime.fromisoformat(data['log_date']).date()
            existing = PatientSymptomLog.objects.filter(
                patient=patient,
                log_date=log_date
            ).first()
            
            if existing:
                # Conflict: log already exists for this date
                return {
                    'success': False,
                    'conflict': True,
                    'error': 'Symptom log already exists for this date',
                    'server_id': str(existing.id)
                }
            
            # Get treatment plan if specified
            treatment_plan = None
            if data.get('treatment_plan_id'):
                try:
                    treatment_plan = PersonalizedTreatmentPlan.objects.get(
                        id=data['treatment_plan_id'],
                        patient=patient
                    )
                except PersonalizedTreatmentPlan.DoesNotExist:
                    pass
            
            # Create symptom log
            log = PatientSymptomLog(
                patient=patient,
                treatment_plan=treatment_plan,
                log_date=log_date,
                log_type=data.get('log_type', 'daily'),
            )
            
            # Set symptom fields
            symptom_fields = [
                'fatigue', 'pain', 'nausea', 'vomiting', 'appetite_loss',
                'sleep_problems', 'shortness_of_breath', 'diarrhea', 'constipation',
                'mouth_sores', 'skin_changes', 'numbness_tingling', 'anxiety',
                'depression', 'confusion', 'overall_wellbeing'
            ]
            
            for field in symptom_fields:
                if field in data:
                    setattr(log, field, data[field])
            
            # Other fields
            if 'pain_location' in data:
                log.pain_location = data['pain_location']
            if 'weight_change' in data:
                log.weight_change = data['weight_change']
            if 'fever' in data:
                log.fever = data['fever']
            if 'fever_temperature' in data:
                log.fever_temperature = data['fever_temperature']
            if 'hair_loss' in data:
                log.hair_loss = data['hair_loss']
            if 'activity_level' in data:
                log.activity_level = data['activity_level']
            if 'additional_symptoms' in data:
                log.additional_symptoms = data['additional_symptoms']
            if 'notes' in data:
                log.notes = data['notes']
            
            log.save()
            
            # Check for severe symptoms and create alert
            from .views import auto_generate_treatment_alerts
            severe = log.get_severe_symptoms()
            if severe:
                from .models import PatientAlert
                PatientAlert.objects.create(
                    patient=patient,
                    alert_type='general',
                    title='Severe Symptoms Reported',
                    message=f'You reported severe symptoms: {", ".join([s["symptom"] for s in severe])}. Your healthcare team will review this.',
                    is_urgent=True
                )
            
            return {
                'success': True,
                'server_id': str(log.id)
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def _sync_alert_read(patient, data):
    """Sync marking an alert as read"""
    try:
        alert_id = data.get('alert_id')
        if not alert_id:
            return {'success': False, 'error': 'alert_id required'}
        
        alert = get_object_or_404(PatientAlert, id=alert_id, patient=patient)
        alert.mark_as_read()
        
        return {
            'success': True,
            'server_id': str(alert.id)
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def _sync_alert_read_all(patient):
    """Sync marking all alerts as read"""
    try:
        from django.utils import timezone
        PatientAlert.objects.filter(
            patient=patient
        ).exclude(status='read').update(
            status='read',
            read_at=timezone.now()
        )
        
        return {
            'success': True
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def _sync_notification_preference(patient, data):
    """Sync notification preference updates"""
    try:
        prefs, created = PatientNotificationPreference.objects.get_or_create(
            patient=patient
        )
        
        if 'enable_in_app' in data:
            prefs.enable_in_app = data['enable_in_app']
        if 'enable_sms' in data:
            prefs.enable_sms = data['enable_sms']
        if 'enable_whatsapp' in data:
            prefs.enable_whatsapp = data['enable_whatsapp']
        if 'enable_email' in data:
            prefs.enable_email = data['enable_email']
        if 'phone_number' in data:
            prefs.phone_number = data['phone_number']
        if 'whatsapp_number' in data:
            prefs.whatsapp_number = data['whatsapp_number']
        if 'symptom_reminder_frequency' in data:
            prefs.symptom_reminder_frequency = data['symptom_reminder_frequency']
        if 'reminder_time' in data:
            from datetime import datetime
            try:
                prefs.reminder_time = datetime.strptime(data['reminder_time'], '%H:%M').time()
            except ValueError:
                pass
        
        prefs.save()
        
        return {
            'success': True,
            'server_id': str(prefs.id)
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@login_required
@patient_required
@require_http_methods(['GET'])
def get_offline_cache(request):
    """
    Get cached data for offline access.
    Returns essential patient data that can be used offline.
    """
    cache, created = OfflineDataCache.objects.get_or_create(patient=request.user)
    
    # If cache is old or empty, refresh it
    from datetime import timedelta
    if created or not cache.last_synced_at or (timezone.now() - cache.last_synced_at) > timedelta(hours=1):
        _refresh_offline_cache(request.user, cache)
    
    return JsonResponse({
        'symptom_logs': cache.symptom_logs,
        'alerts': cache.alerts,
        'treatment_plans': cache.treatment_plans,
        'notifications_prefs': cache.notifications_prefs,
        'last_synced': cache.last_synced_at.isoformat() if cache.last_synced_at else None,
        'cache_version': cache.cache_version,
    })


def _refresh_offline_cache(patient, cache):
    """Refresh the offline cache with latest data"""
    # Get recent symptom logs (last 30 days)
    from datetime import timedelta
    cutoff_date = timezone.now().date() - timedelta(days=30)
    
    logs = PatientSymptomLog.objects.filter(
        patient=patient,
        log_date__gte=cutoff_date
    ).order_by('-log_date')[:50]
    
    cache.symptom_logs = [{
        'id': str(log.id),
        'log_date': log.log_date.isoformat(),
        'overall_wellbeing': log.overall_wellbeing,
        'pain': log.pain,
        'fatigue': log.fatigue,
        'nausea': log.nausea,
        'notes': log.notes,
    } for log in logs]
    
    # Get recent alerts (last 30 days, unread first)
    alerts = PatientAlert.objects.filter(
        patient=patient
    ).order_by('-created_at')[:50]
    
    cache.alerts = [{
        'id': str(alert.id),
        'alert_type': alert.alert_type,
        'title': alert.title,
        'message': alert.message,
        'status': alert.status,
        'is_urgent': alert.is_urgent,
        'created_at': alert.created_at.isoformat(),
    } for alert in alerts]
    
    # Get treatment plans
    plans = PersonalizedTreatmentPlan.objects.filter(
        patient=patient,
        status='active'
    ).order_by('-created_at')
    
    cache.treatment_plans = [{
        'id': str(plan.id),
        'cancer_type': plan.cancer_type,
        'cancer_stage': plan.cancer_stage,
        'created_at': plan.created_at.isoformat(),
    } for plan in plans]
    
    # Get notification preferences
    try:
        prefs = PatientNotificationPreference.objects.get(patient=patient)
        cache.notifications_prefs = {
            'enable_in_app': prefs.enable_in_app,
            'enable_sms': prefs.enable_sms,
            'enable_whatsapp': prefs.enable_whatsapp,
            'enable_email': prefs.enable_email,
            'symptom_reminder_frequency': prefs.symptom_reminder_frequency,
        }
    except PatientNotificationPreference.DoesNotExist:
        cache.notifications_prefs = {}
    
    cache.last_synced_at = timezone.now()
    cache.cache_version += 1
    cache.save()
