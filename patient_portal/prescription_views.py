"""
Prescription Views for Doctor and Patient
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, FileResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from .prescription_models import Prescription, PrescriptionMedicine
from .consultation_models import Consultation
from patient_portal.consultation_views import doctor_required, patient_required
import json
import logging

logger = logging.getLogger(__name__)


@login_required
@doctor_required
def create_prescription(request, consultation_id):
    """Create prescription for a completed consultation - multiple prescriptions allowed"""
    consultation = get_object_or_404(
        Consultation,
        id=consultation_id,
        doctor=request.user
    )
    
    if request.method == 'POST':
        # Create prescription
        prescription = Prescription.objects.create(
            consultation=consultation,
            patient=consultation.patient,
            doctor=request.user,
            diagnosis=request.POST.get('diagnosis', ''),
            symptoms=request.POST.get('symptoms', ''),
            doctor_notes=request.POST.get('doctor_notes', ''),
            follow_up_instructions=request.POST.get('follow_up_instructions', '')
        )
        
        # Add medicines
        medicine_data = json.loads(request.POST.get('medicines_json', '[]'))
        for idx, med in enumerate(medicine_data):
            PrescriptionMedicine.objects.create(
                prescription=prescription,
                medicine_name=med['name'],
                dosage=med['dosage'],
                frequency=med['frequency'],
                timing=med['timing'],
                duration_days=int(med['duration']),
                instructions=med.get('instructions', ''),
                order=idx
            )
        
        messages.success(request, 'Prescription created successfully.')
        return redirect('patient_portal:generate_prescription_pdf', prescription_id=prescription.id)
    
    context = {
        'consultation': consultation,
    }
    return render(request, 'patient_portal/prescription/create_prescription.html', context)


@login_required
@doctor_required
def edit_prescription(request, prescription_id):
    """Edit prescription - DISABLED: Prescriptions are immutable once created"""
    prescription = get_object_or_404(
        Prescription,
        id=prescription_id,
        doctor=request.user
    )
    
    messages.error(request, 'Prescriptions cannot be edited once created. Please create a new prescription if needed.')
    return redirect('patient_portal:view_prescription', prescription_id=prescription.id)


@login_required
def generate_prescription_pdf(request, prescription_id):
    """Generate PDF for prescription with blockchain verification"""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    
    # Check permissions
    if request.user not in [prescription.doctor, prescription.patient]:
        messages.error(request, 'Access denied.')
        return redirect('/')
    
    from .prescription_pdf import generate_prescription_pdf as create_pdf, generate_qr_code
    from django.urls import reverse
    
    # Step 1: Generate verification URL and QR code
    verification_url = request.build_absolute_uri(
        reverse('patient_portal:verify_prescription', args=[prescription.id])
    )
    qr_code_file = generate_qr_code(verification_url, prescription.id)
    prescription.qr_code = qr_code_file
    prescription.save()
    
    # Step 2: Generate PDF WITH QR code (this is the final version users will download)
    pdf_file, pdf_hash = create_pdf(prescription, include_qr=True)
    
    # Save PDF and hash
    prescription.pdf_file = pdf_file
    prescription.pdf_hash = pdf_hash
    prescription.save()
    
    # Step 3: Store on blockchain (using the hash of the PDF WITH QR)
    if settings.BLOCKCHAIN_ENABLED:
        from blockchain.blockchain_service import store_prescription_hash
        try:
            result = store_prescription_hash(
                prescription_id=prescription.id,
                pdf_hash=pdf_hash,
                patient_id=prescription.patient.id,
                doctor_id=prescription.doctor.id
            )
            if result and result.get('success'):
                prescription.blockchain_tx_hash = result['transaction_hash']
                prescription.is_verified = True
                prescription.save()
                logger.info(f"Prescription {prescription.id} stored on blockchain: {result['transaction_hash']}")
            else:
                logger.warning(f"Failed to store prescription on blockchain: {result}")
        except Exception as e:
            logger.error(f"Blockchain error: {e}")
    
    messages.success(request, 'Prescription PDF generated successfully with blockchain verification.')
    return redirect('patient_portal:view_prescription', prescription_id=prescription.id)


@login_required
def view_prescription(request, prescription_id):
    """View prescription details"""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    
    # Check permissions
    if request.user not in [prescription.doctor, prescription.patient]:
        messages.error(request, 'Access denied.')
        return redirect('/')
    
    context = {
        'prescription': prescription,
        'medicines': prescription.medicines.all()
    }
    return render(request, 'patient_portal/prescription/view_prescription.html', context)


@login_required
def download_prescription(request, prescription_id):
    """Download prescription PDF"""
    prescription = get_object_or_404(Prescription, id=prescription_id)
    
    # Check permissions
    if request.user not in [prescription.doctor, prescription.patient]:
        return HttpResponse('Access denied', status=403)
    
    if not prescription.pdf_file:
        messages.error(request, 'PDF not generated yet.')
        return redirect('patient_portal:view_prescription', prescription_id=prescription.id)
    
    response = FileResponse(
        prescription.pdf_file.open('rb'),
        content_type='application/pdf'
    )
    response['Content-Disposition'] = f'attachment; filename="prescription_{prescription.id}.pdf"'
    return response


def verify_prescription(request, prescription_id):
    """Public verification page for prescription"""
    try:
        prescription = get_object_or_404(Prescription, id=prescription_id)
        
        # Verify hash against blockchain
        is_valid = False
        blockchain_data = None
        
        if prescription.pdf_hash and settings.BLOCKCHAIN_ENABLED:
            from blockchain.blockchain_service import get_blockchain_service
            service = get_blockchain_service()
            
            if service.is_connected():
                blockchain_data = service.verify_prescription_hash(prescription.pdf_hash)
                if blockchain_data and blockchain_data.get('exists'):
                    is_valid = True
                    logger.info(f"Prescription {prescription.id} verified on blockchain")
                else:
                    logger.warning(f"Prescription {prescription.id} not found on blockchain")
            else:
                logger.warning("Blockchain service not connected for verification")
        
        context = {
            'prescription': prescription,
            'is_valid': is_valid,
            'blockchain_data': blockchain_data,
            'patient_name': f"{prescription.patient.first_name} {prescription.patient.last_name}",
            'doctor_name': f"Dr. {prescription.doctor.first_name} {prescription.doctor.last_name}",
            'issued_date': prescription.created_at,
            'blockchain_verified': is_valid,
            'tx_hash': prescription.blockchain_tx_hash
        }
        return render(request, 'patient_portal/prescription/verify_prescription.html', context)
    except Exception as e:
        return render(request, 'patient_portal/prescription/verify_prescription.html', {
            'error': 'Prescription not found or invalid.'
        })


@login_required
@doctor_required
def verify_uploaded_prescription(request):
    """
    Allow doctors to upload a prescription PDF and verify it against the blockchain.
    This detects if the document has been tampered with.
    Uses hash-based verification when prescription ID is not available.
    """
    verification_result = None
    prescription = None
    
    if request.method == 'POST':
        uploaded_file = request.FILES.get('prescription_pdf')
        prescription_id = request.POST.get('prescription_id', '').strip()
        
        if not uploaded_file:
            messages.error(request, 'Please upload a prescription PDF file.')
            return redirect('patient_portal:verify_uploaded_prescription')
        
        # Validate file type
        if not uploaded_file.name.lower().endswith('.pdf'):
            messages.error(request, 'Please upload a valid PDF file.')
            return redirect('patient_portal:verify_uploaded_prescription')
        
        # Validate file size (max 10MB)
        if uploaded_file.size > 10 * 1024 * 1024:
            messages.error(request, 'File size must be less than 10MB.')
            return redirect('patient_portal:verify_uploaded_prescription')
        
        # Import verification utilities
        from .prescription_verification import (
            verify_prescription_pdf, 
            get_prescription_by_id_from_pdf,
            compute_pdf_hash,
            extract_pdf_content
        )
        from blockchain.blockchain_service import get_blockchain_service
        
        # Compute hash of uploaded file for logging
        pdf_content = extract_pdf_content(uploaded_file)
        uploaded_file.seek(0)  # Reset file pointer
        uploaded_hash = compute_pdf_hash(pdf_content)
        logger.info(f"=== VERIFICATION START ===")
        logger.info(f"Uploaded file hash: {uploaded_hash}")
        
        # Try to get prescription by ID or extract from PDF
        if not prescription_id:
            # Try to extract prescription ID from PDF
            prescription_id = get_prescription_by_id_from_pdf(uploaded_file)
            uploaded_file.seek(0)  # Reset file pointer
            if prescription_id:
                logger.info(f"Extracted prescription ID from PDF: {prescription_id}")
        
        # Try to find prescription by ID first
        if prescription_id:
            try:
                prescription = Prescription.objects.get(id=prescription_id)
                logger.info(f"Found prescription by ID: {prescription_id}")
                logger.info(f"Stored hash in DB: {prescription.pdf_hash}")
            except (Prescription.DoesNotExist, ValueError):
                logger.warning(f"Prescription with ID {prescription_id} not found in database")
                # Don't error out yet, we'll try hash-based lookup
        
        # If prescription not found by ID, try hash-based verification
        if not prescription:
            logger.info("Attempting hash-based verification via blockchain")
            
            # Query blockchain to see if this hash exists
            blockchain_service = get_blockchain_service()
            if blockchain_service.is_connected():
                blockchain_data = blockchain_service.verify_prescription_hash(uploaded_hash)
                
                if blockchain_data and blockchain_data.get('exists'):
                    # Hash found on blockchain! Try to find prescription in database
                    blockchain_prescription_id = blockchain_data.get('prescription_id')
                    logger.info(f"Hash found on blockchain! Prescription ID: {blockchain_prescription_id}")
                    
                    if blockchain_prescription_id:
                        try:
                            prescription = Prescription.objects.get(pdf_hash=uploaded_hash)
                            logger.info(f"Found prescription by hash: {prescription.id}")
                        except Prescription.DoesNotExist:
                            # Hash exists on blockchain but not in our database
                            # This is still a valid verification
                            verification_result = {
                                'verified': True,
                                'method': 'blockchain_hash',
                                'hash_match': True,
                                'uploaded_hash': uploaded_hash,
                                'blockchain_data': blockchain_data,
                                'details': {
                                    'message': 'Prescription verified on blockchain',
                                    'prescription_id': blockchain_prescription_id,
                                    'timestamp': blockchain_data.get('timestamp'),
                                    'doctor_hash': blockchain_data.get('doctor_hash'),
                                    'patient_hash': blockchain_data.get('patient_hash'),
                                },
                                'warnings': ['Prescription found on blockchain but not in local database. This is a valid prescription.']
                            }
                            
                            context = {
                                'verification_result': verification_result,
                                'prescription': None,
                                'blockchain_verified': True
                            }
                            return render(request, 'authentication/doctor/verify_prescription.html', context)
                    else:
                        messages.warning(request, 'Prescription hash verified on blockchain but prescription ID not available.')
                else:
                    # Hash not found on blockchain
                    logger.warning(f"Hash not found on blockchain: {uploaded_hash}")
                    messages.error(request, 'This prescription is NOT verified. The document hash does not exist on the blockchain. This may be a fake or tampered prescription.')
                    verification_result = {
                        'verified': False,
                        'method': 'hash_not_found',
                        'hash_match': False,
                        'uploaded_hash': uploaded_hash,
                        'details': {'message': 'Prescription hash not found on blockchain'},
                        'warnings': ['This prescription is not registered on the blockchain. It may be fraudulent.']
                    }
                    
                    context = {
                        'verification_result': verification_result,
                        'prescription': None,
                    }
                    return render(request, 'authentication/doctor/verify_prescription.html', context)
            else:
                messages.error(request, 'Blockchain service is not available. Cannot verify prescription.')
                return redirect('patient_portal:verify_uploaded_prescription')
        
        # If we still don't have a prescription, show error
        if not prescription:
            messages.error(request, 'Could not determine prescription ID and hash-based lookup failed. Please enter the prescription ID manually.')
            return redirect('patient_portal:verify_uploaded_prescription')
        
        # Perform detailed verification with the prescription
        verification_result = verify_prescription_pdf(uploaded_file, prescription)
        
        # Log the verification attempt
        logger.info(f"Prescription verification attempted by {request.user.username}: "
                   f"Prescription {prescription.id}, Result: {verification_result['verified']}")
    
    context = {
        'verification_result': verification_result,
        'prescription': prescription,
        'contract_address': getattr(settings, 'PRESCRIPTION_CONTRACT_ADDRESS', ''),
    }
    return render(request, 'authentication/doctor/verify_prescription.html', context)
