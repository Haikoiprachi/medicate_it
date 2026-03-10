# 🏥 MedTriage AI — Multi-Agent Medical Triage System

A production-grade medical triage assistant powered by **LangGraph** multi-agent pipelines,
**FastAPI** backend, and a **React** frontend — with comprehensive privacy protection.

---

## 🏗️ Architecture

```
User Input (React)
    │
    ▼ [Client-side PII stripping + XOR encoding]
    │
FastAPI Backend (/api/triage)
    │
    ▼ [Server-side PII stripping + session hashing]
    │
LangGraph State Graph
    │
    ├──▶ Agent 1: Symptom Extractor
    │         └── Structured symptom extraction
    │
    ├──▶ Agent 2: Risk Analyzer
    │         └── Conditions, red flags, body systems
    │
    ├──▶ Agent 3: Risk Scorer
    │         └── Dynamic 0-100 risk score
    │
    ├──▶ [Conditional Edge] ──── if escalation_flag ──▶ Escalation Node
    │
    └──▶ Agent 4: Triage Decision
              └── Urgency level, recommendations, warnings
```

---

## 🚀 Quick Start

### 1. Clone & Set Up Backend

```bash
cd backend
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 2. Run the FastAPI Server

```bash
cd backend
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

### 3. Set Up & Run the Frontend

```bash
cd frontend
npm create vite@latest . -- --template react
# When prompted, select "React" and "JavaScript"

# Copy App.jsx into src/
cp src/App.jsx src/App.jsx  # already in place

npm install
npm run dev
```

Open `http://localhost:3000` in your browser.

---

## 🔒 Privacy & Security Architecture

### Client-Side Privacy
| Layer | What it does |
|---|---|
| **PII Stripping** | Regex removes phones, emails, names, SSNs, IDs, zip codes before any network call |
| **XOR Encoding** | Raw input is obfuscated in browser memory with a per-session random key |
| **No Persistence** | No localStorage, sessionStorage, cookies, or IndexedDB usage |
| **Anonymous Sessions** | Session ID is a cryptographically random UUID, hashed before use |

### Server-Side Privacy
| Layer | What it does |
|---|---|
| **Second PII Pass** | Server independently strips PII from all incoming inputs |
| **SHA-256 Session Hashing** | Raw session IDs are hashed before any logging |
| **Audit Logs** | Only metadata is logged (agent name, count, boolean flags) — never user content |
| **No DB Storage** | No database writes — state lives only in the LangGraph execution context |
| **CORS Restrictions** | Only localhost:3000 is allowed in development |

### For Production
- Add HTTPS / TLS termination
- Add rate limiting (e.g. `slowapi`)
- Add AES-256 encryption for any at-rest data
- Implement HIPAA-compliant audit logging
- Add authentication (OAuth2 / JWT)
- Set `docs_url=None` (already done) and restrict CORS to your domain

---

## 📡 API Reference

### POST `/api/triage`
```json
// Request
{
  "symptoms": "Describe your symptoms here...",
  "session_id": "optional-client-session-id"
}

// Response
{
  "session_hash": "a3f9c1b2d4e6",
  "extracted_symptoms": { ... },
  "risk_analysis": { ... },
  "risk_score": {
    "overall_score": 65,
    "score_breakdown": { ... },
    "confidence": "high",
    "escalation_flag": false
  },
  "triage_decision": {
    "urgency_level": "URGENT",
    "recommendations": [...],
    "warning_signs": [...],
    ...
  },
  "completed_agents": ["extractor", "analyzer", "scorer", "triage"],
  "errors": [],
  "privacy_log": {
    "pii_stripped": true,
    "raw_input_stored": false,
    "session_linked_to_identity": false
  }
}
```

### GET `/health`
```json
{ "status": "ok", "service": "MedTriage AI", "version": "1.0.0" }
```

---

## 🤖 LangGraph Agent Details

### Agent 1 — Symptom Extractor
- Parses free-text into structured symptoms
- Extracts: severity, duration, location, onset, affected areas

### Agent 2 — Risk Analyzer
- Identifies potential conditions with likelihood
- Detects red flags and body systems involved
- Flags cases requiring immediate attention

### Agent 3 — Risk Scorer
- Calculates dynamic 0–100 risk score
- Weighted breakdown across 5 dimensions:
  - Symptom Severity (0–30)
  - Red Flag Count (0–25)
  - Duration Factor (0–20)
  - System Involvement (0–15)
  - Onset Factor (0–10)

### Conditional Edge — Escalation
- Triggered if `requires_immediate_attention=true` OR `escalation_flag=true`
- Injects escalation marker into state before triage decision

### Agent 4 — Triage Decision
- Outputs one of 5 urgency levels: EMERGENCY / URGENT / SEMI_URGENT / NON_URGENT / SELF_CARE
- Provides recommendations, warning signs, self-care tips, follow-up guidance

---

## ⚠️ Medical Disclaimer

This system is an AI-powered informational tool and does **not** replace professional
medical advice, diagnosis, or treatment. In case of a medical emergency, call 911
or your local emergency services immediately.

---

## 📁 Project Structure

```
medtriage/
├── backend/
│   ├── main.py              # FastAPI app + LangGraph pipeline
│   ├── requirements.txt     # Python dependencies
│   ├── .env.example         # Environment template
│   └── .env                 # Your API key (gitignored)
└── frontend/
    └── src/
        └── App.jsx          # React frontend
```
