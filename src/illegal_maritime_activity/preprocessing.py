"""Loading and filtering of Danish Maritime Authority AIS data.

The raw data has one row per AIS message. This module turns it into the
subsets used in the analysis: fishing vessels only, optionally restricted to
a single flag state.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# Name of the timestamp column in the DMA export.
TIMESTAMP = "# Timestamp"

# The first three digits of an MMSI number are the Maritime Identification
# Digits (MID), which identify the vessel's flag state.
FLAG_PREFIXES: dict[str, tuple[str, ...]] = {
    "Danish": ("219", "220"),
    "Russian": ("273",),
    # Common flags of convenience: Panama, Liberia, Marshall Islands, Malta,
    # Comoros, Hong Kong, Cambodia, Cook Islands and others.
    "FoC": ("583", "470", "351", "352", "353", "354", "636", "637",
            "215", "477", "412", "413", "518"),
}


def load_ais(path: str | Path) -> pd.DataFrame:
    """Load AIS messages from a ``.parquet`` or ``.csv`` file.

    CSV files written by this project keep the raw-file row index as their
    first column, so it is restored as the index.

    Parameters
    ----------
    path : str or Path
        Location of the AIS file.

    Returns
    -------
    pandas.DataFrame
        AIS messages with the timestamp column parsed to datetime.
    """
    path = Path(path)
    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
    else:
        df = pd.read_csv(path, index_col=0, low_memory=False)
    df[TIMESTAMP] = pd.to_datetime(df[TIMESTAMP])
    return df


def filter_fishing(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only messages from vessels whose ship type is fishing.

    The comparison ignores case, and both ``Ship type`` and ``ship type``
    column names are accepted, since they differ between DMA exports.
    """
    col = "Ship type" if "Ship type" in df.columns else "ship type"
    return df[df[col].str.lower() == "fishing"].copy()


def classify_mmsi(mmsi) -> str:
    """Map an MMSI number to a flag group.

    Parameters
    ----------
    mmsi : int, float or str
        Vessel MMSI number.

    Returns
    -------
    str
        ``"Danish"``, ``"Russian"``, ``"FoC"`` (flag of convenience) or
        ``"Other"``.
    """
    mmsi_str = str(int(mmsi))
    for group, prefixes in FLAG_PREFIXES.items():
        if mmsi_str.startswith(prefixes):
            return group
    return "Other"


def filter_flag(df: pd.DataFrame, flag: str) -> pd.DataFrame:
    """Keep only vessels belonging to one flag group, e.g. ``"Russian"``."""
    prefixes = FLAG_PREFIXES[flag]
    mask = df["MMSI"].astype("int64").astype(str).str.startswith(prefixes)
    return df[mask].copy()


def valid_position(df: pd.DataFrame) -> pd.Series:
    """Return a boolean mask of messages with a usable position.

    AIS encodes "position not available" as latitude 91 and longitude 181,
    so any value outside the valid coordinate range is rejected.
    """
    return df["Latitude"].between(-90, 90) & df["Longitude"].between(-180, 180)
