"""
Views for Patient-Doctor Consultation System
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
from datetime import datetime, timedelta
import logging

from authentication.models import User, DoctorProfile
from .consultation_models import DoctorAvailability, ConsultationRequest, Consultation, ConsultationToken
from .models import PatientAlert

logger = logging.getLogger(__name__)


def patient_required(view_func):
    """Decorator to ensure user is a patient"""
    def wrapper(request, *args, **kwargs):
        if request.user.user_type != 'patient':
            messages.error(request, 'Access denied. Patients only.')
            return redirect('patient_login')
        return view_func(request, *args, **kwargs)
    return wrapper


def doctor_required(view_func):
    """Decorator to ensure user is a doctor"""
    def wrapper(request, *args, **kwargs):
        if request.user.user_type != 'doctor':
            messages.error(request, 'Access denied. Doctors only.')
            return redirect('doctor_login')
        return view_func(request, *args, **kwargs)
    return wrapper


# ============================================================================
# Patient Views
# ============================================================================

@login_required
@patient_required
def available_doctors(request):
    """List all available doctors for consultation"""
    # Get all verified doctors
    doctors = User.objects.filter(
        user_type='doctor',
        is_active=True
    ).select_related('doctor_profile').order_by('first_name', 'last_name')
    
    # Get distinct specializations from registered doctors
    from authentication.models import DoctorProfile
    registered_specializations = DoctorProfile.objects.filter(
        user__user_type='doctor',
        user__is_active=True
    ).values_list('specialization', flat=True).distinct().order_by('specialization')
    
    # Create list of available specializations with display names
    available_specializations = []
    for spec_value in registered_specializations:
        if spec_value:
            # Get the display name from choices
            display_name = dict(DoctorProfile.SPECIALIZATION_CHOICES).get(spec_value, spec_value)
            available_specializations.append({
                'value': spec_value,
                'display': display_name
            })
    
    # Filter by specialization if provided
    specialization = request.GET.get('specialization')
    if specialization and specialization != 'all':
        doctors = doctors.filter(doctor_profile__specialization=specialization)
    
    # Search by name
    search = request.GET.get('search', '').strip()
    if search:
        doctors = doctors.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(username__icontains=search)
        )
    
    # Sort by experience or name
    sort_by = request.GET.get('sort', 'name')
    if sort_by == 'experience':
        doctors = doctors.order_by('-doctor_profile__years_of_experience', 'first_name')
    elif sort_by == 'name':
        doctors = doctors.order_by('first_name', 'last_name')
    
    # Get doctors with availability
    doctors_with_availability = []
    for doctor in doctors:
        availability_count = DoctorAvailability.objects.filter(
            doctor=doctor,
            is_available=True
        ).count()
        
        doctors_with_availability.append({
            'doctor': doctor,
            'has_availability': availability_count > 0,
            'profile': getattr(doctor, 'doctor_profile', None)
        })
    
    # Sort by availability if requested
    if sort_by == 'availability':
        doctors_with_availability.sort(key=lambda x: x['has_availability'], reverse=True)
    
    paginator = Paginator(doctors_with_availability, 12)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)
    
    context = {
        'page_obj': page_obj,
        'search_query': search or '',
        'selected_specialization': specialization or '',
        'available_specializations': available_specializations,
        'sort_by': sort_by,
    }
    return render(request, 'patient_portal/consultations/available_doctors.html', context)


@login_required
@patient_required
def doctor_profile_view(request, doctor_id):
    """View doctor's profile and availability"""
    doctor = get_object_or_404(User, id=doctor_id, user_type='doctor')
    
    # Get doctor's availability
    availability_slots = DoctorAvailability.objects.filter(
        doctor=doctor,
        is_available=True
    ).order_by('weekday', 'start_time')
    
    # Group by weekday
    availability_by_day = {}
    for slot in availability_slots:
        day_name = slot.get_weekday_display()
        if day_name not in availability_by_day:
            availability_by_day[day_name] = []
        availability_by_day[day_name].append(slot)
    
    # Get existing consultation requests
    existing_requests = ConsultationRequest.objects.filter(
        patient=request.user,
        doctor=doctor,
        status__in=['pending', 'accepted', 'scheduled']
    ).exists()
    
    context = {
        'doctor': doctor,
        'doctor_profile': getattr(doctor, 'doctor_profile', None),
        'availability_by_day': availability_by_day,
        'existing_requests': existing_requests,
    }
    return render(request, 'patient_portal/consultations/doctor_profile.html', context)


@login_required
@patient_required
def request_consultation(request, doctor_id):
    """Create a consultation request"""
    doctor = get_object_or_404(User, id=doctor_id, user_type='doctor')
    
    # Check if there's already a pending request
    existing = ConsultationRequest.objects.filter(
        patient=request.user,
        doctor=doctor,
        status__in=['pending', 'accepted']
    ).first()
    
    if existing:
        messages.warning(request, 'You already have a pending consultation request with this doctor.')
        return redirect('patient_portal:consultation_requests')
    
    if request.method == 'POST':
        consultation_type = request.POST.get('consultation_type', 'general')
        reason = request.POST.get('reason', '').strip()
        preferred_dates = request.POST.getlist('preferred_dates[]')
        
        if not reason:
            messages.error(request, 'Please provide a reason for consultation.')
            return redirect('patient_portal:doctor_profile_view', doctor_id=doctor_id)
        
        # Create consultation request
        consultation_request = ConsultationRequest.objects.create(
            patient=request.user,
            doctor=doctor,
            consultation_type=consultation_type,
            reason=reason,
            preferred_dates=preferred_dates if preferred_dates else []
        )
        
        # Create notification for doctor
        PatientAlert.objects.create(
            patient=doctor,  # Send to doctor
            alert_type='general',
            title='New Consultation Request',
            message=f'{request.user.first_name} {request.user.last_name} has requested a consultation with you.',
            channel='in_app',
            status='sent',
            sent_at=timezone.now(),
            metadata={
                'patient_id': str(request.user.id),
                'request_id': str(consultation_request.id),
                'type': 'consultation_request'
            }
        )
        
        messages.success(request, f'Consultation request sent to Dr. {doctor.first_name} {doctor.last_name}. They will respond soon.')
        return redirect('patient_portal:consultation_requests')
    
    # GET request - show form
    availability_slots = DoctorAvailability.objects.filter(
        doctor=doctor,
        is_available=True
    ).order_by('weekday', 'start_time')
    
    context = {
        'doctor': doctor,
        'availability_slots': availability_slots,
    }
    return render(request, 'patient_portal/consultations/request_consultation.html', context)


@login_required
@patient_required
def consultation_requests(request):
    """List patient's consultation requests"""
    requests_list = ConsultationRequest.objects.filter(
        patient=request.user
    ).select_related('doctor').order_by('-requested_at')
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        requests_list = requests_list.filter(status=status)
    
    paginator = Paginator(requests_list, 10)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)
    
    context = {
        'page_obj': page_obj,
        'selected_status': status,
    }
    return render(request, 'patient_portal/consultations/consultation_requests.html', context)


@login_required
@patient_required
def accept_suggested_time(request, request_id):
    """Patient accepts doctor's suggested time"""
    consultation_request = get_object_or_404(
        ConsultationRequest,
        id=request_id,
        patient=request.user,
        status='accepted'
    )
    
    if request.method == 'POST':
        selected_time = request.POST.get('selected_time')
        
        if not selected_time:
            messages.error(request, 'Please select a time slot.')
            return redirect('patient_portal:consultation_requests')
        
        try:
            scheduled_datetime = datetime.fromisoformat(selected_time)
            
            # Create consultation
            consultation = Consultation.objects.create(
                request=consultation_request,
                patient=request.user,
                doctor=consultation_request.doctor,
                scheduled_datetime=scheduled_datetime,
                mode='video',  # Default mode
                duration_minutes=30
            )
            
            # Update request status
            consultation_request.status = 'scheduled'
            consultation_request.save()
            
            # Send email to patient
            send_consultation_confirmation_email(request.user, consultation)
            
            # Create notification for patient
            PatientAlert.objects.create(
                patient=request.user,
                alert_type='appointment',
                title='Consultation Confirmed',
                message=f'Your consultation with Dr. {consultation.doctor.first_name} {consultation.doctor.last_name} is confirmed for {scheduled_datetime.strftime("%B %d, %Y at %I:%M %p")}.',
                channel='in_app',
                status='sent',
                sent_at=timezone.now(),
                is_urgent=False,
                metadata={
                    'consultation_id': str(consultation.id),
                    'scheduled_datetime': scheduled_datetime.isoformat()
                }
            )
            
            # Create notification for doctor
            PatientAlert.objects.create(
                patient=consultation.doctor,
                alert_type='appointment',
                title='Consultation Confirmed',
                message=f'Consultation with {request.user.first_name} {request.user.last_name} confirmed for {scheduled_datetime.strftime("%B %d, %Y at %I:%M %p")}.',
                channel='in_app',
                status='sent',
                sent_at=timezone.now(),
                metadata={
                    'consultation_id': str(consultation.id),
                    'patient_id': str(request.user.id)
                }
            )
            
            messages.success(request, 'Consultation confirmed! Check your email for details.')
            return redirect('patient_portal:my_consultations')
            
        except Exception as e:
            messages.error(request, f'Error confirming consultation: {str(e)}')
            return redirect('patient_portal:consultation_requests')
    
    return redirect('patient_portal:consultation_requests')


@login_required
@patient_required
def my_consultations(request):
    """List patient's consultations"""
    consultations = Consultation.objects.filter(
        patient=request.user
    ).select_related('doctor').prefetch_related('consultation_token').order_by('-scheduled_datetime')
    
    # Separate upcoming and past
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    
    # Keep consultations as upcoming if they're scheduled for today or future
    upcoming = consultations.filter(scheduled_datetime__gte=today_start, status='scheduled')
    past = consultations.filter(Q(scheduled_datetime__lt=today_start) | ~Q(status='scheduled'))
    
    # Add can_start_call flag to upcoming consultations
    # Patients can start a call from scheduled time up to 30 minutes after
    upcoming_with_flags = []
    for consultation in upcoming[:5]:
        scheduled_time = consultation.scheduled_datetime
        # Allow calls from scheduled time to 30 minutes after
        call_window_start = scheduled_time
        call_window_end = scheduled_time + timedelta(minutes=30)
        can_start_call = call_window_start <= now <= call_window_end
        
        # Also set flag for when call will be available (show countdown if before)
        time_until_call = (call_window_start - now).total_seconds() if now < call_window_start else 0
        call_expired = now > call_window_end
        
        consultation.can_start_call = can_start_call
        consultation.time_until_call_minutes = max(0, int(time_until_call / 60))
        consultation.call_expired = call_expired
        
        # Attach token info for in-person consultations
        try:
            consultation.token = consultation.consultation_token
        except ConsultationToken.DoesNotExist:
            consultation.token = None
        
        upcoming_with_flags.append(consultation)
    
    # Also attach token info to past consultations
    past_with_tokens = []
    for consultation in past[:10]:
        try:
            consultation.token = consultation.consultation_token
        except ConsultationToken.DoesNotExist:
            consultation.token = None
        past_with_tokens.append(consultation)
    
    context = {
        'upcoming_consultations': upcoming_with_flags,
        'past_consultations': past_with_tokens,
    }
    return render(request, 'patient_portal/consultations/my_consultations.html', context)


@login_required
@patient_required
def download_consultation_token(request, consultation_id):
    """
    Download the in-person consultation token PDF.
    
    Flow (two-transaction approach):
    1. First blockchain TX: register token with a placeholder hash → get TX hash
    2. Generate complete PDF with TX hash, Etherscan link, etc.
    3. Hash the complete PDF
    4. Second blockchain TX: store the actual complete PDF hash
    5. Regenerate final PDF with the updated pdf_hash field
    """
    consultation = get_object_or_404(
        Consultation,
        id=consultation_id,
        patient=request.user,
        mode='in_person'
    )
    
    try:
        token = consultation.consultation_token
    except ConsultationToken.DoesNotExist:
        messages.error(request, 'No token found for this consultation.')
        return redirect('patient_portal:my_consultations')
    
    from .consultation_token_pdf import generate_consultation_token_pdf
    
    # Step 1: If no blockchain TX yet, do a registration transaction first
    if not token.blockchain_tx_hash:
        try:
            from blockchain.blockchain_service import store_consultation_token_hash
            import hashlib
            
            # Use a deterministic registration hash (not the PDF hash yet)
            registration_data = f"token:{token.id}:doctor:{token.doctor.id}:patient:{token.patient.id}:num:{token.token_number}"
            registration_hash = hashlib.sha256(registration_data.encode()).hexdigest()
            
            result = store_consultation_token_hash(
                token_number=token.token_number,
                pdf_hash=registration_hash,
                patient_id=str(token.patient.id),
                doctor_id=str(token.doctor.id)
            )
            if result and result.get('success'):
                token.blockchain_tx_hash = result.get('transaction_hash', '')
                token.is_verified = result.get('confirmed', False)
                token.save()
                logger.info(f"Token #{token.token_number} registered on blockchain: {result.get('transaction_hash')}")
        except Exception as e:
            logger.error(f"Error registering token on blockchain: {str(e)}")
            token.save()
    
    # Step 2: Generate the COMPLETE PDF with TX hash + all details
    pdf_file, pdf_hash = generate_consultation_token_pdf(token)
    
    # Step 3: Store the actual complete PDF hash on blockchain (second TX)
    if token.pdf_hash != pdf_hash and token.blockchain_tx_hash:
        token.pdf_hash = pdf_hash
        token.save()
        
        try:
            from blockchain.blockchain_service import get_blockchain_service
            service = get_blockchain_service()
            if service and service.is_connected() and service.token_contract:
                import hashlib as hl
                # Store the complete PDF hash via a second transaction
                pdf_hash_bytes32 = service.w3.to_bytes(hexstr=('0x' + pdf_hash))
                doctor_hash = service._hash_identifier(str(token.doctor.id))
                patient_hash = service._hash_identifier(str(token.patient.id))
                
                import json
                metadata = json.dumps({
                    'type': 'consultation_token_pdf_hash',
                    'token_number': token.token_number,
                    'is_final_pdf_hash': True,
                })
                
                nonce = service.w3.eth.get_transaction_count(service.account.address)
                gas_estimate = service.token_contract.functions.storeTokenHash(
                    pdf_hash_bytes32, doctor_hash, patient_hash,
                    token.token_number, metadata
                ).estimate_gas({'from': service.account.address})
                
                base_gas_price = service.w3.eth.gas_price
                transaction = service.token_contract.functions.storeTokenHash(
                    pdf_hash_bytes32, doctor_hash, patient_hash,
                    token.token_number, metadata
                ).build_transaction({
                    'chainId': service.w3.eth.chain_id,
                    'from': service.account.address,
                    'nonce': nonce,
                    'gas': int(gas_estimate * 1.5),
                    'gasPrice': int(base_gas_price * 2),
                })
                
                signed_txn = service.w3.eth.account.sign_transaction(
                    transaction, private_key=service.account.key
                )
                tx_hash = service.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
                tx_hex = tx_hash.hex() if tx_hash.hex().startswith('0x') else f"0x{tx_hash.hex()}"
                logger.info(f"Complete PDF hash stored on blockchain: {tx_hex}")
        except Exception as e:
            # Non-fatal: the registration TX is already on chain
            logger.warning(f"Could not store final PDF hash (registration TX already on chain): {str(e)}")
    
    # Step 4: Regenerate final PDF one more time with updated pdf_hash field
    final_pdf, final_hash = generate_consultation_token_pdf(token)
    token.pdf_file.save(f'consultation_token_{token.id}.pdf', final_pdf, save=True)
    
    # Serve the PDF
    token.pdf_file.open('rb')
    response = HttpResponse(token.pdf_file.read(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="consultation_token_{token.token_number}.pdf"'
    token.pdf_file.close()
    return response


@login_required
@patient_required
@require_POST
def cancel_consultation(request, consultation_id):
    """Cancel a consultation"""
    consultation = get_object_or_404(
        Consultation,
        id=consultation_id,
        patient=request.user,
        status='scheduled'
    )
    
    consultation.status = 'cancelled'
    consultation.save()
    
    # Notify doctor
    PatientAlert.objects.create(
        patient=consultation.doctor,
        alert_type='general',
        title='Consultation Cancelled',
        message=f'{request.user.first_name} {request.user.last_name} cancelled the consultation scheduled for {consultation.scheduled_datetime.strftime("%B %d, %Y at %I:%M %p")}.',
        channel='in_app',
        status='sent',
        sent_at=timezone.now(),
        metadata={'consultation_id': str(consultation.id)}
    )
    
    messages.success(request, 'Consultation cancelled successfully.')
    return redirect('patient_portal:my_consultations')


# ============================================================================
# Helper Functions
# ============================================================================

def send_consultation_confirmation_email(patient, consultation):
    """Send confirmation email to patient"""
    try:
        # Generate the correct call link
        call_link = f"{settings.SITE_URL}/portal/call/{consultation.id}/start/"
        
        subject = f'Consultation Confirmed - {consultation.scheduled_datetime.strftime("%B %d, %Y")}'
        message = f"""
Dear {patient.first_name} {patient.last_name},

Your consultation has been confirmed!

Doctor: Dr. {consultation.doctor.first_name} {consultation.doctor.last_name}
Date & Time: {consultation.scheduled_datetime.strftime("%B %d, %Y at %I:%M %p")}
Duration: {consultation.duration_minutes} minutes
Mode: {consultation.get_mode_display()}

To join the call on the scheduled date and time, click here:
{call_link}

Or log in to your patient portal and navigate to "My Consultations" to start the call.

Please be available 5 minutes before the scheduled time and ensure you have:
- A stable internet connection
- Camera and microphone permissions enabled in your browser
- A quiet environment for the consultation

If you need to cancel or reschedule, please log in to your patient portal.

Best regards,
RuralCare Team
"""
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [patient.email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error sending email: {str(e)}")
