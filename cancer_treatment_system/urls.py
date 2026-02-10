"""
URL configuration for cancer_treatment_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse, Http404
from django.views.static import serve
import os
from cancer_detection import evidence_web_views


def serve_media(request, path):
    """
    Custom media file server that serves files from local storage.
    This handles the case where Supabase storage is configured but files
    exist locally (before migration to Supabase).
    """
    file_path = os.path.join(settings.MEDIA_ROOT, path)
    
    if os.path.exists(file_path) and os.path.isfile(file_path):
        # Serve the file from local storage
        return serve(request, path, document_root=settings.MEDIA_ROOT)
    
    raise Http404("Media file not found")


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('authentication.urls')),
    path('cancer-detection/', include('cancer_detection.urls')),
    path('clinical/', include('clinical_decision_support.urls')),
    path('portal/', include('patient_portal.urls')),
    path('insurance/', include('Insurance_SIP.Insurance_SIP.urls')),
    path('medicine/', include('medicine_identifier.urls')),
    path('chatbot/', include('medical_chatbot.urls')),
    
    # Evidence Traceability Engine - Root level HTML views
    path('evidence/search/', evidence_web_views.evidence_search, name='evidence_search'),
    path('evidence/source/<uuid:source_id>/', evidence_web_views.evidence_source_detail, name='evidence_source_detail'),
    path('evidence/rules/', evidence_web_views.rule_based_references_view, name='rule_based_references_view'),
]

# Serve media files
# In production on Render, media comes from Supabase; this serves any local files
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve_media, name='serve_media'),
]
