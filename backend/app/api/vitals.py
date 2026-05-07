from __future__ import annotations
import asyncio
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.vital_signs import VitalCreate, VitalResponse
from app.services.vital_service import create_vital, get_patient_vitals, generate_simulated_vitals
from app.services.prediction_service import run_prediction_for_patient
from app.services.alert_service import check_and_create_alert
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User

router = APIRouter()

# Track whether the simulator is running
_simulator_running = False
_simulator_interval = 60  # seconds


@router.post("/", response_model=VitalResponse)
def add_vital(
    request: VitalCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin", "nurse")),
):
    """Add a manual vital sign entry (nurse or admin). Triggers prediction pipeline."""
    data = request.model_dump()
    data["source"] = "manual"
    vital = create_vital(db, data, entered_by_user_id=current_user.user_id)

    # Trigger prediction pipeline in background
    background_tasks.add_task(_run_prediction_pipeline, request.patient_id)

    return vital


def _run_prediction_pipeline(patient_id: int):
    """Run prediction and alert check for a patient."""
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        prediction = run_prediction_for_patient(db, patient_id)
        if prediction:
            check_and_create_alert(db, prediction)
    except Exception as e:
        print(f"[Prediction] Error for patient {patient_id}: {e}")
    finally:
        db.close()


@router.get("/{patient_id}", response_model=list[VitalResponse])
def list_patient_vitals(
    patient_id: int,
    hours: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get vital signs for a patient."""
    return get_patient_vitals(db, patient_id, hours)


@router.post("/simulate")
def simulate_vitals(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Trigger one cycle of simulated vital generation + predictions for all admitted patients."""
    count = generate_simulated_vitals(db)

    # Run predictions for all admitted patients
    from app.models.patient import Patient
    admitted = db.query(Patient).filter(Patient.status == "admitted").all()
    alerts_created = 0
    for patient in admitted:
        prediction = run_prediction_for_patient(db, patient.patient_id)
        if prediction:
            alert = check_and_create_alert(db, prediction)
            if alert:
                alerts_created += 1

    return {
        "message": f"Generated vitals for {count} patients, created {alerts_created} alerts"
    }


@router.post("/simulator/start")
async def start_simulator(
    current_user: User = Depends(require_role("admin")),
):
    """Start the background vital sign simulator (configurable interval)."""
    global _simulator_running
    if _simulator_running:
        return {"message": "Simulator is already running", "interval": _simulator_interval}

    _simulator_running = True

    async def run_simulator():
        global _simulator_running
        from app.db.session import SessionLocal
        from app.models.patient import Patient
        while _simulator_running:
            try:
                db = SessionLocal()
                count = generate_simulated_vitals(db)

                # Run predictions for all admitted patients
                admitted = db.query(Patient).filter(Patient.status == "admitted").all()
                alerts_created = 0
                for patient in admitted:
                    prediction = run_prediction_for_patient(db, patient.patient_id)
                    if prediction:
                        alert = check_and_create_alert(db, prediction)
                        if alert:
                            alerts_created += 1

                db.close()
                print(f"[Simulator] Vitals for {count} patients, {alerts_created} alerts created")
            except Exception as e:
                print(f"[Simulator] Error: {e}")
            await asyncio.sleep(_simulator_interval)

    asyncio.create_task(run_simulator())
    return {"message": f"Simulator started ({_simulator_interval}s interval)"}


@router.post("/simulator/stop")
def stop_simulator(
    current_user: User = Depends(require_role("admin")),
):
    """Stop the background vital sign simulator."""
    global _simulator_running
    _simulator_running = False
    return {"message": "Simulator stopped"}


@router.get("/simulator/status")
def simulator_status(
    current_user: User = Depends(require_role("admin")),
):
    """Get simulator status."""
    return {
        "running": _simulator_running,
        "interval_seconds": _simulator_interval,
    }


@router.put("/simulator/interval")
def set_simulator_interval(
    interval: int = 60,
    current_user: User = Depends(require_role("admin")),
):
    """Set simulator interval in seconds (applied on next start)."""
    global _simulator_interval
    if interval < 10:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=400, detail="Interval must be at least 10 seconds")
    _simulator_interval = interval
    return {"message": f"Interval set to {interval}s", "interval_seconds": _simulator_interval}
