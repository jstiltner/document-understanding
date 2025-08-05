@echo off
echo Starting Document Understanding API Backend...
cd backend
call ..\venv\Scripts\activate.bat
uvicorn main_v2:app --reload --host 0.0.0.0 --port 8000