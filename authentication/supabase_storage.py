"""
Custom Django Storage Backend for Supabase Storage
"""
import os
import uuid
import mimetypes
from datetime import datetime
from urllib.parse import urljoin

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class SupabaseStorage(Storage):
    """
    Custom storage backend for Supabase Storage.
    Uploads files to Supabase Storage bucket.
    """
    
    def __init__(self, bucket_name=None):
        self.bucket_name = bucket_name or getattr(settings, 'SUPABASE_STORAGE_BUCKET', 'media')
        self.supabase_url = settings.SUPABASE_URL
        self.service_key = settings.SUPABASE_SERVICE_KEY
        
        if not self.supabase_url or not self.service_key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in settings")
        
        # Storage API endpoint
        self.storage_url = f"{self.supabase_url}/storage/v1"
        
        # Headers for API requests
        self.headers = {
            "Authorization": f"Bearer {self.service_key}",
            "apikey": self.service_key,
        }
    
    def _get_file_path(self, name):
        """Generate a unique file path to avoid collisions."""
        # Keep the original structure but add timestamp prefix for uniqueness
        ext = os.path.splitext(name)[1]
        directory = os.path.dirname(name)
        filename = os.path.basename(name)
        
        # Create unique filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = uuid.uuid4().hex[:8]
        new_filename = f"{timestamp}_{unique_id}_{filename}"
        
        if directory:
            return f"{directory}/{new_filename}"
        return new_filename
    
    def _save(self, name, content):
        """
        Save the file to Supabase Storage.
        """
        # Generate unique path
        file_path = self._get_file_path(name)
        
        # Read file content
        if hasattr(content, 'read'):
            file_content = content.read()
            content.seek(0)  # Reset file pointer
        else:
            file_content = content
        
        # Determine content type
        content_type, _ = mimetypes.guess_type(name)
        if not content_type:
            content_type = 'application/octet-stream'
        
        # Upload to Supabase Storage
        upload_url = f"{self.storage_url}/object/{self.bucket_name}/{file_path}"
        
        headers = {
            **self.headers,
            "Content-Type": content_type,
        }
        
        response = requests.post(
            upload_url,
            headers=headers,
            data=file_content,
        )
        
        if response.status_code not in [200, 201]:
            # If bucket not found, create it and retry
            if 'Bucket not found' in response.text or response.status_code == 404:
                self._ensure_bucket_exists()
                # Reset file pointer if needed
                if hasattr(content, 'seek'):
                    content.seek(0)
                    file_content = content.read()
                response = requests.post(
                    upload_url,
                    headers=headers,
                    data=file_content,
                )
            
            if response.status_code not in [200, 201]:
                # Try upsert if file might exist
                response = requests.put(
                    upload_url,
                    headers=headers,
                    data=file_content,
                )
            
                if response.status_code not in [200, 201]:
                    raise Exception(f"Failed to upload file to Supabase: {response.status_code} - {response.text}")
        
        return file_path
    
    def _ensure_bucket_exists(self):
        """Create the storage bucket if it doesn't exist."""
        headers = {
            **self.headers,
            "Content-Type": "application/json",
        }
        # Check if bucket exists
        response = requests.get(f"{self.storage_url}/bucket/{self.bucket_name}", headers=headers)
        if response.status_code == 404:
            payload = {
                "id": self.bucket_name,
                "name": self.bucket_name,
                "public": True,
                "file_size_limit": 52428800,
                "allowed_mime_types": [
                    "image/jpeg", "image/png", "image/gif", "image/webp",
                    "image/bmp", "image/tiff",
                    "application/pdf", "application/octet-stream",
                ]
            }
            requests.post(f"{self.storage_url}/bucket", headers=headers, json=payload)
    
    def _open(self, name, mode='rb'):
        """
        Open a file from Supabase Storage.
        """
        download_url = f"{self.storage_url}/object/{self.bucket_name}/{name}"
        
        response = requests.get(download_url, headers=self.headers)
        
        if response.status_code != 200:
            raise FileNotFoundError(f"File not found in Supabase: {name}")
        
        return ContentFile(response.content, name=name)
    
    def delete(self, name):
        """
        Delete a file from Supabase Storage.
        """
        delete_url = f"{self.storage_url}/object/{self.bucket_name}/{name}"
        
        response = requests.delete(delete_url, headers=self.headers)
        
        # 200 or 404 are both acceptable (file deleted or didn't exist)
        if response.status_code not in [200, 204, 404]:
            raise Exception(f"Failed to delete file from Supabase: {response.status_code} - {response.text}")
    
    def exists(self, name):
        """
        Check if a file exists in Supabase Storage.
        """
        # Try to get file info
        url = f"{self.storage_url}/object/info/{self.bucket_name}/{name}"
        response = requests.get(url, headers=self.headers)
        return response.status_code == 200
    
    def url(self, name):
        """
        Return the public URL for the file.
        """
        # Return public URL (bucket must be set to public in Supabase)
        return f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{name}"
    
    def size(self, name):
        """
        Return the size of the file.
        """
        url = f"{self.storage_url}/object/info/{self.bucket_name}/{name}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            data = response.json()
            return data.get('size', 0)
        return 0
    
    def get_accessed_time(self, name):
        """Not supported by Supabase."""
        raise NotImplementedError("Supabase Storage does not support accessed time")
    
    def get_created_time(self, name):
        """Get the creation time of the file."""
        url = f"{self.storage_url}/object/info/{self.bucket_name}/{name}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            data = response.json()
            created_at = data.get('created_at')
            if created_at:
                return datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        raise NotImplementedError("Could not get created time")
    
    def get_modified_time(self, name):
        """Get the modification time of the file."""
        url = f"{self.storage_url}/object/info/{self.bucket_name}/{name}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 200:
            data = response.json()
            updated_at = data.get('updated_at')
            if updated_at:
                return datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
        raise NotImplementedError("Could not get modified time")
    
    def listdir(self, path):
        """
        List contents of a directory in Supabase Storage.
        """
        list_url = f"{self.storage_url}/object/list/{self.bucket_name}"
        
        payload = {
            "prefix": path if path else "",
            "limit": 1000,
        }
        
        response = requests.post(list_url, headers=self.headers, json=payload)
        
        if response.status_code != 200:
            return [], []
        
        items = response.json()
        dirs = []
        files = []
        
        for item in items:
            name = item.get('name', '')
            if item.get('id') is None:  # It's a folder
                dirs.append(name)
            else:
                files.append(name)
        
        return dirs, files


def ensure_bucket_exists():
    """
    Ensure the media bucket exists in Supabase Storage.
    Call this during app initialization.
    """
    supabase_url = settings.SUPABASE_URL
    service_key = settings.SUPABASE_SERVICE_KEY
    bucket_name = getattr(settings, 'SUPABASE_STORAGE_BUCKET', 'media')
    
    if not supabase_url or not service_key:
        print("Warning: Supabase credentials not set, skipping bucket check")
        return
    
    storage_url = f"{supabase_url}/storage/v1"
    headers = {
        "Authorization": f"Bearer {service_key}",
        "apikey": service_key,
        "Content-Type": "application/json",
    }
    
    # Check if bucket exists
    response = requests.get(f"{storage_url}/bucket/{bucket_name}", headers=headers)
    
    if response.status_code == 404:
        # Create bucket
        payload = {
            "id": bucket_name,
            "name": bucket_name,
            "public": True,  # Make bucket public for serving files
            "file_size_limit": 52428800,  # 50MB limit
            "allowed_mime_types": [
                "image/jpeg",
                "image/png",
                "image/gif",
                "image/webp",
                "application/pdf",
                "application/msword",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ]
        }
        
        create_response = requests.post(
            f"{storage_url}/bucket",
            headers=headers,
            json=payload
        )
        
        if create_response.status_code in [200, 201]:
            print(f"Created Supabase storage bucket: {bucket_name}")
        else:
            print(f"Warning: Could not create bucket: {create_response.status_code} - {create_response.text}")
    elif response.status_code == 200:
        print(f"Supabase storage bucket '{bucket_name}' already exists")
    else:
        print(f"Warning: Could not check bucket: {response.status_code} - {response.text}")
