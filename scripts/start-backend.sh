#!/bin/bash
echo "Starting Document Understanding API Backend..."
cd backend
source ../venv/bin/activate 2>/dev/null || source ../venv/Scripts/activate
uvicorn main_v2:app --reload --host 0.0.0.0 --port 8000