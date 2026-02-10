from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import GovernmentScheme, InsurancePolicy, Application, Eligibility
from authentication.supabase_storage import SupabaseStorage
from .document_validator import get_validator
import json
import uuid
import razorpay


def landing_page(request):
    """Main landing page for insurance platform"""
    # Get featured schemes and policies
    featured_schemes = GovernmentScheme.objects.filter(is_active=True)[:6]
    featured_policies = InsurancePolicy.objects.filter(is_active=True)[:6]
    
    # Get user's applications if logged in
    my_applications = []
    if request.user.is_authenticated:
        my_applications = Application.objects.filter(
            user=request.user,
            status__in=['submitted', 'under_review', 'approved']
        ).select_related('policy', 'scheme').order_by('-created_at')
    
    context = {
        'featured_schemes': featured_schemes,
        'featured_policies': featured_policies,
        'my_applications': my_applications,
    }
    return render(request, 'Insurance_SIP/landing.html', context)


def government_schemes(request):
    """Government schemes listing page"""
    schemes = GovernmentScheme.objects.filter(is_active=True)
    
    # Filters
    scheme_type = request.GET.get('type')
    state = request.GET.get('state')
    search = request.GET.get('search')
    
    if scheme_type:
        schemes = schemes.filter(scheme_type=scheme_type)
    if state:
        schemes = schemes.filter(state=state)
    if search:
        schemes = schemes.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search)
        )
    
    context = {
        'schemes': schemes,
        'scheme_types': GovernmentScheme.SCHEME_TYPES,
    }
    return render(request, 'Insurance_SIP/government_schemes.html', context)


def scheme_detail(request, scheme_id):
    """Scheme detail page"""
    scheme = get_object_or_404(GovernmentScheme, id=scheme_id)
    
    try:
        eligibility = scheme.eligibility_criteria
    except Eligibility.DoesNotExist:
        eligibility = None
    
    # Get user's existing application for this scheme if authenticated
    user_application = None
    if request.user.is_authenticated:
        user_application = Application.objects.filter(
            user=request.user,
            scheme=scheme
        ).order_by('-created_at').first()
    
    context = {
        'scheme': scheme,
        'eligibility': eligibility,
        'user_application': user_application,
    }
    return render(request, 'Insurance_SIP/scheme_detail.html', context)


def insurance_policies(request):
    """Insurance policies listing page"""
    policies = InsurancePolicy.objects.filter(is_active=True)
    
    # Filters
    policy_type = request.GET.get('type')
    search = request.GET.get('search')
    
    if policy_type:
        policies = policies.filter(policy_type=policy_type)
    if search:
        policies = policies.filter(
            Q(name__icontains=search) | 
            Q(description__icontains=search)
        )
    
    context = {
        'policies': policies,
        'policy_types': InsurancePolicy.POLICY_TYPES,
    }
    return render(request, 'Insurance_SIP/insurance_policies.html', context)


def policy_detail(request, policy_id):
    """Policy detail page"""
    policy = get_object_or_404(InsurancePolicy, id=policy_id)
    
    context = {
        'policy': policy,
    }
    return render(request, 'Insurance_SIP/policy_detail.html', context)


@login_required
def apply_scheme(request, scheme_id):
    """Apply for government scheme"""
    scheme = get_object_or_404(GovernmentScheme, id=scheme_id)
    
    if request.method == 'POST':
        application = Application.objects.create(
            user=request.user,
            scheme=scheme,
            applicant_name=request.POST.get('name'),
            applicant_age=request.POST.get('age'),
            applicant_income=request.POST.get('income'),
            applicant_state=request.POST.get('state'),
            status='submitted'
        )
        messages.success(request, f'Application {application.application_id} submitted successfully!')
        return redirect('insurance:track_application', application_id=application.application_id)
    
    context = {
        'scheme': scheme,
    }
    return render(request, 'Insurance_SIP/apply_scheme.html', context)


@login_required
def apply_policy(request, policy_id):
    """Apply for insurance policy with document uploads to Supabase and OCR validation"""
    policy = get_object_or_404(InsurancePolicy, id=policy_id)
    
    if request.method == 'POST':
        try:
            # Initialize OCR validator
            validator = get_validator()
            
            # Initialize Supabase storage
            storage = SupabaseStorage(bucket_name='documents')
            
            # Upload documents to Supabase
            documents_uploaded = {}
            validation_errors = []
            
            # Required documents with validation types
            document_fields = {
                'aadhaar': ('Aadhaar Card', 'aadhaar'),
                'pan': ('PAN Card', 'pan'),
                'income_proof': ('Income Proof', 'income_proof'),
                'medical_records': ('Medical Records', 'medical_records')
            }
            
            for field_name, (display_name, validation_type) in document_fields.items():
                file = request.FILES.get(field_name)
                if file:
                    # Validate document using OCR
                    is_valid, validation_message = validator.validate_document(validation_type, file)
                    
                    if not is_valid:
                        validation_errors.append(f"{display_name}: {validation_message}")
                        continue
                    
                    # Create unique file path
                    ext = file.name.split('.')[-1]
                    file_path = f"insurance/{request.user.id}/{uuid.uuid4().hex[:8]}_{field_name}.{ext}"
                    
                    # Reset file pointer after OCR validation
                    file.seek(0)
                    
                    # Save to Supabase
                    saved_path = storage.save(file_path, file)
                    file_url = storage.url(saved_path)
                    
                    documents_uploaded[field_name] = {
                        'name': display_name,
                        'path': saved_path,
                        'url': file_url,
                        'uploaded_at': str(uuid.uuid1().time),
                        'validated': True,
                        'validation_message': validation_message
                    }
            
            # If there are validation errors, show them to the user
            if validation_errors:
                for error in validation_errors:
                    messages.error(request, error)
                return render(request, 'Insurance_SIP/apply_policy.html', {'policy': policy})
            
            # Create application (initially as draft)
            application = Application.objects.create(
                user=request.user,
                policy=policy,
                applicant_name=request.POST.get('applicant_name'),
                applicant_age=request.POST.get('applicant_age'),
                applicant_income=request.POST.get('applicant_income'),
                applicant_state=request.POST.get('applicant_state'),
                documents_uploaded=documents_uploaded,
                notes=request.POST.get('notes', ''),
                status='draft'
            )
            
            messages.success(request, 'All documents validated successfully!')
            
            # Redirect to payment page
            return redirect('insurance:payment', application_id=application.application_id)
            
        except Exception as e:
            messages.error(request, f'Error submitting application: {str(e)}')
            return render(request, 'Insurance_SIP/apply_policy.html', {'policy': policy})
    
    context = {
        'policy': policy,
    }
    return render(request, 'Insurance_SIP/apply_policy.html', context)


@login_required
def track_application(request, application_id=None):
    """Track application status"""
    if application_id:
        application = get_object_or_404(Application, application_id=application_id, user=request.user)
        context = {
            'application': application,
        }
        return render(request, 'Insurance_SIP/application_detail.html', context)
    else:
        applications = Application.objects.filter(user=request.user).order_by('-created_at')
        context = {
            'applications': applications,
        }
        return render(request, 'Insurance_SIP/track_applications.html', context)


def check_eligibility(request):
    """Check eligibility for schemes"""
    if request.method == 'POST':
        age = int(request.POST.get('age', 0))
        income = float(request.POST.get('income', 0))
        state = request.POST.get('state', '')
        
        # Find eligible schemes
        eligible_schemes = []
        schemes = GovernmentScheme.objects.filter(is_active=True)
        
        for scheme in schemes:
            try:
                eligibility = scheme.eligibility_criteria
                if (eligibility.min_age <= age <= eligibility.max_age and
                    (not eligibility.max_income or income <= eligibility.max_income) and
                    (not eligibility.state or eligibility.state == state)):
                    eligible_schemes.append(scheme)
            except Eligibility.DoesNotExist:
                pass
        
        context = {
            'eligible_schemes': eligible_schemes,
            'age': age,
            'income': income,
            'state': state,
        }
        return render(request, 'Insurance_SIP/eligibility_results.html', context)
    
    return render(request, 'Insurance_SIP/check_eligibility.html')


@login_required
def payment(request, application_id):
    """Payment page for insurance policy"""
    application = get_object_or_404(Application, application_id=application_id, user=request.user)
    
    # Initialize Razorpay client
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    
    # Calculate amount in paise (Razorpay uses smallest currency unit)
    amount = int(application.policy.premium_per_month * 100)
    
    # Create Razorpay order
    order_data = {
        'amount': amount,
        'currency': 'INR',
        'payment_capture': 1,
        'notes': {
            'application_id': application.application_id,
            'policy_id': str(application.policy.id),
            'user_id': str(request.user.id)
        }
    }
    
    razorpay_order = client.order.create(data=order_data)
    
    context = {
        'application': application,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'razorpay_order_id': razorpay_order['id'],
        'amount': amount,
        'currency': 'INR',
        'user_name': request.user.get_full_name() or request.user.username,
        'user_email': request.user.email,
    }
    
    return render(request, 'Insurance_SIP/payment.html', context)


@csrf_exempt
def payment_callback(request):
    """Handle Razorpay payment callback"""
    if request.method == 'POST':
        try:
            # Get payment details
            payment_id = request.POST.get('razorpay_payment_id')
            order_id = request.POST.get('razorpay_order_id')
            signature = request.POST.get('razorpay_signature')
            
            # Initialize Razorpay client
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            
            # Verify payment signature
            params_dict = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            
            client.utility.verify_payment_signature(params_dict)
            
            # Get application ID from order
            order = client.order.fetch(order_id)
            application_id = order['notes']['application_id']
            
            # Update application status
            application = Application.objects.get(application_id=application_id)
            application.status = 'submitted'
            application.save()
            
            messages.success(request, 'Payment successful! Your application has been submitted.')
            return redirect('insurance:landing')
            
        except razorpay.errors.SignatureVerificationError:
            messages.error(request, 'Payment verification failed!')
            return redirect('insurance:landing')
        except Exception as e:
            messages.error(request, f'Payment processing error: {str(e)}')
            return redirect('insurance:landing')
    
    return redirect('insurance:landing')
