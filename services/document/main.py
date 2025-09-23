from fastapi import FastAPI, HTTPException, File, UploadFile, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
import uuid
import asyncio
from typing import List
import psycopg2
from psycopg2.extras import RealDictCursor
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from embedding_service import SentenceTransformer
import PyPDF2
import docx
import magic
from io import BytesIO
from jwt_middleware import get_current_user, get_user_collection_name
from permissions import DocumentPermissions, UserRolePermissions, require_document_permission

app = FastAPI(title="Skynet RC1 Document Service", version="1.0.0")

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

# Database connection
def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)

# Document processing functions
def extract_text_from_pdf(file_data: bytes) -> str:
    """Extract text from PDF"""
    try:
        pdf_file = BytesIO(file_data)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting PDF text: {e}")
        return ""

def extract_text_from_docx(file_data: bytes) -> str:
    """Extract text from Word document"""
    try:
        doc_file = BytesIO(file_data)
        doc = docx.Document(doc_file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()
    except Exception as e:
        print(f"Error extracting DOCX text: {e}")
        return ""

def extract_text_from_file(file_data: bytes, mime_type: str) -> str:
    """Extract text based on file type"""
    if mime_type == 'application/pdf':
        return extract_text_from_pdf(file_data)
    elif mime_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document']:
        return extract_text_from_docx(file_data)
    elif mime_type.startswith('text/'):
        try:
            return file_data.decode('utf-8')
        except:
            return file_data.decode('utf-8', errors='ignore')
    else:
        # Try to decode as text anyway
        try:
            return file_data.decode('utf-8', errors='ignore')
        except:
            return ""

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks"""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence or word boundaries
        if end < len(text):
            last_period = chunk.rfind('.')
            last_space = chunk.rfind(' ')
            
            if last_period > start + chunk_size // 2:
                end = start + last_period + 1
            elif last_space > start + chunk_size // 2:
                end = start + last_space
        
        chunks.append(text[start:end].strip())
        start = end - overlap
    
    return [chunk for chunk in chunks if chunk.strip()]

async def process_document_async(document_id: int, file_data: bytes, mime_type: str, user_id: int, username: str = None):
    """Process document in background"""
    try:
        # Extract text
        text = extract_text_from_file(file_data, mime_type)
        if not text or text.strip() == "":
            # Mark as processed even if no text found
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE documents SET processed = true, processed_at = NOW() WHERE id = %s",
                        (document_id,)
                    )
                    conn.commit()
            print(f"Document {document_id} processed but no text could be extracted")
            return
        
        # Chunk text
        chunks = chunk_text(text)
        
        # Create user-specific Qdrant collection
        collection_name = get_user_collection_name(user_id, username)
        
        # Get embedding dimension from our service
        embedding_dim = embedding_model.embedding_service.get_embedding_dimension()
        
        try:
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=embedding_dim, distance=Distance.COSINE)
            )
        except:
            pass  # Collection might already exist
        
        # Generate embeddings and store in Qdrant
        points = []
        for i, chunk in enumerate(chunks):
            embedding = embedding_model.encode(chunk).tolist()
            point_id = str(uuid.uuid4())
            
            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload={
                    "document_id": document_id,
                    "chunk_index": i,
                    "content": chunk,
                    "user_id": user_id
                }
            )
            points.append(point)
        
        # Upload points to Qdrant
        qdrant_client.upsert(
            collection_name=collection_name,
            points=points
        )
        
        # Update document as processed
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE documents SET processed = true, processed_at = NOW() WHERE id = %s",
                    (document_id,)
                )
                conn.commit()
        
        print(f"Document {document_id} processed successfully with {len(chunks)} chunks")
        
    except Exception as e:
        print(f"Error processing document {document_id}: {e}")
        # Mark document as processed even if failed to avoid infinite stuck state
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE documents SET processed = true, processed_at = NOW() WHERE id = %s",
                    (document_id,)
                )
                conn.commit()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "document-service"}

@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload and process document"""
    try:
        # Read file data
        file_data = await file.read()
        
        # Detect file type
        mime_type = magic.from_buffer(file_data, mime=True)
        
        # Extract user info from JWT token
        user_id = current_user['user_id']
        username = current_user.get('username')
        user_groups = current_user.get('groups', [])
        
        # Check upload permissions for readonly users
        if not UserRolePermissions.check_permission(user_groups, 'can_upload_documents'):
            if UserRolePermissions.get_user_role(user_groups) == 'readonly':
                raise HTTPException(status_code=403, detail="Upload not permitted for readonly users")
        
        # Save document metadata to database
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO documents (user_id, filename, file_path, mime_type, size_bytes)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (user_id, file.filename, f"/data/{file.filename}", mime_type, len(file_data)))
                
                document_id = cur.fetchone()['id']
                conn.commit()
        
        # Save file to disk
        file_path = f"/app/data/{document_id}_{file.filename}"
        with open(file_path, "wb") as f:
            f.write(file_data)
        
        # Update file path in database
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE documents SET file_path = %s WHERE id = %s",
                    (file_path, document_id)
                )
                conn.commit()
        
        # Create audit log for document upload
        DocumentPermissions.create_document_audit_log(
            user_id, document_id, "upload", f"File: {file.filename}, Size: {len(file_data)} bytes"
        )
        
        # Process document asynchronously
        asyncio.create_task(process_document_async(document_id, file_data, mime_type, user_id, username))
        
        return {
            "id": document_id,
            "title": file.filename,
            "status": "processing"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/documents")
async def get_user_documents(current_user: dict = Depends(get_current_user)):
    """Get all documents for a user"""
    try:
        user_id = current_user['user_id']
        user_groups = current_user.get('groups', [])
        
        # Admin users can see all documents
        if UserRolePermissions.check_permission(user_groups, 'can_access_all_documents'):
            documents = DocumentPermissions.get_user_documents(None, include_shared=True)
        else:
            documents = DocumentPermissions.get_user_documents(user_id, include_shared=True)
        
        # Create audit log for document listing
        DocumentPermissions.create_document_audit_log(
            user_id, None, "list_documents", f"Retrieved {len(documents)} documents"
        )
        
        return {"documents": documents}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process/{document_id}")
async def reprocess_document(document_id: int):
    """Reprocess a document"""
    try:
        # Get document info
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT user_id, file_path, mime_type as file_type FROM documents WHERE id = %s",
                    (document_id,)
                )
                doc = cur.fetchone()
                
                if not doc:
                    raise HTTPException(status_code=404, detail="Document not found")
        
        # Read file data
        with open(doc['file_path'], 'rb') as f:
            file_data = f.read()
        
        # Process document
        asyncio.create_task(process_document_async(document_id, file_data, doc['file_type'], doc['user_id']))
        
        return {"status": "reprocessing", "document_id": document_id}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents/{document_id}")
async def delete_document(document_id: int, current_user: dict = Depends(get_current_user)):
    """Delete a document with proper permissions"""
    try:
        user_id = current_user['user_id']
        user_groups = current_user.get('groups', [])
        
        # Check if user can delete this document
        can_delete = (
            DocumentPermissions.check_document_access(user_id, document_id, "delete") or
            UserRolePermissions.check_permission(user_groups, 'can_delete_any_document')
        )
        
        if not can_delete:
            raise HTTPException(
                status_code=403, 
                detail="Insufficient permissions to delete this document"
            )
        
        # Get document info for audit log
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT filename, user_id FROM documents WHERE id = %s",
                    (document_id,)
                )
                doc_info = cur.fetchone()
                
                if not doc_info:
                    raise HTTPException(status_code=404, detail="Document not found")
                
                # Delete document record
                cur.execute("DELETE FROM documents WHERE id = %s", (document_id,))
                conn.commit()
        
        # Create audit log
        DocumentPermissions.create_document_audit_log(
            user_id, document_id, "delete", 
            f"Deleted document: {doc_info['filename']}, Owner: {doc_info['user_id']}"
        )
        
        # TODO: Also delete from Qdrant and file system
        
        return {"message": "Document deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)