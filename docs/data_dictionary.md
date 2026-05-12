# Data Dictionary

This document describes the clinical features used by the ARISE sepsis detection system.

## Dynamic Survival Transformer (DST v2) Features

The model uses a combination of 25 time-varying (vital/lab) features and 127 static features.

### 1. Time-Varying Features (25)
These are collected hourly or extracted from lab reports.

| Feature Index | Name | Description |
|---|---|---|
| 0 | `abp_dia` | Diastolic Blood Pressure (mmHg) |
| 1 | `abp_mean` | Mean Arterial Pressure (mmHg) |
| 2 | `abp_sys` | Systolic Blood Pressure (mmHg) |
| 3 | `heart_rate` | Heart Rate (bpm) |
| 4 | `resp_rate` | Respiratory Rate (breaths/min) |
| 5 | `spo2` | Oxygen Saturation (%) |
| 6 | `temp_c` | Temperature (°C) |
| 7 | `lactate` | Serum Lactate (mmol/L) |
| 8 | `wbc` | White Blood Cell Count (10³/µL) |
| 9 | `sofa_platelets` | SOFA Platelet component |
| 10 | `sofa_bilirubin` | SOFA Bilirubin component |
| 11 | `sofa_creatinine` | SOFA Creatinine component |
| 12 | `urine_output` | Urine Output (mL/hr) |
| 13 | `vasopressor_flag` | Boolean (0/1) for vasopressor use |
| 14 | `shock_index` | Heart Rate / Systolic BP |
| 15 | `hr_delta` | Change in Heart Rate from previous hour |
| 16 | `temp_deviation` | Temperature - 37.0°C |
| 17 | `crp` | C-Reactive Protein (mg/L) |
| 18 | `platelets_raw` | Raw Platelet Count (10³/µL) |
| 19 | `inr` | International Normalized Ratio |
| 20-24 | `*_fresh` | Binary flags (0/1) indicating if a lab was measured in the current hour |

### 2. Static Features (127)
Aggregated statistics over the admission history, demographics, and admission types.
- **Demographics:** `anchor_age`, `gender_male`.
- **Admission Types:** Emergency, Urgent, Elective, Observation, etc.
- **Aggregates (mean, std, min, max, last, slope):** For all 7 vitals and key labs (Lactate, WBC, CRP, Platelets, INR).
- **Clinical Scores:** `sofa_max_24h`, `sofa_mean_24h`, `sofa_hours_ge2`.
- **Missingness:** Missing fractions and indicators for key variables.

## Simulation Data Structure
The `DST_Simulation_v5.xlsx` file contains:
- **Hourly_Sequence_25:** Hourly snapshots of the 25 features listed above.
- **Static_Features_127:** The 127 static features pre-computed for each case.
