from django.urls import path
from . import views
from . import consultation_views
from . import call_views
from . import prescription_views
from . import offline_sync_views
from . import telegram_views

app_name = 'patient_portal'

urlpatterns = [
    # Overview/Dashboard
    path('', views.patient_overview, name='overview'),
    
    # Health Hub - Combined Overview + Symptoms + Side Effects
    path('health-hub/', views.health_hub, name='health_hub'),
    
    # Treatment Center - Combined Plans + Confidence + Explained
    path('treatment-center/', views.treatment_center, name='treatment_center'),
    
    # Confidence View (Simplified)
    path('confidence/', views.patient_confidence_view, name='confidence_view'),
    
    # Treatment Explanations
    path('treatment/', views.treatment_explanation_list, name='treatment_explanation_list'),
    path('treatment/<uuid:explanation_id>/', views.treatment_explanation_detail, name='treatment_explanation_detail'),
    
    # Side Effects
    path('side-effects/', views.side_effects_list, name='side_effects_list'),
    path('side-effects/<uuid:info_id>/', views.side_effects_detail, name='side_effects_detail'),
    
    # Symptom Logging
    path('symptoms/', views.symptom_log_list, name='symptom_log_list'),
    path('symptoms/log/', views.symptom_log_create, name='symptom_log_create'),
    path('symptoms/<uuid:log_id>/', views.symptom_log_detail, name='symptom_log_detail'),
    
    # Alerts & Reminders
    path('alerts/', views.alerts_list, name='alerts_list'),
    path('alerts/<uuid:alert_id>/read/', views.mark_alert_read, name='mark_alert_read'),
    path('alerts/mark-all-read/', views.mark_all_alerts_read, name='mark_all_alerts_read'),
    
    # Notification Preferences
    path('notifications/', views.notification_preferences, name='notification_preferences'),
    
    # Consultations
    path('consultations/doctors/', consultation_views.available_doctors, name='available_doctors'),
    path('consultations/doctor/<uuid:doctor_id>/', consultation_views.doctor_profile_view, name='doctor_profile_view'),
    path('consultations/request/<uuid:doctor_id>/', consultation_views.request_consultation, name='request_consultation'),
    path('consultations/requests/', consultation_views.consultation_requests, name='consultation_requests'),
    path('consultations/accept/<uuid:request_id>/', consultation_views.accept_suggested_time, name='accept_suggested_time'),
    path('consultations/my/', consultation_views.my_consultations, name='my_consultations'),
    path('consultations/cancel/<uuid:consultation_id>/', consultation_views.cancel_consultation, name='cancel_consultation'),
    
    # Call functionality
    path('call/<uuid:consultation_id>/start/', call_views.initiate_call, name='initiate_call'),
    path('call/<uuid:consultation_id>/join/', call_views.doctor_call_view, name='doctor_call_view'),
    path('call/<uuid:consultation_id>/status/', call_views.call_status, name='call_status'),
    path('call/<uuid:consultation_id>/end/', call_views.end_call, name='end_call'),
    path('call/<uuid:consultation_id>/offer/', call_views.send_offer, name='send_offer'),
    path('call/<uuid:consultation_id>/answer/', call_views.send_answer, name='send_answer'),
    path('call/<uuid:consultation_id>/ice/', call_views.send_ice_candidate, name='send_ice_candidate'),
    path('call/<uuid:consultation_id>/agora-token/', call_views.get_agora_token, name='get_agora_token'),
    
    # Prescription Management
    path('prescription/create/<uuid:consultation_id>/', prescription_views.create_prescription, name='create_prescription'),
    path('prescription/<uuid:prescription_id>/edit/', prescription_views.edit_prescription, name='edit_prescription'),
    path('prescription/<uuid:prescription_id>/generate/', prescription_views.generate_prescription_pdf, name='generate_prescription_pdf'),
    path('prescription/<uuid:prescription_id>/', prescription_views.view_prescription, name='view_prescription'),
    path('prescription/<uuid:prescription_id>/download/', prescription_views.download_prescription, name='download_prescription'),
    path('prescription/<uuid:prescription_id>/verify/', prescription_views.verify_prescription, name='verify_prescription'),
    path('prescription/verify-upload/', prescription_views.verify_uploaded_prescription, name='verify_uploaded_prescription'),
    
    # API Endpoints
    path('api/alerts/count/', views.api_unread_alerts_count, name='api_alerts_count'),
    path('api/symptoms/trend/', views.api_symptom_trend, name='api_symptom_trend'),
    path('api/incoming-calls/', call_views.check_incoming_calls, name='api_incoming_calls'),
    path('api/badges/check/', views.api_check_new_badges, name='api_check_badges'),
    path('api/stats/', views.api_user_stats, name='api_user_stats'),
    
    # Offline Sync Endpoints
    path('api/offline/sync-status/', offline_sync_views.sync_status, name='offline_sync_status'),
    path('api/offline/sync/', offline_sync_views.sync_operations, name='offline_sync_operations'),
    path('api/offline/cache/', offline_sync_views.get_offline_cache, name='offline_cache'),
    
    # Telegram Integration
    path('telegram/webhook/', telegram_views.telegram_webhook, name='telegram_webhook'),
    path('telegram/link/', telegram_views.link_telegram_account, name='link_telegram'),
    path('telegram/unlink/', telegram_views.unlink_telegram_account, name='unlink_telegram'),
]
