"""
Preprocessing functions: cleaning, basic joins, time alignment stubs.
Fill in with MIMIC-specific logic later.
"""

from __future__ import annotations
import pandas as pd


from pathlib import Path
import pandas as pd


def load_cohort(data_dir: str):
    data_dir = Path(data_dir)

    patients = pd.read_csv(data_dir / "patients.csv")
    admissions = pd.read_csv(data_dir / "admissions.csv")
    icustays = pd.read_csv(data_dir / "icustays.csv")

    cohort = icustays.merge(
        admissions,
        on=["subject_id", "hadm_id"],
        how="left"
    ).merge(
        patients,
        on="subject_id",
        how="left"
    )

    cohort["intime"] = pd.to_datetime(cohort["intime"])
    cohort["outtime"] = pd.to_datetime(cohort["outtime"])

    cohort["icu_los_hours"] = (
        (cohort["outtime"] - cohort["intime"]).dt.total_seconds() / 3600
    )

    cohort = cohort[cohort["icu_los_hours"] >= 4]
    cohort = cohort[cohort["anchor_age"] >= 18]

    return cohort


def load_preprocessed_vitals(processed_dir: str):
    processed_dir = Path(processed_dir)
    vitals_24h = pd.read_csv(processed_dir / "vitals_24h.csv")
    return vitals_24h


def load_labels(processed_dir: str):
    processed_dir = Path(processed_dir)
    labels = pd.read_csv(processed_dir / "sepsis_labels_multihorizon.csv")
    return labels
