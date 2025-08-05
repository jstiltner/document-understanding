@echo off
setlocal enabledelayedexpansion

REM Development Environment Setup Script for Windows
REM This script sets up the complete development environment for the Document Understanding API

echo 🚀 Setting up Document Understanding API Development Environment
echo ==============================================================

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.8 or higher.
    pause
    exit /b 1
) else (
    for /f "tokens=2" %%i in ('python --version') do set PYTHON_VERSION=%%i
    echo [SUCCESS] Python found: !PYTHON_VERSION!
)

REM Check if Node.js is installed
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Please install Node.js 16 or higher.
    pause
    exit /b 1
) else (
    for /f %%i in ('node --version') do set NODE_VERSION=%%i
    echo [SUCCESS] Node.js found: !NODE_VERSION!
)

REM Check if npm is installed
npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] npm not found. Please install npm.
    pause
    exit /b 1
) else (
    for /f %%i in ('npm --version') do set NPM_VERSION=%%i
    echo [SUCCESS] npm found: !NPM_VERSION!
)

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Docker not found. Some features may not be available.
    set HAS_DOCKER=false
) else (
    for /f "tokens=3" %%i in ('docker --version') do set DOCKER_VERSION=%%i
    echo [SUCCESS] Docker found: !DOCKER_VERSION!
    set HAS_DOCKER=true
)

echo [INFO] All prerequisites checked!
echo.

REM Create virtual environment
echo [INFO] Setting up Python virtual environment...
if not exist "venv" (
    python -m venv venv
    echo [SUCCESS] Virtual environment created
) else (
    echo [WARNING] Virtual environment already exists
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip

REM Install Python dependencies
echo [INFO] Installing Python dependencies...
if exist "backend\requirements.txt" (
    pip install -r backend\requirements.txt
    echo [SUCCESS] Python dependencies installed
) else (
    echo [WARNING] requirements.txt not found, installing basic dependencies...
    pip install fastapi uvicorn sqlalchemy psycopg2-binary alembic python-multipart python-jose[cryptography] passlib[bcrypt] python-dotenv anthropic openai redis celery flower pytest pytest-asyncio httpx
)

REM Install frontend dependencies
echo [INFO] Installing frontend dependencies...
if exist "frontend" (
    cd frontend
    npm install
    echo [SUCCESS] Frontend dependencies installed
    cd ..
) else (
    echo [WARNING] Frontend directory not found
)

REM Create .env file if it doesn't exist
echo [INFO] Setting up environment configuration...
if not exist ".env" (
    (
        echo # Development Environment Configuration
        echo DEVELOPMENT_MODE=true
        echo.
        echo # Database Configuration
        echo DATABASE_URL=postgresql://postgres:password@localhost:5432/doc_understanding
        echo.
        echo # Redis Configuration ^(optional for development^)
        echo REDIS_URL=redis://localhost:6379/0
        echo.
        echo # LLM Provider API Keys ^(add your keys here^)
        echo ANTHROPIC_API_KEY=your_anthropic_key_here
        echo OPENAI_API_KEY=your_openai_key_here
        echo.
        echo # Azure OpenAI Configuration ^(optional^)
        echo AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
        echo AZURE_OPENAI_API_KEY=your_azure_openai_key_here
        echo AZURE_OPENAI_API_VERSION=2024-02-15-preview
        echo AZURE_OPENAI_GPT4_DEPLOYMENT=gpt-4
        echo AZURE_OPENAI_GPT35_DEPLOYMENT=gpt-35-turbo
        echo AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002
        echo.
        echo # Azure Entra ID Configuration ^(optional^)
        echo AZURE_CLIENT_ID=your_client_id_here
        echo AZURE_CLIENT_SECRET=your_client_secret_here
        echo AZURE_TENANT_ID=your_tenant_id_here
        echo.
        echo # Security Configuration
        echo SECRET_KEY=your-secret-key-for-development-only
        echo ALGORITHM=HS256
        echo ACCESS_TOKEN_EXPIRE_MINUTES=30
        echo.
        echo # CORS Configuration
        echo ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
        echo.
        echo # Default LLM Configuration
        echo DEFAULT_LLM_PROVIDER=anthropic
        echo DEFAULT_LLM_MODEL=claude-3-sonnet-20240229
        echo.
        echo # Confidence Thresholds
        echo MIN_CONFIDENCE_THRESHOLD=0.7
        echo REQUIRED_FIELDS_THRESHOLD=0.8
        echo.
        echo # File Upload Configuration
        echo MAX_FILE_SIZE=52428800
        echo UPLOAD_DIR=./uploads
        echo.
        echo # Logging Configuration
        echo LOG_LEVEL=INFO
    ) > .env
    echo [SUCCESS] Environment file created ^(.env^)
    echo [WARNING] Please update the API keys in .env file before running the application
) else (
    echo [WARNING] .env file already exists
)

REM Set up database (if Docker is available)
if "!HAS_DOCKER!"=="true" (
    echo [INFO] Setting up development database with Docker...
    
    REM Check if PostgreSQL container is already running
    docker ps | findstr postgres >nul 2>&1
    if %errorlevel% neq 0 (
        echo [INFO] Starting PostgreSQL container...
        docker run -d --name doc-understanding-postgres -e POSTGRES_DB=doc_understanding -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=password -p 5432:5432 postgres:13
        echo [SUCCESS] PostgreSQL container started
        echo [INFO] Waiting for database to be ready...
        timeout /t 10 /nobreak >nul
    ) else (
        echo [WARNING] PostgreSQL container already running
    )
    
    REM Check if Redis container is running
    docker ps | findstr redis >nul 2>&1
    if %errorlevel% neq 0 (
        echo [INFO] Starting Redis container...
        docker run -d --name doc-understanding-redis -p 6379:6379 redis:7-alpine
        echo [SUCCESS] Redis container started
    ) else (
        echo [WARNING] Redis container already running
    )
) else (
    echo [WARNING] Docker not available. Please set up PostgreSQL and Redis manually.
    echo [WARNING] PostgreSQL: Create database 'doc_understanding' on localhost:5432
    echo [WARNING] Redis: Run Redis server on localhost:6379
)

REM Create necessary directories
echo [INFO] Creating necessary directories...
if not exist "uploads" mkdir uploads
if not exist "logs" mkdir logs
if not exist "temp" mkdir temp
echo [SUCCESS] Directories created

REM Create development scripts
echo [INFO] Creating development scripts...

REM Backend start script
(
    echo @echo off
    echo echo Starting Document Understanding API Backend...
    echo cd backend
    echo call ..\venv\Scripts\activate.bat
    echo uvicorn main_v2:app --reload --host 0.0.0.0 --port 8000
) > scripts\start-backend.bat

REM Frontend start script
(
    echo @echo off
    echo echo Starting Document Understanding API Frontend...
    echo cd frontend
    echo npm start
) > scripts\start-frontend.bat

REM Test script
(
    echo @echo off
    echo echo Running tests...
    echo cd backend
    echo call ..\venv\Scripts\activate.bat
    echo echo Running backend tests...
    echo pytest tests/ -v
    echo if exist "..\frontend" ^(
    echo     echo Running frontend tests...
    echo     cd ..\frontend
    echo     npm test -- --watchAll=false
    echo ^)
) > scripts\run-tests.bat

echo [SUCCESS] Development scripts created

echo.
echo ==============================================================
echo [SUCCESS] Development environment setup complete!
echo.
echo 📋 Next Steps:
echo 1. Update API keys in .env file
echo 2. Start the development environment:
echo    scripts\start-backend.bat ^(in one terminal^)
echo    scripts\start-frontend.bat ^(in another terminal^)
echo.
echo 🔗 Development URLs:
echo    Backend API: http://localhost:8000
echo    Frontend: http://localhost:3000
echo    API Documentation: http://localhost:8000/docs
echo    Health Check: http://localhost:8000/health
echo.
echo 🛠️  Development Commands:
echo    Start backend: scripts\start-backend.bat
echo    Start frontend: scripts\start-frontend.bat
echo    Run tests: scripts\run-tests.bat
echo.
echo 📚 Documentation:
echo    Developer Guide: docs\developer-guide.md
echo    README: README.md
echo.
echo [WARNING] Remember to set DEVELOPMENT_MODE=true in .env for development features
echo ==============================================================

pause