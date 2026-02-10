"""
Django Signals for Gamification and Notifications
Automatically check for badges and send notifications when activities occur
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PatientSymptomLog, PatientAlert
from .consultation_models import Consultation
from .prescription_models import Prescription
from .gamification_service import GamificationService
from .telegram_service import TelegramBotService
import logging

logger = logging.getLogger(__name__)
telegram_bot = TelegramBotService()


@receiver(post_save, sender=PatientAlert)
def send_telegram_notification(sender, instance, created, **kwargs):
    """
    Automatically send Telegram notification when a PatientAlert is created or updated
    """
    if created:
        # Only send for newly created alerts
        try:
            telegram_bot.send_alert_notification(instance)
            logger.info(f"Telegram notification sent for alert {instance.id}")
        except Exception as e:
            logger.error(f"Failed to send Telegram notification for alert {instance.id}: {str(e)}")
    elif instance.status == 'pending' and instance.sent_at is None:
        # Resend if alert was updated and hasn't been sent yet
        try:
            telegram_bot.send_alert_notification(instance)
            logger.info(f"Telegram notification resent for alert {instance.id}")
        except Exception as e:
            logger.error(f"Failed to resend Telegram notification for alert {instance.id}: {str(e)}")


@receiver(post_save, sender=Consultation)
def send_consultation_telegram_notification(sender, instance, created, **kwargs):
    """
    Send Telegram notification when consultation is created or status changes
    """
    try:
        if created:
            # New consultation scheduled
            telegram_bot.send_consultation_notification(instance, 'scheduled')
        else:
            # Check for status changes
            if instance.status == 'completed':
                telegram_bot.send_consultation_notification(instance, 'completed')
            elif instance.status == 'cancelled':
                telegram_bot.send_consultation_notification(instance, 'cancelled')
    except Exception as e:
        logger.error(f"Failed to send consultation Telegram notification: {str(e)}")


@receiver(post_save, sender=Prescription)
def send_prescription_telegram_notification(sender, instance, created, **kwargs):
    """
    Send Telegram notification when a new prescription is created
    """
    if created:
        try:
            telegram_bot.send_prescription_notification(instance)
            logger.info(f"Telegram notification sent for prescription {instance.id}")
        except Exception as e:
            logger.error(f"Failed to send prescription Telegram notification: {str(e)}")


@receiver(post_save, sender=PatientSymptomLog)
def check_badges_on_symptom_log(sender, instance, created, **kwargs):
    """Check for badges when a symptom log is created"""
    if created:
        # Award points for logging symptoms
        GamificationService.award_points(
            instance.patient,
            points=10,
            activity_type='symptom_logged',
            description='Logged symptoms'
        )
        
        # Check for badge eligibility
        activity_data = {
            'id': str(instance.id),
            'log_date': instance.log_date.isoformat(),
        }
        GamificationService.check_and_award_badges(
            instance.patient,
            activity_type='symptom_logged',
            activity_data=activity_data
        )
        
        # Check for level up
        GamificationService.check_level_up(instance.patient)

