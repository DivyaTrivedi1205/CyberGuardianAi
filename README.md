# CyberGuardian AI

An Explainable Cyber Risk Assessment Platform using Machine Learning, Scam Psychology Analysis, Threat Intelligence, and Community Intelligence.

## Project Overview

CyberGuardian AI is an AI-powered cybersecurity platform designed to help users identify, understand, and mitigate digital threats through explainable risk assessment.

Unlike traditional security tools that provide simple safe or unsafe classifications, CyberGuardian AI combines Machine Learning, Rule-Based Analysis, Threat Intelligence, Community Reputation, and Scam Psychology Analysis to generate transparent and actionable security insights.

The platform analyzes URLs, emails, SMS messages, and other digital content to detect phishing attempts, malicious links, social engineering attacks, and suspicious activities. Every assessment is accompanied by detailed explanations so users understand why a threat was flagged and how they can respond safely.

## Vision

To build an intelligent and explainable cybersecurity platform that helps users make safer digital decisions through AI-driven threat analysis and community-powered intelligence.

## Technology Stack

- Frontend: React, Vite, Tailwind CSS
- Backend: FastAPI (Python)
- Database: PostgreSQL for auth/session storage and server-side records
- ML: Scikit-learn, XGBoost, Pandas, NumPy

---

See `docs/` for architecture, API design, and roadmap.

## Development — Quick Start

Verify tools:

```powershell
node -v
npm -v
python --version
pip --version
psql --version
```

Start both services (Windows PowerShell):

```powershell
.\start-dev.ps1
```

Or run services individually:

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Backend:

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r ../requirements.txt
set CYBERGUARDIAN_DATABASE_URL=postgresql://postgres:password@localhost:5432/cyberguardian
uvicorn main:app --reload
```

Open the frontend at the URL shown by Vite (usually http://localhost:5173) and the backend at `http://127.0.0.1:8000`.

