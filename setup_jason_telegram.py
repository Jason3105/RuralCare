"""
List all patient users and link Telegram account
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cancer_treatment_system.settings')
django.setup()

from authentication.models import User, PatientProfile

# List all patient users
print("=" * 60)
print("Available Patient Users:")
print("=" * 60)

patients = User.objects.filter(is_staff=False, is_superuser=False)
for i, user in enumerate(patients, 1):
    try:
        profile = user.patient_profile
        print(f"{i}. Username: {user.username}")
        print(f"   Name: {user.first_name} {user.last_name}")
        print(f"   Email: {user.email}")
        print(f"   Telegram linked: {'Yes' if profile.telegram_chat_id else 'No'}")
        if profile.telegram_chat_id:
            print(f"   Chat ID: {profile.telegram_chat_id}")
        print()
    except PatientProfile.DoesNotExist:
        print(f"{i}. Username: {user.username} (No profile)")
        print()

# Link JasonGonsalves or similar
print("=" * 60)
print("Attempting to link Telegram for Jason Gonsalves...")
print("=" * 60)

# Try different username patterns
possible_usernames = [
    'JasonGonsalves',
    'jasongonsalves', 
    'jason',
    'gonsalves',
    'Jason',
]

for username in possible_usernames:
    try:
        user = User.objects.get(username__iexact=username)
        profile = user.patient_profile
        
        profile.telegram_chat_id = "6066506922"
        profile.telegram_username = "JasonGonsalves"
        profile.telegram_notifications_enabled = True
        profile.save()
        
        print(f"✅ Successfully linked Telegram for {user.username}")
        print(f"   Full name: {user.first_name} {user.last_name}")
        print(f"   Chat ID: {profile.telegram_chat_id}")
        print(f"   Telegram username: {profile.telegram_username}")
        print(f"   Notifications enabled: {profile.telegram_notifications_enabled}")
        break
    except User.DoesNotExist:
        continue
    except PatientProfile.DoesNotExist:
        print(f"⚠️  User {username} found but has no patient profile")
        continue
else:
    print("❌ Could not find user matching Jason Gonsalves")
    print("\nPlease use one of the usernames listed above")
