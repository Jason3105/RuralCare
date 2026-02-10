"""
Voice Assistant Service using Groq LLM
Provides medical assistance through voice interaction
"""

import os
import json
import re
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required


# In-build page redirection: phrase (as mentioned by AI) -> URL path
# Longer phrases first so "My Consultations" is matched before "Consultations"
PATIENT_PAGE_LINKS = [
    ("Patient Dashboard", "/patient/dashboard/"),
    ("Book Consultation", "/portal/consultations/doctors/"),
    ("My Consultations", "/portal/consultations/my/"),
    ("Consultation Requests", "/portal/consultations/requests/"),
    ("Medical Records", "/patient/medical-records/"),
    ("Upload Medical Records", "/patient/medical-records/upload/"),
    ("Prescriptions", "/portal/consultations/my/"),
    ("Medicine Identifier", "/medicine/"),
    ("Cancer Detection", "/cancer-detection/"),
    ("Treatment Planning", "/cancer-detection/treatment-plans/"),
    ("Treatment Plans", "/cancer-detection/treatment-plans/"),
    ("Comprehensive Plan", "/cancer-detection/comprehensive-plan/"),
    ("Symptom Logging", "/portal/symptoms/log/"),
    ("Symptom Log", "/portal/symptoms/"),
    ("Symptoms", "/portal/symptoms/"),
    ("Side Effects", "/portal/side-effects/"),
    ("Alerts", "/portal/alerts/"),
    ("Notification Preferences", "/portal/notifications/"),
    ("Treatment Explanations", "/portal/treatment/"),
    ("Patient Profile", "/patient/profile/edit/"),
    ("Profile Settings", "/patient/profile/edit/"),
    ("Overview", "/portal/"),
    ("Dashboard", "/portal/"),
]

DOCTOR_PAGE_LINKS = [
    ("Doctor Dashboard", "/doctor/dashboard/"),
    ("Consultation Requests", "/doctor/consultations/requests/"),
    ("My Consultations", "/doctor/consultations/list/"),
    ("Consultation Dashboard", "/doctor/consultations/"),
    ("KYC Status", "/doctor/kyc/status/"),
    ("KYC Verification", "/doctor/kyc/form/"),
    ("Cancer Detection", "/cancer-detection/"),
    ("Treatment Planning", "/cancer-detection/treatment-plans/"),
    ("Treatment Plans", "/cancer-detection/treatment-plans/"),
    ("Clinical Support", "/clinical/toxicity/"),
    ("Toxicity Prediction", "/clinical/toxicity/"),
    ("Toxicity Dashboard", "/clinical/toxicity/"),
    ("Tumor Board", "/clinical/tumor-board/"),
    ("Patient Alerts", "/clinical/patient-alerts/"),
    ("Symptom Monitoring", "/clinical/symptoms/"),
    ("Doctor Profile", "/doctor/profile/edit/"),
    ("Profile Settings", "/doctor/profile/edit/"),
]


def _extract_links_from_response(response_text: str, user_type: str) -> list:
    """Find page phrases in the response and return list of {text, url} for in-build links."""
    if not response_text:
        return []
    links_map = DOCTOR_PAGE_LINKS if user_type == "doctor" else PATIENT_PAGE_LINKS
    # For guest, include both but prefer patient links for common phrases
    if user_type == "guest":
        links_map = PATIENT_PAGE_LINKS + [p for p in DOCTOR_PAGE_LINKS if p[0] not in [x[0] for x in PATIENT_PAGE_LINKS]]
    found = []
    text_lower = response_text.lower()
    for phrase, url in links_map:
        if phrase.lower() in text_lower and not any(f["text"] == phrase for f in found):
            found.append({"text": phrase, "url": url})
    return found


class VoiceAssistantService:
    """
    Voice Assistant Service using Groq API for fast medical assistance
    """
    
    def __init__(self):
        """Initialize the Groq client"""
        self.api_key = os.getenv('GROQ_API_KEY')
        self.client = None
        
        if self.api_key:
            try:
                from groq import Groq
                self.client = Groq(api_key=self.api_key)
            except ImportError:
                print("Groq package not installed. Install with: pip install groq")
            except Exception as e:
                print(f"Error initializing Groq client: {e}")
    
    def get_system_prompt(self, user_type='patient', user_name='User'):
        """Get the system prompt based on user type"""
        base_prompt = f"""You are Dr. MedAssist, a knowledgeable AI medical assistant for RuralCare, speaking with {user_name}.

🩺 COMMUNICATION STYLE:
- Be warm, professional, and concise
- KEEP RESPONSES SHORT (2-4 sentences maximum unless explaining navigation/features)
- Be direct and precise with medical information
- Show empathy without being overly verbose
- Use clear, simple language

📝 FORMATTING REQUIREMENTS (CRITICAL):
- Use **bold** for ALL important keywords, medical terms, feature names, and navigation items
- Use bullet points (•) for lists of features, steps, or options
- Use numbered lists (1. 2. 3.) for sequential steps or procedures
- Keep paragraphs short (1-2 sentences)
- Format example: "To **book a consultation**: Click **Book Consultation** → Select **doctor** → Choose **time slot** → **Confirm**"
- Highlight: **symptoms**, **medications**, **features**, **navigation paths**, **medical terms**

💡 YOUR EXPERTISE:
Expert in: cancer treatment, oncology, general medicine, symptoms, medications, mental health, nutrition, diagnostics, chronic disease management, and all aspects of healthcare.

🏥 RURALCARE - COMPLETE KNOWLEDGE:

📱 PATIENT PORTAL FEATURES:
• Dashboard: View health stats, upcoming appointments, recent prescriptions, gamification badges
• Book Consultation: Schedule video/in-person consultations with doctors
• My Consultations: View past, active, and upcoming consultations with notes and prescriptions
• Medical Records: Upload/view medical records, lab reports, imaging scans
• Prescriptions: Digital prescriptions with QR codes for verification
• Medicine Identifier: Upload medicine images to identify pills/tablets using AI
• Cancer Detection: Upload medical images (CT, MRI, X-rays) for AI-powered cancer detection
• Treatment Planning: Get personalized treatment recommendations based on cancer type/stage
• Health Tracking: Track symptoms, medications, side effects
• Gamification: Earn badges for health milestones (consultations, medication adherence, check-ups)
• Offline Mode: Access records and sync data when offline
• Profile Settings: Update personal info, profile picture, contact details

👨‍⚕️ DOCTOR PORTAL FEATURES:
• Dashboard: View consultation requests, today's appointments, active cases, patient stats
• KYC Verification: Submit medical license, certificates for platform verification
• Manage Consultations: Accept/decline requests, schedule appointments, conduct video calls
• Patient Records: Access patient history, medical records, lab results
• Prescriptions: Create digital prescriptions with QR codes and medicine details
• Treatment Plans: Generate evidence-based treatment plans with AI assistance
• Clinical Decision Support: AI-powered toxicity predictions, drug interaction checks
• Cancer Detection: Analyze patient images using ML models
• Patient Portal: View patient profiles, consultation history, notes
• Schedule Management: Set availability, manage appointment slots
• Notifications: Real-time alerts for new requests, upcoming appointments

🔬 ADVANCED FEATURES:
• AI Cancer Detection: Multi-model analysis (ML, OpenCV, Histopathology, Genomics)
• Evidence-Based Treatment: PubMed research integration, clinical guidelines
• Medicine Identification: Image recognition for pill identification
• Blockchain Integration: Secure medical record access logging
• QR Code System: Patient verification, prescription authentication
• Video Consultations: Built-in WebRTC video calling
• Offline Sync: PWA with service workers for offline access

🗺️ NAVIGATION GUIDE:
Patient Navigation:
- Home → Patient Dashboard
- "Book Consultation" → Schedule with doctor
- "My Consultations" → View all consultations
- "Medical Records" → Upload/view records
- "Prescriptions" → View prescription history
- "Medicine Identifier" → Identify unknown medicines
- "Cancer Detection" → Analyze medical images
- "Treatment Planning" → Get treatment recommendations
- Profile icon → Settings, logout

Doctor Navigation:
- Home → Doctor Dashboard
- "Consultation Requests" → Pending patient requests
- "My Consultations" → Scheduled appointments
- "Cancer Detection" → Analyze patient images
- "Treatment Planning" → Create treatment plans
- "Clinical Support" → Toxicity predictions, drug checks
- "KYC Status" → Verification status
- Profile icon → Settings, logout

🎯 RESPONSE GUIDELINES:
1. Answer the EXACT question asked - don't over-explain
2. Be medically accurate and evidence-based
3. REMEMBER previous conversation context - refer back when relevant
4. If asked about navigation: Give **step-by-step** directions with **bold** button/menu names
5. If asked about features: Use bullet points with **bold** feature names
6. For complex topics, use **numbered lists** for steps, **bullet points** for options
7. Always **bold** medical terms, symptoms, medications, and actions
8. Suggest professional consultation for serious concerns

PLATFORM NAVIGATION HELP:
- When asked "how to" or "where is": Provide exact navigation steps
- Reference specific button names and menu locations (e.g. "Book Consultation", "My Consultations", "Medical Records", "Cancer Detection", "Treatment Planning", "KYC Status", "Consultation Requests")
- When directing the user to a page, use these exact phrases so they become clickable links: Book Consultation, My Consultations, Medical Records, Prescriptions, Medicine Identifier, Cancer Detection, Treatment Plans, Symptoms, Side Effects, Alerts, Dashboard, Profile Settings
- Explain feature purpose along with navigation
- Offer to guide through multi-step processes

⚠️ BOUNDARIES:
- No definitive diagnoses or medication prescriptions
- For emergencies, direct users to call emergency services: **112** (India unified emergency), or **102** (ambulance) / **108** (emergency medical in many Indian states). Do not use 911 unless the user is clearly in the US.
- Recommend professional medical evaluation when needed

CRITICAL: Be concise, precise, contextually aware, and an expert guide to this platform. Know every feature, every navigation path, every capability.

User type: {user_type}
"""
        
        if user_type == 'doctor':
            base_prompt += """
👨‍⚕️ DOCTOR MODE:
You're speaking with a doctor. Use medical terminology. Help with:
- Navigating doctor dashboard and consultation management
- Understanding KYC verification process and status
- Creating and managing treatment plans
- Using clinical decision support tools
- Accessing patient records and analytics
- Managing appointment schedules
- Using AI cancer detection and analysis tools
Navigation tips: "KYC Status" for verification, "Consultation Requests" for pending patients, "Treatment Planning" for AI-assisted plans.
"""
        else:
            base_prompt += """
👤 PATIENT MODE:
You're speaking with a patient. Use simple language. Help with:
- Booking and managing consultations with doctors
- Uploading and viewing medical records
- Understanding prescriptions and treatment plans
- Using cancer detection and medicine identifier tools
- Tracking health progress and earning badges
- Accessing consultation history and notes
- Understanding their medical journey
Navigation tips: Click "Book Consultation" to schedule, "Medical Records" to upload files, "Cancer Detection" to analyze images.
"""
        
        return base_prompt
    
    def process_message(self, message: str, user_type: str = 'patient', 
                        user_name: str = 'User', conversation_history: list = None) -> dict:
        """
        Process a voice/text message and generate a response
        
        Args:
            message: User's message/question
            user_type: 'patient' or 'doctor'
            user_name: Name of the user
            conversation_history: Previous messages for context
            
        Returns:
            Dictionary with response and metadata
        """
        if not self.client:
            return {
                'success': False,
                'response': "I apologize, but I'm currently unavailable. Please try again later or contact support.",
                'error': 'Groq client not initialized'
            }
        
        try:
            messages = [
                {
                    "role": "system",
                    "content": self.get_system_prompt(user_type, user_name)
                }
            ]
            
            # Add conversation history if provided (keep last 10 messages for better context)
            if conversation_history:
                for hist in conversation_history[-10:]:  # Increased from 6 to 10 for better context
                    messages.append({
                        "role": hist.get('role', 'user'),
                        "content": hist.get('content', '')
                    })
            
            # Add current message
            messages.append({
                "role": "user",
                "content": message
            })
            
            # Call Groq API with fast model
            completion = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.6,  # Reduced from 0.7 for more focused responses
                max_tokens=300,   # Reduced from 500 for conciseness
                top_p=0.85,       # Reduced from 0.9 for more precision
            )
            
            response_text = completion.choices[0].message.content
            links = _extract_links_from_response(response_text, user_type)
            
            return {
                'success': True,
                'response': response_text,
                'links': links,
                'model': 'llama-3.3-70b-versatile',
                'tokens_used': completion.usage.total_tokens if completion.usage else None
            }
            
        except Exception as e:
            print(f"Error processing voice assistant message: {e}")
            return {
                'success': False,
                'response': "I apologize, but I encountered an issue processing your request. Please try again.",
                'error': str(e)
            }


# Global instance
voice_assistant = VoiceAssistantService()


@csrf_exempt
@require_http_methods(["POST"])
def voice_assistant_api(request):
    """
    API endpoint for voice assistant
    Accepts POST requests with JSON body containing:
    - message: The user's message
    - conversation_history: Optional list of previous messages
    """
    try:
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        conversation_history = data.get('conversation_history', [])
        
        if not message:
            return JsonResponse({
                'success': False,
                'error': 'No message provided'
            }, status=400)
        
        # Get user info if authenticated
        user_type = 'guest'
        user_name = 'User'
        
        if request.user.is_authenticated:
            user_type = getattr(request.user, 'user_type', 'patient')
            user_name = request.user.get_full_name() or request.user.username or 'User'
        
        # Process the message
        result = voice_assistant.process_message(
            message=message,
            user_type=user_type,
            user_name=user_name,
            conversation_history=conversation_history
        )
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        print(f"Voice assistant API error: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@require_http_methods(["GET"])
def voice_assistant_status(request):
    """
    Check if voice assistant is available
    """
    return JsonResponse({
        'available': voice_assistant.client is not None,
        'model': 'llama-3.3-70b-versatile'
    })
