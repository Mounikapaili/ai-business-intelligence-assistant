@echo off
echo Running AI Business Intelligence Assistant Automated Test Suite...
call .venv\Scripts\activate.bat
pytest -v
pause
