from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form, Header
from fastapi.middleware.cors import CORSMiddleware
import os
import requests
from typing import Optional, List, Dict, Any
from auth import get_current_user, get_optional_user, require_staff, require_superuser

app = FastAPI(title="Skynet RC1 API Gateway", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
document_service_url = os.environ.get('DOCUMENT_SERVICE_URL', 'http://document:8000')
ai_chat_service_url = os.environ.get('AI_CHAT_SERVICE_URL', 'http://ai-chat:8000')
frontend_service_url = os.environ.get('FRONTEND_SERVICE_URL', 'http://frontend:8000')

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "api-gateway"}

@app.post("/api/upload")
async def upload_document(
    file: UploadFile = File(...),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Upload document to document service - requires authentication"""
    try:
        files = {'file': (file.filename, await file.read(), file.content_type)}
        data = {'user_id': user['user_id']}
        
        response = requests.post(f"{document_service_url}/upload", files=files, data=data, timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents")
async def get_documents(user: Dict[str, Any] = Depends(get_current_user)):
    """Get user's documents - requires authentication"""
    try:
        response = requests.get(f"{document_service_url}/documents", params={'user_id': user['user_id']})
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat(
    request: dict,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Chat with AI - requires authentication"""
    try:
        message = request.get('message')
        session_id = request.get('session_id')
        
        if not message:
            raise HTTPException(status_code=400, detail="Message is required")
        
        # Add authenticated user ID to request
        chat_request = {
            **request,
            'user_id': user['user_id']
        }
        
        response = requests.post(f"{ai_chat_service_url}/chat", json=chat_request, timeout=120)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search")
async def search_documents(
    request: dict,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Search documents - requires authentication"""
    try:
        query = request.get('query')
        limit = request.get('limit', 5)
        
        if not query:
            raise HTTPException(status_code=400, detail="Query is required")
        
        # Add authenticated user ID to request
        search_request = {
            **request,
            'user_id': user['user_id']
        }
        
        response = requests.post(f"{ai_chat_service_url}/search", json=search_request, timeout=60)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions")
async def get_chat_sessions(user: Dict[str, Any] = Depends(get_current_user)):
    """Get user's chat sessions - requires authentication"""
    try:
        response = requests.get(f"{ai_chat_service_url}/sessions", params={'user_id': user['user_id']})
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}")
async def get_session_messages(
    session_id: int,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get messages for a specific session - requires authentication"""
    try:
        response = requests.get(
            f"{ai_chat_service_url}/sessions/{session_id}", 
            params={'user_id': user['user_id']}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Authentication endpoints - proxy to frontend service
@app.post("/api/auth/login")
async def login(request: dict):
    """Authenticate user - proxy to frontend service"""
    try:
        response = requests.post(f"{frontend_service_url}/api/auth/login/", json=request, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            # Return the error response from frontend
            raise HTTPException(status_code=response.status_code, detail=response.json())
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Authentication service error: {str(e)}")

@app.post("/api/auth/logout")
async def logout(request: dict):
    """Logout user - proxy to frontend service"""
    try:
        response = requests.post(f"{frontend_service_url}/api/auth/logout/", json=request, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.json())
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Authentication service error: {str(e)}")

@app.get("/api/auth/profile")
async def get_profile(authorization: Optional[str] = Header(None)):
    """Get user profile - proxy to frontend service"""
    try:
        headers = {}
        if authorization:
            headers['Authorization'] = authorization
        
        response = requests.get(f"{frontend_service_url}/api/auth/profile/", headers=headers, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.json())
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Authentication service error: {str(e)}")

@app.post("/api/auth/refresh")
async def refresh_token(request: dict):
    """Refresh JWT token - proxy to frontend service"""
    try:
        response = requests.post(f"{frontend_service_url}/api/auth/refresh/", json=request, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.json())
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Authentication service error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)