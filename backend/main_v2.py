from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
import os
from datetime import datetime
import logging

from database.database import engine, get_db
from database.models import Base
from services.auth_service import AuthService
from services.field_service import FieldDefinitionService
from services.llm_service import LLMService
from routers import auth, integration, monitoring, dev_tools
from security.hipaa_middleware import HIPAASecurityMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="Document Understanding API",
        version="2.0.0",
        description="""
## Enterprise AI-Powered Document Processing System

A comprehensive HIPAA-compliant document extraction and processing platform designed for healthcare organizations.

### Key Features

- **🔍 Advanced OCR Processing**: Multi-engine OCR with quality assessment
- **🤖 AI Field Extraction**: Configurable LLM-powered data extraction
- **📋 Review Workflows**: Human-in-the-loop validation and correction
- **🔄 Reinforcement Learning**: Continuous improvement from human feedback
- **📊 Quality Assessment**: Document quality scoring and improvement recommendations
- **⚡ Batch Processing**: High-volume document processing with queue management
- **🔐 RBAC Security**: Role-based access control with audit logging
- **📈 Analytics**: Performance monitoring and staff analytics
- **🔗 Integration APIs**: REST APIs with multiple export formats
- **☁️ Azure Integration**: Azure Entra ID and Azure OpenAI support

### Authentication

Most endpoints require authentication. Use the `/auth/login` endpoint to obtain a JWT token, then include it in the `Authorization` header as `Bearer <token>`.

### Development Mode

When `DEVELOPMENT_MODE=true`, authentication is bypassed for easier testing. This should **never** be used in production.

### Rate Limits

- Standard endpoints: 100 requests/minute
- Upload endpoints: 10 requests/minute
- Batch processing: 5 requests/minute

### Error Handling

All endpoints return consistent error responses:
```json
{
    "detail": "Error description",
    "error_code": "ERROR_CODE",
    "timestamp": "2024-01-01T00:00:00Z"
}
```
        """,
        routes=app.routes,
        tags=[
            {
                "name": "Authentication",
                "description": "User authentication and authorization endpoints"
            },
            {
                "name": "Documents",
                "description": "Document upload, processing, and management"
            },
            {
                "name": "Fields",
                "description": "Field definition configuration and management"
            },
            {
                "name": "Analytics",
                "description": "Performance analytics and reporting"
            },
            {
                "name": "Integration",
                "description": "System integration and export APIs"
            },
            {
                "name": "Monitoring",
                "description": "System monitoring, health checks, and alerts"
            },
            {
                "name": "Development",
                "description": "Development and debugging utilities"
            }
        ]
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token obtained from /auth/login endpoint"
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for service-to-service authentication"
        }
    }
    
    # Add global security requirement
    openapi_schema["security"] = [
        {"BearerAuth": []},
        {"ApiKeyAuth": []}
    ]
    
    # Add server information
    openapi_schema["servers"] = [
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        },
        {
            "url": "https://api.docprocessing.company.com",
            "description": "Production server"
        }
    ]
    
    # Add contact and license information
    openapi_schema["info"]["contact"] = {
        "name": "Development Team",
        "email": "dev@company.com",
        "url": "https://company.com/support"
    }
    
    openapi_schema["info"]["license"] = {
        "name": "Proprietary",
        "url": "https://company.com/license"
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app = FastAPI(
    title="Document Understanding API",
    description="Enterprise AI-powered document extraction and processing system",
    version="2.0.0",
    docs_url=None,  # We'll create custom docs
    redoc_url=None,
    openapi_url="/openapi.json"
)

app.openapi = custom_openapi

# Add HIPAA security middleware
app.add_middleware(HIPAASecurityMiddleware)

# Configure CORS
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(integration.router)
app.include_router(monitoring.router)

# Include development tools (only in development mode)
if os.getenv("DEVELOPMENT_MODE", "false").lower() == "true":
    app.include_router(dev_tools.router)

# Include existing routers (assuming they exist)
try:
    from routers import documents, analytics, fields
    app.include_router(documents.router)
    app.include_router(analytics.router)
    app.include_router(fields.router)
except ImportError:
    logger.warning("Some routers not found - they may need to be created")

@app.on_event("startup")
async def startup_event():
    """Initialize system on startup"""
    try:
        # Initialize database session
        db = next(get_db())
        
        # Initialize default admin user
        auth_service = AuthService(db)
        auth_service.initialize_default_admin()
        
        # Initialize default field definitions
        field_service = FieldDefinitionService(db)
        field_service.initialize_default_fields()
        
        logger.info("System initialization completed successfully")
        
    except Exception as e:
        logger.error(f"System initialization failed: {str(e)}")
    finally:
        if 'db' in locals():
            db.close()

@app.get("/", tags=["System"])
async def root():
    """
    API root endpoint providing system information and available features.
    
    Returns basic system information, version, and available endpoint categories.
    """
    return {
        "message": "Document Understanding API",
        "version": "2.0.0",
        "status": "operational",
        "features": [
            "Batch Processing & Queue Management",
            "Document Quality Assessment",
            "Business Rules Validation",
            "Smart Document Splitting & Classification",
            "Role-Based Access Control (RBAC)",
            "System Integration APIs & Export",
            "Operational Monitoring & Alerting",
            "Staff Performance Analytics",
            "Reinforcement Learning from Human Feedback",
            "HIPAA Compliance & Security",
            "Azure Entra ID Integration",
            "Azure OpenAI Support"
        ],
        "endpoints": {
            "authentication": "/auth",
            "documents": "/documents",
            "fields": "/fields",
            "analytics": "/analytics",
            "integration": "/integration",
            "monitoring": "/monitoring",
            "documentation": "/docs",
            "api_schema": "/openapi.json"
        },
        "development": {
            "swagger_ui": "/docs",
            "redoc": "/redoc",
            "health_check": "/health",
            "version_info": "/version"
        }
    }

@app.get("/health", tags=["Monitoring"])
async def health_check(db: Session = Depends(get_db)):
    """
    Comprehensive health check endpoint.
    
    Checks the status of all system components including database, Redis,
    Celery workers, and external service connections.
    
    Returns:
        dict: Health status of all system components
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "services": {
            "api": "operational",
            "authentication": "enabled",
            "monitoring": "active"
        },
        "providers": {},
        "development_mode": os.getenv("DEVELOPMENT_MODE", "false").lower() == "true"
    }
    
    # Check database connection
    try:
        db.execute("SELECT 1")
        health_status["services"]["database"] = "connected"
    except Exception as e:
        health_status["services"]["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check LLM providers
    try:
        llm_service = LLMService(db)
        provider_status = llm_service.get_provider_status()
        health_status["providers"] = provider_status
        
        # Check if at least one provider is available
        available_providers = [p for p, status in provider_status.items() if status.get('available')]
        if not available_providers:
            health_status["status"] = "degraded"
            health_status["warnings"] = ["No LLM providers configured"]
            
    except Exception as e:
        health_status["providers"] = {"error": str(e)}
        health_status["status"] = "degraded"
    
    # Check Redis connection (if configured)
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        try:
            import redis
            r = redis.from_url(redis_url)
            r.ping()
            health_status["services"]["redis"] = "connected"
        except Exception as e:
            health_status["services"]["redis"] = f"error: {str(e)}"
            health_status["status"] = "degraded"
    else:
        health_status["services"]["redis"] = "not_configured"
    
    # Check Celery workers (if configured)
    try:
        from celery_app import celery_app
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        if active_workers:
            health_status["services"]["celery"] = f"running ({len(active_workers)} workers)"
        else:
            health_status["services"]["celery"] = "no_workers"
    except Exception:
        health_status["services"]["celery"] = "not_configured"
    
    return health_status

@app.get("/version", tags=["System"])
async def get_version():
    """
    Get detailed API version and feature information.
    
    Returns comprehensive version information including release history,
    feature sets, and compatibility information.
    """
    return {
        "version": "2.0.0",
        "release_date": "2024-01-01",
        "api_version": "v2",
        "compatibility": {
            "minimum_client_version": "1.0.0",
            "supported_formats": ["PDF", "TIFF", "PNG", "JPEG"],
            "max_file_size": "50MB",
            "max_batch_size": 100
        },
        "features": {
            "core": [
                "Multi-engine OCR processing",
                "AI-powered field extraction",
                "Human review workflows",
                "Configurable field definitions",
                "Confidence scoring",
                "HIPAA compliance"
            ],
            "enterprise": [
                "Batch processing & queue management",
                "Document quality assessment",
                "Business rules validation",
                "Smart document splitting & classification",
                "Role-based access control (RBAC)",
                "Audit logging & compliance",
                "System integration APIs",
                "Operational monitoring & alerting",
                "Staff performance analytics",
                "Predictive workload management"
            ],
            "ai_ml": [
                "Reinforcement learning from human feedback",
                "Multi-provider LLM support (Anthropic, OpenAI, Azure)",
                "Confidence-based workflow routing",
                "Performance tracking & optimization",
                "Model version management"
            ],
            "integrations": [
                "Azure Entra ID authentication",
                "Azure OpenAI service",
                "REST API with multiple export formats",
                "Webhook notifications",
                "Real-time monitoring dashboards"
            ]
        },
        "changelog": {
            "2.0.0": [
                "Added Azure integrations",
                "Enhanced developer experience",
                "Comprehensive Swagger documentation",
                "Development mode support",
                "Provider status monitoring"
            ],
            "1.5.0": [
                "Enterprise features",
                "Batch processing",
                "Quality assessment",
                "Business rules engine"
            ],
            "1.0.0": [
                "Initial release",
                "Basic document processing",
                "OCR and LLM extraction"
            ]
        }
    }

# Custom Swagger UI with enhanced features
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """Custom Swagger UI with enhanced developer features"""
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Interactive API Documentation",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
        swagger_ui_parameters={
            "deepLinking": True,
            "displayRequestDuration": True,
            "docExpansion": "none",
            "operationsSorter": "alpha",
            "filter": True,
            "showExtensions": True,
            "showCommonExtensions": True,
            "tryItOutEnabled": True
        }
    )

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    """ReDoc documentation interface"""
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{app.title} - API Documentation</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
        <style>
            body {{ margin: 0; padding: 0; }}
        </style>
    </head>
    <body>
        <redoc spec-url="{app.openapi_url}"></redoc>
        <script src="https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js"></script>
    </body>
    </html>
    """)

# Development endpoints (only available in development mode)
@app.get("/dev/status", tags=["Development"], include_in_schema=False)
async def dev_status(db: Session = Depends(get_db)):
    """
    Development status endpoint with detailed system information.
    
    Only available when DEVELOPMENT_MODE=true.
    """
    if not os.getenv("DEVELOPMENT_MODE", "false").lower() == "true":
        return {"error": "Development mode not enabled"}
    
    try:
        llm_service = LLMService(db)
        provider_status = llm_service.get_provider_status()
        
        # Test provider connections
        connection_tests = {}
        for provider in provider_status.keys():
            if provider_status[provider].get('available'):
                connection_tests[provider] = llm_service.test_provider_connection(provider)
        
        return {
            "development_mode": True,
            "environment_variables": {
                "DATABASE_URL": bool(os.getenv("DATABASE_URL")),
                "REDIS_URL": bool(os.getenv("REDIS_URL")),
                "ANTHROPIC_API_KEY": bool(os.getenv("ANTHROPIC_API_KEY")),
                "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
                "AZURE_OPENAI_ENDPOINT": bool(os.getenv("AZURE_OPENAI_ENDPOINT")),
                "AZURE_OPENAI_API_KEY": bool(os.getenv("AZURE_OPENAI_API_KEY")),
                "AZURE_CLIENT_ID": bool(os.getenv("AZURE_CLIENT_ID")),
                "AZURE_TENANT_ID": bool(os.getenv("AZURE_TENANT_ID"))
            },
            "providers": provider_status,
            "connection_tests": connection_tests,
            "database_tables": [
                "users", "documents", "field_definitions", "business_rules",
                "batch_uploads", "document_quality", "workflow_assignments",
                "system_metrics", "audit_logs"
            ]
        }
    except Exception as e:
        return {"error": f"Development status check failed: {str(e)}"}

@app.get("/dev/test-auth", tags=["Development"], include_in_schema=False)
async def dev_test_auth():
    """
    Test authentication bypass in development mode.
    
    Returns mock user data when development mode is enabled.
    """
    if not os.getenv("DEVELOPMENT_MODE", "false").lower() == "true":
        return {"error": "Development mode not enabled"}
    
    return {
        "message": "Authentication bypass active",
        "mock_user": {
            "id": 1,
            "username": "dev_user",
            "email": "dev@company.com",
            "role": "admin",
            "permissions": ["read", "write", "admin"]
        },
        "warning": "This endpoint should never be available in production"
    }

@app.get("/dev/sample-data", tags=["Development"], include_in_schema=False)
async def dev_sample_data():
    """
    Get sample data for testing API endpoints.
    
    Returns example payloads for various API endpoints.
    """
    if not os.getenv("DEVELOPMENT_MODE", "false").lower() == "true":
        return {"error": "Development mode not enabled"}
    
    return {
        "field_definition": {
            "name": "patient_name",
            "display_name": "Patient Name",
            "description": "Full name of the patient",
            "field_type": "text",
            "is_required": True,
            "validation_pattern": "^[A-Za-z\\s]+$",
            "extraction_hints": {
                "keywords": ["patient", "name", "patient name"],
                "context": "Usually found at the top of the document"
            }
        },
        "business_rule": {
            "name": "member_id_validation",
            "description": "Validate member ID format",
            "rule_type": "validation",
            "conditions": {
                "field": "member_id",
                "operator": "matches",
                "value": "^[A-Z]{2}\\d{8}$"
            },
            "actions": {
                "on_success": "continue",
                "on_failure": "flag_for_review"
            }
        },
        "document_upload": {
            "file": "base64_encoded_pdf_content",
            "filename": "sample_document.pdf",
            "document_type": "authorization",
            "priority": "normal",
            "metadata": {
                "source": "fax",
                "received_date": "2024-01-01T10:00:00Z"
            }
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)