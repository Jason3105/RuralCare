from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
from .models import ChatSession, ChatMessage
from .chatbot_service import MedicalChatbot


@login_required
def chatbot_interface(request):
    """Main chatbot interface"""
    # Get or create active session
    active_session = ChatSession.objects.filter(
        patient=request.user,
        is_active=True
    ).first()
    
    if not active_session:
        active_session = ChatSession.objects.create(
            patient=request.user,
            title="New Conversation"
        )
    
    # Get all sessions for sidebar
    all_sessions = ChatSession.objects.filter(
        patient=request.user
    ).order_by('-updated_at')[:20]
    
    # Get messages for active session
    messages = ChatMessage.objects.filter(
        session=active_session
    ).order_by('created_at')
    
    context = {
        'active_session': active_session,
        'all_sessions': all_sessions,
        'messages': messages,
    }
    
    return render(request, 'medical_chatbot/chat_interface.html', context)


@login_required
@require_http_methods(["POST"])
def send_message(request):
    """Handle sending a message and getting AI response"""
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        session_id = data.get('session_id')
        
        if not user_message:
            return JsonResponse({'error': 'Message cannot be empty'}, status=400)
        
        # Get or create session
        if session_id:
            session = get_object_or_404(ChatSession, id=session_id, patient=request.user)
        else:
            session = ChatSession.objects.create(
                patient=request.user,
                title="New Conversation"
            )
        
        # Save user message
        user_msg = ChatMessage.objects.create(
            session=session,
            role='user',
            content=user_message
        )
        
        # Get conversation history
        history = ChatMessage.objects.filter(
            session=session
        ).order_by('created_at')
        
        conversation_history = [
            {'role': msg.role, 'content': msg.content}
            for msg in history
        ]
        
        # Get AI response (singleton - reuses Groq HTTP client)
        chatbot = MedicalChatbot.get_instance()
        ai_response = chatbot.get_response(
            patient=request.user,
            user_message=user_message,
            conversation_history=conversation_history[:-1]  # Exclude the message we just added
        )
        
        if ai_response['success']:
            # Save assistant message
            assistant_msg = ChatMessage.objects.create(
                session=session,
                role='assistant',
                content=ai_response['response'],
                context_used=ai_response.get('context_used', {})
            )
            
            # Update session title if this is the first message
            if history.count() == 1:  # Only user message exists
                title = chatbot.generate_conversation_title(user_message)
                session.title = title
                session.save()
            
            return JsonResponse({
                'success': True,
                'user_message': {
                    'id': str(user_msg.id),
                    'content': user_msg.content,
                    'created_at': user_msg.created_at.isoformat(),
                },
                'assistant_message': {
                    'id': str(assistant_msg.id),
                    'content': assistant_msg.content,
                    'created_at': assistant_msg.created_at.isoformat(),
                },
                'session_id': str(session.id),
                'session_title': session.title,
            })
        else:
            return JsonResponse({
                'success': False,
                'error': ai_response.get('error', 'Unknown error')
            }, status=500)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def new_session(request):
    """Create a new chat session"""
    try:
        # Set current active session to inactive
        ChatSession.objects.filter(
            patient=request.user,
            is_active=True
        ).update(is_active=False)
        
        # Create new session
        session = ChatSession.objects.create(
            patient=request.user,
            title="New Conversation",
            is_active=True
        )
        
        return JsonResponse({
            'success': True,
            'session_id': str(session.id),
            'session_title': session.title,
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["POST"])
def switch_session(request, session_id):
    """Switch to a different chat session"""
    try:
        # Set all sessions to inactive
        ChatSession.objects.filter(
            patient=request.user
        ).update(is_active=False)
        
        # Set selected session to active
        session = get_object_or_404(ChatSession, id=session_id, patient=request.user)
        session.is_active = True
        session.save()
        
        # Get messages for this session
        messages = ChatMessage.objects.filter(
            session=session
        ).order_by('created_at')
        
        messages_data = [
            {
                'id': str(msg.id),
                'role': msg.role,
                'content': msg.content,
                'created_at': msg.created_at.isoformat(),
            }
            for msg in messages
        ]
        
        return JsonResponse({
            'success': True,
            'session_id': str(session.id),
            'session_title': session.title,
            'messages': messages_data,
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
@require_http_methods(["DELETE"])
def delete_session(request, session_id):
    """Delete a chat session"""
    try:
        session = get_object_or_404(ChatSession, id=session_id, patient=request.user)
        session.delete()
        
        return JsonResponse({'success': True})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
