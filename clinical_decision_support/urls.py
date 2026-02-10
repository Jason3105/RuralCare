from django.urls import path
from . import views

app_name = 'clinical_decision_support'

urlpatterns = [
    # AI Confidence Dashboard
    path('confidence/', views.ai_confidence_dashboard, name='ai_confidence_dashboard'),
    path('confidence/<uuid:confidence_id>/', views.ai_confidence_detail, name='ai_confidence_detail'),
    path('confidence/generate/<uuid:plan_id>/', views.generate_confidence_for_plan, name='generate_confidence'),
    
    # XAI Dashboard
    path('xai/', views.xai_dashboard, name='xai_dashboard'),
    path('xai/<uuid:xai_id>/', views.xai_detail, name='xai_detail'),
    path('xai/generate/<uuid:plan_id>/', views.generate_xai_for_plan, name='generate_xai'),
    
    # Tumor Board
    path('tumor-board/', views.tumor_board_list, name='tumor_board_list'),
    path('tumor-board/create/', views.tumor_board_create, name='tumor_board_create'),
    path('tumor-board/<uuid:session_id>/', views.tumor_board_detail, name='tumor_board_detail'),
    path('tumor-board/<uuid:session_id>/invite/', views.tumor_board_invite_member, name='tumor_board_invite'),
    path('tumor-board/<uuid:session_id>/decision/', views.tumor_board_submit_decision, name='tumor_board_decision'),
    path('tumor-board/<uuid:session_id>/activate/', views.tumor_board_activate_plan, name='tumor_board_activate'),
    
    # Toxicity Prediction
    path('toxicity/', views.toxicity_dashboard, name='toxicity_dashboard'),
    path('toxicity/<uuid:prediction_id>/', views.toxicity_detail, name='toxicity_detail'),
    path('toxicity/predict/', views.toxicity_predict, name='toxicity_predict'),
    
    # Symptom Monitoring
    path('symptoms/', views.symptom_monitoring_dashboard, name='symptom_monitoring_dashboard'),
    path('symptoms/patient/<uuid:patient_id>/', views.symptom_monitoring_patient, name='symptom_monitoring_patient'),
    path('symptoms/patient/<uuid:patient_id>/intervention/', views.add_intervention, name='add_intervention'),
    path('symptoms/patient/<uuid:patient_id>/update-status/', views.symptom_update_status, name='symptom_update_status'),
    
    # Patient Alerts (Doctor Features)
    path('patient-alerts/', views.patient_alerts_dashboard, name='patient_alerts_dashboard'),
    path('patient-alerts/send/', views.send_patient_alert, name='send_patient_alert'),
    path('patient-alerts/send-bulk/', views.send_bulk_alerts, name='send_bulk_alerts'),
    path('patient-alerts/quick-send/<uuid:patient_id>/', views.quick_send_alert, name='quick_send_alert'),
    
    # API Endpoints
    path('api/patient/<uuid:patient_id>/plans/', views.api_get_plans_for_patient, name='api_patient_plans'),
    path('api/doctors/', views.api_get_doctors, name='api_doctors'),
]
