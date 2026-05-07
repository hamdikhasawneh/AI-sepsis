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
from app.models.transformer_arch import DynamicSurvivalTransformer

logger = logging.getLogger(__name__)

# ── DST v2 model file paths ───────────────────────────────────
MODEL_PATH           = "app/models/ml_files/dst_best.pt"
CALIBRATOR_PATH      = "app/models/ml_files/dst_calibrators.pkl"
SCALER_PATH          = "app/models/ml_files/dst_scaler.pkl"
VITAL_WINSOR_LO_PATH = "app/models/ml_files/dst_vital_winsor_lo.npy"
VITAL_WINSOR_HI_PATH = "app/models/ml_files/dst_vital_winsor_hi.npy"
STATIC_WINSOR_LO_PATH= "app/models/ml_files/dst_winsor_lo.npy"
STATIC_WINSOR_HI_PATH= "app/models/ml_files/dst_winsor_hi.npy"
SHAP_VALUES_PATH     = "app/models/ml_files/dst_shap_values.npy"
SHAP_STAY_IDS_PATH   = "app/models/ml_files/dst_shap_stay_ids.npy"
FEATURE_COLS_PATH    = "app/models/ml_files/dst_feature_cols.txt"

NUM_BINS   = 48
MAX_HOURS  = 200
time_cuts  = np.linspace(0, MAX_HOURS, NUM_BINS + 1)[1:]

# Bin index for 12h horizon
BIN_12H = int(np.clip(np.searchsorted(time_cuts, 12, "right"), 0, NUM_BINS - 1))

# Alert tiers
ALERT_THRESHOLDS = {
    "no_alert"  : (0.00, 0.50),
    "high_risk" : (0.50, 0.70),
    "critical"  : (0.70, 1.00),
}

# Vital feature medians for imputation (25 features matching X_rich_full)
VITAL_MEDIANS = np.array([
    80.0, 18.0, 37.0, 97.0, 115.0, 65.0, 80.0,
    1.5, 8.0, 200.0, 0.7, 1.1, 60.0,
    120.0, 12.0, 4.0, 140.0, 105.0, 24.0,
    15.0, 7.4, 40.0, 90.0, 0.21, 60.0,
], dtype=np.float32)


def get_alert_tier(score: float) -> str:
    if score >= 0.70:
        return "critical"
    elif score >= 0.50:
        return "high_risk"
    else:
        return "no_alert"


def apply_platt_calibration(surv: np.ndarray, calibrators: dict, num_bins: int = NUM_BINS) -> np.ndarray:
    """Apply Platt scaling (LogisticRegression) calibration to survival curves."""
    surv_cal = surv.copy()
    cal_t_indices = sorted(calibrators.keys())
    for t_idx in cal_t_indices:
        lr = calibrators[t_idx]
        pred_cif = (1 - surv_cal[:, t_idx]).clip(0, 1).reshape(-1, 1)
        cal_cif = lr.predict_proba(pred_cif)[:, 1].clip(0, 1)
        surv_cal[:, t_idx] = 1 - cal_cif
    for t in range(num_bins):
        if t not in calibrators:
            lo = max([k for k in cal_t_indices if k <= t], default=None)
            hi = min([k for k in cal_t_indices if k >= t], default=None)
            if lo is not None and hi is not None and lo != hi:
                w = (t - lo) / (hi - lo)
                surv_cal[:, t] = (1 - w) * surv_cal[:, lo] + w * surv_cal[:, hi]
            elif lo is not None:
                surv_cal[:, t] = surv_cal[:, lo]
            elif hi is not None:
                surv_cal[:, t] = surv_cal[:, hi]
    for t in range(1, num_bins):
        surv_cal[:, t] = np.minimum(surv_cal[:, t], surv_cal[:, t - 1])
    return surv_cal


class BasePredictorService(ABC):
    @abstractmethod
    def predict(self, vitals_window: list[dict], patient_static: dict = None) -> float:
        pass


class DSTPredictorService(BasePredictorService):
    """
    DST v2 prediction service.
    Uses DynamicSurvivalTransformer with Platt scaling calibration.
    Growing window: feeds all available vitals from admission to current hour.
    """
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.calibrators = None
        self.scaler = None
        self.vital_lo = None
        self.vital_hi = None
        self.static_lo = None
        self.static_hi = None
        self.load_model()

    def load_model(self):
        if not os.path.exists(MODEL_PATH):
            logger.warning(f"DST model not found at {MODEL_PATH}. Falling back to mock.")
            return
        try:
            self.model = DynamicSurvivalTransformer(
                vital_dim=25,
                static_dim=127,
                d_model=256,
                nhead=8,
                n_layers=3,
                static_hidden=128,
                fusion_hidden=256,
                num_bins=NUM_BINS,
                dropout=0.2,
                max_seq_len=MAX_HOURS,
            ).to(self.device)
            self.model.load_state_dict(
                torch.load(MODEL_PATH, map_location=self.device, weights_only=True)
            )
            self.model.eval()
            logger.info("DST v2 model loaded successfully.")

            if os.path.exists(CALIBRATOR_PATH):
                self.calibrators = joblib.load(CALIBRATOR_PATH)
                logger.info(f"Platt calibrators loaded: {len(self.calibrators)} time points.")

            if os.path.exists(SCALER_PATH):
                self.scaler = joblib.load(SCALER_PATH)
                logger.info("StandardScaler loaded.")

            if os.path.exists(VITAL_WINSOR_LO_PATH):
                self.vital_lo = np.load(VITAL_WINSOR_LO_PATH)
                self.vital_hi = np.load(VITAL_WINSOR_HI_PATH)
                logger.info("Vital winsorisation bounds loaded.")

            if os.path.exists(STATIC_WINSOR_LO_PATH):
                self.static_lo = np.load(STATIC_WINSOR_LO_PATH)
                self.static_hi = np.load(STATIC_WINSOR_HI_PATH)
                logger.info("Static winsorisation bounds loaded.")

        except Exception as e:
            logger.error(f"Error loading DST v2 model: {e}")
            self.model = None

    def _preprocess_vitals(self, vitals_window: list[dict]) -> np.ndarray:
        """Convert vitals list to (T, 25) array, impute and winsorise."""
        T = len(vitals_window)
        seq = np.zeros((T, 25), dtype=np.float32)
        for i, v in enumerate(vitals_window):
            row = VITAL_MEDIANS.copy()
            row[0]  = v.get("heart_rate")       or row[0]
            row[1]  = v.get("respiratory_rate") or row[1]
            row[2]  = v.get("temperature")      or row[2]
            row[3]  = v.get("spo2")             or row[3]
            row[4]  = v.get("systolic_bp")      or row[4]
            row[5]  = v.get("diastolic_bp")     or row[5]
            row[6]  = v.get("mean_bp")          or row[6]
            seq[i] = row
        # Apply winsorisation
        if self.vital_lo is not None:
            seq = np.clip(seq, self.vital_lo, self.vital_hi)
        # Replace any remaining NaN
        seq = np.nan_to_num(seq, nan=0.0)
        return seq

    def _preprocess_static(self, patient_static: dict) -> np.ndarray:
        """Build 127-dimensional static feature vector, winsorise and scale."""
        static = np.zeros((1, 127), dtype=np.float32)
        if patient_static:
            static[0, 0] = patient_static.get("age", 0) or 0
            static[0, 1] = 1.0 if patient_static.get("gender") == "male" else 0.0
        if self.static_lo is not None:
            static = np.clip(static, self.static_lo, self.static_hi)
        if self.scaler is not None:
            static = self.scaler.transform(static)
        return static.astype(np.float32)

    def predict(self, vitals_window: list[dict], patient_static: dict = None) -> float:
        if self.model is None:
            return MockPredictorService().predict(vitals_window)
        if not vitals_window:
            return 0.0
        try:
            seq     = self._preprocess_vitals(vitals_window)
            static  = self._preprocess_static(patient_static or {})
            T       = len(seq)

            x_seq    = torch.tensor(seq, dtype=torch.float32).unsqueeze(0).to(self.device)
            x_static = torch.tensor(static, dtype=torch.float32).to(self.device)
            lengths  = torch.tensor([T], dtype=torch.long).to(self.device)

            with torch.no_grad():
                pmf = self.model(x_seq, x_static, lengths).cpu().numpy()

            surv = 1 - np.cumsum(pmf, axis=1)

            if self.calibrators:
                surv = apply_platt_calibration(surv, self.calibrators, NUM_BINS)

            risk_score = float(np.clip(1 - surv[0, BIN_12H], 0.0, 1.0))
            return round(risk_score, 4)

        except Exception as e:
            logger.error(f"DST inference error: {e}")
            return MockPredictorService().predict(vitals_window)


class MockPredictorService(BasePredictorService):
    """Mock prediction service for demo/testing when model files are absent."""

    def predict(self, vitals_window: list[dict], patient_static: dict = None) -> float:
        if not vitals_window:
            return round(random.uniform(0.1, 0.3), 4)
        latest = vitals_window[-1]
        risk = 0.0
        hr   = latest.get("heart_rate", 80)
        rr   = latest.get("respiratory_rate", 18)
        temp = latest.get("temperature", 37.0)
        spo2 = latest.get("spo2", 98)
        sbp  = latest.get("systolic_bp", 120)
        if hr   and hr > 100:   risk += (hr - 100) * 0.005
        if hr   and hr > 110:   risk += 0.1
        if rr   and rr > 22:    risk += (rr - 22) * 0.01
        if rr   and rr > 26:    risk += 0.1
        if temp and temp > 38.3:risk += (temp - 38.3) * 0.1
        if temp and temp > 39.0:risk += 0.15
        if spo2 and spo2 < 94:  risk += (94 - spo2) * 0.03
        if spo2 and spo2 < 90:  risk += 0.15
        if sbp  and sbp < 100:  risk += (100 - sbp) * 0.005
        if sbp  and sbp < 90:   risk += 0.15
        risk += random.uniform(-0.05, 0.1)
        return round(max(0.0, min(1.0, risk)), 4)


# ── Singleton accessor ────────────────────────────────────────

_predictor_instance = None


def get_predictor() -> BasePredictorService:
    global _predictor_instance
    if _predictor_instance is None:
        if os.path.exists(MODEL_PATH):
            _predictor_instance = DSTPredictorService()
        else:
            logger.warning("DST model files not found — using MockPredictorService.")
            _predictor_instance = MockPredictorService()
    return _predictor_instance


# ── Threshold and risk level ──────────────────────────────────

def get_risk_level(score: float, threshold: float) -> str:
    if score >= 0.70:
        return "critical"
    elif score >= 0.50:
        return "high_risk"
    elif score >= threshold * 0.6:
        return "medium"
    else:
        return "low"


def get_threshold(db: Session) -> float:
    setting = db.query(SystemSetting).filter(
        SystemSetting.key == "high_risk_threshold"
    ).first()
    return float(setting.value) if setting else 0.50


# ── Prediction orchestration ──────────────────────────────────

def run_prediction_for_patient(db: Session, patient_id: int) -> Prediction | None:
    from app.models.patient import Patient
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        return None

    # Growing window — fetch ALL vitals from admission (not just last 24h)
    vitals = (
        db.query(VitalSign)
        .filter(VitalSign.patient_id == patient_id)
        .order_by(VitalSign.recorded_at.asc())
        .all()
    )

    if len(vitals) < 2:
        return None

    vitals_window = [
        {
            "heart_rate":       v.heart_rate,
            "respiratory_rate": v.respiratory_rate,
            "temperature":      v.temperature,
            "spo2":             v.spo2,
            "systolic_bp":      v.systolic_bp,
            "diastolic_bp":     v.diastolic_bp,
            "mean_bp":          v.mean_bp,
        }
        for v in vitals
    ]

    patient_static  = {"age": patient.age, "gender": patient.gender}
    predictor       = get_predictor()
    risk_score      = predictor.predict(vitals_window, patient_static)
    threshold       = get_threshold(db)
    risk_level      = get_risk_level(risk_score, threshold)
    alert_tier      = get_alert_tier(risk_score)
    version         = "dst-v2" if isinstance(predictor, DSTPredictorService) else "mock-v1"

    prediction = Prediction(
        patient_id=patient_id,
        predicted_at=datetime.now(timezone.utc),
        risk_score=risk_score,
        risk_level=risk_level,
        threshold_used=threshold,
        model_version=version,
        input_window_hours=len(vitals),
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


# ── SHAP lookup for UI ────────────────────────────────────────

def get_shap_for_patient(patient_id: int) -> dict | None:
    """
    Look up precomputed GradientSHAP values for a patient.
    Returns top 8 features with their SHAP values and direction.
    """
    try:
        if not os.path.exists(SHAP_VALUES_PATH):
            return None

        shap_values   = np.load(SHAP_VALUES_PATH)
        shap_stay_ids = np.load(SHAP_STAY_IDS_PATH)

        # Find this patient in the precomputed SHAP results
        idx_arr = np.where(shap_stay_ids == patient_id)[0]
        if len(idx_arr) == 0:
            return None

        idx = idx_arr[0]
        sv  = shap_values[idx]  # (127,)

        # Load feature names
        feature_cols = []
        if os.path.exists(FEATURE_COLS_PATH):
            with open(FEATURE_COLS_PATH) as f:
                feature_cols = f.read().splitlines()
        else:
            feature_cols = [f"feature_{i}" for i in range(len(sv))]

        # Top 8 by absolute SHAP value
        top_idx = np.argsort(np.abs(sv))[::-1][:8]
        features = []
        for fi in top_idx:
            features.append({
                "feature"  : feature_cols[fi] if fi < len(feature_cols) else f"feature_{fi}",
                "shap_value": round(float(sv[fi]), 5),
                "direction": "Risk +" if sv[fi] > 0 else "Protective",
            })

        return {
            "patient_id": int(patient_id),
            "features"  : features,
        }

    except Exception as e:
        logger.error(f"SHAP lookup error for patient {patient_id}: {e}")
        return None
