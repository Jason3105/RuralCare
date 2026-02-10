"""
Custom template tags for media file handling
"""
from django import template
from django.conf import settings
import os

register = template.Library()


@register.filter
def local_media_url(file_field):
    """
    Returns the appropriate URL for a file field.
    - If file exists locally, returns local media URL
    - Otherwise returns the storage backend URL (e.g., Supabase)
    
    Usage: {{ record.document_file|local_media_url }}
    """
    if not file_field:
        return ''
    
    # Get the file name/path from the field
    if hasattr(file_field, 'name') and file_field.name:
        # Check if file exists locally first
        local_path = os.path.join(settings.MEDIA_ROOT, file_field.name)
        if os.path.exists(local_path):
            # Return local media URL
            return f"{settings.MEDIA_URL}{file_field.name}"
        
        # Otherwise return the storage backend URL (Supabase)
        try:
            return file_field.url
        except Exception:
            return f"{settings.MEDIA_URL}{file_field.name}"
    
    return ''


@register.simple_tag
def media_url(file_field):
    """
    Returns the appropriate media URL for a file field.
    
    Usage: {% media_url record.document_file %}
    """
    if not file_field:
        return ''
    
    if hasattr(file_field, 'name') and file_field.name:
        # Check if file exists locally first
        local_path = os.path.join(settings.MEDIA_ROOT, file_field.name)
        if os.path.exists(local_path):
            return f"{settings.MEDIA_URL}{file_field.name}"
        
        # Otherwise return the storage backend URL (Supabase)
        try:
            return file_field.url
        except Exception:
            return f"{settings.MEDIA_URL}{file_field.name}"
    
    return ''
