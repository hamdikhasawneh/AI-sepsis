"""
feature_engineering.py
=======================
Library of all feature-engineering functions extracted from
02_feature_engineering.ipynb.

Usage in model_training (file 3):
    from feature_engineering import (
        compute_temporal_features,
        compute_sofa_features,
        compute_static_features,
        compute_missingness_features,
        compute_lab_features,
        build_feature_table,
        impute_with_medians,
        load_extra_labs,
        load_urine_output_features,
        load_vasopressor_features,
        load_ventilation_features,
        load_blood_culture_features,
    )
"""

import numpy as np
import pandas as pd
import zipfile
from pathlib import Path
from scipy.stats import linregress


# ── Constants ────────────────────────────────────────────────────────────────

FEATURE_COLS = [
    'abp_dia', 'abp_mean', 'abp_sys',
    'heart_rate', 'resp_rate', 'spo2', 'temp_c'
]

EXTRA_LAB_ITEMIDS = [50813, 52442, 51301]   # Lactate (x2), WBC

EXTRA_LAB_ITEMID_TO_NAME = {
    50813: 'lactate',
    52442: 'lactate',
    51301: 'wbc',
}

URINE_ITEMIDS = [
    226559, 226560, 226561, 226584, 226563, 226564,
    226565, 226567, 226557, 226558, 227488, 227489,
]

VENT_PROC_ITEMIDS = [225792, 225794]   # Invasive / non-invasive ventilation

LEAKAGE_COLS = [
    'y_6h', 'y_12h', 'y_24h',
    'eligible_6h', 'eligible_12h', 'eligible_24h',
    'icu_los_hours',
]


# ── Section 1: Load extra labs (Lactate + WBC) ───────────────────────────────

def load_extra_labs(
    lab_zip_path: Path,
    cohort: pd.DataFrame,
    output_file: Path,
    chunk_size: int = 100_000,
    force: bool = False,
) -> pd.DataFrame:
    """
    Extract lactate and WBC from labevents.csv (inside zip) for cohort stays.
    Saves result to output_file and returns the cleaned wide-format DataFrame
    filtered to the first 24 hours of each ICU stay.

    Parameters
    ----------
    lab_zip_path : Path to chartevents_labevents.zip
    cohort       : DataFrame with columns [subject_id, hadm_id, stay_id, intime]
    output_file  : Path to save/load extra_labs_filtered.csv
    chunk_size   : Rows per chunk when reading labevents
    force        : If True, re-extract even if output_file already exists
    """
    if force or not output_file.exists():
        if output_file.exists():
            output_file.unlink()

        stay_ids = set(cohort['stay_id'].dropna().unique())
        first_chunk = True

        with zipfile.ZipFile(lab_zip_path, 'r') as z:
            with z.open('Cleaned/labevents.csv') as f:
                for i, chunk in enumerate(
                    pd.read_csv(
                        f,
                        chunksize=chunk_size,
                        usecols=['subject_id', 'hadm_id', 'charttime', 'itemid', 'valuenum']
                    )
                ):
                    chunk = chunk[chunk['itemid'].isin(EXTRA_LAB_ITEMIDS)]
                    chunk = chunk.merge(
                        cohort[['subject_id', 'hadm_id', 'stay_id']],
                        on=['subject_id', 'hadm_id'],
                        how='inner'
                    )
                    if not chunk.empty:
                        chunk.to_csv(output_file, mode='a', header=first_chunk, index=False)
                        first_chunk = False
                    print(f'  chunk {i + 1} done', end='\r')
        print(f'\nextra_labs_filtered.csv saved → {output_file}')

    extra_labs = pd.read_csv(output_file)
    extra_labs['charttime'] = pd.to_datetime(extra_labs['charttime'])

    # Drop nulls and map item IDs to names
    extra_labs = extra_labs.dropna(subset=['valuenum'])
    extra_labs['lab_name'] = extra_labs['itemid'].map(EXTRA_LAB_ITEMID_TO_NAME)

    # Floor to hourly bins and aggregate
    extra_labs['charttime_hour'] = extra_labs['charttime'].dt.floor('h')
    extra_labs_hourly = (
        extra_labs
        .groupby(['stay_id', 'charttime_hour', 'lab_name'])['valuenum']
        .mean()
        .reset_index()
    )

    # Pivot wide
    extra_labs_wide = extra_labs_hourly.pivot_table(
        index=['stay_id', 'charttime_hour'],
        columns='lab_name',
        values='valuenum'
    ).reset_index()
    extra_labs_wide.columns.name = None

    # Merge intime and compute hours since admit
    extra_labs_wide['charttime_hour'] = pd.to_datetime(extra_labs_wide['charttime_hour'])
    extra_labs_wide = extra_labs_wide.merge(
        cohort[['stay_id', 'intime']], on='stay_id', how='left'
    )
    extra_labs_wide['intime'] = pd.to_datetime(extra_labs_wide['intime'])
    extra_labs_wide['hours_since_admit'] = (
        (extra_labs_wide['charttime_hour'] - extra_labs_wide['intime'])
        .dt.total_seconds() / 3600
    )

    # Filter to first 24 h
    extra_labs_24h = extra_labs_wide[
        (extra_labs_wide['hours_since_admit'] >= 0) &
        (extra_labs_wide['hours_since_admit'] < 24)
    ].copy()
    extra_labs_24h['hour'] = extra_labs_24h['hours_since_admit'].astype(int)

    # Forward-fill within each stay
    extra_labs_24h = extra_labs_24h.sort_values(['stay_id', 'hour'])
    for lab in ['lactate', 'wbc']:
        if lab in extra_labs_24h.columns:
            extra_labs_24h[lab] = (
                extra_labs_24h.groupby('stay_id')[lab]
                .transform(lambda x: x.ffill())
            )

    print(f'Extra labs 24h shape: {extra_labs_24h.shape} | '
          f'stays: {extra_labs_24h["stay_id"].nunique():,}')
    return extra_labs_24h


# ── Section 2: Temporal vital-sign features ──────────────────────────────────

def compute_temporal_features(
    vitals_complete: pd.DataFrame,
    feature_cols: list = FEATURE_COLS,
) -> pd.DataFrame:
    """
    Per-stay summary statistics and linear trends over the first 24 h.

    Slope is computed ONLY on rows where the sensor actually recorded a
    value (uses 'observed_{col}' boolean column if present; falls back to
    all non-NaN rows).

    Parameters
    ----------
    vitals_complete : hourly vitals DataFrame with columns [stay_id, hour, *feature_cols]
    feature_cols    : list of vital-sign column names
    """
    records = []
    for stay_id, group in vitals_complete.groupby('stay_id'):
        group = group.sort_values('hour')
        row = {'stay_id': stay_id}
        hours = group['hour'].values.astype(float)

        for col in feature_cols:
            vals = group[col].values.astype(float)
            row[f'{col}_mean'] = np.nanmean(vals)
            row[f'{col}_std']  = np.nanstd(vals)
            row[f'{col}_min']  = np.nanmin(vals)
            row[f'{col}_max']  = np.nanmax(vals)
            row[f'{col}_last'] = vals[-1] if not np.isnan(vals[-1]) else np.nanmean(vals)

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


# ── Section 3: SOFA summary features ─────────────────────────────────────────

def _score_platelets(x):
    if pd.isna(x): return np.nan
    if x >= 150:   return 0
    if x >= 100:   return 1
    if x >= 50:    return 2
    if x >= 20:    return 3
    return 4

def _score_bilirubin(x):
    if pd.isna(x): return np.nan
    if x < 1.2:    return 0
    if x < 2.0:    return 1
    if x < 6.0:    return 2
    if x < 12.0:   return 3
    return 4

def _score_creatinine(x):
    if pd.isna(x): return np.nan
    if x < 1.2:    return 0
    if x < 2.0:    return 1
    if x < 3.5:    return 2
    if x < 5.0:    return 3
    return 4


def compute_sofa_features(
    sofa_labs: pd.DataFrame,
    cohort: pd.DataFrame,
) -> pd.DataFrame:
    """
    Compute SOFA lab sub-scores (platelets, bilirubin, creatinine) and
    return per-stay summary statistics over the first 24 h.

    Parameters
    ----------
    sofa_labs : DataFrame from sofa_labs_hourly_wide.csv with
                columns [stay_id, charttime_hour, platelets, bilirubin, creatinine]
    cohort    : DataFrame with [stay_id, intime]
    """
    sofa = sofa_labs.merge(cohort[['stay_id', 'intime']], on='stay_id', how='left')
    sofa['intime']         = pd.to_datetime(sofa['intime'])
    sofa['charttime_hour'] = pd.to_datetime(sofa['charttime_hour'])
    sofa['hours_since_admit'] = (
        (sofa['charttime_hour'] - sofa['intime']).dt.total_seconds() / 3600
    )

    sofa_24h = sofa[
        (sofa['hours_since_admit'] >= 0) &
        (sofa['hours_since_admit'] < 24)
    ].copy()
    sofa_24h['hour'] = sofa_24h['hours_since_admit'].astype(int)

    sofa_24h['sofa_platelets']  = sofa_24h['platelets'].apply(_score_platelets)
    sofa_24h['sofa_bilirubin']  = sofa_24h['bilirubin'].apply(_score_bilirubin)
    sofa_24h['sofa_creatinine'] = sofa_24h['creatinine'].apply(_score_creatinine)
    sofa_24h['sofa_lab_total']  = sofa_24h[
        ['sofa_platelets', 'sofa_bilirubin', 'sofa_creatinine']
    ].sum(axis=1, min_count=1)

    records = []
    for stay_id, group in sofa_24h.groupby('stay_id'):
        group = group.sort_values('hour')
        vals  = group['sofa_lab_total'].values.astype(float)
        h     = group['hour'].values.astype(float)
        obs   = ~np.isnan(vals)

        row = {
            'stay_id':          stay_id,
            'sofa_mean_24h':    np.nanmean(vals),
            'sofa_max_24h':     np.nanmax(vals),
            'sofa_last_24h':    vals[obs][-1] if obs.any() else np.nan,
        }

        if obs.sum() >= 2:
            slope, *_ = linregress(h[obs], vals[obs])
            row['sofa_slope_24h'] = slope
        else:
            row['sofa_slope_24h'] = np.nan

        records.append(row)
    return pd.DataFrame(records)


# ── Section 4: Static patient features ───────────────────────────────────────

def compute_static_features(cohort: pd.DataFrame) -> pd.DataFrame:
    """
    Build static demographic features from the cohort table.
    icu_los_hours is excluded to prevent future leakage.

    Parameters
    ----------
    cohort : DataFrame with [stay_id, anchor_age, gender, admission_type]
    """
    static = cohort[[
        'stay_id', 'anchor_age', 'gender', 'admission_type',
    ]].copy()

    static['gender_male'] = (static['gender'].str.upper() == 'M').astype(int)

    admission_dummies = pd.get_dummies(
        static['admission_type'].str.lower().str.replace(' ', '_'),
        prefix='adm_type'
    ).astype(int)
    static = pd.concat([static, admission_dummies], axis=1)

    static = static.drop(columns=['gender', 'admission_type'])
    return static


# ── Section 5: Missingness indicators ────────────────────────────────────────

def compute_missingness_features(
    vitals_complete: pd.DataFrame,
    feature_cols: list = FEATURE_COLS,
) -> pd.DataFrame:
    """
    Fraction of hours with missing readings for each vital sign.

    Parameters
    ----------
    vitals_complete : hourly vitals DataFrame with [stay_id, *feature_cols]
    feature_cols    : list of vital-sign column names
    """
    records = []
    for stay_id, group in vitals_complete.groupby('stay_id'):
        row = {'stay_id': stay_id}
        for col in feature_cols:
            row[f'{col}_missing_frac'] = group[col].isna().sum() / len(group)
        records.append(row)
    return pd.DataFrame(records)


# ── Section 6: Lab features (Lactate + WBC) ──────────────────────────────────

def compute_lab_features(extra_labs_24h: pd.DataFrame) -> pd.DataFrame:
    """
    Per-stay summary statistics for lactate and WBC over the first 24 h.
    Slope is computed only on observed (non-imputed) values.
    Clinical threshold flags are added for lactate and WBC.

    Parameters
    ----------
    extra_labs_24h : forward-filled lab DataFrame from load_extra_labs()
                     with columns [stay_id, hour, lactate, wbc]
    """
    records = []
    for stay_id, group in extra_labs_24h.groupby('stay_id'):
        row = {'stay_id': stay_id}

        for lab in ['lactate', 'wbc']:
            if lab not in group.columns:
                for suffix in ['mean', 'max', 'min', 'first', 'last', 'count', 'missing', 'slope']:
                    row[f'{lab}_{suffix}'] = np.nan if suffix != 'count' else 0
                row[f'{lab}_missing'] = 1
                continue

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

        # Clinical threshold flags (computed on observed values)
        lactate_vals = group['lactate'].dropna().values if 'lactate' in group.columns else np.array([])
        wbc_vals     = group['wbc'].dropna().values     if 'wbc'     in group.columns else np.array([])

        row['lactate_elevated'] = int(any(lactate_vals > 2.0))
        row['lactate_critical'] = int(any(lactate_vals > 4.0))
        row['wbc_high']         = int(any(wbc_vals > 12.0))
        row['wbc_low']          = int(any(wbc_vals < 4.0))

        records.append(row)
    return pd.DataFrame(records)


# ── Section 7: Gap features ───────────────────────────────────────────────────

def load_urine_output_features(
    data_dir: Path,
    cohort: pd.DataFrame,
    output_file: Path,
    force: bool = False,
) -> pd.DataFrame:
    """
    Extract and summarise urine output over the first 24 h.
    Returns a per-stay DataFrame with UO summary columns.
    """
    if force or not output_file.exists():
        stay_ids    = set(cohort['stay_id'].dropna().unique())
        first_chunk = True
        with open(data_dir / 'outputevents.csv') as f:
            for i, chunk in enumerate(pd.read_csv(
                f, chunksize=100_000,
                usecols=['stay_id', 'charttime', 'itemid', 'value']
            )):
                chunk = chunk[
                    chunk['stay_id'].isin(stay_ids) &
                    chunk['itemid'].isin(URINE_ITEMIDS)
                ]
                if not chunk.empty:
                    chunk.to_csv(output_file, mode='a', header=first_chunk, index=False)
                    first_chunk = False
            print(f'UO chunk {i + 1}', end='\r')
        print(f'\nurine_output_filtered.csv saved → {output_file}')

    uo_df = pd.read_csv(output_file)
    uo_df['charttime'] = pd.to_datetime(uo_df['charttime'])
    uo_df = uo_df.merge(cohort[['stay_id', 'intime']], on='stay_id', how='left')
    uo_df['intime'] = pd.to_datetime(uo_df['intime'])
    uo_df['hours_since_admit'] = (
        (uo_df['charttime'] - uo_df['intime']).dt.total_seconds() / 3600
    )

    uo_24h = uo_df[
        (uo_df['hours_since_admit'] >= 0) &
        (uo_df['hours_since_admit'] < 24)
    ].copy()
    uo_24h['value'] = pd.to_numeric(uo_24h['value'], errors='coerce').clip(lower=0, upper=10_000)

    uo_features = (
        uo_24h.groupby('stay_id')['value']
        .agg(
            uo_total_24h='sum',
            uo_mean_hourly=lambda x: x.sum() / 24,
            uo_min_hourly='min',
            uo_count='count',
        )
        .reset_index()
    )
    uo_features['oliguria_flag'] = (uo_features['uo_mean_hourly'] < 0.5).astype(int)
    return uo_features


def load_vasopressor_features(
    output_dir: Path,
    cohort: pd.DataFrame,
) -> pd.DataFrame:
    """
    Load vasopressor binary flag from vasopressors_filtered.csv (if present).
    Returns a per-stay DataFrame with [stay_id, vaso_events_24h, vasopressor_flag].
    """
    vaso_path = output_dir / 'vasopressors_filtered.csv'
    if not vaso_path.exists():
        print('WARNING: vasopressors_filtered.csv not found — flag will be all zeros')
        return pd.DataFrame({'stay_id': cohort['stay_id'], 'vasopressor_flag': 0})

    vaso_df = pd.read_csv(vaso_path)
    vaso_df['starttime'] = pd.to_datetime(vaso_df['starttime'])
    vaso_df = vaso_df.merge(cohort[['stay_id', 'intime']], on='stay_id', how='left')
    vaso_df['intime'] = pd.to_datetime(vaso_df['intime'])
    vaso_df['hours_since_admit'] = (
        (vaso_df['starttime'] - vaso_df['intime']).dt.total_seconds() / 3600
    )
    vaso_24h = vaso_df[
        (vaso_df['hours_since_admit'] >= 0) &
        (vaso_df['hours_since_admit'] < 24)
    ]
    vaso_features = (
        vaso_24h.groupby('stay_id').size()
        .reset_index(name='vaso_events_24h')
    )
    vaso_features['vasopressor_flag'] = 1
    return vaso_features


def load_ventilation_features(
    data_dir: Path,
    cohort: pd.DataFrame,
) -> pd.DataFrame:
    """
    Extract ventilation status over the first 24 h.
    Tries ventilation.csv first, falls back to procedureevents.csv.
    Returns a per-stay DataFrame with [stay_id, ventilated_flag].
    """
    vent_path      = data_dir / 'ventilation.csv'
    vent_proc_path = data_dir / 'procedureevents.csv'

    if vent_path.exists():
        vent_raw = pd.read_csv(vent_path, usecols=['stay_id', 'starttime', 'ventilation_status'])
        vent_raw['starttime'] = pd.to_datetime(vent_raw['starttime'])
        vent_raw = vent_raw.merge(cohort[['stay_id', 'intime']], on='stay_id', how='left')
        vent_raw['intime'] = pd.to_datetime(vent_raw['intime'])
        vent_raw['hours_since_admit'] = (
            (vent_raw['starttime'] - vent_raw['intime']).dt.total_seconds() / 3600
        )
        vent_24h = vent_raw[
            (vent_raw['hours_since_admit'] >= 0) &
            (vent_raw['hours_since_admit'] < 24) &
            (vent_raw['ventilation_status'] == 'InvasiveVent')
        ]
        print('Ventilation loaded from ventilation.csv')

    elif vent_proc_path.exists():
        vent_raw = pd.read_csv(vent_proc_path, usecols=['stay_id', 'starttime', 'itemid'])
        vent_raw = vent_raw[vent_raw['itemid'].isin(VENT_PROC_ITEMIDS)]
        vent_raw['starttime'] = pd.to_datetime(vent_raw['starttime'])
        vent_raw = vent_raw.merge(cohort[['stay_id', 'intime']], on='stay_id', how='left')
        vent_raw['intime'] = pd.to_datetime(vent_raw['intime'])
        vent_raw['hours_since_admit'] = (
            (vent_raw['starttime'] - vent_raw['intime']).dt.total_seconds() / 3600
        )
        vent_24h = vent_raw[
            (vent_raw['hours_since_admit'] >= 0) &
            (vent_raw['hours_since_admit'] < 24)
        ]
        print('Ventilation loaded from procedureevents.csv')

    else:
        print('WARNING: No ventilation source found — flag will be all zeros')
        return pd.DataFrame({'stay_id': cohort['stay_id'], 'ventilated_flag': 0})

    ventilated_stays = set(vent_24h['stay_id'].unique())
    result = cohort[['stay_id']].copy()
    result['ventilated_flag'] = result['stay_id'].isin(ventilated_stays).astype(int)
    return result


def load_blood_culture_features(
    data_dir: Path,
    cohort: pd.DataFrame,
) -> pd.DataFrame:
    """
    Extract blood culture draw and positivity flags from microbiologyevents.csv.
    Returns a per-stay DataFrame with [stay_id, blood_culture_drawn, blood_culture_positive].

    Note: blood_culture_positive reflects the charted result timestamp in MIMIC,
    which may lag the actual draw by 48–72 h. Review before using as a feature
    in short-horizon prediction tasks.
    """
    micro_path = data_dir / 'microbiologyevents.csv'
    if not micro_path.exists():
        print('WARNING: microbiologyevents.csv not found — culture flags will be all zeros')
        result = cohort[['stay_id']].copy()
        result['blood_culture_drawn']    = 0
        result['blood_culture_positive'] = 0
        return result

    micro = pd.read_csv(
        micro_path,
        usecols=['stay_id', 'charttime', 'spec_type_desc', 'org_name']
    )
    micro = micro[micro['spec_type_desc'].str.contains('blood', case=False, na=False)]
    micro['charttime'] = pd.to_datetime(micro['charttime'])
    micro = micro.merge(cohort[['stay_id', 'intime']], on='stay_id', how='left')
    micro['intime'] = pd.to_datetime(micro['intime'])
    micro['hours_since_admit'] = (
        (micro['charttime'] - micro['intime']).dt.total_seconds() / 3600
    )
    micro_24h = micro[
        (micro['hours_since_admit'] >= 0) &
        (micro['hours_since_admit'] < 24)
    ]

    drawn_stays    = set(micro_24h['stay_id'].unique())
    positive_stays = set(micro_24h[micro_24h['org_name'].notna()]['stay_id'].unique())

    result = cohort[['stay_id']].copy()
    result['blood_culture_drawn']    = result['stay_id'].isin(drawn_stays).astype(int)
    result['blood_culture_positive'] = result['stay_id'].isin(positive_stays).astype(int)
    return result


# ── Section 8: Assemble and impute ───────────────────────────────────────────

def build_feature_table(
    stay_ids_order: list,
    temporal_features: pd.DataFrame,
    sofa_features: pd.DataFrame,
    static_features: pd.DataFrame,
    missingness_features: pd.DataFrame,
    lab_features: pd.DataFrame,
    gap_feature_dfs: list = None,
) -> pd.DataFrame:
    """
    Left-join all feature DataFrames onto the canonical stay_id order.

    Parameters
    ----------
    stay_ids_order     : list of stay_ids defining row order
    temporal_features  : output of compute_temporal_features()
    sofa_features      : output of compute_sofa_features()
    static_features    : output of compute_static_features()
    missingness_features : output of compute_missingness_features()
    lab_features       : output of compute_lab_features()
    gap_feature_dfs    : optional list of additional per-stay DataFrames
                         (urine output, vasopressor, ventilation, culture)
    """
    all_features = pd.DataFrame({'stay_id': stay_ids_order})

    for df in [temporal_features, sofa_features, static_features,
               missingness_features, lab_features]:
        all_features = all_features.merge(df, on='stay_id', how='left')

    if gap_feature_dfs:
        for df in gap_feature_dfs:
            all_features = all_features.merge(df, on='stay_id', how='left')

    print(f'Feature table shape: {all_features.shape} | '
          f'features: {all_features.shape[1] - 1}')
    return all_features


def impute_with_medians(
    all_features: pd.DataFrame,
    split_df: pd.DataFrame,
    cohort: pd.DataFrame,
    feature_cols: list = None,
) -> tuple[pd.DataFrame, pd.Series]:
    """
    Fill remaining NaN values with the median computed on training stays ONLY.
    Returns the imputed DataFrame and the medians Series (save for inference).

    Parameters
    ----------
    all_features  : output of build_feature_table()
    split_df      : DataFrame with [subject_id, split] where split ∈ {train, val, test}
    cohort        : DataFrame with [stay_id, subject_id] to map subject→stay
    feature_cols  : columns to impute; defaults to all non-stay_id columns
    """
    if feature_cols is None:
        feature_cols = [c for c in all_features.columns if c != 'stay_id']

    # split_df is subject-level — map to stay-level via cohort
    stay_to_split  = cohort[['stay_id', 'subject_id']].merge(split_df, on='subject_id', how='left')
    train_stay_ids = set(stay_to_split[stay_to_split['split'] == 'train']['stay_id'])
    train_mask     = all_features['stay_id'].isin(train_stay_ids)
    print(f'Training stays for median computation: {train_mask.sum():,}')

    medians = all_features.loc[train_mask, feature_cols].median()

    all_features[feature_cols] = all_features[feature_cols].fillna(medians)
    print(f'Missing after imputation: {all_features[feature_cols].isnull().sum().sum()}')
    return all_features, medians


def assert_no_leakage(all_features: pd.DataFrame) -> None:
    """Raise AssertionError if any known leakage column is present."""
    leaked = [c for c in all_features.columns if c in LEAKAGE_COLS]
    assert len(leaked) == 0, f'LEAKAGE DETECTED: {leaked}'
    print('Leakage check passed ✓')
