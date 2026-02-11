"""
Groq-based Medicine Identifier Service
Uses Groq's fast LLM inference to identify medicines and generate comprehensive details
"""

import os
import json
from typing import Dict, Optional
from datetime import datetime


class GroqMedicineIdentifier:
    """
    AI-powered medicine identification using Groq API
    Provides comprehensive medicine information based on extracted text and visual features
    """
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get or create singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        """Initialize the Groq medicine identifier"""
        # Try multiple ways to get the API key
        self.api_key = os.getenv('GROQ_API_KEY')
        
        # If not in environment, try loading from .env file directly
        if not self.api_key:
            try:
                from dotenv import load_dotenv
                load_dotenv()
                self.api_key = os.getenv('GROQ_API_KEY')
            except ImportError:
                pass
        
        # Also try Django settings
        if not self.api_key:
            try:
                from django.conf import settings
                self.api_key = getattr(settings, 'GROQ_API_KEY', None)
            except:
                pass
        
        self.client = None
        
        if self.api_key:
            try:
                from groq import Groq
                self.client = Groq(api_key=self.api_key)
                print(f"Groq client initialized successfully")
            except ImportError:
                print("Groq package not installed. Install with: pip install groq")
            except Exception as e:
                print(f"Error initializing Groq client: {e}")
        else:
            print("WARNING: GROQ_API_KEY not found in environment variables")
    
    def identify_medicine(
        self, 
        extracted_text: str, 
        image_analysis: Dict,
        detected_info: Dict
    ) -> Dict:
        """
        Identify medicine and generate comprehensive details using Groq AI
        
        Args:
            extracted_text: Text extracted from medicine image via OCR
            image_analysis: Visual analysis results (colors, shapes, etc.)
            detected_info: Pre-extracted medicine info (dosage, form, etc.)
            
        Returns:
            Dictionary with comprehensive medicine information
        """
        if not self.client:
            return self._get_fallback_response(extracted_text, detected_info)
        
        try:
            # Build context from available information
            context = self._build_context(extracted_text, image_analysis, detected_info)
            
            # Create detailed prompt
            prompt = self._create_identification_prompt(context)
            
            # Call Groq API
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # Fast and capable model
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert pharmacist and medical AI assistant with extensive knowledge of pharmaceutical products worldwide, especially Indian medicines.

Your task is to identify medicines from:
1. Text extracted from medicine images (may be partial or unclear)
2. Visual descriptions (colors, shapes, forms)
3. Filename hints that may contain medicine names
4. Any detected patterns like dosages, medicine forms, etc.

IDENTIFICATION STRATEGIES:
- If you see a filename hint like "crocin tablet" or "dolo 650", use that as the primary identifier
- Common Indian medicine brands: Crocin, Dolo, Calpol, Combiflam, Brufen, Disprin, Ecosprin, etc.
- Look for partial matches - "croc" might mean Crocin, "para" might mean Paracetamol
- If dosage is visible (500mg, 650mg), use it to narrow down the medicine
- Visual features like red/yellow tablets can help identify specific products

CRITICAL VALIDATION RULES:
1. If the text/context clearly indicates NON-MEDICINE content (food, animals, people, landscapes, electronics, vehicles, clothing, etc.), set "identification_successful" to false and "is_not_medicine" to true
2. Examples of non-medicine: restaurant menus, food items, selfies, pet photos, car images, building photos, sports content, electronics, clothing
3. If the image appears to be random or unrelated to medicine, clearly indicate this

IMPORTANT RULES:
1. Try to identify the medicine even with limited information
2. If you're 70%+ confident, provide identification with confidence level
3. For common medicines like Crocin, Dolo, Paracetamol - provide complete accurate details
4. Always include a safety disclaimer recommending professional medical advice
5. Never make up specific dosage instructions - always recommend consulting a doctor
6. If image is NOT a medicine, set "is_not_medicine": true and explain why"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,  # Lower temperature for more accurate responses
                max_tokens=2500,
            )
            
            # Parse the response
            response_text = response.choices[0].message.content
            return self._parse_response(response_text)
            
        except Exception as e:
            print(f"Error calling Groq API: {e}")
            return self._get_fallback_response(extracted_text, detected_info, str(e))
    
    def _build_context(
        self, 
        extracted_text: str, 
        image_analysis: Dict, 
        detected_info: Dict
    ) -> str:
        """Build context string from all available information"""
        context_parts = []
        
        # Add extracted text
        if extracted_text:
            context_parts.append(f"TEXT EXTRACTED FROM IMAGE:\n{extracted_text}")
        
        # Add detected information
        if detected_info:
            detected_parts = []
            if detected_info.get('filename_hint'):
                detected_parts.append(f"- Filename hint (user's filename): {detected_info['filename_hint']}")
            if detected_info.get('dosage'):
                detected_parts.append(f"- Detected dosage: {detected_info['dosage']}")
            if detected_info.get('form'):
                detected_parts.append(f"- Detected form: {detected_info['form']}")
            if detected_info.get('possible_names'):
                detected_parts.append(f"- Possible names: {', '.join(detected_info['possible_names'])}")
            if detected_info.get('expiry'):
                detected_parts.append(f"- Expiry date: {detected_info['expiry']}")
            if detected_info.get('batch_number'):
                detected_parts.append(f"- Batch number: {detected_info['batch_number']}")
            
            if detected_parts:
                context_parts.append("DETECTED INFORMATION:\n" + "\n".join(detected_parts))
        
        # Add visual analysis
        if image_analysis:
            visual_parts = []
            if image_analysis.get('dominant_colors'):
                colors = [c['color'] for c in image_analysis['dominant_colors']]
                visual_parts.append(f"- Dominant colors: {', '.join(colors)}")
            if image_analysis.get('detected_form'):
                visual_parts.append(f"- Visual form detection: {image_analysis['detected_form']}")
            if image_analysis.get('circular_objects'):
                visual_parts.append(f"- Circular objects detected: {image_analysis['circular_objects']}")
            
            if visual_parts:
                context_parts.append("VISUAL ANALYSIS:\n" + "\n".join(visual_parts))
        
        return "\n\n".join(context_parts)
    
    def _create_identification_prompt(self, context: str) -> str:
        """Create the identification prompt for Groq"""
        return f"""Based on the following information extracted from a medicine image, identify the medicine and provide comprehensive details.

{context}

Please provide a detailed response in the following JSON format:
{{
    "identification_successful": true/false,
    "is_not_medicine": true/false,
    "invalid_image_reason": "Explain why this is not a medicine image (only if is_not_medicine is true)",
    "confidence_level": "high/medium/low",
    "medicine_name": "Name of the medicine",
    "generic_name": "Generic/active ingredient name",
    "brand_name": "Brand name if identifiable",
    "manufacturer": "Manufacturer if identifiable",
    "drug_class": "Therapeutic class (e.g., Analgesic, Antibiotic, etc.)",
    "medicine_form": "tablet/capsule/syrup/cream/ointment/gel/injection/drops/spray/inhaler/powder/other",
    "strength": "e.g., 500mg, 10ml, etc.",
    "description": "Brief description of what this medicine is",
    "uses": ["Primary use 1", "Primary use 2", "..."],
    "mechanism_of_action": "How the medicine works",
    "dosage_instructions": "General dosage guidelines (always recommend consulting a doctor)",
    "side_effects": {{
        "common": ["Common side effect 1", "..."],
        "serious": ["Serious side effect 1", "..."],
        "rare": ["Rare side effect 1", "..."]
    }},
    "warnings": ["Warning 1", "Warning 2", "..."],
    "contraindications": ["Contraindication 1", "..."],
    "drug_interactions": ["Interaction 1", "..."],
    "pregnancy_category": "Category if known",
    "storage_instructions": "How to store the medicine",
    "active_ingredients": ["Ingredient 1", "..."],
    "inactive_ingredients": ["Ingredient 1", "..."],
    "prescription_required": true/false,
    "additional_info": "Any other important information",
    "safety_disclaimer": "Important safety message for the user"
}}

IMPORTANT:
1. If the image/text clearly shows NON-MEDICINE content, set "identification_successful" to false AND "is_not_medicine" to true, with "invalid_image_reason" explaining what was detected.
2. If you cannot identify the medicine with confidence but it MIGHT be medicine, set "identification_successful" to false and "is_not_medicine" to false.
3. Always include a safety disclaimer recommending professional medical advice.
4. Provide accurate information - do not make up details you're not sure about.
5. If the text is unclear or incomplete, mention what information would help with better identification.

Respond ONLY with the JSON object, no additional text."""
    
    def _parse_response(self, response_text: str) -> Dict:
        """Parse the Groq API response into structured data"""
        try:
            # Try to extract JSON from response
            # Sometimes the model might wrap it in markdown code blocks
            json_text = response_text
            
            # Remove markdown code blocks if present
            if '```json' in json_text:
                json_text = json_text.split('```json')[1].split('```')[0]
            elif '```' in json_text:
                json_text = json_text.split('```')[1].split('```')[0]
            
            # Parse JSON
            result = json.loads(json_text.strip())
            
            # Ensure required fields exist
            result.setdefault('identification_successful', False)
            result.setdefault('is_not_medicine', False)
            result.setdefault('invalid_image_reason', None)
            result.setdefault('confidence_level', 'low')
            result.setdefault('medicine_name', None)
            result.setdefault('uses', [])
            result.setdefault('side_effects', {'common': [], 'serious': [], 'rare': []})
            result.setdefault('warnings', [])
            result.setdefault('safety_disclaimer', 
                "This information is for educational purposes only. Always consult a healthcare professional before using any medication.")
            
            return result
            
        except json.JSONDecodeError as e:
            # If JSON parsing fails, try to extract key information
            return {
                'identification_successful': False,
                'confidence_level': 'low',
                'medicine_name': None,
                'raw_response': response_text,
                'parse_error': str(e),
                'safety_disclaimer': "Could not parse AI response. Please consult a pharmacist for accurate medicine identification."
            }
    
    def _get_fallback_response(
        self, 
        extracted_text: str, 
        detected_info: Dict,
        error: str = None
    ) -> Dict:
        """Generate fallback response when API is unavailable"""
        response = {
            'identification_successful': False,
            'confidence_level': 'low',
            'medicine_name': None,
            'api_error': error or "Groq API not available",
            'extracted_data': {
                'text': extracted_text,
                'detected_info': detected_info
            },
            'suggestions': [
                "The AI service is currently unavailable.",
                "Based on the extracted text and detected information:",
            ],
            'safety_disclaimer': "Please consult a pharmacist or healthcare professional for accurate medicine identification."
        }
        
        # Add any detected information
        if detected_info:
            if detected_info.get('possible_names'):
                response['suggestions'].append(
                    f"Possible medicine names detected: {', '.join(detected_info['possible_names'])}"
                )
            if detected_info.get('dosage'):
                response['strength'] = detected_info['dosage']
            if detected_info.get('form'):
                response['medicine_form'] = detected_info['form']
        
        return response
    
    def get_additional_info(self, medicine_name: str) -> Dict:
        """
        Get additional information about a specific medicine
        Useful when user wants more details about an identified medicine
        """
        if not self.client or not medicine_name:
            return {'error': 'Cannot fetch additional information'}
        
        try:
            prompt = f"""Provide comprehensive medical information about the medicine: {medicine_name}

Include:
1. Complete list of uses and indications
2. Detailed side effects (common, uncommon, serious)
3. Drug interactions to be aware of
4. Special precautions for elderly, children, pregnant women
5. Overdose symptoms and what to do
6. Alternative medicines with similar effects

Format as JSON with clear categories."""

            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a pharmaceutical information specialist. Provide accurate, detailed medicine information in JSON format."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            
            return self._parse_response(response.choices[0].message.content)
            
        except Exception as e:
            return {'error': str(e)}
    
    def check_drug_interaction(self, medicine1: str, medicine2: str) -> Dict:
        """
        Check for potential interactions between two medicines
        """
        if not self.client:
            return {'error': 'Groq API not available'}
        
        try:
            prompt = f"""Analyze potential drug interactions between:
1. {medicine1}
2. {medicine2}

Provide:
1. Interaction severity (none/mild/moderate/severe)
2. Description of interaction
3. Mechanism of interaction
4. Recommendations
5. Alternatives if interaction is significant

Format as JSON."""

            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a clinical pharmacologist expert in drug interactions. Provide accurate interaction information."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                max_tokens=1000,
            )
            
            return self._parse_response(response.choices[0].message.content)
            
        except Exception as e:
            return {'error': str(e)}
