from __future__ import annotations
import os
import random
import logging
import joblib
import torch
import numpy as np
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models.vital_signs import VitalSign
from app.models.prediction import Prediction
from app.models.system_setting import SystemSetting
from app.models.transformer_arch import TransformerSurvival

logger = logging.getLogger(__name__)

# ─── Constants for the Real Model ─────────────────────────────
MODEL_PATH = "app/models/ml_files/transformer_all_best.pt"
CALIBRATOR_PATH = "app/models/ml_files/transformer_all_calibrators.pkl"

# These match the feature structure from notebooks/03b_transformer_only.ipynb
VITAL_MEDIANS_RICH = np.array([
    80.0, 18.0, 37.0, 97.0, 115.0, 65.0, 80.0,
    1.5, 8.0, 200.0, 0.7, 1.1, 60.0,
    120.0, 12.0, 4.0, 140.0, 105.0, 24.0,
    15.0, 7.4, 40.0, 90.0, 0.21, 60.0
], dtype=np.float32)


# ─── Predictor Interface ───

class BasePredictorService(ABC):
    """Abstract base class for prediction services."""

    @abstractmethod
    def predict(self, vitals_window: list[dict], patient_static: dict = None) -> float:
        """
        Given a window of vital sign readings, return a risk score between 0 and 1.
        """
        pass


class TransformerPredictorService(BasePredictorService):
    """
    Real Transformer-based prediction service.
    Loads PyTorch weights and performs inference.
    """
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.calibrators = None
        self.load_model()

    def load_model(self):
        if not os.path.exists(MODEL_PATH):
            logger.warning(f"Model file {MODEL_PATH} not found. Transformer service will not work.")
            return

        try:
            # Initialize architecture (static_dim 96, d_model 128 from notebook)
            self.model = TransformerSurvival(
                vital_dim=25,
                static_dim=96,
                num_bins=48
            ).to(self.device)

            # Load weights
            self.model.load_state_dict(torch.load(MODEL_PATH, map_location=self.device))
            self.model.eval()
            logger.info("Transformer model loaded successfully.")

            # Load calibrators if present
            if os.path.exists(CALIBRATOR_PATH):
                self.calibrators = joblib.load(CALIBRATOR_PATH)
                logger.info("Calibrators loaded successfully.")

        except Exception as e:
            logger.error(f"Error loading transformer model: {e}")
            self.model = None

    def _preprocess(self, vitals_window: list[dict], patient_static: dict):
        """
        Convert raw vitals list to (1, T, 25) tensor and static features to (1, 96).
        """
        # Temporal sequence (last 24 hours max)
        T = min(len(vitals_window), 25) # Model max_seq_len is 25
        seq_data = np.zeros((1, T, 25), dtype=np.float32)

        for i in range(T):
            v = vitals_window[-(T-i)]
            row = VITAL_MEDIANS_RICH.copy()
            row[0] = v.get("heart_rate") or row[0]
            row[1] = v.get("respiratory_rate") or row[1]
            row[2] = v.get("temperature") or row[2]
            row[3] = v.get("spo2") or row[3]
            row[4] = v.get("systolic_bp") or row[4]
            row[5] = v.get("diastolic_bp") or row[5]
            row[6] = v.get("mean_bp") or row[6]
            if patient_static:
                row[24] = patient_static.get("age") or row[24]

            seq_data[0, i, :] = row

        # Static features (96 dims)
        static_data = np.zeros((1, 96), dtype=np.float32)
        if patient_static:
            static_data[0, 0] = patient_static.get("age", 0)
            static_data[0, 1] = 1 if patient_static.get("gender") == "male" else 0

        return (
            torch.tensor(seq_data).to(self.device),
            torch.tensor(static_data).to(self.device),
            torch.tensor([T]).to(self.device)
        )

    def predict(self, vitals_window: list[dict], patient_static: dict = None) -> float:
        if self.model is None:
            # Fallback to internal mock if files missing
            return MockPredictorService().predict(vitals_window)

        try:
            x_seq, x_static, lengths = self._preprocess(vitals_window, patient_static)

            with torch.no_grad():
                pmf = self.model(x_seq, x_static, lengths)
                # PMF is over 48 bins. We predict risk in next ~12 hours.
                risk_score = torch.sum(pmf[0, :12]).item()

            if self.calibrators and 12 in self.calibrators:
                iso = self.calibrators[12]
                risk_score = float(iso.predict([risk_score])[0])

            return round(max(0.0, min(1.0, risk_score)), 4)

        except Exception as e:
            logger.error(f"Inference error: {e}")
            return MockPredictorService().predict(vitals_window)


class MockPredictorService(BasePredictorService):
    """
    Mock prediction service for demo purposes.
    Generates semi-realistic risk scores based on vital sign patterns.
    """

    def predict(self, vitals_window: list[dict], patient_static: dict = None) -> float:
        if not vitals_window:
            return round(random.uniform(0.1, 0.3), 4)

        latest = vitals_window[-1]
        risk = 0.0

        hr = latest.get("heart_rate", 80)
        rr = latest.get("respiratory_rate", 18)
        temp = latest.get("temperature", 37.0)
        spo2 = latest.get("spo2", 98)
        sbp = latest.get("systolic_bp", 120)

        if hr and hr > 100: risk += (hr - 100) * 0.005
        if hr and hr > 110: risk += 0.1
        if rr and rr > 22: risk += (rr - 22) * 0.01
        if rr and rr > 26: risk += 0.1
        if temp and temp > 38.3: risk += (temp - 38.3) * 0.1
        if temp and temp > 39.0: risk += 0.15
        if spo2 and spo2 < 94: risk += (94 - spo2) * 0.03
        if spo2 and spo2 < 90: risk += 0.15
        if sbp and sbp < 100: risk += (100 - sbp) * 0.005
        if sbp and sbp < 90: risk += 0.15

        risk += random.uniform(-0.05, 0.1)
        return round(max(0.0, min(1.0, risk)), 4)


# ─── Singleton accessor ───

_predictor_instance = None


def get_predictor() -> BasePredictorService:
    global _predictor_instance
    if _predictor_instance is None:
        if os.path.exists(MODEL_PATH):
            _predictor_instance = TransformerPredictorService()
        else:
            _predictor_instance = MockPredictorService()
    return _predictor_instance


# ─── Prediction orchestration ───

def get_risk_level(score: float, threshold: float) -> str:
    if score >= threshold:
        return "critical" if score >= 0.9 else "high"
    elif score >= threshold * 0.6:
        return "medium"
    else:
        return "low"


def get_threshold(db: Session) -> float:
    setting = db.query(SystemSetting).filter(SystemSetting.key == "high_risk_threshold").first()
    if setting:
        return float(setting.value)
    return 0.80


def run_prediction_for_patient(db: Session, patient_id: int) -> Prediction | None:
    from app.models.patient import Patient
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        return None

    # Fetch last 24 hours of vitals
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    vitals = (
        db.query(VitalSign)
        .filter(VitalSign.patient_id == patient_id, VitalSign.recorded_at >= cutoff)
        .order_by(VitalSign.recorded_at.asc())
        .all()
    )

    if len(vitals) < 2:
        return None

    vitals_window = [
        {
            "heart_rate": v.heart_rate,
            "respiratory_rate": v.respiratory_rate,
            "temperature": v.temperature,
            "spo2": v.spo2,
            "systolic_bp": v.systolic_bp,
            "diastolic_bp": v.diastolic_bp,
            "mean_bp": v.mean_bp,
        }
        for v in vitals
    ]

    patient_static = {"age": patient.age, "gender": patient.gender}
    predictor = get_predictor()
    risk_score = predictor.predict(vitals_window, patient_static)
    threshold = get_threshold(db)
    risk_level = get_risk_level(risk_score, threshold)

    version = "transformer-v1" if isinstance(predictor, TransformerPredictorService) else "mock-v1"
    prediction = Prediction(
        patient_id=patient_id,
        predicted_at=datetime.now(timezone.utc),
        risk_score=risk_score,
        risk_level=risk_level,
        threshold_used=threshold,
        model_version=version,
        input_window_hours=24,
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


def get_patient_predictions(db: Session, patient_id: int, limit: int = 20):
    return (
        db.query(Prediction)
        .filter(Prediction.patient_id == patient_id)
        .order_by(Prediction.predicted_at.desc())
        .limit(limit)
        .all()
    )


def get_latest_prediction(db: Session, patient_id: int) -> Prediction | None:
    return (
        db.query(Prediction)
        .filter(Prediction.patient_id == patient_id)
        .order_by(Prediction.predicted_at.desc())
        .first()
    )
