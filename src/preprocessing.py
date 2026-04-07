preprocessing.py 
"""
01_data_preprocessing.py
========================
ICU Early Sepsis Detection System — Preprocessing Pipeline
Dataset : MIMIC-IV
Authors : [Your names]

Pipeline steps
--------------
1.  Load base tables (patients, admissions, icustays)
2.  Build ICU cohort (adults, LOS >= 4 h)
3.  Extract & process vital signs → vitals_complete.csv + X_vitals.npy
4.  Compute 6-component SOFA score (labs, cardiovascular, GCS, respiratory)
5.  Build suspected infection timestamps (antibiotic + culture pairing)
6.  Restrict SOFA and infection to ICU window
7.  Identify Sepsis-3 onset per stay
8.  Generate rolling hourly labels (Option B)
9.  Subject-level train / val / test split (no patient leakage)

Outputs (written to OUTPUT_DIR)
--------------------------------
icu_cohort.csv
vitals_hourly_wide.csv
vitals_24h.csv
vitals_complete.csv
X_vitals.npy
sofa_labs_hourly_wide.csv
vasopressors_filtered.csv
resp_sofa_filtered.csv
gcs_filtered.csv
suspected_infection.csv
hourly_labels.csv          ← rolling labels with split column
subject_splits.csv

References
----------
Singer et al. (2016)  Sepsis-3 definition          JAMA
Reyna  et al. (2019)  PhysioNet Sepsis Challenge    Computing in Cardiology
Rice   et al. (2007)  SF-ratio surrogate            Crit Care Med
Sinha  et al. (2020)  SF/PF ratio equivalence       Chest
"""

# ============================================================
DATA_DIR   = Path('/content/drive/MyDrive/gp/Cleaned')
OUTPUT_DIR = Path('/content/drive/MyDrive/mimic_iv_processed')
# ============================================================
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

# ── Change these two paths to match your environment ────────
DATA_DIR   = Path('/content/drive/MyDrive/gp/Cleaned')
OUTPUT_DIR = Path('/content/drive/MyDrive/mimic_iv_processed')
# ────────────────────────────────────────────────────────────

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CHARTEVENTS_ZIP = DATA_DIR / 'chartevents_labevents.zip'
RANDOM_STATE    = 42


# ============================================================
# 1. Load base tables
# ============================================================
print("=" * 60)
print("STEP 1 — Loading base tables")
print("=" * 60)

patients   = pd.read_csv(DATA_DIR / 'patients.csv')
admissions = pd.read_csv(DATA_DIR / 'admissions.csv')
icustays   = pd.read_csv(DATA_DIR / 'icustays.csv')

print(f"patients  : {patients.shape}")
print(f"admissions: {admissions.shape}")
print(f"icustays  : {icustays.shape}")


# ============================================================
# 2. Build ICU cohort
# ============================================================
print("\n" + "=" * 60)
print("STEP 2 — Building ICU cohort")
print("=" * 60)

cohort = (
    icustays
    .merge(admissions, on=['subject_id', 'hadm_id'], how='left')
    .merge(patients,   on='subject_id',               how='left')
)

# Datetime conversions
for col in ['intime', 'outtime', 'admittime', 'dischtime']:
    cohort[col] = pd.to_datetime(cohort[col])

# ICU length of stay in hours
cohort['icu_los_hours'] = (
    (cohort['outtime'] - cohort['intime']).dt.total_seconds() / 3600
)

# Filters
cohort = cohort[cohort['icu_los_hours']  >= 4]   # min 4-hour stay
cohort = cohort[cohort['anchor_age']     >= 18]  # adults only
cohort = cohort.drop_duplicates(subset='stay_id')

print(f"Final cohort : {cohort.shape[0]:,} stays | "
      f"{cohort['subject_id'].nunique():,} unique patients")

cohort.to_csv(OUTPUT_DIR / 'icu_cohort.csv', index=False)
print("Saved: icu_cohort.csv")


# ============================================================
# 3. Vital signs extraction and processing
# ============================================================
print("\n" + "=" * 60)
print("STEP 3 — Vital signs")
print("=" * 60)

VITAL_ITEMIDS = {
    220045: 'heart_rate',
    220210: 'resp_rate',
    223762: 'temp_c',
    220277: 'spo2',
    220050: 'abp_sys',
    220051: 'abp_dia',
    220052: 'abp_mean',
}

FEATURE_COLS = ['abp_dia', 'abp_mean', 'abp_sys',
                'heart_rate', 'resp_rate', 'spo2', 'temp_c']

stay_ids      = set(cohort['stay_id'].dropna().unique())
vital_ids_set = set(VITAL_ITEMIDS.keys())

# ── 3a. Extract from chartevents ─────────────────────────────
vitals_file = OUTPUT_DIR / 'vitals_filtered.csv'
if vitals_file.exists():
    vitals_file.unlink()

first_chunk = True
with zipfile.ZipFile(CHARTEVENTS_ZIP, 'r') as z:
    with z.open('Cleaned/chartevents.csv') as f:
        for i, chunk in enumerate(pd.read_csv(
            f, chunksize=100_000,
            usecols=['subject_id', 'hadm_id', 'stay_id',
                     'charttime', 'itemid', 'valuenum', 'valueuom']
        )):
            chunk = chunk[
                chunk['stay_id'].isin(stay_ids) &
                chunk['itemid'].isin(vital_ids_set)
            ]
            if not chunk.empty:
                chunk.to_csv(vitals_file, mode='a',
                             header=first_chunk, index=False)
                first_chunk = False
            print(f"  vitals chunk {i+1}", end='\r')

print(f"\nVitals extracted")

# ── 3b. Aggregate to hourly wide format ──────────────────────
vitals = pd.read_csv(vitals_file)
vitals['feature_name']   = vitals['itemid'].map(VITAL_ITEMIDS)
vitals['charttime']      = pd.to_datetime(vitals['charttime'])
vitals['charttime_hour'] = vitals['charttime'].dt.floor('h')

vitals_hourly = (
    vitals
    .groupby(['stay_id', 'charttime_hour', 'feature_name'])['valuenum']
    .mean()
    .reset_index()
)

vitals_wide = vitals_hourly.pivot_table(
    index=['stay_id', 'charttime_hour'],
    columns='feature_name',
    values='valuenum'
).reset_index()
vitals_wide.columns.name = None

vitals_wide = vitals_wide.merge(
    cohort[['stay_id', 'intime']], on='stay_id', how='left'
)
vitals_wide['charttime_hour'] = pd.to_datetime(vitals_wide['charttime_hour'])
vitals_wide['intime']         = pd.to_datetime(vitals_wide['intime'])
vitals_wide['hours_since_admit'] = (
    (vitals_wide['charttime_hour'] - vitals_wide['intime'])
    .dt.total_seconds() / 3600
)

vitals_wide.to_csv(OUTPUT_DIR / 'vitals_hourly_wide.csv', index=False)
print("Saved: vitals_hourly_wide.csv")

# ── 3c. Keep first 24 h, require >= 12 observed hours ────────
vitals_24h = vitals_wide[
    (vitals_wide['hours_since_admit'] >= 0) &
    (vitals_wide['hours_since_admit'] <  24)
].copy()
vitals_24h['hour'] = vitals_24h['hours_since_admit'].astype(int)
vitals_24h = vitals_24h[['stay_id', 'hour'] + FEATURE_COLS].copy()
vitals_24h = (
    vitals_24h
    .groupby(['stay_id', 'hour'], as_index=False)
    .mean(numeric_only=True)
)

# Minimum 12 observed hours
valid_stays = (
    vitals_24h.groupby('stay_id')['hour'].nunique()
)
valid_stays = valid_stays[valid_stays >= 12].index
vitals_24h  = vitals_24h[vitals_24h['stay_id'].isin(valid_stays)]

vitals_24h.to_csv(OUTPUT_DIR / 'vitals_24h.csv', index=False)
print("Saved: vitals_24h.csv")

# ── 3d. Build complete 24-h grid with limited imputation ──────
vitals_complete = []
for stay_id, group in vitals_24h.groupby('stay_id'):
    group = group.set_index('hour').reindex(range(24))
    group['stay_id'] = stay_id
    vitals_complete.append(group.reset_index())

vitals_complete = pd.concat(vitals_complete, ignore_index=True)
vitals_complete = vitals_complete.sort_values(['stay_id', 'hour'])

# Forward-fill max 4 h, backward-fill max 1 h (start of stay only)
vitals_complete = (
    vitals_complete
    .groupby('stay_id', group_keys=False)
    .apply(lambda x: x.ffill(limit=4).bfill(limit=1))
)
vitals_complete.reset_index(drop=True, inplace=True)

vitals_complete.to_csv(OUTPUT_DIR / 'vitals_complete.csv', index=False)
print("Saved: vitals_complete.csv")

# ── 3e. Build 3-D LSTM array (n_stays, 24, 7) ────────────────
vitals_complete = vitals_complete.sort_values(
    ['stay_id', 'hour']
).reset_index(drop=True)

stay_ids_order = vitals_complete['stay_id'].drop_duplicates().tolist()

X = np.array([
    vitals_complete[
        vitals_complete['stay_id'] == sid
    ][FEATURE_COLS].values
    for sid in stay_ids_order
])

np.save(OUTPUT_DIR / 'X_vitals.npy', X)
print(f"Saved: X_vitals.npy  shape={X.shape}")


# ============================================================
# 4. SOFA score (6 components)
# ============================================================
print("\n" + "=" * 60)
print("STEP 4 — SOFA score")
print("=" * 60)

# ── 4a. Lab components (platelets, bilirubin, creatinine) ────
SOFA_LAB_ITEMIDS = {
    'platelets':  [51265],
    'bilirubin':  [50885],
    'creatinine': [50912, 52546],
}
all_lab_ids = (
    SOFA_LAB_ITEMIDS['platelets'] +
    SOFA_LAB_ITEMIDS['bilirubin'] +
    SOFA_LAB_ITEMIDS['creatinine']
)
lab_itemid_to_name = {
    51265: 'platelets',
    50885: 'bilirubin',
    50912: 'creatinine',
    52546: 'creatinine',
}

labs_file = OUTPUT_DIR / 'sofa_labs_filtered.csv'
if labs_file.exists():
    labs_file.unlink()

first_chunk = True
with zipfile.ZipFile(CHARTEVENTS_ZIP, 'r') as z:
    with z.open('Cleaned/labevents.csv') as f:
        for i, chunk in enumerate(pd.read_csv(
            f, chunksize=100_000,
            usecols=['subject_id', 'hadm_id', 'charttime', 'itemid', 'valuenum']
        )):
            chunk = chunk[chunk['itemid'].isin(all_lab_ids)]
            chunk = chunk.merge(
                cohort[['subject_id', 'hadm_id', 'stay_id']],
                on=['subject_id', 'hadm_id'], how='inner'
            )
            if not chunk.empty:
                chunk.to_csv(labs_file, mode='a',
                             header=first_chunk, index=False)
                first_chunk = False
            print(f"  labs chunk {i+1}", end='\r')

print("\nSOFA labs extracted")

labs = pd.read_csv(labs_file)
labs['charttime'] = pd.to_datetime(labs['charttime'])
labs = labs.dropna(subset=['valuenum'])
labs['lab_name']      = labs['itemid'].map(lab_itemid_to_name)
labs['charttime_hour'] = labs['charttime'].dt.floor('h')

labs_hourly = (
    labs
    .groupby(['stay_id', 'charttime_hour', 'lab_name'])['valuenum']
    .mean()
    .reset_index()
)

labs_wide = labs_hourly.pivot_table(
    index=['stay_id', 'charttime_hour'],
    columns='lab_name',
    values='valuenum'
).reset_index()
labs_wide.columns.name = None

labs_wide.to_csv(OUTPUT_DIR / 'sofa_labs_hourly_wide.csv', index=False)
print("Saved: sofa_labs_hourly_wide.csv")


def sofa_platelets(x):
    if pd.isna(x):  return np.nan
    if x >= 150:    return 0
    if x >= 100:    return 1
    if x >= 50:     return 2
    if x >= 20:     return 3
    return 4


def sofa_bilirubin(x):
    if pd.isna(x):  return np.nan
    if x < 1.2:     return 0
    if x < 2.0:     return 1
    if x < 6.0:     return 2
    if x < 12.0:    return 3
    return 4


def sofa_creatinine(x):
    if pd.isna(x):  return np.nan
    if x < 1.2:     return 0
    if x < 2.0:     return 1
    if x < 3.5:     return 2
    if x < 5.0:     return 3
    return 4


labs_wide['sofa_platelets']  = labs_wide['platelets'].apply(sofa_platelets)
labs_wide['sofa_bilirubin']  = labs_wide['bilirubin'].apply(sofa_bilirubin)
labs_wide['sofa_creatinine'] = labs_wide['creatinine'].apply(sofa_creatinine)
labs_wide['sofa_lab_total']  = (
    labs_wide[['sofa_platelets', 'sofa_bilirubin', 'sofa_creatinine']]
    .sum(axis=1, min_count=1)
)

# ── 4b. Cardiovascular SOFA (MAP + vasopressors) ─────────────
map_df = vitals_wide[['stay_id', 'charttime_hour', 'abp_mean']].copy()
map_df['sofa_cardio'] = map_df['abp_mean'].apply(
    lambda x: np.nan if pd.isna(x) else (0 if x >= 70 else 1)
)

VASOPRESSOR_ITEMIDS = {
    'dopamine':       221662,
    'dobutamine':     221653,
    'norepinephrine': 221906,
    'epinephrine':    221289,
    'phenylephrine':  221749,
    'vasopressin':    222315,
}
all_vaso_ids = list(VASOPRESSOR_ITEMIDS.values())

vaso_file = OUTPUT_DIR / 'vasopressors_filtered.csv'
if vaso_file.exists():
    vaso_file.unlink()

first_chunk = True
with open(DATA_DIR / 'inputevents.csv') as f:
    for i, chunk in enumerate(pd.read_csv(
        f, chunksize=100_000,
        usecols=['stay_id', 'starttime', 'itemid', 'amount', 'rate', 'rateuom']
    )):
        chunk = chunk[
            chunk['stay_id'].isin(stay_ids) &
            chunk['itemid'].isin(all_vaso_ids)
        ]
        if not chunk.empty:
            chunk.to_csv(vaso_file, mode='a',
                         header=first_chunk, index=False)
            first_chunk = False
        print(f"  vasopressor chunk {i+1}", end='\r')

print("\nVasopressor data extracted")

vaso_df = pd.read_csv(vaso_file)
vaso_df['starttime']      = pd.to_datetime(vaso_df['starttime'])
vaso_df['charttime_hour'] = vaso_df['starttime'].dt.floor('h')

vaso_flag = (
    vaso_df
    .groupby(['stay_id', 'charttime_hour'])
    .size()
    .reset_index(name='vaso_count')
)
vaso_flag['sofa_cardio_vaso'] = 2   # any vasopressor = score 2

map_df = map_df.merge(
    vaso_flag[['stay_id', 'charttime_hour', 'sofa_cardio_vaso']],
    on=['stay_id', 'charttime_hour'], how='left'
)
map_df['sofa_cardio_vaso'] = map_df['sofa_cardio_vaso'].fillna(0)
map_df['sofa_cardio'] = map_df[['sofa_cardio', 'sofa_cardio_vaso']].max(axis=1)

# ── 4c. CNS SOFA (GCS) ───────────────────────────────────────
GCS_ITEMIDS = [220739, 223900, 223901]
gcs_map = {220739: 'eye', 223900: 'verbal', 223901: 'motor'}

gcs_file = OUTPUT_DIR / 'gcs_filtered.csv'
if gcs_file.exists():
    gcs_file.unlink()

first_chunk = True
with zipfile.ZipFile(CHARTEVENTS_ZIP, 'r') as z:
    with z.open('Cleaned/chartevents.csv') as f:
        for i, chunk in enumerate(pd.read_csv(
            f, chunksize=100_000,
            usecols=['subject_id', 'hadm_id', 'stay_id',
                     'charttime', 'itemid', 'valuenum']
        )):
            chunk = chunk[
                chunk['stay_id'].isin(stay_ids) &
                chunk['itemid'].isin(GCS_ITEMIDS)
            ]
            if not chunk.empty:
                chunk.to_csv(gcs_file, mode='a',
                             header=first_chunk, index=False)
                first_chunk = False
        print(f"  GCS chunk {i+1}", end='\r')

print("\nGCS data extracted")

gcs = pd.read_csv(gcs_file)
gcs['charttime']      = pd.to_datetime(gcs['charttime'])
gcs = gcs.dropna(subset=['valuenum'])
gcs['charttime_hour'] = gcs['charttime'].dt.floor('h')
gcs['component']      = gcs['itemid'].map(gcs_map)

gcs_hourly = (
    gcs
    .groupby(['stay_id', 'charttime_hour', 'component'])['valuenum']
    .mean()
    .reset_index()
)

gcs_wide = gcs_hourly.pivot_table(
    index=['stay_id', 'charttime_hour'],
    columns='component',
    values='valuenum'
).reset_index()
gcs_wide.columns.name = None

gcs_wide['gcs_total'] = (
    gcs_wide[['eye', 'verbal', 'motor']].sum(axis=1, min_count=3)
)


def sofa_gcs(x):
    if pd.isna(x): return np.nan
    if x == 15:    return 0
    if x >= 13:    return 1
    if x >= 10:    return 2
    if x >= 6:     return 3
    return 4


gcs_wide['sofa_gcs'] = gcs_wide['gcs_total'].apply(sofa_gcs)

# ── 4d. Respiratory SOFA (PF ratio, SF ratio surrogate) ──────
FIO2_ITEMIDS = [223835]
PAO2_ITEMIDS = [490, 779, 220224]
RESP_ITEMIDS = FIO2_ITEMIDS + PAO2_ITEMIDS

resp_file = OUTPUT_DIR / 'resp_sofa_filtered.csv'
if resp_file.exists():
    resp_file.unlink()

first_chunk = True
with zipfile.ZipFile(CHARTEVENTS_ZIP, 'r') as z:
    with z.open('Cleaned/chartevents.csv') as f:
        for i, chunk in enumerate(pd.read_csv(
            f, chunksize=100_000,
            usecols=['stay_id', 'charttime', 'itemid', 'valuenum']
        )):
            chunk = chunk[
                chunk['stay_id'].isin(stay_ids) &
                chunk['itemid'].isin(RESP_ITEMIDS)
            ]
            if not chunk.empty:
                chunk.to_csv(resp_file, mode='a',
                             header=first_chunk, index=False)
                first_chunk = False
        print(f"  resp chunk {i+1}", end='\r')

print("\nRespiratory data extracted")

resp_df = pd.read_csv(resp_file)
resp_df['charttime']      = pd.to_datetime(resp_df['charttime'])
resp_df['charttime_hour'] = resp_df['charttime'].dt.floor('h')

fio2_df = resp_df[resp_df['itemid'].isin(FIO2_ITEMIDS)].copy()
pao2_df = resp_df[resp_df['itemid'].isin(PAO2_ITEMIDS)].copy()

fio2_hourly = (
    fio2_df.groupby(['stay_id', 'charttime_hour'])['valuenum']
    .mean().reset_index()
)
fio2_hourly.columns = ['stay_id', 'charttime_hour', 'fio2']

pao2_hourly = (
    pao2_df.groupby(['stay_id', 'charttime_hour'])['valuenum']
    .mean().reset_index()
)
pao2_hourly.columns = ['stay_id', 'charttime_hour', 'pao2']

pf_df = pao2_hourly.merge(
    fio2_hourly, on=['stay_id', 'charttime_hour'], how='left'
)
# Convert FiO2 from percentage to fraction if needed
pf_df.loc[pf_df['fio2'] > 1, 'fio2'] = (
    pf_df.loc[pf_df['fio2'] > 1, 'fio2'] / 100
)
pf_df['pf_ratio'] = pf_df['pao2'] / pf_df['fio2']

sf_df = vitals_wide[['stay_id', 'charttime_hour', 'spo2']].merge(
    fio2_hourly, on=['stay_id', 'charttime_hour'], how='left'
)
sf_df['fio2']     = sf_df['fio2'].fillna(0.21)   # room air default
sf_df['sf_ratio'] = sf_df['spo2'] / sf_df['fio2']


def sofa_resp_pf(pf):
    """PaO2/FiO2 ratio → SOFA respiratory score."""
    if pd.isna(pf): return np.nan
    if pf >= 400:   return 0
    if pf >= 300:   return 1
    if pf >= 200:   return 2
    if pf >= 100:   return 3
    return 4


def sofa_resp_sf(sf):
    """SpO2/FiO2 ratio surrogate → SOFA respiratory score.
    Thresholds per Rice et al. 2007 / Sinha et al. 2020."""
    if pd.isna(sf): return np.nan
    if sf >= 315:   return 0
    if sf >= 235:   return 1
    if sf >= 150:   return 2
    return 3   # SF cannot reliably distinguish score 3 vs 4


pf_df['sofa_resp']    = pf_df['pf_ratio'].apply(sofa_resp_pf)
sf_df['sofa_resp_sf'] = sf_df['sf_ratio'].apply(sofa_resp_sf)

# ── 4e. Merge all 6 components → sofa_df ─────────────────────
sofa_df = labs_wide.merge(
    map_df[['stay_id', 'charttime_hour', 'sofa_cardio']],
    on=['stay_id', 'charttime_hour'], how='outer'
)
sofa_df = sofa_df.merge(
    gcs_wide[['stay_id', 'charttime_hour', 'sofa_gcs']],
    on=['stay_id', 'charttime_hour'], how='outer'
)
sofa_df = sofa_df.merge(
    pf_df[['stay_id', 'charttime_hour', 'sofa_resp']],
    on=['stay_id', 'charttime_hour'], how='left'
)
sofa_df = sofa_df.merge(
    sf_df[['stay_id', 'charttime_hour', 'sofa_resp_sf']],
    on=['stay_id', 'charttime_hour'], how='left'
)

# Prefer PF-based respiratory score, fall back to SF surrogate
sofa_df['sofa_resp_final'] = sofa_df['sofa_resp'].combine_first(
    sofa_df['sofa_resp_sf']
)

SOFA_COMPONENTS = [
    'sofa_platelets', 'sofa_bilirubin', 'sofa_creatinine',
    'sofa_cardio', 'sofa_gcs', 'sofa_resp_final'
]
sofa_df['sofa_total'] = sofa_df[SOFA_COMPONENTS].sum(axis=1, min_count=1)

print(f"Full 6-component SOFA computed  shape={sofa_df.shape}")
print(sofa_df['sofa_total'].describe())


# ============================================================
# 5. Suspected infection timestamps
# ============================================================
print("\n" + "=" * 60)
print("STEP 5 — Suspected infection timestamps")
print("=" * 60)

prescriptions = pd.read_csv(
    DATA_DIR / 'prescriptions.csv', low_memory=False
)
micro = pd.read_csv(
    DATA_DIR / 'microbiologyevents.csv', low_memory=False
)

prescriptions['starttime'] = pd.to_datetime(
    prescriptions['starttime'], errors='coerce'
)
micro['charttime'] = pd.to_datetime(micro['charttime'], errors='coerce')
micro['chartdate'] = pd.to_datetime(micro['chartdate'], errors='coerce')
micro['culture_time'] = micro['charttime'].combine_first(micro['chartdate'])

cohort_keys = cohort[['subject_id', 'hadm_id', 'stay_id']].drop_duplicates()

presc = (
    prescriptions
    .merge(cohort_keys, on=['subject_id', 'hadm_id'], how='inner')
    [['subject_id', 'hadm_id', 'stay_id', 'starttime', 'drug']]
    .dropna(subset=['starttime'])
)

cultures = (
    micro
    .merge(cohort_keys, on=['subject_id', 'hadm_id'], how='inner')
    [['subject_id', 'hadm_id', 'stay_id', 'culture_time', 'spec_type_desc']]
    .dropna(subset=['culture_time'])
)

# Antibiotic keyword filter
ANTIBIOTIC_KEYWORDS = [
    'cillin', 'cef', 'cefepime', 'ceftriaxone', 'ceftazidime',
    'vancomycin', 'meropenem', 'imipenem', 'ertapenem',
    'piperacillin', 'tazobactam', 'zosyn',
    'ciprofloxacin', 'levofloxacin', 'moxifloxacin',
    'azithromycin', 'clarithromycin',
    'metronidazole', 'clindamycin',
    'gentamicin', 'amikacin', 'tobramycin',
    'doxycycline', 'tigecycline',
    'trimethoprim', 'sulfamethoxazole',
    'linezolid', 'daptomycin',
]
pattern = '|'.join(ANTIBIOTIC_KEYWORDS)
abx = presc[
    presc['drug'].astype(str).str.lower().str.contains(pattern, na=False)
].copy().rename(columns={'starttime': 'antibiotic_time'})

pairs = abx.merge(
    cultures, on=['subject_id', 'hadm_id', 'stay_id'], how='inner'
)
pairs['time_diff_hours'] = (
    (pairs['antibiotic_time'] - pairs['culture_time'])
    .dt.total_seconds() / 3600
)

# Sepsis-3 suspected infection window:
#   antibiotic within 72 h after culture, OR culture within 24 h after abx
suspected_pairs = pairs[
    ((pairs['time_diff_hours'] >= 0) & (pairs['time_diff_hours'] <= 72)) |
    ((pairs['time_diff_hours'] <  0) & (pairs['time_diff_hours'] >= -24))
].copy()

suspected_pairs['suspected_infection_time'] = suspected_pairs['culture_time']
abx_first = suspected_pairs['time_diff_hours'] < 0
suspected_pairs.loc[abx_first, 'suspected_infection_time'] = (
    suspected_pairs.loc[abx_first, 'antibiotic_time']
)

suspected_infection = (
    suspected_pairs
    .groupby('stay_id', as_index=False)['suspected_infection_time']
    .min()
)

suspected_infection.to_csv(
    OUTPUT_DIR / 'suspected_infection.csv', index=False
)
print(f"Suspected infection stays: {len(suspected_infection):,}")
print("Saved: suspected_infection.csv")


# ============================================================
# 6. Restrict SOFA and infection to ICU window
# ============================================================
print("\n" + "=" * 60)
print("STEP 6 — Restricting to ICU window")
print("=" * 60)

# Timestamps
suspected_infection['suspected_infection_time'] = pd.to_datetime(
    suspected_infection['suspected_infection_time'], errors='coerce'
)
sofa_df['charttime_hour'] = pd.to_datetime(
    sofa_df['charttime_hour'], errors='coerce'
)
cohort['intime']  = pd.to_datetime(cohort['intime'],  errors='coerce')
cohort['outtime'] = pd.to_datetime(cohort['outtime'], errors='coerce')

# Restrict SOFA to ICU hours
sofa_df = sofa_df.merge(
    cohort[['stay_id', 'intime', 'outtime']], on='stay_id', how='left'
)
sofa_df['intime']  = pd.to_datetime(sofa_df['intime'])
sofa_df['outtime'] = pd.to_datetime(sofa_df['outtime'])
sofa_df = sofa_df[
    (sofa_df['charttime_hour'] >= sofa_df['intime']) &
    (sofa_df['charttime_hour'] <  sofa_df['outtime'])
].copy()
print(f"SOFA rows after ICU restriction: {sofa_df.shape[0]:,}")

# Restrict suspected infection to ICU window
suspected_infection = suspected_infection.merge(
    cohort[['stay_id', 'intime', 'outtime']], on='stay_id', how='left'
)
suspected_infection['intime']  = pd.to_datetime(suspected_infection['intime'])
suspected_infection['outtime'] = pd.to_datetime(suspected_infection['outtime'])

# If flagged before ICU admission, clip to intime
suspected_infection['suspected_infection_time'] = (
    suspected_infection[['suspected_infection_time', 'intime']].max(axis=1)
)
# Drop if infection timestamp is after ICU discharge
suspected_infection = suspected_infection[
    suspected_infection['suspected_infection_time'] <
    suspected_infection['outtime']
].copy()[['stay_id', 'suspected_infection_time']]

print(f"Suspected infection stays after ICU restriction: "
      f"{len(suspected_infection):,}")


# ============================================================
# 7. Sepsis-3 onset per stay
# ============================================================
print("\n" + "=" * 60)
print("STEP 7 — Sepsis-3 onset")
print("=" * 60)

sofa_pos = sofa_df[sofa_df['sofa_total'] >= 2][
    ['stay_id', 'charttime_hour']
].copy()

sepsis_candidates = sofa_pos.merge(
    suspected_infection[['stay_id', 'suspected_infection_time']],
    on='stay_id', how='inner'
)
sepsis_candidates['suspected_infection_time'] = pd.to_datetime(
    sepsis_candidates['suspected_infection_time']
)
sepsis_candidates['diff_from_infection_hours'] = (
    (sepsis_candidates['charttime_hour'] -
     sepsis_candidates['suspected_infection_time'])
    .dt.total_seconds() / 3600
)

# Sepsis-3 window: SOFA >= 2 within 48 h before or 24 h after infection
sepsis_candidates = sepsis_candidates[
    (sepsis_candidates['diff_from_infection_hours'] >= -48) &
    (sepsis_candidates['diff_from_infection_hours'] <=  24)
].copy()

sepsis_onset = (
    sepsis_candidates
    .groupby('stay_id', as_index=False)['charttime_hour']
    .min()
    .rename(columns={'charttime_hour': 'sepsis_onset_time'})
)

print(f"Sepsis candidates (patient-hours): {len(sepsis_candidates):,}")
print(f"Stays with Sepsis-3 onset        : {len(sepsis_onset):,}")

# Onset hour relative to ICU admission (for reference)
label_df = cohort[['stay_id', 'intime']].merge(
    sepsis_onset, on='stay_id', how='left'
)
label_df['onset_hour'] = (
    (label_df['sepsis_onset_time'] - label_df['intime'])
    .dt.total_seconds() / 3600
)
print("\nOnset hour distribution:")
print(label_df['onset_hour'].dropna().describe())


# ============================================================
# 8. Rolling hourly labels (Option B — PhysioNet framing)
# ============================================================
print("\n" + "=" * 60)
print("STEP 8 — Rolling hourly labels")
print("=" * 60)

PREDICTION_HORIZON_HOURS = 6   # primary horizon (change for sensitivity)

# Build full hourly grid across each stay
hourly_rows = []
for _, row in cohort.iterrows():
    n_hours = max(int(row['icu_los_hours']), 1)
    for t in range(n_hours):
        hourly_rows.append({
            'stay_id':    row['stay_id'],
            'subject_id': row['subject_id'],
            'hour':       t,
            'abs_time':   row['intime'] + pd.Timedelta(hours=t),
        })

hourly_grid = pd.DataFrame(hourly_rows)
print(f"Hourly grid: {len(hourly_grid):,} patient-hours")

hourly_grid = hourly_grid.merge(
    sepsis_onset[['stay_id', 'sepsis_onset_time']],
    on='stay_id', how='left'
)
hourly_grid['sepsis_onset_time'] = pd.to_datetime(
    hourly_grid['sepsis_onset_time']
)
hourly_grid['hours_to_onset'] = (
    (hourly_grid['sepsis_onset_time'] - hourly_grid['abs_time'])
    .dt.total_seconds() / 3600
)

# Label assignment
hourly_grid['label'] = 0

positive_mask = (
    (hourly_grid['hours_to_onset'] > 0) &
    (hourly_grid['hours_to_onset'] <= PREDICTION_HORIZON_HOURS)
)
hourly_grid.loc[positive_mask, 'label'] = 1

# Exclude hours where patient is already septic
already_septic = hourly_grid['hours_to_onset'] <= 0
hourly_grid.loc[already_septic, 'label'] = np.nan

# Require at least 1 h of history (hour 0 = admission, no prior data)
hourly_grid = hourly_grid[hourly_grid['hour'] >= 1].copy()
hourly_grid = hourly_grid.dropna(subset=['label'])
hourly_grid['label'] = hourly_grid['label'].astype(int)

print(f"\nPrediction points : {len(hourly_grid):,}")
print(f"Positive labels   : {hourly_grid['label'].sum():,}")
print(f"Positive rate     : {hourly_grid['label'].mean():.3%}")
print(f"Unique stays      : {hourly_grid['stay_id'].nunique():,}")
print(f"Unique patients   : {hourly_grid['subject_id'].nunique():,}")

sepsis_captured = hourly_grid[hourly_grid['label'] == 1]['stay_id'].nunique()
print(f"\nSepsis stays with ≥1 positive label : {sepsis_captured:,} / "
      f"{len(sepsis_onset):,} "
      f"({sepsis_captured / len(sepsis_onset):.1%})")


# ============================================================
# 9. Subject-level train / val / test split
# ============================================================
print("\n" + "=" * 60)
print("STEP 9 — Train / Val / Test split")
print("=" * 60)

unique_subjects = hourly_grid['subject_id'].unique()

train_subjects, temp_subjects = train_test_split(
    unique_subjects, test_size=0.30, random_state=RANDOM_STATE
)
val_subjects, test_subjects = train_test_split(
    temp_subjects,  test_size=0.50, random_state=RANDOM_STATE
)

train_stays = hourly_grid[
    hourly_grid['subject_id'].isin(train_subjects)
]['stay_id'].unique()
val_stays   = hourly_grid[
    hourly_grid['subject_id'].isin(val_subjects)
]['stay_id'].unique()
test_stays  = hourly_grid[
    hourly_grid['subject_id'].isin(test_subjects)
]['stay_id'].unique()

# Leakage checks
assert len(set(train_stays) & set(test_stays)) == 0, \
    "LEAKAGE: train/test overlap"
assert len(set(train_stays) & set(val_stays))  == 0, \
    "LEAKAGE: train/val overlap"
assert len(set(val_stays)   & set(test_stays)) == 0, \
    "LEAKAGE: val/test overlap"
print("No patient leakage confirmed ✓")

print(f"\nTrain : {len(train_subjects):,} patients | "
      f"{len(train_stays):,} stays")
print(f"Val   : {len(val_subjects):,} patients | "
      f"{len(val_stays):,} stays")
print(f"Test  : {len(test_subjects):,} patients | "
      f"{len(test_stays):,} stays")

for name, subjects in [('Train', train_subjects),
                        ('Val',   val_subjects),
                        ('Test',  test_subjects)]:
    split = hourly_grid[hourly_grid['subject_id'].isin(subjects)]
    print(f"{name:5s} | {len(split):>9,} points | "
          f"positive rate {split['label'].mean():.3%}")

# Save split assignments
split_df = pd.DataFrame({
    'subject_id': np.concatenate(
        [train_subjects, val_subjects, test_subjects]
    ),
    'split': (
        ['train'] * len(train_subjects) +
        ['val']   * len(val_subjects)   +
        ['test']  * len(test_subjects)
    ),
})
split_df.to_csv(OUTPUT_DIR / 'subject_splits.csv', index=False)
print("\nSaved: subject_splits.csv")

# Attach split column to hourly_grid and save
hourly_grid = hourly_grid.merge(split_df, on='subject_id', how='left')
hourly_grid.to_csv(OUTPUT_DIR / 'hourly_labels.csv', index=False)
print("Saved: hourly_labels.csv  (includes split column)")

print("\n" + "=" * 60)
print("PREPROCESSING COMPLETE")
print("=" * 60)
print(f"Output directory: {OUTPUT_DIR}")
print("Files written:")
for f in sorted(OUTPUT_DIR.glob('*.csv')) + sorted(OUTPUT_DIR.glob('*.npy')):
    size_mb = f.stat().st_size / 1_048_576
    print(f"  {f.name:<40s}  {size_mb:>7.1f} MB")
