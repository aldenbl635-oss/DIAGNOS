# DiagnOS – AI Clinical Reasoning Simulator

> **Educational Simulation Only** – This platform uses synthetic cases and virtual AI patients. It is NOT a real-world clinical diagnostic or treatment tool.

---

## Project Vision

DiagnOS is an AI-powered clinical simulation and assessment platform for medical students. Traditional medical examinations primarily test memory and factual recall. Real clinical practice requires a different skill set:

- Asking the right questions
- Gathering relevant history
- Identifying important symptoms and risk factors
- Forming differential diagnoses
- Selecting appropriate investigations
- Prioritizing investigations
- Interpreting test results
- Updating hypotheses as new evidence appears
- Making appropriate clinical decisions under uncertainty

**The key differentiator:** DiagnOS evaluates HOW a medical student thinks, not merely WHETHER they know the answer.

---

## Features

| Feature | Status |
|---|---|
| Beautiful landing page with educational disclaimer | ✅ |
| JWT authentication (register / login / demo access) | ✅ |
| Student performance dashboard with Recharts radar chart | ✅ |
| Clinical Case Library | ✅ |
| Case Briefing / Patient Chart | ✅ |
| Full Clinical Workstation Simulation UI | ✅ |
| Natural-language AI patient interaction (LLM or offline) | ✅ |
| Physical examination requests | ✅ |
| Investigation ordering system with 1000-credit budget | ✅ |
| Progressive evidence reveal | ✅ |
| Differential diagnosis tracker with sliders | ✅ |
| Complete student action logging to SQLite | ✅ |
| Rule-based scoring engine (65 pts) | ✅ |
| AI qualitative reasoning evaluation (35 pts) | ✅ |
| Full evaluation report with strengths & weaknesses | ✅ |
| Reasoning timeline / action chronology | ✅ |
| Expected vs Actual pathway comparison | ✅ |
| Adaptive learning recommendations | ✅ |
| DEMO MODE (fully offline, no API key needed) | ✅ |

---

## Architecture

```
diagnos/
├── backend/              # Python FastAPI backend
│   ├── main.py           # FastAPI app + CORS config
│   ├── config.py         # Environment settings
│   ├── database.py       # SQLAlchemy engine
│   ├── models.py         # ORM models (User, Case, Session, Action, Evaluation)
│   ├── schemas.py        # Pydantic v2 request/response schemas
│   ├── seed.py           # Database initializer
│   ├── routes/           # API route handlers
│   │   ├── auth.py       # /api/auth/* (register, login, me)
│   │   ├── cases.py      # /api/cases/*
│   │   ├── simulation.py # /api/simulation/* (main engine)
│   │   └── dashboard.py  # /api/dashboard
│   ├── case_engine/      # Structured JSON case loader
│   │   ├── engine.py
│   │   └── cases/
│   │       └── chest_pain_001.json
│   ├── evaluation/       # Clinical reasoning scoring
│   │   ├── scorer.py     # Rule-based evaluation (65 pts)
│   │   └── ai_eval.py    # AI evaluation + hybrid scoring (35 pts)
│   ├── ai/               # LLM client abstraction
│   │   ├── client.py     # Gemini/OpenAI/offline client
│   │   └── simulator.py  # Patient QA matching + LLM simulation
│   ├── prompts/          # Prompt templates
│   │   ├── patient_simulator.txt
│   │   ├── reasoning_evaluator.txt
│   │   └── feedback_generator.txt
│   ├── requirements.txt
│   └── test_main.py      # Pytest unit tests
│
└── frontend/             # React + Vite + Tailwind CSS frontend
    ├── index.html
    ├── vite.config.js    # Vite config with /api proxy
    ├── src/
    │   ├── App.jsx       # State-based router / layout
    │   ├── api/
    │   │   └── client.js # Fetch-based API client
    │   ├── components/
    │   │   └── Common/
    │   │       ├── Navbar.jsx
    │   │       ├── Disclaimer.jsx
    │   │       └── Loader.jsx
    │   └── pages/
    │       ├── Landing.jsx      # Marketing landing page
    │       ├── Login.jsx        # Auth (login + register)
    │       ├── Dashboard.jsx    # Student performance overview
    │       ├── CaseSelection.jsx # Case library browser
    │       ├── Briefing.jsx     # Pre-simulation case brief
    │       ├── Simulation.jsx   # Clinical workstation (main UI)
    │       └── Results.jsx      # Evaluation report
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 8, Tailwind CSS v4, Lucide React, Recharts |
| Backend | Python 3.14, FastAPI, Uvicorn |
| Database | SQLite + SQLAlchemy v2 |
| Auth | python-jose (JWT HS256), PBKDF2/hashlib |
| AI (optional) | Google Gemini 2.0 Flash (google-genai SDK) or OpenAI GPT-4o-mini |
| Testing | Pytest + FastAPI TestClient |

---

## Installation

### Prerequisites
- Python 3.10+ (tested on 3.14)
- Node.js 20+ (tested on 24 LTS)

### 1. Clone / Open Project

```bash
cd c:\Users\Alden\projects\diagnos
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `.env.example` to `backend/.env`:

```bash
cp ../.env.example .env
```

Edit `.env`:

```env
DATABASE_URL=sqlite:///./diagnos.db
SECRET_KEY=your_secret_key_here
DEMO_MODE=True

# Optional – for AI-powered patient simulation:
GEMINI_API_KEY=your_gemini_api_key
# OR
OPENAI_API_KEY=your_openai_api_key
```

### 4. Seed Database

```bash
python seed.py
```

### 5. Frontend Setup

```bash
cd ../frontend
npm install
```

---

## Running the Application

### Start Backend (Terminal 1)

```bash
cd backend
.\venv\Scripts\uvicorn main:app --port 8000 --reload
```

Backend runs at: `http://localhost:8000`  
API docs: `http://localhost:8000/docs`

### Start Frontend (Terminal 2)

```bash
cd frontend
npm run dev
```

Frontend runs at: `http://localhost:5173`

---

## Demo Mode

If no AI API keys are provided or `DEMO_MODE=True` is set in `.env`, the application runs in **fully offline mode**:

- Patient responses are generated using keyword-matching against case Q&A pairs
- Reasoning evaluation uses deterministic rule-based scoring
- All features remain fully functional without internet access

This ensures reliable hackathon demonstrations even without external API access.

---

## Running Tests

```bash
cd backend
.\venv\Scripts\pytest test_main.py -v
```

Expected output: **3 passed**

Tests cover:
- Case engine loading
- User registration and login
- Full simulation workflow (start → questions → investigation → differentials → evaluate)

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Create new user account |
| POST | `/api/auth/login` | Authenticate user, get JWT |
| GET | `/api/auth/me` | Get current user |
| GET | `/api/cases` | List all available cases |
| GET | `/api/cases/{id}` | Get single case details |
| GET | `/api/simulation/{id}` | Get session state for resume |
| POST | `/api/simulation/start` | Start a new simulation session |
| POST | `/api/simulation/{id}/question` | Ask the AI patient a question |
| POST | `/api/simulation/{id}/examination` | Perform a physical examination |
| POST | `/api/simulation/{id}/investigation` | Order a diagnostic test |
| POST | `/api/simulation/{id}/diagnosis` | Update differential diagnoses |
| POST | `/api/simulation/{id}/evaluate` | Submit final diagnosis + get graded |
| GET | `/api/simulation/{id}/results` | Retrieve evaluation results |
| GET | `/api/dashboard` | Get student dashboard statistics |

---

## Scoring System

The scoring system is hybrid (rule-based + AI):

| Category | Max Points | Evaluator |
|---|---|---|
| History Taking | 20 | Rule-based |
| Differential Diagnosis | 15 | Rule-based |
| Investigation Selection | 20 | Rule-based |
| Evidence Interpretation | 20 | AI (scaled) |
| Clinical Reasoning | 15 | AI (scaled) |
| Resource Efficiency | 5 | Rule-based |
| Final Decision | 5 | Rule-based |
| **Total** | **100** | |

---

## Limitations

- Only one fully active case (Atypical Chest Pain) in MVP
- Demo mode uses keyword matching, not a full NLP pipeline
- Patient responses in AI mode are only as good as the configured LLM
- SQLite is used; replace with PostgreSQL for production

## Future Improvements

- More medical specialties and cases
- Voice-based patient interaction
- Multilingual patient simulations
- Instructor/School dashboards and cohort analytics
- Adaptive difficulty based on past performance
- OSCE-style structured assessment templates
- Real-time collaborative simulations
- Bayesian diagnostic reasoning engine
