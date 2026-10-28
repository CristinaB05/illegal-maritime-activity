"""Tests for dark-period detection on small synthetic tracks."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from illegal_maritime_activity.gaps import (  # noqa: E402
    detect_dark_periods, flag_dark_events, haversine_km,
)
from illegal_maritime_activity.preprocessing import TIMESTAMP, classify_mmsi  # noqa: E402


def make_track(mmsi, times, lat=55.0, lon=12.0):
    """Build a minimal AIS track: one message per timestamp, fixed position."""
    return pd.DataFrame({
        "MMSI": mmsi,
        TIMESTAMP: pd.to_datetime(times),
        "Latitude": lat,
        "Longitude": lon,
        "Navigational status": "Engaged in fishing",
        "Name": f"V{mmsi}",
        "IMO": "0",
    })


def test_gap_thresholds_are_exclusive():
    # Gaps of 30 min, 2 h (not > 2 h), 3 h (dark), 24 h (not < 1 day).
    track = make_track(273000001, [
        "2024-01-01 00:00", "2024-01-01 00:30", "2024-01-01 02:30",
        "2024-01-01 05:30", "2024-01-02 05:30",
    ])
    events = detect_dark_periods(track)
    assert len(events) == 1
    assert events.loc[0, "gap_hours"] == 3
    assert events.loc[0, "off_time"] == pd.Timestamp("2024-01-01 02:30")


def test_gaps_are_not_computed_across_vessels():
    a = make_track(273000001, ["2024-01-01 00:00", "2024-01-01 00:30"])
    b = make_track(273000002, ["2024-01-01 05:00", "2024-01-01 05:30"])
    assert detect_dark_periods(pd.concat([a, b], ignore_index=True)).empty


def test_flag_dark_events_marks_off_and_on():
    track = make_track(273000001, [
        "2024-01-01 00:00", "2024-01-01 04:00", "2024-01-01 04:30",
    ])
    flagged = flag_dark_events(track, detect_dark_periods(track))
    assert flagged["Status"].tolist() == ["off", "on", "Regular"]


def test_haversine_one_degree_of_latitude():
    assert haversine_km(55, 12, 56, 12) == pytest.approx(111.2, abs=0.1)


@pytest.mark.parametrize("mmsi, flag", [
    (273212100, "Russian"), (219000000, "Danish"),
    (636000000, "FoC"), (230000000, "Other"),
])
def test_classify_mmsi(mmsi, flag):
    assert classify_mmsi(mmsi) == flag
