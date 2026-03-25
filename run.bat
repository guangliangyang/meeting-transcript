@echo off
echo Starting Meeting Assistant...
cd /d "%~dp0"
call .venv\Scripts\activate
python main.py
pause
