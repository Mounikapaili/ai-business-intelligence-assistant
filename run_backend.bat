@echo off
echo Starting AI Business Intelligence Assistant Backend...
call .venv\Scripts\activate.bat
uvicorn app.main:app --port 8000 --reload
pause
