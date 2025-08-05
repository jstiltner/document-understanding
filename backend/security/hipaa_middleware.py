import os
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Request, Response, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from database.database import Base, get_db

logger = logging.getLogger(__name__)

class HIPAAAuditLog(Base):
    """HIPAA-compliant audit logging model"""
    __tablename__ = "hipaa_audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    session_id = Column(String, nullable=False)
    action = Column(String, nullable=False)  # CREATE, READ, UPDATE, DELETE
    resource_type = Column(String, nullable=False)  # document, patient_data, field_definition
    resource_id = Column(String, nullable=False)
    phi_accessed = Column(Boolean, default=False)
    ip_address = Column(String, nullable=False)
    user_agent = Column(String)
    request_path = Column(String, nullable=False)
    request_method = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    success = Column(Boolean, nullable=False)
    failure_reason = Column(String)
    data_hash = Column(String)  # Hash of accessed data for integrity verification

class HIPAASecurityMiddleware:
    """HIPAA-compliant security middleware"""
    
    def __init__(self):
        self.hipaa_mode = os.getenv("HIPAA_COMPLIANCE_MODE", "false").lower() == "true"
        self.session_timeout = int(os.getenv("SESSION_TIMEOUT_MINUTES", "15"))
        self.max_failed_attempts = int(os.getenv("FAILED_LOGIN_LOCKOUT_ATTEMPTS", "3"))
        self.require_mfa = os.getenv("REQUIRE_MFA", "false").lower() == "true"
        
    async def __call__(self, request: Request, call_next):
        """Main middleware function"""
        start_time = datetime.utcnow()
        
        # Skip HIPAA checks for health endpoints and static files
        if self._is_exempt_path(request.url.path):
            return await call_next(request)
        
        # Extract client information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent", "")
        
        try:
            # Validate session and authentication
            user_id, session_id = await self._validate_session(request)
            
            # Check access permissions
            await self._check_access_permissions(request, user_id)
            
            # Process request
            response = await call_next(request)
            
            # Log successful access
            await self._log_access(
                user_id=user_id,
                session_id=session_id,
                request=request,
                client_ip=client_ip,
                user_agent=user_agent,
                success=True,
                response_status=response.status_code
            )
            
            # Add security headers
            self._add_security_headers(response)
            
            return response
            
        except HTTPException as e:
            # Log failed access attempt
            await self._log_access(
                user_id="anonymous",
                session_id="",
                request=request,
                client_ip=client_ip,
                user_agent=user_agent,
                success=False,
                failure_reason=str(e.detail)
            )
            raise
        except Exception as e:
            # Log unexpected errors
            logger.error(f"HIPAA middleware error: {str(e)}")
            await self._log_access(
                user_id="system",
                session_id="",
                request=request,
                client_ip=client_ip,
                user_agent=user_agent,
                success=False,
                failure_reason=f"System error: {str(e)}"
            )
            raise HTTPException(status_code=500, detail="Internal server error")
    
    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from HIPAA checks"""
        exempt_paths = [
            "/health",
            "/docs",
            "/openapi.json",
            "/static/",
            "/favicon.ico"
        ]
        return any(path.startswith(exempt) for exempt in exempt_paths)
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address"""
        # Check for forwarded headers (load balancer/proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    async def _validate_session(self, request: Request) -> tuple[str, str]:
        """Validate user session and authentication"""
        if not self.hipaa_mode:
            # In non-HIPAA mode, return default user
            return "default_user", "default_session"
        
        # Extract authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # Validate JWT token (simplified - implement proper JWT validation)
        try:
            # This is a placeholder - implement proper JWT validation
            token = auth_header.replace("Bearer ", "")
            user_id, session_id = self._validate_jwt_token(token)
            
            # Check session timeout
            if self._is_session_expired(session_id):
                raise HTTPException(status_code=401, detail="Session expired")
            
            return user_id, session_id
            
        except Exception as e:
            raise HTTPException(status_code=401, detail="Invalid authentication")
    
    def _validate_jwt_token(self, token: str) -> tuple[str, str]:
        """Validate JWT token and extract user info"""
        # Placeholder implementation - use proper JWT library like python-jose
        # This should validate signature, expiration, and extract claims
        if token == "valid_token":
            return "user123", "session456"
        raise ValueError("Invalid token")
    
    def _is_session_expired(self, session_id: str) -> bool:
        """Check if session has expired"""
        # Placeholder - implement session storage and timeout checking
        return False
    
    async def _check_access_permissions(self, request: Request, user_id: str):
        """Check if user has permission to access resource"""
        if not self.hipaa_mode:
            return
        
        # Implement role-based access control
        path = request.url.path
        method = request.method
        
        # Example: Check if user can access PHI
        if self._is_phi_endpoint(path):
            if not self._user_has_phi_access(user_id):
                raise HTTPException(
                    status_code=403, 
                    detail="Insufficient permissions to access PHI"
                )
    
    def _is_phi_endpoint(self, path: str) -> bool:
        """Check if endpoint accesses PHI"""
        phi_endpoints = [
            "/documents",
            "/upload",
            "/review"
        ]
        return any(path.startswith(endpoint) for endpoint in phi_endpoints)
    
    def _user_has_phi_access(self, user_id: str) -> bool:
        """Check if user has PHI access permissions"""
        # Placeholder - implement proper role checking
        return True
    
    async def _log_access(
        self,
        user_id: str,
        session_id: str,
        request: Request,
        client_ip: str,
        user_agent: str,
        success: bool,
        response_status: int = None,
        failure_reason: str = None
    ):
        """Log access attempt for HIPAA audit trail"""
        try:
            db = next(get_db())
            
            # Determine action type
            action = self._get_action_type(request.method, request.url.path)
            
            # Determine resource type and ID
            resource_type, resource_id = self._extract_resource_info(request.url.path)
            
            # Check if PHI was accessed
            phi_accessed = self._is_phi_endpoint(request.url.path) and success
            
            # Create data hash for integrity
            data_hash = self._create_data_hash(user_id, request.url.path, str(datetime.utcnow()))
            
            audit_log = HIPAAAuditLog(
                user_id=user_id,
                session_id=session_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                phi_accessed=phi_accessed,
                ip_address=client_ip,
                user_agent=user_agent,
                request_path=request.url.path,
                request_method=request.method,
                success=success,
                failure_reason=failure_reason,
                data_hash=data_hash
            )
            
            db.add(audit_log)
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log HIPAA audit entry: {str(e)}")
        finally:
            db.close()
    
    def _get_action_type(self, method: str, path: str) -> str:
        """Determine CRUD action type"""
        if method == "GET":
            return "READ"
        elif method == "POST":
            return "CREATE"
        elif method in ["PUT", "PATCH"]:
            return "UPDATE"
        elif method == "DELETE":
            return "DELETE"
        return "OTHER"
    
    def _extract_resource_info(self, path: str) -> tuple[str, str]:
        """Extract resource type and ID from path"""
        parts = path.strip("/").split("/")
        
        if "documents" in parts:
            resource_type = "document"
            # Try to extract document ID
            try:
                doc_index = parts.index("documents")
                if len(parts) > doc_index + 1:
                    resource_id = parts[doc_index + 1]
                else:
                    resource_id = "collection"
            except (ValueError, IndexError):
                resource_id = "unknown"
        elif "fields" in parts:
            resource_type = "field_definition"
            try:
                field_index = parts.index("fields")
                if len(parts) > field_index + 1:
                    resource_id = parts[field_index + 1]
                else:
                    resource_id = "collection"
            except (ValueError, IndexError):
                resource_id = "unknown"
        else:
            resource_type = "system"
            resource_id = path
        
        return resource_type, resource_id
    
    def _create_data_hash(self, user_id: str, path: str, timestamp: str) -> str:
        """Create hash for data integrity verification"""
        data = f"{user_id}:{path}:{timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _add_security_headers(self, response: Response):
        """Add security headers to response"""
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"

# Security utility functions
class HIPAASecurityUtils:
    """HIPAA security utility functions"""
    
    @staticmethod
    def encrypt_phi_field(value: str, key: str = None) -> str:
        """Encrypt PHI field value"""
        # Placeholder - implement proper encryption
        # Use AES-256 encryption with proper key management
        return f"encrypted_{value}"
    
    @staticmethod
    def decrypt_phi_field(encrypted_value: str, key: str = None) -> str:
        """Decrypt PHI field value"""
        # Placeholder - implement proper decryption
        return encrypted_value.replace("encrypted_", "")
    
    @staticmethod
    def mask_phi_for_logging(value: str) -> str:
        """Mask PHI value for logging purposes"""
        if not value or len(value) < 4:
            return "***"
        return f"{value[:2]}***{value[-2:]}"
    
    @staticmethod
    def validate_data_retention(created_date: datetime, retention_days: int) -> bool:
        """Check if data should be retained based on HIPAA requirements"""
        retention_period = timedelta(days=retention_days)
        return datetime.utcnow() - created_date < retention_period
    
    @staticmethod
    def generate_breach_notification(incident_details: dict) -> dict:
        """Generate breach notification data"""
        return {
            "incident_id": f"BREACH_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.utcnow().isoformat(),
            "severity": "HIGH",
            "affected_records": incident_details.get("record_count", 0),
            "notification_required": True,
            "details": incident_details
        }