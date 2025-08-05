#!/bin/bash

# Screenshot Setup and Capture Script
# This script installs dependencies and captures screenshots automatically

echo "📸 Setting up screenshot capture..."

# Check if Node.js is available
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is required but not installed."
    exit 1
fi

# Install Puppeteer if not already installed
echo "📦 Installing Puppeteer..."
npm install puppeteer

# Check if services are running
echo "🔍 Checking if services are running..."

# Check backend
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "⚠️  Backend not running. Starting services..."
    echo "Please run: ./scripts/start-dev.sh"
    echo "Then run this script again."
    exit 1
fi

# Check frontend
if ! curl -s http://localhost:3000 > /dev/null; then
    echo "⚠️  Frontend not running. Please ensure both backend and frontend are running."
    echo "Run: ./scripts/start-dev.sh"
    exit 1
fi

echo "✅ Services are running. Capturing screenshots..."

# Run the screenshot capture script
node scripts/capture-screenshots.js

echo "🎉 Screenshot capture completed!"
echo ""
echo "📁 Screenshots have been saved to docs/screenshots/"
echo "🔍 You can now view them in the README.md file"
echo ""
echo "Next steps:"
echo "1. Review the captured screenshots"
echo "2. Replace any placeholder screenshots with actual interface captures if needed"
echo "3. Commit the screenshots to your repository"