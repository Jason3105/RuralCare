"""
Medicine Identifier URL Configuration
"""

from django.urls import path
from . import views

app_name = 'medicine_identifier'

urlpatterns = [
    # Main views
    path('', views.medicine_dashboard, name='dashboard'),
    path('upload/', views.upload_medicine_image, name='upload'),
    path('result/<uuid:identification_id>/', views.identification_result, name='result'),
    path('history/', views.identification_history, name='history'),
    path('delete/<uuid:identification_id>/', views.delete_identification, name='delete'),
    
    # AJAX endpoints
    path('more-info/<uuid:identification_id>/', views.get_more_info, name='more_info'),
    path('check-interaction/', views.check_interaction, name='check_interaction'),
    
    # API endpoints
    path('api/identify/', views.api_identify_medicine, name='api_identify'),
]
