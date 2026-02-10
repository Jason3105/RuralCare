#!/usr/bin/env bash
# exit on error
set -o errexit

# Install Python dependencies
pip install --upgrade pip

# Install CPU-only PyTorch first (saves ~1.5GB vs full CUDA version)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run database migrations
python manage.py migrate

# Ensure Supabase storage bucket exists
python -c "import django; import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cancer_treatment_system.settings'); django.setup(); from authentication.supabase_storage import ensure_bucket_exists; ensure_bucket_exists()"
