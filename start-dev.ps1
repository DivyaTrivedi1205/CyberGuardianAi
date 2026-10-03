# Start frontend and backend dev servers in separate PowerShell windows (Windows)
# This script uses relative paths based on the script's location

# Get the directory where this script is located
$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendPath = Join-Path $ScriptRoot "backend"
$FrontendPath = Join-Path $ScriptRoot "frontend"

# Start frontend
Start-Process powershell -ArgumentList "-NoExit","-Command",
    "cd '$FrontendPath'; npm run dev"

# Start backend
Start-Process powershell -ArgumentList "-NoExit","-Command",
    "cd '$BackendPath'; uvicorn main:app --reload --port 8000"

Write-Host "CyberGuardian AI starting in new PowerShell windows..."
Write-Host "Backend: http://127.0.0.1:8000"
Write-Host "Frontend: http://localhost:5173 (or as displayed by Vite)"
Write-Host ""
Write-Host "Make sure CYBERGUARDIAN_DATABASE_URL is set in your environment."
