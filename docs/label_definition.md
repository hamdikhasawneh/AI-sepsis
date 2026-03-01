# Label Definition (Sepsis)

## Goal
Predict sepsis in ICU patients using MIMIC data.

## To be finalized
- Dataset version: MIMIC-III or MIMIC-IV
- Sepsis definition: Sepsis-3 preferred (suspected infection + organ dysfunction / SOFA change)
- Prediction horizon: e.g., predict sepsis within the next 6 hours
- Exclusions: pediatrics, very short ICU stays, missing key variables, etc.

## Leakage rules (important)
- Train/test split by patient (or ICU stay), not by rows.
- Features must use information available *up to prediction time only*.
