import os
import json
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
# from .jwt_auth import jwt_required  # Temporarily disabled

# API Gateway URL
API_GATEWAY_URL = os.environ.get('API_GATEWAY_URL', 'http://gateway:8000')

# Frontend Views
def index(request):
    return render(request, 'index.html')

@login_required
def chat(request):
    try:
        # Get sessions from API Gateway
        response = requests.get(f"{API_GATEWAY_URL}/api/sessions", params={'user_id': request.user.id})
        sessions_data = response.json() if response.status_code == 200 else {'sessions': []}
        sessions = sessions_data.get('sessions', [])
    except:
        sessions = []
    
    return render(request, 'chat.html', {'sessions': sessions})

@login_required
def documents(request):
    try:
        # Get documents from API Gateway
        response = requests.get(f"{API_GATEWAY_URL}/api/documents", params={'user_id': request.user.id})
        docs_data = response.json() if response.status_code == 200 else {'documents': []}
        documents = docs_data.get('documents', [])
    except:
        documents = []
    
    return render(request, 'documents.html', {'documents': documents})

# Authentication Views
def universal_login_page(request):
    """Display universal login page (works for both local users and LDAP)"""
    context = {
        'ldap_enabled': getattr(settings, 'LDAP_ENABLED', False),
        'jwt_enabled': getattr(settings, 'JWT_AVAILABLE', False)
    }
    return render(request, 'auth/universal_login.html', context)

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('chat')
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('index')

def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        password_confirm = request.POST['password_confirm']
        
        if password != password_confirm:
            return render(request, 'register.html', {'error': 'Passwords do not match'})
        
        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'Username already exists'})
        
        user = User.objects.create_user(username=username, email=email, password=password)
        login(request, user)
        return redirect('chat')
    
    return render(request, 'register.html')

# API Views (Proxy to API Gateway)
@login_required  # Back to Django session auth temporarily
@require_http_methods(["POST"])
def upload_document(request):
    try:
        # Back to Django session user temporarily
        user = request.user
            
        if 'file' not in request.FILES:
            return JsonResponse({'error': 'No file provided'}, status=400)
        
        file = request.FILES['file']
        
        if file.size > settings.MAX_UPLOAD_SIZE:
            return JsonResponse({'error': 'File too large'}, status=400)
        
        # Forward to API Gateway (back to original approach temporarily)
        files = {'file': (file.name, file.read(), file.content_type)}
        data = {'user_id': user.id}
        
        # Debug logging
        print(f"Upload request - User ID: {user.id}, File: {file.name}")
        
        response = requests.post(
            f"{API_GATEWAY_URL}/api/upload",
            files=files,
            data=data,
            timeout=60
        )
        
        if response.status_code == 200:
            return JsonResponse(response.json())
        else:
            return JsonResponse({'error': 'Upload failed'}, status=response.status_code)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def chat_api(request):
    try:
        data = json.loads(request.body)
        message = data.get('message')
        session_id = data.get('session_id')
        
        if not message:
            return JsonResponse({'error': 'No message provided'}, status=400)
        
        # Forward to API Gateway
        chat_data = {
            'message': message,
            'user_id': request.user.id,
            'session_id': session_id
        }
        
        response = requests.post(
            f"{API_GATEWAY_URL}/api/chat",
            json=chat_data,
            timeout=60
        )
        
        if response.status_code == 200:
            return JsonResponse(response.json())
        else:
            return JsonResponse({'error': 'Chat request failed'}, status=response.status_code)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def documents_api(request):
    try:
        response = requests.get(
            f"{API_GATEWAY_URL}/api/documents",
            params={'user_id': request.user.id}
        )
        
        if response.status_code == 200:
            return JsonResponse(response.json())
        else:
            return JsonResponse({'error': 'Failed to get documents'}, status=response.status_code)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def sessions_api(request):
    try:
        response = requests.get(
            f"{API_GATEWAY_URL}/api/sessions",
            params={'user_id': request.user.id}
        )
        
        if response.status_code == 200:
            return JsonResponse(response.json())
        else:
            return JsonResponse({'error': 'Failed to get sessions'}, status=response.status_code)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def session_detail_api(request, session_id):
    try:
        response = requests.get(
            f"{API_GATEWAY_URL}/api/sessions/{session_id}",
            params={'user_id': request.user.id}
        )
        
        if response.status_code == 200:
            return JsonResponse(response.json())
        else:
            return JsonResponse({'error': 'Failed to get session'}, status=response.status_code)
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)