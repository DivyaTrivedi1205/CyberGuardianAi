@echo off

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "BACKEND_DIR=%SCRIPT_DIR%backend"
set "FRONTEND_DIR=%SCRIPT_DIR%frontend"

echo Starting CyberGuardian AI Backend...
start cmd /k "cd /d "%BACKEND_DIR%" && call venv\Scripts\activate.bat && uvicorn main:app --reload --port 8000"

timeout /t 5 >nul

echo Starting CyberGuardian AI Frontend...
start cmd /k "cd /d "%FRONTEND_DIR%" && npm run dev"

echo.
echo CyberGuardian AI is starting...
echo.
echo Backend: http://127.0.0.1:8000
echo Frontend: http://localhost:5173 (or as displayed by Vite)
echo.
echo Make sure CYBERGUARDIAN_DATABASE_URL is set in your environment.
pause
