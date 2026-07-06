# Backend — CyberGuardian AI

This is a FastAPI backend.

Current auth storage uses PostgreSQL via `CYBERGUARDIAN_DATABASE_URL`.

Setup (Windows PowerShell):

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r ../requirements.txt
set CYBERGUARDIAN_DATABASE_URL=postgresql://postgres:password@localhost:5432/cyberguardian
uvicorn main:app --reload
```

API entrypoint: `main.py` (root path returns a health message).
