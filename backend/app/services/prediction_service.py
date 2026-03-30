"""
Prediction Service Interface and Mock Implementation.

This module provides a clean abstraction for sepsis risk prediction.
The interface can be swapped to use:
  - A real PyTorch .pt LSTM model
  - An external inference API
  - Any other ML backend

To replace the mock predictor:
  1. Create a new class implementing the predict() method
  2. Change get_predictor() to return your new class
"""

import random
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models.vital_signs import VitalSign
from app.models.prediction import Prediction
from app.models.system_setting import SystemSetting


# ─── Predictor Interface ───

class BasePredictorService(ABC):
    """Abstract base class for prediction services."""

    @abstractmethod
    def predict(self, vitals_window: list[dict]) -> float:
        """
        Given a window of vital sign readings, return a risk score between 0 and 1.

        Args:
            vitals_window: List of dicts with keys: heart_rate, respiratory_rate,
                          temperature, spo2, systolic_bp, diastolic_bp, mean_bp

        Returns:
            Float between 0.0 (low risk) and 1.0 (critical risk)
        """
        pass


class MockPredictorService(BasePredictorService):
    """
    Mock prediction service for demo purposes.
    Generates semi-realistic risk scores based on vital sign patterns.
    """

    def predict(self, vitals_window: list[dict]) -> float:
        if not vitals_window:
            return round(random.uniform(0.1, 0.3), 4)

        latest = vitals_window[-1]
        risk = 0.0

        # Analyze vital signs for risk factors
        hr = latest.get("heart_rate", 80)
        rr = latest.get("respiratory_rate", 18)
        temp = latest.get("temperature", 37.0)
        spo2 = latest.get("spo2", 98)
        sbp = latest.get("systolic_bp", 120)

        # Tachycardia (high HR)
        if hr and hr > 100:
            risk += (hr - 100) * 0.005
        if hr and hr > 110:
            risk += 0.1

        # Tachypnea (high RR)
        if rr and rr > 22:
            risk += (rr - 22) * 0.01
        if rr and rr > 26:
            risk += 0.1

        # Fever
        if temp and temp > 38.3:
            risk += (temp - 38.3) * 0.1
        if temp and temp > 39.0:
            risk += 0.15

        # Hypoxemia
        if spo2 and spo2 < 94:
            risk += (94 - spo2) * 0.03
        if spo2 and spo2 < 90:
            risk += 0.15

        # Hypotension
        if sbp and sbp < 100:
            risk += (100 - sbp) * 0.005
        if sbp and sbp < 90:
            risk += 0.15

        # Add some randomness
        risk += random.uniform(-0.05, 0.1)

        # Clamp between 0 and 1
        return round(max(0.0, min(1.0, risk)), 4)


# ─── Singleton accessor ───

_predictor_instance = None


def get_predictor() -> BasePredictorService:
    """
    Get the current predictor service instance.
    To swap to a real model, change this function.
    """
    global _predictor_instance
    if _predictor_instance is None:
        _predictor_instance = MockPredictorService()
    return _predictor_instance


# ─── Prediction orchestration ───

def get_risk_level(score: float, threshold: float) -> str:
    """Convert a risk score to a human-readable level."""
    if score >= threshold:
        return "critical" if score >= 0.9 else "high"
    elif score >= threshold * 0.6:
        return "medium"
    else:
        return "low"


def get_threshold(db: Session) -> float:
    """Get the current high risk threshold from system settings."""
    setting = db.query(SystemSetting).filter(SystemSetting.key == "high_risk_threshold").first()
    if setting:
        return float(setting.value)
    return 0.80  # default


def run_prediction_for_patient(db: Session, patient_id: int) -> Prediction | None:
    """
    Run the full prediction pipeline for a patient:
    1. Fetch last 6 hours of vitals
    2. Check if enough data exists
    3. Run the predictor
    4. Store the prediction record
    5. Return the prediction (alert generation is separate)
    """
    # Fetch last 6 hours of vitals
    cutoff = datetime.now(timezone.utc) - timedelta(hours=6)
    vitals = (
        db.query(VitalSign)
        .filter(VitalSign.patient_id == patient_id, VitalSign.recorded_at >= cutoff)
        .order_by(VitalSign.recorded_at.asc())
        .all()
    )

    # Need at least 2 readings to make a meaningful prediction
    if len(vitals) < 2:
        return None

    # Prepare input for predictor
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

    # Run prediction
    predictor = get_predictor()
    risk_score = predictor.predict(vitals_window)

    # Get threshold
    threshold = get_threshold(db)
    risk_level = get_risk_level(risk_score, threshold)

    # Store prediction
    prediction = Prediction(
        patient_id=patient_id,
        predicted_at=datetime.now(timezone.utc),
        risk_score=risk_score,
        risk_level=risk_level,
        threshold_used=threshold,
        model_version="mock-v1",
        input_window_hours=6,
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)

    return prediction


def get_patient_predictions(db: Session, patient_id: int, limit: int = 20):
    """Get prediction history for a patient."""
    return (
        db.query(Prediction)
        .filter(Prediction.patient_id == patient_id)
        .order_by(Prediction.predicted_at.desc())
        .limit(limit)
        .all()
    )


def get_latest_prediction(db: Session, patient_id: int) -> Prediction | None:
    """Get the latest prediction for a patient."""
    return (
        db.query(Prediction)
        .filter(Prediction.patient_id == patient_id)
        .order_by(Prediction.predicted_at.desc())
        .first()
    )
