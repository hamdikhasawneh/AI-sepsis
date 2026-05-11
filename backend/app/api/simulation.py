from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_role
from app.models.user import User
from app.services.simulation_service import simulation_service
from app.core.config import settings
import os

router = APIRouter()

@router.get("/cases")
def list_cases(
    current_user: User = Depends(get_current_user),
):
    """List available cases from the Excel file."""
    if not os.path.exists(settings.SIMULATION_EXCEL_PATH):
        raise HTTPException(status_code=404, detail="Excel file not found at " + settings.SIMULATION_EXCEL_PATH)
    
    try:
        simulation_service.load_data()
        if simulation_service.static_data is None:
            return {"cases": []}
        cases = simulation_service.static_data['case_name'].unique().tolist()
        return {"cases": cases}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
def get_simulation_status(
    current_user: User = Depends(get_current_user),
):
    """Get the status of the current simulation."""
    return simulation_service.get_status()

@router.post("/start")
async def start_simulation(
    case_name: str,
    current_user: User = Depends(require_role("admin", "doctor")),
):
    """Start simulation for a specific case."""
    success = await simulation_service.start(case_name)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to start simulation")
    return {"message": f"Simulation started for {case_name}"}

@router.post("/stop")
def stop_simulation(
    current_user: User = Depends(require_role("admin", "doctor")),
):
    """Stop the current simulation."""
    simulation_service.stop()
    return {"message": "Simulation stopped"}
