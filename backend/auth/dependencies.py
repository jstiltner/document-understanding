import os
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from database.database import get_db
from database.models import User
from services.auth_service import AuthService

security = HTTPBearer(auto_error=False)  # Don't auto-error for development mode

def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Get authentication service instance"""
    return AuthService(db)

def _create_dev_user(db: Session) -> User:
    """Create a mock development user"""
    # Create a mock user object for development
    dev_user = User(
        id=1,
        username="dev_user",
        email="dev@company.com",
        role="admin",
        is_active=True,
        hashed_password="dev_password_hash"
    )
    return dev_user

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user with development mode bypass"""
    
    # Development mode bypass
    if os.getenv("DEVELOPMENT_MODE", "false").lower() == "true":
        # If no credentials provided in dev mode, return mock user
        if not credentials:
            return _create_dev_user(db)
        
        # If credentials provided, try normal auth first, fallback to dev user
        try:
            token = credentials.credentials
            user = auth_service.get_current_user(token)
            if user:
                return user
        except Exception:
            pass
        
        # Fallback to dev user in development mode
        return _create_dev_user(db)
    
    # Production mode - require valid credentials
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        user = auth_service.get_current_user(token)
        
        if user is None:
            raise credentials_exception
        
        return user
        
    except Exception:
        raise credentials_exception

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user with development mode support"""
    # In development mode, always consider user active
    if os.getenv("DEVELOPMENT_MODE", "false").lower() == "true":
        return current_user
    
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def require_permission(permission: str):
    """Decorator factory for requiring specific permissions with development mode bypass"""
    def permission_checker(
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthService = Depends(get_auth_service)
    ) -> User:
        # Development mode bypass - grant all permissions
        if os.getenv("DEVELOPMENT_MODE", "false").lower() == "true":
            return current_user
        
        if not auth_service.has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}"
            )
        return current_user
    
    return permission_checker

def require_role(role: str):
    """Decorator factory for requiring specific role or higher with development mode bypass"""
    def role_checker(
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthService = Depends(get_auth_service)
    ) -> User:
        # Development mode bypass - grant all roles
        if os.getenv("DEVELOPMENT_MODE", "false").lower() == "true":
            return current_user
        
        if not auth_service.has_role_or_higher(current_user, role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {role} or higher"
            )
        return current_user
    
    return role_checker

# Common permission dependencies
require_admin = require_role("admin")
require_supervisor = require_role("supervisor")
require_reviewer = require_role("reviewer")

require_view_documents = require_permission("view_documents")
require_review_documents = require_permission("review_documents")
require_manage_users = require_permission("manage_users")
require_manage_field_definitions = require_permission("manage_field_definitions")
require_manage_business_rules = require_permission("manage_business_rules")
require_view_system_metrics = require_permission("view_system_metrics")
require_manage_batches = require_permission("manage_batches")

def optional_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Optional authentication with development mode support"""
    
    # Development mode - return dev user if no credentials
    if os.getenv("DEVELOPMENT_MODE", "false").lower() == "true":
        if not credentials:
            return _create_dev_user(db)
    
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        user = auth_service.get_current_user(token)
        return user if user and user.is_active else None
        
    except Exception:
        # In development mode, fallback to dev user on auth failure
        if os.getenv("DEVELOPMENT_MODE", "false").lower() == "true":
            return _create_dev_user(db)
        return None

# Development-specific dependencies
def dev_mode_only():
    """Dependency that only allows access in development mode"""
    def dev_checker():
        if not os.getenv("DEVELOPMENT_MODE", "false").lower() == "true":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Endpoint not available in production mode"
            )
        return True
    return dev_checker

def get_dev_user(db: Session = Depends(get_db)) -> User:
    """Get development user (only available in dev mode)"""
    if not os.getenv("DEVELOPMENT_MODE", "false").lower() == "true":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Development endpoints not available"
        )
    return _create_dev_user(db)