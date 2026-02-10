from django.db import models
from django.contrib.auth import get_user_model
import uuid
from django.utils import timezone

User = get_user_model()


class ChatSession(models.Model):
    """Model to store chat sessions for each patient"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=200, default="New Conversation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'chat_sessions'
        ordering = ['-updated_at']
        
    def __str__(self):
        return f"{self.patient.username} - {self.title}"


class ChatMessage(models.Model):
    """Model to store individual chat messages"""
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    context_used = models.JSONField(default=dict, blank=True, help_text="Medical context used for this response")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']
        
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."


class UserMedicalContext(models.Model):
    """Cache of user's medical context for faster retrieval"""
    patient = models.OneToOneField(User, on_delete=models.CASCADE, related_name='medical_context_cache')
    context_data = models.JSONField(default=dict, help_text="Cached medical context")
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'user_medical_contexts'
        
    def __str__(self):
        return f"Medical Context for {self.patient.username}"
