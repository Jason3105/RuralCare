"""
Management command to initialize Supabase storage bucket.
"""
from django.core.management.base import BaseCommand
from authentication.supabase_storage import ensure_bucket_exists


class Command(BaseCommand):
    help = 'Initialize Supabase storage bucket for file uploads'

    def handle(self, *args, **options):
        self.stdout.write('Initializing Supabase storage bucket...')
        ensure_bucket_exists()
        self.stdout.write(self.style.SUCCESS('Supabase storage bucket initialized!'))
