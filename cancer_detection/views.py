from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.conf import settings
from datetime import datetime
import json
import tempfile
from .models import CancerImageAnalysis, PersonalizedTreatmentPlan, HistopathologyReport, GenomicProfile, TreatmentOutcome
from .opencv_analyzer import CancerImageAnalyzer
from .treatment_planner import TreatmentPlanningEngine
from .histopathology_analyzer import HistopathologyAnalyzer
from .genomics_analyzer import GenomicsAnalyzer
from .outcome_predictor import OutcomePredictor
from .groq_analyzer import GroqAnalyzer
from django.utils import timezone
import os
import json

# All views in this module require authentication
# Unauthenticated users will be redirected to LOGIN_URL (patient_login)


@login_required
def upload_image(request):
    """View for uploading cancer images"""
    if request.method == 'POST':
        if 'image' not in request.FILES:
            messages.error(request, 'Please select an image file.')
            return redirect('cancer_detection:upload_image')
        
        image_file = request.FILES['image']
        image_type = request.POST.get('image_type', 'other')
        
        # Validate file type
        allowed_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
        file_ext = os.path.splitext(image_file.name)[1].lower()
        
        if file_ext not in allowed_extensions:
            messages.error(request, f'Invalid file type. Allowed types: {", ".join(allowed_extensions)}')
            return redirect('cancer_detection:upload_image')
        
        # Create analysis record
        analysis = CancerImageAnalysis.objects.create(
            user=request.user,
            image=image_file,
            image_type=image_type,
            original_filename=image_file.name
        )
        
        # Perform analysis
        try:
            analyzer = CancerImageAnalyzer()  # Uses lazy-loaded models
            # Ensure the file is saved before accessing
            if not analysis.image:
                raise ValueError("Image file not saved properly")
            
            # Handle both local and cloud storage
            # Try to get local path first, if not available, download to temp file
            try:
                image_path = analysis.image.path
            except NotImplementedError:
                # Cloud storage - download to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(analysis.image.name)[1]) as tmp_file:
                    # Read from storage and write to temp file
                    analysis.image.seek(0)
                    tmp_file.write(analysis.image.read())
                    image_path = tmp_file.name
            
            results = analyzer.analyze_image(image_path, image_type)
            
            # Clean up temp file if created
            if 'tmp_file' in dir() and os.path.exists(image_path) and image_path.startswith(tempfile.gettempdir()):
                try:
                    os.unlink(image_path)
                except:
                    pass
            
            # Update analysis with results
            analysis.tumor_detected = results.get('tumor_detected', False)
            analysis.tumor_type = results.get('tumor_type')
            analysis.tumor_stage = results.get('tumor_stage')
            analysis.tumor_size_mm = results.get('tumor_size_mm')
            analysis.tumor_location = results.get('tumor_location')
            analysis.genetic_profile = results.get('genetic_profile', {})
            analysis.comorbidities = results.get('comorbidities', [])
            analysis.analysis_data = results.get('detailed_analysis', {})
            analysis.detection_confidence = results.get('detection_confidence', 0.0)
            analysis.stage_confidence = results.get('stage_confidence', 0.0)
            analysis.save()
            
            messages.success(request, 'Image analyzed successfully!')
            return redirect('cancer_detection:analysis_detail', analysis_id=analysis.id)
            
        except Exception as e:
            messages.error(request, f'Error analyzing image: {str(e)}')
            analysis.delete()  # Delete the record if analysis fails
            return redirect('cancer_detection:upload_image')
    
    return render(request, 'cancer_detection/upload_image.html', {
        'image_types': CancerImageAnalysis.IMAGE_TYPE_CHOICES
    })


@login_required
def analysis_list(request):
    """List all analyses for the current user"""
    analyses = CancerImageAnalysis.objects.filter(user=request.user)
    
    # Pagination
    paginator = Paginator(analyses, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'cancer_detection/analysis_list.html', {
        'page_obj': page_obj
    })


@login_required
def analysis_detail(request, analysis_id):
    """View detailed analysis results"""
    analysis = get_object_or_404(CancerImageAnalysis, id=analysis_id, user=request.user)
    
    # Format analysis data for display
    context = {
        'analysis': analysis,
        'genetic_profile': analysis.genetic_profile or {},
        'comorbidities': analysis.comorbidities or [],
        'detailed_analysis': analysis.analysis_data or {},
    }
    
    return render(request, 'cancer_detection/analysis_detail.html', context)


@login_required
@require_http_methods(["DELETE"])
def delete_analysis(request, analysis_id):
    """Delete an analysis"""
    analysis = get_object_or_404(CancerImageAnalysis, id=analysis_id, user=request.user)
    
    # Delete the image file (works for both local and cloud storage)
    if analysis.image:
        try:
            analysis.image.delete(save=False)
        except:
            pass
    
    analysis.delete()
    messages.success(request, 'Analysis deleted successfully.')
    return JsonResponse({'success': True})


@login_required
def dashboard(request):
    """Cancer detection dashboard"""
    # Get statistics
    total_analyses = CancerImageAnalysis.objects.filter(user=request.user).count()
    detected_cases = CancerImageAnalysis.objects.filter(user=request.user, tumor_detected=True).count()
    recent_analyses = CancerImageAnalysis.objects.filter(user=request.user)[:5]
    
    context = {
        'total_analyses': total_analyses,
        'detected_cases': detected_cases,
        'recent_analyses': recent_analyses,
    }
    
    return render(request, 'cancer_detection/dashboard.html', context)


@login_required
def generate_treatment_plan(request, analysis_id):
    """Generate AI-powered personalized treatment plan from cancer analysis using Groq AI"""
    analysis = get_object_or_404(CancerImageAnalysis, id=analysis_id, user=request.user)
    
    if request.method == 'POST':
        try:
            # Import Groq planner
            from .groq_treatment_planner import GroqTreatmentPlanner
            
            # Get additional patient information from form
            patient_age = int(request.POST.get('age', 50))
            patient_sex = request.POST.get('sex', 'Unknown')
            performance_status = int(request.POST.get('performance_status', 1))
            comorbidities = request.POST.getlist('comorbidities')
            genetic_mutations = request.POST.getlist('mutations')
            
            # Prepare patient data
            patient_data = {
                'age': patient_age,
                'sex': patient_sex,
                'performance_status': performance_status,
                'comorbidities': comorbidities,
                'lab_values': {
                    'ejection_fraction': float(request.POST.get('ejection_fraction', 55)),
                    'creatinine': float(request.POST.get('creatinine', 1.0)),
                    'gfr': float(request.POST.get('gfr', 90)),
                    'bilirubin': float(request.POST.get('bilirubin', 0.7)),
                    'hemoglobin': float(request.POST.get('hemoglobin', 12.0)),
                    'wbc': float(request.POST.get('wbc', 7.0)),
                    'platelets': float(request.POST.get('platelets', 200)),
                }
            }
            
            # Prepare cancer analysis data
            cancer_analyses = [{
                'id': str(analysis.id),
                'tumor_type': analysis.tumor_type or request.POST.get('cancer_type', 'unknown'),
                'stage': analysis.tumor_stage or request.POST.get('stage', '1'),
                'grade': request.POST.get('grade', 'unknown'),
                'size_mm': analysis.tumor_size_mm or float(request.POST.get('size_mm', 0)),
                'location': analysis.tumor_location or request.POST.get('location', 'unknown'),
                'confidence': analysis.detection_confidence,
                'genetic_profile': analysis.genetic_profile,
                'lymph_node_involvement': request.POST.get('lymph_node_involvement', 'false').lower() == 'true',
                'metastases': request.POST.get('metastasis', 'false').lower() == 'true',
                'metastasis_sites': request.POST.getlist('metastasis_sites'),
            }]
            
            # Check for related histopathology reports
            histopathology_reports = []
            related_reports = HistopathologyReport.objects.filter(
                patient=request.user,
                cancer_type__iexact=analysis.tumor_type
            ).order_by('-created_at')[:2]  # Get up to 2 most recent related reports
            
            for report in related_reports:
                histopathology_reports.append({
                    'id': str(report.id),
                    'cancer_type': report.cancer_type,
                    'cancer_subtype': report.cancer_subtype,
                    'grade': report.grade,
                    'stage': report.stage,
                    'tnm_staging': report.tnm_staging,
                    'tumor_size_mm': report.tumor_size_mm,
                    'margin_status': report.margin_status,
                    'lymph_node_status': report.lymph_node_status,
                    'biomarkers': report.biomarkers,
                })
            
            # Check for related genomic profiles
            genomic_profiles = []
            related_profiles = GenomicProfile.objects.filter(
                patient=request.user
            ).order_by('-created_at')[:2]  # Get up to 2 most recent profiles
            
            for profile in related_profiles:
                # Add mutations from form if not already in profile
                profile_mutations = profile.mutations if isinstance(profile.mutations, list) else []
                all_mutations = list(set(profile_mutations + genetic_mutations))
                
                genomic_profiles.append({
                    'id': str(profile.id),
                    'mutations': all_mutations,
                    'biomarkers': profile.biomarkers,
                    'tumor_mutational_burden': profile.tumor_mutational_burden or request.POST.get('tmb', 'unknown'),
                    'microsatellite_instability': profile.msi_status or request.POST.get('msi_status', 'unknown'),
                    'pd_l1_expression': profile.pd_l1_status or request.POST.get('pd_l1_status', 'unknown'),
                })
            
            # If no genomic profiles exist, create one from form data
            if not genomic_profiles and genetic_mutations:
                genomic_profiles.append({
                    'id': 'form_data',
                    'mutations': genetic_mutations,
                    'biomarkers': analysis.genetic_profile.get('biomarkers', {}),
                    'tumor_mutational_burden': request.POST.get('tmb', 'unknown'),
                    'microsatellite_instability': request.POST.get('msi_status', 'unknown'),
                    'pd_l1_expression': request.POST.get('pd_l1_status', 'unknown'),
                })
            
            # Initialize Groq planner (singleton - reuses HTTP client)
            planner = GroqTreatmentPlanner.get_instance()
            
            # Generate comprehensive treatment plan using Groq AI
            comprehensive_plan = planner.create_comprehensive_treatment_plan(
                patient_data=patient_data,
                cancer_analyses=cancer_analyses,
                histopathology_reports=histopathology_reports,
                genomic_profiles=genomic_profiles
            )
            
            # Extract all components
            integrated_data = comprehensive_plan['integrated_data']
            treatment_recommendations = comprehensive_plan['plan_summary']
            pathway = comprehensive_plan['treatment_pathway']
            decision_support = comprehensive_plan['decision_support']
            clinical_trials = comprehensive_plan['clinical_trials']
            outcomes = comprehensive_plan['outcome_predictions']
            
            # Extract treatments from AI recommendations
            systemic_therapy = treatment_recommendations.get('systemic_therapy', {})
            primary_treatment = treatment_recommendations.get('primary_treatment', {})
            
            # Build primary treatments list
            primary_treatments = primary_treatment.get('modalities', [])
            if treatment_recommendations.get('surgery', {}).get('recommended'):
                primary_treatments.append(f"Surgery: {treatment_recommendations['surgery'].get('procedure', 'Surgical resection')}")
            if treatment_recommendations.get('radiation_therapy', {}).get('recommended'):
                rad_therapy = treatment_recommendations['radiation_therapy']
                primary_treatments.append(f"Radiation: {rad_therapy.get('type', 'IMRT')} - {rad_therapy.get('dose', 'Standard fractionation')}")
            
            # Build adjuvant treatments
            adjuvant_treatments = []
            if systemic_therapy.get('chemotherapy', {}).get('recommended'):
                adjuvant_treatments.extend(systemic_therapy['chemotherapy'].get('regimens', []))
            if systemic_therapy.get('hormonal_therapy', {}).get('recommended'):
                adjuvant_treatments.extend(systemic_therapy['hormonal_therapy'].get('agents', []))
            
            # Build targeted therapies
            targeted_therapies = []
            if systemic_therapy.get('targeted_therapy', {}).get('recommended'):
                targeted_therapies.extend(systemic_therapy['targeted_therapy'].get('agents', []))
            if systemic_therapy.get('immunotherapy', {}).get('recommended'):
                targeted_therapies.extend(systemic_therapy['immunotherapy'].get('agents', []))
            
            # Extract side effects
            side_effects_data = treatment_recommendations.get('side_effects', {})
            side_effects = []
            for se in side_effects_data.get('common', []):
                side_effects.append({'name': se, 'severity': 'moderate', 'frequency': 'common'})
            for se in side_effects_data.get('serious', []):
                side_effects.append({'name': se, 'severity': 'severe', 'frequency': 'occasional'})
            
            # Create plan name
            cancer_type = integrated_data.get('cancer_type', analysis.tumor_type or 'Cancer')
            cancer_stage = integrated_data.get('cancer_stage', analysis.tumor_stage or 'Unknown')
            plan_name = f"AI-Powered {cancer_type} Stage {cancer_stage} Plan - {datetime.now().strftime('%Y-%m-%d')}"
            
            # Parse response rate safely
            response_rate_value = 70.0  # Default
            response_rate = outcomes.get('response_rate', '70')
            if isinstance(response_rate, (int, float)):
                response_rate_value = float(response_rate)
            elif isinstance(response_rate, str):
                # Try to extract percentage from string
                import re
                match = re.search(r'(\d+(?:\.\d+)?)\s*%?', response_rate)
                if match:
                    response_rate_value = float(match.group(1))
            
            # Save treatment plan to database
            plan = PersonalizedTreatmentPlan.objects.create(
                patient=request.user,
                analysis=analysis,
                plan_name=plan_name,
                cancer_type=cancer_type,
                cancer_stage=cancer_stage,
                patient_profile={
                    **patient_data,
                    'decision_support': decision_support,
                    'full_recommendations': treatment_recommendations,
                    'data_sources': {
                        'image_analysis': str(analysis.id),
                        'histopathology_reports': len(histopathology_reports),
                        'genomic_profiles': len(genomic_profiles),
                    }
                },
                tumor_analysis=integrated_data.get('tumor_characteristics', {}),
                genetic_profile={
                    'biomarkers': integrated_data.get('biomarkers', {}),
                    'mutations': integrated_data.get('mutations', []),
                    'integrated_genomics': genomic_profiles,
                },
                primary_treatments=primary_treatments,
                adjuvant_treatments=adjuvant_treatments,
                targeted_therapies=targeted_therapies,
                side_effects=side_effects,
                predicted_5yr_survival=outcomes.get('predicted_5yr_survival'),
                remission_probability=response_rate_value,
                quality_of_life_score=75,  # Default
                monitoring_plan=treatment_recommendations.get('monitoring', {}),
                treatment_pathway=pathway,
                clinical_trials=clinical_trials,
                contraindications=treatment_recommendations.get('contraindications', []),
                special_considerations=request.POST.get('special_considerations', ''),
                status='draft'
            )
            
            messages.success(request, 'AI-powered personalized treatment plan generated successfully! Advanced Groq AI has analyzed all available data.')
            return redirect('cancer_detection:treatment_plan_detail', plan_id=plan.id)
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            messages.error(request, f'Error generating treatment plan: {str(e)}')
            return redirect('cancer_detection:analysis_detail', analysis_id=analysis_id)
    
    # Get patient's medical profile if available
    try:
        patient_profile = request.user.patient_profile
    except:
        patient_profile = None
    
    # Common comorbidities list
    comorbidities_list = [
        'Diabetes',
        'Hypertension',
        'Cardiovascular Disease',
        'Chronic Kidney Disease',
        'Chronic Liver Disease',
        'Chronic Pulmonary Disease',
        'History of Other Cancers',
        'HIV/AIDS',
        'Autoimmune Disorder',
    ]
    
    # Common mutations for cancer
    mutations_list = [
        'EGFR',
        'ALK',
        'ROS1',
        'HER2',
        'BRAF V600E',
        'KRAS G12C',
        'TP53',
        'BRCA1',
        'BRCA2',
        'MSI-H',
        'TMB-H',
        'PD-L1+',
    ]
    
    context = {
        'analysis': analysis,
        'patient_profile': patient_profile,
        'comorbidities_list': comorbidities_list,
        'mutations_list': mutations_list,
    }
    
    return render(request, 'cancer_detection/generate_treatment_plan.html', context)


@login_required
def treatment_plan_detail(request, plan_id):
    """View detailed personalized treatment plan"""
    plan = get_object_or_404(PersonalizedTreatmentPlan, id=plan_id, patient=request.user)
    
    # Format lab values keys with spaces instead of underscores for display
    patient_profile = plan.patient_profile.copy() if isinstance(plan.patient_profile, dict) else plan.patient_profile
    if isinstance(patient_profile, dict) and 'lab_values' in patient_profile:
        formatted_lab_values = {}
        for key, value in patient_profile['lab_values'].items():
            formatted_key = key.replace('_', ' ').title()
            formatted_lab_values[formatted_key] = value
        patient_profile['lab_values'] = formatted_lab_values
    
    context = {
        'plan': plan,
        'patient_profile': patient_profile,
        'tumor_analysis': plan.tumor_analysis,
        'genetic_profile': plan.genetic_profile,
        'treatment_pathway': plan.treatment_pathway,
        'monitoring_plan': plan.monitoring_plan,
        'clinical_trials': plan.clinical_trials,
    }
    
    return render(request, 'cancer_detection/treatment_plan_detail.html', context)


@login_required
def treatment_plans_list(request):
    """List all treatment plans for current patient"""
    plans = PersonalizedTreatmentPlan.objects.filter(patient=request.user)
    
    # Pagination
    paginator = Paginator(plans, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_plans': plans.count(),
        'active_plans': plans.filter(status='active').count(),
        'pending_review': plans.filter(status='pending_review').count(),
    }
    
    return render(request, 'cancer_detection/treatment_plans_list.html', context)


@login_required
@require_POST
def submit_treatment_plan_review(request, plan_id):
    """Submit treatment plan for oncologist review"""
    plan = get_object_or_404(PersonalizedTreatmentPlan, id=plan_id, patient=request.user)
    
    if plan.status == 'draft':
        plan.status = 'pending_review'
        plan.save()
        messages.success(request, 'Treatment plan submitted for oncologist review.')
    else:
        messages.warning(request, 'Only draft plans can be submitted for review.')
    
    return redirect('cancer_detection:treatment_plan_detail', plan_id=plan.id)


@login_required
def upload_histopathology_report(request):
    """View for uploading histopathology reports"""
    if request.method == 'POST':
        report_text_input = request.POST.get('report_text', '').strip()
        has_file = 'report_file' in request.FILES
        
        if not has_file and not report_text_input:
            messages.error(request, 'Please either paste report text or upload a report file.')
            return redirect('cancer_detection:histopathology_hub')
        
        report_file = request.FILES.get('report_file') if has_file else None
        report_type = request.POST.get('report_type', 'biopsy')
        
        if has_file:
            # Validate file type
            allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.docx', '.txt']
            file_ext = os.path.splitext(report_file.name)[1].lower()
            
            if file_ext not in allowed_extensions:
                messages.error(request, f'Invalid file type. Allowed types: {", ".join(allowed_extensions)}')
                return redirect('cancer_detection:histopathology_hub')
        
        # Create histopathology report record
        create_kwargs = {'patient': request.user}
        if report_file:
            create_kwargs['report_file'] = report_file
        report = HistopathologyReport.objects.create(**create_kwargs)
        
        # Extract text from file or use pasted text
        try:
            report_text = report_text_input or ""
            
            # Extract text from file if uploaded and no text was pasted
            if has_file and not report_text_input:
                # Handle both local and cloud storage
                try:
                    file_path = report.report_file.path
                except NotImplementedError:
                    # Cloud storage - download to temporary file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
                        report.report_file.seek(0)
                        tmp_file.write(report.report_file.read())
                        file_path = tmp_file.name
                
                if file_ext == '.txt':
                    # Simple text file - fastest
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        report_text = f.read()
                elif file_ext == '.pdf':
                    # Try pdfplumber first (faster), then PyPDF2
                    try:
                        import pdfplumber
                        with pdfplumber.open(file_path) as pdf:
                            pages_text = []
                            for page in pdf.pages[:5]:  # Limit for speed
                                text = page.extract_text()
                                if text:
                                    pages_text.append(text)
                            report_text = "\n".join(pages_text)
                    except ImportError:
                        try:
                            import PyPDF2
                            with open(file_path, 'rb') as f:
                                reader = PyPDF2.PdfReader(f)
                                for page in reader.pages[:5]:
                                    report_text += page.extract_text() or ""
                        except ImportError:
                            report_text = "PDF file uploaded - install pdfplumber for text extraction"
                        except Exception:
                            report_text = "PDF file uploaded - text extraction failed"
                    except Exception:
                        report_text = "PDF file uploaded - text extraction failed"
                elif file_ext == '.docx':
                    # Extract text from DOCX
                    try:
                        from docx import Document
                        doc = Document(file_path)
                        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
                        report_text = "\n".join(paragraphs[:100])  # Limit for speed
                    except ImportError:
                        report_text = "DOCX file uploaded - install python-docx for text extraction"
                    except Exception:
                        report_text = "DOCX file uploaded - text extraction failed"
                elif file_ext in ['.jpg', '.jpeg', '.png']:
                    # Image files - try OCR with pytesseract
                    try:
                        import pytesseract
                        from PIL import Image
                        img = Image.open(file_path)
                        report_text = pytesseract.image_to_string(img)
                    except ImportError:
                        report_text = "Image file uploaded - install pytesseract for OCR"
                    except Exception:
                        report_text = "Image file uploaded - OCR extraction failed"
                
                # Clean up temp file if created (from cloud storage)
                if file_path.startswith(tempfile.gettempdir()):
                    try:
                        os.unlink(file_path)
                    except:
                        pass
            
            # Store extracted text
            report.report_text = report_text
            
            # Perform analysis if we have text - try Groq first for speed
            if report_text and not report_text.startswith(('PDF file', 'DOCX file', 'Image file')):
                results = None
                
                # Try Groq API first (much faster - typically <1 second)
                try:
                    groq_analyzer = GroqAnalyzer.get_instance()
                    if groq_analyzer.is_available():
                        results = groq_analyzer.analyze_histopathology_report(report_text)
                        if results and results.get('confidence', 0) > 0:
                            # Use Groq results
                            report.cancer_type = results.get('cancer_type')
                            report.cancer_subtype = results.get('cancer_subtype')
                            report.grade = results.get('grade')
                            report.stage = results.get('stage')
                            report.tnm_staging = results.get('tnm_staging')
                            report.tumor_size_mm = results.get('tumor_size_mm')
                            report.margin_status = results.get('margin_status')
                            report.biomarkers = results.get('biomarkers', {})
                            
                            # Handle lymph node status
                            if results.get('lymph_node_involved') is not None:
                                report.lymph_node_status = {
                                    'involved': results.get('lymph_node_involved'),
                                    'positive_count': results.get('lymph_node_positive_count'),
                                    'total_count': results.get('lymph_node_total_count'),
                                }
                            
                            report.analysis_results = results
                            report.analysis_confidence = results.get('confidence', 0.0)
                except Exception as e:
                    print(f"Groq analysis failed, falling back to regex: {e}")
                    results = None
                
                # Fallback to regex-based analysis if Groq fails
                if not results or results.get('confidence', 0) == 0:
                    analyzer = HistopathologyAnalyzer()
                    results = analyzer.analyze_report(report_text)
                    
                    # Extract cancer type info
                    cancer_type_info = results.get('cancer_type', {})
                    if isinstance(cancer_type_info, dict):
                        report.cancer_type = cancer_type_info.get('type')
                    else:
                        report.cancer_type = cancer_type_info
                    
                    # Extract grade info
                    grade_info = results.get('grade', {})
                    if isinstance(grade_info, dict):
                        report.grade = grade_info.get('grade')
                    else:
                        report.grade = grade_info
                    
                    # Extract stage info
                    stage_info = results.get('stage', {})
                    if isinstance(stage_info, dict):
                        report.stage = stage_info.get('stage')
                        report.tnm_staging = stage_info.get('tnm')
                    
                    # Extract tumor size
                    size_info = results.get('tumor_size')
                    if size_info and isinstance(size_info, dict):
                        report.tumor_size_mm = size_info.get('size_mm')
                    
                    # Extract other fields
                    report.cancer_subtype = results.get('cancer_subtype')
                    report.biomarkers = results.get('biomarkers', {})
                    report.lymph_node_status = results.get('lymph_node_status', {})
                    
                    margin_info = results.get('margin_status')
                    if margin_info and isinstance(margin_info, dict):
                        report.margin_status = margin_info.get('status')
                    
                    report.analysis_results = results
                    report.analysis_confidence = results.get('confidence', 0.0)
            
            report.status = 'analyzed'
            report.analyzed_at = timezone.now()
            report.save()
            
            messages.success(request, 'Histopathology report uploaded and analyzed successfully!')
            return redirect('cancer_detection:histopathology_detail', report_id=report.id)
            
        except Exception as e:
            messages.error(request, f'Error analyzing report: {str(e)}')
            report.delete()
            return redirect('cancer_detection:histopathology_hub')
    
    return redirect('cancer_detection:histopathology_hub')


@login_required
def histopathology_reports_list(request):
    """List all histopathology reports for the current user"""
    reports = HistopathologyReport.objects.filter(patient=request.user)
    
    # Pagination
    paginator = Paginator(reports, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'cancer_detection/histopathology_list.html', {
        'page_obj': page_obj
    })


@login_required
def histopathology_report_detail(request, report_id):
    """View detailed histopathology report"""
    report = get_object_or_404(HistopathologyReport, id=report_id, patient=request.user)
    
    context = {
        'report': report,
        'analysis_data': report.analysis_results or {},
    }
    
    return render(request, 'cancer_detection/histopathology_detail.html', context)


@login_required
def combined_data_analysis(request):
    """Combined view for all data analysis sections"""
    # Get histopathology reports
    histopathology_reports = HistopathologyReport.objects.filter(patient=request.user).order_by('-created_at')
    
    # Get genomic profiles
    genomic_profiles = GenomicProfile.objects.filter(patient=request.user).order_by('-created_at')
    
    context = {
        'histopathology_reports': histopathology_reports,
        'genomic_profiles': genomic_profiles,
    }
    
    return render(request, 'cancer_detection/combined_data_analysis.html', context)


@login_required
def upload_genomic_profile(request):
    """View for uploading genomic profiles via form entry"""
    if request.method == 'POST':
        # Collect mutations from form
        mutations = {}
        mutation_fields = ['egfr', 'alk', 'her2', 'braf', 'kras', 'brca1', 'brca2', 'tp53']
        for field in mutation_fields:
            value = request.POST.get(f'mutation_{field}', '').strip()
            if value:
                mutations[field.upper()] = value
        
        # Collect biomarkers from form
        biomarkers = {}
        biomarker_er = request.POST.get('biomarker_er', '').strip()
        biomarker_pr = request.POST.get('biomarker_pr', '').strip()
        biomarker_her2 = request.POST.get('biomarker_her2', '').strip()
        biomarker_ki67 = request.POST.get('biomarker_ki67', '').strip()
        
        if biomarker_er:
            biomarkers['ER'] = biomarker_er
        if biomarker_pr:
            biomarkers['PR'] = biomarker_pr
        if biomarker_her2:
            biomarkers['HER2'] = biomarker_her2
        if biomarker_ki67:
            try:
                biomarkers['Ki-67'] = float(biomarker_ki67)
            except ValueError:
                pass
        
        # Collect immunoprofile data
        pd_l1_status = request.POST.get('pd_l1_status', '').strip()
        pd_l1_percentage = request.POST.get('pd_l1_percentage', '').strip()
        msi_status = request.POST.get('msi_status', '').strip()
        tmb = request.POST.get('tmb', '').strip()
        immune_infiltration = request.POST.get('immune_infiltration', '').strip()
        
        # Collect test information
        test_type = request.POST.get('test_type', '').strip()
        test_date = request.POST.get('test_date', '').strip()
        lab_name = request.POST.get('lab_name', '').strip()
        
        # Validate that at least some data was entered
        if not mutations and not biomarkers and not pd_l1_status and not msi_status and not tmb:
            messages.error(request, 'Please enter at least some genomic profile data.')
            return redirect('cancer_detection:upload_genomic')
        
        try:
            # Create genomic profile record
            profile = GenomicProfile.objects.create(
                patient=request.user,
                mutations=mutations,
                biomarkers=biomarkers,
                pd_l1_status=pd_l1_status if pd_l1_status else None,
                pd_l1_percentage=float(pd_l1_percentage) if pd_l1_percentage else None,
                msi_status=msi_status if msi_status else None,
                tumor_mutational_burden=float(tmb) if tmb else None,
                immune_infiltration=immune_infiltration if immune_infiltration else None,
                test_type=test_type if test_type else None,
                test_date=test_date if test_date else None,
                lab_name=lab_name if lab_name else None,
                analyzed_at=timezone.now(),
            )
            
            # Analyze the profile data - try Groq first for speed
            genetic_data = {
                'mutations': mutations,
                'biomarkers': biomarkers,
                'pd_l1_status': pd_l1_status,
                'msi_status': msi_status,
                'tumor_mutational_burden': float(tmb) if tmb else None,
                'immune_infiltration': immune_infiltration,
            }
            
            results = None
            
            # Try Groq API first (much faster)
            try:
                groq_analyzer = GroqAnalyzer.get_instance()
                if groq_analyzer.is_available():
                    results = groq_analyzer.analyze_genomic_profile(genetic_data)
                    if results and results.get('confidence', 0) > 0:
                        profile.actionable_mutations = results.get('actionable_mutations', [])
                        profile.targeted_therapy_eligibility = results.get('targeted_therapy_eligible', {})
                        profile.immunotherapy_eligibility = results.get('immunotherapy_eligible', {})
                        profile.prognostic_profile = results.get('prognostic_profile', {})
                        profile.analysis_results = results
                        profile.save()
            except Exception as e:
                print(f"Groq genomic analysis failed: {e}")
                results = None
            
            # Fallback to regex-based analysis
            if not results or results.get('confidence', 0) == 0:
                try:
                    analyzer = GenomicsAnalyzer()
                    results = analyzer.analyze_genomic_profile(genetic_data)
                    
                    profile.actionable_mutations = results.get('actionable_mutations', [])
                    profile.targeted_therapy_eligibility = results.get('targeted_therapy_eligible', {})
                    profile.immunotherapy_eligibility = results.get('immunotherapy_eligible', {})
                    profile.prognostic_profile = results.get('prognostic_profile', {})
                    profile.analysis_results = results
                    profile.save()
                except Exception as e:
                    # Even if analysis fails, the profile is saved with the raw data
                    pass
            
            messages.success(request, 'Genomic profile saved and analyzed successfully!')
            return redirect('cancer_detection:genomic_detail', profile_id=profile.id)
            
        except Exception as e:
            messages.error(request, f'Error saving genomic profile: {str(e)}')
            return redirect('cancer_detection:upload_genomic')
    
    # Define profile types since they're not in the model
    profile_types = [
        ('ngs', 'Next-Generation Sequencing (NGS)'),
        ('whole_genome', 'Whole Genome Sequencing'),
        ('whole_exome', 'Whole Exome Sequencing'),
        ('targeted_panel', 'Targeted Gene Panel'),
        ('pcr', 'PCR-based Testing'),
        ('ihc', 'Immunohistochemistry'),
        ('fish', 'FISH'),
        ('other', 'Other'),
    ]
    return render(request, 'cancer_detection/upload_genomic.html', {
        'profile_types': profile_types
    })


@login_required
def genomic_profiles_list(request):
    """List all genomic profiles for the current user"""
    profiles = GenomicProfile.objects.filter(patient=request.user)
    
    # Pagination
    paginator = Paginator(profiles, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'cancer_detection/genomic_list.html', {
        'page_obj': page_obj
    })


@login_required
def genomic_profile_detail(request, profile_id):
    """View detailed genomic profile"""
    profile = get_object_or_404(GenomicProfile, id=profile_id, patient=request.user)
    
    context = {
        'profile': profile,
        'mutations': profile.mutations or {},
        'cnv': profile.copy_number_variations or {},
        'analysis_data': profile.analysis_results or {},
    }
    
    return render(request, 'cancer_detection/genomic_detail.html', context)


@login_required
def create_comprehensive_plan(request):
    """Create a comprehensive treatment plan combining multiple data sources using Groq AI"""
    if request.method == 'POST':
        try:
            # Import Groq planner
            from .groq_treatment_planner import GroqTreatmentPlanner
            
            # Get selected analyses, histopathology reports, and genomic profiles
            analysis_ids = request.POST.getlist('analyses')
            report_ids = request.POST.getlist('histopathology_reports')
            profile_ids = request.POST.getlist('genomic_profiles')
            
            # Get patient data from form
            patient_data = {
                'age': int(request.POST.get('age', 50)),
                'sex': request.POST.get('sex', 'Unknown'),
                'performance_status': int(request.POST.get('performance_status', 1)),
                'comorbidities': request.POST.getlist('comorbidities'),
            }
            
            # Collect all analyses
            cancer_analyses = []
            for analysis_id in analysis_ids:
                analysis = get_object_or_404(CancerImageAnalysis, id=analysis_id, user=request.user)
                cancer_analyses.append({
                    'id': str(analysis.id),
                    'tumor_type': analysis.tumor_type,
                    'stage': analysis.tumor_stage,
                    'size_mm': analysis.tumor_size_mm,
                    'location': analysis.tumor_location,
                    'confidence': analysis.detection_confidence,
                    'genetic_profile': analysis.genetic_profile,
                })
            
            # Collect histopathology reports
            histopathology_reports = []
            for report_id in report_ids:
                report = get_object_or_404(HistopathologyReport, id=report_id, patient=request.user)
                histopathology_reports.append({
                    'id': str(report.id),
                    'cancer_type': report.cancer_type,
                    'cancer_subtype': report.cancer_subtype,
                    'grade': report.grade,
                    'stage': report.stage,
                    'tnm_staging': report.tnm_staging,
                    'tumor_size_mm': report.tumor_size_mm,
                    'margin_status': report.margin_status,
                    'lymph_node_status': report.lymph_node_status,
                    'biomarkers': report.biomarkers,
                })
            
            # Collect genomic profiles
            genomic_profiles = []
            for profile_id in profile_ids:
                profile = get_object_or_404(GenomicProfile, id=profile_id, patient=request.user)
                genomic_profiles.append({
                    'id': str(profile.id),
                    'mutations': profile.mutations,
                    'biomarkers': profile.biomarkers,
                    'tumor_mutational_burden': profile.tumor_mutational_burden,
                    'microsatellite_instability': profile.msi_status,
                    'pd_l1_expression': profile.pd_l1_status,
                })
            
            # Initialize Groq planner (singleton - reuses HTTP client)
            planner = GroqTreatmentPlanner.get_instance()
            
            # Generate comprehensive treatment plan
            comprehensive_plan = planner.create_comprehensive_treatment_plan(
                patient_data=patient_data,
                cancer_analyses=cancer_analyses,
                histopathology_reports=histopathology_reports,
                genomic_profiles=genomic_profiles
            )
            
            # Extract integrated data
            integrated_data = comprehensive_plan['integrated_data']
            treatment_recommendations = comprehensive_plan['plan_summary']
            pathway = comprehensive_plan['treatment_pathway']
            decision_support = comprehensive_plan['decision_support']
            clinical_trials = comprehensive_plan['clinical_trials']
            outcomes = comprehensive_plan['outcome_predictions']
            
            # Create plan name
            cancer_type = integrated_data.get('cancer_type', 'Cancer')
            cancer_stage = integrated_data.get('cancer_stage', 'Unknown Stage')
            plan_name = f"Comprehensive {cancer_type} {cancer_stage} - {datetime.now().strftime('%Y-%m-%d')}"
            
            # Get primary and adjuvant treatments
            systemic_therapy = treatment_recommendations.get('systemic_therapy', {})
            primary_treatments = treatment_recommendations.get('primary_treatment', {}).get('modalities', [])
            
            # Collect all systemic therapies
            adjuvant_treatments = []
            if systemic_therapy.get('chemotherapy', {}).get('recommended'):
                adjuvant_treatments.extend(systemic_therapy['chemotherapy'].get('regimens', []))
            if systemic_therapy.get('hormonal_therapy', {}).get('recommended'):
                adjuvant_treatments.extend(systemic_therapy['hormonal_therapy'].get('agents', []))
            
            # Collect targeted therapies
            targeted_therapies = []
            if systemic_therapy.get('targeted_therapy', {}).get('recommended'):
                targeted_therapies.extend(systemic_therapy['targeted_therapy'].get('agents', []))
            if systemic_therapy.get('immunotherapy', {}).get('recommended'):
                targeted_therapies.extend(systemic_therapy['immunotherapy'].get('agents', []))
            
            # Extract side effects
            side_effects_data = treatment_recommendations.get('side_effects', {})
            side_effects = []
            for se in side_effects_data.get('common', []):
                side_effects.append({'name': se, 'severity': 'common', 'frequency': 'common'})
            for se in side_effects_data.get('serious', []):
                side_effects.append({'name': se, 'severity': 'severe', 'frequency': 'occasional'})
            
            # Parse response rate safely
            response_rate_value = 70.0  # Default
            response_rate = outcomes.get('response_rate', '70')
            if isinstance(response_rate, (int, float)):
                response_rate_value = float(response_rate)
            elif isinstance(response_rate, str):
                # Try to extract percentage from string
                import re
                match = re.search(r'(\d+(?:\.\d+)?)\s*%?', response_rate)
                if match:
                    response_rate_value = float(match.group(1))
            
            # Save comprehensive treatment plan
            plan = PersonalizedTreatmentPlan.objects.create(
                patient=request.user,
                plan_name=plan_name,
                cancer_type=integrated_data.get('cancer_type', 'Unknown'),
                cancer_stage=integrated_data.get('cancer_stage', 'Unknown'),
                patient_profile={
                    **patient_data,
                    'integrated_from': {
                        'analyses': len(cancer_analyses),
                        'histopathology': len(histopathology_reports),
                        'genomics': len(genomic_profiles),
                    }
                },
                tumor_analysis=integrated_data.get('tumor_characteristics', {}),
                genetic_profile={
                    'biomarkers': integrated_data.get('biomarkers', {}),
                    'mutations': integrated_data.get('mutations', []),
                    'genomic_profiles': genomic_profiles,
                },
                primary_treatments=primary_treatments,
                adjuvant_treatments=adjuvant_treatments,
                targeted_therapies=targeted_therapies,
                side_effects=side_effects,
                predicted_5yr_survival=outcomes.get('predicted_5yr_survival'),
                remission_probability=response_rate_value,
                quality_of_life_score=75,  # Default
                monitoring_plan=treatment_recommendations.get('monitoring', {}),
                treatment_pathway=pathway,
                clinical_trials=clinical_trials,
                contraindications=treatment_recommendations.get('contraindications', []),
                special_considerations=json.dumps(decision_support, indent=2),
                status='draft'
            )
            
            # Store decision support and full recommendations as additional data
            plan.patient_profile['decision_support'] = decision_support
            plan.patient_profile['full_recommendations'] = treatment_recommendations
            plan.save()
            
            messages.success(request, f'Comprehensive AI-powered treatment plan created successfully! Review the detailed recommendations.')
            return redirect('cancer_detection:treatment_plan_detail', plan_id=plan.id)
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            messages.error(request, f'Error creating comprehensive plan: {str(e)}')
            return redirect('cancer_detection:create_comprehensive_plan')
    
    # Get available data sources for the user
    analyses = CancerImageAnalysis.objects.filter(user=request.user, tumor_detected=True).order_by('-created_at')
    histopathology_reports = HistopathologyReport.objects.filter(patient=request.user).order_by('-created_at')
    genomic_profiles = GenomicProfile.objects.filter(patient=request.user).order_by('-created_at')
    
    # Common comorbidities list
    comorbidities_list = [
        'Diabetes',
        'Hypertension',
        'Cardiovascular Disease',
        'Chronic Kidney Disease',
        'Chronic Liver Disease',
        'COPD/Pulmonary Disease',
        'Previous Cancer History',
        'HIV/AIDS',
        'Autoimmune Disorder',
        'Obesity',
    ]
    
    context = {
        'analyses': analyses,
        'histopathology_reports': histopathology_reports,
        'genomic_profiles': genomic_profiles,
        'comorbidities_list': comorbidities_list,
        'has_data': analyses.exists() or histopathology_reports.exists() or genomic_profiles.exists(),
    }
    
    return render(request, 'cancer_detection/create_comprehensive_plan.html', context)


@login_required
def visualize_treatment_pathway(request, plan_id):
    """Visualize detailed AI-generated treatment pathway with timeline"""
    plan = get_object_or_404(PersonalizedTreatmentPlan, id=plan_id, patient=request.user)
    
    # Extract detailed pathway information
    pathway_data = plan.treatment_pathway or {}
    
    # Organize timeline data
    timeline_phases = []
    if isinstance(pathway_data, dict):
        # Extract phases from AI-generated pathway
        for phase_name, phase_data in pathway_data.items():
            if isinstance(phase_data, dict) and 'weeks' in phase_data:
                timeline_phases.append({
                    'name': phase_name.replace('_', ' ').title(),
                    'duration': phase_data.get('duration', 'Varies'),
                    'weeks': phase_data.get('weeks', []),
                    'description': phase_data.get('description', ''),
                    'key_activities': phase_data.get('key_activities', []),
                })
    
    # Get decision support info for additional context
    decision_support_data = {}
    full_recommendations = {}
    if isinstance(plan.patient_profile, dict):
        decision_support_data = plan.patient_profile.get('decision_support', {})
        full_recommendations = plan.patient_profile.get('full_recommendations', {})
    
    # Extract key milestones from pathway
    milestones = []
    decision_points = []
    for phase in timeline_phases:
        for week_data in phase.get('weeks', []):
            if isinstance(week_data, dict):
                # Extract milestones
                if week_data.get('milestone'):
                    milestones.append({
                        'week': week_data.get('week_number', 'Unknown'),
                        'phase': phase['name'],
                        'milestone': week_data.get('milestone'),
                        'description': week_data.get('description', ''),
                    })
                # Extract decision points
                if week_data.get('decision_point'):
                    decision_points.append({
                        'week': week_data.get('week_number', 'Unknown'),
                        'phase': phase['name'],
                        'decision': week_data.get('decision_point'),
                        'criteria': week_data.get('assessment_criteria', []),
                    })
    
    # Get monitoring schedule from recommendations
    monitoring_schedule = full_recommendations.get('monitoring', {})
    
    context = {
        'plan': plan,
        'treatment_pathway': pathway_data,
        'timeline_phases': timeline_phases,
        'milestones': milestones,
        'decision_points': decision_points,
        'monitoring_schedule': monitoring_schedule,
        'primary_treatments': plan.primary_treatments or [],
        'adjuvant_treatments': plan.adjuvant_treatments or [],
        'targeted_therapies': plan.targeted_therapies or [],
        'clinical_trials': plan.clinical_trials or [],
        'supportive_care': full_recommendations.get('supportive_care', {}),
    }
    
    return render(request, 'cancer_detection/visualize_pathway.html', context)


@login_required
def decision_support(request, plan_id):
    """Provide comprehensive clinical decision support for treatment plan"""
    plan = get_object_or_404(PersonalizedTreatmentPlan, id=plan_id, patient=request.user)
    
    # Extract decision support data from plan
    decision_support_data = {}
    if isinstance(plan.patient_profile, dict):
        decision_support_data = plan.patient_profile.get('decision_support', {})
        full_recommendations = plan.patient_profile.get('full_recommendations', {})
    else:
        full_recommendations = {}
    
    # Get systemic therapy details
    systemic_therapy = full_recommendations.get('systemic_therapy', {})
    
    # Get monitoring plan details
    monitoring = full_recommendations.get('monitoring', {})
    follow_up_plan = full_recommendations.get('follow_up_plan', {})
    
    # Get alternatives and multidisciplinary recommendations
    alternatives = full_recommendations.get('alternatives', [])
    multidisciplinary = full_recommendations.get('multidisciplinary_recommendations', [])
    
    # Get supportive care recommendations
    supportive_care = full_recommendations.get('supportive_care', {})
    
    # Calculate treatment complexity score
    treatment_complexity = 0
    if plan.primary_treatments:
        treatment_complexity += len(plan.primary_treatments) * 2
    if plan.adjuvant_treatments:
        treatment_complexity += len(plan.adjuvant_treatments)
    if plan.targeted_therapies:
        treatment_complexity += len(plan.targeted_therapies)
    
    complexity_level = 'Low' if treatment_complexity < 3 else 'Moderate' if treatment_complexity < 6 else 'High'
    
    context = {
        'plan': plan,
        'decision_support': decision_support_data,
        'full_recommendations': full_recommendations,
        'systemic_therapy': systemic_therapy,
        'monitoring_plan': monitoring,
        'follow_up_plan': follow_up_plan,
        'clinical_trials': plan.clinical_trials or [],
        'contraindications': plan.contraindications or [],
        'alternatives': alternatives,
        'multidisciplinary': multidisciplinary,
        'supportive_care': supportive_care,
        'treatment_complexity': {
            'score': treatment_complexity,
            'level': complexity_level,
        },
        'special_considerations': plan.special_considerations or '',
    }
    
    return render(request, 'cancer_detection/decision_support.html', context)


@login_required
def image_hub(request):
    """Combined view for image upload and analysis history"""
    # Upload form context
    image_types = CancerImageAnalysis.IMAGE_TYPE_CHOICES
    
    # Analysis list with pagination
    analyses = CancerImageAnalysis.objects.filter(user=request.user).order_by('-created_at')
    paginator = Paginator(analyses, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'image_types': image_types,
        'page_obj': page_obj,
    }
    return render(request, 'cancer_detection/image_hub.html', context)


@login_required
def pathology_hub(request):
    """Combined view for histopathology upload and reports list"""
    # Upload form context
    report_types = HistopathologyReport.REPORT_STATUS_CHOICES
    
    # Reports list with pagination
    reports = HistopathologyReport.objects.filter(patient=request.user).order_by('-created_at')
    paginator = Paginator(reports, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'report_types': report_types,
        'page_obj': page_obj,
    }
    return render(request, 'cancer_detection/pathology_hub.html', context)


@login_required
def histopathology_hub(request):
    """Combined view for histopathology report upload and reports list with tabs"""
    # Upload form context
    report_types = HistopathologyReport.REPORT_STATUS_CHOICES
    
    # Reports list with pagination
    reports = HistopathologyReport.objects.filter(patient=request.user).order_by('-created_at')
    paginator = Paginator(reports, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'report_types': report_types,
        'page_obj': page_obj,
    }
    return render(request, 'cancer_detection/histopathology_hub.html', context)


@login_required
def genomics_hub(request):
    """Combined view for genomic profile upload and profiles list"""
    # Upload form context
    profile_types = [
        ('ngs', 'Next-Generation Sequencing (NGS)'),
        ('pcr', 'Polymerase Chain Reaction (PCR)'),
        ('fish', 'Fluorescence In Situ Hybridization (FISH)'),
        ('ihc', 'Immunohistochemistry (IHC)'),
        ('microarray', 'Microarray'),
        ('whole_genome', 'Whole Genome Sequencing'),
        ('whole_exome', 'Whole Exome Sequencing'),
        ('other', 'Other'),
    ]
    
    # Profiles list with pagination
    profiles = GenomicProfile.objects.filter(patient=request.user).order_by('-created_at')
    paginator = Paginator(profiles, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'profile_types': profile_types,
        'page_obj': page_obj,
    }
    return render(request, 'cancer_detection/genomics_hub.html', context)
