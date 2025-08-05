import logging
from typing import Dict, Any, Optional
import requests
import jwt
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import os
from dotenv import load_dotenv

from database.models import User
from services.auth_service import AuthService

load_dotenv()

logger = logging.getLogger(__name__)

class AzureEntraIDService:
    """Service for Azure Entra ID (formerly Azure AD) authentication integration"""
    
    def __init__(self, db: Session):
        self.db = db
        self.auth_service = AuthService(db)
        
        # Azure Entra ID configuration
        self.tenant_id = os.getenv("AZURE_TENANT_ID")
        self.client_id = os.getenv("AZURE_CLIENT_ID")
        self.client_secret = os.getenv("AZURE_CLIENT_SECRET")
        self.redirect_uri = os.getenv("AZURE_REDIRECT_URI", "http://localhost:8000/auth/azure/callback")
        
        # Azure endpoints
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        self.token_endpoint = f"{self.authority}/oauth2/v2.0/token"
        self.userinfo_endpoint = "https://graph.microsoft.com/v1.0/me"
        self.jwks_uri = f"{self.authority}/discovery/v2.0/keys"
        
        # Scopes
        self.scopes = ["openid", "profile", "email", "User.Read"]
        
        self.enabled = all([self.tenant_id, self.client_id, self.client_secret])
        
        if not self.enabled:
            logger.warning("Azure Entra ID not configured - missing required environment variables")
    
    def get_authorization_url(self, state: str = None) -> str:
        """Generate Azure Entra ID authorization URL"""
        
        if not self.enabled:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Azure Entra ID not configured"
            )
        
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.scopes),
            "response_mode": "query"
        }
        
        if state:
            params["state"] = state
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.authority}/oauth2/v2.0/authorize?{query_string}"
    
    def exchange_code_for_token(self, authorization_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token"""
        
        if not self.enabled:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Azure Entra ID not configured"
            )
        
        try:
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": authorization_code,
                "grant_type": "authorization_code",
                "redirect_uri": self.redirect_uri,
                "scope": " ".join(self.scopes)
            }
            
            response = requests.post(self.token_endpoint, data=data)
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Error exchanging code for token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange authorization code"
            )
    
    def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user information from Microsoft Graph"""
        
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(self.userinfo_endpoint, headers=headers)
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Error getting user info: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to get user information"
            )
    
    def verify_id_token(self, id_token: str) -> Dict[str, Any]:
        """Verify and decode Azure ID token"""
        
        try:
            # Get signing keys from Azure
            jwks_response = requests.get(self.jwks_uri)
            jwks_response.raise_for_status()
            jwks = jwks_response.json()
            
            # Decode token header to get key ID
            unverified_header = jwt.get_unverified_header(id_token)
            key_id = unverified_header.get("kid")
            
            # Find the correct key
            signing_key = None
            for key in jwks["keys"]:
                if key["kid"] == key_id:
                    signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                    break
            
            if not signing_key:
                raise ValueError("Unable to find signing key")
            
            # Verify and decode token
            payload = jwt.decode(
                id_token,
                signing_key,
                algorithms=["RS256"],
                audience=self.client_id,
                issuer=f"{self.authority}/v2.0"
            )
            
            return payload
            
        except Exception as e:
            logger.error(f"Error verifying ID token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid ID token"
            )
    
    def authenticate_user(self, authorization_code: str) -> Dict[str, Any]:
        """Complete Azure authentication flow"""
        
        try:
            # Exchange code for tokens
            token_response = self.exchange_code_for_token(authorization_code)
            
            # Get user information
            access_token = token_response["access_token"]
            id_token = token_response.get("id_token")
            
            # Verify ID token if present
            if id_token:
                id_payload = self.verify_id_token(id_token)
                user_info = {
                    "id": id_payload.get("oid"),
                    "email": id_payload.get("email") or id_payload.get("preferred_username"),
                    "name": id_payload.get("name"),
                    "given_name": id_payload.get("given_name"),
                    "family_name": id_payload.get("family_name")
                }
            else:
                # Fallback to Graph API
                user_info = self.get_user_info(access_token)
            
            # Create or update user in local database
            user = self.create_or_update_user(user_info)
            
            # Generate local JWT token
            local_token = self.auth_service.create_access_token(
                data={"sub": user.username}
            )
            
            return {
                "access_token": local_token,
                "token_type": "bearer",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role
                },
                "azure_user_info": user_info
            }
            
        except Exception as e:
            logger.error(f"Azure authentication failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Azure authentication failed"
            )
    
    def create_or_update_user(self, azure_user_info: Dict[str, Any]) -> User:
        """Create or update user based on Azure user information"""
        
        try:
            email = azure_user_info.get("mail") or azure_user_info.get("userPrincipalName")
            username = email.split("@")[0] if email else azure_user_info.get("id")
            
            # Check if user exists
            user = self.db.query(User).filter(User.email == email).first()
            
            if user:
                # Update existing user
                user.full_name = azure_user_info.get("displayName") or azure_user_info.get("name")
                user.last_login = datetime.utcnow()
                self.db.commit()
                
                logger.info(f"Updated existing Azure user: {email}")
            else:
                # Create new user
                user_data = {
                    "username": username,
                    "email": email,
                    "password": "azure_sso",  # Placeholder - not used for SSO users
                    "full_name": azure_user_info.get("displayName") or azure_user_info.get("name"),
                    "role": self.determine_user_role(azure_user_info),
                    "is_active": True
                }
                
                user = self.auth_service.create_user(user_data)
                logger.info(f"Created new Azure user: {email}")
            
            return user
            
        except Exception as e:
            logger.error(f"Error creating/updating Azure user: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create/update user"
            )
    
    def determine_user_role(self, azure_user_info: Dict[str, Any]) -> str:
        """Determine user role based on Azure user information"""
        
        # Default role mapping - can be customized based on Azure groups or attributes
        email = azure_user_info.get("mail") or azure_user_info.get("userPrincipalName", "")
        
        # Example role mapping based on email domain or groups
        if "admin" in email.lower():
            return "admin"
        elif "supervisor" in email.lower() or "manager" in email.lower():
            return "supervisor"
        else:
            return "reviewer"  # Default role
    
    def get_azure_groups(self, access_token: str) -> List[str]:
        """Get user's Azure AD groups for role mapping"""
        
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(
                "https://graph.microsoft.com/v1.0/me/memberOf",
                headers=headers
            )
            response.raise_for_status()
            
            groups = response.json().get("value", [])
            return [group.get("displayName") for group in groups if group.get("displayName")]
            
        except Exception as e:
            logger.error(f"Error getting Azure groups: {str(e)}")
            return []
    
    def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh Azure access token"""
        
        try:
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
                "scope": " ".join(self.scopes)
            }
            
            response = requests.post(self.token_endpoint, data=data)
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Error refreshing token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Failed to refresh token"
            )
    
    def logout_user(self, post_logout_redirect_uri: str = None) -> str:
        """Generate Azure logout URL"""
        
        logout_url = f"{self.authority}/oauth2/v2.0/logout"
        
        if post_logout_redirect_uri:
            logout_url += f"?post_logout_redirect_uri={post_logout_redirect_uri}"
        
        return logout_url
    
    def is_configured(self) -> bool:
        """Check if Azure Entra ID is properly configured"""
        return self.enabled
    
    def get_configuration_status(self) -> Dict[str, Any]:
        """Get Azure configuration status for debugging"""
        
        return {
            "enabled": self.enabled,
            "tenant_id": bool(self.tenant_id),
            "client_id": bool(self.client_id),
            "client_secret": bool(self.client_secret),
            "redirect_uri": self.redirect_uri,
            "authority": self.authority,
            "scopes": self.scopes
        }