from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import timedelta

from database.database import get_db
from database.models import User
from services.auth_service import AuthService
from auth.dependencies import (
    get_current_active_user, require_admin, require_manage_users,
    get_auth_service
)

router = APIRouter(prefix="/auth", tags=["authentication"])

# Pydantic models
class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str = None
    role: str = "reviewer"

class UserUpdate(BaseModel):
    email: EmailStr = None
    full_name: str = None
    role: str = None
    is_active: bool = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    full_name: str = None
    role: str
    is_active: bool
    permissions: List[str] = []
    
    class Config:
        from_attributes = True

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

class PasswordReset(BaseModel):
    username: str
    new_password: str

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Authenticate user and return access token"""
    
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=auth_service.access_token_expire_minutes)
    access_token = auth_service.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Get current user information"""
    
    permissions = auth_service.get_user_permissions(current_user)
    
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        permissions=permissions
    )

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Change current user's password"""
    
    success = auth_service.change_password(
        current_user.id,
        password_data.old_password,
        password_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid old password"
        )
    
    return {"message": "Password changed successfully"}

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    include_inactive: bool = False,
    current_user: User = Depends(require_manage_users),
    auth_service: AuthService = Depends(get_auth_service)
):
    """List all users (admin only)"""
    
    users = auth_service.get_all_users(include_inactive=include_inactive)
    
    result = []
    for user in users:
        permissions = auth_service.get_user_permissions(user)
        result.append(UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            permissions=permissions
        ))
    
    return result

@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_manage_users),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Create a new user (admin only)"""
    
    try:
        # Check if username already exists
        existing_user = auth_service.db.query(User).filter(User.username == user_data.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists"
            )
        
        # Check if email already exists
        existing_email = auth_service.db.query(User).filter(User.email == user_data.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        
        user = auth_service.create_user(user_data.dict())
        permissions = auth_service.get_user_permissions(user)
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            permissions=permissions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating user: {str(e)}"
        )

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(require_manage_users),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Update a user (admin only)"""
    
    try:
        # Filter out None values
        update_data = {k: v for k, v in user_data.dict().items() if v is not None}
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No data provided for update"
            )
        
        user = auth_service.update_user(user_id, update_data)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        permissions = auth_service.get_user_permissions(user)
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            is_active=user.is_active,
            permissions=permissions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user: {str(e)}"
        )

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_manage_users),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Deactivate a user (admin only)"""
    
    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    success = auth_service.delete_user(user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "User deactivated successfully"}

@router.post("/reset-password")
async def reset_password(
    password_data: PasswordReset,
    current_user: User = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Reset user password (admin only)"""
    
    success = auth_service.reset_password(
        password_data.username,
        password_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return {"message": "Password reset successfully"}

@router.get("/roles")
async def list_roles(
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """List available roles and their permissions"""
    
    return {
        "roles": auth_service.role_hierarchy,
        "permissions": auth_service.permissions
    }

@router.get("/users/by-role/{role}")
async def get_users_by_role(
    role: str,
    current_user: User = Depends(require_manage_users),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Get users by role (admin/supervisor only)"""
    
    if role not in auth_service.role_hierarchy:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role"
        )
    
    users = auth_service.get_users_by_role(role)
    
    result = []
    for user in users:
        result.append({
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "last_login": user.last_login.isoformat() if user.last_login else None
        })
    
    return result