# AI Agent Build Specification for ICU Sepsis Detection System

## Project Overview
Build a modular, MVP/demo-friendly full-stack web application for an ICU sepsis early warning system. The system must support simulated device data, manual vital entry, mock prediction inference, alert generation, role-based dashboards, and a PostgreSQL-backed data model. The architecture must be clean enough to later replace the mock prediction service with a real PyTorch LSTM model or an external inference API.

The system is intended first for a university demo, but it must be structured so it can later be deployed to the cloud with minimal redesign.

---

## Core Product Goals
1. Provide separate role-based experiences for doctors, nurses, and admins.
2. Allow nurses and admins to add patients.
3. Allow nurses to enter vitals manually.
4. Simulate device-generated vitals every 1 minute for demo realism.
5. Run prediction logic using the last 6 hours of patient vitals.
6. Start with a mock prediction service and make it easy to swap in a real model later.
7. Create high-risk alerts using a configurable threshold from the admin panel, with a default threshold of `0.80`.
8. Let doctors and nurses view alerts, but only doctors can mark alerts as read.
9. Show active patients on dashboards and discharged/transferred patients in history views.
10. Display vitals-over-time charts on patient detail pages.

---

## Required Tech Stack

### Backend
- FastAPI
- SQLAlchemy ORM
- Alembic for migrations
- PostgreSQL
- JWT authentication
- Pydantic schemas
- Docker support
- Pytest for tests

### Frontend
- React
- Responsive UI for desktop/tablet demo usage
- React Router
- Axios or Fetch wrapper for API calls
- Chart library for vitals visualization (for example Recharts)
- Role-based routing and protected pages

### Infrastructure
- Docker and Docker Compose from the start
- Environment-based configuration
- Seed data script
- README with run instructions

---

## Users and Roles

### Admin
Permissions:
- create users
- manage roles
- assign doctors to patients
- configure alert threshold
- full edit on patient records
- access admin dashboard

### Nurse
Permissions:
- login and view nurse dashboard
- view patients
- add new patients
- limited edit of patient information
- add vitals manually
- view alerts as read-only
- cannot mark alerts as read

### Doctor
Permissions:
- login and view doctor dashboard
- view only assigned patients on active dashboard
- view history for assigned discharged/transferred patients
- view alerts for assigned patients
- mark alerts as read
- mostly view-only patient access except limited clinical note updates

---

## Functional Requirements

### Authentication
Implement JWT-based authentication with username or email plus password.

Minimum requirements:
- login endpoint
- current user endpoint
- hashed passwords
- access token generation
- role-based authorization middleware/dependencies
- protected frontend routes

### Patient Management
Patient fields must include:
- full name
- date of birth
- age
- gender
- admission time
- discharge time
- bed number
- ward or unit
- status (`admitted`, `discharged`, `transferred`)
- assigned doctor
- diagnosis or notes
- created_by_user_id

Rules:
- nurses and admins can add patients
- admins can fully edit patient info
- nurses can do limited edits
- doctors are mostly view-only, but may update limited clinical notes

### Vital Signs
Supported vital signs:
- heart rate
- respiratory rate
- temperature
- SpO2
- systolic BP
- diastolic BP
- mean BP

Sources:
- manual entry by nurse
- simulated monitor/device feed every 1 minute

Every vital row must store:
- patient ID
- recorded timestamp
- source (`manual` or `monitor`)
- optional entered_by_user_id

### Prediction Logic
Prediction for version 1 must use a mock prediction service.

Workflow:
1. A new vital row is created.
2. Backend stores it.
3. Backend fetches the patient’s vitals from the last 6 hours.
4. Backend checks whether enough data exists.
5. Backend prepares a prediction input.
6. Mock prediction service returns a risk score between 0 and 1.
7. Backend stores prediction result.
8. If score is above threshold and no unread alert exists for that patient, create an alert.

Design requirement:
- prediction service must be abstracted behind an interface so it can later be replaced with:
  - a local `.pt` PyTorch model
  - or an inference API

### Alerts
Rules:
- doctors and nurses can see alerts
- nurses are read-only
- only doctors can mark alerts as read
- duplicate active alerts for the same patient should be prevented when an unread alert already exists
- high-risk threshold must be configurable by admin
- default threshold should be `0.80`
- frontend should support visual notification and optional sound notification

### Dashboards
#### Doctor Dashboard
- assigned active patients only
- alert summary for assigned patients
- quick access to patient details
- active patient counts and high-risk indicators

#### Nurse Dashboard
- broader patient access based on operational workflow
- manual vital entry actions
- patient list and alert visibility

#### Admin Dashboard
- user management
- patient assignment tools
- alert threshold configuration
- system configuration summary

### History Page
Show discharged and transferred patients separately from active patients.

### Patient Detail Page
Must include:
- core patient information
- current status
- recent vitals
- vitals charts over time
- prediction history
- alert history
- note section

---

## Non-Functional Requirements
- clean modular architecture
- easy replacement of mock services with real ones
- responsive UI
- Dockerized local setup
- basic test coverage for critical backend flows
- clear README
- maintainable code and naming

---

## Suggested Database Design
Create tables at minimum for:
- `users`
- `patients`
- `vital_signs`
- `predictions`
- `alerts`
- `system_settings`

### Suggested Fields

#### users
- user_id
- username
- email
- password_hash
- full_name
- role
- is_active
- created_at

#### patients
- patient_id
- full_name
- date_of_birth
- age
- gender
- admission_time
- discharge_time
- bed_number
- ward_name
- status
- assigned_doctor_id
- diagnosis_notes
- created_by_user_id
- created_at
- updated_at

#### vital_signs
- vital_id
- patient_id
- recorded_at
- heart_rate
- respiratory_rate
- temperature
- spo2
- systolic_bp
- diastolic_bp
- mean_bp
- source
- entered_by_user_id
- created_at

#### predictions
- prediction_id
- patient_id
- predicted_at
- risk_score
- risk_level
- threshold_used
- model_version
- input_window_hours
- created_at

#### alerts
- alert_id
- prediction_id
- patient_id
- alert_message
- alert_level
- created_at
- is_read
- read_by_user_id
- read_at

#### system_settings
- setting_id
- key
- value
- updated_by_user_id
- updated_at

Store at least:
- `high_risk_threshold`
- optional sound notification preference defaults

---

## Required Backend API Areas
The AI agent should generate REST APIs for at least the following modules.

### Auth
- login
- me / current user
- refresh token if included

### Users/Admin
- create user
- list users
- update user role/status
- assign doctor to patient

### Patients
- create patient
- list active patients
- list history patients
- get patient details
- update patient
- update patient notes

### Vitals
- create manual vital entry
- list patient vitals
- simulate device vital ingestion endpoint or service trigger

### Predictions
- get patient prediction history
- optionally get latest prediction

### Alerts
- list alerts
- list unread alerts
- mark alert as read (doctor only)

### Settings
- get high-risk threshold
- update high-risk threshold (admin only)

---

## Frontend Pages to Generate
1. Login page
2. Doctor dashboard
3. Nurse dashboard
4. Admin dashboard
5. Patient details page
6. Alerts page
7. History/discharged patients page
8. Add patient page
9. Add vitals page

### Frontend Expectations
- responsive layout
- protected routes
- role-based navigation
- reusable API service layer
- reusable UI components
- alert badges / notification indicators
- charts for patient vitals over time
- clear status labels for admitted/discharged/transferred

---

## Architecture Guidance

### Backend Structure Suggestion
Use a scalable structure like:

```text
backend/
  app/
    api/
    core/
    db/
    models/
    schemas/
    services/
    repositories/
    utils/
    dependencies/
    main.py
  alembic/
  tests/
  Dockerfile
```

Important design decisions:
- keep business logic in services, not in route files
- use repositories or equivalent data-access abstraction
- isolate prediction logic inside a prediction service
- isolate alert generation logic inside an alert service
- use settings service for threshold management

### Frontend Structure Suggestion
Use a maintainable React structure like:

```text
frontend/
  src/
    api/
    auth/
    components/
    pages/
    layouts/
    hooks/
    context/
    routes/
    utils/
    types/
    App.jsx or App.tsx
```

Important design decisions:
- central auth state
- role-aware route protection
- reusable table/card/chart components
- separate dashboard page per role

---

## Phased Execution Plan for the AI Agent

## Phase 1: Project Foundation
Goal: create the full project skeleton and configuration.

Tasks:
- initialize backend FastAPI project
- initialize React frontend
- add Docker and Docker Compose
- add environment variable structure
- create README starter
- set up linting/basic formatting if desired

Deliverables:
- monorepo or organized full-stack folder structure
- backend bootstraps successfully
- frontend bootstraps successfully
- containers run locally

Success criteria:
- `docker compose up` brings up app services and database
- frontend can reach backend health endpoint

---

## Phase 2: Database and Data Model
Goal: define persistent structure.

Tasks:
- create SQLAlchemy models
- create Alembic migrations
- implement PostgreSQL schema
- add indexes for frequent queries
- create seed data for admin, doctors, nurses, and demo patients

Deliverables:
- migration files
- seed scripts
- initial test data

Success criteria:
- database initializes automatically
- seeded users and patients are visible

---

## Phase 3: Authentication and Authorization
Goal: secure the application.

Tasks:
- implement JWT login
- implement password hashing
- implement auth dependency/middleware
- implement role-based access control
- implement protected frontend routes

Deliverables:
- login API
- auth service
- frontend login flow

Success criteria:
- each role can log in
- protected pages redirect correctly
- role restrictions are enforced

---

## Phase 4: Core Patient Management
Goal: make patient workflows usable.

Tasks:
- create patient CRUD endpoints with role restrictions
- build add patient page
- build active patients views
- build history page for discharged/transferred patients
- build patient detail page base layout

Deliverables:
- patient APIs
- patient list views
- patient detail page

Success criteria:
- nurses/admins can add patients
- doctors see assigned patients only where appropriate
- history page separates non-active patients

---

## Phase 5: Vital Sign Ingestion
Goal: support both manual and simulated vitals.

Tasks:
- build manual vital entry API and form
- implement simulated device data generator/service running every 1 minute
- persist vital rows with source info
- display recent vitals in patient detail page

Deliverables:
- manual vital entry flow
- simulator module or background process
- patient vitals listing

Success criteria:
- vitals can be entered manually
- simulated vitals are generated for demo patients
- new rows appear correctly in UI

---

## Phase 6: Mock Prediction Pipeline
Goal: introduce prediction behavior without real ML dependency.

Tasks:
- build prediction service interface
- implement mock predictor
- collect last 6 hours of vitals per patient
- calculate or simulate risk score output
- store prediction records

Deliverables:
- prediction service abstraction
- mock predictor implementation
- prediction history endpoint

Success criteria:
- new vital rows can trigger prediction creation
- prediction history is stored and viewable

---

## Phase 7: Alert Engine
Goal: generate actionable alerts.

Tasks:
- implement configurable threshold lookup from settings
- implement alert generation on high risk
- prevent duplicate unread alerts per patient
- implement doctor-only mark-as-read action
- expose alerts in frontend
- add visual and optional sound notifications

Deliverables:
- alert service
- alert endpoints
- alerts page and notification UI

Success criteria:
- high-risk predictions generate alerts
- nurses can view but not resolve alerts
- doctors can mark alerts as read

---

## Phase 8: Role-Based Dashboards and Visualizations
Goal: make the product demo-ready.

Tasks:
- build doctor dashboard
- build nurse dashboard
- build admin dashboard
- add cards, counts, status indicators
- add vitals-over-time charts
- add latest risk/prediction summaries

Deliverables:
- three role-specific dashboards
- chart components
- cleaner UX for demo usage

Success criteria:
- each role sees relevant information only
- patient charts render correctly
- dashboards are responsive and presentation-ready

---

## Phase 9: Admin Controls and Settings
Goal: make configuration manageable.

Tasks:
- add user management screens
- add doctor assignment management
- add configurable high-risk threshold UI
- persist settings in database

Deliverables:
- admin settings panel
- user management features

Success criteria:
- admin can adjust threshold without code changes
- admin can create users and manage assignments

---

## Phase 10: Testing and Hardening
Goal: stabilize the MVP.

Tasks:
- add backend unit tests for auth, patients, vitals, predictions, alerts
- add integration tests for key flows
- verify role permissions
- test alert deduplication behavior
- test dashboard data loading
- improve error handling and validation

Deliverables:
- backend test suite
- selected frontend tests if possible
- bug fixes and validation improvements

Success criteria:
- critical flows pass tests
- common failure cases are handled cleanly

---

## Phase 11: Demo Deployment Readiness
Goal: prepare the system for university presentation.

Tasks:
- finalize Docker setup
- document local run flow
- document seed/demo accounts
- ensure sample data exists
- polish README
- optionally prepare simple production config placeholders

Deliverables:
- complete README
- demo startup instructions
- known limitations section

Success criteria:
- another developer can clone and run the app with clear instructions
- demo scenario works end-to-end

---

## Constraints and Important Rules for the AI Agent
1. Build the system as an MVP, but do not use messy shortcut architecture.
2. Keep the prediction layer swappable.
3. Do not hardcode business logic inside frontend pages.
4. Do not couple alert generation tightly to route handlers.
5. Preserve clear role-based authorization rules.
6. Prefer readable code over overengineered abstractions.
7. Include sample seed data for all roles and several patients.
8. Make charts and dashboards demo-friendly.
9. Use a configurable threshold from the database/admin settings, not a hardcoded constant.
10. Assume device data is simulated first, not connected to real medical hardware.

---

## Suggested Demo Seed Data
Generate seed data for:
- 1 admin user
- 2 doctors
- 2 nurses
- 8 to 12 demo patients
- a mix of admitted, discharged, and transferred patients
- assigned doctor relationships
- historical vitals
- sample predictions
- sample unread and read alerts

---

## Future Extension Notes
Design now so the following can be added later:
- real PyTorch `.pt` LSTM model loading
- inference API integration
- websocket/live updates
- cloud deployment
- audit logs
- device integration
- advanced alert tuning
- analytics and reporting

---

## Final Output the AI Agent Must Produce
The AI agent should generate:
- backend folder structure
- frontend folder structure
- database models and migrations
- API endpoints
- React pages and components
- role-based auth flow
- seed data scripts
- Docker setup
- README
- test files

The generated code should be runnable locally and optimized for a university demo while remaining structured enough for future real-world extension.
