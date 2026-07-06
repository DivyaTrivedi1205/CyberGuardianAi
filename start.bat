@echo off

echo Starting Backend...
start cmd /k "cd /d C:\CyberGuardianAi\backend && call venv\Scripts\activate.bat && set CYBERGUARDIAN_DATABASE_URL=postgresql://postgres:9898123@localhost:5432/cyberguardian && uvicorn main:app --reload --port 8000"

timeout /t 5 >nul

echo Starting Frontend...
start cmd /k "cd /d C:\CyberGuardianAi\frontend && npm run dev"

echo.
echo Backend and Frontend are starting...
pause