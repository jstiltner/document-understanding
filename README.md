# Document Extraction Pipeline

An end-to-end document extraction pipeline for scanned insurance authorization/denial PDFs with OCR, LLM-powered field extraction, and review workflows.

## 🚀 Features

- **PDF Upload**: Web interface and REST API endpoints for document upload
- **OCR Processing**: Tesseract and EasyOCR support for text extraction from scanned PDFs
- **LLM Field Extraction**: Configurable LLM integration (Claude 4, GPT-4) for structured data extraction
- **Review Workflow**: Interactive UI for reviewing and correcting low-confidence extractions
- **Real-time Monitoring**: Dashboard with processing metrics and document status tracking
- **Audit Logging**: Complete audit trail for all document processing activities
- **Configuration Management**: Web-based configuration for LLM providers and processing settings

## 🏗️ Architecture

- **Backend**: Python FastAPI with SQLAlchemy ORM
- **Frontend**: React with TypeScript and Bootstrap
- **Database**: PostgreSQL with comprehensive audit logging
- **OCR**: Tesseract OCR and EasyOCR support
- **LLM**: Configurable providers (Anthropic Claude, OpenAI GPT)
- **Deployment**: Docker Compose for easy deployment

## 📋 Extracted Fields

### Required Fields (must be present for successful processing):
- Facility
- Reference Number
- Patient Last Name
- Patient First Name
- Member ID
- Date of Birth
- Denial Reason

### Optional Fields:
- Payer
- Authorization Number
- Account Number
- Working DRG
- 3rd party reviewer
- Level of Care
- Service
- Clinical Care Guidelines
- Provider TIN
- Case Manager
- Peer to Peer email
- Peer to Peer phone
- Peer to peer fax

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

## 🔧 API Endpoints

### Document Management
- `POST /upload` - Upload PDF document
- `GET /documents` - List all documents
- `GET /documents/{id}` - Get document details
- `GET /documents/{id}/review` - Get document for review

### Configuration
- `GET /config/llm-providers` - Get available LLM providers
- `GET /health` - Health check endpoint

### Interactive API Documentation
Visit http://localhost:8000/docs for complete Swagger documentation.

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

## 🔄 Workflow Overview

```
PDF Upload → OCR Processing → Text Preprocessing → LLM Extraction →
Confidence Analysis → Auto-Approve OR Manual Review → Database Storage
```

1. **Upload**: PDF documents uploaded via web interface or API
2. **OCR**: Text extraction using Tesseract or EasyOCR
3. **Preprocessing**: Text cleaning and chunking for optimal LLM processing
4. **Extraction**: LLM-powered field extraction with confidence scoring
5. **Review**: Low-confidence extractions routed to manual review interface
6. **Storage**: Results stored in PostgreSQL with complete audit trail