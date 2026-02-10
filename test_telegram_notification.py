"""
Test Telegram Notification System
Creates a test alert to verify Telegram notifications are working
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cancer_treatment_system.settings')
django.setup()

from authentication.models import User, PatientProfile
from patient_portal.models import PatientAlert
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_telegram_notification():
    """Create a test alert to trigger Telegram notification"""
    
    # Get a patient user (you need to replace with actual username or create one)
    try:
        patient = User.objects.filter(is_staff=False, is_superuser=False).first()
        if not patient:
            print("❌ No patient users found in database")
            return
        
        print(f"Testing with patient: {patient.username}")
        
        # Check if patient has profile with Telegram
        try:
            profile = patient.patient_profile
            print(f"✓ Patient profile found")
            print(f"  Telegram chat_id: {profile.telegram_chat_id}")
            print(f"  Telegram username: {profile.telegram_username}")
            print(f"  Notifications enabled: {profile.telegram_notifications_enabled}")
            
            if not profile.telegram_chat_id:
                print("⚠️  WARNING: Patient has no Telegram chat_id linked!")
                print("   Please link Telegram account first through the portal")
                return
        except PatientProfile.DoesNotExist:
            print("❌ Patient has no profile")
            return
        
        # Create a test alert
        print("\n📝 Creating test alert...")
        alert = PatientAlert.objects.create(
            patient=patient,
            alert_type='general',
            title='🧪 Test Notification',
            message='This is a test notification to verify your Telegram integration is working correctly!',
            is_urgent=False
        )
        
        print(f"✅ Test alert created: {alert.id}")
        print(f"   Type: {alert.alert_type}")
        print(f"   Title: {alert.title}")
        print(f"   Status: {alert.status}")
        
        print("\n⏳ Waiting for signal to trigger...")
        print("   Check your Telegram app for the notification!")
        print("   Also check Django logs for any errors")
        
    except Exception as e:
        logger.error(f"Error during test: {str(e)}", exc_info=True)
        print(f"\n❌ Error: {str(e)}")

if __name__ == "__main__":
    print("=" * 60)
    print("Telegram Notification Test")
    print("=" * 60)
    test_telegram_notification()
    print("=" * 60)
