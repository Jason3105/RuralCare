from django.urls import path
from . import views

app_name = 'insurance'

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('schemes/', views.government_schemes, name='government_schemes'),
    path('schemes/<uuid:scheme_id>/', views.scheme_detail, name='scheme_detail'),
    path('schemes/<uuid:scheme_id>/apply/', views.apply_scheme, name='apply_scheme'),
    path('policies/', views.insurance_policies, name='insurance_policies'),
    path('policies/<uuid:policy_id>/', views.policy_detail, name='policy_detail'),
    path('policies/<uuid:policy_id>/apply/', views.apply_policy, name='apply_policy'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('payment/<str:application_id>/', views.payment, name='payment'),
    path('check-eligibility/', views.check_eligibility, name='check_eligibility'),
    path('track/', views.track_application, name='track_applications'),
    path('track/<str:application_id>/', views.track_application, name='track_application'),
]
