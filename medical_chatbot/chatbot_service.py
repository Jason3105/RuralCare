"""
AI Chatbot Service using Groq LLM
Provides medical assistance with full patient context
"""
import os
from groq import Groq
from .context_builder import MedicalContextBuilder
import json


class MedicalChatbot:
    """AI-powered medical chatbot with patient context"""
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get or create singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        self.model = "llama-3.3-70b-versatile"  # Fast and accurate
        
    def get_response(self, patient, user_message, conversation_history=None):
        """
        Get AI response with full medical context
        
        Args:
            patient: User object
            user_message: User's question
            conversation_history: List of previous messages
            
        Returns:
            dict with response and context used
        """
        # Build medical context
        context_builder = MedicalContextBuilder(patient)
        medical_context = context_builder.get_context_summary()
        
        # Build system prompt
        system_prompt = self._build_system_prompt(medical_context)
        
        # Build messages for Groq
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-10:]:  # Last 10 messages for context
                messages.append({
                    "role": msg['role'],
                    "content": msg['content']
                })
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        try:
            # Get response from Groq
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=1500,
                top_p=0.9,
            )
            
            assistant_message = response.choices[0].message.content
            
            return {
                'success': True,
                'response': assistant_message,
                'context_used': {
                    'has_medical_history': bool(medical_context),
                    'context_length': len(medical_context),
                },
                'model': self.model,
            }
            
        except Exception as e:
            return {
                'success': False,
                'response': f"I apologize, but I encountered an error: {str(e)}. Please try again.",
                'error': str(e),
            }
    
    def _build_system_prompt(self, medical_context):
        """Build comprehensive system prompt with medical context"""
        
        prompt = f"""You are a helpful medical AI assistant for RuralCare, a healthcare platform for rural communities. You have access to the patient's complete medical records and history.

IMPORTANT GUIDELINES:
1. You have access to the patient's ACTUAL medical data below. Use this information to answer their questions accurately.
2. Be empathetic, clear, and supportive in your responses.
3. When discussing medical conditions, use simple language but be accurate.
4. If asked about their medical history, diagnoses, treatments, or symptoms, refer to the PATIENT MEDICAL CONTEXT below.
5. Always prioritize patient safety - if something seems urgent, advise them to contact their doctor or seek emergency care.
6. You can discuss their medications, treatment plans, symptoms, and test results based on the data provided.
7. If asked about something not in their medical records, be honest and suggest they consult their healthcare provider.
8. Provide specific dates and details when available from their records.
9. Do NOT make up information - only use what's in the patient context below.
10. You can help them understand their diagnoses, treatment plans, and medications in simple terms.

PATIENT MEDICAL CONTEXT:
{medical_context}

Based on this information, answer the patient's questions accurately and helpfully. If they ask about their medical history, refer to the specific data above."""

        return prompt
    
    def generate_conversation_title(self, first_message):
        """Generate a title for the conversation based on first message"""
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": "Generate a short, descriptive title (max 6 words) for a medical conversation based on the user's first message. Just return the title, nothing else."
                    },
                    {
                        "role": "user",
                        "content": first_message
                    }
                ],
                temperature=0.7,
                max_tokens=20,
            )
            
            title = response.choices[0].message.content.strip()
            # Remove quotes if present
            title = title.strip('"\'')
            return title[:100]  # Limit length
            
        except:
            return "Medical Conversation"
