"""
Feature engineering functions (windowed aggregates, missingness, trends).
"""

from __future__ import annotations
import pandas as pd


def make_missingness_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Example placeholder: returns a dataframe of missingness indicators.
    Replace with real feature engineering later.
    """
    miss = df.isna().astype(int)
    miss.columns = [f"{c}_isna" for c in miss.columns]
    return miss
