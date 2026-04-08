"""
02_feature_engineering.py
=========================
ICU Early Sepsis Detection System — Feature Engineering Pipeline
Dataset : MIMIC-IV
Authors : [Your names]

Depends on outputs from 01_data_preprocessing.py

Feature groups produced (96 total)
------------------------------------
1. Temporal vital sign features  — mean, std, min, max, last, slope per vital
                                   slope computed on observed values only (49)
2. SOFA summary features         — max, mean, last, slope, hours >= 2      (5)
3. Static patient features       — age, gender, admission type one-hot     (11)
4. Missingness indicators        — missing fraction per vital over 24h      (7)
5. Lactate and WBC features      — summary stats + clinical threshold flags (21)
6. Gap features                  — urine output, vasopressor, ventilation,
                                   blood culture drawn/positive             (9)

Outputs (written to OUTPUT_DIR)
--------------------------------
engineered_features.csv    — 89,075 stays x 96 features, no labels
feature_medians.csv        — population medians for inference-time imputation
X_vitals.npy               — (89,075 x 24 x 7) LSTM input array
feature_names.txt          — ordered list of 96 feature column names

References
----------
Harutyunyan et al. (2019)  MIMIC-III benchmark          Sci Data
Wang          et al. (2020) MIMIC-Extract                CHIL
Sendak        et al. (2020) Sepsis Watch                 NPJ Digit Med
Wong          et al. (2021) EPIC Sepsis Model            NEJM
"""

# ============================================================
# 0. Imports & paths
# ============================================================
import zipfile
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import linregress

warnings.filterwarnings('ignore')

# ── Change these paths to match your environment ─────────────
DATA_DIR   = Path('/content/drive/MyDrive/gp/Cleaned')
OUTPUT_DIR = Path('/content/drive/MyDrive/mimic_iv_processed')
# ─────────────────────────────────────────────────────────────

FEATURE_COLS = [
    'abp_dia', 'abp_mean', 'abp_sys',
    'heart_rate', 'resp_rate', 'spo2', 'temp_c'
]


# ============================================================
# 1. Load all preprocessed outputs
# ============================================================
print("=" * 60)
print("STEP 1 — Loading preprocessed files")
print("=" * 60)

cohort = pd.read_csv(OUTPUT_DIR / 'icu_cohort.csv')
cohort['intime']  = pd.to_datetime(cohort['intime'])
cohort['outtime'] = pd.to_datetime(cohort['outtime'])

vitals_complete = pd.read_csv(OUTPUT_DIR / 'vitals_complete.csv')

X = np.load(OUTPUT_DIR / 'X_vitals.npy')
print(f"X shape: {X.shape}")

# Stay order must match X row order
stay_ids_order = (
    vitals_complete
    .sort_values(['stay_id', 'hour'])['stay_id']
    .drop_duplicates()
    .tolist()
)
print(f"Stays in X: {len(stay_ids_order):,}")

hourly_labels = pd.read_csv(OUTPUT_DIR / 'hourly_labels.csv')
hourly_labels['abs_time'] = pd.to_datetime(hourly_labels['abs_time'])
print(f"Hourly labels : {hourly_labels.shape} | "
      f"positive rate: {hourly_labels['label'].mean():.3%}")

split_df = pd.read_csv(OUTPUT_DIR / 'subject_splits.csv')

print("\nAll files loaded ✓")
print(f"Cohort   : {cohort['stay_id'].nunique():,} stays | "
      f"{cohort['subject_id'].nunique():,} patients")
print(f"Vitals   : {vitals_complete['stay_id'].nunique():,} stays")


# ============================================================
# 2. Lactate and WBC extraction
# ============================================================
print("\n" + "=" * 60)
print("STEP 2 — Lactate and WBC extraction")
print("=" * 60)

# Lactate — elevated >2 mmol/L signals tissue hypoperfusion (Sepsis-3)
# WBC     — high/low WBC is a classic SIRS criterion
EXTRA_LAB_ITEMIDS = [50813, 52442, 51301]   # Lactate x2, WBC
extra_lab_itemid_to_name = {
    50813: 'lactate',
    52442: 'lactate',
    51301: 'wbc',
}

lab_zip_path = DATA_DIR / 'chartevents_labevents.zip'
output_file  = OUTPUT_DIR / 'extra_labs_filtered.csv'

if not output_file.exists():
    first_chunk = True
    stay_ids    = set(cohort['stay_id'].dropna().unique())
    with zipfile.ZipFile(lab_zip_path, 'r') as z:
        with z.open('Cleaned/labevents.csv') as f:
            for i, chunk in enumerate(pd.read_csv(
                f, chunksize=100_000,
                usecols=['subject_id', 'hadm_id',
                         'charttime', 'itemid', 'valuenum']
            )):
                chunk = chunk[chunk['itemid'].isin(EXTRA_LAB_ITEMIDS)]
                chunk = chunk.merge(
                    cohort[['subject_id', 'hadm_id', 'stay_id']],
                    on=['subject_id', 'hadm_id'], how='inner'
                )
                if not chunk.empty:
                    chunk.to_csv(output_file, mode='a',
                                 header=first_chunk, index=False)
                    first_chunk = False
                print(f'  chunk {i+1}', end='\r')
    print('\nextra_labs_filtered.csv saved')
else:
    print('extra_labs_filtered.csv already exists, skipping extraction')

extra_labs = pd.read_csv(output_file)
extra_labs['charttime'] = pd.to_datetime(extra_labs['charttime'])
extra_labs = extra_labs.dropna(subset=['valuenum'])
extra_labs['lab_name']       = extra_labs['itemid'].map(extra_lab_itemid_to_name)
extra_labs['charttime_hour'] = extra_labs['charttime'].dt.floor('h')

extra_labs_hourly = (
    extra_labs
    .groupby(['stay_id', 'charttime_hour', 'lab_name'])['valuenum']
    .mean()
    .reset_index()
)

extra_labs_wide = extra_labs_hourly.pivot_table(
    index=['stay_id', 'charttime_hour'],
    columns='lab_name',
    values='valuenum'
).reset_index()
extra_labs_wide.columns.name = None

# Filter to first 24h of ICU stay
extra_labs_wide['charttime_hour'] = pd.to_datetime(extra_labs_wide['charttime_hour'])
extra_labs_wide = extra_labs_wide.merge(
    cohort[['stay_id', 'intime']], on='stay_id', how='left'
)
extra_labs_wide['intime'] = pd.to_datetime(extra_labs_wide['intime'])
extra_labs_wide['hours_since_admit'] = (
    (extra_labs_wide['charttime_hour'] - extra_labs_wide['intime'])
    .dt.total_seconds() / 3600
)

extra_labs_24h = extra_labs_wide[
    (extra_labs_wide['hours_since_admit'] >= 0) &
    (extra_labs_wide['hours_since_admit'] <  24)
].copy()
extra_labs_24h['hour'] = extra_labs_24h['hours_since_admit'].astype(int)

print(f"Extra labs 24h shape : {extra_labs_24h.shape}")
print(f"Stays covered        : {extra_labs_24h['stay_id'].nunique():,}")

# Forward fill within each stay (carry last known value forward)
extra_labs_24h = extra_labs_24h.sort_values(['stay_id', 'hour'])
for lab in ['lactate', 'wbc']:
    if lab in extra_labs_24h.columns:
        extra_labs_24h[lab] = (
            extra_labs_24h.groupby('stay_id')[lab]
            .transform(lambda x: x.ffill())
        )

print("Remaining NaN after forward fill:")
cols = [c for c in ['lactate', 'wbc'] if c in extra_labs_24h.columns]
print(extra_labs_24h[cols].isnull().sum())


# ============================================================
# 3. Feature computation functions
# ============================================================

def compute_temporal_features(
    vitals_complete: pd.DataFrame,
    feature_cols: list
) -> pd.DataFrame:
    """
    Per-stay summary statistics and trends over the first 24h.

    Slope is computed only on observed (pre-imputation) rows.
    If observed_{col} flag columns are absent, falls back to
    all non-NaN rows — still safer than slope over a filled grid.
    """
    records = []
    for stay_id, group in vitals_complete.groupby('stay_id'):
        group = group.sort_values('hour')
        row   = {'stay_id': stay_id}
        hours = group['hour'].values.astype(float)

        for col in feature_cols:
            vals = group[col].values.astype(float)
            row[f'{col}_mean'] = np.nanmean(vals)
            row[f'{col}_std']  = np.nanstd(vals)
            row[f'{col}_min']  = np.nanmin(vals)
            row[f'{col}_max']  = np.nanmax(vals)
            row[f'{col}_last'] = (
                vals[-1] if not np.isnan(vals[-1]) else np.nanmean(vals)
            )

            # Slope: observed rows only
            obs_flag = f'observed_{col}'
            if obs_flag in group.columns:
                obs_mask = group[obs_flag].values == 1
            else:
                obs_mask = ~np.isnan(vals)

            obs_hours = hours[obs_mask]
            obs_vals  = vals[obs_mask]

            if len(obs_vals) >= 2:
                slope, *_ = linregress(obs_hours, obs_vals)
                row[f'{col}_slope'] = slope
            else:
                row[f'{col}_slope'] = np.nan

        records.append(row)
    return pd.DataFrame(records)


def compute_sofa_features(
    sofa_labs: pd.DataFrame,
    cohort: pd.DataFrame
) -> pd.DataFrame:
    """
    Per-stay SOFA lab summary over the first 24h.
    Recomputes individual scores from raw lab values so the function
    is self-contained and does not depend on in-memory preprocessing state.
    """
    def score_platelets(x):
        if pd.isna(x): return np.nan
        if x >= 150:   return 0
        if x >= 100:   return 1
        if x >= 50:    return 2
        if x >= 20:    return 3
        return 4

    def score_bilirubin(x):
        if pd.isna(x): return np.nan
        if x < 1.2:    return 0
        if x < 2.0:    return 1
        if x < 6.0:    return 2
        if x < 12.0:   return 3
        return 4

    def score_creatinine(x):
        if pd.isna(x): return np.nan
        if x < 1.2:    return 0
        if x < 2.0:    return 1
        if x < 3.5:    return 2
        if x < 5.0:    return 3
        return 4

    sofa = sofa_labs.merge(
        cohort[['stay_id', 'intime']], on='stay_id', how='left'
    )
    sofa['intime']         = pd.to_datetime(sofa['intime'])
    sofa['charttime_hour'] = pd.to_datetime(sofa['charttime_hour'])
    sofa['hours_since_admit'] = (
        (sofa['charttime_hour'] - sofa['intime']).dt.total_seconds() / 3600
    )
    sofa_24h = sofa[
        (sofa['hours_since_admit'] >= 0) &
        (sofa['hours_since_admit'] <  24)
    ].copy()
    sofa_24h['hour'] = sofa_24h['hours_since_admit'].astype(int)

    sofa_24h['sofa_platelets']  = sofa_24h['platelets'].apply(score_platelets)
    sofa_24h['sofa_bilirubin']  = sofa_24h['bilirubin'].apply(score_bilirubin)
    sofa_24h['sofa_creatinine'] = sofa_24h['creatinine'].apply(score_creatinine)
    sofa_24h['sofa_lab_total']  = sofa_24h[
        ['sofa_platelets', 'sofa_bilirubin', 'sofa_creatinine']
    ].sum(axis=1, min_count=1)

    records = []
    for stay_id, group in sofa_24h.groupby('stay_id'):
        group = group.sort_values('hour')
        vals  = group['sofa_lab_total'].values.astype(float)
        h     = group['hour'].values
        mask  = ~np.isnan(vals)

        slope = np.nan
        if mask.sum() >= 2:
            slope, *_ = linregress(h[mask], vals[mask])

        records.append({
            'stay_id':        stay_id,
            'sofa_max_24h':   np.nanmax(vals)  if mask.any() else np.nan,
            'sofa_mean_24h':  np.nanmean(vals) if mask.any() else np.nan,
            'sofa_last_24h':  vals[-1] if not np.isnan(vals[-1])
                              else np.nanmean(vals),
            'sofa_slope_24h': slope,
            'sofa_hours_ge2': int((vals >= 2).sum()),
        })

    return pd.DataFrame(records)


def compute_static_features(cohort: pd.DataFrame) -> pd.DataFrame:
    """
    Build static features from cohort demographics.
    icu_los_hours excluded — not knowable at prediction time (future leakage).
    """
    static = cohort[[
        'stay_id', 'anchor_age', 'gender',
        'admission_type', 'admission_location',
    ]].copy()

    static['gender_male'] = (static['gender'].str.upper() == 'M').astype(int)

    admission_dummies = pd.get_dummies(
        static['admission_type'].str.lower().str.replace(' ', '_'),
        prefix='adm_type'
    ).astype(int)
    static = pd.concat([static, admission_dummies], axis=1)
    static = static.drop(
        columns=['gender', 'admission_type', 'admission_location']
    )
    return static


def compute_missingness_features(
    vitals_complete: pd.DataFrame,
    feature_cols: list
) -> pd.DataFrame:
    """
    Missing fraction per vital sign over the 24h grid.
    Missingness is itself a clinical signal — a missing ABP may indicate
    the patient did not have an arterial line.
    """
    records = []
    for stay_id, group in vitals_complete.groupby('stay_id'):
        row = {'stay_id': stay_id}
        for col in feature_cols:
            row[f'{col}_missing_frac'] = group[col].isna().sum() / len(group)
        records.append(row)
    return pd.DataFrame(records)


def compute_lab_features(extra_labs_24h: pd.DataFrame) -> pd.DataFrame:
    """
    Per-stay summary statistics for lactate and WBC over first 24h.
    Slope computed only on observed (non-imputed) rows.
    Clinical threshold flags align with Sepsis-3 and SIRS criteria.
    """
    records = []

    for stay_id, group in extra_labs_24h.groupby('stay_id'):
        row = {'stay_id': stay_id}

        for lab in ['lactate', 'wbc']:
            vals = group[lab].dropna().values

            if len(vals) == 0:
                row[f'{lab}_mean']    = np.nan
                row[f'{lab}_max']     = np.nan
                row[f'{lab}_min']     = np.nan
                row[f'{lab}_first']   = np.nan
                row[f'{lab}_last']    = np.nan
                row[f'{lab}_count']   = 0
                row[f'{lab}_missing'] = 1
                row[f'{lab}_slope']   = np.nan
            else:
                row[f'{lab}_mean']    = np.nanmean(vals)
                row[f'{lab}_max']     = np.nanmax(vals)
                row[f'{lab}_min']     = np.nanmin(vals)
                row[f'{lab}_first']   = vals[0]
                row[f'{lab}_last']    = vals[-1]
                row[f'{lab}_count']   = len(vals)
                row[f'{lab}_missing'] = 0

                obs_rows  = group[group[lab].notna()]
                obs_vals  = obs_rows[lab].values.astype(float)
                obs_hours = obs_rows['hour'].values.astype(float)

                if len(obs_vals) >= 2:
                    slope, *_ = linregress(obs_hours, obs_vals)
                    row[f'{lab}_slope'] = slope
                else:
                    row[f'{lab}_slope'] = np.nan

        # Clinical threshold flags
        lactate_vals = group['lactate'].dropna().values
        wbc_vals     = group['wbc'].dropna().values

        # Lactate >2 mmol/L = tissue hypoperfusion (Sepsis-3)
        # Lactate >4 mmol/L = septic shock range
        row['lactate_elevated'] = int(any(lactate_vals > 2.0))
        row['lactate_critical'] = int(any(lactate_vals > 4.0))

        # WBC >12 = leukocytosis, <4 = leukopenia (SIRS criteria)
        row['wbc_high']     = int(any(wbc_vals > 12.0))
        row['wbc_low']      = int(any(wbc_vals < 4.0))
        row['wbc_abnormal'] = int(
            any(wbc_vals > 12.0) or any(wbc_vals < 4.0)
        )

        records.append(row)

    return pd.DataFrame(records)


# ============================================================
# 4. Run all feature computations
# ============================================================
print("\n" + "=" * 60)
print("STEP 4 — Computing features")
print("=" * 60)

# ── 4a. Temporal vital features ──────────────────────────────
print("Computing temporal features (may take a few minutes)...")
temporal_features = compute_temporal_features(vitals_complete, FEATURE_COLS)
print(f"Temporal features shape : {temporal_features.shape}")

# ── 4b. SOFA summary features ────────────────────────────────
sofa_labs = pd.read_csv(OUTPUT_DIR / 'sofa_labs_hourly_wide.csv')
sofa_labs['charttime_hour'] = pd.to_datetime(sofa_labs['charttime_hour'])

print("Computing SOFA features...")
sofa_features = compute_sofa_features(sofa_labs, cohort)
print(f"SOFA features shape     : {sofa_features.shape}")

# ── 4c. Static patient features ──────────────────────────────
static_features = compute_static_features(cohort)
print(f"Static features shape   : {static_features.shape}")

# ── 4d. Missingness indicators ───────────────────────────────
print("Computing missingness features...")
missingness_features = compute_missingness_features(vitals_complete, FEATURE_COLS)
print(f"Missingness shape       : {missingness_features.shape}")

# ── 4e. Lactate and WBC features ─────────────────────────────
print("Computing lab features...")
lab_features = compute_lab_features(extra_labs_24h)
print(f"Lab features shape      : {lab_features.shape}")


# ============================================================
# 5. Combine all features
# ============================================================
print("\n" + "=" * 60)
print("STEP 5 — Combining features")
print("=" * 60)

all_features = (
    pd.DataFrame({'stay_id': stay_ids_order})
    .merge(temporal_features,    on='stay_id', how='left')
    .merge(sofa_features,        on='stay_id', how='left')
    .merge(static_features,      on='stay_id', how='left')
    .merge(missingness_features, on='stay_id', how='left')
    .merge(lab_features,         on='stay_id', how='left')
)

print(f"Combined shape          : {all_features.shape}")
print(f"Missing values (top 10):")
print(all_features.isnull().sum().sort_values(ascending=False).head(10))

# Population median fill — remaining NaN after forward fill
feature_cols_all = [c for c in all_features.columns if c != 'stay_id']
medians = all_features[feature_cols_all].median()
all_features[feature_cols_all] = all_features[feature_cols_all].fillna(medians)
print(f"\nMissing after median fill: {all_features.isnull().sum().sum()}")


# ============================================================
# 6. Gap features (urine output, vasopressor,
#                  ventilation, blood culture)
# ============================================================
print("\n" + "=" * 60)
print("STEP 6 — Gap features")
print("=" * 60)

stay_ids = set(cohort['stay_id'].dropna().unique())

# ── 6a. Urine output ─────────────────────────────────────────
uo_output = OUTPUT_DIR / 'urine_output_filtered.csv'
URINE_ITEMIDS = [
    226559, 226560, 226561, 226584, 226563, 226564, 226565, 226567,
    226557, 226558, 227488, 227489,
]

if not uo_output.exists():
    first_chunk = True
    with open(DATA_DIR / 'outputevents.csv') as f:
        for i, chunk in enumerate(pd.read_csv(
            f, chunksize=100_000,
            usecols=['stay_id', 'charttime', 'itemid', 'value']
        )):
            chunk = chunk[
                chunk['stay_id'].isin(stay_ids) &
                chunk['itemid'].isin(URINE_ITEMIDS)
            ]
            if not chunk.empty:
                chunk.to_csv(uo_output, mode='a',
                             header=first_chunk, index=False)
                first_chunk = False
        print(f'  UO chunk {i+1}', end='\r')
    print('\nurine_output_filtered.csv saved')
else:
    print('urine_output_filtered.csv already exists, skipping')

uo_df = pd.read_csv(uo_output)
uo_df['charttime'] = pd.to_datetime(uo_df['charttime'])
uo_df = uo_df.merge(cohort[['stay_id', 'intime']], on='stay_id', how='left')
uo_df['intime'] = pd.to_datetime(uo_df['intime'])
uo_df['hours_since_admit'] = (
    (uo_df['charttime'] - uo_df['intime']).dt.total_seconds() / 3600
)
uo_24h = uo_df[
    (uo_df['hours_since_admit'] >= 0) &
    (uo_df['hours_since_admit'] <  24)
].copy()
uo_24h['value'] = pd.to_numeric(uo_24h['value'], errors='coerce')

# Clip physiologically impossible values
# Negative UO = data correction entries in MIMIC
# Max realistic 24h UO ~10,000 mL even with aggressive diuresis
uo_24h['value'] = uo_24h['value'].clip(lower=0, upper=10000)

uo_features = (
    uo_24h.groupby('stay_id')['value']
    .agg(
        uo_total_24h='sum',
        uo_mean_hourly=lambda x: x.sum() / 24,
        uo_min_hourly='min',
        uo_count='count'
    )
    .reset_index()
)
# Oliguria = total UO < 500 mL in 24h (clinical threshold)
uo_features['oliguria_flag'] = (
    uo_features['uo_total_24h'] < 500
).astype(int)
print(f"UO features shape       : {uo_features.shape}")

# ── 6b. Vasopressor flag ─────────────────────────────────────
# vasopressors_filtered.csv already extracted in preprocessing
vaso_path = OUTPUT_DIR / 'vasopressors_filtered.csv'

if vaso_path.exists():
    vaso_df = pd.read_csv(vaso_path)
    vaso_df['starttime']      = pd.to_datetime(vaso_df['starttime'])
    vaso_df['charttime_hour'] = vaso_df['starttime'].dt.floor('h')
    vaso_df = vaso_df.merge(
        cohort[['stay_id', 'intime']], on='stay_id', how='left'
    )
    vaso_df['intime'] = pd.to_datetime(vaso_df['intime'])
    vaso_df['hours_since_admit'] = (
        (vaso_df['charttime_hour'] - vaso_df['intime'])
        .dt.total_seconds() / 3600
    )
    vaso_24h = vaso_df[
        (vaso_df['hours_since_admit'] >= 0) &
        (vaso_df['hours_since_admit'] <  24)
    ].copy()
    vaso_features = (
        vaso_24h.groupby('stay_id')
        .size()
        .reset_index(name='vaso_events_24h')
    )
    vaso_features['vasopressor_flag'] = 1
    print(f"Vasopressor features    : {vaso_features.shape}")
else:
    print('WARNING: vasopressors_filtered.csv not found')
    vaso_features = pd.DataFrame(
        columns=['stay_id', 'vaso_events_24h', 'vasopressor_flag']
    )

# ── 6c. Ventilation status ───────────────────────────────────
vent_path      = DATA_DIR / 'ventilation.csv'
vent_proc_path = DATA_DIR / 'procedureevents.csv'
VENT_PROC_ITEMIDS = [225792, 225794]

if vent_path.exists():
    vent_raw = pd.read_csv(
        vent_path,
        usecols=['stay_id', 'starttime', 'ventilation_status']
    )
    vent_raw['starttime'] = pd.to_datetime(vent_raw['starttime'])
    vent_raw = vent_raw.merge(
        cohort[['stay_id', 'intime']], on='stay_id', how='left'
    )
    vent_raw['intime'] = pd.to_datetime(vent_raw['intime'])
    vent_raw['hours_since_admit'] = (
        (vent_raw['starttime'] - vent_raw['intime'])
        .dt.total_seconds() / 3600
    )
    vent_24h = vent_raw[
        (vent_raw['hours_since_admit'] >= 0) &
        (vent_raw['hours_since_admit'] <  24) &
        (vent_raw['ventilation_status'] == 'InvasiveVent')
    ]
    print('Ventilation loaded from ventilation.csv')

elif vent_proc_path.exists():
    vent_raw = pd.read_csv(
        vent_proc_path,
        usecols=['stay_id', 'starttime', 'itemid']
    )
    vent_raw = vent_raw[vent_raw['itemid'].isin(VENT_PROC_ITEMIDS)]
    vent_raw['starttime'] = pd.to_datetime(vent_raw['starttime'])
    vent_raw = vent_raw.merge(
        cohort[['stay_id', 'intime']], on='stay_id', how='left'
    )
    vent_raw['intime'] = pd.to_datetime(vent_raw['intime'])
    vent_raw['hours_since_admit'] = (
        (vent_raw['starttime'] - vent_raw['intime'])
        .dt.total_seconds() / 3600
    )
    vent_24h = vent_raw[
        (vent_raw['hours_since_admit'] >= 0) &
        (vent_raw['hours_since_admit'] <  24)
    ]
    print('Ventilation loaded from procedureevents.csv')

else:
    print('WARNING: No ventilation source found — flag set to 0')
    vent_24h = pd.DataFrame(columns=['stay_id'])

ventilated_stays = (
    set(vent_24h['stay_id'].unique()) if len(vent_24h) > 0 else set()
)
vent_features = cohort[['stay_id']].copy()
vent_features['ventilated_flag'] = (
    vent_features['stay_id'].isin(ventilated_stays).astype(int)
)
print(f"Ventilated in first 24h : {vent_features['ventilated_flag'].sum():,}")

# ── 6d. Blood culture flags ──────────────────────────────────
micro = pd.read_csv(DATA_DIR / 'microbiologyevents.csv', low_memory=False)
micro['charttime'] = pd.to_datetime(micro['charttime'], errors='coerce')
micro['chartdate'] = pd.to_datetime(micro['chartdate'], errors='coerce')
micro['culture_time'] = micro['charttime'].combine_first(micro['chartdate'])

cohort_keys = cohort[
    ['subject_id', 'hadm_id', 'stay_id', 'intime']
].drop_duplicates()
micro = micro.merge(cohort_keys, on=['subject_id', 'hadm_id'], how='inner')
micro['intime'] = pd.to_datetime(micro['intime'])
micro['hours_since_admit'] = (
    (micro['culture_time'] - micro['intime']).dt.total_seconds() / 3600
)

blood_cultures = micro[
    (micro['spec_type_desc'].str.contains('BLOOD', case=False, na=False)) &
    (micro['hours_since_admit'] >= 0) &
    (micro['hours_since_admit'] <  24)
].copy()

culture_drawn = (
    blood_cultures.groupby('stay_id')
    .size()
    .reset_index(name='culture_count')
)
culture_drawn['blood_culture_drawn'] = 1

culture_positive = blood_cultures[
    blood_cultures['org_name'].notna() &
    (blood_cultures['org_name'].str.strip() != '')
][['stay_id']].drop_duplicates()
culture_positive['blood_culture_positive'] = 1

blood_culture_features = culture_drawn[
    ['stay_id', 'blood_culture_drawn']
].merge(culture_positive, on='stay_id', how='left')
blood_culture_features['blood_culture_positive'] = (
    blood_culture_features['blood_culture_positive'].fillna(0).astype(int)
)
print(f"Blood cultures drawn    : "
      f"{blood_culture_features['blood_culture_drawn'].sum():,}")
print(f"Blood cultures positive : "
      f"{blood_culture_features['blood_culture_positive'].sum():,}")

# ── 6e. Merge all gap features into all_features ─────────────
all_features = all_features.merge(
    uo_features, on='stay_id', how='left'
).merge(
    vaso_features[['stay_id', 'vaso_events_24h', 'vasopressor_flag']],
    on='stay_id', how='left'
).merge(
    vent_features, on='stay_id', how='left'
).merge(
    blood_culture_features, on='stay_id', how='left'
)

# Fill binary flags with 0 for stays with no recorded event
for col in ['vasopressor_flag', 'blood_culture_drawn',
            'blood_culture_positive', 'vaso_events_24h']:
    if col in all_features.columns:
        all_features[col] = all_features[col].fillna(0).astype(int)

print(f"\nall_features after gap features : {all_features.shape}")


# ============================================================
# 7. Final median fill + save
# ============================================================
print("\n" + "=" * 60)
print("STEP 7 — Final median fill and save")
print("=" * 60)

new_gap_cols = [
    'uo_total_24h', 'uo_mean_hourly', 'uo_min_hourly', 'uo_count',
    'oliguria_flag', 'vaso_events_24h', 'vasopressor_flag',
    'ventilated_flag', 'blood_culture_drawn', 'blood_culture_positive'
]
new_gap_cols_present = [c for c in new_gap_cols if c in all_features.columns]
gap_medians = all_features[new_gap_cols_present].median()
all_features[new_gap_cols_present] = (
    all_features[new_gap_cols_present].fillna(gap_medians)
)

# Save all outputs
all_features.to_csv(OUTPUT_DIR / 'engineered_features.csv', index=False)
print(f"Saved engineered_features.csv — shape: {all_features.shape}")

medians.to_csv(OUTPUT_DIR / 'feature_medians.csv', header=True)
print("Saved feature_medians.csv")

np.save(OUTPUT_DIR / 'X_vitals.npy', X)
print(f"Saved X_vitals.npy — shape: {X.shape}")

feature_cols_all = [c for c in all_features.columns if c != 'stay_id']
with open(OUTPUT_DIR / 'feature_names.txt', 'w') as f:
    f.write('\n'.join(feature_cols_all))
print(f"Saved feature_names.txt — {len(feature_cols_all)} features")

# Leakage check
leaked = [c for c in all_features.columns
          if c in ['y_6h', 'y_12h', 'y_24h',
                   'eligible_6h', 'eligible_12h', 'eligible_24h',
                   'icu_los_hours']]
assert len(leaked) == 0, f'LEAKAGE: {leaked}'
print("Leakage check passed ✓")


# ============================================================
# 8. Final verification
# ============================================================
print("\n" + "=" * 60)
print("FEATURE ENGINEERING COMPLETE")
print("=" * 60)
print(f"Shape              : {all_features.shape}")
print(f"Total features     : {all_features.shape[1] - 1}")
print(f"Missing values     : {all_features.isnull().sum().sum()}")
print(f"Unique stays       : {all_features['stay_id'].nunique():,}")

print("\nFeature groups:")
print(f"  Temporal vitals  : {len([c for c in all_features.columns if any(v in c for v in ['heart_rate','resp_rate','temp_c','spo2','abp']) and c != 'stay_id'])}")
print(f"  SOFA summary     : {len([c for c in all_features.columns if 'sofa' in c])}")
print(f"  Static           : {len([c for c in all_features.columns if 'age' in c or 'gender' in c or 'adm_type' in c])}")
print(f"  Missingness      : {len([c for c in all_features.columns if 'missing' in c and 'lac' not in c and 'wbc' not in c])}")
print(f"  Lactate/WBC      : {len([c for c in all_features.columns if 'lactate' in c or 'wbc' in c])}")
print(f"  Gap features     : {len([c for c in all_features.columns if any(g in c for g in ['uo_','vaso','vent','culture'])])}")

print("\n--- Label Summary ---")
print(f"Total prediction points : {len(hourly_labels):,}")
print(f"Positive (sepsis)       : {hourly_labels['label'].sum():,}")
print(f"Positive rate           : {hourly_labels['label'].mean():.3%}")
for split in ['train', 'val', 'test']:
    s = hourly_labels[hourly_labels['split'] == split]
    print(f"{split:5s} | {len(s):>9,} points | "
          f"positive rate {s['label'].mean():.3%}")

print("\nFiles saved to Drive:")
for fname in ['engineered_features.csv', 'feature_medians.csv',
              'X_vitals.npy', 'feature_names.txt']:
    fpath = OUTPUT_DIR / fname
    if fpath.exists():
        size_mb = fpath.stat().st_size / 1_048_576
        print(f"  {fname:<35s} {size_mb:>7.1f} MB")
    else:
        print(f"  {fname:<35s} NOT FOUND")
