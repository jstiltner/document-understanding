import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, status
from database.models import User, AuditLog
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class AuthService:
    """Service for user authentication and authorization"""
    
    def __init__(self, db: Session):
        self.db = db
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.secret_key = os.getenv("SECRET_KEY", "your-secret-key-here")
        self.algorithm = os.getenv("ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        
        # Role hierarchy (higher number = more permissions)
        self.role_hierarchy = {
            "viewer": 1,
            "reviewer": 2,
            "supervisor": 3,
            "admin": 4
        }
        
        # Permission definitions
        self.permissions = {
            "viewer": [
                "view_documents",
                "view_extractions",
                "view_analytics"
            ],
            "reviewer": [
                "view_documents",
                "view_extractions",
                "review_documents",
                "submit_feedback",
                "view_analytics"
            ],
            "supervisor": [
                "view_documents",
                "view_extractions",
                "review_documents",
                "submit_feedback",
                "view_analytics",
                "manage_assignments",
                "view_business_rules",
                "resolve_violations",
                "view_user_performance"
            ],
            "admin": [
                "view_documents",
                "view_extractions",
                "review_documents",
                "submit_feedback",
                "view_analytics",
                "manage_assignments",
                "view_business_rules",
                "resolve_violations",
                "view_user_performance",
                "manage_users",
                "manage_field_definitions",
                "manage_business_rules",
                "manage_system_config",
                "view_system_metrics",
                "manage_batches"
            ]
        }
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return self.pwd_context.hash(password)
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate a user with username and password"""
        try:
            user = self.db.query(User).filter(User.username == username).first()
            
            if not user:
                # Log failed login attempt
                self._log_auth_event("login_failed", username, "User not found")
                return None
            
            if not user.is_active:
                # Log inactive user login attempt
                self._log_auth_event("login_failed", username, "User account inactive")
                return None
            
            if not self.verify_password(password, user.hashed_password):
                # Log failed password attempt
                self._log_auth_event("login_failed", username, "Invalid password")
                return None
            
            # Update last login
            user.last_login = datetime.utcnow()
            self.db.commit()
            
            # Log successful login
            self._log_auth_event("login_success", username, "User authenticated successfully")
            
            return user
            
        except Exception as e:
            logger.error(f"Error authenticating user: {str(e)}")
            return None
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            username: str = payload.get("sub")
            
            if username is None:
                return None
            
            return payload
            
        except JWTError:
            return None
    
    def get_current_user(self, token: str) -> Optional[User]:
        """Get current user from JWT token"""
        try:
            payload = self.verify_token(token)
            if not payload:
                return None
            
            username = payload.get("sub")
            if not username:
                return None
            
            user = self.db.query(User).filter(User.username == username).first()
            
            if not user or not user.is_active:
                return None
            
            return user
            
        except Exception as e:
            logger.error(f"Error getting current user: {str(e)}")
            return None
    
    def create_user(self, user_data: Dict[str, Any]) -> User:
        """Create a new user"""
        try:
            # Hash password
            hashed_password = self.get_password_hash(user_data["password"])
            
            # Create user
            user = User(
                username=user_data["username"],
                email=user_data["email"],
                hashed_password=hashed_password,
                full_name=user_data.get("full_name"),
                role=user_data.get("role", "reviewer"),
                is_active=user_data.get("is_active", True)
            )
            
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            
            # Log user creation
            self._log_auth_event("user_created", user.username, f"User created with role: {user.role}")
            
            return user
            
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise
    
    def update_user(self, user_id: int, user_data: Dict[str, Any]) -> Optional[User]:
        """Update an existing user"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return None
            
            # Update fields
            for key, value in user_data.items():
                if key == "password" and value:
                    user.hashed_password = self.get_password_hash(value)
                elif hasattr(user, key) and key != "id":
                    setattr(user, key, value)
            
            self.db.commit()
            self.db.refresh(user)
            
            # Log user update
            self._log_auth_event("user_updated", user.username, f"User updated: {list(user_data.keys())}")
            
            return user
            
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            raise
    
    def delete_user(self, user_id: int) -> bool:
        """Soft delete a user (deactivate)"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            user.is_active = False
            self.db.commit()
            
            # Log user deletion
            self._log_auth_event("user_deactivated", user.username, "User account deactivated")
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            return False
    
    def has_permission(self, user: User, permission: str) -> bool:
        """Check if user has a specific permission"""
        if not user or not user.is_active:
            return False
        
        user_permissions = self.permissions.get(user.role, [])
        return permission in user_permissions
    
    def has_role_or_higher(self, user: User, required_role: str) -> bool:
        """Check if user has required role or higher"""
        if not user or not user.is_active:
            return False
        
        user_level = self.role_hierarchy.get(user.role, 0)
        required_level = self.role_hierarchy.get(required_role, 0)
        
        return user_level >= required_level
    
    def get_user_permissions(self, user: User) -> List[str]:
        """Get all permissions for a user"""
        if not user or not user.is_active:
            return []
        
        return self.permissions.get(user.role, [])
    
    def get_all_users(self, include_inactive: bool = False) -> List[User]:
        """Get all users"""
        query = self.db.query(User)
        
        if not include_inactive:
            query = query.filter(User.is_active == True)
        
        return query.all()
    
    def get_users_by_role(self, role: str) -> List[User]:
        """Get all users with a specific role"""
        return self.db.query(User).filter(
            User.role == role,
            User.is_active == True
        ).all()
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """Change user password"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            
            # Verify old password
            if not self.verify_password(old_password, user.hashed_password):
                self._log_auth_event("password_change_failed", user.username, "Invalid old password")
                return False
            
            # Update password
            user.hashed_password = self.get_password_hash(new_password)
            self.db.commit()
            
            # Log password change
            self._log_auth_event("password_changed", user.username, "Password changed successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Error changing password: {str(e)}")
            return False
    
    def reset_password(self, username: str, new_password: str) -> bool:
        """Reset user password (admin function)"""
        try:
            user = self.db.query(User).filter(User.username == username).first()
            if not user:
                return False
            
            # Update password
            user.hashed_password = self.get_password_hash(new_password)
            self.db.commit()
            
            # Log password reset
            self._log_auth_event("password_reset", user.username, "Password reset by admin")
            
            return True
            
        except Exception as e:
            logger.error(f"Error resetting password: {str(e)}")
            return False
    
    def _log_auth_event(self, action: str, username: str, details: str):
        """Log authentication events"""
        try:
            audit_log = AuditLog(
                document_id=None,
                action=action,
                details={"username": username, "details": details},
                user_id=username,
                timestamp=datetime.utcnow()
            )
            self.db.add(audit_log)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error logging auth event: {str(e)}")
    
    def initialize_default_admin(self):
        """Initialize default admin user if none exists"""
        try:
            admin_count = self.db.query(User).filter(User.role == "admin").count()
            
            if admin_count == 0:
                # Create default admin
                default_admin = {
                    "username": "admin",
                    "email": "admin@company.com",
                    "password": "admin123",  # Should be changed immediately
                    "full_name": "System Administrator",
                    "role": "admin",
                    "is_active": True
                }
                
                self.create_user(default_admin)
                logger.info("Default admin user created. Please change the password immediately.")
                
        except Exception as e:
            logger.error(f"Error initializing default admin: {str(e)}")