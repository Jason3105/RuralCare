"""
Medicine Identifier Views
Handles medicine image upload, processing, and result display
Only accessible to patients
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods, require_POST
from django.conf import settings
from django.core.paginator import Paginator
from django.utils import timezone
from functools import wraps
import os
import json
import tempfile
import time
import numpy as np

from .models import MedicineIdentification, MedicineDatabase
from .image_analyzer import MedicineImageAnalyzer
from .groq_medicine_service import GroqMedicineIdentifier


def patient_required(view_func):
    """Decorator to ensure only patients can access the view"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to access this feature.')
            return redirect('patient_login')
        if request.user.user_type != 'patient':
            messages.error(request, 'This feature is only available to patients.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def convert_to_json_serializable(obj):
    """Convert numpy types and other non-serializable types to JSON-serializable Python types"""
    if isinstance(obj, dict):
        return {k: convert_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    elif isinstance(obj, (np.bool_, )):
        return bool(obj)
    elif isinstance(obj, (np.integer, )):
        return int(obj)
    elif isinstance(obj, (np.floating, )):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj


@patient_required
def upload_medicine_image(request):
    """View for uploading medicine images for identification - Patients only"""
    if request.method == 'POST':
        if 'image' not in request.FILES:
            messages.error(request, 'Please select an image file.')
            return redirect('medicine_identifier:upload')
        
        image_file = request.FILES['image']
        
        # Validate file type - check both extension and content type
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tiff', '.tif', '.gif']
        allowed_content_types = [
            'image/jpeg', 'image/jpg', 'image/png', 'image/bmp', 
            'image/webp', 'image/tiff', 'image/gif', 'image/pjpeg'
        ]
        
        file_ext = os.path.splitext(image_file.name)[1].lower() if image_file.name else ''
        content_type = image_file.content_type.lower() if image_file.content_type else ''
        
        # Accept if either extension OR content type is valid
        ext_valid = file_ext in allowed_extensions
        content_valid = content_type in allowed_content_types
        
        if not ext_valid and not content_valid:
            messages.error(request, f'Invalid file type. Please upload an image file (JPG, PNG, etc.). Detected: {file_ext or "no extension"}, {content_type or "unknown type"}')
            return redirect('medicine_identifier:upload')
        
        # Validate file size (max 10MB)
        if image_file.size > 10 * 1024 * 1024:
            messages.error(request, 'File size too large. Maximum allowed size is 10MB.')
            return redirect('medicine_identifier:upload')
        
        # Create identification record
        identification = MedicineIdentification.objects.create(
            user=request.user,
            image=image_file,
            original_filename=image_file.name,
            status='processing'
        )
        
        # Process the image
        try:
            start_time = time.time()
            
            # Get image path
            try:
                image_path = identification.image.path
            except NotImplementedError:
                # Cloud storage - download to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                    identification.image.seek(0)
                    tmp_file.write(identification.image.read())
                    image_path = tmp_file.name
            
            # Step 1: OpenCV + OCR Analysis
            image_analyzer = MedicineImageAnalyzer()
            analysis_results = image_analyzer.analyze_image(image_path)
            
            # Convert numpy types to Python native types for JSON serialization
            analysis_results = convert_to_json_serializable(analysis_results)
            
            # Check if the image is a valid medicine image
            is_valid_medicine = analysis_results.get('is_valid_medicine_image', True)
            medicine_confidence = analysis_results.get('medicine_confidence_score', 0.5)
            validation_reason = analysis_results.get('validation_reason', '')
            validation_suggestions = analysis_results.get('validation_suggestions', [])
            
            identification.extracted_text = analysis_results.get('extracted_text', '')
            identification.ocr_confidence = float(analysis_results.get('ocr_confidence', 0.0))
            identification.image_analysis = analysis_results.get('visual_analysis', {})
            
            # Step 2: AI-powered medicine identification
            groq_service = GroqMedicineIdentifier()
            
            # Build detected info with filename hint if OCR failed
            detected_info = analysis_results.get('detected_medicine_info', {})
            extracted_text = analysis_results.get('cleaned_text', '')
            
            # If OCR failed, try to extract hints from filename
            if not extracted_text or len(extracted_text.strip()) < 5:
                filename_hint = os.path.splitext(image_file.name)[0]
                # Clean filename: replace underscores/dashes with spaces
                filename_hint = filename_hint.replace('_', ' ').replace('-', ' ')
                detected_info['filename_hint'] = filename_hint
                extracted_text = f"Filename suggests: {filename_hint}"
            
            ai_results = groq_service.identify_medicine(
                extracted_text=extracted_text,
                image_analysis=analysis_results.get('visual_analysis', {}),
                detected_info=detected_info
            )
            
            # Convert AI results to ensure JSON serialization
            ai_results = convert_to_json_serializable(ai_results)
            
            # Check if AI also detected non-medicine image
            ai_detected_not_medicine = ai_results.get('is_not_medicine', False)
            ai_invalid_reason = ai_results.get('invalid_image_reason', '')
            
            # Combine validation results
            if not is_valid_medicine or ai_detected_not_medicine:
                # This is not a valid medicine image
                identification.ai_analysis = {
                    'identification_successful': False,
                    'is_not_medicine': True,
                    'invalid_image_reason': ai_invalid_reason or validation_reason,
                    'validation_suggestions': validation_suggestions,
                    'medicine_confidence_score': medicine_confidence,
                    'safety_disclaimer': "Please upload a clear image of actual medicine packaging, tablets, or medicine bottles for accurate identification."
                }
                identification.status = 'invalid_image'
                identification.identification_confidence = 0.0
                identification.error_message = validation_reason or ai_invalid_reason or "The uploaded image does not appear to be a medicine. Please upload a valid medicine image."
                identification.processing_time_seconds = time.time() - start_time
                identification.save()
                
                # Clean up temp file if created
                if 'tmp_file' in dir() and os.path.exists(image_path) and image_path.startswith(tempfile.gettempdir()):
                    try:
                        os.unlink(image_path)
                    except:
                        pass
                
                messages.warning(request, 'The uploaded image does not appear to be a medicine. Please upload a valid medicine image.')
                return redirect('medicine_identifier:result', identification_id=identification.id)
            
            # Update identification with results
            identification.ai_analysis = ai_results
            
            if ai_results.get('identification_successful'):
                identification.medicine_name = ai_results.get('medicine_name')
                identification.generic_name = ai_results.get('generic_name')
                identification.brand_name = ai_results.get('brand_name')
                identification.manufacturer = ai_results.get('manufacturer')
                identification.drug_class = ai_results.get('drug_class')
                identification.strength = ai_results.get('strength')
                identification.description = ai_results.get('description')
                identification.dosage_instructions = ai_results.get('dosage_instructions')
                identification.storage_instructions = ai_results.get('storage_instructions')
                identification.prescription_required = ai_results.get('prescription_required')
                
                # Lists
                identification.uses = ai_results.get('uses', [])
                identification.warnings = ai_results.get('warnings', [])
                identification.contraindications = ai_results.get('contraindications', [])
                identification.drug_interactions = ai_results.get('drug_interactions', [])
                identification.active_ingredients = ai_results.get('active_ingredients', [])
                identification.inactive_ingredients = ai_results.get('inactive_ingredients', [])
                
                # Side effects - flatten if nested
                side_effects = ai_results.get('side_effects', {})
                if isinstance(side_effects, dict):
                    all_effects = []
                    for category, effects in side_effects.items():
                        if isinstance(effects, list):
                            all_effects.extend([f"{category.title()}: {e}" for e in effects])
                    identification.side_effects = all_effects
                else:
                    identification.side_effects = side_effects if isinstance(side_effects, list) else []
                
                # Detect medicine form
                form = ai_results.get('medicine_form', 'unknown')
                if form in dict(MedicineIdentification.MEDICINE_FORM_CHOICES):
                    identification.medicine_form = form
                
                # Confidence
                confidence_map = {'high': 0.9, 'medium': 0.7, 'low': 0.4}
                identification.identification_confidence = confidence_map.get(
                    ai_results.get('confidence_level', 'low'), 0.4
                )
                
                identification.status = 'completed'
            else:
                identification.status = 'completed'
                identification.identification_confidence = 0.3
            
            # Calculate processing time
            identification.processing_time_seconds = time.time() - start_time
            identification.save()
            
            # Clean up temp file if created
            if 'tmp_file' in dir() and os.path.exists(image_path) and image_path.startswith(tempfile.gettempdir()):
                try:
                    os.unlink(image_path)
                except:
                    pass
            
            messages.success(request, 'Medicine image analyzed successfully!')
            return redirect('medicine_identifier:result', identification_id=identification.id)
            
        except Exception as e:
            identification.status = 'failed'
            identification.error_message = str(e)
            identification.save()
            messages.error(request, f'Error analyzing image: {str(e)}')
            return redirect('medicine_identifier:upload')
    
    # GET request - show upload form
    recent_identifications = MedicineIdentification.objects.filter(
        user=request.user
    ).order_by('-created_at')[:5]
    
    return render(request, 'medicine_identifier/upload.html', {
        'recent_identifications': recent_identifications
    })


@patient_required
def identification_result(request, identification_id):
    """View for displaying identification results - Patients only"""
    identification = get_object_or_404(
        MedicineIdentification,
        id=identification_id,
        user=request.user
    )
    
    return render(request, 'medicine_identifier/result.html', {
        'identification': identification
    })


@patient_required
def identification_history(request):
    """View for displaying user's identification history - Patients only"""
    identifications = MedicineIdentification.objects.filter(
        user=request.user
    ).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(identifications, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'medicine_identifier/history.html', {
        'page_obj': page_obj,
        'identifications': page_obj
    })


@patient_required
@require_POST
def delete_identification(request, identification_id):
    """Delete an identification record - Patients only"""
    identification = get_object_or_404(
        MedicineIdentification,
        id=identification_id,
        user=request.user
    )
    
    # Delete the image file
    if identification.image:
        try:
            identification.image.delete(save=False)
        except:
            pass
    
    identification.delete()
    messages.success(request, 'Identification record deleted successfully.')
    return redirect('medicine_identifier:history')


@patient_required
def get_more_info(request, identification_id):
    """Get additional information about identified medicine (AJAX) - Patients only"""
    identification = get_object_or_404(
        MedicineIdentification,
        id=identification_id,
        user=request.user
    )
    
    if not identification.medicine_name:
        return JsonResponse({'error': 'Medicine not identified'}, status=400)
    
    groq_service = GroqMedicineIdentifier()
    additional_info = groq_service.get_additional_info(identification.medicine_name)
    
    return JsonResponse(additional_info)


@patient_required
def check_interaction(request):
    """Check drug interaction between two medicines (AJAX) - Patients only"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST request required'}, status=405)
    
    try:
        data = json.loads(request.body)
        medicine1 = data.get('medicine1', '').strip()
        medicine2 = data.get('medicine2', '').strip()
        
        if not medicine1 or not medicine2:
            return JsonResponse({'error': 'Both medicine names required'}, status=400)
        
        groq_service = GroqMedicineIdentifier()
        result = groq_service.check_drug_interaction(medicine1, medicine2)
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@patient_required
def medicine_dashboard(request):
    """Dashboard view showing overview of identifications - Patients only"""
    user_identifications = MedicineIdentification.objects.filter(user=request.user)
    
    stats = {
        'total_identifications': user_identifications.count(),
        'successful_identifications': user_identifications.filter(
            status='completed',
            identification_confidence__gte=0.6
        ).count(),
        'failed_identifications': user_identifications.filter(status='failed').count(),
        'invalid_images': user_identifications.filter(status='invalid_image').count(),
        'recent_medicines': user_identifications.filter(
            status='completed',
            medicine_name__isnull=False
        ).values_list('medicine_name', flat=True).distinct()[:10]
    }
    
    recent_identifications = user_identifications.order_by('-created_at')[:10]
    
    return render(request, 'medicine_identifier/dashboard.html', {
        'stats': stats,
        'recent_identifications': recent_identifications
    })


# API Views for potential mobile app integration
@login_required
@require_POST
def api_identify_medicine(request):
    """API endpoint for medicine identification"""
    if 'image' not in request.FILES:
        return JsonResponse({'error': 'No image provided'}, status=400)
    
    image_file = request.FILES['image']
    
    # Validate - check both extension and content type
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif', '.tiff', '.tif']
    allowed_content_types = [
        'image/jpeg', 'image/jpg', 'image/png', 'image/bmp', 
        'image/webp', 'image/tiff', 'image/gif', 'image/pjpeg'
    ]
    
    file_ext = os.path.splitext(image_file.name)[1].lower() if image_file.name else ''
    content_type = image_file.content_type.lower() if image_file.content_type else ''
    
    if file_ext not in allowed_extensions and content_type not in allowed_content_types:
        return JsonResponse({'error': 'Invalid file type'}, status=400)
    
    if image_file.size > 10 * 1024 * 1024:
        return JsonResponse({'error': 'File too large'}, status=400)
    
    # Create and process
    identification = MedicineIdentification.objects.create(
        user=request.user,
        image=image_file,
        original_filename=image_file.name,
        status='processing'
    )
    
    try:
        start_time = time.time()
        
        # Get image path
        try:
            image_path = identification.image.path
        except NotImplementedError:
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                identification.image.seek(0)
                tmp_file.write(identification.image.read())
                image_path = tmp_file.name
        
        # Analyze
        image_analyzer = MedicineImageAnalyzer()
        analysis_results = image_analyzer.analyze_image(image_path)
        
        # Convert numpy types
        analysis_results = convert_to_json_serializable(analysis_results)
        
        # Check if valid medicine image
        is_valid_medicine = analysis_results.get('is_valid_medicine_image', True)
        validation_reason = analysis_results.get('validation_reason', '')
        validation_suggestions = analysis_results.get('validation_suggestions', [])
        
        groq_service = GroqMedicineIdentifier()
        
        # Build detected info
        detected_info = analysis_results.get('detected_medicine_info', {})
        extracted_text = analysis_results.get('cleaned_text', '')
        
        if not extracted_text or len(extracted_text.strip()) < 5:
            filename_hint = os.path.splitext(image_file.name)[0]
            filename_hint = filename_hint.replace('_', ' ').replace('-', ' ')
            detected_info['filename_hint'] = filename_hint
            extracted_text = f"Filename suggests: {filename_hint}"
        
        ai_results = groq_service.identify_medicine(
            extracted_text=extracted_text,
            image_analysis=analysis_results.get('visual_analysis', {}),
            detected_info=detected_info
        )
        
        # Convert AI results
        ai_results = convert_to_json_serializable(ai_results)
        
        # Check for invalid image
        ai_detected_not_medicine = ai_results.get('is_not_medicine', False)
        
        if not is_valid_medicine or ai_detected_not_medicine:
            identification.status = 'invalid_image'
            identification.error_message = validation_reason or ai_results.get('invalid_image_reason', 'Invalid medicine image')
            identification.ai_analysis = {
                'identification_successful': False,
                'is_not_medicine': True,
                'invalid_image_reason': validation_reason or ai_results.get('invalid_image_reason'),
                'validation_suggestions': validation_suggestions
            }
            identification.save()
            return JsonResponse({
                'success': False,
                'error': 'invalid_image',
                'message': 'The uploaded image does not appear to be a medicine.',
                'reason': validation_reason or ai_results.get('invalid_image_reason'),
                'suggestions': validation_suggestions
            }, status=400)
        
        # Update record
        identification.extracted_text = analysis_results.get('extracted_text', '')
        identification.ocr_confidence = analysis_results.get('ocr_confidence', 0.0)
        identification.image_analysis = analysis_results.get('visual_analysis', {})
        identification.ai_analysis = ai_results
        
        if ai_results.get('identification_successful'):
            identification.medicine_name = ai_results.get('medicine_name')
            identification.generic_name = ai_results.get('generic_name')
            identification.status = 'completed'
        else:
            identification.status = 'completed'
        
        identification.processing_time_seconds = time.time() - start_time
        identification.save()
        
        return JsonResponse({
            'success': True,
            'identification_id': str(identification.id),
            'result': ai_results
        })
        
    except Exception as e:
        identification.status = 'failed'
        identification.error_message = str(e)
        identification.save()
        return JsonResponse({'error': str(e)}, status=500)
