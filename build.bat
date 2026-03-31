@echo off
echo ========================================
echo Building Meeting Assistant for Windows
echo ========================================
echo.

REM Activate virtual environment if exists
if exist .venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
)

REM Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

REM Clean previous builds
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Run PyInstaller
echo.
echo Running PyInstaller...
pyinstaller meeting-assistant.spec --noconfirm

REM Create output directory in dist
echo.
echo Creating output directory...
if not exist dist\meeting-assistant\output mkdir dist\meeting-assistant\output

REM Copy .env.example if not already there
if not exist dist\meeting-assistant\.env.example (
    copy .env.example dist\meeting-assistant\.env.example
)

REM Copy prompts.yaml
copy prompts.yaml dist\meeting-assistant\prompts.yaml

REM Create a readme for the release
echo.
echo Creating release readme...
(
echo # Meeting Assistant - Windows Release
echo.
echo ## Quick Start
echo.
echo 1. Copy `.env.example` to `.env`
echo 2. Edit `.env` and add your Gemini API key:
echo    ```
echo    GEMINI_API_KEY=your_api_key_here
echo    ```
echo 3. Run `meeting-assistant.exe`
echo.
echo ## Hotkeys
echo.
echo - **Ctrl+Space**: Get AI dev advice
echo - **Ctrl+Q**: End meeting and generate summary
echo - **Esc**: Exit application
echo.
echo ## Requirements
echo.
echo - Windows 10/11 with Live Captions support
echo - Press Win+Ctrl+L to open Windows Live Captions
echo.
echo ## Output
echo.
echo Meeting summaries are saved in the `output/` folder.
echo.
echo ## Get API Key
echo.
echo Get your Gemini API key from: https://aistudio.google.com/apikey
) > dist\meeting-assistant\README.txt

echo.
echo ========================================
echo Build complete!
echo.
echo Output: dist\meeting-assistant\
echo ========================================
echo.
echo Next steps:
echo 1. Go to dist\meeting-assistant\
echo 2. Copy .env.example to .env
echo 3. Add your GEMINI_API_KEY to .env
echo 4. Run meeting-assistant.exe
echo.
pause
