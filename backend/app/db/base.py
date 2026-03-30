from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models here so Alembic can see them
from app.models.user import User  # noqa: F401, E402
from app.models.patient import Patient  # noqa: F401, E402
from app.models.vital_signs import VitalSign  # noqa: F401, E402
from app.models.prediction import Prediction  # noqa: F401, E402
from app.models.alert import Alert  # noqa: F401, E402
from app.models.system_setting import SystemSetting  # noqa: F401, E402
