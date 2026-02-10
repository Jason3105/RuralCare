"""
Views for Patient QR Code Access System
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from cancer_detection.models import CancerImageAnalysis, PersonalizedTreatmentPlan
from .models import User, PatientQRCode, QRCodeScanLog, PatientProfile, MedicalRecord
from .qr_utils import (
    create_patient_qr_code, 
    validate_qr_token, 
    log_qr_scan,
    regenerate_patient_qr_code,
    disable_patient_qr_code,
    enable_patient_qr_code,
    generate_qr_code
)
from blockchain.status_updater import update_single_transaction
import json
import os


@login_required
def patient_qr_dashboard(request):
    """
    Patient's QR code management dashboard
    Displays their QR code and allows download/regenerate
    """
    if request.user.user_type != 'patient':
        return redirect('patient_login')
    
    # Get or create QR code
    qr_code = PatientQRCode.objects.filter(patient=request.user, is_active=True).first()
    
    if not qr_code:
        # Create new QR code if doesn't exist
        qr_code = create_patient_qr_code(request.user)
    
    # Get scan history
    scan_logs = QRCodeScanLog.objects.filter(patient=request.user).order_by('-scan_timestamp')[:10]
    
    context = {
        'qr_code': qr_code,
        'scan_logs': scan_logs,
        'total_scans': QRCodeScanLog.objects.filter(patient=request.user).count(),
    }
    
    return render(request, 'authentication/patient_qr_dashboard.html', context)


@login_required
def serve_qr_image(request):
    """
    Dynamically generate and serve the QR code image.
    This is a fallback when stored images are not accessible.
    """
    if request.user.user_type != 'patient':
        return HttpResponse(status=403)
    
    qr_code = PatientQRCode.objects.filter(patient=request.user, is_active=True).first()
    
    if not qr_code:
        return HttpResponse(status=404)
    
    # Try to serve from local media first
    if qr_code.qr_code_image:
        local_path = os.path.join(settings.MEDIA_ROOT, qr_code.qr_code_image.name)
        if os.path.exists(local_path):
            with open(local_path, 'rb') as f:
                return HttpResponse(f.read(), content_type='image/png')
    
    # Generate QR code dynamically
    from io import BytesIO
    import qrcode
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_code.encrypted_token)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_io = BytesIO()
    img.save(img_io, format='PNG')
    img_io.seek(0)
    
    return HttpResponse(img_io.getvalue(), content_type='image/png')


@login_required
@require_POST
def regenerate_qr_code(request):
    """
    Regenerate patient's QR code (invalidates old code)
    """
    if request.user.user_type != 'patient':
        messages.error(request, 'Unauthorized access.')
        return redirect('patient_login')
    
    try:
        new_qr_code = regenerate_patient_qr_code(request.user)
        
        if new_qr_code:
            messages.success(request, 'QR code regenerated successfully! Old code is now invalid.')
        else:
            messages.error(request, 'Failed to regenerate QR code. Please try again.')
    
    except Exception as e:
        messages.error(request, f'Error regenerating QR code: {str(e)}')
    
    return redirect('patient_qr_dashboard')


@login_required
@require_POST
def disable_qr_code(request):
    """
    Disable patient's QR code
    """
    if request.user.user_type != 'patient':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        success = disable_patient_qr_code(request.user)
        
        if success:
            messages.success(request, 'QR code disabled successfully.')
            return JsonResponse({
                'success': True,
                'message': 'QR code disabled'
            })
        else:
            return JsonResponse({'error': 'Failed to disable QR code'}, status=400)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def enable_qr_code(request):
    """
    Re-enable patient's QR code
    """
    if request.user.user_type != 'patient':
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        qr_code = enable_patient_qr_code(request.user)
        
        if qr_code:
            messages.success(request, 'QR code re-enabled successfully.')
            return JsonResponse({
                'success': True,
                'message': 'QR code enabled',
                'qr_code_id': str(qr_code.id)
            })
        else:
            return JsonResponse({'error': 'Failed to enable QR code'}, status=400)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def doctor_qr_scanner(request):
    """
    Doctor's QR code scanner interface
    Allows scanning using device camera
    """
    if request.user.user_type != 'doctor':
        return redirect('doctor_login')
    
    context = {
        'page_title': 'QR Code Scanner',
    }
    
    return render(request, 'authentication/doctor_qr_scanner.html', context)


@login_required
@require_POST
def scan_qr_code(request):
    """
    Process scanned QR code token
    Backend validation and patient data retrieval
    """
    if request.user.user_type != 'doctor':
        return JsonResponse({'error': 'Only doctors can scan QR codes'}, status=403)
    
    try:
        data = json.loads(request.body)
        token = data.get('token', '').strip()
        
        if not token:
            return JsonResponse({'error': 'Invalid token'}, status=400)
        
        # Validate token
        qr_code = validate_qr_token(token)
        
        if not qr_code:
            # Log failed scan attempt
            log_qr_scan(
                None,
                request.user,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                access_granted=False,
                denial_reason='Invalid or expired token'
            )
            return JsonResponse({'error': 'Invalid or expired QR code'}, status=400)
        
        patient = qr_code.patient
        
        # Log successful scan
        log_qr_scan(
            qr_code,
            request.user,
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            access_granted=True
        )
        
        # Create notification for patient
        from patient_portal.models import PatientAlert
        doctor_name = f"Dr. {request.user.first_name} {request.user.last_name}" if request.user.first_name else f"Dr. {request.user.username}"
        PatientAlert.objects.create(
            patient=patient,
            alert_type='general',
            title='Your QR Code Was Scanned',
            message=f'{doctor_name} has accessed your medical records via QR code scan at {timezone.now().strftime("%I:%M %p on %B %d, %Y")}.',
            channel='in_app',
            status='sent',
            sent_at=timezone.now(),
            is_urgent=False,
            metadata={
                'doctor_id': str(request.user.id),
                'doctor_name': doctor_name,
                'scan_type': 'qr_code',
                'qr_code_id': str(qr_code.id)
            }
        )
        
        # Retrieve patient data
        patient_data = get_patient_medical_profile(patient)
        
        return JsonResponse({
            'success': True,
            'patient': patient_data,
            'message': 'Patient data retrieved successfully'
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid request format'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Error processing scan: {str(e)}'}, status=500)


@login_required
def scanned_patient_profile(request, patient_id):
    """
    Display detailed patient profile after QR scan
    Only accessible to authenticated doctors
    """
    if request.user.user_type != 'doctor':
        return redirect('doctor_login')
    
    try:
        patient = get_object_or_404(User, id=patient_id, user_type='patient')
        
        # Get patient data
        patient_data = get_patient_medical_profile(patient)
        
        # Get the most recent scan log for this patient by this doctor
        recent_scan = QRCodeScanLog.objects.filter(
            patient=patient,
            scanned_by=request.user,
            access_granted=True
        ).order_by('-scan_timestamp').first()
        
        # Get patient QR code
        patient_qr = PatientQRCode.objects.filter(patient=patient, is_active=True).first()
        
        # Get actual objects for image/document viewing
        cancer_analyses = CancerImageAnalysis.objects.filter(user=patient).order_by('-created_at')[:5]
        medical_records = MedicalRecord.objects.filter(patient=patient).order_by('-created_at')
        
        context = {
            'patient': patient,
            'patient_data': patient_data,
            'recent_scan': recent_scan,
            'patient_qr': patient_qr,
            'cancer_analyses_objects': cancer_analyses,
            'medical_records_objects': medical_records,
        }
        
        return render(request, 'authentication/scanned_patient_profile.html', context)
    
    except Exception as e:
        messages.error(request, f'Error retrieving patient profile: {str(e)}')
        return redirect('doctor_qr_scanner')


@login_required
def qr_scan_analytics(request, patient_id):
    """
    View scan history and analytics for a patient's QR code
    Only accessible to the patient whose code was scanned
    """
    if request.user.id != patient_id and request.user.user_type != 'doctor':
        return redirect('patient_login')
    
    try:
        patient = get_object_or_404(User, id=patient_id, user_type='patient')
        
        if request.user.user_type == 'patient' and request.user != patient:
            return redirect('patient_login')
        
        # Get scan logs
        scan_logs = QRCodeScanLog.objects.filter(patient=patient).order_by('-scan_timestamp')
        
        # Analytics
        total_scans = scan_logs.count()
        unique_doctors = scan_logs.values('scanned_by').distinct().count()
        last_scan = scan_logs.first()
        
        context = {
            'patient': patient,
            'scan_logs': scan_logs,
            'total_scans': total_scans,
            'unique_doctors': unique_doctors,
            'last_scan': last_scan,
        }
        
        return render(request, 'authentication/qr_scan_analytics.html', context)
    
    except Exception as e:
        messages.error(request, f'Error retrieving scan analytics: {str(e)}')
        return redirect('patient_dashboard')


def get_client_ip(request):
    """
    Get client IP address from request
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_patient_medical_profile(patient):
    """
    Retrieve complete medical profile of a patient
    Called when doctor scans QR code
    
    Args:
        patient: User object (patient)
    
    Returns:
        Dictionary with complete patient data
    """
    from cancer_detection.models import CancerImageAnalysis, PersonalizedTreatmentPlan
    
    try:
        # Basic info
        patient_profile = PatientProfile.objects.filter(user=patient).first()
        
        # Cancer analyses
        cancer_analyses = CancerImageAnalysis.objects.filter(user=patient).order_by('-created_at')
        
        # Treatment plans
        treatment_plans = PersonalizedTreatmentPlan.objects.filter(patient=patient).order_by('-created_at')
        
        # Medical records
        medical_records = MedicalRecord.objects.filter(patient=patient).order_by('-created_at')
        
        # Build response
        patient_data = {
            'id': str(patient.id),
            'username': patient.username,
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'email': patient.email,
            'date_joined': patient.date_joined.isoformat(),
            
            # Profile information
            'profile': {
                'date_of_birth': patient_profile.date_of_birth.isoformat() if patient_profile and patient_profile.date_of_birth else None,
                'gender': patient_profile.gender if patient_profile else None,
                'blood_group': patient_profile.blood_group if patient_profile else None,
                'address': patient_profile.address if patient_profile else None,
                'emergency_contact_name': patient_profile.emergency_contact_name if patient_profile else None,
                'emergency_contact_phone': patient_profile.emergency_contact_phone if patient_profile else None,
                'medical_history': patient_profile.medical_history if patient_profile else None,
                'allergies': patient_profile.allergies if patient_profile else None,
                'current_medications': patient_profile.current_medications if patient_profile else None,
            },
            
            # Cancer analyses
            'cancer_analyses': [
                {
                    'id': str(analysis.id),
                    'image_type': analysis.image_type,
                    'tumor_detected': analysis.tumor_detected,
                    'tumor_type': analysis.tumor_type,
                    'tumor_stage': analysis.tumor_stage,
                    'tumor_size_mm': analysis.tumor_size_mm,
                    'tumor_location': analysis.tumor_location,
                    'detection_confidence': analysis.detection_confidence,
                    'created_at': analysis.created_at.isoformat(),
                    'notes': analysis.notes,
                }
                for analysis in cancer_analyses[:5]  # Last 5 analyses
            ],
            
            # Treatment plans
            'treatment_plans': [
                {
                    'id': str(plan.id),
                    'plan_name': plan.plan_name,
                    'cancer_type': plan.cancer_type,
                    'cancer_stage': plan.cancer_stage,
                    'status': plan.status,
                    'predicted_5yr_survival': plan.predicted_5yr_survival,
                    'remission_probability': plan.remission_probability,
                    'quality_of_life_score': plan.quality_of_life_score,
                    'created_at': plan.created_at.isoformat(),
                    'primary_treatments': plan.primary_treatments,
                    'adjuvant_treatments': plan.adjuvant_treatments,
                    'targeted_therapies': plan.targeted_therapies,
                }
                for plan in treatment_plans[:3]  # Last 3 plans
            ],
            
            # Medical records
            'medical_records': [
                {
                    'id': str(record.id),
                    'title': record.title,
                    'document_type': record.document_type,
                    'ocr_status': record.ocr_status,
                    'extracted_text': record.extracted_text[:500] if record.extracted_text else None,  # First 500 chars
                    'created_at': record.created_at.isoformat(),
                }
                for record in medical_records[:5]  # Last 5 records
            ],
            
            'summary': {
                'total_analyses': cancer_analyses.count(),
                'total_with_tumors': cancer_analyses.filter(tumor_detected=True).count(),
                'total_treatment_plans': treatment_plans.count(),
                'total_medical_records': medical_records.count(),
            }
        }
        
        return patient_data
    
    except Exception as e:
        print(f"Error retrieving patient profile: {str(e)}")
        return {}


@require_POST
@login_required
def refresh_blockchain_status(request):
    """
    Refresh blockchain transaction status for a specific scan
    """
    try:
        data = json.loads(request.body)
        tx_hash = data.get('tx_hash')
        
        if not tx_hash:
            return JsonResponse({'success': False, 'error': 'Transaction hash required'}, status=400)
        
        # Update the transaction status
        result = update_single_transaction(tx_hash)
        
        if result['success']:
            # Get updated scan data
            scan = QRCodeScanLog.objects.filter(
                blockchain_tx_hash__in=[tx_hash, tx_hash.lstrip('0x')]
            ).first()
            
            if scan:
                return JsonResponse({
                    'success': True,
                    'confirmed': result.get('confirmed', False),
                    'pending': result.get('pending', False),
                    'already_confirmed': result.get('already_confirmed', False),
                    'block_number': scan.blockchain_block_number,
                    'log_id': scan.blockchain_log_id,
                    'message': result.get('message', 'Status updated')
                })
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

