# PROJECT CONTEXT / HANDOFF DOCUMENT — CyberGuardian AI

> **Generated:** 2026-10-01 · **Workspace:** `c:\Users\DIVYA\OneDrive\Desktop\Desktopp\CyberGuardian`

---

## 1. PROJECT OVERVIEW

### Short Explanation

CyberGuardian AI is a full-stack cybersecurity platform that uses Machine Learning and heuristic analysis to help everyday users detect phishing URLs, spam/scam messages, deepfake images/videos, and weak passwords. It provides explainable risk assessments — not just safe/unsafe labels, but detailed reasons *why* something was flagged — along with scam psychology analysis and a community-powered threat intelligence feed called "CrowdShield."

### Detailed Explanation

**What it is:** A React + FastAPI web application with a dark enterprise security dashboard UI. Users sign in via Google OAuth or email/phone OTP, then access multiple security analysis tools.

**Problem it solves:** Traditional security tools give opaque "malicious/safe" verdicts. CyberGuardian explains *why* something is risky using human-readable feedback covering technical indicators, psychological manipulation tactics, and community reputation data.

**Intended for:** General consumers, students, and non-technical users who want to verify if a URL, message, image, or password is safe before interacting with it. Also positioned as an academic/portfolio project demonstrating explainable AI in cybersecurity.

**Main features (6 total):**

| # | Feature | Status |
|---|---------|--------|
| 1 | Authentication (OTP + Google OAuth) | ✅ Implemented |
| 2 | Password Strength Analyzer | ✅ Implemented |
| 3 | URL Phishing Analyzer (XGBoost ML) | ✅ Implemented |
| 4 | Message/SMS Spam Analyzer (TF-IDF + LR) | ✅ Implemented |
| 5 | Deepfake Image/Video Analyzer (CNN + forensics) | ✅ Implemented |
| 6 | CrowdShield Community Intelligence Feed | ✅ Implemented |
| — | Scam Psychology Engine (cross-feature) | ✅ Implemented |
| — | Scan History per user | ✅ Implemented |

**Current status:** All 6 planned phases from the roadmap are implemented. The project is feature-complete for its MVP scope but has not been deployed to production. It runs locally on Windows with a PostgreSQL database.

**What is missing/incomplete:**
- No production deployment (Phase 6 in roadmap)
- No email delivery system configured (OTP emails are simulated to terminal)
- No phone SMS delivery (simulated to terminal)
- Email dataset placeholder exists but no email-specific analyzer is implemented
- The deepfake CNN model trains on synthetic data, not real deepfakes
- No rate limiting, CAPTCHA, or abuse prevention
- CORS is wide-open (`allow_origins=["*"]`)
- JWT secret is hardcoded as a fallback default

---

## 2. COMPLETE PROJECT STRUCTURE

```
CyberGuardian/
├── .claude/                          # Claude Code configuration
│   └── settings.local.json           # Permissions for Claude Code
├── .git/                             # Git repository
├── .gitignore                        # Git ignore rules
├── LICENSE                           # MIT License
├── README.md                         # Project overview & quick start
├── requirements.txt                  # Python dependencies (root-level)
├── schema.sql                        # Reference SQL schema
├── start-dev.ps1                     # PowerShell dev launcher (both services)
├── start.bat                         # Batch dev launcher (hardcoded paths)
├── client_secret_*.json              # ⚠️ Google OAuth client secret (COMMITTED!)
│
├── backend/                          # FastAPI Python backend
│   ├── .env                          # Environment variables (DB URL)
│   ├── README.md                     # Backend setup docs
│   ├── main.py                       # ★ FastAPI entry point
│   ├── train_models.py               # ML model training script
│   ├── test_deepfake.py              # Deepfake analyzer tests
│   ├── test_local.py                 # Local integration tests
│   ├── test_pipeline.py              # Pipeline integration tests
│   ├── cyberguardian.db              # SQLite leftover (not actively used)
│   ├── venv/                         # Python virtual environment (ignored)
│   ├── __pycache__/                  # Python bytecode cache
│   │
│   ├── app/
│   │   └── __init__.py               # Empty app package
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   └── connection.py             # ★ DB connection, schema init
│   │
│   ├── models/                       # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── auth.py                   # Auth-related Pydantic models
│   │   ├── security.py               # Password analysis models
│   │   └── security_schemas.py       # URL, Message, Deepfake models
│   │
│   ├── routes/                       # FastAPI route handlers
│   │   ├── __init__.py
│   │   ├── auth.py                   # ★ Auth endpoints (OTP, Google, JWT)
│   │   ├── security.py               # ★ All security analysis endpoints
│   │   └── community.py              # CrowdShield endpoints
│   │
│   └── services/                     # Business logic / ML services
│       ├── __init__.py
│       ├── password_service.py       # Password scoring logic
│       ├── url_feature_extractor.py  # ★ 30-feature URL extraction
│       ├── message_analyzer.py       # Message spam detection
│       ├── scam_psychology.py        # Psychology manipulation engine
│       ├── community_reputation.py   # Community blocklist lookup
│       ├── deepfake_analyzer.py      # ★ Deepfake analysis (CNN + forensics)
│       └── deepfake_model.py         # ★ CNN architecture + training
│
├── frontend/                         # React + Vite frontend
│   ├── README.md
│   ├── package.json                  # NPM config
│   ├── package-lock.json             # Lock file
│   ├── index.html                    # HTML entry (loads Google GSI script)
│   ├── node_modules/                 # NPM packages (ignored)
│   └── src/
│       ├── main.jsx                  # React entry point
│       ├── App.jsx                   # ★ MONOLITHIC 2044-line component
│       └── index.css                 # ★ Complete CSS design system (1069 lines)
│
├── models/                           # Pre-trained ML model files
│   ├── url_classifier.pkl            # XGBoost URL phishing model (~392KB)
│   ├── message_classifier.pkl        # TF-IDF + LogReg SMS model (~231KB)
│   └── deepfake_cnn.pth             # PyTorch CNN weights (~113KB)
│
├── datasets/                         # Training data
│   ├── README.md
│   ├── urls/
│   │   ├── phishing_websites/        # UCI ARFF phishing dataset
│   │   └── phishing_websites.zip
│   ├── messages/
│   │   ├── smsspam/                  # SMS Spam Collection dataset
│   │   └── smsspam.zip
│   └── emails/
│       └── README.md                 # Placeholder (no data yet)
│
└── docs/                             # Project documentation
    ├── project-overview.md
    ├── architecture.md
    ├── api-design.md
    ├── database-design.md
    ├── ml-pipeline.md
    ├── design-system.md              # Color palette & font spec
    ├── project-roadmap.md            # 6-phase roadmap
    └── phishing_features_reference.md # Academic reference (UCI features)
```

---

## 3. TECHNOLOGY STACK

| Category | Technology | Where Used | Version |
|----------|-----------|-----------|---------|
| **Languages** | Python | Backend, ML training | 3.x |
| | JavaScript (JSX) | Frontend | ES2020+ |
| | SQL | Database schema | PostgreSQL dialect |
| **Frontend Framework** | React | Single-page app | ^18.2.0 |
| **Build Tool** | Vite | Frontend dev server + bundler | ^5.0.0 |
| **Backend Framework** | FastAPI | REST API | (from pip) |
| **ASGI Server** | Uvicorn | Run FastAPI | (from pip) |
| **Database** | PostgreSQL | Users, scans, OTPs, community reports | (external) |
| **DB Driver** | psycopg2-binary | Python → PostgreSQL | (from pip) |
| **Auth - JWT** | python-jose | JWT token creation/verification | (from pip) |
| **Auth - Password Hashing** | passlib[bcrypt] + bcrypt | Password hashing (available but unused for OTP flow) | (from pip) |
| **Auth - Google** | Google Identity Services (GSI) | Frontend Google Sign-In | CDN script |
| **ML - URL Model** | XGBoost | URL phishing classification | (from pip) |
| **ML - Message Model** | scikit-learn (TfidfVectorizer + LogisticRegression) | SMS spam classification | (from pip) |
| **ML - Deepfake Model** | PyTorch (CNN) | Image deepfake detection | (installed, not in requirements.txt) |
| **ML - Deepfake Forensics** | NumPy, SciPy (laplace), PIL | FFT, ELA, noise analysis | (from pip) |
| **ML - Data** | pandas | ARFF/CSV parsing for training | (from pip) |
| **Image Processing** | Pillow (PIL) | Image loading, EXIF, transforms | (from pip) |
| **Environment** | python-dotenv | Load .env files | (from pip) |
| **Styling** | Vanilla CSS | Dark theme design system | N/A |
| **Font** | Inter | Google Fonts (system-ui fallback) | N/A |

### Notable Missing from requirements.txt
- `torch`, `torchvision`, `scipy`, `Pillow` — **required** by the deepfake analyzer but **not listed** in `requirements.txt`
- `python-multipart` — **required** by FastAPI for file uploads but **not listed**

---

## 4. ARCHITECTURE

```
┌─────────────────────────────────────────────────────┐
│                    USER (Browser)                    │
│          http://localhost:5173 (Vite dev)            │
├─────────────────────────────────────────────────────┤
│              React SPA (App.jsx)                     │
│  ┌─────────┬──────────┬──────────┬────────────────┐ │
│  │Dashboard│ Password │ URL Risk │ Message/Deepfake│ │
│  │         │ Analyzer │ Analyzer │ /CrowdShield   │ │
│  └────┬────┴────┬─────┴────┬─────┴───────┬────────┘ │
│       │  HTTP REST (JSON + multipart/form-data)      │
├───────┼─────────┼──────────┼─────────────┼──────────┤
│       ▼         ▼          ▼             ▼          │
│   FastAPI Backend (http://127.0.0.1:8000)           │
│  ┌──────────────────────────────────────────────┐   │
│  │  Routes: /auth, /security, /community         │   │
│  │  ┌────────────────────────────────────────┐   │   │
│  │  │  Services Layer                         │   │   │
│  │  │  ├── password_service.py                │   │   │
│  │  │  ├── url_feature_extractor.py           │   │   │
│  │  │  ├── message_analyzer.py                │   │   │
│  │  │  ├── scam_psychology.py                 │   │   │
│  │  │  ├── deepfake_analyzer.py               │   │   │
│  │  │  ├── deepfake_model.py (CNN)            │   │   │
│  │  │  └── community_reputation.py            │   │   │
│  │  └────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────┘   │
│       │              │             │                 │
│       ▼              ▼             ▼                │
│  ┌─────────┐  ┌────────────┐  ┌──────────────┐     │
│  │PostgreSQL│  │ ML Models  │  │ Google OAuth  │     │
│  │(users,   │  │ (.pkl/.pth)│  │ tokeninfo API │     │
│  │ scans,   │  │ url_clf    │  └──────────────┘     │
│  │ OTPs,    │  │ msg_clf    │                       │
│  │ reports) │  │ deepfake   │                       │
│  └─────────┘  └────────────┘                       │
└─────────────────────────────────────────────────────┘
```

### Data Flow

1. **User** opens frontend at `localhost:5173`
2. **Auth:** User signs up/in via Google OAuth (GSI) or Email/Phone OTP → backend issues JWT
3. **Analysis:** User submits content (password/URL/message/image) → frontend POSTs to backend
4. **Backend** runs ML model inference + heuristic checks + scam psychology analysis + community reputation lookup
5. **Response** returns risk_score, prediction, features, feedback, scam_psychology → frontend renders results
6. **History:** If authenticated, each scan is logged to PostgreSQL; history is fetchable via GET endpoints

---

## 5. HOW THE PROJECT ACTUALLY WORKS

### Startup Sequence

1. **Backend:** `uvicorn main:app --reload --port 8000`
   - `main.py` creates FastAPI app, adds CORS middleware, registers 3 routers (auth, security, community)
   - `@app.on_event("startup")` calls `initialize_database()` → creates all tables in PostgreSQL if not exists
   - ML models are lazy-loaded on first request (global singletons with `_model = None` pattern)

2. **Frontend:** `npm run dev` → Vite serves React app at `localhost:5173`
   - `main.jsx` renders `<App />` into `#root`
   - `App.jsx` (monolithic, 2044 lines) handles all state, routing, and rendering
   - On mount, checks `localStorage` for saved JWT token → calls `/auth/me` to restore session
   - Loads Google GSI script from CDN for OAuth

### User Interaction Flow

1. **Unauthenticated:** User sees auth page with Login/Signup tabs, Google Sign-In button, or "Continue as Guest"
2. **Guest Mode:** Can use Password Analyzer and URL Analyzer without saving history
3. **Authenticated:** Full access to all tools + scan history persistence
4. **Navigation:** Top navbar + sidebar navigate between: Dashboard, Password Analyzer, URL Risk Analyzer, Message Analyzer, Deepfake Analyzer, CrowdShield Feed

### Request Flow (e.g., URL Analysis)

1. User types URL → clicks "Scan"
2. Frontend POSTs `{ url: "..." }` to `/security/analyze-url` with JWT in Authorization header
3. Backend `security.py` route handler:
   a. Checks community reputation (CrowdShield blocklist)
   b. Extracts 30 URL features via `url_feature_extractor.py`
   c. Runs XGBoost model prediction (`url_classifier.pkl`)
   d. Runs scam psychology analysis on URL text
   e. Saves scan to `url_scans` table if user is authenticated
   f. Returns `{ url, risk_score, prediction, features, feedback, scam_psychology }`
4. Frontend renders risk gauge, feature breakdown, feedback explanations, and psychology triggers

---

## 6. EVERY MAJOR FEATURE

### Feature 1: Authentication System

| Aspect | Detail |
|--------|--------|
| **What it does** | OTP-based login/signup (email/phone) + Google OAuth + JWT sessions |
| **Files** | [`routes/auth.py`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/backend/routes/auth.py), [`models/auth.py`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/backend/models/auth.py) |
| **Auth flow** | Request OTP → Verify OTP → Get JWT → Store in localStorage |
| **Google flow** | GSI credential → POST to `/auth/google` → Verify via Google tokeninfo API → JWT |
| **JWT** | HS256, 24h expiry, contains user ID, name, identifier |
| **OTP** | 6-digit random, 10-minute expiry, stored in `otp_challenges` table |
| **Email delivery** | Simulated (prints to terminal) unless SMTP vars are configured |
| **Phone delivery** | Simulated (prints to terminal), no real SMS integration |
| **Status** | ✅ Working (with simulated OTP delivery) |
| **Limitations** | No rate limiting on OTP requests, JWT secret has hardcoded fallback |

### Feature 2: Password Strength Analyzer

| Aspect | Detail |
|--------|--------|
| **What it does** | Scores passwords 0-100 based on length, character diversity, patterns |
| **Files** | [`services/password_service.py`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/backend/services/password_service.py), [`routes/security.py`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/backend/routes/security.py) (endpoint) |
| **Algorithm** | Rule-based scoring: +30 for ≥12 chars, +10 lowercase, +10 uppercase, +15 digits, +15 symbols, -10 repeats, -20 common words |
| **Grades** | Strong (≥80), Moderate (≥55), Weak (≥30), Critical (<30) |
| **Extra features** | Password generator (client-side), suggestions list |
| **Status** | ✅ Working |
| **Limitations** | No dictionary attack check, no breach database (HaveIBeenPwned) integration |

### Feature 3: URL Phishing Analyzer

| Aspect | Detail |
|--------|--------|
| **What it does** | Analyzes URLs for phishing indicators using 30 features + XGBoost ML + community blocklist + scam psychology |
| **Files** | [`services/url_feature_extractor.py`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/backend/services/url_feature_extractor.py), [`routes/security.py`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/backend/routes/security.py) |
| **ML Model** | XGBoost trained on UCI Phishing Websites ARFF dataset (~11K samples) |
| **30 Features** | IP address, URL length, shortener, @, //, prefix-suffix, subdomains, SSL, domain age, port, DNS, favicon, request URL, anchors, meta/script links, SFH, mailto, redirect, mouseover, right-click, popup, iframe, web traffic, PageRank, Google index, links pointing, statistical report |
| **Feature extraction** | Attempts live HTTP fetch (1.5s timeout) to inspect HTML for page-level features; falls back to defaults |
| **Predictions** | Phishing (≥70), Suspicious (≥35), Legitimate (<35) |
| **Status** | ✅ Working |
| **Limitations** | Many features (domain age, traffic, PageRank) use a simple "is_popular" whitelist heuristic instead of actual WHOIS/Alexa lookups |

### Feature 4: Message/SMS Spam Analyzer

| Aspect | Detail |
|--------|--------|
| **What it does** | Analyzes text messages for spam/phishing using TF-IDF + Logistic Regression ML + heuristic keyword checks |
| **Files** | [`services/message_analyzer.py`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/backend/services/message_analyzer.py), [`routes/security.py`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/backend/routes/security.py) |
| **ML Model** | TF-IDF (5000 features, 1-2 ngrams) → Logistic Regression pipeline, trained on SMS Spam Collection dataset (~5.5K samples) |
| **Heuristics** | Urgency words, financial lures, URLs in text, sensitive info requests, callback numbers, excessive caps |
| **Predictions** | Phishing/Spam (≥70), Suspicious (≥35), Legitimate (<35) |
| **Status** | ✅ Working |
| **Limitations** | No email-specific analysis (email dataset placeholder exists), no attachment analysis |

### Feature 5: Deepfake Image/Video Analyzer

| Aspect | Detail |
|--------|--------|
| **What it does** | Analyzes uploaded images/videos for AI-generated content using CNN inference + digital forensics |
| **Files** | [`services/deepfake_analyzer.py`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/backend/services/deepfake_analyzer.py), [`services/deepfake_model.py`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/backend/services/deepfake_model.py) |
| **Image pipeline** | (1) EXIF metadata extraction → (2) Noise inconsistency (Laplacian) → (3) ELA (Error Level Analysis) → (4) FFT spectral analysis → (5) Channel correlations → (6) CNN model inference → (7) AI metadata signature scan |
| **Video pipeline** | Hash-based deterministic scoring + metadata signature scan (no frame-by-frame analysis) |
| **CNN Architecture** | 3-block CNN: Conv2d→BN→ReLU→Pool ×3 → FC(64→32→2) |
| **Training** | Trained on 400 synthetic images (200 real + 200 fake patterns), NOT real deepfakes |
| **Predictions** | AI Generated (≥65), Suspicious (≥35), Authentic (<35) |
| **Status** | ✅ Working but limited accuracy |
| **Limitations** | CNN trained on synthetic data only; video analysis is hash-based mock, not actual frame analysis |

### Feature 6: CrowdShield (Community Intelligence)

| Aspect | Detail |
|--------|--------|
| **What it does** | Community-sourced threat reports — users report suspicious URLs/messages; after 3+ reports, auto-verified as threat |
| **Files** | [`routes/community.py`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/backend/routes/community.py), [`services/community_reputation.py`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/backend/services/community_reputation.py) |
| **Integration** | URL and Message analyzers check community blocklist before ML analysis |
| **Report lifecycle** | pending → verified_threat (at 3 reports or manual verify) |
| **Status** | ✅ Working |
| **Limitations** | No spam protection on reports, anyone can report anything; no admin panel |

### Cross-Feature: Scam Psychology Engine

| Aspect | Detail |
|--------|--------|
| **What it does** | Identifies cognitive manipulation tactics in text: urgency, authority, fear, greed, trust, curiosity |
| **Files** | [`services/scam_psychology.py`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/backend/services/scam_psychology.py) |
| **How it works** | Regex keyword matching against 6 psychology categories, each scored 0-100 based on match count |
| **Output** | Scores per category, cognitive bias name, human-readable explanation, actionable tips |
| **Used by** | URL Analyzer, Message Analyzer |

---

## 7. CODEBASE ANALYSIS

### Entry Points

| Entry Point | File | Purpose |
|-------------|------|---------|
| Backend API | [`backend/main.py`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/backend/main.py) | FastAPI app creation, router registration, DB init |
| Frontend UI | [`frontend/src/main.jsx`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/frontend/src/main.jsx) | React root render |
| Model Training | [`backend/train_models.py`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/backend/train_models.py) | Train all 3 ML models |

### Important Classes

| Class | File | Purpose |
|-------|------|---------|
| `DeepfakeCNN` | `services/deepfake_model.py` | PyTorch CNN (3 conv blocks + classifier) for image deepfake detection |
| `AuthRequest`, `OtpVerifyRequest`, `UserOut`, etc. | `models/auth.py` | Pydantic request/response schemas for auth endpoints |
| `PasswordAnalysisRequest/Response` | `models/security.py` | Pydantic schemas for password analysis |
| `UrlAnalysisRequest/Response`, `MessageAnalysisRequest/Response`, `DeepfakeAnalysisResponse` | `models/security_schemas.py` | Pydantic schemas for all security endpoints |
| `CommunityReportRequest/Response` | `routes/community.py` (inline) | Pydantic schemas for community reports |

### Important Functions

| Function | File | Purpose |
|----------|------|---------|
| `initialize_database()` | `database/connection.py` | Creates all 7 tables on startup |
| `db_connection()` | `database/connection.py` | Context manager for PostgreSQL connections |
| `get_current_user()` | `routes/auth.py` | JWT → UserOut dependency for protected endpoints |
| `get_optional_user()` | `routes/security.py` | Optional auth — allows guest access |
| `score_password()` | `services/password_service.py` | Rule-based password scoring |
| `extract_features_from_url()` | `services/url_feature_extractor.py` | Extracts 30 phishing features from URL |
| `analyze_message_text()` | `services/message_analyzer.py` | ML + heuristic message analysis |
| `analyze_scam_psychology()` | `services/scam_psychology.py` | Psychology trigger detection |
| `analyze_deepfake()` | `services/deepfake_analyzer.py` | Full deepfake analysis pipeline |
| `get_cnn_model()` | `services/deepfake_analyzer.py` | Lazy-loads CNN model (auto-trains if missing) |
| `check_community_reputation()` | `services/community_reputation.py` | Blocklist lookup |
| `train_url_model()` | `train_models.py` | Trains XGBoost on UCI ARFF dataset |
| `train_message_model()` | `train_models.py` | Trains TF-IDF + LogReg on SMS Spam dataset |
| `train_deepfake_model()` | `services/deepfake_model.py` | Trains Random Forest on forensics features |

### Important Constants

| Constant | File | Value |
|----------|------|-------|
| `API_BASE_URL` | `App.jsx` | `http://127.0.0.1:8000` (overridable via `VITE_API_BASE_URL`) |
| `JWT_ALGORITHM` | `routes/auth.py` | `HS256` |
| `ACCESS_TOKEN_EXPIRES_HOURS` | `routes/auth.py` | `24` |
| `OTP_EXPIRES_MINUTES` | `routes/auth.py` | `10` |
| `POPULAR_DOMAINS` | `services/url_feature_extractor.py` | Set of ~36 trusted domains |
| `AI_SIGNATURES` | `services/deepfake_analyzer.py` | List of 14 AI tool byte signatures |
| `PSYCHOLOGY_RULES` | `services/scam_psychology.py` | 6 categories with keyword patterns |

---

## 8. DEPENDENCIES

### Python (`requirements.txt`)

| Package | Purpose | Essential | Notes |
|---------|---------|-----------|-------|
| `fastapi` | Web framework | ✅ Yes | |
| `uvicorn` | ASGI server | ✅ Yes | |
| `python-jose` | JWT encode/decode | ✅ Yes | |
| `passlib[bcrypt]` | Password hashing | ⚠️ Available but unused | Installed but OTP flow doesn't hash passwords |
| `bcrypt` | Bcrypt backend | ⚠️ Available but unused | |
| `psycopg2-binary` | PostgreSQL driver | ✅ Yes | |
| `python-dotenv` | .env file loading | ✅ Yes | |
| `pandas` | Data loading for training | ✅ For training | Not needed at runtime |
| `numpy` | Numerical operations | ✅ Yes | Used by all ML services |
| `scikit-learn` | ML models | ✅ Yes | URL + Message classifiers |
| `xgboost` | URL classifier | ✅ Yes | |

### Missing from requirements.txt (but required at runtime)

| Package | Purpose | Why Missing |
|---------|---------|-------------|
| `torch` | CNN model | Deepfake feature added later |
| `torchvision` | Image transforms | Deepfake feature added later |
| `scipy` | Laplacian filter | Deepfake feature added later |
| `Pillow` | Image I/O | Deepfake feature added later |
| `python-multipart` | File upload parsing | Required by FastAPI for `UploadFile` |

### Frontend (`package.json`)

| Package | Version | Purpose |
|---------|---------|---------|
| `react` | ^18.2.0 | UI library |
| `react-dom` | ^18.2.0 | React DOM renderer |
| `vite` (dev) | ^5.0.0 | Dev server + bundler |

> **Note:** The frontend has zero third-party UI libraries — no router, no state management, no chart library. Everything is custom.

---

## 9. CONFIGURATION AND ENVIRONMENT VARIABLES

### Environment Variables

| Variable | Where Referenced | Required | Default | Purpose |
|----------|-----------------|----------|---------|---------|
| `CYBERGUARDIAN_DATABASE_URL` | `database/connection.py`, `.env` | ✅ Yes | `postgresql://postgres:password@localhost:5432/cyberguardianai` | PostgreSQL connection string |
| `CYBERGUARDIAN_JWT_SECRET` | `routes/auth.py` | ⚠️ Recommended | `cyberguardian-dev-secret` | JWT signing key |
| `GOOGLE_CLIENT_ID` | `routes/auth.py` | No | [HARDCODED VALUE PRESENT] | Google OAuth client ID |
| `CYBERGUARDIAN_SMTP_HOST` | `routes/auth.py` | No | `smtp.gmail.com` | SMTP server for email OTP |
| `CYBERGUARDIAN_SMTP_PORT` | `routes/auth.py` | No | `587` | SMTP port |
| `CYBERGUARDIAN_SMTP_USERNAME` | `routes/auth.py` | No | `""` (empty = simulate) | SMTP login |
| `CYBERGUARDIAN_SMTP_PASSWORD` | `routes/auth.py` | No | `""` (empty = simulate) | SMTP password |
| `CYBERGUARDIAN_SMTP_FROM_NAME` | `routes/auth.py` | No | `CyberGuardian AI` | Email sender name |
| `VITE_API_BASE_URL` | `App.jsx` | No | `http://127.0.0.1:8000` | Backend API URL |

### Configuration Files

| File | Purpose | Contains Secrets? |
|------|---------|-------------------|
| `backend/.env` | DB URL | [CONFIGURED — contains DB password] |
| `client_secret_*.json` | Google OAuth | ⚠️ **YES — client_secret is committed to repo!** |
| `.claude/settings.local.json` | Claude Code permissions | No |

### ⚠️ Security Issues Found

1. **Google OAuth `client_secret` is committed to the repository** in `client_secret_48190723181-*.json`
2. **`start.bat` contains a hardcoded database password** in the connection string
3. **JWT secret has a hardcoded fallback** (`cyberguardian-dev-secret`) if env var is not set
4. **Google Client ID is hardcoded** in both `routes/auth.py` and `App.jsx`

---

## 10. API / NETWORK ANALYSIS

### Internal API Endpoints

#### Auth Router (`/auth`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/auth/request-otp` | None | Send OTP to email/phone |
| POST | `/auth/verify-otp` | None | Verify OTP → return JWT |
| POST | `/auth/google` | None | Verify Google GSI credential → return JWT |
| POST | `/auth/google-demo` | None | Demo Google login (no real OAuth) |
| GET | `/auth/me` | JWT | Get current user profile |

#### Security Router (`/security`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/security/analyze-password` | Optional | Score a password |
| GET | `/security/password-scans` | JWT | Get password scan history |
| POST | `/security/analyze-url` | Optional | Analyze URL for phishing |
| GET | `/security/url-scans` | JWT | Get URL scan history |
| POST | `/security/analyze-message` | Optional | Analyze message for spam |
| GET | `/security/message-scans` | JWT | Get message scan history |
| POST | `/security/analyze-deepfake` | Optional | Analyze file for deepfake (multipart upload) |
| GET | `/security/deepfake-scans` | JWT | Get deepfake scan history |

#### Community Router (`/community`)

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/community/report` | Optional | Submit threat report |
| GET | `/community/reports` | None | List all reports |
| POST | `/community/verify/{report_id}` | JWT | Verify a threat report |

### External API Calls

| Service | URL | Called From | Purpose |
|---------|-----|------------|---------|
| Google OAuth tokeninfo | `https://oauth2.googleapis.com/tokeninfo?id_token=...` | `routes/auth.py` | Verify Google credential |
| Target URL (live fetch) | User-provided URL | `services/url_feature_extractor.py` | Fetch HTML for page-level feature extraction (1.5s timeout) |

### External CDN

| Resource | URL | Loaded By |
|----------|-----|-----------|
| Google Identity Services | `https://accounts.google.com/gsi/client` | `frontend/index.html` |

---

## 11. DATABASE / DATA STORAGE

### Technology
- **PostgreSQL** via `psycopg2-binary` with raw SQL (no ORM)
- Connection string from `CYBERGUARDIAN_DATABASE_URL` environment variable
- Schema auto-created on app startup via `initialize_database()`

### Tables (7 total)

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `users` | User accounts | id (TEXT PK), name, identifier, identifier_type, auth_provider, created_at, updated_at |
| `otp_challenges` | OTP codes for auth | id (BIGSERIAL PK), identifier, purpose, code, expires_at, consumed |
| `password_scans` | Password analysis history | id, user_id (FK), password_length, score, grade, feedback (JSONB) |
| `url_scans` | URL analysis history | id, user_id (FK), url, risk_score, prediction, features (JSONB) |
| `message_scans` | Message analysis history | id, user_id (FK), message, risk_score, prediction, features (JSONB) |
| `deepfake_scans` | Deepfake analysis history | id, user_id (FK), file_name, file_type, risk_score, prediction, features (JSONB) |
| `community_reports` | CrowdShield threat reports | id, user_id, indicator_type, indicator_value (UNIQUE), reports_count, status |

### Relationships
- All scan tables reference `users(id)` with `ON DELETE CASCADE`
- `community_reports.indicator_value` has a UNIQUE index

### Other Data Storage
- `cyberguardian.db` exists in `backend/` but is a SQLite leftover — **not actively used**
- JWT tokens stored in browser `localStorage`
- ML models stored as `.pkl` / `.pth` files in `models/` directory

---

## 12. AI / ML / MODEL CONFIGURATION

### Model 1: URL Phishing Classifier

| Aspect | Detail |
|--------|--------|
| Algorithm | XGBoost (`XGBClassifier`) |
| Training data | UCI Phishing Websites ARFF dataset |
| Features | 30 integer features (-1, 0, 1) |
| Target | 0 = Legitimate, 1 = Phishing |
| Hyperparameters | n_estimators=150, max_depth=6, lr=0.1 |
| Saved as | `models/url_classifier.pkl` (pickle dict: `{model, features}`) |
| Loaded by | `routes/security.py` → `get_url_model()` |

### Model 2: Message Spam Classifier

| Aspect | Detail |
|--------|--------|
| Algorithm | TF-IDF (5000 features, 1-2 ngrams) → Logistic Regression |
| Training data | SMS Spam Collection dataset |
| Target | 0 = Ham (Legitimate), 1 = Spam |
| Hyperparameters | max_iter=1000 |
| Saved as | `models/message_classifier.pkl` (pickle Pipeline) |
| Loaded by | `services/message_analyzer.py` → `get_message_model()` |

### Model 3: Deepfake CNN

| Aspect | Detail |
|--------|--------|
| Architecture | 3-block CNN (Conv→BN→ReLU→Pool) + FC (64→32→2) |
| Training data | 400 synthetically generated images (NOT real deepfakes) |
| Input | 128×128 RGB images, normalized (ImageNet mean/std) |
| Target | 0 = Real, 1 = AI Generated |
| Saved as | `models/deepfake_cnn.pth` (PyTorch state_dict) |
| Loaded by | `services/deepfake_analyzer.py` → `get_cnn_model()` |
| Auto-train | If `.pth` file is missing, auto-trains on startup |

### Additional Model (trained but not loaded at runtime)

| Aspect | Detail |
|--------|--------|
| Algorithm | Random Forest (n_estimators=100, max_depth=8) |
| Purpose | Deepfake detection via forensics features |
| Saved as | `models/deepfake_rf.pkl` |
| **Status** | Trained by `train_deepfake_model()` but **never loaded** — the analyzer uses the CNN instead |

### No LLM/AI API Integration
This project does **not** use any LLM APIs (OpenAI, Claude, etc.) for its functionality. All ML is local model inference.

---

## 13. CLAUDE CODE / ANTIGRAVITY CONFIGURATION

### Claude Code Setup

| Item | Detail |
|------|--------|
| Config file | `.claude/settings.local.json` |
| Permissions | `Bash(python -c ' *)`, `Bash(pip install *)` |
| Provider | OpenRouter (free tier) |
| API key | Set via `ANTHROPIC_API_KEY` user-level environment variable |
| Global settings | `~/.claude/settings.json`: theme=dark-ansi, model=sonnet |

### No MCP, Skills, Rules, Hooks, or Workflows Configured for the Project

---

## 14. RUN / BUILD / INSTALL INSTRUCTIONS

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL running locally
- A database named `cyberguardian` (or `cyberguardianai`)

### Installation

```powershell
# Backend
cd backend
python -m venv venv
.\venv\Scripts\Activate
pip install -r ..\requirements.txt
pip install torch torchvision scipy Pillow python-multipart  # MISSING from requirements.txt

# Frontend
cd ..\frontend
npm install
```

### Configuration

```powershell
# Set database URL (backend\.env or environment variable)
$env:CYBERGUARDIAN_DATABASE_URL = "postgresql://postgres:YOUR_PASSWORD@localhost:5432/cyberguardian"

# Optional: Set JWT secret for production
$env:CYBERGUARDIAN_JWT_SECRET = "your-secret-key"
```

### Development

```powershell
# Option 1: Use the dev script
.\start-dev.ps1

# Option 2: Run separately
# Terminal 1 — Backend
cd backend
.\venv\Scripts\Activate
uvicorn main:app --reload --port 8000

# Terminal 2 — Frontend
cd frontend
npm run dev
```

### Train Models (if models/ files are missing)

```powershell
cd backend
python train_models.py
```

### Build (Production Frontend)

```powershell
cd frontend
npm run build    # outputs to frontend/dist/
npm run preview  # preview production build
```

### Testing

```powershell
cd backend
python test_deepfake.py
python test_local.py
python test_pipeline.py
```

---

## 15. CURRENT STATE

### ✅ Working
- Authentication (OTP + Google OAuth + JWT)
- Password analyzer (scoring + generation + history)
- URL phishing analyzer (feature extraction + XGBoost + explanations)
- Message spam analyzer (TF-IDF + heuristics + explanations)
- Deepfake analyzer (CNN + forensics + metadata scan)
- CrowdShield community reports (submit, list, verify, blocklist integration)
- Scam psychology analysis (6 categories)
- Scan history (all 4 types) with authenticated persistence
- Dark theme UI with sidebar + top nav
- Guest mode access

### ⚠️ Partially Working
- Email OTP delivery (simulated to terminal, no real SMTP configured)
- Phone OTP delivery (simulated to terminal, no SMS integration)
- Deepfake CNN model (trained on synthetic data only, limited real-world accuracy)
- Video deepfake analysis (hash-based mock, not actual frame analysis)

### ❌ Broken
- `start.bat` has hardcoded paths (`C:\CyberGuardianAi\...`) that won't work from the current project location
- `requirements.txt` is missing essential runtime dependencies (torch, scipy, Pillow, python-multipart)

### 🔲 Missing
- Production deployment (Phase 6)
- Email-specific analyzer (dataset placeholder exists, no implementation)
- Real deepfake training data
- Rate limiting / CAPTCHA
- Admin panel for community moderation
- User profile management
- Notification system
- API documentation (Swagger is auto-generated by FastAPI but not customized)

### ❓ Unknown
- Whether PostgreSQL is currently running and accessible
- Whether all ML model files are intact and loadable
- Frontend build/deployment status

---

## 16. BUGS AND RISKS

### Confirmed Problems

1. **Missing dependencies in `requirements.txt`**: `torch`, `torchvision`, `scipy`, `Pillow`, `python-multipart` are required but not listed. A fresh `pip install -r requirements.txt` will fail to run the deepfake analyzer.

2. **Google OAuth `client_secret` committed to git**: The file `client_secret_48190723181-*.json` contains the OAuth client_secret in plaintext.

3. **Database password in `start.bat`**: The batch file contains `postgresql://postgres:9898123@localhost:5432/cyberguardian` — an actual DB password.

4. **JWT secret hardcoded fallback**: `JWT_SECRET = os.getenv("CYBERGUARDIAN_JWT_SECRET", "cyberguardian-dev-secret")` — if the env var isn't set, a known static secret is used, making JWT forgeable.

5. **Google Client ID hardcoded in frontend**: The Client ID `48190723181-pf48lpee9226voi06h554qq5r93hchbb.apps.googleusercontent.com` is hardcoded in `App.jsx` line 316.

6. **CORS wide open**: `allow_origins=["*"]` in `main.py` allows any domain to make API requests.

7. **`start.bat` wrong paths**: References `C:\CyberGuardianAi\` which doesn't match the current project location.

### Potential Problems

8. **Deepfake Random Forest trained but never used**: `train_deepfake_model()` saves `deepfake_rf.pkl` but the analyzer loads `deepfake_cnn.pth`. Dead code / confusion risk.

9. **No rate limiting**: OTP endpoint can be spammed; analysis endpoints have no throttling; community report can be abused.

10. **No input validation on community reports**: Any user (even anonymous) can flood the report system.

11. **Community reputation lookup does LIKE matching**: The `community_reputation.py` query uses `LIKE` with user input, which could be slow on large datasets and might match unintended entries.

12. **Monolithic frontend**: All 2044 lines in a single `App.jsx` — difficult to maintain, debug, or extend.

13. **No error boundaries in React**: Frontend crashes are not gracefully handled.

14. **`pickle.load` on ML models**: Loading pickle files from disk is a known security concern if models could be tampered with.

15. **OTP code printed in API response**: When SMTP is not configured, the simulated OTP code is returned directly in the API response (`message` field), which is a security concern.

16. **Deprecated `@app.on_event("startup")`**: FastAPI recommends `lifespan` context manager instead.

---

## 17. PROJECT HISTORY / INTENT

### Git History (4 commits)

| Commit | Message |
|--------|---------|
| `f612075` | Initial commit: project scaffold |
| `2865bf7` | commit |
| `0b242d2` | commit |
| `3a62941` | ibo |

### Roadmap (from `docs/project-roadmap.md`)

| Phase | Feature | Status |
|-------|---------|--------|
| Phase 1 | Authentication + Dashboard + Password Analyzer | ✅ Done |
| Phase 2 | URL Risk Analyzer | ✅ Done |
| Phase 3 | Email & Message Analyzer | ✅ Done (message only, no email-specific) |
| Phase 4 | Scam Psychology Engine | ✅ Done |
| Phase 5 | CrowdShield (Community Intelligence) | ✅ Done |
| Phase 6 | Deployment | 🔲 Not started |

### Intent
Academic/portfolio project demonstrating explainable AI in cybersecurity. The emphasis is on *explaining why* threats are flagged, not just binary classification.

---

## 18. IMPORTANT FILES (Ranked)

| Rank | File | Why It Matters | What Breaks |
|------|------|----------------|-------------|
| 1 | [`backend/main.py`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/backend/main.py) | FastAPI entry point; creates app, registers all routes | Entire backend |
| 2 | [`frontend/src/App.jsx`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/frontend/src/App.jsx) | Entire frontend UI, logic, and state (2044 lines) | Entire frontend |
| 3 | [`backend/routes/security.py`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/backend/routes/security.py) | All security analysis endpoints | All analysis features |
| 4 | [`backend/routes/auth.py`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/backend/routes/auth.py) | Authentication system + JWT | Login, protected endpoints |
| 5 | [`backend/database/connection.py`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/backend/database/connection.py) | DB connection + schema creation | All DB-dependent features |
| 6 | [`backend/services/deepfake_analyzer.py`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/backend/services/deepfake_analyzer.py) | Deepfake analysis pipeline | Deepfake feature |
| 7 | [`backend/services/url_feature_extractor.py`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/backend/services/url_feature_extractor.py) | 30-feature URL extraction | URL analyzer accuracy |
| 8 | [`backend/services/scam_psychology.py`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/backend/services/scam_psychology.py) | Psychology engine used by URL + message | Scam explanations |
| 9 | [`frontend/src/index.css`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/frontend/src/index.css) | Complete design system (1069 lines) | All UI styling |
| 10 | [`backend/train_models.py`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/backend/train_models.py) | Trains all ML models | ML model regeneration |
| 11 | [`models/url_classifier.pkl`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/models/url_classifier.pkl) | Pre-trained URL model | URL predictions |
| 12 | [`models/message_classifier.pkl`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/models/message_classifier.pkl) | Pre-trained message model | Message predictions |
| 13 | [`models/deepfake_cnn.pth`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/models/deepfake_cnn.pth) | Pre-trained deepfake CNN | Deepfake predictions |
| 14 | [`requirements.txt`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/requirements.txt) | Python dependencies | Installation |
| 15 | [`frontend/package.json`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/frontend/package.json) | Frontend dependencies | Frontend builds |
| 16 | [`backend/.env`](file:///c:/Users/DIVYA/OneDrive/Desktop/Desktopp/CyberGuardian/backend/.env) | Database URL config | DB connection |

---

## 19. HOW TO MODIFY THE PROJECT SAFELY

### Where to Add New Features
- **New analysis type:** Add service in `backend/services/`, schema in `backend/models/security_schemas.py`, endpoint in `backend/routes/security.py`, UI section in `frontend/src/App.jsx`, table in `backend/database/connection.py`
- **New API endpoint:** Add to appropriate router file in `backend/routes/`
- **New ML model:** Train in `backend/train_models.py`, save to `models/`, load in service file

### Files to Normally Modify
- `App.jsx` — for any UI change (but consider splitting into components first)
- `index.css` — for styling changes
- `routes/security.py` — for new security endpoints
- `services/` — for new business logic
- `database/connection.py` — for new tables

### Files NOT to Manually Edit
- `models/*.pkl`, `models/*.pth` — binary ML model files (regenerate via training)
- `node_modules/`, `venv/`, `__pycache__/` — auto-generated
- `package-lock.json` — auto-managed by npm

### How to Add New AI Models/Providers
1. Add training logic to `train_models.py`
2. Save model to `models/` directory
3. Create service file in `services/` with lazy-loading pattern
4. Add endpoint in `routes/security.py`
5. Add schema in `models/security_schemas.py`
6. Add DB table in `connection.py`

---

## 20. AI HANDOFF CONTEXT

# AI HANDOFF CONTEXT

## Project Purpose
CyberGuardian AI is a full-stack explainable cybersecurity platform. It analyzes passwords, URLs, messages, and images/videos for security threats using ML models and heuristic rules. Key differentiator: every assessment includes detailed human-readable explanations, scam psychology analysis, and community intelligence.

## Tech Stack
- **Frontend:** React 18 + Vite 5 + vanilla CSS (single-file monolith: `App.jsx`, 2044 lines)
- **Backend:** FastAPI (Python) with raw SQL via psycopg2 (no ORM)
- **Database:** PostgreSQL (7 tables)
- **ML:** XGBoost (URL), scikit-learn TF-IDF+LogReg (messages), PyTorch CNN (deepfake)
- **Auth:** JWT (HS256, 24h) + OTP (email/phone simulated) + Google OAuth (GSI)

## Architecture
Frontend (React SPA, port 5173) → Backend (FastAPI, port 8000) → PostgreSQL + ML Models (.pkl/.pth)

## Entry Points
- Backend: `backend/main.py` → `uvicorn main:app --reload`
- Frontend: `frontend/src/main.jsx` → `npm run dev`
- Training: `backend/train_models.py`

## Important Files (read these first)
1. `backend/main.py` — FastAPI app setup
2. `frontend/src/App.jsx` — Entire frontend
3. `backend/routes/security.py` — All analysis endpoints
4. `backend/routes/auth.py` — Auth system
5. `backend/database/connection.py` — DB schema + connection
6. `backend/services/deepfake_analyzer.py` — Deepfake pipeline
7. `backend/services/url_feature_extractor.py` — URL feature extraction
8. `backend/services/scam_psychology.py` — Psychology engine
9. `frontend/src/index.css` — Design system
10. `requirements.txt` — Python deps (INCOMPLETE — see below)

## Current AI/LLM Setup
This project does NOT use any LLM APIs. All ML is local model inference. Claude Code is configured separately for development assistance via OpenRouter.

## API Structure
- `POST /auth/request-otp`, `POST /auth/verify-otp`, `POST /auth/google`, `GET /auth/me`
- `POST /security/analyze-password`, `GET /security/password-scans`
- `POST /security/analyze-url`, `GET /security/url-scans`
- `POST /security/analyze-message`, `GET /security/message-scans`
- `POST /security/analyze-deepfake` (multipart), `GET /security/deepfake-scans`
- `POST /community/report`, `GET /community/reports`, `POST /community/verify/{id}`

## Database (PostgreSQL)
7 tables: `users`, `otp_challenges`, `password_scans`, `url_scans`, `message_scans`, `deepfake_scans`, `community_reports`. All scan tables FK to users. Schema auto-created on startup.

## Environment Variables (NO SECRET VALUES)
- `CYBERGUARDIAN_DATABASE_URL` — PostgreSQL connection string [REQUIRED]
- `CYBERGUARDIAN_JWT_SECRET` — JWT signing key [RECOMMENDED, has insecure default]
- `GOOGLE_CLIENT_ID` — Google OAuth client ID [HARDCODED]
- `CYBERGUARDIAN_SMTP_HOST/PORT/USERNAME/PASSWORD` — Email delivery [OPTIONAL, simulated if empty]
- `VITE_API_BASE_URL` — Backend URL for frontend [OPTIONAL, defaults to localhost:8000]

## Run Commands
```powershell
# Backend
cd backend && .\venv\Scripts\Activate && uvicorn main:app --reload --port 8000
# Frontend
cd frontend && npm run dev
# Train models
cd backend && python train_models.py
```

## Current Bugs
1. `requirements.txt` missing: torch, torchvision, scipy, Pillow, python-multipart
2. Google client_secret committed to repo
3. DB password in start.bat
4. JWT secret has insecure hardcoded fallback
5. CORS allows all origins
6. start.bat has wrong hardcoded paths
7. OTP code returned in API response when SMTP not configured

## Current TODOs
- Production deployment (Phase 6)
- Email-specific analyzer
- Real deepfake training data
- Rate limiting / CAPTCHA
- Split App.jsx into components
- Fix requirements.txt
- Remove committed secrets

## Important Constraints
- Frontend is a single monolithic file (App.jsx) — any UI change happens there
- No ORM — all DB queries are raw SQL strings
- ML models are lazy-loaded singletons; first request triggers loading
- Deepfake CNN auto-trains on synthetic data if model file is missing
- All tests are standalone scripts, no pytest framework

## Coding Conventions
- Python: type hints, f-strings, context managers for DB
- JavaScript: functional components, useState hooks, async/await
- CSS: BEM-style class naming, CSS custom properties for dark theme
- No linting or formatting config detected

## Things an AI Should NOT Change
- ML model binary files (`models/*.pkl`, `models/*.pth`) — regenerate via training
- `datasets/` — training data should remain unchanged
- `docs/phishing_features_reference.md` — academic reference document
- `LICENSE` — MIT license

---

## 21. FINAL SUMMARY

### Project in One Paragraph

CyberGuardian AI is a full-stack explainable cybersecurity platform built with React 18 + Vite (frontend) and FastAPI + PostgreSQL (backend) that provides six security analysis tools: password strength scoring, URL phishing detection (XGBoost ML on 30 features), SMS/message spam detection (TF-IDF + Logistic Regression), deepfake image/video analysis (PyTorch CNN + digital forensics including ELA, FFT, and noise analysis), scam psychology profiling (6 cognitive manipulation categories), and community-sourced threat intelligence ("CrowdShield"). Authentication uses OTP (email/phone, currently simulated) and Google OAuth with JWT sessions. Every analysis returns explainable feedback — not just a risk score, but detailed reasons why content was flagged and actionable tips. The project is feature-complete for its MVP scope across all 6 planned phases but has not been deployed to production and has several dependency, security, and code organization issues to address.

### Architecture in One Diagram

```
User Browser (localhost:5173)
        │
        │ HTTP REST (JSON + multipart)
        ▼
   React SPA (App.jsx)
        │
        ▼
   FastAPI Backend (localhost:8000)
   ├── /auth      → JWT + OTP + Google OAuth
   ├── /security  → Password / URL / Message / Deepfake
   └── /community → CrowdShield Reports
        │                    │
        ▼                    ▼
   PostgreSQL          ML Models (.pkl/.pth)
   (7 tables)          ├── XGBoost (URL)
                       ├── TF-IDF+LR (Message)
                       └── PyTorch CNN (Deepfake)
```

### Critical Files
1. `backend/main.py`
2. `frontend/src/App.jsx`
3. `backend/routes/security.py`
4. `backend/routes/auth.py`
5. `backend/database/connection.py`
6. `backend/services/deepfake_analyzer.py`
7. `backend/services/url_feature_extractor.py`
8. `backend/services/scam_psychology.py`
9. `backend/services/deepfake_model.py`
10. `backend/services/message_analyzer.py`
11. `frontend/src/index.css`
12. `backend/train_models.py`
13. `requirements.txt`
14. `backend/.env`

### Critical Configuration
- `CYBERGUARDIAN_DATABASE_URL` [REQUIRED]
- `CYBERGUARDIAN_JWT_SECRET` [RECOMMENDED]
- `VITE_API_BASE_URL` [OPTIONAL]
- SMTP vars [OPTIONAL — email OTP simulated without them]

### Current TODOs
1. Production deployment
2. Fix `requirements.txt` (add missing packages)
3. Remove committed secrets from git
4. Implement real email/SMS delivery
5. Add rate limiting
6. Split `App.jsx` into components
7. Train deepfake model on real data
8. Implement email-specific analyzer
9. Add admin panel for CrowdShield moderation
10. Fix CORS for production

### Known Problems

**Confirmed:**
- Missing Python dependencies in requirements.txt
- Committed secrets (Google client_secret, DB password)
- Insecure JWT fallback secret
- Wide-open CORS
- Wrong paths in start.bat
- OTP returned in cleartext API response

**Suspected:**
- Deepfake CNN accuracy likely poor (synthetic training data)
- Video analysis is hash-based mock
- No abuse prevention on community reports
- Large monolith frontend will become unmaintainable
- `deepfake_rf.pkl` trained but never loaded (dead code)

### Confidence / Unknowns

| Confident About | Unknown |
|-----------------|---------|
| Complete file structure | Whether PostgreSQL is running |
| All source code logic | Actual ML model accuracy on real data |
| API endpoint mapping | Whether frontend build works correctly |
| Database schema | Whether all pip packages are installed in venv |
| Auth flow | Production deployment requirements |
| Dependencies (listed + missing) | Whether tests currently pass |
