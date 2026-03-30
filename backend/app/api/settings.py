from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.prediction import SettingResponse, SettingUpdate
from app.services.settings_service import get_all_settings, get_setting, update_setting
from app.dependencies.auth import require_role
from app.models.user import User

router = APIRouter()


@router.get("/", response_model=list[SettingResponse])
def list_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Get all system settings (admin only)."""
    return get_all_settings(db)


@router.get("/threshold")
def get_threshold(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Get the current high-risk threshold."""
    value = get_setting(db, "high_risk_threshold", "0.80")
    return {"key": "high_risk_threshold", "value": value}


@router.put("/threshold")
def update_threshold(
    request: SettingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    """Update the high-risk threshold (admin only)."""
    # Validate the value
    try:
        val = float(request.value)
        if not (0.0 < val < 1.0):
            raise ValueError
    except ValueError:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Threshold must be a number between 0 and 1"
        )

    setting = update_setting(db, "high_risk_threshold", request.value, current_user.user_id)
    return {"message": "Threshold updated", "value": setting.value}
