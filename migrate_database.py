"""
Database Migration Script - Django Approach
Migrates data from filled DB to empty DB using Django's serialization
"""

import os
import sys
from pathlib import Path

# Fix Windows console encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cancer_treatment_system.settings')

import django
django.setup()

from django.core.management import call_command
from django.db import connections
from django.apps import apps
import json
from datetime import datetime

print("=" * 60)
print("RuralCare Database Migration (Django Method)")
print("=" * 60)
print()

# Source Database Credentials (FILLED)
SOURCE_DB = {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': 'postgres',
    'USER': 'postgres.wotccnylbziwbmiuvhff',
    'PASSWORD': 'Jacell@100',
    'HOST': 'aws-1-ap-northeast-2.pooler.supabase.com',
    'PORT': '6543',
    'DISABLE_SERVER_SIDE_CURSORS': True,
    'ATOMIC_REQUESTS': False,
    'AUTOCOMMIT': True,
    'CONN_MAX_AGE': 0,
    'CONN_HEALTH_CHECKS': False,
    'TIME_ZONE': None,
    'OPTIONS': {},
    'TEST': {},
}

# Target Database Credentials (EMPTY)
TARGET_DB = {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': 'postgres',
    'USER': 'postgres.kdbsweordecndyyaltos',
    'PASSWORD': 'JacellJamble',
    'HOST': 'aws-1-ap-south-1.pooler.supabase.com',
    'PORT': '5432',
    'DISABLE_SERVER_SIDE_CURSORS': True,
    'ATOMIC_REQUESTS': False,
    'AUTOCOMMIT': True,
    'CONN_MAX_AGE': 0,
    'CONN_HEALTH_CHECKS': False,
    'TIME_ZONE': None,
    'OPTIONS': {},
    'TEST': {},
}

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
dump_file = f"ruralcare_data_{timestamp}.json"

print("Step 1: Exporting data from source database...")
print(f"Source: {SOURCE_DB['HOST']}")
print()

# Temporarily configure source database
from django.conf import settings
from django.db import connection, connections
settings.DATABASES['default'] = SOURCE_DB

# Force close any existing connection and reset
connection.close()
del connections['default']

try:
    # Test connection - get fresh connection with new settings
    connection = connections['default']
    connection.ensure_connection()
    # Disable server-side cursors for PgBouncer compatibility
    connection.disable_server_side_cursors = True
    print("[OK] Connected to source database")
    
    # Export all data
    with open(dump_file, 'w', encoding='utf-8') as f:
        call_command('dumpdata', 
                    '--natural-foreign', 
                    '--natural-primary',
                    '--indent', '2',
                    '--exclude', 'contenttypes',
                    '--exclude', 'auth.permission',
                    stdout=f)
    
    print(f"[OK] Data exported successfully to {dump_file}")
    print()
    
except Exception as e:
    print(f"[FAIL] Export failed: {e}")
    sys.exit(1)
finally:
    connection.close()

print("Step 2: Importing data to target database...")
print(f"Target: {TARGET_DB['HOST']}")
print()

# Switch to target database
settings.DATABASES['default'] = TARGET_DB

# Force close and reset connection for target
connection.close()
del connections['default']

try:
    # Test connection - get fresh connection with new settings
    connection = connections['default']
    connection.ensure_connection()
    connection.disable_server_side_cursors = True
    print("[OK] Connected to target database")
    
    # Run migrations first to ensure schema exists
    print("Running migrations on target database...")
    call_command('migrate', '--no-input')
    print("[OK] Migrations complete")
    print()
    
    # Import data
    print("Importing data...")
    call_command('loaddata', dump_file)
    print("[OK] Data imported successfully")
    print()
    
    print("=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print()
    print("Next Steps:")
    print("1. Update your .env file with new database credentials:")
    print(f"   DB_HOST={TARGET_DB['HOST']}")
    print(f"   DB_PORT={TARGET_DB['PORT']}")
    print(f"   DB_USER={TARGET_DB['USER']}")
    print(f"   DB_PASSWORD={TARGET_DB['PASSWORD']}")
    print()
    print("2. Update Render environment variables with new credentials")
    print()
    print(f"Backup file saved: {dump_file}")
    print("Keep this file safe in case you need to rollback!")
    
except Exception as e:
    print(f"[FAIL] Import failed: {e}")
    print()
    print("Common issues:")
    print("- Check if target database is truly empty")
    print("- Verify all credentials are correct")
    print("- Ensure network connectivity to both databases")
    sys.exit(1)
finally:
    connection.close()
