# Label Definition (Sepsis)

## Goal
Predict the onset of sepsis in ICU patients using MIMIC-IV data with a high-fidelity deep learning architecture.

## Sepsis Definition
- **Standard:** Sepsis-3 (suspected infection + organ dysfunction).
- **Operational Definition:** Onset is defined as the time when both a blood culture is drawn and a new antibiotic is administered (within a ±24h window), accompanied by an increase in SOFA score ≥ 2 points.
- **Target Horizon:** The model predicts the probability of sepsis onset within the **next 12 hours**.

## Prediction Task
- **Input Window:** Rolling 12-hour window of vital signs and laboratory results.
- **Dynamic Context:** The model uses all available data from the time of admission, padding to 12 hours if necessary for very early predictions.
- **Prediction:** A discrete-time survival probability (PMF) over 48 hours, with the risk score derived from the Cumulative Incidence Function (CIF) at the 12-hour mark.

## Data Filtering & Cleaning
- **Inclusion:** Adult patients (age ≥ 18) admitted to ICU wards.
- **Exclusion:**
    - Patients with sepsis onset ≤ 4 hours after ICU admission (pre-existing sepsis).
    - ICU stays shorter than 12 hours.
    - Stays with significant missingness in core vital signs (HR, MAP, Spo2).
- **Leakage Prevention:**
    - Train/Validation/Test splits are strictly partitioned by Patient ID to ensure no data from the same patient appears in both training and evaluation.
    - All features are computed using only information available up to the current prediction hour (no "look-ahead" bias).
