"""
Preprocessing functions: cleaning, basic joins, time alignment stubs.
Fill in with MIMIC-specific logic later.
"""

from pathlib import Path
import zipfile
import pandas as pd
import numpy as np


# -----------------------------
# Constants
# -----------------------------
HEART_RATE_ID = 220045
RESP_RATE_ID = 220210
TEMP_C_ID = 223762
SPO2_ID = 220277
ABP_SYS_ID = 220050
ABP_DIA_ID = 220051
ABP_MEAN_ID = 220052

VITAL_ITEMIDS = [
    HEART_RATE_ID,
    RESP_RATE_ID,
    TEMP_C_ID,
    SPO2_ID,
    ABP_SYS_ID,
    ABP_DIA_ID,
    ABP_MEAN_ID,
]

ITEMID_TO_LABEL = {
    220045: "heart_rate",
    220210: "resp_rate",
    223762: "temp_c",
    220277: "spo2",
    220050: "abp_sys",
    220051: "abp_dia",
    220052: "abp_mean",
}

SOFA_LAB_ITEMIDS = {
    "platelets": [51265],
    "bilirubin": [50885, 53089],
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
GCS_MAP = {
    220739: "eye",
    223900: "verbal",
    223901: "motor",
}

FEATURE_COLS = [
    "abp_dia",
    "abp_mean",
    "abp_sys",
    "heart_rate",
    "resp_rate",
    "spo2",
    "temp_c",
]


# -----------------------------
# Config
# -----------------------------
class PreprocessingConfig:
    def __init__(
        self,
        data_dir: str,
        output_dir: str,
        zip_filename: str = "chartevents_labevents.zip",
        zip_chartevents_member: str = "Cleaned/chartevents.csv",
        zip_labevents_member: str = "Cleaned/labevents.csv",
        min_icu_hours: int = 4,
        min_age: int = 18,
        min_hours_for_sequence: int = 12,
        sequence_hours: int = 24,
    ):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.zip_path = self.data_dir / zip_filename
        self.zip_chartevents_member = zip_chartevents_member
        self.zip_labevents_member = zip_labevents_member

        self.min_icu_hours = min_icu_hours
        self.min_age = min_age
        self.min_hours_for_sequence = min_hours_for_sequence
        self.sequence_hours = sequence_hours


# -----------------------------
# Utilities
# -----------------------------
def sofa_platelets(x):
    if pd.isna(x):
        return np.nan
    if x >= 150:
        return 0
    if x >= 100:
        return 1
    if x >= 50:
        return 2
    if x >= 20:
        return 3
    return 4


def sofa_bilirubin(x):
    if pd.isna(x):
        return np.nan
    if x < 1.2:
        return 0
    if x < 2.0:
        return 1
    if x < 6.0:
        return 2
    if x < 12.0:
        return 3
    return 4


def sofa_creatinine(x):
    if pd.isna(x):
        return np.nan
    if x < 1.2:
        return 0
    if x < 2.0:
        return 1
    if x < 3.5:
        return 2
    if x < 5.0:
        return 3
    return 4


def sofa_map_score(x):
    if pd.isna(x):
        return np.nan
    return 0 if x >= 70 else 1


def sofa_gcs_score(x):
    if pd.isna(x):
        return np.nan
    if x == 15:
        return 0
    if x >= 13:
        return 1
    if x >= 10:
        return 2
    if x >= 6:
        return 3
    return 4


def _save_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False)


# -----------------------------
# Base tables and cohort
# -----------------------------
def load_base_tables(config: PreprocessingConfig):
    patients = pd.read_csv(config.data_dir / "patients.csv")
    admissions = pd.read_csv(config.data_dir / "admissions.csv")
    icustays = pd.read_csv(config.data_dir / "icustays.csv")
    return patients, admissions, icustays


def build_cohort(
    patients: pd.DataFrame,
    admissions: pd.DataFrame,
    icustays: pd.DataFrame,
    config: PreprocessingConfig,
) -> pd.DataFrame:
    cohort = icustays.merge(
        admissions,
        on=["subject_id", "hadm_id"],
        how="left",
    ).merge(
        patients,
        on="subject_id",
        how="left",
    )

    for col in ["intime", "outtime", "admittime", "dischtime"]:
        if col in cohort.columns:
            cohort[col] = pd.to_datetime(cohort[col], errors="coerce")

    cohort["icu_los_hours"] = (
        (cohort["outtime"] - cohort["intime"]).dt.total_seconds() / 3600
    )

    cohort = cohort[cohort["icu_los_hours"] >= config.min_icu_hours].copy()
    cohort = cohort[cohort["anchor_age"] >= config.min_age].copy()

    return cohort


# -----------------------------
# Vitals
# -----------------------------
def extract_filtered_vitals(
    cohort: pd.DataFrame,
    config: PreprocessingConfig,
    chunk_size: int = 100000,
) -> pd.DataFrame:
    output_file = config.output_dir / "vitals_filtered.csv"
    if output_file.exists():
        output_file.unlink()

    stay_ids = set(cohort["stay_id"].dropna().unique())
    first_chunk = True

    with zipfile.ZipFile(config.zip_path, "r") as z:
        with z.open(config.zip_chartevents_member) as f:
            for chunk in pd.read_csv(
                f,
                chunksize=chunk_size,
                usecols=[
                    "subject_id",
                    "hadm_id",
                    "stay_id",
                    "charttime",
                    "itemid",
                    "valuenum",
                    "valueuom",
                ],
            ):
                chunk = chunk[
                    (chunk["stay_id"].isin(stay_ids))
                    & (chunk["itemid"].isin(VITAL_ITEMIDS))
                ]

                if not chunk.empty:
                    chunk.to_csv(
                        output_file,
                        mode="a",
                        header=first_chunk,
                        index=False,
                    )
                    first_chunk = False

    if output_file.exists():
        return pd.read_csv(output_file)

    return pd.DataFrame(
        columns=[
            "subject_id",
            "hadm_id",
            "stay_id",
            "charttime",
            "itemid",
            "valuenum",
            "valueuom",
        ]
    )


def build_vitals_hourly_wide(vitals: pd.DataFrame) -> pd.DataFrame:
    vitals = vitals.copy()
    vitals["feature_name"] = vitals["itemid"].map(ITEMID_TO_LABEL)
    vitals = vitals.dropna(subset=["feature_name", "charttime", "valuenum"])

    vitals["charttime"] = pd.to_datetime(vitals["charttime"], errors="coerce")
    vitals = vitals.dropna(subset=["charttime"])
    vitals["charttime_hour"] = vitals["charttime"].dt.floor("h")

    vitals_hourly = (
        vitals.groupby(["stay_id", "charttime_hour", "feature_name"])["valuenum"]
        .mean()
        .reset_index()
    )

    vitals_wide = vitals_hourly.pivot_table(
        index=["stay_id", "charttime_hour"],
        columns="feature_name",
        values="valuenum",
    ).reset_index()

    vitals_wide.columns.name = None
    return vitals_wide


def build_vitals_24h(
    vitals_wide: pd.DataFrame,
    cohort: pd.DataFrame,
    config: PreprocessingConfig,
) -> pd.DataFrame:
    cohort_small = cohort[["stay_id", "intime"]].copy()

    vitals_wide = vitals_wide.merge(cohort_small, on="stay_id", how="left")
    vitals_wide["charttime_hour"] = pd.to_datetime(
        vitals_wide["charttime_hour"], errors="coerce"
    )
    vitals_wide["intime"] = pd.to_datetime(vitals_wide["intime"], errors="coerce")

    vitals_wide["hours_since_admit"] = (
        vitals_wide["charttime_hour"] - vitals_wide["intime"]
    ).dt.total_seconds() / 3600

    vitals_24h = vitals_wide[
        (vitals_wide["hours_since_admit"] >= 0)
        & (vitals_wide["hours_since_admit"] < config.sequence_hours)
    ].copy()

    vitals_24h["hour"] = vitals_24h["hours_since_admit"].astype(int)

    keep_cols = [
        "stay_id",
        "hour",
        "abp_dia",
        "abp_mean",
        "abp_sys",
        "heart_rate",
        "resp_rate",
        "spo2",
        "temp_c",
    ]

    for col in keep_cols:
        if col not in vitals_24h.columns:
            vitals_24h[col] = np.nan

    vitals_24h = vitals_24h[keep_cols].copy()

    vitals_24h = (
        vitals_24h.groupby(["stay_id", "hour"], as_index=False)
        .mean(numeric_only=True)
    )

    return vitals_24h


def build_vitals_complete(
    vitals_24h: pd.DataFrame,
    config: PreprocessingConfig,
) -> pd.DataFrame:
    valid_stays = vitals_24h.groupby("stay_id")["hour"].nunique()
    valid_stays = valid_stays[valid_stays >= config.min_hours_for_sequence].index
    vitals_24h = vitals_24h[vitals_24h["stay_id"].isin(valid_stays)].copy()

    vitals_complete = []
    for stay_id, group in vitals_24h.groupby("stay_id"):
        group = group.set_index("hour").reindex(range(config.sequence_hours))
        group["stay_id"] = stay_id
        vitals_complete.append(group.reset_index())

    if not vitals_complete:
        return pd.DataFrame(columns=["hour", "stay_id"] + FEATURE_COLS)

    vitals_complete = pd.concat(vitals_complete, ignore_index=True)
    vitals_complete = vitals_complete.sort_values(["stay_id", "hour"])

    vitals_complete = (
        vitals_complete.groupby("stay_id", group_keys=False)
        .apply(lambda x: x.ffill().bfill(), include_groups=False)
        .reset_index(drop=True)
    )

    col_order = ["stay_id", "hour"] + FEATURE_COLS
    for col in col_order:
        if col not in vitals_complete.columns:
            vitals_complete[col] = np.nan

    vitals_complete = vitals_complete[col_order].copy()
    return vitals_complete


def build_lstm_array(vitals_complete: pd.DataFrame):
    vitals_complete = vitals_complete.sort_values(["stay_id", "hour"]).reset_index(drop=True)
    stay_ids_order = vitals_complete["stay_id"].drop_duplicates().tolist()

    X = np.array([
        vitals_complete.loc[vitals_complete["stay_id"] == stay_id, FEATURE_COLS].values
        for stay_id in stay_ids_order
    ])

    return X, stay_ids_order


# -----------------------------
# SOFA labs
# -----------------------------
def extract_sofa_labs(
    cohort: pd.DataFrame,
    config: PreprocessingConfig,
    chunk_size: int = 100000,
) -> pd.DataFrame:
    output_file = config.output_dir / "sofa_labs_filtered.csv"
    if output_file.exists():
        output_file.unlink()

    all_itemids = (
        SOFA_LAB_ITEMIDS["platelets"]
        + SOFA_LAB_ITEMIDS["bilirubin"]
        + SOFA_LAB_ITEMIDS["creatinine"]
    )

    first_chunk = True
    cohort_keys = cohort[["subject_id", "hadm_id", "stay_id"]].drop_duplicates()

    with zipfile.ZipFile(config.zip_path, "r") as z:
        with z.open(config.zip_labevents_member) as f:
            for chunk in pd.read_csv(
                f,
                chunksize=chunk_size,
                usecols=["subject_id", "hadm_id", "charttime", "itemid", "valuenum"],
            ):
                chunk = chunk[chunk["itemid"].isin(all_itemids)]
                chunk = chunk.merge(
                    cohort_keys,
                    on=["subject_id", "hadm_id"],
                    how="inner",
                )

                if not chunk.empty:
                    chunk.to_csv(
                        output_file,
                        mode="a",
                        header=first_chunk,
                        index=False,
                    )
                    first_chunk = False

    if output_file.exists():
        return pd.read_csv(output_file)

    return pd.DataFrame(columns=["subject_id", "hadm_id", "charttime", "itemid", "valuenum", "stay_id"])


def build_sofa_labs_hourly_wide(labs: pd.DataFrame) -> pd.DataFrame:
    labs = labs.copy()
    labs["charttime"] = pd.to_datetime(labs["charttime"], errors="coerce")
    labs = labs.dropna(subset=["charttime", "valuenum"])
    labs["lab_name"] = labs["itemid"].map(LAB_ITEMID_TO_NAME)
    labs = labs.dropna(subset=["lab_name"])
    labs["charttime_hour"] = labs["charttime"].dt.floor("h")

    labs_hourly = (
        labs.groupby(["stay_id", "charttime_hour", "lab_name"])["valuenum"]
        .mean()
        .reset_index()
    )

    labs_wide = labs_hourly.pivot_table(
        index=["stay_id", "charttime_hour"],
        columns="lab_name",
        values="valuenum",
    ).reset_index()

    labs_wide.columns.name = None
    return labs_wide


def add_sofa_lab_scores(labs_wide: pd.DataFrame) -> pd.DataFrame:
    labs_wide = labs_wide.copy()

    for col in ["platelets", "bilirubin", "creatinine"]:
        if col not in labs_wide.columns:
            labs_wide[col] = np.nan

    labs_wide["sofa_platelets"] = labs_wide["platelets"].apply(sofa_platelets)
    labs_wide["sofa_bilirubin"] = labs_wide["bilirubin"].apply(sofa_bilirubin)
    labs_wide["sofa_creatinine"] = labs_wide["creatinine"].apply(sofa_creatinine)

    labs_wide["sofa_lab_total"] = (
        labs_wide["sofa_platelets"]
        + labs_wide["sofa_bilirubin"]
        + labs_wide["sofa_creatinine"]
    )

    return labs_wide


# -----------------------------
# GCS
# -----------------------------
def extract_gcs(
    cohort: pd.DataFrame,
    config: PreprocessingConfig,
    chunk_size: int = 100000,
) -> pd.DataFrame:
    output_file = config.output_dir / "gcs_filtered.csv"
    if output_file.exists():
        output_file.unlink()

    stay_ids = set(cohort["stay_id"].dropna().unique())
    first_chunk = True

    with zipfile.ZipFile(config.zip_path, "r") as z:
        with z.open(config.zip_chartevents_member) as f:
            for chunk in pd.read_csv(
                f,
                chunksize=chunk_size,
                usecols=[
                    "subject_id",
                    "hadm_id",
                    "stay_id",
                    "charttime",
                    "itemid",
                    "valuenum",
                ],
            ):
                chunk = chunk[
                    (chunk["stay_id"].isin(stay_ids))
                    & (chunk["itemid"].isin(GCS_ITEMIDS))
                ]

                if not chunk.empty:
                    chunk.to_csv(
                        output_file,
                        mode="a",
                        header=first_chunk,
                        index=False,
                    )
                    first_chunk = False

    if output_file.exists():
        return pd.read_csv(output_file)

    return pd.DataFrame(columns=["subject_id", "hadm_id", "stay_id", "charttime", "itemid", "valuenum"])


def build_gcs_hourly(gcs: pd.DataFrame) -> pd.DataFrame:
    gcs = gcs.copy()
    gcs["charttime"] = pd.to_datetime(gcs["charttime"], errors="coerce")
    gcs = gcs.dropna(subset=["charttime", "valuenum"])
    gcs["component"] = gcs["itemid"].map(GCS_MAP)
    gcs = gcs.dropna(subset=["component"])
    gcs["charttime_hour"] = gcs["charttime"].dt.floor("h")

    gcs_hourly = (
        gcs.groupby(["stay_id", "charttime_hour", "component"])["valuenum"]
        .mean()
        .reset_index()
    )

    gcs_wide = gcs_hourly.pivot_table(
        index=["stay_id", "charttime_hour"],
        columns="component",
        values="valuenum",
    ).reset_index()

    gcs_wide.columns.name = None

    for col in ["eye", "verbal", "motor"]:
        if col not in gcs_wide.columns:
            gcs_wide[col] = np.nan

    gcs_wide["gcs_total"] = gcs_wide[["eye", "verbal", "motor"]].sum(axis=1, min_count=3)
    gcs_wide["sofa_gcs"] = gcs_wide["gcs_total"].apply(sofa_gcs_score)

    return gcs_wide


# -----------------------------
# SOFA merge
# -----------------------------
def build_sofa_df(
    labs_wide: pd.DataFrame,
    vitals_wide: pd.DataFrame,
    gcs_wide: pd.DataFrame,
) -> pd.DataFrame:
    labs_wide = add_sofa_lab_scores(labs_wide)

    map_df = vitals_wide[["stay_id", "charttime_hour", "abp_mean"]].copy()
    map_df["sofa_map"] = map_df["abp_mean"].apply(sofa_map_score)

    sofa_df = labs_wide.merge(
        map_df[["stay_id", "charttime_hour", "sofa_map"]],
        on=["stay_id", "charttime_hour"],
        how="outer",
    )

    if gcs_wide is not None and not gcs_wide.empty:
        sofa_df = sofa_df.merge(
            gcs_wide[["stay_id", "charttime_hour", "sofa_gcs"]],
            on=["stay_id", "charttime_hour"],
            how="outer",
        )

    for col in [
        "sofa_platelets",
        "sofa_bilirubin",
        "sofa_creatinine",
        "sofa_map",
        "sofa_gcs",
    ]:
        if col not in sofa_df.columns:
            sofa_df[col] = np.nan

    sofa_components = [
        "sofa_platelets",
        "sofa_bilirubin",
        "sofa_creatinine",
        "sofa_map",
        "sofa_gcs",
    ]

    sofa_df["sofa_total"] = sofa_df[sofa_components].sum(axis=1, min_count=1)
    return sofa_df


# -----------------------------
# Suspected infection
# -----------------------------
def build_suspected_infection(
    cohort: pd.DataFrame,
    config: PreprocessingConfig,
) -> pd.DataFrame:
    prescriptions = pd.read_csv(config.data_dir / "prescriptions.csv")
    micro = pd.read_csv(config.data_dir / "microbiologyevents.csv")

    prescriptions["starttime"] = pd.to_datetime(prescriptions["starttime"], errors="coerce")
    micro["charttime"] = pd.to_datetime(micro["charttime"], errors="coerce")
    micro["chartdate"] = pd.to_datetime(micro["chartdate"], errors="coerce")

    micro["culture_time"] = micro["charttime"]
    mask_missing = micro["culture_time"].isna()
    micro.loc[mask_missing, "culture_time"] = micro.loc[mask_missing, "chartdate"]

    cohort_keys = cohort[["subject_id", "hadm_id", "stay_id"]].dropna().drop_duplicates()

    presc = prescriptions.merge(
        cohort_keys,
        on=["subject_id", "hadm_id"],
        how="inner",
    )
    cultures = micro.merge(
        cohort_keys,
        on=["subject_id", "hadm_id"],
        how="inner",
    )

    presc = presc[["subject_id", "hadm_id", "stay_id", "starttime", "drug"]].dropna(subset=["starttime"])
    cultures = cultures[["subject_id", "hadm_id", "stay_id", "culture_time", "spec_type_desc"]].dropna(subset=["culture_time"])

    antibiotic_keywords = [
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
    pattern = "|".join(antibiotic_keywords)

    abx = presc[presc["drug"].astype(str).str.lower().str.contains(pattern, na=False)].copy()
    abx = abx.rename(columns={"starttime": "antibiotic_time"})

    pairs = abx.merge(
        cultures,
        on=["subject_id", "hadm_id", "stay_id"],
        how="inner",
    )

    pairs["time_diff_hours"] = (
        pairs["antibiotic_time"] - pairs["culture_time"]
    ).dt.total_seconds() / 3600.0

    suspected_pairs = pairs[
        (
            (pairs["time_diff_hours"] >= 0)
            & (pairs["time_diff_hours"] <= 72)
        )
        |
        (
            (pairs["time_diff_hours"] < 0)
            & (pairs["time_diff_hours"] >= -24)
        )
    ].copy()

    suspected_pairs["suspected_infection_time"] = suspected_pairs["culture_time"]
    abx_first_mask = suspected_pairs["time_diff_hours"] < 0
    suspected_pairs.loc[abx_first_mask, "suspected_infection_time"] = suspected_pairs.loc[
        abx_first_mask, "antibiotic_time"
    ]

    suspected_infection = (
        suspected_pairs.groupby("stay_id", as_index=False)["suspected_infection_time"]
        .min()
    )

    return suspected_infection


# -----------------------------
# Sepsis labels
# -----------------------------
def build_sepsis_labels(
    cohort: pd.DataFrame,
    sofa_df: pd.DataFrame,
    suspected_infection: pd.DataFrame,
    stay_ids_order: list,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    suspected_infection = suspected_infection.copy()
    suspected_infection["suspected_infection_time"] = pd.to_datetime(
        suspected_infection["suspected_infection_time"], errors="coerce"
    )

    sofa_df = sofa_df.copy()
    sofa_df["charttime_hour"] = pd.to_datetime(sofa_df["charttime_hour"], errors="coerce")

    cohort = cohort.copy()
    cohort["intime"] = pd.to_datetime(cohort["intime"], errors="coerce")

    sofa_pos = sofa_df[sofa_df["sofa_total"] >= 2].copy()

    sepsis_candidates = sofa_pos.merge(
        suspected_infection,
        on="stay_id",
        how="inner",
    )

    sepsis_candidates["diff_from_infection_hours"] = (
        sepsis_candidates["charttime_hour"] - sepsis_candidates["suspected_infection_time"]
    ).dt.total_seconds() / 3600.0

    sepsis_candidates = sepsis_candidates[
        (sepsis_candidates["diff_from_infection_hours"] >= -48)
        & (sepsis_candidates["diff_from_infection_hours"] <= 24)
    ].copy()

    sepsis_onset = (
        sepsis_candidates.groupby("stay_id", as_index=False)["charttime_hour"]
        .min()
        .rename(columns={"charttime_hour": "sepsis_onset_time"})
    )

    label_df = cohort[["stay_id", "intime", "icu_los_hours"]].drop_duplicates().merge(
        sepsis_onset,
        on="stay_id",
        how="left",
    )

    label_df["onset_hour"] = (
        label_df["sepsis_onset_time"] - label_df["intime"]
    ).dt.total_seconds() / 3600.0

    label_df["eligible_6h"] = label_df["icu_los_hours"] >= 30
    label_df["eligible_12h"] = label_df["icu_los_hours"] >= 36
    label_df["eligible_24h"] = label_df["icu_los_hours"] >= 48

    label_df["y_6h"] = (
        (label_df["onset_hour"] >= 24) & (label_df["onset_hour"] < 30)
    ).astype(int)
    label_df["y_12h"] = (
        (label_df["onset_hour"] >= 24) & (label_df["onset_hour"] < 36)
    ).astype(int)
    label_df["y_24h"] = (
        (label_df["onset_hour"] >= 24) & (label_df["onset_hour"] < 48)
    ).astype(int)

    labels_ordered = pd.DataFrame({"stay_id": stay_ids_order}).merge(
        label_df[
            [
                "stay_id",
                "eligible_6h",
                "eligible_12h",
                "eligible_24h",
                "y_6h",
                "y_12h",
                "y_24h",
            ]
        ],
        on="stay_id",
        how="left",
    )

    fill_cols = [
        "eligible_6h",
        "eligible_12h",
        "eligible_24h",
        "y_6h",
        "y_12h",
        "y_24h",
    ]
    labels_ordered[fill_cols] = labels_ordered[fill_cols].fillna(0)

    return sepsis_onset, labels_ordered


# -----------------------------
# Main pipeline
# -----------------------------
def run_preprocessing(
    data_dir: str,
    output_dir: str,
):
    config = PreprocessingConfig(data_dir=data_dir, output_dir=output_dir)

    # Base tables + cohort
    patients, admissions, icustays = load_base_tables(config)
    cohort = build_cohort(patients, admissions, icustays, config)
    _save_csv(cohort, config.output_dir / "icu_cohort.csv")

    # Vitals
    vitals = extract_filtered_vitals(cohort, config)
    _save_csv(vitals, config.output_dir / "vitals_filtered.csv")

    vitals_wide = build_vitals_hourly_wide(vitals)
    _save_csv(vitals_wide, config.output_dir / "vitals_hourly_wide.csv")

    vitals_24h = build_vitals_24h(vitals_wide, cohort, config)
    _save_csv(vitals_24h, config.output_dir / "vitals_24h.csv")

    vitals_complete = build_vitals_complete(vitals_24h, config)
    _save_csv(vitals_complete, config.output_dir / "vitals_complete.csv")

    X, stay_ids_order = build_lstm_array(vitals_complete)

    # SOFA labs
    labs = extract_sofa_labs(cohort, config)
    _save_csv(labs, config.output_dir / "sofa_labs_filtered.csv")

    labs_wide = build_sofa_labs_hourly_wide(labs)
    _save_csv(labs_wide, config.output_dir / "sofa_labs_hourly_wide.csv")

    # GCS
    gcs = extract_gcs(cohort, config)
    _save_csv(gcs, config.output_dir / "gcs_filtered.csv")

    gcs_wide = build_gcs_hourly(gcs)

    # SOFA combined
    sofa_df = build_sofa_df(labs_wide, vitals_wide, gcs_wide)
    _save_csv(sofa_df, config.output_dir / "sofa_total_hourly.csv")

    # Infection + labels
    suspected_infection = build_suspected_infection(cohort, config)
    _save_csv(suspected_infection, config.output_dir / "suspected_infection.csv")

    sepsis_onset, labels_ordered = build_sepsis_labels(
        cohort=cohort,
        sofa_df=sofa_df,
        suspected_infection=suspected_infection,
        stay_ids_order=stay_ids_order,
    )

    _save_csv(sepsis_onset, config.output_dir / "sepsis_onset.csv")
    _save_csv(labels_ordered, config.output_dir / "sepsis_labels_multihorizon.csv")

        return {
        "cohort": cohort,
        "vitals": vitals,
        "vitals_wide": vitals_wide,
        "vitals_24h": vitals_24h,
        "vitals_complete": vitals_complete,
        "X": X,
        "stay_ids_order": stay_ids_order,
        "labs_wide": labs_wide,
        "gcs_wide": gcs_wide,
        "sofa_df": sofa_df,
        "suspected_infection": suspected_infection,
        "sepsis_onset": sepsis_onset,
        "labels_ordered": labels_ordered,
    }


def load_saved_preprocessing_outputs(output_dir: str):
    output_dir = Path(output_dir)

    results = {}

    file_map = {
        "cohort": "icu_cohort.csv",
        "vitals_filtered": "vitals_filtered.csv",
        "vitals_wide": "vitals_hourly_wide.csv",
        "vitals_24h": "vitals_24h.csv",
        "vitals_complete": "vitals_complete.csv",
        "labs_filtered": "sofa_labs_filtered.csv",
        "labs_wide": "sofa_labs_hourly_wide.csv",
        "gcs_filtered": "gcs_filtered.csv",
        "suspected_infection": "suspected_infection.csv",
        "labels_ordered": "sepsis_labels_multihorizon.csv",
    }

    for key, filename in file_map.items():
        file_path = output_dir / filename
        if file_path.exists():
            results[key] = pd.read_csv(file_path)
        else:
            results[key] = None

    return results




