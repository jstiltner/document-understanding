@echo off
setlocal enabledelayedexpansion

REM Screenshot Setup and Capture Script for Windows
REM This script installs dependencies and captures screenshots automatically

echo 📸 Setting up screenshot capture...

REM Check if Node.js is available
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Node.js is required but not installed.
    pause
    exit /b 1
)

REM Install Puppeteer if not already installed
echo 📦 Installing Puppeteer...
npm install puppeteer

REM Check if services are running
echo 🔍 Checking if services are running...

REM Check backend
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Backend not running. Starting services...
    echo Please run: scripts\start-backend.bat
    echo Then run this script again.
    pause
    exit /b 1
)

REM Check frontend
curl -s http://localhost:3000 >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  Frontend not running. Please ensure both backend and frontend are running.
    echo Run backend: scripts\start-backend.bat
    echo Run frontend: scripts\start-frontend.bat
    pause
    exit /b 1
)

echo ✅ Services are running. Capturing screenshots...

REM Run the screenshot capture script
node scripts\capture-screenshots.js

echo 🎉 Screenshot capture completed!
echo.
echo 📁 Screenshots have been saved to docs\screenshots\
echo 🔍 You can now view them in the README.md file
echo.
echo Next steps:
echo 1. Review the captured screenshots
echo 2. Replace any placeholder screenshots with actual interface captures if needed
echo 3. Commit the screenshots to your repository

pause