from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .supabase_client import get_supabase_client
from .models import User, PatientProfile, DoctorProfile, DoctorKYC, MedicalRecord
from .forms import DoctorProfileForm, MedicalRecordForm, PatientProfileForm
import json
import os
import re
import threading
from datetime import datetime
from django.conf import settings

from utils.geocoding import get_lat_lng_from_address


def home(request):
    """Home page"""
    if request.user.is_authenticated:
        if request.user.user_type == 'patient':
            return redirect('patient_dashboard')
        elif request.user.user_type == 'doctor':
            return redirect('doctor_dashboard')
    return render(request, 'authentication/home.html')

def login_page(request):
    """Login selection page"""
    if request.user.is_authenticated:
        return redirect('home')
    return render(request, 'authentication/login.html')

def patient_login(request):
    """Patient login page"""
    if request.user.is_authenticated:
        # If user is already logged in as a patient, go to patient dashboard
        if request.user.user_type == 'patient':
            messages.info(request, 'You are already logged in as a patient.')
            return redirect('patient_dashboard')
        # If user is logged in as a doctor, redirect to doctor dashboard
        elif request.user.user_type == 'doctor':
            messages.warning(request, 'You are logged in as a doctor. Please logout first to access patient login.')
            return redirect('doctor_dashboard')
    return render(request, 'authentication/patient_login.html')

def doctor_login(request):
    """Doctor login page"""
    if request.user.is_authenticated:
        # If user is already logged in as a doctor, go to doctor dashboard
        if request.user.user_type == 'doctor':
            messages.info(request, 'You are already logged in as a doctor.')
            return redirect('doctor_dashboard')
        # If user is logged in as a patient, redirect to patient dashboard
        elif request.user.user_type == 'patient':
            messages.warning(request, 'You are logged in as a patient. Please logout first to access doctor login.')
            return redirect('patient_dashboard')
    return render(request, 'authentication/doctor_login.html')

@csrf_exempt
def auth_callback(request):
    """Handle Supabase authentication callback - supports both GET and POST"""
    
    # Handle GET request (OAuth redirect from Supabase)
    if request.method == 'GET':
        # Store the user_type from query params if available
        user_type = request.GET.get('user_type', 'patient')
        
        # Render a page that will handle the hash fragment
        return render(request, 'authentication/auth_callback.html', {
            'user_type': user_type
        })
    
    # Handle POST request (from JavaScript after extracting tokens)
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            access_token = data.get('access_token')
            user_type = data.get('user_type', 'patient')
            
            if not access_token:
                return JsonResponse({'error': 'Missing access token'}, status=400)
            
            # Get user info from Supabase
            supabase = get_supabase_client()
            
            try:
                # Set the session with the access token
                supabase.auth.set_session(access_token, data.get('refresh_token', ''))
                user_response = supabase.auth.get_user(access_token)
            except Exception as e:
                return JsonResponse({'error': f'Supabase error: {str(e)}'}, status=401)
            
            if not user_response or not user_response.user:
                return JsonResponse({'error': 'Invalid token'}, status=401)
            
            supabase_user = user_response.user
            
            # Get or create Django user
            user, created = User.objects.get_or_create(
                supabase_user_id=supabase_user.id,
                defaults={
                    'username': supabase_user.email.split('@')[0] + '_' + user_type,
                    'email': supabase_user.email,
                    'user_type': user_type,
                    'first_name': supabase_user.user_metadata.get('full_name', '').split()[0] if supabase_user.user_metadata.get('full_name') else '',
                    'last_name': ' '.join(supabase_user.user_metadata.get('full_name', '').split()[1:]) if supabase_user.user_metadata.get('full_name') else '',
                    'profile_picture': supabase_user.user_metadata.get('avatar_url', ''),
                }
            )
            
            # If user already exists with a different role, prevent login
            if not created and user.user_type != user_type:
                return JsonResponse({
                    'error': f'This account is registered as a {user.user_type}. Please use the {user.user_type} login.',
                    'redirect_url': f'/login/{user.user_type}/' if user.user_type in ['patient', 'doctor'] else '/login/'
                }, status=403)
            
            # Create profile based on user type if user was just created
            if created:
                if user_type == 'patient':
                    PatientProfile.objects.create(user=user)
                elif user_type == 'doctor':
                    DoctorProfile.objects.create(
                        user=user,
                        license_number=f"TEMP_{user.id}"  # Should be updated later
                    )
            
            # Store tokens in session
            request.session['access_token'] = access_token
            request.session['refresh_token'] = data.get('refresh_token', '')
            request.session['user_type'] = user_type
            
            # Login user
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            
            # Determine redirect URL
            if user_type == 'patient':
                redirect_url = '/patient/dashboard/'
            else:
                redirect_url = '/doctor/dashboard/'
            
            return JsonResponse({
                'success': True,
                'redirect_url': redirect_url
            })
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

def logout_view(request):
    """Logout user"""
    try:
        # Sign out from Supabase
        access_token = request.session.get('access_token')
        if access_token:
            supabase = get_supabase_client()
            supabase.auth.sign_out()
    except:
        pass
    
    # Clear session
    request.session.flush()
    
    # Logout from Django
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')

def patient_dashboard(request):
    """Patient dashboard - dynamic view with all patient data"""
    if not request.user.is_authenticated or request.user.user_type != 'patient':
        return redirect('patient_login')
    
    from cancer_detection.models import CancerImageAnalysis, PersonalizedTreatmentPlan
    
    # Fetch patient data
    patient_profile = PatientProfile.objects.filter(user=request.user).first()
    cancer_analyses = CancerImageAnalysis.objects.filter(user=request.user).order_by('-created_at')
    treatment_plans = PersonalizedTreatmentPlan.objects.filter(patient=request.user).order_by('-created_at')
    medical_records = MedicalRecord.objects.filter(patient=request.user).order_by('-created_at')
    
    # Calculate statistics
    total_analyses = cancer_analyses.count()
    analyses_with_tumors = cancer_analyses.filter(tumor_detected=True).count()
    total_treatment_plans = treatment_plans.count()
    active_treatment_plans = treatment_plans.filter(status__in=['active', 'pending_review']).count()
    
    # Get latest 3 analyses
    recent_analyses = cancer_analyses[:3]
    
    # Get latest 3 treatment plans
    recent_treatment_plans = treatment_plans[:3]
    
    # Get latest 3 medical records
    recent_medical_records = medical_records[:3]
    
    # Profile completion percentage
    profile_fields = ['date_of_birth', 'gender', 'blood_group', 'address', 'emergency_contact_name', 
                      'emergency_contact_phone', 'medical_history', 'allergies', 'current_medications']
    completed_fields = 0
    if patient_profile:
        for field in profile_fields:
            if getattr(patient_profile, field, None):
                completed_fields += 1
    profile_completion = (completed_fields / len(profile_fields) * 100) if patient_profile else 0
    
    context = {
        'patient_profile': patient_profile,
        'total_analyses': total_analyses,
        'analyses_with_tumors': analyses_with_tumors,
        'total_treatment_plans': total_treatment_plans,
        'active_treatment_plans': active_treatment_plans,
        'recent_analyses': recent_analyses,
        'recent_treatment_plans': recent_treatment_plans,
        'recent_medical_records': recent_medical_records,
        'all_analyses': cancer_analyses,
        'all_treatment_plans': treatment_plans,
        'profile_completion': int(profile_completion),
        'total_medical_records': medical_records.count(),
    }
    
    return render(request, 'authentication/patient_dashboard.html', context)

def doctor_dashboard(request):
    """Doctor dashboard"""
    if not request.user.is_authenticated or request.user.user_type != 'doctor':
        return redirect('doctor_login')
    
    doctor_profile = DoctorProfile.objects.get(user=request.user)
    
    try:
        kyc = DoctorKYC.objects.get(doctor=doctor_profile)
    except DoctorKYC.DoesNotExist:
        kyc = None
    
    # Get recent consultation requests (last 10)
    from patient_portal.consultation_models import ConsultationRequest, Consultation
    from django.utils import timezone
    from datetime import datetime
    
    recent_requests = ConsultationRequest.objects.filter(
        doctor=request.user
    ).select_related('patient', 'patient__patient_profile').order_by('-requested_at')[:10]
    
    # Get ALL today's scheduled consultations (both past and upcoming)
    today = timezone.now().date()
    now = timezone.now()
    todays_consultations = Consultation.objects.filter(
        doctor=request.user,
        scheduled_datetime__date=today,
        status__in=['scheduled', 'completed', 'in_progress']
    ).select_related('patient', 'patient__patient_profile').order_by('scheduled_datetime')
    
    # Count stats
    total_requests = ConsultationRequest.objects.filter(doctor=request.user).count()
    pending_requests = ConsultationRequest.objects.filter(
        doctor=request.user,
        status='pending'
    ).count()
    todays_count = todays_consultations.count()
    
    # Active cases - consultations that are scheduled or in progress
    active_cases = Consultation.objects.filter(
        doctor=request.user,
        status__in=['scheduled', 'in_progress']
    ).count()
    
    context = {
        'kyc': kyc,
        'doctor_profile': doctor_profile,
        'recent_requests': recent_requests,
        'todays_consultations': todays_consultations,
        'total_requests': total_requests,
        'pending_requests': pending_requests,
        'todays_count': todays_count,
        'active_cases': active_cases,
    }
    
    return render(request, 'authentication/doctor_dashboard.html', context)


def kyc_status(request):
    """Display KYC status for doctor"""
    if not request.user.is_authenticated or request.user.user_type != 'doctor':
        return redirect('doctor_login')
    
    doctor_profile = DoctorProfile.objects.get(user=request.user)
    
    try:
        kyc = DoctorKYC.objects.get(doctor=doctor_profile)
    except DoctorKYC.DoesNotExist:
        kyc = None
    
    context = {
        'kyc': kyc,
        'doctor_profile': doctor_profile
    }
    
    return render(request, 'authentication/kyc_status.html', context)


def kyc_form(request):
    """KYC form for doctors"""
    if not request.user.is_authenticated or request.user.user_type != 'doctor':
        return redirect('doctor_login')
    
    doctor_profile = DoctorProfile.objects.get(user=request.user)
    
    try:
        kyc = DoctorKYC.objects.get(doctor=doctor_profile)
        # If already approved, redirect
        if kyc.status == 'approved':
            messages.info(request, 'Your KYC is already approved.')
            return redirect('doctor_dashboard')
    except DoctorKYC.DoesNotExist:
        kyc = None
    
    if request.method == 'POST':

        clinic_address = ", ".join(filter(None, [
            request.POST.get('residential_address'),
            request.POST.get('city'),
            request.POST.get('state'),
            request.POST.get('postal_code'),
            request.POST.get('country'),
        ]))

        lat, lng = get_lat_lng_from_address(clinic_address)

        # Create or update KYC
        kyc_data = {
            'full_name': request.POST.get('full_name'),
            'date_of_birth': request.POST.get('date_of_birth'),
            'gender': request.POST.get('gender'),
            'nationality': request.POST.get('nationality'),
            'personal_email': request.POST.get('personal_email'),
            'mobile_number': request.POST.get('mobile_number'),
            'residential_address': request.POST.get('residential_address'),
            'city': request.POST.get('city'),
            'state': request.POST.get('state'),
            'postal_code': request.POST.get('postal_code'),
            'country': request.POST.get('country'),

            'clinic_address': clinic_address,
            'clinic_latitude': lat,
            'clinic_longitude': lng,

            'license_number_verified': request.POST.get('license_number_verified'),
            'license_issuing_authority': request.POST.get('license_issuing_authority'),
            'license_issue_date': request.POST.get('license_issue_date') or None,
            'license_expiry_date': request.POST.get('license_expiry_date') or None,
            'medical_degree': request.POST.get('medical_degree'),
            'medical_university': request.POST.get('medical_university'),
            'graduation_year': int(request.POST.get('graduation_year')) if request.POST.get('graduation_year') else None,
            'current_hospital': request.POST.get('current_hospital'),
            'designation': request.POST.get('designation'),
            'department_specialty': request.POST.get('department_specialty'),
            'years_of_practice': int(request.POST.get('years_of_practice')) if request.POST.get('years_of_practice') else None,
            'identity_document_type': request.POST.get('identity_document_type'),
            'identity_document_number': request.POST.get('identity_document_number'),
            'address_proof_type': request.POST.get('address_proof_type'),
            'status': 'pending',
            'submitted_at': datetime.now(),
        }
        
        # Handle file uploads
        if 'license_document' in request.FILES:
            kyc_data['license_document'] = request.FILES['license_document']
        if 'degree_certificate' in request.FILES:
            kyc_data['degree_certificate'] = request.FILES['degree_certificate']
        if 'employment_document' in request.FILES:
            kyc_data['employment_document'] = request.FILES['employment_document']
        if 'identity_document_file' in request.FILES:
            kyc_data['identity_document_file'] = request.FILES['identity_document_file']
        if 'address_proof_file' in request.FILES:
            kyc_data['address_proof_file'] = request.FILES['address_proof_file']
        
        if kyc:
            # Update existing KYC
            for key, value in kyc_data.items():
                if value is not None:
                    setattr(kyc, key, value)
            kyc.save()
        else:
            # Create new KYC
            kyc_data['doctor'] = doctor_profile
            kyc = DoctorKYC.objects.create(**kyc_data)
        
        # Sync KYC data to DoctorProfile
        doctor_profile.gender = kyc.gender
        doctor_profile.date_of_birth = kyc.date_of_birth
        doctor_profile.medical_degree = kyc.medical_degree
        doctor_profile.license_number = kyc.license_number_verified
        doctor_profile.years_of_experience = kyc.years_of_practice
        doctor_profile.specialization = kyc.department_specialty if kyc.department_specialty else doctor_profile.specialization
        doctor_profile.hospital_affiliation = kyc.current_hospital
        doctor_profile.city = kyc.city
        doctor_profile.state = kyc.state
        doctor_profile.pincode = kyc.postal_code
        doctor_profile.country = kyc.country
        
        doctor_profile.clinic_address = clinic_address
        doctor_profile.clinic_latitude = lat
        doctor_profile.clinic_longitude = lng

        doctor_profile.clinic_address = kyc.residential_address
        doctor_profile.profile_completed = True
        doctor_profile.save()

        lat, lng = get_lat_lng_from_address(clinic_address)
        
        # Update user phone number
        request.user.phone_number = kyc.mobile_number
        request.user.save()
        
        messages.success(request, 'KYC information submitted successfully. Your application is under review.')
        return redirect('kyc_status')
    
    context = {
        'kyc': kyc,
        'doctor_profile': doctor_profile,
        'gender_choices': [('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
        'identity_doc_types': [('passport', 'Passport'), ('aadhaar', 'Aadhaar'), ('national_id', 'National ID'), ('driving_license', 'Driving License')],
        'address_proof_types': [('utility_bill', 'Utility Bill'), ('rental_agreement', 'Rental Agreement'), ('property_deed', 'Property Deed'), ('bank_statement', 'Bank Statement')],
    }
    
    return render(request, 'authentication/kyc_form.html', context)


def kyc_preview(request):
    """Preview submitted KYC"""
    if not request.user.is_authenticated or request.user.user_type != 'doctor':
        return redirect('doctor_login')
    
    doctor_profile = DoctorProfile.objects.get(user=request.user)
    
    try:
        kyc = DoctorKYC.objects.get(doctor=doctor_profile)
    except DoctorKYC.DoesNotExist:
        messages.error(request, 'No KYC found. Please complete your KYC first.')
        return redirect('kyc_form')
    
    context = {
        'kyc': kyc,
        'doctor_profile': doctor_profile,
    }
    
    return render(request, 'authentication/kyc_preview.html', context)


def doctor_profile_edit(request):
    """Edit doctor profile"""
    if not request.user.is_authenticated or request.user.user_type != 'doctor':
        messages.error(request, 'Please login as a doctor to access this page.')
        return redirect('doctor_login')
    
    try:
        doctor_profile = DoctorProfile.objects.get(user=request.user)
    except DoctorProfile.DoesNotExist:
        messages.error(request, 'Profile not found.')
        return redirect('doctor_dashboard')
    
    if request.method == 'POST':
        form = DoctorProfileForm(request.POST, instance=doctor_profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('doctor_dashboard')
    else:
        form = DoctorProfileForm(instance=doctor_profile)
    
    return render(request, 'authentication/doctor_profile_edit.html', {'form': form})


def patient_profile_edit(request):
    """Edit patient profile"""
    if not request.user.is_authenticated or request.user.user_type != 'patient':
        messages.error(request, 'Please login as a patient to access this page.')
        return redirect('patient_login')
    
    try:
        patient_profile = PatientProfile.objects.get(user=request.user)
    except PatientProfile.DoesNotExist:
        # Create profile if it doesn't exist
        patient_profile = PatientProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        form = PatientProfileForm(request.POST, instance=patient_profile, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('patient_dashboard')
    else:
        form = PatientProfileForm(instance=patient_profile, user=request.user)
    
    return render(request, 'authentication/patient_profile_edit.html', {'form': form})


# Medical Records Views
def medical_records_list(request):
    """List all medical records for the patient"""
    if not request.user.is_authenticated or request.user.user_type != 'patient':
        messages.error(request, 'Please login as a patient to access medical records.')
        return redirect('patient_login')
    
    records = MedicalRecord.objects.filter(patient=request.user).order_by('-created_at')
    
    # Calculate stats
    total_records = records.count()
    completed_records = records.filter(ocr_status='completed').count()
    processing_records = records.filter(ocr_status='processing').count()
    
    context = {
        'records': records,
        'total_records': total_records,
        'completed_records': completed_records,
        'processing_records': processing_records,
    }
    return render(request, 'authentication/medical_records_list.html', context)


def upload_medical_record(request):
    """Upload a new medical record"""
    if not request.user.is_authenticated or request.user.user_type != 'patient':
        messages.error(request, 'Please login as a patient to upload medical records.')
        return redirect('patient_login')
    
    if request.method == 'POST':
        form = MedicalRecordForm(request.POST, request.FILES)
        if form.is_valid():
            record = form.save(commit=False)
            record.patient = request.user
            record.save()
            
            # Start OCR processing in background
            thread = threading.Thread(target=process_ocr, args=(record.id,))
            thread.daemon = True
            thread.start()
            
            messages.success(request, 'Medical record uploaded successfully! OCR processing started.')
            return redirect('medical_record_detail', record_id=record.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = MedicalRecordForm()
    
    return render(request, 'authentication/upload_medical_record.html', {'form': form})


def medical_record_detail(request, record_id):
    """View details of a specific medical record"""
    if not request.user.is_authenticated or request.user.user_type != 'patient':
        messages.error(request, 'Please login as a patient to view medical records.')
        return redirect('patient_login')
    
    try:
        record = MedicalRecord.objects.get(id=record_id, patient=request.user)
    except MedicalRecord.DoesNotExist:
        messages.error(request, 'Medical record not found.')
        return redirect('medical_records_list')
    
    context = {
        'record': record,
    }
    return render(request, 'authentication/medical_record_detail.html', context)


def delete_medical_record(request, record_id):
    """Delete a medical record"""
    if not request.user.is_authenticated or request.user.user_type != 'patient':
        messages.error(request, 'Please login as a patient to delete medical records.')
        return redirect('patient_login')
    
    try:
        record = MedicalRecord.objects.get(id=record_id, patient=request.user)
        
        # Delete the file from storage
        if record.document_file:
            try:
                if os.path.exists(record.document_file.path):
                    os.remove(record.document_file.path)
            except Exception as e:
                print(f"Error deleting file: {e}")
        
        # Delete the record from database
        record_title = record.title
        record.delete()
        
        messages.success(request, f'Medical record "{record_title}" has been deleted successfully.')
    except MedicalRecord.DoesNotExist:
        messages.error(request, 'Medical record not found.')
    
    return redirect('medical_records_list')


def process_ocr(record_id):
    """Process OCR on uploaded medical record"""
    try:
        record = MedicalRecord.objects.get(id=record_id)
        file_path = record.document_file.path
        file_ext = os.path.splitext(file_path)[1].lower()
        
        extracted_text = ""
        
        # Check if Tesseract is available
        try:
            import pytesseract
            from PIL import Image
            tesseract_available = True
        except ImportError:
            tesseract_available = False
            print("Warning: pytesseract not available")
        
        # Process based on file type
        if file_ext == '.pdf':
            # Try PDF text extraction first (faster)
            try:
                import PyPDF2
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    
                    # Check if PDF is encrypted/password protected
                    if pdf_reader.is_encrypted:
                        # Try to decrypt with empty password
                        decryption_result = pdf_reader.decrypt('')
                        if decryption_result == 0:
                            extracted_text = "Error: This PDF is password-protected. Please upload an unprotected version of the document."
                            print("PDF is password protected")
                        else:
                            print("PDF decrypted successfully")
                    
                    # Extract text from pages if not blocked by password
                    if not extracted_text:
                        for page_num, page in enumerate(pdf_reader.pages):
                            page_text = page.extract_text()
                            if page_text.strip():
                                extracted_text += f"\n--- Page {page_num+1} ---\n{page_text}"
                
                # If no text extracted and Tesseract is available, try OCR
                if not extracted_text.strip() and tesseract_available:
                    try:
                        import pdf2image
                        images = pdf2image.convert_from_path(file_path)
                        for i, image in enumerate(images):
                            text = pytesseract.image_to_string(image)
                            extracted_text += f"\n--- Page {i+1} ---\n{text}"
                    except Exception as ocr_error:
                        print(f"OCR error: {ocr_error}")
                        if not extracted_text:
                            extracted_text = f"Could not extract text via OCR. Ensure Poppler and Tesseract are installed."
                        
            except Exception as e:
                error_msg = str(e)
                print(f"Error processing PDF: {error_msg}")
                if not extracted_text:
                    if "PyCryptodome" in error_msg or "AES" in error_msg:
                        extracted_text = "Error: PDF encryption not supported. This should not happen - please restart the server and try again."
                    elif "password" in error_msg.lower():
                        extracted_text = "Error: This PDF is password-protected. Please upload an unprotected version."
                    else:
                        extracted_text = f"Error extracting text from PDF: {error_msg}"
        
        elif file_ext in ['.jpg', '.jpeg', '.png']:
            # Process image with OCR
            if tesseract_available:
                try:
                    from PIL import Image
                    image = Image.open(file_path)
                    extracted_text = pytesseract.image_to_string(image)
                except Exception as e:
                    print(f"Error processing image: {e}")
                    extracted_text = f"Error extracting text from image: {str(e)}\n\nPlease ensure Tesseract OCR is installed."
            else:
                extracted_text = "Tesseract OCR is not installed. Please install pytesseract and Tesseract OCR to process images."
        
        # Extract structured data
        extracted_data = extract_medical_data(extracted_text) if extracted_text else {}
        
        # Update record
        record.extracted_text = extracted_text
        record.extracted_data = extracted_data
        record.ocr_status = 'completed' if extracted_text else 'failed'
        
        # Calculate confidence (simple heuristic)
        if extracted_text and len(extracted_text) > 50:
            record.ocr_confidence = 85.0
        elif extracted_text:
            record.ocr_confidence = 60.0
        else:
            record.ocr_confidence = 0.0
        
        # Try to extract metadata
        if extracted_data:
            if 'hospital_name' in extracted_data:
                record.hospital_name = extracted_data['hospital_name']
            if 'doctor_name' in extracted_data:
                record.doctor_name = extracted_data['doctor_name']
        
        record.save()
        print(f"OCR completed for record {record_id}: {len(extracted_text)} characters extracted")
        
    except Exception as e:
        print(f"OCR Processing Error: {e}")
        import traceback
        traceback.print_exc()
        try:
            record = MedicalRecord.objects.get(id=record_id)
            record.ocr_status = 'failed'
            record.extracted_text = f"Processing failed: {str(e)}"
            record.save()
        except:
            pass


def extract_medical_data(text):
    """Extract structured medical data from OCR text"""
    data = {}
    
    if not text:
        return data
    
    text_lower = text.lower()
    
    # Extract patient name
    name_patterns = [
        r'patient\s*name\s*:?\s*([A-Za-z\s\.]+?)(?:\n|age|gender|date)',
        r'name\s*:?\s*([A-Za-z\s\.]+?)(?:\n|age|gender|date)',
        r'patient\s*:?\s*([A-Za-z\s\.]+?)(?:\n|age|gender)',
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Filter out short or suspicious names
            if len(name) > 2 and not any(char.isdigit() for char in name):
                data['patient_name'] = name
                break
    
    # Extract age
    age_patterns = [
        r'age\s*:?\s*(\d{1,3})',
        r'(\d{1,3})\s*(?:years?|yrs?|y\.o\.)',
    ]
    for pattern in age_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            age = int(match.group(1))
            if 0 < age < 120:  # Valid age range
                data['age'] = str(age)
                break
    
    # Extract gender
    gender_match = re.search(r'gender\s*:?\s*(male|female|m|f)\b', text_lower)
    if gender_match:
        gender = gender_match.group(1).lower()
        data['gender'] = 'Male' if gender in ['male', 'm'] else 'Female'
    elif re.search(r'\b(male|m)\b', text_lower) and not re.search(r'\bfemale\b', text_lower):
        data['gender'] = 'Male'
    elif re.search(r'\b(female|f)\b', text_lower):
        data['gender'] = 'Female'
    
    # Extract date of birth
    dob_patterns = [
        r'(?:date\s*of\s*birth|dob|d\.o\.b\.?)\s*:?\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})',
        r'born\s*:?\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})',
    ]
    for pattern in dob_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['date_of_birth'] = match.group(1).strip()
            break
    
    # Extract report date
    report_date_patterns = [
        r'(?:report\s*date|date)\s*:?\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})',
        r'(?:collected|sample|test)\s*date\s*:?\s*(\d{1,2}[-/\.]\d{1,2}[-/\.]\d{2,4})',
    ]
    for pattern in report_date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['date'] = match.group(1).strip()
            break
    
    # Extract hospital/clinic name
    hospital_patterns = [
        r'hospital\s*:?\s*([A-Za-z0-9\s\-\.,]+?)(?:\n|tel|phone|email|address)',
        r'clinic\s*:?\s*([A-Za-z0-9\s\-\.,]+?)(?:\n|tel|phone|email)',
        r'medical\s*center\s*:?\s*([A-Za-z0-9\s\-\.,]+?)(?:\n|tel|phone)',
    ]
    for pattern in hospital_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            hospital = match.group(1).strip()
            if len(hospital) > 2:
                data['hospital_name'] = hospital[:100]  # Limit length
                break
    
    # Extract doctor name
    doctor_patterns = [
        r'(?:dr\.?|doctor)\s+([A-Za-z\s\.]+?)(?:\n|md|mbbs|physician)',
        r'physician\s*:?\s*([A-Za-z\s\.]+?)(?:\n|$)',
        r'consulting\s*doctor\s*:?\s*([A-Za-z\s\.]+?)(?:\n|$)',
    ]
    for pattern in doctor_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            doctor = match.group(1).strip()
            if len(doctor) > 2:
                data['doctor_name'] = doctor[:50]
                break
    
    # Extract patient ID
    id_patterns = [
        r'(?:patient\s*id|patient\s*no|id\s*no|registration\s*no)\s*:?\s*([A-Za-z0-9\-]+)',
        r'(?:mr\s*no|uhid)\s*:?\s*([A-Za-z0-9\-]+)',
    ]
    for pattern in id_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['patient_id'] = match.group(1).strip()
            break
    
    # Extract test results (improved filtering)
    test_results = {}
    lines = text.split('\n')
    
    # Common medical test parameter keywords
    medical_test_names = [
        'glucose', 'hemoglobin', 'hba1c', 'hgb', 'hct', 'hematocrit',
        'cholesterol', 'ldl', 'hdl', 'vldl', 'triglyceride', 'lipid',
        'creatinine', 'urea', 'bun', 'egfr', 'gfr',
        'sodium', 'potassium', 'chloride', 'bicarbonate', 'calcium', 'magnesium', 'phosphorus',
        'albumin', 'globulin', 'protein', 'bilirubin', 'direct', 'indirect', 'total',
        'sgpt', 'sgot', 'alt', 'ast', 'alp', 'alkaline', 'ggt', 'ldh',
        'amylase', 'lipase', 'cpk', 'troponin', 'bnp', 'nt-pro',
        'wbc', 'rbc', 'platelet', 'neutrophil', 'lymphocyte', 'monocyte', 'eosinophil', 'basophil',
        'esr', 'crp', 'tsh', 't3', 't4', 'ft3', 'ft4', 'cortisol',
        'vitamin', 'b12', 'folate', 'iron', 'ferritin', 'tibc', 'transferrin',
        'uric', 'acid', 'psa', 'cea', 'ca-125', 'ca-19', 'afp',
        'inr', 'pt', 'ptt', 'aptt', 'fibrinogen', 'd-dimer',
        'hbsag', 'anti-hcv', 'hiv', 'vdrl', 'tpha',
        'mcv', 'mch', 'mchc', 'rdw', 'mpv', 'pdw',
        'fasting', 'postprandial', 'random', 'a1c'
    ]
    
    # Words that indicate this is NOT a test result
    exclude_keywords = [
        'email', 'phone', 'tel', 'fax', 'website', 'www', 'http', '@',
        'address', 'street', 'city', 'zip', 'postal',
        'report date', 'collection date', 'receipt date', 'sampling date',
        'patient id', 'patient name', 'your id', 'request code',
        'date of birth', 'age', 'gender', 'physician', 'doctor',
        'page', 'printed', 'generated', 'laboratory', 'hospital',
        'borderline:', 'very high:', 'very low:', 'optimal:', 'normal:',
        'reference range', 'reference value', 'reference interval'
    ]
    
    # Additional patterns that indicate reference ranges, not actual results
    reference_range_patterns = [
        r'^(normal|optimal|borderline|high|low|very high|very low)\s*:',
        r'^(normal|optimal)\s*<',
        r'^\s*<\s*\d+\.?\d*\s*,',  # Starts with < number,
        r'^\s*>\s*\d+\.?\d*\s*,',  # Starts with > number,
    ]
    
    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue
        
        line_lower = line.lower()
        
        # Skip lines with exclude keywords
        if any(keyword in line_lower for keyword in exclude_keywords):
            continue
        
        # Skip reference range patterns
        if any(re.match(pattern, line, re.IGNORECASE) for pattern in reference_range_patterns):
            continue
        
        # Look for test results with colon or tab separator
        if ':' in line or '\t' in line:
            separator = ':' if ':' in line else '\t'
            parts = line.split(separator, 1)
            
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                key_lower = key.lower()
                
                # Skip if key itself is a reference range indicator
                if key_lower in ['normal', 'optimal', 'borderline', 'high', 'low', 'very high', 'very low']:
                    continue
                
                # Check if this is likely a medical test parameter
                is_medical_test = any(test in key_lower for test in medical_test_names)
                
                # Additional criteria: value contains numbers and units
                has_numeric = any(char.isdigit() for char in value)
                has_units = any(unit in value.lower() for unit in ['mg', 'dl', 'mmol', 'g/', 'ml', 'µl', 'ng', 'pg', 'iu', '%', 'cells', 'mm', 'fL', 'sec', 'min'])
                
                # Criteria for valid test results
                if (key and value and 
                    2 < len(key) < 60 and 
                    len(value) < 200 and
                    has_numeric and
                    (is_medical_test or has_units) and
                    not key.isdigit()):
                    
                    test_results[key] = value
    
    # Also try to extract table-like data (parameter | value | range format)
    # Look for lines with multiple values separated by tabs or multiple spaces
    for line in lines:
        line = line.strip()
        if not line or len(line) < 5:
            continue
            
        line_lower = line.lower()
        
        # Skip excluded lines
        if any(keyword in line_lower for keyword in exclude_keywords):
            continue
        
        # Check if line contains medical test name
        if any(test in line_lower for test in medical_test_names):
            # Try to parse table-like format with multiple spaces/tabs
            parts = re.split(r'\s{2,}|\t', line)
            if len(parts) >= 2:
                key = parts[0].strip()
                value = ' '.join(parts[1:]).strip()
                
                if (key and value and 
                    2 < len(key) < 60 and 
                    any(char.isdigit() for char in value) and
                    not key.isdigit() and
                    key not in test_results):  # Avoid duplicates
                    
                    test_results[key] = value
    
    if test_results:
        data['test_results'] = test_results
    
    return data


from django.http import JsonResponse
from .models import DoctorKYC
from utils.location import haversine

@login_required
def nearby_clinics(request):
    """API endpoint returning nearby clinics as JSON"""
    try:
        user_lat = request.GET.get("lat")
        user_lng = request.GET.get("lng")
        
        if not user_lat or not user_lng:
            return JsonResponse({"clinics": [], "error": "Missing lat/lng parameters"}, status=400)
        
        user_lat = float(user_lat)
        user_lng = float(user_lng)
    except (TypeError, ValueError):
        return JsonResponse({"clinics": [], "error": "Invalid lat/lng values"}, status=400)

    clinics = []

    for clinic in DoctorKYC.objects.exclude(
        clinic_latitude=None, clinic_longitude=None
    ):
        distance = haversine(
            user_lat, user_lng,
            clinic.clinic_latitude, clinic.clinic_longitude
        )

        if distance <= 50:  # 50 km radius — generous to always show partner clinics
            clinics.append({
                "name": clinic.full_name,
                "address": clinic.clinic_address or "Address not available",
                "phone": clinic.mobile_number or "",
                "lat": clinic.clinic_latitude,
                "lng": clinic.clinic_longitude,
                "distance": round(distance, 2)
            })
    
    # Sort by distance
    clinics.sort(key=lambda c: c["distance"])

    return JsonResponse({"clinics": clinics})

@login_required
def nearby_clinics_page(request):
    """
    Renders the map page where users can see nearby clinics.
    """
    return render(request, 'authentication/nearby_clinics.html')
