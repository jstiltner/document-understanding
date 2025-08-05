#!/bin/bash

# Development Environment Setup Script
# This script sets up the complete development environment for the Document Understanding API

set -e  # Exit on any error

echo "🚀 Setting up Document Understanding API Development Environment"
echo "=============================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on Windows (Git Bash/WSL)
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    print_status "Detected Windows environment"
    IS_WINDOWS=true
else
    IS_WINDOWS=false
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
print_status "Checking prerequisites..."

# Check Python
if command_exists python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python found: $PYTHON_VERSION"
    PYTHON_CMD="python3"
elif command_exists python; then
    PYTHON_VERSION=$(python --version | cut -d' ' -f2)
    print_success "Python found: $PYTHON_VERSION"
    PYTHON_CMD="python"
else
    print_error "Python not found. Please install Python 3.8 or higher."
    exit 1
fi

# Check Node.js
if command_exists node; then
    NODE_VERSION=$(node --version)
    print_success "Node.js found: $NODE_VERSION"
else
    print_error "Node.js not found. Please install Node.js 16 or higher."
    exit 1
fi

# Check npm
if command_exists npm; then
    NPM_VERSION=$(npm --version)
    print_success "npm found: $NPM_VERSION"
else
    print_error "npm not found. Please install npm."
    exit 1
fi

# Check Docker
if command_exists docker; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
    print_success "Docker found: $DOCKER_VERSION"
    HAS_DOCKER=true
else
    print_warning "Docker not found. Some features may not be available."
    HAS_DOCKER=false
fi

# Check Docker Compose
if command_exists docker-compose; then
    COMPOSE_VERSION=$(docker-compose --version | cut -d' ' -f3 | cut -d',' -f1)
    print_success "Docker Compose found: $COMPOSE_VERSION"
    HAS_COMPOSE=true
else
    print_warning "Docker Compose not found. Using docker compose instead."
    HAS_COMPOSE=false
fi

print_status "All prerequisites checked!"
echo ""

# Create virtual environment
print_status "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    $PYTHON_CMD -m venv venv
    print_success "Virtual environment created"
else
    print_warning "Virtual environment already exists"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
if [ "$IS_WINDOWS" = true ]; then
    source venv/Scripts/activate
else
    source venv/bin/activate
fi
print_success "Virtual environment activated"

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
print_status "Installing Python dependencies..."
if [ -f "backend/requirements.txt" ]; then
    pip install -r backend/requirements.txt
    print_success "Python dependencies installed"
else
    print_warning "requirements.txt not found, installing basic dependencies..."
    pip install fastapi uvicorn sqlalchemy psycopg2-binary alembic python-multipart python-jose[cryptography] passlib[bcrypt] python-dotenv anthropic openai redis celery flower pytest pytest-asyncio httpx
fi

# Install frontend dependencies
print_status "Installing frontend dependencies..."
if [ -d "frontend" ]; then
    cd frontend
    npm install
    print_success "Frontend dependencies installed"
    cd ..
else
    print_warning "Frontend directory not found"
fi

# Create .env file if it doesn't exist
print_status "Setting up environment configuration..."
if [ ! -f ".env" ]; then
    cat > .env << EOF
# Development Environment Configuration
DEVELOPMENT_MODE=true

# Database Configuration
DATABASE_URL=postgresql://postgres:password@localhost:5432/doc_understanding

# Redis Configuration (optional for development)
REDIS_URL=redis://localhost:6379/0

# LLM Provider API Keys (add your keys here)
ANTHROPIC_API_KEY=your_anthropic_key_here
OPENAI_API_KEY=your_openai_key_here

# Azure OpenAI Configuration (optional)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_azure_openai_key_here
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_GPT4_DEPLOYMENT=gpt-4
AZURE_OPENAI_GPT35_DEPLOYMENT=gpt-35-turbo
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002

# Azure Entra ID Configuration (optional)
AZURE_CLIENT_ID=your_client_id_here
AZURE_CLIENT_SECRET=your_client_secret_here
AZURE_TENANT_ID=your_tenant_id_here

# Security Configuration
SECRET_KEY=your-secret-key-for-development-only
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Default LLM Configuration
DEFAULT_LLM_PROVIDER=anthropic
DEFAULT_LLM_MODEL=claude-3-sonnet-20240229

# Confidence Thresholds
MIN_CONFIDENCE_THRESHOLD=0.7
REQUIRED_FIELDS_THRESHOLD=0.8

# File Upload Configuration
MAX_FILE_SIZE=52428800
UPLOAD_DIR=./uploads

# Logging Configuration
LOG_LEVEL=INFO
EOF
    print_success "Environment file created (.env)"
    print_warning "Please update the API keys in .env file before running the application"
else
    print_warning ".env file already exists"
fi

# Set up database (if Docker is available)
if [ "$HAS_DOCKER" = true ]; then
    print_status "Setting up development database with Docker..."
    
    # Check if PostgreSQL container is already running
    if docker ps | grep -q postgres; then
        print_warning "PostgreSQL container already running"
    else
        print_status "Starting PostgreSQL container..."
        docker run -d \
            --name doc-understanding-postgres \
            -e POSTGRES_DB=doc_understanding \
            -e POSTGRES_USER=postgres \
            -e POSTGRES_PASSWORD=password \
            -p 5432:5432 \
            postgres:13
        
        print_success "PostgreSQL container started"
        print_status "Waiting for database to be ready..."
        sleep 10
    fi
    
    # Check if Redis container is running
    if docker ps | grep -q redis; then
        print_warning "Redis container already running"
    else
        print_status "Starting Redis container..."
        docker run -d \
            --name doc-understanding-redis \
            -p 6379:6379 \
            redis:7-alpine
        
        print_success "Redis container started"
    fi
else
    print_warning "Docker not available. Please set up PostgreSQL and Redis manually."
    print_warning "PostgreSQL: Create database 'doc_understanding' on localhost:5432"
    print_warning "Redis: Run Redis server on localhost:6379"
fi

# Run database migrations
print_status "Running database migrations..."
cd backend
if command_exists alembic; then
    # Initialize Alembic if not already done
    if [ ! -d "alembic" ]; then
        alembic init alembic
        print_success "Alembic initialized"
    fi
    
    # Run migrations
    alembic upgrade head 2>/dev/null || print_warning "No migrations to run or database not ready"
else
    print_warning "Alembic not found. Database migrations skipped."
fi
cd ..

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p uploads
mkdir -p logs
mkdir -p temp
print_success "Directories created"

# Set up pre-commit hooks (if available)
if command_exists pre-commit; then
    print_status "Setting up pre-commit hooks..."
    pre-commit install
    print_success "Pre-commit hooks installed"
fi

# Create development scripts
print_status "Creating development scripts..."

# Backend start script
cat > scripts/start-backend.sh << 'EOF'
#!/bin/bash
echo "Starting Document Understanding API Backend..."
cd backend
source ../venv/bin/activate 2>/dev/null || source ../venv/Scripts/activate
uvicorn main_v2:app --reload --host 0.0.0.0 --port 8000
EOF

# Frontend start script
cat > scripts/start-frontend.sh << 'EOF'
#!/bin/bash
echo "Starting Document Understanding API Frontend..."
cd frontend
npm start
EOF

# Full stack start script
cat > scripts/start-dev.sh << 'EOF'
#!/bin/bash
echo "Starting full development environment..."

# Start backend in background
echo "Starting backend..."
./scripts/start-backend.sh &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start frontend in background
echo "Starting frontend..."
./scripts/start-frontend.sh &
FRONTEND_PID=$!

echo "Development environment started!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for interrupt
trap "echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID; exit" INT
wait
EOF

# Make scripts executable
chmod +x scripts/*.sh
print_success "Development scripts created"

# Create test script
cat > scripts/run-tests.sh << 'EOF'
#!/bin/bash
echo "Running tests..."
cd backend
source ../venv/bin/activate 2>/dev/null || source ../venv/Scripts/activate

# Run Python tests
echo "Running backend tests..."
pytest tests/ -v

# Run frontend tests if available
if [ -d "../frontend" ]; then
    echo "Running frontend tests..."
    cd ../frontend
    npm test -- --watchAll=false
fi
EOF

chmod +x scripts/run-tests.sh

print_success "Test script created"

echo ""
echo "=============================================================="
print_success "Development environment setup complete!"
echo ""
echo "📋 Next Steps:"
echo "1. Update API keys in .env file"
echo "2. Start the development environment:"
echo "   ./scripts/start-dev.sh"
echo ""
echo "🔗 Development URLs:"
echo "   Backend API: http://localhost:8000"
echo "   Frontend: http://localhost:3000"
echo "   API Documentation: http://localhost:8000/docs"
echo "   Health Check: http://localhost:8000/health"
echo ""
echo "🛠️  Development Commands:"
echo "   Start backend only: ./scripts/start-backend.sh"
echo "   Start frontend only: ./scripts/start-frontend.sh"
echo "   Run tests: ./scripts/run-tests.sh"
echo ""
echo "📚 Documentation:"
echo "   Developer Guide: docs/developer-guide.md"
echo "   README: README.md"
echo ""
print_warning "Remember to set DEVELOPMENT_MODE=true in .env for development features"
echo "=============================================================="