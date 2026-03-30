"""Settings service for system configuration management."""

from sqlalchemy.orm import Session
from app.models.system_setting import SystemSetting


def get_setting(db: Session, key: str, default: str = "") -> str:
    """Get a system setting by key."""
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    return setting.value if setting else default


def update_setting(db: Session, key: str, value: str, updated_by_user_id: int) -> SystemSetting:
    """Update or create a system setting."""
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()

    if setting:
        setting.value = value
        setting.updated_by_user_id = updated_by_user_id
    else:
        setting = SystemSetting(
            key=key,
            value=value,
            updated_by_user_id=updated_by_user_id,
        )
        db.add(setting)

    db.commit()
    db.refresh(setting)
    return setting


def get_all_settings(db: Session) -> list[dict]:
    """Get all system settings."""
    settings = db.query(SystemSetting).all()
    return [
        {
            "setting_id": s.setting_id,
            "key": s.key,
            "value": s.value,
            "updated_at": s.updated_at,
        }
        for s in settings
    ]
