"""
Database Migration Script - Clean approach
Migrates data from source (filled) DB to target (empty) DB.
Uses environment variables so Django settings picks them up natively.
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent

# Source Database Credentials (FILLED)
SOURCE = {
    'DB_HOST': 'aws-1-ap-northeast-2.pooler.supabase.com',
    'DB_PORT': '6543',
    'DB_NAME': 'postgres',
    'DB_USER': 'postgres.wotccnylbziwbmiuvhff',
    'DB_PASSWORD': 'Jacell@100',
}

# Target Database Credentials (EMPTY)
TARGET = {
    'DB_HOST': 'aws-1-ap-south-1.pooler.supabase.com',
    'DB_PORT': '5432',
    'DB_NAME': 'postgres',
    'DB_USER': 'postgres.kdbsweordecndyyaltos',
    'DB_PASSWORD': 'JacellJamble',
}

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
dump_file = str(BASE_DIR / f"ruralcare_data_{timestamp}.json")
manage_py = str(BASE_DIR / "manage.py")
python_exe = sys.executable

print("=" * 60)
print("RuralCare Database Migration")
print("=" * 60)
print()

# Build env for source
source_env = os.environ.copy()
source_env.update(SOURCE)
source_env['USE_LOCAL_DB'] = 'false'
source_env['PYTHONIOENCODING'] = 'utf-8'
source_env['PYTHONUTF8'] = '1'

# Build env for target
target_env = os.environ.copy()
target_env.update(TARGET)
target_env['USE_LOCAL_DB'] = 'false'
target_env['PYTHONIOENCODING'] = 'utf-8'
target_env['PYTHONUTF8'] = '1'

# --- Step 1: Export from source ---
print("Step 1: Exporting data from source database...")
print(f"Source: {SOURCE['DB_HOST']}:{SOURCE['DB_PORT']}")
print()

# We'll run dumpdata as a subprocess with the source env vars
# This avoids all the connection caching issues
export_cmd = [
    python_exe, manage_py, 'dumpdata',
    '--natural-foreign',
    '--natural-primary',
    '--indent', '2',
    '--exclude', 'contenttypes',
    '--exclude', 'auth.permission',
    '--exclude', 'medicine_identifier.MedicineDatabase',
    '--output', dump_file,
]

result = subprocess.run(export_cmd, env=source_env, capture_output=True, text=True, cwd=str(BASE_DIR))

if result.returncode != 0:
    print(f"[FAIL] Export failed!")
    print(f"stderr: {result.stderr}")
    print(f"stdout: {result.stdout}")
    sys.exit(1)

# Verify file exists and is valid
if not os.path.exists(dump_file):
    print("[FAIL] Dump file was not created")
    sys.exit(1)

file_size = os.path.getsize(dump_file)
print(f"[OK] Data exported to {dump_file} ({file_size:,} bytes)")
print()

# --- Step 2: Migrate target schema ---
print("Step 2: Running migrations on target database...")
print(f"Target: {TARGET['DB_HOST']}:{TARGET['DB_PORT']}")
print()

migrate_cmd = [python_exe, manage_py, 'migrate', '--no-input']
result = subprocess.run(migrate_cmd, env=target_env, capture_output=True, text=True, cwd=str(BASE_DIR))

if result.returncode != 0:
    print(f"[FAIL] Migration failed!")
    print(f"stderr: {result.stderr}")
    print(f"stdout: {result.stdout}")
    sys.exit(1)

print("[OK] Target database schema ready")
print()

# --- Step 2b: Flush target database ---
print("Step 2b: Flushing target database (clearing existing data)...")
flush_cmd = [python_exe, manage_py, 'flush', '--no-input']
result = subprocess.run(flush_cmd, env=target_env, capture_output=True, text=True, cwd=str(BASE_DIR))

if result.returncode != 0:
    print(f"[WARN] Flush had issues (may be OK if DB was empty):")
    print(f"stderr: {result.stderr[:500]}")
else:
    print("[OK] Target database flushed")
print()

# --- Step 3: Load data into target ---
print("Step 3: Importing data to target database...")
print()

load_cmd = [python_exe, str(BASE_DIR / "load_data_no_signals.py"), dump_file]
result = subprocess.run(load_cmd, env=target_env, capture_output=True, text=True, cwd=str(BASE_DIR))

if result.returncode != 0:
    print(f"[FAIL] Import failed!")
    print(f"stderr: {result.stderr}")
    print(f"stdout: {result.stdout}")
    sys.exit(1)

print(f"[OK] Data imported successfully")
print(f"stdout: {result.stdout}")
print()

print("=" * 60)
print("Migration Complete!")
print("=" * 60)
print()
print("Next Steps:")
print(f"1. Update your .env file with new database credentials:")
print(f"   DB_HOST={TARGET['DB_HOST']}")
print(f"   DB_PORT={TARGET['DB_PORT']}")
print(f"   DB_USER={TARGET['DB_USER']}")
print(f"   DB_PASSWORD={TARGET['DB_PASSWORD']}")
print()
print(f"Backup file: {dump_file}")
