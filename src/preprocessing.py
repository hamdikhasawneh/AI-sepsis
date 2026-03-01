"""
Preprocessing functions: cleaning, basic joins, time alignment stubs.
Fill in with MIMIC-specific logic later.
"""

from __future__ import annotations
import pandas as pd


def basic_clean(df: pd.DataFrame) -> pd.DataFrame:
    """Basic cleaning: strip column names, drop duplicate rows."""
    out = df.copy()
    out.columns = [c.strip().lower() for c in out.columns]
    out = out.drop_duplicates()
    return out
