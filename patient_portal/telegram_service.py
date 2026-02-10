"""
Telegram Bot Service for Patient Notifications
Sends alerts, reminders, and updates to patients via Telegram
"""

import os
import requests
import logging
from django.conf import settings
from django.urls import reverse
from authentication.models import PatientProfile

logger = logging.getLogger(__name__)


class TelegramBotService:
    """
    Service for sending notifications via Telegram Bot
    """
    
    def __init__(self):
        """Initialize Telegram Bot with token"""
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '8182454698:AAHnjMMS8DQ8J39M6rTwmL2qWDisUm5HWPA')
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.web_app_url = os.getenv('WEB_APP_URL', 'http://localhost:8000')
    
    def send_message(self, chat_id, message, parse_mode='HTML', reply_markup=None):
        """
        Send a message to a Telegram user
        
        Args:
            chat_id: Telegram chat ID of the user
            message: Message text to send
            parse_mode: 'HTML' or 'Markdown'
            reply_markup: Optional inline keyboard markup
            
        Returns:
            dict: API response or error
        """
        if not chat_id:
            logger.warning("No chat_id provided for Telegram message")
            return {'success': False, 'error': 'No chat_id'}
        
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            
            if reply_markup:
                payload['reply_markup'] = reply_markup
            
            response = requests.post(url, json=payload, timeout=10)
            result = response.json()
            
            if result.get('ok'):
                logger.info(f"Telegram message sent successfully to {chat_id}")
                return {'success': True, 'message_id': result.get('result', {}).get('message_id')}
            else:
                logger.error(f"Telegram API error: {result.get('description')}")
                return {'success': False, 'error': result.get('description')}
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Telegram request failed: {e}")
            return {'success': False, 'error': str(e)}
        except Exception as e:
            logger.error(f"Telegram message error: {e}")
            return {'success': False, 'error': str(e)}
    
    def format_alert_message(self, alert):
        """
        Format a PatientAlert as a Telegram message
        
        Args:
            alert: PatientAlert model instance
            
        Returns:
            str: Formatted HTML message
        """
        # Get alert type emoji
        emoji_map = {
            'symptom_reminder': '📝',
            'doctor_review': '👨‍⚕️',
            'appointment': '📅',
            'medication': '💊',
            'reassurance': '💚',
            'general': '📢',
        }
        emoji = emoji_map.get(alert.alert_type, '🔔')
        
        # Format message
        message = f"<b>{emoji} {alert.title}</b>\n\n"
        message += f"{alert.message}\n\n"
        
        # Add action links based on alert type
        if alert.alert_type == 'symptom_reminder':
            link = f"{self.web_app_url}{reverse('log_symptoms')}"
            message += f"👉 <a href='{link}'>Log Your Symptoms Now</a>"
            
        elif alert.alert_type == 'appointment':
            link = f"{self.web_app_url}{reverse('patient_consultations')}"
            message += f"👉 <a href='{link}'>View Your Appointments</a>"
            
        elif alert.alert_type == 'medication':
            link = f"{self.web_app_url}{reverse('patient_prescriptions')}"
            message += f"👉 <a href='{link}'>View Your Prescriptions</a>"
            
        elif alert.alert_type == 'doctor_review':
            link = f"{self.web_app_url}{reverse('patient_dashboard')}"
            message += f"👉 <a href='{link}'>View Doctor's Response</a>"
            
        else:
            link = f"{self.web_app_url}{reverse('patient_dashboard')}"
            message += f"👉 <a href='{link}'>Go to Dashboard</a>"
        
        # Add footer
        message += f"\n\n<i>Cancer Treatment Planning System</i>"
        
        return message
    
    def send_alert_notification(self, alert):
        """
        Send a patient alert via Telegram
        
        Args:
            alert: PatientAlert model instance
            
        Returns:
            dict: Send result
        """
        try:
            # Get patient's Telegram chat ID from profile
            patient_profile = alert.patient.patient_profile
            
            logger.info(f"🔔 Processing alert {alert.id} for patient {alert.patient.username}")
            logger.debug(f"   Alert type: {alert.alert_type}, Title: {alert.title}")
            
            if not patient_profile.telegram_chat_id:
                logger.info(f"⏭️  Patient {alert.patient.username} has no Telegram chat_id linked - skipping")
                return {'success': False, 'error': 'No telegram_chat_id'}
            
            if not patient_profile.telegram_notifications_enabled:
                logger.info(f"🔕 Patient {alert.patient.username} has Telegram notifications disabled - skipping")
                return {'success': False, 'error': 'Notifications disabled'}
            
            logger.info(f"📤 Sending to Telegram chat_id: {patient_profile.telegram_chat_id}")
            
            # Format and send message
            message = self.format_alert_message(alert)
            logger.debug(f"   Message preview: {message[:100]}...")
            
            result = self.send_message(patient_profile.telegram_chat_id, message)
            
            if result.get('success'):
                logger.info(f"✅ Successfully sent Telegram notification for alert {alert.id}")
            else:
                logger.error(f"❌ Failed to send Telegram notification for alert {alert.id}: {result.get('error')}")
            
            return result
            
        except PatientProfile.DoesNotExist:
            logger.warning(f"⚠️  No patient profile found for user {alert.patient.username} (ID: {alert.patient.id})")
            return {'success': False, 'error': 'No patient profile'}
        except Exception as e:
            logger.error(f"💥 Error sending alert notification {alert.id}: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def send_consultation_notification(self, consultation, notification_type='scheduled'):
        """
        Send consultation-related notifications
        
        Args:
            consultation: Consultation model instance
            notification_type: 'scheduled', 'reminder', 'completed', 'cancelled'
            
        Returns:
            dict: Send result
        """
        try:
            patient_profile = consultation.patient.patient_profile
            
            if not patient_profile.telegram_chat_id:
                return {'success': False, 'error': 'No telegram_chat_id'}
            
            if not patient_profile.telegram_notifications_enabled:
                return {'success': False, 'error': 'Notifications disabled'}
            
            # Format message based on type
            if notification_type == 'scheduled':
                emoji = '✅'
                title = 'Consultation Scheduled'
                message = f"Your consultation with <b>Dr. {consultation.doctor.first_name} {consultation.doctor.last_name}</b> has been scheduled.\n\n"
                message += f"📅 Date: {consultation.scheduled_datetime.strftime('%B %d, %Y')}\n"
                message += f"🕐 Time: {consultation.scheduled_datetime.strftime('%I:%M %p')}\n"
                message += f"📝 Type: {consultation.consultation_type.title()}\n\n"
                
            elif notification_type == 'reminder':
                emoji = '⏰'
                title = 'Consultation Reminder'
                message = f"Your consultation with <b>Dr. {consultation.doctor.first_name} {consultation.doctor.last_name}</b> is coming up!\n\n"
                message += f"📅 Date: {consultation.scheduled_datetime.strftime('%B %d, %Y')}\n"
                message += f"🕐 Time: {consultation.scheduled_datetime.strftime('%I:%M %p')}\n"
                message += f"📝 Type: {consultation.consultation_type.title()}\n\n"
                
            elif notification_type == 'completed':
                emoji = '✅'
                title = 'Consultation Completed'
                message = f"Your consultation with <b>Dr. {consultation.doctor.first_name} {consultation.doctor.last_name}</b> has been completed.\n\n"
                
            elif notification_type == 'cancelled':
                emoji = '❌'
                title = 'Consultation Cancelled'
                message = f"Your consultation with <b>Dr. {consultation.doctor.first_name} {consultation.doctor.last_name}</b> has been cancelled.\n\n"
            else:
                message = ""
            
            # Add link
            link = f"{self.web_app_url}{reverse('patient_portal:my_consultations')}"
            full_message = f"<b>{emoji} {title}</b>\n\n{message}"
            full_message += f"👉 <a href='{link}'>View Consultation Details</a>\n\n"
            full_message += f"<i>Cancer Treatment Planning System</i>"
            
            return self.send_message(patient_profile.telegram_chat_id, full_message)
            
        except PatientProfile.DoesNotExist:
            logger.warning(f"No patient profile for consultation {consultation.id}")
            return {'success': False, 'error': 'No patient profile'}
        except Exception as e:
            logger.error(f"Error sending consultation notification: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def send_prescription_notification(self, prescription):
        """
        Send prescription notification
        
        Args:
            prescription: Prescription model instance
            
        Returns:
            dict: Send result
        """
        try:
            patient_profile = prescription.patient.patient_profile
            
            if not patient_profile.telegram_chat_id:
                return {'success': False, 'error': 'No telegram_chat_id'}
            
            if not patient_profile.telegram_notifications_enabled:
                return {'success': False, 'error': 'Notifications disabled'}
            
            # Format message
            message = f"<b>💊 New Prescription Received</b>\n\n"
            message += f"Dr. <b>{prescription.doctor.first_name} {prescription.doctor.last_name}</b> has prescribed medications for you.\n\n"
            message += f"📅 Date: {prescription.created_at.strftime('%B %d, %Y')}\n"
            message += f"📝 Diagnosis: {prescription.diagnosis}\n\n"
            
            # Add link
            link = f"{self.web_app_url}{reverse('patient_portal:view_prescription', args=[prescription.id])}"
            message += f"👉 <a href='{link}'>View Prescription Details</a>\n\n"
            message += f"<i>Cancer Treatment Planning System</i>"
            
            return self.send_message(patient_profile.telegram_chat_id, message)
            
        except PatientProfile.DoesNotExist:
            logger.warning(f"No patient profile for prescription {prescription.id}")
            return {'success': False, 'error': 'No patient profile'}
        except Exception as e:
            logger.error(f"Error sending prescription notification: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def get_bot_info(self):
        """Get bot information"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url, timeout=5)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get bot info: {e}")
            return {'ok': False, 'error': str(e)}


# Global instance
telegram_bot = TelegramBotService()
