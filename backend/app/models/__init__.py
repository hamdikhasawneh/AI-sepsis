# Import all models so Base.metadata.create_all() picks them up
from app.models.user import User  # noqa: F401
from app.models.patient import Patient  # noqa: F401
from app.models.vital_signs import VitalSign  # noqa: F401
from app.models.prediction import Prediction  # noqa: F401
from app.models.alert import Alert  # noqa: F401
from app.models.system_setting import SystemSetting  # noqa: F401
from app.models.task import Task  # noqa: F401
from app.models.lab_result import LabResult  # noqa: F401
from app.models.document import Document  # noqa: F401
