"""
Telegram Integration Views
Handles Telegram webhook, account linking, and bot interactions
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from authentication.models import PatientProfile
from .telegram_service import TelegramBotService
import json
import logging

logger = logging.getLogger(__name__)
telegram_bot = TelegramBotService()


@csrf_exempt
@require_POST
def telegram_webhook(request):
    """
    Handle incoming Telegram webhook updates
    Used for bot initialization and patient account linking
    """
    try:
        update = json.loads(request.body.decode('utf-8'))
        logger.info(f"Telegram webhook received: {update}")
        
        if 'message' in update:
            message = update['message']
            chat_id = str(message['chat']['id'])
            text = message.get('text', '').strip()
            
            # Handle /start command
            if text.startswith('/start'):
                username = message['chat'].get('username', '')
                first_name = message['chat'].get('first_name', '')
                
                # Extract verification code if present: /start <code>
                parts = text.split()
                if len(parts) > 1:
                    verification_code = parts[1]
                    
                    # Try to find patient with this verification code
                    try:
                        patient_profile = PatientProfile.objects.get(
                            user__username=verification_code
                        )
                        
                        # Link Telegram account
                        patient_profile.telegram_chat_id = chat_id
                        patient_profile.telegram_username = username
                        patient_profile.telegram_notifications_enabled = True
                        patient_profile.save()
                        
                        # Send confirmation message
                        welcome_message = (
                            f"✅ <b>Account Linked Successfully!</b>\n\n"
                            f"Hi {first_name}! Your Telegram account has been linked to your Cancer Treatment Portal account.\n\n"
                            f"You will now receive important notifications about:\n"
                            f"• 🔔 Symptom reminders\n"
                            f"• 👨‍⚕️ Doctor reviews\n"
                            f"• 📅 Appointments\n"
                            f"• 💊 Medication schedules\n"
                            f"• ℹ️ Treatment updates\n\n"
                            f"You can manage notification preferences in your portal settings."
                        )
                        telegram_bot.send_message(chat_id, welcome_message)
                        
                    except PatientProfile.DoesNotExist:
                        error_message = (
                            "❌ <b>Invalid Verification Code</b>\n\n"
                            "Please use the link provided in your patient portal settings to connect your account."
                        )
                        telegram_bot.send_message(chat_id, error_message)
                else:
                    # Generic /start message
                    welcome_message = (
                        f"👋 Welcome to <b>Cancer Treatment Portal</b> notifications!\n\n"
                        f"To link your account:\n"
                        f"1. Log in to the patient portal\n"
                        f"2. Go to Notification Settings\n"
                        f"3. Click 'Link Telegram Account'\n"
                        f"4. Use the provided link or scan QR code\n\n"
                        f"Once linked, you'll receive important treatment updates and reminders."
                    )
                    telegram_bot.send_message(chat_id, welcome_message)
            
            # Handle /stop command (disable notifications)
            elif text == '/stop':
                try:
                    patient_profile = PatientProfile.objects.get(telegram_chat_id=chat_id)
                    patient_profile.telegram_notifications_enabled = False
                    patient_profile.save()
                    
                    message_text = (
                        "🔕 <b>Notifications Disabled</b>\n\n"
                        "You will no longer receive notifications from the Cancer Treatment Portal.\n\n"
                        "To re-enable notifications, visit your portal settings or send /start"
                    )
                    telegram_bot.send_message(chat_id, message_text)
                except PatientProfile.DoesNotExist:
                    pass
            
            # Handle /help command
            elif text == '/help':
                help_message = (
                    "📋 <b>Available Commands:</b>\n\n"
                    "/start - Link your account or re-enable notifications\n"
                    "/stop - Disable notifications\n"
                    "/help - Show this help message\n\n"
                    "For support, contact your healthcare provider through the patient portal."
                )
                telegram_bot.send_message(chat_id, help_message)
        
        return JsonResponse({'status': 'ok'})
        
    except Exception as e:
        logger.error(f"Telegram webhook error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@login_required
def link_telegram_account(request):
    """
    Generate a deep link for patients to connect their Telegram account
    """
    try:
        patient_profile = PatientProfile.objects.get(user=request.user)
        
        # Generate verification code (using username as simple code)
        verification_code = request.user.username
        
        # Create Telegram deep link
        bot_username = "ruralcarebot"  # Your bot username
        deep_link = f"https://t.me/{bot_username}?start={verification_code}"
        
        context = {
            'deep_link': deep_link,
            'is_linked': bool(patient_profile.telegram_chat_id),
            'telegram_username': patient_profile.telegram_username,
            'notifications_enabled': patient_profile.telegram_notifications_enabled
        }
        
        return render(request, 'patient_portal/telegram_link.html', context)
        
    except PatientProfile.DoesNotExist:
        messages.error(request, "Patient profile not found.")
        return redirect('patient_portal:notification_preferences')


@login_required
@require_POST
def unlink_telegram_account(request):
    """
    Unlink patient's Telegram account
    """
    try:
        patient_profile = PatientProfile.objects.get(user=request.user)
        
        # Send goodbye message before unlinking
        if patient_profile.telegram_chat_id:
            goodbye_message = (
                "👋 <b>Account Unlinked</b>\n\n"
                "Your Telegram account has been disconnected from the Cancer Treatment Portal.\n\n"
                "You can reconnect anytime through your portal settings."
            )
            telegram_bot.send_message(patient_profile.telegram_chat_id, goodbye_message)
        
        # Unlink account
        patient_profile.telegram_chat_id = None
        patient_profile.telegram_username = None
        patient_profile.telegram_notifications_enabled = False
        patient_profile.save()
        
        messages.success(request, "Telegram account unlinked successfully.")
        
    except PatientProfile.DoesNotExist:
        messages.error(request, "Patient profile not found.")
    
    return redirect('patient_portal:notification_preferences')
