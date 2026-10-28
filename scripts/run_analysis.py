"""Detect AIS dark periods and write result tables and figures.

Outputs:
  results/dark_periods.csv              one row per dark period
  results/dark_periods_per_vessel.csv   counts and durations per vessel
  results/vessels_with_status.csv       every message with off/on flags
  figures/dark_periods_map.png
  figures/gap_durations.png

Usage:
    python scripts/run_analysis.py
    python scripts/run_analysis.py --min-gap 3 --max-gap 12
"""

import argparse
from pathlib import Path

import pandas as pd

from _paths import ROOT
from illegal_maritime_activity import detect_dark_periods, flag_dark_events, load_ais
from illegal_maritime_activity.plotting import (
    load_basemaps, plot_dark_events, plot_gap_durations,
)


def summarise_by_vessel(events: pd.DataFrame) -> pd.DataFrame:
    """Number of dark periods, total and longest dark time for each vessel."""
    return (events.groupby(["MMSI", "Name"])
            .agg(dark_periods=("gap_hours", "size"),
                 total_dark_hours=("gap_hours", "sum"),
                 longest_gap_hours=("gap_hours", "max"))
            .sort_values("dark_periods", ascending=False))


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path,
                        default=ROOT / "data" / "processed" / "russian_fishing_vessels_2024.csv")
    parser.add_argument("--min-gap", type=float, default=2,
                        help="shortest gap counted, in hours, exclusive (default: 2)")
    parser.add_argument("--max-gap", type=float, default=24,
                        help="longest gap counted, in hours, exclusive (default: 24)")
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--figures-dir", type=Path, default=ROOT / "figures")
    args = parser.parse_args()
    args.results_dir.mkdir(exist_ok=True)
    args.figures_dir.mkdir(exist_ok=True)

    # The sprint files already carry a Status column; it is recomputed here.
    df = load_ais(args.input).drop(columns=["Status"], errors="ignore")

    events = detect_dark_periods(df, pd.Timedelta(hours=args.min_gap),
                                 pd.Timedelta(hours=args.max_gap))
    events.to_csv(args.results_dir / "dark_periods.csv", index=False)
    summarise_by_vessel(events).to_csv(args.results_dir / "dark_periods_per_vessel.csv")
    flag_dark_events(df, events).to_csv(args.results_dir / "vessels_with_status.csv")

    waters, cables = load_basemaps()  # None when the optional layers are absent
    fig, _ = plot_dark_events(events, waters, cables)
    fig.savefig(args.figures_dir / "dark_periods_map.png", dpi=200)
    fig, _ = plot_gap_durations(events)
    fig.savefig(args.figures_dir / "gap_durations.png", dpi=200)

    print(f"Vessels analysed:        {df['MMSI'].nunique()}")
    print(f"Vessels with dark gaps:  {events['MMSI'].nunique()}")
    print(f"Dark periods detected:   {len(events)}")
    print(f"Median gap length:       {events['gap_hours'].median():.1f} h")


if __name__ == "__main__":
    main()
