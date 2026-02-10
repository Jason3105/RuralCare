"""
Manually link a patient's Telegram account for testing
Usage: python link_telegram_manual.py <username> <chat_id>
Example: python link_telegram_manual.py mayankmbhuvad8_patient 123456789
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cancer_treatment_system.settings')
django.setup()

from authentication.models import User, PatientProfile

def link_telegram(username, chat_id):
    """Link a patient's Telegram account"""
    try:
        user = User.objects.get(username=username)
        profile = user.patient_profile
        
        profile.telegram_chat_id = str(chat_id)
        profile.telegram_username = f"test_user_{chat_id}"
        profile.telegram_notifications_enabled = True
        profile.save()
        
        print(f"✅ Successfully linked Telegram for {username}")
        print(f"   Chat ID: {profile.telegram_chat_id}")
        print(f"   Notifications: {profile.telegram_notifications_enabled}")
        
    except User.DoesNotExist:
        print(f"❌ User '{username}' not found")
    except PatientProfile.DoesNotExist:
        print(f"❌ Patient profile not found for user '{username}'")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python link_telegram_manual.py <username> <chat_id>")
        print("Example: python link_telegram_manual.py patient123 987654321")
        sys.exit(1)
    
    username = sys.argv[1]
    chat_id = sys.argv[2]
    
    link_telegram(username, chat_id)
