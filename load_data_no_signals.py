"""
Load data fixture with signals disabled to avoid errors during migration.
"""

import os
import sys
from pathlib import Path
from django.core import serializers
from django.db import connections, transaction
from django.apps import apps
import json

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cancer_treatment_system.settings')

import django
django.setup()

from django.core.signals import request_started
from django.db.models.signals import pre_init, post_init, pre_save, post_save, pre_delete, post_delete, m2m_changed

# Get fixture file from command line
if len(sys.argv) < 2:
    print("Usage: python load_data_no_signals.py <fixture_file>")
    sys.exit(1)

fixture_file = sys.argv[1]

print(f"Loading data from {fixture_file} with signals disabled...")
print()

# Disable all signals
signals_to_disable = [
    pre_init, post_init, pre_save, post_save,
    pre_delete, post_delete, m2m_changed, request_started
]

receivers_cache = []
for signal in signals_to_disable:
    receivers_cache.append((signal, signal.receivers))
    signal.receivers = []

try:
    with open(fixture_file, 'r', encoding='utf-8') as f:
        objects = serializers.deserialize('json', f, ignorenonexistent=True)
        
        with transaction.atomic():
            count = 0
            for obj in objects:
                obj.save()
                count += 1
                if count % 100 == 0:
                    print(f"Loaded {count} objects...", end='\r')
            
            print(f"\n[OK] Loaded {count} objects successfully")
            
except Exception as e:
    print(f"[FAIL] Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
    
finally:
    # Restore signals
    for signal, receivers in receivers_cache:
        signal.receivers = receivers

print("Signals restored")
print("[OK] Migration complete")
