"""
Doctor-side Consultation Views
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse
from datetime import datetime, timedelta

from .consultation_models import DoctorAvailability, ConsultationRequest, Consultation, ConsultationToken
from .models import PatientAlert
from patient_portal.consultation_views import doctor_required


@login_required
@doctor_required
def doctor_consultation_dashboard(request):
    """Doctor's consultation dashboard"""
    # Get pending requests
    pending_requests = ConsultationRequest.objects.filter(
        doctor=request.user,
        status='pending'
    ).select_related('patient').order_by('-requested_at')[:5]
    
    # Get upcoming consultations
    upcoming = Consultation.objects.filter(
        doctor=request.user,
        status='scheduled',
        scheduled_datetime__gte=timezone.now()
    ).select_related('patient').order_by('scheduled_datetime')[:5]
    
    # Get ALL today's consultations (scheduled, in_progress, and completed)
    today = timezone.now().date()
    today_consultations = Consultation.objects.filter(
        doctor=request.user,
        scheduled_datetime__date=today
    ).exclude(
        status__in=['cancelled', 'no_show']
    ).select_related('patient').order_by('scheduled_datetime')
    
    context = {
        'pending_requests': pending_requests,
        'upcoming_consultations': upcoming,
        'today_consultations': today_consultations,
        'pending_count': ConsultationRequest.objects.filter(
            doctor=request.user,
            status='pending'
        ).count(),
    }
    return render(request, 'authentication/doctor/consultation_dashboard.html', context)


@login_required
@doctor_required
def manage_availability(request):
    """Manage doctor's availability"""
    if request.method == 'POST':
        weekday = int(request.POST.get('weekday'))
        start_time = request.POST.get('start_time')
        end_time = request.POST.get('end_time')
        slot_duration = int(request.POST.get('slot_duration', 30))
        
        try:
            DoctorAvailability.objects.create(
                doctor=request.user,
                weekday=weekday,
                start_time=start_time,
                end_time=end_time,
                slot_duration=slot_duration,
                is_available=True
            )
            messages.success(request, 'Availability slot added successfully.')
        except Exception as e:
            messages.error(request, f'Error adding availability: {str(e)}')
        
        return redirect('doctor_manage_availability')
    
    # GET - show availability
    availability_slots = DoctorAvailability.objects.filter(
        doctor=request.user
    ).order_by('weekday', 'start_time')
    
    context = {
        'availability_slots': availability_slots,
    }
    return render(request, 'authentication/doctor/manage_availability.html', context)


@login_required
@doctor_required
@require_POST
def delete_availability(request, slot_id):
    """Delete an availability slot"""
    slot = get_object_or_404(DoctorAvailability, id=slot_id, doctor=request.user)
    slot.delete()
    messages.success(request, 'Availability slot deleted.')
    return redirect('doctor_manage_availability')


@login_required
@doctor_required
@require_POST
def toggle_availability(request, slot_id):
    """Toggle availability slot on/off"""
    slot = get_object_or_404(DoctorAvailability, id=slot_id, doctor=request.user)
    slot.is_available = not slot.is_available
    slot.save()
    
    status = 'enabled' if slot.is_available else 'disabled'
    messages.success(request, f'Availability slot {status}.')
    return redirect('doctor_manage_availability')


@login_required
@doctor_required
def doctor_consultation_requests(request):
    """View all consultation requests"""
    requests_list = ConsultationRequest.objects.filter(
        doctor=request.user
    ).select_related('patient').order_by('-requested_at')
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        requests_list = requests_list.filter(status=status)
    else:
        # Default: show pending and accepted
        requests_list = requests_list.filter(status__in=['pending', 'accepted'])
    
    paginator = Paginator(requests_list, 15)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)
    
    context = {
        'page_obj': page_obj,
        'selected_status': status,
    }
    return render(request, 'authentication/doctor/consultation_requests.html', context)


@login_required
@doctor_required
def respond_to_request(request, request_id):
    """Respond to a consultation request"""
    consultation_request = get_object_or_404(
        ConsultationRequest,
        id=request_id,
        doctor=request.user,
        status='pending'
    )
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'accept':
            # Get scheduling details from form
            scheduled_date = request.POST.get('scheduled_date')
            scheduled_time = request.POST.get('scheduled_time')
            duration = request.POST.get('duration', '30')
            mode = request.POST.get('mode', 'video')
            doctor_notes = request.POST.get('doctor_notes', '')
            meeting_link = request.POST.get('meeting_link', '')
            
            if not scheduled_date or not scheduled_time:
                messages.error(request, 'Please provide date and time for the consultation.')
                return redirect('doctor_respond_to_request', request_id=request_id)
            
            # Create datetime object
            from datetime import datetime
            scheduled_datetime = datetime.strptime(f"{scheduled_date} {scheduled_time}", "%Y-%m-%d %H:%M")
            scheduled_datetime = timezone.make_aware(scheduled_datetime)
            
            # Update request status
            consultation_request.status = 'scheduled'
            consultation_request.doctor_notes = doctor_notes
            consultation_request.responded_at = timezone.now()
            consultation_request.save()
            
            # Create Consultation record
            consultation = Consultation.objects.create(
                request=consultation_request,
                patient=consultation_request.patient,
                doctor=request.user,
                scheduled_datetime=scheduled_datetime,
                duration_minutes=int(duration),
                mode=mode,
                meeting_link=meeting_link,
                doctor_notes=doctor_notes,
                status='scheduled'
            )
            
            # Auto-create token for in-person consultations
            if mode == 'in_person':
                try:
                    token_number = ConsultationToken.get_next_token_number(request.user)
                    ConsultationToken.objects.create(
                        consultation=consultation,
                        doctor=request.user,
                        patient=consultation_request.patient,
                        token_number=token_number,
                    )
                except Exception as e:
                    print(f"Error creating consultation token: {e}")
            
            # Send email notification to patient
            from django.core.mail import send_mail
            from django.conf import settings
            
            # Prepare email content
            doctor_name = f"Dr. {request.user.first_name} {request.user.last_name}"
            patient_name = consultation_request.patient.first_name
            formatted_date = scheduled_datetime.strftime('%B %d, %Y')
            formatted_time = scheduled_datetime.strftime('%I:%M %p')
            mode_display = mode.replace('_', ' ').title()
            
            email_subject = f'Consultation Scheduled - {formatted_date}'
            
            # HTML Email Template
            email_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Consultation Scheduled</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background-color: #f9fafb; line-height: 1.6;">
    <table role="presentation" style="width: 100%; border-collapse: collapse; background-color: #f9fafb;">
        <tr>
            <td style="padding: 40px 20px;">
                <table role="presentation" style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden;">
                    <!-- Header -->
                    <tr>
                        <td style="padding: 32px 32px 24px; border-bottom: 1px solid #e5e7eb;">
                            <h1 style="margin: 0; font-size: 24px; font-weight: 600; color: #111827; letter-spacing: -0.025em;">
                                Consultation Scheduled
                            </h1>
                        </td>
                    </tr>
                    
                    <!-- Body -->
                    <tr>
                        <td style="padding: 32px;">
                            <p style="margin: 0 0 24px; font-size: 15px; color: #374151;">
                                Hello {patient_name},
                            </p>
                            
                            <p style="margin: 0 0 24px; font-size: 15px; color: #374151;">
                                Your consultation has been confirmed. Please find the details below.
                            </p>
                            
                            <!-- Details Box -->
                            <table role="presentation" style="width: 100%; border: 1px solid #e5e7eb; border-radius: 6px; margin-bottom: 24px;">
                                <tr>
                                    <td style="padding: 20px; background-color: #f9fafb;">
                                        <table role="presentation" style="width: 100%;">
                                            <tr>
                                                <td style="padding: 8px 0; font-size: 14px; color: #6b7280; width: 120px;">Doctor</td>
                                                <td style="padding: 8px 0; font-size: 14px; color: #111827; font-weight: 500;">{doctor_name}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0; font-size: 14px; color: #6b7280; border-top: 1px solid #e5e7eb;">Date</td>
                                                <td style="padding: 8px 0; font-size: 14px; color: #111827; font-weight: 500; border-top: 1px solid #e5e7eb;">{formatted_date}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0; font-size: 14px; color: #6b7280; border-top: 1px solid #e5e7eb;">Time</td>
                                                <td style="padding: 8px 0; font-size: 14px; color: #111827; font-weight: 500; border-top: 1px solid #e5e7eb;">{formatted_time}</td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0; font-size: 14px; color: #6b7280; border-top: 1px solid #e5e7eb;">Duration</td>
                                                <td style="padding: 8px 0; font-size: 14px; color: #111827; font-weight: 500; border-top: 1px solid #e5e7eb;">{duration} minutes</td>
                                            </tr>
                                            <tr>
                                                <td style="padding: 8px 0; font-size: 14px; color: #6b7280; border-top: 1px solid #e5e7eb;">Mode</td>
                                                <td style="padding: 8px 0; font-size: 14px; color: #111827; font-weight: 500; border-top: 1px solid #e5e7eb;">{mode_display}</td>
                                            </tr>
                                            {f'''<tr>
                                                <td style="padding: 8px 0; font-size: 14px; color: #6b7280; border-top: 1px solid #e5e7eb;">Meeting Link</td>
                                                <td style="padding: 8px 0; border-top: 1px solid #e5e7eb;">
                                                    <a href="{meeting_link}" style="color: #2563eb; text-decoration: none; font-size: 14px; font-weight: 500;">{meeting_link}</a>
                                                </td>
                                            </tr>''' if meeting_link else ''}
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            {f'''<div style="padding: 16px; background-color: #f9fafb; border-left: 3px solid #111827; border-radius: 4px; margin-bottom: 24px;">
                                <p style="margin: 0; font-size: 14px; color: #111827; font-weight: 500;">Preparation Notes</p>
                                <p style="margin: 8px 0 0; font-size: 14px; color: #374151; white-space: pre-line;">{doctor_notes}</p>
                            </div>''' if doctor_notes else ''}
                            
                            <p style="margin: 0 0 16px; font-size: 14px; color: #374151;">
                                Please ensure you are available at the scheduled time.
                            </p>
                        </td>
                    </tr>
                    
                    <!-- Footer -->
                    <tr>
                        <td style="padding: 24px 32px; border-top: 1px solid #e5e7eb; background-color: #f9fafb;">
                            <p style="margin: 0; font-size: 13px; color: #6b7280;">
                                Cancer Treatment System
                            </p>
                            <p style="margin: 8px 0 0; font-size: 12px; color: #9ca3af;">
                                This is an automated message. Please do not reply to this email.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
            
            # Plain text fallback
            email_text = f"""Consultation Scheduled

Hello {patient_name},

Your consultation has been confirmed.

Details:
Doctor: {doctor_name}
Date: {formatted_date}
Time: {formatted_time}
Duration: {duration} minutes
Mode: {mode_display}
{f'Meeting Link: {meeting_link}' if meeting_link else ''}

{f'Preparation Notes: {doctor_notes}' if doctor_notes else ''}

Please ensure you are available at the scheduled time.

Cancer Treatment System
"""
            
            try:
                from django.core.mail import EmailMultiAlternatives
                
                email = EmailMultiAlternatives(
                    email_subject,
                    email_text,
                    settings.EMAIL_HOST_USER,
                    [consultation_request.patient.email]
                )
                email.attach_alternative(email_html, "text/html")
                email.send(fail_silently=False)
            except Exception as e:
                print(f"Failed to send email: {e}")
            
            # Notify patient in-app
            PatientAlert.objects.create(
                patient=consultation_request.patient,
                alert_type='general',
                title='Consultation Scheduled',
                message=f'Dr. {request.user.first_name} {request.user.last_name} has scheduled your consultation for {scheduled_datetime.strftime("%B %d, %Y at %I:%M %p")}. Check your email for details.',
                channel='in_app',
                status='sent',
                sent_at=timezone.now(),
                is_urgent=True,
                metadata={
                    'consultation_id': str(consultation.id),
                    'scheduled_datetime': scheduled_datetime.isoformat(),
                    'mode': mode,
                    'meeting_link': meeting_link
                }
            )
            
            messages.success(request, 'Consultation scheduled successfully! Patient has been notified via email and in-app alert.')
            return redirect('doctor_consultation_dashboard')
            
        elif action == 'reject':
            rejection_reason = request.POST.get('rejection_reason', '')
            
            consultation_request.status = 'rejected'
            consultation_request.doctor_notes = rejection_reason
            consultation_request.responded_at = timezone.now()
            consultation_request.save()
            
            # Notify patient
            PatientAlert.objects.create(
                patient=consultation_request.patient,
                alert_type='general',
                title='Consultation Request Update',
                message=f'Dr. {request.user.first_name} {request.user.last_name} is unable to accept your consultation request at this time. {rejection_reason}',
                channel='in_app',
                status='sent',
                sent_at=timezone.now(),
                metadata={'request_id': str(consultation_request.id)}
            )
            
            messages.success(request, 'Request rejected. Patient has been notified.')
        
        return redirect('doctor_consultation_requests')
    
    # GET - show response form
    # Get doctor's availability for next 30 days
    today = timezone.now().date()
    available_dates = []
    
    for i in range(30):
        check_date = today + timedelta(days=i)
        weekday = check_date.weekday()
        
        slots = DoctorAvailability.objects.filter(
            doctor=request.user,
            weekday=weekday,
            is_available=True
        )
        
        if slots.exists():
            available_dates.append({
                'date': check_date,
                'slots': slots
            })
    
    context = {
        'consultation_request': consultation_request,
        'available_dates': available_dates[:10],  # Show next 10 available days
        'today': today,
    }
    return render(request, 'authentication/doctor/respond_to_request.html', context)


@login_required
@doctor_required
def doctor_consultations(request):
    """View all consultations"""
    consultations = Consultation.objects.filter(
        doctor=request.user
    ).select_related('patient').prefetch_related('consultation_token').order_by('-scheduled_datetime')
    
    # Filter by status
    status = request.GET.get('status')
    if status:
        consultations = consultations.filter(status=status)
    
    # Separate upcoming and past
    now = timezone.now()
    upcoming = list(consultations.filter(scheduled_datetime__gte=now, status='scheduled'))
    past = list(consultations.filter(Q(scheduled_datetime__lt=now) | ~Q(status='scheduled')))
    
    # Attach token to each consultation for template access
    for c in upcoming + past:
        try:
            c.token = c.consultation_token
        except Exception:
            c.token = None
    
    context = {
        'upcoming_consultations': upcoming,
        'past_consultations': past,
        'selected_status': status,
    }
    return render(request, 'authentication/doctor/consultations_list.html', context)


@login_required
@doctor_required
def consultation_detail(request, consultation_id):
    """View consultation details"""
    consultation = get_object_or_404(
        Consultation.objects.prefetch_related('consultation_token'),
        id=consultation_id,
        doctor=request.user
    )
    
    # Attach token for template access
    try:
        consultation.token = consultation.consultation_token
    except Exception:
        consultation.token = None
    
    if request.method == 'POST':
        # Update consultation notes
        doctor_notes = request.POST.get('doctor_notes', '')
        prescription = request.POST.get('prescription', '')
        
        consultation.doctor_notes = doctor_notes
        consultation.prescription = prescription
        
        if request.POST.get('mark_completed'):
            consultation.status = 'completed'
            consultation.completed_at = timezone.now()
            consultation.save()
            messages.success(request, 'Consultation marked as completed successfully.')
            return redirect('doctor_consultation_detail', consultation_id=consultation_id)
        
        consultation.save()
        messages.success(request, 'Consultation updated successfully.')
        return redirect('doctor_consultation_detail', consultation_id=consultation_id)
    
    context = {
        'consultation': consultation,
    }
    return render(request, 'authentication/doctor/consultation_detail.html', context)


from django.db.models import Q
