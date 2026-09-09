@echo off
echo Starting Meeting Assistant...
cd /d "%~dp0"
rem UTF-8 so Chinese translations render. main() also sets this in code, which is
rem what covers the frozen exe; PYTHONUTF8 additionally covers redirected output.
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
call .venv\Scripts\activate
python main.py
pause
