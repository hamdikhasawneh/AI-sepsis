preprocessing.py
ICU Sepsis Detection Project — Preprocessing Library
-----------------------------------------------------
Converts all preprocessing steps from 01_data_preprocessing.ipynb into
importable functions. The feature engineering notebook can call these
directly instead of re-running the raw notebook.

Usage (in 02_feature_engineering.ipynb):
    from preprocessing import (
        load_cohort,
        load_vitals_complete,
        load_sofa,
        load_sepsis_labels,
        build_X_array,
        run_full_pipeline,
    )
"""

from pathlib import Path
import zipfile

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Default paths  (override by passing arguments to each function)
# ---------------------------------------------------------------------------
_DEFAULT_DATA_DIR   = Path("/content/drive/MyDrive/gp/Cleaned")
_DEFAULT_OUTPUT_DIR = Path("/content/drive/MyDrive/mimic_iv_processed")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VITAL_ITEMIDS = [
    220045,  # Heart Rate
    220210,  # Respiratory Rate
    223762,  # Temperature Celsius
    220277,  # SpO2 (pulse oximetry)
    220050,  # ABP Systolic
    220051,  # ABP Diastolic
    220052,  # ABP Mean
]

ITEMID_TO_VITAL = {
    220045: "heart_rate",
    220210: "resp_rate",
    223762: "temp_c",
    220277: "spo2",
    220050: "abp_sys",
    220051: "abp_dia",
    220052: "abp_mean",
}

FEATURE_COLS = ["abp_dia", "abp_mean", "abp_sys", "heart_rate", "resp_rate", "spo2", "temp_c"]

SOFA_LAB_ITEMIDS = {
    "platelets":  [51265],
    "bilirubin":  [50885, 53089],
    "creatinine": [50912, 52546],
}

LAB_ITEMID_TO_NAME = {
    51265: "platelets",
    50885: "bilirubin",
    53089: "bilirubin",
    50912: "creatinine",
    52546: "creatinine",
}

GCS_ITEMIDS = [220739, 223900, 223901]
GCS_ITEMID_TO_COMPONENT = {220739: "eye", 223900: "verbal", 223901: "motor"}

ANTIBIOTIC_KEYWORDS = [
    "cillin", "cef", "cefepime", "ceftriaxone", "ceftazidime",
    "vancomycin", "meropenem", "imipenem", "ertapenem",
    "piperacillin", "tazobactam", "zosyn",
    "ciprofloxacin", "levofloxacin", "moxifloxacin",
    "azithromycin", "clarithromycin",
    "metronidazole", "clindamycin",
    "gentamicin", "amikacin", "tobramycin",
    "doxycycline", "tigecycline",
    "trimethoprim", "sulfamethoxazole",
    "linezolid", "daptomycin",
]

SEPSIS_ICD_PATTERNS = [
    "99591", "99592", "78552",   # ICD-9
    "A40",   "A41",   "R652",    # ICD-10
]


# ===========================================================================
# SECTION 1 — Cohort
# ===========================================================================

def build_cohort(
    data_dir: Path = _DEFAULT_DATA_DIR,
    output_dir: Path = _DEFAULT_OUTPUT_DIR,
    min_los_hours: float = 4.0,
    min_age: int = 18,
    save: bool = True,
) -> pd.DataFrame:
    """
    Merge icustays + admissions + patients, apply inclusion criteria,
    compute ICU length-of-stay, and (optionally) save icu_cohort.csv.

    Returns
    -------
    cohort : pd.DataFrame
        One row per ICU stay, filtered to adults with LOS >= min_los_hours.
    """
    patients   = pd.read_csv(data_dir / "patients.csv")
    admissions = pd.read_csv(data_dir / "admissions.csv")
    icustays   = pd.read_csv(data_dir / "icustays.csv")

    cohort = (
        icustays
        .merge(admissions, on=["subject_id", "hadm_id"], how="left")
        .merge(patients,   on="subject_id",               how="left")
    )

    # Parse datetime columns
    for col in ["intime", "outtime", "admittime", "dischtime"]:
        cohort[col] = pd.to_datetime(cohort[col])

    # Derived features
    cohort["icu_los_hours"] = (
        (cohort["outtime"] - cohort["intime"]).dt.total_seconds() / 3600
    )

    # Inclusion filters
    cohort = cohort[cohort["icu_los_hours"] >= min_los_hours]
    cohort = cohort[cohort["anchor_age"]    >= min_age]
    cohort = cohort.reset_index(drop=True)

    if save:
        output_dir.mkdir(parents=True, exist_ok=True)
        cohort.to_csv(output_dir / "icu_cohort.csv", index=False)
        print(f"[build_cohort] Saved icu_cohort.csv — shape: {cohort.shape}")

    return cohort


def load_cohort(output_dir: Path = _DEFAULT_OUTPUT_DIR) -> pd.DataFrame:
    """Load a previously saved cohort CSV."""
    path = output_dir / "icu_cohort.csv"
    cohort = pd.read_csv(path)
    for col in ["intime", "outtime", "admittime", "dischtime"]:
        if col in cohort.columns:
            cohort[col] = pd.to_datetime(cohort[col])
    print(f"[load_cohort] Loaded — shape: {cohort.shape}")
    return cohort


# ===========================================================================
# SECTION 2 — Vital Signs
# ===========================================================================

def extract_vitals_filtered(
    cohort: pd.DataFrame,
    data_dir: Path = _DEFAULT_DATA_DIR,
    output_dir: Path = _DEFAULT_OUTPUT_DIR,
    chunk_size: int = 100_000,
) -> Path:
    """
    Stream chartevents.csv (inside the zip) and write only the rows that
    match our cohort stay_ids and VITAL_ITEMIDS to vitals_filtered.csv.

    Returns path to the saved file.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "vitals_filtered.csv"
    if output_file.exists():
        output_file.unlink()

    stay_ids = set(cohort["stay_id"].dropna().unique())
    zip_path = data_dir / "chartevents_labevents.zip"
    first_chunk = True

    with zipfile.ZipFile(zip_path, "r") as z:
        with z.open("Cleaned/chartevents.csv") as f:
            for i, chunk in enumerate(
                pd.read_csv(
                    f,
                    chunksize=chunk_size,
                    usecols=["subject_id", "hadm_id", "stay_id",
                             "charttime", "itemid", "valuenum", "valueuom"],
                )
            ):
                chunk = chunk[
                    chunk["stay_id"].isin(stay_ids) &
                    chunk["itemid"].isin(VITAL_ITEMIDS)
                ]
                if not chunk.empty:
                    chunk.to_csv(output_file, mode="a", header=first_chunk, index=False)
                    first_chunk = False
                print(f"  chunk {i+1} done", end="\r")

    print(f"\n[extract_vitals_filtered] Saved vitals_filtered.csv")
    return output_file


def build_vitals_complete(
    cohort: pd.DataFrame,
    data_dir: Path = _DEFAULT_DATA_DIR,
    output_dir: Path = _DEFAULT_OUTPUT_DIR,
    min_hours: int = 12,
    save: bool = True,
) -> pd.DataFrame:
    """
    Full vital-sign pipeline:
      1. Load vitals_filtered.csv (extract it first if missing).
      2. Map itemids → feature names, floor to hourly bins.
      3. Aggregate per (stay_id, hour), pivot wide.
      4. Restrict to first 24 h post-admission.
      5. Drop stays with < min_hours valid hours.
      6. Reindex each stay to a full 0-23 hour grid.
      7. Forward-fill then backward-fill missing hours.

    Returns
    -------
    vitals_complete : pd.DataFrame
        Columns: stay_id, hour, abp_dia, abp_mean, abp_sys,
                 heart_rate, resp_rate, spo2, temp_c
        Every stay has exactly 24 rows.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    filtered_path = output_dir / "vitals_filtered.csv"
    if not filtered_path.exists():
        print("[build_vitals_complete] vitals_filtered.csv not found — extracting...")
        extract_vitals_filtered(cohort, data_dir, output_dir)

    vitals = pd.read_csv(filtered_path)
    vitals["feature_name"] = vitals["itemid"].map(ITEMID_TO_VITAL)
    vitals["charttime"]    = pd.to_datetime(vitals["charttime"])
    vitals["charttime_hour"] = vitals["charttime"].dt.floor("h")

    # Hourly mean per feature
    vitals_hourly = (
        vitals
        .groupby(["stay_id", "charttime_hour", "feature_name"])["valuenum"]
        .mean()
        .reset_index()
    )

    # Wide format
    vitals_wide = vitals_hourly.pivot_table(
        index=["stay_id", "charttime_hour"],
        columns="feature_name",
        values="valuenum",
    ).reset_index()
    vitals_wide.columns.name = None

    # Merge ICU admission time
    cohort_small = cohort[["stay_id", "intime"]].copy()
    vitals_wide  = vitals_wide.merge(cohort_small, on="stay_id", how="left")
    vitals_wide["charttime_hour"] = pd.to_datetime(vitals_wide["charttime_hour"])
    vitals_wide["intime"]         = pd.to_datetime(vitals_wide["intime"])
    vitals_wide["hours_since_admit"] = (
        (vitals_wide["charttime_hour"] - vitals_wide["intime"]).dt.total_seconds() / 3600
    )

    # First 24 hours only
    vitals_24h = vitals_wide[
        (vitals_wide["hours_since_admit"] >= 0) &
        (vitals_wide["hours_since_admit"] <  24)
    ].copy()
    vitals_24h["hour"] = vitals_24h["hours_since_admit"].astype(int)
    vitals_24h = vitals_24h[["stay_id", "hour"] + FEATURE_COLS].copy()

    # Re-aggregate in case of duplicates within the same integer hour
    vitals_24h = (
        vitals_24h
        .groupby(["stay_id", "hour"], as_index=False)
        .mean(numeric_only=True)
    )

    # Drop stays with too few observed hours
    valid_stays = (
        vitals_24h.groupby("stay_id")["hour"].nunique()
    )
    valid_stays = valid_stays[valid_stays >= min_hours].index
    vitals_24h  = vitals_24h[vitals_24h["stay_id"].isin(valid_stays)]

    # Reindex each stay to a full 0-23 grid
    records = []
    for stay_id, group in vitals_24h.groupby("stay_id"):
        group = group.set_index("hour").reindex(range(24))
        group["stay_id"] = stay_id
        records.append(group.reset_index())
    vitals_complete = pd.concat(records, ignore_index=True)

    # Forward-fill then backward-fill within each stay
    vitals_complete = vitals_complete.sort_values(["stay_id", "hour"])
    vitals_complete = (
        vitals_complete
        .groupby("stay_id", group_keys=False)
        .apply(lambda x: x.ffill().bfill())
    )
    vitals_complete.reset_index(drop=True, inplace=True)

    if save:
        vitals_complete.to_csv(output_dir / "vitals_complete.csv", index=False)
        print(f"[build_vitals_complete] Saved vitals_complete.csv — shape: {vitals_complete.shape}")

    return vitals_complete


def load_vitals_complete(output_dir: Path = _DEFAULT_OUTPUT_DIR) -> pd.DataFrame:
    """Load a previously saved vitals_complete.csv."""
    df = pd.read_csv(output_dir / "vitals_complete.csv")
    print(f"[load_vitals_complete] Loaded — shape: {df.shape}")
    return df


def build_X_array(vitals_complete: pd.DataFrame) -> tuple[np.ndarray, list]:
    """
    Convert vitals_complete into a 3-D NumPy array suitable for LSTM input.

    Returns
    -------
    X : np.ndarray, shape (n_stays, 24, 7)
    stay_ids_order : list  — ordered list of stay_ids matching X rows
    """
    vitals_complete = vitals_complete.sort_values(["stay_id", "hour"]).reset_index(drop=True)
    stay_ids_order  = vitals_complete["stay_id"].drop_duplicates().tolist()
    X = np.array([
        vitals_complete[vitals_complete["stay_id"] == sid][FEATURE_COLS].values
        for sid in stay_ids_order
    ])
    print(f"[build_X_array] X shape: {X.shape}")
    return X, stay_ids_order


# ===========================================================================
# SECTION 3 — SOFA Score
# ===========================================================================

# --- SOFA scoring functions -------------------------------------------------

def _sofa_platelets(x):
    if pd.isna(x):   return np.nan
    if x >= 150:     return 0
    if x >= 100:     return 1
    if x >= 50:      return 2
    if x >= 20:      return 3
    return 4

def _sofa_bilirubin(x):
    if pd.isna(x):   return np.nan
    if x < 1.2:      return 0
    if x < 2.0:      return 1
    if x < 6.0:      return 2
    if x < 12.0:     return 3
    return 4

def _sofa_creatinine(x):
    if pd.isna(x):   return np.nan
    if x < 1.2:      return 0
    if x < 2.0:      return 1
    if x < 3.5:      return 2
    if x < 5.0:      return 3
    return 4

def _sofa_map(x):
    if pd.isna(x):   return np.nan
    return 0 if x >= 70 else 1

def _sofa_gcs(x):
    if pd.isna(x):   return np.nan
    if x == 15:      return 0
    if x >= 13:      return 1
    if x >= 10:      return 2
    if x >= 6:       return 3
    return 4


def _extract_sofa_labs(
    cohort: pd.DataFrame,
    data_dir: Path,
    output_dir: Path,
    chunk_size: int = 100_000,
) -> Path:
    """Stream labevents and save the SOFA-relevant rows."""
    output_file = output_dir / "sofa_labs_filtered.csv"
    if output_file.exists():
        output_file.unlink()

    all_itemids = (
        SOFA_LAB_ITEMIDS["platelets"] +
        SOFA_LAB_ITEMIDS["bilirubin"] +
        SOFA_LAB_ITEMIDS["creatinine"]
    )
    zip_path    = data_dir / "chartevents_labevents.zip"
    first_chunk = True

    with zipfile.ZipFile(zip_path, "r") as z:
        with z.open("Cleaned/labevents.csv") as f:
            for i, chunk in enumerate(
                pd.read_csv(
                    f,
                    chunksize=chunk_size,
                    usecols=["subject_id", "hadm_id", "charttime", "itemid", "valuenum"],
                )
            ):
                chunk = chunk[chunk["itemid"].isin(all_itemids)]
                chunk = chunk.merge(
                    cohort[["subject_id", "hadm_id", "stay_id"]],
                    on=["subject_id", "hadm_id"],
                    how="inner",
                )
                if not chunk.empty:
                    chunk.to_csv(output_file, mode="a", header=first_chunk, index=False)
                    first_chunk = False
                print(f"  chunk {i+1} done", end="\r")

    print(f"\n[_extract_sofa_labs] Saved sofa_labs_filtered.csv")
    return output_file


def _extract_gcs(
    cohort: pd.DataFrame,
    data_dir: Path,
    output_dir: Path,
    chunk_size: int = 100_000,
) -> Path:
    """Stream chartevents and save the GCS-relevant rows."""
    output_file = output_dir / "gcs_filtered.csv"
    if output_file.exists():
        output_file.unlink()

    stay_ids    = set(cohort["stay_id"].dropna().unique())
    zip_path    = data_dir / "chartevents_labevents.zip"
    first_chunk = True

    with zipfile.ZipFile(zip_path, "r") as z:
        with z.open("Cleaned/chartevents.csv") as f:
            for i, chunk in enumerate(
                pd.read_csv(
                    f,
                    chunksize=chunk_size,
                    usecols=["subject_id", "hadm_id", "stay_id",
                             "charttime", "itemid", "valuenum"],
                )
            ):
                chunk = chunk[
                    chunk["stay_id"].isin(stay_ids) &
                    chunk["itemid"].isin(GCS_ITEMIDS)
                ]
                if not chunk.empty:
                    chunk.to_csv(output_file, mode="a", header=first_chunk, index=False)
                    first_chunk = False
                print(f"  chunk {i+1} done", end="\r")

    print(f"\n[_extract_gcs] Saved gcs_filtered.csv")
    return output_file


def build_sofa(
    cohort: pd.DataFrame,
    vitals_wide: pd.DataFrame = None,
    data_dir: Path = _DEFAULT_DATA_DIR,
    output_dir: Path = _DEFAULT_OUTPUT_DIR,
    save: bool = True,
) -> pd.DataFrame:
    """
    Build the hourly SOFA dataframe with components:
        sofa_platelets, sofa_bilirubin, sofa_creatinine,
        sofa_map, sofa_gcs, sofa_total

    Parameters
    ----------
    vitals_wide : optional pre-built vitals_wide DataFrame (used for MAP).
                  If None, it is rebuilt from vitals_filtered.csv.

    Returns
    -------
    sofa_df : pd.DataFrame  — one row per (stay_id, charttime_hour)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # ---- Lab component ----
    labs_path = output_dir / "sofa_labs_filtered.csv"
    if not labs_path.exists():
        _extract_sofa_labs(cohort, data_dir, output_dir)

    labs = pd.read_csv(labs_path)
    labs["charttime"] = pd.to_datetime(labs["charttime"])
    labs = labs.dropna(subset=["valuenum"])
    labs["lab_name"]      = labs["itemid"].map(LAB_ITEMID_TO_NAME)
    labs["charttime_hour"] = labs["charttime"].dt.floor("h")

    labs_hourly = (
        labs.groupby(["stay_id", "charttime_hour", "lab_name"])["valuenum"]
        .mean().reset_index()
    )
    labs_wide_df = labs_hourly.pivot_table(
        index=["stay_id", "charttime_hour"],
        columns="lab_name",
        values="valuenum",
    ).reset_index()
    labs_wide_df.columns.name = None

    labs_wide_df["sofa_platelets"]  = labs_wide_df["platelets"].apply(_sofa_platelets)
    labs_wide_df["sofa_bilirubin"]  = labs_wide_df["bilirubin"].apply(_sofa_bilirubin)
    labs_wide_df["sofa_creatinine"] = labs_wide_df["creatinine"].apply(_sofa_creatinine)
    labs_wide_df["sofa_lab_total"]  = (
        labs_wide_df[["sofa_platelets", "sofa_bilirubin", "sofa_creatinine"]]
        .sum(axis=1, min_count=1)
    )

    # ---- MAP component ----
    if vitals_wide is None:
        # Rebuild minimal vitals_wide for MAP
        filtered_path = output_dir / "vitals_filtered.csv"
        if not filtered_path.exists():
            extract_vitals_filtered(cohort, data_dir, output_dir)
        v = pd.read_csv(filtered_path)
        v["feature_name"]    = v["itemid"].map(ITEMID_TO_VITAL)
        v["charttime"]       = pd.to_datetime(v["charttime"])
        v["charttime_hour"]  = v["charttime"].dt.floor("h")
        v_hourly = (
            v.groupby(["stay_id", "charttime_hour", "feature_name"])["valuenum"]
            .mean().reset_index()
        )
        vitals_wide = v_hourly.pivot_table(
            index=["stay_id", "charttime_hour"],
            columns="feature_name",
            values="valuenum",
        ).reset_index()
        vitals_wide.columns.name = None

    map_df = vitals_wide[["stay_id", "charttime_hour", "abp_mean"]].copy()
    map_df["charttime_hour"] = pd.to_datetime(map_df["charttime_hour"])
    map_df["sofa_map"] = map_df["abp_mean"].apply(_sofa_map)

    # ---- GCS component ----
    gcs_path = output_dir / "gcs_filtered.csv"
    if not gcs_path.exists():
        _extract_gcs(cohort, data_dir, output_dir)

    gcs = pd.read_csv(gcs_path)
    gcs["charttime"]      = pd.to_datetime(gcs["charttime"])
    gcs = gcs.dropna(subset=["valuenum"])
    gcs["charttime_hour"] = gcs["charttime"].dt.floor("h")
    gcs["component"]      = gcs["itemid"].map(GCS_ITEMID_TO_COMPONENT)

    gcs_hourly = (
        gcs.groupby(["stay_id", "charttime_hour", "component"])["valuenum"]
        .mean().reset_index()
    )
    gcs_wide = gcs_hourly.pivot_table(
        index=["stay_id", "charttime_hour"],
        columns="component",
        values="valuenum",
    ).reset_index()
    gcs_wide.columns.name = None

    gcs_wide["gcs_total"] = (
        gcs_wide[["eye", "verbal", "motor"]].sum(axis=1, min_count=3)
    )
    gcs_wide["sofa_gcs"] = gcs_wide["gcs_total"].apply(_sofa_gcs)

    # ---- Combine ----
    sofa_df = (
        labs_wide_df
        .merge(map_df[["stay_id", "charttime_hour", "sofa_map"]],
               on=["stay_id", "charttime_hour"], how="outer")
        .merge(gcs_wide[["stay_id", "charttime_hour", "sofa_gcs"]],
               on=["stay_id", "charttime_hour"], how="outer")
    )

    sofa_components = ["sofa_platelets", "sofa_bilirubin", "sofa_creatinine",
                       "sofa_map", "sofa_gcs"]
    sofa_df["sofa_total"] = sofa_df[sofa_components].sum(axis=1, min_count=1)
    sofa_df["charttime_hour"] = pd.to_datetime(sofa_df["charttime_hour"])

    if save:
        sofa_df.to_csv(output_dir / "sofa_df.csv", index=False)
        print(f"[build_sofa] Saved sofa_df.csv — shape: {sofa_df.shape}")

    return sofa_df


def load_sofa(output_dir: Path = _DEFAULT_OUTPUT_DIR) -> pd.DataFrame:
    """Load a previously saved sofa_df.csv."""
    df = pd.read_csv(output_dir / "sofa_df.csv")
    df["charttime_hour"] = pd.to_datetime(df["charttime_hour"])
    print(f"[load_sofa] Loaded — shape: {df.shape}")
    return df


# ===========================================================================
# SECTION 4 — Suspected Infection
# ===========================================================================

def build_suspected_infection(
    cohort: pd.DataFrame,
    data_dir: Path = _DEFAULT_DATA_DIR,
    output_dir: Path = _DEFAULT_OUTPUT_DIR,
    save: bool = True,
) -> pd.DataFrame:
    """
    Identify earliest suspected infection timestamp per ICU stay using the
    Sepsis-3 antibiotic + culture pairing rule:
        • Culture within 72 h AFTER antibiotics, OR
        • Culture within 24 h BEFORE antibiotics.

    Returns
    -------
    suspected_infection : pd.DataFrame
        Columns: stay_id, suspected_infection_time
    """
    prescriptions = pd.read_csv(data_dir / "prescriptions.csv")
    micro         = pd.read_csv(data_dir / "microbiologyevents.csv")

    prescriptions["starttime"] = pd.to_datetime(prescriptions["starttime"], errors="coerce")
    micro["charttime"]         = pd.to_datetime(micro["charttime"],  errors="coerce")
    micro["chartdate"]         = pd.to_datetime(micro["chartdate"],  errors="coerce")
    micro["culture_time"]      = micro["charttime"].fillna(micro["chartdate"])

    cohort_keys = cohort[["subject_id", "hadm_id", "stay_id"]].dropna().drop_duplicates()

    presc    = prescriptions.merge(cohort_keys, on=["subject_id", "hadm_id"], how="inner")
    cultures = micro.merge(cohort_keys,         on=["subject_id", "hadm_id"], how="inner")

    presc    = presc[["subject_id", "hadm_id", "stay_id", "starttime", "drug"]].dropna(subset=["starttime"])
    cultures = cultures[["subject_id", "hadm_id", "stay_id", "culture_time", "spec_type_desc"]].dropna(subset=["culture_time"])

    # Filter to antibiotics only
    pattern = "|".join(ANTIBIOTIC_KEYWORDS)
    abx = presc[presc["drug"].astype(str).str.lower().str.contains(pattern, na=False)].copy()
    abx = abx.rename(columns={"starttime": "antibiotic_time"})

    pairs = abx.merge(cultures, on=["subject_id", "hadm_id", "stay_id"], how="inner")
    pairs["time_diff_hours"] = (
        (pairs["antibiotic_time"] - pairs["culture_time"]).dt.total_seconds() / 3600.0
    )

    # Sepsis-3 pairing window
    suspected_pairs = pairs[
        ((pairs["time_diff_hours"] >= 0)  & (pairs["time_diff_hours"] <= 72)) |
        ((pairs["time_diff_hours"] <  0)  & (pairs["time_diff_hours"] >= -24))
    ].copy()

    # Infection timestamp = whichever event came first
    suspected_pairs["suspected_infection_time"] = suspected_pairs["culture_time"]
    abx_first = suspected_pairs["time_diff_hours"] < 0
    suspected_pairs.loc[abx_first, "suspected_infection_time"] = (
        suspected_pairs.loc[abx_first, "antibiotic_time"]
    )

    suspected_infection = (
        suspected_pairs
        .groupby("stay_id", as_index=False)["suspected_infection_time"]
        .min()
    )

    if save:
        output_dir.mkdir(parents=True, exist_ok=True)
        suspected_infection.to_csv(output_dir / "suspected_infection.csv", index=False)
        print(f"[build_suspected_infection] Saved — shape: {suspected_infection.shape}")

    return suspected_infection


def load_suspected_infection(output_dir: Path = _DEFAULT_OUTPUT_DIR) -> pd.DataFrame:
    """Load a previously saved suspected_infection.csv."""
    df = pd.read_csv(output_dir / "suspected_infection.csv")
    df["suspected_infection_time"] = pd.to_datetime(df["suspected_infection_time"])
    print(f"[load_suspected_infection] Loaded — shape: {df.shape}")
    return df


# ===========================================================================
# SECTION 5 — Sepsis Labels
# ===========================================================================

def build_sepsis_labels(
    cohort: pd.DataFrame,
    sofa_df: pd.DataFrame,
    suspected_infection: pd.DataFrame,
    stay_ids_order: list,
    output_dir: Path = _DEFAULT_OUTPUT_DIR,
    save: bool = True,
) -> tuple[pd.DataFrame, dict]:
    """
    Apply the Sepsis-3 definition to build multi-horizon labels.

    Sepsis onset = first hour where SOFA >= 2 AND within [-48h, +24h]
    of the suspected infection time.

    Prediction horizons (measured from ICU admission):
        y_6h  — onset in [24 h, 30 h)   requires LOS >= 30 h
        y_12h — onset in [24 h, 36 h)   requires LOS >= 36 h
        y_24h — onset in [24 h, 48 h)   requires LOS >= 48 h

    Returns
    -------
    labels_ordered : pd.DataFrame  aligned to stay_ids_order
    arrays         : dict with keys y_6h, y_12h, y_24h,
                                    eligible_6h, eligible_12h, eligible_24h
                     each a numpy array
    """
    sofa_pos = sofa_df[sofa_df["sofa_total"] >= 2].copy()
    sofa_pos["charttime_hour"] = pd.to_datetime(sofa_pos["charttime_hour"])
    suspected_infection["suspected_infection_time"] = pd.to_datetime(
        suspected_infection["suspected_infection_time"]
    )

    sepsis_candidates = sofa_pos.merge(suspected_infection, on="stay_id", how="inner")
    sepsis_candidates["diff_from_infection_hours"] = (
        (sepsis_candidates["charttime_hour"] - sepsis_candidates["suspected_infection_time"])
        .dt.total_seconds() / 3600.0
    )
    sepsis_candidates = sepsis_candidates[
        (sepsis_candidates["diff_from_infection_hours"] >= -48) &
        (sepsis_candidates["diff_from_infection_hours"] <=  24)
    ].copy()

    sepsis_onset = (
        sepsis_candidates
        .groupby("stay_id", as_index=False)["charttime_hour"]
        .min()
        .rename(columns={"charttime_hour": "sepsis_onset_time"})
    )

    cohort["intime"] = pd.to_datetime(cohort["intime"])
    label_df = (
        cohort[["stay_id", "intime", "icu_los_hours"]]
        .drop_duplicates()
        .merge(sepsis_onset, on="stay_id", how="left")
    )
    label_df["onset_hour"] = (
        (label_df["sepsis_onset_time"] - label_df["intime"]).dt.total_seconds() / 3600.0
    )

    label_df["eligible_6h"]  = label_df["icu_los_hours"] >= 30
    label_df["eligible_12h"] = label_df["icu_los_hours"] >= 36
    label_df["eligible_24h"] = label_df["icu_los_hours"] >= 48

    label_df["y_6h"]  = ((label_df["onset_hour"] >= 24) & (label_df["onset_hour"] < 30)).astype(int)
    label_df["y_12h"] = ((label_df["onset_hour"] >= 24) & (label_df["onset_hour"] < 36)).astype(int)
    label_df["y_24h"] = ((label_df["onset_hour"] >= 24) & (label_df["onset_hour"] < 48)).astype(int)

    label_cols = ["stay_id", "eligible_6h", "eligible_12h", "eligible_24h",
                  "y_6h", "y_12h", "y_24h"]
    labels_ordered = (
        pd.DataFrame({"stay_id": stay_ids_order})
        .merge(label_df[label_cols], on="stay_id", how="left")
    )
    labels_ordered[label_cols[1:]] = labels_ordered[label_cols[1:]].fillna(0)

    arrays = {
        "y_6h":         labels_ordered["y_6h"].astype(int).values,
        "y_12h":        labels_ordered["y_12h"].astype(int).values,
        "y_24h":        labels_ordered["y_24h"].astype(int).values,
        "eligible_6h":  labels_ordered["eligible_6h"].astype(bool).values,
        "eligible_12h": labels_ordered["eligible_12h"].astype(bool).values,
        "eligible_24h": labels_ordered["eligible_24h"].astype(bool).values,
    }

    for k, v in arrays.items():
        if k.startswith("y_"):
            print(f"  {k}: shape={v.shape}  positive_rate={v.mean():.4f}")

    if save:
        output_dir.mkdir(parents=True, exist_ok=True)
        labels_ordered.to_csv(output_dir / "sepsis_labels_multihorizon.csv", index=False)
        print(f"[build_sepsis_labels] Saved sepsis_labels_multihorizon.csv")

    return labels_ordered, arrays


def load_sepsis_labels(
    stay_ids_order: list,
    output_dir: Path = _DEFAULT_OUTPUT_DIR,
) -> tuple[pd.DataFrame, dict]:
    """Load previously saved labels and return (DataFrame, arrays dict)."""
    labels_ordered = pd.read_csv(output_dir / "sepsis_labels_multihorizon.csv")
    arrays = {
        "y_6h":         labels_ordered["y_6h"].astype(int).values,
        "y_12h":        labels_ordered["y_12h"].astype(int).values,
        "y_24h":        labels_ordered["y_24h"].astype(int).values,
        "eligible_6h":  labels_ordered["eligible_6h"].astype(bool).values,
        "eligible_12h": labels_ordered["eligible_12h"].astype(bool).values,
        "eligible_24h": labels_ordered["eligible_24h"].astype(bool).values,
    }
    print(f"[load_sepsis_labels] Loaded — shape: {labels_ordered.shape}")
    return labels_ordered, arrays


# ===========================================================================
# SECTION 6 — Full Pipeline (convenience wrapper)
# ===========================================================================

def run_full_pipeline(
    data_dir: Path = _DEFAULT_DATA_DIR,
    output_dir: Path = _DEFAULT_OUTPUT_DIR,
    force_rebuild: bool = False,
) -> dict:
    """
    Run the complete preprocessing pipeline end-to-end, or load
    cached outputs when they already exist (unless force_rebuild=True).

    Returns a dict with keys:
        cohort, vitals_complete, sofa_df, suspected_infection,
        labels_ordered, X, stay_ids_order, label_arrays
    """
    print("=" * 60)
    print("  ICU Sepsis — Preprocessing Pipeline")
    print("=" * 60)

    # 1. Cohort
    cohort_path = output_dir / "icu_cohort.csv"
    if not force_rebuild and cohort_path.exists():
        cohort = load_cohort(output_dir)
    else:
        cohort = build_cohort(data_dir, output_dir)

    # 2. Vitals
    vitals_path = output_dir / "vitals_complete.csv"
    if not force_rebuild and vitals_path.exists():
        vitals_complete = load_vitals_complete(output_dir)
    else:
        vitals_complete = build_vitals_complete(cohort, data_dir, output_dir)

    # 3. LSTM array
    X, stay_ids_order = build_X_array(vitals_complete)

    # 4. SOFA
    sofa_path = output_dir / "sofa_df.csv"
    if not force_rebuild and sofa_path.exists():
        sofa_df = load_sofa(output_dir)
    else:
        sofa_df = build_sofa(cohort, data_dir=data_dir, output_dir=output_dir)

    # 5. Suspected infection
    inf_path = output_dir / "suspected_infection.csv"
    if not force_rebuild and inf_path.exists():
        suspected_infection = load_suspected_infection(output_dir)
    else:
        suspected_infection = build_suspected_infection(cohort, data_dir, output_dir)

    # 6. Labels
    label_path = output_dir / "sepsis_labels_multihorizon.csv"
    if not force_rebuild and label_path.exists():
        labels_ordered, label_arrays = load_sepsis_labels(stay_ids_order, output_dir)
    else:
        labels_ordered, label_arrays = build_sepsis_labels(
            cohort, sofa_df, suspected_infection, stay_ids_order, output_dir
        )

    print("\n" + "=" * 60)
    print("  Pipeline complete.")
    print(f"  Cohort stays  : {cohort['stay_id'].nunique():,}")
    print(f"  X shape       : {X.shape}")
    print(f"  SOFA rows     : {sofa_df.shape[0]:,}")
    print("=" * 60)

    return {
        "cohort":               cohort,
        "vitals_complete":      vitals_complete,
        "sofa_df":              sofa_df,
        "suspected_infection":  suspected_infection,
        "labels_ordered":       labels_ordered,
        "X":                    X,
        "stay_ids_order":       stay_ids_order,
        "label_arrays":         label_arrays,
    }
