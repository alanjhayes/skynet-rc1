import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import HTTPException, status
import os
from typing import Dict, List, Optional

def get_db_connection():
    """Get database connection"""
    db_url = os.environ.get('DATABASE_URL')
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)

class DocumentPermissions:
    """Handle document-level permissions and access control"""
    
    @staticmethod
    def check_document_access(user_id: int, document_id: int, permission: str = "read") -> bool:
        """
        Check if user has permission to access a specific document
        
        Args:
            user_id: User ID from JWT token
            document_id: Document ID to check
            permission: Type of permission (read, write, delete)
            
        Returns:
            bool: True if user has permission, False otherwise
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Check if user owns the document
                    cur.execute(
                        "SELECT user_id FROM documents WHERE id = %s",
                        (document_id,)
                    )
                    result = cur.fetchone()
                    
                    if not result:
                        return False
                    
                    # Owner has all permissions
                    if result['user_id'] == user_id:
                        return True
                    
                    # Check shared permissions (if implemented)
                    # This could be extended to support document sharing
                    return False
                    
        except Exception:
            return False
    
    @staticmethod
    def get_user_documents(user_id: int, include_shared: bool = False) -> List[Dict]:
        """
        Get all documents accessible to a user
        
        Args:
            user_id: User ID from JWT token
            include_shared: Whether to include documents shared with the user
            
        Returns:
            List of document dictionaries
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    if include_shared:
                        # Extended query to include shared documents
                        # This would require a document_shares table
                        query = """
                            SELECT DISTINCT d.id, d.filename as title, d.mime_type as file_type, 
                                   d.size_bytes as file_size, d.created_at as uploaded_at, 
                                   d.processed, d.user_id,
                                   CASE WHEN d.user_id = %s THEN 'owner' ELSE 'shared' END as access_type
                            FROM documents d
                            WHERE d.user_id = %s
                            ORDER BY d.created_at DESC
                        """
                        cur.execute(query, (user_id, user_id))
                    else:
                        # Only user's own documents
                        cur.execute("""
                            SELECT id, filename as title, mime_type as file_type, 
                                   size_bytes as file_size, created_at as uploaded_at, 
                                   processed, user_id
                            FROM documents 
                            WHERE user_id = %s 
                            ORDER BY created_at DESC
                        """, (user_id,))
                    
                    return [dict(doc) for doc in cur.fetchall()]
                    
        except Exception:
            return []
    
    @staticmethod
    def create_document_audit_log(user_id: int, document_id: int, action: str, details: str = None):
        """
        Create audit log entry for document access
        
        Args:
            user_id: User performing the action
            document_id: Document being accessed
            action: Action performed (upload, download, delete, share, etc.)
            details: Additional details about the action
        """
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO document_audit_log (user_id, document_id, action, details, timestamp)
                        VALUES (%s, %s, %s, %s, NOW())
                        ON CONFLICT DO NOTHING
                    """, (user_id, document_id, action, details))
                    conn.commit()
        except Exception as e:
            # Log error but don't fail the main operation
            print(f"Failed to create audit log: {e}")

class UserRolePermissions:
    """Handle user role-based permissions"""
    
    ROLES = {
        'admin': {
            'can_access_all_documents': True,
            'can_delete_any_document': True,
            'can_manage_users': True,
            'can_view_audit_logs': True
        },
        'user': {
            'can_access_all_documents': False,
            'can_delete_any_document': False,
            'can_manage_users': False,
            'can_view_audit_logs': False
        },
        'readonly': {
            'can_access_all_documents': False,
            'can_delete_any_document': False,
            'can_manage_users': False,
            'can_view_audit_logs': False,
            'can_upload_documents': False
        }
    }
    
    @staticmethod
    def get_user_role(user_groups: List[str]) -> str:
        """
        Determine user role based on AD groups
        
        Args:
            user_groups: List of AD group names from JWT token
            
        Returns:
            str: User role (admin, user, readonly)
        """
        # Define group mappings
        admin_groups = ['skynet-admin', 'domain-admins']
        readonly_groups = ['skynet-readonly']
        
        # Check for admin role
        if any(group in admin_groups for group in user_groups):
            return 'admin'
        
        # Check for readonly role
        if any(group in readonly_groups for group in user_groups):
            return 'readonly'
        
        # Default to user role
        return 'user'
    
    @staticmethod
    def check_permission(user_groups: List[str], permission: str) -> bool:
        """
        Check if user has a specific permission based on their role
        
        Args:
            user_groups: List of AD group names
            permission: Permission to check
            
        Returns:
            bool: True if user has permission
        """
        role = UserRolePermissions.get_user_role(user_groups)
        role_permissions = UserRolePermissions.ROLES.get(role, {})
        return role_permissions.get(permission, False)

def require_document_permission(permission: str = "read"):
    """
    Decorator to require specific document permissions
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract document_id from kwargs or path parameters
            document_id = kwargs.get('document_id')
            
            if not document_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Document ID required"
                )
            
            # Get current user from dependency injection
            current_user = kwargs.get('current_user')
            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            
            user_id = current_user['user_id']
            
            # Check document permissions
            if not DocumentPermissions.check_document_access(user_id, document_id, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions for {permission} access to document"
                )
            
            # Create audit log
            DocumentPermissions.create_document_audit_log(
                user_id, document_id, f"{permission}_access"
            )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator