"""Detection of AIS dark periods for fishing vessels in Danish waters.

Modules
-------
preprocessing
    Load AIS data, keep fishing vessels and map MMSI numbers to flag groups.
gaps
    Find dark periods (AIS gaps between 2 hours and 1 day) and label tracks.
plotting
    Maps and charts of dark periods, cables and fishing activity.
"""

from .gaps import detect_dark_periods, flag_dark_events
from .preprocessing import classify_mmsi, filter_fishing, filter_flag, load_ais

__all__ = [
    "load_ais",
    "filter_fishing",
    "filter_flag",
    "classify_mmsi",
    "detect_dark_periods",
    "flag_dark_events",
]
