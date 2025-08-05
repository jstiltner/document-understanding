# Document Extraction Pipeline

A HIPAA-compliant, end-to-end document extraction pipeline for scanned insurance authorization/denial PDFs with OCR, LLM-powered field extraction, reinforcement learning, and comprehensive review workflows.

## 🚀 Enhanced Features

### **Core Processing**
- **PDF Upload**: Secure web interface and REST API endpoints for document upload
- **OCR Processing**: Tesseract and EasyOCR support for text extraction from scanned PDFs
- **LLM Field Extraction**: Configurable LLM integration (Claude 4, GPT-4) for structured data extraction
- **Review Workflow**: Interactive UI for reviewing and correcting low-confidence extractions

### **Advanced Capabilities**
- **Configurable Fields**: Dynamic field definitions through web interface - no hardcoded fields
- **Reinforcement Learning**: Human feedback automatically improves model performance
- **Performance Analytics**: Real-time model performance tracking and metrics
- **Audit Logging**: Complete HIPAA-compliant audit trail for all activities
- **Real-time Monitoring**: Dashboard with processing metrics and document status tracking

### **HIPAA Compliance**
- **Data Encryption**: End-to-end encryption for PHI at rest and in transit
- **Access Controls**: Role-based authentication and authorization
- **Audit Trails**: Comprehensive logging of all PHI access and modifications
- **Data Retention**: Configurable retention policies with secure deletion
- **Security Monitoring**: Real-time security event monitoring and alerting

## 🏗️ Architecture

- **Backend**: Python FastAPI with SQLAlchemy ORM and HIPAA security controls
- **Frontend**: React with TypeScript, Bootstrap, and secure authentication
- **Database**: PostgreSQL with encryption and comprehensive audit logging
- **OCR**: Tesseract OCR and EasyOCR with secure processing
- **LLM**: Configurable providers (Anthropic Claude, OpenAI GPT) with data privacy controls
- **Security**: TLS/SSL, data encryption, access controls, and audit logging
- **Deployment**: Docker Compose with security hardening

## 🔧 Configurable Field System

Fields are now completely configurable through the web interface:

### **Field Types Supported**:
- **Text**: General text fields
- **Date**: Date fields with validation (MM/DD/YYYY)
- **Email**: Email addresses with format validation
- **Phone**: Phone numbers with format validation
- **Number**: Numeric fields

### **Field Properties**:
- **Display Name**: User-friendly field name
- **Internal Name**: Database field identifier
- **Description**: Field purpose and context
- **Required/Optional**: Processing requirement level
- **Validation Pattern**: Regex validation for data quality
- **Extraction Hints**: Keywords and context clues for LLM

### **Default Insurance Fields** (auto-initialized):
**Required Fields**:
- Facility, Reference Number, Patient Names, Member ID, Date of Birth, Denial Reason

**Optional Fields**:
- Payer, Authorization Number, Account Number, Working DRG, 3rd Party Reviewer, Level of Care, Service, Clinical Guidelines, Provider TIN, Case Manager, Peer-to-Peer Contact Information

## 🤖 Reinforcement Learning System

### **Human Feedback Types**:
- **Confirmation** (+1.0 × confidence): Model prediction was correct
- **Correction** (-0.5 to -1.0): Model found field but value was incorrect
- **Addition** (-2.0): Model missed a field that human reviewer found
- **Removal** (-1.5 × confidence): Model extracted non-existent field

### **Performance Metrics**:
- **Precision**: Correct predictions / (Correct + False Positives)
- **Recall**: Correct predictions / (Correct + False Negatives)
- **F1-Score**: Harmonic mean of precision and recall
- **Reward Score**: Average RL feedback score (-2.0 to +1.0)

### **Learning Loop**:
```
Document Processing → Human Review → Feedback Capture →
Reward Calculation → Performance Tracking → Model Improvement
```

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

1. **Clone and configure**:
   ```bash
   git clone <repository-url>
   cd doc-understanding
   cp .env.example .env
   ```

2. **Edit `.env` file** with your API keys:
   ```bash
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here
   SECRET_KEY=your-secret-key-here
   ```

3. **Start all services**:
   ```bash
   docker-compose up -d
   ```

4. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Option 2: Local Development

#### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Tesseract OCR

#### Backend Setup

1. **Install system dependencies** (Ubuntu/Debian):
   ```bash
   sudo apt-get update
   sudo apt-get install tesseract-ocr tesseract-ocr-eng poppler-utils
   ```

2. **Set up Python environment**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your database URL and API keys
   ```

4. **Start the backend**:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

#### Frontend Setup

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Start the development server**:
   ```bash
   npm start
   ```

## 📖 Usage Guide

### 1. Upload Documents
- Navigate to the dashboard at http://localhost:3000
- Use the upload area to drag & drop or select PDF files
- Monitor processing status in real-time

### 2. Review Extractions
- Documents requiring review will show a "Review" button
- Use the review interface to verify and correct extracted fields
- Required fields must be completed for successful processing

### 3. Monitor Processing
- View processing metrics on the dashboard
- Track document status: pending → processing → completed/review_required
- Access detailed extraction results and confidence scores

### 4. Configure Settings
- Access configuration page to manage LLM providers
- Set API keys for Anthropic Claude and OpenAI
- Adjust confidence thresholds for review requirements

## 🛡️ HIPAA Compliance

This application is designed to be HIPAA-compliant for handling Protected Health Information (PHI) in healthcare environments.

### **Administrative Safeguards**

#### **Access Control & Authentication**
- **Role-Based Access Control (RBAC)**: Configurable user roles and permissions
- **User Authentication**: Secure login with session management
- **Access Logging**: All user actions logged with timestamps and user identification
- **Automatic Logout**: Configurable session timeouts for inactive users

#### **Audit Controls**
- **Comprehensive Audit Trail**: Every PHI access, modification, and deletion logged
- **Audit Log Protection**: Tamper-evident audit logs with integrity verification
- **Regular Audit Reviews**: Built-in reporting for compliance monitoring
- **Retention Policies**: Configurable audit log retention periods

### **Physical Safeguards**

#### **Data Center Security** (Deployment Dependent)
- **Secure Hosting**: Deploy in HIPAA-compliant cloud environments (AWS HIPAA, Azure Healthcare, GCP Healthcare)
- **Physical Access Controls**: Restricted access to servers and infrastructure
- **Environmental Controls**: Temperature, humidity, and power monitoring

### **Technical Safeguards**

#### **Data Encryption**
- **Encryption at Rest**: AES-256 encryption for database and file storage
- **Encryption in Transit**: TLS 1.3 for all network communications
- **Key Management**: Secure key rotation and management practices
- **Database Encryption**: PostgreSQL with transparent data encryption (TDE)

#### **Access Control**
```python
# Example: Role-based access control implementation
@app.middleware("http")
async def hipaa_access_control(request: Request, call_next):
    # Verify user authentication and authorization
    # Log all PHI access attempts
    # Enforce minimum necessary access principle
```

#### **Data Integrity**
- **Checksums**: File integrity verification for uploaded documents
- **Database Constraints**: Data validation and integrity constraints
- **Backup Verification**: Regular backup integrity testing
- **Version Control**: Document version tracking and change management

#### **Transmission Security**
- **HTTPS Only**: All communications encrypted with TLS 1.3
- **API Security**: OAuth 2.0 / JWT token-based authentication
- **Network Segmentation**: Isolated network zones for PHI processing
- **VPN Access**: Secure remote access for authorized personnel

### **HIPAA Implementation Features**

#### **Data Minimization**
- **Configurable Fields**: Only extract necessary PHI fields
- **Automatic Redaction**: Option to redact sensitive fields in logs
- **Retention Policies**: Automatic deletion of PHI after retention period
- **Data Masking**: Mask PHI in non-production environments

#### **Breach Detection & Response**
- **Security Monitoring**: Real-time monitoring for unauthorized access
- **Anomaly Detection**: Unusual access pattern alerts
- **Incident Response**: Automated breach notification workflows
- **Forensic Logging**: Detailed logs for security incident investigation

#### **Business Associate Agreements (BAA)**
- **Third-Party Services**: Ensure all external services (LLM providers, cloud hosting) have signed BAAs
- **Data Processing Agreements**: Clear data handling agreements with all vendors
- **Vendor Risk Assessment**: Regular security assessments of third-party providers

### **HIPAA Configuration**

#### **Environment Variables**
```bash
# HIPAA Security Settings
HIPAA_COMPLIANCE_MODE=true
ENCRYPTION_KEY_ROTATION_DAYS=90
SESSION_TIMEOUT_MINUTES=15
AUDIT_LOG_RETENTION_DAYS=2555  # 7 years
PHI_RETENTION_DAYS=2555
FAILED_LOGIN_LOCKOUT_ATTEMPTS=3
PASSWORD_MIN_LENGTH=12
REQUIRE_MFA=true
```

#### **Database Security**
```sql
-- Enable row-level security
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE field_extractions ENABLE ROW LEVEL SECURITY;

-- Create policies for PHI access
CREATE POLICY phi_access_policy ON documents
    FOR ALL TO authenticated_users
    USING (user_has_access(current_user_id(), id));
```

#### **Audit Logging Enhancement**
```python
class HIPAAAuditLog(Base):
    __tablename__ = "hipaa_audit_logs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    action = Column(String, nullable=False)  # CREATE, READ, UPDATE, DELETE
    resource_type = Column(String, nullable=False)  # document, patient_data
    resource_id = Column(String, nullable=False)
    phi_accessed = Column(Boolean, default=False)
    ip_address = Column(String, nullable=False)
    user_agent = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    success = Column(Boolean, nullable=False)
    failure_reason = Column(String)
```

### **Deployment Security**

#### **Docker Security Hardening**
```dockerfile
# Use non-root user
RUN adduser --disabled-password --gecos '' appuser
USER appuser

# Security scanning
RUN apt-get update && apt-get install -y --no-install-recommends \
    security-updates && \
    rm -rf /var/lib/apt/lists/*

# File permissions
COPY --chown=appuser:appuser . /app
```

#### **Network Security**
```yaml
# docker-compose.yml security enhancements
services:
  backend:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    networks:
      - internal
  
  postgres:
    environment:
      - POSTGRES_SSL_MODE=require
    volumes:
      - postgres_data:/var/lib/postgresql/data:Z
```

### **Compliance Monitoring**

#### **Health Checks**
- **Security Status**: Regular security configuration validation
- **Encryption Status**: Verify all data encryption is active
- **Access Control**: Validate user permissions and access controls
- **Audit Integrity**: Verify audit log completeness and integrity

#### **Compliance Reports**
- **Access Reports**: Who accessed what PHI and when
- **Security Incidents**: Failed login attempts and security violations
- **Data Retention**: PHI retention and deletion compliance
- **Vendor Compliance**: Third-party service compliance status

### **HIPAA Checklist**

- ✅ **Administrative Safeguards**: Access control, audit controls, training
- ✅ **Physical Safeguards**: Secure hosting, environmental controls
- ✅ **Technical Safeguards**: Encryption, access control, audit logs
- ✅ **Risk Assessment**: Regular security risk assessments
- ✅ **Business Associate Agreements**: All third-party services covered
- ✅ **Breach Notification**: Automated incident response procedures
- ✅ **Employee Training**: Security awareness and HIPAA training programs
- ✅ **Data Backup**: Secure, encrypted backup procedures
- ✅ **Disaster Recovery**: Business continuity and data recovery plans

## 🔧 Enhanced API Endpoints

### Document Management
- `POST /upload` - Upload PDF document with HIPAA audit logging
- `GET /documents` - List all documents with access control
- `GET /documents/{id}` - Get document details with PHI access logging
- `GET /documents/{id}/review` - Get document for review interface

### Field Management (New)
- `GET /fields` - Get all active field definitions
- `POST /fields` - Create new field definition
- `PUT /fields/{id}` - Update field definition
- `DELETE /fields/{id}` - Deactivate field definition

### Human Feedback & RL (New)
- `POST /documents/{id}/feedback` - Submit individual human feedback
- `POST /documents/{id}/review/complete` - Complete review with batch feedback
- `GET /analytics/model-performance` - Get model performance metrics
- `GET /analytics/feedback-data` - Get human feedback data for analysis

### Configuration
- `GET /config/llm-providers` - Get available LLM providers and models
- `GET /health` - Health check endpoint with security status

### Interactive API Documentation
Visit http://localhost:8000/docs for complete Swagger documentation with authentication.

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/doc_extraction` |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key | - |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `DEFAULT_LLM_PROVIDER` | Default LLM provider | `anthropic` |
| `DEFAULT_LLM_MODEL` | Default LLM model | `claude-3-sonnet-20240229` |
| `OCR_ENGINE` | OCR engine to use | `tesseract` |
| `MIN_CONFIDENCE_THRESHOLD` | Minimum confidence for auto-approval | `0.7` |
| `REQUIRED_FIELDS_THRESHOLD` | Minimum confidence for required fields | `0.8` |
| `MAX_FILE_SIZE` | Maximum upload file size (bytes) | `50000000` |

### LLM Provider Configuration

#### Anthropic Claude
```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
DEFAULT_LLM_MODEL=claude-3-sonnet-20240229
```

#### OpenAI GPT
```bash
OPENAI_API_KEY=sk-...
DEFAULT_LLM_MODEL=gpt-4-turbo-preview
```

## 🐳 Docker Deployment

### Production Deployment

1. **Prepare environment**:
   ```bash
   cp .env.example .env
   # Configure production values
   ```

2. **Deploy with Docker Compose**:
   ```bash
   docker-compose -f docker-compose.yml up -d
   ```

3. **Scale services** (optional):
   ```bash
   docker-compose up -d --scale backend=3
   ```

### Health Checks
- Backend: `GET /health`
- Database: Automatic health checks in Docker Compose
- Frontend: Nginx serves static files with health monitoring

## 🔍 Monitoring & Troubleshooting

### Logs
```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f postgres
```

### Common Issues

1. **OCR Processing Fails**:
   - Ensure Tesseract is installed and accessible
   - Check file permissions for upload directory
   - Verify PDF file is not corrupted

2. **LLM Extraction Fails**:
   - Verify API keys are correctly configured
   - Check API rate limits and quotas
   - Review OCR text quality

3. **Database Connection Issues**:
   - Ensure PostgreSQL is running
   - Verify database credentials
   - Check network connectivity

## 🧪 Testing

### Backend Tests
```bash
cd backend
python -m pytest tests/ -v
```

### Frontend Tests
```bash
cd frontend
npm test
```

### Integration Tests
```bash
# Test full pipeline with sample document
curl -X POST "http://localhost:8000/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@sample_document.pdf"
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make changes and add tests
4. Commit changes: `git commit -am 'Add new feature'`
5. Push to branch: `git push origin feature/new-feature`
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the troubleshooting section above
- Review API documentation at `/docs`

## 🔄 Enhanced Workflow Overview

```
Secure Upload → OCR Processing → Configurable Field Extraction →
RL-Enhanced Confidence Analysis → Auto-Approve OR Human Review →
Feedback Capture → Performance Tracking → HIPAA-Compliant Storage
```

1. **Secure Upload**: HIPAA-compliant PDF upload with encryption and audit logging
2. **OCR Processing**: Text extraction with secure processing and data handling
3. **Configurable Extraction**: Dynamic field extraction based on configurable definitions
4. **RL-Enhanced Analysis**: Confidence scoring improved by reinforcement learning
5. **Human Review**: Interactive review interface with automatic feedback capture
6. **Performance Tracking**: Model performance analytics and improvement metrics
7. **Compliant Storage**: Encrypted storage with comprehensive audit trails

### **Key Enhancements**:
- **Dynamic Fields**: No hardcoded fields - everything configurable through UI
- **Learning Loop**: Human corrections automatically improve future performance
- **HIPAA Compliance**: Full healthcare data protection and audit requirements
- **Real-time Analytics**: Performance tracking and model improvement metrics