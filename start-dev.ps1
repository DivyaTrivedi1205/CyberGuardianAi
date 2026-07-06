# Start frontend and backend dev servers in separate PowerShell windows (Windows)

# Start frontend
Start-Process powershell -ArgumentList "-NoExit","-Command","cd $PSScriptRoot\frontend; npm install; npm run dev"

# Start backend
Start-Process powershell -ArgumentList "-NoExit","-Command","cd $PSScriptRoot\backend; python -m venv venv; .\venv\Scripts\Activate; pip install -r ..\requirements.txt; uvicorn main:app --reload --port 8000"

Write-Host "Started frontend and backend in new PowerShell windows."
