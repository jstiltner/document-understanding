# GitHub Copilot Instructions for Document Understanding API

## Project Overview

This is an enterprise-grade, HIPAA-compliant document processing system that extracts structured data from scanned insurance authorization/denial PDFs using AI. The system features OCR processing, configurable LLM field extraction, human review workflows, reinforcement learning, and comprehensive enterprise features.

## Architecture & Technology Stack

### Backend (Python)
- **Framework**: FastAPI with comprehensive OpenAPI documentation
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Task Queue**: Redis + Celery for async processing
- **Authentication**: JWT with RBAC, Azure Entra ID integration
- **AI/ML**: Multi-provider LLM support (Anthropic Claude, OpenAI GPT, Azure OpenAI)
- **OCR**: Tesseract and EasyOCR integration
- **Security**: HIPAA compliance middleware, audit logging, encryption

### Frontend (TypeScript/React)
- **Framework**: React with TypeScript
- **Styling**: Bootstrap for responsive UI
- **State Management**: React hooks and context
- **API Integration**: Axios for HTTP requests

### Infrastructure
- **Containerization**: Docker with multi-service compose
- **Monitoring**: Prometheus metrics, health checks
- **Development**: Comprehensive dev tools and debugging utilities

## Code Style & Conventions

### Python Backend
```python
# Use type hints consistently
from typing import Dict, List, Optional, Any
from pydantic import BaseModel

# Service pattern with dependency injection
class DocumentService:
    def __init__(self, db: Session, llm_service: LLMService):
        self.db = db
        self.llm_service = llm_service

# Async/await for I/O operations
async def process_document(file: UploadFile) -> Dict[str, Any]:
    # Implementation
```

### TypeScript Frontend
```typescript
// Use interfaces for type definitions
interface DocumentData {
  id: string;
  filename: string;
  status: 'processing' | 'completed' | 'review_required';
  extractedFields: Record<string, any>;
}

// React functional components with hooks
const DocumentList: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentData[]>([]);
  // Component logic
};
```

## Key Patterns & Best Practices

### 1. Service Layer Pattern
- All business logic in service classes (`backend/services/`)
- Services injected via FastAPI dependencies
- Database operations abstracted through services

### 2. Router Organization
- Feature-based routing (`backend/routers/`)
- Consistent error handling and response formats
- Comprehensive OpenAPI documentation with examples

### 3. Database Models
- SQLAlchemy models with relationships (`backend/database/models.py`)
- Audit logging for all data changes
- Encryption for sensitive fields

### 4. Configuration Management
- Environment-based configuration
- Development mode with authentication bypass
- Configurable field definitions stored in database

### 5. Error Handling
```python
# Consistent error responses
raise HTTPException(
    status_code=status.HTTP_400_BAD_REQUEST,
    detail="Descriptive error message",
    headers={"X-Error-Code": "VALIDATION_ERROR"}
)
```

## Development Workflow

### Setup
1. Run `scripts/setup-dev.sh` (Linux/Mac) or `scripts/setup-dev.bat` (Windows)
2. Set `DEVELOPMENT_MODE=true` in `.env`
3. Configure API keys for LLM providers
4. Start with `./scripts/start-dev.sh`

### Testing
- Use `/dev/*` endpoints for testing and debugging
- Test LLM providers: `GET /dev/test-llm-providers`
- Test OCR engines: `POST /dev/test-ocr`
- Full pipeline test: `POST /dev/test-full-pipeline`

### Development Mode Features
- Authentication bypass (mock admin user)
- Enhanced debugging endpoints
- Detailed error responses
- Provider connection testing

## Critical Components

### 1. Document Processing Pipeline
```
PDF/Image Upload → OCR Processing → LLM Field Extraction → 
Business Rules Validation → Human Review (if needed) → 
Database Storage → Audit Logging
```

### 2. LLM Integration (`backend/services/llm_service.py`)
- Multi-provider support with fallback
- Configurable field definitions
- Confidence scoring and review routing
- Reinforcement learning from human feedback

### 3. Authentication & Authorization
- JWT tokens with role-based permissions
- Azure Entra ID integration for enterprise
- Development mode bypass for testing
- Comprehensive audit logging

### 4. Quality Assessment (`backend/services/quality_service.py`)
- Document quality scoring
- OCR confidence analysis
- Improvement recommendations
- Performance tracking

## Security Considerations

### HIPAA Compliance
- All PHI encrypted at rest and in transit
- Comprehensive audit logging
- Access controls and user permissions
- Data retention policies

### Authentication
- Never bypass authentication in production
- Use strong JWT secrets
- Implement proper session management
- Azure Entra ID for enterprise SSO

### Data Handling
- Sanitize all inputs
- Validate file uploads
- Secure temporary file handling
- Proper error message sanitization

## Common Tasks & Code Patterns

### Adding New Field Types
1. Update `FieldDefinition` model with new type
2. Add validation logic in `FieldDefinitionService`
3. Update LLM prompts to handle new type
4. Add frontend UI components

### Adding New LLM Providers
1. Create provider service in `backend/services/`
2. Implement standard interface methods
3. Update `LLMService` to include new provider
4. Add configuration variables
5. Update provider status monitoring

### Adding New API Endpoints
```python
@router.post("/documents", response_model=DocumentResponse)
async def create_document(
    document_data: DocumentCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> DocumentResponse:
    """
    Create a new document with comprehensive documentation.
    
    - **document_data**: Document creation payload
    - **Returns**: Created document with metadata
    """
    # Implementation with proper error handling
```

### Database Migrations
- Use Alembic for schema changes
- Always backup before migrations
- Test migrations in development first
- Document breaking changes

## Testing Guidelines

### Unit Tests
- Test all service methods
- Mock external dependencies
- Use pytest fixtures for database setup
- Aim for >80% code coverage

### Integration Tests
- Test complete API endpoints
- Use test database
- Test authentication flows
- Validate business logic

### Development Testing
- Use `/dev/test-*` endpoints
- Test with real documents
- Validate LLM provider responses
- Check Azure integrations

## Monitoring & Debugging

### Health Checks
- `/health` - Comprehensive system status
- `/dev/status` - Detailed development information
- `/dev/debug-info` - System configuration details

### Logging
- Structured logging with correlation IDs
- Different log levels for development/production
- Audit logs for all data changes
- Performance metrics collection

### Metrics
- Processing times and throughput
- LLM provider performance
- User activity and system usage
- Error rates and types

## Deployment Considerations

### Environment Variables
```bash
# Core Configuration
DEVELOPMENT_MODE=false  # Never true in production
DATABASE_URL=postgresql://...
REDIS_URL=redis://...

# LLM Providers
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=...

# Security
SECRET_KEY=...  # Strong, unique key
ALLOWED_ORIGINS=...  # Specific domains only
```

### Docker Deployment
- Use multi-stage builds for optimization
- Separate containers for API, workers, and frontend
- Health checks in all containers
- Proper secret management

### Scaling Considerations
- Horizontal scaling with multiple API instances
- Celery workers for background processing
- Database connection pooling
- Redis for session storage and caching

## Troubleshooting Common Issues

### LLM Provider Errors
- Check API keys and quotas
- Validate model availability
- Test with `/dev/test-llm-providers`
- Review provider-specific error codes

### Database Connection Issues
- Verify connection string format
- Check network connectivity
- Validate credentials and permissions
- Review connection pool settings

### OCR Processing Problems
- Verify Tesseract installation
- Check file format support
- Validate file size limits
- Test with sample documents

### Authentication Issues
- Verify JWT secret configuration
- Check token expiration settings
- Validate Azure Entra ID setup
- Test with development mode bypass

## Future Development Guidelines

### Adding New Features
1. Design API endpoints first
2. Update OpenAPI documentation
3. Implement backend services
4. Add frontend components
5. Write comprehensive tests
6. Update documentation

### Performance Optimization
- Profile database queries
- Optimize LLM API calls
- Implement caching strategies
- Monitor resource usage

### Security Updates
- Regular dependency updates
- Security vulnerability scanning
- Penetration testing
- Compliance audits

## Resources & Documentation

- **API Documentation**: `/docs` (Swagger UI)
- **Developer Guide**: `docs/developer-guide.md`
- **Architecture Overview**: `README.md`
- **Database Schema**: `backend/database/models.py`
- **Configuration Reference**: `.env.example`

## Contact & Support

For questions about this codebase:
1. Check existing documentation first
2. Use development debugging tools
3. Review similar implementations in the codebase
4. Follow established patterns and conventions

Remember: This is a healthcare system handling PHI. Always prioritize security, compliance, and data protection in all development decisions.