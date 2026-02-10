from django.contrib import admin
from .models import ChatSession, ChatMessage, UserMedicalContext


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['title', 'patient', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'patient__username', 'patient__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['-updated_at']


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'role', 'content_preview', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['content', 'session__title']
    readonly_fields = ['id', 'created_at']
    ordering = ['-created_at']
    
    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content'


@admin.register(UserMedicalContext)
class UserMedicalContextAdmin(admin.ModelAdmin):
    list_display = ['patient', 'last_updated']
    search_fields = ['patient__username', 'patient__email']
    readonly_fields = ['last_updated']
