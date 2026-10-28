"""Detection of AIS transmission gaps ("dark periods").

A dark period is a gap between two consecutive AIS messages of the same
vessel that is longer than ``min_gap`` (default 2 hours, to ignore short
technical drop-outs) and shorter than ``max_gap`` (default 1 day, to avoid
vessels that are docked or have simply left receiver coverage).

The last message before the gap marks where the AIS went **off**; the first
message after it marks where it came back **on**.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .preprocessing import TIMESTAMP, valid_position

EARTH_RADIUS_KM = 6371.0088
KM_PER_NAUTICAL_MILE = 1.852


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in kilometres between two sets of points.

    All arguments are in decimal degrees and may be scalars or arrays.
    """
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = (np.sin((lat2 - lat1) / 2) ** 2
         + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2)
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def detect_dark_periods(
    df: pd.DataFrame,
    min_gap: pd.Timedelta = pd.Timedelta(hours=2),
    max_gap: pd.Timedelta = pd.Timedelta(days=1),
) -> pd.DataFrame:
    """Find every dark period in a set of AIS messages.

    Parameters
    ----------
    df : pandas.DataFrame
        AIS messages with ``MMSI``, timestamp, ``Latitude``, ``Longitude``
        and ``Navigational status`` columns.
    min_gap, max_gap : pandas.Timedelta
        Gaps strictly between these two values count as dark periods.

    Returns
    -------
    pandas.DataFrame
        One row per dark period with the vessel identity, the time and
        position just before (``off_*``) and just after (``on_*``) the gap,
        the gap length in hours, the straight-line distance between the two
        positions and the average speed in knots needed to cover it.
        Distance and speed are NaN when either position is unavailable.
        ``on_row`` is the raw-data index of the message that ends the gap.
    """
    # Compare each message with the previous message of the same vessel.
    df = df.sort_values(["MMSI", TIMESTAMP])
    prev = df.groupby("MMSI").shift(1)
    gap = df[TIMESTAMP] - prev[TIMESTAMP]
    mask = (gap > min_gap) & (gap < max_gap)

    # `prev` is a shifted copy of `df`, so both share the same index and the
    # "off" message of each gap sits on the same row as its "on" message.
    on, off = df[mask], prev[mask]
    events = pd.DataFrame({
        "MMSI": on["MMSI"],
        "IMO": on.get("IMO"),
        "Name": on.get("Name"),
        "off_time": off[TIMESTAMP],
        "on_time": on[TIMESTAMP],
        "gap_hours": gap[mask].dt.total_seconds() / 3600,
        "off_lat": off["Latitude"], "off_lon": off["Longitude"],
        "on_lat": on["Latitude"], "on_lon": on["Longitude"],
        "off_nav_status": off["Navigational status"],
        "on_nav_status": on["Navigational status"],
    })

    # How far the vessel moved while dark, and how fast it would have had to
    # travel in a straight line to get there. Skipped when either message
    # carries the AIS "position not available" value.
    both_valid = valid_position(on) & valid_position(off)
    distance = haversine_km(events["off_lat"], events["off_lon"],
                            events["on_lat"], events["on_lon"])
    events["distance_km"] = distance.where(both_valid)
    events["implied_speed_kn"] = (
        events["distance_km"] / KM_PER_NAUTICAL_MILE / events["gap_hours"]
    )

    events.index.name = "on_row"
    return events.reset_index()


def flag_dark_events(df: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Label every message as ``Regular``, ``off``, ``on`` or ``on/off``.

    Adds the boolean columns ``ais_off`` (last message before a gap) and
    ``ais_on`` (first message after a gap), plus a ``Status`` column used to
    highlight dark moments when plotting full tracks. A message that ends one
    dark period and starts the next is labelled ``on/off``.
    """
    df = df.sort_values(["MMSI", TIMESTAMP]).copy()
    df["ais_on"] = df.index.isin(set(events["on_row"]))
    # The "off" message is the one right before an "on" message.
    df["ais_off"] = (df.groupby("MMSI")["ais_on"]
                     .shift(-1, fill_value=False).astype(bool))

    df["Status"] = np.select(
        [df["ais_on"] & df["ais_off"], df["ais_on"], df["ais_off"]],
        ["on/off", "on", "off"],
        default="Regular",
    )
    return df
