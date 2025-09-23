from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
import requests
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from qdrant_client import QdrantClient
from embedding_service import SentenceTransformer

app = FastAPI(title="Skynet RC1 AI Chat Service", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize clients
qdrant_client = QdrantClient(url=os.environ.get('QDRANT_URL', 'http://qdrant:6333'))
embedding_model = SentenceTransformer('lightweight-tfidf')  # Using our lightweight implementation
ollama_url = os.environ.get('OLLAMA_URL', 'http://ollama:11434')
ollama_model = os.environ.get('OLLAMA_MODEL', 'llama3.1:8b')

# Database connection
def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)

def search_documents(query: str, user_id: int, limit: int = 5) -> List[dict]:
    """Search user's documents using vector similarity"""
    try:
        # Generate query embedding
        query_embedding = embedding_model.encode(query).tolist()
        
        # Search in user's collection
        collection_name = f"user_{user_id}_documents"
        
        try:
            search_results = qdrant_client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=limit,
                with_payload=True
            )
        except Exception as e:
            print(f"Qdrant search error: {e}")
            return []
        
        # Format results
        results = []
        for result in search_results:
            payload = result.payload
            results.append({
                "document_id": payload.get("document_id"),
                "chunk_content": payload.get("content"),
                "score": result.score,
                "chunk_index": payload.get("chunk_index")
            })
        
        return results
    
    except Exception as e:
        print(f"Error searching documents: {e}")
        return []

def generate_ollama_response(prompt: str, context: str = "") -> str:
    """Generate response using Ollama"""
    full_prompt = f"""Context: {context}

Question: {prompt}

Please provide a helpful response based on the context provided. If the context doesn't contain relevant information, please say so and provide a general response."""

    try:
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": ollama_model,
                "prompt": full_prompt,
                "stream": False
            },
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json().get('response', 'No response generated')
        else:
            return f"Error: Ollama service returned status {response.status_code}"
    
    except requests.exceptions.RequestException as e:
        return f"Error connecting to Ollama: {str(e)}"

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ai-chat-service"}

@app.post("/search")
async def search_user_documents(request: dict):
    """Search user's documents"""
    try:
        query = request.get('query')
        user_id = request.get('user_id')
        limit = request.get('limit', 5)
        
        if not query or not user_id:
            raise HTTPException(status_code=400, detail="Query and user_id are required")
        
        results = search_documents(query, user_id, limit)
        return {"results": results}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
async def chat_with_ai(request: dict):
    """Generate AI response with RAG"""
    try:
        message = request.get('message')
        user_id = request.get('user_id')
        session_id = request.get('session_id')
        
        if not message or not user_id:
            raise HTTPException(status_code=400, detail="Message and user_id are required")
        
        # Search for relevant documents
        relevant_docs = search_documents(message, user_id, 5)
        
        # Get or create chat session
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                if session_id:
                    cur.execute(
                        "SELECT id, title FROM chat_sessions WHERE id = %s AND user_id = %s",
                        (session_id, user_id)
                    )
                    session = cur.fetchone()
                    if not session:
                        raise HTTPException(status_code=404, detail="Session not found")
                else:
                    # Create new session
                    title = message[:50] + "..." if len(message) > 50 else message
                    cur.execute("""
                        INSERT INTO chat_sessions (user_id, title, created_at, updated_at)
                        VALUES (%s, %s, NOW(), NOW())
                        RETURNING id, title
                    """, (user_id, title))
                    session = cur.fetchone()
                    session_id = session['id']
                
                conn.commit()
        
        # Save user message
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO chat_messages (session_id, role, content, timestamp)
                    VALUES (%s, %s, %s, NOW())
                """, (session_id, 'user', message))
                conn.commit()
        
        # Build context from relevant documents
        if relevant_docs:
            # Get document titles
            doc_ids = [doc['document_id'] for doc in relevant_docs]
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    placeholders = ','.join(['%s'] * len(doc_ids))
                    cur.execute(f"SELECT id, title FROM documents WHERE id IN ({placeholders})", doc_ids)
                    doc_titles = {row['id']: row['title'] for row in cur.fetchall()}
            
            context = "\n\n".join([
                f"From '{doc_titles.get(doc['document_id'], 'Unknown')}': {doc['chunk_content']}"
                for doc in relevant_docs
            ])
        else:
            context = "No relevant documents found."
        
        # Generate AI response
        ai_response = generate_ollama_response(message, context)
        
        # Save assistant message
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO chat_messages (session_id, role, content, timestamp)
                    VALUES (%s, %s, %s, NOW())
                    RETURNING id
                """, (session_id, 'assistant', ai_response))
                
                message_id = cur.fetchone()['id']
                
                # Link used documents
                if relevant_docs:
                    for doc in relevant_docs:
                        cur.execute("""
                            INSERT INTO message_documents (message_id, document_id)
                            VALUES (%s, %s)
                        """, (message_id, doc['document_id']))
                
                conn.commit()
        
        # Update session timestamp
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE chat_sessions SET updated_at = NOW() WHERE id = %s",
                    (session_id,)
                )
                conn.commit()
        
        # Format used documents for response
        used_docs = []
        if relevant_docs:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    doc_ids = list(set([doc['document_id'] for doc in relevant_docs]))
                    placeholders = ','.join(['%s'] * len(doc_ids))
                    cur.execute(f"SELECT id, title FROM documents WHERE id IN ({placeholders})", doc_ids)
                    used_docs = [row['title'] for row in cur.fetchall()]
        
        return {
            "session_id": session_id,
            "response": ai_response,
            "used_documents": used_docs
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions")
async def get_chat_sessions(user_id: int):
    """Get user's chat sessions"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT cs.id, cs.title, cs.created_at, cs.updated_at,
                           COUNT(cm.id) as message_count
                    FROM chat_sessions cs
                    LEFT JOIN chat_messages cm ON cs.id = cm.session_id
                    WHERE cs.user_id = %s
                    GROUP BY cs.id, cs.title, cs.created_at, cs.updated_at
                    ORDER BY cs.updated_at DESC
                """, (user_id,))
                
                sessions = cur.fetchall()
        
        return {"sessions": [dict(session) for session in sessions]}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions/{session_id}")
async def get_session_messages(session_id: int, user_id: int):
    """Get messages for a specific session"""
    try:
        # Verify session belongs to user
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, title FROM chat_sessions WHERE id = %s AND user_id = %s",
                    (session_id, user_id)
                )
                session = cur.fetchone()
                
                if not session:
                    raise HTTPException(status_code=404, detail="Session not found")
                
                # Get messages with used documents
                cur.execute("""
                    SELECT cm.id, cm.role, cm.content, cm.timestamp,
                           ARRAY_AGG(DISTINCT d.title) FILTER (WHERE d.title IS NOT NULL) as used_documents
                    FROM chat_messages cm
                    LEFT JOIN message_documents md ON cm.id = md.message_id
                    LEFT JOIN documents d ON md.document_id = d.id
                    WHERE cm.session_id = %s
                    GROUP BY cm.id, cm.role, cm.content, cm.timestamp
                    ORDER BY cm.timestamp
                """, (session_id,))
                
                messages = cur.fetchall()
        
        return {
            "session": dict(session),
            "messages": [dict(msg) for msg in messages]
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)