# Developer Guide

This guide provides comprehensive information for developers working on the Document Understanding Pipeline system.

## 🚀 Quick Start for Developers

### Prerequisites
- Python 3.9+
- Node.js 16+
- Docker & Docker Compose
- Git
- VS Code (recommended)

### Development Setup

1. **Clone and Setup**
```bash
git clone <repository-url>
cd doc-understanding
cp backend/.env.example backend/.env.dev
```

2. **Start Development Environment**
```bash
# Start all services in development mode
docker-compose -f docker-compose.dev.yml up -d

# Or run locally for development
./scripts/dev-setup.sh
```

3. **Access Development Services**
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Flower (Celery)**: http://localhost:5555
- **Database**: localhost:5432

## 🔧 Development Environment

### Environment Configuration

#### Development Mode Settings
```bash
# .env.dev - Development specific settings
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Development Authentication (bypasses production auth)
DEV_MODE=true
DEV_USER_ROLE=admin
DEV_SKIP_AUTH=true

# Local services
DATABASE_URL=postgresql://dev:dev@localhost:5432/doc_extraction_dev
REDIS_URL=redis://localhost:6379/1

# Development LLM settings (optional mock responses)
USE_MOCK_LLM=true
MOCK_CONFIDENCE_SCORE=0.85
```

### Development Authentication

In development mode, authentication is simplified:

```python
# Development user automatically created
{
    "username": "dev",
    "password": "dev123",
    "role": "admin",
    "permissions": ["*"]  # All permissions
}
```

### Hot Reload Setup

#### Backend Hot Reload
```bash
# FastAPI with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Celery with auto-reload
watchmedo auto-restart --directory=./ --pattern=*.py --recursive -- celery -A celery_app worker --loglevel=info
```

#### Frontend Hot Reload
```bash
cd frontend
npm start  # Automatic hot reload enabled
```

## 📚 API Documentation

### Swagger/OpenAPI Integration

The system includes comprehensive API documentation:

- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### API Testing

#### Using Swagger UI
1. Navigate to http://localhost:8000/docs
2. Click "Authorize" and use development credentials
3. Test endpoints directly in the browser

#### Using curl
```bash
# Get auth token
TOKEN=$(curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=dev&password=dev123" | jq -r '.access_token')

# Use token for API calls
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/documents"
```

#### Using Python requests
```python
import requests

# Login
response = requests.post("http://localhost:8000/auth/login", 
    data={"username": "dev", "password": "dev123"})
token = response.json()["access_token"]

# API call
headers = {"Authorization": f"Bearer {token}"}
documents = requests.get("http://localhost:8000/documents", headers=headers)
```

## 🏗️ Architecture Overview

### Project Structure
```
doc-understanding/
├── backend/
│   ├── auth/                 # Authentication & authorization
│   ├── database/             # Database models & migrations
│   ├── routers/              # API route handlers
│   ├── services/             # Business logic services
│   ├── tasks/                # Celery background tasks
│   ├── security/             # Security middleware
│   └── main.py               # FastAPI application
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── services/         # API client services
│   │   └── utils/            # Utility functions
│   └── public/
├── docs/                     # Documentation
├── scripts/                  # Development scripts
└── docker-compose.yml        # Production deployment
```

### Service Architecture

```mermaid
graph TB
    A[React Frontend] --> B[FastAPI Backend]
    B --> C[PostgreSQL Database]
    B --> D[Redis Queue]
    D --> E[Celery Workers]
    E --> F[OCR Service]
    E --> G[LLM Service]
    B --> H[Auth Service]
    B --> I[Monitoring Service]
```

## 🔌 Adding New Features

### Creating a New API Endpoint

1. **Define Pydantic Models**
```python
# models/schemas.py
from pydantic import BaseModel

class NewFeatureRequest(BaseModel):
    name: str
    description: str
    enabled: bool = True

class NewFeatureResponse(BaseModel):
    id: int
    name: str
    status: str
```

2. **Create Service Logic**
```python
# services/new_feature_service.py
from sqlalchemy.orm import Session
from database.models import NewFeature

class NewFeatureService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_feature(self, feature_data: dict) -> NewFeature:
        feature = NewFeature(**feature_data)
        self.db.add(feature)
        self.db.commit()
        return feature
```

3. **Add Router**
```python
# routers/new_feature.py
from fastapi import APIRouter, Depends
from auth.dependencies import require_permission

router = APIRouter(prefix="/features", tags=["features"])

@router.post("/", response_model=NewFeatureResponse)
async def create_feature(
    feature_data: NewFeatureRequest,
    current_user = Depends(require_permission("manage_features"))
):
    # Implementation here
    pass
```

4. **Register Router**
```python
# main.py
from routers import new_feature

app.include_router(new_feature.router)
```

### Adding Database Models

1. **Define Model**
```python
# database/models.py
class NewFeature(Base):
    __tablename__ = "new_features"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
```

2. **Create Migration**
```bash
# Generate migration
alembic revision --autogenerate -m "Add new_features table"

# Apply migration
alembic upgrade head
```

### Adding Background Tasks

1. **Define Task**
```python
# tasks/new_feature_tasks.py
from celery_app import celery_app

@celery_app.task(bind=True)
def process_new_feature(self, feature_id: int):
    # Task implementation
    return {"status": "completed", "feature_id": feature_id}
```

2. **Queue Task**
```python
# In your service or router
from tasks.new_feature_tasks import process_new_feature

# Queue the task
task = process_new_feature.delay(feature_id)
return {"task_id": task.id}
```

## 🧪 Testing

### Unit Tests

```python
# tests/test_new_feature.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_feature():
    response = client.post("/features/", json={
        "name": "Test Feature",
        "description": "Test description"
    })
    assert response.status_code == 200
    assert response.json()["name"] == "Test Feature"
```

### Integration Tests

```python
# tests/test_integration.py
def test_document_processing_pipeline():
    # Upload document
    # Verify OCR processing
    # Verify LLM extraction
    # Verify database storage
    pass
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend

# Run specific test file
pytest tests/test_new_feature.py

# Run with verbose output
pytest -v
```

## 🔍 Debugging

### Logging Configuration

```python
# Development logging
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Service-specific logging
logger = logging.getLogger(__name__)
logger.debug("Debug message")
logger.info("Info message")
logger.error("Error message")
```

### Debug Endpoints

Development mode includes debug endpoints:

```bash
# System status
GET /debug/status

# Database info
GET /debug/db-info

# Cache info
GET /debug/cache-info

# Task queue status
GET /debug/queue-status
```

### VS Code Configuration

`.vscode/launch.json`:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI Debug",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/backend/main.py",
            "console": "integratedTerminal",
            "env": {
                "ENVIRONMENT": "development"
            }
        }
    ]
}
```

## 🔧 Development Tools

### Database Management

```bash
# Connect to development database
psql postgresql://dev:dev@localhost:5432/doc_extraction_dev

# Reset database
./scripts/reset-db.sh

# Seed test data
python scripts/seed_data.py
```

### Queue Management

```bash
# Monitor Celery tasks
celery -A celery_app inspect active

# Purge all tasks
celery -A celery_app purge

# Monitor with Flower
celery -A celery_app flower
```

### Code Quality

```bash
# Format code
black backend/
isort backend/

# Lint code
flake8 backend/
mypy backend/

# Security check
bandit -r backend/
```

## 🚀 Deployment

### Development Deployment

```bash
# Build and start development environment
docker-compose -f docker-compose.dev.yml up --build

# Scale workers
docker-compose -f docker-compose.dev.yml up --scale celery-worker=3
```

### Production Deployment

```bash
# Build production images
docker-compose build

# Deploy to production
docker-compose up -d

# Health check
curl http://localhost:8000/health
```

## 📝 Contributing Guidelines

### Code Style

- **Python**: Follow PEP 8, use Black formatter
- **TypeScript**: Use ESLint configuration
- **Commit Messages**: Use conventional commits format

### Pull Request Process

1. Create feature branch from `develop`
2. Implement feature with tests
3. Update documentation
4. Submit PR with description
5. Address review feedback
6. Merge after approval

### Development Workflow

```bash
# Start new feature
git checkout develop
git pull origin develop
git checkout -b feature/new-feature

# Make changes
# ... code changes ...

# Test changes
pytest
npm test

# Commit changes
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/new-feature
```

## 🔗 Useful Resources

### Documentation Links
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [React Documentation](https://reactjs.org/docs/)

### Development Tools
- [Postman Collection](./postman/doc-understanding.json)
- [VS Code Extensions](./vscode/extensions.json)
- [Docker Compose Override](./docker-compose.override.yml)

### Troubleshooting
- [Common Issues](./troubleshooting.md)
- [Performance Tuning](./performance.md)
- [Security Guidelines](./security.md)