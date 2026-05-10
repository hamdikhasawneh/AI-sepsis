# Running SepsisAI Locally

## Project Structure

```
AI-sepsis/
├── backend/
│   ├── app/
│   │   ├── models/ml_files/    ← DST v2 model files go here
│   │   ├── db/seed.py          ← auto-runs on first startup
│   │   └── main.py
│   └── requirements.txt
├── frontend/
└── docker-compose.yml
```

---

## AI Model Files

The DST v2 model must be present before starting the backend.
All files go inside `backend/app/models/ml_files/`:

| File | Required | Purpose |
|------|----------|---------|
| `dst_best.pt` | Yes | Trained transformer weights |
| `dst_calibrators.pkl` | Yes | Platt calibration per time bin |
| `dst_scaler.pkl` | Yes | StandardScaler for input features |
| `dst_vital_winsor_lo.npy` | Yes | Vital sign winsorisation lower bounds |
| `dst_vital_winsor_hi.npy` | Yes | Vital sign winsorisation upper bounds |
| `dst_winsor_lo.npy` | Yes | Static feature winsorisation lower bounds |
| `dst_winsor_hi.npy` | Yes | Static feature winsorisation upper bounds |
| `dst_feature_cols.txt` | Yes | Feature column ordering |
| `dst_shap_values.npy` | No | Precomputed SHAP attributions |
| `dst_shap_stay_ids.npy` | No | Stay IDs matching SHAP rows |

If any required file is missing the backend logs a warning and falls back to a mock model (`model_version: "mock-v1"`). Real inference shows `model_version: "dst-v2"`.

---

## Database Seeding

Seeding is **automatic** — it runs on every backend startup via the `@app.on_event("startup")` hook in `main.py`. It checks if any users exist first; if the database already has data it skips silently.

**What gets seeded:**

| Entity | Count | Details |
|--------|-------|---------|
| Users | 5 | 1 admin, 2 doctors, 2 nurses |
| Patients | 12 | 8 admitted (ICU-01 to ICU-08), 4 discharged/transferred |
| Vital signs | ~192 | 24 readings per admitted patient (every 30 min) |
| Predictions | ~48 | 6 per admitted patient (every 2 hours) |
| Alerts | 4 | 3 unread + 1 acknowledged |
| System settings | 2 | Risk threshold (0.80), sound notifications |

**Demo credentials:**

| Role | Username | Password |
|------|----------|----------|
| Physician | `dr.smith` | `doctor123` |
| Physician | `dr.johnson` | `doctor123` |
| Nurse | `nurse.jane` | `nurse123` |
| Nurse | `nurse.mike` | `nurse123` |
| Admin | `admin` | `admin123` |

To re-seed (wipe and restart fresh):

```powershell
# No Docker: delete the SQLite file and restart
del backend\sepsis.db
uvicorn app.main:app --reload --port 8000

# Docker: wipe the postgres volume
docker compose down -v
docker compose up
```

---

## Option A — Without Docker (Windows)

### Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.10 or 3.11 | python.org — check "Add to PATH" during install |
| Node.js | 18+ | nodejs.org |
| Tesseract OCR | 5.x | https://github.com/UB-Mannheim/tesseract/wiki — add install dir to PATH |

---

### 1. Place model files

Copy all DST v2 files into:
```
backend\app\models\ml_files\
```

---

### 2. Backend

Open **PowerShell** in the repo root:

```powershell
cd backend

# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate

# Install dependencies (torch download may take a few minutes)
pip install -r requirements.txt
```

Create `backend\.env`:

```env
DATABASE_URL=sqlite:///./sepsis.db
JWT_SECRET_KEY=dev-secret-key-local-xyz123
DEBUG=true
```

```powershell
# Start the backend (must be inside backend/ with venv active)
uvicorn app.main:app --reload --port 8000
```

On first start you will see:

```
[Seed] Seeding database with demo data...
[Seed] ✓ Database seeded successfully!
[Seed]   Users: 5 (1 admin, 2 doctors, 2 nurses)
[Seed]   Patients: 12 (8 admitted, 4 history)
...
INFO: DST v2 model loaded successfully.
INFO: Platt calibrators loaded: N time points.
INFO: StandardScaler loaded.
```

Backend runs at **http://localhost:8000**  
API docs at **http://localhost:8000/docs**

---

### 3. Frontend

Open a **second** PowerShell in the repo root:

```powershell
cd frontend

# Install dependencies (first run only)
npm install

# Start dev server
npm run dev
```

Frontend runs at **http://localhost:5173**

---

## Option B — With Docker

### Prerequisites

- [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/) with WSL 2 backend enabled

---

### 1. Place model files

Same as above — copy DST v2 files into `backend\app\models\ml_files\` before building.

---

### 2. Start everything

```powershell
# From repo root
docker compose up --build
```

This starts three containers in order:

| Container | Port | Notes |
|-----------|------|-------|
| `db` (PostgreSQL 16) | 5432 | backend waits for its health check |
| `backend` (FastAPI) | 8000 | seeds DB automatically on first start |
| `frontend` (Vite) | 5173 | |

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API docs | http://localhost:8000/docs |

---

### 3. Stop

```powershell
# Stop containers (keeps database volume)
docker compose down

# Stop and wipe database (triggers re-seed on next start)
docker compose down -v
```

---

## Verify Everything Works

```powershell
# Health check
curl http://localhost:8000/api/health
# Expected: {"status":"ok"}
```

Then open **http://localhost:5173** → Get Started → select role → click **Fill** to auto-fill demo credentials → Sign In.

If predictions show `model_version: "dst-v2"` in the physician dashboard, the real model is loaded. If they show `mock-v1`, check that all required files are in `ml_files/` and the backend log for load errors.
