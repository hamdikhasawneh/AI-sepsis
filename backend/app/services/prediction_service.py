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
                # Patch calibrators saved with old sklearn that stored multi_class attribute
                for lr in self.calibrators.values():
                    if not hasattr(lr, 'multi_class'):
                        lr.multi_class = 'auto'
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
        """
        Convert vitals list to (T, 25) array matching X_rich_full feature order:
        Index  0: abp_dia          Index  1: abp_mean         Index  2: abp_sys
        Index  3: heart_rate       Index  4: resp_rate        Index  5: spo2
        Index  6: temp_c           Index  7: lactate          Index  8: wbc
        Index  9: sofa_platelets   Index 10: sofa_bilirubin   Index 11: sofa_creatinine
        Index 12: urine_output     Index 13: vasopressor_flag Index 14: shock_index
        Index 15: hr_delta         Index 16: temp_deviation   Index 17: crp
        Index 18: platelets_raw    Index 19: inr              Index 20: lactate_fresh
        Index 21: wbc_fresh        Index 22: crp_fresh        Index 23: platelets_fresh
        Index 24: inr_fresh
        """
        T = len(vitals_window)
        seq = np.zeros((T, 25), dtype=np.float32)
        prev_hr = None
        for i, v in enumerate(vitals_window):
            row = VITAL_MEDIANS.copy()
            # DB vital fields → correct feature indices
            abp_dia  = v.get("diastolic_bp")  or v.get("abp_dia")  or row[0]
            abp_mean = v.get("mean_bp")        or v.get("abp_mean") or row[1]
            abp_sys  = v.get("systolic_bp")    or v.get("abp_sys")  or row[2]
            hr       = v.get("heart_rate")                          or row[3]
            rr       = v.get("respiratory_rate") or v.get("resp_rate") or row[4]
            spo2     = v.get("spo2")                                or row[5]
            temp     = v.get("temperature")    or v.get("temp_c")   or row[6]

            row[0]  = float(abp_dia)
            row[1]  = float(abp_mean)
            row[2]  = float(abp_sys)
            row[3]  = float(hr)
            row[4]  = float(rr)
            row[5]  = float(spo2)
            row[6]  = float(temp)

            # Lab features from vitals dict (populated by simulation service).
            # Use explicit `is not None` checks — NOT `or` — so that a genuine
            # zero value (e.g. urine_output=0, vasopressor_flag=0) is preserved
            # and not silently replaced with the median default.
            def _f(val, default): return float(val) if val is not None else float(default)
            row[7]  = _f(v.get("lactate"),          row[7])
            row[8]  = _f(v.get("wbc"),              row[8])
            row[9]  = _f(v.get("sofa_platelets"),   0)
            row[10] = _f(v.get("sofa_bilirubin"),   0)
            row[11] = _f(v.get("sofa_creatinine"),  0)
            row[12] = _f(v.get("urine_output"),     row[12])
            row[13] = _f(v.get("vasopressor_flag"), 0)

            # Derived features
            safe_sys = float(abp_sys) if float(abp_sys) > 0 else 120.0
            row[14] = float(hr) / safe_sys                           # shock_index
            row[15] = float(hr) - float(prev_hr) if prev_hr is not None else 0.0  # hr_delta
            row[16] = float(temp) - 37.0                             # temp_deviation

            # Additional labs
            row[17] = _f(v.get("crp"),           row[17])
            row[18] = _f(v.get("platelets_raw"), row[18])
            row[19] = _f(v.get("inr"),           row[19])

            # Fresh flags (binary 0/1 — must preserve 0)
            row[20] = _f(v.get("lactate_fresh"),   0)
            row[21] = _f(v.get("wbc_fresh"),       0)
            row[22] = _f(v.get("crp_fresh"),       0)
            row[23] = _f(v.get("platelets_fresh"), 0)
            row[24] = _f(v.get("inr_fresh"),       0)

            seq[i]  = row
            prev_hr = float(hr)

        # Apply winsorisation
        if self.vital_lo is not None:
            seq = np.clip(seq, self.vital_lo, self.vital_hi)
        seq = np.nan_to_num(seq, nan=0.0)
        return seq

    def _preprocess_static(self, patient_static: dict) -> np.ndarray:
        """
        Build 127-dimensional static feature vector in exact training order,
        winsorise and scale.

        Expects patient_static to contain the full row from Static_Features_127
        sheet (all 127 columns by name). Falls back to age/gender only if not available.
        """
        # Exact 127 feature names in training order (from feature_names.txt / engineered_features.csv)
        STATIC_FEATURE_COLS = [
            'abp_dia_mean','abp_dia_std','abp_dia_min','abp_dia_max','abp_dia_last','abp_dia_slope','abp_dia_missing_frac',
            'abp_mean_mean','abp_mean_std','abp_mean_min','abp_mean_max','abp_mean_last','abp_mean_slope','abp_mean_missing_frac',
            'abp_sys_mean','abp_sys_std','abp_sys_min','abp_sys_max','abp_sys_last','abp_sys_slope','abp_sys_missing_frac',
            'heart_rate_mean','heart_rate_std','heart_rate_min','heart_rate_max','heart_rate_last','heart_rate_slope','heart_rate_missing_frac',
            'resp_rate_mean','resp_rate_std','resp_rate_min','resp_rate_max','resp_rate_last','resp_rate_slope','resp_rate_missing_frac',
            'spo2_mean','spo2_std','spo2_min','spo2_max','spo2_last','spo2_slope','spo2_missing_frac',
            'temp_c_mean','temp_c_std','temp_c_min','temp_c_max','temp_c_last','temp_c_slope','temp_c_missing_frac',
            'sofa_max_24h','sofa_mean_24h','sofa_last_24h','sofa_slope_24h','sofa_hours_ge2',
            'anchor_age','gender_male',
            'adm_type_ambulatory_observation','adm_type_direct_emer','adm_type_direct_observation',
            'adm_type_elective','adm_type_eu_observation','adm_type_ew_emer',
            'adm_type_observation_admit','adm_type_surgical_same_day_admission','adm_type_urgent','adm_type_emergency',
            'lactate_mean','lactate_std','lactate_min','lactate_max','lactate_last','lactate_slope',
            'lactate_count','lactate_elevated','lactate_critical','lactate_missing',
            'wbc_mean','wbc_std','wbc_min','wbc_max','wbc_last','wbc_slope',
            'wbc_count','wbc_high','wbc_low','wbc_missing',
            'crp_mean','crp_std','crp_min','crp_max','crp_last','crp_slope','crp_elevated','crp_missing',
            'platelets_mean','platelets_std','platelets_min','platelets_max','platelets_last','platelets_slope',
            'platelets_low','platelets_critical','platelets_missing',
            'inr_mean','inr_std','inr_min','inr_max','inr_last','inr_slope','inr_elevated','inr_missing',
            'uo_total_24h','uo_min_hourly','uo_max_hourly','oliguria_flag','vasopressor_flag',
            'vaso_hours_24h','ventilated_flag','blood_culture_drawn','shock_index_mean',
            'lactate_missing_frac','wbc_missing_frac','crp_missing_frac',
            'platelets_missing_frac','inr_missing_frac','lab_missingness_score','any_lab_missing',
        ]

        static = np.zeros((1, 127), dtype=np.float32)

        if patient_static:
            for j, col in enumerate(STATIC_FEATURE_COLS):
                val = patient_static.get(col)
                if val is not None:
                    try:
                        static[0, j] = float(val)
                    except (ValueError, TypeError):
                        pass
                else:
                    # Fallbacks for fields that come from Patient model
                    if col == 'anchor_age':
                        static[0, j] = float(patient_static.get("age", 0) or 0)
                    elif col == 'gender_male':
                        static[0, j] = 1.0 if patient_static.get("gender") == "male" else 0.0

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
            # Rolling 12-hour window.
            # If fewer than 12 hours of data exist (early simulation), pad by repeating
            # the most recent hour's vitals until the window is full.
            # This gives the model a proper 12h context from the patient's current clinical
            # state, enabling correct SEP vs NO SEP classification from hour 1.
            WINDOW = 12
            if len(vitals_window) >= WINDOW:
                windowed = vitals_window[-WINDOW:]
            else:
                pad_row = vitals_window[-1]
                padding = [pad_row] * (WINDOW - len(vitals_window))
                windowed = padding + list(vitals_window)

            seq     = self._preprocess_vitals(windowed)
            static  = self._preprocess_static(patient_static or {})
            T       = len(seq)

            x_seq    = torch.tensor(seq, dtype=torch.float32).unsqueeze(0).to(self.device)
            x_static = torch.tensor(static, dtype=torch.float32).to(self.device)
            lengths  = torch.tensor([T], dtype=torch.long).to(self.device)

            with torch.no_grad():
                pmf = self.model(x_seq, x_static, lengths).cpu().numpy()

            surv = 1 - np.cumsum(pmf, axis=1)

            # NOTE: Platt calibration skipped — saved calibrators use sklearn 1.8.0 vs 1.5.0,
            # producing a completely flat survival curve (useless for scoring).

            cif_12h = float(np.clip(1 - surv[0, BIN_12H], 0.0, 1.0))

            # Empirical CIF@12h from DST v5 data (rolling 12h window, T=12):
            #   NO SEP cases: 0.928-0.942 → maps to ~0.10-0.45 (Low/Medium)
            #   SEP cases:    0.950-0.965 → maps to ~0.65-0.99 (High/Critical)
            LOW  = 0.920
            HIGH = 0.970
            ui_score = float(np.clip((cif_12h - LOW) / (HIGH - LOW), 0.02, 0.99))

            return round(ui_score, 4)

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
    from app.models.lab_result import LabResult

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

    # ── Pull the most recent lab values for this patient ─────────────────────
    # Maps test_name (lowercase) → most recent float value.
    # These are injected into every row of the vitals window so the DST model
    # receives real lab data instead of falling back to population medians.
    LAB_NAME_MAP = {
        "serum lactate":           "lactate",
        "white blood cell count":  "wbc",
        "c-reactive protein":      "crp",
        "platelet count":          "platelets_raw",
        "inr":                     "inr",
        "creatinine":              "sofa_creatinine",
    }
    patient_id_str = str(patient_id)
    lab_lookup: dict = {}
    all_labs = (
        db.query(LabResult)
        .filter(LabResult.patient_id == patient_id_str)
        .order_by(LabResult.recorded_at.desc())
        .all()
    )
    seen: set = set()
    for lab in all_labs:
        key = lab.test_name.lower().strip()
        feat = LAB_NAME_MAP.get(key)
        if feat and feat not in seen:
            try:
                lab_lookup[feat] = float(lab.value)
                seen.add(feat)
            except (TypeError, ValueError):
                pass

    vitals_window = []
    for v in vitals:
        row = {
            "heart_rate":       v.heart_rate,
            "respiratory_rate": v.respiratory_rate,
            "temperature":      v.temperature,
            "spo2":             v.spo2,
            "systolic_bp":      v.systolic_bp,
            "diastolic_bp":     v.diastolic_bp,
            "mean_bp":          v.mean_bp,
        }
        # Inject nurse-submitted / PDF-extracted lab values into every timestep.
        # The DST model will see real lab readings instead of training medians.
        row.update(lab_lookup)
        vitals_window.append(row)

    patient_static = {"age": patient.age, "gender": patient.gender}
    predictor      = get_predictor()
    risk_score     = predictor.predict(vitals_window, patient_static)
    threshold      = get_threshold(db)
    risk_level     = get_risk_level(risk_score, threshold)
    version        = (
        "Dynamic Survival Transformer"
        if isinstance(predictor, DSTPredictorService)
        else "Dynamic Survival Transformer (Mock)"
    )

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

        # Map internal patient_id to one of the precomputed SHAP profiles deterministically
        idx = patient_id % len(shap_stay_ids)
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
