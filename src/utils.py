"""
Utility functions shared across the project.
"""

from __future__ import annotations
from pathlib import Path
import pandas as pd


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_df(df: pd.DataFrame, path: str | Path, index: bool = False) -> None:
    path = Path(path)
    ensure_dir(path.parent)
    if path.suffix.lower() == ".parquet":
        df.to_parquet(path, index=index)
    elif path.suffix.lower() in [".csv", ".tsv"]:
        sep = "\t" if path.suffix.lower() == ".tsv" else ","
        df.to_csv(path, index=index, sep=sep)
    else:
        raise ValueError(f"Unsupported file type: {path.suffix}")
