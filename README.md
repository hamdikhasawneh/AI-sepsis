# ICU Sepsis Early Warning Detection System

Full-stack web application for ICU sepsis early detection, with role-based dashboards for doctors, nurses, and admins.

## Tech Stack
- **Backend**: FastAPI, SQLAlchemy, PostgreSQL, JWT Auth, Alembic
- **Frontend**: React 18, Vite, Recharts, Axios
- **Infrastructure**: Docker Compose, PostgreSQL 16

## Quick Start

```bash
# Clone and run
docker compose up --build

# Access
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

## Demo Accounts

| Role   | Username      | Password    |
|--------|--------------|-------------|
| Admin  | admin        | admin123    |
| Doctor | dr.smith     | doctor123   |
| Doctor | dr.johnson   | doctor123   |
| Nurse  | nurse.jane   | nurse123    |
| Nurse  | nurse.mike   | nurse123    |

## Project Structure

```
AI-sepsis/
├── backend/
│   ├── app/
│   │   ├── api/          # REST API routes
│   │   ├── core/         # Config, security
│   │   ├── db/           # Database session, base, seed
│   │   ├── models/       # SQLAlchemy models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   ├── dependencies/ # Auth dependencies
│   │   └── main.py       # FastAPI app entry
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api/          # Axios client
│   │   ├── context/      # Auth context
│   │   ├── components/   # Reusable components
│   │   ├── pages/        # Page components
│   │   ├── routes/       # Route guards
│   │   └── App.jsx       # Main app with routing
│   ├── Dockerfile
│   └── package.json
└── docker-compose.yml
```

## Seed Data
The database auto-seeds on first startup with:
- 5 users (1 admin, 2 doctors, 2 nurses)
- 12 patients (8 admitted, 4 discharged/transferred)
- Historical vital signs for all admitted patients
- System settings (threshold = 0.80)

## API Endpoints

| Method | Endpoint                    | Description                  | Access          |
|--------|-----------------------------|------------------------------|-----------------|
| POST   | /api/auth/login             | Login, get JWT token         | Public          |
| GET    | /api/auth/me                | Current user info            | Authenticated   |
| POST   | /api/users/                 | Create user                  | Admin           |
| GET    | /api/users/                 | List users                   | Admin           |
| GET    | /api/users/doctors          | List doctors                 | Admin, Nurse    |
| POST   | /api/patients/              | Add patient                  | Admin, Nurse    |
| GET    | /api/patients/              | List patients                | Authenticated   |
| GET    | /api/patients/{id}          | Patient details              | Authenticated   |
| PATCH  | /api/patients/{id}          | Update patient               | Admin, Nurse    |
| PATCH  | /api/patients/{id}/notes    | Update notes                 | Admin, Doctor   |
| POST   | /api/vitals/                | Record vital signs           | Admin, Nurse    |
| GET    | /api/vitals/{patient_id}    | Get patient vitals           | Authenticated   |
| POST   | /api/vitals/simulate        | Trigger simulated vitals     | Admin           |
| POST   | /api/vitals/simulator/start | Start auto-simulator (60s)   | Admin           |
| POST   | /api/vitals/simulator/stop  | Stop auto-simulator          | Admin           |
