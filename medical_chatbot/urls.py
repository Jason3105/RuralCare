from django.urls import path
from . import views

app_name = 'medical_chatbot'

urlpatterns = [
    path('', views.chatbot_interface, name='chat_interface'),
    path('send/', views.send_message, name='send_message'),
    path('new-session/', views.new_session, name='new_session'),
    path('switch-session/<uuid:session_id>/', views.switch_session, name='switch_session'),
    path('delete-session/<uuid:session_id>/', views.delete_session, name='delete_session'),
]
