from django.urls import path
from . import views
from . import qr_views
from patient_portal import doctor_consultation_views
from . import voice_assistant

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_page, name='login'),
    path('login/patient/', views.patient_login, name='patient_login'),
    path('login/doctor/', views.doctor_login, name='doctor_login'),
    path('auth/callback/', views.auth_callback, name='auth_callback'),
    path('logout/', views.logout_view, name='logout'),
    path('patient/dashboard/', views.patient_dashboard, name='patient_dashboard'),
    path('patient/profile/edit/', views.patient_profile_edit, name='patient_profile_edit'),
    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),
    path('doctor/profile/edit/', views.doctor_profile_edit, name='doctor_profile_edit'),
    # KYC Routes
    path('doctor/kyc/status/', views.kyc_status, name='kyc_status'),
    path('doctor/kyc/form/', views.kyc_form, name='kyc_form'),
    path('doctor/kyc/preview/', views.kyc_preview, name='kyc_preview'),
    
    # Medical Records
    path('patient/medical-records/', views.medical_records_list, name='medical_records_list'),
    path('patient/medical-records/upload/', views.upload_medical_record, name='upload_medical_record'),
    path('patient/medical-records/<uuid:record_id>/', views.medical_record_detail, name='medical_record_detail'),
    path('patient/medical-records/<uuid:record_id>/delete/', views.delete_medical_record, name='delete_medical_record'),
    
    # QR Code Routes
    path('patient/qr-code/', qr_views.patient_qr_dashboard, name='patient_qr_dashboard'),
    path('patient/qr-code/image/', qr_views.serve_qr_image, name='serve_qr_image'),
    path('patient/qr-code/regenerate/', qr_views.regenerate_qr_code, name='regenerate_qr_code'),
    path('patient/qr-code/disable/', qr_views.disable_qr_code, name='disable_qr_code'),
    path('patient/qr-code/enable/', qr_views.enable_qr_code, name='enable_qr_code'),
    path('patient/qr-code/analytics/<uuid:patient_id>/', qr_views.qr_scan_analytics, name='qr_scan_analytics'),
    path('doctor/qr-scanner/', qr_views.doctor_qr_scanner, name='doctor_qr_scanner'),
    path('doctor/qr-scanner/scan/', qr_views.scan_qr_code, name='scan_qr_code'),
    path('doctor/patient/<uuid:patient_id>/profile/', qr_views.scanned_patient_profile, name='scanned_patient_profile'),
    
    # Doctor Consultation Routes
    path('doctor/consultations/', doctor_consultation_views.doctor_consultation_dashboard, name='doctor_consultation_dashboard'),
    path('doctor/consultations/availability/', doctor_consultation_views.manage_availability, name='doctor_manage_availability'),
    path('doctor/consultations/availability/<uuid:slot_id>/delete/', doctor_consultation_views.delete_availability, name='doctor_delete_availability'),
    path('doctor/consultations/availability/<uuid:slot_id>/toggle/', doctor_consultation_views.toggle_availability, name='doctor_toggle_availability'),
    path('doctor/consultations/requests/', doctor_consultation_views.doctor_consultation_requests, name='doctor_consultation_requests'),
    path('doctor/consultations/requests/<uuid:request_id>/respond/', doctor_consultation_views.respond_to_request, name='doctor_respond_to_request'),
    path('doctor/consultations/list/', doctor_consultation_views.doctor_consultation_dashboard, name='doctor_consultations'),
    path('doctor/consultations/<uuid:consultation_id>/', doctor_consultation_views.consultation_detail, name='doctor_consultation_detail'),
    
    # Blockchain status refresh
    path('blockchain/refresh-status/', qr_views.refresh_blockchain_status, name='refresh_blockchain_status'),
    
    # Nearby clinics
    path("clinics/nearby/", views.nearby_clinics_page, name='nearby_clinics'),
    path("api/nearby-clinics/", views.nearby_clinics, name='api_nearby_clinics'),
    
    # Voice Assistant API
    path('api/voice-assistant/', voice_assistant.voice_assistant_api, name='voice_assistant_api'),
    path('api/voice-assistant/status/', voice_assistant.voice_assistant_status, name='voice_assistant_status'),
]